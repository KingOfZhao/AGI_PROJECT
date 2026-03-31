#!/usr/bin/env python3
"""
ml-summit-2025-deep-reader — CLI 入口
用法:
    python3 main.py                          # 处理所有文件
    python3 main.py --input /path/to/dir     # 指定目录
    python3 main.py --pdf-only               # 只处理PDF
    python3 main.py --cross-file             # 生成跨文件关联
"""

import argparse
import sys
import time
from pathlib import Path

# 添加本目录到path
sys.path.insert(0, str(Path(__file__).parent))

from reader import MLSummitReader


def main():
    parser = argparse.ArgumentParser(
        description="2025 ML Summit Beijing 深度阅读器 — PDF/PPTX → Markdown"
    )
    parser.add_argument("--input", "-i",
                        default="/Users/administruter/Downloads/2025MLSUMMITBJ",
                        help="输入目录路径")
    parser.add_argument("--output", "-o",
                        default=None,
                        help="输出目录路径（默认: 输入目录/markdown_output）")
    parser.add_argument("--pdf-only", action="store_true",
                        help="只处理 PDF 文件")
    parser.add_argument("--pptx-only", action="store_true",
                        help="只处理 PPTX 文件")
    parser.add_argument("--cross-file", action="store_true",
                        help="生成跨文件关联报告")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="详细输出")

    args = parser.parse_args()

    print("=" * 60)
    print("  2025 ML Summit Beijing — 深度阅读器 v1.0.0")
    print("=" * 60)

    t0 = time.time()

    reader = MLSummitReader(root_dir=args.input)
    if args.output:
        reader.output_dir = Path(args.output)
        reader.output_dir.mkdir(parents=True, exist_ok=True)

    # 批量处理
    results = reader.process_all(pdf_only=args.pdf_only, pptx_only=args.pptx_only)

    # 跨文件关联
    if args.cross_file:
        print(f"\n{'='*60}")
        print("📊 生成跨文件关联报告...")
        reader.generate_cross_file_report()

    elapsed = time.time() - t0
    print(f"\n⏱️ 总耗时: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
