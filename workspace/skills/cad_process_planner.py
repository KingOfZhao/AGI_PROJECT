#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工艺规划技能 — 概念/图纸 → 可实践检查清单 → 工艺步骤
====================================================
核心pipeline:
  1. 输入: 工业概念描述 或 DXF图纸解析结果
  2. LLM分析: 智谱API生成结构化工艺规划
  3. 输出: JSON格式的检查清单 + 工艺步骤 + 热处理方案

架构: tool_controller模式 — 智谱API思考, Python执行验证
参考: ARKNESS (KG+LLM CAPP), MIT Design-to-Manufacturing
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SKILL_META = {
    "name": "cad_process_planner",
    "display_name": "工艺规划引擎",
    "description": "从工业概念或CAD图纸生成结构化工艺规划: 检查清单+加工步骤+热处理+刀具参数",
    "tags": ["CAPP", "工艺规划", "检查清单", "加工", "热处理", "工业制造"],
    "capabilities": [
        "concept_to_checklist: 工业概念→可实践检查清单",
        "dxf_to_process_plan: DXF图纸→完整工艺规划",
        "generate_heat_treatment: 生成热处理方案",
        "generate_machining_steps: 生成加工步骤(含刀具/进给/转速)",
    ],
}

# ==================== 提示词模板 ====================

CHECKLIST_PROMPT = """你是一位资深制造工程师和工艺规划专家。请根据以下工业概念/需求，生成一份结构化的可实践检查清单。

用户需求：
{concept}

{context}

请严格按以下JSON格式输出：
{{
  "part_name": "零件名称",
  "material": "推荐材料及牌号",
  "checklist": [
    {{
      "step": 1,
      "category": "设计|选材|粗加工|精加工|热处理|表面处理|检验",
      "action": "具体可执行的操作描述",
      "tools_required": ["所需工具/设备"],
      "parameters": {{"关键参数名": "参数值"}},
      "verification": "如何验证此步骤完成",
      "codeable": true或false,
      "notes": "注意事项"
    }}
  ],
  "total_steps": 总步骤数,
  "estimated_time": "预估总工时",
  "critical_dimensions": ["关键尺寸列表"],
  "risks": ["潜在风险"]
}}"""

PROCESS_PLAN_PROMPT = """你是一位CNC加工和工艺规划专家。请根据以下CAD图纸分析结果，生成完整的工艺规划。

图纸分析：
{dxf_summary}

图纸详情：
- 实体: {entity_counts}
- 尺寸: {dimensions}
- 文字标注: {texts}
- 图纸范围: {bounds}

{extra_requirements}

请严格按以下JSON格式输出：
{{
  "part_name": "零件名称(从图纸推断)",
  "material": "推荐材料",
  "overall_dimensions": "外形尺寸",
  "machining_steps": [
    {{
      "step": 1,
      "operation": "工序名称(车削/铣削/钻孔/磨削/线切割等)",
      "description": "详细操作描述",
      "tool": "刀具型号/规格",
      "spindle_speed": "主轴转速(RPM)",
      "feed_rate": "进给速率(mm/min)",
      "depth_of_cut": "切削深度(mm)",
      "coolant": "冷却液类型",
      "fixture": "装夹方式",
      "tolerance": "公差要求"
    }}
  ],
  "heat_treatment": {{
    "required": true或false,
    "process": "热处理类型(淬火/回火/渗碳/氮化等)",
    "temperature": "温度(°C)",
    "duration": "保温时间",
    "cooling": "冷却方式",
    "target_hardness": "目标硬度(HRC)"
  }},
  "inspection": [
    {{
      "item": "检验项目",
      "method": "检验方法",
      "standard": "验收标准"
    }}
  ],
  "estimated_time": "预估总工时",
  "mastercam_notes": "Mastercam编程注意事项"
}}"""

HEAT_TREATMENT_PROMPT = """你是一位热处理工艺专家。请根据以下零件信息，设计完整的热处理方案。

零件信息：
{part_info}

请按JSON格式输出完整的热处理工艺卡：
{{
  "material": "材料牌号",
  "treatment_type": "热处理类型",
  "pre_treatment": "预处理(如有)",
  "steps": [
    {{
      "step": 1,
      "process": "工艺名称",
      "temperature": "温度范围(°C)",
      "heating_rate": "升温速率(°C/h)",
      "holding_time": "保温时间",
      "cooling_method": "冷却方式(空冷/水冷/油冷/炉冷)",
      "atmosphere": "气氛(如适用)",
      "notes": "注意事项"
    }}
  ],
  "target_properties": {{
    "hardness": "目标硬度",
    "tensile_strength": "抗拉强度",
    "elongation": "延伸率"
  }},
  "quality_check": ["检验项目"],
  "safety_notes": ["安全注意事项"]
}}"""


# ==================== 核心函数 ====================

def _call_zhipu(prompt: str, task_type: str = "reasoning") -> str:
    """调用智谱API"""
    try:
        from workspace.skills.zhipu_ai_caller import call_zhipu
        result = call_zhipu(prompt, task_type=task_type, model="glm-4-plus")
        if result.get("success"):
            return result["content"]
        return ""
    except Exception:
        pass

    # Fallback: 直接用agi模块
    try:
        import agi_v13_cognitive_lattice as agi
        messages = [
            {"role": "system", "content": "你是一位资深制造工程师。请严格按JSON格式输出。"},
            {"role": "user", "content": prompt}
        ]
        result = agi.llm_call(messages)
        return result.get('raw', str(result)) if isinstance(result, dict) else str(result)
    except Exception as e:
        return f"LLM调用失败: {e}"


