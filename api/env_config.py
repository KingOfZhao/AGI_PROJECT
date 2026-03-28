#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 环境配置管理
======================
12-Factor App 配置外部化: 所有配置从环境变量读取，支持.env文件。
对应维度42: 云原生开发 (12-Factor配置)
对应维度85: 数据隐私合规 (移除硬编码密钥)
"""

import os
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent

# 尝试加载 .env 文件
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


class EnvConfig:
    """环境变量驱动的配置(12-Factor App)"""

    # ==================== 系统 ====================
    AGI_ENV = os.getenv("AGI_ENV", "development")
    AGI_DEBUG = os.getenv("AGI_DEBUG", "false").lower() == "true"
    AGI_LOG_LEVEL = os.getenv("AGI_LOG_LEVEL", "INFO")
    AGI_VERSION = "13.3.0"

    # ==================== 数据库 ====================
    AGI_DB_PATH = os.getenv("AGI_DB_PATH", str(PROJECT_ROOT / "memory.db"))

    # ==================== API服务 ====================
    AGI_API_HOST = os.getenv("AGI_API_HOST", "0.0.0.0")
    AGI_API_PORT = int(os.getenv("AGI_API_PORT", "5002"))

    # ==================== LLM后端 ====================
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
    ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b")

    # ==================== 安全 ====================
    AGI_EXEC_TIMEOUT = int(os.getenv("AGI_EXEC_TIMEOUT", "30"))
    AGI_MAX_TOKENS = int(os.getenv("AGI_MAX_TOKENS", "8192"))
    AGI_TEMPERATURE = float(os.getenv("AGI_TEMPERATURE", "0.35"))

    # ==================== Redis缓存 ====================
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    @classmethod
    def is_production(cls) -> bool:
        return cls.AGI_ENV == "production"

    @classmethod
    def is_test(cls) -> bool:
        return cls.AGI_ENV == "test"

    @classmethod
    def validate(cls) -> dict:
        """验证关键配置"""
        issues = []
        if cls.is_production():
            if not cls.ZHIPU_API_KEY:
                issues.append("ZHIPU_API_KEY未设置")
            if cls.AGI_DEBUG:
                issues.append("生产环境不应启用DEBUG")
        return {
            "valid": len(issues) == 0,
            "env": cls.AGI_ENV,
            "issues": issues,
        }

    @classmethod
    def summary(cls) -> dict:
        """配置摘要(隐藏敏感信息)"""
        return {
            "env": cls.AGI_ENV,
            "debug": cls.AGI_DEBUG,
            "log_level": cls.AGI_LOG_LEVEL,
            "db_path": cls.AGI_DB_PATH,
            "api_host": cls.AGI_API_HOST,
            "api_port": cls.AGI_API_PORT,
            "zhipu_configured": bool(cls.ZHIPU_API_KEY),
            "ollama_host": cls.OLLAMA_HOST,
            "ollama_model": cls.OLLAMA_MODEL,
            "exec_timeout": cls.AGI_EXEC_TIMEOUT,
        }
