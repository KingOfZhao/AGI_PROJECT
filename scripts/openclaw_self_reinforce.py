#!/usr/bin/env python3
"""
OpenClaw Self-Reinforcement Trainer
====================================
持续进化训练器 — 利用智谱 GLM API 强化 OpenClaw 代码能力，目标超越 Claude Opus 4.6

策略:
- 前10轮: 基础热身 (HumanEval / LeetCode Hard 风格)
- 中间轮: 真实 GitHub Issue + SWE-bench 风格
- 后期轮: 自生成合成难题 → 自我测试 → 进化
- 混用模型: 日常 GLM-5-Turbo (快+省), 关键验证 GLM-5

遵循 Local-First 策略:
- 智谱 Coding Plan Pro: https://open.bigmodel.cn/api/coding/paas/v4
- 额度守护: 自动降级 + 峰谷调度
- Skill 存储: workspace/skills/ (6000+ skills 库)
"""

import os
import sys
import json
import time
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

import requests

# ── 路径 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "core"))

SKILLS_DIR = PROJECT_ROOT / "workspace" / "skills"
TRAINING_LOG_DIR = PROJECT_ROOT / "data" / "training_logs"
TRAINING_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ════════════════════════════════════════════════════════════
# 智谱额度守护器
# ════════════════════════════════════════════════════════════

@dataclass
class QuotaStatus:
    five_hour: float = 100.0
    weekly: float = 100.0
    monthly: float = 100.0
    five_hour_used: int = 0
    five_hour_total: int = 400
    is_peak: bool = False
    multiplier: float = 1.0

class ZhipuQuotaGuard:
    """智谱额度守护 + 自动降级"""
    
    # Coding Plan Pro 专用端点 (重要!)
    CODING_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"
    QUOTA_URL = "https://open.bigmodel.cn/api/monitor/usage/quota/limit"
    
    # 峰谷时段 (UTC+8)
    PEAK_HOURS = range(14, 18)  # 14:00-18:00 = 3x, 其他 = 2x
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY", "")
        if not self.api_key:
            # 尝试从 .env 加载
            env_file = PROJECT_ROOT / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("ZHIPU_API_KEY="):
                        self.api_key = line.split("=", 1)[1].strip().strip('"')
                        break
        
        self.base_url = self.CODING_BASE_URL
        self.client = None
        self._init_client()
        
        self.primary_model = "glm-5-turbo"
        self.fallback_model = "glm-4.7"
        self.current_model = self.primary_model
        
        self.last_quota_check = 0
        self.quota_cache: QuotaStatus = QuotaStatus()
        self.call_count = 0
        self.total_tokens = 0
        
    def _init_client(self):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            print("⚠️ openai 库未安装，使用 requests 直接调用")
            self.client = None
    
    def check_quota(self, force: bool = False) -> QuotaStatus:
        """查询剩余额度 (5分钟缓存)"""
        if not force and time.time() - self.last_quota_check < 300:
            return self.quota_cache
        
        try:
            resp = requests.get(
                self.QUOTA_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                self.quota_cache = QuotaStatus(
                    five_hour=data.get("fiveHourRemainingPercent", 100),
                    weekly=data.get("weeklyRemainingPercent", 100),
                    monthly=data.get("monthlyRemainingPercent", 100),
                    five_hour_used=data.get("fiveHourUsed", 0),
                    five_hour_total=data.get("fiveHourTotal", 400),
                )
                self.last_quota_check = time.time()
        except Exception as e:
            print(f"⚠️ 额度查询失败: {e}")
        
        # 计算峰谷
        hour = datetime.now().hour
        self.quota_cache.is_peak = hour in self.PEAK_HOURS
        self.quota_cache.multiplier = 3.0 if self.quota_cache.is_peak else 2.0
        
        return self.quota_cache
    
    def should_downgrade(self) -> bool:
        """检查是否需要降级 (任意额度 < 5%)"""
        q = self.check_quota()
        low = any(pct < 5 for pct in [q.five_hour, q.weekly, q.monthly])
        
        if low:
            if self.current_model != self.fallback_model:
                print(f"🚨 额度不足 (5h:{q.five_hour:.1f}% 周:{q.weekly:.1f}% 月:{q.monthly:.1f}%), 降级到 {self.fallback_model}")
            self.current_model = self.fallback_model
            return True
        else:
            self.current_model = self.primary_model
            return False
    
    def chat(self, messages: List[Dict], max_tokens: int = 8192, 
             temperature: float = 0.7, use_cache: bool = True) -> Dict:
        """带额度守护的聊天调用"""
        self.should_downgrade()
        t0 = time.time()
        
        try:
            extra_headers = {}
            if use_cache:
                extra_headers["anthropic-beta"] = "prompt-caching-2024-07-31"
            
            if self.client:
                resp = self.client.chat.completions.create(
                    model=self.current_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    extra_headers=extra_headers if extra_headers else None
                )
                content = resp.choices[0].message.content
                tokens = getattr(resp.usage, 'total_tokens', 0)
            else:
                # fallback to requests
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.current_model, "messages": messages, 
                          "max_tokens": max_tokens, "temperature": temperature},
                    timeout=120
                )
                data = resp.json()
                if "error" in data:
                    raise Exception(data["error"].get("message", str(data["error"])))
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
            
            self.call_count += 1
            self.total_tokens += tokens
            
            return {
                "success": True,
                "content": content,
                "model": self.current_model,
                "tokens": tokens,
                "duration": round(time.time() - t0, 2)
            }
        except Exception as e:
            err = str(e)
            # 1113 = 余额不足, 快速失败
            if "1113" in err:
                print(f"❌ 余额不足，停止调用")
                return {"success": False, "content": "", "error": "余额不足", "model": self.current_model}
            # 429 = 限速, 等待重试
            if "429" in err or "1302" in err:
                print(f"⏳ 限速，等待5秒后重试...")
                time.sleep(5)
                return self.chat(messages, max_tokens, temperature, use_cache)
            
            return {"success": False, "content": "", "error": err[:200], "model": self.current_model,
                    "duration": round(time.time() - t0, 2)}


