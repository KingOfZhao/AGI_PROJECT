"""查看最近对话记录，分析文件产出能力"""
import sqlite3, json, sys
sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT')

db = sqlite3.connect('/Users/administruter/Desktop/AGI_PROJECT/memory.db')
db.row_factory = sqlite3.Row

# 查看最近20条对话
print("=" * 80)
print("最近20条对话记录")
print("=" * 80)
rows = db.execute("""
    SELECT id, session_id, role, substr(content, 1, 200) as content_preview, 
           metadata, created_at
    FROM chat_history 
    ORDER BY id DESC 
    LIMIT 20
""").fetchall()

for r in reversed(rows):
    meta = json.loads(r['metadata']) if r['metadata'] else {}
    mode = meta.get('mode', '')
    has_actions = 'actions' in str(meta)
    fast_path = meta.get('fast_path', False)
    print(f"\n[{r['created_at']}] session={r['session_id']} role={r['role']} mode={mode}")
    print(f"  内容: {r['content_preview']}")
    if has_actions:
        print(f"  ** 包含actions元数据 **")
    if fast_path:
        print(f"  ** fast_path=True **")

# 查看包含action结果的对话
print("\n" + "=" * 80)
print("包含action执行结果的对话（最近10条）")
print("=" * 80)
rows2 = db.execute("""
    SELECT id, session_id, role, substr(content, 1, 300) as content_preview,
           metadata, created_at
    FROM chat_history 
    WHERE metadata LIKE '%action%' OR content LIKE '%创建文件%' OR content LIKE '%文件已创建%'
       OR content LIKE '%create_file%' OR content LIKE '%execute_python%'
    ORDER BY id DESC 
    LIMIT 10
""").fetchall()

if rows2:
    for r in reversed(rows2):
        print(f"\n[{r['created_at']}] session={r['session_id']} role={r['role']}")
        print(f"  内容: {r['content_preview']}")
else:
    print("  没有找到包含action执行记录的对话")

# 统计各模式使用情况
print("\n" + "=" * 80)
print("对话模式使用统计")
print("=" * 80)
rows3 = db.execute("""
    SELECT metadata, COUNT(*) as cnt
    FROM chat_history 
    WHERE role='user'
    GROUP BY 1
    ORDER BY cnt DESC
    LIMIT 20
""").fetchall()

mode_counts = {}
for r in rows3:
    try:
        meta = json.loads(r['metadata']) if r['metadata'] else {}
        m = meta.get('mode', 'unknown')
    except:
        m = 'unknown'
    mode_counts[m] = mode_counts.get(m, 0) + r['cnt']

for m, c in sorted(mode_counts.items(), key=lambda x: -x[1]):
    print(f"  {m}: {c}次")

db.close()
