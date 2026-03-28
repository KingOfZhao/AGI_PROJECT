"""
跨产线知识泛化与迁移模块 (Cross-Production-Line Transfer Learning)

该模块实现了基于深度学习的跨域迁移框架，专门解决工业场景下（如汽车焊接到电子组装）
的知识复用问题。核心采用基于特征对齐的Few-shot微调策略。

主要组件:
- ProductionLineTransfer: 核心迁移学习类
- DomainDiscriminator: 域判别器（用于对抗训练）
- FeatureEncoder: 通用特征编码器

输入数据格式:
    源域数据: {"features": np.ndarray, "labels": np.ndarray, "domain": "source"}
    目标域数据: {"features": np.ndarray, "labels": np.ndarray, "domain": "target"}
    
输出格式:
    {
        "model": trained_model,
        "metrics": {"accuracy": float, "transfer_loss": float},
        "adapted_weights": np.ndarray
    }
"""

import numpy as np
import logging
from typing import Dict, Tuple, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import warnings
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# 初始化日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TransferConfig:
    """迁移学习配置参数"""
    input_dim: int = 64  # 输入特征维度
    hidden_dim: int = 128  # 隐藏层维度
    n_classes: int = 5  # 分类类别数
    learning_rate: float = 0.001
    batch_size: int = 32
    adaptation_steps: int = 100  # Few-shot适应步数
    lambda_transfer: float = 0.1  # 迁移损失权重


class FeatureEncoder:
    """通用特征编码器（模拟神经网络前向传播）"""
    
    def __init__(self, input_dim: int, hidden_dim: int):
        self.weights = np.random.randn(input_dim, hidden_dim) * 0.01
        self.bias = np.zeros(hidden_dim)
        
    def forward(self, x: np.ndarray) -> np.ndarray:
        """前向传播（带ReLU激活）"""
        if x.ndim == 1:
            x = x.reshape(1, -1)
        return np.maximum(0, np.dot(x, self.weights) + self.bias)
    
    def update(self, grads: np.ndarray, lr: float):
        """参数更新（简化版SGD）"""
        self.weights -= lr * grads


class DomainDiscriminator:
    """域判别器（用于对抗训练）"""
    
    def __init__(self, hidden_dim: int):
        self.weights = np.random.randn(hidden_dim, 1) * 0.01
        self.bias = 0.0
        
    def forward(self, features: np.ndarray) -> np.ndarray:
        """域预测（Sigmoid输出）"""
        logits = np.dot(features, self.weights) + self.bias
        return 1 / (1 + np.exp(-logits))
    
    def domain_loss(self, source_feat: np.ndarray, target_feat: np.ndarray) -> float:
        """计算域混淆损失"""
        source_pred = self.forward(source_feat)
        target_pred = self.forward(target_feat)
        
        # 希望判别器无法区分源域和目标域
        loss = -np.mean(np.log(source_pred + 1e-8) + np.log(1 - target_pred + 1e-8))
        return loss


