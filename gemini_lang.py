#!/usr/bin/env python3
"""
ChatGemini 語言切換工具

功能：
1. 互動式語言選擇
2. 程式化語言設定
3. 查看當前語言
4. 更新 .env 配置

使用方式：
    python3 gemini_lang.py              # 互動式選擇
    python3 gemini_lang.py --set en     # 設定為英文
    python3 gemini_lang.py --current    # 查看當前語言
    python3 gemini_lang.py --list       # 列出可用語言
"""

import sys
import os
from pathlib import Path

# 確保專案根目錄在 sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.i18n import init_i18n, get_available_languages, get_language_info, switch_language, get_current_language
from utils.locale_detector import SUPPORTED_LANGS, validate_language_code, normalize_language_code


def update_env_file(lang: str):
    """
    更新 .env 檔案中的 GEMINI_LANG 設定

    Args:
        lang: 語言代碼
    """
    env_file = project_root / ".env"

    # 讀取現有內容
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 檢查是否已有 GEMINI_LANG
        found = False
        for i, line in enumerate(lines):
            if line.startswith('GEMINI_LANG='):
                lines[i] = f'GEMINI_LANG={lang}\n'
                found = True
                break

        # 如果沒有，添加到檔案末尾
        if not found:
            lines.append(f'\nGEMINI_LANG={lang}\n')

        # 寫回檔案
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    else:
        # 如果 .env 不存在，創建新檔案
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(f'GEMINI_LANG={lang}\n')


def print_language_menu():
    """顯示語言選擇選單"""
    available = get_available_languages()

    print("\n" + "=" * 60)
    print("語言選擇 / Language Selection / 言語選択 / 언어 선택")
    print("=" * 60)

    for i, lang_code in enumerate(available, 1):
        info = get_language_info(lang_code)
        name = info.get('name', lang_code)
        native_name = info.get('native_name', name)
        print(f"[{i}] {lang_code:8s} - {name} ({native_name})")

    print("=" * 60)


def interactive_language_selection():
    """互動式語言選擇"""
    available = get_available_languages()

    # 顯示選單
    print_language_menu()

    # 提示輸入
    try:
        choice = input("\n請選擇語言 / Please select language [1-{}]: ".format(len(available)))

        # 處理直接輸入語言代碼
        if choice in available:
            selected_lang = choice
        else:
            # 處理數字選擇
            index = int(choice) - 1
            if 0 <= index < len(available):
                selected_lang = available[index]
            else:
                print(f"❌ 無效的選項 / Invalid option: {choice}")
                return False

        # 設定語言
        return set_language(selected_lang, interactive=True)

    except (ValueError, KeyError, IndexError):
        print("❌ 無效的輸入 / Invalid input")
        return False
    except KeyboardInterrupt:
        print("\n\n已取消 / Cancelled")
        return False


def set_language(lang: str, interactive: bool = False):
    """
    設定語言

    Args:
        lang: 語言代碼
        interactive: 是否為互動模式

    Returns:
        是否成功
    """
    # 正規化語言代碼
    lang = normalize_language_code(lang)

    # 驗證語言代碼
    if not validate_language_code(lang):
        print(f"❌ 不支援的語言 / Unsupported language: {lang}")
        print(f"   支援的語言 / Supported: {', '.join(SUPPORTED_LANGS)}")
        return False

    # 檢查語言包是否存在
    available = get_available_languages()
    if lang not in available:
        print(f"⚠️  語言包不存在 / Language pack not found: {lang}")
        print(f"   可用語言 / Available: {', '.join(available)}")
        return False

    # 切換語言
    success = switch_language(lang)
    if not success:
        print(f"❌ 切換語言失敗 / Failed to switch language: {lang}")
        return False

    # 更新 .env
    try:
        update_env_file(lang)
    except Exception as e:
        print(f"⚠️  無法更新 .env: {e}")
        print(f"   語言已切換，但下次啟動可能需要重新設定")

    # 顯示成功訊息
    info = get_language_info(lang)
    name = info.get('name', lang)

    if lang == 'zh-TW':
        print(f"\n✅ 語言已切換至：{name} ({lang})")
        print(f"   設定已保存至 .env")
        if interactive:
            print(f"\n💡 提示：重新啟動程式以套用新語言")
    else:
        print(f"\n✅ Language switched to: {name} ({lang})")
        print(f"   Setting saved to .env")
        if interactive:
            print(f"\n💡 Tip: Restart the program to apply the new language")

    return True


def show_current_language():
    """顯示當前語言"""
    current = get_current_language()
    info = get_language_info(current)

    name = info.get('name', current)
    native_name = info.get('native_name', name)

    print("\n" + "=" * 60)
    print("當前語言 / Current Language")
    print("=" * 60)
    print(f"代碼 / Code:       {current}")
    print(f"名稱 / Name:       {name}")
    print(f"本地名 / Native:   {native_name}")
    print("=" * 60)


def list_available_languages():
    """列出可用語言"""
    available = get_available_languages()
    current = get_current_language()

    print("\n" + "=" * 60)
    print("可用語言 / Available Languages")
    print("=" * 60)

    for lang_code in available:
        info = get_language_info(lang_code)
        name = info.get('name', lang_code)
        native_name = info.get('native_name', name)

        marker = " ← 當前 / Current" if lang_code == current else ""
        print(f"{lang_code:8s} - {name:15s} ({native_name}){marker}")

    print("=" * 60)


def main():
    """主函數"""
    # 初始化 i18n
    init_i18n()

    # 解析命令列參數
    if len(sys.argv) == 1:
        # 無參數：互動式選擇
        interactive_language_selection()

    elif len(sys.argv) >= 2:
        command = sys.argv[1]

        if command == '--current':
            # 顯示當前語言
            show_current_language()

        elif command == '--list':
            # 列出可用語言
            list_available_languages()

        elif command == '--set':
            # 設定語言
            if len(sys.argv) < 3:
                print("❌ 請指定語言代碼 / Please specify language code")
                print("   用法 / Usage: python3 gemini_lang.py --set <lang>")
                print(f"   範例 / Example: python3 gemini_lang.py --set en")
                sys.exit(1)

            lang = sys.argv[2]
            success = set_language(lang)
            sys.exit(0 if success else 1)

        elif command == '--help' or command == '-h':
            # 顯示幫助
            print(__doc__)

        else:
            # 嘗試作為語言代碼
            lang = command
            success = set_language(lang)
            sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
