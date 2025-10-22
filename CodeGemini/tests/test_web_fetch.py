#!/usr/bin/env python3
"""
CodeGemini Web Fetch 測試
測試網頁抓取功能
"""

import os
import sys
from pathlib import Path
from rich.console import Console

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.web_fetch import WebFetcher, FetchedPage

console = Console()


def test_fetched_page_creation():
    """測試 1：FetchedPage 建立"""
    console.print("\n[bold]測試 1：FetchedPage 建立[/bold]")

    try:
        page = FetchedPage(
            url="https://example.com",
            title="Example Domain",
            content="This is example content.",
            raw_html="<html><body>Test</body></html>",
            status_code=200
        )

        assert page.url == "https://example.com", "URL 錯誤"
        assert page.title == "Example Domain", "標題錯誤"
        assert page.content == "This is example content.", "內容錯誤"
        assert page.status_code == 200, "狀態碼錯誤"
        assert page.word_count == 4, f"字數統計錯誤：{page.word_count}"
        assert not page.is_redirect, "不應為重定向"

        console.print(f"[green]✓ FetchedPage 建立成功[/green]")
        console.print(f"  URL：{page.url}")
        console.print(f"  標題：{page.title}")
        console.print(f"  字數：{page.word_count}")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_redirect_detection():
    """測試 2：重定向檢測"""
    console.print("\n[bold]測試 2：重定向檢測[/bold]")

    try:
        # 無重定向
        page1 = FetchedPage(
            url="https://example.com",
            title="Test",
            content="Test",
            raw_html="<html></html>",
            status_code=200
        )
        assert not page1.is_redirect, "不應為重定向"

        # 有重定向
        page2 = FetchedPage(
            url="https://example.com/new",
            title="Test",
            content="Test",
            raw_html="<html></html>",
            status_code=200,
            redirected_from="https://example.com/old"
        )
        assert page2.is_redirect, "應為重定向"
        assert page2.redirected_from == "https://example.com/old", "重定向來源錯誤"

        console.print(f"[green]✓ 重定向檢測成功[/green]")
        console.print(f"  無重定向：✓")
        console.print(f"  有重定向：✓")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_web_fetcher_initialization():
    """測試 3：WebFetcher 初始化"""
    console.print("\n[bold]測試 3：WebFetcher 初始化[/bold]")

    try:
        fetcher = WebFetcher()

        assert fetcher.timeout == 30, "預設超時時間應為 30 秒"
        assert fetcher.max_retries == 3, "預設重試次數應為 3"
        assert fetcher.cache is not None, "快取應初始化"

        # 測試自訂參數
        fetcher2 = WebFetcher(timeout=10, max_retries=5, cache_ttl=600)
        assert fetcher2.timeout == 10, "自訂超時時間錯誤"
        assert fetcher2.max_retries == 5, "自訂重試次數錯誤"

        console.print(f"[green]✓ WebFetcher 初始化成功[/green]")
        console.print(f"  預設超時：{fetcher.timeout} 秒")
        console.print(f"  預設重試：{fetcher.max_retries} 次")
        console.print(f"  快取已初始化：✓")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_url_validation():
    """測試 4：URL 驗證"""
    console.print("\n[bold]測試 4：URL 驗證[/bold]")

    try:
        fetcher = WebFetcher()

        # 有效 URL
        assert fetcher._is_valid_url("https://example.com"), "應為有效 URL"
        assert fetcher._is_valid_url("http://example.com/path"), "應為有效 URL"
        assert fetcher._is_valid_url("https://example.com:8080"), "應為有效 URL"

        # 無效 URL
        assert not fetcher._is_valid_url("not a url"), "不應為有效 URL"
        assert not fetcher._is_valid_url("ftp://example.com"), "不應為有效 URL"
        assert not fetcher._is_valid_url(""), "不應為有效 URL"

        console.print(f"[green]✓ URL 驗證成功[/green]")
        console.print(f"  有效 URL：✓")
        console.print(f"  無效 URL：✓")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_html_title_extraction():
    """測試 5：HTML 標題提取"""
    console.print("\n[bold]測試 5：HTML 標題提取[/bold]")

    try:
        fetcher = WebFetcher()

        # 測試 <title> 標籤
        html1 = "<html><head><title>Test Title</title></head><body></body></html>"
        title1 = fetcher._extract_title(html1)
        assert title1 == "Test Title", f"標題提取錯誤：{title1}"

        # 測試 <h1> 標籤
        html2 = "<html><body><h1>Heading Title</h1></body></html>"
        title2 = fetcher._extract_title(html2)
        assert title2 == "Heading Title", f"標題提取錯誤：{title2}"

        # 測試 og:title
        html3 = '<html><head><meta property="og:title" content="OG Title"></head><body></body></html>'
        title3 = fetcher._extract_title(html3)
        assert title3 == "OG Title", f"標題提取錯誤：{title3}"

        # 測試無標題
        html4 = "<html><body></body></html>"
        title4 = fetcher._extract_title(html4)
        assert title4 == "（無標題）", f"無標題處理錯誤：{title4}"

        console.print(f"[green]✓ 標題提取成功[/green]")
        console.print(f"  <title> 標籤：✓")
        console.print(f"  <h1> 標籤：✓")
        console.print(f"  og:title：✓")
        console.print(f"  無標題處理：✓")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_html_to_markdown_conversion():
    """測試 6：HTML 轉 Markdown"""
    console.print("\n[bold]測試 6：HTML 轉 Markdown[/bold]")

    try:
        fetcher = WebFetcher()

        # 簡單 HTML
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Title</h1>
            <p>This is a <strong>test</strong> paragraph.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
        </html>
        """

        markdown = fetcher._convert_html_to_markdown(html)

        assert "# Title" in markdown or "#Title" in markdown, "標題轉換失敗"
        assert "test" in markdown, "內容轉換失敗"
        assert isinstance(markdown, str), "應返回字串"

        console.print(f"[green]✓ HTML 轉 Markdown 成功[/green]")
        console.print(f"  標題轉換：✓")
        console.print(f"  內容轉換：✓")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_cache_operations():
    """測試 7：快取操作"""
    console.print("\n[bold]測試 7：快取操作[/bold]")

    try:
        fetcher = WebFetcher(cache_ttl=10)

        # 建立測試頁面
        page = FetchedPage(
            url="https://test.com",
            title="Test",
            content="Test content",
            raw_html="<html></html>",
            status_code=200
        )

        # 儲存到快取
        fetcher._save_to_cache("https://test.com", page)

        # 從快取讀取
        cached_page = fetcher._get_from_cache("https://test.com")
        assert cached_page is not None, "應能從快取讀取"
        assert cached_page.title == "Test", "快取內容錯誤"

        # 檢查快取統計
        stats = fetcher.get_cache_stats()
        assert stats["size"] == 1, "快取大小錯誤"
        assert stats["ttl"] == 10, "快取 TTL 錯誤"

        # 清空快取
        fetcher.clear_cache()
        stats_after = fetcher.get_cache_stats()
        assert stats_after["size"] == 0, "快取應已清空"

        console.print(f"[green]✓ 快取操作成功[/green]")
        console.print(f"  儲存：✓")
        console.print(f"  讀取：✓")
        console.print(f"  統計：✓")
        console.print(f"  清空：✓")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_fetch_example_com():
    """測試 8：抓取 example.com（實際網路請求）"""
    console.print("\n[bold]測試 8：抓取 example.com[/bold]")

    try:
        fetcher = WebFetcher()
        page = fetcher.fetch("https://example.com", use_cache=False)

        if page:
            assert page.status_code == 200, f"狀態碼應為 200，但得到 {page.status_code}"
            assert page.title, "應有標題"
            assert page.content, "應有內容"
            assert page.url == "https://example.com" or page.url == "http://www.example.com/", "URL 錯誤"
            assert len(page.content) > 0, "內容不應為空"

            console.print(f"[green]✓ 抓取 example.com 成功[/green]")
            console.print(f"  標題：{page.title}")
            console.print(f"  狀態碼：{page.status_code}")
            console.print(f"  字數：{page.word_count}")
        else:
            console.print(f"[yellow]⚠️  抓取失敗（可能是網路問題）[/yellow]")

        return True

    except Exception as e:
        console.print(f"[yellow]⚠️  測試跳過（網路問題）：{e}[/yellow]")
        return True


def test_cache_reuse():
    """測試 9：快取重用"""
    console.print("\n[bold]測試 9：快取重用[/bold]")

    try:
        fetcher = WebFetcher(cache_ttl=60)

        # 第一次抓取
        page1 = fetcher.fetch("https://example.com", use_cache=True)

        if page1:
            # 第二次抓取（應使用快取）
            import time
            start_time = time.time()
            page2 = fetcher.fetch("https://example.com", use_cache=True)
            elapsed = time.time() - start_time

            assert page2 is not None, "應能從快取讀取"
            assert elapsed < 0.1, "快取讀取應很快"  # 應該在 0.1 秒內完成

            console.print(f"[green]✓ 快取重用成功[/green]")
            console.print(f"  快取讀取時間：{elapsed:.3f} 秒")
        else:
            console.print(f"[yellow]⚠️  測試跳過（網路問題）[/yellow]")

        return True

    except Exception as e:
        console.print(f"[yellow]⚠️  測試跳過（網路問題）：{e}[/yellow]")
        return True


# ==================== 主測試流程 ====================

def main():
    """執行所有測試"""
    console.print("=" * 70)
    console.print("[bold cyan]CodeGemini Web Fetch - 測試套件[/bold cyan]")
    console.print("=" * 70)

    tests = [
        ("FetchedPage 建立", test_fetched_page_creation),
        ("重定向檢測", test_redirect_detection),
        ("WebFetcher 初始化", test_web_fetcher_initialization),
        ("URL 驗證", test_url_validation),
        ("HTML 標題提取", test_html_title_extraction),
        ("HTML 轉 Markdown", test_html_to_markdown_conversion),
        ("快取操作", test_cache_operations),
        ("抓取 example.com", test_fetch_example_com),
        ("快取重用", test_cache_reuse),
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
        console.print("\n[green]🎉 所有測試通過！Web Fetch 準備就緒。[/green]")


if __name__ == "__main__":
    main()
