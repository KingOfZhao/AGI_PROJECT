# orchestrator.py
# AGI Orchestrator: 君臣佐使 多模型协同架构
# 君(Emperor) = 本地14B: 无幻觉验证+路由决策+proven锚定
# 臣(Minister) = GLM-5: 主力算力(复杂代码/多语言/深度推理)
# 佐(Assistant) = GLM-4.7: 快速代码生成(简单任务/原型)
# 使(Messenger) = GLM-4.5-Air: 轻量响应(对话/规划)
# 目标：全面超越 Claude Opus 4.6

import hashlib
import json
import time
import re
import threading
from datetime import datetime

import agi_v13_cognitive_lattice as agi
import cognitive_core


# ==================== 思考步骤记录器 ====================
class ThinkingTracker:
    """记录orchestrator的完整思考过程，供前端折叠展示"""

    def __init__(self):
        self.steps = []
        self._lock = threading.Lock()

    def add(self, step_type, title, detail="", model=None):
        with self._lock:
            self.steps.append({
                "type": step_type,
                "title": title,
                "detail": detail,
                "model": model,
                "timestamp": time.time()
            })

    def to_list(self):
        with self._lock:
            return list(self.steps)

    def summary(self):
        with self._lock:
            return f"{len(self.steps)}步思考"


