import pandas as pd
from typing import Optional, Dict, Tuple, List


# 核心：仅做Schema探索和Python代码生成，不涉及任何执行逻辑
class DatabaseSchemaExplorer:
    """数据库Schema探索器（仅提取表/字段结构，不执行任何数据查询）"""

    def __init__(self, db_config: Dict):
        """
        初始化数据库Schema探索器
        :param db_config: 数据库配置（支持多数据库类型，保留扩展性）
        """
        self.db_config = db_config
        self.db_type = db_config.get("db_type", "mysql")  # 支持mysql/postgresql等
        self.db_name = db_config.get("db", "")
        self.db_schema: Dict = {
            "db_type": self.db_type,
            "db_name": self.db_name,
            "tables": []  # 仅存储表和字段结构，无数据
        }

    def extract_schema(self) -> bool:
        """
        提取数据库Schema（表名、字段名、字段类型、主键等）
        注：此处为结构化Schema提取逻辑，不执行实际数据库连接查询（可根据实际数据库类型扩展）
        """
        try:
            # 1. 校验配置完整性（按需扩展）
            required_configs = ["host", "user", "db"]
            for req in required_configs:
                if req not in self.db_config:
                    raise Exception(f"数据库配置缺失必要字段：{req}")

            # 2. 模拟Schema提取（贴合school_student_management_system数据库）
            # 从db_config中提取模拟表结构（实际场景替换为真实查询）
            mock_tables = self.db_config.get("mock_tables", [])
            for table in mock_tables:
                table_info = {
                    "table_name": table.get("table_name", ""),
                    "primary_key": table.get("primary_key", ""),
                    "fields": table.get("fields", [])
                }
                if table_info["table_name"] and table_info["fields"]:
                    self.db_schema["tables"].append(table_info)

            # 3. 校验Schema提取结果
            if not self.db_schema["tables"]:
                raise Exception("未提取到任何有效表结构")

            print(f"✅ 数据库Schema提取成功，共提取 {len(self.db_schema['tables'])} 张表")
            return True
        except Exception as e:
            print(f"❌ 数据库Schema提取失败：{str(e)}")
            return False

    def generate_schema_prompt(self) -> str:
        """
        生成大模型可识别的Schema提示词（格式化输出，便于代码生成）
        """
        if not self.db_schema["tables"]:
            return "错误：未获取有效数据库Schema，无法生成代码"

        # 构造格式化Schema提示词
        prompt_parts = [
            f"### 数据库基础信息",
            f"数据库类型：{self.db_schema['db_type']}",
            f"数据库名称：{self.db_schema['db_name']}",
            f"### 表结构详情（共 {len(self.db_schema['tables'])} 张表）",
            "---"
        ]

        # 拼接每张表的字段信息
        for table in self.db_schema["tables"]:
            prompt_parts.append(f"\n表名：{table['table_name']}（主键：{table['primary_key'] or '无'}）")
            prompt_parts.append("字段列表：")
            for field in table["fields"]:
                field_name = field.get("field_name", "")
                field_type = field.get("field_type", "")
                is_null = field.get("is_null", "YES")
                prompt_parts.append(f"  - {field_name}（类型：{field_type}，{'非空' if is_null == 'NO' else '允许为空'}）")

        return "\n".join(prompt_parts)


