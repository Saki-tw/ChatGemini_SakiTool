#!/usr/bin/env python3
"""
ChatGemini_SakiTool - Gemini 對話腳本 v2.0
完全使用新 SDK (google-genai)
支援功能：
- 思考模式（動態控制）
- 新台幣計價
- 對話記錄
- 快取自動管理
- 檔案附加
- 增強型輸入（方向鍵、歷史）
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
from rich.markdown import Markdown
from rich.panel import Panel

# ==========================================
# 載入配置檔案（可選）
# ==========================================
try:
    import config
    CONFIG_AVAILABLE = True
    print("✅ 已載入 config.py 配置")
except ImportError:
    CONFIG_AVAILABLE = False
    # 如果 config.py 不存在，使用預設配置
    class config:
        """預設配置（當 config.py 不存在時使用）"""
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

# 終端機輸入增強
try:
    from prompt_toolkit import prompt, PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter, Completer, Completion
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.lexers import PygmentsLexer
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False
    print("⚠️  建議安裝 prompt-toolkit 以獲得更好的輸入體驗")
    print("   執行: pip install prompt-toolkit")

# 新 SDK
from google import genai
from google.genai import types

# ==========================================
# 根據 config.py 動態導入模組
# ==========================================

# 導入計價系統
if config.MODULES.get('pricing', {}).get('enabled', True):
    try:
        from gemini_pricing import PricingCalculator, USD_TO_TWD as PRICING_USD_TO_TWD
        PRICING_ENABLED = True
    except ImportError:
        PRICING_ENABLED = False
        PRICING_USD_TO_TWD = config.USD_TO_TWD
        print("提示：gemini_pricing.py 不存在，計價功能已停用")
else:
    PRICING_ENABLED = False
    PRICING_USD_TO_TWD = config.USD_TO_TWD
    print("ℹ️  計價功能已在 config.py 中停用")

# 使用配置檔案中的匯率或模組中的匯率
USD_TO_TWD = PRICING_USD_TO_TWD if PRICING_ENABLED else config.USD_TO_TWD

# 導入快取管理器
if config.MODULES.get('cache_manager', {}).get('enabled', True):
    try:
        from gemini_cache_manager import CacheManager
        CACHE_ENABLED = True
    except ImportError:
        CACHE_ENABLED = False
        print("提示：gemini_cache_manager.py 不存在，快取功能已停用")
else:
    CACHE_ENABLED = False
    print("ℹ️  快取功能已在 config.py 中停用")

# 導入檔案管理器
if config.MODULES.get('file_manager', {}).get('enabled', True):
    try:
        from gemini_file_manager import FileManager
        FILE_MANAGER_ENABLED = True
    except ImportError:
        FILE_MANAGER_ENABLED = False
        print("提示：gemini_file_manager.py 不存在，檔案上傳功能已停用")
else:
    FILE_MANAGER_ENABLED = False
    print("ℹ️  檔案管理功能已在 config.py 中停用")

# 導入翻譯器
if config.MODULES.get('translator', {}).get('enabled', True):
    try:
        from gemini_translator import get_translator
        TRANSLATOR_ENABLED = True
        global_translator = get_translator()
    except ImportError:
        TRANSLATOR_ENABLED = False
        global_translator = None
        print("提示：gemini_translator.py 不存在，翻譯功能已停用")
else:
    TRANSLATOR_ENABLED = False
    global_translator = None
    print("ℹ️  翻譯功能已在 config.py 中停用")

# 導入影音相關模組 - Flow Engine
if config.MODULES.get('flow_engine', {}).get('enabled', False):
    try:
        from gemini_flow_engine import FlowEngine
        FLOW_ENGINE_ENABLED = True
    except ImportError:
        FLOW_ENGINE_ENABLED = False
        print("提示：gemini_flow_engine.py 不存在，Flow 引擎功能已停用")
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

# 導入媒體查看器 - Media Viewer
try:
    from gemini_media_viewer import MediaViewer
    MEDIA_VIEWER_ENABLED = True
except ImportError:
    MEDIA_VIEWER_ENABLED = False

# 導入影片特效處理器 - Video Effects
if config.MODULES.get('video_effects', {}).get('enabled', False):
    try:
        from gemini_video_effects import VideoEffects
        VIDEO_EFFECTS_ENABLED = True
    except ImportError:
        VIDEO_EFFECTS_ENABLED = False
else:
    VIDEO_EFFECTS_ENABLED = False

# 導入 CodeGemini（Gemini CLI 管理）- 不受 config.py 控制，始終嘗試載入
try:
    from CodeGemini import CodeGemini
    CODEGEMINI_ENABLED = True
except ImportError:
    CODEGEMINI_ENABLED = False

# 導入 Codebase Embedding（根據 config.py 控制）
global_codebase_embedding = None
if config.MODULES.get('codebase_embedding', {}).get('enabled', False):
    if CODEGEMINI_ENABLED:
        try:
            # 初始化 CodebaseEmbedding
            codegemini_instance = CodeGemini()
            API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            global_codebase_embedding = codegemini_instance.enable_codebase_embedding(
                vector_db_path=os.path.expanduser("~/.gemini/embeddings"),
                api_key=API_KEY,
                orthogonal_mode=True,  # 啟用正交模式，自動去重
                similarity_threshold=0.85
            )
            CODEBASE_EMBEDDING_ENABLED = True
            print("✅ Codebase Embedding 已啟用")
        except Exception as e:
            CODEBASE_EMBEDDING_ENABLED = False
            global_codebase_embedding = None
            print(f"提示：Codebase Embedding 初始化失敗: {e}")
    else:
        CODEBASE_EMBEDDING_ENABLED = False
        print("提示：Codebase Embedding 需要 CodeGemini 模組")
else:
    CODEBASE_EMBEDDING_ENABLED = False

# 導入智能觸發器（無痕整合 CodeGemini 功能）
try:
    from gemini_smart_triggers import (
        auto_enhance_prompt,
        BackgroundTodoTracker
    )
    SMART_TRIGGERS_ENABLED = True
    print("✅ 智能觸發器已啟用（無痕整合）")
except ImportError:
    SMART_TRIGGERS_ENABLED = False
    print("提示：gemini_smart_triggers.py 不存在，智能觸發功能已停用")

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
        suggest_translator_dependency_missing,

        # 媒體處理相關
        suggest_cannot_get_duration,
        suggest_missing_stream,
        suggest_no_video_stream,
        suggest_corrupted_file,

        # JSON 相關
        auto_fix_json,
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
    print("✅ 錯誤修復建議系統已啟用")
except ImportError:
    ERROR_FIX_ENABLED = False
    global_error_logger = None
    print("提示：error_fix_suggestions.py 不存在，錯誤修復建議已停用")

# ========== 進階功能自動整合 ==========

# 導入 API 自動重試機制
if config.MODULES.get('api_retry', {}).get('enabled', True):
    try:
        from api_retry_wrapper import with_retry, APIRetryConfig
        API_RETRY_ENABLED = True
        print("✅ API 自動重試機制已啟用")
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
        print("✅ 智能錯誤診斷系統已啟用")
    except ImportError:
        ERROR_DIAGNOSTICS_ENABLED = False
        global_error_diagnostics = None
else:
    ERROR_DIAGNOSTICS_ENABLED = False
    global_error_diagnostics = None

# 導入相關對話建議系統
if config.MODULES.get('conversation_suggestion', {}).get('enabled', True):
    try:
        from gemini_conversation_suggestion import ConversationSuggestion
        CONVERSATION_SUGGESTION_ENABLED = True
        # 初始化（如果 Codebase Embedding 已啟用）
        if CODEBASE_EMBEDDING_ENABLED and global_codebase_embedding:
            global_conversation_suggestion = ConversationSuggestion(
                embedding=global_codebase_embedding,
                enabled=True,
                top_k=3,
                min_similarity=0.7
            )
            print("✅ 相關對話建議系統已啟用")
        else:
            global_conversation_suggestion = None
            CONVERSATION_SUGGESTION_ENABLED = False
            print("⚠️  相關對話建議需要 Codebase Embedding 啟用")
    except ImportError:
        CONVERSATION_SUGGESTION_ENABLED = False
        global_conversation_suggestion = None
else:
    CONVERSATION_SUGGESTION_ENABLED = False
    global_conversation_suggestion = None

# 導入智能觸發器（自動增強提示）
if config.MODULES.get('smart_triggers', {}).get('enabled', True):
    try:
        import gemini_smart_triggers
        SMART_TRIGGERS_ENABLED = True
        print("✅ 智能觸發器已啟用（自動檢測意圖）")
    except ImportError:
        SMART_TRIGGERS_ENABLED = False
else:
    SMART_TRIGGERS_ENABLED = False

# 導入性能優化模組
if config.MODULES.get('performance_optimization', {}).get('enabled', True):
    try:
        from gemini_performance import cached, LRUCache
        PERFORMANCE_OPT_ENABLED = True
        print("✅ 性能優化模組已啟用")
    except ImportError:
        PERFORMANCE_OPT_ENABLED = False
else:
    PERFORMANCE_OPT_ENABLED = False

# 導入媒體查看器（附加檔案時自動顯示資訊）
if config.MODULES.get('media_viewer', {}).get('enabled', True):
    try:
        from gemini_media_viewer import MediaViewer
        MEDIA_VIEWER_AUTO_ENABLED = True
        global_media_viewer = MediaViewer()
        print("✅ 媒體查看器已啟用（附加檔案時自動顯示資訊）")
    except ImportError:
        MEDIA_VIEWER_AUTO_ENABLED = False
        global_media_viewer = None
else:
    MEDIA_VIEWER_AUTO_ENABLED = False
    global_media_viewer = None

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

# 從環境變數獲取 API 金鑰
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    logger.error("未找到 GEMINI_API_KEY 環境變數")
    # 使用錯誤修復建議系統
    if ERROR_FIX_ENABLED:
        suggest_api_key_setup()
    else:
        print("錯誤：請設置 GEMINI_API_KEY 環境變數")
        print("請在 .env 文件中添加：GEMINI_API_KEY=你的API金鑰")
    sys.exit(1)

# 配置新 SDK客戶端
client = genai.Client(api_key=API_KEY)

# 常數定義
# 對話記錄統一儲存路徑
DEFAULT_LOG_DIR = os.path.join(os.path.expanduser("~"), "SakiStudio", "ChatGemini", "ChatLOG")

DEFAULT_MODEL = 'gemini-2.5-flash'
MAX_CONTEXT_TOKENS = 2000000

# 初始化
console = Console()
if PRICING_ENABLED:
    global_pricing_calculator = PricingCalculator()
if CACHE_ENABLED:
    global_cache_manager = CacheManager()
if FILE_MANAGER_ENABLED:
    global_file_manager = FileManager()

# 思考簽名管理器（用於多輪對話脈絡維護）
global_thinking_signature_manager = None  # 將在需要時初始化

# 思考過程顯示配置（全域）
SHOW_THINKING_PROCESS = False  # 預設隱藏，但會抓取，按 Ctrl+T 可切換顯示
LAST_THINKING_PROCESS = None   # 儲存最近一次的思考過程（英文原文）
LAST_THINKING_TRANSLATED = None  # 儲存最近一次的翻譯（繁體中文）
CTRL_T_PRESS_COUNT = 0  # Ctrl+T 按壓次數（0=未顯示, 1=顯示翻譯, 2=顯示雙語）

# 推薦的模型列表
RECOMMENDED_MODELS: Dict[str, tuple] = {
    '1': ('gemini-2.5-pro', 'Gemini 2.5 Pro - 最強大（思考模式）'),
    '2': ('gemini-2.5-flash', 'Gemini 2.5 Flash - 快速且智慧（推薦）'),
    '3': ('gemini-2.5-flash-8b', 'Gemini 2.5 Flash-8B - 最便宜'),
    '4': ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash - 快速版'),
}

# 支援思考模式的模型
THINKING_MODELS = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-8b']

# 各模型的最低快取門檻要求（tokens）
# 根據 Gemini API Context Caching 規範
MIN_TOKENS = {
    'gemini-2.5-pro': 4096,           # Pro 版本需要更多
    'gemini-2.5-flash': 1024,         # Flash 版本標準
    'gemini-2.5-flash-8b': 1024,      # Flash-8B 版本標準
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
            self.commands = ['cache', 'media', 'video', 'veo', 'model', 'clear', 'exit', 'help', 'debug', 'test']
            if CODEGEMINI_ENABLED:
                self.commands.extend(['cli', 'gemini-cli'])
            if CODEBASE_EMBEDDING_ENABLED:
                self.commands.extend(['/search_code', '/search_history'])

            # 思考模式語法提示
            self.think_patterns = [
                '[think:auto]',
                '[think:1000]',
                '[think:2000]',
                '[think:5000]',
                '[think:1000,response:500]',
                '[no-think]'
            ]

        def get_completions(self, document, complete_event):
            word = document.get_word_before_cursor()
            text = document.text_before_cursor

            # 1. 思考模式語法補全
            if '[think' in text.lower() or word.startswith('['):
                for pattern in self.think_patterns:
                    if pattern.lower().startswith(word.lower()):
                        yield Completion(
                            pattern,
                            start_position=-len(word),
                            display_meta='思考模式語法'
                        )

            # 2. 指令補全
            elif not text or text.isspace() or (len(text) < 10 and not any(c in text for c in '[/@')):
                for cmd in self.commands:
                    if cmd.lower().startswith(word.lower()):
                        yield Completion(
                            cmd,
                            start_position=-len(word),
                            display_meta='指令'
                        )

    command_completer = SmartCompleter()

    # 創建輸入樣式（馬卡龍紫色系）
    input_style = Style.from_dict({
        'prompt': '#b19cd9 bold',  # 馬卡龍薰衣草紫
        'multiline': '#c8b1e4 italic',  # 淡紫色
    })

    # 創建按鍵綁定
    key_bindings = KeyBindings()

    @key_bindings.add('c-t')
    def toggle_thinking_display(event):
        """Ctrl+T: 切換思考過程顯示（循環：隱藏 → 翻譯 → 雙語對照）"""
        global SHOW_THINKING_PROCESS, LAST_THINKING_PROCESS, LAST_THINKING_TRANSLATED, CTRL_T_PRESS_COUNT

        # 沒有思考過程時提示
        if not LAST_THINKING_PROCESS:
            console.print("\n[magenta]💭 尚未產生思考過程[/magenta]\n")
            event.app.current_buffer.insert_text("")
            return

        # 循環切換：0(隱藏) → 1(翻譯) → 2(雙語) → 0
        CTRL_T_PRESS_COUNT = (CTRL_T_PRESS_COUNT + 1) % 3

        if CTRL_T_PRESS_COUNT == 1:
            # 第一次按下：顯示翻譯（或原文）
            SHOW_THINKING_PROCESS = True
            console.print("\n[bright_magenta]━━━ 🧠 思考過程（翻譯） ━━━[/bright_magenta]")

            # 如果有翻譯且翻譯功能啟用，顯示翻譯；否則顯示原文
            if TRANSLATOR_ENABLED and global_translator and LAST_THINKING_TRANSLATED:
                console.print(f"[dim]{LAST_THINKING_TRANSLATED}[/dim]")
            else:
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
                if TRANSLATOR_ENABLED and global_translator:
                    console.print("[dim magenta]💡 提示：翻譯功能可能未啟用或無可用引擎[/dim magenta]")

            console.print("[bright_magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━[/bright_magenta]\n")

        elif CTRL_T_PRESS_COUNT == 2:
            # 第二次按下：顯示雙語對照
            console.print("\n[bright_magenta]━━━ 🧠 思考過程（雙語對照） ━━━[/bright_magenta]")

            if TRANSLATOR_ENABLED and global_translator and LAST_THINKING_TRANSLATED:
                console.print("[bold bright_magenta]🇹🇼 繁體中文：[/bold bright_magenta]")
                console.print(f"[dim]{LAST_THINKING_TRANSLATED}[/dim]\n")
                console.print("[bold bright_magenta]🇬🇧 英文原文：[/bold bright_magenta]")
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
            else:
                console.print("[bold bright_magenta]🇬🇧 英文原文：[/bold bright_magenta]")
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
                if TRANSLATOR_ENABLED and global_translator:
                    console.print("[dim magenta]💡 提示：翻譯功能可能未啟用或無可用引擎[/dim magenta]")

            console.print("[bright_magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━[/bright_magenta]\n")

        else:
            # 第三次按下：隱藏
            SHOW_THINKING_PROCESS = False
            console.print("\n[magenta]💭 思考過程已隱藏[/magenta]\n")

        event.app.current_buffer.insert_text("")  # 保持輸入狀態

    @key_bindings.add('escape', 'enter')
    def insert_newline(event):
        """Alt+Enter: 插入新行（多行編輯）"""
        event.app.current_buffer.insert_text('\n')

    @key_bindings.add('c-d')
    def show_help_hint(event):
        """Ctrl+D: 顯示輸入提示"""
        console.print("\n[bright_magenta]💡 輸入提示：[/bright_magenta]")
        console.print("  • [bold]Alt+Enter[/bold] - 插入新行（多行輸入）")
        console.print("  • [bold]Ctrl+T[/bold] - 切換思考過程顯示")
        console.print("  • [bold]↑/↓[/bold] - 瀏覽歷史記錄")
        console.print("  • [bold]Tab[/bold] - 自動補全指令與語法")
        console.print("  • [bold][think:1000,response:500][/bold] - 指定思考與回應 tokens")
        console.print()
        event.app.current_buffer.insert_text("")


def extract_thinking_process(response) -> Optional[str]:
    """
    從回應中提取思考過程內容

    Args:
        response: Gemini API 回應物件

    Returns:
        思考過程文字，如果不存在則回傳 None
    """
    try:
        if not hasattr(response, 'candidates') or not response.candidates:
            return None

        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
            return None

        # 遍歷所有 parts，查找思考內容
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


def parse_thinking_config(user_input: str, model_name: str = "") -> tuple:
    """
    解析思考模式配置

    支援格式:
    - [think:2000] 使用指定 tokens 思考
    - [think:1000,response:500] 同時指定思考與回應 tokens
    - [think:auto] 或 [think:-1] 動態思考
    - [no-think] 或 [think:0] 不思考（部分模型支援）

    各模型限制：
    - gemini-2.5-pro: -1 (動態) 或 128-32768 tokens，無法停用
    - gemini-2.5-flash: -1 (動態) 或 0-24576 tokens，0=停用
    - gemini-2.5-flash-8b (lite): -1 (動態) 或 512-24576 tokens，0=停用

    Args:
        user_input: 使用者輸入
        model_name: 模型名稱

    Returns:
        (清理後的輸入, 是否使用思考, 思考預算, 最大輸出tokens)
    """
    # 根據模型判斷限制
    is_pro = 'pro' in model_name.lower()
    is_lite = '8b' in model_name.lower() or 'lite' in model_name.lower()

    # 設定各模型的限制
    if is_pro:
        MAX_TOKENS = 32768
        MIN_TOKENS = 128
        ALLOW_DISABLE = False  # Pro 無法停用思考
    elif is_lite:
        MAX_TOKENS = 24576
        MIN_TOKENS = 512
        ALLOW_DISABLE = True
    else:  # flash
        MAX_TOKENS = 24576
        MIN_TOKENS = 0
        ALLOW_DISABLE = True

    # 預設值
    use_thinking = True
    thinking_budget = -1  # 動態
    max_output_tokens = None  # None 表示使用模型預設值

    # 檢查是否禁用思考
    no_think_pattern = r'\[no-think\]'
    if re.search(no_think_pattern, user_input, re.IGNORECASE):
        if not ALLOW_DISABLE:
            print(f"⚠️  {model_name} 不支援停用思考，將使用動態模式")
            thinking_budget = -1
        else:
            thinking_budget = 0
        user_input = re.sub(no_think_pattern, '', user_input, flags=re.IGNORECASE).strip()
        return user_input, use_thinking, thinking_budget, max_output_tokens

    # 檢查帶 response 參數的思考預算: [think:1000,response:500]
    think_response_pattern = r'\[think:(-?\d+|auto),\s*response:(\d+)\]'
    match = re.search(think_response_pattern, user_input, re.IGNORECASE)
    if match:
        budget_str = match.group(1).lower()
        response_tokens = int(match.group(2))

        # 處理思考預算
        if budget_str == 'auto':
            thinking_budget = -1
        else:
            thinking_budget = int(budget_str)

            # 驗證思考預算範圍
            if thinking_budget == 0:
                if not ALLOW_DISABLE:
                    print(f"⚠️  {model_name} 不支援停用思考（0 tokens），已調整為最小值 {MIN_TOKENS} tokens")
                    thinking_budget = MIN_TOKENS
            elif thinking_budget == -1:
                pass  # 保持 -1
            elif thinking_budget < MIN_TOKENS:
                print(f"⚠️  思考預算低於最小值 {MIN_TOKENS} tokens，已調整")
                thinking_budget = MIN_TOKENS
            elif thinking_budget > MAX_TOKENS:
                print(f"⚠️  思考預算超過上限 {MAX_TOKENS:,} tokens，已調整為最大值")
                thinking_budget = MAX_TOKENS

        # 設定輸出 tokens（最大 8192）
        if response_tokens < 1:
            print(f"⚠️  回應 tokens 至少為 1，已調整")
            max_output_tokens = 1
        elif response_tokens > 8192:
            print(f"⚠️  回應 tokens 超過上限 8192，已調整為最大值")
            max_output_tokens = 8192
        else:
            max_output_tokens = response_tokens

        user_input = re.sub(think_response_pattern, '', user_input, flags=re.IGNORECASE).strip()
        return user_input, use_thinking, thinking_budget, max_output_tokens

    # 檢查單獨的思考預算: [think:2000]
    think_pattern = r'\[think:(-?\d+|auto)\]'
    match = re.search(think_pattern, user_input, re.IGNORECASE)
    if match:
        budget_str = match.group(1).lower()
        if budget_str == 'auto':
            thinking_budget = -1
        else:
            thinking_budget = int(budget_str)

            # 處理停用請求 (0)
            if thinking_budget == 0:
                if not ALLOW_DISABLE:
                    print(f"⚠️  {model_name} 不支援停用思考（0 tokens），已調整為最小值 {MIN_TOKENS} tokens")
                    thinking_budget = MIN_TOKENS
                # else: thinking_budget = 0 保持不變
            # 處理動態請求 (-1)
            elif thinking_budget == -1:
                pass  # 保持 -1
            # 處理指定 tokens
            elif thinking_budget < MIN_TOKENS:
                print(f"⚠️  思考預算低於最小值 {MIN_TOKENS} tokens，已調整")
                thinking_budget = MIN_TOKENS
            elif thinking_budget > MAX_TOKENS:
                print(f"⚠️  思考預算超過上限 {MAX_TOKENS:,} tokens，已調整為最大值")
                thinking_budget = MAX_TOKENS

        user_input = re.sub(think_pattern, '', user_input, flags=re.IGNORECASE).strip()

    return user_input, use_thinking, thinking_budget, max_output_tokens


def process_file_attachments(user_input: str) -> tuple:
    """
    處理檔案附加（智慧判斷文字檔vs媒體檔）

    支援格式:
    - @/path/to/file.txt  （文字檔：直接讀取）
    - 附加 image.jpg      （圖片：上傳API）
    - 讀取 ~/code.py      （程式碼：直接讀取）
    - 上傳 video.mp4      （影片：上傳API）

    Args:
        user_input: 使用者輸入

    Returns:
        (處理後的輸入, 上傳的檔案物件列表)
    """
    # 偵測檔案路徑模式
    file_patterns = [
        r'@([^\s]+)',           # @file.txt
        r'附加\s+([^\s]+)',     # 附加 file.txt
        r'讀取\s+([^\s]+)',     # 讀取 file.txt
        r'上傳\s+([^\s]+)',     # 上傳 file.mp4
    ]

    # 文字檔副檔名（直接讀取）
    TEXT_EXTENSIONS = {'.txt', '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.xml',
                       '.html', '.css', '.md', '.yaml', '.yml', '.toml', '.ini',
                       '.sh', '.bash', '.zsh', '.c', '.cpp', '.h', '.java', '.go',
                       '.rs', '.php', '.rb', '.sql', '.log', '.csv', '.env'}

    # 媒體檔副檔名（上傳API）
    MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg',
                        '.mp4', '.mpeg', '.mov', '.avi', '.flv', '.webm', '.mkv',
                        '.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a',
                        '.pdf', '.doc', '.docx', '.ppt', '.pptx'}

    files_content = []
    uploaded_files = []

    for pattern in file_patterns:
        matches = re.findall(pattern, user_input)
        for file_path in matches:
            file_path = os.path.expanduser(file_path)

            if not os.path.isfile(file_path):
                # 使用錯誤修復建議系統
                if ERROR_FIX_ENABLED:
                    suggest_file_not_found(file_path)
                else:
                    print(f"⚠️  找不到檔案: {file_path}")
                continue

            # 判斷檔案類型
            ext = os.path.splitext(file_path)[1].lower()

            if ext in TEXT_EXTENSIONS:
                # 文字檔：直接讀取
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        files_content.append(f"\n\n[檔案: {file_path}]\n```{ext[1:]}\n{content}\n```\n")
                        print(f"✅ 已讀取文字檔: {file_path}")
                except UnicodeDecodeError:
                    # 嘗試其他編碼
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                            files_content.append(f"\n\n[檔案: {file_path}]\n```\n{content}\n```\n")
                            print(f"✅ 已讀取文字檔: {file_path} (latin-1)")
                    except Exception as e:
                        print(f"⚠️  無法讀取檔案 {file_path}: {e}")
                except Exception as e:
                    print(f"⚠️  無法讀取檔案 {file_path}: {e}")

            elif ext in MEDIA_EXTENSIONS:
                # 媒體檔：上傳 API
                if FILE_MANAGER_ENABLED:
                    try:
                        # 媒體查看器：上傳前顯示檔案資訊（自動整合）
                        if MEDIA_VIEWER_AUTO_ENABLED and global_media_viewer:
                            try:
                                global_media_viewer.show_file_info(file_path)
                            except Exception as e:
                                logger.debug(f"媒體查看器顯示失敗: {e}")

                        uploaded_file = global_file_manager.upload_file(file_path)
                        uploaded_files.append(uploaded_file)
                        print(f"✅ 已上傳媒體檔: {file_path}")
                    except Exception as e:
                        print(f"⚠️  上傳失敗 {file_path}: {e}")
                else:
                    print(f"⚠️  檔案管理器未啟用，無法上傳 {file_path}")

            else:
                # 未知類型：嘗試當文字檔讀取
                print(f"⚠️  未知檔案類型 {ext}，嘗試當文字檔讀取...")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        files_content.append(f"\n\n[檔案: {file_path}]\n```\n{content}\n```\n")
                        print(f"✅ 已讀取檔案: {file_path}")
                except Exception as e:
                    print(f"⚠️  無法處理檔案 {file_path}: {e}")

    # 移除檔案路徑標記
    for pattern in file_patterns:
        user_input = re.sub(pattern, '', user_input)

    # 將文字檔案內容添加到 prompt
    if files_content:
        user_input = user_input.strip() + "\n" + "\n".join(files_content)

    return user_input, uploaded_files


def get_user_input(prompt_text: str = "你: ") -> str:
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
            # 使用 HTML 格式化提示文字，支援顏色
            formatted_prompt = HTML(f'<ansimagenta><b>{prompt_text}</b></ansimagenta>')  # 馬卡龍紫色

            return prompt(
                formatted_prompt,
                history=input_history,
                auto_suggest=AutoSuggestFromHistory(),
                completer=command_completer,
                key_bindings=key_bindings,
                enable_suspend=True,  # 允許 Ctrl+Z 暫停
                mouse_support=False,  # 禁用滑鼠支援避免衝突
                multiline=False,  # 預設單行，使用 Alt+Enter 可插入新行
                prompt_continuation=lambda width, line_number, is_soft_wrap: '... ',  # 多行續行提示
                complete_while_typing=True,  # 打字時即時補全
                style=input_style,  # 應用自訂樣式
            ).strip()
        except (KeyboardInterrupt, EOFError):
            return ""
        except Exception as e:
            # 降級到標準 input()
            logger.debug(f"prompt_toolkit 錯誤，降級到標準 input(): {e}")
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


class AutoCacheManager:
    """自動快取管理器"""

    def __init__(self, enabled: bool = False, mode: str = 'auto', threshold: int = 5000, ttl: int = 1):
        self.enabled = enabled
        self.mode = mode  # 'auto' 或 'prompt'
        self.threshold = threshold
        self.ttl_hours = ttl
        self.conversation_pairs = []  # [(user_msg, ai_msg, input_tokens), ...]
        self.total_input_tokens = 0
        self.cache_created = False
        self.active_cache = None
        self.exclude_next = False  # 下一次對話是否排除

    def add_conversation(self, user_msg: str, ai_msg: str, input_tokens: int):
        """記錄對話（除非被排除）"""
        if not self.exclude_next:
            self.conversation_pairs.append((user_msg, ai_msg, input_tokens))
            self.total_input_tokens += input_tokens
        self.exclude_next = False  # 重置排除標記

    def should_trigger(self) -> bool:
        """是否應該觸發快取建立"""
        return (self.enabled and
                not self.cache_created and
                self.total_input_tokens >= self.threshold)

    def show_trigger_prompt(self, model_name: str) -> bool:
        """顯示快取觸發提示（含精確成本計算）"""
        print("\n" + "🔔 " + "━" * 58)
        print("快取觸發提醒")
        print("━" * 60)
        print(f"📊 目前狀態：")
        print(f"  累積輸入：{self.total_input_tokens:,} tokens")
        print(f"  對話輪次：{len(self.conversation_pairs)} 次")
        print()

        # 計算快取本身的成本與節省
        if PRICING_ENABLED:
            try:
                # 1. 快取建立成本（一次性）
                cache_create_cost, _ = global_pricing_calculator.calculate_text_cost(
                    model_name, self.total_input_tokens, 0, 0
                )

                # 2. 未來使用快取的成本對比
                # 假設後續還會輸入相同數量的 tokens
                future_input = self.total_input_tokens
                future_output = 2000  # 假設平均輸出

                # 不使用快取：每次都要付全額
                no_cache_cost, _ = global_pricing_calculator.calculate_text_cost(
                    model_name, future_input, future_output, 0
                )

                # 使用快取：輸入部分享 90% 折扣
                cache_input_cost, _ = global_pricing_calculator.calculate_text_cost(
                    model_name, future_input, 0, 0
                )
                cache_output_cost, _ = global_pricing_calculator.calculate_text_cost(
                    model_name, 0, future_output, 0
                )
                with_cache_cost = (cache_input_cost * 0.1) + cache_output_cost

                # 每次節省
                per_query_savings = no_cache_cost - with_cache_cost

                # 計算損益平衡點（需要幾次查詢才回本）
                if per_query_savings > 0:
                    breakeven = int(cache_create_cost / per_query_savings) + 1
                else:
                    breakeven = 999

                print(f"💰 成本分析：")
                print(f"  快取建立成本：NT$ {cache_create_cost * USD_TO_TWD:.2f} (一次性)")
                print()
                print(f"  後續每次查詢（{future_input:,} tokens 輸入）：")
                print(f"    不使用快取：NT$ {no_cache_cost * USD_TO_TWD:.2f}")
                print(f"    使用快取：  NT$ {with_cache_cost * USD_TO_TWD:.2f}")
                print(f"    每次節省：  NT$ {per_query_savings * USD_TO_TWD:.2f} (省 {((per_query_savings/no_cache_cost)*100):.0f}%)")
                print()
                print(f"  💡 損益平衡：{breakeven} 次查詢後開始省錢")
                print(f"     (快取有效期 {self.ttl_hours} 小時)")
                print()

            except Exception as e:
                logger.warning(f"成本計算失敗: {e}")

        # 顯示快取內容預覽
        print(f"📦 快取內容預覽：")
        preview_count = min(3, len(self.conversation_pairs))
        for i in range(preview_count):
            user_msg, ai_msg, _ = self.conversation_pairs[i]
            user_preview = user_msg[:50] + "..." if len(user_msg) > 50 else user_msg
            ai_preview = ai_msg[:50] + "..." if len(ai_msg) > 50 else ai_msg
            print(f"  - 你: {user_preview}")
            print(f"  - AI: {ai_preview}")

        if len(self.conversation_pairs) > preview_count:
            print(f"  ... (共 {len(self.conversation_pairs)} 輪對話)")

        print("━" * 60)
        response = input("建立快取？ (y/n) [y]: ").strip().lower()
        return response != 'n'

    def create_cache(self, model_name: str) -> bool:
        """建立快取"""
        if not CACHE_ENABLED:
            print("⚠️  快取功能未啟用（gemini_cache_manager.py 未找到）")
            return False

        try:
            # 組合對話歷史
            cache_content = []
            for user_msg, ai_msg, _ in self.conversation_pairs:
                cache_content.append(f"User: {user_msg}\n\nAssistant: {ai_msg}\n\n")

            combined_content = "\n".join(cache_content)

            # 建立快取
            print("\n⏳ 建立快取中...")
            cache = global_cache_manager.create_cache(
                model=model_name,
                contents=[combined_content],
                display_name=f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                ttl_hours=self.ttl_hours
            )

            self.active_cache = cache
            self.cache_created = True
            print("✅ 快取建立成功！後續對話將自動使用快取節省成本。\n")
            return True

        except Exception as e:
            print(f"⚠️  快取建立失敗：{e}")
            return False


class ChatLogger:
    """對話記錄管理器"""

    def __init__(self, log_dir: str = DEFAULT_LOG_DIR):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.session_start = datetime.now()
        self.session_file = os.path.join(
            log_dir,
            f"conversation_{self.session_start.strftime('%Y%m%d_%H%M%S')}.txt"
        )
        # JSON 記錄檔案（包含思考過程）
        self.json_file = os.path.join(
            log_dir,
            f"conversation_{self.session_start.strftime('%Y%m%d_%H%M%S')}.json"
        )
        self.model_name = None
        self.conversation_history = []  # 儲存完整對話歷史
        logger.info(f"對話記錄將儲存至：{self.session_file}")

    def set_model(self, model_name: str):
        """設定當前使用的模型"""
        self.model_name = model_name
        self._log_message("SYSTEM", f"使用模型: {model_name}")
        self.conversation_history.append({
            "role": "system",
            "content": f"使用模型: {model_name}",
            "timestamp": datetime.now().isoformat()
        })

    def log_user(self, message: str):
        """記錄使用者訊息"""
        self._log_message("USER", message)
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

    def log_assistant(self, message: str, thinking_process: Optional[str] = None):
        """
        記錄助手回應

        Args:
            message: 助手回應內容
            thinking_process: 思考過程（可選）
        """
        self._log_message("ASSISTANT", message)

        # 如果有思考過程，也記錄到文字檔
        if thinking_process:
            self._log_message("THINKING", thinking_process)

        # 記錄到 JSON（包含思考過程）
        entry = {
            "role": "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        if thinking_process:
            entry["thinking_process"] = thinking_process

        self.conversation_history.append(entry)

    def _log_message(self, role: str, message: str):
        """內部記錄方法"""
        try:
            with open(self.session_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"\n[{timestamp}] {role}:\n")
                f.write(f"{message}\n")
                f.write("-" * 80 + "\n")
        except Exception as e:
            logger.error(f"記錄失敗：{e}")

    def save_session(self):
        """儲存會話（同時儲存文字和 JSON）"""
        # 儲存 JSON
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "session_start": self.session_start.isoformat(),
                    "model": self.model_name,
                    "conversation": self.conversation_history
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON 記錄已儲存至：{self.json_file}")
        except Exception as e:
            logger.error(f"JSON 儲存失敗：{e}")

        logger.info(f"對話已儲存至：{self.session_file}")


class ThinkingSignatureManager:
    """思考簽名持久化管理器

    用於保存和載入思考簽名，以維持多輪對話的思考脈絡。
    注意：思考簽名僅在啟用函數呼叫時產生。
    """

    def __init__(self, state_dir: str = DEFAULT_LOG_DIR):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.state_file = os.path.join(state_dir, "thinking_signature_state.json")
        self.last_response_parts = None  # 保存最後一次完整的 response parts
        self.has_function_calling = False  # 標記是否啟用函數呼叫

        # 啟動時自動載入
        self._load_state()

    def _load_state(self):
        """從檔案載入最後保存的思考簽名狀態"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.has_function_calling = data.get('has_function_calling', False)
                    # 注意：response parts 無法直接序列化，這裡只記錄狀態
                    if self.has_function_calling:
                        logger.info("已載入思考簽名狀態（函數呼叫已啟用）")
                    else:
                        logger.debug("思考簽名狀態：函數呼叫未啟用")
        except Exception as e:
            logger.warning(f"載入思考簽名狀態失敗：{e}")

    def save_response(self, response, has_function_calling: bool = False):
        """保存完整的 response（包含思考簽名）

        Args:
            response: Gemini API 回應物件
            has_function_calling: 當前請求是否包含函數宣告
        """
        self.has_function_calling = has_function_calling

        if has_function_calling and hasattr(response, 'candidates'):
            # 只有啟用函數呼叫時才保存 parts
            try:
                # 提取完整的 parts（包含 thought_signature）
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        self.last_response_parts = candidate.content.parts
                        logger.debug("已保存思考簽名（含 parts）")
            except Exception as e:
                logger.warning(f"保存思考簽名失敗：{e}")

        # 保存狀態到檔案
        self._save_state()

    def _save_state(self):
        """保存狀態到檔案"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'has_function_calling': self.has_function_calling,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            logger.debug("思考簽名狀態已保存")
        except Exception as e:
            logger.warning(f"保存思考簽名狀態失敗：{e}")

    def get_last_response_parts(self):
        """獲取最後保存的 response parts（用於下次請求）

        Returns:
            最後一次的 response parts，如果沒有則返回 None
        """
        return self.last_response_parts if self.has_function_calling else None

    def clear(self):
        """清除保存的思考簽名"""
        self.last_response_parts = None
        self.has_function_calling = False
        self._save_state()
        logger.info("已清除思考簽名")


def setup_auto_cache(model_name: str) -> dict:
    """配置自動快取"""
    print("\n" + "=" * 60)
    print("💾 自動快取管理（可節省 75-90% 成本）")
    print("=" * 60)

    choice = input("\n啟用自動快取？\n  [y] 是（推薦，5000 tokens 自動建立）\n  [c] 自訂設定\n  [n] 否\n\n你的選擇 [y]: ").strip().lower() or 'y'

    if choice == 'n':
        print("✓ 快取功能已關閉\n")
        return {'enabled': False}

    if choice == 'c':
        print("\n🔧 進階設定")
        print("-" * 60)

        # 觸發模式
        mode_choice = input("\n觸發模式？\n  [a] 自動建立（達到門檻直接建立）\n  [p] 每次詢問（達到門檻時確認）\n\n選擇 [a]: ").strip().lower() or 'a'
        mode = 'auto' if mode_choice == 'a' else 'prompt'

        # 快取門檻
        threshold_choice = input("\n快取門檻？\n  [1] 3000 tokens（約 3 頁文字）\n  [2] 5000 tokens（約 5 頁，推薦）\n  [3] 8000 tokens（約 8 頁文字）\n  [c] 自訂\n\n選擇 [2]: ").strip() or '2'

        threshold_map = {'1': 3000, '2': 5000, '3': 8000}
        if threshold_choice == 'c':
            custom = input("請輸入門檻（tokens）: ").strip()
            threshold = int(custom) if custom.isdigit() else 5000
        else:
            threshold = threshold_map.get(threshold_choice, 5000)

        # 檢查模型最低要求
        min_required = MIN_TOKENS.get(model_name, 1024)
        if threshold < min_required:
            print(f"\n⚠️  {model_name} 最低需要 {min_required} tokens")
            print(f"   自動調整為 {min_required}")
            threshold = min_required

        # TTL
        ttl_input = input("\n存活時間（小時） [1]: ").strip()
        ttl = int(ttl_input) if ttl_input.isdigit() else 1

        print(f"\n✓ 設定完成：{mode} 模式，門檻 {threshold:,} tokens，TTL {ttl}h\n")
        return {'enabled': True, 'mode': mode, 'threshold': threshold, 'ttl': ttl}

    else:  # 'y' - 使用預設值
        print("✓ 使用推薦設定：自動模式，5000 tokens，TTL 1 小時\n")
        return {'enabled': True, 'mode': 'auto', 'threshold': 5000, 'ttl': 1}


def parse_cache_control(user_input: str, cache_mgr: AutoCacheManager) -> tuple:
    """
    解析快取即時控制指令

    Returns:
        (處理後的輸入, 快取動作)
    """
    # [cache:now] - 立即建立快取
    if re.search(r'\[cache:now\]', user_input, re.I):
        user_input = re.sub(r'\[cache:now\]', '', user_input, flags=re.I).strip()
        return user_input, 'create_now'

    # [cache:off] - 暫停自動快取
    if re.search(r'\[cache:off\]', user_input, re.I):
        user_input = re.sub(r'\[cache:off\]', '', user_input, flags=re.I).strip()
        cache_mgr.enabled = False
        print("⚠️  自動快取已暫停")
        return user_input, None

    # [cache:on] - 恢復自動快取
    if re.search(r'\[cache:on\]', user_input, re.I):
        user_input = re.sub(r'\[cache:on\]', '', user_input, flags=re.I).strip()
        cache_mgr.enabled = True
        print("✓ 自動快取已恢復")
        return user_input, None

    # [no-cache] - 本次對話不列入快取
    if re.search(r'\[no-cache\]', user_input, re.I):
        user_input = re.sub(r'\[no-cache\]', '', user_input, flags=re.I).strip()
        cache_mgr.exclude_next = True
        print("⚠️  本次對話不列入快取")
        return user_input, None

    return user_input, None


def select_model() -> str:
    """選擇 Gemini 模型"""
    print("\n" + "=" * 60)
    print("請選擇 Gemini 模型：")
    print("=" * 60)

    for key, (model_name, description) in RECOMMENDED_MODELS.items():
        print(f"{key}. {description}")

    print("\n0. 自訂模型名稱")
    print("-" * 60)

    while True:
        choice = input(f"\n請輸入選項 (1-{len(RECOMMENDED_MODELS)} 或 0): ").strip()

        if choice == '0':
            custom_model = input("請輸入模型名稱: ").strip()
            if custom_model:
                return custom_model
            else:
                print("模型名稱不能為空，請重試")
                continue

        if choice in RECOMMENDED_MODELS:
            model_name, _ = RECOMMENDED_MODELS[choice]
            return model_name

        print("無效的選項，請重試")


def send_message(
    model_name: str,
    user_input: str,
    chat_logger: ChatLogger,
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
        thinking_budget: 思考預算，依模型而異：
            - -1: 動態模式（所有模型）
            - gemini-2.5-pro: 128-32768 tokens（無法停用）
            - gemini-2.5-flash: 0-24576 tokens（0=停用）
            - gemini-2.5-flash-8b: 512-24576 tokens（0=停用）
        max_output_tokens: 最大輸出 tokens（1-8192，None=使用模型預設值）
        uploaded_files: 上傳的檔案物件列表

    Returns:
        AI 回應文本
    """
    try:
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

                # 自動檢測並增強 prompt，並取得額外 token 使用量
                user_input, hidden_trigger_tokens = auto_enhance_prompt(
                    user_input=user_input,
                    api_key=api_key,
                    uploaded_files=uploaded_files,
                    enable_task_planning=True,
                    enable_web_search=True,
                    enable_code_analysis=True
                )

                # 如果沒有額外用量，設為 None
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
            print(f"📝 [輸出限制] {max_output_tokens:,} tokens")

        if supports_thinking and use_thinking:
            config.thinking_config = types.ThinkingConfig(
                thinking_budget=thinking_budget,
                include_thoughts=True  # 啟用思考摘要串流
            )
            # 顯示思考簽名
            if thinking_budget == -1:
                print("🧠 [思考簽名] 動態思考模式 ✓")
            else:
                # 計算並顯示預估費用
                if PRICING_ENABLED:
                    try:
                        pricing = global_pricing_calculator.get_model_pricing(model_name)
                        input_price = pricing.get('input', pricing.get('input_low', 0))
                        estimated_cost_usd = (thinking_budget / 1000) * input_price
                        estimated_cost_twd = estimated_cost_usd * USD_TO_TWD
                        print(f"🧠 [思考簽名] {thinking_budget:,} tokens ✓ (預估: NT$ {estimated_cost_twd:.4f} / ${estimated_cost_usd:.6f})")
                    except (KeyError, AttributeError, TypeError) as e:
                        logger.warning(f"計價估算失敗 (模型: {model_name}, 預算: {thinking_budget}): {e}")
                        print(f"🧠 [思考簽名] {thinking_budget:,} tokens ✓")
                else:
                    print(f"🧠 [思考簽名] {thinking_budget:,} tokens ✓")
        elif supports_thinking and not use_thinking:
            print("🧠 [思考簽名] 已停用 ✗")

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

        # 處理串流 chunks
        for chunk in stream:
            final_response = chunk  # 持續更新，最後一個包含完整 metadata

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
                if hasattr(part, 'thought') and part.thought:
                    # 這是思考摘要
                    thoughts_text += part.text

                    if SHOW_THINKING_PROCESS and not thinking_displayed:
                        # 首次顯示思考標題
                        console.print("\n[dim bright_magenta]━━━ 🧠 思考過程（即時串流） ━━━[/dim bright_magenta]")
                        thinking_displayed = True

                    if SHOW_THINKING_PROCESS:
                        # 即時顯示思考內容
                        console.print(f"[dim]{part.text}[/dim]", end="", flush=True)
                else:
                    # 這是正常回應文字
                    response_text += part.text

                    if not answer_started:
                        # 首次輸出回應時的處理
                        if thinking_displayed:
                            console.print("[dim bright_magenta]\n━━━━━━━━━━━━━━━[/dim bright_magenta]\n")
                            print("Gemini: ", end="", flush=True)
                        answer_started = True

                    # 串流輸出回應文字
                    print(part.text, end="", flush=True)

        # 串流結束，換行
        print()

        # 保存思考過程
        thinking_process = thoughts_text if thoughts_text else None
        LAST_THINKING_PROCESS = thinking_process

        # 翻譯思考過程（無論是否顯示都先翻譯，以便 Ctrl+T 使用）
        global LAST_THINKING_TRANSLATED, CTRL_T_PRESS_COUNT
        LAST_THINKING_TRANSLATED = None  # 重置翻譯
        CTRL_T_PRESS_COUNT = 0  # 重置 Ctrl+T 計數器

        if thinking_process and TRANSLATOR_ENABLED and global_translator and global_translator.translation_enabled:
            LAST_THINKING_TRANSLATED = global_translator.translate(thinking_process)

        # 如果有思考過程但未顯示，給予提示
        if thinking_process and not SHOW_THINKING_PROCESS:
            if TRANSLATOR_ENABLED and global_translator and global_translator.translation_enabled:
                console.print("[dim magenta]💭 已產生思考摘要 (Ctrl+T 顯示翻譯思路)[/dim magenta]")
            else:
                console.print("[dim magenta]💭 已產生思考摘要 (Ctrl+T 顯示思路)[/dim magenta]")

        # 如果啟用翻譯且已顯示思考，則追加翻譯
        if thinking_process and SHOW_THINKING_PROCESS and TRANSLATOR_ENABLED and global_translator and global_translator.translation_enabled and LAST_THINKING_TRANSLATED:
            if LAST_THINKING_TRANSLATED != thinking_process:
                console.print("\n[dim bright_magenta]━━━ 🌐 思考過程翻譯 ━━━[/dim bright_magenta]")
                console.print("[dim bright_magenta]【繁體中文】[/dim bright_magenta]")
                console.print(f"[dim]{LAST_THINKING_TRANSLATED}[/dim]")
                console.print("[dim bright_magenta]━━━━━━━━━━━━━━━[/dim bright_magenta]\n")

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
            # 優先使用新欄位 thoughts_token_count，向後相容舊欄位 thinking_tokens
            thinking_tokens = getattr(final_response.usage_metadata, 'thoughts_token_count',
                                     getattr(final_response.usage_metadata, 'thinking_tokens', 0))
            input_tokens = getattr(final_response.usage_metadata, 'prompt_tokens', 0)
            output_tokens = getattr(final_response.usage_metadata, 'candidates_tokens', 0)

        # 顯示即時成本（新台幣，包含智能觸發器成本）
        if PRICING_ENABLED and input_tokens > 0 and output_tokens > 0:
            try:
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
                cost_display = f"💰 本次成本: NT${cost * USD_TO_TWD:.2f}"

                # Token 使用明細
                token_parts = []
                token_parts.append(f"輸入: {input_tokens:,} tokens")
                if thinking_tokens > 0:
                    token_parts.append(f"思考: {thinking_tokens:,} tokens")
                token_parts.append(f"輸出: {output_tokens:,} tokens")

                # 如果有隱藏成本，顯示提示
                if hidden_cost > 0:
                    token_parts.append(f"🤖智能增強: {hidden_input + hidden_output:,} tokens")

                cost_display += f" ({', '.join(token_parts)})"
                cost_display += f" | 累計: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f} (${global_pricing_calculator.total_cost:.6f})"

                print(cost_display)

                # 如果有隱藏成本，顯示詳細說明
                if hidden_cost > 0:
                    hidden_model = details.get('hidden_trigger_model', 'unknown')
                    print(f"   ├─ 對話成本: NT${(cost - hidden_cost) * USD_TO_TWD:.2f}")
                    print(f"   └─ 智能增強成本: NT${hidden_cost * USD_TO_TWD:.2f} (任務規劃, {hidden_model})")

            except Exception as e:
                logger.warning(f"計價失敗: {e}")

        return response_text

    except Exception as e:
        error_msg = f"發送失敗：{e}"
        logger.error(error_msg)
        print(f"\n✗ {error_msg}")

        # 智能錯誤診斷（自動整合）
        if ERROR_DIAGNOSTICS_ENABLED and global_error_diagnostics:
            try:
                context = {
                    'operation': 'Gemini API 請求',
                    'model': model_name,
                    'user_input': user_input[:100] if len(user_input) > 100 else user_input,
                    'uploaded_files': len(uploaded_files) if uploaded_files else 0
                }
                _, solutions = global_error_diagnostics.diagnose_and_suggest(
                    error=e,
                    operation="Gemini API 請求",
                    context=context
                )
                if solutions:
                    console.print("\n[bright_magenta]💡 可能的解決方案：[/bright_magenta]")
                    for i, sol in enumerate(solutions[:3], 1):
                        console.print(f"  {i}. {sol.title}")
                        console.print(f"     {sol.description}")
                        if sol.command:
                            console.print(f"     執行：[magenta]{sol.command}[/magenta]")
            except Exception as diag_error:
                logger.debug(f"錯誤診斷失敗: {diag_error}")

        return None


