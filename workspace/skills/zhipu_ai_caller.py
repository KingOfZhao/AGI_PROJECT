#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智谱 AI 调用技能 — 让本地模型借用云端算力

功能：
  1. 多模型支持: glm-4-flash(快速) / glm-4-plus(强力) / glm-4-long(长文) / glm-5(旗舰)
  2. 任务委托: 代码生成 / 深度推理 / 翻译 / 摘要 / 分析 / 自由对话
  3. 本地验证: 云端结果经本地Ollama校验，标注可信度
  4. 多轮对话: 支持上下文连续对话
  5. 安全机制: API Key 安全管理 / 请求限速 / Token 统计

架构哲学：
  本地模型 = 大脑（决策+校验）
  智谱 AI  = 外脑（复杂推理+海量知识）
  本地模型决定何时调用、如何校验、是否采纳
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any

# ==================== 配置 ====================

# 智谱 AI 模型能力矩阵
ZHIPU_MODELS = {
    "glm-4-flash": {
        "name": "GLM-4 Flash",
        "desc": "快速响应，适合简单任务",
        "api_type": "openai",
        "max_tokens": 4096,
        "cost_per_1k": 0.001,  # 元/千token (极低)
        "strengths": ["速度快", "成本低", "日常对话"],
    },
    "glm-4-air": {
        "name": "GLM-4 Air",
        "desc": "均衡模型，性价比高",
        "api_type": "openai",
        "max_tokens": 8192,
        "cost_per_1k": 0.005,
        "strengths": ["均衡", "代码生成", "逻辑推理"],
    },
    "glm-4-plus": {
        "name": "GLM-4 Plus",
        "desc": "高性能模型，复杂推理",
        "api_type": "openai",
        "max_tokens": 8192,
        "cost_per_1k": 0.05,
        "strengths": ["复杂推理", "代码优化", "深度分析"],
    },
    "glm-4-long": {
        "name": "GLM-4 Long",
        "desc": "长上下文模型，128K窗口",
        "api_type": "openai",
        "max_tokens": 4096,
        "cost_per_1k": 0.001,
        "strengths": ["超长文本", "文档分析", "代码审查"],
    },
    "glm-5": {
        "name": "GLM-5 旗舰",
        "desc": "最强模型，Anthropic协议",
        "api_type": "anthropic",
        "max_tokens": 8192,
        "cost_per_1k": 0.05,
        "strengths": ["最强推理", "复杂编程", "创造性任务"],
    },
    "GLM-4.5-Air": {
        "name": "GLM-4.5 Air",
        "desc": "新一代均衡模型，强编码能力",
        "api_type": "openai",
        "max_tokens": 8192,
        "cost_per_1k": 0.005,
        "strengths": ["代码生成", "逻辑推理", "性价比高", "动作规划"],
    },
    "GLM-4.7": {
        "name": "GLM-4.7",
        "desc": "最新高性能模型，复杂任务专用",
        "api_type": "openai",
        "max_tokens": 16384,
        "cost_per_1k": 0.05,
        "strengths": ["复杂编程", "架构设计", "深度推理", "文件产出"],
    },
}

# 任务类型 → 推荐模型映射
TASK_MODEL_MAP = {
    "code_gen":     "GLM-4.5-Air",     # 代码生成 → 4.5-Air强编码
    "code_review":  "glm-4-long",      # 代码审查 → 长上下文
    "reasoning":    "GLM-4.7",         # 深度推理 → 4.7最新高性能
    "translate":    "glm-4-flash",     # 翻译 → 快速模型
    "summarize":    "glm-4-flash",     # 摘要 → 快速模型
    "analyze":      "GLM-4.7",         # 分析 → 4.7最新高性能
    "long_doc":     "glm-4-long",      # 长文档 → 长上下文
    "creative":     "glm-5",           # 创造性 → 旗舰
    "chat":         "glm-4-flash",     # 日常对话 → 快速
    "complex":      "glm-5",           # 复杂任务 → 旗舰
    "action_plan":  "GLM-4.5-Air",     # 动作规划 → 4.5-Air精准JSON
    "code_execute": "GLM-4.7",         # 代码执行产出 → 4.7最强编码
}

