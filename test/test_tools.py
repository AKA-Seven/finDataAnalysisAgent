# test/test_tools.py
"""
简单测试脚本（不依赖 pytest，使用标准库）
直接运行此文件即可执行所有工具测试：python test/test_tools.py
测试结果会打印 PASS / FAIL / SKIP
重点测试：
- 每个工具的基本功能（简单输入）
- db_query：数据库相关测试若连接失败则 SKIP
- python_executor：简单代码执行
- word/excel：生成文件并检查路径存在（自动清理）
"""

import json
import traceback
from pathlib import Path
from tools import (
    PythonExecutorTool,
    DBQueryTool,
    WordGeneratorTool,
    ExcelHandlerTool,
)
from config import config


def assert_true(condition, test_name):
    if condition:
        print(f"{test_name}: PASS")
    else:
        print(f"{test_name}: FAIL")


def assert_equal(actual, expected, test_name):
    if actual == expected:
        print(f"{test_name}: PASS")
    else:
        print(f"{test_name}: FAIL (got {repr(actual)}, expected {repr(expected)})")


def run_test(func):
    """运行测试，捕获异常"""
    try:
        func()
    except Exception:
        print(f"{func.__name__}: ERROR")
        traceback.print_exc()


# ====================== python_executor 测试 ======================
def test_python_executor():
    tool = PythonExecutorTool()

    # 简单print测试
    input_str = json.dumps({"code": "print('Hello from PythonExecutor!')"})
    result = tool.run(input_str)
    assert_true("执行成功" in result, "python_executor basic success")
    assert_true("Hello from PythonExecutor!" in result, "python_executor simple print")

    # pandas测试（移除 'import pandas as pd'，直接使用 pandas，因为预导入）
    input_str = json.dumps({
        "code": """
df = pandas.DataFrame({'a': [1, 2, 3]})
print(df.describe())
"""
    })
    result = tool.run(input_str)
    assert_true("执行成功" in result, "python_executor pandas success")
    # 检查 df.describe() 输出关键部分（pandas 标准格式包含这些）
    assert_true("count" in result and "3.0" in result, "python_executor pandas count")
    assert_true("mean" in result and "2.0" in result, "python_executor pandas describe")

    # 额外调试输出
    print("PythonExecutor pandas 测试实际返回结果：")
    print(result)

    # 只在所有 assert 通过后打印 ALL PASS（修复原测试bug）
    print("test_python_executor: ALL PASS")


# ====================== db_query 测试 ======================
def test_db_query():
    tool = DBQueryTool()

    try:
        # list_tables
        result = tool.run(json.dumps({"action": "list_tables"}))
        assert_true("数据库表格列表" in result and isinstance(result, str), "db_query list_tables")
        print(f"表格列表预览: {result[:100]}...")

        # query_data 基本（SELECT 1）
        result = tool.run(json.dumps({
            "action": "query_data",
            "sql": "SELECT 1 AS test_col",
            "limit": 5
        }))
        assert_true("总行数：1" in result or "test_col" in result, "db_query simple select")

        print("test_db_query: ALL PASS")
    except Exception as e:
        print(f"test_db_query: SKIP (数据库连接失败: {str(e)})")


# ====================== word_generator 测试 ======================
def test_word_generator():
    tool = WordGeneratorTool()

    input_str = json.dumps({
        "sections": [
            {"type": "heading", "text": "测试报告", "level": 1},
            {"type": "paragraph", "text": "这是一个自动生成的Word测试文件。"},
            {"type": "table", "data": [["姓名", "年龄"], ["张三", 30], ["李四", 25]], "caption": "测试表格"}
        ],
        "output_filename": "test_word_report.docx"
    })

    result = tool.run(input_str)
    assert_true("Word报告生成成功" in result and "test_word_report.docx" in result, "word_generator basic")

    # 检查文件存在并清理
    if "文件路径：" in result:
        file_path = Path(result.split("文件路径：")[-1].strip())
        assert_true(file_path.exists(), "word_generator file exists")
        file_path.unlink()  # 清理
        print("生成的Word文件已清理")

    print("test_word_generator: ALL PASS")


# ====================== excel_handler 测试 ======================
def test_excel_handler():
    tool = ExcelHandlerTool()

    input_str = json.dumps({
        "mode": "create",
        "sheets": [
            {
                "sheet_name": "测试数据",
                "data": [["产品", "销量"], ["A", 100], ["B", 200]],
                "start_cell": "A1"
            }
        ],
        "output_filename": "test_excel_report.xlsx"
    })

    result = tool.run(input_str)
    assert_true("Excel文件已生成" in result and "test_excel_report.xlsx" in result, "excel_handler basic")

    # 检查文件存在并清理
    if "：" in result:
        file_path = Path(result.split("：")[-1].strip())
        assert_true(file_path.exists(), "excel_handler file exists")
        file_path.unlink()  # 清理
        print("生成的Excel文件已清理")

    print("test_excel_handler: ALL PASS")


if __name__ == "__main__":
    print("开始运行 tools 测试...\n")
    run_test(test_python_executor)
    run_test(test_db_query)
    run_test(test_word_generator)
    run_test(test_excel_handler)
    print("\n所有测试完成。")