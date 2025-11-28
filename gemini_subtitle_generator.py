#!/usr/bin/env python3
"""
Gemini 字幕生成模組
提供影片語音辨識、翻譯、字幕檔生成功能
"""
import os
import sys
import subprocess
import tempfile
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console
from utils.i18n import safe_t
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# 導入 Gemini API
from google.genai import types

# 共用工具模組
from utils.api_client import get_gemini_client

# 導入計價模組
from utils.pricing_loader import (
    get_pricing_calculator,
    USD_TO_TWD,
    PRICING_ENABLED
)

# 導入翻譯模組
try:
    from gemini_translator import get_translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

# 導入音訊處理模組
try:
    from gemini_audio_processor import AudioProcessor
    AUDIO_PROCESSOR_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSOR_AVAILABLE = False

# 🔧 任務 1.3：導入上傳輔助模組（整合重試、超時、錯誤處理）
try:
    from gemini_upload_helper import upload_file
    UPLOAD_HELPER_AVAILABLE = True
except ImportError:
    UPLOAD_HELPER_AVAILABLE = False

# 導入統一的錯誤修復建議系統
try:
    from error_fix_suggestions import (
        suggest_video_file_not_found,
        suggest_corrupted_file,
        suggest_missing_stream,
        suggest_json_parse_failed,
        suggest_unsupported_subtitle_format,
        auto_fix_json,
        ErrorLogger
    )
    ERROR_FIX_ENABLED = True
except ImportError:
    ERROR_FIX_ENABLED = False

# 導入 API 重試機制
try:
    from utils.api_retry import with_retry
    API_RETRY_ENABLED = True
except ImportError:
    # 如果未安裝，提供空裝飾器
    def with_retry(operation_name: str, max_retries: int = 3):
        def decorator(func):
            return func
        return decorator
    API_RETRY_ENABLED = False

# Console
console = Console()

# 設定日誌
import logging
logger = logging.getLogger(__name__)

# 初始化錯誤記錄器
error_logger = ErrorLogger() if ERROR_FIX_ENABLED else None


@dataclass
class SubtitleSegment:
    """字幕片段資料結構"""
    index: int                    # 字幕序號
    start_time: float            # 開始時間（秒）
    end_time: float              # 結束時間（秒）
    text: str                    # 字幕文字
    translation: Optional[str] = None  # 翻譯文字（可選）


