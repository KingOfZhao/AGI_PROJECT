#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI 全速成长系统 — 启动脚本
===========================
用法:
  1. 默认运行（10轮，最少100万tokens/小时）:
     python run_growth.py

  2. 自定义轮次:
     python run_growth.py --rounds 20

  3. 自定义tokens目标:
     python run_growth.py --target-tokens 2000000

  4. 仅测试模式（不消耗大量tokens）:
     python run_growth.py --test-mode

  5. 从指定轮次继续:
     python run_growth.py --resume 5

  6. 查看历史报告:
     python run_growth.py --report
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 设置项目路径
PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# 默认配置
DEFAULT_CONFIG = {
    "min_rounds": 10,
    "max_rounds": 100,
    "target_tokens_per_hour": 1000000,  # 100万
    "node_confidence_threshold": 0.7,
    "skill_validation_threshold": 80,
    "check_interval": 5,  # 每5个SKILL检查一次
    "glm5_temperature": 0.8,
    "database_write_buffer_ratio": 0.1,  # 10% tokens预留给数据库写入
}


def main():
    parser = argparse.ArgumentParser(
        description="AGI 全速成长系统 — GLM-5驱动的四向碰撞真实节点获取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_growth.py                              # 默认运行10轮
  python run_growth.py --rounds 20                  # 运行20轮
  python run_growth.py --target-tokens 2000000      # 目标200万tokens/小时
  python run_growth.py --test-mode                  # 测试模式（低消耗）
  python run_growth.py --resume 5                   # 从第5轮继续
  python run_growth.py --report                     # 查看历史报告
        """
    )

    parser.add_argument("--rounds", "-r", type=int, default=None,
                        help="循环轮次（默认: 10）")
    parser.add_argument("--target-tokens", "-t", type=int, default=None,
                        help="每小时目标tokens消耗（默认: 1000000）")
    parser.add_argument("--test-mode", action="store_true",
                        help="测试模式（低tokens消耗）")
    parser.add_argument("--resume", type=int, default=None,
                        help="从指定轮次继续")
    parser.add_argument("--report", action="store_true",
                        help="查看历史成长报告")
    parser.add_argument("--config", default=None,
                        help="自定义配置文件路径（JSON格式）")

    args = parser.parse_args()

    # 加载配置
    config = DEFAULT_CONFIG.copy()
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config.update(json.load(f))
    
    if args.rounds:
        config["min_rounds"] = args.rounds
    if args.target_tokens:
        config["target_tokens_per_hour"] = args.target_tokens
    if args.test_mode:
        config["target_tokens_per_hour"] = 10000  # 测试模式仅1万tokens/小时
        config["min_rounds"] = 2

    # 查看报告模式
    if args.report:
        show_growth_report()
        return

    # 检查环境
    if not check_environment():
        print("❌ 环境检查失败，请先完成环境准备")
        sys.exit(1)

    # 启动成长系统
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           AGI 全速成长系统 v1.0                          ║
║     GLM-5 驱动的四向碰撞真实节点获取                      ║
╚══════════════════════════════════════════════════════════╝

配置:
  最少轮次: {config['min_rounds']}
  最多轮次: {config['max_rounds']}
  目标tokens/小时: {config['target_tokens_per_hour']:,}
  节点confidence阈值: {config['node_confidence_threshold']}
  SKILL验证阈值: {config['skill_validation_threshold']}
  测试模式: {'是' if args.test_mode else '否'}
""")

    # 导入核心引擎（延迟导入以便先检查环境）
    try:
        from growth_engine import GrowthEngine
    except ImportError:
        print("❌ 无法导入 growth_engine，请先实现核心引擎代码")
        print("提示: 参考 docs/321自成长待处理/AGI全速成长系统_实践清单.md")
        sys.exit(1)

    # 创建引擎实例
    engine = GrowthEngine(config)

    # 恢复模式
    if args.resume:
        print(f"\n从第 {args.resume} 轮继续...\n")
        engine.resume_from_round(args.resume)
    
    # 运行成长循环
    try:
        engine.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断，正在保存当前进度...")
        engine.save_checkpoint()
        print("✅ 进度已保存，可使用 --resume 参数继续")
    except Exception as e:
        print(f"\n\n❌ 运行错误: {e}")
        import traceback
        traceback.print_exc()
        engine.save_checkpoint()
        sys.exit(1)


def check_environment() -> bool:
    """检查环境是否就绪"""
    print("🔍 检查环境...")
    
    issues = []
    
    # 1. 检查智谱API配置
    try:
        import agi_v13_cognitive_lattice as agi
        if not hasattr(agi, '_zhipu_call_direct'):
            issues.append("智谱API未配置")
    except ImportError:
        issues.append("无法导入 agi_v13_cognitive_lattice")
    
    # 2. 检查数据库
    db_path = PROJECT_DIR / "memory.db"
    if not db_path.exists():
        issues.append(f"数据库不存在: {db_path}")
    
    # 3. 检查必要目录
    required_dirs = [
        PROJECT_DIR / "workspace" / "skills",
        PROJECT_DIR / "docs" / "321自成长待处理",
    ]
    for d in required_dirs:
        if not d.exists():
            issues.append(f"目录不存在: {d}")
    
    # 4. 检查智谱API余额（可选）
    # TODO: 实现余额检查
    
    if issues:
        print("\n❌ 环境检查发现问题:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n请参考 docs/321自成长待处理/AGI全速成长系统_实践清单.md 完成环境准备")
        return False
    
    print("✅ 环境检查通过\n")
    return True


def show_growth_report():
    """显示历史成长报告"""
    report_path = PROJECT_DIR / "docs" / "321自成长待处理" / "growth_final_report.md"
    
    if not report_path.exists():
        print("❌ 未找到成长报告，请先运行至少一轮成长循环")
        return
    
    print(report_path.read_text(encoding='utf-8'))
    
    # 也可以从数据库读取更详细的数据
    try:
        import sqlite3
        db_path = PROJECT_DIR / "memory.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 查询最近的成长统计
        cursor.execute("""
            SELECT 
                round_number,
                COUNT(*) as events,
                SUM(tokens_used) as total_tokens,
                SUM(elapsed_seconds) as total_seconds
            FROM growth_log
            GROUP BY round_number
            ORDER BY round_number DESC
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        if rows:
            print("\n\n最近10轮详细统计:\n")
            print("| 轮次 | 事件数 | Tokens | 耗时(s) |")
            print("|------|--------|--------|---------|")
            for row in rows:
                print(f"| {row[0]} | {row[1]} | {row[2]:,} | {row[3]:.1f} |")
        
        conn.close()
    except Exception as e:
        print(f"\n⚠️ 无法从数据库读取详细统计: {e}")


if __name__ == "__main__":
    main()
