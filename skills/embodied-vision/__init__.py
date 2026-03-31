"""
embodied-vision — 具身智能视觉系统
统一入口
"""

from .primitives import VisualPrimitives, EdgeDetector, CornerDetector, ContourAnalyzer, TextureAnalyzer, ColorSegmenter
from .detection import ObjectDetector, SaliencyDetector, HierarchicalSegmenter, FeatureMatcher
