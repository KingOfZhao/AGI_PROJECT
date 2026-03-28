"""
模块名称: industrial_log_parser
描述: 这是一个用于AGI系统的高级技能模块，旨在利用大语言模型（LLM）将非标准化的工业设备维修日志
      （自然语言）转化为结构化三元组，并与预定义的故障代码树进行对齐。
      该模块解决了工业领域大量存在的非结构化“死数据”无法被自动化系统利用的痛点。

依赖:
    - pydantic (用于数据验证)
    - logging (标准库)
    - json (标准库)
    - typing (标准库)

注意: 实际生产环境中，需要集成真实的LLM API调用（如OpenAI, Anthropic或私有部署模型）。
      本示例中包含一个Mock LLM函数以演示逻辑。
"""

import json
import logging
import re
from typing import List, Dict, Tuple, Optional, Any
from pydantic import BaseModel, ValidationError, Field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据模型 ---

class MaintenanceLog(BaseModel):
    """维修日志输入模型"""
    log_id: str
    content: str
    timestamp: Optional[str] = None

class ExtractedTriple(BaseModel):
    """从日志中提取的三元组模型"""
    fault_phenomenon: str = Field(..., description="描述故障的具体现象")
    action_taken: str = Field(..., description="描述采取的维修措施")
    parts_replaced: str = Field(..., description="描述更换的备件，若无则填写'None'")

class AlignedResult(BaseModel):
    """最终对齐后的结果模型"""
    original_log_id: str
    triple: ExtractedTriple
    matched_fault_code: str
    confidence_score: float = Field(ge=0.0, le=1.0)

# --- 核心函数 ---

def call_llm_api(prompt: str, model_type: str = "gpt-4-turbo") -> str:
    """
    [Mock 函数] 模拟调用大语言模型API。
    在实际场景中，这里会包含 requests 库或 SDK 调用。
    
    Args:
        prompt (str): 发送给LLM的提示词。
        model_type (str): 使用的模型类型。
        
    Returns:
        str: LLM返回的字符串（通常是JSON格式）。
    """
    logger.debug(f"Mocking LLM call with model: {model_type}")
    
    # 模拟一个智能提取的响应
    mock_response = {
        "fault_phenomenon": "主轴电机过热并触发报警代码E-501",
        "action_taken": "清洁散热风扇，重新校准传感器阈值",
        "parts_replaced": "None"
    }
    return json.dumps(mock_response)

def extract_triples_with_llm(logs: List[MaintenanceLog]) -> List[Tuple[str, ExtractedTriple]]:
    """
    利用大语言模型从非标准化文本中提取故障现象、处理措施、备件更换三元组。
    
    Args:
        logs (List[MaintenanceLog]): 维修日志对象列表。
        
    Returns:
        List[Tuple[str, ExtractedTriple]]: 包含日志ID和提取出的三元组的列表。
        
    Raises:
        ValueError: 如果输入日志为空。
    """
    if not logs:
        logger.error("输入日志列表为空")
        raise ValueError("Input logs cannot be empty")
        
    results = []
    
    for log in logs:
        logger.info(f"正在处理日志 ID: {log.log_id}")
        
        # 构造Few-Shot Prompt以提高提取精度
        prompt = f"""
        你是一个工业设备维护专家。请分析以下维修日志，提取三个关键信息：
        1. 故障现象
        2. 处理措施
        3. 备件更换
        
        日志内容:
        "{log.content}"
        
        请仅返回JSON格式，包含键: fault_phenomenon, action_taken, parts_replaced。
        """
        
        try:
            # 调用LLM (这里使用Mock函数)
            llm_response_str = call_llm_api(prompt)
            response_data = json.loads(llm_response_str)
            
            # 使用Pydantic进行数据验证
            triple = ExtractedTriple(**response_data)
            results.append((log.log_id, triple))
            logger.debug(f"成功提取三元组: {triple}")
            
        except json.JSONDecodeError:
            logger.error(f"日志 {log.log_id} LLM返回非JSON格式: {llm_response_str}")
        except ValidationError as e:
            logger.error(f"日志 {log.log_id} 数据验证失败: {e}")
        except Exception as e:
            logger.critical(f"处理日志 {log.log_id} 时发生未预期错误: {e}", exc_info=True)
            
    return results

