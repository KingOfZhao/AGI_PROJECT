#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dart & Flutter 全领域知识注入脚本
将 _dart_nodes_data.py 中定义的节点和关系注入认知格数据库
"""

import sys, json, sqlite3, time, struct, uuid
import numpy as np
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "memory.db"
sys.path.insert(0, str(Path(__file__).parent))

from _dart_nodes_data import DART_CORE_NODES, FLUTTER_WIDGET_NODES, FLUTTER_ADVANCED_NODES, RELATIONS
import agi_v13_cognitive_lattice as agi


def get_embedding_blob(text):
    """使用系统同一embedding方法，确保格式一致"""
    try:
        return agi.get_embedding(text)
    except Exception as e:
        print(f"  ⚠ embedding失败: {e}")
        return None


def inject_nodes(conn):
    """注入所有节点"""
    c = conn.cursor()
    all_nodes = DART_CORE_NODES + FLUTTER_WIDGET_NODES + FLUTTER_ADVANCED_NODES
    
    injected = 0
    skipped = 0
    total = len(all_nodes)
    
    print(f"\n{'='*60}")
    print(f"  注入 Dart/Flutter 知识节点 ({total} 个)")
    print(f"{'='*60}\n")
    
    for i, (domain, content) in enumerate(all_nodes):
        # 检查是否已存在（基于内容前40字符匹配）
        content_prefix = content[:40]
        c.execute("SELECT id FROM cognitive_nodes WHERE content LIKE ?", (content_prefix + '%',))
        existing = c.fetchone()
        
        if existing:
            # 更新已有节点为proven并加深内容
            c.execute("""UPDATE cognitive_nodes 
                        SET status='proven', content=?, domain=?, 
                            last_verified_at=?, verified_source='dart_flutter_injection'
                        WHERE id=?""",
                     (content, domain, datetime.now().isoformat(), existing[0]))
            skipped += 1
            status_char = "↑"
        else:
            # 生成embedding (使用系统同一方法)
            print(f"  [{i+1}/{total}] 生成embedding: {content[:50]}...")
            blob = get_embedding_blob(content)
            
            c.execute("""INSERT INTO cognitive_nodes 
                        (content, domain, status, created_at, 
                         last_verified_at, embedding, verified_source)
                        VALUES (?, ?, 'proven', ?, ?, ?, 'dart_flutter_injection')""",
                     (content, domain,
                      datetime.now().isoformat(),
                      datetime.now().isoformat(),
                      blob))
            injected += 1
            status_char = "+"
        
        # 进度
        pct = (i + 1) / total * 100
        bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
        print(f"\r  {bar} {pct:5.1f}% [{status_char}] {domain}: {content[:40]}...", end="", flush=True)
    
    conn.commit()
    print(f"\n\n  ✓ 新注入: {injected} 个节点")
    print(f"  ↑ 更新: {skipped} 个节点")
    return injected + skipped


def inject_relations(conn):
    """注入节点间关系"""
    c = conn.cursor()
    
    print(f"\n{'='*60}")
    print(f"  注入 Dart/Flutter 知识关系 ({len(RELATIONS)} 条)")
    print(f"{'='*60}\n")
    
    injected = 0
    failed = 0
    
    for src_kw, tgt_kw, rel_type, strength in RELATIONS:
        # 模糊匹配源节点
        c.execute("SELECT id, content FROM cognitive_nodes WHERE content LIKE ? LIMIT 1",
                 (f"%{src_kw}%",))
        src = c.fetchone()
        
        # 模糊匹配目标节点
        c.execute("SELECT id, content FROM cognitive_nodes WHERE content LIKE ? LIMIT 1",
                 (f"%{tgt_kw}%",))
        tgt = c.fetchone()
        
        if not src or not tgt:
            failed += 1
            miss = "src" if not src else "tgt"
            kw = src_kw if not src else tgt_kw
            print(f"  ⚠ 未找到{miss}: {kw}")
            continue
        
        # 检查是否已存在
        c.execute("""SELECT id FROM node_relations 
                    WHERE node1_id=? AND node2_id=? AND relation_type=?""",
                 (src[0], tgt[0], rel_type))
        if c.fetchone():
            continue
        
        c.execute("""INSERT INTO node_relations 
                    (node1_id, node2_id, relation_type, confidence, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 (src[0], tgt[0], rel_type, strength,
                  f"{src_kw} -> {tgt_kw}",
                  datetime.now().isoformat()))
        injected += 1
        print(f"  + [{rel_type}] {src_kw[:30]} → {tgt_kw[:30]} ({strength})")
    
    conn.commit()
    print(f"\n  ✓ 新关系: {injected} 条")
    print(f"  ⚠ 未匹配: {failed} 条")
    return injected


