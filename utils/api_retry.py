#!/usr/bin/env python3
"""
Gemini API 調用重試機制
提供自動重試、錯誤診斷、友好的錯誤訊息和解決方案建議
"""

import time
import functools
from typing import Callable, Any, Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class APIRetryConfig:
    """API 重試配置"""
    max_retries: int = 3
    base_delay: float = 2.0  # 基礎延遲（秒）
    max_delay: float = 30.0  # 最大延遲（秒）
    exponential_backoff: bool = True  # 指數退避

    # 可重試的錯誤模式
    retryable_errors = [
        "503",  # Service Unavailable
        "429",  # Too Many Requests
        "500",  # Internal Server Error
        "502",  # Bad Gateway
        "504",  # Gateway Timeout
        "timeout",
        "connection",
        "quota exceeded",
        "rate limit",
        "temporarily unavailable",
        "resource exhausted",
    ]

    # 不可重試的錯誤模式
    non_retryable_errors = [
        "401",  # Unauthorized
        "403",  # Forbidden
        "404",  # Not Found
        "invalid api key",
        "permission denied",
        "invalid argument",
        "invalid request",
        "bad request",
        "not found",
    ]


def is_retryable_error(error: Exception) -> bool:
    """
    判斷錯誤是否可重試

    Args:
        error: 異常物件

    Returns:
        True 如果錯誤可重試，False 否則
    """
    error_str = str(error).lower()

    # 檢查不可重試模式（優先）
    for pattern in APIRetryConfig.non_retryable_errors:
        if pattern in error_str:
            return False

    # 檢查可重試模式
    for pattern in APIRetryConfig.retryable_errors:
        if pattern in error_str:
            return True

    # 預設：可重試（保守策略）
    return True


def get_error_reason(error: Exception) -> str:
    """
    獲取錯誤原因的友好說明

    Args:
        error: 異常物件

    Returns:
        友好的錯誤原因說明
    """
    error_str = str(error).lower()

    if "503" in error_str or "service unavailable" in error_str:
        return "Gemini API 暫時無法使用（伺服器過載）"
    elif "429" in error_str or "rate limit" in error_str:
        return "API 調用頻率過高（達到速率限制）"
    elif "500" in error_str:
        return "Gemini API 內部錯誤"
    elif "timeout" in error_str:
        return "網路連線超時"
    elif "connection" in error_str:
        return "網路連線失敗"
    elif "quota" in error_str or "resource exhausted" in error_str:
        return "API 配額已用盡"
    elif "401" in error_str or "unauthorized" in error_str:
        return "API 金鑰無效或已過期"
    elif "403" in error_str or "forbidden" in error_str:
        return "無權限存取此 API"
    elif "404" in error_str or "not found" in error_str:
        return "請求的資源不存在"
    elif "invalid api key" in error_str:
        return "API 金鑰格式錯誤"
    elif "invalid argument" in error_str or "bad request" in error_str:
        return "請求參數錯誤"
    else:
        return "未知錯誤"


