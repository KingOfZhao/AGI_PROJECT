#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 结构化日志系统
========================
替换print为标准logging模块，支持结构化JSON日志输出。
对应维度80: 日志监控与可观测性集成
"""

import logging
import logging.handlers
import json
import time
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


class StructuredFormatter(logging.Formatter):
    """结构化JSON日志格式器"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if hasattr(record, 'component'):
            log_entry["component"] = record.component
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, 'tool_name'):
            log_entry["tool_name"] = record.tool_name
        if hasattr(record, 'model'):
            log_entry["model"] = record.model
        if hasattr(record, 'extra_data'):
            log_entry["data"] = record.extra_data
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """控制台可读格式器(带颜色)"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        component = getattr(record, 'component', record.module)
        msg = record.getMessage()
        duration = ""
        if hasattr(record, 'duration_ms'):
            duration = f" ({record.duration_ms:.0f}ms)"
        return f"  {color}[{ts}] [{component}] {msg}{duration}{self.RESET}"


class MetricsCollector:
    """简易指标收集器(Prometheus兼容格式导出)"""

    def __init__(self):
        self._counters = {}
        self._gauges = {}
        self._histograms = {}
        self._start_time = time.time()

    def inc(self, name, value=1, labels=None):
        key = (name, str(labels or {}))
        self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name, value, labels=None):
        key = (name, str(labels or {}))
        self._gauges[key] = value

    def observe(self, name, value, labels=None):
        key = (name, str(labels or {}))
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-500:]

    def export_prometheus(self):
        """导出Prometheus文本格式指标"""
        lines = []
        lines.append(f"# AGI v13.3 Metrics")
        lines.append(f"agi_uptime_seconds {time.time() - self._start_time:.0f}")

        for (name, labels), value in self._counters.items():
            lines.append(f"{name}{{{labels}}} {value}")
        for (name, labels), value in self._gauges.items():
            lines.append(f"{name}{{{labels}}} {value}")
        for (name, labels), values in self._histograms.items():
            if values:
                lines.append(f"{name}_count{{{labels}}} {len(values)}")
                lines.append(f"{name}_sum{{{labels}}} {sum(values):.3f}")
                lines.append(f"{name}_avg{{{labels}}} {sum(values)/len(values):.3f}")
        return "\n".join(lines)

    def get_summary(self):
        """获取指标摘要字典"""
        summary = {
            "uptime_s": round(time.time() - self._start_time, 1),
            "counters": {f"{n}": v for (n, _), v in self._counters.items()},
            "gauges": {f"{n}": v for (n, _), v in self._gauges.items()},
        }
        for (name, _), values in self._histograms.items():
            if values:
                summary[f"{name}_avg"] = round(sum(values) / len(values), 3)
                summary[f"{name}_count"] = len(values)
        return summary


# ==================== 全局实例 ====================
metrics = MetricsCollector()


def get_logger(name, component=None):
    """获取组件日志器"""
    logger = logging.getLogger(f"agi.{name}")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # 控制台输出(可读格式)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(ConsoleFormatter())
        logger.addHandler(ch)

        # 文件输出(结构化JSON) - 带日志轮转
        log_file = LOG_DIR / f"agi_{name}.jsonl"
        fh = logging.handlers.RotatingFileHandler(
            str(log_file), maxBytes=5*1024*1024, backupCount=3,
            encoding='utf-8'
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(StructuredFormatter())
        logger.addHandler(fh)

        logger.propagate = False

    # 添加默认component
    old_factory = logging.getLogRecordFactory()
    comp = component or name

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, 'component'):
            record.component = comp
        return record

    logging.setLogRecordFactory(record_factory)
    return logger


# 预创建核心日志器
log_api = get_logger("api", "APIServer")
log_tool = get_logger("tool", "ToolController")
log_orch = get_logger("orchestrator", "Orchestrator")
log_action = get_logger("action", "ActionEngine")
log_lattice = get_logger("lattice", "CognitiveLattice")
