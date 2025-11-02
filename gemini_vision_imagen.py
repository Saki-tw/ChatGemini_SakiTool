#!/usr/bin/env python3
"""
Gemini Vision + Imagen 組合創作模組

功能：
- 使用 Gemini Vision 分析原圖
- 根據編輯指示生成新的圖片描述
- 使用 Imagen 生成新圖片

設計原則：
- 完全獨立，不依賴 gemini_chat.py
- 透過 gemini_pricing.py 計價接口
- 使用 utils/api_client.py 獲取 client
- 清晰的成本顯示
"""
import os
from typing import Optional
from datetime import datetime
from rich.console import Console
from PIL import Image

# 共用工具模組
from utils.api_client import get_gemini_client
from i18n_utils import t
from gemini_pricing import USD_TO_TWD

# 計價模組（僅用於計價，不沾黏業務邏輯）
try:
    from utils.pricing_loader import (
        get_pricing_calculator,
        PRICING_ENABLED
    )
    PRICING_AVAILABLE = True
except ImportError:
    PRICING_AVAILABLE = False
    PRICING_ENABLED = False

# Imagen 生成器（用於最終生成）
from gemini_imagen_generator import generate_image

console = Console()

# 初始化 API 客戶端
client = get_gemini_client()

# 輸出目錄
from utils.path_manager import get_image_dir
OUTPUT_DIR = str(get_image_dir('vision_imagen'))


def get_image_dimensions(image_path: str) -> tuple:
    """
    獲取圖片尺寸

    Args:
        image_path: 圖片路徑

    Returns:
        (寬度, 高度)
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        console.print(f"[yellow]{t('media.vision_imagen.cannot_read_dimensions', error=str(e))}[/yellow]")
        # 預設尺寸（Full HD）
        return (1920, 1080)


def analyze_image_with_gemini(
    image_path: str,
    edit_instruction: str,
    gemini_model: str = "gemini-2.5-flash"
) -> tuple:
    """
    使用 Gemini Vision 分析圖片並生成新描述

    Args:
        image_path: 原始圖片路徑
        edit_instruction: 編輯指示
        gemini_model: Gemini 模型名稱

    Returns:
        (新圖片描述, 實際成本, 詳細資訊)
    """
    console.print(f"\n[#B565D8]{t('media.vision_imagen.step1_title')}[/#B565D8]")

    # 上傳圖片
    console.print(f"[dim #E8C4F0]{t('media.vision_imagen.uploading_image')}[/dim #E8C4F0]")
    uploaded_image = client.files.upload(file=image_path)
    console.print(f"[dim #E8C4F0]{t('media.vision_imagen.uploaded', name=uploaded_image.name)}[/dim #E8C4F0]")

    # 構建分析提示
    analysis_prompt = f"""{t('media.vision_imagen.analysis_prompt.intro')}

{t('media.vision_imagen.analysis_prompt.step1_title')}
{t('media.vision_imagen.analysis_prompt.step1_item1')}
{t('media.vision_imagen.analysis_prompt.step1_item2')}
{t('media.vision_imagen.analysis_prompt.step1_item3')}

{t('media.vision_imagen.analysis_prompt.step2_title')}
{t('media.vision_imagen.analysis_prompt.step2_instruction', instruction=edit_instruction)}

{t('media.vision_imagen.analysis_prompt.step3_title')}
{t('media.vision_imagen.analysis_prompt.step3_line1')}
{t('media.vision_imagen.analysis_prompt.step3_line2')}
{t('media.vision_imagen.analysis_prompt.step3_item1')}
{t('media.vision_imagen.analysis_prompt.step3_item2')}
{t('media.vision_imagen.analysis_prompt.step3_item3')}

