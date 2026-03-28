"""v7.0 节点真实性分级模块集成测试"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)


import sys
sys.path.insert(0, "/Users/administruter/Desktop/AGI_PROJECT")

from diepre_growth_framework import NodeTruthClassifier, ComputeOptimizer

# === Test 1: L1 本体真实 (标准/定律/算法关键词) ===
node1 = {"content": "ISO 9001标准在质量管理中的应用", "type": "hypothesis", "confidence": 0.8, "domain": "quality"}
r1 = NodeTruthClassifier.classify(node1)
assert r1["truth_level"] >= 1, f"ISO node should be L1+, got L{r1['truth_level']}"
print("Test1 PASS: ISO node -> %s (L%d)" % (r1["truth_label"], r1["truth_level"]))

# === Test 2: L1 本体真实 (API/组件关键词) ===
node2 = {"content": "React组件的状态管理", "type": "hypothesis", "confidence": 0.7, "domain": "frontend"}
r2 = NodeTruthClassifier.classify(node2)
assert r2["truth_level"] >= 1, f"React node should be L1+, got L{r2['truth_level']}"
print("Test2 PASS: React node -> %s (L%d)" % (r2["truth_label"], r2["truth_level"]))

# === Test 3: L1 本体真实 (算法关键词) ===
node3 = {"content": "使用Dijkstra算法实现最短路径", "type": "proven", "confidence": 0.9, "domain": "algorithms"}
r3 = NodeTruthClassifier.classify(node3)
assert r3["truth_level"] >= 1, f"Dijkstra node should be L1+, got L{r3['truth_level']}"
print("Test3 PASS: Dijkstra node -> %s (L%d)" % (r3["truth_label"], r3["truth_level"]))

# === Test 4: L2 关系真实 (跨域碰撞) ===
node4 = {"content": "单一职责原则在多领域的应用", "type": "proven", "confidence": 0.75, "domain": "design"}
ctx4 = {"cross_domain_count": 3}
r4 = NodeTruthClassifier.classify(node4, ctx4)
assert r4["truth_level"] >= 2, f"Cross-domain node should be L2+, got L{r4['truth_level']}"
print("Test4 PASS: Cross-domain node -> %s (L%d)" % (r4["truth_label"], r4["truth_level"]))

# === Test 5: L3 能力真实 (测试通过) ===
node5 = {"content": "HTTP请求处理模块", "type": "proven", "confidence": 0.85, "domain": "backend"}
ctx5 = {"test_passed": True}
r5 = NodeTruthClassifier.classify(node5, ctx5)
assert r5["truth_level"] >= 3, f"Test-passed node should be L3+, got L{r5['truth_level']}"
print("Test5 PASS: Test-passed node -> %s (L%d)" % (r5["truth_label"], r5["truth_level"]))

# === Test 6: deprecated (低置信度) ===
node6 = {"content": "已过时的假说", "type": "deprecated", "confidence": 0.05, "domain": "general"}
r6 = NodeTruthClassifier.classify(node6)
assert r6["truth_level"] == -1, f"Deprecated node should be L-1, got L{r6['truth_level']}"
print("Test6 PASS: Deprecated node -> %s (L%d)" % (r6["truth_label"], r6["truth_level"]))

# === Test 7: L5 进化真实 (证伪幸存) ===
node7 = {"content": "经过多轮验证的核心原则", "type": "proven", "confidence": 0.95, "domain": "core", "verify_count": 15}
ctx7 = {"falsify_survived": 6, "convergence_sigma": 0.005}
r7 = NodeTruthClassifier.classify(node7, ctx7)
assert r7["truth_level"] >= 5, f"Evolutionary node should be L5, got L{r7['truth_level']}"
print("Test7 PASS: Evolutionary node -> %s (L%d)" % (r7["truth_label"], r7["truth_level"]))

# === Test 8: batch_classify ===
nodes = [node1, node2, node3, node4, node5, node6, node7]
ctxs = {node4.get("id", ""): ctx4, node5.get("id", ""): ctx5, node7.get("id", ""): ctx7}
batch = NodeTruthClassifier.batch_classify(nodes, ctxs)
stats = batch["stats"]
print("Test8 PASS: Batch stats: total=%d, avg_level=%.2f" % (stats["total"], stats["avg_level"]))

# === Test 9: ComputeOptimizer ===
co = ComputeOptimizer()
assert co.get_token_budget(0) == 4096, "L0 should be 4096"
assert co.get_token_budget(3) == 9830, "L3 should be 9830"
assert co.should_generate_skill({"truth_level": 0, "confidence": 0.4}) == False
assert co.should_generate_skill({"truth_level": 3, "confidence": 0.9}) == True
print("Test9 PASS: ComputeOptimizer token budgets and skill filtering OK")

print("\n=== All 9 tests passed! v7.0 modules working correctly ===")
