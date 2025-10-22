#!/usr/bin/env python3
"""
Gemini 音訊處理模組
提供音訊分離、合併、音量調整、淡入淡出等功能
"""
import os
import subprocess
import tempfile
from typing import Optional, List, Tuple
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# 導入統一的錯誤修復建議系統
try:
    from error_fix_suggestions import (
        suggest_ffmpeg_install,
        suggest_video_file_not_found,
        suggest_empty_file,
        suggest_corrupted_file,
        suggest_missing_stream,
        suggest_cannot_get_duration,
        ErrorLogger
    )
    ERROR_FIX_ENABLED = True
except ImportError:
    ERROR_FIX_ENABLED = False

console = Console()

# 設定日誌
import logging
logger = logging.getLogger(__name__)

# 初始化錯誤記錄器
error_logger = ErrorLogger() if ERROR_FIX_ENABLED else None


class AudioProcessor:
    """音訊處理工具類別"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化音訊處理器

        Args:
            output_dir: 輸出目錄，預設為 ~/gemini_videos/audio
        """
        if output_dir is None:
            output_dir = os.path.join(
                os.path.expanduser("~"),
                "gemini_videos",
                "audio"
            )
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # 驗證 ffmpeg
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """檢查 ffmpeg 是否已安裝"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # 🎯 一鍵修復：顯示 ffmpeg 安裝建議
            if ERROR_FIX_ENABLED:
                suggest_ffmpeg_install()
                # 記錄錯誤
                if error_logger:
                    error_logger.log_error(
                        error_type="FFmpegNotInstalled",
                        file_path="N/A",
                        details={"command": "ffmpeg -version", "error": str(e)}
                    )
            else:
                console.print("[red]錯誤：未找到 ffmpeg[/red]")
                console.print("[yellow]請安裝 ffmpeg：brew install ffmpeg (macOS)[/yellow]")

            raise RuntimeError("ffmpeg 未安裝或無法執行，請參考上述建議")

    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        format: str = "aac"
    ) -> str:
        """
        從影片中提取音訊

        Args:
            video_path: 影片路徑
            output_path: 輸出音訊路徑，預設自動生成
            format: 音訊格式 (aac, mp3, wav)

        Returns:
            str: 輸出音訊路徑
        """
        # 驗證輸入檔案
        self._validate_media_file(video_path, required_type="video")

        console.print(f"\n[cyan]🎵 提取音訊...[/cyan]")
        console.print(f"  影片：{os.path.basename(video_path)}")

        # 設定輸出路徑
        if output_path is None:
            base_name = Path(video_path).stem
            extension = self._get_audio_extension(format)
            output_path = os.path.join(
                self.output_dir,
                f"{base_name}_audio.{extension}"
            )

        # 提取音訊
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # 不處理影片
            "-acodec", self._get_audio_codec(format),
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
                task = progress.add_task("提取中...", total=None)

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )

                progress.update(task, completed=100, description="[green]✓ 提取完成[/green]")

            console.print(f"[green]✓ 音訊已提取：{output_path}[/green]")
            return output_path

        except subprocess.CalledProcessError as e:
            self._handle_ffmpeg_error(
                e,
                operation="音訊提取",
                input_files=[video_path],
                output_file=output_path
            )

    def merge_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: Optional[str] = None,
        replace: bool = True
    ) -> str:
        """
        合併音訊到影片

        Args:
            video_path: 影片路徑
            audio_path: 音訊路徑
            output_path: 輸出路徑，預設自動生成
            replace: 是否替換原音訊（True）或混合（False）

        Returns:
            str: 輸出影片路徑
        """
        # 驗證輸入檔案
        self._validate_media_file(video_path, required_type="video")
        self._validate_media_file(audio_path, required_type="audio")

        console.print(f"\n[cyan]🎵 合併音訊...[/cyan]")
        console.print(f"  影片：{os.path.basename(video_path)}")
        console.print(f"  音訊：{os.path.basename(audio_path)}")
        console.print(f"  模式：{'替換' if replace else '混合'}原音訊")

        # 設定輸出路徑
        if output_path is None:
            base_name = Path(video_path).stem
            output_path = os.path.join(
                self.output_dir,
                f"{base_name}_with_audio.mp4"
            )

        if replace:
            # 替換原音訊
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",  # 影片不重新編碼
                "-c:a", "aac",
                "-map", "0:v:0",  # 使用第一個輸入的影片
                "-map", "1:a:0",  # 使用第二個輸入的音訊
                "-shortest",  # 以較短的為準
                "-y",
                output_path
            ]
        else:
            # 混合音訊
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first",
                "-c:v", "copy",
                "-c:a", "aac",
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
                task = progress.add_task("合併中...", total=None)

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )

                progress.update(task, completed=100, description="[green]✓ 合併完成[/green]")

            console.print(f"[green]✓ 影片已合併：{output_path}[/green]")
            return output_path

        except subprocess.CalledProcessError as e:
            self._handle_ffmpeg_error(
                e,
                operation="音訊合併",
                input_files=[video_path, audio_path],
                output_file=output_path
            )

    def adjust_volume(
        self,
        audio_or_video_path: str,
        volume: float,
        output_path: Optional[str] = None
    ) -> str:
        """
        調整音量

        Args:
            audio_or_video_path: 音訊或影片路徑
            volume: 音量倍數 (0.5 = 50%, 1.0 = 100%, 2.0 = 200%)
            output_path: 輸出路徑，預設自動生成

        Returns:
            str: 輸出檔案路徑
        """
        # 驗證輸入檔案
        self._validate_media_file(audio_or_video_path, required_type="any")

        console.print(f"\n[cyan]🔊 調整音量...[/cyan]")
        console.print(f"  檔案：{os.path.basename(audio_or_video_path)}")
        console.print(f"  音量：{volume * 100:.0f}%")

        # 判斷是影片還是音訊
        is_video = self._is_video_file(audio_or_video_path)

        # 設定輸出路徑
        if output_path is None:
            base_name = Path(audio_or_video_path).stem
            extension = Path(audio_or_video_path).suffix
            output_path = os.path.join(
                self.output_dir,
                f"{base_name}_vol{int(volume * 100)}{extension}"
            )

        # 調整音量
        if is_video:
            cmd = [
                "ffmpeg",
                "-i", audio_or_video_path,
                "-af", f"volume={volume}",
                "-c:v", "copy",  # 影片不重新編碼
                "-c:a", "aac",
                "-y",
                output_path
            ]
        else:
            cmd = [
                "ffmpeg",
                "-i", audio_or_video_path,
                "-af", f"volume={volume}",
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

                progress.update(task, completed=100, description="[green]✓ 處理完成[/green]")

            console.print(f"[green]✓ 音量已調整：{output_path}[/green]")
            return output_path

        except subprocess.CalledProcessError as e:
            self._handle_ffmpeg_error(
                e,
                operation="音量調整",
                input_files=[audio_or_video_path],
                output_file=output_path
            )

    def add_background_music(
        self,
        video_path: str,
        music_path: str,
        output_path: Optional[str] = None,
        music_volume: float = 0.3,
        fade_duration: float = 2.0
    ) -> str:
        """
        添加背景音樂

        Args:
            video_path: 影片路徑
            music_path: 背景音樂路徑
            output_path: 輸出路徑，預設自動生成
            music_volume: 背景音樂音量 (0.0-1.0，預設 0.3)
            fade_duration: 淡入淡出時長（秒，預設 2.0）

        Returns:
            str: 輸出影片路徑
        """
        # 驗證輸入檔案
        self._validate_media_file(video_path, required_type="video")
        self._validate_media_file(music_path, required_type="audio")

        console.print(f"\n[cyan]🎵 添加背景音樂...[/cyan]")
        console.print(f"  影片：{os.path.basename(video_path)}")
        console.print(f"  音樂：{os.path.basename(music_path)}")
        console.print(f"  音樂音量：{music_volume * 100:.0f}%")
        console.print(f"  淡入淡出：{fade_duration} 秒")

        # 設定輸出路徑
        if output_path is None:
            base_name = Path(video_path).stem
            output_path = os.path.join(
                self.output_dir,
                f"{base_name}_with_bgm.mp4"
            )

        # 添加背景音樂（混合原音訊）
        # 1. 降低背景音樂音量
        # 2. 添加淡入淡出效果
        # 3. 循環播放直到影片結束
        # 4. 混合原音訊和背景音樂
        filter_complex = (
            f"[1:a]volume={music_volume},"
            f"afade=t=in:st=0:d={fade_duration},"
            f"afade=t=out:st={fade_duration}:d={fade_duration},"
            f"aloop=loop=-1:size=2e+09[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first[aout]"
        )

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
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

                progress.update(task, completed=100, description="[green]✓ 處理完成[/green]")

            console.print(f"[green]✓ 背景音樂已添加：{output_path}[/green]")
            return output_path

        except subprocess.CalledProcessError as e:
            self._handle_ffmpeg_error(
                e,
                operation="背景音樂添加",
                input_files=[video_path, music_path],
                output_file=output_path
            )

    def fade_in_out(
        self,
        audio_or_video_path: str,
        output_path: Optional[str] = None,
        fade_in: float = 2.0,
        fade_out: float = 2.0
    ) -> str:
        """
        添加音訊淡入淡出效果

        Args:
            audio_or_video_path: 音訊或影片路徑
            output_path: 輸出路徑，預設自動生成
            fade_in: 淡入時長（秒，預設 2.0）
            fade_out: 淡出時長（秒，預設 2.0）

        Returns:
            str: 輸出檔案路徑
        """
        # 驗證輸入檔案
        self._validate_media_file(audio_or_video_path, required_type="any")

        console.print(f"\n[cyan]🎵 添加淡入淡出...[/cyan]")
        console.print(f"  檔案：{os.path.basename(audio_or_video_path)}")
        console.print(f"  淡入：{fade_in} 秒")
        console.print(f"  淡出：{fade_out} 秒")

        # 獲取檔案時長
        duration = self._get_duration(audio_or_video_path)
        if duration is None:
            try:
                from error_fix_suggestions import suggest_cannot_get_duration
                suggest_cannot_get_duration(audio_or_video_path)
            except ImportError:
                pass

            raise RuntimeError("無法獲取檔案時長，請參考上述診斷")

        fade_out_start = max(0, duration - fade_out)

        # 判斷是影片還是音訊
        is_video = self._is_video_file(audio_or_video_path)

        # 設定輸出路徑
        if output_path is None:
            base_name = Path(audio_or_video_path).stem
            extension = Path(audio_or_video_path).suffix
            output_path = os.path.join(
                self.output_dir,
                f"{base_name}_fade{extension}"
            )

        # 添加淡入淡出
        audio_filter = f"afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}"

        if is_video:
            cmd = [
                "ffmpeg",
                "-i", audio_or_video_path,
                "-af", audio_filter,
                "-c:v", "copy",
                "-c:a", "aac",
                "-y",
                output_path
            ]
        else:
            cmd = [
                "ffmpeg",
                "-i", audio_or_video_path,
                "-af", audio_filter,
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

                progress.update(task, completed=100, description="[green]✓ 處理完成[/green]")

            console.print(f"[green]✓ 淡入淡出已添加：{output_path}[/green]")
            return output_path

        except subprocess.CalledProcessError as e:
            self._handle_ffmpeg_error(
                e,
                operation="淡入淡出處理",
                input_files=[audio_or_video_path],
                output_file=output_path
            )

    def _get_audio_extension(self, format: str) -> str:
        """獲取音訊檔案副檔名"""
        extensions = {
            'aac': 'aac',
            'mp3': 'mp3',
            'wav': 'wav'
        }
        return extensions.get(format.lower(), 'aac')

    def _get_audio_codec(self, format: str) -> str:
        """獲取音訊編碼器"""
        codecs = {
            'aac': 'aac',
            'mp3': 'libmp3lame',
            'wav': 'pcm_s16le'
        }
        return codecs.get(format.lower(), 'aac')

    def _is_video_file(self, file_path: str) -> bool:
        """判斷是否為影片檔案"""
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm'}
        return Path(file_path).suffix.lower() in video_extensions

    def _get_duration(self, file_path: str) -> Optional[float]:
        """獲取檔案時長（秒）"""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path
        ]

        try:
            import json
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )

            data = json.loads(result.stdout)
            return float(data['format']['duration'])

        except Exception as e:
            console.print(f"[yellow]警告：無法獲取檔案時長 - {e}[/yellow]")
            return None

    def _validate_media_file(self, file_path: str, required_type: str = "any") -> bool:
        """
        驗證媒體檔案完整性

        Args:
            file_path: 檔案路徑
            required_type: 'video', 'audio', 'any'

        Returns:
            bool: 檔案是否有效

        Raises:
            FileNotFoundError: 檔案不存在
            ValueError: 檔案格式錯誤或損壞
        """
        # 1. 檢查檔案存在性
        if not os.path.isfile(file_path):
            # 🎯 一鍵修復：顯示檔案不存在的修復建議並嘗試自動搜尋
            if ERROR_FIX_ENABLED:
                alternative = suggest_video_file_not_found(file_path, auto_fix=True)
                if alternative and os.path.isfile(alternative):
                    console.print(f"[green]✅ 已切換至：{alternative}[/green]\n")
                    file_path = alternative
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            else:
                raise FileNotFoundError(f"找不到檔案：{file_path}")

        # 2. 檢查檔案大小（避免空檔案）
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            # 🎯 一鍵修復：顯示空檔案診斷
            if ERROR_FIX_ENABLED:
                suggest_empty_file(file_path)
                # 記錄錯誤
                if error_logger:
                    error_logger.log_error(
                        error_type="EmptyFile",
                        file_path=file_path,
                        details={"size": 0}
                    )
            raise ValueError(f"檔案為空（0 bytes）：{file_path}，請參考上述診斷")

        # 3. 使用 ffprobe 驗證格式
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=format_name,duration",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            file_path
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
                timeout=10
            )

            import json
            data = json.loads(result.stdout)

            # 檢查是否有有效串流
            if 'streams' not in data or len(data['streams']) == 0:
                raise ValueError(f"檔案無有效媒體串流：{file_path}")

            # 檢查媒體類型
            if required_type == "video":
                has_video = any(s.get('codec_type') == 'video' for s in data['streams'])
                if not has_video:
                    # 🎯 一鍵修復：顯示缺少影片串流的修復建議
                    if ERROR_FIX_ENABLED:
                        suggest_missing_stream(file_path, missing_type="video")
                        if error_logger:
                            error_logger.log_error(
                                error_type="MissingVideoStream",
                                file_path=file_path,
                                details={"streams": data['streams']}
                            )
                    raise ValueError(f"檔案不包含影片串流：{file_path}，請參考上述建議")
            elif required_type == "audio":
                has_audio = any(s.get('codec_type') == 'audio' for s in data['streams'])
                if not has_audio:
                    # 🎯 一鍵修復：顯示缺少音訊串流的修復建議
                    if ERROR_FIX_ENABLED:
                        suggest_missing_stream(file_path, missing_type="audio")
                        if error_logger:
                            error_logger.log_error(
                                error_type="MissingAudioStream",
                                file_path=file_path,
                                details={"streams": data['streams']}
                            )
                    raise ValueError(f"檔案不包含音訊串流：{file_path}，請參考上述建議")

            logger.debug(f"檔案驗證通過：{file_path} ({file_size:,} bytes)")
            return True

        except subprocess.TimeoutExpired:
            # 🎯 一鍵修復：顯示檔案損壞診斷（超時情況）
            if ERROR_FIX_ENABLED:
                suggest_corrupted_file(file_path, stderr="檔案驗證超時")
                if error_logger:
                    error_logger.log_error(
                        error_type="FileCorrupted",
                        file_path=file_path,
                        details={"error": "驗證超時"}
                    )
            raise ValueError(f"檔案驗證超時（可能損壞）：{file_path}，請參考上述修復建議")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr if e.stderr else "無錯誤訊息"

            # 🎯 一鍵修復：顯示檔案損壞的詳細修復建議
            if ERROR_FIX_ENABLED:
                suggest_corrupted_file(file_path, stderr)
                if error_logger:
                    error_logger.log_error(
                        error_type="FileCorrupted",
                        file_path=file_path,
                        details={"stderr": stderr[:500]}
                    )

            raise ValueError(f"檔案格式錯誤或損壞：{file_path}，請參考上述修復建議")
        except json.JSONDecodeError:
            # 🎯 一鍵修復：ffprobe 輸出解析失敗
            if ERROR_FIX_ENABLED:
                suggest_corrupted_file(file_path, stderr="ffprobe 輸出無法解析")
            raise ValueError(f"無法解析檔案資訊（ffprobe 輸出異常）：{file_path}，請參考上述建議")

    def _handle_ffmpeg_error(
        self,
        error: subprocess.CalledProcessError,
        operation: str,
        input_files: List[str],
        output_file: str
    ) -> None:
        """
        統一處理 ffmpeg 錯誤，提供詳細診斷資訊

        Args:
            error: ffmpeg 執行錯誤
            operation: 操作名稱（如「音訊提取」）
            input_files: 輸入檔案列表
            output_file: 輸出檔案路徑

        Raises:
            RuntimeError: 包含詳細錯誤資訊
        """
        stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else str(error.stderr)

        # 分析常見錯誤模式
        error_patterns = {
            "Invalid data found": "檔案格式錯誤或損壞",
            "Permission denied": "檔案權限不足",
            "No such file": "找不到指定檔案",
            "Disk quota exceeded": "磁碟空間不足",
            "codec not currently supported": "不支援的編碼格式",
            "does not contain any stream": "檔案不包含有效串流",
            "Invalid argument": "參數錯誤或檔案路徑包含特殊字元",
            "Conversion failed": "格式轉換失敗",
            "Output file is empty": "輸出檔案為空",
            "already exists": "輸出檔案已存在"
        }

        # 尋找錯誤原因
        error_reason = "未知錯誤"
        for pattern, reason in error_patterns.items():
            if pattern in stderr:
                error_reason = reason
                break

        # 建構詳細錯誤訊息
        error_msg = f"""{operation}失敗：{error_reason}

