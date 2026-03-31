# DiePre 刀模设计 — 会话总结 (2026-03-29)

> 供新会话快速恢复上下文用

---

## 一、已完成能力

### 鸡蛋保护垫参数化生成器 ✅
- **文件**: `项目清单/刀模活字印刷3D项目/egg_protector_generator.py`
- **参数**: D=45, d=37.9, n=8, α=12°(顶弧半角)
- **几何**: n瓣环形排列, 每瓣=外径圆弧(2α)+两腰直线, 底端点在内径圆上
- **角度约束**: α≤13.8°时顶角和连接角都>90°; α=12°时顶角131.8°/连接角104.5°
- **DXF**: 原生ARC实体, 图层CUT(红), 支持2000/2004/2007/2010/2013/2018
- **输出**: `output/egg_protector_D45_d37.9_AC2007.dxf` + preview.png
- **关键公式**: 见 `memory/2026-03-29.md` 中"鸡蛋保护垫数学公式"段

### DiePre后端API端点 ✅
- **文件**: `/Users/administruter/Desktop/DiePre AI/backend/app/routes/reasoning.py`
- `/image/analyze` — 图片上传识别 → 返回参数清单 (690行)
- `/image/generate-dieline` — 用户填尺寸 → 生成entities (831行)
- `/export/dxf` — entities → DXF下载, 支持版本选择 (1031行)
- `/text/analyze` — 文字描述 → 识别类型 → 返回参数清单 (NEW, ~1009行)
- **支持类型**: 鸡蛋保护垫/圆形盒/天地盖/矩形盒

### 公差分析引擎 ✅
- `core/error_budget.py` — 公差-成本优化, 7种制造资源库
- `core/monte_carlo_tolerance.py` — 蒙特卡洛公差链模拟
- `core/drift_tracker.py` — MC参数漂移追踪
- 已集成DiePre后端4个公差API端点

### 锁舌绘制 (进行中)
- **六边形**: 顶34→斜边→最长44.56→斜边→底42.1, 高14.16mm
- **输出**: `output/lock_tab_hex_AC2007.dxf`
- **待确认**: 用户说"两个顶外角弧度179", 含义未明, R=3圆角已生成待审

---

## 二、待办 (按优先级)

| # | 任务 | 状态 | 依赖 |
|---|------|------|------|
| 1 | 后端API同步鸡蛋保护垫为圆弧+α版本 | ⏳ | 用户确认形状OK后 |
| 2 | 锁舌"外角弧度179"确认 | ⏳ | 等用户回复 |
| 3 | 前端适配ARC实体渲染 | ⏳ | |
| 4 | 3D预览重构(CadPreview3D.vue) | 🔒 | 需用户决策 |
| 5 | skill节点高价值代码提取(反向贝叶斯网络) | ⏳ | |
| 6 | 知识采集(需VPN, DuckDuckGo被墙) | 🔒 | |

---

## 三、关键约束

- **DXF**: 禁止未定义linetype, 必须BYLAYER; 图层CUT(红)/CONSTRUCTION(灰)
- **API**: 只走 `https://open.bigmodel.cn/api/anthropic`, 严禁PAAS直连
- **安全**: 外部代码走Docker沙箱, 镜像源 `docker.1panel.live`
- **前端**: Step1 analyze → Step2 generate-dieline, `/text/analyze`新增文字入口
- **端口**: 后端8000, 前端5173, `lsof -ti:8000 | xargs kill -9` 后重启

---

## 四、关键文件路径

| 文件 | 路径 |
|------|------|
| 鸡蛋保护垫生成器 | `项目清单/刀模活字印刷3D项目/egg_protector_generator.py` |
| DXF输出目录 | `项目清单/刀模活字印刷3D项目/output/` |
| 后端reasoning | `/Users/administruter/Desktop/DiePre AI/backend/app/routes/reasoning.py` |
| 前端刀版设计 | `/Users/administruter/Desktop/DiePre AI/frontend/src/views/DielineDesign.vue` |
| 公差引擎 | `core/error_budget.py`, `core/monte_carlo_tolerance.py`, `core/drift_tracker.py` |
| 设备数据库 | `core/machine_database.py` (7台设备) |
| 标准库 | `core/standards_database.py` (18条已知事实+5公式) |
| 认知核心 | `core/cognitive_core.py` (568行) |
| Docker沙箱 | `core/docker_sandbox.py` + `docker/Dockerfile.sandbox` |
| Skill索引 | `data/skill_index.json` (2556节点) |

---

## 五、DiePre知识库状态

- 总节点3746, 已确认2237, 争议1439, 碎片率22%
- 确认知识库: `confirmed_knowledge_base.md` (3126行)
- **30条关键已知**: 见 `MEMORY.md` "DiePre 项目关键已知"段
- **深度推演**: K因子相变/微瓦楞E-F参数/裱合耦合/RSS非正态/四国标准矩阵
