# agi_v13_cognitive_lattice.py
# 版本：v13.3 Cognitive Lattice（认知格核心 + 无限自成长 + 四向碰撞 + 人机共生）
# 核心思想：
#   认知格哲学已植入模型灵魂 — 模型以四向碰撞范式思考
#   自上而下拆解未知→抵达已知（真实物理路径）
#   自下而上从已知合成新问题→突破认知边界
#   左右跨域碰撞→发现重叠→构建结构化认知网络
#   人类领域自洽实践者具现化节点 → AI 梳理实践清单 → 无限循环成长
# 支持后端：
#   本地: Ollama (推荐 qwen2.5-coder:14b)
#   云端: OpenAI / xAI(Grok) / 智谱GLM / DeepSeek / 任何 OpenAI 兼容 API
# 前置条件：
#   pip install openai sentence-transformers numpy
#   本地部署: brew install ollama && ollama pull qwen2.5-coder:14b

import sqlite3
import json
import time
import re
import uuid
import random
import threading
import numpy as np
from pathlib import Path
from datetime import datetime
import cognitive_core

# ==================== 多后端配置 ====================
# 切换后端：修改 ACTIVE_BACKEND 即可
# 本地部署只需安装 Ollama，无需 API Key

BACKENDS = {
    "ollama": {
        "name": "Ollama 本地部署",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",                        # Ollama 不需要真实 key
        "model": "qwen2.5-coder:14b",               # 32GB 内存推荐 14B，内存紧张用 7b
        "embedding_model": "nomic-embed-text",       # Ollama 内置 embedding
    },
    "ollama_7b": {
        "name": "Ollama 本地轻量",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "qwen2.5-coder:7b",
        "embedding_model": "nomic-embed-text",
    },
    "openai": {
        "name": "OpenAI GPT",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-你的OpenAI密钥",
        "model": "gpt-4o",
        "embedding_model": None,                     # 用本地 sentence-transformers
    },
    "xai": {
        "name": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "api_key": "xai-你的xAI密钥",
        "model": "grok-3-mini",
        "embedding_model": None,
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-你的DeepSeek密钥",
        "model": "deepseek-chat",
        "embedding_model": None,
    },
    "zhipu": {
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "8b9c47697cba446baeae08f712faddc7.rYaSMdJYONxdGgBb",
        "model": "glm-4-flash",
        "embedding_model": None,
        "api_type": "openai",
    },
    "zhipu_45air": {
        "name": "智谱 GLM-4.5-Air",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "8b9c47697cba446baeae08f712faddc7.rYaSMdJYONxdGgBb",
        "model": "GLM-4.5-Air",
        "embedding_model": None,
        "api_type": "openai",
    },
    "zhipu_47": {
        "name": "智谱 GLM-4.7",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "8b9c47697cba446baeae08f712faddc7.rYaSMdJYONxdGgBb",
        "model": "GLM-4.7",
        "embedding_model": None,
        "api_type": "openai",
    },
    "zhipu_glm5": {
        "name": "智谱 GLM-5 (Anthropic)",
        "base_url": "https://open.bigmodel.cn/api/anthropic",
        "api_key": "8b9c47697cba446baeae08f712faddc7.rYaSMdJYONxdGgBb",
        "model": "glm-5",
        "embedding_model": None,
        "api_type": "anthropic",
    },
    "zhipu_45airx": {
        "name": "智谱 GLM-4.5-AirX (超快响应)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "8b9c47697cba446baeae08f712faddc7.rYaSMdJYONxdGgBb",
        "model": "GLM-4.5-AirX",
        "embedding_model": None,
        "api_type": "openai",
    },
}

class Config:
    # ★★★ 切换后端：改这一行即可 ★★★
    ACTIVE_BACKEND = "ollama"            # 可选: ollama / ollama_7b / openai / xai / deepseek / zhipu

    DB_PATH = Path(__file__).parent / "memory.db"
    TEMPERATURE = 0.35
    MAX_TOKENS = 8192
    COLLISION_THRESHOLD = 0.72          # 重叠碰撞阈值
    CROSS_DOMAIN_THRESHOLD = 0.65       # 跨域碰撞阈值
    ENABLE_HUMAN_INGEST = True
    SELF_GROWTH_INTERVAL = 300          # 自成长循环间隔（秒）
    GROWTH_BATCH_SIZE = 3               # 每次自成长从DB取几个节点
    MAX_DEPTH_PER_CYCLE = 2             # 每次自成长最大拆解深度
    ZHIPU_AUTO_DELEGATE = True          # 智谱API自动委托开关（本地模型不佳时自动调用智谱）
    ZHIPU_GROWTH_ENABLED = True         # 智谱API自主成长开关

    @classmethod
    def backend(cls):
        return BACKENDS[cls.ACTIVE_BACKEND]

    @classmethod
    def model(cls):
        return cls.backend()["model"]

    @classmethod
    def switch_backend(cls, backend_name):
        """动态切换后端，返回是否成功"""
        if backend_name not in BACKENDS:
            return False
        cls.ACTIVE_BACKEND = backend_name
        # 强制重建 LLM 客户端
        _LazyModels._llm_client = None
        print(f"  [Config] 后端切换为: {BACKENDS[backend_name]['name']}")
        return True


# ==================== 懒加载管理器 ====================
class _LazyModels:
    """延迟加载 LLM 客户端和 Embedding 模型，避免启动卡顿"""
    _llm_client = None
    _embed_client = None   # 独立的 Ollama embedding 客户端，不受后端切换影响
    _embed_model = None
    _ollama_embed = False
    _init_lock = threading.Lock()  # 防止多线程并发初始化导致segfault

    @classmethod
    def llm_client(cls):
        if cls._llm_client is None:
            with cls._init_lock:
                if cls._llm_client is None:  # double-check
                    from openai import OpenAI
                    b = Config.backend()
                    cls._llm_client = OpenAI(
                        api_key=b["api_key"],
                        base_url=b["base_url"],
                    )
                    print(f"  [LLM] 已连接：{b['name']} ({b['model']})")
        return cls._llm_client

    @classmethod
    def embed_client(cls):
        """独立的 Ollama embedding 客户端，不受后端切换影响"""
        if cls._embed_client is None:
            with cls._init_lock:
                if cls._embed_client is None:  # double-check
                    from openai import OpenAI
                    ollama_b = BACKENDS.get("ollama", BACKENDS.get("ollama_7b"))
                    if ollama_b:
                        cls._embed_client = OpenAI(
                            api_key=ollama_b["api_key"],
                            base_url=ollama_b["base_url"],
                        )
                        print(f"  [Embedding] 独立 Ollama 客户端已建立: {ollama_b['base_url']}")
        return cls._embed_client

    @classmethod
    def embed_model(cls):
        if cls._embed_model is None:
            with cls._init_lock:
                if cls._embed_model is None:  # double-check
                    # 优先使用 Ollama embedding，不管当前 LLM 后端是什么
                    ollama_b = BACKENDS.get("ollama", BACKENDS.get("ollama_7b"))
                    if ollama_b and ollama_b.get("embedding_model"):
                        cls._ollama_embed = True
                        cls._embed_model = ollama_b["embedding_model"]
                        print(f"  [Embedding] 使用 Ollama 内置: {ollama_b['embedding_model']}")
                    else:
                        from sentence_transformers import SentenceTransformer
                        print("  [Embedding] 加载本地模型 BAAI/bge-large-zh-v1.5 ...")
                        cls._embed_model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
                        cls._ollama_embed = False
                        print("  [Embedding] 加载完成")
        return cls._embed_model

Models = _LazyModels


