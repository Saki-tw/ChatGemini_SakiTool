#!/usr/bin/env python3
"""
增強型批次處理器
新增功能：
1. 任務依賴管理（DAG）
2. 任務分組
3. 自訂重試策略（指數退避、固定延遲等）
"""
import os
import json
import time
import threading
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod
import logging

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


# ==================== 任務狀態與資料結構 ====================

class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "待處理"
    WAITING_DEPENDENCIES = "等待依賴"
    RUNNING = "執行中"
    COMPLETED = "已完成"
    FAILED = "失敗"
    CANCELLED = "已取消"
    PAUSED = "已暫停"


class TaskPriority(Enum):
    """任務優先級"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


# ==================== 重試策略 ====================

class RetryStrategy(ABC):
    """重試策略基類"""

    @abstractmethod
    def get_delay(self, retry_count: int) -> float:
        """
        獲取重試延遲時間

        Args:
            retry_count: 當前重試次數（從 1 開始）

        Returns:
            延遲秒數
        """
        pass

    @abstractmethod
    def should_retry(self, retry_count: int, max_retries: int, error: Exception) -> bool:
        """
        判斷是否應該重試

        Args:
            retry_count: 當前重試次數
            max_retries: 最大重試次數
            error: 異常資訊

        Returns:
            是否應該重試
        """
        pass


class FixedDelayRetry(RetryStrategy):
    """固定延遲重試策略"""

    def __init__(self, delay: float = 1.0):
        """
        Args:
            delay: 固定延遲秒數
        """
        self.delay = delay

    def get_delay(self, retry_count: int) -> float:
        return self.delay

    def should_retry(self, retry_count: int, max_retries: int, error: Exception) -> bool:
        return retry_count < max_retries


class ExponentialBackoffRetry(RetryStrategy):
    """指數退避重試策略"""

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0
    ):
        """
        Args:
            base_delay: 基礎延遲秒數
            max_delay: 最大延遲秒數
            multiplier: 指數倍增因子
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier

    def get_delay(self, retry_count: int) -> float:
        """計算指數退避延遲：delay = base_delay * (multiplier ^ (retry_count - 1))"""
        delay = self.base_delay * (self.multiplier ** (retry_count - 1))
        return min(delay, self.max_delay)

    def should_retry(self, retry_count: int, max_retries: int, error: Exception) -> bool:
        return retry_count < max_retries


class LinearBackoffRetry(RetryStrategy):
    """線性退避重試策略"""

    def __init__(
        self,
        base_delay: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 30.0
    ):
        """
        Args:
            base_delay: 基礎延遲秒數
            increment: 每次增加的延遲秒數
            max_delay: 最大延遲秒數
        """
        self.base_delay = base_delay
        self.increment = increment
        self.max_delay = max_delay

    def get_delay(self, retry_count: int) -> float:
        """計算線性退避延遲：delay = base_delay + increment * (retry_count - 1)"""
        delay = self.base_delay + self.increment * (retry_count - 1)
        return min(delay, self.max_delay)

    def should_retry(self, retry_count: int, max_retries: int, error: Exception) -> bool:
        return retry_count < max_retries


class CustomRetry(RetryStrategy):
    """自訂重試策略"""

    def __init__(
        self,
        delay_func: Callable[[int], float],
        should_retry_func: Optional[Callable[[int, int, Exception], bool]] = None
    ):
        """
        Args:
            delay_func: 自訂延遲函數，接收 retry_count，返回延遲秒數
            should_retry_func: 自訂重試判斷函數（可選）
        """
        self.delay_func = delay_func
        self.should_retry_func = should_retry_func

    def get_delay(self, retry_count: int) -> float:
        return self.delay_func(retry_count)

    def should_retry(self, retry_count: int, max_retries: int, error: Exception) -> bool:
        if self.should_retry_func:
            return self.should_retry_func(retry_count, max_retries, error)
        return retry_count < max_retries


# ==================== 批次任務 ====================