class SubtitleGenerator:
    """字幕生成器類別"""

    def __init__(self, api_key: Optional[str] = None, pricing_calculator=None):
        """
        初始化字幕生成器

        Args:
            api_key: Gemini API 金鑰，預設從環境變數讀取（傳入時會建立新客戶端）
            pricing_calculator: 計價計算器實例，預設使用全域計價器
        """
        if api_key:
            # 使用自訂 API 金鑰時建立新客戶端
            self.client = get_gemini_client(api_key=api_key, force_new=True)
            self.api_key = api_key
        else:
            # 使用共用客戶端
            self.client = get_gemini_client()
            from utils.api_client import get_api_key
            self.api_key = get_api_key()

        # 初始化計價器
        if pricing_calculator:
            self.pricing_calculator = pricing_calculator
        elif PRICING_ENABLED:
            self.pricing_calculator = get_pricing_calculator(silent=True)
        else:
            self.pricing_calculator = None

        # 初始化音訊處理器
        if AUDIO_PROCESSOR_AVAILABLE:
            self.audio_processor = AudioProcessor()
        else:
            self.audio_processor = None
            console.print(safe_t('common.warning', fallback='[#E8C4F0]警告：gemini_audio_processor 不可用，音訊提取功能受限[/#E8C4F0]'))

        # 初始化翻譯器
        if TRANSLATOR_AVAILABLE:
            self.translator = get_translator()
        else:
            self.translator = None
            console.print(safe_t('common.warning', fallback='[#E8C4F0]警告：gemini_translator 不可用，翻譯功能已停用[/#E8C4F0]'))

        # 輸出目錄 - 使用統一配置
        from utils.path_manager import get_video_dir
        self.output_dir = str(get_video_dir('subtitles'))

        # 驗證依賴
        self._check_dependencies()

    def _check_dependencies(self):
        """檢查必要的依賴"""
        # 檢查 ffmpeg
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(safe_t('common.warning', fallback='[#E8C4F0]警告：未找到 ffmpeg，部分功能可能受限[/#E8C4F0]'))

    def generate_subtitles(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        format: str = "srt",
        translate: bool = False,
        target_language: str = "zh-TW",
        source_language: Optional[str] = None,
        show_cost: bool = True
    ) -> str:
        """
        生成字幕檔案

        Args:
            video_path: 影片檔案路徑
            output_path: 輸出字幕路徑，預設自動生成
            format: 字幕格式 ('srt' 或 'vtt')
            translate: 是否翻譯字幕
            target_language: 目標語言（預設繁體中文）
            source_language: 來源語言（None 表示自動偵測）
            show_cost: 是否顯示成本資訊（預設 True）

        Returns:
            str: 輸出字幕檔案路徑
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            if ERROR_FIX_ENABLED:
                alternative_path = suggest_video_file_not_found(video_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    video_path = alternative_path
                    console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{video_path}[/#B565D8]\n', video_path=video_path))
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            else:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"找不到影片檔案：{video_path}")

        console.print(safe_t('common.generating', fallback='\n[#E8C4F0]📝 生成字幕...[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  影片：{basename}', basename=os.path.basename(video_path)))
        console.print(safe_t('common.message', fallback='  格式：{fmt}', fmt=format.upper()))
        translate_text = '是 (' + target_language + ')' if translate else '否'
        console.print(safe_t('common.message', fallback='  翻譯：{translate_text}', translate_text=translate_text))

        # 步驟 1: 提取音訊
        audio_path = self._extract_audio(video_path)

        # 步驟 2: 語音辨識
        segments = self._transcribe_audio(audio_path, source_language, show_cost=show_cost)

        # 步驟 3: 翻譯（如果需要）
        if translate and self.translator:
            segments = self._translate_segments(segments, target_language)

        # 步驟 4: 生成字幕檔案
        if output_path is None:
            base_name = Path(video_path).stem
            suffix = "_translated" if translate else ""
            extension = format.lower()
            output_path = os.path.join(
                self.output_dir,
                f"{base_name}_subtitles{suffix}.{extension}"
            )

        self._write_subtitle_file(segments, output_path, format)

        # 清理臨時音訊檔案
        if os.path.exists(audio_path):
            os.remove(audio_path)

        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 字幕已生成：{output_path}[/#B565D8]', output_path=output_path))
        return output_path

    def _extract_audio(self, video_path: str) -> str:
        """提取影片音訊"""
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]🎵 步驟 1/4: 提取音訊...[/#E8C4F0]'))

        if self.audio_processor:
            # 使用 AudioProcessor
            audio_path = self.audio_processor.extract_audio(
                video_path,
                format="wav"  # 使用 WAV 格式以獲得最佳語音辨識效果
            )
            return audio_path
        else:
            # 使用 ffmpeg 直接提取
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(
                temp_dir,
                f"{Path(video_path).stem}_audio.wav"
            )

            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",  # 16kHz 採樣率（語音辨識標準）
                "-ac", "1",       # 單聲道
                "-y",
                audio_path
            ]

            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
                console.print(safe_t('common.completed', fallback='[#B565D8]✓ 音訊已提取[/#B565D8]'))
                return audio_path
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)

                # 分析常見錯誤
                error_reason = "未知錯誤"
                is_file_corrupted = False
                is_missing_stream = False
                if "Invalid data found" in stderr or "moov atom not found" in stderr:
                    error_reason = "影片檔案格式錯誤或損壞"
                    is_file_corrupted = True
                elif "Permission denied" in stderr:
                    error_reason = "檔案權限不足"
                elif "does not contain any stream" in stderr or "Invalid argument" in stderr:
                    error_reason = "影片檔案不包含有效音訊串流"
                    is_missing_stream = True
                elif "Disk quota exceeded" in stderr:
                    error_reason = "磁碟空間不足"

                error_msg = f"""音訊提取失敗：{error_reason}

影片檔案：{video_path}
輸出檔案：{audio_path}
ffmpeg 錯誤碼：{e.returncode}

