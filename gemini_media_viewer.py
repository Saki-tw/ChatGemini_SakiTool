#!/usr/bin/env python3
"""
Gemini 媒體檔案查看器
提供圖片和影片的資訊查看、預覽和 AI 分析功能
"""
import os
import sys
import subprocess
import json
from typing import Dict, Optional, List, Tuple
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# 導入價格模組
from utils.pricing_loader import get_pricing_calculator, PRICING_ENABLED
from gemini_pricing import USD_TO_TWD

console = Console()

# 初始化價格計算器
global_pricing_calculator = get_pricing_calculator(silent=True)

# 支援的檔案格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'}
VIDEO_EXTENSIONS = {'.mp4', '.mpeg', '.mov', '.avi', '.flv', '.wmv', '.webm', '.mkv', '.m4v'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a', '.wma'}


class MediaViewer:
    """媒體檔案查看器"""

    def __init__(self):
        """初始化查看器"""
        self.console = console

        # 初始化 Gemini API（如果可用）
        if GENAI_AVAILABLE:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                self.client = genai.Client(api_key=api_key)
                self.ai_analysis_enabled = True
            else:
                self.client = None
                self.ai_analysis_enabled = False
        else:
            self.client = None
            self.ai_analysis_enabled = False

    def get_file_type(self, file_path: str) -> str:
        """判斷檔案類型"""
        ext = Path(file_path).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return 'image'
        elif ext in VIDEO_EXTENSIONS:
            return 'video'
        elif ext in AUDIO_EXTENSIONS:
            return 'audio'
        else:
            return 'unknown'

    def get_image_info(self, image_path: str) -> Dict:
        """
        獲取圖片資訊

        Args:
            image_path: 圖片路徑

        Returns:
            圖片資訊字典
        """
        if not os.path.isfile(image_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_file_not_found
                alternative_path = suggest_file_not_found(image_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    image_path = alternative_path
                    console.print(f"[bright_magenta]✅ 已切換至：{image_path}[/green]\n")
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"圖片檔案不存在: {image_path}")

        info = {
            'path': image_path,
            'filename': os.path.basename(image_path),
            'size_bytes': os.path.getsize(image_path),
            'size_mb': os.path.getsize(image_path) / (1024 * 1024),
        }

        # 使用 Pillow 獲取詳細資訊
        if PILLOW_AVAILABLE:
            try:
                with Image.open(image_path) as img:
                    info['width'] = img.width
                    info['height'] = img.height
                    info['format'] = img.format
                    info['mode'] = img.mode
                    info['resolution'] = f"{img.width}x{img.height}"

                    # 計算寬高比
                    from math import gcd
                    divisor = gcd(img.width, img.height)
                    info['aspect_ratio'] = f"{img.width//divisor}:{img.height//divisor}"

            except Exception as e:
                info['error'] = str(e)

        return info

    def get_video_info(self, video_path: str) -> Dict:
        """
        獲取影片資訊

        Args:
            video_path: 影片路徑

        Returns:
            影片資訊字典
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_file_not_found
                alternative_path = suggest_file_not_found(video_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    video_path = alternative_path
                    console.print(f"[bright_magenta]✅ 已切換至：{video_path}[/green]\n")
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"影片檔案不存在: {video_path}")

        info = {
            'path': video_path,
            'filename': os.path.basename(video_path),
            'size_bytes': os.path.getsize(video_path),
            'size_mb': os.path.getsize(video_path) / (1024 * 1024),
            'size_gb': os.path.getsize(video_path) / (1024 * 1024 * 1024),
        }

        # 使用 ffprobe 獲取詳細資訊
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)

                # 格式資訊
                if 'format' in data:
                    fmt = data['format']
                    info['duration'] = float(fmt.get('duration', 0))
                    info['bitrate'] = int(fmt.get('bit_rate', 0))
                    info['format_name'] = fmt.get('format_name', 'Unknown')

                # 視訊流資訊
                video_stream = None
                audio_stream = None

                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video' and not video_stream:
                        video_stream = stream
                    elif stream.get('codec_type') == 'audio' and not audio_stream:
                        audio_stream = stream

                if video_stream:
                    info['width'] = video_stream.get('width', 0)
                    info['height'] = video_stream.get('height', 0)
                    info['resolution'] = f"{info['width']}x{info['height']}"
                    info['codec'] = video_stream.get('codec_name', 'Unknown')
                    info['fps'] = eval(video_stream.get('r_frame_rate', '0/1'))

                    # 計算寬高比
                    if info['width'] and info['height']:
                        from math import gcd
                        divisor = gcd(info['width'], info['height'])
                        info['aspect_ratio'] = f"{info['width']//divisor}:{info['height']//divisor}"

                if audio_stream:
                    info['audio_codec'] = audio_stream.get('codec_name', 'Unknown')
                    info['audio_channels'] = audio_stream.get('channels', 0)
                    info['audio_sample_rate'] = audio_stream.get('sample_rate', 0)

        except subprocess.TimeoutExpired:
            info['error'] = 'ffprobe timeout'
        except Exception as e:
            info['error'] = str(e)

        return info

    def display_image_info(self, image_path: str):
        """顯示圖片資訊"""
        self.console.print(f"\n[magenta]📸 圖片資訊：{os.path.basename(image_path)}[/magenta]\n")

        try:
            info = self.get_image_info(image_path)

            # 創建資訊表格
            table = Table(show_header=False, box=None)
            table.add_column("屬性", style="bright_magenta")
            table.add_column("值", style="white")

            table.add_row("檔案名稱", info['filename'])
            table.add_row("檔案路徑", info['path'])
            table.add_row("檔案大小", f"{info['size_mb']:.2f} MB ({info['size_bytes']:,} bytes)")

            if 'resolution' in info:
                table.add_row("解析度", info['resolution'])
            if 'aspect_ratio' in info:
                table.add_row("寬高比", info['aspect_ratio'])
            if 'format' in info:
                table.add_row("格式", info['format'])
            if 'mode' in info:
                table.add_row("色彩模式", info['mode'])

            self.console.print(table)

            if 'error' in info:
                self.console.print(f"\n[magenta]⚠ 警告：{info['error']}[/yellow]")

        except Exception as e:
            self.console.print(f"[dim magenta]錯誤：{e}[/red]")

    def display_video_info(self, video_path: str):
        """顯示影片資訊"""
        self.console.print(f"\n[magenta]🎬 影片資訊：{os.path.basename(video_path)}[/magenta]\n")

        try:
            info = self.get_video_info(video_path)

            # 創建資訊表格
            table = Table(show_header=False, box=None)
            table.add_column("屬性", style="bright_magenta")
            table.add_column("值", style="white")

            table.add_row("檔案名稱", info['filename'])
            table.add_row("檔案路徑", info['path'])

            # 檔案大小
            if info['size_gb'] >= 1:
                table.add_row("檔案大小", f"{info['size_gb']:.2f} GB")
            else:
                table.add_row("檔案大小", f"{info['size_mb']:.2f} MB")

            if 'duration' in info:
                duration = info['duration']
                minutes = int(duration // 60)
                seconds = duration % 60
                table.add_row("時長", f"{minutes}:{seconds:05.2f} ({duration:.2f} 秒)")

            if 'resolution' in info:
                table.add_row("解析度", info['resolution'])
            if 'aspect_ratio' in info:
                table.add_row("寬高比", info['aspect_ratio'])
            if 'fps' in info:
                table.add_row("幀率", f"{info['fps']:.2f} FPS")
            if 'codec' in info:
                table.add_row("視訊編碼", info['codec'])
            if 'audio_codec' in info:
                table.add_row("音訊編碼", info['audio_codec'])
            if 'audio_channels' in info:
                table.add_row("音訊聲道", str(info['audio_channels']))
            if 'bitrate' in info:
                bitrate_mbps = info['bitrate'] / 1_000_000
                table.add_row("比特率", f"{bitrate_mbps:.2f} Mbps")

            self.console.print(table)

            # API 限制檢查
            if info['size_mb'] > 2000:
                self.console.print(f"\n[dim magenta]⚠ 警告：檔案大小超過 Gemini API 限制（2GB）[/red]")
            elif info['size_mb'] > 1900:
                self.console.print(f"\n[magenta]⚠ 提示：檔案大小接近 API 限制，建議壓縮[/yellow]")

            if 'error' in info:
                self.console.print(f"\n[magenta]⚠ 警告：{info['error']}[/yellow]")

        except Exception as e:
            self.console.print(f"[dim magenta]錯誤：{e}[/red]")

    def analyze_with_ai(self, file_path: str, custom_prompt: Optional[str] = None):
        """
        使用 Gemini AI 分析媒體檔案

        Args:
            file_path: 檔案路徑
            custom_prompt: 自訂提示（可選）
        """
        if not self.ai_analysis_enabled:
            self.console.print("[magenta]AI 分析功能未啟用（需要 GEMINI_API_KEY）[/yellow]")
            return

        file_type = self.get_file_type(file_path)

        if file_type not in ['image', 'video']:
            self.console.print(f"[magenta]不支援的檔案類型：{file_type}[/yellow]")
            return

        self.console.print(f"\n[magenta]🤖 AI 分析中...[/magenta]\n")

        try:
            # 上傳檔案
            uploaded_file = self.client.files.upload(file=file_path)

            # 準備提示
            if custom_prompt:
                prompt = custom_prompt
            else:
                if file_type == 'image':
                    prompt = "請詳細描述這張圖片的內容、風格、色彩和主題。"
                else:  # video
                    prompt = "請分析這段影片的內容、場景、動作和主題。"

            # 生成分析
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=[uploaded_file, prompt]
            )

            # 提取並計算成本
            if PRICING_ENABLED and global_pricing_calculator:
                thinking_tokens = getattr(response.usage_metadata, 'thinking_tokens', 0)
                input_tokens = getattr(response.usage_metadata, 'prompt_tokens', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_tokens', 0)

                cost, details = global_pricing_calculator.calculate_text_cost(
                    'gemini-2.0-flash-exp',
                    input_tokens,
                    output_tokens,
                    thinking_tokens
                )

                # 顯示成本資訊
                if cost > 0:
                    self.console.print(f"[dim]💰 分析成本: NT${cost * USD_TO_TWD:.2f} (${cost:.6f} USD)[/dim]")
                    self.console.print(f"[dim]   輸入: {input_tokens:,} tokens, 輸出: {output_tokens:,} tokens, 思考: {thinking_tokens:,} tokens[/dim]")
                    self.console.print(f"[dim]   累計成本: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f} (${global_pricing_calculator.total_cost:.6f} USD)[/dim]")

            # 顯示結果
            self.console.print(Panel(
                response.text,
                title="[bold magenta]AI 分析結果[/bold magenta]",
                border_style="bright_magenta"
            ))

        except Exception as e:
            self.console.print(f"[dim magenta]AI 分析失敗：{e}[/red]")

    def view_file(self, file_path: str, analyze: bool = False, custom_prompt: Optional[str] = None):
        """
        查看媒體檔案

        Args:
            file_path: 檔案路徑
            analyze: 是否進行 AI 分析
            custom_prompt: 自訂分析提示
        """
        if not os.path.isfile(file_path):
            self.console.print(f"[dim magenta]檔案不存在：{file_path}[/red]")
            return

        file_type = self.get_file_type(file_path)

        if file_type == 'image':
            self.display_image_info(file_path)
        elif file_type == 'video':
            self.display_video_info(file_path)
        elif file_type == 'audio':
            self.console.print("[magenta]音訊檔案資訊查看功能開發中[/yellow]")
        else:
            self.console.print(f"[magenta]不支援的檔案類型[/yellow]")
            return

        # AI 分析
        if analyze:
            self.analyze_with_ai(file_path, custom_prompt)


def interactive_mode():
    """互動模式"""
    viewer = MediaViewer()

    console.print("\n[bold magenta]🎬 Gemini 媒體檔案查看器[/bold magenta]\n")

    while True:
        console.print("\n" + "=" * 60)
        file_path = console.input("\n[magenta]請輸入檔案路徑（或輸入 'exit' 退出）：[/magenta]\n").strip()

        if not file_path or file_path.lower() in ['exit', 'quit', '退出']:
            console.print("\n[bright_magenta]再見！[/green]")
            break

        if not os.path.isfile(file_path):
            console.print("[dim magenta]檔案不存在[/red]")
            continue

        # 顯示資訊
        viewer.view_file(file_path)

        # 詢問是否進行 AI 分析
        if viewer.ai_analysis_enabled:
            analyze = console.input("\n[magenta]進行 AI 分析？(y/N): [/magenta]").strip().lower()
            if analyze == 'y':
                custom = console.input("[magenta]自訂分析提示（可留空使用預設）：[/magenta]\n").strip()
                viewer.analyze_with_ai(file_path, custom if custom else None)

        # 詢問是否開啟檔案
        open_file = console.input("\n[magenta]開啟檔案？(y/N): [/magenta]").strip().lower()
        if open_file == 'y':
            os.system(f'open "{file_path}"')


def main():
    """主程式"""
    if len(sys.argv) < 2:
        # 互動模式
        interactive_mode()
    else:
        # 命令列模式
        file_path = sys.argv[1]
        analyze = '--analyze' in sys.argv or '-a' in sys.argv

        viewer = MediaViewer()
        viewer.view_file(file_path, analyze=analyze)


if __name__ == "__main__":
    main()
