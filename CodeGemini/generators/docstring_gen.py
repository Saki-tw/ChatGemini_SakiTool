#!/usr/bin/env python3
"""
CodeGemini Docstring 自動生成器
自動為 Python 函數生成符合規範的 Docstring

功能：
1. AST 解析函數簽名（參數、返回值、類型提示）
2. 使用 Gemini API 智能生成 Docstring
3. 支援 Google Style / NumPy Style / Sphinx Style
4. 符合 PEP 257 規範
5. 批次處理多個函數
"""

import ast
import re
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# 添加父目錄到路徑以導入 config_manager
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    # 簡單替代品
    class Console:
        def print(self, *args, **kwargs):
            # 移除 Rich 樣式標記
            text = ' '.join(str(arg) for arg in args)
            text = re.sub(r'\[.*?\]', '', text)
            print(text)

try:
    import google.generativeai as genai
except ImportError:
    print("Error: 需要安裝 google-generativeai 套件")
    print("執行: pip install google-generativeai")
    sys.exit(1)

console = Console()


@dataclass
class FunctionSignature:
    """函數簽名資訊"""
    name: str
    args: List[str]  # 參數名稱列表
    arg_types: Dict[str, str]  # 參數類型提示 {參數名: 類型}
    return_type: Optional[str]  # 返回值類型
    is_async: bool  # 是否為異步函數
    is_method: bool  # 是否為類方法
    class_name: Optional[str]  # 所屬類名（如果是方法）
    decorators: List[str]  # 裝飾器列表
    existing_docstring: Optional[str]  # 現有的 Docstring
    source_code: str  # 函數源碼
    lineno: int  # 行號


class FunctionAnalyzer:
    """AST 函數解析器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.source_code = None
        self.tree = None

    def load_file(self) -> bool:
        """載入並解析 Python 檔案"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.source_code = f.read()

            self.tree = ast.parse(self.source_code)
            return True
        except Exception as e:
            console.print(f"[red]✗ 無法讀取檔案 {self.file_path}: {e}[/red]")
            return False

    def extract_functions(self, include_methods: bool = True) -> List[FunctionSignature]:
        """
        提取檔案中的所有函數

        Args:
            include_methods: 是否包含類方法

        Returns:
            List[FunctionSignature]: 函數簽名列表
        """
        if not self.tree:
            return []

        functions = []

        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 判斷是否為類方法
                is_method = False
                class_name = None

                # 檢查父節點是否為 ClassDef
                for parent in ast.walk(self.tree):
                    if isinstance(parent, ast.ClassDef):
                        if node in parent.body:
                            is_method = True
                            class_name = parent.name
                            break

                # 如果不包含方法且此為方法，跳過
                if not include_methods and is_method:
                    continue

                func_sig = self._parse_function_node(node, is_method, class_name)
                functions.append(func_sig)

        return functions

    def _parse_function_node(
        self,
        node: ast.FunctionDef,
        is_method: bool = False,
        class_name: Optional[str] = None
    ) -> FunctionSignature:
        """解析單個函數節點"""

        # 提取參數
        args = []
        arg_types = {}

        for arg in node.args.args:
            # 跳過 self 和 cls
            if arg.arg in ['self', 'cls']:
                continue

            args.append(arg.arg)

            # 提取類型提示
            if arg.annotation:
                arg_types[arg.arg] = ast.unparse(arg.annotation)

        # 提取返回值類型
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        # 提取裝飾器
        decorators = [ast.unparse(dec) for dec in node.decorator_list]

        # 提取現有 Docstring
        existing_docstring = ast.get_docstring(node)

        # 提取函數源碼
        try:
            source_lines = self.source_code.splitlines()
            func_source = ast.get_source_segment(self.source_code, node)
            if not func_source:
                # 如果 get_source_segment 失敗，手動提取
                start_line = node.lineno - 1
                end_line = node.end_lineno if node.end_lineno else start_line + 1
                func_source = '\n'.join(source_lines[start_line:end_line])
        except:
            func_source = f"def {node.name}(...):\n    pass"

        is_async = isinstance(node, ast.AsyncFunctionDef)

        return FunctionSignature(
            name=node.name,
            args=args,
            arg_types=arg_types,
            return_type=return_type,
            is_async=is_async,
            is_method=is_method,
            class_name=class_name,
            decorators=decorators,
            existing_docstring=existing_docstring,
            source_code=func_source,
            lineno=node.lineno
        )


