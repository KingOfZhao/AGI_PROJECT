def auto_逻辑自洽性验证_在给定特定上下文约束下_8be5e2(context_constraints: dict, structured_plan: dict) -> tuple[bool, str]:
    """
    验证在给定特定上下文约束下，AI生成的结构化方案是否逻辑自洽（无逻辑漏洞、无幻觉）。
    
    参数:
        context_constraints (dict): 包含上下文约束条件的字典，例如：
            {
                "time_range": [0, 100],  # 时间范围
                "resource_limits": {"energy": 50, "data": 1000},  # 资源限制
                "forbidden_actions": ["delete", "modify"]  # 禁止操作
            }
        structured_plan (dict): AI生成的结构化方案，例如：
            {
                "steps": [
                    {"action": "collect", "cost": {"energy": 10, "data": 100}},
                    {"action": "analyze", "cost": {"energy": 20, "data": 500}},
                    {"action": "report", "cost": {"energy": 5, "data": 200}}
                ],
                "total_cost": {"energy": 35, "data": 800}
            }
    
    返回:
        tuple[bool, str]: 
            - 第一个元素表示验证是否通过（True=通过，False=失败）
            - 第二个元素包含详细的验证结果或错误信息
    
    异常处理:
        - 输入类型错误
        - 缺少必要字段
        - 资源超限
        - 逻辑冲突
        - 幻觉检测
    """
    
    # 输入验证
    if not isinstance(context_constraints, dict) or not isinstance(structured_plan, dict):
        return False, "错误：输入参数必须是字典类型"
    
    try:
        # 验证1: 检查必要字段存在性
        required_fields = ["steps", "total_cost"]
        for field in required_fields:
            if field not in structured_plan:
                return False, f"错误：方案中缺少必要字段 '{field}'"
        
        # 验证2: 资源消耗一致性检查
        calculated_cost = {"energy": 0, "data": 0}
        for step in structured_plan["steps"]:
            if "cost" not in step:
                return False, f"错误：步骤 {step} 中缺少 'cost' 字段"
            
            for resource, amount in step["cost"].items():
                if not isinstance(amount, (int, float)):
                    return False, f"错误：资源 {resource} 的值必须是数字"
                calculated_cost[resource] += amount
        
        # 比较计算值与声明值
        for resource, declared in structured_plan["total_cost"].items():
            if calculated_cost.get(resource, 0) != declared:
                return False, (
                    f"资源 {resource} 消耗不一致: "
                    f"计算值 {calculated_cost[resource]} ≠ 声明值 {declared}"
                )
        
        # 验证3: 上下文约束检查
        if "time_range" in context_constraints:
            step_count = len(structured_plan["steps"])
            min_time, max_time = context_constraints["time_range"]
            if not (min_time <= step_count <= max_time):
                return False, (
                    f"步骤数量 {step_count} 超出时间范围 [{min_time}, {max_time}]"
                )
        
        if "resource_limits" in context_constraints:
            for resource, limit in context_constraints["resource_limits"].items():
                if calculated_cost.get(resource, 0) > limit:
                    return False, (
                        f"资源 {resource} 消耗 {calculated_cost[resource]} "
                        f"超过限制 {limit}"
                    )
        
        # 验证4: 禁止操作检查
        if "forbidden_actions" in context_constraints:
            forbidden = set(context_constraints["forbidden_actions"])
            for step in structured_plan["steps"]:
                if step["action"] in forbidden:
                    return False, f"错误：禁止操作 '{step['action']}' 出现在方案中"
        
        # 验证5: 逻辑自洽性检查
        # 检查步骤顺序逻辑（示例：收集步骤必须在分析步骤之前）
        collect_found = False
        for step in structured_plan["steps"]:
            if step["action"] == "collect":
                collect_found = True
            elif step["action"] == "analyze" and not collect_found:
                return False, "逻辑错误：分析步骤出现在收集步骤之前"
        
        # 验证6: 幻觉检测（示例：检查是否引用不存在的资源）
        valid_resources = {"energy", "data", "time"}  # 假设有效资源集合
        for step in structured_plan["steps"]:
            for resource in step["cost"].keys():
                if resource not in valid_resources:
                    return False, f"幻觉检测：无效资源 '{resource}'"
        
        return True, "验证通过：方案逻辑自洽且符合所有约束条件"
    
    except Exception as e:
        return False, f"验证过程中发生意外错误: {str(e)}"


# 示例用法
if __name__ == "__main__":
    # 示例上下文约束
    constraints = {
        "time_range": [1, 10],
        "resource_limits": {"energy": 50, "data": 1000},
        "forbidden_actions": ["delete", "modify"]
    }
    
    # 有效方案示例
    valid_plan = {
        "steps": [
            {"action": "collect", "cost": {"energy": 10, "data": 100}},
            {"action": "analyze", "cost": {"energy": 20, "data": 500}},
            {"action": "report", "cost": {"energy": 5, "data": 200}}
        ],
        "total_cost": {"energy": 35, "data": 800}
    }
    
    # 无效方案示例（资源超限）
    invalid_plan = {
        "steps": [
            {"action": "collect", "cost": {"energy": 60, "data": 100}},
            {"action": "analyze", "cost": {"energy": 20, "data": 500}}
        ],
        "total_cost": {"energy": 80, "data": 600}
    }
    
    # 测试有效方案
    result, message = auto_逻辑自洽性验证_在给定特定上下文约束下_8be5e2(constraints, valid_plan)
    print(f"有效方案验证结果: {result}, 信息: {message}")
    
    # 测试无效方案
    result, message = auto_逻辑自洽性验证_在给定特定上下文约束下_8be5e2(constraints, invalid_plan)
    print(f"无效方案验证结果: {result}, 信息: {message}")