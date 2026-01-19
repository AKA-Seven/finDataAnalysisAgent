# main.py
"""
项目入口文件：初始化配置、启动 ReAct Agent
默认运行后进入交互模式：提示输入问题，Agent回答，支持多轮对话（历史保留）
- 输入 'exit' 或 'quit' 退出
- 自动生成 session_id，并打印
- 支持连续对话（历史自动管理）
运行方式：python main.py
"""

import sys
import time
import hashlib
from agents import ConversationManager, TaskDispatcher  # 从 agents 包导入

def generate_session_id() -> str:
    """生成唯一 session_id（基于时间戳 + 哈希）"""
    timestamp = str(time.time())
    return "session_" + hashlib.md5(timestamp.encode()).hexdigest()[:12]

def main():
    # 自动生成 session_id
    session_id = generate_session_id()
    print(f"自动生成 session_id: {session_id}")

    # 初始化对话管理器（自动加载/保存历史）
    conv_manager = ConversationManager(session_id=session_id)
    dispatcher = TaskDispatcher(conv_manager=conv_manager)

    print("进入交互模式（输入 'exit' 或 'quit' 退出）")
    print("你可以连续输入问题，Agent 会基于历史上下文回答。")

    while True:
        try:
            user_input = input("\n输入问题: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("退出交互模式。历史已保存到 sessions/。")
                break
            if not user_input:
                continue

            # 分发任务（使用 dispatcher，支持多轮历史）
            result = dispatcher.dispatch(user_input)
            print("\nAgent 回答:\n", result)

            # 自动总结长上下文
            conv_manager.summarize_if_long()

        except KeyboardInterrupt:
            print("\n用户中断，退出交互模式。历史已保存。")
            break
        except Exception as e:
            print(f"错误：{str(e)}")

if __name__ == "__main__":
    main()