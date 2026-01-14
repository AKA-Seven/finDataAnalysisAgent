import os
import time
import gc
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from typing import Optional, List, Dict, Any
import win32com.client as win32
from os.path import abspath, exists


class ExcelOperator:
    """Excel文档操作核心类（增强版）：解决权限拒绝，支持df读写、有/无宏区分、已有文件加宏/加函数"""

    def __init__(self):
        self.workbook = None  # openpyxl的工作簿对象（用于.xlsx/.xlsm数据读写，无宏操作）
        self.current_sheet = None
        self.file_path = None

    # ========== 读取Excel返回DataFrame ==========
    def read_excel_to_df(self, file_path: Optional[str] = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        读取Excel文件，返回pandas DataFrame
        :param file_path: Excel文件路径（若为None，使用当前已打开的文件路径）
        :param sheet_name: 工作表名称（若为None，读取当前激活工作表/第一个工作表）
        :return: pd.DataFrame
        """
        target_path = file_path or self.file_path
        if not target_path or not exists(target_path):
            raise FileNotFoundError("Excel文件不存在，请指定有效文件路径")

        try:
            # 支持.xlsx和.xlsm格式，使用openpyxl引擎
            sheet_to_read = sheet_name or self.current_sheet.title if self.current_sheet else None
            df = pd.read_excel(
                target_path,
                sheet_name=sheet_to_read,
                engine="openpyxl"
            )
            return df
        except Exception as e:
            raise Exception(f"读取Excel转为DataFrame失败：{str(e)}")

    # ========== 新建无宏Excel（.xlsx） ==========
    def new_excel(self, sheet_name: str = "Sheet1") -> bool:
        """新建无宏Excel文档（.xlsx格式，无法存储宏）"""
        try:
            self.workbook = Workbook()
            default_sheet = self.workbook.active
            self.workbook.remove(default_sheet)
            self.current_sheet = self.workbook.create_sheet(title=sheet_name)
            return True
        except Exception as e:
            raise Exception(f"新建无宏Excel失败：{str(e)}")

    # ========== 修复：新建带宏支持的空白Excel（.xlsm） ==========
    def new_excel_with_macro_support(self, save_path: str, sheet_name: str = "Sheet1") -> bool:
        """
        新建带宏支持的空白Excel文档（.xlsm格式，强制释放文件句柄，避免权限拒绝）
        :param save_path: 保存路径（必须以.xlsm结尾）
        :param sheet_name: 工作表名称
        :return: 操作结果
        """
        # 格式校验
        if not save_path.endswith(".xlsm"):
            raise Exception("带宏支持的Excel文件必须以.xlsm结尾，请修改保存路径")
        if os.name != "nt":
            raise Exception("仅支持Windows系统，无法创建带宏Excel文件")

        # 相对路径转绝对路径，避免Excel COM解析错误
        abs_save_path = abspath(save_path)
        excel_app = None
        workbook = None

        try:
            # 启动Excel COM组件，创建空白.xlsm
            excel_app = win32.Dispatch("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False

            workbook = excel_app.Workbooks.Add()
            worksheet = workbook.Worksheets(1)
            worksheet.Name = sheet_name

            # 使用绝对路径保存，确保写入项目根目录
            workbook.SaveAs(Filename=abs_save_path, FileFormat=52)  # 52=.xlsm格式

            # 强制刷新缓存，关闭工作簿
            workbook.RefreshAll()
            workbook.Close(SaveChanges=False)

            # 关键修复1：强制退出Excel，释放所有资源
            excel_app.Quit()

            # 关键修复2：手动释放COM对象，避免句柄残留
            del workbook
            del excel_app
            gc.collect()  # 手动触发垃圾回收，释放锁定的文件句柄

            # 关键修复3：延长延时，确保文件句柄完全解锁（从0.5秒改为1秒）
            time.sleep(1)

            # 校验文件是否创建成功且可写入
            if not exists(abs_save_path):
                raise Exception(f"文件保存失败，未找到：{abs_save_path}")
            if not os.access(abs_save_path, os.W_OK):
                raise Exception(f"文件无写入权限：{abs_save_path}")

            # 用openpyxl打开.xlsm，强制可写模式，保留VBA宏
            self.open_excel(abs_save_path, sheet_name)
            self.file_path = abs_save_path
            print(f"✅ 带宏支持的空白Excel已创建，保存至：{abs_save_path}")
            return True
        except Exception as e:
            # 异常时，强制释放所有COM资源
            if workbook:
                try:
                    workbook.Close(SaveChanges=False)
                except:
                    pass
            if excel_app:
                try:
                    excel_app.Quit()
                except:
                    pass
            del workbook
            del excel_app
            gc.collect()
            raise Exception(f"新建带宏支持Excel失败：{str(e)}")

    # ========== 修复：打开已存在的Excel（.xlsx/.xlsm） ==========
    def open_excel(self, file_path: str, sheet_name: Optional[str] = None) -> bool:
        """打开已存在的Excel文档（支持.xlsx/.xlsm，强制可写模式，保留VBA宏）"""
        if not exists(file_path):
            raise FileNotFoundError(f"Excel文件不存在：{file_path}")
        try:
            # 关键优化：read_only=False 强制可写，keep_vba=True 保留.xlsm的宏
            self.workbook = load_workbook(
                file_path,
                data_only=True,
                read_only=False,
                keep_vba=True
            )
            self.file_path = file_path
            if sheet_name and sheet_name in self.workbook.sheetnames:
                self.current_sheet = self.workbook[sheet_name]
            else:
                self.current_sheet = self.workbook.active
            print(f"✅ 成功打开Excel：{file_path}，工作表：{self.current_sheet.title}")
            return True
        except Exception as e:
            raise Exception(f"打开Excel失败：{str(e)}")

    # ========== 写入单元格数据 ==========
    def write_cell(self, row: int, col: int, value: Any, save_immediately: bool = False) -> bool:
        """写入指定单元格数据（行、列从1开始）"""
        if not self.current_sheet:
            raise Exception("请先新建或打开Excel文档")
        try:
            self.current_sheet.cell(row=row, column=col, value=value)
            if save_immediately and self.file_path:
                self.save_excel()
            elif save_immediately and not self.file_path:
                raise Exception("未指定保存路径，无法立即保存")
            return True
        except Exception as e:
            raise Exception(f"写入单元格失败：{str(e)}")

    # ========== 修复：保存Excel文档（避免文件占用冲突） ==========
    def save_excel(self, file_path: Optional[str] = None) -> bool:
        """
        保存Excel文档（优化：避免文件占用，支持.xlsm数据写入不丢失宏）
        :param file_path: 保存路径（若为None，使用当前已打开的文件路径）
        :return: 操作结果
        """
        if not self.workbook:
            raise Exception("请先新建或打开Excel文档")
        try:
            target_path = file_path or self.file_path
            if not target_path:
                raise Exception("请指定Excel保存路径")

            # 关键优化1：校验文件是否可写入
            if exists(target_path) and not os.access(target_path, os.W_OK):
                raise Exception(f"文件被占用或无写入权限，无法保存：{target_path}")

            # 关键优化2：.xlsm文件特殊处理，避免宏丢失且解决占用
            if target_path.endswith(".xlsm"):
                # 重新以可写模式打开，保留宏并更新数据
                temp_workbook = load_workbook(
                    target_path,
                    data_only=True,
                    read_only=False,
                    keep_vba=True
                )
                temp_sheet = temp_workbook[self.current_sheet.title]

                # 复制当前工作表最新数据到临时工作簿
                for row in self.current_sheet.iter_rows(min_row=1, max_row=self.current_sheet.max_row,
                                                        min_col=1, max_col=self.current_sheet.max_column,
                                                        values_only=False):
                    for cell in row:
                        temp_sheet[cell.coordinate] = cell.value

                # 保存并关闭临时工作簿，释放句柄
                temp_workbook.save(target_path)
                temp_workbook.close()
            else:
                # .xlsx文件直接保存
                self.workbook.save(target_path)

            self.file_path = target_path
            print(f"✅ Excel文件已成功保存：{target_path}")
            return True
        except Exception as e:
            raise Exception(f"保存Excel失败：{str(e)}")

    # ========== 仅对已有Excel添加VBA宏过程（Sub） ==========
    def add_vba_macro_to_existing(self, existing_xlsm_path: str, vba_sub_code: str,
                                  module_name: str = "MacroModule") -> bool:
        """
        对已存在的.xlsm文件添加VBA宏过程（Sub，可运行的宏）
        :param existing_xlsm_path: 已有.xlsm文件路径
        :param vba_sub_code: VBA宏过程代码（Sub...End Sub）
        :param module_name: VBA模块名称（避免重复）
        :return: 操作结果
        """
        # 前置校验
        if not existing_xlsm_path.endswith(".xlsm"):
            raise Exception("仅支持对.xlsm格式文件添加宏，请修改文件路径")
        if not exists(existing_xlsm_path):
            raise FileNotFoundError(f"已存在的.xlsm文件不存在：{existing_xlsm_path}")
        if os.name != "nt":
            raise Exception("仅支持Windows系统，无法调用Excel COM组件写入宏")

        excel_app = None
        workbook = None
        try:
            # 启动Excel COM组件，打开已有.xlsm
            excel_app = win32.Dispatch("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False

            workbook = excel_app.Workbooks.Open(Filename=abspath(existing_xlsm_path))

            # 访问VBA项目，添加/获取标准模块（1 = vbext_ct_StdModule）
            vba_project = workbook.VBProject
            try:
                # 若模块已存在，直接获取
                vba_module = vba_project.VBComponents(module_name)
            except:
                # 模块不存在，新建标准模块
                vba_module = vba_project.VBComponents.Add(1)
                vba_module.Name = module_name

            # 写入VBA宏过程代码（追加到模块末尾）
            vba_module.CodeModule.AddFromString(vba_sub_code)

            # 保存修改并关闭
            workbook.Save()
            workbook.Close(SaveChanges=False)
            excel_app.Quit()

            # 释放COM资源，避免文件占用
            del workbook
            del excel_app
            gc.collect()

            print(f"✅ VBA宏过程已成功添加到：{existing_xlsm_path}")
            return True
        except Exception as e:
            if workbook:
                try:
                    workbook.Close(SaveChanges=False)
                except:
                    pass
            if excel_app:
                try:
                    excel_app.Quit()
                except:
                    pass
            del workbook
            del excel_app
            gc.collect()
            raise Exception(f"❌ 给已有Excel添加宏失败：{str(e)}")

    # ========== 仅对已有Excel添加VBA自定义函数（Function） ==========
    def add_vba_function_to_existing(self, existing_xlsm_path: str, vba_func_code: str,
                                     module_name: str = "FunctionModule") -> bool:
        """
        对已存在的.xlsm文件添加VBA自定义函数（Function，可在单元格中调用）
        :param existing_xlsm_path: 已有.xlsm文件路径
        :param vba_func_code: VBA自定义函数代码（Function...End Function）
        :param module_name: VBA模块名称（避免重复）
        :return: 操作结果
        """
        # 前置校验
        if not existing_xlsm_path.endswith(".xlsm"):
            raise Exception("仅支持对.xlsm格式文件添加自定义函数，请修改文件路径")
        if not exists(existing_xlsm_path):
            raise FileNotFoundError(f"已存在的.xlsm文件不存在：{existing_xlsm_path}")
        if os.name != "nt":
            raise Exception("仅支持Windows系统，无法调用Excel COM组件写入函数")

        excel_app = None
        workbook = None
        try:
            # 启动Excel COM组件，打开已有.xlsm
            excel_app = win32.Dispatch("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False

            workbook = excel_app.Workbooks.Open(Filename=abspath(existing_xlsm_path))

            # 访问VBA项目，添加/获取标准模块（1 = vbext_ct_StdModule）
            vba_project = workbook.VBProject
            try:
                # 若模块已存在，直接获取
                vba_module = vba_project.VBComponents(module_name)
            except:
                # 模块不存在，新建标准模块
                vba_module = vba_project.VBComponents.Add(1)
                vba_module.Name = module_name

            # 写入VBA自定义函数代码（追加到模块末尾）
            vba_module.CodeModule.AddFromString(vba_func_code)

            # 保存修改并关闭
            workbook.Save()
            workbook.Close(SaveChanges=False)
            excel_app.Quit()

            # 释放COM资源，避免文件占用
            del workbook
            del excel_app
            gc.collect()

            print(f"✅ VBA自定义函数已成功添加到：{existing_xlsm_path}")
            return True
        except Exception as e:
            if workbook:
                try:
                    workbook.Close(SaveChanges=False)
                except:
                    pass
            if excel_app:
                try:
                    excel_app.Quit()
                except:
                    pass
            del workbook
            del excel_app
            gc.collect()
            raise Exception(f"❌ 给已有Excel添加自定义函数失败：{str(e)}")

    # ========== 关闭Excel文档 ==========
    def close_excel(self) -> None:
        """关闭Excel文档，释放所有资源"""
        if self.workbook:
            self.workbook.close()
            # 释放openpyxl资源，避免文件占用
            del self.workbook
            del self.current_sheet
            self.workbook = None
            self.current_sheet = None
            self.file_path = None
            gc.collect()


# ========== main函数（保持不变，修复后可正常运行） ==========
def main():
    # 初始化Excel操作实例
    excel_op = ExcelOperator()
    # 定义测试文件路径
    test_xlsx_path = "./测试_无宏Excel.xlsx"
    test_xlsm_path = "./测试_带宏Excel.xlsm"

    try:
        # ---------------------- 步骤1：新建无宏Excel（.xlsx），写入数据并读取返回df ----------------------
        print("=== 步骤1：新建无宏Excel并测试df读写 ===")
        # 新建无宏Excel
        excel_op.new_excel(sheet_name="TestXlsxSheet")
        # 写入测试数据
        test_data = [
            (1, 1, "姓名"), (1, 2, "年龄"), (1, 3, "薪资"),
            (2, 1, "张三"), (2, 2, 28), (2, 3, 15000),
            (3, 1, "李四"), (3, 2, 32), (3, 3, 20000)
        ]
        for row, col, value in test_data:
            excel_op.write_cell(row, col, value)
        # 保存无宏Excel
        excel_op.save_excel(test_xlsx_path)
        # 读取Excel返回df并打印
        df_xlsx = excel_op.read_excel_to_df(test_xlsx_path)
        print("无宏Excel的DataFrame结果：")
        print(df_xlsx)
        print("-" * 50)

        # ---------------------- 步骤2：新建带宏支持的空白Excel（.xlsm），写入测试数据 ----------------------
        print("\n=== 步骤2：新建带宏支持Excel并写入数据 ===")
        excel_op.new_excel_with_macro_support(
            save_path=test_xlsm_path,
            sheet_name="TestXlsmSheet"
        )
        # 写入测试数据（用于宏和函数验证）
        xlsm_test_data = [
            (1, 1, "数值1"), (1, 2, "数值2"), (1, 3, "计算结果（宏）"), (1, 4, "计算结果（函数）"),
            (2, 1, 100), (2, 2, 200), (2, 3, ""), (2, 4, ""),
            (3, 1, 300), (3, 2, 400), (3, 3, ""), (3, 4, "")
        ]
        for row, col, value in xlsm_test_data:
            excel_op.write_cell(row, col, value)
        # 保存数据（不修改宏，仅更新工作表数据）
        excel_op.save_excel()
        print("带宏Excel已写入测试数据")
        print("-" * 50)

        # ---------------------- 步骤3：对已有.xlsm文件添加VBA宏过程（Sub） ----------------------
        print("\n=== 步骤3：给已有带宏Excel添加宏过程 ===")
        # 定义VBA宏过程代码（求和对应行的数值，填充到C列）
        vba_sub_code = '''
' 宏功能：求和A列和B列对应行的数值，填充到C列
Sub CalculateSumToC()
    Dim ws As Worksheet
    Dim last_row As Integer
    Set ws = ThisWorkbook.Worksheets("TestXlsmSheet")
    last_row = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    ' 从第2行开始计算（跳过表头）
    For i = 2 To last_row
        If IsNumeric(ws.Cells(i, 1).Value) And IsNumeric(ws.Cells(i, 2).Value) Then
            ws.Cells(i, 3).Value = ws.Cells(i, 1).Value + ws.Cells(i, 2).Value
        Else
            ws.Cells(i, 3).Value = "非数值"
        End If
    Next i

    MsgBox "✅ 宏执行完成！已完成求和计算并填充到C列", vbInformation, "执行结果"
End Sub
'''
        # 给已有.xlsm添加宏
        excel_op.add_vba_macro_to_existing(
            existing_xlsm_path=test_xlsm_path,
            vba_sub_code=vba_sub_code,
            module_name="SumMacroModule"
        )
        print("-" * 50)

        # ---------------------- 步骤4：对已有.xlsm文件添加VBA自定义函数（Function） ----------------------
        print("\n=== 步骤4：给已有带宏Excel添加自定义函数 ===")
        # 定义VBA自定义函数代码（两数相乘，可在单元格中调用=MyMultiply(A2,B2)）
        vba_func_code = '''
' 自定义函数：计算两个数的乘积（支持单元格调用）
Function MyMultiply(num1 As Double, num2 As Double) As Double
    MyMultiply = num1 * num2
End Function

' 自定义函数：计算两个数的差值
Function MySubtract(num1 As Double, num2 As Double) As Double
    MySubtract = num1 - num2
End Function
'''
        # 给已有.xlsm添加自定义函数
        excel_op.add_vba_function_to_existing(
            existing_xlsm_path=test_xlsm_path,
            vba_func_code=vba_func_code,
            module_name="CalcFunctionModule"
        )
        print("-" * 50)

        # ---------------------- 步骤5：读取带宏Excel的最新数据返回df ----------------------
        print("\n=== 步骤5：读取带宏Excel的DataFrame结果 ===")
        df_xlsm = excel_op.read_excel_to_df(test_xlsm_path)
        print("带宏Excel的DataFrame结果：")
        print(df_xlsm)
        print("-" * 50)

        # ---------------------- 测试完成提示 ----------------------
        print("\n=== 所有测试步骤完成！===")
        print(f"1. 无宏Excel文件：{abspath(test_xlsx_path)}")
        print(f"2. 带宏Excel文件：{abspath(test_xlsm_path)}")
        print("\n验证指南：")
        print("a. 打开带宏Excel文件，点击「启用内容」")
        print("b. 运行宏「CalculateSumToC」：开发工具→宏→选择CalculateSumToC→执行（C列会填充求和结果）")
        print("c. 调用自定义函数：在D2单元格输入=MyMultiply(A2,B2)，回车后查看乘积结果")
        print("d. 下拉填充D列，验证函数批量调用功能")

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误：{str(e)}")
    finally:
        # 关闭Excel资源，释放所有句柄
        excel_op.close_excel()
        gc.collect()


if __name__ == "__main__":
    main()