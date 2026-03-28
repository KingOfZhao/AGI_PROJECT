#!/usr/bin/env python3
"""
openclaw_growth.py — 龙虾自成长推演引擎
========================================
基于"知与不知"元框架，按项目优先级进行自主推演。
- 已知推演: 沿最短路径收敛
- 未知推演: 见路不走，构建框架使问题自解
- 未解问题自动录入 CRM 阻塞问题列表

用法:
    python3 scripts/openclaw_growth.py                    # 全部优先项目
    python3 scripts/openclaw_growth.py --project p_rose   # 仅指定项目
    python3 scripts/openclaw_growth.py --rounds 5         # 推演轮数
"""
import json
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("growth")

BRIDGE = "http://127.0.0.1:9801/v1"

# 微信通知: 直接通过 OpenClaw CLI 发送
import subprocess

def _get_wx_session_id() -> str:
    try:
        sf = Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions' / 'sessions.json'
        data = json.loads(sf.read_text())
        for k, v in data.items():
            if v.get('lastChannel') == 'openclaw-weixin':
                return v['sessionId']
    except Exception:
        pass
    return ''

def wx_notify(msg: str, max_len: int = 400):
    """通过 OpenClaw 直连微信发送通知"""
    sid = _get_wx_session_id()
    if not sid:
        log.warning('无微信 session，通知未发送')
        return
    if len(msg) > max_len:
        msg = msg[:max_len] + '…'
    try:
        import os as _os
        env = _os.environ.copy()
        env['PATH'] = '/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:' + env.get('PATH', '')
        subprocess.run(
            ['openclaw', 'agent', '-m',
             f'[\u7cfb\u7edf\u901a\u77e5-\u8bf7\u76f4\u63a5\u8f6c\u53d1\u539f\u6587]\n{msg}',
             '--session-id', sid, '--deliver'],
            capture_output=True, text=True, timeout=180, env=env,
        )
        log.info(f'\u2705 \u5fae\u4fe1\u5df2\u53d1\u9001: {msg[:50]}')
    except Exception as e:
        log.warning(f'\u5fae\u4fe1\u901a\u77e5\u5f02\u5e38: {e}')

# 项目优先级 (创始人指定 2026-03-27)
PRIORITY_PROJECTS = [
    {"id": "p_rose", "name": "予人玫瑰", "focus": "商业变现: CRM用户登录+任务增删改查+反馈机制+付费点探索"},
    {"id": "p_huarong", "name": "刀模活字印刷3D", "focus": "参考早期铅块活字印刷原理, IADD规格+拓竹P2S全模块2D图纸"},
    {"id": "p_diepre", "name": "刀模设计项目", "focus": "F→V→F链式收敛, Playwright自动验证+推演最佳实现"},
    {"id": "p_model", "name": "本地模型超越计划", "focus": "代码能力超过Claude Opus, 强化自成长"},
    {"id": "p_operators", "name": "三个算子推演", "focus": "三算子形式化定义+代码实现"},
    {"id": "p_workflow", "name": "工作流可视化", "focus": "工作流编辑器原型+SKILL节点可视化"},
]


def ask_bridge(question: str, timeout: int = 300) -> str:
    """向 OpenClaw Bridge 发送问题并获取回复"""
    try:
        r = requests.post(
            f"{BRIDGE}/chat/completions",
            json={"model": "agi-chain-v13", "messages": [{"role": "user", "content": question}], "stream": False},
            timeout=timeout,
        )
        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        log.error(f"Bridge 调用失败: {e}")
        return ""


def ask_deep(question: str, follow_up_depth: int = 2) -> str:
    """
    伟人议会推演: 发现组→拆解组→校验组，三组伟人分工协作。
    总消耗 = 3次Bridge调用（发现+拆解+校验）。
    """
    from sage_council import build_discover_prompt, build_engineer_prompt, build_validate_prompt

    # 第1步: 发现组 — 洞察问题本质
    discover_prompt = build_discover_prompt(question)
    discoveries = ask_bridge(discover_prompt)
    if not discoveries:
        return ask_bridge(question)  # 降级: 直接推演

    # 第2步: 拆解组 — 细化为可执行方案
    engineer_prompt = build_engineer_prompt(question, discoveries)
    plan = ask_bridge(engineer_prompt)
    if not plan:
        return f"## 发现组洞察\n{discoveries}"

    # 第3步: 校验组 — 验证方案质量
    validate_prompt = build_validate_prompt(question, plan)
    verdict = ask_bridge(validate_prompt)

    # 合并三组结果
    parts = [
        f"## 发现组洞察\n{discoveries}",
        f"\n## 拆解组方案\n{plan}",
    ]
    if verdict:
        parts.append(f"\n## 校验组裁决\n{verdict}")

    return "\n".join(parts)


