#!/usr/bin/env python3
"""
CodeGemini Context Builder 測試
測試 Smart Context Builder 功能
"""
import os
import sys
import tempfile
from pathlib import Path
from rich.console import Console

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from context.builder import (
    ContextBuilder,
    Context,
    CodeSnippet,
    FileContext,
    RelevanceLevel
)
from context.scanner import CodebaseScanner

console = Console()


def create_test_project():
    """建立測試專案"""
    temp_dir = tempfile.mkdtemp(prefix="codegemini_proj_")

    # 建立測試檔案
    test_files = {
        "main.py": """#!/usr/bin/env python3
def main():
    print("Hello, World!")
    user_login()

def user_login():
    username = input("Username: ")
    password = input("Password: ")
    return authenticate(username, password)

if __name__ == "__main__":
    main()
""",
        "auth.py": """def authenticate(username, password):
    # 驗證使用者
    if username == "admin" and password == "secret":
        return True
    return False

def get_user_profile(username):
    # 取得使用者資料
    return {"username": username, "role": "admin"}
""",
        "database.py": """class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        # 連接資料庫
        pass

    def query(self, sql):
        # 執行查詢
        pass
""",
        "utils.py": """def format_date(date):
    return date.strftime("%Y-%m-%d")

def validate_email(email):
    return "@" in email
""",
    }

    for filename, content in test_files.items():
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return temp_dir


