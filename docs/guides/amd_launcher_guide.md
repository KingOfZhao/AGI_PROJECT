# AMD GPU Kernel Challenge 参赛启动器使用指南

> 工具: `amd_race_launcher.py`  
> 作者: Zhao Dylan  
> 竞赛: AMD Developer Challenge February 2026  
> 硬件: AMD Instinct MI355X (CDNA4, gfx950)

---

## 概述

AMD参赛启动器是一个集成本地模型推演能力的自动化工具，用于生成GPU kernel优化方案。它整合了：

1. **AMD参赛知识库**: 3个算子详细信息、第一名性能数据、硬件规格
2. **Leaderboard安全策略**: 禁止/允许的优化方法清单
3. **本地模型推演**: 使用Ollama/Qwen2.5-Coder进行多轮优化方案生成
4. **代码领域链路**: 自动注入GPU kernel优化相关知识节点到AGI知识库

---

## 参赛信息总览

### 三大算子

| 算子 | Leaderboard | 最高分 | 当前性能 | #1性能 | 差距 | 排名 |
|------|------------|--------|---------|--------|------|------|
| **MXFP4 GEMM** | amd-mxfp4-mm | 1000分 | 24.016µs | 8.094µs | 2.97x | ~25-35 |
| **MLA Decode** | amd-mixed-mla | 1250分 | 223.601µs | 32.972µs | 6.78x | ~40-50 |
| **MXFP4 MoE** | amd-moe-mxfp4 | 1500分 | 185.393µs | 109.793µs | 1.69x | ~30-40 |

**总分**: 3750分 (满分)  
**截止日期**: 2026-04-07 07:59 UTC

### MI355X 硬件规格

- **架构**: CDNA4 (gfx950)
- **CU数**: 304
- **HBM3E带宽**: 8 TB/s
- **L2缓存**: 256 MB
- **MFMA FP4**: 原生fp4×fp4矩阵指令, ~2.4 PetaFLOPS
- **LDS/CU**: 64 KB
- **Wavefront**: 64 lanes

---

## 安装与配置

### 前置条件

1. **Python 3.9+**
2. **Ollama** (本地模型推理引擎)
   ```bash
   # macOS
   brew install ollama
   ollama pull qwen2.5-coder:14b
   ```
3. **AGI项目依赖**
   ```bash
   cd /Users/administruter/Desktop/AGI_PROJECT
   pip install -r requirements.txt
   ```

### 配置检查

确认本地模型后端已配置:
```bash
# 检查agi_v13_cognitive_lattice.py中的ACTIVE_BACKEND
grep "ACTIVE_BACKEND" agi_v13_cognitive_lattice.py
# 应该输出: ACTIVE_BACKEND = "ollama"
```

---

## 使用方法

### 1. 注入AMD知识节点 (首次运行)

```bash
python3 amd_race_launcher.py --inject-nodes
```

这会将以下知识注入到AGI知识库 (`memory.db`):
- 10个代码领域节点 (GPU_kernel_optimization, MXFP4_quantization等)
- 7个硬件规格节点 (MI355X架构参数)

**输出示例**:
```
🔧 注入AMD参赛知识节点到AGI知识库...
✅ 已注入 10 个代码节点
✅ 已注入 7 个硬件规格节点
```

### 2. 单个算子推演

#### MXFP4 GEMM 优化推演
```bash
python3 amd_race_launcher.py --kernel mxfp4_gemm --rounds 3
```

#### MLA Decode 优化推演
```bash
python3 amd_race_launcher.py --kernel mla_decode --rounds 5
```

#### MXFP4 MoE 优化推演
```bash
python3 amd_race_launcher.py --kernel mxfp4_moe --rounds 3
```

### 3. 全部算子推演

```bash
python3 amd_race_launcher.py --kernel all --rounds 3
```

这会依次对3个算子各进行3轮推演，总共9轮。

---

## 推演输出

### 控制台输出

