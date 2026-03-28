"""
高级Python模块：文脉感知参数冻结

该模块实现了'文脉感知参数冻结'技术，这是一种基于功能对环境敏感度的动态微调策略。
不同于传统的层级冻结方法，本方法借鉴建筑学的地基与上部结构关系，根据参数的功能
特性而非层级深度决定冻结策略。

核心思想：
- 环境敏感参数（如BatchNorm统计量）：即使浅层也激进更新
- 普适真理参数（如几何特征提取器）：即使高层也保持稳定
"""

import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from collections import defaultdict
import numpy as np
import torch
import torch.nn as nn
from dataclasses import dataclass
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ParamCategory(Enum):
    """参数功能类别枚举"""
    ENVIRONMENT_SENSITIVE = auto()  # 环境敏感参数（如BatchNorm统计量）
    UNIVERSAL_TRUTH = auto()        # 普适真理参数（如几何特征提取器）
    TRANSITIONAL = auto()           # 过渡参数
    UNKNOWN = auto()                # 未知类别


@dataclass
class FreezingConfig:
    """冻结策略配置"""
    env_sensitive_lr_mult: float = 10.0      # 环境敏感参数学习率乘数
    universal_truth_lr_mult: float = 0.1     # 普适真理参数学习率乘数
    transition_lr_mult: float = 1.0          # 过渡参数学习率乘数
    min_params_to_freeze: int = 1            # 最少冻结参数数量
    freeze_threshold: float = 0.7            # 冻结阈值（0-1）
    enable_logging: bool = True              # 是否启用日志


