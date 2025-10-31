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
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console
from utils.i18n import safe_t

console = Console()


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
        console.print(f"\n[#DDA0DD]🔍 {safe_t('test_gen.analyzing_file', '分析檔案：{path}', path=file_path)}[/#DDA0DD]")

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

            console.print(f"[#DA70D6]✓ {safe_t('test_gen.analysis_complete', '分析完成')}[/green]")
            console.print(f"  {safe_t('test_gen.functions', '函數')}：{len(functions)} {safe_t('common.unit', '個')}")
            console.print(f"  {safe_t('test_gen.classes', '類別')}：{len(classes)} {safe_t('common.unit', '個')}")

            return {
                "file_path": file_path,
                "functions": functions,
                "classes": classes,
                "imports": imports
            }

        except Exception as e:
            console.print(f"[dim #DDA0DD]✗ {safe_t('test_gen.analysis_failed', '分析失敗：{error}', error=e)}[/red]")
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
        console.print(f"\n[#DDA0DD]📝 {safe_t('test_gen.generating_tests', '生成測試程式碼...')}[/#DDA0DD]")

        if self.framework == "pytest":
            test_code = self._generate_pytest(analysis)
        elif self.framework == "unittest":
            test_code = self._generate_unittest(analysis)
        else:
            raise ValueError(safe_t('test_gen.unsupported_framework', '不支援的測試框架：{framework}', framework=self.framework))

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(test_code)
            console.print(f"[#DA70D6]✓ {safe_t('test_gen.test_file_saved', '測試檔案已儲存：{path}', path=output_path)}[/green]")

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


# ==================== 命令列介面 ====================

def main():
    """測試生成器命令列工具"""
    import sys

    console.print(f"\n[bold #DDA0DD]{safe_t('test_gen.title', 'CodeGemini Test Generator')}[/bold #DDA0DD]\n")

    if len(sys.argv) < 2:
        console.print(safe_t('test_gen.usage', '用法') + "：")
        console.print("  python generators/test_gen.py <file_path> [--framework pytest|unittest] [--output <path>]")
        console.print(f"\n{safe_t('test_gen.examples', '範例')}：")
        console.print("  python generators/test_gen.py mymodule.py")
        console.print("  python generators/test_gen.py mymodule.py --framework unittest --output test_mymodule.py")
        return

    file_path = sys.argv[1]

    # 解析參數
    framework = "pytest"
    output_path = None

    for i, arg in enumerate(sys.argv):
        if arg == "--framework" and i + 1 < len(sys.argv):
            framework = sys.argv[i + 1]
        elif arg == "--output" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    # 生成測試
    generator = TestGenerator(framework=framework)
    analysis = generator.analyze_file(file_path)

    if analysis:
        test_code = generator.generate_test(analysis, output_path)

        if not output_path:
            console.print(f"\n[#DDA0DD]{safe_t('test_gen.generated_code', '生成的測試程式碼')}：[/#DDA0DD]\n")
            console.print(test_code)


if __name__ == "__main__":
    main()
