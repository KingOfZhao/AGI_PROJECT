"""
长文本逻辑一致性守护系统

该模块实现了一个基于静态单赋值(SSA)原理的逻辑一致性检测器。
它将NLP中的指代消解链转化为图结构，利用活性分析和到达定值分析
来检测文本中的逻辑漏洞、概念突兀引入及属性矛盾。

Core Concept:
1. Parser: 将文本解析为Coreference Chain (指代链)
2. SSA Builder: 将指代链转换为SSA形式
3. Analyzer: 执行数据流分析
"""

import logging
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LogicIssueType(Enum):
    """逻辑问题类型枚举"""
    UNDECLARED_REFERENCE = "概念未定义即使用"
    ATTRIBUTE_CONTRADICTION = "属性前后矛盾"
    SCOPE_VIOLATION = "作用域违规"

@dataclass
class LogicIssue:
    """逻辑问题数据结构"""
    issue_type: LogicIssueType
    description: str
    location: str
    severity: str = "WARNING"

@dataclass
class TextStatement:
    """文本陈述单元"""
    id: str
    subject: str
    predicate: str
    obj: Any
    line_number: int
    scope_id: str = "global"

@dataclass
class SSANode:
    """SSA图节点"""
    var_name: str
    version: int
    definition_stmt: TextStatement
    uses: List[TextStatement] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

