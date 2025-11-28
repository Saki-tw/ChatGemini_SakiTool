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
from utils.i18n import safe_t
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

# 支援的模型（2025-11-29 更新）
MODELS = {
    '1': ('imagen-4.0-generate-001', 'Imagen 4 - 最新標準版'),
    '2': ('imagen-4.0-ultra-generate-001', 'Imagen 4 Ultra - 最高品質'),
    '3': ('imagen-4.0-fast-generate-001', 'Imagen 4 Fast - 快速生成 (最便宜)'),
    '4': ('imagen-3.0-generate-001', 'Imagen 3 - 舊版穩定'),
}

DEFAULT_MODEL = 'imagen-4.0-generate-001'
# 使用統一輸出目錄配置
from utils.path_manager import get_image_dir
OUTPUT_DIR = str(get_image_dir('imagen'))


def select_model() -> str:
    """選擇 Imagen 模型"""
    console.print(safe_t('common.message', fallback='\n[#E8C4F0]請選擇 Imagen 模型：[/#E8C4F0]'))
    for key, (model_name, description) in MODELS.items():
        console.print(f"  {key}. {description}")

    choice = console.input("\n請選擇 (1-4, 預設=1): ").strip() or '1'

    if choice in MODELS:
        return MODELS[choice][0]
    else:
        console.print(safe_t('common.message', fallback='[#E8C4F0]無效選擇，使用預設模型[/#E8C4F0]'))
        return DEFAULT_MODEL


