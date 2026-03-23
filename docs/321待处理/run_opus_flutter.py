#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Opus Flutter 工程师 — 实践调用脚本
====================================
用法:
  1. 默认生成（微信克隆）:
     python run_opus_flutter.py

  2. 自定义需求:
     python run_opus_flutter.py "做一个小红书克隆，包含瀑布流首页、笔记详情、发布、个人中心"

  3. 指定输出目录:
     python run_opus_flutter.py "做一个抖音克隆" --output ~/Desktop/my_douyin

  4. 仅分析需求（不生成代码）:
     python run_opus_flutter.py "做一个超级App" --analyze-only

  5. 仅校验已有项目:
     python run_opus_flutter.py --verify ~/Desktop/testProject/wechat_clone

  6. 仅运行自动修复:
     python run_opus_flutter.py --fix ~/Desktop/testProject/wechat_clone
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# 设置项目路径
PROJECT_DIR = Path(__file__).parent.parent.parent
WORKSPACE_DIR = PROJECT_DIR / "workspace"
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(WORKSPACE_DIR))

# 默认输出目录
DEFAULT_OUTPUT = str(WORKSPACE_DIR / "outputs" / f"flutter_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def main():
    parser = argparse.ArgumentParser(
        description="Opus Flutter 工程师 — 复刻 Claude Opus 4.6 的 Flutter 项目生成能力",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_opus_flutter.py
  python run_opus_flutter.py "做一个外卖App"
  python run_opus_flutter.py "做一个聊天App" --output ./my_chat_app
  python run_opus_flutter.py --verify ./existing_project
  python run_opus_flutter.py --fix ./existing_project
  python run_opus_flutter.py "做一个图片浏览器" --analyze-only
        """
    )

    parser.add_argument("requirement", nargs="?", default=None,
                        help="自然语言需求描述（默认: 微信克隆）")
    parser.add_argument("--output", "-o", default=None,
                        help="输出目录路径")
    parser.add_argument("--analyze-only", "-a", action="store_true",
                        help="仅分析需求，不生成代码")
    parser.add_argument("--verify", "-v", default=None,
                        help="校验已有Flutter项目的质量")
    parser.add_argument("--fix", "-f", default=None,
                        help="自动修复已有Flutter项目的常见问题")
    parser.add_argument("--with-lattice", action="store_true",
                        help="注入认知网络（需要AGI核心运行）")

    args = parser.parse_args()

    # 导入技能
    try:
        from skills.opus_flutter_engineer import (
            analyze_flutter_requirement,
            design_architecture,
            generate_flutter_project,
            auto_fix_common_issues,
            generate_flutter_tests,
            generate_project_scaffolding,
            verify_project_quality,
            full_pipeline,
        )
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print(f"请确保在 AGI_PROJECT 目录下运行，或检查 skills/opus_flutter_engineer.py 是否存在")
        sys.exit(1)

    # ========== 模式1: 校验已有项目 ==========
    if args.verify:
        project_dir = os.path.expanduser(args.verify)
        print(f"\n📋 校验项目: {project_dir}\n")
        result = verify_project_quality(project_dir)
        print(f"\n{'='*60}")
        print(f"质量评分: {result['score']}/100")
        print(f"问题数量: {len(result.get('issues', []))}")
        print(f"{'='*60}")
        for issue in result.get("issues", []):
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue["severity"], "•")
            print(f"  {icon} {issue['message']}")
        if result.get("suggestions"):
            print(f"\n建议:")
            for s in result["suggestions"]:
                print(f"  💡 {s}")
        return

    # ========== 模式2: 自动修复 ==========
    if args.fix:
        project_dir = os.path.expanduser(args.fix)
        print(f"\n🔧 自动修复: {project_dir}\n")
        result = auto_fix_common_issues(project_dir)
        print(f"\n{'='*60}")
        print(f"修复项数: {result['count']}")
        print(f"{'='*60}")
        for fix in result.get("fixes_applied", []):
            print(f"  ✅ {fix}")
        if result["count"] == 0:
            print("  ✨ 没有发现需要自动修复的问题")
        return

    # ========== 模式3: 仅分析需求 ==========
    requirement = args.requirement or "做一个微信克隆应用，包含聊天列表、聊天详情、通讯录、朋友圈、个人中心"

    if args.analyze_only:
        print(f"\n🔍 需求分析: {requirement}\n")
        spec = analyze_flutter_requirement(requirement)
        print(json.dumps(spec, ensure_ascii=False, indent=2))

        print(f"\n📐 架构设计...\n")
        arch = design_architecture(spec)
        print(f"架构模式: {arch.get('pattern')}")
        print(f"文件数量: {len(arch.get('file_plan', []))}")
        print(f"依赖数量: {len(arch.get('dependencies', {}))}")
        print(f"\n文件计划:")
        for f in arch.get("file_plan", []):
            print(f"  📄 {f['path']} — {f.get('purpose', '')}")
        print(f"\n依赖列表:")
        for pkg, ver in sorted(arch.get("dependencies", {}).items()):
            print(f"  📦 {pkg}: {ver}")
        return

    # ========== 模式4: 完整管线 ==========
    output_dir = args.output or DEFAULT_OUTPUT
    output_dir = os.path.expanduser(output_dir)

    print(f"""
╔══════════════════════════════════════════════════════════╗
║           Opus Flutter 工程师 v2.0                       ║
║     复刻 Claude Opus 4.6 的 Flutter 项目生成能力          ║
╚══════════════════════════════════════════════════════════╝

📝 需求: {requirement}
📁 输出: {output_dir}
""")

    # 认知网络（可选）
    lattice = None
    if args.with_lattice:
        try:
            import agi_v13_cognitive_lattice as agi
            lattice = agi.get_lattice()
            print("🧠 认知网络已连接\n")
        except Exception:
            print("⚠️ 认知网络连接失败，继续无网络模式\n")

    # 执行完整管线
    result = full_pipeline(requirement, output_dir, lattice=lattice)

    # 输出结果
    print(f"""
{'='*60}
{'✅ 生成成功!' if result['success'] else '⚠️ 生成完成（有问题）'}
{'='*60}

📊 统计:
  领域: {result.get('domain', '?')}
  项目名: {result.get('app_name', '?')}
  文件数: {len(result.get('files', []))}
  质量分: {result.get('quality_score', 0)}/100
  耗时: {result.get('elapsed_seconds', 0)}s

📄 生成的文件:""")

    for f in result.get("files", []):
        print(f"  📄 {f['path']} ({f['lines']} 行) — {f.get('purpose', '')}")

    # 阶段详情
    print(f"\n📋 阶段执行详情:")
    for phase in result.get("phases", []):
        phase_name = phase.get("phase", "?")
        phase_info = {k: v for k, v in phase.items() if k != "phase"}
        print(f"  ▸ {phase_name}: {phase_info}")

    # 质量问题
    issues = result.get("quality_issues", [])
    if issues:
        print(f"\n⚠️ 质量问题 ({len(issues)}):")
        for issue in issues[:10]:
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.get("severity", ""), "•")
            print(f"  {icon} {issue.get('message', '')}")
        if len(issues) > 10:
            print(f"  ... 还有 {len(issues) - 10} 个问题")

    print(f"\n📁 项目路径: {output_dir}")
    print(f"\n下一步:")
    print(f"  cd {output_dir}")
    print(f"  flutter pub get")
    print(f"  flutter run")

    # 保存结果到JSON
    result_path = Path(output_dir) / "generation_report.json"
    try:
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n📊 生成报告已保存: {result_path}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
