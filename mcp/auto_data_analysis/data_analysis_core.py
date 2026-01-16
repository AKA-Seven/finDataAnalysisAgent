import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List


# 核心：灵活生成分析代码，无需求时回退到标准流程
class DfStructureExtractor:
    """DataFrame结构提取器（提取列名、数据类型等，为大模型提供精准上下文）"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化DF结构提取器
        :param df: 输入的Pandas DataFrame（仅提取结构，不操作/修改任何数据）
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("输入必须是Pandas DataFrame对象")

        self.df = df
        self.df_structure: Dict = {
            "shape": df.shape,
            "columns": [],
            "numeric_columns": [],
            "datetime_columns": [],
            "categorical_columns": []
        }
        self._extract_df_structure()

    def _extract_df_structure(self) -> None:
        """提取DF的核心结构信息（列类型、非空值、缺失值等）"""
        for col in self.df.columns:
            col_info = {
                "column_name": col,
                "dtype": str(self.df[col].dtype),
                "non_null_count": int(self.df[col].notna().sum()),
                "null_count": int(self.df[col].isna().sum())
            }
            self.df_structure["columns"].append(col_info)

            # 列类型分类（用于大模型针对性生成代码）
            if pd.api.types.is_numeric_dtype(self.df[col]):
                self.df_structure["numeric_columns"].append(col)
            elif pd.api.types.is_datetime64_any_dtype(self.df[col]):
                self.df_structure["datetime_columns"].append(col)
            elif pd.api.types.is_object_dtype(self.df[col]) or pd.api.types.is_categorical_dtype(self.df[col]):
                self.df_structure["categorical_columns"].append(col)

    def generate_structure_prompt(self) -> str:
        """生成大模型可识别的DF结构格式化提示词"""
        if not self.df_structure["columns"]:
            return "错误：输入DataFrame无有效列，无法进行数据分析"

        # 构造DF结构提示词
        prompt_parts = [
            "### DataFrame 基础结构信息",
            f"数据规模：{self.df_structure['shape'][0]} 行 × {self.df_structure['shape'][1]} 列",
            f"数值列（支持统计/聚合/异常检测）：{', '.join(self.df_structure['numeric_columns']) or '无'}",
            f"时间列（支持趋势/时序分析）：{', '.join(self.df_structure['datetime_columns']) or '无'}",
            f"分类列（支持分组/维度分析）：{', '.join(self.df_structure['categorical_columns']) or '无'}",
            "### 列详情（非空值/缺失值）",
            "---"
        ]

        # 拼接列详情
        for col in self.df_structure["columns"]:
            prompt_parts.append(
                f"列名：{col['column_name']} | 类型：{col['dtype']} | 非空值：{col['non_null_count']} | 缺失值：{col['null_count']}"
            )

        return "\n".join(prompt_parts)


class LLMautoAnalysisClient:
    """大模型自动化分析代码生成客户端（参数化传入API，支持灵活需求/标准流程回退）"""

    def __init__(self, llm_api_config: Dict):
        """
        初始化大模型客户端
        :param llm_api_config: 大模型API配置（兼容DeepSeek/GPT等平台，参数化传入）
        """
        self.llm_config = llm_api_config
        self.api_key = llm_api_config.get("api_key", "")
        self.base_url = llm_api_config.get("base_url", "")
        self.model_name = llm_api_config.get("model_name", "")
        self.endpoint = llm_api_config.get("endpoint", "")
        self.max_tokens = llm_api_config.get("max_tokens", 3000)
        self.temperature = llm_api_config.get("temperature", 0.1)

        # 校验配置完整性
        self._validate_llm_config()

    def _validate_llm_config(self) -> None:
        """校验大模型配置必填项"""
        required_configs = ["api_key", "base_url", "model_name"]
        missing_configs = [req for req in required_configs if not self.llm_config.get(req)]
        if missing_configs:
            raise Exception(f"大模型配置缺失必填项：{', '.join(missing_configs)}")

    def _is_blank_or_general_query(self, user_nl: str) -> bool:
        """判断用户需求是否为空/模糊，是否需要回退到标准流程"""
        if not user_nl or not user_nl.strip():
            return True

        # 去除空白后的纯文本
        clean_nl = user_nl.strip().lower()
        # 模糊需求关键词（判定为无具体需求，触发标准流程）
        general_keywords = ["分析数据", "数据处理", "默认分析", "完整分析", "全量分析", "帮我分析"]

        # 判定条件：1. 文本长度过短 或 2. 包含模糊需求关键词
        return len(clean_nl) < 10 or any(keyword in clean_nl for keyword in general_keywords)

    def _generate_analysis_prompt(self, user_nl: str, df_structure_prompt: str) -> List[Dict]:
        """
        生成大模型提示词（核心：区分灵活需求/标准流程）
        :param user_nl: 用户自然语言需求
        :param df_structure_prompt: DataFrame结构提示词
        :return: 大模型Chat API消息体
        """
        # 判定是否需要回退到标准流程
        use_standard_flow = self._is_blank_or_general_query(user_nl)

        # 标准流程定义（无具体需求时的兜底分析步骤）
        standard_flow_definition = """
        标准数据分析流程（按以下步骤依次执行）：
        1.  数据预处理：缺失值统计、重复值清理（不删除原始数据，仅生成清理后的副本）
        2.  描述性统计：数值列的均值、中位数、方差、标准差、四分位数、分组聚合（按分类列）
        3.  趋势分析（如有时间列）：时间序列聚合（日/月/年）、环比增长率计算、趋势可视化保存
        4.  异常检测：IQR法识别数值列离群值、生成异常数据子集、异常预警标注
        5.  结果汇总：返回包含所有分析结果的字典，包含统计数据、图表路径、异常数据
        """

        # 灵活需求提示词（有具体需求时）
        flexible_system_prompt = f"""
