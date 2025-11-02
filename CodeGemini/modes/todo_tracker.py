#!/usr/bin/env python3
"""
CodeGemini Todo Tracker Module
任務追蹤模組 - 提供任務管理和進度追蹤

此模組負責：
1. 新增任務（Todo）
2. 更新任務狀態（pending/in_progress/completed）
3. 追蹤任務進度
4. 顯示任務列表
5. 支援 activeForm（進行中形式）
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

# 確保可以 import utils
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.i18n import safe_t

console = Console()


class TodoStatus(str, Enum):
    """任務狀態"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class Todo:
    """任務"""
    content: str  # 任務內容（祈使句形式）
    active_form: str  # 進行中形式（現在進行式）
    status: TodoStatus = TodoStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    index: int = 0  # 任務索引

    def mark_in_progress(self) -> None:
        """標記為進行中"""
        self.status = TodoStatus.IN_PROGRESS
        if not self.started_at:
            self.started_at = datetime.now()

    def mark_completed(self) -> None:
        """標記為已完成"""
        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now()

    @property
    def is_pending(self) -> bool:
        """是否待處理"""
        return self.status == TodoStatus.PENDING

    @property
    def is_in_progress(self) -> bool:
        """是否進行中"""
        return self.status == TodoStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == TodoStatus.COMPLETED

    @property
    def display_text(self) -> str:
        """顯示文字（根據狀態選擇）"""
        if self.is_in_progress:
            return self.active_form
        return self.content


class TodoTracker:
    """
    任務追蹤器

    提供類似 Claude Code TodoWrite 的功能：
    - 追蹤任務狀態
    - 實時進度顯示
    - 確保同一時間只有一個 in_progress 任務
    - 支援任務的新增、更新、刪除
    """

    def __init__(self):
        """初始化任務追蹤器"""
        self.todos: List[Todo] = []
        self._index_counter = 0

        console.print(safe_t('codegemini.todo.initialized', fallback="[dim]TodoTracker 初始化完成[/dim]"))

    def add_todo(
        self,
        content: str,
        active_form: str,
        status: TodoStatus = TodoStatus.PENDING
    ) -> Todo:
        """
        新增任務

        Args:
            content: 任務內容（祈使句，如：「實作功能」）
            active_form: 進行中形式（現在進行式，如：「實作功能中」）
            status: 初始狀態

        Returns:
            Todo: 新增的任務
        """
        self._index_counter += 1

        todo = Todo(
            content=content,
            active_form=active_form,
            status=status,
            index=self._index_counter
        )

        self.todos.append(todo)

        return todo

    def update_status(self, index: int, status: TodoStatus) -> bool:
        """
        更新任務狀態

        Args:
            index: 任務索引（從 1 開始）
            status: 新狀態

        Returns:
            bool: 是否成功更新
        """
        todo = self._get_todo_by_index(index)

        if not todo:
            console.print(safe_t('codegemini.todo.not_found', fallback="[dim #B565D8]✗ 任務不存在：#{index}[/red]", index=index))
            return False

        # 如果要設為 in_progress，檢查是否已有其他 in_progress 任務
        if status == TodoStatus.IN_PROGRESS:
            in_progress_todos = [t for t in self.todos if t.is_in_progress]
            if in_progress_todos:
                console.print(safe_t('codegemini.todo.already_in_progress', fallback="[#B565D8]⚠️  已有進行中的任務：{content}[/#B565D8]", content=in_progress_todos[0].content))
                # 自動將其標記為 completed
                in_progress_todos[0].mark_completed()

        # 更新狀態
        old_status = todo.status
        todo.status = status

        if status == TodoStatus.IN_PROGRESS:
            todo.mark_in_progress()
        elif status == TodoStatus.COMPLETED:
            todo.mark_completed()

        console.print(safe_t('codegemini.todo.status_updated', fallback="[#B565D8]✓ 任務 #{index} 狀態更新：{old} → {new}[/#B565D8]", index=index, old=old_status.value, new=status.value))

        return True

    def mark_in_progress(self, index: int) -> bool:
        """標記任務為進行中"""
        return self.update_status(index, TodoStatus.IN_PROGRESS)

    def mark_completed(self, index: int) -> bool:
        """標記任務為已完成"""
        return self.update_status(index, TodoStatus.COMPLETED)

    def get_todos(self) -> List[Todo]:
        """取得所有任務"""
        return self.todos.copy()

    def get_pending_todos(self) -> List[Todo]:
        """取得待處理任務"""
        return [t for t in self.todos if t.is_pending]

    def get_in_progress_todo(self) -> Optional[Todo]:
        """取得進行中的任務（應該只有一個）"""
        in_progress = [t for t in self.todos if t.is_in_progress]
        return in_progress[0] if in_progress else None

    def get_completed_todos(self) -> List[Todo]:
        """取得已完成任務"""
        return [t for t in self.todos if t.is_completed]

    def get_progress(self) -> Dict[str, Any]:
        """取得進度資訊"""
        total = len(self.todos)
        completed = len(self.get_completed_todos())
        in_progress = 1 if self.get_in_progress_todo() else 0
        pending = len(self.get_pending_todos())

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "progress_percentage": (completed / total * 100) if total > 0 else 0
        }

    def display_progress(self) -> None:
        """展示進度"""
        progress_info = self.get_progress()

        console.print(safe_t('codegemini.todo.progress_title', fallback="\n[bold]📊 任務進度[/bold]\n"))

        # 進度條
        total = progress_info["total"]
        completed = progress_info["completed"]
        percentage = progress_info["progress_percentage"]

        console.print(safe_t('codegemini.todo.total_tasks', fallback="總任務：{total}", total=total))
        console.print(safe_t('codegemini.todo.completed_tasks', fallback="已完成：[#B565D8]{completed}[/#B565D8]", completed=completed))
        console.print(safe_t('codegemini.todo.in_progress_tasks', fallback="進行中：[#B565D8]{count}[/#B565D8]", count=progress_info['in_progress']))
        console.print(safe_t('codegemini.todo.pending_tasks', fallback="待處理：[dim]{count}[/dim]", count=progress_info['pending']))
        console.print(safe_t('codegemini.todo.progress_percentage', fallback="進度：[#B565D8]{percentage:.1f}%[/#B565D8]", percentage=percentage))

        # 進度條視覺化
        bar_length = 50
        filled_length = int(bar_length * completed / total) if total > 0 else 0
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        console.print(safe_t('codegemini.todo.progress_bar', fallback="\n[#B565D8]{bar}[/#B565D8] {percentage:.0f}%\n", bar=bar, percentage=percentage))

    def display_todos(self, show_completed: bool = True) -> None:
        """
        展示任務列表

        Args:
            show_completed: 是否顯示已完成任務
        """
        if not self.todos:
            console.print(safe_t('codegemini.todo.no_tasks', fallback="[#B565D8]⚠️  無任務[/#B565D8]"))
            return

        console.print(safe_t('codegemini.todo.list_title', fallback="\n[bold]📋 任務列表[/bold]\n"))

        table = Table(show_header=True, header_style="bold #B565D8")
        console_width = console.width or 120
        table.add_column("#", style="dim", width=max(4, int(console_width * 0.03)))
        table.add_column(safe_t('codegemini.todo.status_column', fallback="狀態"), style="white", width=max(10, int(console_width * 0.12)))
        table.add_column(safe_t('codegemini.todo.task_column', fallback="任務"), style="white")

        for todo in self.todos:
            # 過濾已完成任務
            if not show_completed and todo.is_completed:
                continue

            # 狀態圖示
            if todo.is_completed:
                status_text = safe_t('codegemini.todo.status_completed', fallback="[#B565D8]✅ 完成[/#B565D8]")
            elif todo.is_in_progress:
                status_text = safe_t('codegemini.todo.status_in_progress', fallback="[#B565D8]⏳ 進行中[/#B565D8]")
            else:  # pending
                status_text = safe_t('codegemini.todo.status_pending', fallback="[dim]⏸️  待處理[/dim]")

            # 任務文字
            task_text = todo.display_text

            table.add_row(
                str(todo.index),
                status_text,
                task_text
            )

        console.print(table)

        # 顯示進度
        self.display_progress()

    def remove_todo(self, index: int) -> bool:
        """
        移除任務

        Args:
            index: 任務索引

        Returns:
            bool: 是否成功移除
        """
        todo = self._get_todo_by_index(index)

        if not todo:
            console.print(safe_t('codegemini.todo.not_found', fallback="[dim #B565D8]✗ 任務不存在：#{index}[/red]", index=index))
            return False

        self.todos.remove(todo)
        console.print(safe_t('codegemini.todo.removed', fallback="[#B565D8]✓ 任務 #{index} 已移除[/#B565D8]", index=index))

        return True

    def clear_completed(self) -> int:
        """清除已完成任務"""
        completed = self.get_completed_todos()
        count = len(completed)

        for todo in completed:
            self.todos.remove(todo)

        if count > 0:
            console.print(safe_t('codegemini.todo.cleared', fallback="[#B565D8]✓ 清除了 {count} 個已完成任務[/#B565D8]", count=count))

        return count

    def _get_todo_by_index(self, index: int) -> Optional[Todo]:
        """根據索引取得任務"""
        for todo in self.todos:
            if todo.index == index:
                return todo
        return None


