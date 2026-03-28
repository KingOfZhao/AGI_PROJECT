"""
模块: auto_skill_context_window_pruner
描述: 实现AGI系统中的技能调用上下文窗口动态裁剪机制。
      模拟操作系统内存分页管理，仅加载相关技能的接口定义而非完整实现。
"""

import logging
import hashlib
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
MAX_CONTEXT_TOKENS = 4096  # 模拟上下文窗口大小限制
EMBEDDING_DIMENSION = 256  # 向量维度

@dataclass
class SkillSignature:
    """
    技能签名对象，表示技能的元数据和接口定义。
    
    属性:
        skill_id: 技能唯一标识符
        name: 技能名称
        interface: 技能接口定义 (输入输出格式)
        description: 技能功能描述
        keywords: 技能关键词列表
        token_count: 接口定义的token数量估算
        embedding: 技能的向量表示
    """
    skill_id: str
    name: str
    interface: Dict[str, Any]
    description: str
    keywords: List[str] = field(default_factory=list)
    token_count: int = 0
    embedding: List[float] = field(default_factory=lambda: [0.0]*EMBEDDING_DIMENSION)
    
    def __post_init__(self):
        """初始化后处理，计算token估算"""
        if not self.token_count:
            # 简单估算：每个字符约0.25个token
            total_chars = len(self.name) + len(self.description) + len(str(self.interface))
            self.token_count = max(50, int(total_chars * 0.25))  # 最小50 tokens


