#!/usr/bin/env python3
"""
Gemini 思考過程翻譯模組 v2.2
支援免費優先的自動切換架構：
  主引擎：deep-translator (完全免費,無需帳號)
  備用：返回英文原文

v2.2 更新：
- ✨ 新增 Rich UI 輸出,大幅提升使用者體驗
- ✨ 新增進度提示與狀態顯示
- ✨ 新增 Markdown 渲染支援
- ✨ 新增錯誤訊息美化
- ✨ 新增互動式狀態面板

v2.1 更新：
- deep-translator 設為主引擎（完全免費,易用）
- 單次快取機制（僅保存當前 Prompt,發送新 Prompt 時自動清除）
- 優化快取 key 生成（使用完整文本 MD5 hash,避免碰撞）
- 支援 Ctrl+T 雙語對照（顯示繁中 + 英文原文）
"""
import os
import logging
import hashlib
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from utils.i18n import safe_t
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich import print as rprint

# i18n 國際化支援
try:
    from utils import safe_t
except ImportError:
    # 降級：提供簡單的 fallback 函數
    def safe_t(key: str, fallback: str = None, **kwargs):
        if fallback is None:
            fallback = key.split('.')[-1]
        try:
            return fallback.format(**kwargs)
        except:
            return fallback

# 設定日誌
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

# 初始化 Rich Console
console = Console()

# 導入統一的錯誤修復建議系統
try:
    from error_fix_suggestions import (
        suggest_dependency_missing,
        ErrorLogger
    )
    ERROR_FIX_ENABLED = True
except ImportError:
    ERROR_FIX_ENABLED = False

# 初始化錯誤記錄器
error_logger = ErrorLogger() if ERROR_FIX_ENABLED else None


