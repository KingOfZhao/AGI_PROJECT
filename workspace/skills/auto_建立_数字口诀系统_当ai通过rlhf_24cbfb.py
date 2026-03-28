"""
数字口诀自动生成系统 (Digital Mnemonic System)

该模块旨在实现人机共生与知识传承。当AI通过RLHF或对抗训练掌握高难度逻辑后，
系统不仅保存权重，还自动生成“人类可读的隐喻性口诀”，帮助人类开发者快速理解
复杂的AI决策逻辑。

核心功能:
1. 监听AI的学习事件（如高奖励的Bug修复）。
2. 基于LLM模拟生成隐喻性口诀。
3. 将口诀与原始逻辑关联存储，形成“数字口诀库”。

输入格式:
    LearningEvent (Dict): 包含 task_id, description, logic_trace, reward_score
输出格式:
    MnemonicRecord (DataClass): 包含 mnemonic_id, content, metaphor_type, timestamp
"""

import logging
import json
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
MIN_REWARD_THRESHOLD = 0.85  # 只有奖励高于此值的逻辑才会生成口诀
STORAGE_DIR = Path("./mnemonic_knowledge_base")
STORAGE_FILE = STORAGE_DIR / "mnemonics.json"


class MnemonicGenerationError(Exception):
    """口诀生成过程中的自定义异常"""
    pass


@dataclass
class LearningEvent:
    """表示AI的一次学习事件"""
    task_id: str
    description: str
    logic_trace: str  # AI的推理过程或代码片段
    reward_score: float  # RLHF奖励分数 (0.0 - 1.0)

    def __post_init__(self):
        if not 0.0 <= self.reward_score <= 1.0:
            raise ValueError("reward_score must be between 0.0 and 1.0")


@dataclass
class MnemonicRecord:
    """表示生成的口诀记录"""
    mnemonic_id: str
    task_id: str
    content: str  # 口诀内容
    explanation: str  # 口诀对应的逻辑解释
    metaphor_type: str  # 隐喻类型 (如: "nature", "craft", "daily_life")
    created_at: str


def validate_learning_event(event: LearningEvent) -> bool:
    """
    辅助函数：验证学习事件是否符合生成口诀的标准。

    Args:
        event: LearningEvent 对象

    Returns:
        bool: 如果验证通过返回 True

    Raises:
        ValueError: 如果数据无效
    """
    if not isinstance(event, LearningEvent):
        raise ValueError("Input must be a LearningEvent instance.")

    if not event.description or not event.logic_trace:
        raise ValueError("Description and logic_trace cannot be empty.")

    if event.reward_score < MIN_REWARD_THRESHOLD:
        logger.info(
            f"Task {event.task_id} reward ({event.reward_score}) is below threshold "
            f"({MIN_REWARD_THRESHOLD}). Skipping mnemonic generation."
        )
        return False

    return True


def _simulate_llm_generation(logic_trace: str, description: str) -> Dict[str, str]:
    """
    核心辅助函数：模拟LLM根据逻辑生成隐喻口诀的过程。
    在实际生产环境中，这里会调用GPT-4或其他大模型的API。

    Args:
        logic_trace: AI的推理逻辑
        description: 任务描述

    Returns:
        Dict: 包含 'content' (口诀) 和 'metaphor_type' 的字典
    """
    # 这里使用规则模拟LLM的创造性生成
    trace_lower = logic_trace.lower()
    
    if "deadlock" in trace_lower or "lock" in trace_lower:
        return {
            "content": "若遇死锁，如解绳结，先松后紧，莫用蛮力。",
            "metaphor_type": "craft",
            "explanation": "处理死锁时，应先释放部分资源（松），再尝试获取锁（紧），避免硬等待导致系统僵死。"
        }
    elif "memory leak" in trace_lower or "leak" in trace_lower:
        return {
            "content": "如堵水渠，寻其源头，疏通为上，切勿只堵不疏。",
            "metaphor_type": "nature",
            "explanation": "内存泄漏如同水渠堵塞，需找到引用源头并断开，而非仅仅增加内存。"
        }
    elif "race condition" in trace_lower or "concurrent" in trace_lower:
        return {
            "content": "双车过桥，需有红绿灯，令行禁止，方保无虞。",
            "metaphor_type": "daily_life",
            "explanation": "并发竞争需通过锁或信号量（红绿灯）来控制访问顺序，确保数据一致性。"
        }
    else:
        return {
            "content": "抽丝剥茧，寻其纹理，顺其自然，迎刃而解。",
            "metaphor_type": "craft",
            "explanation": "通用逻辑：遵循代码和数据结构的内在规律，逐步分析问题。"
        }