@dataclass
class EnhancedBatchTask:
    """增強型批次任務資料結構"""
    task_id: str
    task_type: str              # 'flow_generation', 'veo_generation', etc.
    parameters: Dict[str, Any]  # 任務參數

    # 基本屬性
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING

    # 時間追蹤
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # 結果與錯誤
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # 重試設定
    retry_count: int = 0
    max_retries: int = 3
    retry_strategy: Optional[RetryStrategy] = None

    # 依賴管理（新增）
    dependencies: List[str] = field(default_factory=list)  # 依賴的任務 ID
    dependents: List[str] = field(default_factory=list)    # 依賴此任務的任務 ID

    # 分組管理（新增）
    group_id: Optional[str] = None

    # 元數據
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

        # 設定預設重試策略
        if self.retry_strategy is None:
            self.retry_strategy = FixedDelayRetry(delay=1.0)


# ==================== 任務分組 ====================

@dataclass
class TaskGroup:
    """任務分組"""
    group_id: str
    name: str
    description: str = ""

    # 群組內任務
    task_ids: List[str] = field(default_factory=list)

    # 群組狀態
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""

    # 群組設定
    priority: TaskPriority = TaskPriority.MEDIUM
    max_concurrent: int = 3  # 群組內最大並行任務數

    # 依賴管理（群組間依賴）
    dependencies: List[str] = field(default_factory=list)  # 依賴的群組 ID

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


# ==================== 增強型批次處理器 ====================

