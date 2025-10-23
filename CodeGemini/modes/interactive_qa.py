#!/usr/bin/env python3
"""
CodeGemini Interactive Q&A Module
互動式問答模組 - 提供使用者互動功能

此模組負責：
1. 詢問使用者問題（單選/多選）
2. 提供選項說明
3. 支援自訂輸入
4. 確認對話（是/否）
"""

import re
from typing import List, Dict, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()


class InteractiveQA:
    """
    互動式問答

    提供類似 Claude Code AskUserQuestion 的功能：
    - 支援單選與多選
    - 選項標籤與說明
    - 自動提供「Other」選項
    """

    def __init__(self):
        """初始化互動式問答"""
        console.print("[dim]InteractiveQA 初始化完成[/dim]")

    def ask_question(
        self,
        question: str,
        options: List[Dict[str, str]],
        header: str = "",
        multi_select: bool = False
    ) -> List[str]:
        """
        詢問使用者問題

        Args:
            question: 問題內容
            options: 選項列表 [{"label": "...", "description": "..."}, ...]
            header: 問題標題（短標籤，最多 12 字）
            multi_select: 是否支援多選

        Returns:
            List[str]: 選中的選項標籤列表
        """
        console.print(f"\n[bold magenta]{'=' * 70}[/bold magenta]")

        # 顯示標題
        if header:
            console.print(f"[bold]📌 {header}[/bold]")

        # 顯示問題
        console.print(f"[bold yellow]❓ {question}[/bold yellow]")
        console.print(f"[dim]{'-' * 70}[/dim]\n")

        # 顯示選項表格
        table = Table(show_header=False, box=None, padding=(0, 1))
        console_width = console.width or 120
        table.add_column("編號", style="bright_magenta", width=max(6, int(console_width * 0.05)))
        table.add_column("選項", style="white")
        table.add_column("說明", style="dim")

        for i, option in enumerate(options, 1):
            label = option.get("label", "")
            description = option.get("description", "")
            table.add_row(f"[{i}]", label, description)

        # 添加「其他」選項
        table.add_row("[0]", "其他", "自訂輸入")

        console.print(table)

        # 提示
        if multi_select:
            console.print("\n[dim]💡 多選模式：輸入選項編號（用空格或逗號分隔），或輸入 0 自訂[/dim]")
        else:
            console.print("\n[dim]💡 輸入選項編號，或輸入 0 自訂[/dim]")

        console.print(f"[bold magenta]{'=' * 70}[/bold magenta]\n")

        # 取得使用者輸入
        while True:
            try:
                user_input = Prompt.ask("請選擇").strip()

                if not user_input:
                    console.print("[magenta]⚠️  請輸入選項編號[/yellow]")
                    continue

                # 處理自訂輸入
                if user_input == "0":
                    custom = Prompt.ask("請輸入自訂答案").strip()
                    return [custom] if custom else []

                # 解析選擇
                if multi_select:
                    return self._parse_multi_select(user_input, options)
                else:
                    return self._parse_single_select(user_input, options)

            except ValueError as e:
                console.print(f"[dim magenta]✗ {e}[/red]")
                continue
            except KeyboardInterrupt:
                console.print("\n\n[magenta]⚠️  已取消[/yellow]")
                return []

    def _parse_single_select(
        self,
        user_input: str,
        options: List[Dict[str, str]]
    ) -> List[str]:
        """解析單選輸入"""
        try:
            idx = int(user_input)
            if 1 <= idx <= len(options):
                return [options[idx - 1]["label"]]
            else:
                raise ValueError(f"選項 {idx} 不存在，請輸入 1-{len(options)}")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("請輸入有效的數字")
            raise

    def _parse_multi_select(
        self,
        user_input: str,
        options: List[Dict[str, str]]
    ) -> List[str]:
        """解析多選輸入"""
        # 支援空格或逗號分隔
        selections = re.split(r'[,\s]+', user_input)
        indices = []

        for s in selections:
            try:
                idx = int(s)
                if 1 <= idx <= len(options):
                    indices.append(idx - 1)
                else:
                    raise ValueError(f"選項 {idx} 不存在，請輸入 1-{len(options)}")
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"'{s}' 不是有效的數字")
                raise

        if indices:
            return [options[i]["label"] for i in indices]
        else:
            raise ValueError("請至少選擇一個選項")

    def confirm(self, message: str, default: bool = True) -> bool:
        """
        詢問確認（是/否）

        Args:
            message: 確認訊息
            default: 預設值

        Returns:
            bool: 使用者確認結果
        """
        return Confirm.ask(f"[magenta]{message}[/yellow]", default=default)

    def ask_text(self, prompt: str, default: str = "") -> str:
        """
        詢問文字輸入

        Args:
            prompt: 提示訊息
            default: 預設值

        Returns:
            str: 使用者輸入
        """
        return Prompt.ask(f"[magenta]{prompt}[/magenta]", default=default)


# ==================== 命令列介面 ====================

def main():
    """Interactive Q&A 命令列工具"""
    console.print("\n[bold magenta]CodeGemini Interactive Q&A Demo[/bold magenta]\n")

    qa = InteractiveQA()

    # 示例 1：單選
    console.print("[bold]示例 1：選擇測試框架（單選）[/bold]")
    answers = qa.ask_question(
        question="請選擇要使用的測試框架？",
        header="測試框架",
        options=[
            {"label": "pytest", "description": "推薦，功能強大且易用"},
            {"label": "unittest", "description": "Python 內建標準庫"},
            {"label": "nose2", "description": "pytest 的替代方案"}
        ],
        multi_select=False
    )
    console.print(f"\n[bright_magenta]✓ 您選擇了：{answers}[/green]\n")

    # 示例 2：多選
    console.print("[bold]示例 2：選擇要實作的功能（多選）[/bold]")
    answers = qa.ask_question(
        question="請選擇要實作的功能？（可多選）",
        header="功能選擇",
        options=[
            {"label": "Web Search", "description": "網路搜尋功能"},
            {"label": "Web Fetch", "description": "網頁抓取功能"},
            {"label": "Background Shell", "description": "背景進程管理"},
            {"label": "Todo Tracking", "description": "任務追蹤功能"}
        ],
        multi_select=True
    )
    console.print(f"\n[bright_magenta]✓ 您選擇了：{', '.join(answers)}[/green]\n")

    # 示例 3：確認
    if qa.confirm("是否繼續執行？"):
        console.print("[bright_magenta]✓ 繼續執行[/green]")
    else:
        console.print("[magenta]⚠️  已取消[/yellow]")


if __name__ == "__main__":
    main()
