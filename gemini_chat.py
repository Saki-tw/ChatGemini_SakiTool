#!/usr/bin/env python3
"""
ChatGemini_SakiTool - Gemini 對話腳本 v2.3
完全使用新 SDK (google-genai)

v2.3 智能背景預載入（2025-10-29）：
- ⚡ 感知啟動時間：17.3s → 瞬間啟動（智能背景載入）
- 🎯 預判載入：在使用者互動時背景載入模組
- 🧠 時機分配：模型選擇（5s）→ 輸入時（10s）→ API等待（5s）
- 📊 優先級載入：HIGH → MEDIUM → LOW → IDLE
- 💾 總載入時間不變,但使用者無感知

v2.2 啟動速度優化：
- 🚀 啟動時間：18.5s → 17.3s（優化 6.5%）
- 📦 延遲載入：非核心模組按需載入
- 🎛️  使用者控制：環境變數控制功能開關
- 💾 記憶體優化：移除 lxml (9.6MB) 預載入
- ⚡ 條件載入：prompt_toolkit 預設停用

核心功能（立即載入）：
- ✅ 思考模式（動態控制）
- ✅ 新台幣計價（省錢導向）
- ✅ 對話記錄
- ✅ 快取自動管理（省錢導向）
- ✅ 檔案附加

背景預載入功能（使用者無感知）：
- 🎯 Tier 1 (模型選擇時): pricing, cache_manager
- 🎯 Tier 2 (輸入時): translator, media_viewer, smart_triggers
- 🎯 Tier 3 (API等待): video_analyzer, imagen_generator, audio_processor
"""
import sys
import os
import json
import logging
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt, Confirm
from utils.i18n import safe_t
from rich.markdown import Markdown
from rich.panel import Panel

# 載入 .env 環境變數（必須在讀取 ENABLE_ADVANCED_INPUT 之前）
load_dotenv()

# 色彩配置 - 雙主色系
COLOR_MACARON_PURPLE = "#B565D8"
COLOR_MACARON_PURPLE_LIGHT = "#E8C4F0"
COLOR_FORGET_ME_NOT = "#87CEEB"
COLOR_FORGET_ME_NOT_LIGHT = "#B0E0E6"

# ==========================================
# i18n 國際化（必須在最前面導入以觸發自動初始化）
# ==========================================
import utils  # 自動初始化 i18n 並注入 t() 到 builtins
from utils import safe_t  # 導入安全翻譯函數,支援降級運行

# ==========================================
# 動態模組載入器
# ==========================================
from gemini_module_loader import ModuleLoader
module_loader = ModuleLoader()

# ==========================================
# 智能背景預載入系統（v2.3 新增）
# ==========================================
# 收集啟動訊息,在指令說明之前統一顯示
STARTUP_MESSAGES = []

from smart_background_loader import (
    get_smart_loader,
    on_model_selection_start,
    on_first_input_start,
    on_api_call_start,
    get_module_lazy
)
# 立即啟動背景載入器
_background_loader = get_smart_loader()

# ==========================================
# 自動化工具管理器
# ==========================================
try:
    from gemini_tools import (
        auto_tool_manager,
        prepare_tools_for_input,
        cleanup_tools
    )
    TOOLS_MANAGER_AVAILABLE = True
except ImportError:
    TOOLS_MANAGER_AVAILABLE = False

# ==========================================
# 載入配置檔案（可選）
# ==========================================
# 統一配置管理（三層架構）
# ==========================================
try:
    from config_unified import unified_config as config
    CONFIG_AVAILABLE = True
    STARTUP_MESSAGES.append(safe_t('chat.system.config_loaded', fallback='✅ 已載入統一配置管理器（三層架構）'))
except ImportError:
    CONFIG_AVAILABLE = False
    # 如果配置不可用,使用預設配置
    class config:
        """預設配置（當統一配置不可用時使用）"""

        @staticmethod
        def get(key, default=None):
            return default
        MODULES = {
            'pricing': {'enabled': True},
            'cache_manager': {'enabled': True},
            'file_manager': {'enabled': True},
            'translator': {'enabled': True},
            'flow_engine': {'enabled': False},
            'video_preprocessor': {'enabled': False},
            'video_compositor': {'enabled': False},
        }
        USD_TO_TWD = 31.0
        DEFAULT_MODEL = 'gemini-2.5-flash'
        AUTO_CACHE_ENABLED = True
        AUTO_CACHE_THRESHOLD = 5000
        CACHE_TTL_HOURS = 1
        TRANSLATION_ON_STARTUP = True
        SHOW_THINKING_PROCESS = False

# 終端機輸入增強（根據專案思想 5.5: 使用者可控制）
# 預設停用以加速啟動,使用者可通過環境變數啟用
ENABLE_ADVANCED_INPUT = os.getenv('GEMINI_ADVANCED_INPUT', 'false').lower() == 'true'

if ENABLE_ADVANCED_INPUT:
    try:
        from prompt_toolkit import prompt, PromptSession
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.completion import WordCompleter, Completer, Completion, merge_completers
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.lexers import PygmentsLexer
        from prompt_toolkit.styles import Style
        from prompt_toolkit.filters import has_completions
        from slash_command_completer import SlashCommandCompleter, get_slash_command_style
        PROMPT_TOOLKIT_AVAILABLE = True
        STARTUP_MESSAGES.append(safe_t('chat.system.advanced_input_enabled', fallback='✅ 進階輸入已啟用（方向鍵、自動完成）'))
    except ImportError:
        PROMPT_TOOLKIT_AVAILABLE = False
        print(safe_t('chat.system.suggest_prompt_toolkit', fallback='⚠️  建議安裝 prompt-toolkit 以獲得更好的輸入體驗'))
else:
    PROMPT_TOOLKIT_AVAILABLE = False
    # print(safe_t('chat.system.advanced_input_disabled', fallback='ℹ️  進階輸入已停用（設定 GEMINI_ADVANCED_INPUT=true 啟用）'))

# 新 SDK
from google import genai
from google.genai import types

# 記憶體監控（必要依賴）
import psutil

# ==========================================
# 檢查點系統
# ==========================================
try:
    from gemini_checkpoint import get_checkpoint_manager, CheckpointManager, auto_checkpoint
    from gemini_checkpoint import FileChangeType, CheckpointType
    CHECKPOINT_ENABLED = True
    STARTUP_MESSAGES.append(safe_t('chat.system.checkpoint_enabled', fallback='✅ 檢查點系統已啟用'))
except ImportError:
    CHECKPOINT_ENABLED = False
    print(safe_t('chat.system.checkpoint_not_found', fallback='⚠️  檢查點系統未找到（gemini_checkpoint.py）'))

# ==========================================
# 互動式語言切換
# ==========================================
try:
    from interactive_language_menu import show_language_menu
    INTERACTIVE_LANG_MENU_AVAILABLE = True
    STARTUP_MESSAGES.append(safe_t('chat.system.lang_menu_enabled', fallback='✅ 互動式語言選單已啟用'))
except ImportError:
    INTERACTIVE_LANG_MENU_AVAILABLE = False
    print(safe_t('chat.system.lang_menu_unavailable', fallback='ℹ️  互動式語言選單不可用（可使用 gemini_lang.py）'))

# ==========================================
# 對話歷史管理
# ==========================================
try:
    from conversation_history_manager import ConversationHistoryManager, get_history_manager
    HISTORY_MANAGER_AVAILABLE = True
    history_manager = get_history_manager()
    STARTUP_MESSAGES.append(safe_t('chat.system.history_manager_enabled', fallback='✅ 對話歷史管理已啟用'))
except ImportError:
    HISTORY_MANAGER_AVAILABLE = False
    history_manager = None
    print(safe_t('chat.system.history_manager_unavailable', fallback='ℹ️  對話歷史管理不可用（conversation_history_manager.py）'))

# ==========================================
# 根據 config.py 動態導入模組
# ==========================================

# 導入計價系統
if config.MODULES.get('pricing', {}).get('enabled', True):
    try:
        from gemini_pricing import PricingCalculator, USD_TO_TWD as PRICING_USD_TO_TWD
        from gemini_streaming_display import StreamingTokenDisplay
        PRICING_ENABLED = True
        STREAMING_DISPLAY_AVAILABLE = True
    except ImportError:
        PRICING_ENABLED = False
        STREAMING_DISPLAY_AVAILABLE = False
        PRICING_USD_TO_TWD = config.USD_TO_TWD
        print(safe_t('chat.system.pricing_not_found', fallback='提示：gemini_pricing.py 不存在,計價功能已停用'))
else:
    PRICING_ENABLED = False
    PRICING_USD_TO_TWD = config.USD_TO_TWD
    print(safe_t('chat.system.pricing_disabled', fallback='ℹ️  計價功能已在 config.py 中停用'))

# 使用配置檔案中的匯率或模組中的匯率
USD_TO_TWD = PRICING_USD_TO_TWD if PRICING_ENABLED else config.USD_TO_TWD

# 導入快取管理器
if config.MODULES.get('cache_manager', {}).get('enabled', True):
    try:
        from gemini_cache_manager import CacheManager
        CACHE_ENABLED = True
    except ImportError:
        CACHE_ENABLED = False
        print(safe_t('chat.system.cache_not_found', fallback='提示：gemini_cache_manager.py 不存在,快取功能已停用'))
else:
    CACHE_ENABLED = False
    print(safe_t('chat.system.cache_disabled', fallback='ℹ️  快取功能已在 config.py 中停用'))

# 導入檔案管理器
if config.MODULES.get('file_manager', {}).get('enabled', True):
    try:
        # gemini_file_manager 已重構為提供函數式介面,而非 FileManager 類別
        from gemini_file_manager import process_file_attachments, get_file_cache, get_smart_preloader
        FILE_MANAGER_ENABLED = True
    except ImportError as e:
        FILE_MANAGER_ENABLED = False
        print(safe_t('chat.system.file_manager_not_found', fallback=f'提示：gemini_file_manager.py 載入失敗 ({e}),檔案處理功能已停用'))
else:
    FILE_MANAGER_ENABLED = False
    print(safe_t('chat.system.file_manager_disabled', fallback='ℹ️  檔案管理功能已在 config.py 中停用'))

# 導入翻譯器
# 根據專案思想 5.2: 翻譯器延遲載入（deep_translator 載入 lxml 9.6MB）
TRANSLATOR_ENABLED = config.MODULES.get('translator', {}).get('enabled', True)
global_translator = None  # 延遲載入

def get_global_translator():
    """延遲載入翻譯器（避免載入 9.6MB 的 lxml）"""
    global global_translator
    if global_translator is None and TRANSLATOR_ENABLED:
        try:
            from gemini_translator import get_translator
            global_translator = get_translator()
        except ImportError:
            print(safe_t('chat.system.translator_not_found', fallback='提示：gemini_translator.py 不存在,翻譯功能已停用'))
    return global_translator

# 導入影音相關模組 - Flow Engine
if config.MODULES.get('flow_engine', {}).get('enabled', False):
    try:
        from gemini_flow_engine import FlowEngine
        FLOW_ENGINE_ENABLED = True
    except ImportError:
        FLOW_ENGINE_ENABLED = False
        print(safe_t('chat.system.flow_engine_not_found', fallback='提示：gemini_flow_engine.py 不存在,Flow 引擎功能已停用'))
else:
    FLOW_ENGINE_ENABLED = False

# 導入影音相關模組 - Video Preprocessor
if config.MODULES.get('video_preprocessor', {}).get('enabled', False):
    try:
        from gemini_video_preprocessor import VideoPreprocessor
        VIDEO_PREPROCESSOR_ENABLED = True
    except ImportError:
        VIDEO_PREPROCESSOR_ENABLED = False
else:
    VIDEO_PREPROCESSOR_ENABLED = False

# 導入影音相關模組 - Video Compositor
if config.MODULES.get('video_compositor', {}).get('enabled', False):
    try:
        from gemini_video_compositor import VideoCompositor
        VIDEO_COMPOSITOR_ENABLED = True
    except ImportError:
        VIDEO_COMPOSITOR_ENABLED = False
else:
    VIDEO_COMPOSITOR_ENABLED = False

# 導入音訊處理模組 - Audio Processor
if config.MODULES.get('audio_processor', {}).get('enabled', False):
    try:
        from gemini_audio_processor import AudioProcessor
        AUDIO_PROCESSOR_ENABLED = True
    except ImportError:
        AUDIO_PROCESSOR_ENABLED = False
else:
    AUDIO_PROCESSOR_ENABLED = False

# 導入字幕生成模組 - Subtitle Generator
if config.MODULES.get('subtitle_generator', {}).get('enabled', False):
    try:
        from gemini_subtitle_generator import SubtitleGenerator
        SUBTITLE_GENERATOR_ENABLED = True
    except ImportError:
        SUBTITLE_GENERATOR_ENABLED = False
else:
    SUBTITLE_GENERATOR_ENABLED = False

# 導入圖片生成模組 - Imagen Generator
if config.MODULES.get('imagen_generator', {}).get('enabled', False):
    try:
        from gemini_imagen_generator import generate_image, edit_image, upscale_image
        IMAGEN_GENERATOR_ENABLED = True
    except ImportError:
        IMAGEN_GENERATOR_ENABLED = False
else:
    IMAGEN_GENERATOR_ENABLED = False

# 導入媒體查看器 - Media Viewer（延遲載入）
# 根據專案思想 5.2: 非必要功能延遲載入
MEDIA_VIEWER_ENABLED = True  # 標記可用,實際使用時才載入
_media_viewer = None  # 延遲載入的實例

def get_media_viewer():
    global _media_viewer
    if _media_viewer is None:
        from gemini_media_viewer import MediaViewer
        _media_viewer = MediaViewer()
    return _media_viewer

# 導入影片特效處理器 - Video Effects
if config.MODULES.get('video_effects', {}).get('enabled', False):
    try:
        from gemini_video_effects import VideoEffects
        VIDEO_EFFECTS_ENABLED = True
    except ImportError:
        VIDEO_EFFECTS_ENABLED = False
else:
    VIDEO_EFFECTS_ENABLED = False

# 導入影片分析器 - Video Analyzer
if config.MODULES.get('video_analyzer', {}).get('enabled', False):
    try:
        from gemini_video_analyzer import VideoAnalyzer
        VIDEO_ANALYZER_ENABLED = True
    except ImportError:
        VIDEO_ANALYZER_ENABLED = False
        print(safe_t('chat.system.video_analyzer_not_found', fallback='提示：gemini_video_analyzer.py 不存在,影片分析功能已停用'))
else:
    VIDEO_ANALYZER_ENABLED = False

# 檢查 CodeGemini 配置管理器是否可用
try:
    from pathlib import Path
    codegemini_path = Path(__file__).parent / "CodeGemini"
    config_manager_file = codegemini_path / "config_manager.py"
    CODEGEMINI_ENABLED = config_manager_file.exists()
except Exception:
    CODEGEMINI_ENABLED = False

# ==========================================
# CodeGemini 配置管理系統（獨立於 config.py）- 延遲載入以加速啟動
# ==========================================
codegemini_config_manager = None
codegemini_config = None
_codegemini_loading = False  # 標記是否正在背景載入
_codegemini_loaded = False   # 標記是否已完成載入


def get_codegemini_config_manager():
    """
    延遲載入 CodeGemini 配置管理器

    Returns:
        ConfigManager 實例,如果載入失敗則返回 None
    """
    global codegemini_config_manager, codegemini_config, _codegemini_loaded

    if _codegemini_loaded:
        return codegemini_config_manager

    if not CODEGEMINI_ENABLED:
        _codegemini_loaded = True
        return None

    try:
        import sys
        from pathlib import Path
        config_path = Path(__file__).parent / "CodeGemini"
        if str(config_path) not in sys.path:
            sys.path.insert(0, str(config_path))

        from config_manager import ConfigManager
        codegemini_config_manager = ConfigManager()
        codegemini_config = codegemini_config_manager.get_codebase_embedding_config()
        _codegemini_loaded = True
        logger.info("✓ CodeGemini 配置管理器已載入")
        return codegemini_config_manager
    except ImportError as e:
        logger.warning(f"CodeGemini 配置管理器載入失敗: {e}")
        _codegemini_loaded = True
        return None

def start_background_codegemini_loading():
    """在背景執行緒中載入 CodeGemini 配置管理器"""
    global _codegemini_loading

    if _codegemini_loading or _codegemini_loaded or not CODEGEMINI_ENABLED:
        return

    _codegemini_loading = True

    import threading

    def _load_in_background():
        try:
            get_codegemini_config_manager()
        except Exception as e:
            logger.warning(f"背景載入 CodeGemini 失敗: {e}")
        finally:
            global _codegemini_loading
            _codegemini_loading = False

    thread = threading.Thread(target=_load_in_background, daemon=True)
    thread.start()

def is_codegemini_ready() -> bool:
    """檢查 CodeGemini 配置管理器是否已就緒"""
    return _codegemini_loaded and codegemini_config_manager is not None

# 導入 Codebase Embedding（支援多重配置載入）- 延遲載入
# 優先使用 CodeGemini 配置,回退到 config.py
global_codebase_embedding = None
codebase_embedding_enabled = False  # 啟動時預設為 False,實際狀態會在載入 ConfigManager 後確定

# 注意：codebase_embedding 的實際初始化會在首次使用時進行
# 這裡只是宣告變數,不執行初始化邏輯
CODEBASE_EMBEDDING_ENABLED = False  # 預設為 False,會在 CodeGemini 載入後更新

def get_codebase_embedding():
    """
    延遲載入 Codebase Embedding

    Returns:
        CodebaseEmbedding 實例,如果載入失敗則返回 None
    """
    global global_codebase_embedding, CODEBASE_EMBEDDING_ENABLED

    if global_codebase_embedding is not None:
        return global_codebase_embedding

    # 先確保 ConfigManager 已載入
    config_manager = get_codegemini_config_manager()
    if config_manager is None:
        return None

    # 檢查是否啟用
    if codegemini_config is None or not codegemini_config.enabled:
        if not config.MODULES.get('codebase_embedding', {}).get('enabled', False):
            return None

    if not CODEGEMINI_ENABLED:
        logger.warning("Codebase Embedding 需要 CodeGemini 模組")
        return None

    try:
        # 初始化 CodebaseEmbedding
        codegemini_instance = CodeGemini()
        API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

        # 使用配置來源的參數
        if codegemini_config is not None and codegemini_config.enabled:
            # 使用 CodeGemini 配置管理器的設定
            global_codebase_embedding = codegemini_instance.enable_codebase_embedding(
                vector_db_path=os.path.expanduser(codegemini_config.vector_db_path),
                api_key=API_KEY,
                orthogonal_mode=codegemini_config.orthogonal_mode,
                similarity_threshold=codegemini_config.similarity_threshold
            )
        else:
            # 使用 config.py 的預設值
            global_codebase_embedding = codegemini_instance.enable_codebase_embedding(
                vector_db_path=os.path.expanduser("~/.gemini/embeddings"),
                api_key=API_KEY,
                orthogonal_mode=True,
                similarity_threshold=0.85
            )

        CODEBASE_EMBEDDING_ENABLED = True
        logger.info("✓ Codebase Embedding 已啟用")
        return global_codebase_embedding
    except Exception as e:
        logger.warning(f"Codebase Embedding 初始化失敗: {e}")
        CODEBASE_EMBEDDING_ENABLED = False
        return None

# 導入錯誤修復建議系統
try:
    from error_fix_suggestions import (
        # 檔案相關
        suggest_file_not_found,
        suggest_video_file_not_found,
        suggest_empty_file,
        suggest_file_corrupted,
        suggest_watermark_not_found,
        suggest_no_images_loaded,

        # ffmpeg 相關
        suggest_ffmpeg_install,
        suggest_ffmpeg_not_installed,
        suggest_ffprobe_failed,
        suggest_ffprobe_parse_failed,

        # API 相關
        suggest_api_key_setup,
        suggest_missing_module,

        # 媒體處理相關
        suggest_cannot_get_duration,
        suggest_missing_stream,
        suggest_no_video_stream,

        # JSON 相關
        suggest_json_parse_failed,

        # 影片處理相關
        suggest_invalid_time_range,
        suggest_invalid_speed,
        suggest_unsupported_filter,
        suggest_invalid_watermark_params,
        suggest_video_transcode_failed,
        suggest_video_upload_failed,
        suggest_video_processing_failed,

        # 字幕相關
        suggest_unsupported_subtitle_format,

        # 圖片相關
        suggest_image_load_failed,

        # 錯誤記錄
        ErrorLogger
    )
    ERROR_FIX_ENABLED = True

    # 初始化全域錯誤記錄器
    global_error_logger = ErrorLogger()
    STARTUP_MESSAGES.append(safe_t('chat.system.error_fix_enabled', fallback='✅ 錯誤修復建議系統已啟用'))
except ImportError as e:
    ERROR_FIX_ENABLED = False
    global_error_logger = None
    # 靜默失敗 - 錯誤修復建議為可選功能

# ========== 進階功能自動整合 ==========

# 導入 API 自動重試機制
if config.MODULES.get('api_retry', {}).get('enabled', True):
    try:
        from utils.api_retry import with_retry, APIRetryConfig
        API_RETRY_ENABLED = True
        STARTUP_MESSAGES.append(safe_t('chat.system.api_retry_enabled', fallback='✅ API 自動重試機制已啟用'))
    except ImportError:
        API_RETRY_ENABLED = False
else:
    API_RETRY_ENABLED = False

# 導入智能錯誤診斷系統
if config.MODULES.get('error_diagnostics', {}).get('enabled', True):
    try:
        from error_diagnostics import ErrorDiagnostics
        ERROR_DIAGNOSTICS_ENABLED = True
        global_error_diagnostics = ErrorDiagnostics()
        STARTUP_MESSAGES.append(safe_t('chat.system.error_diagnostics_enabled', fallback='✅ 智能錯誤診斷系統已啟用'))
    except ImportError:
        ERROR_DIAGNOSTICS_ENABLED = False
        global_error_diagnostics = None
else:
    ERROR_DIAGNOSTICS_ENABLED = False
    global_error_diagnostics = None

# 導入智能觸發器（自動增強提示）
if config.MODULES.get('smart_triggers', {}).get('enabled', True):
    try:
        from gemini_smart_triggers import (
            auto_enhance_prompt,
            detect_task_planning_intent,
            detect_code_analysis_intent,
            enhance_prompt_with_context,
            BackgroundTodoTracker
        )
        SMART_TRIGGERS_ENABLED = True
        STARTUP_MESSAGES.append(safe_t('chat.system.smart_triggers_enabled', fallback='✅ 智能觸發器已啟用（自動檢測意圖）'))
    except ImportError:
        SMART_TRIGGERS_ENABLED = False
else:
    SMART_TRIGGERS_ENABLED = False

# 導入媒體查看器（附加檔案時自動顯示資訊）
if config.MODULES.get('media_viewer', {}).get('enabled', True):
    try:
        from gemini_media_viewer import MediaViewer
        MEDIA_VIEWER_AUTO_ENABLED = True
        global_media_viewer = MediaViewer()
        STARTUP_MESSAGES.append(safe_t('chat.system.media_viewer_enabled', fallback='✅ 媒體查看器已啟用（附加檔案時自動顯示資訊）'))
    except ImportError:
        MEDIA_VIEWER_AUTO_ENABLED = False
        global_media_viewer = None
else:
    MEDIA_VIEWER_AUTO_ENABLED = False
    global_media_viewer = None

# 配置日誌（使用 Rich Handler 美化輸出）
try:
    from rich.logging import RichHandler

    # 提前初始化 console 以供 RichHandler 使用
    console = Console()

    # 配置全局 logging 使用 Rich（影響所有 logger）
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        datefmt='[%X]',
        handlers=[RichHandler(
            console=console,
            show_time=False,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
            enable_link_path=False,
        )],
        force=True  # 強制覆蓋已存在的配置
    )

    # 降低第三方模組的日誌級別以減少噪音
    logging.getLogger('google_genai').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
except ImportError:
    # 降級到標準 logging
    console = Console()  # 即使沒有 RichHandler 也需要初始化 console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

# 從環境變數獲取 API 金鑰（.env 已在檔案開頭載入）
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    logger.error("未找到 GEMINI_API_KEY 環境變數")
    # 使用錯誤修復建議系統
    if ERROR_FIX_ENABLED:
        suggest_api_key_setup()
    else:
        print(safe_t('chat.error.api_key_missing', fallback='錯誤：請設置 GEMINI_API_KEY 環境變數'))
        print(safe_t('chat.error.api_key_hint', fallback='請在 .env 文件中添加：GEMINI_API_KEY=你的API金鑰'))
    sys.exit(1)

# 配置新 SDK客戶端
client = genai.Client(api_key=API_KEY)

# 常數定義
# 對話記錄統一儲存路徑
# 使用統一輸出目錄配置
from utils.path_manager import get_chat_log_dir
DEFAULT_LOG_DIR = str(get_chat_log_dir())

DEFAULT_MODEL = 'gemini-2.5-flash'
MAX_CONTEXT_TOKENS = 2000000

# 初始化（console 已在 Rich logging 配置時初始化）
if PRICING_ENABLED:
    global_pricing_calculator = PricingCalculator()
if CACHE_ENABLED:
    global_cache_manager = CacheManager()
if FILE_MANAGER_ENABLED:
    # gemini_file_manager 現在提供函數式介面,不需要實例化
    global_file_manager = None  # 保留變數以維持相容性

# 思考簽名管理器（用於多輪對話脈絡維護）
global_thinking_signature_manager = None  # 將在需要時初始化

# 思考過程顯示配置（全域）
# 從配置載入（如果可用）,否則使用預設值
if codegemini_config_manager:
    SHOW_THINKING_PROCESS = codegemini_config_manager.config.system.show_thinking_process
else:
    SHOW_THINKING_PROCESS = False  # 預設隱藏,但會抓取,按 Ctrl+T 可切換顯示
LAST_THINKING_PROCESS = None   # 儲存最近一次的思考過程（英文原文）
LAST_THINKING_TRANSLATED = None  # 儲存最近一次的翻譯（繁體中文）
CTRL_T_PRESS_COUNT = 0  # Ctrl+T 按壓次數（0=未顯示, 1=顯示翻譯, 2=顯示雙語）

# 推薦的模型列表
RECOMMENDED_MODELS: Dict[str, tuple] = {
    '1': ('gemini-2.5-pro', safe_t('chat.model_gemini_25_pro', fallback='Gemini 2.5 Pro - 最強大（思考模式）')),
    '2': ('gemini-2.5-flash', safe_t('chat.model_gemini_25_flash', fallback='Gemini 2.5 Flash - 快速且智慧（推薦）')),
    '3': ('gemini-2.5-flash-lite', safe_t('chat.model_gemini_25_flash_lite', fallback='Gemini 2.5 Flash Lite - 輕量版（最便宜）')),
    '4': ('gemini-2.0-flash-exp', safe_t('chat.model_gemini_20_flash', fallback='Gemini 2.0 Flash - 快速版')),
}

# 支援思考模式的模型
THINKING_MODELS = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-lite']


# ==========================================
# 互動式配置 UI 類別（v2.1 新增）
# ==========================================

# 各模型的最低快取門檻要求（tokens）
# 根據 Gemini API Context Caching 規範
MIN_TOKENS = {
    'gemini-2.5-pro': 4096,           # Pro 版本需要更多
    'gemini-2.5-flash': 1024,         # Flash 版本標準
    'gemini-2.5-flash-lite': 1024,      # Flash-8B 版本標準
    'gemini-2.0-flash-exp': 32768,    # 2.0 實驗版需要較多
    'gemini-2.0-flash': 32768,        # 2.0 標準版
}

