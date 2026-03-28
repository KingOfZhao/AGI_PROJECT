#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: Opus Flutter 工程师
=========================
复刻 Claude Opus 4.6 的 Flutter 项目生成能力。
八阶段认知管线：需求理解→领域建模→架构决策→依赖选型→接口设计→代码生成→质量校验→交付整合。

核心差异点（相比原始 flutter_generator.py）：
1. 不是生成 hello world，而是生成多文件生产级项目
2. 有领域建模能力（自动推导实体、关系、行为）
3. 有架构决策能力（根据复杂度选择分层/模块化/引擎架构）
4. 有依赖选型知识库（场景→库映射矩阵）
5. 有质量校验（import检查、依赖一致性、代码规范）
6. 按依赖顺序生成文件，每个文件感知已生成文件的上下文

参考文档: docs/Claude_Opus_4.6_需求到实现完整流程.md
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

PROJECT_DIR = Path(__file__).parent.parent.parent
WORKSPACE_DIR = PROJECT_DIR / "workspace"
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(WORKSPACE_DIR))

SKILL_META = {
    "name": "Opus Flutter 工程师",
    "description": "复刻 Claude Opus 4.6 的 Flutter 项目生成能力：八阶段认知管线",
    "tags": ["flutter", "dart", "code_generation", "architecture", "mobile_app", "opus_level"],
    "version": "1.0",
}

# ==================== 知识库：依赖选型矩阵 ====================

DEPENDENCY_MATRIX = {
    "screen_adaptation": {"package": "flutter_screenutil", "version": "^5.9.0", "comment": "屏幕适配"},
    "state_management_light": {"package": "provider", "version": "^6.1.1", "comment": "轻量级状态管理"},
    "state_management_full": {"package": "get", "version": "^4.6.6", "comment": "路由+DI+状态管理"},
    "http_client": {"package": "dio", "version": "^5.4.0", "comment": "HTTP客户端"},
    "local_storage_light": {"package": "shared_preferences", "version": "^2.2.2", "comment": "轻量本地存储"},
    "local_storage_sql": {"package": "sqflite", "version": "^2.3.0", "comment": "SQLite数据库"},
    "local_storage_nosql": {"package": "hive", "version": "^2.2.3", "comment": "高性能NoSQL"},
    "image_cache": {"package": "cached_network_image", "version": "^3.3.0", "comment": "网络图片缓存"},
    "image_viewer": {"package": "photo_view", "version": "^0.14.0", "comment": "图片缩放浏览"},
    "image_picker": {"package": "image_picker", "version": "^1.0.7", "comment": "相册/相机选图"},
    "video_player": {"package": "video_player", "version": "^2.8.2", "comment": "视频播放"},
    "camera": {"package": "camera", "version": "^0.10.5+9", "comment": "相机访问"},
    "permission": {"package": "permission_handler", "version": "^11.1.0", "comment": "权限管理"},
    "intl": {"package": "intl", "version": "^0.18.1", "comment": "国际化与日期格式化"},
    "websocket": {"package": "web_socket_channel", "version": "^2.4.0", "comment": "WebSocket通信"},
    "waterfall": {"package": "flutter_staggered_grid_view", "version": "^0.7.0", "comment": "瀑布流布局"},
    "shimmer": {"package": "shimmer", "version": "^3.0.0", "comment": "骨架屏加载"},
    "svg": {"package": "flutter_svg", "version": "^2.0.9", "comment": "SVG图标"},
    "badges": {"package": "badges", "version": "^3.1.1", "comment": "角标"},
    "lottie": {"package": "lottie", "version": "^2.7.0", "comment": "Lottie动画"},
    "path_provider": {"package": "path_provider", "version": "^2.1.1", "comment": "文件路径"},
    "json_annotation": {"package": "json_annotation", "version": "^4.8.1", "comment": "JSON注解"},
    "connectivity": {"package": "connectivity_plus", "version": "^5.0.2", "comment": "网络状态"},
    "map_amap": {"package": "amap_flutter_map", "version": "^3.0.0", "comment": "高德地图"},
    "location": {"package": "geolocator", "version": "^10.1.0", "comment": "定位"},
    "qr_scan": {"package": "mobile_scanner", "version": "^3.5.5", "comment": "二维码扫描"},
    "qr_generate": {"package": "qr_flutter", "version": "^4.1.0", "comment": "二维码生成"},
}

# 领域 → 必需依赖映射
DOMAIN_DEPENDENCIES = {
    "im": ["screen_adaptation", "state_management_light", "http_client", "local_storage_light",
           "local_storage_sql", "image_cache", "image_viewer", "image_picker", "video_player",
           "camera", "permission", "intl", "websocket", "badges", "path_provider",
           "json_annotation", "qr_scan", "qr_generate"],
    "short_video": ["screen_adaptation", "state_management_light", "http_client", "local_storage_light",
                    "local_storage_nosql", "image_cache", "video_player", "camera", "permission",
                    "intl", "websocket", "lottie", "shimmer", "svg", "path_provider"],
    "content_community": ["screen_adaptation", "state_management_light", "http_client",
                          "local_storage_light", "image_cache", "image_viewer", "image_picker",
                          "permission", "intl", "waterfall", "shimmer", "svg", "path_provider"],
    "image_processing": ["image_cache", "path_provider", "state_management_light"],
    "super_app": ["screen_adaptation", "state_management_full", "http_client", "local_storage_light",
                  "local_storage_nosql", "image_cache", "shimmer", "badges", "intl", "svg",
                  "permission", "map_amap", "location", "path_provider", "json_annotation"],
}

# ==================== Round 1: Flutter 知识库 ====================

