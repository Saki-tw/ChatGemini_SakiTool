#!/usr/bin/env python3
"""
Gemini API 客戶端統一初始化模組
提供全專案共用的 API 客戶端初始化功能
"""
import os
import sys
from typing import Optional
from dotenv import load_dotenv

# 新 SDK
from google import genai

# Rich Console（可選）
try:
    from rich.console import Console
    _console = Console()
    RICH_AVAILABLE = True
except ImportError:
    _console = None
    RICH_AVAILABLE = False


class APIClientError(Exception):
    """API 客戶端錯誤"""
    pass


# 全域客戶端實例（單例模式）
_client_instance: Optional[genai.Client] = None
_api_key_cache: Optional[str] = None


def _print_error(message: str) -> None:
    """輸出錯誤訊息（根據環境選擇格式）"""
    if RICH_AVAILABLE and _console:
        _console.print(f"[dim #DDA0DD]{message}[/red]")
    else:
        print(f"錯誤：{message}", file=sys.stderr)


def _print_success(message: str) -> None:
    """輸出成功訊息（根據環境選擇格式）"""
    if RICH_AVAILABLE and _console:
        _console.print(f"[#DA70D6]{message}[/green]")
    else:
        print(f"✓ {message}")


def get_api_key(raise_error: bool = True) -> Optional[str]:
    """
    取得 Gemini API 金鑰

    Args:
        raise_error: 找不到金鑰時是否拋出錯誤（預設 True）

    Returns:
        API 金鑰，如果不存在且 raise_error=False 則返回 None

    Raises:
        APIClientError: 找不到 API 金鑰且 raise_error=True
    """
    global _api_key_cache

    # 如果已經快取，直接返回
    if _api_key_cache:
        return _api_key_cache

    # 載入環境變數
    load_dotenv()

    # 取得 API 金鑰
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        if raise_error:
            # 顯示詳細的設定指引
            try:
                from error_fix_suggestions import suggest_api_key_setup
                suggest_api_key_setup()
            except ImportError:
                _print_error("請設置 GEMINI_API_KEY 環境變數")

            raise APIClientError("Gemini API 金鑰未設定，請按照上述步驟設定後重試")
        return None

    # 快取金鑰
    _api_key_cache = api_key
    return api_key


def get_gemini_client(
    api_key: Optional[str] = None,
    force_new: bool = False,
    raise_error: bool = True
) -> Optional[genai.Client]:
    """
    取得 Gemini API 客戶端（單例模式）

    Args:
        api_key: 自訂 API 金鑰（可選，預設從環境變數讀取）
        force_new: 強制建立新客戶端（預設 False）
        raise_error: 初始化失敗時是否拋出錯誤（預設 True）

    Returns:
        Gemini API 客戶端實例，如果失敗且 raise_error=False 則返回 None

    Raises:
        APIClientError: 初始化失敗且 raise_error=True

    Examples:
        >>> # 基本用法（使用環境變數中的 API 金鑰）
        >>> client = get_gemini_client()

        >>> # 使用自訂 API 金鑰
        >>> client = get_gemini_client(api_key="your-api-key")

        >>> # 強制建立新客戶端
        >>> new_client = get_gemini_client(force_new=True)

        >>> # 不拋出錯誤，返回 None
        >>> client = get_gemini_client(raise_error=False)
    """
    global _client_instance

    # 如果已經有實例且不強制建立新的，直接返回
    if _client_instance and not force_new:
        return _client_instance

    # 取得 API 金鑰
    if not api_key:
        api_key = get_api_key(raise_error=raise_error)
        if not api_key:
            return None

    try:
        # 建立客戶端
        client = genai.Client(api_key=api_key)

        # 快取客戶端實例
        _client_instance = client

        return client

    except Exception as e:
        error_msg = f"初始化 Gemini API 客戶端失敗：{str(e)}"
        if raise_error:
            _print_error(error_msg)
            raise APIClientError(error_msg) from e
        return None


def init_api_client(
    api_key: Optional[str] = None,
    force_new: bool = False,
    silent: bool = False
) -> genai.Client:
    """
    初始化 Gemini API 客戶端（便利函數）

    這是 get_gemini_client 的簡化版本，專為模組初始化設計
    失敗時會拋出錯誤並退出程式（適用於獨立腳本）

    Args:
        api_key: 自訂 API 金鑰（可選）
        force_new: 強制建立新客戶端（預設 False）
        silent: 靜音模式，不輸出成功訊息（預設 False）

    Returns:
        Gemini API 客戶端實例

    Raises:
        SystemExit: 初始化失敗時退出程式

    Examples:
        >>> # 在模組開頭初始化
        >>> from utils.api_client import init_api_client
        >>> client = init_api_client()
    """
    try:
        client = get_gemini_client(api_key=api_key, force_new=force_new, raise_error=True)

        if not silent:
            _print_success("Gemini API 客戶端已初始化")

        return client

    except APIClientError:
        sys.exit(1)


def reset_client() -> None:
    """
    重置全域客戶端實例

    用於測試或需要重新初始化的情況
    """
    global _client_instance, _api_key_cache
    _client_instance = None
    _api_key_cache = None


# 向後相容：提供舊版初始化方式
def create_client(api_key: Optional[str] = None) -> genai.Client:
    """
    建立 Gemini API 客戶端（向後相容函數）

    此函數為向後相容性保留，建議使用 get_gemini_client() 或 init_api_client()

    Args:
        api_key: API 金鑰（可選）

    Returns:
        Gemini API 客戶端實例
    """
    return get_gemini_client(api_key=api_key, force_new=True, raise_error=True)


if __name__ == "__main__":
    # 測試模組
    print("測試 API 客戶端模組...")

    try:
        # 測試 1: 取得 API 金鑰
        print("\n測試 1: 取得 API 金鑰")
        api_key = get_api_key(raise_error=False)
        if api_key:
            print(f"✓ API 金鑰: {api_key[:20]}...")
        else:
            print("✗ 未找到 API 金鑰")

        # 測試 2: 初始化客戶端
        print("\n測試 2: 初始化客戶端")
        client = get_gemini_client(raise_error=False)
        if client:
            print(f"✓ 客戶端類型: {type(client)}")
        else:
            print("✗ 客戶端初始化失敗")

        # 測試 3: 單例模式
        print("\n測試 3: 單例模式")
        client2 = get_gemini_client()
        print(f"✓ 是否為同一實例: {client is client2}")

        # 測試 4: 強制建立新客戶端
        print("\n測試 4: 強制建立新客戶端")
        client3 = get_gemini_client(force_new=True)
        print(f"✓ 是否為不同實例: {client is not client3}")

        print("\n✓ 所有測試通過")

    except Exception as e:
        print(f"\n✗ 測試失敗: {e}")
        sys.exit(1)