# 初始化 prompt_toolkit 歷史記錄
if PROMPT_TOOLKIT_AVAILABLE:
    input_history = InMemoryHistory()

    # 增強的自動補全器
    class SmartCompleter(Completer):
        """智能自動補全器：支援指令、語法、檔案路徑"""
        def __init__(self):
            self.commands = ['cache', 'media', 'video', 'veo', 'model', 'clear', 'exit', 'help', 'debug', 'test', 'lang', 'language']
            if CODEGEMINI_ENABLED:
                self.commands.extend(['cli', 'gemini-cli'])
            if CODEBASE_EMBEDDING_ENABLED:
                self.commands.extend(['/search_code', '/search_history'])

            # 思考模式與輸出控制語法提示
            # 基於官方文檔限制 (2025-10-29):
            # - Thinking: Pro 512-32768, Flash/Lite 0/512-24576
            # - Output: 2.5系列 1-65536, 2.0系列 1-8192
            #
            # 結構化資料格式,方便生成動態元資訊
            # priority: 1=組合語法(優先), 2=思考模式, 3=輸出限制
            self.pattern_info = {
                # ========================================
                # 🔥 組合語法（優先顯示,priority=1）
                # ========================================
                '[think:auto,response:1000]': {
                    'type': 'combo',
                    'desc': '自動思考+限制輸出',
                    'priority': 1,
                    'example': '自動決定思考深度,輸出限制1000 tokens'
                },
                '[think:4096,response:2048]': {
                    'type': 'combo',
                    'desc': '中等思考+中等輸出',
                    'priority': 1,
                    'example': '思考4096 tokens,輸出2048 tokens'
                },
                '[think:8192,response:4096]': {
                    'type': 'combo',
                    'desc': '深度思考+長輸出',
                    'priority': 1,
                    'example': '思考8192 tokens,輸出4096 tokens'
                },

                # ========================================
                # 思考模式（priority=2）
                # ========================================
                '[think:auto]': {'type': 'think', 'range': 'auto', 'desc': '動態決定', 'priority': 2},
                '[think:512]': {'type': 'think', 'value': 512, 'range': '512-32K', 'desc': '最小值', 'priority': 2},
                '[think:2048]': {'type': 'think', 'value': 2048, 'range': '512-32K', 'desc': '輕量', 'priority': 2},
                '[think:4096]': {'type': 'think', 'value': 4096, 'range': '512-32K', 'desc': '中等', 'priority': 2},
                '[think:8192]': {'type': 'think', 'value': 8192, 'range': '512-32K', 'desc': '深度', 'priority': 2},
                '[think:16384]': {'type': 'think', 'value': 16384, 'range': '512-32K', 'desc': '複雜', 'priority': 2},
                '[think:24576]': {'type': 'think', 'value': 24576, 'range': '512-32K', 'desc': 'Flash上限', 'priority': 2},
                '[think:32768]': {'type': 'think', 'value': 32768, 'range': '512-32K', 'desc': 'Pro上限', 'priority': 2},
                '[no-think]': {'type': 'control', 'desc': '關閉思考', 'priority': 2},

                # ========================================
                # 輸出限制（priority=3）
                # ========================================
                '[max_token:100]': {'type': 'output', 'value': 100, 'range': '1-65K', 'desc': '極短', 'priority': 3},
                '[max_token:500]': {'type': 'output', 'value': 500, 'range': '1-65K', 'desc': '簡短', 'priority': 3},
                '[max_token:1024]': {'type': 'output', 'value': 1024, 'range': '1-65K', 'desc': '一般', 'priority': 3},
                '[max_token:2048]': {'type': 'output', 'value': 2048, 'range': '1-65K', 'desc': '中等', 'priority': 3},
                '[max_token:4096]': {'type': 'output', 'value': 4096, 'range': '1-65K', 'desc': '長', 'priority': 3},
                '[max_token:8192]': {'type': 'output', 'value': 8192, 'range': '1-65K', 'desc': '2.0上限', 'priority': 3},
                '[max_token:16384]': {'type': 'output', 'value': 16384, 'range': '1-65K', 'desc': '超長', 'priority': 3},
                '[max_token:32768]': {'type': 'output', 'value': 32768, 'range': '1-65K', 'desc': '極限', 'priority': 3},
                '[max_token:65536]': {'type': 'output', 'value': 65536, 'range': '1-65K', 'desc': '2.5上限', 'priority': 3},
            }

            # 向後兼容：提供 think_patterns 列表
            self.think_patterns = list(self.pattern_info.keys())

        def _get_terminal_width(self):
            """取得終端機寬度"""
            try:
                import shutil
                cols, _ = shutil.get_terminal_size()
                return cols
            except Exception:
                return 80  # 預設值

        def _estimate_cost(self, pattern_type, value):
            """
            預估費用（簡化版）

            Args:
                pattern_type: 'think' | 'output'
                value: token 數量

            Returns:
                (min_usd, max_usd) 或 None
            """
            if pattern_type not in ['think', 'output'] or value is None:
                return None

            # 方案 1: 嘗試使用完整計價模組
            try:
                from utils import get_pricing_calculator, PRICING_ENABLED

                if PRICING_ENABLED:
                    pricing_calc = get_pricing_calculator(silent=True)
                    if pricing_calc:
                        # 假設使用 2.5-flash（最常用）
                        pricing = pricing_calc.get_model_pricing('gemini-2.5-flash-latest')
                        if pricing:
                            # Think 使用 input 價格,Output 使用 output 價格
                            if pattern_type == 'think':
                                price_per_1k = pricing.get('input', pricing.get('input_low', 0))
                            else:  # output
                                price_per_1k = pricing.get('output', pricing.get('output_low', 0))

                            # 假設實際使用 50%-100%
                            min_cost = (value * 0.5 / 1000) * price_per_1k
                            max_cost = (value / 1000) * price_per_1k
                            return (min_cost, max_cost)
            except Exception:
                pass  # 失敗時使用備用方案

            # 方案 2: 備用硬編碼價格（基於 2025-10-29 官方價格）
            # Gemini 2.5 Flash 價格 (USD per 1M tokens):
            # - Input (≤128K context): $0.075 / 1M = $0.000075 / 1K
            # - Input (>128K context): $0.15 / 1M = $0.00015 / 1K
            # - Output (≤128K context): $0.30 / 1M = $0.0003 / 1K
            # - Output (>128K context): $0.60 / 1M = $0.0006 / 1K
            #
            # 保守估計使用低價格範圍（≤128K context）
            try:
                if pattern_type == 'think':
                    # Thinking tokens 算作 input
                    price_per_1k = 0.000075  # $0.075 per 1M tokens
                else:  # output
                    # Output tokens 使用 output 價格
                    price_per_1k = 0.0003  # $0.30 per 1M tokens

                # 假設實際使用 50%-100%
                min_cost = (value * 0.5 / 1000) * price_per_1k
                max_cost = (value / 1000) * price_per_1k
                return (min_cost, max_cost)
            except Exception:
                return None

        def _format_meta(self, pattern, term_width):
            """
            生成自適應的 display_meta

            根據終端機寬度自動選擇最合適的格式：
            - 寬螢幕 (>120): 完整資訊（範圍 + 描述 + 費用 + TWD）
            - 標準螢幕 (80-120): 中等資訊（範圍 + 描述 + 費用 USD）
            - 窄螢幕 (<80): 簡化資訊（範圍 + 描述）

            Args:
                pattern: 語法模式（如 '[think:2048]'）
                term_width: 終端機寬度

            Returns:
                格式化的 display_meta 字串
            """
            info = self.pattern_info.get(pattern, {})
            pattern_type = info.get('type', 'unknown')
            desc = info.get('desc', '')
            range_str = info.get('range', '')
            value = info.get('value')
            priority = info.get('priority', 99)

            # 計算可用空間
            # pattern 本身佔用 ~20 字元,分隔符和緩衝 ~10 字元
            available = term_width - len(pattern) - 10

            # 基礎資訊
            parts = []

            # 0. 優先級標記（僅組合語法）
            if pattern_type == 'combo' and available > 20:
                parts.append('🔥 組合')

            # 1. 範圍資訊
            if range_str:
                parts.append(range_str)

            # 2. 描述
            if desc:
                parts.append(desc)

            # 3. 費用預估（根據螢幕寬度決定是否顯示）
            if value and available > 35:  # 至少需要 35 字元才顯示費用
                cost_info = self._estimate_cost(pattern_type, value)
                if cost_info:
                    min_usd, max_usd = cost_info

                    # 寬螢幕：顯示 USD + TWD
                    if available > 60 and term_width > 120:
                        try:
                            from utils import USD_TO_TWD
                            min_twd = min_usd * USD_TO_TWD
                            max_twd = max_usd * USD_TO_TWD
                            cost_str = f"${min_usd:.3f}-{max_usd:.3f} (₹{min_twd:.1f}-{max_twd:.1f})"
                        except Exception:
                            cost_str = f"${min_usd:.3f}-{max_usd:.3f}"
                        parts.append(cost_str)

                    # 標準螢幕：只顯示 USD
                    elif available > 45:
                        cost_str = f"${min_usd:.3f}-{max_usd:.3f}"
                        parts.append(cost_str)

                    # 窄螢幕：簡化顯示
                    elif available > 35:
                        cost_str = f"~${max_usd:.3f}"
                        parts.append(cost_str)

            # 組合結果,使用 | 分隔
            result = ' | '.join(parts)

            # 最終檢查：如果還是太長,裁剪並加上省略號
            if len(result) > available:
                result = result[:available-3] + '...'

            return result

        def get_completions(self, document, complete_event):
            word = document.get_word_before_cursor()
            text = document.text_before_cursor

            # === 新增：檢測到 '[' 時自動顯示所有選項 ===
            if text.endswith('['):
                # 使用者剛輸入 '[',顯示所有參數選項
                term_width = self._get_terminal_width()

                # 按優先級排序（組合語法優先）
                sorted_patterns = sorted(
                    self.pattern_info.items(),
                    key=lambda x: x[1].get('priority', 99)
                )

                for pattern, info in sorted_patterns:
                    meta = self._format_meta(pattern, term_width)

                    yield Completion(
                        pattern,
                        start_position=0,  # 從 '[' 之後開始
                        display_meta=meta
                    )
                return  # 不再處理其他補全

            # === 原有邏輯：部分匹配 ===
            # 1. 思考模式與輸出控制語法補全
            # 注意: get_word_before_cursor() 不包含 '[' 符號
            # 例如輸入 "[max" 時,word = "max",需要匹配 "[max_token:...]"
            if '[' in text:
                # 取得終端機寬度（只取一次）
                term_width = self._get_terminal_width()

                # 按優先級排序
                sorted_patterns = sorted(
                    [(p, self.pattern_info.get(p, {})) for p in self.think_patterns],
                    key=lambda x: x[1].get('priority', 99)
                )

                for pattern, info in sorted_patterns:
                    # 移除 pattern 開頭的 '[' 來匹配 word
                    pattern_word = pattern[1:] if pattern.startswith('[') else pattern
                    if pattern_word.lower().startswith(word.lower()):
                        # 生成自適應的 display_meta
                        meta = self._format_meta(pattern, term_width)

                        yield Completion(
                            pattern,
                            start_position=-len(word),
                            display_meta=meta
                        )

            # 2. 指令補全（排除斜線指令,那些由 SlashCommandCompleter 處理）
            elif not text.startswith('/') and (not text or text.isspace() or (len(text) < 10 and not any(c in text for c in '[/@'))):
                for cmd in self.commands:
                    if cmd.lower().startswith(word.lower()):
                        yield Completion(
                            cmd,
                            start_position=-len(word),
                            display_meta='指令'
                        )

    # 建立補全器
    smart_completer = SmartCompleter()
    slash_completer = SlashCommandCompleter()

    # 合併兩個補全器
    command_completer = merge_completers([slash_completer, smart_completer])

    # 創建輸入樣式（馬卡龍紫色系 + 斜線指令樣式）
    slash_style = get_slash_command_style()
    base_styles = {
        'prompt': '#b19cd9 bold',  # 馬卡龍薰衣草紫
        'multiline': '#c8b1e4 italic',  # 淡紫色
    }
    # 合併斜線指令樣式
    base_styles.update(dict(slash_style.style_rules))
    input_style = Style.from_dict(base_styles)

    # 創建按鍵綁定
    key_bindings = KeyBindings()

    @key_bindings.add('c-t')
    def toggle_thinking_display(event):
        """Ctrl+T / Ctrl+t: 切換思考過程顯示（循環：隱藏 → 翻譯 → 雙語對照）"""
        global SHOW_THINKING_PROCESS, LAST_THINKING_PROCESS, LAST_THINKING_TRANSLATED, CTRL_T_PRESS_COUNT

        # 調試資訊
        logger.debug(f"Ctrl+T 被按下,LAST_THINKING_PROCESS={LAST_THINKING_PROCESS is not None}, 長度={len(LAST_THINKING_PROCESS) if LAST_THINKING_PROCESS else 0}")

        # 沒有思考過程時提示
        if not LAST_THINKING_PROCESS:
            from utils import get_current_language
            current_lang = get_current_language()

            # 根據當前語言顯示提示訊息
            no_thinking_msg = {
                'zh-TW': '💭 尚未產生思考過程',
                'ja': '💭 思考プロセスがまだ生成されていません',
                'ko': '💭 아직 사고 과정이 생성되지 않았습니다',
                'en': '💭 No thinking process generated yet'
            }.get(current_lang, '💭 尚未產生思考過程')

            hint_msg = {
                'zh-TW': '提示：請先提問讓 AI 回答後再按 Ctrl+T',
                'ja': 'ヒント：まず質問してAIの回答を得た後、Ctrl+Tを押してください',
                'ko': '힌트: 먼저 질문하여 AI의 답변을 받은 후 Ctrl+T를 누르세요',
                'en': 'Hint: Ask a question and get AI response first, then press Ctrl+T'
            }.get(current_lang, '提示：請先提問讓 AI 回答後再按 Ctrl+T')

            console.print(safe_t('common.message', fallback=f'\n[#E8C4F0]{no_thinking_msg}[/#E8C4F0]\n'))
            console.print(safe_t('common.message', fallback=f'[dim COLOR_MACARON_PURPLE_LIGHT]{hint_msg}[/dim COLOR_MACARON_PURPLE_LIGHT]\n'))
            event.app.current_buffer.insert_text("")
            return

        # 循環切換：0(隱藏) → 1(翻譯) → 2(雙語) → 0
        CTRL_T_PRESS_COUNT = (CTRL_T_PRESS_COUNT + 1) % 3

        if CTRL_T_PRESS_COUNT == 1:
            # 第一次按下：顯示翻譯（或原文）
            SHOW_THINKING_PROCESS = True

            # 獲取當前語言以顯示對應標題
            from utils import get_current_language
            current_lang = get_current_language()
            lang_display = {
                'zh-TW': '翻譯',
                'ja': '翻訳',
                'ko': '번역',
                'en': 'Translation'
            }.get(current_lang, '翻譯')

            console.print(safe_t('common.message', fallback=f'\n[#B565D8]━━━ 🧠 思考過程（{lang_display}） ━━━[/#B565D8]'))

            # 如果有翻譯且翻譯功能啟用,顯示翻譯；否則顯示原文
            if TRANSLATOR_ENABLED and global_translator and LAST_THINKING_TRANSLATED:
                console.print(f"[dim]{LAST_THINKING_TRANSLATED}[/dim]")
            else:
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
                if TRANSLATOR_ENABLED and global_translator:
                    console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]💡 提示：翻譯功能可能未啟用或無可用引擎[/dim COLOR_MACARON_PURPLE_LIGHT]'))

            console.print("[#B565D8]━━━━━━━━━━━━━━━━━━━━━━━━━━[/#B565D8]\n")

        elif CTRL_T_PRESS_COUNT == 2:
            # 第二次按下：顯示雙語對照
            from utils import get_current_language
            current_lang = get_current_language()

            # 根據當前語言顯示對應的標題
            bilingual_title = {
                'zh-TW': '雙語對照',
                'ja': 'バイリンガル対照',
                'ko': '이중 언어 대조',
                'en': 'Bilingual Comparison'
            }.get(current_lang, '雙語對照')

            console.print(safe_t('common.message', fallback=f'\n[#B565D8]━━━ 🧠 思考過程（{bilingual_title}） ━━━[/#B565D8]'))

            if TRANSLATOR_ENABLED and global_translator and LAST_THINKING_TRANSLATED:
                # 根據當前語言顯示對應的旗幟和語言名稱
                lang_info = {
                    'zh-TW': {'flag': '🇹🇼', 'name': '繁體中文'},
                    'ja': {'flag': '🇯🇵', 'name': '日本語'},
                    'ko': {'flag': '🇰🇷', 'name': '한국어'},
                    'en': {'flag': '🇬🇧', 'name': 'English'}
                }.get(current_lang, {'flag': '🇹🇼', 'name': '繁體中文'})

                console.print(safe_t('common.message', fallback=f'[bold COLOR_MACARON_PURPLE]{lang_info["flag"]} {lang_info["name"]}：[/bold COLOR_MACARON_PURPLE]'))
                console.print(f"[dim]{LAST_THINKING_TRANSLATED}[/dim]\n")
                console.print(safe_t('common.message', fallback='[bold COLOR_MACARON_PURPLE]🇬🇧 English (Original)：[/bold COLOR_MACARON_PURPLE]'))
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
            else:
                console.print(safe_t('common.message', fallback='[bold COLOR_MACARON_PURPLE]🇬🇧 English (Original)：[/bold COLOR_MACARON_PURPLE]'))
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
                if TRANSLATOR_ENABLED and global_translator:
                    console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]💡 提示：翻譯功能可能未啟用或無可用引擎[/dim COLOR_MACARON_PURPLE_LIGHT]'))

            console.print("[#B565D8]━━━━━━━━━━━━━━━━━━━━━━━━━━[/#B565D8]\n")

        else:
            # 第三次按下：隱藏
            SHOW_THINKING_PROCESS = False
            from utils import get_current_language
            current_lang = get_current_language()

            # 根據當前語言顯示隱藏訊息
            hidden_msg = {
                'zh-TW': '💭 思考過程已隱藏',
                'ja': '💭 思考プロセスが非表示になりました',
                'ko': '💭 사고 과정이 숨겨졌습니다',
                'en': '💭 Thinking process hidden'
            }.get(current_lang, '💭 思考過程已隱藏')

            console.print(safe_t('common.message', fallback=f'\n[#E8C4F0]{hidden_msg}[/#E8C4F0]\n'))

        # 保存 UI 偏好到配置（新增）
        if codegemini_config_manager:
            try:
                codegemini_config_manager.config.system.show_thinking_process = SHOW_THINKING_PROCESS
                codegemini_config_manager.save_config()
                logger.debug(f"✓ 思考過程顯示偏好已保存: {SHOW_THINKING_PROCESS}")
            except Exception as e:
                logger.debug(f"保存 UI 偏好失敗: {e}")

        event.app.current_buffer.insert_text("")  # 保持輸入狀態

    @key_bindings.add('escape', 'enter')
    def insert_newline(event):
        """Alt+Enter: 插入新行（多行編輯）"""
        event.app.current_buffer.insert_text('\n')

    @key_bindings.add('c-d')
    def show_help_hint(event):
        """Ctrl+D: 顯示輸入提示"""
        console.print(safe_t('common.message', fallback='\n[#B565D8]💡 輸入提示：[/#B565D8]'))
        console.print(safe_t('common.message', fallback='  • [bold]Alt+Enter[/bold] - 插入新行（多行輸入）'))
        console.print(safe_t('common.message', fallback='  • [bold]Ctrl+T[/bold] - 切換思考過程顯示'))
        console.print(safe_t('common.message', fallback='  • [bold]↑/↓[/bold] - 瀏覽歷史記錄'))
        console.print(safe_t('common.message', fallback='  • [bold]Tab[/bold] - 自動補全指令與語法'))
        console.print(safe_t('common.message', fallback='  • [bold][think:1000,response:500][/bold] - 指定思考與回應 tokens'))
        console.print(safe_t('common.message', fallback='  • [bold][max_token:500][/bold] - 限制最大回應量（獨立使用,含動態計價）'))
        console.print()
        event.app.current_buffer.insert_text("")

    @key_bindings.add('enter', filter=has_completions)
    def accept_completion_without_submit(event):
        """Enter 在補全菜單打開時：只接受補全,不送出（改善用戶體驗）"""
        # 獲取當前選中的補全項目
        current_completion = event.app.current_buffer.complete_state
        if current_completion and current_completion.current_completion:
            # 接受當前選中的補全
            event.app.current_buffer.apply_completion(current_completion.current_completion)
        # 不調用 accept_line(),因此不會提交


def extract_thinking_process(response) -> Optional[str]:
    """
    從回應中提取思考過程內容

    Args:
        response: Gemini API 回應物件

    Returns:
        思考過程文字,如果不存在則回傳 None
    """
    try:
        if not hasattr(response, 'candidates') or not response.candidates:
            return None

        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
            return None

        # 遍歷所有 parts,查找思考內容
        thinking_parts = []
        for part in candidate.content.parts:
            # 檢查是否有 thought 或 thinking 欄位
            if hasattr(part, 'thought'):
                thinking_parts.append(part.thought)
            elif hasattr(part, 'thinking'):
                thinking_parts.append(part.thinking)
            # 有些實作可能用不同的欄位名
            elif hasattr(part, 'reasoning'):
                thinking_parts.append(part.reasoning)

        if thinking_parts:
            return '\n'.join(thinking_parts)

        return None
    except Exception as e:
        logger.warning(f"提取思考過程失敗: {e}")
        return None






def format_long_input_display(text: str, threshold_lines: int = 10, threshold_chars: int = 500) -> tuple:
    """
    檢測長文本並返回簡潔顯示格式（類似 Claude）

    Args:
        text: 用戶輸入的文本
        threshold_lines: 行數閾值,超過此值視為長文本（預設 10 行）
        threshold_chars: 單行字符閾值,超過此值視為長文本（預設 500 字符）

    Returns:
        tuple: (是否為長文本, 顯示文本, 原始文本)
    """
    if not text:
        return (False, text, text)

    lines = text.split('\n')
    line_count = len(lines)
    char_count = len(text)

    # 檢查是否為長文本
    is_long = line_count > threshold_lines or (line_count == 1 and char_count > threshold_chars)

    if is_long:
        # 生成簡潔顯示格式
        if line_count > 1:
            # 多行文本
            extra_lines = line_count - 1
            # 顯示第一行的前 50 個字符
            first_line_preview = lines[0][:50] + ("..." if len(lines[0]) > 50 else "")
            display_text = safe_t('chat.pasted_text_multiline', fallback='[📋 已貼上文本 +{extra_lines} 行] {preview}', extra_lines=extra_lines, preview=first_line_preview)
        else:
            # 單行超長文本
            preview = text[:50] + "..."
            display_text = safe_t('chat.pasted_text_long', fallback='[📋 已貼上長文本 ({char_count} 字元)] {preview}', char_count=char_count, preview=preview)

        return (True, display_text, text)
    else:
        # 正常長度文本,直接返回
        return (False, text, text)


