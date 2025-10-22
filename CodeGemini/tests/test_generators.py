#!/usr/bin/env python3
"""
CodeGemini Code Generators 測試
測試 Test Generator 和 Documentation Generator
"""

import os
import sys
import tempfile
from pathlib import Path
from rich.console import Console

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators.test_gen import TestGenerator
from generators.doc_gen import DocumentationGenerator

console = Console()


def create_sample_module():
    """建立測試用 Python 模組"""
    temp_dir = tempfile.mkdtemp(prefix="gen_test_")
    module_path = os.path.join(temp_dir, "sample.py")

    code = '''#!/usr/bin/env python3
"""
示例模組
用於測試生成器功能
"""


def add(a: int, b: int) -> int:
    """
    將兩個數字相加

    Args:
        a: 第一個數字
        b: 第二個數字

    Returns:
        int: 兩數之和
    """
    return a + b


def multiply(x, y):
    """乘法運算"""
    return x * y


class Calculator:
    """
    計算器類別
    提供基本數學運算
    """

    def __init__(self):
        """初始化計算器"""
        self.result = 0

    def calculate(self, operation: str, a: float, b: float) -> float:
        """
        執行計算

        Args:
            operation: 運算類型
            a: 第一個運算元
            b: 第二個運算元

        Returns:
            float: 計算結果
        """
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        return 0

    def _internal_method(self):
        """內部方法（不應生成測試）"""
        pass
'''

    with open(module_path, 'w', encoding='utf-8') as f:
        f.write(code)

    return temp_dir, module_path


def test_test_generator_initialization():
    """測試 1：TestGenerator 初始化"""
    console.print("\n[bold]測試 1：TestGenerator 初始化[/bold]")

    try:
        # pytest 框架
        gen_pytest = TestGenerator(framework="pytest")
        assert gen_pytest.framework == "pytest", "pytest 框架初始化失敗"

        # unittest 框架
        gen_unittest = TestGenerator(framework="unittest")
        assert gen_unittest.framework == "unittest", "unittest 框架初始化失敗"

        console.print(f"[green]✓ TestGenerator 初始化成功[/green]")
        console.print(f"  pytest 框架：✓")
        console.print(f"  unittest 框架：✓")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_code_analysis():
    """測試 2：程式碼分析"""
    console.print("\n[bold]測試 2：程式碼分析[/bold]")

    try:
        temp_dir, module_path = create_sample_module()
        generator = TestGenerator()

        # 分析檔案
        analysis = generator.analyze_file(module_path)

        assert analysis is not None, "分析結果為 None"
        assert len(analysis["functions"]) == 2, f"函數數量錯誤：{len(analysis['functions'])}"
        assert len(analysis["classes"]) == 1, f"類別數量錯誤：{len(analysis['classes'])}"

        # 檢查函數資訊
        func_names = [f.name for f in analysis["functions"]]
        assert "add" in func_names, "缺少 add 函數"
        assert "multiply" in func_names, "缺少 multiply 函數"

        # 檢查類別資訊
        cls = analysis["classes"][0]
        assert cls.name == "Calculator", "類別名稱錯誤"
        assert len(cls.methods) >= 2, "類別方法數量不足"

        console.print(f"[green]✓ 程式碼分析成功[/green]")
        console.print(f"  函數：{len(analysis['functions'])} 個")
        console.print(f"  類別：{len(analysis['classes'])} 個")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_pytest_generation():
    """測試 3：pytest 測試生成"""
    console.print("\n[bold]測試 3：pytest 測試生成[/bold]")

    try:
        temp_dir, module_path = create_sample_module()
        generator = TestGenerator(framework="pytest")

        # 分析並生成測試
        analysis = generator.analyze_file(module_path)
        test_code = generator.generate_test(analysis)

        # 驗證生成的測試程式碼
        assert "import pytest" in test_code, "缺少 pytest 導入"
        assert "def test_add()" in test_code, "缺少 add 測試函數"
        assert "class TestCalculator:" in test_code, "缺少 Calculator 測試類別"
        assert "@pytest.fixture" in test_code, "缺少 fixture"

        console.print(f"[green]✓ pytest 測試生成成功[/green]")
        console.print(f"  包含 pytest 導入：✓")
        console.print(f"  包含測試函數：✓")
        console.print(f"  包含測試類別：✓")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_unittest_generation():
    """測試 4：unittest 測試生成"""
    console.print("\n[bold]測試 4：unittest 測試生成[/bold]")

    try:
        temp_dir, module_path = create_sample_module()
        generator = TestGenerator(framework="unittest")

        # 分析並生成測試
        analysis = generator.analyze_file(module_path)
        test_code = generator.generate_test(analysis)

        # 驗證生成的測試程式碼
        assert "import unittest" in test_code, "缺少 unittest 導入"
        assert "class TestFunctions(unittest.TestCase):" in test_code, "缺少函數測試類別"
        assert "class TestCalculator(unittest.TestCase):" in test_code, "缺少 Calculator 測試類別"
        assert "def setUp(self):" in test_code, "缺少 setUp 方法"

        console.print(f"[green]✓ unittest 測試生成成功[/green]")
        console.print(f"  包含 unittest 導入：✓")
        console.print(f"  包含測試類別：✓")
        console.print(f"  包含 setUp 方法：✓")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_doc_generator_initialization():
    """測試 5：DocumentationGenerator 初始化"""
    console.print("\n[bold]測試 5：DocumentationGenerator 初始化[/bold]")

    try:
        temp_dir, _ = create_sample_module()

        generator = DocumentationGenerator(temp_dir)

        assert generator.project_path == Path(temp_dir), "專案路徑錯誤"
        assert len(generator.modules) == 0, "初始模組列表應為空"

        console.print(f"[green]✓ DocumentationGenerator 初始化成功[/green]")
        console.print(f"  專案路徑：{generator.project_path}")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_project_scanning():
    """測試 6：專案掃描"""
    console.print("\n[bold]測試 6：專案掃描[/bold]")

    try:
        temp_dir, _ = create_sample_module()

        generator = DocumentationGenerator(temp_dir)
        generator.scan_project()

        assert len(generator.modules) > 0, "未掃描到任何模組"

        module = generator.modules[0]
        assert module.name == "sample", "模組名稱錯誤"
        assert len(module.functions) == 2, "函數數量錯誤"
        assert len(module.classes) == 1, "類別數量錯誤"

        console.print(f"[green]✓ 專案掃描成功[/green]")
        console.print(f"  掃描到模組：{len(generator.modules)} 個")
        console.print(f"  函數：{len(module.functions)} 個")
        console.print(f"  類別：{len(module.classes)} 個")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_readme_generation():
    """測試 7：README 生成"""
    console.print("\n[bold]測試 7：README 生成[/bold]")

    try:
        temp_dir, _ = create_sample_module()

        generator = DocumentationGenerator(temp_dir)
        generator.scan_project()

        readme = generator.generate_readme()

        # 驗證 README 內容
        project_name = Path(temp_dir).name
        assert f"# {project_name}" in readme, "缺少專案標題"
        assert "## 📁 專案結構" in readme, "缺少專案結構"
        assert "## 📦 模組清單" in readme, "缺少模組清單"
        assert "sample" in readme, "缺少 sample 模組"

        console.print(f"[green]✓ README 生成成功[/green]")
        console.print(f"  包含專案標題：✓")
        console.print(f"  包含專案結構：✓")
        console.print(f"  包含模組清單：✓")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_api_docs_generation():
    """測試 8：API 文檔生成"""
    console.print("\n[bold]測試 8：API 文檔生成[/bold]")

    try:
        temp_dir, _ = create_sample_module()

        generator = DocumentationGenerator(temp_dir)
        generator.scan_project()

        api_docs = generator.generate_api_docs()

        # 驗證 API 文檔內容
        assert "API 文檔" in api_docs, "缺少 API 文檔標題"
        assert "class Calculator" in api_docs, "缺少 Calculator 類別文檔"
        assert "def add" in api_docs, "缺少 add 函數文檔"
        assert "將兩個數字相加" in api_docs, "缺少函數說明"

        console.print(f"[green]✓ API 文檔生成成功[/green]")
        console.print(f"  包含類別文檔：✓")
        console.print(f"  包含函數文檔：✓")
        console.print(f"  包含說明文字：✓")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


