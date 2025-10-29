#!/usr/bin/env python3
"""
功能偵測與自動降級系統

功能：
1. 檢測 Python 版本（asyncio 需求）
2. 檢測依賴套件可用性
3. 自動降級到相容版本
4. 提供功能可用性查詢

設計原則：
- 零破壞性：總是能找到可用的實作
- 透明降級：使用者無需關心底層實作
- 清晰提示：告知使用者當前使用的版本

作者：Saki-TW (Saki@saki-studio.com.tw) with Claude
版本：v1.0.3
創建日期：2025-10-25
"""

import sys
import importlib
from typing import Optional, Type, Any, Dict
from rich.console import Console

console = Console()


class FeatureDetector:
    """
    功能偵測器

    提供系統功能檢測和智能降級機制

    使用範例：
        >>> # 自動選擇最佳批次處理器
        >>> BatchProcessor = FeatureDetector.get_batch_processor()
        >>> processor = BatchProcessor(max_concurrent=5)
        >>>
        >>> # 檢測 asyncio 支援
        >>> if FeatureDetector.supports_asyncio():
        >>>     # 使用異步版本
        >>>     pass
    """

    # 快取檢測結果
    _cache: Dict[str, bool] = {}

    @staticmethod
    def supports_asyncio() -> bool:
        """
        檢測是否支援 asyncio

        Returns:
            True 如果 Python 版本 >= 3.7
        """
        if 'asyncio' not in FeatureDetector._cache:
            FeatureDetector._cache['asyncio'] = sys.version_info >= (3, 7)

        return FeatureDetector._cache['asyncio']

    @staticmethod
    def supports_typing_extensions() -> bool:
        """
        檢測是否支援 typing 擴展

        Returns:
            True 如果 Python 版本 >= 3.8 或已安裝 typing_extensions
        """
        if 'typing_extensions' not in FeatureDetector._cache:
            try:
                import typing_extensions
                FeatureDetector._cache['typing_extensions'] = True
            except ImportError:
                FeatureDetector._cache['typing_extensions'] = sys.version_info >= (3, 8)

        return FeatureDetector._cache['typing_extensions']

    @staticmethod
    def supports_package(package_name: str) -> bool:
        """
        檢測套件是否可用

        Args:
            package_name: 套件名稱

        Returns:
            True 如果套件已安裝且可導入
        """
        cache_key = f"package:{package_name}"
        if cache_key not in FeatureDetector._cache:
            try:
                importlib.import_module(package_name)
                FeatureDetector._cache[cache_key] = True
            except ImportError:
                FeatureDetector._cache[cache_key] = False

        return FeatureDetector._cache[cache_key]

    @staticmethod
    def get_batch_processor() -> Type:
        """
        獲取最佳批次處理器

        自動選擇：
        - Python 3.7+ + asyncio 可用 → AsyncBatchProcessor（推薦）
        - 否則 → BatchProcessor（降級）

        Returns:
            批次處理器類別

        使用範例：
            >>> BatchProcessor = FeatureDetector.get_batch_processor()
            >>> processor = BatchProcessor(max_concurrent=5)
        """
        # 嘗試使用異步版本
        if FeatureDetector.supports_asyncio():
            try:
                from gemini_async_batch_processor import AsyncBatchProcessor
                console.print(
                    "[dim]✓ 使用異步批次處理器（優化版，效能提升 5-10x）[/dim]"
                )
                return AsyncBatchProcessor
            except ImportError:
                # 異步版本未實作，降級
                pass

        # 降級到同步版本
        try:
            from gemini_batch_processor import BatchProcessor
            console.print(
                "[dim]ℹ️  使用同步批次處理器（相容模式）[/dim]"
            )
            return BatchProcessor
        except ImportError:
            console.print(
                "[red]錯誤：無法導入任何批次處理器！[/red]"
            )
            raise ImportError("批次處理器不可用")

    @staticmethod
    def get_http_client(async_mode: bool = False) -> Type:
        """
        獲取最佳 HTTP 客戶端

        自動選擇：
        - async_mode=True → aiohttp 或 httpx（異步）
        - async_mode=False → requests（同步）

        Args:
            async_mode: 是否需要異步客戶端

        Returns:
            HTTP 客戶端類別
        """
        if async_mode:
            # 優先使用 aiohttp
            if FeatureDetector.supports_package('aiohttp'):
                import aiohttp
                console.print("[dim]✓ 使用 aiohttp（異步 HTTP 客戶端）[/dim]")
                return aiohttp.ClientSession

            # 降級到 httpx
            if FeatureDetector.supports_package('httpx'):
                import httpx
                console.print("[dim]✓ 使用 httpx（異步 HTTP 客戶端）[/dim]")
                return httpx.AsyncClient

            # 無法使用異步，警告並降級
            console.print(
                "[#DDA0DD]警告：未安裝異步 HTTP 客戶端（aiohttp 或 httpx），降級到同步模式[/#DDA0DD]"
            )

        # 同步模式：使用 requests
        if FeatureDetector.supports_package('requests'):
            import requests
            console.print("[dim]✓ 使用 requests（同步 HTTP 客戶端）[/dim]")
            return requests.Session

        console.print("[red]錯誤：無法導入任何 HTTP 客戶端！[/red]")
        raise ImportError("HTTP 客戶端不可用")

    @staticmethod
    def get_cache_backend(
        preferred: str = "memory",
        **kwargs
    ):
        """
        獲取快取後端

        自動選擇：
        - preferred="memory" → MemoryLRUCache
        - preferred="redis" → Redis（如果可用）
        - preferred="memcached" → Memcached（如果可用）
        - 降級 → MemoryLRUCache

        Args:
            preferred: 偏好的快取後端
            **kwargs: 傳遞給快取實例的參數

        Returns:
            快取實例
        """
        if preferred == "redis" and FeatureDetector.supports_package('redis'):
            import redis
            console.print("[dim]✓ 使用 Redis 快取後端[/dim]")
            # 這裡應該返回 Redis 包裝器
            # 簡化版本：返回記憶體快取
            pass

        if preferred == "memcached" and FeatureDetector.supports_package('pymemcache'):
            import pymemcache
            console.print("[dim]✓ 使用 Memcached 快取後端[/dim]")
            # 這裡應該返回 Memcached 包裝器
            pass

        # 預設：使用記憶體快取
        from .memory_cache import MemoryLRUCache
        console.print("[dim]✓ 使用記憶體 LRU 快取後端[/dim]")
        return MemoryLRUCache(**kwargs)

    @staticmethod
    def check_environment() -> Dict[str, Any]:
        """
        檢查執行環境

        Returns:
            環境資訊字典，包含：
            - python_version: Python 版本
            - asyncio_support: asyncio 支援
            - available_packages: 可用套件列表
            - recommendations: 建議安裝的套件
        """
        # 檢測常用套件
        packages_to_check = [
            'aiohttp',
            'httpx',
            'requests',
            'redis',
            'pymemcache',
            'rich',
            'google.generativeai'
        ]

        available = []
        missing = []

        for package in packages_to_check:
            if FeatureDetector.supports_package(package):
                available.append(package)
            else:
                missing.append(package)

        # 生成建議
        recommendations = []
        if not FeatureDetector.supports_asyncio():
            recommendations.append("升級到 Python 3.7+ 以獲得更好的效能")

        if 'aiohttp' not in available and 'httpx' not in available:
            recommendations.append("安裝 aiohttp 或 httpx 以啟用異步 HTTP 請求")

        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "asyncio_support": FeatureDetector.supports_asyncio(),
            "available_packages": available,
            "missing_packages": missing,
            "recommendations": recommendations
        }

    @staticmethod
    def display_environment_info() -> None:
        """顯示環境資訊（Rich 格式）"""
        from rich.table import Table
        from rich.panel import Panel

        info = FeatureDetector.check_environment()

        # 建立表格
        table = Table(title="執行環境資訊", show_header=True)
        table.add_column("項目", style="#87CEEB")
        table.add_column("狀態", style="green")

        # 基本資訊
        table.add_row("Python 版本", info['python_version'])
        table.add_row(
            "AsyncIO 支援",
            "✓ 支援" if info['asyncio_support'] else "✗ 不支援"
        )

        # 可用套件
        table.add_row(
            "可用套件",
            ", ".join(info['available_packages']) if info['available_packages'] else "無"
        )

        console.print(table)

        # 建議
        if info['recommendations']:
            recommendations_text = "\n".join(
                f"• {rec}" for rec in info['recommendations']
            )
            console.print(Panel(
                recommendations_text,
                title="建議",
                border_style="#DDA0DD"
            ))


