#!/usr/bin/env python3
"""
Gemini 影片分析工具 - 完全使用新 SDK
支援影片上傳、分析、對話理解
"""
import os
import sys
import time
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# 新 SDK
from google.genai import types

# 共用工具模組
from utils import (
    get_gemini_client,
    get_pricing_calculator,
    PRICING_ENABLED,
    USD_TO_TWD,
    supports_thinking,
    create_generation_config,
    THINKING_MODELS
)

# 導入 API 重試機制
try:
    from api_retry_wrapper import with_retry
    API_RETRY_ENABLED = True
except ImportError:
    # 如果未安裝，提供空裝飾器
    def with_retry(operation_name: str, max_retries: int = 3):
        def decorator(func):
            return func
        return decorator
    API_RETRY_ENABLED = False

# 初始化 API 客戶端
client = get_gemini_client()

# 初始化計價器
global_pricing_calculator = get_pricing_calculator(silent=True)

# Console
console = Console()

# 支援的影片格式
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mpeg', '.mov', '.avi', '.flv', '.mpg', '.webm', '.wmv', '.3gpp']

# 預設模型
DEFAULT_MODEL = 'gemini-2.5-pro'


class VideoAnalyzer:
    """影片分析器（新 SDK 版本）"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        console.print(f"[green]✓ 已載入模型：{model_name}[/green]")

    def upload_video(self, video_path: str, display_name: Optional[str] = None) -> types.File:
        """
        上傳影片到 Gemini API

        Args:
            video_path: 影片檔案路徑
            display_name: 顯示名稱（可選）

        Returns:
            上傳的檔案物件
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_file_not_found
                alternative_path = suggest_file_not_found(video_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    video_path = alternative_path
                    console.print(f"[green]✅ 已切換至：{video_path}[/green]\n")
                else:
                    raise FileNotFoundError(f"找不到影片檔案，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"找不到影片檔案: {video_path}")

        # 檢查檔案格式
        file_ext = os.path.splitext(video_path)[1].lower()
        if file_ext not in SUPPORTED_VIDEO_FORMATS:
            console.print(f"[yellow]警告：{file_ext} 可能不受支援[/yellow]")
            console.print(f"支援的格式: {', '.join(SUPPORTED_VIDEO_FORMATS)}")

        # 設定顯示名稱
        if not display_name:
            display_name = os.path.basename(video_path)

        # 檢查檔案大小
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024 * 1024)

        console.print(f"\n[cyan]📹 影片資訊：[/cyan]")
        console.print(f"   檔案名稱：{os.path.basename(video_path)}")
        console.print(f"   檔案大小：{file_size_mb:.2f} MB")
        console.print(f"   格式：{file_ext}")

        # 檢查是否已上傳（新 SDK）
        console.print("\n[cyan]🔍 檢查是否已上傳...[/cyan]")
        try:
            for existing_file in client.files.list():
                if existing_file.display_name == display_name:
                    console.print(f"[green]✓ 檔案已存在：{existing_file.name}[/green]")
                    # 檢查狀態
                    if existing_file.state.name == "ACTIVE":
                        console.print("[green]✓ 影片已就緒，可以開始分析[/green]")
                        return existing_file
                    elif existing_file.state.name == "PROCESSING":
                        console.print("[yellow]⏳ 檔案正在處理中，等待完成...[/yellow]")
                        return self._wait_for_processing(existing_file)
        except Exception as e:
            console.print(f"[yellow]檢查已上傳檔案時發生錯誤：{e}[/yellow]")

        # 上傳檔案（新 SDK）
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"上傳中... ({file_size_mb:.2f} MB)", total=None)

            try:
                # 新 SDK 上傳方式
                video_file = client.files.upload(
                    path=video_path,
                    config=types.UploadFileConfig(
                        display_name=display_name
                    )
                )
                progress.update(task, description="[green]✓ 上傳完成[/green]")
            except Exception as e:
                progress.update(task, description="[red]✗ 上傳失敗[/red]")

                # 顯示詳細的錯誤修復建議
                try:
                    from error_fix_suggestions import suggest_video_upload_failed
                    suggest_video_upload_failed(video_path, str(e))
                except ImportError:
                    pass

                raise Exception(f"上傳失敗：{e}，請參考上述解決方案")

        console.print(f"[green]✓ 檔案名稱：{video_file.name}[/green]")

        # 等待處理完成
        video_file = self._wait_for_processing(video_file)

        return video_file

    def _wait_for_processing(self, video_file: types.File) -> types.File:
        """等待影片處理完成"""
        console.print("\n[cyan]⏳ 等待影片處理...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("處理中...", total=None)

            while video_file.state.name == "PROCESSING":
                time.sleep(5)
                # 新 SDK 獲取檔案狀態
                video_file = client.files.get(name=video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"影片處理失敗：{video_file.state.name}")

            progress.update(task, description="[green]✓ 處理完成[/green]")

        console.print(f"[green]✓ 影片已就緒，可以開始分析[/green]")
        return video_file

    @with_retry("影片分析", max_retries=3)
    def analyze_video(
        self,
        video_file: types.File,
        prompt: str,
        show_cost: bool = True
    ) -> str:
        """
        分析影片內容（已包含自動重試）

        Args:
            video_file: 上傳的影片檔案
            prompt: 分析提示
            show_cost: 是否顯示成本

        Returns:
            分析結果文字
        """
        console.print(f"\n[cyan]🤖 使用模型：{self.model_name}[/cyan]")
        console.print(f"[cyan]💭 提示：{prompt}[/cyan]\n")

        # 使用工具建立配置（自動判斷思考模式）
        config = create_generation_config(self.model_name, thinking_budget=-1)

        console.print("[cyan]Gemini：[/cyan]")

        try:
            # 使用新 SDK 發送請求
            response = client.models.generate_content(
                model=self.model_name,
                contents=[video_file, prompt],
                config=config
            )

            # 顯示回應
            console.print(response.text)
            console.print("\n")

            # 提取 tokens
            thinking_tokens = 0
            input_tokens = 0
            output_tokens = 0

            if hasattr(response, 'usage_metadata'):
                thinking_tokens = getattr(response.usage_metadata, 'thinking_tokens', 0)
                input_tokens = getattr(response.usage_metadata, 'prompt_tokens', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_tokens', 0)

            # 顯示成本（新台幣）
            if PRICING_ENABLED and show_cost and input_tokens > 0:
                try:
                    cost, details = global_pricing_calculator.calculate_text_cost(
                        self.model_name,
                        input_tokens,
                        output_tokens,
                        thinking_tokens
                    )
                    if thinking_tokens > 0:
                        console.print(f"[dim]💰 本次成本: NT${cost * USD_TO_TWD:.2f} (影片+提示: {input_tokens:,} tokens, 思考: {thinking_tokens:,} tokens, 回應: {output_tokens:,} tokens) | 累計: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f} (${global_pricing_calculator.total_cost:.6f})[/dim]")
                    else:
                        console.print(f"[dim]💰 本次成本: NT${cost * USD_TO_TWD:.2f} (影片+提示: {input_tokens:,} tokens, 回應: {output_tokens:,} tokens) | 累計: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f} (${global_pricing_calculator.total_cost:.6f})[/dim]")
                except Exception as e:
                    pass

            return response.text

        except Exception as e:
            console.print(f"[red]✗ 分析失敗：{e}[/red]")
            raise

    def interactive_video_chat(self, video_file: types.File):
        """
        與影片進行互動式對話

        Args:
            video_file: 上傳的影片檔案
        """
        console.print("\n" + "=" * 60)
        console.print(f"[bold cyan]影片互動式對話（模型：{self.model_name}）[/bold cyan]")
        console.print("=" * 60)
        console.print("\n[yellow]提示：[/yellow]")
        console.print("  - 輸入 'exit' 或 'quit' 退出")
        console.print("  - 輸入 'info' 顯示影片資訊")
        console.print("  - 直接輸入問題開始分析")
        console.print("-" * 60 + "\n")

        # 檢查是否支援思考模式
        supports_thinking = any(tm in self.model_name for tm in THINKING_MODELS)

        while True:
            try:
                user_input = input("你: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit', '退出']:
                    console.print("\n[green]再見！[/green]")
                    break

                if user_input.lower() == 'info':
                    console.print(f"\n[cyan]影片資訊：[/cyan]")
                    console.print(f"  名稱：{video_file.display_name}")
                    console.print(f"  檔案名稱：{video_file.name}")
                    console.print(f"  狀態：{video_file.state.name}")
                    console.print(f"  建立時間：{video_file.create_time}")
                    console.print(f"  過期時間：{video_file.expiration_time}\n")
                    continue

                # 配置
                config = types.GenerateContentConfig()
                if supports_thinking:
                    config.thinking_config = types.ThinkingConfig(thinking_budget=-1)

                # 發送消息（包含影片）
                console.print("\n[cyan]Gemini：[/cyan]")

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=[video_file, user_input],
                    config=config
                )

                console.print(response.text)
                console.print("\n")

                # 顯示成本
                if PRICING_ENABLED and hasattr(response, 'usage_metadata'):
                    thinking_tokens = getattr(response.usage_metadata, 'thinking_tokens', 0)
                    input_tokens = getattr(response.usage_metadata, 'prompt_tokens', 0)
                    output_tokens = getattr(response.usage_metadata, 'candidates_tokens', 0)

                    if input_tokens > 0:
                        try:
                            cost, _ = global_pricing_calculator.calculate_text_cost(
                                self.model_name,
                                input_tokens,
                                output_tokens,
                                thinking_tokens
                            )
                            if thinking_tokens > 0:
                                console.print(f"[dim]💰 本次成本: NT${cost * USD_TO_TWD:.2f} (影片+提示: {input_tokens:,}, 思考: {thinking_tokens:,}, 回應: {output_tokens:,}) | 累計: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f}[/dim]\n")
                            else:
                                console.print(f"[dim]💰 本次成本: NT${cost * USD_TO_TWD:.2f} (影片+提示: {input_tokens:,}, 回應: {output_tokens:,}) | 累計: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f}[/dim]\n")
                        except (AttributeError, KeyError, TypeError) as e:
                            logger.warning(f"計價顯示失敗 (模型: {self.model_name}, tokens: {input_tokens}): {e}")

            except KeyboardInterrupt:
                console.print("\n\n[green]再見！[/green]")
                break
            except Exception as e:
                console.print(f"\n[red]錯誤：{e}[/red]\n")

    def list_uploaded_videos(self):
        """列出所有已上傳的影片檔案"""
        console.print("\n[cyan]📁 已上傳的檔案：[/cyan]\n")

        try:
            video_files = []
            for f in client.files.list():
                # 檢查是否為影片格式
                if f.display_name and any(ext in f.display_name.lower() for ext in SUPPORTED_VIDEO_FORMATS):
                    video_files.append(f)

            if not video_files:
                console.print("[yellow]沒有找到已上傳的影片檔案[/yellow]")
                return

            for i, f in enumerate(video_files, 1):
                console.print(f"{i}. [green]{f.display_name}[/green]")
                console.print(f"   名稱: {f.name}")
                console.print(f"   狀態: {f.state.name}")
                console.print(f"   建立時間: {f.create_time}")
                console.print()

        except Exception as e:
            console.print(f"[red]✗ 列出檔案失敗：{e}[/red]")


def show_usage():
    """顯示使用方式"""
    console.print(Panel.fit(
        """[bold cyan]Gemini 影片分析工具 - 使用方式[/bold cyan]

[yellow]1. 互動式分析（推薦）[/yellow]
   python3 gemini_video_analyzer.py video.mp4

[yellow]2. 單次分析[/yellow]
   python3 gemini_video_analyzer.py video.mp4 "描述這個影片的內容"

[yellow]3. 列出已上傳的影片[/yellow]
   python3 gemini_video_analyzer.py --list

[yellow]4. 指定模型[/yellow]
   python3 gemini_video_analyzer.py --model gemini-2.5-flash video.mp4
        """,
        border_style="cyan"
    ))


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='Gemini 影片分析工具（新 SDK）')
    parser.add_argument('video_path', nargs='?', help='影片檔案路徑')
    parser.add_argument('prompt', nargs='*', help='分析提示（可選，不提供則進入互動模式）')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='模型名稱')
    parser.add_argument('--list', action='store_true', help='列出已上傳的影片')

    args = parser.parse_args()

    # 列出已上傳的檔案
    if args.list:
        analyzer = VideoAnalyzer(model_name=args.model)
        analyzer.list_uploaded_videos()
        sys.exit(0)

    # 顯示使用方式
    if not args.video_path:
        show_usage()
        sys.exit(0)

    # 初始化分析器
    analyzer = VideoAnalyzer(model_name=args.model)

    try:
        # 上傳影片
        video_file = analyzer.upload_video(args.video_path)

        # 如果有提供問題，直接分析
        if args.prompt:
            prompt = " ".join(args.prompt)
            analyzer.analyze_video(video_file, prompt)
        else:
            # 進入互動模式
            analyzer.interactive_video_chat(video_file)

    except Exception as e:
        console.print(f"\n[red]錯誤：{e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
