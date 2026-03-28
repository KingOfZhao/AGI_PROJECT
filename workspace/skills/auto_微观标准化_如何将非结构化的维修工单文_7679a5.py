"""
名称: auto_微观标准化_如何将非结构化的维修工单文_7679a5
描述: 【微观标准化】如何将非结构化的维修工单文本（包含大量口语、错别字、非标术语）转化为标准的‘故障-操作-结果’三元组结构？这需要一种能够容忍噪声的NLP解析器，从碎片化的维修日志中提取出可复用的‘真实节点’。
领域: NLP / Data Mining
"""

import logging
import re
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MaintenanceCategory(Enum):
    """维修工单分类枚举"""
    MECHANICAL = "机械故障"
    ELECTRICAL = "电气故障"
    SOFTWARE = "软件故障"
    HYDRAULIC = "液压故障"
    OTHER = "其他"

@dataclass
class FaultActionResult:
    """故障-操作-结果（F-A-R）三元组数据结构"""
    fault: str
    action: str
    result: str
    confidence: float
    category: MaintenanceCategory
    raw_text: str

class DataValidationError(Exception):
    """自定义数据验证错误"""
    pass

def preprocess_text(text: str) -> str:
    """
    预处理非结构化文本，清洗噪声数据
    
    Args:
        text (str): 原始维修工单文本
        
    Returns:
        str: 清洗后的标准化文本
        
    Raises:
        DataValidationError: 当输入文本为空或无效时抛出
    """
    if not text or not isinstance(text, str):
        raise DataValidationError("输入文本不能为空且必须为字符串")
    
    # 记录原始文本用于日志
    original_text = text
    
    try:
        # 转换为小写
        text = text.lower()
        
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 标准化常见错别字和口语表达
        correction_dict = {
            '机戒': '机械',
            '电七': '电气',
            '软剑': '软件',
            '液牙': '液压',
            '坏掉了': '损坏',
            '不工作了': '停止运行',
            '没反应': '无响应',
            '修好了': '已修复',
            '换了个': '更换',
            '检查了一下': '检查'
        }
        
        for wrong, correct in correction_dict.items():
            text = text.replace(wrong, correct)
            
        logger.info(f"文本预处理完成: '{original_text}' -> '{text}'")
        return text
        
    except Exception as e:
        logger.error(f"文本预处理失败: {str(e)}", exc_info=True)
        raise DataValidationError(f"文本预处理失败: {str(e)}")

def extract_far_triples(text: str) -> List[FaultActionResult]:
    """
    从标准化文本中提取故障-操作-结果（F-A-R）三元组
    
    Args:
        text (str): 预处理后的标准化文本
        
    Returns:
        List[FaultActionResult]: 提取的F-A-R三元组列表
        
    Raises:
        DataValidationError: 当文本无法解析时抛出
    """
    if not text:
        raise DataValidationError("输入文本不能为空")
    
    try:
        # 定义关键词模式（简化版，实际应用中可使用更复杂的NLP模型）
        fault_patterns = [
            r'(故障|损坏|停止运行|无响应|异常)',
            r'(机械|电气|软件|液压).*?(故障|损坏)'
        ]
        
        action_patterns = [
            r'(检查|更换|维修|调整|清洁|测试)',
            r'(对.*?进行了.*?操作)'
        ]
        
        result_patterns = [
            r'(已修复|恢复正常|问题解决|运行正常)',
            r'(结果.*?(正常|解决|修复))'
        ]
        
        # 尝试匹配模式
        fault = ""
        action = ""
        result = ""
        confidence = 0.0
        
        # 提取故障
        for pattern in fault_patterns:
            match = re.search(pattern, text)
            if match:
                fault = match.group(0)
                confidence += 0.3
                break
                
        # 提取操作
        for pattern in action_patterns:
            match = re.search(pattern, text)
            if match:
                action = match.group(0)
                confidence += 0.3
                break
                
        # 提取结果
        for pattern in result_patterns:
            match = re.search(pattern, text)
            if match:
                result = match.group(0)
                confidence += 0.4
                break
                
        # 如果没有匹配到完整的三元组，尝试简单分割
        if not all([fault, action, result]):
            parts = text.split('，')
            if len(parts) >= 3:
                fault = parts[0]
                action = parts[1]
                result = parts[2]
                confidence = 0.5  # 降低置信度
                
        # 确定分类
        category = MaintenanceCategory.OTHER
        if "机械" in fault:
            category = MaintenanceCategory.MECHANICAL
        elif "电气" in fault:
            category = MaintenanceCategory.ELECTRICAL
        elif "软件" in fault:
            category = MaintenanceCategory.SOFTWARE
        elif "液压" in fault:
            category = MaintenanceCategory.HYDRAULIC
            
        # 验证提取结果
        if not fault or not action or not result:
            logger.warning(f"无法从文本中提取完整F-A-R三元组: {text}")
            return []
            
        # 创建F-A-R对象
        far_triple = FaultActionResult(
            fault=fault,
            action=action,
            result=result,
            confidence=confidence,
            category=category,
            raw_text=text
        )
        
        logger.info(f"成功提取F-A-R三元组: {asdict(far_triple)}")
        return [far_triple]
        
    except Exception as e:
        logger.error(f"F-A-R提取失败: {str(e)}", exc_info=True)
        raise DataValidationError(f"F-A-R提取失败: {str(e)}")

