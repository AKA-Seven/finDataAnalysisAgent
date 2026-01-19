import json
from pathlib import Path
from utils.llm_utils import call_deepseek
from config import config
from typing import Dict, List

class ConversationManager:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.history: List[Dict[str, str]] = [{"role": "system", "content": "系统提示：你是智能助手，使用ReAct框架。"}]
        self.session_dir = Path("sessions")
        self.session_dir.mkdir(exist_ok=True)
        self.load_session()

    def load_session(self):
        file_path = self.session_dir / f"{self.session_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                self.history = json.load(f)

    def append_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self.save_session()

    def get_history(self) -> List[Dict[str, str]]:
        return self.history.copy()

    def summarize_if_long(self, max_tokens: int = 1500):
        # 粗估token：len(str(history)) / 4 ≈ tokens
        if sum(len(msg["content"]) for msg in self.history) > max_tokens * 4:
            summary_prompt = [{"role": "system", "content": "总结以下对话历史为简洁摘要："},
                              {"role": "user", "content": str(self.history[: -5])}]  # 总结旧消息
            summary = call_deepseek(summary_prompt)
            self.history = [{"role": "system", "content": f"历史摘要：{summary}"}] + self.history[-5:]

    def save_session(self):
        file_path = self.session_dir / f"{self.session_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)