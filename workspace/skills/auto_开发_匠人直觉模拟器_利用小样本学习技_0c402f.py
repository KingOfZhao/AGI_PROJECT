"""
匠人直觉模拟器

本模块实现了一个基于小样本学习的"匠人直觉模拟器"。它不依赖暴力网格搜索，
而是利用元学习和高斯过程回归（GPR）模拟老工匠在"火候"、"湿度"等模糊变量
上的决策边界。通过"启发式直觉"（Acquisition Function），AI能在巨大的
参数搜索空间中，像老匠人一样根据少量特征迅速定位最优参数范围。

主要应用场景：
- 极度非结构化环境下的参数调优
- 复杂社会系统模拟
- 稀缺数据下的决策边界预测
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel
from scipy.stats import norm
from scipy.optimize import minimize

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ArtisanIntuitionSimulator")


@dataclass
class CraftParameter:
    """
    匠人工艺参数定义类。
    
    属性:
        name (str): 参数名称（如 '火候'、'湿度'）
        min_val (float): 最小值
        max_val (float): 最大值
        step (float): 调整步长（模拟老匠人的手感精度）
    """
    name: str
    min_val: float
    max_val: float
    step: float = 0.1

    def __post_init__(self):
        """数据验证"""
        if self.min_val >= self.max_val:
            raise ValueError(f"参数 {self.name} 的最小值必须小于最大值")
        if self.step <= 0:
            raise ValueError("步长必须为正数")

    def normalize(self, value: float) -> float:
        """将数值归一化到 [0, 1] 区间"""
        return (value - self.min_val) / (self.max_val - self.min_val)

    def denormalize(self, value: float) -> float:
        """从 [0, 1] 区间还原到原始区间"""
        return self.min_val + value * (self.max_val - self.min_val)


@dataclass
class IntuitionMemory:
    """
    匠人的“经验记忆”存储。
    
    属性:
        X (np.ndarray): 已知的参数样本（归一化后）
        y (np.ndarray): 对应的工艺评分（通常假设越大越好，或根据场景定义）
    """
    X: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    y: np.ndarray = field(default_factory=lambda: np.empty((0, 1)))
    
    def add_observation(self, params: np.ndarray, score: float):
        """添加一次观察记录"""
        if self.X.size == 0:
            self.X = np.array([params])
        else:
            self.X = np.vstack([self.X, params])
        
        self.y = np.append(self.y, score)


class ArtisanIntuitionSimulator:
    """
    匠人直觉模拟器核心类。
    
    利用高斯过程作为非参数模型，模拟老工匠对于模糊变量的认知。
    通过 Expected Improvement (EI) 策略来模拟“预感”，决定下一步尝试什么参数。
    """
    
    def __init__(self, parameters: List[CraftParameter]):
        """
        初始化模拟器。
        
        参数:
            parameters (List[CraftParameter]): 需要调优的参数定义列表
        """
        if not parameters:
            raise ValueError("参数列表不能为空")
            
        self.parameters = parameters
        self.dim = len(parameters)
        self.memory = IntuitionMemory()
        
        # 定义核函数：Matern核模拟平滑但不一定无限可导的物理过程（更像人工操作）
        kernel = ConstantKernel(1.0) * Matern(length_scale=1.0, nu=1.5)
        self.gp_model = GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-6,
            normalize_y=True,
            n_restarts_optimizer=5
        )
        
        self.is_fitted = False
        logger.info(f"匠人直觉模拟器已初始化，关注维度: {[p.name for p in parameters]}")

    def _validate_inputs(self, param_dict: Dict[str, float]) -> np.ndarray:
        """
        辅助函数：验证输入参数并进行边界检查与归一化。
        
        参数:
            param_dict (Dict[str, float]): 原始参数键值对
            
        返回:
            np.ndarray: 归一化后的参数向量
            
        异常:
            ValueError: 当参数缺失或超出边界时抛出
        """
        if len(param_dict) != self.dim:
            raise ValueError(f"输入参数维度不匹配，期望 {self.dim}，得到 {len(param_dict)}")
            
        normalized_vector = []
        for p_def in self.parameters:
            val = param_dict.get(p_def.name)
            
            if val is None:
                raise ValueError(f"缺少参数: {p_def.name}")
            
            # 边界检查（允许微小的浮点数误差）
            if not (p_def.min_val - 1e-4 <= val <= p_def.max_val + 1e-4):
                logger.error(f"参数 {p_def.name}={val} 超出边界 [{p_def.min_val}, {p_def.max_val}]")
                raise ValueError(f"参数 {p_def.name} 超出允许范围")
                
            normalized_vector.append(p_def.normalize(val))
            
        return np.array(normalized_vector)

    def observe(self, sample_data: List[Dict[str, float]], scores: List[float]):
        """
        核心函数 1: 观察并学习。
        
        模拟老工匠积累经验的过程。输入少量的样本（小样本学习），
        更新内部的高斯过程模型。
        
        参数:
            sample_data (List[Dict]): 样本数据列表，每个元素是参数键值对
            scores (List[float]): 对应的评价分数（如产品质量分）
        """
        if len(sample_data) != len(scores):
            raise ValueError("样本数据与分数列表长度不一致")
            
        logger.info(f"正在吸收 {len(sample_data)} 条经验数据...")
        
        processed_X = []
        for i, sample in enumerate(sample_data):
            try:
                norm_vec = self._validate_inputs(sample)
                processed_X.append(norm_vec)
                # 这里同时也存入原始memory，虽然GP模型内部会存，但保留显式记忆便于分析
                self.memory.add_observation(norm_vec, scores[i])
            except ValueError as e:
                logger.warning(f"跳过无效样本 {i}: {e}")
                continue
                
        if not processed_X:
            logger.error("没有有效数据可供学习")
            return

        X_train = np.array(processed_X)
        y_train = np.array(scores)
        
        # 训练模型
        try:
            self.gp_model.fit(X_train, y_train)
            self.is_fitted = True
            logger.info("直觉模型训练完成。匠人已掌握当前数据的'手感'。")
        except Exception as e:
            logger.error(f"模型训练失败: {e}")
            self.is_fitted = False

    def _expected_improvement(self, x: np.ndarray) -> float:
        """
        辅助函数：计算期望增量。
        
        这是“匠人直觉”的数学表达。它衡量的是：在当前认知下，
        尝试某组参数比目前已知最好结果好多少的概率。
        """
        if not self.is_fitted:
            return 0.0
            
        x = x.reshape(1, -1)
        mu, sigma = self.gp_model.predict(x, return_std=True)
        
        # 找到当前记忆中的最佳分数
        y_max = np.max(self.memory.y)
        
        # EI 公式
        with np.errstate(divide='warn'):
            imp = mu - y_max
            Z = imp / sigma
            ei = imp * norm.cdf(Z) + sigma * norm.pdf(Z)
            ei[sigma == 0.0] = 0.0
            
        return ei[0]

    def consult_intuition(self, context_hints: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        核心函数 2: 咨询直觉。
        
        基于当前的经验模型，给出下一个最可能提升质量的参数组合建议。
        这不是随机搜索，而是基于模型的“预感”。
        
        参数:
            context_hints (Optional[Dict]): 上下文提示，可以固定某些参数的值。
            
        返回:
            Dict[str, float]: 建议的参数组合。
        """
        if not self.is_fitted or self.memory.X.shape[0] < 2:
            logger.warning("经验不足（样本过少或未训练），返回随机探索参数")
            return self._random_suggestion(context_hints)

        # 定义优化目标函数（负EI，因为scipy是最小化）
        def objective(x):
            return -self._expected_improvement(x)

        # 多起点优化，模拟匠人脑海中的多种可能性推演
        n_restarts = 10
        best_x = None
        best_ei = -np.inf
        
        # 确定哪些维度是固定的，哪些需要优化
        fixed_dims = {}
        if context_hints:
            for p_def in self.parameters:
                if p_def.name in context_hints:
                    # 这里简化处理：context_hints 暂时仅作为参考，不强制硬约束，
                    # 或者可以在初始化边界时处理。这里主要演示直觉搜索。
                    pass

        # 生成随机起点
        x_seeds = np.random.uniform(0, 1, size=(n_restarts, self.dim))
        
        # 将已知的最佳点也加入起点
        best_known_idx = np.argmax(self.memory.y)
        x_seeds[0] = self.memory.X[best_known_idx]

        bounds = [(0.0, 1.0)] * self.dim

        for x0 in x_seeds:
            res = minimize(
                objective,
                x0,
                bounds=bounds,
                method='L-BFGS-B'
            )
            if -res.fun > best_ei:
                best_ei = -res.fun
                best_x = res.x

        if best_x is None:
            return self._random_suggestion(context_hints)

        # 反归一化
        suggestion = {}
        for i, p_def in enumerate(self.parameters):
            raw_val = p_def.denormalize(best_x[i])
            # 对齐到定义的步长（匠人的手感精度）
            raw_val = round(raw_val / p_def.step) * p_def.step
            suggestion[p_def.name] = round(raw_val, 4)

        logger.info(f"直觉建议参数: {suggestion} (预测EI值: {best_ei:.4f})")
        return suggestion

    def _random_suggestion(self, hints: Optional[Dict] = None) -> Dict[str, float]:
        """纯随机建议，用于冷启动"""
        suggestion = {}
        for p in self.parameters:
            rand_val = np.random.uniform(p.min_val, p.max_val)
            suggestion[p.name] = round(rand_val, 2)
        return suggestion


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 1. 定义工艺参数（模拟烧制陶瓷的火候和湿度）
    # 火候: 800 - 1200 度
    # 湿度: 10% - 60%
    params_def = [
        CraftParameter(name="火候", min_val=800, max_val=1200, step=5),
        CraftParameter(name="湿度", min_val=0.1, max_val=0.6, step=0.01)
    ]

    # 2. 初始化模拟器
    artisan = ArtisanIntuitionSimulator(parameters=params_def)

    # 3. 模拟小样本历史数据（老匠人的几次成功与失败记录）
    # 假设最佳点在 1050度，湿度 0.35 左右
    history_samples = [
        {"火候": 900, "湿度": 0.2},
        {"火候": 1100, "湿度": 0.5},
        {"火候": 1000, "湿度": 0.3},
        {"火候": 1040, "湿度": 0.34}, # 接近最优
        {"火候": 950, "湿度": 0.6}
    ]
    # 模拟评分（越高越好，加入噪声模拟现实）
    history_scores = [60, 70, 80, 95, 65]

    # 4. 让AI学习这些小样本
    artisan.observe(history_samples, history_scores)

    # 5. 咨询直觉，获取下一步建议
    print("\n--- 匠人直觉咨询 ---")
    for i in range(3):
        suggestion = artisan.consult_intuition()
        print(f"第 {i+1} 次建议: {suggestion}")
        
    # 输出格式说明:
    # 建议结果为 Dict[str, float]，键为参数名，值为建议的浮点数。
    # 系统会自动根据 step 进行取整，模拟工匠的操作精度。