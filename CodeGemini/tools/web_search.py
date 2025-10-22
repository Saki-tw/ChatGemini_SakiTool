#!/usr/bin/env python3
"""
CodeGemini Web Search Module
網路搜尋工具 - 提供網路搜尋功能

此模組負責：
1. 多搜尋引擎支援（DuckDuckGo, Google Custom Search）
2. 域名過濾（允許/封鎖特定網域）
3. 搜尋結果格式化
4. 結果排序與限制
"""

import os
import re
import json
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from rich.console import Console

console = Console()


class SearchEngine(str, Enum):
    """搜尋引擎類型"""
    DUCKDUCKGO = "duckduckgo"
    GOOGLE_CUSTOM = "google_custom"
    BRAVE = "brave"


@dataclass
class SearchResult:
    """搜尋結果"""
    title: str
    url: str
    snippet: str
    source: str = ""  # 來源網域
    rank: int = 0  # 排名
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches_domain_filter(
        self,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None
    ) -> bool:
        """檢查是否符合域名過濾條件"""
        domain = self._extract_domain(self.url)

        # 檢查封鎖列表
        if blocked_domains and any(blocked in domain for blocked in blocked_domains):
            return False

        # 檢查允許列表
        if allowed_domains and not any(allowed in domain for allowed in allowed_domains):
            return False

        return True

    def _extract_domain(self, url: str) -> str:
        """從 URL 提取域名"""
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else ""


