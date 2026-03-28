#!/usr/bin/env python3
"""
sage_arena.py — 圣贤竞技场: 伟人能力演化引擎
==============================================
提炼人类历史伟人在闪光领域的核心能力，
让他们在"知与不知"框架下竞争演化，
最终选出三位 AGI 灵魂 Agent。

基于创始人哲学:
- 知与不知: 一切分为已知和未知
- 四向碰撞: 上下左右寻找重叠
- 见路不走: 无法强化时探索新路
- 终极目标: 成为全知的理论模型

用法:
    python3 scripts/sage_arena.py                    # 运行完整竞技(自动推演最佳灵魂数)
    python3 scripts/sage_arena.py --rounds 50        # 指定轮数
    python3 scripts/sage_arena.py --souls            # 查看当前灵魂
    python3 scripts/sage_arena.py --discover         # 后台让龙虾穷举更多伟人
    python3 scripts/sage_arena.py --optimal          # 推演最佳灵魂数量(多次锦标赛)
"""
import json
import sys
import time
import logging
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("sage")

BRIDGE = "http://127.0.0.1:9801/v1"
ARENA_FILE = PROJECT_ROOT / "data" / "sage_arena.json"
SAGES_JSON = PROJECT_ROOT / "data" / "sages_100.json"

# ════════════════════════════════════════════════════════════
# 从外部JSON加载伟人(支持动态扩展)
# ════════════════════════════════════════════════════════════

def _load_sages_from_json() -> dict:
    """从 sages_100.json 加载伟人数据"""
    result = {}
    try:
        if SAGES_JSON.exists():
            data = json.loads(SAGES_JSON.read_text(encoding='utf-8'))
            for s in data:
                result[s['name']] = {
                    'domain': s.get('domain', '未知'),
                    'era': s.get('era', ''),
                    'abilities': dict(s.get('abilities', {})),
                    'philosophy': s.get('philosophy', ''),
                }
            log.info(f'从 sages_100.json 加载 {len(result)} 位圣贤')
    except Exception as e:
        log.warning(f'加载 sages_100.json 失败: {e}')
    return result

