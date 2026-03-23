import re
import ast
import traceback
from typing import Optional, Dict, Any

class RLHFCodeFixer:
    """
    强化学习闭环代码修复器，通过持续迭代修正代码直到可执行。
    
    该类实现了一个基于错误反馈的自动代码修复机制，通过以下步骤工作：
    1. 执行初始代码并捕获错误
    2. 根据错误信息生成修复策略
    3. 应用修复并验证结果
    4. 重复过程直到代码成功执行
    
    Attributes:
        initial_code (str): 初始代码字符串
        max_iterations (int): 最大修复迭代次数
        current_code (str): 当前修复后的代码
        execution_history (list): 执行历史记录
    """
    
    def __init__(self, initial_code: str, max_iterations: int = 5):
        """
        初始化代码修复器
        
        Args:
            initial_code (str): 需要修复的初始代码
            max_iterations (int): 最大修复尝试次数，默认为5
        """
        self.initial_code = initial_code
        self.max_iterations = max_iterations
        self.current_code = initial_code
        self.execution_history = []
        
    def _execute_code(self) -> Dict[str, Any]:
        """
        执行当前代码并返回执行结果
        
        Returns:
            Dict: 包含执行状态、结果和错误信息的字典
        """
        try:
            # 创建独立命名空间执行代码
            namespace = {}
            exec(self.current_code, namespace)
            
            # 检查是否生成了可执行节点
            if 'execute_node' in namespace:
                return {
                    'status': 'success',
                    'result': namespace['execute_node'](),
                    'error': None
                }
            else:
                return {
                    'status': 'incomplete',
                    'result': None,
                    'error': "代码未生成可执行节点"
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'result': None,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _generate_fix(self, error_msg: str, traceback_info: Optional[str] = None) -> str:
        """
        根据错误信息生成修复策略
        
        Args:
            error_msg (str): 错误信息
            traceback_info (str): 可选的堆栈跟踪信息
            
        Returns:
            str: 修复后的代码
        """
        # 基础修复规则库
        fix_rules = {
            r"NameError: name '(\w+)' is not defined": 
                lambda m: f"# 修复：添加缺失变量\n{m.group(1)} = None\n\n{self.current_code}",
            r"SyntaxError: invalid syntax":
                lambda m: f"# 修复：修正语法错误\n{self.current_code}\n# 添加缺失的冒号或括号",
            r"TypeError: unsupported operand type\(s\) for (\+)":
                lambda m: f"# 修复：类型转换\nstr({m.group(1)}) + str({m.group(1)})\n\n{self.current_code}",
            r"IndexError: list index out of range":
                lambda m: f"# 修复：添加边界检查\nif 0 <= index < len(list):\n    # 原代码\n\n{self.current_code}"
        }
        
        # 尝试匹配错误模式
        for pattern, fix_func in fix_rules.items():
            match = re.search(pattern, error_msg)
            if match:
                return fix_func(match)
        
        # 默认修复策略：添加错误处理
        return f"""
try:
    {self.current_code}
except Exception as e:
    print(f"错误: {{e}}")
    # 修复逻辑待实现
"""
    
    def _validate_syntax(self, code: str) -> bool:
        """
        验证代码语法是否正确
        
        Args:
            code (str): 待验证的代码
            
        Returns:
            bool: 语法是否正确
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def fix_until_success(self) -> Dict[str, Any]:
        """
        持续修复代码直到成功执行或达到最大迭代次数
        
        Returns:
            Dict: 最终执行结果和修复历史
        """
        for iteration in range(self.max_iterations):
            print(f"尝试执行 (迭代 {iteration + 1}/{self.max_iterations})")
            
            # 执行当前代码
            execution_result = self._execute_code()
            self.execution_history.append({
                'iteration': iteration,
                'code': self.current_code,
                'result': execution_result
            })
            
            if execution_result['status'] == 'success':
                return {
                    'status': 'success',
                    'final_code': self.current_code,
                    'result': execution_result['result'],
                    'iterations': iteration + 1,
                    'history': self.execution_history
                }
            
            # 生成修复代码
            error_msg = execution_result['error']
            traceback_info = execution_result.get('traceback', '')
            
            print(f"捕获错误: {error_msg}")
            fixed_code = self._generate_fix(error_msg, traceback_info)
            
            # 验证修复后的代码语法
            if not self._validate_syntax(fixed_code):
                print("修复代码语法无效，尝试基础修复...")
                fixed_code = self._generate_fix("SyntaxError: invalid syntax")
            
            self.current_code = fixed_code
            print("应用修复...")
        
        return {
            'status': 'failed',
            'final_code': self.current_code,
            'error': f"达到最大迭代次数 {self.max_iterations}",
            'history': self.execution_history
        }

# 示例使用
if __name__ == "__main__":
    # 初始代码示例（包含常见错误）
    initial_code = """
def create_node():
    # 尝试创建可执行节点
    node = {
        'type': 'process',
        'action': lambda x: x + undefined_var  # NameError
    }
    return node

def execute_node():
    node = create_node()
    return node['action'](5)  # 触发错误
"""
    
    # 创建修复器实例
    fixer = RLHFCodeFixer(initial_code)
    
    # 执行修复过程
    result = fixer.fix_until_success()
    
    # 输出结果
    print("\n=== 修复结果 ===")
    print(f"状态: {result['status']}")
    print(f"最终代码:\n{result['final_code']}")
    
    if result['status'] == 'success':
        print(f"执行结果: {result['result']}")
    else:
        print(f"最终错误: {result['error']}")
    
    print("\n=== 执行历史 ===")
    for entry in result['history']:
        print(f"迭代 {entry['iteration'] + 1}:")
        print(f"  状态: {entry['result']['status']}")
        if entry['result']['error']:
            print(f"  错误: {entry['result']['error']}")