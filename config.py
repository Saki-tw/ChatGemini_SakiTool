#!/usr/bin/env python3
"""
ChatGemini_SakiTool - 配置檔案
版本：1.0.0
用途：管理模組啟用/停用及系統參數
"""

# ==========================================
# 模組啟用設定
# ==========================================

MODULES = {
    # ========== 核心模組（建議保持啟用）==========

    'pricing': {
        'enabled': True,
        'required': True,  # 核心功能，不可停用
        'description': '計價系統（新台幣即時顯示）',
        'dependencies': [],
        'file': 'gemini_pricing.py'
    },

    'cache_manager': {
        'enabled': True,
        'required': False,
        'description': '快取管理（節省 75-90% API 成本）',
        'dependencies': [],
        'file': 'gemini_cache_manager.py'
    },

    'file_manager': {
        'enabled': True,
        'required': False,
        'description': '檔案上傳管理（支援大檔案）',
        'dependencies': [],
        'file': 'gemini_file_manager.py'
    },

    # ========== 可選模組 ==========

    'translator': {
        'enabled': True,
        'required': False,
        'description': '翻譯功能（思考過程雙語對照）',
        'dependencies': ['deep-translator'],
        'file': 'gemini_translator.py',
        'notes': '需要 deep-translator 套件'
    },

    'image_analyzer': {
        'enabled': False,
        'required': False,
        'description': '圖像分析（8 種預設任務）',
        'dependencies': ['Pillow'],
        'file': 'gemini_image_analyzer.py',
        'notes': '需要 Pillow 套件'
    },

    'video_analyzer': {
        'enabled': False,
        'required': False,
        'description': '影片分析（最長 2 小時）',
        'dependencies': [],
        'file': 'gemini_video_analyzer.py',
        'notes': '獨立工具，可從命令列調用'
    },

    'veo_generator': {
        'enabled': False,
        'required': False,
        'description': 'Veo 影片生成（8 秒 720p/1080p）',
        'dependencies': [],
        'file': 'gemini_veo_generator.py',
        'notes': '需要 Veo API 權限'
    },

    # ========== 影音功能模組 ==========

    'flow_engine': {
        'enabled': False,
        'required': False,
        'description': 'Flow 引擎（自然語言影片生成，突破 8 秒限制）',
        'dependencies': ['ffmpeg-python'],
        'file': 'gemini_flow_engine.py',
        'notes': '需要系統安裝 ffmpeg，且需要 Veo API 權限'
    },

    'video_preprocessor': {
        'enabled': False,
        'required': False,
        'description': '影片預處理（分割、關鍵幀提取）',
        'dependencies': ['ffmpeg-python'],
        'file': 'gemini_video_preprocessor.py',
        'notes': '需要系統安裝 ffmpeg'
    },

    'video_compositor': {
        'enabled': False,
        'required': False,
        'description': '影片合併（無損合併）',
        'dependencies': ['ffmpeg-python'],
        'file': 'gemini_video_compositor.py',
        'notes': '需要系統安裝 ffmpeg'
    },

    'audio_processor': {
        'enabled': True,
        'required': False,
        'description': '音訊處理（提取、合併、音量調整、BGM、淡入淡出）',
        'dependencies': ['ffmpeg-python'],
        'file': 'gemini_audio_processor.py',
        'notes': '需要系統安裝 ffmpeg'
    },

    'imagen_generator': {
        'enabled': True,
        'required': False,
        'description': 'Imagen 圖片生成（Text-to-Image、編輯、放大）',
        'dependencies': [],
        'file': 'gemini_imagen_generator.py',
        'notes': '需要 Imagen API 權限'
    },

    'video_effects': {
        'enabled': True,
        'required': False,
        'description': '影片特效處理（時間裁切、濾鏡、速度調整、浮水印）',
        'dependencies': ['ffmpeg-python'],
        'file': 'gemini_video_effects.py',
        'notes': '需要系統安裝 ffmpeg，部分功能需重新編碼'
    },

    'subtitle_generator': {
        'enabled': True,
        'required': False,
        'description': '字幕生成（語音辨識、字幕燒錄）',
        'dependencies': ['ffmpeg-python'],
        'file': 'gemini_subtitle_generator.py',
        'notes': '需要系統安裝 ffmpeg，使用 Gemini API 進行語音辨識'
    },

    # ========== CodeGemini 整合模組 ==========

    'codebase_embedding': {
        'enabled': False,
        'required': False,
        'description': 'Codebase Embedding（程式碼庫向量化、對話記錄搜尋）',
        'dependencies': ['numpy'],
        'file': 'CodeGemini/codebase_embedding.py',
        'notes': '使用 Gemini Text Embedding API（免費），支援語意搜尋'
    },

    # ========== 進階功能（自動化增強）==========

    'api_retry': {
        'enabled': True,
        'required': False,
        'description': 'API 自動重試機制（指數退避、智能錯誤分類）',
        'dependencies': [],
        'file': 'api_retry_wrapper.py',
        'notes': '自動包裝所有 API 呼叫，失敗時自動重試'
    },

    'error_diagnostics': {
        'enabled': True,
        'required': False,
        'description': '智能錯誤診斷（自動診斷、一鍵修復建議）',
        'dependencies': [],
        'file': 'error_diagnostics.py',
        'notes': '錯誤發生時自動診斷並提供解決方案'
    },

    'conversation_suggestion': {
        'enabled': True,
        'required': False,
        'description': '相關對話建議（自動搜尋相似歷史對話）',
        'dependencies': [],
        'file': 'gemini_conversation_suggestion.py',
        'notes': '需要 codebase_embedding 啟用，基於向量搜尋',
        'top_k': 3,
        'min_similarity': 0.7
    },

    'smart_triggers': {
        'enabled': True,
        'required': False,
        'description': '智能觸發器（意圖檢測、自動觸發功能）',
        'dependencies': [],
        'file': 'gemini_smart_triggers.py',
        'notes': '自動檢測使用者意圖，觸發 CodeGemini 功能'
    },

    'performance': {
        'enabled': True,
        'required': False,
        'description': '性能優化（LRU 快取、並行處理）',
        'dependencies': [],
        'file': 'gemini_performance.py',
        'notes': '自動優化常用函數，提升性能'
    },

    'clip_advisor': {
        'enabled': True,
        'required': False,
        'description': 'AI 剪輯建議（智能片段推薦、參與度評分）',
        'dependencies': ['ffmpeg-python'],
        'file': 'gemini_clip_advisor.py',
        'notes': '影片分析時自動提供剪輯建議'
    },

    'video_summarizer': {
        'enabled': True,
        'required': False,
        'description': '影片智能摘要（多層次摘要、章節標記）',
        'dependencies': ['ffmpeg-python'],
        'file': 'gemini_video_summarizer.py',
        'notes': '影片分析時自動生成摘要'
    },

    'batch_processor': {
        'enabled': True,
        'required': False,
        'description': '批次處理系統（排程、進度追蹤）',
        'dependencies': [],
        'file': 'gemini_batch_processor.py',
        'notes': '支援批次任務處理，最多 3 個並行'
    },

    'media_viewer': {
        'enabled': True,
        'required': False,
        'description': '媒體查看器（檔案資訊、AI 分析）',
        'dependencies': ['Pillow'],
        'file': 'gemini_media_viewer.py',
        'notes': '附加檔案時自動顯示檔案資訊'
    },
}

