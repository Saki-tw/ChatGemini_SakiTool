#!/usr/bin/env python3
"""
Gemini Flow Engine - 核心引擎
實作類似 Google Flow 的自然語言影片編輯功能
"""
import os
import json
import tempfile
import shutil
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from rich.console import Console
from utils.i18n import safe_t
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from google.genai import types

# 共用工具模組
from utils.api_client import get_gemini_client, get_api_key
from utils.pricing_loader import get_pricing_calculator, PRICING_ENABLED
from gemini_pricing import USD_TO_TWD

# 導入記憶體管理模組
from gemini_memory_manager import (
    process_video_chunked,
    get_video_duration,
    MemoryPoolManager,
    ParallelProcessor
)

# 導入相關模組
from gemini_video_preprocessor import VideoPreprocessor
from gemini_video_compositor import VideoCompositor

# 導入錯誤處理模組
try:
    from gemini_error_handler import (
        retry_on_error,
        RecoveryManager,
        APIError,
        VideoProcessingError,
        ErrorFormatter,
        ErrorLogger
    )
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    # 如果錯誤處理模組不存在,定義基本異常
    ERROR_HANDLING_AVAILABLE = False
    class APIError(Exception):
        pass
    class VideoProcessingError(Exception):
        pass
    class RecoveryManager:
        def __init__(self):
            pass
    class ErrorLogger:
        def __init__(self):
            pass
    def retry_on_error(*args, **kwargs):
        """Stub decorator when error handling is not available"""
        def decorator(func):
            return func
        return decorator

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
    class PreflightChecker:
        @staticmethod
        def run_full_check(*args, **kwargs):
            return []
    class ParameterValidator:
        @staticmethod
        def validate_veo_parameters(*args, **kwargs):
            return []
    class ContentPolicyChecker:
        @staticmethod
        def check_compliance(*args, **kwargs):
            return []

# Console
console = Console()


@dataclass
class SegmentPlan:
    """分段計畫資料結構"""
    duration: int              # 片段時長（秒）
    prompt: str                # Veo 提示詞
    scene_id: str              # 場景識別碼
    order: int                 # 順序
    reference_image: Optional[str] = None  # 參考圖片路徑（選用）


