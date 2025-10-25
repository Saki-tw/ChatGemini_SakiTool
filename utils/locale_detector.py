#!/usr/bin/env python3
"""
系統語言偵測模組

負責：
1. 偵測系統語言設定
2. 環境變數讀取
3. 語言代碼正規化

作者: Saki-tw (with Claude Code)
日期: 2025-10-25
版本: 1.0.0
"""

import os
import locale
import subprocess
from typing import Optional


# ============================================================================
# 語言代碼映射表
# ============================================================================

LANG_MAP = {
    'zh_TW': 'zh-TW',
    'zh_HK': 'zh-TW',  # 香港繁中 → 台灣繁中
    'zh_CN': 'zh-TW',  # 簡中暫時對應繁中（未來可擴展）
    'en_US': 'en',
    'en_GB': 'en',
    'en_AU': 'en',
    'en_CA': 'en',
    'ja_JP': 'ja',
    'ko_KR': 'ko',
}

# 支援的語言列表
SUPPORTED_LANGS = ['zh-TW', 'en', 'ja', 'ko']


# ============================================================================
# 主要偵測函數
# ============================================================================

def detect_system_language() -> str:
    """
    偵測系統語言

    偵測順序：
    1. 環境變數 GEMINI_LANG
    2. 環境變數 LANG
    3. macOS: defaults read -g AppleLocale
    4. Linux: locale
    5. 預設值 zh-TW

    Returns:
        語言代碼（zh-TW, en, ja, ko）

    Examples:
        >>> detect_system_language()
        'zh-TW'
    """

    # 1. 檢查 GEMINI_LANG 環境變數（最高優先權）
    gemini_lang = os.getenv('GEMINI_LANG')
    if gemini_lang and gemini_lang in SUPPORTED_LANGS:
        return gemini_lang

    # 2. 檢查 LANG 環境變數
    lang_env = os.getenv('LANG', '')
    if lang_env:
        lang_code = _parse_locale(lang_env)
        if lang_code:
            return lang_code

    # 3. macOS 特殊處理
    if os.uname().sysname == 'Darwin':
        try:
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleLocale'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                locale_str = result.stdout.strip()
                lang_code = _parse_locale(locale_str)
                if lang_code:
                    return lang_code
        except Exception:
            pass

    # 4. Python locale 模組
    try:
        sys_locale = locale.getdefaultlocale()[0]
        if sys_locale:
            lang_code = _parse_locale(sys_locale)
            if lang_code:
                return lang_code
    except Exception:
        pass

    # 5. 預設值（符合天條 3：使用最好的預設值）
    return 'zh-TW'


def _parse_locale(locale_str: str) -> Optional[str]:
    """
    解析 locale 字串

    Args:
        locale_str: locale 字串（如 zh_TW.UTF-8, en_US, ja_JP.eucJP）

    Returns:
        語言代碼（zh-TW, en, ja, ko）或 None

    Examples:
        >>> _parse_locale('zh_TW.UTF-8')
        'zh-TW'

        >>> _parse_locale('en_US')
        'en'

        >>> _parse_locale('ja_JP.eucJP')
        'ja'

        >>> _parse_locale('ko_KR')
        'ko'
    """
    if not locale_str:
        return None

    # 移除編碼部分（如 .UTF-8, .eucJP）
    locale_str = locale_str.split('.')[0]

    # 映射至支援的語言
    mapped = LANG_MAP.get(locale_str)
    if mapped and mapped in SUPPORTED_LANGS:
        return mapped

    # 嘗試只取前兩碼
    lang_short = locale_str[:2].lower()
    if lang_short == 'zh':
        return 'zh-TW'  # 預設繁中
    elif lang_short in ['en', 'ja', 'ko']:
        return lang_short

    return None


# ============================================================================
# 輔助函數
# ============================================================================

def get_language_prompt(detected_lang: str) -> str:
    """
    取得語言確認提示（用於 INSTALL.sh）

    Args:
        detected_lang: 偵測到的語言代碼

    Returns:
        多語系提示字串

    Examples:
        >>> get_language_prompt('zh-TW')
        '✓ 偵測到繁體中文，使用繁體中文介面'

        >>> get_language_prompt('en')
        '✓ Detected English, using English interface'
    """
    prompts = {
        'zh-TW': '✓ 偵測到繁體中文，使用繁體中文介面',
        'en': '✓ Detected English, using English interface',
        'ja': '✓ 日本語を検出しました、日本語インターフェースを使用します',
        'ko': '✓ 한국어 감지됨, 한국어 인터페이스 사용',
    }

    return prompts.get(detected_lang, prompts['zh-TW'])


def validate_language_code(lang: str) -> bool:
    """
    驗證語言代碼是否有效

    Args:
        lang: 語言代碼

    Returns:
        是否有效

    Examples:
        >>> validate_language_code('zh-TW')
        True

        >>> validate_language_code('fr')
        False
    """
    return lang in SUPPORTED_LANGS


def normalize_language_code(lang: str) -> str:
    """
    正規化語言代碼

    Args:
        lang: 語言代碼（可能格式不正確）

    Returns:
        正規化的語言代碼

    Examples:
        >>> normalize_language_code('zh_TW')
        'zh-TW'

        >>> normalize_language_code('zh-tw')
        'zh-TW'

        >>> normalize_language_code('EN')
        'en'
    """
    # 轉換 underscore 為 hyphen
    lang = lang.replace('_', '-')

    # 處理大小寫
    if lang.lower() in ['zh-tw', 'zhtw']:
        return 'zh-TW'
    elif lang.lower() in ['en', 'english']:
        return 'en'
    elif lang.lower() in ['ja', 'japanese']:
        return 'ja'
    elif lang.lower() in ['ko', 'korean']:
        return 'ko'

    # 如果已經正確，直接返回
    if lang in SUPPORTED_LANGS:
        return lang

    # 預設值
    return 'zh-TW'


# ============================================================================
# 測試與除錯
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("語言偵測模組測試")
    print("=" * 60)

    # 測試系統語言偵測
    detected = detect_system_language()
    print(f"\n偵測到的語言: {detected}")
    print(f"提示訊息: {get_language_prompt(detected)}")

    # 測試環境變數
    print(f"\nGEMINI_LANG: {os.getenv('GEMINI_LANG', '(未設定)')}")
    print(f"LANG: {os.getenv('LANG', '(未設定)')}")

    # 測試 locale 解析
    print(f"\n測試 locale 解析:")
    test_locales = [
        'zh_TW.UTF-8',
        'en_US',
        'ja_JP.eucJP',
        'ko_KR',
        'zh_CN.GB2312',
    ]
    for test_locale in test_locales:
        parsed = _parse_locale(test_locale)
        print(f"  {test_locale:20s} -> {parsed}")

    # 測試語言代碼驗證
    print(f"\n測試語言代碼驗證:")
    test_codes = ['zh-TW', 'en', 'ja', 'ko', 'fr', 'de']
    for code in test_codes:
        valid = validate_language_code(code)
        status = "✓" if valid else "✗"
        print(f"  {status} {code}")

    # 測試正規化
    print(f"\n測試語言代碼正規化:")
    test_normalize = ['zh_TW', 'zh-tw', 'EN', 'japanese', 'Korean']
    for code in test_normalize:
        normalized = normalize_language_code(code)
        print(f"  {code:15s} -> {normalized}")

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)