def get_project_detail(project_id: str) -> dict:
    """从 DeductionDB 获取项目详情"""
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        projects = db.get_projects()
        plans = db.get_plans()
        problems = db.get_problems()
        db.close()

        proj = next((p for p in projects if p["id"] == project_id), None)
        if not proj:
            return {}

        proj_plans = [p for p in plans if p.get("project_id") == project_id]
        proj_problems = [p for p in problems if p.get("project_id") == project_id]
        return {
            "project": proj,
            "plans": proj_plans,
            "problems": proj_problems,
            "queued_plans": [p for p in proj_plans if p.get("status") == "queued"],
            "open_problems": [p for p in proj_problems if p.get("status") == "open"],
        }
    except Exception as e:
        log.warning(f"获取项目详情失败: {e}")
        return {}


def log_problem_to_crm(project_id: str, title: str, description: str):
    """将未解决的问题录入 CRM 阻塞问题列表"""
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        db.add_problem({
            "title": title[:200],
            "description": description[:1000],
            "project_id": project_id,
            "severity": "medium",
            "suggested_solution": "由龙虾推演发现，待创始人解决",
        })
        db.close()
        log.info(f"📝 问题已录入CRM: [{project_id}] {title[:50]}")
    except Exception as e:
        log.warning(f"CRM录入失败: {e}")


