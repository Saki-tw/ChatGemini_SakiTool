#!/usr/bin/env python3
"""
Gemini 錯誤處理模組
提供統一的錯誤處理、重試機制、詳細錯誤訊息、失敗恢復功能

本模組提供:
- 6 種自定義異常類別(API、檔案、FFmpeg、網路、驗證錯誤)
- retry_on_error 裝飾器(指數退避 + 隨機抖動)
- RecoveryManager 失敗恢復管理
- ErrorLogger 錯誤日誌記錄
- ErrorFormatter 錯誤訊息格式化

設計原則:
- 統一的錯誤處理介面
- 詳細的錯誤上下文資訊
- 自動重試機制(避免驚群效應)
- 失敗恢復與checkpoint支援
"""
import os
import sys
import time
import json
import traceback
import functools
from typing import Optional, Callable, Any, Dict, List, Type, Tuple
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from utils.i18n import safe_t

console = Console()


# ============================================================================
# 錯誤類別定義
# ============================================================================
# 提供 6 種自定義異常,涵蓋影音處理的常見錯誤場景:
# - GeminiVideoError: 基礎錯誤類別
# - APIError: Gemini API 呼叫錯誤
# - FileProcessingError: 檔案讀寫、格式錯誤
# - FFmpegError: FFmpeg 命令執行失敗
# - NetworkError: 網路連接問題
# - ValidationError: 參數驗證失敗
# ============================================================================

class ErrorSeverity(Enum):
    """錯誤嚴重程度"""
    LOW = "low"          # 可忽略的警告
    MEDIUM = "medium"       # 需要注意但不影響主要功能
    HIGH = "high"         # 影響功能但可恢復
    CRITICAL = "critical"   # 致命錯誤,需要立即處理

    def localized(self) -> str:
        """返回本地化的嚴重程度名稱"""
        return safe_t(f'error.severity.{self.value}', fallback=self.value)


class GeminiVideoError(Exception):
    """
    Gemini 影音處理基礎錯誤類別

    所有自定義異常的基類,提供統一的錯誤資訊結構:
    - 嚴重程度分級
    - 錯誤原因鏈
    - 上下文資訊
    - 修復建議
    - 時間戳記
    """

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.message = message  # 錯誤訊息
        self.severity = severity  # 嚴重程度
        self.cause = cause  # 原始異常(如有)
        self.context = context or {}  # 上下文資訊(檔案路徑、參數等)
        self.suggestions = suggestions or []  # 修復建議列表
        self.timestamp = datetime.now()  # 發生時間

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'suggestions': self.suggestions,
            'cause': str(self.cause) if self.cause else None
        }


class APIError(GeminiVideoError):
    """API 相關錯誤"""

    def __init__(self, message: str, api_name: str = "Gemini", **kwargs):
        super().__init__(message, **kwargs)
        self.api_name = api_name
        self.context['api_name'] = api_name


class FileProcessingError(GeminiVideoError):
    """檔案處理錯誤"""

    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        if file_path:
            self.context['file_path'] = file_path


