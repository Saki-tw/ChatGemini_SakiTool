"""
ChatGemini_SakiTool 共用工具模組
提供 API 客戶端、計價系統、思考模式、性能監控、i18n 國際化等共用功能

**載入策略**: 延遲載入 (Lazy Loading)
- 只在實際使用時才載入子模組
- 大幅減少啟動時間 (從 16.7s 降至 <1s)
- 保持向後兼容性

作者: Saki-tw (with Claude Code)
日期: 2025-10-29
版本: 2.0.0 - 延遲載入重構
"""

# ============================================================================
# 延遲載入實作 (透過 __getattr__)
# ============================================================================
# 注意: 此檔案不再直接導入任何子模組
# 所有導入都透過 __getattr__ 延遲執行

# 全域快取 - 避免重複導入
_module_cache = {}
_i18n_initialized = False


def __getattr__(name):
    """
    延遲載入子模組

    當外部代碼嘗試訪問 utils 模組的屬性時，此函數會被調用。
    我們在此時才真正導入所需的子模組，實現延遲載入。

    Args:
        name: 屬性名稱

    Returns:
        屬性值 (函數、類別或常量)

    Raises:
        AttributeError: 屬性不存在
    """
    # 檢查快取
    if name in _module_cache:
        return _module_cache[name]

    # ========================================================================
    # i18n 國際化模組
    # ========================================================================
    if name in ('t', '_', 'safe_t', 'get_current_language', 'switch_language',
                'get_available_languages', 'init_i18n'):
        from .i18n import (
            t, _, safe_t, get_current_language, switch_language,
            get_available_languages, init_i18n
        )

        # 批次快取所有 i18n 函數
        _module_cache.update({
            't': t,
            '_': _,
            'safe_t': safe_t,
            'get_current_language': get_current_language,
            'switch_language': switch_language,
            'get_available_languages': get_available_languages,
            'init_i18n': init_i18n,
        })

        # 延遲初始化 i18n (只在首次使用時)
        # 注意: 不再自動初始化，由調用方決定是否需要初始化

        return _module_cache[name]

    # ========================================================================
    # API 客戶端
    # ========================================================================
    elif name in ('get_gemini_client', 'init_api_client', 'reset_client'):
        from .api_client import get_gemini_client, init_api_client, reset_client

        _module_cache.update({
            'get_gemini_client': get_gemini_client,
            'init_api_client': init_api_client,
            'reset_client': reset_client,
        })

        return _module_cache[name]

    # ========================================================================
    # 計價系統
    # ========================================================================
    elif name in ('get_pricing_calculator', 'PRICING_ENABLED', 'USD_TO_TWD',
                  'check_pricing_available'):
        from .pricing_loader import (
            get_pricing_calculator,
            PRICING_ENABLED,
            USD_TO_TWD,
            check_pricing_available
        )

        _module_cache.update({
            'get_pricing_calculator': get_pricing_calculator,
            'PRICING_ENABLED': PRICING_ENABLED,
            'USD_TO_TWD': USD_TO_TWD,
            'check_pricing_available': check_pricing_available,
        })

        return _module_cache[name]

    # ========================================================================
    # 思考模式輔助
    # ========================================================================
    elif name in ('supports_thinking', 'create_generation_config',
                  'get_thinking_config', 'estimate_thinking_cost',
                  'is_thinking_enabled_in_config', 'THINKING_MODELS',
                  'MODEL_GEMINI_2_5_PRO', 'MODEL_GEMINI_2_5_FLASH',
                  'MODEL_GEMINI_2_0_FLASH_THINKING'):
        from .thinking_helpers import (
            supports_thinking,
            create_generation_config,
            get_thinking_config,
            estimate_thinking_cost,
            is_thinking_enabled_in_config,
            THINKING_MODELS,
            MODEL_GEMINI_2_5_PRO,
            MODEL_GEMINI_2_5_FLASH,
            MODEL_GEMINI_2_0_FLASH_THINKING,
        )

        _module_cache.update({
            'supports_thinking': supports_thinking,
            'create_generation_config': create_generation_config,
            'get_thinking_config': get_thinking_config,
            'estimate_thinking_cost': estimate_thinking_cost,
            'is_thinking_enabled_in_config': is_thinking_enabled_in_config,
            'THINKING_MODELS': THINKING_MODELS,
            'MODEL_GEMINI_2_5_PRO': MODEL_GEMINI_2_5_PRO,
            'MODEL_GEMINI_2_5_FLASH': MODEL_GEMINI_2_5_FLASH,
            'MODEL_GEMINI_2_0_FLASH_THINKING': MODEL_GEMINI_2_0_FLASH_THINKING,
        })

        return _module_cache[name]

    # ========================================================================
    # 性能監控
    # ========================================================================
    elif name in ('get_performance_monitor', 'reset_monitor', 'measure',
                  'track_performance', 'print_performance_summary',
                  'print_bottleneck_report', 'export_performance_report',
                  'PerformanceMonitor'):
        from .performance_monitor import (
            get_performance_monitor,
            reset_monitor,
            measure,
            track_performance,
            print_performance_summary,
            print_bottleneck_report,
            export_performance_report,
            PerformanceMonitor
        )

        _module_cache.update({
            'get_performance_monitor': get_performance_monitor,
            'reset_monitor': reset_monitor,
            'measure': measure,
            'track_performance': track_performance,
            'print_performance_summary': print_performance_summary,
            'print_bottleneck_report': print_bottleneck_report,
            'export_performance_report': export_performance_report,
            'PerformanceMonitor': PerformanceMonitor,
        })

        return _module_cache[name]

    # ========================================================================
    # 輸入輔助（prompt-toolkit 整合）
    # ========================================================================
    elif name in ('get_user_input', 'clear_input_history',
                  'is_advanced_input_available', 'PROMPT_TOOLKIT_AVAILABLE'):
        from .input_helpers import (
            get_user_input,
            clear_input_history,
            is_advanced_input_available,
            PROMPT_TOOLKIT_AVAILABLE
        )

        _module_cache.update({
            'get_user_input': get_user_input,
            'clear_input_history': clear_input_history,
            'is_advanced_input_available': is_advanced_input_available,
            'PROMPT_TOOLKIT_AVAILABLE': PROMPT_TOOLKIT_AVAILABLE,
        })

        return _module_cache[name]

    # ========================================================================
    # 屬性不存在
    # ========================================================================
    raise AttributeError(f"module 'utils' has no attribute '{name}'")


