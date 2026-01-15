# agent/prompts/base_parser_prompt.py
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

def get_nl_task_parser_prompt() -> ChatPromptTemplate:
    """
    获取自然语言任务解析提示词模板（用于将用户输入转为结构化任务）
    :return: LangChain ChatPromptTemplate实例
    """
    return ChatPromptTemplate.from_messages([
        ("system", """你是一个金融业务指令解析助手，需要将用户输入转换为结构化任务。
        要求：
        1. 提取核心信息：业务场景（scene）、时间范围（time_range）、操作类型（operation）、数据目标（target）
        2. 若信息缺失，填充为"未提及"，不凭空捏造
        3. 严格按照输出格式返回，不得包含其他无关内容"""),
        MessagesPlaceholder(variable_name="chat_history"),  # 插入短期记忆（上下文）
        ("human", "{input}"),  # 插入当前用户输入
        ("human", "请严格按照以下格式返回结果：\n{format_instructions}")  # 插入结构化格式说明（由OutputParser自动生成）
    ])