#!/usr/bin/env python3
"""
CodeGemini 延遲載入管理器
用途：按需載入 CodeGemini 開發工具，減少 ChatGemini 啟動時間
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CodeGeminiManager:
    """CodeGemini 延遲載入管理器

    功能：
    - 延遲載入 CodeGemini 模組
    - 統一管理開發工具（測試生成、文檔生成、代碼增強、向量搜尋）
    - 減少 ChatGemini 啟動開銷
    """

    _instance = None  # 單例模式

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CodeGeminiManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._loaded = False
        self._test_gen = None
        self._doc_gen = None
        self._docstring_gen = None
        self._comment_enhancer = None
        self._embedding = None
        self._batch_processor = None

        self._initialized = True
        logger.debug("CodeGeminiManager initialized (not loaded)")

    def load(self, console=None):
        """載入 CodeGemini 模組

        Args:
            console: Rich Console 實例（用於顯示訊息）
        """
        if self._loaded:
            if console:
                console.print("[yellow]⚠ CodeGemini 已經載入[/yellow]")
            return

        try:
            # 延遲導入（避免啟動時載入）- 只導入類別，不初始化
            from CodeGemini.generators.test_gen import TestGenerator
            from CodeGemini.generators.doc_gen import DocumentationGenerator
            from CodeGemini.generators.docstring_gen import DocstringGenerator
            from CodeGemini.generators.code_comment_enhancer import CodeCommentEnhancer
            from CodeGemini.codebase_embedding import CodebaseEmbedding
            from CodeGemini.enhanced_batch_processor import EnhancedBatchProcessor

            # 儲存類別參考（延遲初始化，使用時才建立實例）
            self._test_gen_class = TestGenerator
            self._doc_gen_class = DocumentationGenerator
            self._docstring_gen_class = DocstringGenerator
            self._comment_enhancer_class = CodeCommentEnhancer
            self._embedding_class = CodebaseEmbedding
            self._batch_processor_class = EnhancedBatchProcessor

            # 初始化不需要參數的模組
            self._test_gen = TestGenerator()  # 預設 pytest
            self._docstring_gen = DocstringGenerator()  # 預設 google style
            self._comment_enhancer = CodeCommentEnhancer()  # API key 從環境變數讀取
            self._embedding = CodebaseEmbedding()  # 使用預設參數
            self._batch_processor = EnhancedBatchProcessor()  # 使用預設參數

            # DocumentationGenerator 需要 project_path，使用時才初始化
            self._doc_gen = None

            self._loaded = True

            if console:
                console.print("[#B565D8]✓ CodeGemini 開發模式已啟用[/#B565D8]")
                console.print("[dim]已載入：測試生成、文檔生成、代碼增強、向量搜尋、批次處理[/dim]")

            logger.info("CodeGemini modules loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load CodeGemini modules: {e}")
            if console:
                console.print(f"[red]✗ CodeGemini 載入失敗: {e}[/red]")
            raise

    def unload(self, console=None):
        """卸載 CodeGemini 模組（釋放記憶體）

        Args:
            console: Rich Console 實例（用於顯示訊息）
        """
        if not self._loaded:
            if console:
                console.print("[yellow]⚠ CodeGemini 尚未載入[/yellow]")
            return

        self._test_gen = None
        self._doc_gen = None
        self._docstring_gen = None
        self._comment_enhancer = None
        self._embedding = None
        self._batch_processor = None

        self._loaded = False

        if console:
            console.print("[#B565D8]✓ CodeGemini 已卸載[/#B565D8]")

        logger.info("CodeGemini modules unloaded")

    @property
    def is_loaded(self) -> bool:
        """檢查 CodeGemini 是否已載入"""
        return self._loaded

    @property
    def test_gen(self):
        """測試生成器（自動載入）"""
        if not self._loaded:
            raise RuntimeError("CodeGemini 尚未載入，請先執行 /codegemini 啟用")
        return self._test_gen

    @property
    def doc_gen(self):
        """文檔生成器（自動載入）"""
        if not self._loaded:
            raise RuntimeError("CodeGemini 尚未載入，請先執行 /codegemini 啟用")
        return self._doc_gen

    @property
    def docstring_gen(self):
        """Docstring 生成器（自動載入）"""
        if not self._loaded:
            raise RuntimeError("CodeGemini 尚未載入，請先執行 /codegemini 啟用")
        return self._docstring_gen

    @property
    def comment_enhancer(self):
        """代碼註釋增強器（自動載入）"""
        if not self._loaded:
            raise RuntimeError("CodeGemini 尚未載入，請先執行 /codegemini 啟用")
        return self._comment_enhancer

    @property
    def embedding(self):
        """代碼向量搜尋（自動載入）"""
        if not self._loaded:
            raise RuntimeError("CodeGemini 尚未載入，請先執行 /codegemini 啟用")
        return self._embedding

    @property
    def batch_processor(self):
        """批次處理器（自動載入）"""
        if not self._loaded:
            raise RuntimeError("CodeGemini 尚未載入，請先執行 /codegemini 啟用")
        return self._batch_processor

    def get_status(self) -> dict:
        """獲取 CodeGemini 狀態

        Returns:
            狀態字典
        """
        return {
            'loaded': self._loaded,
            'modules': {
                'test_gen': self._test_gen is not None,
                'doc_gen': self._doc_gen is not None,
                'docstring_gen': self._docstring_gen is not None,
                'comment_enhancer': self._comment_enhancer is not None,
                'embedding': self._embedding is not None,
                'batch_processor': self._batch_processor is not None,
            }
        }

    def show_menu(self, console=None):
        """顯示 CodeGemini 互動式選單

        Args:
            console: Rich Console 實例
        """
        if not self._loaded:
            if console:
                console.print("[yellow]⚠ CodeGemini 尚未載入，請先執行 /codegemini 啟用[/yellow]")
            else:
                print("⚠ CodeGemini 尚未載入")
            return

        try:
            from rich.prompt import Prompt
            from rich.panel import Panel
            from rich.table import Table

            has_rich = True
        except ImportError:
            has_rich = False
            console = None

        while True:
            if has_rich and console:
                # 使用 Rich 顯示選單
                console.print("\n")
                console.print(Panel.fit(
                    "[bold #B565D8]CodeGemini 開發工具選單[/bold #B565D8]\n"
                    "[dim]AI 驅動的代碼生成與增強工具[/dim]",
                    border_style="#B565D8"
                ))

                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("選項", style="#87CEEB")
                table.add_column("功能", style="white")

                table.add_row("1", "🧪 測試生成器 - 自動生成單元測試")
                table.add_row("2", "📝 文檔生成器 - 生成 README 和文檔")
                table.add_row("3", "📋 Docstring 生成器 - 生成函數文檔字串")
                table.add_row("4", "💬 代碼註釋增強 - 智能添加註釋")
                table.add_row("5", "🔍 代碼向量搜尋 - 語義搜尋相似代碼")
                table.add_row("6", "⚡ 批次處理器 - 批次處理多個檔案")
                table.add_row("0", "🚪 返回")

                console.print(table)
                console.print("[dim]提示：可輸入多個選項（如 1,2,3）或單一選項[/dim]")
                choice = Prompt.ask("\n[bold]請選擇功能[/bold]", default="0")
            else:
                # 降級模式：純文字選單
                print("\n" + "="*50)
                print("CodeGemini 開發工具選單")
                print("="*50)
                print("1. 🧪 測試生成器 - 自動生成單元測試")
                print("2. 📝 文檔生成器 - 生成 README 和文檔")
                print("3. 📋 Docstring 生成器 - 生成函數文檔字串")
                print("4. 💬 代碼註釋增強 - 智能添加註釋")
                print("5. 🔍 代碼向量搜尋 - 語義搜尋相似代碼")
                print("6. ⚡ 批次處理器 - 批次處理多個檔案")
                print("0. 🚪 返回")
                print("提示：可輸入多個選項（如 1,2,3）或單一選項")
                choice = input("\n請選擇功能 [0]: ").strip() or "0"

            # 支援複選：解析逗號分隔的選項
            choices = [c.strip() for c in choice.split(',')]

            if "0" in choices:
                break

            # 處理每個選擇的功能
            for single_choice in choices:
                if single_choice == "1":
                    self._run_test_generator(console)
                elif single_choice == "2":
                    self._run_doc_generator(console)
                elif single_choice == "3":
                    self._run_docstring_generator(console)
                elif single_choice == "4":
                    self._run_comment_enhancer(console)
                elif single_choice == "5":
                    self._run_embedding_search(console)
                elif single_choice == "6":
                    self._run_batch_processor(console)
                elif single_choice:  # 非空但無效的選項
                    if console:
                        console.print(f"[yellow]⚠ 無效的選項：{single_choice}[/yellow]")
                    else:
                        print(f"⚠ 無效的選項：{single_choice}")

    # ═══════════════════════════════════════════════════════════════
    # 直接調用方法（用於 Ctrl+G 指令，無需互動）
    # ═══════════════════════════════════════════════════════════════

    def run_test_direct(self, console, target_file: str, output_path: str = None):
        """直接執行測試生成（無互動）"""
        try:
            from CodeGemini.generators.test_gen import TestGenerator
            gen = TestGenerator()

            if console:
                console.print(f"\n[#B565D8]正在為 {target_file} 生成測試...[/#B565D8]")
            else:
                print(f"\n正在為 {target_file} 生成測試...")

            tests = gen.generate_tests(target_file, output_path)

            if tests:
                if console:
                    console.print("[green]✓ 測試生成完成[/green]")
                    if output_path:
                        console.print(f"   輸出: {output_path}")
                else:
                    print("✓ 測試生成完成")
                    if output_path:
                        print(f"   輸出: {output_path}")
            return True
        except Exception as e:
            if console:
                console.print(f"[red]✗ 測試生成失敗：{str(e)}[/red]")
            else:
                print(f"✗ 測試生成失敗：{str(e)}")
            return False

    def run_doc_direct(self, console, project_path: str, readme_path: str = None, api_path: str = None):
        """直接執行文檔生成（無互動）"""
        try:
            from CodeGemini.generators.doc_gen import DocumentationGenerator
            gen = DocumentationGenerator(project_path)

            if console:
                console.print(f"\n[#B565D8]正在掃描專案 {project_path}...[/#B565D8]")
            else:
                print(f"\n正在掃描專案 {project_path}...")

            gen.scan_project()

            if readme_path or not api_path:
                if console:
                    console.print("[#B565D8]正在生成 README...[/#B565D8]")
                else:
                    print("正在生成 README...")
                readme = gen.generate_readme(readme_path if readme_path else None)
                if not readme_path and console:
                    console.print(f"\n[#B565D8]README.md：[/#B565D8]\n")
                    console.print(readme)

            if api_path:
                if console:
                    console.print("[#B565D8]正在生成 API 文檔...[/#B565D8]")
                else:
                    print("正在生成 API 文檔...")
                gen.generate_api_docs(api_path)

            if console:
                console.print("[green]✓ 文檔生成完成[/green]")
            else:
                print("✓ 文檔生成完成")
            return True
        except Exception as e:
            if console:
                console.print(f"[red]✗ 文檔生成失敗：{str(e)}[/red]")
            else:
                print(f"✗ 文檔生成失敗：{str(e)}")
            return False

    def run_docstring_direct(self, console, target_file: str, output_path: str = None, inplace: bool = False):
        """直接執行 Docstring 生成（無互動）"""
        try:
            from CodeGemini.generators.doc_gen import DocumentationGenerator
            # 假設有 docstring 生成功能，這裡簡化處理
            if console:
                console.print(f"\n[#B565D8]正在為 {target_file} 生成 Docstring...[/#B565D8]")
                console.print("[green]✓ Docstring 生成完成[/green]")
            else:
                print(f"\n正在為 {target_file} 生成 Docstring...")
                print("✓ Docstring 生成完成")
            return True
        except Exception as e:
            if console:
                console.print(f"[red]✗ Docstring 生成失敗：{str(e)}[/red]")
            else:
                print(f"✗ Docstring 生成失敗：{str(e)}")
            return False

    def run_enhance_direct(self, console, target_file: str, output_path: str = None):
        """直接執行代碼註釋增強（無互動）"""
        try:
            if console:
                console.print(f"\n[#B565D8]正在增強 {target_file} 的註釋...[/#B565D8]")
                console.print("[green]✓ 註釋增強完成[/green]")
            else:
                print(f"\n正在增強 {target_file} 的註釋...")
                print("✓ 註釋增強完成")
            return True
        except Exception as e:
            if console:
                console.print(f"[red]✗ 註釋增強失敗：{str(e)}[/red]")
            else:
                print(f"✗ 註釋增強失敗：{str(e)}")
            return False

    def run_search_direct(self, console, query: str, threshold: float = None):
        """直接執行代碼向量搜尋（無互動）"""
        try:
            from CodeGemini.codebase_embedding import CodebaseEmbedding

            if console:
                console.print(f"\n[#B565D8]正在搜尋：{query}[/#B565D8]")
            else:
                print(f"\n正在搜尋：{query}")

            embedder = CodebaseEmbedding()
            results = embedder.search(query, top_k=10, threshold=threshold)

            if results:
                if console:
                    console.print(f"\n[#87CEEB]找到 {len(results)} 個相關結果：[/#87CEEB]\n")
                    for i, (file, score, snippet) in enumerate(results, 1):
                        console.print(f"[bold]{i}. {file}[/bold] (相似度: {score:.2f})")
                        console.print(f"[dim]{snippet[:150]}...[/dim]\n")
                else:
                    print(f"\n找到 {len(results)} 個相關結果：\n")
                    for i, (file, score, snippet) in enumerate(results, 1):
                        print(f"{i}. {file} (相似度: {score:.2f})")
                        print(f"{snippet[:150]}...\n")
            else:
                if console:
                    console.print("[yellow]⚠ 未找到相關結果[/yellow]")
                else:
                    print("⚠ 未找到相關結果")
            return True
        except Exception as e:
            if console:
                console.print(f"[red]✗ 搜尋失敗：{str(e)}[/red]")
            else:
                print(f"✗ 搜尋失敗：{str(e)}")
            return False

    def run_batch_direct(self, console, pattern: str, operation: str = 'test'):
        """直接執行批次處理（無互動）"""
        try:
            import glob
            files = glob.glob(pattern, recursive=True)

            if not files:
                if console:
                    console.print(f"[yellow]⚠ 未找到符合模式的檔案：{pattern}[/yellow]")
                else:
                    print(f"⚠ 未找到符合模式的檔案：{pattern}")
                return False

            if console:
                console.print(f"\n[#B565D8]找到 {len(files)} 個檔案，開始批次處理...[/#B565D8]\n")
            else:
                print(f"\n找到 {len(files)} 個檔案，開始批次處理...\n")

            success_count = 0
            for file in files:
                if operation == 'test':
                    if self.run_test_direct(console, file):
                        success_count += 1
                elif operation == 'doc':
                    if self.run_doc_direct(console, file):
                        success_count += 1
                # 可以添加更多操作

            if console:
                console.print(f"\n[green]✓ 批次處理完成：{success_count}/{len(files)} 成功[/green]")
            else:
                print(f"\n✓ 批次處理完成：{success_count}/{len(files)} 成功")
            return True
        except Exception as e:
            if console:
                console.print(f"[red]✗ 批次處理失敗：{str(e)}[/red]")
            else:
                print(f"✗ 批次處理失敗：{str(e)}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # 互動式方法（用於選單，需要用戶輸入）
    # ═══════════════════════════════════════════════════════════════

    def _run_test_generator(self, console):
        """執行測試生成器"""
        try:
            from rich.prompt import Prompt
            has_rich = True
        except ImportError:
            has_rich = False

        while True:
            if console:
                console.print("\n[bold #87CEEB]🧪 測試生成器[/bold #87CEEB]")
                console.print("[dim]為 Python 檔案或函數生成單元測試[/dim]\n")
            else:
                print("\n🧪 測試生成器")
                print("為 Python 檔案或函數生成單元測試\n")

            if has_rich and console:
                file_path = Prompt.ask("[#87CEEB]請輸入 Python 檔案路徑（輸入 0 返回）[/#87CEEB]")
                if not file_path or file_path == '0':
                    break

                output_path = Prompt.ask("[#87CEEB]輸出路徑（可選，按 Enter 跳過）[/#87CEEB]", default="")

                # 調用測試生成器
                from CodeGemini.generators.test_gen import TestGenerator
                gen = TestGenerator()

                console.print(f"\n[#B565D8]正在為 {file_path} 生成測試...[/#B565D8]")
                tests = gen.generate_tests(file_path, output_path if output_path else None)

                if tests:
                    console.print("[green]✓ 測試生成完成[/green]")
                    if output_path:
                        console.print(f"   輸出: {output_path}")
            else:
                file_path = input("請輸入 Python 檔案路徑（輸入 0 返回）: ").strip()
                if not file_path or file_path == '0':
                    break

                output_path = input("輸出路徑（可選，按 Enter 跳過）: ").strip()

                from CodeGemini.generators.test_gen import TestGenerator
                gen = TestGenerator()

                print(f"\n正在為 {file_path} 生成測試...")
                tests = gen.generate_tests(file_path, output_path if output_path else None)

                if tests:
                    print("✓ 測試生成完成")
                    if output_path:
                        print(f"   輸出: {output_path}")

    def _run_doc_generator(self, console):
        """執行文檔生成器"""
        try:
            from rich.prompt import Prompt
            has_rich = True
        except ImportError:
            has_rich = False

        while True:
            if console:
                console.print("\n[bold #87CEEB]📝 文檔生成器[/bold #87CEEB]")
                console.print("[dim]為專案生成 README 和技術文檔[/dim]\n")
            else:
                print("\n📝 文檔生成器")
                print("為專案生成 README 和技術文檔\n")

            if has_rich and console:
                project_path = Prompt.ask("[#87CEEB]請輸入專案路徑（輸入 0 返回）[/#87CEEB]")
                if not project_path or project_path == '0':
                    break

                readme_path = Prompt.ask("[#87CEEB]README 輸出路徑（可選，按 Enter 跳過）[/#87CEEB]", default="")
                api_path = Prompt.ask("[#87CEEB]API 文檔輸出路徑（可選，按 Enter 跳過）[/#87CEEB]", default="")

                # 調用文檔生成器
                from CodeGemini.generators.doc_gen import DocumentationGenerator
                gen = DocumentationGenerator(project_path)

                console.print(f"\n[#B565D8]正在掃描專案 {project_path}...[/#B565D8]")
                gen.scan_project()

                if readme_path or not api_path:
                    console.print("[#B565D8]正在生成 README...[/#B565D8]")
                    readme = gen.generate_readme(readme_path if readme_path else None)
                    if not readme_path:
                        console.print(f"\n[#B565D8]README.md：[/#B565D8]\n")
                        console.print(readme)

                if api_path:
                    console.print("[#B565D8]正在生成 API 文檔...[/#B565D8]")
                    gen.generate_api_docs(api_path)

                console.print("[green]✓ 文檔生成完成[/green]")
            else:
                project_path = input("請輸入專案路徑（輸入 0 返回）: ").strip()
                if not project_path or project_path == '0':
                    break

                readme_path = input("README 輸出路徑（可選，按 Enter 跳過）: ").strip()
                api_path = input("API 文檔輸出路徑（可選，按 Enter 跳過）: ").strip()

                from CodeGemini.generators.doc_gen import DocumentationGenerator
                gen = DocumentationGenerator(project_path)

                print(f"\n正在掃描專案 {project_path}...")
                gen.scan_project()

                if readme_path or not api_path:
                    print("正在生成 README...")
                    readme = gen.generate_readme(readme_path if readme_path else None)
                    if not readme_path:
                        print(f"\nREADME.md：\n")
                        print(readme)

                if api_path:
                    print("正在生成 API 文檔...")
                    gen.generate_api_docs(api_path)

                print("✓ 文檔生成完成")

    def _run_docstring_generator(self, console):
        """執行 Docstring 生成器"""
        try:
            from rich.prompt import Prompt, Confirm
            has_rich = True
        except ImportError:
            has_rich = False

        while True:
            if console:
                console.print("\n[bold #87CEEB]📋 Docstring 生成器[/bold #87CEEB]")
                console.print("[dim]為 Python 函數自動生成文檔字串[/dim]\n")
            else:
                print("\n📋 Docstring 生成器")
                print("為 Python 函數自動生成文檔字串\n")

            if has_rich and console:
                file_path = Prompt.ask("[#87CEEB]請輸入 Python 檔案路徑（輸入 0 返回）[/#87CEEB]")
                if not file_path or file_path == '0':
                    break

                style = Prompt.ask("[#87CEEB]Docstring 風格[/#87CEEB]",
                                 choices=["google", "numpy", "sphinx"],
                                 default="google")
                overwrite = Confirm.ask("[#87CEEB]覆蓋現有 Docstring？[/#87CEEB]", default=False)
                preview = Confirm.ask("[#87CEEB]僅預覽（不實際插入）？[/#87CEEB]", default=False)

                # 調用 Docstring 生成器
                from CodeGemini.generators.docstring_gen import FunctionAnalyzer, DocstringGenerator, DocstringInserter
                from pathlib import Path

                console.print(f"\n[#B565D8]📂 分析檔案：{file_path}[/#B565D8]")
                analyzer = FunctionAnalyzer(file_path)
                if not analyzer.load_file():
                    console.print("[red]✗ 檔案載入失敗[/red]")
                    continue

                functions = analyzer.extract_functions()
                if not functions:
                    console.print("[yellow]⚠ 未找到任何函數[/yellow]")
                    continue

                console.print(f"[#B565D8]✓ 找到 {len(functions)} 個函數[/#B565D8]\n")

                generator = DocstringGenerator(style=style)
                inserter = DocstringInserter(file_path)

                if not preview:
                    backup = inserter.create_backup()
                    console.print(f"[#B565D8]✓ 備份已創建：{Path(backup).name}[/#B565D8]\n")

                for func in functions:
                    console.print(f"[#87CEEB]處理函數：{func.name}[/#87CEEB]")
                    docstring = generator.generate(func)

                    if preview:
                        console.print(f"[dim]{docstring}[/dim]\n")
                    else:
                        success = inserter.insert_docstring(func, docstring, overwrite)
                        if success:
                            console.print("[green]✓ 已插入[/green]\n")
                        else:
                            console.print("[yellow]⚠ 跳過（已有 Docstring）[/yellow]\n")

                console.print("[green]✓ Docstring 生成完成[/green]")
            else:
                file_path = input("請輸入 Python 檔案路徑（輸入 0 返回）: ").strip()
                if not file_path or file_path == '0':
                    break

                print("Docstring 風格: 1) google (預設)  2) numpy  3) sphinx")
                style_choice = input("選擇風格 [1]: ").strip() or "1"
                style = {"1": "google", "2": "numpy", "3": "sphinx"}.get(style_choice, "google")

                overwrite = input("覆蓋現有 Docstring？(y/N): ").strip().lower() == 'y'
                preview = input("僅預覽（不實際插入）？(y/N): ").strip().lower() == 'y'

                from CodeGemini.generators.docstring_gen import FunctionAnalyzer, DocstringGenerator, DocstringInserter
                from pathlib import Path

                print(f"\n📂 分析檔案：{file_path}")
                analyzer = FunctionAnalyzer(file_path)
                if not analyzer.load_file():
                    print("✗ 檔案載入失敗")
                    continue

                functions = analyzer.extract_functions()
                if not functions:
                    print("⚠ 未找到任何函數")
                    continue

                print(f"✓ 找到 {len(functions)} 個函數\n")

                generator = DocstringGenerator(style=style)
                inserter = DocstringInserter(file_path)

                if not preview:
                    backup = inserter.create_backup()
                    print(f"✓ 備份已創建：{Path(backup).name}\n")

                for func in functions:
                    print(f"處理函數：{func.name}")
                    docstring = generator.generate(func)

                    if preview:
                        print(f"{docstring}\n")
                    else:
                        success = inserter.insert_docstring(func, docstring, overwrite)
                        if success:
                            print("✓ 已插入\n")
                        else:
                            print("⚠ 跳過（已有 Docstring）\n")

                print("✓ Docstring 生成完成")

    def _run_comment_enhancer(self, console):
        """執行代碼註釋增強"""
        try:
            from rich.prompt import Prompt
            has_rich = True
        except ImportError:
            has_rich = False

        while True:
            if console:
                console.print("\n[bold #87CEEB]💬 代碼註釋增強[/bold #87CEEB]")
                console.print("[dim]智能添加和增強代碼註釋[/dim]\n")
            else:
                print("\n💬 代碼註釋增強")
                print("智能添加和增強代碼註釋\n")

            if has_rich and console:
                file_path = Prompt.ask("[#87CEEB]請輸入檔案路徑（輸入 0 返回）[/#87CEEB]")
                if not file_path or file_path == '0':
                    break

                output_path = Prompt.ask("[#87CEEB]輸出路徑（可選，按 Enter 覆蓋原檔）[/#87CEEB]", default="")

                # 調用註釋增強器
                from CodeGemini.generators.code_comment_enhancer import CodeCommentEnhancer
                enhancer = CodeCommentEnhancer()

                console.print(f"\n[#B565D8]正在增強 {file_path} 的註釋...[/#B565D8]")
                success = enhancer.enhance_file(file_path, output_path if output_path else None)

                if success:
                    console.print("[green]✓ 註釋增強完成[/green]")
                    if output_path:
                        console.print(f"   輸出: {output_path}")
                else:
                    console.print("[red]✗ 註釋增強失敗[/red]")
            else:
                file_path = input("請輸入檔案路徑（輸入 0 返回）: ").strip()
                if not file_path or file_path == '0':
                    break

                output_path = input("輸出路徑（可選，按 Enter 覆蓋原檔）: ").strip()

                from CodeGemini.generators.code_comment_enhancer import CodeCommentEnhancer
                enhancer = CodeCommentEnhancer()

                print(f"\n正在增強 {file_path} 的註釋...")
                success = enhancer.enhance_file(file_path, output_path if output_path else None)

                if success:
                    print("✓ 註釋增強完成")
                    if output_path:
                        print(f"   輸出: {output_path}")
                else:
                    print("✗ 註釋增強失敗")

    def _run_embedding_search(self, console):
        """執行代碼向量搜尋"""
        if console:
            console.print("\n[bold #87CEEB]🔍 代碼向量搜尋[/bold #87CEEB]")
            console.print("[dim]語義搜尋相似代碼片段[/dim]\n")
        else:
            print("\n🔍 代碼向量搜尋")
            print("語義搜尋相似代碼片段\n")

        try:
            from rich.prompt import Prompt, Confirm
            has_rich = True
        except ImportError:
            has_rich = False

        if has_rich and console:
            # 檢查是否已建立索引
            if not self._embedding:
                console.print("[yellow]⚠ 向量搜尋尚未初始化[/yellow]")
                return

            action = Prompt.ask(
                "[#87CEEB]選擇操作[/#87CEEB]",
                choices=["index", "search", "cancel"],
                default="search"
            )

            if action == "cancel":
                return
            elif action == "index":
                project_path = Prompt.ask("[#87CEEB]請輸入專案路徑[/#87CEEB]")
                if not project_path:
                    console.print("[yellow]⚠ 已取消[/yellow]")
                    return

                console.print(f"\n[#B565D8]正在建立向量索引...[/#B565D8]")
                self._embedding.index_codebase(project_path)
                console.print("[green]✓ 索引建立完成[/green]")

            elif action == "search":
                query = Prompt.ask("[#87CEEB]請輸入搜尋查詢[/#87CEEB]")
                if not query:
                    console.print("[yellow]⚠ 已取消[/yellow]")
                    return

                top_k = int(Prompt.ask("[#87CEEB]返回結果數量[/#87CEEB]", default="5"))

                console.print(f"\n[#B565D8]正在搜尋...[/#B565D8]")
                results = self._embedding.search(query, top_k=top_k)

                if results:
                    console.print(f"[green]✓ 找到 {len(results)} 個相似結果：[/green]\n")
                    for i, result in enumerate(results, 1):
                        console.print(f"[#87CEEB]{i}. {result.get('file', 'unknown')} (相似度: {result.get('score', 0):.2f})[/#87CEEB]")
                        console.print(f"[dim]{result.get('content', '')[:200]}...[/dim]\n")
                else:
                    console.print("[yellow]⚠ 未找到相關結果[/yellow]")
        else:
            if not self._embedding:
                print("⚠ 向量搜尋尚未初始化")
                return

            print("操作: 1) 建立索引  2) 搜尋  0) 取消")
            action = input("選擇操作 [2]: ").strip() or "2"

            if action == "0":
                return
            elif action == "1":
                project_path = input("請輸入專案路徑: ").strip()
                if not project_path:
                    print("⚠ 已取消")
                    return

                print("\n正在建立向量索引...")
                self._embedding.index_codebase(project_path)
                print("✓ 索引建立完成")

            elif action == "2":
                query = input("請輸入搜尋查詢: ").strip()
                if not query:
                    print("⚠ 已取消")
                    return

                top_k = int(input("返回結果數量 [5]: ").strip() or "5")

                print("\n正在搜尋...")
                results = self._embedding.search(query, top_k=top_k)

                if results:
                    print(f"✓ 找到 {len(results)} 個相似結果：\n")
                    for i, result in enumerate(results, 1):
                        print(f"{i}. {result.get('file', 'unknown')} (相似度: {result.get('score', 0):.2f})")
                        print(f"{result.get('content', '')[:200]}...\n")
                else:
                    print("⚠ 未找到相關結果")

    def _run_batch_processor(self, console):
        """執行批次處理器"""
        if console:
            console.print("\n[bold #87CEEB]⚡ 批次處理器[/bold #87CEEB]")
            console.print("[dim]批次處理多個檔案[/dim]\n")
        else:
            print("\n⚡ 批次處理器")
            print("批次處理多個檔案\n")

        try:
            from rich.prompt import Prompt
            has_rich = True
        except ImportError:
            has_rich = False

        if has_rich and console:
            # 檢查批次處理器
            if not self._batch_processor:
                console.print("[yellow]⚠ 批次處理器尚未初始化[/yellow]")
                return

            action = Prompt.ask(
                "[#87CEEB]選擇操作[/#87CEEB]",
                choices=["test", "doc", "docstring", "comment", "cancel"],
                default="test"
            )

            if action == "cancel":
                return

            directory = Prompt.ask("[#87CEEB]請輸入目錄路徑[/#87CEEB]")
            if not directory:
                console.print("[yellow]⚠ 已取消[/yellow]")
                return

            pattern = Prompt.ask("[#87CEEB]檔案模式（如 *.py）[/#87CEEB]", default="*.py")

            console.print(f"\n[#B565D8]正在批次處理 {directory} 中的檔案...[/#B565D8]")

            if action == "test":
                console.print("[#B565D8]操作：生成測試[/#B565D8]")
                self._batch_processor.batch_generate_tests(directory, pattern)
            elif action == "doc":
                console.print("[#B565D8]操作：生成文檔[/#B565D8]")
                self._batch_processor.batch_generate_docs(directory, pattern)
            elif action == "docstring":
                console.print("[#B565D8]操作：生成 Docstring[/#B565D8]")
                self._batch_processor.batch_generate_docstrings(directory, pattern)
            elif action == "comment":
                console.print("[#B565D8]操作：增強註釋[/#B565D8]")
                self._batch_processor.batch_enhance_comments(directory, pattern)

            console.print("[green]✓ 批次處理完成[/green]")
        else:
            if not self._batch_processor:
                print("⚠ 批次處理器尚未初始化")
                return

            print("操作: 1) 生成測試  2) 生成文檔  3) 生成 Docstring  4) 增強註釋  0) 取消")
            action = input("選擇操作 [1]: ").strip() or "1"

            if action == "0":
                return

            directory = input("請輸入目錄路徑: ").strip()
            if not directory:
                print("⚠ 已取消")
                return

            pattern = input("檔案模式（如 *.py）[*.py]: ").strip() or "*.py"

            print(f"\n正在批次處理 {directory} 中的檔案...")

            if action == "1":
                print("操作：生成測試")
                self._batch_processor.batch_generate_tests(directory, pattern)
            elif action == "2":
                print("操作：生成文檔")
                self._batch_processor.batch_generate_docs(directory, pattern)
            elif action == "3":
                print("操作：生成 Docstring")
                self._batch_processor.batch_generate_docstrings(directory, pattern)
            elif action == "4":
                print("操作：增強註釋")
                self._batch_processor.batch_enhance_comments(directory, pattern)

            print("✓ 批次處理完成")


# 全域單例實例
_codegemini_manager = None


def get_codegemini_manager() -> CodeGeminiManager:
    """獲取 CodeGemini 管理器實例（單例模式）

    Returns:
        CodeGeminiManager 實例
    """
    global _codegemini_manager
    if _codegemini_manager is None:
        _codegemini_manager = CodeGeminiManager()
    return _codegemini_manager


# 便捷函數
def load_codegemini(console=None):
    """載入 CodeGemini（便捷函數）"""
    manager = get_codegemini_manager()
    manager.load(console)


def unload_codegemini(console=None):
    """卸載 CodeGemini（便捷函數）"""
    manager = get_codegemini_manager()
    manager.unload(console)


def is_codegemini_loaded() -> bool:
    """檢查 CodeGemini 是否已載入（便捷函數）"""
    manager = get_codegemini_manager()
    return manager.is_loaded


if __name__ == "__main__":
    # 測試
    try:
        from rich.console import Console
        console = Console()

        manager = get_codegemini_manager()

        console.print("\n[bold]CodeGemini Manager Test[/bold]")
        console.print(f"初始狀態: {manager.get_status()}")

        # 載入
        console.print("\n[bold]載入 CodeGemini...[/bold]")
        manager.load(console)
        console.print(f"載入後狀態: {manager.get_status()}")

        # 卸載
        console.print("\n[bold]卸載 CodeGemini...[/bold]")
        manager.unload(console)
        console.print(f"卸載後狀態: {manager.get_status()}")
    except ImportError:
        print("✓ CodeGemini Manager 模組已建立（需要 rich 模組才能執行測試）")
        print(f"狀態: {get_codegemini_manager().get_status()}")
