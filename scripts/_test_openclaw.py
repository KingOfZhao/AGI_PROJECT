#!/usr/bin/env python3
"""端到端测试: OpenClaw能力集成"""
import sys, time, json
sys.path.insert(0, '.')

print("=" * 60)
print("  OpenClaw 能力集成测试")
print("=" * 60)

# ---- Test 1: MMR重排 ----
print("\n[测试1] MMR多样性重排")
from workspace.skills.openclaw_abilities import mmr_rerank

items = [
    {"content": "Python列表推导式是简洁的循环替代", "similarity": 0.9},
    {"content": "Python列表推导式用于快速创建列表", "similarity": 0.88},
    {"content": "Python字典推导式与列表推导式类似", "similarity": 0.85},
    {"content": "Flask是Python轻量级Web框架", "similarity": 0.82},
    {"content": "Python的装饰器模式用于函数增强", "similarity": 0.80},
]

result_diverse = mmr_rerank(items, lam=0.5)
result_relevant = mmr_rerank(items, lam=1.0)
print(f"  原始顺序: {[i['content'][:15] for i in items]}")
print(f"  λ=1.0(纯相关): {[i['content'][:15] for i in result_relevant]}")
print(f"  λ=0.5(多样性): {[i['content'][:15] for i in result_diverse]}")
# λ=1.0应该保持原始排序（纯相关性）
assert result_relevant[0]['similarity'] >= result_relevant[1]['similarity'], "λ=1.0应按分数降序"
# λ=0.5应该在前3个结果中引入多样性（Flask或装饰器）
diverse = any('Flask' in r['content'] or '装饰器' in r['content'] for r in result_diverse[:3])
assert diverse, "λ=0.5应该在前3个结果中引入多样性"
# 验证第一个结果仍是最高分的
assert result_diverse[0]['content'].startswith('Python列表推导式是')
print("  ✅ MMR正确：λ=1.0保序，λ=0.5引入多样性")

# ---- Test 2: 时间衰减 ----
print("\n[测试2] 时间衰减")
from workspace.skills.openclaw_abilities import temporal_decay_multiplier, apply_temporal_decay

# 半衰期30天
m0 = temporal_decay_multiplier(0, 30)
m30 = temporal_decay_multiplier(30, 30)
m60 = temporal_decay_multiplier(60, 30)
print(f"  0天: {m0:.3f}, 30天: {m30:.3f}, 60天: {m60:.3f}")
assert abs(m0 - 1.0) < 0.001, "0天应该是1.0"
assert abs(m30 - 0.5) < 0.001, "30天应该是0.5"
assert abs(m60 - 0.25) < 0.001, "60天应该是0.25"
print("  ✅ 衰减曲线正确")

# ---- Test 3: 查询扩展 ----
print("\n[测试3] 查询扩展")
from workspace.skills.openclaw_abilities import expand_query

r1 = expand_query("如何用Python实现快速排序")
print(f"  输入: '如何用Python实现快速排序'")
print(f"  关键词: {r1['keywords_en'] + r1['keywords_cn']}")
print(f"  领域: {r1['domain_hints']}")
assert 'python' in r1['keywords_en'], "应该提取python"
assert 'python' in r1['domain_hints'], "应该检测到python领域"
print("  ✅ 查询扩展正确")

r2 = expand_query("that thing we discussed about Flutter state management")
print(f"  输入: 'that thing we discussed about Flutter state management'")
print(f"  关键词: {r2['keywords_en']}")
print(f"  领域: {r2['domain_hints']}")
assert 'flutter' in r2['keywords_en'], "应该提取flutter"
assert 'dart' in r2['domain_hints'], "应该检测到dart领域"
print("  ✅ 英文查询扩展正确")

# ---- Test 4: 可验证性分类 ----
print("\n[测试4] 可验证性分类")
from workspace.skills.openclaw_abilities import classify_verifiability

v1 = classify_verifiability("run pytest and check all tests pass")
v2 = classify_verifiability("如何实现完美的微服务架构")
v3 = classify_verifiability("execute `pip install flask` in terminal")
print(f"  'run pytest...' → {v1['classification']} (具体{v1['concrete_score']}/抽象{v1['abstract_score']})")
print(f"  '如何实现完美...' → {v2['classification']} (具体{v2['concrete_score']}/抽象{v2['abstract_score']})")
print(f"  'execute pip...' → {v3['classification']} (具体{v3['concrete_score']}/抽象{v3['abstract_score']})")
assert v1['can_verify'] == True, "具体动作应该可验证"
assert v2['can_verify'] == False, "抽象目标应该不可验证"
assert v3['can_verify'] == True, "包含命令应该可验证"
print("  ✅ 可验证性分类正确")

# ---- Test 5: 增强搜索管道 ----
print("\n[测试5] 增强搜索管道")
from workspace.skills.openclaw_abilities import enhanced_search

mock_results = [
    {"content": "Python的GIL全局解释器锁限制多线程", "similarity": 0.85},
    {"content": "Python的GIL使得CPU密集型任务无法并行", "similarity": 0.83},
    {"content": "Python多进程可以绕过GIL限制", "similarity": 0.80},
    {"content": "asyncio是Python的异步IO框架", "similarity": 0.75},
]

result = enhanced_search("Python GIL是什么", mock_results, apply_mmr=True)
print(f"  查询关键词: {result['stats']['keywords']}")
print(f"  结果数: {result['stats']['total_results']}")
print(f"  MMR应用: {result['stats']['mmr_applied']}")
print(f"  重排结果: {[r['content'][:20] for r in result['results']]}")
assert result['stats']['total_results'] == 4
assert 'python' in result['stats']['keywords']
print("  ✅ 增强搜索管道正确")

# ---- Summary ----
print("\n" + "=" * 60)
print("  全部测试通过! ✅ 5/5")
print("=" * 60)
