#!/usr/bin/env python3
"""
治理层级推演引擎 v2.0 — 王朝循环制
====================================
五阶段王朝循环: 【推演】→【构建】→【反贼】→【分裂】→【一统】
每个循环10轮, 每次推翻旧制, 反贼检测低效, 镇压或分裂, 最终一统。

推演目标:
  用户 = 皇帝 (提出问题的最高决策者)
  推演 = 从人类5000年全球治理经验提炼最高效层级与职级
  映射 = 最优体系映射到代码领域: 本地模型 + GLM-5 协作 + 链式调用 + 算力智能

五阶段循环:
  Phase 1 推演: 六向碰撞 + 搜索全球治理知识
  Phase 2 构建: 生成新层级体系JSON + 验证
  Phase 3 反贼: 检测低效/不合理 → 标记反贼 → 镇压(开源/论文/前沿)
  Phase 4 分裂: 反贼过多 → 群雄割据 → 多架构竞争
  Phase 5 一统: 评估竞争架构 → 胜者一统

作者: Zhao Dylan
"""

import sys
import os
import json
import re
import time
import hashlib
import threading
import traceback
import requests as _requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 路径配置 ====================
SCRIPT_DIR = Path(__file__).parent
AGI_DIR = Path("/Users/administruter/Desktop/AGI_PROJECT")
OUTPUT_DIR = SCRIPT_DIR
CHECKPOINT_PATH = SCRIPT_DIR / ".gov_checkpoint.json"
PREV_HIERARCHY_PATH = SCRIPT_DIR / "上一次层级体系.json"
DYNASTY_LOG_DIR = SCRIPT_DIR / "王朝记录"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DYNASTY_LOG_DIR.mkdir(parents=True, exist_ok=True)

# 导入本地数据库+搜索模块
sys.path.insert(0, str(SCRIPT_DIR))
from gov_db import GovernanceDB, GovernanceSearcher

# 导入技能路由 (Skill Router)
sys.path.insert(0, str(AGI_DIR / "scripts"))
try:
    from pcm_skill_router import route_skills_formatted
    SKILL_ROUTER_AVAILABLE = True
except ImportError:
    SKILL_ROUTER_AVAILABLE = False
    def route_skills_formatted(q, top_k=5): return ""

# ==================== 本地模型配置 ====================
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:14b")


# ==================== 敏感词替换系统 ====================
# 将可能触发内容过滤(1301)的敏感词替换为学术化表述
# 格式: "敏感词" → "安全替代词"
SANITIZE_MAP = {
    # 军事敏感词 → 组织管理学术语 (仅多字词, 避免单字误伤)
    "镇压反贼": "修正异常节点",
    "镇压": "修正",
    "反贼检测": "异常节点检测",
    "反贼探测": "异常节点探测",
    "反贼": "异常节点",
    "叛乱": "系统异常",
    "灭亡": "终止运行",
    "攻击": "压力测试",
    "战争": "竞争博弈",
    "入侵": "外部干扰",
    "屠杀": "大规模淘汰",
    "政变": "架构突变",
    "群雄割据": "多方分区自治",
    "割据": "分区自治",
    "造反": "发起变革",
    "起义": "自下而上变革",
    "暴动": "非预期重组",
    "杀戮": "大规模淘汰",
    "死刑": "强制终止",
    "处死": "强制淘汰",
    # 政治敏感人物 → 代号
    "蒋介石": "历史指挥官K",
    "毛泽东": "历史领导者M",
    "希特勒": "欧洲集权领导者H",
    "斯大林": "苏联领导者S",
    "习近平": "当代领导者X",
    # 政治敏感概念
    "独裁者": "集中决策者",
    "独裁": "集中决策",
    "专制": "单一决策链",
    "极权制": "高度集中制",
    "极权": "高度集中",
    "腐败": "效率衰减",
    "暴政": "过度集权",
    "篡位": "非授权接管",
    "政权更迭": "架构迭代",
    "推翻政权": "重构架构",
    # 敏感历史事件
    "文化大革命": "历史运动CR",
    "大跃进": "历史运动GL",
    "天安门事件": "历史事件TA",
    "六四事件": "历史事件64",
    # 武器/暴力 (仅多字复合词)
    "武器装备": "工具配置",
    "军事武器": "组织工具",
    "弹药": "资源消耗品",
}

# 按长度降序排列, 确保长词优先替换 (避免"蒋介石"被拆成"蒋介"+"石")
_SANITIZE_PAIRS = sorted(SANITIZE_MAP.items(), key=lambda x: len(x[0]), reverse=True)
# 还原时也按替代词长度降序, 长词优先还原
_RESTORE_PAIRS = sorted([(v, k) for k, v in SANITIZE_MAP.items()],
                        key=lambda x: len(x[0]), reverse=True)


def _sanitize_text(text):
    """替换敏感词为安全表述"""
    for sensitive, safe in _SANITIZE_PAIRS:
        text = text.replace(sensitive, safe)
    return text


def _restore_text(text):
    """将安全表述还原为原始词汇 (用于输出展示)"""
    if not text:
        return text
    for safe, original in _RESTORE_PAIRS:
        text = text.replace(safe, original)
    return text


# ==================== 本地模型调用封装 ====================

_call_count = 0
_call_lock = threading.Lock()


def _call_ollama(prompt: str, system: str = "", max_tokens: int = 8192) -> str:
    """调用本地 Ollama 模型 (替代 GLM-5 智谱 API)"""
    global _call_count
    with _call_lock:
        _call_count += 1
        n = _call_count
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_ctx": 16384,
            "num_predict": max_tokens,
        }
    }
    try:
        resp = _requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=300)
        resp.raise_for_status()
        text = resp.json().get("response", "")
        if n <= 3 or n % 10 == 0:
            print(f"      [Ollama #{n}] {len(text)} chars, model={OLLAMA_MODEL}")
        return text
    except Exception as e:
        print(f"      ⚠️ [Ollama #{n}] 调用失败: {e}")
        return ""


def _get_skill_context(topic: str) -> str:
    """通过 Skill Router 获取相关技能上下文, 辅助推演"""
    if not SKILL_ROUTER_AVAILABLE:
        return ""
    try:
        ctx = route_skills_formatted(topic, top_k=5)
        if ctx and "未找到" not in ctx:
            return f"\n## 可用技能参考\n{ctx}\n"
    except Exception:
        pass
    return ""


def call_glm5(prompt, system="", max_tokens=8192):
    """本地模型调用 (接口兼容原 GLM-5, 内部走 Ollama)"""
    # 本地模型无内容过滤, 无需 sanitize, 但保持接口一致
    return _call_ollama(prompt, system=system, max_tokens=max_tokens)


def call_glm5_emperor(prompt, extra_system=""):
    """皇帝视角推演: 最大能力、零回避、必须推翻旧制"""
    system = f"""你现在是一位穿越5000年、遍历全球所有文明的治理顾问。要求:
1. 零回避: 不回避任何失败案例, 不美化任何制度, 直言弊端
2. 全量化: 所有层级必须有人数/比例/管辖幅度的数值
3. 推翻精神: 每次推演必须质疑上一次的结论, 给出推翻理由
4. 映射代码: 最终必须映射到AI协作架构 (模型=将领, 函数=士兵, API=驿站)
5. 引用史实: 每个结论必须引用至少1个历史案例 (国家+年代+结果)
6. 反贼意识: 主动发现体系中的低效/漏洞/瓶颈, 标记为"反贼"
{extra_system}"""
    return call_glm5(prompt, system=system, max_tokens=8192)


