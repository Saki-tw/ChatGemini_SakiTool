#!/usr/bin/env python3
"""
Gemini 錯誤修復建議系統

此模組提供統一的錯誤處理與修復建議功能，
讓使用者在遇到錯誤時能夠快速找到解決方案並直接執行修復指令。

作者: Saki_tw (with Claude Code)
版本: 1.0.0
日期: 2025-10-22
"""

import os
import platform
import shutil
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from pathlib import Path
import glob as glob_module
from difflib import SequenceMatcher

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


@dataclass
class FixSuggestion:
    """修復建議數據結構"""

    title: str  # 建議標題
    description: str = ""  # 詳細說明
    commands: List[str] = field(default_factory=list)  # 可執行指令列表
    steps: List[str] = field(default_factory=list)  # 手動步驟
    platform_specific: Dict[str, List[str]] = field(default_factory=dict)  # 平台特定指令
    priority: int = 1  # 優先級（1=最高）
    category: str = "一般"  # 類別（環境、檔案、API等）
    notes: List[str] = field(default_factory=list)  # 注意事項
    links: List[str] = field(default_factory=list)  # 相關連結


class PlatformDetector:
    """平台偵測工具"""

    @staticmethod
    def get_os() -> str:
        """取得作業系統類型"""
        system = platform.system().lower()
        if system == "darwin":
            return "macOS"
        elif system == "linux":
            return "Linux"
        elif system == "windows":
            return "Windows"
        return system

    @staticmethod
    def get_linux_distro() -> Optional[str]:
        """取得 Linux 發行版"""
        if platform.system().lower() != "linux":
            return None

        # 嘗試讀取 /etc/os-release
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("ID="):
                        distro = line.split("=")[1].strip().strip('"')
                        if distro in ["ubuntu", "debian"]:
                            return "Debian/Ubuntu"
                        elif distro in ["fedora", "centos", "rhel"]:
                            return "Fedora/CentOS"
        except:
            pass

        return "Linux"

    @staticmethod
    def get_shell() -> str:
        """取得當前 Shell"""
        shell = os.environ.get("SHELL", "")
        if "zsh" in shell:
            return "zsh"
        elif "bash" in shell:
            return "bash"
        return "sh"

    @staticmethod
    def get_shell_rc_file() -> str:
        """取得 Shell 設定檔路徑"""
        shell = PlatformDetector.get_shell()
        home = str(Path.home())

        if shell == "zsh":
            return f"{home}/.zshrc"
        elif shell == "bash":
            if PlatformDetector.get_os() == "macOS":
                return f"{home}/.bash_profile"
            else:
                return f"{home}/.bashrc"
        return f"{home}/.profile"