# ==================== 核心 Orchestrator ====================
class TaskOrchestrator:
    """本地14B作为主导者，检查真实节点充分性，智能调用云端辅助
    
    协同流程:
    1. 本地14B分析问题 → 提取意图和复杂度
    2. 搜索proven节点 → 检查覆盖率
    3. 覆盖率充分 → fast_path直接回答
    4. 覆盖率不足 → 根据任务类型路由到最优云端模型
    5. GLM-5协同模式 → 本地准备上下文 → GLM-5推理 → 本地验证锚定率
    6. 结果验证 → 拆解为真实节点 OR 标记unsolvable
    """

    def __init__(self, lattice):
        self.lattice = lattice
        self._broadcast_fn = None  # SSE广播回调

    def set_broadcast(self, fn):
        self._broadcast_fn = fn

    def _broadcast(self, step_type, detail, status="running"):
        if self._broadcast_fn:
            try:
                self._broadcast_fn(step_type, detail, status)
            except:
                pass
        print(f"  [Orchestrator:{step_type}] {detail}")

    # ==================== 问题追踪 ====================
    def track_problem(self, question, complexity=0.0, model="", routing_reason=""):
        """记录问题到追踪表，返回 problem_id"""
        q_hash = hashlib.md5(question.encode()).hexdigest()
        with self.lattice._lock:
            try:
                c = self.lattice.conn.execute("""
                    INSERT INTO problem_tracking
                    (user_question, question_hash, status, complexity_score,
                     assigned_model, routing_reason)
                    VALUES (?, ?, 'decomposing', ?, ?, ?)
                """, (question, q_hash, complexity, model, routing_reason))
                self.lattice.conn.commit()
                return c.lastrowid
            except Exception as e:
                print(f"  [问题追踪] 记录失败: {e}")
                return None

    def update_problem_status(self, problem_id, status, node_ids=None,
                              unsolvable_reason=None, proven_coverage=0.0):
        """更新问题状态"""
        if not problem_id:
            return
        with self.lattice._lock:
            try:
                self.lattice.conn.execute("""
                    UPDATE problem_tracking
                    SET status=?, final_node_ids=?, unsolvable_reason=?,
                        proven_coverage=?, updated_at=datetime('now')
                    WHERE id=?
                """, (status,
                      json.dumps(node_ids) if node_ids else None,
                      unsolvable_reason, proven_coverage, problem_id))
                self.lattice.conn.commit()
            except Exception as e:
                print(f"  [问题追踪] 更新失败: {e}")

    def log_step(self, problem_id, step_type, model_used, output_summary,
                 success=True, duration_ms=0):
        """记录拆解步骤到日志"""
        if not problem_id:
            return
        with self.lattice._lock:
            try:
                self.lattice.conn.execute("""
                    INSERT INTO problem_decomposition_log
                    (problem_id, step_type, model_used, output_summary,
                     success, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (problem_id, step_type, model_used,
                      str(output_summary)[:500], 1 if success else 0, duration_ms))
                self.lattice.conn.commit()
            except Exception as e:
                print(f"  [拆解日志] 记录失败: {e}")

    def get_unsolvable_problems(self, limit=50):
        """获取无法处理的问题列表"""
        with self.lattice._lock:
            c = self.lattice.conn.cursor()
            c.execute("""
                SELECT id, user_question, unsolvable_reason, retry_count,
                       complexity_score, assigned_model, created_at
                FROM problem_tracking
                WHERE status = 'unsolvable'
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in c.fetchall()]

    def get_problem_history(self, problem_id):
        """获取问题的完整拆解历史"""
        with self.lattice._lock:
            c = self.lattice.conn.cursor()
            c.execute("SELECT * FROM problem_tracking WHERE id=?", (problem_id,))
            problem = c.fetchone()
            if not problem:
                return None
            c.execute("""
                SELECT * FROM problem_decomposition_log
                WHERE problem_id=? ORDER BY created_at ASC
            """, (problem_id,))
            steps = [dict(r) for r in c.fetchall()]
            return {"problem": dict(problem), "steps": steps}

    def get_orchestrator_stats(self):
        """获取orchestrator统计数据"""
        with self.lattice._lock:
            c = self.lattice.conn.cursor()
            stats = {}
            c.execute("SELECT COUNT(*) as cnt FROM problem_tracking")
            stats['total_problems'] = c.fetchone()['cnt']
            c.execute("""
                SELECT status, COUNT(*) as cnt
                FROM problem_tracking GROUP BY status
            """)
            stats['status_dist'] = {r['status']: r['cnt'] for r in c.fetchall()}
            c.execute("""
                SELECT assigned_model, COUNT(*) as cnt
                FROM problem_tracking GROUP BY assigned_model
            """)
            stats['model_usage'] = {
                (r['assigned_model'] or 'unknown'): r['cnt']
                for r in c.fetchall()
            }
            c.execute("SELECT AVG(complexity_score) as avg FROM problem_tracking")
            row = c.fetchone()
            stats['avg_complexity'] = round(row['avg'] or 0, 3)
            c.execute("SELECT AVG(proven_coverage) as avg FROM problem_tracking")
            row = c.fetchone()
            stats['avg_proven_coverage'] = round(row['avg'] or 0, 3)
            return stats

    # ==================== 复杂度评估 ====================
    def analyze_complexity(self, question, context_nodes=None):
        """本地14B分析任务复杂度（0-1评分）和任务类型"""
        context_nodes = context_nodes or []
        features = {
            'length': len(question),
            'proven_count': sum(
                1 for n in context_nodes if n.get('status') == 'proven'),
            'total_related': len(context_nodes),
            'code_intent': self._detect_code_intent(question),
            'multi_step': self._detect_multi_step(question),
            'domain_count': len(
                set(n.get('domain', 'general') for n in context_nodes)),
        }

        # 计算proven命中率
        if features['total_related'] > 0:
            features['proven_rate'] = (
                features['proven_count'] / features['total_related'])
        else:
            features['proven_rate'] = 0.0

        # 复杂度评分
        score = 0.4  # 默认中等
        if features['proven_rate'] > 0.8 and features['proven_count'] >= 2:
            score = 0.1  # 简单：proven充分
        elif features['code_intent']:
            score = 0.6  # 代码任务
        elif features['multi_step']:
            score = 0.7  # 多步推理
        elif features['proven_rate'] < 0.3:
            score = 0.8  # 知识边界：proven少

        # 推断任务类型
        if features['code_intent']:
            task_type = 'code_generation'
        elif features['multi_step']:
            task_type = 'deep_reasoning'
        elif features['length'] < 30 and features['proven_rate'] > 0.5:
            task_type = 'quick_chat'
        else:
            task_type = 'general'

        return score, task_type, features

    def _detect_code_intent(self, question):
        kw = ['代码', '编写', '实现', '函数', 'class', 'def', 'function',
              '脚本', 'script', '程序', 'program', 'bug', '调试', '算法',
              'api', '接口', '数据库', 'sql', 'python', 'java', 'rust',
              'go ', 'golang', 'c#', 'csharp', '.net', 'typescript',
              'javascript', 'react', 'vue', 'flutter', 'swift',
              'wasm', 'webassembly', 'solidity', '智能合约', 'blockchain',
              'docker', 'k8s', 'kubernetes', 'ci/cd', 'devops',
              'unity', 'unreal', '游戏开发', 'game',
              'electron', 'tauri', '桌面应用', 'desktop']
        return any(k in question.lower() for k in kw)

    def _detect_code_complexity(self, question):
        """检测代码任务的复杂度: simple/medium/complex"""
        q = question.lower()
        # 复杂: 多语言/架构设计/系统级/非Python
        complex_kw = ['rust', 'go ', 'golang', 'c#', 'java', '.net',
                      'wasm', 'webassembly', 'solidity', '智能合约',
                      '架构', 'microservice', '微服务', '分布式',
                      'unity', 'unreal', '游戏引擎', 'electron', 'tauri',
                      '跨平台', '编译器', 'compiler', '操作系统', 'kernel',
                      '重构整个', '全栈', 'fullstack', '系统设计']
        # 中等: 标准代码生成
        medium_kw = ['python', 'javascript', 'typescript', 'react', 'vue',
                     'flutter', 'swift', 'sql', '数据库', 'api',
                     'docker', 'k8s', 'ci/cd']
        if any(k in q for k in complex_kw):
            return 'complex'
        if any(k in q for k in medium_kw):
            return 'medium'
        return 'simple'

    def _detect_multi_step(self, question):
        kw = ['如何', '步骤', '流程', '过程', '设计', '架构', '方案',
              '首先', '然后', '最后', '对比', '比较', '分析',
              'step', 'process', 'design', 'plan']
        return any(k in question.lower() for k in kw)

    # ==================== 真实节点充分性检查 ====================
    def check_proven_sufficiency(self, question, proven_nodes):
        """本地14B检查proven节点是否足够解决问题"""
        if not proven_nodes:
            return {
                'sufficient': False,
                'coverage': 0.0,
                'need_glm5': True,
                'reason': '完全无proven节点覆盖'
            }

        # 计算覆盖率：基于语义相似度
        high_sim = [n for n in proven_nodes
                    if n.get('similarity', 0) > 0.7]
        medium_sim = [n for n in proven_nodes
                      if 0.5 < n.get('similarity', 0) <= 0.7]
        coverage = min(1.0,
                       len(high_sim) * 0.3 + len(medium_sim) * 0.15)

        sufficient = coverage >= 0.6 and len(high_sim) >= 2
        need_glm5 = coverage < 0.4 or len(high_sim) == 0

        if sufficient:
            reason = f"proven充分: {len(high_sim)}个高相似+{len(medium_sim)}个中相似"
        elif need_glm5:
            reason = f"proven不足(覆盖{coverage:.0%})，需GLM-5辅助"
        else:
            reason = f"proven部分覆盖({coverage:.0%})，可用GLM-4.5-Air补充"

        return {
            'sufficient': sufficient,
            'coverage': round(coverage, 3),
            'need_glm5': need_glm5,
            'reason': reason,
            'high_sim_count': len(high_sim),
            'medium_sim_count': len(medium_sim)
        }

    # ==================== 君臣佐使 智能路由 ====================
    def route(self, question, proven_nodes, complexity, task_type):
        """君臣佐使路由:
        君(14B) = proven充分时fast_path验证
        臣(GLM-5) = 复杂代码/多语言/深度推理 (主力算力)
        佐(GLM-4.7) = 简单Python代码快速生成
        使(GLM-4.5-Air) = 轻量对话/规划
        """
        sufficiency = self.check_proven_sufficiency(question, proven_nodes)

        # 1. 君: proven充分 → fast_path (本地14B无幻觉验证)
        if sufficiency['sufficient']:
            return {
                'model': 'fast_path',
                'role': '君',
                'reason': f'[君] proven充分({sufficiency["coverage"]:.0%})，本地无幻觉验证',
                'proven_coverage': sufficiency['coverage'],
                'sufficiency': sufficiency
            }

        # 2. 代码任务 → 根据复杂度分流到臣(GLM-5)或佐(GLM-4.7)
        if task_type == 'code_generation':
            code_complexity = self._detect_code_complexity(question)
            if code_complexity == 'complex':
                # 臣: 复杂代码(多语言/架构/系统级) → GLM-5主力
                return {
                    'model': 'GLM-5',
                    'role': '臣',
                    'reason': f'[臣] 复杂代码任务({code_complexity})，GLM-5主力算力',
                    'proven_coverage': sufficiency['coverage'],
                    'sufficiency': sufficiency,
                    'code_complexity': code_complexity
                }
            elif code_complexity == 'medium':
                # 臣/佐分流: 中等代码，proven不足用GLM-5，否则GLM-4.7
                if sufficiency['need_glm5'] or complexity > 0.5:
                    return {
                        'model': 'GLM-5',
                        'role': '臣',
                        'reason': f'[臣] 中等代码+proven不足，GLM-5补充算力',
                        'proven_coverage': sufficiency['coverage'],
                        'sufficiency': sufficiency,
                        'code_complexity': code_complexity
                    }
                else:
                    return {
                        'model': 'GLM-4.7',
                        'role': '佐',
                        'reason': f'[佐] 中等代码任务，GLM-4.7快速生成',
                        'proven_coverage': sufficiency['coverage'],
                        'sufficiency': sufficiency,
                        'code_complexity': code_complexity
                    }
            else:
                # 佐: 简单代码 → GLM-4.7快速生成
                return {
                    'model': 'GLM-4.7',
                    'role': '佐',
                    'reason': f'[佐] 简单代码任务，GLM-4.7快速原型',
                    'proven_coverage': sufficiency['coverage'],
                    'sufficiency': sufficiency,
                    'code_complexity': code_complexity
                }

        # 3. 臣: proven严重不足 + 复杂推理 → GLM-5
        if sufficiency['need_glm5'] or complexity > 0.7:
            return {
                'model': 'GLM-5',
                'role': '臣',
                'reason': f'[臣] {sufficiency["reason"]}',
                'proven_coverage': sufficiency['coverage'],
                'sufficiency': sufficiency
            }

        # 4. 使: 中等复杂度 → GLM-4.5-Air
        if complexity > 0.3:
            return {
                'model': 'GLM-4.5-Air',
                'role': '使',
                'reason': f'[使] 中等复杂度({complexity:.1f})，GLM-4.5-Air轻量响应',
                'proven_coverage': sufficiency['coverage'],
                'sufficiency': sufficiency
            }

        # 5. 君: 简单对话 → 本地14B
        return {
            'model': 'local_14b',
            'role': '君',
            'reason': '[君] 简单任务，本地模型无幻觉处理',
            'proven_coverage': sufficiency['coverage'],
            'sufficiency': sufficiency
        }

    # ==================== GLM-5 协同推理 ====================
    def execute_glm5_collaborative(self, question, proven_nodes,
                                    thinking, problem_id=None):
        """GLM-5协同推理：本地准备上下文 → GLM-5推理 → 本地验证锚定率
        
        核心：GLM-5必须基于已有真实节点推理，本地14B验证其输出
        """
        t0 = time.time()
        self._broadcast("glm5_collab", "准备真实节点上下文...", "running")
        thinking.add("glm5_prepare", "准备真实节点上下文",
                      f"基于{len(proven_nodes)}个proven节点", "local_14b")

        # 1. 本地14B准备proven节点上下文
        proven_ctx = self._prepare_proven_context(proven_nodes)

        # 2. 构建GLM-5专用prompt
        messages = self._build_glm5_messages(question, proven_ctx)

        # 3. 调用GLM-5
        self._broadcast("glm5_collab",
                         f"调用GLM-5辅助推理(基于{len(proven_nodes)}个真实节点)...",
                         "running")
        thinking.add("glm5_call", "调用GLM-5深度推理",
                      f"问题: {question[:60]}...", "GLM-5")

        glm5_result = agi.glm5_call(messages)
        duration = int((time.time() - t0) * 1000)

        if glm5_result is None:
            self._broadcast("glm5_collab", "GLM-5调用失败", "error")
            thinking.add("glm5_fail", "GLM-5调用失败", "回退到GLM-4.5-Air")
            self.log_step(problem_id, "glm5_call", "GLM-5",
                          "调用失败", False, duration)
            return None

        # 4. 提取文本
        if isinstance(glm5_result, dict):
            result_text = glm5_result.get('raw', json.dumps(
                glm5_result, ensure_ascii=False))
        elif isinstance(glm5_result, list):
            result_text = json.dumps(glm5_result, ensure_ascii=False)
        else:
            result_text = str(glm5_result)

        # 5. 本地14B验证锚定率
        self._broadcast("glm5_collab", "本地验证GLM-5输出锚定率...", "running")
        grounding = agi._proven_grounding_check(result_text, proven_nodes)
        g_ratio = grounding.get('grounding_ratio', 0.0)

        thinking.add("glm5_verify", "验证GLM-5锚定率",
                      f"锚定率: {g_ratio:.0%} "
                      f"({len(grounding.get('grounded_sentences',[]))}句有锚/"
                      f"{len(grounding.get('ungrounded_sentences',[]))}句无锚)",
                      "local_14b")

        self.log_step(problem_id, "glm5_call", "GLM-5",
                      f"锚定率:{g_ratio:.0%} 返回{len(result_text)}字符",
                      True, duration)

        if g_ratio < 0.3:
            # 锚定率太低，GLM-5脱离真实节点，标记警告
            self._broadcast("glm5_collab",
                             f"⚠ GLM-5锚定率仅{g_ratio:.0%}，输出可能含幻觉",
                             "running")
            thinking.add("glm5_warning", "锚定率偏低",
                          f"仅{g_ratio:.0%}，输出需谨慎使用", "local_14b")

        self._broadcast("glm5_collab",
                         f"GLM-5协同完成(锚定率{g_ratio:.0%})", "done")

        return {
            'text': result_text,
            'grounding_ratio': g_ratio,
            'grounding_detail': grounding,
            'model': 'GLM-5',
            'duration_ms': duration
        }

    def _prepare_proven_context(self, proven_nodes):
        """准备proven节点上下文"""
        if not proven_nodes:
            return ""
        lines = []
        for i, n in enumerate(proven_nodes[:15], 1):
            domain = n.get('domain', 'general')
            content = n.get('content', '')[:120]
            sim = n.get('similarity', 0)
            lines.append(f"{i}. [{domain}] {content} (置信度:{sim:.2f})")
        return "\n".join(lines)

    def _build_glm5_messages(self, question, proven_context):
        """构建GLM-5专用prompt：强制基于真实节点推理"""
        system = (
            "你是一个高性能推理引擎，正在协助本地认知引擎解决问题。\n\n"
            "## 已验证的真实节点（proven nodes）\n"
            "以下是经过人类实践验证的真实知识，请基于这些节点进行推理：\n\n"
            f"{proven_context}\n\n"
            "## 重要约束\n"
            "1. 你的推理必须尽可能基于以上真实节点\n"
            "2. 对每个推理结论，标注其依据：\n"
            "   - [基于节点X] = 有真实节点直接支撑\n"
            "   - [推理延伸] = 从真实节点合理推导\n"
            "   - [超出边界] = 超出当前真实节点覆盖范围\n"
            "3. 如果问题完全超出真实节点范围，诚实说明\n"
            "4. 优先提供可实践、可验证的具体方案"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": question}
        ]

    # ==================== 主流程 ====================
    def process(self, question, context_nodes=None, enable_tracking=True):
        """Orchestrator主流程：分析→路由→执行→验证
        
        返回: {
            'text': str,           # 最终回答文本
            'model_used': str,     # 使用的模型
            'routing': dict,       # 路由决策详情
            'thinking': list,      # 思考步骤（供前端折叠展示）
            'problem_id': int,     # 问题追踪ID
            'grounding_ratio': float  # 锚定率
        }
        """
        t0 = time.time()
        thinking = ThinkingTracker()
        context_nodes = context_nodes or []

        # 0. 提取proven节点
        proven_nodes = [n for n in context_nodes
                        if n.get('status') == 'proven']
        all_related = context_nodes

        # 1. 复杂度分析
        self._broadcast("orchestrator", "分析问题复杂度...", "running")
        complexity, task_type, features = self.analyze_complexity(
            question, context_nodes)
        thinking.add("complexity", "复杂度评估",
                      f"评分:{complexity:.1f} 类型:{task_type} "
                      f"proven:{features['proven_count']}/"
                      f"{features['total_related']}")

        # 2. 路由决策
        routing = self.route(question, proven_nodes, complexity, task_type)
        model = routing['model']
        self._broadcast("orchestrator",
                         f"路由决策: {model} ({routing['reason']})",
                         "running")
        thinking.add("routing", f"路由到 {model}",
                      routing['reason'], model)

        # 3. 记录问题追踪
        problem_id = None
        if enable_tracking:
            problem_id = self.track_problem(
                question, complexity, model, routing['reason'])

        # 4. 执行推理
        result_text = ""
        grounding_ratio = routing.get('proven_coverage', 0.0)

        if model == 'fast_path':
            # proven充分，直接返回（交给api_server的fast_path处理）
            result_text = None  # 标记让api_server走自己的fast_path
            thinking.add("fast_path", "proven节点充分",
                          f"覆盖率{routing['proven_coverage']:.0%}，直接回答")

        elif model == 'GLM-5':
            # GLM-5协同模式
            glm5_result = self.execute_glm5_collaborative(
                question, proven_nodes, thinking, problem_id)
            if glm5_result:
                result_text = glm5_result['text']
                grounding_ratio = glm5_result['grounding_ratio']
            else:
                # GLM-5失败，回退到GLM-4.5-Air
                self._broadcast("orchestrator",
                                 "GLM-5不可用，回退GLM-4.5-Air", "running")
                thinking.add("fallback", "回退GLM-4.5-Air",
                              "GLM-5调用失败")
                model = 'GLM-4.5-Air'
                messages = cognitive_core.make_top_down_prompt(
                    question, all_related)
                air_result = agi._zhipu_call_direct(messages, "reasoning")
                if air_result:
                    result_text = (air_result.get('raw', str(air_result))
                                   if isinstance(air_result, dict)
                                   else str(air_result))
                self.log_step(problem_id, "fallback", "GLM-4.5-Air",
                              f"回退调用，返回{len(result_text or '')}字符")

        elif model == 'GLM-4.7':
            # 佐: 快速代码生成(简单/中等任务)
            thinking.add("code_gen", "[佐] 快速代码生成", "", "GLM-4.7")
            messages = [
                {"role": "system",
                 "content": "你是一个高质量代码生成器。输出可直接运行的代码，"
                            "包含完整的import和错误处理。"},
                {"role": "user", "content": question}
            ]
            code_result = agi._zhipu_call_direct(messages, "code_execute")
            if code_result:
                result_text = (code_result.get('raw', str(code_result))
                               if isinstance(code_result, dict)
                               else str(code_result))
            self.log_step(problem_id, "code_gen", "GLM-4.7",
                          f"[佐]返回{len(result_text or '')}字符")

        elif model == 'GLM-4.5-Air':
            # 中等复杂度推理
            thinking.add("reasoning", "中等推理模式", "", "GLM-4.5-Air")
            messages = cognitive_core.make_top_down_prompt(
                question, all_related)
            air_result = agi._zhipu_call_direct(messages, "reasoning")
            if air_result:
                result_text = (air_result.get('raw', str(air_result))
                               if isinstance(air_result, dict)
                               else str(air_result))
            self.log_step(problem_id, "reasoning", "GLM-4.5-Air",
                          f"返回{len(result_text or '')}字符")

        else:
            # 本地14B
            thinking.add("local", "本地模型处理", "", "local_14b")
            messages = cognitive_core.make_top_down_prompt(
                question, all_related)
            local_result = agi.llm_call(messages, _allow_delegate=False)
            if local_result:
                result_text = (local_result.get('raw', str(local_result))
                               if isinstance(local_result, dict)
                               else str(local_result))
            self.log_step(problem_id, "local", "local_14b",
                          f"返回{len(result_text or '')}字符")

        # 5. 更新问题状态
        duration = int((time.time() - t0) * 1000)
        thinking.add("complete", "处理完成",
                      f"耗时{duration}ms 模型:{model} "
                      f"锚定率:{grounding_ratio:.0%}")

        if enable_tracking and problem_id:
            if result_text:
                self.update_problem_status(
                    problem_id, 'decomposed',
                    proven_coverage=grounding_ratio)
            elif model != 'fast_path':
                self.update_problem_status(
                    problem_id, 'unsolvable',
                    unsolvable_reason='所有模型均未能返回有效结果',
                    proven_coverage=grounding_ratio)

        self._broadcast("orchestrator",
                         f"完成: {model} 耗时{duration}ms", "done")

        return {
            'text': result_text,
            'model_used': model,
            'routing': routing,
            'thinking_steps': thinking.to_list(),
            'problem_id': problem_id,
            'grounding_ratio': grounding_ratio,
            'complexity': complexity,
            'task_type': task_type,
            'duration_ms': duration
        }

    # ==================== 无法处理问题分类 ====================
    def classify_unsolvable(self, question, result_text=""):
        """分类无法处理的原因"""
        q_lower = question.lower()

        if any(k in q_lower for k in ['伦理', '违法', '危险', '攻击', '黑客']):
            return 'ethical_constraint'
        if any(k in q_lower for k in ['实验', '测量', '物理验证', '硬件']):
            return 'needs_human_practice'
        if any(k in q_lower for k in ['最新', '实时', '今天', '刚刚']):
            return 'knowledge_gap'
        if not result_text or len(result_text) < 20:
            return 'resource_limitation'
        return 'ambiguous_intent'

    # ==================== 重试机制 ====================
    def retry_problem(self, problem_id):
        """重试一个unsolvable问题"""
        with self.lattice._lock:
            c = self.lattice.conn.cursor()
            c.execute("SELECT * FROM problem_tracking WHERE id=?",
                      (problem_id,))
            row = c.fetchone()
            if not row:
                return None
            problem = dict(row)

        if problem['status'] != 'unsolvable':
            return {"error": "只能重试unsolvable状态的问题"}

        # 更新重试计数
        with self.lattice._lock:
            self.lattice.conn.execute("""
                UPDATE problem_tracking
                SET retry_count = retry_count + 1,
                    status = 'pending'
                WHERE id = ?
            """, (problem_id,))
            self.lattice.conn.commit()

        # 重新处理
        context = self.lattice.find_similar_nodes(
            problem['user_question'], threshold=0.4, limit=5)
        return self.process(problem['user_question'], context)
