#!/usr/bin/env python3
"""

# i18n support
import sys
from pathlib import Path

# 確保可以 import utils
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.i18n import safe_t
CodeGemini Web Fetch Module
網頁抓取工具 - 提供網頁內容抓取功能

此模組負責：
1. 抓取 URL 內容
2. HTML → Markdown 轉換
3. Redirect 處理
4. 快取管理（15 分鐘自清理）
"""

import os
import re
import time
import hashlib
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from cachetools import TTLCache
from rich.console import Console
import html2text

console = Console()


@dataclass
class FetchedPage:
    """抓取的網頁"""
    url: str
    title: str
    content: str  # Markdown 格式
    raw_html: str
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    redirected_from: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        """字數統計"""
        return len(self.content.split())

    @property
    def is_redirect(self) -> bool:
        """是否為重定向"""
        return self.redirected_from is not None


class WebFetcher:
    """
    網頁抓取工具

    功能：
    - 抓取網頁內容並轉換為 Markdown
    - 處理 HTTP 重定向
    - 自動快取（15 分鐘 TTL）
    - 安全檢查與錯誤處理
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        cache_ttl: int = 900,  # 15 分鐘 = 900 秒
        user_agent: Optional[str] = None
    ):
        """
        初始化網頁抓取工具

        Args:
            timeout: 請求超時時間（秒）
            max_retries: 最大重試次數
            cache_ttl: 快取生存時間（秒）
            user_agent: 自訂 User-Agent
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # 初始化快取（TTL Cache，15 分鐘自動清理）
        self.cache = TTLCache(maxsize=100, ttl=cache_ttl)

        # 初始化 HTML 轉 Markdown 轉換器
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # 不換行
        self.html_converter.unicode_snob = True  # Unicode 支援
        self.html_converter.ignore_emphasis = False

        console.print(f"[dim]{safe_t('web_fetch.fetcher_initialized', 'WebFetcher 初始化完成')}（{safe_t('web_fetch.cache_ttl', '快取 TTL')}: {cache_ttl}{safe_t('common.seconds', '秒')}）[/dim]")

    def fetch(
        self,
        url: str,
        use_cache: bool = True,
        follow_redirects: bool = True
    ) -> Optional[FetchedPage]:
        """
        抓取網頁

        Args:
            url: 目標 URL
            use_cache: 是否使用快取
            follow_redirects: 是否追蹤重定向

        Returns:
            Optional[FetchedPage]: 抓取的網頁，失敗返回 None
        """
        console.print(f"\n[#B565D8]🌐 {safe_t('web_fetch.fetching', '抓取網頁')}：{url}[/#B565D8]")

        # 檢查快取
        if use_cache:
            cached_page = self._get_from_cache(url)
            if cached_page:
                console.print(f"[#B565D8]✓ {safe_t('web_fetch.from_cache', '從快取讀取')}[/#B565D8]")
                return cached_page

        # 驗證 URL
        if not self._is_valid_url(url):
            console.print(f"[dim #B565D8]✗ {safe_t('web_fetch.invalid_url', '無效的 URL')}：{url}[/red]")
            return None

        # 執行抓取
        try:
            response = self._make_request(url, follow_redirects)

            if response is None:
                return None

            # 檢查狀態碼
            if response.status_code != 200:
                console.print(f"[#B565D8]⚠️  HTTP {response.status_code}[/#B565D8]")

            # 提取重定向資訊
            redirected_from = None
            if response.history:
                redirected_from = response.history[0].url
                console.print(f"[#B565D8]↪️  {safe_t('web_fetch.redirected_from', '重定向自')}：{redirected_from}[/#B565D8]")

            # 轉換 HTML 為 Markdown
            html_content = response.text
            markdown_content = self._convert_html_to_markdown(html_content)

            # 提取標題
            title = self._extract_title(html_content)

            # 建立 FetchedPage
            page = FetchedPage(
                url=response.url,
                title=title,
                content=markdown_content,
                raw_html=html_content,
                status_code=response.status_code,
                headers=dict(response.headers),
                redirected_from=redirected_from,
                metadata={
                    "content_type": response.headers.get("Content-Type", ""),
                    "encoding": response.encoding
                }
            )

            # 儲存到快取
            if use_cache:
                self._save_to_cache(url, page)

            console.print(f"[#B565D8]✓ {safe_t('web_fetch.fetch_success', '抓取成功')}[/#B565D8]")
            console.print(f"  {safe_t('web_fetch.title', '標題')}：{title}")
            console.print(f"  {safe_t('web_fetch.word_count', '字數')}：{page.word_count}")

            return page

        except Exception as e:
            console.print(f"[dim #B565D8]✗ {safe_t('web_fetch.fetch_failed', '抓取失敗')}：{e}[/red]")
            return None

    def _make_request(
        self,
        url: str,
        follow_redirects: bool
    ) -> Optional[requests.Response]:
        """發送 HTTP 請求"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=follow_redirects
                )

                return response

            except requests.exceptions.Timeout:
                console.print(f"[#B565D8]⚠️  {safe_t('web_fetch.request_timeout', '請求超時')}（{safe_t('web_fetch.attempt', '嘗試')} {attempt + 1}/{self.max_retries}）[/#B565D8]")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                    continue
                else:
                    return None

            except requests.exceptions.RequestException as e:
                console.print(f"[dim #B565D8]✗ {safe_t('web_fetch.request_error', '請求錯誤')}：{e}[/red]")
                return None

        return None

    def _convert_html_to_markdown(self, html: str) -> str:
        """將 HTML 轉換為 Markdown"""
        try:
            # 清理 HTML
            html = self._clean_html(html)

            # 轉換為 Markdown
            markdown = self.html_converter.handle(html)

            # 後處理
            markdown = self._post_process_markdown(markdown)

            return markdown

        except Exception as e:
            console.print(f"[#B565D8]⚠️  {safe_t('web_fetch.markdown_error', 'Markdown 轉換錯誤')}：{e}[/#B565D8]")
            # 回退到純文字
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()

    def _clean_html(self, html: str) -> str:
        """清理 HTML（移除 script、style 等）"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # 移除不需要的標籤
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'noscript']):
            tag.decompose()

        return str(soup)

    def _post_process_markdown(self, markdown: str) -> str:
        """後處理 Markdown（清理多餘空行等）"""
        # 移除連續的多個空行
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)

        # 移除行尾空白
        markdown = re.sub(r'[ \t]+\n', '\n', markdown)

        # 移除開頭和結尾空白
        markdown = markdown.strip()

        return markdown

    def _extract_title(self, html: str) -> str:
        """從 HTML 提取標題"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # 嘗試從 <title> 提取
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)

        # 嘗試從 <h1> 提取
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)

        # 嘗試從 og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']

        return safe_t('web_fetch.no_title', '（無標題）')

    def _is_valid_url(self, url: str) -> bool:
        """驗證 URL 格式"""
        # 簡單的 URL 驗證
        pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # 可選端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return bool(pattern.match(url))

    def _get_cache_key(self, url: str) -> str:
        """生成快取鍵"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_from_cache(self, url: str) -> Optional[FetchedPage]:
        """從快取讀取"""
        key = self._get_cache_key(url)
        return self.cache.get(key)

    def _save_to_cache(self, url: str, page: FetchedPage) -> None:
        """儲存到快取"""
        key = self._get_cache_key(url)
        self.cache[key] = page

    def clear_cache(self) -> None:
        """清空快取"""
        self.cache.clear()
        console.print(f"[#B565D8]✓ {safe_t('web_fetch.cache_cleared', '快取已清空')}[/#B565D8]")

    def get_cache_stats(self) -> Dict[str, Any]:
        """取得快取統計"""
        return {
            "size": len(self.cache),
            "maxsize": self.cache.maxsize,
            "ttl": self.cache.ttl,
            "items": list(self.cache.keys())
        }


