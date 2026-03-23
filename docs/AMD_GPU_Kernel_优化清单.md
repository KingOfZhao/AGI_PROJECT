# AMD $100K GPU Kernel 极限优化清单
## 竞赛: AMD Developer Challenge February 2026
## 目标硬件: AMD Instinct MI355X (gfx950+)
## 截止日期: 2026-04-07 07:59 UTC
## 参赛者: Zhao Dylan

---

## 计分规则
- 每个内核问题得分 = 最大分值 × [1 - (排名分值/20)]
- 排名分值 = 0,1,2,...18,19 (第1名=0, 第20名=19)
- 总分 = 三项之和, 满分 = 1500 + 1250 + 1000 = 3750

| 排行榜 | 最高分 | 排名1得分 | 排名5得分 | 排名10得分 |
|--------|--------|-----------|-----------|------------|
| MXFP4 MoE (amd-moe-mx-fp4) | 1500 | 1500 | 1200 | 825 |
| MLA Decode (amd-mixed-mla) | 1250 | 1250 | 1000 | 687.5 |
| MXFP4 GEMM (amd-mx-fp4-mm) | 1000 | 1000 | 800 | 550 |

---

## 第一部分: MI355X 硬件特性拆解

### 核心规格
| 参数 | 值 | 优化含义 |
|------|-----|---------|
| 架构 | CDNA 4 (gfx950) | 支持MXFP4原生MFMA指令 |
| CU数量 | 304 | 大规模并行,需要充分占满 |
| HBM3e带宽 | ~8 TB/s | memory-bound kernel的天花板 |
| L2缓存 | 256 MB | 可缓存中等规模KV cache |
| MFMA fp4 | 原生支持 | fp4×fp4→fp32累加,不需要dequant |
| Wavefront | 64线程 | 调度粒度 |
| LDS | 64 KB/CU | 关键:KV广播到16个query head |

### MXFP4 原生支持
- **E2M1格式**: 值域 [0, 0.5, 1, 1.5, 2, 3, 4, 6]
- **E8M0 scale**: 纯指数缩放(2的幂)
- **Block size = 32**: 每32个元素共享一个scale
- **fp4x2 packing**: 每字节存2个fp4值
- **MFMA fp4×fp4**: MI355X原生矩阵乘,无需反量化

---

## 第二部分: 三大算子深度分析

### 2.1 MXFP4 GEMM (amd-mx-fp4-mm) — 最高1000分

#### 问题描述
```
bf16 A [M,K] → MXFP4量化 → gemm_a4w4(A_q, B_shuffle) → bf16 C [M,N]
B已预量化+预shuffle, 只需量化A并执行GEMM
```

#### 参考实现关键路径
```python
# 步骤1: 量化A (单独的Triton kernel)
A_q, A_scale_sh = _quant_mxfp4(A, shuffle=True)  # ~3-5μs
# 步骤2: GEMM (CK kernel)
out = aiter.gemm_a4w4(A_q, B_shuffle, A_scale_sh, B_scale_sh, dtype=bf16, bpreshuffle=True)  # ~5-20μs
```

#### Benchmark尺寸 (排名按几何均值)
| M | N | K | 参考时间(μs) | 特征 |
|---|---|---|-------------|------|
| 4 | 2880 | 512 | 8.2 | 极小M,memory-bound |
| 16 | 2112 | 7168 | 20.9 | 中K,计算密集 |
| 32 | 4096 | 512 | 9.5 | 小K大N |
| 32 | 2880 | 512 | 9.2 | 小K中N |
| 64 | 7168 | 2048 | 12.7 | 平衡 |
| 256 | 3072 | 1536 | 12.2 | 较大M |

#### 瓶颈分析
1. **两次kernel launch**: quant和GEMM分开 → launch overhead ~2-5μs
2. **小M场景**: M=4/16/32时CU严重闲置,利用率<10%
3. **量化A的全局内存写回**: A_q写到HBM再被GEMM读 → 无谓的内存往返
4. **e8m0_shuffle额外开销**: scale重排也是独立kernel

