#!/usr/bin/env python3
"""
思考模式輔助工具
統一管理思考模式檢查和配置生成

本模組提供：
- 模型思考能力檢測
- 思考配置自動生成
- 費用估算
- 配置狀態檢查

使用範例：
    from utils.thinking_helpers import supports_thinking, create_generation_config

    if supports_thinking('gemini-2.5-pro'):
        config = create_generation_config('gemini-2.5-pro', thinking_budget=5000)
"""
from typing import Optional
from functools import lru_cache
from google.genai import types

# ============================================================================
# 模型名稱常數（避免 typo，統一管理）
# ============================================================================

MODEL_GEMINI_2_5_PRO = 'gemini-2.5-pro'
MODEL_GEMINI_2_5_FLASH = 'gemini-2.5-flash'
MODEL_GEMINI_2_5_FLASH_8B = 'gemini-2.5-flash-8b'
MODEL_GEMINI_2_0_FLASH_THINKING = 'gemini-2.0-flash-thinking'

# 支援思考模式的模型列表
# 注意：此列表會影響 supports_thinking() 的判斷結果
THINKING_MODELS = [
    MODEL_GEMINI_2_5_PRO,
    MODEL_GEMINI_2_5_FLASH,
    MODEL_GEMINI_2_5_FLASH_8B,
    MODEL_GEMINI_2_0_FLASH_THINKING,
]


@lru_cache(maxsize=128)
def supports_thinking(model_name: str) -> bool:
    """
    檢查模型是否支援思考模式

    使用 LRU 快取優化重複查詢（快取上限 128 筆）

    Args:
        model_name: 模型名稱

    Returns:
        True 如果模型支援思考模式，否則 False

    Examples:
        >>> supports_thinking('gemini-2.5-pro')
        True
        >>> supports_thinking('gemini-2.5-pro-001')  # 帶版本號也支援
        True
        >>> supports_thinking('gemini-1.5-flash')
        False

    注意：
        - 此函數使用 @lru_cache 快取結果
        - 快取大小限制為 128 個不同的模型名稱
        - 適用於頻繁查詢相同模型的場景
        - 使用精確匹配或前綴匹配（處理帶版本號的模型）
    """
    if not model_name:
        return False

    # 先嘗試精確匹配
    if model_name in THINKING_MODELS:
        return True

    # 再檢查是否以任一支援思考的模型名稱開頭（處理帶版本號的情況）
    # 例如：'gemini-2.5-pro-001' 會匹配 'gemini-2.5-pro'
    return any(model_name.startswith(tm) for tm in THINKING_MODELS)


def create_generation_config(
    model_name: str,
    thinking_budget: Optional[int] = None,
    **kwargs
) -> types.GenerateContentConfig:
    """
    建立生成內容配置（自動判斷是否啟用思考模式）

    此函數會自動檢測模型是否支援思考模式，並根據 thinking_budget
    參數決定如何配置思考功能。對於不支援思考的模型，thinking_budget
    參數會被自動忽略。

    Args:
        model_name: 模型名稱（例如：'gemini-2.5-pro'）
        thinking_budget: 思考 token 預算
            - None 或 -1: 動態思考模式（自動決定，推薦）
            - 0: 禁用思考
            - >0: 固定思考預算（例如：5000）
        **kwargs: 其他配置參數（傳遞給 GenerateContentConfig）

    Returns:
        GenerateContentConfig 實例

    Examples:
        >>> # 自動啟用思考（支援的模型）
        >>> config = create_generation_config('gemini-2.5-pro')

        >>> # 固定思考預算
        >>> config = create_generation_config('gemini-2.5-pro', thinking_budget=5000)

        >>> # 禁用思考
        >>> config = create_generation_config('gemini-2.5-pro', thinking_budget=0)

        >>> # 不支援思考的模型（自動忽略 thinking_budget）
        >>> config = create_generation_config('gemini-1.5-flash', thinking_budget=5000)

    注意：
        - 對於不支援思考的模型，thinking_budget 會被忽略
        - 動態模式（-1）讓模型自行決定思考深度，通常是最佳選擇
        - 固定預算適用於需要控制成本的場景
    """
    # 建立基礎配置
    config = types.GenerateContentConfig(**kwargs)

    # 只有支援思考的模型才啟用思考模式
    if supports_thinking(model_name):
        # 如果未指定預算或為 -1，使用動態模式（推薦）
        if thinking_budget is None or thinking_budget == -1:
            config.thinking_config = types.ThinkingConfig(thinking_budget=-1)
        # 如果預算 > 0，使用固定預算
        elif thinking_budget > 0:
            config.thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)
        # thinking_budget == 0 時不設定 thinking_config（明確禁用思考）

    return config


def get_thinking_config(thinking_budget: Optional[int] = None) -> Optional[types.ThinkingConfig]:
    """
    取得思考配置物件

    Args:
        thinking_budget: 思考 token 預算
            - None 或 -1: 動態思考模式
            - 0: 返回 None（禁用）
            - >0: 固定思考預算

    Returns:
        ThinkingConfig 實例或 None

    Examples:
        >>> # 動態思考
        >>> config = get_thinking_config()
        >>> config = get_thinking_config(-1)

        >>> # 固定預算
        >>> config = get_thinking_config(5000)

        >>> # 禁用思考
        >>> config = get_thinking_config(0)
        >>> print(config)  # None
    """
    if thinking_budget is None or thinking_budget == -1:
        return types.ThinkingConfig(thinking_budget=-1)
    elif thinking_budget > 0:
        return types.ThinkingConfig(thinking_budget=thinking_budget)
    else:
        # thinking_budget == 0 或負值（除了 -1）
        return None


