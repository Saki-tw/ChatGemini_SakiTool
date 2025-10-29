#!/usr/bin/env python3
"""
啟動效能剖析工具
在 gemini_chat.py 的各個階段插入計時點,找出真正的瓶頸
"""
import time
import sys

# 記錄整體開始時間
GLOBAL_START = time.time()
checkpoints = {}

def checkpoint(name):
    """記錄檢查點時間"""
    elapsed = time.time() - GLOBAL_START
    checkpoints[name] = elapsed
    print(f"⏱️  [{elapsed:6.3f}s] {name}")

checkpoint("0. 開始執行")

# ==========================================
# 開始模擬 gemini_chat.py 的載入流程
# ==========================================

checkpoint("1. 導入基礎模組 (sys, os, json, etc)")
import os
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

checkpoint("2. 導入 dotenv")
from dotenv import load_dotenv

checkpoint("3. 導入 rich")
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

checkpoint("4. 導入 utils (觸發 i18n 初始化)")
# 這裡會觸發 i18n 的自動初始化
import utils

checkpoint("5. 導入 safe_t")
from utils import safe_t

checkpoint("6. 導入 gemini_module_loader")
from gemini_module_loader import ModuleLoader

checkpoint("7. 嘗試載入 gemini_tools")
try:
    from gemini_tools import auto_tool_manager, prepare_tools_for_input, cleanup_tools
except ImportError:
    pass

checkpoint("8. 載入 config_unified")
try:
    from config_unified import unified_config as config
except ImportError:
    class config:
        @staticmethod
        def get(key, default=None):
            return default
        MODULES = {}

checkpoint("9. 導入 prompt_toolkit")
try:
    from prompt_toolkit import prompt, PromptSession
    from prompt_toolkit.history import InMemoryHistory
except ImportError:
    pass

checkpoint("10. 導入 google.genai SDK")
from google import genai
from google.genai import types

checkpoint("11. 導入 psutil")
import psutil

checkpoint("12. 載入 gemini_checkpoint")
try:
    from gemini_checkpoint import get_checkpoint_manager, CheckpointManager
except ImportError:
    pass

checkpoint("13. 載入 interactive_language_menu")
try:
    from interactive_language_menu import show_language_menu
except ImportError:
    pass

checkpoint("14. 條件載入 - gemini_pricing")
try:
    from gemini_pricing import PricingCalculator
except ImportError:
    pass

checkpoint("15. 條件載入 - gemini_cache_manager")
try:
    from gemini_cache_manager import CacheManager
except ImportError:
    pass

checkpoint("16. 條件載入 - gemini_file_manager")
try:
    from gemini_file_manager import FileManager
except ImportError:
    pass

checkpoint("17. 條件載入 - gemini_translator")
try:
    from gemini_translator import get_translator
except ImportError:
    pass

checkpoint("18. 條件載入 - gemini_media_viewer")
try:
    from gemini_media_viewer import MediaViewer
except ImportError:
    pass

checkpoint("19. 載入 CodeGemini")
try:
    from CodeGemini import CodeGemini
except ImportError:
    pass

checkpoint("20. 載入 error_fix_suggestions")
try:
    from error_fix_suggestions import ErrorLogger
except ImportError:
    pass

checkpoint("21. 載入 utils.api_retry")
try:
    from utils.api_retry import with_retry
except ImportError:
    pass

checkpoint("22. 載入 error_diagnostics")
try:
    from error_diagnostics import ErrorDiagnostics
except ImportError:
    pass

checkpoint("23. 載入 gemini_smart_triggers")
try:
    import gemini_smart_triggers
except ImportError:
    pass

checkpoint("24. 載入 .env")
load_dotenv()

checkpoint("25. 初始化 API 客戶端")
API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
if API_KEY:
    client = genai.Client(api_key=API_KEY)

checkpoint("26. 完成所有初始化")

# ==========================================
# 分析結果
# ==========================================
print("\n" + "=" * 80)
print("啟動效能分析報告")
print("=" * 80)

# 計算每個階段的耗時
prev_time = 0
print(f"\n{'階段':<50} {'累計時間':<12} {'階段耗時':<12}")
print("-" * 80)

for name, elapsed in checkpoints.items():
    stage_time = elapsed - prev_time
    print(f"{name:<50} {elapsed:>8.3f}s    {stage_time:>8.3f}s")
    prev_time = elapsed

total_time = checkpoints["26. 完成所有初始化"]
print("-" * 80)
print(f"{'總啟動時間':<50} {total_time:>8.3f}s")
print("=" * 80)

# 找出最慢的階段
slow_stages = []
prev_time = 0
for name, elapsed in checkpoints.items():
    stage_time = elapsed - prev_time
    if stage_time > 0.1:  # 超過 100ms 的階段
        slow_stages.append((name, stage_time))
    prev_time = elapsed

if slow_stages:
    print("\n⚠️  慢速階段 (>100ms):")
    for name, duration in sorted(slow_stages, key=lambda x: x[1], reverse=True):
        percentage = (duration / total_time) * 100
        print(f"  {name:<50} {duration:>8.3f}s ({percentage:>5.1f}%)")

print("\n💡 結論:")
if total_time > 5:
    print(f"  啟動時間過長 ({total_time:.1f}秒),需要優化")
elif total_time > 3:
    print(f"  啟動時間偏慢 ({total_time:.1f}秒),建議優化")
else:
    print(f"  啟動時間可接受 ({total_time:.1f}秒)")
print("=" * 80)
