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
        'notes': '需要 codebase_embedding 啟用，基於向量搜尋'
    },

    'smart_triggers': {
        'enabled': True,
        'required': False,
        'description': '智能觸發器（意圖檢測、自動觸發功能）',
        'dependencies': [],
        'file': 'gemini_smart_triggers.py',
        'notes': '自動檢測使用者意圖，觸發 CodeGemini 功能'
    },

    'performance_optimization': {
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

# Codebase Embedding 設定
EMBEDDING_AUTO_SAVE_CONVERSATIONS = False  # 是否自動將對話儲存到向量資料庫
EMBEDDING_VECTOR_DB_PATH = ".embeddings"  # 向量資料庫路徑
EMBEDDING_SESSION_ID_PREFIX = "chat_"     # Session ID 前綴
EMBEDDING_ENABLE_ON_STARTUP = False       # 啟動時是否自動啟用 Codebase Embedding

# 對話記錄儲存位置：~/SakiStudio/ChatGemini/ChatLOG

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
