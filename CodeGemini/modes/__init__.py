#!/usr/bin/env python3
"""
CodeGemini Modes Module (TESTING ONLY)
模式系統 - 提供不同的操作模式（僅供測試使用）

⚠️ 注意：此模組化版本僅供獨立測試使用
主要實作位於專案根目錄的 CodeGemini.py

模組：
- plan_mode: 規劃模式（Plan Mode）
- todo_tracker: 任務追蹤（Todo Tracking）- 包含 Rich 視覺化用於測試
- interactive_qa: 互動式問答（Interactive Q&A）- 包含 Rich 視覺化用於測試
"""

from .plan_mode import PlanMode, Plan
from .todo_tracker import TodoTracker, Todo, TodoStatus
from .interactive_qa import InteractiveQA

__all__ = ['PlanMode', 'Plan', 'TodoTracker', 'Todo', 'TodoStatus', 'InteractiveQA']
