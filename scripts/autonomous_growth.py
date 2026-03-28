#!/usr/bin/env python3
"""
OpenClaw 自主成长引擎
=======================
自主调用 + 优先级驱动 + 持续推演优化

核心能力:
1. 优先级调度: 根据项目紧急度/技能缺口/推演队列动态排序
2. 自主触发: 闲置检测/定时任务/API触发
3. 多模式成长: 代码强化/知识推演/技能扩展/节点证伪
4. 资源守护: 智谱额度监控/峰谷调度/自动降级

遵循 Local-First 策略:
- Tier 0: 本地 Skill 库复用
- Tier 1: 本地 Ollama + 智谱 GLM
- Tier 2: Claude (仅必要时)
"""

import os
import sys
import json
import time
import signal
import threading
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import logging

# ── 路径 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("autonomous_growth")

# ════════════════════════════════════════════════════════════
# 成长优先级
# ════════════════════════════════════════════════════════════

class GrowthPriority(Enum):
    """成长任务优先级"""
    CRITICAL = 1    # 阻塞问题/紧急修复
    HIGH = 2        # 用户明确请求/活跃项目推演
    MEDIUM = 3      # 常规成长/技能扩展
    LOW = 4         # 闲置探索/知识归纳
    BACKGROUND = 5  # 后台优化/清理


@dataclass
class GrowthTask:
    """成长任务"""
    id: str
    type: str  # code_reinforce | deduction | skill_expand | node_falsify | knowledge_sync
    priority: GrowthPriority
    title: str
    description: str = ""
    project_id: str = ""
    plan_id: str = ""
    context: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    estimated_tokens: int = 5000
    max_rounds: int = 5
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "project_id": self.project_id,
            "plan_id": self.plan_id,
            "context": self.context,
            "created_at": self.created_at,
            "estimated_tokens": self.estimated_tokens,
        }


# ════════════════════════════════════════════════════════════
# 优先级调度器
# ════════════════════════════════════════════════════════════

class PriorityScheduler:
    """优先级任务调度器"""
    
    def __init__(self):
        self.queue: List[GrowthTask] = []
        self.lock = threading.Lock()
        self.completed: List[Dict] = []
        
    def add_task(self, task: GrowthTask):
        with self.lock:
            self.queue.append(task)
            self.queue.sort(key=lambda t: (t.priority.value, t.created_at))
            log.info(f"📥 任务入队: [{task.priority.name}] {task.title}")
    
    def get_next(self) -> Optional[GrowthTask]:
        with self.lock:
            if self.queue:
                return self.queue.pop(0)
            return None
    
    def peek(self) -> Optional[GrowthTask]:
        with self.lock:
            return self.queue[0] if self.queue else None
    
    def size(self) -> int:
        return len(self.queue)
    
    def mark_completed(self, task: GrowthTask, result: Dict):
        with self.lock:
            self.completed.append({
                "task": task.to_dict(),
                "result": result,
                "completed_at": datetime.now().isoformat()
            })
            # 只保留最近100条
            if len(self.completed) > 100:
                self.completed = self.completed[-100:]


# ════════════════════════════════════════════════════════════
# 成长任务生成器
# ════════════════════════════════════════════════════════════