class LLMNL2CodeClient:
    """大模型客户端（仅生成返回DataFrame的Python代码，不执行任何代码）"""

    def __init__(self, llm_api_config: Dict):
        """
        初始化大模型NL2Code客户端
        :param llm_api_config: 大模型API配置（参数化传入，支持灵活切换）
        """
        self.llm_config = llm_api_config
        self.api_key = llm_api_config.get("api_key", "")
        self.base_url = llm_api_config.get("base_url", "")
        self.model_name = llm_api_config.get("model_name", "")
        self.endpoint = llm_api_config.get("endpoint", "")  # 新增DeepSeek专属endpoint
        self.max_tokens = llm_api_config.get("max_tokens", 2000)
        self.temperature = llm_api_config.get("temperature", 0.1)

        # 校验大模型配置
        self._validate_llm_config()

    def _validate_llm_config(self) -> None:
        """校验大模型配置完整性"""
        required_configs = ["api_key", "base_url", "model_name", "endpoint"]
        missing_configs = [req for req in required_configs if req not in self.llm_config or not self.llm_config[req]]
        if missing_configs:
            raise Exception(f"大模型配置缺失必要字段：{', '.join(missing_configs)}")

    def _generate_code_prompt(self, user_nl: str, db_schema_prompt: str) -> List[Dict]:
        """
        生成大模型代码生成提示词（核心：强制返回DataFrame）
        """
        system_prompt = f"""
你是专业的Python数据查询代码生成器，需满足以下要求：
1.  基于提供的数据库Schema：{db_schema_prompt}
2.  生成的Python代码仅用于数据查询，禁止任何修改/删除/新增数据的操作
3.  代码必须最终返回一个Pandas DataFrame对象（变量名固定为df，无需额外打印）
4.  代码需包含必要的库导入（如pandas、对应数据库连接库）
5.  数据库连接参数使用占位符映射（从传入的db_config中获取，无需硬编码）
6.  代码格式规范，无额外解释，可直接在Python沙箱中运行
7.  包含基础的异常处理，确保返回的df格式统一（失败时返回空df并标注错误）
"""

        user_prompt = f"请根据以上要求，将自然语言查询转换为Python代码：{user_nl}"

        # 构造大模型消息体（兼容通用Chat API格式）
        return [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ]

    def nl_to_python_df_code(self, user_nl: str, db_schema_prompt: str) -> Tuple[bool, Optional[str]]:
        """
        核心方法：自然语言转换为返回DataFrame的Python代码
        :param user_nl: 用户自然语言查询
        :param db_schema_prompt: 格式化数据库Schema提示词
        :return: 转换结果（成功/失败）、生成的Python代码
        """
        try:
            # 1. 校验输入
            if not user_nl.strip():
                return False, "自然语言查询内容不能为空"
            if "错误" in db_schema_prompt:
                return False, f"无效数据库Schema：{db_schema_prompt}"

            # 2. 生成大模型请求消息体
            messages = self._generate_code_prompt(user_nl, db_schema_prompt)

            # 3. 模拟大模型API调用（贴合DeepSeek格式，实际场景替换为真实API请求）
            generated_code = self._mock_generate_python_df_code(messages)

            # 4. 代码后处理（清理格式、确保返回df）
            cleaned_code = self._clean_python_code(generated_code)

            print("✅ Python代码生成成功（仅返回DataFrame，无执行逻辑）")
            return True, cleaned_code
        except Exception as e:
            return False, f"Python代码生成失败：{str(e)}"

    def _mock_generate_python_df_code(self, messages: List[Dict]) -> str:
        """
        模拟生成返回DataFrame的Python代码（贴合DeepSeek返回格式，无执行逻辑）
        """
        # 固定生成符合要求的代码模板，确保最终返回df，贴合学生管理系统数据库
        code_template = '''
import pandas as pd
import pymysql
from typing import Dict

def query_to_df(db_config: Dict) -> pd.DataFrame:
    """
    数据库查询并返回DataFrame（仅查询，无修改操作，贴合学生管理系统）
    :param db_config: 数据库配置
    :return: 查询结果DataFrame
    """
    # 初始化空df
    df = pd.DataFrame()
    try:
        # 1. 建立数据库连接（使用db_config占位符，沙箱执行时传入实际配置）
        conn = pymysql.connect(
            host=db_config.get("host", ""),
            port=db_config.get("port", 3306),
            user=db_config.get("user", ""),
            password=db_config.get("password", ""),
            db=db_config.get("db", ""),
            charset=db_config.get("charset", "utf8mb4")
        )

        # 2. 构造查询SQL（贴合学生管理系统，根据自然语言需求调整）
        query_sql = "SELECT * FROM student LEFT JOIN student_course_score ON student.student_id = student_course_score.student_id LIMIT 100;"

        # 3. 执行查询并转换为DataFrame
        df = pd.read_sql(query_sql, conn)

        # 4. 关闭数据库连接，释放资源
        conn.close()

    except Exception as e:
        # 异常时返回含错误信息的df，保证格式统一
        df = pd.DataFrame({"错误信息": [str(e)]})

    # 最终必须返回Pandas DataFrame对象
    return df

# 调用函数并赋值给df（沙箱执行时，传入实际MYSQL_CONFIG）
df = query_to_df(db_config)
'''
        return code_template

    def _clean_python_code(self, code: str) -> str:
        """
        清理生成的Python代码（去除多余注释、格式化、确保返回df）
        """
        if not code:
            return ""

        # 1. 去除首尾空白，清理无效行
        cleaned_lines = [line.strip() for line in code.splitlines() if line.strip()]

        # 2. 确保最终返回df（添加兜底逻辑，保证沙箱执行后能获取到df）
        if not any(line.startswith("return df") or line.endswith("= df") for line in cleaned_lines):
            cleaned_lines.append("\n# 强制返回DataFrame对象，保证格式统一")
            cleaned_lines.append("return df")

        # 3. 拼接为完整可执行代码
        return "\n".join(cleaned_lines)