#### 优化方案 (按收益排序)
| # | 方案 | 预期收益 | 难度 | 风险 |
|---|------|---------|------|------|
| G1 | **融合quant+GEMM为Triton单kernel** | 20-40% | 高 | 正确性 |
| G2 | **使用aiter Triton GEMM替代CK** | 10-20% | 中 | API兼容 |
| G3 | **预分配输出+CUDA Graph** | 5-15% | 低 | 无 |
| G4 | **小M专用: 向量化quant+splitK GEMM** | 15-30% | 高 | 仅特定尺寸 |
| G5 | **避免contiguous()拷贝** | 3-5% | 低 | 无 |
| G6 | **流水线: 量化A的同时开始GEMM** | 10-20% | 中 | 同步 |

---

### 2.2 MLA Decode (amd-mixed-mla) — 最高1250分

#### 问题描述
```
DeepSeek R1 MLA forward_absorb:
q: (total_q, 16, 576) bf16 → 16个query head
kv_data: 提供bf16/fp8/mxfp4三种格式
输出: (total_q, 16, 512) bf16

核心: 变长批次的attention decode (q_seq_len=1)
```

#### 参考实现关键路径
```python
# 1. Q量化为fp8 (~1μs)
q_fp8, q_scale = quantize_fp8(q)
# 2. 构建metadata (~5μs)
meta = _make_mla_decode_metadata(...)
# 3. MLA decode (主体, ~100-800μs)
mla_decode_fwd(q_fp8, kv_fp8, o, ..., q_scale=q_scale, kv_scale=kv_scale)
```

#### Benchmark尺寸
| batch | q_seq | kv_seq | a8w8参考(μs) | 特征 |
|-------|-------|--------|-------------|------|
| 4 | 1 | 1024 | ~118 | 极小batch,memory-bound |
| 4 | 1 | 8192 | ~113 | 长KV |
| 32 | 1 | 1024 | ~150 | 中batch |
| 32 | 1 | 8192 | ~160 | 中batch长KV |
| 64 | 1 | 1024 | ~140 | |
| 64 | 1 | 8192 | ~171 | |
| 256 | 1 | 1024 | ~200 | 大batch |
| 256 | 1 | 8192 | ~349 | **最大case** |

#### 瓶颈分析
1. **Memory-bound**: decode阶段q_seq_len=1, 主要瓶颈是读取KV cache
2. **fp8 KV带宽**: 576 bytes/token × total_kv → bs=256,kv=8k时 = 1.2GB
3. **16:1 GQA ratio**: 1个KV head广播到16个Q head → KV只读1次但需广播
4. **Split-K reduce**: 32-way split有reduce开销
5. **metadata构建**: 每次都重新分配+填充

#### 优化方案 (按收益排序)
| # | 方案 | 预期收益 | 难度 | 风险 |
|---|------|---------|------|------|
| M1 | **MXFP4 KV cache (4x带宽节省)** | 30-50% | 高 | 精度 |
| M2 | **调优NUM_KV_SPLITS** | 5-15% | 低 | 无 |
| M3 | **预分配metadata+输出(避免malloc)** | 5-10% | 低 | 无 |
| M4 | **CUDA Graph封装** | 3-8% | 低 | 动态shape |
| M5 | **自定义Triton FlashDecoding** | 20-40% | 极高 | 正确性 |
| M6 | **跳过Q量化(用bf16 Q + fp8 KV = a16w8)** | 3-5% | 低 | 精度 |
| M7 | **KV在LDS中复用(16 head共享)** | 10-20% | 高 | MI355X LDS |

---

### 2.3 MXFP4 MoE (amd-moe-mx-fp4) — 最高1500分

#### 问题描述
```
DeepSeek R1 MoE: 256 routed experts + 1 shared, top-8 routed + 1 shared = 9/token
Stage 1: hidden → quant → gate_up GEMM → SwiGLU
Stage 2: intermediate → quant → down GEMM → weighted reduce
```

