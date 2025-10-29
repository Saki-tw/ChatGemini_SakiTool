#!/usr/bin/env python3
"""
記憶體 LRU 快取管理器

功能：
1. 自動追蹤記憶體使用量
2. 達到閾值時自動釋放最舊的項目
3. 支援手動清理
4. 提供統計資訊

演算法：
- LRU (Least Recently Used) 策略
- 時間複雜度：O(1) get/put 操作
- 空間複雜度：O(n) n=項目數

作者：Saki-TW (Saki@saki-studio.com.tw) with Claude
版本：v1.0.3
創建日期：2025-10-25
"""

import sys
import time
from collections import OrderedDict
from typing import Any, Optional, Dict
from rich.console import Console

console = Console()


class MemoryLRUCache:
    """
    記憶體感知的 LRU 快取

    特性：
    1. 自動追蹤記憶體使用量
    2. 達到閾值時自動釋放最舊的項目
    3. 支援 TTL（Time To Live）過期機制
    4. 線程安全（基本版本）

    演算法：
    - 使用 OrderedDict 實作 LRU
    - get 操作將項目移到最新位置
    - put 操作檢查容量，必要時移除最舊項目
    - 時間複雜度：O(1) for get/put

    使用範例：
        >>> cache = MemoryLRUCache(max_size_mb=100, max_items=50)
        >>> cache.put("key1", "value1")
        >>> value = cache.get("key1")  # 返回 "value1"
        >>> stats = cache.get_stats()  # 獲取統計資訊
    """

    def __init__(
        self,
        max_size_mb: int = 500,
        max_items: int = 100,
        default_ttl: Optional[int] = None,
        verbose: bool = False
    ):
        """
        初始化 LRU 快取

        Args:
            max_size_mb: 最大記憶體限制（MB）
            max_items: 最大項目數限制
            default_ttl: 預設 TTL（秒），None 表示永不過期
            verbose: 是否輸出詳細日誌
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_items = max_items
        self.default_ttl = default_ttl
        self.verbose = verbose

        # 核心資料結構
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.sizes: Dict[str, int] = {}  # {key: size_bytes}
        self.timestamps: Dict[str, float] = {}  # {key: creation_time}
        self.ttls: Dict[str, Optional[int]] = {}  # {key: ttl_seconds}

        # 統計資訊
        self.total_size = 0
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0

    def get(self, key: str) -> Optional[Any]:
        """
        獲取快取值（並移到最新位置）

        Args:
            key: 快取鍵

        Returns:
            快取值，如果不存在或已過期則返回 None

        時間複雜度：O(1)
        """
        if key not in self.cache:
            self.miss_count += 1
            return None

        # 檢查 TTL
        if self._is_expired(key):
            if self.verbose:
                console.print(f"[dim]⏰ 快取過期：{key[:30]}...[/dim]")
            self._remove(key)
            self.miss_count += 1
            return None

        # 移到最新位置（LRU 核心邏輯）
        self.cache.move_to_end(key)
        self.hit_count += 1

        return self.cache[key]

    def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        存入快取值（並自動清理）

        Args:
            key: 快取鍵
            value: 快取值
            ttl: TTL（秒），None 使用預設 TTL

        演算法：
        1. 計算值的大小
        2. 如果鍵已存在，先移除舊值
        3. 檢查容量，必要時清理最舊項目
        4. 存入新值

        時間複雜度：O(1) 平攤
        """
        # 計算大小
        size = sys.getsizeof(value)

        # 如果已存在，先移除
        if key in self.cache:
            self.total_size -= self.sizes[key]
            del self.cache[key]
            del self.sizes[key]
            del self.timestamps[key]
            del self.ttls[key]

        # 清理過期項目
        self._cleanup_expired()

        # 檢查是否需要清理空間
        while (
            (self.total_size + size > self.max_size_bytes) or
            (len(self.cache) >= self.max_items)
        ):
            if not self.cache:
                # 如果單個項目超過最大限制，記錄警告但仍然存入
                if size > self.max_size_bytes:
                    console.print(
                        f"[#DDA0DD]⚠️  警告：單個項目大小 ({size / 1024 / 1024:.1f}MB) "
                        f"超過快取限制 ({self.max_size_bytes / 1024 / 1024:.1f}MB)[/#DDA0DD]"
                    )
                break

            # 移除最舊項目（FIFO）
            self._evict_oldest()

        # 存入新值
        self.cache[key] = value
        self.sizes[key] = size
        self.timestamps[key] = time.time()
        self.ttls[key] = ttl if ttl is not None else self.default_ttl
        self.total_size += size

        if self.verbose:
            console.print(
                f"[dim]💾 快取存入：{key[:30]}... "
                f"({size / 1024:.1f}KB, 總計: {self.total_size / 1024 / 1024:.1f}MB)[/dim]"
            )

    def remove(self, key: str) -> bool:
        """
        手動移除快取項目

        Args:
            key: 快取鍵

        Returns:
            是否成功移除
        """
        if key in self.cache:
            self._remove(key)
            return True
        return False

    def clear(self) -> None:
        """清空所有快取"""
        count = len(self.cache)
        size_mb = self.total_size / 1024 / 1024

        self.cache.clear()
        self.sizes.clear()
        self.timestamps.clear()
        self.ttls.clear()
        self.total_size = 0

        if self.verbose:
            console.print(
                f"[dim]🗑️  清空快取：{count} 個項目，釋放 {size_mb:.1f}MB[/dim]"
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取快取統計資訊

        Returns:
            統計資訊字典，包含：
            - items: 當前項目數
            - total_size_mb: 當前總大小（MB）
            - max_size_mb: 最大限制（MB）
            - usage_percent: 使用率百分比
            - hit_count: 命中次數
            - miss_count: 未命中次數
            - hit_rate: 命中率
            - eviction_count: 淘汰次數
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = (
            (self.hit_count / total_requests * 100)
            if total_requests > 0
            else 0.0
        )

        return {
            "items": len(self.cache),
            "max_items": self.max_items,
            "total_size_mb": round(self.total_size / 1024 / 1024, 2),
            "max_size_mb": round(self.max_size_bytes / 1024 / 1024, 2),
            "usage_percent": round(
                (self.total_size / self.max_size_bytes) * 100, 2
            ) if self.max_size_bytes > 0 else 0.0,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(hit_rate, 2),
            "eviction_count": self.eviction_count,
        }

    def display_stats(self) -> None:
        """顯示快取統計資訊（Rich 格式）"""
        from rich.table import Table

        stats = self.get_stats()

        table = Table(title="快取統計資訊", show_header=True)
        table.add_column("指標", style="#87CEEB")
        table.add_column("值", style="green")

        table.add_row("項目數", f"{stats['items']} / {stats['max_items']}")
        table.add_row(
            "記憶體使用",
            f"{stats['total_size_mb']}MB / {stats['max_size_mb']}MB "
            f"({stats['usage_percent']}%)"
        )
        table.add_row("命中次數", str(stats['hit_count']))
        table.add_row("未命中次數", str(stats['miss_count']))
        table.add_row("命中率", f"{stats['hit_rate']}%")
        table.add_row("淘汰次數", str(stats['eviction_count']))

        console.print(table)

    # 內部方法

    def _is_expired(self, key: str) -> bool:
        """檢查項目是否過期"""
        ttl = self.ttls.get(key)
        if ttl is None:
            return False

        timestamp = self.timestamps.get(key, 0)
        return (time.time() - timestamp) > ttl

    def _remove(self, key: str) -> None:
        """內部移除方法"""
        if key in self.cache:
            self.total_size -= self.sizes[key]
            del self.cache[key]
            del self.sizes[key]
            del self.timestamps[key]
            del self.ttls[key]

    def _evict_oldest(self) -> None:
        """淘汰最舊的項目（LRU 核心邏輯）"""
        if not self.cache:
            return

        # OrderedDict 的 popitem(last=False) 移除最舊項目
        oldest_key, _ = self.cache.popitem(last=False)
        size_kb = self.sizes[oldest_key] / 1024
        self.total_size -= self.sizes.pop(oldest_key)
        del self.timestamps[oldest_key]
        del self.ttls[oldest_key]
        self.eviction_count += 1

        if self.verbose:
            console.print(
                f"[dim]🗑️  淘汰快取：{oldest_key[:30]}... (-{size_kb:.1f}KB)[/dim]"
            )

    def _cleanup_expired(self) -> None:
        """清理所有過期項目"""
        expired_keys = [
            key for key in self.cache
            if self._is_expired(key)
        ]

        for key in expired_keys:
            if self.verbose:
                console.print(f"[dim]⏰ 清理過期快取：{key[:30]}...[/dim]")
            self._remove(key)


# 全域快取實例（單例模式）
_global_cache: Optional[MemoryLRUCache] = None


def get_global_cache(
    max_size_mb: int = 500,
    max_items: int = 100,
    **kwargs
) -> MemoryLRUCache:
    """
    獲取全域快取實例（單例模式）

    Args:
        max_size_mb: 最大記憶體限制（MB）
        max_items: 最大項目數限制
        **kwargs: 其他參數傳遞給 MemoryLRUCache

    Returns:
        全域快取實例
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = MemoryLRUCache(
            max_size_mb=max_size_mb,
            max_items=max_items,
            **kwargs
        )
    return _global_cache


# 裝飾器：自動快取函數結果
def cached(
    ttl: Optional[int] = None,
    cache_instance: Optional[MemoryLRUCache] = None
):
    """
    函數結果快取裝飾器

    Args:
        ttl: 快取 TTL（秒）
        cache_instance: 快取實例，None 使用全域快取

    使用範例：
        >>> @cached(ttl=300)
        >>> def expensive_function(arg1, arg2):
        >>>     # 耗時操作
        >>>     return result
    """
    def decorator(func):
        cache = cache_instance or get_global_cache()

        def wrapper(*args, **kwargs):
            # 生成快取鍵
            import hashlib
            import json

            key_data = {
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            key = hashlib.md5(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()

            # 檢查快取
            result = cache.get(key)
            if result is not None:
                return result

            # 執行函數
            result = func(*args, **kwargs)

            # 存入快取
            cache.put(key, result, ttl=ttl)

            return result

        return wrapper
    return decorator


if __name__ == "__main__":
    # 測試程式碼
    console.print("[bold #87CEEB]測試 MemoryLRUCache[/bold #87CEEB]\n")

    # 建立快取實例
    cache = MemoryLRUCache(
        max_size_mb=10,  # 10MB 限制
        max_items=5,     # 5 個項目限制
        default_ttl=5,   # 5 秒過期
        verbose=True
    )

    # 測試存取
    console.print("[#DDA0DD]測試 1：基本存取[/#DDA0DD]")
    cache.put("key1", "value1" * 100)
    cache.put("key2", "value2" * 100)
    cache.put("key3", "value3" * 100)

    console.print(f"Get key1: {cache.get('key1')[:20]}...")
    console.print(f"Get key2: {cache.get('key2')[:20]}...")
    console.print(f"Get key4 (不存在): {cache.get('key4')}")

    # 測試 LRU 淘汰
    console.print("\n[#DDA0DD]測試 2：LRU 淘汰（超過項目數限制）[/#DDA0DD]")
    cache.put("key4", "value4" * 100)
    cache.put("key5", "value5" * 100)
    cache.put("key6", "value6" * 100)  # 應該淘汰 key1

    console.print(f"Get key1 (應已淘汰): {cache.get('key1')}")
    console.print(f"Get key6: {cache.get('key6')[:20]}...")

    # 顯示統計
    console.print("\n[#DDA0DD]測試 3：統計資訊[/#DDA0DD]")
    cache.display_stats()

    # 測試 TTL
    console.print("\n[#DDA0DD]測試 4：TTL 過期[/#DDA0DD]")
    cache.put("temp_key", "temp_value", ttl=2)
    console.print(f"立即讀取: {cache.get('temp_key')}")
    console.print("等待 3 秒...")
    time.sleep(3)
    console.print(f"3 秒後讀取 (應已過期): {cache.get('temp_key')}")

    # 最終統計
    console.print("\n[#DDA0DD]最終統計[/#DDA0DD]")
    cache.display_stats()
