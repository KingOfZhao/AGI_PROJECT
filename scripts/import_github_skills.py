#!/usr/bin/env python3
"""
import_github_skills.py — 将 GitHub skills repo 中的 SKILL.md 导入到本地 skills 目录
格式兼容: OpenClaw skills 格式 (SKILL.md + _meta.json)

用法:
  python3 import_github_skills.py <repo_dir> <skills_dir> <source_name>
"""

import sys
import json
import hashlib
import re
import time
import shutil
from pathlib import Path


def parse_skill_md(skill_md_path: Path) -> dict | None:
    """解析 SKILL.md 文件，提取 YAML frontmatter 和正文"""
    text = skill_md_path.read_text(encoding="utf-8", errors="replace")

    # 提取 YAML frontmatter
    fm = {}
    body = text
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if fm_match:
        raw_fm, body = fm_match.group(1), fm_match.group(2)
        for line in raw_fm.splitlines():
            kv = line.split(":", 1)
            if len(kv) == 2:
                fm[kv[0].strip()] = kv[1].strip()

    name = fm.get("name") or skill_md_path.parent.name
    if not name:
        return None

    return {
        "name": name,
        "description": fm.get("description", ""),
        "triggers": [t.strip() for t in fm.get("triggers", "").split(",") if t.strip()],
        "domain": fm.get("domain", "general"),
        "role": fm.get("role", "specialist"),
        "scope": fm.get("scope", "implementation"),
        "license": fm.get("license", "MIT"),
        "author": fm.get("metadata.author", fm.get("author", "")),
        "version": fm.get("metadata.version", fm.get("version", "1.0.0")),
        "related_skills": [s.strip() for s in fm.get("related-skills", "").split(",") if s.strip()],
        "raw_frontmatter": fm,
        "body": body.strip(),
        "full_text": text,
    }


def slug_from_name(name: str, source: str) -> str:
    """生成唯一 slug"""
    safe = re.sub(r"[^a-z0-9\-]", "-", name.lower())
    safe = re.sub(r"-+", "-", safe).strip("-")
    return f"{source}-{safe}"


def import_skills_from_repo(repo_dir: Path, skills_dir: Path, source_name: str) -> dict:
    """扫描 repo_dir 中的所有 SKILL.md，导入到 skills_dir"""
    new_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []

    # 查找所有 SKILL.md（直接子目录 或 根目录本身）
    skill_files: list[Path] = []
    # 标准格式: skills/<slug>/SKILL.md
    skill_files.extend(repo_dir.rglob("SKILL.md"))
    # 兜底: 根目录下的 *.md
    if not skill_files:
        skill_files.extend(repo_dir.glob("*.md"))

    for skill_file in skill_files:
        if skill_file.name.lower() == "readme.md":
            continue

        parsed = parse_skill_md(skill_file)
        if not parsed:
            skipped_count += 1
            continue

        slug = slug_from_name(parsed["name"], source_name)
        target_dir = skills_dir / slug

        # 检查是否已存在且相同内容（md5）
        target_skill = target_dir / "SKILL.md"
        existing_hash = ""
        if target_skill.exists():
            existing_hash = hashlib.md5(target_skill.read_bytes()).hexdigest()
        new_hash = hashlib.md5(parsed["full_text"].encode()).hexdigest()

        if existing_hash == new_hash:
            skipped_count += 1
            continue

        is_new = not target_dir.exists()
        target_dir.mkdir(parents=True, exist_ok=True)

        # 写 SKILL.md
        target_skill.write_text(parsed["full_text"], encoding="utf-8")

        # 写 _meta.json（OpenClaw 格式）
        meta = {
            "ownerId": f"github-{source_name}",
            "slug": slug,
            "version": parsed["version"],
            "publishedAt": int(time.time() * 1000),
            "source": f"https://github.com/{source_name}/skills.git",
            "name": parsed["name"],
            "description": parsed["description"],
            "domain": parsed["domain"],
            "triggers": parsed["triggers"],
            "related_skills": parsed["related_skills"],
        }
        (target_dir / "_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        if is_new:
            new_count += 1
        else:
            updated_count += 1

    return {
        "new": new_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": errors,
    }


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"用法: {sys.argv[0]} <repo_dir> <skills_dir> <source_name>")
        sys.exit(1)

    repo_dir = Path(sys.argv[1])
    skills_dir = Path(sys.argv[2])
    source_name = sys.argv[3]

    if not repo_dir.exists():
        print(f"✗ repo_dir 不存在: {repo_dir}")
        sys.exit(1)

    skills_dir.mkdir(parents=True, exist_ok=True)
    result = import_skills_from_repo(repo_dir, skills_dir, source_name)

    print(
        f"新增: {result['new']}, 更新: {result['updated']}, "
        f"跳过: {result['skipped']}, 错误: {len(result['errors'])}"
    )
    if result["errors"]:
        for e in result["errors"]:
            print(f"  ✗ {e}")