# ==================== 系统提示 ====================
SYSTEM_PROMPT = """你是治理层级推演专家, 精通:
- 中国: 周礼分封→秦郡县→唐三省六部→明废丞相→清军机处→PLA军改
- 罗马: 共和制→帝制→行省制→军团编制(军团→大队→百人队→十人队)
- 蒙古: 十进制(十户→百户→千户→万户→汗), 怯薛军
- 拿破仑: 军→军团→师→旅→团→营→连→排→班
- 普鲁士/德国: 参谋制度, 任务式指挥(Auftragstaktik)
- 美军: 联合作战体系, 模块化旅战斗队(BCT)
- 日本: 藩→县, 武士→町奉行, 丰田精益管理
- 英国: 议会制+文官制度, 枢密院
- 科技公司: Google扁平化, Amazon两个披萨团队, Valve无层级, 字节跳动OKR
- 开源社区: Linux BDFL, Apache基金会, Rust RFC治理
- AI Agent: LangGraph多Agent编排, CrewAI层级, AutoGen对话, Supervisor-Worker模式

核心原则:
- 管辖幅度(span of control): 每级管3-10人, 超过则效率骤降
- 信息损耗: 每多一层级, 信息保真度下降约30%
- 决策延迟: 层级越多, 响应越慢; 但太少则负载过重
- 权力制衡: 无监督的权力必然腐败 (阿克顿定律)
- 适应性: 环境变化快时需扁平化, 稳定时可纵深化
- 反贼原理: 任何体系都有内生矛盾, 低效之处必然产生"反贼"(变革力量)"""


# ==================== 反贼类型定义 ====================
REBEL_TYPES = {
    "bottleneck": {"label": "瓶颈反贼", "desc": "信息/决策瓶颈, 单点过载"},
    "redundancy": {"label": "冗余反贼", "desc": "层级重叠, 职能重复, 资源浪费"},
    "latency": {"label": "延迟反贼", "desc": "决策链路过长, 响应迟缓"},
    "single_point": {"label": "单点故障反贼", "desc": "关键节点无备份, 一崩全崩"},
    "power_vacuum": {"label": "权力真空反贼", "desc": "制衡缺失, 无监督区域"},
    "info_loss": {"label": "信息衰减反贼", "desc": "层级过多导致信息严重失真"},
    "rigidity": {"label": "僵化反贼", "desc": "体系无法适应变化, 缺乏弹性"},
    "overload": {"label": "过载反贼", "desc": "某层级管辖幅度过大, 超出有效管理范围"},
    "unmapped": {"label": "映射缺失反贼", "desc": "层级无法映射到代码架构, 纯理论无法落地"},
    "historical_trap": {"label": "历史陷阱反贼", "desc": "重复历史上已证明失败的模式"},
}

SEVERITY_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0}


# ==================== 节点提取模式 ====================
NODE_PATTERNS = [
    (r"(?:层级|level|tier|级别)[:\s：]*([^\n]{10,200})", "hierarchy_level", 0.80),
    (r"(?:职级|rank|品级|秩级)[:\s：]*([^\n]{10,200})", "rank_definition", 0.80),
    (r"(?:管辖幅度|span of control|管辖|下辖)[:\s：]*([^\n]{10,200})", "span_of_control", 0.85),
    (r"(?:管理方法|管理模式|management)[:\s：]*([^\n]{10,200})", "management_method", 0.70),
    (r"(?:军|师|旅|团|营|连|排|班|军团|大队|百人队|万户|千户)[^\n]{5,150}", "military_unit", 0.85),
    (r"(?:三公|九卿|六部|三省|内阁|军机处|枢密院|议会|总统|首相)[^\n]{5,150}", "gov_institution", 0.85),
    (r"(?:失败|灭亡|衰落|崩溃|冗官|腐败|割据)[:\s：]*([^\n]{10,200})", "failure_case", 0.75),
    (r"(?:成功|统一|崛起|高效|精简)[:\s：]*([^\n]{10,200})", "success_case", 0.75),
    (r"(?:反贼|叛乱|低效|瓶颈|冗余|单点故障)[:\s：]*([^\n]{10,200})", "rebel_indicator", 0.70),
    (r"(?:镇压|优化|改进|重构|替代方案)[:\s：]*([^\n]{10,200})", "suppression_method", 0.70),
    (r"(?:原则|定律|法则|规律)[:\s：]*([^\n]{10,200})", "principle", 0.70),
    (r"(?:映射|对应|类比|相当于)[:\s：]*([^\n]{10,200})", "code_mapping", 0.65),
    (r"(?:推翻|否定|反对|质疑|缺陷)[:\s：]*([^\n]{10,200})", "overthrow", 0.60),
    (r"(?:Agent|LLM|模型|函数|API|Orchestrator|Supervisor)[^\n]{5,150}", "ai_architecture", 0.80),
    (r"(?:LangGraph|CrewAI|AutoGen|LangChain|OpenAI|GLM)[^\n]{5,150}", "ai_framework", 0.80),
]


# ==================== 六向碰撞方向 ====================
SIX_DIRECTIONS = [
    {"name": "historical_evolution", "label": "历史演进",
     "topic": "从先秦→秦汉→唐宋→明清→近现代→AI时代, 每次变革的原因和效果"},
    {"name": "east_west_compare", "label": "东西方对比",
     "topic": "中国中央集权 vs 罗马行省 vs 蒙古十进制 vs 欧洲封建 vs 美国联邦 vs 科技公司"},
    {"name": "military_civilian", "label": "军政对比",
     "topic": "军队编制(军师旅团营连排班) vs 文官体制(省市县乡) vs AI Agent层级"},
    {"name": "success_failure", "label": "成败归因",
     "topic": "成功(秦统一/PLA军改/Google/Linux) vs 失败(王莽/拜占庭冗官/诺基亚僵化)"},
    {"name": "flat_vs_deep", "label": "扁平vs纵深",
     "topic": "Valve零层级 vs Amazon两个披萨 vs PLA合成旅 vs 清八旗, 何时扁平/何时纵深?"},
    {"name": "overthrow_rebuild", "label": "推翻重建",
     "topic": "质疑当前体系, 找出致命缺陷, 提出替代方案。每次改革都是推翻旧制"},
]