class WebSearch:
    """
    網路搜尋工具

    支援多個搜尋引擎：
    - DuckDuckGo（預設，免費）
    - Google Custom Search（需要 API Key）
    - Brave Search（需要 API Key）
    """

    def __init__(
        self,
        engine: SearchEngine = SearchEngine.DUCKDUCKGO,
        api_key: Optional[str] = None,
        cx_id: Optional[str] = None,  # Google Custom Search Engine ID
        pricing_tracker: Optional[Any] = None  # PricingDisplay instance
    ):
        """
        初始化搜尋工具

        Args:
            engine: 搜尋引擎類型
            api_key: API 金鑰（Google/Brave 需要）
            cx_id: Google Custom Search Engine ID
            pricing_tracker: PricingDisplay 實例（用於追蹤成本）
        """
        self.engine = engine
        self.api_key = api_key or os.getenv("SEARCH_API_KEY")
        self.cx_id = cx_id or os.getenv("GOOGLE_CSE_ID")
        self.pricing_tracker = pricing_tracker

        # 驗證設定
        if engine == SearchEngine.GOOGLE_CUSTOM:
            if not self.api_key or not self.cx_id:
                console.print("[yellow]⚠️  Google Custom Search 需要 API Key 和 CSE ID[/yellow]")
                console.print("[yellow]   回退到 DuckDuckGo[/yellow]")
                self.engine = SearchEngine.DUCKDUCKGO

        elif engine == SearchEngine.BRAVE:
            if not self.api_key:
                console.print("[yellow]⚠️  Brave Search 需要 API Key[/yellow]")
                console.print("[yellow]   回退到 DuckDuckGo[/yellow]")
                self.engine = SearchEngine.DUCKDUCKGO

    def search(
        self,
        query: str,
        max_results: int = 10,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        safe_search: bool = True
    ) -> List[SearchResult]:
        """
        執行搜尋

        Args:
            query: 搜尋關鍵字
            max_results: 最大結果數量
            allowed_domains: 允許的域名列表
            blocked_domains: 封鎖的域名列表
            safe_search: 安全搜尋

        Returns:
            List[SearchResult]: 搜尋結果列表
        """
        console.print(f"\n[cyan]🔍 搜尋：{query}[/cyan]")
        console.print(f"[dim]搜尋引擎：{self.engine.value}[/dim]")

        try:
            # 根據引擎類型執行搜尋
            if self.engine == SearchEngine.GOOGLE_CUSTOM:
                results = self._search_google_custom(query, max_results, safe_search)
            elif self.engine == SearchEngine.BRAVE:
                results = self._search_brave(query, max_results, safe_search)
            else:  # DUCKDUCKGO
                results = self._search_duckduckgo(query, max_results, safe_search)

            # 應用域名過濾
            if allowed_domains or blocked_domains:
                results = [
                    r for r in results
                    if r.matches_domain_filter(allowed_domains, blocked_domains)
                ]

            # 限制結果數量
            results = results[:max_results]

            # 設置排名
            for i, result in enumerate(results, 1):
                result.rank = i

            # 追蹤 API 使用（如果有 pricing_tracker）
            if self.pricing_tracker and hasattr(self.pricing_tracker, 'track_search_usage'):
                engine_key = {
                    SearchEngine.GOOGLE_CUSTOM: 'google_custom_search',
                    SearchEngine.BRAVE: 'brave_search',
                    SearchEngine.DUCKDUCKGO: 'duckduckgo'
                }.get(self.engine, 'duckduckgo')

                self.pricing_tracker.track_search_usage(engine_key, query_count=1)

            console.print(f"[green]✓ 找到 {len(results)} 個結果[/green]")

            return results

        except Exception as e:
            console.print(f"[red]✗ 搜尋失敗：{e}[/red]")
            return []

    def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        safe_search: bool
    ) -> List[SearchResult]:
        """使用 DuckDuckGo 搜尋（HTML 解析方式）"""
        try:
            # DuckDuckGo HTML 搜尋 URL
            url = "https://html.duckduckgo.com/html/"

            params = {
                "q": query,
                "kl": "tw-tzh"  # 台灣繁體中文
            }

            if safe_search:
                params["kp"] = "1"  # 嚴格安全搜尋

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }

            response = requests.post(url, data=params, headers=headers, timeout=10)
            response.raise_for_status()

            # 解析 HTML 結果
            results = self._parse_duckduckgo_html(response.text)

            return results[:max_results]

        except Exception as e:
            console.print(f"[yellow]⚠️  DuckDuckGo 搜尋錯誤：{e}[/yellow]")
            return []

    def _parse_duckduckgo_html(self, html: str) -> List[SearchResult]:
        """解析 DuckDuckGo HTML 結果"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # 尋找結果區塊
        result_divs = soup.find_all('div', class_='result')

        for div in result_divs:
            try:
                # 提取標題和 URL
                title_tag = div.find('a', class_='result__a')
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                url = title_tag.get('href', '')

                # 提取摘要
                snippet_tag = div.find('a', class_='result__snippet')
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                # 提取來源
                source_tag = div.find('a', class_='result__url')
                source = source_tag.get_text(strip=True) if source_tag else ""

                if title and url:
                    result = SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source=source,
                        metadata={"engine": "duckduckgo"}
                    )
                    results.append(result)

            except Exception as e:
                console.print(f"[dim]解析結果時出錯：{e}[/dim]")
                continue

        return results

    def _search_google_custom(
        self,
        query: str,
        max_results: int,
        safe_search: bool
    ) -> List[SearchResult]:
        """使用 Google Custom Search API"""
        try:
            url = "https://www.googleapis.com/customsearch/v1"

            params = {
                "key": self.api_key,
                "cx": self.cx_id,
                "q": query,
                "num": min(max_results, 10)  # Google API 限制 10
            }

            if safe_search:
                params["safe"] = "active"

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get("items", []):
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=item.get("displayLink", ""),
                    metadata={
                        "engine": "google_custom",
                        "kind": item.get("kind", "")
                    }
                )
                results.append(result)

            return results

        except Exception as e:
            console.print(f"[yellow]⚠️  Google Custom Search 錯誤：{e}[/yellow]")
            return []

    def _search_brave(
        self,
        query: str,
        max_results: int,
        safe_search: bool
    ) -> List[SearchResult]:
        """使用 Brave Search API"""
        try:
            url = "https://api.search.brave.com/res/v1/web/search"

            params = {
                "q": query,
                "count": max_results
            }

            if safe_search:
                params["safesearch"] = "strict"

            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get("web", {}).get("results", []):
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source=item.get("display_url", ""),
                    metadata={
                        "engine": "brave",
                        "age": item.get("age", "")
                    }
                )
                results.append(result)

            return results

        except Exception as e:
            console.print(f"[yellow]⚠️  Brave Search 錯誤：{e}[/yellow]")
            return []

    def display_results(self, results: List[SearchResult]) -> None:
        """展示搜尋結果"""
        if not results:
            console.print("[yellow]⚠️  無搜尋結果[/yellow]")
            return

        console.print(f"\n[bold]🔍 搜尋結果（{len(results)} 個）[/bold]\n")

        for result in results:
            console.print(f"[bold cyan]{result.rank}. {result.title}[/bold cyan]")
            console.print(f"   [blue]{result.url}[/blue]")
            if result.snippet:
                # 限制摘要長度
                snippet = result.snippet[:200] + "..." if len(result.snippet) > 200 else result.snippet
                console.print(f"   {snippet}")
            console.print()


# ==================== 命令列介面 ====================

def main():
    """Web Search 命令列工具"""
    import sys

    console.print("\n[bold cyan]CodeGemini Web Search Tool[/bold cyan]\n")

    if len(sys.argv) < 2:
        console.print("用法：")
        console.print("  python tools/web_search.py <query> [--engine <engine>] [--max <num>]")
        console.print("\n搜尋引擎：")
        console.print("  duckduckgo  - DuckDuckGo（預設，免費）")
        console.print("  google      - Google Custom Search（需要 API Key）")
        console.print("  brave       - Brave Search（需要 API Key）")
        console.print("\n範例：")
        console.print("  python tools/web_search.py 'Python 教學'")
        console.print("  python tools/web_search.py 'Gemini API' --engine google --max 5")
        return

    query = sys.argv[1]
    engine = SearchEngine.DUCKDUCKGO
    max_results = 10

    # 解析參數
    for i, arg in enumerate(sys.argv):
        if arg == "--engine" and i + 1 < len(sys.argv):
            engine_str = sys.argv[i + 1].lower()
            if engine_str == "google":
                engine = SearchEngine.GOOGLE_CUSTOM
            elif engine_str == "brave":
                engine = SearchEngine.BRAVE
        elif arg == "--max" and i + 1 < len(sys.argv):
            max_results = int(sys.argv[i + 1])

    # 執行搜尋
    searcher = WebSearch(engine=engine)
    results = searcher.search(query, max_results=max_results)
    searcher.display_results(results)


if __name__ == "__main__":
    main()
