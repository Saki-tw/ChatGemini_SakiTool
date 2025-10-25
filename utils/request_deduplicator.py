#!/usr/bin/env python3
"""
請求去重器
使用 LRU 快取避免重複的 API 調用

特性：
1. SHA256 hash 生成去重鍵
2. LRU 快取（最近最少使用）
3. TTL 過期機制（防止過期資料）
4. 並發請求共享（相同請求只調用一次）
5. 統計資訊收集（命中率、快取大小等）

作者：Claude Code (Sonnet 4.5)
日期：2025-10-25
版本：1.0.0
"""
import asyncio
import hashlib
import re
import time
from collections import OrderedDict
from typing import Callable, Any, Optional, Dict
from rich.console import Console

console = Console()


# ==================== LRU 快取 ====================

class LRUCache:
    """
    LRU（最近最少使用）快取

    特性：
    - 固定容量（達到上限時移除最舊項目）
    - TTL 過期（超過時間的項目自動移除）
    - O(1) 查詢和更新
    """

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        初始化 LRU 快取

        Args:
            max_size: 最大快取項目數
            ttl: 快取有效期（秒）
        """
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        獲取快取項目

        Args:
            key: 快取鍵

        Returns:
            快取值（如果存在且未過期），否則 None
        """
        # 檢查 TTL
        if key in self.timestamps:
            if time.time() - self.timestamps[key] > self.ttl:
                self.remove(key)
                return None

        # 檢查是否存在
        if key not in self.cache:
            return None

        # 命中，移到最新（OrderedDict 會維護順序）
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: Any):
        """
        新增/更新快取項目

        Args:
            key: 快取鍵
            value: 快取值
        """
        # 已存在，更新
        if key in self.cache:
            self.cache.move_to_end(key)
            self.cache[key] = value
            self.timestamps[key] = time.time()
            return

        # 檢查容量
        if len(self.cache) >= self.max_size:
            # 移除最舊的（OrderedDict 的第一個）
            oldest_key = next(iter(self.cache))
            self.remove(oldest_key)

        # 新增
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self.cache.move_to_end(key)

    def remove(self, key: str):
        """
        移除快取項目

        Args:
            key: 快取鍵
        """
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]

    def clear(self):
        """清空快取"""
        self.cache.clear()
        self.timestamps.clear()

    def size(self) -> int:
        """獲取當前快取大小"""
        return len(self.cache)


# ==================== 去重器 ====================

