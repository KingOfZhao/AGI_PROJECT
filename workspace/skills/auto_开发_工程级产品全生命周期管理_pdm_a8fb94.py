"""
工程级产品全生命周期管理(PDM)移动端看板模拟器
通过Flutter状态管理树映射CAD的BOM装配树，实现工程变更指令(ECO)的级联影响分析
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PDM_ECO_Simulator")


@dataclass
class PartParameter:
    """零件参数数据结构"""
    name: str
    value: Union[float, int, str]
    unit: str
    is_critical: bool = False
    tolerances: Tuple[float, float] = (0.0, 0.0)


@dataclass
class Part:
    """零件节点数据结构"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    parameters: Dict[str, PartParameter] = field(default_factory=dict)
    children: List['Part'] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # 参数依赖关系
    eco_status: str = "UNAFFECTED"  # UNAFFECTED, AFFECTED, MODIFIED


class PDMECOSimulator:
    """工程变更指令(ECO)模拟器核心类"""
    
    def __init__(self):
        self.part_tree = self._build_sample_bom_tree()
        self.change_history: List[Dict] = []
        self.affected_parts: Set[str] = set()
        
    def _build_sample_bom_tree(self) -> Part:
        """构建示例BOM装配树"""
        root = Part(name="Assembly_Root")
        
        # 创建子部件
        sub_assembly1 = Part(name="SubAssembly_1")
        sub_assembly2 = Part(name="SubAssembly_2")
        
        # 添加零件参数
        sub_assembly1.parameters = {
            "length": PartParameter("length", 100.0, "mm", True, (98.0, 102.0)),
            "width": PartParameter("width", 50.0, "mm", True, (49.0, 51.0)),
            "material": PartParameter("material", "AL6061", "N/A")
        }
        
        sub_assembly2.parameters = {
            "length": PartParameter("length", 75.0, "mm", False, (73.5, 76.5)),
            "width": PartParameter("width", 40.0, "mm", False, (39.0, 41.0))
        }
        
        # 设置依赖关系 (当子部件1的length改变时，影响子部件2的width)
        sub_assembly1.dependencies = {
            "length": ["SubAssembly_2.width"]
        }
        
        # 添加到根节点
        root.children.extend([sub_assembly1, sub_assembly2])
        
        logger.info("Sample BOM tree constructed with %d top-level assemblies", len(root.children))
        return root
    
    def _validate_parameter_change(
        self, 
        part: Part, 
        param_name: str, 
        new_value: Union[float, int, str]
    ) -> bool:
        """验证参数变更是否合法"""
        if param_name not in part.parameters:
            logger.error("Parameter %s not found in part %s", param_name, part.name)
            return False
            
        param = part.parameters[param_name]
        
        # 类型检查
        if not isinstance(new_value, type(param.value)):
            logger.error(
                "Type mismatch for parameter %s. Expected %s, got %s",
                param_name, type(param.value), type(new_value)
            )
            return False
            
        # 数值范围检查
        if isinstance(new_value, (int, float)):
            min_val = param.value + param.tolerances[0]
            max_val = param.value + param.tolerances[1]
            if not (min_val <= new_value <= max_val):
                logger.warning(
                    "Value %s outside tolerance range (%s, %s) for parameter %s",
                    new_value, min_val, max_val, param_name
                )
                # 允许超出公差但记录警告
                
        return True
    
    def _find_part_by_name(self, part_name: str, current_part: Optional[Part] = None) -> Optional[Part]:
        """通过名称递归查找零件"""
        if current_part is None:
            current_part = self.part_tree
            
        if current_part.name == part_name:
            return current_part
            
        for child in current_part.children:
            found = self._find_part_by_name(part_name, child)
            if found:
                return found
                
        return None
    
    def apply_eco_change(
        self,
        part_name: str,
        param_name: str,
        new_value: Union[float, int, str],
        cascade: bool = True
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """
        应用工程变更指令(ECO)并分析影响
        
        Args:
            part_name: 要修改的零件名称
            param_name: 要修改的参数名称
            new_value: 新参数值
            cascade: 是否级联影响分析
            
        Returns:
            Tuple[成功状态, 受影响零件及参数字典]
            
        Example:
            >>> simulator = PDMECOSimulator()
            >>> success, affected = simulator.apply_eco_change(
            ...     "SubAssembly_1", "length", 102.5
            ... )
        """
        logger.info("Applying ECO: %s.%s = %s", part_name, param_name, new_value)
        
        # 重置影响状态
        self.affected_parts = set()
        impact_map: Dict[str, List[str]] = {}
        
        # 查找目标零件
        target_part = self._find_part_by_name(part_name)
        if not target_part:
            logger.error("Part %s not found in BOM tree", part_name)
            return False, impact_map
            
        # 验证参数变更
        if not self._validate_parameter_change(target_part, param_name, new_value):
            return False, impact_map
            
        # 应用变更
        old_value = target_part.parameters[param_name].value
        target_part.parameters[param_name].value = new_value
        target_part.eco_status = "MODIFIED"
        self.affected_parts.add(target_part.name)
        impact_map[target_part.name] = [param_name]
        
        # 记录变更历史
        change_record = {
            "part": part_name,
            "param": param_name,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": logging.Formatter.default_msec_format
        }
        self.change_history.append(change_record)
        
        # 级联影响分析
        if cascade and param_name in target_part.dependencies:
            for dep_ref in target_part.dependencies[param_name]:
                dep_part_name, dep_param = dep_ref.split(".")
                dep_part = self._find_part_by_name(dep_part_name)
                
                if dep_part:
                    dep_part.eco_status = "AFFECTED"
                    self.affected_parts.add(dep_part.name)
                    impact_map.setdefault(dep_part_name, []).append(dep_param)
                    logger.info(
                        "Cascade effect detected: %s.%s affected by %s.%s change",
                        dep_part_name, dep_param, part_name, param_name
                    )
        
        logger.info("ECO applied successfully. Affected parts: %s", self.affected_parts)
        return True, impact_map
    
    def get_eco_status_report(self) -> Dict[str, Dict[str, Union[str, List[str]]]]:
        """
        获取当前ECO状态报告
        
        Returns:
            包含所有零件状态和受影响参数的字典
            
        Example:
            >>> report = simulator.get_eco_status_report()
            >>> print(report["SubAssembly_1"]["status"])
        """
        report = {}
        
        def _traverse_tree(part: Part):
            report[part.name] = {
                "status": part.eco_status,
                "affected_params": [],
                "children": [child.name for child in part.children]
            }
            
            if part.eco_status != "UNAFFECTED":
                report[part.name]["affected_params"] = [
                    p for p in part.parameters 
                    if part.eco_status == "MODIFIED" or 
                    (part.eco_status == "AFFECTED" and p in part.dependencies)
                ]
            
            for child in part.children:
                _traverse_tree(child)
        
        _traverse_tree(self.part_tree)
        return report
    
    def reset_eco_status(self) -> None:
        """重置所有零件的ECO状态"""
        def _reset_tree(part: Part):
            part.eco_status = "UNAFFECTED"
            for child in part.children:
                _reset_tree(child)
        
        _reset_tree(self.part_tree)
        self.affected_parts = set()
        logger.info("ECO status reset for all parts")


def example_usage():
    """使用示例"""
    # 初始化模拟器
    pdm_simulator = PDMECOSimulator()
    
    # 应用工程变更
    success, impact = pdm_simulator.apply_eco_change(
        part_name="SubAssembly_1",
        param_name="length",
        new_value=102.5
    )
    
    if success:
        print("ECO applied successfully. Impact analysis:")
        for part, params in impact.items():
            print(f"- {part}: {', '.join(params)}")
    
    # 获取状态报告
    report = pdm_simulator.get_eco_status_report()
    print("\nECO Status Report:")
    for part, data in report.items():
        if data["status"] != "UNAFFECTED":
            print(f"{part}: {data['status']} (Affected: {', '.join(data['affected_params'])})")
    
    # 重置状态
    pdm_simulator.reset_eco_status()
    print("\nAfter reset:", pdm_simulator.get_eco_status_report()["SubAssembly_1"]["status"])


if __name__ == "__main__":
    example_usage()