#!/usr/bin/env python3
"""
Cascade Hook: post_cascade_response
自动处理每次Cascade回复后的标准化流程:
- 提取关键信息记录到CRM
- 记录交互日志用于后续skill生成
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

    response_text = data.get('tool_info', {}).get('response', '')
    if not response_text or len(response_text) < 20:
        return

    trajectory_id = data.get('trajectory_id', 'unknown')
    timestamp = data.get('timestamp', datetime.now().isoformat())

    # 记录交互日志
    log_entry = {
        'timestamp': timestamp,
        'trajectory_id': trajectory_id,
        'response_length': len(response_text),
        'response_preview': response_text[:500],
    }

    log_file = os.path.join(LOG_DIR, f"cascade_{datetime.now().strftime('%Y%m%d')}.jsonl")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    # 尝试记录到CRM数据库
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from deduction_db import DeductionDB
        db = DeductionDB()
        # 简单记录为一条问题/交互记录
        # 仅在回复较长(有实质内容)时记录
        if len(response_text) > 200:
            db.conn.execute(
                '''INSERT OR IGNORE INTO cascade_interactions
                   (trajectory_id, timestamp, response_preview, response_length)
                   VALUES (?, ?, ?, ?)''',
                (trajectory_id, timestamp, response_text[:1000], len(response_text))
            )
            db.conn.commit()
        db.close()
    except Exception:
        pass  # CRM记录失败不阻断


if __name__ == '__main__':
    main()