class FileHelper:
    """檔案相關輔助工具"""

    @staticmethod
    def find_similar_files(file_path: str, max_results: int = 5) -> List[Dict[str, any]]:
        """
        尋找相似的檔案

        Args:
            file_path: 檔案路徑
            max_results: 最多返回幾個結果

        Returns:
            相似檔案列表，包含路徑、大小、修改時間等資訊
        """
        directory = os.path.dirname(file_path) or "."
        filename = os.path.basename(file_path)

        if not os.path.isdir(directory):
            return []

        similar_files = []

        # 搜尋目錄中的所有檔案
        try:
            for entry in os.scandir(directory):
                if entry.is_file():
                    # 計算檔名相似度
                    similarity = SequenceMatcher(None, filename, entry.name).ratio()

                    if similarity > 0.3:  # 相似度閾值
                        stat = entry.stat()
                        similar_files.append({
                            "path": entry.path,
                            "name": entry.name,
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "similarity": similarity
                        })
        except Exception:
            pass

        # 按相似度排序
        similar_files.sort(key=lambda x: x["similarity"], reverse=True)

        return similar_files[:max_results]

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化檔案大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def check_file_integrity(file_path: str) -> Dict[str, any]:
        """
        檢查檔案完整性

        Returns:
            包含 exists, readable, writable, executable, size 等資訊的字典
        """
        info = {
            "exists": os.path.exists(file_path),
            "readable": False,
            "writable": False,
            "executable": False,
            "size": 0,
            "is_empty": False
        }

        if info["exists"]:
            info["readable"] = os.access(file_path, os.R_OK)
            info["writable"] = os.access(file_path, os.W_OK)
            info["executable"] = os.access(file_path, os.X_OK)

            try:
                info["size"] = os.path.getsize(file_path)
                info["is_empty"] = info["size"] == 0
            except:
                pass

        return info

    @staticmethod
    def get_media_info(file_path: str) -> Optional[Dict[str, any]]:
        """
        獲取媒體檔案詳細資訊

        Args:
            file_path: 媒體檔案路徑

        Returns:
            包含檔案大小、時長、串流資訊等的字典，如果獲取失敗則返回 None
        """
        try:
            import subprocess
            import json

            # 使用 ffprobe 獲取媒體資訊
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                 '-show_format', '-show_streams', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            data = json.loads(result.stdout)

            # 解析格式資訊
            format_info = data.get('format', {})
            streams = data.get('streams', [])

            # 尋找影片和音訊串流
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)

            # 計算時長
            duration = float(format_info.get('duration', 0))
            duration_min = int(duration // 60)
            duration_sec = int(duration % 60)
            duration_str = f"{duration_min}:{duration_sec:02d}"

            # 計算檔案大小
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)

            # 建立資訊字典
            info = {
                'size_bytes': size_bytes,
                'size_mb': size_mb,
                'size_str': FileHelper.format_file_size(size_bytes),
                'duration': duration,
                'duration_str': duration_str,
                'has_video': video_stream is not None,
                'has_audio': audio_stream is not None,
            }

            # 影片串流資訊
            if video_stream:
                width = video_stream.get('width', 0)
                height = video_stream.get('height', 0)
                fps_str = video_stream.get('r_frame_rate', '0/1')

                # 計算 fps
                try:
                    fps_parts = fps_str.split('/')
                    if len(fps_parts) == 2:
                        fps = int(fps_parts[0]) / int(fps_parts[1])
                    else:
                        fps = float(fps_str)
                except:
                    fps = 0

                info['video_codec'] = video_stream.get('codec_name', 'unknown').upper()
                info['resolution'] = f"{width}x{height}"
                info['fps'] = int(fps)

            # 音訊串流資訊
            if audio_stream:
                channels = audio_stream.get('channels', 0)
                sample_rate = audio_stream.get('sample_rate', 'unknown')

                info['audio_codec'] = audio_stream.get('codec_name', 'unknown').upper()
                info['sample_rate'] = sample_rate
                info['channels'] = 'stereo' if channels == 2 else ('mono' if channels == 1 else f'{channels}ch')

            return info

        except Exception as e:
            # 靜默失敗，返回 None
            return None


class CommandGenerator:
    """指令生成器"""

    @staticmethod
    def ffmpeg_install_commands() -> Dict[str, List[str]]:
        """生成 ffmpeg 安裝指令"""
        return {
            "macOS": ["brew install ffmpeg"],
            "Debian/Ubuntu": ["sudo apt-get update", "sudo apt-get install ffmpeg"],
            "Fedora/CentOS": ["sudo yum install ffmpeg"],
            "Windows": ["# 請從 https://ffmpeg.org/download.html 下載並安裝"]
        }

    @staticmethod
    def env_var_set_commands(var_name: str, var_value: str = "your-value-here") -> Dict[str, List[str]]:
        """生成環境變數設定指令"""
        shell_rc = PlatformDetector.get_shell_rc_file()

        return {
            "臨時設定（本次終端）": [
                f'export {var_name}="{var_value}"'
            ],
            "永久設定（寫入設定檔）": [
                f'echo \'export {var_name}="{var_value}"\' >> {shell_rc}',
                f'source {shell_rc}'
            ]
        }

    @staticmethod
    def file_repair_commands(file_path: str) -> List[str]:
        """生成檔案修復指令"""
        ext = os.path.splitext(file_path)[1].lower()
        repaired_path = file_path.replace(ext, f"_repaired{ext}")

        if ext in [".mp4", ".mov", ".avi", ".mkv"]:
            return [
                f'ffmpeg -i "{file_path}" -c copy "{repaired_path}"'
            ]
        elif ext in [".mp3", ".wav", ".aac", ".flac"]:
            return [
                f'ffmpeg -i "{file_path}" -c copy "{repaired_path}"'
            ]
        else:
            return []

    @staticmethod
    def file_info_commands(file_path: str) -> List[str]:
        """生成檔案資訊查詢指令"""
        commands = []

        # 基本資訊
        if PlatformDetector.get_os() != "Windows":
            commands.append(f'file "{file_path}"')
            commands.append(f'ls -lh "{file_path}"')

        # 媒體檔案資訊
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".aac"]:
            commands.append(f'ffprobe -v error -show_format -show_streams "{file_path}"')

        return commands


