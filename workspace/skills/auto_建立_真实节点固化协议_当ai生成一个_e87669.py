"""
模块名称: toki_protocol_engine
描述: 建立‘真实节点固化协议’。当AI生成一个假设性节点后，自动生成一套最小化的
      ‘实践验证清单’（Toki清单），并将其分发给人类或模拟代理执行。
      核心功能是将自然语言假设转化为可执行的测试步骤。

作者: AGI System Core Team
版本: 1.0.0
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TokiProtocolEngine")


class NodeVerificationStatus(Enum):
    """节点验证状态枚举"""
    HYPOTHETICAL = "hypothetical"  # 假设性节点，待验证
    VERIFIED = "verified"          # 已验证为真
    FALSIFIED = "falsified"        # 已证伪
    PENDING = "pending"            # 验证中


class ExecutionAgentType(Enum):
    """执行代理类型"""
    HUMAN = "human"
    SIMULATOR = "simulator"
    ROBOTIC = "robotic"


@dataclass
class HypotheticalNode:
    """假设性节点数据结构"""
    node_id: str
    content: str  # 自然语言描述的假设
    context: Dict[str, str]  # 上下文信息
    confidence: float  # AI对该假设的置信度 (0.0 - 1.0)
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他节点ID


@dataclass
class VerificationStep:
    """验证步骤数据结构"""
    step_id: str
    description: str  # 步骤的自然语言描述
    executable_code: Optional[str] = None  # 可执行代码（Python/Shell等）
    expected_outcome: str = ""  # 预期结果
    required_agent: ExecutionAgentType = ExecutionAgentType.SIMULATOR
    priority: int = 1  # 1-5, 5为最高优先级


@dataclass
class TokiChecklist:
    """Toki 实践验证清单"""
    checklist_id: str
    source_node_id: str
    steps: List[VerificationStep]
    status: NodeVerificationStatus = NodeVerificationStatus.PENDING
    distribution_targets: List[Dict[str, str]] = field(default_factory=list)


class TokiProtocolEngine:
    """
    Toki协议引擎：负责将假设性节点转化为可执行的验证清单。
    
    核心逻辑：
    1. 解析假设节点的自然语言内容。
    2. 提取关键变量和断言。
    3. 生成最小化的验证步骤集（MVP）。
    4. 封装成清单并准备分发。
    """

    def __init__(self, default_agent: ExecutionAgentType = ExecutionAgentType.SIMULATOR):
        self.default_agent = default_agent
        self._step_counter = 0
        logger.info("Toki Protocol Engine initialized.")

    def _generate_step_id(self) -> str:
        """辅助函数：生成唯一的步骤ID"""
        self._step_counter += 1
        return f"toki_step_{uuid.uuid4().hex[:6]}_{self._step_counter}"

    def _parse_hypothesis_content(self, content: str) -> Dict[str, str]:
        """
        辅助函数：简单的假设解析器。
        实际AGI场景中，这里会调用LLM进行语义分析。
        此处使用规则匹配进行模拟。
        """
        logger.debug(f"Parsing hypothesis content: {content[:50]}...")
        parsed_data = {
            "subject": "unknown",
            "action": "exists",
            "condition": "True"
        }

        # 简单的关键词提取逻辑 (模拟 NLP)
        if "API" in content:
            parsed_data['subject'] = "API Endpoint"
            parsed_data['action'] = "response_valid"
        elif "file" in content.lower():
            parsed_data['subject'] = "File System"
            parsed_data['action'] = "read_access"
        elif "user" in content.lower():
            parsed_data['subject'] = "User Behavior"
            parsed_data['action'] = "interaction"
        
        return parsed_data

    def generate_verification_steps(self, node: HypotheticalNode) -> List[VerificationStep]:
        """
        核心函数 1: 根据假设节点生成验证步骤列表。
        
        Args:
            node (HypotheticalNode): 待验证的假设节点。
            
        Returns:
            List[VerificationStep]: 生成的验证步骤列表。
            
        Raises:
            ValueError: 如果节点置信度无效或内容为空。
        """
        # 数据验证
        if not node.content:
            logger.error("Node content is empty.")
            raise ValueError("Hypothetical node content cannot be empty.")
        
        if not (0.0 <= node.confidence <= 1.0):
            logger.error(f"Invalid confidence value: {node.confidence}")
            raise ValueError("Confidence must be between 0.0 and 1.0.")

        logger.info(f"Generating verification steps for node: {node.node_id}")
        
        parsed = self._parse_hypothesis_content(node.content)
        steps = []

        # 生成逻辑：根据解析出的意图构建步骤
        # 这里模拟了一个从 NL -> Executable Code 的映射过程
        
        # 步骤 1: 环境检查
        steps.append(VerificationStep(
            step_id=self._generate_step_id(),
            description=f"Verify environment for {parsed['subject']}",
            executable_code=f"print('Checking env for {parsed['subject']}')",
            required_agent=ExecutionAgentType.SIMULATOR,
            priority=5
        ))

        # 步骤 2: 核心断言测试
        # 假设如果是API相关，我们生成一个Python requests代码片段
        code_snippet = None
        if parsed['subject'] == "API Endpoint":
            code_snippet = "import requests\nresp = requests.get('URL_PLACEHOLDER')\nassert resp.status_code == 200"
        
        steps.append(VerificationStep(
            step_id=self._generate_step_id(),
            description=f"Execute core action: {node.content}",
            executable_code=code_snippet,
            expected_outcome="Action completed without errors",
            required_agent=self.default_agent,
            priority=4
        ))

        # 步骤 3: 副作用检查 - 如果是高优先级节点
        if node.confidence < 0.8:
            steps.append(VerificationStep(
                step_id=self._generate_step_id(),
                description="Perform manual sanity check (Low confidence fallback)",
                required_agent=ExecutionAgentType.HUMAN,
                priority=3
            ))

        logger.info(f"Generated {len(steps)} steps.")
        return steps

    def create_and_distribute_toki_list(
        self, 
        node: HypotheticalNode, 
        targets: List[Dict[str, str]]
    ) -> TokiChecklist:
        """
        核心函数 2: 创建完整的Toki清单并模拟分发。
        
        Args:
            node (HypotheticalNode): 源节点。
            targets (List[Dict[str, str]]): 分发目标列表，包含 agent_id 和 type。
            
        Returns:
            TokiChecklist: 包含所有步骤和分发状态的清单对象。
        """
        logger.info(f"Creating Toki Checklist for node {node.node_id}")
        
        # 生成步骤
        try:
            steps = self.generate_verification_steps(node)
        except ValueError as e:
            logger.error(f"Failed to generate steps: {e}")
            # 返回一个空的或错误状态的清单，而不是崩溃
            return TokiChecklist(
                checklist_id=f"err_{uuid.uuid4().hex}",
                source_node_id=node.node_id,
                steps=[],
                status=NodeVerificationStatus.FALSIFIED # 无法生成步骤视为逻辑证伪
            )

        # 创建清单
        checklist = TokiChecklist(
            checklist_id=f"toki_{uuid.uuid4().hex[:8]}",
            source_node_id=node.node_id,
            steps=steps,
            distribution_targets=targets
        )

        # 模拟分发逻辑
        for target in targets:
            agent_type = target.get('type', 'unknown')
            agent_id = target.get('id', 'unknown')
            logger.info(f"Distributing task {checklist.checklist_id} to {agent_type} agent: {agent_id}")
            
            # 这里可以接入实际的消息队列或API调用
            # 例如: message_queue.publish(agent_id, checklist.to_json())
            
        return checklist

    def to_dict(self, checklist: TokiChecklist) -> Dict:
        """辅助序列化方法"""
        return asdict(checklist)

# ============================================================
# 使用示例 / Usage Example
# ============================================================
if __name__ == "__main__":
    # 1. 初始化协议引擎
    engine = TokiProtocolEngine(default_agent=ExecutionAgentType.SIMULATOR)
    
    # 2. 定义一个由AI生成的假设性节点
    # 假设AI认为："连接到外部天气API可以成功获取当前温度"
    ai_hypothesis = HypotheticalNode(
        node_id="hyp_node_001",
        content="The external Weather API is responsive and returns valid JSON temperature data.",
        context={"environment": "production", "api_key": "xxxx"},
        confidence=0.75,
        dependencies=[]
    )
    
    # 3. 定义分发目标 (模拟代理和人类审核员)
    distribution_list = [
        {"id": "sim_agent_01", "type": "simulator"},
        {"id": "human_admin", "type": "human"}
    ]
    
    # 4. 执行协议：生成并分发 Toki 清单
    try:
        final_checklist = engine.create_and_distribute_toki_list(
            node=ai_hypothesis,
            targets=distribution_list
        )
        
        # 5. 打印结果
        print("\n--- Generated Toki Checklist (JSON) ---")
        # 自定义序列化以处理 Enum
        result_dict = engine.to_dict(final_checklist)
        def enum_handler(obj):
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
        print(json.dumps(result_dict, default=enum_handler, indent=2))
        
    except Exception as e:
        logger.critical(f"System critical failure: {e}")