def process_maintenance_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理单条维修记录，返回标准化结果
    
    Args:
        record (Dict[str, Any]): 原始维修记录，包含文本和其他元数据
        
    Returns:
        Dict[str, Any]: 标准化后的处理结果
        
    Raises:
        DataValidationError: 当输入记录无效时抛出
    """
    if not record or not isinstance(record, dict):
        raise DataValidationError("输入记录必须是非空字典")
        
    if 'text' not in record:
        raise DataValidationError("输入记录必须包含'text'字段")
        
    try:
        # 预处理文本
        cleaned_text = preprocess_text(record['text'])
        
        # 提取F-A-R三元组
        far_triples = extract_far_triples(cleaned_text)
        
        # 构建结果
        result = {
            'original_record': record,
            'cleaned_text': cleaned_text,
            'far_triples': [asdict(triple) for triple in far_triples],
            'status': 'success' if far_triples else 'partial',
            'error': None
        }
        
        logger.info(f"记录处理完成: {record.get('id', 'unknown')}")
        return result
        
    except Exception as e:
        logger.error(f"记录处理失败: {str(e)}", exc_info=True)
        return {
            'original_record': record,
            'cleaned_text': None,
            'far_triples': [],
            'status': 'failed',
            'error': str(e)
        }

def main():
    """示例用法"""
    # 示例维修记录
    sample_records = [
        {
            "id": "wo-12345",
            "text": "机戒设备不工作了，检查了一下发现是轴承坏了，换了个新的，现在运行正常了。",
            "timestamp": "2023-05-15T08:30:00Z",
            "technician": "张工"
        },
        {
            "id": "wo-12346",
            "text": "电七系统没反应，测试了所有连接线，紧固了松动的接头，问题解决。",
            "timestamp": "2023-05-16T14:45:00Z",
            "technician": "李工"
        },
        {
            "id": "wo-12347",
            "text": "软件程序卡死，重启了系统，恢复正常。",
            "timestamp": "2023-05-17T09:15:00Z",
            "technician": "王工"
        }
    ]
    
    # 处理每条记录
    for record in sample_records:
        print(f"\n处理记录: {record['id']}")
        print("=" * 50)
        
        result = process_maintenance_record(record)
        
        if result['status'] == 'success':
            print("标准化文本:", result['cleaned_text'])
            print("\n提取的F-A-R三元组:")
            for triple in result['far_triples']:
                print(f"故障: {triple['fault']}")
                print(f"操作: {triple['action']}")
                print(f"结果: {triple['result']}")
                print(f"分类: {triple['category']}")
                print(f"置信度: {triple['confidence']:.2f}")
        else:
            print("处理失败:", result['error'])

if __name__ == "__main__":
    main()