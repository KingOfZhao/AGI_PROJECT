"""
ram_lock_connector.py — 内存条式卡扣连接器

将刀模活字印刷模块的连接方式从燕尾榫改为内存条卡扣:
  1. 底座上有T型卡槽 (类似主板内存插槽)
  2. 模块底部有T型卡榫 (类似内存条金手指边缘)
  3. 从一端斜插入, 按下另一端, 两侧弹性卡扣自动锁死
  4. 按下两侧卡扣释放

优势:
  - 插拔快速 (< 1秒 vs 燕尾榫需要精确对齐)
  - 无需工具
  - 弹性补偿打印公差
  - 锁定后零晃动
  - 支持密集排列 (模块间距 < 1mm)

尺寸参考:
  - DDR5内存条卡扣: 金手指厚度0.3mm, 卡扣行程2mm
  - 刀模刀片厚度: 0.71mm (2pt)
  - 3D打印精度: ±0.15mm (PETG-CF)

适配 cad_to_3d.py 的 STLGenerator
"""

import math
from typing import List, Tuple
from dataclasses import dataclass


# ═══ RAM Lock 几何参数 ═══

@dataclass
class RAMLockParams:
    """内存条卡扣参数"""
    # 模块侧 (模块底部突出的T型榫)
    tenon_width: float = 3.0        # T型榫头部宽度 (mm)
    tenon_thickness: float = 1.2    # T型榫颈部厚度 (mm)
    tenon_height: float = 2.0       # T型榫突出高度 (mm)
    tenon_insert_angle: float = 15  # 插入引导斜角 (度)
    
    # 底座侧 (底座上的T型槽)
    slot_width: float = 3.3         # 槽宽 = tenon_width + 公差
    slot_neck_width: float = 1.5    # 颈部槽宽 = tenon_thickness + 公差
    slot_depth: float = 2.3         # 槽深 = tenon_height + 公差
    
    # 弹性卡扣
    latch_length: float = 4.0       # 卡扣臂长度 (mm)
    latch_width: float = 1.0        # 卡扣厚度 (mm)
    latch_height: float = 1.5       # 卡扣突出高度 (mm)
    latch_spring_back: float = 0.3  # 弹性回弹量 (mm)
    
    # 材料/打印参数
    wall_thickness: float = 1.2     # 最小壁厚
    tolerance: float = 0.15         # 打印公差


DEFAULT_RAM_LOCK = RAMLockParams()


def generate_ram_lock_slot_triangles(
    length: float,
    params: RAMLockParams = DEFAULT_RAM_LOCK,
    base_height: float = 5.0,
    base_width: float = 4.86,
) -> List[Tuple]:
    """
    生成底座上的RAM卡槽 (T型槽 + 两侧卡扣)
    
    返回三角形列表: [(normal, v1, v2, v3), ...]
    用于STLGenerator的subtract=True (挖槽)
    
    Args:
        length: 槽长度 (mm)
        params: RAM Lock参数
        base_height: 底座高度
        base_width: 底座总宽度
    """
    triangles = []
    
    # 1. T型槽 (从顶面向下挖)
    cy = base_width / 2  # 槽中心Y坐标
    
    # 上部宽槽 (T型头部空间)
    slot_top_width = params.slot_width
    slot_top_depth = params.tenon_height * 0.4  # 上部占40%
    
    # 下部窄槽 (T型颈部空间)  
    slot_neck_depth = params.slot_depth - slot_top_depth
    
    # 宽槽
    t = triangles
    x0, x1 = 0, length
    y0 = cy - slot_top_width / 2
    y1 = cy + slot_top_width / 2
    z0 = base_height
    z1 = base_height + slot_top_depth
    _add_box_triangles(t, x0, y0, z0, length, slot_top_width, slot_top_depth)
    
    # 窄槽
    y0n = cy - params.slot_neck_width / 2
    y1n = cy + params.slot_neck_width / 2
    z0n = z1
    z1n = base_height + params.slot_depth
    _add_box_triangles(t, x0, y0n, z0n, length, params.slot_neck_width, slot_neck_depth)
    
    # 2. 两侧卡扣释放槽 (让卡扣有弹性空间)
    latch_slot_width = params.latch_width + 0.4
    latch_slot_depth = params.latch_height + params.latch_spring_back
    
    for side in [-1, 1]:  # 左/右
        ly = cy + side * (slot_top_width / 2 + 0.5)  # 卡扣槽位置
        _add_box_triangles(t,
            params.latch_length,  # X: 从插入端开始
            ly - latch_slot_width / 2,  # Y
            z0,  # Z: 从顶面开始
            length - 2 * params.latch_length,  # 宽度
            latch_slot_width,
            latch_slot_depth,
        )
    
    # 3. 插入端斜面 (15°引导角)
    angle_rad = math.radians(params.tenon_insert_angle)
    chamfer_depth = params.slot_depth * math.tan(angle_rad)
    # 左侧斜面
    _add_wedge_triangles(t,
        0, cy - slot_top_width / 2 - 0.5, z0,
        chamfer_depth, slot_top_width + 1, params.slot_depth,
        angle_rad, side='left',
    )
    
    return triangles


