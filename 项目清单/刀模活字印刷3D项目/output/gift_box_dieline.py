#!/usr/bin/env python3
"""
天地盖礼品盒 DXF 刀线图生成器

产品: 天地盖礼品盒
尺寸: 内尺寸 100mm(长) × 80mm(宽) × 40mm(高)
材料: 350g白卡纸, 厚度约0.45mm
"""

import os
import math
from pathlib import Path

try:
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False
    print("警告: ezdxf未安装，使用简化DXF生成")

OUTPUT_DIR = Path(__file__).parent


# ═══════════════════════════════════════════════════════════════
# 参数配置
# ═══════════════════════════════════════════════════════════════

class BoxParams:
    """盒子参数"""
    # 内尺寸
    inner_length = 100.0  # mm
    inner_width = 80.0    # mm
    inner_height = 40.0   # mm
    
    # 材料
    paper_thickness = 0.45  # mm (350g白卡纸)
    
    # 结构参数
    lid_clearance = 1.0     # 盖子比底大的间隙
    lid_height_ratio = 0.55  # 盖高度为底高度的比例
    glue_tab_width = 15.0   # 粘口宽度
    
    # 计算外尺寸
    @property
    def bottom_outer_length(self):
        return self.inner_length + 2 * self.paper_thickness
    
    @property
    def bottom_outer_width(self):
        return self.inner_width + 2 * self.paper_thickness
    
    @property
    def lid_inner_length(self):
        return self.bottom_outer_length + self.lid_clearance
    
    @property
    def lid_inner_width(self):
        return self.bottom_outer_width + self.lid_clearance
    
    @property
    def lid_outer_length(self):
        return self.lid_inner_length + 2 * self.paper_thickness
    
    @property
    def lid_outer_width(self):
        return self.lid_inner_width + 2 * self.paper_thickness
    
    @property
    def lid_height(self):
        return self.inner_height * self.lid_height_ratio


# ═══════════════════════════════════════════════════════════════
# DXF生成器
# ═══════════════════════════════════════════════════════════════

