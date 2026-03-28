#!/usr/bin/env python3
"""检查推演数据库中的所有问题和步骤"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deduction.db")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=== ALL BLOCKED PROBLEMS ===")
rows = conn.execute(
    "SELECT id, title, description, severity, status, plan_id, project_id, "
    "suggested_solution, created_at FROM blocked_problems ORDER BY id"
).fetchall()
for r in rows:
    print(f"#{r['id']} [{r['status']}] sev={r['severity']} proj={r['project_id']}")
    print(f"  title: {r['title']}")
    print(f"  desc:  {r['description'][:300]}")
    print(f"  sol:   {(r['suggested_solution'] or '')[:200]}")
    print()

print(f"Total problems: {len(rows)}")
print()

print("=== DEDUCTION STEPS ===")
rows2 = conn.execute(
    "SELECT plan_id, step_number, phase, model_used, tokens_used, "
    "substr(response,1,300) as preview FROM deduction_steps "
    "ORDER BY plan_id, step_number"
).fetchall()
for r in rows2:
    print(f"  {r['plan_id']} step={r['step_number']} {r['phase']} "
          f"{r['model_used']} {r['tokens_used']}tok")
    prev = r['preview'].replace('\n', ' ')[:200]
    print(f"    {prev}")
    print()

print("=== NODES EXTRACTED ===")
rows3 = conn.execute(
    "SELECT id, plan_id, node_type, name, confidence, truth_level "
    "FROM deduction_nodes ORDER BY plan_id, id"
).fetchall()
for r in rows3:
    print(f"  #{r['id']} [{r['node_type']}] {r['name']} "
          f"conf={r['confidence']} truth={r['truth_level']}")

print(f"\nTotal nodes: {len(rows3)}")
conn.close()
