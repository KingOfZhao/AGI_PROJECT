#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10次复杂能力验证脚本
立即执行，验证Orchestrator的复杂问题处理能力
验证过程中产生的临时文件会自动删除
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)


import json, time, os, sys, traceback, tempfile, shutil
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agi_v13_cognitive_lattice as agi
import orchestrator as orch_module

# 10个高难度验证问题
CAPABILITY_TESTS = [
    {
        "id": 1,
        "name": "分布式事务一致性",
        "prompt": "请详细设计一个分布式事务框架，需要同时支持TCC（Try-Confirm-Cancel）和SAGA两种模式。要求：1)给出完整的状态机设计 2)事务协调器的核心算法伪代码 3)超时补偿策略 4)数据一致性证明 5)并发冲突解决方案。请用结构化方式输出，每个部分都要有完整的技术细节。",
        "verify_keywords": ["TCC", "SAGA", "补偿", "状态机", "一致性", "超时"],
        "min_length": 500,
    },
    {
        "id": 2,
        "name": "Transformer从零实现",
        "prompt": "请从零开始用Python/PyTorch实现一个完整的Transformer模型。要求包含：1)Multi-Head Attention完整代码 2)Position Encoding 3)Feed-Forward Network 4)Layer Normalization 5)Encoder和Decoder完整实现 6)训练循环代码 7)每一步的数学公式和维度标注。不要使用nn.Transformer，全部手写。",
        "verify_keywords": ["attention", "softmax", "encoder", "decoder", "forward"],
        "min_length": 800,
    },
    {
        "id": 3,
        "name": "B+树完整实现",
        "prompt": "请用Python完整实现一个B+树，要求：1)插入操作（含节点分裂）2)删除操作（含节点合并和借位）3)范围查询 4)点查询 5)序列化/反序列化到磁盘 6)并发读写安全（读写锁）7)完整的单元测试。请给出完整可运行的代码。",
        "verify_keywords": ["class", "insert", "delete", "search", "split", "merge"],
        "min_length": 600,
    },
    {
        "id": 4,
        "name": "微服务架构设计",
        "prompt": "请为一个千万级用户的电商平台设计完整的微服务架构。要求：1)服务拆分方案（至少15个服务）2)服务间通信协议选择（同步/异步）3)数据库拆分和数据一致性方案 4)缓存策略（多级缓存）5)限流熔断降级策略 6)分布式事务处理 7)监控告警体系 8)容灾和高可用方案。每个部分要有具体的技术选型和原因。",
        "verify_keywords": ["微服务", "数据库", "缓存", "限流", "熔断", "监控"],
        "min_length": 600,
    },
    {
        "id": 5,
        "name": "编译器前端实现",
        "prompt": "请用Python实现一个完整的编译器前端，目标语言是一个简化版的类C语言。要求：1)词法分析器（支持标识符、数字、字符串、运算符、关键字）2)递归下降语法解析器（支持变量声明、赋值、if-else、while、函数定义和调用）3)AST数据结构定义 4)语义分析（类型检查、作用域分析）5)符号表管理 6)错误报告（行号、列号）。给出完整可运行代码。",
        "verify_keywords": ["class", "token", "parse", "AST", "def", "return"],
        "min_length": 700,
    },
    {
        "id": 6,
        "name": "分布式一致性算法",
        "prompt": "请详细解释并用Python实现Raft共识算法的核心部分。要求：1)Leader选举算法及完整状态转换 2)日志复制机制 3)安全性保证的数学证明 4)成员变更（Joint Consensus）5)日志压缩和快照 6)客户端交互协议。给出完整的伪代码或Python实现，并解释每个关键决策点。",
        "verify_keywords": ["Raft", "leader", "follower", "candidate", "log", "commit"],
        "min_length": 600,
    },
    {
        "id": 7,
        "name": "神经网络优化器数学推导",
        "prompt": "请完整推导以下优化器的数学原理和实现：1)SGD with Momentum - 动量的物理直觉和数学推导 2)Adam - 一阶矩和二阶矩估计的推导，偏差校正的原因 3)AdamW - 权重衰减与L2正则的区别证明 4)LAMB - 层自适应学习率的推导 5)用Python/NumPy从零实现这四个优化器 6)收敛性分析和超参数选择指导。",
        "verify_keywords": ["gradient", "momentum", "adam", "learning_rate", "update"],
        "min_length": 600,
    },
    {
        "id": 8,
        "name": "实时推荐系统设计",
        "prompt": "请设计一个完整的实时推荐系统，日活用户1000万。要求：1)离线特征工程管线（用户特征、物品特征、交叉特征，具体特征列表）2)召回层设计（多路召回：协同过滤、向量召回、热门召回、关注召回）3)排序模型（DeepFM/DIN架构细节）4)重排序层（多样性、新鲜度、商业化）5)实时特征更新（Flink处理用户行为流）6)A/B测试框架 7)冷启动策略 8)完整的系统架构图描述。",
        "verify_keywords": ["召回", "排序", "特征", "模型", "A/B", "实时"],
        "min_length": 600,
    },
    {
        "id": 9,
        "name": "操作系统内核组件",
        "prompt": "请用Python模拟实现操作系统的三个核心组件：1)进程调度器 - 实现MLFQ(多级反馈队列)算法，支持优先级提升、时间片轮转、IO阻塞处理 2)内存管理 - 实现分页系统，包含页表、TLB缓存、页面置换(LRU)、缺页中断处理 3)文件系统 - 实现类ext2的简化版，包含inode、数据块、目录项、路径解析。每个组件都要有完整的可运行代码和测试用例。",
        "verify_keywords": ["class", "schedule", "page", "inode", "def", "process"],
        "min_length": 700,
    },
    {
        "id": 10,
        "name": "密码学协议实现",
        "prompt": "请用Python实现以下密码学协议和算法：1)Diffie-Hellman密钥交换 - 完整实现，包含大素数生成 2)RSA加解密 - 包含密钥生成、加密、解密、签名验证 3)AES-256-GCM - 分组加密、认证加密模式 4)SHA-256哈希 - 从零实现压缩函数 5)HMAC-SHA256 6)简化版TLS握手协议模拟。每个算法要有数学原理说明和完整可运行代码。不要使用cryptography等高级库，只用基础数学运算。",
        "verify_keywords": ["def", "encrypt", "decrypt", "key", "hash", "prime"],
        "min_length": 700,
    },
]


