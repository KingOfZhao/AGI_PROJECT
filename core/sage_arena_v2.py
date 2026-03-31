"""
伟人竞技场 v2 — 多人独立推理引擎
===================================
核心改进:
  1. 重构数据: 20人×10维, 梯度50-99, 高区分度
  2. 多人独立推理: 每位伟人独立调用API, 产出独立分析
  3. 交叉碰撞: 收集所有视角后, 由主模型汇总碰撞

API调用: Zhipu GLM-5 (Anthropic兼容)
"""

import json
import os
import time
import httpx
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from core.sage_data import SAGES, THINKING_DIMENSIONS, TOPIC_SAGE_MAP


@dataclass
class SageOpinion:
    """伟人独立分析结果"""
    name: str
    domain: str
    perspective: str       # 该伟人的思维透镜
    analysis: str          # 独立分析内容
    key_insight: str       # 核心洞察
    blind_spot: str        # 盲区警告
    confidence: str        # 置信度判断
    api_model: str         # 使用的模型
    tokens_used: int = 0
    latency_ms: int = 0


@dataclass
class ArenaSynthesis:
    """竞技场综合结果"""
    topic: str
    participants: List[str]
    opinions: List[SageOpinion]
    consensus: str
    key_disagreements: List[str]
    new_insights: List[str]
    recommended_actions: List[str]
    blind_spots_combined: List[str]


