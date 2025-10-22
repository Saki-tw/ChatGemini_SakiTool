#!/usr/bin/env python3
"""
Gemini Imagen 圖片生成工具
使用 Imagen 3 從文字生成高品質圖片
"""
import os
import sys
from typing import Optional, List
from google.genai import types
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

# 共用工具模組
from utils.api_client import get_gemini_client
from utils.pricing_loader import (
    get_pricing_calculator,
    PRICING_ENABLED,
    USD_TO_TWD
)

console = Console()

# 初始化 API 客戶端
client = get_gemini_client()

# 初始化計價器
global_pricing_calculator = get_pricing_calculator(silent=True)

# 支援的模型
MODELS = {
    '1': ('imagen-3.0-generate-001', 'Imagen 3 - 最高品質'),
    '2': ('imagen-3.0-fast-generate-001', 'Imagen 3 Fast - 快速生成'),
}

DEFAULT_MODEL = 'imagen-3.0-generate-001'
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "gemini_images")


def select_model() -> str:
    """選擇 Imagen 模型"""
    console.print("\n[cyan]請選擇 Imagen 模型：[/cyan]")
    for key, (model_name, description) in MODELS.items():
        console.print(f"  {key}. {description}")

    choice = console.input("\n請選擇 (1-2, 預設=1): ").strip() or '1'

    if choice in MODELS:
        return MODELS[choice][0]
    else:
        console.print("[yellow]無效選擇，使用預設模型[/yellow]")
        return DEFAULT_MODEL