```
============================================================
🧠 启动本地模型推演: mxfp4_gemm
============================================================

📝 推演提示词:
------------------------------------------------------------
# AMD GPU Kernel 优化任务

## 目标算子: amd-mxfp4-mm
- 当前性能: 24.016µs
- 第一名性能: 8.094µs
...
------------------------------------------------------------

🔄 开始 3 轮推演...

[轮次 1/3]
✅ 轮次 1 完成
响应长度: 2847 字符
响应预览: 基于给定的约束条件，我为MXFP4 GEMM优化提供以下三个方案...

[轮次 2/3]
✅ 轮次 2 完成
...

💾 推演结果已保存: docs/AMD_推演结果/mxfp4_gemm_20260324_091523.json

============================================================
📊 mxfp4_gemm 推演总结
============================================================

算子: amd-mxfp4-mm
当前性能: 24.016µs (排名 ~25-35)
目标性能: 8.094µs (第1名)
性能差距: 2.97x

推演轮次: 3
成功轮次: 3/3

✅ 推演已完成，请查看保存的JSON文件获取详细方案

下一步:
1. 阅读推演结果，选择最优方案
2. 实现优化代码
3. 本地测试验证
4. 提交到leaderboard: popcorn submit --leaderboard amd-mxfp4-mm --gpu MI355X --mode leaderboard mx_fp4_mm_optimized.py
```

### JSON结果文件

保存路径: `docs/AMD_推演结果/{kernel_name}_{timestamp}.json`

**文件结构**:
```json
{
  "kernel": "mxfp4_gemm",
  "timestamp": "20260324_091523",
  "results": [
    {
      "round": 1,
      "response": "基于给定的约束条件，我为MXFP4 GEMM优化提供以下三个方案:\n\n### 1. 低风险方案 (预期5-15%提升)\n...",
      "timestamp": "2026-03-24T09:15:23.456789"
    },
    {
      "round": 2,
      "response": "...",
      "timestamp": "2026-03-24T09:16:45.123456"
    },
    {
      "round": 3,
      "response": "...",
      "timestamp": "2026-03-24T09:18:12.789012"
    }
  ],
  "knowledge_base": {
    "leaderboard": "amd-mxfp4-mm",
    "max_score": 1000,
    "current_time": "24.016µs",
    ...
  }
}
```

---

## 推演提示词结构

启动器会为每个算子生成结构化的推演提示词，包含:

### 1. 目标算子信息
- 当前性能 vs 第一名性能
- 性能差距
- 最高分值

### 2. 算子描述
- 输入输出格式
- 计算流程

### 3. 性能瓶颈分析
- Memory-bound / Compute-bound
- 具体瓶颈点

### 4. 优化优先级
- 低风险方案
- 中风险方案
- 高风险方案

### 5. Leaderboard安全约束
- ❌ 禁止的优化方法 (CUDA Graph, data_ptr缓存等)
- ✅ 安全的优化方法 (Config-keyed缓存, 算法优化等)

### 6. 硬件规格
- MI355X完整参数

### 7. 任务要求
要求本地模型输出3个具体方案，每个方案包含:
- 优化思路
- 预期收益
- 实施难度
- 风险评估
- 伪代码示例

---

## Leaderboard安全策略 (重要!)

### ⚠️ 核心约束

Leaderboard模式 (`recheck=True`) 下:
- **每次迭代重新生成数据** (seed += 13)
- **每次都检查correctness**
- **L2 Cache每次清空**

### ❌ 禁止的优化方法

1. **CUDA Graph replay** — 数据变了, Graph无效
2. **data_ptr-keyed输出缓存** — 地址复用导致返回旧值
3. **A_quant缓存** — A值每次都变
4. **任何依赖"输入值不变"的缓存**

### ✅ 安全的优化方法

1. **Config-keyed元数据缓存** — 形状/indptr/metadata在同一test case内不变
2. **Pre-allocate输出tensor** — 形状不变, 值每次重写
3. **算法优化** — Shared Expert分离, 减少fused_moe工作量
4. **Kernel选择** — 尝试更快的Triton/CK kernel
5. **Python开销最小化** — 模块级导入, 减少条件分支

