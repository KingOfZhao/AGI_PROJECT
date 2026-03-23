import re
from typing import Any, Dict, List, Union

def auto_将数据治理中的etl_抽取_转换_加载_73f4d4(
    raw_data: Union[str, List[Any], Dict[str, Any]],
    emotion_noise_keywords: List[str] = None,
    output_format: str = "dict"
) -> Union[Dict[str, Any], str]:
    """
    将数据治理中的ETL（抽取、转换、加载）流程映射至人类认知过程。
    通过AI识别并隔离情绪'噪声'（归一化），还原客观事实'信号'（去噪），
    将混沌的日常经验转化为结构化的高质量'认知数据集'。

    Args:
        raw_data (Union[str, List[Any], Dict[str, Any]]): 
            原始输入数据，可以是文本、列表或字典格式
        emotion_noise_keywords (List[str], optional): 
            情绪噪声关键词列表，默认包含常见情绪词汇
        output_format (str, optional): 
            输出格式，"dict"（默认）或"str"

    Returns:
        Union[Dict[str, Any], str]: 
            结构化认知数据集（字典格式）或字符串格式结果

    Raises:
        ValueError: 当输入数据类型不支持或输出格式无效时
        TypeError: 当输入数据无法转换为字符串时
    """
    # 初始化情绪噪声关键词（默认值）
    if emotion_noise_keywords is None:
        emotion_noise_keywords = [
            "非常", "极其", "特别", "超级", "太", "好极了", "糟糕透了",
            "讨厌", "喜欢", "爱", "恨", "开心", "难过", "生气", "害怕",
            "完美", "可怕", "震惊", "惊喜", "失望", "满意", "不满"
        ]

    # ===== 抽取阶段：从原始数据中提取信息 =====
    try:
        # 统一转换为字符串处理
        if isinstance(raw_data, (list, dict)):
            extracted_text = str(raw_data)
        elif isinstance(raw_data, str):
            extracted_text = raw_data
        else:
            raise TypeError("输入数据必须是字符串、列表或字典类型")
    except Exception as e:
        raise TypeError(f"数据转换失败: {str(e)}")

    # ===== 转换阶段：去噪与归一化处理 =====
    def denoise_normalize(text: str) -> str:
        """内部函数：执行去噪和归一化操作"""
        # 1. 移除情绪噪声关键词（不区分大小写）
        for keyword in emotion_noise_keywords:
            text = re.sub(
                rf"\b{re.escape(keyword)}\b", 
                "", 
                text, 
                flags=re.IGNORECASE
            )
        
        # 2. 移除标点符号（保留基本句号、逗号、问号）
        text = re.sub(r"[^\w\s.,?]", "", text)
        
        # 3. 归一化处理：统一空格、去除首尾空格
        text = " ".join(text.split())
        
        # 4. 移除重复标点（如".."替换为"."）
        text = re.sub(r"([.,?])\1+", r"\1", text)
        
        return text.strip()

    # 执行转换
    processed_text = denoise_normalize(extracted_text)

    # ===== 加载阶段：结构化输出 =====
    try:
        # 解析处理后的文本为结构化数据
        cognitive_dataset = {
            "原始数据": raw_data,
            "去噪后文本": processed_text,
            "噪声关键词": emotion_noise_keywords,
            "处理状态": "成功"
        }

        # 根据输出格式返回结果
        if output_format == "dict":
            return cognitive_dataset
        elif output_format == "str":
            return str(cognitive_dataset)
        else:
            raise ValueError("输出格式必须是 'dict' 或 'str'")
            
    except Exception as e:
        raise ValueError(f"数据加载失败: {str(e)}")


# ===== 示例使用 =====
if __name__ == "__main__":
    # 测试数据
    test_data = """
    我对这个产品感到非常满意！它的性能超级棒，简直完美无缺。
    虽然价格有点贵，但物超所值！强烈推荐！
    """
    
    try:
        # 执行ETL认知处理
        result = auto_将数据治理中的etl_抽取_转换_加载_73f4d4(
            raw_data=test_data,
            output_format="dict"
        )
        
        print("=== 认知数据集 ===")
        print(result)
        
        # 字符串输出示例
        str_result = auto_将数据治理中的etl_抽取_转换_加载_73f4d4(
            raw_data=["测试数据", "包含情绪词汇"],
            output_format="str"
        )
        print("\n=== 字符串输出 ===")
        print(str_result)
        
    except Exception as e:
        print(f"处理失败: {str(e)}")