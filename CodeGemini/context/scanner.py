#!/usr/bin/env python3
"""
CodeGemini Codebase Scanner Module
程式碼庫掃描器 - 專案結構分析

此模組負責：
1. 掃描專案結構
2. 檢測程式語言和框架
3. 提取依賴關係
4. 建立符號索引
"""
import os
import json
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.tree import Tree

console = Console()


class ProjectType(Enum):
    """專案類型"""
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    JAVA = "Java"
    GO = "Go"
    RUST = "Rust"
    CPP = "C++"
    CSHARP = "C#"
    RUBY = "Ruby"
    PHP = "PHP"
    MIXED = "Mixed"      # 多語言
    UNKNOWN = "Unknown"


@dataclass
class Framework:
    """框架資訊"""
    name: str                     # 框架名稱
    version: Optional[str] = None # 版本
    confidence: float = 1.0       # 檢測信心度（0-1）


@dataclass
class Dependency:
    """依賴套件資訊"""
    name: str                     # 套件名稱
    version: Optional[str] = None # 版本
    dev_dependency: bool = False  # 是否為開發依賴


@dataclass
class Symbol:
    """符號資訊（類別、函數等）"""
    name: str                     # 符號名稱
    type: str                     # 類型：class, function, variable
    file_path: str                # 所在檔案
    line_number: int = 0          # 行號


@dataclass
class SymbolIndex:
    """符號索引"""
    classes: List[Symbol] = field(default_factory=list)
    functions: List[Symbol] = field(default_factory=list)
    variables: List[Symbol] = field(default_factory=list)


@dataclass
class ProjectContext:
    """專案上下文（完整版）"""
    project_path: str                              # 專案路徑
    project_type: ProjectType                      # 專案類型
    frameworks: List[Framework] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    file_count: int = 0                            # 檔案總數
    source_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    symbol_index: Optional[SymbolIndex] = None
    project_structure: Optional[str] = None        # 專案結構樹


