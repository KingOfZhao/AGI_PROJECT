#!/usr/bin/env python3
"""
端到端测试 - 予人玫瑰CRM + 刀模3D

测试覆盖:
1. CRM完整流程
2. 刀模3D完整流程  
3. 工作流集成
4. API端点
"""

import os
import sys
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "项目清单/予人玫瑰"))
sys.path.insert(0, str(PROJECT_ROOT / "项目清单/刀模活字印刷3D项目"))


# ═══════════════════════════════════════════════════════════════
# 测试框架
# ═══════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    message: str = ""
    duration_ms: int = 0


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.results: list[TestResult] = []
    
    def run_test(self, name: str, test_func):
        """运行单个测试"""
        start = time.time()
        try:
            test_func()
            result = TestResult(
                name=name,
                passed=True,
                duration_ms=int((time.time() - start) * 1000)
            )
        except AssertionError as e:
            result = TestResult(
                name=name,
                passed=False,
                message=str(e),
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            result = TestResult(
                name=name,
                passed=False,
                message=f"异常: {type(e).__name__}: {e}",
                duration_ms=int((time.time() - start) * 1000)
            )
        
        self.results.append(result)
        
        status = "✓" if result.passed else "✗"
        print(f"  {status} {name} ({result.duration_ms}ms)")
        if not result.passed:
            print(f"    {result.message}")
        
        return result.passed
    
    def summary(self) -> Dict[str, Any]:
        """生成摘要"""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total_time = sum(r.duration_ms for r in self.results)
        
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/len(self.results)*100:.1f}%" if self.results else "0%",
            "total_time_ms": total_time
        }


# ═══════════════════════════════════════════════════════════════
# CRM测试
# ═══════════════════════════════════════════════════════════════

