#!/usr/bin/env python3
"""
AMD GPU Kernel Challenge 参赛启动器
集成本地模型推演能力，自动生成优化方案

参赛信息:
- 竞赛: AMD Developer Challenge February 2026
- 硬件: AMD Instinct MI355X (CDNA4, gfx950)
- 截止: 2026-04-07 07:59 UTC
- 参赛者: Zhao Dylan
- 目标: 3个算子全部进入 Top 5

三大算子:
1. MXFP4 GEMM (amd-mxfp4-mm) — 最高1000分
2. MLA Decode (amd-mixed-mla) — 最高1250分
3. MXFP4 MoE (amd-moe-mxfp4) — 最高1500分
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)



import sys
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# 项目路径
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

# 导入AGI核心模块
from agi_v13_cognitive_lattice import CognitiveLattice

# AMD参赛知识库
AMD_RACE_KNOWLEDGE = {
    "competition": {
        "name": "AMD Developer Challenge February 2026",
        "deadline": "2026-04-07 07:59 UTC",
        "hardware": "AMD Instinct MI355X (CDNA4, gfx950)",
        "total_prize": "$100,000",
        "participant": "Zhao Dylan"
    },
    
    "hardware_specs": {
        "architecture": "CDNA4 (gfx950)",
        "cu_count": 304,
        "hbm3e_bandwidth": "8 TB/s",
        "l2_cache": "256 MB",
        "mfma_fp4": "Native fp4×fp4 MFMA, ~2.4 PetaFLOPS",
        "lds_per_cu": "64 KB",
        "wavefront": "64 lanes"
    },
    
    "kernels": {
        "mxfp4_gemm": {
            "leaderboard": "amd-mxfp4-mm",
            "max_score": 1000,
            "current_time": "24.016µs",
            "rank1_time": "8.094µs",
            "gap": "2.97x",
            "current_rank": "~25-35",
            "description": "bf16 A [M,K] → MXFP4量化 → gemm_a4w4(A_q, B_shuffle) → bf16 C [M,N]",
            "bottleneck": "量化A + shuffle开销, 小M场景CU利用率低",
            "optimization_priority": [
                "消除冗余操作 + 预分配",
                "尝试Triton GEMM路径 (gemm_afp4wfp4)",
                "自定义Triton fused quant+GEMM (高风险)"
            ]
        },
        
        "mla_decode": {
            "leaderboard": "amd-mixed-mla",
            "max_score": 1250,
            "current_time": "223.601µs",
            "rank1_time": "32.972µs",
            "gap": "6.78x",
            "current_rank": "~40-50",
            "description": "DeepSeek R1 MLA forward_absorb: q(total_q,16,576) + kv_data(bf16/fp8/mxfp4) → (total_q,16,512)",
            "bottleneck": "Memory-bound, 读取KV cache带宽瓶颈, 16:1 GQA广播",
            "optimization_priority": [
                "动态NUM_KV_SPLITS + 预分配metadata",
                "尝试a16w8路径 (跳过Q量化)",
                "MXFP4 KV cache (4x带宽节省, 高风险)"
            ]
        },
        
        "mxfp4_moe": {
            "leaderboard": "amd-moe-mxfp4",
            "max_score": 1500,
            "current_time": "185.393µs",
            "rank1_time": "109.793µs",
            "gap": "1.69x",
            "current_rank": "~30-40",
            "description": "DeepSeek R1 MoE: 256 routed + 1 shared, top-8 routed + 1 shared = 9/token",
            "bottleneck": "Expert负载不均, shared expert处理ALL tokens成为瓶颈",
            "optimization_priority": [
                "参数调优 (expert_mask, doweight_stage1)",
                "共享expert分离为dense GEMM",
                "自定义Triton fused MoE kernel (高风险)"
            ]
        }
    },
    
    "leaderboard_safety": {
        "recheck_mode": True,
        "data_regeneration": "每次迭代重新生成数据 (seed += 13)",
        "correctness_check": "每次都检查",
        "forbidden_optimizations": [
            "CUDA Graph replay (数据变了, Graph无效)",
            "data_ptr-keyed输出缓存 (地址复用导致返回旧值)",
            "A_quant缓存 (A值每次都变)",
            "任何依赖'输入值不变'的缓存"
        ],
        "safe_optimizations": [
            "Config-keyed元数据缓存 (形状/indptr/metadata在同一test case内不变)",
            "Pre-allocate输出tensor (形状不变, 值每次重写)",
            "算法优化 (Shared Expert分离, 减少fused_moe工作量)",
            "Kernel选择 (尝试更快的Triton/CK kernel)",
            "Python开销最小化 (模块级导入, 减少条件分支)"
        ]
    },
    
    "submission_commands": {
        "mxfp4_gemm": "popcorn submit --leaderboard amd-mxfp4-mm --gpu MI355X --mode leaderboard mx_fp4_mm_optimized.py",
        "mla_decode": "popcorn submit --leaderboard amd-mixed-mla --gpu MI355X --mode leaderboard mixed_mla_optimized.py",
        "mxfp4_moe": "popcorn submit --leaderboard amd-moe-mxfp4 --gpu MI355X --mode leaderboard moe_mxfp4_optimized.py"
    },
    
    "code_domain_nodes": [
        "GPU_kernel_optimization",
        "MXFP4_quantization",
        "Triton_kernel_programming",
        "CK_kernel_tuning",
        "Memory_bandwidth_optimization",
        "MFMA_instruction_utilization",
        "LDS_shared_memory_management",
        "Flash_Attention_optimization",
        "MoE_routing_optimization",
        "CUDA_Graph_alternatives"
    ]
}


class AMDRaceLauncher:
    """AMD参赛启动器 - 集成本地模型推演能力"""
    
    def __init__(self):
        self.lattice = CognitiveLattice()
        self.db_path = PROJECT_DIR / "memory.db"
        self.docs_dir = PROJECT_DIR / "docs"
        self.race_knowledge = AMD_RACE_KNOWLEDGE
        
    def inject_amd_nodes(self):
        """注入AMD参赛相关的代码领域节点到知识库"""
        print("🔧 注入AMD参赛知识节点到AGI知识库...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 注入代码领域节点
        for node_name in self.race_knowledge["code_domain_nodes"]:
            cursor.execute("""
                INSERT OR IGNORE INTO proven_nodes 
                (domain, content, confidence, verification_count, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "software_engineering",
                f"AMD GPU Kernel优化能力: {node_name}",
                0.85,
                1,
                datetime.now().isoformat()
            ))
        
        # 注入AMD硬件规格节点
        for spec_key, spec_value in self.race_knowledge["hardware_specs"].items():
            cursor.execute("""
                INSERT OR IGNORE INTO proven_nodes 
                (domain, content, confidence, verification_count, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "hardware_architecture",
                f"MI355X {spec_key}: {spec_value}",
                0.95,
                2,
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ 已注入 {len(self.race_knowledge['code_domain_nodes'])} 个代码节点")
        print(f"✅ 已注入 {len(self.race_knowledge['hardware_specs'])} 个硬件规格节点")
    
    def generate_optimization_prompt(self, kernel_name):
        """生成针对特定kernel的优化推演提示词"""
        kernel_info = self.race_knowledge["kernels"][kernel_name]
        safety_info = self.race_knowledge["leaderboard_safety"]
        
        prompt = f"""# AMD GPU Kernel 优化任务

## 目标算子: {kernel_info['leaderboard']}
- 当前性能: {kernel_info['current_time']}
- 第一名性能: {kernel_info['rank1_time']}
- 性能差距: {kernel_info['gap']}
- 当前排名: {kernel_info['current_rank']}
- 最高分值: {kernel_info['max_score']}分

## 算子描述
{kernel_info['description']}

## 性能瓶颈
{kernel_info['bottleneck']}

## 优化优先级
{chr(10).join(f"{i+1}. {opt}" for i, opt in enumerate(kernel_info['optimization_priority']))}

## Leaderboard安全约束
⚠️ 重要: leaderboard模式下每次迭代都会重新生成数据 (seed += 13)

### 禁止的优化方法:
{chr(10).join(f"❌ {opt}" for opt in safety_info['forbidden_optimizations'])}

### 安全的优化方法:
{chr(10).join(f"✅ {opt}" for opt in safety_info['safe_optimizations'])}

## 硬件规格 (MI355X)
- 架构: {self.race_knowledge['hardware_specs']['architecture']}
- CU数: {self.race_knowledge['hardware_specs']['cu_count']}
- HBM3E带宽: {self.race_knowledge['hardware_specs']['hbm3e_bandwidth']}
- MFMA FP4: {self.race_knowledge['hardware_specs']['mfma_fp4']}
- LDS/CU: {self.race_knowledge['hardware_specs']['lds_per_cu']}

## 任务要求
请基于以上信息，推演出3个具体的优化方案:
1. **低风险方案** (预期5-15%提升): 参数调优、预分配、减少Python开销
2. **中风险方案** (预期15-30%提升): 尝试不同kernel路径、算法优化
3. **高风险方案** (预期30-50%提升): 自定义Triton kernel、架构重构

每个方案需要包含:
- 优化思路
- 预期收益
- 实施难度
- 风险评估
- 伪代码示例

请开始推演。
"""
        return prompt
    
    def extract_nodes_from_response(self, response: str, kernel_name: str) -> List[Dict]:
        """从推演响应中提取真实节点"""
        nodes = []
        
        # 提取优化方案中的关键技术点
        patterns = [
            r"(?:优化|方案|策略|技术)[:：]\s*([^\n]{10,100})",
            r"(?:使用|采用|实现)\s*([A-Za-z0-9_\s]{5,50})",
            r"(?:kernel|GEMM|MLA|MoE|Triton|CK)\s*([^\n]{10,80})",
            r"(?:预期收益|性能提升)[:：]\s*([0-9]+[-~]?[0-9]*%)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches[:5]:  # 每个模式最多提取5个
                if len(match.strip()) > 10:
                    nodes.append({
                        "content": match.strip(),
                        "domain": "gpu_kernel_optimization",
                        "source": f"AMD_{kernel_name}_reasoning",
                        "confidence": 0.75
                    })
        
        # 提取代码片段
        code_blocks = re.findall(r"```(?:python)?\n([^`]+)```", response)
        for code in code_blocks[:3]:  # 最多提取3个代码块
            if len(code.strip()) > 20:
                nodes.append({
                    "content": f"Code: {code.strip()[:200]}",
                    "domain": "code_implementation",
                    "source": f"AMD_{kernel_name}_code",
                    "confidence": 0.80
                })
        
        return nodes
    
    def save_nodes_to_database(self, nodes: List[Dict]) -> int:
        """保存节点到本地数据库"""
        if not nodes:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        for node in nodes:
            try:
                cursor.execute("""
                    INSERT INTO proven_nodes 
                    (domain, content, confidence, verification_count, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    node["domain"],
                    node["content"],
                    node["confidence"],
                    1,
                    datetime.now().isoformat(),
                    json.dumps({"source": node["source"]})
                ))
                saved_count += 1
            except sqlite3.IntegrityError:
                # 节点已存在，跳过
                pass
        
        conn.commit()
        conn.close()
        
        return saved_count
    
    def check_context_length(self, prompt: str, response: str) -> Tuple[bool, int]:
        """检查上下文长度是否超限"""
        # 粗略估算token数 (1 token ≈ 4 characters for Chinese/English mix)
        prompt_tokens = len(prompt) // 4
        response_tokens = len(response) // 4
        total_tokens = prompt_tokens + response_tokens
        
        # Qwen2.5-Coder:14b 上下文窗口 = 32K tokens
        max_tokens = 32000
        is_exceeded = total_tokens > max_tokens * 0.8  # 80%阈值
        
        return is_exceeded, total_tokens
    
    def run_local_model_reasoning(self, kernel_name, rounds=3):
        """使用本地模型进行多轮推演"""
        print(f"\n{'='*60}")
        print(f"🧠 启动本地模型推演: {kernel_name}")
        print(f"{'='*60}\n")
        
        prompt = self.generate_optimization_prompt(kernel_name)
        
        print("📝 推演提示词:")
        print("-" * 60)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print("-" * 60)
        
        # 调用本地模型进行推演
        print(f"\n🔄 开始 {rounds} 轮推演...\n")
        
        results = []
        all_nodes = []
        
        for round_num in range(1, rounds + 1):
            print(f"[轮次 {round_num}/{rounds}]")
            
            try:
                # 使用CognitiveLattice的LLM调用能力
                from agi_v13_cognitive_lattice import _call_llm
                
                response = _call_llm(
                    prompt=prompt,
                    system="你是AMD GPU Kernel优化专家，精通Triton、CK kernel编程和CDNA4架构。请基于给定的约束条件，提供具体可行的优化方案。",
                    max_tokens=4096
                )
                
                # 检查上下文长度
                is_exceeded, total_tokens = self.check_context_length(prompt, response)
                if is_exceeded:
                    print(f"⚠️  上下文长度警告: {total_tokens} tokens (已超过80%阈值)")
                    print(f"   建议: 减少推演轮次或简化提示词\n")
                
                # 提取节点
                nodes = self.extract_nodes_from_response(response, kernel_name)
                all_nodes.extend(nodes)
                
                results.append({
                    "round": round_num,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "nodes_extracted": len(nodes),
                    "context_tokens": total_tokens
                })
                
                print(f"✅ 轮次 {round_num} 完成")
                print(f"响应长度: {len(response)} 字符")
                print(f"上下文tokens: {total_tokens}")
                print(f"提取节点: {len(nodes)} 个")
                print(f"响应预览: {response[:200]}...\n")
                
            except Exception as e:
                print(f"❌ 轮次 {round_num} 失败: {e}\n")
                results.append({
                    "round": round_num,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # 保存所有节点到数据库
        if all_nodes:
            saved_count = self.save_nodes_to_database(all_nodes)
            print(f"\n💾 已保存 {saved_count}/{len(all_nodes)} 个节点到数据库")
        
        return results, all_nodes
    
    def save_reasoning_results(self, kernel_name, results):
        """保存推演结果到文件"""
        output_dir = self.docs_dir / "AMD_推演结果"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{kernel_name}_{timestamp}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "kernel": kernel_name,
                "timestamp": timestamp,
                "results": results,
                "knowledge_base": self.race_knowledge["kernels"][kernel_name]
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 推演结果已保存: {output_file}")
        return output_file
    
    def generate_optimization_checklist(self, kernel_name, results, nodes) -> str:
        """生成优化清单总结"""
        checklist = f"# {kernel_name.upper()} 优化清单\n\n"
        checklist += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        kernel_info = self.race_knowledge["kernels"][kernel_name]
        
        # 性能目标
        checklist += "## 性能目标\n\n"
        checklist += f"- 当前性能: {kernel_info['current_time']}\n"
        checklist += f"- 目标性能: {kernel_info['rank1_time']} (第1名)\n"
        checklist += f"- 性能差距: {kernel_info['gap']}\n"
        checklist += f"- 当前排名: {kernel_info['current_rank']}\n\n"
        
        # 推演统计
        checklist += "## 推演统计\n\n"
        success_count = sum(1 for r in results if "error" not in r)
        total_nodes = sum(r.get("nodes_extracted", 0) for r in results if "error" not in r)
        checklist += f"- 推演轮次: {len(results)}\n"
        checklist += f"- 成功轮次: {success_count}\n"
        checklist += f"- 提取节点: {total_nodes} 个\n"
        checklist += f"- 保存节点: {len(nodes)} 个\n\n"
        
        # 优化方向
        checklist += "## 优化方向 (按优先级)\n\n"
        for i, opt in enumerate(kernel_info["optimization_priority"], 1):
            checklist += f"{i}. {opt}\n"
        checklist += "\n"
        
        # 安全约束
        checklist += "## Leaderboard安全约束\n\n"
        checklist += "### ❌ 禁止的优化:\n"
        for forbidden in self.race_knowledge["leaderboard_safety"]["forbidden_optimizations"][:3]:
            checklist += f"- {forbidden}\n"
        checklist += "\n### ✅ 允许的优化:\n"
        for safe in self.race_knowledge["leaderboard_safety"]["safe_optimizations"][:3]:
            checklist += f"- {safe}\n"
        checklist += "\n"
        
        # 提取的关键节点
        if nodes:
            checklist += "## 提取的关键技术点\n\n"
            for i, node in enumerate(nodes[:10], 1):  # 最多显示10个
                checklist += f"{i}. {node['content'][:100]}...\n"
            checklist += "\n"
        
        # 下一步行动
        checklist += "## 下一步行动\n\n"
        checklist += "- [ ] 阅读推演结果JSON文件\n"
        checklist += "- [ ] 选择最优方案并实现代码\n"
        checklist += "- [ ] 本地测试验证性能\n"
        checklist += f"- [ ] 提交: `{self.race_knowledge['submission_commands'][kernel_name]}`\n\n"
        
        return checklist
    
    def generate_summary_report(self, kernel_name, results, nodes):
        """生成推演总结报告"""
        print(f"\n{'='*60}")
        print(f"📊 {kernel_name} 推演总结")
        print(f"{'='*60}\n")
        
        kernel_info = self.race_knowledge["kernels"][kernel_name]
        
        print(f"算子: {kernel_info['leaderboard']}")
        print(f"当前性能: {kernel_info['current_time']} (排名 {kernel_info['current_rank']})")
        print(f"目标性能: {kernel_info['rank1_time']} (第1名)")
        print(f"性能差距: {kernel_info['gap']}\n")
        
        print(f"推演轮次: {len(results)}")
        success_count = sum(1 for r in results if "error" not in r)
        print(f"成功轮次: {success_count}/{len(results)}")
        total_nodes = sum(r.get("nodes_extracted", 0) for r in results if "error" not in r)
        print(f"提取节点: {total_nodes} 个")
        print(f"保存节点: {len(nodes)} 个\n")
        
        # 上下文使用情况
        if success_count > 0:
            avg_tokens = sum(r.get("context_tokens", 0) for r in results if "error" not in r) / success_count
            print(f"平均上下文: {int(avg_tokens)} tokens")
            if avg_tokens > 25600:  # 80% of 32K
                print("⚠️  上下文使用率较高，建议减少轮次或简化提示词\n")
            else:
                print("✅ 上下文使用正常\n")
        
        if success_count > 0:
            print("✅ 推演已完成，请查看保存的文件获取详细方案")
            print("\n下一步:")
            print("1. 查看优化清单: docs/AMD_推演结果/{kernel}_checklist.md")
            print("2. 阅读推演结果: docs/AMD_推演结果/{kernel}_{timestamp}.json")
            print("3. 实现优化代码")
            print("4. 本地测试验证")
            print(f"5. 提交到leaderboard: {self.race_knowledge['submission_commands'][kernel_name]}")
        else:
            print("❌ 所有推演轮次都失败，请检查AGI配置")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AMD GPU Kernel Challenge 参赛启动器")
    parser.add_argument(
        "--kernel",
        choices=["mxfp4_gemm", "mla_decode", "mxfp4_moe", "all"],
        default="all",
        help="选择要推演的kernel (默认: all)"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="推演轮次 (默认: 3)"
    )
    parser.add_argument(
        "--inject-nodes",
        action="store_true",
        help="注入AMD参赛知识节点到AGI知识库"
    )
    
    args = parser.parse_args()
    
    launcher = AMDRaceLauncher()
    
    # 注入知识节点
    if args.inject_nodes:
        launcher.inject_amd_nodes()
    
    # 选择要推演的kernels
    if args.kernel == "all":
        kernels = ["mxfp4_gemm", "mla_decode", "mxfp4_moe"]
    else:
        kernels = [args.kernel]
    
    # 对每个kernel进行推演
    for kernel_name in kernels:
        results, nodes = launcher.run_local_model_reasoning(kernel_name, rounds=args.rounds)
        output_file = launcher.save_reasoning_results(kernel_name, results)
        
        # 生成并保存优化清单
        checklist = launcher.generate_optimization_checklist(kernel_name, results, nodes)
        checklist_file = output_file.parent / f"{kernel_name}_checklist.md"
        checklist_file.write_text(checklist, encoding="utf-8")
        print(f"📋 优化清单已保存: {checklist_file}")
        
        launcher.generate_summary_report(kernel_name, results, nodes)
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
