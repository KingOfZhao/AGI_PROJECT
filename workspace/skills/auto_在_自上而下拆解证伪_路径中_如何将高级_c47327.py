"""
高级工艺参数到机台指令自动转换与路径搜索模块

该模块实现了在'自上而下拆解证伪'路径中的核心算法，旨在将高级工艺参数
（例如 '表面光洁度 Ra0.4'）自动分解为底层可执行的机台指令序列（G-code修正）。
系统利用现有的SKILL节点库（模拟1932个节点），通过蒙特卡洛树搜索(MCTS)
寻找从参数到指令的最短因果路径。

Input Format:
    - param_name: str (e.g., "surface_roughness")
    - param_value: float (e.g., 0.4)
    - skill_graph: Dict representing the knowledge graph.

Output Format:
    - result: Dict containing 'g_code_sequence' (List[str]), 
              'path' (List[str]), and 'confidence' (float).
"""

import math
import random
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Skill_Decomposer")

@dataclass
class SkillNode:
    """
    SKILL节点数据结构，表示知识图谱中的一个原子能力。
    """
    node_id: str
    description: str
    node_type: str  # 'param', 'process', 'machine_action', 'gcode'
    input_req: Dict[str, Any] = field(default_factory=dict)
    output_eff: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)

class MCTSNode:
    """
    蒙特卡洛树搜索节点。
    """
    def __init__(self, state: str, parent: Optional['MCTSNode'] = None):
        self.state = state  # 当前节点ID或状态描述
        self.parent = parent
        self.children: List[MCTSNode] = []
        self.visit_count = 0
        self.win_score = 0.0  # 这里的"win"代表更接近目标或路径更优

    def calculate_ucb(self, exploration_param: float = 1.41) -> float:
        """计算UCB1值"""
        if self.visit_count == 0:
            return float('inf')
        exploitation = self.win_score / self.visit_count
        exploration = math.sqrt(math.log(self.parent.visit_count) / self.visit_count) if self.parent else 0
        return exploitation + exploration_param * exploration

    def select_child(self) -> 'MCTSNode':
        """选择UCB值最大的子节点"""
        return max(self.children, key=lambda child: child.calculate_ucb())

    def expand(self, skill_graph: Dict[str, SkillNode]):
        """扩展节点"""
        current_node_data = skill_graph.get(self.state)
        if not current_node_data:
            return
        
        for child_id in current_node_data.children:
            if not any(c.state == child_id for c in self.children):
                self.children.append(MCTSNode(state=child_id, parent=self))

    def is_fully_expanded(self, skill_graph: Dict[str, SkillNode]) -> bool:
        """检查是否完全扩展"""
        node_data = skill_graph.get(self.state)
        if not node_data:
            return False
        return len(self.children) == len(node_data.children)

