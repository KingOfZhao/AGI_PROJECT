"""
技能用途:
统计指定目录及其子目录中的总文件数量。
"""

import os
import sys
from typing import Dict

# 设置项目目录
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_DIR)

SKILL_META = {
    "name": "unnamed_tool",
    "display_name": "Unnamed Tool",
    "description": "统计指定目录及其子目录中的总文件数量",
    "tags": []
}

def count_files_in_directory(directory: str) -> Dict[str, bool]:
    """
    统计指定目录及其子目录中的总文件数量。

    参数:
    directory (str): 要统计的目录路径。

    返回:
    Dict[str, bool]: 包含 success 字段，表示操作是否成功。
    """
    try:
        file_count = 0
        for root, dirs, files in os.walk(directory):
            file_count += len(files)
        
        print(f"Total number of files in {directory}: {file_count}")
        return {"success": True}
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False}

if __name__ == "__main__":
    # 自测代码
    test_directory = os.path.join(PROJECT_DIR, "test_data")
    result = count_files_in_directory(test_directory)
    print(result)