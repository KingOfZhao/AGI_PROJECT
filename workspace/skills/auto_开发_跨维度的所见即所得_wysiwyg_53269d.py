"""
跨维度钣金展开与制造模块

本模块实现了面向AGI系统的钣金展开算法，支持：
- 3D钣金参数到2D展开图的实时转换
- 折弯补偿计算（K因子/中性层）
- 加工G代码生成（切割路径）
- 展开图几何数据导出（JSON格式）

输入格式：
{
    "length": 100.0,      # 长度
    "width": 50.0,        # 宽度
    "thickness": 2.0,     # 板厚
    "bend_angle": 90.0,   # 折弯角度（度）
    "bend_radius": 3.0,   # 折弯内半径
    "k_factor": 0.4       # 中性层系数
}

输出格式：
{
    "flat_pattern": {...},  # 展开图几何数据
    "gcode": "G01 X...",    # 加工指令
    "bend_deduction": 4.2  # 折弯扣除量
}
"""

import math
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SheetMetalParams:
    """钣金参数数据类"""
    length: float          # 长度
    width: float           # 宽度
    thickness: float       # 板厚
    bend_angle: float      # 折弯角度（度）
    bend_radius: float     # 折弯内半径
    k_factor: float = 0.4  # 中性层系数 (默认0.4)

    def __post_init__(self):
        """数据验证"""
        if self.length <= 0 or self.width <= 0:
            raise ValueError("长度和宽度必须为正数")
        if self.thickness <= 0:
            raise ValueError("板厚必须为正数")
        if not (0 <= self.bend_angle <= 180):
            raise ValueError("折弯角度必须在0-180度之间")
        if self.bend_radius < 0:
            raise ValueError("折弯半径不能为负")
        if not (0 <= self.k_factor <= 0.5):
            logger.warning(f"K因子{self.k_factor}超出常规范围(0-0.5)")


@dataclass
class Point2D:
    """二维坐标点"""
    x: float
    y: float

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}


@dataclass
class Line2D:
    """二维线段"""
    start: Point2D
    end: Point2D

    def to_dict(self) -> Dict[str, Dict]:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict()
        }


