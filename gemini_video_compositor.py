#!/usr/bin/env python3
"""
Gemini 影片合併與後製模組
提供影片合併、過渡效果、片段替換等功能
"""
import os
import subprocess
import tempfile
from typing import List, Optional
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from utils.i18n import safe_t

console = Console()


class VideoCompositor:
    """影片合併與後製工具類別"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化合併器

        Args:
            output_dir: 輸出目錄,預設為 ~/gemini_videos/composed
        """
        if output_dir is None:
            # 使用統一輸出目錄配置
            from utils.path_manager import get_video_dir
            output_dir = str(get_video_dir('composed'))
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
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(safe_t('video.compositor.ffmpeg_not_found', fallback='[dim #E8C4F0]錯誤：未找到 ffmpeg[/dim]'))
            console.print(safe_t('video.compositor.install_ffmpeg', fallback='[#E8C4F0]請安裝 ffmpeg：brew install ffmpeg (macOS)[/#E8C4F0]'))
            raise RuntimeError(safe_t('video.compositor.ffmpeg_not_installed', fallback='ffmpeg 未安裝'))

    def concat_segments(
        self,
        video_paths: List[str],
        output_path: Optional[str] = None,
        transition: str = "none"
    ) -> str:
        """
        合併多段影片（無損合併）

        ⚠️ 僅支援無過渡合併（concat demuxer）,禁止有損編碼

        Args:
            video_paths: 影片路徑列表（依順序）
            output_path: 輸出影片路徑,預設自動生成
            transition: 過渡類型（僅支援 "none",其他選項已禁用）

        Returns:
            str: 輸出影片路徑

        Raises:
            ValueError: 若使用非 "none" 的過渡效果
        """
        if not video_paths:
            raise ValueError(safe_t('video.compositor.empty_video_list', fallback='影片路徑列表為空'))

        # 驗證所有檔案存在
        for video_path in video_paths:
            if not os.path.isfile(video_path):
                raise FileNotFoundError(safe_t('video.compositor.file_not_found', fallback='找不到影片檔案：{path}', path=video_path))

        # 設定輸出路徑
        if output_path is None:
            timestamp = Path(video_paths[0]).stem
            output_path = os.path.join(
                self.output_dir,
                f"merged_{timestamp}.mp4"
            )

        console.print(safe_t('video.compositor.merging_videos', fallback='\n[#E8C4F0]🎬 合併影片...[/#E8C4F0]'))
        console.print(safe_t('video.compositor.segment_count', fallback='  片段數量：{count}', count=len(video_paths)))
        console.print(safe_t('video.compositor.transition_effect', fallback='  過渡效果：{transition}', transition=transition))

        # 禁止有損過渡效果
        if transition != "none":
            console.print(safe_t('video.compositor.transition_disabled', fallback='\n[dim #E8C4F0]✗ 錯誤：過渡效果已禁用[/dim]'))
            console.print(safe_t('video.compositor.no_lossy_encoding', fallback='  系統禁止有損編碼以保持影片品質'))
            console.print(safe_t('video.compositor.transition_quality_loss', fallback='  過渡效果需要重新編碼影片,會造成品質損失'))
            raise ValueError(
                safe_t('video.compositor.transition_not_allowed', fallback='禁止使用過渡效果（{transition}）。系統僅支援無損合併（transition=\'none\'）。', transition=transition)
            )

        # 使用 concat demuxer（無損合併）
        return self._concat_demuxer(video_paths, output_path)

    def _concat_demuxer(
        self,
        video_paths: List[str],
        output_path: str
    ) -> str:
        """使用 concat demuxer 無損合併（最快）"""
        # 創建臨時 concat 檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for video_path in video_paths:
                # 使用絕對路徑
                abs_path = os.path.abspath(video_path)
                f.write(f"file '{abs_path}'\n")

        try:
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",  # 不重新編碼
                "-y",
                output_path
            ]

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(safe_t('video.compositor.merging', fallback='合併中...'), total=None)

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )

                progress.update(task, completed=100, description=safe_t('video.compositor.merge_complete', fallback='[#B565D8]✓ 合併完成[/#B565D8]'))

            console.print(safe_t('video.compositor.video_merged', fallback='[#B565D8]✓ 影片已合併：{path}[/#B565D8]', path=output_path))
            return output_path

        except subprocess.CalledProcessError as e:
            raise RuntimeError(safe_t('video.compositor.merge_failed', fallback='ffmpeg 合併失敗：{error}', error=e.stderr.decode()))
        finally:
            # 清理臨時檔案
            if os.path.exists(concat_file):
                os.remove(concat_file)

    def _concat_with_transition(
        self,
        video_paths: List[str],
        output_path: str,
        transition: str,
        transition_duration: float = 0.5
    ) -> str:
        """使用 filter_complex 合併（支援過渡效果）"""
        console.print(safe_t('video.compositor.transition_warning', fallback='[#E8C4F0]注意：過渡效果需要重新編碼,耗時較長[/#E8C4F0]'))

        # 構建 filter_complex
        filter_parts = []
        inputs = []

        for i, video_path in enumerate(video_paths):
            inputs.extend(["-i", video_path])

            if i < len(video_paths) - 1:
                # 為當前片段加上淡出
                filter_parts.append(
                    f"[{i}:v]fade=t=out:st={transition_duration}:d={transition_duration}[v{i}out]"
                )

                # 為下一片段加上淡入
                filter_parts.append(
                    f"[{i+1}:v]fade=t=in:st=0:d={transition_duration}[v{i+1}in]"
                )

        # 合併所有片段
        concat_inputs = []
        for i in range(len(video_paths)):
            if i == 0:
                concat_inputs.append(f"[v{i}out]")
            elif i == len(video_paths) - 1:
                concat_inputs.append(f"[v{i}in]")
            else:
                concat_inputs.append(f"[v{i}out]")
                concat_inputs.append(f"[v{i}in]")

        # 音訊處理（簡單合併）
        audio_inputs = "".join([f"[{i}:a]" for i in range(len(video_paths))])

        filter_complex = ";".join(filter_parts) + ";" + \
                        "".join(concat_inputs) + f"concat=n={len(concat_inputs)}:v=1:a=0[outv];" + \
                        audio_inputs + f"concat=n={len(video_paths)}:v=0:a=1[outa]"

        cmd = [
            "ffmpeg",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "medium",
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
                task = progress.add_task(safe_t('video.compositor.processing_transition', fallback='處理過渡效果...'), total=None)

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )

                progress.update(task, completed=100, description=safe_t('video.compositor.processing_complete', fallback='[#B565D8]✓ 處理完成[/#B565D8]'))

            console.print(safe_t('video.compositor.merged_with_transition', fallback='[#B565D8]✓ 影片已合併（含過渡效果）：{path}[/#B565D8]', path=output_path))
            return output_path

        except subprocess.CalledProcessError as e:
            raise RuntimeError(safe_t('video.compositor.processing_failed', fallback='ffmpeg 處理失敗：{error}', error=e.stderr.decode()))

    def replace_segment(
        self,
        base_video: str,
        new_segment: str,
        start_time: float,
        output_path: Optional[str] = None
    ) -> str:
        """
        替換影片中的某個時段（用於 Insert 功能）

        Args:
            base_video: 原始影片路徑
            new_segment: 新片段影片路徑
            start_time: 替換起始時間（秒）
            output_path: 輸出路徑,預設自動生成

        Returns:
            str: 輸出影片路徑
        """
        if not os.path.isfile(base_video):
            raise FileNotFoundError(safe_t('video.compositor.base_video_not_found', fallback='找不到影片檔案：{path}', path=base_video))
        if not os.path.isfile(new_segment):
            raise FileNotFoundError(safe_t('video.compositor.new_segment_not_found', fallback='找不到新片段檔案：{path}', path=new_segment))

        console.print(safe_t('video.compositor.replacing_segment', fallback='\n[#E8C4F0]✂️  替換影片片段...[/#E8C4F0]'))
        console.print(safe_t('video.compositor.original_video', fallback='  原始影片：{name}', name=os.path.basename(base_video)))
        console.print(safe_t('video.compositor.new_segment', fallback='  新片段：{name}', name=os.path.basename(new_segment)))
        console.print(safe_t('video.compositor.replace_position', fallback='  替換位置：{time}s', time=start_time))

        # 獲取新片段時長
        probe_cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            new_segment
        ]

        import json
        probe_result = subprocess.run(
            probe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )

        probe_data = json.loads(probe_result.stdout)
        new_segment_duration = float(probe_data['format']['duration'])

        console.print(safe_t('video.compositor.segment_duration', fallback='  新片段時長：{duration:.2f}s', duration=new_segment_duration))

        # 設定輸出路徑
        if output_path is None:
            base_name = Path(base_video).stem
            output_path = os.path.join(
                self.output_dir,
                f"{base_name}_edited.mp4"
            )

        # 創建臨時目錄
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. 提取前段（0 ~ start_time）
            part1_path = os.path.join(temp_dir, "part1.mp4")
            if start_time > 0:
                cmd1 = [
                    "ffmpeg",
                    "-i", base_video,
                    "-t", str(start_time),
                    "-c", "copy",
                    "-y",
                    part1_path
                ]
                subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            # 2. 提取後段（start_time + new_segment_duration ~ end）
            part3_path = os.path.join(temp_dir, "part3.mp4")
            cmd3 = [
                "ffmpeg",
                "-ss", str(start_time + new_segment_duration),
                "-i", base_video,
                "-c", "copy",
                "-y",
                part3_path
            ]
            subprocess.run(cmd3, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            # 3. 合併三段
            parts = []
            if start_time > 0:
                parts.append(part1_path)
            parts.append(new_segment)
            parts.append(part3_path)

            # 使用 concat_segments 合併
            return self.concat_segments(parts, output_path)

    def add_transitions(
        self,
        video_paths: List[str],
        transition_type: str = "fade",
        transition_duration: float = 0.5,
        output_dir: Optional[str] = None
    ) -> List[str]:
        """
        為每個片段加入過渡效果（已禁用）

        ⚠️ 此功能已禁用,因需要有損編碼

        Args:
            video_paths: 影片路徑列表
            transition_type: 過渡類型（已禁用）
            transition_duration: 過渡時長（已禁用）
            output_dir: 輸出目錄（已禁用）

        Returns:
            List[str]: 不會返回,直接拋出異常

        Raises:
            RuntimeError: 功能已禁用
        """
        console.print(safe_t('video.compositor.transitions_disabled', fallback='\n[dim #E8C4F0]✗ 錯誤：過渡效果功能已禁用[/dim]'))
        console.print(safe_t('video.compositor.transitions_need_encoding', fallback='  過渡效果需要重新編碼影片（libx264）,會造成品質損失'))
        console.print(safe_t('video.compositor.no_lossy_policy', fallback='  系統禁止有損編碼以保持影片原始品質'))

        raise RuntimeError(
            safe_t('video.compositor.transitions_function_disabled', fallback='add_transitions() 功能已禁用。此功能需要有損編碼（libx264）,與系統「禁止有損壓縮」政策衝突。')
        )


def main():
    """測試用主程式"""
    import sys

    if len(sys.argv) < 3:
        console.print(safe_t('video.compositor.usage', fallback='[#E8C4F0]用法：[/#E8C4F0]'))
        console.print(safe_t('video.compositor.usage_command', fallback='  python gemini_video_compositor.py <command> <args>'))
        console.print(safe_t('video.compositor.commands', fallback='\n[#E8C4F0]命令：[/#E8C4F0]'))
        console.print(safe_t('video.compositor.concat_command', fallback='  concat <video1> <video2> [video3...] - 合併影片'))
        console.print(safe_t('video.compositor.replace_command', fallback='  replace <base> <new_segment> <start_time> - 替換片段'))
        sys.exit(1)

    command = sys.argv[1]
    compositor = VideoCompositor()

    try:
        if command == "concat":
            video_paths = sys.argv[2:]
            output = compositor.concat_segments(video_paths)
            console.print(safe_t('video.compositor.concat_done', fallback='\n[#B565D8]✓ 合併完成：{output}[/#B565D8]', output=output))

        elif command == "replace":
            if len(sys.argv) < 5:
                console.print(safe_t('video.compositor.replace_needs_args', fallback='[dim #E8C4F0]錯誤：replace 需要 3 個參數[/dim]'))
                sys.exit(1)

            base_video = sys.argv[2]
            new_segment = sys.argv[3]
            start_time = float(sys.argv[4])

            output = compositor.replace_segment(base_video, new_segment, start_time)
            console.print(safe_t('video.compositor.replace_done', fallback='\n[#B565D8]✓ 替換完成：{output}[/#B565D8]', output=output))

        else:
            console.print(safe_t('video.compositor.unknown_command', fallback='[dim #E8C4F0]未知命令：{command}[/dim]', command=command))
            sys.exit(1)

    except Exception as e:
        console.print(safe_t('common.error', fallback='\n[dim #E8C4F0]錯誤：{error}[/dim]', error=str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
