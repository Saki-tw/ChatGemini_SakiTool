#!/usr/bin/env python3
"""
互動式選單工具
使用 prompt_toolkit 實現支援上下鍵導航的選單
"""
from typing import List, Tuple, Optional
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.formatted_text import HTML
from rich.console import Console

console = Console()


def show_menu(title: str, options: List[Tuple[str, str, str]]) -> Optional[str]:
    """
    顯示互動式選單（使用 radiolist_dialog）

    Args:
        title: 選單標題
        options: 選項列表，格式為 [(選項ID, 顯示文字, 描述), ...]
                標題項目：ID 以 'header_' 開頭（不可選擇，僅顯示於文檔）
                分隔符：ID 為 'separator'（不可選擇）

    Returns:
        選中的選項ID，如果取消則返回 None

    Example:
        >>> options = [
        ...     ('header_ai', '>>> AI 創作生成', ''),
        ...     ('1', '[1] Flow 影片生成', '1080p 長影片，自然語言'),
        ...     ('2', '[2] Veo 影片生成', '8秒快速生成'),
        ...     ('separator', '', ''),
        ...     ('99', '[99] 返回主選單', '')
        ... ]
        >>> choice = show_menu('🎬 多媒體創作中心', options)
        >>> print(f"使用者選擇：{choice}")
    """
    # 過濾掉標題和分隔符（不可選擇的項目）
    selectable_options = [
        (opt_id, f"{display_text}  {desc}" if desc else display_text)
        for opt_id, display_text, desc in options
        if not opt_id.startswith('header_') and opt_id != 'separator'
    ]

    if not selectable_options:
        console.print("[yellow]⚠ 選單沒有可選擇的項目[/yellow]")
        return None

    try:
        # 使用 radiolist_dialog 顯示選單
        result = radiolist_dialog(
            title=HTML(f'<ansibrightmagenta><b> {title} </b></ansibrightmagenta>'),
            text=HTML('<b>使用 ↑↓ 選擇，Enter 確認，ESC 取消</b>'),
            values=selectable_options,
            style={
                'dialog': 'bg:#1a1a1a',
                'dialog.body': 'bg:#1a1a1a fg:#E8C4F0',
                'dialog shadow': 'bg:#000000',
                'dialog frame.label': 'bg:#E8C4F0 fg:#000000',
                'radio-list': 'bg:#1a1a1a',
                'radio-checked': 'bg:#B565D8 fg:#000000 bold',
                'radio': 'fg:#E8C4F0',
                'button': 'bg:#E8C4F0 fg:#000000',
                'button.focused': 'bg:#B565D8 fg:#000000'
            }
        ).run()

        return result
    except KeyboardInterrupt:
        # 處理 Ctrl+C
        return None
    except Exception as e:
        console.print(f"[red]✗ 選單錯誤：{e}[/red]")
        return None


# ============================================
# 測試代碼
# ============================================
if __name__ == '__main__':
    # 測試選單
    test_options = [
        ('header_ai', '\n>>> AI 創作生成', ''),
        ('1', '[1] Flow 影片生成', '1080p 長影片，自然語言'),
        ('2', '[2] Veo 影片生成', '8秒快速生成'),
        ('3', '[3] 圖像創作', '生成/編輯/放大 - Imagen 3'),
        ('header_tools', '\n>>> 處理工具', ''),
        ('4', '[4] 影片工具箱', '剪輯/特效/字幕/合併'),
        ('5', '[5] 音訊工具箱', '提取/混音/BGM/特效'),
        ('separator', '', ''),
        ('99', '[99] 返回主選單', '')
    ]

    console.print("\n[bold #B565D8]測試互動式選單[/bold #B565D8]\n")
    result = show_menu('🎬 多媒體創作中心', test_options)

    if result:
        console.print(f"\n[green]✓ 使用者選擇：{result}[/green]")
    else:
        console.print("\n[yellow]✗ 使用者取消選擇[/yellow]")
