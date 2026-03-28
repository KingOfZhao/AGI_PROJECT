# AI 执行清单 — 每次运行前必读

> 本文档是 AI 助手在每次执行任务前的强制扫描清单。
> 最后更新: 2026-03-26

---

## 一、项目突破点清单

### 🔴 紧急突破 (当前瓶颈)

| ID | 突破点 | 当前值 | 目标值 | 突破路径 |
|----|--------|--------|--------|----------|
| B1 | SWE-Bench 通过率 | 35% | 55% | 多文件编辑pipeline + AST差分 + 测试自动生成 |
| B2 | 技能库有效率 | 64% | 80% | 清理935个占位符, 补全实际代码 |
| B3 | proven节点数 | 1200 | 2000 | 极致推演引擎5轮+ 自成长引擎并行20轮 |
| B4 | S3王朝治理实现度 | 60% | 85% | 完善反贼检测规则, 增加架构缺陷自修复 |
| B5 | S2技能库锚定 | 70% | 90% | SkillSearcher索引优化, 语义匹配增强 |

### 🟡 重要突破 (能力提升)

| ID | 突破点 | 当前值 | 目标值 | 突破路径 |
|----|--------|--------|--------|----------|
| B6 | 95维编码均分 | 84.2 | 87.0 | 弱项提升: 多语言/200K上下文/Computer Use |
| B7 | 多语言能力(Rust/Go/Java) | 55 | 75 | 专项碰撞推演 + 跨语言模式提取 |
| B8 | 代码解释能力 | 75 | 82 | 上下文增强 + AST分析 + 链式推理 |
| B9 | API响应延迟 | ~3s | ~1.5s | proven快速路径 + 缓存预热 + 语义索引 |
| B10 | Agent自治能力 | 40% | 70% | 工具锻造 + 自主学习循环 + 自我修复 |

### 🟢 长期突破 (战略方向)

| ID | 突破点 | 描述 |
|----|--------|------|
| B11 | 200K上下文稳定处理 | 超长上下文窗口下的稳定推理 |
| B12 | Computer Use集成 | 屏幕操作 + 浏览器自动化 |
| B13 | 跨域迁移 | 代码→工业→医疗→商业知识迁移 |
| B14 | 多Agent协作 | Agent间通信 + 任务分配 + 结果汇总 |

---

## 二、8大超越策略检查

每次推演前确认以下策略是否被正确调用:

| 检查项 | 策略 | 模块 | 状态 |
|--------|------|------|------|
| [ ] | S1 ULDS 11律约束注入 | `core/extreme_deduction_engine.py` | 必须 |
| [ ] | S2 技能库锚定(2624技能) | `SkillSearcher` | 必须 |
| [ ] | S3 王朝治理(反贼检测) | `GovernanceChecker` | 必须 |
| [ ] | S4 四向碰撞(上下左右) | `CollisionEngine` | 必须 |
| [ ] | S5 5级真实性验证 | `NodeTruthClassifier` | 推荐 |
| [ ] | S6 并行推理(多模型) | `orchestrator.py` | 推荐 |
| [ ] | S7 零回避扫描(12灾难) | `ZeroAvoidanceScanner` | 推荐 |
| [ ] | S8 链式收敛(F→V→F) | `ChainLinkTracker` | 推荐 |

---

## 三、Shell/命令安全规则 (永久生效)

### 🚫 绝对禁止的危险模式

以下模式会导致 shell 进入交互等待状态, **必须在生成命令前检查并避免**:

#### 1. 引号未闭合
```
❌ echo "hello world        → dquote> 等待闭合
❌ echo 'hello world        → quote> 等待闭合
✅ echo "hello world"       → 正确
✅ echo 'hello world'       → 正确
```

**规则**: 每条命令中双引号 `"` 和单引号 `'` 必须成对出现。如果字符串包含引号, 使用转义 `\"` 或切换引号类型。

#### 2. 括号未闭合
```
❌ if [ -f test.py           → > 等待闭合
❌ echo $(date               → )> 等待闭合
❌ function foo {             → }> 等待闭合
✅ if [ -f test.py ]; then echo ok; fi
✅ echo $(date)
✅ function foo { echo ok; }
```

