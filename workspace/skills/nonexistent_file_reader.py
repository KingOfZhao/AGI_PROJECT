"""
工具名: nonexistent_file_reader
显示名: 不存在文件读取工具
描述: 该工具用于尝试读取一个不存在的文件，并返回其路径。
标签: ["文件操作", "异常处理"]
"""

import os
import sys

# 设置项目目录
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_DIR)

SKILL_META = {
    "name": "nonexistent_file_reader",
    "display_name": "不存在文件读取工具",
    "description": "该工具用于尝试读取一个不存在的文件，并返回其路径。",
    "tags": ["文件操作", "异常处理"]
}

def read_nonexistent_file(file_path: str) -> dict:
    """
    尝试读取一个不存在的文件并返回其路径。

    参数:
    file_path (str): 文件的完整路径

    返回:
    dict: 包含 success 字段和文件路径
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return {"success": True, "file_path": file_path, "content": content}
    except FileNotFoundError:
        return {"success": False, "file_path": file_path, "error": "文件不存在"}

if __name__ == "__main__":
    # 自测代码
    test_file_path = os.path.join(PROJECT_DIR, "nonexistent_file.txt")
    result = read_nonexistent_file(test_file_path)
    print(result)