class CodebaseScanner:
    """程式碼庫掃描器"""

    # 忽略的目錄
    IGNORED_DIRS = {
        '.git', '.svn', '.hg',                    # 版本控制
        '__pycache__', '.pytest_cache', '.mypy_cache',  # Python 快取
        'node_modules', '.npm',                   # Node.js
        'venv', '.venv', 'env', '.env', 'virtualenv',  # Python 虛擬環境
        'build', 'dist', 'out', 'target',        # 建置輸出
        '.idea', '.vscode', '.vs',               # IDE
        'coverage', '.coverage',                  # 測試覆蓋率
    }

    # 語言檔案擴展名映射
    LANGUAGE_EXTENSIONS = {
        ProjectType.PYTHON: {'.py', '.pyw', '.pyx'},
        ProjectType.JAVASCRIPT: {'.js', '.jsx', '.mjs', '.cjs'},
        ProjectType.TYPESCRIPT: {'.ts', '.tsx'},
        ProjectType.JAVA: {'.java'},
        ProjectType.GO: {'.go'},
        ProjectType.RUST: {'.rs'},
        ProjectType.CPP: {'.cpp', '.cc', '.cxx', '.c', '.h', '.hpp'},
        ProjectType.CSHARP: {'.cs'},
        ProjectType.RUBY: {'.rb'},
        ProjectType.PHP: {'.php'},
    }

    # 框架檢測規則（檔案名稱 → 框架）
    FRAMEWORK_MARKERS = {
        # Python
        'flask': ['app.py', 'wsgi.py'],
        'django': ['manage.py', 'settings.py'],
        'fastapi': ['main.py'],
        'pytest': ['pytest.ini', 'conftest.py'],

        # JavaScript/TypeScript
        'react': ['package.json'],  # 需檢查內容
        'vue': ['vue.config.js', 'package.json'],
        'angular': ['angular.json'],
        'next.js': ['next.config.js'],
        'express': ['package.json'],

        # 其他
        'spring': ['pom.xml', 'build.gradle'],
        'rails': ['Gemfile', 'config.ru'],
    }

    def __init__(self, cache_enabled: bool = True):
        """
        初始化掃描器

        Args:
            cache_enabled: 是否啟用快取
        """
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, ProjectContext] = {}

    def scan_project(
        self,
        project_path: str,
        max_depth: int = 10,
        build_symbol_index: bool = False
    ) -> ProjectContext:
        """
        掃描專案

        Args:
            project_path: 專案路徑
            max_depth: 最大掃描深度
            build_symbol_index: 是否建立符號索引

        Returns:
            ProjectContext: 專案上下文
        """
        if not os.path.isdir(project_path):
            raise ValueError(f"專案路徑不存在：{project_path}")

        project_path = os.path.abspath(project_path)

        # 檢查快取
        if self.cache_enabled and project_path in self._cache:
            console.print(f"[magenta]使用快取的掃描結果[/yellow]")
            return self._cache[project_path]

        console.print(f"\n[magenta]🔍 掃描專案：{project_path}[/magenta]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("掃描檔案...", total=None)

            # 步驟 1：收集檔案
            source_files, test_files, config_files = self._collect_files(
                project_path, max_depth
            )

            progress.update(task, description="檢測語言...")

            # 步驟 2：檢測語言
            project_type = self._detect_language(source_files)

            progress.update(task, description="檢測框架...")

            # 步驟 3：檢測框架
            frameworks = self._detect_frameworks(project_path, source_files, config_files)

            progress.update(task, description="提取依賴...")

            # 步驟 4：提取依賴
            dependencies = self._extract_dependencies(project_path, project_type)

            progress.update(task, description="完成", completed=100)

        # 步驟 5：建立符號索引（選用）
        symbol_index = None
        if build_symbol_index and project_type == ProjectType.PYTHON:
            console.print(f"[magenta]建立符號索引...[/magenta]")
            symbol_index = self.build_symbol_index(project_path, source_files)

        # 步驟 6：生成專案結構樹
        project_structure = self._generate_structure_tree(project_path, max_depth=3)

        # 建立專案上下文
        context = ProjectContext(
            project_path=project_path,
            project_type=project_type,
            frameworks=frameworks,
            dependencies=dependencies,
            file_count=len(source_files) + len(test_files) + len(config_files),
            source_files=source_files,
            test_files=test_files,
            config_files=config_files,
            symbol_index=symbol_index,
            project_structure=project_structure
        )

        # 快取結果
        if self.cache_enabled:
            self._cache[project_path] = context

        # 顯示摘要
        self._print_summary(context)

        return context

    def _collect_files(
        self,
        project_path: str,
        max_depth: int
    ) -> tuple[List[str], List[str], List[str]]:
        """
        收集專案檔案

        Returns:
            (source_files, test_files, config_files)
        """
        source_files = []
        test_files = []
        config_files = []

        for root, dirs, files in os.walk(project_path):
            # 計算深度
            depth = root[len(project_path):].count(os.sep)
            if depth > max_depth:
                continue

            # 忽略指定目錄
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)

                # 分類檔案
                if self._is_source_file(file):
                    if self._is_test_file(file_path):
                        test_files.append(rel_path)
                    else:
                        source_files.append(rel_path)
                elif self._is_config_file(file):
                    config_files.append(rel_path)

        return source_files, test_files, config_files

    def _is_source_file(self, filename: str) -> bool:
        """判斷是否為源碼檔案"""
        ext = os.path.splitext(filename)[1].lower()
        for extensions in self.LANGUAGE_EXTENSIONS.values():
            if ext in extensions:
                return True
        return False

    def _is_test_file(self, file_path: str) -> bool:
        """判斷是否為測試檔案"""
        file_lower = file_path.lower()
        return any([
            'test' in file_lower,
            'spec' in file_lower,
            file_lower.endswith('_test.py'),
            file_lower.endswith('.test.js'),
            file_lower.endswith('.spec.ts'),
        ])

    def _is_config_file(self, filename: str) -> bool:
        """判斷是否為配置檔案"""
        config_patterns = {
            'package.json', 'package-lock.json',
            'requirements.txt', 'Pipfile', 'pyproject.toml', 'setup.py',
            'pom.xml', 'build.gradle', 'Cargo.toml',
            '.env', '.env.example', 'config.yaml', 'config.json',
            'Dockerfile', 'docker-compose.yml',
            '.gitignore', 'README.md',
        }
        return filename in config_patterns

    def _detect_language(self, source_files: List[str]) -> ProjectType:
        """檢測專案語言"""
        if not source_files:
            return ProjectType.UNKNOWN

        # 統計各語言檔案數量
        lang_counts: Dict[ProjectType, int] = {}

        for file_path in source_files:
            ext = os.path.splitext(file_path)[1].lower()

            for lang_type, extensions in self.LANGUAGE_EXTENSIONS.items():
                if ext in extensions:
                    lang_counts[lang_type] = lang_counts.get(lang_type, 0) + 1
                    break

        if not lang_counts:
            return ProjectType.UNKNOWN

        # 取最多的語言
        primary_lang = max(lang_counts.items(), key=lambda x: x[1])

        # 檢查是否為多語言專案
        if len(lang_counts) > 1:
            secondary_count = sorted(lang_counts.values())[-2]
            if secondary_count > len(source_files) * 0.2:  # 次要語言超過 20%
                return ProjectType.MIXED

        return primary_lang[0]

    def _detect_frameworks(
        self,
        project_path: str,
        source_files: List[str],
        config_files: List[str]
    ) -> List[Framework]:
        """檢測使用的框架"""
        frameworks = []
        all_files = source_files + config_files

        # 基於檔案名稱的檢測
        for framework_name, markers in self.FRAMEWORK_MARKERS.items():
            for marker in markers:
                if any(marker in f for f in all_files):
                    # 特殊處理：package.json 需檢查內容
                    if marker == 'package.json':
                        frameworks.extend(self._detect_js_frameworks(project_path))
                    else:
                        frameworks.append(Framework(name=framework_name, confidence=0.9))
                    break

        return frameworks

    def _detect_js_frameworks(self, project_path: str) -> List[Framework]:
        """從 package.json 檢測 JavaScript 框架"""
        package_json_path = os.path.join(project_path, 'package.json')

        if not os.path.exists(package_json_path):
            return []

        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            frameworks = []
            dependencies = {**data.get('dependencies', {}), **data.get('devDependencies', {})}

            # 檢測常見框架
            framework_map = {
                'react': 'React',
                'vue': 'Vue.js',
                '@angular/core': 'Angular',
                'next': 'Next.js',
                'express': 'Express',
                'nest': 'NestJS',
            }

            for dep_name, framework_name in framework_map.items():
                if dep_name in dependencies:
                    version = dependencies[dep_name].lstrip('^~')
                    frameworks.append(Framework(
                        name=framework_name,
                        version=version,
                        confidence=1.0
                    ))

            return frameworks

        except Exception:
            return []

    def _extract_dependencies(
        self,
        project_path: str,
        project_type: ProjectType
    ) -> List[Dependency]:
        """提取依賴套件"""
        if project_type == ProjectType.PYTHON:
            return self._extract_python_dependencies(project_path)
        elif project_type in [ProjectType.JAVASCRIPT, ProjectType.TYPESCRIPT]:
            return self._extract_js_dependencies(project_path)
        else:
            return []

    def _extract_python_dependencies(self, project_path: str) -> List[Dependency]:
        """提取 Python 依賴"""
        dependencies = []

        # 檢查 requirements.txt
        req_file = os.path.join(project_path, 'requirements.txt')
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # 簡單解析（實際應使用 pkg_resources）
                            match = re.match(r'^([a-zA-Z0-9_-]+)([>=<].+)?$', line)
                            if match:
                                name = match.group(1)
                                version = match.group(2).lstrip('>=<') if match.group(2) else None
                                dependencies.append(Dependency(name=name, version=version))
            except Exception:
                pass

        return dependencies

    def _extract_js_dependencies(self, project_path: str) -> List[Dependency]:
        """提取 JavaScript/TypeScript 依賴"""
        package_json = os.path.join(project_path, 'package.json')

        if not os.path.exists(package_json):
            return []

        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            dependencies = []

            # 生產依賴
            for name, version in data.get('dependencies', {}).items():
                dependencies.append(Dependency(
                    name=name,
                    version=version.lstrip('^~'),
                    dev_dependency=False
                ))

            # 開發依賴
            for name, version in data.get('devDependencies', {}).items():
                dependencies.append(Dependency(
                    name=name,
                    version=version.lstrip('^~'),
                    dev_dependency=True
                ))

            return dependencies

        except Exception:
            return []

    def build_symbol_index(
        self,
        project_path: str,
        source_files: List[str]
    ) -> SymbolIndex:
        """
        建立符號索引（僅 Python，簡化版）

        Args:
            project_path: 專案路徑
            source_files: 源碼檔案列表

        Returns:
            SymbolIndex: 符號索引
        """
        index = SymbolIndex()

        # 僅處理 Python 檔案
        python_files = [f for f in source_files if f.endswith('.py')]

        for rel_path in python_files[:50]:  # 限制 50 個檔案避免太慢
            file_path = os.path.join(project_path, rel_path)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 簡單的正則匹配（實際應使用 AST）
                # 匹配類別
                for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                    line_no = content[:match.start()].count('\n') + 1
                    index.classes.append(Symbol(
                        name=match.group(1),
                        type='class',
                        file_path=rel_path,
                        line_number=line_no
                    ))

                # 匹配函數
                for match in re.finditer(r'^def\s+(\w+)', content, re.MULTILINE):
                    line_no = content[:match.start()].count('\n') + 1
                    index.functions.append(Symbol(
                        name=match.group(1),
                        type='function',
                        file_path=rel_path,
                        line_number=line_no
                    ))

            except Exception:
                continue

        return index

    def _generate_structure_tree(self, project_path: str, max_depth: int = 3) -> str:
        """生成專案結構樹（純文字版）"""
        lines = []
        lines.append(os.path.basename(project_path) + "/")

        def walk_dir(path: str, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return

            try:
                items = sorted(os.listdir(path))
            except PermissionError:
                return

            # 過濾忽略的目錄
            items = [item for item in items if item not in self.IGNORED_DIRS]

            for i, item in enumerate(items):
                item_path = os.path.join(path, item)
                is_last = i == len(items) - 1

                # 繪製樹狀結構
                if is_last:
                    lines.append(f"{prefix}└── {item}")
                    new_prefix = prefix + "    "
                else:
                    lines.append(f"{prefix}├── {item}")
                    new_prefix = prefix + "│   "

                # 遞迴子目錄
                if os.path.isdir(item_path):
                    walk_dir(item_path, new_prefix, depth + 1)

        walk_dir(project_path)
        return "\n".join(lines)

    def _print_summary(self, context: ProjectContext):
        """顯示掃描摘要"""
        console.print(f"\n[bold green]✅ 掃描完成[/bold green]\n")

        console.print(f"[bold magenta]專案資訊：[/bold magenta]")
        console.print(f"  專案類型：{context.project_type.value}")
        console.print(f"  檔案總數：{context.file_count}")
        console.print(f"    - 源碼：{len(context.source_files)}")
        console.print(f"    - 測試：{len(context.test_files)}")
        console.print(f"    - 配置：{len(context.config_files)}")

        if context.frameworks:
            console.print(f"\n[bold magenta]檢測到的框架：[/bold magenta]")
            for fw in context.frameworks:
                version_str = f" ({fw.version})" if fw.version else ""
                console.print(f"  - {fw.name}{version_str}")

        if context.dependencies:
            console.print(f"\n[bold magenta]依賴套件：[/bold magenta]{len(context.dependencies)} 個")

        if context.symbol_index:
            console.print(f"\n[bold magenta]符號索引：[/bold magenta]")
            console.print(f"  類別：{len(context.symbol_index.classes)}")
            console.print(f"  函數：{len(context.symbol_index.functions)}")


def main():
    """測試用主程式"""
    import sys

    if len(sys.argv) < 2:
        console.print("[magenta]用法：[/magenta]")
        console.print('  python scanner.py <專案路徑>')
        console.print("\n[magenta]範例：[/magenta]")
        console.print('  python scanner.py .')
        sys.exit(1)

    project_path = sys.argv[1]

    try:
        scanner = CodebaseScanner()
        context = scanner.scan_project(
            project_path,
            build_symbol_index=True
        )

        # 顯示專案結構樹
        if context.project_structure:
            console.print(f"\n[bold magenta]專案結構：[/bold magenta]")
            console.print(context.project_structure)

    except Exception as e:
        console.print(f"\n[dim magenta]錯誤：{e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