class ContextAwareFreezer:
    """
    文脉感知参数冻结器
    
    该类实现了基于功能对环境敏感度的动态微调策略，根据参数在神经网络中的
    功能角色而非层级深度来决定冻结策略。
    
    属性:
        model (nn.Module): 要处理的PyTorch模型
        config (FreezingConfig): 冻结策略配置
        param_categories (Dict[str, ParamCategory]): 参数名称到类别的映射
        param_sensitivity_scores (Dict[str, float]): 参数环境敏感度分数
        
    示例:
        >>> model = resnet18(pretrained=True)
        >>> config = FreezingConfig(env_sensitive_lr_mult=10.0)
        >>> freezer = ContextAwareFreezer(model, config)
        >>> freezer.analyze_model()
        >>> freezer.apply_freezing_strategy()
    """
    
    def __init__(
        self,
        model: nn.Module,
        config: Optional[FreezingConfig] = None
    ) -> None:
        """
        初始化文脉感知参数冻结器
        
        参数:
            model: 要处理的PyTorch模型
            config: 冻结策略配置，如果为None则使用默认配置
            
        异常:
            ValueError: 如果模型为空或配置无效
        """
        if model is None:
            raise ValueError("模型不能为None")
            
        self.model = model
        self.config = config or FreezingConfig()
        self._validate_config()
        
        self.param_categories: Dict[str, ParamCategory] = {}
        self.param_sensitivity_scores: Dict[str, float] = {}
        self.layer_hierarchy: Dict[str, int] = {}
        self.param_groups: Dict[ParamCategory, List[str]] = defaultdict(list)
        
        if self.config.enable_logging:
            logger.info("初始化文脉感知参数冻结器")
            logger.info(f"配置: {self.config}")
    
    def _validate_config(self) -> None:
        """验证配置参数的有效性"""
        if not 0 <= self.config.freeze_threshold <= 1:
            raise ValueError("冻结阈值必须在0到1之间")
            
        if self.config.min_params_to_freeze < 1:
            raise ValueError("最少冻结参数数量必须大于0")
            
        if self.config.env_sensitive_lr_mult <= 0:
            raise ValueError("环境敏感参数学习率乘数必须大于0")
            
        if self.config.universal_truth_lr_mult <= 0:
            raise ValueError("普适真理参数学习率乘数必须大于0")
    
    def _identify_param_category(
        self,
        name: str,
        param: nn.Parameter,
        layer_depth: int
    ) -> Tuple[ParamCategory, float]:
        """
        识别参数的功能类别和环境敏感度分数
        
        参数:
            name: 参数名称
            param: 参数张量
            layer_depth: 参数所在层的深度
            
        返回:
            Tuple[ParamCategory, float]: 参数类别和敏感度分数
        """
        # 基于参数名称和特征识别类别
        name_lower = name.lower()
        
        # 环境敏感参数识别（BatchNorm, LayerNorm等）
        if any(x in name_lower for x in ['bn', 'batch', 'norm', 'running_mean', 'running_var']):
            return ParamCategory.ENVIRONMENT_SENSITIVE, 0.9
        
        # 普适真理参数识别（几何特征提取器）
        if any(x in name_lower for x in ['conv', 'geometry', 'shape', 'edge', 'corner']):
            # 检查参数维度，高维几何特征更可能是普适真理
            if param.dim() >= 4 and param.size(1) > 64:
                return ParamCategory.UNIVERSAL_TRUTH, 0.2
        
        # 基于层深度的辅助判断
        if layer_depth < 3:  # 浅层
            # 浅层通常是普适真理，除非是归一化层
            if 'weight' in name_lower and param.dim() >= 2:
                return ParamCategory.UNIVERSAL_TRUTH, 0.3
        elif layer_depth > 10:  # 深层
            # 深层更可能是任务特定的
            return ParamCategory.TRANSITIONAL, 0.5
        
        # 默认为过渡参数
        return ParamCategory.TRANSITIONAL, 0.5
    
    def _build_layer_hierarchy(self) -> Dict[str, int]:
        """
        构建模型的层级结构
        
        返回:
            Dict[str, int]: 参数名称到层深度的映射
        """
        hierarchy = {}
        current_depth = 0
        prev_module = None
        
        for name, module in self.model.named_modules():
            if module != prev_module:
                current_depth += 1
                prev_module = module
            
            for param_name, _ in module.named_parameters(recurse=False):
                full_name = f"{name}.{param_name}" if name else param_name
                hierarchy[full_name] = current_depth
        
        return hierarchy
    
    def analyze_model(self) -> Dict[str, Tuple[ParamCategory, float]]:
        """
        分析模型中的所有参数，识别其功能类别和环境敏感度
        
        返回:
            Dict[str, Tuple[ParamCategory, float]]: 参数分析结果
            
        异常:
            RuntimeError: 如果模型没有参数
        """
        if self.config.enable_logging:
            logger.info("开始分析模型参数...")
        
        # 构建层级结构
        self.layer_hierarchy = self._build_layer_hierarchy()
        
        if not self.layer_hierarchy:
            raise RuntimeError("模型没有可训练参数")
        
        analysis_result = {}
        
        for name, param in self.model.named_parameters():
            layer_depth = self.layer_hierarchy.get(name, 0)
            category, sensitivity = self._identify_param_category(name, param, layer_depth)
            
            self.param_categories[name] = category
            self.param_sensitivity_scores[name] = sensitivity
            self.param_groups[category].append(name)
            
            analysis_result[name] = (category, sensitivity)
            
            if self.config.enable_logging:
                logger.debug(
                    f"参数: {name}, 层级: {layer_depth}, "
                    f"类别: {category.name}, 敏感度: {sensitivity:.2f}"
                )
        
        if self.config.enable_logging:
            logger.info(f"分析完成，共分析 {len(analysis_result)} 个参数")
            for category, params in self.param_groups.items():
                logger.info(f"  {category.name}: {len(params)} 个参数")
        
        return analysis_result
    
    def apply_freezing_strategy(
        self,
        custom_sensitivity: Optional[Dict[str, float]] = None
    ) -> Dict[str, bool]:
        """
        应用文脉感知的参数冻结策略
        
        参数:
            custom_sensitivity: 自定义参数敏感度分数，如果提供将覆盖自动分析结果
            
        返回:
            Dict[str, bool]: 参数名称到冻结状态的映射
            
        异常:
            ValueError: 如果在调用analyze_model之前调用此方法
        """
        if not self.param_categories:
            raise ValueError("必须先调用analyze_model方法分析模型")
        
        if self.config.enable_logging:
            logger.info("应用文脉感知参数冻结策略...")
        
        # 使用自定义敏感度分数或自动分析结果
        sensitivity_scores = custom_sensitivity or self.param_sensitivity_scores
        
        if custom_sensitivity:
            self._validate_custom_sensitivity(custom_sensitivity)
        
        freezing_decisions = {}
        frozen_count = 0
        
        for name, param in self.model.named_parameters():
            if name not in self.param_categories:
                logger.warning(f"未找到参数 {name} 的类别信息，使用默认策略")
                category = ParamCategory.UNKNOWN
            else:
                category = self.param_categories[name]
            
            sensitivity = sensitivity_scores.get(name, 0.5)
            
            # 基于类别的冻结策略
            if category == ParamCategory.ENVIRONMENT_SENSITIVE:
                # 环境敏感参数：高敏感度，不冻结，使用高学习率
                should_freeze = False
                param.requires_grad = True
                
            elif category == ParamCategory.UNIVERSAL_TRUTH:
                # 普适真理参数：低敏感度，根据阈值决定冻结
                should_freeze = sensitivity < (1 - self.config.freeze_threshold)
                param.requires_grad = not should_freeze
                
            else:  # TRANSITIONAL 或 UNKNOWN
                # 过渡参数：根据敏感度分数决定
                should_freeze = sensitivity < self.config.freeze_threshold
                param.requires_grad = not should_freeze
            
            freezing_decisions[name] = should_freeze
            
            if should_freeze:
                frozen_count += 1
            
            if self.config.enable_logging:
                logger.debug(
                    f"参数: {name}, 类别: {category.name}, "
                    f"敏感度: {sensitivity:.2f}, 冻结: {should_freeze}"
                )
        
        if self.config.enable_logging:
            total_params = len(freezing_decisions)
            frozen_percent = (frozen_count / total_params) * 100 if total_params > 0 else 0
            logger.info(
                f"冻结策略应用完成: 冻结 {frozen_count}/{total_params} "
                f"({frozen_percent:.1f}%) 个参数"
            )
        
        return freezing_decisions
    
    def _validate_custom_sensitivity(
        self,
        sensitivity_scores: Dict[str, float]
    ) -> None:
        """验证自定义敏感度分数的有效性"""
        for name, score in sensitivity_scores.items():
            if not 0 <= score <= 1:
                raise ValueError(f"参数 {name} 的敏感度分数 {score} 不在0-1范围内")
    
    def get_parameter_groups(
        self,
        base_lr: float = 1e-3
    ) -> List[Dict[str, Any]]:
        """
        获取基于文脉感知策略的参数组，用于优化器
        
        参数:
            base_lr: 基础学习率
            
        返回:
            List[Dict[str, Any]]: 参数组配置，可直接用于优化器
            
        示例:
            >>> freezer = ContextAwareFreezer(model)
            >>> freezer.analyze_model()
            >>> param_groups = freezer.get_parameter_groups(base_lr=1e-3)
            >>> optimizer = Adam(param_groups)
        """
        if not self.param_categories:
            raise ValueError("必须先调用analyze_model方法分析模型")
        
        param_groups = []
        
        # 为每个类别创建参数组
        for category in ParamCategory:
            params = []
            for name, param in self.model.named_parameters():
                if self.param_categories.get(name) == category and param.requires_grad:
                    params.append(param)
            
            if not params:
                continue
            
            # 根据类别设置学习率乘数
            if category == ParamCategory.ENVIRONMENT_SENSITIVE:
                lr_mult = self.config.env_sensitive_lr_mult
            elif category == ParamCategory.UNIVERSAL_TRUTH:
                lr_mult = self.config.universal_truth_lr_mult
            else:
                lr_mult = self.config.transition_lr_mult
            
            param_groups.append({
                'params': params,
                'lr': base_lr * lr_mult,
                'name': category.name
            })
        
        if self.config.enable_logging:
            logger.info(f"创建了 {len(param_groups)} 个参数组")
        
        return param_groups
    
    def get_freezing_report(self) -> str:
        """
        生成详细的冻结策略报告
        
        返回:
            str: 格式化的报告字符串
        """
        if not self.param_categories:
            return "尚未分析模型，请先调用analyze_model方法"
        
        report = []
        report.append("=" * 60)
        report.append("文脉感知参数冻结策略报告")
        report.append("=" * 60)
        report.append(f"模型类型: {self.model.__class__.__name__}")
        report.append(f"总参数数量: {len(self.param_categories)}")
        report.append("")
        
        for category in ParamCategory:
            params = self.param_groups.get(category, [])
            if not params:
                continue
            
            frozen_count = sum(
                1 for name in params 
                if not self.model.state_dict()[name].requires_grad
            )
            
            report.append(f"{category.name}:")
            report.append(f"  参数数量: {len(params)}")
            report.append(f"  冻结数量: {frozen_count}")
            report.append(f"  学习率乘数: ", end="")
            
            if category == ParamCategory.ENVIRONMENT_SENSITIVE:
                report.append(f"{self.config.env_sensitive_lr_mult}")
            elif category == ParamCategory.UNIVERSAL_TRUTH:
                report.append(f"{self.config.universal_truth_lr_mult}")
            else:
                report.append(f"{self.config.transition_lr_mult}")
            
            report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)


