#!/usr/bin/env python3
"""
國際化 (i18n) 核心模組

負責：
1. 語言包載入與快取
2. 翻譯函數 t() / _()
3. 參數化翻譯
4. 執行期語言切換
5. 回退機制

作者: Saki-tw (with Claude Code)
日期: 2025-10-25
版本: 1.0.0
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from functools import lru_cache


class I18n:
    """國際化管理器"""

    def __init__(self, default_lang: str = "zh-TW"):
        """
        初始化 i18n 系統

        Args:
            default_lang: 預設語言代碼（zh-TW, en, ja, ko）
        """
        self.current_lang = default_lang
        self.locale_dir = Path(__file__).parent.parent / "locales"
        self._cache: Dict[str, Dict] = {}
        self._load_language(default_lang)

    def _load_yaml(self, lang: str) -> Dict:
        """
        載入 YAML 語言包

        Args:
            lang: 語言代碼

        Returns:
            語言包字典

        Raises:
            FileNotFoundError: 語言包檔案不存在
        """
        # 將 zh-TW 轉換為 zh_TW.yaml
        lang_file = lang.replace('-', '_')
        yaml_file = self.locale_dir / f"{lang_file}.yaml"

        if not yaml_file.exists():
            raise FileNotFoundError(f"語言包不存在: {yaml_file}")

        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_language(self, lang: str) -> None:
        """
        載入語言包至快取

        Args:
            lang: 語言代碼

        Note:
            如果載入失敗且不是預設語言，會回退至 zh-TW
        """
        try:
            self._cache[lang] = self._load_yaml(lang)
            self.current_lang = lang
        except FileNotFoundError:
            if lang != "zh-TW":
                print(f"⚠️  找不到 {lang} 語言包，回退至繁體中文")
                self._load_language("zh-TW")
            else:
                raise

    def t(self, key: str, **kwargs) -> str:
        """
        翻譯函數（主要接口）

        Args:
            key: 翻譯鍵值（支援點號路徑，如 "chat.welcome"）
            **kwargs: 參數化變數

        Returns:
            翻譯後的字串

        Examples:
            >>> i18n.t("chat.welcome")
            '歡迎使用 ChatGemini！'

            >>> i18n.t("pricing.cost_line", currency="NT$", twd="12.34", usd="0.40")
            '💰 成本: NT$12.34 ($0.40 USD)'
        """
        keys = key.split('.')
        data = self._cache.get(self.current_lang, {})

        # 遍歷巢狀字典
        for k in keys:
            if isinstance(data, dict):
                data = data.get(k)
            else:
                break

        # 找不到翻譯，返回 key
        if data is None:
            return f"[MISSING: {key}]"

        # 不是字串（可能是字典），返回 key
        if not isinstance(data, str):
            return f"[INVALID: {key}]"

        # 參數化替換
        if kwargs:
            try:
                return data.format(**kwargs)
            except (KeyError, ValueError) as e:
                # 參數化失敗，返回原始字串
                return data

        return data

    def switch_language(self, lang: str) -> bool:
        """
        切換語言

        Args:
            lang: 語言代碼（zh-TW, en, ja, ko）

        Returns:
            是否成功切換
        """
        try:
            # 如果語言包已在快取中，直接切換
            if lang in self._cache:
                self.current_lang = lang
                return True

            # 否則載入語言包
            self._load_language(lang)
            return True
        except Exception as e:
            print(f"❌ 切換語言失敗: {e}")
            return False

    def get_available_languages(self) -> list:
        """
        取得可用語言清單

        Returns:
            語言代碼列表
        """
        langs = []
        for yaml_file in self.locale_dir.glob("*.yaml"):
            lang_code = yaml_file.stem.replace('_', '-')
            langs.append(lang_code)
        return sorted(langs)

    def get_language_name(self, lang: str = None) -> str:
        """
        取得語言名稱

        Args:
            lang: 語言代碼（None 表示當前語言）

        Returns:
            語言名稱
        """
        lang = lang or self.current_lang
        data = self._cache.get(lang, {})
        return data.get('meta', {}).get('name', lang)

    def get_current_language(self) -> str:
        """
        取得當前語言代碼

        Returns:
            語言代碼
        """
        return self.current_lang


# ============================================================================
# 全域單例
# ============================================================================

_i18n_instance: Optional[I18n] = None


def init_i18n(lang: str = None, inject_builtins: bool = True) -> I18n:
    """
    初始化 i18n 系統

    Args:
        lang: 語言代碼（None 表示自動偵測）
        inject_builtins: 是否將 t() 函數注入到 builtins 中（預設 True）

    Returns:
        I18n 實例

    優先級：
        1. 明確指定的語言參數
        2. config.py 的三層配置系統（環境變數 > 使用者配置 > 系統預設）
        3. 自動偵測系統語言
    """
    global _i18n_instance

    if lang is None:
        # 先確保 .env 已載入
        try:
            from pathlib import Path
            from dotenv import load_dotenv
            import os

            project_root = Path(__file__).parent.parent
            env_file = project_root / '.env'
            if env_file.exists():
                load_dotenv(env_file, override=False)  # 不覆蓋已存在的環境變數
        except Exception:
            pass  # 如果載入失敗，繼續執行

        # 嘗試從 config.py 讀取語言設定
        try:
            import sys
            from pathlib import Path
            # 確保 project root 在 sys.path 中
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from config import get_language
            lang = get_language()
        except Exception:
            # 如果無法讀取 config，回退到自動偵測
            from utils.locale_detector import detect_system_language
            lang = detect_system_language()

    _i18n_instance = I18n(default_lang=lang)

    # 將 t() 函數注入到 builtins，讓所有模組都可以直接使用
    if inject_builtins:
        import builtins
        builtins.t = t
        builtins._ = _

    return _i18n_instance


def get_i18n() -> I18n:
    """
    取得 i18n 實例

    Returns:
        I18n 實例

    Note:
        如果尚未初始化，會自動初始化
    """
    global _i18n_instance

    if _i18n_instance is None:
        _i18n_instance = init_i18n()

    return _i18n_instance


def t(key: str, **kwargs) -> str:
    """
    翻譯函數快捷方式

    Args:
        key: 翻譯鍵值
        **kwargs: 參數化變數

    Returns:
        翻譯後的字串

    Examples:
        >>> from utils.i18n import t
        >>> t("chat.welcome")
        '歡迎使用 ChatGemini！'
    """
    return get_i18n().t(key, **kwargs)


# 別名（符合 i18n 慣例）
_ = t


def switch_language(lang: str, save_to_env: bool = False) -> bool:
    """
    切換語言（全域函數）

    Args:
        lang: 語言代碼
        save_to_env: 是否將設定保存到 .env 檔案

    Returns:
        是否成功切換
    """
    success = get_i18n().switch_language(lang)

    if success:
        # 重新注入 builtins，確保所有模組使用新語言
        import builtins
        if hasattr(builtins, 't'):
            builtins.t = t
            builtins._ = _

        # 保存到 .env
        if save_to_env:
            _save_language_to_env(lang)

    return success


def get_current_language() -> str:
    """
    取得當前語言（全域函數）

    Returns:
        語言代碼
    """
    return get_i18n().get_current_language()


def get_available_languages() -> list:
    """
    取得可用語言清單（全域函數）

    Returns:
        語言代碼列表
    """
    return get_i18n().get_available_languages()


# ============================================================================
# 工具函數
# ============================================================================

def _save_language_to_env(lang: str) -> bool:
    """
    保存語言設定到 .env 檔案

    Args:
        lang: 語言代碼

    Returns:
        是否成功保存
    """
    try:
        # 定位 .env 檔案
        project_root = Path(__file__).parent.parent
        env_file = project_root / '.env'

        # 讀取現有內容
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []

        # 更新或添加 GEMINI_LANG
        lang_line = f'GEMINI_LANG={lang}\n'
        updated = False

        for i, line in enumerate(lines):
            if line.startswith('GEMINI_LANG='):
                lines[i] = lang_line
                updated = True
                break

        if not updated:
            # 如果沒有找到，添加到最後
            # 確保檔案結尾有換行
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.append(lang_line)

        # 寫回檔案
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"⚠️  保存語言設定到 .env 失敗: {e}")
        return False


def is_language_available(lang: str) -> bool:
    """
    檢查語言是否可用

    Args:
        lang: 語言代碼

    Returns:
        是否可用
    """
    return lang in get_available_languages()


def get_language_info(lang: str = None) -> Dict[str, Any]:
    """
    取得語言資訊

    Args:
        lang: 語言代碼（None 表示當前語言）

    Returns:
        語言資訊字典
    """
    i18n = get_i18n()
    lang = lang or i18n.current_lang

    # 確保語言包已載入
    if lang not in i18n._cache:
        try:
            i18n._load_language(lang)
        except Exception:
            return {}

    meta = i18n._cache[lang].get('meta', {})
    return {
        'code': lang,
        'name': meta.get('name', lang),
        'native_name': meta.get('native_name', meta.get('name', lang)),
        'version': meta.get('version', '1.0.0'),
        'author': meta.get('author', 'Unknown'),
    }


if __name__ == "__main__":
    # 簡單測試
    print("=" * 60)
    print("i18n 模組測試")
    print("=" * 60)

    # 初始化（繁中）
    i18n = init_i18n('zh-TW')
    print(f"當前語言: {i18n.get_current_language()}")
    print(f"語言名稱: {i18n.get_language_name()}")

    # 測試翻譯（需要先有語言包）
    print(f"\n測試翻譯:")
    print(f"  chat.welcome = {t('chat.welcome')}")

    # 測試可用語言
    print(f"\n可用語言: {get_available_languages()}")

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)