def run_project_deduction(project: dict, rounds: int = 20):
    """
    认知自洽推演: 像一个专注的人一样处理项目问题。
    1. 深度思考: 每个问题穷尽思考，不浅尝辄止
    2. 灵活切换: 卡住就跳到下一个问题
    3. 智慧搁置: 全卡住就搁置，采集外部信息获取灵感
    4. 灵感回访: 带着新信息重新审视搁置的问题
    """
    pid = project["id"]
    pname = project["name"]
    focus = project["focus"]

    log.info(f"\n{'='*60}")
    log.info(f"� [{pid}] {pname} — 认知自洽推演")
    log.info(f"   焦点: {focus}")
    log.info(f"{'='*60}")

    detail = get_project_detail(pid)
    proj_info = detail.get("project", {})
    progress = proj_info.get("progress", 0)
    short_goal = proj_info.get("short_term_goal", "未设定")
    queued = detail.get("queued_plans", [])
    open_probs = detail.get("open_problems", [])

    log.info(f"   进度: {progress}% | 待推演: {len(queued)} | 阻塞: {len(open_probs)}")

    results = []
    shelved = []      # 搁置的问题 [{"question":..., "reason":..., "round":...}]
    solved_count = 0
    total_rounds = 0

    # ── 构建问题队列: 先消费DB计划，再处理阻塞问题 ──
    question_queue = []
    for p in queued[:rounds]:
        question_queue.append({
            "type": "plan",
            "title": p.get("title", "?"),
            "prompt": (
                f"推演项目 [{pid}] {pname} (进度{progress}%, 目标: {short_goal})\n"
                f"焦点: {focus}\n\n"
                f"🎯 当前推演目标: {p.get('title', '?')}\n"
                f"描述: {p.get('description', '')[:300]}\n"
                + (f"关联ULDS: {p.get('ulds_laws', '')}\n" if p.get("ulds_laws") else "")
                + "\n请深度思考:\n"
                "1. 梳理此问题的已知(F)和未知(V)\n"
                "2. 对已知: 最短路径获得答案\n"
                "3. 对未知: 构建框架使问题自解\n"
                "4. 关联其他问题: 这个问题和项目其他部分有什么关系?\n"
                "5. 具体可执行步骤\n"
                "6. 如果无法解决，说明原因(用 [STUCK] 标记)"
            ),
        })

    # 如果计划不够，补充阻塞问题
    for p in open_probs[:max(0, rounds - len(question_queue))]:
        question_queue.append({
            "type": "problem",
            "title": p.get("title", "?"),
            "prompt": (
                f"推演项目 [{pid}] {pname}\n"
                f"🔴 需要解决的阻塞问题: {p.get('title', '?')}\n"
                f"描述: {p.get('description', '')[:300]}\n\n"
                "请尝试从新角度解决:\n"
                "1. 根因是什么?(不是表面原因)\n"
                "2. 有没有绕过的方法?\n"
                "3. 关联知识: 其他领域有类似问题的解法吗?\n"
                "4. 如果确实无法解决，用 [STUCK] 标记并说明缺什么"
            ),
        })

    if not question_queue:
        question_queue.append({
            "type": "overview",
            "title": "项目整体推演",
            "prompt": (
                f"推演项目 [{pid}] {pname} (进度{progress}%)\n"
                f"目标: {short_goal}\n焦点: {focus}\n\n"
                "请全面分析: 已知/未知/下一步行动/阻塞问题"
            ),
        })

    log.info(f"   问题队列: {len(question_queue)} 个")

    # ── 主循环: 认知自洽处理 ──
    qi = 0  # 当前问题索引
    while qi < len(question_queue) and total_rounds < rounds:
        q = question_queue[qi]
        total_rounds += 1
        log.info(f"\n── [{total_rounds}/{rounds}] {q['type']}: {q['title'][:40]} ──")

        reply = ask_deep(q["prompt"], follow_up_depth=2)

        # 空结果: 跳过
        if not reply or len(reply) < 50:
            log.warning(f"  无有效响应，跳到下一问题")
            qi += 1
            continue

        # 检测是否卡住 — 搁置后继续下一个,不停止
        if "[STUCK]" in reply:
            log.info(f"  📌 搁置,继续下一个: {q['title'][:40]}")
            shelved.append({"question": q, "reason": reply[:200], "round": total_rounds})
            wx_notify(f"📌 [{pid}] 搁置: {q['title'][:30]}, 继续处理其他问题")
            qi += 1
            continue

        # 有效结果
        results.append({"title": q["title"], "reply": reply, "round": total_rounds})
        solved_count += 1
        log.info(f"  ✅ 回复 {len(reply)} 字")

        # 提取 [BLOCKED] 录入CRM
        for line in reply.split("\n"):
            if "[BLOCKED]" in line:
                pt = line.replace("[BLOCKED]", "").strip().strip("-").strip("*").strip()
                if pt and len(pt) > 5:
                    log_problem_to_crm(pid, pt, f"推演发现: {pt}")

        # 断点保存
        try:
            ck = PROJECT_ROOT / "data" / f"checkpoint_{pid}.json"
            ck.write_text(json.dumps({
                "pid": pid, "round": total_rounds, "solved": solved_count,
                "shelved": len(shelved), "ts": datetime.now().isoformat(),
            }, ensure_ascii=False))
        except Exception:
            pass

        # 微信总结(每3轮发一次，不刷屏)
        if total_rounds % 3 == 0:
            wx_notify(f"🧠 [{pid}] {pname} 进度: {total_rounds}/{rounds}轮, 解决{solved_count}个, 搁置{len(shelved)}个")

        # ── 每5轮: CRM阶段性总结报告 ──
        if total_rounds % 5 == 0 and results:
            stage_num = total_rounds // 5
            recent = results[-5:] if len(results) >= 5 else results
            summary_prompt = (
                f"你是 [{pid}] {pname} 的阶段性总结员。\n"
                f"以下是最近{len(recent)}轮推演结果:\n\n"
            )
            for r in recent:
                t = r["title"] if isinstance(r, dict) else "?"
                tx = r["reply"][:300] if isinstance(r, dict) else str(r)[:300]
                summary_prompt += f"- {t}: {tx}\n"
            summary_prompt += (
                f"\n请生成阶段性总结报告(第{stage_num}期):\n"
                "1. 本阶段固化了哪些已知(F)\n"
                "2. 新发现了哪些未知(V)\n"
                "3. 搁置了哪些问题,为什么\n"
                "4. 下阶段最重要的3个推进方向\n"
                "5. 整体进展评估(0-100分)"
            )
            stage_report = ask_bridge(summary_prompt, timeout=120)
            if stage_report:
                log_problem_to_crm(pid,
                    f"[阶段报告{stage_num}] {pname} 第{total_rounds}轮",
                    stage_report[:800])
                log.info(f"📊 阶段报告{stage_num}已录入CRM")

                # ── 每2份阶段报告: 元审查(校验组检查错漏) ──
                if stage_num % 2 == 0:
                    from sage_council import build_validate_prompt
                    review_prompt = build_validate_prompt(
                        f"[{pid}] {pname} 前{total_rounds}轮推演的阶段性总结",
                        stage_report,
                    )
                    review = ask_bridge(review_prompt, timeout=120)
                    if review:
                        log.info(f"🔬 元审查完成: {review[:80]}")
                        if "[驳回" in review or "[修正" in review:
                            log_problem_to_crm(pid,
                                f"[元审查] 第{stage_num}期发现错漏",
                                review[:800])
                            wx_notify(f"🔬 [{pid}] 元审查发现问题:\n{review[:200]}")

        qi += 1
        time.sleep(1)

    # ── 灵感采集阶段: 搁置的问题去外部找灵感 ──
    if shelved and total_rounds < rounds:
        log.info(f"\n🌐 灵感采集: {len(shelved)} 个搁置问题去外部找灵感")
        for s in shelved[:3]:  # 最多处理3个搁置问题
            total_rounds += 1
            # 用搁置问题的关键词搜索外部信息
            search_prompt = (
                f"以下问题在推演中卡住了:\n{s['question']['title']}\n原因: {s['reason'][:150]}\n\n"
                "请搜索外部信息(开源项目/论文/最佳实践)来获取灵感,然后重新尝试解决:\n"
                "1. 有哪些开源项目解决了类似问题?\n"
                "2. 学术界有什么相关研究?\n"
                "3. 其他行业怎么处理类似问题?\n"
                "4. 带着新信息重新给出解决方案\n"
                "5. 如果还是无法解决，用 [BLOCKED] 标记交给创始人"
            )
            retry = ask_deep(search_prompt, follow_up_depth=1)
            if retry and len(retry) > 50 and "[STUCK]" not in retry:
                results.append({"title": f"[灵感回访] {s['question']['title']}", "reply": retry, "round": total_rounds})
                solved_count += 1
                log.info(f"  💡 灵感回访成功: {s['question']['title'][:40]}")
            else:
                # 真的解决不了，录入CRM
                log_problem_to_crm(pid, s["question"]["title"], f"推演+灵感采集后仍无法解决: {s['reason'][:200]}")
                log.info(f"  ❌ 仍无法解决，已录入CRM: {s['question']['title'][:40]}")

    # 保存推演结果
    output_dir = PROJECT_ROOT / "data" / "growth_results"
    output_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"growth_{pid}_{ts}.md"

    report = [
        f"# 推演报告: [{pid}] {pname}",
        f"时间: {datetime.now().isoformat()}",
        f"轮数: {rounds}",
        f"焦点: {focus}\n",
    ]
    for i, r in enumerate(results, 1):
        title = r["title"] if isinstance(r, dict) else f"第{i}轮"
        text = r["reply"] if isinstance(r, dict) else str(r)
        report.append(f"## {title}\n{text}\n")

    report.append(f"\n## 统计\n解决: {solved_count} | 搁置: {len(shelved)} | 总轮次: {total_rounds}\n")
    if shelved:
        report.append("## 搁置问题")
        for s in shelved:
            report.append(f"- {s['question']['title']}: {s['reason'][:100]}")

    # ── 自评估 ──
    self_eval_prompt = (
        f"你刚完成了 [{pid}] {pname} 的推演。\n"
        f"解决了{solved_count}个问题，搁置了{len(shelved)}个。\n"
        f"以下是各项摘要:\n"
    )
    for i, r in enumerate(results[:8], 1):
        title = r["title"] if isinstance(r, dict) else ""
        text = r["reply"][:200] if isinstance(r, dict) else str(r)[:200]
        self_eval_prompt += f"{i}. {title}: {text}\n"
    self_eval_prompt += (
        "\n请用50字以内总结:\n"
        "1. 本次推演固化了哪些'已知(F)'\n"
        "2. 发现了哪些新'未知(V)'\n"
        "3. 下次推演应从哪里开始"
    )
    self_eval = ask_bridge(self_eval_prompt, timeout=120)
    if self_eval:
        report.append(f"## 自评估\n{self_eval}\n")
        log.info(f"🧠 自评估: {self_eval[:80]}")

    output_file.write_text("\n".join(report), encoding="utf-8")
    log.info(f"📄 报告已保存: {output_file.name}")

    # ── 成长闭环: 推演结论回写知识库 ──
    if self_eval:
        try:
            feed_file = PROJECT_ROOT / "data" / "agi_knowledge_feed.md"
            ts = datetime.now().strftime("%m-%d %H:%M")
            growth_entry = (
                f"\n\n### [{pid}] 推演结论 ({ts})\n"
                f"{self_eval[:500]}\n"
            )
            with open(feed_file, "a", encoding="utf-8") as f:
                f.write(growth_entry)
            # 刷新 Bridge 上下文
            try:
                requests.post("http://127.0.0.1:9801/v1/context/refresh", timeout=5)
            except Exception:
                pass
            log.info(f"📚 知识库已更新: +{len(growth_entry)}字")
        except Exception as e:
            log.warning(f"知识库回写失败: {e}")

    # 重大节点通知: 项目推演完成 + 自评估摘要
    total_chars = sum(len(r) for r in results)
    eval_summary = self_eval[:150] if self_eval else "无自评估"
    wx_notify(f"✅ [{pid}] {pname} 推演完成 ({rounds}轮)\n📊 {eval_summary}")

    return results