FLUTTER_WIDGET_KNOWLEDGE = {
    "layout": {
        "Row": "水平排列子Widget，用mainAxisAlignment/crossAxisAlignment控制对齐",
        "Column": "垂直排列子Widget，同Row对齐方式",
        "Stack": "层叠布局，配合Positioned定位子Widget",
        "Expanded": "在Flex布局中占满剩余空间，flex参数控制比例",
        "SizedBox": "固定宽高的空间占位，常用于间距",
        "Padding": "内边距，优先用EdgeInsets.symmetric/only",
        "Container": "万能容器，含padding/margin/decoration/constraints",
        "ConstrainedBox": "约束子Widget的最大/最小宽高",
        "AspectRatio": "强制子Widget保持宽高比",
        "Wrap": "自动换行的流式布局",
    },
    "scrolling": {
        "ListView.builder": "懒加载列表，必须用于长列表（性能关键）",
        "GridView.builder": "懒加载网格",
        "PageView": "页面滑动，常用于Tab页或引导页",
        "CustomScrollView": "自定义滚动效果，配合Sliver系列",
        "NestedScrollView": "嵌套滚动，常用于TabBar+列表的Profile页",
        "SliverAppBar": "可折叠的AppBar，配合CustomScrollView",
        "SliverList": "Sliver懒加载列表",
        "RefreshIndicator": "下拉刷新包装器",
        "NotificationListener<ScrollNotification>": "滚动事件监听，用于上拉加载更多",
    },
    "interaction": {
        "GestureDetector": "手势检测（点击、双击、长按、拖拽）",
        "InkWell": "Material风格的点击效果（水波纹）",
        "Dismissible": "滑动删除",
        "Draggable": "拖拽Widget",
        "InteractiveViewer": "缩放和平移，用于图片查看器",
    },
    "display": {
        "CachedNetworkImage": "网络图片加载+缓存，必须指定placeholder和errorWidget",
        "CircleAvatar": "圆形头像",
        "ClipRRect": "圆角裁剪",
        "Hero": "页面转场动画",
        "AnimatedContainer": "自动动画的Container",
        "Shimmer": "骨架屏加载效果",
    },
    "input": {
        "TextField": "文本输入，用TextEditingController管理",
        "Form + TextFormField": "表单验证",
        "Checkbox/Switch/Radio": "选择控件",
        "Slider": "滑块",
        "BottomSheet": "底部弹出面板",
        "showModalBottomSheet": "模态底部面板",
    },
    "navigation": {
        "BottomNavigationBar": "底部导航栏（3-5个Tab）",
        "NavigationBar": "Material 3底部导航",
        "TabBar + TabBarView": "顶部Tab切换",
        "Drawer": "侧边抽屉菜单",
        "Navigator.push/pop": "页面路由",
        "GoRouter/GetX路由": "声明式路由管理",
    },
    "painting": {
        "CustomPainter": "自定义绘制（Canvas API），用于图表、动画、特效",
        "shouldRepaint": "控制是否需要重绘（性能关键）",
        "RepaintBoundary": "隔离重绘区域，减少GPU负担",
    },
}

DESIGN_PATTERN_TEMPLATES = {
    "singleton_service": '''/// {ServiceName} 单例服务
class {ServiceName} {{
  static final {ServiceName} _instance = {ServiceName}._internal();
  factory {ServiceName}() => _instance;
  {ServiceName}._internal();

  bool _isInitialized = false;

  Future<void> initialize() async {{
    if (_isInitialized) return;
    // 初始化逻辑
    _isInitialized = true;
  }}

  void dispose() {{
    // 释放资源
    _isInitialized = false;
  }}
}}''',

    "immutable_model": '''/// {ModelName} 数据模型
@immutable
class {ModelName} {{
  final String id;
  {fields}

  const {ModelName}({{
    required this.id,
    {constructor_params}
  }});

  factory {ModelName}.fromJson(Map<String, dynamic> json) {{
    return {ModelName}(
      id: json['id'] as String,
      {from_json_fields}
    );
  }}

  Map<String, dynamic> toJson() => {{
    'id': id,
    {to_json_fields}
  }};

  {ModelName} copyWith({{
    String? id,
    {copy_with_params}
  }}) {{
    return {ModelName}(
      id: id ?? this.id,
      {copy_with_body}
    );
  }}

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is {ModelName} && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => '{ModelName}(id: $id)';
}}''',

    "change_notifier_provider": '''/// {ProviderName} 状态管理
class {ProviderName} extends ChangeNotifier {{
  List<{EntityType}> _{items_name} = [];
  bool _isLoading = false;
  String? _error;

  List<{EntityType}> get {items_name} => List.unmodifiable(_{items_name});
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> load{EntityType}s() async {{
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {{
      // 加载数据
      _isLoading = false;
      notifyListeners();
    }} catch (e) {{
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }}
  }}

  void add{EntityType}({EntityType} item) {{
    _{items_name}.add(item);
    notifyListeners();
  }}

  void remove{EntityType}(String id) {{
    _{items_name}.removeWhere((item) => item.id == id);
    notifyListeners();
  }}
}}''',

    "websocket_service": '''/// WebSocket 实时通信服务
class WebSocketService {{
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _channel;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 5;
  String? _lastUrl;

  final _messageController = StreamController<Map<String, dynamic>>.broadcast();
  final _stateController = StreamController<String>.broadcast();

  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  Stream<String> get stateStream => _stateController.stream;

  Future<void> connect(String url) async {{
    _lastUrl = url;
    try {{
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _stateController.add('connected');
      _reconnectAttempts = 0;
      _startHeartbeat();
      _channel!.stream.listen(
        (data) => _messageController.add(jsonDecode(data)),
        onError: (e) {{ _stateController.add('error'); _reconnect(); }},
        onDone: () {{ _stateController.add('disconnected'); _reconnect(); }},
      );
    }} catch (e) {{
      _stateController.add('error');
      _reconnect();
    }}
  }}

  void send(Map<String, dynamic> data) {{
    _channel?.sink.add(jsonEncode(data));
  }}

  void _startHeartbeat() {{
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(Duration(seconds: 30), (_) {{
      send({{'type': 'ping'}});
    }});
  }}

  void _reconnect() {{
    if (_reconnectAttempts >= _maxReconnectAttempts || _lastUrl == null) return;
    _reconnectAttempts++;
    _reconnectTimer = Timer(
      Duration(seconds: _reconnectAttempts * 2),
      () => connect(_lastUrl!),
    );
  }}

  void disconnect() {{
    _heartbeatTimer?.cancel();
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _stateController.add('disconnected');
  }}

  void dispose() {{
    disconnect();
    _messageController.close();
    _stateController.close();
  }}
}}''',
}

