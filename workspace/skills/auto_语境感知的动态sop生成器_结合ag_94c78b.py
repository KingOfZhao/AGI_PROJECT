"""
名称: auto_语境感知的动态sop生成器_结合ag_94c78b
描述: 【语境感知的动态SOP生成器】
该模块实现了一个能够处理极度模糊指令的执行引擎。它利用'人机共生'中的实践节点
（如'老板的习惯'、'客户的偏好'）作为隐式参数，自动填充API调用中的缺失参数。
将模糊的'搞一下那个报告'直接转化为具体的、带参数的可执行任务流。
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, TypedDict, Union
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError, validator

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class ContextParameter(BaseModel):
    """定义上下文参数的结构"""
    key: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source: str  # 来源：例如 'user_profile', 'historical_behavior'

class TaskNode(BaseModel):
    """定义SOP中的单个任务节点"""
    id: str
    action: str
    params: Dict[str, Any]
    dependencies: List[str] = []  # 依赖的前置任务ID

class SOPSchema(BaseModel):
    """标准作业程序(SOP)的JSON结构"""
    sop_id: str
    created_at: str
    intent: str
    risk_level: str  # low, medium, high
    execution_flow: List[TaskNode]
    estimated_time: int  # seconds

class UserProfile(BaseModel):
    """用户画像模型，存储隐式参数"""
    user_id: str
    preferences: Dict[str, Any]
    habits: Dict[str, Any]
    relationships: Dict[str, Any]

# --- 核心类 ---

class ContextAwareSOPGenerator:
    """
    语境感知的动态SOP生成器。
    
    结合AGI的JSON结构化能力与实践技能的语境处理，将模糊指令转化为可执行任务流。
    """
    
    def __init__(self, user_context_db: Dict[str, UserProfile]):
        """
        初始化生成器。
        
        Args:
            user_context_db: 模拟的用户上下文数据库。
        """
        self.user_context_db = user_context_db
        logger.info("SOP Generator initialized with %d user profiles.", len(user_context_db))

    def _retrieve_implicit_params(self, user_id: str, keywords: List[str]) -> Dict[str, ContextParameter]:
        """
        [辅助函数] 根据关键词从用户上下文中检索隐式参数。
        
        Args:
            user_id: 用户ID
            keywords: 从指令中提取的关键词列表
            
        Returns:
            匹配到的隐式参数字典
        """
        implicit_params = {}
        if user_id not in self.user_context_db:
            logger.warning("User ID %s not found in context DB.", user_id)
            return implicit_params

        profile = self.user_context_db[user_id]
        
        # 简单的关键词匹配逻辑 (实际AGI场景中会使用向量检索)
        if "报告" in keywords or "report" in keywords:
            # 假设老板习惯看PDF格式，且偏好数据看板A
            implicit_params["format"] = ContextParameter(
                key="format", 
                value=profile.habits.get("preferred_report_format", "PDF"),
                confidence=0.9,
                source="boss_habit"
            )
            implicit_params["source_data"] = ContextParameter(
                key="source_data",
                value=profile.habits.get("default_dashboard", "Sales_Dashboard_Q4"),
                confidence=0.85,
                source="historical_behavior"
            )
            
        if "发送" in keywords or "发" in keywords:
            # 假设默认发送给秘书组
            implicit_params["recipient"] = ContextParameter(
                key="recipient",
                value=profile.relationships.get("default_assistant", "sec_team@corp.com"),
                confidence=0.95,
                source="org_structure"
            )
            
        logger.info("Retrieved %d implicit params for keywords: %s", len(implicit_params), keywords)
        return implicit_params

    def _analyze_intent_structure(self, vague_instruction: str) -> Dict[str, Any]:
        """
        [内部方法] 模拟AGI解析自然语言意图，提取骨架。
        实际场景中这里会调用LLM。
        """
        # 模拟NLP解析结果
        structure = {
            "raw_text": vague_instruction,
            "keywords": re.findall(r'\w+', vague_instruction),
            "detected_actions": [],
            "required_entities": []
        }
        
        if "搞一下" in vague_instruction or "处理" in vague_instruction:
            structure["detected_actions"].append("generate")
        if "发" in vague_instruction or "送给" in vague_instruction:
            structure["detected_actions"].append("send")
        if "报告" in vague_instruction:
            structure["required_entities"].append("report_object")
            
        return structure

    def generate_dynamic_sop(
        self, 
        vague_instruction: str, 
        user_id: str, 
        explicit_params: Optional[Dict] = None
    ) -> SOPSchema:
        """
        [核心函数1] 生成动态SOP。
        
        Args:
            vague_instruction: 模糊的自然语言指令，如 "搞一下那个报告"
            user_id: 发起指令的用户ID
            explicit_params: 显式提供的参数（覆盖隐式参数）
            
        Returns:
            SOPSchema: 结构化的标准作业程序对象
            
        Raises:
            ValueError: 如果无法生成有效的SOP
        """
        logger.info(f"Received vague instruction: '{vague_instruction}' from {user_id}")
        
        # 1. 意图结构化分析
        intent_data = self._analyze_intent_structure(vague_instruction)
        
        # 2. 获取隐式上下文参数
        implicit_params = self._retrieve_implicit_params(user_id, intent_data["keywords"])
        
        # 3. 参数融合 (显式 > 隐式)
        final_params = {}
        for key, param_obj in implicit_params.items():
            final_params[key] = param_obj.value
            
        if explicit_params:
            final_params.update(explicit_params)
            
        # 4. 校验必要参数是否完整
        if not final_params.get("source_data"):
             raise ValueError("Missing critical parameter: source_data (cannot infer from context)")

        # 5. 构建任务流 (基于模板 + 动态参数)
        # 这里演示生成一个简单的线性流程：打开 -> 截取 -> 格式化 -> 发送
        sop_id = f"SOP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        task_nodes = []
        
        # Node 1: 打开数据源
        task_nodes.append(TaskNode(
            id="step_1_open",
            action="open_application",
            params={"app_name": "BI_Tool", "target": final_params.get("source_data")},
            dependencies=[]
        ))
        
        # Node 2: 截取数据 (模拟模糊指令具体化)
        task_nodes.append(TaskNode(
            id="step_2_capture",
            action="capture_data",
            params={
                "range": "last_month",  # 假设这是AGI推断出的时间范围
                "metrics": ["revenue", "growth"]
            },
            dependencies=["step_1_open"]
        ))
        
        # Node 3: 生成报告
        task_nodes.append(TaskNode(
            id="step_3_generate",
            action="export_file",
            params={
                "format": final_params.get("format", "PDF"),
                "template": "standard_executive_summary"
            },
            dependencies=["step_2_capture"]
        ))
        
        # Node 4: 发送 (如果意图包含发送)
        if "send" in intent_data["detected_actions"]:
            task_nodes.append(TaskNode(
                id="step_4_send",
                action="send_email",
                params={
                    "to": final_params.get("recipient"),
                    "subject": f"Report Generated for {user_id}"
                },
                dependencies=["step_3_generate"]
            ))

        # 6. 封装SOP对象
        try:
            sop = SOPSchema(
                sop_id=sop_id,
                created_at=datetime.now().isoformat(),
                intent=vague_instruction,
                risk_level="medium", # 涉及数据外发，默认中等风险
                execution_flow=task_nodes,
                estimated_time=30
            )
            logger.info(f"Successfully generated SOP: {sop_id}")
            return sop
        except ValidationError as e:
            logger.error(f"SOP Schema validation failed: {e}")
            raise ValueError("Generated SOP failed validation")

# --- 工具函数 ---

def visualize_sop_flow(sop: SOPSchema) -> str:
    """
    [核心函数2] 将SOP对象可视化为简单的文本流程图。
    
    Args:
        sop: SOPSchema对象
        
    Returns:
        str: 可读的流程描述字符串
    """
    output = [f"--- SOP Flow: {sop.sop_id} ---"]
    output.append(f"Origin Request: {sop.intent}")
    output.append(f"Risk Level: {sop.risk_level}")
    output.append("Execution Plan:")
    
    for node in sop.execution_flow:
        deps = f"(depends on: {', '.join(node.dependencies)})" if node.dependencies else "(start)"
        params_str = ", ".join([f"{k}={v}" for k, v in node.params.items()])
        output.append(f"  [{node.id}] Action: {node.action.upper()} | Params: {{{params_str}}} | {deps}")
        
    return "\n".join(output)

# --- 主程序与示例 ---

if __name__ == "__main__":
    # 模拟上下文数据库
    mock_db = {
        "user_001": UserProfile(
            user_id="user_001",
            preferences={"language": "zh-CN"},
            habits={
                "preferred_report_format": "PPT", # 老板喜欢PPT
                "default_dashboard": "Regional_Sales_2023"
            },
            relationships={
                "default_assistant": "manager@corp.com"
            }
        )
    }

    # 初始化生成器
    generator = ContextAwareSOPGenerator(user_context_db=mock_db)

    # 示例1: 极度模糊的指令
    vague_cmd = "搞一下那个报告，发给我"
    
    try:
        print("\n" + "="*30)
        print(f"Processing Vague Command: '{vague_cmd}'")
        print("="*30 + "\n")
        
        # 生成SOP
        sop_result = generator.generate_dynamic_sop(
            vague_instruction=vague_cmd,
            user_id="user_001"
        )
        
        # 可视化输出
        print(visualize_sop_flow(sop_result))
        
        # 导出JSON结构 (模拟API输出)
        print("\nJSON Output for AGI Execution Engine:")
        print(sop_result.json(indent=2))
        
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        logging.exception("Unexpected error during SOP generation")