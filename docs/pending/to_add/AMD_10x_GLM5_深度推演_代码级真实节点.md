# AMD GPU Kernel 10x GLM-5 深度推演 — 代码级真实节点 + 100x自成长架构

## 时间: 2026-03-23 22:45
## 目标: 穷尽 leaderboard-safe 优化节点 + 设计100x GLM-5多线程自成长引擎

---

## 第一部分: 三大Kernel全部优化节点汇总

### 1.1 MXFP4 GEMM — 当前v5 (25行, ~24µs baseline)

**当前代码热路径**: `dynamic_mxfp4_quant → e8m0_shuffle → gemm_a4w4` = 3次kernel launch

| 节点ID | 优化项 | 类型 | 预期收益 | Leaderboard安全 | 实现难度 | 状态 |
|--------|--------|------|---------|----------------|---------|------|
| G1 | Triton GEMM路径 (gemm_afp4wfp4) | 替代kernel | 10-20% | ✅ | 中 | 待验证API |
| G2 | 融合quant+shuffle为单Triton kernel | kernel融合 | 15-25% (省1 launch) | ✅ | 高 | 未实现 |
| G3 | 预分配输出tensor | 内存优化 | 3-5% | ✅ | 低 | 未实现 |
| G4 | 小M专用GEMV路径 (M=4) | 算法选择 | 10-30% (仅M≤8) | ✅ | 中 | 未实现 |
| G5 | Python开销极限压缩 | 解释器优化 | 1-2% | ✅ | 低 | 已做 |

**关键差距**: 当前~24µs vs #1的8.09µs = **3x差距**
- 但8.09µs是含Graph/缓存的benchmark数字，leaderboard真实性能未知
- 如果#1也是纯计算路径，差距可能来自Triton GEMM路径

**G1深度分析 — Triton GEMM**:
```python
# reference.py line 101 提到的路径:
from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import matmul_afp4wfp4
# 可能的API:
# matmul_afp4wfp4(A_fp4, B_fp4, A_scale, B_scale) → bf16 output
# 优势: Triton自适应tile size, 对小M(4-32)可能有更好的CU利用率
# 风险: API签名未知, scale格式可能需要非shuffled版本
```

### 1.2 MLA Decode — 当前v9 (110行, ~60-200µs)

**当前代码热路径**: config-keyed metadata缓存 + 动态Q dtype + mla_decode_fwd

| 节点ID | 优化项 | 类型 | 预期收益 | Leaderboard安全 | 实现难度 | 状态 |
|--------|--------|------|---------|----------------|---------|------|
| M1 | **MXFP4 KV cache** | 带宽优化 | **30-47%** | ✅ (rtol=0.1) | 高 | 关键路径 |
| M2 | 动态NUM_KV_SPLITS | 参数调优 | 5-15% | ✅ | 低 | ✅已实现 |
| M3 | Config-keyed metadata缓存 | 避免重复计算 | ~20µs/call | ✅ | 低 | ✅已实现 |
| M4 | bf16 Q跳过量化 (小batch) | 省kernel | 3-5% | ✅ | 低 | ✅已实现 |
| M5 | fp8 Q量化内联 (大batch) | 省函数调用 | 1-2% | ✅ | 低 | ✅已实现 |
| M6 | 预分配输出tensor | 内存优化 | 2-3% | ✅ | 低 | ✅已实现 |
| M7 | 自定义Triton FlashDecoding | 重写kernel | 20-40% | ✅ | 极高 | 未实现 |

**关键差距**: 当前~60-200µs vs #1的32.97µs
- **M1 MXFP4 KV是唯一能跨越差距的方案**
- bs=256,kv=8192: fp8 KV=1.18GB, mxfp4 KV=0.63GB → **47%带宽节省**
- check_implementation容差: rtol=0.1, atol=0.1 + 5% mismatch_ratio容忍
- 数据已提供: `kv_data["mxfp4"] = (fp4x2_tensor, e8m0_scale)`

