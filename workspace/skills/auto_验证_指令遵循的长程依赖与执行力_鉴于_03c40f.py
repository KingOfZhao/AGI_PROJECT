"""
模块名称: auto_验证_指令遵循的长程依赖与执行力_鉴于_03c40f
描述: 验证AGI系统在长链条任务中的指令遵循与长程依赖能力。
      通过模拟构建电商网站的20步流程，检测AI是否在第20步依然遵守第1步设定的约束条件。
作者: AGI System Core
版本: 1.0.0
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('long_term_dependency_validator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GlobalConstraint:
    """
    全局约束条件数据结构
    用于存储在第1步设定的、需要在整个长程任务中被遵守的约束。
    """
    db_version: str = "PostgreSQL-13.2"
    api_version: str = "v2"
    currency: str = "CNY"
    encoding: str = "UTF-8"
    secret_key_hash: str = field(default="", init=False)

    def __post_init__(self):
        # 模拟生成一个唯一的会话哈希，用于验证身份
        raw_key = f"{self.db_version}-{self.api_version}-{datetime.now().isoformat()}"
        self.secret_key_hash = hashlib.sha256(raw_key.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, str]:
        return {
            "db_version": self.db_version,
            "api_version": self.api_version,
            "currency": self.currency,
            "encoding": self.encoding,
            "session_hash": self.secret_key_hash
        }

@dataclass
class TaskStep:
    """任务步骤数据结构"""
    step_id: int
    description: str
    action_type: str  # e.g., 'db_config', 'api_call', 'data_process'
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class LongTermDependencyValidator:
    """
    核心验证类：用于执行长链条任务并验证约束条件。
    
    该类模拟一个复杂的工程任务（如搭建电商网站），包含超过15个步骤。
    它在执行过程中会故意引入干扰项，并在最后一步验证最初的约束是否被保留。
    """

    def __init__(self, initial_constraints: GlobalConstraint):
        """
        初始化验证器。
        
        Args:
            initial_constraints (GlobalConstraint): 任务开始时设定的全局约束。
        """
        self.constraints = initial_constraints
        self.execution_history: List[Dict[str, Any]] = []
        self.is_valid_state = True
        logger.info(f"Validator initialized with constraints: {self.constraints.to_dict()}")

    def _check_boundary(self, step_data: Dict[str, Any]) -> bool:
        """
        辅助函数：检查输入数据的边界和安全性。
        
        Args:
            step_data (Dict[str, Any]): 待检查的数据。
            
        Returns:
            bool: 数据是否合法。
        """
        if not isinstance(step_data, dict):
            logger.error("Invalid input type: expected dict.")
            return False
        
        required_keys = ["action", "params"]
        if not all(key in step_data for key in required_keys):
            logger.error(f"Missing required keys in step data: {required_keys}")
            return False
            
        if len(json.dumps(step_data)) > 1024 * 10:  # 限制数据大小
            logger.warning("Input data exceeds size limit.")
            return False
            
        return True

    def execute_step(self, step: TaskStep) -> Dict[str, Any]:
        """
        核心函数1: 执行单个任务步骤。
        
        模拟执行过程，并根据当前步骤ID模拟'遗忘'或'偏移'。
        包含完整的错误处理和状态记录。
        
        Args:
            step (TaskStep): 任务步骤对象。
            
        Returns:
            Dict[str, Any]: 执行结果。
        """
        logger.info(f"Executing Step {step.step_id}: {step.description}")
        
        # 数据验证
        if not self._check_boundary(step.payload):
            return {"status": "error", "message": "Invalid payload"}
        
        result = {
            "step_id": step.step_id,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "check_passed": True
        }

        # 模拟长程依赖检查：在特定步骤验证关键约束
        try:
            if step.action_type == "db_config":
                # 验证数据库版本约束
                used_db = step.payload.get("db_type", "Unknown")
                if used_db != self.constraints.db_version:
                    logger.error(f"Constraint Violation at Step {step.step_id}: Expected DB {self.constraints.db_version}, got {used_db}")
                    result["check_passed"] = False
                    self.is_valid_state = False
                    
            elif step.action_type == "payment_setup":
                # 验证货币单位约束
                used_currency = step.payload.get("currency", "USD")
                if used_currency != self.constraints.currency:
                    logger.error(f"Constraint Violation at Step {step.step_id}: Expected Currency {self.constraints.currency}, got {used_currency}")
                    result["check_passed"] = False
                    self.is_valid_state = False

            # 模拟正常的业务逻辑处理
            processed_data = self._mock_process_logic(step.payload)
            result["output"] = processed_data

        except Exception as e:
            logger.exception(f"Exception during step {step.step_id}")
            result["status"] = "fail"
            result["error"] = str(e)
        
        self.execution_history.append(result)
        return result

    def validate_final_state(self) -> Tuple[bool, str]:
        """
        核心函数2: 验证最终状态与长程依赖完整性。
        
        检查整个执行历史，确认是否有任何步骤违反了初始约束，
        以及最终状态是否包含初始设定的关键哈希值。
        
        Returns:
            Tuple[bool, str]: (是否验证通过, 详细报告)
        """
        logger.info("Initiating Final State Validation...")
        
        if not self.is_valid_state:
            return False, "Validation Failed: Constraints were violated during intermediate steps."
        
        if len(self.execution_history) < 15:
            return False, f"Validation Failed: Insufficient step count ({len(self.execution_history)}/15). Long-term dependency not tested."
            
        # 检查是否包含初始会话哈希（模拟记忆保持）
        # 在实际场景中，这里会检查最终的配置文件或代码输出
        last_step = self.execution_history[-1]
        if "output" in last_step:
             # 假设最终输出应该包含初始约束的指纹
             final_fingerprint = last_step["output"].get("session_fingerprint")
             if final_fingerprint != self.constraints.secret_key_hash:
                 return False, "Validation Failed: Lost context of initial session fingerprint in final step."
        
        return True, "Validation Successful: All long-term constraints maintained."

    def _mock_process_logic(self, data: Dict) -> Dict:
        """
        辅助函数: 模拟数据处理逻辑。
        """
        return {
            "processed": True,
            "input_keys": list(data.keys()),
            "session_fingerprint": self.constraints.secret_key_hash # 保持上下文传递
        }

def run_e_commerce_simulation(scenario: str = "standard") -> None:
    """
    使用示例：模拟一个'从零搭建电商网站'的20步流程。
    
    Args:
        scenario (str): 'standard' (正确遵循) 或 'drift' (模拟遗忘)。
    """
    print(f"\n--- Starting Simulation: {scenario} ---")
    
    # 1. 设定初始约束 (Step 0)
    constraints = GlobalConstraint(db_version="PostgreSQL-13.2", currency="CNY")
    validator = LongTermDependencyValidator(constraints)
    
    # 定义长链条任务步骤
    tasks = [
        TaskStep(1, "Initialize Project", "setup", {"path": "/var/www/shop"}),
        TaskStep(2, "Setup Database Schema", "db_config", {"db_type": "PostgreSQL-13.2"}),
        # ... 省略中间步骤以节省空间，实际逻辑会自动计数 ...
        TaskStep(15, "Configure Payment Gateway", "payment_setup", {"currency": "CNY" if scenario == "standard" else "USD"}), # 模拟在第15步可能的偏差
        TaskStep(20, "Final Deployment Check", "deploy", {"target": "production"})
    ]
    
    # 填充到20步的模拟
    current_step_id = 3
    while len(tasks) < 19:
        tasks.insert(current_step_id - 1, TaskStep(current_step_id, f"Intermediate Logic {current_step_id}", "logic", {"data": "dummy"}))
        current_step_id += 1

    # 执行任务
    for task in tasks:
        validator.execute_step(task)

    # 最终验证
    is_success, report = validator.validate_final_state()
    
    print(f"Simulation Result: {'SUCCESS' if is_success else 'FAILED'}")
    print(f"Report: {report}")
    print("-------------------------------------------")

if __name__ == "__main__":
    # 运行正常场景
    run_e_commerce_simulation(scenario="standard")
    
    # 运行偏差场景（模拟遗忘第1步的货币约束）
    run_e_commerce_simulation(scenario="drift")