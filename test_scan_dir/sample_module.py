#!/usr/bin/env python3
"""
範例模組 - 用於測試批次處理功能
"""

def add(a, b):
    """加法函數"""
    return a + b

def subtract(a, b):
    """減法函數"""
    return a - b

def multiply(a, b):
    """乘法函數"""
    return a * b

def __private_function():
    """私有函數 - 應被過濾"""
    pass

class Calculator:
    """計算機類別"""

    def __init__(self):
        """初始化"""
        self.result = 0

    def add(self, value):
        """加法方法"""
        self.result += value
        return self.result

    def reset(self):
        """重置"""
        self.result = 0

    def __internal_method(self):
        """私有方法 - 應被過濾"""
        pass
