#!/usr/bin/env python3
"""
闲置推演引擎 - OpenClaw 在无用户请求时自动进行代码领域和项目推演成长

功能:
1. 监控闲置状态 (无请求超过设定时间)
2. 代码领域推演 - 分析项目代码,发现优化点,生成改进建议
3. 项目完善推演 - 检查项目完整性,补充缺失组件
4. 成长记录 - 将推演结果存入CRM和知识库

用法:
  python3 scripts/idle_growth_engine.py              # 前台运行
  python3 scripts/idle_growth_engine.py --daemon     # 后台运行
  python3 scripts/idle_growth_engine.py --status     # 查看状态
  python3 scripts/idle_growth_engine.py --stop       # 停止
"""

import os
import sys
import json
import time
import signal
import random
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# 配置
IDLE_THRESHOLD_SECONDS = 300  # 5分钟无请求视为闲置
GROWTH_INTERVAL_SECONDS = 600  # 每10分钟执行一轮推演
MAX_GROWTH_PER_SESSION = 20   # 每轮最多推演20个任务

PID_FILE = PROJECT_ROOT / ".idle_growth.pid"
STATE_FILE = PROJECT_ROOT / ".idle_growth_state.json"
LOG_FILE = PROJECT_ROOT / "logs" / "idle_growth.log"
LAST_REQUEST_FILE = PROJECT_ROOT / ".last_request_time"

LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
log = logging.getLogger("idle_growth")


@dataclass
class GrowthTask:
    """推演任务"""
    task_type: str  # code_analysis, project_improve, skill_expand, doc_complete
    target: str     # 目标文件/目录/项目
    description: str
    priority: int = 5
    status: str = "pending"
    result: str = ""
    created_at: str = ""
    completed_at: str = ""