class DocstringGenerator:
    """Docstring 生成器（使用 Gemini API）"""

    def __init__(self, api_key: Optional[str] = None, style: str = 'google'):
        """
        初始化 Docstring 生成器

        Args:
            api_key: Gemini API 金鑰（如果為 None，從環境變數讀取）
            style: Docstring 風格 ('google', 'numpy', 'sphinx')
        """
        self.style = style.lower()

        # 設定 API
        if api_key:
            genai.configure(api_key=api_key)
        else:
            # 從環境變數或 config_manager 讀取
            try:
                from config_manager import load_config
                config = load_config()
                api_key = config.get('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
            except:
                pass

        # 初始化模型
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def generate(self, func_sig: FunctionSignature) -> str:
        """
        生成 Docstring

        Args:
            func_sig: 函數簽名資訊

        Returns:
            str: 生成的 Docstring
        """
        prompt = self._build_prompt(func_sig)

        try:
            response = self.model.generate_content(prompt)
            docstring = self._extract_docstring(response.text)
            return docstring
        except Exception as e:
            console.print(f"[yellow]⚠ Gemini API 錯誤: {e}[/yellow]")
            # 降級到模板生成
            return self._generate_template(func_sig)

    def _build_prompt(self, func_sig: FunctionSignature) -> str:
        """構建 Gemini Prompt"""

        style_examples = {
            'google': '''
範例（Google Style）:
"""
簡短描述（一行）。

詳細說明（可選，多行）。

Args:
    param1 (type): 參數說明
    param2 (type): 參數說明

Returns:
    type: 返回值說明

Raises:
    ErrorType: 錯誤說明

Examples:
    >>> function_name(arg1, arg2)
    result
"""
''',
            'numpy': '''
範例（NumPy Style）:
"""
簡短描述（一行）。

詳細說明（可選，多行）。

Parameters
----------
param1 : type
    參數說明
param2 : type
    參數說明

Returns
-------
type
    返回值說明

Raises
------
ErrorType
    錯誤說明

Examples
--------
>>> function_name(arg1, arg2)
result
"""
''',
            'sphinx': '''
範例（Sphinx Style）:
"""
簡短描述（一行）。

詳細說明（可選，多行）。

:param param1: 參數說明
:type param1: type
:param param2: 參數說明
:type param2: type
:returns: 返回值說明
:rtype: type
:raises ErrorType: 錯誤說明

Example:
    >>> function_name(arg1, arg2)
    result
"""
'''
        }

        # 構建參數說明
        params_info = []
        for arg in func_sig.args:
            arg_type = func_sig.arg_types.get(arg, 'Any')
            params_info.append(f"    {arg}: {arg_type}")

        params_str = "\n".join(params_info) if params_info else "    (無參數)"

        return_type_str = func_sig.return_type or "None"

        prompt = f"""
你是一位資深的 Python 開發專家。請為以下函數生成高品質的 Docstring。

函數資訊：
- 函數名稱: {func_sig.name}
- 是否異步: {'是' if func_sig.is_async else '否'}
- 是否為方法: {'是（類：' + func_sig.class_name + '）' if func_sig.is_method else '否'}
- 參數列表:
{params_str}
- 返回值類型: {return_type_str}
- 裝飾器: {', '.join(func_sig.decorators) if func_sig.decorators else '無'}

函數源碼：
```python
{func_sig.source_code}
```

要求：
1. 使用 **{self.style.upper()} 風格**
2. 符合 PEP 257 規範
3. 簡短描述精準（一行）
4. 參數說明清楚具體
5. 包含返回值說明
6. 如果有異常，列出可能的異常
7. 提供使用範例（Examples）
8. 使用繁體中文撰寫說明

{style_examples.get(self.style, style_examples['google'])}

請直接輸出 Docstring 內容（包含三引號），不要添加任何額外說明。
"""
        return prompt

    def _extract_docstring(self, response_text: str) -> str:
        """從 Gemini 回應中提取 Docstring"""
        # 移除 Markdown 程式碼區塊標記
        text = response_text.strip()

        # 移除 ```python 和 ```
        text = re.sub(r'```python\s*', '', text)
        text = re.sub(r'```\s*$', '', text)

        # **修正全形標點為半形**（避免語法錯誤）
        fullwidth_to_halfwidth = {
            '，': ',',
            '。': '.',
            '：': ':',
            '；': ';',
            '！': '!',
            '？': '?',
            '（': '(',
            '）': ')',
            '「': '"',
            '」': '"',
            '『': "'",
            '』': "'",
        }

        for fullwidth, halfwidth in fullwidth_to_halfwidth.items():
            text = text.replace(fullwidth, halfwidth)

        # 移除可能重複的三引號
        text = text.strip()
        while text.startswith('"""'):
            text = text[3:].strip()
        while text.endswith('"""'):
            text = text[:-3].strip()

        # 確保使用三引號
        text = '"""' + text + '"""'

        return text

    def _generate_template(self, func_sig: FunctionSignature) -> str:
        """生成模板 Docstring（當 API 失敗時使用）"""
        if self.style == 'google':
            return self._template_google(func_sig)
        elif self.style == 'numpy':
            return self._template_numpy(func_sig)
        elif self.style == 'sphinx':
            return self._template_sphinx(func_sig)
        else:
            return self._template_google(func_sig)

    def _template_google(self, func_sig: FunctionSignature) -> str:
        """Google Style 模板"""
        lines = ['"""', f'{func_sig.name} 函數說明。', '']

        if func_sig.args:
            lines.append('Args:')
            for arg in func_sig.args:
                arg_type = func_sig.arg_types.get(arg, 'Any')
                lines.append(f'    {arg} ({arg_type}): 參數說明')
            lines.append('')

        if func_sig.return_type and func_sig.return_type != 'None':
            lines.append('Returns:')
            lines.append(f'    {func_sig.return_type}: 返回值說明')
            lines.append('')

        lines.append('"""')
        return '\n'.join(lines)

    def _template_numpy(self, func_sig: FunctionSignature) -> str:
        """NumPy Style 模板"""
        lines = ['"""', f'{func_sig.name} 函數說明。', '']

        if func_sig.args:
            lines.append('Parameters')
            lines.append('----------')
            for arg in func_sig.args:
                arg_type = func_sig.arg_types.get(arg, 'Any')
                lines.append(f'{arg} : {arg_type}')
                lines.append('    參數說明')
            lines.append('')

        if func_sig.return_type and func_sig.return_type != 'None':
            lines.append('Returns')
            lines.append('-------')
            lines.append(f'{func_sig.return_type}')
            lines.append('    返回值說明')
            lines.append('')

        lines.append('"""')
        return '\n'.join(lines)

    def _template_sphinx(self, func_sig: FunctionSignature) -> str:
        """Sphinx Style 模板"""
        lines = ['"""', f'{func_sig.name} 函數說明。', '']

        for arg in func_sig.args:
            arg_type = func_sig.arg_types.get(arg, 'Any')
            lines.append(f':param {arg}: 參數說明')
            lines.append(f':type {arg}: {arg_type}')

        if func_sig.return_type and func_sig.return_type != 'None':
            lines.append(f':returns: 返回值說明')
            lines.append(f':rtype: {func_sig.return_type}')

        lines.append('"""')
        return '\n'.join(lines)


class DocstringInserter:
    """Docstring 插入引擎"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.backup_path = None

    def create_backup(self) -> str:
        """創建備份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_path = f"{self.file_path}.backup_docstring_{timestamp}"

        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        with open(self.backup_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return self.backup_path

    def insert_docstring(
        self,
        func_sig: FunctionSignature,
        docstring: str,
        overwrite: bool = False
    ) -> bool:
        """
        插入 Docstring 到函數定義下方

        Args:
            func_sig: 函數簽名
            docstring: 要插入的 Docstring
            overwrite: 是否覆蓋現有 Docstring

        Returns:
            bool: 是否成功插入
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 如果已有 Docstring 且不覆蓋，跳過
            if func_sig.existing_docstring and not overwrite:
                return False

            # 找到函數定義行
            target_line = func_sig.lineno - 1  # 0-indexed

            # 確定縮排層級
            func_line = lines[target_line]
            indent = len(func_line) - len(func_line.lstrip())
            inner_indent = ' ' * (indent + 4)

            # 格式化 Docstring
            docstring_lines = docstring.split('\n')
            formatted_lines = []

            for i, line in enumerate(docstring_lines):
                if i == 0:
                    # 第一行
                    formatted_lines.append(inner_indent + line + '\n')
                else:
                    # 其他行
                    formatted_lines.append(inner_indent + line + '\n')

            # 找到插入位置（函數定義的下一行）
            insert_pos = target_line + 1

            # 如果已有 Docstring，移除舊的
            if func_sig.existing_docstring:
                # 找到舊 Docstring 的結束位置
                in_docstring = False
                doc_end_line = insert_pos

                for i in range(insert_pos, len(lines)):
                    line_stripped = lines[i].strip()
                    if '"""' in line_stripped or "'''" in line_stripped:
                        if in_docstring:
                            # 找到結束引號
                            doc_end_line = i + 1
                            break
                        else:
                            # 開始引號
                            in_docstring = True

                # 刪除舊 Docstring
                del lines[insert_pos:doc_end_line]

            # 插入新 Docstring
            for line in reversed(formatted_lines):
                lines.insert(insert_pos, line)

            # 寫回檔案
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            return True

        except Exception as e:
            console.print(f"[red]✗ 插入失敗: {e}[/red]")
            return False

    def validate_syntax(self) -> Tuple[bool, Optional[str]]:
        """驗證 Python 語法"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            ast.parse(content)
            return True, None
        except SyntaxError as e:
            return False, f"line {e.lineno}: {e.msg}"

    def restore_backup(self) -> bool:
        """從備份恢復"""
        if not self.backup_path or not Path(self.backup_path).exists():
            return False

        try:
            with open(self.backup_path, 'r', encoding='utf-8') as f:
                content = f.read()

            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False


def main():
    """命令列介面"""
    import argparse

    parser = argparse.ArgumentParser(
        description='CodeGemini Docstring 自動生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('file', help='Python 檔案路徑')
    parser.add_argument(
        '--style',
        choices=['google', 'numpy', 'sphinx'],
        default='google',
        help='Docstring 風格（預設：google）'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='覆蓋現有 Docstring'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='只預覽，不實際插入'
    )
    parser.add_argument(
        '--api-key',
        help='Gemini API 金鑰（選用，預設從環境變數讀取）'
    )

    args = parser.parse_args()

    console.print("\n[bold #B565D8]📝 CodeGemini Docstring 自動生成器[/bold #B565D8]\n")

    # 1. 分析檔案
    console.print(f"[#B565D8]📂 分析檔案：{args.file}[/#B565D8]")

    analyzer = FunctionAnalyzer(args.file)
    if not analyzer.load_file():
        return 1

    functions = analyzer.extract_functions()

    if not functions:
        console.print("[yellow]⚠ 未找到任何函數[/yellow]")
        return 0

    console.print(f"[#B565D8]✓ 找到 {len(functions)} 個函數[/#B565D8]\n")

    # 2. 生成 Docstrings
    generator = DocstringGenerator(api_key=args.api_key, style=args.style)
    inserter = DocstringInserter(args.file)

    if not args.preview:
        backup = inserter.create_backup()
        console.print(f"[#B565D8]✓ 備份已創建：{Path(backup).name}[/#B565D8]\n")

    results = {
        'generated': 0,
        'skipped': 0,
        'failed': 0
    }

    for func in functions:
        console.print(f"[#B565D8]處理函數：{func.name} (line {func.lineno})[/#B565D8]")

        # 如果已有 Docstring 且不覆蓋，跳過
        if func.existing_docstring and not args.overwrite:
            console.print(f"[dim]  ⊳ 已有 Docstring，跳過[/dim]")
            results['skipped'] += 1
            continue

        # 生成 Docstring
        console.print(f"[dim]  ⊳ 使用 Gemini 生成 {args.style} 風格 Docstring...[/dim]")

        docstring = generator.generate(func)

        # 顯示預覽
        if HAS_RICH:
            syntax = Syntax(docstring, "python", theme="monokai", line_numbers=False)
            console.print(Panel(syntax, title=f"生成的 Docstring ({args.style})"))
        else:
            print(f"\n生成的 Docstring ({args.style}):")
            print("=" * 60)
            print(docstring)
            print("=" * 60)

        if args.preview:
            results['generated'] += 1
            continue

        # 插入 Docstring
        if inserter.insert_docstring(func, docstring, overwrite=args.overwrite):
            console.print("[#B565D8]  ✓ 已插入[/#B565D8]\n")
            results['generated'] += 1
        else:
            console.print("[red]  ✗ 插入失敗[/red]\n")
            results['failed'] += 1

    # 3. 驗證語法
    if not args.preview:
        console.print("[#B565D8]🔍 驗證語法...[/#B565D8]")
        syntax_ok, error_msg = inserter.validate_syntax()

        if syntax_ok:
            console.print("[#B565D8]✓ 語法驗證通過[/#B565D8]\n")
        else:
            console.print(f"[red]✗ 語法錯誤: {error_msg}[/red]")
            console.print("[yellow]⚠ 正在恢復備份...[/yellow]")
            if inserter.restore_backup():
                console.print("[#B565D8]✓ 已恢復備份[/#B565D8]\n")
            return 1

    # 4. 顯示統計
    if HAS_RICH:
        table = Table(title="執行統計")
        table.add_column("項目", style="#87CEEB")
        table.add_column("數量", style="magenta")

        table.add_row("找到函數", str(len(functions)))
        table.add_row("已生成", str(results['generated']))
        table.add_row("已跳過", str(results['skipped']))
        table.add_row("失敗", str(results['failed']))

        console.print(table)
        console.print()
    else:
        print("\n執行統計:")
        print("=" * 40)
        print(f"找到函數: {len(functions)}")
        print(f"已生成: {results['generated']}")
        print(f"已跳過: {results['skipped']}")
        print(f"失敗: {results['failed']}")
        print("=" * 40)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
