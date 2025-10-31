#!/usr/bin/env python3
"""
Gemini 影片預處理模組
提供影片壓縮、關鍵幀提取、分割等功能,支援 Veo 影片生成
"""
import os
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from rich.console import Console
from utils.i18n import safe_t
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# 導入統一的錯誤修復建議系統
try:
    from error_fix_suggestions import (
        suggest_ffmpeg_install,
        suggest_video_file_not_found,
        suggest_empty_file,
        suggest_corrupted_file,
        suggest_missing_stream,
        suggest_cannot_get_duration,
        suggest_ffprobe_failed,
        suggest_video_transcode_failed,
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


class VideoPreprocessor:
    """影片預處理工具類別"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化預處理器

        Args:
            output_dir: 輸出目錄,預設為 ~/gemini_videos/preprocessed
        """
        if output_dir is None:
            # 使用統一輸出目錄配置
            from utils.path_manager import get_video_dir
            output_dir = str(get_video_dir('preprocessed'))
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # 驗證 ffmpeg 和 ffprobe 是否可用
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """檢查 ffmpeg 和 ffprobe 是否已安裝"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            subprocess.run(
                ["ffprobe", "-version"],
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
                # 降級方案：顯示基本錯誤訊息
                console.print(safe_t('error.not_found', fallback='[dim #E8C4F0]錯誤：未找到 ffmpeg 或 ffprobe[/red]'))
                console.print(safe_t('common.message', fallback='[#E8C4F0]請安裝 ffmpeg：brew install ffmpeg (macOS)[/#E8C4F0]'))

            raise RuntimeError(safe_t("video_preprocessor.msg_9300_ffmpeg_未安裝_請按照上述步驟安裝", fallback="ffmpeg 未安裝,請按照上述步驟安裝後重試"))

    def get_video_info(self, video_path: str) -> Dict:
        """
        使用 ffprobe 獲取影片元數據

        Args:
            video_path: 影片檔案路徑

        Returns:
            影片資訊字典,包含：
            - duration: 時長（秒）
            - width: 寬度
            - height: 高度
            - fps: 幀率
            - codec: 編碼
            - bitrate: 位元率
            - size_mb: 檔案大小（MB）
            - format: 格式
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示影片檔案修復建議
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                suggest_video_file_not_found(video_path)
            except ImportError:
                # 如果沒有修復建議模組,使用基本錯誤訊息
                pass

            raise FileNotFoundError(safe_t("video_preprocessor.msg_12200_找不到影片檔案", fallback="找不到影片檔案: {video_path}").format(video_path=video_path))

        try:
            # 使用 ffprobe 獲取 JSON 格式的資訊
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )

            data = json.loads(result.stdout)

            # 提取影片流資訊
            video_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break

            if not video_stream:
                # 顯示詳細的修復建議（包含檔案資訊和修復指令）
                try:
                    from error_fix_suggestions import suggest_no_video_stream
                    suggest_no_video_stream(video_path)
                except ImportError:
                    # 降級方案：顯示基本錯誤訊息
                    pass

                raise ValueError(safe_t("video_preprocessor.msg_16100_找不到影片流", fallback="找不到影片流"))

            # 組織資訊
            format_data = data.get("format", {})

            info = {
                "duration": float(format_data.get("duration", 0)),
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "fps": self._parse_fps(video_stream.get("r_frame_rate", "0/1")),
                "codec": video_stream.get("codec_name", "unknown"),
                "bitrate": int(format_data.get("bit_rate", 0)),
                "size_mb": os.path.getsize(video_path) / (1024 * 1024),
                "format": format_data.get("format_name", "unknown"),
                "aspect_ratio": f"{video_stream.get('width', 0)}:{video_stream.get('height', 0)}"
            }

            return info

        except subprocess.CalledProcessError as e:
            # 顯示 ffprobe 執行失敗的修復建議
            try:
                from error_fix_suggestions import suggest_ffprobe_failed
                suggest_ffprobe_failed(video_path, e)
            except ImportError:
                pass

            raise RuntimeError(safe_t("video_preprocessor.msg_18800_ffprobe_執行失敗", fallback="ffprobe 執行失敗: {stderr}").format(stderr=e.stderr))
        except json.JSONDecodeError as e:
            try:
                from error_fix_suggestions import suggest_ffprobe_parse_failed
                suggest_ffprobe_parse_failed(video_path, e)
            except ImportError:
                pass

            raise RuntimeError(safe_t("video_preprocessor.msg_19600_解析_ffprobe_輸出失敗", fallback="解析 ffprobe 輸出失敗: {e}").format(e=e))

    def _parse_fps(self, fps_str: str) -> float:
        """解析幀率字串（如 '30/1'）"""
        try:
            num, denom = fps_str.split('/')
            return float(num) / float(denom)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def compress_for_api(
        self,
        video_path: str,
        target_size_mb: int = 1900,
        output_filename: Optional[str] = None
    ) -> str:
        """
        檢查影片是否符合 API 大小限制（< 2GB）

        ⚠️ 此方法禁止有損壓縮,僅檢查檔案大小
        若檔案過大,建議使用 split_by_duration() 分割影片

        Args:
            video_path: 原始影片路徑
            target_size_mb: 目標大小（MB）,預設 1900MB
            output_filename: 未使用（保留相容性）

        Returns:
            影片路徑（若符合大小要求）

        Raises:
            RuntimeError: 若檔案超過大小限制
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示影片檔案修復建議
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                suggest_video_file_not_found(video_path)
            except ImportError:
                # 如果沒有修復建議模組,使用基本錯誤訊息
                pass

            raise FileNotFoundError(safe_t("video_preprocessor.msg_23800_找不到影片檔案", fallback="找不到影片檔案: {video_path}").format(video_path=video_path))

        # 獲取影片資訊
        info = self.get_video_info(video_path)
        current_size_mb = info["size_mb"]

        console.print(safe_t('common.message', fallback='\n[#E8C4F0]📊 影片資訊：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  檔案大小：{current_size_mb:.2f} MB', current_size_mb=current_size_mb))
        console.print(safe_t('common.message', fallback='  解析度：{width}x{height}', width=info['width'], height=info['height']))
        console.print(safe_t('common.message', fallback='  時長：{duration:.2f} 秒', duration=info["duration"]))
        console.print(safe_t('common.message', fallback='  編碼：{codec}', codec=info["codec"]))

        # 檢查是否符合大小要求
        if current_size_mb <= target_size_mb:
            console.print(safe_t('common.completed', fallback='[#B565D8]✓ 檔案大小符合要求（{current_size_mb:.2f} MB ≤ {target_size_mb} MB）[/green]', current_size_mb=current_size_mb, target_size_mb=target_size_mb))
            return video_path

        # 檔案過大,拒絕處理
        console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]✗ 錯誤：影片檔案過大[/red]'))
        console.print(safe_t('common.message', fallback='  當前大小：{current_size_mb:.2f} MB', current_size_mb=current_size_mb))
        console.print(safe_t('common.message', fallback='  限制大小：{target_size_mb} MB', target_size_mb=target_size_mb))
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]建議解決方案：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  1. 使用 split_by_duration() 分割影片為多個小片段'))
        console.print(safe_t('common.message', fallback='  2. 在影片編輯軟體中預先分割影片'))
        console.print(safe_t('common.message', fallback='  3. 使用較短的影片片段'))

        raise RuntimeError(
            safe_t("video_preprocessor.msg_26500_影片檔案過大", fallback="影片檔案過大 ({current_size_mb:.2f} MB > {target_size_mb} MB)。請使用 split_by_duration() 分割影片,或使用較小的影片檔案。系統禁止有損壓縮以保持影片品質。").format(current_size_mb=current_size_mb, target_size_mb=target_size_mb)
        )

    def extract_keyframes(
        self,
        video_path: str,
        num_frames: int = 3,
        method: str = "uniform"
    ) -> List[str]:
        """
        提取關鍵幀作為 Veo 參考圖片

        Args:
            video_path: 影片路徑
            num_frames: 提取幀數,預設 3（Veo 最多支援 3 張）
            method: 提取方法
                - 'uniform': 等距提取（開頭、中間、結尾）
                - 'scene': 場景檢測（未實作）

        Returns:
            提取的圖片路徑列表
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示影片檔案修復建議
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                suggest_video_file_not_found(video_path)
            except ImportError:
                # 如果沒有修復建議模組,使用基本錯誤訊息
                pass

            raise FileNotFoundError(safe_t("video_preprocessor.msg_29800_找不到影片檔案", fallback="找不到影片檔案: {video_path}").format(video_path=video_path))

        if num_frames > 3:
            console.print(safe_t('common.warning', fallback='[#E8C4F0]警告：Veo 最多支援 3 張參考圖片,將限制為 3 張[/#E8C4F0]'))
            num_frames = 3

        # 獲取影片資訊
        info = self.get_video_info(video_path)
        duration = info["duration"]

        console.print(safe_t('common.message', fallback='\n[#E8C4F0]🖼️  提取關鍵幀...[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  影片時長：{duration:.2f} 秒', duration=duration))
        console.print(safe_t('common.message', fallback='  提取數量：{num_frames} 幀', num_frames=num_frames))

        # 計算提取時間點
        if method == "uniform":
            timestamps = self._calculate_uniform_timestamps(duration, num_frames)
        else:
            raise NotImplementedError(f"方法 '{method}' 尚未實作")

        # 提取幀
        frame_paths = []
        base_name = os.path.splitext(os.path.basename(video_path))[0]

        for i, timestamp in enumerate(timestamps):
            output_filename = f"{base_name}_frame_{i+1}_{timestamp:.2f}s.jpg"
            output_path = os.path.join(self.output_dir, output_filename)

            cmd = [
                "ffmpeg",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",  # 高品質
                "-y",
                output_path
            ]

            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
                frame_paths.append(output_path)
                console.print(safe_t('common.completed', fallback='  ✓ 提取幀 {i+1}：{timestamp:.2f}s', frame_num=i+1, timestamp=timestamp))
            except subprocess.CalledProcessError as e:
                console.print(safe_t('error.failed', fallback='  ✗ 提取幀 {i+1} 失敗：{e}', frame_num=i+1, e=e))

        console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 已提取 {len(frame_paths)} 幀[/green]', frame_paths_count=len(frame_paths)))
        for path in frame_paths:
            console.print(f"  - {path}")

        return frame_paths

    def _calculate_uniform_timestamps(
        self,
        duration: float,
        num_frames: int
    ) -> List[float]:
        """計算等距時間點"""
        if num_frames == 1:
            return [duration / 2]
        elif num_frames == 2:
            return [duration * 0.25, duration * 0.75]
        elif num_frames == 3:
            return [duration * 0.15, duration * 0.5, duration * 0.85]
        else:
            # 通用等距計算
            interval = duration / (num_frames + 1)
            return [interval * (i + 1) for i in range(num_frames)]

    def split_by_duration(
        self,
        video_path: str,
        segment_duration: int = 8,
        output_prefix: Optional[str] = None
    ) -> List[str]:
        """
        將長影片分割成固定時長片段

        Args:
            video_path: 影片路徑
            segment_duration: 片段時長（秒）,預設 8 秒（Veo 限制）
            output_prefix: 輸出檔名前綴,預設為原檔名

        Returns:
            分割後的影片路徑列表
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示影片檔案修復建議
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                suggest_video_file_not_found(video_path)
            except ImportError:
                # 如果沒有修復建議模組,使用基本錯誤訊息
                pass

            raise FileNotFoundError(safe_t("video_preprocessor.msg_39700_找不到影片檔案", fallback="找不到影片檔案: {video_path}").format(video_path=video_path))

        # 獲取影片資訊
        info = self.get_video_info(video_path)
        duration = info["duration"]

        # 計算片段數量
        num_segments = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)

        console.print(safe_t('common.message', fallback='\n[#E8C4F0]✂️  分割影片...[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  影片時長：{duration:.2f} 秒', duration=duration))
        console.print(safe_t('common.message', fallback='  片段時長：{segment_duration} 秒', segment_duration=segment_duration))
        console.print(safe_t('common.message', fallback='  片段數量：{num_segments}', num_segments=num_segments))

        # 準備輸出前綴
        if output_prefix is None:
            output_prefix = os.path.splitext(os.path.basename(video_path))[0]

        # 分割影片
        segment_paths = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(safe_t("video_preprocessor.msg_42500_分割中", fallback="分割中..."), total=num_segments)

            for i in range(num_segments):
                start_time = i * segment_duration
                output_filename = f"{output_prefix}_segment_{i+1:03d}.mp4"
                output_path = os.path.join(self.output_dir, output_filename)

                cmd = [
                    "ffmpeg",
                    "-ss", str(start_time),
                    "-i", video_path,
                    "-t", str(segment_duration),
                    "-c", "copy",  # 不重新編碼（快速）
                    "-y",
                    output_path
                ]

                try:
                    subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True
                    )
                    segment_paths.append(output_path)
                    progress.update(task, advance=1)
                except subprocess.CalledProcessError as e:
                    stderr = e.stderr.decode('utf-8') if e.stderr else str(e)
                    console.print(safe_t('error.failed', fallback='[dim #E8C4F0]✗ 分割片段 {i+1} 失敗[/red]', frame_num=i+1))

                    # 顯示轉碼失敗修復建議
                    try:
                        from error_fix_suggestions import suggest_video_transcode_failed
                        suggest_video_transcode_failed(video_path, output_path, stderr)
                    except ImportError:
                        console.print(safe_t('error.failed', fallback='[dim #E8C4F0]錯誤：{stderr[:200]}[/red]', stderr_short=stderr[:200]))

        console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 已分割為 {len(segment_paths)} 個片段[/green]', segment_paths_count=len(segment_paths)))
        for i, path in enumerate(segment_paths, 1):
            segment_info = self.get_video_info(path)
            console.print(f"  {i}. {os.path.basename(path)} ({segment_info['duration']:.2f}s)")

        return segment_paths


def main():
    """測試用主程式"""
    import sys

    if len(sys.argv) < 2:
        console.print(safe_t('common.message', fallback='[#E8C4F0]用法：[/#E8C4F0]'))
        console.print("  python gemini_video_preprocessor.py <video_path> [command]")
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]命令：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  info         - 顯示影片資訊（預設）'))
        console.print(safe_t('common.message', fallback='  compress     - 壓縮影片'))
        console.print(safe_t('common.message', fallback='  keyframes    - 提取關鍵幀'))
        console.print(safe_t('common.message', fallback='  split        - 分割影片'))
        sys.exit(1)

    video_path = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "info"

    preprocessor = VideoPreprocessor()

    try:
        if command == "info":
            info = preprocessor.get_video_info(video_path)
            console.print(safe_t('common.message', fallback='\n[#E8C4F0]📊 影片資訊：[/#E8C4F0]'))
            for key, value in info.items():
                console.print(f"  {key}: {value}")

        elif command == "compress":
            output = preprocessor.compress_for_api(video_path)
            console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 壓縮完成：{output}[/green]', output=output))

        elif command == "keyframes":
            frames = preprocessor.extract_keyframes(video_path)
            console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 已提取 {len(frames)} 幀[/green]', frames_count=len(frames)))

        elif command == "split":
            segments = preprocessor.split_by_duration(video_path)
            console.print(safe_t('common.completed', fallback='\n[#B565D8]✓ 已分割為 {len(segments)} 個片段[/green]', segments_count=len(segments)))

        else:
            console.print(safe_t('common.message', fallback='[dim #E8C4F0]未知命令：{command}[/red]', command=command))
            sys.exit(1)

    except Exception as e:
        console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]錯誤：{e}[/red]', e=e))
        sys.exit(1)


if __name__ == "__main__":
    main()
