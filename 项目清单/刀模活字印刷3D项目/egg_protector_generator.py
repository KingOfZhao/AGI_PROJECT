"""
egg_protector_generator.py — 鸡蛋保护垫刀模DXF生成器

几何: n瓣环形排列, 每瓣由弧+两腰组成
  - 顶边: 外径圆弧 (弧度 = 2 × top_half_angle)
  - 底边两端点在内径圆上 (角度 = ±π/n, 保证相邻瓣交汇)
  - 两腰: 直线, 从弧端点到内径圆端点
  - 顶弧 < 底边跨度 → 夹角 > 90°
  - 外径圆上相邻瓣之间有间隙

DXF: ezdxf (AutoCAD 2000~2018)
"""

import math
from dataclasses import dataclass
from typing import List
from pathlib import Path

import ezdxf


@dataclass
class EggProtectorParams:
    D_outer: float            # 外径直径 mm
    D_inner: float            # 内径直径 mm
    n: int = 8                # 瓣数
    top_half_angle_deg: float = 18.0  # 顶弧半角(度), 每瓣45°中弧占的角度, <22.5°时夹角>90°

    @property
    def R(self): return self.D_outer / 2
    @property
    def r(self): return self.D_inner / 2
    @property
    def step(self): return 2 * math.pi / self.n
    @property
    def half_step(self): return math.pi / self.n  # 底端半角 = 22.5° for n=8
    @property
    def top_half_angle(self): return math.radians(self.top_half_angle_deg)

    @property
    def corner_angle(self):
        """顶角(度): 弧切线与腰的夹角"""
        R, r = self.R, self.r
        a = self.top_half_angle
        hs = self.half_step
        # 弧右端点切线(回退方向)
        t_back = (math.sin(a), -math.cos(a))
        # 腰方向
        ptr = (R*math.cos(a), R*math.sin(a))
        pbr = (r*math.cos(hs), r*math.sin(hs))
        v_side = (pbr[0]-ptr[0], pbr[1]-ptr[1])
        cos_th = (t_back[0]*v_side[0]+t_back[1]*v_side[1]) / (math.dist((0,0),t_back)*math.dist((0,0),v_side))
        return math.degrees(math.acos(max(-1, min(1, cos_th))))

    @property
    def outer_gap_deg(self):
        """外径圆上相邻瓣间隙(度)"""
        return math.degrees(2 * (self.half_step - self.top_half_angle))

    def validate(self):
        e = []
        if self.D_inner >= self.D_outer: e.append("内径<外径")
        if self.n < 3: e.append("瓣数>=3")
        if self.top_half_angle_deg >= math.degrees(self.half_step):
            e.append(f"top_half_angle必须<{math.degrees(self.half_step):.1f}°才能>90°")
        return e


DXF_VERSIONS = {
    '2000': 'R2000', '2004': 'R2004', '2007': 'R2007',
    '2010': 'R2010', '2013': 'R2013', '2018': 'R2018',
}


def generate_egg_protector_dxf(params: EggProtectorParams, output_path: str, autocad_version: str = '2010') -> str:
    errors = params.validate()
    if errors:
        raise ValueError("参数错误: " + "; ".join(errors))

    ver = DXF_VERSIONS.get(str(autocad_version), 'R2010')
    doc = ezdxf.new(dxfversion=ver)
    doc.layers.add('CUT', color=1)
    doc.layers.add('CONSTRUCTION', color=8)
    msp = doc.modelspace()

    # 辅助圆
    msp.add_circle((0, 0), params.R, dxfattribs={'layer': 'CONSTRUCTION'})
    msp.add_circle((0, 0), params.r, dxfattribs={'layer': 'CONSTRUCTION'})

    alpha = params.top_half_angle  # 顶弧半角
    hs = params.half_step          # 底端半角(固定)

    for i in range(params.n):
        angle = i * params.step

        # ── 顶边: 外径圆弧 ──
        a_start = angle - alpha
        a_end = angle + alpha
        msp.add_arc((0, 0), params.R, math.degrees(a_start), math.degrees(a_end),
                    dxfattribs={'layer': 'CUT'})

        # ── 弧端点(外径圆上) ──
        p_top_left  = (params.R * math.cos(a_start), params.R * math.sin(a_start))
        p_top_right = (params.R * math.cos(a_end), params.R * math.sin(a_end))

        # ── 底端点(内径圆上, 固定±half_step) ──
        p_bot_left  = (params.r * math.cos(angle - hs), params.r * math.sin(angle - hs))
        p_bot_right = (params.r * math.cos(angle + hs), params.r * math.sin(angle + hs))

        # ── 左腰 + 右腰 ──
        msp.add_line(p_top_left, p_bot_left, dxfattribs={'layer': 'CUT'})
        msp.add_line(p_top_right, p_bot_right, dxfattribs={'layer': 'CUT'})

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(output_path)
    return output_path


def preview(params):
    return f"""=== 鸡蛋保护垫 ===
外径 D={params.D_outer}mm  内径 d={params.D_inner}mm  瓣数 n={params.n}
径向深度 = {params.R - params.r:.2f} mm
顶弧半角 = {params.top_half_angle_deg}° (弧占{2*params.top_half_angle_deg:.1f}°/瓣)
底端半角 = {math.degrees(params.half_step):.1f}° (底端占{2*math.degrees(params.half_step):.1f}°/瓣)
外径间隙 = {params.outer_gap_deg:.1f}°
顶角 = {params.corner_angle:.1f}° (>90° ✅)
顶边与外径圆弧贴合 ✅  底边两端点在内径圆上 ✅"""


if __name__ == "__main__":
    params = EggProtectorParams(D_outer=45, D_inner=37.9, n=8, top_half_angle_deg=18.0)
    print(preview(params))
    out = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/output"
    for v in ['2010', '2007']:
        path = generate_egg_protector_dxf(params, f"{out}/egg_protector_D{params.D_outer}_d{params.D_inner}_AC{v}.dxf", autocad_version=v)
        print(f"✅ {path}")
