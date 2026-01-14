import subprocess
import sys
import os
import tempfile
import resource
from typing import Dict, Tuple, Optional, List

# 沙箱默认配置（安全隔离+资源限制）
DEFAULT_PYTHON_SANDBOX_CONFIG = {
    "timeout": 30,  # 脚本执行超时时间（秒）
    "max_output_bytes": 2 * 1024 * 1024,  # 最大输出字节数（2MB）
    "max_memory_mb": 512,  # 最大内存限制（MB）
    "temp_dir_prefix": "python_analysis_sandbox_",
    "forbidden_modules": {"os", "subprocess", "socket", "shutil", "ctypes", "sysconfig", "pty"},
    "forbidden_functions": {"system", "popen", "spawn", "fork", "exec", "eval", "execfile"},
    "d_temp_dir": "./python_sandbox_temp"
}


class SafePythonSandbox:
    """Python脚本安全沙箱：环境隔离、资源限制、安全校验"""

    def __init__(self, sandbox_config: Optional[Dict] = None):
        self.config = DEFAULT_PYTHON_SANDBOX_CONFIG.copy()
        if sandbox_config:
            self.config.update(sandbox_config)

        # 解析配置
        self.timeout = self.config["timeout"]
        self.max_output_bytes = self.config["max_output_bytes"]
        self.max_memory_mb = self.config["max_memory_mb"]
        self.temp_dir_prefix = self.config["temp_dir_prefix"]
        self.forbidden_modules = set(self.config["forbidden_modules"])
        self.forbidden_functions = set(self.config["forbidden_functions"])
        self.d_temp_root = self.config["d_temp_dir"]

        # 创建临时目录
        self.temp_dir = self._create_temp_dir()
        print(f"[OK] Python沙箱初始化完成，临时目录：{self.temp_dir}")

    def _create_temp_dir(self) -> str:
        """创建隔离的临时目录"""
        try:
            os.makedirs(self.d_temp_root, exist_ok=True)
            temp_dir = tempfile.mkdtemp(
                prefix=self.temp_dir_prefix,
                dir=self.d_temp_root
            )
            return temp_dir
        except Exception as e:
            print(f"[WARN] 自定义临时目录创建失败：{str(e)}，降级回系统默认临时目录")
            temp_dir = tempfile.mkdtemp(prefix=self.temp_dir_prefix)
            return temp_dir

    def _check_script_safety(self, script: str) -> Tuple[bool, str]:
        """Python脚本安全性校验：禁用危险模块/函数、检查敏感操作"""
        if not script or not script.strip():
            return False, "错误：Python脚本内容为空"

        script_clean = script.strip()

        # 1. 检查禁用模块导入
        for mod in self.forbidden_modules:
            import_patterns = [
                f"import {mod}",
                f"from {mod} import",
                f"import {mod} as",
                f"from {mod} .",  # 处理 from mod.sub import 情况
            ]
            for pattern in import_patterns:
                if pattern in script_clean:
                    return False, f"禁止导入危险模块「{mod}」，脚本包含：{pattern}"

        # 2. 检查禁用函数调用
        for func in self.forbidden_functions:
            if func in script_clean:
                # 排除合法的变量名/字符串（简单过滤）
                if not any([
                    f"def {func}(",
                    f"class {func}(",
                    f'"{func}"',
                    f"'{func}'",
                    f"`{func}`"
                ]) in script_clean:
                    return False, f"禁止调用危险函数「{func}」，脚本包含敏感操作"

        # 3. 检查敏感关键字（代码执行/文件操作）
        dangerous_keywords = {"open(", "file(", "os.remove", "os.rmdir", "shutil.rmtree"}
        for keyword in dangerous_keywords:
            if keyword in script_clean:
                return False, f"脚本包含危险操作「{keyword}」，禁止执行"

        return True, "Python脚本安全校验通过"

    def _set_resource_limits(self):
        """设置子进程资源限制（内存/CPU）"""
        # 限制内存：max_memory_mb MB 转换为字节
        max_memory_bytes = self.max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        # 限制CPU时间：超时时间的1.5倍
        resource.setrlimit(resource.RLIMIT_CPU, (int(self.timeout * 1.5), int(self.timeout * 1.5)))

    def _generate_standalone_exec_code(self, script: str) -> str:
        """生成独立可运行的隔离执行代码"""
        # 禁止模块列表转字符串
        forbidden_modules_str = str(list(self.forbidden_modules))
        # 核心执行代码：隔离环境 + 资源限制 + 脚本执行
        standalone_code = f"""
# 沙箱隔离执行代码（自动生成，禁止修改）
import sys
import os

# ===================== 第一步：禁用危险模块 =====================
class ForbiddenModule:
    def __getattr__(self, attr_name):
        raise ImportError("模块被沙箱禁止使用：{{attr_name}}")

# 覆盖危险模块，防止导入/使用
forbidden_modules = {forbidden_modules_str}
for mod_name in forbidden_modules:
    if mod_name in sys.modules:
        sys.modules[mod_name] = ForbiddenModule()
    sys.modules[mod_name] = ForbiddenModule()

# ===================== 第二步：设置资源限制 =====================
try:
    import resource
    # 内存限制：{self.max_memory_mb}MB
    max_memory = {self.max_memory_mb} * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
    # CPU时间限制：{int(self.timeout * 1.5)}秒
    resource.setrlimit(resource.RLIMIT_CPU, ({int(self.timeout * 1.5)}, {int(self.timeout * 1.5)}))
except ImportError:
    print("[WARN] 资源限制模块不可用（非Linux系统），仅启用超时控制")

# ===================== 第三步：执行用户脚本 =====================
print("[INFO] 开始执行数据分析脚本...")
try:
    # 执行用户脚本（隔离命名空间）
    exec_globals = {{}}
    exec(\"\"\"{script}\"\"\", exec_globals)
    print("[INFO] 数据分析脚本执行完成")
except Exception as e:
    print(f"[ERROR] 脚本执行异常：{{type(e).__name__}} - {{str(e)}}")
    raise
"""
        # 清理空行，保证代码格式
        clean_lines = []
        for line in standalone_code.splitlines():
            if line.strip() or (line and not line.isspace()):
                clean_lines.append(line)
        while clean_lines and not clean_lines[0].strip():
            clean_lines.pop(0)
        return "\\n".join(clean_lines)

    def _run_subprocess(self, exec_file_path: str) -> Tuple[bool, str]:
        """子进程运行隔离脚本，控制超时和输出"""
        try:
            result = subprocess.run(
                [sys.executable, exec_file_path],
                cwd=self.temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='replace',
                preexec_fn=self._set_resource_limits if sys.platform != "win32" else None
            )

            # 截断超大输出
            stdout = result.stdout[:self.max_output_bytes]
            stderr = result.stderr[:self.max_output_bytes]
            full_output = f"[STDOUT]\\n{stdout}\\n\\n[STDERR]\\n{stderr}"

            if result.returncode != 0:
                return False, f"脚本执行失败（返回码：{result.returncode}）\\n{full_output}"
            return True, full_output

        except subprocess.TimeoutExpired:
            return False, f"脚本执行超时（超过 {self.timeout} 秒）"
        except Exception as e:
            return False, f"子进程启动失败：{str(e)}"

    def run_script_in_sandbox(self, script: str) -> Tuple[bool, str]:
        """对外接口：在沙箱中运行Python脚本"""
        # 1. 安全校验
        is_safe, safety_msg = self._check_script_safety(script)
        if not is_safe:
            return False, f"安全校验失败：{safety_msg}"

        # 2. 生成隔离执行代码
        exec_code = self._generate_standalone_exec_code(script)

        # 3. 写入临时执行文件
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='_sandbox_exec.py',
            dir=self.temp_dir,
            delete=False,
            encoding='utf-8'
        )
        temp_file.write(exec_code)
        temp_file_path = temp_file.name
        temp_file.close()

        # 4. 子进程执行
        exec_success, exec_output = self._run_subprocess(temp_file_path)

        # 5. 清理临时文件
        try:
            os.remove(temp_file_path)
        except Exception as e:
            print(f"[WARN] 临时文件清理失败：{str(e)}")

        # 6. 返回结果
        if exec_success:
            return True, f"[OK] 脚本执行成功\\n\\n{exec_output}"
        else:
            return False, f"[ERROR] 脚本执行失败\\n\\n{exec_output}"

    def cleanup(self) -> str:
        """清理沙箱所有临时资源"""
        try:
            # 递归删除临时目录及文件
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"[WARN] 无法删除文件：{file_path}，错误：{str(e)}")
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        os.rmdir(dir_path)
                    except Exception as e:
                        print(f"[WARN] 无法删除目录：{dir_path}，错误：{str(e)}")
            os.rmdir(self.temp_dir)

            # 尝试删除根临时目录（空则删）
            try:
                os.rmdir(self.d_temp_root)
            except Exception:
                pass

            return f"[OK] 沙箱临时资源清理完成，已删除目录：{self.temp_dir}"
        except Exception as e:
            return f"[WARN] 沙箱资源清理失败：{str(e)}"