class EnhancedBatchProcessor:
    """增強型批次處理器"""

    def __init__(
        self,
        max_concurrent: int = 3,
        storage_dir: Optional[str] = None,
        console: Optional[Any] = None
    ):
        """
        初始化增強型批次處理器

        Args:
            max_concurrent: 最大並行任務數
            storage_dir: 任務存儲目錄
            console: Rich Console 實例（可選）
        """
        self.max_concurrent = max_concurrent
        self.storage_dir = Path(storage_dir) if storage_dir else Path.home() / ".batch_processor"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Console 設定
        if RICH_AVAILABLE:
            self.console = console or Console()
        else:
            self.console = None

        # 任務與群組
        self.tasks: Dict[str, EnhancedBatchTask] = {}
        self.groups: Dict[str, TaskGroup] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.task_handlers: Dict[str, Callable] = {}

        # 控制標誌
        self._paused = False
        self._stop_requested = False

        # 載入已存在的任務與群組
        self._load_state()

        logger.info("✓ EnhancedBatchProcessor 已初始化")

    # ==================== 狀態管理 ====================

    def _load_state(self):
        """載入保存的任務與群組"""
        # 載入任務
        tasks_file = self.storage_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        # 處理 Enum 和策略
                        task_data['priority'] = TaskPriority[task_data['priority']] if isinstance(task_data['priority'], str) else task_data['priority']
                        task_data['status'] = TaskStatus[task_data['status']] if isinstance(task_data['status'], str) else task_data['status']

                        # 重建重試策略（暫時使用預設）
                        task_data.pop('retry_strategy', None)

                        task = EnhancedBatchTask(**task_data)
                        self.tasks[task.task_id] = task

                self._print(f"[cyan]📂 載入了 {len(self.tasks)} 個任務[/cyan]")
            except Exception as e:
                self._print(f"[yellow]載入任務失敗：{e}[/yellow]")

        # 載入群組
        groups_file = self.storage_dir / "groups.json"
        if groups_file.exists():
            try:
                with open(groups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for group_data in data.get('groups', []):
                        group_data['priority'] = TaskPriority[group_data['priority']] if isinstance(group_data['priority'], str) else group_data['priority']
                        group_data['status'] = TaskStatus[group_data['status']] if isinstance(group_data['status'], str) else group_data['status']

                        group = TaskGroup(**group_data)
                        self.groups[group.group_id] = group

                self._print(f"[cyan]📂 載入了 {len(self.groups)} 個任務群組[/cyan]")
            except Exception as e:
                self._print(f"[yellow]載入群組失敗：{e}[/yellow]")

    def _save_state(self):
        """保存任務與群組到檔案"""
        # 保存任務
        tasks_file = self.storage_dir / "tasks.json"
        try:
            data = {
                'tasks': [
                    {
                        **asdict(task),
                        'priority': task.priority.name,
                        'status': task.status.name,
                        'retry_strategy': None  # 策略物件無法序列化，儲存為 None
                    }
                    for task in self.tasks.values()
                ]
            }
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._print(f"[red]保存任務失敗：{e}[/red]")

        # 保存群組
        groups_file = self.storage_dir / "groups.json"
        try:
            data = {
                'groups': [
                    {
                        **asdict(group),
                        'priority': group.priority.name,
                        'status': group.status.name
                    }
                    for group in self.groups.values()
                ]
            }
            with open(groups_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._print(f"[red]保存群組失敗：{e}[/red]")

    def _print(self, message: str):
        """統一的輸出方法"""
        if self.console:
            self.console.print(message)
        else:
            # 移除 Rich 標記
            import re
            clean_message = re.sub(r'\[.*?\]', '', message)
            print(clean_message)

    # ==================== 任務處理器註冊 ====================

    def register_handler(self, task_type: str, handler: Callable):
        """
        註冊任務處理器

        Args:
            task_type: 任務類型
            handler: 處理函數，接收參數並返回結果
        """
        self.task_handlers[task_type] = handler
        self._print(f"[green]✓ 註冊任務處理器：{task_type}[/green]")

    # ==================== 任務管理 ====================

    def add_task(
        self,
        task_type: str,
        parameters: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        task_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        group_id: Optional[str] = None,
        max_retries: int = 3,
        retry_strategy: Optional[RetryStrategy] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加任務到批次佇列

        Args:
            task_type: 任務類型
            parameters: 任務參數
            priority: 優先級
            task_id: 任務 ID（可選，自動生成）
            dependencies: 依賴的任務 ID 列表
            group_id: 所屬群組 ID
            max_retries: 最大重試次數
            retry_strategy: 重試策略
            metadata: 額外元數據

        Returns:
            任務 ID
        """
        if task_id is None:
            task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        task = EnhancedBatchTask(
            task_id=task_id,
            task_type=task_type,
            parameters=parameters,
            priority=priority,
            dependencies=dependencies or [],
            group_id=group_id,
            max_retries=max_retries,
            retry_strategy=retry_strategy or FixedDelayRetry(),
            metadata=metadata or {}
        )

        # 檢查依賴的任務是否存在
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                raise ValueError(f"依賴的任務不存在：{dep_id}")
            # 更新依賴任務的 dependents
            self.tasks[dep_id].dependents.append(task_id)

        # 如果有依賴，設定狀態為等待依賴
        if task.dependencies:
            task.status = TaskStatus.WAITING_DEPENDENCIES

        self.tasks[task_id] = task

        # 如果指定了群組，添加到群組
        if group_id and group_id in self.groups:
            self.groups[group_id].task_ids.append(task_id)

        self._save_state()
        self._print(f"[green]✓ 已添加任務：{task_id}[/green]")

        return task_id

    def add_tasks_batch(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        批次添加多個任務

        Args:
            tasks: 任務列表

        Returns:
            任務 ID 列表
        """
        task_ids = []
        for task_data in tasks:
            task_id = self.add_task(
                task_type=task_data.get('task_type'),
                parameters=task_data.get('parameters', {}),
                priority=task_data.get('priority', TaskPriority.MEDIUM),
                dependencies=task_data.get('dependencies'),
                group_id=task_data.get('group_id'),
                max_retries=task_data.get('max_retries', 3),
                retry_strategy=task_data.get('retry_strategy'),
                metadata=task_data.get('metadata')
            )
            task_ids.append(task_id)

        self._print(f"[green]✓ 已批次添加 {len(task_ids)} 個任務[/green]")
        return task_ids

    # ==================== 任務分組管理 ====================

    def create_group(
        self,
        name: str,
        description: str = "",
        group_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        max_concurrent: int = 3,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        建立任務分組

        Args:
            name: 群組名稱
            description: 群組描述
            group_id: 群組 ID（可選）
            priority: 群組優先級
            max_concurrent: 群組內最大並行任務數
            dependencies: 依賴的群組 ID 列表

        Returns:
            群組 ID
        """
        if group_id is None:
            group_id = f"group_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        group = TaskGroup(
            group_id=group_id,
            name=name,
            description=description,
            priority=priority,
            max_concurrent=max_concurrent,
            dependencies=dependencies or []
        )

        self.groups[group_id] = group
        self._save_state()

        self._print(f"[green]✓ 已建立任務群組：{group_id}[/green]")
        return group_id

    def add_task_to_group(self, task_id: str, group_id: str):
        """將任務添加到群組"""
        if task_id not in self.tasks:
            raise ValueError(f"任務不存在：{task_id}")
        if group_id not in self.groups:
            raise ValueError(f"群組不存在：{group_id}")

        self.tasks[task_id].group_id = group_id
        if task_id not in self.groups[group_id].task_ids:
            self.groups[group_id].task_ids.append(task_id)

        self._save_state()
        self._print(f"[green]✓ 已將任務 {task_id} 添加到群組 {group_id}[/green]")

    def get_group_tasks(self, group_id: str) -> List[EnhancedBatchTask]:
        """獲取群組內的所有任務"""
        if group_id not in self.groups:
            return []

        return [
            self.tasks[task_id]
            for task_id in self.groups[group_id].task_ids
            if task_id in self.tasks
        ]

    def pause_group(self, group_id: str):
        """暫停群組內的所有任務"""
        if group_id not in self.groups:
            raise ValueError(f"群組不存在：{group_id}")

        for task_id in self.groups[group_id].task_ids:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == TaskStatus.PENDING or task.status == TaskStatus.WAITING_DEPENDENCIES:
                    task.status = TaskStatus.PAUSED

        self.groups[group_id].status = TaskStatus.PAUSED
        self._save_state()
        self._print(f"[yellow]⏸️  已暫停群組：{group_id}[/yellow]")

    def resume_group(self, group_id: str):
        """恢復群組內的所有任務"""
        if group_id not in self.groups:
            raise ValueError(f"群組不存在：{group_id}")

        for task_id in self.groups[group_id].task_ids:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == TaskStatus.PAUSED:
                    # 恢復為適當的狀態
                    if task.dependencies:
                        task.status = TaskStatus.WAITING_DEPENDENCIES
                    else:
                        task.status = TaskStatus.PENDING

        self.groups[group_id].status = TaskStatus.PENDING
        self._save_state()
        self._print(f"[green]▶️  已恢復群組：{group_id}[/green]")

    def cancel_group(self, group_id: str):
        """取消群組內的所有任務"""
        if group_id not in self.groups:
            raise ValueError(f"群組不存在：{group_id}")

        cancelled_count = 0
        for task_id in self.groups[group_id].task_ids:
            if self.cancel_task(task_id):
                cancelled_count += 1

        self.groups[group_id].status = TaskStatus.CANCELLED
        self._save_state()
        self._print(f"[red]🚫 已取消群組 {group_id}（{cancelled_count} 個任務）[/red]")

    # ==================== 依賴管理 ====================

    def _check_dependencies_satisfied(self, task: EnhancedBatchTask) -> bool:
        """檢查任務的所有依賴是否已完成"""
        if not task.dependencies:
            return True

        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False

        return True

    def _update_dependent_tasks(self, task_id: str):
        """當任務完成時，更新依賴此任務的其他任務狀態"""
        task = self.tasks.get(task_id)
        if not task:
            return

        for dependent_id in task.dependents:
            dependent = self.tasks.get(dependent_id)
            if dependent and dependent.status == TaskStatus.WAITING_DEPENDENCIES:
                if self._check_dependencies_satisfied(dependent):
                    dependent.status = TaskStatus.PENDING
                    self._print(f"[cyan]🔓 任務 {dependent_id} 的依賴已滿足，設為待處理[/cyan]")

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """獲取任務依賴圖"""
        graph = {}
        for task_id, task in self.tasks.items():
            graph[task_id] = task.dependencies.copy()
        return graph

    def _topological_sort(self) -> List[str]:
        """拓撲排序，返回任務執行順序"""
        # 構建入度表
        in_degree = {task_id: len(task.dependencies) for task_id, task in self.tasks.items()}

        # 找出入度為 0 的任務
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # 取出入度為 0 的任務（按優先級排序）
            queue.sort(key=lambda tid: self.tasks[tid].priority.value, reverse=True)
            task_id = queue.pop(0)
            result.append(task_id)

            # 更新依賴此任務的其他任務的入度
            task = self.tasks[task_id]
            for dependent_id in task.dependents:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # 檢查是否有循環依賴
        if len(result) != len(self.tasks):
            raise ValueError("檢測到循環依賴！")

        return result

    # ==================== 任務執行 ====================

    def _execute_task(self, task: EnhancedBatchTask):
        """執行單個任務（在獨立執行緒中）"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        self._save_state()

        try:
            # 獲取任務處理器
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"未找到任務處理器：{task.task_type}")

            # 執行任務
            self._print(f"\n[cyan]▶️  開始執行任務：{task.task_id}[/cyan]")
            result = handler(**task.parameters)

            # 標記完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result if isinstance(result, dict) else {'output': str(result)}

            self._print(f"[green]✅ 任務完成：{task.task_id}[/green]")

            # 更新依賴此任務的其他任務
            self._update_dependent_tasks(task.task_id)

        except Exception as e:
            self._print(f"[red]❌ 任務失敗：{task.task_id} - {e}[/red]")

            # 使用重試策略判斷是否重試
            if task.retry_strategy.should_retry(task.retry_count + 1, task.max_retries, e):
                task.retry_count += 1
                delay = task.retry_strategy.get_delay(task.retry_count)

                self._print(f"[yellow]🔄 將在 {delay:.1f} 秒後重試任務 ({task.retry_count}/{task.max_retries})：{task.task_id}[/yellow]")

                # 延遲後設回待處理
                time.sleep(delay)
                task.status = TaskStatus.PENDING
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now().isoformat()

        finally:
            self._save_state()
            # 從運行任務中移除
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]

    def start(self, blocking: bool = True):
        """
        開始執行批次任務

        Args:
            blocking: 是否阻塞直到所有任務完成
        """
        self._print(f"\n[bold cyan]🚀 開始批次處理（最大並行：{self.max_concurrent}）[/bold cyan]\n")

        if blocking:
            self._run_blocking()
        else:
            threading.Thread(target=self._run_blocking, daemon=True).start()

    def _run_blocking(self):
        """阻塞式執行所有任務"""
        # 計算待處理任務
        pending_tasks = [
            t for t in self.tasks.values()
            if t.status in [TaskStatus.PENDING, TaskStatus.WAITING_DEPENDENCIES]
        ]
        total_tasks = len(pending_tasks)

        if total_tasks == 0:
            self._print("[yellow]沒有待處理的任務[/yellow]")
            return

        completed = 0

        if RICH_AVAILABLE and self.console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            ) as progress:
                progress_task = progress.add_task(
                    f"處理 {total_tasks} 個任務",
                    total=total_tasks
                )

                completed = self._run_task_loop(progress, progress_task, total_tasks)
        else:
            completed = self._run_task_loop(None, None, total_tasks)

        self._print(f"\n[bold green]✅ 批次處理完成！（完成 {completed}/{total_tasks} 個任務）[/bold green]")
        self.display_summary()

    def _run_task_loop(self, progress, progress_task, total_tasks) -> int:
        """任務執行循環"""
        completed = 0

        while completed < total_tasks and not self._stop_requested:
            if self._paused:
                time.sleep(1)
                continue

            # 獲取可執行的任務（依賴已滿足且狀態為 PENDING）
            executable_tasks = [
                t for t in self.tasks.values()
                if t.status == TaskStatus.PENDING and self._check_dependencies_satisfied(t)
            ]

            # 按優先級排序
            executable_tasks.sort(key=lambda x: x.priority.value, reverse=True)

            # 啟動新任務（不超過並行限制）
            while len(self.running_tasks) < self.max_concurrent and executable_tasks:
                task = executable_tasks.pop(0)
                thread = threading.Thread(target=self._execute_task, args=(task,))
                thread.start()
                self.running_tasks[task.task_id] = thread

            # 檢查完成的任務
            for task_id, thread in list(self.running_tasks.items()):
                if not thread.is_alive():
                    thread.join()
                    # 檢查任務狀態
                    task = self.tasks.get(task_id)
                    if task and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        completed += 1
                        if progress and progress_task is not None:
                            progress.update(progress_task, completed=completed)

            # 短暫休眠避免過度消耗 CPU
            time.sleep(0.5)

        return completed

    # ==================== 任務控制 ====================

    def pause(self):
        """暫停批次處理（不影響正在執行的任務）"""
        self._paused = True
        self._print("[yellow]⏸️  批次處理已暫停[/yellow]")

    def resume(self):
        """恢復批次處理"""
        self._paused = False
        self._print("[green]▶️  批次處理已恢復[/green]")

    def stop(self):
        """停止批次處理"""
        self._stop_requested = True
        self._print("[red]⏹️  批次處理已停止[/red]")

    def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        task = self.tasks.get(task_id)
        if not task:
            self._print(f"[red]未找到任務：{task_id}[/red]")
            return False

        if task.status == TaskStatus.RUNNING:
            self._print(f"[yellow]無法取消正在執行的任務：{task_id}[/yellow]")
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now().isoformat()
        self._save_state()

        self._print(f"[green]✓ 已取消任務：{task_id}[/green]")
        return True

    # ==================== 查詢與顯示 ====================

    def get_task(self, task_id: str) -> Optional[EnhancedBatchTask]:
        """獲取任務資訊"""
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        group_id: Optional[str] = None
    ) -> List[EnhancedBatchTask]:
        """列出任務"""
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        if group_id:
            tasks = [t for t in tasks if t.group_id == group_id]

        return tasks

    def display_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        group_id: Optional[str] = None
    ):
        """顯示任務列表"""
        tasks = self.list_tasks(status=status, task_type=task_type, group_id=group_id)

        if not tasks:
            self._print("[yellow]沒有符合條件的任務[/yellow]")
            return

        if RICH_AVAILABLE and self.console:
            table = Table(title=f"批次任務列表（共 {len(tasks)} 個）")
            table.add_column("任務 ID", style="cyan", no_wrap=True)
            table.add_column("類型", style="green")
            table.add_column("狀態", style="yellow")
            table.add_column("優先級", style="magenta")
            table.add_column("群組", style="blue")
            table.add_column("依賴", style="dim")
            table.add_column("重試", style="red")

            for task in tasks:
                status_emoji = {
                    TaskStatus.PENDING: "⏸️",
                    TaskStatus.WAITING_DEPENDENCIES: "⏳",
                    TaskStatus.RUNNING: "▶️",
                    TaskStatus.COMPLETED: "✅",
                    TaskStatus.FAILED: "❌",
                    TaskStatus.CANCELLED: "🚫",
                    TaskStatus.PAUSED: "⏸️"
                }.get(task.status, "")

                table.add_row(
                    task.task_id[:25] + "..." if len(task.task_id) > 25 else task.task_id,
                    task.task_type,
                    f"{status_emoji} {task.status.value}",
                    task.priority.name,
                    task.group_id or "-",
                    str(len(task.dependencies)),
                    f"{task.retry_count}/{task.max_retries}"
                )

            self.console.print(table)
        else:
            # 純文字輸出
            print(f"\n批次任務列表（共 {len(tasks)} 個）")
            print("-" * 80)
            for task in tasks:
                print(f"ID: {task.task_id}")
                print(f"  類型: {task.task_type}")
                print(f"  狀態: {task.status.value}")
                print(f"  優先級: {task.priority.name}")
                print(f"  群組: {task.group_id or '-'}")
                print(f"  依賴數: {len(task.dependencies)}")
                print(f"  重試: {task.retry_count}/{task.max_retries}")
                print("-" * 80)

    def display_groups(self):
        """顯示任務群組列表"""
        if not self.groups:
            self._print("[yellow]沒有任務群組[/yellow]")
            return

        if RICH_AVAILABLE and self.console:
            table = Table(title=f"任務群組列表（共 {len(self.groups)} 個）")
            table.add_column("群組 ID", style="cyan")
            table.add_column("名稱", style="green")
            table.add_column("描述", style="dim")
            table.add_column("任務數", style="yellow")
            table.add_column("狀態", style="magenta")
            table.add_column("優先級", style="blue")

            for group in self.groups.values():
                table.add_row(
                    group.group_id,
                    group.name,
                    group.description[:30] + "..." if len(group.description) > 30 else group.description,
                    str(len(group.task_ids)),
                    group.status.value,
                    group.priority.name
                )

            self.console.print(table)
        else:
            # 純文字輸出
            print(f"\n任務群組列表（共 {len(self.groups)} 個）")
            print("-" * 80)
            for group in self.groups.values():
                print(f"ID: {group.group_id}")
                print(f"  名稱: {group.name}")
                print(f"  任務數: {len(group.task_ids)}")
                print(f"  狀態: {group.status.value}")
                print("-" * 80)

    def display_summary(self):
        """顯示任務統計摘要"""
        stats = {status: 0 for status in TaskStatus}

        for task in self.tasks.values():
            stats[task.status] = stats.get(task.status, 0) + 1

        summary_text = f"""
[bold cyan]批次任務統計[/bold cyan]

  總任務數：{len(self.tasks)}
  ✅ 已完成：{stats[TaskStatus.COMPLETED]}
  ▶️  執行中：{stats[TaskStatus.RUNNING]}
  ⏸️  待處理：{stats[TaskStatus.PENDING]}
  ⏳ 等待依賴：{stats[TaskStatus.WAITING_DEPENDENCIES]}
  ⏸️  已暫停：{stats[TaskStatus.PAUSED]}
  ❌ 失敗：{stats[TaskStatus.FAILED]}
  🚫 已取消：{stats[TaskStatus.CANCELLED]}

  總群組數：{len(self.groups)}
        """

        if RICH_AVAILABLE and self.console:
            self.console.print(Panel(summary_text, border_style="cyan"))
        else:
            print(summary_text)

    def clear_completed(self):
        """清理已完成的任務"""
        completed_ids = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]

        for task_id in completed_ids:
            del self.tasks[task_id]

        self._save_state()
        self._print(f"[green]✓ 已清理 {len(completed_ids)} 個已完成的任務[/green]")