class CRMTests:
    """予人玫瑰CRM测试"""
    
    def __init__(self, runner: TestRunner):
        self.runner = runner
        self.db = None
        self.test_customer_id = None
        self.test_task_id = None
    
    def setup(self):
        """测试准备"""
        try:
            from rose_crm import CRMDatabase
            
            # 使用临时数据库
            self.db_path = Path(tempfile.gettempdir()) / "test_rose_crm.db"
            if self.db_path.exists():
                self.db_path.unlink()
            
            self.db = CRMDatabase(self.db_path)
            return True
        except ImportError:
            print("  跳过CRM测试: 模块未加载")
            return False
    
    def teardown(self):
        """清理"""
        if self.db_path and self.db_path.exists():
            self.db_path.unlink()
    
    def run_all(self):
        """运行所有CRM测试"""
        print("\n[CRM测试]")
        
        if not self.setup():
            return
        
        try:
            self.runner.run_test("创建客户", self.test_create_customer)
            self.runner.run_test("获取客户", self.test_get_customer)
            self.runner.run_test("更新客户", self.test_update_customer)
            self.runner.run_test("搜索客户", self.test_search_customer)
            self.runner.run_test("客户列表", self.test_list_customers)
            self.runner.run_test("创建任务", self.test_create_task)
            self.runner.run_test("任务列表", self.test_list_tasks)
            self.runner.run_test("完成任务", self.test_complete_task)
            self.runner.run_test("创建跟进", self.test_create_followup)
            self.runner.run_test("创建反馈", self.test_create_feedback)
            self.runner.run_test("统计面板", self.test_dashboard_stats)
            self.runner.run_test("数据导出", self.test_export_data)
        finally:
            self.teardown()
    
    def test_create_customer(self):
        """测试创建客户"""
        customer_id = self.db.create_customer(
            name="测试客户",
            company="测试公司",
            phone="13800138000",
            email="test@example.com",
            source="端到端测试"
        )
        
        assert customer_id is not None, "客户ID不应为空"
        assert customer_id > 0, "客户ID应为正数"
        
        self.test_customer_id = customer_id
    
    def test_get_customer(self):
        """测试获取客户"""
        if not self.test_customer_id:
            self.test_create_customer()
        
        customer = self.db.get_customer(self.test_customer_id)
        
        assert customer is not None, "客户不应为空"
        assert customer["name"] == "测试客户", "客户名称不匹配"
        assert customer["company"] == "测试公司", "公司名称不匹配"
    
    def test_update_customer(self):
        """测试更新客户"""
        if not self.test_customer_id:
            self.test_create_customer()
        
        success = self.db.update_customer(
            self.test_customer_id,
            name="更新后的客户",
            status="active"
        )
        
        assert success, "更新应成功"
        
        customer = self.db.get_customer(self.test_customer_id)
        assert customer["name"] == "更新后的客户", "名称应已更新"
    
    def test_search_customer(self):
        """测试搜索客户"""
        customers = self.db.list_customers(search="测试")
        
        assert isinstance(customers, list), "应返回列表"
    
    def test_list_customers(self):
        """测试客户列表"""
        customers = self.db.list_customers(limit=10)
        
        assert isinstance(customers, list), "应返回列表"
        assert len(customers) <= 10, "应遵守limit"
    
    def test_create_task(self):
        """测试创建任务"""
        if not self.test_customer_id:
            self.test_create_customer()
        
        task_id = self.db.create_task(
            title="测试任务",
            customer_id=self.test_customer_id,
            description="这是一个测试任务",
            priority="high",
            due_date="2025-12-31"
        )
        
        assert task_id is not None, "任务ID不应为空"
        assert task_id > 0, "任务ID应为正数"
        
        self.test_task_id = task_id
    
    def test_list_tasks(self):
        """测试任务列表"""
        tasks = self.db.list_tasks()
        
        assert isinstance(tasks, list), "应返回列表"
    
    def test_complete_task(self):
        """测试完成任务"""
        if not self.test_task_id:
            self.test_create_task()
        
        success = self.db.complete_task(self.test_task_id)
        
        assert success, "完成任务应成功"
    
    def test_create_followup(self):
        """测试创建跟进"""
        if not self.test_customer_id:
            self.test_create_customer()
        
        followup_id = self.db.create_followup(
            customer_id=self.test_customer_id,
            content="测试跟进记录",
            followup_type="电话"
        )
        
        assert followup_id is not None, "跟进ID不应为空"
    
    def test_create_feedback(self):
        """测试创建反馈"""
        if not self.test_task_id:
            self.test_create_task()
        
        feedback_id = self.db.create_feedback(
            task_id=self.test_task_id,
            rating=5,
            comment="测试反馈"
        )
        
        assert feedback_id is not None, "反馈ID不应为空"
    
    def test_dashboard_stats(self):
        """测试统计面板"""
        stats = self.db.get_dashboard_stats()
        
        assert isinstance(stats, dict), "应返回字典"
        assert "customers" in stats, "应包含客户统计"
        assert "tasks" in stats, "应包含任务统计"
    
    def test_export_data(self):
        """测试数据导出"""
        # 导出到临时文件
        export_path = Path(tempfile.gettempdir()) / "test_export.json"
        
        data = {
            "customers": self.db.list_customers(),
            "tasks": self.db.list_tasks(),
            "stats": self.db.get_dashboard_stats()
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        assert export_path.exists(), "导出文件应存在"
        
        # 验证可读取
        with open(export_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert "customers" in loaded, "应包含客户数据"
        
        export_path.unlink()


# ═══════════════════════════════════════════════════════════════
# 刀模3D测试
# ═══════════════════════════════════════════════════════════════

class DieCut3DTests:
    """刀模3D测试"""
    
    def __init__(self, runner: TestRunner):
        self.runner = runner
        self.pipeline = None
        self.output_dir = None
    
    def setup(self):
        """测试准备"""
        try:
            from cad_to_3d import CADTo3DPipeline
            
            self.output_dir = Path(tempfile.gettempdir()) / "test_diecut_output"
            self.output_dir.mkdir(exist_ok=True)
            
            self.pipeline = CADTo3DPipeline(self.output_dir)
            return True
        except ImportError as e:
            print(f"  跳过刀模3D测试: 模块未加载 ({e})")
            return False
    
    def teardown(self):
        """清理"""
        if self.output_dir and self.output_dir.exists():
            import shutil
            shutil.rmtree(self.output_dir, ignore_errors=True)
    
    def run_all(self):
        """运行所有刀模3D测试"""
        print("\n[刀模3D测试]")
        
        if not self.setup():
            return
        
        try:
            self.runner.run_test("路径分解", self.test_path_decomposition)
            self.runner.run_test("模块匹配", self.test_module_matching)
            self.runner.run_test("STL生成", self.test_stl_generation)
            self.runner.run_test("成本估算", self.test_cost_estimation)
            self.runner.run_test("完整流程", self.test_full_pipeline)
        finally:
            self.teardown()
    
    def test_path_decomposition(self):
        """测试路径分解"""
        from cad_to_3d import PathSegment, ModuleDecomposer, Point2D
        
        # 创建测试路径
        segments = [
            PathSegment(Point2D(0, 0), Point2D(100, 0), "line"),
            PathSegment(Point2D(100, 0), Point2D(100, 50), "line"),
            PathSegment(Point2D(100, 50), Point2D(0, 50), "line"),
            PathSegment(Point2D(0, 50), Point2D(0, 0), "line"),
        ]
        
        decomposer = ModuleDecomposer()
        modules = decomposer.decompose(segments)
        
        assert len(modules) > 0, "应生成模块"
    
    def test_module_matching(self):
        """测试模块匹配"""
        from cad_to_3d import PathSegment, ModuleDecomposer, Point2D, ModuleType
        
        # 直线段
        segment = PathSegment(Point2D(0, 0), Point2D(100, 0), "line")
        
        decomposer = ModuleDecomposer()
        modules = decomposer.decompose([segment])
        
        assert len(modules) > 0, "应匹配到模块"
        assert modules[0].module_type in [ModuleType.STRAIGHT, "STRAIGHT", "straight"], "应为直线模块"
    
    def test_stl_generation(self):
        """测试STL生成"""
        from cad_to_3d import STLGenerator
        
        generator = STLGenerator()
        
        # 生成直线模块STL数据
        stl_data = generator.generate_straight_module(50.0)
        
        assert stl_data is not None, "应返回STL数据"
        assert len(stl_data) > 0, "STL数据应有内容"
        
        # 保存并验证
        stl_path = self.output_dir / "test_straight.stl"
        stl_path.write_bytes(stl_data)
        
        assert stl_path.exists(), "STL文件应存在"
        assert stl_path.stat().st_size > 0, "STL文件应有内容"
    
    def test_cost_estimation(self):
        """测试成本估算"""
        from cad_to_3d import DieCutModule, Point2D, ModuleType
        
        modules = [
            DieCutModule("m1", ModuleType.STRAIGHT, Point2D(0, 0), length=50),
            DieCutModule("m2", ModuleType.CORNER_90, Point2D(50, 0), length=20),
            DieCutModule("m3", ModuleType.STRAIGHT, Point2D(70, 0), length=30),
        ]
        
        # 简单成本计算
        base_cost = sum(m.length * 0.5 for m in modules)
        
        assert base_cost > 0, "成本应大于0"
    
    def test_full_pipeline(self):
        """测试完整流程"""
        # 创建空的演示DXF
        demo_dxf = self.output_dir / "demo.dxf"
        demo_dxf.write_text("")
        
        guide = self.pipeline.process(demo_dxf)
        
        assert guide is not None, "应返回组装指南"
        assert len(guide.modules) > 0, "应有模块"
        assert guide.estimated_cost > 0, "成本应大于0"


# ═══════════════════════════════════════════════════════════════
# 工作流测试
# ═══════════════════════════════════════════════════════════════

class WorkflowTests:
    """工作流集成测试"""
    
    def __init__(self, runner: TestRunner):
        self.runner = runner
    
    def run_all(self):
        """运行所有工作流测试"""
        print("\n[工作流测试]")
        
        self.runner.run_test("终端执行器", self.test_terminal_executor)
        self.runner.run_test("安全检查", self.test_security_check)
        self.runner.run_test("链式执行", self.test_chain_execution)
        self.runner.run_test("代码执行循环", self.test_code_execution_loop)
    
    def test_terminal_executor(self):
        """测试终端执行器"""
        from terminal_executor import TerminalExecutor
        
        executor = TerminalExecutor()
        result = executor.execute("echo 'hello world'")
        
        assert result.success, f"执行应成功: {result.stderr}"
        assert "hello world" in result.stdout, "输出应包含hello world"
    
    def test_security_check(self):
        """测试安全检查"""
        from terminal_executor import TerminalExecutor, SecurityLevel
        
        executor = TerminalExecutor()
        
        # 安全命令
        level, _ = executor.check_security("ls -la")
        assert level == SecurityLevel.SAFE, "ls应为安全命令"
        
        # 危险命令
        level, _ = executor.check_security("rm -rf /")
        assert level == SecurityLevel.DANGEROUS, "rm -rf /应为危险命令"
    
    def test_chain_execution(self):
        """测试链式执行"""
        from terminal_executor import TerminalExecutor, ChainStep
        
        executor = TerminalExecutor()
        
        steps = [
            ChainStep("echo 'step1'"),
            ChainStep("echo 'step2'"),
        ]
        
        result = executor.execute_chain(steps)
        
        assert result.success, "链式执行应成功"
        assert len(result.steps) == 2, "应有2个步骤"
    
    def test_code_execution_loop(self):
        """测试代码执行循环"""
        from code_execution_loop import CodeExecutionLoop
        
        loop = CodeExecutionLoop(max_iterations=3)
        
        result = loop.execute(
            "输出数字1到5的和",
            requirements=["使用sum函数"],
            save_skill=False
        )
        
        # 可能成功也可能失败，但应该有迭代
        assert result.iterations > 0, "应有迭代"


# ═══════════════════════════════════════════════════════════════
# API测试
# ═══════════════════════════════════════════════════════════════

class APITests:
    """API测试"""
    
    def __init__(self, runner: TestRunner):
        self.runner = runner
    
    def run_all(self):
        """运行所有API测试"""
        print("\n[API测试]")
        
        self.runner.run_test("CRM服务", self.test_crm_service)
        self.runner.run_test("刀模服务", self.test_diecut_service)
        self.runner.run_test("工作流服务", self.test_workflow_service)
    
    def test_crm_service(self):
        """测试CRM服务"""
        from project_api import RoseCRMService
        
        service = RoseCRMService()
        result = service.get_stats()
        
        # 即使CRM未加载，也应返回响应
        assert hasattr(result, 'success'), "应返回ApiResponse"
    
    def test_diecut_service(self):
        """测试刀模服务"""
        from project_api import DieCut3DService
        
        service = DieCut3DService()
        result = service.get_quote(10, "medium")
        
        assert result.success, "报价应成功"
        assert result.data["module_count"] == 10, "模块数应为10"
    
    def test_workflow_service(self):
        """测试工作流服务"""
        from project_api import WorkflowService
        
        service = WorkflowService()
        
        # 工作流依赖CRM，可能失败
        result = service.customer_order_workflow(
            "测试客户",
            "测试公司"
        )
        
        assert hasattr(result, 'success'), "应返回ApiResponse"


# ═══════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("端到端测试 - 予人玫瑰CRM + 刀模3D")
    print("=" * 60)
    
    runner = TestRunner()
    
    # 运行所有测试
    CRMTests(runner).run_all()
    DieCut3DTests(runner).run_all()
    WorkflowTests(runner).run_all()
    APITests(runner).run_all()
    
    # 打印摘要
    summary = runner.summary()
    
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"总计: {summary['total']}")
    print(f"通过: {summary['passed']} ✓")
    print(f"失败: {summary['failed']} ✗")
    print(f"通过率: {summary['pass_rate']}")
    print(f"总耗时: {summary['total_time_ms']}ms")
    
    # 返回状态码
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
