#!/usr/bin/env python3
"""
統一錯誤處理系統 (Unified Error Handler) - 輕量級動態載入版本

核心設計原則:
1. 核心框架 < 200 行 (不含註釋)
2. 所有修復函數採用延遲載入 - 避免啟動時載入巨獸模組
3. 優秀的 UX 體驗 - 錯誤訊息有用且能協助修正

版本: v2.0.0 - 輕量級重構
日期: 2025-10-29 10:21:38 CST
作者: Saki-tw with Claude Code (Sonnet 4.5)
"""

import sys
import os
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path

# 確保可以導入專案模組
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Rich UI 組件 (輕量級,可接受)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None  # 降級為純文字輸出

# ❌ 移除頂層導入 - 改為延遲載入
# import error_diagnostics  ← 刪除 (3,490 行巨獸)
# import error_fix_suggestions  ← 刪除 (505 行)

# 延遲載入快取
_error_diagnostics_module = None
_error_fix_suggestions_module = None


# ==================== 資料結構定義 ====================

class FixMode(Enum):
    """修復模式枚舉"""
    AUTO = "auto"           # 自動修復 (不詢問直接執行)
    SEMI_AUTO = "semi"      # 半自動 (詢問後執行)
    MANUAL = "manual"       # 手動 (僅顯示步驟)


class ErrorType(Enum):
    """錯誤類型分類"""
    FILE_NOT_FOUND = "file_not_found"
    FILE_CORRUPTED = "file_corrupted"
    EMPTY_FILE = "empty_file"
    MISSING_DEPENDENCY = "missing_dependency"
    API_ERROR = "api_error"
    API_KEY_MISSING = "api_key_missing"
    FFMPEG_ERROR = "ffmpeg_error"
    FFMPEG_NOT_INSTALLED = "ffmpeg_not_installed"
    JSON_PARSE_ERROR = "json_parse_error"
    PERMISSION_ERROR = "permission_error"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"
    VIDEO_ERROR = "video_error"
    IMAGE_ERROR = "image_error"
    AUDIO_ERROR = "audio_error"
    SUBTITLE_ERROR = "subtitle_error"
    UPLOAD_ERROR = "upload_error"
    TRANSCODE_ERROR = "transcode_error"
    UNKNOWN = "unknown"


@dataclass
class FixAction:
    """修復動作資料結構"""
    name: str                                   # 動作名稱
    description: str                            # 動作描述
    function: Callable                          # 執行函數
    params: Dict[str, Any] = field(default_factory=dict)        # 所需參數
    param_schema: Dict[str, type] = field(default_factory=dict) # 參數型別定義
    auto_executable: bool = True                # 是否可自動執行
    requires_user_input: bool = False           # 是否需要用戶輸入
    priority: int = 5                           # 優先級 (1-10, 數字越小優先級越高)


@dataclass
class ErrorContext:
    """錯誤上下文資料結構"""
    error: Exception                            # 原始錯誤
    error_type: ErrorType                       # 錯誤類型
    error_message: str                          # 錯誤訊息
    traceback_str: str                          # 追蹤訊息
    context_info: Dict[str, Any] = field(default_factory=dict)  # 上下文資訊
    suggested_fixes: List[FixAction] = field(default_factory=list)  # 建議的修復動作
    timestamp: datetime = field(default_factory=datetime.now)       # 發生時間
    diagnosis_result: Optional[Any] = None      # 診斷結果


# ==================== 錯誤分類器 ====================

