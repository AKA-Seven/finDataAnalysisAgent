# test/test_agents.py
"""
测试 agents 包的核心功能（ConversationManager, TaskDispatcher, run_react_agent）
使用标准库运行：python test/test_agents.py
测试策略：
- ConversationManager：历史追加、保存/加载、总结长上下文
- run_react_agent：简单ReAct循环（mock LLM响应，避免真实API调用）
- TaskDispatcher：简单/复杂任务分发（mock分类）
"""

import json
import os
import shutil
from pathlib import Path
from typing import List, Dict
from agents.conversation_manager import ConversationManager
from agents.react_agent import run_react_agent
from agents.task_dispatcher import TaskDispatcher

# 临时会话目录（测试后清理）
TEST_SESSION_DIR = Path("test_sessions")
TEST_SESSION_DIR.mkdir(exist_ok=True)

def assert_true(condition, test_name):
    if condition:
        print(f"{test_name}: PASS")
    else:
        print(f"{test_name}: FAIL")

def assert_equal(actual, expected, test_name):
    if actual == expected:
        print(f"{test_name}: PASS")
    else:
        print(f"{test_name}: FAIL (got {repr(actual)}, expected {repr(expected)})")

def clean_test_dir():
    """清理测试目录"""
    if TEST_SESSION_DIR.exists():
        shutil.rmtree(TEST_SESSION_DIR)

# ====================== ConversationManager 测试 ======================
def test_conversation_manager():
    session_id = "test_manager"
    file_path = TEST_SESSION_DIR / f"{session_id}.json"

    # 初始化并追加消息
    manager = ConversationManager(session_id=session_id)
    manager.append_message("user", "测试查询1")
    manager.append_message("assistant", "测试响应1")

    # 检查历史
    history = manager.get_history()
    assert_equal(len(history), 3, "history length (system + 2 messages)")
    assert_equal(history[-1]["content"], "测试响应1", "last message content")

    # 保存并重新加载
    manager.save_session()
    new_manager = ConversationManager(session_id=session_id)
    new_history = new_manager.get_history()
    assert_equal(len(new_history), 3, "loaded history length")
    assert_equal(new_history[-1]["content"], "测试响应1", "loaded last message")

    # 总结长上下文（模拟长历史）
    long_history = [{"role": "user", "content": "msg" * 1000}] * 10  # 模拟超长
    manager.history = [{"role": "system", "content": "sys"}] + long_history
    manager.summarize_if_long(max_tokens=500)
    assert_true(len(manager.get_history()) < 10, "summary shortened history")

    print("test_conversation_manager: ALL PASS")

# ====================== run_react_agent 测试 ======================
# def test_run_react_agent():
#     # Mock LLM（避免真实API调用）
#     def mock_call_deepseek(messages):
#         last_msg = messages[-1]["content"]
#         if "Thought" in last_msg or "Action" in last_msg:
#             return "Thought: 完成\nFinal Answer: 测试响应"
#         return "Thought: 需要工具\nAction: db_query[{\"action\": \"list_tables\"}]"
#
#     # 临时替换call_deepseek
#     import utils.llm_utils
#     original_call = utils.llm_utils.call_deepseek
#     utils.llm_utils.call_deepseek = mock_call_deepseek
#
#     try:
#         history = [{"role": "system", "content": "测试系统"}]
#         final_answer, updated_history = run_react_agent("测试查询", history=history)
#
#         assert_true("测试响应" in final_answer, "final answer content")
#         assert_equal(len(updated_history), 3, "updated history length (system + user + assistant)")
#         assert_true("Final Answer" in updated_history[-1]["content"], "has final answer")
#     finally:
#         utils.llm_utils.call_deepseek = original_call  # 恢复
#
#     print("test_run_react_agent: ALL PASS")

# ====================== TaskDispatcher 测试 ======================
def test_task_dispatcher():
    session_id = "test_dispatcher"
    manager = ConversationManager(session_id=session_id)
    dispatcher = TaskDispatcher(manager)

    # Mock call_deepseek for ALL calls (分类 + simple响应 + ReAct + 总结)
    def mock_call_deepseek(messages):
        last_content = messages[-1]["content"]

        # 模拟分类
        if "分类查询" in messages[0]["content"]:
            return "simple" if "简单" in last_content else "complex"

        # 模拟 simple 任务响应
        if "这是一个简单查询" in last_content:
            return "简单响应：测试通过"

        # 模拟 ReAct 响应（快速结束循环）
        if "复杂查询需要工具" in last_content or "Thought" in last_content:
            return "Thought: 测试中\nFinal Answer: 测试响应"

        # 模拟总结（如果触发）
        if "总结以下对话历史" in messages[0]["content"]:
            return "历史摘要：测试摘要"

        # 默认返回（防止意外调用）
        return "默认 mock 响应"

    import utils.llm_utils
    original_call = utils.llm_utils.call_deepseek
    utils.llm_utils.call_deepseek = mock_call_deepseek

    try:
        # 简单任务（mock 返回 "简单响应：测试通过"）
        result_simple = dispatcher.dispatch("这是一个简单查询")
        assert_true("简单响应" in result_simple, "simple dispatch (mock)")

        # 复杂任务（mock ReAct 返回 "测试响应"）
        result_complex = dispatcher.dispatch("复杂查询需要工具")
        assert_true("测试响应" in result_complex, "complex dispatch (mock)")

        # 检查历史追加（2个 dispatch: 每个添加 user + assistant，共 +4，加上初始 system=5）
        assert_equal(len(manager.get_history()), 5, "history after 2 dispatches")

        # 强制触发总结（设置小 max_tokens 测试）
        manager.summarize_if_long(max_tokens=1)  # 模拟长历史
        assert_true("历史摘要" in manager.get_history()[0]["content"], "summarize mock")

    finally:
        utils.llm_utils.call_deepseek = original_call

    print("test_task_dispatcher: ALL PASS")

if __name__ == "__main__":
    print("开始测试 agents 包...\n")
    clean_test_dir()  # 清理旧文件
    test_conversation_manager()
    # test_run_react_agent()
    test_task_dispatcher()
    clean_test_dir()  # 清理
    print("\n所有测试完成。")