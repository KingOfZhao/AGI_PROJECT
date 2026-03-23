#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5个超复杂Flutter项目代码实现验证脚本
通过Orchestrator生成完整Flutter项目代码，存储到 ~/Desktop/testProject/
"""
import json, time, os, sys, traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agi_v13_cognitive_lattice as agi
import orchestrator as orch_module

OUTPUT_DIR = Path.home() / "Desktop" / "testProject"
OUTPUT_DIR.mkdir(exist_ok=True)

# ===== 5个超复杂Flutter项目定义 =====
FLUTTER_PROJECTS = [
    {
        "name": "wechat_clone",
        "title": "微信核心功能Flutter实现",
        "description": """请用Flutter完整实现微信的核心功能，要求：
1. 消息列表页：联系人列表、未读消息计数、最后消息预览、置顶、免打扰
2. 聊天页：文本/图片/语音/视频消息、消息气泡、时间分组、长按菜单、引用回复
3. 朋友圈：图文发布、九宫格图片、点赞评论、时间线、下拉刷新
4. 通讯录：字母索引、搜索、分组、新朋友请求
5. 发现页：扫一扫入口、小程序入口、看一看、搜一搜
6. 个人中心：头像编辑、二维码名片、设置页
7. 状态管理：使用Riverpod/BLoC管理全局状态
8. 路由管理：命名路由、页面转场动画、深链接支持
9. 本地存储：SQLite消息持久化、SharedPreferences设置
10. 网络层：WebSocket实时通信、HTTP API封装、断线重连

请提供完整可运行的代码，包含所有dart文件、pubspec.yaml、文件目录结构。
代码要求：生产级质量、完整错误处理、性能优化(列表懒加载、图片缓存)。""",
        "files_expected": [
            "lib/main.dart",
            "lib/app.dart",
            "lib/models/message.dart",
            "lib/models/contact.dart",
            "lib/models/moment.dart",
            "lib/screens/chat_list_screen.dart",
            "lib/screens/chat_detail_screen.dart",
            "lib/screens/moments_screen.dart",
            "lib/screens/contacts_screen.dart",
            "lib/screens/discover_screen.dart",
            "lib/screens/profile_screen.dart",
            "lib/widgets/message_bubble.dart",
            "lib/widgets/moment_card.dart",
            "lib/services/websocket_service.dart",
            "lib/services/database_service.dart",
            "lib/providers/chat_provider.dart",
            "pubspec.yaml",
        ]
    },
    {
        "name": "douyin_clone",
        "title": "抖音核心功能Flutter实现",
        "description": """请用Flutter完整实现抖音的核心功能，要求：
1. 全屏视频流：PageView垂直滑动切换视频、预加载上下视频、无缝播放
2. 视频播放器：自定义控制器、进度条、音量手势、亮度手势、双击点赞特效
3. 互动层：点赞动画(心形飘起)、评论抽屉、分享面板、关注按钮、头像旋转
4. 评论系统：评论列表、回复嵌套、点赞、@提及、表情
5. 直播间：实时弹幕、礼物动画、观众列表、连麦UI
6. 拍摄页：相机预览、美颜滤镜切换、倒计时、音乐选择、速度调节
7. 搜索发现：热门话题、搜索建议、搜索结果(视频/用户/话题Tab)
8. 个人主页：作品/喜欢Tab、粉丝/关注数、编辑资料
9. 性能优化：视频预加载策略、内存管理(释放非可见视频)、FPS优化
10. 动画系统：点赞粒子效果、页面转场、弹幕滚动、礼物动画

