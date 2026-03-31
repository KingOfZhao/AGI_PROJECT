"""
line_type_classifier.py — DiePre 线条类型分类器
v1.0 — 2026-03-31

基于多特征融合的切割线/折叠线/压痕线分类:
1. 线宽(Stroke Width): 切割线粗(≥3px), 折叠线细(1-2px)
2. 断续性(Continuity): 虚线=折叠/压痕, 实线=切割
3. 长度(Long): 短线段可能是噪点
4. 方向一致性: 切割线多为直线段，折叠线可能有微弯
5. 端点特征: 封闭轮廓vs开放线段

输出: 每条线段标注LineType + 置信度
"""

import os
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from enum import Enum


class LineType(Enum):
    CUT = "cut"          # 切割线 — 粗实线，穿透纸板
    FOLD = "fold"        # 折叠线 — 细实线或虚线，不穿透
    CREASE = "crease"    # 压痕线 — 点划线
    SLOT = "slot"        # 插槽 — 短粗线段
    BRIDGE = "bridge"    # 桥接线 — 连接切割线的短线
    UNKNOWN = "unknown"


@dataclass
class ClassifiedLine:
    """分类后的线段"""
    start: Tuple[float, float]
    end: Tuple[float, float]
    line_type: LineType
    confidence: float  # 0-1
    features: Dict = field(default_factory=dict)  # 原始特征值

    @property
    def length_px(self) -> float:
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return math.sqrt(dx*dx + dy*dy)

    @property
    def angle_deg(self) -> float:
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return math.degrees(math.atan2(dy, dx))

    def to_dict(self) -> Dict:
        return {
            "start": list(self.start),
            "end": list(self.end),
            "type": self.line_type.value,
            "confidence": round(self.confidence, 3),
            "length_px": round(self.length_px, 1),
            "angle_deg": round(self.angle_deg, 1),
            "features": {k: round(v, 3) if isinstance(v, float) else v
                         for k, v in self.features.items()},
        }