# ==================== LLM 统一调用 ====================
def _anthropic_call(messages, model=None):
    """通过 Anthropic 兼容接口调用 LLM（智谱 GLM-5 等）"""
    import requests as _req
    b = Config.backend()
    model = model or b["model"]
    base_url = b["base_url"].rstrip("/")
    api_key = b["api_key"]

    # 拆分 system 和 chat messages
    system_text = ""
    chat_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n"
        else:
            chat_msgs.append({"role": m["role"], "content": m["content"]})
    if not chat_msgs:
        chat_msgs = [{"role": "user", "content": system_text}]
        system_text = ""

    body = {
        "model": model,
        "max_tokens": Config.MAX_TOKENS,
        "messages": chat_msgs,
    }
    if system_text.strip():
        body["system"] = system_text.strip()

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    resp = _req.post(f"{base_url}/v1/messages", headers=headers, json=body, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    # Anthropic 响应格式: {"content": [{"type": "text", "text": "..."}]}
    content = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            content += block.get("text", "")
    return content.strip()


def _parse_llm_content(content):
    """解析LLM返回的内容，尝试提取JSON"""
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    try:
        return json.loads(content)
    except:
        return {"raw": content}


def _zhipu_call_direct(messages, task_type="chat"):
    """直接调用智谱API，不经过后端切换"""
    zhipu_b = BACKENDS.get("zhipu")
    if not zhipu_b or not zhipu_b.get("api_key"):
        return None
    try:
        from openai import OpenAI
        # 根据任务类型选择模型
        model_map = {"code_gen": "GLM-4.5-Air", "reasoning": "GLM-4.7",
                     "long_doc": "glm-4-long", "chat": "glm-4-flash",
                     "action_plan": "GLM-4.5-Air", "code_execute": "GLM-4.7",
                     "analyze": "GLM-4.7", "deep_reasoning": "GLM-4.7",
                     "quick_chat": "GLM-4.5-AirX"}
        model = model_map.get(task_type, "glm-4-flash")
        client = OpenAI(api_key=zhipu_b["api_key"], base_url=zhipu_b["base_url"])
        resp = client.chat.completions.create(
            model=model,
            max_tokens=Config.MAX_TOKENS,
            temperature=0.3,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        content = resp.choices[0].message.content.strip()
        print(f"  [自动委托] 智谱 {model} 返回 {len(content)} 字符")
        return _parse_llm_content(content)
    except Exception as e:
        print(f"  [自动委托] 智谱调用失败: {e}")
        return None


def glm5_call(messages, max_tokens=8192):
    """直接调用 GLM-5 (Anthropic 接口)，供 orchestrator 使用
    不经过 Config.backend()，直接使用 zhipu_glm5 配置"""
    glm5_b = BACKENDS.get("zhipu_glm5")
    if not glm5_b:
        print("  [GLM-5] 后端未配置，回退到 GLM-4.7")
        return _zhipu_call_direct(messages, "deep_reasoning")
    try:
        import requests as _req
        base_url = glm5_b["base_url"].rstrip("/")
        api_key = glm5_b["api_key"]
        model = glm5_b["model"]

        system_text = ""
        chat_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_text += m["content"] + "\n"
            else:
                chat_msgs.append({"role": m["role"], "content": m["content"]})
        if not chat_msgs:
            chat_msgs = [{"role": "user", "content": system_text}]
            system_text = ""

        body = {"model": model, "max_tokens": max_tokens, "messages": chat_msgs}
        if system_text.strip():
            body["system"] = system_text.strip()

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        resp = _req.post(f"{base_url}/v1/messages", headers=headers, json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        content = content.strip()
        if content:
            print(f"  [GLM-5] 返回 {len(content)} 字符")
            return _parse_llm_content(content)
        return None
    except Exception as e:
        print(f"  [GLM-5] 调用失败: {e}，回退到 GLM-4.7")
        return _zhipu_call_direct(messages, "deep_reasoning")


def glm45airx_call(messages):
    """直接调用 GLM-4.5-AirX (超快响应)，供 orchestrator 使用"""
    airx_b = BACKENDS.get("zhipu_45airx")
    if not airx_b:
        return _zhipu_call_direct(messages, "quick_chat")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=airx_b["api_key"], base_url=airx_b["base_url"])
        resp = client.chat.completions.create(
            model=airx_b["model"],
            max_tokens=2048,
            temperature=0.3,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        content = resp.choices[0].message.content.strip()
        print(f"  [GLM-4.5-AirX] 返回 {len(content)} 字符")
        return _parse_llm_content(content)
    except Exception as e:
        print(f"  [GLM-4.5-AirX] 调用失败: {e}")
        return None


def _detect_task_type(messages):
    """从消息内容检测任务类型"""
    text = " ".join(m.get("content", "") for m in messages).lower()
    if any(k in text for k in ['代码', 'code', '实现', '编写', '函数', '程序', 'def ', 'class ', 'import ']):
        return "code_gen"
    if any(k in text for k in ['推理', '分析', '为什么', '原因', '解释', 'reason', 'analyze', '设计方案']):
        return "reasoning"
    if len(text) > 3000:
        return "long_doc"
    return "chat"


def _needs_delegation(result, messages):
    """判断本地模型结果是否需要委托给云端"""
    # 1. 错误 → 委托
    if isinstance(result, dict) and "error" in result:
        return True
    # 2. 空结果 → 委托
    if isinstance(result, list) and len(result) == 0:
        return True
    # 3. 内容太短（可能回答不充分）
    raw = ""
    if isinstance(result, dict):
        raw = result.get("raw", "")
    elif isinstance(result, list):
        raw = json.dumps(result, ensure_ascii=False)
    if isinstance(raw, str) and len(raw) < 30:
        # 检查消息复杂度——简单问题短回答是正常的
        q_len = sum(len(m.get("content", "")) for m in messages if m.get("role") == "user")
        if q_len > 100:  # 问题长但回答短 → 委托
            return True
    # 4. 本地模型明确表示不确定/不知道
    if isinstance(raw, str):
        uncertainty = ['不确定', '无法回答', '不知道', '超出', '我没有', 'i don\'t know',
                       'i\'m not sure', 'cannot answer', '抱歉我无法', '无法确定']
        raw_lower = raw.lower()
        if any(u in raw_lower for u in uncertainty):
            return True
    return False


def llm_call(messages, model=None, _allow_delegate=True):
    model = model or Config.model()
    try:
        b = Config.backend()
        # 根据 api_type 选择调用方式
        if b.get("api_type") == "anthropic":
            content = _anthropic_call(messages, model)
        else:
            client = Models.llm_client()
            resp = client.chat.completions.create(
                model=model,
                max_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages]
            )
            content = resp.choices[0].message.content.strip()
        result = _parse_llm_content(content)
    except Exception as e:
        print(f"  [LLM] 调用失败: {e}")
        result = {"error": str(e)}

    # 自动委托：本地模型结果不佳时自动调用智谱API（受开关控制）
    if _allow_delegate and Config.ZHIPU_AUTO_DELEGATE and Config.ACTIVE_BACKEND in ('ollama', 'ollama_7b'):
        if _needs_delegation(result, messages):
            task_type = _detect_task_type(messages)
            print(f"  [自动委托] 本地结果不佳，委托智谱({task_type})...")
            _broadcast("auto_delegate", f"本地模型能力不足，自动委托智谱AI({task_type})", "running")
            zhipu_result = _zhipu_call_direct(messages, task_type)
            if zhipu_result is not None:
                _broadcast("auto_delegate", "智谱AI返回结果，已自动采纳", "done")
                return zhipu_result
            _broadcast("auto_delegate", "智谱API不可用，使用本地结果", "done")

    return result


# ==================== 双模验证调用 ====================
_step_callback = None  # api_server.py 设置此回调，让验证过程可以广播SSE步骤

def set_step_callback(fn):
    """注册步骤广播回调，供api_server在启动时设置"""
    global _step_callback
    _step_callback = fn

def _broadcast(step_type, detail, status="running"):
    """内部广播辅助函数"""
    if _step_callback:
        try: _step_callback(step_type, detail, status)
        except: pass
    print(f"  [{step_type}] {detail}")

def _is_cloud_backend():
    """判断当前后端是否为云端（非本地Ollama）"""
    return Config.ACTIVE_BACKEND not in ('ollama', 'ollama_7b')

def _local_ollama_call(messages):
    """强制使用本地Ollama调用，不管当前后端是什么"""
    from openai import OpenAI
    ollama_b = BACKENDS.get("ollama", BACKENDS.get("ollama_7b"))
    if not ollama_b:
        return {"error": "本地Ollama未配置"}
    client = OpenAI(api_key=ollama_b["api_key"], base_url=ollama_b["base_url"])
    try:
        resp = client.chat.completions.create(
            model=ollama_b["model"],
            max_tokens=Config.MAX_TOKENS,
            temperature=0.2,  # 校验时用低温度，更确定性
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        content = resp.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        try:
            return json.loads(content)
        except:
            return {"raw": content}
    except Exception as e:
        print(f"  [本地校验] Ollama调用失败: {e}")
        return {"error": str(e)}


def _proven_grounding_check(text, proven_nodes):
    """句级proven节点事实锚定检查 — 不依赖本地LLM质量
    
    将云端输出拆句，每句与proven节点做cosine相似度比对，
    计算整体事实锚定率(grounding_ratio)。
    
    返回: {grounding_ratio, grounded_sentences, ungrounded_sentences, avg_similarity}
    """
    if not proven_nodes or not text:
        return {"grounding_ratio": 0.0, "grounded_sentences": [], "ungrounded_sentences": [], "avg_similarity": 0.0}

    # 拆句(中英文句号/问号/感叹号/换行)
    sentences = re.split(r'[。！？\n.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 8]  # 过滤过短片段
    if not sentences:
        return {"grounding_ratio": 0.0, "grounded_sentences": [], "ungrounded_sentences": [], "avg_similarity": 0.0}

    # 获取proven节点embeddings
    proven_embs = []
    for n in proven_nodes[:15]:
        try:
            emb = get_embedding(n.get('content', ''))
            proven_embs.append((n, emb))
        except Exception:
            continue

    if not proven_embs:
        return {"grounding_ratio": 0.0, "grounded_sentences": [], "ungrounded_sentences": [], "avg_similarity": 0.0}

    grounded = []
    ungrounded = []
    total_sim = 0.0
    GROUNDING_THRESHOLD = 0.45  # 与proven节点相似度>0.45视为有事实支撑

    for sent in sentences[:20]:  # 最多检查20句，避免过慢
        try:
            sent_emb = get_embedding(sent)
            max_sim = 0.0
            best_node = None
            for node, pemb in proven_embs:
                sim = cosine_similarity(sent_emb, pemb)
                if sim > max_sim:
                    max_sim = sim
                    best_node = node
            total_sim += max_sim
            if max_sim >= GROUNDING_THRESHOLD:
                grounded.append({"sentence": sent[:80], "similarity": round(max_sim, 3),
                                 "anchor": best_node.get('content', '')[:60] if best_node else ""})
            else:
                ungrounded.append({"sentence": sent[:80], "max_similarity": round(max_sim, 3)})
        except Exception:
            ungrounded.append({"sentence": sent[:80], "max_similarity": 0.0})

    total = len(grounded) + len(ungrounded)
    ratio = len(grounded) / total if total > 0 else 0.0
    avg_sim = total_sim / total if total > 0 else 0.0

    return {
        "grounding_ratio": round(ratio, 3),
        "grounded_sentences": grounded,
        "ungrounded_sentences": ungrounded,
        "avg_similarity": round(avg_sim, 3),
    }


def verified_llm_call(messages, lattice=None, question=""):
    """双模验证调用：云端AI推理 + 本地模型校验 + proven节点句级锚定
    
    流程：
    1. 收集相关proven节点作为校验标尺
    2. 向云端AI注入反幻觉约束后调用
    3. proven节点句级锚定检查(embedding cosine, 不依赖本地LLM)
    4. 本地模型用proven节点校验云端输出
    5. 综合两层验证信号，返回清洁结果
    
    如果当前是本地后端，直接调用不走验证流程。
    """
    if not _is_cloud_backend():
        return llm_call(messages)

    _broadcast("verification", f"双模验证启动: {Config.backend()['name']} + proven锚定 + 本地校验", "running")

    # 1. 收集proven节点作为校验标尺
    proven_nodes = []
    if lattice and question:
        try:
            all_related = lattice.find_similar_nodes(question, threshold=0.35, limit=10)
            proven_nodes = [n for n in all_related if n.get('status') == 'proven']
            _broadcast("verification", f"找到 {len(proven_nodes)} 个proven校验标尺", "running")
        except Exception:
            pass

    # 2. 向云端AI注入反幻觉约束
    constrained_messages = list(messages)
    if constrained_messages and constrained_messages[0]["role"] == "system":
        constrained_messages[0] = {
            "role": "system",
            "content": constrained_messages[0]["content"] + "\n\n" + cognitive_core.CLOUD_AI_CONSTRAINT
        }
    else:
        constrained_messages.insert(0, {
            "role": "system",
            "content": cognitive_core.CLOUD_AI_CONSTRAINT
        })

    # 注入proven节点上下文，让云端AI基于真实知识回答
    if proven_nodes:
        proven_ctx = "\n".join(
            f"- [proven] {n.get('content','')[:80]}" for n in proven_nodes[:8]
        )
        for i, m in enumerate(constrained_messages):
            if m["role"] == "user":
                constrained_messages[i] = {
                    "role": "user",
                    "content": f"以下是已验证的真实知识节点，请基于这些真实知识回答，超出部分请明确标注为假设：\n{proven_ctx}\n\n{m['content']}"
                }
                break

    # 3. 调用云端AI
    _broadcast("verification", f"调用云端 {Config.model()}...", "running")
    cloud_result = llm_call(constrained_messages)

    # 结构化JSON数组（如拆解结果）直接返回
    if isinstance(cloud_result, list):
        _broadcast("verification", f"云端返回结构化数据({len(cloud_result)}项)", "done")
        return cloud_result

    cloud_text = cloud_result.get('raw', str(cloud_result)) if isinstance(cloud_result, dict) else str(cloud_result)

    if not cloud_text or len(cloud_text) < 10:
        return cloud_result

    # 4. proven节点句级锚定检查（embedding级别，不依赖本地LLM）
    grounding = {"grounding_ratio": 0.0}
    if proven_nodes:
        _broadcast("verification", "proven节点句级锚定检查...", "running")
        try:
            grounding = _proven_grounding_check(cloud_text, proven_nodes)
            g_ratio = grounding["grounding_ratio"]
            g_count = len(grounding.get("grounded_sentences", []))
            u_count = len(grounding.get("ungrounded_sentences", []))
            _broadcast("verification", f"锚定率:{g_ratio:.0%} ({g_count}句有锚/{u_count}句无锚)", "running")
        except Exception as e:
            _broadcast("verification", f"锚定检查异常: {e}", "running")

    # 5. 本地模型校验
    _broadcast("verification", "本地Ollama校验中...", "running")
    check_messages = cognitive_core.make_hallucination_check_prompt(
        cloud_text, proven_nodes, question
    )
    check_result = _local_ollama_call(check_messages)

    # 6. 综合两层验证信号
    g_ratio = grounding.get("grounding_ratio", 0.0)

    if isinstance(check_result, dict) and not check_result.get('error'):
        llm_confidence = check_result.get('confidence', 0.5)
        rejected = check_result.get('rejected_parts', [])
        verified = check_result.get('verified_parts', [])
        hypothesis = check_result.get('hypothesis_parts', [])
        cleaned = check_result.get('cleaned_response', cloud_text)
        limitations = check_result.get('honest_limitations', [])

        # 综合置信度 = 0.4*本地LLM判断 + 0.6*proven锚定率
        combined_confidence = round(0.4 * llm_confidence + 0.6 * g_ratio, 3) if g_ratio > 0 else llm_confidence

        # 构建验证报告
        report_parts = []
        if verified:
            report_parts.append(f"✅ 已验证({len(verified)}项)")
        if hypothesis:
            report_parts.append(f"❓ 待验证({len(hypothesis)}项)")
        if rejected:
            report_parts.append(f"❌ 已删除幻觉({len(rejected)}项)")
        if limitations:
            report_parts.append(f"⚠ 诚实局限({len(limitations)}项)")
        report_parts.append(f"🔗 锚定率:{g_ratio:.0%}")

        verification_tag = " | ".join(report_parts)
        confidence_tag = f"可信度:{combined_confidence:.0%}"

        final_text = cleaned if (cleaned and len(cleaned) > 20) else cloud_text
        if rejected:
            final_text += f"\n\n---\n⚠ **本地校验发现 {len(rejected)} 项幻觉已删除：**\n"
            for rj in rejected[:5]:
                final_text += f"- ❌ {rj}\n"

        # 锚定率低时追加未锚定句子警告
        if g_ratio < 0.3 and grounding.get("ungrounded_sentences"):
            final_text += f"\n\n---\n⚠ **proven锚定率偏低({g_ratio:.0%})，以下内容缺乏proven节点支撑：**\n"
            for ug in grounding["ungrounded_sentences"][:3]:
                final_text += f"- ❓ {ug['sentence']}\n"

        _broadcast("verification", f"校验完成: {verification_tag}, {confidence_tag}", "done")
        return {"raw": final_text, "_verification": {
            "confidence": combined_confidence,
            "reliable": combined_confidence >= 0.5,
            "verified_count": len(verified),
            "hypothesis_count": len(hypothesis),
            "rejected_count": len(rejected),
            "grounding_ratio": g_ratio,
            "grounded_count": len(grounding.get("grounded_sentences", [])),
            "tag": f"[{verification_tag} | {confidence_tag}]"
        }}
    else:
        # 本地校验失败 → 仅依赖proven锚定
        if g_ratio >= 0.5:
            _broadcast("verification", f"本地校验失败，但proven锚定率{g_ratio:.0%}可接受", "done")
            return {"raw": cloud_text + f"\n\n⚠ **本地校验未完成，proven锚定率:{g_ratio:.0%}**",
                    "_verification": {"confidence": g_ratio * 0.8, "reliable": g_ratio >= 0.6,
                                      "grounding_ratio": g_ratio, "tag": f"[本地校验失败 | 锚定率:{g_ratio:.0%}]"}}
        else:
            _broadcast("verification", "本地校验失败且锚定率低，标记为未校验", "error")
            return {"raw": cloud_text + "\n\n⚠ **本地校验未完成，此回答未经验证**",
                    "_verification": {"confidence": 0.2, "reliable": False,
                                      "grounding_ratio": g_ratio, "tag": "[未校验]"}}


# ==================== 工具函数 ====================
_embedding_lock = threading.Lock()
_thread_local = threading.local()  # 每线程独立的Ollama客户端，防止httpx连接池malloc崩溃

def _get_thread_embed_client():
    """获取当前线程专属的Ollama embedding客户端"""
    if not hasattr(_thread_local, 'embed_client') or _thread_local.embed_client is None:
        ollama_b = BACKENDS.get("ollama", BACKENDS.get("ollama_7b"))
        if ollama_b:
            from openai import OpenAI
            _thread_local.embed_client = OpenAI(
                api_key=ollama_b["api_key"],
                base_url=ollama_b["base_url"],
            )
    return getattr(_thread_local, 'embed_client', None)

def get_embedding(text: str) -> bytes:
    with _embedding_lock:
        if Models._ollama_embed or Models._embed_model is None:
            # 确保模型配置已加载
            model_name = Models.embed_model()
            if Models._ollama_embed:
                # 使用线程专属客户端获取embedding（避免共享httpx连接池导致segfault）
                try:
                    client = _get_thread_embed_client()
                    if client is None:
                        raise RuntimeError("Ollama embedding 客户端未就绪")
                    resp = client.embeddings.create(
                        model=model_name,
                        input=text
                    )
                    vec = np.array(resp.data[0].embedding, dtype=np.float32)
                    return vec.tobytes()
                except Exception as e:
                    print(f"  [Embedding] Ollama embedding 失败，回退本地: {e}")
                    # 回退到 sentence-transformers
                    from sentence_transformers import SentenceTransformer
                    Models._embed_model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
                    Models._ollama_embed = False
        vec = Models.embed_model().encode(text)
        return vec.tobytes()

def cosine_similarity(a: bytes, b: bytes) -> float:
    a_arr = np.frombuffer(a, dtype=np.float32)
    b_arr = np.frombuffer(b, dtype=np.float32)
    if a_arr.shape != b_arr.shape:
        return 0.0  # 维度不匹配（不同 embedding 模型产生的向量）
    if np.linalg.norm(a_arr) == 0 or np.linalg.norm(b_arr) == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

def _sanitize_item(item):
    """校验并修复单个拆解项的字段完整性（兼容认知节点和动作计划两种格式）"""
    if not isinstance(item, dict):
        if isinstance(item, str) and len(item.strip()) > 3:
            return {"content": item.strip(), "can_verify": False, "domain": "general", "reasoning": ""}
        return None
    # 动作计划项（有action字段）直接通过，不需要content
    if item.get("action"):
        return item
    # 认知节点项：必须有content
    if not item.get("content") and not item.get("question"):
        return None
    # 字段默认值填充
    item.setdefault("content", item.get("question", ""))
    item.setdefault("can_verify", False)
    item.setdefault("domain", "general")
    item.setdefault("reasoning", "")
    item.setdefault("depth", 0)
    # 类型修正
    if isinstance(item["can_verify"], str):
        item["can_verify"] = item["can_verify"].lower() in ("true", "yes", "1", "是")
    if isinstance(item.get("depth"), str):
        try:
            item["depth"] = int(item["depth"])
        except (ValueError, TypeError):
            item["depth"] = 0
    return item


def _extract_json_from_text(text):
    """从LLM文本中尝试提取JSON数组（多种容错策略）"""
    if not isinstance(text, str):
        return None
    # 策略1: 标准JSON数组
    m = re.search(r'\[[\s\S]*\]', text)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    # 策略2: ```json ... ``` 代码块
    m = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 策略3: 修复常见问题(尾部逗号, 单引号)
    if m:
        fixed = m.group(1) if m else text
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)  # 移除尾部逗号
        fixed = fixed.replace("'", '"')  # 单引号→双引号
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
    return None


def extract_items(result):
    """从 LLM 返回结果中提取列表项，兼容多种格式 + Schema校验 + 容错修复"""
    items = None

    if isinstance(result, list):
        items = result
    elif isinstance(result, dict):
        if "error" in result:
            return []
        if "raw" in result:
            raw = result["raw"]
            if isinstance(raw, list):
                items = raw
            elif isinstance(raw, str):
                # 先尝试标准解析
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        items = parsed
                    elif isinstance(parsed, dict):
                        items = [parsed]
                except json.JSONDecodeError:
                    # 容错：从文本中提取JSON
                    extracted = _extract_json_from_text(raw)
                    if extracted and isinstance(extracted, list):
                        items = extracted
            if items is None:
                return []
        else:
            # 可能直接是单个 dict 项
            items = [result]
    else:
        return []

    # Schema校验 + 字段修复
    sanitized = []
    for item in items:
        fixed = _sanitize_item(item)
        if fixed is not None:
            sanitized.append(fixed)

    return sanitized

# ==================== 数据库操作 ====================
class CognitiveLattice:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS cognitive_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL UNIQUE,
            domain TEXT DEFAULT 'general',
            status TEXT DEFAULT 'known' CHECK(status IN ('known', 'hypothesis', 'falsified', 'proven')),
            verified_source TEXT,
            depth INTEGER DEFAULT 0,
            parent_id INTEGER,
            embedding BLOB,
            access_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            last_verified_at TEXT
        );

        CREATE TABLE IF NOT EXISTS node_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node1_id INTEGER,
            node2_id INTEGER,
            relation_type TEXT,
            confidence REAL DEFAULT 0.5,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(node1_id) REFERENCES cognitive_nodes(id),
            FOREIGN KEY(node2_id) REFERENCES cognitive_nodes(id)
        );

        CREATE TABLE IF NOT EXISTS growth_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            action TEXT,
            detail TEXT,
            nodes_before INTEGER,
            nodes_after INTEGER,
            relations_before INTEGER,
            relations_after INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS practice_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER,
            practice_content TEXT,
            result TEXT,
            verified BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(node_id) REFERENCES cognitive_nodes(id)
        );

        CREATE INDEX IF NOT EXISTS idx_content ON cognitive_nodes(content);
        CREATE INDEX IF NOT EXISTS idx_status ON cognitive_nodes(status);
        CREATE INDEX IF NOT EXISTS idx_domain ON cognitive_nodes(domain);

        -- Orchestrator: 问题生命周期追踪
        CREATE TABLE IF NOT EXISTS problem_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_question TEXT NOT NULL,
            question_hash TEXT,
            status TEXT DEFAULT 'pending',
            complexity_score REAL,
            assigned_model TEXT,
            decomposition_depth INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            final_node_ids TEXT,
            unsolvable_reason TEXT,
            retry_count INTEGER DEFAULT 0,
            proven_coverage REAL DEFAULT 0.0,
            routing_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS problem_decomposition_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER,
            step_type TEXT,
            model_used TEXT,
            input_summary TEXT,
            output_summary TEXT,
            success INTEGER DEFAULT 1,
            duration_ms INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (problem_id) REFERENCES problem_tracking(id)
        );

        CREATE INDEX IF NOT EXISTS idx_pt_hash ON problem_tracking(question_hash);
        CREATE INDEX IF NOT EXISTS idx_pt_status ON problem_tracking(status);
        CREATE INDEX IF NOT EXISTS idx_pdl_problem ON problem_decomposition_log(problem_id);
        """)
        self.conn.commit()
        # 旧数据库 schema 迁移：为旧表补充新列
        migrate_columns = [
            ("cognitive_nodes", "depth", "INTEGER DEFAULT 0"),
            ("cognitive_nodes", "parent_id", "INTEGER"),
            ("cognitive_nodes", "access_count", "INTEGER DEFAULT 0"),
        ]
        for table, col, col_type in migrate_columns:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                self.conn.commit()
            except sqlite3.OperationalError:
                pass  # 列已存在，跳过

    # ---------- 节点操作 ----------
    def add_node(self, content: str, domain: str = "general",
                 status: str = "known", source: str = "human",
                 depth: int = 0, parent_id: int = None, silent: bool = False):
        if not content or not content.strip():
            return None
        content = content.strip()
        emb = get_embedding(content)
        with self._lock:
            c = self.conn.cursor()
            try:
                c.execute("""
                    INSERT INTO cognitive_nodes
                        (content, domain, status, verified_source, depth, parent_id, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (content, domain, status, source, depth, parent_id, emb))
                self.conn.commit()
                if not silent:
                    print(f"  [+节点] {content[:60]}  (域:{domain} 源:{source} 状态:{status})")
                return c.lastrowid
            except sqlite3.IntegrityError:
                c.execute("SELECT id FROM cognitive_nodes WHERE content = ?", (content,))
                row = c.fetchone()
                return row['id'] if row else None

    def update_node_status(self, node_id: int, new_status: str, reason: str = ""):
        with self._lock:
            c = self.conn.cursor()
            c.execute("""
                UPDATE cognitive_nodes
                SET status = ?, last_verified_at = datetime('now')
                WHERE id = ?
            """, (new_status, node_id))
            if c.rowcount > 0:
                self.conn.commit()

    def touch_node(self, node_id: int):
        """增加节点访问计数，活跃节点更容易被选中进行成长"""
        with self._lock:
            self.conn.execute(
                "UPDATE cognitive_nodes SET access_count = access_count + 1 WHERE id = ?",
                (node_id,))
            self.conn.commit()

    # ---------- 查询操作 ----------
    def get_random_known_nodes(self, n: int = 3, domain: str = None):
        """从已知节点池中随机取 n 个，优先取访问少的（探索更多边界）"""
        with self._lock:
            c = self.conn.cursor()
            if domain:
                c.execute("""
                    SELECT * FROM cognitive_nodes
                    WHERE status IN ('known', 'proven') AND domain = ?
                    ORDER BY access_count ASC, RANDOM() LIMIT ?
                """, (domain, n))
            else:
                c.execute("""
                    SELECT * FROM cognitive_nodes
                    WHERE status IN ('known', 'proven')
                    ORDER BY access_count ASC, RANDOM() LIMIT ?
                """, (n,))
            return [dict(r) for r in c.fetchall()]

    def get_hypothesis_nodes(self, n: int = 5):
        """取待验证假设节点"""
        with self._lock:
            c = self.conn.cursor()
            c.execute("""
                SELECT * FROM cognitive_nodes
                WHERE status = 'hypothesis'
                ORDER BY created_at DESC LIMIT ?
            """, (n,))
            return [dict(r) for r in c.fetchall()]

    def get_all_domains(self):
        with self._lock:
            c = self.conn.cursor()
            c.execute("SELECT DISTINCT domain FROM cognitive_nodes")
            return [r['domain'] for r in c.fetchall()]

    def get_nodes_by_domain(self, domain: str, limit: int = 50):
        with self._lock:
            c = self.conn.cursor()
            c.execute("""
                SELECT * FROM cognitive_nodes WHERE domain = ?
                ORDER BY created_at DESC LIMIT ?
            """, (domain, limit))
            return [dict(r) for r in c.fetchall()]

    def find_similar_nodes(self, text: str, threshold: float = 0.7, limit: int = 5):
        """混合语义搜索：分层检索 + 领域优先
        
        策略：
        1. 从查询中提取领域关键词（Dart/Flutter/Python等）
        2. 分两层检索：领域匹配层（优先）+ 全局层（补充）
        3. 领域匹配层：domain或content包含关键词的节点，按embedding相似度排序
        4. 全局层：其余节点按embedding相似度排序，补充剩余位置
        """
        emb = get_embedding(text)
        text_lower = text.lower()
        
        # 领域关键词映射
        domain_keywords = {
            'dart': ['dart'],
            'flutter': ['flutter'],
            'python': ['python', 'gil', 'asyncio', 'pip', 'pytest'],
            'android': ['android', 'kotlin'],
            'ios': ['ios', 'swift', 'swiftui'],
            'web': ['web', 'html', 'css', 'javascript', 'react', 'vue'],
            'devops': ['devops', 'docker', 'k8s', 'ci/cd', 'kubernetes'],
            'agi': ['agi', '认知格', 'cognitive lattice', '四向碰撞', '自成长'],
            'openclaw': ['openclaw', 'gateway', '控制平面'],
            '搜索': ['搜索', 'search', 'mmr', 'embedding', '向量', '混合搜索', '时间衰减'],
            '架构': ['架构', 'architecture', '微服务', 'agent', '子agent', 'subagent', '故障转移', 'fallback'],
            '可靠性': ['可靠性', '循环检测', 'loop detection', '断路器', 'circuit breaker'],
            '操作系统': ['操作系统', 'linux', 'kernel', 'epoll', 'namespace', 'cgroup', '进程', '虚拟内存', '页表', '调度'],
            '网络': ['tcp', 'udp', 'http', 'https', 'tls', 'dns', '拥塞', '握手', 'cors', '网络协议'],
            '数据库': ['数据库', 'database', 'sql', 'sqlite', 'mysql', 'postgres', 'b+树', '索引', 'mvcc', 'wal', '事务'],
            '分布式': ['分布式', 'raft', 'cap', '一致性哈希', '2pc', 'paxos', '分区', '副本'],
            '安全': ['安全', 'security', 'jwt', 'bcrypt', '注入', 'xss', 'csrf', '加密', '密码', 'argon2'],
            '算法': ['算法', 'algorithm', '排序', '动态规划', 'dp', '二分', '哈希表', '图论', 'dijkstra', 'bfs', 'dfs'],
            '机器学习': ['机器学习', 'ml', '梯度', 'transformer', 'attention', '过拟合', '神经网络', 'embedding', 'word2vec'],
            '工程': ['git', 'api', 'rest', 'restful', '性能优化', 'profiling', '12-factor', '重构'],
            '数学': ['数学', '概率', '贝叶斯', '线性代数', '矩阵', '复杂度', '大o'],
            '并发': ['并发', '多线程', '多进程', '死锁', 'async', 'await', '协程', '锁', 'mutex'],
            '菩提道': ['菩提', '声闻', '缘觉', '菩萨', '罗汉', '佛果', '十地', '波罗蜜', '四果', '阿罗汉', '辟支佛', '须陀洹', '无穷层级', '果位'],
        }
        
        # 检测查询中的领域关键词
        matched_kws = set()
        for domain_key, keywords in domain_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    matched_kws.add(kw)
        
        # 提取查询中的中文/英文关键词
        cn_raw = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        cn_terms = list(cn_raw)
        for t in cn_raw:
            if len(t) > 3:
                cn_terms.extend([t[i:i+3] for i in range(len(t)-2)])
            if len(t) > 2:
                cn_terms.extend([t[i:i+2] for i in range(len(t)-1)])
        en_terms = [t.lower() for t in re.findall(r'[a-zA-Z]{2,}', text)]
        all_terms = set(cn_terms + en_terms)
        
        with self._lock:
            c = self.conn.cursor()
            c.execute("SELECT id, content, domain, status, embedding FROM cognitive_nodes WHERE embedding IS NOT NULL")
            all_rows = c.fetchall()
        
        tier1 = []  # 领域匹配层
        tier2 = []  # 全局层
        
        for row in all_rows:
            sim = cosine_similarity(emb, row['embedding'])
            row_content = row['content'] or ''
            row_content_lower = row_content.lower()
            content_len = len(row_content)
            
            # 短文本惩罚：nomic-embed-text对短文本产生退化embedding(相似度虚高)
            if content_len < 15:
                sim *= 0.3
            elif content_len < 30:
                sim *= 0.6
            elif content_len < 50:
                sim *= 0.85
            
            # 内容关键词加权：查询中的关键词出现在节点内容中则加分
            content_keyword_boost = 0.0
            for term in en_terms:
                if term in row_content_lower:
                    content_keyword_boost += 0.12
            for term in cn_raw:
                if term in row_content_lower:
                    content_keyword_boost += 0.08
            content_keyword_boost = min(content_keyword_boost, 0.3)
            boosted_sim = min(sim + content_keyword_boost, 1.0)
            
            if boosted_sim < threshold:
                continue
            
            entry = {
                'id': row['id'], 'content': row['content'],
                'domain': row['domain'], 'status': row['status'],
                'similarity': round(boosted_sim, 6)
            }
            
            # 判断是否属于领域匹配层（必须包含领域关键词）
            row_text = ((row['domain'] or '') + ' ' + (row['content'] or '')).lower()
            is_domain_match = any(kw in row_text for kw in matched_kws)
            
            if matched_kws and is_domain_match:
                tier1.append(entry)
            else:
                tier2.append(entry)
        
        tier1.sort(key=lambda x: x['similarity'], reverse=True)
        tier2.sort(key=lambda x: x['similarity'], reverse=True)
        
        # 领域匹配结果优先，剩余位置用全局结果补充
        if matched_kws:
            results = tier1[:limit]
            remaining = limit - len(results)
            if remaining > 0:
                results.extend(tier2[:remaining])
        else:
            # 无领域关键词时走纯embedding排序
            results = (tier1 + tier2)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            results = results[:limit]
        
        return results

    def add_relation(self, n1_id: int, n2_id: int, rel_type: str, confidence: float, desc: str):
        with self._lock:
            c = self.conn.cursor()
            # 避免重复关联
            c.execute("""
                SELECT id FROM node_relations
                WHERE (node1_id=? AND node2_id=?) OR (node1_id=? AND node2_id=?)
            """, (n1_id, n2_id, n2_id, n1_id))
            if c.fetchone():
                return False
            c.execute("""
                INSERT INTO node_relations (node1_id, node2_id, relation_type, confidence, description)
                VALUES (?, ?, ?, ?, ?)
            """, (n1_id, n2_id, rel_type, confidence, desc))
            self.conn.commit()
            return True

    # ---------- 统计 ----------
    def stats(self):
        with self._lock:
            c = self.conn.cursor()
            c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes")
            total_nodes = c.fetchone()['cnt']
            c.execute("SELECT status, COUNT(*) as cnt FROM cognitive_nodes GROUP BY status")
            status_dist = {r['status']: r['cnt'] for r in c.fetchall()}
            c.execute("SELECT COUNT(*) as cnt FROM node_relations")
            total_relations = c.fetchone()['cnt']
            c.execute("SELECT COUNT(DISTINCT domain) as cnt FROM cognitive_nodes")
            total_domains = c.fetchone()['cnt']
            return {
                'total_nodes': total_nodes,
                'total_relations': total_relations,
                'total_domains': total_domains,
                'status_distribution': status_dist,
            }

    def log_growth(self, cycle_id: str, action: str, detail: str,
                   nodes_before: int, nodes_after: int,
                   rels_before: int, rels_after: int):
        with self._lock:
            self.conn.execute("""
                INSERT INTO growth_log (cycle_id, action, detail,
                    nodes_before, nodes_after, relations_before, relations_after)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cycle_id, action, detail, nodes_before, nodes_after, rels_before, rels_after))
            self.conn.commit()

    def get_growth_history(self, limit: int = 10):
        c = self.conn.cursor()
        c.execute("SELECT * FROM growth_log ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in c.fetchall()]


# ==================== 双向拆解引擎 ====================
class DualDirectionDecomposer:
    @staticmethod
    def top_down(question: str, context_nodes: list = None, lattice=None):
        """自上而下拆解：认知格核心驱动，把问题拆解到真实物理路径
        当提供lattice且使用云端后端时，走双模验证流程"""
        messages = cognitive_core.make_top_down_prompt(question, context_nodes)
        if lattice and _is_cloud_backend():
            return verified_llm_call(messages, lattice=lattice, question=question)
        return llm_call(messages)

    @staticmethod
    def bottom_up(known_node: str, known_domain: str = "general", all_domains: list = None):
        """自下而上：认知格核心驱动，从已知节点突破认知边界"""
        messages = cognitive_core.make_bottom_up_prompt(known_node, known_domain, all_domains)
        return llm_call(messages)

    @staticmethod
    def deep_decompose(lattice, question: str, depth: int = 0, max_depth: int = 2, parent_id: int = None):
        """递归拆解：自上而下持续拆解直到可验证或达到最大深度"""
        if depth >= max_depth:
            return []

        # 查找相关已知节点作为上下文
        similar = lattice.find_similar_nodes(question, threshold=0.5, limit=3)
        top_result = DualDirectionDecomposer.top_down(question, similar)
        items = extract_items(top_result)

        all_nodes = []
        for item in items:
            content = item.get('content', '') if isinstance(item, dict) else str(item)
            can_verify = item.get('can_verify', False) if isinstance(item, dict) else False
            domain = item.get('domain', 'general') if isinstance(item, dict) else 'general'

            if not content:
                continue

            status = "known" if can_verify else "hypothesis"
            nid = lattice.add_node(content, domain, status,
                                   source="top_down", depth=depth, parent_id=parent_id)
            if nid:
                all_nodes.append({'id': nid, 'content': content, 'domain': domain, 'status': status})
                if parent_id:
                    lattice.add_relation(parent_id, nid, "decomposed_from", 0.9,
                                         f"深度{depth}拆解")

                # 如果不可验证，继续拆解
                if not can_verify and depth + 1 < max_depth:
                    sub = DualDirectionDecomposer.deep_decompose(
                        lattice, content, depth + 1, max_depth, nid)
                    all_nodes.extend(sub)

        return all_nodes


# ==================== 四向碰撞引擎 ====================
class CollisionEngine:
    """
    四向碰撞：
      上↔下：自上而下拆解结果 vs 自下而上生成的问题
      左↔右：不同领域节点之间的跨域碰撞
    """

    @staticmethod
    def vertical_collide(lattice, top_items: list, bottom_items: list):
        """上下碰撞：拆解假设 vs 已知衍生问题"""
        added = 0
        for t in top_items:
            t_content = t.get("content", "") if isinstance(t, dict) else str(t)
            if not t_content:
                continue
            t_emb = get_embedding(t_content)

            for b in bottom_items:
                b_content = b.get("question", "") if isinstance(b, dict) else str(b)
                if not b_content:
                    continue
                b_emb = get_embedding(b_content)
                sim = cosine_similarity(t_emb, b_emb)
                if sim > Config.COLLISION_THRESHOLD:
                    n1_id = lattice.add_node(t_content, "collision_vertical", "hypothesis",
                                             source="collision")
                    n2_id = lattice.add_node(b_content, "collision_vertical", "hypothesis",
                                             source="collision")
                    if n1_id and n2_id:
                        if lattice.add_relation(n1_id, n2_id, "vertical_overlap", sim,
                                                f"上下碰撞 相似度:{sim:.3f}"):
                            print(f"  [碰撞↕] {t_content[:30]}... ↔ {b_content[:30]}... ({sim:.3f})")
                            added += 1
        return added

    @staticmethod
    def cross_domain_collide(lattice):
        """左右碰撞：扫描不同领域节点，寻找跨域关联
        为防止关系爆炸，每次最多检查 max_pairs 个领域对"""
        domains = lattice.get_all_domains()
        if len(domains) < 2:
            return 0

        # 限制碰撞范围：随机采样领域对，防止O(n²)爆炸
        max_pairs = 15
        all_pairs = []
        for i, d1 in enumerate(domains):
            for d2 in domains[i+1:]:
                all_pairs.append((d1, d2))
        if len(all_pairs) > max_pairs:
            all_pairs = random.sample(all_pairs, max_pairs)

        added = 0
        for d1, d2 in all_pairs:
            try:
                nodes1 = lattice.get_nodes_by_domain(d1, limit=8)
                nodes2 = lattice.get_nodes_by_domain(d2, limit=8)

                for n1 in nodes1:
                    if not n1.get('embedding'):
                        continue
                    for n2 in nodes2:
                        if not n2.get('embedding'):
                            continue
                        sim = cosine_similarity(n1['embedding'], n2['embedding'])
                        if sim > Config.CROSS_DOMAIN_THRESHOLD:
                            if lattice.add_relation(n1['id'], n2['id'], "cross_domain", sim,
                                                    f"跨域({d1}↔{d2}) 相似度:{sim:.3f}"):
                                added += 1
            except Exception as e:
                print(f"  [碰撞↔] 领域对({d1}↔{d2})碰撞失败: {e}")
                continue
        return added


# ==================== 自成长引擎 ====================
class SelfGrowthEngine:
    """
    自成长核心循环：
    1. 从DB取已知节点 → 自下而上生成新问题
    2. 对新问题 → 自上而下拆解至已知
    3. 上下碰撞 → 发现重叠
    4. 跨域碰撞 → 发现跨领域关联
    5. 记录成长日志
    """

    def __init__(self, lattice: CognitiveLattice):
        self.lattice = lattice
        self._running = False

    def run_one_cycle(self):
        """执行一次完整的自成长循环"""
        cycle_id = str(uuid.uuid4())[:8]
        stats_before = self.lattice.stats()
        print(f"\n{'='*60}")
        print(f"  自成长循环 [{cycle_id}] 开始")
        print(f"  当前认知网络：{stats_before['total_nodes']}节点 / "
              f"{stats_before['total_relations']}关联 / "
              f"{stats_before['total_domains']}领域")
        print(f"{'='*60}")

        # 步骤1：取已知节点
        known_nodes = self.lattice.get_random_known_nodes(Config.GROWTH_BATCH_SIZE)
        if not known_nodes:
            print("  [!] 无已知节点可供成长，请先录入种子节点")
            return

        all_bottom_items = []
        all_top_items = []

        for node in known_nodes:
            self.lattice.touch_node(node['id'])

            # 步骤2：自下而上 — 从已知生成新问题（注入认知格核心）
            print(f"\n  [↑自下而上] 从「{node['content'][:40]}...」出发")
            all_domains = self.lattice.get_all_domains()
            bottom_result = DualDirectionDecomposer.bottom_up(
                node['content'], node.get('domain', 'general'), all_domains)
            bottom_items = extract_items(bottom_result)
            all_bottom_items.extend(bottom_items)

            # 为每个新问题存入假设节点
            for item in bottom_items:
                q = item.get('question', '') if isinstance(item, dict) else str(item)
                d = item.get('potential_domain', 'general') if isinstance(item, dict) else 'general'
                if q:
                    nid = self.lattice.add_node(q, d, "hypothesis",
                                                source="bottom_up", parent_id=node['id'])
                    if nid:
                        self.lattice.add_relation(node['id'], nid, "generated_question", 0.7,
                                                  "自下而上生成")

            # 步骤3：自上而下 — 取一个新问题深度拆解
            if bottom_items:
                target_q = bottom_items[0]
                target_content = target_q.get('question', '') if isinstance(target_q, dict) else str(target_q)
                if target_content:
                    print(f"  [↓自上而下] 拆解「{target_content[:40]}...」")
                    decomposed = DualDirectionDecomposer.deep_decompose(
                        self.lattice, target_content,
                        max_depth=Config.MAX_DEPTH_PER_CYCLE, parent_id=node['id'])
                    for d_node in decomposed:
                        all_top_items.append(d_node)

        # 步骤4：上下碰撞
        print(f"\n  [碰撞↕] 上下碰撞检测中... (上:{len(all_top_items)} × 下:{len(all_bottom_items)})")
        v_added = CollisionEngine.vertical_collide(self.lattice, all_top_items, all_bottom_items)

        # 步骤5：跨域碰撞
        print(f"  [碰撞↔] 跨域碰撞检测中...")
        h_added = CollisionEngine.cross_domain_collide(self.lattice)

        # 记录成长
        stats_after = self.lattice.stats()
        self.lattice.log_growth(
            cycle_id, "full_cycle",
            f"自下而上:{len(all_bottom_items)}问题 自上而下:{len(all_top_items)}拆解 "
            f"上下碰撞:{v_added} 跨域碰撞:{h_added}",
            stats_before['total_nodes'], stats_after['total_nodes'],
            stats_before['total_relations'], stats_after['total_relations']
        )

        new_nodes = stats_after['total_nodes'] - stats_before['total_nodes']
        new_rels = stats_after['total_relations'] - stats_before['total_relations']
        print(f"\n  循环 [{cycle_id}] 完成：新增 {new_nodes} 节点, {new_rels} 关联")
        print(f"  认知网络现状：{stats_after['total_nodes']}节点 / "
              f"{stats_after['total_relations']}关联 / "
              f"{stats_after['total_domains']}领域")
        print(f"  状态分布：{stats_after['status_distribution']}")
        return stats_after

    def start_background_growth(self, interval: int = None):
        """后台自动成长（守护线程）"""
        interval = interval or Config.SELF_GROWTH_INTERVAL
        self._running = True

        def loop():
            while self._running:
                try:
                    self.run_one_cycle()
                except Exception as e:
                    print(f"  [自成长异常] {e}")
                time.sleep(interval)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        print(f"  [自成长] 后台成长已启动，间隔 {interval}秒")

    def stop_background_growth(self):
        self._running = False
        print("  [自成长] 后台成长已停止")

    # ===== F7: 离线成长模式（纯proven embedding碰撞，不依赖LLM） =====
    def run_offline_cycle(self):
        """F7: 离线成长循环 — 纯proven节点embedding碰撞发现新关联
        
        不调用任何LLM，仅利用已有proven节点的embedding进行：
        1. 跨域碰撞：不同领域proven节点寻找深层关联
        2. 孤立节点连接：为无关联的proven节点寻找最近邻
        3. 关系强度更新：基于新碰撞结果增强关系网络
        """
        cycle_id = str(uuid.uuid4())[:8]
        stats_before = self.lattice.stats()
        print(f"\n{'='*60}")
        print(f"  离线成长循环 [{cycle_id}] (纯embedding碰撞，无LLM)")
        print(f"  当前：{stats_before['total_nodes']}节点 / "
              f"{stats_before['total_relations']}关联")
        print(f"{'='*60}")

        new_relations = 0

        # 步骤1: 跨域碰撞（扩大范围）
        print(f"  [离线↔] 跨域proven碰撞...")
        h_added = self._offline_cross_domain_collide()
        new_relations += h_added

        # 步骤2: 孤立节点连接
        print(f"  [离线🔗] 孤立proven节点连接...")
        o_added = self._connect_orphan_nodes()
        new_relations += o_added

        # 步骤3: 相似proven节点聚类发现
        print(f"  [离线📊] proven节点聚类发现...")
        c_added = self._cluster_proven_nodes()
        new_relations += c_added

        # 记录
        stats_after = self.lattice.stats()
        self.lattice.log_growth(
            cycle_id, "offline_cycle",
            f"离线碰撞: 跨域{h_added} 孤立连接{o_added} 聚类{c_added}",
            stats_before['total_nodes'], stats_after['total_nodes'],
            stats_before['total_relations'], stats_after['total_relations']
        )

        new_rels = stats_after['total_relations'] - stats_before['total_relations']
        print(f"\n  离线循环 [{cycle_id}] 完成：新增 {new_rels} 关联")
        return {
            "cycle_id": cycle_id,
            "cross_domain": h_added,
            "orphan_connected": o_added,
            "clustered": c_added,
            "total_new_relations": new_rels,
        }

    def _offline_cross_domain_collide(self):
        """仅用proven节点做跨域碰撞，阈值略低以发现更多关联"""
        domains = self.lattice.get_all_domains()
        if len(domains) < 2:
            return 0

        max_pairs = 25  # 离线模式可以更多
        all_pairs = []
        for i, d1 in enumerate(domains):
            for d2 in domains[i+1:]:
                all_pairs.append((d1, d2))
        if len(all_pairs) > max_pairs:
            all_pairs = random.sample(all_pairs, max_pairs)

        added = 0
        lower_threshold = max(Config.CROSS_DOMAIN_THRESHOLD - 0.05, 0.3)

        for d1, d2 in all_pairs:
            try:
                nodes1 = self.lattice.get_nodes_by_domain(d1, limit=15)
                nodes2 = self.lattice.get_nodes_by_domain(d2, limit=15)
                # 只取proven节点
                nodes1 = [n for n in nodes1 if n.get('status') == 'proven' and n.get('embedding')]
                nodes2 = [n for n in nodes2 if n.get('status') == 'proven' and n.get('embedding')]

                for n1 in nodes1:
                    for n2 in nodes2:
                        sim = cosine_similarity(n1['embedding'], n2['embedding'])
                        if sim > lower_threshold:
                            if self.lattice.add_relation(
                                n1['id'], n2['id'], "offline_cross_domain", sim,
                                f"离线跨域({d1}↔{d2}) {sim:.3f}"):
                                added += 1
            except Exception as e:
                continue
        print(f"    跨域碰撞: {added} 新关联")
        return added

    def _connect_orphan_nodes(self):
        """为没有任何关联的proven节点寻找最近邻"""
        with self.lattice._lock:
            cursor = self.lattice.conn.execute("""
                SELECT cn.id, cn.content, cn.domain, cn.embedding
                FROM cognitive_nodes cn
                WHERE cn.status = 'proven' AND cn.embedding IS NOT NULL
                AND cn.id NOT IN (
                    SELECT node1_id FROM node_relations
                    UNION
                    SELECT node2_id FROM node_relations
                )
                LIMIT 30
            """)
            orphans = [dict(row) for row in cursor.fetchall()]

        if not orphans:
            print(f"    无孤立proven节点")
            return 0

        added = 0
        for orphan in orphans:
            # 寻找最近邻
            similar = self.lattice.find_similar_nodes(
                orphan['content'], threshold=0.3, limit=3)
            for s in similar:
                if s['id'] != orphan['id']:
                    if self.lattice.add_relation(
                        orphan['id'], s['id'], "offline_nearest", s['similarity'],
                        f"离线孤立连接 {s['similarity']:.3f}"):
                        added += 1
                        break  # 每个孤立节点只连接最相似的一个
        print(f"    孤立连接: {added}/{len(orphans)} 节点")
        return added

    def _cluster_proven_nodes(self):
        """在同一领域内发现高相似度proven节点对，强化关联"""
        domains = self.lattice.get_all_domains()
        added = 0

        for domain in random.sample(domains, min(5, len(domains))):
            nodes = self.lattice.get_nodes_by_domain(domain, limit=20)
            proven = [n for n in nodes if n.get('status') == 'proven' and n.get('embedding')]

            for i in range(len(proven)):
                for j in range(i + 1, len(proven)):
                    sim = cosine_similarity(proven[i]['embedding'], proven[j]['embedding'])
                    if sim > 0.7:  # 高阈值：同领域强关联
                        if self.lattice.add_relation(
                            proven[i]['id'], proven[j]['id'],
                            "offline_cluster", sim,
                            f"离线聚类({domain}) {sim:.3f}"):
                            added += 1
        print(f"    聚类发现: {added} 强关联")
        return added

    def start_offline_growth(self, interval: int = 300):
        """启动离线后台成长（不需要LLM，纯embedding碰撞）"""
        self._running = True

        def loop():
            while self._running:
                try:
                    self.run_offline_cycle()
                except Exception as e:
                    print(f"  [离线成长异常] {e}")
                time.sleep(interval)

        t = threading.Thread(target=loop, daemon=True, name="offline_growth")
        t.start()
        print(f"  [离线成长] 后台离线成长已启动，间隔 {interval}秒")
        return {"status": "started", "mode": "offline", "interval": interval}


# ==================== 人机共生 ====================
class HumanNodeIngestion:
    @staticmethod
    def ingest_human_node(lattice):
        content = input("请输入你领域内具现化的真实小节点（或实践反馈）：").strip()
        if not content:
            print("输入为空，取消")
            return
        domain = input("领域（例如：摆摊/量子物理/烹饪/代码实现）：").strip() or "general"
        nid = lattice.add_node(content, domain, "known", source="human_practice")
        if nid:
            # 自动与已有节点碰撞
            similar = lattice.find_similar_nodes(content, threshold=Config.CROSS_DOMAIN_THRESHOLD)
            for s in similar:
                if s['id'] != nid:
                    lattice.add_relation(nid, s['id'], "human_linked", s['similarity'],
                                         f"人类节点自动关联 ({s['similarity']:.3f})")
                    print(f"  [关联] → {s['content'][:40]}... ({s['similarity']:.3f})")

    @staticmethod
    def batch_ingest(lattice, nodes: list):
        """批量录入节点：[{"content": "...", "domain": "..."}]"""
        count = 0
        for n in nodes:
            nid = lattice.add_node(
                n.get('content', ''), n.get('domain', 'general'),
                n.get('status', 'known'), n.get('source', 'seed'),
                silent=True)
            if nid:
                count += 1
        print(f"  [批量录入] 成功 {count}/{len(nodes)} 个节点")
        return count


class PracticeListGenerator:
    @staticmethod
    def generate_practice_list(lattice, unknown_node: str):
        # 寻找相关已知节点作为参考
        related = lattice.find_similar_nodes(unknown_node, threshold=0.5, limit=3)
        # 识别领域
        domain = "general"
        if related:
            domain = related[0].get('domain', 'general')

        messages = cognitive_core.make_practice_list_prompt(unknown_node, domain, related)
        result = llm_call(messages)
        items = extract_items(result)

        print("\n  实践清单：")
        if items:
            for i, item in enumerate(items, 1):
                if isinstance(item, dict):
                    print(f"  {i}. {item.get('step', item)}")
                    print(f"     预期：{item.get('expected', '?')}")
                    print(f"     验证：{item.get('verify_method', '?')}")
                    print(f"     难度：{item.get('difficulty', '?')}")
                else:
                    print(f"  {i}. {item}")
        else:
            raw = result.get('raw', result) if isinstance(result, dict) else result
            print(f"  {raw}")

        # 存入实践记录
        node_matches = lattice.find_similar_nodes(unknown_node, threshold=0.6, limit=1)
        if node_matches:
            nid = node_matches[0]['id']
            with lattice._lock:
                lattice.conn.execute(
                    "INSERT INTO practice_records (node_id, practice_content) VALUES (?, ?)",
                    (nid, json.dumps(items, ensure_ascii=False)))
                lattice.conn.commit()

        return items


# ==================== 种子知识：代码领域真实节点 ====================
SEED_CODING_NODES = [
    # --- 编程语言基础（真实可实践节点）---
    {"content": "变量是对内存地址的命名引用，赋值操作将值绑定到变量名", "domain": "编程基础"},
    {"content": "函数是将一组语句封装为可复用单元的机制，通过参数接收输入，通过返回值输出结果", "domain": "编程基础"},
    {"content": "条件分支(if/else)根据布尔表达式的真假选择执行路径", "domain": "编程基础"},
    {"content": "循环(for/while)通过重复执行代码块处理批量数据或等待条件满足", "domain": "编程基础"},
    {"content": "递归是函数调用自身来解决问题的方法，必须有基线条件防止无限递归", "domain": "编程基础"},
    {"content": "类型系统约束变量可存储的值的种类，静态类型在编译期检查，动态类型在运行时检查", "domain": "编程基础"},

    # --- 数据结构（真实可验证节点）---
    {"content": "数组/列表通过连续内存存储元素，按索引O(1)访问，插入删除O(n)", "domain": "数据结构"},
    {"content": "哈希表通过哈希函数将键映射到桶，平均O(1)查找，最坏O(n)", "domain": "数据结构"},
    {"content": "栈是后进先出(LIFO)结构，函数调用栈就是典型应用", "domain": "数据结构"},
    {"content": "队列是先进先出(FIFO)结构，消息队列和任务调度依赖此特性", "domain": "数据结构"},
    {"content": "树结构通过父子关系组织数据，二叉搜索树支持O(log n)查找", "domain": "数据结构"},
    {"content": "图结构用节点和边表示多对多关系，适合建模网络、路径、依赖关系", "domain": "数据结构"},

    # --- 软件工程实践（真实可操作节点）---
    {"content": "版本控制(Git)通过记录每次变更的快照实现代码历史追溯和多人协作", "domain": "软件工程"},
    {"content": "单元测试验证单个函数/方法的行为是否符合预期，是代码质量的第一道防线", "domain": "软件工程"},
    {"content": "代码审查(Code Review)通过同行检查发现逻辑错误和设计缺陷", "domain": "软件工程"},
    {"content": "持续集成(CI)在每次提交后自动运行测试，尽早发现集成问题", "domain": "软件工程"},
    {"content": "重构是在不改变外部行为的前提下改善代码内部结构", "domain": "软件工程"},
    {"content": "关注点分离原则要求每个模块只负责一个明确的职责", "domain": "软件工程"},

    # --- 架构与设计模式（真实可实践节点）---
    {"content": "分层架构将系统分为表示层、业务逻辑层、数据访问层，每层只依赖下层", "domain": "架构设计"},
    {"content": "依赖注入通过外部传入依赖对象而非内部创建，实现松耦合", "domain": "架构设计"},
    {"content": "观察者模式通过发布-订阅机制实现对象间一对多的松耦合通知", "domain": "架构设计"},
    {"content": "REST API 通过 HTTP 动词(GET/POST/PUT/DELETE)对资源进行 CRUD 操作", "domain": "架构设计"},
    {"content": "数据库索引通过B+树等结构加速查询，但会增加写入开销和存储空间", "domain": "架构设计"},

    # --- 调试与问题解决（真实实践节点）---
    {"content": "调试的第一步是稳定复现问题，不能复现的bug无法可靠修复", "domain": "调试实践"},
    {"content": "二分法调试通过逐步缩小问题范围定位根因，比逐行排查效率高", "domain": "调试实践"},
    {"content": "日志是生产环境调试的主要手段，需要在关键路径记录足够的上下文信息", "domain": "调试实践"},
    {"content": "异常处理应当捕获具体异常类型而非笼统捕获所有异常", "domain": "调试实践"},
    {"content": "性能优化前必须先用profiler定位瓶颈，避免过早优化", "domain": "调试实践"},

    # --- Python 实践（真实可执行节点）---
    {"content": "Python列表推导式[expr for x in iterable if cond]是创建列表的简洁高效方式", "domain": "Python"},
    {"content": "Python装饰器@decorator本质是接收函数返回函数的高阶函数", "domain": "Python"},
    {"content": "Python的with语句通过上下文管理器确保资源(文件/连接)正确释放", "domain": "Python"},
    {"content": "Python虚拟环境(venv)隔离项目依赖，避免不同项目间的包版本冲突", "domain": "Python"},
    {"content": "SQLite是Python内置的嵌入式关系数据库，无需单独安装服务端", "domain": "Python"},
    {"content": "Python的GIL(全局解释器锁)限制同一时刻只有一个线程执行字节码", "domain": "Python"},

    # --- AI/ML 基础（真实可验证节点）---
    {"content": "向量嵌入(Embedding)将文本映射到高维向量空间，语义相似的文本距离更近", "domain": "AI基础"},
    {"content": "余弦相似度通过计算两个向量夹角的余弦值衡量方向相似性，范围[-1,1]", "domain": "AI基础"},
    {"content": "大语言模型通过预测下一个token生成文本，本质是条件概率分布", "domain": "AI基础"},
    {"content": "Prompt Engineering通过精心设计输入提示词引导LLM产生期望输出", "domain": "AI基础"},
    {"content": "RAG(检索增强生成)先检索相关文档再让LLM基于检索结果生成回答", "domain": "AI基础"},

    # --- 网络与系统（真实可操作节点）---
    {"content": "HTTP是无状态协议，每次请求独立，服务器不保留客户端状态", "domain": "网络系统"},
    {"content": "TCP通过三次握手建立可靠连接，保证数据有序到达", "domain": "网络系统"},
    {"content": "进程拥有独立地址空间，线程共享进程的地址空间但有独立执行栈", "domain": "网络系统"},
    {"content": "缓存通过保存计算结果避免重复计算，用空间换时间", "domain": "网络系统"},
]


def seed_database(lattice: CognitiveLattice):
    """将种子知识节点录入数据库（仅首次运行时）"""
    stats = lattice.stats()
    if stats['total_nodes'] > 0:
        return  # 已有数据，不重复录入
    print("\n  [初始化] 录入代码领域种子知识节点...")
    HumanNodeIngestion.batch_ingest(lattice, SEED_CODING_NODES)
    # 初始跨域碰撞
    print("  [初始化] 执行初始跨域碰撞...")
    CollisionEngine.cross_domain_collide(lattice)
    print("  [初始化] 种子知识录入完成\n")


# ==================== 认知网络可视化（文本） ====================
def print_network_status(lattice: CognitiveLattice):
    stats = lattice.stats()
    print(f"\n{'='*60}")
    print(f"  认知网络状态")
    print(f"{'='*60}")
    print(f"  总节点数：{stats['total_nodes']}")
    print(f"  总关联数：{stats['total_relations']}")
    print(f"  覆盖领域：{stats['total_domains']}")
    print(f"  状态分布：")
    for status, count in stats['status_distribution'].items():
        bar = "█" * min(count, 40)
        print(f"    {status:12s} [{count:4d}] {bar}")

    domains = lattice.get_all_domains()
    print(f"\n  领域列表：")
    for d in domains:
        nodes = lattice.get_nodes_by_domain(d, limit=100)
        print(f"    [{d}] {len(nodes)} 个节点")
    print(f"{'='*60}")


def print_growth_history(lattice: CognitiveLattice):
    history = lattice.get_growth_history(10)
    if not history:
        print("  暂无成长记录")
        return
    print(f"\n{'='*60}")
    print(f"  最近成长记录")
    print(f"{'='*60}")
    for h in history:
        n_delta = h['nodes_after'] - h['nodes_before']
        r_delta = h['relations_after'] - h['relations_before']
        print(f"  [{h['created_at']}] 循环:{h['cycle_id']}")
        print(f"    {h['detail']}")
        print(f"    变化：节点 +{n_delta}, 关联 +{r_delta}")
    print(f"{'='*60}")


# ==================== 认知烙印（Cognitive Imprinting） ====================
def cognitive_imprint(lattice: CognitiveLattice):
    """
    认知烙印：首次部署时，用认知格哲学初始化模型的思维模式。
    这不是简单的系统提示词，而是让模型内化四向碰撞思维范式，
    并用自己的理解重述核心原则，验证哲学已植入。
    """
    # 检查是否已完成烙印
    c = lattice.conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM growth_log WHERE action = 'cognitive_imprint'")
    if c.fetchone()['cnt'] > 0:
        print("  [认知核心] 认知格哲学已植入 ✓")
        return True

    print("\n" + "=" * 60)
    print("  ★ 认知烙印（Cognitive Imprinting）★")
    print("  正在将认知格哲学植入模型灵魂...")
    print("=" * 60)

    stats_before = lattice.stats()

    # 执行认知烙印
    result = llm_call(cognitive_core.COGNITIVE_IMPRINT_PROMPT)

    if isinstance(result, dict) and "error" in result:
        print(f"  [!] 认知烙印失败: {result['error']}")
        print("  [!] 请检查 LLM 后端连接，然后重新运行")
        return False

    # 展示模型的认知烙印回应
    raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
    print(f"\n  [认知核心回应]\n")
    for line in raw.split('\n'):
        print(f"    {line}")

    # 记录烙印完成
    stats_after = lattice.stats()
    lattice.log_growth(
        "imprint", "cognitive_imprint",
        "认知格哲学植入完成：四向碰撞思维范式已内化",
        stats_before['total_nodes'], stats_after['total_nodes'],
        stats_before['total_relations'], stats_after['total_relations']
    )

    print(f"\n  ★ 认知烙印完成 — 模型现在以认知格范式思考 ★")
    print("=" * 60)
    return True


# ==================== 主程序 ====================
def main():
    print("=" * 60)
    b = Config.backend()
    print("  AGI v13.3 Cognitive Lattice")
    print("  认知格核心 + 无限自成长 + 四向碰撞 + 人机共生")
    print(f"  后端：{b['name']} ({b['model']})")
    print("=" * 60)
    print("\n认知格核心原理：")
    print("  ↓ 自上而下拆解未知 → 抵达「真实物理路径」（可实践验证）")
    print("  ↑ 自下而上从已知合成 → 突破认知边界")
    print("  ↔ 跨域碰撞 → 发现不同领域的隐藏重叠")
    print("  ⟳ 碰撞循环 → 新节点参与下一轮 → 无限自成长")
    print("  人类具现化：领域自洽实践者录入真实节点 → AI 梳理清单 → 人类验证")
    print(f"\n当前后端: {Config.ACTIVE_BACKEND} → 修改 Config.ACTIVE_BACKEND 切换")
    print("可用后端: " + " / ".join(BACKENDS.keys()))
    print("\n支持命令：")
    print("  直接输入问题     → 认知格四向碰撞处理")
    print("  具现化节点       → 录入人类真实实践节点")
    print("  生成实践清单     → 为未知节点生成验证步骤")
    print("  认知状态         → 查看认知网络统计")
    print("  成长日志         → 查看成长历史")
    print("  自成长           → 手动触发一次自成长循环")
    print("  自动成长         → 启动后台自动成长")
    print("  停止成长         → 停止后台自动成长")
    print("  认知烙印         → 重新执行认知格哲学植入")
    print("  搜索 <关键词>    → 语义搜索认知网络")
    print("  exit             → 退出\n")

    lattice = CognitiveLattice()
    seed_database(lattice)

    # ★ 认知烙印：首次运行时将认知格哲学植入模型 ★
    cognitive_imprint(lattice)

    growth_engine = SelfGrowthEngine(lattice)

    while True:
        try:
            q = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() in ['exit', 'quit', 'q']:
            break

        # ---------- 具现化节点 ----------
        if q == "具现化节点":
            HumanNodeIngestion.ingest_human_node(lattice)
            continue

        # ---------- 生成实践清单 ----------
        if q == "生成实践清单":
            node = input("输入要验证的未知节点/假设：").strip()
            if node:
                PracticeListGenerator.generate_practice_list(lattice, node)
            continue

        # ---------- 认知状态 ----------
        if q == "认知状态":
            print_network_status(lattice)
            continue

        # ---------- 成长日志 ----------
        if q == "成长日志":
            print_growth_history(lattice)
            continue

        # ---------- 自成长 ----------
        if q == "自成长":
            growth_engine.run_one_cycle()
            continue

        # ---------- 自动成长 ----------
        if q == "自动成长":
            try:
                interval = int(input("成长间隔（秒，默认300）：").strip() or "300")
            except ValueError:
                interval = 300
            growth_engine.start_background_growth(interval)
            continue

        # ---------- 停止成长 ----------
        if q == "停止成长":
            growth_engine.stop_background_growth()
            continue

        # ---------- 认知烙印 ----------
        if q == "认知烙印":
            # 清除旧烙印记录，重新执行
            with lattice._lock:
                lattice.conn.execute("DELETE FROM growth_log WHERE action = 'cognitive_imprint'")
                lattice.conn.commit()
            cognitive_imprint(lattice)
            continue

        # ---------- 语义搜索 ----------
        if q.startswith("搜索"):
            keyword = q[2:].strip()
            if keyword:
                results = lattice.find_similar_nodes(keyword, threshold=0.4, limit=10)
                if results:
                    print(f"\n  搜索「{keyword}」的结果：")
                    for r in results:
                        print(f"  [{r['domain']:8s}] [{r['status']:10s}] "
                              f"{r['content'][:50]}  (相似度:{r['similarity']:.3f})")
                else:
                    print("  未找到相关节点")
            continue

        # ---------- 默认：双向拆解 + 碰撞 ----------
        print(f"\n  处理问题：{q}")

        # 1. 查找相关已知节点
        related = lattice.find_similar_nodes(q, threshold=0.4, limit=5)
        if related:
            print(f"\n  [关联] 找到 {len(related)} 个相关已知节点：")
            for r in related:
                print(f"    [{r['domain']}] {r['content'][:50]}... ({r['similarity']:.3f})")

        # 2. 自上而下拆解
        print(f"\n  [↓自上而下] 拆解中...")
        top_result = DualDirectionDecomposer.top_down(q, related)
        top_items = extract_items(top_result)
        for item in top_items:
            content = item.get('content', '') if isinstance(item, dict) else str(item)
            can_v = item.get('can_verify', False) if isinstance(item, dict) else False
            domain = item.get('domain', 'general') if isinstance(item, dict) else 'general'
            if content:
                status = "known" if can_v else "hypothesis"
                lattice.add_node(content, domain, status, source="top_down")

        # 3. 自下而上（从相关已知节点或随机已知节点出发，注入认知格核心）
        print(f"\n  [↑自下而上] 生成新问题...")
        known_for_bu = related[:2] if related else lattice.get_random_known_nodes(2)
        all_domains = lattice.get_all_domains()
        all_bottom_items = []
        for kn in known_for_bu:
            content = kn.get('content', '')
            domain = kn.get('domain', 'general')
            if content:
                bottom_result = DualDirectionDecomposer.bottom_up(content, domain, all_domains)
                items = extract_items(bottom_result)
                all_bottom_items.extend(items)
                for item in items:
                    bq = item.get('question', '') if isinstance(item, dict) else str(item)
                    bd = item.get('potential_domain', 'general') if isinstance(item, dict) else 'general'
                    if bq:
                        lattice.add_node(bq, bd, "hypothesis", source="bottom_up")

        # 4. 上下碰撞
        print(f"\n  [碰撞↕] 上下碰撞检测...")
        v_added = CollisionEngine.vertical_collide(lattice, top_items, all_bottom_items)
        print(f"  上下碰撞新增关联：{v_added}")

        # 5. 跨域碰撞
        print(f"  [碰撞↔] 跨域碰撞检测...")
        h_added = CollisionEngine.cross_domain_collide(lattice)
        print(f"  跨域碰撞新增关联：{h_added}")

        # 6. 显示当前状态摘要
        stats = lattice.stats()
        print(f"\n  当前认知网络：{stats['total_nodes']}节点 / "
              f"{stats['total_relations']}关联 / {stats['total_domains']}领域")

    # 退出前保存
    print("\n  认知网络已保存。再见！")
    lattice.conn.close()


if __name__ == "__main__":
    main()
