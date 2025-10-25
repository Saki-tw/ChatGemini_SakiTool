#!/usr/bin/env python3
"""
異步適配器工具
為同步函數自動添加異步支援

特性：
1. 自動將同步函數包裝為異步函數
2. 在執行緒池中執行同步函數（避免阻塞事件循環）
3. 智能分發：自動檢測事件循環並選擇最佳執行方式
4. 零侵入：無需修改原有程式碼

作者：Claude Code (Sonnet 4.5)
日期：2025-10-25
版本：1.0.0
"""
import asyncio
import inspect
import functools
from typing import Callable, Any, TypeVar, Optional
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')


# ==================== 核心適配器 ====================

class AsyncAdapter:
    """
    異步適配器

    將同步函數自動轉換為異步函數，並在執行緒池中執行。
    避免阻塞事件循環，適合 I/O 密集型操作。
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化適配器

        Args:
            max_workers: 執行緒池最大工作執行緒數（預設：None = CPU數*5）
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def run_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        在執行緒池中執行同步函數

        Args:
            func: 同步函數
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            函數執行結果
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor,
            functools.partial(func, *args, **kwargs)
        )

    def to_async(self, func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
        """
        將同步函數轉換為異步函數

        Args:
            func: 同步函數

        Returns:
            異步函數

        使用範例：
            sync_func = lambda x: x + 1
            async_func = adapter.to_async(sync_func)
            result = await async_func(5)  # 返回 6
        """
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self.run_sync(func, *args, **kwargs)

        return async_wrapper

    async def close(self):
        """關閉執行緒池"""
        self.executor.shutdown(wait=True)

    async def __aenter__(self):
        """異步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器出口"""
        await self.close()


# ==================== 裝飾器 ====================

def make_async(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
    """
    裝飾器：將同步函數轉換為異步函數

    使用範例：
        @make_async
        def sync_function(x, y):
            time.sleep(1)
            return x + y

        # 現在可以異步調用
        result = await sync_function(3, 4)

    Args:
        func: 同步函數

    Returns:
        異步函數
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(func, *args, **kwargs)
        )

    return async_wrapper


def smart_dispatch(async_func: Callable = None, sync_func: Callable = None):
    """
    智能分發裝飾器

    自動檢測是否在事件循環中，並選擇最佳執行方式：
    - 在事件循環中 → 使用異步版本
    - 否則 → 使用同步版本

    使用範例：
        @smart_dispatch(
            async_func=analyze_image_async,
            sync_func=analyze_image_sync
        )
        def analyze_image(path):
            pass  # 實際不會執行，僅作為介面

        # 自動選擇
        result = analyze_image("image.jpg")  # 會自動選擇 async 或 sync

    Args:
        async_func: 異步版本函數
        sync_func: 同步版本函數

    Returns:
        智能分發函數
    """
    def decorator(interface_func: Callable) -> Callable:
        @functools.wraps(interface_func)
        def wrapper(*args, **kwargs):
            try:
                # 檢測是否在事件循環中
                loop = asyncio.get_running_loop()

                # 在事件循環中，使用異步版本
                if async_func:
                    return async_func(*args, **kwargs)
                else:
                    raise RuntimeError("異步版本不可用")

            except RuntimeError:
                # 沒有事件循環，使用同步版本
                if sync_func:
                    return sync_func(*args, **kwargs)
                else:
                    # 沒有同步版本，嘗試在新事件循環中執行異步版本
                    if async_func:
                        return asyncio.run(async_func(*args, **kwargs))
                    else:
                        raise RuntimeError("同步和異步版本都不可用")

        return wrapper

    return decorator


# ==================== 批次處理工具 ====================

async def gather_with_concurrency(n: int, *tasks):
    """
    限制並行數的 gather

    Args:
        n: 最大並行數
        *tasks: 協程列表

    Returns:
        所有任務的結果

    使用範例：
        tasks = [fetch_data(i) for i in range(100)]
        results = await gather_with_concurrency(10, *tasks)
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def map_async(
    func: Callable,
    items: list,
    max_concurrent: int = 10
) -> list:
    """
    異步 map 函數（限制並行數）

    Args:
        func: 異步函數
        items: 項目列表
        max_concurrent: 最大並行數

    Returns:
        結果列表

    使用範例：
        async def process(item):
            await asyncio.sleep(0.1)
            return item * 2

        results = await map_async(process, [1, 2, 3, 4, 5])
    """
    tasks = [func(item) for item in items]
    return await gather_with_concurrency(max_concurrent, *tasks)


# ==================== 使用範例 ====================

if __name__ == "__main__":
    import time

    # 示範 1：基本使用
    async def demo_basic():
        print("\n示範 1：基本異步適配器")
        print("="*60)

        # 同步函數
        def sync_task(task_id, delay):
            print(f"  執行任務 {task_id}")
            time.sleep(delay)
            return f"任務 {task_id} 完成"

        # 創建適配器
        async with AsyncAdapter() as adapter:
            # 轉換為異步
            async_task = adapter.to_async(sync_task)

            # 並行執行
            results = await asyncio.gather(
                async_task(1, 0.5),
                async_task(2, 0.5),
                async_task(3, 0.5),
            )

            print(f"\n結果：{results}")

    # 示範 2：裝飾器
    async def demo_decorator():
        print("\n示範 2：make_async 裝飾器")
        print("="*60)

        @make_async
        def heavy_computation(n):
            time.sleep(0.5)
            return sum(range(n))

        # 並行執行
        results = await asyncio.gather(
            heavy_computation(1000),
            heavy_computation(2000),
            heavy_computation(3000),
        )

        print(f"\n結果：{results}")

    # 示範 3：批次處理
    async def demo_batch():
        print("\n示範 3：限制並行的批次處理")
        print("="*60)

        async def process_item(item):
            print(f"  處理項目 {item}")
            await asyncio.sleep(0.1)
            return item * 2

        # 處理 20 個項目，最多 5 個並行
        items = list(range(1, 21))
        results = await map_async(
            process_item,
            items,
            max_concurrent=5
        )

        print(f"\n完成 {len(results)} 個項目")
        print(f"結果：{results[:5]}... （顯示前5個）")

    # 執行所有示範
    async def main():
        print("\n" + "="*70)
        print("異步適配器工具示範")
        print("="*70)

        await demo_basic()
        await demo_decorator()
        await demo_batch()

        print("\n" + "="*70)
        print("示範完成")
        print("="*70 + "\n")

    asyncio.run(main())
