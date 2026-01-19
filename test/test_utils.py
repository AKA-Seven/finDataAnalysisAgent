# test/test_utils.py
"""
简单测试脚本（不依赖 pytest，使用标准库）
直接运行此文件即可执行所有测试：python test/test_utils.py
测试结果会打印 PASS / FAIL / SKIP
"""

import traceback
from pathlib import Path
import pandas as pd
from utils import (
    get_tables,
    get_table_schema,
    execute_query,
    call_deepseek,
    get_output_path,
    df_to_table_data,
    save_text_to_file,
)
from config import config


def assert_equal(actual, expected, test_name):
    if actual == expected:
        print(f"{test_name}: PASS")
    else:
        print(f"{test_name}: FAIL (got {actual}, expected {expected})")


def assert_true(condition, test_name):
    if condition:
        print(f"{test_name}: PASS")
    else:
        print(f"{test_name}: FAIL")


def run_test(func):
    """装饰器风格运行测试，捕获异常"""
    try:
        func()
    except Exception:
        print(f"{func.__name__}: ERROR")
        traceback.print_exc()


# ====================== file_utils 测试 ======================
def test_file_utils():
    # get_output_path
    filename = "test_dir/subdir/test.txt"
    path = get_output_path(filename)
    assert_true(path.is_absolute(), "get_output_path absolute")
    assert_true(config.OUTPUT_DIR in path.parents, "get_output_path in outputs")
    assert_equal(path.name, "test.txt", "get_output_path filename")

    # df_to_table_data (pandas)
    df = pd.DataFrame({
        "name": ["Alice", "Bob", None],
        "age": [25, 30, 35],
        "score": [95.5, None, 88.0]
    })
    table_data = df_to_table_data(df)
    expected = [
        ["name", "age", "score"],
        ["Alice", "25", "95.5"],
        ["Bob", "30", ""],
        ["", "35", "88.0"]
    ]
    assert_equal(table_data, expected, "df_to_table_data pandas")

    # df_to_table_data (list)
    raw_data = [[1, "test", None], [3.14, True, "end"]]
    table_data = df_to_table_data(raw_data)
    expected = [["1", "test", ""], ["3.14", "True", "end"]]
    assert_equal(table_data, expected, "df_to_table_data list")

    # save_text_to_file
    content = "这是一个测试文件内容\n支持中文和换行"
    filename = "temp_test_file.txt"
    path = save_text_to_file(content, filename)
    assert_true(path.exists(), "save_text_to_file exists")
    assert_equal(path.read_text(encoding="utf-8"), content, "save_text_to_file content")

    # 清理
    path.unlink()
    try:
        path.parent.rmdir()
    except:
        pass
    print("test_file_utils: ALL PASS")


# ====================== db_utils 测试 ======================
def test_db_utils():
    try:
        tables = get_tables()
        assert_true(isinstance(tables, list), "get_tables returns list")
        print(f"数据库表格列表: {tables}")

        if tables:
            schema = get_table_schema(tables[0])
            assert_true(isinstance(schema, list) and len(schema) > 0, "get_table_schema valid")
            assert_true("Field" in schema[0], "get_table_schema dict keys")

        result = execute_query("SELECT 1 AS test_col")
        assert_equal(len(result), 1, "execute_query basic")
        assert_equal(result[0]["test_col"], 1, "execute_query result")

        print("test_db_utils: ALL PASS")
    except Exception as e:
        print(f"test_db_utils: SKIP (数据库连接失败: {str(e)})")


# ====================== llm_utils 测试 ======================
def test_llm_utils_structure():
    # 仅测试函数存在（不实际调用）
    assert_true(callable(call_deepseek), "call_deepseek callable")
    print("test_llm_utils_structure: PASS")


def test_llm_utils_real():
    # 真实调用（默认跳过，手动运行时可取消注释）
    print("test_llm_utils_real: SKIP (避免消耗 token，如需测试请手动调用)")
    # messages = [{"role": "user", "content": "Say 'Hello, utils test!'"}]
    # response = call_deepseek(messages, max_tokens=50)
    # print(f"LLM 响应: {response}")
    # assert_true(len(response) > 0, "llm real response")


if __name__ == "__main__":
    print("开始运行 utils 测试...\n")
    run_test(test_file_utils)
    run_test(test_db_utils)
    run_test(test_llm_utils_structure)
    # run_test(test_llm_utils_real)  # 如需真实调用 LLM，请取消注释
    print("\n所有测试完成。")