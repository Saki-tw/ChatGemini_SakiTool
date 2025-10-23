#!/usr/bin/env python3
"""
Gemini Imagen 圖片生成工具
使用 Imagen 3 從文字生成高品質圖片
"""
import os
import sys
from typing import Optional, List, Dict, Tuple
from google.genai import types
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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
# 使用統一輸出目錄配置
from utils.path_manager import get_image_dir
OUTPUT_DIR = str(get_image_dir('imagen'))


def select_model() -> str:
    """選擇 Imagen 模型"""
    console.print("\n[magenta]請選擇 Imagen 模型：[/magenta]")
    for key, (model_name, description) in MODELS.items():
        console.print(f"  {key}. {description}")

    choice = console.input("\n請選擇 (1-2, 預設=1): ").strip() or '1'

    if choice in MODELS:
        return MODELS[choice][0]
    else:
        console.print("[magenta]無效選擇，使用預設模型[/yellow]")
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
    console.print("\n[magenta]" + "=" * 60 + "[/magenta]")
    console.print(f"[bold magenta]🎨 Imagen 圖片生成[/bold magenta]")
    console.print("[magenta]" + "=" * 60 + "[/magenta]\n")

    console.print(f"[magenta]模型：[/magenta] {model}")
    console.print(f"[magenta]提示：[/magenta] {prompt}")
    if negative_prompt:
        console.print(f"[magenta]負面提示：[/magenta] {negative_prompt}")
    console.print(f"[magenta]長寬比：[/magenta] {aspect_ratio}")
    console.print(f"[magenta]數量：[/magenta] {number_of_images}")

    # 計價預估（如果啟用）
    pricing_calc = None
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=number_of_images,
            operation='generate'
        )
        console.print(f"\n[magenta]💰 費用預估：[/yellow]")
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
    console.print("\n[magenta]⏳ 開始生成圖片...[/magenta]\n")

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

            progress.update(task, description="[bright_magenta]✓ 生成完成[/green]")

        # 確保輸出目錄存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 保存圖片
        console.print(f"\n[magenta]💾 保存圖片中...[/magenta]")

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
        console.print(f"\n[magenta]📊 圖片資訊：[/magenta]")
        console.print(f"  生成數量：{len(output_paths)}")
        console.print(f"  儲存目錄：{OUTPUT_DIR}")

        # 計算總檔案大小
        total_size = sum(os.path.getsize(p) for p in output_paths) / (1024 * 1024)
        console.print(f"  總大小：{total_size:.2f} MB")

        # 顯示實際成本
        if pricing_calc:
            console.print(f"\n[magenta]💰 實際費用：[/yellow]")
            actual_cost = details['per_image_rate'] * len(output_paths)
            console.print(f"  NT${actual_cost * USD_TO_TWD:.2f} (${actual_cost:.4f} USD)")

        return output_paths

    except Exception as e:
        console.print(f"\n[dim magenta]❌ 生成失敗：{e}[/red]")
        raise