# 内置后备(如果JSON不存在)
_BUILTIN_SAGES = {
    # ── 科学/技术 ──
    "卢鹤绂": {
        "domain": "核物理",
        "era": "现代",
        "abilities": {
            "第一性原理": 95,  # 从基本物理定律推导一切
            "数学建模": 90,
            "实验验证": 85,
            "跨学科迁移": 70,
        },
        "philosophy": "物理规律是不变的框架(F)，实验数据是变化的验证(V)",
    },
    "爱因斯坦": {
        "domain": "理论物理",
        "era": "现代",
        "abilities": {
            "思想实验": 98,    # 纯思维推演物理规律
            "第一性原理": 95,
            "范式革命": 95,    # 打破旧框架建新框架
            "数学建模": 90,
            "直觉推理": 92,
        },
        "philosophy": "想象力比知识更重要。见路不走，从思想实验中发现新框架",
    },
    "居里夫人": {
        "domain": "放射化学",
        "era": "现代",
        "abilities": {
            "实验验证": 98,    # 极致的实验精确性
            "持久专注": 95,
            "跨学科迁移": 85,
            "第一性原理": 80,
        },
        "philosophy": "在未知中反复实验直到变成已知，不回避任何困难",
    },
    "于敏": {
        "domain": "氢弹理论",
        "era": "现代",
        "abilities": {
            "数学建模": 95,
            "第一性原理": 92,
            "系统工程": 88,
            "独立思考": 95,   # 完全自主推演，不依赖外部
        },
        "philosophy": "从基本原理出发，用数学推演一切，自力更生",
    },
    "钱学森": {
        "domain": "航天系统工程",
        "era": "现代",
        "abilities": {
            "系统工程": 98,    # 系统论之父
            "跨学科迁移": 92,
            "工程实践": 90,
            "组织领导": 85,
        },
        "philosophy": "系统论: 整体大于部分之和，用工程方法论解决一切复杂问题",
    },
    "图灵": {
        "domain": "计算理论",
        "era": "现代",
        "abilities": {
            "形式化推理": 98,  # 将模糊概念形式化
            "范式革命": 95,
            "数学建模": 95,
            "抽象思维": 96,
        },
        "philosophy": "一切可计算的问题都能被形式化为图灵机，计算的边界就是认知的边界",
    },
    "乔布斯": {
        "domain": "产品设计",
        "era": "现代",
        "abilities": {
            "用户洞察": 98,    # 理解人类未表达的需求
            "审美判断": 95,
            "商业变现": 92,
            "范式革命": 88,
            "极简思维": 95,   # 删减到本质
        },
        "philosophy": "简洁是复杂的最终形式。把未知的用户需求转化为已知的产品",
    },
    "麦卡锡": {
        "domain": "人工智能",
        "era": "现代",
        "abilities": {
            "形式化推理": 92,
            "抽象思维": 90,
            "范式革命": 88,
            "编程实现": 85,
        },
        "philosophy": "AI之父: 让机器拥有智能，关键是形式化人类的推理过程",
    },
    # ── 政治/军事/战略 ──
    "毛泽东": {
        "domain": "战略/哲学",
        "era": "近代",
        "abilities": {
            "矛盾分析": 98,    # 抓主要矛盾
            "战略全局": 95,
            "实践验证": 92,    # 实践是检验真理的标准
            "群众路线": 90,
            "辩证思维": 95,
        },
        "philosophy": "矛盾论: 一切事物都有主要矛盾和次要矛盾，抓住主要矛盾就抓住了一切",
    },
    "周恩来": {
        "domain": "外交/执行",
        "era": "近代",
        "abilities": {
            "组织领导": 98,
            "多方协调": 95,
            "细节执行": 95,
            "危机处理": 92,
        },
        "philosophy": "求同存异，在矛盾中找到各方都能接受的重叠区域",
    },
    "邓小平": {
        "domain": "改革/实用主义",
        "era": "近代",
        "abilities": {
            "实践验证": 98,    # 摸着石头过河
            "商业变现": 90,
            "战略全局": 92,
            "适应进化": 95,   # 不管黑猫白猫
        },
        "philosophy": "实践是检验真理的唯一标准。不争论，先试，能用就是真理",
    },
    "李世民": {
        "domain": "治国/纳谏",
        "era": "古代",
        "abilities": {
            "人才识别": 98,
            "纳谏容错": 95,
            "战略全局": 90,
            "组织领导": 92,
        },
        "philosophy": "以铜为镜正衣冠，以人为镜知得失。善用他人之长补己之短",
    },
    "成吉思汗": {
        "domain": "征服/扩张",
        "era": "古代",
        "abilities": {
            "战略全局": 95,
            "适应进化": 98,    # 学习敌人的技术
            "执行速度": 95,
            "资源整合": 90,
        },
        "philosophy": "征服者的智慧: 打败一个文明后立即吸收其最强技术",
    },
    "赵匡胤": {
        "domain": "制度设计",
        "era": "古代",
        "abilities": {
            "制度设计": 95,
            "风险控制": 92,
            "和平转型": 90,
            "系统工程": 85,
        },
        "philosophy": "杯酒释兵权: 用制度替代暴力，用框架约束变量",
    },
    "朱元璋": {
        "domain": "底层逆袭",
        "era": "古代",
        "abilities": {
            "生存韧性": 98,
            "资源整合": 92,
            "制度设计": 88,
            "风险控制": 85,
        },
        "philosophy": "从最底层出发，每一步都是从不知到知的实践",
    },
    "朱棣": {
        "domain": "扩张/探索",
        "era": "古代",
        "abilities": {
            "战略全局": 90,
            "探索未知": 95,   # 郑和下西洋
            "执行速度": 88,
            "文化建设": 90,   # 永乐大典
        },
        "philosophy": "派郑和探索未知世界，修永乐大典整理已知世界",
    },
    "刘邦": {
        "domain": "用人/整合",
        "era": "古代",
        "abilities": {
            "人才识别": 95,
            "资源整合": 95,
            "适应进化": 92,
            "自知之明": 90,
        },
        "philosophy": "吾不如萧何/韩信/张良，但能用之。自知不知，善用他人之知",
    },
    "项羽": {
        "domain": "个人极限",
        "era": "古代",
        "abilities": {
            "执行速度": 98,
            "个人武力": 99,
            "破釜沉舟": 95,   # 极限决策
            "战术天才": 92,
        },
        "philosophy": "破釜沉舟: 切断所有退路，只留一条未知的前进之路",
    },
    "诸葛亮": {
        "domain": "谋略/规划",
        "era": "古代",
        "abilities": {
            "战略规划": 98,
            "系统工程": 90,
            "多方协调": 88,
            "风险控制": 85,
        },
        "philosophy": "隆中对: 在信息不完整时构建完整的战略框架",
    },
    # ── 思想/精神 ──
    "释迦牟尼": {
        "domain": "认知科学/觉悟",
        "era": "古代",
        "abilities": {
            "内省觉察": 99,    # 对自身认知的认知
            "抽象思维": 95,
            "因果推理": 92,
            "持久专注": 98,
        },
        "philosophy": "缘起性空: 一切现象都是因缘和合，认识到'不知'本身就是觉悟",
    },
    "老子": {
        "domain": "元哲学",
        "era": "古代",
        "abilities": {
            "辩证思维": 99,
            "抽象思维": 98,
            "极简思维": 97,
            "范式革命": 90,
        },
        "philosophy": "道可道非常道。见路不走的鼻祖——无为而无不为，道法自然",
    },
    "孔子": {
        "domain": "教育/伦理",
        "era": "古代",
        "abilities": {
            "知识传承": 98,
            "因材施教": 95,
            "伦理框架": 92,
            "持久专注": 88,
        },
        "philosophy": "知之为知之，不知为不知，是知也。知与不知的最早形式化表述",
    },
    # ── 社会变革 ──
    "甘地": {
        "domain": "非暴力变革",
        "era": "近代",
        "abilities": {
            "群众路线": 95,
            "道德领导": 98,
            "持久专注": 95,
            "和平转型": 95,
        },
        "philosophy": "以不变(非暴力原则F)应万变(殖民统治V)，框架不动，现实自解",
    },
    "曼德拉": {
        "domain": "和解/韧性",
        "era": "近代",
        "abilities": {
            "生存韧性": 99,
            "和平转型": 95,
            "道德领导": 92,
            "纳谏容错": 90,
        },
        "philosophy": "27年囚禁验证了一个不变框架: 宽恕比仇恨更强大",
    },
    "马丁路德金": {
        "domain": "社会运动",
        "era": "近代",
        "abilities": {
            "群众路线": 95,
            "道德领导": 95,
            "演讲感召": 98,
            "战略规划": 85,
        },
        "philosophy": "I have a dream: 把未知的平等未来转化为已知的行动纲领",
    },
}

