#!/usr/bin/env python3
"""
gstack Skill Importer — 安全扫描 + 导入到本地能力库
====================================================
1. 解析 gstack 仓库中全部 SKILL.md 文件
2. 安全扫描: 检查 telemetry / cookie / binary / shell 风险
3. 安全的 skill 保存到 workspace/skills/ (meta.json 格式)
4. gstack 自身架构逻辑也整理为一个 meta-skill
5. 生成安全扫描报告
"""

import re
import json
import datetime
from pathlib import Path
from typing import Optional
from collections import defaultdict

# ─────────────────────────── 路径配置 ───────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GSTACK_DIR = PROJECT_ROOT / "gstack"
LOCAL_SKILL_DIR = PROJECT_ROOT / "workspace" / "skills"
REPORT_PATH = PROJECT_ROOT / "docs" / "gstack_skill_scan_report.md"

# ─────────────────────────── 安全规则 ───────────────────────────

# 高风险关键词 (直接拦截)
BLACKLIST_PATTERNS = [
    r"\bblockchain\b", r"\bdefi\b",
    r"\bmalware\b", r"\bransomware\b", r"\btrojan\b",
    r"\bkeylog\b", r"\brootkit\b",
    r"\bphishing\b", r"\bcredential.harvest\b",
    r"\bcryptocurrency\b", r"\bcrypto\s*wallet\b", r"\bcrypto\s*token\b",
    r"\bmint\s*token\b", r"\bsmart\s*contract\b",
]

# crypto 上下文判断: 仅当 crypto 在加密货币上下文中才拦截
# "cryptographic", "crypto API", "crypto module" 等密码学用法不拦截
CRYPTO_SAFE_CONTEXTS = [
    "cryptographic", "crypto api", "crypto module", "crypto library",
    "webcrypto", "node:crypto", "crypto.subtle", "crypto random",
]

# 需要标记 WARNING 的特征
WARNING_FEATURES = {
    "telemetry": {
        "patterns": ["telemetry", "analytics", "usage data", "supabase"],
        "reason": "包含遥测/数据收集功能 (opt-in, 但需注意)",
    },
    "cookie_access": {
        "patterns": ["cookie", "keychain", "decrypt"],
        "reason": "访问浏览器 cookie / 系统钥匙串",
    },
    "compiled_binary": {
        "patterns": ["compiled binary", "bun build --compile"],
        "reason": "使用预编译二进制文件 (难以审计)",
    },
    "external_network": {
        "patterns": ["curl ", "POST ", "supabase", "http request"],
        "reason": "存在外部网络请求",
    },
    "shell_execution": {
        "patterns": ["rm -rf", "DROP TABLE", "force-push", "kubectl delete"],
        "reason": "涉及危险 shell 命令 (但本身是安全防护类 skill)",
    },
}

# 安全类别 (这些 skill 本身就是安全/防护工具)
SAFETY_SKILL_NAMES = {"careful", "freeze", "guard", "unfreeze", "cso"}


# ─────────────────────────── SKILL.md 解析器 ───────────────────────────

