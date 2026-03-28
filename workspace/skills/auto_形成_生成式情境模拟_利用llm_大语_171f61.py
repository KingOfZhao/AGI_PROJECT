"""
生成式情境模拟模块

本模块利用大语言模型(LLM)构建高保真的"教育平行宇宙"，创建复杂的虚拟社会或科学困境场景。
学生通过决策参与历史或科学进程，AI根据学生决策实时演化剧情走向，培养跨学科问题解决能力。

典型用例:
    >>> simulator = GenerativeScenarioSimulator(api_key="your_api_key")
    >>> scenario = simulator.create_scenario(
    ...     theme="ancient_civilization",
    ...     complexity=0.8,
    ...     conflict_level="high"
    ... )
    >>> next_event = simulator.process_user_decision(
    ...     scenario_id=scenario.id,
    ...     decision="I negotiate with the neighboring city-state for grain"
    ... )
"""

import os
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Literal
from datetime import datetime
import requests

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scenario_simulation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 类型别名
ScenarioID = str
ConflictLevel = Literal["low", "medium", "high", "extreme"]
Complexity = float  # 0.0-1.0之间
DecisionText = str


@dataclass
class ScenarioEvent:
    """表示情境中的一个事件节点"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    possible_actions: List[str] = field(default_factory=list)
    historical_context: Dict[str, str] = field(default_factory=dict)
    scientific_principles: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Scenario:
    """表示一个完整的生成式情境模拟"""
    id: ScenarioID
    theme: str
    complexity: Complexity
    conflict_level: ConflictLevel
    events: List[ScenarioEvent] = field(default_factory=list)
    user_decisions: List[Dict[str, Union[str, ScenarioEvent]]] = field(default_factory=list)
    current_state: Dict[str, Union[str, float, Dict]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class GenerativeScenarioSimulator:
    """生成式情境模拟器
    
    利用大语言模型创建和演化复杂的教育情境，根据用户决策实时调整剧情走向。
    
    属性:
        api_key (str): LLM API密钥
        base_url (str): LLM API基础URL
        scenarios (Dict[ScenarioID, Scenario]): 活跃的情境模拟
        max_history_length (int): 保留的决策历史最大长度
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """初始化生成式情境模拟器
        
        参数:
            api_key: LLM API密钥，如未提供则从环境变量LLM_API_KEY获取
            base_url: LLM API基础URL，如未提供则从环境变量LLM_BASE_URL获取
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.llm-provider.com/v1")
        self.scenarios: Dict[ScenarioID, Scenario] = {}
        self.max_history_length = 10
        
        if not self.api_key:
            logger.warning("No API key provided. Set LLM_API_KEY environment variable or pass api_key parameter.")
    
    def _validate_complexity(self, complexity: Complexity) -> None:
        """验证复杂度参数是否在有效范围内
        
        参数:
            complexity: 要验证的复杂度值
            
        异常:
            ValueError: 如果复杂度不在0.0-1.0范围内
        """
        if not 0.0 <= complexity <= 1.0:
            raise ValueError(f"Complexity must be between 0.0 and 1.0, got {complexity}")
    
    def _call_llm_api(self, prompt: str, max_tokens: int = 1000) -> str:
        """调用LLM API生成文本
        
        参数:
            prompt: 输入提示文本
            max_tokens: 生成的最大token数量
            
        返回:
            生成的文本内容
            
        异常:
            RuntimeError: 如果API调用失败
        """
        if not self.api_key:
            raise RuntimeError("No API key available for LLM API calls")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("choices", [{}])[0].get("text", "")
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM API call failed: {str(e)}")
            raise RuntimeError(f"Failed to call LLM API: {str(e)}")
    
    def _generate_scenario_prompt(self, theme: str, complexity: Complexity, 
                                conflict_level: ConflictLevel) -> str:
        """生成创建情境的提示文本
        
        参数:
            theme: 情境主题
            complexity: 情境复杂度
            conflict_level: 冲突级别
            
        返回:
            生成的提示文本
        """
        return f"""
        Create an immersive historical/scientific scenario with these parameters:
        - Theme: {theme}
        - Complexity (0.0-1.0): {complexity}
        - Conflict Level: {conflict_level}
        
        The scenario should:
        1. Present a complex, conflict-filled situation requiring cross-disciplinary knowledge
        2. Have no clear "right" answers, forcing nuanced decision-making
        3. Include rich historical or scientific context
        4. Be open-ended enough to evolve based on user decisions
        
        Provide the scenario in JSON format with these fields:
        - "description": detailed scenario description
        - "possible_actions": list of 3-5 initial actions the user can take
        - "historical_context": relevant historical or scientific background
        - "scientific_principles": key principles at play
        """
    
    def create_scenario(self, theme: str, complexity: Complexity = 0.7, 
                       conflict_level: ConflictLevel = "high") -> Scenario:
        """创建新的生成式情境模拟
        
        参数:
            theme: 情境主题 (如 "ancient_civilization", "climate_change", "space_colonization")
            complexity: 情境复杂度 (0.0-1.0)
            conflict_level: 冲突级别 ("low", "medium", "high", "extreme")
            
        返回:
            创建的Scenario对象
            
        异常:
            ValueError: 如果参数无效
            RuntimeError: 如果场景创建失败
        """
        try:
            self._validate_complexity(complexity)
            
            scenario_id = str(uuid.uuid4())
            prompt = self._generate_scenario_prompt(theme, complexity, conflict_level)
            
            # 在实际实现中，这里会调用LLM API
            # 为了示例，我们使用模拟数据
            llm_response = self._call_llm_api(prompt) if self.api_key else self._mock_llm_response(theme)
            
            try:
                scenario_data = json.loads(llm_response)
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response as JSON, using fallback")
                scenario_data = self._get_fallback_scenario(theme)
            
            initial_event = ScenarioEvent(
                description=scenario_data.get("description", ""),
                possible_actions=scenario_data.get("possible_actions", []),
                historical_context=scenario_data.get("historical_context", {}),
                scientific_principles=scenario_data.get("scientific_principles", [])
            )
            
            scenario = Scenario(
                id=scenario_id,
                theme=theme,
                complexity=complexity,
                conflict_level=conflict_level,
                events=[initial_event],
                current_state={
                    "progress": 0.0,
                    "metrics": {
                        "political_stability": 0.5,
                        "resource_availability": 0.5,
                        "public_support": 0.5
                    }
                }
            )
            
            self.scenarios[scenario_id] = scenario
            logger.info(f"Created new scenario with ID: {scenario_id}")
            
            return scenario
            
        except Exception as e:
            logger.error(f"Failed to create scenario: {str(e)}")
            raise RuntimeError(f"Scenario creation failed: {str(e)}")
    
    def process_user_decision(self, scenario_id: ScenarioID, decision: DecisionText) -> ScenarioEvent:
        """处理用户决策并生成下一个事件
        
        参数:
            scenario_id: 情境ID
            decision: 用户的决策文本
            
        返回:
            生成的下一个ScenarioEvent
            
        异常:
            ValueError: 如果情境不存在或决策无效
            RuntimeError: 如果事件生成失败
        """
        try:
            if scenario_id not in self.scenarios:
                raise ValueError(f"Scenario with ID {scenario_id} not found")
            
            scenario = self.scenarios[scenario_id]
            current_event = scenario.events[-1]
            
            # 记录用户决策
            decision_record = {
                "decision": decision,
                "event": current_event,
                "timestamp": datetime.now().isoformat()
            }
            scenario.user_decisions.append(decision_record)
            
            # 限制历史记录长度
            if len(scenario.user_decisions) > self.max_history_length:
                scenario.user_decisions.pop(0)
            
            # 生成下一个事件的提示
            prompt = self._generate_next_event_prompt(scenario, decision)
            
            # 调用LLM API生成下一个事件
            llm_response = self._call_llm_api(prompt) if self.api_key else self._mock_next_event(scenario, decision)
            
            try:
                next_event_data = json.loads(llm_response)
            except json.JSONDecodeError:
                logger.warning("Failed to parse next event response as JSON, using fallback")
                next_event_data = self._get_fallback_next_event(decision)
            
            # 更新情境状态
            self._update_scenario_state(scenario, decision, next_event_data)
            
            # 创建新事件
            next_event = ScenarioEvent(
                description=next_event_data.get("description", ""),
                possible_actions=next_event_data.get("possible_actions", []),
                historical_context=next_event_data.get("historical_context", {}),
                scientific_principles=next_event_data.get("scientific_principles", [])
            )
            
            scenario.events.append(next_event)
            scenario.current_state["progress"] = min(1.0, scenario.current_state["progress"] + 0.1)
            
            logger.info(f"Processed decision for scenario {scenario_id}, generated new event")
            
            return next_event
            
        except Exception as e:
            logger.error(f"Failed to process user decision: {str(e)}")
            raise RuntimeError(f"Decision processing failed: {str(e)}")
    
    def _generate_next_event_prompt(self, scenario: Scenario, decision: DecisionText) -> str:
        """生成下一个事件的提示文本
        
        参数:
            scenario: 当前情境对象
            decision: 用户的决策文本
            
        返回:
            生成的提示文本
        """
        history = "\n".join(
            f"- {d['decision']}" for d in scenario.user_decisions[-3:]
        )
        
        return f"""
        Based on the current scenario state and user decision, generate the next event:
        
        Current Scenario: {scenario.theme} (Complexity: {scenario.complexity}, Conflict: {scenario.conflict_level})
        Current State: {json.dumps(scenario.current_state, indent=2)}
        
        Recent Decisions:
        {history}
        
        User's Latest Decision: "{decision}"
        
        Generate the next event that:
        1. Realistically evolves from the user's decision
        2. Introduces new challenges or complications
        3. Requires the user to apply knowledge from multiple disciplines
        4. Maintains the historical/scientific authenticity
        
        Provide the response in JSON format with these fields:
        - "description": what happens next
        - "possible_actions": new set of actions the user can take
        - "historical_context": relevant historical/scientific background
        - "scientific_principles": key principles now at play
        """
    
    def _update_scenario_state(self, scenario: Scenario, decision: DecisionText, 
                             next_event_data: Dict) -> None:
        """更新情境状态基于用户决策
        
        参数:
            scenario: 要更新的情境对象
            decision: 用户的决策文本
            next_event_data: 下一个事件的数据
        """
        # 简单的状态更新逻辑 - 实际实现会更复杂
        metrics = scenario.current_state["metrics"]
        
        # 根据决策内容调整指标
        if "negotiate" in decision.lower():
            metrics["political_stability"] = min(1.0, metrics["political_stability"] + 0.1)
        elif "attack" in decision.lower():
            metrics["political_stability"] = max(0.0, metrics["political_stability"] - 0.2)
            metrics["public_support"] = max(0.0, metrics["public_support"] - 0.1)
        
        # 确保指标在0.0-1.0范围内
        for key in metrics:
            metrics[key] = max(0.0, min(1.0, metrics[key]))
    
    def _mock_llm_response(self, theme: str) -> str:
        """模拟LLM响应用于测试/演示
        
        参数:
            theme: 情境主题
            
        返回:
            模拟的JSON响应字符串
        """
        mock_responses = {
            "ancient_civilization": json.dumps({
                "description": "You are the governor of a prosperous city-state in 200 AD, facing a severe drought while neighboring kingdoms threaten war. Your engineers have proposed an ambitious aqueduct project, but it requires resources your city lacks.",
                "possible_actions": [
                    "Negotiate with neighboring kingdoms for resources",
                    "Implement strict water rationing",
                    "Divert military funds to the aqueduct project",
                    "Seek advice from religious leaders"
                ],
                "historical_context": {
                    "period": "Roman Empire era",
                    "technological_level": "Advanced engineering",
                    "social_structure": "City-state with democratic elements"
                },
                "scientific_principles": [
                    "Hydrology",
                    "Civil engineering",
                    "Resource management",
                    "Diplomacy"
                ]
            }),
            "climate_change": json.dumps({
                "description": "You are the mayor of a coastal city in 2050, facing rising sea levels and increasing extreme weather events. A powerful corporation offers to build flood defenses, but demands control over city resources.",
                "possible_actions": [
                    "Accept the corporation's offer",
                    "Develop community-based solutions",
                    "Implement managed retreat from coastal areas",
                    "Seek federal government intervention"
                ],
                "historical_context": {
                    "period": "Mid-21st century",
                    "technological_level": "Advanced climate modeling",
                    "social_structure": "Democratic city government"
                },
                "scientific_principles": [
                    "Climate science",
                    "Urban planning",
                    "Economics",
                    "Social equity"
                ]
            })
        }
        
        return mock_responses.get(theme, json.dumps({
            "description": f"A complex {theme} scenario with multiple challenges and no clear solutions.",
            "possible_actions": [
                "Analyze the situation carefully",
                "Consult with experts",
                "Implement a bold solution",
                "Wait for more information"
            ],
            "historical_context": {
                "period": "Contemporary",
                "technological_level": "Advanced",
                "social_structure": "Complex modern society"
            },
            "scientific_principles": [
                "Systems thinking",
                "Critical analysis",
                "Decision theory",
                "Risk assessment"
            ]
        }))
    
    def _mock_next_event(self, scenario: Scenario, decision: DecisionText) -> str:
        """模拟下一个事件的响应用于测试/演示
        
        参数:
            scenario: 当前情境对象
            decision: 用户的决策文本
            
        返回:
            模拟的JSON响应字符串
        """
        # 简单的逻辑根据决策内容生成不同响应
        if "negotiate" in decision.lower():
            return json.dumps({
                "description": "Your diplomatic efforts are partially successful. The neighboring kingdom agrees to provide some resources, but demands territorial concessions in return.",
                "possible_actions": [
                    "Accept the territorial demands",
                    "Counter with a different proposal",
                    "Seek alternative resource sources",
                    "Prepare for conflict"
                ],
                "historical_context": {
                    "period": "Continuing crisis",
                    "technological_level": "Same as before",
                    "social_structure": "Increased political tension"
                },
                "scientific_principles": [
                    "Diplomacy",
                    "Geopolitics",
                    "Resource economics"
                ]
            })
        else:
            return json.dumps({
                "description": "Your chosen approach has unexpected consequences. A new faction emerges in the city opposing your policies, and the original crisis intensifies.",
                "possible_actions": [
                    "Address the new faction's concerns",
                    "Double down on your current approach",
                    "Seek compromise",
                    "Implement emergency measures"
                ],
                "historical_context": {
                    "period": "Crisis intensification",
                    "technological_level": "Same as before",
                    "social_structure": "Emerging internal conflict"
                },
                "scientific_principles": [
                    "Social dynamics",
                    "Crisis management",
                    "Leadership under pressure"
                ]
            })
    
    def _get_fallback_scenario(self, theme: str) -> Dict:
        """获取后备情境数据当LLM响应无效时
        
        参数:
            theme: 情境主题
            
        返回:
            后备情境数据字典
        """
        return {
            "description": f"A challenging {theme} scenario requiring careful decision-making.",
            "possible_actions": [
                "Analyze the situation",
                "Consult with advisors",
                "Take immediate action",
                "Wait for developments"
            ],
            "historical_context": {
                "period": "Contemporary",
                "technological_level": "Advanced",
                "social_structure": "Complex society"
            },
            "scientific_principles": [
                "Critical thinking",
                "Problem solving",
                "Decision making"
            ]
        }
    
    def _get_fallback_next_event(self, decision: DecisionText) -> Dict:
        """获取后备下一个事件数据当LLM响应无效时
        
        参数:
            decision: 用户的决策文本
            
        返回:
            后备事件数据字典
        """
        return {
            "description": f"Your decision '{decision}' leads to new developments in the scenario.",
            "possible_actions": [
                "Continue with current approach",
                "Change strategy",
                "Seek more information",
                "Consult with others"
            ],
            "historical_context": {
                "period": "Ongoing scenario",
                "technological_level": "Same as before",
                "social_structure": "Evolving situation"
            },
            "scientific_principles": [
                "Adaptive management",
                "Continuous learning",
                "Iterative problem solving"
            ]
        }
    
    def get_scenario_state(self, scenario_id: ScenarioID) -> Dict:
        """获取情境的当前状态
        
        参数:
            scenario_id: 情境ID
            
        返回:
            包含情境状态的字典
            
        异常:
            ValueError: 如果情境不存在
        """
        if scenario_id not in self.scenarios:
            raise ValueError(f"Scenario with ID {scenario_id} not found")
        
        scenario = self.scenarios[scenario_id]
        return {
            "id": scenario.id,
            "theme": scenario.theme,
            "complexity": scenario.complexity,
            "conflict_level": scenario.conflict_level,
            "current_event": scenario.events[-1].description,
            "progress": scenario.current_state["progress"],
            "metrics": scenario.current_state["metrics"],
            "decision_count": len(scenario.user_decisions)
        }


# 使用示例
if __name__ == "__main__":
    try:
        # 初始化模拟器 (需要设置LLM_API_KEY环境变量或传入api_key参数)
        simulator = GenerativeScenarioSimulator()
        
        # 创建新情境
        print("Creating ancient civilization scenario...")
        scenario = simulator.create_scenario(
            theme="ancient_civilization",
            complexity=0.8,
            conflict_level="high"
        )
        
        print(f"Created scenario with ID: {scenario.id}")
        print(f"Initial event: {scenario.events[0].description}")
        print("Possible actions:")
        for i, action in enumerate(scenario.events[0].possible_actions, 1):
            print(f"{i}. {action}")
        
        # 处理用户决策
        print("\nProcessing user decision...")
        next_event = simulator.process_user_decision(
            scenario_id=scenario.id,
            decision="I negotiate with the neighboring kingdoms for resources"
        )
        
        print(f"Next event: {next_event.description}")
        print("New possible actions:")
        for i, action in enumerate(next_event.possible_actions, 1):
            print(f"{i}. {action}")
        
        # 获取情境状态
        print("\nCurrent scenario state:")
        state = simulator.get_scenario_state(scenario.id)
        print(json.dumps(state, indent=2))
        
    except Exception as e:
        print(f"Error in simulation: {str(e)}")