请提供完整可运行的代码。视频播放使用video_player或chewie。
特别注意：全屏视频滑动的流畅性和内存管理是核心难点。""",
        "files_expected": [
            "lib/main.dart",
            "lib/screens/video_feed_screen.dart",
            "lib/screens/live_room_screen.dart",
            "lib/screens/camera_screen.dart",
            "lib/screens/search_screen.dart",
            "lib/screens/profile_screen.dart",
            "lib/widgets/video_player_widget.dart",
            "lib/widgets/interaction_panel.dart",
            "lib/widgets/comment_drawer.dart",
            "lib/widgets/danmaku_widget.dart",
            "lib/widgets/like_animation.dart",
            "lib/widgets/gift_animation.dart",
            "lib/services/video_preload_service.dart",
            "lib/models/video.dart",
            "lib/providers/video_provider.dart",
            "pubspec.yaml",
        ]
    },
    {
        "name": "xiaohongshu_clone",
        "title": "小红书核心功能Flutter实现",
        "description": """请用Flutter完整实现小红书的核心功能，要求：
1. 瀑布流首页：双列不等高瀑布流布局、图片自适应高度、懒加载、下拉刷新
2. 笔记详情页：轮播图片/视频、标题+正文、标签、位置、商品链接
3. 互动功能：点赞、收藏、评论、分享、关注作者
4. 发布笔记：多图选择、图片编辑(滤镜/裁剪/文字)、标签添加、话题关联
5. 搜索发现：搜索建议、分类浏览、热门话题、推荐用户
6. 个人主页：笔记列表、收藏列表、获赞数据、编辑资料
7. 电商功能：商品卡片、价格标签、购买链接、商品详情弹窗
8. 消息系统：互动通知(点赞/评论/关注)、私信列表
9. 瀑布流核心：自定义RenderObject或使用flutter_staggered_grid_view
10. 图片处理：高质量图片加载、缩略图策略、EXIF方向处理

请提供完整可运行的代码。瀑布流的性能和图片加载策略是核心难点。
使用cached_network_image做图片缓存，shimmer做加载占位。""",
        "files_expected": [
            "lib/main.dart",
            "lib/screens/home_screen.dart",
            "lib/screens/note_detail_screen.dart",
            "lib/screens/publish_screen.dart",
            "lib/screens/search_screen.dart",
            "lib/screens/profile_screen.dart",
            "lib/screens/message_screen.dart",
            "lib/widgets/waterfall_grid.dart",
            "lib/widgets/note_card.dart",
            "lib/widgets/image_carousel.dart",
            "lib/widgets/product_card.dart",
            "lib/widgets/tag_input.dart",
            "lib/models/note.dart",
            "lib/models/product.dart",
            "lib/services/image_service.dart",
            "lib/providers/note_provider.dart",
            "pubspec.yaml",
        ]
    },
    {
        "name": "image_8k_viewer",
        "title": "8K超高清图片查看器Flutter实现",
        "description": """请用Flutter实现一个高性能8K超高清图片查看器，要求：
1. 分块加载引擎：将8K图片(7680x4320)分割为256x256瓦片，按需加载可见区域
2. 多级缩放：支持0.1x到20x缩放，pinch手势缩放、双击缩放、缩放动画
3. 平滑平移：惯性滚动、边界弹回、fling手势
4. 金字塔缓存：多分辨率层级(1/16→1/8→1/4→1/2→原图)，根据缩放级别选择层
5. 内存管理：LRU瓦片缓存、内存压力监控、自动释放远离视口的瓦片
6. 图片解码：后台Isolate解码、JPEG渐进式加载、WebP支持
7. EXIF信息：解析并显示拍摄参数、GPS位置、直方图
8. 图片列表：缩略图网格、滑动浏览、预加载相邻图片
9. 手势系统：单指平移、双指缩放旋转、双击放大/还原、长按菜单
10. 渲染优化：CustomPainter直接绘制瓦片、RepaintBoundary隔离、帧率监控

