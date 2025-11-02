#!/usr/bin/env python3
"""
Gemini 批次處理模組
支援批次影片生成、排程任務、進度追蹤
"""
import os
import json
import time
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from rich.console import Console
from utils.i18n import safe_t
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

console = Console()


# ==================== 任務狀態與資料結構 ====================

class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "待處理"
    RUNNING = "執行中"
    COMPLETED = "已完成"
    FAILED = "失敗"
    CANCELLED = "已取消"


class TaskPriority(Enum):
    """任務優先級"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class BatchTask:
    """批次任務資料結構"""
    task_id: str
    task_type: str              # 'flow_generation', 'veo_generation', 'subtitle_generation', etc.
    parameters: Dict[str, Any]  # 任務參數
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


# ==================== 批次處理器 ====================

class BatchProcessor:
    """批次處理器"""

    def __init__(
        self,
        max_concurrent: int = 3,
        storage_dir: Optional[str] = None
    ):
        """
        初始化批次處理器

        Args:
            max_concurrent: 最大並行任務數
            storage_dir: 任務存儲目錄（預設使用統一診斷目錄）
        """
        self.max_concurrent = max_concurrent
        if storage_dir is None:
            # 使用統一診斷目錄
            from utils.path_manager import get_diagnostics_dir
            self.storage_dir = get_diagnostics_dir('batch')
        else:
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.tasks: Dict[str, BatchTask] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.task_handlers: Dict[str, Callable] = {}

        # 載入已存在的任務
        self._load_tasks()

    def _load_tasks(self):
        """載入保存的任務"""
        tasks_file = self.storage_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        task = BatchTask(**task_data)
                        # 轉換 Enum
                        task.priority = TaskPriority[task.priority] if isinstance(task.priority, str) else task.priority
                        task.status = TaskStatus[task.status] if isinstance(task.status, str) else task.status
                        self.tasks[task.task_id] = task
                # 只在有任務時才顯示
                if len(self.tasks) > 0:
                    console.print(safe_t('common.loading', fallback='[#E8C4F0]📂 載入了 {tasks_count} 個任務[/#E8C4F0]', tasks_count=len(self.tasks)))
            except Exception as e:
                console.print(safe_t('error.failed', fallback='[#E8C4F0]載入任務失敗：{e}[/#E8C4F0]', e=e))

    def _save_tasks(self):
        """保存任務到檔案"""
        tasks_file = self.storage_dir / "tasks.json"
        try:
            data = {
                'tasks': [
                    {
                        **asdict(task),
                        'priority': task.priority.name,
                        'status': task.status.name
                    }
                    for task in self.tasks.values()
                ]
            }
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(safe_t('error.failed', fallback='[dim #E8C4F0]保存任務失敗：{e}[/red]', e=e))

    def register_handler(self, task_type: str, handler: Callable):
        """
        註冊任務處理器

        Args:
            task_type: 任務類型
            handler: 處理函數,接收參數並返回結果
        """
        self.task_handlers[task_type] = handler
        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 註冊任務處理器：{task_type}[/green]', task_type=task_type))

    def add_task(
        self,
        task_type: str,
        parameters: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        task_id: Optional[str] = None
    ) -> str:
        """
        添加任務到批次佇列

        Args:
            task_type: 任務類型
            parameters: 任務參數
            priority: 優先級
            task_id: 任務 ID（可選,自動生成）

        Returns:
            任務 ID
        """
        if task_id is None:
            task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        task = BatchTask(
            task_id=task_id,
            task_type=task_type,
            parameters=parameters,
            priority=priority
        )

        self.tasks[task_id] = task
        self._save_tasks()

        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 已添加任務：{task_id}[/green]', task_id=task_id))
        return task_id

    def add_tasks_batch(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        批次添加多個任務

        Args:
            tasks: 任務列表,每個任務包含 task_type, parameters, priority

        Returns:
            任務 ID 列表
        """
        task_ids = []
        for task_data in tasks:
            task_id = self.add_task(
                task_type=task_data.get('task_type'),
                parameters=task_data.get('parameters', {}),
                priority=task_data.get('priority', TaskPriority.MEDIUM)
            )
            task_ids.append(task_id)

        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 已批次添加 {len(task_ids)} 個任務[/green]', task_ids_count=len(task_ids)))
        return task_ids

    def _execute_task(self, task: BatchTask):
        """執行單個任務（在獨立執行緒中）"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        self._save_tasks()

        try:
            # 獲取任務處理器
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"未找到任務處理器：{task.task_type}")

            # 執行任務
            console.print(safe_t('common.message', fallback='\n[#E8C4F0]▶️  開始執行任務：{task.task_id}[/#E8C4F0]', task_id=task.task_id))
            result = handler(**task.parameters)

            # 標記完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result if isinstance(result, dict) else {'output': str(result)}

            console.print(safe_t('common.completed', fallback='[#B565D8]✅ 任務完成：{task.task_id}[/green]', task_id=task.task_id))

        except Exception as e:
            console.print(safe_t('error.failed', fallback='[dim #E8C4F0]❌ 任務失敗：{task.task_id} - {e}[/red]', task_id=task.task_id, e=e))

            # 重試邏輯
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                console.print(safe_t('common.message', fallback='[#E8C4F0]🔄 重試任務 ({task.retry_count}/{task.max_retries})：{task.task_id}[/#E8C4F0]', retry_count=task.retry_count, max_retries=task.max_retries, task_id=task.task_id))
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now().isoformat()

        finally:
            self._save_tasks()
            # 從運行任務中移除
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]

    def start(self, blocking: bool = True):
        """
        開始執行批次任務

        Args:
            blocking: 是否阻塞直到所有任務完成
        """
        console.print(safe_t('common.processing', fallback='\n[bold #E8C4F0]🚀 開始批次處理（最大並行：{self.max_concurrent}）[/bold #E8C4F0]\n', max_concurrent=self.max_concurrent))

        if blocking:
            self._run_blocking()
        else:
            threading.Thread(target=self._run_blocking, daemon=True).start()

    def _run_blocking(self):
        """阻塞式執行所有任務"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:

            # 計算總任務數
            pending_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
            total_tasks = len(pending_tasks)

            if total_tasks == 0:
                console.print(safe_t('common.processing', fallback='[#E8C4F0]沒有待處理的任務[/#E8C4F0]'))
                return

            progress_task = progress.add_task(
                f"處理 {total_tasks} 個任務",
                total=total_tasks
            )

            completed = 0

            while completed < total_tasks:
                # 獲取待處理任務（按優先級排序）
                pending_tasks = [
                    t for t in self.tasks.values()
                    if t.status == TaskStatus.PENDING
                ]
                pending_tasks.sort(key=lambda x: x.priority.value, reverse=True)

                # 啟動新任務（不超過並行限制）
                while len(self.running_tasks) < self.max_concurrent and pending_tasks:
                    task = pending_tasks.pop(0)
                    thread = threading.Thread(target=self._execute_task, args=(task,))
                    thread.start()
                    self.running_tasks[task.task_id] = thread

                # 等待任何任務完成
                for task_id, thread in list(self.running_tasks.items()):
                    if not thread.is_alive():
                        thread.join()
                        completed += 1
                        progress.update(progress_task, completed=completed)

                # 短暫休眠避免過度消耗 CPU
                time.sleep(0.5)

        console.print(safe_t('common.completed', fallback='\n[bold green]✅ 批次處理完成！[/bold green]'))
        self.display_summary()

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任務

        Args:
            task_id: 任務 ID

        Returns:
            是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task:
            console.print(safe_t('common.message', fallback='[dim #E8C4F0]未找到任務：{task_id}[/red]', task_id=task_id))
            return False

        if task.status == TaskStatus.RUNNING:
            console.print(safe_t('common.message', fallback='[#E8C4F0]無法取消正在執行的任務：{task_id}[/#E8C4F0]', task_id=task_id))
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now().isoformat()
        self._save_tasks()

        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 已取消任務：{task_id}[/green]', task_id=task_id))
        return True

    def get_task(self, task_id: str) -> Optional[BatchTask]:
        """獲取任務資訊"""
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None
    ) -> List[BatchTask]:
        """
        列出任務

        Args:
            status: 篩選狀態
            task_type: 篩選任務類型

        Returns:
            任務列表
        """
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        return tasks

    def display_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None
    ):
        """顯示任務列表"""
        tasks = self.list_tasks(status=status, task_type=task_type)

        if not tasks:
            # 靜默返回，不顯示訊息（避免噪音）
            return

        table = Table(title=f"批次任務列表（共 {len(tasks)} 個）")
        table.add_column("任務 ID", style="#B565D8")
        table.add_column("類型", style="green")
        table.add_column("狀態", style="#E8C4F0")
        table.add_column("優先級", style="#E8C4F0")
        table.add_column("建立時間", style="dim")
        table.add_column("重試次數", style="#E8C4F0")

        for task in tasks:
            status_emoji = {
                TaskStatus.PENDING: "⏸️",
                TaskStatus.RUNNING: "▶️",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.CANCELLED: "🚫"
            }.get(task.status, "")

            table.add_row(
                task.task_id[:30],
                task.task_type,
                f"{status_emoji} {task.status.value}",
                task.priority.name,
                task.created_at[:19],
                f"{task.retry_count}/{task.max_retries}"
            )

        console.print(table)

    def display_summary(self):
        """顯示任務統計摘要"""
        stats = {
            TaskStatus.PENDING: 0,
            TaskStatus.RUNNING: 0,
            TaskStatus.COMPLETED: 0,
            TaskStatus.FAILED: 0,
            TaskStatus.CANCELLED: 0
        }

        for task in self.tasks.values():
            stats[task.status] = stats.get(task.status, 0) + 1

        summary_text = f"""
[bold #E8C4F0]批次任務統計[/bold #E8C4F0]

  總任務數：{len(self.tasks)}
  ✅ 已完成：{stats[TaskStatus.COMPLETED]}
  ▶️  執行中：{stats[TaskStatus.RUNNING]}
  ⏸️  待處理：{stats[TaskStatus.PENDING]}
  ❌ 失敗：{stats[TaskStatus.FAILED]}
  🚫 已取消：{stats[TaskStatus.CANCELLED]}
        """

        console.print(Panel(summary_text, border_style="#B565D8"))

    def clear_completed(self):
        """清理已完成的任務"""
        completed_ids = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]

        for task_id in completed_ids:
            del self.tasks[task_id]

        self._save_tasks()
        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 已清理 {len(completed_ids)} 個已完成的任務[/green]', completed_ids_count=len(completed_ids)))


