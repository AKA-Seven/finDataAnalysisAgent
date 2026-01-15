# agent/parser/nl_parser.py
import re
from typing import Dict, Optional, Any

# 统一绝对导入：从agent.dialogue导入核心类
from agent.dialogue import MemoryStore, ContextManager


class NLParser:
    """
    自然语言指令解析类，依赖ContextManager，提取核心业务信息
    核心功能：解析用户输入（结合上下文）、补全缺失信息、校验解析结果
    支持提取：业务场景、时间范围、数据类型、操作类型、核心目标
    """

    def __init__(self, context_manager: ContextManager):
        """
        初始化自然语言解析器（依赖注入ContextManager）
        :param context_manager: 上下文管理器实例，用于获取完整对话上下文
        """
        self._context_manager = context_manager
        # 关键词映射表（可根据业务扩展）
        self._scene_keywords = {
            "销售分析": ["销售", "营收", "业绩", "订单", "销售额"],
            "成本分析": ["成本", "开支", "支出", "结算", "成本金额"],
            "利润分析": ["利润", "净利", "毛利", "收益"],
            "异常检测": ["异常", "预警", "违规", "超出范围", "异常值"]
        }
        self._operation_keywords = {
            "统计聚合": ["统计", "汇总", "合计", "均值", "中位数", "Top"],
            "趋势分析": ["趋势", "环比", "同比", "增长", "变化", "时序"],
            "报表生成": ["报表", "Excel", "导出", "展示", "格式"],
            "异常识别": ["检测", "识别", "查找", "筛选", "异常"]
        }
        self._time_patterns = [
            r"(\d{4}年\d{1,2}月)",  # 匹配"2024年2月"
            r"(\d{4}-\d{1,2})",  # 匹配"2024-02"
            r"(\d{4}年Q\d)",  # 匹配"2024年Q1"
            r"(\d{4}年)"  # 匹配"2024年"
        ]

    def parse_nl(self) -> Dict[str, Any]:
        """
        核心方法：解析自然语言指令，提取原始结构化信息
        :return: 原始解析结果字典，包含核心业务信息
        """
        # 1. 获取关键上下文和当前用户输入
        key_context = self._context_manager.extract_key_context()
        user_input = key_context.get("current_user_input", "").strip()
        if not user_input:
            return {"error": "无有效用户输入", "parse_status": "failed"}

        # 2. 提取核心信息
        parse_result = {
            "scene": self._extract_scene(user_input, key_context),
            "time_range": self._extract_time_range(user_input),
            "data_type": self._extract_data_type(user_input),
            "operation": self._extract_operation(user_input),
            "target": self._extract_target(user_input),
            "raw_input": user_input,
            "parse_status": "success"
        }

        # 3. 补全缺失信息（从上下文/默认值）
        parse_result = self._fill_missing_info(parse_result, key_context)

        return parse_result

    def _extract_scene(self, user_input: str, key_context: Dict) -> str:
        """提取业务场景（优先从用户输入，无则从上下文补全）"""
        # 从用户输入中匹配场景关键词
        for scene, keywords in self._scene_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                return scene

        # 从上下文补全
        return key_context.get("scene", "未知场景")

    def _extract_time_range(self, user_input: str) -> str:
        """提取时间范围（使用正则匹配）"""
        for pattern in self._time_patterns:
            match = re.search(pattern, user_input)
            if match:
                return match.group(1)

        return "未指定时间"

    def _extract_data_type(self, user_input: str) -> str:
        """提取数据类型（简化实现，可扩展）—— 修正split("")错误"""
        data_types = ["销售数据", "成本数据", "利润数据", "全量数据"]
        # 直接匹配完整数据类型，无需拆分字符串（删除了多余的split("")）
        for data_type in data_types:
            if data_type in user_input or any(word in user_input for word in data_type):
                return data_type

        return "未指定数据类型"

    def _extract_operation(self, user_input: str) -> str:
        """提取操作类型"""
        for operation, keywords in self._operation_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                return operation

        return "未指定操作"

    def _extract_target(self, user_input: str) -> str:
        """提取核心目标（简化实现，返回用户输入核心部分）"""
        # 移除常见语气词和前缀
        prefixes = ["帮我", "我要", "请", "麻烦", "能否"]
        target = user_input
        for prefix in prefixes:
            if target.startswith(prefix):
                target = target[len(prefix):].strip()

        return target

    def _fill_missing_info(self, parse_result: Dict, key_context: Dict) -> Dict:
        """补全解析结果中缺失的信息（从上下文/默认值）"""
        # 补全场景
        if parse_result.get("scene") == "未知场景" and key_context.get("scene") != "未提及":
            parse_result["scene"] = key_context.get("scene")

        # 补全时间范围
        if parse_result.get("time_range") == "未指定时间" and key_context.get("time_range") != "未提及":
            parse_result["time_range"] = key_context.get("time_range")

        # 补全默认操作
        if parse_result.get("operation") == "未指定操作":
            parse_result["operation"] = "统计聚合"

        return parse_result

    def validate_parse_result(self, parse_result: Dict) -> (bool, Optional[str]):
        """
        校验解析结果的有效性
        :param parse_result: 原始解析结果字典
        :return: （是否有效，错误信息/None）
        """
        if parse_result.get("parse_status") != "success":
            return False, parse_result.get("error", "未知解析错误")

        # 核心字段校验（场景不能为空）
        if parse_result.get("scene") in ["未知场景", ""]:
            return False, "无法提取有效业务场景，请明确输入相关业务关键词"

        return True, None


# 测试示例（可直接运行该文件验证功能）
if __name__ == "__main__":
    # 1. 初始化阶段1的记忆存储和上下文管理器（统一绝对导入）
    memory = MemoryStore()
    context_manager = ContextManager(memory)

    # 2. 模拟用户输入和上下文
    user_input = "调取系统数据库，分析并统计2024年2月的金融云销售数据，生成Excel报表返回给我"
    context_manager.update_context(user_input)

    # 3. 初始化自然语言解析器
    nl_parser = NLParser(context_manager)

    # 4. 执行解析并验证结果
    parse_result = nl_parser.parse_nl()
    is_valid, error_msg = nl_parser.validate_parse_result(parse_result)

    print("=== 自然语言解析结果 ===")
    for key, value in parse_result.items():
        print(f"{key}：{value}")

    print(f"\n=== 解析结果校验 ===")
    print(f"是否有效：{is_valid}")
    if not is_valid:
        print(f"错误信息：{error_msg}")