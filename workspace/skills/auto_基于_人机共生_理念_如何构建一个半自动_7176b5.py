"""
人机共生概念固化闭环系统

本模块实现了一个半自动化的概念固化系统，基于人机共生理念构建。
当AI发现潜在新模式时，系统会自动生成最小化实践清单供人类执行，
并根据人类反馈结果修正网络权重。

核心流程：
1. 模式检测：AI持续监控数据流，检测潜在新模式
2. 任务生成：为新模式生成最小化实践清单
3. 人类执行：人类执行任务并提供反馈
4. 权重调整：根据反馈修正网络权重
5. 模型更新：更新系统知识库

输入输出格式：
- 输入：原始数据流(JSON格式)，人类反馈(结构化文本)
- 输出：实践清单(JSON格式)，更新后的模型权重(二进制)
"""

import logging
import json
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
import pickle

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('concept_solidification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """表示检测到的新模式"""
    pattern_id: str
    description: str
    confidence: float
    detected_at: datetime
    features: Dict[str, float]


@dataclass
class Task:
    """表示人类需要执行的任务"""
    task_id: str
    pattern_id: str
    description: str
    priority: int  # 1-5, 5最高
    deadline: datetime
    parameters: Dict[str, Any]


@dataclass
class Feedback:
    """表示人类对任务的反馈"""
    task_id: str
    executed_at: datetime
    success: bool
    observations: str
    rating: int  # 1-5, 5最符合预期


class ModelInterface(ABC):
    """模型接口抽象基类"""
    
    @abstractmethod
    def detect_patterns(self, data: np.ndarray) -> List[Pattern]:
        """检测数据中的新模式"""
        pass
    
    @abstractmethod
    def adjust_weights(self, feedback: List[Feedback]) -> float:
        """根据反馈调整模型权重"""
        pass
    
    @abstractmethod
    def save(self, path: Path) -> bool:
        """保存模型到文件"""
        pass
    
    @abstractmethod
    def load(self, path: Path) -> bool:
        """从文件加载模型"""
        pass


class NeuralNetworkModel(ModelInterface):
    """神经网络模型实现"""
    
    def __init__(self, input_size: int = 10, hidden_size: int = 20):
        self.weights = {
            'input_hidden': np.random.randn(input_size, hidden_size),
            'hidden_output': np.random.randn(hidden_size, 1)
        }
        self.pattern_count = 0
    
    def detect_patterns(self, data: np.ndarray) -> List[Pattern]:
        """检测数据中的新模式"""
        if data.ndim != 2 or data.shape[1] != self.weights['input_hidden'].shape[0]:
            raise ValueError("输入数据维度不匹配")
        
        # 简化的模式检测逻辑 - 实际应用中应使用更复杂的算法
        predictions = np.dot(data, self.weights['input_hidden'])
        predictions = np.dot(predictions, self.weights['hidden_output'])
        
        patterns = []
        for i, pred in enumerate(predictions):
            if pred > 0.7:  # 阈值检测
                self.pattern_count += 1
                pattern = Pattern(
                    pattern_id=f"p_{self.pattern_count}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    description=f"高置信度模式#{self.pattern_count}",
                    confidence=float(pred),
                    detected_at=datetime.now(),
                    features={"feature_1": float(pred), "feature_2": 1.0 - float(pred)}
                )
                patterns.append(pattern)
                logger.info(f"检测到新模式: {pattern.pattern_id} (置信度: {pred:.2f})")
        
        return patterns
    
    def adjust_weights(self, feedback: List[Feedback]) -> float:
        """根据反馈调整模型权重"""
        if not feedback:
            logger.warning("收到空反馈列表")
            return 0.0
        
        total_adjustment = 0.0
        for fb in feedback:
            # 简单的权重调整逻辑
            adjustment_factor = fb.rating / 5.0
            if not fb.success:
                adjustment_factor *= -0.5
            
            # 随机调整部分权重 (实际应用中应使用更复杂的算法)
            adjust_size = int(0.1 * self.weights['input_hidden'].size)
            indices = np.random.choice(self.weights['input_hidden'].size, adjust_size, replace=False)
            flat_weights = self.weights['input_hidden'].ravel()
            flat_weights[indices] += adjustment_factor * np.random.randn(adjust_size)
            self.weights['input_hidden'] = flat_weights.reshape(self.weights['input_hidden'].shape)
            
            total_adjustment += abs(adjustment_factor)
            logger.info(f"根据反馈 {fb.task_id} 调整权重 (调整因子: {adjustment_factor:.2f})")
        
        avg_adjustment = total_adjustment / len(feedback)
        logger.info(f"平均权重调整: {avg_adjustment:.4f}")
        return avg_adjustment
    
    def save(self, path: Path) -> bool:
        """保存模型到文件"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                pickle.dump(self.weights, f)
            logger.info(f"模型已保存到 {path}")
            return True
        except Exception as e:
            logger.error(f"保存模型失败: {str(e)}")
            return False
    
    def load(self, path: Path) -> bool:
        """从文件加载模型"""
        try:
            if not path.exists():
                logger.error(f"模型文件不存在: {path}")
                return False
                
            with open(path, 'rb') as f:
                self.weights = pickle.load(f)
            logger.info(f"已从 {path} 加载模型")
            return True
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            return False


class TaskGenerator:
    """任务生成器，为检测到的模式生成最小化实践清单"""
    
    def __init__(self, task_templates: Dict[str, str]):
        self.task_templates = task_templates
        self.task_count = 0
    
    def generate_tasks(self, pattern: Pattern) -> List[Task]:
        """为模式生成实践任务"""
        if pattern.confidence < 0.5 or pattern.confidence > 1.0:
            raise ValueError(f"无效的置信度值: {pattern.confidence}")
        
        tasks = []
        priority = min(5, max(1, int(pattern.confidence * 5)))
        
        for template_name, template in self.task_templates.items():
            self.task_count += 1
            task = Task(
                task_id=f"t_{self.task_count}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                pattern_id=pattern.pattern_id,
                description=template.format(
                    pattern_description=pattern.description,
                    confidence=pattern.confidence
                ),
                priority=priority,
                deadline=datetime.now() + timedelta(days=1),
                parameters={"template": template_name, "pattern_features": pattern.features}
            )
            tasks.append(task)
            logger.info(f"生成任务: {task.task_id} (优先级: {priority})")
        
        return tasks


class ConceptSolidificationSystem:
    """人机共生概念固化闭环系统"""
    
    def __init__(
        self,
        model: ModelInterface,
        task_generator: TaskGenerator,
        model_path: Path = Path("models/concept_model.pkl")
    ):
        self.model = model
        self.task_generator = task_generator
        self.model_path = model_path
        self.pending_tasks: Dict[str, Task] = {}
        self.completed_feedback: List[Feedback] = []
        
        # 尝试加载已有模型
        if self.model_path.exists():
            self.model.load(self.model_path)
    
    def process_data_stream(self, data_stream: List[Dict[str, Any]]) -> List[Task]:
        """
        处理数据流，检测模式并生成任务
        
        Args:
            data_stream: 输入数据流，每个元素应为包含特征向量的字典
            
        Returns:
            生成的人类需要执行的任务列表
        """
        if not data_stream:
            logger.warning("收到空数据流")
            return []
        
        try:
            # 将数据转换为numpy数组
            features = []
            for data in data_stream:
                if 'features' not in data:
                    raise ValueError("数据项缺少'features'字段")
                features.append(data['features'])
            
            data_array = np.array(features)
            
            # 检测模式
            patterns = self.model.detect_patterns(data_array)
            if not patterns:
                logger.info("未检测到显著模式")
                return []
            
            # 为每个模式生成任务
            all_tasks = []
            for pattern in patterns:
                tasks = self.task_generator.generate_tasks(pattern)
                for task in tasks:
                    self.pending_tasks[task.task_id] = task
                all_tasks.extend(tasks)
            
            return all_tasks
            
        except Exception as e:
            logger.error(f"处理数据流时出错: {str(e)}")
            return []
    
    def process_human_feedback(self, feedback: Feedback) -> bool:
        """
        处理人类反馈并调整模型
        
        Args:
            feedback: 人类对任务的反馈
            
        Returns:
            处理是否成功
        """
        if feedback.task_id not in self.pending_tasks:
            logger.error(f"未知的任务ID: {feedback.task_id}")
            return False
        
        try:
            # 验证反馈数据
            if feedback.rating < 1 or feedback.rating > 5:
                raise ValueError(f"无效的评分值: {feedback.rating}")
            
            # 存储反馈
            self.completed_feedback.append(feedback)
            task = self.pending_tasks.pop(feedback.task_id)
            
            # 当积累足够反馈时调整模型
            if len(self.completed_feedback) >= 3:  # 每3个反馈调整一次
                avg_adjustment = self.model.adjust_weights(self.completed_feedback)
                self.completed_feedback = []
                
                # 保存调整后的模型
                if not self.model.save(self.model_path):
                    logger.error("保存调整后的模型失败")
                
                logger.info(f"模型权重调整完成 (平均调整: {avg_adjustment:.4f})")
            
            return True
            
        except Exception as e:
            logger.error(f"处理反馈时出错: {str(e)}")
            return False
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        获取待处理任务列表
        
        Returns:
            待处理任务的字典列表，包含任务详情
        """
        return [
            {
                'task_id': task.task_id,
                'pattern_id': task.pattern_id,
                'description': task.description,
                'priority': task.priority,
                'deadline': task.deadline.isoformat(),
                'parameters': task.parameters
            }
            for task in self.pending_tasks.values()
        ]
    
    def export_tasks_to_json(self, file_path: Path) -> bool:
        """
        将待处理任务导出为JSON文件
        
        Args:
            file_path: 目标文件路径
            
        Returns:
            导出是否成功
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            tasks = self.get_pending_tasks()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            
            logger.info(f"任务已导出到 {file_path}")
            return True
        except Exception as e:
            logger.error(f"导出任务失败: {str(e)}")
            return False


# 示例用法
if __name__ == "__main__":
    from datetime import timedelta
    
    # 初始化系统组件
    model = NeuralNetworkModel(input_size=5, hidden_size=10)
    task_templates = {
        'verification': "验证模式: {pattern_description} (置信度: {confidence:.2f})",
        'exploration': "探索模式边界: {pattern_description}",
        'application': "应用模式: {pattern_description} 于实际场景"
    }
    task_generator = TaskGenerator(task_templates)
    
    # 创建概念固化系统
    system = ConceptSolidificationSystem(
        model=model,
        task_generator=task_generator,
        model_path=Path("models/example_model.pkl")
    )
    
    # 模拟数据流
    data_stream = [
        {'features': [0.1, 0.2, 0.3, 0.4, 0.5]},
        {'features': [0.6, 0.7, 0.8, 0.9, 1.0]},  # 可能触发模式
        {'features': [1.1, 1.2, 1.3, 1.4, 1.5]},  # 可能触发模式
        {'features': [0.5, 0.5, 0.5, 0.5, 0.5]}
    ]
    
    # 处理数据流并生成任务
    tasks = system.process_data_stream(data_stream)
    print(f"生成 {len(tasks)} 个任务")
    
    # 导出任务
    system.export_tasks_to_json(Path("output/pending_tasks.json"))
    
    # 模拟人类反馈
    if tasks:
        first_task = tasks[0]
        feedback = Feedback(
            task_id=first_task.task_id,
            executed_at=datetime.now(),
            success=True,
            observations="模式验证成功，观察到预期行为",
            rating=4
        )
        system.process_human_feedback(feedback)
    
    # 获取剩余待处理任务
    pending = system.get_pending_tasks()
    print(f"剩余 {len(pending)} 个待处理任务")