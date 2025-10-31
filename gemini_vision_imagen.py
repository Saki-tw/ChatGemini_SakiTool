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
from utils.i18n import safe_t
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
        console.print(f"[yellow]⚠️  無法讀取圖片尺寸：{e}[/yellow]")
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
    console.print("\n[#B565D8]📊 Step 1/2: Gemini Vision 分析原圖[/#B565D8]")

    # 上傳圖片
    console.print("[dim #E8C4F0]📤 上傳圖片...[/dim #E8C4F0]")
    uploaded_image = client.files.upload(file=image_path)
    console.print(f"[dim #E8C4F0]✅ 已上傳：{uploaded_image.name}[/dim #E8C4F0]")

    # 構建分析提示
    analysis_prompt = f"""
請仔細分析這張圖片，並按以下步驟處理：

1. **描述原圖**：
   - 主要物件和內容
   - 顏色、光線、構圖
   - 風格和氛圍

2. **應用修改指示**：
   編輯指示：{edit_instruction}

3. **生成新的圖片描述**：
   根據上述修改指示，生成一段完整的圖片描述，適合用於 Imagen 圖片生成。
   描述應該：
   - 具體且詳細
   - 包含風格、顏色、構圖等細節
   - 適合 AI 圖片生成

請直接輸出最終的圖片描述（不需要其他說明）。
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

        console.print(f"\n[dim #E8C4F0]💰 預估成本：${estimated_cost:.6f} USD (NT$ {estimated_cost * USD_TO_TWD:.2f})[/dim #E8C4F0]")
        console.print(f"[dim #E8C4F0]   - 圖片 tokens: {est_details['image_tokens']} ({width}x{height})[/dim #E8C4F0]")

    # 執行分析
    console.print("\n[#E8C4F0]🔍 分析中...[/#E8C4F0]")
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

            console.print(f"\n[#B565D8]✅ 分析完成[/#B565D8]")
            console.print(f"[dim #E8C4F0]💰 實際成本：${actual_cost:.6f} USD (NT$ {actual_cost * USD_TO_TWD:.2f})[/dim #E8C4F0]")
            console.print(f"[dim #E8C4F0]   - 輸入 tokens: {response.usage_metadata.prompt_token_count}[/dim #E8C4F0]")
            console.print(f"[dim #E8C4F0]   - 輸出 tokens: {response.usage_metadata.candidates_token_count}[/dim #E8C4F0]")

            # 記錄實際成本到預算
            pricing_calc.record_actual_cost(actual_cost)
        else:
            console.print(f"\n[#B565D8]✅ 分析完成[/#B565D8]")

        # 清理上傳的檔案
        try:
            client.files.delete(name=uploaded_image.name)
        except:
            pass

        return new_description, actual_cost, response.usage_metadata if hasattr(response, 'usage_metadata') else None

    except Exception as e:
        console.print(f"[red]❌ 分析失敗：{e}[/red]")
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
    console.print("\n[#B565D8]📊 Step 2/2: Imagen 生成新圖片[/#B565D8]")

    # 計算成本
    if PRICING_AVAILABLE and PRICING_ENABLED:
        pricing_calc = get_pricing_calculator()

        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=imagen_model,
            number_of_images=number_of_images
        )

        console.print(f"\n[dim #E8C4F0]💰 預估成本：${cost:.6f} USD (NT$ {cost * USD_TO_TWD:.2f})[/dim #E8C4F0]")
        console.print(f"[dim #E8C4F0]   - 單價：${details['per_image_rate']:.4f} / 張[/dim #E8C4F0]")

    # 生成圖片
    console.print("\n[#E8C4F0]🎨 生成中...[/#E8C4F0]")
    try:
        # 使用現有的 generate_image 函數
        image_paths = generate_image(
            prompt=description,
            model=imagen_model,
            number_of_images=number_of_images,
            show_cost=False  # 已經顯示過了
        )

        console.print(f"\n[#B565D8]✅ 生成完成[/#B565D8]")

        # Imagen 不提供 token 資訊，直接使用計算的成本
        actual_cost = cost if (PRICING_AVAILABLE and PRICING_ENABLED) else 0

        return image_paths, actual_cost

    except Exception as e:
        console.print(f"[red]❌ 生成失敗：{e}[/red]")
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
    console.print("[bold #B565D8]🎨 Gemini Vision + Imagen 智能圖片創作[/bold #B565D8]")
    console.print("="*70)

    # 驗證原圖存在
    if not os.path.isfile(source_image_path):
        raise FileNotFoundError(f"原始圖片不存在: {source_image_path}")

    console.print(f"\n[#E8C4F0]原圖：[/#E8C4F0] {source_image_path}")
    console.print(f"[#E8C4F0]指示：[/#E8C4F0] {edit_instruction}")
    console.print(f"[#E8C4F0]模型：[/#E8C4F0] {gemini_model} + {imagen_model}")

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

        console.print(f"\n[#E8C4F0]💰 預估總成本：${estimated_total:.6f} USD (NT$ {estimated_total * USD_TO_TWD:.2f})[/#E8C4F0]")

        # 檢查預算
        can_proceed, warning, budget_status = pricing_calc.check_budget(estimated_total)

        if warning:
            console.print(f"[yellow]⚠️  {warning}[/yellow]")

        if not can_proceed:
            raise RuntimeError(f"預算不足：{warning}")

    # Step 1: Gemini Vision 分析
    new_description, gemini_cost, _ = analyze_image_with_gemini(
        image_path=source_image_path,
        edit_instruction=edit_instruction,
        gemini_model=gemini_model
    )

    # 顯示生成的描述
    console.print(f"\n[dim #E8C4F0]📝 生成的描述：[/dim #E8C4F0]")
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
        console.print("[bold #B565D8]💰 成本總結[/bold #B565D8]")
        console.print("="*70)
        console.print(f"Gemini Vision 分析：${gemini_cost:.6f} USD (NT$ {gemini_cost * USD_TO_TWD:.2f})")
        console.print(f"Imagen 圖片生成：  ${imagen_cost:.6f} USD (NT$ {imagen_cost * USD_TO_TWD:.2f})")
        console.print(f"{'─'*70}")
        console.print(f"[bold]總計：           ${total_cost:.6f} USD (NT$ {total_cost * USD_TO_TWD:.2f})[/bold]")
        console.print("="*70)

    # 返回第一張圖片路徑
    output_path = image_paths[0] if isinstance(image_paths, list) else image_paths

    console.print(f"\n[bold #B565D8]✅ 創作完成！[/bold #B565D8]")
    console.print(f"[#E8C4F0]輸出：[/#E8C4F0] {output_path}")

    if number_of_images > 1:
        console.print(f"[dim #E8C4F0]共生成 {len(image_paths)} 張圖片[/dim #E8C4F0]")

    return output_path


def main():
    """測試函數"""
    import sys

    if len(sys.argv) < 3:
        console.print("[yellow]用法：python3 gemini_vision_imagen.py <圖片路徑> <編輯指示>[/yellow]")
        console.print("\n範例：")
        console.print("  python3 gemini_vision_imagen.py photo.jpg '把背景改成藍色天空'")
        sys.exit(1)

    source_path = sys.argv[1]
    instruction = sys.argv[2]

    try:
        output = create_image_with_vision(
            source_image_path=source_path,
            edit_instruction=instruction,
            show_cost=True
        )

        console.print(f"\n[bold green]✅ 成功！輸出：{output}[/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]❌ 錯誤：{e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