def fix_missing_embeddings(conn):
    """为缺少embedding的Dart/Flutter节点补充"""
    c = conn.cursor()
    c.execute("""SELECT id, content FROM cognitive_nodes 
                WHERE (domain LIKE '%Dart%' OR domain LIKE '%Flutter%')
                AND embedding IS NULL""")
    missing = c.fetchall()
    
    if not missing:
        print("\n  ✓ 所有Dart/Flutter节点已有embedding")
        return 0
    
    print(f"\n  补充 {len(missing)} 个节点的embedding...")
    fixed = 0
    for node_id, content in missing:
        blob = get_embedding_blob(content)
        if blob:
            c.execute("UPDATE cognitive_nodes SET embedding=? WHERE id=?", (blob, node_id))
            fixed += 1
            print(f"  ✓ embedding: {content[:50]}...")
    
    conn.commit()
    print(f"  ✓ 补充完成: {fixed}/{len(missing)}")
    return fixed


def verify_results(conn):
    """验证注入结果"""
    c = conn.cursor()
    
    print(f"\n{'='*60}")
    print(f"  验证结果")
    print(f"{'='*60}\n")
    
    # 按domain统计
    c.execute("""SELECT domain, COUNT(*), 
                 SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) as has_emb
                FROM cognitive_nodes 
                WHERE domain LIKE '%Dart%' OR domain LIKE '%Flutter%'
                GROUP BY domain ORDER BY domain""")
    
    total_nodes = 0
    total_emb = 0
    for domain, count, has_emb in c.fetchall():
        total_nodes += count
        total_emb += has_emb
        emb_pct = has_emb / count * 100
        print(f"  {domain:30s}  {count:3d} 节点  embedding:{has_emb}/{count} ({emb_pct:.0f}%)")
    
    # 关系统计
    c.execute("""SELECT relation_type, COUNT(*) FROM node_relations nr
                JOIN cognitive_nodes s ON nr.node1_id=s.id
                JOIN cognitive_nodes t ON nr.node2_id=t.id
                WHERE (s.domain LIKE '%Dart%' OR s.domain LIKE '%Flutter%')
                AND (t.domain LIKE '%Dart%' OR t.domain LIKE '%Flutter%')
                GROUP BY relation_type""")
    
    print(f"\n  关系统计:")
    total_rels = 0
    for rel_type, count in c.fetchall():
        total_rels += count
        print(f"    {rel_type:20s}  {count:3d} 条")
    
    # 整体统计
    c.execute("SELECT status, COUNT(*) FROM cognitive_nodes GROUP BY status")
    print(f"\n  全局节点统计:")
    for status, count in c.fetchall():
        print(f"    {status:12s}  {count:4d}")
    
    print(f"\n  {'─'*40}")
    print(f"  Dart/Flutter 节点总计: {total_nodes}")
    print(f"  Dart/Flutter 关系总计: {total_rels}")
    print(f"  Embedding 覆盖率: {total_emb}/{total_nodes} ({total_emb/max(total_nodes,1)*100:.0f}%)")


def main():
    print("=" * 60)
    print("  Dart & Flutter 全领域知识注入")
    print("  目标: 构建完整的 Dart/Flutter 认知网络")
    print("=" * 60)
    
    conn = sqlite3.connect(str(DB_PATH))
    
    try:
        # 1. 注入节点
        node_count = inject_nodes(conn)
        
        # 2. 注入关系
        rel_count = inject_relations(conn)
        
        # 3. 补充embedding
        fix_missing_embeddings(conn)
        
        # 4. 验证
        verify_results(conn)
        
        print(f"\n{'='*60}")
        print(f"  ✅ Dart/Flutter 知识注入完成!")
        print(f"{'='*60}\n")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
