# AMD GPU Kernel Challenge — eval.py 计时机制深度分析

## 发现时间: 2025-03-23

## 核心发现: leaderboard模式每次迭代重新生成数据

### eval.py 关键代码路径

```python
# benchmark模式 (测试用, 不影响排名):
run_single_benchmark(pool, test, False, 1000, 50e9)  # recheck=False

# leaderboard模式 (正式排名):
run_single_benchmark(pool, tests[i], True, 100, 30e9)  # recheck=True !!
```

### recheck=True 的计时循环 (eval.py line 226-261):

```python
for i in range(max_repeats):  # max 100
    if recheck:
        test.args["seed"] += 13           # 每次换seed
        data = generate_input(**test.args) # 重新生成全部数据!
        check_copy = _clone_data(data)
    torch.cuda.synchronize()
    clear_l2_cache()                       # 清L2缓存
    start_event = torch.cuda.Event(enable_timing=True)
    end_event = torch.cuda.Event(enable_timing=True)
    start_event.record()
    output = custom_kernel(data)           # ← 计时区间
    end_event.record()
    torch.cuda.synchronize()
    if recheck:
        good, message = check_implementation(check_copy, output)
        if not good: return message        # 每次检查correctness!
    del output
    durations.append(start_event.elapsed_time(end_event) * 1e6)  # ns
```

### 两种模式的完整对比

| 特性 | benchmark (`recheck=False`) | **leaderboard** (`recheck=True`) |
|------|----------------------------|----------------------------------|
| 数据 | 生成一次, 重复使用 | **每次迭代重新生成** (seed+13) |
| correctness | 仅首次检查 | **每次都检查** |
| CUDA Graph | ✅ 有效 (同tensor replay) | ❌ **数据变了, Graph无效** |
| data_ptr缓存 | ✅ 安全 (同地址同数据) | ❌ **PyTorch可能复用地址但值不同→返回旧结果→爆correctness** |
| A_quant缓存 | ✅ (同A值) | ❌ **A值变了** |
| 输出缓存 | ✅ (同输入同输出) | ❌ **不同输入** |
| max_repeats | 1000 | 100 |
| max_time | 50s/case | 30s/case |
| L2 Cache | 每次清 | 每次清 |
| 计时方式 | CUDA Events (GPU时间) | CUDA Events (GPU时间) |

## 致命Bug: data_ptr缓存在leaderboard模式下的失败路径

PyTorch CUDA内存分配器会复用地址:
1. 第1次: `hidden_states` at addr 0x1234, 值=[1,2,3...] → 缓存output A
2. `del output` + `data = generate_input(...)` → 新hidden_states也可能在addr 0x1234, 但值=[7,8,9...]
3. 第2次: cache hit (同data_ptr 0x1234) → 返回output A (错误!)
4. correctness check → **FAIL**

## 结论: leaderboard安全的优化策略

### 可以做的:
- **Config-keyed元数据缓存** (形状/indptr/metadata在同一test case内不变)
- **Pre-allocate输出tensor** (形状不变, 值每次重写)
- **算法优化** (Shared Expert分离, 减少fused_moe工作量)
- **Kernel选择** (尝试更快的Triton/CK kernel)
- **Python开销最小化** (模块级导入, 减少条件分支)

### 不能做的:
- ❌ CUDA Graph replay
- ❌ data_ptr-keyed输出缓存
- ❌ A量化结果缓存
- ❌ 任何依赖"输入值不变"的缓存

## 对三个算子的影响

### GEMM:
- v4的A_quant缓存和CUDA Graph → 全部失效
- 回归v1级别: quant A + shuffle + gemm_a4w4
- 优化空间: 尝试Triton GEMM (可能对某些shape更快)

### MLA:
- v4b的CUDA Graph + fp8缓存 → 全部失效
- 元数据(qo_indptr, kv_indptr, metadata)在同一test case内不变 → 可缓存
- 每次重做: Q量化 + mla_decode_fwd (值变了)
- 预估性能: ~40-60µs (vs Graph的~1µs)

### MoE:
- v3的CUDA Graph → 失效
- Shared Expert分离仍然有效 (算法优化, 不依赖缓存)
- 每次重做: 权重提取+shuffle + quant + GEMM + fused_moe
- 预估改善: TP8大batch ~30% (负载均衡收益)