def show_error_solutions(error: Exception, operation_name: str = "API 調用"):
    """
    顯示錯誤的解決方案

    Args:
        error: 異常物件
        operation_name: 操作名稱
    """
    error_str = str(error).lower()

    console.print(f"\n[#B565D8]💡 解決方案：[/#B565D8]")

    # API 金鑰相關錯誤
    if "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
        console.print("   1. 檢查 API 金鑰是否正確")
        console.print("   2. 確認 API 金鑰是否已啟用")
        console.print("   3. 檢查 API 配額是否已用盡")
        console.print("   4. 重新生成 API 金鑰\n")

        console.print("   查看 API 金鑰設定：")
        console.print(Panel(
            "echo $GEMINI_API_KEY",
            border_style="bright_magenta",
            expand=False
        ))

        console.print("\n   取得新的 API 金鑰：")
        console.print(Panel(
            "https://makersuite.google.com/app/apikey",
            border_style="bright_magenta",
            expand=False
        ))

    # 配額用盡
    elif "quota" in error_str or "resource exhausted" in error_str:
        console.print("   1. 檢查 API 使用量配額")
        console.print("   2. 等待配額重置（通常為每分鐘/每日）")
        console.print("   3. 升級到付費方案以獲得更高配額")
        console.print("   4. 減少 API 調用頻率\n")

        console.print("   查看配額狀態：")
        console.print(Panel(
            "https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas",
            border_style="bright_magenta",
            expand=False
        ))

    # 速率限制
    elif "429" in error_str or "rate limit" in error_str:
        console.print("   1. 降低 API 調用頻率")
        console.print("   2. 在請求間添加延遲")
        console.print("   3. 使用批次處理減少請求數量")
        console.print("   4. 考慮升級到更高配額的方案\n")

    # 網路問題
    elif "timeout" in error_str or "connection" in error_str:
        console.print("   1. 檢查網路連線狀態")
        console.print("   2. 檢查防火牆設定")
        console.print("   3. 嘗試更換網路環境")
        console.print("   4. 增加請求超時時間\n")

        console.print("   測試網路連線：")
        console.print(Panel(
            "ping -c 4 generativelanguage.googleapis.com",
            border_style="bright_magenta",
            expand=False
        ))

    # 參數錯誤
    elif "invalid argument" in error_str or "bad request" in error_str:
        console.print("   1. 檢查請求參數是否正確")
        console.print("   2. 確認檔案格式是否支援")
        console.print("   3. 檢查檔案大小是否超過限制")
        console.print("   4. 參考 API 文檔確認參數規格\n")

        console.print("   API 文檔：")
        console.print(Panel(
            "https://ai.google.dev/api",
            border_style="bright_magenta",
            expand=False
        ))

    # 伺服器錯誤
    elif "500" in error_str or "503" in error_str or "502" in error_str or "504" in error_str:
        console.print("   1. 等待幾分鐘後重試")
        console.print("   2. 檢查 Google Cloud 狀態頁面")
        console.print("   3. 減少請求大小或複雜度")
        console.print("   4. 如持續發生，聯絡 Google 支援\n")

        console.print("   檢查服務狀態：")
        console.print(Panel(
            "https://status.cloud.google.com/",
            border_style="bright_magenta",
            expand=False
        ))

    # 未知錯誤
    else:
        console.print("   1. 檢查錯誤訊息並搜尋相關解決方案")
        console.print("   2. 確認所有依賴套件已正確安裝")
        console.print("   3. 查看程式日誌獲取更多資訊")
        console.print("   4. 嘗試更新到最新版本\n")


