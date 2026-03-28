"""
Module: auto_cognitive_exoskeleton_protocol
Description: 认知外骨骼与界面重构协议。
             将游戏'修改器'思维引入通用教育界面，允许AI作为中介，
             将'不适合人类处理的格式'实时转码为'最适合该个体认知特征的格式'。
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InputFormat(Enum):
    """输入数据格式枚举"""
    TEXT_DENSE = "text_dense"
    TEXT_LOGIC = "text_logic"
    DATA_RAW = "data_raw"
    AUDIO_STREAM = "audio_stream"

class OutputFormat(Enum):
    """输出认知格式枚举"""
    VISUAL_SPATIAL = "visual_spatial"  # 视觉空间结构
    TEXT_SIMPLIFIED = "text_simplified" # 简化文本
    INTERACTIVE_SANDBOX = "interactive_sandbox" # 交互沙盒
    ABSTRACT_CONCEPT = "abstract_concept" # 抽象概念图

@dataclass
class CognitiveProfile:
    """用户的认知特征画像"""
    user_id: str
    processing_speed: float = 1.0  # 0.5 (慢) to 2.0 (快)
    memory_capacity: str = "average"  # low, average, high
    preferred_modality: OutputFormat = OutputFormat.VISUAL_SPATIAL
    neurotype: str = "neurotypical"  # e.g., neurotypical, adhd, dyslexic, autistic

@dataclass
class InterfaceParameters:
    """界面底层的'修改器'参数"""
    time_dilation_factor: float = 1.0  # 时间流速修改
    information_density: float = 1.0   # 信息密度 (0.1 sparse to 5.0 dense)
    feedback_intensity: str = "normal" # positive, neutral, normal
    error_tolerance: float = 0.8       # 容错率

@dataclass
class EducationalContent:
    """教育内容数据结构"""
    content_id: str
    raw_data: str
    format_type: InputFormat
    complexity_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class CognitiveExoskeleton:
    """
    认知外骨骼核心类。
    负责解析用户认知特征，动态调整界面参数，并转码内容格式。
    """
    
    def __init__(self, user_profile: CognitiveProfile):
        self.profile = user_profile
        self.interface_params = InterfaceParameters()
        self._calibrate_interface()
        logger.info(f"Cognitive Exoskeleton initialized for user {user_profile.user_id}")

    def _calibrate_interface(self) -> None:
        """
        [辅助函数] 根据用户画像校准界面参数。
        模拟游戏开始前的'画质/难度'自动检测。
        """
        try:
            # 针对神经多样性的特定调整
            if self.profile.neurotype == "adhd":
                self.interface_params.time_dilation_factor = 1.5 # 加快反馈
                self.interface_params.information_density = 0.6  # 降低密度防止过载
                self.interface_params.feedback_intensity = "high_contrast"
            elif self.profile.neurotype == "dyslexic":
                self.interface_params.information_density = 0.4
                # 强制使用非纯文本格式
                self.profile.preferred_modality = OutputFormat.VISUAL_SPATIAL
            
            # 边界检查
            self.interface_params.time_dilation_factor = max(0.1, min(5.0, self.interface_params.time_dilation_factor))
            self.interface_params.information_density = max(0.1, min(5.0, self.interface_params.information_density))
            
            logger.debug(f"Interface calibrated: {self.interface_params}")
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            raise RuntimeError("Failed to calibrate cognitive interface") from e

    def transcode_content(self, content: EducationalContent) -> Dict[str, Any]:
        """
        [核心函数 1] 内容转码器。
        将原始教育内容转换为适合当前用户认知特征的最佳格式。
        
        Args:
            content (EducationalContent): 原始教育内容对象
            
        Returns:
            Dict[str, Any]: 包含转码后数据和新界面参数的字典
        """
        if not content.raw_data:
            raise ValueError("Content raw_data cannot be empty")

        start_time = time.time()
        logger.info(f"Transcoding content {content.content_id} for modality {self.profile.preferred_modality}")

        processed_data: Union[str, Dict]
        
        try:
            # 模拟AI转码逻辑
            if self.profile.preferred_modality == OutputFormat.VISUAL_SPATIAL:
                processed_data = self._convert_to_visual_structure(content)
            elif self.profile.preferred_modality == OutputFormat.TEXT_SIMPLIFIED:
                processed_data = self._simplify_text(content)
            else:
                processed_data = content.raw_data # Fallback

            # 应用时间修改参数 (模拟)
            processing_delay = 0.1 * self.interface_params.time_dilation_factor
            time.sleep(processing_delay) # 仅用于模拟时间流速感知

            result = {
                "transcoded_content": processed_data,
                "active_modifiers": {
                    "density": self.interface_params.information_density,
                    "time_flow": self.interface_params.time_dilation_factor
                },
                "original_format": content.format_type.value,
                "target_format": self.profile.preferred_modality.value
            }
            
            logger.info(f"Transcoding completed in {time.time() - start_time:.4f}s")
            return result

        except Exception as e:
            logger.error(f"Error during transcoding: {e}")
            return {"error": str(e), "fallback": content.raw_data}

    def real_time_adapt(self, engagement_signal: Dict[str, float]) -> InterfaceParameters:
        """
        [核心函数 2] 实时适应接口。
        类似游戏中的'动态难度调整'，根据实时生物反馈或交互数据修改界面。
        
        Args:
            engagement_signal (Dict[str, float]): 包含 'focus', 'stress', 'progress' 的字典
            
        Returns:
            InterfaceParameters: 更新后的界面参数对象
        """
        focus = engagement_signal.get('focus', 0.5)
        stress = engagement_signal.get('stress', 0.5)
        
        # 数据验证
        if not (0 <= focus <= 1 and 0 <= stress <= 1):
            logger.warning("Invalid signal range detected. Clamping values.")
            focus = max(0, min(1, focus))
            stress = max(0, min(1, stress))

        logger.debug(f"Adapting interface based on Focus: {focus}, Stress: {stress}")

        # 动态逻辑：如果压力高，降低密度；如果专注高，增加密度
        if stress > 0.8:
            self.interface_params.information_density *= 0.9
            self.interface_params.time_dilation_factor *= 1.1 # 放慢时间
            logger.info("High stress detected: Reducing density, slowing time.")
        elif focus > 0.8:
            self.interface_params.information_density = min(5.0, self.interface_params.information_density * 1.05)
            logger.info("High focus detected: Increasing information density.")

        return self.interface_params

    # --- 以下是内部转换辅助逻辑 ---
    
    def _convert_to_visual_structure(self, content: EducationalContent) -> Dict[str, Any]:
        """将线性文本转换为视觉空间节点图结构"""
        # 这里是模拟逻辑，实际AGI环境会调用LLM或视觉模型
        return {
            "type": "mind_map",
            "central_node": content.content_id,
            "edges": [
                {"node": "Concept A", "distance": 10 * (1/self.interface_params.information_density)},
                {"node": "Concept B", "distance": 20 * (1/self.interface_params.information_density)}
            ],
            "raw_preview": content.raw_data[:50] + "..."
        }

    def _simplify_text(self, content: EducationalContent) -> str:
        """简化文本逻辑，增加间距"""
        words = content.raw_data.split()
        chunk_size = int(10 * self.interface_params.information_density)
        chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        return "\n\n".join(chunks)

# 使用示例
if __name__ == "__main__":
    # 1. 创建用户画像 (假设为ADHD用户，处理速度慢，偏好视觉)
    user = CognitiveProfile(
        user_id="user_999",
        processing_speed=0.8,
        neurotype="adhd",
        preferred_modality=OutputFormat.VISUAL_SPATIAL
    )

    # 2. 初始化外骨骼
    exoskeleton = CognitiveExoskeleton(user)

    # 3. 准备原始高密度教育内容
    raw_content = EducationalContent(
        content_id="phy_101",
        raw_data="Quantum mechanics is a fundamental theory in physics that provides a description of the physical properties of nature at the scale of atoms and subatomic particles. It is the foundation of all quantum physics including quantum chemistry, quantum field theory, quantum technology, and quantum information science.",
        format_type=InputFormat.TEXT_DENSE,
        complexity_score=0.9
    )

    # 4. 执行转码 (将高密度文本转为视觉结构)
    result = exoskeleton.transcode_content(raw_content)
    print("\n--- Transcoded Result ---")
    print(f"Target Format: {result['target_format']}")
    print(f"Content Structure: {result['transcoded_content']}")

    # 5. 模拟实时适应 (检测到用户压力大)
    bio_feedback = {"focus": 0.4, "stress": 0.9, "progress": 0.2}
    new_params = exoskeleton.real_time_adapt(bio_feedback)
    print("\n--- Adapted Parameters ---")
    print(f"New Density: {new_params.information_density:.2f}")
    print(f"New Time Flow: {new_params.time_dilation_factor:.2f}")