class ThinkingTranslator:
    """
    思考過程翻譯器（免費優先架構）

    引擎優先順序：
    1. deep-translator (主引擎)
       - 100% 免費,無使用限制
       - 不需要任何帳號或 API key
       - 使用 Google Translate 非官方介面
       - 穩定性高

    2. 返回原文 (備用)
       - 當翻譯引擎失敗時
       - 顯示英文原文而非報錯

    快取機制（單次快取）：
    - 僅保存當前 Prompt 的翻譯結果
    - 發送新 Prompt 時自動清除舊快取
    - 使用完整文本的 MD5 hash 作為 key（避免碰撞）
    - Ctrl+T 第二次按時使用快取（不重複翻譯）
    """

    def __init__(self):
        self.current_prompt_cache: Dict[str, str] = {}  # 單次快取（僅當前 Prompt）
        self.translation_count = 0  # 已翻譯字元數（統計用）
        self.current_engine = None  # 當前使用的引擎
        self.engine_status: Dict[str, str] = {}  # 引擎狀態記錄
        self.translation_enabled = True  # 翻譯開關（預設啟用）

        # === 初始化主引擎：deep-translator ===
        self.deep_translator_available = False
        try:
            from deep_translator import GoogleTranslator
            # 測試是否可用
            GoogleTranslator(source='en', target='zh-TW')
            self.deep_translator_available = True
            self.current_engine = "deep-translator"
            self.engine_status['deep_translator'] = safe_t('translator.engine_status_main', fallback="✅ 主引擎（免費）")
            logger.info(safe_t('translator.engine_ready', fallback="✅ deep-translator 已就緒（主引擎,完全免費）"))
            console.print(f"[dim green]{safe_t('translator.engine_loaded', fallback='✓ 翻譯引擎已載入：deep-translator')}[/dim green]")
        except ImportError:
            self.engine_status['deep_translator'] = safe_t('translator.engine_not_installed', fallback="❌ 未安裝 deep-translator")
            logger.warning(safe_t('translator.install_prompt', fallback="❌ 未安裝 deep-translator,請執行：pip install deep-translator"))

            # 使用 Rich UI 顯示錯誤
            console.print(f"[#E8C4F0]{safe_t('translator.engine_missing', fallback='⚠️  翻譯引擎未安裝')}[/#E8C4F0]")

            # 顯示依賴缺失的修復建議
            if ERROR_FIX_ENABLED:
                suggest_dependency_missing('deep-translator', 'pip install deep-translator')
        except Exception as e:
            self.engine_status['deep_translator'] = safe_t('translator.test_failed', fallback="❌ 測試失敗: {error}", error=str(e))
            logger.warning(safe_t('translator.test_failed', fallback="deep-translator 測試失敗: {error}", error=str(e)))
            console.print(f"[dim #E8C4F0]{safe_t('translator.load_failed', fallback='❌ 翻譯引擎載入失敗: {error}', error=str(e))}[/red]")

        # === 備用：返回原文（始終可用）===
        self.engine_status['fallback'] = safe_t('translator.fallback_ready', fallback="✅ 備用方案")
        if not self.deep_translator_available:
            self.current_engine = safe_t('translator.no_translation', fallback="原文顯示（無翻譯）")
            logger.warning(safe_t('translator.no_engine', fallback="⚠️  無可用翻譯引擎,將顯示英文原文"))

    def toggle_translation(self) -> bool:
        """
        切換翻譯功能開關

        Returns:
            切換後的狀態（True=啟用,False=停用）
        """
        self.translation_enabled = not self.translation_enabled
        status = safe_t('common.enabled' if self.translation_enabled else 'common.disabled',
                       fallback="啟用" if self.translation_enabled else "停用")
        logger.info(safe_t('translator.toggle_status', fallback="翻譯功能已{status}", status=status))
        return self.translation_enabled

    def set_translation(self, enabled: bool):
        """
        設定翻譯功能開關

        Args:
            enabled: True=啟用,False=停用
        """
        self.translation_enabled = enabled
        status = safe_t('common.enabled' if enabled else 'common.disabled',
                       fallback="啟用" if enabled else "停用")
        logger.info(safe_t('translator.set_status', fallback="翻譯功能已{status}", status=status))

    def clear_current_prompt_cache(self):
        """
        清除當前 Prompt 的快取

        用途：發送新 Prompt 時調用,清除舊的翻譯快取
        """
        if self.current_prompt_cache:
            cache_count = len(self.current_prompt_cache)
            self.current_prompt_cache.clear()
            logger.debug(safe_t('translator.cache_cleared',
                              fallback="已清除當前 Prompt 快取（{count} 個項目）",
                              count=cache_count))

    def translate(self, text: str, source_lang: str = 'en', target_lang: str = 'zh-TW') -> str:
        """
        翻譯文字（使用單次快取機制）

        Args:
            text: 要翻譯的文字
            source_lang: 來源語言代碼（預設 'en'）
            target_lang: 目標語言代碼（預設 'zh-TW' 繁體中文）

        Returns:
            翻譯後的文字,失敗則返回原文
        """
        # 檢查是否啟用翻譯
        if not self.translation_enabled:
            logger.debug(safe_t('translator.disabled_return_original',
                              fallback="翻譯功能已停用,返回原文"))
            return text

        if not text or not text.strip():
            return text

        # 使用完整文本的 MD5 hash 作為 cache key（避免碰撞）
        cache_key = hashlib.md5(f"{source_lang}:{target_lang}:{text}".encode('utf-8')).hexdigest()

        # 檢查單次快取
        if cache_key in self.current_prompt_cache:
            logger.debug(safe_t('translator.use_cache',
                              fallback="✅ 使用當前 Prompt 快取（節省翻譯時間）"))
            return self.current_prompt_cache[cache_key]

        # === 嘗試主引擎：deep-translator ===
        if self.deep_translator_available:
            result = self._translate_with_deep_translator(text, source_lang, target_lang)
            if result:
                self.current_prompt_cache[cache_key] = result  # 儲存到單次快取
                self.translation_count += len(text)
                logger.debug(safe_t('translator.translate_cached',
                                  fallback="✅ 翻譯成功並快取 ({chars} 字元)",
                                  chars=len(text)))
                return result
            else:
                logger.warning(safe_t('translator.fallback_original',
                                    fallback="deep-translator 失敗,使用備用方案（原文）"))

        # === 備用：返回原文 ===
        logger.info(safe_t('translator.engine_failed',
                          fallback="翻譯引擎失敗,返回英文原文"))
        return text  # 返回原文而非 None

    def _translate_with_deep_translator(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """使用 deep-translator 翻譯（主引擎）"""
        try:
            from deep_translator import GoogleTranslator

            # deep-translator 語言代碼：zh-TW (繁體中文) / en (英文)
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_text = translator.translate(text)

            logger.debug(safe_t('translator.success',
                              fallback="✅ deep-translator 翻譯成功 ({chars} 字元)",
                              chars=len(text)))

            return translated_text

        except Exception as e:
            logger.error(safe_t('translator.error',
                              fallback="❌ deep-translator 錯誤: {error}",
                              error=str(e)))
            self.engine_status['deep_translator'] = safe_t('translator.runtime_error',
                                                           fallback="❌ 運行錯誤: {error}",
                                                           error=str(e))
            return None

    def get_status(self) -> Dict:
        """
        獲取翻譯器狀態

        Returns:
            包含狀態資訊的字典
        """
        return {
            'translation_enabled': self.translation_enabled,
            'current_engine': self.current_engine or "無可用引擎",
            'engines': self.engine_status.copy(),
            'translated_chars': self.translation_count,
            'current_cache_size': len(self.current_prompt_cache)  # 單次快取大小
        }

    def clear_cache(self):
        """清除翻譯快取（與 clear_current_prompt_cache 相同,保留向後相容）"""
        self.clear_current_prompt_cache()

    def is_available(self) -> bool:
        """檢查是否有可用的翻譯引擎"""
        return self.deep_translator_available

    def get_engine_list(self) -> List[str]:
        """獲取可用引擎列表"""
        engines = []
        if self.deep_translator_available:
            engines.append("deep-translator (主引擎,免費)")
        engines.append("原文顯示 (備用)")
        return engines

    def print_status_panel(self):
        """使用 Rich UI 顯示翻譯器狀態面板"""
        status = self.get_status()

        # 建立狀態表格
        table = Table(title="🌐 翻譯器狀態", show_header=True, header_style="bold #E8C4F0")
        console_width = console.width or 120
        table.add_column("項目", style="#E8C4F0", width=max(18, int(console_width * 0.25)))
        table.add_column("狀態", style="#E8C4F0")

        # 翻譯功能狀態
        status_icon = "✅ 啟用" if status['translation_enabled'] else "❌ 停用"
        table.add_row("翻譯功能", status_icon)

        # 當前引擎
        table.add_row("當前引擎", f"[#B565D8]{status['current_engine']}[/green]")

        # 引擎狀態
        for engine, state in status['engines'].items():
            engine_name = engine.replace('_', ' ').title()
            table.add_row(f"  └─ {engine_name}", state)

        # 使用統計
        table.add_row("已翻譯字元數", f"[#E8C4F0]{status['translated_chars']:,}[/#E8C4F0]")
        table.add_row("快取項目數", f"[#E8C4F0]{status['current_cache_size']}[/#E8C4F0]")

        console.print(table)

    def print_translation_with_rich(self, original: str, translated: str, show_original: bool = False):
        """
        使用 Rich UI 顯示翻譯結果

        Args:
            original: 原文
            translated: 翻譯結果
            show_original: 是否顯示原文對照
        """
        if show_original:
            # 雙語對照模式
            console.print(Panel(
                Markdown(f"**原文：**\n{original}\n\n**翻譯：**\n{translated}"),
                title="[bold #E8C4F0]雙語對照[/bold #E8C4F0]",
                border_style="#E8C4F0"
            ))
        else:
            # 僅顯示翻譯（使用 Markdown 渲染）
            console.print(Markdown(translated))

    def translate_with_progress(self, text: str, source_lang: str = 'en', target_lang: str = 'zh-TW') -> str:
        """
        帶進度提示的翻譯（適用於長文本）

        Args:
            text: 要翻譯的文字
            source_lang: 來源語言代碼
            target_lang: 目標語言代碼

        Returns:
            翻譯結果
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[#E8C4F0]翻譯中...", total=None)

            result = self.translate(text, source_lang, target_lang)

            progress.update(task, completed=True)

        return result


# ============================================================
# 全域翻譯器實例（單例模式）
# ============================================================

_translator_instance = None


def get_translator() -> ThinkingTranslator:
    """
    獲取全域翻譯器實例（單例模式）

    Returns:
        ThinkingTranslator 實例
    """
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = ThinkingTranslator()
    return _translator_instance


def translate_thinking(text: str) -> str:
    """
    便捷函數：翻譯思考過程（英文 → 當前 i18n 語言）

    Args:
        text: 英文思考過程文字

    Returns:
        翻譯後的文字（根據當前 i18n 語言）,失敗則返回原文
    """
    # 獲取當前 i18n 語言設定
    target_lang = 'zh-TW'  # 預設為繁體中文
    try:
        from utils import get_current_language
        current_lang = get_current_language()

        # 將 i18n 語言代碼轉換為翻譯引擎語言代碼
        lang_mapping = {
            'zh-TW': 'zh-TW',  # 繁體中文
            'en': 'en',        # 英文（不需要翻譯）
            'ja': 'ja',        # 日文
            'ko': 'ko'         # 韓文
        }
        target_lang = lang_mapping.get(current_lang, 'zh-TW')

        # 如果目標語言是英文,直接返回原文（不需要翻譯）
        if target_lang == 'en':
            return text

    except Exception as e:
        logger.debug(safe_t('translator.i18n_fallback',
                          fallback="無法獲取 i18n 語言,使用預設 zh-TW: {error}",
                          error=str(e)))

    translator = get_translator()
    return translator.translate(text, source_lang='en', target_lang=target_lang)


# ============================================================
# 測試程式碼
# ============================================================

if __name__ == "__main__":
    # 設定日誌級別
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 使用 Rich UI 顯示標題
    console.print(Panel(
        "[bold #E8C4F0]思考過程翻譯器測試 v2.2[/bold #E8C4F0]\n\n"
        "[dim]使用 Rich UI 提升使用體驗[/dim]",
        title="🌐 Gemini Translator",
        border_style="#E8C4F0"
    ))

    translator = get_translator()

    # 使用 Rich UI 顯示狀態
    console.print("\n")
    translator.print_status_panel()

    # 測試翻譯功能
    console.print("\n")
    console.print(Panel(
        "[bold #E8C4F0]測試翻譯功能[/bold #E8C4F0]",
        border_style="#E8C4F0"
    ))

    test_cases = [
        "Let me think about this problem step by step.",
        "First, I need to understand the requirements.",
        "The algorithm has O(n log n) time complexity."
    ]

    for i, test_text in enumerate(test_cases, 1):
        console.print(f"\n[bold #E8C4F0]{safe_t('translator.test_num', fallback='測試 {num}:', num=i)}[/bold #E8C4F0]")
        console.print(f"[dim]{safe_t('translator.original', fallback='原文')}：[/dim] {test_text}")

        # 使用帶進度提示的翻譯
        result = translator.translate_with_progress(test_text)

        console.print(safe_t('common.message', fallback='[#B565D8]翻譯：[/green] {result}', result=result))
        console.print(safe_t('common.message', fallback='[dim]引擎：{translator.current_engine}[/dim]', current_engine=translator.current_engine))

    # 測試雙語對照
    console.print("\n")
    console.print(Panel(
        "[bold #E8C4F0]測試雙語對照模式[/bold #E8C4F0]",
        border_style="#E8C4F0"
    ))

    test_text = "This is a test for bilingual display mode."
    result = translator.translate(test_text)
    translator.print_translation_with_rich(test_text, result, show_original=True)

    # 測試翻譯開關
    console.print("\n")
    console.print(Panel(
        "[bold #E8C4F0]測試翻譯開關[/bold #E8C4F0]",
        border_style="#E8C4F0"
    ))

    status_text = "✅ 啟用" if translator.translation_enabled else "❌ 停用"
    console.print(f"[#E8C4F0]當前狀態:[/#E8C4F0] {status_text}")
    translator.toggle_translation()
    status_text = "✅ 啟用" if translator.translation_enabled else "❌ 停用"
    console.print(f"[#E8C4F0]切換後:[/#E8C4F0] {status_text}")

    test_text = "Testing translation toggle."
    console.print(safe_t('common.message', fallback='\n[dim]原文：[/dim] {test_text}', test_text=test_text))
    result = translator.translate(test_text)
    console.print(safe_t('common.message', fallback='[#E8C4F0]結果：[/#E8C4F0] {result} [dim](應顯示原文)[/dim]', result=result))

    translator.toggle_translation()
    status_text = "✅ 啟用" if translator.translation_enabled else "❌ 停用"
    console.print(f"\n[#E8C4F0]再次切換:[/#E8C4F0] {status_text}")
    result = translator.translate(test_text)
    console.print(safe_t('common.message', fallback='[#E8C4F0]結果：[/#E8C4F0] {result} [dim](應顯示翻譯)[/dim]', result=result))

    # 最終狀態
    console.print("\n")
    translator.print_status_panel()

    console.print("\n")
    console.print(Panel(
        "[bold green]✅ 測試完成！[/bold green]",
        border_style="#E8C4F0"
    ))