#### 参考实现关键路径
```python
output = fused_moe(
    hidden_states,
    gate_up_weight_shuffled, down_weight_shuffled,
    topk_weights, topk_ids,
    activation=ActivationType.Silu,
    quant_type=QuantType.per_1x32,
    w1_scale=gate_up_weight_scale_shuffled,
    w2_scale=down_weight_scale_shuffled,
    hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
)
```

#### Benchmark尺寸
| bs | E | d_hidden | d_expert | top_k | 参考(μs) |
|----|---|----------|----------|-------|---------|
| 16 | 257 | 7168 | 256 | 9 | 152.7 |
| 128 | 257 | 7168 | 256 | 9 | 239.0 |
| 512 | 257 | 7168 | 256 | 9 | 336.5 |
| 16 | 33 | 7168 | 512 | 9 | 106.2 |
| 128 | 33 | 7168 | 512 | 9 | 141.1 |
| 512 | 33 | 7168 | 512 | 9 | 225.0 |
| 512 | 33 | 7168 | 2048 | 9 | 380.4 |

#### 瓶颈分析
1. **Expert负载不均**: top-k路由导致某些expert分配多token、某些少
2. **两阶段pipeline**: Stage1和Stage2之间有中间结果写回
3. **小d_expert (256)**: GEMM粒度太小,CU利用率低
4. **Shared expert开销**: 所有token都经过shared expert,但按MoE路径处理
5. **256-alignment padding**: 额外padding浪费带宽

#### 优化方案 (按收益排序)
| # | 方案 | 预期收益 | 难度 | 风险 |
|---|------|---------|------|------|
| E1 | **fused_moe参数调优(doweight_stage1等)** | 5-15% | 低 | 无 |
| E2 | **Shared expert单独dense GEMM** | 10-20% | 中 | 正确性 |
| E3 | **自定义expert排序减少padding** | 5-10% | 中 | 正确性 |
| E4 | **CUDA Graph** | 3-8% | 低 | 动态 |
| E5 | **自定义Triton fused MoE kernel** | 20-40% | 极高 | 正确性 |
| E6 | **Stage间LDS缓存中间结果** | 15-25% | 高 | MI355X |

---

## 第三部分: 5轮推演对照 (本地14B vs GLM-5)

### 第1轮: 基线策略对比

#### 本地14B分析
**MXFP4 GEMM策略**:
- 首选G3(预分配+CUDA Graph) + G5(避免多余contiguous) = 低风险8-15%提升
- 次选G2(Triton GEMM替代) — aiter有`gemm_afp4wfp4.py`可直接调用

**MLA Decode策略**:
- 首选M2(调NUM_KV_SPLITS)+M3(预分配) = 低风险10-20%
- M6(a16w8跳过Q量化)值得尝试

**MoE策略**:
- 首选E1(参数调优) = 最低风险
- fused_moe已经很优化,难以大幅超越

#### GLM-5分析 (推演)
**MXFP4 GEMM策略**:
- 应该尝试写Triton fused quant+GEMM kernel (G1)
- MI355X的MFMA_F4指令可以直接做fp4×fp4,无需手动dequant
- 使用`tl.dot`配合fp4类型可以在Triton中直接利用MFMA

**MLA Decode策略**:
- MXFP4 KV (M1)是最大赢面 — 4x带宽节省
- 需要自定义attention kernel融合dequant
- 或者找到aiter是否有a4w4 MLA kernel

**MoE策略**:
- 共享expert分离为dense GEMM (E2)可减少路由开销
- 大bs场景用split-K

#### 差异记录
| 项目 | 本地14B | GLM-5 | 差异原因 |
|------|---------|-------|---------|
| GEMM | 保守:预分配+参数调优 | 激进:Triton fused kernel | 14B对Triton细节把握不足 |
| MLA | 调优参数 | MXFP4 KV + 自定义kernel | GLM-5有更多CUDA kernel经验 |
| MoE | 仅参数调优 | 共享expert分离 | 14B对fused_moe内部不熟 |

---

### 第2轮: 深入MXFP4 GEMM优化