class DigitalMnemonicSystem:
    """
    数字口诀系统主类。
    负责处理高价值的学习事件，生成口诀，并持久化存储。
    """

    def __init__(self, storage_path: Path = STORAGE_FILE):
        """
        初始化系统。

        Args:
            storage_path: 口诀存储文件的路径
        """
        self.storage_path = storage_path
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """确保存储目录和文件存在"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding='utf-8')
            logger.info(f"Initialized storage at {self.storage_path}")

    def generate_mnemonic(self, event: LearningEvent) -> Optional[MnemonicRecord]:
        """
        核心函数1：根据学习事件生成口诀记录。

        Args:
            event: AI的学习事件

        Returns:
            MnemonicRecord: 生成的口诀记录，如果不符合条件则返回 None

        Raises:
            MnemonicGenerationError: 生成过程中发生错误
        """
        try:
            # 1. 数据验证
            if not validate_learning_event(event):
                return None

            logger.info(f"Generating mnemonic for high-reward task: {event.task_id}")

            # 2. 调用模拟LLM生成口诀
            generation_result = _simulate_llm_generation(event.logic_trace, event.description)

            # 3. 构建记录对象
            record = MnemonicRecord(
                mnemonic_id=f"MN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{event.task_id}",
                task_id=event.task_id,
                content=generation_result['content'],
                explanation=generation_result['explanation'],
                metaphor_type=generation_result['metaphor_type'],
                created_at=datetime.now().isoformat()
            )

            logger.info(f"Successfully generated mnemonic: {record.content}")
            return record

        except Exception as e:
            logger.error(f"Failed to generate mnemonic for task {event.task_id}: {e}")
            raise MnemonicGenerationError(f"Generation failed: {e}") from e

    def save_mnemonic(self, record: MnemonicRecord) -> bool:
        """
        核心函数2：将口诀记录保存到持久化存储中。

        Args:
            record: 要保存的口诀记录

        Returns:
            bool: 保存成功返回 True
        """
        try:
            # 读取现有数据
            existing_data: List[Dict] = json.loads(self.storage_path.read_text(encoding='utf-8'))
            
            # 追加新记录
            existing_data.append(asdict(record))
            
            # 写回文件
            self.storage_path.write_text(json.dumps(existing_data, indent=2, ensure_ascii=False), encoding='utf-8')
            
            logger.info(f"Mnemonic {record.mnemonic_id} saved successfully.")
            return True
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to save mnemonic: {e}")
            return False

    def process_learning_event(self, event: LearningEvent) -> bool:
        """
        组合函数：处理事件并自动保存。
        这是系统对外的主要接口。

        Args:
            event: 学习事件

        Returns:
            bool: 处理并保存成功返回 True
        """
        try:
            record = self.generate_mnemonic(event)
            if record:
                return self.save_mnemonic(record)
            return False
        except MnemonicGenerationError:
            return False


# 使用示例
if __name__ == "__main__":
    # 初始化系统
    system = DigitalMnemonicSystem()

    # 模拟一个高难度的并发Bug修复事件 (RLHF高分)
    high_reward_event = LearningEvent(
        task_id="BUG-FIX-1024",
        description="修复多线程环境下的死锁问题",
        logic_trace="Detected deadlock in thread A holding lock 1 waiting for lock 2, "
                     "while thread B holds lock 2 waiting for lock 1. "
                     "Solution: Implement lock ordering and try_lock with timeout.",
        reward_score=0.95
    )

    # 模拟一个普通事件 (低分，不应生成口诀)
    low_reward_event = LearningEvent(
        task_id="SIMPLE-TASK-001",
        description="打印日志",
        logic_trace="print('hello world')",
        reward_score=0.4
    )

    print("--- 处理高分事件 ---")
    system.process_learning_event(high_reward_event)

    print("\n--- 处理低分事件 ---")
    system.process_learning_event(low_reward_event)

    # 读取并展示存储的口诀
    print("\n--- 当前知识库中的口诀 ---")
    try:
        with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
            mnemonics = json.load(f)
            for m in mnemonics:
                print(f"口诀: {m['content']}")
                print(f"解释: {m['explanation']}")
                print("-" * 30)
    except FileNotFoundError:
        print("知识库文件未找到")