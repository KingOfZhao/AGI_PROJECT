"""
模块名称: auto_人在回路证伪闭环_模拟人机共生_ai_98fd3b
描述: 本模块实现了一个AGI架构下的【人在回路证伪闭环】系统。它模拟了人机共生的协作过程，
     其中AI生成初始策略（创业冷启动清单），模拟人类用户执行该策略，并在特定步骤
     注入"现实世界"的意外干扰（如API不存在、法律禁止）。系统必须检测这些失败，
     证伪原定计划中的假设，并即时重构剩余的可执行步骤。
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StepStatus(Enum):
    """步骤状态的枚举类"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED_PSEUDOSCIENCE = "failed_pseudoscientific"  # 伪节点：假设被证伪

@dataclass
class TaskStep:
    """代表清单中的每一个步骤"""
    step_id: int
    description: str
    status: StepStatus = StepStatus.PENDING
    error_reason: Optional[str] = None
    is_pseudo_node: bool = False  # 标记是否为伪节点

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class HumanInTheLoopPerturbation:
    """
    模拟人在回路中的随机干扰源。
    用于注入现实世界的摩擦力，测试AGI系统的鲁棒性。
    """
    
    # 定义在第3步和第7步将发生的具体"意外现实"
    PERTURBATION_MAP: Dict[int, Dict[str, str]] = {
        3: {
            "type": "API_FAILURE",
            "message": "错误: 目标API端点 'https://api.legacy-vendor.com/v1' 已永久下线 (404)。"
        },
        7: {
            "type": "LEGAL_CONSTRAINT",
            "message": "合规阻断: 该业务模式涉及数据跨境传输，违反最新的《数据安全法》第12条。"
        }
    }

    @staticmethod
    def inject_reality(step_id: int) -> Optional[Dict[str, str]]:
        """
        辅助函数：模拟人类用户执行时遇到的现实阻碍。
        
        Args:
            step_id: 当前执行的步骤ID
            
        Returns:
            如果该步骤被设定为失败点，返回包含错误信息的字典；否则返回None。
        """
        if step_id in HumanInTheLoopPerturbation.PERTURBATION_MAP:
            failure_info = HumanInTheLoopPerturbation.PERTURBATION_MAP[step_id]
            logger.warning(f"⚠️ [HUMAN LOOP] 检测到意外现实注入 @ Step {step_id}: {failure_info['message']}")
            return failure_info
        return None