# ==================== 使用範例（僅供參考）====================

if __name__ == "__main__":
    # 範例：批次影片生成
    def example_video_generation(prompt: str, duration: int = 8) -> Dict[str, Any]:
        """範例影片生成函數"""
        console.print(safe_t('common.generating', fallback='生成影片：{prompt[:30]}... ({duration}秒)', prompt_short=prompt[:30], duration=duration))
        time.sleep(2)  # 模擬生成
        return {
            'video_path': f'/path/to/video_{prompt[:10]}.mp4',
            'duration': duration
        }

    # 創建批次處理器
    processor = BatchProcessor(max_concurrent=2)

    # 註冊處理器
    processor.register_handler('video_generation', example_video_generation)

    # 添加任務
    processor.add_task(
        task_type='video_generation',
        parameters={'prompt': 'A cat playing piano', 'duration': 8},
        priority=TaskPriority.HIGH
    )

    processor.add_task(
        task_type='video_generation',
        parameters={'prompt': 'A dog dancing', 'duration': 8},
        priority=TaskPriority.MEDIUM
    )

    processor.add_task(
        task_type='video_generation',
        parameters={'prompt': 'A bird singing', 'duration': 8},
        priority=TaskPriority.LOW
    )

    # 顯示任務
    processor.display_tasks()

    # 開始執行
    processor.start(blocking=True)
