#!/usr/bin/env python3
"""快速验证 pacdora_import.py 的数据库建表、插入、查询、状态更新逻辑"""

import os, sys, json, sqlite3, tempfile

# 导入目标模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pacdora_import as pi

# 使用临时DB
tmp_db = os.path.join(tempfile.gettempdir(), "test_pacdora_v2.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)
pi.DB_PATH = tmp_db

errors = []

# ─── Test 1: 建表 ───
print("Test 1: 建表...")
try:
    conn = pi.init_db(tmp_db)
    cols = conn.execute("PRAGMA table_info(pacdora_items)").fetchall()
    col_names = [c[1] for c in cols]
    print(f"  ✓ 建表成功, {len(cols)} 列")
    assert "knife_status" in col_names, "缺少 knife_status"
    assert "image_status" in col_names, "缺少 image_status"
    assert "num" in col_names, "缺少 num"
    assert "class2Bymodel" in col_names, "缺少 class2Bymodel"
    assert "modeSetting" in col_names, "缺少 modeSetting"
    print(f"  ✓ 关键列验证通过")
except Exception as e:
    errors.append(f"Test 1 FAIL: {e}")
    print(f"  ✗ {e}")

# ─── Test 2: 插入 ───
print("Test 2: 插入...")
try:
    test_item = {
        "id": 1, "num": 150010, "name": "翻盖礼品盒", "showName": "翻盖礼品盒",
        "mockupName": "翻盖礼品盒", "nameKey": "test-dieline-150010",
        "mockupNameKey": "test-mockup-150010",
        "class1": "(218)", "class2": "(229)", "class3": "",
        "class2Bymodel": "折叠盒", "anchorName": "折叠盒",
        "class2Namekey": "折叠盒", "class2DielineNamekey": "folding-box-dielines",
        "class2MockupNamekey": "folding-box-mockups",
        "cate_id": 1, "def_science_id": 5,
        "length": 315, "width": 202, "height": 62,
        "sort": 99999999, "is_enterprise": 0, "use_count": 100000000,
        "knife": "https://oss.pacdora.cn/preview/dieline-150010.png",
        "image": "https://oss.pacdora.cn/preview/mockup-150010.jpg",
        "keywords": "150010,盒子", "modelKeywords": "150010,盒子",
        "usageKeywords": "", "styleKeywords": "", "productKeywords": "",
        "tags": ["150010", "盒子", "折叠盒"],
        "blankTitle": "blank", "blankAlt": "alt",
        "dielinesTitle": "dl", "dielinesAlt": "da",
        "svgTitle": "svg", "svgAlt": "sa",
        "description": "测试描述",
        "cate_info": {"cate_no": "150010", "complex_type": 0},
        "modeSetting": [{"id": 30762, "material": "FLUTE"}],
        "liked": None,
        "demoProjectDataUrl": "https://cloud.pacdora.com/demoProject/150010.json",
        "create_time": "1584420637182", "update_time": "1750406418940"
    }
    is_new = pi.upsert_item(conn, test_item)
    conn.commit()
    assert is_new, "应为新增"
    print(f"  ✓ 新增成功")
except Exception as e:
    errors.append(f"Test 2 FAIL: {e}")
    print(f"  ✗ {e}")
    import traceback; traceback.print_exc()

# ─── Test 3: 查询 ───
print("Test 3: 查询...")
try:
    row = conn.execute("SELECT num, name, knife_status, image_status, class2Bymodel FROM pacdora_items WHERE num=150010").fetchone()
    assert row is not None, "查不到记录"
    assert row[0] == 150010
    assert row[1] == "翻盖礼品盒"
    assert row[2] == "pending"
    assert row[3] == "pending"
    assert row[4] == "折叠盒"
    print(f"  ✓ 查询: num={row[0]}, name={row[1]}, knife_status={row[2]}, category={row[4]}")
except Exception as e:
    errors.append(f"Test 3 FAIL: {e}")
    print(f"  ✗ {e}")

# ─── Test 4: 更新(upsert) ───
print("Test 4: 更新(upsert)...")
try:
    test_item["name"] = "翻盖礼品盒V2"
    is_new = pi.upsert_item(conn, test_item)
    conn.commit()
    assert not is_new, "应为更新"
    row = conn.execute("SELECT name FROM pacdora_items WHERE num=150010").fetchone()
    assert row[0] == "翻盖礼品盒V2"
    print(f"  ✓ 更新成功: name={row[0]}")
except Exception as e:
    errors.append(f"Test 4 FAIL: {e}")
    print(f"  ✗ {e}")

# ─── Test 5: 状态更新 ───
print("Test 5: 状态更新...")
try:
    conn.execute("UPDATE pacdora_items SET knife_status='downloaded', knife_local='/tmp/test.png' WHERE num=150010")
    conn.commit()
    row = conn.execute("SELECT knife_status, knife_local FROM pacdora_items WHERE num=150010").fetchone()
    assert row[0] == "downloaded"
    assert row[1] == "/tmp/test.png"
    print(f"  ✓ knife_status={row[0]}, knife_local={row[1]}")
except Exception as e:
    errors.append(f"Test 5 FAIL: {e}")
    print(f"  ✗ {e}")

# ─── Test 6: 统计查询 ───
print("Test 6: 统计查询...")
try:
    stats = conn.execute("""SELECT COUNT(*),
        SUM(CASE WHEN knife_status='downloaded' THEN 1 ELSE 0 END),
        SUM(CASE WHEN knife_status='pending' THEN 1 ELSE 0 END),
        SUM(CASE WHEN image_status='pending' THEN 1 ELSE 0 END)
        FROM pacdora_items""").fetchone()
    assert stats[0] == 1
    assert stats[1] == 1  # downloaded
    assert stats[2] == 0  # pending
    assert stats[3] == 1  # image still pending
    print(f"  ✓ total={stats[0]}, knife_downloaded={stats[1]}, image_pending={stats[3]}")
except Exception as e:
    errors.append(f"Test 6 FAIL: {e}")
    print(f"  ✗ {e}")

# ─── Test 7: 旧表迁移 ───
print("Test 7: 旧表迁移兼容...")
try:
    tmp_db2 = os.path.join(tempfile.gettempdir(), "test_pacdora_migration.db")
    if os.path.exists(tmp_db2): os.remove(tmp_db2)
    # 创建旧schema的表
    c2 = sqlite3.connect(tmp_db2)
    c2.execute("""CREATE TABLE pacdora_items (
        id INTEGER PRIMARY KEY, api_id INTEGER, num INTEGER UNIQUE,
        name TEXT, knife_url TEXT, image_url TEXT)""")
    c2.execute("INSERT INTO pacdora_items VALUES (1, 1, 999, 'old', 'url1', 'url2')")
    c2.commit()
    c2.close()
    # 用新脚本打开 → 应自动迁移
    c3 = pi.init_db(tmp_db2)
    # 旧表应被备份
    backup = c3.execute("SELECT COUNT(*) FROM pacdora_items_v1_backup").fetchone()[0]
    assert backup == 1, "旧表数据未备份"
    # 新表应为空
    new_count = c3.execute("SELECT COUNT(*) FROM pacdora_items").fetchone()[0]
    assert new_count == 0, "新表应为空"
    c3.close()
    os.remove(tmp_db2)
    print(f"  ✓ 旧表自动迁移成功, 备份{backup}条数据")
except Exception as e:
    errors.append(f"Test 7 FAIL: {e}")
    print(f"  ✗ {e}")

# ─── 清理 ───
conn.close()
if os.path.exists(tmp_db): os.remove(tmp_db)

# ─── 结果 ───
print(f"\n{'='*40}")
if errors:
    print(f"  ✗ {len(errors)} 个测试失败:")
    for e in errors:
        print(f"    - {e}")
else:
    print("  ✅ 全部 7 个测试通过!")
print(f"{'='*40}")