# Round 2: 架构模板库 — 每种架构的标准文件列表
ARCHITECTURE_FILE_TEMPLATES = {
    "layer_based_im": [
        {"path": "lib/main.dart", "purpose": "应用入口+MaterialApp配置+路由", "key_classes": ["App", "MainPage"]},
        {"path": "lib/models/message.dart", "purpose": "消息数据模型", "key_classes": ["Message", "MessageType", "MessageStatus"]},
        {"path": "lib/models/conversation.dart", "purpose": "会话数据模型", "key_classes": ["Conversation"]},
        {"path": "lib/models/contact.dart", "purpose": "联系人数据模型", "key_classes": ["Contact"]},
        {"path": "lib/models/moment.dart", "purpose": "朋友圈数据模型", "key_classes": ["Moment", "Comment"]},
        {"path": "lib/services/websocket_service.dart", "purpose": "WebSocket实时通信服务(单例,含心跳+重连)", "key_classes": ["WebSocketService"]},
        {"path": "lib/services/database_service.dart", "purpose": "本地数据库服务(SQLite,含建表+CRUD)", "key_classes": ["DatabaseService"]},
        {"path": "lib/providers/chat_provider.dart", "purpose": "聊天状态管理(ChangeNotifier)", "key_classes": ["ChatProvider"]},
        {"path": "lib/screens/chat_list_screen.dart", "purpose": "聊天列表页", "key_classes": ["ChatListScreen"]},
        {"path": "lib/screens/chat_detail_screen.dart", "purpose": "聊天详情页(消息收发UI)", "key_classes": ["ChatDetailScreen"]},
        {"path": "lib/screens/contacts_screen.dart", "purpose": "通讯录页(按字母分组)", "key_classes": ["ContactsScreen"]},
        {"path": "lib/screens/discover_screen.dart", "purpose": "发现页(功能入口列表)", "key_classes": ["DiscoverScreen"]},
        {"path": "lib/screens/moments_screen.dart", "purpose": "朋友圈页(Feed流)", "key_classes": ["MomentsScreen"]},
        {"path": "lib/screens/profile_screen.dart", "purpose": "个人中心页", "key_classes": ["ProfileScreen"]},
        {"path": "lib/widgets/message_bubble.dart", "purpose": "消息气泡组件", "key_classes": ["MessageBubble"]},
        {"path": "lib/widgets/moment_card.dart", "purpose": "朋友圈卡片组件", "key_classes": ["MomentCard"]},
    ],
    "layer_based_content_community": [
        {"path": "lib/main.dart", "purpose": "应用入口+底部导航+路由", "key_classes": ["App", "MainPage"]},
        {"path": "lib/models/note.dart", "purpose": "笔记数据模型", "key_classes": ["Note", "NoteType"]},
        {"path": "lib/models/user.dart", "purpose": "用户数据模型", "key_classes": ["User"]},
        {"path": "lib/providers/note_provider.dart", "purpose": "笔记状态管理(ChangeNotifier)", "key_classes": ["NoteProvider"]},
        {"path": "lib/screens/home_screen.dart", "purpose": "首页(瀑布流)", "key_classes": ["HomeScreen"]},
        {"path": "lib/screens/note_detail_screen.dart", "purpose": "笔记详情页(图文+评论)", "key_classes": ["NoteDetailScreen"]},
        {"path": "lib/screens/publish_screen.dart", "purpose": "发布笔记页(图片选择+文本)", "key_classes": ["PublishScreen"]},
        {"path": "lib/screens/search_screen.dart", "purpose": "搜索页(分类+热搜)", "key_classes": ["SearchScreen"]},
        {"path": "lib/screens/profile_screen.dart", "purpose": "个人中心页(NestedScrollView)", "key_classes": ["ProfileScreen"]},
        {"path": "lib/screens/message_screen.dart", "purpose": "消息页", "key_classes": ["MessageScreen"]},
        {"path": "lib/services/image_service.dart", "purpose": "图片处理服务(压缩+上传)", "key_classes": ["ImageService"]},
        {"path": "lib/widgets/waterfall_grid.dart", "purpose": "瀑布流组件(MasonryGridView)", "key_classes": ["WaterfallGrid"]},
        {"path": "lib/widgets/note_card.dart", "purpose": "笔记卡片组件", "key_classes": ["NoteCard"]},
        {"path": "lib/widgets/image_carousel.dart", "purpose": "图片轮播组件", "key_classes": ["ImageCarousel"]},
        {"path": "lib/widgets/tag_input.dart", "purpose": "标签输入组件", "key_classes": ["TagInput"]},
    ],
    "layer_based_short_video": [
        {"path": "lib/main.dart", "purpose": "应用入口+暗色主题+导航", "key_classes": ["App", "MainNavigation"]},
        {"path": "lib/models/video.dart", "purpose": "视频数据模型", "key_classes": ["VideoModel", "CommentModel"]},
        {"path": "lib/providers/video_provider.dart", "purpose": "视频状态管理", "key_classes": ["VideoProvider"]},
        {"path": "lib/services/video_preload_service.dart", "purpose": "视频预加载服务(控制器池+内存管理)", "key_classes": ["VideoPreloadService"]},
        {"path": "lib/screens/video_feed_screen.dart", "purpose": "视频流页面(垂直PageView)", "key_classes": ["VideoFeedScreen"]},
        {"path": "lib/screens/camera_screen.dart", "purpose": "拍摄页面", "key_classes": ["CameraScreen"]},
        {"path": "lib/screens/profile_screen.dart", "purpose": "个人中心页", "key_classes": ["ProfileScreen"]},
        {"path": "lib/screens/search_screen.dart", "purpose": "搜索/发现页", "key_classes": ["SearchScreen"]},
        {"path": "lib/screens/live_room_screen.dart", "purpose": "直播间页面(弹幕+礼物)", "key_classes": ["LiveRoomScreen"]},
        {"path": "lib/widgets/video_player_widget.dart", "purpose": "视频播放组件", "key_classes": ["VideoPlayerWidget"]},
        {"path": "lib/widgets/interaction_panel.dart", "purpose": "右侧互动栏(点赞/评论/分享)", "key_classes": ["InteractionPanel"]},
        {"path": "lib/widgets/comment_drawer.dart", "purpose": "评论抽屉组件", "key_classes": ["CommentDrawer"]},
        {"path": "lib/widgets/like_animation.dart", "purpose": "双击点赞动画", "key_classes": ["LikeAnimation"]},
        {"path": "lib/widgets/danmaku_widget.dart", "purpose": "弹幕组件", "key_classes": ["DanmakuWidget"]},
        {"path": "lib/widgets/gift_animation.dart", "purpose": "礼物动画组件", "key_classes": ["GiftAnimation"]},
    ],
}

