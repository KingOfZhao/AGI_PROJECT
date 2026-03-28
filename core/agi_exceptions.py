#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 自定义异常层级
========================
提供精细化异常分类，替代bare except，提升鲁棒性。
对应维度79: 异常处理与鲁棒性
"""


class AGIBaseError(Exception):
    """AGI系统基础异常"""
    def __init__(self, message="", context=None):
        super().__init__(message)
        self.context = context or {}


# ==================== LLM相关异常 ====================
class LLMError(AGIBaseError):
    """LLM调用相关异常基类"""
    pass

class LLMTimeoutError(LLMError):
    """LLM调用超时"""
    pass

class LLMRateLimitError(LLMError):
    """LLM API限流"""
    pass

class LLMResponseParseError(LLMError):
    """LLM响应解析失败"""
    pass

class LLMContextOverflowError(LLMError):
    """上下文超出模型最大长度"""
    pass


# ==================== 工具执行异常 ====================
class ToolError(AGIBaseError):
    """工具执行相关异常基类"""
    pass

class ToolNotFoundError(ToolError):
    """工具未注册"""
    pass

class ToolTimeoutError(ToolError):
    """工具执行超时"""
    pass

class ToolParameterError(ToolError):
    """工具参数错误"""
    pass

class CodeExecutionError(ToolError):
    """代码执行失败"""
    pass

class ShellCommandError(ToolError):
    """Shell命令执行失败"""
    pass

class DangerousCommandError(ToolError):
    """危险命令被阻止"""
    pass


# ==================== 文件操作异常 ====================
class FileOperationError(AGIBaseError):
    """文件操作异常基类"""
    pass

class FileSecurityError(FileOperationError):
    """文件安全检查未通过(路径越权/扩展名不允许)"""
    pass

class FileNotFoundError_(FileOperationError):
    """文件不存在(避免与内置FileNotFoundError冲突)"""
    pass


# ==================== 认知格异常 ====================
class CognitiveLatticeError(AGIBaseError):
    """认知格相关异常基类"""
    pass

class NodeNotFoundError(CognitiveLatticeError):
    """认知节点不存在"""
    pass

class EmbeddingError(CognitiveLatticeError):
    """向量嵌入失败"""
    pass

class GroundingError(CognitiveLatticeError):
    """Proven锚定检查失败"""
    pass


# ==================== Orchestrator异常 ====================
class OrchestratorError(AGIBaseError):
    """编排器相关异常基类"""
    pass

class RoutingError(OrchestratorError):
    """模型路由决策失败"""
    pass

class ComplexityAnalysisError(OrchestratorError):
    """复杂度分析失败"""
    pass

class TaskDecompositionError(OrchestratorError):
    """任务分解失败"""
    pass


# ==================== 安全异常 ====================
class SecurityError(AGIBaseError):
    """安全相关异常基类"""
    pass

class SQLInjectionAttemptError(SecurityError):
    """SQL注入尝试被检测"""
    pass

class UnauthorizedAccessError(SecurityError):
    """未授权访问"""
    pass


# ==================== 配置异常 ====================
class ConfigError(AGIBaseError):
    """配置相关异常"""
    pass

class BackendNotFoundError(ConfigError):
    """后端配置不存在"""
    pass

class APIKeyMissingError(ConfigError):
    """API Key缺失"""
    pass