class DielineGenerator:
    """刀线图生成器"""
    
    def __init__(self, params: BoxParams):
        self.params = params
        
        if HAS_EZDXF:
            self.doc = ezdxf.new('R2010')
            self.msp = self.doc.modelspace()
            self._setup_linetypes()
        else:
            self.lines = []  # 简化模式
    
    def _setup_linetypes(self):
        """设置线型"""
        if not HAS_EZDXF:
            return
        
        # 添加虚线线型
        self.doc.linetypes.add(
            "DASHED",
            pattern=[0.5, 0.25, -0.25],
            description="Fold line"
        )
        
        # 创建图层
        self.doc.layers.add("CUT", color=1)      # 红色 - 切割线
        self.doc.layers.add("FOLD", color=5)     # 蓝色 - 折痕线
        self.doc.layers.add("ANNO", color=7)     # 白色 - 标注
    
    def add_cut_line(self, x1, y1, x2, y2):
        """添加切割线（实线）"""
        if HAS_EZDXF:
            self.msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "CUT"})
        else:
            self.lines.append(("CUT", x1, y1, x2, y2))
    
    def add_fold_line(self, x1, y1, x2, y2):
        """添加折痕线（虚线）"""
        if HAS_EZDXF:
            self.msp.add_line(
                (x1, y1), (x2, y2), 
                dxfattribs={"layer": "FOLD", "linetype": "DASHED"}
            )
        else:
            self.lines.append(("FOLD", x1, y1, x2, y2))
    
    def add_text(self, x, y, text, height=3):
        """添加文字标注"""
        if HAS_EZDXF:
            self.msp.add_text(
                text, 
                dxfattribs={"layer": "ANNO", "height": height}
            ).set_placement((x, y))
    
    def generate_box_dieline(self, length, width, height, glue_tab, offset_x=0, offset_y=0):
        """
        生成盒子展开图
        
        结构:
              [顶盖耳]
        [左耳][顶盖][右耳][粘口]
              [前面]
        [左耳][底面][右耳]
              [后面]
              [底盖耳]
        """
        p = self.params
        x0, y0 = offset_x, offset_y
        
        # ── 底面 (中心) ──
        bx, by = x0 + height, y0 + height + width
        
        # 底面轮廓（切割线）
        self.add_cut_line(bx, by, bx + length, by)
        self.add_cut_line(bx + length, by, bx + length, by + width)
        self.add_cut_line(bx + length, by + width, bx, by + width)
        self.add_cut_line(bx, by + width, bx, by)
        
        # ── 前面板 ──
        fy = by - height
        # 切割线
        self.add_cut_line(bx, fy, bx + length, fy)
        # 折痕线（与底面连接）
        self.add_fold_line(bx, by, bx + length, by)
        
        # 前面板左右连接线
        self.add_cut_line(bx, fy, bx, by)
        self.add_cut_line(bx + length, fy, bx + length, by)
        
        # ── 后面板 ──
        ry = by + width + height
        # 切割线
        self.add_cut_line(bx, ry, bx + length, ry)
        # 折痕线
        self.add_fold_line(bx, by + width, bx + length, by + width)
        
        # 后面板左右连接线
        self.add_cut_line(bx, by + width, bx, ry)
        self.add_cut_line(bx + length, by + width, bx + length, ry)
        
        # ── 左侧面板 ──
        lx = bx - height
        # 切割线
        self.add_cut_line(lx, by, lx, by + width)
        # 折痕线
        self.add_fold_line(bx, by, bx, by + width)
        
        # 左面板上下连接线
        self.add_cut_line(lx, by, bx, by)
        self.add_cut_line(lx, by + width, bx, by + width)
        
        # ── 右侧面板 ──
        rx = bx + length + height
        # 切割线
        self.add_cut_line(rx, by, rx, by + width)
        # 折痕线
        self.add_fold_line(bx + length, by, bx + length, by + width)
        
        # 右面板上下连接线
        self.add_cut_line(bx + length, by, rx, by)
        self.add_cut_line(bx + length, by + width, rx, by + width)
        
        # ── 粘口（右侧延伸）──
        gx = rx + glue_tab
        # 粘口轮廓（梯形）
        self.add_cut_line(rx, by + 5, gx - 5, by + 5)
        self.add_cut_line(gx - 5, by + 5, gx, by + 10)
        self.add_cut_line(gx, by + 10, gx, by + width - 10)
        self.add_cut_line(gx, by + width - 10, gx - 5, by + width - 5)
        self.add_cut_line(gx - 5, by + width - 5, rx, by + width - 5)
        # 折痕线
        self.add_fold_line(rx, by + 5, rx, by + width - 5)
        
        # ── 顶盖耳（前面板上方）──
        ear_height = 15
        ey = fy - ear_height
        # 顶部梯形耳
        self.add_cut_line(bx + 10, ey, bx + length - 10, ey)
        self.add_cut_line(bx + 10, ey, bx, fy)
        self.add_cut_line(bx + length - 10, ey, bx + length, fy)
        # 折痕线
        self.add_fold_line(bx, fy, bx + length, fy)
        
        # ── 底盖耳（后面板下方）──
        ey2 = ry + ear_height
        self.add_cut_line(bx + 10, ey2, bx + length - 10, ey2)
        self.add_cut_line(bx + 10, ey2, bx, ry)
        self.add_cut_line(bx + length - 10, ey2, bx + length, ry)
        # 折痕线
        self.add_fold_line(bx, ry, bx + length, ry)
        
        # ── 左侧耳（上下）──
        # 上耳
        self.add_cut_line(lx - 10, by + width - 5, lx, by + width - 5)
        self.add_cut_line(lx - 10, by + width - 5, lx - 10, by + width - 10)
        self.add_cut_line(lx - 10, by + width - 10, lx, by + width)
        # 下耳
        self.add_cut_line(lx - 10, by + 5, lx, by + 5)
        self.add_cut_line(lx - 10, by + 5, lx - 10, by + 10)
        self.add_cut_line(lx - 10, by + 10, lx, by)
        
        # ── 右侧耳（上下）──
        # 上耳
        self.add_cut_line(rx + 10, by + width - 5, rx, by + width - 5)
        self.add_cut_line(rx + 10, by + width - 5, rx + 10, by + width - 10)
        self.add_cut_line(rx + 10, by + width - 10, rx, by + width)
        # 下耳
        self.add_cut_line(rx + 10, by + 5, rx, by + 5)
        self.add_cut_line(rx + 10, by + 5, rx + 10, by + 10)
        self.add_cut_line(rx + 10, by + 10, rx, by)
        
        # 返回总尺寸
        return {
            "total_width": 2 * height + length + glue_tab + 20,
            "total_height": 2 * height + 2 * width + 2 * ear_height
        }
    
    def generate_bottom(self):
        """生成底盒刀线"""
        p = self.params
        
        self.add_text(5, 5, f"底盒 - 内尺寸: {p.inner_length}x{p.inner_width}x{p.inner_height}mm")
        
        return self.generate_box_dieline(
            length=p.inner_length,
            width=p.inner_width,
            height=p.inner_height,
            glue_tab=p.glue_tab_width,
            offset_x=10,
            offset_y=10
        )
    
    def generate_lid(self, offset_y=0):
        """生成盖盒刀线"""
        p = self.params
        
        self.add_text(5, offset_y + 5, 
                     f"盖盒 - 内尺寸: {p.lid_inner_length:.1f}x{p.lid_inner_width:.1f}x{p.lid_height:.1f}mm")
        
        return self.generate_box_dieline(
            length=p.lid_inner_length,
            width=p.lid_inner_width,
            height=p.lid_height,
            glue_tab=p.glue_tab_width,
            offset_x=10,
            offset_y=offset_y + 10
        )
    
    def save(self, filename):
        """保存DXF文件"""
        filepath = OUTPUT_DIR / filename
        
        if HAS_EZDXF:
            self.doc.saveas(str(filepath))
        else:
            # 简化DXF格式
            self._save_simple_dxf(filepath)
        
        return filepath
    
    def _save_simple_dxf(self, filepath):
        """简化DXF保存（无ezdxf时使用）"""
        with open(filepath, 'w') as f:
            # DXF头部
            f.write("0\nSECTION\n2\nHEADER\n0\nENDSEC\n")
            f.write("0\nSECTION\n2\nENTITIES\n")
            
            # 写入线段
            for line in self.lines:
                layer, x1, y1, x2, y2 = line
                f.write(f"0\nLINE\n8\n{layer}\n")
                f.write(f"10\n{x1}\n20\n{y1}\n30\n0\n")
                f.write(f"11\n{x2}\n21\n{y2}\n31\n0\n")
            
            f.write("0\nENDSEC\n0\nEOF\n")


