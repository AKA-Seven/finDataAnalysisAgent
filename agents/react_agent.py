# agents/react_agent.py
"""
ReAct Agent 主实现（更新版，支持传入/返回历史）
修复：显式导入 List, Dict (from typing import List, Dict)
其他逻辑同原版：ReAct 循环，工具调用
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from config import config
from utils.llm_utils import call_deepseek
from tools import (
    PythonExecutorTool,
    DBQueryTool,
    WordGeneratorTool,
    ExcelHandlerTool,
)

# 注册工具
TOOLS = [
    PythonExecutorTool(),
    DBQueryTool(),
    WordGeneratorTool(),
    ExcelHandlerTool(),
]
TOOL_DICT: Dict[str, object] = {tool.name: tool for tool in TOOLS}

# 系统提示（ReAct + 工具描述）
SYSTEM_PROMPT = f"""
你是一个智能助手，使用 ReAct 框架（Reason + Act）解决问题。
严格遵循以下格式输出：
Thought: 你的推理过程
Action: tool_name[{{json 参数}}]  # 只在需要工具时输出
Observation: 工具返回结果（由系统提供）
Final Answer: 最终答案（包含文件路径、总结等）

可用工具：
{chr(10).join([f"- {t.name}: {t.description}" for t in TOOLS])}

规则：
1. 如果问题不需要任何工具，直接输出 Final Answer: ...
2. 需要数据查询、代码执行、生成报告时，使用对应工具。
3. Action 必须是 JSON 格式（双引号）。
4. 大数据处理优先用 python_executor。
5. 最终答案必须包含有用信息。
6. 不要重复调用相同工具，除非必要。
"""

# 正则解析
ACTION_PATTERN = re.compile(r"Action:\s*(\w+)\s*\[(.+?)\]", re.DOTALL | re.MULTILINE)
FINAL_ANSWER_PATTERN = re.compile(r"Final Answer:\s*(.+)", re.DOTALL | re.MULTILINE)


def parse_llm_response(response: str) -> Dict[str, Optional[str]]:
    action_match = ACTION_PATTERN.search(response)
    final_match = FINAL_ANSWER_PATTERN.search(response)

    if final_match:
        return {"type": "final", "content": final_match.group(1).strip()}

    if action_match:
        tool_name = action_match.group(1).strip()
        try:
            params_str = action_match.group(2).strip()
            params = json.loads(params_str)
        except json.JSONDecodeError:
            params = {}
        return {"type": "action", "tool_name": tool_name, "params": params}

    return {"type": "none", "content": response.strip()}


def execute_action(tool_name: str, params: Dict) -> str:
    if tool_name not in TOOL_DICT:
        return f"错误：未知工具 '{tool_name}'。"

    tool = TOOL_DICT[tool_name]
    try:
        input_str = json.dumps(params)
        return tool.run(input_str)
    except Exception as e:
        return f"工具执行失败：{str(e)}"


def run_react_agent(query: str, history: List[Dict[str, str]] = None,
                    max_iterations: int = config.AGENT.max_iterations) -> Tuple[str, List[Dict[str, str]]]:
    """
    运行 ReAct，传入/返回历史（支持多轮）
    返回 (final_answer, updated_history)
    """
    if history is None:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]

    history.append({"role": "user", "content": query})

    iteration = 0
    final_answer = None

    while iteration < max_iterations:
        iteration += 1
        response = call_deepseek(messages=history)

        parsed = parse_llm_response(response)

        if parsed["type"] == "final":
            final_answer = parsed["content"]
            history.append({"role": "assistant", "content": response})
            break

        elif parsed["type"] == "action":
            tool_name = parsed["tool_name"]
            params = parsed["params"]
            observation = execute_action(tool_name, params)

            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": f"Observation: {observation}"})

        else:
            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": "请继续思考或给出 Final Answer。"})

    if final_answer is None:
        final_answer = "任务未完成。"

    return final_answer.strip(), history