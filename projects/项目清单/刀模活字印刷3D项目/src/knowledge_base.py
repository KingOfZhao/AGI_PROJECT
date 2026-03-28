"""
刀模活字印刷3D项目 — 知识库 (固定规则/标准/约束)
"""

IADD_STEEL_RULE_SPECS = {
    "blade_thickness": {
        "2pt": {"mm": 0.71, "inch": 0.028, "use": "精细设计、薄材料"},
        "3pt": {"mm": 1.07, "inch": 0.042, "use": "标准切割、中等材料"},
        "4pt": {"mm": 1.42, "inch": 0.056, "use": "厚材料、重型切割"},
        "6pt": {"mm": 2.13, "inch": 0.084, "use": "特厚材料"},
        "8pt": {"mm": 2.84, "inch": 0.112, "use": "极厚材料"},
    },
    "blade_height": {
        "standard_937": {"mm": 23.80, "inch": 0.937, "use": "平压模切机标准"},
        "22mm": {"mm": 22.0, "use": "日本/亚洲标准"},
        "30mm": {"mm": 30.0, "use": "加高刀"},
        "50mm": {"mm": 50.0, "use": "厚瓦楞"},
        "60mm": {"mm": 60.0, "use": "双瓦楞"},
        "80mm": {"mm": 80.0, "use": "三瓦楞/特殊"},
    },
    "bevel_types": {
        "CB": "中心斜角 — 通用", "LCB": "长中心斜角 — 厚材料",
        "SB": "侧斜角 — 薄膜", "LSB": "长侧斜角 — 精密",
    },
    "tolerance_mm": 0.254,
    "die_board": {
        "material": ["Baltic Birch Plywood", "Acrylic", "Composite"],
        "thickness_mm": [18, 19, 22],
        "slot_kerf_mm": 0.71,
    },
    "ejection_rubber": {
        "types": ["开孔泡沫", "闭孔泡沫", "硅胶"],
        "height_above_rule_mm": 1.5,
        "compression_ratio": 0.5,
    },
}

BAMBU_P1S_P2S = {
    "build_volume_mm": {"x": 256, "y": 256, "z": 256},
    "nozzle_mm": [0.2, 0.4, 0.6, 0.8],
    "layer_height_mm": {"min": 0.05, "max": 0.35, "rec": 0.20},
    "accuracy_mm": 0.15,
    "min_wall_mm": 0.8,
    "min_feature_mm": 0.4,
    "materials": [
        {"name": "PLA", "strength": "中", "cost": "低"},
        {"name": "PETG", "strength": "中高", "cost": "低"},
        {"name": "PETG-CF", "strength": "很高", "cost": "高"},
        {"name": "PA-Nylon", "strength": "很高", "cost": "中"},
        {"name": "ABS", "strength": "高", "cost": "中"},
        {"name": "PC", "strength": "很高", "cost": "高"},
    ],
    "best_for_die": "PETG-CF",
}

MOVABLE_TYPE = {
    "gutenberg_alloy": "Pb:Sn:Sb=82:9:9, mp=247°C",
    "type_high_mm": 23.317,  # ≈ IADD 23.8mm
    "principles": ["标准化", "可互换", "可复用", "组合无限", "可替换"],
    "huarong_dao": "受限空间排列优化 = 2D Bin Packing + Path Coverage",
}

CONNECTOR_SPECS = {
    "dovetail": {"width_mm": 5.0, "depth_mm": 3.0, "taper_deg": 15, "clearance_mm": 0.15},
    "pin": {"diameter_mm": 3.0, "depth_mm": 5.0, "clearance_mm": 0.1},
    "snap_fit": {"deflection_mm": 0.5, "beam_length_mm": 8.0},
}

PHYSICAL_LAWS = {
    "blade_kerf": "切割宽度=刀片厚度",
    "min_bend_radius": "R_min ≥ 3×刀片厚度",
    "slot_fit": "槽宽=刀片厚度+0.03mm过盈",
    "corner_radius": "R ≥ 刀片厚度",
    "print_resolution": "特征≥喷嘴直径(0.4mm)",
    "print_overhang": "悬空≤45°",
    "assembly_tolerance": "拼接间隙≈0.3mm",
}

MODULE_TYPES = [
    "STRAIGHT", "ARC", "CORNER_90", "CORNER_45", "CORNER_VAR",
    "T_JOINT", "CROSS_JOINT", "END_CAP", "BRIDGE", "EJECTOR_PAD", "BASE_TILE",
]