# ===================== 自执行测试 =====================
if __name__ == "__main__":
    # 测试1：合法的数据分析脚本（基于模板）
    test_script = '''
import pandas as pd
import matplotlib.pyplot as plt

# 模拟数据生成
data = pd.DataFrame({{
    "date": pd.date_range(start="2024-01-01", periods=30),
    "sales": [100 + i * 5 + (i % 7) * 10 for i in range(30)],
    "profit": [20 + i * 2 + (i % 7) * 3 for i in range(30)]
}})

# 数据清洗
data = data.dropna()
data["profit_rate"] = (data["profit"] / data["sales"] * 100).round(2)

# 基础分析
print("=== 销售数据统计 ===")
print(f"总销售额：{data['sales'].sum():.2f}")
print(f"平均利润率：{data['profit_rate'].mean():.2f}%")
print("\\n=== 前5条数据 ===")
print(data.head())

# 禁用可视化（测试环境）
# plt.plot(data["date"], data["sales"], label="销售额")
# plt.plot(data["date"], data["profit"], label="利润")
# plt.legend()
# plt.savefig("sales_analysis.png")
'''

    # 测试2：危险脚本（用于校验）
    dangerous_script = '''
import os
os.system("rm -rf /")  # 危险操作
'''

    # 初始化沙箱
    sandbox = SafePythonSandbox()
    try:
        print("===== 测试1：合法数据分析脚本 =====")
        success, output = sandbox.run_script_in_sandbox(test_script)
        print(output)

        print("\\n===== 测试2：危险脚本（安全校验） =====")
        success, output = sandbox.run_script_in_sandbox(dangerous_script)
        print(output)
    finally:
        # 清理资源
        cleanup_msg = sandbox.cleanup()
        print(f"\\n{cleanup_msg}")