def api_retry(
    operation_name: str = "API 調用",
    max_retries: Optional[int] = None,
    show_progress: bool = True
):
    """
    API 重試裝飾器

    提供自動重試、錯誤診斷、友好的錯誤訊息和解決方案建議

    Args:
        operation_name: 操作名稱（顯示在錯誤訊息中）
        max_retries: 最大重試次數（None 使用預設值）
        show_progress: 是否顯示進度條和詳細資訊

    Returns:
        裝飾器函數

    Example:
        >>> @api_retry("語音辨識", max_retries=3)
        >>> def transcribe_audio(audio_path):
        >>>     # API 調用
        >>>     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            config = APIRetryConfig()
            retries = max_retries if max_retries is not None else config.max_retries

            last_error = None
            retry_stats = {
                'attempts': 0,
                'failures': 0,
                'total_delay': 0,
                'start_time': time.time()
            }

            for attempt in range(1, retries + 1):
                retry_stats['attempts'] = attempt

                try:
                    # 顯示進度
                    if show_progress and attempt == 1:
                        console.print(f"\n[#B565D8]🔄 {operation_name}中...[/#B565D8]")

                    # 執行 API 調用
                    result = func(*args, **kwargs)

                    # 成功
                    if attempt > 1:
                        # 計算總耗時
                        total_time = time.time() - retry_stats['start_time']
                        success_rate = ((attempt - retry_stats['failures']) / attempt) * 100

                        console.print(
                            f"\n[#B565D8]✓ {operation_name}成功（第 {attempt} 次嘗試）[/#B565D8]"
                        )
                        console.print(
                            f"   [dim]耗時：{total_time:.1f} 秒（含重試）[/dim]"
                        )

                        # 顯示重試統計
                        if show_progress:
                            console.print(f"\n[#B565D8]📊 重試統計：[/#B565D8]")
                            console.print(f"   - 總嘗試次數：{attempt}")
                            console.print(f"   - 失敗次數：{retry_stats['failures']}")
                            console.print(f"   - 成功率：{success_rate:.0f}%")

                            if retry_stats['failures'] >= 2:
                                console.print(
                                    "   - [#B565D8]建議：網路連線可能不穩定，建議檢查網路狀況[/#B565D8]"
                                )

                    return result

                except Exception as e:
                    last_error = e
                    retry_stats['failures'] += 1

                    # 判斷是否可重試
                    retryable = is_retryable_error(e)
                    error_reason = get_error_reason(e)

                    # 顯示錯誤
                    error_prefix = "⚠️ " if retryable else "✗"
                    console.print(
                        f"\n[#B565D8]{error_prefix} {operation_name}失敗（第 {attempt}/{retries} 次）[/#B565D8]"
                    )
                    console.print(f"   錯誤：{str(e)[:100]}")
                    console.print(f"   原因：{error_reason}")

                    # 不可重試
                    if not retryable:
                        console.print(
                            f"\n[dim #B565D8]⚠️  此錯誤無法透過重試解決[/red]\n"
                        )

                        # 提供解決建議
                        show_error_solutions(e, operation_name)
                        raise

                    # 最後一次嘗試
                    if attempt == retries:
                        console.print(
                            f"\n[dim #B565D8]✗ {operation_name}失敗（已達最大重試次數）[/red]\n"
                        )

                        # 仍然顯示解決方案
                        show_error_solutions(e, operation_name)
                        raise

                    # 計算延遲時間
                    if config.exponential_backoff:
                        delay = min(
                            config.base_delay * (2 ** (attempt - 1)),
                            config.max_delay
                        )
                    else:
                        delay = config.base_delay

                    retry_stats['total_delay'] += delay

                    # 顯示重試提示
                    console.print(f"\n   [#B565D8]⏳ {delay:.0f} 秒後自動重試...[/#B565D8]")
                    time.sleep(delay)

            # 理論上不會到這裡
            if last_error:
                raise last_error

        return wrapper
    return decorator


def with_retry(operation_name: str, max_retries: int = 3):
    """
    簡化版重試裝飾器

    Args:
        operation_name: 操作名稱
        max_retries: 最大重試次數

    Returns:
        裝飾器函數

    Example:
        >>> @with_retry("語音辨識")
        >>> def transcribe_audio(audio_path):
        >>>     # API 調用
        >>>     pass
    """
    return api_retry(operation_name=operation_name, max_retries=max_retries, show_progress=True)


# 測試函數（僅用於開發測試）
if __name__ == "__main__":
    import random

    print("=" * 60)
    print("API 重試機制測試")
    print("=" * 60)

    # 測試 1：模擬暫時性錯誤（503）
    @with_retry("測試 API 調用", max_retries=3)
    def test_api_call_503():
        """模擬 503 錯誤，第 3 次成功"""
        if not hasattr(test_api_call_503, 'call_count'):
            test_api_call_503.call_count = 0

        test_api_call_503.call_count += 1

        if test_api_call_503.call_count < 3:
            raise Exception("503 Service Unavailable")

        return "成功！"

    # 測試 2：模擬不可重試錯誤（401）
    @with_retry("API 金鑰驗證", max_retries=3)
    def test_api_call_401():
        """模擬 401 錯誤"""
        raise Exception("401 Unauthorized: Invalid API Key")

    print("\n測試 1：暫時性錯誤（503）- 應該在第 3 次成功")
    try:
        result = test_api_call_503()
        print(f"結果：{result}")
    except Exception as e:
        print(f"失敗：{e}")

    print("\n" + "=" * 60)
    print("\n測試 2：不可重試錯誤（401）- 應該立即失敗並顯示解決方案")
    try:
        result = test_api_call_401()
        print(f"結果：{result}")
    except Exception as e:
        print(f"預期的失敗（已顯示解決方案）")