def generate_ram_lock_tenon_triangles(
    length: float,
    params: RAMLockParams = DEFAULT_RAM_LOCK,
    base_height: float = 5.0,
    base_width: float = 4.86,
) -> List[Tuple]:
    """
    生成模块底部的RAM卡榫 (T型突出 + 两侧卡扣)
    
    返回三角形列表: [(normal, v1, v2, v3), ...]
    用于STLGenerator (添加到模块底部)
    
    Args:
        length: 榫长度 (mm)
        params: RAM Lock参数
        base_height: 模块底座高度
        base_width: 模块底座总宽度
    """
    triangles = []
    cy = base_width / 2
    
    # 1. T型榫颈部 (窄条)
    neck_y0 = cy - params.tenon_thickness / 2
    neck_y1 = cy + params.tenon_thickness / 2
    _add_box_triangles(triangles,
        0, neck_y0, 0,
        length, params.tenon_thickness, params.tenon_height * 0.6,
    )
    
    # 2. T型榫头部 (宽条, 在颈部上方)
    head_y0 = cy - params.tenon_width / 2
    head_y1 = cy + params.tenon_width / 2
    head_z0 = params.tenon_height * 0.6
    head_z1 = params.tenon_height
    _add_box_triangles(triangles,
        0, head_y0, head_z0,
        length, params.tenon_width, head_z1 - head_z0,
    )
    
    # 3. 两侧弹性卡扣 (悬臂结构)
    for side in [-1, 1]:
        latch_y = cy + side * (params.tenon_width / 2 + params.latch_width / 2 + 0.1)
        latch_z = params.tenon_height * 0.5
        
        # 卡扣臂 (从模块底部延伸)
        _add_box_triangles(triangles,
            params.latch_length,  # X: 从插入端开始
            latch_y - params.latch_width / 2,
            latch_z,
            length - 2 * params.latch_length,  # 臂长度
            params.latch_width,
            params.latch_height,
        )
        
        # 卡扣头部 (锁定凸起)
        _add_box_triangles(triangles,
            length - 2 * params.latch_length,  # X: 远端
            latch_y - params.latch_width / 2,
            latch_z + params.latch_height - 0.3,
            params.latch_length,
            params.latch_width + 0.3,  # 稍宽以卡住
            0.3,  # 锁定凸起高度
        )
    
    # 4. 插入端斜面 (15°引导, 方便滑入)
    angle_rad = math.radians(params.tenon_insert_angle)
    chamfer = params.tenon_height * math.tan(angle_rad)
    # 前端T型头部斜面
    _add_wedge_triangles(triangles,
        0, cy - params.tenon_width / 2, head_z0,
        chamfer, params.tenon_width, head_z1 - head_z0,
        angle_rad, side='left',
    )
    
    return triangles


# ═══ STL 三角形辅助函数 ═══

def _add_box_triangles(
    triangles: list,
    x, y, z,
    dx, dy, dz,
):
    """添加长方体 (12个三角形)"""
    # 8个顶点
    v = [
        (x, y, z),             # 0: 底面左后
        (x+dx, y, z),          # 1: 底面右后
        (x+dx, y+dy, z),       # 2: 底面右前
        (x, y+dy, z),          # 3: 底面左前
        (x, y, z+dz),          # 4: 顶面左后
        (x+dx, y, z+dz),       # 5: 顶面右后
        (x+dx, y+dy, z+dz),    # 6: 顶面右前
        (x, y+dy, z+dz),       # 7: 顶面左前
    ]
    
    # 6个面, 每面2个三角形 (法向量朝外)
    faces = [
        # 底面 (z=-1)
        ((0, 0, -1), v[0], v[1], v[2]),
        ((0, 0, -1), v[0], v[2], v[3]),
        # 顶面 (z=+1)
        ((0, 0, 1), v[4], v[6], v[5]),
        ((0, 0, 1), v[4], v[7], v[6]),
        # 左面 (y=-1)
        ((0, -1, 0), v[0], v[4], v[5]),
        ((0, -1, 0), v[0], v[5], v[1]),
        # 右面 (y=+1)
        ((0, 1, 0), v[3], v[2], v[6]),
        ((0, 1, 0), v[3], v[6], v[7]),
        # 前面 (x=+1)
        ((1, 0, 0), v[1], v[5], v[6]),
        ((1, 0, 0), v[1], v[6], v[2]),
        # 后面 (x=-1)
        ((-1, 0, 0), v[0], v[3], v[7]),
        ((-1, 0, 0), v[0], v[7], v[4]),
    ]
    
    for normal, va, vb, vc in faces:
        triangles.append((normal, va, vb, vc))