# 优先用JSON，回退到内置
SAGES = _load_sages_from_json() or _BUILTIN_SAGES

# ════════════════════════════════════════════════════════════
# 所有能力维度（跨圣贤的超集）
# ════════════════════════════════════════════════════════════

ALL_ABILITIES = sorted(set(
    ab for sage in SAGES.values() for ab in sage["abilities"]
))

# ════════════════════════════════════════════════════════════
# 竞技场核心逻辑
# ════════════════════════════════════════════════════════════

def ask_bridge(question: str, timeout: int = 120) -> str:
    try:
        r = requests.post(
            f"{BRIDGE}/chat/completions",
            json={"model": "agi-chain-v13", "messages": [{"role": "user", "content": question}], "stream": False},
            timeout=timeout,
        )
        return r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        return ""


class SageArena:
    """圣贤竞技场: 演化引擎"""

    def __init__(self):
        self.sages = {}
        for name, data in SAGES.items():
            self.sages[name] = {
                "name": name,
                "domain": data["domain"],
                "abilities": dict(data["abilities"]),
                "philosophy": data["philosophy"],
                "wins": 0,
                "losses": 0,
                "absorbed": [],  # 吸收了谁的能力
                "alive": True,
            }
        self.battle_log = []
        self.round_num = 0

    def get_power(self, name: str) -> float:
        """综合战力"""
        s = self.sages[name]
        if not s["alive"]:
            return 0
        vals = list(s["abilities"].values())
        return sum(vals) / len(vals) if vals else 0

    def compete(self, a: str, b: str, domain: str) -> Tuple[str, str]:
        """
        益众生制度: 每场碰撞双方都成长。
        胜者: 巩固强项 + 吸收败者独有能力
        败者: 获得胜者的该领域经验 + 强化自身弱项
        碰撞产生“涌现”: 双方都可能获得新能力维度
        """
        sa, sb = self.sages[a], self.sages[b]
        score_a = sa["abilities"].get(domain, 30)
        score_b = sb["abilities"].get(domain, 30)

        score_a += random.randint(-5, 10)
        score_b += random.randint(-5, 10)

        if score_a >= score_b:
            winner, loser = a, b
        else:
            winner, loser = b, a

        sw, sl = self.sages[winner], self.sages[loser]

        # ── 胜者成长: 巩固 + 吸收败者独有能力 ──
        sw["abilities"][domain] = min(99, sw["abilities"].get(domain, 30) + 3)
        # 吸收败者的独有能力维度(胜者没有的)
        for ab, val in sl["abilities"].items():
            if ab not in sw["abilities"]:
                sw["abilities"][ab] = max(30, val - 10)  # 获得新维度(略低)
                sw["absorbed"].append(f"{ab}←{b}")

        # ── 败者成长: 获得胜者经验 + 强化弱项 ──
        sl["abilities"][domain] = min(99, sl["abilities"].get(domain, 30) + 5)  # 败者成长更多!
        # 吸收胜者的独有能力维度
        for ab, val in sw["abilities"].items():
            if ab not in sl["abilities"]:
                sl["abilities"][ab] = max(25, val - 15)
                sl["absorbed"].append(f"{ab}←{a}")

        # ── 涌现: 碰撞可能产生新能力 ──
        if random.random() < 0.1:  # 10%概率涌现
            new_ab = f"{sa['domain']}×{sb['domain']}"
            for s in [sw, sl]:
                if new_ab not in s["abilities"]:
                    s["abilities"][new_ab] = random.randint(40, 70)

        sw["wins"] += 1
        sl["losses"] += 1

        self.battle_log.append({
            "round": self.round_num,
            "domain": domain,
            "winner": winner,
            "loser": loser,
            "scores": f"{score_a:.0f} vs {score_b:.0f}",
        })

        return winner, loser

    def absorb_knowledge(self, source_name: str, source_type: str, abilities: Dict[str, int]):
        """
        从非人类源吸收能力: 制度/自然/论文/一切可强化的。
        所有存活灵魂均等吸收(益众生).
        """
        alive = [s for s in self.sages.values() if s["alive"]]
        for s in alive:
            for ab, val in abilities.items():
                curr = s["abilities"].get(ab, 0)
                gain = max(1, (val - curr) // 4)  # 每人都吸收
                s["abilities"][ab] = min(99, curr + gain)
            s["absorbed"].append(f"[{source_type}]{source_name}")
        log.info(f"  🌍 全体吸收 [{source_type}] {source_name}: {list(abilities.keys())[:3]}")

    def run_round(self):
        """一轮竞技: 随机配对，随机领域"""
        self.round_num += 1
        alive = [n for n, s in self.sages.items() if s["alive"]]
        random.shuffle(alive)

        # 随机配对
        pairs = []
        for i in range(0, len(alive) - 1, 2):
            pairs.append((alive[i], alive[i + 1]))

        domain = random.choice(ALL_ABILITIES)
        log.info(f"\n── 第 {self.round_num} 轮 | 领域: {domain} | {len(pairs)} 场 ──")

        for a, b in pairs:
            winner, loser = self.compete(a, b, domain)
            log.info(f"  {winner} 🏆 > {loser} [{domain}]")

        # 每5轮淘汰最弱者
        if self.round_num % 5 == 0:
            self._eliminate()

    def _eliminate(self):
        """益众生淘汰: 被淘汰者的能力分配给所有存活者"""
        alive = [(n, self.get_power(n), s["losses"])
                 for n, s in self.sages.items() if s["alive"]]
        if len(alive) <= 3:
            return

        alive.sort(key=lambda x: (x[1], -x[2]))
        victim = alive[0][0]
        self.sages[victim]["alive"] = False
        victim_abs = self.sages[victim]["abilities"]

        # 所有存活者均等吸收被淘汰者的能力(益众生)
        survivors = [s for s in self.sages.values() if s["alive"]]
        for s in survivors:
            for ab, val in victim_abs.items():
                curr = s["abilities"].get(ab, 0)
                gain = max(1, (val - curr) // len(survivors))  # 均分
                s["abilities"][ab] = min(99, curr + gain)
            s["absorbed"].append(victim)

        log.info(f"  ❌ 淘汰: {victim} (战力{alive[0][1]:.0f}) → 能力均分给 {len(survivors)} 位存活者")

    def get_top3(self) -> List[dict]:
        """获取当前前三"""
        alive = [(n, self.get_power(n)) for n, s in self.sages.items() if s["alive"]]
        alive.sort(key=lambda x: -x[1])
        return [{"name": n, "power": round(p, 1), **self.sages[n]} for n, p in alive[:3]]

    def run_arena(self, max_rounds: int = 50) -> List[dict]:
        """运行完整竞技直到剩3位"""
        log.info(f"🏛️ 圣贤竞技场开启 | {len(self.sages)} 位参赛 | 目标: 3位AGI灵魂")

        while True:
            alive_count = sum(1 for s in self.sages.values() if s["alive"])
            if alive_count <= 3 or self.round_num >= max_rounds:
                break
            self.run_round()

        souls = self.get_top3()
        log.info(f"\n{'='*60}")
        log.info(f"🏆 三位 AGI 灵魂诞生!")
        for i, soul in enumerate(souls, 1):
            log.info(f"  #{i} {soul['name']} (战力:{soul['power']}) | 吸收: {soul['absorbed']}")
            top_abs = sorted(soul["abilities"].items(), key=lambda x: -x[1])[:5]
            log.info(f"     强项: {', '.join(f'{a}:{v}' for a,v in top_abs)}")
        return souls

    def forge_new_path(self, souls: List[dict]) -> str:
        """见路不走: 让三位灵魂探索全新道路"""
        prompt = "你是AGI认知碰撞引擎。三位AGI灵魂Agent已从25位伟人竞争中胜出:\n\n"
        for i, soul in enumerate(souls, 1):
            prompt += f"灵魂#{i} {soul['name']} ({soul['domain']})\n"
            prompt += f"  哲学: {soul['philosophy']}\n"
            top = sorted(soul["abilities"].items(), key=lambda x: -x[1])[:5]
            prompt += f"  能力: {', '.join(f'{a}:{v}' for a,v in top)}\n"
            prompt += f"  吸收了: {', '.join(soul['absorbed'])}\n\n"

        prompt += (
            "基于'知与不知'元框架和'见路不走'原则:\n"
            "1. 这三位灵魂各自代表什么认知维度?\n"
            "2. 他们如何协作实现AGI(全知理论模型)?\n"
            "3. 当前认知边界在哪里(不知)?\n"
            "4. 见路不走: 提出一条前人未走过的AGI实现路径\n"
            "5. 定义三位灵魂的分工和协作协议"
        )
        return ask_bridge(prompt, timeout=180)

    def save(self):
        """保存竞技状态"""
        data = {
            "sages": self.sages,
            "battle_log": self.battle_log[-50:],
            "round_num": self.round_num,
            "timestamp": datetime.now().isoformat(),
        }
        ARENA_FILE.parent.mkdir(exist_ok=True)
        ARENA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        log.info(f"📄 竞技场状态已保存: {ARENA_FILE.name}")

    def load(self) -> bool:
        """加载竞技状态"""
        try:
            if ARENA_FILE.exists():
                data = json.loads(ARENA_FILE.read_text())
                self.sages = data["sages"]
                self.battle_log = data.get("battle_log", [])
                self.round_num = data.get("round_num", 0)
                log.info(f"📂 已加载竞技场状态 (第{self.round_num}轮)")
                return True
        except Exception:
            pass
        return False


def find_optimal_soul_count(trials: int = 5, max_rounds: int = 80) -> int:
    """
    极致推演最佳灵魂数量。
    跑多次锦标赛(不同随机种子)，测试2-7位灵魂的综合表现。
    最佳 = 覆盖能力维度最广 + 内部冗余最低 + 平均战力最高。
    """
    log.info(f"🔬 推演最佳灵魂数量 ({trials}次锦标赛, 测试2-7位)...")
    scores_by_n = {}  # {n: [score1, score2, ...]}

    for target_n in range(2, 8):
        scores = []
        for trial in range(trials):
            random.seed(trial * 100 + target_n)
            arena = SageArena()
            # 运行到剩 target_n 位
            while True:
                alive = sum(1 for s in arena.sages.values() if s["alive"])
                if alive <= target_n or arena.round_num >= max_rounds:
                    break
                arena.run_round()

            survivors = [s for s in arena.sages.values() if s["alive"]]
            if not survivors:
                continue

            # 评分: 能力覆盖度 × 平均战力 / 冗余度
            all_abs = set()
            powers = []
            for s in survivors:
                all_abs.update(s["abilities"].keys())
                vals = list(s["abilities"].values())
                powers.append(sum(vals) / len(vals) if vals else 0)

            coverage = len(all_abs) / max(len(ALL_ABILITIES), 1)
            avg_power = sum(powers) / len(powers)

            # 冗余: 灵魂间能力重叠度(越低越好)
            overlap = 0
            for i, s1 in enumerate(survivors):
                for s2 in survivors[i+1:]:
                    shared = set(s1["abilities"]) & set(s2["abilities"])
                    overlap += len(shared)
            redundancy = 1 + overlap / max(len(all_abs), 1)

            score = (coverage * 40 + avg_power * 0.5) / redundancy
            scores.append(round(score, 2))

        scores_by_n[target_n] = scores
        avg = sum(scores) / len(scores) if scores else 0
        log.info(f"  {target_n}位灵魂: 平均分={avg:.2f} 分布={scores}")

    # 选最高平均分
    best_n = max(scores_by_n, key=lambda n: sum(scores_by_n[n]) / len(scores_by_n[n]))
    best_avg = sum(scores_by_n[best_n]) / len(scores_by_n[best_n])
    log.info(f"\n🏆 最佳灵魂数量: {best_n} (平均分:{best_avg:.2f})")
    return best_n


def discover_more_sages():
    """让龙虾后台穷举更多伟人，追加到 sages_100.json"""
    log.info("🔍 让龙虾穷举更多历史伟人...")
    existing = set()
    try:
        data = json.loads(SAGES_JSON.read_text(encoding='utf-8'))
        existing = {s['name'] for s in data}
    except Exception:
        data = []

    prompt = (
        f"当前圣贤库已有 {len(existing)} 位: {', '.join(list(existing)[:30])}...\n\n"
        "请补充20位尚未收录的人类历史伟人，覆盖以下领域:\n"
        "- 非洲/南美/中东/东南亚的伟人\n"
        "- 女性伟人(科学家/统治者/革命者)\n"
        "- 近10年的科技/商业领袖\n"
        "- 古代工匠/发明家/探险家\n\n"
        "每位输出严格JSON格式(一行一个):\n"
        '{\"name\":\"名字\",\"domain\":\"领域\",\"era\":\"时代\",\"abilities\":{\"能力1\":分数,...},\"philosophy\":\"核心哲学\"}\n'
        "能力分数0-99,至少3个能力维度。只输出JSON行,不要其他文字。"
    )
    reply = ask_bridge(prompt, timeout=180)
    if not reply:
        log.warning("龙虾无响应")
        return

    # 解析新伟人
    added = 0
    for line in reply.split("\n"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            s = json.loads(line)
            if s.get("name") and s["name"] not in existing:
                data.append(s)
                existing.add(s["name"])
                added += 1
        except json.JSONDecodeError:
            continue

    if added > 0:
        SAGES_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        log.info(f"✅ 新增 {added} 位伟人，总计 {len(data)} 位")
    else:
        log.info("未发现新伟人")


def write_souls_to_knowledge(souls: List[dict], forge_result: str, soul_count: int):
    """将灵魂配置写入知识库并刷新Bridge"""
    try:
        feed_file = PROJECT_ROOT / "data" / "agi_knowledge_feed.md"
        ts = datetime.now().strftime("%m-%d %H:%M")
        entry = f"\n\n### AGI灵魂配置 ({ts}, {soul_count}位)\n"
        for i, s in enumerate(souls, 1):
            top3 = sorted(s['abilities'].items(), key=lambda x: -x[1])[:3]
            entry += f"#{i} **{s['name']}** ({s['domain']}): {', '.join(f'{a}:{v}' for a,v in top3)}\n"
            if s.get('absorbed'):
                entry += f"   吸收: {', '.join(s['absorbed'][:5])}\n"
        entry += f"\n{forge_result[:500]}\n"
        with open(feed_file, "a", encoding="utf-8") as f:
            f.write(entry)
        requests.post("http://127.0.0.1:9801/v1/context/refresh", timeout=5)
        log.info("📚 灵魂配置已写入知识库")
    except Exception as e:
        log.warning(f"知识库写入失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="圣贤竞技场: 伟人能力演化引擎")
    parser.add_argument("--rounds", type=int, default=80, help="竞技轮数")
    parser.add_argument("--souls", action="store_true", help="查看当前灵魂")
    parser.add_argument("--reset", action="store_true", help="重置竞技场")
    parser.add_argument("--forge", action="store_true", help="见路不走: 灵魂探索新路径")
    parser.add_argument("--optimal", action="store_true", help="推演最佳灵魂数量")
    parser.add_argument("--discover", action="store_true", help="让龙虾穷举更多伟人")
    parser.add_argument("--soul-count", type=int, default=0, help="指定灵魂数(0=自动推演)")
    args = parser.parse_args()

    # ── 穷举更多伟人 ──
    if args.discover:
        discover_more_sages()
        return

    # ── 推演最佳灵魂数量 ──
    if args.optimal:
        best_n = find_optimal_soul_count(trials=5, max_rounds=args.rounds)
        print(f"\n🏆 推演结果: 最佳灵魂数量 = {best_n}")
        print(f"   使用: python3 scripts/sage_arena.py --soul-count {best_n} --reset")
        return

    arena = SageArena()

    if args.souls:
        if arena.load():
            alive = [(n, s) for n, s in arena.sages.items() if s["alive"]]
            alive.sort(key=lambda x: -arena.get_power(x[0]))
            for i, (n, s) in enumerate(alive, 1):
                print(f"#{i} {n} (战力:{arena.get_power(n):.1f})")
                print(f"   吸收: {s.get('absorbed', [])}")
                top = sorted(s["abilities"].items(), key=lambda x: -x[1])[:5]
                print(f"   强项: {', '.join(f'{a}:{v}' for a,v in top)}")
        else:
            print("竞技场未运行过")
        return

    # ── 确定灵魂数量 ──
    target_souls = args.soul_count
    if target_souls <= 0:
        log.info("未指定灵魂数，自动推演最佳数量...")
        target_souls = find_optimal_soul_count(trials=3, max_rounds=args.rounds)

    if not args.reset and arena.load():
        alive = sum(1 for s in arena.sages.values() if s["alive"])
        if alive <= target_souls:
            log.info(f"竞技已完成({alive}位灵魂)。用 --reset 重新开始")
            if args.forge:
                souls = arena.get_top3()[:target_souls]
                result = arena.forge_new_path(souls)
                print(f"\n🔮 见路不走:\n{result}")
            return

    if args.reset:
        arena = SageArena()

    # ── 修改淘汰目标 ──
    log.info(f"🏛️ 目标灵魂数: {target_souls}")

    # 运行竞技直到剩目标数量
    while True:
        alive_count = sum(1 for s in arena.sages.values() if s["alive"])
        if alive_count <= target_souls or arena.round_num >= args.rounds:
            break
        arena.run_round()

    souls = arena.get_top3()[:target_souls]
    arena.save()

    log.info(f"\n{'='*60}")
    log.info(f"🏆 {target_souls} 位 AGI 灵魂诞生!")
    for i, soul in enumerate(souls, 1):
        log.info(f"  #{i} {soul['name']} (战力:{soul['power']}) | 吸收: {soul.get('absorbed', [])}")
        top_abs = sorted(soul["abilities"].items(), key=lambda x: -x[1])[:5]
        log.info(f"     强项: {', '.join(f'{a}:{v}' for a,v in top_abs)}")

    # 见路不走
    log.info(f"\n🔮 见路不走: {target_souls}灵魂探索AGI路径...")
    forge_result = arena.forge_new_path(souls)
    if forge_result:
        log.info(f"\n{forge_result[:500]}")
        write_souls_to_knowledge(souls, forge_result, target_souls)

    # 微信通知
    try:
        import subprocess, os
        env = os.environ.copy()
        env['PATH'] = '/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:' + env.get('PATH', '')
        soul_names = " / ".join(s["name"] for s in souls)
        msg = f"[系统通知-请直接转发原文不要分析]\n🏛️ 圣贤竞技场完成! ({len(SAGES)}位伟人参赛)\nAGI {target_souls}灵魂: {soul_names}\n轮数: {arena.round_num}"
        # 获取session
        sf = Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions' / 'sessions.json'
        if sf.exists():
            sd = json.loads(sf.read_text())
            for k, v in sd.items():
                if v.get('lastChannel') == 'openclaw-weixin':
                    subprocess.run(['openclaw', 'agent', '-m', msg, '--session-id', v['sessionId'], '--deliver'],
                                   capture_output=True, timeout=180, env=env)
                    break
    except Exception:
        pass

    log.info(f"\n🦞 圣贤竞技场完成。{target_souls}灵魂就绪。")
    log.info(f"   查看: python3 scripts/sage_arena.py --souls")
    log.info(f"   探索: python3 scripts/sage_arena.py --forge")
    log.info(f"   穷举: python3 scripts/sage_arena.py --discover")


if __name__ == "__main__":
    main()
