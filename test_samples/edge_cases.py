#!/usr/bin/env python3
"""特殊情況測試範例 - 生成器、裝飾器、async 函數"""

import asyncio
from typing import Iterator, List
from functools import wraps


def fibonacci_generator(n: int) -> Iterator[int]:
    """費波那契數列生成器

    Args:
        n: 生成的數量

    Yields:
        int: 費波那契數
    """
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


async def async_fetch_data(url: str) -> dict:
    """異步獲取資料

    Args:
        url: 資料網址

    Returns:
        dict: 資料內容
    """
    # 模擬異步 I/O
    await asyncio.sleep(0.1)
    return {"url": url, "status": "success"}


async def async_process_batch(items: List[str]) -> List[str]:
    """異步批次處理

    Args:
        items: 要處理的項目列表

    Returns:
        List[str]: 處理結果
    """
    tasks = [async_fetch_data(item) for item in items]
    results = await asyncio.gather(*tasks)
    return [r.get('status', 'unknown') for r in results]


def cache_result(func):
    """快取裝飾器

    Args:
        func: 要裝飾的函數

    Returns:
        裝飾後的函數
    """
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


@cache_result
def expensive_calculation(x: int, y: int) -> int:
    """耗時計算（帶快取裝飾器）

    Args:
        x: 第一個數字
        y: 第二個數字

    Returns:
        int: 計算結果
    """
    # 模擬耗時計算
    result = 0
    for i in range(x):
        for j in range(y):
            result += i * j
    return result


class ContextProcessor:
    """上下文管理器範例"""

    def __init__(self, name: str):
        self.name = name
        self.is_open = False

    def __enter__(self):
        """進入上下文"""
        self.is_open = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        self.is_open = False
        return False

    def process(self, data: str) -> str:
        """處理資料

        Args:
            data: 輸入資料

        Returns:
            str: 處理結果
        """
        if not self.is_open:
            raise RuntimeError("Context not opened")
        return f"{self.name}: {data}"