# ==================== 工具函數 ====================

def create_retry_strategy(
    strategy_type: str = "fixed",
    **kwargs
) -> RetryStrategy:
    """
    建立重試策略的工廠函數

    Args:
        strategy_type: 策略類型 ('fixed', 'exponential', 'linear', 'custom')
        **kwargs: 策略參數

    Returns:
        RetryStrategy 實例
    """
    if strategy_type == "fixed":
        return FixedDelayRetry(delay=kwargs.get('delay', 1.0))

    elif strategy_type == "exponential":
        return ExponentialBackoffRetry(
            base_delay=kwargs.get('base_delay', 1.0),
            max_delay=kwargs.get('max_delay', 60.0),
            multiplier=kwargs.get('multiplier', 2.0)
        )

    elif strategy_type == "linear":
        return LinearBackoffRetry(
            base_delay=kwargs.get('base_delay', 1.0),
            increment=kwargs.get('increment', 1.0),
            max_delay=kwargs.get('max_delay', 30.0)
        )

    elif strategy_type == "custom":
        delay_func = kwargs.get('delay_func')
        should_retry_func = kwargs.get('should_retry_func')
        if not delay_func:
            raise ValueError("custom 策略需要提供 delay_func")
        return CustomRetry(delay_func, should_retry_func)

    else:
        raise ValueError(f"未知的策略類型：{strategy_type}")