# ==================== 命令列介面 ====================

def main():
    """Web Fetch 命令列工具"""
    import sys

    console.print("\n[bold #B565D8]CodeGemini Web Fetch Tool[/bold #B565D8]\n")

    if len(sys.argv) < 2:
        console.print(f"{safe_t('common.usage', '用法')}：")
        console.print("  python tools/web_fetch.py <url> [--no-cache] [--output <file>]")
        console.print(f"\n{safe_t('common.options', '選項')}：")
        console.print(f"  --no-cache  {safe_t('web_fetch.no_cache', '不使用快取')}")
        console.print(f"  --output    {safe_t('web_fetch.output_to_file', '輸出到檔案')}")
        console.print(f"\n{safe_t('common.examples', '範例')}：")
        console.print("  python tools/web_fetch.py https://example.com")
        console.print("  python tools/web_fetch.py https://example.com --output page.md")
        return

    url = sys.argv[1]
    use_cache = True
    output_file = None

    # 解析參數
    for i, arg in enumerate(sys.argv):
        if arg == "--no-cache":
            use_cache = False
        elif arg == "--output" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]

    # 執行抓取
    fetcher = WebFetcher()
    page = fetcher.fetch(url, use_cache=use_cache)

    if page:
        # 顯示結果
        console.print(f"\n[bold]📄 {safe_t('web_fetch.page_content', '網頁內容')}：[/bold]\n")
        console.print(f"[bold #B565D8]{safe_t('web_fetch.title', '標題')}：[/bold #B565D8]{page.title}")
        console.print(f"[bold #B565D8]URL：[/bold #B565D8]{page.url}")
        console.print(f"[bold #B565D8]{safe_t('web_fetch.word_count', '字數')}：[/bold #B565D8]{page.word_count}")
        console.print(f"[bold #B565D8]{safe_t('web_fetch.status_code', '狀態碼')}：[/bold #B565D8]{page.status_code}")

        if page.is_redirect:
            console.print(f"[bold #B565D8]{safe_t('web_fetch.redirected_from', '重定向自')}：[/bold #B565D8]{page.redirected_from}")

        console.print(f"\n[dim]--- {safe_t('web_fetch.markdown_content', 'Markdown 內容')}（{safe_t('web_fetch.first_chars', '前')} 500 {safe_t('common.characters', '字')}） ---[/dim]")
        console.print(page.content[:500] + "..." if len(page.content) > 500 else page.content)

        # 輸出到檔案
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {page.title}\n\n")
                f.write(f"**URL:** {page.url}\n\n")
                f.write(f"**{safe_t('web_fetch.fetch_time', '抓取時間')}:** {page.fetched_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write(page.content)

            console.print(f"\n[#B565D8]✓ {safe_t('web_fetch.saved_to', '已儲存到')}：{output_file}[/#B565D8]")
    else:
        console.print(f"[dim #B565D8]✗ {safe_t('web_fetch.fetch_failed', '抓取失敗')}[/red]")


if __name__ == "__main__":
    main()
