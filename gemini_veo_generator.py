#!/usr/bin/env python3
"""
Gemini Veo 3.1 影片生成工具
使用 Veo 3.1 從文字生成高品質影片
"""
import os
import sys
import time
from typing import Optional, List
from google.genai import types
from rich.console import Console
from utils.i18n import safe_t
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from datetime import datetime

# 共用工具模組
from utils.api_client import get_gemini_client
from utils.pricing_loader import (
    get_pricing_calculator,
    PRICING_ENABLED,
    USD_TO_TWD
)

# 導入錯誤處理模組
try:
    from gemini_error_handler import (
        retry_on_error, APIError, FileProcessingError, NetworkError,
        ErrorFormatter, RecoveryManager, ErrorLogger, suggest_solutions
    )
    ERROR_HANDLING_ENABLED = True
except ImportError:
    ERROR_HANDLING_ENABLED = False
    console_temp = Console()
    console_temp.print("[#DDA0DD]提示：gemini_error_handler.py 不存在，進階錯誤處理已停用[/#DDA0DD]")

# 導入影片預處理模組
try:
    from gemini_video_preprocessor import VideoPreprocessor
    PREPROCESSOR_AVAILABLE = True
except ImportError:
    PREPROCESSOR_AVAILABLE = False

# 導入預防性驗證模組
try:
    from gemini_validator import (
        PreflightChecker,
        ParameterValidator,
        ContentPolicyChecker,
        ValidationLevel
    )
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False

# 初始化 API 客戶端
client = get_gemini_client()

# Console
console = Console()

# 初始化錯誤處理（如果啟用）
error_logger = None
recovery_manager = None
if ERROR_HANDLING_ENABLED:
    error_logger = ErrorLogger()
    recovery_manager = RecoveryManager()

# 支援的模型
MODELS = {
    '1': ('veo-3.1-generate-preview', 'Veo 3.1 - 最高品質 (720p/1080p, 8秒)'),
    '2': ('veo-3.1-fast-generate-preview', 'Veo 3.1 Fast - 快速生成'),
    '3': ('veo-3.0-generate-preview', 'Veo 3.0 - 穩定版本'),
}

DEFAULT_MODEL = 'veo-3.1-generate-preview'
# 使用統一輸出目錄配置
from utils.path_manager import get_video_dir
OUTPUT_DIR = str(get_video_dir('veo'))


def select_model() -> str:
    """選擇 Veo 模型"""
    console.print(safe_t('common.message', fallback='\n[#DDA0DD]請選擇 Veo 模型：[/#DDA0DD]'))
    for key, (model_name, description) in MODELS.items():
        console.print(f"  {key}. {description}")

    choice = console.input("\n請選擇 (1-3, 預設=1): ").strip() or '1'

    if choice in MODELS:
        return MODELS[choice][0]
    else:
        console.print(safe_t('common.message', fallback='[#DDA0DD]無效選擇，使用預設模型[/#DDA0DD]'))
        return DEFAULT_MODEL


