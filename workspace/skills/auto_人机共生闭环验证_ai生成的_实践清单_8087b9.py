def auto_人机共生闭环验证_ai生成的_实践清单_8087b9(practice_list, execution_results):
    """
    验证人机共生闭环：AI生成的实践清单由人类执行后能否获得可量化的正向反馈
    
    参数:
        practice_list (list): AI生成的实践清单，每个实践是包含以下键的字典:
            - 'id': 实践唯一标识符
            - 'description': 实践描述
            - 'expected_target': 预期量化目标值 (数值)
        execution_results (dict): 执行结果字典，键为实践ID，值为执行结果列表:
            - 每个结果应为数值类型
            - 列表长度表示执行次数
    
    返回:
        dict: 验证结果，包含:
            - 'feedback_per_practice': 每个实践的详细反馈
            - 'summary': 整体验证摘要
            - 'errors': 错误信息列表
    
    异常处理:
        - 处理缺失实践ID
        - 处理非数值结果
        - 处理空结果列表
    """
    feedback_per_practice = {}
    errors = []
    consolidated_count = 0
    total_feedbacks = 0
    
    for practice in practice_list:
        practice_id = practice.get('id')
        if not practice_id:
            errors.append(f"实践缺少ID: {practice}")
            continue
            
        try:
            # 获取实践参数
            description = practice.get('description', '未描述')
            expected_target = practice['expected_target']
            
            # 获取执行结果
            results = execution_results.get(practice_id, [])
            if not results:
                errors.append(f"实践 {practice_id} 无执行结果")
                continue
                
            # 验证结果类型
            try:
                numeric_results = [float(r) for r in results]
            except (ValueError, TypeError):
                errors.append(f"实践 {practice_id} 包含非数值结果: {results}")
                continue
                
            # 计算统计量
            avg_result = sum(numeric_results) / len(numeric_results)
            max_result = max(numeric_results)
            min_result = min(numeric_results)
            
            # 计算单次反馈达标情况
            single_feedbacks = [r >= expected_target for r in numeric_results]
            feedback_rate = sum(single_feedbacks) / len(single_feedbacks)
            
            # 判断固化条件 (至少3次执行且80%达标)
            is_consolidated = (
                len(numeric_results) >= 3 and 
                feedback_rate >= 0.8
            )
            
            # 更新统计
            if is_consolidated:
                consolidated_count += 1
            total_feedbacks += len(single_feedbacks)
            
            # 构建实践反馈
            feedback_per_practice[practice_id] = {
                'description': description,
                'expected_target': expected_target,
                'execution_count': len(numeric_results),
                'average_result': round(avg_result, 2),
                'max_result': round(max_result, 2),
                'min_result': round(min_result, 2),
                'feedback_rate': round(feedback_rate, 2),
                'is_consolidated': is_consolidated,
                'single_feedbacks': single_feedbacks
            }
            
        except Exception as e:
            errors.append(f"处理实践 {practice_id} 时出错: {str(e)}")
    
    # 计算整体摘要
    total_practices = len(practice_list)
    consolidation_rate = consolidated_count / total_practices if total_practices > 0 else 0
    overall_feedback_rate = sum(
        f['feedback_rate'] * f['execution_count'] 
        for f in feedback_per_practice.values()
    ) / total_feedbacks if total_feedbacks > 0 else 0
    
    summary = {
        'total_practices': total_practices,
        'consolidated_practices': consolidated_count,
        'consolidation_rate': round(consolidation_rate, 2),
        'overall_feedback_rate': round(overall_feedback_rate, 2),
        'practices_with_feedback': len(feedback_per_practice)
    }
    
    return {
        'feedback_per_practice': feedback_per_practice,
        'summary': summary,
        'errors': errors
    }


# 示例用法
if __name__ == "__main__":
    # 示例实践清单
    practices = [
        {
            "id": "p1",
            "description": "每日冥想练习",
            "expected_target": 30  # 目标：每日30分钟
        },
        {
            "id": "p2",
            "description": "学习新技能",
            "expected_target": 5   # 目标：每周学习5小时
        },
        {
            "id": "p3",
            "description": "社交互动",
            "expected_target": 10  # 目标：每日10次积极互动
        }
    ]
    
    # 示例执行结果
    results = {
        "p1": [25, 30, 35, 40, 30],  # 达标率80%
        "p2": [4, 5, 6, 4, 5, 6],    # 达标率100%
        "p3": [8, 9, 10, 11, 12]     # 达标率100%
    }
    
    # 执行验证
    verification_result = auto_人机共生闭环验证_ai生成的_实践清单_8087b9(practices, results)
    
    # 打印结果
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(verification_result)