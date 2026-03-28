# AMD GPU Kernel 算子推演数据汇总

## 竞赛信息
- **竞赛**: AMD Developer Challenge February 2026
- **硬件**: AMD Instinct MI355X (CDNA4, gfx950)
- **截止日期**: 2026-04-07 07:59 UTC
- **参赛者**: Zhao Dylan

## 三大算子

| 算子 | Leaderboard | 最高分 | 当前状态 | 当前几何均值 |
|------|------------|--------|---------|------------|
| MXFP4 GEMM | amd-mxfp4-mm | 1000 | ✅ 已上榜 | ~24µs |
| MLA Decode | amd-mixed-mla | 1250 | ⚠️ Leaderboard失败 | ~100µs |
| MXFP4 MoE | amd-moe-mxfp4 | 1500 | ❌ 正确性失败 | 未知 |

## 文件索引

| 文件 | 描述 |
|------|------|
| `MXFP4_MoE_ULDS推演报告.md` | MoE算子ULDS v2.1极致推演报告 |
| `三算子迭代历史汇总.md` | 三个算子的全部版本迭代记录 |
| `README.md` | 本文件 |

## 源数据位置
- 算子代码: `/Users/administruter/Desktop/flutterProject/reference-kernels-local/problems/amd_202602/`
- 优化清单: `/Users/administruter/Desktop/AGI_PROJECT/docs/AMD_GPU_Kernel_优化清单.md`
- 20轮分析: `/Users/administruter/Desktop/AGI_PROJECT/docs/AMD_20轮极限优化分析.md`
- 安全策略: `/Users/administruter/Desktop/AGI_PROJECT/docs/待添加/AMD_v5_Leaderboard安全策略全记录.md`
- 提交日志: `/Users/administruter/Desktop/flutterProject/reference-kernels-local/problems/amd_202602/submit_log_20260325_204833.txt`