def generate_video(
    prompt: str,
    model: str = DEFAULT_MODEL,
    negative_prompt: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    video_to_extend: Optional[str] = None,
    aspect_ratio: str = "16:9",
    duration: int = 8,
    show_cost: bool = True
) -> str:
    """
    生成影片

    Args:
        prompt: 影片描述提示
        model: 使用的模型
        negative_prompt: 負面提示（避免的內容）
        reference_images: 參考圖片路徑列表（最多3張）
        video_to_extend: 要延伸的影片路徑
        aspect_ratio: 長寬比 (16:9, 9:16, 1:1)
        duration: 影片長度（秒）
        show_cost: 是否顯示成本資訊（預設 True）

    Returns:
        生成的影片檔案路徑
    """
    console.print("\n[#DDA0DD]" + "=" * 60 + "[/#DDA0DD]")
    console.print(safe_t('common.generating', fallback='[bold #DDA0DD]🎬 Veo 影片生成[/bold #DDA0DD]'))
    console.print("[#DDA0DD]" + "=" * 60 + "[/#DDA0DD]\n")

    console.print(safe_t('common.message', fallback='[#DDA0DD]模型：[/#DDA0DD] {model}', model=model))
    console.print(safe_t('common.message', fallback='[#DDA0DD]提示：[/#DDA0DD] {prompt}', prompt=prompt))
    if negative_prompt:
        console.print(safe_t('common.message', fallback='[#DDA0DD]負面提示：[/#DDA0DD] {negative_prompt}', negative_prompt=negative_prompt))
    console.print(safe_t('common.message', fallback='[#DDA0DD]長寬比：[/#DDA0DD] {aspect_ratio}', aspect_ratio=aspect_ratio))
    console.print(safe_t('common.message', fallback='[#DDA0DD]長度：[/#DDA0DD] {duration} 秒', duration=duration))

    # 初始化計價器（如果啟用）
    pricing_calc = None
    if PRICING_ENABLED and show_cost:
        pricing_calc = PricingCalculator()
        cost, details = pricing_calc.calculate_video_generation_cost(model, duration)
        console.print(safe_t('common.message', fallback='\n[#DDA0DD]💰 費用預估：[/#DDA0DD]'))
        console.print(f"  NT${cost * USD_TO_TWD:.2f} (${cost:.4f} USD)")
        console.print(safe_t('common.message', fallback='  單價：NT${per_second_twd}/秒 (${details['per_second_rate']:.2f} USD/秒)', per_second_twd=details["per_second_rate"] * USD_TO_TWD, details['per_second_rate']:.2f=details['per_second_rate']))
        console.print()

    # 🔍 預防性驗證（避免浪費時間和金錢）
    if VALIDATION_AVAILABLE:
        console.print(safe_t('common.message', fallback='[#DDA0DD]🔍 執行參數驗證...[/#DDA0DD]'))

        # 驗證參數
        validation_results = ParameterValidator.validate_veo_parameters(
            prompt=prompt,
            duration=duration,
            resolution="1080p",  # Veo 默認最高品質
            aspect_ratio=aspect_ratio
        )

        # 內容政策檢查
        if prompt:
            content_check = ContentPolicyChecker.check_prompt(prompt)
            validation_results.extend(content_check)

        # 檢查是否有錯誤
        errors = [r for r in validation_results if r.level == ValidationLevel.ERROR]
        warnings = [r for r in validation_results if r.level == ValidationLevel.WARNING]

        if errors:
            console.print(safe_t('error.failed', fallback='\n[dim #DDA0DD]❌ 參數驗證失敗：[/red]'))

            # 檢查是否為時長超過限制
            duration_error = None
            for err in errors:
                console.print(f"  ❌ {err.message}")
                if err.suggestions:
                    console.print(safe_t('common.message', fallback='     [#DDA0DD]建議：[/#DDA0DD]'))
                    for sug in err.suggestions:
                        console.print(f"       → {sug}")

                if "時長超過限制" in err.message:
                    duration_error = err

            # 🎯 智能引導：自動切換到 Flow Engine
            if duration_error and duration > 8:
                console.print(safe_t('common.message', fallback='\n[bold #DDA0DD]💡 智能解決方案[/bold #DDA0DD]'))
                console.print(safe_t('common.generating', fallback='[#DDA0DD]您想生成 {duration} 秒的影片，但 Veo 3.1 限制為 8 秒。[/#DDA0DD]', duration=duration))
                console.print(safe_t('common.generating', fallback='[#DDA0DD]我可以自動使用 Flow Engine 分段生成並合併！[/#DDA0DD]\n'))

                from rich.prompt import Confirm
                if Confirm.ask("是否切換到 Flow Engine？", default=True):
                    console.print(safe_t('common.completed', fallback='\n[#DA70D6]✅ 正在切換到 Flow Engine...[/green]\n'))

                    # 導入 Flow Engine
                    try:
                        from gemini_flow_engine import FlowEngine

                        # 初始化 Flow Engine
                        engine = FlowEngine(
                            resolution=resolution if 'resolution' in locals() else "1080p",
                            aspect_ratio=aspect_ratio
                        )

                        # 使用自然語言生成分段
                        console.print(safe_t('common.message', fallback='[#DDA0DD]🤖 使用 AI 自動規劃分段...[/#DDA0DD]\n'))
                        segments = engine.natural_language_to_segments(
                            user_description=prompt,
                            total_duration=duration
                        )

                        # 生成影片
                        final_video = engine.generate_multi_segment_video(
                            segments=segments,
                            veo_model=model
                        )

                        console.print(safe_t('common.completed', fallback='\n[bold green]✅ Flow Engine 生成完成！[/bold green]'))
                        console.print(safe_t('common.message', fallback='[#DDA0DD]影片路徑：[/#DDA0DD] {final_video}', final_video=final_video))

                        return final_video

                    except ImportError:
                        console.print(safe_t('error.failed', fallback='[dim #DDA0DD]❌ Flow Engine 模組不存在[/red]'))
                        console.print(safe_t('common.message', fallback='[#DDA0DD]請確認 gemini_flow_engine.py 存在[/#DDA0DD]'))
                        raise ValueError("無法使用 Flow Engine")
                else:
                    console.print(safe_t('common.message', fallback='\n[#DDA0DD]請調整時長至 8 秒或更短後重試[/#DDA0DD]'))

            raise ValueError("參數驗證失敗，請修復上述問題後重試")

        if warnings:
            console.print(safe_t('common.warning', fallback='\n[#DDA0DD]⚠️  發現警告：[/#DDA0DD]'))
            for warn in warnings:
                console.print(f"  ⚠️  {warn.message}")

        console.print(safe_t('common.completed', fallback='[#DA70D6]✅ 參數驗證通過[/green]\n'))

    # 準備配置
    config_params = {
        "aspect_ratio": aspect_ratio,
        "duration_seconds": duration
    }

    if negative_prompt:
        config_params["negative_prompt"] = negative_prompt

    # 處理參考圖片
    if reference_images:
        console.print(safe_t('common.message', fallback='[#DDA0DD]參考圖片：[/#DDA0DD] {len(reference_images)} 張', reference_images_count=len(reference_images)))
        uploaded_images = []
        for img_path in reference_images[:3]:  # 最多3張
            if os.path.isfile(img_path):
                uploaded_img = client.files.upload(file=img_path)
                uploaded_images.append(uploaded_img)
                console.print(f"  ✓ {os.path.basename(img_path)}")
        config_params["reference_images"] = uploaded_images

    config = types.GenerateVideosConfig(**config_params)

    # 開始生成
    console.print(safe_t('common.generating', fallback='\n[#DDA0DD]⏳ 開始生成影片...[/#DDA0DD]\n'))

    # 生成任務 ID（用於恢復）
    task_id = f"veo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        if video_to_extend:
            # 延伸現有影片
            console.print(safe_t('common.message', fallback='[#DDA0DD]延伸影片：[/#DDA0DD] {video_to_extend}', video_to_extend=video_to_extend))
            if os.path.isfile(video_to_extend):
                video_file = client.files.upload(file=video_to_extend)
                operation = client.models.generate_videos(
                    model=model,
                    prompt=prompt,
                    video=video_file,
                    config=config
                )
            else:
                error = FileProcessingError(
                    f"找不到影片檔案: {video_to_extend}",
                    file_path=video_to_extend,
                    suggestions=[
                        "檢查檔案路徑是否正確",
                        "確認檔案是否存在",
                        "檢查檔案權限"
                    ]
                ) if ERROR_HANDLING_ENABLED else FileNotFoundError(f"找不到影片檔案: {video_to_extend}")
                raise error
        else:
            # 從文字生成影片
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                config=config
            )

        # 顯示進度
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("生成中...", total=100)

            poll_count = 0
            while not operation.done:
                time.sleep(10)
                operation = client.operations.get(operation)
                poll_count += 1

                # 簡單的進度估算（假設平均需要2-3分鐘）
                estimated_progress = min(95, poll_count * 5)
                progress.update(task, completed=estimated_progress)

            progress.update(task, completed=100, description="[#DA70D6]✓ 生成完成[/green]")

        # 獲取生成的影片
        if not operation.result or not operation.result.generated_videos:
            error = APIError(
                "生成失敗：沒有返回影片",
                api_name="Veo",
                suggestions=[
                    "檢查提示詞是否符合內容政策",
                    "確認 API 配額是否足夠",
                    "嘗試調整提示詞或參數",
                    "稍後再試"
                ]
            ) if ERROR_HANDLING_ENABLED else ValueError("生成失敗：沒有返回影片")
            raise error

        generated_video = operation.result.generated_videos[0]

        # 確保輸出目錄存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 下載影片
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"veo_video_{timestamp}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        console.print(safe_t('common.message', fallback='\n[#DDA0DD]💾 下載影片中...[/#DDA0DD]'))

        # 下載檔案
        with open(output_path, 'wb') as f:
            video_data = client.files.download(file=generated_video.video)
            f.write(video_data)

        console.print(safe_t('common.completed', fallback='[#DA70D6]✓ 影片已儲存：{output_path}[/green]', output_path=output_path))

        # 顯示影片資訊
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        console.print(safe_t('common.message', fallback='\n[#DDA0DD]📊 影片資訊：[/#DDA0DD]'))
        console.print(safe_t('common.message', fallback='  檔案大小：{file_size} MB', file_size=file_size))
        console.print(safe_t('common.saving', fallback='  儲存路徑：{output_path}', output_path=output_path))

        # 顯示實際成本
        if pricing_calc:
            pricing_calc.print_cost_summary(details)

        # 成功完成，刪除恢復檢查點（如果有）
        if recovery_manager:
            recovery_manager.delete_checkpoint(task_id)

        return output_path

    except Exception as e:
        # 使用增強的錯誤處理
        if ERROR_HANDLING_ENABLED:
            # 記錄錯誤
            if error_logger:
                error_logger.log_error(e, context={
                    'model': model,
                    'prompt': prompt[:100],  # 僅記錄前 100 字元
                    'duration': duration,
                    'aspect_ratio': aspect_ratio
                })

            # 顯示詳細錯誤訊息
            ErrorFormatter.display_error(e, show_traceback=False)

            # 保存恢復檢查點
            if recovery_manager:
                recovery_manager.save_checkpoint(
                    task_id=task_id,
                    task_type="veo_generation",
                    state={
                        'model': model,
                        'prompt': prompt,
                        'negative_prompt': negative_prompt,
                        'aspect_ratio': aspect_ratio,
                        'duration': duration
                    },
                    completed_steps=[],
                    total_steps=1,
                    error=e
                )
        else:
            # 基本錯誤處理
            console.print(safe_t('error.failed', fallback='\n[dim #DDA0DD]❌ 生成失敗：{e}[/red]', e=e))

        raise