def visualize_sensitivity_distribution(
    freezer: ContextAwareFreezer,
    save_path: Optional[str] = None
) -> np.ndarray:
    """
    可视化参数环境敏感度分布（辅助函数）
    
    参数:
        freezer: 已初始化并分析过的ContextAwareFreezer实例
        save_path: 可选，保存图表的路径
        
    返回:
        np.ndarray: 敏感度分数的直方图数据
        
    异常:
        ValueError: 如果freezer未分析模型
    """
    if not freezer.param_sensitivity_scores:
        raise ValueError("ContextAwareFreezer实例必须先调用analyze_model方法")
    
    scores = np.array(list(freezer.param_sensitivity_scores.values()))
    
    # 计算直方图
    hist, bin_edges = np.histogram(scores, bins=20, range=(0, 1))
    
    # 这里只是示例，实际应用中可以使用matplotlib进行可视化
    if freezer.config.enable_logging:
        logger.info("敏感度分布统计:")
        for i in range(len(hist)):
            logger.info(
                f"  {bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}: "
                f"{'#' * int(hist[i] / max(hist) * 20)} ({hist[i]})"
            )
    
    return hist


# 使用示例
if __name__ == "__main__":
    # 创建示例模型
    model = nn.Sequential(
        nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3),
        nn.BatchNorm2d(64),
        nn.ReLU(inplace=True),
        nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
        
        nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),
        nn.BatchNorm2d(128),
        nn.ReLU(inplace=True),
        
        nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1),
        nn.BatchNorm2d(256),
        nn.ReLU(inplace=True),
        
        nn.AdaptiveAvgPool2d((1, 1)),
        nn.Flatten(),
        nn.Linear(256, 10)
    )
    
    # 初始化配置和冻结器
    config = FreezingConfig(
        env_sensitive_lr_mult=10.0,
        universal_truth_lr_mult=0.1,
        freeze_threshold=0.6,
        enable_logging=True
    )
    
    freezer = ContextAwareFreezer(model, config)
    
    # 分析模型
    analysis = freezer.analyze_model()
    
    # 应用冻结策略
    decisions = freezer.apply_freezing_strategy()
    
    # 获取参数组用于优化器
    param_groups = freezer.get_parameter_groups(base_lr=1e-3)
    
    # 打印报告
    print(freezer.get_freezing_report())
    
    # 可视化敏感度分布
    hist = visualize_sensitivity_distribution(freezer)