class SkillContextManager:
    """
    技能上下文管理器，实现动态裁剪和加载机制。
    """
    
    def __init__(self):
        """初始化技能上下文管理器"""
        self.skill_registry: Dict[str, SkillSignature] = {}
        self.active_skills: Set[str] = set()
        self.current_context_usage = 0
        self._initialize_mock_skills()
        
    def _initialize_mock_skills(self) -> None:
        """初始化模拟技能库"""
        skill_templates = [
            {
                "name": "weather_forecast",
                "description": "获取指定城市的天气预报",
                "interface": {"input": {"city": "str"}, "output": {"forecast": "dict"}},
                "keywords": ["天气", "预报", "气象"]
            },
            {
                "name": "stock_analysis",
                "description": "分析股票市场趋势",
                "interface": {"input": {"symbol": "str"}, "output": {"analysis": "dict"}},
                "keywords": ["股票", "金融", "投资"]
            },
            {
                "name": "recipe_generator",
                "description": "根据食材生成食谱",
                "interface": {"input": {"ingredients": "list"}, "output": {"recipe": "str"}},
                "keywords": ["食谱", "烹饪", "食材"]
            },
            {
                "name": "code_generator",
                "description": "生成Python代码片段",
                "interface": {"input": {"prompt": "str"}, "output": {"code": "str"}},
                "keywords": ["编程", "代码", "开发"]
            },
            {
                "name": "language_translator",
                "description": "多语言翻译工具",
                "interface": {"input": {"text": "str", "target_lang": "str"}, "output": {"translation": "str"}},
                "keywords": ["翻译", "语言", "文本"]
            }
        ]
        
        for i, template in enumerate(skill_templates):
            skill_id = f"skill_{hashlib.md5(template['name'].encode()).hexdigest()[:8]}"
            # 生成模拟向量 (实际应用中应使用真实嵌入模型)
            embedding = [0.1 * (i+1)] * EMBEDDING_DIMENSION
            
            self.skill_registry[skill_id] = SkillSignature(
                skill_id=skill_id,
                name=template["name"],
                interface=template["interface"],
                description=template["description"],
                keywords=template["keywords"],
                embedding=embedding
            )
            
        logger.info(f"初始化完成，已加载 {len(self.skill_registry)} 个技能签名")

    def _calculate_relevance_score(self, skill: SkillSignature, query: str) -> float:
        """
        计算技能与查询的相关性得分 (辅助函数)。
        
        参数:
            skill: 技能签名对象
            query: 用户查询文本
            
        返回:
            相关性得分 (0.0-1.0)
        """
        score = 0.0
        query_lower = query.lower()
        
        # 关键词匹配
        for kw in skill.keywords:
            if kw in query_lower:
                score += 0.2
                
        # 名称匹配
        if skill.name.split('_')[0] in query_lower:
            score += 0.3
            
        # 模拟向量相似度 (实际应用中应使用余弦相似度)
        if skill.embedding:
            score += 0.5 * (skill.embedding[0] / 10.0)  # 简化计算
            
        return min(score, 1.0)  # 确保得分在0-1之间

    def load_skill_interface(self, skill_id: str) -> bool:
        """
        加载技能接口定义到上下文 (核心函数1)。
        
        参数:
            skill_id: 要加载的技能ID
            
        返回:
            bool: 是否成功加载
            
        异常:
            ValueError: 如果技能ID无效
        """
        if skill_id not in self.skill_registry:
            logger.error(f"无效的技能ID: {skill_id}")
            raise ValueError(f"技能 {skill_id} 不存在")
            
        if skill_id in self.active_skills:
            logger.debug(f"技能 {skill_id} 已在上下文中")
            return True
            
        skill = self.skill_registry[skill_id]
        
        # 检查上下文窗口剩余空间
        remaining = MAX_CONTEXT_TOKENS - self.current_context_usage
        if skill.token_count > remaining:
            logger.warning(f"上下文窗口不足 (需要 {skill.token_count}, 剩余 {remaining})")
            return False
            
        # 模拟加载接口定义
        self.active_skills.add(skill_id)
        self.current_context_usage += skill.token_count
        logger.info(f"已加载技能接口: {skill.name} (使用 {skill.token_count} tokens)")
        return True

    def dynamic_skill_pruning(self, query: str, top_k: int = 3) -> List[str]:
        """
        动态裁剪并加载最相关的技能 (核心函数2)。
        
        参数:
            query: 用户查询文本
            top_k: 要加载的技能数量
            
        返回:
            List[str]: 加载成功的技能ID列表
            
        异常:
            RuntimeError: 如果没有技能可用
        """
        if not self.skill_registry:
            logger.error("技能注册表为空")
            raise RuntimeError("没有可用的技能")
            
        # 计算所有技能的相关性得分
        scored_skills = []
        for skill_id, skill in self.skill_registry.items():
            score = self._calculate_relevance_score(skill, query)
            scored_skills.append((skill_id, score))
            
        # 按得分排序并选择top_k
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        selected_skills = scored_skills[:top_k]
        
        # 尝试加载选中的技能
        loaded_skills = []
        for skill_id, score in selected_skills:
            if self.load_skill_interface(skill_id):
                loaded_skills.append(skill_id)
            else:
                logger.warning(f"无法加载技能 {skill_id} (得分: {score:.2f})")
                
        if not loaded_skills:
            logger.error("无法加载任何相关技能")
            raise RuntimeError("技能加载失败 - 可能是上下文窗口已满")
            
        logger.info(f"动态裁剪完成，已加载 {len(loaded_skills)}/{top_k} 个相关技能")
        return loaded_skills

    def get_active_context(self) -> Dict[str, Any]:
        """
        获取当前活跃的技能上下文 (辅助函数)。
        
        返回:
            Dict: 包含活跃技能接口和上下文使用情况的字典
        """
        return {
            "active_skills": [
                {
                    "id": skill_id,
                    "interface": self.skill_registry[skill_id].interface,
                    "name": self.skill_registry[skill_id].name
                }
                for skill_id in self.active_skills
            ],
            "context_usage": {
                "total": MAX_CONTEXT_TOKENS,
                "used": self.current_context_usage,
                "available": MAX_CONTEXT_TOKENS - self.current_context_usage
            }
        }

    def clear_context(self) -> None:
        """清空当前上下文"""
        self.active_skills.clear()
        self.current_context_usage = 0
        logger.info("上下文已清空")


# 使用示例
if __name__ == "__main__":
    try:
        # 初始化技能管理器
        manager = SkillContextManager()
        
        # 模拟用户查询
        user_query = "帮我查一下北京明天的天气预报"
        
        # 动态裁剪技能
        print(f"\n处理查询: '{user_query}'")
        selected_skills = manager.dynamic_skill_pruning(user_query, top_k=2)
        
        # 查看加载的技能
        context = manager.get_active_context()
        print("\n当前活跃技能:")
        for skill in context["active_skills"]:
            print(f"- {skill['name']}: {skill['interface']}")
            
        print(f"\n上下文使用情况: {context['context_usage']['used']}/{context['context_usage']['total']} tokens")
        
        # 清空上下文
        manager.clear_context()
        
    except Exception as e:
        logger.error(f"发生错误: {str(e)}", exc_info=True)