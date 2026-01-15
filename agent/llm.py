# agent/llm.py
from langchain_openai import ChatOpenAI
from typing import Optional

def init_deepseek_llm(
    api_key: str,
    model_name: str = "deepseek-chat",
    base_url: str = "https://api.deepseek.com/v1",
    temperature: float = 0.1,
    max_tokens: Optional[int] = 3000
) -> ChatOpenAI:
    """
    初始化DeepSeek大模型（LangChain ChatOpenAI兼容）
    :param api_key: DeepSeek API Key
    :param model_name: 模型名称，默认deepseek-chat
    :param base_url: DeepSeek API地址
    :param temperature: 温度系数，默认0.1（确定性输出）
    :param max_tokens: 最大生成token数
    :return: LangChain ChatOpenAI实例
    """
    return ChatOpenAI(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens
    )