请提供完整可运行的代码。核心难点是瓦片管理和60fps流畅交互。
这是一个技术密集型项目，需要自定义渲染管线。""",
        "files_expected": [
            "lib/main.dart",
            "lib/screens/gallery_screen.dart",
            "lib/screens/viewer_screen.dart",
            "lib/engine/tile_manager.dart",
            "lib/engine/tile_cache.dart",
            "lib/engine/pyramid_loader.dart",
            "lib/engine/image_decoder.dart",
            "lib/widgets/tile_painter.dart",
            "lib/widgets/gesture_handler.dart",
            "lib/widgets/zoom_controls.dart",
            "lib/widgets/exif_panel.dart",
            "lib/widgets/histogram_widget.dart",
            "lib/models/tile.dart",
            "lib/models/image_meta.dart",
            "lib/utils/memory_monitor.dart",
            "lib/utils/fps_counter.dart",
            "pubspec.yaml",
        ]
    },
    {
        "name": "super_app",
        "title": "超级App(外卖+打车+支付)Flutter实现",
        "description": """请用Flutter实现一个集成外卖、打车、支付的超级App，要求：

【外卖模块】
1. 餐厅列表：距离排序、评分过滤、品类筛选、搜索
2. 菜品页：分类侧边栏、购物车浮层、规格选择(辣度/份量)、加购动画
3. 订单页：地址选择、优惠券、配送费计算、下单确认
4. 骑手追踪：地图实时位置、预计送达时间、路线显示

【打车模块】
5. 地图选点：高德/百度地图集成、起终点标记、路线预览
6. 叫车流程：车型选择、价格预估、排队等待、司机信息
7. 行程中：实时轨迹、剩余时间、紧急联系、行程分享

【支付模块】
8. 钱包：余额、充值、提现、交易记录
9. 支付：密码支付、生物识别(FaceID/指纹)、二维码收付款
10. 账单：按月统计、分类图表、导出

【通用】
11. 状态管理：GetX或Riverpod全局状态
12. 地图集成：多地图SDK适配层
13. 推送通知：订单状态变更、骑手/司机消息
14. 动画：加购小球动画、地图车辆平滑移动、支付成功烟花

