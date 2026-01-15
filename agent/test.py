# test_core_agent.py
"""
Agent核心模块全链路测试：验证对话初始化→输入接收→指令解析→任务执行→记忆管理→报表导出
"""
from agent.dialogue import MemoryStore, ContextManager
from agent.parser import NLParser, TaskStructor, ScenarioMatcher
from agent.core import ReportAgent

def test_report_agent_full_flow():
    # 1. 初始化前置模块（依赖注入准备）
    memory = MemoryStore()
    context_manager = ContextManager(memory)
    nl_parser = NLParser(context_manager)
    task_structor = TaskStructor(nl_parser)
    scenario_matcher = ScenarioMatcher()

    # 2. 初始化报表Agent（金融专属）
    report_agent = ReportAgent(
        memory_store=memory,
        context_manager=context_manager,
        nl_parser=nl_parser,
        task_structor=task_structor,
        scenario_matcher=scenario_matcher
    )

    # 3. 执行完整Agent流程
    try:
        # 步骤1：初始化对话
        report_agent.init_dialogue()

        # 步骤2：接收用户输入（金融报表需求）
        user_input = "帮我生成2024年2月的成本分析报表，检测异常数据，符合金融合规要求"
        if not report_agent.receive_user_input(user_input):
            raise Exception("接收用户输入失败")

        # 步骤3：解析指令，生成结构化Task
        task = report_agent.parse_instruction()
        if not task:
            raise Exception("指令解析失败")

        # 步骤4：执行金融报表任务
        result = report_agent._execute_task()
        if not result:
            raise Exception("任务执行失败")

        # 步骤5：管理记忆（保存到长期记忆）
        report_agent.manage_memory(save_to_long_term=True)

        # 步骤6：格式化并展示结果
        formatted_result = report_agent.format_result()
        print("\n" + "="*50)
        print("=== 最终展示结果 ===")
        print(formatted_result)
        print("="*50)

        # 步骤7：额外导出CSV格式报表
        csv_export_path = report_agent.export_report(format="csv")
        if csv_export_path:
            print(f"\n=== 额外导出CSV报表完成：{csv_export_path} ===")

    except Exception as e:
        print(f"\n=== 全链路测试失败：{e} ===")

if __name__ == "__main__":
    test_report_agent_full_flow()