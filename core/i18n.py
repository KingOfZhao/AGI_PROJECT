#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 国际化框架
=====================
对应维度83: 国际化(i18n)支持
"""

import json
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).parent

# ==================== 语言包 ====================
_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh": {
        "system.healthy": "系统健康",
        "system.degraded": "系统降级",
        "system.version": "版本",
        "chat.empty_message": "消息不能为空",
        "chat.stopped": "已停止",
        "chat.searching": "搜索相关已知节点...",
        "chat.found_nodes": "找到 {count} 个相关节点",
        "chat.no_nodes": "未找到相关节点",
        "chat.fast_path": "快速路径：{count} 个proven节点命中",
        "chat.decomposing": "自上而下拆解中...",
        "chat.bottom_up": "自下而上生成新问题...",
        "chat.collision": "四向碰撞检测中...",
        "tool.start": "Tool Controller启动",
        "tool.done": "完成: {rounds}轮, {calls}次工具调用",
        "tool.error": "工具执行错误",
        "action.planning": "分析问题，匹配能力...",
        "action.planned": "规划了 {count} 个动作",
        "action.intent_detected": "检测到执行意图",
        "security.dangerous": "危险命令被阻止",
        "security.path_denied": "安全限制：路径不在允许范围内",
        "error.timeout": "执行超时 ({seconds}s)",
        "error.unknown_tool": "未知工具: {name}",
    },
    "en": {
        "system.healthy": "System Healthy",
        "system.degraded": "System Degraded",
        "system.version": "Version",
        "chat.empty_message": "Message cannot be empty",
        "chat.stopped": "Stopped",
        "chat.searching": "Searching related knowledge nodes...",
        "chat.found_nodes": "Found {count} related nodes",
        "chat.no_nodes": "No related nodes found",
        "chat.fast_path": "Fast path: {count} proven nodes matched",
        "chat.decomposing": "Top-down decomposition...",
        "chat.bottom_up": "Bottom-up question generation...",
        "chat.collision": "Four-direction collision detection...",
        "tool.start": "Tool Controller started",
        "tool.done": "Done: {rounds} rounds, {calls} tool calls",
        "tool.error": "Tool execution error",
        "action.planning": "Analyzing problem, matching capabilities...",
        "action.planned": "Planned {count} actions",
        "action.intent_detected": "Action intent detected",
        "security.dangerous": "Dangerous command blocked",
        "security.path_denied": "Security: path not in allowed range",
        "error.timeout": "Execution timeout ({seconds}s)",
        "error.unknown_tool": "Unknown tool: {name}",
    },
    "ja": {
        "system.healthy": "システム正常",
        "system.degraded": "システム低下",
        "chat.empty_message": "メッセージは空にできません",
        "chat.searching": "関連知識ノードを検索中...",
        "tool.start": "ツールコントローラー起動",
    },
}

# 当前语言
_current_lang = "zh"


def set_language(lang: str):
    """设置当前语言"""
    global _current_lang
    if lang in _TRANSLATIONS:
        _current_lang = lang


def get_language() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    """翻译键值"""
    lang_dict = _TRANSLATIONS.get(_current_lang, _TRANSLATIONS["zh"])
    text = lang_dict.get(key)
    if text is None:
        # 回退到中文
        text = _TRANSLATIONS["zh"].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def available_languages() -> list:
    return list(_TRANSLATIONS.keys())