def interactive_mode():
    """互動式影片生成模式"""
    console.print(safe_t('common.generating', fallback='\n[bold #DDA0DD]🎬 Veo 互動式影片生成[/bold #DDA0DD]\n'))

    # 初始化預處理器（如果可用）
    preprocessor = None
    if PREPROCESSOR_AVAILABLE:
        try:
            preprocessor = VideoPreprocessor()
            console.print(safe_t('common.completed', fallback='[#DA70D6]✓ 影片預處理功能已啟用[/green]'))
        except Exception as e:
            console.print(safe_t('error.failed', fallback='[#DDA0DD]⚠ 預處理功能初始化失敗：{e}[/#DDA0DD]', e=e))

    # 選擇模型
    model = select_model()

    while True:
        console.print("\n" + "=" * 60)

        # 獲取提示
        prompt = console.input("\n[#DDA0DD]請描述您想生成的影片（或輸入 'exit' 退出）：[/#DDA0DD]\n").strip()

        if not prompt or prompt.lower() in ['exit', 'quit', '退出']:
            console.print(safe_t('common.message', fallback='\n[#DA70D6]再見！[/green]'))
            break

        # 負面提示（可選）
        negative_prompt = console.input("\n[#DDA0DD]負面提示（避免的內容，可留空）：[/#DDA0DD]\n").strip()
        if not negative_prompt:
            negative_prompt = None

        # 長寬比
        console.print(safe_t('common.message', fallback='\n[#DDA0DD]選擇長寬比：[/#DDA0DD]'))
        console.print(safe_t('common.message', fallback='  1. 16:9 (橫向)'))
        console.print(safe_t('common.message', fallback='  2. 9:16 (直向)'))
        console.print(safe_t('common.message', fallback='  3. 1:1 (方形)'))
        aspect_choice = console.input("\n請選擇 (1-3, 預設=1): ").strip() or '1'

        aspect_ratios = {'1': '16:9', '2': '9:16', '3': '1:1'}
        aspect_ratio = aspect_ratios.get(aspect_choice, '16:9')

        # 影片長度
        duration_input = console.input("\n[#DDA0DD]影片長度（秒，預設=8）：[/#DDA0DD] ").strip()
        duration = int(duration_input) if duration_input.isdigit() else 8

        # 參考圖片（可選）
        ref_images_input = console.input("\n[#DDA0DD]參考圖片路徑（用逗號分隔，最多3張，可留空）：[/#DDA0DD]\n").strip()
        reference_images = None
        if ref_images_input:
            reference_images = [img.strip() for img in ref_images_input.split(',')]

        # 影片延伸（可選）
        video_to_extend = console.input("\n[#DDA0DD]要延伸的影片路徑（可留空）：[/#DDA0DD]\n").strip()
        if not video_to_extend:
            video_to_extend = None
        elif preprocessor and os.path.isfile(video_to_extend):
            # 檢查影片大小，如果超過 2GB 提示壓縮
            try:
                video_info = preprocessor.get_video_info(video_to_extend)
                if video_info['size_mb'] > 1900:
                    console.print(safe_t('common.message', fallback='\n[#DDA0DD]⚠ 影片大小 {video_info['size_mb']} MB 超過建議值[/#DDA0DD]', video_info['size_mb']:.2f=video_info['size_mb']))
                    compress_choice = console.input("[#DDA0DD]是否壓縮影片？(Y/n): [/#DDA0DD]").strip().lower()
                    if compress_choice != 'n':
                        video_to_extend = preprocessor.compress_for_api(video_to_extend)
            except Exception as e:
                console.print(safe_t('common.message', fallback='[#DDA0DD]⚠ 無法檢查影片：{e}[/#DDA0DD]', e=e))

        try:
            # 生成影片
            output_path = generate_video(
                prompt=prompt,
                model=model,
                negative_prompt=negative_prompt,
                reference_images=reference_images,
                video_to_extend=video_to_extend,
                aspect_ratio=aspect_ratio,
                duration=duration
            )

            # 詢問是否開啟影片
            open_video = console.input("\n[#DDA0DD]要開啟影片嗎？(y/N): [/#DDA0DD]").strip().lower()
            if open_video == 'y':
                os.system(f'open "{output_path}"')

            # 詢問是否繼續
            continue_gen = console.input("\n[#DDA0DD]繼續生成另一個影片？(Y/n): [/#DDA0DD]").strip().lower()
            if continue_gen == 'n':
                break

        except Exception as e:
            console.print(safe_t('error.failed', fallback='\n[dim #DDA0DD]錯誤：{e}[/red]', e=e))
            continue_gen = console.input("\n[#DDA0DD]繼續嘗試？(Y/n): [/#DDA0DD]").strip().lower()
            if continue_gen == 'n':
                break


def main():
    """主程式"""
    console.print(safe_t('common.generating', fallback='[bold #DDA0DD]Gemini Veo 3.1 影片生成工具[/bold #DDA0DD]\n'))

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
            output_path = generate_video(prompt=prompt, model=model)

            # 自動開啟影片
            console.print(safe_t('common.message', fallback='\n[#DDA0DD]🎥 開啟影片中...[/#DDA0DD]'))
            os.system(f'open "{output_path}"')

        except Exception as e:
            console.print(safe_t('error.failed', fallback='\n[dim #DDA0DD]錯誤：{e}[/red]', e=e))
            sys.exit(1)


if __name__ == "__main__":
    main()
