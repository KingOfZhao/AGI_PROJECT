"""
AGI Skill: Auto Build Complex Interactive Drawing Viewer (Flutter/CAD)
Name: auto_构建_复杂交互式图纸查看器_在flut_3e7864
Description: Generates high-performance Flutter architecture code for CAD/BIM viewers.
             Focuses on Layer Composition, Hardware Acceleration, and Spatial Indexing.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RenderOptimizationLevel(Enum):
    """渲染优化级别枚举"""
    STANDARD = "standard"
    COMPOSITED = "composited"
    HARDWARE_LAYER = "hardware_layer"

@dataclass
class CADLayer:
    """CAD图层数据结构"""
    id: str
    name: str
    visible: bool = True
    z_index: int = 0
    is_locked: bool = False
    opacity: float = 1.0
    # Flutter特定属性
    use_offscreen_buffer: bool = False 
    cache_mode: str = "none" # none, raster, layer

    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError(f"Opacity must be between 0.0 and 1.0, got {self.opacity}")
        if not self.id:
            raise ValueError("Layer ID cannot be empty")

@dataclass
class FlutterWidgetSpec:
    """Flutter组件生成规范"""
    class_name: str
    imports: List[str] = field(default_factory=list)
    state_fields: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    build_method: str = ""

class CADViewerArchitectureBuilder:
    """
    核心类：构建高性能Flutter CAD查看器架构。
    
    该类负责将CAD图层逻辑映射为Flutter的渲染树，重点解决：
    1. 万级零件的渲染性能（通过RepaintBoundary和OpacityLayer）。
    2. 图层过滤与隔离（通过KeepAlive）。
    3. 精确的点击测试（通过Spatial Indexing建议）。
    """

    def __init__(self, project_name: str, optimization: RenderOptimizationLevel):
        self.project_name = project_name
        self.optimization = optimization
        self._layers: List[CADLayer] = []
        logger.info(f"Initialized Architecture Builder for {project_name} with {optimization.value} mode.")

    def add_layer(self, layer: CADLayer) -> None:
        """添加图层到架构中"""
        try:
            self._layers.append(layer)
            logger.debug(f"Added layer: {layer.name}")
        except Exception as e:
            logger.error(f"Failed to add layer: {e}")
            raise

    def _generate_imports(self) -> str:
        """生成Flutter必要的导入语句"""
        return """
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'dart:math' as math;
import 'dart:ui' as ui;
"""

    def _generate_spatial_index_helper(self) -> str:
        """
        辅助函数：生成空间索引逻辑的Dart代码片段。
        用于加速巨大体量下的Hit-testing。
        """
        return """
  // 辅助类：用于BIM模型快速碰撞检测的R-tree简化实现建议
  // 实际生产建议使用 'rbush' dart package
  class SpatialIndexHelper {
    final List<Rect> boundingBoxes;
    
    SpatialIndexHelper(this.boundingBoxes);

    // 简单的边界检查过滤，复杂场景应使用四叉树或R-Tree
    List<int> queryPotentialHits(Offset tapPosition, double tolerance) {
      final Rect hitRect = Rect.fromCenter(center: tapPosition, width: tolerance, height: tolerance);
      List<int> indices = [];
      
      for (int i = 0; i < boundingBoxes.length; i++) {
        if (boundingBoxes[i].overlaps(hitRect)) {
          indices.add(i);
        }
      }
      return indices;
    }
  }
"""

    def generate_layer_stack_widget(self) -> FlutterWidgetSpec:
        """
        核心函数：生成复杂的图层堆叠Widget代码。
        
        实现细节：
        - 利用 `RepaintBoundary` 隔离重绘区域。
        - 根据配置使用 `Opacity` 或 `Transform` 触发Compositing。
        - 包含图层过滤逻辑。
        
        Returns:
            FlutterWidgetSpec: 包含完整Dart代码的对象。
        """
        logger.info("Generating Layer Stack Widget...")
        
        # 生成图层过滤逻辑
        layer_filter_logic = "final visibleLayers = _layers.where((l) => l.visible).toList();"
        
        # 生成具体的Stack children代码
        stack_children_code = """
        children: visibleLayers.map((layer) {
          // 关键优化：对于静态或半静态CAD图层，使用RepaintBoundary
          // 这会创建一个CompositingLayer，避免父级重绘时波及子级
          return RepaintBoundary(
            key: ValueKey(layer.id),
            child: Opacity(
              opacity: layer.opacity,
              // 如果启用了硬件加速优化，建议Flutter Engine光栅化缓存
              alwaysIncludeSemantics: false,
              child: _buildLayerContent(layer),
            ),
          );
        }).toList(),
        """

        # 组装Build方法
        build_method = f"""
    @override
    Widget build(BuildContext context) {{
      {layer_filter_logic}
      
      return GestureDetector(
        onTapUp: _handleComplexHitTest,
        child: InteractiveViewer(
          minScale: 0.1,
          maxScale: 5.0,
          constrained: false, // 允许在大画布上平移
          child: Container(
            color: Colors.black,
            // 使用Stack实现图层叠加
            child: Stack(
              clipBehavior: Clip.none,
              {stack_children_code}
            ),
          ),
        ),
      );
    }}
    """

        # 生成具体的图层渲染逻辑（模拟）
        layer_content_method = """
    Widget _buildLayerContent(CADLayer layer) {
      // 在实际应用中，这里会调用CustomPaint或巨大的Widget树
      // 这里模拟返回一个带颜色的Container代表图层内容
      return CustomPaint(
        painter: CADLayerPainter(layer),
        size: Size.infinite,
      );
    }
    
    void _handleComplexHitTest(TapUpDetails details) {{
      // 实现基于图层的Hit-testing
      // 1. 转换坐标
      // 2. 使用SpatialIndexHelper快速筛选
      // 3. 遍历可见图层进行精确测试
      print("Hit test at: ${{details.localPosition}}");
    }}
    """

        spec = FlutterWidgetSpec(
            class_name="ComplexCADViewer",
            imports=[self._generate_imports()],
            state_fields=[
                "List<CADLayer> _layers = [];",
                "SpatialIndexHelper? _spatialIndex;"
            ],
            methods=[self._generate_spatial_index_helper(), layer_content_method],
            build_method=build_method
        )
        
        return spec

    def generate_compositing_optimizer(self) -> str:
        """
        核心函数：生成关于图层合成的优化建议和补丁代码。
        
        主要处理：
        - 避免过度绘制。
        - 何时使用SaveLayer。
        
        Returns:
            str: Markdown格式的优化指南和Dart片段。
        """
        logger.info("Generating Compositing Optimization Guidelines...")
        
        guide = f"""
        # CAD图层性能优化指南
        
        ## 1. Compositing Layers 策略
        对于 '{self.project_name}' 这种万级零件场景，必须利用Flutter的Layer Tree。
        
        ### 关键点:
        - **RepaintBoundary**: 在每个 `CADLayer` Widget 之间插入此组件。这会告诉Flutter Engine创建一个新的 `PictureLayer` 或 `DisplayList`，避免一个图层的重绘影响其他图层。
        - **Opacity**: 虽然Opacity有性能开销，但在CAD场景下，用于控制图层显隐的Opacity（0.0 vs 1.0）可以配合 `saveLayer` 实现复杂的遮罩效果。
        
        ### 代码建议:
        