**M1关键代码路径**:
```python
# 问题: mla_decode_fwd是否接受fp4x2格式的kv_buffer?
# kv_4d = kv_mxfp4.view(total_kv, PAGE_SIZE, nkv, dim//2)  # fp4x2
# kv_scale = mxfp4_scale  # block-wise E8M0, 非scalar
# 
# fp8路径: kv_scale是scalar float32 → API简单
# mxfp4路径: kv_scale是[total_kv*nkv, dim//32] E8M0 → API可能不兼容
#
# 策略: try/except, 失败则回退fp8
```

### 1.3 MXFP4 MoE — 当前v7 (34行, ~150-340µs)

**当前代码**: 直接调用fused_moe, 与reference完全相同

| 节点ID | 优化项 | 类型 | 预期收益 | Leaderboard安全 | 实现难度 | 状态 |
|--------|--------|------|---------|----------------|---------|------|
| E1 | fused_moe参数调优 | 参数 | 5-10% | ✅ | 低 | 部分 |
| E2 | Shared expert分离为dense GEMM | 算法重构 | **-1µs到+31%** | ✅ | 中 | 分析完成:不划算 |
| E3 | expert_mask过滤空expert | 调度优化 | 3-8% (小bs) | ✅ | 低 | 未实现 |
| E4 | 预计算padding参数 | Python优化 | 1-2% | ✅ | 低 | ✅已实现 |
| E5 | 自定义Triton fused MoE | 重写kernel | 20-40% | ✅ | 极高 | 未实现 |

**关键差距**: 当前~150-340µs vs #1的109.79µs = **1.5x差距**
- fused_moe是CK kernel, Python层几乎无优化空间
- E3(expert_mask)是唯一低风险可尝试项
- E5(自定义kernel)是唯一能大幅超越的路径, 但工程量极大

**E3实现方案**:
```python
# 小bs (16)时, 257个expert中大部分分配0 token
# expert_mask可以跳过空expert的work group分配
# 实现: 
# mask = torch.zeros(E_total, dtype=torch.bool, device="cuda")
# active = topk_ids.unique()
# mask[active] = True
# fused_moe(..., expert_mask=mask)
```

### 1.4 eval.py关键发现汇总

| 发现 | 影响 | 应对 |
|------|------|------|
| leaderboard: recheck=True, 每次regenerate数据 | Graph/缓存全部失效 | ✅已处理(v5) |
| MoE eval.py: _clone_data返回原数据不clone | fused_moe对clone敏感 | 无优化空间 |
| L2 cache每次清除 (16GB dummy alloc) | 无法利用L2局部性 | 接受 |
| 几何均值排名 | 最差case权重很大 | 优化最慢case优先 |
| max_repeats=100, max_time=30s | ~100次迭代取均值 | 稳定性很重要 |

---

## 第二部分: 100x GLM-5 多线程自成长架构设计

### 2.1 当前瓶颈分析

当前 `growth_engine.py` 的GLM-5调用模式:
```
[串行] Phase1(top_down) → Phase2(bottom_up) → Phase3(horizontal×2) → 
       Phase4(deep_reasoning) → Phase4.5(code_domain) → Phase5(falsify×N) → 
       Phase6(convert×N) → Phase7(validate) → Phase8(visualize)
```

**问题**:
- 每轮~9次GLM-5调用, 每次2s rate-limit + ~30-60s响应 = **~500s/轮**
- 单线程串行: CPU空闲等待API响应
- Phase5证伪: N个节点逐个串行调用 = N × 60s

**100x消耗量目标**: 当前~70K tokens/轮 → 目标 **7M tokens/轮**

### 2.2 多线程并发架构

```
                    ┌─ Thread Pool (8-16 workers) ─┐
                    │                               │
  ┌─────────────┐   │  ┌──────┐  ┌──────┐          │
  │ Task Queue  │──▶│  │GLM-5 │  │GLM-5 │  ...×16  │
  │ (优先级队列) │   │  │Call-1│  │Call-2│          │
  └─────────────┘   │  └──────┘  └──────┘          │
        ▲           │      │         │              │
        │           └──────┼─────────┼──────────────┘
        │                  ▼         ▼
  ┌─────────────┐   ┌─────────────────┐
  │ Result Queue │◀──│  Response Pool  │
  └─────────────┘   └─────────────────┘
        │
        ▼
  ┌─────────────────────────────────┐
  │ Aggregator (主线程)              │
  │ - 收集结果                      │
  │ - 去重/合并                     │
  │ - 写入DB                       │
  │ - 触发下游Phase                │
  └─────────────────────────────────┘
```

