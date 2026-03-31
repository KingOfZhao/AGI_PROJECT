#!/usr/bin/env bash
# requires bash 3.2+ (macOS compatible)
# sync_github_skills.sh — 从 GitHub 拉取 skills 并导入到本地
# 计划任务: 每两天自动运行一次 (LaunchAgent: com.openclaw.flutter-skills-sync)
#
# 用法:
#   bash sync_github_skills.sh                  # 同步所有配置的 repo
#   bash sync_github_skills.sh --dry-run        # 只显示会做什么
#   bash sync_github_skills.sh --force          # 强制重新克隆

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CACHE_DIR="$PROJECT_ROOT/.skills_cache"
SKILLS_DIR="$PROJECT_ROOT/skills"
LOG_FILE="$PROJECT_ROOT/data/skills_sync.log"
DRY_RUN=false
FORCE=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --force)   FORCE=true ;;
  esac
done

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# ── 配置的 skills 仓库（兼容 bash 3.2）──────────────────────
REPO_NAMES=("flutter")
REPO_URLS=("https://github.com/flutter/skills.git")

mkdir -p "$CACHE_DIR" "$SKILLS_DIR" "$(dirname "$LOG_FILE")"

log "=== Skills Sync 开始 ==="
log "PROJECT_ROOT: $PROJECT_ROOT"
log "CACHE_DIR:    $CACHE_DIR"
log "SKILLS_DIR:   $SKILLS_DIR"

total_new=0
total_updated=0
total_failed=0

for i in "${!REPO_NAMES[@]}"; do
  name="${REPO_NAMES[$i]}"
  repo_url="${REPO_URLS[$i]}"
  repo_dir="$CACHE_DIR/$name"

  log "--- 处理 [$name] $repo_url"

  # Clone or pull
  if [ -d "$repo_dir/.git" ] && [ "$FORCE" = false ]; then
    log "  拉取更新..."
    if $DRY_RUN; then
      log "  [DRY-RUN] git -C $repo_dir pull"
    else
      git -c http.version=HTTP/1.1 -C "$repo_dir" pull --quiet 2>&1 | tee -a "$LOG_FILE" || {
        log "  ⚠ pull 失败，跳过此 repo"
        ((total_failed++)) || true
        continue
      }
    fi
  else
    log "  克隆..."
    if $DRY_RUN; then
      log "  [DRY-RUN] git clone $repo_url $repo_dir"
    else
      rm -rf "$repo_dir"
      git -c http.version=HTTP/1.1 clone --depth=1 "$repo_url" "$repo_dir" 2>&1 | tee -a "$LOG_FILE" || {
        log "  ✗ clone 失败，网络不可达: $repo_url"
        ((total_failed++)) || true
        continue
      }
    fi
  fi

  # 导入 skills
  log "  导入 skills..."
  if $DRY_RUN; then
    log "  [DRY-RUN] python3 $SCRIPT_DIR/import_github_skills.py $repo_dir $SKILLS_DIR $name"
  else
    result=$(python3 "$SCRIPT_DIR/import_github_skills.py" "$repo_dir" "$SKILLS_DIR" "$name" 2>&1)
    log "  $result"
    new_count=$(echo "$result" | grep -oP '新增: \K\d+' || echo 0)
    upd_count=$(echo "$result" | grep -oP '更新: \K\d+' || echo 0)
    ((total_new += new_count)) || true
    ((total_updated += upd_count)) || true
  fi
done

log "=== 同步完成: 新增 $total_new, 更新 $total_updated, 失败 $total_failed ==="

# 更新最后同步时间
if ! $DRY_RUN; then
  python3 - <<PYEOF
import json, datetime, pathlib
f = pathlib.Path("$PROJECT_ROOT/data/skills_sync_state.json")
state = json.loads(f.read_text()) if f.exists() else {}
state["last_sync"] = datetime.datetime.now().isoformat()
state["total_new"] = $total_new
state["total_updated"] = $total_updated
state["total_failed"] = $total_failed
f.write_text(json.dumps(state, indent=2, ensure_ascii=False))
PYEOF
fi

exit $total_failed
