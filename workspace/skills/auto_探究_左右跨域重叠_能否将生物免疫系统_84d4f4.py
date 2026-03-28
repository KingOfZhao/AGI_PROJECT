"""
模块名称: auto_探究_左右跨域重叠_能否将生物免疫系统_84d4f4
描述: 探究'左右跨域重叠'：构建'工业免疫网络'，将设备异常特征视为抗原，
      历史维修方案视为抗体。验证跨域迁移是否能比传统模式识别更早发现'亚健康'状态。
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from sklearn.preprocessing import MinMaxScaler

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ImmuneUnit:
    """
    免疫单元基类（通用结构）。
    """
    id: str
    feature_vector: np.ndarray  # 特征向量 (归一化后)
    label: str = "Unknown"      # 标签 (如 'Normal', 'Bearing_Fault', 'SubHealth')
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.feature_vector, np.ndarray):
            raise TypeError("feature_vector 必须是 numpy.ndarray 类型")

@dataclass
class Antibody(ImmuneUnit):
    """
    抗体类：代表已知的历史故障模式及对应的维修方案。
    """
    repair_solution: str = "To be defined"  # 维修/应对方案

@dataclass
class Antigen(ImmuneUnit):
    """
    抗原类：代表实时监测到的设备状态特征。
    """
    is_detected: bool = False
    matched_antibody_id: Optional[str] = None

class IndustrialImmuneNetwork:
    """
    工业免疫网络核心类。
    
    模拟生物免疫系统，通过计算抗原（实时数据）与抗体（历史知识）之间的
    亲和力（Affinity，即特征空间的距离/相似度）来诊断设备状态。
    
    核心假设：相比传统阈值报警，基于形状匹配的免疫机制能识别特征向量
    微小偏移产生的"亚健康"状态（非典型故障模式）。
    """
    
    def __init__(self, affinity_threshold: float = 0.15, early_warning_factor: float = 1.5):
        """
        初始化网络。
        
        Args:
            affinity_threshold (float): 判定为"已识别"的最大距离阈值（0-1之间）。
            early_warning_factor (float): 用于检测"亚健康"的系数。
        """
        if not (0 < affinity_threshold < 1):
            raise ValueError("affinity_threshold 必须在 0 和 1 之间")
            
        self.antibodies: List[Antibody] = []
        self.scaler = MinMaxScaler()
        self.is_fitted = False
        self.affinity_threshold = affinity_threshold
        self.early_warning_factor = early_warning_factor
        logger.info("工业免疫网络初始化完成。阈值: %.3f", affinity_threshold)

    def register_antibodies(self, antibody_data: List[Dict[str, Any]]) -> None:
        """
        注册抗体（训练阶段）。将历史故障特征注入网络，构建免疫记忆库。
        
        Args:
            antibody_data: 包含抗体信息的字典列表。
                           格式: [{'id': str, 'features': List[float], 'label': str, 'solution': str}, ...]
        """
        if not antibody_data:
            raise ValueError("抗体数据不能为空")

        raw_features = []
        temp_antibodies = []

        try:
            # 数据提取与初步验证
            for item in antibody_data:
                if 'features' not in item or 'id' not in item:
                    logger.warning(f"跳过无效数据项: {item}")
                    continue
                
                vec = np.array(item['features'], dtype=float)
                if vec.ndim != 1:
                    raise ValueError(f"ID {item['id']} 的特征维度错误，必须是一维数组")
                
                raw_features.append(vec)
                temp_antibodies.append(item)

            if not raw_features:
                raise RuntimeError("没有有效的抗体数据可供注册")

            # 归一化特征向量 (0-1 scaling) 以便计算欧式距离作为亲和力
            # 注意：这里假设抗原也会使用同样的scaler进行transform
            fitted_features = self.scaler.fit_transform(raw_features)

            for item, norm_vec in zip(temp_antibodies, fitted_features):
                antibody = Antibody(
                    id=item['id'],
                    feature_vector=norm_vec,
                    label=item.get('label', 'General_Fault'),
                    repair_solution=item.get('solution', 'Check Manual'),
                    metadata=item.get('metadata', {})
                )
                self.antibodies.append(antibody)

            self.is_fitted = True
            logger.info(f"成功注册 {len(self.antibodies)} 个抗体。免疫记忆库构建完成。")

        except Exception as e:
            logger.error(f"注册抗体失败: {str(e)}")
            raise

    def _calculate_affinity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        辅助函数：计算两个特征向量之间的亲和力（距离）。
        使用欧式距离，值越小表示亲和力越高（越相似）。
        
        Args:
            vec1: 归一化特征向量1
            vec2: 归一化特征向量2
            
        Returns:
            float: 欧式距离 (0 到 sqrt(D) 之间，归一化后通常 < 2)
        """
        # 边界检查
        if vec1.shape != vec2.shape:
            raise ValueError("特征向量维度不匹配")
        
        return np.linalg.norm(vec1 - vec2)

    def diagnose(self, real_time_data: Dict[str, List[float]]) -> Dict[str, Any]:
        """
        核心功能：诊断实时数据（抗原）。
        遍历免疫库，寻找匹配的抗体，并检测亚健康状态。
        
        Args:
            real_time_data: 字典，包含 'id' 和 'features'。
                            格式: {'id': 'sensor_001', 'features': [0.1, 0.5, ...]}
        
        Returns:
            Dict: 诊断报告，包含状态、匹配的抗体、建议方案和风险评分。
        """
        if not self.is_fitted:
            raise RuntimeError("网络尚未训练，请先调用 register_antibodies")
        
        if 'features' not in real_time_data:
            raise ValueError("输入数据缺少 'features' 字段")

        try:
            # 1. 数据预处理
            raw_vec = np.array(real_time_data['features']).reshape(1, -1)
            norm_vec = self.scaler.transform(raw_vec).flatten() # 保持与训练数据一致的缩放
            
            antigen = Antigen(id=real_time_data.get('id', 'unknown'), feature_vector=norm_vec)
            
            min_distance = float('inf')
            best_match: Optional[Antibody] = None
            distances = []

            # 2. 遍历抗体库（模拟免疫识别过程）
            for antibody in self.antibodies:
                dist = self._calculate_affinity(antigen.feature_vector, antibody.feature_vector)
                distances.append(dist)
                
                if dist < min_distance:
                    min_distance = dist
                    best_match = antibody
            
            # 3. 状态判定逻辑 (跨域探究核心)
            # 传统模式识别通常是 if dist < threshold: fault else: normal
            # 免疫网络探究：引入"亚健康"（Sub-Health）中间态
            
            status = "Normal"
            diagnosis_detail = "系统运行正常，无匹配抗原。"
            
            # 计算全局平均距离作为基准
            avg_distance = np.mean(distances) if distances else 0
            
            if min_distance <= self.affinity_threshold:
                status = "Fault_Detected"
                diagnosis_detail = f"检测到已知故障模式: {best_match.label}"
                antigen.is_detected = True
                antigen.matched_antibody_id = best_match.id
            elif min_distance <= (self.affinity_threshold * self.early_warning_factor):
                # 即使没有完全匹配，如果距离接近阈值，视为"亚健康"
                status = "Sub_Health"
                diagnosis_detail = "检测到异常特征偏移，疑似亚健康状态（未知抗原）。"
                logger.warning(f"亚健康预警！距离: {min_distance:.4f}, 阈值: {self.affinity_threshold}")
            elif min_distance < avg_distance * 0.8: # 额外的启发式检查
                status = "Watchlist"
                diagnosis_detail = "特征趋向异常，建议关注。"

            # 4. 生成报告
            report = {
                "antigen_id": antigen.id,
                "status": status,
                "detail": diagnosis_detail,
                "affinity_score": float(min_distance),
                "matched_antibody_id": antigen.matched_antibody_id,
                "recommended_action": best_match.repair_solution if best_match and status == "Fault_Detected" else "Continue Monitoring",
                "timestamp": np.datetime64('now').astype(str)
            }
            
            logger.info(f"诊断完成 - ID: {antigen.id}, 状态: {status}, 亲和力: {min_distance:.4f}")
            return report

        except Exception as e:
            logger.error(f"诊断过程中发生错误: {str(e)}")
            return {"error": str(e), "status": "System_Error"}

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 模拟数据：工业设备的振动和温度特征 [vib_x, vib_y, temp, pressure]
    # 假设正常范围是归一化后的 [0.1, 0.1, 0.2, 0.15] 附近
    
    # 1. 构建历史知识库 (抗体)
    history_faults = [
        {
            "id": "AB_001_Bearing_Wear", 
            "features": [0.8, 0.9, 0.7, 0.2], 
            "label": "Bearing Wear", 
            "solution": "Replace Bearing ASAP"
        },
        {
            "id": "AB_002_Overheat", 
            "features": [0.2, 0.3, 0.95, 0.9], 
            "label": "System Overheat", 
            "solution": "Check Cooling System"
        },
        {
            "id": "AB_003_Lubrication", 
            "features": [0.4, 0.5, 0.3, 0.1], 
            "label": "Low Lubrication", 
            "solution": "Add Oil"
        }
    ]

    # 2. 初始化网络
    # 阈值设为 0.2 (归一化后的欧式距离)
    # 这意味着如果特征向量的几何距离小于0.2，则认为是同类故障
    immune_net = IndustrialImmuneNetwork(affinity_threshold=0.2, early_warning_factor=1.8)
    
    # 3. 训练 (注入抗体)
    immune_net.register_antibodies(history_faults)

    # 4. 实时监测 (输入抗原)
    
    # Case A: 正常状态
    test_case_normal = {"id": "Sensor_A", "features": [0.1, 0.1, 0.2, 0.1]}
    
    # Case B: 明显的轴承磨损故障 (与 AB_001 接近)
    test_case_fault = {"id": "Sensor_B", "features": [0.75, 0.88, 0.65, 0.25]}
    
    # Case C: 亚健康/未知异常 (处于正常和故障之间，不直接匹配任何已知，但偏离正常)
    # 这个特征点距离 AB_001 可能是 0.3 左右 (大于 0.2)，但小于 0.2 * 1.8 = 0.36
    test_case_subhealth = {"id": "Sensor_C", "features": [0.6, 0.7, 0.5, 0.2]}

    print("\n--- 诊断报告 ---")
    
    print(f"\nCase A (Normal): {immune_net.diagnose(test_case_normal)['status']}")
    
    report_b = immune_net.diagnose(test_case_fault)
    print(f"\nCase B (Fault): {report_b['status']} -> Action: {report_b['recommended_action']}")
    
    report_c = immune_net.diagnose(test_case_subhealth)
    print(f"\nCase C (SubHealth): {report_c['status']} -> Detail: {report_c['detail']}")