# ai_report_agent/mcp/auto_data_analysis/descriptive_analysis.py（完善，继承BaseMCP）
from typing import Dict, Any, List
import pandas as pd
import os
from datetime import datetime
from mcp.base_mcp import BaseMCP
from ai_report_agent.config import get_global_config

class DescriptiveAnalysis(BaseMCP):
    """自动数据分析模块：描述性统计（实现BaseMCP接口）"""
    def __init__(self):
        super().__init__()
        self.analysis_dimensions = []  # 支持的分析维度
        self.default_output_path = ""  # 默认分析结果输出路径

    def init(self, module_config: Dict[str, Any] = None) -> bool:
        """
        初始化自动数据分析模块（加载分析维度、配置输出路径）
        :param module_config: 专属配置（如支持的统计方法）
        :return: 初始化是否成功
        """
        try:
            # 加载配置
            self.module_config = module_config or {}
            self.analysis_dimensions = self.module_config.get("analysis_dimensions", ["mean", "median", "std", "sum"])
            self.default_output_path = get_global_config().get("default_output_path", "./data/output/analysis")

            # 创建输出目录
            os.makedirs(self.default_output_path, exist_ok=True)

            self.initialized = True
            self.logger.info("自动数据分析模块（描述性统计）初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"自动数据分析模块初始化失败：{str(e)}")
            return False

    def execute(self, task_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行自动数据分析任务（标准化输入输出）
        【输入字段】（task_dict["params"]内）：
            - raw_data: 原始数据（NL2SQL返回的query_result，列表字典格式）
            - field_names: 结果字段名列表
            - analysis_type: 分析类型（如"descriptive"、"trend"、"anomaly"）
            - target_fields: 目标分析字段（如["cost_amount"]）
        【输出字段】（result["data"]内）：
            - statistics_result: 统计结果（字典格式，如{"cost_amount": {"mean": 15000}}）
            - analysis_chart_path: 分析图表路径（如趋势图、直方图）
            - analysis_report_path: 分析报告路径（json格式）
            - target_fields: 目标分析字段
        """
        # 1. 输入标准化
        if not self.initialized:
            return self._standardize_output("failed", error_msg="自动数据分析模块未初始化")
        standardized_task = self._standardize_input(task_dict)
        task_id = standardized_task["task_id"]
        task_params = standardized_task["params"]
        output_path = standardized_task["output_path"] or self.default_output_path

        try:
            # 2. 提取专属输入参数
            raw_data = task_params.get("raw_data", [])
            field_names = task_params.get("field_names", [])
            analysis_type = task_params.get("analysis_type", "descriptive")
            target_fields = task_params.get("target_fields", [])

            if not (raw_data and field_names and target_fields):
                raise Exception("缺少核心分析参数：raw_data/field_names/target_fields")
            if analysis_type != "descriptive":
                raise Exception(f"暂不支持分析类型：{analysis_type}，仅支持descriptive")

            # 3. 核心逻辑：转换数据 → 执行描述性统计 → 生成报告
            df = pd.DataFrame(raw_data, columns=field_names)
            statistics_result = self._calculate_statistics(df, target_fields)
            analysis_report_path = self._save_analysis_report(statistics_result, task_id, output_path)
            analysis_chart_path = self._generate_analysis_chart(df, target_fields, task_id, output_path)

            # 4. 构造专属输出数据
            analysis_data = {
                "statistics_result": statistics_result,
                "analysis_type": analysis_type,
                "target_fields": target_fields,
                "analysis_report_path": analysis_report_path,
                "analysis_chart_path": analysis_chart_path,
                "data_count": len(raw_data)
            }

            # 5. 输出标准化（填充文件路径、任务ID）
            result = self._standardize_output("success", data=analysis_data)
            result["task_id"] = task_id
            result["execute_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result["output_files"] = [analysis_report_path, analysis_chart_path]

            self.logger.info(f"自动数据分析任务 {task_id} 执行成功，生成报告：{analysis_report_path}")
            return result
        except Exception as e:
            error_msg = f"自动数据分析任务 {task_id} 执行失败：{str(e)}"
            self.logger.error(error_msg)
            result = self._standardize_output("failed", error_msg=error_msg)
            result["task_id"] = task_id
            return result

    def close(self) -> bool:
        """释放自动数据分析模块资源（无特殊资源，直接标记未初始化）"""
        try:
            self.initialized = False
            self.logger.info("自动数据分析模块资源释放成功")
            return True
        except Exception as e:
            self.logger.error(f"自动数据分析模块资源释放失败：{str(e)}")
            return False

    # 以下为辅助方法（简化实现）
    def _calculate_statistics(self, df: pd.DataFrame, target_fields: List[str]) -> Dict[str, Any]:
        """计算描述性统计结果"""
        statistics_result = {}
        for field in target_fields:
            if field not in df.columns:
                self.logger.warning(f"字段 {field} 不在数据中，跳过统计")
                continue
            field_stats = {}
            if "mean" in self.analysis_dimensions:
                field_stats["mean"] = round(df[field].mean(), 2)
            if "median" in self.analysis_dimensions:
                field_stats["median"] = round(df[field].median(), 2)
            if "std" in self.analysis_dimensions:
                field_stats["std"] = round(df[field].std(), 2)
            if "sum" in self.analysis_dimensions:
                field_stats["sum"] = round(df[field].sum(), 2)
            statistics_result[field] = field_stats
        return statistics_result

    def _save_analysis_report(self, statistics_result: Dict, task_id: str, output_path: str) -> str:
        """保存分析报告为json文件"""
        import json
        report_filename = f"analysis_report_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        report_path = os.path.join(output_path, report_filename)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(statistics_result, f, ensure_ascii=False, indent=4)
        return report_path

    def _generate_analysis_chart(self, df: pd.DataFrame, target_fields: List[str], task_id: str, output_path: str) -> str:
        """模拟生成分析图表（返回路径，实际项目中用matplotlib/seaborn实现）"""
        chart_filename = f"analysis_chart_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        chart_path = os.path.join(output_path, chart_filename)
        # 模拟生成图表（实际项目中绘制直方图/趋势图）
        with open(chart_path, "w") as f:
            f.write("Mock Chart Data")
        return chart_path