# ════════════════════════════════════════════════════════════
# 训练任务库
# ════════════════════════════════════════════════════════════

WARMUP_TASKS = [
    # HumanEval 风格
    {"id": "warmup_01", "desc": "实现一个函数，检查字符串是否为有效的括号序列（支持 ()[]{}）", "difficulty": "easy"},
    {"id": "warmup_02", "desc": "实现 LRU 缓存，支持 get/put 操作，O(1) 时间复杂度", "difficulty": "medium"},
    {"id": "warmup_03", "desc": "实现一个线程安全的单例模式装饰器", "difficulty": "medium"},
    {"id": "warmup_04", "desc": "实现 Trie 树，支持 insert/search/startsWith/delete", "difficulty": "medium"},
    {"id": "warmup_05", "desc": "实现一个支持通配符 * 和 ? 的文件名匹配函数", "difficulty": "medium"},
    
    # LeetCode Hard 风格
    {"id": "warmup_06", "desc": "实现正则表达式匹配，支持 . 和 * 元字符", "difficulty": "hard"},
    {"id": "warmup_07", "desc": "合并 K 个有序链表，要求 O(N log K) 时间复杂度", "difficulty": "hard"},
    {"id": "warmup_08", "desc": "实现一个支持 O(1) 获取中位数的数据结构", "difficulty": "hard"},
    {"id": "warmup_09", "desc": "实现滑动窗口最大值，要求 O(N) 时间复杂度", "difficulty": "hard"},
    {"id": "warmup_10", "desc": "计算直方图中最大矩形面积", "difficulty": "hard"},
]

INTERMEDIATE_TASKS = [
    # GitHub Issue 风格
    {"id": "inter_01", "desc": "实现一个高性能的异步任务队列，支持优先级、分布式锁、自动重试和死信队列", "difficulty": "expert"},
    {"id": "inter_02", "desc": "实现一个轻量级的依赖注入容器，支持单例/瞬态/作用域生命周期", "difficulty": "expert"},
    {"id": "inter_03", "desc": "实现一个支持增量更新的 JSON Diff/Patch 库 (RFC 6902)", "difficulty": "expert"},
    {"id": "inter_04", "desc": "实现一个基于 AST 的代码格式化器，支持 Python 代码", "difficulty": "expert"},
    {"id": "inter_05", "desc": "实现一个支持事务的内存 KV 数据库，带 MVCC 并发控制", "difficulty": "expert"},
    
    # SWE-bench 风格
    {"id": "inter_06", "desc": "实现一个 Git 风格的版本控制系统核心：blob/tree/commit 对象 + 分支 + 合并", "difficulty": "expert"},
    {"id": "inter_07", "desc": "实现一个支持协程的轻量级调度器，类似 asyncio 但更简单", "difficulty": "expert"},
    {"id": "inter_08", "desc": "实现一个支持管道的 Shell 命令解析器和执行器", "difficulty": "expert"},
    {"id": "inter_09", "desc": "实现一个支持热重载的配置管理系统，带变更通知和回滚", "difficulty": "expert"},
    {"id": "inter_10", "desc": "实现一个基于 LSP 协议的简单代码补全服务器", "difficulty": "expert"},
]