{t('media.vision_imagen.analysis_prompt.outro')}
"""

    # 計算預估成本
    if PRICING_AVAILABLE and PRICING_ENABLED:
        pricing_calc = get_pricing_calculator()

        # 獲取圖片尺寸
        width, height = get_image_dimensions(image_path)

        # 預估 token（prompt 約 150 tokens，輸出約 500 tokens）
        estimated_cost, est_details = pricing_calc.calculate_multimodal_cost(
            model_name=gemini_model,
            prompt_tokens=150,
            images=[(width, height)],
            output_tokens=500
        )

        console.print(f"\n[dim #E8C4F0]{t('media.vision_imagen.estimated_cost', cost_usd=f'{estimated_cost:.6f}', cost_twd=f'{estimated_cost * USD_TO_TWD:.2f}')}[/dim #E8C4F0]")
        console.print(f"[dim #E8C4F0]{t('media.vision_imagen.image_tokens', tokens=est_details['image_tokens'], width=width, height=height)}[/dim #E8C4F0]")

    # 執行分析
    console.print(f"\n[#E8C4F0]{t('media.vision_imagen.analyzing')}[/#E8C4F0]")
    try:
        response = client.models.generate_content(
            model=gemini_model,
            contents=[analysis_prompt, uploaded_image]
        )

        new_description = response.text.strip()

        # 計算實際成本
        actual_cost = 0
        if PRICING_AVAILABLE and PRICING_ENABLED and response.usage_metadata:
            actual_cost, actual_details = pricing_calc.calculate_text_cost(
                model_name=gemini_model,
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count
            )

            console.print(f"\n[#B565D8]{t('media.vision_imagen.analysis_complete')}[/#B565D8]")
            console.print(f"[dim #E8C4F0]{t('media.vision_imagen.actual_cost', cost_usd=f'{actual_cost:.6f}', cost_twd=f'{actual_cost * USD_TO_TWD:.2f}')}[/dim #E8C4F0]")
            console.print(f"[dim #E8C4F0]{t('media.vision_imagen.input_tokens', tokens=response.usage_metadata.prompt_token_count)}[/dim #E8C4F0]")
            console.print(f"[dim #E8C4F0]{t('media.vision_imagen.output_tokens', tokens=response.usage_metadata.candidates_token_count)}[/dim #E8C4F0]")

            # 記錄實際成本到預算
            pricing_calc.record_actual_cost(actual_cost)
        else:
            console.print(f"\n[#B565D8]{t('media.vision_imagen.analysis_complete')}[/#B565D8]")

        # 清理上傳的檔案
        try:
            client.files.delete(name=uploaded_image.name)
        except:
            pass

        return new_description, actual_cost, response.usage_metadata if hasattr(response, 'usage_metadata') else None

    except Exception as e:
        console.print(f"[red]{t('media.vision_imagen.analysis_failed', error=str(e))}[/red]")
        raise


def generate_image_with_imagen(
    description: str,
    imagen_model: str = "imagen-4.0-fast-generate-001",
    number_of_images: int = 1
) -> tuple:
    """
    使用 Imagen 生成圖片

    Args:
        description: 圖片描述
        imagen_model: Imagen 模型名稱
        number_of_images: 生成數量

    Returns:
        (圖片路徑列表, 實際成本)
    """
    console.print(f"\n[#B565D8]{t('media.vision_imagen.step2_title')}[/#B565D8]")

    # 計算成本
    if PRICING_AVAILABLE and PRICING_ENABLED:
        pricing_calc = get_pricing_calculator()

        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=imagen_model,
            number_of_images=number_of_images
        )

        cost_usd_str = f'{cost:.6f}'
        cost_twd_str = f'{cost * USD_TO_TWD:.2f}'
        unit_price_str = f"{details['per_image_rate']:.4f}"

        console.print(f"\n[dim #E8C4F0]{t('media.vision_imagen.estimated_cost', cost_usd=cost_usd_str, cost_twd=cost_twd_str)}[/dim #E8C4F0]")
        console.print(f"[dim #E8C4F0]{t('media.vision_imagen.unit_price', price=unit_price_str)}[/dim #E8C4F0]")

    # 生成圖片
    console.print(f"\n[#E8C4F0]{t('media.vision_imagen.generating')}[/#E8C4F0]")
    try:
        # 使用現有的 generate_image 函數
        image_paths = generate_image(
            prompt=description,
            model=imagen_model,
            number_of_images=number_of_images,
            show_cost=False  # 已經顯示過了
        )

        console.print(f"\n[#B565D8]{t('media.vision_imagen.generation_complete')}[/#B565D8]")

        # Imagen 不提供 token 資訊，直接使用計算的成本
        actual_cost = cost if (PRICING_AVAILABLE and PRICING_ENABLED) else 0

        return image_paths, actual_cost

    except Exception as e:
        console.print(f"[red]{t('media.vision_imagen.generation_failed', error=str(e))}[/red]")
        raise


def create_image_with_vision(
    source_image_path: str,
    edit_instruction: str,
    gemini_model: str = "gemini-2.5-flash",
    imagen_model: str = "imagen-4.0-fast-generate-001",
    number_of_images: int = 1,
    show_cost: bool = True
) -> str:
    """
    使用 Gemini Vision + Imagen 組合創作圖片

    流程：
    1. Gemini Vision 分析原圖並生成新描述
    2. Imagen 根據描述生成新圖片

    Args:
        source_image_path: 原始圖片路徑
        edit_instruction: 編輯指示（如"把背景改成藍天"）
        gemini_model: Gemini 模型（預設 gemini-2.5-flash）
        imagen_model: Imagen 模型（預設 imagen-4.0-fast 最便宜）
        number_of_images: 生成圖片數量（預設 1）
        show_cost: 是否顯示成本資訊

    Returns:
        生成的圖片路徑（如果生成多張，返回第一張）

    Raises:
        FileNotFoundError: 原始圖片不存在
        Exception: API 錯誤

    Example:
        output = create_image_with_vision(
            source_image_path="photo.jpg",
            edit_instruction="把背景改成藍色天空",
            show_cost=True
        )
        print(f"已生成：{output}")
    """
    console.print("\n" + "="*70)
    console.print(f"[bold #B565D8]{t('media.vision_imagen.title')}[/bold #B565D8]")
    console.print("="*70)

    # 驗證原圖存在
    if not os.path.isfile(source_image_path):
        raise FileNotFoundError(t('media.vision_imagen.source_not_found', path=source_image_path))

    console.print(f"\n[#E8C4F0]{t('media.vision_imagen.source_image')}[/#E8C4F0] {source_image_path}")
    console.print(f"[#E8C4F0]{t('media.vision_imagen.instruction')}[/#E8C4F0] {edit_instruction}")
    console.print(f"[#E8C4F0]{t('media.vision_imagen.model')}[/#E8C4F0] {gemini_model} + {imagen_model}")

    # 檢查預算（如果啟用）
    if PRICING_AVAILABLE and PRICING_ENABLED and show_cost:
        pricing_calc = get_pricing_calculator()

        # 預估總成本（粗估）
        width, height = get_image_dimensions(source_image_path)

        estimated_total, _ = pricing_calc.calculate_gemini_imagen_combo_cost(
            gemini_model=gemini_model,
            imagen_model=imagen_model,
            analysis_prompt_tokens=150,
            source_images=[(width, height)],
            analysis_output_tokens=500,
            number_of_generated_images=number_of_images
        )

        console.print(f"\n[#E8C4F0]{t('media.vision_imagen.estimated_total_cost', cost_usd=f'{estimated_total:.6f}', cost_twd=f'{estimated_total * USD_TO_TWD:.2f}')}[/#E8C4F0]")

        # 檢查預算
        can_proceed, warning, budget_status = pricing_calc.check_budget(estimated_total)

        if warning:
            console.print(f"[yellow]⚠️  {warning}[/yellow]")

        if not can_proceed:
            raise RuntimeError(t('media.vision_imagen.budget_insufficient', warning=warning))

    # Step 1: Gemini Vision 分析
    new_description, gemini_cost, _ = analyze_image_with_gemini(
        image_path=source_image_path,
        edit_instruction=edit_instruction,
        gemini_model=gemini_model
    )

    # 顯示生成的描述
    console.print(f"\n[dim #E8C4F0]{t('media.vision_imagen.generated_description')}[/dim #E8C4F0]")
    console.print(f"[dim #E8C4F0]{new_description[:200]}{'...' if len(new_description) > 200 else ''}[/dim #E8C4F0]")

    # Step 2: Imagen 生成
    image_paths, imagen_cost = generate_image_with_imagen(
        description=new_description,
        imagen_model=imagen_model,
        number_of_images=number_of_images
    )

    # 總結成本
    if show_cost and (PRICING_AVAILABLE and PRICING_ENABLED):
        total_cost = gemini_cost + imagen_cost

        console.print("\n" + "="*70)
        console.print(f"[bold #B565D8]{t('media.vision_imagen.cost_summary')}[/bold #B565D8]")
        console.print("="*70)
        console.print(t('media.vision_imagen.vision_analysis_cost', cost_usd=f'{gemini_cost:.6f}', cost_twd=f'{gemini_cost * USD_TO_TWD:.2f}'))
        console.print(t('media.vision_imagen.imagen_generation_cost', cost_usd=f'{imagen_cost:.6f}', cost_twd=f'{imagen_cost * USD_TO_TWD:.2f}'))
        console.print(f"{'─'*70}")
        console.print(f"[bold]{t('media.vision_imagen.total_cost', cost_usd=f'{total_cost:.6f}', cost_twd=f'{total_cost * USD_TO_TWD:.2f}')}[/bold]")
        console.print("="*70)

    # 返回第一張圖片路徑
    output_path = image_paths[0] if isinstance(image_paths, list) else image_paths

    console.print(f"\n[bold #B565D8]{t('media.vision_imagen.creation_complete')}[/bold #B565D8]")
    console.print(f"[#E8C4F0]{t('media.vision_imagen.output')}[/#E8C4F0] {output_path}")

    if number_of_images > 1:
        console.print(f"[dim #E8C4F0]{t('media.vision_imagen.generated_count', count=len(image_paths))}[/dim #E8C4F0]")

    return output_path


def main():
    """測試函數"""
    import sys

    if len(sys.argv) < 3:
        console.print(f"[yellow]{t('media.vision_imagen.cli.usage')}[/yellow]")
        console.print(f"\n{t('media.vision_imagen.cli.example')}")
        console.print(t('media.vision_imagen.cli.example_cmd'))
        sys.exit(1)

    source_path = sys.argv[1]
    instruction = sys.argv[2]

    try:
        output = create_image_with_vision(
            source_image_path=source_path,
            edit_instruction=instruction,
            show_cost=True
        )

        console.print(f"\n[bold green]{t('media.vision_imagen.cli.success', output=output)}[/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]{t('media.vision_imagen.cli.error', error=str(e))}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
