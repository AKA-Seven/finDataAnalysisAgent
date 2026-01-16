"""
文件工具：提供路径处理、文件读写、目录创建、格式验证等通用能力
"""
import os
import shutil
from typing import List, Optional

def get_abs_path(relative_path: str) -> str:
    """
    相对路径转绝对路径（兼容不同运行环境）
    :param relative_path: 相对路径
    :return: 绝对路径
    """
    return os.path.abspath(relative_path)

def ensure_dir(dir_path: str) -> None:
    """
    确保目录存在，不存在则创建
    :param dir_path: 目录路径
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    读取文本文件内容
    :param file_path: 文件路径
    :param encoding: 文件编码
    :return: 文件内容
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")

    with open(file_path, "r", encoding=encoding) as f:
        return f.read()

def write_file(file_path: str, content: str, encoding: str = "utf-8", overwrite: bool = True) -> None:
    """
    写入文本文件内容
    :param file_path: 文件路径
    :param content: 写入内容
    :param encoding: 文件编码
    :param overwrite: 是否覆盖已有文件（False则追加）
    """
    # 确保目录存在
    ensure_dir(os.path.dirname(file_path))

    mode = "w" if overwrite else "a"
    with open(file_path, mode, encoding=encoding) as f:
        f.write(content)

def delete_file(file_path: str) -> bool:
    """
    删除文件（兼容不存在的文件，不抛出异常）
    :param file_path: 文件路径
    :return: 是否删除成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False

def list_dir_files(dir_path: str, suffix: Optional[str] = None) -> List[str]:
    """
    列出目录下所有文件（可选过滤后缀）
    :param dir_path: 目录路径
    :param suffix: 文件后缀（如".xlsx"）
    :return: 文件路径列表
    """
    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"不是有效目录：{dir_path}")

    file_list = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if suffix and not file.endswith(suffix):
                continue
            file_list.append(os.path.join(root, file))

    return file_list

def validate_file_format(file_path: str, supported_formats: List[str]) -> bool:
    """
    验证文件格式是否支持
    :param file_path: 文件路径
    :param supported_formats: 支持的格式列表（如["xlsx", "csv"]）
    :return: 是否支持
    """
    file_suffix = os.path.splitext(file_path)[1].lstrip(".").lower()
    return file_suffix in [fmt.lower() for fmt in supported_formats]

def copy_file(src_path: str, dst_path: str) -> None:
    """
    复制文件
    :param src_path: 源文件路径
    :param dst_path: 目标文件路径
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"源文件不存在：{src_path}")

    ensure_dir(os.path.dirname(dst_path))
    shutil.copy2(src_path, dst_path)