輸入檔案：
{chr(10).join(f'  - {f} ({os.path.getsize(f):,} bytes)' if os.path.isfile(f) else f'  - {f} (不存在)' for f in input_files)}

輸出檔案：{output_file}

ffmpeg 錯誤碼：{error.returncode}

詳細資訊（最後 500 字元）：
{stderr[-500:] if len(stderr) > 500 else stderr}"""

        logger.error(error_msg)

        # 🎯 一鍵修復：根據錯誤類型顯示對應修復建議
        if ERROR_FIX_ENABLED and error_logger:
            # 記錄錯誤到統計系統
            error_logger.log_error(
                error_type="FFmpegError",
                file_path=input_files[0] if input_files else output_file,
                details={
                    'operation': operation,
                    'error_reason': error_reason,
                    'returncode': error.returncode,
                    'stderr_preview': stderr[-500:] if len(stderr) > 500 else stderr
                }
            )

            # 根據錯誤原因顯示具體修復建議
            if "檔案格式錯誤或損壞" in error_reason:
                for f in input_files:
                    if os.path.isfile(f):
                        suggest_corrupted_file(f, stderr)
                        break

        raise RuntimeError(error_msg.strip())


def main():
    """測試用主程式"""
    import sys

    if len(sys.argv) < 3:
        console.print("[cyan]用法：[/cyan]")
        console.print("  python gemini_audio_processor.py <命令> <參數>")
        console.print("\n[cyan]命令：[/cyan]")
        console.print("  extract <影片路徑>                     - 提取音訊")
        console.print("  merge <影片路徑> <音訊路徑>             - 合併音訊（替換）")
        console.print("  volume <檔案路徑> <音量倍數>            - 調整音量")
        console.print("  bgm <影片路徑> <音樂路徑> [音量]        - 添加背景音樂")
        console.print("  fade <檔案路徑> [淡入秒數] [淡出秒數]   - 淡入淡出")
        sys.exit(1)

    command = sys.argv[1]
    processor = AudioProcessor()

    try:
        if command == "extract":
            if len(sys.argv) < 3:
                console.print("[red]錯誤：需要提供影片路徑[/red]")
                sys.exit(1)
            output = processor.extract_audio(sys.argv[2])
            console.print(f"\n[green]✓ 完成：{output}[/green]")

        elif command == "merge":
            if len(sys.argv) < 4:
                console.print("[red]錯誤：需要提供影片路徑和音訊路徑[/red]")
                sys.exit(1)
            output = processor.merge_audio(sys.argv[2], sys.argv[3])
            console.print(f"\n[green]✓ 完成：{output}[/green]")

        elif command == "volume":
            if len(sys.argv) < 4:
                console.print("[red]錯誤：需要提供檔案路徑和音量倍數[/red]")
                sys.exit(1)
            volume = float(sys.argv[3])
            output = processor.adjust_volume(sys.argv[2], volume)
            console.print(f"\n[green]✓ 完成：{output}[/green]")

        elif command == "bgm":
            if len(sys.argv) < 4:
                console.print("[red]錯誤：需要提供影片路徑和音樂路徑[/red]")
                sys.exit(1)
            music_volume = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3
            output = processor.add_background_music(
                sys.argv[2],
                sys.argv[3],
                music_volume=music_volume
            )
            console.print(f"\n[green]✓ 完成：{output}[/green]")

        elif command == "fade":
            if len(sys.argv) < 3:
                console.print("[red]錯誤：需要提供檔案路徑[/red]")
                sys.exit(1)
            fade_in = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
            fade_out = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
            output = processor.fade_in_out(
                sys.argv[2],
                fade_in=fade_in,
                fade_out=fade_out
            )
            console.print(f"\n[green]✓ 完成：{output}[/green]")

        else:
            console.print(f"[red]未知命令：{command}[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"\n[red]錯誤：{e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
