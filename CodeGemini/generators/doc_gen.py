#!/usr/bin/env python3
"""
CodeGemini Documentation Generator Module
文檔生成器 - 自動生成程式碼文檔

此模組負責：
1. 分析專案結構
2. 生成 README.md
3. 生成 API 文檔
4. 生成模組文檔
"""

import os
import ast
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console

# 重用 test_gen 的資料結構
import sys
sys.path.insert(0, str(Path(__file__).parent))
from test_gen import FunctionInfo, ClassInfo

console = Console()


@dataclass
class ModuleInfo:
    """模組資訊"""
    name: str
    path: str
    docstring: Optional[str]
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[str]


class DocumentationGenerator:
    """
    文檔生成器

    自動分析專案並生成 Markdown 文檔
    """

    def __init__(self, project_path: str):
        """
        初始化文檔生成器

        Args:
            project_path: 專案根目錄
        """
        self.project_path = Path(project_path)
        self.modules: List[ModuleInfo] = []

    def scan_project(self, exclude_dirs: Optional[List[str]] = None) -> None:
        """
        掃描專案中的 Python 檔案

        Args:
            exclude_dirs: 要排除的目錄列表
        """
        console.print(f"\n[magenta]🔍 掃描專案：{self.project_path}[/magenta]")

        if exclude_dirs is None:
            exclude_dirs = [
                '__pycache__', '.git', 'venv', '.venv',
                'node_modules', 'build', 'dist', '.pytest_cache'
            ]

        python_files = []

        for py_file in self.project_path.rglob("*.py"):
            # 檢查是否在排除目錄中
            if any(exclude in py_file.parts for exclude in exclude_dirs):
                continue

            python_files.append(py_file)

        console.print(f"[bright_magenta]✓ 發現 {len(python_files)} 個 Python 檔案[/green]")

        # 分析每個檔案
        for py_file in python_files:
            module_info = self._analyze_module(py_file)
            if module_info:
                self.modules.append(module_info)

        console.print(f"[bright_magenta]✓ 分析完成：{len(self.modules)} 個模組[/green]")

    def _analyze_module(self, file_path: Path) -> Optional[ModuleInfo]:
        """分析單個模組"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            module_docstring = ast.get_docstring(tree)
            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 只收集模組級函數
                    is_toplevel = isinstance(node, ast.FunctionDef) and \
                                  any(n == node for n in tree.body)

                    if is_toplevel:
                        func_info = self._extract_function_info(node)
                        functions.append(func_info)

                elif isinstance(node, ast.ClassDef):
                    class_info = self._extract_class_info(node)
                    classes.append(class_info)

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.unparse(node))

            relative_path = file_path.relative_to(self.project_path)
            module_name = str(relative_path).replace(os.sep, '.').replace('.py', '')

            return ModuleInfo(
                name=module_name,
                path=str(relative_path),
                docstring=module_docstring,
                functions=functions,
                classes=classes,
                imports=imports
            )

        except Exception as e:
            console.print(f"[magenta]警告：無法分析 {file_path} - {e}[/yellow]")
            return None

    def _extract_function_info(self, node: ast.FunctionDef) -> FunctionInfo:
        """提取函數資訊（從 test_gen 複製）"""
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
        """提取類別資訊（從 test_gen 複製）"""
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

    def generate_readme(self, output_path: Optional[str] = None) -> str:
        """
        生成 README.md

        Args:
            output_path: 輸出路徑（選用）

        Returns:
            str: README 內容
        """
        console.print(f"\n[magenta]📝 生成 README.md...[/magenta]")

        lines = []

        # 專案名稱
        project_name = self.project_path.name
        lines.append(f"# {project_name}")
        lines.append("")

        # 專案描述（從主模組取得）
        main_module = self._find_main_module()
        if main_module and main_module.docstring:
            lines.append("## 📖 專案說明")
            lines.append("")
            lines.append(main_module.docstring)
            lines.append("")

        # 目錄結構
        lines.append("## 📁 專案結構")
        lines.append("")
        lines.append("```")
        lines.extend(self._generate_tree_structure())
        lines.append("```")
        lines.append("")

        # 模組列表
        lines.append("## 📦 模組清單")
        lines.append("")

        for module in sorted(self.modules, key=lambda m: m.name):
            lines.append(f"### `{module.name}`")
            lines.append("")

            if module.docstring:
                first_line = module.docstring.split('\n')[0]
                lines.append(first_line)
                lines.append("")

            if module.functions:
                lines.append(f"**函數：** {len(module.functions)} 個")
            if module.classes:
                lines.append(f"**類別：** {len(module.classes)} 個")

            lines.append("")

        # 安裝說明
        lines.append("## 🚀 安裝與使用")
        lines.append("")
        lines.append("```bash")
        lines.append("# 安裝依賴")
        lines.append("pip install -r requirements.txt")
        lines.append("")
        lines.append("# 執行專案")
        lines.append("python main.py")
        lines.append("```")
        lines.append("")

        # 開發
        lines.append("## 🛠️ 開發")
        lines.append("")
        lines.append("```bash")
        lines.append("# 執行測試")
        lines.append("pytest")
        lines.append("")
        lines.append("# 程式碼檢查")
        lines.append("pylint *.py")
        lines.append("```")
        lines.append("")

        # 授權
        lines.append("## 📄 授權")
        lines.append("")
        lines.append("MIT License")
        lines.append("")

        readme_content = "\n".join(lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            console.print(f"[bright_magenta]✓ README 已儲存：{output_path}[/green]")

        return readme_content

    def generate_api_docs(self, output_path: Optional[str] = None) -> str:
        """
        生成 API 文檔

        Args:
            output_path: 輸出路徑（選用）

        Returns:
            str: API 文檔內容
        """
        console.print(f"\n[magenta]📝 生成 API 文檔...[/magenta]")

        lines = []

        # 標題
        project_name = self.project_path.name
        lines.append(f"# {project_name} API 文檔")
        lines.append("")
        lines.append("自動生成的 API 參考文檔")
        lines.append("")

        # 為每個模組生成文檔
        for module in sorted(self.modules, key=lambda m: m.name):
            lines.append(f"## 模組：`{module.name}`")
            lines.append("")

            if module.docstring:
                lines.append(module.docstring)
                lines.append("")

            # 類別文檔
            if module.classes:
                lines.append("### 類別")
                lines.append("")

                for cls in module.classes:
                    lines.extend(self._generate_class_doc(cls))
                    lines.append("")

            # 函數文檔
            if module.functions:
                lines.append("### 函數")
                lines.append("")

                for func in module.functions:
                    lines.extend(self._generate_function_doc(func))
                    lines.append("")

            lines.append("---")
            lines.append("")

        api_docs = "\n".join(lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(api_docs)
            console.print(f"[bright_magenta]✓ API 文檔已儲存：{output_path}[/green]")

        return api_docs

    def _generate_class_doc(self, cls: ClassInfo) -> List[str]:
        """生成類別文檔"""
        lines = []

        # 類別名稱
        lines.append(f"#### `class {cls.name}`")
        lines.append("")

        # 繼承關係
        if cls.base_classes:
            bases = ", ".join(cls.base_classes)
            lines.append(f"繼承自：`{bases}`")
            lines.append("")

        # 類別說明
        if cls.docstring:
            lines.append(cls.docstring)
            lines.append("")

        # 方法列表
        if cls.methods:
            lines.append("**方法：**")
            lines.append("")

            for method in cls.methods:
                if method.name.startswith('__'):
                    continue  # 跳過魔術方法

                # 方法簽名
                args_str = ", ".join(method.args)
                returns_str = f" -> {method.returns}" if method.returns else ""

                lines.append(f"- `{method.name}({args_str}){returns_str}`")

                if method.docstring:
                    first_line = method.docstring.split('\n')[0]
                    lines.append(f"  - {first_line}")

            lines.append("")

        return lines

    def _generate_function_doc(self, func: FunctionInfo) -> List[str]:
        """生成函數文檔"""
        lines = []

        # 函數簽名
        args_str = ", ".join(func.args)
        returns_str = f" -> {func.returns}" if func.returns else ""
        async_prefix = "async " if func.is_async else ""

        lines.append(f"#### `{async_prefix}def {func.name}({args_str}){returns_str}`")
        lines.append("")

        # 函數說明
        if func.docstring:
            lines.append(func.docstring)
            lines.append("")

        return lines

    def _generate_tree_structure(self) -> List[str]:
        """生成目錄樹結構"""
        lines = []

        # 簡化版：只顯示 Python 檔案
        lines.append(f"{self.project_path.name}/")

        for module in sorted(self.modules, key=lambda m: m.path):
            depth = module.path.count(os.sep)
            indent = "  " * (depth + 1)
            name = Path(module.path).name

            # 添加圖示
            if module.classes or module.functions:
                icon = "📦"
            else:
                icon = "📄"

            lines.append(f"{indent}{icon} {name}")

        return lines

    def _find_main_module(self) -> Optional[ModuleInfo]:
        """尋找主模組（通常是 __init__.py 或 main.py）"""
        for module in self.modules:
            if module.name in ['__init__', 'main', 'app']:
                return module

        # 如果沒找到，返回第一個模組
        return self.modules[0] if self.modules else None


# ==================== 命令列介面 ====================

def main():
    """文檔生成器命令列工具"""
    import sys

    console.print("\n[bold magenta]CodeGemini Documentation Generator[/bold magenta]\n")

    if len(sys.argv) < 2:
        console.print("用法：")
        console.print("  python generators/doc_gen.py <project_path> [--readme <path>] [--api <path>]")
        console.print("\n範例：")
        console.print("  python generators/doc_gen.py ./myproject")
        console.print("  python generators/doc_gen.py ./myproject --readme README.md --api API.md")
        return

    project_path = sys.argv[1]

    # 解析參數
    readme_path = None
    api_path = None

    for i, arg in enumerate(sys.argv):
        if arg == "--readme" and i + 1 < len(sys.argv):
            readme_path = sys.argv[i + 1]
        elif arg == "--api" and i + 1 < len(sys.argv):
            api_path = sys.argv[i + 1]

    # 生成文檔
    generator = DocumentationGenerator(project_path)
    generator.scan_project()

    if readme_path or not api_path:
        readme = generator.generate_readme(readme_path)
        if not readme_path:
            console.print(f"\n[magenta]README.md：[/magenta]\n")
            console.print(readme)

    if api_path:
        api_docs = generator.generate_api_docs(api_path)


if __name__ == "__main__":
    main()