class TaskGenerator:
    """从各种来源生成成长任务"""
    
    def __init__(self):
        self.db = None
        self._init_db()
    
    def _init_db(self):
        try:
            from deduction_db import DeductionDB
            self.db = DeductionDB()
        except Exception as e:
            log.warning(f"DeductionDB 加载失败: {e}")
    
    def scan_all_sources(self) -> List[GrowthTask]:
        """扫描所有来源生成任务"""
        tasks = []
        tasks.extend(self._from_blocked_problems())
        tasks.extend(self._from_deduction_queue())
        tasks.extend(self._from_skill_gaps())
        tasks.extend(self._from_low_truth_nodes())
        tasks.extend(self._from_code_reinforce_queue())
        return tasks
    
    def _from_blocked_problems(self) -> List[GrowthTask]:
        """从阻塞问题生成任务"""
        tasks = []
        if not self.db:
            return tasks
        
        try:
            rows = self.db.conn.execute(
                "SELECT * FROM blocked_problems WHERE status='open' ORDER BY severity DESC"
            ).fetchall()
            for row in rows:
                r = dict(row)
                severity_map = {"critical": GrowthPriority.CRITICAL, 
                               "high": GrowthPriority.HIGH,
                               "medium": GrowthPriority.MEDIUM,
                               "low": GrowthPriority.LOW}
                tasks.append(GrowthTask(
                    id=f"blocked_{r['id']}",
                    type="deduction",
                    priority=severity_map.get(r.get("severity", "medium"), GrowthPriority.MEDIUM),
                    title=f"解决阻塞: {r['title'][:50]}",
                    description=r.get("description", ""),
                    project_id=r.get("project_id", ""),
                    context={"blocked_id": r["id"], "suggested_solution": r.get("suggested_solution")},
                    estimated_tokens=8000,
                    max_rounds=10
                ))
        except Exception as e:
            log.warning(f"扫描阻塞问题失败: {e}")
        
        return tasks
    
    def _from_deduction_queue(self) -> List[GrowthTask]:
        """从推演队列生成任务"""
        tasks = []
        if not self.db:
            return tasks
        
        try:
            rows = self.db.conn.execute(
                "SELECT * FROM deduction_plans WHERE status='queued' ORDER BY priority, created_at LIMIT 10"
            ).fetchall()
            for row in rows:
                r = dict(row)
                priority_map = {"urgent": GrowthPriority.CRITICAL,
                               "high": GrowthPriority.HIGH,
                               "medium": GrowthPriority.MEDIUM,
                               "low": GrowthPriority.LOW}
                tasks.append(GrowthTask(
                    id=f"plan_{r['id']}",
                    type="deduction",
                    priority=priority_map.get(r.get("priority", "medium"), GrowthPriority.MEDIUM),
                    title=r["title"],
                    description=r.get("description", ""),
                    project_id=r.get("project_id", ""),
                    plan_id=r["id"],
                    context={"ulds_laws": r.get("ulds_laws"), "target_metrics": r.get("target_metrics")},
                    estimated_tokens=int(r.get("estimated_rounds", 5)) * 3000,
                    max_rounds=int(r.get("estimated_rounds", 5))
                ))
        except Exception as e:
            log.warning(f"扫描推演队列失败: {e}")
        
        return tasks
    
    def _from_skill_gaps(self) -> List[GrowthTask]:
        """从技能缺口生成任务"""
        tasks = []
        
        # 定义核心能力维度
        core_dimensions = [
            ("distributed_systems", "分布式系统", "实现分布式一致性/负载均衡/容错机制"),
            ("compiler_design", "编译器设计", "实现词法分析/语法解析/代码生成"),
            ("database_engine", "数据库引擎", "实现B+树索引/事务ACID/查询优化"),
            ("network_protocol", "网络协议", "实现TCP状态机/HTTP解析/RPC框架"),
            ("ml_inference", "机器学习推理", "实现模型加载/张量计算/推理优化"),
        ]
        
        skills_dir = PROJECT_ROOT / "workspace" / "skills"
        for dim_id, dim_name, dim_desc in core_dimensions:
            # 检查是否已有相关 skill
            existing = list(skills_dir.glob(f"*{dim_id}*.py")) + list(skills_dir.glob(f"*{dim_id}*.meta.json"))
            if len(existing) < 3:  # 少于3个相关skill视为缺口
                tasks.append(GrowthTask(
                    id=f"skillgap_{dim_id}",
                    type="code_reinforce",
                    priority=GrowthPriority.MEDIUM,
                    title=f"技能扩展: {dim_name}",
                    description=dim_desc,
                    context={"dimension": dim_id, "existing_count": len(existing)},
                    estimated_tokens=10000,
                    max_rounds=8
                ))
        
        return tasks
    
    def _from_low_truth_nodes(self) -> List[GrowthTask]:
        """从低置信度节点生成证伪任务"""
        tasks = []
        
        try:
            db_path = PROJECT_ROOT / "core" / "proven_nodes.db"
            if not db_path.exists():
                return tasks
            
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM proven_nodes WHERE confidence < 0.7 AND confidence > 0.3 LIMIT 10"
            ).fetchall()
            conn.close()
            
            for row in rows:
                r = dict(row)
                tasks.append(GrowthTask(
                    id=f"falsify_{r['id']}",
                    type="node_falsify",
                    priority=GrowthPriority.LOW,
                    title=f"证伪验证: {r.get('name', '未命名')[:40]}",
                    description=r.get("content", "")[:200],
                    context={"node_id": r["id"], "current_confidence": r.get("confidence", 0)},
                    estimated_tokens=3000,
                    max_rounds=3
                ))
        except Exception as e:
            log.debug(f"扫描低置信度节点失败: {e}")
        
        return tasks
    
    def _from_code_reinforce_queue(self) -> List[GrowthTask]:
        """从代码强化队列生成任务"""
        # 检查是否有待强化的代码任务
        queue_file = PROJECT_ROOT / "data" / "reinforce_queue.json"
        tasks = []
        
        if queue_file.exists():
            try:
                queue = json.loads(queue_file.read_text())
                for item in queue[:5]:
                    tasks.append(GrowthTask(
                        id=f"reinforce_{item.get('id', int(time.time()))}",
                        type="code_reinforce",
                        priority=GrowthPriority.HIGH if item.get("urgent") else GrowthPriority.MEDIUM,
                        title=item.get("title", "代码强化任务"),
                        description=item.get("description", ""),
                        context=item.get("context", {}),
                        estimated_tokens=item.get("tokens", 8000),
                        max_rounds=item.get("rounds", 5)
                    ))
            except Exception as e:
                log.warning(f"读取强化队列失败: {e}")
        
        return tasks


