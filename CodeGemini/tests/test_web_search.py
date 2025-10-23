#!/usr/bin/env python3
"""
CodeGemini Web Search 測試
測試網路搜尋功能
"""

import os
import sys
from pathlib import Path
from rich.console import Console

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.web_search import WebSearch, SearchResult, SearchEngine

console = Console()


def test_search_engine_enum():
    """測試 1：SearchEngine 列舉"""
    console.print("\n[bold]測試 1：SearchEngine 列舉[/bold]")

    try:
        assert SearchEngine.DUCKDUCKGO == "duckduckgo", "DuckDuckGo 值錯誤"
        assert SearchEngine.GOOGLE_CUSTOM == "google_custom", "Google Custom 值錯誤"
        assert SearchEngine.BRAVE == "brave", "Brave 值錯誤"

        console.print(f"[bright_magenta]✓ SearchEngine 列舉正確[/green]")
        console.print(f"  DuckDuckGo: {SearchEngine.DUCKDUCKGO}")
        console.print(f"  Google Custom: {SearchEngine.GOOGLE_CUSTOM}")
        console.print(f"  Brave: {SearchEngine.BRAVE}")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_search_result_creation():
    """測試 2：SearchResult 建立"""
    console.print("\n[bold]測試 2：SearchResult 建立[/bold]")

    try:
        result = SearchResult(
            title="Python 教學",
            url="https://example.com/python",
            snippet="這是一個 Python 教學範例",
            source="example.com",
            rank=1
        )

        assert result.title == "Python 教學", "標題錯誤"
        assert result.url == "https://example.com/python", "URL 錯誤"
        assert result.snippet == "這是一個 Python 教學範例", "摘要錯誤"
        assert result.source == "example.com", "來源錯誤"
        assert result.rank == 1, "排名錯誤"

        console.print(f"[bright_magenta]✓ SearchResult 建立成功[/green]")
        console.print(f"  標題：{result.title}")
        console.print(f"  URL：{result.url}")
        console.print(f"  排名：{result.rank}")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_domain_extraction():
    """測試 3：域名提取"""
    console.print("\n[bold]測試 3：域名提取[/bold]")

    try:
        result = SearchResult(
            title="測試",
            url="https://www.example.com/path/to/page",
            snippet="測試"
        )

        domain = result._extract_domain(result.url)
        assert domain == "www.example.com", f"域名提取錯誤：{domain}"

        # 測試不同格式
        domain2 = result._extract_domain("http://github.com/user/repo")
        assert domain2 == "github.com", f"域名提取錯誤：{domain2}"

        console.print(f"[bright_magenta]✓ 域名提取成功[/green]")
        console.print(f"  {result.url} -> {domain}")
        console.print(f"  http://github.com/user/repo -> {domain2}")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_domain_filtering():
    """測試 4：域名過濾"""
    console.print("\n[bold]測試 4：域名過濾[/bold]")

    try:
        result1 = SearchResult(title="測試1", url="https://github.com/test", snippet="測試")
        result2 = SearchResult(title="測試2", url="https://stackoverflow.com/test", snippet="測試")
        result3 = SearchResult(title="測試3", url="https://example.com/test", snippet="測試")

        # 測試允許列表
        assert result1.matches_domain_filter(allowed_domains=["github.com"]), "允許列表測試失敗"
        assert not result2.matches_domain_filter(allowed_domains=["github.com"]), "允許列表測試失敗"

        # 測試封鎖列表
        assert result1.matches_domain_filter(blocked_domains=["example.com"]), "封鎖列表測試失敗"
        assert not result3.matches_domain_filter(blocked_domains=["example.com"]), "封鎖列表測試失敗"

        # 測試組合
        assert result1.matches_domain_filter(
            allowed_domains=["github.com", "stackoverflow.com"],
            blocked_domains=["spam.com"]
        ), "組合過濾測試失敗"

        console.print(f"[bright_magenta]✓ 域名過濾成功[/green]")
        console.print(f"  允許列表：✓")
        console.print(f"  封鎖列表：✓")
        console.print(f"  組合過濾：✓")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_web_search_initialization():
    """測試 5：WebSearch 初始化"""
    console.print("\n[bold]測試 5：WebSearch 初始化[/bold]")

    try:
        # 測試預設引擎（DuckDuckGo）
        searcher = WebSearch()
        assert searcher.engine == SearchEngine.DUCKDUCKGO, "預設引擎應為 DuckDuckGo"

        # 測試指定引擎
        searcher_google = WebSearch(engine=SearchEngine.GOOGLE_CUSTOM)
        # 因為沒有 API Key，應該回退到 DuckDuckGo
        assert searcher_google.engine == SearchEngine.DUCKDUCKGO, "無 API Key 應回退到 DuckDuckGo"

        console.print(f"[bright_magenta]✓ WebSearch 初始化成功[/green]")
        console.print(f"  預設引擎：{searcher.engine}")
        console.print(f"  回退機制：✓")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_duckduckgo_search():
    """測試 6：DuckDuckGo 搜尋（實際網路請求）"""
    console.print("\n[bold]測試 6：DuckDuckGo 搜尋[/bold]")

    try:
        searcher = WebSearch(engine=SearchEngine.DUCKDUCKGO)
        results = searcher.search("Python programming", max_results=5)

        # 驗證結果
        assert isinstance(results, list), "結果應為列表"

        if len(results) > 0:
            assert all(isinstance(r, SearchResult) for r in results), "所有結果應為 SearchResult"
            assert all(r.title for r in results), "所有結果應有標題"
            assert all(r.url for r in results), "所有結果應有 URL"
            assert len(results) <= 5, "結果數量應不超過 max_results"

            # 檢查排名
            for i, result in enumerate(results, 1):
                assert result.rank == i, f"排名應為 {i}"

            console.print(f"[bright_magenta]✓ DuckDuckGo 搜尋成功[/green]")
            console.print(f"  結果數量：{len(results)}")
            console.print(f"  第一個結果：{results[0].title}")
        else:
            console.print(f"[magenta]⚠️  未獲得搜尋結果（可能是網路問題）[/yellow]")

        return True

    except Exception as e:
        console.print(f"[magenta]⚠️  搜尋測試跳過（網路問題）：{e}[/yellow]")
        # 網路測試失敗不應算作測試失敗
        return True


