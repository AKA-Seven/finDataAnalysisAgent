# agent/dialogue/memory_store.py
from datetime import datetime
from typing import Dict, List, Optional, Any


class MemoryStore:
    """
    对话记忆存储类，负责管理「短期记忆」和「长期记忆」的增、删、查、存
    - 短期记忆：存储当前对话轮次的临时数据（用户输入、临时解析结果等），单次对话有效，可覆盖
    - 长期记忆：存储历史业务的有效结果（如生成的报表、分析结论等），持久化保存（本次实现内存存储，可扩展为文件/数据库存储）
    """

    def __init__(self):
        """初始化记忆存储，清空初始记忆"""
        # 短期记忆：字典格式，存储当前对话的临时数据
        self._short_term_memory: Dict[str, Any] = {}
        # 长期记忆：列表格式，存储历史业务结果，每个元素为一个业务结果字典
        self._long_term_memory: List[Dict[str, Any]] = []

    def add_short_term_memory(self, key: str, value: Any, overwrite: bool = True) -> None:
        """
        向短期记忆中添加/更新数据
        :param key: 记忆键（如"user_input"、"parse_result"、"temp_task"）
        :param value: 记忆值（任意可序列化数据类型）
        :param overwrite: 若键已存在，是否覆盖（默认True，短期记忆默认覆盖临时数据）
        """
        if not overwrite and key in self._short_term_memory:
            return  # 不覆盖且键已存在，直接返回
        self._short_term_memory[key] = value

    def get_short_term_memory(self, key: Optional[str] = None) -> Any:
        """
        获取短期记忆数据
        :param key: 可选，记忆键；若为None，返回完整的短期记忆字典
        :return: 对应键的记忆值，或完整短期记忆字典；键不存在返回None
        """
        if key is None:
            return self._short_term_memory.copy()  # 返回副本，避免外部修改原始数据
        return self._short_term_memory.get(key, None)

    def clear_short_term_memory(self, specific_keys: Optional[List[str]] = None) -> None:
        """
        清理短期记忆数据
        :param specific_keys: 可选，需要清理的特定键列表；若为None，清空所有短期记忆
        """
        if specific_keys is None:
            self._short_term_memory = {}
        else:
            for key in specific_keys:
                if key in self._short_term_memory:
                    del self._short_term_memory[key]

    def add_long_term_memory(self, scene: str, result: Any, export_path: Optional[str] = None, **kwargs) -> None:
        """
        向长期记忆中添加历史业务结果（自动记录创建时间，不可覆盖，仅追加）
        :param scene: 业务场景（如"销售分析"、"成本结算报表"）
        :param result: 业务结果（如报表数据、分析结论、生成的代码）
        :param export_path: 可选，结果导出文件路径（如"./202402_sales_report.xlsx"）
        :param kwargs: 可选扩展字段（如"time_range": "2024年2月"）
        """
        long_term_item = {
            "scene": scene,
            "result": result,
            "export_path": export_path,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **kwargs
        }
        self._long_term_memory.append(long_term_item)

    def get_long_term_memory(self, scene: Optional[str] = None, latest_only: bool = True) -> Any:
        """
        获取长期记忆数据
        :param scene: 可选，业务场景；若为None，返回所有长期记忆
        :param latest_only: 若指定scene，是否仅返回该场景的最新一条结果（默认True）
        :return: 长期记忆数据（列表/字典），无匹配结果返回空列表/空字典
        """
        # 返回所有长期记忆
        if scene is None:
            return self._long_term_memory.copy()  # 返回副本，避免外部修改原始数据

        # 筛选指定场景的所有结果
        scene_memory = [item for item in self._long_term_memory if item.get("scene") == scene]
        if not scene_memory:
            return {} if latest_only else []

        # 返回最新一条或所有结果
        if latest_only:
            return scene_memory[-1]  # 最新一条在列表末尾
        return scene_memory

    def clear_expired_long_term_memory(self, keep_latest_n: int = 10) -> None:
        """
        清理过期长期记忆，仅保留最新的N条结果（避免内存溢出）
        :param keep_latest_n: 保留最新结果的数量（默认保留最近10条业务结果）
        """
        if len(self._long_term_memory) > keep_latest_n:
            self._long_term_memory = self._long_term_memory[-keep_latest_n:]


# 测试示例（可直接运行该文件验证功能）
if __name__ == "__main__":
    # 初始化记忆存储
    memory = MemoryStore()

    # 测试短期记忆
    print("=== 测试短期记忆 ===")
    memory.add_short_term_memory("user_input", "帮我分析2024年2月的销售数据")
    memory.add_short_term_memory("temp_param", {"time_range": "2024-02"})
    print("完整短期记忆：", memory.get_short_term_memory())
    print("获取指定键（user_input）：", memory.get_short_term_memory("user_input"))
    memory.clear_short_term_memory(["temp_param"])
    print("清理temp_param后的短期记忆：", memory.get_short_term_memory())

    # 测试长期记忆
    print("\n=== 测试长期记忆 ===")
    memory.add_long_term_memory(
        scene="销售分析",
        result="2024年2月销售额100万，同比增长20%",
        export_path="./202402_sales_report.xlsx",
        time_range="2024年2月"
    )
    memory.add_long_term_memory(
        scene="成本分析",
        result="2024年2月成本60万，环比下降5%",
        export_path="./202402_cost_report.xlsx",
        time_range="2024年2月"
    )
    print("所有长期记忆：", memory.get_long_term_memory())
    print("销售分析最新结果：", memory.get_long_term_memory(scene="销售分析"))
    memory.clear_expired_long_term_memory(keep_latest_n=1)
    print("保留最新1条长期记忆：", memory.get_long_term_memory())