# ════════════════════════════════════════════════════════════
# 任务执行器
# ════════════════════════════════════════════════════════════

class TaskExecutor:
    """任务执行器"""
    
    def __init__(self):
        self.guard = None
        self.chain = None
        self.reinforce_trainer = None
        self._init_components()
    
    def _init_components(self):
        """延迟初始化组件"""
        try:
            from openclaw_self_reinforce import ZhipuQuotaGuard, SelfReinforceTrainer
            self.guard = ZhipuQuotaGuard()
            self.reinforce_trainer = SelfReinforceTrainer()
            log.info("✅ 代码强化组件已加载")
        except Exception as e:
            log.warning(f"代码强化组件加载失败: {e}")
        
        try:
            from wechat_chain_processor import ChainProcessor
            self.chain = ChainProcessor()
            log.info("✅ 7步链组件已加载")
        except Exception as e:
            log.warning(f"7步链组件加载失败: {e}")
    
    def execute(self, task: GrowthTask) -> Dict:
        """执行单个任务"""
        log.info(f"🚀 执行任务: [{task.type}] {task.title}")
        t0 = time.time()
        
        try:
            if task.type == "code_reinforce":
                result = self._execute_code_reinforce(task)
            elif task.type == "deduction":
                result = self._execute_deduction(task)
            elif task.type == "node_falsify":
                result = self._execute_falsify(task)
            elif task.type == "skill_expand":
                result = self._execute_skill_expand(task)
            elif task.type == "knowledge_sync":
                result = self._execute_knowledge_sync(task)
            else:
                result = {"success": False, "error": f"未知任务类型: {task.type}"}
            
            result["duration"] = round(time.time() - t0, 2)
            log.info(f"✅ 任务完成: {task.title} ({result['duration']}s)")
            return result
        
        except Exception as e:
            log.error(f"❌ 任务失败: {task.title} - {e}")
            return {"success": False, "error": str(e), "duration": round(time.time() - t0, 2)}
    
    def _execute_code_reinforce(self, task: GrowthTask) -> Dict:
        """执行代码强化任务"""
        if not self.reinforce_trainer:
            return {"success": False, "error": "代码强化组件未加载"}
        
        task_dict = {
            "id": task.id,
            "desc": task.description or task.title,
            "difficulty": task.context.get("difficulty", "expert")
        }
        
        results = self.reinforce_trainer.run_epoch(task_dict, task.max_rounds, auto_feedback=True)
        
        success_count = sum(1 for r in results if r.get("test_ok"))
        return {
            "success": success_count > 0,
            "epochs": len(results),
            "success_rate": success_count / max(len(results), 1),
            "total_tokens": sum(r.get("tokens", 0) for r in results),
            "final_model": results[-1].get("model") if results else None
        }
    
    def _execute_deduction(self, task: GrowthTask) -> Dict:
        """执行推演任务"""
        if not self.chain:
            return {"success": False, "error": "7步链组件未加载"}
        
        # 构建推演 prompt
        prompt = f"""请对以下问题进行深度推演分析:

**任务**: {task.title}
**描述**: {task.description}
**项目**: {task.project_id}
**ULDS相关**: {task.context.get('ulds_laws', '待分析')}

请进行:
1. 问题分解 (自上而下)
2. 知识归纳 (自下而上)
3. 跨域碰撞 (寻找重叠)
4. 可执行步骤输出

输出格式:
- 核心发现 (3-5条)
- 待证伪假设 (2-3条)
- 下一步行动 (可执行)
"""
        
        result = self.chain.process(prompt)
        
        if result and result.final_answer:
            # 更新推演计划状态
            if task.plan_id:
                try:
                    from deduction_db import DeductionDB
                    db = DeductionDB()
                    db.conn.execute(
                        "UPDATE deduction_plans SET status='in_progress', started_at=? WHERE id=?",
                        (datetime.now().isoformat(), task.plan_id)
                    )
                    db.conn.commit()
                    db.close()
                except Exception:
                    pass
            
            return {
                "success": True,
                "answer": result.final_answer[:1000],
                "steps": len(result.steps),
                "route": result.route_decision,
                "risks": len(result.risks)
            }
        
        return {"success": False, "error": "推演无结果"}
    
    def _execute_falsify(self, task: GrowthTask) -> Dict:
        """执行证伪任务"""
        if not self.chain:
            return {"success": False, "error": "7步链组件未加载"}
        
        prompt = f"""请尝试证伪以下节点:

**节点内容**: {task.description}
**当前置信度**: {task.context.get('current_confidence', 0.5)}

证伪分析:
1. 逻辑一致性检查
2. 边界条件测试
3. 反例搜索
4. 实际应用验证

输出 JSON:
{{"can_falsify": bool, "reason": "...", "new_confidence": 0.0-1.0, "evidence": "..."}}
"""
        
        result = self.chain.process(prompt)
        
        if result and result.final_answer:
            # 尝试解析结果
            try:
                import re
                match = re.search(r'\{[^}]+\}', result.final_answer)
                if match:
                    parsed = json.loads(match.group())
                    return {"success": True, **parsed}
            except:
                pass
            
            return {"success": True, "raw_answer": result.final_answer[:500]}
        
        return {"success": False, "error": "证伪分析无结果"}
    
    def _execute_skill_expand(self, task: GrowthTask) -> Dict:
        """执行技能扩展任务"""
        # 调用 PCM 路由器寻找相关 skill
        try:
            from pcm_skill_router import route_skills
            related = route_skills(task.title, top_k=5)
            
            if related:
                return {
                    "success": True,
                    "found_skills": [s["name"] for s in related],
                    "top_score": related[0].get("score", 0)
                }
            else:
                # 没找到相关 skill，触发代码强化生成
                return self._execute_code_reinforce(task)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_knowledge_sync(self, task: GrowthTask) -> Dict:
        """执行知识同步任务"""
        # 刷新 AGI 上下文
        try:
            from openclaw_bridge import _refresh_context
            _refresh_context()
            return {"success": True, "action": "context_refreshed"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ════════════════════════════════════════════════════════════
# 自主成长引擎
# ════════════════════════════════════════════════════════════

class AutonomousGrowthEngine:
    """自主成长引擎 — OpenClaw 核心进化系统"""
    
    STATE_FILE = PROJECT_ROOT / ".autonomous_growth_state.json"
    PID_FILE = PROJECT_ROOT / ".autonomous_growth.pid"
    LAST_REQUEST_FILE = PROJECT_ROOT / ".last_request_time"
    
    def __init__(self):
        self.scheduler = PriorityScheduler()
        self.generator = TaskGenerator()
        self.executor = TaskExecutor()
        
        self.running = False
        self.paused = False
        self.idle_threshold = 300  # 5分钟无请求视为闲置
        self.scan_interval = 60    # 1分钟扫描一次任务源
        self.max_concurrent = 2    # 最大并发任务数
        
        self.stats = {
            "total_tasks": 0,
            "success_tasks": 0,
            "failed_tasks": 0,
            "total_tokens": 0,
            "start_time": None,
            "last_task_time": None
        }
        
        self._load_state()
    
    def _load_state(self):
        """加载持久化状态"""
        if self.STATE_FILE.exists():
            try:
                state = json.loads(self.STATE_FILE.read_text())
                self.stats.update(state.get("stats", {}))
                # 恢复队列
                for t in state.get("queue", []):
                    task = GrowthTask(
                        id=t["id"], type=t["type"],
                        priority=GrowthPriority(t["priority"]),
                        title=t["title"], description=t.get("description", ""),
                        project_id=t.get("project_id", ""),
                        plan_id=t.get("plan_id", ""),
                        context=t.get("context", {}),
                        created_at=t.get("created_at", "")
                    )
                    self.scheduler.add_task(task)
                log.info(f"📂 恢复状态: {self.scheduler.size()} 任务待处理")
            except Exception as e:
                log.warning(f"状态加载失败: {e}")
    
    def _save_state(self):
        """保存持久化状态"""
        try:
            state = {
                "stats": self.stats,
                "queue": [t.to_dict() for t in self.scheduler.queue],
                "saved_at": datetime.now().isoformat()
            }
            self.STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        except Exception as e:
            log.warning(f"状态保存失败: {e}")
    
    def _is_idle(self) -> bool:
        """检查系统是否闲置"""
        try:
            if self.LAST_REQUEST_FILE.exists():
                last_time = float(self.LAST_REQUEST_FILE.read_text().strip())
                return (time.time() - last_time) > self.idle_threshold
        except:
            pass
        return True  # 默认闲置
    
    def _scan_and_queue(self):
        """扫描任务源并入队"""
        log.info("🔍 扫描任务源...")
        tasks = self.generator.scan_all_sources()
        
        # 过滤已在队列中的任务
        existing_ids = {t.id for t in self.scheduler.queue}
        new_tasks = [t for t in tasks if t.id not in existing_ids]
        
        for task in new_tasks:
            self.scheduler.add_task(task)
        
        if new_tasks:
            log.info(f"📥 新增 {len(new_tasks)} 个任务，队列总数: {self.scheduler.size()}")
    
    def _process_one(self) -> bool:
        """处理单个任务，返回是否有任务可处理"""
        task = self.scheduler.get_next()
        if not task:
            return False
        
        self.stats["total_tasks"] += 1
        self.stats["last_task_time"] = datetime.now().isoformat()
        
        result = self.executor.execute(task)
        
        if result.get("success"):
            self.stats["success_tasks"] += 1
        else:
            self.stats["failed_tasks"] += 1
        
        self.stats["total_tokens"] += result.get("total_tokens", 0)
        self.scheduler.mark_completed(task, result)
        self._save_state()
        
        return True
    
    def run_once(self) -> Dict:
        """运行一次成长循环 (适合 API 调用)"""
        self._scan_and_queue()
        
        if self.scheduler.size() == 0:
            return {"status": "no_tasks", "queue_size": 0}
        
        # 处理最高优先级任务
        task = self.scheduler.peek()
        if task:
            self._process_one()
            return {
                "status": "completed",
                "task": task.to_dict(),
                "queue_size": self.scheduler.size(),
                "stats": self.stats
            }
        
        return {"status": "empty", "queue_size": 0}
    
    def run_batch(self, max_tasks: int = 5) -> Dict:
        """批量运行多个任务"""
        self._scan_and_queue()
        
        results = []
        for _ in range(max_tasks):
            if not self._process_one():
                break
            results.append(self.scheduler.completed[-1] if self.scheduler.completed else None)
        
        return {
            "status": "batch_completed",
            "tasks_processed": len(results),
            "queue_remaining": self.scheduler.size(),
            "stats": self.stats
        }
    
    def run_daemon(self):
        """守护进程模式 — 持续自主成长"""
        log.info("🚀 启动自主成长守护进程")
        self.running = True
        self.stats["start_time"] = datetime.now().isoformat()
        
        # 写入 PID
        self.PID_FILE.write_text(str(os.getpid()))
        
        # 信号处理
        def handle_signal(signum, frame):
            log.info("📴 收到停止信号，正在保存状态...")
            self.running = False
        
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        last_scan = 0
        
        while self.running:
            try:
                # 定期扫描任务源
                if time.time() - last_scan > self.scan_interval:
                    self._scan_and_queue()
                    last_scan = time.time()
                
                # 检查是否闲置
                if not self._is_idle():
                    log.debug("⏸️ 用户活跃，暂停成长任务")
                    time.sleep(10)
                    continue
                
                # 检查是否暂停
                if self.paused:
                    time.sleep(5)
                    continue
                
                # 处理任务
                if self.scheduler.size() > 0:
                    self._process_one()
                else:
                    log.debug("💤 队列为空，等待新任务...")
                    time.sleep(30)
                
            except Exception as e:
                log.error(f"守护进程异常: {e}")
                time.sleep(10)
        
        # 清理
        self._save_state()
        if self.PID_FILE.exists():
            self.PID_FILE.unlink()
        log.info("✅ 自主成长守护进程已停止")
    
    def get_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "running": self.running,
            "paused": self.paused,
            "queue_size": self.scheduler.size(),
            "next_task": self.scheduler.peek().to_dict() if self.scheduler.peek() else None,
            "stats": self.stats,
            "is_idle": self._is_idle(),
            "recent_completed": self.scheduler.completed[-5:] if self.scheduler.completed else []
        }
    
    def add_task_manual(self, task_type: str, title: str, description: str = "",
                        priority: str = "medium", context: Dict = None) -> Dict:
        """手动添加任务 (供 API 调用)"""
        priority_map = {
            "critical": GrowthPriority.CRITICAL,
            "high": GrowthPriority.HIGH,
            "medium": GrowthPriority.MEDIUM,
            "low": GrowthPriority.LOW,
            "background": GrowthPriority.BACKGROUND
        }
        
        task = GrowthTask(
            id=f"manual_{int(time.time())}",
            type=task_type,
            priority=priority_map.get(priority, GrowthPriority.MEDIUM),
            title=title,
            description=description,
            context=context or {}
        )
        
        self.scheduler.add_task(task)
        self._save_state()
        
        return {"status": "added", "task": task.to_dict(), "queue_size": self.scheduler.size()}