# ═══════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("天地盖礼品盒 刀线图生成")
    print("=" * 60)
    
    # 创建参数
    params = BoxParams()
    
    print(f"\n📦 盒子参数:")
    print(f"  内尺寸: {params.inner_length} × {params.inner_width} × {params.inner_height} mm")
    print(f"  纸厚: {params.paper_thickness} mm")
    print(f"  盖间隙: {params.lid_clearance} mm")
    
    print(f"\n📐 计算尺寸:")
    print(f"  底盒外尺寸: {params.bottom_outer_length:.2f} × {params.bottom_outer_width:.2f} mm")
    print(f"  盖盒内尺寸: {params.lid_inner_length:.2f} × {params.lid_inner_width:.2f} mm")
    print(f"  盖盒外尺寸: {params.lid_outer_length:.2f} × {params.lid_outer_width:.2f} mm")
    print(f"  盖高度: {params.lid_height:.2f} mm")
    
    # 生成底盒DXF
    print("\n🔧 生成底盒刀线...")
    gen_bottom = DielineGenerator(params)
    bottom_size = gen_bottom.generate_bottom()
    bottom_path = gen_bottom.save("gift_box_bottom.dxf")
    print(f"  ✓ 底盒刀线图: {bottom_path}")
    print(f"    展开尺寸: {bottom_size['total_width']:.1f} × {bottom_size['total_height']:.1f} mm")
    
    # 生成盖盒DXF
    print("\n🔧 生成盖盒刀线...")
    gen_lid = DielineGenerator(params)
    lid_size = gen_lid.generate_lid()
    lid_path = gen_lid.save("gift_box_lid.dxf")
    print(f"  ✓ 盖盒刀线图: {lid_path}")
    print(f"    展开尺寸: {lid_size['total_width']:.1f} × {lid_size['total_height']:.1f} mm")
    
    # 生成合并文件
    print("\n🔧 生成合并刀线...")
    gen_combined = DielineGenerator(params)
    gen_combined.generate_bottom()
    gen_combined.generate_lid(offset_y=bottom_size['total_height'] + 30)
    combined_path = gen_combined.save("gift_box_combined.dxf")
    print(f"  ✓ 合并刀线图: {combined_path}")
    
    print("\n" + "=" * 60)
    print("✅ 刀线图生成完成!")
    print("=" * 60)
    
    return {
        "bottom": str(bottom_path),
        "lid": str(lid_path),
        "combined": str(combined_path)
    }


if __name__ == "__main__":
    result = main()
    print(f"\n📁 CAD文件地址:")
    for name, path in result.items():
        print(f"  {name}: {path}")
