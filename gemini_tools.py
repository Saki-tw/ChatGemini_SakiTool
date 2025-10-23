#!/usr/bin/env python3
"""
ChatGemini_SakiTool - 自動化工具管理系統
Automatic Tool Management System

設計理念：
1. 完全自動化 - 用戶無需手動配置
2. 惰性載入 - 需要時才初始化，節省資源
3. 靜默管理 - 載入/卸載在後台進行，不打擾用戶
4. 智能偵測 - 根據輸入自動判斷需要哪些工具
5. 配置驅動 - 所有設定隱藏在 config

特性：
- 用到時顯示「已載入」，不用時默默卸載
- 不會有任何配置介面打擾用戶
- 所有控制都透過 config.py 完成

Author: Saki-tw
Created: 2025-10-23
Version: 2.0 (全自動化版本)
"""

import os
import re
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from rich.console import Console

console = Console()


# ==========================================
# 工具載入記錄
# ==========================================

@dataclass
class ToolLoadRecord:
    """工具載入記錄"""
    tool_name: str
    loaded_at: datetime
    last_used: datetime
    use_count: int = 0
    instance: Any = None

    def mark_used(self):
        """標記為已使用"""
        self.last_used = datetime.now()
        self.use_count += 1

    @property
    def idle_time(self) -> float:
        """閒置時間（秒）"""
        return (datetime.now() - self.last_used).total_seconds()


# ==========================================
# 自動化工具管理器
# ==========================================