class FFmpegError(GeminiVideoError):
    """FFmpeg 相關錯誤"""

    def __init__(self, message: str, command: Optional[List[str]] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.command = command
        if command:
            self.context['command'] = ' '.join(command)


class NetworkError(GeminiVideoError):
    """網路相關錯誤"""

    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.url = url
        if url:
            self.context['url'] = url


class ValidationError(GeminiVideoError):
    """驗證錯誤"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, severity=ErrorSeverity.MEDIUM, **kwargs)
        self.field = field
        if field:
            self.context['field'] = field


# ============================================================================
# 錯誤訊息格式化器(Rich Formatting)
# ============================================================================
# 將錯誤轉換為美觀的 Rich 格式化輸出:
# - 彩色錯誤類型標示
# - 嚴重程度標記
# - 上下文資訊展示
# - 修復建議列表
# - 堆疊追蹤(可選)
# ============================================================================

class ErrorFormatter:
    """
    錯誤訊息格式化器

    使用 Rich 函式庫提供彩色、結構化的錯誤輸出,
    提升錯誤訊息的可讀性與除錯效率。
    """

    @staticmethod
    def format_error(
        error: Exception,
        show_traceback: bool = True,
        show_suggestions: bool = True
    ) -> str:
        """
        格式化錯誤訊息

        Args:
            error: 錯誤物件
            show_traceback: 是否顯示堆疊追蹤
            show_suggestions: 是否顯示建議

        Returns:
            格式化後的錯誤訊息
        """
        lines = []

        # === 第 1 部分:錯誤類型與基本訊息 ===
        error_type = error.__class__.__name__
        lines.append(f"[bold red]❌ {error_type}[/bold red]")
        lines.append(f"[red]{str(error)}[/red]")

        # === 第 2 部分:自訂錯誤的額外資訊 ===
        # 只有繼承自 GeminiVideoError 的異常才有這些屬性
        if isinstance(error, GeminiVideoError):
            # 顯示嚴重程度(LOW/MEDIUM/HIGH/CRITICAL)
            lines.append(f"\n[#E8C4F0]{safe_t('error.formatter.severity', fallback='Severity')}:{error.severity.value}[/#E8C4F0]")
            # 顯示錯誤發生時間
            lines.append(f"[dim]{safe_t('error.formatter.time', fallback='Time')}:{error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")

            # 上下文資訊(檔案路徑、API 名稱、命令等)
            if error.context:
                lines.append(f"\n[#87CEEB]{safe_t('error.formatter.context', fallback='Context')}:[/#87CEEB]")
                for key, value in error.context.items():
                    lines.append(f"  • {key}: {value}")

            # 修復建議列表
            if show_suggestions and error.suggestions:
                lines.append(f"\n[green]{safe_t('error.formatter.suggestions', fallback='Suggestions')}:[/green]")
                for i, suggestion in enumerate(error.suggestions, 1):
                    lines.append(f"  {i}. {suggestion}")

        # === 第 3 部分:堆疊追蹤(Stack Trace)===
        # 堆疊追蹤對於除錯非常重要,顯示錯誤發生的完整呼叫鏈
        if show_traceback:
            tb = traceback.format_exc()
            # 過濾掉空的或無意義的追蹤
            if tb and tb != "NoneType: None\n":
                lines.append(f"\n[dim]{safe_t('error.formatter.traceback', fallback='Traceback')}:[/dim]")
                lines.append(f"[dim]{tb}[/dim]")

        # 將所有行合併為單一字串,用換行分隔
        return "\n".join(lines)

    @staticmethod
    def display_error(error: Exception, **kwargs):
        """顯示格式化的錯誤訊息"""
        formatted = ErrorFormatter.format_error(error, **kwargs)
        console.print(Panel(formatted, title=safe_t('error.panel.details', fallback='Error Details'), border_style="red"))


# ============================================================================
# 重試裝飾器(Exponential Backoff)
# ============================================================================
# 實作指數退避演算法,避免瞬間大量重試造成系統負載
# 重試間隔:delay, delay*backoff, delay*backoff^2, ...
# 例如:1s, 2s, 4s, 8s...
# ============================================================================

def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    重試裝飾器(支援指數退避)

    提供自動重試機制,使用指數退避演算法避免系統過載。
    適用於 API 呼叫、網路請求、FFmpeg 執行等可能暫時失敗的操作。

    Args:
        max_retries: 最大重試次數(預設 3)
        delay: 初始延遲時間,單位秒(預設 1.0)
        backoff: 延遲倍數,用於指數退避(預設 2.0)
            - 第 1 次重試:delay 秒
            - 第 2 次重試:delay * backoff 秒
            - 第 3 次重試:delay * backoff^2 秒
        exceptions: 要重試的異常類型(預設所有 Exception)
        on_retry: 重試時的回調函數,接收 (exception, attempt_number)

    Returns:
        裝飾器函數

    Example:
        @retry_on_error(max_retries=3, delay=2.0, backoff=2.0)
        def call_api():
            # API 呼叫可能因網路問題失敗
            return client.generate_content(...)

        # 重試時間序列:2s, 4s, 8s

    注意:
        - 使用指數退避避免瞬間大量重試
        - 適合暫時性錯誤(網路、限流、暫時忙碌)
        - 不適合永久性錯誤(金鑰錯誤、檔案不存在)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            # 重試迴圈:嘗試 max_retries + 1 次(初始嘗試 + 重試)
            for attempt in range(max_retries + 1):
                try:
                    # 執行目標函數
                    return func(*args, **kwargs)

                except exceptions as e:
                    # 捕獲到允許重試的異常
                    last_exception = e

                    # 檢查是否還有剩餘重試次數
                    if attempt < max_retries:
                        # 呼叫重試回調
                        if on_retry:
                            on_retry(e, attempt + 1)
                        else:
                            console.print(
                                safe_t('error.retry.attempting',
                                       fallback="[#E8C4F0]⚠️  Attempt {attempt}/{max_retries} failed, retrying in {delay:.1f}s...[/#E8C4F0]",
                                       attempt=attempt + 1,
                                       max_retries=max_retries,
                                       delay=current_delay)
                            )
                            console.print(safe_t('error.message', fallback="[dim]Error: {error}[/dim]", error=str(e)))

                        time.sleep(current_delay)
                        # 指數退避:下次延遲時間 = 當前延遲 * backoff
                        current_delay *= backoff
                    else:
                        # 最後一次嘗試失敗
                        console.print(
                            safe_t('error.retry.max_retries_reached',
                                   fallback="[red]❌ Max retries ({max_retries}) reached, operation failed[/red]",
                                   max_retries=max_retries)
                        )
                        raise

            # 理論上不會到這裡,但為了型別安全
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# ============================================================================
# 失敗恢復管理器(Checkpoint & Recovery)
# ============================================================================
# 提供長時間任務的失敗恢復機制:
# - 定期儲存檢查點(checkpoint)
# - 失敗後從上次檢查點恢復
# - 避免重新執行已完成的步驟
# 適用場景:影片批次處理、多步驟轉換流程
# ============================================================================

@dataclass
class RecoveryCheckpoint:
    """
    恢復檢查點資料結構

    儲存任務執行狀態,用於失敗後恢復。每個檢查點包含:
    - 任務識別資訊
    - 當前執行狀態
    - 已完成的步驟列表
    - 錯誤資訊(如有)
    """
    task_id: str
    task_type: str
    timestamp: str
    state: Dict[str, Any]
    completed_steps: List[str]
    total_steps: int
    error: Optional[Dict[str, Any]] = None


class RecoveryManager:
    """失敗恢復管理器"""

    def __init__(self, recovery_dir: Optional[str] = None):
        """
        初始化恢復管理器

        Args:
            recovery_dir: 恢復檔案目錄,預設為 ~/gemini_videos/.recovery
        """
        if recovery_dir is None:
            recovery_dir = os.path.join(
                os.path.expanduser("~"),
                "gemini_videos",
                ".recovery"
            )
        self.recovery_dir = Path(recovery_dir)
        self.recovery_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        task_id: str,
        task_type: str,
        state: Dict[str, Any],
        completed_steps: List[str],
        total_steps: int,
        error: Optional[Exception] = None
    ) -> str:
        """
        保存恢復檢查點

        Args:
            task_id: 任務 ID
            task_type: 任務類型
            state: 當前狀態
            completed_steps: 已完成步驟
            total_steps: 總步驟數
            error: 錯誤資訊(選用)

        Returns:
            檢查點檔案路徑
        """
        checkpoint = RecoveryCheckpoint(
            task_id=task_id,
            task_type=task_type,
            timestamp=datetime.now().isoformat(),
            state=state,
            completed_steps=completed_steps,
            total_steps=total_steps,
            error=error.to_dict() if isinstance(error, GeminiVideoError) else None
        )

        # 檢查點檔案命名:{task_id}.json
        checkpoint_path = self.recovery_dir / f"{task_id}.json"

        # 將 dataclass 轉換為字典並儲存為 JSON
        # indent=2 讓檔案可讀性更高(方便手動檢查)
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(checkpoint), f, ensure_ascii=False, indent=2)

        console.print(safe_t('error.recovery.saved',
                             fallback="[#87CEEB]💾 Recovery checkpoint saved: {name}[/#87CEEB]",
                             name=checkpoint_path.name))
        return str(checkpoint_path)

    def load_checkpoint(self, task_id: str) -> Optional[RecoveryCheckpoint]:
        """
        載入恢復檢查點

        Args:
            task_id: 任務 ID

        Returns:
            恢復檢查點,若不存在則回傳 None
        """
        checkpoint_path = self.recovery_dir / f"{task_id}.json"

        # 檢查檢查點檔案是否存在
        if not checkpoint_path.exists():
            return None

        try:
            # 讀取 JSON 檔案
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 將字典還原為 RecoveryCheckpoint 物件
            checkpoint = RecoveryCheckpoint(**data)
            console.print(safe_t('error.recovery.loaded',
                                 fallback="[#87CEEB]📂 Recovery checkpoint loaded: {name}[/#87CEEB]",
                                 name=checkpoint_path.name))
            return checkpoint

        except Exception as e:
            console.print(safe_t('error.recovery.load_failed',
                                 fallback="[red]Failed to load checkpoint: {error}[/red]",
                                 error=str(e)))
            return None

    def delete_checkpoint(self, task_id: str) -> bool:
        """
        刪除恢復檢查點

        Args:
            task_id: 任務 ID

        Returns:
            是否成功刪除
        """
        checkpoint_path = self.recovery_dir / f"{task_id}.json"

        if checkpoint_path.exists():
            checkpoint_path.unlink()
            console.print(safe_t('error.recovery.deleted',
                                 fallback="[green]🗑️  Recovery checkpoint deleted: {name}[/green]",
                                 name=checkpoint_path.name))
            return True
        return False

    def list_checkpoints(self) -> List[RecoveryCheckpoint]:
        """列出所有恢復檢查點"""
        checkpoints = []

        for checkpoint_file in self.recovery_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                checkpoints.append(RecoveryCheckpoint(**data))
            except Exception as e:
                console.print(safe_t('error.recovery.read_warning',
                                     fallback="[#E8C4F0]Warning: Cannot read checkpoint {name}: {error}[/#E8C4F0]",
                                     name=checkpoint_file.name,
                                     error=str(e)))

        return checkpoints

    def display_checkpoints(self):
        """顯示所有恢復檢查點"""
        checkpoints = self.list_checkpoints()

        if not checkpoints:
            console.print(safe_t('error.recovery.no_checkpoints', fallback='[#E8C4F0]No recovery checkpoints available[/#E8C4F0]'))
            return

        table = Table(title=safe_t('error.recovery.table_title', fallback='Recovery Checkpoints'))
        table.add_column(safe_t('error.recovery.col_task_id', fallback='Task ID'), style="#87CEEB")
        table.add_column(safe_t('error.recovery.col_type', fallback='Type'), style="green")
        table.add_column(safe_t('error.recovery.col_progress', fallback='Progress'), style="#E8C4F0")
        table.add_column(safe_t('error.recovery.col_time', fallback='Time'), style="dim")
        table.add_column(safe_t('error.recovery.col_status', fallback='Status'), style="#E8C4F0")

        for cp in checkpoints:
            progress = f"{len(cp.completed_steps)}/{cp.total_steps}"
            status = safe_t('error.recovery.status_failed', fallback='❌ Failed') if cp.error else safe_t('error.recovery.status_paused', fallback='⏸️ Paused')
            table.add_row(
                cp.task_id,
                cp.task_type,
                progress,
                cp.timestamp,
                status
            )

        console.print(table)

    def cleanup_old_checkpoints(self, days: int = 7):
        """
        清理舊的恢復檢查點

        Args:
            days: 保留天數,超過此天數的檢查點將被刪除
        """
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted = 0

        for checkpoint_file in self.recovery_dir.glob("*.json"):
            if checkpoint_file.stat().st_mtime < cutoff_time:
                checkpoint_file.unlink()
                deleted += 1

        if deleted > 0:
            console.print(safe_t('error.recovery.cleaned',
                                 fallback="[green]Cleaned up {count} old recovery checkpoints[/green]",
                                 count=deleted))


# ============================================================================
# 錯誤記錄器(Structured Logging)
# ============================================================================
# 提供結構化錯誤日誌功能:
# - JSONL 格式儲存(每行一個 JSON 物件)
# - 包含完整堆疊追蹤
# - 支援上下文資訊
# - 易於後續分析與除錯
# ============================================================================

class ErrorLogger:
    """
    錯誤記錄器

    使用 JSONL(JSON Lines)格式記錄錯誤,方便後續分析。
    每個錯誤記錄包含時間戳、錯誤類型、訊息、堆疊追蹤等資訊。
    """

    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化錯誤記錄器

        Args:
            log_dir: 日誌目錄,預設為 ~/gemini_videos/.logs
        """
        if log_dir is None:
            log_dir = os.path.join(
                os.path.expanduser("~"),
                "gemini_videos",
                ".logs"
            )
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.error_log_path = self.log_dir / "errors.jsonl"

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        記錄錯誤

        Args:
            error: 錯誤物件
            context: 額外的上下文資訊
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': error.__class__.__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }

        # 如果是自訂錯誤,包含額外資訊
        if isinstance(error, GeminiVideoError):
            log_entry.update(error.to_dict())

        # 寫入日誌檔案(JSONL 格式:每行一個 JSON 物件)
        # 使用 append 模式,不會覆蓋現有日誌
        # ensure_ascii=False 保留中文字符
        with open(self.error_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def get_error_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        取得錯誤統計

        Args:
            days: 統計天數

        Returns:
            錯誤統計資料
        """
        # 如果日誌檔案不存在,返回空統計
        if not self.error_log_path.exists():
            return {'total': 0, 'by_type': {}, 'by_severity': {}}

        # 計算時間截止點(只統計最近 N 天的錯誤)
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        # 初始化統計結構
        stats = {
            'total': 0,           # 總錯誤數
            'by_type': {},        # 按錯誤類型分組
            'by_severity': {}     # 按嚴重程度分組
        }

        # 逐行讀取 JSONL 檔案
        with open(self.error_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    # 解析 JSON 行
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()

                    # 只統計時間範圍內的錯誤
                    if entry_time >= cutoff_time:
                        stats['total'] += 1

                        # 統計錯誤類型(APIError, FileProcessingError...)
                        error_type = entry.get('type', 'Unknown')
                        stats['by_type'][error_type] = stats['by_type'].get(error_type, 0) + 1

                        # 統計嚴重程度(LOW, MEDIUM, HIGH, CRITICAL)
                        severity = entry.get('severity', 'Unknown')
                        stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1

                except Exception:
                    # 跳過損壞的 JSON 行
                    continue

        return stats

    def display_error_stats(self, days: int = 7):
        """顯示錯誤統計"""
        stats = self.get_error_stats(days)

        console.print(safe_t('error.stats.title',
                             fallback="\n[bold #87CEEB]📊 Error Statistics (Last {days} days)[/bold #87CEEB]\n",
                             days=days))
        console.print(safe_t('error.stats.total',
                             fallback="Total Errors: {total}",
                             total=stats['total']))

        if stats['by_type']:
            console.print(safe_t('error.stats.by_type', fallback="\n[#E8C4F0]Distribution by Type:[/#E8C4F0]"))
            for error_type, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
                console.print(f"  • {error_type}: {count}")

        if stats['by_severity']:
            console.print(safe_t('error.stats.by_severity', fallback="\n[#E8C4F0]Distribution by Severity:[/#E8C4F0]"))
            for severity, count in sorted(stats['by_severity'].items(), key=lambda x: x[1], reverse=True):
                console.print(f"  • {severity}: {count}")


# ==================== 輔助函數 ====================

def suggest_solutions(error: Exception) -> List[str]:
    """
    根據錯誤類型提供建議的解決方案

    Args:
        error: 錯誤物件

    Returns:
        建議列表
    """
    suggestions = []

    if isinstance(error, FileNotFoundError):
        suggestions.extend([
            safe_t('error.suggestion.check_file_path', fallback='Check if the file path is correct'),
            safe_t('error.suggestion.confirm_file_exists', fallback='Confirm the file exists'),
            safe_t('error.suggestion.check_file_permission', fallback='Check file permissions')
        ])
    elif isinstance(error, PermissionError):
        suggestions.extend([
            safe_t('error.suggestion.check_permission_settings', fallback='Check file permission settings'),
            safe_t('error.suggestion.confirm_write_permission', fallback='Confirm you have write permissions'),
            safe_t('error.suggestion.try_admin_mode', fallback='Try running with administrator privileges')
        ])
    elif isinstance(error, ConnectionError) or isinstance(error, NetworkError):
        suggestions.extend([
            safe_t('error.suggestion.check_network', fallback='Check network connection'),
            safe_t('error.suggestion.confirm_api_service', fallback='Confirm API service is available'),
            safe_t('error.suggestion.check_firewall', fallback='Check firewall settings'),
            safe_t('error.suggestion.try_later', fallback='Try again later')
        ])
    elif isinstance(error, APIError):
        suggestions.extend([
            safe_t('error.suggestion.check_api_key', fallback='Check if the API key is correct'),
            safe_t('error.suggestion.confirm_api_quota', fallback='Confirm API quota is sufficient'),
            safe_t('error.suggestion.check_api_status', fallback='Check API service status'),
            safe_t('error.suggestion.check_api_docs', fallback='Review API documentation')
        ])
    elif isinstance(error, FFmpegError):
        suggestions.extend([
            safe_t('error.suggestion.install_ffmpeg', fallback='Ensure ffmpeg is installed: brew install ffmpeg'),
            safe_t('error.suggestion.check_ffmpeg_version', fallback='Check if ffmpeg version meets requirements'),
            safe_t('error.suggestion.confirm_video_format', fallback='Confirm video format is supported'),
            safe_t('error.suggestion.check_video_corruption', fallback='Check if video file is corrupted')
        ])

    return suggestions


# ==================== 使用範例(僅供參考,不會執行)====================

if __name__ == "__main__":
    # 範例 1:使用重試裝飾器
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def risky_api_call():
        """可能失敗的 API 呼叫"""
        import random
        if random.random() < 0.7:
            raise APIError(safe_t('error.example.api_unavailable', fallback='API temporarily unavailable'), api_name="Gemini")
        return safe_t('error.example.success', fallback='Success')

    # 範例 2:使用自訂錯誤與建議
    try:
        raise FileProcessingError(
            safe_t('error.example.cannot_process_video', fallback='Cannot process video file'),
            file_path="/path/to/video.mp4",
            suggestions=[
                safe_t('error.example.check_video_format', fallback='Check if video format is supported'),
                safe_t('error.example.confirm_ffmpeg', fallback='Confirm ffmpeg is installed'),
                safe_t('error.example.convert_format', fallback='Try converting video format')
            ]
        )
    except GeminiVideoError as e:
        ErrorFormatter.display_error(e)

    # 範例 3:使用恢復管理器
    recovery_mgr = RecoveryManager()

    # 保存檢查點
    recovery_mgr.save_checkpoint(
        task_id="video_gen_001",
        task_type="flow_generation",
        state={"current_segment": 2, "total_segments": 5},
        completed_steps=["segment_1", "segment_2"],
        total_steps=5
    )

    # 顯示檢查點
    recovery_mgr.display_checkpoints()

    # 範例 4:使用錯誤記錄器
    error_logger = ErrorLogger()

    try:
        raise ValidationError(safe_t('error.example.invalid_param', fallback='Invalid parameter'), field="resolution")
    except Exception as e:
        error_logger.log_error(e, context={"user": "test", "operation": "generate_video"})

    # 顯示統計
    error_logger.display_error_stats(days=7)
