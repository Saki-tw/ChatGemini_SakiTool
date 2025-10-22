#!/usr/bin/env python3
"""
Gemini 大檔案上傳管理器 - 完全使用新 SDK
支援無限大小的檔案上傳（使用 resumable upload）
"""
import os
import sys
import time
import mimetypes
from typing import Optional, List, Dict

# 新 SDK
from google.genai import types

# 共用工具模組
from utils.api_client import get_gemini_client
from utils.pricing_loader import (
    get_pricing_calculator,
    PRICING_ENABLED,
    USD_TO_TWD
)

# API 重試機制
try:
    from api_retry_wrapper import with_retry
    API_RETRY_ENABLED = True
except ImportError:
    API_RETRY_ENABLED = False

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn
from rich.table import Table

console = Console()

# 初始化 API 客戶端
client = get_gemini_client()

# 支援的檔案類型（擴展列表）
SUPPORTED_TYPES = {
    # 影片
    'video': ['.mp4', '.mpeg', '.mov', '.avi', '.flv', '.mpg', '.webm', '.wmv', '.3gpp', '.mkv'],
    # 音訊
    'audio': ['.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a'],
    # 圖片
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
    # 文件
    'document': ['.pdf', '.txt', '.doc', '.docx', '.csv', '.json', '.xml'],
}


