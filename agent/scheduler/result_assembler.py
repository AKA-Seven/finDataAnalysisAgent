# ai_report_agent/agent/scheduler/result_assembler.py
from typing import Dict, Any, List, Optional
import os
from datetime import datetime
from utils import get_logger, write_file, get_abs_path

class ResultAssembler:
    """结果整合器：汇总多MCP模块结果，格式化生成最终交付物"""
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.default_output_dir = "./data/output/final"
        os.makedirs(self.default_output_dir, exist_ok=True)

    def assemble_single_result(self, mcp_result: Dict[str, Any], output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        整合单个MCP模块执行结果，生成最终交付物
        :param mcp_result: MCP模块执行结果
        :param output_dir: 最终输出目录
        :return: 整合后的最终结果
        """
        if not mcp_result:
            raise ValueError("MCP执行结果不能为空")

        # 1. 校验MCP结果状态
        task_id = mcp_result.get("task_id", "unknown_task")
        mcp_status = mcp_result.get("status", "failed")
        if mcp_status == "failed":
            self.logger.warning(f"任务 {task_id} MCP执行失败，跳过结果整合：{mcp_result.get('error_msg')}")
            return mcp_result

        # 2. 初始化输出目录
        output_dir = output_dir or self.default_output_dir
        os.makedirs(output_dir, exist_ok=True)

        try:
            # 3. 提取MCP核心数据，按模块类型格式化
            mcp_module = mcp_result.get("mcp_module", "unknown_mcp")
            mcp_data = mcp_result.get("data", {})
            final_data = {}

            # 按MCP模块类型分别处理
            if mcp_module == "SQLGenerator":
                final_data = self._assemble_nl2sql_result(mcp_data, task_id, output_dir)
            elif mcp_module == "DescriptiveAnalysis":
                final_data = self._assemble_analysis_result(mcp_data, task_id, output_dir)
            elif mcp_module == "ExcelParser":
                final_data = self._assemble_excel_result(mcp_data, task_id, output_dir)
            elif mcp_module == "PythonSandbox":
                final_data = self._assemble_sandbox_result(mcp_data, task_id, output_dir)
            else:
                final_data = mcp_data

            # 4. 生成最终汇总报告（json格式）
            final_report_path = self._generate_final_report(
                task_id=task_id,
                mcp_module=mcp_module,
                final_data=final_data,
                output_dir=output_dir
            )

            # 5. 构造整合后的最终结果
            assembled_result = {
                "task_id": task_id,
                "status": "success",
                "mcp_module": mcp_module,
                "final_data": final_data,
                "final_report_path": final_report_path,
                "output_files": mcp_result.get("output_files", []) + [final_report_path],
                "assemble_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error_msg": ""
            }

            self.logger.info(f"任务 {task_id} 结果整合完成，生成最终报告：{final_report_path}")
            return assembled_result
        except Exception as e:
            error_msg = f"任务 {task_id} 结果整合失败：{str(e)}"
            self.logger.error(error_msg)
            return {
                "task_id": task_id,
                "status": "failed",
                "error_msg": error_msg,
                "assemble_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def assemble_batch_results(self, result_list: List[Dict[str, Any]], output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        整合批量（串联/并行）任务结果，生成汇总报告
        :param result_list: MCP模块执行结果列表
        :param output_dir: 最终输出目录
        :return: 批量整合后的最终结果
        """
        if not result_list:
            raise ValueError("任务结果列表不能为空")

        output_dir = output_dir or self.default_output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 1. 统计结果状态
        success_count = 0
        failed_count = 0
        batch_output_files = []
        batch_final_data = []

        for result in result_list:
            task_id = result.get("task_id", "unknown_task")
            if result.get("status") == "success":
                # 整合单个结果
                assembled_single = self.assemble_single_result(result, output_dir)
                batch_final_data.append(assembled_single)
                batch_output_files.extend(assembled_single.get("output_files", []))
                success_count += 1
            else:
                batch_final_data.append(result)
                failed_count += 1

        # 2. 生成批量汇总报告
        batch_report = {
            "batch_task_count": len(result_list),
            "success_count": success_count,
            "failed_count": failed_count,
            "assemble_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "task_results": batch_final_data
        }
        batch_report_path = self._generate_final_report(
            task_id="batch_task_summary",
            mcp_module="batch_assemble",
            final_data=batch_report,
            output_dir=output_dir
        )
        batch_output_files.append(batch_report_path)

        # 3. 构造批量整合结果
        return {
            "batch_status": "success" if failed_count == 0 else "partially_success",
            "success_count": success_count,
            "failed_count": failed_count,
            "batch_report_path": batch_report_path,
            "output_files": list(set(batch_output_files)),  # 去重
            "assemble_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # 以下为各MCP模块结果的专属整合方法
    def _assemble_nl2sql_result(self, nl2sql_data: Dict[str, Any], task_id: str, output_dir: str) -> Dict[str, Any]:
        """整合NL2SQL模块结果"""
        # 生成SQL结果CSV文件（可选）
        query_result = nl2sql_data.get("query_result", [])
        if query_result:
            import csv
            csv_filename = f"nl2sql_result_{task_id}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            field_names = nl2sql_data.get("field_names", [])
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=field_names)
                writer.writeheader()
                writer.writerows(query_result)
            nl2sql_data["csv_result_path"] = get_abs_path(csv_path)
        return nl2sql_data

    def _assemble_analysis_result(self, analysis_data: Dict[str, Any], task_id: str, output_dir: str) -> Dict[str, Any]:
        """整合自动数据分析模块结果"""
        # 补充分析结果的可视化路径（已由MCP生成，此处仅校验）
        chart_path = analysis_data.get("analysis_chart_path", "")
        if chart_path and not os.path.exists(chart_path):
            self.logger.warning(f"分析图表 {chart_path} 不存在")
        return analysis_data

    def _assemble_excel_result(self, excel_data: Dict[str, Any], task_id: str, output_dir: str) -> Dict[str, Any]:
        """整合Excel Parser模块结果"""
        # 校验Excel文件是否存在
        excel_path = excel_data.get("excel_file_path", "")
        if excel_path and not os.path.exists(excel_path):
            self.logger.warning(f"Excel文件 {excel_path} 不存在")
        return excel_data

    def _assemble_sandbox_result(self, sandbox_data: Dict[str, Any], task_id: str, output_dir: str) -> Dict[str, Any]:
        """整合Python Sandbox模块结果"""
        # 保存脚本执行日志（已由MCP生成，此处仅汇总）
        return sandbox_data

    def _generate_final_report(self, task_id: str, mcp_module: str, final_data: Dict[str, Any], output_dir: str) -> str:
        """生成最终汇总报告（json格式）"""
        import json
        report_filename = f"final_report_{mcp_module}_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        report_path = os.path.join(output_dir, report_filename)
        final_report = {
            "task_id": task_id,
            "mcp_module": mcp_module,
            "generate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": final_data
        }
        write_file(report_path, json.dumps(final_report, ensure_ascii=False, indent=4))
        return get_abs_path(report_path)