class FlowEngine:
    """Flow 功能引擎"""

    def __init__(
        self,
        pricing_calculator: Optional[PricingCalculator] = None,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9"
    ):
        """初始化 Flow 引擎

        Args:
            pricing_calculator: 計價計算器（選用）
            resolution: 影片解析度（'720p' 或 '1080p',預設 1080p）
            aspect_ratio: 影片比例（'16:9' 或 '9:16',預設 16:9）
        """
        # 初始化 API
        self.api_key = get_api_key()
        self.client = get_gemini_client()

        # 初始化輔助模組
        self.preprocessor = VideoPreprocessor()
        self.compositor = VideoCompositor()

        # 初始化錯誤處理模組
        self.recovery_manager = RecoveryManager()
        self.error_logger = ErrorLogger()

        # 初始化計價器
        self.pricing = pricing_calculator or get_pricing_calculator(silent=True)

        # 影片配置
        self.resolution = resolution
        self.aspect_ratio = aspect_ratio

        # 輸出目錄 - 使用統一配置
        from utils.path_manager import get_video_dir
        self.output_dir = str(get_video_dir('flow'))

    def natural_language_to_segments(
        self,
        user_description: str,
        target_duration: int = 30,
        segment_duration: int = 8
    ) -> List[SegmentPlan]:
        """
        使用 Gemini 將自然語言轉換為分段計畫

        Args:
            user_description: 使用者描述
            target_duration: 目標總時長（秒）,預設 30 秒
            segment_duration: 每段時長（秒）,預設 8 秒（Veo 限制）

        Returns:
            List[SegmentPlan]: 分段計畫列表
        """
        console.print(safe_t('flow.engine.analyzing_description', fallback='\n[#E8C4F0]🤖 分析使用者描述...[/#E8C4F0]'))
        console.print(safe_t('flow.engine.description_label', fallback='  描述：{user_description}', user_description=user_description))
        console.print(safe_t('flow.engine.target_duration_label', fallback='  目標時長：{target_duration}秒', target_duration=target_duration))

        # 計算所需片段數量
        num_segments = (target_duration + segment_duration - 1) // segment_duration

        # 構建 Gemini 提示詞
        prompt = safe_t("flow.engine.segment_prompt_template", fallback="""你是一個專業的影片分鏡腳本編寫者。

使用者想要生成一個影片,描述如下：
「{user_description}」

請將這個描述拆解為 {num_segments} 個片段,每個片段 {segment_duration} 秒,確保：
1. 敘事連貫流暢
2. 每個片段都有具體的視覺描述
3. 包含場景、動作、氛圍、光線等細節
4. 適合用於 Veo 影片生成（詳細的提示詞）

請以 JSON 格式回應,格式如下：
{{
  "segments": [
    {{
      "order": 1,
      "scene_id": "intro",
      "prompt": "詳細的視覺描述,包含場景、動作、光線、氛圍等"
    }},
    ...
  ]
}}

只需要回傳 JSON,不要有其他說明文字。""").format(
            user_description=user_description,
            num_segments=num_segments,
            segment_duration=segment_duration
        )

        try:
            # 調用 Gemini API
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )

            # 提取並計算成本
            if PRICING_ENABLED and self.pricing:
                thinking_tokens = getattr(response.usage_metadata, 'thinking_tokens', 0)
                input_tokens = getattr(response.usage_metadata, 'prompt_tokens', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_tokens', 0)

                cost, details = self.pricing.calculate_text_cost(
                    'gemini-2.0-flash-exp',
                    input_tokens,
                    output_tokens,
                    thinking_tokens
                )

                # 顯示成本資訊
                if cost > 0:
                    cost_twd = cost * USD_TO_TWD
                    console.print(safe_t('flow.engine.segment_plan_cost', fallback='[dim]💰 分段計畫生成成本: NT${cost_twd:.2f} (${cost:.6f} USD)[/dim]', cost_twd=cost_twd, cost=cost))
                    console.print(safe_t('flow.engine.token_usage', fallback='[dim]   輸入: {input_tokens:,} tokens, 輸出: {output_tokens:,} tokens, 思考: {thinking_tokens:,} tokens[/dim]', input_tokens=input_tokens, output_tokens=output_tokens, thinking_tokens=thinking_tokens))
                    total_cost_twd = self.pricing.total_cost * USD_TO_TWD
                    total_cost_usd = self.pricing.total_cost
                    console.print(safe_t('flow.engine.accumulated_cost', fallback='[dim]   累計成本: NT${total_cost_twd:.2f} (${total_cost_usd:.6f} USD)[/dim]', total_cost_twd=total_cost_twd, total_cost_usd=total_cost_usd))

            # 解析回應
            response_text = response.text.strip()

            # 移除可能的 markdown 標記
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # 解析 JSON
            data = json.loads(response_text)

            # 轉換為 SegmentPlan 物件
            segments = []
            for seg_data in data['segments']:
                segment = SegmentPlan(
                    duration=segment_duration,
                    prompt=seg_data['prompt'],
                    scene_id=seg_data['scene_id'],
                    order=seg_data['order']
                )
                segments.append(segment)

            console.print(safe_t('flow.engine.segments_generated', fallback='[#B565D8]✓ 已生成 {segments_count} 個片段計畫[/#B565D8]', segments_count=len(segments)))

            # 顯示計畫
            for i, seg in enumerate(segments, 1):
                console.print(safe_t('flow.engine.segment_info', fallback='\n[#E8C4F0]片段 {i} ({scene_id})：[/#E8C4F0]', i=i, scene_id=seg.scene_id))
                console.print(f"  {seg.prompt[:80]}...")

            return segments

        except Exception as e:
            error = APIError(
                safe_t("flow.engine.api_call_failed", fallback="Gemini API 調用失敗：{error}").format(error=str(e)),
                api_name="Gemini 2.0 Flash Exp",
                context={
                    "user_description": user_description[:100],
                    "num_segments": num_segments,
                    "segment_duration": segment_duration
                },
                suggestions=[
                    safe_t("flow.engine.suggestion.check_network", fallback="檢查網路連接是否正常"),
                    safe_t("flow.engine.suggestion.check_api_key", fallback="確認 API 金鑰是否有效"),
                    safe_t("flow.engine.suggestion.check_quota", fallback="查看 API 配額是否足夠"),
                    safe_t("flow.engine.suggestion.use_fallback", fallback="使用備案分段策略繼續執行")
                ],
                cause=e
            )
            self.error_logger.log_error(error)
            ErrorFormatter.display_error(error, show_traceback=False)

            console.print(safe_t('flow.engine.using_fallback_strategy', fallback='[#E8C4F0]使用備案分段策略繼續執行...[/#E8C4F0]'))
            # 返回備案：簡單等分
            return self._create_fallback_segments(
                user_description,
                num_segments,
                segment_duration
            )

    def _create_fallback_segments(
        self,
        description: str,
        num_segments: int,
        segment_duration: int
    ) -> List[SegmentPlan]:
        """創建備案分段（當 API 失敗時）"""
        console.print(safe_t('flow.engine.using_fallback_strategy', fallback='[#E8C4F0]使用備案分段策略...[/#E8C4F0]'))

        segments = []
        for i in range(num_segments):
            segment = SegmentPlan(
                duration=segment_duration,
                prompt=safe_t("flow.engine.fallback_segment", fallback="{description},片段 {num}").format(description=description, num=i+1),
                scene_id=f"segment_{i+1}",
                order=i+1
            )
            segments.append(segment)

        return segments

    def generate_multi_segment_video(
        self,
        segments: List[SegmentPlan],
        output_filename: Optional[str] = None,
        veo_model: str = "veo-3.1-generate-preview",
        show_progress: bool = True
    ) -> str:
        """
        批次生成多段 Veo 影片並合併

        Args:
            segments: 分段計畫列表
            output_filename: 輸出檔名
            veo_model: Veo 模型名稱
            show_progress: 是否顯示進度條

        Returns:
            str: 最終影片路徑
        """
        console.print(safe_t('flow.engine.start_generating_video', fallback='\n[#E8C4F0]🎬 開始生成影片...[/#E8C4F0]'))
        console.print(safe_t('flow.engine.segment_count_label', fallback='  片段數量：{segments_count}', segments_count=len(segments)))
        console.print(safe_t('flow.engine.veo_model_label', fallback='  Veo 模型：{veo_model}', veo_model=veo_model))

        # 🔍 飛行前檢查（預防失敗）
        if VALIDATION_AVAILABLE:
            console.print(safe_t('flow.engine.preflight_check', fallback='\n[#E8C4F0]🔍 執行飛行前檢查...[/#E8C4F0]'))
            preflight_results = PreflightChecker.run_full_check()

            # 檢查是否有錯誤
            errors = [r for r in preflight_results if r.level == ValidationLevel.ERROR]
            warnings = [r for r in preflight_results if r.level == ValidationLevel.WARNING]

            if errors:
                console.print(safe_t('flow.engine.preflight_failed_message', fallback='[dim #E8C4F0]❌ 飛行前檢查失敗,無法繼續執行：[/red]'))
                for err in errors:
                    console.print(f"  ❌ {err.message}")
                    if err.suggestions:
                        console.print(safe_t('flow.engine.suggestions_label', fallback='     [#E8C4F0]建議：[/#E8C4F0]'))
                        for sug in err.suggestions:
                            console.print(f"       → {sug}")
                raise RuntimeError(safe_t("flow.engine.preflight_failed", fallback="飛行前檢查失敗,請修復上述問題後重試"))

            if warnings:
                console.print(safe_t('flow.engine.warnings_found', fallback='[#E8C4F0]⚠️  發現警告（可繼續執行）：[/#E8C4F0]'))
                for warn in warnings:
                    console.print(f"  ⚠️  {warn.message}")

            console.print(safe_t('flow.engine.preflight_passed', fallback='[#B565D8]✅ 飛行前檢查通過[/#B565D8]\n'))

        # 創建任務 ID 用於恢復
        task_id = f"flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 創建臨時目錄
        temp_dir = tempfile.mkdtemp(prefix="flow_segments_")
        segment_paths = []

        try:
            # 保存初始檢查點
            self.recovery_manager.save_checkpoint(
                task_id=task_id,
                task_type="flow_generation",
                state={
                    "segments": [{"order": s.order, "prompt": s.prompt[:50]} for s in segments],
                    "temp_dir": temp_dir,
                    "veo_model": veo_model,
                    "output_filename": output_filename
                },
                completed_steps=[],
                total_steps=len(segments)
            )

            # 批次生成片段
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    safe_t("flow.engine.generating_segments", fallback="[#E8C4F0]生成 {count} 個片段...").format(count=len(segments)),
                    total=len(segments)
                )

                for i, segment in enumerate(segments):
                    segment_num = i + 1
                    segment_prompt_preview = segment.prompt[:60]
                    console.print(safe_t('flow.engine.generating_segment', fallback='\n[#E8C4F0]生成片段 {segment_num}/{segments_count}：{scene_id}[/#E8C4F0]', segment_num=segment_num, segments_count=len(segments), scene_id=segment.scene_id))
                    console.print(safe_t('flow.engine.prompt_preview', fallback='  提示詞：{prompt_preview}...', prompt_preview=segment_prompt_preview))

                    # 調用 Veo API 生成影片
                    try:
                        segment_path = self._generate_veo_video(
                            prompt=segment.prompt,
                            duration=segment.duration,
                            output_path=os.path.join(temp_dir, f"segment_{i+1:03d}.mp4"),
                            model=veo_model,
                            reference_image=segment.reference_image
                        )

                        segment_paths.append(segment_path)
                        console.print(safe_t('flow.engine.generation_complete', fallback='  [#B565D8]✓ 生成完成[/#B565D8]'))

                        # 更新檢查點
                        self.recovery_manager.save_checkpoint(
                            task_id=task_id,
                            task_type="flow_generation",
                            state={
                                "segment_paths": segment_paths,
                                "current_segment": i + 1,
                                "temp_dir": temp_dir
                            },
                            completed_steps=[f"segment_{i+1}"],
                            total_steps=len(segments)
                        )

                    except Exception as e:
                        # 保存失敗檢查點
                        error = VideoProcessingError(
                            safe_t("flow.engine.segment_generation_failed", fallback="片段 {current}/{total} 生成失敗").format(current=i+1, total=len(segments)),
                            context={
                                "segment_id": segment.scene_id,
                                "segment_order": i + 1,
                                "total_segments": len(segments),
                                "completed_segments": len(segment_paths),
                                "prompt": segment.prompt[:100],
                                "task_id": task_id
                            },
                            suggestions=[
                                safe_t("flow.engine.suggestion.resume_task", fallback="使用指令恢復任務：python gemini_chat.py recovery resume {task_id}").format(task_id=task_id),
                                safe_t("flow.engine.suggestion.check_segments", fallback="檢查已生成的片段保存在：{temp_dir}").format(temp_dir=temp_dir),
                                safe_t("flow.engine.suggestion.simplify_prompt", fallback="嘗試簡化提示詞後重新生成"),
                                safe_t("flow.engine.suggestion.check_logs", fallback="查看錯誤日誌以了解詳情")
                            ],
                            cause=e
                        )
                        self.recovery_manager.save_checkpoint(
                            task_id=task_id,
                            task_type="flow_generation",
                            state={
                                "segment_paths": segment_paths,
                                "failed_segment": i + 1,
                                "temp_dir": temp_dir
                            },
                            completed_steps=[f"segment_{j+1}" for j in range(i)],
                            total_steps=len(segments),
                            error=error
                        )
                        self.error_logger.log_error(error)
                        ErrorFormatter.display_error(error)
                        raise error

                    progress.update(task, advance=1)

            # 合併所有片段
            console.print(safe_t('flow.engine.merging_segments', fallback='\n[#E8C4F0]🎞️  合併 {segment_paths_count} 個片段...[/#E8C4F0]', segment_paths_count=len(segment_paths)))

            if output_filename is None:
                output_filename = safe_t("flow.engine.output_filename", fallback="flow_video_{segments_count}segments.mp4").format(segments_count=len(segments))

            output_path = os.path.join(self.output_dir, output_filename)

            final_video = self.compositor.concat_segments(
                video_paths=segment_paths,
                output_path=output_path,
                transition="none"  # 固定使用無損合併（禁止過渡效果）
            )

            console.print(safe_t('flow.engine.video_generation_complete', fallback='\n[#B565D8]✅ 影片生成完成！[/#B565D8]'))
            total_duration = len(segments) * segments[0].duration
            console.print(safe_t('flow.engine.total_duration_label', fallback='  總時長：{total_duration} 秒', total_duration=total_duration))
            console.print(safe_t('flow.engine.save_path_label', fallback='  儲存路徑：{final_video}', final_video=final_video))

            # 標記任務完成並刪除檢查點
            self.recovery_manager.delete_checkpoint(task_id)

            return final_video

        except Exception as e:
            # 錯誤已在內部處理,僅記錄到日誌
            if not isinstance(e, (APIError, VideoProcessingError)):
                error = VideoProcessingError(
                    safe_t("flow.engine.unexpected_error", fallback="影片生成過程發生未預期錯誤"),
                    context={"task_id": task_id},
                    suggestions=[
                        safe_t("flow.engine.suggestion.resume_task", fallback="使用指令恢復任務：python gemini_chat.py recovery resume {task_id}").format(task_id=task_id),
                        safe_t("flow.engine.suggestion.check_logs", fallback="查看錯誤日誌以了解詳情"),
                        safe_t("flow.engine.suggestion.check_dependencies", fallback="確認所有依賴模組正常運作")
                    ],
                    cause=e
                )
                self.error_logger.log_error(error)
                ErrorFormatter.display_error(error)
            raise

        finally:
            # 清理臨時檔案
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    console.print(safe_t('flow.engine.temp_files_cleaned', fallback='[dim]已清理臨時檔案：{temp_dir}[/dim]', temp_dir=temp_dir))
                except (OSError, PermissionError) as e:
                    # 改善錯誤處理：記錄但不中斷
                    cleanup_error = FileProcessingError(
                        safe_t("flow.engine.cleanup_failed", fallback="臨時檔案清理失敗"),
                        file_path=temp_dir,
                        context={"error_type": e.__class__.__name__},
                        suggestions=[
                            safe_t("flow.engine.suggestion.manual_delete", fallback="手動刪除臨時目錄：rm -rf {temp_dir}").format(temp_dir=temp_dir),
                            safe_t("flow.engine.suggestion.check_permissions", fallback="檢查檔案權限是否正確"),
                            safe_t("flow.engine.suggestion.check_disk_space", fallback="確認磁碟空間充足")
                        ],
                        cause=e
                    )
                    self.error_logger.log_error(cleanup_error)
                    console.print(safe_t('flow.engine.cleanup_warning', fallback='[#E8C4F0]警告：無法清理臨時檔案 {temp_dir},請手動刪除[/#E8C4F0]', temp_dir=temp_dir))

    @retry_on_error(
        max_retries=3,
        delay=2.0,
        backoff=2.0,
        exceptions=(APIError, Exception)
    )
    def _generate_veo_video(
        self,
        prompt: str,
        duration: int,
        output_path: str,
        model: str,
        reference_image: Optional[str] = None
    ) -> str:
        """
        調用 Veo API 生成單段影片（帶重試機制）

        Args:
            prompt: 提示詞
            duration: 時長（秒）
            output_path: 輸出路徑
            model: 模型名稱
            reference_image: 參考圖片（選用）

        Returns:
            str: 生成的影片路徑
        """
        # 🔍 預防性參數驗證
        if VALIDATION_AVAILABLE:
            validation_results = ParameterValidator.validate_veo_parameters(
                prompt=prompt,
                duration=duration,
                resolution=self.resolution,
                aspect_ratio=self.aspect_ratio
            )

            # 檢查是否有錯誤
            errors = [r for r in validation_results if r.level == ValidationLevel.ERROR]
            if errors:
                error_msg = safe_t("flow.engine.validation_failed", fallback="參數驗證失敗：\n")
                for err in errors:
                    error_msg += f"  ❌ {err.message}\n"
                    if err.suggestions:
                        error_msg += safe_t("flow.engine.suggestions", fallback="     建議：\n")
                        for sug in err.suggestions:
                            error_msg += f"       → {sug}\n"

                raise ValueError(error_msg.strip())

        try:
            # 構建請求配置（包含解析度與比例）
            # ✅ 根據是否使用參考圖片設置 person_generation
            if reference_image and os.path.exists(reference_image):
                # Image-to-video 模式必須使用 "allow_adult"（Gemini API 限制）
                person_gen = "allow_adult"
            else:
                # Text-to-video 模式使用 "allow_all"
                person_gen = "allow_all"

            config = types.GenerateVideoConfig(
                aspectRatio=self.aspect_ratio,  # 16:9 或 9:16
                resolution=self.resolution,      # 720p 或 1080p
                personGeneration=person_gen,     # ✅ 人物生成控制
                generation_config=types.VideoGenerationConfig(
                    image_generation_config=types.ImageGenerationConfig(
                        seed=None  # 隨機種子
                    )
                )
            )

            # 如果有參考圖片,使用 image-to-video
            if reference_image and os.path.exists(reference_image):
                # 上傳參考圖片
                with open(reference_image, 'rb') as f:
                    image_data = f.read()

                # 調用 image-to-video
                response = self.client.models.generate_video(
                    model=model,
                    prompt=prompt,
                    image=image_data,
                    config=config
                )
            else:
                # 調用 text-to-video
                response = self.client.models.generate_video(
                    model=model,
                    prompt=prompt,
                    config=config
                )

            # 儲存影片
            with open(output_path, 'wb') as f:
                f.write(response.video_data)

            return output_path

        except Exception as e:
            error = APIError(
                safe_t("flow.engine.veo_generation_failed", fallback="Veo API 影片生成失敗"),
                api_name="Veo 3.1",
                context={
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "duration": f"{duration} 秒",
                    "resolution": self.resolution,
                    "aspect_ratio": self.aspect_ratio,
                    "model": model,
                    "output_path": output_path,
                    "has_reference_image": reference_image is not None
                },
                suggestions=[
                    safe_t("flow.engine.suggestion.check_veo_quota", fallback="檢查 Veo API 配額（https://console.cloud.google.com/）"),
                    safe_t("flow.engine.suggestion.check_content_policy", fallback="確認提示詞是否符合 Veo 內容政策"),
                    safe_t("flow.engine.suggestion.simplify_veo_prompt", fallback="嘗試簡化提示詞：{prompt_preview}...").format(prompt_preview=prompt[:50]),
                    safe_t("flow.engine.suggestion.check_duration", fallback="檢查影片時長設定（當前：{duration} 秒,建議：≤8 秒）").format(duration=duration),
                    safe_t("flow.engine.suggestion.check_api_status", fallback="查看 Gemini API 狀態頁面"),
                    safe_t("flow.engine.suggestion.wait_retry", fallback="等待 2-5 分鐘後重試（API 可能暫時過載）")
                ],
                cause=e
            )
            self.error_logger.log_error(error)
            raise error

    def generate_from_description(
        self,
        description: str,
        target_duration: int = 30,
        output_filename: Optional[str] = None,
        show_cost: bool = True
    ) -> str:
        """
        從自然語言描述生成完整影片（一鍵生成）

        Args:
            description: 自然語言描述
            target_duration: 目標時長（秒）
            output_filename: 輸出檔名
            show_cost: 是否顯示成本資訊

        Returns:
            str: 最終影片路徑
        """
        console.print("\n" + "="*60)
        console.print(safe_t('flow.engine.flow_engine_title', fallback='[bold #E8C4F0]Gemini Flow Engine - 自然語言影片生成[/bold #E8C4F0]'))
        console.print("="*60)
        console.print(safe_t('flow.engine.video_config', fallback='[#E8C4F0]影片配置：{resolution} @ {aspect_ratio} (24fps)[/#E8C4F0]', resolution=self.resolution, aspect_ratio=self.aspect_ratio))

        # 顯示費用預估
        if self.pricing and show_cost:
            estimate = self.pricing.estimate_flow_cost(target_duration)
            console.print(safe_t('flow.engine.cost_estimate_title', fallback='\n[#E8C4F0]💰 費用預估：[/#E8C4F0]'))
            console.print(safe_t('flow.engine.target_duration_estimate', fallback='  目標時長：{target_duration} 秒', target_duration=estimate["target_duration"]))
            console.print(safe_t('flow.engine.actual_duration_estimate', fallback='  實際時長：{actual_duration} 秒（{num_segments} 段）', actual_duration=estimate["actual_duration"], num_segments=estimate["num_segments"]))
            planning_cost = estimate['breakdown']['planning']
            veo_cost = estimate['breakdown']['veo']
            total_cost = estimate['breakdown']['total']
            console.print(safe_t('flow.engine.planning_cost_label', fallback='  Gemini 分段計畫：{planning_cost}', planning_cost=planning_cost))
            console.print(safe_t('flow.engine.veo_cost_label', fallback='  Veo 影片生成：{veo_cost}', veo_cost=veo_cost))
            console.print(safe_t('flow.engine.total_cost_estimate', fallback='  [bold]預估總成本：{total_cost}[/bold]', total_cost=total_cost))
            console.print()

            # 詢問是否繼續
            user_confirm = input(safe_t("flow.engine.confirm_prompt", fallback="是否繼續生成？(y/n): ")).strip().lower()
            if user_confirm != 'y':
                console.print(safe_t('flow.engine.generation_cancelled', fallback='[#E8C4F0]已取消生成[/#E8C4F0]'))
                return None

        # 第一步：生成分段計畫
        segments = self.natural_language_to_segments(
            user_description=description,
            target_duration=target_duration
        )

        # 第二步：批次生成並合併
        final_video = self.generate_multi_segment_video(
            segments=segments,
            output_filename=output_filename
        )

        # 顯示實際費用
        if self.pricing and show_cost:
            cost, details = self.pricing.calculate_flow_engine_cost(
                target_duration=target_duration,
                segment_duration=8
            )
            self.pricing.print_cost_summary(details)

        return final_video


def main():
    """測試用主程式"""
    import sys

    if len(sys.argv) < 2:
        console.print(safe_t('flow.engine.usage_title', fallback='[#E8C4F0]用法：[/#E8C4F0]'))
        console.print('  python gemini_flow_engine.py "影片描述" [時長]')
        console.print(safe_t('flow.engine.example_title', fallback='\n[#E8C4F0]範例：[/#E8C4F0]'))
        console.print('  python gemini_flow_engine.py "一個人走進森林,發現寶藏" 30')
        sys.exit(1)

    description = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    try:
        engine = FlowEngine()
        output = engine.generate_from_description(
            description=description,
            target_duration=duration
        )

        console.print(safe_t('flow.engine.success_message', fallback='\n[bold green]✅ 成功！影片已生成：[/bold green]'))
        console.print(f"   {output}")

    except Exception as e:
        console.print(safe_t('flow.engine.error_message', fallback='\n[dim #E8C4F0]錯誤：{e}[/red]', e=e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
