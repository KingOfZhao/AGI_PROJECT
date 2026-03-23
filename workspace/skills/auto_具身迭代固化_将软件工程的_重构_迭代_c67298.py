"""
CodeBrainCortex: 模拟生物认知系统的软件重构工具
结合神经可塑性(修改频率)与记忆固化(Bug分布)进行代码重构建议
"""

import logging
from typing import Dict, List, Tuple, Optional

class CodeBrainCortex:
    """
    模拟生物认知系统的软件重构工具
    通过分析代码修改频率(神经激活)和Bug分布(病理损伤)提出重构建议
    
    Attributes:
        activation_threshold (int): 激活强度阈值(默认10)
        bug_threshold (int): Bug数量阈值(默认5)
        repo_snapshot (Dict): 代码库快照 {文件路径: {'activation': 修改次数, 'bugs': Bug数量}}
    """
    
    def __init__(self, repo_snapshot: Dict, activation_threshold: int = 10, bug_threshold: int = 5):
        """
        初始化代码大脑皮层
        
        Args:
            repo_snapshot: 代码库快照字典
            activation_threshold: 激活强度阈值(神经激活)
            bug_threshold: Bug数量阈值(病理损伤)
            
        Raises:
            ValueError: 输入数据格式无效
        """
        self.activation_threshold = activation_threshold
        self.bug_threshold = bug_threshold
        self.repo_snapshot = self._validate_snapshot(repo_snapshot)
        self.suggestions: List[Dict] = []
        
    def _validate_snapshot(self, snapshot: Dict) -> Dict:
        """验证输入数据格式"""
        if not isinstance(snapshot, dict):
            raise ValueError("repo_snapshot必须是字典类型")
            
        for path, data in snapshot.items():
            if not isinstance(data, dict):
                raise ValueError(f"文件{path}的数据必须是字典")
            if 'activation' not in data or 'bugs' not in data:
                raise ValueError(f"文件{path}缺少activation或bugs字段")
            if not isinstance(data['activation'], (int, float)) or not isinstance(data['bugs'], (int, float)):
                raise ValueError(f"文件{path}的activation和bugs必须是数字")
                
        return snapshot
    
    def _classify_module(self, activation: float, bugs: float) -> str:
        """
        根据激活强度和Bug数量对模块进行分类
        
        Returns:
            str: 分类结果 ('myelination', 'bug_fix', 'pruning', 'stable')
        """
        if activation >= self.activation_threshold and bugs < self.bug_threshold:
            return "myelination"  # 髓鞘化：高频低Bug模块优化
        elif activation >= self.activation_threshold and bugs >= self.bug_threshold:
            return "bug_fix"      # 优先修复Bug
        elif activation < self.activation_threshold and bugs >= self.bug_threshold:
            return "pruning"      # 突触修剪：低频高Bug模块重构
        else:
            return "stable"       # 稳定模块：低频低Bug
    
    def _generate_suggestion(self, path: str, activation: float, bugs: float, classification: str) -> Dict:
        """生成具体重构建议"""
        suggestion = {
            "file_path": path,
            "classification": classification,
            "activation": activation,
            "bugs": bugs,
            "action": "",
            "reason": ""
        }
        
        if classification == "myelination":
            suggestion["action"] = "实施髓鞘化优化"
            suggestion["reason"] = f"高频激活(激活值{activation:.1f})且低Bug数量({bugs:.1f})：建议缓存优化、内联函数或预计算"
        elif classification == "bug_fix":
            suggestion["action"] = "优先修复Bug并重构"
            suggestion["reason"] = f"高频激活(激活值{activation:.1f})且高Bug数量({bugs:.1f})：存在严重认知障碍，需紧急修复"
        elif classification == "pruning":
            suggestion["action"] = "实施突触修剪"
            suggestion["reason"] = f"低频激活(激活值{activation:.1f})但高Bug数量({bugs:.1f})：建议删除或重构低效模块"
        else:
            suggestion["action"] = "维持现状"
            suggestion["reason"] = f"低频激活(激活值{activation:.1f})且低Bug数量({bugs:.1f})：模块状态稳定"
            
        return suggestion
    
    def analyze(self) -> List[Dict]:
        """
        分析代码库并生成重构建议
        
        Returns:
            List[Dict]: 重构建议列表，每个建议包含文件路径、分类、激活值、Bug数量、操作和原因
        """
        self.suggestions = []
        
        for path, data in self.repo_snapshot.items():
            activation = data['activation']
            bugs = data['bugs']
            classification = self._classify_module(activation, bugs)
            suggestion = self._generate_suggestion(path, activation, bugs, classification)
            self.suggestions.append(suggestion)
            
        return self.suggestions
    
    def get_myelination_candidates(self) -> List[Dict]:
        """获取髓鞘化优化候选模块"""
        return [s for s in self.suggestions if s["classification"] == "myelination"]
    
    def get_pruning_candidates(self) -> List[Dict]:
        """获取突触修剪候选模块"""
        return [s for s in self.suggestions if s["classification"] == "pruning"]
    
    def get_bug_fix_priority(self) -> List[Dict]:
        """获取Bug修复优先级模块"""
        return [s for s in self.suggestions if s["classification"] == "bug_fix"]
    
    def generate_report(self) -> str:
        """生成分析报告"""
        if not self.suggestions:
            return "未生成分析结果，请先调用analyze()方法"
            
        report = ["=== 代码大脑皮层分析报告 ===", ""]
        report.append(f"激活阈值: {self.activation_threshold}")
        report.append(f"Bug阈值: {self.bug_threshold}")
        report.append("")
        
        for suggestion in self.suggestions:
            report.append(f"文件: {suggestion['file_path']}")
            report.append(f"激活值: {suggestion['activation']:.1f} | Bug数量: {suggestion['bugs']:.1f}")
            report.append(f"建议操作: {suggestion['action']}")
            report.append(f"原因: {suggestion['reason']}")
            report.append("-" * 40)
            
        return "\n".join(report)


# 示例使用
if __name__ == "__main__":
    # 模拟代码库快照
    repo_data = {
        "core/auth.py": {"activation": 25.3, "bugs": 2.1},
        "utils/helpers.py": {"activation": 8.7, "bugs": 6.4},
        "models/data.py": {"activation": 32.1, "bugs": 12.8},
        "tests/unit.py": {"activation": 5.2, "bugs": 0.8},
        "api/v1/endpoints.py": {"activation": 18.9, "bugs": 4.3}
    }
    
    try:
        # 初始化代码大脑皮层
        cortex = CodeBrainCortex(repo_data, activation_threshold=15, bug_threshold=5)
        
        # 执行分析
        suggestions = cortex.analyze()
        
        # 获取特定建议
        myelination = cortex.get_myelination_candidates()
        pruning = cortex.get_pruning_candidates()
        bug_fix = cortex.get_bug_fix_priority()
        
        # 生成报告
        report = cortex.generate_report()
        print(report)
        
        # 输出特定建议
        print("\n=== 髓鞘化优化候选 ===")
        for item in myelination:
            print(f"{item['file_path']}: {item['action']}")
            
        print("\n=== 突触修剪候选 ===")
        for item in pruning:
            print(f"{item['file_path']}: {item['action']}")
            
        print("\n=== Bug修复优先级 ===")
        for item in bug_fix:
            print(f"{item['file_path']}: {item['action']}")
            
    except ValueError as e:
        logging.error(f"输入数据错误: {e}")
    except Exception as e:
        logging.error(f"分析过程中发生错误: {e}")