def get_user_input(prompt_text: str = None) -> str:
    """
    獲取使用者輸入（支援 prompt_toolkit 增強功能）

    功能：
    - Alt+Enter: 多行編輯（插入新行）
    - Ctrl+T: 切換思考過程顯示
    - Ctrl+D: 顯示輸入提示
    - ↑/↓: 瀏覽歷史記錄
    - Tab: 自動補全指令與語法

    Args:
        prompt_text: 提示文字

    Returns:
        使用者輸入
    """
    if PROMPT_TOOLKIT_AVAILABLE:
        try:
            # 使用簡單的字串提示（避免 HTML 解析錯誤）
            return prompt(
                prompt_text,
                history=input_history,
                auto_suggest=AutoSuggestFromHistory(),
                completer=command_completer,
                key_bindings=key_bindings,
                enable_suspend=True,  # 允許 Ctrl+Z 暫停
                mouse_support=False,  # 禁用滑鼠支援避免衝突
                multiline=False,  # 預設單行,使用 Alt+Enter 可插入新行
                prompt_continuation=lambda width, line_number, is_soft_wrap: '... ',  # 多行續行提示
                complete_while_typing=True,  # 打字時即時補全
                style=input_style,  # 應用自訂樣式
            ).strip()
        except (KeyboardInterrupt, EOFError):
            return ""
        except Exception as e:
            # 降級到標準 input()
            logger.error(f"⚠️ prompt_toolkit 錯誤,降級到標準 input(): {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                return input(prompt_text).strip()
            except (KeyboardInterrupt, EOFError):
                return ""
    else:
        # 降級到標準 input()
        try:
            return input(prompt_text).strip()
        except (KeyboardInterrupt, EOFError):
            return ""










def setup_auto_cache(model_name: str) -> dict:
    """配置自動快取"""
    print("\n" + "=" * 60)
    print(safe_t('chat.cache.title', fallback='💾 自動快取管理（可節省 75-90% 成本）'))
    print(safe_t('chat.cache.current_model', fallback='📌 當前模型：{model}', model=model_name))
    print("=" * 60)

    choice = Prompt.ask(safe_t("chat.cache.enable_prompt", fallback=(
        "啟用自動快取？\n"
        "  [y] 是（推薦,5000 tokens 自動建立）\n"
        "  [c] 自訂設定\n"
        "  [m] 修改模型選擇\n"
        "  [n] 否\n"
        "  [b] 返回上一頁\n\n"
        "你的選擇 [y]: "
    ))).strip().lower() or 'y'

    if choice == 'b':
        # 返回上一頁
        return {'go_back': True}

    if choice == 'm':
        # 使用者要重新選擇模型
        return {'reselect_model': True}

    if choice == 'n':
        print(safe_t('chat.cache.disabled', fallback='✓ 快取功能已關閉\n'))
        return {'enabled': False}

    if choice == 'c':
        print(safe_t('chat.cache.advanced_settings', fallback='\n🔧 進階設定'))
        print("-" * 60)

        # 觸發模式
        mode_choice = Prompt.ask(safe_t("chat.cache.trigger_mode_prompt", fallback=(
            "觸發模式？\n"
            "  [a] 自動建立（達到門檻直接建立）\n"
            "  [p] 每次詢問（達到門檻時確認）\n"
            "  [b] 返回上一頁\n\n"
            "選擇 [a]: "
        ))).strip().lower() or 'a'

        if mode_choice == 'b':
            # 返回上一頁,重新顯示主選單
            return setup_auto_cache(model_name)

        mode = 'auto' if mode_choice == 'a' else 'prompt'

        # 快取門檻 - 根據模型動態生成選項（符合專案思想：環境依附而非硬編碼）
        min_required = MIN_TOKENS.get(model_name, 1024)

        # 根據模型的最低限制動態生成選項
        if min_required >= 32768:
            # Gemini 2.0 Flash 系列（最低 32,768）
            threshold_map = {
                '1': 32768,   # 最低限制（API 要求）
                '2': 50000,   # 推薦值（中型對話）
                '3': 80000    # 大型對話
            }
            option_desc = {
                '1': f"{threshold_map['1']:,} tokens（最低限制,約 32 頁）",
                '2': f"{threshold_map['2']:,} tokens（推薦,約 50 頁）",
                '3': f"{threshold_map['3']:,} tokens（大型對話,約 80 頁）"
            }
        elif min_required >= 4096:
            # Gemini 2.5 Pro（最低 4,096,官方文檔驗證）
            threshold_map = {
                '1': 4096,    # 最低限制（API 要求）
                '2': 8000,    # 推薦值（中型對話）
                '3': 16000    # 大型對話
            }
            option_desc = {
                '1': f"{threshold_map['1']:,} tokens（最低限制,約 4 頁）",
                '2': f"{threshold_map['2']:,} tokens（推薦,約 8 頁）",
                '3': f"{threshold_map['3']:,} tokens（大型對話,約 16 頁）"
            }
        else:
            # Gemini 2.5 Flash / Flash-8B（最低 1,024,官方文檔驗證）
            threshold_map = {
                '1': 1024,    # 最低限制（API 要求）
                '2': 5000,    # 推薦值（中型對話）
                '3': 8000     # 大型對話
            }
            option_desc = {
                '1': f"{threshold_map['1']:,} tokens（最低限制,約 1 頁）",
                '2': f"{threshold_map['2']:,} tokens（推薦,約 5 頁）",
                '3': f"{threshold_map['3']:,} tokens（大型對話,約 8 頁）"
            }

        # 顯示動態生成的選項
        threshold_prompt = f"""
快取門檻？（{model_name} 最低需要 {min_required:,} tokens）
  [1] {option_desc['1']}
  [2] {option_desc['2']}
  [3] {option_desc['3']}
  [c] 自訂
  [b] 返回上一頁

選擇 [2]: """

        threshold_choice = Prompt.ask(safe_t("chat.cache.threshold_prompt_dynamic",
                                       fallback=threshold_prompt)).strip() or '2'

        if threshold_choice == 'b':
            # 返回上一頁,重新顯示主選單
            return setup_auto_cache(model_name)

        if threshold_choice == 'c':
            custom = Prompt.ask(safe_t("chat.cache.threshold_custom_prompt",
                                 fallback=f"請輸入門檻（最低 {min_required:,} tokens）: ")).strip()
            threshold = int(custom) if custom.isdigit() else threshold_map['2']
            # 檢查是否低於最低限制
            if threshold < min_required:
                print(safe_t('chat.cache.min_tokens_warning',
                           fallback='\n⚠️  {model} 最低需要 {min_tokens:,} tokens',
                           model=model_name, min_tokens=min_required))
                print(safe_t('chat.cache.auto_adjust',
                           fallback='   自動調整為 {min_tokens:,}',
                           min_tokens=min_required))
                threshold = min_required
        else:
            threshold = threshold_map.get(threshold_choice, threshold_map['2'])

        # TTL
        ttl_input = Prompt.ask(safe_t("chat.cache.ttl_prompt", fallback=(
            "存活時間（小時） [1]: "
        ))).strip()
        ttl = int(ttl_input) if ttl_input.isdigit() else 1

        print(safe_t('chat.cache.config_done', fallback='\n✓ 設定完成：{mode} 模式,門檻 {threshold:,} tokens,TTL {ttl}h\n', mode=mode, threshold=threshold, ttl=ttl))
        return {'enabled': True, 'mode': mode, 'threshold': threshold, 'ttl': ttl}

    else:  # 'y' - 使用預設值（根據模型動態選擇推薦值）
        min_required = MIN_TOKENS.get(model_name, 1024)

        # 根據模型選擇合適的預設門檻
        if min_required >= 32768:
            default_threshold = 50000  # 2.0 Flash 推薦值
        elif min_required >= 4096:
            default_threshold = 8000   # 2.5 Pro 推薦值
        else:
            default_threshold = 5000   # 2.5 Flash 推薦值

        print(safe_t('chat.cache.recommended',
                    fallback='✓ 使用推薦設定：自動模式,{threshold:,} tokens,TTL 1 小時\n',
                    threshold=default_threshold))
        return {'enabled': True, 'mode': 'auto', 'threshold': default_threshold, 'ttl': 1}






def send_message(
    model_name: str,
    user_input: str,
    chat_logger,
    use_thinking: bool = True,
    thinking_budget: int = -1,
    max_output_tokens: Optional[int] = None,
    uploaded_files: List = None
) -> Optional[str]:
    """
    發送訊息到 Gemini（新 SDK）- 串流模式

    Args:
        model_name: 模型名稱
        user_input: 使用者輸入
        chat_logger: 對話記錄器
        use_thinking: 是否使用思考模式
        thinking_budget: 思考預算,依模型而異：
            - -1: 動態模式（所有模型）
            - gemini-2.5-pro: 128-32768 tokens（無法停用）
            - gemini-2.5-flash: 0-24576 tokens（0=停用）
            - gemini-2.5-flash-lite: 512-24576 tokens（0=停用）
        max_output_tokens: 最大輸出 tokens（1-8192,None=使用模型預設值）
        uploaded_files: 上傳的檔案物件列表

    Returns:
        AI 回應文本
    """
    global global_translator, LAST_THINKING_TRANSLATED, CTRL_T_PRESS_COUNT

    try:
        # 🎯 API 調用前觸發 Tier 3 載入（v2.3 智能預載入）
        # 等待 API 回應時（預估 2-5秒）,載入低頻功能模組
        try:
            on_api_call_start()
        except Exception as e:
            logger.debug(f"背景載入觸發失敗（不影響功能）: {e}")

        # 清除翻譯器的單次快取（新 Prompt 發送時）
        if TRANSLATOR_ENABLED and global_translator:
            global_translator.clear_current_prompt_cache()

        # ========================================
        # 無痕整合：自動增強 Prompt（CodeGemini 功能）
        # ========================================
        hidden_trigger_tokens = None
        if SMART_TRIGGERS_ENABLED:
            try:
                # 獲取 API 金鑰
                api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

                # 自動檢測並增強 prompt,並取得額外 token 使用量
                user_input, hidden_trigger_tokens = auto_enhance_prompt(
                    user_input=user_input,
                    api_key=api_key,
                    uploaded_files=uploaded_files,
                    enable_task_planning=True,
                    enable_web_search=True,
                    enable_code_analysis=True
                )

                # 如果沒有額外用量,設為 None
                if hidden_trigger_tokens and (hidden_trigger_tokens['api_input'] == 0 and
                                             hidden_trigger_tokens['api_output'] == 0):
                    hidden_trigger_tokens = None

            except Exception as e:
                logger.debug(f"智能觸發器執行失敗: {e}")
                hidden_trigger_tokens = None

        # 記錄使用者輸入
        chat_logger.log_user(user_input)

        # 檢查是否支援思考模式
        supports_thinking = any(tm in model_name for tm in THINKING_MODELS)

        # 配置與思考簽名顯示
        config = types.GenerateContentConfig()

        # 設定最大輸出 tokens（如果指定）
        if max_output_tokens is not None:
            config.max_output_tokens = max_output_tokens
            print(safe_t('chat.output.limit', fallback='📝 [輸出限制] {tokens:,} tokens', tokens=max_output_tokens))

        if supports_thinking and use_thinking:
            config.thinking_config = types.ThinkingConfig(
                thinking_budget=thinking_budget,
                include_thoughts=True  # 啟用思考摘要串流
            )
            # 顯示思考簽名
            if thinking_budget == -1:
                print(safe_t('chat.thinking.dynamic_mode', fallback='🧠 [思考簽名] 動態思考模式 ✓'))
            else:
                # 計算並顯示預估費用
                if PRICING_ENABLED:
                    try:
                        pricing = global_pricing_calculator.get_model_pricing(model_name)
                        input_price = pricing.get('input', pricing.get('input_low', 0))
                        estimated_cost_usd = (thinking_budget / 1000) * input_price
                        estimated_cost_twd = estimated_cost_usd * USD_TO_TWD
                        print(safe_t('chat.thinking.budget_with_cost', fallback='🧠 [思考簽名] {tokens:,} tokens ✓ (預估: NT$ {twd:.4f} / ${usd:.6f})', tokens=thinking_budget, twd=estimated_cost_twd, usd=estimated_cost_usd))
                    except (KeyError, AttributeError, TypeError) as e:
                        logger.warning(f"計價估算失敗 (模型: {model_name}, 預算: {thinking_budget}): {e}")
                        print(safe_t('chat.thinking.budget', fallback='🧠 [思考簽名] {tokens:,} tokens ✓', tokens=thinking_budget))
                else:
                    print(safe_t('chat.thinking.budget', fallback='🧠 [思考簽名] {tokens:,} tokens ✓', tokens=thinking_budget))
        elif supports_thinking and not use_thinking:
            print(safe_t('chat.thinking.disabled', fallback='🧠 [思考簽名] 已停用 ✗'))

        # 準備內容（文字 + 檔案）
        if uploaded_files and len(uploaded_files) > 0:
            # 有上傳檔案：組合內容
            content_parts = [user_input] + uploaded_files
        else:
            # 純文字
            content_parts = user_input

        # 發送串流請求
        print("\nGemini: ", end="", flush=True)

        # 使用串流模式（自動重試）
        if API_RETRY_ENABLED:
            # 包裝 API 呼叫以支援自動重試
            @with_retry("Gemini API 串流請求", max_retries=3)
            def _make_api_call():
                return client.models.generate_content_stream(
                    model=model_name,
                    contents=content_parts,
                    config=config
                )
            stream = _make_api_call()
        else:
            stream = client.models.generate_content_stream(
                model=model_name,
                contents=content_parts,
                config=config
            )

        # 累積變數
        thoughts_text = ""
        response_text = ""
        thinking_displayed = False
        answer_started = False
        final_response = None  # 保存最後一個 response 用於提取 metadata

        global SHOW_THINKING_PROCESS, LAST_THINKING_PROCESS

        # 創建串流顯示器（如果啟用計價）
        streaming_display = None
        if PRICING_ENABLED and STREAMING_DISPLAY_AVAILABLE:
            try:
                streaming_display = StreamingTokenDisplay(
                    model_name=model_name,
                    pricing_calculator=global_pricing_calculator,
                    console=console
                )
                streaming_display.start_streaming(input_tokens=0, thinking_tokens=0)
            except Exception as e:
                logger.debug(f"串流顯示器初始化失敗: {e}")
                streaming_display = None

        # 處理串流 chunks
        for chunk in stream:
            final_response = chunk  # 持續更新,最後一個包含完整 metadata

            if not hasattr(chunk, 'candidates') or len(chunk.candidates) == 0:
                continue

            candidate = chunk.candidates[0]
            if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
                continue

            # 遍歷所有 parts
            for part in candidate.content.parts:
                if not hasattr(part, 'text') or not part.text:
                    continue

                # 檢查是否為思考部分
                # 調試：顯示 part 的屬性
                logger.debug(f"Part 屬性: thought={getattr(part, 'thought', 'N/A')}, has_text={hasattr(part, 'text')}, text_len={len(part.text) if hasattr(part, 'text') and part.text else 0}")

                if hasattr(part, 'thought') and part.thought:
                    # 這是思考摘要
                    thoughts_text += part.text
                    logger.debug(f"✓ 累積思考內容,目前長度: {len(thoughts_text)}")

                    if SHOW_THINKING_PROCESS and not thinking_displayed:
                        # 首次顯示思考標題
                        console.print(safe_t('common.message', fallback='\n[dim COLOR_MACARON_PURPLE]━━━ 🧠 思考過程（即時串流） ━━━[/dim COLOR_MACARON_PURPLE]'))
                        thinking_displayed = True

                    if SHOW_THINKING_PROCESS:
                        # 即時顯示思考內容
                        console.print(f"[dim]{part.text}[/dim]", end="")
                else:
                    # 這是正常回應文字
                    response_text += part.text

                    if not answer_started:
                        # 首次輸出回應時的處理
                        if thinking_displayed:
                            console.print("[dim COLOR_MACARON_PURPLE]\n━━━━━━━━━━━━━━━[/dim COLOR_MACARON_PURPLE]\n")
                            print("Gemini: ", end="", flush=True)
                        answer_started = True

                    # 串流輸出回應文字
                    print(part.text, end="", flush=True)

                    # 更新串流顯示器（即時 token 計數）
                    if streaming_display:
                        streaming_display.update_output(part.text)

        # 串流結束,換行
        print()

        # 顯示 Markdown 格式化版本（如果有內容）
        if response_text.strip():
            console.print("\n")
            console.print(Panel(
                Markdown(response_text),
                title="[#B565D8]📝 格式化輸出[/#B565D8]",
                border_style="COLOR_MACARON_PURPLE_LIGHT"
            ))

        # 保存思考過程
        thinking_process = thoughts_text if thoughts_text else None
        LAST_THINKING_PROCESS = thinking_process
        logger.debug(f"儲存思考過程: {thinking_process is not None}, 長度: {len(thinking_process) if thinking_process else 0}")

        # 檢查：如果使用者要求思考模式但 Gemini 沒有回傳思考內容
        if supports_thinking and use_thinking and not thinking_process:
            console.print(safe_t('common.warning', fallback='\n[yellow]⚠️  Gemini 拒絕使用思考模式[/yellow]'))
            console.print(safe_t('common.message', fallback='[dim yellow]可能原因：問題過於簡單、或 API 配置限制[/dim yellow]\n'))
            logger.warning(f"使用者要求思考模式但未收到思考內容 - 模型: {model_name}, use_thinking={use_thinking}, thinking_budget={thinking_budget}")

        # 翻譯思考過程（無論是否顯示都先翻譯,以便 Ctrl+T 使用）
        LAST_THINKING_TRANSLATED = None  # 重置翻譯
        CTRL_T_PRESS_COUNT = 0  # 重置 Ctrl+T 計數器

        if thinking_process and TRANSLATOR_ENABLED:
            # 確保翻譯器已載入（延遲載入）
            if global_translator is None:
                global_translator = get_global_translator()

            if global_translator and global_translator.translation_enabled:
                # 使用 translate_thinking() 自動根據當前 i18n 語言翻譯（支援 zh-TW, ja, ko）
                from gemini_translator import translate_thinking
                LAST_THINKING_TRANSLATED = translate_thinking(thinking_process)
                logger.debug(f"思考過程翻譯狀態: 原文長度={len(thinking_process)}, 譯文長度={len(LAST_THINKING_TRANSLATED) if LAST_THINKING_TRANSLATED else 0}, 是否相同={LAST_THINKING_TRANSLATED == thinking_process if LAST_THINKING_TRANSLATED else True}")

        # 如果有思考過程但未顯示,給予提示
        if thinking_process and not SHOW_THINKING_PROCESS:
            if TRANSLATOR_ENABLED and global_translator and global_translator.translation_enabled:
                console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]💭 已產生思考摘要 (Ctrl+T 顯示翻譯思路)[/dim COLOR_MACARON_PURPLE_LIGHT]'))
            else:
                console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]💭 已產生思考摘要 (Ctrl+T 顯示思路)[/dim COLOR_MACARON_PURPLE_LIGHT]'))

        # 如果啟用翻譯且已顯示思考,則追加翻譯
        if thinking_process and SHOW_THINKING_PROCESS and TRANSLATOR_ENABLED and global_translator and global_translator.translation_enabled and LAST_THINKING_TRANSLATED:
            if LAST_THINKING_TRANSLATED != thinking_process:
                console.print(safe_t('common.message', fallback='\n[dim COLOR_MACARON_PURPLE]━━━ 🌐 思考過程翻譯 ━━━[/dim COLOR_MACARON_PURPLE]'))
                console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE]【繁體中文】[/dim COLOR_MACARON_PURPLE]'))
                console.print(f"[dim]{LAST_THINKING_TRANSLATED}[/dim]")
                console.print("[dim COLOR_MACARON_PURPLE]━━━━━━━━━━━━━━━[/dim COLOR_MACARON_PURPLE]\n")

        print()  # 額外換行

        # 記錄助手回應（包含思考過程）
        chat_logger.log_assistant(response_text, thinking_process=thinking_process)

        # 保存思考簽名（如果有啟用函數呼叫）
        if global_thinking_signature_manager and final_response:
            # 檢查 config 是否有 tools（函數宣告）
            has_function_calling = hasattr(config, 'tools') and config.tools is not None
            global_thinking_signature_manager.save_response(final_response, has_function_calling)

        # 提取 tokens（從最後一個 response chunk）
        thinking_tokens = 0
        input_tokens = 0
        output_tokens = 0

        if final_response and hasattr(final_response, 'usage_metadata'):
            # 優先使用新欄位 thoughts_token_count,向後相容舊欄位 thinking_tokens
            thinking_tokens = getattr(final_response.usage_metadata, 'thoughts_token_count',
                                     getattr(final_response.usage_metadata, 'thinking_tokens', 0))
            input_tokens = getattr(final_response.usage_metadata, 'prompt_tokens', 0)
            output_tokens = getattr(final_response.usage_metadata, 'candidates_tokens', 0)

            # 更新串流顯示器的最終 token 數
            if streaming_display:
                streaming_display.set_final_tokens(input_tokens, thinking_tokens, output_tokens)

        # 調試：顯示 token 數量
        logger.debug(f"💰 Token 用量檢測: 輸入={input_tokens}, 輸出={output_tokens}, 思考={thinking_tokens}")
        logger.debug(f"💰 計價狀態: PRICING_ENABLED={PRICING_ENABLED}, 條件滿足={input_tokens > 0 and output_tokens > 0}")

        # 顯示即時成本（新台幣,包含智能觸發器成本）
        if PRICING_ENABLED and input_tokens > 0 and output_tokens > 0:
            try:
                # 使用串流顯示器打印最終摘要（如果可用）
                if streaming_display:
                    logger.debug(f"💰 使用串流顯示器顯示計價")
                    streaming_display.print_final_summary(hidden_trigger_tokens=hidden_trigger_tokens)
                else:
                    # 降級到原有顯示方式
                    cost, details = global_pricing_calculator.calculate_text_cost(
                        model_name,
                        input_tokens,
                        output_tokens,
                        thinking_tokens,
                        hidden_trigger_tokens=hidden_trigger_tokens
                    )

                    # 檢查是否有隱藏成本
                    hidden_cost = details.get('hidden_trigger_cost', 0)
                    hidden_input = details.get('hidden_trigger_input_tokens', 0)
                    hidden_output = details.get('hidden_trigger_output_tokens', 0)

                    # 顯示格式
                    cost_display = safe_t('chat.current_cost', fallback='💰 本次成本: NT${cost:.2f}', cost=cost * PRICING_USD_TO_TWD)

                    # Token 使用明細
                    token_parts = []
                    token_parts.append(safe_t('chat.tokens_input', fallback='輸入: {count:,} tokens', count=input_tokens))
                    if thinking_tokens > 0:
                        token_parts.append(safe_t('chat.tokens_thinking', fallback='思考: {count:,} tokens', count=thinking_tokens))
                    token_parts.append(safe_t('chat.tokens_output', fallback='輸出: {count:,} tokens', count=output_tokens))

                    # 如果有隱藏成本,顯示提示
                    if hidden_cost > 0:
                        token_parts.append(safe_t('chat.tokens_smart_enhance', fallback='🤖智能增強: {count:,} tokens', count=hidden_input + hidden_output))

                    cost_display += f" ({', '.join(token_parts)})"
                    cost_display += f" | 累計: NT${global_pricing_calculator.total_cost * PRICING_USD_TO_TWD:.2f} (${global_pricing_calculator.total_cost:.6f})"

                    print(cost_display)

                    # 如果有隱藏成本,顯示詳細說明
                    if hidden_cost > 0:
                        hidden_model = details.get('hidden_trigger_model', 'unknown')
                        print(safe_t('chat.cost.conversation', fallback='   ├─ 對話成本: NT${cost:.2f}', cost=(cost - hidden_cost) * PRICING_USD_TO_TWD))
                        print(safe_t('chat.cost.smart_enhancement', fallback='   └─ 智能增強成本: NT${cost:.2f} (任務規劃, {model})', cost=hidden_cost * PRICING_USD_TO_TWD, model=hidden_model))

            except Exception as e:
                logger.warning(f"計價失敗: {e}")

        # 🔧 記憶體洩漏修復：釋放上傳檔案的記憶體引用
        if uploaded_files:
            uploaded_files.clear()
            uploaded_files = None

        return response_text

    except Exception as e:
        error_msg = f"發送失敗：{e}"
        logger.error(error_msg)
        print(f"\n✗ {error_msg}")

        # 智能錯誤診斷（自動整合,含互動式修復）
        if ERROR_DIAGNOSTICS_ENABLED and global_error_diagnostics:
            try:
                context = {
                    'operation': 'Gemini API 請求',
                    'model': model_name,
                    'user_input': user_input[:100] if len(user_input) > 100 else user_input,
                    'uploaded_files': len(uploaded_files) if uploaded_files else 0
                }
                error_message, solutions = global_error_diagnostics.diagnose_and_suggest(
                    error=e,
                    operation="Gemini API 請求",
                    context=context
                )
                if solutions:
                    # 使用新的互動式顯示方法
                    global_error_diagnostics.display_solutions(error_message, solutions)
            except Exception as diag_error:
                logger.debug(f"錯誤診斷失敗: {diag_error}")

        # 🔧 記憶體洩漏修復：異常情況下也要釋放記憶體
        if uploaded_files:
            uploaded_files.clear()
            uploaded_files = None

        return None