# 任务系统提示词
TASK_SYSTEM_PROMPTS = {
    "code_gen": "你是一位资深软件工程师。请生成高质量、可运行的代码。包含必要注释、错误处理和类型标注。",
    "code_review": "你是一位代码审查专家。请仔细审查代码，指出潜在问题、安全隐患、性能瓶颈，并给出改进建议。",
    "reasoning": "你是一位严谨的逻辑推理专家。请逐步推理，每步给出依据。区分已知事实和推测，标注置信度。",
    "translate": "你是一位专业翻译。请在保持原意的同时，使译文流畅自然。技术术语保留英文原文。",
    "summarize": "你是一位文档摘要专家。请提炼核心要点，按重要性排序，保持简洁且不丢失关键信息。",
    "analyze": "你是一位系统分析师。请进行深入分析，识别核心问题、因果关系、潜在风险和可行方案。",
    "creative": "你是一位富有创造力的思考者。请提供新颖独到的见解和方案，突破常规思维框架。",
    "chat": "你是一位知识渊博的助手。请准确、简洁地回答问题。不确定的内容请明确标注。",
}

# ==================== 统计追踪 ====================
_usage_stats = {
    "total_calls": 0,
    "total_tokens": 0,
    "total_cost": 0.0,
    "by_model": {},
    "by_task": {},
    "errors": 0,
    "last_call": None,
}
_conversations = {}  # session_id -> messages list
_session_meta = {}   # session_id -> {"token_est": int, "consecutive_failures": int, "resets": int}

# 会话自动重置阈值
SESSION_TOKEN_LIMIT = 8000       # 估算token超过此值时自动重置
SESSION_MAX_FAILURES = 3          # 连续验证失败超过此值时强制重置
SESSION_KEEP_LAST_N = 2           # 重置时保留最近N轮对话