# ==========================================
# 系統參數
# ==========================================

# Gemini 模型設定
DEFAULT_MODEL = "gemini-2.5-flash"  # 預設使用的 Gemini 模型

# 支援的模型列表（用於 gemini_chat.py 中的選單）
AVAILABLE_MODELS = [
    "gemini-2.5-pro",           # 最強大，支援思考模式
    "gemini-2.5-flash",         # 推薦，快速且智慧
    "gemini-2.5-flash-8b",      # 最便宜
    "gemini-2.0-flash-exp",     # 實驗性
]

# 各模型上下文窗口大小（tokens）- 官方精確值
MODEL_CONTEXT_LIMITS = {
    'gemini-2.5-pro': 2_097_152,        # 2,097,152 tokens (2^21, 約 200萬)
    'gemini-2.5-flash': 1_048_576,      # 1,048,576 tokens (2^20, 約 100萬)
    'gemini-2.5-flash-8b': 1_048_576,   # 1,048,576 tokens (2^20, 約 100萬)
    'gemini-2.0-flash-exp': 1_048_576,  # 1,048,576 tokens (2^20, 約 100萬)
    'gemini-1.5-pro': 2_097_152,        # 2,097,152 tokens (2^21, 約 200萬)
    'gemini-1.5-flash': 1_048_576,      # 1,048,576 tokens (2^20, 約 100萬)
}