class ErrorFixer:
    """錯誤修復建議生成器"""

    def __init__(self):
        self.platform = PlatformDetector.get_os()
        self.linux_distro = PlatformDetector.get_linux_distro()

    def display_error_with_fixes(
        self,
        error_message: str,
        error_type: str,
        suggestions: List[FixSuggestion],
        context: Optional[Dict[str, any]] = None
    ):
        """
        顯示錯誤訊息與修復建議

        Args:
            error_message: 錯誤訊息
            error_type: 錯誤類型
            suggestions: 修復建議列表
            context: 額外的上下文資訊
        """
        console.print()
        console.print("=" * 80, style="red")
        console.print(f"✗ {error_type}", style="bold red")
        console.print("=" * 80, style="red")
        console.print()

        # 顯示錯誤訊息
        console.print(Panel(
            error_message,
            title="錯誤詳情",
            border_style="red",
            box=box.ROUNDED
        ))

        # 顯示上下文資訊（如果有）
        if context:
            console.print()
            context_text = "\n".join([f"{k}: {v}" for k, v in context.items()])
            console.print(Panel(
                context_text,
                title="相關資訊",
                border_style="yellow",
                box=box.ROUNDED
            ))

        # 顯示修復建議
        console.print()
        console.print("💡 [bold cyan]修復建議[/bold cyan]")
        console.print()

        for i, suggestion in enumerate(suggestions, 1):
            self._display_suggestion(i, suggestion)

    def _display_suggestion(self, index: int, suggestion: FixSuggestion):
        """顯示單個修復建議"""

        # 標題
        console.print(f"[bold green]{index}️⃣ {suggestion.title}[/bold green]")

        # 說明
        if suggestion.description:
            console.print(f"   {suggestion.description}")

        # 平台特定指令
        if suggestion.platform_specific:
            for platform_name, commands in suggestion.platform_specific.items():
                console.print(f"\n   [cyan]🔧 {platform_name}[/cyan]")
                console.print("   執行指令：")

                for cmd in commands:
                    # 使用 Panel 顯示指令框
                    console.print(Panel(
                        Text(cmd, style="bold yellow"),
                        box=box.ROUNDED,
                        border_style="cyan",
                        padding=(0, 1),
                        expand=False
                    ))

        # 一般指令
        elif suggestion.commands:
            console.print("\n   執行指令：")
            for cmd in suggestion.commands:
                console.print(Panel(
                    Text(cmd, style="bold yellow"),
                    box=box.ROUNDED,
                    border_style="cyan",
                    padding=(0, 1),
                    expand=False
                ))

        # 手動步驟
        if suggestion.steps:
            console.print("\n   [cyan]📝 手動步驟：[/cyan]")
            for step_idx, step in enumerate(suggestion.steps, 1):
                console.print(f"   {step_idx}. {step}")

        # 注意事項
        if suggestion.notes:
            console.print("\n   [yellow]⚠️  注意事項：[/yellow]")
            for note in suggestion.notes:
                console.print(f"   • {note}")

        # 相關連結
        if suggestion.links:
            console.print("\n   [blue]🔗 相關連結：[/blue]")
            for link in suggestion.links:
                console.print(f"   • {link}")

        console.print()

    # ==================== 特定錯誤類型的修復建議生成器 ====================

    def suggest_ffmpeg_not_found(self) -> List[FixSuggestion]:
        """生成 ffmpeg 未安裝的修復建議"""
        suggestions = []

        # 安裝 ffmpeg
        install_cmds = CommandGenerator.ffmpeg_install_commands()

        platform_cmds = {}
        if self.platform == "macOS":
            platform_cmds["macOS 用戶"] = install_cmds["macOS"]
        elif self.platform == "Linux":
            if self.linux_distro == "Debian/Ubuntu":
                platform_cmds["Linux (Ubuntu/Debian) 用戶"] = install_cmds["Debian/Ubuntu"]
            elif self.linux_distro == "Fedora/CentOS":
                platform_cmds["Linux (Fedora/CentOS) 用戶"] = install_cmds["Fedora/CentOS"]
            else:
                platform_cmds["Linux 用戶"] = install_cmds["Debian/Ubuntu"]
        elif self.platform == "Windows":
            platform_cmds["Windows 用戶"] = install_cmds["Windows"]

        suggestions.append(FixSuggestion(
            title="安裝 ffmpeg",
            description="ffmpeg 是處理音訊與影片的必要工具",
            platform_specific=platform_cmds,
            priority=1,
            category="環境",
            notes=["安裝完成後請重新執行程式"],
            links=["https://ffmpeg.org/download.html"]
        ))

        return suggestions

    def suggest_api_key_not_set(self, var_name: str = "GEMINI_API_KEY") -> List[FixSuggestion]:
        """生成 API 金鑰未設定的修復建議"""
        suggestions = []

        env_cmds = CommandGenerator.env_var_set_commands(var_name)

        suggestions.append(FixSuggestion(
            title="設定 API 金鑰",
            description="需要設定 Gemini API 金鑰才能使用此功能",
            platform_specific=env_cmds,
            priority=1,
            category="環境",
            steps=[
                "前往 https://aistudio.google.com/apikey",
                "登入 Google 帳號",
                "點擊「Create API Key」",
                "複製金鑰並使用上述指令設定"
            ],
            links=["https://aistudio.google.com/apikey"]
        ))

        return suggestions

    def suggest_file_not_found(self, file_path: str) -> List[FixSuggestion]:
        """生成檔案不存在的修復建議"""
        suggestions = []

        # 尋找相似檔案
        similar_files = FileHelper.find_similar_files(file_path, max_results=5)

        if similar_files:
            files_info = "\n".join([
                f"{i+1}. {f['name']} ({FileHelper.format_file_size(f['size'])})"
                for i, f in enumerate(similar_files)
            ])

            suggestions.append(FixSuggestion(
                title="相似檔案",
                description=f"在相同目錄找到 {len(similar_files)} 個相似檔案：\n{files_info}",
                steps=[
                    "檢查是否為檔名錯誤",
                    "使用上述相似檔案之一重新執行程式"
                ],
                priority=1,
                category="檔案"
            ))

        # 搜尋檔案
        directory = os.path.dirname(file_path) or "."
        filename = os.path.basename(file_path)

        suggestions.append(FixSuggestion(
            title="搜尋檔案",
            description="使用 find 指令搜尋檔案",
            commands=[
                f'find "{directory}" -name "*{filename}*"'
            ],
            priority=2,
            category="檔案"
        ))

        return suggestions

    def suggest_file_empty(self, file_path: str) -> List[FixSuggestion]:
        """生成檔案為空的修復建議"""
        suggestions = []

        suggestions.append(FixSuggestion(
            title="可能的原因與解決方案",
            description="檔案為空可能由以下原因造成",
            steps=[
                "⚠️  下載未完成 - 檢查下載是否完整並重新下載",
                "⚠️  檔案傳輸中斷 - 使用可靠的檔案傳輸方式",
                "⚠️  磁碟空間不足 - 使用下方指令檢查磁碟空間"
            ],
            commands=["df -h"] if self.platform != "Windows" else ["wmic logicaldisk get size,freespace,caption"],
            priority=1,
            category="檔案"
        ))

        suggestions.append(FixSuggestion(
            title="刪除空檔案",
            description="如果確定此檔案無用，可以刪除",
            commands=[f'rm "{file_path}"'] if self.platform != "Windows" else [f'del "{file_path}"'],
            priority=2,
            category="檔案",
            notes=["刪除前請確認檔案確實無用"]
        ))

        return suggestions

    def suggest_file_corrupted(self, file_path: str, error_detail: str = "") -> List[FixSuggestion]:
        """生成檔案損壞的修復建議"""
        suggestions = []

        ext = os.path.splitext(file_path)[1].lower()

        # 嘗試修復檔案
        if ext in [".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".aac"]:
            repair_cmds = CommandGenerator.file_repair_commands(file_path)

            suggestions.append(FixSuggestion(
                title="嘗試修復檔案（重新封裝）",
                description="使用 ffmpeg 重新封裝檔案，可能修復輕微損壞",
                commands=repair_cmds,
                priority=1,
                category="檔案",
                notes=["此方法僅適用於輕微損壞的檔案"]
            ))

        # 驗證檔案
        info_cmds = CommandGenerator.file_info_commands(file_path)
        if info_cmds:
            suggestions.append(FixSuggestion(
                title="驗證檔案完整性",
                description="使用工具檢查檔案詳細資訊",
                commands=info_cmds,
                priority=2,
                category="檔案"
            ))

        # 重新獲取檔案
        suggestions.append(FixSuggestion(
            title="重新獲取檔案",
            description="如果檔案確實損壞，建議重新下載或獲取",
            steps=[
                "重新下載或獲取原始檔案",
                "檢查下載/傳輸過程是否完整",
                "驗證檔案 MD5 / SHA256 校驗碼（如有提供）"
            ],
            priority=3,
            category="檔案"
        ))

        return suggestions

    def suggest_missing_stream(self, file_path: str, stream_type: str = "audio") -> List[FixSuggestion]:
        """生成缺少音訊/影片串流的修復建議"""
        suggestions = []

        stream_name = "音訊" if stream_type == "audio" else "影片"
        file_stem = os.path.splitext(file_path)[0]

        if stream_type == "audio":
            # === 缺少音訊串流的解決方案 ===

            # 選項 1：添加靜音音軌（推薦）
            output_path = f"{file_stem}_with_audio.mp4"
            suggestions.append(FixSuggestion(
                title="添加靜音音軌（推薦）",
                description=(
                    "為影片添加靜音音軌，以滿足處理需求\n\n"
                    "說明：\n"
                    "  • anullsrc：生成靜音音訊\n"
                    "  • r=48000：採樣率 48kHz（標準）\n"
                    "  • cl=stereo：立體聲\n"
                    "  • c:v copy：影片不重新編碼（快速）\n\n"
                    "預估時間：約 30-60 秒"
                ),
                commands=[
                    f'ffmpeg -i "{file_path}" \\',
                    '       -f lavfi -i anullsrc=r=48000:cl=stereo \\',
                    '       -c:v copy -c:a aac \\',
                    '       -shortest \\',
                    f'       "{output_path}"'
                ],
                priority=1,
                category="檔案"
            ))

            # 選項 2：添加背景音樂
            music_output = f"{file_stem}_with_music.mp4"
            suggestions.append(FixSuggestion(
                title="添加背景音樂",
                description="如果您有背景音樂檔案，可以直接添加",
                commands=[
                    f'ffmpeg -i "{file_path}" \\',
                    '       -i "/path/to/music.mp3" \\',
                    '       -c:v copy -c:a aac \\',
                    '       -shortest \\',
                    f'       "{music_output}"'
                ],
                priority=2,
                category="檔案",
                notes=["請將 /path/to/music.mp3 替換為實際的音樂檔案路徑"]
            ))

            # 選項 3：檢查檔案詳細資訊
            suggestions.append(FixSuggestion(
                title="檢查檔案詳細資訊",
                description="執行指令查看所有串流",
                commands=[
                    f'ffprobe -v error -show_streams "{file_path}"'
                ],
                priority=3,
                category="檔案"
            ))

            # 選項 4：使用其他檔案
            suggestions.append(FixSuggestion(
                title="使用其他檔案",
                description="如果您需要包含音訊的影片，請使用包含音軌的影片檔案",
                steps=[
                    "某些情況下無音訊是正常的，例如：",
                    "  • 螢幕錄影（未錄製聲音）",
                    "  • GIF 轉 MP4",
                    "  • 延時攝影"
                ],
                priority=4,
                category="檔案"
            ))

        else:  # stream_type == "video"
            # === 缺少影片串流的解決方案 ===

            # 選項 1：添加黑屏影片（推薦）
            black_output = f"{file_stem}_with_video.mp4"
            suggestions.append(FixSuggestion(
                title="添加黑屏影片（推薦）",
                description=(
                    "為音訊添加黑屏影片軌，以滿足處理需求\n\n"
                    "說明：\n"
                    "  • color=black：黑色畫面\n"
                    "  • s=1280x720：解析度 720p\n"
                    "  • r=30：幀率 30fps\n"
                    "  • c:a copy：音訊不重新編碼（快速）"
                ),
                commands=[
                    'ffmpeg -f lavfi -i color=black:s=1280x720:r=30 \\',
                    f'       -i "{file_path}" \\',
                    '       -c:v libx264 -c:a copy \\',
                    '       -shortest \\',
                    f'       "{black_output}"'
                ],
                priority=1,
                category="檔案"
            ))

            # 選項 2：添加靜態圖片
            image_output = f"{file_stem}_with_image.mp4"
            suggestions.append(FixSuggestion(
                title="添加靜態圖片",
                description="使用圖片作為影片背景",
                commands=[
                    'ffmpeg -loop 1 -i "/path/to/image.jpg" \\',
                    f'       -i "{file_path}" \\',
                    '       -c:v libx264 -c:a copy \\',
                    '       -shortest \\',
                    f'       "{image_output}"'
                ],
                priority=2,
                category="檔案",
                notes=["請將 /path/to/image.jpg 替換為實際的圖片檔案路徑"]
            ))

            # 選項 3：轉換為純音訊格式
            audio_output = f"{file_stem}.mp3"
            suggestions.append(FixSuggestion(
                title="轉換為純音訊格式",
                description="如果您只需要音訊，建議轉換為 .mp3 或 .aac",
                commands=[
                    f'ffmpeg -i "{file_path}" \\',
                    '       -vn -c:a copy \\',
                    f'       "{audio_output}"'
                ],
                priority=3,
                category="檔案",
                notes=["-vn 表示不包含影片串流"]
            ))

        return suggestions

    def suggest_unsupported_filter(self, filter_name: str, supported_filters: dict) -> List[FixSuggestion]:
        """生成不支援的濾鏡的修復建議"""
        suggestions = []

        # 濾鏡描述對照表
        filter_descriptions = {
            'grayscale': ('黑白效果', '將影片轉為灰階', 'hue=s=0'),
            'sepia': ('懷舊效果', '棕褐色調，復古風格', 'colorchannelmixer'),
            'vintage': ('復古效果', '經典復古色調', 'curves=vintage'),
            'contrast': ('高對比', '增強對比度，畫面更鮮明', 'eq=contrast=1.2'),
            'blur': ('模糊效果', '高斯模糊，柔焦效果', 'boxblur=2:1'),
            'sharpen': ('銳化', '增強邊緣清晰度', 'unsharp=5:5:1.0'),
            'brighten': ('增亮', '提升畫面亮度', 'eq=brightness=0.1'),
            'vignette': ('暈影', '邊緣變暗效果，聚焦中心', 'vignette'),
        }

        # 建立濾鏡列表說明
        filter_list = []
        for fname in sorted(supported_filters.keys()):
            if fname in filter_descriptions:
                name_cn, desc, _ = filter_descriptions[fname]
                filter_list.append(f"  ✅ {name_cn} ({fname})\n     特性：{desc}")
            else:
                filter_list.append(f"  ✅ {fname}")

        filter_list_str = "\n\n".join(filter_list)

        # 建議 1：顯示支援的濾鏡列表
        suggestions.append(FixSuggestion(
            title="支援的濾鏡列表",
            description=f"以下是所有可用的濾鏡效果：\n\n{filter_list_str}",
            priority=1,
            category="參數"
        ))

        # 建議 2：使用範例
        examples = []
        example_filters = list(supported_filters.keys())[:3]  # 取前 3 個作為範例
        for ex in example_filters:
            examples.append(f'apply_filter(video_path, "{ex}", output_path)')

        suggestions.append(FixSuggestion(
            title="濾鏡使用範例",
            description="以下是正確的濾鏡使用方式",
            commands=examples,
            priority=2,
            category="參數",
            steps=[
                "1. 選擇上述支援的濾鏡名稱",
                "2. 將濾鏡名稱作為參數傳入 apply_filter() 函數",
                "3. 可選擇品質參數：'high'（高）、'medium'（中）、'low'（低）"
            ]
        ))

        # 建議 3：模糊匹配（如果輸入的名稱與某個支援的濾鏡相似）
        from difflib import get_close_matches
        similar = get_close_matches(filter_name, supported_filters.keys(), n=3, cutoff=0.4)

        if similar:
            similar_desc = "\n".join([
                f"  • {s}" + (f" - {filter_descriptions[s][0]}" if s in filter_descriptions else "")
                for s in similar
            ])

            suggestions.append(FixSuggestion(
                title="您是否想使用以下濾鏡？",
                description=f"根據您輸入的 '{filter_name}'，可能是指：\n\n{similar_desc}",
                priority=3,
                category="參數",
                notes=[f"嘗試使用 '{similar[0]}' 替代 '{filter_name}'"]
            ))

        return suggestions


# ==================== 便捷函數 ====================

def show_ffmpeg_not_found_error():
    """顯示 ffmpeg 未安裝錯誤與修復建議"""
    fixer = ErrorFixer()
    suggestions = fixer.suggest_ffmpeg_not_found()
    fixer.display_error_with_fixes(
        error_message="系統中找不到 ffmpeg 工具，無法處理音訊或影片檔案。",
        error_type="ffmpeg 未安裝",
        suggestions=suggestions
    )


def show_api_key_not_set_error(var_name: str = "GEMINI_API_KEY"):
    """顯示 API 金鑰未設定錯誤與修復建議"""
    fixer = ErrorFixer()
    suggestions = fixer.suggest_api_key_not_set(var_name)
    fixer.display_error_with_fixes(
        error_message=f"環境變數 {var_name} 未設定，無法使用 Gemini API。",
        error_type="API 金鑰未設定",
        suggestions=suggestions
    )


def show_file_not_found_error(file_path: str):
    """顯示檔案不存在錯誤與修復建議"""
    fixer = ErrorFixer()
    suggestions = fixer.suggest_file_not_found(file_path)
    fixer.display_error_with_fixes(
        error_message=f"找不到檔案：{file_path}",
        error_type="檔案不存在",
        suggestions=suggestions,
        context={"檔案路徑": file_path}
    )


def show_file_empty_error(file_path: str):
    """顯示檔案為空錯誤與修復建議"""
    fixer = ErrorFixer()
    suggestions = fixer.suggest_file_empty(file_path)
    fixer.display_error_with_fixes(
        error_message=f"檔案為空（0 bytes）：{file_path}",
        error_type="檔案為空",
        suggestions=suggestions,
        context={"檔案路徑": file_path}
    )


def show_file_corrupted_error(file_path: str, error_detail: str = ""):
    """顯示檔案損壞錯誤與修復建議"""
    fixer = ErrorFixer()
    suggestions = fixer.suggest_file_corrupted(file_path, error_detail)

    error_msg = f"檔案格式錯誤或損壞：{file_path}"
    if error_detail:
        error_msg += f"\n\n詳細資訊：{error_detail}"

    fixer.display_error_with_fixes(
        error_message=error_msg,
        error_type="檔案損壞",
        suggestions=suggestions,
        context={"檔案路徑": file_path}
    )


def show_missing_stream_error(file_path: str, stream_type: str = "audio"):
    """顯示缺少串流錯誤與修復建議（包含詳細檔案資訊）"""
    fixer = ErrorFixer()
    suggestions = fixer.suggest_missing_stream(file_path, stream_type)

    stream_name = "音訊" if stream_type == "audio" else "影片"

    # 獲取媒體檔案詳細資訊
    media_info = FileHelper.get_media_info(file_path)

    # 建立上下文資訊
    context = {"檔案路徑": file_path}

    if media_info:
        # 顯示檔案詳細資訊
        context["檔案資訊"] = (
            f"\n  • 大小：{media_info['size_str']}\n"
            f"  • 時長：{media_info['duration_str']}"
        )

        # 影片串流資訊
        if media_info['has_video']:
            video_info = (
                f"✓ 存在（{media_info['video_codec']}, "
                f"{media_info['resolution']}, "
                f"{media_info['fps']}fps）"
            )
        else:
            video_info = "✗ 不存在"
        context["影片串流"] = video_info

        # 音訊串流資訊
        if media_info['has_audio']:
            audio_info = (
                f"✓ 存在（{media_info['audio_codec']}, "
                f"{media_info['sample_rate']}Hz, "
                f"{media_info['channels']}）"
            )
        else:
            audio_info = "✗ 不存在"
        context["音訊串流"] = audio_info

    fixer.display_error_with_fixes(
        error_message=f"檔案不包含{stream_name}串流：{file_path}",
        error_type=f"缺少{stream_name}串流",
        suggestions=suggestions,
        context=context
    )


def show_unsupported_filter_error(filter_name: str, supported_filters: dict):
    """顯示不支援的濾鏡錯誤與修復建議"""
    fixer = ErrorFixer()
    suggestions = fixer.suggest_unsupported_filter(filter_name, supported_filters)

    # 建立上下文資訊
    context = {
        "輸入的濾鏡": filter_name,
        "支援的濾鏡數量": len(supported_filters)
    }

    fixer.display_error_with_fixes(
        error_message=f"不支援的濾鏡：{filter_name}",
        error_type="不支援的濾鏡",
        suggestions=suggestions,
        context=context
    )


# ==================== 測試程式 ====================

if __name__ == "__main__":
    """測試各種錯誤修復建議"""

    console.print("\n[bold cyan]錯誤修復建議系統測試[/bold cyan]\n")

    # 測試 1: ffmpeg 未安裝
    console.print("[yellow]測試 1: ffmpeg 未安裝[/yellow]")
    show_ffmpeg_not_found_error()

    console.print("\n" + "=" * 80 + "\n")

    # 測試 2: API 金鑰未設定
    console.print("[yellow]測試 2: API 金鑰未設定[/yellow]")
    show_api_key_not_set_error()

    console.print("\n" + "=" * 80 + "\n")

    # 測試 3: 檔案不存在
    console.print("[yellow]測試 3: 檔案不存在[/yellow]")
    show_file_not_found_error("/path/to/nonexistent/video.mp4")

    console.print("\n" + "=" * 80 + "\n")

    # 測試 4: 檔案為空
    console.print("[yellow]測試 4: 檔案為空[/yellow]")
    show_file_empty_error("/path/to/empty/video.mp4")

    console.print("\n" + "=" * 80 + "\n")

    # 測試 5: 檔案損壞
    console.print("[yellow]測試 5: 檔案損壞[/yellow]")
    show_file_corrupted_error("/path/to/corrupted/video.mp4", "moov atom not found")

    console.print("\n" + "=" * 80 + "\n")

    # 測試 6: 缺少音訊串流
    console.print("[yellow]測試 6: 缺少音訊串流[/yellow]")
    show_missing_stream_error("/path/to/video.mp4", "audio")
