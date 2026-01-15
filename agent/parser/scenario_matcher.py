# agent/parser/scenario_matcher.py
from typing import Dict, Optional, Any, List
from dataclasses import asdict

# 统一绝对导入：导入Task和TaskStructor，以及测试用的前置模块
from agent.parser.task_structor import Task, TaskStructor
from agent.parser.nl_parser import NLParser
from agent.dialogue import MemoryStore, ContextManager

class ScenarioMatcher:
    """
    场景匹配类，实现「业务场景-宽表-处理规则」的映射与补全
    核心功能：匹配场景对应的宽表、补充处理规则、动态更新场景映射
    """
    def __init__(self):
        """初始化场景匹配器，加载默认场景映射表"""
        # 场景映射表：场景 → （宽表名称 + 处理规则 + 字段映射）
        self._scene_mapping: Dict[str, Dict[str, Any]] = {
            "销售分析": {
                "wide_table": "sales_wide_table",
                "process_rules": [
                    "按产品分类/区域分类进行聚合统计",
                    "计算月度/季度环比/同比增长率",
                    "生成销售额Top10排行榜",
                    "保存销售趋势图为sales_trend.png"
                ],
                "field_mapping": {
                    "销售额": "sales_amount",
                    "产品分类": "product_category",
                    "销售区域": "sales_region",
                    "销售时间": "sales_date"
                }
            },
            "成本分析": {
                "wide_table": "cost_wide_table",
                "process_rules": [
                    "按成本类型进行汇总统计",
                    "检测成本异常值（IQR法）",
                    "计算成本占销售额的比例",
                    "保存成本分布直方图为cost_distribution.png"
                ],
                "field_mapping": {
                    "成本金额": "cost_amount",
                    "成本类型": "cost_type",
                    "结算时间": "settle_date",
                    "部门": "department"
                }
            },
            "利润分析": {
                "wide_table": "profit_wide_table",
                "process_rules": [
                    "计算毛利（销售额-成本）和净利率",
                    "按季度聚合利润数据",
                    "分析利润与销售额的相关性",
                    "保存利润趋势图为profit_trend.png"
                ],
                "field_mapping": {
                    "毛利": "gross_profit",
                    "净利": "net_profit",
                    "利润日期": "profit_date",
                    "产品线": "product_line"
                }
            },
            "异常检测": {
                "wide_table": "business_anomaly_table",
                "process_rules": [
                    "使用IQR法/3σ法检测数值列异常值",
                    "标注异常数据的原因（超出上下限/突变）",
                    "汇总异常数据并生成预警报表",
                    "保存异常数据清单为anomaly_list.xlsx"
                ],
                "field_mapping": {
                    "业务数据": "business_data",
                    "数据类型": "data_type",
                    "检测时间": "detect_date",
                    "异常等级": "anomaly_level"
                }
            }
        }

    def match_scene_to_table(self, task: Task) -> Task:
        """
        核心方法：根据任务的业务场景，匹配宽表和处理规则，补全到Task参数中
        :param task: 结构化Task实例
        :return: 补充了宽表和处理规则的Task实例
        """
        # 1. 获取任务场景
        scene = task.scene
        if scene not in self._scene_mapping:
            raise Exception(f"无匹配的场景映射：{scene}，支持场景：{list(self._scene_mapping.keys())}")

        # 2. 获取场景对应的映射信息
        scene_info = self._scene_mapping[scene]

        # 3. 补全任务参数（不修改原始Task，返回新实例）
        updated_params = task.params.copy()
        updated_params.update({
            "wide_table": scene_info["wide_table"],
            "process_rules": scene_info["process_rules"],
            "field_mapping": scene_info["field_mapping"]
        })

        # 4. 生成更新后的Task实例
        updated_task = Task(
            task_id=task.task_id,
            task_type=task.task_type,
            scene=task.scene,
            mcp_config=task.mcp_config,
            params=updated_params,
            priority=task.priority,
            create_time=task.create_time,
            status=task.status
        )

        return updated_task

    def update_scene_mapping(self, scene: str, scene_info: Dict[str, Any], overwrite: bool = True) -> None:
        """
        动态更新场景映射表
        :param scene: 业务场景名称
        :param scene_info: 场景映射信息（包含wide_table/process_rules/field_mapping）
        :param overwrite: 若场景已存在，是否覆盖（默认True）
        """
        required_scene_info_fields = ["wide_table", "process_rules", "field_mapping"]
        missing_fields = [f for f in required_scene_info_fields if f not in scene_info]
        if missing_fields:
            raise Exception(f"场景信息缺失必填字段：{missing_fields}")

        if not overwrite and scene in self._scene_mapping:
            return

        self._scene_mapping[scene] = scene_info

    def get_scene_process_rules(self, scene: str) -> Optional[List[str]]:
        """获取指定场景的处理规则"""
        if scene not in self._scene_mapping:
            return None
        return self._scene_mapping[scene]["process_rules"]

    def get_all_scenes(self) -> List[str]:
        """获取所有支持的业务场景"""
        return list(self._scene_mapping.keys())

# 测试示例（可直接运行该文件验证功能）
if __name__ == "__main__":
    # 1. 初始化前置模块（完整链路：记忆存储→上下文→NL解析→任务结构化）
    memory = MemoryStore()
    context_manager = ContextManager(memory)
    user_input = "帮我统计2024年2月的销售数据，生成Excel报表"
    context_manager.update_context(user_input)

    # 1.2 初始化NL解析器和任务结构化器
    nl_parser = NLParser(context_manager)
    task_structor = TaskStructor(nl_parser)

    # 1.3 生成结构化任务
    task = task_structor.convert_to_task()

    # 2. 初始化场景匹配器
    scenario_matcher = ScenarioMatcher()

    # 3. 场景匹配并补全任务
    try:
        updated_task = scenario_matcher.match_scene_to_table(task)

        print("=== 场景匹配后更新的Task ===")
        print(f"业务场景：{updated_task.scene}")
        print(f"匹配宽表：{updated_task.params.get('wide_table')}")
        print(f"处理规则：")
        for idx, rule in enumerate(updated_task.params.get('process_rules', []), 1):
            print(f"  {idx}. {rule}")
        print(f"字段映射：{updated_task.params.get('field_mapping')}")

        # 4. 测试动态更新场景映射
        new_scene_info = {
            "wide_table": "customer_wide_table",
            "process_rules": ["按客户等级统计", "生成客户留存率报表"],
            "field_mapping": {"客户名称": "customer_name", "客户等级": "customer_level"}
        }
        scenario_matcher.update_scene_mapping("客户分析", new_scene_info)
        print(f"\n=== 动态更新后支持的场景 ===")
        print(scenario_matcher.get_all_scenes())
    except Exception as e:
        print(f"场景匹配失败：{e}")