def run_single_test(orchestrator, test, temp_dir):
    """执行单个能力验证"""
    result = {
        "id": test["id"],
        "name": test["name"],
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "model_used": None,
        "complexity": 0,
        "task_type": None,
        "duration_ms": 0,
        "response_length": 0,
        "keyword_hits": 0,
        "keyword_total": len(test["verify_keywords"]),
        "keywords_found": [],
        "keywords_missing": [],
        "meets_length": False,
        "thinking_steps_count": 0,
        "grounding_ratio": 0,
        "score": 0,  # 0-100
        "error": None,
    }

    t0 = time.time()
    try:
        orch_result = orchestrator.process(
            test["prompt"], context_nodes=[], enable_tracking=True
        )
        text = orch_result.get("text", "")
        result["model_used"] = orch_result.get("model_used", "unknown")
        result["complexity"] = orch_result.get("complexity", 0)
        result["task_type"] = orch_result.get("task_type", "")
        result["grounding_ratio"] = orch_result.get("grounding_ratio", 0)
        result["thinking_steps_count"] = len(orch_result.get("thinking_steps", []))
        result["response_length"] = len(text)
        result["duration_ms"] = orch_result.get("duration_ms", 0)

        # 关键词验证
        text_lower = text.lower()
        for kw in test["verify_keywords"]:
            if kw.lower() in text_lower:
                result["keywords_found"].append(kw)
                result["keyword_hits"] += 1
            else:
                result["keywords_missing"].append(kw)

        # 长度验证
        result["meets_length"] = result["response_length"] >= test["min_length"]

        # 综合评分 (关键词命中60% + 长度达标20% + 有思考步骤10% + 复杂度合理10%)
        kw_score = (result["keyword_hits"] / result["keyword_total"]) * 60
        len_score = 20 if result["meets_length"] else (result["response_length"] / test["min_length"]) * 20
        think_score = 10 if result["thinking_steps_count"] > 0 else 0
        complexity_score = 10 if result["complexity"] > 0.3 else 5
        result["score"] = min(100, kw_score + len_score + think_score + complexity_score)

        result["status"] = "success"

        # 临时保存响应（后面会删除）
        tmp_file = os.path.join(temp_dir, f"test_{test['id']}.txt")
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(text)

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        traceback.print_exc()

    if not result["duration_ms"]:
        result["duration_ms"] = int((time.time() - t0) * 1000)
    return result