ADVANCED_TASKS = [
    # 系统级挑战
    {"id": "adv_01", "desc": "实现一个分布式一致性算法 (Raft) 的核心逻辑", "difficulty": "master"},
    {"id": "adv_02", "desc": "实现一个支持 SQL 子集的查询引擎 (SELECT/WHERE/JOIN/GROUP BY)", "difficulty": "master"},
    {"id": "adv_03", "desc": "实现一个字节码虚拟机，支持基本的算术和控制流", "difficulty": "master"},
    {"id": "adv_04", "desc": "实现一个基于 Actor 模型的并发框架", "difficulty": "master"},
    {"id": "adv_05", "desc": "实现一个支持增量编译的表达式编译器", "difficulty": "master"},
]


# ════════════════════════════════════════════════════════════
# 代码评估器
# ════════════════════════════════════════════════════════════

class CodeEvaluator:
    """代码质量评估"""
    
    @staticmethod
    def extract_code(response: str) -> str:
        """从响应中提取代码块"""
        import re
        # 优先提取 ```python 块
        blocks = re.findall(r'```python\n(.*?)```', response, re.DOTALL)
        if blocks:
            return blocks[0].strip()
        # 其次 ``` 块
        blocks = re.findall(r'```\n(.*?)```', response, re.DOTALL)
        if blocks:
            return blocks[0].strip()
        return ""
    
    @staticmethod
    def syntax_check(code: str) -> Tuple[bool, str]:
        """语法检查"""
        try:
            compile(code, '<string>', 'exec')
            return True, ""
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} at line {e.lineno}"
    
    @staticmethod
    def run_tests(code: str, timeout: int = 10) -> Tuple[bool, str]:
        """运行内置测试"""
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.write("\n\n# Auto-run if __name__ == '__main__' block exists\n")
            f.write("if __name__ == '__main__':\n    pass\n")
            temp_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True, text=True, timeout=timeout
            )
            os.unlink(temp_path)
            
            if result.returncode == 0:
                return True, result.stdout[:500] if result.stdout else "运行成功"
            else:
                return False, result.stderr[:500]
        except subprocess.TimeoutExpired:
            os.unlink(temp_path)
            return False, "执行超时"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def complexity_score(code: str) -> Dict:
        """代码复杂度评分"""
        lines = code.split('\n')
        non_empty = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        # 简单指标
        loc = len(non_empty)
        functions = len([l for l in lines if l.strip().startswith('def ')])
        classes = len([l for l in lines if l.strip().startswith('class ')])
        imports = len([l for l in lines if l.strip().startswith(('import ', 'from '))])
        
        return {
            "loc": loc,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "avg_line_length": sum(len(l) for l in non_empty) / max(loc, 1)
        }


# ════════════════════════════════════════════════════════════
# Skill 存储器
# ════════════════════════════════════════════════════════════

class SkillStorage:
    """Skill 存储管理"""
    
    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)
    
    def save_skill(self, task_id: str, code: str, metadata: Dict) -> Path:
        """保存 Skill 到库"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = task_id.replace(" ", "_").replace("/", "_")[:50]
        
        # 保存代码
        skill_file = self.skills_dir / f"reinforce_{safe_id}_{timestamp}.py"
        skill_file.write_text(code, encoding='utf-8')
        
        # 保存元数据
        meta_file = self.skills_dir / f"reinforce_{safe_id}_{timestamp}.meta.json"
        meta_file.write_text(json.dumps({
            "task_id": task_id,
            "created": timestamp,
            "source": "openclaw_self_reinforce",
            **metadata
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        
        return skill_file
    
    def get_best_version(self, task_id: str) -> Optional[str]:
        """获取任务的最佳版本代码"""
        safe_id = task_id.replace(" ", "_").replace("/", "_")[:50]
        pattern = f"reinforce_{safe_id}_*.py"
        files = sorted(self.skills_dir.glob(pattern), reverse=True)
        
        if files:
            return files[0].read_text(encoding='utf-8')
        return None


# ════════════════════════════════════════════════════════════
# 自我强化训练器
# ════════════════════════════════════════════════════════════

class SelfReinforceTrainer:
    """OpenClaw 自我强化训练器"""
    
    SYSTEM_PROMPT = """你是 OpenClaw 代码专精训练师。
目标：在代码实现领域超越 Claude Opus 4.6。