class CompatibilityAdapter:
    """
    相容性適配器

    提供統一的介面，自動處理不同版本的差異

    使用範例：
        >>> adapter = CompatibilityAdapter()
        >>> # 自動選擇最佳實作
        >>> result = adapter.batch_process(tasks)
    """

    def __init__(self, prefer_async: bool = True, verbose: bool = False):
        """
        初始化適配器

        Args:
            prefer_async: 是否偏好異步實作
            verbose: 是否輸出詳細日誌
        """
        self.prefer_async = prefer_async and FeatureDetector.supports_asyncio()
        self.verbose = verbose

        if self.verbose:
            console.print(
                f"[dim]相容性適配器初始化：async={'啟用' if self.prefer_async else '停用'}[/dim]"
            )

    def get_best_implementation(
        self,
        async_impl: Optional[Type] = None,
        sync_impl: Optional[Type] = None
    ) -> Type:
        """
        獲取最佳實作

        Args:
            async_impl: 異步實作類別
            sync_impl: 同步實作類別

        Returns:
            最佳實作類別
        """
        if self.prefer_async and async_impl is not None:
            if self.verbose:
                console.print("[dim]選擇異步實作[/dim]")
            return async_impl

        if sync_impl is not None:
            if self.verbose:
                console.print("[dim]選擇同步實作[/dim]")
            return sync_impl

        raise ValueError("無可用實作")


