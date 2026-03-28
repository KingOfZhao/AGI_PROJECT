#!/usr/bin/env python3
"""测试问题过滤器"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from deduction_runner import is_valid_problem, classify_problem

# 应该被过滤的垃圾
garbage = [
    '**:',
    '问题',
    '>',
    'dquote>',
    'quote>',
    ')>',
    '}>',
    '',
    '  ',
    '::',
    'File not found: {self.filepath}")',
    'Invalid DXF structure: {self.filepath}")',
    'raise ValueError(f"No parser for {ext}")',
]

# 应该通过的有效问题
valid = [
    'PDF流式数据的语义丢失',
    '缺乏行业通用颜色-工艺对照表标准',
    '光栅PDF矢量还原 (需引入CV引擎)',
    '缺少PDF矢量流的图形状态机模拟验证',
    '缺乏通用的刀模DXF图层命名工业标准数据',
    '手绘草图识别 (非矢量输入)',
    'PDF复杂嵌套CTM变换矩阵的通用鲁棒解析算法缺失',
    'OLLAMA_URL未定义导致Playwright+LLM验证链路物理断裂',
]

print("=== GARBAGE (should all be REJECTED) ===")
all_ok = True
for g in garbage:
    result = is_valid_problem(g)
    status = "REJECT" if not result else "PASS(BUG!)"
    if result:
        all_ok = False
    print(f"  {status:12s} {repr(g)[:60]}")

print(f"\n=== VALID (should all be ACCEPTED) ===")
for v in valid:
    result = is_valid_problem(v)
    status = "ACCEPT" if result else "REJECT(BUG!)"
    if not result:
        all_ok = False
    print(f"  {status:12s} {repr(v)[:60]}")

print(f"\n{'ALL TESTS PASSED' if all_ok else 'SOME TESTS FAILED!'}")

# Test classify_problem title cleaning
print("\n=== TITLE CLEANING ===")
plan = {'id': 'test', 'title': '刀模图解析引擎', 'project_id': 'p_diepre'}
cases = [
    '**PDF光栅化内容识别**',
    '光栅化PDF的矢量还原**:',
    '`CTM变换矩阵`解析缺失',
    '**缺乏行业标准**:',
]
for c in cases:
    prob = classify_problem(c, plan, 'decompose', '')
    if prob:
        print(f"  IN:  {c}")
        print(f"  OUT: {prob['title']}")
        print(f"  SEV: {prob['severity']} CAT: {prob['description'].split('分类: ')[1].split(' |')[0]}")
        print()
