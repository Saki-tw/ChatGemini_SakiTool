#!/usr/bin/env python3
"""
進階測試生成器 - 使用 Gemini AI 生成智能單元測試

設計哲學：
- 智能推理 - 使用 Gemini API 理解程式碼邏輯
- 全面覆蓋 - 生成正常/邊界/異常三類測試
- Mock 自動化 - 智能識別並生成 Mock 物件
- 批次處理 - 支援檔案/目錄掃描

Created: 2025-11-01
Author: Claude Code with Saki-tw
"""

import os
import sys
import ast
import re
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich.table import Table
from rich import box

console = Console()


@dataclass
class FunctionInfo:
    """函數資訊"""
    name: str
    args: List[str]
    arg_types: Dict[str, str]  # 參數類型註解
    returns: Optional[str]
    docstring: Optional[str]
    source_code: str
    line_number: int
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None
    external_calls: List[str] = None  # 外部函數調用（需要 Mock）

    def __post_init__(self):
        if self.external_calls is None:
            self.external_calls = []


@dataclass
class TestCase:
    """測試案例"""
    category: str  # normal, boundary, exception
    description: str
    setup_code: str
    test_code: str
    assertion_code: str
    mock_code: str = ""


class AdvancedTestGenerator:
    """進階測試生成器 - Gemini AI 驅動"""

    def __init__(self, framework: str = "pytest", use_gemini: bool = True):
        """初始化測試生成器

        Args:
            framework: 測試框架 (pytest/unittest)
            use_gemini: 是否使用 Gemini API 智能生成
        """
        self.framework = framework
        self.use_gemini = use_gemini
        self.gemini_client = None

        if use_gemini:
            self._init_gemini()

    def _init_gemini(self):
        """初始化 Gemini API 客戶端"""
        try:
            from google import genai

            api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if not api_key:
                console.print("[yellow]⚠ 未找到 Gemini API 金鑰，將使用基本模板[/yellow]")
                self.use_gemini = False
                return

            self.gemini_client = genai.Client(api_key=api_key)
            console.print("[green]✓ Gemini API 已就緒[/green]")

        except ImportError:
            console.print("[yellow]⚠ google-genai 未安裝，將使用基本模板[/yellow]")
            self.use_gemini = False
        except Exception as e:
            console.print(f"[yellow]⚠ Gemini 初始化失敗: {e}[/yellow]")
            self.use_gemini = False

    def analyze_function(self, source_code: str, function_name: Optional[str] = None) -> FunctionInfo:
        """分析單個函數

        Args:
            source_code: 函數原始碼
            function_name: 函數名稱（如果為 None 則自動偵測）

        Returns:
            FunctionInfo: 函數資訊
        """
        try:
            tree = ast.parse(source_code)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if function_name is None or node.name == function_name:
                        return self._extract_function_info(node, source_code)

            raise ValueError(f"找不到函數: {function_name}")

        except Exception as e:
            console.print(f"[red]✗ 分析失敗: {e}[/red]")
            return None

    def _extract_function_info(self, node: ast.FunctionDef, source_code: str) -> FunctionInfo:
        """提取函數詳細資訊"""
        # 參數
        args = [arg.arg for arg in node.args.args if arg.arg != 'self']

        # 參數類型註解
        arg_types = {}
        for arg in node.args.args:
            if arg.arg != 'self' and arg.annotation:
                arg_types[arg.arg] = ast.unparse(arg.annotation)

        # 返回值類型
        returns = None
        if node.returns:
            returns = ast.unparse(node.returns)

        # Docstring
        docstring = ast.get_docstring(node)

        # 檢測外部調用
        external_calls = self._detect_external_calls(node)

        # 取得原始碼片段
        func_source = ast.get_source_segment(source_code, node)

        return FunctionInfo(
            name=node.name,
            args=args,
            arg_types=arg_types,
            returns=returns,
            docstring=docstring,
            source_code=func_source or "",
            line_number=node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            external_calls=external_calls
        )

    def _detect_external_calls(self, node: ast.FunctionDef) -> List[str]:
        """檢測函數中的外部調用（需要 Mock）"""
        external_calls = []

        for child in ast.walk(node):
            # 檢測函數調用
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    external_calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    external_calls.append(ast.unparse(child.func))

        # 去重並排除內建函數
        builtins = {'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple'}
        return list(set(call for call in external_calls if call not in builtins))

    def generate_test_cases(self, func_info: FunctionInfo) -> List[TestCase]:
        """生成測試案例

        Args:
            func_info: 函數資訊

        Returns:
            List[TestCase]: 測試案例列表
        """
        if self.use_gemini:
            return self._generate_with_gemini(func_info)
        else:
            return self._generate_with_template(func_info)

    def _generate_with_gemini(self, func_info: FunctionInfo) -> List[TestCase]:
        """使用 Gemini API 生成智能測試案例"""
        console.print(f"[dim]正在為 {func_info.name} 生成智能測試案例...[/dim]")

        prompt = f"""你是一個專業的 Python 測試工程師。請為以下函數生成完整的單元測試案例。

函數資訊：
```python
{func_info.source_code}
```

參數類型：{func_info.arg_types if func_info.arg_types else '無類型註解'}
返回值：{func_info.returns if func_info.returns else '無返回值註解'}
外部調用：{', '.join(func_info.external_calls) if func_info.external_calls else '無'}

請生成以下三類測試案例（使用 {self.framework} 框架）：

1. **正常情況測試**（至少 3 個案例）
   - 典型輸入值
   - 不同的有效組合

2. **邊界條件測試**
   - 空值測試（None, 空字串, 空列表等）
   - 極值測試（最大值, 最小值）
   - 邊界值測試

3. **異常處理測試**
   - 無效輸入
   - 錯誤類型
   - 預期的異常

請以 JSON 格式回覆，格式如下：
{{
  "test_cases": [
    {{
      "category": "normal",
      "description": "測試描述",
      "setup": "# 準備測試資料\\nvalue = 42",
      "execution": "result = {func_info.name}(value)",
      "assertion": "assert result == expected",
      "mock_needed": ["函數名"] (如果需要 Mock)
    }},
    ...
  ]
}}

注意：
- 使用繁體中文描述
- 程式碼使用英文
- 確保測試案例具體可執行
- 如有外部調用，生成 Mock 程式碼
"""

        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )

            # 解析 Gemini 回應
            return self._parse_gemini_response(response.text, func_info)

        except Exception as e:
            console.print(f"[yellow]⚠ Gemini 生成失敗，使用基本模板: {e}[/yellow]")
            return self._generate_with_template(func_info)

    def _parse_gemini_response(self, response_text: str, func_info: FunctionInfo) -> List[TestCase]:
        """解析 Gemini 回應"""
        import json

        # 提取 JSON 部分
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if not json_match:
            raise ValueError("無法從 Gemini 回應中提取 JSON")

        data = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))

        test_cases = []
        for case_data in data.get('test_cases', []):
            # 生成 Mock 程式碼
            mock_code = ""
            if case_data.get('mock_needed'):
                mock_code = self._generate_mock_code(case_data['mock_needed'])

            test_cases.append(TestCase(
                category=case_data.get('category', 'normal'),
                description=case_data.get('description', ''),
                setup_code=case_data.get('setup', ''),
                test_code=case_data.get('execution', ''),
                assertion_code=case_data.get('assertion', ''),
                mock_code=mock_code
            ))

        return test_cases

    def _generate_with_template(self, func_info: FunctionInfo) -> List[TestCase]:
        """使用基本模板生成測試案例"""
        test_cases = []

        # 正常情況測試
        test_cases.append(TestCase(
            category='normal',
            description=f'測試 {func_info.name} 正常情況',
            setup_code=self._generate_setup_code(func_info, 'normal'),
            test_code=f'result = {func_info.name}({", ".join(func_info.args)})',
            assertion_code='assert result is not None  # TODO: 修改為實際預期值'
        ))

        # 邊界條件測試
        if func_info.args:
            test_cases.append(TestCase(
                category='boundary',
                description=f'測試 {func_info.name} 空值情況',
                setup_code=self._generate_setup_code(func_info, 'boundary'),
                test_code=f'result = {func_info.name}({", ".join(["None"] * len(func_info.args))})',
                assertion_code='# TODO: 驗證空值處理'
            ))

        # 異常處理測試
        test_cases.append(TestCase(
            category='exception',
            description=f'測試 {func_info.name} 異常處理',
            setup_code='# 準備無效輸入',
            test_code=f'with pytest.raises(Exception):\n        {func_info.name}(invalid_input)',
            assertion_code=''
        ))

        return test_cases

    def _generate_setup_code(self, func_info: FunctionInfo, category: str) -> str:
        """生成測試準備程式碼"""
        lines = []
        lines.append("# 準備測試資料")

        for arg in func_info.args:
            if category == 'normal':
                # 根據類型註解推斷值
                arg_type = func_info.arg_types.get(arg, '')
                if 'int' in arg_type:
                    lines.append(f"{arg} = 42")
                elif 'str' in arg_type:
                    lines.append(f'{arg} = "test"')
                elif 'list' in arg_type or 'List' in arg_type:
                    lines.append(f"{arg} = [1, 2, 3]")
                else:
                    lines.append(f"{arg} = None  # TODO: 設定 {arg} 的測試值")
            elif category == 'boundary':
                lines.append(f"{arg} = None")
            else:
                lines.append(f"{arg} = 'invalid'")

        return '\n    '.join(lines)

    def _generate_mock_code(self, mock_targets: List[str]) -> str:
        """生成 Mock 程式碼"""
        lines = []

        for target in mock_targets:
            mock_name = f"mock_{target.replace('.', '_')}"
            lines.append(f"with patch('{target}') as {mock_name}:")
            lines.append(f"    {mock_name}.return_value = None  # TODO: 設定 Mock 返回值")

        return '\n    '.join(lines)

    def generate_pytest_file(
        self,
        func_info: FunctionInfo,
        test_cases: List[TestCase],
        output_path: Optional[str] = None
    ) -> str:
        """生成完整的 pytest 測試檔案"""
        lines = []

        # 檔頭
        lines.append("#!/usr/bin/env python3")
        lines.append('"""')
        lines.append(f'測試模組：{func_info.name}')
        lines.append('自動生成的單元測試')
        lines.append(f'生成時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append('"""')
        lines.append("")

        # 導入
        lines.append("import pytest")
        lines.append("from unittest.mock import Mock, patch, MagicMock")
        lines.append("")
        lines.append("# TODO: 從被測試模組導入函數")
        lines.append(f"# from your_module import {func_info.name}")
        lines.append("")

        # Fixtures
        if func_info.external_calls:
            lines.append("# Fixtures for mocking")
            for call in func_info.external_calls:
                fixture_name = f"mock_{call.replace('.', '_')}"
                lines.append(f"@pytest.fixture")
                lines.append(f"def {fixture_name}():")
                lines.append(f'    """Mock {call}"""')
                lines.append(f"    with patch('{call}') as mock:")
                lines.append(f"        mock.return_value = None  # TODO: 設定返回值")
                lines.append(f"        yield mock")
                lines.append("")

        # 生成測試函數
        for i, test_case in enumerate(test_cases, 1):
            test_name = f"test_{func_info.name}_{test_case.category}_{i}"

            lines.append(f"def {test_name}():")
            lines.append(f'    """{test_case.description}"""')

            if test_case.mock_code:
                lines.append(f"    {test_case.mock_code}")

            if test_case.setup_code:
                lines.append(f"    {test_case.setup_code}")

            lines.append(f"    ")
            lines.append(f"    # 執行測試")
            lines.append(f"    {test_case.test_code}")

            if test_case.assertion_code:
                lines.append(f"    ")
                lines.append(f"    # 驗證結果")
                lines.append(f"    {test_case.assertion_code}")

            lines.append("")
            lines.append("")

        # 生成測試文件
        lines.append("# 測試覆蓋率統計")
        lines.append(f"# 正常測試: {sum(1 for tc in test_cases if tc.category == 'normal')}")
        lines.append(f"# 邊界測試: {sum(1 for tc in test_cases if tc.category == 'boundary')}")
        lines.append(f"# 異常測試: {sum(1 for tc in test_cases if tc.category == 'exception')}")

        test_code = "\n".join(lines)

        # 儲存檔案
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(test_code)
            console.print(f"[green]✓ 測試檔案已儲存: {output_path}[/green]")

        return test_code

    def batch_process_file(self, file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """批次處理單個檔案中的所有函數

        Args:
            file_path: 輸入檔案路徑
            output_dir: 輸出目錄（如果為 None 則使用同目錄下的 tests/）

        Returns:
            處理結果統計
        """
        console.print(f"\n[bold #B565D8]🔍 掃描檔案: {file_path}[/bold #B565D8]")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # 排除私有函數和 magic 方法
                    if not node.name.startswith('_'):
                        func_info = self._extract_function_info(node, source_code)
                        functions.append(func_info)

            console.print(f"[#87CEEB]發現 {len(functions)} 個公開函數[/#87CEEB]\n")

            if not functions:
                console.print("[yellow]未找到可測試的函數[/yellow]")
                return {"processed": 0, "failed": 0}

            # 準備輸出目錄
            if output_dir is None:
                output_dir = Path(file_path).parent / 'tests'

            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 處理每個函數
            results = {"processed": 0, "failed": 0, "files": []}

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                task = progress.add_task("生成測試...", total=len(functions))

                for func in functions:
                    try:
                        # 生成測試案例
                        test_cases = self.generate_test_cases(func)

                        # 輸出檔案
                        test_file_name = f"test_{func.name}.py"
                        test_file_path = output_dir / test_file_name

                        # 生成測試檔案
                        self.generate_pytest_file(func, test_cases, str(test_file_path))

                        results["processed"] += 1
                        results["files"].append(str(test_file_path))

                    except Exception as e:
                        console.print(f"[red]✗ 處理 {func.name} 失敗: {e}[/red]")
                        results["failed"] += 1

                    progress.update(task, advance=1)

            return results

        except Exception as e:
            console.print(f"[red]✗ 檔案處理失敗: {e}[/red]")
            return {"processed": 0, "failed": 1}

    def batch_process_directory(self, dir_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """批次處理目錄中的所有 Python 檔案

        Args:
            dir_path: 輸入目錄路徑
            output_dir: 輸出目錄

        Returns:
            處理結果統計
        """
        console.print(f"\n[bold #B565D8]📁 掃描目錄: {dir_path}[/bold #B565D8]")

        dir_path = Path(dir_path)
        python_files = list(dir_path.rglob("*.py"))

        # 排除測試檔案和 __init__.py
        python_files = [
            f for f in python_files
            if not f.name.startswith('test_') and f.name != '__init__.py'
        ]

        console.print(f"[#87CEEB]發現 {len(python_files)} 個 Python 檔案[/#87CEEB]\n")

        total_results = {"processed": 0, "failed": 0, "files": []}

        for py_file in python_files:
            console.print(f"\n[dim]處理: {py_file.name}[/dim]")
            file_results = self.batch_process_file(str(py_file), output_dir)

            total_results["processed"] += file_results["processed"]
            total_results["failed"] += file_results["failed"]
            total_results["files"].extend(file_results.get("files", []))

        return total_results


def main():
    """命令列介面"""
    import argparse

    parser = argparse.ArgumentParser(
        description='進階測試生成器 - 使用 Gemini AI 生成智能單元測試',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  # 為單一函數生成測試
  python3 advanced_test_gen.py my_module.py

  # 指定輸出路徑
  python3 advanced_test_gen.py my_module.py --output tests/test_my_module.py

  # 批次處理整個目錄
  python3 advanced_test_gen.py src/ --batch --output tests/

  # 使用 unittest 框架（預設為 pytest）
  python3 advanced_test_gen.py my_module.py --framework unittest

  # 不使用 Gemini（僅基本模板）
  python3 advanced_test_gen.py my_module.py --no-gemini
        """
    )

    parser.add_argument('path', help='Python 檔案或目錄路徑')
    parser.add_argument('--output', '-o', help='輸出路徑或目錄')
    parser.add_argument('--framework', '-f', choices=['pytest', 'unittest'], default='pytest',
                        help='測試框架（預設: pytest）')
    parser.add_argument('--batch', '-b', action='store_true',
                        help='批次處理模式（處理目錄）')
    parser.add_argument('--no-gemini', action='store_true',
                        help='不使用 Gemini API（僅基本模板）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='顯示詳細輸出')

    args = parser.parse_args()

    console.print("\n[bold #B565D8]🧪 進階測試生成器[/bold #B565D8]\n")

    # 初始化生成器
    generator = AdvancedTestGenerator(
        framework=args.framework,
        use_gemini=not args.no_gemini
    )

    # 處理模式
    input_path = Path(args.path)

    if args.batch or input_path.is_dir():
        # 批次處理目錄
        results = generator.batch_process_directory(str(input_path), args.output)

        # 顯示統計
        console.print("\n[bold]處理完成！[/bold]")
        console.print(f"  成功: {results['processed']}")
        console.print(f"  失敗: {results['failed']}")
        console.print(f"  總計: {results['processed'] + results['failed']}")

    elif input_path.is_file():
        # 處理單一檔案
        results = generator.batch_process_file(str(input_path), args.output)

        console.print("\n[bold]處理完成！[/bold]")
        console.print(f"  生成測試: {results['processed']}")
        console.print(f"  失敗: {results['failed']}")

    else:
        console.print(f"[red]✗ 路徑不存在: {input_path}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()
