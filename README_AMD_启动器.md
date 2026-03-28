# AMD GPU Kernel Challenge 参赛启动器 - 快速开始

> 🚀 一键启动本地模型推演，自动提取节点、监控上下文、生成优化清单

---

## 快速启动

```bash
cd /Users/administruter/Desktop/AGI_PROJECT
./start_amd_reasoning.sh
```

**交互式菜单**会引导您完成：
1. 选择算子 (GEMM / MLA / MoE / 全部)
2. 选择轮次 (1轮快速 / 3轮标准 / 5轮深度 / 10轮极限)
3. 自动推演并保存结果

---

## 核心功能

### ✅ 已实现的增强功能

#### 1. **自动节点提取与数据库保存**
- 每轮推演后自动提取关键技术点
- 保存到 `memory.db` 的 `proven_nodes` 表
- 提取内容包括:
  - 优化方案关键点
  - 性能提升预期
  - 代码实现片段
  - Kernel技术细节

#### 2. **上下文长度监控**
- 实时计算 prompt + response 的 token 数
- 超过 80% 阈值 (25.6K/32K) 时自动警告
- 提示: "建议减少推演轮次或简化提示词"

#### 3. **优化清单自动生成**
每次推演后自动生成 `{kernel}_checklist.md`，包含:
- 性能目标 (当前 vs 第一名)
- 推演统计 (轮次、节点数)
- 优化方向 (按优先级)
- Leaderboard安全约束
- 提取的关键技术点
- 下一步行动清单

#### 4. **完整的推演总结**
控制台输出:
- 算子性能对比
- 推演成功率
- 节点提取/保存数量
- 上下文使用情况
- 下一步操作指引

---

## 输出文件

### 📁 `docs/AMD_推演结果/`

每次推演生成3个文件:

1. **`{kernel}_{timestamp}.json`** - 完整推演结果
   ```json
   {
     "kernel": "mxfp4_gemm",
     "timestamp": "20260324_090000",
     "results": [
       {
         "round": 1,
         "response": "...",
         "nodes_extracted": 12,
         "context_tokens": 8456
       }
     ]
   }
   ```

2. **`{kernel}_checklist.md`** - 优化清单
   ```markdown
   # MXFP4_GEMM 优化清单
   
   ## 性能目标
   - 当前性能: 24.016µs
   - 目标性能: 8.094µs (第1名)
   - 性能差距: 2.97x
   
   ## 推演统计
   - 推演轮次: 3
   - 成功轮次: 3
   - 提取节点: 36 个
   - 保存节点: 28 个
   
   ## 优化方向 (按优先级)
   1. 消除冗余操作 + 预分配
   2. 尝试Triton GEMM路径
   3. 自定义Triton fused quant+GEMM
   
   ## 提取的关键技术点
   1. 使用aiter Triton GEMM替代CK kernel...
   2. 预分配输出tensor避免动态分配...
   ...
   
   ## 下一步行动
   - [ ] 阅读推演结果JSON文件
   - [ ] 选择最优方案并实现代码
   - [ ] 本地测试验证性能
   - [ ] 提交到leaderboard
   ```

3. **数据库节点** - 自动保存到 `memory.db`

---

## 使用示例

### 示例1: 快速验证 (1轮推演)

```bash
./start_amd_reasoning.sh
# 选择: 1 (MXFP4 GEMM)
# 选择: 1 (1轮)
```

**输出**:
```
✅ 轮次 1 完成
响应长度: 2847 字符
上下文tokens: 8456
提取节点: 12 个

💾 已保存 12/12 个节点到数据库
📋 优化清单已保存: docs/AMD_推演结果/mxfp4_gemm_checklist.md

📊 mxfp4_gemm 推演总结
算子: amd-mxfp4-mm
当前性能: 24.016µs (排名 ~25-35)
目标性能: 8.094µs (第1名)
性能差距: 2.97x

推演轮次: 1
成功轮次: 1/1
提取节点: 12 个
保存节点: 12 个

平均上下文: 8456 tokens
✅ 上下文使用正常
```

### 示例2: 全部算子深度推演 (5轮)

```bash
./start_amd_reasoning.sh
# 选择: 4 (全部算子)
# 选择: 3 (5轮)
```

**预期时间**: ~15-30分钟 (取决于本地模型速度)

**输出**: 15个文件 (3个算子 × 5轮)
- 3个 JSON 结果文件
- 3个 Markdown 清单
- ~150个节点保存到数据库

---

## 命令行选项

如果不想使用交互式菜单，可以直接调用Python脚本:

```bash
# 单个算子 + 指定轮次
python3 amd_race_launcher.py --kernel mxfp4_gemm --rounds 3

# 全部算子
python3 amd_race_launcher.py --kernel all --rounds 5

# 仅注入知识节点
python3 amd_race_launcher.py --inject-nodes

# 查看帮助
python3 amd_race_launcher.py --help
```

---

## 节点提取示例

**从推演响应中自动提取**:

```python
# 提取模式1: 优化方案
"优化: 使用Triton GEMM替代CK kernel" 
→ 节点: "使用Triton GEMM替代CK kernel"

# 提取模式2: 性能预期
"预期收益: 15-30%提升"
→ 节点: "15-30%"

# 提取模式3: 代码片段
```python
from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import gemm_afp4wfp4
output = gemm_afp4wfp4(A_q, B_shuffle, ...)
```
→ 节点: "Code: from aiter.ops.triton.gemm..."
```

**保存到数据库**:
```sql
INSERT INTO proven_nodes 
(domain, content, confidence, verification_count, created_at, metadata)
VALUES 
('gpu_kernel_optimization', '使用Triton GEMM替代CK kernel', 0.75, 1, '2026-03-24T09:00:00', '{"source": "AMD_mxfp4_gemm_reasoning"}');
```

---

## 上下文监控

**阈值设置**: 32K tokens × 80% = 25.6K tokens

**监控逻辑**:
```python
prompt_tokens = len(prompt) // 4  # 粗略估算
response_tokens = len(response) // 4
total_tokens = prompt_tokens + response_tokens

if total_tokens > 25600:
    print("⚠️ 上下文长度警告: {total_tokens} tokens")
    print("   建议: 减少推演轮次或简化提示词")
```

**实际案例**:
- 1轮推演: ~8K tokens ✅
- 3轮推演: ~15K tokens ✅
- 5轮推演: ~22K tokens ✅
- 10轮推演: ~28K tokens ⚠️ (接近上限)

---

## 故障排查

### 问题1: 启动脚本无权限

```bash
chmod +x start_amd_reasoning.sh
```

### 问题2: Ollama未安装

```bash
brew install ollama
ollama pull qwen2.5-coder:14b
ollama serve
```

### 问题3: 数据库写入失败

检查 `memory.db` 文件权限:
```bash
ls -l memory.db
chmod 644 memory.db
```

### 问题4: 节点提取为空

- 检查推演响应格式
- 调整正则表达式模式 (在 `extract_nodes_from_response` 方法中)

---

## 下一步工作流程

```mermaid
graph LR
    A[启动推演] --> B[查看清单]
    B --> C[阅读JSON结果]
    C --> D[选择最优方案]
    D --> E[实现代码]
    E --> F[本地测试]
    F --> G[提交Leaderboard]
```

### 1. 查看优化清单
```bash
cat docs/AMD_推演结果/mxfp4_gemm_checklist.md
```

### 2. 阅读详细结果
```bash
cat docs/AMD_推演结果/mxfp4_gemm_*.json | jq '.results[0].response'
```

### 3. 实现优化代码
编辑文件:
```
/Users/administruter/Desktop/flutterProject/reference-kernels-local/problems/amd_202602/mx_fp4_mm_optimized.py
```

### 4. 本地测试
```bash
cd /Users/administruter/Desktop/flutterProject/reference-kernels-local
popcorn test --leaderboard amd-mxfp4-mm --gpu MI355X --mode benchmark problems/amd_202602/mx_fp4_mm_optimized.py
```

### 5. 提交到Leaderboard
```bash
popcorn submit --leaderboard amd-mxfp4-mm --gpu MI355X --mode leaderboard problems/amd_202602/mx_fp4_mm_optimized.py
```

---

## 技术细节

### 节点提取正则表达式

```python
patterns = [
    r"(?:优化|方案|策略|技术)[:：]\s*([^\n]{10,100})",
    r"(?:使用|采用|实现)\s*([A-Za-z0-9_\s]{5,50})",
    r"(?:kernel|GEMM|MLA|MoE|Triton|CK)\s*([^\n]{10,80})",
    r"(?:预期收益|性能提升)[:：]\s*([0-9]+[-~]?[0-9]*%)",
]
```

### 数据库Schema

```sql
CREATE TABLE proven_nodes (
    id INTEGER PRIMARY KEY,
    domain TEXT,
    content TEXT,
    confidence REAL,
    verification_count INTEGER,
    created_at TEXT,
    metadata TEXT
);
```

### 上下文Token估算

```python
# 中英混合文本: 1 token ≈ 4 characters
tokens = len(text) // 4
```

---

## 参考文档

- **优化清单**: `docs/AMD_GPU_Kernel_优化清单.md`
- **20轮分析**: `docs/AMD_20轮极限优化分析.md`
- **Leaderboard机制**: `docs/待添加/AMD_Leaderboard_eval机制深度分析.md`
- **安全策略**: `docs/待添加/AMD_v5_Leaderboard安全策略全记录.md`
- **使用指南**: `docs/AMD_参赛启动器使用指南.md`

---

## 联系方式

- **参赛者**: Zhao Dylan
- **项目路径**: `/Users/administruter/Desktop/AGI_PROJECT`
- **代码路径**: `/Users/administruter/Desktop/flutterProject/reference-kernels-local/problems/amd_202602/`

---

*生成时间: 2026-03-24*  
*版本: v2.0 (增强版)*