class IdleGrowthEngine:
    """闲置推演引擎"""
    
    def __init__(self):
        self.running = False
        self.last_growth_time = 0
        self.growth_count = 0
        self.tasks_completed = 0
        self.current_task: Optional[GrowthTask] = None
        
        # 加载 Bridge 调用能力
        try:
            from code_agent import CodeAgent
            self.code_agent = CodeAgent(workspace=PROJECT_ROOT)
            log.info("[代码代理] 已加载")
        except ImportError:
            self.code_agent = None
            log.warning("[代码代理] 未加载")
        
        # 加载推演链
        try:
            from wechat_chain_processor import ChainProcessor
            self.chain = ChainProcessor()
            log.info("[推演链] 已加载")
        except ImportError:
            self.chain = None
            log.warning("[推演链] 未加载，将使用简化模式")
    
    def is_idle(self) -> bool:
        """检测是否处于闲置状态"""
        # 检查最后请求时间文件
        if LAST_REQUEST_FILE.exists():
            try:
                last_time = float(LAST_REQUEST_FILE.read_text().strip())
                idle_seconds = time.time() - last_time
                return idle_seconds > IDLE_THRESHOLD_SECONDS
            except:
                pass
        
        # 如果文件不存在，检查 Bridge 是否有活动
        # 默认认为闲置
        return True
    
    def update_last_request(self):
        """更新最后请求时间（供 Bridge 调用）"""
        try:
            LAST_REQUEST_FILE.write_text(str(time.time()))
        except:
            pass
    
    def generate_growth_tasks(self) -> List[GrowthTask]:
        """生成推演任务列表"""
        tasks = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 代码分析任务 - 扫描项目中的Python文件
        scripts_dir = PROJECT_ROOT / "scripts"
        py_files = list(scripts_dir.glob("*.py"))
        random.shuffle(py_files)
        
        for f in py_files[:3]:
            tasks.append(GrowthTask(
                task_type="code_analysis",
                target=str(f),
                description=f"分析 {f.name} 的代码质量和优化点",
                priority=random.randint(3, 7),
                created_at=now,
            ))
        
        # 2. 项目完善任务
        project_tasks = [
            GrowthTask(
                task_type="project_improve",
                target="workspace/skills",
                description="扫描 Skill 库，检查是否有重复或过时的技能",
                priority=5,
                created_at=now,
            ),
            GrowthTask(
                task_type="project_improve",
                target="tests",
                description="检查测试覆盖率，生成缺失的测试用例建议",
                priority=6,
                created_at=now,
            ),
            GrowthTask(
                task_type="doc_complete",
                target="docs",
                description="检查文档完整性，补充缺失的文档",
                priority=4,
                created_at=now,
            ),
        ]
        tasks.extend(project_tasks)
        
        # 3. 代码领域推演 - 学习新技术
        code_learning_topics = [
            "Python 3.12 新特性和最佳实践",
            "异步编程优化模式",
            "代码性能优化技巧",
            "设计模式在AI系统中的应用",
            "错误处理和日志最佳实践",
        ]
        topic = random.choice(code_learning_topics)
        tasks.append(GrowthTask(
            task_type="skill_expand",
            target="code_domain",
            description=f"推演学习: {topic}",
            priority=5,
            created_at=now,
        ))
        
        # 4. 项目特定推演
        try:
            from deduction_db import DeductionDB
            db = DeductionDB()
            projects = db.get_projects()
            active_projects = [p for p in projects if p.get("status") == "active"]
            db.close()
            
            for proj in active_projects[:2]:
                tasks.append(GrowthTask(
                    task_type="project_improve",
                    target=f"project:{proj['id']}",
                    description=f"推演完善项目 [{proj['name']}]: 检查目标达成进度，识别阻塞问题",
                    priority=8,
                    created_at=now,
                ))
        except Exception as e:
            log.warning(f"加载项目列表失败: {e}")
        
        # 按优先级排序
        tasks.sort(key=lambda t: -t.priority)
        return tasks[:MAX_GROWTH_PER_SESSION]
    
    def execute_task(self, task: GrowthTask) -> bool:
        """执行单个推演任务"""
        self.current_task = task
        task.status = "running"
        log.info(f"🧠 执行任务: [{task.task_type}] {task.description[:50]}...")
        
        try:
            if task.task_type == "code_analysis":
                result = self._analyze_code(task.target)
            elif task.task_type == "project_improve":
                result = self._improve_project(task.target, task.description)
            elif task.task_type == "skill_expand":
                result = self._expand_skill(task.description)
            elif task.task_type == "doc_complete":
                result = self._complete_docs(task.target)
            else:
                result = f"未知任务类型: {task.task_type}"
            
            task.result = result[:2000] if result else "无结果"
            task.status = "completed"
            task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.info(f"  ✅ 完成: {task.result[:80]}...")
            return True
            
        except Exception as e:
            task.status = "failed"
            task.result = f"错误: {e}"
            log.error(f"  ❌ 失败: {e}")
            return False
        finally:
            self.current_task = None
    
    def _analyze_code(self, file_path: str) -> str:
        """分析代码文件"""
        if not self.code_agent:
            return "代码代理未加载"
        
        # 读取文件
        result = self.code_agent.read_file(file_path)
        if not result.success:
            return f"读取失败: {result.error}"
        
        code_content = result.output[:3000]
        
        # 用推演链分析
        if self.chain:
            prompt = f"""分析以下代码的质量和优化点:

```python
{code_content}
```

请从以下角度分析:
1. 代码结构和可读性
2. 潜在的bug或错误处理问题
3. 性能优化建议
4. 最佳实践改进建议

输出简洁的改进建议列表。"""
            
            try:
                chain_result = self.chain.process(prompt, context="代码分析任务")
                if chain_result and chain_result.final_answer:
                    return chain_result.final_answer
            except Exception as e:
                log.warning(f"推演链调用失败: {e}")
        
        # 简化分析
        lines = code_content.split("\n")
        stats = {
            "total_lines": len(lines),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "comment_lines": sum(1 for l in lines if l.strip().startswith("#")),
            "function_count": sum(1 for l in lines if l.strip().startswith("def ")),
            "class_count": sum(1 for l in lines if l.strip().startswith("class ")),
        }
        return f"代码统计: {json.dumps(stats, ensure_ascii=False)}"
    
    def _improve_project(self, target: str, description: str) -> str:
        """项目完善推演"""
        if self.chain:
            prompt = f"""项目完善任务:
目标: {target}
描述: {description}

请分析并给出具体的改进建议和行动项。"""
            
            try:
                result = self.chain.process(prompt, context="项目完善任务")
                if result and result.final_answer:
                    return result.final_answer
            except Exception as e:
                log.warning(f"推演链调用失败: {e}")
        
        # 简化处理
        if target.startswith("project:"):
            return f"项目推演完成: {description}"
        
        if self.code_agent:
            result = self.code_agent.list_dir(target, max_depth=2)
            if result.success:
                return f"目录结构分析完成:\n{result.output[:500]}"
        
        return f"项目分析完成: {target}"
    
    def _expand_skill(self, description: str) -> str:
        """技能扩展推演"""
        if self.chain:
            prompt = f"""技能学习推演:
{description}

请生成:
1. 核心概念总结
2. 实践应用示例
3. 可封装为Skill的代码模板"""
            
            try:
                result = self.chain.process(prompt, context="技能扩展任务")
                if result and result.final_answer:
                    # 尝试保存为Skill
                    self._save_as_skill(description, result.final_answer)
                    return result.final_answer
            except Exception as e:
                log.warning(f"推演链调用失败: {e}")
        
        return f"技能推演完成: {description}"
    
    def _complete_docs(self, target: str) -> str:
        """文档完善"""
        if self.code_agent:
            result = self.code_agent.list_dir(target, max_depth=2)
            if result.success:
                files = result.output
                return f"文档目录扫描完成:\n{files[:500]}\n\n建议: 检查是否缺少README或API文档"
        
        return "文档检查完成"
    
    def _save_as_skill(self, topic: str, content: str):
        """将推演结果保存为Skill"""
        try:
            import re
            # 提取代码块
            code_blocks = re.findall(r"```python\n(.*?)```", content, re.DOTALL)
            if not code_blocks:
                return
            
            # 生成Skill文件名
            safe_name = re.sub(r"[^\w]+", "_", topic)[:30].lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            skill_name = f"skill_idle_{safe_name}_{timestamp}"
            
            skill_path = PROJECT_ROOT / "workspace" / "skills" / f"{skill_name}.py"
            meta_path = skill_path.with_suffix(".meta.json")
            
            # 保存代码
            skill_code = f'''#!/usr/bin/env python3
"""
自动推演生成的Skill: {topic}
生成时间: {datetime.now().isoformat()}
"""

{code_blocks[0]}

if __name__ == "__main__":
    print("Skill: {topic}")
'''
            skill_path.write_text(skill_code, encoding="utf-8")
            
            # 保存元数据
            meta = {
                "name": skill_name,
                "description": topic,
                "tags": ["auto_generated", "idle_growth"],
                "created_at": datetime.now().isoformat(),
                "source": "idle_growth_engine",
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            
            log.info(f"  💾 保存Skill: {skill_name}")
        except Exception as e:
            log.warning(f"保存Skill失败: {e}")
    
    def save_growth_record(self, tasks: List[GrowthTask]):
        """保存成长记录到CRM"""
        try:
            from deduction_db import DeductionDB
            db = DeductionDB()
            
            completed = [t for t in tasks if t.status == "completed"]
            if completed:
                summary = f"闲置推演完成 {len(completed)} 个任务:\n"
                for t in completed[:5]:
                    summary += f"- [{t.task_type}] {t.description[:40]}\n"
                
                # 记录为推演日志
                db.execute("""
                    INSERT INTO deduction_logs (session_id, round_num, phase, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    f"idle_{datetime.now().strftime('%Y%m%d')}",
                    self.growth_count,
                    "idle_growth",
                    summary,
                    datetime.now().isoformat(),
                ))
                db.conn.commit()
            
            db.close()
            log.info(f"📝 成长记录已保存到CRM")
        except Exception as e:
            log.warning(f"保存成长记录失败: {e}")
    
    def run_growth_cycle(self):
        """执行一轮推演"""
        self.growth_count += 1
        log.info(f"\n{'='*50}")
        log.info(f"🌱 开始第 {self.growth_count} 轮闲置推演")
        log.info(f"{'='*50}")
        
        # 生成任务
        tasks = self.generate_growth_tasks()
        log.info(f"生成 {len(tasks)} 个推演任务")
        
        # 执行任务
        for i, task in enumerate(tasks):
            # 检查是否仍然闲置
            if not self.is_idle():
                log.info(f"⚡ 检测到用户活动，暂停推演 ({i}/{len(tasks)} 已完成)")
                break
            
            if not self.running:
                log.info("推演引擎已停止")
                break
            
            self.execute_task(task)
            self.tasks_completed += 1
            
            # 任务间隔，避免过度消耗资源
            time.sleep(2)
        
        # 保存成长记录
        self.save_growth_record(tasks)
        
        log.info(f"🌱 第 {self.growth_count} 轮推演完成")
        self.last_growth_time = time.time()
    
    def run(self):
        """主运行循环"""
        # 写入PID
        PID_FILE.write_text(str(os.getpid()))
        
        self.running = True
        log.info("=" * 50)
        log.info("🌙 闲置推演引擎启动")
        log.info(f"闲置阈值: {IDLE_THRESHOLD_SECONDS}s")
        log.info(f"推演间隔: {GROWTH_INTERVAL_SECONDS}s")
        log.info("=" * 50)
        
        # 信号处理
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        
        while self.running:
            try:
                if self.is_idle():
                    # 检查是否到达推演间隔
                    if time.time() - self.last_growth_time > GROWTH_INTERVAL_SECONDS:
                        self.run_growth_cycle()
                else:
                    log.debug("用户活跃中，等待闲置...")
                
                # 等待下次检查
                time.sleep(30)
                self._save_state()
                
            except Exception as e:
                log.error(f"推演循环异常: {e}")
                time.sleep(60)
        
        log.info("🌙 闲置推演引擎已停止")
        self._cleanup()
    
    def _handle_signal(self, signum, frame):
        """处理停止信号"""
        log.info(f"收到信号 {signum}，准备退出...")
        self.running = False
    
    def _save_state(self):
        """保存状态"""
        state = {
            "pid": os.getpid(),
            "running": self.running,
            "growth_count": self.growth_count,
            "tasks_completed": self.tasks_completed,
            "last_growth_time": self.last_growth_time,
            "current_task": asdict(self.current_task) if self.current_task else None,
            "updated_at": datetime.now().isoformat(),
        }
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def _cleanup(self):
        """清理"""
        if PID_FILE.exists():
            PID_FILE.unlink()


def get_status() -> dict:
    """获取状态"""
    if not STATE_FILE.exists():
        return {"running": False}
    
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        
        # 检查进程是否存在
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                state["process_alive"] = True
            except:
                state["process_alive"] = False
        else:
            state["process_alive"] = False
        
        return state
    except:
        return {"running": False}


def stop_engine():
    """停止引擎"""
    if not PID_FILE.exists():
        print("闲置推演引擎未运行")
        return
    
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"已发送停止信号 (PID {pid})")
        
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print("闲置推演引擎已停止")
                return
        
        print("强制终止...")
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        print("进程已不存在")
        PID_FILE.unlink()
    except Exception as e:
        print(f"停止失败: {e}")


def print_status():
    """打印状态"""
    state = get_status()
    
    print("\n" + "=" * 50)
    print("🌙 闲置推演引擎状态")
    print("=" * 50)
    
    if state.get("process_alive"):
        print(f"状态: ✅ 运行中 (PID {state.get('pid', '?')})")
    else:
        print("状态: ❌ 未运行")
    
    print(f"推演轮次: {state.get('growth_count', 0)}")
    print(f"完成任务: {state.get('tasks_completed', 0)}")
    
    if state.get("last_growth_time"):
        last = datetime.fromtimestamp(state["last_growth_time"])
        print(f"上次推演: {last.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if state.get("current_task"):
        task = state["current_task"]
        print(f"当前任务: [{task.get('task_type')}] {task.get('description', '')[:40]}")
    
    print(f"更新时间: {state.get('updated_at', '-')}")
    print("=" * 50 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw 闲置推演引擎")
    parser.add_argument("--daemon", "-d", action="store_true", help="后台运行")
    parser.add_argument("--stop", action="store_true", help="停止引擎")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--once", action="store_true", help="执行一轮后退出")
    args = parser.parse_args()
    
    if args.status:
        print_status()
        return
    
    if args.stop:
        stop_engine()
        return
    
    # 检查是否已运行
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            print(f"闲置推演引擎已在运行 (PID {pid})")
            print("使用 --stop 停止，或 --status 查看状态")
            return
        except ProcessLookupError:
            PID_FILE.unlink()
    
    # 后台运行
    if args.daemon:
        if os.fork() > 0:
            print("闲置推演引擎已启动（后台）")
            return
        os.setsid()
        if os.fork() > 0:
            sys.exit(0)
    
    # 启动引擎
    engine = IdleGrowthEngine()
    
    if args.once:
        engine.running = True
        engine.run_growth_cycle()
    else:
        engine.run()


if __name__ == "__main__":
    main()
