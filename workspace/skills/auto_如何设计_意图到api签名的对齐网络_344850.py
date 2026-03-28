"""
高级意图到API签名对齐网络模块

该模块实现了将自然语言描述的微观功能意图（如'把这张图变模糊'）无损映射到具体代码函数签名的系统。
核心功能包括：
1. 意图解析与标准化
2. 类型系统感知的API签名生成
3. 异常处理推断
4. 返回值类型推断

输入格式示例：
{
    "intent": "把这张图变模糊",
    "context": {
        "language": "python",
        "libraries": ["opencv-python"],
        "target_function": "gaussian_blur"
    }
}

输出格式示例：
{
    "signature": {
        "name": "apply_gaussian_blur",
        "parameters": [
            {"name": "image", "type": "np.ndarray", "desc": "输入图像"},
            {"name": "kernel_size", "type": "Tuple[int, int]", "default": "(5, 5)"}
        ],
        "return_type": "np.ndarray",
        "exceptions": ["ValueError"]
    },
    "implementation_snippet": "..."
}
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import re

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class APIParameter:
    """API参数数据类"""
    name: str
    type: str
    desc: str = ""
    default: Optional[str] = None

@dataclass
class APISignature:
    """API签名数据类"""
    name: str
    parameters: List[APIParameter]
    return_type: str
    exceptions: List[str]
    implementation_snippet: str = ""

class IntentAlignmentNetwork:
    """
    意图到API签名对齐网络
    
    该类实现了将自然语言意图映射到精确API签名的功能，考虑了类型系统、
    库设计哲学和最佳实践。
    """
    
    def __init__(self):
        self.type_system = {
            'python': {
                'image': 'np.ndarray',
                'number': 'Union[int, float]',
                'string': 'str',
                'list': 'List[Any]',
                'dict': 'Dict[str, Any]'
            },
            'java': {
                'image': 'BufferedImage',
                'number': 'double',
                'string': 'String',
                'list': 'List<Object>',
                'dict': 'Map<String, Object>'
            }
        }
        
        self.library_patterns = {
            'opencv-python': {
                'blur': {
                    'function': 'GaussianBlur',
                    'params': [
                        APIParameter('src', 'np.ndarray', '输入图像'),
                        APIParameter('ksize', 'Tuple[int, int]', '核大小', '(5, 5)'),
                        APIParameter('sigmaX', 'float', 'X方向标准差', '0')
                    ],
                    'return': 'np.ndarray'
                }
            },
            'pillow': {
                'blur': {
                    'function': 'filter',
                    'params': [
                        APIParameter('image', 'Image.Image', '输入图像'),
                        APIParameter('filter', 'ImageFilter.BuiltinFilter', '滤镜类型', 'ImageFilter.BLUR')
                    ],
                    'return': 'Image.Image'
                }
            }
        }
    
    def normalize_intent(self, intent: str) -> Dict[str, str]:
        """
        标准化自然语言意图
        
        参数:
            intent: 原始意图字符串，如"把这张图变模糊"
            
        返回:
            包含标准化意图信息的字典，包括:
            - operation: 主要操作类型
            - target: 操作目标
            - modifiers: 修饰词列表
            
        示例:
            >>> normalize_intent("把这张图变模糊")
            {'operation': 'blur', 'target': 'image', 'modifiers': ['变']}
        """
        if not intent or not isinstance(intent, str):
            raise ValueError("意图必须是非空字符串")
            
        # 移除标点符号并分词
        cleaned = re.sub(r'[^\w\s]', '', intent.lower())
        words = cleaned.split()
        
        # 意图识别模式
        patterns = {
            'blur': ['模糊', 'blur', '变模糊', '模糊化'],
            'resize': ['调整大小', 'resize', '缩放', '改变尺寸'],
            'rotate': ['旋转', 'rotate', '转动'],
            'crop': ['裁剪', 'crop', '剪切']
        }
        
        result = {'operation': '', 'target': '', 'modifiers': []}
        
        # 识别操作
        for op, keywords in patterns.items():
            if any(kw in words for kw in keywords):
                result['operation'] = op
                break
        
        # 识别目标
        if '图' in words or 'image' in words:
            result['target'] = 'image'
        
        # 识别修饰词
        modifiers = ['变', '快速', '高质量', '渐变']
        result['modifiers'] = [w for w in words if w in modifiers]
        
        logger.info(f"标准化意图: {intent} -> {result}")
        return result
    
    def generate_signature(
        self,
        intent: str,
        language: str = 'python',
        library: Optional[str] = None
    ) -> APISignature:
        """
        生成API签名
        
        参数:
            intent: 自然语言意图
            language: 目标编程语言
            library: 目标库名称
            
        返回:
            APISignature对象
            
        示例:
            >>> sig = generate_signature("把这张图变模糊", "python", "opencv-python")
            >>> sig.name
            'apply_gaussian_blur'
        """
        if language not in self.type_system:
            raise ValueError(f"不支持的语言: {language}")
            
        normalized = self.normalize_intent(intent)
        operation = normalized['operation']
        target = normalized['target']
        
        if not operation or not target:
            raise ValueError("无法从意图中识别出明确的操作或目标")
            
        # 确定库
        if not library:
            library = self._infer_library(language, operation)
            logger.info(f"自动推断库: {library}")
            
        if library not in self.library_patterns:
            raise ValueError(f"不支持的库: {library}")
            
        # 获取库特定模式
        pattern = self.library_patterns[library].get(operation)
        if not pattern:
            raise ValueError(f"库 {library} 不支持操作: {operation}")
            
        # 生成函数名
        func_name = self._generate_function_name(operation, normalized['modifiers'])
        
        # 创建参数列表
        params = []
        for p in pattern['params']:
            params.append(APIParameter(
                name=p.name,
                type=self._map_type(p.type, language),
                desc=p.desc,
                default=p.default
            ))
            
        # 推断异常
        exceptions = self._infer_exceptions(library, operation)
        
        # 生成实现片段
        snippet = self._generate_implementation_snippet(
            library, operation, func_name, params, pattern['return']
        )
        
        return APISignature(
            name=func_name,
            parameters=params,
            return_type=self._map_type(pattern['return'], language),
            exceptions=exceptions,
            implementation_snippet=snippet
        )
    
    def _infer_library(self, language: str, operation: str) -> str:
        """
        根据语言和操作推断最合适的库
        
        参数:
            language: 编程语言
            operation: 操作类型
            
        返回:
            推断的库名称
        """
        if language == 'python':
            if operation in ['blur', 'resize', 'rotate']:
                return 'opencv-python'
        elif language == 'java':
            if operation == 'blur':
                return 'java-image-processing'
        return 'standard-library'
    
    def _generate_function_name(self, operation: str, modifiers: List[str]) -> str:
        """
        生成函数名称
        
        参数:
            operation: 操作类型
            modifiers: 修饰词列表
            
        返回:
            生成的函数名
        """
        op_map = {
            'blur': 'blur',
            'resize': 'resize',
            'rotate': 'rotate',
            'crop': 'crop'
        }
        
        base = op_map.get(operation, operation)
        if '快速' in modifiers:
            base = f"fast_{base}"
        if '高质量' in modifiers:
            base = f"high_quality_{base}"
            
        return f"apply_{base}"
    
    def _map_type(self, type_str: str, language: str) -> str:
        """
        将通用类型映射到特定语言的类型
        
        参数:
            type_str: 类型字符串
            language: 目标语言
            
        返回:
            映射后的类型字符串
        """
        if language not in self.type_system:
            return type_str
            
        # 检查是否是已知的通用类型
        for generic, specific in self.type_system[language].items():
            if generic in type_str.lower():
                return type_str.replace(generic, specific)
        return type_str
    
    def _infer_exceptions(self, library: str, operation: str) -> List[str]:
        """
        推断可能的异常
        
        参数:
            library: 库名称
            operation: 操作类型
            
        返回:
            可能的异常列表
        """
        common_exceptions = ['ValueError', 'TypeError']
        
        if library == 'opencv-python':
            if operation == 'blur':
                return common_exceptions + ['cv2.error']
        elif library == 'pillow':
            if operation == 'blur':
                return common_exceptions + ['PIL.UnidentifiedImageError']
                
        return common_exceptions
    
    def _generate_implementation_snippet(
        self,
        library: str,
        operation: str,
        func_name: str,
        params: List[APIParameter],
        return_type: str
    ) -> str:
        """
        生成实现代码片段
        
        参数:
            library: 库名称
            operation: 操作类型
            func_name: 函数名
            params: 参数列表
            return_type: 返回类型
            
        返回:
            实现代码片段字符串
        """
        param_str = ", ".join(f"{p.name}: {p.type}" for p in params)
        defaults = [p for p in params if p.default is not None]
        
        snippet = f"def {func_name}({param_str}) -> {return_type}:\n"
        snippet += f'    """实现{operation}操作"""\n'
        
        if library == 'opencv-python' and operation == 'blur':
            snippet += "    import cv2\n"
            snippet += "    if kernel_size[0] % 2 == 0 or kernel_size[1] % 2 == 0:\n"
            snippet += "        raise ValueError('核大小必须是奇数')\n"
            snippet += "    return cv2.GaussianBlur(src, kernel_size, sigmaX)\n"
        elif library == 'pillow' and operation == 'blur':
            snippet += "    from PIL import ImageFilter\n"
            snippet += "    return image.filter(filter)\n"
        else:
            snippet += "    # 实现细节取决于具体库\n"
            snippet += "    pass\n"
            
        return snippet

def validate_intent_data(data: Dict) -> bool:
    """
    验证输入意图数据
    
    参数:
        data: 输入数据字典
        
    返回:
        bool: 数据是否有效
        
    示例:
        >>> validate_intent_data({'intent': '模糊图像', 'context': {'language': 'python'}})
        True
    """
    required_fields = ['intent']
    if not all(field in data for field in required_fields):
        logger.error("输入数据缺少必要字段")
        return False
        
    if not isinstance(data['intent'], str):
        logger.error("意图必须是字符串")
        return False
        
    if 'context' in data:
        if not isinstance(data['context'], dict):
            logger.error("上下文必须是字典")
            return False
            
        if 'language' in data['context'] and not isinstance(data['context']['language'], str):
            logger.error("语言必须是字符串")
            return False
            
    return True

def main():
    """使用示例"""
    # 示例1: 基本用法
    intent_system = IntentAlignmentNetwork()
    intent = "把这张图快速变模糊"
    
    try:
        signature = intent_system.generate_signature(intent, "python", "opencv-python")
        print(f"生成的API签名:\n{signature}")
    except ValueError as e:
        print(f"错误: {e}")
    
    # 示例2: 带验证的完整流程
    input_data = {
        "intent": "高质量模糊这张图片",
        "context": {
            "language": "python",
            "library": "pillow"
        }
    }
    
    if validate_intent_data(input_data):
        sig = intent_system.generate_signature(
            input_data['intent'],
            input_data['context']['language'],
            input_data['context']['library']
        )
        print("\n高质量模糊的API签名:")
        print(f"函数名: {sig.name}")
        print(f"参数: {[p.name for p in sig.parameters]}")
        print(f"返回类型: {sig.return_type}")
        print("\n实现片段:")
        print(sig.implementation_snippet)

if __name__ == "__main__":
    main()