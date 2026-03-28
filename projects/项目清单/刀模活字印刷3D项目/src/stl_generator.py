#!/usr/bin/env python3
"""
刀模模块 STL 生成器 — 参数化生成3D打印模型
使用纯Python生成STL (无需CadQuery依赖)
"""
import math
import struct
import os
from typing import List, Tuple
from knowledge_base import IADD_STEEL_RULE_SPECS, CONNECTOR_SPECS

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
MODULE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "模块库")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODULE_DIR, exist_ok=True)

# ─── STL 写入工具 ────────────────────────────────────────────────

def _write_stl_binary(filepath: str, triangles: List[Tuple]):
    """写入二进制STL"""
    with open(filepath, "wb") as f:
        f.write(b'\0' * 80)  # header
        f.write(struct.pack('<I', len(triangles)))
        for normal, v1, v2, v3 in triangles:
            f.write(struct.pack('<fff', *normal))
            f.write(struct.pack('<fff', *v1))
            f.write(struct.pack('<fff', *v2))
            f.write(struct.pack('<fff', *v3))
            f.write(struct.pack('<H', 0))

def _normal(v1, v2, v3):
    """计算三角面法向量"""
    ax, ay, az = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
    bx, by, bz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
    nx = ay*bz - az*by
    ny = az*bx - ax*bz
    nz = ax*by - ay*bx
    l = math.sqrt(nx*nx + ny*ny + nz*nz) or 1
    return (nx/l, ny/l, nz/l)

def _box_triangles(x0, y0, z0, dx, dy, dz):
    """生成长方体的三角面列表"""
    x1, y1, z1 = x0+dx, y0+dy, z0+dz
    # 8个顶点
    v = [
        (x0,y0,z0), (x1,y0,z0), (x1,y1,z0), (x0,y1,z0),  # bottom
        (x0,y0,z1), (x1,y0,z1), (x1,y1,z1), (x0,y1,z1),  # top
    ]
    # 6个面, 每面2个三角
    faces = [
        (0,1,2,3),  # bottom -Z
        (4,7,6,5),  # top +Z
        (0,4,5,1),  # front -Y
        (2,6,7,3),  # back +Y
        (0,3,7,4),  # left -X
        (1,5,6,2),  # right +X
    ]
    tris = []
    for a,b,c,d in faces:
        n = _normal(v[a], v[b], v[c])
        tris.append((n, v[a], v[b], v[c]))
        tris.append((n, v[a], v[c], v[d]))
    return tris

def _slot_subtract(body_tris, slot_x0, slot_y0, slot_z0, slot_dx, slot_dy, slot_dz):
    """简化的槽道: 用额外的内壁三角面模拟(非布尔减法)"""
    # 对于STL,我们生成槽道的内壁面
    x0, y0, z0 = slot_x0, slot_y0, slot_z0
    dx, dy, dz = slot_dx, slot_dy, slot_dz
    # 槽道内壁 (4面,无顶无底开口)
    x1, y1, z1 = x0+dx, y0+dy, z0+dz
    v = [
        (x0,y0,z0), (x1,y0,z0), (x1,y1,z0), (x0,y1,z0),
        (x0,y0,z1), (x1,y0,z1), (x1,y1,z1), (x0,y1,z1),
    ]
    tris = []
    # 内壁法向量指向内部(反转)
    inner_faces = [
        (1,0,4,5),  # front inner
        (3,2,6,7),  # back inner
        (0,3,7,4),  # left inner
        (2,1,5,6),  # right inner
    ]
    for a,b,c,d in inner_faces:
        n = _normal(v[a], v[b], v[c])
        tris.append((n, v[a], v[b], v[c]))
        tris.append((n, v[a], v[c], v[d]))
    return body_tris + tris


# ─── 模块 STL 生成器 ─────────────────────────────────────────────