# ==================== 主測試流程 ====================

def main():
    """執行所有測試"""
    console.print("=" * 70)
    console.print("[bold cyan]CodeGemini Code Generators - 測試套件[/bold cyan]")
    console.print("=" * 70)

    tests = [
        ("TestGenerator 初始化", test_test_generator_initialization),
        ("程式碼分析", test_code_analysis),
        ("pytest 測試生成", test_pytest_generation),
        ("unittest 測試生成", test_unittest_generation),
        ("DocumentationGenerator 初始化", test_doc_generator_initialization),
        ("專案掃描", test_project_scanning),
        ("README 生成", test_readme_generation),
        ("API 文檔生成", test_api_docs_generation),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ 通過" if result else "❌ 失敗"
        except Exception as e:
            console.print(f"[red]測試異常：{e}[/red]")
            results[test_name] = "❌ 失敗"

    # 顯示測試總結
    console.print("\n" + "=" * 70)
    console.print("[bold]測試總結[/bold]")
    console.print("=" * 70)

    for test_name, result in results.items():
        console.print(f"  {test_name}: {result}")

    # 統計
    passed = sum(1 for r in results.values() if "通過" in r)
    total = len(results)

    console.print("-" * 70)
    console.print(f"[bold]總計：{passed}/{total} 測試通過[/bold]")

    if passed < total:
        console.print(f"\n[yellow]⚠️  {total - passed} 個測試失敗[/yellow]")
    else:
        console.print("\n[green]🎉 所有測試通過！Code Generators 準備就緒。[/green]")


if __name__ == "__main__":
    main()
