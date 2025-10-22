#!/usr/bin/env python3
"""
Gemini 圖像分析工具 - 完全使用新 SDK
支援圖像理解、OCR、物體偵測、圖像比較等功能
"""
import os
import sys
import base64
from typing import Optional, List
from PIL import Image
from rich.console import Console
from rich.panel import Panel

# 新 SDK
from google.genai import types

# 共用工具模組
from utils.api_client import get_gemini_client
from utils.pricing_loader import (
    get_pricing_calculator,
    PRICING_ENABLED,
    USD_TO_TWD
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

# 支援的圖片格式
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
DEFAULT_MODEL = 'gemini-2.5-flash'

# 預設提示詞範本
PROMPT_TEMPLATES = {
    'describe': '詳細描述這張圖片的內容，包括主要物體、場景、顏色、氛圍等。',
    'ocr': '提取圖片中所有可見的文字內容，保持原始格式和排版。',
    'objects': '列出圖片中所有可見的物體，並說明它們的位置和特徵。',
    'analyze': '深入分析這張圖片，包括：\n1. 主題和內容\n2. 構圖和視覺元素\n3. 色彩運用\n4. 可能的用途或意義',
    'compare': '比較這些圖片的異同，分析它們的共同點和差異。',
    'caption': '為這張圖片生成一個簡短但有描述性的標題（20字以內）。',
    'translate': '翻譯圖片中的所有文字為中文。',
    'count': '計算並列出圖片中每種物體的數量。',
}

# 支援思考模式的模型
THINKING_MODELS = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-8b']


class ImageAnalyzer:
    """圖像分析器（新 SDK 版本）"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        console.print(f"[green]✓ 已載入模型：{model_name}[/green]")

    def _image_to_part(self, image_path: str) -> types.Part:
        """將圖片轉換為 Part 物件"""
        # 讀取圖片
        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        # 取得 MIME 類型
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }
        mime_type = mime_map.get(ext, 'image/jpeg')

        # 建立 Part
        return types.Part(
            inline_data=types.Blob(
                mime_type=mime_type,
                data=image_bytes
            )
        )

    @with_retry("圖片分析", max_retries=3)
    def analyze_image(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        task: str = 'describe'
    ) -> str:
        """
        分析單張圖片（已包含自動重試）

        Args:
            image_path: 圖片路徑
            prompt: 自訂提示詞
            task: 預設任務類型

        Returns:
            分析結果
        """
        # 檢查檔案
        if not os.path.isfile(image_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                # 此函數通用於所有檔案類型
                alternative_path = suggest_video_file_not_found(image_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    image_path = alternative_path
                    console.print(f"[green]✅ 已切換至：{image_path}[/green]\n")
                else:
                    raise FileNotFoundError(f"找不到圖片，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"找不到圖片：{image_path}")

        # 檢查格式
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in SUPPORTED_FORMATS:
            console.print(f"[yellow]警告：{ext} 可能不受支援[/yellow]")

        # 載入圖片資訊
        try:
            img = Image.open(image_path)
            console.print(f"\n[cyan]📷 圖片資訊：[/cyan]")
            console.print(f"   檔案：{os.path.basename(image_path)}")
            console.print(f"   大小：{img.size[0]} × {img.size[1]}")
            console.print(f"   格式：{img.format}")
        except Exception as e:
            # 🎯 一鍵修復：顯示圖片載入失敗的修復建議
            try:
                from error_fix_suggestions import suggest_image_load_failed
                suggest_image_load_failed(image_path, e)
            except ImportError:
                pass

            raise Exception(f"無法載入圖片：{e}，請參考上述解決方案")

        # 選擇提示詞
        if not prompt:
            prompt = PROMPT_TEMPLATES.get(task, PROMPT_TEMPLATES['describe'])

        console.print(f"\n[cyan]💭 任務：{task}[/cyan]")
        console.print(f"[cyan]📝 提示：{prompt[:50]}...[/cyan]" if len(prompt) > 50 else f"[cyan]📝 提示：{prompt}[/cyan]")

        # 分析圖片
        console.print(f"\n[cyan]🤖 Gemini 分析中...[/cyan]\n")

        try:
            # 轉換圖片為 Part
            image_part = self._image_to_part(image_path)

            # 檢查是否支援思考模式
            supports_thinking = any(tm in self.model_name for tm in THINKING_MODELS)

            # 配置
            config = types.GenerateContentConfig()
            if supports_thinking:
                config.thinking_config = types.ThinkingConfig(thinking_budget=-1)

            # 發送請求
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, image_part],
                config=config
            )

            # 顯示結果
            console.print("[cyan]Gemini：[/cyan]")
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
            if PRICING_ENABLED and input_tokens > 0:
                try:
                    cost, details = global_pricing_calculator.calculate_text_cost(
                        self.model_name,
                        input_tokens,
                        output_tokens,
                        thinking_tokens
                    )
                    if thinking_tokens > 0:
                        console.print(f"[dim]💰 本次成本: NT${cost * USD_TO_TWD:.2f} (圖片+提示: {input_tokens:,} tokens, 思考: {thinking_tokens:,} tokens, 回應: {output_tokens:,} tokens) | 累計: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f} (${global_pricing_calculator.total_cost:.6f})[/dim]")
                    else:
                        console.print(f"[dim]💰 本次成本: NT${cost * USD_TO_TWD:.2f} (圖片+提示: {input_tokens:,} tokens, 回應: {output_tokens:,} tokens) | 累計: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f} (${global_pricing_calculator.total_cost:.6f})[/dim]")
                except Exception as e:
                    pass

            return response.text

        except Exception as e:
            console.print(f"[red]✗ 分析失敗：{e}[/red]")
            raise

    def analyze_multiple_images(
        self,
        image_paths: List[str],
        prompt: Optional[str] = None,
        task: str = 'compare'
    ) -> str:
        """分析多張圖片"""
        # 載入所有圖片
        console.print(f"\n[cyan]📷 載入 {len(image_paths)} 張圖片：[/cyan]")

        parts = []
        for i, path in enumerate(image_paths, 1):
            try:
                img = Image.open(path)
                console.print(f"   {i}. {os.path.basename(path)} ({img.size[0]}×{img.size[1]})")
                parts.append(self._image_to_part(path))
            except Exception as e:
                console.print(f"   [red]✗ {os.path.basename(path)} - 載入失敗：{e}[/red]")

        if not parts:
            # 🎯 一鍵修復：顯示無圖片載入修復建議
            try:
                from error_fix_suggestions import suggest_no_images_loaded
                suggest_no_images_loaded(len(image_paths), image_paths)
            except ImportError:
                # 如果沒有修復建議模組，使用基本錯誤訊息
                pass

            raise ValueError("沒有成功載入任何圖片")

        # 選擇提示詞
        if not prompt:
            prompt = PROMPT_TEMPLATES.get(task, PROMPT_TEMPLATES['compare'])

        console.print(f"\n[cyan]💭 任務：{task}[/cyan]")

        # 分析
        console.print(f"\n[cyan]🤖 Gemini 分析中...[/cyan]\n")

        try:
            # 配置
            supports_thinking = any(tm in self.model_name for tm in THINKING_MODELS)
            config = types.GenerateContentConfig()
            if supports_thinking:
                config.thinking_config = types.ThinkingConfig(thinking_budget=-1)

            # 構建內容：提示詞 + 所有圖片
            contents = [prompt] + parts

            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            console.print("[cyan]Gemini：[/cyan]")
            console.print(response.text)
            console.print("\n")

            return response.text

        except Exception as e:
            console.print(f"[red]✗ 分析失敗：{e}[/red]")
            raise

    def batch_analyze(
        self,
        image_paths: List[str],
        task: str = 'describe'
    ) -> List[dict]:
        """批次分析多張圖片"""
        results = []

        console.print(f"\n[bold cyan]📦 批次分析 {len(image_paths)} 張圖片[/bold cyan]")

        for i, path in enumerate(image_paths, 1):
            console.print(f"\n[cyan]━━━ 圖片 {i}/{len(image_paths)} ━━━[/cyan]")

            try:
                result_text = self.analyze_image(path, task=task)
                results.append({
                    'path': path,
                    'filename': os.path.basename(path),
                    'task': task,
                    'result': result_text,
                    'success': True
                })
            except Exception as e:
                console.print(f"[red]✗ 分析失敗：{e}[/red]")
                results.append({
                    'path': path,
                    'filename': os.path.basename(path),
                    'task': task,
                    'error': str(e),
                    'success': False
                })

        # 統計
        success_count = sum(1 for r in results if r['success'])
        console.print(f"\n[green]✓ 批次分析完成：{success_count}/{len(image_paths)} 成功[/green]")

        return results


def show_examples():
    """顯示使用範例"""
    console.print(Panel.fit(
        """[bold cyan]Gemini 圖像分析工具 - 使用範例[/bold cyan]

[yellow]1. 基本圖片描述[/yellow]
   python3 gemini_image_analyzer.py describe image.jpg

[yellow]2. OCR 文字提取[/yellow]
   python3 gemini_image_analyzer.py ocr document.png

[yellow]3. 物體偵測[/yellow]
   python3 gemini_image_analyzer.py objects photo.jpg

[yellow]4. 圖片比較[/yellow]
   python3 gemini_image_analyzer.py compare image1.jpg image2.jpg

[yellow]5. 批次分析[/yellow]
   python3 gemini_image_analyzer.py batch *.jpg
        """,
        border_style="cyan"
    ))


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='Gemini 圖像分析工具（新 SDK）')
    parser.add_argument('task', nargs='?', help='任務類型或 "examples" 顯示範例')
    parser.add_argument('images', nargs='*', help='圖片路徑')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='模型名稱')
    parser.add_argument('--prompt', help='自訂提示詞')

    args = parser.parse_args()

    # 顯示範例
    if args.task == 'examples' or not args.task:
        show_examples()
        sys.exit(0)

    # 檢查圖片
    if not args.images:
        console.print("[red]錯誤：請提供圖片路徑[/red]")
        show_examples()
        sys.exit(1)

    # 初始化分析器
    analyzer = ImageAnalyzer(model_name=args.model)

    try:
        # 比較模式（多張圖片）
        if args.task == 'compare' and len(args.images) > 1:
            analyzer.analyze_multiple_images(args.images, task='compare')

        # 批次模式
        elif args.task == 'batch':
            analyzer.batch_analyze(args.images, task='describe')

        # 自訂提示
        elif args.prompt:
            analyzer.analyze_image(args.images[0], prompt=args.prompt)

        # 單張圖片分析
        else:
            analyzer.analyze_image(args.images[0], task=args.task)

    except Exception as e:
        console.print(f"[red]✗ 執行失敗：{e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
