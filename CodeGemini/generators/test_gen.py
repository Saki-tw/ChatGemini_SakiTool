#!/usr/bin/env python3
"""
CodeGemini Test Generator Module
測試生成器 - 自動生成單元測試程式碼

此模組負責：
1. 分析原始碼結構
2. 生成單元測試框架
3. 生成測試案例
4. 支援多種測試框架（pytest, unittest）
"""

import os
import re
import ast
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from utils.i18n import safe_t

console = Console()

# 設置日誌
logging.basicConfig(
    filename='test_gen.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@dataclass
class FunctionInfo:
    """函數資訊"""
    name: str
    args: List[str]
    returns: Optional[str]
    docstring: Optional[str]
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None


@dataclass
class ClassInfo:
    """類別資訊"""
    name: str
    methods: List[FunctionInfo]
    docstring: Optional[str]
    base_classes: List[str]


class TestGenerator:
    """
    測試生成器

    自動分析程式碼並生成對應的測試檔案
    """

    def __init__(self, framework: str = "pytest"):
        """
        初始化測試生成器

        Args:
            framework: 測試框架（pytest 或 unittest）
        """
        self.framework = framework
        self.imports = set()

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        分析 Python 檔案

        Args:
            file_path: 檔案路徑

        Returns:
            Dict: 分析結果
        """
        console.print(f"\n[#B565D8]🔍 {safe_t('test_gen.analyzing_file', '分析檔案：{path}', path=file_path)}[/#B565D8]")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 檢查是否為類別方法
                    is_method = any(
                        isinstance(parent, ast.ClassDef)
                        for parent in ast.walk(tree)
                        if any(child == node for child in ast.iter_child_nodes(parent))
                    )

                    if not is_method:
                        func_info = self._extract_function_info(node)
                        functions.append(func_info)

                elif isinstance(node, ast.ClassDef):
                    class_info = self._extract_class_info(node)
                    classes.append(class_info)

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.unparse(node))

            console.print(f"[#B565D8]✓ {safe_t('test_gen.analysis_complete', '分析完成')}[/#B565D8]")
            console.print(f"  {safe_t('test_gen.functions', '函數')}：{len(functions)} {safe_t('common.unit', '個')}")
            console.print(f"  {safe_t('test_gen.classes', '類別')}：{len(classes)} {safe_t('common.unit', '個')}")

            return {
                "file_path": file_path,
                "functions": functions,
                "classes": classes,
                "imports": imports
            }

        except Exception as e:
            console.print(f"[dim #B565D8]✗ {safe_t('test_gen.analysis_failed', '分析失敗：{error}', error=e)}[/dim #B565D8]")
            return None

    def _extract_function_info(self, node: ast.FunctionDef) -> FunctionInfo:
        """提取函數資訊"""
        args = [arg.arg for arg in node.args.args if arg.arg != 'self']

        returns = None
        if node.returns:
            returns = ast.unparse(node.returns)

        docstring = ast.get_docstring(node)

        is_async = isinstance(node, ast.AsyncFunctionDef)

        return FunctionInfo(
            name=node.name,
            args=args,
            returns=returns,
            docstring=docstring,
            is_async=is_async,
            is_method=False
        )

    def _extract_class_info(self, node: ast.ClassDef) -> ClassInfo:
        """提取類別資訊"""
        methods = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function_info(item)
                func_info.is_method = True
                func_info.class_name = node.name
                methods.append(func_info)

        base_classes = [ast.unparse(base) for base in node.bases]
        docstring = ast.get_docstring(node)

        return ClassInfo(
            name=node.name,
            methods=methods,
            docstring=docstring,
            base_classes=base_classes
        )

    def generate_test(
        self,
        analysis: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """
        生成測試程式碼

        Args:
            analysis: 檔案分析結果
            output_path: 輸出路徑（選用）

        Returns:
            str: 測試程式碼
        """
        console.print(f"\n[#B565D8]📝 {safe_t('test_gen.generating_tests', '生成測試程式碼...')}[/#B565D8]")

        if self.framework == "pytest":
            test_code = self._generate_pytest(analysis)
        elif self.framework == "unittest":
            test_code = self._generate_unittest(analysis)
        else:
            raise ValueError(safe_t('test_gen.unsupported_framework', '不支援的測試框架：{framework}', framework=self.framework))

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(test_code)
            console.print(f"[#B565D8]✓ {safe_t('test_gen.test_file_saved', '測試檔案已儲存：{path}', path=output_path)}[/#B565D8]")

        return test_code

    def _generate_pytest(self, analysis: Dict[str, Any]) -> str:
        """生成 pytest 測試程式碼"""
        lines = []

        # 標頭註解
        file_name = Path(analysis["file_path"]).name
        lines.append("#!/usr/bin/env python3")
        lines.append('"""')
        lines.append(f'測試模組：{file_name}')
        lines.append('自動生成的測試程式碼')
        lines.append('"""')
        lines.append("")

        # 導入
        lines.append("import pytest")
        lines.append("from unittest.mock import Mock, patch")
        lines.append("")

        # 導入被測試模組
        module_name = Path(analysis["file_path"]).stem
        lines.append(f"# 從被測試模組導入")
        lines.append(f"# from {module_name} import ...")
        lines.append("")

        # 生成函數測試
        for func in analysis["functions"]:
            lines.extend(self._generate_pytest_function(func))
            lines.append("")

        # 生成類別測試
        for cls in analysis["classes"]:
            lines.extend(self._generate_pytest_class(cls))
            lines.append("")

        return "\n".join(lines)

    def _generate_pytest_function(self, func: FunctionInfo) -> List[str]:
        """生成單個函數的 pytest 測試"""
        lines = []

        # Fixture（如果需要）
        if func.args:
            lines.append(f"@pytest.fixture")
            lines.append(f"def {func.name}_params():")
            lines.append(f'    """提供測試參數"""')
            lines.append(f"    return {{}}")
            lines.append("")

        # 測試函數
        test_name = f"test_{func.name}"
        lines.append(f"def {test_name}():")
        lines.append(f'    """測試 {func.name} 函數"""')
        lines.append(f"    # TODO: 實作測試邏輯")

        if func.docstring:
            lines.append(f"    # 函數說明：{func.docstring.splitlines()[0]}")

        lines.append(f"    ")
        lines.append(f"    # 準備測試資料")

        for arg in func.args:
            lines.append(f"    {arg} = None  # TODO: 設定 {arg} 的測試值")

        lines.append(f"    ")
        lines.append(f"    # 執行測試")
        args_str = ", ".join(func.args)
        lines.append(f"    # result = {func.name}({args_str})")
        lines.append(f"    ")
        lines.append(f"    # 驗證結果")
        lines.append(f"    # assert result == expected")
        lines.append(f"    pass")

        return lines

    def _generate_pytest_class(self, cls: ClassInfo) -> List[str]:
        """生成類別的 pytest 測試"""
        lines = []

        # 測試類別
        lines.append(f"class Test{cls.name}:")
        lines.append(f'    """測試 {cls.name} 類別"""')
        lines.append("")

        # Fixture：建立測試實例
        lines.append(f"    @pytest.fixture")
        lines.append(f"    def {cls.name.lower()}_instance(self):")
        lines.append(f'        """建立 {cls.name} 測試實例"""')
        lines.append(f"        # return {cls.name}()")
        lines.append(f"        pass")
        lines.append("")

        # 測試初始化
        lines.append(f"    def test_init(self):")
        lines.append(f'        """測試初始化"""')
        lines.append(f"        # instance = {cls.name}()")
        lines.append(f"        # assert instance is not None")
        lines.append(f"        pass")
        lines.append("")

        # 為每個方法生成測試
        for method in cls.methods:
            if method.name.startswith('_'):
                continue  # 跳過私有方法

            lines.append(f"    def test_{method.name}(self, {cls.name.lower()}_instance):")
            lines.append(f'        """測試 {method.name} 方法"""')
            lines.append(f"        # TODO: 實作測試邏輯")

            if method.docstring:
                lines.append(f"        # 方法說明：{method.docstring.splitlines()[0]}")

            lines.append(f"        pass")
            lines.append("")

        return lines

    def _generate_unittest(self, analysis: Dict[str, Any]) -> str:
        """生成 unittest 測試程式碼"""
        lines = []

        # 標頭註解
        file_name = Path(analysis["file_path"]).name
        lines.append("#!/usr/bin/env python3")
        lines.append('"""')
        lines.append(f'測試模組：{file_name}')
        lines.append('自動生成的測試程式碼')
        lines.append('"""')
        lines.append("")

        # 導入
        lines.append("import unittest")
        lines.append("from unittest.mock import Mock, patch")
        lines.append("")

        # 導入被測試模組
        module_name = Path(analysis["file_path"]).stem
        lines.append(f"# 從被測試模組導入")
        lines.append(f"# from {module_name} import ...")
        lines.append("")

        # 生成測試類別
        for cls in analysis["classes"]:
            lines.extend(self._generate_unittest_class(cls))
            lines.append("")

        # 為獨立函數生成測試類別
        if analysis["functions"]:
            lines.append("class TestFunctions(unittest.TestCase):")
            lines.append('    """測試獨立函數"""')
            lines.append("")

            for func in analysis["functions"]:
                lines.extend(self._generate_unittest_function(func))
                lines.append("")

        # 主程式
        lines.append("")
        lines.append('if __name__ == "__main__":')
        lines.append("    unittest.main()")

        return "\n".join(lines)

    def _generate_unittest_function(self, func: FunctionInfo) -> List[str]:
        """生成單個函數的 unittest 測試"""
        lines = []

        test_name = f"test_{func.name}"
        lines.append(f"    def {test_name}(self):")
        lines.append(f'        """測試 {func.name} 函數"""')
        lines.append(f"        # TODO: 實作測試邏輯")

        if func.docstring:
            lines.append(f"        # 函數說明：{func.docstring.splitlines()[0]}")

        lines.append(f"        self.fail('Not implemented')")

        return lines

    def _generate_unittest_class(self, cls: ClassInfo) -> List[str]:
        """生成類別的 unittest 測試"""
        lines = []

        lines.append(f"class Test{cls.name}(unittest.TestCase):")
        lines.append(f'    """測試 {cls.name} 類別"""')
        lines.append("")

        # setUp 方法
        lines.append(f"    def setUp(self):")
        lines.append(f'        """測試前準備"""')
        lines.append(f"        # self.instance = {cls.name}()")
        lines.append(f"        pass")
        lines.append("")

        # tearDown 方法
        lines.append(f"    def tearDown(self):")
        lines.append(f'        """測試後清理"""')
        lines.append(f"        pass")
        lines.append("")

        # 為每個方法生成測試
        for method in cls.methods:
            if method.name.startswith('_'):
                continue  # 跳過私有方法

            lines.append(f"    def test_{method.name}(self):")
            lines.append(f'        """測試 {method.name} 方法"""')
            lines.append(f"        # TODO: 實作測試邏輯")

            if method.docstring:
                lines.append(f"        # 方法說明：{method.docstring.splitlines()[0]}")

            lines.append(f"        self.fail('Not implemented')")
            lines.append("")

        return lines


# ==================== 批次處理功能 ====================

class BatchTestGenerator:
    """
    批次測試生成器

    支援：
    - 單檔案多函數掃描
    - 目錄遞迴掃描
    - 進度顯示
    - 錯誤處理與日誌
    """

    # 排除的目錄名稱
    EXCLUDED_DIRS = {
        'venv', '.venv', 'venv_py314',  # 虛擬環境
        '__pycache__', '.git', '.svn',   # 版本控制
        'node_modules', '.tox',           # 其他工具
        'build', 'dist', '.eggs',         # 構建產物
    }

    # 排除的檔案模式
    EXCLUDED_PATTERNS = {
        'test_*.py',      # 已存在的測試檔案
        '*_test.py',      # 已存在的測試檔案
        'conftest.py',    # pytest 配置
        'setup.py',       # 設定檔案
    }

    def __init__(self, framework: str = "pytest", filter_private: bool = True):
        """
        初始化批次測試生成器

        Args:
            framework: 測試框架（pytest 或 unittest）
            filter_private: 是否過濾私有函數（__開頭）
        """
        self.framework = framework
        self.filter_private = filter_private
        self.generator = TestGenerator(framework=framework)
        self.stats = {
            'total_files': 0,
            'total_functions': 0,
            'total_classes': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

    def scan_file_functions(self, file_path: str) -> List[FunctionInfo]:
        """
        2.5.1 實作單檔案多函數掃描

        使用 AST 遍歷整個 Python 檔案，提取所有函數定義

        Args:
            file_path: Python 檔案路徑

        Returns:
            List[FunctionInfo]: 函數資訊列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # 過濾私有函數（可選）
                    if self.filter_private and node.name.startswith('__'):
                        continue

                    # 過濾特殊方法（可選）
                    if self.filter_private and node.name.startswith('_') and node.name.endswith('_'):
                        continue

                    # 檢查是否為類別方法
                    is_method = False
                    class_name = None

                    # 遍歷父節點尋找類別定義
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef):
                            if node in ast.walk(parent):
                                is_method = True
                                class_name = parent.name
                                break

                    func_info = self.generator._extract_function_info(node)
                    func_info.is_method = is_method
                    func_info.class_name = class_name
                    functions.append(func_info)

            logging.info(f"成功掃描檔案: {file_path}, 找到 {len(functions)} 個函數")
            return functions

        except SyntaxError as e:
            logging.error(f"語法錯誤 - {file_path}: {e}")
            return []
        except Exception as e:
            logging.error(f"掃描檔案失敗 - {file_path}: {e}")
            return []

    def scan_directory(self, directory: str, recursive: bool = True) -> List[str]:
        """
        2.5.2 實作目錄遞迴掃描

        使用 Path.rglob() 遞迴查找 Python 檔案，排除特定目錄

        Args:
            directory: 目錄路徑
            recursive: 是否遞迴掃描子目錄

        Returns:
            List[str]: Python 檔案路徑列表
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            logging.error(f"目錄不存在: {directory}")
            return []

        if not dir_path.is_dir():
            logging.error(f"不是目錄: {directory}")
            return []

        python_files = []

        # 使用 rglob 或 glob
        pattern = '**/*.py' if recursive else '*.py'

        for file_path in dir_path.glob(pattern):
            # 檢查是否在排除目錄中
            if any(excluded in file_path.parts for excluded in self.EXCLUDED_DIRS):
                logging.info(f"跳過排除目錄中的檔案: {file_path}")
                self.stats['skipped'] += 1
                continue

            # 檢查檔案名稱模式
            if any(file_path.match(pattern) for pattern in self.EXCLUDED_PATTERNS):
                logging.info(f"跳過測試檔案: {file_path}")
                self.stats['skipped'] += 1
                continue

            python_files.append(str(file_path))

        logging.info(f"目錄掃描完成: {directory}, 找到 {len(python_files)} 個 Python 檔案")
        return python_files

    def batch_generate(
        self,
        target: str,
        output_dir: Optional[str] = None,
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        批次生成測試

        2.5.3 整合 Rich Progress Bar
        2.5.4 錯誤處理與日誌

        Args:
            target: 檔案路徑或目錄路徑
            output_dir: 輸出目錄（預設為 tests/）
            recursive: 是否遞迴掃描子目錄

        Returns:
            Dict: 批次處理結果統計
        """
        target_path = Path(target)

        # 確定要處理的檔案列表
        if target_path.is_file():
            files_to_process = [str(target_path)]
        elif target_path.is_dir():
            files_to_process = self.scan_directory(str(target_path), recursive)
        else:
            console.print(f"[red]❌ 無效的路徑: {target}[/red]")
            return self.stats

        if not files_to_process:
            console.print(f"[yellow]⚠️  沒有找到要處理的 Python 檔案[/yellow]")
            return self.stats

        self.stats['total_files'] = len(files_to_process)

        # 設置輸出目錄
        if output_dir is None:
            output_dir = "tests"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 2.5.3 Rich Progress Bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                "[#B565D8]生成測試檔案...",
                total=len(files_to_process)
            )

            for file_path in files_to_process:
                # 更新進度描述
                file_name = Path(file_path).name
                progress.update(task, description=f"[#B565D8]處理: {file_name}")

                try:
                    # 分析檔案
                    analysis = self.generator.analyze_file(file_path)

                    if not analysis:
                        self.stats['failed'] += 1
                        logging.error(f"分析失敗: {file_path}")
                        progress.advance(task)
                        continue

                    # 統計
                    self.stats['total_functions'] += len(analysis['functions'])
                    self.stats['total_classes'] += len(analysis['classes'])

                    # 生成測試檔案名稱
                    source_name = Path(file_path).stem
                    test_file_name = f"test_{source_name}.py"
                    test_file_path = output_path / test_file_name

                    # 生成測試程式碼
                    test_code = self.generator.generate_test(
                        analysis,
                        output_path=str(test_file_path)
                    )

                    self.stats['success'] += 1
                    logging.info(f"成功生成測試: {test_file_path}")

                except SyntaxError as e:
                    self.stats['failed'] += 1
                    logging.error(f"語法錯誤 - {file_path}: {e}")
                    console.print(f"[yellow]⚠️  語法錯誤: {file_name} - {e}[/yellow]")

                except Exception as e:
                    self.stats['failed'] += 1
                    logging.error(f"處理失敗 - {file_path}: {e}")
                    console.print(f"[red]❌ 處理失敗: {file_name} - {e}[/red]")

                progress.advance(task)

        # 顯示最終報告
        self._print_summary()

        return self.stats

    def _print_summary(self):
        """顯示批次處理摘要"""
        console.print("\n" + "="*60)
        console.print("[bold #B565D8]批次測試生成摘要[/bold #B565D8]")
        console.print("="*60)

        console.print(f"\n📁 處理的檔案: {self.stats['total_files']}")
        console.print(f"✅ 成功: {self.stats['success']}")
        console.print(f"❌ 失敗: {self.stats['failed']}")
        console.print(f"⏭️  跳過: {self.stats['skipped']}")

        console.print(f"\n📊 統計:")
        console.print(f"   函數總數: {self.stats['total_functions']}")
        console.print(f"   類別總數: {self.stats['total_classes']}")

        # 計算成功率
        if self.stats['total_files'] > 0:
            success_rate = (self.stats['success'] / self.stats['total_files']) * 100
            console.print(f"\n📈 成功率: {success_rate:.1f}%")

        # 日誌檔案提示
        console.print(f"\n📝 詳細日誌: test_gen.log")
        console.print("="*60 + "\n")


# ==================== 命令列介面 ====================

def create_argument_parser():
    """
    2.6.1 設計命令列參數結構
    2.6.2 實作 ArgumentParser

    創建並配置命令列參數解析器

    Returns:
        argparse.ArgumentParser: 配置完成的參數解析器
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog='test_gen.py',
        description='CodeGemini 單元測試自動生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例:
  # 單檔案模式
  python generators/test_gen.py mymodule.py
  python generators/test_gen.py mymodule.py --framework unittest --output test_mymodule.py

  # 批次處理模式
  python generators/test_gen.py src/ --batch
  python generators/test_gen.py . --batch --output-dir my_tests/

  # 預覽模式（不實際寫入）
  python generators/test_gen.py mymodule.py --preview

  # 生成 Mock 物件
  python generators/test_gen.py mymodule.py --include-mocks
        '''
    )

    # 位置參數：輸入檔案或目錄
    parser.add_argument(
        'input',
        type=str,
        metavar='<input_file_or_dir>',
        help='輸入檔案路徑或目錄路徑'
    )

    # --output, -o: 輸出檔案（單檔案模式）
    parser.add_argument(
        '--output', '-o',
        type=str,
        metavar='<path>',
        help='輸出測試檔案路徑（預設：自動生成 test_<檔名>.py）'
    )

    # --output-dir: 輸出目錄（批次模式）
    parser.add_argument(
        '--output-dir',
        type=str,
        metavar='<dir>',
        default='./tests',
        help='輸出測試檔案的目錄（預設：./tests）'
    )

    # --framework: 測試框架
    parser.add_argument(
        '--framework',
        type=str,
        choices=['pytest', 'unittest'],
        default='pytest',
        help='測試框架（預設：pytest）'
    )

    # --include-mocks: 是否生成 Mock
    parser.add_argument(
        '--include-mocks',
        action='store_true',
        default=True,
        help='生成 Mock 物件（預設：True）'
    )

    # --no-mocks: 不生成 Mock
    parser.add_argument(
        '--no-mocks',
        action='store_true',
        help='不生成 Mock 物件'
    )

    # --style: 測試命名風格
    parser.add_argument(
        '--style',
        type=str,
        default='test_<func_name>',
        help='測試命名風格（預設：test_<func_name>）'
    )

    # --verbose, -v: 詳細輸出
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細輸出模式'
    )

    # --preview: 預覽模式（不實際寫入）
    parser.add_argument(
        '--preview',
        action='store_true',
        help='預覽模式（僅顯示生成的測試程式碼，不實際寫入檔案）'
    )

    # --batch: 批次處理模式
    parser.add_argument(
        '--batch',
        action='store_true',
        help='批次處理模式（處理目錄中所有 Python 檔案）'
    )

    # --no-recursive: 不遞迴掃描（僅批次模式）
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='不遞迴掃描子目錄（僅批次模式）'
    )

    # --filter-private: 過濾私有函數
    parser.add_argument(
        '--filter-private',
        action='store_true',
        default=True,
        help='過濾私有函數（__開頭）（預設：True）'
    )

    return parser


def main():
    """
    2.6.3 整合主流程

    測試生成器命令列工具
    根據參數初始化 TestGenerator 並調用相應功能
    """
    import sys

    # 創建參數解析器
    parser = create_argument_parser()

    # 如果沒有參數，顯示幫助訊息
    if len(sys.argv) == 1:
        console.print(f"\n[bold #B565D8]CodeGemini Test Generator[/bold #B565D8]\n")
        parser.print_help()
        return 0

    # 解析命令列參數
    args = parser.parse_args()

    # 顯示標題
    console.print(f"\n[bold #B565D8]{safe_t('test_gen.title', 'CodeGemini Test Generator')}[/bold #B565D8]\n")

    # 參數驗證：檔案/目錄存在性
    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[red]❌ 錯誤: 路徑不存在 - {args.input}[/red]")
        return 1

    # 處理 --no-mocks 參數
    include_mocks = args.include_mocks and not args.no_mocks

    # 詳細輸出模式
    if args.verbose:
        console.print(f"[dim]參數設定：[/dim]")
        console.print(f"  輸入: {args.input}")
        console.print(f"  框架: {args.framework}")
        console.print(f"  Mock: {'是' if include_mocks else '否'}")
        console.print(f"  預覽模式: {'是' if args.preview else '否'}")
        console.print(f"  批次模式: {'是' if args.batch else '否'}")
        console.print()

    # 批次處理模式
    if args.batch or input_path.is_dir():
        console.print(f"[#B565D8]🚀 啟動批次處理模式...[/#B565D8]\n")

        batch_generator = BatchTestGenerator(
            framework=args.framework,
            filter_private=args.filter_private
        )

        stats = batch_generator.batch_generate(
            target=args.input,
            output_dir=args.output_dir,
            recursive=not args.no_recursive
        )

        # 返回適當的退出碼
        if stats['failed'] > 0:
            return 1
        return 0

    # 單檔案模式
    generator = TestGenerator(framework=args.framework)
    analysis = generator.analyze_file(args.input)

    if not analysis:
        console.print(f"[red]❌ 分析失敗[/red]")
        return 1

    # 生成測試程式碼
    output_path = args.output

    # 預覽模式：不寫入檔案
    if args.preview:
        console.print(f"\n[#B565D8]📋 預覽模式 - 生成的測試程式碼：[/#B565D8]\n")
        test_code = generator.generate_test(analysis, output_path=None)
        console.print(test_code)
        console.print(f"\n[yellow]ℹ️  預覽模式：未寫入任何檔案[/yellow]")
        return 0

    # 正常模式：生成並寫入
    test_code = generator.generate_test(analysis, output_path)

    if not output_path:
        console.print(f"\n[#B565D8]{safe_t('test_gen.generated_code', '生成的測試程式碼')}：[/#B565D8]\n")
        console.print(test_code)

    # 輸出結果摘要
    console.print(f"\n[#B565D8]✅ 測試生成完成[/#B565D8]")
    console.print(f"   函數: {len(analysis['functions'])} 個")
    console.print(f"   類別: {len(analysis['classes'])} 個")

    if output_path:
        console.print(f"   輸出: {output_path}")

    # 返回成功退出碼
    return 0


if __name__ == "__main__":
    main()