def generate_images_batch(
    prompts: List[str],
    model: str = DEFAULT_MODEL,
    negative_prompts: Optional[List[Optional[str]]] = None,
    aspect_ratios: Optional[List[str]] = None,
    max_workers: int = 3,
    show_cost: bool = True
) -> Dict[str, List[str]]:
    """
    並行生成多組圖片（支援不同 prompt）

    Args:
        prompts: 圖片描述提示列表
        model: 使用的模型
        negative_prompts: 負面提示列表（對應每個 prompt）
        aspect_ratios: 長寬比列表（對應每個 prompt）
        max_workers: 並行工作數（預設 3，避免 API rate limit）
        show_cost: 是否顯示成本資訊

    Returns:
        字典 {prompt: [output_paths]}

    Performance:
        - 3 個 prompts，max_workers=3 → 3x 提升
        - 避免 API rate limit（Imagen API 有速率限制）
    """
    console.print("\n[magenta]" + "=" * 60 + "[/magenta]")
    console.print(f"[bold magenta]🎨 Imagen 批次圖片生成（並行處理）[/bold magenta]")
    console.print("[magenta]" + "=" * 60 + "[/magenta]\n")

    console.print(f"[magenta]模型：[/magenta] {model}")
    console.print(f"[magenta]Prompt 數量：[/magenta] {len(prompts)}")
    console.print(f"[magenta]並行數量：[/magenta] {max_workers}")

    # 準備參數列表
    if negative_prompts is None:
        negative_prompts = [None] * len(prompts)
    if aspect_ratios is None:
        aspect_ratios = ["1:1"] * len(prompts)

    # 確保列表長度一致
    assert len(prompts) == len(negative_prompts) == len(aspect_ratios), \
        "prompts, negative_prompts, aspect_ratios 長度必須一致"

    # 計價預估
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        total_images = len(prompts)
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=total_images,
            operation='generate'
        )
        console.print(f"\n[magenta]💰 總費用預估：[/yellow]")
        console.print(f"  NT${cost * USD_TO_TWD:.2f} (${cost:.4f} USD)")
        console.print(f"  單價：NT${details['per_image_rate'] * USD_TO_TWD:.2f}/張\n")

    console.print(f"[magenta]⏳ 開始並行生成 {len(prompts)} 組圖片...[/magenta]\n")

    results: Dict[str, List[str]] = {}

    # 使用 ThreadPoolExecutor 並行處理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任務
        future_to_prompt = {
            executor.submit(
                generate_image,
                prompt=prompts[i],
                model=model,
                negative_prompt=negative_prompts[i],
                number_of_images=1,
                aspect_ratio=aspect_ratios[i],
                show_cost=False  # 批次模式不顯示個別成本
            ): prompts[i]
            for i in range(len(prompts))
        }

        # 使用 Rich Progress 追蹤進度
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[magenta]生成中...",
                total=len(prompts)
            )

            # 收集結果
            for future in as_completed(future_to_prompt):
                prompt = future_to_prompt[future]
                try:
                    output_paths = future.result()
                    results[prompt] = output_paths
                    progress.update(task, advance=1)
                except Exception as e:
                    console.print(f"\n[dim magenta]❌ Prompt '{prompt[:30]}...' 生成失敗：{e}[/red]")
                    results[prompt] = []
                    progress.update(task, advance=1)

    # 顯示總結
    console.print(f"\n[magenta]" + "=" * 60 + "[/magenta]")
    console.print(f"[bold green]✓ 批次生成完成[/bold green]")
    console.print(f"[magenta]" + "=" * 60 + "[/magenta]\n")

    total_images = sum(len(paths) for paths in results.values())
    console.print(f"[magenta]📊 總結：[/magenta]")
    console.print(f"  成功生成：{total_images} 張圖片")
    console.print(f"  失敗數量：{len(prompts) - len([p for p in results.values() if p])}")

    # 顯示實際成本
    if PRICING_ENABLED and show_cost:
        console.print(f"\n[magenta]💰 實際費用：[/yellow]")
        actual_cost = details['per_image_rate'] * total_images
        console.print(f"  NT${actual_cost * USD_TO_TWD:.2f} (${actual_cost:.4f} USD)")

    return results


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
    console.print("\n[magenta]" + "=" * 60 + "[/magenta]")
    console.print(f"[bold magenta]✏️ Imagen 圖片編輯[/bold magenta]")
    console.print("[magenta]" + "=" * 60 + "[/magenta]\n")

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

    console.print(f"[magenta]原始圖片：[/magenta] {image_path}")
    console.print(f"[magenta]編輯提示：[/magenta] {prompt}")

    # 上傳圖片
    console.print(f"\n[magenta]📤 上傳圖片...[/magenta]")
    uploaded_image = client.files.upload(file=image_path)

    # 計價預估
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=1,
            operation='edit'
        )
        console.print(f"\n[magenta]💰 費用預估：[/yellow]")
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

            progress.update(task, description="[bright_magenta]✓ 編輯完成[/green]")

        # 保存編輯後的圖片
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"imagen_edit_{timestamp}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        image_data = client.files.download(file=response.generated_image.image)
        with open(output_path, 'wb') as f:
            f.write(image_data)

        console.print(f"\n[bright_magenta]✓ 圖片已儲存：{output_path}[/green]")

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        console.print(f"\n[magenta]📊 圖片資訊：[/magenta]")
        console.print(f"  檔案大小：{file_size:.2f} MB")

        return output_path

    except Exception as e:
        console.print(f"\n[dim magenta]❌ 編輯失敗：{e}[/red]")
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
    console.print("\n[magenta]" + "=" * 60 + "[/magenta]")
    console.print(f"[bold magenta]🔍 Imagen 圖片放大[/bold magenta]")
    console.print("[magenta]" + "=" * 60 + "[/magenta]\n")

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

    console.print(f"[magenta]原始圖片：[/magenta] {image_path}")

    # 上傳圖片
    console.print(f"\n[magenta]📤 上傳圖片...[/magenta]")
    uploaded_image = client.files.upload(file=image_path)

    # 計價預估
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=1,
            operation='upscale'
        )
        console.print(f"\n[magenta]💰 費用預估：[/yellow]")
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

            progress.update(task, description="[bright_magenta]✓ 放大完成[/green]")

        # 保存放大後的圖片
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"imagen_upscale_{timestamp}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        image_data = client.files.download(file=response.generated_image.image)
        with open(output_path, 'wb') as f:
            f.write(image_data)

        console.print(f"\n[bright_magenta]✓ 圖片已儲存：{output_path}[/green]")

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        console.print(f"\n[magenta]📊 圖片資訊：[/magenta]")
        console.print(f"  檔案大小：{file_size:.2f} MB")

        return output_path

    except Exception as e:
        console.print(f"\n[dim magenta]❌ 放大失敗：{e}[/red]")
        raise