你是专业的Python自动化数据分析代码生成器，需满足以下要求：
1.  基于提供的DataFrame结构：{df_structure_prompt}
2.  严格按照用户自然语言需求生成对应分析代码，支持任意数据分析功能（不限于统计/趋势/异常）
3.  生成的Python代码要求：
    - 输入：一个名为df的Pandas DataFrame对象（直接操作df，无需重新读取数据）
    - 输出：明确的分析结果（统计字典、可视化图表、异常df、聚合结果等，按需返回）
    - 包含必要库导入（pandas、numpy、matplotlib、scipy等）和完整异常处理
    - 格式规范、注释清晰，可直接在Python沙箱中运行，无额外解释
    - 仅做数据分析，不修改/删除原始数据，不打印无关信息
    - 最终返回可直接使用的分析结果对象（如analysis_result、anomaly_df等）
4.  若涉及可视化，将图表保存为本地文件（不直接显示），返回图表文件路径。
"""

        # 标准流程提示词（无具体需求时）
        standard_system_prompt = f"""
你是专业的Python自动化数据分析代码生成器，需满足以下要求：
1.  基于提供的DataFrame结构：{df_structure_prompt}
2.  用户无具体分析需求，执行{standard_flow_definition}
3.  生成的Python代码要求：
    - 输入：一个名为df的Pandas DataFrame对象（直接操作df，无需重新读取数据）
    - 输出：包含标准流程所有结果的汇总字典（key对应各步骤结果，便于下游解析）
    - 包含必要库导入（pandas、numpy、matplotlib、scipy等）和完整异常处理
    - 格式规范、注释清晰，可直接在Python沙箱中运行，无额外解释
    - 仅做数据分析，不修改/删除原始数据，不打印无关信息
    - 可视化图表保存为本地文件，返回图表路径，不直接显示。
