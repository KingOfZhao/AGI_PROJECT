"""
数字组织相容性免疫系统

该模块实现了一个动态的数字免疫系统，旨在保护分布式系统免受未知攻击。
不同于传统的静态防火墙，该系统通过学习“自我”的数学表征来识别“非我”抗原。
当检测到异常流量或逻辑时，系统会模拟生物免疫反应，生成特定的“抗体”
（微服务补丁或隔离策略）并部署，从而赋予系统主动进化的能力。

核心概念:
- Self (自我): 正常业务逻辑与流量模式的统计基线。
- Non-Self (非我): 偏离基线的异常模式（抗原）。
- T-Cell (T细胞): 核心决策逻辑，负责分析抗原并生成抗体。
- Antibody (抗体): 针对特定威胁的防御代码或策略。

输入格式:
- TrafficData: 包含 'latency', 'packet_size', 'request_rate' 等数值特征的字典。

输出格式:
- AntibodyResponse: 包含 'status', 'antibody_id', 'patch_code', 'isolation_rule' 的字典。
"""

import logging
import statistics
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DigitalImmuneSystem")


@dataclass
class Antibody:
    """代表生成的数字抗体（防御策略）。"""
    antibody_id: str
    target_signature: str
    patch_code: str
    isolation_rule: Dict[str, Any]
    efficacy_score: float = 0.9


class DigitalTissueCompatibilitySystem:
    """
    数字组织相容性免疫系统主类。

    该类负责维护“自我”基线，监控传入流量，并在检测到异常时触发免疫响应。
    """

    def __init__(self, sensitivity_threshold: float = 2.5):
        """
        初始化免疫系统。

        Args:
            sensitivity_threshold: 判定为异常的标准差倍数（Z-score阈值）。
                                  值越低越敏感，误报率越高。
        """
        self.sensitivity_threshold = sensitivity_threshold
        self.self_baseline: Dict[str, Tuple[float, float]] = {}  # key: (mean, std_dev)
        self.memory_cells: List[str] = []  # 记录已识别的威胁特征
        self._is_initialized = False

    def learn_self_pattern(self, training_data: List[Dict[str, float]]) -> None:
        """
        核心函数 1: 学习“自我”模式。

        通过分析正常的业务流量数据，建立数学基线。如果数据不足或格式错误，
        将抛出 ValueError。

        Args:
            training_data: 包含正常流量特征的字典列表。
                           例如: [{'latency': 50, 'size': 1024}, ...]

        Raises:
            ValueError: 如果输入数据为空或包含无效数值。
        """
        if not training_data:
            raise ValueError("训练数据不能为空，无法建立自我基线。")

        logger.info("开始建立数字组织'自我'基线...")
        keys = training_data[0].keys()

        for key in keys:
            try:
                values = [d[key] for d in training_data if key in d]
                if not values:
                    continue

                mean_val = statistics.mean(values)
                stdev_val = statistics.stdev(values) if len(values) > 1 else 0.0
                
                # 防止标准差为0导致的除零错误
                if stdev_val == 0:
                    stdev_val = 1e-6

                self.self_baseline[key] = (mean_val, stdev_val)
                logger.debug(f"特征 '{key}' 基线: 均值={mean_val:.2f}, 标准差={stdev_val:.2f}")

            except (statistics.StatisticsError, TypeError) as e:
                logger.error(f"处理特征 '{key}' 时发生错误: {e}")
                raise ValueError(f"无效的数据格式导致无法计算特征 '{key}' 的统计量。")

        self._is_initialized = True
        logger.info(f"基线建立完成。已学习 {len(self.self_baseline)} 个特征维度。")

    def detect_and_respond(self, traffic_sample: Dict[str, float]) -> Optional[Antibody]:
        """
        核心函数 2: 检测威胁并生成免疫响应。

        分析传入的流量样本。如果偏离“自我”基线超过阈值，则识别为“非我”抗原，
        并调用 T 细胞逻辑生成抗体。

        Args:
            traffic_sample: 待检测的单个流量样本。

        Returns:
            Antibody: 如果检测到威胁，返回生成的抗体对象；否则返回 None。
        """
        if not self._is_initialized:
            logger.warning("系统未初始化，无法进行检测。请先调用 learn_self_pattern。")
            return None

        self._validate_input(traffic_sample)

        anomaly_score = 0.0
        anomaly_details = []

        # 计算偏离度
        for key, (mean, std) in self.self_baseline.items():
            if key in traffic_sample:
                value = traffic_sample[key]
                z_score = abs((value - mean) / std)
                if z_score > self.sensitivity_threshold:
                    anomaly_score += z_score
                    anomaly_details.append(f"{key}(z={z_score:.2f})")

        # 判定逻辑
        if anomaly_score > 0:
            threat_signature = f"THREAT_{uuid.uuid4().hex[:8]}"
            logger.warning(f"检测到非我抗原! 综合异常分: {anomaly_score:.2f}. 异常特征: {anomaly_details}")
            
            # 呈递给核心决策层 (T-Cell) 并生成抗体
            antibody = self._synthesize_antibody(threat_signature, traffic_sample, anomaly_details)
            return antibody

        logger.debug("样本符合自我模式，放行。")
        return None

    def _synthesize_antibody(self, signature: str, antigen: Dict[str, float], details: List[str]) -> Antibody:
        """
        辅助函数: 模拟 T 细胞生成抗体的过程。

        根据抗原特征生成特定的防御代码（补丁）和隔离规则。

        Args:
            signature: 威胁的唯一签名。
            antigen: 原始攻击样本。
            details: 异常特征描述。

        Returns:
            Antibody: 构建好的抗体对象。
        """
        logger.info(f"T-Cell 正在分析抗原 {signature} 并合成抗体...")

        # 动态生成补丁代码 (模拟)
        patch_code = f"""
def auto_patch_{signature}(request):
    # 动态生成的防御逻辑
    if request.get('latency', 0) > {antigen.get('latency', 0) * 0.9}:
        return False  # 拦截
    return True
"""

        # 动态生成隔离规则
        isolation_rule = {
            "source_ip_ban": True,
            "rate_limit": "10/sec",
            "signature_match": signature,
            "action": "quarantine_and_analyze"
        }

        antibody = Antibody(
            antibody_id=f"AB-{uuid.uuid4().hex[:6].upper()}",
            target_signature=signature,
            patch_code=patch_code.strip(),
            isolation_rule=isolation_rule
        )

        self.memory_cells.append(signature)
        logger.info(f"抗体 {antibody.antibody_id} 已合成并准备部署。")
        return antibody

    def _validate_input(self, data: Dict[str, float]) -> None:
        """
        辅助函数: 验证输入数据的完整性。

        Args:
            data: 待验证的数据字典。

        Raises:
            TypeError: 如果数据不是字典或包含非数值。
        """
        if not isinstance(data, dict):
            raise TypeError("输入数据必须是字典类型。")

        for key, value in data.items():
            if not isinstance(value, (int, float)):
                raise TypeError(f"特征 '{key}' 的值必须是数值类型，当前为 {type(value)}。")


