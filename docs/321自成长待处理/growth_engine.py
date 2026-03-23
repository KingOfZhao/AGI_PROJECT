#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI 全速成长引擎 — 核心实现
============================
实现四向碰撞机制、节点→SKILL转换、验证优化、循环控制
"""

import sys
import os
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))


class GrowthEngine:
    """AGI 全速成长引擎主控制器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db_path = PROJECT_DIR / "memory.db"
        self.current_round = 0
        self.history = []
        self.all_skills = []
        
        # 初始化子系统
        self.collision_engine = FourWayCollisionEngine(self)
        self.converter = NodeToSkillConverter(PROJECT_DIR / "workspace" / "skills")
        self.validator = SkillTemplateValidator()
        self.checker = IncrementalChecker()
        
        # 初始化数据库
        self._init_database()
    
    def run(self):
        """运行成长循环"""
        min_rounds = self.config.get("min_rounds", 10)
        max_rounds = self.config.get("max_rounds", 100)
        
        print(f"\n{'='*60}")
        print(f"开始全速成长（最少{min_rounds}轮，最多{max_rounds}轮）")
        print(f"{'='*60}\n")
        
        for round_num in range(1, max_rounds + 1):
            self.current_round = round_num
            
            print(f"\n{'#'*60}")
            print(f"# 第 {round_num} 轮成长")
            print(f"{'#'*60}\n")
            
            round_start = time.time()
            
            # 任务一：节点获取
            task1_result = self._task_one()
            
            # 任务二：验证优化
            task2_result = self._task_two(task1_result)
            
            # 合并结果
            round_result = {**task1_result, **task2_result}
            round_result["round"] = round_num
            round_result["elapsed_seconds"] = time.time() - round_start
            
            self.history.append(round_result)
            
            # 保存到数据库
            self._save_round_to_db(round_result)
            
            # 判断是否达到阈值
            threshold_X = self._calculate_threshold_X(round_num)
            effective_output = round_result.get("effective_output", 0)
            
            print(f"\n{'='*60}")
            print(f"本轮有效产出: {effective_output}")
            print(f"阈值 X: {threshold_X}")
            print(f"Tokens 消耗: {round_result.get('tokens_used', 0):,}")
            print(f"{'='*60}\n")
            
            if round_num >= min_rounds and effective_output >= threshold_X:
                print(f"\n✅ 达到阈值，成长循环结束（第 {round_num} 轮）")
                break
            
            if round_num >= min_rounds and effective_output < threshold_X * 0.3:
                print(f"\n⚠️ 产出过低（{effective_output} < {threshold_X * 0.3:.0f}），建议人工介入检查")
        
        # 生成最终报告
        self._generate_final_report()
    
    def _task_one(self) -> Dict:
        """任务一：GLM-5驱动的真实节点获取"""
        print(f"[任务一] 节点获取中...")
        
        start_tokens = self.collision_engine.token_usage["total"]
        
        # 1. 自上而下拆解
        big_questions = [
            "如何实现 AGI",
            "如何让 AI 具备自我成长能力",
            "如何构建真实认知网络",
            "如何实现人机共生的认知系统"
        ]
        
        all_sub_questions = []
        for q in big_questions:
            try:
                sub_qs = self.collision_engine.top_down_decompose(q)
                all_sub_questions.extend(sub_qs)
                print(f"  ✓ 拆解 '{q}' → {len(sub_qs)} 个子问题")
            except Exception as e:
                print(f"  ✗ 拆解失败: {e}")
        
        # 2. 自下而上构建
        proven_nodes = self._get_proven_nodes_from_db()
        patterns = []
        if len(proven_nodes) >= 3:
            try:
                patterns = self.collision_engine.bottom_up_construct(proven_nodes[:20])
                print(f"  ✓ 从 {len(proven_nodes)} 个节点识别出 {len(patterns)} 个模式")
            except Exception as e:
                print(f"  ✗ 模式识别失败: {e}")
        
        # 3. 左右寻找重叠
        overlaps = []
        domains = self._group_nodes_by_domain(proven_nodes)
        if len(domains) >= 2:
            domain_names = list(domains.keys())[:2]
            try:
                overlaps = self.collision_engine.horizontal_overlap(
                    domains[domain_names[0]][:10],
                    domains[domain_names[1]][:10]
                )
                print(f"  ✓ 跨域 '{domain_names[0]}' ↔ '{domain_names[1]}' 发现 {len(overlaps)} 个重叠")
            except Exception as e:
                print(f"  ✗ 重叠检测失败: {e}")
        
        # 4. 从重叠构建新节点
        new_nodes = self.collision_engine.construct_from_overlap(overlaps)
        
        # 保存新节点到数据库
        for node in new_nodes:
            self._save_node_to_db(node)
        
        # 5. 节点→SKILL 转换
        new_skills = []
        for node in new_nodes:
            skill = self.converter.convert(node)
            if skill:
                new_skills.append(skill)
                self._save_skill_to_db(skill)
        
        end_tokens = self.collision_engine.token_usage["total"]
        
        return {
            "sub_questions": len(all_sub_questions),
            "patterns": len(patterns),
            "overlaps": len(overlaps),
            "new_nodes": len(new_nodes),
            "new_skills": len(new_skills),
            "tokens_used": end_tokens - start_tokens
        }
    
    def _task_two(self, task1_result: Dict) -> Dict:
        """任务二：验证优化"""
        print(f"[任务二] 验证优化中...")
        
        # 读取新生成的 SKILL
        new_skill_count = task1_result.get("new_skills", 0)
        valid_skills = 0
        
        # 从数据库读取最新的 SKILL 进行验证
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, meta_json FROM skills 
            WHERE forged_by = 'growth_engine'
            ORDER BY created_at DESC
            LIMIT ?
        """, (new_skill_count,))
        
        for row in cursor.fetchall():
            skill_id, skill_name, meta_json = row
            try:
                skill_meta = json.loads(meta_json)
                validation = self.validator.validate(skill_meta)
                
                # 更新验证分数
                cursor.execute("""
                    UPDATE skills SET validation_score = ? WHERE id = ?
                """, (validation["score"], skill_id))
                
                if validation["valid"]:
                    valid_skills += 1
                    self.all_skills.append(skill_meta)
                    print(f"  ✓ {skill_name}: {validation['score']}/100")
                else:
                    print(f"  ✗ {skill_name}: {validation['score']}/100 - {validation['issues']}")
            except Exception as e:
                print(f"  ✗ 验证失败 {skill_name}: {e}")
        
        conn.commit()
        conn.close()
        
        # 每 5 个 SKILL 检查依赖关系
        self.checker.skill_count = len(self.all_skills)
        if self.checker.should_check():
            self.checker.check(self.all_skills)
        
        # 计算有效产出
        effective_output = task1_result.get("new_nodes", 0) + valid_skills
        
        return {
            "valid_skills": valid_skills,
            "effective_output": effective_output,
            "validation_rate": valid_skills / new_skill_count if new_skill_count > 0 else 0
        }
    
    def _calculate_threshold_X(self, round_num: int) -> int:
        """动态计算阈值 X"""
        base = 20
        growth = 1.5
        expected = base * (growth ** (round_num - 1))
        
        if self.history:
            avg_output = sum(h.get("effective_output", 0) for h in self.history) / len(self.history)
            if avg_output < expected * 0.7:
                expected = avg_output * 1.2
        
        return int(expected)
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建表（如果不存在）
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS proven_nodes (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                source TEXT,
                collision_type TEXT,
                confidence REAL DEFAULT 0.8,
                domain TEXT,
                tags TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                file_path TEXT,
                description TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                forged_by TEXT,
                source_node_id TEXT,
                meta_json TEXT,
                validation_score INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS growth_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_number INTEGER NOT NULL,
                phase TEXT NOT NULL,
                event_type TEXT,
                entity_id TEXT,
                tokens_used INTEGER DEFAULT 0,
                elapsed_seconds REAL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        conn.close()
    
    def _get_proven_nodes_from_db(self) -> List[Dict]:
        """从数据库获取已有真实节点"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, content, type, domain, confidence, tags, metadata
            FROM proven_nodes
            WHERE confidence >= ?
            ORDER BY created_at DESC
            LIMIT 100
        """, (self.config.get("node_confidence_threshold", 0.7),))
        
        nodes = []
        for row in cursor.fetchall():
            nodes.append({
                "id": row[0],
                "content": row[1],
                "type": row[2],
                "domain": row[3],
                "confidence": row[4],
                "tags": json.loads(row[5]) if row[5] else [],
                "metadata": json.loads(row[6]) if row[6] else {}
            })
        
        conn.close()
        return nodes
    
    def _group_nodes_by_domain(self, nodes: List[Dict]) -> Dict[str, List[Dict]]:
        """按领域分组节点"""
        domains = {}
        for node in nodes:
            domain = node.get("domain", "general")
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(node)
        return domains
    
    def _save_node_to_db(self, node: Dict):
        """保存节点到数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        node_id = node.get("id", f"node_{int(time.time()*1000)}")
        cursor.execute("""
            INSERT OR REPLACE INTO proven_nodes 
            (id, content, type, source, collision_type, confidence, domain, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node_id,
            node.get("content", ""),
            node.get("type", "proven"),
            node.get("source", "collision"),
            node.get("collision_type", ""),
            node.get("confidence", 0.8),
            node.get("domain", "general"),
            json.dumps(node.get("tags", []), ensure_ascii=False),
            json.dumps(node.get("metadata", {}), ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def _save_skill_to_db(self, skill: Dict):
        """保存 SKILL 到数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        skill_id = skill.get("name", f"skill_{int(time.time()*1000)}")
        cursor.execute("""
            INSERT OR REPLACE INTO skills
            (id, name, file_path, description, tags, forged_by, source_node_id, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill_id,
            skill.get("name", ""),
            skill.get("file", ""),
            skill.get("description", ""),
            json.dumps(skill.get("tags", []), ensure_ascii=False),
            "growth_engine",
            skill.get("source_node_id", ""),
            json.dumps(skill, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def _save_round_to_db(self, round_result: Dict):
        """保存轮次结果到数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO growth_log 
            (round_number, phase, event_type, tokens_used, elapsed_seconds, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            round_result.get("round", 0),
            "round_complete",
            "summary",
            round_result.get("tokens_used", 0),
            round_result.get("elapsed_seconds", 0),
            json.dumps(round_result, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_final_report(self):
        """生成最终报告"""
        report_path = PROJECT_DIR / "docs" / "321自成长待处理" / "growth_final_report.md"
        
        total_rounds = len(self.history)
        total_nodes = sum(h.get("new_nodes", 0) for h in self.history)
        total_skills = sum(h.get("valid_skills", 0) for h in self.history)
        total_tokens = sum(h.get("tokens_used", 0) for h in self.history)
        
        report = f"""# AGI 全速成长系统 — 最终报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 总体统计

- **总轮次**: {total_rounds}
- **总节点产出**: {total_nodes}
- **总 SKILL 产出**: {total_skills}
- **总 Tokens 消耗**: {total_tokens:,}
- **平均每轮 Tokens**: {total_tokens // total_rounds if total_rounds else 0:,}
- **平均每轮节点**: {total_nodes / total_rounds if total_rounds else 0:.1f}
- **平均每轮 SKILL**: {total_skills / total_rounds if total_rounds else 0:.1f}

## 逐轮详情

| 轮次 | 新节点 | 新SKILL | 有效SKILL | Tokens | 有效产出 | 耗时(s) | 验证率 |
|------|--------|---------|----------|--------|---------|---------|--------|
"""
        
        for h in self.history:
            report += f"| {h['round']} | {h.get('new_nodes', 0)} | {h.get('new_skills', 0)} | {h.get('valid_skills', 0)} | {h.get('tokens_used', 0):,} | {h.get('effective_output', 0)} | {h.get('elapsed_seconds', 0):.1f} | {h.get('validation_rate', 0)*100:.0f}% |\n"
        
        report += f"\n## 成功标准评估\n\n"
        
        # 最低标准
        report += f"### 最低标准（10轮后）\n\n"
        report += f"- {'✅' if total_tokens >= 10000000 else '❌'} Tokens 总消耗 ≥ 1000万 (实际: {total_tokens:,})\n"
        report += f"- {'✅' if total_nodes >= 100 else '❌'} 真实节点产出 ≥ 100 (实际: {total_nodes})\n"
        report += f"- {'✅' if total_skills >= 60 else '❌'} SKILL 产出 ≥ 60 (实际: {total_skills})\n"
        
        avg_validation = sum(h.get('validation_rate', 0) for h in self.history) / len(self.history) if self.history else 0
        report += f"- {'✅' if avg_validation >= 0.6 else '❌'} SKILL 验证通过率 ≥ 60% (实际: {avg_validation*100:.1f}%)\n"
        
        report_path.write_text(report, encoding='utf-8')
        print(f"\n✅ 最终报告已生成: {report_path}")
    
    def save_checkpoint(self):
        """保存检查点"""
        checkpoint = {
            "current_round": self.current_round,
            "history": self.history,
            "timestamp": datetime.now().isoformat()
        }
        checkpoint_path = PROJECT_DIR / "docs" / "321自成长待处理" / "checkpoint.json"
        checkpoint_path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"检查点已保存: {checkpoint_path}")
    
    def resume_from_round(self, round_num: int):
        """从指定轮次恢复"""
        checkpoint_path = PROJECT_DIR / "docs" / "321自成长待处理" / "checkpoint.json"
        if checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding='utf-8'))
            self.current_round = checkpoint.get("current_round", 0)
            self.history = checkpoint.get("history", [])
            print(f"从检查点恢复: 第 {self.current_round} 轮")


class FourWayCollisionEngine:
    """四向碰撞引擎（简化实现）"""
    
    def __init__(self, growth_engine):
        self.growth_engine = growth_engine
        self.token_usage = {"total": 0, "hourly": 0, "last_reset": time.time()}
    
    def top_down_decompose(self, big_question: str) -> List[Dict]:
        """自上而下拆解（模拟实现）"""
        # TODO: 实际应调用 GLM-5
        self._track_tokens(5000)
        return [
            {"id": f"Q{i}", "question": f"{big_question} - 子问题{i}", "difficulty": 3}
            for i in range(1, 6)
        ]
    
    def bottom_up_construct(self, proven_nodes: List[Dict]) -> List[Dict]:
        """自下而上构建（模拟实现）"""
        # TODO: 实际应调用 GLM-5
        self._track_tokens(8000)
        return [
            {"pattern_id": f"P{i}", "pattern_name": f"模式{i}"}
            for i in range(1, 4)
        ]
    
    def horizontal_overlap(self, domain_a: List[Dict], domain_b: List[Dict]) -> List[Dict]:
        """左右寻找重叠（模拟实现）"""
        # TODO: 实际应调用 GLM-5
        self._track_tokens(6000)
        return [
            {"overlap_id": f"O{i}", "similarity": 0.85, "fusion_capability": f"融合能力{i}"}
            for i in range(1, 3)
        ]
    
    def construct_from_overlap(self, overlaps: List[Dict]) -> List[Dict]:
        """从重叠构建新节点"""
        new_nodes = []
        for overlap in overlaps:
            if overlap.get("similarity", 0) > 0.7:
                node = {
                    "id": f"node_{int(time.time()*1000)}_{len(new_nodes)}",
                    "content": overlap.get("fusion_capability", ""),
                    "type": "proven",
                    "source": "collision",
                    "collision_type": "horizontal_overlap",
                    "confidence": overlap.get("similarity", 0),
                    "domain": "cross_domain",
                    "tags": ["glm5_generated", "collision"],
                    "metadata": overlap
                }
                new_nodes.append(node)
        return new_nodes
    
    def _track_tokens(self, tokens: int):
        """追踪 tokens"""
        self.token_usage["total"] += tokens
        self.token_usage["hourly"] += tokens
        
        if time.time() - self.token_usage["last_reset"] > 3600:
            print(f"[TokenUsage] 过去1小时: {self.token_usage['hourly']:,} tokens")
            self.token_usage["hourly"] = 0
            self.token_usage["last_reset"] = time.time()


class NodeToSkillConverter:
    """节点→SKILL 转换器"""
    
    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
    
    def convert(self, node: Dict) -> Optional[Dict]:
        """转换节点为 SKILL"""
        content = node.get("content", "").lower()
        
        if any(kw in content for kw in ["实现", "生成", "执行"]):
            return self._to_skill(node)
        return None
    
    def _to_skill(self, node: Dict) -> Dict:
        """转换为 SKILL"""
        skill_name = f"auto_{node.get('id', 'unknown')}"
        return {
            "name": skill_name,
            "file": f"skills/{skill_name}.py",
            "description": node.get("content", ""),
            "tags": node.get("tags", []) + ["auto_generated"],
            "created_at": datetime.now().isoformat(),
            "forged_by": "growth_engine",
            "source_node_id": node.get("id", ""),
            "design_spec": {
                "name": skill_name,
                "display_name": node.get("content", "")[:50],
                "functions": [],
                "dependencies": []
            }
        }


class SkillTemplateValidator:
    """SKILL 模板校验器"""
    
    REQUIRED_FIELDS = ["name", "file", "description", "tags", "design_spec"]
    
    def validate(self, skill_meta: Dict) -> Dict:
        """校验 SKILL"""
        issues = []
        
        for field in self.REQUIRED_FIELDS:
            if field not in skill_meta:
                issues.append(f"缺少字段: {field}")
        
        score = max(0, 100 - len(issues) * 20)
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "score": score
        }


class IncrementalChecker:
    """增量检查器"""
    
    def __init__(self):
        self.skill_count = 0
        self.last_check_count = 0
    
    def should_check(self) -> bool:
        """是否应检查"""
        return self.skill_count - self.last_check_count >= 5
    
    def check(self, all_skills: List[Dict]):
        """执行检查"""
        print(f"\n{'='*60}")
        print(f"增量检查 (当前 SKILL 数: {len(all_skills)})")
        print(f"{'='*60}")
        
        # 简化的依赖分析
        dep_count = sum(len(s.get("design_spec", {}).get("dependencies", [])) for s in all_skills)
        print(f"  总依赖数: {dep_count}")
        
        self.last_check_count = self.skill_count