class ErrorClassifier:
    """錯誤分類器 - 將異常映射到 ErrorType"""

    # 錯誤訊息關鍵字映射
    ERROR_PATTERNS = {
        ErrorType.FILE_NOT_FOUND: [
            "No such file or directory",
            "File not found",
            "FileNotFoundError",
            "找不到檔案",
            "找不到圖片",
            "找不到影片",
        ],
        ErrorType.FILE_CORRUPTED: [
            "corrupted",
            "damaged",
            "invalid format",
            "corrupt",
            "損壞",
        ],
        ErrorType.EMPTY_FILE: [
            "empty file",
            "file is empty",
            "空檔案",
        ],
        ErrorType.MISSING_DEPENDENCY: [
            "No module named",
            "ModuleNotFoundError",
            "ImportError",
            "缺少模組",
        ],
        ErrorType.API_KEY_MISSING: [
            "API key",
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
            "Missing API key",
        ],
        ErrorType.FFMPEG_NOT_INSTALLED: [
            "ffmpeg not found",
            "ffmpeg: not found",
            "Cannot find ffmpeg",
        ],
        ErrorType.FFMPEG_ERROR: [
            "ffmpeg error",
            "FFmpeg",
            "Conversion failed",
        ],
        ErrorType.JSON_PARSE_ERROR: [
            "JSONDecodeError",
            "Invalid JSON",
            "JSON parse",
        ],
        ErrorType.PERMISSION_ERROR: [
            "PermissionError",
            "Permission denied",
            "權限不足",
        ],
        ErrorType.NETWORK_ERROR: [
            "ConnectionError",
            "Timeout",
            "Network",
            "連線錯誤",
        ],
        ErrorType.VIDEO_ERROR: [
            "video",
            "影片",
        ],
        ErrorType.IMAGE_ERROR: [
            "image",
            "PIL",
            "圖片",
        ],
        ErrorType.UPLOAD_ERROR: [
            "upload failed",
            "上傳失敗",
        ],
    }

    @classmethod
    def classify(cls, error: Exception, context_info: Dict[str, Any] = None) -> ErrorType:
        """
        分類錯誤

        Args:
            error: 異常對象
            context_info: 上下文資訊

        Returns:
            ErrorType
        """
        error_str = str(error).lower()
        error_type_name = type(error).__name__

        # 1. 根據異常類型判斷
        if isinstance(error, FileNotFoundError):
            return ErrorType.FILE_NOT_FOUND
        elif isinstance(error, PermissionError):
            return ErrorType.PERMISSION_ERROR
        elif isinstance(error, ModuleNotFoundError) or isinstance(error, ImportError):
            return ErrorType.MISSING_DEPENDENCY

        # 2. 根據錯誤訊息關鍵字判斷
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in error_str or pattern.lower() in error_type_name.lower():
                    return error_type

        # 3. 根據上下文資訊判斷
        if context_info:
            if 'file_path' in context_info:
                return ErrorType.FILE_NOT_FOUND
            if 'api_key' in context_info:
                return ErrorType.API_KEY_MISSING

        return ErrorType.UNKNOWN


# ==================== 動態載入輔助函數 ====================

def _lazy_import_error_diagnostics():
    """延遲載入 error_diagnostics 模組"""
    global _error_diagnostics_module
    if _error_diagnostics_module is None:
        try:
            import error_diagnostics
            _error_diagnostics_module = error_diagnostics
        except ImportError as e:
            print(f"⚠️  無法載入 error_diagnostics: {e}", file=sys.stderr)
            _error_diagnostics_module = False  # 標記為不可用
    return _error_diagnostics_module if _error_diagnostics_module is not False else None


def _lazy_import_error_fix_suggestions():
    """延遲載入 error_fix_suggestions 模組"""
    global _error_fix_suggestions_module
    if _error_fix_suggestions_module is None:
        try:
            import error_fix_suggestions
            _error_fix_suggestions_module = error_fix_suggestions
        except ImportError as e:
            print(f"⚠️  無法載入 error_fix_suggestions: {e}", file=sys.stderr)
            _error_fix_suggestions_module = False  # 標記為不可用
    return _error_fix_suggestions_module if _error_fix_suggestions_module is not False else None


# ==================== 修復動作映射表 (輕量級) ====================

class FixActionRegistry:
    """
    修復動作註冊表 - 輕量級映射表

    只儲存元數據 (模組名, 函數名),不載入實際函數
    """

    # 錯誤類型 → [(函數名, 描述)]
    _REGISTRY_METADATA = {
        ErrorType.FILE_NOT_FOUND: [
            ("suggest_file_not_found", "檔案不存在修復建議"),
        ],
        ErrorType.EMPTY_FILE: [
            ("suggest_empty_file", "空檔案處理建議"),
        ],
        ErrorType.FILE_CORRUPTED: [
            ("suggest_file_corrupted", "檔案損壞處理建議"),
        ],
        ErrorType.MISSING_DEPENDENCY: [
            ("suggest_missing_module", "缺少模組安裝建議"),
        ],
        ErrorType.API_KEY_MISSING: [
            ("suggest_api_key_setup", "API Key 設定協助"),
        ],
        ErrorType.FFMPEG_NOT_INSTALLED: [
            ("suggest_ffmpeg_install", "FFmpeg 安裝協助"),
        ],
        ErrorType.FFMPEG_ERROR: [
            ("suggest_ffmpeg_install", "FFmpeg 錯誤修復"),
        ],
        ErrorType.JSON_PARSE_ERROR: [
            ("suggest_json_parse_failed", "JSON 解析錯誤修復"),
        ],
        ErrorType.VIDEO_ERROR: [
            ("suggest_video_file_not_found", "影片檔案問題修復"),
        ],
        ErrorType.IMAGE_ERROR: [
            ("suggest_image_load_failed", "圖片載入失敗處理"),
        ],
        ErrorType.UPLOAD_ERROR: [
            ("suggest_video_upload_failed", "上傳失敗處理建議"),
        ],
        ErrorType.TRANSCODE_ERROR: [
            ("suggest_video_transcode_failed", "轉碼失敗處理建議"),
        ],
    }

    @classmethod
    def get_fix_functions(cls, error_type: ErrorType) -> List[Callable]:
        """
        動態載入並獲取修復函數列表 (按需載入)

        Args:
            error_type: 錯誤類型

        Returns:
            修復函數列表 (可能為空)
        """
        metadata_list = cls._REGISTRY_METADATA.get(error_type, [])
        if not metadata_list:
            return []

        # 延遲載入 error_fix_suggestions 模組
        module = _lazy_import_error_fix_suggestions()
        if not module:
            return []

        # 動態獲取函數
        fix_functions = []
        for function_name, description in metadata_list:
            func = getattr(module, function_name, None)
            if func:
                # 附加描述到函數 (供 UI 顯示)
                func._fix_description = description
                fix_functions.append(func)
            else:
                print(f"⚠️  找不到修復函數: {function_name}", file=sys.stderr)

        return fix_functions


