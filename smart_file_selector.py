#!/usr/bin/env python3
"""
智能檔案選擇系統 (Smart File Selector)
實作兩階段信心度選擇機制，支援多選與即時報價

Created: 2025-10-24 00:00 (UTC+8)
Purpose: C-2 違規修復 - 智能預設值與彈性選擇
"""
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich import box

# 信心度閾值
CONFIDENCE_THRESHOLD = 0.85

# 匯率 (與 gemini_pricing.py 統一)
USD_TO_TWD = 31.0

console = Console()


class SmartFileSelector:
    """智能檔案選擇器 - 兩階段選擇機制"""

    def __init__(self):
        self.console = console

    def estimate_file_processing_cost(
        self,
        file_count: int,
        avg_file_size_mb: float = 10.0,
        model_name: str = 'gemini-2.5-flash'
    ) -> Dict[str, float]:
        """
        估算檔案處理成本

        Args:
            file_count: 檔案數量
            avg_file_size_mb: 平均檔案大小 (MB)
            model_name: 使用的模型

        Returns:
            成本資訊字典
        """
        # 簡化估算: 1MB 視頻 ≈ 2580 tokens (10秒 @ 1 FPS)
        # 假設平均處理需要輸入 tokens + 輸出 tokens
        tokens_per_mb = 2580
        avg_input_tokens = int(avg_file_size_mb * tokens_per_mb)
        avg_output_tokens = 500  # 估算輸出

        # 使用 gemini_pricing 模組的定價
        # 這裡使用簡化計算 (Flash 模型)
        input_cost_per_1k = 0.00015625  # Flash input
        output_cost_per_1k = 0.000625   # Flash output

        single_file_cost = (
            (avg_input_tokens / 1000) * input_cost_per_1k +
            (avg_output_tokens / 1000) * output_cost_per_1k
        )

        total_cost_usd = single_file_cost * file_count
        total_cost_twd = total_cost_usd * USD_TO_TWD

        return {
            'file_count': file_count,
            'single_file_cost_usd': single_file_cost,
            'single_file_cost_twd': single_file_cost * USD_TO_TWD,
            'total_cost_usd': total_cost_usd,
            'total_cost_twd': total_cost_twd
        }

    def _display_pricing_estimate(self, selected_count: int):
        """顯示即時台幣報價"""
        if selected_count == 0:
            return

        cost_info = self.estimate_file_processing_cost(selected_count)

        pricing_text = (
            f"[plum]💰 預估成本[/plum]\n"
            f"  選擇檔案數: [orchid1]{selected_count}[/orchid1] 個\n"
            f"  單檔成本: [dim]NT${cost_info['single_file_cost_twd']:.4f}[/dim]\n"
            f"  總成本: [bold orchid1]NT${cost_info['total_cost_twd']:.2f}[/bold orchid1] "
            f"[dim](${cost_info['total_cost_usd']:.6f} USD)[/dim]"
        )

        self.console.print(Panel(
            pricing_text,
            border_style="plum",
            box=box.ROUNDED
        ))

    def _sort_by_time(self, files: List[Dict]) -> List[Dict]:
        """按時間排序 (最近到最遠)"""
        # 假設 files 中有 'modified_time' 或 'path' 可以獲取時間
        for f in files:
            if 'modified_time' not in f and 'path' in f:
                try:
                    stat = os.stat(f['path'])
                    f['modified_time'] = stat.st_mtime
                except:
                    f['modified_time'] = 0

        return sorted(files, key=lambda x: x.get('modified_time', 0), reverse=True)

    def _display_file_table(
        self,
        files: List[Dict],
        title: str = "檔案列表",
        show_selection_index: bool = True
    ):
        """顯示檔案表格"""
        table = Table(
            title=f"[plum]{title}[/plum]",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold plum"
        )

        console_width = console.width or 120

        if show_selection_index:
            table.add_column("#", style="dim", width=max(3, int(console_width * 0.03)), justify="right")

        table.add_column("檔名", style="orchid1", no_wrap=False)
        table.add_column("信心度", style="medium_orchid", justify="center", width=max(8, int(console_width * 0.08)))
        table.add_column("大小", style="dim", justify="right", width=max(8, int(console_width * 0.08)))
        table.add_column("修改時間", style="dim", width=max(14, int(console_width * 0.12)))

        for i, file_info in enumerate(files, 1):
            name = file_info.get('name', '未知')
            confidence = file_info.get('similarity', 0.0)
            size_mb = file_info.get('size', 0) / (1024 * 1024)
            time_ago = file_info.get('time_ago', '未知')

            confidence_str = f"{int(confidence * 100)}%"
            size_str = f"{size_mb:.1f} MB"

            row_data = [name, confidence_str, size_str, time_ago]
            if show_selection_index:
                row_data.insert(0, str(i))

            table.add_row(*row_data)

        self.console.print(table)

    def _multi_select_files(
        self,
        files: List[Dict],
        prompt_text: str = "輸入要選擇的檔案編號"
    ) -> List[Dict]:
        """
        多選檔案介面

        Args:
            files: 檔案列表
            prompt_text: 提示文字

        Returns:
            選中的檔案列表
        """
        self.console.print(
            f"\n[plum]{prompt_text}[/plum]\n"
            f"[dim]· 可輸入多個編號 (用空格或逗號分隔)，例如: 1 3 5 或 1,3,5[/dim]\n"
            f"[dim]· 輸入 'all' 選擇全部，輸入 'cancel' 取消[/dim]\n"
        )

        while True:
            try:
                choice_str = Prompt.ask(
                    "[plum]選擇[/plum]",
                    default="cancel"
                )

                choice_str = choice_str.strip().lower()

                if choice_str == 'cancel':
                    return []

                if choice_str == 'all':
                    self._display_pricing_estimate(len(files))
                    return files

                # 解析輸入的編號
                choice_str = choice_str.replace(',', ' ')
                indices = [int(x.strip()) for x in choice_str.split() if x.strip().isdigit()]

                # 驗證編號有效性
                valid_indices = [i for i in indices if 1 <= i <= len(files)]

                if not valid_indices:
                    self.console.print("[#E8C4F0]⚠ 未輸入有效編號，請重新輸入[/#E8C4F0]")
                    continue

                selected = [files[i - 1] for i in valid_indices]

                # 顯示選中的檔案
                self.console.print(f"\n[plum]✓ 已選擇 {len(selected)} 個檔案:[/plum]")
                for idx in valid_indices:
                    self.console.print(f"  [dim]{idx}.[/dim] [orchid1]{files[idx-1]['name']}[/orchid1]")

                # 顯示報價
                self._display_pricing_estimate(len(selected))

                # 確認
                if Confirm.ask("[plum]確認選擇?[/plum]", default=True):
                    return selected
                else:
                    self.console.print("[dim]請重新選擇...[/dim]\n")

            except (ValueError, IndexError):
                self.console.print("[#E8C4F0]⚠ 輸入格式錯誤，請輸入有效編號[/#E8C4F0]")
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[#E8C4F0]已取消[/#E8C4F0]")
                return []

    def select_high_confidence(
        self,
        similar_files: List[Dict],
        top_n: int = 5
    ) -> Optional[List[Dict]]:
        """
        高信心度選擇路徑 (>=0.85)

        流程:
        1. 使用者選擇: 預設 / 我要自行選擇檔案
        2. 若選擇手動: 顯示 top_n 個 + "顯示全部"
        3. 顯示全部: 時間排序 + 多選 + 報價

        Args:
            similar_files: 相似檔案列表 (已按信心度排序)
            top_n: 預設顯示的檔案數

        Returns:
            選中的檔案列表 (可能包含多個)
        """
        # 最高信心度的檔案
        best_match = similar_files[0]
        confidence = best_match.get('similarity', 0.0)

        self.console.print(
            Panel(
                f"[plum]🎯 最佳匹配[/plum]\n"
                f"  檔名: [orchid1]{best_match['name']}[/orchid1]\n"
                f"  信心度: [bold medium_orchid]{int(confidence * 100)}%[/bold medium_orchid]\n"
                f"  路徑: [dim]{best_match['path']}[/dim]",
                border_style="plum",
                box=box.ROUNDED
            )
        )

        # 選項1: 預設使用最佳匹配
        use_default = Confirm.ask(
            "\n[plum]使用預設最佳匹配?[/plum] (否則手動選擇)",
            default=True
        )

        if use_default:
            self._display_pricing_estimate(1)
            return [best_match]

        # 選項2: 手動選擇
        self.console.print("\n[plum]📋 手動選擇模式[/plum]\n")

        # 顯示 top_n 個檔案
        display_files = similar_files[:top_n]
        self._display_file_table(display_files, title=f"信心度排序 (前 {top_n} 個)")

        # 提供選項
        self.console.print(
            f"\n[plum]選項:[/plum]\n"
            f"  [dim]1-{len(display_files)}:[/dim] 選擇對應檔案 (可多選)\n"
            f"  [dim]0:[/dim] 顯示全部檔案 (依時間排序)\n"
            f"  [dim]cancel:[/dim] 取消\n"
        )

        choice = Prompt.ask(
            "[plum]請選擇[/plum]",
            default="cancel"
        ).strip().lower()

        if choice == '0' or choice == 'all':
            # 顯示全部 (時間排序)
            all_files_sorted = self._sort_by_time(similar_files.copy())
            self.console.print("\n[plum]📅 全部檔案 (依時間排序)[/plum]\n")
            self._display_file_table(all_files_sorted, title="時間排序 (最近到最遠)")
            return self._multi_select_files(all_files_sorted)

        elif choice == 'cancel':
            return None

        else:
            # 直接從 top_n 中選擇 (支援多選)
            return self._multi_select_files(display_files, "從上方列表選擇檔案")

    def select_low_confidence(
        self,
        similar_files: List[Dict]
    ) -> Optional[List[Dict]]:
        """
        低信心度選擇路徑 (<0.85)

        流程:
        1. 同時顯示: 信心度最高 3 個 + 時間最近 3 個 (不重複) = 6 個
        2. 第 7 個選項: "顯示全部" (時間排序)
        3. 多選 + 報價

        Args:
            similar_files: 相似檔案列表 (已按信心度排序)

        Returns:
            選中的檔案列表
        """
        self.console.print(
            Panel(
                "[#E8C4F0]⚠ 信心度較低 (<85%)[/#E8C4F0]\n"
                "[dim]自動顯示多個候選檔案供您選擇[/dim]",
                border_style="#E8C4F0",
                box=box.ROUNDED
            )
        )

        # 1. 信心度最高 3 個
        top_by_confidence = similar_files[:3]

        # 2. 時間最近 3 個 (排除已在 top 3 的)
        time_sorted = self._sort_by_time(similar_files.copy())
        top_by_time = []
        for f in time_sorted:
            if f not in top_by_confidence and len(top_by_time) < 3:
                top_by_time.append(f)

        # 3. 合併 (6 個)
        combined_files = top_by_confidence + top_by_time

        # 顯示表格 (分段顯示)
        self.console.print("\n[plum]📊 信心度排序 (前 3 個)[/plum]")
        self._display_file_table(top_by_confidence, title="", show_selection_index=True)

        if top_by_time:
            self.console.print("\n[plum]📅 時間排序 (最近 3 個)[/plum]")
            # 重新編號從 4 開始
            for i, f in enumerate(top_by_time, 4):
                size_mb = f.get('size', 0) / (1024 * 1024)
                confidence = int(f.get('similarity', 0.0) * 100)
                self.console.print(
                    f"  [dim]{i}.[/dim] [orchid1]{f['name']}[/orchid1] "
                    f"[dim]({confidence}% · {size_mb:.1f} MB · {f.get('time_ago', '未知')})[/dim]"
                )

        # 選項
        self.console.print(
            f"\n[plum]選項:[/plum]\n"
            f"  [dim]1-{len(combined_files)}:[/dim] 選擇對應檔案 (可多選)\n"
            f"  [dim]7 或 all:[/dim] 顯示全部檔案 (依時間排序)\n"
            f"  [dim]cancel:[/dim] 取消\n"
        )

        choice = Prompt.ask(
            "[plum]請選擇[/plum]",
            default="cancel"
        ).strip().lower()

        if choice == '7' or choice == 'all':
            # 顯示全部 (時間排序)
            all_files_sorted = self._sort_by_time(similar_files.copy())
            self.console.print("\n[plum]📅 全部檔案 (依時間排序)[/plum]\n")
            self._display_file_table(all_files_sorted, title="時間排序 (最近到最遠)")
            return self._multi_select_files(all_files_sorted)

        elif choice == 'cancel':
            return None

        else:
            # 從 combined_files 中選擇 (支援多選)
            return self._multi_select_files(combined_files, "從上方列表選擇檔案")

    def smart_select(
        self,
        similar_files: List[Dict],
        confidence_threshold: float = CONFIDENCE_THRESHOLD
    ) -> Optional[List[Dict]]:
        """
        智能選擇主入口

        根據最高信心度自動選擇處理路徑:
        - >= 0.85: 高信心度路徑 (預設 / 手動選擇)
        - < 0.85: 低信心度路徑 (自動顯示 6 個候選)

        Args:
            similar_files: 相似檔案列表 (已按信心度排序)
            confidence_threshold: 信心度閾值 (預設 0.85)

        Returns:
            選中的檔案列表，若取消則返回 None
        """
        if not similar_files:
            self.console.print("[#E8C4F0]⚠ 未找到相似檔案[/#E8C4F0]")
            return None

        # 確保按信心度排序
        similar_files.sort(key=lambda x: x.get('similarity', 0), reverse=True)

        # 最高信心度
        best_confidence = similar_files[0].get('similarity', 0.0)

        self.console.print(
            f"\n[plum]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/plum]\n"
            f"[plum]🔍 智能檔案選擇器[/plum]\n"
            f"[dim]找到 {len(similar_files)} 個相似檔案，最高信心度: {int(best_confidence * 100)}%[/dim]\n"
            f"[plum]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/plum]\n"
        )

        # 路徑選擇
        if best_confidence >= confidence_threshold:
            # 高信心度路徑
            return self.select_high_confidence(similar_files)
        else:
            # 低信心度路徑
            return self.select_low_confidence(similar_files)


# ==================== 便捷函數 ====================

def smart_file_selection(
    similar_files: List[Dict],
    confidence_threshold: float = CONFIDENCE_THRESHOLD
) -> Optional[List[str]]:
    """
    便捷函數: 智能檔案選擇

    Args:
        similar_files: 相似檔案列表
        confidence_threshold: 信心度閾值

    Returns:
        選中的檔案路徑列表 (字串)
    """
    selector = SmartFileSelector()
    selected_files = selector.smart_select(similar_files, confidence_threshold)

    if selected_files:
        return [f['path'] for f in selected_files]
    else:
        return None


if __name__ == "__main__":
    # 測試範例
    test_files = [
        {
            'name': 'video_2024_10_23_high_quality.mp4',
            'path': '/path/to/video_2024_10_23_high_quality.mp4',
            'size': 15 * 1024 * 1024,  # 15 MB
            'similarity': 0.92,
            'time_ago': '2 小時前',
            'modified_time': 1729700000
        },
        {
            'name': 'video_2024_10_22.mp4',
            'path': '/path/to/video_2024_10_22.mp4',
            'size': 12 * 1024 * 1024,
            'similarity': 0.88,
            'time_ago': '1 天前',
            'modified_time': 1729600000
        },
        {
            'name': 'video_final.mp4',
            'path': '/path/to/video_final.mp4',
            'size': 20 * 1024 * 1024,
            'similarity': 0.75,
            'time_ago': '3 天前',
            'modified_time': 1729400000
        },
        {
            'name': 'video_backup.mp4',
            'path': '/path/to/video_backup.mp4',
            'size': 10 * 1024 * 1024,
            'similarity': 0.65,
            'time_ago': '1 週前',
            'modified_time': 1729000000
        }
    ]

    console.print("\n[bold plum]測試 1: 高信心度情境 (92%)[/bold plum]")
    selector = SmartFileSelector()
    result = selector.smart_select(test_files)
    console.print(f"\n[green]選擇結果:[/green] {[f['name'] for f in result] if result else '已取消'}")

    # 測試低信心度
    test_files_low = [f.copy() for f in test_files]
    for f in test_files_low:
        f['similarity'] *= 0.8  # 降低信心度到 <0.85

    console.print("\n[bold plum]測試 2: 低信心度情境 (<85%)[/bold plum]")
    result2 = selector.smart_select(test_files_low)
    console.print(f"\n[green]選擇結果:[/green] {[f['name'] for f in result2] if result2 else '已取消'}")
