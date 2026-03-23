"""
双向转换器：代码语法与自然语言语义之间的最小损失映射
领域：AI编译原理
功能：实现代码与自然语言的双向转换，减少映射损失
"""

import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer
from typing import Tuple, Optional
import warnings

class CodeNLTranslator:
    """
    代码与自然语言双向转换器，基于T5模型实现最小损失映射
    
    属性:
        model (T5ForConditionalGeneration): 预训练T5模型
        tokenizer (T5Tokenizer): T5分词器
        device (torch.device): 计算设备
    """
    
    def __init__(self, model_name: str = "t5-small"):
        """
        初始化转换器
        
        参数:
            model_name (str): 预训练模型名称，默认为't5-small'
            
        异常:
            RuntimeError: 当模型加载失败时抛出
        """
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.tokenizer = T5Tokenizer.from_pretrained(model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            raise RuntimeError(f"模型加载失败: {str(e)}")

    def _preprocess_input(self, text: str, task_prefix: str) -> torch.Tensor:
        """
        预处理输入文本
        
        参数:
            text (str): 输入文本
            task_prefix (str): 任务前缀（如"translate code to natural language: "）
            
        返回:
            torch.Tensor: 分词后的输入张量
        """
        # 添加任务前缀并分词
        input_text = f"{task_prefix}{text}"
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding="max_length"
        )
        return inputs.input_ids.to(self.device)

    def _generate_output(self, input_ids: torch.Tensor) -> str:
        """
        生成输出文本
        
        参数:
            input_ids (torch.Tensor): 输入张量
            
        返回:
            str: 生成的文本
        """
        # 生成输出
        outputs = self.model.generate(
            input_ids,
            max_length=256,
            num_beams=5,
            early_stopping=True,
            no_repeat_ngram_size=2
        )
        # 解码并清理特殊标记
        return self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True
        )

    def code_to_nl(self, code: str) -> str:
        """
        将代码转换为自然语言描述
        
        参数:
            code (str): 输入代码字符串
            
        返回:
            str: 自然语言描述
            
        异常:
            ValueError: 当输入为空时抛出
        """
        if not code.strip():
            raise ValueError("输入代码不能为空")
            
        try:
            input_ids = self._preprocess_input(code, "translate code to natural language: ")
            return self._generate_output(input_ids)
        except Exception as e:
            warnings.warn(f"代码转换失败: {str(e)}")
            return "转换过程中发生错误"

    def nl_to_code(self, description: str) -> str:
        """
        将自然语言描述转换为代码
        
        参数:
            description (str): 自然语言描述
            
        返回:
            str: 生成的代码
            
        异常:
            ValueError: 当输入为空时抛出
        """
        if not description.strip():
            raise ValueError("输入描述不能为空")
            
        try:
            input_ids = self._preprocess_input(description, "translate natural language to code: ")
            return self._generate_output(input_ids)
        except Exception as e:
            warnings.warn(f"自然语言转换失败: {str(e)}")
            return "转换过程中发生错误"

    def bidirectional_translate(self, text: str, to_code: bool = False) -> Tuple[str, str]:
        """
        双向转换接口
        
        参数:
            text (str): 输入文本（代码或自然语言）
            to_code (bool): 是否转换为代码，默认为False（转换为自然语言）
            
        返回:
            Tuple[str, str]: (原始文本, 转换结果)
        """
        if to_code:
            return text, self.nl_to_code(text)
        return text, self.code_to_nl(text)

# 使用示例
if __name__ == "__main__":
    try:
        # 初始化转换器
        translator = CodeNLTranslator()
        
        # 示例1：代码转自然语言
        code = "def add(a, b):\n    return a + b"
        nl_result = translator.code_to_nl(code)
        print(f"代码: {code}\n自然语言: {nl_result}\n")
        
        # 示例2：自然语言转代码
        description = "创建一个函数计算两个数的和"
        code_result = translator.nl_to_code(description)
        print(f"自然语言: {description}\n代码: {code_result}\n")
        
        # 示例3：双向转换
        original, converted = translator.bidirectional_translate(code, to_code=True)
        print(f"原始: {original}\n转换结果: {converted}")
        
    except Exception as e:
        print(f"错误: {str(e)}")