class StartupPlannerAgent:
    """
    AI代理核心类。
    负责生成初始计划、接收反馈、证伪节点并修正路径。
    """
    
    def __init__(self):
        self.current_plan: List[TaskStep] = []
        self.pseudo_nodes: List[int] = []
    
    def generate_initial_plan(self) -> List[TaskStep]:
        """
        [核心函数 1]
        生成初始的10步创业冷启动清单。
        模拟AI基于内部模型生成的"完美"理论路径。
        """
        logger.info("🤖 [AI] 正在生成初始创业冷启动清单...")
        
        ideal_plan = [
            "市场痛点分析与假设构建",
            "组建核心创始团队",
            "调用第三方数据接口构建MVP原型",  # Step 3: 潜在伪节点 (API)
            "种子轮天使融资洽谈",
            "最小可行性产品(MVP)内测",
            "初期种子用户获取与留存",
            "启动全球化自动营销邮件群发",    # Step 7: 潜在伪节点 (Legal)
            "建立自动化客户服务机器人",
            "A轮增长指标冲刺",
            "IPO准备与上市辅导"
        ]
        
        self.current_plan = [
            TaskStep(step_id=i+1, description=desc) 
            for i, desc in enumerate(ideal_plan)
        ]
        
        logger.info(f"✅ [AI] 初始清单生成完毕，共 {len(self.current_plan)} 个步骤。")
        return self.current_plan

    def adapt_and_falsify(self, failed_step_id: int, error_context: Dict[str, str]) -> bool:
        """
        [核心函数 2]
        基于现实反馈进行证伪闭环。
        1. 标记失败点为伪节点。
        2. 重新评估剩余步骤的依赖关系。
        3. 生成修正后的路径。
        
        Args:
            failed_step_id: 失败的步骤ID
            error_context: 错误详情
            
        Returns:
            修正是否成功的布尔值
        """
        logger.info(f"🔄 [AI] 触发证伪闭环机制，正在处理 Step {failed_step_id} 的失败...")
        
        # 1. 标记伪节点
        for step in self.current_plan:
            if step.step_id == failed_step_id:
                step.status = StepStatus.FAILED_PSEUDOSCIENCE
                step.error_reason = error_context.get('message')
                step.is_pseudo_node = True
                self.pseudo_nodes.append(failed_step_id)
        
        # 2. 路径修正逻辑 (模拟)
        # 如果第3步失败，我们需要替换数据源策略
        # 如果第7步失败，我们需要更改市场策略
        corrected_steps = []
        
        for step in self.current_plan:
            if step.step_id <= failed_step_id:
                # 保留已执行或失败的步骤（作为历史记录）
                corrected_steps.append(step)
            else:
                # 对剩余步骤进行修正检查
                new_desc = step.description
                if failed_step_id == 3 and "数据" in step.description:
                    new_desc += " (修正: 使用爬虫自建数据集替代API)"
                    logger.info(f"    -> 修正后续步骤 {step.step_id}: 增加自建数据集策略")
                
                if failed_step_id == 7 and ("全球化" in step.description or "营销" in step.description):
                    new_desc = step.description.replace("全球化", "本地化合规").replace("邮件群发", "私域社群运营")
                    logger.info(f"    -> 修正后续步骤 {step.step_id}: 调整为合规运营策略")
                
                step.description = new_desc
                corrected_steps.append(step)
        
        self.current_plan = corrected_steps
        logger.info(f"✅ [AI] 路径重构完成。伪节点已标记: {self.pseudo_nodes}")
        return True

    def execute_simulation(self):
        """
        执行模拟闭环：AI生成 -> 人执行(模拟) -> 遇到意外 -> AI修正 -> 继续执行
        """
        print("\n" + "="*20 + " SIMULATION START " + "="*20)
        
        # 1. AI 生成
        plan = self.generate_initial_plan()
        self._print_plan(plan)
        
        # 2. 模拟执行循环
        for step in self.current_plan:
            logger.info(f"🚀 [EXEC] 尝试执行 Step {step.step_id}: {step.description}...")
            
            # 模拟人在回路中的干扰
            perturbation = HumanInTheLoopPerturbation.inject_reality(step.step_id)
            
            if perturbation:
                # 遇到阻碍，触发修正
                self.adapt_and_falsify(step.step_id, perturbation)
                # 在真实场景中，这里可能需要停止等待，但在模拟中我们直接更新状态并打印新计划
                print("\n" + "- "*20 + " PLAN UPDATED " + "- "*20)
                self._print_plan(self.current_plan)
                print("- " * 42 + "\n")
            else:
                # 执行成功
                step.status = StepStatus.SUCCESS
                logger.info(f"👍 [SUCCESS] Step {step.step_id} 验证通过。")
        
        print("\n" + "="*20 + " SIMULATION END " + "="*20)
        self._export_results()

    def _print_plan(self, plan: List[TaskStep]):
        """辅助函数：可视化打印当前计划"""
        for step in plan:
            status_icon = "✅" if step.status == StepStatus.SUCCESS else ("❌" if step.is_pseudo_node else "⏳")
            pseudo_tag = " [伪节点 - PSEUDO NODE]" if step.is_pseudo_node else ""
            print(f"{status_icon} Step {step.step_id}: {step.description}{pseudo_tag}")
            if step.error_reason:
                print(f"    └─ Reason: {step.error_reason}")

    def _export_results(self) -> None:
        """辅助函数：将最终结果导出为JSON格式，模拟数据持久化"""
        output_data = {
            "simulation_type": "Human-In-The-Loop Falsification",
            "final_plan_validity": "PARTIALLY_ADAPTED",
            "pseudo_nodes_identified": self.pseudo_nodes,
            "steps": [s.to_dict() for s in self.current_plan]
        }
        
        try:
            with open("simulation_report.json", "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            logger.info("📊 最终模拟报告已生成: simulation_report.json")
        except IOError as e:
            logger.error(f"文件写入失败: {e}")

def main():
    """
    使用示例：
    实例化 StartupPlannerAgent 并运行 execute_simulation 方法。
    这将自动完成生成、干扰注入、修正的完整闭环。
    """
    # 初始化 AI 代理
    agent = StartupPlannerAgent()
    
    # 运行人在回路证伪模拟
    agent.execute_simulation()

if __name__ == "__main__":
    main()