**规则**: 所有 `(` `)` `[` `]` `{` `}` 必须配对。`if/then` 必须有 `fi`, `do` 必须有 `done`, `case` 必须有 `esac`。

#### 3. 反引号未闭合
```
❌ echo `date                → `> 等待闭合
✅ echo `date`               → 正确
✅ echo $(date)              → 推荐用 $() 替代反引号
```

**规则**: 优先使用 `$()` 替代反引号, 支持嵌套且不易出错。

#### 4. 管道/续行未完成
```
❌ cat file.txt |            → > 等待下一条命令
❌ echo hello \              → > 等待续行内容
✅ cat file.txt | grep pattern
✅ echo hello world
```

**规则**: 管道 `|` 后必须紧跟命令。反斜杠 `\` 续行后必须有下一行内容。

#### 5. Here-Document 未结束
```
❌ cat << EOF                → heredoc> 等待 EOF
   hello world
   (忘记写 EOF)
✅ cat << EOF
   hello world
   EOF
```

**规则**: Here-Document 的结束标记必须独占一行, 且前面不能有空格(除非用 `<<-`)。

#### 6. Python/代码字符串中的引号
```
❌ python3 -c "print("hello")"     → 引号冲突
✅ python3 -c "print('hello')"     → 单双引号交替
✅ python3 -c 'print("hello")'     → 单双引号交替
```

**规则**: 当命令中嵌入代码时, 外层和内层使用不同类型的引号。

### ✅ 命令生成检查清单

生成每条 shell 命令前, 必须通过以下检查:

1. **引号配对检查**: 统计 `"` 和 `'` 数量, 各自必须为偶数(转义的不算)
2. **括号配对检查**: `(` = `)`, `[` = `]`, `{` = `}`
3. **控制结构检查**: `if→fi`, `do→done`, `case→esac`, `while/for→do→done`
4. **管道完整检查**: `|` 后必须有命令, `\` 后必须有续行
5. **Here-Doc检查**: `<<` 后的标记必须在后续行中出现作为结束
6. **嵌套引号检查**: 代码字符串中的引号不与外层冲突
7. **特殊字符检查**: `$`, `!`, `*` 在双引号中可能被展开, 需要时使用单引号或转义

### 🔧 安全命令模板

```bash
# 安全的多行命令 (用 && 连接, 不用续行符)
cmd1 && cmd2 && cmd3

# 安全的条件执行
test -f file.txt && echo "exists" || echo "not found"

# 安全的变量赋值
VAR="value with spaces"

# 安全的 Python 执行
python3 -c 'import sys; print(sys.version)'

# 安全的 grep (用单引号包裹正则)
grep -rn 'pattern' /path/to/dir

# 安全的 find
find /path -name '*.py' -type f

# 安全的循环 (单行)
for f in *.py; do echo "$f"; done
```

---

## 四、代码生成安全规则

### 正则表达式安全
```python
# ❌ 未转义的特殊字符
re.search("O(n^2)", text)      # 括号被当作分组
# ✅ 正确转义
re.search(r"O\(n\^2\)", text)  # 使用 raw string + 转义
```

### 路径安全
```python
# ❌ 硬编码路径
path = "/Users/administruter/Desktop/AGI_PROJECT/api_server.py"
# ✅ 动态路径
path = Path(__file__).resolve().parent / "api_server.py"
```

### Import 安全
```python
# 移动文件后, 确保 sys.path 包含正确目录
# 使用 _paths.py 或 PYTHONPATH 环境变量
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
```

---

## 五、推演前环境检查

```bash
# 1. Ollama 是否运行
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; print(json.load(sys.stdin)['models'][0]['name'])"

# 2. PYTHONPATH 是否设置
echo $PYTHONPATH | grep -q "core" && echo "OK" || echo "需要: export PYTHONPATH=core:api:."

# 3. 虚拟环境是否激活
which python3 | grep -q "venv" && echo "venv OK" || echo "需要: source venv/bin/activate"

# 4. 端口是否可用
lsof -i :5002 >/dev/null 2>&1 && echo "5002被占用" || echo "5002可用"
```

---

> **本文档由 AI 在每次执行任务前自动扫描。如需修改突破点或规则, 直接编辑本文件。**