class AutoToolManager:
    """
    自動化工具管理器

    完全自動化的工具管理系統：
    - 根據輸入自動偵測需要的工具
    - 惰性載入（需要時才初始化）
    - 自動卸載不用的工具（節省記憶體）
    - 靜默操作（不打擾用戶）
    """

    def __init__(
        self,
        auto_unload_timeout: int = 300,  # 5 分鐘未使用自動卸載
        show_load_message: bool = False   # 是否顯示載入訊息（預設靜默）
    ):
        """
        初始化自動化工具管理器

        Args:
            auto_unload_timeout: 自動卸載閒置時間（秒）
            show_load_message: 是否顯示載入訊息
        """
        self._loaded_tools: Dict[str, ToolLoadRecord] = {}
        self._auto_unload_timeout = auto_unload_timeout
        self._show_load_message = show_load_message

        # 工具載入器映射（惰性載入）
        self._tool_loaders = {
            'web_search': self._load_web_search,
            'web_fetch': self._load_web_fetch,
            'background_shell': self._load_background_shell
        }

        # 偵測關鍵字映射
        self._detection_keywords = {
            'web_search': [
                r'搜尋.*(?:資訊|資料|文章)',
                r'查詢.*(?:網路|網頁)',
                r'找.*(?:相關|資訊)',
                r'search\s+for',
                r'find\s+information',
                r'google\s+',
                r'搜一下',
                r'查一下'
            ],
            'web_fetch': [
                r'https?://\S+',  # 包含 URL
                r'抓取.*(?:網頁|內容)',
                r'讀取.*(?:網頁|頁面)',
                r'fetch\s+',
                r'get\s+(?:webpage|page|url)',
                r'下載.*網頁'
            ],
            'background_shell': [
                r'執行.*(?:命令|指令)',
                r'運行.*(?:腳本|程式)',
                r'run\s+command',
                r'execute\s+',
                r'背景執行',
                r'後台運行',
                r'bash\s+',
                r'shell\s+'
            ]
        }

    def detect_and_prepare(self, user_input: str) -> List[str]:
        """
        根據用戶輸入自動偵測並準備工具

        Args:
            user_input: 用戶輸入

        Returns:
            List[str]: 準備好的工具名稱列表
        """
        prepared_tools = []

        for tool_name, patterns in self._detection_keywords.items():
            if self._should_load_tool(user_input, patterns):
                if self._ensure_loaded(tool_name):
                    prepared_tools.append(tool_name)

        # 自動清理閒置工具
        self._cleanup_idle_tools()

        return prepared_tools

    def _should_load_tool(self, user_input: str, patterns: List[str]) -> bool:
        """
        判斷是否需要載入工具

        Args:
            user_input: 用戶輸入
            patterns: 偵測模式列表

        Returns:
            bool: 是否需要載入
        """
        for pattern in patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return True
        return False

    def _ensure_loaded(self, tool_name: str) -> bool:
        """
        確保工具已載入（惰性載入）

        Args:
            tool_name: 工具名稱

        Returns:
            bool: 是否成功載入
        """
        # 如果已載入，標記為使用並返回
        if tool_name in self._loaded_tools:
            self._loaded_tools[tool_name].mark_used()
            return True

        # 惰性載入工具
        loader = self._tool_loaders.get(tool_name)
        if not loader:
            console.print(f"[dim]⚠️ 未知工具：{tool_name}[/dim]")
            return False

        try:
            # 靜默載入
            tool_instance = loader()

            # 記錄載入
            self._loaded_tools[tool_name] = ToolLoadRecord(
                tool_name=tool_name,
                loaded_at=datetime.now(),
                last_used=datetime.now(),
                use_count=1,
                instance=tool_instance
            )

            # 僅在配置允許時顯示訊息
            if self._show_load_message:
                console.print(f"[dim]✓ {tool_name} 已載入[/dim]")

            return True

        except Exception as e:
            console.print(f"[dim]⚠️ {tool_name} 載入失敗：{e}[/dim]")
            return False

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """
        取得工具實例（用於實際調用）

        Args:
            tool_name: 工具名稱

        Returns:
            Optional[Any]: 工具實例
        """
        record = self._loaded_tools.get(tool_name)
        if record:
            record.mark_used()

            # 首次實際使用時顯示訊息
            if record.use_count == 1:
                console.print(f"[dim bright_magenta]✓ 使用 {tool_name}[/green][/dim]")

            return record.instance
        return None

    def _cleanup_idle_tools(self):
        """自動清理閒置工具（靜默卸載）"""
        to_unload = []

        for tool_name, record in self._loaded_tools.items():
            if record.idle_time > self._auto_unload_timeout:
                to_unload.append(tool_name)

        for tool_name in to_unload:
            self._unload_tool(tool_name)

    def _unload_tool(self, tool_name: str):
        """卸載工具（靜默操作）"""
        if tool_name in self._loaded_tools:
            del self._loaded_tools[tool_name]
            # 完全靜默，不顯示任何訊息

    def force_unload_all(self):
        """強制卸載所有工具（用於程序結束）"""
        self._loaded_tools.clear()

    def get_stats(self) -> Dict[str, Any]:
        """取得統計資訊（用於調試）"""
        return {
            'loaded_count': len(self._loaded_tools),
            'tools': {
                name: {
                    'use_count': record.use_count,
                    'idle_time': f"{record.idle_time:.1f}s"
                }
                for name, record in self._loaded_tools.items()
            }
        }

    # ==========================================
    # 工具載入器（惰性載入實作）
    # ==========================================

    def _load_web_search(self):
        """載入 WebSearch 工具"""
        from CodeGemini.tools.web_search import WebSearch, SearchEngine

        # 根據配置選擇搜尋引擎
        try:
            from config import SEARCH_ENGINE
            engine = SearchEngine(SEARCH_ENGINE) if hasattr(SearchEngine, SEARCH_ENGINE.upper()) else SearchEngine.DUCKDUCKGO
        except:
            engine = SearchEngine.DUCKDUCKGO

        return WebSearch(engine=engine)

    def _load_web_fetch(self):
        """載入 WebFetch 工具"""
        from CodeGemini.tools.web_fetch import WebFetcher

        # 根據配置設定參數
        try:
            from config import WEB_FETCH_TIMEOUT, WEB_FETCH_CACHE_TTL
            timeout = WEB_FETCH_TIMEOUT
            cache_ttl = WEB_FETCH_CACHE_TTL
        except:
            timeout = 30
            cache_ttl = 900

        return WebFetcher(timeout=timeout, cache_ttl=cache_ttl)

    def _load_background_shell(self):
        """載入 BackgroundShell 工具"""
        from CodeGemini.tools.background_shell import BackgroundShellManager

        return BackgroundShellManager()


# ==========================================
# 工具調用包裝器（高級 API）
# ==========================================