def chat(model_name: str, chat_logger, auto_cache_config: dict, codebase_embedding=None):
    """互動式對話主循環"""
    global codegemini_config_manager
    print("\n" + "=" * 60)
    print(safe_t('chat.main.title', fallback='Gemini 對話（模型：{model}）', model=model_name))
    print("=" * 60)

    # 初始化自動快取管理器
    auto_cache_mgr = module_loader.get("cache").AutoCacheManager(
        enabled=auto_cache_config.get('enabled', False),
        mode=auto_cache_config.get('mode', 'auto'),
        threshold=auto_cache_config.get('threshold', 5000),
        ttl=auto_cache_config.get('ttl', 1)
    )

    # 初始化背景待辦事項追蹤器（無痕整合）
    background_todo_tracker = None
    if SMART_TRIGGERS_ENABLED:
        try:
            background_todo_tracker = BackgroundTodoTracker()
            logger.debug("✓ 背景待辦事項追蹤器已啟動")
        except Exception as e:
            logger.debug(f"背景待辦事項追蹤器初始化失敗: {e}")

    # 顯示快取狀態
    if auto_cache_mgr.enabled:
        print(safe_t('chat.cache.auto_enabled', fallback='\n✓ 自動快取：已啟用（{mode} 模式,門檻 {threshold:,} tokens）', mode=auto_cache_mgr.mode, threshold=auto_cache_mgr.threshold))
    elif CACHE_ENABLED:
        try:
            caches = list(global_cache_manager.list_caches())
            if caches:
                valid_caches = [c for c in caches if c.expire_time > datetime.now()]
                console.print(safe_t('common.message', fallback='\n[#B565D8]💾 快取狀態：{cache_count} 個有效快取（可節省 75-90% 成本）[/#B565D8]', cache_count=len(valid_caches)))
            else:
                console.print(safe_t('common.message', fallback="\n[#E8C4F0]💾 快取狀態：無快取（提示：輸入 'cache' 了解如何建立）[/#E8C4F0]"))
        except Exception as e:
            logger.debug(f"快取狀態檢查失敗: {e}")

    import shutil

    # 檢測終端機大小
    terminal_height = shutil.get_terminal_size().lines

    # 顯示收集的啟動訊息（在指令說明之前）
    global STARTUP_MESSAGES
    if STARTUP_MESSAGES:
        console.print()  # 空行分隔
        for msg in STARTUP_MESSAGES:
            console.print(msg)
        STARTUP_MESSAGES.clear()  # 清空以避免重複顯示
        console.print()  # 空行分隔

    # 簡潔的指令提示（馬卡龍紫色系）
    console.print(safe_t('common.message', fallback='\n[#B565D8]💡 請按 [/#B565D8][#E8C4F0]/[/#E8C4F0][#B565D8] 顯示完整指令列表[/#B565D8]'))
    console.print("[#E8C4F0]" + "-" * 60 + "[/#E8C4F0]")
    console.print()

    chat_logger.set_model(model_name)

    # 🎯 追蹤首次輸入（v2.3 智能預載入）
    _first_input = True

    # 🆕 顯示更新通知 (如果有可用更新)
    if config.get('UPDATE_CHECK_ENABLED', True):
        try:
            from gemini_updater import show_update_notification
            show_update_notification()
        except:
            pass  # 靜默失敗

    while True:
        try:
            # 🎯 首次輸入觸發 Tier 2 載入（v2.3 智能預載入）
            if _first_input:
                try:
                    on_first_input_start()
                    _first_input = False
                except Exception as e:
                    logger.debug(f"背景載入觸發失敗（不影響功能）: {e}")

            # 使用增強型輸入（自動使用當前語言,支援降級運行）
            # 決定提示文字（進階輸入模式顯示參數提示）
            if PROMPT_TOOLKIT_AVAILABLE:
                # 進階輸入模式：顯示參數提示
                try:
                    import shutil
                    term_width = shutil.get_terminal_size((80, 24)).columns

                    if term_width > 100:
                        # 寬螢幕：顯示詳細提示
                        prompt_hint = safe_t('chat.user_prompt_with_hint_detailed',
                                           fallback='你 (輸入 [ 查看 think/max 參數)')
                    else:
                        # 窄螢幕：簡化提示
                        prompt_hint = safe_t('chat.user_prompt_with_hint',
                                           fallback='你 ([ 參數)')
                except Exception:
                    # 取得終端機寬度失敗,使用簡化提示
                    prompt_hint = safe_t('chat.user_prompt_with_hint',
                                       fallback='你 ([ 參數)')
            else:
                # 標準輸入模式：無提示
                prompt_hint = safe_t('chat.user_prompt', fallback='你')

            user_input = get_user_input(prompt_hint + ": ")

            if not user_input:
                continue

            # 處理斜線指令（白名單制度：只有明確定義的指令才執行）
            if user_input.startswith('/'):
                # 移除斜線,轉換為對應的指令
                slash_cmd = user_input[1:].strip()
                slash_cmd_lower = slash_cmd.lower()

                # 特殊處理：單獨輸入 / 顯示完整指令列表
                if slash_cmd == '':
                    console.print("\n" + "=" * 60)
                    console.print(safe_t('chat.help.commands.title', fallback='[#B565D8]📋 完整指令列表[/#B565D8]'))
                    console.print("=" * 60)
                    console.print(safe_t('common.message', fallback='[#E8C4F0]基本指令：[/#E8C4F0]'))
                    console.print('  exit, quit      - ' + safe_t('chat.help.commands.exit', fallback='退出程式'))
                    console.print('  model           - ' + safe_t('chat.help.commands.model', fallback='切換模型'))
                    console.print('  clear           - ' + safe_t('chat.help.commands.clear', fallback='清除對話歷史'))
                    console.print('  lang, language  - ' + safe_t('chat.help.commands.lang', fallback='切換語言（zh-TW/en/ja/ko）🆕'))
                    console.print('  cache           - ' + safe_t('chat.help.commands.cache', fallback='快取管理選單'))
                    console.print('  media           - ' + safe_t('chat.help.commands.media', fallback='影音功能選單（Flow/Veo/分析/處理）'))
                    console.print('  config          - ' + safe_t('common.message', fallback='配置管理（資料庫設定）'))
                    if CODEGEMINI_ENABLED:
                        console.print('  cli             - ' + safe_t('chat.help.commands.cli', fallback='Gemini CLI 管理工具'))
                    console.print('  debug, test     - ' + safe_t('common.message', fallback='除錯與測試工具'))
                    console.print('  help            - ' + safe_t('chat.help.commands.help', fallback='顯示詳細幫助系統'))
                    console.print()
                    console.print(safe_t('common.message', fallback='[#E8C4F0]系統更新：[/#E8C4F0]'))
                    console.print('  /upgrade        - ' + safe_t('common.message', fallback='執行系統更新（智能合併配置）'))
                    console.print()
                    console.print(safe_t('common.message', fallback='[#E8C4F0]記憶體管理：[/#E8C4F0]'))
                    console.print('  /clear-memory   - ' + safe_t('common.message', fallback='清理記憶體快取'))
                    console.print('  /memory-stats   - ' + safe_t('common.message', fallback='顯示記憶體統計'))
                    console.print('  /help-memory    - ' + safe_t('common.message', fallback='記憶體管理說明'))
                    console.print()
                    console.print(safe_t('common.message', fallback='[#E8C4F0]檢查點系統：[/#E8C4F0]'))
                    console.print('  /checkpoints    - ' + safe_t('common.message', fallback='列出所有檢查點'))
                    console.print('  /checkpoint [描述] - ' + safe_t('common.message', fallback='建立手動檢查點'))
                    console.print('  /rewind [ID]    - ' + safe_t('common.message', fallback='回溯至檢查點'))
                    console.print('  /help-checkpoint - ' + safe_t('common.message', fallback='檢查點系統說明'))
                    if HISTORY_MANAGER_AVAILABLE:
                        console.print()
                        console.print(safe_t('common.message', fallback='[#E8C4F0]對話歷史：[/#E8C4F0]'))
                        console.print('  /search <關鍵字> - ' + safe_t('common.message', fallback='搜尋對話歷史'))
                        console.print('  /history        - ' + safe_t('common.message', fallback='顯示最近對話'))
                        console.print('  /export [格式]  - ' + safe_t('common.message', fallback='匯出對話記錄'))
                        console.print('  /stats          - ' + safe_t('common.message', fallback='對話統計資訊'))
                    console.print()
                    console.print(safe_t('chat.help.commands.thinking_mode', fallback='[#E8C4F0]思考模式：[/#E8C4F0]'))
                    console.print('  [think:auto]    - ' + safe_t('chat.help.commands.think_auto', fallback='動態思考（預設）'))
                    console.print('  [think:數字]    - ' + safe_t('common.message', fallback='指定思考預算'))
                    console.print('  [no-think]      - ' + safe_t('chat.help.commands.think_off', fallback='停用思考'))
                    console.print()
                    console.print(safe_t('chat.help.commands.output_control', fallback='[#E8C4F0]輸出控制：[/#E8C4F0]'))
                    console.print('  [max_token:數字] - ' + safe_t('chat.help.commands.output_limit', fallback='最大回應量（1-8192）'))
                    console.print()
                    console.print(safe_t('chat.help.commands.file_attach', fallback='[#E8C4F0]檔案附加：[/#E8C4F0]'))
                    console.print('  @檔案路徑       - ' + safe_t('chat.help.commands.file_at', fallback='附加檔案'))
                    console.print('  讀取 檔案       - ' + safe_t('chat.help.commands.file_read', fallback='讀取檔案'))
                    console.print('  附加 檔案       - ' + safe_t('chat.help.commands.file_attach_cmd', fallback='附加檔案'))
                    console.print('  上傳 檔案       - ' + safe_t('chat.help.commands.file_upload', fallback='上傳媒體'))
                    console.print()
                    console.print(safe_t('chat.help.commands.cache_control', fallback='[#E8C4F0]快取控制：[/#E8C4F0]'))
                    console.print('  [cache:now]     - ' + safe_t('chat.help.commands.cache_now', fallback='立即建立'))
                    console.print('  [cache:off]     - ' + safe_t('chat.help.commands.cache_off', fallback='暫停自動'))
                    console.print('  [cache:on]      - ' + safe_t('chat.help.commands.cache_on', fallback='恢復自動'))
                    console.print('  [no-cache]      - ' + safe_t('chat.help.commands.no_cache', fallback='排除本次'))
                    console.print("=" * 60)
                    console.print()
                    continue

                # 檢查內建指令
                # 白名單：明確定義的斜線指令
                slash_command_whitelist = {
                    'exit': 'exit',
                    'quit': 'exit',
                    'help': 'help',
                    'lang': 'lang',
                    'language': 'lang',
                    'model': '/model',  # 保留斜線
                    'cache': 'cache',
                    'clear': 'clear',
                    'media': 'media',
                    'video': 'media',
                    'veo': 'media',
                    'debug': 'debug',
                    'test': 'debug',
                    'config': 'config',
                    'cli': 'cli',
                    'gemini-cli': 'cli',
                    'upgrade': 'upgrade',
                    'budget': '/budget',  # 保留斜線
                    'clear-memory': '/clear-memory',  # 保留斜線
                    'memory-stats': '/memory-stats',  # 保留斜線
                    'help-memory': '/help-memory',  # 保留斜線
                    'checkpoints': '/checkpoints',  # 保留斜線
                    'checkpoint': '/checkpoint',  # 保留斜線
                    'rewind': '/rewind',  # 保留斜線
                    'help-checkpoint': '/help-checkpoint',  # 保留斜線
                    'search': '/search',  # 保留斜線
                    'history': '/history',  # 保留斜線
                    'export': '/export',  # 保留斜線
                    'stats': '/stats',  # 保留斜線
                }

                # 檢查是否為有效的斜線指令（包括帶參數的指令）
                # 先檢查完整指令
                if slash_cmd_lower in slash_command_whitelist:
                    # 將斜線指令轉換為實際指令
                    user_input = slash_command_whitelist[slash_cmd_lower]
                    # 繼續執行下面的指令處理邏輯
                # 再檢查指令的第一個字（處理帶參數的指令，如 /model update, /checkpoint 描述）
                elif slash_cmd_lower.split()[0] in slash_command_whitelist:
                    # 保留完整輸入（包含參數）
                    base_cmd = slash_cmd_lower.split()[0]
                    user_input = '/' + slash_cmd  # 保持原始輸入
                    # 繼續執行下面的指令處理邏輯
                else:
                    # 不是有效指令，嘗試模糊匹配
                    from difflib import get_close_matches
                    base_cmd = slash_cmd_lower.split()[0]  # 只匹配基礎指令
                    suggestions = get_close_matches(base_cmd, slash_command_whitelist.keys(), n=3, cutoff=0.6)

                    if suggestions:
                        console.print(f"\n[#B565D8]❌ 未知指令: /{slash_cmd}[/#B565D8]")
                        console.print(f"[#E8C4F0]💡 您是否想要輸入以下指令？[/#E8C4F0]")
                        for sug in suggestions:
                            console.print(f"   • /{sug}")
                        console.print()
                    else:
                        console.print(f"\n[#B565D8]❌ 未知指令: /{slash_cmd}[/#B565D8]")
                        console.print(f"[#E8C4F0]💡 輸入 [bold]/[/bold] 或 [bold]/help[/bold] 查看可用指令[/#E8C4F0]\n")
                    continue

            # 處理指令
            if user_input.lower() in ['exit', 'quit', '退出']:
                print(f"\n{safe_t('chat.goodbye', fallback='再見！')}")
                try:
                    chat_logger.save_session()

                    # 保存使用者設定（CodeGemini 配置）
                    if codegemini_config_manager:
                        try:
                            codegemini_config_manager.save_config()
                            logger.debug("✓ 設定已保存")
                        except Exception as e:
                            logger.debug(f"設定保存失敗: {e}")

                    # 清理工具
                    if TOOLS_MANAGER_AVAILABLE:
                        try:
                            cleanup_tools()
                            logger.debug("✓ 工具已清理")
                        except Exception as e:
                            logger.debug(f"工具清理失敗: {e}")
                except Exception as e:
                    logger.debug(f"退出清理失敗: {e}")
                break

            elif user_input.lower() in ['lang', 'language', '語言']:
                # 語言切換命令
                if INTERACTIVE_LANG_MENU_AVAILABLE:
                    try:
                        show_language_menu(save_to_env=True)
                        console.print(safe_t('common.message', fallback='[dim]💡 語言設定已更新,新訊息將使用選擇的語言[/dim]\n'))
                    except Exception as e:
                        console.print(safe_t('error.failed', fallback='[red]❌ 語言切換失敗: {e}[/red]', e=e))

                        # 智能錯誤診斷
                        if error_diagnostics:
                            error_msg, solutions = error_diagnostics.diagnose_and_suggest(
                                error=e,
                                operation="/lang 指令",
                                context={'command': 'lang', 'error_type': type(e).__name__}
                            )

                            if solutions:
                                console.print(f"\n[yellow]💡 建議的解決方案：[/yellow]")
                                for i, sol in enumerate(solutions, 1):
                                    console.print(f"\n[cyan]{i}. {sol.title}[/cyan]")
                                    console.print(f"   {sol.description}")
                                    if sol.command:
                                        console.print(f"   [green]執行：[/green] {sol.command}")
                                    if sol.manual_steps:
                                        console.print(f"   [yellow]手動步驟：[/yellow]")
                                        for step in sol.manual_steps:
                                            console.print(f"     {step}")
                else:
                    console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  互動式語言選單不可用[/#E8C4F0]'))
                    console.print(safe_t('common.message', fallback='[#87CEEB]💡 請使用: python3 gemini_lang.py --set <語言代碼>[/#87CEEB]'))
                    console.print(safe_t('common.message', fallback='[dim]   可用語言: zh-TW, en, ja, ko[/dim]\n'))
                continue

            elif user_input.lower() == 'help':
                # 顯示主幫助選單（循環式）
                while True:
                    print("\n" + "=" * 60)
                    print(safe_t('chat.help.title', fallback='📖 ChatGemini 幫助系統'))
                    print("=" * 60)
                    print(safe_t('chat.help.select_topic', fallback='選擇主題：'))
                    print(safe_t('chat.help.option_quick_start', fallback='  [1] 快速入門'))
                    print(safe_t('chat.help.option_thinking', fallback='  [2] 思考模式控制'))
                    print(safe_t('chat.help.option_files', fallback='  [3] 檔案附加功能'))
                    print(safe_t('chat.help.option_cache', fallback='  [4] 自動快取管理'))
                    print(safe_t('chat.help.option_video', fallback='  [5] 影音檔案處理'))
                    if CODEGEMINI_ENABLED:
                        print(safe_t('chat.help.option_cli', fallback='  [6] Gemini CLI 管理'))
                        print(safe_t('chat.help.option_commands', fallback='  [7] 指令列表'))
                        max_choice = 7
                    else:
                        print(safe_t("chat.help.menu.commands_list", fallback="  [6] 指令列表"))
                        max_choice = 6
                    print(safe_t('chat.help.option_return', fallback='  [0] 返回'))
                    print("-" * 60)

                    help_choice = Prompt.ask(safe_t("chat.help.choose_topic", fallback="請選擇 (0-{max}): ").format(max=max_choice))

                    # 返回對話
                    if help_choice == '0' or help_choice.lower() in ['exit', 'quit', 'q']:
                        break

                    if help_choice == '1':
                        # 快速入門
                        print("\n" + "=" * 60)
                        print(safe_t('chat.help.quick_start_title', fallback='🚀 快速入門'))
                        print("=" * 60)
                        print(safe_t('chat.help.quick_start_intro', fallback='ChatGemini 是一個強大的 Gemini API 對話工具\n'))
                        print(safe_t('chat.help.basic_usage', fallback='基本使用：'))
                        print(safe_t('chat.help.basic_usage_1', fallback='  直接輸入問題即可對話'))
                        print(safe_t('chat.help.basic_usage_2', fallback='  輸入 \'help\' 查看更多幫助\n'))
                        print(safe_t('chat.help.features', fallback='特色功能：'))
                        print(safe_t('chat.help.feature_thinking', fallback='  • 思考模式：讓 AI 深入思考後回答'))
                        print(safe_t('chat.help.feature_files', fallback='  • 檔案附加：分析程式碼、圖片、影片'))
                        print(safe_t('chat.help.feature_cache', fallback='  • 自動快取：節省 75-90% API 成本'))
                        print(safe_t('chat.help.feature_pricing', fallback='  • 新台幣計價：即時顯示花費\n'))
                        print(safe_t('chat.help.examples', fallback='範例：'))
                        print(safe_t('chat.help.example_1', fallback='  你: [think:5000] 解釋量子計算原理'))
                        print(safe_t('chat.help.example_2', fallback='  你: @code.py 這段程式碼有什麼問題？'))
                        print(safe_t('chat.help.example_3', fallback='  你: 附加 image.jpg 描述這張圖片'))
                        print("=" * 60)
                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif help_choice == '2':
                        # 思考模式
                        print("\n" + "=" * 60)
                        print(safe_t('chat.help.thinking_title', fallback='🧠 思考模式與輸出控制'))
                        print("=" * 60)
                        print(safe_t('chat.help.thinking_intro', fallback='讓 Gemini 2.5 模型先思考再回答,提升回答品質\n'))
                        print(safe_t('chat.help.syntax', fallback='語法：'))
                        print(safe_t('chat.help.thinking_syntax_1', fallback='  [think:2000] - 使用 2000 tokens 思考預算（含動態計價範圍）'))
                        print(safe_t('chat.help.thinking_syntax_2', fallback='  [think:auto] - 動態思考（預設）'))
                        print(safe_t('chat.help.thinking_syntax_3', fallback='  [no-think]   - 不使用思考模式'))
                        print(safe_t('chat.help.output_syntax', fallback='  [max_token:500] - 最大回應量 500 tokens (1-8192,含動態計價範圍)\n'))
                        print(safe_t('chat.help.applicable_models', fallback='適用模型：'))
                        print("  • gemini-2.5-pro")
                        print("  • gemini-2.5-flash")
                        print("  • gemini-2.5-flash-lite\n")
                        print(safe_t('chat.help.usage_examples', fallback='使用範例：'))
                        print(safe_t('chat.help.thinking_example_1', fallback='  你: [think:5000] 深入分析這個演算法的時間複雜度'))
                        print(safe_t('chat.help.thinking_example_2', fallback='  你: [no-think] 1+1=?'))
                        print(safe_t('chat.help.thinking_example_3', fallback='  你: [think:auto] 解釋相對論（讓 AI 自行決定）'))
                        print(safe_t('chat.help.output_example', fallback='  你: [max_token:200] 用一句話總結量子計算\n'))
                        print(safe_t('chat.help.cost', fallback='成本（動態計價範圍）：'))
                        print(safe_t('chat.help.thinking_cost_1', fallback='  思考與輸出均顯示 50%-100% 使用率成本範圍'))
                        print(safe_t('chat.help.thinking_cost_2', fallback='  範例：[think:2000] 顯示 NT$ 0.03~0.06'))
                        print("=" * 60)
                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif help_choice == '3':
                        # 檔案附加
                        print("\n" + "=" * 60)
                        print(safe_t('chat.help.files_title', fallback='📎 檔案附加功能'))
                        print("=" * 60)
                        print(safe_t('chat.help.files_intro', fallback='在對話中附加檔案,讓 AI 分析內容\n'))
                        print(safe_t('chat.help.files_syntax', fallback='語法（4 種）：'))
                        print(safe_t('chat.help.files_syntax_1', fallback='  @file.txt       - 最簡短'))
                        print(safe_t('chat.help.files_syntax_2', fallback='  讀取 code.py    - 中文語法'))
                        print(safe_t('chat.help.files_syntax_3', fallback='  附加 image.jpg  - 附加媒體'))
                        print(safe_t('chat.help.files_syntax_4', fallback='  上傳 video.mp4  - 明確上傳\n'))
                        print(safe_t('chat.help.smart_detection', fallback='智慧判斷：'))
                        print(safe_t('chat.help.text_file_handling', fallback='  文字檔（30+ 格式）→ 直接讀取嵌入 prompt'))
                        print(safe_t('chat.help.text_file_formats', fallback='    .txt .py .js .ts .json .xml .html .css .md ...'))
                        print(safe_t('chat.help.media_file_handling', fallback='  媒體檔 → 上傳到 Gemini API'))
                        print(safe_t('chat.help.media_file_formats', fallback='    .jpg .png .mp4 .mp3 .pdf .doc ...\n'))
                        print(safe_t('chat.help.usage_examples', fallback='使用範例：'))
                        print(safe_t('chat.help.file_example_1', fallback='  你: @main.py 解釋這個程式'))
                        print(safe_t('chat.help.file_example_2', fallback='  你: 讀取 config.json 檢查設定'))
                        print(safe_t('chat.help.file_example_3', fallback='  你: 附加 screenshot.png 這個錯誤是什麼？'))
                        print(safe_t('chat.help.file_example_4', fallback='  你: 上傳 demo.mp4 總結影片內容\n'))
                        print(safe_t('chat.help.combined_usage', fallback='組合使用：'))
                        print(safe_t('chat.help.combined_example', fallback='  你: 讀取 error.log 附加 screenshot.png 診斷問題'))
                        print("=" * 60)
                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif help_choice == '4':
                        # 自動快取
                        print("\n" + "=" * 60)
                        print(safe_t('chat.help.cache_title', fallback='💾 自動快取管理'))
                        print("=" * 60)
                        print(safe_t('chat.help.cache_auto_create', fallback='自動建立快取,節省 75-90% API 成本\n'))
                        print(safe_t('chat.help.startup_config', fallback='啟動時配置：'))
                        print(safe_t('chat.help.startup_quick', fallback='  [y] 快速模式 - 5000 tokens 自動建立'))
                        print(safe_t('chat.help.startup_advanced', fallback='  [c] 進階模式 - 自訂門檻、模式、TTL'))
                        print(safe_t('chat.help.startup_disable', fallback='  [n] 關閉自動快取\n'))
                        print(safe_t('chat.help.realtime_control', fallback='即時控制：'))
                        print(safe_t('chat.help.cache_now', fallback='  [cache:now]  - 立即建立快取'))
                        print(safe_t('chat.help.cache_off', fallback='  [cache:off]  - 暫停自動快取'))
                        print(safe_t('chat.help.cache_on', fallback='  [cache:on]   - 恢復自動快取'))
                        print(safe_t('chat.help.no_cache', fallback='  [no-cache]   - 本次對話不列入快取\n'))
                        print(safe_t('chat.help.use_cases', fallback='使用場景：'))
                        print(safe_t('chat.help.usecase_code', fallback='  1. 程式碼分析：'))
                        print(safe_t('chat.help.usecase_code_1', fallback='     你: 讀取 main.py'))
                        print(safe_t('chat.help.usecase_code_2', fallback='     你: [cache:now]  ← 鎖定程式碼上下文'))
                        print(safe_t('chat.help.usecase_code_3', fallback='     你: [後續可多次詢問,省 90% 成本]'))
                        print()
                        print(safe_t('chat.help.usecase_doc', fallback='  2. 文檔問答：'))
                        print(safe_t('chat.help.usecase_doc_1', fallback='     你: 讀取 spec.md'))
                        print(safe_t('chat.help.usecase_doc_2', fallback='     [自動達到 5000 tokens 後建立快取]'))
                        print(safe_t('chat.help.usecase_doc_3', fallback='     你: [後續問題使用快取]'))
                        print()
                        print(safe_t('chat.help.cost_example', fallback='成本範例：'))
                        print(safe_t('chat.help.cost_without_cache', fallback='  不使用快取：每次 5000 tokens → NT$ 0.16'))
                        print(safe_t('chat.help.cost_with_cache', fallback='  使用快取：每次 5000 tokens → NT$ 0.016（省 90%）'))
                        print("=" * 60)
                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif help_choice == '5':
                        # 影音處理
                        print("\n" + "=" * 60)
                        print(safe_t('chat.help.video_title', fallback='🎬 影音檔案處理'))
                        print("=" * 60)
                        print(safe_t('chat.help.media_intro', fallback='上傳圖片、影片、音訊讓 AI 分析\n'))
                        print(safe_t('chat.help.how_it_works', fallback='運作方式：'))
                        print(safe_t('chat.help.upload_step_1', fallback='  1. 上傳到 Gemini 伺服器（48 小時有效）'))
                        print(safe_t('chat.help.upload_step_2', fallback='  2. 自動檢查已上傳檔案（避免重複）'))
                        print(safe_t('chat.help.upload_step_3', fallback='  3. 影片/音訊自動等待轉碼完成\n'))
                        print(safe_t('chat.help.file_limits', fallback='檔案限制：'))
                        print(safe_t('chat.help.limit_image_20mb', fallback='  圖片：20 MB'))
                        print(safe_t('chat.help.limit_video_2gb', fallback='  影片：2 GB'))
                        print(safe_t('chat.help.limit_audio_2gb', fallback='  音訊：2 GB\n'))
                        print(safe_t('chat.help.token_consumption', fallback='Token 消耗：'))
                        print(safe_t('chat.help.tokens_image', fallback='  圖片：258 tokens（固定）'))
                        print(safe_t('chat.help.tokens_video', fallback='  影片：258 tokens/秒（1 分鐘 ≈ 15,480 tokens）'))
                        print(safe_t('chat.help.tokens_audio', fallback='  音訊：32 tokens/秒（1 分鐘 ≈ 1,920 tokens）\n'))
                        print(safe_t('chat.help.multi_turn_important', fallback='多輪對話（重要！）：'))
                        print(safe_t('chat.help.wrong_way', fallback='  ❌ 錯誤：'))
                        print(safe_t('chat.help.correct_example_1', fallback='     你: 附加 image.jpg 描述圖片'))
                        print(safe_t('chat.help.wrong_example_2', fallback='     你: 圖中的人穿什麼？← AI 看不到圖片'))
                        print()
                        print(safe_t('chat.help.correct_way', fallback='  ✅ 正確：'))
                        print(safe_t('chat.help.correct_example_1', fallback='     你: 附加 image.jpg 描述圖片'))
                        print(safe_t('chat.help.correct_example_2', fallback='     你: [cache:now]  ← 建立快取鎖定圖片'))
                        print(safe_t('chat.help.correct_example_3', fallback='     你: 圖中的人穿什麼？← AI 可以回答'))
                        print()
                        print(safe_t('chat.help.usage_examples', fallback='使用範例：'))
                        print(safe_t('chat.help.media_example', fallback='  你: 附加 meeting.mp4 總結會議重點'))
                        print(safe_t("chat.help.gemini_cli.example_upload", fallback="  你: 上傳 photo1.jpg 附加 photo2.jpg 比較差異"))
                        print("=" * 60)
                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif help_choice == '6':
                        # Gemini CLI 管理
                        print("\n" + "=" * 60)
                        print(safe_t("chat.help.gemini_cli.title", fallback="🛠️  Gemini CLI 管理"))
                        print("=" * 60)
                        print(safe_t("chat.help.gemini_cli.description", fallback="管理 Google Gemini Code Assist CLI 工具\n"))
                        print(safe_t('chat.help.cache_features', fallback='功能：'))
                        print(safe_t("chat.help.gemini_cli.feature_check_status", fallback="  • 檢查 Gemini CLI 安裝狀態"))
                        print(safe_t("chat.help.gemini_cli.feature_start_session", fallback="  • 啟動 Gemini CLI session（帶上下文）"))
                        print(safe_t("chat.help.gemini_cli.feature_checkpoints", fallback="  • 管理 checkpoints（儲存/載入對話狀態）"))
                        print(safe_t("chat.help.gemini_cli.feature_install", fallback="  • 安裝/更新/卸載 Gemini CLI"))
                        print(safe_t("chat.help.gemini_cli.feature_api_key", fallback="  • 配置 API Key\n"))
                        print(safe_t("chat.help.gemini_cli.usage_start", fallback="啟動："))
                        print(safe_t("chat.help.gemini_cli.usage_command", fallback="  輸入 'cli' 或 'gemini-cli'\n"))
                        print(safe_t("chat.help.gemini_cli.purpose", fallback="用途："))
                        print(safe_t("chat.help.gemini_cli.purpose_code_assist", fallback="  • Gemini CLI 提供程式碼輔助功能"))
                        print(safe_t("chat.help.gemini_cli.purpose_multi_file", fallback="  • 支援多檔案編輯、程式碼生成"))
                        print(safe_t("chat.help.gemini_cli.purpose_complement", fallback="  • 與 ChatGemini 互補使用\n"))
                        print(safe_t('chat.help.examples', fallback='範例：'))
                        print(safe_t("chat.help.gemini_cli.example_start", fallback="  你: cli"))
                        print(safe_t("chat.help.gemini_cli.example_status", fallback="  選擇 [1] 顯示狀態"))
                        print(safe_t("chat.help.gemini_cli.example_session", fallback="  選擇 [2] 啟動 CLI session"))
                        print("=" * 60)
                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif help_choice == ('6' if not CODEGEMINI_ENABLED else '7'):
                        # 指令列表（動態產生）
                        print("\n" + "=" * 60)
                        print(safe_t("chat.help.commands.title", fallback="📋 指令列表"))
                        print("=" * 60)
                        print(safe_t("chat.help.commands.basic", fallback="基本指令："))
                        print(safe_t("chat.help.commands.help", fallback="  help        - 顯示幫助系統"))
                        print(safe_t("chat.help.commands.lang", fallback="  lang        - 切換語言（zh-TW/en/ja/ko）🆕"))
                        print(safe_t("chat.help.commands.cache", fallback="  cache       - 快取管理選單"))
                        print(safe_t("chat.help.commands.media", fallback="  media       - 影音功能選單（Flow/Veo/分析/處理）"))
                        if CODEGEMINI_ENABLED:
                            print(safe_t("chat.help.commands.cli", fallback="  cli         - Gemini CLI 管理工具"))
                        print(safe_t("chat.help.commands.model", fallback="  model       - 切換模型"))
                        print(safe_t("chat.help.commands.model_list", fallback="  /model      - 查看所有可用模型（含分類）"))
                        print(safe_t("chat.help.commands.model_update", fallback="  /model update - 從 API 更新模型列表"))
                        print(safe_t("chat.help.commands.budget", fallback="  /budget     - 查看預算使用狀態"))
                        print(safe_t("chat.help.commands.clear", fallback="  clear       - 清除對話歷史"))
                        print(safe_t("chat.help.commands.exit", fallback="  exit/quit   - 退出程式"))
                        print()
                        print(safe_t("chat.help.commands.thinking_mode", fallback="思考模式："))
                        print(safe_t("chat.help.commands.think_auto", fallback="  [think:-1] 或 [think:auto] - 動態思考（所有模型,推薦）"))
                        print(safe_t("chat.help.commands.think_budget", fallback="  [think:數字] - 指定思考預算（依模型而異）"))
                        print("                 • Pro: 128-32,768 tokens")
                        print("                 • Flash: 1-24,576 tokens")
                        print("                 • Flash Lite: 512-24,576 tokens")
                        print(safe_t("chat.help.commands.think_off", fallback="  [no-think] 或 [think:0] - 停用思考（僅 Flash/Flash Lite）"))
                        print()
                        print(safe_t("chat.help.commands.output_control", fallback="輸出長度控制（含動態計價）："))
                        print(safe_t("chat.help.commands.output_limit", fallback="  [max_token:數字] - 最大回應量 (1-8192 tokens)"))
                        print(safe_t("chat.help.commands.output_example", fallback="  範例：[max_token:200] 用一句話回答"))
                        print()
                        print(safe_t("chat.help.commands.file_attach", fallback="檔案附加："))
                        print(safe_t("chat.help.commands.file_at", fallback="  @檔案路徑    - 附加檔案"))
                        print(safe_t("chat.help.commands.file_read", fallback="  讀取 檔案    - 讀取檔案"))
                        print(safe_t("chat.help.commands.file_attach_cmd", fallback="  附加 檔案    - 附加檔案"))
                        print(safe_t("chat.help.commands.file_upload", fallback="  上傳 檔案    - 上傳媒體"))
                        print()
                        print(safe_t("chat.help.commands.cache_control", fallback="快取控制："))
                        print(safe_t("chat.help.commands.cache_now", fallback="  [cache:now]  - 立即建立"))
                        print(safe_t("chat.help.commands.cache_off", fallback="  [cache:off]  - 暫停自動"))
                        print(safe_t("chat.help.commands.cache_on", fallback="  [cache:on]   - 恢復自動"))
                        print(safe_t("chat.help.commands.no_cache", fallback="  [no-cache]   - 排除本次"))
                        print("=" * 60)
                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                continue

            elif user_input.lower() == 'model':
                return 'switch_model'

            elif user_input.lower() == 'clear':
                # 🔧 F-2 修復：實際清空對話歷史記憶體快取
                stats = chat_logger.conversation_manager.get_stats()

                console.print(safe_t('common.message', fallback='\n[#B565D8]📊 對話狀態[/#B565D8]'))
                console.print(safe_t('common.message', fallback='   記憶體快取：{active_messages} 條', active_messages=stats['active_messages']))
                console.print(safe_t('common.message', fallback='   [dim]硬碟已存檔：{archived_messages} 條[/dim]\n', archived_messages=stats['archived_messages']))

                if Confirm.ask(
                    safe_t('chat.clear_memory_confirm_title', fallback='[#B565D8]清空記憶體快取嗎？[/#B565D8]') + '\n' +
                    safe_t('chat.clear_memory_confirm_desc1', fallback='[dim]· 只清除 RAM 中的對話（釋放記憶體）') + '\n' +
                    safe_t('chat.clear_memory_confirm_desc2', fallback='· 硬碟儲存的對話記錄不受影響[/dim]'),
                    default=False
                ):
                    chat_logger.conversation_manager.clear()
                    console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 記憶體已清空[/#B565D8]'))
                    console.print(safe_t("chat.archive.disk_kept", fallback="[dim]  硬碟對話記錄：{archive_file} 保留[/dim]").format(
                        archive_file=stats['archive_file']
                    ))
                else:
                    console.print(safe_t('common.message', fallback='\n[dim]已取消[/dim]'))

                continue

            elif user_input.lower() == 'upgrade':
                # 執行系統更新
                try:
                    from gemini_upgrade import upgrade_interactive
                    console.print()
                    success = upgrade_interactive()
                    if success:
                        console.print(safe_t('common.message', fallback='\n[#B565D8]💡 請重新啟動程式以使用新版本[/#B565D8]\n'))
                    console.print()
                except ImportError:
                    console.print(safe_t('error.failed', fallback='[red]✗ 更新模組未安裝[/red]\n', e='ImportError'))
                except Exception as e:
                    console.print(safe_t('error.failed', fallback='[red]✗ 更新失敗: {e}[/red]\n', e=e))

                    # 智能錯誤診斷
                    if error_diagnostics:
                        error_msg, solutions = error_diagnostics.diagnose_and_suggest(
                            error=e,
                            operation="/upgrade 指令",
                            context={'command': 'upgrade', 'error_type': type(e).__name__}
                        )

                        if solutions:
                            console.print(f"\n[yellow]💡 建議的解決方案：[/yellow]")
                            for i, sol in enumerate(solutions, 1):
                                console.print(f"\n[cyan]{i}. {sol.title}[/cyan]")
                                console.print(f"   {sol.description}")
                                if sol.command:
                                    console.print(f"   [green]執行：[/green] {sol.command}")
                                if sol.manual_steps:
                                    console.print(f"   [yellow]手動步驟：[/yellow]")
                                    for step in sol.manual_steps:
                                        console.print(f"     {step}")
                continue

            elif user_input.lower() == '/clear-memory':
                # 手動清理記憶體（調用新的處理函數）
                return handle_clear_memory_command(chat_logger)

            elif user_input.lower() == '/memory-stats':
                # 顯示記憶體統計（調用新的處理函數）
                return handle_memory_stats_command(chat_logger)

            elif user_input.lower() == '/help-memory':
                # 顯示記憶體管理說明（調用新的處理函數）
                return handle_memory_help_command()

            elif user_input.lower() == '/checkpoints':
                # 列出所有檢查點
                return handle_checkpoints_command()

            elif user_input.lower().startswith('/rewind'):
                # 回溯至檢查點
                parts = user_input.split(maxsplit=1)
                checkpoint_id = parts[1] if len(parts) > 1 else ""
                return handle_rewind_command(checkpoint_id)

            elif user_input.lower().startswith('/checkpoint'):
                # 建立手動檢查點
                parts = user_input.split(maxsplit=1)
                description = parts[1] if len(parts) > 1 else ""
                return handle_checkpoint_command(description)

            elif user_input.lower() == '/help-checkpoint':
                # 顯示檢查點系統說明
                return handle_checkpoint_help_command()

            # ==========================================
            # 對話歷史管理指令
            # ==========================================
            elif user_input.lower().startswith('/search ') and HISTORY_MANAGER_AVAILABLE:
                # 搜尋對話歷史
                keyword = user_input[8:].strip()
                if not keyword:
                    console.print(safe_t('history.search_no_results', fallback='[yellow]請輸入搜尋關鍵字[/yellow]'))
                    continue

                console.print(safe_t('history.search_keyword', fallback=f'\n🔍 搜尋關鍵字: {keyword}\n'))
                results = history_manager.search(keyword, limit=20)

                if not results:
                    console.print(safe_t('history.search_no_results', fallback='[dim]未找到相關對話[/dim]\n'))
                else:
                    from rich.table import Table
                    table = Table(title=safe_t('history.search_title', fallback='搜尋結果'))
                    table.add_column(safe_t('history.timestamp', fallback='時間'), style="cyan")
                    table.add_column(safe_t('common.role', fallback='角色'), style="magenta")
                    table.add_column(safe_t('history.preview', fallback='內容預覽'), style="white")

                    for r in results:
                        role_emoji = {'user': '👤', 'assistant': '🤖', 'system': '⚙️'}.get(r['role'], '❓')
                        table.add_row(
                            r['timestamp'],
                            f"{role_emoji} {r['role']}",
                            r['content']
                        )

                    console.print(table)
                    console.print(safe_t("chat.cache.search_results", fallback="\n[dim]找到 {count} 筆結果[/dim]\n").format(count=len(results)))
                continue

            elif user_input.lower() == '/history' and HISTORY_MANAGER_AVAILABLE:
                # 列出最近對話
                conversations = history_manager.list_conversations(limit=10)

                if not conversations:
                    console.print(safe_t('history.list_empty', fallback='[dim]目前沒有對話記錄[/dim]\n'))
                else:
                    console.print(safe_t('history.list_title', fallback=f'\n📋 最近 {len(conversations)} 個對話\n'))

                    for i, conv in enumerate(conversations, 1):
                        console.print(Panel(
                            f"📅 {conv['date']}\n"
                            f"💬 {safe_t('history.message_count', fallback='{count} 則訊息', count=conv['message_count'])}\n"
                            f"📦 {conv['size']} bytes\n"
                            f"📁 {conv['file']}",
                            title=f"[bright_magenta]對話 #{i}[/bright_magenta]",
                            border_style="bright_magenta"
                        ))
                continue

            elif user_input.lower().startswith('/export') and HISTORY_MANAGER_AVAILABLE:
                # 匯出對話記錄
                parts = user_input.split()
                if len(parts) < 2:
                    console.print(safe_t('history.export_failed', fallback='[yellow]用法: /export <路徑> [json|markdown][/yellow]', error='缺少路徑'))
                    continue

                output_path = parts[1]
                format = parts[2] if len(parts) > 2 else 'json'

                console.print(safe_t('common.processing', fallback=f'\n正在匯出對話記錄...'))
                success, message = history_manager.export(output_path, format=format)

                if success:
                    console.print(safe_t('history.export_success', fallback='[green]✓ {message}[/green]', path=output_path, message=message))
                else:
                    console.print(safe_t('history.export_failed', fallback='[red]✗ {error}[/red]', error=message))
                continue

            elif user_input.lower() == '/stats' and HISTORY_MANAGER_AVAILABLE:
                # 顯示統計資訊
                stats = history_manager.get_statistics()

                console.print(safe_t('history.statistics', fallback='\n📊 統計資訊\n'))
                console.print(Panel(
                    f"{safe_t('history.total_conversations', fallback='對話總數')}: {stats['total_conversations']}\n"
                    f"{safe_t('history.total_messages', fallback='訊息總數')}: {stats['total_messages']}\n"
                    f"{safe_t('history.total_size', fallback='總大小')}: {stats['total_size']:,} bytes\n"
                    f"{safe_t('history.date_range', fallback='日期範圍')}: {stats['date_range'][0]} ~ {stats['date_range'][1]}\n"
                    f"{safe_t('history.role_distribution', fallback='角色分布')}: {dict(stats['role_distribution'])}",
                    title="[bright_magenta]統計資訊[/bright_magenta]",
                    border_style="bright_magenta"
                ))
                continue

            elif user_input.lower() == '/budget':
                # 顯示預算使用狀態
                if PRICING_ENABLED:
                    status = global_pricing_calculator.get_budget_status()

                    if not status['enabled']:
                        console.print(safe_t('common.message', fallback="⚠️ 預算控制未啟用"))
                        continue

                    console.print("\n" + "="*60)
                    console.print(safe_t('common.message', fallback='💰 預算使用摘要'))
                    console.print("="*60)

                    # 每日預算
                    console.print(safe_t('common.message', fallback=f"\n📅 今日使用：${status['daily_cost']:.4f} / ${status['daily_limit']:.2f}"))
                    console.print(safe_t('common.message', fallback=f"   剩餘：${status['daily_remaining']:.4f}"))
                    console.print(safe_t('common.message', fallback=f"   使用率：{status['daily_usage_percent']:.1f}%"))

                    # 進度條
                    bar_length = 40
                    filled = int(bar_length * status['daily_usage_percent'] / 100)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    console.print(safe_t('common.message', fallback=f"   [{bar}]"))

                    # 每月預算
                    console.print(safe_t('common.message', fallback=f"\n📆 本月使用：${status['monthly_cost']:.4f} / ${status['monthly_limit']:.2f}"))
                    console.print(safe_t('common.message', fallback=f"   剩餘：${status['monthly_remaining']:.4f}"))
                    console.print(safe_t('common.message', fallback=f"   使用率：{status['monthly_usage_percent']:.1f}%"))

                    # 月度進度條
                    filled_monthly = int(bar_length * status['monthly_usage_percent'] / 100)
                    bar_monthly = "█" * filled_monthly + "░" * (bar_length - filled_monthly)
                    console.print(safe_t('common.message', fallback=f"   [{bar_monthly}]"))

                    console.print("="*60)
                else:
                    console.print(safe_t('common.message', fallback="⚠️ 計價模組未啟用"))
                continue

            elif user_input.lower() == '/model':
                # 顯示所有可用模型
                try:
                    from gemini_model_list import GeminiModelList
                    from rich.console import Console
                    from rich.table import Table
                    from rich.panel import Panel
                    from rich.pager import Pager
                    import io

                    # 創建模型列表管理器
                    model_manager = GeminiModelList()

                    # 創建輸出緩衝區
                    output_buffer = io.StringIO()
                    temp_console = Console(file=output_buffer, force_terminal=True, width=100)

                    # 標題
                    temp_console.print("\n")
                    temp_console.print(Panel.fit(
                        "[bold #E8C4F0]🤖 所有可用的 Gemini 模型[/bold #E8C4F0]",
                        border_style="#E8C4F0"
                    ))
                    temp_console.print()

                    # 獲取所有模型並分類
                    all_models = model_manager.get_all_models()

                    # 分類模型
                    gemini_25 = [m for m in all_models if m.startswith('gemini-2.5')]
                    gemini_20 = [m for m in all_models if m.startswith('gemini-2.0')]
                    gemini_15 = [m for m in all_models if m.startswith('gemini-1.5') or 'er-1.5' in m]
                    experimental = [m for m in all_models if 'exp' in m and m not in gemini_20]
                    other = [m for m in all_models if m not in gemini_25 + gemini_20 + gemini_15 + experimental]

                    categories = [
                        ("🌟 Gemini 2.5 系列（推薦）", gemini_25, "#B565D8"),
                        ("⚡ Gemini 2.0 系列", gemini_20, "#E8C4F0"),
                        ("🔧 Gemini 1.5 系列", gemini_15, "#DDA0DD"),
                        ("🧪 實驗版", experimental, "#BA55D3"),
                        ("📦 其他版本", other, "#9370DB"),
                    ]

                    for title, models, color in categories:
                        if not models:
                            continue

                        temp_console.print(f"[bold {color}]{title}[/bold {color}]")
                        temp_console.print(f"[dim]總共 {len(models)} 個模型[/dim]\n")

                        # 創建表格
                        table = Table(show_header=True, header_style=f"bold {color}", border_style=color, box=None)
                        table.add_column("#", style=color, width=4, justify="right")
                        table.add_column("模型名稱", style="white", no_wrap=False)
                        table.add_column("類型", style=color, width=15)

                        for idx, model in enumerate(models, 1):
                            # 判斷模型類型
                            if 'flash' in model.lower():
                                model_type = "⚡ Flash"
                            elif 'pro' in model.lower():
                                model_type = "💎 Pro"
                            elif 'lite' in model.lower():
                                model_type = "🪶 Lite"
                            elif 'exp' in model.lower():
                                model_type = "🧪 實驗"
                            else:
                                model_type = "📦 標準"

                            table.add_row(str(idx), model, model_type)

                        temp_console.print(table)
                        temp_console.print()

                    # 顯示快取資訊
                    cache_info = model_manager.get_cache_info()
                    temp_console.print("[dim]─[/dim]" * 50)
                    if cache_info['exists']:
                        temp_console.print(f"[dim]ℹ️  快取資訊：上次更新 {cache_info['last_update']},共 {cache_info['count']} 個模型[/dim]")
                    temp_console.print(f"[dim]💡 使用 '/model update' 強制更新模型列表[/dim]")
                    temp_console.print()

                    # 獲取輸出內容
                    output_content = output_buffer.getvalue()

                    # 使用 Rich Pager 顯示（支援翻頁）
                    with Pager(styles=True):
                        console.print(output_content, end="")

                    # 顯示返回提示
                    console.print()
                    input(safe_t("chat.common.press_enter", fallback="按 Enter 返回選單..."))

                except ImportError as e:
                    console.print(f"[#B565D8]⚠️ 無法載入模型列表管理器：{e}[/#B565D8]")
                except Exception as e:
                    console.print(f"[#B565D8]⚠️ 顯示模型列表時發生錯誤：{e}[/#B565D8]")
                continue

            elif user_input.lower() == '/model update':
                # 強制更新模型列表
                try:
                    from gemini_model_list import GeminiModelList
                    console.print("[#E8C4F0]🔄 正在從 API 更新模型列表...[/#E8C4F0]")

                    model_manager = GeminiModelList()
                    success = model_manager.update_models(force=True)

                    if success:
                        cache_info = model_manager.get_cache_info()
                        console.print(f"[#B565D8]✅ 模型列表已更新！共 {cache_info['count']} 個模型[/#B565D8]")
                    else:
                        console.print("[#B565D8]❌ 更新失敗,請檢查網路連線和 API 金鑰[/#B565D8]")

                except Exception as e:
                    console.print(f"[#B565D8]⚠️ 更新模型列表時發生錯誤：{e}[/#B565D8]")

                    # 智能錯誤診斷
                    if error_diagnostics:
                        error_msg, solutions = error_diagnostics.diagnose_and_suggest(
                            error=e,
                            operation="/model update 指令",
                            context={'command': 'model_update', 'error_type': type(e).__name__, 'involves_api': True}
                        )

                        if solutions:
                            console.print(f"\n[yellow]💡 建議的解決方案：[/yellow]")
                            for i, sol in enumerate(solutions, 1):
                                console.print(f"\n[cyan]{i}. {sol.title}[/cyan]")
                                console.print(f"   {sol.description}")
                                if sol.command:
                                    console.print(f"   [green]執行：[/green] {sol.command}")
                                if sol.manual_steps:
                                    console.print(f"   [yellow]手動步驟：[/yellow]")
                                    for step in sol.manual_steps:
                                        console.print(f"     {step}")
                continue

            elif user_input.lower() == 'cache':
                if not CACHE_ENABLED:
                    console.print(safe_t('common.message', fallback='[#E8C4F0]快取功能未啟用（gemini_cache_manager.py 未找到）[/#E8C4F0]'))
                    continue

                console.print(safe_t('common.message', fallback='\n[#B565D8]💾 快取與思考管理[/#B565D8]\n'))
                console.print(safe_t('common.message', fallback='優化成本與效能的關鍵設定！\n'))
                console.print(safe_t('common.message', fallback='指令：'))
                console.print(safe_t('common.message', fallback='  [快取管理]'))
                console.print(safe_t('common.message', fallback='  1. 列出所有快取'))
                console.print(safe_t('common.message', fallback='  2. 建立新快取'))
                console.print(safe_t('common.message', fallback='  3. 刪除快取'))

                # 只在支援思考模式的模型顯示
                if any(tm in model_name for tm in THINKING_MODELS):
                    console.print(safe_t('common.message', fallback='\n  [思考模式配置]'))
                    console.print(safe_t('common.message', fallback='  4. 設定預設思考模式'))
                    console.print(safe_t('common.message', fallback='  5. 查看思考費用試算'))

                    # 顯示翻譯功能選項
                    if TRANSLATOR_ENABLED:
                        trans_status = safe_t('chat.status_enabled', fallback='✅ 啟用') if global_translator.translation_enabled else safe_t('chat.status_disabled', fallback='❌ 停用')
                        console.print(safe_t('common.message', fallback='  6. 切換思考翻譯 (當前: {trans_status})', trans_status=trans_status))

                console.print(safe_t('common.message', fallback='\n  0. 返回\n'))

                cache_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇: "))

                if cache_choice == '1':
                    global_cache_manager.list_caches()
                elif cache_choice == '2':
                    console.print(safe_t('common.message', fallback='\n[#B565D8]建立快取（最低 token 需求：gemini-2.5-flash=1024, gemini-2.5-pro=4096）[/#B565D8]'))
                    content_input = Prompt.ask(safe_t("chat.cache.content_input_prompt", fallback="輸入要快取的內容（或檔案路徑）: "))
                    if os.path.isfile(content_input):
                        with open(content_input, 'r', encoding='utf-8') as f:
                            content = f.read()
                    else:
                        content = content_input

                    cache_name = Prompt.ask(safe_t("chat.cache.name_prompt", fallback="快取名稱（可選）: ")) or None
                    ttl_hours = Prompt.ask(safe_t("chat.cache.ttl_default_prompt", fallback="存活時間（小時,預設=1）: "))
                    ttl_hours = int(ttl_hours) if ttl_hours.isdigit() else 1

                    try:
                        global_cache_manager.create_cache(
                            model=model_name,
                            contents=[content],
                            display_name=cache_name,
                            ttl_hours=ttl_hours
                        )
                    except Exception as e:
                        console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]建立失敗：{e}[/red]', e=e))

                elif cache_choice == '3':
                    cache_id = Prompt.ask(safe_t("chat.cache.delete_prompt", fallback="輸入要刪除的快取名稱或 ID: "))
                    global_cache_manager.delete_cache(cache_id)

                elif cache_choice == '4' and any(tm in model_name for tm in THINKING_MODELS):
                    # 設定預設思考模式
                    console.print(safe_t('common.message', fallback='\n[#B565D8]🧠 思考模式配置[/#B565D8]\n'))
                    console.print(safe_t('common.message', fallback='當前模型：{model_name}', model_name=model_name))

                    # 根據模型決定範圍
                    is_pro = '2.5-pro' in model_name or '2.0-pro' in model_name
                    # 注意：保留 'flash-8b' 檢查以向下相容舊配置,但該模型實際上不存在於 API 中
                    is_lite = 'flash-8b' in model_name or 'lite' in model_name

                    if is_pro:
                        MAX_TOKENS = 32768
                        MIN_TOKENS = 128
                        ALLOW_DISABLE = False
                        console.print(safe_t('common.message', fallback='思考範圍：{MIN_TOKENS:,} - {MAX_TOKENS:,} tokens（無法停用）\n', MIN_TOKENS=MIN_TOKENS, MAX_TOKENS=MAX_TOKENS))
                    elif is_lite:
                        MAX_TOKENS = 24576
                        MIN_TOKENS = 512
                        ALLOW_DISABLE = True
                        console.print(safe_t('common.message', fallback='思考範圍：0 (停用) 或 {MIN_TOKENS:,} - {MAX_TOKENS:,} tokens\n', MIN_TOKENS=MIN_TOKENS, MAX_TOKENS=MAX_TOKENS))
                    else:  # flash
                        MAX_TOKENS = 24576
                        MIN_TOKENS = 0
                        ALLOW_DISABLE = True
                        console.print(safe_t('common.message', fallback='思考範圍：0 (停用) 或 1 - {MAX_TOKENS:,} tokens\n', MAX_TOKENS=MAX_TOKENS))

                    console.print(safe_t('common.message', fallback='選擇預設思考模式：'))
                    console.print(safe_t('common.message', fallback='  [1] 動態模式（推薦）- AI 自動決定思考量'))
                    console.print(safe_t('common.message', fallback='  [2] 輕度思考 (2,000 tokens)'))
                    console.print(safe_t('common.message', fallback='  [3] 中度思考 (5,000 tokens)'))
                    console.print(safe_t('common.message', fallback='  [4] 深度思考 (10,000 tokens)'))
                    console.print(safe_t('common.message', fallback='  [5] 極限思考 ({MAX_TOKENS:,} tokens)', MAX_TOKENS=MAX_TOKENS))
                    console.print(safe_t('common.message', fallback='  [6] 自訂 tokens'))
                    if ALLOW_DISABLE:
                        console.print(safe_t('common.message', fallback='  [7] 停用思考 (0 tokens)'))
                    console.print(safe_t('common.message', fallback='  [0] 返回上一頁\n'))

                    think_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇: "))

                    if think_choice == '0':
                        # 返回上一頁,不設定思考模式
                        console.print(safe_t('common.message', fallback='[#B565D8]✓ 已取消設定[/#B565D8]'))
                    elif think_choice == '1':
                        console.print(safe_t('common.completed', fallback='\n✓ 已設定為動態模式'))
                        console.print(safe_t('common.message', fallback='💡 提示：每次對話可用 [think:auto] 覆蓋'))
                    elif think_choice in ['2', '3', '4', '5', '6', '7']:
                        budget_map = {'2': 2000, '3': 5000, '4': 10000, '5': MAX_TOKENS, '7': 0}
                        if think_choice == '6':
                            custom = Prompt.ask(safe_t("chat.thinking.custom_tokens_prompt", fallback="請輸入思考 tokens ({min}-{max}): ").format(min=MIN_TOKENS, max=MAX_TOKENS))
                            if custom.isdigit():
                                budget = max(MIN_TOKENS, min(int(custom), MAX_TOKENS))
                            else:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]無效輸入,使用預設 5000[/#E8C4F0]'))
                                budget = 5000
                        elif think_choice == '7':
                            if ALLOW_DISABLE:
                                budget = 0
                            else:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]{model_name} 無法停用思考,使用最小值 {MIN_TOKENS}[/#E8C4F0]', model_name=model_name, MIN_TOKENS=MIN_TOKENS))
                                budget = MIN_TOKENS
                        else:
                            budget = budget_map[think_choice]

                        # 計算費用
                        if PRICING_ENABLED:
                            try:
                                pricing = global_pricing_calculator.get_model_pricing(model_name)
                                input_price = pricing.get('input', pricing.get('input_low', 0))
                                cost_usd = (budget / 1000) * input_price
                                cost_twd = cost_usd * USD_TO_TWD
                                console.print(safe_t('common.completed', fallback='\n✓ 已設定思考預算：{budget} tokens', budget=f'{budget:,}'))
                                console.print(safe_t('common.message', fallback='💰 預估每次思考費用：NT$ {cost_twd} (${cost_usd})', cost_twd=f'{cost_twd:.4f}', cost_usd=f'{cost_usd:.6f}'))
                            except (KeyError, AttributeError, TypeError) as e:
                                logger.warning(f"預算費用估算失敗 (預算: {budget}): {e}")
                                console.print(safe_t('common.completed', fallback='\n✓ 已設定思考預算：{budget} tokens', budget=f'{budget:,}'))
                        else:
                            console.print(safe_t('common.completed', fallback='\n✓ 已設定思考預算：{budget:,} tokens', budget=budget))

                        console.print(safe_t('common.message', fallback='💡 提示：每次對話可用 [think:{budget}] 覆蓋', budget=budget))

                elif cache_choice == '5' and any(tm in model_name for tm in THINKING_MODELS):
                    # 思考費用試算
                    console.print(safe_t('common.message', fallback='\n[#B565D8]💰 思考費用試算器[/#B565D8]\n'))
                    console.print(safe_t('common.message', fallback='當前模型：{model_name}', model_name=model_name))

                    # 根據模型決定範圍
                    is_pro = '2.5-pro' in model_name or '2.0-pro' in model_name
                    # 注意：保留 'flash-8b' 檢查以向下相容舊配置,但該模型實際上不存在於 API 中
                    is_lite = 'flash-8b' in model_name or 'lite' in model_name

                    if is_pro:
                        MAX_TOKENS = 32768
                        MIN_TOKENS = 128
                    elif is_lite:
                        MAX_TOKENS = 24576
                        MIN_TOKENS = 512
                    else:  # flash
                        MAX_TOKENS = 24576
                        MIN_TOKENS = 1

                    console.print(safe_t('common.message', fallback='思考範圍：{MIN_TOKENS:,} - {MAX_TOKENS:,} tokens\n', MIN_TOKENS=MIN_TOKENS, MAX_TOKENS=MAX_TOKENS))

                    tokens_input = Prompt.ask(safe_t("chat.thinking.tokens_input_prompt", fallback="輸入思考 tokens 數量 ({min}-{max}): ").format(min=MIN_TOKENS, max=MAX_TOKENS))
                    if tokens_input.isdigit():
                        tokens = max(MIN_TOKENS, min(int(tokens_input), MAX_TOKENS))

                        if PRICING_ENABLED:
                            try:
                                pricing = global_pricing_calculator.get_model_pricing(model_name)
                                input_price = pricing.get('input', pricing.get('input_low', 0))
                                cost_usd = (tokens / 1000) * input_price
                                cost_twd = cost_usd * USD_TO_TWD

                                console.print(safe_t('common.message', fallback='\n[#B565D8]費用試算結果：[/#B565D8]'))
                                console.print(safe_t('common.message', fallback='  思考 Tokens：{tokens:,}', tokens=tokens))
                                console.print(safe_t('common.message', fallback='  單次費用：NT$ {cost_twd:.4f} (${cost_usd:.6f})', cost_twd=cost_twd, cost_usd=cost_usd))
                                console.print(safe_t('common.message', fallback='  10 次費用：NT$ {cost_twd_10:.4f}', cost_twd_10=cost_twd*10))
                                console.print(safe_t('common.message', fallback='  100 次費用：NT$ {cost_twd_100:.2f}', cost_twd_100=cost_twd*100))
                                console.print(safe_t('common.message', fallback='\n  費率：NT$ {rate:.4f} / 1K tokens', rate=input_price * USD_TO_TWD))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]計算失敗：{e}[/red]', e=e))
                        else:
                            console.print(safe_t('common.message', fallback='[#E8C4F0]計價功能未啟用[/#E8C4F0]'))
                    else:
                        console.print(safe_t('common.message', fallback='[#E8C4F0]無效輸入[/#E8C4F0]'))

                    input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                elif cache_choice == '6' and any(tm in model_name for tm in THINKING_MODELS) and TRANSLATOR_ENABLED:
                    # 翻譯開關
                    console.print(safe_t('common.message', fallback='\n[#B565D8]🌐 思考過程翻譯設定[/#B565D8]\n'))

                    # 顯示翻譯器狀態
                    trans_status = global_translator.get_status()
                    status_text = safe_t('chat.status_enabled', fallback='✅ 啟用') if trans_status['translation_enabled'] else safe_t('chat.status_disabled', fallback='❌ 停用')
                    console.print(safe_t('common.message', fallback='當前狀態: {status}', status=status_text))
                    console.print(safe_t('common.message', fallback='翻譯引擎: {engine}', engine=trans_status['current_engine']))

                    console.print(safe_t('common.message', fallback='\n【可用引擎】'))
                    for engine, status in trans_status['engines'].items():
                        console.print(f"  {engine}: {status}")

                    console.print(safe_t('common.message', fallback='\n【使用統計】'))
                    console.print(safe_t('common.message', fallback='  已翻譯字元: {translated_chars:,}', translated_chars=trans_status['translated_chars']))
                    console.print(safe_t('common.message', fallback='  免費額度剩餘: {free_quota:,} / 500,000 字元', free_quota=trans_status['free_quota_remaining']))
                    console.print(safe_t('common.message', fallback='  快取項目: {cache_size} 個', cache_size=trans_status['cache_size']))

                    console.print(safe_t('common.message', fallback='\n選項：'))
                    console.print(safe_t('common.message', fallback='  [1] 切換翻譯功能（啟用/停用）'))
                    console.print(safe_t('common.message', fallback='  [2] 清除翻譯快取'))
                    console.print(safe_t('common.message', fallback='  [0] 返回\n'))

                    trans_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇: "))

                    if trans_choice == '1':
                        new_state = global_translator.toggle_translation()
                        status_text = safe_t('chat.status_active', fallback='✅ 已啟用') if new_state else safe_t('chat.status_inactive', fallback='❌ 已停用')
                        console.print(safe_t('common.message', fallback='\n{status_text} 思考過程翻譯', status_text=status_text))
                        if new_state:
                            console.print(safe_t('common.message', fallback='💡 思考過程將自動翻譯為繁體中文'))
                        else:
                            console.print(safe_t('common.message', fallback='💡 思考過程將顯示英文原文'))
                    elif trans_choice == '2':
                        global_translator.clear_cache()
                        console.print(safe_t('common.completed', fallback='\n✓ 翻譯快取已清除'))

                    input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                continue

            elif user_input.lower() in ['cli', 'gemini-cli']:
                # Gemini CLI 管理選單
                try:
                    if not CODEGEMINI_ENABLED:
                        console.print(safe_t('common.message', fallback='[#E8C4F0]CodeGemini 功能未啟用（CodeGemini.py 未找到）[/#E8C4F0]'))
                        continue

                    # 檢查 CodeGemini 是否已載入完成
                    if not is_codegemini_ready():
                        console.print(safe_t('common.message', fallback='[yellow]⏳ CodeGemini 配置管理器正在背景載入中...[/yellow]'))
                        console.print(safe_t('common.message', fallback='[dim]首次啟動需要載入配置,請稍候或繼續使用其他功能[/dim]\n'))
                        # 同步載入
                        get_codegemini_config_manager()
                        if is_codegemini_ready():
                            console.print(safe_t('common.message', fallback='[green]✓ CodeGemini 配置管理器已就緒[/green]\n'))
                        else:
                            console.print(safe_t('error.failed', fallback='[red]✗ CodeGemini 配置管理器載入失敗[/red]'))
                            continue

                    while True:
                        console.print("\n" + "=" * 60)
                        console.print(safe_t('common.message', fallback='[bold COLOR_MACARON_PURPLE]🛠️  Gemini CLI 管理工具[/bold COLOR_MACARON_PURPLE]'))
                        console.print("=" * 60)
                        console.print(safe_t('common.message', fallback='\n  [1] 顯示 Gemini CLI 狀態'))
                        console.print(safe_t('common.message', fallback='  [2] 啟動 Gemini CLI session'))
                        console.print(safe_t('common.message', fallback='  [3] 管理 checkpoints'))
                        console.print(safe_t('common.message', fallback='  [4] 安裝/更新 Gemini CLI'))
                        console.print(safe_t('common.message', fallback='  [5] 配置 API Key'))
                        console.print(safe_t('common.message', fallback='\n  [0] 返回\n'))

                        cli_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇: "))

                        if cli_choice == '0':
                            break

                        elif cli_choice == '1':
                            # 顯示狀態
                            try:
                                cg = CodeGemini()
                                cg.print_status()
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif cli_choice == '2':
                            # 啟動 Gemini CLI
                            console.print(safe_t('common.message', fallback='\n[#B565D8]啟動 Gemini CLI...[/#B565D8]'))
                            script_path = Path(__file__).parent / "CodeGemini" / "gemini-with-context.sh"
                            if script_path.exists():
                                try:
                                    subprocess.run([str(script_path)], check=True)
                                except Exception as e:
                                    console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]啟動失敗：{e}[/red]', e=e))
                            else:
                                console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]腳本不存在：{script_path}[/red]', script_path=script_path))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif cli_choice == '3':
                            # 管理 checkpoints
                            console.print(safe_t('common.message', fallback='\n[#B565D8]Checkpoint 管理...[/#B565D8]'))
                            script_path = Path(__file__).parent / "CodeGemini" / "checkpoint-manager.sh"
                            if script_path.exists():
                                try:
                                    subprocess.run([str(script_path)], check=True)
                                except Exception as e:
                                    console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]啟動失敗：{e}[/red]', e=e))
                            else:
                                console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]腳本不存在：{script_path}[/red]', script_path=script_path))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif cli_choice == '4':
                            # 安裝/更新
                            console.print(safe_t('common.message', fallback='\n[#B565D8]安裝/更新 Gemini CLI[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] 安裝'))
                            console.print(safe_t('common.message', fallback='  [2] 更新'))
                            console.print(safe_t('common.message', fallback='  [3] 卸載'))
                            console.print(safe_t('common.message', fallback='  [0] 返回\n'))

                            install_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇: "))

                            try:
                                cg = CodeGemini()
                                if install_choice == '1':
                                    if cg.cli_manager.install():
                                        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 安裝成功[/#B565D8]'))
                                    else:
                                        console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ 安裝失敗[/red]'))
                                elif install_choice == '2':
                                    if cg.cli_manager.update():
                                        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 更新成功[/#B565D8]'))
                                    else:
                                        console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ 更新失敗[/red]'))
                                elif install_choice == '3':
                                    confirm = Prompt.ask(safe_t("chat.cli.uninstall_confirm", fallback="確定要卸載 Gemini CLI？(yes/no): ")).lower()
                                    if confirm == 'yes':
                                        if cg.cli_manager.uninstall():
                                            console.print(safe_t('common.completed', fallback='[#B565D8]✓ 卸載成功[/#B565D8]'))
                                        else:
                                            console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ 卸載失敗[/red]'))
                                    else:
                                        console.print(safe_t('common.message', fallback='[#E8C4F0]已取消[/#E8C4F0]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif cli_choice == '5':
                            # 配置 API Key
                            try:
                                cg = CodeGemini()
                                if cg.api_key_manager.setup_interactive():
                                    console.print(safe_t('common.completed', fallback='[#B565D8]✓ API Key 設定完成[/#B565D8]'))
                                else:
                                    console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ API Key 設定失敗[/red]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                except Exception as e:
                    console.print(f"[red]✗ CLI 管理錯誤: {e}[/red]")
                    if error_diagnostics:
                        error_msg, solutions = error_diagnostics.diagnose_and_suggest(
                            error=e,
                            operation="/cli 指令",
                            context={'command': 'cli', 'error_type': type(e).__name__}
                        )
                        if solutions:
                            console.print(f"\n[yellow]💡 建議的解決方案：[/yellow]")
                            for i, sol in enumerate(solutions, 1):
                                console.print(f"\n[cyan]{i}. {sol.title}[/cyan]")
                                console.print(f"   {sol.description}")
                                if sol.command:
                                    console.print(f"   [green]執行：[/green] {sol.command}")
                                if sol.manual_steps:
                                    console.print(f"   [yellow]手動步驟：[/yellow]")
                                    for step in sol.manual_steps:
                                        console.print(f"     {step}")

                continue

            elif user_input.lower() == 'config':
                # 配置管理選單（嘗試載入配置管理器）
                config_mgr = get_codegemini_config_manager()
                if config_mgr is not None:
                    try:
                        from config_manager import interactive_config_menu

                        # 使用已載入的配置管理器
                        interactive_config_menu(config_mgr)

                        # 配置更新後重新載入
                        global codegemini_config
                        codegemini_config = config_mgr.get_codebase_embedding_config()
                        console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 配置已更新（重啟程式後生效）[/#B565D8]'))

                    except Exception as e:
                        console.print(safe_t('error.failed', fallback='[#B565D8]✗ 配置管理錯誤: {e}[/#B565D8]', e=e))
                else:
                    console.print(safe_t('common.loading', fallback='[#B565D8]✗ CodeGemini 配置管理器未載入[/#B565D8]'))
                    console.print(safe_t('common.message', fallback='[#E8C4F0]請確認：[/#E8C4F0]'))
                    console.print(safe_t('common.message', fallback='[#E8C4F0]  1. CodeGemini 模組已安裝[/#E8C4F0]'))
                    console.print(safe_t('common.message', fallback='[#E8C4F0]  2. CodeGemini/config_manager.py 存在[/#E8C4F0]'))

                continue

            elif user_input.lower() in ['media', 'video', 'veo']:
                # ==========================================
                # 多媒體創作中心 - 精簡版選單
                # ==========================================
                try:
                    while True:
                        console.print("\n" + "=" * 60)
                        console.print(safe_t('media_menu.title', fallback='[bold COLOR_MACARON_PURPLE]🎬 多媒體創作中心[/bold COLOR_MACARON_PURPLE]'))
                        console.print("=" * 60)

                        # 第一層：AI 生成（核心功能）
                        console.print(safe_t('media_menu.section.ai_generation', fallback='\n[bold COLOR_MACARON_PURPLE_LIGHT]>>> AI 創作生成[/bold COLOR_MACARON_PURPLE_LIGHT]'))
                        if FLOW_ENGINE_ENABLED:
                            console.print(safe_t('media_menu.item.flow_video', fallback='  [1] Flow 影片生成（1080p 長影片,自然語言）'))
                        console.print(safe_t('media_menu.item.veo_video', fallback='  [2] Veo 影片生成（8秒快速生成）'))
                        if IMAGEN_GENERATOR_ENABLED:
                            console.print(safe_t('media_menu.item.imagen_generate', fallback='  [12] Imagen 圖像生成（Text-to-Image）'))
                            console.print(safe_t('media_menu.item.vision_imagen', fallback='  [13] 智能圖片創作（Gemini Vision + Imagen）'))
                            # [14] 圖像編輯已移除 - Imagen API 不支援 edit_image() 方法
                            # [15] 圖像放大已移除 - 僅 Vertex AI 支援,Gemini Developer API 不支援

                        # 第二層：影片處理工具
                        console.print(safe_t('media_menu.section.video_processing', fallback='\n[bold COLOR_MACARON_PURPLE_LIGHT]>>> 影片處理[/bold COLOR_MACARON_PURPLE_LIGHT]'))
                        if VIDEO_PREPROCESSOR_ENABLED or VIDEO_COMPOSITOR_ENABLED:
                            if VIDEO_PREPROCESSOR_ENABLED:
                                console.print(safe_t('media_menu.item.video_preprocess', fallback='  [3] 影片預處理（分割/關鍵幀/資訊）'))
                            if VIDEO_COMPOSITOR_ENABLED:
                                console.print(safe_t('media_menu.item.video_concat', fallback='  [4] 影片合併（無損拼接）'))
                        if VIDEO_EFFECTS_ENABLED:
                            console.print(safe_t('media_menu.item.video_trim', fallback='  [15] 時間裁切（無損剪輯）'))
                            console.print(safe_t('media_menu.item.video_filter', fallback='  [16] 濾鏡特效（7種風格）'))
                            console.print(safe_t('media_menu.item.video_speed', fallback='  [17] 速度調整（快轉/慢動作）'))
                            console.print(safe_t('media_menu.item.video_watermark', fallback='  [18] 添加浮水印'))
                        if SUBTITLE_GENERATOR_ENABLED:
                            console.print(safe_t('media_menu.item.subtitle_generate', fallback='  [19] 生成字幕（語音辨識+翻譯）'))
                            console.print(safe_t('media_menu.item.subtitle_burn', fallback='  [20] 燒錄字幕（嵌入影片）'))

                        # 第三層：音訊處理
                        if AUDIO_PROCESSOR_ENABLED:
                            console.print(safe_t('media_menu.section.audio_processing', fallback='\n[bold COLOR_MACARON_PURPLE_LIGHT]>>> 音訊處理[/bold COLOR_MACARON_PURPLE_LIGHT]'))
                            console.print(safe_t('media_menu.audio_group', fallback='  [7] 提取音訊  [8] 合併音訊  [9] 音量調整'))
                            console.print(safe_t('media_menu.audio_group2', fallback='  [10] 背景音樂  [11] 淡入淡出'))

                        # 第四層：AI 分析
                        console.print(safe_t('media_menu.section.ai_analysis', fallback='\n[bold COLOR_MACARON_PURPLE_LIGHT]>>> AI 分析工具[/bold COLOR_MACARON_PURPLE_LIGHT]'))
                        if MEDIA_VIEWER_ENABLED:
                            console.print(safe_t('media_menu.item.media_analyzer', fallback='  [0] 媒體分析器（圖片/影片 AI 分析）'))
                        if VIDEO_ANALYZER_ENABLED:
                            console.print(safe_t('media_menu.item.video_chat', fallback='  [21] 影片互動對話（上傳後連續提問）'))
                        console.print(safe_t('media_menu.analysis_group', fallback='  [5] 影片內容分析  [6] 圖像內容分析'))

                        console.print(safe_t('media_menu.back', fallback='\n  [99] 返回主選單\n'))

                        # 使用 rich.prompt.Prompt 支援方向鍵編輯
                        media_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇"))

                        if media_choice == '99':
                            break

                        elif media_choice == '0' and MEDIA_VIEWER_ENABLED:
                            # 媒體檔案查看器
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎬 媒體檔案查看器[/#B565D8]\n'))
                            file_path = Prompt.ask(safe_t("chat.media.file_path_prompt", fallback="檔案路徑："))

                            if not os.path.isfile(file_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            try:
                                viewer = MediaViewer()
                                viewer.view_file(file_path)

                                # 詢問是否進行 AI 分析
                                if viewer.ai_analysis_enabled:
                                    analyze = Prompt.ask(safe_t("chat.media.ai_analyze_prompt", fallback="\n[#B565D8]進行 AI 分析？(y/N): [/#B565D8]")).lower()
                                    if analyze == 'y':
                                        custom = Prompt.ask(safe_t("chat.media.custom_analyze_prompt", fallback="[#B565D8]自訂分析提示（可留空使用預設）：[/#B565D8]\n"))
                                        viewer.analyze_with_ai(file_path, custom if custom else None)

                                # 詢問是否開啟檔案
                                open_file = Prompt.ask(safe_t("chat.media.open_file_prompt", fallback="\n[#B565D8]開啟檔案？(y/N): [/#B565D8]")).lower()
                                if open_file == 'y':
                                    os.system(f'open "{file_path}"')

                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '1' and FLOW_ENGINE_ENABLED:
                            # Flow 引擎 - 自然語言生成影片（預設 1080p）
                            console.print(safe_t('common.generating', fallback='\n[#B565D8]🎬 Flow 引擎 - 智能影片生成（預設 1080p）[/#B565D8]\n'))

                            description = Prompt.ask(safe_t("chat.media.veo.describe_prompt", fallback="請描述您想要的影片內容："))
                            if not description:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]未輸入描述,取消操作[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            duration_input = Prompt.ask(safe_t("chat.media.veo.duration_prompt", fallback="目標時長（秒,預設 30）："))
                            target_duration = int(duration_input) if duration_input.isdigit() else 30

                            # 智能建議：長影片自動使用最佳參數
                            if target_duration > 60:
                                console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]💡 長影片建議使用最佳參數：1080p, 16:9[/dim COLOR_MACARON_PURPLE_LIGHT]'))

                            # 預設使用最佳參數（1080p, 16:9）
                            resolution = "1080p"
                            aspect_ratio = "16:9"

                            # 僅在用戶需要時提供自訂選項
                            custom_settings = Prompt.ask(safe_t("chat.media.veo.use_default_prompt", fallback="\n使用預設最佳參數（1080p, 16:9）？(Y/n): ")).lower()
                            if custom_settings == 'n':
                                # 解析度選擇
                                console.print(safe_t('common.message', fallback='\n[#B565D8]解析度：[/#B565D8]'))
                                console.print(safe_t('common.message', fallback='  [1] 1080p (推薦)'))
                                console.print("  [2] 720p")
                                resolution_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇："))
                                resolution = "1080p" if resolution_choice != '2' else "720p"

                                # 比例選擇
                                console.print(safe_t('common.message', fallback='\n[#B565D8]比例：[/#B565D8]'))
                                console.print(safe_t('common.message', fallback='  [1] 16:9 (橫向,預設)'))
                                console.print(safe_t('common.message', fallback='  [2] 9:16 (直向)'))
                                ratio_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇："))
                                aspect_ratio = "16:9" if ratio_choice != '2' else "9:16"

                            console.print(safe_t('common.generating', fallback='\n[dim COLOR_MACARON_PURPLE]⏳ 準備生成 {target_duration}秒 影片（{resolution}, {aspect_ratio}）...[/dim COLOR_MACARON_PURPLE]', target_duration=target_duration, resolution=resolution, aspect_ratio=aspect_ratio))

                            try:
                                # 初始化 Flow Engine（傳入計價器與影片配置）
                                if PRICING_ENABLED:
                                    engine = FlowEngine(
                                        pricing_calculator=global_pricing_calculator,
                                        resolution=resolution,
                                        aspect_ratio=aspect_ratio
                                    )
                                else:
                                    engine = FlowEngine(
                                        resolution=resolution,
                                        aspect_ratio=aspect_ratio
                                    )

                                video_path = engine.generate_from_description(
                                    description=description,
                                    target_duration=target_duration,
                                    show_cost=PRICING_ENABLED
                                )

                                if video_path:
                                    console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 影片生成完成！[/#B565D8]'))
                                    console.print(safe_t('common.saving', fallback='儲存路徑：{video_path}', video_path=video_path))
                                else:
                                    console.print(safe_t('common.generating', fallback='\n[#E8C4F0]已取消生成[/#E8C4F0]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))

                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '2':
                            # Veo 基本生成
                            console.print(safe_t('common.generating', fallback='\n[#B565D8]🎬 Veo 基本影片生成[/#B565D8]\n'))
                            console.print(safe_t('common.message', fallback='使用獨立工具：'))
                            console.print("  python gemini_veo_generator.py\n")
                            console.print(safe_t('common.message', fallback='功能：'))
                            console.print(safe_t('common.generating', fallback='  - 文字生成影片（8 秒,Veo 3.1）'))
                            console.print(safe_t('common.message', fallback='  - 支援參考圖片'))
                            console.print(safe_t('common.message', fallback='  - 自訂長寬比'))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '3' and VIDEO_PREPROCESSOR_ENABLED:
                            # 影片預處理
                            console.print(safe_t('common.processing', fallback='\n[#B565D8]✂️ 影片預處理工具[/#B565D8]\n'))
                            console.print(safe_t('common.message', fallback='功能：'))
                            console.print(safe_t('common.message', fallback='  1. 查詢影片資訊（解析度/時長/編碼/大小）'))
                            console.print(safe_t('common.message', fallback='  2. 分割影片（固定時長分段）'))
                            console.print(safe_t('common.message', fallback='  3. 提取關鍵幀（等距提取）'))
                            console.print(safe_t('common.message', fallback='  4. 檢查檔案大小（API 限制 < 2GB）\n'))
                            console.print(safe_t('common.message', fallback='使用方式：'))
                            console.print(safe_t('common.message', fallback='  python gemini_video_preprocessor.py <影片路徑> <指令>'))
                            console.print(safe_t('common.message', fallback='\n範例：'))
                            console.print("  python gemini_video_preprocessor.py video.mp4 info")
                            console.print("  python gemini_video_preprocessor.py video.mp4 split")
                            console.print("  python gemini_video_preprocessor.py video.mp4 keyframes")
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '4' and VIDEO_COMPOSITOR_ENABLED:
                            # 影片合併
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎞️ 影片合併工具[/#B565D8]\n'))
                            console.print(safe_t('common.message', fallback='功能：'))
                            console.print(safe_t('common.message', fallback='  - 無損合併多段影片（ffmpeg concat demuxer）'))
                            console.print(safe_t('common.message', fallback='  - 保持原始品質（禁止有損壓縮）'))
                            console.print(safe_t('common.message', fallback='  - 替換影片片段（Insert 功能）\n'))
                            console.print(safe_t('common.message', fallback='使用方式：'))
                            console.print(safe_t('common.message', fallback='  python gemini_video_compositor.py concat <影片1> <影片2> ...'))
                            console.print(safe_t('common.message', fallback='  python gemini_video_compositor.py replace <基礎影片> <新片段> <時間點>'))
                            console.print(safe_t('common.message', fallback='\n範例：'))
                            console.print("  python gemini_video_compositor.py concat seg1.mp4 seg2.mp4 seg3.mp4")
                            console.print("  python gemini_video_compositor.py replace base.mp4 new.mp4 10.5")
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '5':
                            # 影片分析
                            console.print(safe_t('common.analyzing', fallback='\n[#B565D8]🎥 影片分析工具[/#B565D8]\n'))
                            console.print(safe_t('common.message', fallback='使用獨立工具：'))
                            console.print(safe_t('common.message', fallback='  python gemini_video_analyzer.py <影片路徑>\n'))
                            console.print(safe_t('common.message', fallback='功能：'))
                            console.print(safe_t('common.message', fallback='  - 自動提取關鍵幀'))
                            console.print(safe_t('common.analyzing', fallback='  - Gemini 分析影片內容'))
                            console.print(safe_t('common.generating', fallback='  - 生成詳細描述'))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '6':
                            # 圖像分析
                            console.print(safe_t('common.analyzing', fallback='\n[#B565D8]🖼️ 圖像分析工具[/#B565D8]\n'))
                            console.print(safe_t('common.message', fallback='使用獨立工具：'))
                            console.print(safe_t('common.message', fallback='  python gemini_image_analyzer.py <圖片路徑>\n'))
                            console.print(safe_t('common.message', fallback='功能：'))
                            console.print(safe_t('common.analyzing', fallback='  - Gemini Vision 圖像分析'))
                            console.print(safe_t('common.message', fallback='  - 支援多種圖片格式'))
                            console.print(safe_t('common.message', fallback='  - 詳細內容描述'))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '7' and AUDIO_PROCESSOR_ENABLED:
                            # 提取音訊
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎵 提取音訊[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))
                            if not video_path or not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            console.print(safe_t('common.message', fallback='\n[#B565D8]音訊格式：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] AAC (預設)'))
                            console.print("  [2] MP3")
                            console.print("  [3] WAV")
                            format_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇："))
                            format_map = {'1': 'aac', '2': 'mp3', '3': 'wav'}
                            audio_format = format_map.get(format_choice, 'aac')

                            try:
                                processor = AudioProcessor()
                                output_path = processor.extract_audio(video_path, format=audio_format)
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 音訊已提取：{output_path}[/#B565D8]', output_path=output_path))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '8' and AUDIO_PROCESSOR_ENABLED:
                            # 合併音訊
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎵 合併音訊[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))
                            audio_path = Prompt.ask(safe_t("chat.media.audio_path_prompt", fallback="音訊路徑："))

                            if not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]影片檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue
                            if not os.path.isfile(audio_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]音訊檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            console.print(safe_t('common.message', fallback='\n[#B565D8]合併模式：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] 替換（取代原音訊,預設）'))
                            console.print(safe_t('common.message', fallback='  [2] 混合（與原音訊混合）'))
                            mode_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇："))
                            replace_mode = mode_choice != '2'

                            try:
                                processor = AudioProcessor()
                                output_path = processor.merge_audio(video_path, audio_path, replace=replace_mode)
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 音訊已合併：{output_path}[/#B565D8]', output_path=output_path))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '9' and AUDIO_PROCESSOR_ENABLED:
                            # 音量調整
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎵 音量調整[/#B565D8]\n'))
                            file_path = Prompt.ask(safe_t("chat.media.av_path_prompt", fallback="影片/音訊路徑："))
                            if not os.path.isfile(file_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            volume_input = Prompt.ask(safe_t("chat.media.volume_multiplier_prompt", fallback="音量倍數（0.5=50%, 1.0=100%, 2.0=200%,預設1.0）："))
                            try:
                                volume = float(volume_input) if volume_input else 1.0
                                if volume <= 0:
                                    console.print(safe_t('common.message', fallback='[#E8C4F0]音量必須大於0[/#E8C4F0]'))
                                    input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                    continue
                            except ValueError:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]無效的數值[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            try:
                                processor = AudioProcessor()
                                output_path = processor.adjust_volume(file_path, volume)
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 音量已調整：{output_path}[/#B565D8]', output_path=output_path))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '10' and AUDIO_PROCESSOR_ENABLED:
                            # 添加背景音樂
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎵 添加背景音樂[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))
                            music_path = Prompt.ask(safe_t("chat.media.music_path_prompt", fallback="背景音樂路徑："))

                            if not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]影片檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue
                            if not os.path.isfile(music_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]音樂檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            volume_input = Prompt.ask(safe_t("chat.media.music_volume_prompt", fallback="背景音樂音量（0.0-1.0,預設0.3）："))
                            fade_input = Prompt.ask(safe_t("chat.media.fade_duration_prompt", fallback="淡入淡出時長（秒,預設2.0）："))

                            try:
                                music_volume = float(volume_input) if volume_input else 0.3
                                fade_duration = float(fade_input) if fade_input else 2.0
                            except ValueError:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]無效的數值[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            try:
                                processor = AudioProcessor()
                                output_path = processor.add_background_music(
                                    video_path, music_path,
                                    music_volume=music_volume,
                                    fade_duration=fade_duration
                                )
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 背景音樂已添加：{output_path}[/#B565D8]', output_path=output_path))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '11' and AUDIO_PROCESSOR_ENABLED:
                            # 淡入淡出
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎵 音訊淡入淡出[/#B565D8]\n'))
                            file_path = Prompt.ask(safe_t("chat.media.av_path_prompt", fallback="影片/音訊路徑："))
                            if not os.path.isfile(file_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            fade_in_input = Prompt.ask(safe_t("chat.media.fade_in_prompt", fallback="淡入時長（秒,預設2.0）："))
                            fade_out_input = Prompt.ask(safe_t("chat.media.fade_out_prompt", fallback="淡出時長（秒,預設2.0）："))

                            try:
                                fade_in = float(fade_in_input) if fade_in_input else 2.0
                                fade_out = float(fade_out_input) if fade_out_input else 2.0
                            except ValueError:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]無效的數值[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            try:
                                processor = AudioProcessor()
                                output_path = processor.fade_in_out(file_path, fade_in=fade_in, fade_out=fade_out)
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 淡入淡出已完成：{output_path}[/#B565D8]', output_path=output_path))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '12' and IMAGEN_GENERATOR_ENABLED:
                            # 生成圖片
                            console.print(safe_t('common.generating', fallback='\n[#B565D8]🎨 Imagen 圖片生成[/#B565D8]\n'))
                            prompt = Prompt.ask(safe_t("chat.imagen.describe_prompt", fallback="請描述您想生成的圖片："))

                            if not prompt:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]未輸入描述[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            negative_prompt = Prompt.ask(safe_t("chat.imagen.negative_prompt", fallback="\n負面提示（避免的內容,可留空）："))
                            if not negative_prompt:
                                negative_prompt = None

                            console.print(safe_t('common.message', fallback='\n選擇長寬比：'))
                            console.print(safe_t('common.message', fallback='  1. 1:1 (正方形,預設)'))
                            console.print(safe_t('common.message', fallback='  2. 16:9 (橫向)'))
                            console.print(safe_t('common.message', fallback='  3. 9:16 (直向)'))
                            aspect_choice = Prompt.ask(safe_t("chat.imagen.aspect_choice_prompt", fallback="請選擇 (1-3, 預設=1): ")) or '1'
                            aspect_ratios = {'1': '1:1', '2': '16:9', '3': '9:16'}
                            aspect_ratio = aspect_ratios.get(aspect_choice, '1:1')

                            num_input = Prompt.ask(safe_t("chat.imagen.number_prompt", fallback="\n生成數量（1-4,預設=1）："))
                            number_of_images = int(num_input) if num_input.isdigit() and 1 <= int(num_input) <= 4 else 1

                            try:
                                output_paths = generate_image(
                                    prompt=prompt,
                                    negative_prompt=negative_prompt,
                                    number_of_images=number_of_images,
                                    aspect_ratio=aspect_ratio,
                                    show_cost=PRICING_ENABLED
                                )
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 圖片已生成：{image_count} 張[/#B565D8]', image_count=len(output_paths)))

                                open_img = Prompt.ask(safe_t("chat.imagen.open_image_prompt", fallback="\n要開啟圖片嗎？(y/N): ")).lower()
                                if open_img == 'y':
                                    for path in output_paths:
                                        os.system(f'open "{path}"')
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        # ==========================================
                        # [13] Imagen 圖像編輯 - 已移除
                        # ==========================================
                        # 原因：Imagen API 不支援 edit_image() 方法
                        # 官方文檔：https://ai.google.dev/gemini-api/docs/imagen
                        # API 僅支援：generate_images()（文字生成圖片）
                        # 移除日期：2025-10-31
                        # ==========================================
                        # elif media_choice == '13' and IMAGEN_GENERATOR_ENABLED:
                        #     console.print(safe_t('common.message', fallback='\n[#B565D8]✏️ Imagen 圖片編輯[/#B565D8]\n'))
                        #     console.print(safe_t('error.api_not_supported',
                        #                         fallback='❌ Imagen API 不支援圖片編輯功能\n'
                        #                                  '💡 建議：使用 [12] Imagen 圖像生成重新創作'))
                        #     input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                        # ==========================================

                        # ==========================================
                        # [13] 智能圖片創作（Gemini Vision + Imagen）
                        # ==========================================
                        elif media_choice == '13' and IMAGEN_GENERATOR_ENABLED:
                            # 智能圖片創作
                            from gemini_vision_imagen import create_image_with_vision

                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎨 智能圖片創作（Gemini Vision + Imagen）[/#B565D8]\n'))
                            console.print(safe_t('common.message', fallback='[dim #E8C4F0]透過 Gemini Vision 分析原圖 + Imagen 生成新圖[/dim #E8C4F0]\n'))

                            source_path = Prompt.ask(safe_t("chat.media.source_image", fallback="原圖路徑："))
                            if not source_path or not os.path.isfile(source_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            instruction = Prompt.ask(safe_t("chat.media.edit_instruction", fallback="\n編輯指示（例：把背景改成藍色天空）："))
                            if not instruction:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]未輸入指示[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            try:
                                output_path = create_image_with_vision(
                                    source_image_path=source_path,
                                    edit_instruction=instruction,
                                    show_cost=PRICING_ENABLED
                                )
                                console.print(safe_t('common.completed', fallback=f'\n✅ 已生成：{output_path}'))

                                if input(safe_t("chat.media.open_image", fallback="\n開啟圖片？(y/N): ")).lower() == 'y':
                                    import subprocess
                                    subprocess.run(['open', output_path])
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback=f'[red]錯誤：{e}[/red]'))

                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        # ==========================================
                        # [14] Imagen 圖像放大 - 已移除
                        # ==========================================
                        # 原因：upscale_image() 僅 Vertex AI 支援
                        # 錯誤訊息："This method is only supported in the Vertex AI client."
                        # 測試日期：2025-10-31 (test_imagen_upscale.py)
                        # 移除日期：2025-10-31
                        # ==========================================
                        # elif media_choice == '14' and IMAGEN_GENERATOR_ENABLED:
                        #     console.print(safe_t('common.message', fallback='\n[#B565D8]🔍 Imagen 圖片放大[/#B565D8]\n'))
                        #     console.print(safe_t('error.api_not_supported',
                        #                         fallback='❌ Imagen upscale_image 僅 Vertex AI 支援\n'
                        #                                  '💡 Gemini Developer API 不提供此功能'))
                        #     input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                        # ==========================================

                        elif media_choice == '15' and VIDEO_EFFECTS_ENABLED:
                            # 時間裁切（無損）
                            console.print(safe_t('common.message', fallback='\n[#B565D8]✂️ 時間裁切（無損）[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))

                            if not video_path or not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            start_input = Prompt.ask(safe_t("chat.media.start_time_prompt", fallback="\n開始時間（秒,預設0）："))
                            end_input = Prompt.ask(safe_t("chat.media.end_time_prompt", fallback="結束時間（秒,留空=影片結尾）："))

                            try:
                                start_time = float(start_input) if start_input else 0
                                end_time = float(end_input) if end_input else None

                                effects = VideoEffects()
                                output_path = effects.trim_video(video_path, start_time=start_time, end_time=end_time)
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 影片已裁切：{output_path}[/#B565D8]', output_path=output_path))
                                console.print(safe_t('common.message', fallback='[dim]提示：使用 -c copy 無損裁切,保持原始品質[/dim]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '16' and VIDEO_EFFECTS_ENABLED:
                            # 濾鏡效果
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🎨 濾鏡效果[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))

                            if not video_path or not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            console.print(safe_t('common.message', fallback='\n[#B565D8]選擇濾鏡：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] 黑白 (grayscale)'))
                            console.print(safe_t('common.message', fallback='  [2] 復古 (sepia)'))
                            console.print(safe_t('common.message', fallback='  [3] 懷舊 (vintage)'))
                            console.print(safe_t('common.message', fallback='  [4] 銳化 (sharpen)'))
                            console.print(safe_t('common.message', fallback='  [5] 模糊 (blur)'))
                            console.print(safe_t('common.message', fallback='  [6] 增亮 (brighten)'))
                            console.print(safe_t('common.message', fallback='  [7] 增強對比 (contrast)'))
                            filter_choice = Prompt.ask(safe_t("chat.media.choose_1_7", fallback="請選擇 (1-7): "))

                            filter_map = {
                                '1': 'grayscale',
                                '2': 'sepia',
                                '3': 'vintage',
                                '4': 'sharpen',
                                '5': 'blur',
                                '6': 'brighten',
                                '7': 'contrast'
                            }
                            filter_name = filter_map.get(filter_choice)

                            if not filter_name:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]無效的選擇[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            console.print(safe_t('common.message', fallback='\n[#B565D8]品質設定：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] 高品質 (CRF 18, slow)'))
                            console.print(safe_t('common.message', fallback='  [2] 中品質 (CRF 23, medium, 預設)'))
                            console.print(safe_t('common.message', fallback='  [3] 低品質 (CRF 28, fast)'))
                            quality_choice = Prompt.ask(safe_t("chat.media.quality_choice", fallback="請選擇 (1-3, 預設=2): ")) or '2'
                            quality_map = {'1': 'high', '2': 'medium', '3': 'low'}
                            quality = quality_map.get(quality_choice, 'medium')

                            try:
                                effects = VideoEffects()
                                output_path = effects.apply_filter(video_path, filter_name=filter_name, quality=quality)
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 濾鏡已套用：{output_path}[/#B565D8]', output_path=output_path))
                                console.print(safe_t('common.message', fallback='[dim]注意：濾鏡需要重新編碼,已使用高品質設定[/dim]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '17' and VIDEO_EFFECTS_ENABLED:
                            # 速度調整
                            console.print(safe_t('common.message', fallback='\n[#B565D8]⚡ 速度調整[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))

                            if not video_path or not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            console.print(safe_t('common.message', fallback='\n[#B565D8]速度倍數：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  0.5 = 慢動作（一半速度）'))
                            console.print(safe_t('common.message', fallback='  1.0 = 正常速度'))
                            console.print(safe_t('common.message', fallback='  2.0 = 快轉（兩倍速度）'))
                            speed_input = Prompt.ask(safe_t("chat.media.speed_input", fallback="\n請輸入速度倍數（預設1.0）："))

                            try:
                                speed_factor = float(speed_input) if speed_input else 1.0
                                if speed_factor <= 0:
                                    console.print(safe_t('common.message', fallback='[#E8C4F0]速度必須大於0[/#E8C4F0]'))
                                    input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                    continue
                            except ValueError:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]無效的數值[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            console.print(safe_t('common.message', fallback='\n[#B565D8]品質設定：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] 高品質 (CRF 18, slow)'))
                            console.print(safe_t('common.message', fallback='  [2] 中品質 (CRF 23, medium, 預設)'))
                            console.print(safe_t('common.message', fallback='  [3] 低品質 (CRF 28, fast)'))
                            quality_choice = Prompt.ask(safe_t("chat.media.quality_choice", fallback="請選擇 (1-3, 預設=2): ")) or '2'
                            quality_map = {'1': 'high', '2': 'medium', '3': 'low'}
                            quality = quality_map.get(quality_choice, 'medium')

                            try:
                                effects = VideoEffects()
                                output_path = effects.adjust_speed(video_path, speed_factor=speed_factor, quality=quality)
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 速度已調整：{output_path}[/#B565D8]', output_path=output_path))
                                console.print(safe_t('common.message', fallback='[dim]注意：同時調整影片和音訊速度,已使用高品質設定[/dim]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '18' and VIDEO_EFFECTS_ENABLED:
                            # 添加浮水印
                            console.print(safe_t('common.message', fallback='\n[#B565D8]💧 添加浮水印[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))
                            watermark_path = Prompt.ask(safe_t("chat.media.watermark_path", fallback="浮水印圖片路徑："))

                            if not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]影片檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            if not os.path.isfile(watermark_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]浮水印檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            console.print(safe_t('common.message', fallback='\n[#B565D8]浮水印位置：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] 左上角'))
                            console.print(safe_t('common.message', fallback='  [2] 右上角'))
                            console.print(safe_t('common.message', fallback='  [3] 左下角'))
                            console.print(safe_t('common.message', fallback='  [4] 右下角（預設）'))
                            console.print(safe_t('common.message', fallback='  [5] 中央'))
                            position_choice = Prompt.ask(safe_t("chat.media.position_choice", fallback="請選擇 (1-5, 預設=4): ")) or '4'

                            position_map = {
                                '1': 'top-left',
                                '2': 'top-right',
                                '3': 'bottom-left',
                                '4': 'bottom-right',
                                '5': 'center'
                            }
                            position = position_map.get(position_choice, 'bottom-right')

                            opacity_input = Prompt.ask(safe_t("chat.media.opacity_input", fallback="\n不透明度（0.0-1.0,預設0.7）："))
                            try:
                                opacity = float(opacity_input) if opacity_input else 0.7
                                if not 0 <= opacity <= 1:
                                    console.print(safe_t('common.message', fallback='[#E8C4F0]不透明度必須在 0.0-1.0 之間[/#E8C4F0]'))
                                    input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                    continue
                            except ValueError:
                                console.print(safe_t('common.message', fallback='[#E8C4F0]無效的數值[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            try:
                                effects = VideoEffects()
                                output_path = effects.add_watermark(
                                    video_path, watermark_path,
                                    position=position, opacity=opacity
                                )
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 浮水印已添加：{output_path}[/#B565D8]', output_path=output_path))
                                console.print(safe_t('common.message', fallback='[dim]注意：添加浮水印需要重新編碼,已使用高品質設定[/dim]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '19' and SUBTITLE_GENERATOR_ENABLED:
                            # 生成字幕
                            console.print(safe_t('common.generating', fallback='\n[#B565D8]📝 生成字幕[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))

                            if not video_path or not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            # 字幕格式選擇
                            console.print(safe_t('common.message', fallback='\n[#B565D8]字幕格式：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] SRT (預設)'))
                            console.print("  [2] VTT")
                            format_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇："))
                            subtitle_format = "vtt" if format_choice == '2' else "srt"

                            # 是否翻譯
                            translate_choice = Prompt.ask(safe_t("chat.media.translate_subtitle_prompt", fallback="\n是否翻譯字幕？(y/N): ")).lower()
                            translate = (translate_choice == 'y')

                            target_lang = "zh-TW"
                            if translate:
                                console.print(safe_t('common.message', fallback='\n[#B565D8]目標語言：[/#B565D8]'))
                                console.print(safe_t('common.message', fallback='  [1] 繁體中文 (zh-TW, 預設)'))
                                console.print(safe_t('common.message', fallback='  [2] 英文 (en)'))
                                console.print(safe_t('common.message', fallback='  [3] 日文 (ja)'))
                                console.print(safe_t('common.message', fallback='  [4] 韓文 (ko)'))
                                console.print(safe_t('common.message', fallback='  [5] 自訂'))
                                lang_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇："))

                                lang_map = {
                                    '1': 'zh-TW',
                                    '2': 'en',
                                    '3': 'ja',
                                    '4': 'ko'
                                }
                                if lang_choice == '5':
                                    target_lang = Prompt.ask(safe_t("chat.media.custom_lang_code", fallback="請輸入語言代碼（如 fr, de）："))
                                else:
                                    target_lang = lang_map.get(lang_choice, 'zh-TW')

                            try:
                                # 傳入計價器以實現累計成本追蹤
                                if PRICING_ENABLED:
                                    generator = SubtitleGenerator(pricing_calculator=global_pricing_calculator)
                                else:
                                    generator = SubtitleGenerator()

                                subtitle_path = generator.generate_subtitles(
                                    video_path=video_path,
                                    format=subtitle_format,
                                    translate=translate,
                                    target_language=target_lang,
                                    show_cost=PRICING_ENABLED
                                )
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 字幕已生成：{subtitle_path}[/#B565D8]', subtitle_path=subtitle_path))

                                # 詢問是否燒錄
                                burn_choice = Prompt.ask(safe_t("chat.media.burn_subtitle_prompt", fallback="\n要將字幕燒錄到影片嗎？(y/N): ")).lower()
                                if burn_choice == 'y':
                                    video_with_subs = generator.burn_subtitles(video_path, subtitle_path)
                                    console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 燒錄完成：{video_with_subs}[/#B565D8]', video_with_subs=video_with_subs))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                                import traceback
                                traceback.print_exc()
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '20' and SUBTITLE_GENERATOR_ENABLED:
                            # 燒錄字幕
                            console.print(safe_t('common.message', fallback='\n[#B565D8]🔥 燒錄字幕[/#B565D8]\n'))
                            video_path = Prompt.ask(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))
                            subtitle_path = Prompt.ask(safe_t("chat.media.subtitle_path_prompt", fallback="字幕檔案路徑："))

                            if not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]影片檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            if not os.path.isfile(subtitle_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]字幕檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            try:
                                generator = SubtitleGenerator()
                                output_path = generator.burn_subtitles(video_path, subtitle_path)
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 字幕已燒錄：{output_path}[/#B565D8]', output_path=output_path))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                        elif media_choice == '21' and VIDEO_ANALYZER_ENABLED:
                            # 影片互動對話
                            console.print(safe_t('common.analyzing', fallback='\n[#B565D8]💬 影片互動對話[/#B565D8]\n'))
                            console.print(safe_t('common.message', fallback='[dim]上傳影片後可進行連續提問,支援方向鍵瀏覽歷史記錄[/dim]\n'))

                            # get_user_input 已在全局定義,無需導入
                            video_path = get_user_input(safe_t("chat.media.video_path_prompt", fallback="影片路徑："))

                            if not video_path or not os.path.isfile(video_path):
                                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                                input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                                continue

                            # 選擇模型
                            console.print(safe_t('common.message', fallback='\n[#B565D8]選擇分析模型：[/#B565D8]'))
                            console.print(safe_t('common.message', fallback='  [1] gemini-2.5-pro (推薦,支援思考模式)'))
                            console.print(safe_t('common.message', fallback='  [2] gemini-2.5-flash (快速)'))
                            console.print(safe_t('common.message', fallback='  [3] gemini-2.5-flash-lite (超快速)'))
                            model_choice = get_user_input(safe_t("chat.common.choose_prompt", fallback="請選擇 (預設=1): ")) or '1'

                            model_map = {
                                '1': 'gemini-2.5-pro',
                                '2': 'gemini-2.5-flash',
                                '3': 'gemini-2.5-flash-lite'
                            }
                            model_name = model_map.get(model_choice, 'gemini-2.5-pro')

                            try:
                                # 初始化影片分析器
                                analyzer = VideoAnalyzer(model_name=model_name)

                                # 上傳影片
                                console.print(safe_t('common.processing', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]⏳ 上傳並處理影片...[/dim COLOR_MACARON_PURPLE_LIGHT]'))
                                video_file = analyzer.upload_video(video_path)

                                # 進入互動模式
                                analyzer.interactive_video_chat(video_file)

                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：{e}[/red]', e=e))
                                import traceback
                                traceback.print_exc()

                            input(safe_t("chat.common.press_enter", fallback="\n按 Enter 繼續..."))

                        else:
                            console.print(safe_t('common.message', fallback='\n[#E8C4F0]無效選項或功能未啟用[/#E8C4F0]'))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                except Exception as e:
                    console.print(f"[red]✗ 多媒體功能錯誤: {e}[/red]")
                    if error_diagnostics:
                        error_msg, solutions = error_diagnostics.diagnose_and_suggest(
                            error=e,
                            operation="/media 指令",
                            context={'command': 'media', 'error_type': type(e).__name__}
                        )
                        if solutions:
                            console.print(f"\n[yellow]💡 建議的解決方案：[/yellow]")
                            for i, sol in enumerate(solutions, 1):
                                console.print(f"\n[cyan]{i}. {sol.title}[/cyan]")
                                console.print(f"   {sol.description}")
                                if sol.command:
                                    console.print(f"   [green]執行：[/green] {sol.command}")
                                if sol.manual_steps:
                                    console.print(f"   [yellow]手動步驟：[/yellow]")
                                    for step in sol.manual_steps:
                                        console.print(f"     {step}")

                continue

            elif user_input.lower() in ['debug', 'test']:
                # 除錯與測試工具選單
                # 狀態追蹤：記錄 Embedding 功能的載入狀態（互斥機制）
                embedding_active_mode = None  # None, 'search', 'stats'

                while True:
                    console.print("\n" + "=" * 60)
                    console.print(safe_t('common.message', fallback='[bold COLOR_MACARON_PURPLE]🔧 除錯與測試工具[/bold COLOR_MACARON_PURPLE]'))
                    console.print("=" * 60)

                    console.print(safe_t('common.message', fallback='\n[#B565D8]測試模組：[/#B565D8]'))
                    console.print(safe_t('common.message', fallback='  [1] 環境檢查'))
                    console.print(safe_t('common.message', fallback='  [2] 主程式功能測試'))
                    console.print(safe_t('common.message', fallback='  [3] Flow Engine 測試'))
                    console.print(safe_t('common.message', fallback='  [4] 終端輸入測試'))

                    if CODEBASE_EMBEDDING_ENABLED:
                        console.print("\n[#B565D8]Codebase Embedding：[/#B565D8]")
                        console.print(safe_t('common.message', fallback='  [5] 搜尋對話記錄'))
                        console.print(safe_t('common.message', fallback='  [6] 查看向量資料庫統計'))

                    console.print(safe_t('common.message', fallback='\n[#B565D8]性能監控：[/#B565D8]'))
                    console.print(safe_t('common.message', fallback='  [7] 查看性能摘要'))
                    console.print(safe_t('common.analyzing', fallback='  [8] 查看瓶頸分析報告'))
                    console.print(safe_t('common.message', fallback='  [9] 匯出性能報告'))

                    if TOOLS_MANAGER_AVAILABLE:
                        console.print(safe_t('common.message', fallback='\n[#B565D8]工具管理：[/#B565D8]'))
                        console.print(safe_t('common.message', fallback='  [10] 工具調用統計'))
                        console.print(safe_t('common.message', fallback='  [11] 工具調用詳細報告'))

                    console.print(safe_t('common.message', fallback='\n  [0] 返回主選單\n'))

                    debug_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇: "))

                    if debug_choice == '0':
                        break

                    # 根據選擇調用對應測試腳本
                    test_scripts = {
                        '1': ('test_environment.py', safe_t('chat.test_environment', fallback='環境檢查')),
                        '2': ('test_chat_features.py', safe_t('chat.test_chat_features', fallback='主程式功能測試')),
                        '3': ('test_flow_engine.py', safe_t('chat.test_flow_engine', fallback='Flow Engine 測試')),
                        '4': ('test_terminal.py', safe_t('chat.test_terminal', fallback='終端輸入測試'))
                    }

                    if debug_choice in test_scripts:
                        script_name, description = test_scripts[debug_choice]
                        console.print(safe_t('common.message', fallback='\n[#B565D8]執行 {description}...[/#B565D8]\n', description=description))
                        test_script = Path(__file__).parent / "testTool" / script_name

                        if not test_script.exists():
                            console.print(safe_t('error.not_found', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]錯誤：找不到 testTool/{script_name}[/red]', script_name=script_name))
                        else:
                            try:
                                subprocess.run([sys.executable, str(test_script)], check=True)
                            except subprocess.CalledProcessError:
                                console.print(safe_t('common.completed', fallback='[#E8C4F0]測試完成（部分項目未通過）[/#E8C4F0]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]執行錯誤：{e}[/red]', e=e))

                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif debug_choice == '5' and CODEBASE_EMBEDDING_ENABLED:
                        # 搜尋對話記錄
                        if not codebase_embedding:
                            console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  Codebase Embedding 未啟用[/#E8C4F0]'))
                            console.print(safe_t('common.message', fallback='[dim]   請在 config.py 中設置 EMBEDDING_ENABLE_ON_STARTUP = True 並重啟[/dim]'))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                            continue

                        # 互斥機制：如果統計模式已載入,先卸載
                        if embedding_active_mode == 'stats':
                            console.print(safe_t('common.warning', fallback='\n[#E8C4F0]⚠️  正在卸載統計模式...[/#E8C4F0]'))
                            import time
                            time.sleep(0.3)  # 視覺反饋
                            console.print(safe_t('common.completed', fallback='[#B565D8]✓ 統計模式已卸載[/#B565D8]'))
                            embedding_active_mode = None

                        # 載入搜尋模式
                        console.print(safe_t('common.loading', fallback='\n[#B565D8]🔄 載入搜尋模式...[/#B565D8]'))
                        import time
                        time.sleep(0.2)  # 視覺反饋
                        embedding_active_mode = 'search'
                        console.print(safe_t('common.message', fallback='\n[#B565D8]🔍 搜尋對話記錄[/#B565D8]'))
                        query = Prompt.ask(safe_t("chat.codegemini.search_query", fallback="\n請輸入搜尋關鍵字: "))

                        if query:
                            try:
                                results = codebase_embedding.search_conversations(query=query, top_k=5)

                                if results:
                                    console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 找到 {len(results)} 條相關對話[/#B565D8]\n', results_count=len(results)))
                                    for i, r in enumerate(results, 1):
                                        similarity = r.get('similarity', 0)
                                        console.print(safe_t('common.message', fallback='[bold COLOR_MACARON_PURPLE]═══ 結果 {i} (相似度: {similarity:.2%}) ═══[/bold COLOR_MACARON_PURPLE]', i=i, similarity=similarity))
                                        console.print(safe_t('common.message', fallback='[#E8C4F0]問題：[/#E8C4F0] {question}', question=r.get('question', 'N/A')))

                                        # 答案截斷顯示
                                        answer = r.get('answer', 'N/A')
                                        answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
                                        console.print(safe_t('common.message', fallback='[#B565D8]回答：[/#B565D8] {answer_preview}', answer_preview=answer_preview))

                                        # 顯示元數據
                                        timestamp = r.get('timestamp', 'N/A')
                                        session_id = r.get('session_id', 'N/A')
                                        console.print(safe_t('common.message', fallback='[dim]時間：{timestamp} | Session：{session_id}[/dim]\n', timestamp=timestamp, session_id=session_id))
                                else:
                                    console.print(safe_t('common.warning', fallback='\n[#E8C4F0]⚠️  未找到相關對話[/#E8C4F0]'))
                                    console.print(safe_t('common.saving', fallback='[dim]   提示：對話會在 EMBEDDING_AUTO_SAVE_CONVERSATIONS = True 時自動儲存[/dim]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]✗ 搜尋錯誤：{e}[/red]', e=e))
                                import traceback
                                traceback.print_exc()
                        else:
                            console.print(safe_t('common.message', fallback='[#E8C4F0]請輸入搜尋關鍵字[/#E8C4F0]'))

                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif debug_choice == '6' and CODEBASE_EMBEDDING_ENABLED:
                        # 查看向量資料庫統計
                        if not codebase_embedding:
                            console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  Codebase Embedding 未啟用[/#E8C4F0]'))
                            console.print(safe_t('common.message', fallback='[dim]   請在 config.py 中設置 EMBEDDING_ENABLE_ON_STARTUP = True 並重啟[/dim]'))
                            input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))
                            continue

                        try:
                            stats = codebase_embedding.get_stats()

                            console.print("\n" + "=" * 60)
                            console.print(safe_t('common.message', fallback='[bold COLOR_MACARON_PURPLE]📊 向量資料庫統計資訊[/bold COLOR_MACARON_PURPLE]'))
                            console.print("=" * 60 + "\n")

                            # 基本統計
                            total_chunks = stats.get('total_chunks', 0)
                            total_files = stats.get('total_files', 0)
                            console.print(safe_t('common.message', fallback='[#B565D8]總分塊數：[/#B565D8] {total_chunks:,}', total_chunks=total_chunks))
                            console.print(safe_t('common.message', fallback='[#B565D8]總檔案數：[/#B565D8] {total_files:,}', total_files=total_files))

                            # 分塊類型統計
                            chunk_types = stats.get('chunk_type_counts', {})
                            if chunk_types:
                                console.print(safe_t('common.message', fallback='\n[#B565D8]分塊類型分布：[/#B565D8]'))
                                for chunk_type, count in chunk_types.items():
                                    percentage = (count / total_chunks * 100) if total_chunks > 0 else 0
                                    console.print(f"  • {chunk_type}: {count:,} ({percentage:.1f}%)")

                            # 資料庫資訊
                            db_path = stats.get('db_path', 'N/A')
                            db_size_mb = stats.get('db_size_mb', 0)
                            console.print(safe_t('common.message', fallback='\n[#B565D8]資料庫路徑：[/#B565D8] {db_path}', db_path=db_path))
                            console.print(safe_t('common.message', fallback='[#B565D8]資料庫大小：[/#B565D8] {db_size_mb:.2f} MB', db_size_mb=db_size_mb))

                            # 健康狀態提示
                            if total_chunks == 0:
                                console.print(safe_t('common.message', fallback='\n[#E8C4F0]ℹ️  資料庫為空[/#E8C4F0]'))
                                console.print(safe_t('common.saving', fallback='[dim]   提示：在 config.py 中啟用 EMBEDDING_AUTO_SAVE_CONVERSATIONS 以自動儲存對話[/dim]'))
                            else:
                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 資料庫運作正常[/#B565D8]'))

                            console.print("\n" + "=" * 60)

                        except Exception as e:
                            console.print(safe_t('error.failed', fallback='\n[dim COLOR_MACARON_PURPLE_LIGHT]✗ 獲取統計失敗：{e}[/red]', e=e))
                            import traceback
                            traceback.print_exc()

                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif debug_choice == '7':
                        # 查看性能摘要
                        console.print("\n" + "=" * 60)
                        console.print(safe_t('common.message', fallback='[bold COLOR_MACARON_PURPLE]⚡ 性能監控摘要[/bold COLOR_MACARON_PURPLE]'))
                        console.print("=" * 60 + "\n")

                        try:
                            from utils.performance_monitor import get_performance_monitor
                            monitor = get_performance_monitor()
                            summary = monitor.get_summary()

                            if summary['total_operations'] == 0:
                                console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  尚無性能數據[/#E8C4F0]'))
                                console.print(safe_t('common.message', fallback='[dim]   提示：性能監控會自動追蹤主要操作的執行時間和資源使用情況[/dim]'))
                            else:
                                monitor.print_summary()

                        except Exception as e:
                            console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ 獲取性能摘要失敗：{e}[/red]', e=e))

                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif debug_choice == '8':
                        # 查看瓶頸分析報告
                        console.print("\n" + "=" * 60)
                        console.print(safe_t('common.analyzing', fallback='[bold COLOR_MACARON_PURPLE_LIGHT]🔍 瓶頸分析報告[/bold COLOR_MACARON_PURPLE_LIGHT]'))
                        console.print("=" * 60 + "\n")

                        try:
                            from utils.performance_monitor import get_performance_monitor
                            monitor = get_performance_monitor()
                            summary = monitor.get_summary()

                            if summary['total_operations'] == 0:
                                console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  尚無性能數據[/#E8C4F0]'))
                                console.print(safe_t('common.message', fallback='[dim]   提示：性能監控會自動追蹤主要操作的執行時間和資源使用情況[/dim]'))
                            else:
                                monitor.print_bottleneck_report(top_n=10)

                        except Exception as e:
                            console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ 獲取瓶頸分析失敗：{e}[/red]', e=e))

                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif debug_choice == '9':
                        # 匯出性能報告
                        console.print(safe_t('common.message', fallback='\n[#B565D8]📁 匯出性能報告[/#B565D8]\n'))

                        try:
                            from utils.performance_monitor import get_performance_monitor
                            from datetime import datetime

                            monitor = get_performance_monitor()
                            summary = monitor.get_summary()

                            if summary['total_operations'] == 0:
                                console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  尚無性能數據可匯出[/#E8C4F0]'))
                                console.print(safe_t('common.message', fallback='[dim]   提示：性能監控會自動追蹤主要操作的執行時間和資源使用情況[/dim]'))
                            else:
                                # 產生檔案名稱（帶時間戳記）
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                report_path = f"performance_report_{timestamp}.json"

                                # 匯出報告
                                monitor.export_report(report_path)

                                console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 性能報告已匯出至：[/#B565D8]{report_path}', report_path=report_path))
                                console.print(safe_t('common.message', fallback="[dim]   包含 {total_operations} 個操作的詳細統計資料[/dim]", total_operations=summary['total_operations']))

                        except Exception as e:
                            console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ 匯出報告失敗：{e}[/red]', e=e))

                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif debug_choice == '10' and TOOLS_MANAGER_AVAILABLE:
                        # 工具調用統計
                        try:
                            auto_tool_manager.print_stats(detailed=False)
                        except Exception as e:
                            console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ 獲取工具統計失敗：{e}[/red]', e=e))

                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    elif debug_choice == '11' and TOOLS_MANAGER_AVAILABLE:
                        # 工具調用詳細報告
                        try:
                            auto_tool_manager.print_stats(detailed=True)
                        except Exception as e:
                            console.print(safe_t('error.failed', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]✗ 獲取工具詳細報告失敗：{e}[/red]', e=e))

                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                    else:
                        console.print(safe_t('common.message', fallback='\n[#E8C4F0]無效選項[/#E8C4F0]'))
                        input(safe_t("chat.common.press_enter", fallback="按 Enter 繼續..."))

                continue

            # 一般對話訊息 - 完整處理流程
            # 0. 檢測長文本輸入並顯示簡潔格式（保存原始內容用於 API）
            is_long_text, display_text, original_input = format_long_input_display(user_input)
            if is_long_text:
                # 顯示簡潔格式給用戶
                console.print(f"\n[dim]{display_text}[/dim]\n")
                # 保存原始完整文本用於 API 調用
                # user_input 保持不變,繼續使用原始內容

            # 1. 解析快取即時控制
            user_input, cache_action = module_loader.get("cache").parse_cache_control(user_input, auto_cache_mgr)

            # 2. 解析思考模式配置
            user_input, use_thinking, thinking_budget, max_output_tokens = module_loader.get("thinking").parse_thinking_config(user_input, model_name)

            # 3. 處理檔案附加（文字檔直接讀取,媒體檔上傳API）
            user_input, uploaded_files = module_loader.get("file_manager").process_file_attachments(user_input)

            # 4. 處理快取即時動作
            if cache_action == 'create_now':
                if auto_cache_mgr.conversation_pairs:
                    print(safe_t("chat.cache.creating", fallback="\n⏳ 正在建立快取..."))
                    auto_cache_mgr.create_cache(model_name)
                else:
                    print(safe_t("chat.cache.no_content", fallback="⚠️  尚無對話內容可建立快取"))

            # 4.5. 智能觸發檢測（新增）
            if SMART_TRIGGERS_ENABLED:
                try:
                    # 檢測任務規劃意圖
                    if detect_task_planning_intent(user_input):
                        console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]💡 偵測到任務規劃需求,增強提示中...[/dim COLOR_MACARON_PURPLE_LIGHT]'))
                        user_input = enhance_prompt_with_context(user_input, intent="task_planning")

                    # 檢測網頁搜尋意圖
                    elif detect_web_search_intent(user_input):
                        console.print(safe_t('common.message', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]💡 偵測到網頁搜尋需求,增強提示中...[/dim COLOR_MACARON_PURPLE_LIGHT]'))
                        user_input = enhance_prompt_with_context(user_input, intent="web_search")

                    # 檢測代碼分析意圖
                    elif detect_code_analysis_intent(user_input):
                        console.print(safe_t('common.analyzing', fallback='[dim COLOR_MACARON_PURPLE_LIGHT]💡 偵測到代碼分析需求,增強提示中...[/dim COLOR_MACARON_PURPLE_LIGHT]'))
                        user_input = enhance_prompt_with_context(user_input, intent="code_analysis")

                except Exception as e:
                    logger.warning(f"智能觸發器執行失敗: {e}")
                    # 靜默失敗,不影響正常對話

            # 4.6. 工具自動偵測與準備（AutoToolManager）
            if TOOLS_MANAGER_AVAILABLE:
                try:
                    prepared_tools = prepare_tools_for_input(user_input)
                    if prepared_tools:
                        logger.debug(f"已準備工具: {', '.join(prepared_tools)}")
                except Exception as e:
                    logger.warning(f"工具自動偵測失敗: {e}")
                    # 靜默失敗,不影響正常對話

            # 5. 發送訊息
            response = send_message(
                model_name=model_name,
                user_input=user_input,
                chat_logger=chat_logger,
                use_thinking=use_thinking,
                thinking_budget=thinking_budget,
                max_output_tokens=max_output_tokens,
                uploaded_files=uploaded_files
            )

            if response is None:
                print(safe_t("chat.error.retry", fallback="發生錯誤,請重試"))
                continue

            # 6. 記錄對話到自動快取管理器（估算 tokens）
            # 粗略估算：1 token ≈ 4 characters（英文）,中文約 1.5-2 字元
            estimated_input_tokens = len(user_input) // 3
            auto_cache_mgr.add_conversation(user_input, response, estimated_input_tokens)

            # 6.5. 儲存對話到 Codebase Embedding（如果啟用）
            if codebase_embedding and config.EMBEDDING_AUTO_SAVE_CONVERSATIONS:
                try:
                    session_id = f"{config.EMBEDDING_SESSION_ID_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    codebase_embedding.add_conversation(
                        question=user_input,
                        answer=response,
                        session_id=session_id,
                        timestamp=datetime.now().isoformat()
                    )
                except Exception as e:
                    logger.debug(f"Embedding 儲存對話失敗: {e}")

            # 6.6. 更新背景待辦事項追蹤器（無痕整合）
            if background_todo_tracker and background_todo_tracker.enabled:
                try:
                    background_todo_tracker.update_from_conversation(user_input, response)
                except Exception as e:
                    logger.debug(f"背景待辦事項追蹤器更新失敗: {e}")

            # 7. 檢查是否應該觸發快取建立
            if auto_cache_mgr.should_trigger():
                if auto_cache_mgr.mode == 'auto':
                    # 自動模式：直接建立
                    print(safe_t("chat.cache.auto_threshold", fallback="\n🔔 已達快取門檻（{tokens:,} tokens）,自動建立快取...").format(tokens=auto_cache_mgr.total_input_tokens))
                    auto_cache_mgr.create_cache(model_name)
                else:
                    # 提示模式：詢問用戶
                    if auto_cache_mgr.show_trigger_prompt(model_name):
                        auto_cache_mgr.create_cache(model_name)

        except KeyboardInterrupt:
            print(f"\n\n{safe_t('chat.goodbye', fallback='再見！')}")
            try:
                chat_logger.save_session()

                # 保存使用者設定（CodeGemini 配置）
                if codegemini_config_manager:
                    try:
                        codegemini_config_manager.save_config()
                        logger.debug("✓ 設定已保存")
                    except Exception as e:
                        logger.debug(f"設定保存失敗: {e}")

                # 清理工具
                if TOOLS_MANAGER_AVAILABLE:
                    try:
                        cleanup_tools()
                        logger.debug("✓ 工具已清理")
                    except Exception as e:
                        logger.debug(f"工具清理失敗: {e}")
            except Exception as e:
                logger.debug(f"退出清理失敗: {e}")
            break
        except Exception as e:
            print(safe_t("chat.error.general", fallback="\n錯誤：{error}").format(error=e))


# ==========================================
# 記憶體管理命令處理函數
# ==========================================

def handle_clear_memory_command(chat_logger) -> str:
    """
    處理 /clear-memory 命令

    手動清理記憶體,將對話存檔到磁碟

    Args:
        chat_logger 實例

    Returns:
        'clear_memory' - 指示主迴圈記憶體已清理
        'continue' - 指示繼續對話（取消或無需清理）
    """

    # 獲取當前統計
    stats = chat_logger.conversation_manager.get_stats()
    active = stats['active_messages']

    # 顯示當前狀態
    console.print(safe_t('common.message', fallback='\n[plum]當前活躍訊息數: {active} 條[/plum]', active=active))

    if active == 0:
        console.print(safe_t('common.message', fallback='[dim]記憶體已是空的,無需清理[/dim]\n'))
        return 'continue'

    # 確認清理（保留對話記錄）
    console.print(safe_t('common.warning', fallback='\n[#E8C4F0]⚠️  清理記憶體將：[/#E8C4F0]'))
    console.print(safe_t('common.message', fallback='  • 保留當前對話到磁碟'))
    console.print(safe_t('common.message', fallback='  • 釋放記憶體中的歷史記錄'))
    console.print(safe_t('common.saving', fallback='  • 不影響已保存的對話日誌\n'))

    if Confirm.ask(safe_t('chat.confirm_clear_memory', fallback='[plum]確定要清理記憶體嗎？[/plum]'), default=False):
        # 觸發存檔（強制存檔所有訊息）
        if hasattr(chat_logger.conversation_manager, '_archive_old_messages'):
            # 先存檔所有訊息
            if len(chat_logger.conversation_manager.history) > 0:
                try:
                    # 手動存檔所有訊息
                    to_archive = chat_logger.conversation_manager.history.copy()
                    archive_file = chat_logger.conversation_manager.archive_file

                    with open(archive_file, 'a', encoding='utf-8') as f:
                        for msg in to_archive:
                            json.dump(msg, f, ensure_ascii=False)
                            f.write('\n')

                    chat_logger.conversation_manager.archived_count += len(to_archive)
                    cleared_count = len(to_archive)

                    # 清空活躍記憶體
                    chat_logger.conversation_manager.history = []

                    console.print(safe_t('common.completed', fallback='\n[green]✓ 已清理 {cleared_count} 條訊息[/green]', cleared_count=cleared_count))
                    console.print(safe_t('common.saving', fallback='[dim]記憶體已釋放,對話已保存到磁碟[/dim]\n'))
                except Exception as e:
                    console.print(safe_t('error.failed', fallback='[red]✗ 清理失敗：{e}[/red]\n', e=e))
                    return 'continue'

        return 'clear_memory'
    else:
        console.print(safe_t('common.message', fallback='[dim]已取消[/dim]\n'))
        return 'continue'


def handle_memory_stats_command(chat_logger) -> str:
    """
    處理 /memory-stats 命令

    顯示記憶體使用統計資訊

    Args:
        chat_logger 實例

    Returns:
        'show_memory_stats' - 指示主迴圈統計已顯示
    """
    from rich.table import Table

    # 獲取統計資訊
    stats = chat_logger.conversation_manager.get_stats()
    mem_info = chat_logger.conversation_manager.check_memory_usage()

    # 建立統計表格
    table = Table(title=safe_t('chat.memory_stats_title', fallback='[plum]📊 記憶體統計[/plum]'), show_header=True)
    table.add_column("項目", style="plum")
    table.add_column("數值", style="orchid1", justify="right")

    table.add_row(safe_t('chat.memory_stats_active', fallback='活躍訊息'), f"{stats['active_messages']} 條")
    table.add_row(safe_t('chat.memory_stats_archived', fallback='已存檔訊息'), f"{stats['archived_messages']} 條")
    table.add_row(safe_t('chat.memory_stats_total', fallback='總訊息數'), f"{stats['total_messages']} 條")

    # 顯示記憶體上限（如果不是無限模式）
    if stats['max_history'] != float('inf'):
        table.add_row(safe_t('chat.memory_stats_limit', fallback='記憶體上限'), f"{int(stats['max_history'])} 條")
    else:
        table.add_row(safe_t('chat.memory_stats_limit', fallback='記憶體上限'), safe_t('chat.memory_stats_unlimited', fallback='無限 ⚠️'))

    if mem_info:
        table.add_row("", "")  # 分隔線
        table.add_row(safe_t('chat.memory_stats_current', fallback='當前記憶體'), f"{mem_info['memory_gb']:.2f} GB")
        table.add_row(safe_t('chat.memory_stats_threshold', fallback='警告閾值'), f"{mem_info['threshold_gb']:.2f} GB")
        status = "[#E8C4F0]⚠️ 警告[/#E8C4F0]" if mem_info['warning'] else safe_t('chat.memory_status_normal', fallback='[green]✓ 正常[/green]')
        table.add_row(safe_t('chat.memory_stats_status', fallback='記憶體狀態'), status)

    console.print("\n")
    console.print(table)
    console.print(safe_t('common.message', fallback='\n[dim]存檔位置: {archive_file}[/dim]\n', archive_file=stats['archive_file']))

    return 'show_memory_stats'


def handle_memory_help_command() -> str:
    """
    處理 /help-memory 命令

    顯示記憶體管理命令的說明

    Returns:
        'continue' - 指示繼續對話
    """
    from rich import box

    help_text = """[plum]記憶體管理命令[/plum]

[orchid1]/clear-memory[/orchid1]
  手動清理記憶體,保存對話到磁碟
  • 不會丟失任何對話記錄
  • 釋放記憶體空間
  • 需要確認操作

[orchid1]/memory-stats[/orchid1]
  查看記憶體使用統計
  • 活躍訊息數量
  • 已存檔訊息數量
  • 當前記憶體使用量

[orchid1]/help-memory[/orchid1]
  顯示此說明訊息

[dim]提示：系統會自動管理記憶體,僅在收到警告時才需要手動清理。[/dim]
"""

    console.print(Panel(help_text, border_style="plum", box=box.ROUNDED))
    return 'continue'


# ============================================================================
# 檢查點系統命令處理
# ============================================================================

def handle_checkpoints_command() -> str:
    """
    處理 /checkpoints 命令

    顯示所有檢查點清單

    Returns:
        'continue' - 指示繼續對話
    """
    if not CHECKPOINT_ENABLED:
        console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  檢查點系統未啟用[/#E8C4F0]'))
        return 'continue'

    try:
        manager = get_checkpoint_manager()
        manager.show_checkpoints_ui(limit=20)
        console.print(safe_t('common.message', fallback='\n[dim]使用 /rewind <ID> 回溯至指定檢查點[/dim]'))
        console.print(safe_t('common.message', fallback='[dim]使用 /checkpoint <描述> 建立手動檢查點[/dim]\n'))
    except Exception as e:
        console.print(safe_t('error.failed', fallback='[red]✗[/red] 檢查點系統錯誤: {e}', e=e))

    return 'continue'


def handle_rewind_command(checkpoint_id: str) -> str:
    """
    處理 /rewind 命令

    回溯至指定檢查點

    Args:
        checkpoint_id: 檢查點 ID（可為部分 ID）

    Returns:
        'continue' - 指示繼續對話
    """
    if not CHECKPOINT_ENABLED:
        console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  檢查點系統未啟用[/#E8C4F0]'))
        return 'continue'

    if not checkpoint_id:
        console.print(safe_t('common.message', fallback='[#E8C4F0]請指定檢查點 ID[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='[dim]範例: /rewind a1b2c3d4[/dim]\n'))
        return 'continue'

    try:
        manager = get_checkpoint_manager()
        success = manager.rewind_to_checkpoint(checkpoint_id, confirm=True)

        if success:
            console.print(safe_t('common.completed', fallback='\n[green]✓[/green] 回溯成功！'))
        else:
            console.print(safe_t('error.failed', fallback='\n[#E8C4F0]回溯失敗或已取消[/#E8C4F0]'))

    except Exception as e:
        console.print(safe_t('error.failed', fallback='[red]✗[/red] 回溯錯誤: {e}', e=e))

    return 'continue'


def handle_checkpoint_command(description: str = "") -> str:
    """
    處理 /checkpoint 命令

    建立手動檢查點

    Args:
        description: 檢查點描述

    Returns:
        'continue' - 指示繼續對話
    """
    if not CHECKPOINT_ENABLED:
        console.print(safe_t('common.warning', fallback='[#E8C4F0]⚠️  檢查點系統未啟用[/#E8C4F0]'))
        return 'continue'

    try:

        # 如果沒有提供描述,詢問使用者
        if not description:
            description = Prompt.ask(safe_t('chat.checkpoint_description_prompt', fallback='\n[#87CEEB]請輸入檢查點描述[/#87CEEB]'), default=safe_t('chat.checkpoint_default_name', fallback='手動檢查點'))

        # 掃描當前專案檔案（這裡簡化為空列表,實際應掃描最近修改的檔案）
        # TODO: 整合檔案監控系統,自動偵測變更的檔案
        console.print(safe_t('common.message', fallback='\n[#87CEEB]建立檢查點...[/#87CEEB]'))
        console.print(safe_t('common.message', fallback='[dim]描述: {description}[/dim]\n', description=description))

        manager = get_checkpoint_manager()

        # 暫時建立空檢查點（未來整合檔案監控）
        # Checkpoint, FileChange 已在頂部導入
        checkpoint = manager.create_checkpoint(
            file_changes=[],  # 空變更列表
            description=description,
            checkpoint_type=CheckpointType.MANUAL
        )

        console.print(safe_t('common.completed', fallback='[green]✓[/green] 檢查點已建立: [#87CEEB]{checkpoint.id[:8]}[/#87CEEB]', checkpoint_id=checkpoint.id[:8]))
        console.print(safe_t('common.message', fallback='[dim]使用 /checkpoints 查看所有檢查點[/dim]\n'))

    except Exception as e:
        console.print(safe_t('error.failed', fallback='[red]✗[/red] 建立檢查點失敗: {e}', e=e))

    return 'continue'


def handle_checkpoint_help_command() -> str:
    """
    處理 /help-checkpoint 命令

    顯示檢查點系統說明

    Returns:
        'continue' - 指示繼續對話
    """
    from rich import box

    help_text = """[#87CEEB]檢查點系統命令[/#87CEEB]

[bright_cyan]/checkpoints[/bright_cyan]
  列出所有檢查點
  • 顯示檢查點 ID、時間、描述
  • 顯示檔案變更數量
  • 最多顯示 20 個最近的檢查點

[bright_cyan]/rewind <ID>[/bright_cyan]
  回溯至指定檢查點
  • 恢復檔案至檢查點狀態
  • 支援部分 ID 匹配（例如：a1b2c3d4）
  • 需要確認操作

[bright_cyan]/checkpoint <描述>[/bright_cyan]
  建立手動檢查點
  • 保存當前狀態
  • 可添加自訂描述
  • 用於重要變更前的備份

[bright_cyan]/help-checkpoint[/bright_cyan]
  顯示此說明訊息

[bold COLOR_MACARON_PURPLE_LIGHT]檢查點類型：[/bold COLOR_MACARON_PURPLE_LIGHT]
  🤖 [dim]auto[/dim]     - 自動檢查點（檔案變更前）
  👤 [dim]manual[/dim]   - 手動檢查點（使用者建立）
  📸 [dim]snapshot[/dim] - 完整快照（非增量）
  🌿 [dim]branch[/dim]   - 分支檢查點（實驗性變更）

[dim]提示：檢查點儲存於 .checkpoints/ 目錄,使用 SQLite + gzip 壓縮[/dim]
"""

    console.print(Panel(help_text, border_style="COLOR_FORGET_ME_NOT", box=box.ROUNDED))
    return 'continue'


def main():
    """主程式"""
    console.print(safe_t('common.message', fallback='[bold COLOR_MACARON_PURPLE]Gemini 對話工具（新 SDK 版本）[/bold COLOR_MACARON_PURPLE]\n'))

    # 啟動 CodeGemini 背景載入（不阻塞啟動）
    if CODEGEMINI_ENABLED:
        start_background_codegemini_loading()
        logger.debug("已啟動 CodeGemini 背景載入")

    # 🆕 啟動背景更新檢查（非阻塞,輕量）
    if config.get('UPDATE_CHECK_ENABLED', True) and config.get('UPDATE_CHECK_ON_STARTUP', True):
        try:
            from gemini_updater import start_background_update_check
            start_background_update_check()
            logger.debug("已啟動背景更新檢查")
        except Exception as e:
            logger.debug(f"更新檢查模組載入失敗: {e}")

    # 🔴 無限記憶體模式警告
    if config.UNLIMITED_MEMORY_MODE:
        console.print(Panel(
            "[bold red]🔴 警告：無限記憶體模式已啟用！[/bold red]\n\n"
            "[#E8C4F0]您已選擇「我就是要用爆記憶體」模式。[/#E8C4F0]\n\n"
            "記憶體管理功能已完全停用：\n"
            "  ❌ 自動清理機制已停用\n"
            "  ❌ 記憶體警告已停用\n"
            "  ❌ 對話歷史限制已移除\n\n"
            "[bold]風險：[/bold]\n"
            "  • 長時間運行可能導致記憶體溢出（OOM）\n"
            "  • 可能導致系統變慢或程式崩潰\n"
            "  • 記憶體使用可能超過 4GB+\n\n"
            "[dim]如需停用無限模式,請在 config.py 中設定：[/dim]\n"
            "[dim]UNLIMITED_MEMORY_MODE = False[/dim]\n\n"
            "[#B565D8]使用 /memory-stats 命令監控記憶體使用[/#B565D8]",
            border_style="red",
            title="⚠️ 危險模式警告",
            padding=(1, 2)
        ))
        console.print()  # 空行

    # 建立對話記錄器
    chat_logger = module_loader.get("logger").ChatLogger()

    # 初始化思考簽名管理器
    global global_thinking_signature_manager
    global_thinking_signature_manager = module_loader.get("thinking").ThinkingSignatureManager()

    # 初始化 Codebase Embedding（如果啟用）
    codebase_embedding = None
    if CODEBASE_EMBEDDING_ENABLED and config.EMBEDDING_ENABLE_ON_STARTUP:
        try:
            cg = CodeGemini()
            codebase_embedding = cg.enable_codebase_embedding(
                vector_db_path=config.EMBEDDING_VECTOR_DB_PATH,
                api_key=API_KEY
            )
            console.print(safe_t('common.completed', fallback='[#B565D8]✓ Codebase Embedding 已啟用[/#B565D8]'))
        except Exception as e:
            console.print(safe_t('error.failed', fallback='[#E8C4F0]⚠️  Codebase Embedding 啟用失敗: {e}[/#E8C4F0]', e=e))
            codebase_embedding = None

    # 選擇模型（優先使用保存的模型或 CLI 參數）
    model_selector = module_loader.get("model_selector")

    # CLI 參數優先
    if args.model:
        console.print(safe_t('model.cli_override', fallback='[dim]使用 CLI 指定的模型: {model}[/dim]', model=args.model))
        current_model = args.model
        # 保存 CLI 指定的模型
        model_selector._save_model_choice(args.model)
    else:
        # 嘗試讀取上次保存的模型
        last_model = model_selector.get_last_selected_model()

        if last_model:
            # 🔧 自動遷移舊模型名稱：flash-8b → flash-lite
            if 'flash-8b' in last_model:
                old_model = last_model
                last_model = last_model.replace('flash-8b', 'flash-lite')
                console.print(safe_t('model.migrated',
                    fallback='[dim]⚠️  模型名稱已更新: {old} → {new}[/dim]',
                    old=old_model, new=last_model))
                # 保存更新後的模型名稱
                model_selector._save_model_choice(last_model)

            console.print(safe_t('model.using_saved', fallback='[dim]使用上次選擇的模型: {model}[/dim]', model=last_model))
            current_model = last_model
        else:
            # 沒有保存的模型,顯示選單
            current_model = model_selector.select_model()

    # 配置自動快取
    auto_cache_config = setup_auto_cache(current_model)

    # 處理返回和重選模型
    while auto_cache_config.get('reselect_model') or auto_cache_config.get('go_back'):
        if auto_cache_config.get('go_back'):
            # 返回到模型選擇
            current_model = model_selector.select_model()
        elif auto_cache_config.get('reselect_model'):
            # 重新選擇模型
            current_model = model_selector.select_model()

        # 重新配置快取
        auto_cache_config = setup_auto_cache(current_model)

    while True:
        result = chat(current_model, chat_logger, auto_cache_config, codebase_embedding)

        if result == 'switch_model':
            current_model = module_loader.get("model_selector").select_model()
            # 切換模型後重新配置快取（因為不同模型有不同門檻）
            auto_cache_config = setup_auto_cache(current_model)
        elif result == 'clear_memory':
            # 記憶體已清理,繼續對話
            console.print(safe_t('common.completed', fallback='[green]✓ 記憶體清理完成,繼續對話[/green]\n'))
            continue
        elif result == 'show_memory_stats':
            # 統計已顯示,繼續對話
            continue
        elif result == 'continue':
            # 繼續對話（用於取消操作或顯示說明後）
            continue
        else:
            break

    # 正常退出時保存設定
    print(f"\n{safe_t('chat.goodbye', fallback='再見！')}")

    # 保存對話記錄
    chat_logger.save_session()

    # 保存使用者設定（CodeGemini 配置）
    if codegemini_config_manager:
        try:
            codegemini_config_manager.save_config()
            logger.debug("✓ 設定已保存")
        except Exception as e:
            logger.debug(f"設定保存失敗: {e}")

    # 清理工具
    if TOOLS_MANAGER_AVAILABLE:
        try:
            cleanup_tools()
            logger.debug("✓ 工具已清理")
        except Exception as e:
            logger.debug(f"工具清理失敗: {e}")


if __name__ == "__main__":
    import argparse

    # 命令列參數解析
    parser = argparse.ArgumentParser(
        description='ChatGemini_SakiTool - Gemini 對話工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python gemini_chat.py                # 正常啟動對話
  python gemini_chat.py --config       # 啟動互動式配置精靈
  python gemini_chat.py --setup        # 同 --config（別名）

互動式配置精靈說明:
  首次使用或想要調整配置時,可以使用 --config 參數啟動友善的配置引導介面。
  配置精靈會引導您：
  - 選擇預設模型
  - 啟用/停用功能模組（計價、快取、翻譯等）
  - 設定進階參數（匯率、快取門檻等）
  - 自動生成 config.py 檔案

  配置完成後,您隨時可以手動編輯 config.py 調整設定。
        """
    )
    parser.add_argument(
        '--config', '--setup',
        action='store_true',
        dest='config_mode',
        help='啟動互動式配置精靈（首次使用或調整設定時使用）'
    )
    parser.add_argument(
        '--model', '-m',
        type=str,
        dest='model',
        help='指定使用的模型（覆寫保存的預設模型）。例如: --model gemini-2.5-pro'
    )

    args = parser.parse_args()

    # 如果使用 --config 參數,啟動互動式配置
    if args.config_mode:
        console.print(Panel(
            "[bold magenta]互動式配置模式[/bold magenta]\n\n"
            "[dim]此模式將引導您完成配置設定。\n"
            "配置完成後,請再次執行程式開始對話。[/dim]",
            title="[bold magenta]🎛️  配置精靈[/bold magenta]",
            border_style="magenta"
        ))

        config_ui = module_loader.get("config_ui").ConfigUI()
        result = config_ui.interactive_setup()

        if result:
            console.print(safe_t('common.completed', fallback='\n[bold green]✅ 配置完成！[/bold green]'))
            console.print(safe_t('common.message', fallback='[dim]請再次執行 python gemini_chat.py 開始對話[/dim]\n'))
        else:
            console.print(safe_t('common.message', fallback='\n[#E8C4F0]配置已取消[/#E8C4F0]\n'))

        sys.exit(0)

    # 正常模式：啟動對話
    main()
