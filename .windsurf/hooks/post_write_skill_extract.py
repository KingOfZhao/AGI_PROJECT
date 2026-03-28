#!/usr/bin/env python3
"""
Cascade Hook: post_write_code
当Cascade写入Python文件时，自动检查是否应提取为可复用skill。
仅记录日志，不自动创建文件（避免干扰Cascade工作流）。
"""
import sys
import json
import os
from datetime import datetime

PROJECT_ROOT = '/Users/administruter/Desktop/AGI_PROJECT'
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs', 'cascade_hooks')
os.makedirs(LOG_DIR, exist_ok=True)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        data = json.loads(raw)
    except Exception:
        return

    tool_info = data.get('tool_info', {})
    file_path = tool_info.get('file_path', '')

    # 只关注Python文件的写入
    if not file_path.endswith('.py'):
        return

    edits = tool_info.get('edits', [])
    if not edits:
        return

    # 计算新增代码行数
    total_new_lines = 0
    for edit in edits:
        new_str = edit.get('new_string', '')
        old_str = edit.get('old_string', '')
        total_new_lines += len(new_str.split('\n')) - len(old_str.split('\n'))

    # 仅记录较大的代码变更（>10行新增）
    if total_new_lines < 10:
        return

    log_entry = {
        'timestamp': data.get('timestamp', datetime.now().isoformat()),
        'trajectory_id': data.get('trajectory_id', 'unknown'),
        'file_path': file_path,
        'new_lines_added': total_new_lines,
        'edit_count': len(edits),
        'skill_candidate': total_new_lines > 30,  # 30+行可能值得提取为skill
    }

    log_file = os.path.join(LOG_DIR, f"code_writes_{datetime.now().strftime('%Y%m%d')}.jsonl")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
