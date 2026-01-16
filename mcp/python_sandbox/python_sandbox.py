# ai_report_agent/mcp/python_sandbox/sandbox_core.py（完善，继承BaseMCP）
from typing import Dict, Any
import os
import tempfile
from datetime import datetime
from mcp.base_mcp import BaseMCP
from config import get_global_config

class PythonSandbox(BaseMCP):
    """Python沙箱模块：安全执行自定义脚本（实现BaseMCP接口）"""
    def __init__(self):
        super().__init__()
        self.sandbox_dir = ""  # 沙箱工作目录
        self.resource_limit = {}  # 资源限制（内存、超时）
        self.temp_script_path = ""  # 临时脚本路径

    def init(self, module_config: Dict[str, Any] = None) -> bool:
        """
        初始化Python沙箱（创建工作目录、配置资源限制）
        :param module_config: 专属配置（如内存限制、超时时间）
        :return: 初始化是否成功
        """
        try:
            # 加载配置
            self.module_config = module_config or {}
            self.resource_limit = {
                "max_memory": self.module_config.get("max_memory", "1G"),
                "timeout": self.module_config.get("timeout", 30)  # 超时时间（秒）
            }
            self.sandbox_dir = get_global_config().get("sandbox_dir", "./data/temp/sandbox")

            # 创建沙箱目录
            os.makedirs(self.sandbox_dir, exist_ok=True)

            self.initialized = True
            self.logger.info("Python沙箱模块初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"Python沙箱模块初始化失败：{str(e)}")
            return False

    def execute(self, task_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Python沙箱任务（标准化输入输出）
        【输入字段】（task_dict["params"]内）：
            - script_content: 脚本内容（字符串格式，或模板名称）
            - script_params: 脚本执行参数（字典格式，如{"data_path": "./data/wide_tables/cost.csv"}）
            - script_template: 脚本模板名称（如"trend_analysis_template.py"）
            - save_script: 是否保存脚本文件（True/False）
        【输出字段】（result["data"]内）：
            - script_exec_result: 脚本执行结果（标准输出/返回值）
            - script_log: 脚本执行日志
            - temp_script_path: 临时脚本路径（若保存）
            - exec_status: 执行状态（如"completed"、"timeout"）
        """
        # 1. 输入标准化
        if not self.initialized:
            return self._standardize_output("failed", error_msg="Python沙箱模块未初始化")
        standardized_task = self._standardize_input(task_dict)
        task_id = standardized_task["task_id"]
        task_params = standardized_task["params"]
        output_path = standardized_task["output_path"]

        try:
            # 2. 提取专属输入参数
            script_content = task_params.get("script_content", "")
            script_params = task_params.get("script_params", {})
            script_template = task_params.get("script_template", "")
            save_script = task_params.get("save_script", False)

            if not (script_content or script_template):
                raise Exception("缺少核心脚本参数：script_content/script_template")

            # 3. 核心逻辑：生成临时脚本 → 安全执行 → 收集结果（简化实现，模拟执行）
            self.temp_script_path = self._generate_temp_script(script_content, script_template, task_id, save_script, output_path)
            exec_result, exec_log, exec_status = self._execute_script(script_params)

            # 4. 构造专属输出数据
            sandbox_data = {
                "script_exec_result": exec_result,
                "script_log": exec_log,
                "temp_script_path": self.temp_script_path if save_script else "",
                "exec_status": exec_status,
                "resource_limit": self.resource_limit
            }

            # 5. 输出标准化
            result = self._standardize_output("success", data=sandbox_data)
            result["task_id"] = task_id
            result["execute_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if save_script:
                result["output_files"] = [self.temp_script_path]

            self.logger.info(f"Python沙箱任务 {task_id} 执行成功，执行状态：{exec_status}")
            return result
        except Exception as e:
            error_msg = f"Python沙箱任务 {task_id} 执行失败：{str(e)}"
            self.logger.error(error_msg)
            result = self._standardize_output("failed", error_msg=error_msg)
            result["task_id"] = task_id
            return result

    def close(self) -> bool:
        """释放沙箱资源（删除临时脚本、清理工作目录）"""
        try:
            # 删除临时脚本（若未配置保存）
            if self.temp_script_path and os.path.exists(self.temp_script_path) and not self.module_config.get("save_temp_script", False):
                os.remove(self.temp_script_path)
                self.logger.info(f"删除临时脚本：{self.temp_script_path}")
            self.initialized = False
            self.logger.info("Python沙箱模块资源释放成功")
            return True
        except Exception as e:
            self.logger.error(f"Python沙箱模块资源释放失败：{str(e)}")
            return False

    # 以下为辅助方法
    def _generate_temp_script(self, script_content: str, script_template: str, task_id: str, save_script: bool, output_path: str) -> str:
        """生成临时脚本文件"""
        # 模拟加载模板（实际项目中从模板目录读取）
        if script_template:
            script_content = f"# 模板：{script_template}\n" + script_content

        # 生成临时脚本路径
        if save_script:
            script_filename = f"sandbox_script_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.py"
            script_path = os.path.join(output_path, script_filename)
        else:
            temp_file = tempfile.NamedTemporaryFile(dir=self.sandbox_dir, suffix=".py", delete=False)
            script_path = temp_file.name
            temp_file.write(script_content.encode("utf-8"))
            temp_file.close()

        # 保存脚本内容（若开启保存）
        if save_script:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

        return script_path

    def _execute_script(self, script_params: Dict) -> (str, str, str):
        """模拟执行脚本（实际项目中实现安全隔离、资源限制）"""
        # 模拟执行结果
        exec_result = f"脚本执行成功，参数：{script_params}，返回结果：OK"
        exec_log = f"[{datetime.now()}] 脚本开始执行 → [{datetime.now()}] 脚本执行完成"
        exec_status = "completed"
        return exec_result, exec_log, exec_status