def generate_image(
    prompt: str,
    model: str = DEFAULT_MODEL,
    negative_prompt: Optional[str] = None,
    number_of_images: int = 1,
    aspect_ratio: str = "1:1",
    safety_filter_level: str = "block_some",
    person_generation: str = "allow_all",
    show_cost: bool = True
) -> List[str]:
    """
    生成圖片

    Args:
        prompt: 圖片描述提示
        model: 使用的模型
        negative_prompt: 負面提示（避免的內容）
        number_of_images: 生成圖片數量（1-8）
        aspect_ratio: 長寬比 (1:1, 16:9, 9:16, 3:4, 4:3)
        safety_filter_level: 安全過濾級別
        person_generation: 人物生成控制
        show_cost: 是否顯示成本資訊

    Returns:
        生成的圖片檔案路徑列表
    """
    console.print("\n[cyan]" + "=" * 60 + "[/cyan]")
    console.print(f"[bold cyan]🎨 Imagen 圖片生成[/bold cyan]")
    console.print("[cyan]" + "=" * 60 + "[/cyan]\n")

    console.print(f"[cyan]模型：[/cyan] {model}")
    console.print(f"[cyan]提示：[/cyan] {prompt}")
    if negative_prompt:
        console.print(f"[cyan]負面提示：[/cyan] {negative_prompt}")
    console.print(f"[cyan]長寬比：[/cyan] {aspect_ratio}")
    console.print(f"[cyan]數量：[/cyan] {number_of_images}")

    # 計價預估（如果啟用）
    pricing_calc = None
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=number_of_images,
            operation='generate'
        )
        console.print(f"\n[yellow]💰 費用預估：[/yellow]")
        console.print(f"  NT${cost * USD_TO_TWD:.2f} (${cost:.4f} USD)")
        console.print(f"  單價：NT${details['per_image_rate'] * USD_TO_TWD:.2f}/張 (${details['per_image_rate']:.2f} USD/張)")
        console.print()

    # 準備配置
    config_params = {
        "number_of_images": number_of_images,
        "aspect_ratio": aspect_ratio,
        "safety_filter_level": safety_filter_level,
        "person_generation": person_generation,
    }

    if negative_prompt:
        config_params["negative_prompt"] = negative_prompt

    config = types.GenerateImagesConfig(**config_params)

    # 開始生成
    console.print("\n[cyan]⏳ 開始生成圖片...[/cyan]\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("生成中...", total=None)

            # 生成圖片
            response = client.models.generate_images(
                model=model,
                prompt=prompt,
                config=config
            )

            progress.update(task, description="[green]✓ 生成完成[/green]")

        # 確保輸出目錄存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 保存圖片
        console.print(f"\n[cyan]💾 保存圖片中...[/cyan]")

        output_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i, generated_image in enumerate(response.generated_images):
            output_filename = f"imagen_{timestamp}_{i+1}.png"
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            # 下載圖片
            image_data = client.files.download(file=generated_image.image)
            with open(output_path, 'wb') as f:
                f.write(image_data)

            output_paths.append(output_path)
            console.print(f"  [{i+1}] {output_path}")

        # 顯示圖片資訊
        console.print(f"\n[cyan]📊 圖片資訊：[/cyan]")
        console.print(f"  生成數量：{len(output_paths)}")
        console.print(f"  儲存目錄：{OUTPUT_DIR}")

        # 計算總檔案大小
        total_size = sum(os.path.getsize(p) for p in output_paths) / (1024 * 1024)
        console.print(f"  總大小：{total_size:.2f} MB")

        # 顯示實際成本
        if pricing_calc:
            console.print(f"\n[yellow]💰 實際費用：[/yellow]")
            actual_cost = details['per_image_rate'] * len(output_paths)
            console.print(f"  NT${actual_cost * USD_TO_TWD:.2f} (${actual_cost:.4f} USD)")

        return output_paths

    except Exception as e:
        console.print(f"\n[red]❌ 生成失敗：{e}[/red]")
        raise


def edit_image(
    image_path: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    show_cost: bool = True
) -> str:
    """
    編輯圖片

    Args:
        image_path: 原始圖片路徑
        prompt: 編輯描述
        model: 使用的模型
        show_cost: 是否顯示成本資訊

    Returns:
        編輯後的圖片路徑
    """
    console.print("\n[cyan]" + "=" * 60 + "[/cyan]")
    console.print(f"[bold cyan]✏️ Imagen 圖片編輯[/bold cyan]")
    console.print("[cyan]" + "=" * 60 + "[/cyan]\n")

    if not os.path.isfile(image_path):
        # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
        try:
            from error_fix_suggestions import suggest_file_not_found
            alternative_path = suggest_file_not_found(image_path, auto_fix=True)

            if alternative_path and os.path.isfile(alternative_path):
                # 用戶選擇了替代檔案，使用新路徑
                image_path = alternative_path
                console.print(f"[green]✅ 已切換至：{image_path}[/green]\n")
            else:
                raise FileNotFoundError(f"找不到檔案，請參考上述建議")
        except ImportError:
            # 如果沒有修復建議模組，直接拋出錯誤
            raise FileNotFoundError(f"圖片檔案不存在: {image_path}")

    console.print(f"[cyan]原始圖片：[/cyan] {image_path}")
    console.print(f"[cyan]編輯提示：[/cyan] {prompt}")

    # 上傳圖片
    console.print(f"\n[cyan]📤 上傳圖片...[/cyan]")
    uploaded_image = client.files.upload(file=image_path)

    # 計價預估
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=1,
            operation='edit'
        )
        console.print(f"\n[yellow]💰 費用預估：[/yellow]")
        console.print(f"  NT${cost * USD_TO_TWD:.2f} (${cost:.4f} USD)")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("編輯中...", total=None)

            # 編輯圖片
            response = client.models.edit_image(
                model=model,
                prompt=prompt,
                image=uploaded_image,
            )

            progress.update(task, description="[green]✓ 編輯完成[/green]")

        # 保存編輯後的圖片
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"imagen_edit_{timestamp}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        image_data = client.files.download(file=response.generated_image.image)
        with open(output_path, 'wb') as f:
            f.write(image_data)

        console.print(f"\n[green]✓ 圖片已儲存：{output_path}[/green]")

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        console.print(f"\n[cyan]📊 圖片資訊：[/cyan]")
        console.print(f"  檔案大小：{file_size:.2f} MB")

        return output_path

    except Exception as e:
        console.print(f"\n[red]❌ 編輯失敗：{e}[/red]")
        raise


