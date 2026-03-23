class UncertaintyQuantification:
    """
    实现人机共生不确定性量化协议，用于将模糊概念拆解为可执行的布尔逻辑。
    
    功能：
    1. 识别输入中的模糊概念
    2. 向人类发起定向询问获取明确信息
    3. 将模糊概念转换为可执行的布尔逻辑表达式
    
    使用示例：
    >>> uq = UncertaintyQuantification()
    >>> uq.process_fuzzy_concept("高收入人群")
    'income > 50000'
    """
    
    def __init__(self):
        """初始化不确定性量化器，预定义模糊概念规则库"""
        self.rules = {
            "高收入": {
                "question": "请定义高收入的年收入阈值（单位：元）",
                "type": "numeric",
                "logic": lambda x: f"income > {x}"
            },
            "年轻": {
                "question": "请定义年轻的最大年龄（单位：岁）",
                "type": "numeric",
                "logic": lambda x: f"age < {x}"
            },
            "大城市": {
                "question": "请定义大城市的最低人口规模（单位：万人）",
                "type": "numeric",
                "logic": lambda x: f"population > {x * 10000}"
            },
            "优质产品": {
                "question": "请定义优质产品的最低评分（1-10分）",
                "type": "numeric",
                "logic": lambda x: f"rating >= {x}"
            }
        }
    
    def identify_ambiguity(self, input_str):
        """
        识别输入中的模糊概念
        
        参数:
            input_str (str): 用户输入的模糊概念描述
            
        返回:
            list: 识别到的模糊概念列表
            
        异常:
            ValueError: 当输入为空或非字符串时
        """
        if not isinstance(input_str, str) or not input_str.strip():
            raise ValueError("输入必须是非空字符串")
            
        # 简单关键词匹配（实际应用可使用NLP技术）
        matched = []
        for concept in self.rules:
            if concept in input_str:
                matched.append(concept)
        return matched
    
    def query_human(self, question):
        """
        向人类发起定向询问
        
        参数:
            question (str): 询问内容
            
        返回:
            str: 人类提供的明确信息
            
        异常:
            KeyboardInterrupt: 用户中断输入
            ValueError: 输入无效时
        """
        try:
            print(f"\n[人类交互] {question}")
            response = input("请输入您的回答: ").strip()
            if not response:
                raise ValueError("回答不能为空")
            return response
        except KeyboardInterrupt:
            print("\n用户中断交互")
            raise
        except Exception as e:
            print(f"输入错误: {e}")
            raise ValueError("无效的输入格式")
    
    def decompose_to_boolean(self, ambiguous_concept):
        """
        将模糊概念拆解为可执行的布尔逻辑
        
        参数:
            ambiguous_concept (str): 模糊概念名称
            
        返回:
            str: 生成的布尔逻辑表达式
            
        异常:
            KeyError: 概念不存在于规则库中
            ValueError: 人类提供无效值时
        """
        if ambiguous_concept not in self.rules:
            raise KeyError(f"未定义的模糊概念: {ambiguous_concept}")
            
        rule = self.rules[ambiguous_concept]
        
        try:
            # 获取人类明确信息
            human_input = self.query_human(rule["question"])
            
            # 根据类型处理输入
            if rule["type"] == "numeric":
                value = float(human_input)
                if value < 0:
                    raise ValueError("数值必须为正数")
                return rule["logic"](value)
            else:
                return rule["logic"](human_input)
                
        except ValueError as e:
            raise ValueError(f"无效输入: {e}")
    
    def process_fuzzy_concept(self, input_str):
        """
        处理模糊概念的完整流程
        
        参数:
            input_str (str): 包含模糊概念的输入字符串
            
        返回:
            dict: 包含识别结果和布尔逻辑的字典
            
        异常:
            ValueError: 处理过程中出现错误时
        """
        try:
            # 1. 识别模糊概念
            ambiguous_concepts = self.identify_ambiguity(input_str)
            if not ambiguous_concepts:
                return {"status": "no_ambiguity", "message": "未检测到模糊概念"}
            
            results = {}
            for concept in ambiguous_concepts:
                # 2. 发起询问并生成布尔逻辑
                try:
                    boolean_logic = self.decompose_to_boolean(concept)
                    results[concept] = {
                        "status": "resolved",
                        "boolean_logic": boolean_logic
                    }
                except Exception as e:
                    results[concept] = {
                        "status": "failed",
                        "error": str(e)
                    }
            
            return {
                "status": "processed",
                "input": input_str,
                "results": results
            }
            
        except Exception as e:
            raise ValueError(f"处理失败: {e}")


# 示例用法
if __name__ == "__main__":
    try:
        uq = UncertaintyQuantification()
        
        # 测试用例1：高收入
        result1 = uq.process_fuzzy_concept("我们需要识别高收入人群")
        print("\n处理结果1:")
        print(result1)
        
        # 测试用例2：年轻
        result2 = uq.process_fuzzy_concept("寻找年轻用户")
        print("\n处理结果2:")
        print(result2)
        
        # 测试用例3：无效概念
        result3 = uq.process_fuzzy_concept("模糊概念不存在")
        print("\n处理结果3:")
        print(result3)
        
    except Exception as e:
        print(f"程序运行错误: {e}")