def _extract_json(text: str) -> Optional[Dict]:
    """从LLM输出中提取JSON"""
    import re
    # 尝试直接解析
    try:
        return json.loads(text)
    except:
        pass
    # 尝试提取代码块中的JSON
    m = re.search(r'```(?:json)?\s*\n([\s\S]*?)```', text)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    # 尝试提取最外层{}
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            return json.loads(m.group())
        except:
            pass
    return None


def concept_to_checklist(concept: str, context: str = "") -> Dict[str, Any]:
    """
    工业概念 → 可实践检查清单

    Args:
        concept: 工业概念/需求描述 (如"加工一个带3个M8螺纹孔的法兰盘")
        context: 额外上下文 (材料/尺寸/公差等)

    Returns:
        {"success": bool, "checklist": {...}, "raw": str}
    """
    t0 = time.time()
    ctx_section = f"\n额外信息:\n{context}" if context else ""
    prompt = CHECKLIST_PROMPT.format(concept=concept, context=ctx_section)
    raw = _call_zhipu(prompt, "reasoning")

    parsed = _extract_json(raw)
    if parsed:
        return {
            "success": True,
            "checklist": parsed,
            "steps_count": len(parsed.get("checklist", [])),
            "duration": round(time.time() - t0, 2),
        }
    return {
        "success": False,
        "error": "无法解析工艺规划输出",
        "raw": raw[:2000],
        "duration": round(time.time() - t0, 2),
    }


def dxf_to_process_plan(file_path: str, extra_requirements: str = "") -> Dict[str, Any]:
    """
    DXF图纸 → 完整工艺规划

    Args:
        file_path: DXF文件路径
        extra_requirements: 额外加工要求

    Returns:
        {"success": bool, "plan": {...}, "dxf_summary": str}
    """
    t0 = time.time()

    # 先解析DXF
    from workspace.skills.cad_file_recognizer import parse_dxf
    dxf_data = parse_dxf(file_path)
    if not dxf_data["success"]:
        return dxf_data

    # 构建提示
    extra = f"\n额外要求:\n{extra_requirements}" if extra_requirements else ""
    prompt = PROCESS_PLAN_PROMPT.format(
        dxf_summary=dxf_data.get("summary", ""),
        entity_counts=json.dumps(dxf_data.get("entity_counts", {}), ensure_ascii=False),
        dimensions=json.dumps(dxf_data.get("dimensions", [])[:10], ensure_ascii=False),
        texts=json.dumps([t["text"] for t in dxf_data.get("texts", [])[:10]], ensure_ascii=False),
        bounds=json.dumps(dxf_data.get("bounds", {}), ensure_ascii=False),
        extra_requirements=extra,
    )

    raw = _call_zhipu(prompt, "reasoning")
    parsed = _extract_json(raw)

    if parsed:
        return {
            "success": True,
            "plan": parsed,
            "dxf_summary": dxf_data["summary"],
            "steps_count": len(parsed.get("machining_steps", [])),
            "duration": round(time.time() - t0, 2),
        }
    return {
        "success": False,
        "error": "无法解析工艺规划输出",
        "dxf_summary": dxf_data["summary"],
        "raw": raw[:2000],
        "duration": round(time.time() - t0, 2),
    }


def generate_heat_treatment(part_info: str) -> Dict[str, Any]:
    """
    生成热处理方案

    Args:
        part_info: 零件信息描述 (材料/硬度要求/用途等)
    """
    t0 = time.time()
    prompt = HEAT_TREATMENT_PROMPT.format(part_info=part_info)
    raw = _call_zhipu(prompt, "reasoning")
    parsed = _extract_json(raw)
    if parsed:
        return {"success": True, "heat_treatment": parsed, "duration": round(time.time() - t0, 2)}
    return {"success": False, "error": "无法解析热处理方案", "raw": raw[:2000]}


def save_plan_to_file(plan_data: Dict, output_path: str = None) -> Dict[str, Any]:
    """将工艺规划保存为JSON文件"""
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(PROJECT_ROOT / "workspace" / "outputs" / f"process_plan_{ts}.json")

    p = Path(output_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / output_path
    p.parent.mkdir(parents=True, exist_ok=True)

    plan_data["generated_at"] = datetime.now().isoformat()
    plan_data["generator"] = "AGI v13.3 CAD Process Planner"

    p.write_text(json.dumps(plan_data, ensure_ascii=False, indent=2), encoding='utf-8')
    return {"success": True, "path": str(p), "size": p.stat().st_size}


# ==================== 自测 ====================

if __name__ == "__main__":
    print("=== 工艺规划引擎 自测 ===\n")

    # 测试概念→检查清单 (需要网络/API)
    print("--- concept_to_checklist ---")
    try:
        result = concept_to_checklist(
            "加工一个外径100mm、内径60mm、厚度20mm的45#钢法兰盘，带4个均布M8螺纹通孔",
            "表面粗糙度Ra1.6, 端面平行度0.02mm"
        )
        if result["success"]:
            print(f"生成 {result['steps_count']} 个步骤, 耗时 {result['duration']}s")
            print(json.dumps(result["checklist"], ensure_ascii=False, indent=2)[:500])
        else:
            print(f"失败: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"跳过(需要API): {e}")

    print("\n=== 自测完成 ===")
