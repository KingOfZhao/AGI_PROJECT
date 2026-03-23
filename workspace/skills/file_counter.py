"""
工具名: file_counter
显示名: 文件计数器
描述: 该工具用于统计指定目录及其子目录中的总文件数量。
标签: ["文件管理", "统计", "递归"]
"""

import os
import sys

# 设置项目目录路径
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)

SKILL_META = {
    "name": "file_counter",
    "display_name": "文件计数器",
    "description": "该工具用于统计指定目录及其子目录中的总文件数量。",
    "tags": ["文件管理", "统计", "递归"]
}

def count_total_files(directory_path: str) -> dict:
    """
    计算指定目录及其子目录中的总文件数量。

    参数:
    directory_path (str): 要计数的目录路径

    返回:
    dict: 包含 success 字段和 total_files 字段
    """
    try:
        total_files = 0
        for root, dirs, files in os.walk(directory_path):
            total_files += len(files)
        return {"success": True, "total_files": total_files}
    except Exception as e:
        return {"success": False, "error_message": str(e)}

if __name__ == "__main__":
    # 自测代码
    test_directory = "/path/to/test/directory"
    result = count_total_files(test_directory)
    print(result)