"""

        # 构造系统提示词（根据需求类型切换）
        system_prompt = standard_system_prompt if use_standard_flow else flexible_system_prompt

        # 构造用户提示词（无具体需求时明确告知执行标准流程）
        user_prompt = (
            "请执行标准数据分析流程，生成完整的Python分析代码"
            if use_standard_flow
            else f"请根据以下需求生成Python分析代码：{user_nl}"
        )

        # 返回大模型兼容的消息体
        return [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ]

    def generate_analysis_code(self, user_nl: str, df_structure_prompt: str) -> Tuple[bool, Optional[str]]:
        """
        核心方法：生成Python分析代码（灵活需求/标准流程二选一）
        :param user_nl: 用户自然语言需求
        :param df_structure_prompt: DataFrame结构提示词
        :return: 生成结果（成功/失败）、对应的Python分析代码
        """
        try:
            # 1. 输入校验
            if "错误" in df_structure_prompt:
                return False, f"无效DataFrame结构：{df_structure_prompt}"

            # 2. 生成大模型请求消息体
            messages = self._generate_analysis_prompt(user_nl, df_structure_prompt)

            # 3. 模拟大模型API调用（实际场景替换为真实API请求，兼容DeepSeek格式）
            generated_code = self._mock_generate_analysis_code(messages, self._is_blank_or_general_query(user_nl))

            # 4. 代码后处理（格式化、补全依赖、确保可运行）
            cleaned_code = self._clean_analysis_code(generated_code)

            print(f"✅ 分析代码生成成功（{'标准流程' if self._is_blank_or_general_query(user_nl) else '自定义需求'}）")
            return True, cleaned_code
        except Exception as e:
            return False, f"代码生成失败：{str(e)}"

    def _mock_generate_analysis_code(self, messages: List[Dict], use_standard_flow: bool) -> str:
        """
        模拟生成分析代码（区分标准流程/灵活需求，实际场景替换为真实大模型返回）
        :param use_standard_flow: 是否使用标准流程
        :return: 完整Python分析代码
        """
        if use_standard_flow:
            # 标准流程代码模板（兜底：数据预处理→描述性统计→趋势分析→异常检测→结果汇总）
            code_template = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# 配置matplotlib中文显示（解决中文乱码）
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

def standard_data_analysis(df: pd.DataFrame) -> Dict:
    """
    标准自动化数据分析流程（无具体需求时兜底执行）
    :param df: 输入的Pandas DataFrame
    :return: 包含所有分析结果的汇总字典
    """
    # 初始化分析结果汇总
    analysis_summary = {
        "analysis_status": "success",
        "data_preprocess": {},
        "descriptive_statistics": {},
        "trend_analysis": {},
        "anomaly_detection": {},
        "error": None
    }

    try:
        # ===================== 步骤1：数据预处理（缺失值/重复值统计） =====================
        df_clean = df.copy()  # 生成副本，不修改原始数据
        analysis_summary["data_preprocess"]["original_shape"] = df.shape
        analysis_summary["data_preprocess"]["null_value_stat"] = df.isnull().sum().to_dict()
        analysis_summary["data_preprocess"]["duplicate_count"] = int(df.duplicated().sum())

        # 清理重复值（保留第一个）
        df_clean = df_clean.drop_duplicates(keep="first")
        analysis_summary["data_preprocess"]["cleaned_shape"] = df_clean.shape

        # ===================== 步骤2：描述性统计（数值列/分组聚合） =====================
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        if not numeric_cols.empty:
            # 整体描述性统计
            desc_stats = df_clean[numeric_cols].describe().round(2)
            analysis_summary["descriptive_statistics"]["overall_stats"] = desc_stats.to_dict()

            # 分类列分组聚合（如有）
            categorical_cols = df_clean.select_dtypes(include=[object, "category"]).columns
            if not categorical_cols.empty:
                group_agg = df_clean.groupby(categorical_cols[0])[numeric_cols].agg(
                    ["mean", "median", "std", "sum"]
                ).round(2)
                analysis_summary["descriptive_statistics"]["group_aggregation"] = group_agg.to_dict()

        # ===================== 步骤3：趋势分析（时间序列，如有时间列） =====================
        datetime_cols = df_clean.select_dtypes(include=["datetime64"]).columns
        if not datetime_cols.empty:
            df_trend = df_clean.copy()
            df_trend.set_index(datetime_cols[0], inplace=True)

            # 月度聚合（数值列均值）
            monthly_agg = df_trend[numeric_cols].resample("M").mean().round(2)
            analysis_summary["trend_analysis"]["monthly_aggregation"] = monthly_agg.to_dict()

            # 环比增长率计算
            monthly_growth = monthly_agg.pct_change() * 100
            analysis_summary["trend_analysis"]["monthly_mom_growth"] = monthly_growth.round(2).to_dict()

            # 趋势可视化并保存
            plt.figure(figsize=(12, 6))
            for col in numeric_cols:
                plt.plot(monthly_agg.index, monthly_agg[col], label=col, linewidth=2)
            plt.title("数值列月度趋势图")
            plt.xlabel("时间")
            plt.ylabel("数值")
            plt.legend(loc="best")
            plt.grid(alpha=0.3, linestyle="--")
            plt.savefig("standard_trend_analysis.png", dpi=150, bbox_inches="tight")
            plt.close()
            analysis_summary["trend_analysis"]["trend_chart_path"] = "standard_trend_analysis.png"

        # ===================== 步骤4：异常检测（IQR法识别离群值） =====================
        if not numeric_cols.empty:
            anomaly_result = {}
            anomaly_df_list = []
            for col in numeric_cols:
                col_data = df_clean[col].dropna()
                if not col_data.empty:
                    Q1 = col_data.quantile(0.25)
                    Q3 = col_data.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    # 提取异常值
                    col_anomalies = df_clean[(df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)]
                    anomaly_result[col] = {
                        "lower_bound": lower_bound,
                        "upper_bound": upper_bound,
                        "anomaly_count": len(col_anomalies),
                        "anomaly_data": col_anomalies[[col]].to_dict()
                    }
                    anomaly_df_list.append(col_anomalies)

            # 合并所有异常数据
            if anomaly_df_list:
                final_anomaly_df = pd.concat(anomaly_df_list).drop_duplicates()
                analysis_summary["anomaly_detection"]["anomaly_df"] = final_anomaly_df.to_dict()
            analysis_summary["anomaly_detection"]["numeric_cols_anomaly"] = anomaly_result

        return analysis_summary

    except Exception as e:
        # 异常处理，返回错误信息
        analysis_summary["analysis_status"] = "failed"
        analysis_summary["error"] = str(e)
        return analysis_summary

# 调用标准分析函数，传入输入的df对象（沙箱执行时直接运行即可获取汇总结果）
standard_analysis_output = standard_data_analysis(df)
'''
        else:
            # 灵活需求代码模板（适配任意用户需求，仅保留核心结构，由大模型填充具体逻辑）
            code_template = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from typing import Dict, Optional

# 配置matplotlib中文显示（解决中文乱码）
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

def custom_data_analysis(df: pd.DataFrame) -> object:
    """
    自定义自动化数据分析（根据用户需求实现核心功能）
    :param df: 输入的Pandas DataFrame
    :return: 符合用户需求的分析结果
    """
    try:
        # 初始化分析结果
        custom_analysis_result = {}

        # ===================== 核心分析逻辑（根据用户需求定制） =====================
        # 1. 数据预处理（按需调整：缺失值填充、数据类型转换、筛选等）
        df_custom = df.copy()  # 生成副本，不修改原始数据

        # 2. 核心分析功能（根据用户需求灵活实现：聚合、排序、可视化、建模等）
        # 示例：可支持用户需求如"按产品分类统计销售额Top10"、"计算年度同比增长率"、"绘制成本分布直方图"等
        # （实际场景由大模型根据用户具体需求填充精准逻辑）

        # 3. 结果整理与可视化（按需保存图表，返回具体结果）

        # ===================== 返回最终分析结果 =====================
        return custom_analysis_result

    except Exception as e:
        # 异常处理，返回错误信息
        return {"error": str(e), "analysis_status": "failed"}

# 调用自定义分析函数，传入输入的df对象（沙箱执行时直接运行即可获取结果）
custom_analysis_output = custom_data_analysis(df)
'''
        return code_template

    def _clean_analysis_code(self, code: str) -> str:
        """清理生成的分析代码（补全依赖、格式化、确保可直接运行）"""
        if not code:
            return ""

        # 1. 清理空行和多余空白
        cleaned_lines = [line.strip() for line in code.splitlines() if line.strip()]

        # 2. 确保包含必要的库导入（兜底补全）
        required_imports = [
            "import pandas as pd",
            "import numpy as np"
        ]
        existing_imports = [line for line in cleaned_lines if line.startswith("import")]
        for req_import in required_imports:
            if req_import not in existing_imports:
                cleaned_lines.insert(0, req_import)

        # 3. 确保最终调用分析函数并生成结果变量
        if not any(
                line.endswith("= standard_data_analysis(df)") or line.endswith("= custom_data_analysis(df)") for line in
                cleaned_lines):
            cleaned_lines.append("\n# 执行数据分析，传入输入的df对象")
            cleaned_lines.append("analysis_output = custom_data_analysis(df)" if not self._is_blank_or_general_query(
                "") else "analysis_output = standard_data_analysis(df)")

        # 4. 拼接为完整可运行代码
        return "\n".join(cleaned_lines)


class AutoDataAnalysisMCP:
    """自动化数据分析核心组件（输入df+自然语言，输出Python代码，无执行逻辑）"""

    def __init__(self, llm_api_config: Dict):
        """
        初始化自动化数据分析组件
        :param llm_api_config: 大模型API配置（参数化传入，兼容DeepSeek等平台）
        """
        self.llm_api_config = llm_api_config
        self.llm_client = LLMautoAnalysisClient(llm_api_config)
        self.df_structure_extractor: Optional[DfStructureExtractor] = None
        self.generated_analysis_code: Optional[str] = None

    def generate_analysis_code(self, df: pd.DataFrame, user_nl_query: str = "") -> Optional[str]:
        """
        核心流程：输入df+自然语言 → 提取df结构 → 生成Python分析代码（灵活/标准二选一）
        :param df: 输入的Pandas DataFrame（宽表）
        :param user_nl_query: 用户自然语言分析要求（可选，为空/模糊时回退到标准流程）
        :return: 生成的Python自动化分析代码
        """
        try:
            # 步骤1：提取DataFrame结构
            self.df_structure_extractor = DfStructureExtractor(df)
            df_structure_prompt = self.df_structure_extractor.generate_structure_prompt()

            # 步骤2：调用大模型生成分析代码（自动判断是否回退标准流程）
            success, code_or_error = self.llm_client.generate_analysis_code(
                user_nl_query,
                df_structure_prompt
            )
            if not success:
                print(f"❌ 分析代码生成失败：{code_or_error}")
                return None

            # 步骤3：保存并返回代码
            self.generated_analysis_code = code_or_error
            return self.generated_analysis_code
        except Exception as e:
            print(f"❌ 流程执行失败：{str(e)}")
            return None


# -------------------------- 测试示例（main函数） --------------------------
if __name__ == "__main__":
    # 1. 用户提供的DeepSeek大模型配置（复用现有配置）
    DEEPSEEK_CONFIG = {
        "api_key": "sk-fe09e253e6f14adba6cf56eb1e1c106c",
        "base_url": "https://api.deepseek.com",
        "model_name": "deepseek-chat",
        "endpoint": "/v1/chat/completions",
        "max_tokens": 3000,
        "temperature": 0.1
    }

    # 2. 生成模拟宽表df（贴合销售/成本场景，用于测试）
    dates = pd.date_range(start="2024-01-01", periods=120, freq="D")
    sales_data = np.random.randint(1000, 5000, size=120) + np.linspace(0, 1500, 120)  # 带增长趋势的销售额
    cost_data = sales_data * np.random.uniform(0.6, 0.8, size=120)  # 成本数据
    category_data = np.random.choice(["A类产品", "B类产品", "C类产品"], size=120)  # 产品分类
    region_data = np.random.choice(["华北", "华东", "华南"], size=120)  # 区域分类

    # 插入异常值（用于标准流程的异常检测测试）
    sales_data[15] = 18000
    sales_data[30] = -800
    cost_data[45] = 12000

    df = pd.DataFrame({
        "date": dates,
        "sales_amount": sales_data,
        "cost_amount": cost_data,
        "product_category": category_data,
        "sales_region": region_data
    })
    df["date"] = pd.to_datetime(df["date"])  # 转换为时间列
    print(f"✅ 模拟宽表df生成完成，形状：{df.shape}")
    print(f"✅ df列类型信息：\n{df.dtypes}")

    # 3. 初始化自动化数据分析组件
    auto_analysis_mcp = AutoDataAnalysisMCP(llm_api_config=DEEPSEEK_CONFIG)

    # 4. 测试场景1：无具体需求（模糊查询，回退到标准流程）
    print("\n" + "=" * 80)
    print("测试场景1：无具体需求（模糊查询，回退到标准流程）")
    print("=" * 80)
    try:
        user_nl_blank = "分析数据"
        generated_code_standard = auto_analysis_mcp.generate_analysis_code(df, user_nl_blank)
        if generated_code_standard:
            print("\n=== 生成的标准流程分析代码（部分展示）===")
            print("-" * 100)
            # 展示前50行代码（避免输出过长）
            print("\n".join(generated_code_standard.splitlines()[:50]))
            print("...（后续代码省略，完整代码可直接传入沙箱执行）")
            print("-" * 100)
    except Exception as e:
        print(f"❌ 测试场景1失败：{str(e)}")

    # 5. 测试场景2：有具体需求（灵活生成对应代码）
    print("\n" + "=" * 80)
    print("测试场景2：有具体需求（灵活生成对应分析代码）")
    print("=" * 80)
    try:
        user_nl_specific = """
        1.  按产品分类和销售区域，分组统计销售额和成本的总和、均值
        2.  筛选出2024年2月的销售数据，计算每个区域的销售额环比增长率（对比1月）
        3.  绘制各产品分类的销售额占比饼图，保存为product_sales_pie.png
        """
        print(f"=== 输入具体自然语言需求 ===")
        print(user_nl_specific.strip())

        generated_code_custom = auto_analysis_mcp.generate_analysis_code(df, user_nl_specific)
        if generated_code_custom:
            print("\n=== 生成的自定义需求分析代码 ===")
            print("-" * 100)
            print(generated_code_custom)
            print("-" * 100)
            print(
                "\n提示：1. 代码可直接传入Python沙箱执行；2. 标准流程兜底保证无需求时的完整分析；3. 自定义需求支持任意数据分析功能，无类型限制")
    except Exception as e:
        print(f"❌ 测试场景2失败：{str(e)}")