def _add_wedge_triangles(
    triangles: list,
    x, y, z,
    length, width, height,
    angle_rad: float,
    side: str = 'left',
):
    """添加楔形 (引导斜面)"""
    dx = height * math.tan(angle_rad)
    
    v = [
        (x, y, z),
        (x + dx, y, z),
        (x + dx, y + width, z),
        (x, y + width, z),
        (x, y, z + height),
        (x + dx, y, z + height),
        (x + dx, y + width, z + height),
        (x, y + width, z + height),
    ]
    
    triangles.append(((0,0,-1), v[0], v[2], v[1]))
    triangles.append(((0,0,1), v[4], v[5], v[7]))
    triangles.append(((0,0,1), v[5], v[6], v[7]))
    triangles.append(((0,-1,0), v[0], v[1], v[5]))
    triangles.append(((0,-1,0), v[0], v[5], v[4]))
    triangles.append(((0,1,0), v[2], v[3], v[7]))
    triangles.append(((0,1,0), v[2], v[7], v[6]))
    if side == 'left':
        triangles.append(((1,0,0), v[0], v[4], v[3]))
        triangles.append(((1,0,0), v[0], v[3], v[2]))  # 斜面
    else:
        triangles.append(((-1,0,0), v[1], v[2], v[6]))
        triangles.append(((-1,0,0), v[1], v[6], v[5]))


# ═══ 集成到 cad_to_3d.py 的接口 ═══

def get_ram_lock_params_for_die_cut():
    """获取刀模活字印刷项目的RAM Lock参数"""
    return RAMLockParams(
        tenon_width=3.0,
        tenon_thickness=1.2,
        tenon_height=2.0,
        tenon_insert_angle=15,
        slot_width=3.3,
        slot_neck_width=1.5,
        slot_depth=2.3,
        latch_length=4.0,
        latch_width=1.0,
        latch_height=1.5,
        latch_spring_back=0.3,
        wall_thickness=1.2,
        tolerance=0.15,
    )


def integration_notes():
    """集成说明 — 如何替换 cad_to_3d.py 中的燕尾榫"""
    return """
=== RAM Lock 集成到 cad_to_3d.py ===

1. 替换 MODULE_PARAMS 中的连接参数:
   OLD: connector_size=5.0, connector_taper=15.0
   NEW: 使用 RAMLockParams

2. 替换 STLGenerator._add_dovetail() 为:
   def _add_ram_lock_tenon(self, ...):
       triangles = generate_ram_lock_tenon_triangles(...)
       self.triangles.extend(triangles)

3. 新增底座生成方法:
   def generate_base_plate(self, total_length, num_slots):
       # 底座 + T型卡槽
       slot_triangles = generate_ram_lock_slot_triangles(...)
       # 底座外形
       self._add_box(0, 0, 0, total_length, base_width, base_height)
       # 挖槽
       for offset in slot_offsets:
           self.triangles.extend(offset_triangles)

4. 插拔操作:
   - 安装: 一端先斜插入(15°角), 另一端按下, 卡扣自动锁定
   - 拆卸: 同时按下两侧卡扣, 向上抽出
   - 力度: PETG-CF打印, 卡扣弹性臂~0.3mm回弹

5. 打印建议:
   - 材料: PETG-CF (刚性+韧性)
   - 层高: 0.2mm
   - 填充: 卡扣区域 60%, 其他 40%
   - 方向: 卡扣臂沿Y轴打印 (跨层强度最大)
"""


if __name__ == "__main__":
    import struct
    
    params = get_ram_lock_params_for_die_cut()
    
    print("=== RAM Lock 连接器 ===\n")
    print("参数:")
    for k, v in vars(params).items():
        print(f"  {k}: {v}mm")
    
    # 生成测试STL (50mm直线模块)
    length = 50.0
    
    # 模块侧 (T型榫 + 卡扣)
    tenon_tris = generate_ram_lock_tenon_triangles(length, params)
    print(f"\n模块榫三角形: {len(tenon_tris)}")
    
    # 底座侧 (T型槽)
    slot_tris = generate_ram_lock_slot_triangles(length, params)
    print(f"底座槽三角形: {len(slot_tris)}")
    
    # 保存测试STL
    def save_stl(filepath, triangles, name):
        header_str = f"RAM Lock {name} - DieCut3D"
        header = header_str.encode() + b"\0" * (80 - len(header_str))
        data = bytearray(header)
        data.extend(struct.pack("<I", len(triangles)))
        for normal, v1, v2, v3 in triangles:
            data.extend(struct.pack("<fff", *normal))
            data.extend(struct.pack("<fff", *v1))
            data.extend(struct.pack("<fff", *v2))
            data.extend(struct.pack("<fff", *v3))
            data.extend(struct.pack("<H", 0))
        with open(filepath, "wb") as f:
            f.write(bytes(data))
        print(f"已保存: {filepath} ({len(triangles)} triangles)")
    
    out = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/output"
    save_stl(f"{out}/RAM_TENON_test.stl", tenon_tris, "Tenon")
    save_stl(f"{out}/RAM_SLOT_test.stl", slot_tris, "Slot")
    
    print(f"\n{integration_notes()}")
