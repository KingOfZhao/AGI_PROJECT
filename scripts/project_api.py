#!/usr/bin/env python3
"""
项目API集成 - 予人玫瑰CRM + 刀模3D的统一API

端点:
- /api/rose/*  - CRM API
- /api/diecut/* - 刀模3D API
- /api/workflow/* - 自动化工作流
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "项目清单/予人玫瑰"))
sys.path.insert(0, str(PROJECT_ROOT / "项目清单/刀模活字印刷3D项目"))

# Flask
try:
    from flask import Flask, request, jsonify, send_file
    from werkzeug.utils import secure_filename
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    Flask = None

# 导入项目模块
try:
    from rose_crm import CRMDatabase
    HAS_CRM = True
except ImportError:
    HAS_CRM = False
    CRMDatabase = None

try:
    from cad_to_3d import CADTo3DPipeline, DXFParser, ModuleDecomposer
    HAS_DIECUT = True
except ImportError:
    HAS_DIECUT = False
    CADTo3DPipeline = None


# ═══════════════════════════════════════════════════════════════
# 响应模型
# ═══════════════════════════════════════════════════════════════

@dataclass
class ApiResponse:
    """统一API响应"""
    success: bool
    data: Any = None
    message: str = ""
    errors: List[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "errors": self.errors or [],
            "timestamp": datetime.now().isoformat()
        }


# ═══════════════════════════════════════════════════════════════
# 服务层
# ═══════════════════════════════════════════════════════════════

class RoseCRMService:
    """予人玫瑰CRM服务"""
    
    def __init__(self):
        if HAS_CRM:
            db_path = PROJECT_ROOT / "项目清单/予人玫瑰/rose_crm.db"
            self.db = CRMDatabase(db_path)
        else:
            self.db = None
    
    def list_customers(self, status: str = None, search: str = None, 
                       limit: int = 100) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        customers = self.db.list_customers(status=status, search=search, limit=limit)
        return ApiResponse(True, data=customers, message=f"找到 {len(customers)} 个客户")
    
    def get_customer(self, customer_id: int) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        customer = self.db.get_customer(customer_id)
        if not customer:
            return ApiResponse(False, message="客户不存在")
        return ApiResponse(True, data=customer)
    
    def create_customer(self, name: str, **kwargs) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        try:
            customer_id = self.db.create_customer(name, **kwargs)
            return ApiResponse(True, data={"id": customer_id}, message="客户创建成功")
        except Exception as e:
            return ApiResponse(False, errors=[str(e)])
    
    def update_customer(self, customer_id: int, **kwargs) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        if self.db.update_customer(customer_id, **kwargs):
            return ApiResponse(True, message="客户更新成功")
        return ApiResponse(False, message="更新失败")
    
    def delete_customer(self, customer_id: int) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        if self.db.delete_customer(customer_id):
            return ApiResponse(True, message="客户已删除")
        return ApiResponse(False, message="删除失败")
    
    def list_tasks(self, status: str = None, customer_id: int = None) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        tasks = self.db.list_tasks(status=status, customer_id=customer_id)
        return ApiResponse(True, data=tasks, message=f"找到 {len(tasks)} 个任务")
    
    def create_task(self, title: str, customer_id: int = None, **kwargs) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        try:
            task_id = self.db.create_task(title, customer_id, **kwargs)
            return ApiResponse(True, data={"id": task_id}, message="任务创建成功")
        except Exception as e:
            return ApiResponse(False, errors=[str(e)])
    
    def complete_task(self, task_id: int) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        if self.db.complete_task(task_id):
            return ApiResponse(True, message="任务已完成")
        return ApiResponse(False, message="操作失败")
    
    def get_stats(self) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        stats = self.db.get_dashboard_stats()
        return ApiResponse(True, data=stats)
    
    def create_followup(self, customer_id: int, content: str, **kwargs) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        try:
            followup_id = self.db.create_followup(customer_id, content, **kwargs)
            return ApiResponse(True, data={"id": followup_id}, message="跟进记录创建成功")
        except Exception as e:
            return ApiResponse(False, errors=[str(e)])
    
    def create_feedback(self, task_id: int, rating: int, comment: str = None) -> ApiResponse:
        if not self.db:
            return ApiResponse(False, errors=["CRM模块未加载"])
        
        try:
            feedback_id = self.db.create_feedback(task_id, rating, comment)
            return ApiResponse(True, data={"id": feedback_id}, message="反馈提交成功")
        except Exception as e:
            return ApiResponse(False, errors=[str(e)])


class DieCut3DService:
    """刀模3D服务"""
    
    def __init__(self):
        self.output_dir = PROJECT_ROOT / "项目清单/刀模活字印刷3D项目/output"
        self.output_dir.mkdir(exist_ok=True)
        
        if HAS_DIECUT:
            self.pipeline = CADTo3DPipeline(self.output_dir)
        else:
            self.pipeline = None
    
    def analyze_design(self, file_path: Path) -> ApiResponse:
        """分析设计文件"""
        if not file_path.exists():
            return ApiResponse(False, errors=["文件不存在"])
        
        # 获取文件信息
        stat = file_path.stat()
        
        # 简单分析
        analysis = {
            "file_name": file_path.name,
            "file_size": stat.st_size,
            "format": file_path.suffix[1:].upper(),
            "dimensions": {
                "width_mm": 300.0,  # 演示值
                "height_mm": 200.0,
            },
            "complexity": "medium",
            "estimated_modules": 10,
            "estimated_cost": 70.0
        }
        
        return ApiResponse(True, data=analysis, message="分析完成")
    
    def generate_modules(self, file_path: Path = None, demo: bool = False) -> ApiResponse:
        """生成模块"""
        if not self.pipeline:
            return ApiResponse(False, errors=["刀模3D模块未加载"])
        
        try:
            if demo or not file_path:
                # 演示模式
                demo_file = self.output_dir.parent / "demo.dxf"
                demo_file.write_text("")  # 空文件触发演示路径
                guide = self.pipeline.process(demo_file)
            else:
                guide = self.pipeline.process(file_path)
            
            return ApiResponse(True, data={
                "total_modules": len(guide.modules),
                "module_count": guide.module_count,
                "estimated_cost": guide.estimated_cost,
                "stl_files": guide.stl_files,
                "notes": guide.notes
            }, message="模块生成完成")
        except Exception as e:
            return ApiResponse(False, errors=[str(e)])
    
    def get_quote(self, module_count: int, complexity: str = "medium") -> ApiResponse:
        """获取报价"""
        # 基础成本
        base_cost_per_module = {
            "simple": 5,
            "medium": 7,
            "complex": 10
        }
        
        cost = module_count * base_cost_per_module.get(complexity, 7)
        
        # 加价策略
        markup = 1.5 if module_count < 20 else 1.3
        price = cost * markup
        
        return ApiResponse(True, data={
            "module_count": module_count,
            "complexity": complexity,
            "material_cost": cost,
            "labor_cost": module_count * 2,
            "total_cost": cost + module_count * 2,
            "price": price,
            "markup": markup,
            "profit_margin": (price - cost) / price * 100
        }, message="报价生成完成")
    
    def list_stl_files(self) -> ApiResponse:
        """列出STL文件"""
        stl_files = list(self.output_dir.glob("*.stl"))
        
        files = []
        for f in stl_files:
            files.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        
        return ApiResponse(True, data=files, message=f"找到 {len(files)} 个STL文件")


class WorkflowService:
    """工作流服务"""
    
    def __init__(self):
        self.crm = RoseCRMService()
        self.diecut = DieCut3DService()
    
    def customer_order_workflow(self, 
                                customer_name: str,
                                company: str,
                                cad_file: Path = None) -> ApiResponse:
        """客户下单工作流"""
        
        workflow_result = {
            "steps": [],
            "customer": None,
            "modules": None,
            "quote": None,
            "task": None
        }
        
        # Step 1: 创建客户
        step1 = self.crm.create_customer(customer_name, company=company)
        workflow_result["steps"].append({
            "step": "create_customer",
            "success": step1.success,
            "message": step1.message
        })
        
        if not step1.success:
            return ApiResponse(False, data=workflow_result, 
                             errors=["创建客户失败"] + (step1.errors or []))
        
        customer_id = step1.data["id"]
        workflow_result["customer"] = {"id": customer_id, "name": customer_name}
        
        # Step 2: 生成刀模模块
        step2 = self.diecut.generate_modules(cad_file, demo=(cad_file is None))
        workflow_result["steps"].append({
            "step": "generate_modules",
            "success": step2.success,
            "message": step2.message
        })
        
        if not step2.success:
            return ApiResponse(False, data=workflow_result,
                             errors=["模块生成失败"] + (step2.errors or []))
        
        workflow_result["modules"] = step2.data
        
        # Step 3: 生成报价
        step3 = self.diecut.get_quote(step2.data["total_modules"])
        workflow_result["steps"].append({
            "step": "generate_quote",
            "success": step3.success,
            "message": step3.message
        })
        
        workflow_result["quote"] = step3.data
        
        # Step 4: 创建任务
        step4 = self.crm.create_task(
            f"刀模订单 - {customer_name}",
            customer_id,
            description=f"模块数: {step2.data['total_modules']}, 报价: ¥{step3.data['price']:.2f}",
            priority="high"
        )
        workflow_result["steps"].append({
            "step": "create_task",
            "success": step4.success,
            "message": step4.message
        })
        
        if step4.success:
            workflow_result["task"] = {"id": step4.data["id"]}
        
        return ApiResponse(True, data=workflow_result, message="工作流执行完成")


# ═══════════════════════════════════════════════════════════════
# Flask API
# ═══════════════════════════════════════════════════════════════

def create_app() -> Optional[Flask]:
    """创建Flask应用"""
    if not HAS_FLASK:
        return None
    
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
    
    crm_service = RoseCRMService()
    diecut_service = DieCut3DService()
    workflow_service = WorkflowService()
    
    # ── Rose CRM API ──
    
    @app.route("/api/rose/customers", methods=["GET"])
    def list_customers():
        result = crm_service.list_customers(
            status=request.args.get("status"),
            search=request.args.get("search"),
            limit=int(request.args.get("limit", 100))
        )
        return jsonify(result.to_dict())
    
    @app.route("/api/rose/customers/<int:customer_id>", methods=["GET"])
    def get_customer(customer_id):
        result = crm_service.get_customer(customer_id)
        return jsonify(result.to_dict())
    
    @app.route("/api/rose/customers", methods=["POST"])
    def create_customer():
        data = request.get_json() or {}
        if not data.get("name"):
            return jsonify(ApiResponse(False, errors=["名称必填"]).to_dict()), 400
        
        result = crm_service.create_customer(**data)
        return jsonify(result.to_dict()), 201 if result.success else 400
    
    @app.route("/api/rose/customers/<int:customer_id>", methods=["PUT"])
    def update_customer(customer_id):
        data = request.get_json() or {}
        result = crm_service.update_customer(customer_id, **data)
        return jsonify(result.to_dict())
    
    @app.route("/api/rose/customers/<int:customer_id>", methods=["DELETE"])
    def delete_customer(customer_id):
        result = crm_service.delete_customer(customer_id)
        return jsonify(result.to_dict())
    
    @app.route("/api/rose/tasks", methods=["GET"])
    def list_tasks():
        result = crm_service.list_tasks(
            status=request.args.get("status"),
            customer_id=request.args.get("customer_id", type=int)
        )
        return jsonify(result.to_dict())
    
    @app.route("/api/rose/tasks", methods=["POST"])
    def create_task():
        data = request.get_json() or {}
        if not data.get("title"):
            return jsonify(ApiResponse(False, errors=["标题必填"]).to_dict()), 400
        
        result = crm_service.create_task(**data)
        return jsonify(result.to_dict()), 201 if result.success else 400
    
    @app.route("/api/rose/tasks/<int:task_id>/complete", methods=["POST"])
    def complete_task(task_id):
        result = crm_service.complete_task(task_id)
        return jsonify(result.to_dict())
    
    @app.route("/api/rose/stats", methods=["GET"])
    def get_stats():
        result = crm_service.get_stats()
        return jsonify(result.to_dict())
    
    @app.route("/api/rose/followups", methods=["POST"])
    def create_followup():
        data = request.get_json() or {}
        if not data.get("customer_id") or not data.get("content"):
            return jsonify(ApiResponse(False, errors=["customer_id和content必填"]).to_dict()), 400
        
        result = crm_service.create_followup(**data)
        return jsonify(result.to_dict()), 201 if result.success else 400
    
    @app.route("/api/rose/feedbacks", methods=["POST"])
    def create_feedback():
        data = request.get_json() or {}
        if not data.get("task_id") or not data.get("rating"):
            return jsonify(ApiResponse(False, errors=["task_id和rating必填"]).to_dict()), 400
        
        result = crm_service.create_feedback(**data)
        return jsonify(result.to_dict()), 201 if result.success else 400
    
    # ── DieCut 3D API ──
    
    @app.route("/api/diecut/analyze", methods=["POST"])
    def analyze_design():
        if "file" not in request.files:
            return jsonify(ApiResponse(False, errors=["没有上传文件"]).to_dict()), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify(ApiResponse(False, errors=["文件名为空"]).to_dict()), 400
        
        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_path = Path(tempfile.gettempdir()) / filename
        file.save(str(temp_path))
        
        result = diecut_service.analyze_design(temp_path)
        return jsonify(result.to_dict())
    
    @app.route("/api/diecut/generate", methods=["POST"])
    def generate_modules():
        data = request.get_json() or {}
        demo = data.get("demo", True)
        file_path = Path(data["file_path"]) if data.get("file_path") else None
        
        result = diecut_service.generate_modules(file_path, demo=demo)
        return jsonify(result.to_dict())
    
    @app.route("/api/diecut/quote", methods=["POST"])
    def get_quote():
        data = request.get_json() or {}
        if not data.get("module_count"):
            return jsonify(ApiResponse(False, errors=["module_count必填"]).to_dict()), 400
        
        result = diecut_service.get_quote(
            data["module_count"],
            data.get("complexity", "medium")
        )
        return jsonify(result.to_dict())
    
    @app.route("/api/diecut/stl", methods=["GET"])
    def list_stl():
        result = diecut_service.list_stl_files()
        return jsonify(result.to_dict())
    
    @app.route("/api/diecut/stl/<filename>", methods=["GET"])
    def download_stl(filename):
        file_path = diecut_service.output_dir / secure_filename(filename)
        if not file_path.exists():
            return jsonify(ApiResponse(False, errors=["文件不存在"]).to_dict()), 404
        
        return send_file(str(file_path), as_attachment=True)
    
    # ── Workflow API ──
    
    @app.route("/api/workflow/order", methods=["POST"])
    def customer_order():
        data = request.get_json() or {}
        if not data.get("customer_name") or not data.get("company"):
            return jsonify(ApiResponse(False, errors=["customer_name和company必填"]).to_dict()), 400
        
        cad_file = Path(data["cad_file"]) if data.get("cad_file") else None
        
        result = workflow_service.customer_order_workflow(
            data["customer_name"],
            data["company"],
            cad_file
        )
        return jsonify(result.to_dict())
    
    # ── 健康检查 ──
    
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "ok",
            "services": {
                "crm": HAS_CRM,
                "diecut": HAS_DIECUT
            }
        })
    
    @app.route("/api/status", methods=["GET"])
    def api_status():
        return jsonify({
            "rose_crm": {
                "available": HAS_CRM,
                "endpoints": [
                    "GET /api/rose/customers",
                    "POST /api/rose/customers",
                    "GET /api/rose/tasks",
                    "POST /api/rose/tasks",
                    "GET /api/rose/stats"
                ]
            },
            "diecut_3d": {
                "available": HAS_DIECUT,
                "endpoints": [
                    "POST /api/diecut/analyze",
                    "POST /api/diecut/generate",
                    "POST /api/diecut/quote",
                    "GET /api/diecut/stl"
                ]
            },
            "workflow": {
                "available": True,
                "endpoints": [
                    "POST /api/workflow/order"
                ]
            }
        })
    
    return app


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="项目API服务器")
    parser.add_argument("--port", type=int, default=5011, help="端口号")
    parser.add_argument("--host", default="0.0.0.0", help="主机地址")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    
    args = parser.parse_args()
    
    app = create_app()
    if not app:
        print("Flask未安装，无法启动服务器")
        print("运行: pip install flask")
        return
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║              项目API服务器 - OpenClaw集成                      ║
╠═══════════════════════════════════════════════════════════════╣
║  予人玫瑰 CRM:  /api/rose/*                                   ║
║  刀模3D:       /api/diecut/*                                  ║
║  工作流:       /api/workflow/*                                ║
╠═══════════════════════════════════════════════════════════════╣
║  服务地址: http://{args.host}:{args.port}                          ║
║  健康检查: http://{args.host}:{args.port}/health                   ║
║  API状态:  http://{args.host}:{args.port}/api/status               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