def upscale_image(
    image_path: str,
    model: str = "imagen-3.0-capability-upscale-001",
    show_cost: bool = True
) -> str:
    """
    放大圖片

    Args:
        image_path: 原始圖片路徑
        model: 使用的模型
        show_cost: 是否顯示成本資訊

    Returns:
        放大後的圖片路徑
    """
    console.print("\n[cyan]" + "=" * 60 + "[/cyan]")
    console.print(f"[bold cyan]🔍 Imagen 圖片放大[/bold cyan]")
    console.print("[cyan]" + "=" * 60 + "[/cyan]\n")

    if not os.path.isfile(image_path):
        # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
        try:
            from error_fix_suggestions import suggest_file_not_found
            alternative_path = suggest_file_not_found(image_path, auto_fix=True)

            if alternative_path and os.path.isfile(alternative_path):
                # 用戶選擇了替代檔案，使用新路徑
                image_path = alternative_path
                console.print(f"[green]✅ 已切換至：{image_path}[/green]\n")
            else:
                raise FileNotFoundError(f"找不到檔案，請參考上述建議")
        except ImportError:
            # 如果沒有修復建議模組，直接拋出錯誤
            raise FileNotFoundError(f"圖片檔案不存在: {image_path}")

    console.print(f"[cyan]原始圖片：[/cyan] {image_path}")

    # 上傳圖片
    console.print(f"\n[cyan]📤 上傳圖片...[/cyan]")
    uploaded_image = client.files.upload(file=image_path)

    # 計價預估
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=1,
            operation='upscale'
        )
        console.print(f"\n[yellow]💰 費用預估：[/yellow]")
        console.print(f"  NT${cost * USD_TO_TWD:.2f} (${cost:.4f} USD)")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("放大中...", total=None)

            # 放大圖片
            response = client.models.upscale_image(
                model=model,
                image=uploaded_image,
            )

            progress.update(task, description="[green]✓ 放大完成[/green]")

        # 保存放大後的圖片
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"imagen_upscale_{timestamp}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        image_data = client.files.download(file=response.generated_image.image)
        with open(output_path, 'wb') as f:
            f.write(image_data)

        console.print(f"\n[green]✓ 圖片已儲存：{output_path}[/green]")

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        console.print(f"\n[cyan]📊 圖片資訊：[/cyan]")
        console.print(f"  檔案大小：{file_size:.2f} MB")

        return output_path

    except Exception as e:
        console.print(f"\n[red]❌ 放大失敗：{e}[/red]")
        raise


