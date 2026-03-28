"""
node_cleaner.py — DiePre 节点数据清洗工具

问题：待存入节点目录中 70%+ 的节点为表格碎片（内容<25字符）
目标：从源头解决数据质量问题，提取有价值的内容

从已知/未知推演中涌现的需求：
- 碎片节点浪费推演时间
- 需要区分"有价值的推演节点"和"无价值的数据残留"
"""

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from collections import Counter
from datetime import datetime


@dataclass
class NodeStats:
    """节点统计"""
    total: int = 0
    valid: int = 0
    fragments: int = 0
    by_type: dict = field(default_factory=lambda: Counter())
    by_status: dict = field(default_factory=lambda: Counter())
    avg_content_length: float = 0.0
    total_content_length: int = 0


def parse_node_file(filepath: str) -> dict:
    """
    解析单个节点文件
    
    Returns:
        dict with id, type, status, content_length, content_preview, filepath
    """
    filename = os.path.basename(filepath)
    
    # 解析文件名格式: YYYYMMDD_HHMMSS_XXXX_STATUS_TYPE.md
    parts = filename.replace('.md', '').split('_')
    
    result = {
        "filename": filename,
        "filepath": filepath,
        "node_id": parts[2] if len(parts) > 2 else "unknown",
        "timestamp": f"{parts[0]}_{parts[1]}" if len(parts) > 1 else "unknown",
        "status": "UNKNOWN",
        "type": "unknown",
        "content_length": 0,
        "content_preview": "",
    }
    
    # 提取状态
    for i, part in enumerate(parts):
        if part in ("PENDING", "INFER_PENDING", "DISPUTED", "SUCCESS", "INFER_SUCCESS", "FALSIFIED"):
            result["status"] = part
            break
    
    # 提取类型
    for i, part in enumerate(parts):
        if part in ("fixed_rule", "formula", "formula_rss", "machine_spec",
                     "machine_brand", "error_factor",
                     "inferred_error", "inferred_optimization", "inferred_variable",
                     "inferred_rule", "inferred_open_question", "open_question",
                     "standard_international", "standard_iso",
                     "standard_china", "material_type", "collision_disputed",
                     "deduction_report", "deduction_summary"):
            result["type"] = part
            break
    
    # 读取内容
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取"## 内容"后面的部分
        match = re.search(r'## 内容\s*\n(.+?)(?=\n## |\Z)', content, re.DOTALL)
        if match:
            body = match.group(1).strip()
        else:
            body = content.strip()
        
        result["content_length"] = len(body)
        result["content_preview"] = body[:200] if body else ""
        result["full_content"] = content
    except Exception:
        pass
    
    return result


def analyze_directory(dir_path: str) -> Tuple[List[dict], NodeStats]:
    """
    分析整个节点目录
    
    Returns:
        (节点列表, 统计信息)
    """
    nodes = []
    stats = NodeStats()
    
    for filename in os.listdir(dir_path):
        if not filename.endswith('.md'):
            continue
        
        filepath = os.path.join(dir_path, filename)
        node = parse_node_file(filepath)
        nodes.append(node)
        
        stats.total += 1
        stats.by_type[node["type"]] += 1
        stats.by_status[node["status"]] += 1
        stats.total_content_length += node["content_length"]
        
        if node["content_length"] >= 25:
            stats.valid += 1
        else:
            stats.fragments += 1
    
    if stats.total > 0:
        stats.avg_content_length = stats.total_content_length / stats.total
        stats.fragment_rate = round(stats.fragments / stats.total * 100, 1)
    
    # 按内容长度排序（有价值的在前）
    nodes.sort(key=lambda n: n["content_length"], reverse=True)
    
    return nodes, stats


def generate_report(stats: NodeStats, output_path: str):
    """生成分析报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": stats.total,
            "valid": stats.valid,
            "fragments": stats.fragments,
            "fragment_rate": round(stats.fragments / stats.total * 100, 1) if stats.total > 0 else 0,
            "avg_content_length": round(stats.avg_content_length, 1),
        },
        "by_type": dict(stats.by_type),
        "by_status": dict(stats.by_status),
        "recommendations": []
    }
    
    if stats.fragment_rate > 50:
        report["recommendations"].append(
            f"碎片率{stats.fragment_rate}%过高，建议上游数据生成逻辑增加内容长度校验"
        )
    if stats.by_type.get("unknown", 0) > 0:
        report["recommendations"].append(
            f"{stats.by_type['unknown']}个节点类型无法识别，需要补充解析规则"
        )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report


if __name__ == "__main__":
    node_dir = "/Users/administruter/Desktop/DiePre AI/待存入节点/"
    report_path = "/Users/administruter/Desktop/AGI_PROJECT/data/node_analysis_report.json"
    
    print("分析节点目录...")
    nodes, stats = analyze_directory(node_dir)
    
    print(f"\n{'='*50}")
    print(f"节点分析报告")
    print(f"{'='*50}")
    print(f"总节点数: {stats.total}")
    print(f"有效节点: {stats.valid}")
    print(f"碎片节点: {stats.fragments} ({stats.fragment_rate:.1f}%)")
    print(f"平均内容长度: {stats.avg_content_length:.1f} 字符")
    
    print(f"\n按状态分布:")
    for status, count in stats.by_status.most_common():
        print(f"  {status}: {count}")
    
    print(f"\n按类型分布:")
    for typ, count in stats.by_type.most_common():
        print(f"  {typ}: {count}")
    
    print(f"\n最有价值的10个节点:")
    for node in nodes[:10]:
        print(f"  [{node['status']}] {node['filename']} ({node['content_length']}字符)")
        if node['content_preview']:
            print(f"    → {node['content_preview'][:80]}...")
    
    # 生成JSON报告
    report = generate_report(stats, report_path)
    print(f"\n报告已保存: {report_path}")
    
    if report["recommendations"]:
        print(f"\n建议:")
        for rec in report["recommendations"]:
            print(f"  ⚠️ {rec}")