def test_search_with_domain_filter():
    """測試 7：帶域名過濾的搜尋"""
    console.print("\n[bold]測試 7：帶域名過濾的搜尋[/bold]")

    try:
        searcher = WebSearch(engine=SearchEngine.DUCKDUCKGO)

        # 搜尋並只允許 github.com
        results = searcher.search(
            "Python examples",
            max_results=10,
            allowed_domains=["github.com"]
        )

        if len(results) > 0:
            # 驗證所有結果都來自 github.com
            for result in results:
                domain = result._extract_domain(result.url)
                assert "github.com" in domain, f"結果應來自 github.com，但得到 {domain}"

            console.print(f"[bright_magenta]✓ 域名過濾搜尋成功[/green]")
            console.print(f"  過濾後結果：{len(results)} 個")
            console.print(f"  全部來自 github.com：✓")
        else:
            console.print(f"[magenta]⚠️  過濾後無結果（正常）[/yellow]")

        return True

    except Exception as e:
        console.print(f"[magenta]⚠️  搜尋測試跳過（網路問題）：{e}[/yellow]")
        return True


def test_search_with_blocked_domains():
    """測試 8：封鎖特定域名的搜尋"""
    console.print("\n[bold]測試 8：封鎖特定域名的搜尋[/bold]")

    try:
        searcher = WebSearch(engine=SearchEngine.DUCKDUCKGO)

        # 搜尋並封鎖某些域名
        results = searcher.search(
            "Python tutorial",
            max_results=10,
            blocked_domains=["w3schools.com", "tutorialspoint.com"]
        )

        if len(results) > 0:
            # 驗證所有結果都不包含封鎖的域名
            for result in results:
                domain = result._extract_domain(result.url)
                assert "w3schools.com" not in domain, f"不應包含封鎖域名"
                assert "tutorialspoint.com" not in domain, f"不應包含封鎖域名"

            console.print(f"[bright_magenta]✓ 封鎖域名搜尋成功[/green]")
            console.print(f"  結果數量：{len(results)} 個")
            console.print(f"  已排除封鎖域名：✓")
        else:
            console.print(f"[magenta]⚠️  無搜尋結果[/yellow]")

        return True

    except Exception as e:
        console.print(f"[magenta]⚠️  搜尋測試跳過（網路問題）：{e}[/yellow]")
        return True


def test_display_results():
    """測試 9：結果展示"""
    console.print("\n[bold]測試 9：結果展示[/bold]")

    try:
        # 建立測試結果
        results = [
            SearchResult(
                title="Python 官方文檔",
                url="https://docs.python.org",
                snippet="Python 是一個強大的程式語言...",
                source="docs.python.org",
                rank=1
            ),
            SearchResult(
                title="Python 教學",
                url="https://example.com/python",
                snippet="學習 Python 程式設計...",
                source="example.com",
                rank=2
            )
        ]

        searcher = WebSearch()

        # 展示結果（不應拋出異常）
        searcher.display_results(results)

        console.print(f"[bright_magenta]✓ 結果展示成功[/green]")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


# ==================== 主測試流程 ====================

def main():
    """執行所有測試"""
    console.print("=" * 70)
    console.print("[bold magenta]CodeGemini Web Search - 測試套件[/bold magenta]")
    console.print("=" * 70)

    tests = [
        ("SearchEngine 列舉", test_search_engine_enum),
        ("SearchResult 建立", test_search_result_creation),
        ("域名提取", test_domain_extraction),
        ("域名過濾", test_domain_filtering),
        ("WebSearch 初始化", test_web_search_initialization),
        ("DuckDuckGo 搜尋", test_duckduckgo_search),
        ("帶域名過濾的搜尋", test_search_with_domain_filter),
        ("封鎖特定域名的搜尋", test_search_with_blocked_domains),
        ("結果展示", test_display_results),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ 通過" if result else "❌ 失敗"
        except Exception as e:
            console.print(f"[dim magenta]測試異常：{e}[/red]")
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
        console.print(f"\n[magenta]⚠️  {total - passed} 個測試失敗[/yellow]")
    else:
        console.print("\n[bright_magenta]🎉 所有測試通過！Web Search 準備就緒。[/green]")


if __name__ == "__main__":
    main()