# 使用示例
if __name__ == "__main__":
    # 1. 初始化系统
    immune_system = DigitalTissueCompatibilitySystem(sensitivity_threshold=2.0)

    # 2. 模拟正常流量数据 (自我)
    normal_traffic = [
        {"latency": 50, "packet_size": 1024, "cpu_load": 20},
        {"latency": 52, "packet_size": 1020, "cpu_load": 21},
        {"latency": 49, "packet_size": 1030, "cpu_load": 19},
        {"latency": 51, "packet_size": 1025, "cpu_load": 20},
        {"latency": 50, "packet_size": 1024, "cpu_load": 20},
    ]

    # 3. 学习自我模式
    try:
        immune_system.learn_self_pattern(normal_traffic)
    except ValueError as e:
        logger.error(f"初始化失败: {e}")
        exit(1)

    # 4. 模拟正常请求 (应该被放行)
    print("\n--- 测试正常流量 ---")
    response = immune_system.detect_and_respond({"latency": 51, "packet_size": 1022, "cpu_load": 20})
    print(f"结果: {response}")

    # 5. 模拟新型攻击 (非我 - 高延迟，大包)
    print("\n--- 测试异常流量 (DDoS/攻击) ---")
    attack_traffic = {"latency": 500, "packet_size": 9000, "cpu_load": 95}
    antibody = immune_system.detect_and_respond(attack_traffic)

    if antibody:
        print(f"!!! 检测到攻击 !!!")
        print(f"抗体ID: {antibody.antibody_id}")
        print(f"生成的补丁代码:\n{antibody.patch_code}")
        print(f"隔离策略: {antibody.isolation_rule}")
    else:
        print("系统未能检测到攻击。")