class FileManager:
    """大檔案上傳管理器（新 SDK 版本）"""

    def __init__(self):
        self.uploaded_files: Dict[str, types.File] = {}

    def get_file_type(self, file_path: str) -> str:
        """獲取檔案類型"""
        ext = os.path.splitext(file_path)[1].lower()
        for file_type, extensions in SUPPORTED_TYPES.items():
            if ext in extensions:
                return file_type
        return 'unknown'

    def upload_file(
        self,
        file_path: str,
        display_name: Optional[str] = None,
        force_reupload: bool = False
    ) -> types.File:
        """
        上傳檔案（新 SDK 自動處理大檔案）

        Args:
            file_path: 檔案路徑
            display_name: 顯示名稱
            force_reupload: 強制重新上傳（即使已存在）

        Returns:
            上傳的檔案物件
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"找不到檔案: {file_path}")

        # 檢查檔案大小
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)

        # 設定顯示名稱
        if not display_name:
            display_name = os.path.basename(file_path)

        # 獲取檔案類型
        file_type = self.get_file_type(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)

        console.print(f"\n[cyan]📁 檔案資訊：[/cyan]")
        console.print(f"   名稱：{os.path.basename(file_path)}")
        console.print(f"   大小：{file_size_mb:.2f} MB ({file_size:,} bytes)")
        console.print(f"   類型：{file_type}")
        console.print(f"   MIME：{mime_type or '未知'}")

        # 檢查是否已上傳（除非強制重新上傳）
        if not force_reupload:
            console.print(f"\n[cyan]🔍 檢查是否已上傳...[/cyan]")
            existing_file = self._find_existing_file(display_name)
            if existing_file:
                console.print(f"[green]✓ 檔案已存在，使用現有檔案[/green]")
                console.print(f"   名稱: {existing_file.name}")
                console.print(f"   狀態: {existing_file.state.name}")
                self.uploaded_files[display_name] = existing_file

                # 如果還在處理中，等待完成
                if existing_file.state.name == "PROCESSING":
                    return self._wait_for_processing(existing_file)

                return existing_file

        # 上傳檔案（新 SDK）
        console.print(f"\n[cyan]📤 開始上傳...[/cyan]")
        if file_size_mb > 20:
            console.print(f"   [yellow]大檔案模式：新 SDK 自動處理分塊上傳[/yellow]")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"上傳中",
                total=file_size
            )

            try:
                # 新 SDK 上傳方式（自動重試）
                if API_RETRY_ENABLED:
                    @with_retry("檔案上傳", max_retries=3)
                    def _upload():
                        return client.files.upload(
                            path=file_path,
                            config=types.UploadFileConfig(
                                display_name=display_name,
                                mime_type=mime_type
                            )
                        )
                    uploaded_file = _upload()
                else:
                    uploaded_file = client.files.upload(
                        path=file_path,
                        config=types.UploadFileConfig(
                            display_name=display_name,
                            mime_type=mime_type
                        )
                    )

                # 更新進度為完成
                progress.update(task, completed=file_size, description="[green]✓ 上傳完成[/green]")

            except Exception as e:
                progress.update(task, description="[red]✗ 上傳失敗[/red]")
                raise Exception(f"上傳失敗: {e}")

        console.print(f"[green]✓ 檔案名稱：{uploaded_file.name}[/green]")

        # 等待處理（針對影片和音訊）
        if file_type in ['video', 'audio']:
            uploaded_file = self._wait_for_processing(uploaded_file)

        # 儲存到快取
        self.uploaded_files[display_name] = uploaded_file

        return uploaded_file

    def _find_existing_file(self, display_name: str) -> Optional[types.File]:
        """查找已上傳的檔案"""
        try:
            # 自動重試列出檔案
            if API_RETRY_ENABLED:
                @with_retry("列出檔案", max_retries=2)
                def _list_files():
                    return list(client.files.list())
                files = _list_files()
            else:
                files = list(client.files.list())

            for f in files:
                if f.display_name == display_name:
                    return f
        except Exception as e:
            console.print(f"[yellow]警告：無法列出檔案 - {e}[/yellow]")
        return None

    def _wait_for_processing(self, file: types.File) -> types.File:
        """等待檔案處理完成"""
        console.print(f"\n[cyan]⏳ 等待處理...[/cyan]")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("處理中...", total=None)

            start_time = time.time()
            while file.state.name == "PROCESSING":
                elapsed = int(time.time() - start_time)
                progress.update(task, description=f"處理中... ({elapsed}秒)")
                time.sleep(5)
                # 新 SDK 獲取檔案狀態（自動重試）
                if API_RETRY_ENABLED:
                    @with_retry("獲取檔案狀態", max_retries=2)
                    def _get_file():
                        return client.files.get(name=file.name)
                    file = _get_file()
                else:
                    file = client.files.get(name=file.name)

            if file.state.name == "FAILED":
                raise ValueError(f"處理失敗：{file.state.name}")

            progress.update(task, description="[green]✓ 處理完成[/green]")

        return file

    def upload_multiple_files(
        self,
        file_paths: List[str]
    ) -> List[types.File]:
        """
        批次上傳多個檔案

        Args:
            file_paths: 檔案路徑列表

        Returns:
            上傳的檔案物件列表
        """
        uploaded_files = []

        console.print(f"\n[bold cyan]📦 批次上傳 {len(file_paths)} 個檔案[/bold cyan]\n")

        for i, file_path in enumerate(file_paths, 1):
            console.print(f"[cyan]━━━ 檔案 {i}/{len(file_paths)} ━━━[/cyan]")
            try:
                uploaded_file = self.upload_file(file_path)
                uploaded_files.append(uploaded_file)
            except Exception as e:
                console.print(f"[red]✗ 上傳失敗：{e}[/red]")
                continue

        console.print(f"\n[green]✓ 批次上傳完成：{len(uploaded_files)}/{len(file_paths)} 成功[/green]")

        return uploaded_files

    def list_uploaded_files(self, max_files: int = 100) -> List[types.File]:
        """列出所有已上傳的檔案"""
        console.print(f"\n[cyan]📁 已上傳的檔案（最多 {max_files} 個）：[/cyan]\n")

        try:
            files = []
            count = 0
            for f in client.files.list():
                files.append(f)
                count += 1
                if count >= max_files:
                    break

            if not files:
                console.print("[yellow]沒有找到已上傳的檔案[/yellow]")
                return []

            # 建立表格
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("名稱", style="green")
            table.add_column("大小", justify="right")
            table.add_column("狀態", justify="center")
            table.add_column("建立時間")
            table.add_column("過期時間")

            for f in files:
                # 獲取檔案大小（如果有）
                size_str = "N/A"
                if hasattr(f, 'size_bytes') and f.size_bytes:
                    size_mb = f.size_bytes / (1024 * 1024)
                    size_str = f"{size_mb:.2f} MB"

                # 狀態顏色
                status_color = "green" if f.state.name == "ACTIVE" else "yellow"

                table.add_row(
                    f.display_name,
                    size_str,
                    f"[{status_color}]{f.state.name}[/{status_color}]",
                    str(f.create_time).split('.')[0] if f.create_time else "N/A",
                    str(f.expiration_time).split('.')[0] if f.expiration_time else "N/A"
                )

            console.print(table)
            console.print(f"\n總計：{len(files)} 個檔案")

            return files

        except Exception as e:
            console.print(f"[red]✗ 列出檔案失敗：{e}[/red]")
            return []

    def delete_file(self, file_name_or_display_name: str) -> bool:
        """
        刪除已上傳的檔案

        Args:
            file_name_or_display_name: 檔案名稱或顯示名稱

        Returns:
            是否成功刪除
        """
        try:
            # 新 SDK 刪除檔案
            client.files.delete(name=file_name_or_display_name)
            console.print(f"[green]✓ 已刪除：{file_name_or_display_name}[/green]")

            # 從快取移除
            if file_name_or_display_name in self.uploaded_files:
                del self.uploaded_files[file_name_or_display_name]

            return True

        except Exception as e:
            # 嘗試通過顯示名稱查找並刪除
            file = self._find_existing_file(file_name_or_display_name)
            if file:
                try:
                    client.files.delete(name=file.name)
                    console.print(f"[green]✓ 已刪除：{file_name_or_display_name}[/green]")
                    return True
                except Exception as e2:
                    console.print(f"[red]✗ 刪除失敗：{e2}[/red]")
                    return False
            else:
                console.print(f"[red]✗ 找不到檔案：{file_name_or_display_name}[/red]")
                return False

    def get_file_info(self, display_name: str) -> Optional[types.File]:
        """獲取檔案資訊"""
        file = self._find_existing_file(display_name)
        if file:
            console.print(f"\n[cyan]📄 檔案資訊：[/cyan]")
            console.print(f"   顯示名稱：{file.display_name}")
            console.print(f"   檔案名稱：{file.name}")
            console.print(f"   狀態：{file.state.name}")
            console.print(f"   建立時間：{file.create_time}")
            console.print(f"   過期時間：{file.expiration_time}")
            if hasattr(file, 'size_bytes') and file.size_bytes:
                console.print(f"   大小：{file.size_bytes / (1024 * 1024):.2f} MB")
            if hasattr(file, 'mime_type') and file.mime_type:
                console.print(f"   MIME 類型：{file.mime_type}")
            return file
        else:
            console.print(f"[red]找不到檔案：{display_name}[/red]")
            return None


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='Gemini 大檔案上傳管理器（新 SDK）')
    parser.add_argument('command', choices=['upload', 'list', 'delete', 'info'],
                       help='命令：upload(上傳), list(列表), delete(刪除), info(資訊)')
    parser.add_argument('files', nargs='*', help='檔案路徑（upload/delete/info 時使用）')
    parser.add_argument('--force', action='store_true', help='強制重新上傳')

    args = parser.parse_args()

    manager = FileManager()

    if args.command == 'upload':
        if not args.files:
            console.print("[red]錯誤：請提供要上傳的檔案路徑[/red]")
            sys.exit(1)

        if len(args.files) == 1:
            manager.upload_file(args.files[0], force_reupload=args.force)
        else:
            manager.upload_multiple_files(args.files)

    elif args.command == 'list':
        manager.list_uploaded_files()

    elif args.command == 'delete':
        if not args.files:
            console.print("[red]錯誤：請提供要刪除的檔案名稱[/red]")
            sys.exit(1)

        for file_name in args.files:
            manager.delete_file(file_name)

    elif args.command == 'info':
        if not args.files:
            console.print("[red]錯誤：請提供檔案名稱[/red]")
            sys.exit(1)

        for file_name in args.files:
            manager.get_file_info(file_name)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 互動模式
        console.print("\n[bold cyan]Gemini 大檔案上傳管理器（新 SDK）[/bold cyan]\n")
        console.print("使用方式：")
        console.print("  python3 gemini_file_manager.py upload <檔案路徑> [--force]")
        console.print("  python3 gemini_file_manager.py list")
        console.print("  python3 gemini_file_manager.py delete <檔案名稱>")
        console.print("  python3 gemini_file_manager.py info <檔案名稱>")
        console.print("\n範例：")
        console.print("  python3 gemini_file_manager.py upload large_video.mp4")
        console.print("  python3 gemini_file_manager.py upload file1.mp4 file2.mp4 file3.mp4")
        console.print("  python3 gemini_file_manager.py list")
        console.print("\n[yellow]註：新 SDK 自動處理大檔案分塊上傳[/yellow]")
        sys.exit(0)
    else:
        main()