每次输出必须包含:
1. 完整可运行的 Python 代码 (```python 代码块)
2. 内置测试用例 (if __name__ == '__main__' 块)
3. 改进说明 (相比上一版本的优化点)

代码要求:
- 类型提示完整
- 错误处理健壮
- 性能优化到位
- 边界条件覆盖
- 文档字符串清晰"""

    def __init__(self):
        self.guard = ZhipuQuotaGuard()
        self.evaluator = CodeEvaluator()
        self.storage = SkillStorage()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.history: List[Dict] = []
        
    def reinforce(self, task_desc: str, previous_code: str = "", 
                  feedback: str = "", use_strong_model: bool = False) -> Dict:
        """单轮强化"""
        # 临时切换强模型
        original_model = self.guard.current_model
        if use_strong_model:
            self.guard.current_model = "glm-5"
        
        user_prompt = f"任务：{task_desc}"
        if previous_code:
            user_prompt += f"\n\n上一版本代码：\n```python\n{previous_code}\n```"
        if feedback:
            user_prompt += f"\n\n反馈：{feedback}"
        user_prompt += "\n\n请生成下一代更优实现。"
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        result = self.guard.chat(messages, max_tokens=8192, temperature=0.7)
        
        # 恢复模型
        self.guard.current_model = original_model
        
        if result["success"]:
            code = self.evaluator.extract_code(result["content"])
            syntax_ok, syntax_err = self.evaluator.syntax_check(code)
            
            result["code"] = code
            result["syntax_ok"] = syntax_ok
            result["syntax_error"] = syntax_err
            result["complexity"] = self.evaluator.complexity_score(code)
            
            if syntax_ok:
                test_ok, test_output = self.evaluator.run_tests(code)
                result["test_ok"] = test_ok
                result["test_output"] = test_output
            else:
                result["test_ok"] = False
                result["test_output"] = syntax_err
        
        return result
    
    def run_epoch(self, task: Dict, epochs: int = 10, 
                  auto_feedback: bool = True) -> List[Dict]:
        """运行多轮进化"""
        task_id = task["id"]
        task_desc = task["desc"]
        difficulty = task.get("difficulty", "unknown")
        
        print(f"\n{'='*60}")
        print(f"🎯 任务: {task_id} ({difficulty})")
        print(f"📝 {task_desc}")
        print(f"{'='*60}")
        
        results = []
        best_code = self.storage.get_best_version(task_id) or ""
        
        for epoch in range(epochs):
            print(f"\n--- 第 {epoch+1}/{epochs} 轮 ---")
            
            # 生成反馈
            if auto_feedback and results:
                last = results[-1]
                if not last.get("syntax_ok"):
                    feedback = f"语法错误: {last.get('syntax_error', '未知')}"
                elif not last.get("test_ok"):
                    feedback = f"测试失败: {last.get('test_output', '未知')}"
                else:
                    feedback = "运行通过，请继续优化性能和代码质量"
            else:
                feedback = input(f"第 {epoch+1} 轮反馈 (回车跳过): ").strip()
                if not feedback:
                    feedback = "请继续优化"
            
            # 最后一轮用强模型验证
            use_strong = (epoch == epochs - 1 and difficulty in ("expert", "master"))
            
            result = self.reinforce(task_desc, best_code, feedback, use_strong)
            result["epoch"] = epoch + 1
            result["task_id"] = task_id
            results.append(result)
            
            # 打印结果
            if result["success"]:
                status = "✅" if result.get("test_ok") else ("⚠️" if result.get("syntax_ok") else "❌")
                print(f"{status} 模型: {result['model']} | Tokens: {result.get('tokens', 0)} | 耗时: {result.get('duration', 0)}s")
                print(f"   代码: {result.get('complexity', {}).get('loc', 0)} 行, "
                      f"{result.get('complexity', {}).get('functions', 0)} 函数")
                
                # 更新最佳代码
                if result.get("test_ok") and result.get("code"):
                    best_code = result["code"]
            else:
                print(f"❌ 失败: {result.get('error', '未知错误')}")
                if "余额不足" in result.get("error", ""):
                    print("💸 额度耗尽，停止训练")
                    break
        
        # 保存最佳版本
        if best_code:
            skill_path = self.storage.save_skill(task_id, best_code, {
                "difficulty": difficulty,
                "epochs": len(results),
                "final_model": results[-1].get("model", ""),
                "final_test_ok": results[-1].get("test_ok", False),
            })
            print(f"\n💾 已保存最佳版本: {skill_path.name}")
        
        return results
    
    def run_training_session(self, phase: str = "warmup", 
                             epochs_per_task: int = 5,
                             max_tasks: int = 5) -> Dict:
        """运行训练会话"""
        if phase == "warmup":
            tasks = WARMUP_TASKS[:max_tasks]
        elif phase == "intermediate":
            tasks = INTERMEDIATE_TASKS[:max_tasks]
        elif phase == "advanced":
            tasks = ADVANCED_TASKS[:max_tasks]
        else:
            tasks = WARMUP_TASKS[:3] + INTERMEDIATE_TASKS[:2]
        
        print(f"\n🚀 开始 {phase} 阶段训练")
        print(f"📊 任务数: {len(tasks)}, 每任务轮数: {epochs_per_task}")
        print(f"💳 当前模型: {self.guard.current_model}")
        
        # 检查额度
        quota = self.guard.check_quota(force=True)
        print(f"📈 额度状态: 5h={quota.five_hour:.1f}% 周={quota.weekly:.1f}% 月={quota.monthly:.1f}%")
        print(f"⏰ 峰谷: {'峰时 3x' if quota.is_peak else '谷时 2x'}")
        
        session_results = {
            "session_id": self.session_id,
            "phase": phase,
            "start_time": datetime.now().isoformat(),
            "tasks": []
        }
        
        for task in tasks:
            try:
                results = self.run_epoch(task, epochs_per_task, auto_feedback=True)
                session_results["tasks"].append({
                    "task_id": task["id"],
                    "epochs": len(results),
                    "success_rate": sum(1 for r in results if r.get("test_ok")) / max(len(results), 1),
                    "total_tokens": sum(r.get("tokens", 0) for r in results),
                })
            except KeyboardInterrupt:
                print("\n⚠️ 用户中断")
                break
            except Exception as e:
                print(f"❌ 任务异常: {e}")
                continue
        
        session_results["end_time"] = datetime.now().isoformat()
        session_results["total_calls"] = self.guard.call_count
        session_results["total_tokens"] = self.guard.total_tokens
        
        # 保存会话日志
        log_file = TRAINING_LOG_DIR / f"session_{self.session_id}.json"
        log_file.write_text(json.dumps(session_results, ensure_ascii=False, indent=2))
        print(f"\n📄 会话日志: {log_file}")
        
        return session_results
    
    def generate_synthetic_task(self) -> Dict:
        """让模型自己生成合成难题"""
        messages = [
            {"role": "system", "content": "你是一个编程挑战设计师。生成一个有挑战性但可实现的 Python 编程任务。"},
            {"role": "user", "content": """生成一个编程任务，要求：
1. 难度适中偏难 (LeetCode Hard 级别)
2. 需要综合运用数据结构和算法
3. 有明确的输入输出定义
4. 可以用单文件 Python 实现

输出格式 (JSON):
{"id": "synthetic_xxx", "desc": "任务描述", "difficulty": "hard/expert"}"""}
        ]
        
        result = self.guard.chat(messages, max_tokens=500, temperature=0.9)
        if result["success"]:
            try:
                # 提取 JSON
                import re
                match = re.search(r'\{[^}]+\}', result["content"])
                if match:
                    return json.loads(match.group())
            except:
                pass
        
        # fallback
        return {"id": f"synthetic_{int(time.time())}", 
                "desc": "实现一个支持正则表达式的文本搜索引擎", 
                "difficulty": "expert"}


# ════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw 自我强化训练器")
    parser.add_argument("--phase", choices=["warmup", "intermediate", "advanced", "mixed"], 
                        default="warmup", help="训练阶段")
    parser.add_argument("--epochs", type=int, default=5, help="每任务轮数")
    parser.add_argument("--tasks", type=int, default=3, help="最大任务数")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    parser.add_argument("--synthetic", action="store_true", help="生成合成任务")
    args = parser.parse_args()
    
    trainer = SelfReinforceTrainer()
    
    if args.synthetic:
        print("🧪 生成合成任务...")
        task = trainer.generate_synthetic_task()
        print(f"📝 生成任务: {task}")
        trainer.run_epoch(task, args.epochs)
    elif args.interactive:
        print("🎮 交互模式")
        while True:
            desc = input("\n任务描述 (q退出): ").strip()
            if desc.lower() == 'q':
                break
            task = {"id": f"custom_{int(time.time())}", "desc": desc, "difficulty": "custom"}
            trainer.run_epoch(task, args.epochs, auto_feedback=False)
    else:
        trainer.run_training_session(args.phase, args.epochs, args.tasks)
    
    print(f"\n✨ 训练完成! 总调用: {trainer.guard.call_count}, 总Tokens: {trainer.guard.total_tokens}")


if __name__ == "__main__":
    main()