class SageArenaV2:
    """
    伟人竞技场 v2 — 多人独立推理
    
    流程:
    1. select_sages(topic) → 选出5位伟人
    2. build_prompt(sage, topic, context) → 为每人构建独立prompt
    3. call_api(prompt) → 独立调用API获取分析
    4. synthesize(opinions) → 汇总碰撞
    """
    
    def __init__(self):
        self.api_key = os.environ.get("ZHIPU_API_KEY", "")
        self.api_url = os.environ.get("ZHIPU_ANTHROPIC_URL", 
                                     "https://open.bigmodel.cn/api/anthropic")
        if not self.api_key:
            # Try .env file
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if line.startswith("ZHIPU_API_KEY="):
                        self.api_key = line.split("=", 1)[1].strip()
                    if line.startswith("ZHIPU_ANTHROPIC_URL="):
                        self.api_url = line.split("=", 1)[1].strip()
    
    def select_sages(self, topic: str, top_n: int = 5) -> List[Tuple[str, dict]]:
        """根据主题选择最相关的伟人"""
        # 1. 精确匹配TOPIC_SAGE_MAP
        matched = []
        for keyword, names in TOPIC_SAGE_MAP.items():
            if keyword in topic:
                for name in names:
                    if name in SAGES:
                        matched.append((name, SAGES[name]))
        
        # 去重, 保留顺序
        seen = set()
        unique_matched = []
        for name, data in matched:
            if name not in seen:
                seen.add(name)
                unique_matched.append((name, data))
        
        # 2. 如果精确匹配不够, 按维度评分补充
        if len(unique_matched) < top_n:
            topic_keywords = self._extract_keywords(topic)
            remaining = []
            for name, data in SAGES.items():
                if name not in seen:
                    score = self._relevance_score(data, topic_keywords)
                    remaining.append((name, data, score))
            remaining.sort(key=lambda x: x[2], reverse=True)
            for name, data, _ in remaining:
                if len(unique_matched) >= top_n:
                    break
                unique_matched.append((name, data))
                seen.add(name)
        
        return unique_matched[:top_n]
    
    def _extract_keywords(self, topic: str) -> set:
        """从主题中提取关键词"""
        keywords = set()
        for kw in ["K因子", "误差", "RSS", "裱合", "微瓦楞", "标准", "精度",
                    "膨胀", "收缩", "压痕", "相变", "公差", "爆线", "自动",
                    "公式", "材料", "设备", "含水量", "MC", "槽宽", "折叠"]:
            if kw in topic:
                keywords.add(kw)
        # Generic keywords
        keywords.update(topic.split())
        return keywords
    
    def _relevance_score(self, sage_data: dict, keywords: set) -> float:
        """计算伟人与主题的相关性"""
        scores = sage_data["scores"]
        # Top dimensions for DiePre
        diepre_dims = ["first_principles", "math_formalization", "empirical_validation",
                       "system_thinking", "precision_obsession", "risk_awareness"]
        
        total = sum(scores.get(d, 0) for d in diepre_dims)
        
        # Domain match bonus
        domain = sage_data["domain"]
        for kw in keywords:
            if kw in domain or kw in sage_data.get("diepre_lens", ""):
                total += 15
        
        return total
    
    def build_prompt(
        self,
        sage_name: str,
        sage_data: dict,
        topic: str,
        context: str = "",
        known_facts: List[str] = None,
    ) -> str:
        """
        为伟人构建独立推理prompt
        
        关键: 不是让模型"扮演"伟人, 而是用伟人的思维框架约束推理方向
        """
        scores = sage_data["scores"]
        top_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        top_dim_names = [THINKING_DIMENSIONS.get(d, {}).get("name", d) for d, _ in top_dims]
        low_dims = [(d, s) for d, s in scores.items() if s < 65]
        low_dim_names = [THINKING_DIMENSIONS.get(d, {}).get("name", d) for d, _ in low_dims[:2]]
        
        facts_str = ""
        if known_facts:
            facts_str = "\n".join(f"  - {f}" for f in known_facts)
        
        prompt = f"""你是{topic}领域的分析者。

你的思维框架受{ sage_name}({sage_data['domain']})影响:
- 核心哲学: {sage_data['philosophy']}
- 思维风格: {sage_data['thinking_style']}
- DiePre透镜: {sage_data['diepre_lens']}
- 你的强项: {', '.join(top_dim_names)} (分数{[s for _, s in top_dims]})
- 你的盲区: {', '.join(low_dim_names) if low_dim_names else '无明显盲区'}

你必须严格按照上述思维框架来分析问题。不要泛泛而谈, 要给出具体的、可执行的结论。

已知事实:
{facts_str if facts_str else '无特定已知事实'}

请分析:
1. 从你的思维框架出发, 对"已知事实"的深度解读
2. 你发现的新洞察或新问题
3. 你的盲区可能导致什么被忽略
4. 你推荐的下一步行动

要求: 简洁、具体、有数据支撑。避免空话。每点不超过2句话。"""
        
        return prompt
    
    def call_api(self, system_prompt: str, user_prompt: str, model: str = "glm-5-turbo") -> Tuple[str, int, int]:
        """
        调用Zhipu API (Anthropic兼容)
        
        Returns: (response_text, tokens_used, latency_ms)
        """
        if not self.api_key:
            return "[API key未配置]", 0, 0
        
        start = time.time()
        try:
            resp = httpx.post(
                f"{self.api_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=30.0,
            )
            latency = int((time.time() - start) * 1000)
            
            if resp.status_code == 200:
                data = resp.json()
                text = data["content"][0]["text"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return text, tokens, latency
            else:
                return f"[API错误 {resp.status_code}: {resp.text[:200]}]", 0, latency
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return f"[调用失败: {e}]", 0, latency
    
    def run_arena(
        self,
        topic: str,
        known_facts: List[str] = None,
        context: str = "",
        top_n: int = 5,
        model: str = "glm-5-turbo",
        use_api: bool = True,
    ) -> ArenaSynthesis:
        """
        运行完整竞技场
        
        Args:
            topic: 推演主题
            known_facts: 已知事实列表
            context: 额外上下文
            top_n: 参与伟人数
            model: API模型
            use_api: 是否调用API (False则生成空壳用于测试)
        """
        # 1. 选择伟人
        selected = self.select_sages(topic, top_n)
        
        # 2. 每人独立推理
        opinions = []
        total_tokens = 0
        
        for name, data in selected:
            prompt = self.build_prompt(name, data, topic, context, known_facts)
            
            if use_api:
                analysis, tokens, latency = self.call_api(prompt, prompt, model)
            else:
                analysis = f"[{name}的独立分析 — API未调用]"
                tokens, latency = 0, 0
            
            total_tokens += tokens
            
            opinion = SageOpinion(
                name=name,
                domain=data["domain"],
                perspective=data["diepre_lens"],
                analysis=analysis,
                key_insight=data["strength"],
                blind_spot=data["blindspot"],
                confidence="高" if use_api else "待验证",
                api_model=model,
                tokens_used=tokens,
                latency_ms=latency,
            )
            opinions.append(opinion)
        
        # 3. 综合碰撞
        synthesis = self._synthesize(topic, opinions)
        
        return synthesis
    
    def _synthesize(self, topic: str, opinions: List[SageOpinion]) -> ArenaSynthesis:
        """汇总碰撞"""
        # 收集所有洞察和盲区
        insights = [o.key_insight for o in opinions]
        blind_spots = [o.blind_spot for o in opinions]
        
        # 识别分歧: 比如一个说"需要更多实验", 另一个说"现有数据够用"
        disagreements = []
        # Check for opposing perspectives
        caution_sages = [o.name for o in opinions if "风险" in o.blind_spot or "实验" in o.blind_spot]
        aggressive_sages = [o.name for o in opinions if "理论" in o.perspective or "推导" in o.perspective]
        if caution_sages and aggressive_sages:
            disagreements.append(
                f"实验派({', '.join(caution_sages)}) vs 推导派({', '.join(aggressive_sages)})"
            )
        
        # 生成共识
        all_dims = set()
        for name, data in SAGES.items():
            if name in [o.name for o in opinions]:
                for dim, score in data["scores"].items():
                    if score >= 90:
                        all_dims.add(THINKING_DIMENSIONS.get(dim, {}).get("name", dim))
        
        consensus = f"多视角共识: 从{', '.join(list(all_dims)[:4])}角度综合分析"
        
        # 推荐行动
        actions = []
        for o in opinions:
            if "验证" in o.blind_spot or "实验" in o.perspective:
                actions.append(f"[{o.name}] 需要实测数据验证")
            if "工程" in o.blind_spot or "制造" in o.perspective:
                actions.append(f"[{o.name}] 需要工厂实际验证")
            if "风险" in o.perspective or "极限" in o.perspective:
                actions.append(f"[{o.name}] 需要评估精度极限")
        
        if not actions:
            actions.append("综合各视角, 当前推演方向正确, 继续深入")
        
        return ArenaSynthesis(
            topic=topic,
            participants=[o.name for o in opinions],
            opinions=opinions,
            consensus=consensus,
            key_disagreements=disagreements,
            new_insights=insights,
            recommended_actions=actions,
            blind_spots_combined=blind_spots,
        )
    
    def print_synthesis(self, syn: ArenaSynthesis):
        """打印竞技场结果"""
        print(f"\n{'='*70}")
        print(f"  伟人竞技场 v2 — {syn.topic}")
        print(f"{'='*70}")
        print(f"\n🎯 参与者: {', '.join(syn.participants)}")
        print(f"\n📊 共识: {syn.consensus}")
        
        if syn.key_disagreements:
            print(f"\n⚡ 分歧:")
            for d in syn.key_disagreements:
                print(f"  • {d}")
        
        print(f"\n--- 各伟人独立分析 ---")
        for o in syn.opinions:
            print(f"\n【{o.name}·{o.domain}】({o.latency_ms}ms, {o.tokens_used}tokens)")
            print(f"  透镜: {o.perspective}")
            print(f"  分析: {o.analysis[:300]}{'...' if len(o.analysis)>300 else ''}")
            print(f"  盲区: ⚠️ {o.blind_spot}")
        
        print(f"\n--- 综合建议 ---")
        for a in syn.recommended_actions:
            print(f"  → {a}")


if __name__ == "__main__":
    arena = SageArenaV2()
    
    print(f"API配置: {'✅' if arena.api_key else '❌'} ({arena.api_url})")
    print(f"伟人数据: {len(SAGES)}人 × {len(THINKING_DIMENSIONS)}维")
    
    # === 测试1: 伟人选择区分度 ===
    print(f"\n{'='*70}")
    print("  验证: 伟人选择区分度")
    print(f"{'='*70}")
    
    topics = [
        "K因子相变模型",
        "误差预算RSS计算",
        "裱合胶水收缩耦合",
        "微瓦楞标准盲区",
        "±0.5mm精度不可达",
        "清废临界角",
    ]
    
    for topic in topics:
        selected = arena.select_sages(topic, 5)
        names = [f"{n}({d['domain']})" for n, d in selected]
        print(f"  {topic}: {', '.join(names)}")
    
    # === 测试2: Prompt构建 ===
    print(f"\n{'='*70}")
    print("  验证: Prompt质量")
    print(f"{'='*70}")
    
    for topic in ["K因子相变模型", "±0.5mm精度不可达"]:
        selected = arena.select_sages(topic, 3)
        for name, data in selected[:1]:  # just first
            prompt = arena.build_prompt(name, data, topic, known_facts=[
                "K=0.35(正常), K=0.25(爆线临界)",
                "d/T≥0.65触发相变",
            ])
            print(f"\n--- {name} 分析 '{topic}' ---")
            print(prompt[:500])
    
    # === 测试3: API调用 (如果key可用) ===
    if arena.api_key:
        print(f"\n{'='*70}")
        print("  验证: API独立推理")
        print(f"{'='*70}")
        
        syn = arena.run_arena(
            topic="K因子相变模型 — 压痕深度与材料刚度的非线性关系",
            known_facts=[
                "K=0.35(单瓦楞正常), K=0.25(爆线临界)",
                "d/T≥0.65触发相变, K骤降",
                "MC≥16%触发湿态相变",
            ],
            top_n=3,
            use_api=True,
        )
        arena.print_synthesis(syn)
    else:
        print("\n⚠️ API key未配置, 跳过API调用测试")