# ==================== 參數收集器 ====================

class ParameterCollector:
    """參數收集器 - 互動式收集修復動作所需的參數"""

    @staticmethod
    def collect_params(param_schema: Dict[str, type], existing_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        收集參數

        Args:
            param_schema: 參數型別定義 {"param_name": type}
            existing_params: 已有的參數值

        Returns:
            完整的參數字典
        """
        params = existing_params.copy() if existing_params else {}

        console.print("\n[#87CEEB]需要收集以下參數：[/#87CEEB]")

        for param_name, param_type in param_schema.items():
            if param_name in params:
                console.print(f"  ✓ {param_name}: [green]{params[param_name]}[/green] (已提供)")
                continue

            # 互動式收集參數
            prompt_text = f"  請輸入 {param_name} ({param_type.__name__})"

            try:
                if param_type == bool:
                    value = Confirm.ask(prompt_text, default=False)
                elif param_type == int:
                    value_str = Prompt.ask(prompt_text)
                    value = int(value_str)
                elif param_type == float:
                    value_str = Prompt.ask(prompt_text)
                    value = float(value_str)
                else:  # str or others
                    value = Prompt.ask(prompt_text)

                params[param_name] = value

            except (ValueError, KeyboardInterrupt) as e:
                console.print(f"[red]✗ 參數收集失敗: {e}[/red]")
                return {}

        return params

    @staticmethod
    def validate_params(params: Dict[str, Any], param_schema: Dict[str, type]) -> bool:
        """
        驗證參數有效性

        Args:
            params: 參數字典
            param_schema: 參數型別定義

        Returns:
            是否有效
        """
        for param_name, param_type in param_schema.items():
            if param_name not in params:
                console.print(f"[red]✗ 缺少必要參數: {param_name}[/red]")
                return False

            if not isinstance(params[param_name], param_type):
                console.print(f"[red]✗ 參數類型錯誤: {param_name} (期望 {param_type.__name__}, 實際 {type(params[param_name]).__name__})[/red]")
                return False

        return True


# ==================== 統一錯誤處理器 ====================

class UnifiedErrorHandler:
    """統一錯誤處理器 - 主控制器"""

    def __init__(
        self,
        mode: FixMode = FixMode.SEMI_AUTO,
        enable_logging: bool = True,
        log_file: Optional[str] = None,
        silent: bool = False  # 新增: 靜默模式,不輸出初始化訊息
    ):
        """
        初始化 (輕量級 - 不載入巨獸模組)

        Args:
            mode: 修復模式 (AUTO/SEMI_AUTO/MANUAL)
            enable_logging: 是否啟用日誌
            log_file: 日誌檔案路徑
            silent: 靜默模式,不輸出初始化訊息
        """
        self.mode = mode
        self.enable_logging = enable_logging
        self.log_file = log_file or "unified_error_handler.log"

        # 錯誤歷史
        self.error_history: List[ErrorContext] = []

        # 不再初始化重量級組件,改為按需使用
        # self.classifier = ErrorClassifier()  ← 改為靜態方法
        # self.registry = FixActionRegistry()  ← 改為類方法

        if not silent and RICH_AVAILABLE:
            console.print("[green]✅ 輕量級錯誤處理系統已就緒[/green]")

    def handle(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        auto_fix: Optional[bool] = None
    ) -> bool:
        """
        處理錯誤 (主要入口)

        Args:
            error: 異常對象
            context: 上下文資訊
            auto_fix: 是否自動修復 (覆蓋 mode 設定)

        Returns:
            是否成功修復
        """
        try:
            # 1. 建立錯誤上下文
            error_context = self._build_error_context(error, context or {})

            # 2. 顯示錯誤資訊
            self._display_error(error_context)

            # 3. 診斷錯誤 (如果可用)
            if DIAGNOSTICS_AVAILABLE:
                self._diagnose_error(error_context)

            # 4. 獲取修復動作
            fix_actions = self._get_fix_actions(error_context)

            if not fix_actions:
                console.print("[#DDA0DD]⚠️  沒有可用的修復動作[/#DDA0DD]")
                return False

            # 5. 顯示修復方案
            self._display_fix_actions(fix_actions)

            # 6. 決定是否執行修復
            should_fix = auto_fix if auto_fix is not None else self._should_execute_fixes()

            if not should_fix:
                console.print("[dim]已取消修復[/dim]")
                return False

            # 7. 執行修復
            success = self._execute_fixes(fix_actions, error_context)

            # 8. 記錄歷史
            self.error_history.append(error_context)

            return success

        except Exception as e:
            console.print(f"[red]✗ 錯誤處理過程中發生異常: {e}[/red]")
            traceback.print_exc()
            return False

    def _build_error_context(self, error: Exception, context_info: Dict[str, Any]) -> ErrorContext:
        """建立錯誤上下文"""
        error_type = ErrorClassifier.classify(error, context_info)  # 改為靜態方法調用
        error_message = str(error)
        traceback_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

        return ErrorContext(
            error=error,
            error_type=error_type,
            error_message=error_message,
            traceback_str=traceback_str,
            context_info=context_info,
            suggested_fixes=[],
            timestamp=datetime.now()
        )

    def _display_error(self, error_context: ErrorContext):
        """顯示錯誤資訊"""
        if RICH_AVAILABLE:
            console.print()
            console.print(Panel(
                f"[red bold]錯誤類型:[/red bold] {error_context.error_type.value}\n"
                f"[red bold]錯誤訊息:[/red bold] {error_context.error_message}\n"
                f"[dim]時間: {error_context.timestamp.strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
                title="🚨 錯誤資訊",
                border_style="red"
            ))
        else:
            # 降級為純文字輸出
            print("\n" + "=" * 60)
            print("🚨 錯誤資訊")
            print("=" * 60)
            print(f"錯誤類型: {error_context.error_type.value}")
            print(f"錯誤訊息: {error_context.error_message}")
            print(f"時間: {error_context.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60 + "\n")

    def _diagnose_error(self, error_context: ErrorContext):
        """診斷錯誤 (延遲載入診斷模組)"""
        # 延遲載入 error_diagnostics
        diagnostics_module = _lazy_import_error_diagnostics()
        if not diagnostics_module:
            return  # 診斷模組不可用,跳過

        try:
            diagnostics = diagnostics_module.ErrorDiagnostics()
            result = diagnostics.diagnose(error_context.error, error_context.context_info)
            error_context.diagnosis_result = result

            if result and hasattr(result, 'solutions') and result.solutions:
                if RICH_AVAILABLE:
                    console.print("\n[#87CEEB]📋 診斷結果:[/#87CEEB]")
                    for i, solution in enumerate(result.solutions, 1):
                        console.print(f"  {i}. {solution.title}")
                        console.print(f"     [dim]{solution.description}[/dim]")
                else:
                    print("\n📋 診斷結果:")
                    for i, solution in enumerate(result.solutions, 1):
                        print(f"  {i}. {solution.title}")
                        print(f"     {solution.description}")

        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[#DDA0DD]⚠️  診斷失敗: {e}[/#DDA0DD]")
            else:
                print(f"⚠️  診斷失敗: {e}", file=sys.stderr)

    def _get_fix_actions(self, error_context: ErrorContext) -> List[FixAction]:
        """獲取修復動作列表 (延遲載入修復函數)"""
        # 使用類方法動態載入
        fix_functions = FixActionRegistry.get_fix_functions(error_context.error_type)

        if not fix_functions:
            return []

        fix_actions = []
        for func in fix_functions:
            # 包裝為 FixAction
            description = getattr(func, '_fix_description', func.__doc__ or "修復動作")
            fix_action = FixAction(
                name=func.__name__,
                description=description,
                function=func,
                params=error_context.context_info.copy(),
                auto_executable=True,
                requires_user_input=True,
                priority=5
            )
            fix_actions.append(fix_action)

        # 按優先級排序
        fix_actions.sort(key=lambda x: x.priority)

        error_context.suggested_fixes = fix_actions
        return fix_actions

    def _display_fix_actions(self, fix_actions: List[FixAction]):
        """顯示修復方案"""
        if RICH_AVAILABLE:
            console.print("\n[#87CEEB]🔧 可用的修復方案:[/#87CEEB]")

            table = Table(show_header=True, header_style="bold #87CEEB")
            table.add_column("#", width=4)
            table.add_column("名稱", width=30)
            table.add_column("描述", width=50)
            table.add_column("優先級", width=8)

            for i, action in enumerate(fix_actions, 1):
                table.add_row(
                    str(i),
                    action.name,
                    action.description.split('\n')[0][:50],
                    f"P{action.priority}"
                )

            console.print(table)
        else:
            # 降級為純文字輸出
            print("\n🔧 可用的修復方案:")
            for i, action in enumerate(fix_actions, 1):
                print(f"  [{i}] {action.name}")
                print(f"      {action.description.split(chr(10))[0][:50]}")
                print(f"      優先級: P{action.priority}")

    def _should_execute_fixes(self) -> bool:
        """決定是否執行修復"""
        if self.mode == FixMode.AUTO:
            return True
        elif self.mode == FixMode.MANUAL:
            return False
        else:  # SEMI_AUTO
            if RICH_AVAILABLE:
                return Confirm.ask("\n是否執行自動修復?", default=True)
            else:
                # 降級為標準 input
                try:
                    response = input("\n是否執行自動修復? [y/n] (預設 y): ").strip().lower()
                    return response in ['y', 'yes', '是', ''] or response == ''
                except (KeyboardInterrupt, EOFError):
                    return False

    def _execute_fixes(self, fix_actions: List[FixAction], error_context: ErrorContext) -> bool:
        """執行修復動作"""
        if RICH_AVAILABLE:
            console.print("\n[#87CEEB]🔄 開始執行修復...[/#87CEEB]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:

                for action in fix_actions:
                    task = progress.add_task(f"執行: {action.name}", total=1)

                    try:
                        # 執行修復函數
                        result = action.function(**action.params)

                        progress.update(task, completed=1)
                        console.print(f"[green]✓ 完成: {action.name}[/green]")

                        # 如果修復成功，返回 True
                        if result is not False:
                            return True

                    except Exception as e:
                        console.print(f"[red]✗ 失敗: {action.name} - {e}[/red]")
                        continue
        else:
            # 降級為純文字輸出
            print("\n🔄 開始執行修復...")
            for i, action in enumerate(fix_actions, 1):
                print(f"  [{i}/{len(fix_actions)}] 執行: {action.name}")
                try:
                    result = action.function(**action.params)
                    print(f"      ✓ 完成")

                    if result is not False:
                        return True

                except Exception as e:
                    print(f"      ✗ 失敗: {e}", file=sys.stderr)
                    continue

        return False


# ==================== 便利函數 ====================

# 全域處理器實例
_global_handler: Optional[UnifiedErrorHandler] = None


def get_error_handler(
    mode: FixMode = FixMode.SEMI_AUTO,
    force_new: bool = False
) -> UnifiedErrorHandler:
    """
    獲取全域錯誤處理器實例

    Args:
        mode: 修復模式
        force_new: 是否強制創建新實例

    Returns:
        UnifiedErrorHandler 實例
    """
    global _global_handler

    if _global_handler is None or force_new:
        _global_handler = UnifiedErrorHandler(mode=mode)

    return _global_handler


def handle_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    auto_fix: Optional[bool] = None,
    mode: FixMode = FixMode.SEMI_AUTO
) -> bool:
    """
    便利函數 - 處理單一錯誤

    Args:
        error: 異常對象
        context: 上下文資訊
        auto_fix: 是否自動修復
        mode: 修復模式

    Returns:
        是否成功修復
    """
    handler = get_error_handler(mode=mode)
    return handler.handle(error, context, auto_fix)


# ==================== 主程式 (測試) ====================

if __name__ == "__main__":
    console.print("[bold #DDA0DD]統一錯誤處理系統 v1.0.0[/bold #DDA0DD]")
    console.print("=" * 60)

    # 測試案例
    print("\n測試 1: FileNotFoundError")
    try:
        with open("/nonexistent/file.txt") as f:
            pass
    except Exception as e:
        handle_error(e, context={"file_path": "/nonexistent/file.txt"})

    print("\n測試 2: ModuleNotFoundError")
    try:
        import nonexistent_module
    except Exception as e:
        handle_error(e, context={"module_name": "nonexistent_module"})