---

## 典型工作流程

### 完整优化流程

```bash
# Step 1: 首次运行，注入知识节点
python3 amd_race_launcher.py --inject-nodes

# Step 2: 对单个算子进行深度推演 (5轮)
python3 amd_race_launcher.py --kernel mxfp4_gemm --rounds 5

# Step 3: 查看推演结果
cat docs/AMD_推演结果/mxfp4_gemm_*.json | jq '.results[0].response'

# Step 4: 根据推演结果实现优化代码
# 编辑: /Users/administruter/Desktop/flutterProject/reference-kernels-local/problems/amd_202602/mx_fp4_mm_optimized.py

# Step 5: 本地测试
cd /Users/administruter/Desktop/flutterProject/reference-kernels-local
popcorn test --leaderboard amd-mxfp4-mm --gpu MI355X --mode benchmark problems/amd_202602/mx_fp4_mm_optimized.py

# Step 6: 提交到leaderboard
popcorn submit --leaderboard amd-mxfp4-mm --gpu MI355X --mode leaderboard problems/amd_202602/mx_fp4_mm_optimized.py

# Step 7: 重复Step 2-6，迭代优化
```

---

## 高级用法

### 调整推演轮次

根据算子复杂度调整:
- **简单优化** (参数调优): 1-3轮
- **中等优化** (算法改进): 3-5轮
- **复杂优化** (自定义kernel): 5-10轮

```bash
# 深度推演 (10轮)
python3 amd_race_launcher.py --kernel mla_decode --rounds 10
```

### 批量推演

```bash
# 对所有算子各推演5轮
python3 amd_race_launcher.py --kernel all --rounds 5
```

### 结合growth_engine使用

将AMD优化能力集成到自成长引擎:

```bash
# 1. 注入AMD节点
python3 amd_race_launcher.py --inject-nodes

# 2. 启动自成长引擎，聚焦代码领域
python3 growth_engine.py --parallel --workers 4 --rounds 20
```

---

## 故障排查

### 问题1: 导入错误

```
ImportError: cannot import name 'AGI_v13_CognitiveLattice'
```

**解决**: 已修复，使用 `CognitiveLattice` 类名

### 问题2: 本地模型未响应

```
❌ 轮次 1 失败: Connection refused
```

**解决**:
```bash
# 检查Ollama服务
ollama list
ollama serve

# 拉取模型
ollama pull qwen2.5-coder:14b
```

### 问题3: 推演结果质量不佳

**解决**:
1. 增加推演轮次 (`--rounds 5`)
2. 检查提示词是否包含足够上下文
3. 尝试切换到更强的模型 (如GLM-5)

---

## 提交命令参考

### MXFP4 GEMM
```bash
popcorn submit --leaderboard amd-mxfp4-mm --gpu MI355X --mode leaderboard mx_fp4_mm_optimized.py
```

### MLA Decode
```bash
popcorn submit --leaderboard amd-mixed-mla --gpu MI355X --mode leaderboard mixed_mla_optimized.py
```

### MXFP4 MoE
```bash
popcorn submit --leaderboard amd-moe-mxfp4 --gpu MI355X --mode leaderboard moe_mxfp4_optimized.py
```

---

## 参考文档

- `docs/AMD_GPU_Kernel_优化清单.md` — 完整优化策略
- `docs/AMD_20轮极限优化分析.md` — 20轮推演对比
- `docs/待添加/AMD_Leaderboard_eval机制深度分析.md` — 计时机制分析
- `docs/待添加/AMD_v5_Leaderboard安全策略全记录.md` — 安全策略详解

---

## 联系方式

- 参赛者: Zhao Dylan
- 项目路径: `/Users/administruter/Desktop/AGI_PROJECT`
- 代码路径: `/Users/administruter/Desktop/flutterProject/reference-kernels-local/problems/amd_202602/`

---

*生成时间: 2026-03-24*  
*版本: v1.0*