def generate_image(
    prompt: str,
    model: str = DEFAULT_MODEL,
    negative_prompt: Optional[str] = None,
    number_of_images: int = 1,
    aspect_ratio: str = "1:1",
    safety_filter_level: str = "block_some",
    person_generation: str = "allow_adult",  # ✅ 修復：Gemini API 不支援 "allow_all"，僅支援 "allow_adult" 或 "dont_allow"
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
        person_generation: 人物生成控制（僅支援 "allow_adult" 或 "dont_allow"）
            - "allow_adult": 允許成人（預設）
            - "dont_allow": 禁止生成人物
            - ⚠️ "allow_all" 僅在 Vertex AI 支援，Gemini API 不支援
        show_cost: 是否顯示成本資訊

    Returns:
        生成的圖片檔案路徑列表
    """
    console.print("\n[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]")
    console.print(safe_t('common.generating', fallback='[bold #E8C4F0]🎨 Imagen 圖片生成[/bold #E8C4F0]'))
    console.print("[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]\n")

    console.print(safe_t('common.message', fallback='[#E8C4F0]模型：[/#E8C4F0] {model}', model=model))
    console.print(safe_t('common.message', fallback='[#E8C4F0]提示：[/#E8C4F0] {prompt}', prompt=prompt))
    if negative_prompt:
        console.print(safe_t('common.message', fallback='[#E8C4F0]負面提示：[/#E8C4F0] {negative_prompt}', negative_prompt=negative_prompt))
    console.print(safe_t('common.message', fallback='[#E8C4F0]長寬比：[/#E8C4F0] {aspect_ratio}', aspect_ratio=aspect_ratio))
    console.print(safe_t('common.message', fallback='[#E8C4F0]數量：[/#E8C4F0] {number_of_images}', number_of_images=number_of_images))

    # 計價預估（如果啟用）
    pricing_calc = None
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=number_of_images,
            operation='generate'
        )
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]💰 費用預估：[/#E8C4F0]'))
        cost_twd = cost * USD_TO_TWD
        console.print(safe_t('common.message', fallback='  總費用：NT${cost_twd:.2f} (${cost:.4f} USD)', cost_twd=cost_twd, cost=cost))
        per_image_twd = details['per_image_rate'] * USD_TO_TWD
        per_image_rate = details['per_image_rate']
        console.print(safe_t('common.message', fallback='  單價：NT${per_image_twd:.2f}/張 (${per_image_rate:.2f} USD/張)', per_image_twd=per_image_twd, per_image_rate=per_image_rate))
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
    console.print(safe_t('common.generating', fallback='\n[#E8C4F0]⏳ 開始生成圖片...[/#E8C4F0]\n'))

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

            progress.update(task, description="[#B565D8]✓ 生成完成[/#B565D8]")

        # 確保輸出目錄存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 保存圖片
        console.print(safe_t('common.saving', fallback='\n[#E8C4F0]💾 保存圖片中...[/#E8C4F0]'))

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
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]📊 圖片資訊：[/#E8C4F0]'))
        console.print(safe_t('common.generating', fallback='  生成數量：{len(output_paths)}', output_paths_count=len(output_paths)))
        console.print(safe_t('common.saving', fallback='  儲存目錄：{OUTPUT_DIR}', OUTPUT_DIR=OUTPUT_DIR))

        # 計算總檔案大小
        total_size = sum(os.path.getsize(p) for p in output_paths) / (1024 * 1024)
        console.print(safe_t('common.message', fallback='  總大小：{total_size:.2f} MB', total_size=total_size))

        # 顯示實際成本
        if pricing_calc:
            console.print(safe_t('common.message', fallback='\n[#E8C4F0]💰 實際費用：[/#E8C4F0]'))
            actual_cost = details['per_image_rate'] * len(output_paths)
            console.print(f"  NT${actual_cost * USD_TO_TWD:.2f} (${actual_cost:.4f} USD)")

        return output_paths

    except Exception as e:
        console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]❌ 生成失敗：{e}[/dim]', e=e))
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
    console.print("\n[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]")
    console.print(safe_t('common.processing', fallback='[bold #E8C4F0]🎨 Imagen 批次圖片生成（並行處理）[/bold #E8C4F0]'))
    console.print("[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]\n")

    console.print(safe_t('common.message', fallback='[#E8C4F0]模型：[/#E8C4F0] {model}', model=model))
    console.print(safe_t('common.message', fallback='[#E8C4F0]Prompt 數量：[/#E8C4F0] {len(prompts)}', prompts_count=len(prompts)))
    console.print(safe_t('common.message', fallback='[#E8C4F0]並行數量：[/#E8C4F0] {max_workers}', max_workers=max_workers))

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
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]💰 總費用預估：[/#E8C4F0]'))
        console.print(f"  NT${cost * USD_TO_TWD:.2f} (${cost:.4f} USD)")
        per_image_twd = details["per_image_rate"] * USD_TO_TWD
        console.print(safe_t('common.message', fallback='  單價：NT${per_image_twd:.2f}/張\n', per_image_twd=per_image_twd))

    console.print(safe_t('common.generating', fallback='[#E8C4F0]⏳ 開始並行生成 {len(prompts)} 組圖片...[/#E8C4F0]\n', prompts_count=len(prompts)))

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
                f"[#E8C4F0]生成中...",
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
                    console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]❌ Prompt "{prompt_short}..." 生成失敗：{e}[/dim]', prompt_short=prompt[:30], e=e))
                    results[prompt] = []
                    progress.update(task, advance=1)

    # 顯示總結
    console.print(f"\n[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]")
    console.print(safe_t('common.completed', fallback='[bold green]✓ 批次生成完成[/bold green]'))
    console.print(f"[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]\n")

    total_images = sum(len(paths) for paths in results.values())
    console.print(safe_t('common.message', fallback='[#E8C4F0]📊 總結：[/#E8C4F0]'))
    console.print(safe_t('common.generating', fallback='  成功生成：{total_images} 張圖片', total_images=total_images))
    failed_count = len(prompts) - len([p for p in results.values() if p])
    console.print(safe_t('error.failed', fallback='  失敗數量：{failed_count}', failed_count=failed_count))

    # 顯示實際成本
    if PRICING_ENABLED and show_cost:
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]💰 實際費用：[/#E8C4F0]'))
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
    ⚠️ 已廢棄 (DEPRECATED) - Imagen API 不支援此功能

    編輯圖片 - 此功能無法使用

    原因：Google Imagen API 不提供 edit_image() 方法
    官方文檔：https://ai.google.dev/gemini-api/docs/imagen
    API 僅支援：generate_images() (文字生成圖片)

    替代方案：
    1. 使用 generate_image() 重新生成圖片
    2. 使用 Gemini Vision 分析圖片 + Imagen 生成新圖片

    移除日期：2025-10-31

    Args:
        image_path: 原始圖片路徑
        prompt: 編輯描述
        model: 使用的模型
        show_cost: 是否顯示成本資訊

    Returns:
        編輯後的圖片路徑

    Raises:
        NotImplementedError: API 不支援此功能
    """
    # ==========================================
    # API 限制錯誤：Imagen 不支援圖片編輯
    # ==========================================
    console.print("\n[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]")
    console.print(safe_t('common.message', fallback='[bold red]⚠️  Imagen 圖片編輯 - 功能不可用[/bold red]'))
    console.print("[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]\n")

    console.print(safe_t('error.api_not_supported',
                        fallback='[dim #E8C4F0]❌ Imagen API 不支援圖片編輯功能[/dim #E8C4F0]\n'
                                 '[dim #E8C4F0]📚 官方文檔：https://ai.google.dev/gemini-api/docs/imagen[/dim #E8C4F0]\n'
                                 '[dim #E8C4F0]✅ API 僅支援：generate_images() (文字生成圖片)[/dim #E8C4F0]\n'))
    console.print(safe_t('common.message', fallback='[#B565D8]💡 替代方案：[/#B565D8]'))
    console.print(safe_t('common.message', fallback='  1. 使用 Imagen 圖像生成 (選項 [12]) 重新創作'))
    console.print(safe_t('common.message', fallback='  2. 使用 Gemini Vision 分析圖片後，用 Imagen 生成新圖片\n'))

    raise NotImplementedError(
        "Imagen API does not support edit_image() method. "
        "Only generate_images() is available. "
        "See: https://ai.google.dev/gemini-api/docs/imagen"
    )

    # 以下代碼已無效（保留用於未來 API 更新）
    if not os.path.isfile(image_path):
        # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
        try:
            from error_fix_suggestions import suggest_file_not_found
            alternative_path = suggest_file_not_found(image_path, auto_fix=True)

            if alternative_path and os.path.isfile(alternative_path):
                # 用戶選擇了替代檔案，使用新路徑
                image_path = alternative_path
                console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{image_path}[/#B565D8]\n', image_path=image_path))
            else:
                raise FileNotFoundError(f"找不到檔案，請參考上述建議")
        except ImportError:
            # 如果沒有修復建議模組，直接拋出錯誤
            raise FileNotFoundError(f"圖片檔案不存在: {image_path}")

    console.print(safe_t('common.message', fallback='[#E8C4F0]原始圖片：[/#E8C4F0] {image_path}', image_path=image_path))
    console.print(safe_t('common.message', fallback='[#E8C4F0]編輯提示：[/#E8C4F0] {prompt}', prompt=prompt))

    # 上傳圖片
    console.print(safe_t('common.message', fallback='\n[#E8C4F0]📤 上傳圖片...[/#E8C4F0]'))
    uploaded_image = client.files.upload(file=image_path)

    # 計價預估
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=1,
            operation='edit'
        )
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]💰 費用預估：[/#E8C4F0]'))
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

            progress.update(task, description="[#B565D8]✓ 編輯完成[/#B565D8]")

        # 保存編輯後的圖片
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"imagen_edit_{timestamp}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        image_data = client.files.download(file=response.generated_image.image)
        with open(output_path, 'wb') as f:
            f.write(image_data)

        console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 圖片已儲存：{output_path}[/#B565D8]', output_path=output_path))

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]📊 圖片資訊：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  檔案大小：{file_size:.2f} MB', file_size=file_size))

        return output_path

    except Exception as e:
        console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]❌ 編輯失敗：{e}[/dim]', e=e))
        raise