def chat(model_name: str, chat_logger: ChatLogger, auto_cache_config: dict, codebase_embedding=None):
    """互動式對話主循環"""
    print("\n" + "=" * 60)
    print(f"Gemini 對話（模型：{model_name}）")
    print("=" * 60)

    # 初始化自動快取管理器
    auto_cache_mgr = AutoCacheManager(
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
        print(f"\n✓ 自動快取：已啟用（{auto_cache_mgr.mode} 模式，門檻 {auto_cache_mgr.threshold:,} tokens）")
    elif CACHE_ENABLED:
        try:
            caches = list(global_cache_manager.list_caches())
            if caches:
                valid_caches = [c for c in caches if c.expire_time > datetime.now()]
                console.print(f"\n[bright_magenta]💾 快取狀態：{len(valid_caches)} 個有效快取（可節省 75-90% 成本）[/bright_magenta]")
            else:
                console.print(f"\n[magenta]💾 快取狀態：無快取（提示：輸入 'cache' 了解如何建立）[/magenta]")
        except Exception as e:
            logger.debug(f"快取狀態檢查失敗: {e}")

    print("\n基本指令：")
    print("  exit, quit - 退出")
    print("  model - 切換模型")
    print("  clear - 清除對話")
    print("  cache - 快取管理（節省成本 75-90%）")
    print("  config - 配置管理（資料庫設定）")
    print("  media - 影音功能選單（Flow/Veo/分析）")
    print("  debug - 除錯與測試工具")
    print("  help - 完整指令列表")

    # 顯示思考模式提示（僅支援的模型）
    if any(tm in model_name for tm in THINKING_MODELS):
        print("\n💡 思考模式（在輸入前加上）：")
        print("  [think:auto] - 動態思考（預設）")
        print("  [think:2000] - 固定 2000 tokens 思考")
        print("  [no-think] - 關閉思考")
        print("\n  示例：[think:5000] 請分析這段程式碼的效能問題...")

    print("-" * 60 + "\n")

    chat_logger.set_model(model_name)

    while True:
        try:
            # 使用增強型輸入
            user_input = get_user_input("你: ")

            if not user_input:
                continue

            # 處理指令
            if user_input.lower() in ['exit', 'quit', '退出']:
                print("\n再見！")
                chat_logger.save_session()
                break

            elif user_input.lower() == 'help':
                # 顯示主幫助選單
                print("\n" + "=" * 60)
                print("📖 ChatGemini 幫助系統")
                print("=" * 60)
                print("選擇主題：")
                print("  [1] 快速入門")
                print("  [2] 思考模式控制")
                print("  [3] 檔案附加功能")
                print("  [4] 自動快取管理")
                print("  [5] 影音檔案處理")
                if CODEGEMINI_ENABLED:
                    print("  [6] Gemini CLI 管理")
                    print("  [7] 指令列表")
                    max_choice = 7
                else:
                    print("  [6] 指令列表")
                    max_choice = 6
                print("  [0] 返回")
                print("-" * 60)

                help_choice = input(f"請選擇 (0-{max_choice}): ").strip()

                if help_choice == '1':
                    # 快速入門
                    print("\n" + "=" * 60)
                    print("🚀 快速入門")
                    print("=" * 60)
                    print("ChatGemini 是一個強大的 Gemini API 對話工具\n")
                    print("基本使用：")
                    print("  直接輸入問題即可對話")
                    print("  輸入 'help' 查看更多幫助\n")
                    print("特色功能：")
                    print("  • 思考模式：讓 AI 深入思考後回答")
                    print("  • 檔案附加：分析程式碼、圖片、影片")
                    print("  • 自動快取：節省 75-90% API 成本")
                    print("  • 新台幣計價：即時顯示花費\n")
                    print("範例：")
                    print("  你: [think:5000] 解釋量子計算原理")
                    print("  你: @code.py 這段程式碼有什麼問題？")
                    print("  你: 附加 image.jpg 描述這張圖片")
                    print("=" * 60)
                    input("\n按 Enter 繼續...")

                elif help_choice == '2':
                    # 思考模式
                    print("\n" + "=" * 60)
                    print("🧠 思考模式控制")
                    print("=" * 60)
                    print("讓 Gemini 2.5 模型先思考再回答，提升回答品質\n")
                    print("語法：")
                    print("  [think:2000] - 使用 2000 tokens 思考預算")
                    print("  [think:auto] - 動態思考（預設）")
                    print("  [no-think]   - 不使用思考模式\n")
                    print("適用模型：")
                    print("  • gemini-2.5-pro")
                    print("  • gemini-2.5-flash")
                    print("  • gemini-2.5-flash-8b\n")
                    print("使用範例：")
                    print("  你: [think:5000] 深入分析這個演算法的時間複雜度")
                    print("  你: [no-think] 1+1=?")
                    print("  你: [think:auto] 解釋相對論（讓 AI 自行決定）\n")
                    print("成本：")
                    print("  思考 tokens 按輸入價格計費")
                    print("  範例：2000 tokens 思考 ≈ NT$ 0.06")
                    print("=" * 60)
                    input("\n按 Enter 繼續...")

                elif help_choice == '3':
                    # 檔案附加
                    print("\n" + "=" * 60)
                    print("📎 檔案附加功能")
                    print("=" * 60)
                    print("在對話中附加檔案，讓 AI 分析內容\n")
                    print("語法（4 種）：")
                    print("  @file.txt       - 最簡短")
                    print("  讀取 code.py    - 中文語法")
                    print("  附加 image.jpg  - 附加媒體")
                    print("  上傳 video.mp4  - 明確上傳\n")
                    print("智慧判斷：")
                    print("  文字檔（30+ 格式）→ 直接讀取嵌入 prompt")
                    print("    .txt .py .js .ts .json .xml .html .css .md ...")
                    print("  媒體檔 → 上傳到 Gemini API")
                    print("    .jpg .png .mp4 .mp3 .pdf .doc ...\n")
                    print("使用範例：")
                    print("  你: @main.py 解釋這個程式")
                    print("  你: 讀取 config.json 檢查設定")
                    print("  你: 附加 screenshot.png 這個錯誤是什麼？")
                    print("  你: 上傳 demo.mp4 總結影片內容\n")
                    print("組合使用：")
                    print("  你: 讀取 error.log 附加 screenshot.png 診斷問題")
                    print("=" * 60)
                    input("\n按 Enter 繼續...")

                elif help_choice == '4':
                    # 自動快取
                    print("\n" + "=" * 60)
                    print("💾 自動快取管理")
                    print("=" * 60)
                    print("自動建立快取，節省 75-90% API 成本\n")
                    print("啟動時配置：")
                    print("  [y] 快速模式 - 5000 tokens 自動建立")
                    print("  [c] 進階模式 - 自訂門檻、模式、TTL")
                    print("  [n] 關閉自動快取\n")
                    print("即時控制：")
                    print("  [cache:now]  - 立即建立快取")
                    print("  [cache:off]  - 暫停自動快取")
                    print("  [cache:on]   - 恢復自動快取")
                    print("  [no-cache]   - 本次對話不列入快取\n")
                    print("使用場景：")
                    print("  1. 程式碼分析：")
                    print("     你: 讀取 main.py")
                    print("     你: [cache:now]  ← 鎖定程式碼上下文")
                    print("     你: [後續可多次詢問，省 90% 成本]")
                    print()
                    print("  2. 文檔問答：")
                    print("     你: 讀取 spec.md")
                    print("     [自動達到 5000 tokens 後建立快取]")
                    print("     你: [後續問題使用快取]")
                    print()
                    print("成本範例：")
                    print("  不使用快取：每次 5000 tokens → NT$ 0.16")
                    print("  使用快取：每次 5000 tokens → NT$ 0.016（省 90%）")
                    print("=" * 60)
                    input("\n按 Enter 繼續...")

                elif help_choice == '5':
                    # 影音處理
                    print("\n" + "=" * 60)
                    print("🎬 影音檔案處理")
                    print("=" * 60)
                    print("上傳圖片、影片、音訊讓 AI 分析\n")
                    print("運作方式：")
                    print("  1. 上傳到 Gemini 伺服器（48 小時有效）")
                    print("  2. 自動檢查已上傳檔案（避免重複）")
                    print("  3. 影片/音訊自動等待轉碼完成\n")
                    print("檔案限制：")
                    print("  圖片：20 MB")
                    print("  影片：2 GB")
                    print("  音訊：2 GB\n")
                    print("Token 消耗：")
                    print("  圖片：258 tokens（固定）")
                    print("  影片：258 tokens/秒（1 分鐘 ≈ 15,480 tokens）")
                    print("  音訊：32 tokens/秒（1 分鐘 ≈ 1,920 tokens）\n")
                    print("多輪對話（重要！）：")
                    print("  ❌ 錯誤：")
                    print("     你: 附加 image.jpg 描述圖片")
                    print("     你: 圖中的人穿什麼？← AI 看不到圖片")
                    print()
                    print("  ✅ 正確：")
                    print("     你: 附加 image.jpg 描述圖片")
                    print("     你: [cache:now]  ← 建立快取鎖定圖片")
                    print("     你: 圖中的人穿什麼？← AI 可以回答")
                    print()
                    print("使用範例：")
                    print("  你: 附加 meeting.mp4 總結會議重點")
                    print("  你: 上傳 photo1.jpg 附加 photo2.jpg 比較差異")
                    print("=" * 60)
                    input("\n按 Enter 繼續...")

                elif help_choice == '6':
                    # Gemini CLI 管理
                    print("\n" + "=" * 60)
                    print("🛠️  Gemini CLI 管理")
                    print("=" * 60)
                    print("管理 Google Gemini Code Assist CLI 工具\n")
                    print("功能：")
                    print("  • 檢查 Gemini CLI 安裝狀態")
                    print("  • 啟動 Gemini CLI session（帶上下文）")
                    print("  • 管理 checkpoints（儲存/載入對話狀態）")
                    print("  • 安裝/更新/卸載 Gemini CLI")
                    print("  • 配置 API Key\n")
                    print("啟動：")
                    print("  輸入 'cli' 或 'gemini-cli'\n")
                    print("用途：")
                    print("  • Gemini CLI 提供程式碼輔助功能")
                    print("  • 支援多檔案編輯、程式碼生成")
                    print("  • 與 ChatGemini 互補使用\n")
                    print("範例：")
                    print("  你: cli")
                    print("  選擇 [1] 顯示狀態")
                    print("  選擇 [2] 啟動 CLI session")
                    print("=" * 60)
                    input("\n按 Enter 繼續...")

                elif help_choice == ('6' if not CODEGEMINI_ENABLED else '7'):
                    # 指令列表
                    print("\n" + "=" * 60)
                    print("📋 指令列表")
                    print("=" * 60)
                    print("基本指令：")
                    print("  help        - 顯示幫助系統")
                    print("  cache       - 快取管理選單")
                    print("  media       - 影音功能選單（Flow/Veo/分析/處理）")
                    if CODEGEMINI_ENABLED:
                        print("  cli         - Gemini CLI 管理工具")
                    print("  model       - 切換模型")
                    print("  clear       - 清除對話歷史")
                    print("  exit/quit   - 退出程式")
                    print()
                    print("思考模式：")
                    print("  [think:-1] 或 [think:auto] - 動態思考（所有模型，推薦）")
                    print("  [think:數字] - 指定思考預算（依模型而異）")
                    print("                 • Pro: 128-32,768 tokens")
                    print("                 • Flash: 1-24,576 tokens")
                    print("                 • Flash-8b: 512-24,576 tokens")
                    print("  [no-think] 或 [think:0] - 停用思考（僅 Flash/Flash-8b）")
                    print()
                    print("檔案附加：")
                    print("  @檔案路徑    - 附加檔案")
                    print("  讀取 檔案    - 讀取檔案")
                    print("  附加 檔案    - 附加檔案")
                    print("  上傳 檔案    - 上傳媒體")
                    print()
                    print("快取控制：")
                    print("  [cache:now]  - 立即建立")
                    print("  [cache:off]  - 暫停自動")
                    print("  [cache:on]   - 恢復自動")
                    print("  [no-cache]   - 排除本次")
                    print("=" * 60)
                    input("\n按 Enter 繼續...")

                continue

            elif user_input.lower() == 'model':
                return 'switch_model'

            elif user_input.lower() == 'clear':
                print("\n✓ 對話已清除")
                # 新 SDK 不需要手動清除，每次都是新請求
                continue

            elif user_input.lower() == 'cache':
                if not CACHE_ENABLED:
                    console.print("[magenta]快取功能未啟用（gemini_cache_manager.py 未找到）[/magenta]")
                    continue

                console.print("\n[bright_magenta]💾 快取與思考管理[/bright_magenta]\n")
                console.print("優化成本與效能的關鍵設定！\n")
                console.print("指令：")
                console.print("  [快取管理]")
                console.print("  1. 列出所有快取")
                console.print("  2. 建立新快取")
                console.print("  3. 刪除快取")

                # 只在支援思考模式的模型顯示
                if any(tm in model_name for tm in THINKING_MODELS):
                    console.print("\n  [思考模式配置]")
                    console.print("  4. 設定預設思考模式")
                    console.print("  5. 查看思考費用試算")

                    # 顯示翻譯功能選項
                    if TRANSLATOR_ENABLED:
                        trans_status = "✅ 啟用" if global_translator.translation_enabled else "❌ 停用"
                        console.print(f"  6. 切換思考翻譯 (當前: {trans_status})")

                console.print("\n  0. 返回\n")

                cache_choice = input("請選擇: ").strip()

                if cache_choice == '1':
                    global_cache_manager.list_caches()
                elif cache_choice == '2':
                    console.print("\n[bright_magenta]建立快取（最低 token 需求：gemini-2.5-flash=1024, gemini-2.5-pro=4096）[/bright_magenta]")
                    content_input = input("輸入要快取的內容（或檔案路徑）: ").strip()
                    if os.path.isfile(content_input):
                        with open(content_input, 'r', encoding='utf-8') as f:
                            content = f.read()
                    else:
                        content = content_input

                    cache_name = input("快取名稱（可選）: ").strip() or None
                    ttl_hours = input("存活時間（小時，預設=1）: ").strip()
                    ttl_hours = int(ttl_hours) if ttl_hours.isdigit() else 1

                    try:
                        global_cache_manager.create_cache(
                            model=model_name,
                            contents=[content],
                            display_name=cache_name,
                            ttl_hours=ttl_hours
                        )
                    except Exception as e:
                        console.print(f"[red]建立失敗：{e}[/red]")

                elif cache_choice == '3':
                    cache_id = input("輸入要刪除的快取名稱或 ID: ").strip()
                    global_cache_manager.delete_cache(cache_id)

                elif cache_choice == '4' and any(tm in model_name for tm in THINKING_MODELS):
                    # 設定預設思考模式
                    console.print("\n[bright_magenta]🧠 思考模式配置[/bright_magenta]\n")
                    console.print(f"當前模型：{model_name}")

                    # 根據模型決定範圍
                    is_pro = '2.5-pro' in model_name or '2.0-pro' in model_name
                    is_lite = 'flash-8b' in model_name or 'lite' in model_name

                    if is_pro:
                        MAX_TOKENS = 32768
                        MIN_TOKENS = 128
                        ALLOW_DISABLE = False
                        console.print(f"思考範圍：{MIN_TOKENS:,} - {MAX_TOKENS:,} tokens（無法停用）\n")
                    elif is_lite:
                        MAX_TOKENS = 24576
                        MIN_TOKENS = 512
                        ALLOW_DISABLE = True
                        console.print(f"思考範圍：0 (停用) 或 {MIN_TOKENS:,} - {MAX_TOKENS:,} tokens\n")
                    else:  # flash
                        MAX_TOKENS = 24576
                        MIN_TOKENS = 0
                        ALLOW_DISABLE = True
                        console.print(f"思考範圍：0 (停用) 或 1 - {MAX_TOKENS:,} tokens\n")

                    console.print("選擇預設思考模式：")
                    console.print("  [1] 動態模式（推薦）- AI 自動決定思考量")
                    console.print("  [2] 輕度思考 (2,000 tokens)")
                    console.print("  [3] 中度思考 (5,000 tokens)")
                    console.print("  [4] 深度思考 (10,000 tokens)")
                    console.print(f"  [5] 極限思考 ({MAX_TOKENS:,} tokens)")
                    console.print("  [6] 自訂 tokens")
                    if ALLOW_DISABLE:
                        console.print("  [7] 停用思考 (0 tokens)")
                    console.print("  [0] 取消\n")

                    think_choice = input("請選擇: ").strip()

                    if think_choice == '1':
                        console.print("\n✓ 已設定為動態模式")
                        console.print("💡 提示：每次對話可用 [think:auto] 覆蓋")
                    elif think_choice in ['2', '3', '4', '5', '6', '7']:
                        budget_map = {'2': 2000, '3': 5000, '4': 10000, '5': MAX_TOKENS, '7': 0}
                        if think_choice == '6':
                            custom = input(f"請輸入思考 tokens ({MIN_TOKENS}-{MAX_TOKENS}): ").strip()
                            if custom.isdigit():
                                budget = max(MIN_TOKENS, min(int(custom), MAX_TOKENS))
                            else:
                                console.print("[magenta]無效輸入，使用預設 5000[/magenta]")
                                budget = 5000
                        elif think_choice == '7':
                            if ALLOW_DISABLE:
                                budget = 0
                            else:
                                console.print(f"[magenta]{model_name} 無法停用思考，使用最小值 {MIN_TOKENS}[/magenta]")
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
                                console.print(f"\n✓ 已設定思考預算：{budget:,} tokens")
                                console.print(f"💰 預估每次思考費用：NT$ {cost_twd:.4f} (${cost_usd:.6f})")
                            except (KeyError, AttributeError, TypeError) as e:
                                logger.warning(f"預算費用估算失敗 (預算: {budget}): {e}")
                                console.print(f"\n✓ 已設定思考預算：{budget:,} tokens")
                        else:
                            console.print(f"\n✓ 已設定思考預算：{budget:,} tokens")

                        console.print(f"💡 提示：每次對話可用 [think:{budget}] 覆蓋")

                elif cache_choice == '5' and any(tm in model_name for tm in THINKING_MODELS):
                    # 思考費用試算
                    console.print("\n[bright_magenta]💰 思考費用試算器[/bright_magenta]\n")
                    console.print(f"當前模型：{model_name}")

                    # 根據模型決定範圍
                    is_pro = '2.5-pro' in model_name or '2.0-pro' in model_name
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

                    console.print(f"思考範圍：{MIN_TOKENS:,} - {MAX_TOKENS:,} tokens\n")

                    tokens_input = input(f"輸入思考 tokens 數量 ({MIN_TOKENS}-{MAX_TOKENS}): ").strip()
                    if tokens_input.isdigit():
                        tokens = max(MIN_TOKENS, min(int(tokens_input), MAX_TOKENS))

                        if PRICING_ENABLED:
                            try:
                                pricing = global_pricing_calculator.get_model_pricing(model_name)
                                input_price = pricing.get('input', pricing.get('input_low', 0))
                                cost_usd = (tokens / 1000) * input_price
                                cost_twd = cost_usd * USD_TO_TWD

                                console.print("\n[bright_magenta]費用試算結果：[/bright_magenta]")
                                console.print(f"  思考 Tokens：{tokens:,}")
                                console.print(f"  單次費用：NT$ {cost_twd:.4f} (${cost_usd:.6f})")
                                console.print(f"  10 次費用：NT$ {cost_twd*10:.4f}")
                                console.print(f"  100 次費用：NT$ {cost_twd*100:.2f}")
                                console.print(f"\n  費率：NT$ {input_price * USD_TO_TWD:.4f} / 1K tokens")
                            except Exception as e:
                                console.print(f"[red]計算失敗：{e}[/red]")
                        else:
                            console.print("[magenta]計價功能未啟用[/magenta]")
                    else:
                        console.print("[magenta]無效輸入[/magenta]")

                    input("\n按 Enter 繼續...")

                elif cache_choice == '6' and any(tm in model_name for tm in THINKING_MODELS) and TRANSLATOR_ENABLED:
                    # 翻譯開關
                    console.print("\n[bright_magenta]🌐 思考過程翻譯設定[/bright_magenta]\n")

                    # 顯示翻譯器狀態
                    trans_status = global_translator.get_status()
                    console.print(f"當前狀態: {'✅ 啟用' if trans_status['translation_enabled'] else '❌ 停用'}")
                    console.print(f"翻譯引擎: {trans_status['current_engine']}")

                    console.print(f"\n【可用引擎】")
                    for engine, status in trans_status['engines'].items():
                        console.print(f"  {engine}: {status}")

                    console.print(f"\n【使用統計】")
                    console.print(f"  已翻譯字元: {trans_status['translated_chars']:,}")
                    console.print(f"  免費額度剩餘: {trans_status['free_quota_remaining']:,} / 500,000 字元")
                    console.print(f"  快取項目: {trans_status['cache_size']} 個")

                    console.print("\n選項：")
                    console.print("  [1] 切換翻譯功能（啟用/停用）")
                    console.print("  [2] 清除翻譯快取")
                    console.print("  [0] 返回\n")

                    trans_choice = input("請選擇: ").strip()

                    if trans_choice == '1':
                        new_state = global_translator.toggle_translation()
                        status_text = "✅ 已啟用" if new_state else "❌ 已停用"
                        console.print(f"\n{status_text} 思考過程翻譯")
                        if new_state:
                            console.print("💡 思考過程將自動翻譯為繁體中文")
                        else:
                            console.print("💡 思考過程將顯示英文原文")
                    elif trans_choice == '2':
                        global_translator.clear_cache()
                        console.print("\n✓ 翻譯快取已清除")

                    input("\n按 Enter 繼續...")

                continue

            elif user_input.lower() in ['cli', 'gemini-cli']:
                # Gemini CLI 管理選單
                if not CODEGEMINI_ENABLED:
                    console.print("[magenta]CodeGemini 功能未啟用（CodeGemini.py 未找到）[/magenta]")
                    continue

                while True:
                    console.print("\n" + "=" * 60)
                    console.print("[bold bright_magenta]🛠️  Gemini CLI 管理工具[/bold bright_magenta]")
                    console.print("=" * 60)
                    console.print("\n  [1] 顯示 Gemini CLI 狀態")
                    console.print("  [2] 啟動 Gemini CLI session")
                    console.print("  [3] 管理 checkpoints")
                    console.print("  [4] 安裝/更新 Gemini CLI")
                    console.print("  [5] 配置 API Key")
                    console.print("\n  [0] 返回\n")

                    cli_choice = input("請選擇: ").strip()

                    if cli_choice == '0':
                        break

                    elif cli_choice == '1':
                        # 顯示狀態
                        try:
                            cg = CodeGemini()
                            cg.print_status()
                        except Exception as e:
                            console.print(f"[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif cli_choice == '2':
                        # 啟動 Gemini CLI
                        console.print("\n[bright_magenta]啟動 Gemini CLI...[/bright_magenta]")
                        script_path = Path(__file__).parent / "CodeGemini" / "gemini-with-context.sh"
                        if script_path.exists():
                            try:
                                subprocess.run([str(script_path)], check=True)
                            except Exception as e:
                                console.print(f"[red]啟動失敗：{e}[/red]")
                        else:
                            console.print(f"[red]腳本不存在：{script_path}[/red]")
                        input("\n按 Enter 繼續...")

                    elif cli_choice == '3':
                        # 管理 checkpoints
                        console.print("\n[bright_magenta]Checkpoint 管理...[/bright_magenta]")
                        script_path = Path(__file__).parent / "CodeGemini" / "checkpoint-manager.sh"
                        if script_path.exists():
                            try:
                                subprocess.run([str(script_path)], check=True)
                            except Exception as e:
                                console.print(f"[red]啟動失敗：{e}[/red]")
                        else:
                            console.print(f"[red]腳本不存在：{script_path}[/red]")
                        input("\n按 Enter 繼續...")

                    elif cli_choice == '4':
                        # 安裝/更新
                        console.print("\n[bright_magenta]安裝/更新 Gemini CLI[/bright_magenta]")
                        console.print("  [1] 安裝")
                        console.print("  [2] 更新")
                        console.print("  [3] 卸載")
                        console.print("  [0] 返回\n")

                        install_choice = input("請選擇: ").strip()

                        try:
                            cg = CodeGemini()
                            if install_choice == '1':
                                if cg.cli_manager.install():
                                    console.print("[bright_magenta]✓ 安裝成功[/bright_magenta]")
                                else:
                                    console.print("[red]✗ 安裝失敗[/red]")
                            elif install_choice == '2':
                                if cg.cli_manager.update():
                                    console.print("[bright_magenta]✓ 更新成功[/bright_magenta]")
                                else:
                                    console.print("[red]✗ 更新失敗[/red]")
                            elif install_choice == '3':
                                confirm = input("確定要卸載 Gemini CLI？(yes/no): ").strip().lower()
                                if confirm == 'yes':
                                    if cg.cli_manager.uninstall():
                                        console.print("[bright_magenta]✓ 卸載成功[/bright_magenta]")
                                    else:
                                        console.print("[red]✗ 卸載失敗[/red]")
                                else:
                                    console.print("[magenta]已取消[/magenta]")
                        except Exception as e:
                            console.print(f"[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif cli_choice == '5':
                        # 配置 API Key
                        try:
                            cg = CodeGemini()
                            if cg.api_key_manager.setup_interactive():
                                console.print("[bright_magenta]✓ API Key 設定完成[/bright_magenta]")
                            else:
                                console.print("[red]✗ API Key 設定失敗[/red]")
                        except Exception as e:
                            console.print(f"[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                continue

            elif user_input.lower() == 'config':
                # 配置管理選單
                try:
                    # 動態導入配置管理器
                    import sys
                    from pathlib import Path
                    config_path = Path(__file__).parent / "CodeGemini"
                    sys.path.insert(0, str(config_path))

                    from config_manager import ConfigManager, interactive_config_menu

                    # 建立或載入配置管理器
                    config_mgr = ConfigManager()

                    # 進入互動式配置選單
                    interactive_config_menu(config_mgr)

                except ImportError as e:
                    console.print(f"[red]✗ 無法載入配置管理器: {e}[/red]")
                    console.print("[magenta]請確認 CodeGemini/config_manager.py 存在[/magenta]")
                except Exception as e:
                    console.print(f"[red]✗ 配置管理錯誤: {e}[/red]")

                continue

            elif user_input.lower() in ['media', 'video', 'veo']:
                # ==========================================
                # 多媒體創作中心 - 精簡版選單
                # ==========================================
                while True:
                    console.print("\n" + "=" * 60)
                    console.print("[bold bright_magenta]🎬 多媒體創作中心[/bold bright_magenta]")
                    console.print("=" * 60)

                    # 第一層：AI 生成（核心功能）
                    console.print("\n[bold magenta]>>> AI 創作生成[/bold magenta]")
                    if FLOW_ENGINE_ENABLED:
                        console.print("  [1] Flow 影片生成（1080p 長影片，自然語言）")
                    console.print("  [2] Veo 影片生成（8秒快速生成）")
                    if IMAGEN_GENERATOR_ENABLED:
                        console.print("  [12] Imagen 圖像生成（Text-to-Image）")
                        console.print("  [13] Imagen 圖像編輯（AI 編輯）")
                        console.print("  [14] Imagen 圖像放大（Upscaling）")

                    # 第二層：影片處理工具
                    console.print("\n[bold magenta]>>> 影片處理[/bold magenta]")
                    if VIDEO_PREPROCESSOR_ENABLED or VIDEO_COMPOSITOR_ENABLED:
                        if VIDEO_PREPROCESSOR_ENABLED:
                            console.print("  [3] 影片預處理（分割/關鍵幀/資訊）")
                        if VIDEO_COMPOSITOR_ENABLED:
                            console.print("  [4] 影片合併（無損拼接）")
                    if VIDEO_EFFECTS_ENABLED:
                        console.print("  [15] 時間裁切（無損剪輯）")
                        console.print("  [16] 濾鏡特效（7種風格）")
                        console.print("  [17] 速度調整（快轉/慢動作）")
                        console.print("  [18] 添加浮水印")
                    if SUBTITLE_GENERATOR_ENABLED:
                        console.print("  [19] 生成字幕（語音辨識+翻譯）")
                        console.print("  [20] 燒錄字幕（嵌入影片）")

                    # 第三層：音訊處理
                    if AUDIO_PROCESSOR_ENABLED:
                        console.print("\n[bold magenta]>>> 音訊處理[/bold magenta]")
                        console.print("  [7] 提取音訊  [8] 合併音訊  [9] 音量調整")
                        console.print("  [10] 背景音樂  [11] 淡入淡出")

                    # 第四層：AI 分析
                    console.print("\n[bold magenta]>>> AI 分析工具[/bold magenta]")
                    if MEDIA_VIEWER_ENABLED:
                        console.print("  [0] 媒體分析器（圖片/影片 AI 分析）")
                    console.print("  [5] 影片內容分析  [6] 圖像內容分析")

                    console.print("\n  [99] 返回主選單\n")

                    media_choice = input("請選擇: ").strip()

                    if media_choice == '99':
                        break

                    elif media_choice == '0' and MEDIA_VIEWER_ENABLED:
                        # 媒體檔案查看器
                        console.print("\n[bright_magenta]🎬 媒體檔案查看器[/bright_magenta]\n")
                        file_path = input("檔案路徑：").strip()

                        if not os.path.isfile(file_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            viewer = MediaViewer()
                            viewer.view_file(file_path)

                            # 詢問是否進行 AI 分析
                            if viewer.ai_analysis_enabled:
                                analyze = input("\n[bright_magenta]進行 AI 分析？(y/N): [/bright_magenta]").strip().lower()
                                if analyze == 'y':
                                    custom = input("[bright_magenta]自訂分析提示（可留空使用預設）：[/bright_magenta]\n").strip()
                                    viewer.analyze_with_ai(file_path, custom if custom else None)

                            # 詢問是否開啟檔案
                            open_file = input("\n[bright_magenta]開啟檔案？(y/N): [/bright_magenta]").strip().lower()
                            if open_file == 'y':
                                os.system(f'open "{file_path}"')

                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '1' and FLOW_ENGINE_ENABLED:
                        # Flow 引擎 - 自然語言生成影片（預設 1080p）
                        console.print("\n[bright_magenta]🎬 Flow 引擎 - 智能影片生成（預設 1080p）[/bright_magenta]\n")

                        description = input("請描述您想要的影片內容：").strip()
                        if not description:
                            console.print("[magenta]未輸入描述，取消操作[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        duration_input = input("目標時長（秒，預設 30）：").strip()
                        target_duration = int(duration_input) if duration_input.isdigit() else 30

                        # 智能建議：長影片自動使用最佳參數
                        if target_duration > 60:
                            console.print("[dim magenta]💡 長影片建議使用最佳參數：1080p, 16:9[/dim magenta]")

                        # 預設使用最佳參數（1080p, 16:9）
                        resolution = "1080p"
                        aspect_ratio = "16:9"

                        # 僅在用戶需要時提供自訂選項
                        custom_settings = input("\n使用預設最佳參數（1080p, 16:9）？(Y/n): ").strip().lower()
                        if custom_settings == 'n':
                            # 解析度選擇
                            console.print("\n[bright_magenta]解析度：[/bright_magenta]")
                            console.print("  [1] 1080p (推薦)")
                            console.print("  [2] 720p")
                            resolution_choice = input("請選擇：").strip()
                            resolution = "1080p" if resolution_choice != '2' else "720p"

                            # 比例選擇
                            console.print("\n[bright_magenta]比例：[/bright_magenta]")
                            console.print("  [1] 16:9 (橫向，預設)")
                            console.print("  [2] 9:16 (直向)")
                            ratio_choice = input("請選擇：").strip()
                            aspect_ratio = "16:9" if ratio_choice != '2' else "9:16"

                        console.print(f"\n[dim bright_magenta]⏳ 準備生成 {target_duration}秒 影片（{resolution}, {aspect_ratio}）...[/dim bright_magenta]")

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
                                console.print(f"\n[bright_magenta]✅ 影片生成完成！[/bright_magenta]")
                                console.print(f"儲存路徑：{video_path}")
                            else:
                                console.print("\n[magenta]已取消生成[/magenta]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")

                        input("\n按 Enter 繼續...")

                    elif media_choice == '2':
                        # Veo 基本生成
                        console.print("\n[bright_magenta]🎬 Veo 基本影片生成[/bright_magenta]\n")
                        console.print("使用獨立工具：")
                        console.print("  python gemini_veo_generator.py\n")
                        console.print("功能：")
                        console.print("  - 文字生成影片（8 秒，Veo 3.1）")
                        console.print("  - 支援參考圖片")
                        console.print("  - 自訂長寬比")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '3' and VIDEO_PREPROCESSOR_ENABLED:
                        # 影片預處理
                        console.print("\n[bright_magenta]✂️ 影片預處理工具[/bright_magenta]\n")
                        console.print("功能：")
                        console.print("  1. 查詢影片資訊（解析度/時長/編碼/大小）")
                        console.print("  2. 分割影片（固定時長分段）")
                        console.print("  3. 提取關鍵幀（等距提取）")
                        console.print("  4. 檢查檔案大小（API 限制 < 2GB）\n")
                        console.print("使用方式：")
                        console.print("  python gemini_video_preprocessor.py <影片路徑> <指令>")
                        console.print("\n範例：")
                        console.print("  python gemini_video_preprocessor.py video.mp4 info")
                        console.print("  python gemini_video_preprocessor.py video.mp4 split")
                        console.print("  python gemini_video_preprocessor.py video.mp4 keyframes")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '4' and VIDEO_COMPOSITOR_ENABLED:
                        # 影片合併
                        console.print("\n[bright_magenta]🎞️ 影片合併工具[/bright_magenta]\n")
                        console.print("功能：")
                        console.print("  - 無損合併多段影片（ffmpeg concat demuxer）")
                        console.print("  - 保持原始品質（禁止有損壓縮）")
                        console.print("  - 替換影片片段（Insert 功能）\n")
                        console.print("使用方式：")
                        console.print("  python gemini_video_compositor.py concat <影片1> <影片2> ...")
                        console.print("  python gemini_video_compositor.py replace <基礎影片> <新片段> <時間點>")
                        console.print("\n範例：")
                        console.print("  python gemini_video_compositor.py concat seg1.mp4 seg2.mp4 seg3.mp4")
                        console.print("  python gemini_video_compositor.py replace base.mp4 new.mp4 10.5")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '5':
                        # 影片分析
                        console.print("\n[bright_magenta]🎥 影片分析工具[/bright_magenta]\n")
                        console.print("使用獨立工具：")
                        console.print("  python gemini_video_analyzer.py <影片路徑>\n")
                        console.print("功能：")
                        console.print("  - 自動提取關鍵幀")
                        console.print("  - Gemini 分析影片內容")
                        console.print("  - 生成詳細描述")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '6':
                        # 圖像分析
                        console.print("\n[bright_magenta]🖼️ 圖像分析工具[/bright_magenta]\n")
                        console.print("使用獨立工具：")
                        console.print("  python gemini_image_analyzer.py <圖片路徑>\n")
                        console.print("功能：")
                        console.print("  - Gemini Vision 圖像分析")
                        console.print("  - 支援多種圖片格式")
                        console.print("  - 詳細內容描述")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '7' and AUDIO_PROCESSOR_ENABLED:
                        # 提取音訊
                        console.print("\n[bright_magenta]🎵 提取音訊[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()
                        if not video_path or not os.path.isfile(video_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        console.print("\n[bright_magenta]音訊格式：[/bright_magenta]")
                        console.print("  [1] AAC (預設)")
                        console.print("  [2] MP3")
                        console.print("  [3] WAV")
                        format_choice = input("請選擇：").strip()
                        format_map = {'1': 'aac', '2': 'mp3', '3': 'wav'}
                        audio_format = format_map.get(format_choice, 'aac')

                        try:
                            processor = AudioProcessor()
                            output_path = processor.extract_audio(video_path, format=audio_format)
                            console.print(f"\n[bright_magenta]✅ 音訊已提取：{output_path}[/bright_magenta]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '8' and AUDIO_PROCESSOR_ENABLED:
                        # 合併音訊
                        console.print("\n[bright_magenta]🎵 合併音訊[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()
                        audio_path = input("音訊路徑：").strip()

                        if not os.path.isfile(video_path):
                            console.print("[magenta]影片檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue
                        if not os.path.isfile(audio_path):
                            console.print("[magenta]音訊檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        console.print("\n[bright_magenta]合併模式：[/bright_magenta]")
                        console.print("  [1] 替換（取代原音訊，預設）")
                        console.print("  [2] 混合（與原音訊混合）")
                        mode_choice = input("請選擇：").strip()
                        replace_mode = mode_choice != '2'

                        try:
                            processor = AudioProcessor()
                            output_path = processor.merge_audio(video_path, audio_path, replace=replace_mode)
                            console.print(f"\n[bright_magenta]✅ 音訊已合併：{output_path}[/bright_magenta]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '9' and AUDIO_PROCESSOR_ENABLED:
                        # 音量調整
                        console.print("\n[bright_magenta]🎵 音量調整[/bright_magenta]\n")
                        file_path = input("影片/音訊路徑：").strip()
                        if not os.path.isfile(file_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        volume_input = input("音量倍數（0.5=50%, 1.0=100%, 2.0=200%，預設1.0）：").strip()
                        try:
                            volume = float(volume_input) if volume_input else 1.0
                            if volume <= 0:
                                console.print("[magenta]音量必須大於0[/magenta]")
                                input("\n按 Enter 繼續...")
                                continue
                        except ValueError:
                            console.print("[magenta]無效的數值[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            processor = AudioProcessor()
                            output_path = processor.adjust_volume(file_path, volume)
                            console.print(f"\n[bright_magenta]✅ 音量已調整：{output_path}[/bright_magenta]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '10' and AUDIO_PROCESSOR_ENABLED:
                        # 添加背景音樂
                        console.print("\n[bright_magenta]🎵 添加背景音樂[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()
                        music_path = input("背景音樂路徑：").strip()

                        if not os.path.isfile(video_path):
                            console.print("[magenta]影片檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue
                        if not os.path.isfile(music_path):
                            console.print("[magenta]音樂檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        volume_input = input("背景音樂音量（0.0-1.0，預設0.3）：").strip()
                        fade_input = input("淡入淡出時長（秒，預設2.0）：").strip()

                        try:
                            music_volume = float(volume_input) if volume_input else 0.3
                            fade_duration = float(fade_input) if fade_input else 2.0
                        except ValueError:
                            console.print("[magenta]無效的數值[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            processor = AudioProcessor()
                            output_path = processor.add_background_music(
                                video_path, music_path,
                                music_volume=music_volume,
                                fade_duration=fade_duration
                            )
                            console.print(f"\n[bright_magenta]✅ 背景音樂已添加：{output_path}[/bright_magenta]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '11' and AUDIO_PROCESSOR_ENABLED:
                        # 淡入淡出
                        console.print("\n[bright_magenta]🎵 音訊淡入淡出[/bright_magenta]\n")
                        file_path = input("影片/音訊路徑：").strip()
                        if not os.path.isfile(file_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        fade_in_input = input("淡入時長（秒，預設2.0）：").strip()
                        fade_out_input = input("淡出時長（秒，預設2.0）：").strip()

                        try:
                            fade_in = float(fade_in_input) if fade_in_input else 2.0
                            fade_out = float(fade_out_input) if fade_out_input else 2.0
                        except ValueError:
                            console.print("[magenta]無效的數值[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            processor = AudioProcessor()
                            output_path = processor.fade_in_out(file_path, fade_in=fade_in, fade_out=fade_out)
                            console.print(f"\n[bright_magenta]✅ 淡入淡出已完成：{output_path}[/bright_magenta]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '12' and IMAGEN_GENERATOR_ENABLED:
                        # 生成圖片
                        console.print("\n[bright_magenta]🎨 Imagen 圖片生成[/bright_magenta]\n")
                        prompt = input("請描述您想生成的圖片：").strip()

                        if not prompt:
                            console.print("[magenta]未輸入描述[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        negative_prompt = input("\n負面提示（避免的內容，可留空）：").strip()
                        if not negative_prompt:
                            negative_prompt = None

                        console.print("\n選擇長寬比：")
                        console.print("  1. 1:1 (正方形，預設)")
                        console.print("  2. 16:9 (橫向)")
                        console.print("  3. 9:16 (直向)")
                        aspect_choice = input("請選擇 (1-3, 預設=1): ").strip() or '1'
                        aspect_ratios = {'1': '1:1', '2': '16:9', '3': '9:16'}
                        aspect_ratio = aspect_ratios.get(aspect_choice, '1:1')

                        num_input = input("\n生成數量（1-4，預設=1）：").strip()
                        number_of_images = int(num_input) if num_input.isdigit() and 1 <= int(num_input) <= 4 else 1

                        try:
                            output_paths = generate_image(
                                prompt=prompt,
                                negative_prompt=negative_prompt,
                                number_of_images=number_of_images,
                                aspect_ratio=aspect_ratio,
                                show_cost=PRICING_ENABLED
                            )
                            console.print(f"\n[bright_magenta]✅ 圖片已生成：{len(output_paths)} 張[/bright_magenta]")

                            open_img = input("\n要開啟圖片嗎？(y/N): ").strip().lower()
                            if open_img == 'y':
                                for path in output_paths:
                                    os.system(f'open "{path}"')
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '13' and IMAGEN_GENERATOR_ENABLED:
                        # 編輯圖片
                        console.print("\n[bright_magenta]✏️ Imagen 圖片編輯[/bright_magenta]\n")
                        image_path = input("圖片路徑：").strip()

                        if not os.path.isfile(image_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        prompt = input("\n請描述如何編輯此圖片：").strip()
                        if not prompt:
                            console.print("[magenta]未輸入編輯描述[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            output_path = edit_image(
                                image_path=image_path,
                                prompt=prompt,
                                show_cost=PRICING_ENABLED
                            )
                            console.print(f"\n[bright_magenta]✅ 圖片已編輯：{output_path}[/bright_magenta]")

                            open_img = input("\n要開啟圖片嗎？(y/N): ").strip().lower()
                            if open_img == 'y':
                                os.system(f'open "{output_path}"')
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '14' and IMAGEN_GENERATOR_ENABLED:
                        # 放大圖片
                        console.print("\n[bright_magenta]🔍 Imagen 圖片放大[/bright_magenta]\n")
                        image_path = input("圖片路徑：").strip()

                        if not os.path.isfile(image_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            output_path = upscale_image(
                                image_path=image_path,
                                show_cost=PRICING_ENABLED
                            )
                            console.print(f"\n[bright_magenta]✅ 圖片已放大：{output_path}[/bright_magenta]")

                            open_img = input("\n要開啟圖片嗎？(y/N): ").strip().lower()
                            if open_img == 'y':
                                os.system(f'open "{output_path}"')
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '15' and VIDEO_EFFECTS_ENABLED:
                        # 時間裁切（無損）
                        console.print("\n[bright_magenta]✂️ 時間裁切（無損）[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()

                        if not video_path or not os.path.isfile(video_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        start_input = input("\n開始時間（秒，預設0）：").strip()
                        end_input = input("結束時間（秒，留空=影片結尾）：").strip()

                        try:
                            start_time = float(start_input) if start_input else 0
                            end_time = float(end_input) if end_input else None

                            effects = VideoEffects()
                            output_path = effects.trim_video(video_path, start_time=start_time, end_time=end_time)
                            console.print(f"\n[bright_magenta]✅ 影片已裁切：{output_path}[/bright_magenta]")
                            console.print("[dim]提示：使用 -c copy 無損裁切，保持原始品質[/dim]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '16' and VIDEO_EFFECTS_ENABLED:
                        # 濾鏡效果
                        console.print("\n[bright_magenta]🎨 濾鏡效果[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()

                        if not video_path or not os.path.isfile(video_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        console.print("\n[bright_magenta]選擇濾鏡：[/bright_magenta]")
                        console.print("  [1] 黑白 (grayscale)")
                        console.print("  [2] 復古 (sepia)")
                        console.print("  [3] 懷舊 (vintage)")
                        console.print("  [4] 銳化 (sharpen)")
                        console.print("  [5] 模糊 (blur)")
                        console.print("  [6] 增亮 (brighten)")
                        console.print("  [7] 增強對比 (contrast)")
                        filter_choice = input("請選擇 (1-7): ").strip()

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
                            console.print("[magenta]無效的選擇[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        console.print("\n[bright_magenta]品質設定：[/bright_magenta]")
                        console.print("  [1] 高品質 (CRF 18, slow)")
                        console.print("  [2] 中品質 (CRF 23, medium, 預設)")
                        console.print("  [3] 低品質 (CRF 28, fast)")
                        quality_choice = input("請選擇 (1-3, 預設=2): ").strip() or '2'
                        quality_map = {'1': 'high', '2': 'medium', '3': 'low'}
                        quality = quality_map.get(quality_choice, 'medium')

                        try:
                            effects = VideoEffects()
                            output_path = effects.apply_filter(video_path, filter_name=filter_name, quality=quality)
                            console.print(f"\n[bright_magenta]✅ 濾鏡已套用：{output_path}[/bright_magenta]")
                            console.print("[dim]注意：濾鏡需要重新編碼，已使用高品質設定[/dim]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '17' and VIDEO_EFFECTS_ENABLED:
                        # 速度調整
                        console.print("\n[bright_magenta]⚡ 速度調整[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()

                        if not video_path or not os.path.isfile(video_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        console.print("\n[bright_magenta]速度倍數：[/bright_magenta]")
                        console.print("  0.5 = 慢動作（一半速度）")
                        console.print("  1.0 = 正常速度")
                        console.print("  2.0 = 快轉（兩倍速度）")
                        speed_input = input("\n請輸入速度倍數（預設1.0）：").strip()

                        try:
                            speed_factor = float(speed_input) if speed_input else 1.0
                            if speed_factor <= 0:
                                console.print("[magenta]速度必須大於0[/magenta]")
                                input("\n按 Enter 繼續...")
                                continue
                        except ValueError:
                            console.print("[magenta]無效的數值[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        console.print("\n[bright_magenta]品質設定：[/bright_magenta]")
                        console.print("  [1] 高品質 (CRF 18, slow)")
                        console.print("  [2] 中品質 (CRF 23, medium, 預設)")
                        console.print("  [3] 低品質 (CRF 28, fast)")
                        quality_choice = input("請選擇 (1-3, 預設=2): ").strip() or '2'
                        quality_map = {'1': 'high', '2': 'medium', '3': 'low'}
                        quality = quality_map.get(quality_choice, 'medium')

                        try:
                            effects = VideoEffects()
                            output_path = effects.adjust_speed(video_path, speed_factor=speed_factor, quality=quality)
                            console.print(f"\n[bright_magenta]✅ 速度已調整：{output_path}[/bright_magenta]")
                            console.print("[dim]注意：同時調整影片和音訊速度，已使用高品質設定[/dim]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '18' and VIDEO_EFFECTS_ENABLED:
                        # 添加浮水印
                        console.print("\n[bright_magenta]💧 添加浮水印[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()
                        watermark_path = input("浮水印圖片路徑：").strip()

                        if not os.path.isfile(video_path):
                            console.print("[magenta]影片檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        if not os.path.isfile(watermark_path):
                            console.print("[magenta]浮水印檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        console.print("\n[bright_magenta]浮水印位置：[/bright_magenta]")
                        console.print("  [1] 左上角")
                        console.print("  [2] 右上角")
                        console.print("  [3] 左下角")
                        console.print("  [4] 右下角（預設）")
                        console.print("  [5] 中央")
                        position_choice = input("請選擇 (1-5, 預設=4): ").strip() or '4'

                        position_map = {
                            '1': 'top-left',
                            '2': 'top-right',
                            '3': 'bottom-left',
                            '4': 'bottom-right',
                            '5': 'center'
                        }
                        position = position_map.get(position_choice, 'bottom-right')

                        opacity_input = input("\n不透明度（0.0-1.0，預設0.7）：").strip()
                        try:
                            opacity = float(opacity_input) if opacity_input else 0.7
                            if not 0 <= opacity <= 1:
                                console.print("[magenta]不透明度必須在 0.0-1.0 之間[/magenta]")
                                input("\n按 Enter 繼續...")
                                continue
                        except ValueError:
                            console.print("[magenta]無效的數值[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            effects = VideoEffects()
                            output_path = effects.add_watermark(
                                video_path, watermark_path,
                                position=position, opacity=opacity
                            )
                            console.print(f"\n[bright_magenta]✅ 浮水印已添加：{output_path}[/bright_magenta]")
                            console.print("[dim]注意：添加浮水印需要重新編碼，已使用高品質設定[/dim]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    elif media_choice == '19' and SUBTITLE_GENERATOR_ENABLED:
                        # 生成字幕
                        console.print("\n[bright_magenta]📝 生成字幕[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()

                        if not video_path or not os.path.isfile(video_path):
                            console.print("[magenta]檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        # 字幕格式選擇
                        console.print("\n[bright_magenta]字幕格式：[/bright_magenta]")
                        console.print("  [1] SRT (預設)")
                        console.print("  [2] VTT")
                        format_choice = input("請選擇：").strip()
                        subtitle_format = "vtt" if format_choice == '2' else "srt"

                        # 是否翻譯
                        translate_choice = input("\n是否翻譯字幕？(y/N): ").strip().lower()
                        translate = (translate_choice == 'y')

                        target_lang = "zh-TW"
                        if translate:
                            console.print("\n[bright_magenta]目標語言：[/bright_magenta]")
                            console.print("  [1] 繁體中文 (zh-TW, 預設)")
                            console.print("  [2] 英文 (en)")
                            console.print("  [3] 日文 (ja)")
                            console.print("  [4] 韓文 (ko)")
                            console.print("  [5] 自訂")
                            lang_choice = input("請選擇：").strip()

                            lang_map = {
                                '1': 'zh-TW',
                                '2': 'en',
                                '3': 'ja',
                                '4': 'ko'
                            }
                            if lang_choice == '5':
                                target_lang = input("請輸入語言代碼（如 fr, de）：").strip()
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
                            console.print(f"\n[bright_magenta]✅ 字幕已生成：{subtitle_path}[/bright_magenta]")

                            # 詢問是否燒錄
                            burn_choice = input("\n要將字幕燒錄到影片嗎？(y/N): ").strip().lower()
                            if burn_choice == 'y':
                                video_with_subs = generator.burn_subtitles(video_path, subtitle_path)
                                console.print(f"\n[bright_magenta]✅ 燒錄完成：{video_with_subs}[/bright_magenta]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                            import traceback
                            traceback.print_exc()
                        input("\n按 Enter 繼續...")

                    elif media_choice == '20' and SUBTITLE_GENERATOR_ENABLED:
                        # 燒錄字幕
                        console.print("\n[bright_magenta]🔥 燒錄字幕[/bright_magenta]\n")
                        video_path = input("影片路徑：").strip()
                        subtitle_path = input("字幕檔案路徑：").strip()

                        if not os.path.isfile(video_path):
                            console.print("[magenta]影片檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        if not os.path.isfile(subtitle_path):
                            console.print("[magenta]字幕檔案不存在[/magenta]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            generator = SubtitleGenerator()
                            output_path = generator.burn_subtitles(video_path, subtitle_path)
                            console.print(f"\n[bright_magenta]✅ 字幕已燒錄：{output_path}[/bright_magenta]")
                        except Exception as e:
                            console.print(f"\n[red]錯誤：{e}[/red]")
                        input("\n按 Enter 繼續...")

                    else:
                        console.print("\n[magenta]無效選項或功能未啟用[/magenta]")
                        input("\n按 Enter 繼續...")

                continue

            elif user_input.lower() in ['debug', 'test']:
                # 除錯與測試工具選單
                # 狀態追蹤：記錄 Embedding 功能的載入狀態（互斥機制）
                embedding_active_mode = None  # None, 'search', 'stats'

                while True:
                    console.print("\n" + "=" * 60)
                    console.print("[bold bright_magenta]🔧 除錯與測試工具[/bold bright_magenta]")
                    console.print("=" * 60)

                    console.print("\n[bright_magenta]測試模組：[/bright_magenta]")
                    console.print("  [1] 環境檢查")
                    console.print("  [2] 主程式功能測試")
                    console.print("  [3] Flow Engine 測試")
                    console.print("  [4] 終端輸入測試")

                    if CODEBASE_EMBEDDING_ENABLED:
                        console.print("\n[bright_magenta]Codebase Embedding：[/bright_magenta]")
                        console.print("  [5] 搜尋對話記錄")
                        console.print("  [6] 查看向量資料庫統計")

                    console.print("\n[bright_magenta]性能監控：[/bright_magenta]")
                    console.print("  [7] 查看性能摘要")
                    console.print("  [8] 查看瓶頸分析報告")
                    console.print("  [9] 匯出性能報告")

                    console.print("\n  [0] 返回主選單\n")

                    debug_choice = input("請選擇: ").strip()

                    if debug_choice == '0':
                        break

                    # 根據選擇調用對應測試腳本
                    test_scripts = {
                        '1': ('test_environment.py', '環境檢查'),
                        '2': ('test_chat_features.py', '主程式功能測試'),
                        '3': ('test_flow_engine.py', 'Flow Engine 測試'),
                        '4': ('test_terminal.py', '終端輸入測試')
                    }

                    if debug_choice in test_scripts:
                        script_name, description = test_scripts[debug_choice]
                        console.print(f"\n[bright_magenta]執行 {description}...[/bright_magenta]\n")
                        test_script = Path(__file__).parent / "testTool" / script_name

                        if not test_script.exists():
                            console.print(f"[red]錯誤：找不到 testTool/{script_name}[/red]")
                        else:
                            try:
                                subprocess.run([sys.executable, str(test_script)], check=True)
                            except subprocess.CalledProcessError:
                                console.print(f"[magenta]測試完成（部分項目未通過）[/magenta]")
                            except Exception as e:
                                console.print(f"[red]執行錯誤：{e}[/red]")

                        input("\n按 Enter 繼續...")

                    elif debug_choice == '5' and CODEBASE_EMBEDDING_ENABLED:
                        # 搜尋對話記錄
                        if not codebase_embedding:
                            console.print("[magenta]⚠️  Codebase Embedding 未啟用[/magenta]")
                            console.print("[dim]   請在 config.py 中設置 EMBEDDING_ENABLE_ON_STARTUP = True 並重啟[/dim]")
                            input("\n按 Enter 繼續...")
                            continue

                        # 互斥機制：如果統計模式已載入，先卸載
                        if embedding_active_mode == 'stats':
                            console.print("\n[magenta]⚠️  正在卸載統計模式...[/magenta]")
                            import time
                            time.sleep(0.3)  # 視覺反饋
                            console.print("[bright_magenta]✓ 統計模式已卸載[/bright_magenta]")
                            embedding_active_mode = None

                        # 載入搜尋模式
                        console.print("\n[bright_magenta]🔄 載入搜尋模式...[/bright_magenta]")
                        import time
                        time.sleep(0.2)  # 視覺反饋
                        embedding_active_mode = 'search'
                        console.print("\n[bright_magenta]🔍 搜尋對話記錄[/bright_magenta]")
                        query = input("\n請輸入搜尋關鍵字: ").strip()

                        if query:
                            try:
                                results = codebase_embedding.search_conversations(query=query, top_k=5)

                                if results:
                                    console.print(f"\n[bright_magenta]✓ 找到 {len(results)} 條相關對話[/bright_magenta]\n")
                                    for i, r in enumerate(results, 1):
                                        similarity = r.get('similarity', 0)
                                        console.print(f"[bold bright_magenta]═══ 結果 {i} (相似度: {similarity:.2%}) ═══[/bold bright_magenta]")
                                        console.print(f"[magenta]問題：[/magenta] {r.get('question', 'N/A')}")

                                        # 答案截斷顯示
                                        answer = r.get('answer', 'N/A')
                                        answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
                                        console.print(f"[bright_magenta]回答：[/bright_magenta] {answer_preview}")

                                        # 顯示元數據
                                        timestamp = r.get('timestamp', 'N/A')
                                        session_id = r.get('session_id', 'N/A')
                                        console.print(f"[dim]時間：{timestamp} | Session：{session_id}[/dim]\n")
                                else:
                                    console.print("\n[magenta]⚠️  未找到相關對話[/magenta]")
                                    console.print("[dim]   提示：對話會在 EMBEDDING_AUTO_SAVE_CONVERSATIONS = True 時自動儲存[/dim]")
                            except Exception as e:
                                console.print(f"\n[red]✗ 搜尋錯誤：{e}[/red]")
                                import traceback
                                traceback.print_exc()
                        else:
                            console.print("[magenta]請輸入搜尋關鍵字[/magenta]")

                        input("\n按 Enter 繼續...")

                    elif debug_choice == '6' and CODEBASE_EMBEDDING_ENABLED:
                        # 查看向量資料庫統計
                        if not codebase_embedding:
                            console.print("[magenta]⚠️  Codebase Embedding 未啟用[/magenta]")
                            console.print("[dim]   請在 config.py 中設置 EMBEDDING_ENABLE_ON_STARTUP = True 並重啟[/dim]")
                            input("\n按 Enter 繼續...")
                            continue

                        try:
                            stats = codebase_embedding.get_stats()

                            console.print("\n" + "=" * 60)
                            console.print("[bold bright_magenta]📊 向量資料庫統計資訊[/bold bright_magenta]")
                            console.print("=" * 60 + "\n")

                            # 基本統計
                            total_chunks = stats.get('total_chunks', 0)
                            total_files = stats.get('total_files', 0)
                            console.print(f"[bright_magenta]總分塊數：[/bright_magenta] {total_chunks:,}")
                            console.print(f"[bright_magenta]總檔案數：[/bright_magenta] {total_files:,}")

                            # 分塊類型統計
                            chunk_types = stats.get('chunk_type_counts', {})
                            if chunk_types:
                                console.print(f"\n[bright_magenta]分塊類型分布：[/bright_magenta]")
                                for chunk_type, count in chunk_types.items():
                                    percentage = (count / total_chunks * 100) if total_chunks > 0 else 0
                                    console.print(f"  • {chunk_type}: {count:,} ({percentage:.1f}%)")

                            # 資料庫資訊
                            db_path = stats.get('db_path', 'N/A')
                            db_size_mb = stats.get('db_size_mb', 0)
                            console.print(f"\n[bright_magenta]資料庫路徑：[/bright_magenta] {db_path}")
                            console.print(f"[bright_magenta]資料庫大小：[/bright_magenta] {db_size_mb:.2f} MB")

                            # 健康狀態提示
                            if total_chunks == 0:
                                console.print("\n[magenta]ℹ️  資料庫為空[/magenta]")
                                console.print("[dim]   提示：在 config.py 中啟用 EMBEDDING_AUTO_SAVE_CONVERSATIONS 以自動儲存對話[/dim]")
                            else:
                                console.print(f"\n[bright_magenta]✓ 資料庫運作正常[/bright_magenta]")

                            console.print("\n" + "=" * 60)

                        except Exception as e:
                            console.print(f"\n[red]✗ 獲取統計失敗：{e}[/red]")
                            import traceback
                            traceback.print_exc()

                        input("\n按 Enter 繼續...")

                    elif debug_choice == '7':
                        # 查看性能摘要
                        console.print("\n" + "=" * 60)
                        console.print("[bold bright_magenta]⚡ 性能監控摘要[/bold bright_magenta]")
                        console.print("=" * 60 + "\n")

                        try:
                            from utils.performance_monitor import get_performance_monitor
                            monitor = get_performance_monitor()
                            summary = monitor.get_summary()

                            if summary['total_operations'] == 0:
                                console.print("[magenta]⚠️  尚無性能數據[/magenta]")
                                console.print("[dim]   提示：性能監控會自動追蹤主要操作的執行時間和資源使用情況[/dim]")
                            else:
                                monitor.print_summary()

                        except Exception as e:
                            console.print(f"[red]✗ 獲取性能摘要失敗：{e}[/red]")

                        input("\n按 Enter 繼續...")

                    elif debug_choice == '8':
                        # 查看瓶頸分析報告
                        console.print("\n" + "=" * 60)
                        console.print("[bold magenta]🔍 瓶頸分析報告[/bold magenta]")
                        console.print("=" * 60 + "\n")

                        try:
                            from utils.performance_monitor import get_performance_monitor
                            monitor = get_performance_monitor()
                            summary = monitor.get_summary()

                            if summary['total_operations'] == 0:
                                console.print("[magenta]⚠️  尚無性能數據[/magenta]")
                                console.print("[dim]   提示：性能監控會自動追蹤主要操作的執行時間和資源使用情況[/dim]")
                            else:
                                monitor.print_bottleneck_report(top_n=10)

                        except Exception as e:
                            console.print(f"[red]✗ 獲取瓶頸分析失敗：{e}[/red]")

                        input("\n按 Enter 繼續...")

                    elif debug_choice == '9':
                        # 匯出性能報告
                        console.print("\n[bright_magenta]📁 匯出性能報告[/bright_magenta]\n")

                        try:
                            from utils.performance_monitor import get_performance_monitor
                            from datetime import datetime

                            monitor = get_performance_monitor()
                            summary = monitor.get_summary()

                            if summary['total_operations'] == 0:
                                console.print("[magenta]⚠️  尚無性能數據可匯出[/magenta]")
                                console.print("[dim]   提示：性能監控會自動追蹤主要操作的執行時間和資源使用情況[/dim]")
                            else:
                                # 產生檔案名稱（帶時間戳記）
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                report_path = f"performance_report_{timestamp}.json"

                                # 匯出報告
                                monitor.export_report(report_path)

                                console.print(f"\n[bright_magenta]✓ 性能報告已匯出至：[/bright_magenta]{report_path}")
                                console.print(f"[dim]   包含 {summary['total_operations']} 個操作的詳細統計資料[/dim]")

                        except Exception as e:
                            console.print(f"[red]✗ 匯出報告失敗：{e}[/red]")

                        input("\n按 Enter 繼續...")

                    else:
                        console.print("\n[magenta]無效選項[/magenta]")
                        input("\n按 Enter 繼續...")

                continue

            # 一般對話訊息 - 完整處理流程
            # 1. 解析快取即時控制
            user_input, cache_action = parse_cache_control(user_input, auto_cache_mgr)

            # 2. 解析思考模式配置
            user_input, use_thinking, thinking_budget, max_output_tokens = parse_thinking_config(user_input, model_name)

            # 3. 處理檔案附加（文字檔直接讀取，媒體檔上傳API）
            user_input, uploaded_files = process_file_attachments(user_input)

            # 3.5. 顯示相關對話建議（自動整合）
            if CONVERSATION_SUGGESTION_ENABLED and global_conversation_suggestion:
                try:
                    suggestions = global_conversation_suggestion.get_suggestions(
                        current_question=user_input,
                        session_id=None
                    )
                    if suggestions:
                        global_conversation_suggestion.display_suggestions(suggestions, show_full=False)
                except Exception as e:
                    logger.debug(f"對話建議顯示失敗: {e}")

            # 4. 處理快取即時動作
            if cache_action == 'create_now':
                if auto_cache_mgr.conversation_pairs:
                    print("\n⏳ 正在建立快取...")
                    auto_cache_mgr.create_cache(model_name)
                else:
                    print("⚠️  尚無對話內容可建立快取")

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
                print("發生錯誤，請重試")
                continue

            # 6. 記錄對話到自動快取管理器（估算 tokens）
            # 粗略估算：1 token ≈ 4 characters（英文），中文約 1.5-2 字元
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

            # 6.5b. 儲存對話到相關對話建議系統（自動整合）
            if CONVERSATION_SUGGESTION_ENABLED and global_conversation_suggestion:
                try:
                    session_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    global_conversation_suggestion.add_conversation(
                        question=user_input,
                        answer=response,
                        session_id=session_id
                    )
                except Exception as e:
                    logger.debug(f"對話建議儲存失敗: {e}")

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
                    print(f"\n🔔 已達快取門檻（{auto_cache_mgr.total_input_tokens:,} tokens），自動建立快取...")
                    auto_cache_mgr.create_cache(model_name)
                else:
                    # 提示模式：詢問用戶
                    if auto_cache_mgr.show_trigger_prompt(model_name):
                        auto_cache_mgr.create_cache(model_name)

        except KeyboardInterrupt:
            print("\n\n再見！")
            chat_logger.save_session()
            break
        except Exception as e:
            print(f"\n錯誤：{e}")


def main():
    """主程式"""
    console.print("[bold bright_magenta]Gemini 對話工具（新 SDK 版本）[/bold bright_magenta]\n")

    # 建立對話記錄器
    chat_logger = ChatLogger()

    # 初始化思考簽名管理器
    global global_thinking_signature_manager
    global_thinking_signature_manager = ThinkingSignatureManager()

    # 初始化 Codebase Embedding（如果啟用）
    codebase_embedding = None
    if CODEBASE_EMBEDDING_ENABLED and config.EMBEDDING_ENABLE_ON_STARTUP:
        try:
            cg = CodeGemini()
            codebase_embedding = cg.enable_codebase_embedding(
                vector_db_path=config.EMBEDDING_VECTOR_DB_PATH,
                api_key=API_KEY
            )
            console.print("[bright_magenta]✓ Codebase Embedding 已啟用[/bright_magenta]")
        except Exception as e:
            console.print(f"[magenta]⚠️  Codebase Embedding 啟用失敗: {e}[/magenta]")
            codebase_embedding = None

    # 選擇模型
    current_model = select_model()

    # 配置自動快取
    auto_cache_config = setup_auto_cache(current_model)

    while True:
        result = chat(current_model, chat_logger, auto_cache_config, codebase_embedding)

        if result == 'switch_model':
            current_model = select_model()
            # 切換模型後重新配置快取（因為不同模型有不同門檻）
            auto_cache_config = setup_auto_cache(current_model)
        else:
            break


if __name__ == "__main__":
    main()