詳細資訊（最後 300 字元）：
{stderr[-300:] if len(stderr) > 300 else stderr}"""

                logger.error(error_msg)

                # 🎯 一鍵修復：顯示檔案損壞修復建議
                if is_file_corrupted:
                    if ERROR_FIX_ENABLED:
                        suggest_corrupted_file(video_path, stderr)
                        if error_logger:
                            error_logger.log_error(
                                error_type="FileCorrupted",
                                file_path=video_path,
                                details={"stderr": stderr[:500]}
                            )
                # 🎯 任務 42: 缺少音訊串流的修復建議
                elif is_missing_stream:
                    if ERROR_FIX_ENABLED:
                        suggest_missing_stream(video_path, missing_type="audio")
                        if error_logger:
                            error_logger.log_error(
                                error_type="MissingAudioStream",
                                file_path=video_path,
                                details={"stderr": stderr[:500]}
                            )

                raise RuntimeError(error_msg.strip())

    @with_retry("語音辨識", max_retries=3)
    def _transcribe_audio(
        self,
        audio_path: str,
        source_language: Optional[str] = None,
        show_cost: bool = True
    ) -> List[SubtitleSegment]:
        """
        使用 Gemini API 進行語音辨識（已包含自動重試）

        Args:
            audio_path: 音訊檔案路徑
            source_language: 來源語言（None 表示自動偵測）
            show_cost: 是否顯示成本資訊（預設 True）

        Returns:
            List[SubtitleSegment]: 字幕片段列表
        """
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]🎤 步驟 2/4: 語音辨識...[/#E8C4F0]'))

        # 🔧 任務 1.3：使用優化的上傳輔助模組（含重試、超時、進度顯示）
        if UPLOAD_HELPER_AVAILABLE:
            # 使用整合的上傳輔助工具
            uploaded_file = upload_file(
                client=self.client,
                file_path=audio_path,
                display_name=os.path.basename(audio_path),
                max_retries=3  # 音訊檔案通常較小，3 次重試足夠
            )
        else:
            # 降級：使用原始上傳方式
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("上傳音訊...", total=None)
                uploaded_file = self.client.files.upload(path=audio_path)
                progress.update(task, completed=100, description="[#B565D8]✓ 上傳完成[/#B565D8]")

        # 顯示成本警告
        console.print(safe_t('common.message', fallback='[dim]📁 檔案已上傳: {uploaded_file.name}[/dim]', name=uploaded_file.name))
        console.print(safe_t('common.analyzing', fallback='[dim]ℹ️  注意:使用此檔案進行分析時會產生 API 成本[/dim]'))

        # 等待處理完成
        while uploaded_file.state.name == "PROCESSING":
            import time
            time.sleep(2)
            uploaded_file = self.client.files.get(name=uploaded_file.name)

        # 使用 Gemini 進行語音辨識並生成時間軸
        prompt = """請將這段音訊轉錄為文字，並提供準確的時間戳記。

輸出格式要求（嚴格的 JSON 格式）：
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "第一句話"
    },
    {
      "start": 2.5,
      "end": 5.0,
      "text": "第二句話"
    }
  ]
}

