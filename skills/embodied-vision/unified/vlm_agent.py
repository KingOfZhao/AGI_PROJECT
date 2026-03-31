#!/usr/bin/env python3
"""
embodied-vision VLM-Driven Agent Pipeline

核心思想: VLM(视觉语言模型)不是额外的分析步骤, 而是**决策核心**。

传统Pipeline: 图像 → CV算法 → 规则分类 → 输出
Agent Pipeline: 图像 → VLM理解 → 决策 → CV执行 → VLM验证 → 输出

关键区别:
- 传统: CV是主体, VLM是辅助
- Agent: VLM是主体, CV是工具
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any


# ═══════════════════════════════════════════
# Agent决策协议
# ═══════════════════════════════════════════

@dataclass
class AgentDecision:
    """Agent决策"""
    step: str  # what/where/when/how
    action: str  # 具体动作
    params: Dict = field(default_factory=dict)
    confidence: float = 0.0
    reason: str = ""


@dataclass 
class AgentObservation:
    """Agent观察"""
    timestamp: str
    image_path: str
    cv_features: Dict = field(default_factory=dict)  # CV提供的事实
    vlm_understanding: Dict = field(default_factory=dict)  # VLM提供语义
    quality_score: float = 0.0


@dataclass
class AgentPipelineResult:
    """Agent Pipeline完整结果"""
    decisions: List[AgentDecision] = field(default_factory=list)
    observations: List[AgentObservation] = field(default_factory=list)
    final_output: Dict = field(default_factory=dict)
    total_steps: int = 0
    duration_ms: float = 0.0
    success: bool = False


class VisionAgent:
    """
    VLM-Driven Vision Agent
    
    使用方式:
      agent = VisionAgent()
      result = agent.process("photo.jpg")
      # Agent自主决定: 用什么参数处理, 输出什么格式, 是否需要重试
    """
    
    def __init__(self):
        self.history: List[AgentPipelineResult] = []
        self.max_retries = 3
        self.min_quality_score = 60.0
    
    def process(self, image_path: str, 
                task: str = "diepre") -> AgentPipelineResult:
        """
        处理图像 (Agent自主决策模式)
        
        task: "diepre" (刀模分析) / "scene" (场景理解) / "grasp" (抓取规划)
        """
        t0 = time.time()
        result = AgentPipelineResult()
        
        # === Step 1: 观察 (CV特征提取) ===
        obs1 = self._observe(image_path)
        result.observations.append(obs1)
        
        # === Step 2: VLM理解 (需要Agent调用VLM) ===
        obs2 = self._vlm_understand(image_path, task)
        result.observations.append(obs2)
        
        # === Step 3: 决策 (Agent根据观察+理解做决策) ===
        decisions = self._decide(obs1, obs2, task)
        result.decisions = decisions
        
        # === Step 4: 执行 (用CV工具执行决策) ===
        for i, decision in enumerate(decisions):
            exec_result = self._execute(image_path, decision)
            
            # === Step 5: 验证 (评估输出质量) ===
            if exec_result and "output_path" in exec_result:
                quality = self._evaluate_output(exec_result["output_path"])
                
                # === Step 6: 反馈循环 (质量不够→调整参数→重试) ===
                retry = 0
                while quality < self.min_quality_score and retry < self.max_retries:
                    adjustment = self._adjust_params(decision, quality, retry)
                    exec_result = self._execute(image_path, adjustment)
                    if exec_result and "output_path" in exec_result:
                        quality = self._evaluate_output(exec_result["output_path"])
                    retry += 1
                
                if quality >= self.min_quality_score:
                    result.final_output = exec_result
                    result.success = True
        
        result.total_steps = len(decisions)
        result.duration_ms = (time.time() - t0) * 1000
        self.history.append(result)
        
        return result
    
    def _observe(self, image_path: str) -> AgentObservation:
        """CV特征提取 (观察阶段)"""
        import cv2
        import numpy as np
        
        obs = AgentObservation(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            image_path=image_path,
        )
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                return obs
            
            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 快速特征
            v = np.median(gray)
            edge = cv2.Canny(gray, max(0, 0.7*v), min(255, 1.3*v))
            
            obs.cv_features = {
                "size": (w, h),
                "brightness": float(np.mean(gray)),
                "contrast": float(np.std(gray)),
                "edge_density": float(cv2.countNonZero(edge) / (h*w)),
                "is_landscape": w > h,
                "aspect_ratio": round(w / max(h, 1), 2),
                "is_color": len(img.shape) == 3,
            }
        except Exception as e:
            obs.cv_features["error"] = str(e)
        
        return obs
    
    def _vlm_understand(self, image_path: str, task: str) -> AgentObservation:
        """VLM语义理解 (需要Agent实际调用VLM)"""
        obs = AgentObservation(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            image_path=image_path,
        )
        
        # VLM prompt根据task不同
        if task == "diepre":
            obs.vlm_understanding = {
                "task": "diepre",
                "prompt": "分析这张刀模展开图: 1)FEFCO类型 2)印刷内容 3)材质 4)翼片结构",
                "status": "pending_vlm_call",
                "expected_output": {
                    "fefco_type": "0215",
                    "material": "kraft",
                    "printed_text": [],
                    "flap_structure": "tuck-top",
                }
            }
        elif task == "scene":
            obs.vlm_understanding = {
                "task": "scene",
                "prompt": "描述场景中的物体、空间关系、可执行操作",
                "status": "pending_vlm_call",
            }
        elif task == "grasp":
            obs.vlm_understanding = {
                "task": "grasp",
                "prompt": "识别可抓取物体, 建议抓取点和方向",
                "status": "pending_vlm_call",
            }
        
        return obs
    
    def _decide(self, obs_cv: AgentObservation, obs_vlm: AgentObservation,
                task: str) -> List[AgentDecision]:
        """Agent决策: 根据观察+理解决定如何处理"""
        decisions = []
        cv = obs_cv.cv_features
        vlm = obs_vlm.vlm_understanding
        
        if task == "diepre":
            # 决策1: 前景提取参数
            brightness = cv.get("brightness", 128)
            contrast = cv.get("contrast", 50)
            
            if brightness > 150:
                otsu_bias = -20  # 偏亮图像降低阈值
            elif brightness < 100:
                otsu_bias = 20  # 偏暗图像提高阈值
            else:
                otsu_bias = 0
            
            decisions.append(AgentDecision(
                step="foreground_extraction",
                action="adaptive_threshold",
                params={"otsu_bias": otsu_bias},
                confidence=0.85,
                reason=f"亮度={brightness:.0f}, 对比度={contrast:.0f}, 偏移={otsu_bias}"
            ))
            
            # 决策2: 印刷过滤策略
            edge_density = cv.get("edge_density", 0.1)
            if edge_density > 0.2:
                filter_strength = "aggressive"  # 边缘密集→强过滤
            elif edge_density > 0.1:
                filter_strength = "moderate"
            else:
                filter_strength = "mild"
            
            decisions.append(AgentDecision(
                step="print_filtering",
                action="mser_inpainting",
                params={"strength": filter_strength, "min_area": 30 if filter_strength == "aggressive" else 50},
                confidence=0.8,
                reason=f"边缘密度={edge_density:.3f}, 过滤强度={filter_strength}"
            ))
            
            # 决策3: 线条提取参数
            decisions.append(AgentDecision(
                step="line_extraction",
                action="adaptive_binary",
                params={
                    "block_size": 21,
                    "C": 5 if contrast > 40 else 10,
                },
                confidence=0.75,
                reason=f"对比度={contrast:.0f}, C参数自适应"
            ))
            
            # 决策4: 分类阈值 (基于VLM识别的FEFCO类型)
            fefco = vlm.get("expected_output", {}).get("fefco_type", "0201")
            if fefco in ("0215", "0216"):
                # tuck-top: 压痕线较多
                width_threshold = "median"
            elif fefco in ("0200", "0201"):
                # RSC: 刀线压痕比例接近
                width_threshold = "histogram_valley"
            else:
                width_threshold = "median"
            
            decisions.append(AgentDecision(
                step="line_classification",
                action="width_based",
                params={"threshold_method": width_threshold},
                confidence=0.7,
                reason=f"FEFCO={fefco}, 阈值方法={width_threshold}"
            ))
        
        return decisions
    
    def _execute(self, image_path: str, decision: AgentDecision) -> Optional[Dict]:
        """执行决策 (调用CV工具)"""
        # 这里应该调用实际的Pipeline
        # 简化版: 返回预期输出路径
        return {
            "decision": decision.action,
            "params": decision.params,
            "output_path": f"/tmp/agent_output_{decision.step}.png",
            "status": "executed"
        }
    
    def _evaluate_output(self, output_path: str) -> float:
        """评估输出质量"""
        import cv2
        import numpy as np
        
        img = cv2.imread(output_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0
        
        h, w = img.shape
        
        bg = np.sum(img > 200) / (h * w)
        lines = np.sum(img < 50) / (h * w)
        noise = np.sum((img >= 50) & (img <= 200)) / (h * w)
        
        score = bg * 30 + min(lines, 0.3) / 0.3 * 30 + (1 - noise) * 20 + 20
        return min(score, 100)
    
    def _adjust_params(self, decision: AgentDecision, 
                       quality: float, retry: int) -> AgentDecision:
        """根据质量反馈调整参数"""
        new_params = decision.params.copy()
        
        # 简单调整策略
        if quality < 40:
            # 质量很低: 大幅调整
            factor = 1.5
        elif quality < 60:
            # 质量中等: 中等调整
            factor = 1.2
        else:
            # 质量接近目标: 小幅调整
            factor = 1.05
        
        # 根据step类型调整不同参数
        if "block_size" in new_params:
            new_val = new_params["block_size"] * (factor if retry % 2 == 0 else 1/factor)
            new_params["block_size"] = max(11, min(41, new_val))
        
        if "C" in new_params:
            new_params["C"] = new_params["C"] * factor
        
        if "min_area" in new_params:
            new_params["min_area"] = max(10, new_params["min_area"] * (1/factor))
        
        return AgentDecision(
            step=decision.step,
            action=decision.action,
            params=new_params,
            confidence=decision.confidence * 0.9,  # 每次重试置信度略降
            reason=f"重试{retry+1}, 质量={quality:.0f}, 因子={factor}"
        )
    
    def get_performance_summary(self) -> Dict:
        """获取历史性能摘要"""
        if not self.history:
            return {"total_runs": 0}
        
        successful = [r for r in self.history if r.success]
        return {
            "total_runs": len(self.history),
            "successful": len(successful),
            "success_rate": len(successful) / len(self.history),
            "avg_duration_ms": sum(r.duration_ms for r in self.history) / len(self.history),
            "avg_quality": 0,  # 需要实际评估
        }


# ═══════════════════════════════════════════
# DiePre Agent (具体任务)
# ═══════════════════════════════════════════

class DiePreAgent(VisionAgent):
    """
    DiePre专用Agent
    继承VisionAgent, 专门处理刀模展开图
    """
    
    def process(self, image_path: str, task: str = "diepre") -> AgentPipelineResult:
        """DiePre专用处理流程"""
        result = super().process(image_path, task="diepre")
        
        # 添加DiePre专用决策
        obs = result.observations[0] if result.observations else None
        if obs and obs.cv_features:
            cv = obs.cv_features
            
            # 检查是否需要透视矫正
            if cv.get("aspect_ratio", 1.0) > 1.5 or cv.get("aspect_ratio", 1.0) < 0.67:
                result.decisions.insert(0, AgentDecision(
                    step="perspective_correction",
                    action="auto_correct",
                    params={"method": "convex_hull"},
                    confidence=0.9,
                    reason=f"长宽比={cv['aspect_ratio']}, 需要矫正"
                ))
        
        return result


if __name__ == "__main__":
    import sys
    
    path = sys.argv[1] if len(sys.argv) > 1 else "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg"
    
    agent = DiePreAgent()
    result = agent.process(path)
    
    print(f"=== VLM-Driven Agent Pipeline ===")
    print(f"  耗时: {result.duration_ms:.0f}ms")
    print(f"  步骤: {result.total_steps}")
    print(f"  成功: {result.success}")
    print(f"\n  观察:")
    for i, obs in enumerate(result.observations):
        print(f"    [{i}] CV特征: {list(obs.cv_features.keys())}")
        if obs.vlm_understanding:
            print(f"    [{i}] VLM: {obs.vlm_understanding.get('task', 'N/A')}")
    
    print(f"\n  决策:")
    for d in result.decisions:
        print(f"    {d.step}: {d.action} (置信={d.confidence:.2f})")
        print(f"      参数: {d.params}")
        print(f"      原因: {d.reason}")
    
    perf = agent.get_performance_summary()
    print(f"\n  性能: {perf}")
    
    print(f"\n✅ Agent Pipeline测试完成")
