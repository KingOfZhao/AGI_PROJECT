"""
名称: auto_反直觉知识关卡生成器_利用ai将高密_d404a0
描述: 【反直觉知识关卡生成器】
该模块利用AI将高密度文本（如《博弈论》）拆解为'规则'而非'段落'。
系统不只生成摘要，而是构建一个可交互的微型模拟器。学习者通过调整参数
（如囚徒困境的刑期），直接观察'反直觉结论'（如纳什均衡的非最优性）是
如何从底层规则涌现的。将'阅读'转化为'参数调优'，实现极高密度的认知内化。
"""

import logging
import json
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GameType(Enum):
    """支持的博弈类型枚举"""
    PRISONERS_DILEMMA = "PrisonersDilemma"
    TRAGEDY_OF_COMMONS = "TragedyOfCommons"
    ULTIMATUM_GAME = "UltimatumGame"


@dataclass
class Strategy:
    """策略定义"""
    name: str
    description: str
    function_ref: str  # 指向决策逻辑的引用或简单描述


@dataclass
class RuleSet:
    """规则集定义"""
    parameters: Dict[str, Any]
    payoff_matrix: Dict[str, Dict[str, Tuple[int, int]]]
    win_condition: str
    description: str


@dataclass
class SimulationResult:
    """模拟结果"""
    scenario_name: str
    player_choice: str
    opponent_choice: str
    player_payoff: int
    opponent_payoff: int
    is_nash_equilibrium: bool
    counter_intuitive_insight: str


class KnowledgeSimulator:
    """
    核心类：基于规则的知识模拟器。
    用于将静态知识转化为可交互的动态模型。
    """

    def __init__(self, topic: str, game_type: GameType):
        """
        初始化模拟器。

        Args:
            topic (str): 知识主题，如 "博弈论"。
            game_type (GameType): 模拟类型。
        """
        self.topic = topic
        self.game_type = game_type
        self.rule_set: Optional[RuleSet] = None
        self.strategies: List[Strategy] = []
        logger.info(f"初始化模拟器: 主题={topic}, 类型={game_type.value}")

    def load_rules_from_ai(self, high_density_text: str) -> RuleSet:
        """
        [核心函数1]
        模拟AI解析过程：将高密度文本解析为结构化的规则集。
        在实际AGI场景中，这里会调用LLM进行结构化提取。
        
        Args:
            high_density_text (str): 输入的高密度知识文本。
            
        Returns:
            RuleSet: 解析后的规则对象。
            
        Raises:
            ValueError: 如果文本无法解析为有效的规则。
        """
        logger.info("开始解析高密度文本以提取规则...")
        
        # 模拟AI解析逻辑：这里预置了囚徒困境的规则作为演示
        # 真实场景下，Prompt会是："Extract rules and payoff matrix from text: {high_density_text}"
        if "囚徒" in high_density_text or "Prisoner" in high_density_text or self.game_type == GameType.PRISONERS_DILEMMA:
            self.rule_set = RuleSet(
                parameters={
                    "temptation_payoff": 5,  # 背叛的诱惑
                    "reward_payoff": 3,      # 双方合作的奖励
                    "punishment_payoff": 1,  # 双方背叛的惩罚
                    "sucker_payoff": 0       # 被出卖的代价
                },
                payoff_matrix={
                    "Cooperate": {"Cooperate": (3, 3), "Defect": (0, 5)},
                    "Defect": {"Cooperate": (5, 0), "Defect": (1, 1)}
                },
                win_condition="Maximize total payoff over iterations",
                description="经典的囚徒困境模型，展示个体理性如何导致集体非理性。"
            )
            self.strategies = [
                Strategy("Cooperate", "与对方合作，保持沉默", "always_cooperate"),
                Strategy("Defect", "背叛对方，以此换取减刑", "always_defect")
            ]
            logger.info("规则集提取成功：囚徒困境")
            return self.rule_set
        else:
            logger.error("无法从文本中提取匹配的规则集")
            raise ValueError("不支持的文本内容或模拟类型")

    def configure_parameters(self, param_overrides: Dict[str, int]) -> bool:
        """
        [辅助函数]
        允许用户覆盖默认参数，重新定义博弈环境。
        包含数据验证和边界检查。
        
        Args:
            param_overrides (Dict[str, int]): 参数键值对。
            
        Returns:
            bool: 是否配置成功。
        """
        if not self.rule_set:
            logger.warning("尚未加载规则集，无法配置参数")
            return False

        logger.info(f"尝试更新参数: {param_overrides}")
        
        # 边界检查：确保参数逻辑有效
        # 在囚徒困境中，通常要求 T > R > P > S
        # T=Tempration, R=Reward, P=Punishment, S=Sucker
        try:
            t = param_overrides.get('temptation_payoff', self.rule_set.parameters['temptation_payoff'])
            r = param_overrides.get('reward_payoff', self.rule_set.parameters['reward_payoff'])
            p = param_overrides.get('punishment_payoff', self.rule_set.parameters['punishment_payoff'])
            s = param_overrides.get('sucker_payoff', self.rule_set.parameters['sucker_payoff'])

            if not (t > r > p > s):
                logger.error(f"参数违反博弈论逻辑约束: 要求 T({t}) > R({r}) > P({p}) > S({s})")
                return False
            
            # 更新参数
            self.rule_set.parameters.update(param_overrides)
            
            # 重新构建收益矩阵
            self.rule_set.payoff_matrix = {
                "Cooperate": {"Cooperate": (r, r), "Defect": (s, t)},
                "Defect": {"Cooperate": (t, s), "Defect": (p, p)}
            }
            logger.info("参数配置成功，收益矩阵已更新。")
            return True

        except KeyError as e:
            logger.error(f"缺少必要的参数键: {e}")
            return False
        except Exception as e:
            logger.error(f"参数配置过程中发生未知错误: {e}")
            return False

    def run_simulation_step(
        self, 
        player_strategy_name: str, 
        opponent_strategy_name: str = "Defect"
    ) -> SimulationResult:
        """
        [核心函数2]
        运行单步模拟，计算结果并生成反直觉洞察。
        
        Args:
            player_strategy_name (str): 玩家选择的策略。
            opponent_strategy_name (str): 对手选择的策略 (默认为理性人/背叛)。
            
        Returns:
            SimulationResult: 包含结果和洞察的对象。
        """
        if not self.rule_set:
            raise RuntimeError("必须先加载规则集 (load_rules_from_ai)")

        # 数据验证：检查策略是否存在
        valid_strategies = [s.name for s in self.strategies]
        if player_strategy_name not in valid_strategies:
            raise ValueError(f"无效策略: {player_strategy_name}")
        
        # 获取收益
        try:
            p_payoff, o_payoff = self.rule_set.payoff_matrix[player_strategy_name][opponent_strategy_name]
        except KeyError:
            raise ValueError("策略组合在收益矩阵中不存在")

        # 判断是否为纳什均衡
        # 简单逻辑：如果给定对手策略，玩家无法通过改变策略获得更高收益，则是纳什均衡
        is_nash = False
        if opponent_strategy_name == "Defect":
            # 如果对手背叛，我也背叛（1）比合作（0）好，所以(Defect, Defect)是纳什均衡
            is_nash = (player_strategy_name == "Defect")
        
        # 生成反直觉洞察
        insight = self._generate_insight(
            player_strategy_name, 
            opponent_strategy_name, 
            p_payoff, 
            o_payoff, 
            is_nash
        )

        result = SimulationResult(
            scenario_name=self.game_type.value,
            player_choice=player_strategy_name,
            opponent_choice=opponent_strategy_name,
            player_payoff=p_payoff,
            opponent_payoff=o_payoff,
            is_nash_equilibrium=is_nash,
            counter_intuitive_insight=insight
        )
        
        logger.info(f"模拟完成: 玩家({player_strategy_name}) vs 对手({opponent_strategy_name}) -> 收益: {p_payoff}")
        return result

    def _generate_insight(
        self, 
        p_move: str, 
        o_move: str, 
        p_score: int, 
        o_score: int, 
        is_nash: bool
    ) -> str:
        """
        内部方法：根据结果生成教育性洞察。
        """
        if p_move == "Cooperate" and o_move == "Defect":
            return f"【反直觉时刻】：你选择了高尚的合作，结果却获得了最低收益({p_score})。"
            "在缺乏沟通机制的情况下，善良往往被视为软弱可欺。"
        
        if is_nash and p_score < self.rule_set.parameters['reward_payoff']:
            r = self.rule_set.parameters['reward_payoff']
            return (f"【反直觉时刻】：纳什均衡点并不等于全局最优解！"
            f"虽然每个人都做出了'理性'的选择({p_move})，但结果({p_score}) "
            f"远差于双方合作所能获得的({r})。这就是'个体理性导致集体非理性'。")
            
        if p_move == "Cooperate" and o_move == "Cooperate":
            return "理想状态达成。但在单次博弈中，这是一个不稳定的脆弱平衡。"
            
        return "系统处于稳态，但也可能处于低效的陷阱中。"

    def export_configuration(self) -> str:
        """导出当前配置为JSON字符串"""
        if not self.rule_set:
            return "{}"
        return json.dumps({
            "topic": self.topic,
            "type": self.game_type.value,
            "rules": asdict(self.rule_set),
            "strategies": [asdict(s) for s in self.strategies]
        }, indent=2)