class ProductionLineTransfer:
    """
    跨产线知识迁移核心类
    
    示例用法:
    >>> config = TransferConfig(input_dim=10, n_classes=3)
    >>> transfer = ProductionLineTransfer(config)
    >>> source_data = {"features": np.random.rand(100, 10), "labels": np.random.randint(0,3,100)}
    >>> target_data = {"features": np.random.rand(20, 10), "labels": np.random.randint(0,3,20)}
    >>> result = transfer.transfer_knowledge(source_data, target_data)
    """
    
    def __init__(self, config: TransferConfig):
        """初始化迁移框架"""
        self.config = config
        self.encoder = FeatureEncoder(config.input_dim, config.hidden_dim)
        self.classifier = np.random.randn(config.hidden_dim, config.n_classes) * 0.01
        self.discriminator = DomainDiscriminator(config.hidden_dim)
        self._validate_config()
        
    def _validate_config(self):
        """验证配置参数合法性"""
        if self.config.learning_rate <= 0:
            raise ValueError("Learning rate must be positive")
        if self.config.batch_size <= 0:
            raise ValueError("Batch size must be positive")
            
    def _preprocess_data(self, data: Dict) -> Tuple[np.ndarray, np.ndarray]:
        """数据预处理和验证"""
        if not isinstance(data, dict):
            raise TypeError("Input data must be dictionary")
            
        features = np.asarray(data["features"])
        labels = np.asarray(data["labels"])
        
        if features.ndim != 2:
            raise ValueError("Features must be 2D array")
        if features.shape[1] != self.config.input_dim:
            raise ValueError(f"Expected input dim {self.config.input_dim}, got {features.shape[1]}")
            
        # 归一化处理
        features = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-8)
        return features, labels
    
    def _compute_gradients(self, features: np.ndarray, labels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """计算分类任务梯度（简化版）"""
        # 前向传播
        encoded = self.encoder.forward(features)
        logits = np.dot(encoded, self.classifier)
        
        # Softmax交叉熵梯度（简化计算）
        probs = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
        one_hot = np.eye(self.config.n_classes)[labels]
        grad_logits = (probs - one_hot) / len(labels)
        
        # 反向传播
        grad_classifier = np.dot(encoded.T, grad_logits)
        grad_encoded = np.dot(grad_logits, self.classifier.T)
        
        return grad_classifier, grad_encoded
    
    def adapt_to_target(self, target_data: Dict, n_shots: int = 5) -> Dict[str, float]:
        """
        Few-shot适应到目标域
        
        参数:
            target_data: 目标域数据（少量标注样本）
            n_shots: 每个类别使用的样本数
            
        返回:
            包含适应指标的字典
        """
        try:
            features, labels = self._preprocess_data(target_data)
            
            # 选择few-shot样本
            selected_idx = []
            for c in range(self.config.n_classes):
                class_idx = np.where(labels == c)[0]
                if len(class_idx) > 0:
                    selected_idx.extend(np.random.choice(class_idx, min(n_shots, len(class_idx)), replace=False))
            
            if not selected_idx:
                warnings.warn("No valid samples selected for adaptation")
                return {"adapt_loss": float('nan')}
                
            X_shot = features[selected_idx]
            y_shot = labels[selected_idx]
            
            # 微调适应
            losses = []
            for step in range(self.config.adaptation_steps):
                # 计算梯度
                grad_clf, grad_enc = self._compute_gradients(X_shot, y_shot)
                
                # 更新参数
                self.classifier -= self.config.learning_rate * grad_clf
                self.encoder.update(grad_enc.T, self.config.learning_rate)
                
                # 记录损失
                encoded = self.encoder.forward(X_shot)
                logits = np.dot(encoded, self.classifier)
                loss = -np.mean(np.log(np.sum(np.exp(logits), axis=1)))
                losses.append(loss)
                
                if step % 20 == 0:
                    logger.debug(f"Adaptation step {step}, loss: {loss:.4f}")
            
            return {
                "adapt_loss": np.mean(losses[-10:]),
                "final_accuracy": self._evaluate(X_shot, y_shot)
            }
            
        except Exception as e:
            logger.error(f"Adaptation failed: {str(e)}")
            raise RuntimeError(f"Target domain adaptation error: {str(e)}") from e
    
    def transfer_knowledge(
        self,
        source_data: Dict,
        target_data: Dict,
        n_shots: int = 5
    ) -> Dict[str, Union[object, Dict]]:
        """
        完整的跨产线知识迁移流程
        
        参数:
            source_data: 源产线数据（大量标注）
            target_data: 目标产线数据（少量标注）
            n_shots: 目标域每类样本数
            
        返回:
            包含迁移结果和指标的字典
        """
        logger.info("Starting cross-production-line knowledge transfer")
        
        try:
            # 1. 源域预训练
            logger.info("Phase 1: Source domain pre-training")
            X_source, y_source = self._preprocess_data(source_data)
            
            # 简化训练循环（实际应用应使用PyTorch/TensorFlow）
            for epoch in range(5):  # 5个伪epoch
                grad_clf, grad_enc = self._compute_gradients(X_source, y_source)
                self.classifier -= self.config.learning_rate * grad_clf
                self.encoder.update(grad_enc.T, self.config.learning_rate)
            
            # 2. 域适应
            logger.info("Phase 2: Target domain adaptation")
            adapt_metrics = self.adapt_to_target(target_data, n_shots)
            
            # 3. 计算迁移距离
            X_target, _ = self._preprocess_data(target_data)
            source_feat = self.encoder.forward(X_source[:100])  # 限制样本量
            target_feat = self.encoder.forward(X_target)
            
            transfer_loss = self.discriminator.domain_loss(source_feat, target_feat)
            
            result = {
                "model": self,
                "adaptation_metrics": adapt_metrics,
                "transfer_distance": transfer_loss,
                "source_performance": self._evaluate(X_source, y_source),
                "target_performance": adapt_metrics["final_accuracy"]
            }
            
            logger.info(f"Transfer completed. Target accuracy: {adapt_metrics['final_accuracy']:.2%}")
            return result
            
        except Exception as e:
            logger.error(f"Knowledge transfer failed: {str(e)}")
            raise RuntimeError(f"Transfer process error: {str(e)}") from e
    
    def _evaluate(self, features: np.ndarray, labels: np.ndarray) -> float:
        """评估模型性能"""
        encoded = self.encoder.forward(features)
        logits = np.dot(encoded, self.classifier)
        preds = np.argmax(logits, axis=1)
        return accuracy_score(labels, preds)


def visualize_transfer_result(result: Dict) -> None:
    """
    可视化迁移结果（辅助函数）
    
    参数:
        result: transfer_knowledge的输出结果
    """
    print("\nTransfer Learning Results:")
    print(f"- Source Domain Accuracy: {result['source_performance']:.2%}")
    print(f"- Target Domain Accuracy: {result['target_performance']:.2%}")
    print(f"- Transfer Distance: {result['transfer_distance']:.4f}")
    print(f"- Adaptation Loss: {result['adaptation_metrics']['adapt_loss']:.4f}")


# 使用示例
if __name__ == "__main__":
    # 模拟汽车焊接产线数据（源域）
    source_data = {
        "features": np.random.randn(1000, 10),  # 1000个样本，10个传感器特征
        "labels": np.random.randint(0, 5, 1000),  # 5种焊接质量等级
        "domain": "automotive_welding"
    }
    
    # 模拟电子组装产线数据（目标域）
    target_data = {
        "features": np.random.randn(50, 10) * 1.2,  # 50个样本，带域偏移
        "labels": np.random.randint(0, 5, 50),
        "domain": "electronics_assembly"
    }
    
    # 初始化并执行迁移
    config = TransferConfig(input_dim=10, n_classes=5)
    transfer_system = ProductionLineTransfer(config)
    transfer_result = transfer_system.transfer_knowledge(source_data, target_data, n_shots=3)
    
    # 输出结果
    visualize_transfer_result(transfer_result)