def upscale_image(
    image_path: str,
    model: str = "imagen-3.0-capability-upscale-001",
    show_cost: bool = True
) -> str:
    """
    ⚠️ 已廢棄 (DEPRECATED) - 僅 Vertex AI 支援此功能

    放大圖片 - 此功能在 Gemini Developer API 無法使用

    原因：upscale_image() 方法僅在 Vertex AI 客戶端可用
    錯誤訊息："This method is only supported in the Vertex AI client."
    測試結果：test_imagen_upscale.py (2025-10-31)

    替代方案：
    1. 使用 Vertex AI 客戶端（需要 Google Cloud 專案配置）
    2. 使用第三方圖片放大工具

    移除日期：2025-10-31

    Args:
        image_path: 原始圖片路徑
        model: 使用的模型
        show_cost: 是否顯示成本資訊

    Returns:
        放大後的圖片路徑

    Raises:
        NotImplementedError: Gemini Developer API 不支援此功能
    """
    # ==========================================
    # API 限制錯誤：upscale_image 僅 Vertex AI 支援
    # ==========================================
    console.print("\n[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]")
    console.print(safe_t('common.message', fallback='[bold red]⚠️  Imagen 圖片放大 - 功能不可用[/bold red]'))
    console.print("[#E8C4F0]" + "=" * 60 + "[/#E8C4F0]\n")

    console.print(safe_t('error.api_not_supported',
                        fallback='[dim #E8C4F0]❌ upscale_image 僅 Vertex AI 客戶端支援[/dim #E8C4F0]\n'
                                 '[dim #E8C4F0]📚 錯誤訊息："This method is only supported in the Vertex AI client."[/dim #E8C4F0]\n'
                                 '[dim #E8C4F0]✅ 本專案使用 Gemini Developer API，不支援此功能[/dim #E8C4F0]\n'))
    console.print(safe_t('common.message', fallback='[#B565D8]💡 替代方案：[/#B565D8]'))
    console.print(safe_t('common.message', fallback='  1. 配置 Vertex AI 客戶端（需要 Google Cloud 專案）'))
    console.print(safe_t('common.message', fallback='  2. 使用第三方圖片放大工具\n'))

    raise NotImplementedError(
        "upscale_image() is only supported in the Vertex AI client. "
        "Gemini Developer API does not support this method. "
        "Error: 'This method is only supported in the Vertex AI client.'"
    )

    # 以下代碼已無效（保留用於 Vertex AI 遷移參考）
    if not os.path.isfile(image_path):
        # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
        try:
            from error_fix_suggestions import suggest_file_not_found
            alternative_path = suggest_file_not_found(image_path, auto_fix=True)

            if alternative_path and os.path.isfile(alternative_path):
                # 用戶選擇了替代檔案，使用新路徑
                image_path = alternative_path
                console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{image_path}[/#B565D8]\n', image_path=image_path))
            else:
                raise FileNotFoundError(f"找不到檔案，請參考上述建議")
        except ImportError:
            # 如果沒有修復建議模組，直接拋出錯誤
            raise FileNotFoundError(f"圖片檔案不存在: {image_path}")

    console.print(safe_t('common.message', fallback='[#E8C4F0]原始圖片：[/#E8C4F0] {image_path}', image_path=image_path))

    # 上傳圖片
    console.print(safe_t('common.message', fallback='\n[#E8C4F0]📤 上傳圖片...[/#E8C4F0]'))
    uploaded_image = client.files.upload(file=image_path)

    # 計價預估
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_image_generation_cost(
            model_name=model,
            number_of_images=1,
            operation='upscale'
        )
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]💰 費用預估：[/#E8C4F0]'))
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

            progress.update(task, description="[#B565D8]✓ 放大完成[/#B565D8]")

        # 保存放大後的圖片
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"imagen_upscale_{timestamp}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        image_data = client.files.download(file=response.generated_image.image)
        with open(output_path, 'wb') as f:
            f.write(image_data)

        console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 圖片已儲存：{output_path}[/#B565D8]', output_path=output_path))

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]📊 圖片資訊：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  檔案大小：{file_size:.2f} MB', file_size=file_size))

        return output_path

    except Exception as e:
        console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]❌ 放大失敗：{e}[/dim]', e=e))
        raise