请提供完整可运行的代码。这是最复杂的项目，模块间需要共享状态。""",
        "files_expected": [
            "lib/main.dart",
            "lib/app_shell.dart",
            "lib/food/screens/restaurant_list.dart",
            "lib/food/screens/menu_screen.dart",
            "lib/food/screens/order_screen.dart",
            "lib/food/screens/tracking_screen.dart",
            "lib/food/widgets/cart_sheet.dart",
            "lib/ride/screens/map_screen.dart",
            "lib/ride/screens/ride_screen.dart",
            "lib/ride/widgets/route_overlay.dart",
            "lib/pay/screens/wallet_screen.dart",
            "lib/pay/screens/payment_screen.dart",
            "lib/pay/screens/bills_screen.dart",
            "lib/pay/widgets/qr_scanner.dart",
            "lib/shared/services/map_service.dart",
            "lib/shared/models/order.dart",
            "lib/shared/providers/auth_provider.dart",
            "pubspec.yaml",
        ]
    },
]


def generate_project(orchestrator, project, output_dir):
    """使用Orchestrator为单个Flutter项目生成完整代码"""
    proj_dir = output_dir / project["name"]
    proj_dir.mkdir(exist_ok=True)

    result = {
        "name": project["name"],
        "title": project["title"],
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "files_generated": [],
        "thinking_steps": [],
        "model_used": None,
        "complexity": 0,
        "duration_ms": 0,
        "error": None,
        "response_preview": "",
    }

    t0 = time.time()
    try:
        # 第一步：整体架构和核心文件生成
        print(f"    [架构] 生成项目架构和核心代码...")
        orch_result = orchestrator.process(
            project["description"],
            context_nodes=[],
            enable_tracking=True
        )
        result["model_used"] = orch_result.get("model_used", "unknown")
        result["complexity"] = orch_result.get("complexity", 0)
        result["thinking_steps"] = orch_result.get("thinking_steps", [])

        main_text = orch_result.get("text", "")
        result["response_preview"] = main_text[:500]

        # 保存主响应
        main_file = proj_dir / "architecture_response.md"
        with open(main_file, "w", encoding="utf-8") as f:
            f.write(f"# {project['title']}\n\n")
            f.write(f"**模型**: {result['model_used']}\n")
            f.write(f"**复杂度**: {result['complexity']}\n\n")
            f.write(main_text)
        result["files_generated"].append(str(main_file.relative_to(output_dir)))

        # 第二步：逐个文件生成代码
        for file_path in project["files_expected"]:
            print(f"    [代码] 生成 {file_path}...", end="", flush=True)
            file_prompt = (
                f"作为{project['title']}项目的一部分，请生成以下文件的完整Flutter/Dart代码：\n"
                f"文件路径: {file_path}\n"
                f"项目背景: {project['description'][:200]}...\n\n"
                f"要求：\n"
                f"1. 生成完整可运行的代码，不要省略任何部分\n"
                f"2. 包含必要的import语句\n"
                f"3. 包含完整的类/Widget实现\n"
                f"4. 添加关键注释说明\n"
                f"5. 遵循Flutter最佳实践\n\n"
                f"请只输出该文件的代码，不要包含其他文件的代码。"
            )
            try:
                file_result = orchestrator.process(
                    file_prompt, context_nodes=[], enable_tracking=False
                )
                file_text = file_result.get("text", "")

                # 提取代码块
                code = extract_code_block(file_text, file_path)

                # 保存文件
                target = proj_dir / file_path
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(code)
                result["files_generated"].append(file_path)
                print(f" ✓ ({len(code)} chars)")
            except Exception as e:
                print(f" ✗ {e}")

        result["status"] = "success"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        traceback.print_exc()

    result["duration_ms"] = int((time.time() - t0) * 1000)
    return result


def extract_code_block(text, file_path):
    """从LLM响应中提取代码块"""
    # 尝试提取 ```dart ... ``` 或 ```yaml ... ``` 代码块
    ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
    lang_hints = ["dart", "yaml", "yml", ""] if ext in ("dart", "yaml") else [""]

    import re
    for lang in lang_hints:
        pattern = rf"```{lang}\s*\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # 返回最长的代码块
            return max(matches, key=len).strip()

    # 如果没有代码块标记，返回全文
    return text.strip()


def main():
    print("=" * 60)
    print("  5个超复杂Flutter项目代码验证")
    print(f"  输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    # 初始化
    print("\n[初始化] 认知格和Orchestrator...")
    lattice = agi.CognitiveLattice()
    agi.seed_database(lattice)
    orchestrator = orch_module.TaskOrchestrator(lattice)
    print("  ✓ 初始化完成\n")

    all_results = []
    for i, project in enumerate(FLUTTER_PROJECTS, 1):
        print(f"\n{'='*50}")
        print(f"  项目 {i}/5: {project['title']}")
        print(f"  预期文件数: {len(project['files_expected'])}")
        print(f"{'='*50}")

        result = generate_project(orchestrator, project, OUTPUT_DIR)
        all_results.append(result)

        status_icon = "✓" if result["status"] == "success" else "✗"
        print(f"\n  [{status_icon}] {project['title']}")
        print(f"      模型: {result['model_used']} | 复杂度: {result['complexity']:.1f}")
        print(f"      生成文件: {len(result['files_generated'])}/{len(project['files_expected'])+1}")
        print(f"      耗时: {result['duration_ms']}ms")

    # 保存汇总
    summary = {
        "total_projects": len(FLUTTER_PROJECTS),
        "timestamp": datetime.now().isoformat(),
        "output_dir": str(OUTPUT_DIR),
        "projects": all_results,
    }
    summary_file = OUTPUT_DIR / "verification_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  全部完成!")
    print(f"  汇总报告: {summary_file}")
    print(f"  项目目录: {OUTPUT_DIR}")
    for r in all_results:
        icon = "✓" if r["status"] == "success" else "✗"
        print(f"    [{icon}] {r['title']} - {len(r['files_generated'])} files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
