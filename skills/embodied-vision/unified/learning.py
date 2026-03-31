#!/usr/bin/env python3
"""
embodied-vision/learning — 学习组件

从成功/失败案例中自动学习:
- 参数自动优化 (贝叶斯优化简化版)
- 抓取策略学习 (从成功案例中提取模式)
- 感知质量评估 (输出质量评分)
- 增量学习 (持续改进)
"""

import json
import time
import math
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


# ═══════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════

@dataclass
class Experiment:
    """一次实验记录"""
    id: int
    timestamp: str
    params: Dict[str, float]  # 使用的参数
    result: Dict  # 结果指标
    score: float  # 综合评分
    success: bool


@dataclass  
class ParameterSpace:
    """参数搜索空间"""
    name: str
    low: float
    high: float
    step: float = 0.01
    type: str = "float"  # float/int/log


@dataclass
class LearnedStrategy:
    """学到的策略"""
    name: str
    conditions: Dict  # 适用条件
    params: Dict  # 推荐参数
    confidence: float
    sample_count: int


# ═══════════════════════════════════════════
# 1. 参数优化器
# ═══════════════════════════════════════════

class ParameterOptimizer:
    """
    简化贝叶斯优化
    用于自动调优视觉pipeline参数
    """
    
    def __init__(self, param_space: List[ParameterSpace]):
        self.param_space = param_space
        self.experiments: List[Experiment] = []
        self.best_score = 0.0
        self.best_params: Dict = {}
        self.next_id = 0
    
    def suggest(self) -> Dict[str, float]:
        """建议下一组参数"""
        if len(self.experiments) < 5:
            # 初始: 随机采样
            return self._random_sample()
        
        # 收集成功经验
        top_exp = sorted(self.experiments, key=lambda e: -e.score)[:10]
        
        # 在最优参数附近搜索
        best = self.best_params
        suggestion = {}
        
        for ps in self.param_space:
            name = ps.name
            if name in best:
                # 在最优值附近扰动
                delta = (ps.high - ps.low) * 0.1
                delta *= random.uniform(-1, 1)
                suggestion[name] = max(ps.low, min(ps.high, best[name] + delta))
            else:
                suggestion[name] = random.uniform(ps.low, ps.high)
        
        return suggestion
    
    def record(self, params: Dict[str, float], score: float, 
               result: Dict = None, success: bool = True):
        """记录一次实验"""
        exp = Experiment(
            id=self.next_id,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            params=params,
            result=result or {},
            score=score,
            success=success
        )
        self.experiments.append(exp)
        self.next_id += 1
        
        if score > self.best_score:
            self.best_score = score
            self.best_params = params.copy()
    
    def _random_sample(self) -> Dict[str, float]:
        params = {}
        for ps in self.param_space:
            if ps.type == "log":
                log_low = math.log(ps.low)
                log_high = math.log(ps.high)
                params[ps.name] = math.exp(random.uniform(log_low, log_high))
            else:
                params[ps.name] = random.uniform(ps.low, ps.high)
        return params
    
    def get_best(self) -> Tuple[Dict[str, float], float]:
        """获取最优参数和分数"""
        return self.best_params, self.best_score
    
    def save(self, path: str):
        data = {
            "experiments": [
                {"id": e.id, "params": e.params, "score": e.score, 
                 "result": e.result, "success": e.success, "timestamp": e.timestamp}
                for e in self.experiments
            ],
            "best_score": self.best_score,
            "best_params": self.best_params,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2))
    
    def load(self, path: str):
        if not Path(path).exists():
            return
        data = json.loads(Path(path).read_text())
        self.best_score = data.get("best_score", 0)
        self.best_params = data.get("best_params", {})
        for e in data.get("experiments", []):
            self.experiments.append(Experiment(
                id=e["id"], timestamp=e["timestamp"],
                params=e["params"], result=e.get("result", {}),
                score=e["score"], success=e.get("success", True)
            ))


# ═══════════════════════════════════════════
# 2. 质量评估器
# ═══════════════════════════════════════════

