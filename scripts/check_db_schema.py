import sqlite3
conn = sqlite3.connect("/Users/administruter/Desktop/AGI_PROJECT/memory.db")
c = conn.cursor()
for t in ["growth_log", "proven_nodes", "skills", "collision_history", "pcm", "skill_dependencies"]:
    try:
        c.execute(f"PRAGMA table_info({t})")
        cols = c.fetchall()
        print(f"\n{t}:")
        for col in cols:
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"\n{t}: ERROR {e}")
conn.close()