要求：
1. 每個片段不超過 5 秒
2. 準確標記開始和結束時間（秒數，小數點後一位）
3. 文字轉錄要準確完整
4. 只輸出 JSON，不要其他說明文字
"""

        if source_language:
            prompt += f"\n5. 音訊語言是：{source_language}"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("辨識中...", total=None)

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type=uploaded_file.mime_type
                            ),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ]
            )

            progress.update(task, completed=100, description="[#B565D8]✓ 辨識完成[/#B565D8]")

        # 顯示成本（在解析結果之前）
        if hasattr(response, 'usage_metadata'):
            thinking_tokens = getattr(response.usage_metadata, 'thinking_tokens', 0)
            input_tokens = getattr(response.usage_metadata, 'prompt_tokens', 0) or getattr(response.usage_metadata, 'prompt_token_count', 0)
            output_tokens = getattr(response.usage_metadata, 'candidates_tokens', 0) or getattr(response.usage_metadata, 'candidates_token_count', 0)

            if PRICING_ENABLED and self.pricing_calculator and show_cost and input_tokens > 0:
                try:
                    cost, details = self.pricing_calculator.calculate_text_cost(
                        "gemini-2.5-flash",
                        input_tokens,
                        output_tokens,
                        thinking_tokens
                    )
                    console.print(safe_t('common.message', fallback='[dim]💰 語音辨識成本: NT${cost_twd:.2f} (音訊+提示: {input_tokens:,} tokens, 回應: {output_tokens:,} tokens) | 累計: NT${total_cost_twd:.2f} (${total_cost_usd:.6f})[/dim]', cost_twd=cost * USD_TO_TWD, input_tokens=input_tokens, output_tokens=output_tokens, total_cost_twd=self.pricing_calculator.total_cost * USD_TO_TWD, total_cost_usd=self.pricing_calculator.total_cost))
                except (KeyError, AttributeError, TypeError) as e:
                    logger.warning(f"計價顯示失敗，模型: gemini-2.5-flash, 輸入: {input_tokens}, 輸出: {output_tokens}, 錯誤: {e}")

        # 解析結果
        result_text = response.text.strip()

        # 清理可能的 markdown 代碼塊標記
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(lines[1:-1])  # 移除第一行和最後一行
        result_text = result_text.strip()

        try:
            import json
            data = json.loads(result_text)
            segments_data = data.get("segments", [])

            segments = []
            for idx, seg in enumerate(segments_data, start=1):
                segments.append(SubtitleSegment(
                    index=idx,
                    start_time=float(seg["start"]),
                    end_time=float(seg["end"]),
                    text=seg["text"].strip()
                ))

            console.print(safe_t('common.completed', fallback='[#B565D8]✓ 共識別 {len(segments)} 個片段[/#B565D8]', segments_count=len(segments)))

            # 刪除上傳的檔案
            self.client.files.delete(name=uploaded_file.name)

            return segments

        except json.JSONDecodeError as e:
            # 嘗試使用新版 JSON 修復建議
            try:
                from error_fix_suggestions import suggest_json_parse_failed
                fixed_json = suggest_json_parse_failed(
                    result_text,
                    str(e),
                    "語音辨識"
                )

                # 如果自動修復成功，使用修復後的 JSON 重新解析
                if fixed_json:
                    try:
                        data = json.loads(fixed_json)
                        segments_data = data.get("segments", [])

                        segments = []
                        for idx, seg in enumerate(segments_data, start=1):
                            segments.append(SubtitleSegment(
                                index=idx,
                                start_time=float(seg.get("start", 0)),
                                end_time=float(seg.get("end", 0)),
                                text=seg.get("text", "").strip()
                            ))

                        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 使用修復後的 JSON 成功解析 {len(segments)} 個字幕片段[/#B565D8]', segments_count=len(segments)))

                        # 刪除上傳的檔案
                        if 'uploaded_file' in locals():
                            self.client.files.delete(name=uploaded_file.name)

                        return segments
                    except Exception as parse_error:
                        console.print(safe_t('common.message', fallback='[dim #E8C4F0]✗ 修復後的 JSON 仍無法解析：{parse_error}[/dim]', parse_error=parse_error))

            except ImportError:
                # 降級到舊版錯誤顯示
                console.print(safe_t('error.failed', fallback='[dim #E8C4F0]JSON 解析錯誤：{e}[/dim]', e=e))
                console.print(safe_t('common.message', fallback='[#E8C4F0]原始回應：{result_text}[/#E8C4F0]', result_text=result_text))

            raise RuntimeError("語音辨識結果解析失敗，請參考上述修復建議")

    def _translate_segments(
        self,
        segments: List[SubtitleSegment],
        target_language: str
    ) -> List[SubtitleSegment]:
        """翻譯字幕片段"""
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]🌐 步驟 3/4: 翻譯字幕（目標：{target_language}）...[/#E8C4F0]', target_language=target_language))

        if not self.translator:
            console.print(safe_t('common.warning', fallback='[#E8C4F0]警告：翻譯功能不可用，跳過翻譯步驟[/#E8C4F0]'))
            return segments

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("翻譯中...", total=len(segments))

            for segment in segments:
                # 翻譯文字
                translated = self.translator.translate(
                    segment.text,
                    target_lang=target_language
                )
                segment.translation = translated
                progress.advance(task)

        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 翻譯完成[/#B565D8]'))
        return segments

    def _write_subtitle_file(
        self,
        segments: List[SubtitleSegment],
        output_path: str,
        format: str
    ):
        """寫入字幕檔案"""
        console.print(safe_t('common.generating', fallback='\n[#E8C4F0]💾 步驟 4/4: 生成 {fmt} 檔案...[/#E8C4F0]', fmt=format.upper()))

        format = format.lower()
        if format == "srt":
            self._write_srt(segments, output_path)
        elif format == "vtt":
            self._write_vtt(segments, output_path)
        else:
            try:
                from error_fix_suggestions import suggest_unsupported_subtitle_format
                suggest_unsupported_subtitle_format(format)
            except ImportError:
                pass

            raise ValueError(f"不支援的字幕格式：{format}，請參考上述支援格式")

        console.print(safe_t('common.completed', fallback='[#B565D8]✓ 檔案已生成[/#B565D8]'))

    def _write_srt(self, segments: List[SubtitleSegment], output_path: str):
        """生成 SRT 格式字幕"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                # 序號
                f.write(f"{segment.index}\n")

                # 時間軸
                start = self._format_srt_time(segment.start_time)
                end = self._format_srt_time(segment.end_time)
                f.write(f"{start} --> {end}\n")

                # 文字
                if segment.translation:
                    # 雙語字幕（原文 + 翻譯）
                    f.write(f"{segment.translation}\n")
                    f.write(f"{segment.text}\n")
                else:
                    f.write(f"{segment.text}\n")

                # 空行
                f.write("\n")

    def _write_vtt(self, segments: List[SubtitleSegment], output_path: str):
        """生成 VTT 格式字幕"""
        with open(output_path, 'w', encoding='utf-8') as f:
            # VTT 標頭
            f.write("WEBVTT\n\n")

            for segment in segments:
                # 時間軸
                start = self._format_vtt_time(segment.start_time)
                end = self._format_vtt_time(segment.end_time)
                f.write(f"{start} --> {end}\n")

                # 文字
                if segment.translation:
                    # 雙語字幕
                    f.write(f"{segment.translation}\n")
                    f.write(f"{segment.text}\n")
                else:
                    f.write(f"{segment.text}\n")

                # 空行
                f.write("\n")

    def _format_srt_time(self, seconds: float) -> str:
        """格式化 SRT 時間戳（HH:MM:SS,mmm）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_vtt_time(self, seconds: float) -> str:
        """格式化 VTT 時間戳（HH:MM:SS.mmm）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        將字幕嵌入影片（燒錄字幕）

        Args:
            video_path: 影片路徑
            subtitle_path: 字幕檔案路徑
            output_path: 輸出影片路徑，預設自動生成

        Returns:
            str: 輸出影片路徑
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            if ERROR_FIX_ENABLED:
                alternative_path = suggest_video_file_not_found(video_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    video_path = alternative_path
                    console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{video_path}[/#B565D8]\n', video_path=video_path))
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            else:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"找不到影片檔案：{video_path}")

        if not os.path.isfile(subtitle_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            if ERROR_FIX_ENABLED:
                alternative_path = suggest_video_file_not_found(subtitle_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    subtitle_path = alternative_path
                    console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{subtitle_path}[/#B565D8]\n', subtitle_path=subtitle_path))
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            else:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"找不到字幕檔案：{subtitle_path}")

        console.print(safe_t('common.message', fallback='\n[#E8C4F0]🔥 燒錄字幕...[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  影片：{basename}', basename=os.path.basename(video_path)))
        console.print(safe_t('common.message', fallback='  字幕：{basename}', basename=os.path.basename(subtitle_path)))

        # 設定輸出路徑
        if output_path is None:
            base_name = Path(video_path).stem
            output_path = os.path.join(
                self.output_dir,
                f"{base_name}_with_subtitles.mp4"
            )

        # 轉換字幕路徑為絕對路徑並處理特殊字元
        subtitle_path_abs = os.path.abspath(subtitle_path)
        # Windows 路徑處理
        subtitle_path_abs = subtitle_path_abs.replace('\\', '/')
        subtitle_path_abs = subtitle_path_abs.replace(':', '\\:')

        # 燒錄字幕
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles={subtitle_path_abs}",
            "-c:a", "copy",
            "-y",
            output_path
        ]

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("處理中...", total=None)

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )

                progress.update(task, completed=100, description="[#B565D8]✓ 處理完成[/#B565D8]")

            console.print(safe_t('common.completed', fallback='[#B565D8]✓ 字幕已燒錄：{output_path}[/#B565D8]', output_path=output_path))
            return output_path

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)

            # 分析常見錯誤
            error_reason = "未知錯誤"
            if "Invalid data found" in stderr or "moov atom not found" in stderr:
                error_reason = "影片檔案格式錯誤或損壞"
            elif "Permission denied" in stderr:
                error_reason = "檔案權限不足"
            elif "Fontconfig" in stderr or "font" in stderr.lower():
                error_reason = "字幕字型問題（可能缺少必要字型）"
            elif "invalid" in stderr.lower() and "subtitle" in stderr.lower():
                error_reason = "字幕檔案格式錯誤"
            elif "No such file" in stderr:
                error_reason = "找不到字幕檔案或影片檔案"
            elif "Disk quota exceeded" in stderr:
                error_reason = "磁碟空間不足"

            error_msg = f"""字幕燒錄失敗：{error_reason}

影片檔案：{video_path}
字幕檔案：{subtitle_path}
輸出檔案：{output_path}
ffmpeg 錯誤碼：{e.returncode}

詳細資訊（最後 400 字元）：
{stderr[-400:] if len(stderr) > 400 else stderr}"""

            logger.error(error_msg)

            # 🎯 一鍵修復：根據錯誤類型顯示對應修復建議
            if ERROR_FIX_ENABLED and error_logger:
                # 記錄錯誤
                error_logger.log_error(
                    error_type="SubtitleBurnError",
                    file_path=video_path,
                    details={
                        'subtitle_path': subtitle_path,
                        'error_reason': error_reason,
                        'stderr': stderr[-400:] if len(stderr) > 400 else stderr
                    }
                )

                # 根據錯誤類型顯示修復建議
                if "檔案格式錯誤或損壞" in error_reason:
                    suggest_corrupted_file(video_path, stderr)

            raise RuntimeError(error_msg.strip())