# 使用示例
if __name__ == "__main__":
    # 1. 初始化系统
    simulator = KnowledgeSimulator(topic="Game Theory 101", game_type=GameType.PRISONERS_DILEMMA)
    
    # 2. (模拟) 从高密度文本加载规则
    text_content = "在囚徒困境中，背叛是占优策略..."
    try:
        rules = simulator.load_rules_from_ai(text_content)
        print(f"--- 加载规则: {rules.description} ---")
        
        # 3. 交互：用户尝试修改参数 (试图改变环境)
        # 尝试将合作收益调低，看看会发生什么
        print("\n--- 尝试调整参数 (无效调整) ---")
        simulator.configure_parameters({
            "temptation_payoff": 2, # T
            "reward_payoff": 3,    # R
            "punishment_payoff": 4,# P (违反了 T > R > P > S 中的 R > P)
            "sucker_payoff": 1     # S
        })
        
        # 4. 运行模拟：学习者选择"合作"，对手选择默认的"背叛"
        print("\n--- 运行模拟: 选择合作 vs 理性对手 ---")
        result = simulator.run_simulation_step("Cooperate", "Defect")
        print(f"结果: 得分 {result.player_payoff}")
        print(f"洞察: {result.counter_intuitive_insight}")
        
        # 5. 运行模拟：学习者选择"背叛" (纳什均衡)
        print("\n--- 运行模拟: 选择背叛 vs 理性对手 ---")
        result_nash = simulator.run_simulation_step("Defect", "Defect")
        print(f"结果: 得分 {result_nash.player_payoff}")
        print(f"是否纳什均衡: {result_nash.is_nash_equilibrium}")
        print(f"洞察: {result_nash.counter_intuitive_insight}")

    except Exception as e:
        logger.error(f"运行时错误: {e}")