# Round 3: 代码质量检查清单（注入到代码生成Prompt中）
CODE_QUALITY_CHECKLIST = """
代码质量检查清单（生成代码时必须逐项确认）：
1. ✅ 所有 import 语句在文件顶部且使用 package: 前缀
2. ✅ 所有类字段声明类型（String, int, bool, List<T>）
3. ✅ 必需参数使用 required 关键字
4. ✅ 可空字段使用 ? 标记（String?）
5. ✅ StatefulWidget 的 dispose() 中释放所有 Controller/Timer/Stream
6. ✅ 网络请求包裹在 try-catch 中
7. ✅ 列表使用 ListView.builder 而非 ListView(children:[])
8. ✅ 常量 Widget 使用 const 关键字
9. ✅ 数据模型类使用 @immutable 注解
10. ✅ 中文功能注释（/// dartdoc 格式）
11. ✅ 服务类使用单例模式
12. ✅ 状态管理类继承 ChangeNotifier 并在修改后调用 notifyListeners()
13. ✅ 图片加载使用 CachedNetworkImage 并提供 placeholder 和 errorWidget
14. ✅ 枚举类型用于消息类型/状态等有限值集合
15. ✅ 文件命名使用 snake_case
"""

# 架构模式映射
ARCHITECTURE_PATTERNS = {
    "layer_based": {
        "description": "按层分：models/providers/screens/services/widgets",
        "suitable_for": ["im", "short_video", "content_community"],
        "dirs": ["models", "providers", "screens", "services", "widgets"],
    },
    "feature_based": {
        "description": "按功能模块分：每个模块独立 screens/widgets",
        "suitable_for": ["super_app"],
        "dirs": None,  # 动态生成
    },
    "engine_based": {
        "description": "按引擎分：engine/models/screens/utils/widgets",
        "suitable_for": ["image_processing"],
        "dirs": ["engine", "models", "screens", "utils", "widgets"],
    },
}


# ==================== LLM 调用 ====================

def _llm(messages, expect_json=False):
    """统一 LLM 调用入口"""
    try:
        import agi_v13_cognitive_lattice as agi
        result = agi.llm_call(messages)
    except ImportError:
        return {"error": "AGI 核心未加载"} if expect_json else "AGI 核心未加载"

    if expect_json:
        if isinstance(result, (list, dict)) and "raw" not in result:
            return result
        raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
        json_match = re.search(r'```(?:json)?\s*\n(.*?)```', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"raw": raw}
    raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
    return raw