#### 本地14B推演
```python
# 优化1: 消除不必要的contiguous()调用
# A和B已经是contiguous的(randn生成),无需再调
# 优化2: 内联_quant_mxfp4,减少函数调用开销
# 优化3: 预分配输出tensor,避免gemm_a4w4内部分配
```

#### GLM-5推演
```python
# 关键洞察: aiter有两条GEMM路径
# 路径1: CK gemm_a4w4 (当前reference用的)
# 路径2: Triton gemm_afp4wfp4 (reference.py注释提到)
# 
# Triton路径可能对小M有更好的性能!
# 因为Triton可以自适应tile size,而CK用固定tile
#
# 另外: 对于M=4的极端case:
# 可以考虑把GEMM转换为向量-矩阵乘(GEMV)
# 用tl.load + tl.dot的方式手写
```

#### 差异记录
| 项目 | 本地14B | GLM-5 | 差异原因 |
|------|---------|-------|---------|
| GEMM路径选择 | 只用CK | 尝试Triton路径 | GLM-5了解aiter双路径 |
| 小M优化 | 无 | 考虑GEMV | GLM-5了解GEMV/GEMM切换点 |
| launch开销 | 接受2次launch | 尝试fuse | GLM-5对kernel fusion更熟 |

---

### 第3轮: 深入MLA Decode优化

#### 本地14B推演
```python
# 关键参数调优:
# NUM_KV_SPLITS: 32是否最优? 
# - bs=4,kv=1024: total_kv=4096, 4096/32=128 per split → 可能太少
# - bs=256,kv=8192: total_kv=2M, 2M/32=64K per split → 合理
# 建议: 根据total_kv动态选择splits
#   small (total_kv < 16K): splits=16
#   medium (16K-256K): splits=32
#   large (>256K): splits=64

# 预分配优化:
# kv_indices每次都重新arange → 可预分配
# metadata每次都重建 → 可缓存
```

#### GLM-5推演
```python
# 核心洞察: MXFP4 KV cache是最大赢面
# 
# 当前fp8 KV: 576 bytes/token → MXFP4: 288+18=306 bytes/token (47%节省)
# 
# 但aiter的mla_decode_fwd可能不直接支持MXFP4 KV
# 需要检查: 是否有a4w4的MLA kernel?
# 
# 如果没有,备选方案:
# 1. 写自定义Triton FlashDecoding kernel (M5)
#    - 从HBM读MXFP4 KV → 在寄存器/LDS中dequant → bf16
#    - 执行QK^T → softmax → V multiply
#    - 这是最大的工程挑战但也是最大的性能赢面
#
# 2. a16w8 (bf16 Q + fp8 KV): 跳过Q量化开销
#    - Q量化对小batch影响大(~1μs / quantize_fp8调用)
#    - a16w8 kernel: mla_a16w8_qh16_m16x4_n16x1_coex0_mask1_ps
#    - 可能比a8w8 + Q量化开销更快
```

#### 差异记录
| 项目 | 本地14B | GLM-5 | 差异原因 |
|------|---------|-------|---------|
| KV precision | 保持fp8 | 尝试MXFP4 | GLM-5理解带宽瓶颈更深 |
| splits调优 | 固定值 | 动态选择 | GLM-5了解split-reduce tradeoff |
| Q precision | 保持fp8 | 尝试跳过量化 | GLM-5对a16w8路径更熟 |

---

### 第4轮: 深入MoE优化

#### 本地14B推演
```python
# fused_moe参数分析:
# doweight_stage1=False (当前) vs True
#   False: 权重在Stage2后应用
#   True: 权重在Stage1后应用
#   对于SwiGLU, False更合理(减少乘法次数)
#
# expert_mask=None: 不过滤expert
# 可以尝试设置expert_mask来跳过空expert (bs小时有效)
#
# 关键: fused_moe是CK kernel,参数空间有限
```