def test_context_builder_init():
    """測試 ContextBuilder 初始化"""
    console.print("\n[bold magenta]測試 1：ContextBuilder 初始化[/bold magenta]")

    try:
        temp_dir = create_test_project()

        builder = ContextBuilder(temp_dir, token_budget=10000)
        console.print("[bright_magenta]✓ ContextBuilder 初始化成功[/green]")
        console.print(f"  專案路徑：{builder.project_path}")
        console.print(f"  Token 預算：{builder.token_budget}")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_keyword_extraction():
    """測試關鍵字提取"""
    console.print("\n[bold magenta]測試 2：關鍵字提取[/bold magenta]")

    try:
        temp_dir = create_test_project()
        builder = ContextBuilder(temp_dir)

        # 測試中文
        keywords_zh = builder._extract_keywords("新增使用者登入功能")
        assert len(keywords_zh) > 0, "未提取到關鍵字"
        console.print(f"[bright_magenta]✓ 中文關鍵字提取成功：{keywords_zh[:5]}[/green]")

        # 測試英文
        keywords_en = builder._extract_keywords("Add user authentication feature")
        assert len(keywords_en) > 0, "未提取到英文關鍵字"
        console.print(f"[bright_magenta]✓ 英文關鍵字提取成功：{keywords_en[:5]}[/green]")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_file_relevance():
    """測試檔案相關性計算"""
    console.print("\n[bold magenta]測試 3：檔案相關性計算[/bold magenta]")

    try:
        temp_dir = create_test_project()
        builder = ContextBuilder(temp_dir)

        keywords = ["user", "login", "auth"]
        task_desc = "實作使用者登入功能"

        # 計算 auth.py 的相關性（應該很高）
        score_auth = builder._calculate_file_relevance("auth.py", task_desc, keywords)
        assert score_auth > 0.5, "auth.py 相關性分數過低"
        console.print(f"[bright_magenta]✓ auth.py 相關性：{score_auth:.2f}[/green]")

        # 計算 utils.py 的相關性（應該較低）
        score_utils = builder._calculate_file_relevance("utils.py", task_desc, keywords)
        assert score_utils < score_auth, "utils.py 相關性應低於 auth.py"
        console.print(f"[bright_magenta]✓ utils.py 相關性：{score_utils:.2f}[/green]")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_file_prioritization():
    """測試檔案優先級排序"""
    console.print("\n[bold magenta]測試 4：檔案優先級排序[/bold magenta]")

    try:
        temp_dir = create_test_project()
        builder = ContextBuilder(temp_dir)

        # 掃描專案
        builder.project_context = builder.scanner.scan_project(temp_dir, max_depth=1, build_symbol_index=False)

        task_desc = "實作使用者登入功能"
        keywords = ["user", "login", "auth", "password"]

        prioritized = builder.prioritize_files(
            task_desc,
            builder.project_context.source_files,
            keywords
        )

        assert len(prioritized) > 0, "未排序任何檔案"
        console.print(f"[bright_magenta]✓ 檔案排序成功：{len(prioritized)} 個檔案[/green]")

        # 驗證 auth.py 應該排在前面
        auth_index = next((i for i, f in enumerate(prioritized) if "auth" in f), None)
        assert auth_index is not None and auth_index < len(prioritized) // 2, "auth.py 排序不正確"
        console.print(f"[bright_magenta]✓ auth.py 排序正確（第 {auth_index + 1} 位）[/green]")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_code_snippet_extraction():
    """測試程式碼片段提取"""
    console.print("\n[bold magenta]測試 5：程式碼片段提取[/bold magenta]")

    try:
        temp_dir = create_test_project()
        builder = ContextBuilder(temp_dir)

        keywords = ["authenticate", "password"]

        snippets = builder.extract_relevant_code("auth.py", keywords, max_snippets=3)

        assert len(snippets) > 0, "未提取到程式碼片段"
        console.print(f"[bright_magenta]✓ 提取到 {len(snippets)} 個程式碼片段[/green]")

        # 驗證片段內容
        for snippet in snippets:
            assert snippet.file_path == "auth.py", "檔案路徑不正確"
            assert snippet.content, "片段內容為空"
            assert snippet.start_line > 0, "起始行號無效"
            console.print(f"  - 片段：第 {snippet.start_line}-{snippet.end_line} 行，相關性：{snippet.relevance_score:.2f}")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_context_building():
    """測試完整上下文建立"""
    console.print("\n[bold magenta]測試 6：完整上下文建立[/bold magenta]")

    try:
        temp_dir = create_test_project()
        builder = ContextBuilder(temp_dir, token_budget=50000)

        task_desc = "實作使用者登入功能"

        context = builder.build_for_task(
            task_description=task_desc,
            max_files=5,
            include_tests=False
        )

        # 驗證上下文
        assert context.task_description == task_desc, "任務描述不正確"
        assert context.included_files > 0, "未包含任何檔案"
        assert context.total_tokens > 0, "未計算 token 數"
        assert context.total_tokens <= context.token_budget, "超出 token 預算"
        console.print(f"[bright_magenta]✓ 上下文建立成功[/green]")
        console.print(f"  包含檔案：{context.included_files}")
        console.print(f"  預估 tokens：{context.total_tokens:,}")
        console.print(f"  預算使用率：{context.total_tokens / context.token_budget * 100:.1f}%")

        # 驗證檔案上下文
        assert len(context.file_contexts) > 0, "檔案上下文為空"
        for fc in context.file_contexts:
            assert fc.file_path, "檔案路徑為空"
            assert fc.relevance_score >= 0, "相關性分數無效"

        console.print(f"[bright_magenta]✓ 所有驗證通過[/green]")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_context_compression():
    """測試上下文壓縮"""
    console.print("\n[bold magenta]測試 7：上下文壓縮[/bold magenta]")

    try:
        temp_dir = create_test_project()
        builder = ContextBuilder(temp_dir, token_budget=50000)

        # 建立上下文
        context = builder.build_for_task("實作使用者登入功能", max_files=10)
        original_tokens = context.total_tokens

        # 壓縮上下文
        compressed = builder.compress_context(context, target_reduction=0.5)

        assert compressed.total_tokens < original_tokens, "壓縮未減少 tokens"
        console.print(f"[bright_magenta]✓ 上下文壓縮成功[/green]")
        console.print(f"  原始：{original_tokens:,} tokens")
        console.print(f"  壓縮後：{compressed.total_tokens:,} tokens")
        console.print(f"  減少：{(1 - compressed.total_tokens / original_tokens) * 100:.0f}%")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_token_estimation():
    """測試 Token 估算"""
    console.print("\n[bold magenta]測試 8：Token 估算[/bold magenta]")

    try:
        temp_dir = create_test_project()
        builder = ContextBuilder(temp_dir)

        # 建立上下文
        context = builder.build_for_task("實作使用者登入功能", max_files=3)

        # 估算 tokens
        estimated = builder.estimate_token_usage(context)

        assert estimated > 0, "Token 估算為 0"
        assert estimated == context.total_tokens, "Token 估算不一致"
        console.print(f"[bright_magenta]✓ Token 估算成功：{estimated:,} tokens[/green]")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """執行所有測試"""
    console.print("\n" + "=" * 70)
    console.print("[bold magenta]CodeGemini Context Builder - 測試套件[/bold magenta]")
    console.print("=" * 70)

    tests = [
        ("ContextBuilder 初始化", test_context_builder_init),
        ("關鍵字提取", test_keyword_extraction),
        ("檔案相關性計算", test_file_relevance),
        ("檔案優先級排序", test_file_prioritization),
        ("程式碼片段提取", test_code_snippet_extraction),
        ("完整上下文建立", test_context_building),
        ("上下文壓縮", test_context_compression),
        ("Token 估算", test_token_estimation),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    # 測試總結
    console.print("\n" + "=" * 70)
    console.print("[bold magenta]測試總結[/bold magenta]")
    console.print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[bright_magenta]✅ 通過[/green]" if result else "[dim magenta]❌ 失敗[/red]"
        console.print(f"  {name}: {status}")

    console.print("\n" + "-" * 70)
    console.print(f"[bold]總計：{passed}/{total} 測試通過[/bold]")

    if passed == total:
        console.print("\n[bold green]🎉 所有測試通過！Context Builder 準備就緒。[/bold green]")
        return 0
    else:
        console.print(f"\n[bold yellow]⚠️  {total - passed} 個測試失敗[/bold yellow]")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