### 2.3 可并行Phase分析

| Phase | 可并行 | 依赖 | 并发度 | 说明 |
|-------|--------|------|--------|------|
| 1 top_down | ✅ | 无 | ×4 (4个不同问题) | 每轮同时拆解4个大问题 |
| 2 bottom_up | ✅ | 无 | ×3 (3组不同节点) | 每轮从3个角度归纳 |
| 3 horizontal | ✅ | 无 | ×6 (6对跨域) | 每轮碰撞6对域 |
| 4 deep_reasoning | ✅ | 无 | ×2 (不同节点集) | 两组节点并行推演 |
| 4.5 code_domain | ✅ | 无 | ×5 (5组维度全做) | **关键**: 全部5组维度每轮都做 |
| 5 falsify | ✅ | 1-4.5 | ×N (每节点独立) | **最大并行**: 所有节点同时证伪 |
| 6 convert | ✅ | 5 | ×N (每节点独立) | 所有proven节点同时生成SKILL |
| 7 validate | ❌ | 6 | ×1 | 本地校验,无需API |

**并发后每轮调用次数**:
- Phase1: 4次 (并行)
- Phase2: 3次 (并行)  
- Phase3: 6次 (并行)
- Phase4: 2次 (并行)
- Phase4.5: 5次 (并行)
- Phase5: ~40次 (并行, ~20个节点×2重试)
- Phase6: ~15次 (并行)
- **总计: ~75次/轮** (vs 当前~9次)
- **Tokens: ~600K/轮** (vs 当前~70K)

### 2.4 代码领域真实节点增长策略

当前code_domain每轮只做1组(4个维度), 5轮才覆盖全部20维度。

**100x方案**: 每轮全部5组同时推演, 且每组内4个维度各自独立调用 = **20路并行**

**更深层: 代码领域专项碰撞**

在Phase3(左右重叠)中增加代码领域专项碰撞对:
```python
CODE_COLLISION_PAIRS = [
    ("gpu_kernel_optimization", "triton_compiler"),      # GPU优化×Triton编译器
    ("memory_bandwidth", "quantization_theory"),          # 内存带宽×量化理论
    ("cuda_graph", "kernel_fusion"),                      # CUDA Graph×Kernel融合
    ("moe_routing", "load_balancing"),                    # MoE路由×负载均衡
    ("attention_mechanism", "memory_hierarchy"),           # 注意力×内存层级
    ("compiler_optimization", "hardware_architecture"),    # 编译器优化×硬件架构
    ("numerical_precision", "neural_network_training"),    # 数值精度×神经网络训练
    ("parallel_computing", "algorithm_design"),            # 并行计算×算法设计
]
```

### 2.5 GLM-5 API并发限制分析

智谱GLM-5 API特征:
- 接口: Anthropic兼容 (`/api/anthropic/v1/messages`)
- 当前rate-limit: `time.sleep(2)` = 0.5 QPS
- 预估并发上限: **8-16 QPS** (需实测)
- 超出限制: HTTP 429 Too Many Requests

**自适应限速策略**:
```python
class AdaptiveRateLimiter:
    def __init__(self, initial_qps=2.0, max_qps=16.0):
        self.qps = initial_qps
        self.max_qps = max_qps
        self.success_streak = 0
        self.lock = threading.Lock()
    
    def wait(self):
        with self.lock:
            time.sleep(1.0 / self.qps)
    
    def on_success(self):
        with self.lock:
            self.success_streak += 1
            if self.success_streak >= 10:
                self.qps = min(self.qps * 1.5, self.max_qps)
                self.success_streak = 0
    
    def on_rate_limit(self):
        with self.lock:
            self.qps = max(self.qps * 0.5, 0.5)
            self.success_streak = 0
```

---