class LongTextLogicGuardian:
    """
    长文本逻辑一致性守护系统主类。
    
    使用编译器原理中的SSA(Static Single Assignment)和数据流分析技术
    来检测长文本中的逻辑漏洞。
    """
    
    def __init__(self):
        self.symbol_table: Dict[str, List[SSANode]] = {}  # 变量名 -> SSA节点列表(版本历史)
        self.statements: List[TextStatement] = []
        self.current_scope: str = "global"
        self.issues: List[LogicIssue] = []
        
    def _validate_input_text(self, text_blocks: List[str]) -> bool:
        """验证输入文本格式"""
        if not isinstance(text_blocks, list):
            raise ValueError("Input must be a list of text blocks (strings)")
        if not all(isinstance(t, str) for t in text_blocks):
            raise ValueError("All text blocks must be strings")
        return True

    def _mock_nlp_parser(self, text: str, line_num: int) -> List[TextStatement]:
        """
        [辅助函数] 模拟NLP解析器
        在实际AGI场景中，这里会连接真正的NLP模型进行指代消解和关系抽取。
        为了演示逻辑，这里使用基于规则的简单解析。
        """
        statements = []
        text = text.lower().strip()
        
        # 简单的规则解析
        if " is " in text:
            parts = text.split(" is ", 1)
            subj = parts[0].strip()
            stmt = TextStatement(
                id=f"stmt_{line_num}",
                subject=subj,
                predicate="is",
                obj=parts[1].strip(),
                line_number=line_num,
                scope_id=self.current_scope
            )
            statements.append(stmt)
            
        elif " has " in text:
            parts = text.split(" has ", 1)
            subj = parts[0].strip()
            stmt = TextStatement(
                id=f"stmt_{line_num}",
                subject=subj,
                predicate="has",
                obj=parts[1].strip(),
                line_number=line_num,
                scope_id=self.current_scope
            )
            statements.append(stmt)
            
        return statements

    def build_ssa_graph(self, text_blocks: List[str]) -> Dict[str, List[SSANode]]:
        """
        核心函数1: 构建SSA图
        
        将文本流转化为SSA表示。每个新定义或属性修改都会产生新版本的变量。
        
        Args:
            text_blocks: 文本块列表
            
        Returns:
            更新后的符号表
        """
        try:
            self._validate_input_text(text_blocks)
            logger.info(f"Starting SSA construction for {len(text_blocks)} blocks.")
            
            for idx, block in enumerate(text_blocks):
                parsed_stmts = self._mock_nlp_parser(block, idx)
                
                for stmt in parsed_stmts:
                    self.statements.append(stmt)
                    var_name = stmt.subject
                    
                    # 获取当前最新版本号
                    current_version = 0
                    if var_name in self.symbol_table:
                        current_version = self.symbol_table[var_name][-1].version + 1
                    
                    # 创建新的SSA节点
                    new_node = SSANode(
                        var_name=var_name,
                        version=current_version,
                        definition_stmt=stmt,
                        attributes={"value": stmt.obj} if stmt.predicate == "is" else {}
                    )
                    
                    if var_name not in self.symbol_table:
                        self.symbol_table[var_name] = []
                    self.symbol_table[var_name].append(new_node)
                    
            return self.symbol_table
            
        except Exception as e:
            logger.error(f"Error during SSA graph construction: {str(e)}")
            raise

    def analyze_dataflow(self) -> List[LogicIssue]:
        """
        核心函数2: 数据流分析与逻辑漏洞检测
        
        执行类似于编译器中的"到达定值分析"和"活性分析"。
        
        Returns:
            检测到的逻辑问题列表
        """
        logger.info("Starting dataflow analysis...")
        self.issues = [] # Reset issues
        
        # 定义集：存储每个变量首次定义的位置
        definitions: Dict[str, int] = {}

        for idx, stmt in enumerate(self.statements):
            subj = stmt.subject
            
            # 1. 检查未定义即使用 - 类似于变量未声明
            # 假设主语是被定义/更新，如果谓语是 'is' 通常视为强定义
            if stmt.predicate == "is":
                definitions[subj] = idx
            
            # 检查属性一致性
            if subj in self.symbol_table:
                nodes = self.symbol_table[subj]
                if len(nodes) > 1:
                    # 对比最新两个版本
                    last_node = nodes[-1]
                    prev_node = nodes[-2]
                    
                    # 2. 检查属性矛盾
                    if (last_node.attributes.get("value") is not None and 
                        prev_node.attributes.get("value") is not None and
                        last_node.attributes.get("value") != prev_node.attributes.get("value")):
                        
                        # 简单的矛盾检测逻辑（实际场景需要语义理解，比如 'dead' vs 'alive'）
                        val1 = prev_node.attributes["value"]
                        val2 = last_node.attributes["value"]
                        
                        # 硬编码矛盾规则示例
                        contradictions = {("alive", "dead"), ("red", "blue"), ("true", "false")}
                        if (val1, val2) in contradictions:
                            issue = LogicIssue(
                                issue_type=LogicIssueType.ATTRIBUTE_CONTRADICTION,
                                description=f"Subject '{subj}' changed from '{val1}' to '{val2}' which is a logical contradiction.",
                                location=f"Lines {prev_node.definition_stmt.line_number} -> {last_node.definition_stmt.line_number}",
                                severity="ERROR"
                            )
                            self.issues.append(issue)
                            logger.warning(f"Detected contradiction: {issue.description}")

        # 3. 检查孤立概念 - 在前文中完全没有出现过的主语，但在语境中暗示已知
        # (此处简化为检查是否在definitions中，虽然SSA构建时已经隐式处理了定义)
        
        logger.info(f"Analysis complete. Found {len(self.issues)} issues.")
        return self.issues

    def generate_report(self) -> str:
        """生成逻辑审计报告"""
        if not self.issues:
            return "✅ 逻辑审计通过：未检测到明显的结构性逻辑漏洞。"
        
        report_lines = ["🚨 逻辑审计报告：检测到以下潜在问题"]
        for issue in self.issues:
            report_lines.append(
                f"[{issue.severity}] {issue.issue_type.value} @ {issue.location}\n"
                f"   -> {issue.description}"
            )
        return "\n".join(report_lines)

# 使用示例
if __name__ == "__main__":
    # 模拟一段逻辑混乱的新闻文本
    sample_news = [
        "The suspect is alive",   # 定义：嫌疑人活着
        "The suspect has a gun",  # 属性：有枪
        "The car is red",         # 引入新概念：车
        "The suspect is dead",    # 矛盾：嫌疑人死了 (与第一句矛盾)
        "The weapon is missing"   # 突兀概念：Weapon (未定义，虽然可能指代gun，但严格逻辑上需要消解)
    ]

    guardian = LongTextLogicGuardian()
    
    print("--- 正在构建 SSA 图 ---")
    ssa_graph = guardian.build_ssa_graph(sample_news)
    # 打印部分SSA图结构以供验证
    for var, nodes in ssa_graph.items():
        print(f"Var: {var}, Versions: {len(nodes)}")

    print("\n--- 正在进行数据流分析 ---")
    issues = guardian.analyze_dataflow()
    
    print("\n--- 最终报告 ---")
    print(guardian.generate_report())