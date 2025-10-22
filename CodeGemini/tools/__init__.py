#!/usr/bin/env python3
"""
CodeGemini Tools Module (TESTING ONLY)
工具模組 - 提供各種工具功能（僅供測試使用）

⚠️ 注意：此模組化版本僅供獨立測試使用
主要實作位於 /Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/CodeGemini.py

模組：
- web_search: 網路搜尋工具（Stage 7）
- web_fetch: 網頁抓取工具（Stage 8）
- background_shell: 背景 Shell 管理（Stage 9）- 包含 Rich 視覺化用於測試
"""

from .web_search import WebSearch, SearchResult, SearchEngine
from .web_fetch import WebFetcher, FetchedPage
from .background_shell import BackgroundShellManager, BackgroundShell, ShellStatus

__all__ = [
    'WebSearch', 'SearchResult', 'SearchEngine',
    'WebFetcher', 'FetchedPage',
    'BackgroundShellManager', 'BackgroundShell', 'ShellStatus'
]