# ============================================================================
# 明確定義 __all__ (文檔與 IDE 支援)
# ============================================================================
__all__ = [
    # i18n 國際化
    't',
    '_',
    'safe_t',
    'get_current_language',
    'switch_language',
    'get_available_languages',
    'init_i18n',
    # API 客戶端
    'get_gemini_client',
    'init_api_client',
    'reset_client',
    # 計價系統
    'get_pricing_calculator',
    'PRICING_ENABLED',
    'USD_TO_TWD',
    'check_pricing_available',
    # 思考模式
    'supports_thinking',
    'create_generation_config',
    'get_thinking_config',
    'estimate_thinking_cost',
    'is_thinking_enabled_in_config',
    'THINKING_MODELS',
    'MODEL_GEMINI_2_5_PRO',
    'MODEL_GEMINI_2_5_FLASH',
    'MODEL_GEMINI_2_0_FLASH_THINKING',
    # 性能監控
    'get_performance_monitor',
    'reset_monitor',
    'measure',
    'track_performance',
    'print_performance_summary',
    'print_bottleneck_report',
    'export_performance_report',
    'PerformanceMonitor',
    # 輸入輔助
    'get_user_input',
    'clear_input_history',
    'is_advanced_input_available',
    'PROMPT_TOOLKIT_AVAILABLE',
]

__version__ = '2.0.0'

# ============================================================================
# 輔助函數 - 手動初始化 i18n (可選)
# ============================================================================
def ensure_i18n_initialized(inject_builtins: bool = True):
    """
    確保 i18n 已初始化

    此函數可由主程式明確調用，以確保 i18n 系統在需要時已初始化。
    這比自動初始化更明確、可控。

    Args:
        inject_builtins: 是否將 t() 注入到 builtins (預設 True)

    Returns:
        是否成功初始化
    """
    global _i18n_initialized

    if _i18n_initialized:
        return True

    try:
        from .i18n import init_i18n
        init_i18n(inject_builtins=inject_builtins)
        _i18n_initialized = True
        return True
    except Exception as e:
        import sys
        print(f"⚠️  i18n 初始化失敗: {e}", file=sys.stderr)
        return False


# 將 ensure_i18n_initialized 加入 __all__
__all__.append('ensure_i18n_initialized')