def parse_skill_md(filepath: Path) -> Optional[dict]:
    """解析一个 SKILL.md 文件，提取 YAML frontmatter 中的元数据"""
    text = filepath.read_text(encoding="utf-8")

    # 提取 YAML frontmatter
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None

    frontmatter = m.group(1)

    # 提取字段
    name_m = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    version_m = re.search(r"^version:\s*(.+)$", frontmatter, re.MULTILINE)

    # 提取 description (可能是多行)
    desc_m = re.search(r"^description:\s*\|?\s*\n((?:\s{2,}.+\n?)+)", frontmatter, re.MULTILINE)
    if not desc_m:
        desc_m = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)

    # 提取 allowed-tools
    tools_m = re.search(r"^allowed-tools:\s*\n((?:\s+-\s+.+\n?)+)", frontmatter, re.MULTILINE)
    tools = []
    if tools_m:
        tools = re.findall(r"-\s+(.+)", tools_m.group(1))

    # 提取 hooks
    has_hooks = "hooks:" in frontmatter

    name = name_m.group(1).strip() if name_m else filepath.parent.name
    version = version_m.group(1).strip() if version_m else "unknown"
    description = ""
    if desc_m:
        if desc_m.lastindex and desc_m.lastindex >= 1:
            raw = desc_m.group(1)
            # 清理缩进
            lines = [l.strip() for l in raw.strip().splitlines()]
            description = " ".join(lines)

    # 获取完整内容用于安全扫描
    skill_dir = filepath.parent
    full_content = text

    return {
        "name": name,
        "version": version,
        "description": description[:500],
        "allowed_tools": tools,
        "has_hooks": has_hooks,
        "skill_dir": str(skill_dir.relative_to(GSTACK_DIR)),
        "file_path": str(filepath),
        "full_content": full_content,
        "source": "gstack",
        "url": f"https://github.com/garrytan/gstack/tree/main/{skill_dir.relative_to(GSTACK_DIR)}",
        "license": "MIT",
        "author": "Garry Tan (YC CEO)",
    }