def _estimate_session_tokens(session_id: str) -> int:
    """估算会话累计token数"""
    msgs = _conversations.get(session_id, [])
    return sum(len(m.get("content", "")) // 2 for m in msgs)


def _auto_reset_session(session_id: str, reason: str = "") -> bool:
    """智能会话重置：清除历史但保留最近对话，防止幻觉累积
    
    参考: LangGraph state reset + Zep smart context retrieval
    """
    msgs = _conversations.get(session_id, [])
    if not msgs:
        return False

    # 保留最近N轮(2*N条消息)
    keep_count = SESSION_KEEP_LAST_N * 2
    if len(msgs) > keep_count:
        _conversations[session_id] = msgs[-keep_count:]
    else:
        _conversations[session_id] = []

    # 更新元数据
    meta = _session_meta.setdefault(session_id, {"token_est": 0, "consecutive_failures": 0, "resets": 0})
    meta["resets"] += 1
    meta["token_est"] = _estimate_session_tokens(session_id)
    meta["consecutive_failures"] = 0

    print(f"  [智谱会话重置] session={session_id} reason={reason} resets={meta['resets']}")
    return True


def record_verification_failure(session_id: str):
    """记录验证失败，连续失败超阈值时触发自动重置"""
    if not session_id:
        return
    meta = _session_meta.setdefault(session_id, {"token_est": 0, "consecutive_failures": 0, "resets": 0})
    meta["consecutive_failures"] += 1
    if meta["consecutive_failures"] >= SESSION_MAX_FAILURES:
        _auto_reset_session(session_id, f"连续{meta['consecutive_failures']}次验证失败")


def record_verification_success(session_id: str):
    """记录验证成功，重置连续失败计数"""
    if not session_id:
        return
    meta = _session_meta.setdefault(session_id, {"token_est": 0, "consecutive_failures": 0, "resets": 0})
    meta["consecutive_failures"] = 0


def _get_config():
    """读取智谱AI配置（从主配置文件）"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    import agi_v13_cognitive_lattice as agi
    
    # 优先使用 zhipu 配置
    zhipu_cfg = agi.BACKENDS.get("zhipu", {})
    zhipu5_cfg = agi.BACKENDS.get("zhipu_glm5", {})
    
    return {
        "openai_base_url": zhipu_cfg.get("base_url", "https://open.bigmodel.cn/api/paas/v4"),
        "anthropic_base_url": zhipu5_cfg.get("base_url", "https://open.bigmodel.cn/api/anthropic"),
        "api_key": zhipu_cfg.get("api_key", ""),
    }


# ==================== 核心调用函数 ====================

def call_zhipu(
    prompt: str,
    task_type: str = "chat",
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.4,
    max_tokens: Optional[int] = None,
    context: Optional[List[Dict]] = None,
    session_id: Optional[str] = None,
    verify_locally: bool = False,
) -> Dict[str, Any]:
    """
    调用智谱 AI 完成任务
    
    Args:
        prompt: 用户提示/任务描述
        task_type: 任务类型 (code_gen/reasoning/translate/summarize/analyze/chat/complex等)
        model: 指定模型（为空则自动选择）
        system_prompt: 自定义系统提示（为空则使用任务默认）
        temperature: 温度参数
        max_tokens: 最大输出token数
        context: 额外上下文 [{"role":"user/assistant","content":"..."}]
        session_id: 会话ID（支持多轮对话）
        verify_locally: 是否用本地模型验证结果
        
    Returns:
        {
            "success": bool,
            "content": str,           # AI回复内容
            "model": str,             # 使用的模型
            "task_type": str,         # 任务类型
            "tokens": int,            # 消耗token数(估算)
            "duration": float,        # 耗时(秒)
            "verification": {...},    # 本地验证结果(如果启用)
            "error": str,             # 错误信息(如果失败)
        }
    """
    t0 = time.time()
    
    # 1. 自动选择模型
    if not model:
        model = TASK_MODEL_MAP.get(task_type, "glm-4-flash")
    
    model_info = ZHIPU_MODELS.get(model)
    if not model_info:
        return {"success": False, "error": f"未知模型: {model}", "content": ""}
    
    # 2. 构建消息
    sys_prompt = system_prompt or TASK_SYSTEM_PROMPTS.get(task_type, TASK_SYSTEM_PROMPTS["chat"])
    
    messages = []
    
    # 恢复会话历史（含自动重置检查）
    if session_id and session_id in _conversations:
        # 检查是否需要自动重置
        est_tokens = _estimate_session_tokens(session_id)
        if est_tokens > SESSION_TOKEN_LIMIT:
            _auto_reset_session(session_id, f"token估算{est_tokens}>{SESSION_TOKEN_LIMIT}")
        messages = list(_conversations[session_id])
    
    # 添加额外上下文
    if context:
        for ctx in context:
            messages.append({"role": ctx.get("role", "user"), "content": ctx.get("content", "")})
    
    # 添加当前提示
    messages.append({"role": "user", "content": prompt})
    
    # 3. 调用API
    cfg = _get_config()
    api_type = model_info["api_type"]
    final_max_tokens = max_tokens or model_info["max_tokens"]
    
    try:
        if api_type == "anthropic":
            content = _call_anthropic(cfg, model, messages, sys_prompt, final_max_tokens, temperature)
        else:
            content = _call_openai(cfg, model, messages, sys_prompt, final_max_tokens, temperature)
    except Exception as e:
        _usage_stats["errors"] += 1
        return {
            "success": False,
            "error": str(e),
            "content": "",
            "model": model,
            "task_type": task_type,
            "duration": time.time() - t0,
        }
    
    # 4. 保存会话历史
    if session_id:
        if session_id not in _conversations:
            _conversations[session_id] = []
        _conversations[session_id].append({"role": "user", "content": prompt})
        _conversations[session_id].append({"role": "assistant", "content": content})
        # 限制历史长度
        if len(_conversations[session_id]) > 40:
            _conversations[session_id] = _conversations[session_id][-20:]
    
    # 5. 统计
    est_tokens = len(prompt + content) // 2  # 粗略估算
    duration = time.time() - t0
    cost = est_tokens / 1000 * model_info.get("cost_per_1k", 0.01)
    
    _usage_stats["total_calls"] += 1
    _usage_stats["total_tokens"] += est_tokens
    _usage_stats["total_cost"] += cost
    _usage_stats["last_call"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _usage_stats["by_model"][model] = _usage_stats["by_model"].get(model, 0) + 1
    _usage_stats["by_task"][task_type] = _usage_stats["by_task"].get(task_type, 0) + 1
    
    result = {
        "success": True,
        "content": content,
        "model": model,
        "model_name": model_info["name"],
        "task_type": task_type,
        "tokens_est": est_tokens,
        "cost_est": round(cost, 4),
        "duration": round(duration, 2),
    }
    
    # 6. 本地验证（可选）
    if verify_locally and content:
        result["verification"] = _verify_with_local(prompt, content, task_type)
    
    return result


def _call_openai(cfg, model, messages, system_prompt, max_tokens, temperature):
    """通过 OpenAI 兼容接口调用"""
    from openai import OpenAI
    
    client = OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["openai_base_url"],
    )
    
    full_messages = [{"role": "system", "content": system_prompt}]
    full_messages.extend(messages)
    
    resp = client.chat.completions.create(
        model=model,
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    return resp.choices[0].message.content.strip()


def _call_anthropic(cfg, model, messages, system_prompt, max_tokens, temperature):
    """通过 Anthropic 兼容接口调用 (GLM-5)"""
    import requests as _req
    
    base_url = cfg["anthropic_base_url"].rstrip("/")
    
    # 分离 system 和 chat messages
    chat_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_prompt += "\n" + m["content"]
        else:
            chat_msgs.append({"role": m["role"], "content": m["content"]})
    
    if not chat_msgs:
        chat_msgs = [{"role": "user", "content": system_prompt}]
        system_prompt = ""
    
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": chat_msgs,
    }
    if system_prompt.strip():
        body["system"] = system_prompt.strip()
    
    headers = {
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    
    resp = _req.post(f"{base_url}/v1/messages", headers=headers, json=body, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    
    content = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            content += block.get("text", "")
    
    return content.strip()


def _verify_with_local(prompt, cloud_response, task_type):
    """用本地 Ollama 模型校验云端结果"""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        import agi_v13_cognitive_lattice as agi
        
        check_prompt = f"""请校验以下AI回答的质量和准确性。

用户问题: {prompt[:500]}

AI回答: {cloud_response[:2000]}

请以JSON格式输出评估:
{{
    "overall_quality": "good/acceptable/poor",
    "factual_accuracy": 0.0到1.0,
    "issues": ["问题1", "问题2"],
    "suggestion": "改进建议(如果有)"
}}

只输出JSON，不要其他文字。"""
        
        result = agi._local_ollama_call([
            {"role": "system", "content": "你是一个严格的AI输出质量审查员。"},
            {"role": "user", "content": check_prompt}
        ])
        
        if isinstance(result, dict) and not result.get("error"):
            return {
                "verified": True,
                "quality": result.get("overall_quality", "unknown"),
                "accuracy": result.get("factual_accuracy", 0.5),
                "issues": result.get("issues", []),
            }
        else:
            return {"verified": False, "reason": "本地校验返回异常"}
    except Exception as e:
        return {"verified": False, "reason": str(e)}


# ==================== 高级任务接口 ====================

def generate_code(
    task: str,
    language: str = "python",
    model: Optional[str] = None,
    verify: bool = True,
) -> Dict[str, Any]:
    """委托智谱AI生成代码"""
    prompt = f"""请用 {language} 实现以下需求：

{task}

要求：
1. 代码完整可运行
2. 包含必要的 import
3. 包含关键注释
4. 包含错误处理
5. 如果是函数/类，包含使用示例"""
    
    result = call_zhipu(
        prompt=prompt,
        task_type="code_gen",
        model=model,
        verify_locally=verify,
    )
    
    # 提取代码块
    if result["success"]:
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', result["content"], re.DOTALL)
        if code_blocks:
            result["code"] = code_blocks[0].strip()
        else:
            result["code"] = result["content"]
    
    return result


def deep_reasoning(
    question: str,
    context: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """委托智谱AI进行深度推理"""
    prompt = question
    if context:
        prompt = f"背景信息：\n{context}\n\n问题：\n{question}"
    
    return call_zhipu(
        prompt=prompt,
        task_type="reasoning",
        model=model or "glm-4-plus",
        verify_locally=True,
    )


def analyze_document(
    document: str,
    instruction: str = "请分析这段文档的核心内容和关键观点",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """委托智谱AI分析长文档"""
    prompt = f"{instruction}\n\n---\n{document}"
    
    return call_zhipu(
        prompt=prompt,
        task_type="long_doc" if len(document) > 5000 else "analyze",
        model=model,
    )


def translate_text(
    text: str,
    target_lang: str = "中文",
    source_lang: str = "自动检测",
) -> Dict[str, Any]:
    """委托智谱AI翻译文本"""
    prompt = f"请将以下{source_lang}文本翻译为{target_lang}：\n\n{text}"
    
    return call_zhipu(
        prompt=prompt,
        task_type="translate",
    )


def multi_turn_chat(
    message: str,
    session_id: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """多轮对话"""
    return call_zhipu(
        prompt=message,
        task_type="chat",
        model=model,
        system_prompt=system_prompt,
        session_id=session_id,
    )


# ==================== 智能委托 ====================

def smart_delegate(
    task: str,
    local_context: Optional[List[Dict]] = None,
    force_model: Optional[str] = None,
    verify: bool = True,
) -> Dict[str, Any]:
    """
    智能委托 — 本地模型分析任务后决定最优委托策略
    
    流程：
    1. 本地模型分析任务复杂度和类型
    2. 自动选择最优智谱模型
    3. 构建上下文增强的prompt
    4. 调用智谱AI
    5. 本地验证结果
    """
    # 构建上下文
    ctx_text = ""
    if local_context:
        ctx_text = "\n相关已知节点：\n" + "\n".join(
            f"- [{n.get('domain', '?')}] {n.get('content', '')[:80]}"
            for n in local_context[:5]
        )
    
    # 分析任务类型（基于关键词）
    task_lower = task.lower()
    if any(k in task_lower for k in ['代码', 'code', '实现', '编写', '函数', '程序', '脚本']):
        task_type = "code_gen"
    elif any(k in task_lower for k in ['推理', '分析', '为什么', '原因', 'reason', 'analyze']):
        task_type = "reasoning"
    elif any(k in task_lower for k in ['翻译', 'translate', '译']):
        task_type = "translate"
    elif any(k in task_lower for k in ['摘要', '总结', 'summarize', 'summary']):
        task_type = "summarize"
    elif any(k in task_lower for k in ['审查', 'review', '检查', '优化']):
        task_type = "code_review"
    elif len(task) > 3000:
        task_type = "long_doc"
    else:
        task_type = "chat"
    
    # 构建增强prompt
    enhanced_prompt = task
    if ctx_text:
        enhanced_prompt = f"{task}\n\n{ctx_text}"
    
    return call_zhipu(
        prompt=enhanced_prompt,
        task_type=task_type,
        model=force_model,
        verify_locally=verify,
    )


# ==================== 会话管理 ====================

def list_sessions() -> List[str]:
    """列出活跃会话"""
    return list(_conversations.keys())


def clear_session(session_id: str) -> bool:
    """清除指定会话"""
    if session_id in _conversations:
        del _conversations[session_id]
        return True
    return False


def clear_all_sessions():
    """清除所有会话"""
    _conversations.clear()


# ==================== 统计与诊断 ====================

def get_usage_stats() -> Dict:
    """获取使用统计"""
    return dict(_usage_stats)


def get_available_models() -> Dict:
    """获取可用模型列表"""
    return {k: {
        "name": v["name"],
        "desc": v["desc"],
        "strengths": v["strengths"],
        "api_type": v["api_type"],
    } for k, v in ZHIPU_MODELS.items()}


def test_connection(model: str = "glm-4-flash") -> Dict:
    """测试与智谱AI的连接"""
    return call_zhipu(
        prompt="请回复'连接成功'四个字。",
        task_type="chat",
        model=model,
        max_tokens=20,
    )