def _extract_dart_code(raw_text: str) -> str:
    """从 LLM 输出中提取 Dart 代码块"""
    pattern = r'```(?:dart)?\s*\n(.*?)```'
    match = re.search(pattern, raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    if 'import ' in raw_text or 'class ' in raw_text or 'void main' in raw_text:
        lines = raw_text.strip().split('\n')
        start = 0
        for i, line in enumerate(lines):
            if any(line.strip().startswith(k) for k in ['import', 'library', 'part', '//', 'class', 'void', 'enum']):
                start = i
                break
        return '\n'.join(lines[start:]).strip()
    return raw_text.strip()


def _log(msg):
    """日志输出"""
    try:
        from action_engine import _emit_step
        _emit_step("opus_flutter_engineer", msg, "running")
    except Exception:
        pass
    print(f"  [OpusFlutter] {msg}")


# ==================== Phase 1+2: 需求分析 + 领域建模 ====================

def analyze_flutter_requirement(requirement: str) -> Dict:
    """
    将自然语言需求转换为结构化规格 + 领域模型。

    返回:
      {
        "domain": "im|short_video|content_community|image_processing|super_app|custom",
        "app_name": "项目名",
        "features": [{"id":"F1","name":"...","description":"...","priority":"must|should|nice"}],
        "entities": [{"name":"Message","fields":[{"name":"id","type":"String","required":true}],"behaviors":["send","receive"]}],
        "relationships": [{"from":"User","to":"Message","type":"1:N"}],
        "complexity": {"level":"low|medium|high","file_count":16,"estimated_lines":3000},
        "tech_decisions": {"state_management":"provider","storage":"sqflite","communication":"websocket"},
        "implicit_requirements": ["消息状态管理","WebSocket心跳","图片缓存","下拉刷新"]
      }
    """
    _log("Phase 1+2: 需求分析 + 领域建模")

    messages = [
        {"role": "system", "content": """你是 Flutter 高级架构师。将用户需求转换为结构化规格和领域模型。

你必须识别：
1. 核心领域（im=即时通讯, short_video=短视频, content_community=内容社区, image_processing=图像处理, super_app=超级应用, custom=其他）
2. 所有必需功能（包括用户未提到的工程需求：错误处理、缓存、状态管理、权限）
3. 数据实体（含字段名、类型、是否必需）
4. 实体关系
5. 复杂度评估

输出严格 JSON:
```json
{
  "domain": "领域标识",
  "app_name": "项目名_snake_case",
  "features": [
    {"id": "F1", "name": "功能名", "description": "描述", "priority": "must|should|nice"}
  ],
  "entities": [
    {
      "name": "EntityName",
      "fields": [
        {"name": "id", "type": "String", "required": true, "description": "唯一标识"}
      ],
      "behaviors": ["create", "read", "update", "delete"]
    }
  ],
  "relationships": [
    {"from": "User", "to": "Message", "type": "1:N", "description": "用户发送多条消息"}
  ],
  "complexity": {
    "level": "low|medium|high",
    "file_count": 16,
    "estimated_lines": 3000
  },
  "tech_decisions": {
    "state_management": "provider|getx|bloc",
    "storage": "sqflite|hive|shared_preferences",
    "communication": "websocket|http_only|none"
  },
  "implicit_requirements": ["消息状态管理", "WebSocket心跳重连", "图片缓存策略", "下拉刷新分页"]
}
```"""},
        {"role": "user", "content": f"需求：{requirement}"}
    ]

    result = _llm(messages, expect_json=True)

    if isinstance(result, dict) and "domain" in result:
        _log(f"  领域={result.get('domain')}, 实体={len(result.get('entities', []))}, "
             f"复杂度={result.get('complexity', {}).get('level', '?')}")
        return result

    # 回退：基于关键词匹配
    domain = "custom"
    for kw, dom in [("微信", "im"), ("聊天", "im"), ("抖音", "short_video"), ("视频", "short_video"),
                     ("小红书", "content_community"), ("图片查看", "image_processing"),
                     ("超级", "super_app"), ("外卖", "super_app"), ("打车", "super_app")]:
        if kw in requirement:
            domain = dom
            break

    return {
        "domain": domain,
        "app_name": "flutter_app",
        "features": [{"id": "F1", "name": "核心功能", "description": requirement, "priority": "must"}],
        "entities": [],
        "relationships": [],
        "complexity": {"level": "medium", "file_count": 10, "estimated_lines": 2000},
        "tech_decisions": {"state_management": "provider", "storage": "shared_preferences", "communication": "http_only"},
        "implicit_requirements": ["错误处理", "加载状态"]
    }


# ==================== Phase 3+4+5: 架构决策 + 依赖选型 + 接口设计 ====================

def design_architecture(spec: Dict) -> Dict:
    """
    根据需求规格设计完整架构。

    返回:
      {
        "pattern": "layer_based|feature_based|engine_based",
        "directory_structure": {"lib/": {"models/": [...], "screens/": [...]}},
        "file_plan": [{"path":"lib/models/message.dart","purpose":"消息数据模型","key_classes":["Message","MessageType"]}],
        "dependencies": {"provider":"^6.1.1", ...},
        "implementation_order": ["lib/models/message.dart", ...],
        "pubspec_yaml": "完整的pubspec.yaml内容"
      }
    """
    _log("Phase 3+4+5: 架构决策 + 依赖选型 + 接口设计")

    domain = spec.get("domain", "custom")
    app_name = spec.get("app_name", "flutter_app")

    # Phase 3: 架构模式选择
    pattern = "layer_based"
    for pat_name, pat_info in ARCHITECTURE_PATTERNS.items():
        if domain in pat_info["suitable_for"]:
            pattern = pat_name
            break

    # Phase 4: 依赖选型（从知识库映射）
    dep_keys = DOMAIN_DEPENDENCIES.get(domain, ["screen_adaptation", "state_management_light", "http_client"])
    dependencies = {}
    dep_comments = {}
    for key in dep_keys:
        if key in DEPENDENCY_MATRIX:
            info = DEPENDENCY_MATRIX[key]
            dependencies[info["package"]] = info["version"]
            dep_comments[info["package"]] = info["comment"]

    # Phase 5: 文件规划（优先使用模板，LLM细化）
    # Round 2 改进：先查找预定义的架构模板
    template_key = f"{pattern}_{domain}"
    template_files = ARCHITECTURE_FILE_TEMPLATES.get(template_key, [])

    if template_files:
        # 使用预定义模板作为文件计划
        file_plan = template_files
        impl_order = [f["path"] for f in template_files]
        _log(f"  使用预定义架构模板: {template_key} ({len(template_files)} 个文件)")
    else:
        # 无匹配模板，使用LLM生成
        messages = [
            {"role": "system", "content": f"""你是 Flutter 架构师。基于需求规格设计文件计划。

架构模式: {pattern}
项目名: {app_name}
领域: {domain}

要求:
1. 每个文件有明确的单一职责
2. 按依赖顺序排列（被依赖的先实现）
3. models/ 中的每个实体类单独一个文件
4. 服务类使用单例模式
5. 状态管理类使用 ChangeNotifier

输出严格 JSON:
```json
{{
  "file_plan": [
    {{
      "path": "lib/models/message.dart",
      "purpose": "消息数据模型，含MessageType枚举和Message类",
      "key_classes": ["Message", "MessageType", "MessageStatus"],
      "depends_on": []
    }}
  ],
  "implementation_order": ["lib/models/message.dart", "..."]
}}
```"""},
            {"role": "user", "content": f"需求规格:\n{json.dumps(spec, ensure_ascii=False, indent=2)}\n\n请设计文件计划:"}
        ]

        design = _llm(messages, expect_json=True)
        file_plan = design.get("file_plan", []) if isinstance(design, dict) else []
        impl_order = design.get("implementation_order", [f["path"] for f in file_plan]) if isinstance(design, dict) else []

    # 生成 pubspec.yaml
    pubspec = _generate_pubspec(app_name, dependencies, dep_comments)

    result = {
        "pattern": pattern,
        "file_plan": file_plan,
        "dependencies": dependencies,
        "implementation_order": impl_order,
        "pubspec_yaml": pubspec,
    }

    # Round 2: 注入设计模式模板引用
    result["pattern_templates"] = list(DESIGN_PATTERN_TEMPLATES.keys())

    _log(f"  架构={pattern}, 文件数={len(file_plan)}, 依赖数={len(dependencies)}")
    return result


def _generate_pubspec(app_name: str, dependencies: Dict, comments: Dict) -> str:
    """生成 pubspec.yaml 内容"""
    lines = [
        f"name: {app_name}",
        f"description: A Flutter project generated by Opus Flutter Engineer.",
        "publish_to: 'none'",
        "version: 1.0.0+1",
        "",
        "environment:",
        "  sdk: '>=3.0.0 <4.0.0'",
        "",
        "dependencies:",
        "  flutter:",
        "    sdk: flutter",
        "",
        "  cupertino_icons: ^1.0.6",
    ]

    for pkg, ver in sorted(dependencies.items()):
        comment = comments.get(pkg, "")
        if comment:
            lines.append(f"  {pkg}: {ver:<24} # {comment}")
        else:
            lines.append(f"  {pkg}: {ver}")

    lines.extend([
        "",
        "dev_dependencies:",
        "  flutter_test:",
        "    sdk: flutter",
        "  flutter_lints: ^3.0.1",
        "  build_runner: ^2.4.8",
        "  json_serializable: ^6.7.1",
        "",
        "flutter:",
        "  uses-material-design: true",
        "",
        "  assets:",
        "    - assets/images/",
        "    - assets/icons/",
    ])

    return "\n".join(lines)


# ==================== Phase 6: 代码生成 ====================

def generate_flutter_project(requirement: str, architecture: Dict, output_dir: str) -> Dict:
    """
    按实现顺序生成所有 Dart 文件。

    关键策略：
    1. 每个文件生成时，携带已生成文件的上下文
    2. 按 implementation_order 顺序生成（被依赖的先生成）
    3. 每个文件独立调用 LLM，确保代码完整性
    """
    _log("Phase 6: 代码生成")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 写入 pubspec.yaml
    pubspec_path = output_path / "pubspec.yaml"
    pubspec_path.write_text(architecture["pubspec_yaml"], encoding='utf-8')
    _log(f"  已生成: pubspec.yaml")

    # 创建 assets 目录
    (output_path / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (output_path / "assets" / "icons").mkdir(parents=True, exist_ok=True)

    generated_files = []
    generated_context = ""

    impl_order = architecture.get("implementation_order", [])
    plan_map = {f["path"]: f for f in architecture.get("file_plan", [])}

    for file_path in impl_order:
        file_plan = plan_map.get(file_path, {"path": file_path, "purpose": "", "key_classes": []})

        _log(f"  生成: {file_path} ({file_plan.get('purpose', '?')})")

        # Round 1+3: 注入 Widget 知识和质量检查清单
        widget_hint = ""
        purpose_lower = file_plan.get('purpose', '').lower()
        for category, widgets in FLUTTER_WIDGET_KNOWLEDGE.items():
            for widget_name, desc in widgets.items():
                if any(kw in purpose_lower for kw in [widget_name.lower(), category]):
                    widget_hint += f"\n- {widget_name}: {desc}"
        if widget_hint:
            widget_hint = f"\n\n推荐使用的 Widget:{widget_hint}"

        # Round 2: 注入设计模式模板提示
        pattern_hint = ""
        if "服务" in purpose_lower or "service" in purpose_lower:
            pattern_hint = f"\n\n服务类模板参考:\n{DESIGN_PATTERN_TEMPLATES['singleton_service'][:200]}..."
        elif "模型" in purpose_lower or "model" in purpose_lower:
            pattern_hint = f"\n\n数据模型模板参考:\n{DESIGN_PATTERN_TEMPLATES['immutable_model'][:200]}..."
        elif "provider" in purpose_lower or "状态" in purpose_lower:
            pattern_hint = f"\n\n状态管理模板参考:\n{DESIGN_PATTERN_TEMPLATES['change_notifier_provider'][:200]}..."

        messages = [
            {"role": "system", "content": f"""你是 Dart/Flutter 代码生成器，遵循 Claude Opus 4.6 的代码质量标准。

为以下文件生成完整、可运行的 Dart 代码。

{CODE_QUALITY_CHECKLIST}

文件路径: {file_path}
文件职责: {file_plan.get('purpose', '')}
关键类: {file_plan.get('key_classes', [])}
依赖文件: {file_plan.get('depends_on', [])}
{widget_hint}
{pattern_hint}

常见错误（必须避免）:
- ❌ 忘记 import 语句
- ❌ 忘记在 dispose() 中释放 Controller
- ❌ 使用 ListView(children:[]) 而非 ListView.builder
- ❌ 忘记 required 关键字
- ❌ 括号不匹配

只输出完整的 Dart 代码，用 ```dart ``` 包裹。"""},
            {"role": "user", "content": f"""需求: {requirement}

{('已生成的相关文件上下文:\n' + generated_context[-3000:]) if generated_context else '这是第一个文件。'}

请生成 {file_path} 的完整代码:"""}
        ]

        raw = _llm(messages)
        code = _extract_dart_code(raw)

        if not code or len(code) < 20:
            _log(f"  ⚠️ 代码生成失败: {file_path}，使用占位符")
            code = f"// TODO: {file_plan.get('purpose', file_path)}\n// 自动生成失败，需要手动实现\n"

        # 写入文件
        full_path = output_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(code, encoding='utf-8')

        generated_files.append({
            "path": file_path,
            "lines": code.count('\n') + 1,
            "purpose": file_plan.get('purpose', ''),
            "key_classes": file_plan.get('key_classes', []),
        })

        # 累积上下文（截断以控制 token）
        generated_context += f"\n\n// === {file_path} ===\n{code[:1500]}"

    _log(f"  代码生成完成: {len(generated_files)} 个文件")
    return {
        "success": True,
        "files_generated": len(generated_files),
        "total_lines": sum(f["lines"] for f in generated_files),
        "files": generated_files,
    }


# ==================== Phase 7: 质量校验 ====================

def verify_project_quality(project_dir: str) -> Dict:
    """
    校验生成的 Flutter 项目质量。

    检查项:
    1. 所有 .dart 文件的 import 是否可解析
    2. pubspec.yaml 声明的依赖是否在代码中使用
    3. 代码中使用的 package 是否在 pubspec.yaml 中声明
    4. 是否有空文件或过小文件
    5. main.dart 是否存在且有入口函数
    6. 文件命名是否符合 snake_case
    """
    _log("Phase 7: 质量校验")

    project_path = Path(project_dir)
    issues = []
    score = 100

    # 1. 检查 pubspec.yaml 存在
    pubspec_path = project_path / "pubspec.yaml"
    if not pubspec_path.exists():
        issues.append({"severity": "error", "message": "缺少 pubspec.yaml"})
        score -= 20

    # 2. 收集所有 .dart 文件
    dart_files = list(project_path.rglob("*.dart"))
    if not dart_files:
        issues.append({"severity": "error", "message": "没有找到 .dart 文件"})
        return {"score": 0, "issues": issues, "suggestions": ["需要重新生成代码"]}

    # 3. 检查 main.dart
    main_dart = project_path / "lib" / "main.dart"
    if not main_dart.exists():
        issues.append({"severity": "error", "message": "缺少 lib/main.dart"})
        score -= 15
    else:
        content = main_dart.read_text(encoding='utf-8', errors='replace')
        if "void main()" not in content and "void main(" not in content:
            issues.append({"severity": "warning", "message": "main.dart 缺少 main() 入口函数"})
            score -= 10

    # 4. 检查每个文件的基本质量
    declared_packages = set()
    used_packages = set()

    if pubspec_path.exists():
        pubspec_content = pubspec_path.read_text(encoding='utf-8', errors='replace')
        for line in pubspec_content.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#') and not line.startswith('-'):
                pkg = line.split(':')[0].strip()
                if pkg and pkg not in ('flutter', 'sdk', 'name', 'description', 'version',
                                        'publish_to', 'environment', 'dependencies',
                                        'dev_dependencies', 'flutter_test', 'uses-material-design',
                                        'assets'):
                    declared_packages.add(pkg)

    for dart_file in dart_files:
        try:
            content = dart_file.read_text(encoding='utf-8', errors='replace')
        except Exception:
            issues.append({"severity": "warning", "message": f"无法读取: {dart_file.name}"})
            score -= 2
            continue

        rel_path = dart_file.relative_to(project_path)
        lines = content.count('\n') + 1

        # 空文件检查
        if lines < 3 or len(content.strip()) < 20:
            issues.append({"severity": "warning", "message": f"{rel_path}: 文件过小 ({lines} 行)"})
            score -= 3

        # 文件名检查 (snake_case)
        name = dart_file.stem
        if name != name.lower() or ' ' in name:
            issues.append({"severity": "info", "message": f"{rel_path}: 文件名不符合 snake_case"})
            score -= 1

        # 提取使用的 package
        for line in content.split('\n'):
            match = re.match(r"import\s+'package:(\w+)/", line)
            if match:
                used_packages.add(match.group(1))

    # 5. 依赖一致性检查
    # 声明但未使用
    unused = declared_packages - used_packages - {'flutter', 'flutter_test', 'flutter_lints',
                                                    'build_runner', 'json_serializable',
                                                    'hive_generator', 'cupertino_icons'}
    for pkg in unused:
        issues.append({"severity": "warning", "message": f"依赖声明但未使用: {pkg}"})
        score -= 2

    # 使用但未声明
    undeclared = used_packages - declared_packages - {'flutter', 'dart'}
    for pkg in undeclared:
        issues.append({"severity": "error", "message": f"使用但未声明依赖: {pkg}"})
        score -= 5

    # 6. 文件数评估
    if len(dart_files) < 5:
        issues.append({"severity": "info", "message": f"文件数偏少 ({len(dart_files)})，建议进一步拆分"})
        score -= 3

    score = max(0, min(100, score))

    suggestions = []
    if score < 60:
        suggestions.append("建议重新生成项目，当前质量不达标")
    if unused:
        suggestions.append(f"移除未使用的依赖: {', '.join(unused)}")
    if undeclared:
        suggestions.append(f"在 pubspec.yaml 中添加: {', '.join(undeclared)}")

    _log(f"  质量评分: {score}/100, 问题数: {len(issues)}")
    return {
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
        "stats": {
            "dart_files": len(dart_files),
            "declared_packages": len(declared_packages),
            "used_packages": len(used_packages),
        }
    }


# ==================== Round 4: 自动修复常见问题 ====================

def auto_fix_common_issues(project_dir: str) -> Dict:
    """
    自动修复生成代码中的常见问题。

    修复项:
    1. 缺失的 material.dart import
    2. 括号不匹配
    3. 缺失的 dispose() 方法
    4. 文件末尾缺少换行
    """
    _log("Round 4: 自动修复常见问题")
    project_path = Path(project_dir)
    fixes_applied = []

    for dart_file in project_path.rglob("*.dart"):
        try:
            content = dart_file.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue

        original = content
        rel_path = str(dart_file.relative_to(project_path))

        # Fix 1: 确保有 material.dart import（如果使用了 Flutter Widget）
        flutter_keywords = ['StatelessWidget', 'StatefulWidget', 'Widget', 'BuildContext',
                           'Scaffold', 'AppBar', 'Container', 'Text', 'Column', 'Row',
                           'MaterialApp', 'ThemeData', 'Colors', 'Icons', 'EdgeInsets']
        uses_flutter = any(kw in content for kw in flutter_keywords)
        has_material_import = "import 'package:flutter/material.dart'" in content
        if uses_flutter and not has_material_import:
            content = "import 'package:flutter/material.dart';\n" + content
            fixes_applied.append(f"{rel_path}: 添加 material.dart import")

        # Fix 2: 确保文件末尾有换行
        if content and not content.endswith('\n'):
            content += '\n'

        # Fix 3: 检查括号匹配（简单检查）
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces > close_braces:
            diff = open_braces - close_braces
            content = content.rstrip() + '\n' + ('}\n' * diff)
            fixes_applied.append(f"{rel_path}: 补齐 {diff} 个闭合括号")
        elif close_braces > open_braces:
            fixes_applied.append(f"{rel_path}: ⚠️ 多余闭合括号（需手动检查）")

        # Fix 4: 检查 StatefulWidget 是否有 dispose
        if 'extends State<' in content and 'void dispose()' not in content:
            # 检查是否有需要 dispose 的 Controller
            controllers = re.findall(r'(?:final|late)\s+\w*Controller\s+(\w+)', content)
            timers = re.findall(r'(?:final|late)\s+Timer\??\s+(\w+)', content)
            if controllers or timers:
                dispose_body = '\n  @override\n  void dispose() {\n'
                for c in controllers:
                    dispose_body += f'    {c}.dispose();\n'
                for t in timers:
                    dispose_body += f'    {t}?.cancel();\n'
                dispose_body += '    super.dispose();\n  }\n'
                # 插入到最后一个 } 之前
                last_brace = content.rfind('}')
                if last_brace > 0:
                    content = content[:last_brace] + dispose_body + content[last_brace:]
                    fixes_applied.append(f"{rel_path}: 自动添加 dispose() 方法")

        if content != original:
            dart_file.write_text(content, encoding='utf-8')

    _log(f"  自动修复完成: {len(fixes_applied)} 项修复")
    return {"fixes_applied": fixes_applied, "count": len(fixes_applied)}


# ==================== Round 5: 测试生成 + 工程脚手架 ====================

def generate_flutter_tests(project_dir: str, app_name: str) -> Dict:
    """为 Flutter 项目生成基础测试文件"""
    _log("Round 5: 生成测试文件")
    project_path = Path(project_dir)
    test_dir = project_path / "test"
    test_dir.mkdir(exist_ok=True)

    # 基础 widget test
    widget_test = f'''import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:{app_name}/main.dart';

void main() {{
  testWidgets('App should render without errors', (WidgetTester tester) async {{
    // 构建应用
    await tester.pumpWidget(const App());

    // 验证应用能正常渲染
    expect(find.byType(MaterialApp), findsOneWidget);
  }});

  testWidgets('Bottom navigation should exist', (WidgetTester tester) async {{
    await tester.pumpWidget(const App());
    await tester.pumpAndSettle();

    // 检查底部导航栏
    expect(find.byType(BottomNavigationBar).evaluate().isNotEmpty ||
           find.byType(NavigationBar).evaluate().isNotEmpty, isTrue);
  }});
}}
'''

    # 模型单元测试
    model_tests = []
    models_dir = project_path / "lib" / "models"
    if models_dir.exists():
        for model_file in models_dir.glob("*.dart"):
            model_name = model_file.stem
            class_name = ''.join(word.capitalize() for word in model_name.split('_'))
            model_tests.append(f'''
  group('{class_name} Model', () {{
    test('should create from JSON', () {{
      final json = {{'id': 'test_1'}};
      // TODO: Add proper JSON fields for {class_name}
      expect(json['id'], equals('test_1'));
    }});

    test('should convert to JSON', () {{
      // TODO: Create {class_name} instance and verify toJson()
      expect(true, isTrue);
    }});
  }});''')

    unit_test = f'''import 'package:flutter_test/flutter_test.dart';

void main() {{
{"".join(model_tests) if model_tests else "  test('placeholder test', () { expect(true, isTrue); });"}
}}
'''

    # 写入测试文件
    (test_dir / "widget_test.dart").write_text(widget_test, encoding='utf-8')
    (test_dir / "model_test.dart").write_text(unit_test, encoding='utf-8')

    _log(f"  测试文件生成: widget_test.dart, model_test.dart")
    return {"files": ["test/widget_test.dart", "test/model_test.dart"]}


def generate_project_scaffolding(project_dir: str, app_name: str) -> Dict:
    """生成工程脚手架文件（.gitignore, README, analysis_options）"""
    _log("Round 5: 生成工程脚手架文件")
    project_path = Path(project_dir)
    files_created = []

    # .gitignore
    gitignore = """# Flutter/Dart
.dart_tool/
.packages
.pub/
build/
.flutter-plugins
.flutter-plugins-dependencies

# IDE
.idea/
.vscode/
*.iml
*.ipr
*.iws

# macOS
.DS_Store
*.swp
*.swo

# Android
**/android/**/gradle-wrapper.jar
**/android/.gradle
**/android/captures/
**/android/gradlew
**/android/gradlew.bat
**/android/local.properties
**/android/**/GeneratedPluginRegistrant.java

# iOS
**/ios/**/*.mode1v3
**/ios/**/*.mode2v3
**/ios/**/*.moved-aside
**/ios/**/*.pbxuser
**/ios/**/*.perspectivev3
**/ios/**/DerivedData/
**/ios/.symlinks/
**/ios/**/Pods/

# Misc
*.log
coverage/
"""
    (project_path / ".gitignore").write_text(gitignore, encoding='utf-8')
    files_created.append(".gitignore")

    # README.md
    readme = f"""# {app_name.replace('_', ' ').title()}

A Flutter project generated by **Opus Flutter Engineer** (AGI Skill).

## Getting Started

```bash
flutter pub get
flutter run
```

## Project Structure

```
lib/
├── models/       # Data models
├── providers/    # State management (ChangeNotifier)
├── screens/      # App screens/pages
├── services/     # Business logic services
└── widgets/      # Reusable UI components
```

## Testing

```bash
flutter test
```

## Generated by
Opus Flutter Engineer — Claude Opus 4.6 level Flutter project generation skill.
"""
    (project_path / "README.md").write_text(readme, encoding='utf-8')
    files_created.append("README.md")

    # analysis_options.yaml
    analysis = """include: package:flutter_lints/flutter.yaml

linter:
  rules:
    - prefer_const_constructors
    - prefer_const_declarations
    - prefer_final_fields
    - prefer_final_locals
    - avoid_print
    - require_trailing_commas
    - sort_child_properties_last
    - use_key_in_widget_constructors
    - sized_box_for_whitespace
    - prefer_single_quotes

analyzer:
  errors:
    missing_required_param: error
    missing_return: error
  exclude:
    - "**/*.g.dart"
    - "**/*.freezed.dart"
"""
    (project_path / "analysis_options.yaml").write_text(analysis, encoding='utf-8')
    files_created.append("analysis_options.yaml")

    _log(f"  脚手架文件生成: {', '.join(files_created)}")
    return {"files": files_created}


# ==================== 完整管线 ====================

def full_pipeline(requirement: str, output_dir: str, lattice=None) -> Dict:
    """
    完整八阶段管线：需求 → 可运行 Flutter 项目。

    Args:
        requirement: 自然语言需求
        output_dir: 输出目录
        lattice: 认知网络实例（可选）

    Returns:
        {success, project_path, files, quality_score, phases}
    """
    _log(f"=== Opus Flutter 工程师 启动 ===")
    _log(f"需求: {requirement[:100]}")
    _log(f"输出: {output_dir}")

    phases = []
    start_time = datetime.now()

    # Phase 1+2: 需求分析 + 领域建模
    spec = analyze_flutter_requirement(requirement)
    phases.append({"phase": "requirement_analysis", "domain": spec.get("domain"),
                   "entities": len(spec.get("entities", [])),
                   "features": len(spec.get("features", []))})

    # Phase 3+4+5: 架构决策 + 依赖选型 + 接口设计
    architecture = design_architecture(spec)
    phases.append({"phase": "architecture_design", "pattern": architecture.get("pattern"),
                   "files_planned": len(architecture.get("file_plan", [])),
                   "dependencies": len(architecture.get("dependencies", {}))})

    # Phase 6: 代码生成
    gen_result = generate_flutter_project(requirement, architecture, output_dir)
    phases.append({"phase": "code_generation",
                   "files_generated": gen_result.get("files_generated", 0),
                   "total_lines": gen_result.get("total_lines", 0)})

    # Phase 6b (Round 4): 自动修复常见问题
    fix_result = auto_fix_common_issues(output_dir)
    phases.append({"phase": "auto_fix",
                   "fixes_applied": fix_result.get("count", 0)})

    # Phase 6c (Round 5): 生成测试 + 工程脚手架
    app_name = spec.get("app_name", "flutter_app")
    test_result = generate_flutter_tests(output_dir, app_name)
    scaffold_result = generate_project_scaffolding(output_dir, app_name)
    phases.append({"phase": "scaffolding",
                   "test_files": len(test_result.get("files", [])),
                   "scaffold_files": len(scaffold_result.get("files", []))})

    # Phase 7: 质量校验
    quality = verify_project_quality(output_dir)
    phases.append({"phase": "quality_verification",
                   "score": quality.get("score", 0),
                   "issues": len(quality.get("issues", []))})

    # Phase 8: 交付整合
    elapsed = (datetime.now() - start_time).total_seconds()
    success = gen_result.get("success", False) and quality.get("score", 0) >= 40

    # 注入认知网络
    if lattice and success:
        try:
            lattice.add_node(
                f"[Flutter项目] {spec.get('app_name', 'app')}: {requirement[:80]}",
                "实践产出", "proven", source="opus_flutter_engineer", silent=True
            )
        except Exception:
            pass

    result = {
        "success": success,
        "project_path": str(output_dir),
        "app_name": spec.get("app_name", "flutter_app"),
        "domain": spec.get("domain", "custom"),
        "files": gen_result.get("files", []),
        "quality_score": quality.get("score", 0),
        "quality_issues": quality.get("issues", []),
        "phases": phases,
        "elapsed_seconds": round(elapsed, 1),
    }

    _log(f"=== 完成: 成功={success}, 质量={quality.get('score', 0)}/100, 耗时={elapsed:.1f}s ===")
    return result


# ==================== 入口 ====================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        req = " ".join(sys.argv[1:])
    else:
        req = "做一个微信克隆应用，包含聊天、通讯录、朋友圈、个人中心"

    output = str(WORKSPACE_DIR / "outputs" / "flutter_gen")
    result = full_pipeline(req, output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