# 預設上下文窗口（用於未列出的模型）
MAX_CONTEXT_TOKENS = 1_048_576  # 1,048,576 tokens (預設使用較保守的 100萬)

# 自動快取設定
AUTO_CACHE_ENABLED = True      # 是否啟用自動快取
AUTO_CACHE_THRESHOLD = 5000    # 自動建立快取的 tokens 門檻
AUTO_CACHE_MODE = "auto"       # "auto" 自動建立 / "prompt" 詢問確認
CACHE_TTL_HOURS = 1            # 快取有效期（小時）

# 翻譯設定
TRANSLATION_ON_STARTUP = True  # 啟動時是否預設啟用翻譯

# 計價設定
USD_TO_TWD = 31.0              # 美元轉新台幣匯率

# 思考模式設定
SHOW_THINKING_PROCESS = False  # 預設是否顯示思考過程（False = 隱藏，用 Ctrl+T 切換）
MAX_THINKING_BUDGET = 24576    # 最大思考預算（tokens）

# 對話記錄設定
SAVE_CONVERSATION_HISTORY = True     # 是否自動儲存對話記錄
CONVERSATION_SAVE_FORMAT = "both"    # "txt" 純文字 / "json" JSON / "both" 兩者都存

# ==========================================
# 記憶體管理設定（對話歷史防洩漏）
# ==========================================
MEMORY_MANAGEMENT_ENABLED = True         # 是否啟用記憶體管理（防止洩漏）
MAX_CONVERSATION_HISTORY = 100           # 最大活躍對話條數（100 條 = 約 50 輪對話）
MEMORY_WARNING_THRESHOLD_GB = 1.5        # 記憶體警告閾值（GB）
MEMORY_AUTO_CLEANUP = True               # 達到閾值時自動清理

# ⚠️⚠️⚠️ 危險選項：無限記憶體模式 ⚠️⚠️⚠️
UNLIMITED_MEMORY_MODE = False            # 🔴 我就是要用爆記憶體（預設：False）
#
# ⚠️ 警告：啟用此選項將完全停用記憶體管理機制！
#
# 適用場景：
#   ✓ 記憶體充足的環境（16GB+ RAM）
#   ✓ 需要保留完整對話歷史的極長會話
#   ✓ 測試或特殊用途
#
# 風險：
#   ✗ 可能導致記憶體溢出（OOM）
#   ✗ 可能導致系統變慢或程式崩潰
#   ✗ 長時間運行後記憶體可能超過 4GB+
#
# 建議：
#   • 僅在明確了解風險的情況下啟用
#   • 使用 /memory-stats 命令監控記憶體使用
#   • 定期手動執行 /clear-memory 清理（雖然會被警告）

# ==========================================
# 工具管理設定（自動化工具整合）
# ==========================================
# 自動化工具管理原則：
# - 完全自動化，用戶無需配置
# - 惰性載入，需要時才初始化
# - 靜默管理，不打擾用戶
# - 智能偵測，自動判斷需求

# 自動工具管理
AUTO_TOOL_ENABLED = True                    # 是否啟用自動工具管理（預設開啟）
AUTO_TOOL_UNLOAD_TIMEOUT = 300              # 閒置多久自動卸載（秒，預設 5 分鐘）
SHOW_TOOL_LOAD_MESSAGE = False              # 載入時是否顯示訊息（預設靜默）

# Web Search 工具配置
SEARCH_ENGINE = "duckduckgo"                # 搜尋引擎：duckduckgo / google_custom / brave
SEARCH_API_KEY = None                       # 搜尋 API Key（Google/Brave 需要，可留空使用 DuckDuckGo）
GOOGLE_CSE_ID = None                        # Google Custom Search Engine ID（可選）

# Web Fetch 工具配置
WEB_FETCH_TIMEOUT = 30                      # 網頁抓取超時（秒）
WEB_FETCH_CACHE_TTL = 900                   # 網頁快取生存時間（秒，預設 15 分鐘）
WEB_FETCH_MAX_RETRIES = 3                   # 最大重試次數

# Background Shell 工具配置
SHELL_MAX_OUTPUT_LINES = 1000               # Shell 輸出緩衝區最大行數
SHELL_DEFAULT_TIMEOUT = 3600                # Shell 預設超時（秒，預設 1 小時）