def interactive_mode():
    """互動式圖片生成模式"""
    console.print("\n[bold cyan]🎨 Imagen 互動式圖片生成[/bold cyan]\n")

    # 選擇模型
    model = select_model()

    while True:
        console.print("\n" + "=" * 60)
        console.print("\n[cyan]功能選擇：[/cyan]")
        console.print("  [1] 生成圖片（Text-to-Image）")
        console.print("  [2] 編輯圖片（Image Editing）")
        console.print("  [3] 放大圖片（Upscaling）")
        console.print("  [0] 退出\n")

        choice = console.input("請選擇: ").strip()

        if choice == '0':
            console.print("\n[green]再見！[/green]")
            break

        elif choice == '1':
            # 生成圖片
            prompt = console.input("\n[cyan]請描述您想生成的圖片（或輸入 'back' 返回）：[/cyan]\n").strip()

            if not prompt or prompt.lower() == 'back':
                continue

            # 負面提示
            negative_prompt = console.input("\n[cyan]負面提示（避免的內容，可留空）：[/cyan]\n").strip()
            if not negative_prompt:
                negative_prompt = None

            # 長寬比
            console.print("\n[cyan]選擇長寬比：[/cyan]")
            console.print("  1. 1:1 (正方形，預設)")
            console.print("  2. 16:9 (橫向)")
            console.print("  3. 9:16 (直向)")
            console.print("  4. 3:4")
            console.print("  5. 4:3")
            aspect_choice = console.input("\n請選擇 (1-5, 預設=1): ").strip() or '1'

            aspect_ratios = {'1': '1:1', '2': '16:9', '3': '9:16', '4': '3:4', '5': '4:3'}
            aspect_ratio = aspect_ratios.get(aspect_choice, '1:1')

            # 生成數量
            num_input = console.input("\n[cyan]生成數量（1-8，預設=1）：[/cyan] ").strip()
            number_of_images = int(num_input) if num_input.isdigit() and 1 <= int(num_input) <= 8 else 1

            try:
                output_paths = generate_image(
                    prompt=prompt,
                    model=model,
                    negative_prompt=negative_prompt,
                    number_of_images=number_of_images,
                    aspect_ratio=aspect_ratio
                )

                # 詢問是否開啟圖片
                open_img = console.input("\n[cyan]要開啟圖片嗎？(y/N): [/cyan]").strip().lower()
                if open_img == 'y' and output_paths:
                    for path in output_paths:
                        os.system(f'open "{path}"')

            except Exception as e:
                console.print(f"\n[red]錯誤：{e}[/red]")

        elif choice == '2':
            # 編輯圖片
            image_path = console.input("\n[cyan]圖片路徑（或輸入 'back' 返回）：[/cyan]\n").strip()

            if not image_path or image_path.lower() == 'back':
                continue

            if not os.path.isfile(image_path):
                console.print("[yellow]檔案不存在[/yellow]")
                continue

            prompt = console.input("\n[cyan]請描述如何編輯此圖片：[/cyan]\n").strip()

            if not prompt:
                console.print("[yellow]未輸入編輯描述[/yellow]")
                continue

            try:
                output_path = edit_image(
                    image_path=image_path,
                    prompt=prompt,
                    model=model
                )

                open_img = console.input("\n[cyan]要開啟圖片嗎？(y/N): [/cyan]").strip().lower()
                if open_img == 'y':
                    os.system(f'open "{output_path}"')

            except Exception as e:
                console.print(f"\n[red]錯誤：{e}[/red]")

        elif choice == '3':
            # 放大圖片
            image_path = console.input("\n[cyan]圖片路徑（或輸入 'back' 返回）：[/cyan]\n").strip()

            if not image_path or image_path.lower() == 'back':
                continue

            if not os.path.isfile(image_path):
                console.print("[yellow]檔案不存在[/yellow]")
                continue

            try:
                output_path = upscale_image(
                    image_path=image_path
                )

                open_img = console.input("\n[cyan]要開啟圖片嗎？(y/N): [/cyan]").strip().lower()
                if open_img == 'y':
                    os.system(f'open "{output_path}"')

            except Exception as e:
                console.print(f"\n[red]錯誤：{e}[/red]")

        else:
            console.print("\n[yellow]無效選項[/yellow]")


def main():
    """主程式"""
    console.print("[bold cyan]Gemini Imagen 3 圖片生成工具[/bold cyan]\n")

    # 檢查命令行參數
    if len(sys.argv) < 2:
        # 沒有參數，進入互動模式
        interactive_mode()
    else:
        # 命令行模式
        prompt = " ".join(sys.argv[1:])

        # 選擇模型
        model = select_model()

        try:
            output_paths = generate_image(prompt=prompt, model=model)

            # 自動開啟圖片
            console.print("\n[cyan]🖼️ 開啟圖片中...[/cyan]")
            for path in output_paths:
                os.system(f'open "{path}"')

        except Exception as e:
            console.print(f"\n[red]錯誤：{e}[/red]")
            sys.exit(1)


if __name__ == "__main__":
    main()
