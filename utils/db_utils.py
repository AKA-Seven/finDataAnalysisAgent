"""
数据库工具：提供数据库连接池、通用查询/执行方法，兼容多种数据库类型
"""
import sqlite3
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import get_global_config
from .file_utils import ensure_dir
from .exception_utils import ConfigException, DataProcessException

class DBConnectionPool:
    """数据库连接池（支持SQLite/MySQL/PostgreSQL）"""
    def __init__(self):
        self.config = get_global_config()["database"]
        self.engine = None
        self.Session = None
        self._init_connection()

    def _init_connection(self) -> None:
        """初始化数据库连接"""
        db_type = self.config["type"].lower()
        try:
            if db_type == "sqlite":
                # 确保SQLite文件目录存在
                db_file_path = self.config["file_path"]
                ensure_dir(os.path.dirname(db_file_path))
                conn_str = f"sqlite:///{db_file_path}"
            elif db_type == "mysql":
                conn_str = f"mysql+pymysql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['db_name']}"
            elif db_type == "postgresql":
                conn_str = f"postgresql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['db_name']}"
            else:
                raise ConfigException(f"不支持的数据库类型：{db_type}")

            # 创建引擎
            self.engine = create_engine(
                conn_str,
                pool_size=self.config["pool_size"],
                pool_recycle=self.config["timeout"],
                echo=False
            )

            # 创建会话工厂
            self.Session = sessionmaker(bind=self.engine)
        except Exception as e:
            raise ConfigException(f"数据库连接初始化失败：{str(e)}")

    def get_session(self):
        """获取数据库会话"""
        if not self.Session:
            self._init_connection()
        return self.Session()

    def close(self) -> None:
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()

# 全局数据库连接池实例
_DB_POOL = DBConnectionPool()

def db_query(sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    通用数据库查询方法
    :param sql: 查询SQL语句
    :param params: 查询参数（字典格式）
    :return: 查询结果（列表字典）
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise DataProcessException("仅支持SELECT查询语句")

    session = _DB_POOL.get_session()
    try:
        result = session.execute(sql, params or {})
        # 转换为列表字典格式
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
    except Exception as e:
        raise DataProcessException(f"数据库查询失败：{str(e)}")
    finally:
        session.close()

def db_execute(sql: str, params: Optional[Dict[str, Any]] = None) -> int:
    """
    通用数据库执行方法（INSERT/UPDATE/DELETE）
    :param sql: 执行SQL语句
    :param params: 执行参数（字典格式）
    :return: 受影响的行数
    """
    sql_upper = sql.strip().upper()
    if not any(sql_upper.startswith(prefix) for prefix in ["INSERT", "UPDATE", "DELETE"]):
        raise DataProcessException("仅支持INSERT/UPDATE/DELETE执行语句")

    session = _DB_POOL.get_session()
    try:
        result = session.execute(sql, params or {})
        session.commit()
        return result.rowcount
    except Exception as e:
        session.rollback()
        raise DataProcessException(f"数据库执行失败：{str(e)}")
    finally:
        session.close()