# Codebase Embedding 設定
EMBEDDING_AUTO_SAVE_CONVERSATIONS = False  # 是否自動將對話儲存到向量資料庫
EMBEDDING_VECTOR_DB_PATH = "embeddings"   # 向量資料庫路徑（相對於 Cache 目錄）
EMBEDDING_SESSION_ID_PREFIX = "chat_"     # Session ID 前綴
EMBEDDING_ENABLE_ON_STARTUP = False       # 啟動時是否自動啟用 Codebase Embedding

# ==========================================
# 統一輸出目錄配置（7 個標準目錄）
# ==========================================

from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent

# 7 個標準輸出目錄（不可由使用者配置，但模組化管理）
OUTPUT_DIRS = {
    'chat_logs': PROJECT_ROOT / 'ChatLogs',                    # 1. gemini_chat.py 對話日誌（文字）
    'code_gemini': PROJECT_ROOT / 'CodeGemini',                # 2. CodeGemini 主目錄
    'code_logs': PROJECT_ROOT / 'CodeGemini' / 'CodeLogs',     # 3. CodeGemini 日誌（文字）
    'diagnostics': PROJECT_ROOT / 'Diagnostics',               # 4. 錯誤診斷、恢復、批次任務
    'system_tool': PROJECT_ROOT / 'SystemTool',                # 5. 測試工具、debug 工具輸出
    'cache': PROJECT_ROOT / 'Cache',                           # 6. 所有快取檔案
    'media_outputs': PROJECT_ROOT / 'MediaOutputs',            # 7. 所有非文字模態的正式輸出
}

# MediaOutputs 子目錄
MEDIA_SUBDIRS = {
    'videos': OUTPUT_DIRS['media_outputs'] / 'Videos',         # 所有影片輸出
    'images': OUTPUT_DIRS['media_outputs'] / 'Images',         # 所有圖片輸出
    'audio': OUTPUT_DIRS['media_outputs'] / 'Audio',           # 所有音訊輸出
}

# 自動建立所有輸出目錄
for dir_path in OUTPUT_DIRS.values():
    dir_path.mkdir(parents=True, exist_ok=True)

# 自動建立 MediaOutputs 子目錄
for dir_path in MEDIA_SUBDIRS.values():
    dir_path.mkdir(parents=True, exist_ok=True)

# ==========================================
# 進階設定（通常不需修改）
# ==========================================

# 最低快取要求（tokens）
MIN_CACHE_TOKENS = {
    'gemini-2.5-pro': 4096,
    'gemini-2.5-flash': 1024,
    'gemini-2.5-flash-8b': 1024,
    'gemini-2.0-flash-exp': 1024,
}

# 思考模式支援的模型
THINKING_MODELS = [
    'gemini-2.5-pro',
    'gemini-2.5-flash',
    'gemini-2.5-flash-8b',
]

# 檔案類型定義（用於智慧檔案附加）
TEXT_EXTENSIONS = {
    '.txt', '.py', '.js', '.ts', '.jsx', '.tsx',
    '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs',
    '.php', '.rb', '.swift', '.kt', '.scala',
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.env',
    '.md', '.markdown', '.rst', '.csv', '.log',
    '.sh', '.bash', '.zsh', '.fish', '.ps1',
    '.sql', '.graphql', '.proto',
    '.html', '.css', '.scss', '.sass', '.less',
}

MEDIA_EXTENSIONS = {
    # 圖片
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico',
    # 影片
    '.mp4', '.mpeg', '.mov', '.avi', '.flv', '.wmv', '.webm', '.mkv', '.m4v',
    # 音訊
    '.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a', '.wma',
    # 文檔
    '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
}

# ==========================================
# 配置驗證函數
# ==========================================