class LineTypeClassifier:
    """
    多特征线条分类器
    
    特征提取:
    - stroke_width: 沿线段法线方向采样，统计线宽均值
    - continuity: 线段上断点比例（0=完全连续, 1=完全断裂）
    - length: 线段长度(像素)
    - angle: 线段角度
    - endpoint_type: 端点是否连接到其他线段
    
    分类规则(基于包装行业知识):
    - 切割线: 粗(≥3px) + 连续 + 长(≥50px)
    - 折叠线: 细(1-2px) + 连续或虚线 + 长(≥50px)
    - 压痕线: 细 + 高断续性 + 中等长度
    - 桥接线: 短(10-40px) + 粗 + 连接切割线
    - 插槽: 短 + 粗 + 孤立
    """

    def __init__(self, pixel_to_mm: float = 0.25):
        self.pixel_to_mm = pixel_to_mm
        self.classified_lines: List[ClassifiedLine] = []

    def extract_features(self, binary_img, x1, y1, x2, y2) -> Dict:
        """
        提取单条线段的特征
        
        Args:
            binary_img: 二值图像(0=白, 255=黑)，numpy数组
            x1,y1,x2,y2: 线段端点坐标
        """
        import numpy as np

        h, w = binary_img.shape[:2]
        length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        angle = math.atan2(y2-y1, x2-x1)

        features = {
            "length_px": length,
            "angle_deg": math.degrees(angle),
        }

        # 1. 线宽估计: 沿法线方向采样
        if length > 0:
            normal_angle = angle + math.pi/2
            dx_n = math.cos(normal_angle)
            dy_n = math.sin(normal_angle)

            widths = []
            num_samples = max(2, int(length / 5))
            for i in range(num_samples):
                t = i / max(1, num_samples - 1)
                cx = x1 + t * (x2 - x1)
                cy = y1 + t * (y2 - y1)

                # 沿法线方向双向扫描找边缘
                for sign in [1, -1]:
                    for dist in range(1, 20):
                        px = int(cx + sign * dist * dx_n)
                        py = int(cy + sign * dist * dy_n)
                        if not (0 <= px < w and 0 <= py < h):
                            break
                        if binary_img[py, px] == 0:  # hit white=background
                            widths.append(dist)
                            break

            features["stroke_width"] = sum(widths) / len(widths) if widths else 1.0
        else:
            features["stroke_width"] = 0

        # 2. 连续性: 沿线段方向采样，检查像素值
        if length > 1:
            num_check = max(2, int(length / 2))
            dark_count = 0
            total_count = 0
            for i in range(num_check):
                t = i / max(1, num_check - 1)
                px = int(x1 + t * (x2 - x1))
                py = int(y1 + t * (y2 - y1))
                if 0 <= px < w and 0 <= py < h:
                    total_count += 1
                    if binary_img[py, px] > 0:  # dark=line
                        dark_count += 1
            features["continuity"] = dark_count / max(1, total_count)
        else:
            features["continuity"] = 1.0

        # 3. 线宽一致性(标准差/均值)
        # (simplified — just use stroke_width and length)

        return features

    def classify(self, features: Dict, neighbor_count: int = 0) -> Tuple[LineType, float]:
        """
        基于特征进行分类
        
        Returns: (LineType, confidence)
        """
        length = features.get("length_px", 0)
        width = features.get("stroke_width", 1.0)
        continuity = features.get("continuity", 1.0)

        scores = {}

        # 切割线评分: 粗 + 连续 + 长
        cut_score = 0
        if width >= 3.0:
            cut_score += 0.4
        elif width >= 2.0:
            cut_score += 0.2
        if continuity > 0.85:
            cut_score += 0.3
        if length >= 50:
            cut_score += 0.3
        elif length >= 30:
            cut_score += 0.15
        scores[LineType.CUT] = cut_score

        # 折叠线评分: 细 + 连续 + 长
        fold_score = 0
        if 1.0 <= width <= 2.5:
            fold_score += 0.4
        elif width < 1.0:
            fold_score += 0.2
        if continuity > 0.7:
            fold_score += 0.3
        if length >= 50:
            fold_score += 0.3
        elif length >= 30:
            fold_score += 0.15
        scores[LineType.FOLD] = fold_score

        # 压痕线评分: 细 + 断续
        crease_score = 0
        if width <= 2.0:
            crease_score += 0.3
        if 0.2 < continuity < 0.8:
            crease_score += 0.4
        elif continuity <= 0.2:
            crease_score += 0.2
        if length >= 20:
            crease_score += 0.3
        scores[LineType.CREASE] = crease_score

        # 桥接线评分: 短 + 粗 + 有邻居
        bridge_score = 0
        if 10 <= length <= 40:
            bridge_score += 0.4
        if width >= 2.0:
            bridge_score += 0.3
        if neighbor_count >= 1:
            bridge_score += 0.3
        scores[LineType.BRIDGE] = bridge_score

        # 插槽评分: 短 + 粗 + 孤立
        slot_score = 0
        if length <= 30:
            slot_score += 0.4
        if width >= 3.0:
            slot_score += 0.3
        if neighbor_count == 0:
            slot_score += 0.3
        scores[LineType.SLOT] = slot_score

        # 选最高分
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        # 归一化置信度
        confidence = min(1.0, best_score / 0.8)

        # 如果最高分太低，标记UNKNOWN
        if best_score < 0.3:
            return LineType.UNKNOWN, 0.2

        return best_type, confidence

    def process_image(self, binary_path: str) -> List[ClassifiedLine]:
        """
        处理二值化图像，返回分类后的线段列表
        
        Args:
            binary_path: 二值化图像路径(白底黑线)
        """
        import cv2
        import numpy as np

        img = cv2.imread(binary_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Cannot read: {binary_path}")

        # Canny边缘检测 + HoughLinesP
        edges = cv2.Canny(img, 50, 150)
        lines_p = cv2.HoughLinesP(
            edges, rho=1, theta=np.pi/180,
            threshold=50, minLineLength=20, maxLineGap=10
        )

        if lines_p is None:
            return []

        # 提取特征 + 分类
        results = []
        for line in lines_p:
            x1, y1, x2, y2 = line[0].astype(float)

            features = self.extract_features(img, x1, y1, x2, y2)
            line_type, confidence = self.classify(features)

            results.append(ClassifiedLine(
                start=(x1, y1),
                end=(x2, y2),
                line_type=line_type,
                confidence=confidence,
                features=features,
            ))

        self.classified_lines = results
        return results

    def get_statistics(self) -> Dict:
        """获取分类统计"""
        if not self.classified_lines:
            return {"total": 0}

        type_counts = {}
        confidence_by_type = {}
        for cl in self.classified_lines:
            t = cl.line_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
            if t not in confidence_by_type:
                confidence_by_type[t] = []
            confidence_by_type[t].append(cl.confidence)

        avg_conf = {t: sum(v)/len(v) for t, v in confidence_by_type.items()}

        return {
            "total": len(self.classified_lines),
            "by_type": type_counts,
            "avg_confidence": {t: round(v, 3) for t, v in avg_conf.items()},
            "total_cut": type_counts.get("cut", 0),
            "total_fold": type_counts.get("fold", 0),
            "total_crease": type_counts.get("crease", 0),
            "total_bridge": type_counts.get("bridge", 0),
            "total_unknown": type_counts.get("unknown", 0),
        }

    def export_json(self, output_path: str):
        """导出分类结果为JSON"""
        import json
        data = {
            "statistics": self.get_statistics(),
            "lines": [cl.to_dict() for cl in self.classified_lines],
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return output_path

    def generate_annotated_image(self, binary_path: str, output_path: str):
        """
        生成标注了线段类型的彩色图像
        
        颜色编码:
        - 切割线(CUT): 红色
        - 折叠线(FOLD): 蓝色
        - 压痕线(CREASE): 绿色
        - 桥接线(BRIDGE): 黄色
        - 插槽(SLOT): 紫色
        - 未知(UNKNOWN): 灰色
        """
        import cv2
        import numpy as np

        img = cv2.imread(binary_path)
        if img is None:
            raise ValueError(f"Cannot read: {binary_path}")

        colors = {
            LineType.CUT: (0, 0, 255),      # Red
            LineType.FOLD: (255, 0, 0),      # Blue
            LineType.CREASE: (0, 255, 0),    # Green
            LineType.BRIDGE: (0, 255, 255),  # Yellow
            LineType.SLOT: (255, 0, 255),    # Purple
            LineType.UNKNOWN: (128, 128, 128),  # Gray
        }

        for cl in self.classified_lines:
            color = colors.get(cl.line_type, (128, 128, 128))
            pt1 = (int(cl.start[0]), int(cl.start[1]))
            pt2 = (int(cl.end[0]), int(cl.end[1]))
            thickness = 2 if cl.line_type == LineType.CUT else 1
            cv2.line(img, pt1, pt2, color, thickness)

        # 添加图例
        legend_y = 30
        for lt, color in colors.items():
            cv2.putText(img, lt.value, (10, legend_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            legend_y += 20

        cv2.imwrite(output_path, img)
        return output_path


def batch_classify(input_dir: str, output_dir: str):
    """
    批量分类: 处理目录下所有二值化图像
    """
    classifier = LineTypeClassifier()
    os.makedirs(output_dir, exist_ok=True)

    results = {}
    for fname in sorted(os.listdir(input_dir)):
        if '_binary.png' in fname and '_binary_cad' not in fname:
            input_path = os.path.join(input_dir, fname)
            base = fname.replace('_binary.png', '')

            try:
                lines = classifier.process_image(input_path)
                stats = classifier.get_statistics()

                # 导出JSON
                json_path = os.path.join(output_dir, f"{base}_classified.json")
                classifier.export_json(json_path)

                # 导出标注图像
                img_path = os.path.join(output_dir, f"{base}_classified.png")
                classifier.generate_annotated_image(input_path, img_path)

                results[base] = stats
                print(f"✅ {base}: {stats['total']} lines "
                      f"(CUT={stats.get('total_cut',0)} "
                      f"FOLD={stats.get('total_fold',0)} "
                      f"CREASE={stats.get('total_crease',0)} "
                      f"BRIDGE={stats.get('total_bridge',0)} "
                      f"UNK={stats.get('total_unknown',0)})")

            except Exception as e:
                results[base] = {"error": str(e)}
                print(f"❌ {base}: {e}")

    # 汇总
    summary_path = os.path.join(output_dir, "_batch_summary.json")
    import json
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


if __name__ == "__main__":
    import sys
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "data/vision_output"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/vision_output"

    print(f"=== DiePre Line Type Classifier ===")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print()

    results = batch_classify(input_dir, output_dir)
    print(f"\n=== Done: {len(results)} images processed ===")
