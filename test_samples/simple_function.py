#!/usr/bin/env python3
"""簡單函數測試範例 - 1-2 個參數，明確返回值"""


def add(a: int, b: int) -> int:
    """加法運算

    Args:
        a: 第一個數字
        b: 第二個數字

    Returns:
        int: 兩數之和
    """
    return a + b


def greet(name: str) -> str:
    """生成問候語

    Args:
        name: 姓名

    Returns:
        str: 問候訊息
    """
    return f"Hello, {name}!"


def is_even(number: int) -> bool:
    """檢查數字是否為偶數

    Args:
        number: 要檢查的數字

    Returns:
        bool: True 如果是偶數，否則 False
    """
    return number % 2 == 0
