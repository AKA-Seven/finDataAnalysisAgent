"""数据分析通用模板：减少重复开发，标准化分析流程"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Optional, List
import os

# 设置中文字体（解决matplotlib中文显示问题）
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def data_analysis_template(
    data_source: str,
    output_dir: str = "./analysis_result",
    columns_to_analyze: Optional[List[str]] = None,
    drop_na: bool = True,
    generate_chart: bool = True
) -> Dict:
    """
    通用数据分析模板：数据读取→清洗→分析→可视化→结果导出

    Args:
        data_source: 数据来源（文件路径，支持csv/excel）
        output_dir: 结果输出目录
        columns_to_analyze: 指定分析列（None则分析所有列）
        drop_na: 是否删除缺失值
        generate_chart: 是否生成可视化图表

    Returns:
        分析结果字典（包含统计信息、文件路径等）
    """
    analysis_result = {
        "status": "success",
        "statistics": {},
        "output_files": [],
        "error": None
    }

    try:
        # 1. 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 2. 数据读取
        print("[TEMPLATE] 开始读取数据：", data_source)
        if data_source.endswith(".csv"):
            df = pd.read_csv(data_source, encoding="utf-8")
        elif data_source.endswith(".xlsx"):
            df = pd.read_excel(data_source)
        else:
            raise ValueError(f"不支持的文件格式：{data_source}")
        analysis_result["raw_data_shape"] = df.shape
        print(f"[TEMPLATE] 原始数据形状：{df.shape}")

        # 3. 数据清洗
        if drop_na:
            df = df.dropna()
            print(f"[TEMPLATE] 清洗后数据形状：{df.shape}")
        if columns_to_analyze:
            df = df[columns_to_analyze]
        analysis_result["clean_data_shape"] = df.shape

        # 4. 基础统计分析
        print("[TEMPLATE] 开始基础统计分析...")
        stats = df.describe(include="all").round(2)
        analysis_result["statistics"] = stats.to_dict()
        print("[TEMPLATE] 统计信息：")
        print(stats)

        # 5. 可视化（数值列）
        if generate_chart:
            print("[TEMPLATE] 生成可视化图表...")
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                # 子图：直方图+折线图
                fig, axes = plt.subplots(len(numeric_cols), 1, figsize=(10, 4 * len(numeric_cols)))
                if len(numeric_cols) == 1:
                    axes = [axes]

                for idx, col in enumerate(numeric_cols):
                    # 直方图
                    axes[idx].hist(df[col], bins=20, alpha=0.7, label=f"{col} 分布")
                    # 均值线
                    axes[idx].axvline(df[col].mean(), color="red", linestyle="--", label=f"均值：{df[col].mean():.2f}")
                    axes[idx].set_title(f"{col} 分布分析")
                    axes[idx].legend()
                    axes[idx].grid(alpha=0.3)

                # 保存图表
                chart_path = os.path.join(output_dir, "numeric_columns_analysis.png")
                plt.tight_layout()
                plt.savefig(chart_path, dpi=150, bbox_inches="tight")
                analysis_result["output_files"].append(chart_path)
                print(f"[TEMPLATE] 图表已保存：{chart_path}")
                plt.close()

        # 6. 导出分析结果
        result_path = os.path.join(output_dir, "analysis_result.csv")
        stats.to_csv(result_path, encoding="utf-8")
        analysis_result["output_files"].append(result_path)
        print(f"[TEMPLATE] 统计结果已导出：{result_path}")

        print("[TEMPLATE] 数据分析完成！")

    except Exception as e:
        analysis_result["status"] = "failed"
        analysis_result["error"] = str(e)
        print(f"[TEMPLATE] 分析失败：{str(e)}")

    return analysis_result


def export_analysis_result(
    result: Dict,
    export_path: str = "./final_analysis_report.txt"
) -> str:
    """
    导出分析结果报告（文本格式）

    Args:
        result: data_analysis_template返回的结果字典
        export_path: 报告导出路径

    Returns:
        报告文件路径
    """
    with open(export_path, "w", encoding="utf-8") as f:
        f.write("=== 数据分析报告 ===\\n")
        f.write(f"执行状态：{result['status']}\\n")
        if result["error"]:
            f.write(f"错误信息：{result['error']}\\n")
        else:
            f.write(f"原始数据形状：{result['raw_data_shape']}\\n")
            f.write(f"清洗后数据形状：{result['clean_data_shape']}\\n")
            f.write("\\n=== 核心统计信息 ===\\n")
            for col, stats in result["statistics"].items():
                f.write(f"列 {col}：\\n")
                for key, val in stats.items():
                    f.write(f"  {key}: {val}\\n")
            f.write("\\n=== 输出文件 ===\\n")
            for file in result["output_files"]:
                f.write(f"- {file}\\n")
    print(f"[EXPORT] 分析报告已导出：{export_path}")
    return export_path


# ===================== 模板测试 =====================
if __name__ == "__main__":
    # 生成测试数据
    test_data_path = "./test_sales_data.csv"
    test_df = pd.DataFrame({
        "product": ["A", "B", "C"] * 100,
        "sales": [100 + np.random.randint(10, 50) for _ in range(300)],
        "profit": [20 + np.random.randint(5, 20) for _ in range(300)],
        "date": pd.date_range(start="2024-01-01", periods=300)
    })
    test_df.to_csv(test_data_path, index=False, encoding="utf-8")

    # 执行模板分析
    result = data_analysis_template(
        data_source=test_data_path,
        columns_to_analyze=["sales", "profit"],
        drop_na=True,
        generate_chart=True
    )

    # 导出报告
    export_analysis_result(result, "./test_analysis_report.txt")

    # 清理测试文件
    try:
        os.remove(test_data_path)
        print("[TEST] 测试数据文件已清理")
    except Exception as e:
        print(f"[TEST] 测试数据清理失败：{e}")