## 第三部分: 代码领域真实节点图谱

### 3.1 AMD GPU Kernel 优化 — 可验证真实节点

每个节点都是经过代码验证的、有具体µs数字的真实知识。

```
[根节点] MI355X MXFP4 Kernel优化
├── [GEMM分支]
│   ├── ✅ [G-N1] dynamic_mxfp4_quant是Triton kernel (已验证)
│   ├── ✅ [G-N2] e8m0_shuffle是独立Triton kernel (已验证)
│   ├── ✅ [G-N3] gemm_a4w4是CK kernel, 需shuffled输入 (已验证)
│   ├── ✅ [G-N4] leaderboard每次regenerate数据, Graph无效 (已验证)
│   ├── ❓ [G-N5] gemm_afp4wfp4 Triton路径是否更快? (待验证)
│   └── ❓ [G-N6] 融合quant+shuffle能否省1个launch? (待验证)
│
├── [MLA分支]
│   ├── ✅ [M-N1] metadata仅依赖(bs,qsl,kvsl), 不依赖seed (已验证)
│   ├── ✅ [M-N2] 动态NUM_KV_SPLITS: 8/16/32/64按total_kv (已验证)
│   ├── ✅ [M-N3] bf16 Q对小batch更快(省quant) (已验证)
│   ├── ✅ [M-N4] fp8 Q对大batch更快(高吞吐) (已验证)
│   ├── ❓ [M-N5] mla_decode_fwd是否支持fp4x2 KV输入? (关键待验证)
│   ├── ❓ [M-N6] MXFP4 KV精度是否通过10%容差? (关键待验证)
│   └── ❓ [M-N7] block-wise E8M0 scale如何传入kv_scale? (待验证)
│
├── [MoE分支]
│   ├── ✅ [E-N1] fused_moe CK kernel处理全部逻辑(quant+GEMM+SwiGLU+reduce) (已验证)
│   ├── ✅ [E-N2] shared expert分离对大多数case不划算(-1µs) (已验证)
│   ├── ✅ [E-N3] _clone_data在MoE eval中不clone(fused_moe对地址敏感) (已验证)
│   ├── ❓ [E-N4] expert_mask过滤空expert是否有效? (待验证)
│   └── ❓ [E-N5] doweight_stage1=True是否更快? (待验证)
│
└── [跨域节点]
    ├── ✅ [X-N1] leaderboard用CUDA Events GPU计时, 不含CPU开销 (已验证)
    ├── ✅ [X-N2] 几何均值排名 = 最差case影响最大 (已验证)
    ├── ✅ [X-N3] clear_l2_cache分配16GB dummy tensor (已验证)
    └── ✅ [X-N4] Python开销不计入GPU时间但影响总迭代速度 (已验证)
```

### 3.2 自成长引擎 — 代码领域节点生长路径

```
[阶段1: 当前] 串行GLM-5, ~70K tokens/轮
    ↓ (升级多线程)
[阶段2: 并行] 8-16线程GLM-5, ~600K tokens/轮 (8.5x)
    ↓ (增加代码碰撞对)
[阶段3: 代码专项] 20维度全并行 + 代码碰撞对, ~2M tokens/轮 (28x)
    ↓ (多轮快速迭代)
[阶段4: 100x] 每小时5轮 × 2M = 10M tokens/小时 (100x+)
```

---

## 第四部分: 实施代码 — 多线程GLM-5调用器

### 4.1 核心类: ParallelGLM5Caller

见 growth_engine.py 升级代码 (下方实现)

### 4.2 升级要点

1. **ThreadPoolExecutor替代串行调用**: 最大16并发
2. **自适应限速**: 成功时加速, 429时减速
3. **Phase依赖图**: Phase1-4.5并行 → Phase5并行 → Phase6并行
4. **代码维度全覆盖**: 每轮5组×4维度 = 20维度同时推演
5. **结果聚合器**: 去重、合并、冲突检测
6. **断点续传**: checkpoint.json记录进度

*生成: 2026-03-23 22:50 | 推演强度: 10x GLM-5 | 自成长方向: 代码领域真实节点*