# ==================== 命令列介面 ====================

def main():
    """Todo Tracker 命令列工具"""
    console.print(safe_t('codegemini.todo.demo_title', fallback="\n[bold #B565D8]CodeGemini Todo Tracker Demo[/bold #B565D8]\n"))

    tracker = TodoTracker()

    # 示例：新增任務
    console.print(safe_t('codegemini.todo.demo_add_tasks', fallback="[bold]新增任務...[/bold]"))
    tracker.add_todo(safe_t('codegemini.todo.demo_task1', fallback="實作 Web Search"), safe_t('codegemini.todo.demo_task1_active', fallback="實作 Web Search 中"))
    tracker.add_todo(safe_t('codegemini.todo.demo_task2', fallback="實作 Web Fetch"), safe_t('codegemini.todo.demo_task2_active', fallback="實作 Web Fetch 中"))
    tracker.add_todo(safe_t('codegemini.todo.demo_task3', fallback="實作 Background Shells"), safe_t('codegemini.todo.demo_task3_active', fallback="實作 Background Shells 中"))
    tracker.add_todo(safe_t('codegemini.todo.demo_task4', fallback="撰寫測試"), safe_t('codegemini.todo.demo_task4_active', fallback="撰寫測試中"))

    # 展示任務
    tracker.display_todos()

    # 標記第一個為進行中
    console.print(safe_t('codegemini.todo.demo_start_first', fallback="\n[bold]開始第一個任務...[/bold]"))
    tracker.mark_in_progress(1)
    tracker.display_todos(show_completed=False)

    # 完成第一個
    console.print(safe_t('codegemini.todo.demo_complete_first', fallback="\n[bold]完成第一個任務...[/bold]"))
    tracker.mark_completed(1)

    # 開始第二個
    tracker.mark_in_progress(2)
    tracker.display_todos(show_completed=False)


if __name__ == "__main__":
    main()
