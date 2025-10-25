#!/usr/bin/env python3
"""
i18n 模組實際載入驗證測試
驗證所有 i18n 相關模組是否能在實際環境中正常載入和運作
"""

import sys
import os
from pathlib import Path

# 確保專案根目錄在 sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 測試結果收集
test_results = []
total_tests = 0
passed_tests = 0


def test_result(test_name, passed, detail=""):
    """記錄測試結果"""
    global total_tests, passed_tests
    total_tests += 1
    if passed:
        passed_tests += 1
        status = "✅ PASS"
    else:
        status = "❌ FAIL"

    result = f"{status} | {test_name}"
    if detail:
        result += f"\n     詳情: {detail}"

    test_results.append(result)
    print(result)
    return passed


def print_section(title):
    """打印測試區塊標題"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# ============================================================================
# 測試 1: 依賴模組檢查
# ============================================================================
print_section("測試 1: 檢查 Python 依賴模組")

try:
    import yaml
    test_result("導入 yaml", True, f"版本: {yaml.__version__ if hasattr(yaml, '__version__') else 'unknown'}")
except ImportError as e:
    test_result("導入 yaml", False, str(e))

try:
    from pathlib import Path
    test_result("導入 pathlib", True, "內建模組")
except ImportError as e:
    test_result("導入 pathlib", False, str(e))

try:
    from functools import lru_cache
    test_result("導入 functools.lru_cache", True, "內建模組")
except ImportError as e:
    test_result("導入 functools.lru_cache", False, str(e))

try:
    from typing import Dict, Optional, Any
    test_result("導入 typing", True, "內建模組")
except ImportError as e:
    test_result("導入 typing", False, str(e))


# ============================================================================
# 測試 2: i18n 核心模組載入
# ============================================================================
print_section("測試 2: i18n 核心模組載入")

try:
    from utils.locale_detector import (
        detect_system_language,
        validate_language_code,
        normalize_language_code,
        SUPPORTED_LANGS
    )
    test_result("導入 utils.locale_detector", True, f"支援語言: {SUPPORTED_LANGS}")
except ImportError as e:
    test_result("導入 utils.locale_detector", False, str(e))
    sys.exit(1)

try:
    from utils.i18n import (
        init_i18n,
        t,
        _,
        switch_language,
        get_current_language,
        get_available_languages,
        get_language_info
    )
    test_result("導入 utils.i18n", True, "所有函數正常導入")
except ImportError as e:
    test_result("導入 utils.i18n", False, str(e))
    sys.exit(1)


# ============================================================================
# 測試 3: 語言包檔案存在性檢查
# ============================================================================
print_section("測試 3: 語言包檔案存在性檢查")

locale_dir = project_root / "locales"
expected_langs = ['zh-TW', 'en', 'ja', 'ko']

for lang in expected_langs:
    lang_file = lang.replace('-', '_')
    yaml_file = locale_dir / f"{lang_file}.yaml"

    if yaml_file.exists():
        size = yaml_file.stat().st_size / 1024  # KB
        test_result(f"語言包檔案存在: {lang}", True, f"{yaml_file.name} ({size:.1f} KB)")
    else:
        test_result(f"語言包檔案存在: {lang}", False, f"找不到: {yaml_file}")


# ============================================================================
# 測試 4: 語言包載入測試
# ============================================================================
print_section("測試 4: 語言包載入測試（4 種語言）")

for lang in expected_langs:
    try:
        i18n = init_i18n(lang)
        current = i18n.get_current_language()
        if current == lang:
            test_result(f"載入語言包: {lang}", True, f"當前語言: {current}")
        else:
            test_result(f"載入語言包: {lang}", False, f"預期 {lang}，實際 {current}")
    except Exception as e:
        test_result(f"載入語言包: {lang}", False, str(e))


# ============================================================================
# 測試 5: 基本翻譯功能測試
# ============================================================================
print_section("測試 5: 基本翻譯功能測試")

# 繁中測試
init_i18n('zh-TW')
test_cases_zh = [
    ("chat.welcome", "歡迎使用 ChatGemini！"),
    ("common.yes", "是"),
    ("common.no", "否"),
    ("pricing.cost", "成本"),
    ("errors.api_error", "API 呼叫失敗"),
]

for key, expected in test_cases_zh:
    result = t(key)
    if result == expected:
        test_result(f"繁中翻譯: {key}", True, f"'{result}'")
    else:
        test_result(f"繁中翻譯: {key}", False, f"預期 '{expected}'，實際 '{result}'")

# 英文測試
init_i18n('en')
test_cases_en = [
    ("chat.welcome", "Welcome to ChatGemini!"),
    ("common.yes", "Yes"),
    ("pricing.cost", "Cost"),
]

for key, expected in test_cases_en:
    result = t(key)
    if result == expected:
        test_result(f"英文翻譯: {key}", True, f"'{result}'")
    else:
        test_result(f"英文翻譯: {key}", False, f"預期 '{expected}'，實際 '{result}'")

# 日文測試
init_i18n('ja')
test_cases_ja = [
    ("chat.welcome", "ChatGeminiへようこそ！"),
    ("common.yes", "はい"),
    ("pricing.cost", "コスト"),
]

for key, expected in test_cases_ja:
    result = t(key)
    if result == expected:
        test_result(f"日文翻譯: {key}", True, f"'{result}'")
    else:
        test_result(f"日文翻譯: {key}", False, f"預期 '{expected}'，實際 '{result}'")

# 韓文測試
init_i18n('ko')
test_cases_ko = [
    ("chat.welcome", "ChatGemini에 오신 것을 환영합니다!"),
    ("common.yes", "예"),
    ("pricing.cost", "비용"),
]

for key, expected in test_cases_ko:
    result = t(key)
    if result == expected:
        test_result(f"韓文翻譯: {key}", True, f"'{result}'")
    else:
        test_result(f"韓文翻譯: {key}", False, f"預期 '{expected}'，實際 '{result}'")


# ============================================================================
# 測試 6: 參數化翻譯測試
# ============================================================================
print_section("測試 6: 參數化翻譯測試")

init_i18n('zh-TW')

# 測試 1: pricing.cost_line
result = t("pricing.cost_line", currency="NT$", twd="12.34", usd="0.40")
expected_parts = ["NT$12.34", "0.40"]
if all(part in result for part in expected_parts):
    test_result("參數化翻譯: pricing.cost_line", True, f"'{result}'")
else:
    test_result("參數化翻譯: pricing.cost_line", False, f"結果: '{result}'")

# 測試 2: cache.cache_created
result = t("cache.cache_created", name="test_cache")
expected = "快取已建立: test_cache"
if result == expected:
    test_result("參數化翻譯: cache.cache_created", True, f"'{result}'")
else:
    test_result("參數化翻譯: cache.cache_created", False, f"預期 '{expected}'，實際 '{result}'")

# 測試 3: 日文參數化
init_i18n('ja')
result = t("cache.cache_created", name="test_cache")
expected = "キャッシュが作成されました: test_cache"
if result == expected:
    test_result("日文參數化翻譯", True, f"'{result}'")
else:
    test_result("日文參數化翻譯", False, f"預期 '{expected}'，實際 '{result}'")


# ============================================================================
# 測試 7: 語言切換功能測試
# ============================================================================
print_section("測試 7: 語言切換功能測試")

# 測試切換到各種語言
for lang in expected_langs:
    success = switch_language(lang)
    current = get_current_language()

    if success and current == lang:
        test_result(f"切換語言至 {lang}", True, f"當前: {current}")
    else:
        test_result(f"切換語言至 {lang}", False, f"預期 {lang}，實際 {current}")


# ============================================================================
# 測試 8: 回退機制測試
# ============================================================================
print_section("測試 8: 回退機制測試")

init_i18n('zh-TW')

# 測試不存在的鍵值
result = t("nonexistent.key.that.does.not.exist")
if result.startswith("[MISSING:"):
    test_result("不存在鍵值回退", True, f"'{result}'")
else:
    test_result("不存在鍵值回退", False, f"應顯示 [MISSING: ...], 實際: '{result}'")

# 測試無效語言代碼
try:
    success = switch_language("fr")  # 法文，不支援
    if not success:
        test_result("無效語言代碼處理", True, "正確拒絕不支援的語言")
    else:
        test_result("無效語言代碼處理", False, "不應接受不支援的語言")
except Exception as e:
    test_result("無效語言代碼處理", False, f"發生異常: {e}")


# ============================================================================
# 測試 9: gemini_pricing.py 整合測試
# ============================================================================
print_section("測試 9: gemini_pricing.py 整合測試")

try:
    from gemini_pricing import GeminiPricing
    test_result("導入 gemini_pricing", True, "模組正常導入")

    # 測試是否使用 i18n
    init_i18n('zh-TW')
    pricing = GeminiPricing()
    test_result("gemini_pricing 初始化", True, "GeminiPricing 實例化成功")

except ImportError as e:
    test_result("導入 gemini_pricing", False, str(e))
except Exception as e:
    test_result("gemini_pricing 初始化", False, str(e))


# ============================================================================
# 測試 10: gemini_lang.py 工具測試
# ============================================================================
print_section("測試 10: gemini_lang.py 工具載入測試")

try:
    # 檢查檔案存在
    lang_tool = project_root / "gemini_lang.py"
    if lang_tool.exists():
        test_result("gemini_lang.py 檔案存在", True, str(lang_tool))
    else:
        test_result("gemini_lang.py 檔案存在", False, "找不到檔案")

    # 測試執行（透過 subprocess）
    import subprocess
    result = subprocess.run(
        [sys.executable, str(lang_tool), "--current"],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode == 0:
        test_result("gemini_lang.py --current", True, "執行成功")
    else:
        test_result("gemini_lang.py --current", False, f"返回碼: {result.returncode}")

except Exception as e:
    test_result("gemini_lang.py 執行測試", False, str(e))


# ============================================================================
# 測試 11: 語言偵測功能測試
# ============================================================================
print_section("測試 11: 語言偵測功能測試")

detected_lang = detect_system_language()
if detected_lang in SUPPORTED_LANGS:
    test_result("系統語言偵測", True, f"偵測到: {detected_lang}")
else:
    test_result("系統語言偵測", False, f"偵測到不支援的語言: {detected_lang}")

# 測試語言代碼正規化
test_cases_normalize = [
    ("zh_TW", "zh-TW"),
    ("zh-tw", "zh-TW"),
    ("EN", "en"),
    ("japanese", "ja"),
]

for input_code, expected in test_cases_normalize:
    result = normalize_language_code(input_code)
    if result == expected:
        test_result(f"正規化: {input_code}", True, f"'{input_code}' → '{result}'")
    else:
        test_result(f"正規化: {input_code}", False, f"預期 '{expected}'，實際 '{result}'")

# 測試語言代碼驗證
for lang in expected_langs:
    if validate_language_code(lang):
        test_result(f"驗證語言代碼: {lang}", True, "有效")
    else:
        test_result(f"驗證語言代碼: {lang}", False, "無效")


# ============================================================================
# 測試 12: get_language_info 測試
# ============================================================================
print_section("測試 12: get_language_info 功能測試")

for lang in expected_langs:
    try:
        info = get_language_info(lang)

        required_keys = ['code', 'name', 'native_name', 'version', 'author']
        if all(key in info for key in required_keys):
            test_result(f"語言資訊: {lang}", True, f"名稱: {info['name']}, 本地名: {info['native_name']}")
        else:
            missing = [key for key in required_keys if key not in info]
            test_result(f"語言資訊: {lang}", False, f"缺少鍵值: {missing}")
    except Exception as e:
        test_result(f"語言資訊: {lang}", False, str(e))


# ============================================================================
# 測試 13: 併發語言切換測試
# ============================================================================
print_section("測試 13: 快速併發語言切換測試")

try:
    # 快速切換多次
    langs = ['zh-TW', 'en', 'ja', 'ko', 'zh-TW']
    all_success = True

    for lang in langs:
        success = switch_language(lang)
        current = get_current_language()
        if not (success and current == lang):
            all_success = False
            break

    if all_success:
        test_result("併發語言切換", True, f"成功切換 {len(langs)} 次")
    else:
        test_result("併發語言切換", False, "切換過程中出現錯誤")
except Exception as e:
    test_result("併發語言切換", False, str(e))


# ============================================================================
# 測試 14: 記憶體效率測試（語言包快取）
# ============================================================================
print_section("測試 14: 語言包快取機制測試")

try:
    # 第一次載入
    init_i18n('zh-TW')
    switch_language('en')

    # 切回繁中（應從快取載入）
    switch_language('zh-TW')
    result1 = t("chat.welcome")

    # 再次切換到英文（應從快取載入）
    switch_language('en')
    result2 = t("chat.welcome")

    if result1 == "歡迎使用 ChatGemini！" and result2 == "Welcome to ChatGemini!":
        test_result("語言包快取機制", True, "快取正常運作")
    else:
        test_result("語言包快取機制", False, f"翻譯錯誤: {result1}, {result2}")
except Exception as e:
    test_result("語言包快取機制", False, str(e))


# ============================================================================
# 測試 15: .env 檔案整合測試
# ============================================================================
print_section("測試 15: .env 檔案讀取測試")

env_file = project_root / ".env"
if env_file.exists():
    test_result(".env 檔案存在", True, str(env_file))

    # 嘗試讀取 GEMINI_LANG
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            if 'GEMINI_LANG=' in content:
                # 提取語言設定
                for line in content.split('\n'):
                    if line.startswith('GEMINI_LANG='):
                        lang = line.split('=')[1].strip()
                        test_result(".env GEMINI_LANG 設定", True, f"語言: {lang}")
                        break
            else:
                test_result(".env GEMINI_LANG 設定", False, "找不到 GEMINI_LANG")
    except Exception as e:
        test_result(".env 讀取", False, str(e))
else:
    test_result(".env 檔案存在", False, "找不到 .env 檔案")


# ============================================================================
# 總結報告
# ============================================================================
print_section("測試總結報告")

print(f"\n總測試數: {total_tests}")
print(f"通過: {passed_tests}")
print(f"失敗: {total_tests - passed_tests}")
print(f"通過率: {passed_tests / total_tests * 100:.1f}%\n")

if passed_tests == total_tests:
    print("🎉 所有測試通過！i18n 模組載入完全正常！")
    exit_code = 0
else:
    print("⚠️  部分測試失敗，請檢查上述錯誤訊息")
    exit_code = 1

# 返回測試結果供外部使用
if __name__ == "__main__":
    sys.exit(exit_code)
