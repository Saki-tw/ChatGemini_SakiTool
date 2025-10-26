"""
ChatGemini_SakiTool 共用工具模組
提供 API 客戶端、計價系統、思考模式、性能監控、i18n 國際化等共用功能
"""

# i18n 國際化系統（優先載入並自動初始化）
from .i18n import (
    t,
    _,
    get_current_language,
    switch_language,
    get_available_languages,
    init_i18n
)

# 自動初始化 i18n（注入到 builtins，讓所有模組都可以直接使用 t()）
try:
    init_i18n(inject_builtins=True)
except Exception as e:
    # 如果初始化失敗，不中斷其他功能
    import sys
    print(f"⚠️  i18n 初始化失敗: {e}", file=sys.stderr)

from .api_client import get_gemini_client, init_api_client, reset_client
from .pricing_loader import (
    get_pricing_calculator,
    PRICING_ENABLED,
    USD_TO_TWD,
    check_pricing_available
)
from .thinking_helpers import (
    supports_thinking,
    create_generation_config,
    get_thinking_config,
    estimate_thinking_cost,
    is_thinking_enabled_in_config,
    THINKING_MODELS,
    MODEL_GEMINI_2_5_PRO,
    MODEL_GEMINI_2_5_FLASH,
    MODEL_GEMINI_2_5_FLASH_8B,
    MODEL_GEMINI_2_0_FLASH_THINKING,
)
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

__all__ = [
    # i18n 國際化
    't',
    '_',
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
    'MODEL_GEMINI_2_5_FLASH_8B',
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
]

__version__ = '1.1.0'