def validate_config():
    """
    驗證配置是否合法
    返回：(是否合法, 錯誤訊息列表)
    """
    errors = []

    # 檢查必要模組
    for module_name, module_config in MODULES.items():
        if module_config.get('required', False) and not module_config.get('enabled', False):
            errors.append(f"必要模組 '{module_name}' 不能被停用")

    # 檢查 AUTO_CACHE_THRESHOLD
    if AUTO_CACHE_THRESHOLD < 1024:
        errors.append(f"AUTO_CACHE_THRESHOLD ({AUTO_CACHE_THRESHOLD}) 不能小於 1024")

    # 檢查 CACHE_TTL_HOURS
    if not (1 <= CACHE_TTL_HOURS <= 24):
        errors.append(f"CACHE_TTL_HOURS ({CACHE_TTL_HOURS}) 必須在 1-24 小時之間")

    # 檢查 AUTO_CACHE_MODE
    if AUTO_CACHE_MODE not in ['auto', 'prompt']:
        errors.append(f"AUTO_CACHE_MODE 必須是 'auto' 或 'prompt'")

    # 檢查 USD_TO_TWD
    if USD_TO_TWD <= 0:
        errors.append(f"USD_TO_TWD ({USD_TO_TWD}) 必須大於 0")

    return len(errors) == 0, errors


def get_enabled_modules():
    """
    取得所有已啟用的模組名稱列表
    """
    return [name for name, config in MODULES.items() if config.get('enabled', False)]


def is_module_enabled(module_name):
    """
    檢查指定模組是否已啟用
    """
    return MODULES.get(module_name, {}).get('enabled', False)


# ==========================================
# 三層配置系統（Tier 1: 系統預設）
# ==========================================

import os
from typing import Any, Optional