def align_to_fault_tree(
    extracted_data: List[Tuple[str, ExtractedTriple]], 
    fault_tree: Dict[str, List[str]]
) -> List[AlignedResult]:
    """
    将提取出的三元组与现有的故障代码树进行对齐（自上而下匹配）。
    
    Args:
        extracted_data (List[Tuple[str, ExtractedTriple]]): 提取出的数据。
        fault_tree (Dict[str, List[str]]): 故障树字典，Key是故障代码，Value是关键词列表。
        
    Returns:
        List[AlignedResult]: 对齐后的最终结果列表。
    """
    aligned_results = []
    
    for log_id, triple in extracted_data:
        best_match_code = "UNKNOWN"
        best_score = 0.0
        
        # 简单的关键词匹配逻辑（实际AGI场景中应使用向量嵌入相似度搜索）
        # 这里演示自上而下的遍历逻辑
        text_to_match = f"{triple.fault_phenomenon} {triple.action_taken}".lower()
        
        for code, keywords in fault_tree.items():
            match_count = 0
            for kw in keywords:
                if kw.lower() in text_to_match:
                    match_count += 1
            
            # 计算简单的置信度分数
            if len(keywords) > 0:
                score = match_count / len(keywords)
                # 只要分数更高，或者覆盖了核心关键词，就更新匹配
                if score > best_score:
                    best_score = score
                    best_match_code = code
        
        # 设定阈值
        final_score = best_score if best_score > 0.1 else 0.0
        if final_score == 0.0:
            best_match_code = "UNMATCHED"
            
        result = AlignedResult(
            original_log_id=log_id,
            triple=triple,
            matched_fault_code=best_match_code,
            confidence_score=final_score
        )
        aligned_results.append(result)
        logger.info(f"日志 {log_id} 对齐到代码 {best_match_code} (Score: {final_score:.2f})")
        
    return aligned_results

# --- 辅助函数 ---

def preprocess_raw_text(raw_text: str) -> str:
    """
    辅助函数：对原始文本进行清洗，去除噪音字符。
    
    Args:
        raw_text (str): 原始脏数据文本。
        
    Returns:
        str: 清洗后的文本。
    """
    if not raw_text:
        return ""
    # 去除多余的空格和换行
    text = re.sub(r'\s+', ' ', raw_text).strip()
    # 这里可以添加更多的清洗规则，如去除特定的HTML标签等
    return text

# --- 主程序示例 ---

if __name__ == "__main__":
    # 1. 定义模拟的故障代码树
    # Key: 故障代码, Value: 关联关键词
    fault_code_tree = {
        "ERR-MOTOR-01": ["电机", "过热", "E-501", "噪音"],
        "ERR-CTRL-02": ["PLC", "通讯", "丢失", "断连"],
        "ERR-HYD-03": ["液压", "泄漏", "压力低"]
    }

    # 2. 模拟输入数据
    raw_logs_data = [
        {
            "log_id": "LOG-001", 
            "content": "设备停机，操作员报告主轴电机非常烫手，屏幕显示 E-501。维修人员清理了风扇。"
        },
        {
            "log_id": "LOG-002", 
            "content": "控制柜指示灯闪烁，PLC通讯时断时续，检查发现是网线松动。"
        }
    ]

    # 3. 数据预处理与验证
    clean_logs = []
    for item in raw_logs_data:
        try:
            cleaned_content = preprocess_raw_text(item['content'])
            clean_logs.append(MaintenanceLog(log_id=item['log_id'], content=cleaned_content))
        except Exception as e:
            logger.warning(f"跳过无效数据 {item}: {e}")

    # 4. 执行核心流程：提取 -> 对齐
    try:
        # 第一步：LLM 提取
        extracted_triples = extract_triples_with_llm(clean_logs)
        
        if extracted_triples:
            # 第二步：故障树对齐
            final_results = align_to_fault_tree(extracted_triples, fault_code_tree)
            
            # 打印结果
            print("\n=== 处理结果 ===")
            for res in final_results:
                print(res.model_dump_json(indent=2))
        else:
            print("未能提取出有效数据。")
            
    except Exception as e:
        logger.critical(f"系统运行失败: {e}")