# ════════════════════════════════════════════════════════════
# API 端点 (供 OpenClaw Bridge 调用)
# ════════════════════════════════════════════════════════════

_ENGINE: Optional[AutonomousGrowthEngine] = None

def get_engine() -> AutonomousGrowthEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = AutonomousGrowthEngine()
    return _ENGINE


def api_trigger_growth(task_type: str = None, title: str = None, 
                       priority: str = "medium") -> Dict:
    """API: 触发成长任务"""
    engine = get_engine()
    
    if task_type and title:
        return engine.add_task_manual(task_type, title, priority=priority)
    else:
        return engine.run_once()


def api_run_batch(max_tasks: int = 5) -> Dict:
    """API: 批量运行"""
    return get_engine().run_batch(max_tasks)


def api_get_status() -> Dict:
    """API: 获取状态"""
    return get_engine().get_status()


def api_pause():
    """API: 暂停"""
    engine = get_engine()
    engine.paused = True
    return {"status": "paused"}


def api_resume():
    """API: 恢复"""
    engine = get_engine()
    engine.paused = False
    return {"status": "resumed"}


# ════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw 自主成长引擎")
    parser.add_argument("--daemon", action="store_true", help="守护进程模式")
    parser.add_argument("--once", action="store_true", help="运行一次")
    parser.add_argument("--batch", type=int, default=0, help="批量运行N个任务")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--add", type=str, help="手动添加任务 (格式: type:title)")
    parser.add_argument("--priority", type=str, default="medium", help="任务优先级")
    parser.add_argument("--idle-threshold", type=int, default=300, help="闲置阈值(秒)")
    args = parser.parse_args()
    
    engine = get_engine()
    engine.idle_threshold = args.idle_threshold
    
    if args.status:
        status = engine.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.add:
        parts = args.add.split(":", 1)
        task_type = parts[0]
        title = parts[1] if len(parts) > 1 else "手动任务"
        result = engine.add_task_manual(task_type, title, priority=args.priority)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.batch > 0:
        result = engine.run_batch(args.batch)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.once:
        result = engine.run_once()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.daemon:
        engine.run_daemon()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