def discover_all_skills() -> list[dict]:
    """发现 gstack 中所有 SKILL.md 文件"""
    skills = []

    # 根目录的 SKILL.md (主入口)
    root_skill = GSTACK_DIR / "SKILL.md"
    if root_skill.exists():
        parsed = parse_skill_md(root_skill)
        if parsed:
            parsed["name"] = "gstack-browse"  # 根级 SKILL.md 是 browse 功能
            parsed["is_root"] = True
            skills.append(parsed)

    # 各子目录的 SKILL.md
    for skill_dir in sorted(GSTACK_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists() and skill_dir.name not in (".git", ".github", "test", "lib", "docs", "scripts", "bin", "browse", "supabase"):
            parsed = parse_skill_md(skill_md)
            if parsed:
                skills.append(parsed)

    # browse 子目录单独处理 (它有自己的完整 SKILL.md)
    browse_skill = GSTACK_DIR / "browse" / "SKILL.md"
    if browse_skill.exists():
        parsed = parse_skill_md(browse_skill)
        if parsed:
            parsed["name"] = "gstack-browse-engine"
            skills.append(parsed)

    return skills


# ─────────────────────────── 安全扫描 ───────────────────────────

class GstackSafetyScanner:
    """gstack 专用安全扫描器"""

    def __init__(self):
        self.stats = defaultdict(int)
        self.findings = []

    def scan(self, skill: dict) -> dict:
        """扫描一个 skill，返回安全级别"""
        reasons = []
        text = skill["full_content"].lower()
        name = skill["name"].lower()

        # Layer 1: 黑名单检查
        for pattern in BLACKLIST_PATTERNS:
            if re.search(pattern, text):
                reasons.append(f"BLOCKED: blacklist pattern '{pattern}'")

        if reasons:
            skill["safety_level"] = "blocked"
            skill["safety_reasons"] = reasons
            self.stats["blocked"] += 1
            return skill

        # Layer 2: WARNING 特征检测
        warnings = []
        for feature_name, feature_info in WARNING_FEATURES.items():
            for pat in feature_info["patterns"]:
                if pat.lower() in text:
                    warnings.append(f"WARNING: {feature_name} — {feature_info['reason']}")
                    break

        # Layer 3: 安全防护类 skill 降级 warning
        if name in SAFETY_SKILL_NAMES:
            warnings = [w.replace("WARNING:", "INFO:") for w in warnings]

        # Layer 4: hook 检测 (PreToolUse hooks 有更高权限)
        if skill.get("has_hooks"):
            warnings.append("INFO: 使用 hooks (PreToolUse) — 可拦截工具调用")

        # 判定
        has_warning = any(w.startswith("WARNING:") for w in warnings)
        if has_warning:
            skill["safety_level"] = "warning"
            self.stats["warning"] += 1
        else:
            skill["safety_level"] = "safe"
            self.stats["safe"] += 1

        skill["safety_reasons"] = warnings if warnings else ["SAFE: 无风险特征"]
        return skill

    def scan_repo_level(self) -> list[str]:
        """扫描仓库级别的安全特征"""
        findings = []

        # 检查 telemetry 系统
        tel_log = GSTACK_DIR / "bin" / "gstack-telemetry-log"
        tel_sync = GSTACK_DIR / "bin" / "gstack-telemetry-sync"
        if tel_log.exists():
            findings.append("⚠️ TELEMETRY: gstack-telemetry-log 收集使用数据到本地 JSONL")
        if tel_sync.exists():
            content = tel_sync.read_text(encoding="utf-8")
            if "supabase" in content.lower():
                findings.append("⚠️ TELEMETRY-SYNC: gstack-telemetry-sync 上传数据到 Supabase (opt-in)")
            if "telemetry off" in content or '"off"' in content:
                findings.append("✅ TELEMETRY: 支持完全关闭 (gstack-config set telemetry off)")

        # 检查预编译二进制
        binaries = list((GSTACK_DIR / "bin").glob("*"))
        compiled = [b for b in binaries if b.stat().st_size > 1_000_000]  # >1MB = likely compiled
        if compiled:
            for b in compiled:
                size_mb = b.stat().st_size / 1_000_000
                findings.append(f"⚠️ BINARY: {b.name} ({size_mb:.1f} MB 预编译二进制)")

        # 检查 cookie 访问
        cookie_dir = GSTACK_DIR / "setup-browser-cookies"
        if cookie_dir.exists():
            findings.append("⚠️ COOKIE: setup-browser-cookies 可访问浏览器 cookie (需要 Keychain 授权)")

        # 检查许可证
        license_file = GSTACK_DIR / "LICENSE"
        if license_file.exists():
            content = license_file.read_text()
            if "MIT" in content:
                findings.append("✅ LICENSE: MIT 开源许可 — 可自由使用/修改/分发")

        # 检查安全模型
        arch_file = GSTACK_DIR / "ARCHITECTURE.md"
        if arch_file.exists():
            content = arch_file.read_text()
            if "localhost" in content:
                findings.append("✅ SECURITY: 浏览器服务仅绑定 localhost")
            if "Bearer token" in content:
                findings.append("✅ SECURITY: 每次会话使用随机 Bearer token 认证")

        self.findings = findings
        return findings


# ─────────────────────────── 分类映射 ───────────────────────────

SKILL_CATEGORY_MAP = {
    # 产品规划
    "office-hours": "product-planning",
    "plan-ceo-review": "product-planning",
    "autoplan": "product-planning",

    # 工程评审
    "plan-eng-review": "engineering-review",
    "review": "engineering-review",
    "codex": "engineering-review",

    # 设计
    "plan-design-review": "design-review",
    "design-consultation": "design-review",
    "design-review": "design-review",

    # 发布 & 部署
    "ship": "release-deploy",
    "land-and-deploy": "release-deploy",
    "canary": "release-deploy",
    "setup-deploy": "release-deploy",
    "document-release": "release-deploy",

    # QA & 测试
    "qa": "qa-testing",
    "qa-only": "qa-testing",
    "benchmark": "qa-testing",
    "gstack-browse": "qa-testing",
    "gstack-browse-engine": "qa-testing",

    # 安全
    "cso": "security",
    "careful": "safety-guardrails",
    "freeze": "safety-guardrails",
    "guard": "safety-guardrails",
    "unfreeze": "safety-guardrails",

    # 浏览器
    "browse": "browser-automation",
    "setup-browser-cookies": "browser-automation",

    # 调试 & 回顾
    "investigate": "debugging",
    "retro": "retrospective",

    # 管理
    "gstack-upgrade": "tool-management",
}


# ─────────────────────────── 导入到 skill 库 ───────────────────────────

def skill_to_meta_json(skill: dict) -> dict:
    """将 gstack skill 转换为本地 meta.json 格式"""
    category = SKILL_CATEGORY_MAP.get(skill["name"], "workflow")
    slug = f"gstack_{skill['name'].replace('-', '_')}"

    return {
        "name": f"gstack/{skill['name']}",
        "slug": slug,
        "description": skill["description"],
        "description_zh": "",
        "tags": [
            "gstack", "workflow", category, "open_source", "mit_license",
            "claude_code", "ai_engineering",
        ],
        "url": skill["url"],
        "source": "gstack",
        "author": skill["author"],
        "license": skill["license"],
        "version": skill.get("version", "unknown"),
        "category": category,
        "allowed_tools": skill.get("allowed_tools", []),
        "has_hooks": skill.get("has_hooks", False),
        "safety_level": skill.get("safety_level", "unknown"),
        "safety_reasons": skill.get("safety_reasons", []),
        "created_at": datetime.datetime.now().isoformat(),
        "imported_by": "gstack_skill_importer",
    }


def save_skills(skills: list[dict]) -> int:
    """保存安全的 skill 到本地能力库"""
    LOCAL_SKILL_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0

    for skill in skills:
        if skill.get("safety_level") == "blocked":
            continue

        meta = skill_to_meta_json(skill)
        slug = meta["slug"]
        filepath = LOCAL_SKILL_DIR / f"{slug}.meta.json"

        # 写入
        filepath.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        saved += 1

    return saved


# ─────────────────────────── gstack 架构 meta-skill ───────────────────────────

def create_gstack_architecture_skill() -> Path:
    """将 gstack 自身的架构逻辑整理为一个 meta-skill"""
    meta = {
        "name": "gstack/architecture",
        "slug": "gstack_architecture_pattern",
        "description": (
            "gstack AI Engineering Workflow Architecture — Garry Tan's open-source software factory. "
            "Core pattern: SKILL.md-based role specialization turns AI coding agents into a virtual "
            "engineering team with 28 specialist roles. Key innovations: (1) Persistent headless "
            "browser daemon (Bun-compiled, sub-100ms per command, localhost-only with bearer token auth); "
            "(2) Role-based SKILL.md files that give AI agents specific personas (CEO, eng manager, "
            "designer, QA lead, security officer, release engineer); (3) Pipeline workflow: "
            "office-hours → plan-ceo-review → plan-eng-review → plan-design-review → implement → "
            "review → qa → ship → land-and-deploy → canary → retro; (4) Safety guardrails via "
            "PreToolUse hooks (careful/freeze/guard) that intercept destructive commands; "
            "(5) Boil-the-Lake philosophy — when AI makes marginal cost near-zero, always do "
            "the complete thing. Architecture: CLI → HTTP → Bun.serve daemon → CDP → Chromium. "
            "State management via atomic JSON file writes. Auto-start on first use, 30min idle shutdown."
        ),
        "description_zh": (
            "gstack AI 工程工作流架构 — YC CEO Garry Tan 的开源软件工厂。"
            "核心模式: 基于 SKILL.md 的角色专业化，将 AI 编码 Agent 变成包含 28 个专家角色的虚拟工程团队。"
            "关键创新: (1) 持久化无头浏览器守护进程 (Bun 编译，每命令 <100ms); "
            "(2) 角色化 SKILL.md 赋予 AI 不同人格 (CEO/工程经理/设计师/QA/安全官); "
            "(3) 流水线工作流: 构思→CEO评审→工程评审→设计评审→实现→Review→QA→发布→部署→金丝雀→回顾; "
            "(4) PreToolUse hooks 安全护栏拦截危险命令; "
            "(5) Boil-the-Lake 哲学 — AI 使边际成本趋近于零时，永远做完整版。"
        ),
        "tags": [
            "gstack", "architecture", "workflow", "ai_engineering", "role_specialization",
            "skill_md", "headless_browser", "virtual_team", "pipeline", "safety_guardrails",
            "boil_the_lake", "claude_code", "open_source", "mit_license",
        ],
        "url": "https://github.com/garrytan/gstack",
        "source": "gstack",
        "author": "Garry Tan (YC CEO)",
        "license": "MIT",
        "category": "architecture-pattern",
        "safety_level": "safe",
        "safety_reasons": ["SAFE: 纯架构模式描述，无可执行代码"],
        "design_spec": {
            "core_principles": [
                "Boil the Lake — AI 使完整实现成本趋近于零，永远选择完整方案",
                "Search Before Building — 构建前先搜索已有解决方案",
                "Role Specialization — 每个 SKILL.md 定义一个专家角色",
                "Pipeline Workflow — 从构思到部署的完整流水线",
                "Safety by Default — PreToolUse hooks 拦截危险操作",
            ],
            "architecture": {
                "runtime": "Bun (compiled binary, native SQLite, native TypeScript)",
                "browser": "Persistent Chromium daemon via CDP, localhost-only, bearer token auth",
                "skills": "28 SKILL.md files, YAML frontmatter + markdown body",
                "state": "Atomic JSON file writes (~/.gstack/browse.json)",
                "lifecycle": "Auto-start on first use, 30min idle shutdown, version auto-restart",
            },
            "workflow_pipeline": [
                "office-hours → 产品构思与重构",
                "plan-ceo-review → CEO 级方案评审",
                "plan-eng-review → 工程架构锁定",
                "plan-design-review → 设计维度评分",
                "implement → 代码实现",
                "review → PR 评审 (SQL安全/LLM信任/竞态检测)",
                "qa → 浏览器实测 + 修复 + 验证",
                "ship → 测试/评审/推送/PR 一键完成",
                "land-and-deploy → 合并/CI/部署/健康检查",
                "canary → 部署后金丝雀监控",
                "retro → 周回顾/团队贡献分析",
            ],
            "skill_roles": {
                "product": ["office-hours", "plan-ceo-review", "autoplan"],
                "engineering": ["plan-eng-review", "review", "codex", "investigate"],
                "design": ["plan-design-review", "design-consultation", "design-review"],
                "qa": ["qa", "qa-only", "benchmark", "browse"],
                "release": ["ship", "land-and-deploy", "canary", "document-release"],
                "security": ["cso", "careful", "freeze", "guard", "unfreeze"],
            },
        },
        "created_at": datetime.datetime.now().isoformat(),
        "imported_by": "gstack_skill_importer",
    }

    filepath = LOCAL_SKILL_DIR / "gstack_architecture_pattern.meta.json"
    filepath.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return filepath


# ─────────────────────────── 报告生成 ───────────────────────────

def generate_report(skills: list[dict], scanner: GstackSafetyScanner, saved: int) -> str:
    """生成安全扫描报告"""
    lines = [
        "# gstack Skill 安全扫描 & 导入报告",
        f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**仓库**: https://github.com/garrytan/gstack",
        f"**作者**: Garry Tan (YC CEO)",
        f"**许可证**: MIT",
        "",
        "## 概览",
        f"- **发现 skill 总数**: {len(skills)}",
        f"- **安全 (safe)**: {scanner.stats['safe']}",
        f"- **警告 (warning)**: {scanner.stats['warning']}",
        f"- **拦截 (blocked)**: {scanner.stats['blocked']}",
        f"- **导入到本地能力库**: {saved} skills",
        "",
        "## 仓库级安全分析",
    ]

    for finding in scanner.findings:
        lines.append(f"- {finding}")

    lines.extend(["", "## Skill 详细扫描结果", ""])
    lines.append("| Skill | 安全级别 | 类别 | 原因 |")
    lines.append("|-------|---------|------|------|")

    for s in skills:
        level = s.get("safety_level", "unknown")
        icon = {"safe": "✅", "warning": "⚠️", "blocked": "🚫"}.get(level, "❓")
        category = SKILL_CATEGORY_MAP.get(s["name"], "workflow")
        reasons = "; ".join(s.get("safety_reasons", [])[:2])
        lines.append(f"| {s['name']} | {icon} {level} | {category} | {reasons} |")

    lines.extend([
        "",
        "## gstack 架构分析",
        "",
        "### 核心模式",
        "- **角色专业化**: 28 个 SKILL.md 文件，每个定义一个专家角色",
        "- **流水线工作流**: office-hours → plan → review → implement → qa → ship → deploy → retro",
        "- **持久化浏览器**: Bun 编译的 Chromium 守护进程，<100ms/命令",
        "- **安全护栏**: PreToolUse hooks 拦截 rm -rf / DROP TABLE / force-push",
        "- **Boil the Lake**: AI 使边际成本趋近零，永远做完整版",
        "",
        "### 安全模型",
        "- 浏览器服务仅绑定 localhost",
        "- 每会话随机 Bearer token 认证",
        "- Cookie 在内存解密，不落盘明文",
        "- 遥测完全 opt-in (off/anonymous/community)",
        "",
        "### 导入说明",
        "- 全部 skill 已转为 `workspace/skills/gstack_*.meta.json` 格式",
        "- gstack 架构模式已整理为 `gstack_architecture_pattern.meta.json`",
        "- 可通过 PCM skill router 查询: `route_skills('gstack QA测试')`",
    ])

    report_text = "\n".join(lines)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    return report_text


# ─────────────────────────── 主流程 ───────────────────────────

def main():
    print("=" * 60)
    print("🔍 gstack Skill Importer — 安全扫描 + 导入")
    print("=" * 60)

    if not GSTACK_DIR.exists():
        print(f"[ERROR] gstack 目录不存在: {GSTACK_DIR}")
        return

    # Step 1: 发现全部 skill
    print("\n📖 Step 1: 发现全部 SKILL.md...")
    skills = discover_all_skills()
    print(f"   ✅ 发现 {len(skills)} 个 skill")
    for s in skills:
        print(f"     - {s['name']}: {s['description'][:80]}...")

    # Step 2: 安全扫描
    print("\n🛡️  Step 2: 安全扫描...")
    scanner = GstackSafetyScanner()

    # 2a. 仓库级扫描
    repo_findings = scanner.scan_repo_level()
    for f in repo_findings:
        print(f"   {f}")

    # 2b. 逐 skill 扫描
    for skill in skills:
        scanner.scan(skill)

    print(f"\n   📊 Safe: {scanner.stats['safe']} | Warning: {scanner.stats['warning']} | Blocked: {scanner.stats['blocked']}")

    # Step 3: 保存到本地能力库
    print("\n💾 Step 3: 保存 skill 到本地能力库...")
    saved = save_skills(skills)
    print(f"   ✅ 保存 {saved} skills → {LOCAL_SKILL_DIR}")

    # Step 4: 创建架构 meta-skill
    print("\n🏗️  Step 4: 创建 gstack 架构 meta-skill...")
    arch_path = create_gstack_architecture_skill()
    print(f"   ✅ 架构模式 → {arch_path}")

    # Step 5: 生成报告
    print("\n📊 Step 5: 生成扫描报告...")
    report = generate_report(skills, scanner, saved)
    print(f"   ✅ 报告 → {REPORT_PATH}")

    # 摘要
    print("\n" + "=" * 60)
    print("✅ 全部完成!")
    print(f"   发现: {len(skills)} skills")
    print(f"   导入: {saved} skills + 1 架构 meta-skill")
    print(f"   报告: {REPORT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
