#!/usr/bin/env python3
"""
互動式語言選單工具
提供即時、美觀的語言切換介面
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.i18n import switch_language, get_current_language, get_language_info, get_available_languages, safe_t
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

console = Console()

def show_language_menu(save_to_env: bool = True) -> str:
    """
    顯示互動式語言選單

    Args:
        save_to_env: 是否將選擇保存到 .env 檔案

    Returns:
        選擇的語言代碼
    """

    # 獲取當前語言和可用語言
    current_lang = get_current_language()
    available_langs = get_available_languages()

    # 語言資訊對照
    lang_info_map = {
        'zh-TW': {'flag': '🇹🇼', 'name': '繁體中文', 'native': '繁體中文'},
        'en': {'flag': '🇺🇸', 'name': 'English', 'native': 'English'},
        'ja': {'flag': '🇯🇵', 'name': '日本語', 'native': '日本語'},
        'ko': {'flag': '🇰🇷', 'name': '한국어', 'native': '한국어'}
    }

    # 建立語言選擇表格
    table = Table(show_header=True, header_style="bold #87CEEB", box=box.ROUNDED)
    table.add_column(safe_t('language_menu.column_option', fallback='選項'), style="bold #E8C4F0", width=8, justify="center")
    table.add_column(safe_t('language_menu.column_flag', fallback='旗幟'), width=6, justify="center")
    table.add_column(safe_t('language_menu.column_language', fallback='語言'), style="#87CEEB", width=20)
    table.add_column(safe_t('language_menu.column_native_name', fallback='本地名稱'), style="green", width=20)
    table.add_column(safe_t('language_menu.column_status', fallback='狀態'), width=12, justify="center")

    # 添加語言選項
    for idx, lang_code in enumerate(available_langs, 1):
        info = lang_info_map.get(lang_code, {})
        flag = info.get('flag', '🌐')
        name = info.get('name', lang_code)
        native = info.get('native', lang_code)

        # 標記當前語言
        status = f"✅ {safe_t('language_menu.current', fallback='當前')}" if lang_code == current_lang else ""

        table.add_row(
            f"[{idx}]",
            flag,
            name,
            native,
            status
        )

    # 添加取消選項
    table.add_row(
        "[0]",
        "❌",
        safe_t('language_menu.cancel', fallback='取消'),
        "Cancel",
        ""
    )

    # 顯示面板
    current_info = lang_info_map.get(current_lang, {})
    current_flag = current_info.get('flag', '🌐')
    current_native = current_info.get('native', current_lang)

    panel = Panel(
        table,
        title=safe_t('language_menu.title', fallback='🌍 語言選擇 / Language Selection'),
        subtitle=safe_t('language_menu.current_subtitle', fallback='當前: {flag} {native} ({code})').format(
            flag=current_flag, native=current_native, code=current_lang
        ),
        border_style="#87CEEB",
        box=box.DOUBLE,
        padding=(1, 2)
    )

    console.print("\n")
    console.print(panel)
    console.print()

    # 獲取用戶輸入
    while True:
        try:
            choice = Prompt.ask(
                f"[bold #87CEEB]{safe_t('language_menu.prompt', fallback='請選擇語言 / Select language')}[/bold #87CEEB]",
                default="0"
            )

            # 取消
            if choice == "0":
                console.print(f"[#E8C4F0]{safe_t('language_menu.cancelled', fallback='✖ 已取消 / Cancelled')}[/#E8C4F0]\n")
                return current_lang

            # 驗證輸入
            choice_num = int(choice)
            if 1 <= choice_num <= len(available_langs):
                selected_lang = available_langs[choice_num - 1]

                # 如果選擇相同語言
                if selected_lang == current_lang:
                    console.print(f"[#E8C4F0]{safe_t('language_menu.already_using', fallback='ℹ️  已經是 {native} / Already using {native}').format(native=current_native)}[/#E8C4F0]\n")
                    return current_lang

                # 切換語言
                success = switch_language(selected_lang, save_to_env=save_to_env)

                if success:
                    new_info = lang_info_map.get(selected_lang, {})
                    new_flag = new_info.get('flag', '🌐')
                    new_native = new_info.get('native', selected_lang)

                    console.print()
                    console.print(Panel(
                        f"[bold green]{safe_t('language_menu.switched', fallback='✅ 語言已切換至：{flag} {native}').format(flag=new_flag, native=new_native)}[/bold green]\n"
                        f"[bold green]✅ Language switched to: {new_flag} {new_native}[/bold green]",
                        border_style="green",
                        box=box.ROUNDED,
                        padding=(1, 2)
                    ))
                    console.print()

                    if save_to_env:
                        console.print(f"[dim]{safe_t('language_menu.settings_saved', fallback='💾 設定已保存至 .env / Settings saved to .env')}[/dim]\n")

                    return selected_lang
                else:
                    console.print(f"[red]{safe_t('language_menu.switch_failed', fallback='❌ 切換失敗 / Switch failed')}[/red]\n")
                    return current_lang
            else:
                console.print(f"[red]{safe_t('language_menu.invalid_choice', fallback='❌ 無效的選擇，請輸入 0-{max} / Invalid choice, please enter 0-{max}').format(max=len(available_langs))}[/red]")

        except ValueError:
            console.print(f"[red]{safe_t('language_menu.enter_number', fallback='❌ 請輸入數字 / Please enter a number')}[/red]")
        except KeyboardInterrupt:
            console.print(f"\n[#E8C4F0]{safe_t('language_menu.cancelled', fallback='✖ 已取消 / Cancelled')}[/#E8C4F0]\n")
            return current_lang

def show_quick_switch_hints():
    """顯示快速切換提示"""
    console.print(f"\n[dim]{safe_t('language_menu.tips_title', fallback='💡 提示 / Tips:')}[/dim]")
    tip_text = "• 在對話中輸入 'lang' 或 'language' 可快速打開此選單"
    console.print(f"[dim]  {safe_t('language_menu.tip_quick_switch', fallback=tip_text)}[/dim]")
    console.print(f"[dim]  {safe_t('language_menu.tip_cli_switch', fallback='• 使用 gemini_lang.py --set <code> 可直接切換')}[/dim]")
    console.print("[dim]  • Quick switch: Type 'lang' or 'language' in chat[/dim]")
    console.print()

if __name__ == "__main__":
    # 獨立執行時的測試
    console.print("\n")
    console.print("╔" + "═" * 78 + "╗", style="bold #E8C4F0")
    console.print("║" + " " * 22 + "互動式語言選單測試" + " " * 32 + "║", style="bold #E8C4F0")
    console.print("╚" + "═" * 78 + "╝", style="bold #E8C4F0")

    selected = show_language_menu(save_to_env=True)
    show_quick_switch_hints()

    console.print(f"[green]✅ 最終語言: {selected}[/green]\n")
