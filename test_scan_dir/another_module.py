#!/usr/bin/env python3
"""
另一個範例模組
"""

def greet(name):
    """問候函數"""
    return f"Hello, {name}!"

def farewell(name):
    """告別函數"""
    return f"Goodbye, {name}!"

class Greeter:
    """問候者類別"""

    def say_hello(self, name):
        """說哈囉"""
        return f"Hello, {name}"

    def say_goodbye(self, name):
        """說再見"""
        return f"Goodbye, {name}"