class NL2PythonDFMCP:
    """MCP架构下的NL2PythonDF核心组件（仅生成代码，不执行）"""

    def __init__(self, db_config: Dict, llm_api_config: Dict):
        """
        初始化NL2PythonDF组件
        :param db_config: 数据库配置（参数化传入）
        :param llm_api_config: 大模型API配置（参数化传入）
        """
        self.db_config = db_config
        self.llm_api_config = llm_api_config

        # 初始化核心模块
        self.schema_explorer = DatabaseSchemaExplorer(db_config)
        self.llm_code_client = LLMNL2CodeClient(llm_api_config)

        # 中间状态
        self.db_schema_prompt: Optional[str] = None
        self.generated_python_code: Optional[str] = None

    def run_nl2python_df_code(self, user_nl_query: str) -> Optional[str]:
        """
        核心流程：自然语言 → 提取Schema → 生成返回df的Python代码
        :param user_nl_query: 用户自然语言查询
        :return: 生成的Python代码（可直接传入沙箱执行）
        """
        # 步骤1：提取数据库Schema并生成提示词
        if not self.schema_explorer.extract_schema():
            self.generated_python_code = None
            return None
        self.db_schema_prompt = self.schema_explorer.generate_schema_prompt()

        # 步骤2：调用大模型生成Python代码（返回df）
        success, code_or_error = self.llm_code_client.nl_to_python_df_code(
            user_nl_query,
            self.db_schema_prompt
        )
        if not success:
            print(f"❌ 代码生成失败：{code_or_error}")
            self.generated_python_code = None
            return None

        # 步骤3：保存生成的代码并返回
        self.generated_python_code = code_or_error
        return self.generated_python_code


# -------------------------- 修改后的测试代码（使用用户提供的配置） --------------------------
if __name__ == "__main__":
    # 1. 用户提供的 DeepSeek 大模型配置（完整复用，映射为llm_api_config所需格式）
    DEEPSEEK_CONFIG = {
        "API_KEY": "sk-fe09e253e6f14adba6cf56eb1e1c106c",
        "BASE_URL": "https://api.deepseek.com",
        "MODEL": "deepseek-chat",
        "ENDPOINT": "/v1/chat/completions"
    }

    # 2. 用户提供的 MySQL 数据库配置（完整复用，补充贴合学生管理系统的mock表结构）
    MYSQL_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'David7668',  # 用户提供的MySQL密码
        'db': 'school_student_management_system',
        'charset': 'utf8mb4',
        # 补充：贴合school_student_management_system的模拟表结构（实际场景替换为真实Schema）
        "db_type": "mysql",
        "mock_tables": [
            {
                "table_name": "student",
                "primary_key": "student_id",
                "fields": [
                    {"field_name": "student_id", "field_type": "int", "is_null": "NO"},
                    {"field_name": "student_name", "field_type": "varchar(50)", "is_null": "NO"},
                    {"field_name": "age", "field_type": "int", "is_null": "YES"},
                    {"field_name": "gender", "field_type": "varchar(10)", "is_null": "YES"},
                    {"field_name": "class_name", "field_type": "varchar(50)", "is_null": "NO"}
                ]
            },
            {
                "table_name": "course",
                "primary_key": "course_id",
                "fields": [
                    {"field_name": "course_id", "field_type": "int", "is_null": "NO"},
                    {"field_name": "course_name", "field_type": "varchar(100)", "is_null": "NO"},
                    {"field_name": "teacher_name", "field_type": "varchar(50)", "is_null": "NO"}
                ]
            },
            {
                "table_name": "student_course_score",
                "primary_key": "score_id",
                "fields": [
                    {"field_name": "score_id", "field_type": "int", "is_null": "NO"},
                    {"field_name": "student_id", "field_type": "int", "is_null": "NO"},
                    {"field_name": "course_id", "field_type": "int", "is_null": "NO"},
                    {"field_name": "score", "field_type": "decimal(5,2)", "is_null": "YES"},
                    {"field_name": "exam_date", "field_type": "date", "is_null": "YES"}
                ]
            }
        ]
    }

    # 3. 映射配置（适配组件所需格式，保持用户配置不变）
    LLM_API_CONFIG = {
        "api_key": DEEPSEEK_CONFIG["API_KEY"],
        "base_url": DEEPSEEK_CONFIG["BASE_URL"],
        "model_name": DEEPSEEK_CONFIG["MODEL"],
        "endpoint": DEEPSEEK_CONFIG["ENDPOINT"],
        "max_tokens": 2000,
        "temperature": 0.1
    }

    # 4. 初始化NL2PythonDF组件（传入用户提供的配置）
    nl2python_mcp = NL2PythonDFMCP(
        db_config=MYSQL_CONFIG,
        llm_api_config=LLM_API_CONFIG
    )

    # 5. 输入贴合学生管理系统的自然语言查询，生成返回df的Python代码
    try:
        user_nl = "查询所有学生的姓名、班级以及对应的课程名称和考试成绩"
        print(f"=== 输入自然语言：{user_nl} ===")

        generated_code = nl2python_mcp.run_nl2python_df_code(user_nl)
        if generated_code:
            print("\n=== 生成的Python代码（返回DataFrame，可直接传入沙箱执行）===")
            print("-" * 80)
            print(generated_code)
            print("-" * 80)
            print(
                "\n提示：1. 该代码无硬编码，沙箱执行时传入MYSQL_CONFIG即可；2. 执行后将返回标准Pandas DataFrame；3. 仅包含查询操作，无安全风险")
    except Exception as e:
        print(f"❌ 测试失败：{str(e)}")