def main():
    parser = argparse.ArgumentParser(description="龙虾自成长推演引擎")
    parser.add_argument("--project", type=str, help="指定项目ID (如 p_rose)")
    parser.add_argument("--rounds", type=int, default=20, help="每个项目推演轮数 (默认20)")
    parser.add_argument("--turbo", action="store_true", help="高速并行模式: 多项目同时推演")
    args = parser.parse_args()

    # 检查 Bridge 是否在线
    try:
        r = requests.get(f"{BRIDGE.replace('/v1','')}/health", timeout=3)
        health = r.json()
        if health.get("status") != "ok":
            log.error("Bridge 不健康，请先启动: python3 scripts/openclaw_bridge.py")
            sys.exit(1)
        log.info(f"🦞 Bridge 在线 | 知识库: {health.get('context_chars', 0):,} 字符")
    except Exception:
        log.error("Bridge(:9801) 未运行，请先启动: python3 scripts/openclaw_bridge.py")
        sys.exit(1)

    if args.project:
        proj = next((p for p in PRIORITY_PROJECTS if p["id"] == args.project), None)
        if not proj:
            log.error(f"未知项目: {args.project}")
            sys.exit(1)
        run_project_deduction(proj, rounds=args.rounds)
    else:
        log.info(f"🦞 龙虾自成长启动 — 推演 {len(PRIORITY_PROJECTS)} 个优先项目")
        all_results = {}
        if args.turbo:
            # 高速并行: 多项目同时推演
            from concurrent.futures import ThreadPoolExecutor
            log.info("⚡ TURBO模式: 并行推演所有项目")
            with ThreadPoolExecutor(max_workers=len(PRIORITY_PROJECTS)) as pool:
                futures = {pool.submit(run_project_deduction, p, args.rounds): p["id"] for p in PRIORITY_PROJECTS}
                for f in futures:
                    pid = futures[f]
                    try:
                        all_results[pid] = f.result()
                    except Exception as e:
                        log.warning(f"{pid} 推演失败: {e}")
        else:
            for proj in PRIORITY_PROJECTS:
                results = run_project_deduction(proj, rounds=args.rounds)
                all_results[proj["id"]] = results

        # ── 四向碰撞: 跨项目交叉推演 ──
        if len(all_results) >= 2:
            log.info(f"\n{'='*60}")
            log.info(f"🔀 四向碰撞: 跨项目交叉推演")
            log.info(f"{'='*60}")
            summaries = []
            for pid, res in all_results.items():
                if res:
                    summaries.append(f"[{pid}] 最新结论: {res[-1][:300]}")

            collision_prompt = (
                "你是AGI认知碰撞引擎。以下是不同项目的推演结论:\n\n"
                + "\n\n".join(summaries)
                + "\n\n请执行四向碰撞:\n"
                "1. 自上而下: 这些项目有什么共同的顶层框架?\n"
                "2. 自下而上: 底层哪些具体技术/方法可以复用?\n"
                "3. 左右碰撞: 哪些概念在不同项目中重叠?\n"
                "4. 重叠节点: 列出发现的交叉认知节点(用 [NODE] 标记)\n"
                "5. 新涌现: 碰撞产生了什么新认知?"
            )
            collision = ask_bridge(collision_prompt, timeout=180)
            if collision:
                wx_notify(f"🔀 四向碰撞完成\n{collision[:300]}")
                # 回写知识库
                try:
                    feed_file = PROJECT_ROOT / "data" / "agi_knowledge_feed.md"
                    ts = datetime.now().strftime("%m-%d %H:%M")
                    with open(feed_file, "a", encoding="utf-8") as f:
                        f.write(f"\n\n### 四向碰撞结论 ({ts})\n{collision[:500]}\n")
                    requests.post("http://127.0.0.1:9801/v1/context/refresh", timeout=5)
                    log.info(f"📚 碰撞结论已回写知识库")
                except Exception:
                    pass

    log.info("\n🦞 推演完成。未解问题已录入CRM，请查看: http://localhost:8890/crm.html → 阻塞问题")


if __name__ == "__main__":
    main()