def interactive_mode():
    """互動式圖片生成模式"""
    console.print("\n[bold magenta]🎨 Imagen 互動式圖片生成[/bold magenta]\n")

    # 選擇模型
    model = select_model()

    while True:
        console.print("\n" + "=" * 60)
        console.print("\n[magenta]功能選擇：[/magenta]")
        console.print("  [1] 生成圖片（Text-to-Image）")
        console.print("  [2] 批次生成圖片（Batch Generation - 並行處理）")
        console.print("  [3] 編輯圖片（Image Editing）")
        console.print("  [4] 放大圖片（Upscaling）")
        console.print("  [0] 退出\n")

        choice = console.input("請選擇: ").strip()

        if choice == '0':
            console.print("\n[bright_magenta]再見！[/green]")
            break

        elif choice == '1':
            # 生成圖片
            prompt = console.input("\n[magenta]請描述您想生成的圖片（或輸入 'back' 返回）：[/magenta]\n").strip()

            if not prompt or prompt.lower() == 'back':
                continue

            # 負面提示
            negative_prompt = console.input("\n[magenta]負面提示（避免的內容，可留空）：[/magenta]\n").strip()
            if not negative_prompt:
                negative_prompt = None

            # 長寬比
            console.print("\n[magenta]選擇長寬比：[/magenta]")
            console.print("  1. 1:1 (正方形，預設)")
            console.print("  2. 16:9 (橫向)")
            console.print("  3. 9:16 (直向)")
            console.print("  4. 3:4")
            console.print("  5. 4:3")
            aspect_choice = console.input("\n請選擇 (1-5, 預設=1): ").strip() or '1'

            aspect_ratios = {'1': '1:1', '2': '16:9', '3': '9:16', '4': '3:4', '5': '4:3'}
            aspect_ratio = aspect_ratios.get(aspect_choice, '1:1')

            # 生成數量
            num_input = console.input("\n[magenta]生成數量（1-8，預設=1）：[/magenta] ").strip()
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
                open_img = console.input("\n[magenta]要開啟圖片嗎？(y/N): [/magenta]").strip().lower()
                if open_img == 'y' and output_paths:
                    for path in output_paths:
                        os.system(f'open "{path}"')

            except Exception as e:
                console.print(f"\n[dim magenta]錯誤：{e}[/red]")

        elif choice == '2':
            # 批次生成圖片（並行處理）
            console.print("\n[magenta]批次圖片生成模式（輸入多個 prompt，並行處理）[/magenta]")
            console.print("[magenta]每行一個 prompt，輸入空行結束：[/yellow]\n")

            prompts = []
            while True:
                line = console.input(f"Prompt #{len(prompts)+1} (留空結束): ").strip()
                if not line:
                    break
                prompts.append(line)

            if not prompts:
                console.print("[magenta]未輸入任何 prompt[/yellow]")
                continue

            # 長寬比選擇（全部統一）
            console.print("\n[magenta]選擇長寬比（套用至所有圖片）：[/magenta]")
            console.print("  1. 1:1 (正方形，預設)")
            console.print("  2. 16:9 (橫向)")
            console.print("  3. 9:16 (直向)")
            console.print("  4. 3:4")
            console.print("  5. 4:3")
            aspect_choice = console.input("\n請選擇 (1-5, 預設=1): ").strip() or '1'

            aspect_ratios_map = {'1': '1:1', '2': '16:9', '3': '9:16', '4': '3:4', '5': '4:3'}
            aspect_ratio = aspect_ratios_map.get(aspect_choice, '1:1')

            # 並行數量
            max_workers_input = console.input("\n[magenta]並行數量（1-5，預設=3）：[/magenta] ").strip()
            max_workers = int(max_workers_input) if max_workers_input.isdigit() and 1 <= int(max_workers_input) <= 5 else 3

            try:
                results = generate_images_batch(
                    prompts=prompts,
                    model=model,
                    aspect_ratios=[aspect_ratio] * len(prompts),
                    max_workers=max_workers
                )

                # 顯示結果摘要
                console.print("\n[magenta]📋 生成結果摘要：[/magenta]")
                for i, (prompt, paths) in enumerate(results.items(), 1):
                    if paths:
                        console.print(f"  [{i}] {prompt[:50]}... → {len(paths)} 張圖片")
                    else:
                        console.print(f"  [{i}] {prompt[:50]}... → [dim magenta]失敗[/red]")

                # 詢問是否開啟圖片
                open_img = console.input("\n[magenta]要開啟所有圖片嗎？(y/N): [/magenta]").strip().lower()
                if open_img == 'y':
                    for paths in results.values():
                        for path in paths:
                            os.system(f'open "{path}"')

            except Exception as e:
                console.print(f"\n[dim magenta]錯誤：{e}[/red]")

        elif choice == '3':
            # 編輯圖片
            image_path = console.input("\n[magenta]圖片路徑（或輸入 'back' 返回）：[/magenta]\n").strip()

            if not image_path or image_path.lower() == 'back':
                continue

            if not os.path.isfile(image_path):
                console.print("[magenta]檔案不存在[/yellow]")
                continue

            prompt = console.input("\n[magenta]請描述如何編輯此圖片：[/magenta]\n").strip()

            if not prompt:
                console.print("[magenta]未輸入編輯描述[/yellow]")
                continue

            try:
                output_path = edit_image(
                    image_path=image_path,
                    prompt=prompt,
                    model=model
                )

                open_img = console.input("\n[magenta]要開啟圖片嗎？(y/N): [/magenta]").strip().lower()
                if open_img == 'y':
                    os.system(f'open "{output_path}"')

            except Exception as e:
                console.print(f"\n[dim magenta]錯誤：{e}[/red]")

        elif choice == '4':
            # 放大圖片
            image_path = console.input("\n[magenta]圖片路徑（或輸入 'back' 返回）：[/magenta]\n").strip()

            if not image_path or image_path.lower() == 'back':
                continue

            if not os.path.isfile(image_path):
                console.print("[magenta]檔案不存在[/yellow]")
                continue

            try:
                output_path = upscale_image(
                    image_path=image_path
                )

                open_img = console.input("\n[magenta]要開啟圖片嗎？(y/N): [/magenta]").strip().lower()
                if open_img == 'y':
                    os.system(f'open "{output_path}"')

            except Exception as e:
                console.print(f"\n[dim magenta]錯誤：{e}[/red]")

        else:
            console.print("\n[magenta]無效選項[/yellow]")


def main():
    """主程式"""
    console.print("[bold magenta]Gemini Imagen 3 圖片生成工具[/bold magenta]\n")

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
            console.print("\n[magenta]🖼️ 開啟圖片中...[/magenta]")
            for path in output_paths:
                os.system(f'open "{path}"')

        except Exception as e:
            console.print(f"\n[dim magenta]錯誤：{e}[/red]")
            sys.exit(1)


if __name__ == "__main__":
    main()