class RequestDeduplicator:
    """
    請求去重器

    自動檢測並避免重複的 API 調用。
    使用 LRU 快取存儲最近的結果，並在收到相同請求時直接返回快取。

    使用範例：
        deduper = RequestDeduplicator(
            max_cache_size=1000,
            ttl=300
        )

        # 定義 fetch 函數
        async def fetch_result():
            response = await api.generate_content(...)
            return response.text

        # 獲取結果（自動去重）
        result = await deduper.get_or_fetch(
            model='gemini-2.5-flash',
            content='分析這張圖片',
            fetch_func=fetch_result
        )
    """

    def __init__(
        self,
        max_cache_size: int = 1000,
        ttl: int = 300,
        enabled: bool = True,
        verbose: bool = False
    ):
        """
        初始化去重器

        Args:
            max_cache_size: 最大快取項目數
            ttl: 快取有效期（秒）
            enabled: 是否啟用去重
            verbose: 是否顯示詳細資訊
        """
        self.cache = LRUCache(max_cache_size, ttl)
        self.enabled = enabled
        self.verbose = verbose

        # 正在執行的請求 {key: Future}
        # 用於並發請求共享（相同請求同時到達時）
        self.pending: Dict[str, asyncio.Task] = {}

        # 統計資訊
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'dedup_hits': 0,  # 並發去重
            'cache_misses': 0
        }

        # 鎖（保護 pending）
        self._lock = asyncio.Lock()

    async def get_or_fetch(
        self,
        model: str,
        content: str,
        fetch_func: Callable[[], Any],
        config: Optional[Dict] = None
    ) -> Any:
        """
        獲取結果（優先使用快取）

        流程：
        1. 檢查快取
        2. 檢查是否有相同請求正在執行
        3. 執行新請求並快取結果

        Args:
            model: 模型名稱
            content: 請求內容
            fetch_func: 獲取結果的函數（無參數）
            config: 配置參數（可選，用於生成去重鍵）

        Returns:
            API 回應結果
        """
        if not self.enabled:
            # 去重器停用，直接調用
            return await fetch_func()

        self.stats['total_requests'] += 1

        # 生成去重鍵
        key = self._generate_key(model, content, config)

        # 檢查快取
        cached = self.cache.get(key)
        if cached is not None:
            self.stats['cache_hits'] += 1
            if self.verbose:
                console.print(f"[dim]💾 快取命中（去重）[/dim]")
            return cached

        # 檢查是否有相同請求正在執行
        async with self._lock:
            if key in self.pending:
                self.stats['dedup_hits'] += 1
                if self.verbose:
                    console.print(f"[dim]🔗 等待現有請求完成（並發去重）[/dim]")

                # 等待現有請求完成
                task = self.pending[key]

        # 如果有正在執行的請求，等待它
        if key in self.pending:
            try:
                result = await task
                return result
            except Exception as e:
                # 如果現有請求失敗，不使用其結果
                pass

        # 快取未命中，執行新請求
        self.stats['cache_misses'] += 1

        async with self._lock:
            # 再次檢查（避免競爭條件）
            if key in self.pending:
                task = self.pending[key]
                return await task

            # 創建新任務
            task = asyncio.create_task(fetch_func())
            self.pending[key] = task

        try:
            # 執行請求
            result = await task

            # 快取結果
            self.cache.put(key, result)

            return result

        except Exception as e:
            # 請求失敗，不快取
            raise

        finally:
            # 清理 pending
            async with self._lock:
                if key in self.pending:
                    del self.pending[key]

    def _generate_key(
        self,
        model: str,
        content: str,
        config: Optional[Dict] = None
    ) -> str:
        """
        生成去重鍵

        使用 SHA256 hash 確保：
        1. 相同內容 → 相同鍵
        2. 不同內容 → 不同鍵
        3. 鍵長度固定（不受內容長度影響）

        Args:
            model: 模型名稱
            content: 請求內容
            config: 配置參數（可選）

        Returns:
            去重鍵（SHA256 hex）
        """
        # 標準化內容（移除多餘空白、統一換行）
        normalized = re.sub(r'\s+', ' ', content.strip())

        # 構建鍵字串
        key_parts = [model, normalized]

        # 加入配置參數（如果有）
        if config:
            # 只考慮影響結果的參數
            relevant_params = ['temperature', 'top_p', 'top_k', 'max_tokens']
            for param in relevant_params:
                if param in config:
                    key_parts.append(f"{param}={config[param]}")

        key_string = "|".join(key_parts)

        # 生成 hash
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計資訊

        Returns:
            統計資訊字典
        """
        total = self.stats['total_requests']
        cache_hits = self.stats['cache_hits']
        dedup_hits = self.stats['dedup_hits']

        return {
            **self.stats,
            'hit_rate': (
                (cache_hits + dedup_hits) / total
            ) if total > 0 else 0,
            'cache_hit_rate': cache_hits / total if total > 0 else 0,
            'dedup_hit_rate': dedup_hits / total if total > 0 else 0,
            'cache_size': self.cache.size()
        }

    def clear_cache(self):
        """清空快取"""
        self.cache.clear()

    async def close(self):
        """關閉去重器（清理資源）"""
        # 等待所有正在執行的請求完成
        if self.pending:
            await asyncio.gather(*self.pending.values(), return_exceptions=True)

        self.pending.clear()
        self.cache.clear()


# ==================== 使用範例 ====================

if __name__ == "__main__":
    import random

    async def demo():
        """示範請求去重"""
        print("\n" + "="*70)
        print("請求去重器示範")
        print("="*70 + "\n")

        # 模擬 API 調用
        api_call_count = 0

        async def mock_fetch(request_id: str) -> str:
            """模擬 API 調用"""
            nonlocal api_call_count
            api_call_count += 1

            await asyncio.sleep(0.1)  # 模擬網路延遲
            return f"Result for {request_id}"

        # 創建去重器
        deduper = RequestDeduplicator(
            max_cache_size=100,
            ttl=60,
            verbose=True
        )

        # 測試 1：重複請求去重
        print("測試 1：提交 10 個相同請求")
        print("-" * 70)

        api_call_count = 0
        start = time.time()

        tasks = [
            deduper.get_or_fetch(
                model='gemini-2.5-flash',
                content='分析這張圖片',
                fetch_func=lambda: mock_fetch('same_request')
            )
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        print(f"\n✅ 完成 {len(results)} 個請求")
        print(f"⏱️  總耗時：{elapsed:.2f}s")
        print(f"📞 API 調用次數：{api_call_count} 次（預期：1 次）")

        stats = deduper.get_stats()
        print(f"📊 命中率：{stats['hit_rate']*100:.1f}%")
        print(f"   快取命中：{stats['cache_hits']}")
        print(f"   並發去重：{stats['dedup_hits']}")
        print(f"   快取未命中：{stats['cache_misses']}")

        # 測試 2：混合請求（部分重複）
        print("\n測試 2：混合請求（50% 重複）")
        print("-" * 70)

        api_call_count = 0
        requests = ['A', 'B', 'C'] * 10  # 30 個請求，3 個唯一

        start = time.time()

        tasks = [
            deduper.get_or_fetch(
                model='gemini-2.5-flash',
                content=f'請求 {req}',
                fetch_func=lambda r=req: mock_fetch(r)
            )
            for req in requests
        ]

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        print(f"\n✅ 完成 {len(results)} 個請求")
        print(f"⏱️  總耗時：{elapsed:.2f}s")
        print(f"📞 API 調用次數：{api_call_count} 次（預期：3 次）")

        stats = deduper.get_stats()
        print(f"📊 總體命中率：{stats['hit_rate']*100:.1f}%")
        print(f"   快取大小：{stats['cache_size']} 項目")

        print("\n" + "="*70)
        print("示範完成")
        print("="*70 + "\n")

        await deduper.close()

    asyncio.run(demo())
