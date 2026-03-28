"""
生成式认知坍缩引擎

该模块实现了一个基于L-System (Lindenmayer System) 的知识结构生成与重构系统。
它将知识领域视为一个分形结构，通过提取核心公理和生成规则，推演出完整的知识树。
用户可以交互式地修改节点参数，实时观察其对整体知识结构的影响，从而验证对领域的掌握程度。

核心概念：
- 公理: 知识的起始点，最基础的定义或概念。
- 规则: 知识衍化的逻辑，定义了概念如何分解为子概念或关联其他概念。
- 变量: 影响衍化过程的反直觉参数或环境因子。
- 状态: 当前衍化步骤的字符串表示，映射为知识树的拓扑结构。
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class LSystemConfig:
    """
    L-System 配置类，定义了生成式认知系统的基本参数。
    
    Attributes:
        axiom (str): 初始公理字符串，代表知识的起点。
        rules (Dict[str, str]): 生成规则字典，键为前驱，变量为后继。
        iterations (int): 迭代次数，控制知识树的深度。
        angle (float): 分支角度（用于可视化或逻辑分支权重）。
        ignored_symbols (Set[str]): 在计算上下文时忽略的符号。
    """
    axiom: str
    rules: Dict[str, str]
    iterations: int = 3
    angle: float = 25.0
    ignored_symbols: Set[str] = field(default_factory=lambda: {'[', ']', '+', '-'})

    def __post_init__(self):
        """数据验证"""
        if not self.axiom:
            raise ValueError("公理不能为空")
        if self.iterations < 0:
            raise ValueError("迭代次数不能为负数")
        if not self.rules:
            logger.warning("规则集为空，系统将仅输出公理。")


class GenerativeCognitiveEngine:
    """
    生成式认知坍缩引擎。
    
    利用L-System逻辑模拟知识结构的生长与坍缩。通过修改生成规则，
    用户可以探索不同的知识拓扑结构。
    """

    def __init__(self, config: LSystemConfig):
        """
        初始化引擎。
        
        Args:
            config (LSystemConfig): 系统配置对象。
        """
        self.config = config
        self.current_state = config.axiom
        self.history: List[str] = []
        logger.info("GenerativeCognitiveEngine 初始化完成。核心公理: %s", self.config.axiom)

    def _validate_rule_syntax(self, predecessor: str, successor: str) -> bool:
        """
        辅助函数：验证生成规则的语法有效性。
        
        Args:
            predecessor (str): 规则前驱。
            successor (str): 规则后继。
            
        Returns:
            bool: 如果规则有效返回 True，否则抛出异常。
            
        Raises:
            ValueError: 如果规则格式不符合逻辑。
        """
        if not predecessor.isalpha() or len(predecessor) != 1:
            # 支持随机L-System等扩展通常需要更复杂的解析，这里仅做基础校验
            if len(predecessor) > 1:
                logger.warning("检测到上下文敏感规则: %s，当前版本仅支持简单替换。", predecessor)
        
        if not successor:
            raise ValueError(f"规则后继不能为空: {predecessor} -> ")
            
        return True

    def apply_rules(self, local_variables: Optional[Dict[str, str]] = None) -> str:
        """
        核心函数：执行认知迭代（L-System 演化）。
        
        根据当前的公理和规则集，进行指定次数的迭代，生成最终的知识结构字符串。
        支持通过 local_variables 动态修改规则中的参数。
        
        Args:
            local_variables (Optional[Dict[str, str]]): 用于替换规则中特定占位符的参数。
        
        Returns:
            str: 演化后的最终状态字符串（知识骨架）。
            
        Raises:
            RecursionError: 如果迭代导致字符串指数级爆炸超出内存限制。
        """
        logger.info("开始知识树演化，迭代深度: %d", self.config.iterations)
        current_gen = self.config.axiom
        self.history = [current_gen]

        try:
            for i in range(self.config.iterations):
                next_gen = []
                for char in current_gen:
                    # 检查是否有匹配的规则
                    replacement = self.config.rules.get(char, char)
                    
                    # 如果有局部变量注入，进行简单的参数替换（模拟反直觉变量注入）
                    if local_variables:
                        for key, val in local_variables.items():
                            replacement = replacement.replace(f"${key}", val)
                    
                    next_gen.append(replacement)
                
                current_gen = "".join(next_gen)
                self.history.append(current_gen)
                
                # 边界检查：防止无限生长导致系统崩溃
                if len(current_gen) > 100000:
                    logger.error("认知结构溢出：生成字符串过长 (>100k)，已终止。")
                    raise MemoryError("Knowledge structure overflow")
                    
                logger.debug("Iteration %d: Length %d", i+1, len(current_gen))

            self.current_state = current_gen
            logger.info("演化完成。最终结构复杂度: %d", len(self.current_state))
            return self.current_state

        except Exception as e:
            logger.exception("演化过程中发生错误: %s", e)
            raise

    def compress_knowledge(self, state: str) -> Dict[str, int]:
        """
        核心函数：知识压缩与拓扑分析。
        
        解析生成的字符串，将其映射为可交互的知识节点统计。
        模拟 'A4纸' 上的压缩视图，提取关键节点的分布密度。
        
        Args:
            state (str): 演化后的状态字符串。
            
        Returns:
            Dict[str, int]: 各个核心概念（字符）在结构中出现的频率统计。
        """
        if not state:
            return {}
            
        frequency_map: Dict[str, int] = {}
        
        # 过滤掉控制字符，只统计知识节点
        clean_state = [c for c in state if c.isalpha()]
        
        for char in clean_state:
            frequency_map[char] = frequency_map.get(char, 0) + 1
            
        # 按频率排序
        sorted_map = dict(sorted(frequency_map.items(), key=lambda item: item[1], reverse=True))
        
        logger.info("知识压缩分析完成。核心节点数: %d", len(sorted_map))
        return sorted_map

    def modify_node_and_recalculate(self, target_rule_key: str, new_rule_value: str) -> Tuple[str, Dict[str, int]]:
        """
        辅助功能：交互式修改与即时演算。
        
        允许用户修改某一条生成规则，并立即查看其对整体结构的影响。
        
        Args:
            target_rule_key (str): 要修改的规则前驱（概念核心）。
            new_rule_value (str): 新的生成逻辑。
            
        Returns:
            Tuple[str, Dict[str, int]]: 新的状态字符串和新的压缩统计。
        """
        if target_rule_key not in self.config.rules:
            logger.warning("规则 %s 不存在，将作为新规则添加。", target_rule_key)
        
        try:
            self._validate_rule_syntax(target_rule_key, new_rule_value)
            self.config.rules[target_rule_key] = new_rule_value
            logger.info("规则已更新: %s -> %s", target_rule_key, new_rule_value)
            
            # 重新演算
            new_state = self.apply_rules()
            new_stats = self.compress_knowledge(new_state)
            
            return new_state, new_stats
            
        except ValueError as e:
            logger.error("规则修改失败: %s", e)
            return self.current_state, self.compress_knowledge(self.current_state)


# 使用示例
if __name__ == "__main__":
    # 示例：模拟一个简单的生物学知识树 (Algae growth model as knowledge branching)
    # A = 核心概念, B = 辅助概念
    # 规则: A->AB (概念分裂), B->A (概念回归)
    
    print("--- 生成式认知坍缩引擎演示 ---")
    
    # 1. 定义初始配置
    # 假设我们在研究 "神经网络架构"
    # A: 基础层, B: 激活函数, C: 优化器
    # 初始只有基础层 A
    # 规则: 基础层 (A) 产生 激活函数 (B) 和 基础层 (A) -> A->B
    # 激活函数 (B) 产生 优化器 (C) -> B->C
    # 优化器 (C) 回归到 基础层 (C->A)
    
    knowledge_config = LSystemConfig(
        axiom="A",  # 核心公理：基础层
        rules={
            "A": "AB",  # 基础层衍生出新的层和激活函数
            "B": "C",   # 激活函数后接优化器
            "C": "A"    # 优化器后回归基础层概念（循环）
        },
        iterations=5
    )

    # 2. 初始化引擎
    engine = GenerativeCognitiveEngine(knowledge_config)

    # 3. 执行推演
    try:
        final_structure = engine.apply_rules()
        print(f"\n[推演结果] 知识骨架序列: {final_structure[:50]}... (总长度: {len(final_structure)})")
        
        # 4. 压缩分析
        stats = engine.compress_knowledge(final_structure)
        print(f"\n[压缩视图] 节点分布: {stats}")
        
        # 5. 交互式修改 (模拟用户探索)
        print("\n[交互] 修改规则: 'A' -> 'AC' (引入反直觉变量 C)")
        new_struct, new_stats = engine.modify_node_and_recalculate("A", "AC")
        print(f"[结果] 新知识骨架序列: {new_struct[:50]}...")
        print(f"[结果] 新节点分布: {new_stats}")

    except Exception as e:
        print(f"系统运行出错: {e}")