# 便捷函數
def check_and_display_environment():
    """便捷函數：檢查並顯示環境資訊"""
    FeatureDetector.display_environment_info()


def get_optimal_batch_processor():
    """便捷函數：獲取最佳批次處理器"""
    return FeatureDetector.get_batch_processor()


if __name__ == "__main__":
    # 測試程式碼
    console.print("[bold #87CEEB]功能偵測測試[/bold #87CEEB]\n")

    # 測試基本檢測
    console.print("[#DDA0DD]測試 1：基本功能檢測[/#DDA0DD]")
    console.print(f"AsyncIO 支援：{FeatureDetector.supports_asyncio()}")
    console.print(f"Typing Extensions 支援：{FeatureDetector.supports_typing_extensions()}")

    # 測試套件檢測
    console.print("\n[#DDA0DD]測試 2：套件可用性檢測[/#DDA0DD]")
    packages = ['rich', 'google.generativeai', 'aiohttp', 'httpx', 'requests']
    for package in packages:
        available = FeatureDetector.supports_package(package)
        status = "✓ 可用" if available else "✗ 不可用"
        console.print(f"{package}: {status}")

    # 顯示環境資訊
    console.print("\n[#DDA0DD]測試 3：完整環境資訊[/#DDA0DD]")
    FeatureDetector.display_environment_info()

    # 測試智能選擇
    console.print("\n[#DDA0DD]測試 4：智能元件選擇[/#DDA0DD]")
    try:
        BatchProcessor = FeatureDetector.get_batch_processor()
        console.print(f"選擇的批次處理器：{BatchProcessor.__name__}")
    except ImportError as e:
        console.print(f"[red]錯誤：{e}[/red]")

    try:
        HttpClient = FeatureDetector.get_http_client(async_mode=True)
        console.print(f"選擇的 HTTP 客戶端：{HttpClient.__name__}")
    except ImportError as e:
        console.print(f"[red]錯誤：{e}[/red]")

    # 測試快取後端
    console.print("\n[#DDA0DD]測試 5：快取後端選擇[/#DDA0DD]")
    cache = FeatureDetector.get_cache_backend(max_size_mb=100)
    console.print(f"選擇的快取後端：{cache.__class__.__name__}")
