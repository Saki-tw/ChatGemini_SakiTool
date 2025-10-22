#!/usr/bin/env python3
"""
智能錯誤診斷系統

當錯誤發生時：
1. 自動診斷問題根源
2. 生成一鍵解決方案（如果可行）
3. 提供可執行的修復指令
4. 如果無法自動修復，則顯示清晰的錯誤訊息
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class Solution:
    """解決方案數據結構"""
    title: str  # 解決方案標題
    description: str  # 詳細說明
    command: Optional[str] = None  # 可執行指令（一鍵修復）
    manual_steps: Optional[List[str]] = None  # 手動步驟
    priority: int = 1  # 優先級（1=最高）
    auto_fixable: bool = False  # 是否可自動修復


class ErrorDiagnostics:
    """智能錯誤診斷系統"""

    def __init__(self):
        self.console = Console()

    def diagnose_and_suggest(
        self,
        error: Exception,
        operation: str,
        context: dict
    ) -> Tuple[str, List[Solution]]:
        """
        診斷錯誤並提供解決方案

        Args:
            error: 發生的異常
            operation: 操作名稱（如「音訊提取」）
            context: 上下文資訊 {
                'input_files': [...],
                'output_file': '...',
                'stderr': '...',
                ...
            }

        Returns:
            (error_message, solutions): 錯誤訊息和解決方案列表
        """
        error_str = str(error)
        solutions = []

        # 1. 磁碟空間不足
        if "Disk quota exceeded" in error_str or "No space left" in error_str:
            solutions = self._solve_disk_space_issue(context)

        # 2. 權限不足
        elif "Permission denied" in error_str:
            solutions = self._solve_permission_issue(context)

        # 3. 檔案損壞或格式錯誤
        elif any(kw in error_str for kw in ["Invalid data", "moov atom not found", "corrupt"]):
            solutions = self._solve_corrupted_file(context)

        # 4. 缺少音訊串流
        elif "does not contain any stream" in error_str:
            solutions = self._solve_no_audio_stream(context)

        # 5. 編碼格式不支援
        elif "codec not currently supported" in error_str:
            solutions = self._solve_unsupported_codec(context)

        # 6. 檔案不存在
        elif "No such file" in error_str or isinstance(error, FileNotFoundError):
            solutions = self._solve_file_not_found(context)

        # 7. 字型問題（字幕燒錄）
        elif "Fontconfig" in error_str or "font" in error_str.lower():
            solutions = self._solve_font_issue(context)

        # 8. 記憶體不足
        elif "out of memory" in error_str.lower() or "cannot allocate" in error_str.lower():
            solutions = self._solve_memory_issue(context)

        # 生成錯誤訊息
        error_message = self._format_error_message(error, operation, context)

        return error_message, solutions

    def _solve_disk_space_issue(self, context: dict) -> List[Solution]:
        """解決磁碟空間不足問題"""
        output_dir = os.path.dirname(context.get('output_file', ''))
        if not output_dir:
            output_dir = os.getcwd()

        # 取得磁碟使用情況
        try:
            total, used, free = shutil.disk_usage(output_dir)
            free_gb = free / (1024**3)
        except:
            free_gb = 0

        solutions = [
            Solution(
                title="清理臨時檔案",
                description=f"當前剩餘空間：{free_gb:.2f} GB。清理系統臨時檔案可釋放空間。",
                command=f"find /tmp -type f -name '*.tmp' -o -name '*.temp' | xargs rm -f",
                priority=1,
                auto_fixable=False  # 需要用戶確認
            ),
            Solution(
                title="清理專案臨時檔案",
                description="清理本專案的臨時音訊/影片檔案",
                command=f"find {output_dir} -type f -name '*_temp.*' -o -name '*_tmp.*' | xargs rm -f",
                priority=2,
                auto_fixable=False
            ),
            Solution(
                title="更改輸出目錄",
                description="將輸出目錄改為空間較大的磁碟",
                manual_steps=[
                    "1. 使用 df -h 查看可用磁碟空間",
                    "2. 修改輸出路徑參數至空間充足的目錄",
                    "3. 重新執行操作"
                ],
                priority=3
            )
        ]

        return solutions

    def _solve_permission_issue(self, context: dict) -> List[Solution]:
        """解決權限不足問題"""
        input_files = context.get('input_files', [])
        output_file = context.get('output_file', '')

        # 檢查哪個檔案有權限問題
        problem_files = []
        for f in input_files + [output_file]:
            if f and os.path.exists(f):
                if not os.access(f, os.R_OK):
                    problem_files.append((f, '讀取'))
                elif f == output_file and not os.access(os.path.dirname(f) or '.', os.W_OK):
                    problem_files.append((f, '寫入'))

        solutions = []

        if problem_files:
            for file_path, permission_type in problem_files:
                solutions.append(Solution(
                    title=f"修復檔案權限：{os.path.basename(file_path)}",
                    description=f"檔案缺少{permission_type}權限",
                    command=f"chmod 644 '{file_path}'",
                    priority=1,
                    auto_fixable=False
                ))

        # 通用解決方案
        if output_file:
            output_dir = os.path.dirname(output_file) or '.'
            solutions.append(Solution(
                title="修復輸出目錄權限",
                description="確保對輸出目錄有寫入權限",
                command=f"chmod 755 '{output_dir}'",
                priority=2,
                auto_fixable=False
            ))

        return solutions

    def _solve_corrupted_file(self, context: dict) -> List[Solution]:
        """解決檔案損壞問題"""
        input_files = context.get('input_files', [])

        solutions = [
            Solution(
                title="驗證檔案完整性",
                description="使用 ffprobe 檢查檔案是否真的損壞",
                command=f"ffprobe -v error '{input_files[0]}'" if input_files else None,
                priority=1,
                auto_fixable=False
            ),
            Solution(
                title="嘗試修復檔案",
                description="使用 ffmpeg 重新封裝檔案（可能修復輕微損壞）",
                command=f"ffmpeg -i '{input_files[0]}' -c copy '{input_files[0]}.repaired.mp4'" if input_files else None,
                priority=2,
                auto_fixable=False
            ),
            Solution(
                title="重新下載或獲取檔案",
                description="如果檔案確實損壞，建議重新獲取原始檔案",
                manual_steps=[
                    "1. 確認檔案來源",
                    "2. 重新下載或複製檔案",
                    "3. 驗證檔案完整性（檢查檔案大小、MD5 等）",
                    "4. 重新執行操作"
                ],
                priority=3
            )
        ]

        return solutions

    def _solve_no_audio_stream(self, context: dict) -> List[Solution]:
        """解決缺少音訊串流問題"""
        input_files = context.get('input_files', [])

        solutions = [
            Solution(
                title="檢查檔案串流資訊",
                description="確認檔案是否包含音訊軌",
                command=f"ffprobe -v error -show_streams '{input_files[0]}'" if input_files else None,
                priority=1,
                auto_fixable=False
            ),
            Solution(
                title="使用其他檔案",
                description="如果檔案確實沒有音訊，請使用包含音訊的檔案",
                manual_steps=[
                    "1. 確認影片檔案是否包含音軌",
                    "2. 如果是無聲影片，請先添加音軌",
                    "3. 或使用其他包含音訊的影片"
                ],
                priority=2
            )
        ]

        return solutions

    def _solve_unsupported_codec(self, context: dict) -> List[Solution]:
        """解決編碼格式不支援問題"""
        input_files = context.get('input_files', [])

        solutions = [
            Solution(
                title="轉換為常見格式",
                description="將檔案轉換為 H.264/AAC 格式（最廣泛支援）",
                command=f"ffmpeg -i '{input_files[0]}' -c:v libx264 -c:a aac '{input_files[0]}.converted.mp4'" if input_files else None,
                priority=1,
                auto_fixable=False
            ),
            Solution(
                title="檢查 ffmpeg 編碼器",
                description="查看 ffmpeg 支援的編碼器",
                command="ffmpeg -codecs",
                priority=2,
                auto_fixable=False
            )
        ]

        return solutions

    def _solve_file_not_found(self, context: dict) -> List[Solution]:
        """解決檔案不存在問題"""
        input_files = context.get('input_files', [])

        solutions = []

        for file_path in input_files:
            if not file_path:
                continue

            # 嘗試找相似檔名
            parent_dir = os.path.dirname(file_path) or '.'
            filename = os.path.basename(file_path)

            similar_files = []
            if os.path.isdir(parent_dir):
                for f in os.listdir(parent_dir):
                    if f.lower().startswith(filename[:5].lower()):
                        similar_files.append(f)

            if similar_files:
                solutions.append(Solution(
                    title="可能的相似檔案",
                    description=f"在 {parent_dir} 找到相似檔案：{', '.join(similar_files[:3])}",
                    manual_steps=[
                        "1. 確認檔案路徑是否正確",
                        "2. 檢查上述相似檔案是否為目標檔案",
                        "3. 更正檔案路徑後重試"
                    ],
                    priority=1
                ))

            solutions.append(Solution(
                title="檢查檔案路徑",
                description="確認檔案是否存在於指定位置",
                command=f"ls -lh '{parent_dir}'",
                priority=2,
                auto_fixable=False
            ))

        return solutions

    def _solve_font_issue(self, context: dict) -> List[Solution]:
        """解決字型問題"""
        solutions = [
            Solution(
                title="安裝中文字型",
                description="字幕燒錄需要中文字型支援",
                command="brew install --cask font-noto-sans-cjk",  # macOS
                priority=1,
                auto_fixable=False
            ),
            Solution(
                title="指定字型檔案",
                description="在字幕樣式中明確指定字型檔案路徑",
                manual_steps=[
                    "1. 找到系統中的字型檔案（.ttf 或 .otf）",
                    "2. 在字幕參數中指定字型路徑",
                    "3. 重新執行燒錄"
                ],
                priority=2
            )
        ]

        return solutions

    def _solve_memory_issue(self, context: dict) -> List[Solution]:
        """解決記憶體不足問題"""
        solutions = [
            Solution(
                title="降低處理品質",
                description="使用較低的解析度或位元率",
                manual_steps=[
                    "1. 調整輸出解析度（如 1080p → 720p）",
                    "2. 降低位元率參數",
                    "3. 重新執行操作"
                ],
                priority=1
            ),
            Solution(
                title="分段處理",
                description="將大檔案分段處理後再合併",
                manual_steps=[
                    "1. 使用 ffmpeg 將影片分段",
                    "2. 逐段處理",
                    "3. 合併處理後的片段"
                ],
                priority=2
            ),
            Solution(
                title="釋放系統記憶體",
                description="關閉其他應用程式以釋放記憶體",
                manual_steps=[
                    "1. 關閉不必要的應用程式",
                    "2. 清理系統快取",
                    "3. 重新執行操作"
                ],
                priority=3
            )
        ]

        return solutions

    def _format_error_message(
        self,
        error: Exception,
        operation: str,
        context: dict
    ) -> str:
        """格式化錯誤訊息"""
        error_str = str(error)

        # 簡化常見錯誤訊息
        if "Invalid data found" in error_str or "moov atom not found" in error_str:
            return f"{operation}失敗：影片檔案格式錯誤或損壞"
        elif "Permission denied" in error_str:
            return f"{operation}失敗：檔案權限不足"
        elif "Disk quota exceeded" in error_str or "No space left" in error_str:
            return f"{operation}失敗：磁碟空間不足"
        elif "does not contain any stream" in error_str:
            return f"{operation}失敗：檔案不包含有效音訊串流"
        elif "codec not currently supported" in error_str:
            return f"{operation}失敗：不支援的編碼格式"
        elif isinstance(error, FileNotFoundError):
            return f"{operation}失敗：找不到指定檔案"
        else:
            return f"{operation}失敗：{error_str}"

    def display_solutions(
        self,
        error_message: str,
        solutions: List[Solution]
    ) -> None:
        """
        顯示錯誤訊息和解決方案

        Args:
            error_message: 錯誤訊息
            solutions: 解決方案列表
        """
        # 顯示錯誤訊息
        console.print(f"\n[red]✗ {error_message}[/red]\n")

        if not solutions:
            console.print("[dim]無可用的自動解決方案[/dim]")
            return

        # 按優先級排序
        solutions.sort(key=lambda s: s.priority)

        # 顯示解決方案
        console.print("[cyan]💡 建議的解決方案：[/cyan]\n")

        for i, solution in enumerate(solutions, 1):
            # 解決方案標題
            if solution.auto_fixable:
                icon = "🔧"
                auto_tag = " [green](可自動修復)[/green]"
            elif solution.command:
                icon = "⚡"
                auto_tag = " [yellow](一鍵執行)[/yellow]"
            else:
                icon = "📝"
                auto_tag = ""

            console.print(f"{icon} [bold]{i}. {solution.title}{auto_tag}[/bold]")
            console.print(f"   [dim]{solution.description}[/dim]")

            # 顯示指令
            if solution.command:
                console.print(f"   [green]執行指令：[/green]")
                console.print(Panel(
                    solution.command,
                    border_style="green",
                    padding=(0, 1)
                ))

            # 顯示手動步驟
            if solution.manual_steps:
                console.print(f"   [yellow]手動步驟：[/yellow]")
                for step in solution.manual_steps:
                    console.print(f"   {step}")

            console.print()  # 空行


def diagnose_error(
    error: Exception,
    operation: str,
    context: dict
) -> Tuple[str, List[Solution]]:
    """
    便捷函數：診斷錯誤並返回訊息和解決方案

    Args:
        error: 發生的異常
        operation: 操作名稱
        context: 上下文資訊

    Returns:
        (error_message, solutions)
    """
    diagnostics = ErrorDiagnostics()
    return diagnostics.diagnose_and_suggest(error, operation, context)


def display_error_with_solutions(
    error: Exception,
    operation: str,
    context: dict
) -> None:
    """
    便捷函數：診斷錯誤並顯示解決方案

    Args:
        error: 發生的異常
        operation: 操作名稱
        context: 上下文資訊
    """
    diagnostics = ErrorDiagnostics()
    error_message, solutions = diagnostics.diagnose_and_suggest(error, operation, context)
    diagnostics.display_solutions(error_message, solutions)


if __name__ == "__main__":
    # 測試範例
    console.print("[bold cyan]智能錯誤診斷系統 - 測試範例[/bold cyan]\n")

    # 模擬磁碟空間不足錯誤
    error = RuntimeError("ffmpeg: Disk quota exceeded")
    context = {
        'input_files': ['/path/to/video.mp4'],
        'output_file': '/path/to/output.mp4',
        'stderr': 'Disk quota exceeded'
    }

    display_error_with_solutions(error, "音訊提取", context)