class PrecisionManufacturingDecomposer:
    """
    核心类：处理高级参数到底层指令的分解。
    """
    
    def __init__(self, skill_repository: Dict[str, SkillNode]):
        self.skill_repository = skill_repository
        logger.info(f"Decomposer initialized with {len(skill_repository)} skills.")

    def validate_input(self, param_name: str, param_value: float) -> bool:
        """
        输入数据验证和边界检查。
        """
        if not isinstance(param_name, str) or not param_name.strip():
            logger.error("Parameter name must be a non-empty string.")
            raise ValueError("Invalid parameter name")
        
        if not isinstance(param_value, (int, float)) or param_value <= 0:
            logger.error(f"Parameter value must be positive number, got {param_value}")
            raise ValueError("Invalid parameter value")
            
        logger.debug(f"Input validated: {param_name}={param_value}")
        return True

    def find_optimal_path_mcts(self, root_state: str, target_state_type: str, iterations: int = 1000) -> Optional[MCTSNode]:
        """
        使用蒙特卡洛树搜索(MCTS)在SKILL图谱中寻找最优路径。
        
        Args:
            root_state: 起始节点ID (高级参数)
            target_state_type: 目标节点类型 (如 'gcode')
            iterations: 模拟迭代次数
            
        Returns:
            最佳目标节点或None
        """
        root = MCTSNode(state=root_state)
        
        for i in range(iterations):
            node = root
            
            # 1. Selection (选择)
            while node.children and node.is_fully_expanded(self.skill_repository):
                node = node.select_child()
            
            # 2. Expansion (扩展)
            if node.visit_count > 0 or node == root:
                node.expand(self.skill_repository)
                if node.children:
                    node = random.choice(node.children)
            
            # 3. Simulation (模拟)
            current_sim_state = node.state
            depth = 0
            max_depth = 20
            path_found = False
            
            # 随机游走直到找到目标类型或达到最大深度
            while depth < max_depth:
                node_data = self.skill_repository.get(current_sim_state)
                if not node_data:
                    break
                
                if node_data.node_type == target_state_type:
                    path_found = True
                    break
                
                if not node_data.children:
                    break
                
                current_sim_state = random.choice(node_data.children)
                depth += 1
            
            # 4. Backpropagation (反向传播)
            # 奖励函数：如果找到目标，得分高；路径越短，得分越高
            score = 0.0
            if path_found:
                score = 100.0 / (depth + 1)  # 鼓励短路径
            
            temp_node = node
            while temp_node:
                temp_node.visit_count += 1
                temp_node.win_score += score
                temp_node = temp_node.parent

        # 返回访问次数最多的子节点路径中的最佳叶节点
        best_child = max(root.children, key=lambda c: c.visit_count) if root.children else None
        logger.info(f"MCTS completed. Best child visit count: {best_child.visit_count if best_child else 0}")
        return best_child

    def _translate_param_to_gcode(self, path: List[str], target_value: float) -> List[str]:
        """
        辅助函数：根据路径和目标值生成具体的G-code修正指令。
        这是一个简化的映射逻辑，实际AGI需结合物理引擎。
        """
        gcode_sequence = []
        logger.info(f"Translating path: {' -> '.join(path)}")
        
        # 模拟简单的逻辑映射
        # 假设路径中包含了 "adjust_spindle_speed" 和 "adjust_feed_rate"
        if "adjust_spindle_speed" in path:
            # 简单的启发式：光洁度要求越高，转速越高
            rpm = int(3000 / target_value) 
            gcode_sequence.append(f"G97 S{rpm} M03 (Set spindle speed for Ra {target_value})")
            
        if "adjust_feed_rate" in path:
            # 进给率降低以提高光洁度
            feed = round(0.1 * target_value, 3)
            gcode_sequence.append(f"G01 F{feed} (Set feed rate)")
            
        if "tool_path_fine_tuning" in path:
            gcode_sequence.append("G41 D01 (Tool radius compensation left)")
            
        gcode_sequence.append(f"(End of sequence for Ra {target_value})")
        return gcode_sequence

    def decompose_parameter(self, param_name: str, param_value: float) -> Dict[str, Any]:
        """
        主函数：执行自上而下的分解证伪流程。
        
        Args:
            param_name: 高级参数名 (需匹配SKILL库中的ID)
            param_value: 参数值
            
        Returns:
            包含G-code序列和执行路径的字典
        """
        try:
            self.validate_input(param_name, param_value)
            
            # 检查起始节点是否存在
            if param_name not in self.skill_repository:
                logger.error(f"Skill node '{param_name}' not found in repository.")
                return {"error": "Skill not found", "g_code_sequence": []}

            logger.info(f"Starting decomposition for {param_name}={param_value}")
            
            # 运行MCTS寻找路径
            # 目标是找到类型为 'gcode' 的节点
            best_node = self.find_optimal_path_mcts(param_name, "gcode")
            
            if not best_node:
                logger.warning("MCTS failed to find a valid path to G-code.")
                return {"error": "Path not found", "g_code_sequence": []}

            # 重构路径
            path = []
            curr = best_node
            while curr:
                path.append(curr.state)
                curr = curr.parent
            path.reverse() # 从根到叶
            
            # 生成指令
            gcode_instructions = self._translate_param_to_gcode(path, param_value)
            
            return {
                "status": "success",
                "path": path,
                "g_code_sequence": gcode_instructions,
                "confidence": best_node.win_score / best_node.visit_count if best_node.visit_count > 0 else 0
            }
            
        except Exception as e:
            logger.exception("Error during parameter decomposition")
            return {"error": str(e), "g_code_sequence": []}

# --- Mock Data Generation for Demonstration ---
def _load_mock_skill_repository() -> Dict[str, SkillNode]:
    """构建模拟的制造知识图谱"""
    return {
        "surface_roughness": SkillNode("surface_roughness", "Control Surface Finish", "param", children=["thermal_control", "kinematic_optimization"]),
        "thermal_control": SkillNode("thermal_control", "Manage Heat Affected Zone", "process", children=["coolant_adjustment"]),
        "kinematic_optimization": SkillNode("kinematic_optimization", "Optimize Movement Dynamics", "process", children=["adjust_spindle_speed", "adjust_feed_rate"]),
        "coolant_adjustment": SkillNode("coolant_adjustment", "Change Coolant Concentration", "machine_action", children=["gcode_coolant_valve"]),
        "adjust_spindle_speed": SkillNode("adjust_spindle_speed", "Modify RPM", "machine_action", children=["gcode_spindle"]),
        "adjust_feed_rate": SkillNode("adjust_feed_rate", "Modify Feed per Tooth", "machine_action", children=["gcode_feed"]),
        "gcode_coolant_valve": SkillNode("gcode_coolant_valve", "M08/M09", "gcode"),
        "gcode_spindle": SkillNode("gcode_spindle", "G97 S...", "gcode"),
        "gcode_feed": SkillNode("gcode_feed", "G01 F...", "gcode"),
    }

if __name__ == "__main__":
    # 使用示例
    mock_skills = _load_mock_skill_repository()
    decomposer = PrecisionManufacturingDecomposer(mock_skills)
    
    # 场景：将表面光洁度 Ra0.4 分解为 G-code
    result = decomposer.decompose_parameter("surface_roughness", 0.4)
    
    print("\n--- Decomposition Result ---")
    print(json.dumps(result, indent=2))