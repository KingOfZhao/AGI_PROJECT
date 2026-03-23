#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 插件注册表
=====================
提供可扩展的插件机制，允许动态注册/发现/加载工具和技能模块。
对应维度76: 代码可扩展性
对应维度78: 依赖注入模式
"""

import importlib
import inspect
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional

PROJECT_ROOT = Path(__file__).parent


class PluginRegistry:
    """轻量级插件注册表 — 支持工具/技能/后端的动态注册与发现"""

    def __init__(self):
        self._plugins: Dict[str, Dict] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._services: Dict[str, Any] = {}  # DI容器(维度78)
        self._load_time = time.time()

    # ==================== 插件管理 ====================

    def register(self, name: str, plugin: Any, category: str = "tool",
                 version: str = "1.0", metadata: Dict = None):
        """注册一个插件"""
        self._plugins[name] = {
            "name": name,
            "plugin": plugin,
            "category": category,
            "version": version,
            "metadata": metadata or {},
            "registered_at": time.time(),
            "enabled": True,
        }

    def unregister(self, name: str):
        """注销一个插件"""
        self._plugins.pop(name, None)

    def get(self, name: str) -> Optional[Any]:
        """获取插件实例"""
        entry = self._plugins.get(name)
        if entry and entry["enabled"]:
            return entry["plugin"]
        return None

    def list_plugins(self, category: str = None) -> List[Dict]:
        """列出所有已注册插件"""
        plugins = []
        for name, entry in self._plugins.items():
            if category and entry["category"] != category:
                continue
            plugins.append({
                "name": name,
                "category": entry["category"],
                "version": entry["version"],
                "enabled": entry["enabled"],
                "metadata": entry["metadata"],
            })
        return plugins

    def enable(self, name: str):
        if name in self._plugins:
            self._plugins[name]["enabled"] = True

    def disable(self, name: str):
        if name in self._plugins:
            self._plugins[name]["enabled"] = False

    # ==================== Hook系统 (事件驱动扩展) ====================

    def add_hook(self, event: str, callback: Callable):
        """注册事件钩子"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def trigger(self, event: str, **kwargs) -> List[Any]:
        """触发事件，执行所有注册的钩子"""
        results = []
        for callback in self._hooks.get(event, []):
            try:
                results.append(callback(**kwargs))
            except Exception as e:
                results.append({"error": str(e)})
        return results

    # ==================== DI容器 (维度78: 依赖注入) ====================

    def register_service(self, name: str, instance: Any):
        """注册一个服务实例(单例)"""
        self._services[name] = instance

    def get_service(self, name: str) -> Optional[Any]:
        """获取服务实例"""
        return self._services.get(name)

    def inject(self, func: Callable) -> Callable:
        """装饰器: 自动注入依赖"""
        sig = inspect.signature(func)
        def wrapper(*args, **kwargs):
            for param_name, param in sig.parameters.items():
                if param_name not in kwargs and param_name in self._services:
                    kwargs[param_name] = self._services[param_name]
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    # ==================== 自动发现 ====================

    def auto_discover(self, skills_dir: str = None):
        """自动发现并注册 workspace/skills/ 下的插件"""
        sd = Path(skills_dir) if skills_dir else PROJECT_ROOT / "workspace" / "skills"
        count = 0
        for meta_file in sd.glob("*.meta.json"):
            try:
                meta = json.loads(meta_file.read_text(encoding='utf-8'))
                name = meta.get("name", meta_file.stem)
                py_file = meta_file.with_suffix('').with_suffix('.py')
                if py_file.exists():
                    self.register(name, str(py_file), category="skill",
                                  metadata=meta)
                    count += 1
            except Exception:
                continue
        return count

    # ==================== 统计 ====================

    def stats(self) -> Dict:
        categories = {}
        for entry in self._plugins.values():
            cat = entry["category"]
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_plugins": len(self._plugins),
            "categories": categories,
            "hooks": {k: len(v) for k, v in self._hooks.items()},
            "services": list(self._services.keys()),
            "uptime_s": round(time.time() - self._load_time, 1),
        }


# ==================== 全局注册表单例 ====================
registry = PluginRegistry()
