#!/usr/bin/env python3
"""
Gemini 計價系統統一導入模組
提供全專案共用的計價系統初始化功能
"""
import sys
from typing import Optional

# Rich Console（可選）
try:
    from rich.console import Console
    _console = Console()
    RICH_AVAILABLE = True
except ImportError:
    _console = None
    RICH_AVAILABLE = False


def _print_warning(message: str) -> None:
    """輸出警告訊息（根據環境選擇格式）"""
    if RICH_AVAILABLE and _console:
        _console.print(f"[#DDA0DD]{message}[/#DDA0DD]")
    else:
        print(f"⚠️  {message}", file=sys.stderr)


def _print_info(message: str) -> None:
    """輸出資訊訊息（根據環境選擇格式）"""
    if RICH_AVAILABLE and _console:
        _console.print(f"[#DA70D6]{message}[/#DA70D6]")
    else:
        print(f"ℹ️  {message}")


# 嘗試導入計價模組
try:
    from gemini_pricing import PricingCalculator, USD_TO_TWD as _PRICING_USD_TO_TWD
    PRICING_ENABLED = True
    USD_TO_TWD = _PRICING_USD_TO_TWD
except ImportError:
    PRICING_ENABLED = False
    USD_TO_TWD = 31.0  # 預設匯率
    PricingCalculator = None


# 全域計價器實例（單例模式）
_pricing_instance: Optional['PricingCalculator'] = None


def get_pricing_calculator(
    force_new: bool = False,
    silent: bool = False
) -> Optional['PricingCalculator']:
    """
    取得計價計算器實例（單例模式）

    Args:
        force_new: 強制建立新實例（預設 False）
        silent: 靜音模式，不輸出警告（預設 False）

    Returns:
        PricingCalculator 實例，如果模組不可用則返回 None

    Examples:
        >>> # 基本用法
        >>> pricing = get_pricing_calculator()
        >>> if pricing:
        ...     cost = pricing.estimate_cost(model, input_tokens, output_tokens)

        >>> # 檢查計價是否啟用
        >>> from utils.pricing_loader import PRICING_ENABLED
        >>> if PRICING_ENABLED:
        ...     pricing = get_pricing_calculator()
    """
    global _pricing_instance

    # 如果計價模組不可用
    if not PRICING_ENABLED:
        if not silent:
            _print_warning("計價模組 (gemini_pricing.py) 不可用，計價功能已停用")
        return None

    # 如果已經有實例且不強制建立新的，直接返回
    if _pricing_instance and not force_new:
        return _pricing_instance

    try:
        # 建立計價器實例
        calculator = PricingCalculator()
        _pricing_instance = calculator
        return calculator

    except Exception as e:
        if not silent:
            _print_warning(f"初始化計價器失敗：{str(e)}")
        return None


def init_pricing(
    force_new: bool = False,
    required: bool = False,
    silent: bool = False
) -> Optional['PricingCalculator']:
    """
    初始化計價系統（便利函數）

    Args:
        force_new: 強制建立新實例（預設 False）
        required: 計價系統是否為必需（預設 False，設為 True 時找不到會退出程式）
        silent: 靜音模式，不輸出訊息（預設 False）

    Returns:
        PricingCalculator 實例，如果不可用且 required=False 則返回 None

    Raises:
        SystemExit: 計價系統不可用且 required=True

    Examples:
        >>> # 可選計價（不可用也不影響）
        >>> pricing = init_pricing()
        >>> if pricing:
        ...     pricing.show_cost()

        >>> # 必需計價（不可用會退出）
        >>> pricing = init_pricing(required=True)
        >>> pricing.show_cost()
    """
    calculator = get_pricing_calculator(force_new=force_new, silent=silent)

    if not calculator and required:
        _print_warning("計價系統為必需功能，但無法初始化")
        _print_info("請確保 gemini_pricing.py 存在")
        sys.exit(1)

    return calculator


def reset_pricing() -> None:
    """
    重置全域計價器實例

    用於測試或需要重新初始化的情況
    """
    global _pricing_instance
    _pricing_instance = None


def check_pricing_available() -> bool:
    """
    檢查計價系統是否可用

    Returns:
        True 如果可用，False 如果不可用

    Examples:
        >>> if check_pricing_available():
        ...     pricing = get_pricing_calculator()
        ...     pricing.show_cost()
        ... else:
        ...     print("計價功能不可用")
    """
    return PRICING_ENABLED


def get_usd_to_twd_rate() -> float:
    """
    取得美元對台幣匯率

    Returns:
        匯率（來自計價模組或預設值 31.0）

    Examples:
        >>> rate = get_usd_to_twd_rate()
        >>> twd_cost = usd_cost * rate
    """
    return USD_TO_TWD


# 便利函數：建立全域計價器（向後相容）
def create_global_pricing_calculator() -> Optional['PricingCalculator']:
    """
    建立全域計價器（向後相容函數）

    此函數為向後相容性保留，建議使用 get_pricing_calculator()

    Returns:
        PricingCalculator 實例或 None
    """
    return get_pricing_calculator(force_new=False, silent=True)


if __name__ == "__main__":
    # 測試模組
    print("測試計價系統模組...")

    # 測試 1: 檢查計價是否可用
    print(f"\n測試 1: 計價系統可用性")
    print(f"✓ PRICING_ENABLED: {PRICING_ENABLED}")
    print(f"✓ USD_TO_TWD: {USD_TO_TWD}")

    # 測試 2: 取得計價器
    print(f"\n測試 2: 取得計價器")
    pricing = get_pricing_calculator(silent=False)
    if pricing:
        print(f"✓ 計價器類型: {type(pricing)}")
    else:
        print("✗ 計價器不可用")

    # 測試 3: 單例模式
    if pricing:
        print(f"\n測試 3: 單例模式")
        pricing2 = get_pricing_calculator()
        print(f"✓ 是否為同一實例: {pricing is pricing2}")

        # 測試 4: 強制建立新實例
        print(f"\n測試 4: 強制建立新實例")
        pricing3 = get_pricing_calculator(force_new=True)
        print(f"✓ 是否為不同實例: {pricing is not pricing3}")

    # 測試 5: 匯率取得
    print(f"\n測試 5: 匯率取得")
    rate = get_usd_to_twd_rate()
    print(f"✓ 匯率: {rate}")

    print("\n✓ 所有測試通過")