def main():
    """測試用主程式"""
    import sys

    if len(sys.argv) < 2:
        console.print(safe_t('common.message', fallback='[#E8C4F0]用法：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  python gemini_subtitle_generator.py <影片路徑> [選項]'))
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]選項：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  --translate       啟用翻譯'))
        console.print(safe_t('common.message', fallback='  --lang <語言>     目標語言（預設 zh-TW）'))
        console.print(safe_t('common.message', fallback='  --format <格式>   字幕格式 srt/vtt（預設 srt）'))
        console.print(safe_t('common.message', fallback='  --burn            燒錄字幕到影片'))
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]範例：[/#E8C4F0]'))
        console.print("  python gemini_subtitle_generator.py video.mp4")
        console.print("  python gemini_subtitle_generator.py video.mp4 --translate --lang zh-TW")
        console.print("  python gemini_subtitle_generator.py video.mp4 --translate --burn")
        sys.exit(1)

    video_path = sys.argv[1]
    translate = "--translate" in sys.argv
    burn = "--burn" in sys.argv

    # 解析語言參數
    target_lang = "zh-TW"
    if "--lang" in sys.argv:
        lang_idx = sys.argv.index("--lang")
        if lang_idx + 1 < len(sys.argv):
            target_lang = sys.argv[lang_idx + 1]

    # 解析格式參數
    subtitle_format = "srt"
    if "--format" in sys.argv:
        format_idx = sys.argv.index("--format")
        if format_idx + 1 < len(sys.argv):
            subtitle_format = sys.argv[format_idx + 1]

    try:
        generator = SubtitleGenerator()

        # 生成字幕
        subtitle_path = generator.generate_subtitles(
            video_path,
            format=subtitle_format,
            translate=translate,
            target_language=target_lang
        )

        console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 字幕檔案：{subtitle_path}[/#B565D8]', subtitle_path=subtitle_path))

        # 燒錄字幕（如果需要）
        if burn:
            video_with_subs = generator.burn_subtitles(video_path, subtitle_path)
            console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 燒錄影片：{video_with_subs}[/#B565D8]', video_with_subs=video_with_subs))

    except Exception as e:
        console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]錯誤：{e}[/dim]', e=e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