class SheetMetalUnfolder:
    """钣金展开计算引擎"""
    
    def __init__(self, params: SheetMetalParams):
        """初始化展开计算器
        
        Args:
            params: 钣金参数对象
        """
        self.params = params
        self._validate_params()
        logger.info(f"初始化钣金展开器: {params}")
        
    def _validate_params(self) -> None:
        """内部参数验证"""
        if self.params.bend_radius < self.params.thickness * 0.5:
            logger.warning(
                f"折弯半径{self.params.bend_radius}小于最小推荐值"
                f"{self.params.thickness * 0.5}"
            )
    
    def calculate_bend_deduction(self) -> float:
        """计算折弯扣除量
        
        基于经验公式：BD = 2*(T + R)*tan(A/2) - (π/180)*A*(R + K*T)
        
        Returns:
            float: 折弯扣除量
        """
        T = self.params.thickness
        R = self.params.bend_radius
        A = math.radians(self.params.bend_angle)
        K = self.params.k_factor
        
        # 计算折弯扣除量
        bend_allowance = (math.pi / 180) * self.params.bend_angle * (R + K * T)
        outside_setback = (T + R) * math.tan(A / 2)
        bend_deduction = 2 * outside_setback - bend_allowance
        
        logger.debug(f"折弯扣除量计算: BD={bend_deduction:.3f}")
        return round(bend_deduction, 4)
    
    def generate_flat_pattern(self) -> Dict[str, Union[List[Dict], float]]:
        """生成2D展开图几何数据
        
        Returns:
            包含顶点、边和尺寸的字典
        """
        try:
            # 计算展开长度
            bend_deduction = self.calculate_bend_deduction()
            flat_length = self.params.length + self.params.width - bend_deduction
            
            # 生成顶点
            vertices = [
                Point2D(0, 0),
                Point2D(self.params.length, 0),
                Point2D(self.params.length, self.params.width - bend_deduction),
                Point2D(flat_length, self.params.width - bend_deduction),
                Point2D(flat_length, self.params.width - bend_deduction + self.params.width),
                Point2D(0, self.params.width - bend_deduction + self.params.width)
            ]
            
            # 生成边
            edges = [
                Line2D(vertices[0], vertices[1]),
                Line2D(vertices[1], vertices[2]),
                Line2D(vertices[2], vertices[3]),
                Line2D(vertices[3], vertices[4]),
                Line2D(vertices[4], vertices[5]),
                Line2D(vertices[5], vertices[0])
            ]
            
            # 转换为可序列化格式
            result = {
                "vertices": [v.to_dict() for v in vertices],
                "edges": [e.to_dict() for e in edges],
                "dimensions": {
                    "flat_length": flat_length,
                    "flat_width": self.params.width,
                    "bend_deduction": bend_deduction
                }
            }
            
            logger.info("展开图生成成功")
            return result
            
        except Exception as e:
            logger.error(f"展开图生成失败: {str(e)}")
            raise RuntimeError(f"展开计算错误: {str(e)}") from e
    
    def generate_gcode(self, feed_rate: int = 1000) -> str:
        """生成切割G代码
        
        Args:
            feed_rate: 进给速度 (mm/min)
            
        Returns:
            G代码字符串
        """
        try:
            pattern = self.generate_flat_pattern()
            vertices = pattern["vertices"]
            
            gcode_lines = [
                "G21 ; 设置单位为毫米",
                "G90 ; 绝对坐标模式",
                f"G1 F{feed_rate} ; 设置进给速度",
                "G0 Z5 ; 抬起切割头",
                f"G0 X{vertices[0]['x']} Y{vertices[0]['y']} ; 移动到起点",
                "M3 S1000 ; 启动激光",
                "G1 Z0 ; 下降切割头"
            ]
            
            # 添加切割路径
            for vertex in vertices[1:]:
                gcode_lines.append(
                    f"G1 X{vertex['x']:.3f} Y{vertex['y']:.3f}"
                )
            
            # 返回起点并结束
            gcode_lines.extend([
                f"G1 X{vertices[0]['x']:.3f} Y{vertices[0]['y']:.3f} ; 闭合路径",
                "G0 Z5 ; 抬起切割头",
                "M5 ; 关闭激光",
                "G0 X0 Y0 ; 返回原点",
                "M30 ; 程序结束"
            ])
            
            logger.info("G代码生成成功")
            return "\n".join(gcode_lines)
            
        except Exception as e:
            logger.error(f"G代码生成失败: {str(e)}")
            raise RuntimeError(f"G代码生成错误: {str(e)}") from e


def export_to_json(data: Dict, filepath: str) -> bool:
    """将展开数据导出为JSON文件
    
    Args:
        data: 要导出的数据字典
        filepath: 输出文件路径
        
    Returns:
        bool: 导出是否成功
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"数据已导出到 {filepath}")
        return True
    except IOError as e:
        logger.error(f"文件导出失败: {str(e)}")
        return False


# 使用示例
if __name__ == "__main__":
    # 示例1: 基本钣金展开
    try:
        params = SheetMetalParams(
            length=100.0,
            width=50.0,
            thickness=2.0,
            bend_angle=90.0,
            bend_radius=3.0
        )
        
        unfolder = SheetMetalUnfolder(params)
        
        # 计算展开图
        pattern = unfolder.generate_flat_pattern()
        print("\n展开图数据:")
        print(json.dumps(pattern, indent=2))
        
        # 生成G代码
        gcode = unfolder.generate_gcode(feed_rate=1200)
        print("\n生成的G代码:")
        print(gcode)
        
        # 导出到文件
        export_data = {
            "params": params.__dict__,
            "flat_pattern": pattern,
            "gcode": gcode.split("\n")
        }
        export_to_json(export_data, "sheet_metal_output.json")
        
    except Exception as e:
        logger.error(f"示例执行失败: {str(e)}")