def interactive_mode():
    """互動式圖片生成模式"""
    console.print(safe_t('common.generating', fallback='\n[bold #E8C4F0]🎨 Imagen 互動式圖片生成[/bold #E8C4F0]\n'))

    # 選擇模型
    model = select_model()

    while True:
        console.print("\n" + "=" * 60)
        console.print(safe_t('imagen.menu_title', fallback='\n[#E8C4F0]功能選擇：[/#E8C4F0]'))
        console.print(safe_t('imagen.menu_generate', fallback='  [1] 生成圖片（Text-to-Image）'))
        console.print(safe_t('imagen.menu_batch', fallback='  [2] 批次生成圖片（Batch Generation - 並行處理）'))
        console.print(safe_t('imagen.menu_edit', fallback='  [3] 編輯圖片（Image Editing）'))
        console.print(safe_t('imagen.menu_upscale', fallback='  [4] 放大圖片（Upscaling）'))
        console.print(safe_t('imagen.menu_exit', fallback='  [0] 退出\n'))

        choice = console.input("請選擇: ").strip()

        if choice == '0':
            console.print(safe_t('common.message', fallback='\n[#B565D8]再見！[/#B565D8]'))
            break

        elif choice == '1':
            # 生成圖片
            prompt = console.input("\n[#E8C4F0]請描述您想生成的圖片（或輸入 'back' 返回）：[/#E8C4F0]\n").strip()

            if not prompt or prompt.lower() == 'back':
                continue

            # 負面提示
            negative_prompt = console.input("\n[#E8C4F0]負面提示（避免的內容，可留空）：[/#E8C4F0]\n").strip()
            if not negative_prompt:
                negative_prompt = None

            # 長寬比
            console.print(safe_t('common.message', fallback='\n[#E8C4F0]選擇長寬比：[/#E8C4F0]'))
            console.print(safe_t('common.message', fallback='  1. 1:1 (正方形，預設)'))
            console.print(safe_t('common.message', fallback='  2. 16:9 (橫向)'))
            console.print(safe_t('common.message', fallback='  3. 9:16 (直向)'))
            console.print("  4. 3:4")
            console.print("  5. 4:3")
            aspect_choice = console.input("\n請選擇 (1-5, 預設=1): ").strip() or '1'

            aspect_ratios = {'1': '1:1', '2': '16:9', '3': '9:16', '4': '3:4', '5': '4:3'}
            aspect_ratio = aspect_ratios.get(aspect_choice, '1:1')

            # 生成數量
            num_input = console.input("\n[#E8C4F0]生成數量（1-8，預設=1）：[/#E8C4F0] ").strip()
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
                open_img = console.input("\n[#E8C4F0]要開啟圖片嗎？(y/N): [/#E8C4F0]").strip().lower()
                if open_img == 'y' and output_paths:
                    for path in output_paths:
                        os.system(f'open "{path}"')

            except Exception as e:
                console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]錯誤：{e}[/dim]', e=e))

        elif choice == '2':
            # 批次生成圖片（並行處理）
            console.print(safe_t('common.processing', fallback='\n[#E8C4F0]批次圖片生成模式（輸入多個 prompt，並行處理）[/#E8C4F0]'))
            console.print(safe_t('common.message', fallback='[#E8C4F0]每行一個 prompt，輸入空行結束：[/#E8C4F0]\n'))

            prompts = []
            while True:
                line = console.input(f"Prompt #{len(prompts)+1} (留空結束): ").strip()
                if not line:
                    break
                prompts.append(line)

            if not prompts:
                console.print(safe_t('common.message', fallback='[#E8C4F0]未輸入任何 prompt[/#E8C4F0]'))
                continue

            # 長寬比選擇（全部統一）
            console.print(safe_t('common.message', fallback='\n[#E8C4F0]選擇長寬比（套用至所有圖片）：[/#E8C4F0]'))
            console.print(safe_t('common.message', fallback='  1. 1:1 (正方形，預設)'))
            console.print(safe_t('common.message', fallback='  2. 16:9 (橫向)'))
            console.print(safe_t('common.message', fallback='  3. 9:16 (直向)'))
            console.print("  4. 3:4")
            console.print("  5. 4:3")
            aspect_choice = console.input("\n請選擇 (1-5, 預設=1): ").strip() or '1'

            aspect_ratios_map = {'1': '1:1', '2': '16:9', '3': '9:16', '4': '3:4', '5': '4:3'}
            aspect_ratio = aspect_ratios_map.get(aspect_choice, '1:1')

            # 並行數量
            max_workers_input = console.input("\n[#E8C4F0]並行數量（1-5，預設=3）：[/#E8C4F0] ").strip()
            max_workers = int(max_workers_input) if max_workers_input.isdigit() and 1 <= int(max_workers_input) <= 5 else 3

            try:
                results = generate_images_batch(
                    prompts=prompts,
                    model=model,
                    aspect_ratios=[aspect_ratio] * len(prompts),
                    max_workers=max_workers
                )

                # 顯示結果摘要
                console.print(safe_t('common.generating', fallback='\n[#E8C4F0]📋 生成結果摘要：[/#E8C4F0]'))
                for i, (prompt, paths) in enumerate(results.items(), 1):
                    if paths:
                        console.print(safe_t('common.message', fallback='  [{i}] {prompt[:50]}... → {len(paths)} 張圖片', i=i, prompt_short=prompt[:50], paths_count=len(paths)))
                    else:
                        console.print(safe_t('error.failed', fallback='  [{i}] {prompt[:50]}... → [dim #E8C4F0]失敗[/dim]', i=i, prompt_short=prompt[:50]))

                # 詢問是否開啟圖片
                open_img = console.input("\n[#E8C4F0]要開啟所有圖片嗎？(y/N): [/#E8C4F0]").strip().lower()
                if open_img == 'y':
                    for paths in results.values():
                        for path in paths:
                            os.system(f'open "{path}"')

            except Exception as e:
                console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]錯誤：{e}[/dim]', e=e))

        elif choice == '3':
            # 編輯圖片
            image_path = console.input("\n[#E8C4F0]圖片路徑（或輸入 'back' 返回）：[/#E8C4F0]\n").strip()

            if not image_path or image_path.lower() == 'back':
                continue

            if not os.path.isfile(image_path):
                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                continue

            prompt = console.input("\n[#E8C4F0]請描述如何編輯此圖片：[/#E8C4F0]\n").strip()

            if not prompt:
                console.print(safe_t('common.message', fallback='[#E8C4F0]未輸入編輯描述[/#E8C4F0]'))
                continue

            try:
                output_path = edit_image(
                    image_path=image_path,
                    prompt=prompt,
                    model=model
                )

                open_img = console.input("\n[#E8C4F0]要開啟圖片嗎？(y/N): [/#E8C4F0]").strip().lower()
                if open_img == 'y':
                    os.system(f'open "{output_path}"')

            except Exception as e:
                console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]錯誤：{e}[/dim]', e=e))

        elif choice == '4':
            # 放大圖片
            image_path = console.input("\n[#E8C4F0]圖片路徑（或輸入 'back' 返回）：[/#E8C4F0]\n").strip()

            if not image_path or image_path.lower() == 'back':
                continue

            if not os.path.isfile(image_path):
                console.print(safe_t('common.message', fallback='[#E8C4F0]檔案不存在[/#E8C4F0]'))
                continue

            try:
                output_path = upscale_image(
                    image_path=image_path
                )

                open_img = console.input("\n[#E8C4F0]要開啟圖片嗎？(y/N): [/#E8C4F0]").strip().lower()
                if open_img == 'y':
                    os.system(f'open "{output_path}"')

            except Exception as e:
                console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]錯誤：{e}[/dim]', e=e))

        else:
            console.print(safe_t('common.message', fallback='\n[#E8C4F0]無效選項[/#E8C4F0]'))


def main():
    """主程式"""
    console.print(safe_t('common.generating', fallback='[bold #E8C4F0]Gemini Imagen 3 圖片生成工具[/bold #E8C4F0]\n'))

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
            console.print(safe_t('common.message', fallback='\n[#E8C4F0]🖼️ 開啟圖片中...[/#E8C4F0]'))
            for path in output_paths:
                os.system(f'open "{path}"')

        except Exception as e:
            console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]錯誤：{e}[/dim]', e=e))
            sys.exit(1)


if __name__ == "__main__":
    main()