class QualityEvaluator:
    """
    评估视觉pipeline输出质量
    用于自动评分和参数优化
    """
    
    @staticmethod
    def evaluate_white_black(image_path: str) -> Dict:
        """
        评估白底黑边图质量
        """
        import cv2
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {"score": 0, "error": "无法读取"}
        
        h, w = img.shape
        
        # 1. 背景纯净度 (白底应接近255)
        bg_pixels = img[img > 200]
        bg_purity = float(len(bg_pixels) / (h * w))
        bg_mean = float(bg_pixels.mean()) if len(bg_pixels) > 0 else 0
        
        # 2. 线条密度 (黑线占比)
        line_pixels = img[img < 50]
        line_density = float(len(line_pixels) / (h * w))
        
        # 3. 线条连续性 (中间灰度像素应少)
        mid_pixels = img[(img >= 50) & (img <= 200)]
        noise_ratio = float(len(mid_pixels) / (h * w))
        
        # 4. 边缘利用 (线条应分布在图像中心区域)
        center_mask = np.zeros((h, w), dtype=np.uint8)
        margin = min(h, w) // 10
        center_mask[margin:h-margin, margin:w-margin] = 255
        center_lines = cv2.countNonZero(cv2.bitwise_and(cv2.threshold(img, 50, 255, cv2.THRESH_BINARY_INV)[1], center_mask))
        edge_utilization = center_lines / max(len(line_pixels), 1)
        
        # 综合评分
        score = (
            bg_purity * 30 +        # 背景纯度 30%
            min(line_density, 0.3) / 0.3 * 30 +  # 线条密度 30% (3-30%最佳)
            (1 - noise_ratio) * 20 +  # 低噪声 20%
            edge_utilization * 20     # 边缘利用 20%
        )
        
        return {
            "score": round(min(score, 100), 1),
            "bg_purity": round(bg_purity, 3),
            "line_density": round(line_density, 4),
            "noise_ratio": round(noise_ratio, 4),
            "edge_utilization": round(edge_utilization, 3),
            "total_white_pct": round(bg_purity * 100, 1),
            "total_black_pct": round(line_density * 100, 1),
        }


# Fix: need numpy for evaluate
import numpy as np


# ═══════════════════════════════════════════
# 3. 策略学习器
# ═══════════════════════════════════════════

class StrategyLearner:
    """
    从实验中学习策略
    "当纹理熵>5时, 增大Canny阈值"
    "当线条密度<5%时, 降低自适应阈值blockSize"
    """
    
    def __init__(self):
        self.strategies: List[LearnedStrategy] = []
    
    def learn_from_experiments(self, experiments: List[Experiment]):
        """从实验中提取策略"""
        # 按条件分组
        groups = defaultdict(list)
        
        for exp in experiments:
            if not exp.success:
                continue
            
            # 简单条件: 纹理熵高/低, 边缘密度高/低
            tex_entropy = exp.result.get("texture_entropy", 5.0)
            edge_density = exp.result.get("edge_density", 0.1)
            
            conditions = {}
            if tex_entropy > 5:
                conditions["texture"] = "high"
            elif tex_entropy < 3:
                conditions["texture"] = "low"
            else:
                conditions["texture"] = "medium"
            
            if edge_density > 0.15:
                conditions["edges"] = "dense"
            elif edge_density < 0.05:
                conditions["edges"] = "sparse"
            else:
                conditions["edges"] = "normal"
            
            key = json.dumps(conditions, sort_keys=True)
            groups[key].append(exp)
        
        # 每组提取最优参数
        new_strategies = []
        for key, exps in groups.items():
            if len(exps) < 2:
                continue
            
            conditions = json.loads(key)
            best = max(exps, key=lambda e: e.score)
            
            # 提取参数趋势
            avg_params = {}
            for param_name in best.params:
                values = [e.params.get(param_name, 0) for e in exps if param_name in e.params]
                if values:
                    # 加权平均(权重=score)
                    total_weight = sum(e.score for e in exps if param_name in e.params)
                    if total_weight > 0:
                        avg_params[param_name] = sum(
                            e.params.get(param_name, 0) * e.score 
                            for e in exps if param_name in e.params
                        ) / total_weight
            
            strategy = LearnedStrategy(
                name=f"strategy_{len(self.strategies)+1}",
                conditions=conditions,
                params=avg_params,
                confidence=best.score / 100,
                sample_count=len(exps)
            )
            new_strategies.append(strategy)
        
        self.strategies.extend(new_strategies)
        return new_strategies
    
    def suggest_for(self, conditions: Dict) -> Optional[Dict]:
        """根据当前条件推荐参数"""
        best_match = None
        best_confidence = 0
        
        for strategy in self.strategies:
            match_score = 0
            total = 0
            for key, value in conditions.items():
                if key in strategy.conditions:
                    total += 1
                    if strategy.conditions[key] == value:
                        match_score += 1
            
            if total > 0:
                match_ratio = match_score / total
                confidence = match_ratio * strategy.confidence
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = strategy
        
        if best_match:
            return best_match.params
        return None