def main():
    print("=" * 60)
    print("  10次复杂能力验证")
    print("  (临时文件将自动删除)")
    print("=" * 60)

    # 初始化
    print("\n[初始化] 认知格和Orchestrator...")
    lattice = agi.CognitiveLattice()
    agi.seed_database(lattice)
    orchestrator = orch_module.TaskOrchestrator(lattice)
    print("  ✓ 初始化完成\n")

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="agi_verify_")
    print(f"  临时目录: {temp_dir}")

    all_results = []
    total_score = 0

    for test in CAPABILITY_TESTS:
        print(f"\n  [{test['id']:2d}/10] {test['name']}", end="", flush=True)
        result = run_single_test(orchestrator, test, temp_dir)
        all_results.append(result)
        total_score += result["score"]

        icon = "✓" if result["status"] == "success" else "✗"
        print(f" [{icon}]")
        print(f"         模型: {result['model_used']} | 复杂度: {result['complexity']:.1f}")
        print(f"         响应: {result['response_length']} chars | "
              f"关键词: {result['keyword_hits']}/{result['keyword_total']} | "
              f"评分: {result['score']:.0f}/100")
        if result["keywords_missing"]:
            print(f"         缺失: {', '.join(result['keywords_missing'])}")
        if result["error"]:
            print(f"         错误: {result['error'][:60]}")

    # 删除临时文件
    print(f"\n  [清理] 删除临时文件: {temp_dir}")
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("  ✓ 临时文件已删除")

    # 汇总报告
    avg_score = total_score / len(CAPABILITY_TESTS)
    success_count = sum(1 for r in all_results if r["status"] == "success")
    high_score_count = sum(1 for r in all_results if r["score"] >= 70)

    print(f"\n{'='*60}")
    print(f"  验证报告")
    print(f"{'='*60}")
    print(f"  成功: {success_count}/10")
    print(f"  平均评分: {avg_score:.1f}/100")
    print(f"  高分(≥70): {high_score_count}/10")
    print()

    # 模型使用统计
    model_usage = {}
    for r in all_results:
        m = r["model_used"] or "unknown"
        model_usage[m] = model_usage.get(m, 0) + 1
    print(f"  模型使用: {json.dumps(model_usage, ensure_ascii=False)}")

    # 各测试详情
    print(f"\n  {'测试':<20} {'模型':<12} {'评分':>5} {'关键词':>6} {'长度':>8}")
    print(f"  {'-'*55}")
    for r in all_results:
        print(f"  {r['name']:<20} {(r['model_used'] or 'N/A'):<12} "
              f"{r['score']:5.0f} "
              f"{r['keyword_hits']}/{r['keyword_total']:>4} "
              f"{r['response_length']:>7}")

    # 结论
    print(f"\n  综合评级: ", end="")
    if avg_score >= 80:
        print("★★★★★ 优秀 - Orchestrator复杂问题处理能力出色")
    elif avg_score >= 60:
        print("★★★★☆ 良好 - 基本满足复杂问题处理需求")
    elif avg_score >= 40:
        print("★★★☆☆ 一般 - 部分复杂问题处理存在不足")
    else:
        print("★★☆☆☆ 需改进 - 复杂问题处理能力有待提升")
    print(f"{'='*60}\n")

    return all_results


if __name__ == "__main__":
    results = main()
    # 以JSON格式输出结果供调用方使用
    print("\n===JSON_RESULTS_START===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("===JSON_RESULTS_END===")