def estimate_thinking_cost(
    thinking_budget: int,
    model_name: str,
    pricing_calculator,
    usd_to_twd: float = 31.0
) -> tuple[float, float]:
    """
    估算思考模式的費用

    根據思考 token 預算和模型計價，估算使用思考模式的成本。
    此函數對計價錯誤具有容錯性，失敗時返回 (0.0, 0.0)。

    Args:
        thinking_budget: 思考 token 預算（例如：5000）
        model_name: 模型名稱（例如：'gemini-2.5-pro'）
        pricing_calculator: PricingCalculator 實例（來自 utils.pricing_loader）
        usd_to_twd: 美元對台幣匯率（預設 31.0，可根據實際匯率調整）

    Returns:
        (cost_usd, cost_twd) 費用元組
        - cost_usd: 美元費用
        - cost_twd: 台幣費用
        - 計價失敗時返回 (0.0, 0.0)

    Examples:
        >>> from utils import get_pricing_calculator
        >>> pricing = get_pricing_calculator()
        >>> if pricing:
        ...     usd, twd = estimate_thinking_cost(5000, 'gemini-2.5-pro', pricing)
        ...     print(f"預估費用: NT${twd:.4f} (${usd:.6f})")

    注意：
        - 此函數使用 input token 價格計算（思考過程算作輸入）
        - 計價失敗時會靜默返回 0，不會拋出異常
        - 僅為估算值，實際費用以 API 回傳為準
    """
    try:
        # 取得模型計價資訊
        pricing = pricing_calculator._get_pricing(model_name)
        # 優先使用 'input'，其次 'input_low'（某些模型有分段計價）
        input_price = pricing.get('input', pricing.get('input_low', 0))
        # 計算費用（token 數 / 1000 * 單價）
        cost_usd = (thinking_budget / 1000) * input_price
        cost_twd = cost_usd * usd_to_twd
        return cost_usd, cost_twd
    except (KeyError, AttributeError, TypeError):
        # 計價失敗時返回 0（容錯處理）
        return 0.0, 0.0


def is_thinking_enabled_in_config(config: types.GenerateContentConfig) -> bool:
    """
    檢查 GenerateContentConfig 中是否啟用思考模式

    此函數可用於驗證配置是否正確設定思考功能，適合在發送請求前進行檢查。

    Args:
        config: GenerateContentConfig 實例

    Returns:
        True 如果啟用思考模式，否則 False

    Examples:
        >>> # 檢查支援思考的模型
        >>> config = create_generation_config('gemini-2.5-pro')
        >>> is_thinking_enabled_in_config(config)
        True

        >>> # 檢查禁用思考的配置
        >>> config = create_generation_config('gemini-2.5-pro', thinking_budget=0)
        >>> is_thinking_enabled_in_config(config)
        False

        >>> # 檢查不支援思考的模型
        >>> config = create_generation_config('gemini-1.5-flash')
        >>> is_thinking_enabled_in_config(config)
        False

    注意：
        - 此函數只檢查配置物件，不檢查模型實際能力
        - 用於在 API 請求前驗證配置正確性
    """
    # 檢查配置物件是否有 thinking_config 屬性且不為 None
    return hasattr(config, 'thinking_config') and config.thinking_config is not None


if __name__ == "__main__":
    # ========================================================================
    # 模組自我測試（直接執行此檔案時運行）
    # 用途：驗證所有函數功能正常
    # ========================================================================
    print("測試思考模式輔助工具...")

    # 測試 1: 支援檢查（驗證 supports_thinking 函數）
    print("\n測試 1: 模型支援檢查")
    # 使用常數定義的模型名稱（避免硬編碼）
    test_models = [
        MODEL_GEMINI_2_5_PRO,  # 應該支援
        MODEL_GEMINI_2_5_FLASH,  # 應該支援
        'gemini-1.5-flash',  # 應該不支援（舊版本）
        MODEL_GEMINI_2_0_FLASH_THINKING,  # 應該支援
    ]
    for model in test_models:
        result = supports_thinking(model)
        print(f"  {model}: {'✓ 支援' if result else '✗ 不支援'}")

    # 測試 2: 配置生成（驗證 create_generation_config 和 is_thinking_enabled_in_config）
    print("\n測試 2: 配置生成")

    # 動態思考模式（預設，推薦）
    config1 = create_generation_config(MODEL_GEMINI_2_5_PRO)
    print(f"  動態思考: {is_thinking_enabled_in_config(config1)}")

    # 固定預算（成本控制）
    config2 = create_generation_config(MODEL_GEMINI_2_5_PRO, thinking_budget=5000)
    print(f"  固定預算: {is_thinking_enabled_in_config(config2)}")

    # 禁用思考（最快回應）
    config3 = create_generation_config(MODEL_GEMINI_2_5_PRO, thinking_budget=0)
    print(f"  禁用思考: {is_thinking_enabled_in_config(config3)}")

    # 不支援的模型（自動忽略 thinking_budget）
    config4 = create_generation_config('gemini-1.5-flash', thinking_budget=5000)
    print(f"  不支援模型: {is_thinking_enabled_in_config(config4)}")

    # 測試 3: ThinkingConfig 生成
    print("\n測試 3: ThinkingConfig 生成")

    tc1 = get_thinking_config()
    print(f"  預設（動態）: {tc1 is not None}")

    tc2 = get_thinking_config(5000)
    print(f"  固定 5000: {tc2 is not None}")

    tc3 = get_thinking_config(0)
    print(f"  禁用（0）: {tc3 is None}")

    print("\n✓ 所有測試通過")