# ═══════════════════════════════════════════
# 4. 自动调优流程
# ═══════════════════════════════════════════

class AutoTuner:
    """
    自动调优DiePre Pipeline
    """
    
    def __init__(self, pipeline_func, eval_func, param_space: List[ParameterSpace]):
        """
        pipeline_func: (image_path, params) -> output_path
        eval_func: (output_path) -> score
        """
        self.pipeline = pipeline_func
        self.evaluate = eval_func
        self.optimizer = ParameterOptimizer(param_space)
        self.learner = StrategyLearner()
    
    def tune(self, image_path: str, n_iterations: int = 20) -> Dict:
        """运行n轮自动调优"""
        print(f"自动调优开始: {n_iterations}轮")
        
        for i in range(n_iterations):
            params = self.optimizer.suggest()
            print(f"\n  轮次 {i+1}/{n_iterations}: 参数={ {k: round(v,2) for k,v in params.items()} }")
            
            try:
                output_path = self.pipeline(image_path, params)
                eval_result = self.evaluate(output_path)
                score = eval_result.get("score", 0)
                
                self.optimizer.record(params, score, eval_result, score > 50)
                
                print(f"    评分: {score:.1f} (最佳: {self.optimizer.best_score:.1f})")
            except Exception as e:
                print(f"    错误: {e}")
        
        # 学习策略
        self.learner.learn_from_experiments(self.optimizer.experiments)
        
        best_params, best_score = self.optimizer.get_best()
        print(f"\n调优完成: 最佳评分={best_score:.1f}")
        print(f"最佳参数: {best_params}")
        
        return {
            "best_score": best_score,
            "best_params": best_params,
            "iterations": n_iterations,
            "strategies_learned": len(self.learner.strategies)
        }


# ═══════════════════════════════════════════
# 演示
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import cv2
    
    # 评估现有v4输出
    output_dir = Path("/Users/administruter/Desktop/DiePre AI/vision_pipeline/output_v4")
    evaluator = QualityEvaluator()
    
    print("=== DiePre v4 输出质量评估 ===\n")
    
    for f in sorted(output_dir.glob("*_white_black.png")):
        result = evaluator.evaluate_white_black(str(f))
        print(f"  {f.name:50s} | 评分={result['score']:5.1f} "
              f"白={result['total_white_pct']:5.1f}% "
              f"黑={result['total_black_pct']:5.1f}% "
              f"噪声={result['noise_ratio']:.3f}")
    
    # 演示策略学习
    print("\n=== 策略学习演示 ===\n")
    
    optimizer = ParameterOptimizer([
        ParameterSpace("canny_low", 10, 100),
        ParameterSpace("canny_high", 50, 300),
        ParameterSpace("block_size", 11, 41),
        ParameterSpace("morph_kernel", 1, 15),
    ])
    
    # 模拟实验
    for i in range(20):
        params = optimizer.suggest()
        # 模拟评分(纹理高→需要更高阈值)
        tex = random.uniform(1, 10)
        score = random.gauss(60, 15)
        if tex > 6:
            score += params.get("canny_low", 50) * 0.2  # 高纹理→高阈值好
        score = max(0, min(100, score))
        
        optimizer.record(params, score, 
                        {"texture_entropy": tex, "edge_density": random.uniform(0.02, 0.3)},
                        score > 50)
    
    best_params, best_score = optimizer.get_best()
    print(f"模拟实验: 20轮")
    print(f"  最佳评分: {best_score:.1f}")
    print(f"  最佳参数: { {k: round(v,2) for k,v in best_params.items()} }")
    
    # 学习策略
    learner = StrategyLearner()
    strategies = learner.learn_from_experiments(optimizer.experiments)
    print(f"  学到策略: {len(strategies)}")
    for s in strategies:
        print(f"    {s.conditions} → 置信度={s.confidence:.2f} 样本={s.sample_count}")
    
    print(f"\n✅ 学习组件测试完成")