class UnifiedConfig:
    """
    統一配置類別 - 三層配置系統

    優先級（由低到高）：
    1. Tier 1: 系統預設（config.py 中的常數）
    2. Tier 2: 使用者配置（~/.cache/codegemini/config.json）
    3. Tier 3: 環境變數（執行期覆寫）

    使用範例：
        config = get_config()
        model = config.get('DEFAULT_MODEL')
        max_history = config.get('MAX_CONVERSATION_HISTORY')
    """

    _instance = None  # 單例模式

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UnifiedConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Tier 1: 系統預設值（從本檔案讀取）
        self._system_defaults = self._load_system_defaults()

        # Tier 2: 使用者配置（從 ConfigManager 載入）
        self._user_config = {}
        self._load_user_config()

        # Tier 3: 環境變數映射
        self._env_mapping = {
            # API 設定
            'GEMINI_API_KEY': 'GEMINI_API_KEY',

            # 模型設定
            'DEFAULT_MODEL': 'GEMINI_DEFAULT_MODEL',
            'TEMPERATURE': 'GEMINI_TEMPERATURE',
            'TOP_P': 'GEMINI_TOP_P',
            'TOP_K': 'GEMINI_TOP_K',
            'MAX_OUTPUT_TOKENS': 'GEMINI_MAX_TOKENS',

            # 記憶體管理
            'MAX_CONVERSATION_HISTORY': 'GEMINI_MAX_HISTORY',
            'UNLIMITED_MEMORY_MODE': 'GEMINI_UNLIMITED_MEMORY',
            'MEMORY_WARNING_THRESHOLD_GB': 'MEMORY_WARNING_GB',

            # 快取設定
            'AUTO_CACHE_ENABLED': 'GEMINI_AUTO_CACHE',
            'AUTO_CACHE_THRESHOLD': 'AUTO_CACHE_THRESHOLD',
            'CACHE_TTL_HOURS': 'CACHE_TTL_HOURS',

            # 其他設定
            'USD_TO_TWD': 'USD_TO_TWD',
            'TRANSLATION_ON_STARTUP': 'GEMINI_TRANSLATION',
            'SHOW_THINKING_PROCESS': 'SHOW_THINKING_PROCESS',
        }

        self._initialized = True

    def _load_system_defaults(self) -> dict:
        """載入系統預設值（Tier 1）"""
        return {
            # 模型設定
            'DEFAULT_MODEL': DEFAULT_MODEL,
            'AVAILABLE_MODELS': AVAILABLE_MODELS,
            'MODEL_CONTEXT_LIMITS': MODEL_CONTEXT_LIMITS,
            'MAX_CONTEXT_TOKENS': MAX_CONTEXT_TOKENS,

            # 快取設定
            'AUTO_CACHE_ENABLED': AUTO_CACHE_ENABLED,
            'AUTO_CACHE_THRESHOLD': AUTO_CACHE_THRESHOLD,
            'AUTO_CACHE_MODE': AUTO_CACHE_MODE,
            'CACHE_TTL_HOURS': CACHE_TTL_HOURS,

            # 翻譯設定
            'TRANSLATION_ON_STARTUP': TRANSLATION_ON_STARTUP,

            # 計價設定
            'USD_TO_TWD': USD_TO_TWD,

            # 思考模式設定
            'SHOW_THINKING_PROCESS': SHOW_THINKING_PROCESS,
            'MAX_THINKING_BUDGET': MAX_THINKING_BUDGET,

            # 對話記錄設定
            'SAVE_CONVERSATION_HISTORY': SAVE_CONVERSATION_HISTORY,
            'CONVERSATION_SAVE_FORMAT': CONVERSATION_SAVE_FORMAT,

            # 記憶體管理設定
            'MEMORY_MANAGEMENT_ENABLED': MEMORY_MANAGEMENT_ENABLED,
            'MAX_CONVERSATION_HISTORY': MAX_CONVERSATION_HISTORY,
            'MEMORY_WARNING_THRESHOLD_GB': MEMORY_WARNING_THRESHOLD_GB,
            'MEMORY_AUTO_CLEANUP': MEMORY_AUTO_CLEANUP,
            'UNLIMITED_MEMORY_MODE': UNLIMITED_MEMORY_MODE,

            # Embedding 設定
            'EMBEDDING_AUTO_SAVE_CONVERSATIONS': EMBEDDING_AUTO_SAVE_CONVERSATIONS,
            'EMBEDDING_VECTOR_DB_PATH': EMBEDDING_VECTOR_DB_PATH,
            'EMBEDDING_SESSION_ID_PREFIX': EMBEDDING_SESSION_ID_PREFIX,
            'EMBEDDING_ENABLE_ON_STARTUP': EMBEDDING_ENABLE_ON_STARTUP,

            # 輸出目錄
            'OUTPUT_DIRS': OUTPUT_DIRS,
            'MEDIA_SUBDIRS': MEDIA_SUBDIRS,

            # 模組配置
            'MODULES': MODULES,
        }

    def _load_user_config(self):
        """載入使用者配置（Tier 2）"""
        try:
            from CodeGemini.config_manager import ConfigManager, SystemConfig
            config_manager = ConfigManager()

            user_cfg = {}

            # 1. CodebaseEmbedding 相關
            emb_config = config_manager.config.codebase_embedding
            if emb_config.enabled:
                user_cfg['EMBEDDING_ENABLE_ON_STARTUP'] = True
                user_cfg['EMBEDDING_VECTOR_DB_PATH'] = emb_config.vector_db_path

            # 2. SystemConfig 覆寫（僅在使用者有明確設定時才覆寫）
            sys_config = config_manager.config.system
            defaults = SystemConfig()

            # 比較每個參數，只在與預設值不同時才覆寫
            if sys_config.default_model != defaults.default_model:
                user_cfg['DEFAULT_MODEL'] = sys_config.default_model

            if sys_config.max_conversation_history != defaults.max_conversation_history:
                user_cfg['MAX_CONVERSATION_HISTORY'] = sys_config.max_conversation_history

            if sys_config.unlimited_memory_mode != defaults.unlimited_memory_mode:
                user_cfg['UNLIMITED_MEMORY_MODE'] = sys_config.unlimited_memory_mode

            if sys_config.auto_cache_enabled != defaults.auto_cache_enabled:
                user_cfg['AUTO_CACHE_ENABLED'] = sys_config.auto_cache_enabled

            if sys_config.auto_cache_threshold != defaults.auto_cache_threshold:
                user_cfg['AUTO_CACHE_THRESHOLD'] = sys_config.auto_cache_threshold

            if sys_config.translation_on_startup != defaults.translation_on_startup:
                user_cfg['TRANSLATION_ON_STARTUP'] = sys_config.translation_on_startup

            if sys_config.usd_to_twd != defaults.usd_to_twd:
                user_cfg['USD_TO_TWD'] = sys_config.usd_to_twd

            if sys_config.memory_warning_threshold_gb != defaults.memory_warning_threshold_gb:
                user_cfg['MEMORY_WARNING_THRESHOLD_GB'] = sys_config.memory_warning_threshold_gb

            if sys_config.memory_auto_cleanup != defaults.memory_auto_cleanup:
                user_cfg['MEMORY_AUTO_CLEANUP'] = sys_config.memory_auto_cleanup

            self._user_config = user_cfg

        except Exception as e:
            # 如果載入失敗，使用空配置
            import logging
            logging.debug(f"無法載入使用者配置: {e}")
            self._user_config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置值（按優先級合併）

        Args:
            key: 配置鍵名
            default: 預設值（如果所有層都找不到）

        Returns:
            配置值
        """
        # Tier 3: 檢查環境變數（最高優先級）
        env_key = self._env_mapping.get(key)
        if env_key and env_key in os.environ:
            env_value = os.environ[env_key]
            # 類型轉換
            return self._convert_env_value(env_value, key)

        # Tier 2: 檢查使用者配置
        if key in self._user_config:
            return self._user_config[key]

        # Tier 1: 返回系統預設值
        return self._system_defaults.get(key, default)

    def _convert_env_value(self, value: str, key: str) -> Any:
        """將環境變數字串轉換為正確的類型"""
        # 布林值轉換
        bool_keys = [
            'UNLIMITED_MEMORY_MODE', 'AUTO_CACHE_ENABLED',
            'TRANSLATION_ON_STARTUP', 'SHOW_THINKING_PROCESS'
        ]
        if key in bool_keys:
            return value.lower() in ('true', '1', 'yes', 'on')

        # 整數轉換
        int_keys = [
            'MAX_CONVERSATION_HISTORY', 'AUTO_CACHE_THRESHOLD',
            'TOP_K', 'MAX_OUTPUT_TOKENS', 'CACHE_TTL_HOURS'
        ]
        if key in int_keys:
            try:
                return int(value)
            except ValueError:
                return self._system_defaults.get(key)

        # 浮點數轉換
        float_keys = [
            'USD_TO_TWD', 'MEMORY_WARNING_THRESHOLD_GB',
            'TEMPERATURE', 'TOP_P'
        ]
        if key in float_keys:
            try:
                return float(value)
            except ValueError:
                return self._system_defaults.get(key)

        # 預設返回字串
        return value

    def set_user_config(self, key: str, value: Any):
        """
        設定使用者配置（Tier 2）

        Args:
            key: 配置鍵名
            value: 配置值
        """
        self._user_config[key] = value

    def reload(self):
        """重新載入所有配置"""
        self._load_user_config()

    def get_config_summary(self) -> dict:
        """獲取配置摘要（用於除錯）"""
        return {
            'tier1_system': list(self._system_defaults.keys()),
            'tier2_user': self._user_config,
            'tier3_env': {k: os.environ.get(v) for k, v in self._env_mapping.items() if v in os.environ}
        }


# 全域配置實例（單例）
_global_config = None

def get_config() -> UnifiedConfig:
    """
    獲取統一配置實例（單例模式）

    使用範例：
        from config import get_config
        config = get_config()
        model = config.get('DEFAULT_MODEL')

    Returns:
        UnifiedConfig 實例
    """
    global _global_config
    if _global_config is None:
        _global_config = UnifiedConfig()
    return _global_config


# ==========================================
# 配置載入時自動驗證
# ==========================================

if __name__ == "__main__":
    # 當直接執行此檔案時，進行配置驗證
    is_valid, errors = validate_config()

    if is_valid:
        print("✅ 配置驗證通過")
        print(f"\n已啟用的模組（{len(get_enabled_modules())} 個）：")
        for module_name in get_enabled_modules():
            desc = MODULES[module_name]['description']
            print(f"  • {module_name}: {desc}")
    else:
        print("❌ 配置驗證失敗：")
        for error in errors:
            print(f"  • {error}")
        exit(1)

    # 測試三層配置系統
    print("\n" + "=" * 60)
    print("三層配置系統測試")
    print("=" * 60)

    config = get_config()

    print("\n📋 配置摘要：")
    summary = config.get_config_summary()
    print(f"  Tier 1 (系統預設): {len(summary['tier1_system'])} 個參數")
    print(f"  Tier 2 (使用者配置): {len(summary['tier2_user'])} 個覆寫")
    print(f"  Tier 3 (環境變數): {len(summary['tier3_env'])} 個覆寫")

    print("\n🔍 測試關鍵配置：")
    print(f"  DEFAULT_MODEL = {config.get('DEFAULT_MODEL')}")
    print(f"  MAX_CONVERSATION_HISTORY = {config.get('MAX_CONVERSATION_HISTORY')}")
    print(f"  UNLIMITED_MEMORY_MODE = {config.get('UNLIMITED_MEMORY_MODE')}")
    print(f"  USD_TO_TWD = {config.get('USD_TO_TWD')}")

    print("\n✅ 三層配置系統測試通過！")