class ModuleSTLGenerator:
    """为每种刀模模块生成参数化STL文件"""

    def __init__(self, blade_point: str = "2pt"):
        self.bp = blade_point
        self.bp_mm = IADD_STEEL_RULE_SPECS["blade_thickness"][blade_point]["mm"]
        self.slot_width = self.bp_mm + 0.03  # 过盈配合
        self.blade_height = 23.8  # 标准刀高
        self.base_height = 5.0   # 底座高度
        self.total_height = self.blade_height + self.base_height
        self.body_width = max(8.0, self.slot_width + 4.0)  # 两侧壁各2mm
        self.dt = CONNECTOR_SPECS["dovetail"]

    def generate_straight(self, length_mm: float, role: str = "CUT") -> str:
        """生成直线段模块STL"""
        w = self.body_width
        d = 12.0  # body depth
        h = self.total_height

        # 主体
        tris = _box_triangles(0, 0, 0, length_mm, w, h)

        # 刀片槽道 (中心, 从顶面向下)
        slot_x = 0
        slot_y = (w - self.slot_width) / 2
        slot_z = self.base_height  # 从底座顶开始
        slot_h = self.blade_height + 0.5  # 稍深一点确保穿透
        tris = _slot_subtract(tris, slot_x, slot_y, slot_z,
                              length_mm, self.slot_width, slot_h)

        # 燕尾榫 (两端)
        dt_w = self.dt["width_mm"]
        dt_d = self.dt["depth_mm"]
        # 左端凸榫
        tris += _box_triangles(-dt_d, (w-dt_w)/2, 2, dt_d, dt_w, h-4)
        # 右端凹槽 (简化为小方块占位)
        tris += _box_triangles(length_mm, (w-dt_w)/2-0.15, 2,
                               dt_d, dt_w+0.3, h-4)

        name = f"STRAIGHT_{self.bp}_{length_mm:.0f}mm_{role}"
        path = os.path.join(MODULE_DIR, f"{name}.stl")
        _write_stl_binary(path, tris)
        return path

    def generate_corner(self, angle_deg: float, inner_radius_mm: float = 2.0) -> str:
        """生成转角模块STL (简化为方块+弧形槽道)"""
        blk = max(15, inner_radius_mm * 2 + 8)
        h = self.total_height

        # 方块主体
        tris = _box_triangles(0, 0, 0, blk, blk, h)

        # 弧形槽道用多段直线近似
        cx, cy = blk/2, blk/2
        r = inner_radius_mm
        n_segs = max(4, int(angle_deg / 15))
        start_a = math.radians(-angle_deg / 2)

        for i in range(n_segs):
            a1 = start_a + math.radians(angle_deg * i / n_segs)
            a2 = start_a + math.radians(angle_deg * (i+1) / n_segs)
            x1 = cx + r * math.cos(a1)
            y1 = cy + r * math.sin(a1)
            x2 = cx + r * math.cos(a2)
            y2 = cy + r * math.sin(a2)
            seg_len = math.hypot(x2-x1, y2-y1)
            if seg_len > 0.1:
                tris += _box_triangles(
                    min(x1,x2)-self.slot_width/2, min(y1,y2)-self.slot_width/2,
                    self.base_height, seg_len+self.slot_width, seg_len+self.slot_width,
                    self.blade_height)

        name = f"CORNER_{self.bp}_{angle_deg:.0f}deg_R{inner_radius_mm:.1f}"
        path = os.path.join(MODULE_DIR, f"{name}.stl")
        _write_stl_binary(path, tris)
        return path

    def generate_t_joint(self) -> str:
        """生成T形接头STL"""
        blk = 20.0
        h = self.total_height
        tris = _box_triangles(0, 0, 0, blk, blk, h)

        # 三向槽道
        sw = self.slot_width
        mid = blk / 2
        # 水平槽
        tris = _slot_subtract(tris, 0, mid-sw/2, self.base_height, blk, sw, self.blade_height)
        # 垂直槽 (上半)
        tris = _slot_subtract(tris, mid-sw/2, mid, self.base_height, sw, blk/2, self.blade_height)

        name = f"T_JOINT_{self.bp}"
        path = os.path.join(MODULE_DIR, f"{name}.stl")
        _write_stl_binary(path, tris)
        return path

    def generate_cross_joint(self) -> str:
        """生成十字接头STL"""
        blk = 20.0
        h = self.total_height
        tris = _box_triangles(0, 0, 0, blk, blk, h)

        sw = self.slot_width
        mid = blk / 2
        tris = _slot_subtract(tris, 0, mid-sw/2, self.base_height, blk, sw, self.blade_height)
        tris = _slot_subtract(tris, mid-sw/2, 0, self.base_height, sw, blk, self.blade_height)

        name = f"CROSS_JOINT_{self.bp}"
        path = os.path.join(MODULE_DIR, f"{name}.stl")
        _write_stl_binary(path, tris)
        return path

    def generate_end_cap(self, style: str = "平头") -> str:
        """生成端头STL"""
        w = self.body_width
        l = 10.0
        h = self.total_height
        tris = _box_triangles(0, 0, 0, l, w, h)
        # 半截刀槽
        tris = _slot_subtract(tris, 0, (w-self.slot_width)/2, self.base_height,
                              l*0.7, self.slot_width, self.blade_height)

        name = f"END_CAP_{self.bp}_{style}"
        path = os.path.join(MODULE_DIR, f"{name}.stl")
        _write_stl_binary(path, tris)
        return path

    def generate_base_tile(self, width_mm: float, depth_mm: float) -> str:
        """生成底板模块STL"""
        h = 5.0  # 底板厚度
        tris = _box_triangles(0, 0, 0, width_mm, depth_mm, h)

        # 边缘拼接榫 (简化为凸台)
        tab_w, tab_d, tab_h = 10, 3, 3
        # 每边中间位置
        tris += _box_triangles(width_mm/2-tab_w/2, -tab_d, 1, tab_w, tab_d, tab_h)  # front
        tris += _box_triangles(width_mm/2-tab_w/2, depth_mm, 1, tab_w, tab_d, tab_h)  # back
        tris += _box_triangles(-tab_d, depth_mm/2-tab_w/2, 1, tab_d, tab_w, tab_h)  # left
        tris += _box_triangles(width_mm, depth_mm/2-tab_w/2, 1, tab_d, tab_w, tab_h)  # right

        name = f"BASE_TILE_{width_mm:.0f}x{depth_mm:.0f}mm"
        path = os.path.join(MODULE_DIR, f"{name}.stl")
        _write_stl_binary(path, tris)
        return path

    def generate_bridge(self, bridge_len: float = 5.0) -> str:
        """生成桥接模块STL"""
        w = self.body_width
        h = self.total_height
        tris = _box_triangles(0, 0, 0, bridge_len, w, h)
        # 桥接无刀片槽,两端有燕尾榫
        dt_w = self.dt["width_mm"]
        dt_d = self.dt["depth_mm"]
        tris += _box_triangles(-dt_d, (w-dt_w)/2, 2, dt_d, dt_w, h-4)
        tris += _box_triangles(bridge_len, (w-dt_w)/2, 2, dt_d, dt_w, h-4)

        name = f"BRIDGE_{self.bp}_{bridge_len:.0f}mm"
        path = os.path.join(MODULE_DIR, f"{name}.stl")
        _write_stl_binary(path, tris)
        return path

    def generate_all_standard(self) -> List[str]:
        """生成所有标准模块STL"""
        files = []
        print(f"生成标准模块 (刀片:{self.bp} = {self.bp_mm}mm)...")

        # 直线段: 5种标准长度
        for l in [20, 50, 100, 150, 200]:
            f = self.generate_straight(l)
            files.append(f)
            print(f"  ✓ STRAIGHT {l}mm → {os.path.basename(f)}")

        # 转角: 45° 和 90°
        for a in [45, 90]:
            for rad in [1.42, 3.0]:
                f = self.generate_corner(a, rad)
                files.append(f)
                print(f"  ✓ CORNER {a}° R{rad} → {os.path.basename(f)}")

        # 接头
        f = self.generate_t_joint()
        files.append(f); print(f"  ✓ T_JOINT → {os.path.basename(f)}")

        f = self.generate_cross_joint()
        files.append(f); print(f"  ✓ CROSS_JOINT → {os.path.basename(f)}")

        # 端头
        for sty in ["平头", "圆头"]:
            f = self.generate_end_cap(sty)
            files.append(f); print(f"  ✓ END_CAP {sty} → {os.path.basename(f)}")

        # 底板
        for w, d in [(100,100), (150,150), (200,200)]:
            f = self.generate_base_tile(w, d)
            files.append(f); print(f"  ✓ BASE_TILE {w}×{d} → {os.path.basename(f)}")

        # 桥接
        for bl in [5, 10]:
            f = self.generate_bridge(bl)
            files.append(f); print(f"  ✓ BRIDGE {bl}mm → {os.path.basename(f)}")

        print(f"\n共生成 {len(files)} 个STL文件 → {MODULE_DIR}")
        return files


if __name__ == "__main__":
    import sys
    bp = sys.argv[1] if len(sys.argv) > 1 else "2pt"
    gen = ModuleSTLGenerator(bp)
    gen.generate_all_standard()