class ToolWrapper:
    """
    工具調用包裝器

    提供更高級的 API，隱藏底層複雜性
    """

    def __init__(self, manager: AutoToolManager):
        self.manager = manager

    def search_web(self, query: str, max_results: int = 5) -> Optional[Any]:
        """
        搜尋網路

        Args:
            query: 搜尋關鍵字
            max_results: 最大結果數

        Returns:
            搜尋結果
        """
        tool = self.manager.get_tool('web_search')
        if tool:
            return tool.search(query, max_results=max_results)
        return None

    def fetch_webpage(self, url: str) -> Optional[Any]:
        """
        抓取網頁

        Args:
            url: 網頁 URL

        Returns:
            網頁內容
        """
        tool = self.manager.get_tool('web_fetch')
        if tool:
            return tool.fetch(url)
        return None

    def run_shell_command(self, command: str) -> Optional[str]:
        """
        執行 Shell 命令

        Args:
            command: 命令

        Returns:
            Shell ID
        """
        tool = self.manager.get_tool('background_shell')
        if tool:
            return tool.start_shell(command)
        return None

    def get_shell_output(self, shell_id: str) -> Optional[str]:
        """
        取得 Shell 輸出

        Args:
            shell_id: Shell ID

        Returns:
            輸出內容
        """
        tool = self.manager.get_tool('background_shell')
        if tool:
            return tool.get_output(shell_id)
        return None


# ==========================================
# 全局實例（單例）
# ==========================================

# 從 config 讀取設定
try:
    from config import AUTO_TOOL_UNLOAD_TIMEOUT, SHOW_TOOL_LOAD_MESSAGE
    _auto_unload_timeout = AUTO_TOOL_UNLOAD_TIMEOUT
    _show_load_message = SHOW_TOOL_LOAD_MESSAGE
except:
    _auto_unload_timeout = 300  # 預設 5 分鐘
    _show_load_message = False  # 預設靜默

# 創建全局管理器
auto_tool_manager = AutoToolManager(
    auto_unload_timeout=_auto_unload_timeout,
    show_load_message=_show_load_message
)

# 創建工具包裝器
tool_wrapper = ToolWrapper(auto_tool_manager)


# ==========================================
# 便利函數（供 gemini_chat.py 使用）
# ==========================================

def prepare_tools_for_input(user_input: str) -> List[str]:
    """
    根據用戶輸入準備工具（自動偵測）

    Args:
        user_input: 用戶輸入

    Returns:
        List[str]: 準備好的工具列表
    """
    return auto_tool_manager.detect_and_prepare(user_input)


def search_web(query: str, max_results: int = 5):
    """搜尋網路（便利函數）"""
    return tool_wrapper.search_web(query, max_results)


def fetch_webpage(url: str):
    """抓取網頁（便利函數）"""
    return tool_wrapper.fetch_webpage(url)


def run_shell_command(command: str):
    """執行命令（便利函數）"""
    return tool_wrapper.run_shell_command(command)


def get_shell_output(shell_id: str):
    """取得輸出（便利函數）"""
    return tool_wrapper.get_shell_output(shell_id)


def cleanup_tools():
    """清理工具（程序結束時調用）"""
    auto_tool_manager.force_unload_all()


# ==========================================
# 測試程式
# ==========================================

if __name__ == "__main__":
    console.print("\n[bold bright_magenta]自動化工具管理系統測試[/bold bright_magenta]\n")

    # 測試 1: 自動偵測搜尋需求
    console.print("[bold]測試 1: 搜尋偵測[/bold]")
    user_input_1 = "請幫我搜尋一下 Python 最新版本的資訊"
    prepared = prepare_tools_for_input(user_input_1)
    console.print(f"輸入: {user_input_1}")
    console.print(f"準備工具: {prepared}\n")

    # 測試 2: 自動偵測網頁抓取需求
    console.print("[bold]測試 2: 網頁抓取偵測[/bold]")
    user_input_2 = "請抓取 https://example.com 的內容"
    prepared = prepare_tools_for_input(user_input_2)
    console.print(f"輸入: {user_input_2}")
    console.print(f"準備工具: {prepared}\n")

    # 測試 3: 自動偵測命令執行需求
    console.print("[bold]測試 3: 命令執行偵測[/bold]")
    user_input_3 = "請在背景執行 ping google.com"
    prepared = prepare_tools_for_input(user_input_3)
    console.print(f"輸入: {user_input_3}")
    console.print(f"準備工具: {prepared}\n")

    # 顯示統計
    console.print("[bold]統計資訊:[/bold]")
    console.print(auto_tool_manager.get_stats())

    console.print("\n[bright_magenta]✓ 測試完成[/green]\n")