# ==================== 王朝循环推演引擎 ====================
class DynastyCycleEngine:
    """
    王朝循环推演引擎 v2.0
    五阶段循环: 推演→构建→反贼→分裂→一统
    每轮10次迭代
    """

    SPLIT_THRESHOLD = 5       # 活跃反贼数 >= 此值 → 触发分裂
    MAX_SUPPRESSION = 3       # 每个反贼最多镇压尝试次数
    MAX_FACTIONS = 4          # 分裂时最多产生的派系数
    ROUNDS_PER_CYCLE = 10     # 每个循环的轮数

    def __init__(self):
        self.db = GovernanceDB()
        self.session_id = None
        self._global_seen = set()
        self._global_seen_lock = threading.Lock()
        self._round_new_counts = []

    # ==================== 工具方法 ====================
    @staticmethod
    def _fingerprint(content):
        cleaned = re.sub(r'[\s\*\#\-\|：:。，,、\(\)\[\]（）【】""\'\"\\/$]', '', content)
        if len(cleaned) < 12:
            return hashlib.md5(cleaned.encode()).hexdigest()
        ngrams = set(cleaned[i:i+4] for i in range(len(cleaned) - 3))
        return hashlib.md5("".join(sorted(ngrams)).encode()).hexdigest()

    def _is_dup(self, content, ntype):
        fp = self._fingerprint(content)
        key = f"{ntype}:{fp}"
        with self._global_seen_lock:
            if key in self._global_seen:
                return True
            self._global_seen.add(key)
            return False

    def extract_nodes(self, text, source, round_num=0, phase=""):
        """从推演文本中提取治理节点"""
        nodes = []
        node_ids = []
        seen_local = set()
        for pat, ntype, conf in NODE_PATTERNS:
            for m in re.findall(pat, text)[:8]:
                content = m.strip() if isinstance(m, str) else str(m).strip()
                if len(content) < 10 or content in seen_local:
                    continue
                seen_local.add(content)
                cleaned = re.sub(r'[\s\*\#\-\|]', '', content)
                if len(cleaned) < 8:
                    continue
                if self._is_dup(content, ntype):
                    continue
                nid = self.db.save_node(self.session_id, content, ntype, source,
                                        confidence=conf, collision_round=round_num, phase=phase)
                nodes.append({"content": content, "type": ntype, "confidence": conf, "id": nid})
                node_ids.append(nid)
        # 保存同轮同源节点的共现关系
        for i, nid_a in enumerate(node_ids):
            for nid_b in node_ids[i+1:i+4]:
                self.db.save_relation(self.session_id, nid_a, nid_b,
                                      "co_occurrence", f"{source} round:{round_num}", round_num)
        return nodes

    @staticmethod
    def _extract_json(text):
        """从文本中提取JSON对象 — 支持代码块包裹和裸JSON"""
        # Strategy 1: ```json {...} ```
        json_match = re.search(r'```json\s*(\{.+?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        # Strategy 2: 找最大的 {...} 块 (支持深层嵌套)
        # 用栈匹配法找完整的JSON对象
        candidates = []
        i = 0
        while i < len(text):
            if text[i] == '{':
                depth = 0
                start = i
                in_str = False
                escape = False
                for j in range(i, len(text)):
                    c = text[j]
                    if escape:
                        escape = False
                        continue
                    if c == '\\':
                        escape = True
                        continue
                    if c == '"' and not escape:
                        in_str = not in_str
                        continue
                    if in_str:
                        continue
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            candidates.append(text[start:j+1])
                            i = j
                            break
            i += 1
        # 按长度降序尝试 (最大的JSON块最可能是完整体系)
        candidates.sort(key=len, reverse=True)
        for cand in candidates:
            try:
                obj = json.loads(cand)
                if isinstance(obj, dict) and ("层级" in obj or "体系名称" in obj or "levels" in obj
                                              or "总层级数" in obj or "制衡机制" in obj):
                    return obj
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def _extract_score(text):
        score_match = re.search(r'(?:总分|评分|得分|score)[:\s：]*(\d{1,3})', text, re.IGNORECASE)
        if score_match:
            return min(int(score_match.group(1)), 100)
        return 50

    @staticmethod
    def _extract_list(text, pattern):
        """从文本中提取列表项"""
        items = []
        for m in re.findall(pattern, text):
            item = m.strip() if isinstance(m, str) else str(m).strip()
            if len(item) > 5:
                items.append(item)
        return items

    # ==================== 断点续推 ====================
    def _save_checkpoint(self, data):
        data["session_id"] = self.session_id
        data["saved_at"] = datetime.now().isoformat()
        CHECKPOINT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def load_checkpoint():
        if CHECKPOINT_PATH.exists():
            try:
                data = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
                if data.get("session_id"):
                    return data
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    @staticmethod
    def delete_checkpoint():
        if CHECKPOINT_PATH.exists():
            CHECKPOINT_PATH.unlink()

    def _restore_session(self, checkpoint):
        self.session_id = checkpoint["session_id"]
        existing_nodes = self.db.get_all_nodes(self.session_id)
        for n in existing_nodes:
            content, ntype = n.get("content", ""), n.get("node_type", "")
            if content and ntype:
                fp = self._fingerprint(content)
                self._global_seen.add(f"{ntype}:{fp}")
        print(f"  🔄 恢复session: {self.session_id} ({len(existing_nodes)}个已有节点)")

    def _load_prev_hierarchy(self):
        if PREV_HIERARCHY_PATH.exists():
            try:
                return json.loads(PREV_HIERARCHY_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def _save_hierarchy_file(self, hierarchy):
        PREV_HIERARCHY_PATH.write_text(json.dumps(hierarchy, ensure_ascii=False, indent=2), encoding="utf-8")

    # ==================== Phase 1: 推演 ====================
    def phase1_reasoning(self, search_ctx, prev_hierarchy, round_num):
        """六向碰撞推演"""
        prev_text = json.dumps(prev_hierarchy, ensure_ascii=False, indent=2)[:3000] if prev_hierarchy else ""
        direction_results = {}

        # 获取技能上下文 (仅查一次, 所有方向共享)
        skill_ctx = _get_skill_context(f"治理体系 编码架构 链式调用 技能协调 知识图谱")

        def _run_dir(d):
            prompt = f"""基于以下搜索结果, 进行【{d['label']}】方向推演。
{search_ctx[:4000]}
{skill_ctx}
{"## 上一次体系 (需质疑/推翻)" + chr(10) + prev_text if prev_text else ""}

推演方向: {d['topic']}

要求:
1. 列出该方向下发现的所有层级/职级/编制, 标注管辖幅度/人数/历史来源
2. 给出核心结论 (支持或反对当前体系)
3. 主动发现"反贼": 该方向中哪些元素暴露了当前体系的低效/漏洞?
4. 映射到代码AI协作: 每个层级对应什么角色 (模型/Agent/函数/API), 可参考上方的可用技能
5. 如果是推翻重建方向, 必须给出推翻理由和替代方案

格式: markdown, 关键数据用**加粗**, 反贼用🔴标记"""
            result = call_glm5(prompt, system=SYSTEM_PROMPT, max_tokens=8192)
            self.db.save_log(self.session_id, round_num, d["name"], "result", result or "", "phase1")
            if result:
                self.extract_nodes(result, f"dir_{d['name']}", round_num, "phase1")
            return result

        # 本地模型串行执行 (Ollama 单并发, 避免争抢GPU)
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = {executor.submit(_run_dir, d): d["name"] for d in SIX_DIRECTIONS}
            for future in as_completed(futures):
                dname = futures[future]
                try:
                    direction_results[dname] = future.result()
                    print(f"    ✅ {dname}")
                except Exception as e:
                    print(f"    ⚠️ {dname}: {e}")
                    direction_results[dname] = None

        return direction_results

    # ==================== Phase 2: 构建 ====================
    def phase2_build(self, direction_results, prev_hierarchy, round_num):
        """碰撞综合 → 生成新层级体系"""
        parts = []
        for d in SIX_DIRECTIONS:
            res = direction_results.get(d["name"], "")
            if res:
                parts.append(f"### {d['label']}结论\n{res[:2000]}\n")
        collision_input = "\n".join(parts)

        prev_section = ""
        if prev_hierarchy:
            prev_section = f"""
## 上一次的层级体系 (Round {round_num-1})
{json.dumps(prev_hierarchy, ensure_ascii=False, indent=2)[:2000]}

⚠️ 你必须质疑上述体系, 找出至少3个致命缺陷, 然后重建。"""

        prompt = f"""综合六个方向的推演结果进行碰撞, 产生新的层级体系。

{collision_input[:12000]}
{prev_section}

## 任务

### 1. 碰撞分析
对六个方向的矛盾点进行分析。

### 2. 推翻旧制
列出上一次体系的致命缺陷和推翻理由。

### 3. 新的最优层级体系
用JSON格式输出:
```json
{{
  "体系名称": "...",
  "总层级数": N,
  "推翻理由": "为什么比上一次更好",
  "层级": [
    {{
      "level": 0, "名称": "皇帝/决策者",
      "代码映射": "用户(你), 提出问题",
      "管辖幅度": "3-5", "职责": "...", "历史案例": "...", "人数": "1"
    }}
  ],
  "制衡机制": ["监察", "轮换"],
  "信息通路": "...",
  "代码架构映射": {{"皇帝": "User(你)"}}
}}
```

### 4. 评分 (0-100)
维度: 效率/制衡/适应性/信息保真度/代码可映射性

### 5. 潜在反贼预测
预测新体系中可能出现的"反贼"(低效/漏洞), 每个反贼标注:
- 🔴 反贼名称 | 类型 | 严重程度(critical/high/medium/low) | 所在层级 | 描述"""

        result = call_glm5_emperor(prompt)
        self.db.save_log(self.session_id, round_num, "collision", "result", result or "", "phase2")
        if result:
            self.extract_nodes(result, f"collision_r{round_num}", round_num, "phase2")

        hierarchy = self._extract_json(result) if result else None
        score = self._extract_score(result) if result else 0

        if hierarchy:
            self.db.save_hierarchy(self.session_id, round_num, hierarchy,
                                   hierarchy.get("推翻理由", ""), score)
        return result, hierarchy, score

    # ==================== Phase 3: 反贼 ====================
    def phase3_rebels(self, hierarchy, collision_text, round_num):
        """检测反贼 + 镇压"""
        if not hierarchy:
            print("    ⚠️ 无有效体系, 跳过反贼检测")
            return []

        # Step 3a: 检测反贼
        rebels = self._detect_rebels(hierarchy, collision_text, round_num)
        if not rebels:
            print("    ✅ 未检测到反贼, 体系稳固")
            return []

        print(f"    🔴 检测到 {len(rebels)} 个反贼!")
        for r in rebels:
            print(f"      [{r['severity']}] {r['rebel_name']}: {r['description'][:60]}")

        # Step 3b: 逐个镇压
        for rebel in rebels:
            self._suppress_rebel(rebel, hierarchy, round_num)

        # 返回当前活跃反贼
        return self.db.get_active_rebels(self.session_id)

    def _detect_rebels(self, hierarchy, collision_text, round_num):
        """用GLM-5检测体系中的反贼"""
        hier_text = json.dumps(hierarchy, ensure_ascii=False, indent=2)

        prompt = f"""你是反贼探测器。分析以下治理层级体系, 找出所有低效/不合理/有漏洞的地方。
每个问题 = 一个"反贼"。

## 当前层级体系
{hier_text[:4000]}

## 碰撞推演中发现的问题线索
{(collision_text or '')[:3000]}

## 反贼类型 (从以下类型中选择)
{json.dumps({k: v['desc'] for k, v in REBEL_TYPES.items()}, ensure_ascii=False, indent=2)}

## 要求
找出尽可能多的反贼。参考:
- 开源项目最佳实践 (LangGraph/CrewAI/AutoGen的Agent编排模式)
- 学术论文 (管辖幅度/信息衰减/组织效率)
- 历史失败案例 (为什么这个设计会重蹈覆辙?)
- 代码可行性 (这个层级能否真正映射到代码?)

每个反贼用JSON格式:
```json
[
  {{
    "rebel_name": "反贼名称",
    "rebel_type": "bottleneck|redundancy|latency|single_point|power_vacuum|info_loss|rigidity|overload|unmapped|historical_trap",
    "severity": "critical|high|medium|low",
    "target_level": 0,
    "description": "详细描述问题和历史依据"
  }}
]
```"""

        result = call_glm5(prompt, system="你是组织效率分析专家, 擅长发现体系漏洞。零回避, 必须直言。", max_tokens=4096)
        self.db.save_log(self.session_id, round_num, "rebel_detect", "result", result or "", "phase3")

        if not result:
            return []

        # 提取反贼JSON — 多策略
        rebels = []
        rebel_list = None

        # Strategy 1: ```json [...] ```
        json_match = re.search(r'```json\s*(\[.+?\])\s*```', result, re.DOTALL)
        if json_match:
            try:
                rebel_list = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 2: 裸JSON数组 (GLM-5常返回不带代码块的JSON)
        if not rebel_list:
            # 找第一个 [ 到最后一个 ] 的范围
            arr_start = result.find('[')
            arr_end = result.rfind(']')
            if arr_start >= 0 and arr_end > arr_start:
                try:
                    rebel_list = json.loads(result[arr_start:arr_end+1])
                except json.JSONDecodeError:
                    pass

        # Strategy 3: 逐个提取 {...} 对象
        if not rebel_list:
            rebel_list = []
            for m in re.finditer(r'\{[^{}]*"rebel_name"[^{}]*\}', result):
                try:
                    obj = json.loads(m.group())
                    rebel_list.append(obj)
                except json.JSONDecodeError:
                    pass

        if rebel_list:
            for r in rebel_list:
                if isinstance(r, dict) and r.get("rebel_name"):
                    rid = self.db.create_rebel(
                        self.session_id,
                        r.get("rebel_name", "未命名"),
                        r.get("rebel_type", "bottleneck"),
                        r.get("description", ""),
                        r.get("severity", "medium"),
                        r.get("target_level", -1),
                        round_num
                    )
                    r["id"] = rid
                    rebels.append(r)

        # 如果JSON提取全部失败, 用正则兜底
        if not rebels:
            for m in re.finditer(r'🔴\s*(.+?)[\|｜](.+?)[\|｜](.+?)[\|｜].*?[\|｜]\s*(.+)', result):
                name = m.group(1).strip()
                rtype = m.group(2).strip().lower()
                sev = m.group(3).strip().lower()
                desc = m.group(4).strip()
                if rtype not in REBEL_TYPES:
                    rtype = "bottleneck"
                if sev not in SEVERITY_ORDER:
                    sev = "medium"
                rid = self.db.create_rebel(self.session_id, name, rtype, desc, sev, -1, round_num)
                rebels.append({"id": rid, "rebel_name": name, "rebel_type": rtype,
                               "severity": sev, "description": desc})

        self.extract_nodes(result, "rebel_detection", round_num, "phase3")
        return rebels

    def _suppress_rebel(self, rebel, hierarchy, round_num):
        """镇压单个反贼: 用开源最佳实践+论文+前沿数据提供解决方案"""
        rebel_id = rebel.get("id")
        rebel_name = rebel.get("rebel_name", "?")
        rebel_desc = rebel.get("description", "")
        hier_text = json.dumps(hierarchy, ensure_ascii=False, indent=2)[:2000]

        print(f"      ⚔️ 镇压反贼: {rebel_name}...")

        prompt = f"""你是镇压反贼的将军。一个"反贼"(体系漏洞)被发现, 你必须提供镇压方案。

## 反贼信息
- 名称: {rebel_name}
- 类型: {rebel.get('rebel_type', '?')} ({REBEL_TYPES.get(rebel.get('rebel_type',''), {}).get('desc','')})
- 严重程度: {rebel.get('severity', '?')}
- 描述: {rebel_desc}

## 当前体系
{hier_text}

## 镇压要求
1. 引用开源项目最佳实践 (如LangGraph的Supervisor模式, CrewAI的层级Agent, AutoGen的对话模式)
2. 引用学术论文或管理理论 (如span of control研究, 组织效率论文)
3. 引用历史案例 (哪个文明/组织成功解决过类似问题?)
4. 给出具体的修改方案: 修改哪个层级? 增加/删除什么? 如何映射到代码?

## 输出格式
```json
{{
  "镇压成功": true或false,
  "方案名称": "...",
  "修改层级": [0, 1, 2],
  "具体修改": "详细描述",
  "引用依据": ["开源: ...", "论文: ...", "历史: ..."],
  "新体系片段": {{}}
}}
```

如果你认为这个反贼无法镇压(是体系的根本性矛盾), 设置"镇压成功"为false并解释原因。"""

        result = call_glm5(prompt, system="你是组织变革专家, 精通开源治理、军事改革、企业重组。", max_tokens=4096)
        self.db.save_log(self.session_id, round_num, f"suppress_{rebel_name[:20]}", "result", result or "", "phase3")

        if not result:
            self.db.update_rebel_suppression(rebel_id, {"attempt": 1, "result": "no_response"}, "active")
            return False

        # 解析镇压结果
        suppression = self._extract_json(result)
        success = False
        if suppression:
            success = suppression.get("镇压成功", False)
        else:
            success = "镇压成功" in result and ("true" in result.lower() or "是" in result)

        attempt_log = {
            "attempt": 1,
            "result": "success" if success else "failed",
            "response": (result or "")[:2000],
            "timestamp": datetime.now().isoformat()
        }

        if success:
            self.db.update_rebel_suppression(rebel_id, attempt_log, "suppressed")
            print(f"      ✅ 镇压成功: {rebel_name}")
            self.extract_nodes(result, f"suppress_{rebel_name[:20]}", round_num, "phase3")
        else:
            # 检查是否还有镇压机会
            rebel_row = self.db.conn.execute("SELECT suppression_count FROM gov_rebels WHERE id=?",
                                              (rebel_id,)).fetchone()
            count = (rebel_row["suppression_count"] if rebel_row else 0) + 1
            if count >= self.MAX_SUPPRESSION:
                self.db.update_rebel_suppression(rebel_id, attempt_log, "unsuppressable")
                print(f"      ❌ 无法镇压 (已尝试{count}次): {rebel_name}")
            else:
                self.db.update_rebel_suppression(rebel_id, attempt_log, "active")
                print(f"      🔄 镇压失败 ({count}/{self.MAX_SUPPRESSION}): {rebel_name}")

        return success

    # ==================== Phase 4: 分裂 ====================
    def phase4_split(self, hierarchy, active_rebels, round_num):
        """当反贼过多 → 群雄割据, 产生多个竞争架构"""
        if len(active_rebels) < self.SPLIT_THRESHOLD:
            print(f"    ℹ️ 活跃反贼({len(active_rebels)})<阈值({self.SPLIT_THRESHOLD}), 无需分裂")
            return None

        print(f"    ⚔️ 群雄割据! 活跃反贼{len(active_rebels)}个, 触发分裂!")
        hier_text = json.dumps(hierarchy, ensure_ascii=False, indent=2)[:3000]
        rebels_text = "\n".join([f"- [{r['severity']}] {r['rebel_name']}: {r['description'][:80]}"
                                 for r in active_rebels])

        prompt = f"""当前王朝体系面临太多无法镇压的反贼, 必须分裂为群雄割据!

## 当前体系
{hier_text}

## 无法镇压的反贼 ({len(active_rebels)}个)
{rebels_text}

## 任务: 产生{self.MAX_FACTIONS}个竞争派系

每个派系代表一种不同的治理理念, 必须针对性地解决部分反贼:

要求:
1. 每个派系有独特的治理理念 (如: 极致扁平派/军事纵深派/联邦自治派/AI原生派)
2. 每个派系用JSON格式输出完整层级体系 (格式同前)
3. 每个派系标注: 能解决哪些反贼? 会引入哪些新反贼?
4. 每个派系映射到不同的代码架构模式

输出格式:
```json
[
  {{
    "faction_id": "flat_faction",
    "faction_name": "极致扁平派",
    "理念": "...",
    "解决的反贼": ["反贼1", "反贼2"],
    "新增的反贼": ["新反贼1"],
    "hierarchy": {{完整层级体系JSON}},
    "代码架构": "描述"
  }}
]
```"""

        result = call_glm5_emperor(prompt)
        self.db.save_log(self.session_id, round_num, "split", "result", result or "", "phase4")

        if not result:
            return None

        # 提取派系
        factions = []
        json_match = re.search(r'```json\s*(\[.+?\])\s*```', result, re.DOTALL)
        if json_match:
            try:
                faction_list = json.loads(json_match.group(1))
                for f in faction_list[:self.MAX_FACTIONS]:
                    if isinstance(f, dict) and f.get("faction_id"):
                        fid = f["faction_id"]
                        fname = f.get("faction_name", fid)
                        fhier = f.get("hierarchy", {})
                        self.db.create_faction(self.session_id, fid, fname, fhier, "split")
                        factions.append(f)
                        print(f"      🏴 派系: {fname}")
            except json.JSONDecodeError:
                pass

        self.extract_nodes(result, "faction_split", round_num, "phase4")

        if not factions:
            print("    ⚠️ 未能产生有效派系")
        return factions

    # ==================== Phase 5: 一统 ====================
    def phase5_unify(self, factions, hierarchy, round_num):
        """评估所有竞争架构, 胜者一统天下"""
        if not factions:
            print("    ℹ️ 无竞争派系, 当前体系维持统治")
            return hierarchy

        # 对每个派系进行反贼检测
        faction_scores = {}
        for f in factions:
            fid = f.get("faction_id", "?")
            fhier = f.get("hierarchy", {})
            fname = f.get("faction_name", fid)

            print(f"    🔍 评估派系: {fname}...")

            # 用GLM-5评估
            prompt = f"""评估以下治理派系, 从5个维度打分 (0-100):

## 派系: {fname}
理念: {f.get('理念', '?')}
层级体系: {json.dumps(fhier, ensure_ascii=False)[:2000]}
声称解决的反贼: {f.get('解决的反贼', [])}
可能新增的反贼: {f.get('新增的反贼', [])}

## 评分维度
1. 效率 (决策速度, 资源利用)
2. 制衡 (防腐败, 错误检测)
3. 适应性 (应变能力, 弹性)
4. 信息保真度 (底层信息到顶层的准确度)
5. 代码可映射性 (能否真正映射到本地模型+GLM-5协作架构)

输出:
- 总分: X/100
- 各维度得分
- 致命弱点
- 能否真正消灭反贼的评估"""

            result = call_glm5(prompt, system=SYSTEM_PROMPT, max_tokens=2048)
            score = self._extract_score(result) if result else 30
            rebel_count = len(f.get("新增的反贼", []))
            faction_scores[fid] = {"score": score, "rebel_count": rebel_count, "name": fname}
            self.db.update_faction_score(self.session_id, fid, score, rebel_count)
            print(f"      📊 {fname}: {score}分, 预期新反贼{rebel_count}个")

        # 也评估原有体系
        if hierarchy:
            orig_rebels = len(self.db.get_active_rebels(self.session_id))
            orig_score = self._extract_score(json.dumps(hierarchy, ensure_ascii=False)) if hierarchy else 40
            faction_scores["original"] = {"score": orig_score, "rebel_count": orig_rebels, "name": "原体系"}

        # 选出胜者: 得分最高 * (1 - 0.1*新反贼数)
        best_fid, best_info = None, {"score": -1}
        for fid, info in faction_scores.items():
            effective = info["score"] * (1 - 0.1 * min(info["rebel_count"], 5))
            info["effective_score"] = effective
            if effective > best_info.get("effective_score", -1):
                best_fid = fid
                best_info = info

        print(f"\n    👑 一统天下: {best_info.get('name', '?')} (有效得分: {best_info.get('effective_score', 0):.1f})")

        if best_fid and best_fid != "original":
            self.db.crown_faction(self.session_id, best_fid)
            # 找到胜出派系的层级体系
            for f in factions:
                if f.get("faction_id") == best_fid:
                    return f.get("hierarchy", hierarchy)

        return hierarchy

    # ==================== 验证阶段 ====================
    def _verify_hierarchy(self, hierarchy, round_num):
        """验证层级体系的完整性和可行性"""
        if not hierarchy:
            return False, "无有效体系"

        issues = []
        if "层级" not in hierarchy:
            issues.append("缺少'层级'字段")
        elif not isinstance(hierarchy["层级"], list):
            issues.append("'层级'不是列表")
        elif len(hierarchy["层级"]) < 2:
            issues.append("层级数少于2, 过于简单")

        if "制衡机制" not in hierarchy:
            issues.append("缺少制衡机制")
        if "代码架构映射" not in hierarchy:
            issues.append("缺少代码架构映射")

        # 检查每个层级的完整性
        for lv in hierarchy.get("层级", []):
            if not lv.get("名称"):
                issues.append(f"Level {lv.get('level','?')} 缺少名称")
            if not lv.get("代码映射"):
                issues.append(f"Level {lv.get('level','?')} 缺少代码映射")

        if issues:
            return False, "; ".join(issues)
        return True, "验证通过"

    # ==================== 主循环 ====================
    def run(self, num_cycles=1, rounds_per_cycle=None, _checkpoint=None):
        """运行王朝循环: 每个循环 = 推演→构建→反贼→分裂→一统, 共10轮"""
        if rounds_per_cycle is None:
            rounds_per_cycle = self.ROUNDS_PER_CYCLE

        resume_cycle = 0
        resume_round = 0
        resume_phase = 0

        if _checkpoint:
            self._restore_session(_checkpoint)
            resume_cycle = _checkpoint.get("completed_cycle", 0)
            resume_round = _checkpoint.get("completed_round", 0)
            resume_phase = _checkpoint.get("completed_phase", 0)
            num_cycles = _checkpoint.get("num_cycles", num_cycles)
            rounds_per_cycle = _checkpoint.get("rounds_per_cycle", rounds_per_cycle)
        else:
            self.session_id = self.db.create_session()

        # Ollama 连接检测
        try:
            _resp = _requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            _models = [m["name"] for m in _resp.json().get("models", [])]
            _model_ok = any(OLLAMA_MODEL in m for m in _models)
        except Exception:
            _models, _model_ok = [], False
        if not _model_ok:
            print(f"  ❌ Ollama 未运行或模型 {OLLAMA_MODEL} 不可用! 可用模型: {_models}")
            print(f"     请先运行: ollama pull {OLLAMA_MODEL}")
            sys.exit(1)

        skill_status = "✅ 已加载" if SKILL_ROUTER_AVAILABLE else "❌ 未加载"

        print(f"""
╔═══════════════════════════════════════════════════════════════════════╗
║  治理层级推演引擎 v2.1 — 本地模型 + 王朝循环制                        ║
║  五阶段: 【推演】→【构建】→【反贼】→【分裂】→【一统】                 ║
║  模型: {OLLAMA_MODEL:<20s} | Skill Router: {skill_status}              ║
║  循环: {num_cycles} | 每循环: {rounds_per_cycle}轮 | 分裂阈值: {self.SPLIT_THRESHOLD}反贼                      ║
║  Session: {self.session_id:<57s}  ║
╚═══════════════════════════════════════════════════════════════════════╝
""")

        # Phase 0: 搜索
        print("=" * 70)
        print("🔍 Phase 0: 全球治理体系搜索")
        print("=" * 70)
        searcher = GovernanceSearcher()
        searcher.run_all()
        search_ctx = searcher.build_context()

        # 加载上一次体系
        prev_hierarchy = self._load_prev_hierarchy()
        if prev_hierarchy:
            print(f"\n📜 上一次体系: {prev_hierarchy.get('体系名称', '未命名')} — 本次将推翻它!")

        all_dynasty_records = []

        for cycle in range(resume_cycle, num_cycles):
            dynasty_num = cycle + 1
            print(f"\n{'#' * 70}")
            print(f"# 🏛️ 第 {dynasty_num} 个王朝循环")
            print(f"{'#' * 70}")

            current_hierarchy = prev_hierarchy
            best_hierarchy = None
            best_score = 0
            all_collisions = []
            cycle_factions = None

            start_round = (resume_round + 1) if cycle == resume_cycle and resume_round > 0 else 1

            for rnd in range(start_round, rounds_per_cycle + 1):
                pre_count = len(self._global_seen)
                start_phase = resume_phase if (cycle == resume_cycle and rnd == start_round) else 0

                print(f"\n{'=' * 70}")
                print(f"🔄 王朝{dynasty_num} — Round {rnd}/{rounds_per_cycle}")
                print("=" * 70)

                # ======== Phase 1: 推演 ========
                if start_phase < 1:
                    print(f"\n  📐 Phase 1: 六向碰撞推演 (Round {rnd})")
                    direction_results = self.phase1_reasoning(search_ctx, current_hierarchy, rnd)
                    self._save_checkpoint({"completed_cycle": cycle, "completed_round": rnd,
                                           "completed_phase": 1, "num_cycles": num_cycles,
                                           "rounds_per_cycle": rounds_per_cycle})
                else:
                    direction_results = {}
                    print("  ⏩ Phase 1 已完成")

                # ======== Phase 2: 构建 ========
                if start_phase < 2:
                    print(f"\n  🏗️ Phase 2: 碰撞构建新体系")
                    collision_text, new_hierarchy, score = self.phase2_build(
                        direction_results, current_hierarchy, rnd)
                    if collision_text:
                        all_collisions.append(collision_text)

                    if new_hierarchy:
                        valid, msg = self._verify_hierarchy(new_hierarchy, rnd)
                        if valid:
                            print(f"    ✅ 新体系: {new_hierarchy.get('体系名称', '?')} (评分: {score})")
                            if score >= best_score:
                                best_hierarchy = new_hierarchy
                                best_score = score
                            current_hierarchy = new_hierarchy
                        else:
                            print(f"    ⚠️ 验证失败: {msg}")
                    else:
                        print("    ⚠️ 未能提取JSON体系")

                    self._save_checkpoint({"completed_cycle": cycle, "completed_round": rnd,
                                           "completed_phase": 2, "num_cycles": num_cycles,
                                           "rounds_per_cycle": rounds_per_cycle})
                else:
                    collision_text = ""
                    print("  ⏩ Phase 2 已完成")

                # ======== Phase 3: 反贼 ========
                if start_phase < 3:
                    print(f"\n  🔴 Phase 3: 反贼检测与镇压")
                    active_rebels = self.phase3_rebels(current_hierarchy, collision_text, rnd)

                    # 如果有未镇压的反贼, 再次尝试镇压
                    retry = 0
                    while active_rebels and retry < 2:
                        retry += 1
                        print(f"\n    🔄 第{retry+1}次镇压尝试...")
                        for rebel in active_rebels[:3]:
                            self._suppress_rebel(rebel, current_hierarchy, rnd)
                        active_rebels = self.db.get_active_rebels(self.session_id)

                    self._save_checkpoint({"completed_cycle": cycle, "completed_round": rnd,
                                           "completed_phase": 3, "num_cycles": num_cycles,
                                           "rounds_per_cycle": rounds_per_cycle})
                else:
                    active_rebels = self.db.get_active_rebels(self.session_id)
                    print("  ⏩ Phase 3 已完成")

                # ======== Phase 4: 分裂 ========
                if start_phase < 4:
                    print(f"\n  ⚔️ Phase 4: 群雄割据检测")
                    factions = self.phase4_split(current_hierarchy, active_rebels, rnd)
                    if factions:
                        cycle_factions = factions

                    self._save_checkpoint({"completed_cycle": cycle, "completed_round": rnd,
                                           "completed_phase": 4, "num_cycles": num_cycles,
                                           "rounds_per_cycle": rounds_per_cycle})
                else:
                    factions = None
                    print("  ⏩ Phase 4 已完成")

                # ======== Phase 5: 一统 ========
                if start_phase < 5 and cycle_factions:
                    print(f"\n  👑 Phase 5: 一统天下")
                    unified = self.phase5_unify(cycle_factions, current_hierarchy, rnd)
                    if unified and unified != current_hierarchy:
                        current_hierarchy = unified
                        best_hierarchy = unified
                        cycle_factions = None  # 一统后重置
                        print("    🎉 新架构一统天下! 下一轮将推翻它!")
                else:
                    if not cycle_factions:
                        print(f"\n  👑 Phase 5: 无需一统, 当前体系稳固")

                # 重置 resume_phase
                resume_phase = 0

                # 收敛检测
                new_nodes = len(self._global_seen) - pre_count
                self._round_new_counts.append(new_nodes)
                print(f"\n  📈 本轮新增节点: {new_nodes}")

                self._save_checkpoint({"completed_cycle": cycle, "completed_round": rnd,
                                       "completed_phase": 5, "num_cycles": num_cycles,
                                       "rounds_per_cycle": rounds_per_cycle})

                if len(self._round_new_counts) >= 3:
                    if all(c < 2 for c in self._round_new_counts[-3:]):
                        print(f"\n  🔔 收敛: 连续3轮新增<2节点, 结束本王朝")
                        break

                time.sleep(0.3)

            # 王朝结束: 记录
            all_rebels = self.db.get_all_rebels(self.session_id)
            suppressed = sum(1 for r in all_rebels if r["status"] == "suppressed")
            unsuppressed = sum(1 for r in all_rebels if r["status"] in ("active", "unsuppressable"))

            final_hierarchy = best_hierarchy or current_hierarchy
            if final_hierarchy:
                self.db.create_dynasty(
                    self.session_id, dynasty_num,
                    final_hierarchy.get("体系名称", f"王朝{dynasty_num}"),
                    final_hierarchy,
                    total_rebels=len(all_rebels),
                    suppressed=suppressed, unsuppressed=unsuppressed,
                    score=best_score
                )
                self._save_hierarchy_file(final_hierarchy)

            dynasty_record = {
                "dynasty_num": dynasty_num,
                "hierarchy": final_hierarchy,
                "score": best_score,
                "total_rebels": len(all_rebels),
                "suppressed": suppressed,
                "unsuppressed": unsuppressed,
                "collisions": len(all_collisions)
            }
            all_dynasty_records.append(dynasty_record)

            # 为下一个王朝准备推翻
            prev_hierarchy = final_hierarchy

            print(f"\n{'=' * 70}")
            print(f"🏛️ 王朝{dynasty_num}结束")
            print(f"  体系: {(final_hierarchy or {}).get('体系名称', '?')}")
            print(f"  评分: {best_score}")
            print(f"  反贼: 总{len(all_rebels)} / 镇压{suppressed} / 未镇压{unsuppressed}")
            print(f"{'=' * 70}")

        # ==================== 生成最终报告 ====================
        self._generate_final_report(all_dynasty_records)

        # 清理
        self.delete_checkpoint()
        self.db.end_session(self.session_id,
                            f"完成: {num_cycles}个王朝循环, 最终评分{best_score}")
        self.db.close()

        return best_hierarchy or current_hierarchy

    # ==================== 报告生成 ====================
    def _generate_final_report(self, dynasty_records):
        """生成完整推演报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_nodes = self.db.get_all_nodes(self.session_id)
        all_rebels = self.db.get_all_rebels(self.session_id)
        all_logs = self.db.get_logs(self.session_id)
        all_relations = self.db.get_relations(self.session_id)
        dynasties = self.db.get_dynasties(self.session_id)
        factions = self.db.get_factions(self.session_id)

        # 节点类型统计
        type_counts = {}
        for n in all_nodes:
            t = n.get("node_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        # 反贼统计
        rebel_type_counts = {}
        for r in all_rebels:
            rt = r.get("rebel_type", "unknown")
            rebel_type_counts[rt] = rebel_type_counts.get(rt, 0) + 1

        final_hier = dynasty_records[-1]["hierarchy"] if dynasty_records else None

        report = f"""# 治理层级推演报告 v2.0 — 王朝循环制
> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> Session: {self.session_id}
> 循环模式: 【推演】→【构建】→【反贼】→【分裂】→【一统】

## 一、推演概要

| 指标 | 数值 |
|------|------|
| 王朝循环数 | {len(dynasty_records)} |
| 提取节点 | {len(all_nodes)} |
| 节点关系 | {len(all_relations)} |
| 推演日志 | {len(all_logs)}条 |
| 反贼总数 | {len(all_rebels)} |
| 已镇压 | {sum(1 for r in all_rebels if r['status'] == 'suppressed')} |
| 未镇压 | {sum(1 for r in all_rebels if r['status'] in ('active', 'unsuppressable'))} |
| 竞争派系 | {len(factions)} |

## 二、节点类型分布

| 类型 | 数量 |
|------|------|
"""
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            report += f"| {t} | {c} |\n"

        report += f"""
## 三、反贼统计

| 反贼类型 | 数量 | 说明 |
|----------|------|------|
"""
        for rt, c in sorted(rebel_type_counts.items(), key=lambda x: -x[1]):
            desc = REBEL_TYPES.get(rt, {}).get("desc", "")
            report += f"| {rt} | {c} | {desc} |\n"

        report += "\n### 反贼详情\n\n"
        for r in all_rebels:
            status_icon = "✅" if r["status"] == "suppressed" else "❌" if r["status"] == "unsuppressable" else "🔴"
            report += f"- {status_icon} **{r['rebel_name']}** [{r['severity']}] — {r['description'][:100]}\n"
            report += f"  镇压尝试: {r['suppression_count']}次, 状态: {r['status']}\n"

        report += f"""
## 四、王朝更替记录

"""
        for rec in dynasty_records:
            h = rec["hierarchy"] or {}
            report += f"""### 王朝 {rec['dynasty_num']}: {h.get('体系名称', '未命名')}
- 评分: {rec['score']}
- 反贼: 总{rec['total_rebels']} / 镇压{rec['suppressed']} / 未镇压{rec['unsuppressed']}
- 碰撞轮次: {rec['collisions']}

"""
            if h.get("层级"):
                report += "| 层级 | 名称 | 代码映射 | 管辖幅度 |\n|------|------|---------|----------|\n"
                for lv in h["层级"]:
                    report += f"| L{lv.get('level','?')} | {lv.get('名称','?')} | {lv.get('代码映射','?')} | {lv.get('管辖幅度','?')} |\n"
                report += "\n"

        if factions:
            report += "## 五、群雄割据记录\n\n"
            for f in factions:
                report += f"- **{f.get('faction_name', '?')}** ({f.get('faction_id', '?')}): 得分{f.get('score', 0)}, 状态{f.get('status', '?')}\n"

        report += f"""
## 六、最终一统体系

```json
{json.dumps(final_hier, ensure_ascii=False, indent=2) if final_hier else '未能产生有效体系'}
```

## 七、代码架构映射建议

"""
        if final_hier and "层级" in final_hier:
            report += "| 层级 | 治理角色 | 代码映射 | 职责 |\n|------|---------|---------|------|\n"
            for lv in final_hier["层级"]:
                report += f"| L{lv.get('level','?')} | {lv.get('名称','?')} | {lv.get('代码映射','?')} | {lv.get('职责','')[:60]} |\n"

        if final_hier and "制衡机制" in final_hier:
            report += "\n### 制衡机制\n"
            for m in final_hier["制衡机制"]:
                report += f"- {m}\n"

        if final_hier and "信息通路" in final_hier:
            report += f"\n### 信息通路\n{final_hier['信息通路']}\n"

        report += f"""
---
> 治理层级推演引擎 v2.0 — 王朝循环制
> 循环: 推演→构建→反贼→分裂→一统
> 下次运行将推翻本次结论, 开启新王朝
"""

        # 保存文件
        report_path = OUTPUT_DIR / f"推演报告_{timestamp}.md"
        report_path.write_text(report, encoding="utf-8")

        # 保存碰撞详情到王朝记录目录
        dynasty_path = DYNASTY_LOG_DIR / f"王朝记录_{timestamp}.md"
        dynasty_detail = f"# 王朝循环详情\n> Session: {self.session_id}\n\n"
        for rec in dynasty_records:
            h = rec["hierarchy"] or {}
            dynasty_detail += f"## 王朝 {rec['dynasty_num']}: {h.get('体系名称', '?')}\n"
            dynasty_detail += f"评分: {rec['score']} | 反贼: {rec['total_rebels']}\n\n"
            dynasty_detail += f"```json\n{json.dumps(h, ensure_ascii=False, indent=2)}\n```\n\n"
            dynasty_detail += "---\n\n"
        dynasty_path.write_text(dynasty_detail, encoding="utf-8")

        # 保存反贼记录
        rebel_path = DYNASTY_LOG_DIR / f"反贼记录_{timestamp}.json"
        rebel_path.write_text(json.dumps(all_rebels, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        # 保存最优层级体系JSON
        if final_hier:
            hier_path = OUTPUT_DIR / f"最优层级体系_{timestamp}.json"
            hier_path.write_text(json.dumps(final_hier, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n{'=' * 70}")
        print("✅ 推演完成!")
        print(f"{'=' * 70}")
        print(f"  📊 节点数: {len(all_nodes)}")
        print(f"  🔗 关系数: {len(all_relations)}")
        print(f"  📝 日志数: {len(all_logs)}")
        print(f"  🔴 反贼数: {len(all_rebels)} (镇压{sum(1 for r in all_rebels if r['status']=='suppressed')})")
        print(f"  🏛️ 王朝数: {len(dynasty_records)}")
        if final_hier:
            print(f"  👑 最终体系: {final_hier.get('体系名称', '?')}")
            print(f"  📊 最终评分: {dynasty_records[-1]['score'] if dynasty_records else '?'}")
            if "层级" in final_hier:
                print(f"  📐 层级详情:")
                for lv in final_hier["层级"]:
                    print(f"    L{lv.get('level','?')} {lv.get('名称','?')} → {lv.get('代码映射','?')}")
        print(f"\n  📄 推演报告: {report_path}")
        print(f"  📄 王朝记录: {dynasty_path}")
        print(f"  📄 反贼记录: {rebel_path}")
        print(f"  💾 最优体系: {PREV_HIERARCHY_PATH} (下次运行将推翻)")


# ==================== 主函数 ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="治理层级推演引擎 v2.0 — 王朝循环制")
    parser.add_argument("--cycles", type=int, default=1, help="王朝循环数 (默认1)")
    parser.add_argument("--rounds", type=int, default=10, help="每循环轮数 (默认10)")
    parser.add_argument("--split-threshold", type=int, default=5, help="触发分裂的反贼数阈值 (默认5)")
    parser.add_argument("--no-resume", action="store_true", help="忽略断点, 全新推演")
    args = parser.parse_args()

    engine = DynastyCycleEngine()
    engine.SPLIT_THRESHOLD = args.split_threshold

    checkpoint = None
    if not args.no_resume:
        checkpoint = DynastyCycleEngine.load_checkpoint()
        if checkpoint:
            sid = checkpoint.get("session_id", "?")
            cyc = checkpoint.get("completed_cycle", 0)
            rnd = checkpoint.get("completed_round", 0)
            phase = checkpoint.get("completed_phase", 0)
            print(f"  🔄 发现断点: session={sid}, cycle={cyc}, round={rnd}, phase={phase}")

    engine.run(num_cycles=args.cycles, rounds_per_cycle=args.rounds, _checkpoint=checkpoint)


if __name__ == "__main__":
    main()