#### GLM-5推演  
```python
# 深度分析:
# 
# 1. 共享expert优化 (E2):
#    shared expert处理ALL tokens → 这是一个dense GEMM
#    当前: shared expert混在routed experts中,经过MoE路由逻辑
#    优化: 把shared expert单独提出来做dense GEMM
#    
#    实现:
#    - topk_ids最后1列是shared expert → 分离出来
#    - routed: fused_moe with topk=8 (不含shared)  
#    - shared: 标准gemm_a4w4 (dense, 无路由开销)
#    - 合并: output = routed_output + shared_output
#    
#    收益: 减少shared expert的路由overhead
#    风险: 两次kernel launch vs 一次fused
#
# 2. 对于小bs+大E(257 experts):
#    大部分expert只分配到0-1个token → 极度稀疏
#    CK的fused_moe用padding处理 → 浪费
#    自定义compact dispatch可以消除padding
#
# 3. 对于大bs+小E(33 experts, d_expert=2048):
#    每个expert分配到~bs*9/33≈139个token
#    GEMM粒度足够大 → split-K可以进一步提速
```

#### 差异记录
| 项目 | 本地14B | GLM-5 | 差异原因 |
|------|---------|-------|---------|
| 参数调优 | doweight_stage1 | 整体架构重构 | GLM-5看到了结构性优化 |
| 共享expert | 不分离 | 分离为dense GEMM | GLM-5理解MoE稀疏性 |
| 稀疏优化 | 无 | compact dispatch | GLM-5了解CK内部实现 |

---

### 第5轮: 综合最优策略确定

#### 最终优化方案 (融合本地14B + GLM-5见解)

##### MXFP4 GEMM — 最终方案
```
优先级1 (必做): 消除冗余操作 + 预分配
优先级2 (尝试): aiter Triton GEMM路径 (gemm_afp4wfp4)
优先级3 (高风险): 自定义Triton fused quant+GEMM
```

##### MLA Decode — 最终方案
```
优先级1 (必做): 动态NUM_KV_SPLITS + 预分配metadata
优先级2 (尝试): a16w8路径 (跳过Q量化)
优先级3 (高风险): MXFP4 KV + 自定义FlashDecoding
```

##### MXFP4 MoE — 最终方案
```
优先级1 (必做): 参数调优 (expert_mask, doweight_stage1)
优先级2 (尝试): 共享expert分离为dense GEMM
优先级3 (高风险): 自定义Triton fused MoE kernel
```

#### 5轮差异汇总
| 轮次 | 关键差异 | 差异原因 | 采纳决策 |
|------|---------|---------|---------|
| 1 | 保守vs激进 | 14B风险规避,GLM-5追求极致 | 分层实施:先稳后激进 |
| 2 | CK-only vs Triton双路径 | 14B不了解Triton GEMM | 采纳GLM-5:尝试Triton |
| 3 | 固定splits vs MXFP4 KV | 14B对带宽计算不够深 | 采纳GLM-5:MXFP4是关键 |
| 4 | 参数调优 vs 架构重构 | 14B对fused_moe内部不熟 | 先参数调优,再尝试分离 |
| 5 | 综合 | — | 三级优先级分层实施 |

---

## 第四部分: 实施计划

### Phase 1: 安全提交 (先拿分)
- [x] 直接提交reference submission → 建立baseline排名
- [ ] 每个kernel做最小优化 → 提交更新

### Phase 2: 中等优化
- [ ] GEMM: Triton路径 + 预分配
- [ ] MLA: 动态splits + 预分配metadata
- [ ] MoE: 参数调优

### Phase 3: 极限优化
- [ ] GEMM: Fused quant+GEMM
- [ ] MLA: MXFP4 KV
- [ ] MoE: 共享expert分离

### 提交命令
```bash
# MXFP4 GEMM
popcorn submit --leaderboard amd-mxfp4-mm --gpu MI355X --mode leaderboard mx_fp4_mm_optimized.py

# MLA Decode
popcorn submit --leaderboard amd-mixed-mla --gpu MI355X --mode leaderboard mixed_mla_optimized.py

# MXFP4 MoE
popcorn submit --leaderboard amd-moe-mxfp4 --gpu MI355X --mode leaderboard moe_mxfp4_optimized.py
```

---

*生成: 2026-03-24 | 参赛者: Zhao Dylan | 5轮推演完成*
