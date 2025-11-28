#!/usr/bin/env python3
"""
Gemini 影片特效處理工具
支援無損時間裁切、高品質濾鏡效果、速度調整等
"""
import os
import subprocess
import json
from typing import Optional, Tuple
from pathlib import Path
from rich.console import Console
from utils.i18n import safe_t
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from datetime import datetime

console = Console()

# 輸出目錄
# 使用統一輸出目錄配置
from utils.path_manager import get_video_dir
OUTPUT_DIR = str(get_video_dir('effects'))


class VideoEffects:
    """影片特效處理器"""

    def __init__(self):
        """初始化處理器"""
        self.console = console
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        # 檢查 ffmpeg
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """檢查 ffmpeg 是否可用"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 顯示一鍵修復方案
            try:
                from error_fix_suggestions import suggest_ffmpeg_not_installed
                suggest_ffmpeg_not_installed()
            except ImportError:
                # 降級方案：顯示基本錯誤訊息
                console.print(safe_t('error.not_found', fallback='[dim #E8C4F0]錯誤：未找到 ffmpeg[/dim]'))
                console.print(safe_t('common.message', fallback='[#E8C4F0]請安裝 ffmpeg：brew install ffmpeg (macOS)[/#E8C4F0]'))

            raise RuntimeError("ffmpeg 未安裝，請按照上述步驟安裝後重試")

    def _get_video_duration(self, video_path: str) -> float:
        """獲取影片時長（秒）"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception as e:
            # 顯示一鍵修復方案
            try:
                from error_fix_suggestions import suggest_cannot_get_duration
                suggest_cannot_get_duration(video_path, e)
            except ImportError:
                # 降級方案：顯示基本錯誤訊息
                console.print(safe_t('error.cannot_process', fallback='[dim #E8C4F0]錯誤：無法獲取影片時長[/dim]'))
                console.print(safe_t('error.failed', fallback='[dim]錯誤詳情：{e}[/dim]', e=e))

            raise RuntimeError(f"無法獲取影片時長: {e}")

    def trim_video(
        self,
        video_path: str,
        start_time: float = 0,
        end_time: Optional[float] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        裁切影片時間段（無損）

        Args:
            video_path: 影片路徑
            start_time: 開始時間（秒）
            end_time: 結束時間（秒），None 表示到結尾
            output_path: 輸出路徑（可選）

        Returns:
            輸出檔案路徑
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                alternative_path = suggest_video_file_not_found(video_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    video_path = alternative_path
                    console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{video_path}[/#B565D8]\n', video_path=video_path))
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"影片檔案不存在: {video_path}")

        # 獲取影片時長
        duration = self._get_video_duration(video_path)

        if end_time is None:
            end_time = duration

        if start_time < 0 or end_time > duration or start_time >= end_time:
            # 🎯 一鍵修復：顯示修復建議
            try:
                from error_fix_suggestions import suggest_invalid_time_range
                suggest_invalid_time_range(start_time, end_time, duration, video_path)
            except ImportError:
                pass

            raise ValueError(f"無效的時間範圍: {start_time}s - {end_time}s (影片長度: {duration}s)")

        # 準備輸出路徑
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = Path(video_path).suffix
            output_filename = f"trimmed_{timestamp}{ext}"
            output_path = os.path.join(self.output_dir, output_filename)

        trim_duration = end_time - start_time

        self.console.print(f"\n[#E8C4F0]✂️ 裁切影片時間段（無損）[/#E8C4F0]")
        self.console.print(f"開始時間: {start_time}s")
        self.console.print(f"結束時間: {end_time}s")
        self.console.print(f"片段長度: {trim_duration:.2f}s\n")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("處理中...", total=None)

                # 使用 -c copy 無損裁切
                cmd = [
                    'ffmpeg',
                    '-ss', str(start_time),
                    '-t', str(trim_duration),
                    '-i', video_path,
                    '-c', 'copy',
                    '-avoid_negative_ts', '1',
                    output_path
                ]

                subprocess.run(cmd, check=True, capture_output=True)
                progress.update(task, description="[#B565D8]✓ 完成[/#B565D8]")

            self.console.print(f"\n[#B565D8]✅ 影片已裁切：{output_path}[/#B565D8]")
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            self.console.print(f"檔案大小：{file_size:.2f} MB")

            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.console.print(f"\n[dim #E8C4F0]❌ 處理失敗：{error_msg}[/dim]")
            raise

    def apply_filter(
        self,
        video_path: str,
        filter_name: str,
        output_path: Optional[str] = None,
        quality: str = "high"
    ) -> str:
        """
        應用濾鏡效果（需重新編碼）

        Args:
            video_path: 影片路徑
            filter_name: 濾鏡名稱 (grayscale, sepia, vintage, sharpen, blur)
            output_path: 輸出路徑（可選）
            quality: 品質 (high, medium, low)

        Returns:
            輸出檔案路徑
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                alternative_path = suggest_video_file_not_found(video_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    video_path = alternative_path
                    console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{video_path}[/#B565D8]\n', video_path=video_path))
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"影片檔案不存在: {video_path}")

        # 濾鏡定義
        filters = {
            'grayscale': 'hue=s=0',  # 黑白
            'sepia': 'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131',  # 復古棕色
            'vintage': 'curves=vintage',  # 復古效果
            'sharpen': 'unsharp=5:5:1.0:5:5:0.0',  # 銳化
            'blur': 'boxblur=2:1',  # 模糊
            'brighten': 'eq=brightness=0.1',  # 增亮
            'contrast': 'eq=contrast=1.2',  # 增強對比
        }

        if filter_name not in filters:
            # 🎯 一鍵修復：顯示修復建議
            try:
                from error_fix_suggestions import suggest_unsupported_filter
                suggest_unsupported_filter(filter_name, filters)
            except ImportError:
                pass

            raise ValueError(f"不支援的濾鏡: {filter_name}。支援: {list(filters.keys())}")

        # 品質設定
        quality_settings = {
            'high': ['-crf', '18', '-preset', 'slow'],
            'medium': ['-crf', '23', '-preset', 'medium'],
            'low': ['-crf', '28', '-preset', 'fast']
        }

        if quality not in quality_settings:
            quality = 'high'

        # 準備輸出路徑
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = Path(video_path).suffix
            output_filename = f"{filter_name}_{timestamp}{ext}"
            output_path = os.path.join(self.output_dir, output_filename)

        self.console.print(f"\n[#E8C4F0]🎨 應用濾鏡效果[/#E8C4F0]")
        self.console.print(f"濾鏡: {filter_name}")
        self.console.print(f"品質: {quality}")
        self.console.print(f"\n[#E8C4F0]⚠️  此操作需要重新編碼影片（使用高品質設置）[/#E8C4F0]\n")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("處理中...", total=None)

                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-vf', filters[filter_name],
                    '-c:v', 'libx264',
                    *quality_settings[quality],
                    '-c:a', 'copy',
                    output_path
                ]

                subprocess.run(cmd, check=True, capture_output=True)
                progress.update(task, description="[#B565D8]✓ 完成[/#B565D8]")

            self.console.print(f"\n[#B565D8]✅ 濾鏡已應用：{output_path}[/#B565D8]")
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            self.console.print(f"檔案大小：{file_size:.2f} MB")

            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.console.print(f"\n[dim #E8C4F0]❌ 處理失敗：{error_msg}[/dim]")
            raise

    def apply_multiple_filters(
        self,
        video_path: str,
        filter_names: list,
        output_path: Optional[str] = None,
        quality: str = "high"
    ) -> str:
        """
        批次應用多個濾鏡效果（使用 filter_complex，單次編碼）

        Args:
            video_path: 影片路徑
            filter_names: 濾鏡名稱列表，依序應用
            output_path: 輸出路徑（可選）
            quality: 品質 (high, medium, low)

        Returns:
            輸出檔案路徑

        Performance:
            - 5 個濾鏡：單次編碼 vs 5 次編碼
            - 時間：原時間 / 5 = 5x 提升
            - 品質：無損失（避免多次重新編碼）

        Example:
            apply_multiple_filters('video.mp4', ['grayscale', 'sharpen', 'contrast'])
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"影片檔案不存在: {video_path}")

        # 濾鏡定義
        filters = {
            'grayscale': 'hue=s=0',
            'sepia': 'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131',
            'vintage': 'curves=vintage',
            'sharpen': 'unsharp=5:5:1.0:5:5:0.0',
            'blur': 'boxblur=2:1',
            'brighten': 'eq=brightness=0.1',
            'contrast': 'eq=contrast=1.2',
        }

        # 驗證所有濾鏡
        for filter_name in filter_names:
            if filter_name not in filters:
                raise ValueError(f"不支援的濾鏡: {filter_name}。支援: {list(filters.keys())}")

        # 品質設定
        quality_settings = {
            'high': ['-crf', '18', '-preset', 'slow'],
            'medium': ['-crf', '23', '-preset', 'medium'],
            'low': ['-crf', '28', '-preset', 'fast']
        }

        if quality not in quality_settings:
            quality = 'high'

        # 準備輸出路徑
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = Path(video_path).suffix
            filter_chain_name = "_".join(filter_names)
            output_filename = f"multi_{filter_chain_name}_{timestamp}{ext}"
            output_path = os.path.join(self.output_dir, output_filename)

        # 建立 filter chain（串聯所有濾鏡）
        filter_chain = ",".join([filters[name] for name in filter_names])

        self.console.print(f"\n[#E8C4F0]🎨 批次應用濾鏡效果[/#E8C4F0]")
        self.console.print(f"濾鏡鏈: {' → '.join(filter_names)}")
        self.console.print(f"品質: {quality}")
        self.console.print(f"\n[#B565D8]✨ 優化：單次編碼應用所有濾鏡（{len(filter_names)}x 提升）[/#B565D8]\n")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task(f"處理 {len(filter_names)} 個濾鏡...", total=None)

                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-vf', filter_chain,  # 使用 filter chain
                    '-c:v', 'libx264',
                    *quality_settings[quality],
                    '-c:a', 'copy',
                    '-y',  # 覆蓋輸出
                    output_path
                ]

                subprocess.run(cmd, check=True, capture_output=True)
                progress.update(task, description=f"[#B565D8]✓ 完成 ({len(filter_names)} 個濾鏡)[/#B565D8]")

            self.console.print(f"\n[#B565D8]✅ 所有濾鏡已應用：{output_path}[/#B565D8]")
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            self.console.print(f"檔案大小：{file_size:.2f} MB")
            self.console.print(f"[dim]提示：單次編碼避免了 {len(filter_names)-1} 次額外的品質損失[/dim]")

            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.console.print(f"\n[dim #E8C4F0]❌ 處理失敗：{error_msg}[/dim]")
            raise

    def adjust_speed(
        self,
        video_path: str,
        speed_factor: float,
        output_path: Optional[str] = None,
        quality: str = "high"
    ) -> str:
        """
        調整影片速度（需重新編碼）

        Args:
            video_path: 影片路徑
            speed_factor: 速度倍數 (0.5 = 慢動作, 2.0 = 2倍速)
            output_path: 輸出路徑（可選）
            quality: 品質 (high, medium, low)

        Returns:
            輸出檔案路徑
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                alternative_path = suggest_video_file_not_found(video_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    video_path = alternative_path
                    console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{video_path}[/#B565D8]\n', video_path=video_path))
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"影片檔案不存在: {video_path}")

        if speed_factor <= 0:
            # 🎯 一鍵修復：顯示速度倍數設定建議
            try:
                from error_fix_suggestions import suggest_invalid_speed
                suggest_invalid_speed(speed_factor)
            except ImportError:
                pass
            raise ValueError("速度倍數必須大於 0")

        # 品質設定
        quality_settings = {
            'high': ['-crf', '18', '-preset', 'slow'],
            'medium': ['-crf', '23', '-preset', 'medium'],
            'low': ['-crf', '28', '-preset', 'fast']
        }

        if quality not in quality_settings:
            quality = 'high'

        # 準備輸出路徑
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = Path(video_path).suffix
            speed_str = f"{speed_factor:.1f}x".replace('.', '_')
            output_filename = f"speed_{speed_str}_{timestamp}{ext}"
            output_path = os.path.join(self.output_dir, output_filename)

        self.console.print(f"\n[#E8C4F0]⚡ 調整影片速度[/#E8C4F0]")
        self.console.print(f"速度倍數: {speed_factor}x")
        self.console.print(f"品質: {quality}")
        self.console.print(f"\n[#E8C4F0]⚠️  此操作需要重新編碼影片（使用高品質設置）[/#E8C4F0]\n")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("處理中...", total=None)

                # 計算 PTS 倍數（與速度相反）
                pts_factor = 1.0 / speed_factor
                audio_tempo = speed_factor

                # 同時調整視訊和音訊速度
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-filter_complex', f'[0:v]setpts={pts_factor}*PTS[v];[0:a]atempo={audio_tempo}[a]',
                    '-map', '[v]',
                    '-map', '[a]',
                    '-c:v', 'libx264',
                    *quality_settings[quality],
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    output_path
                ]

                subprocess.run(cmd, check=True, capture_output=True)
                progress.update(task, description="[#B565D8]✓ 完成[/#B565D8]")

            self.console.print(f"\n[#B565D8]✅ 速度已調整：{output_path}[/#B565D8]")
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            self.console.print(f"檔案大小：{file_size:.2f} MB")

            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.console.print(f"\n[dim #E8C4F0]❌ 處理失敗：{error_msg}[/dim]")
            raise

    def add_watermark(
        self,
        video_path: str,
        watermark_path: str,
        position: str = "bottom-right",
        opacity: float = 0.7,
        output_path: Optional[str] = None,
        quality: str = "high"
    ) -> str:
        """
        添加浮水印（需重新編碼）

        Args:
            video_path: 影片路徑
            watermark_path: 浮水印圖片路徑
            position: 位置 (top-left, top-right, bottom-left, bottom-right, center)
            opacity: 不透明度 (0.0-1.0)
            output_path: 輸出路徑（可選）
            quality: 品質 (high, medium, low)

        Returns:
            輸出檔案路徑
        """
        if not os.path.isfile(video_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_video_file_not_found
                alternative_path = suggest_video_file_not_found(video_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    video_path = alternative_path
                    console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{video_path}[/#B565D8]\n', video_path=video_path))
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"影片檔案不存在: {video_path}")

        if not os.path.isfile(watermark_path):
            # 🎯 一鍵修復：顯示修復建議並嘗試自動修復
            try:
                from error_fix_suggestions import suggest_watermark_not_found
                alternative_path = suggest_watermark_not_found(watermark_path, auto_fix=True)

                if alternative_path and os.path.isfile(alternative_path):
                    # 用戶選擇了替代檔案，使用新路徑
                    watermark_path = alternative_path
                    console.print(safe_t('common.completed', fallback='[#B565D8]✅ 已切換至：{watermark_path}[/#B565D8]\n', watermark_path=watermark_path))
                else:
                    raise FileNotFoundError(f"找不到檔案，請參考上述建議")
            except ImportError:
                # 如果沒有修復建議模組，直接拋出錯誤
                raise FileNotFoundError(f"浮水印檔案不存在: {watermark_path}")

        if not 0 <= opacity <= 1:
            try:
                from error_fix_suggestions import suggest_invalid_watermark_params
                suggest_invalid_watermark_params(opacity=opacity)
            except ImportError:
                pass
            raise ValueError("不透明度必須在 0.0 到 1.0 之間")

        # 位置定義
        positions = {
            'top-left': '10:10',
            'top-right': 'W-w-10:10',
            'bottom-left': '10:H-h-10',
            'bottom-right': 'W-w-10:H-h-10',
            'center': '(W-w)/2:(H-h)/2'
        }

        if position not in positions:
            try:
                from error_fix_suggestions import suggest_invalid_watermark_params
                suggest_invalid_watermark_params(position=position, supported_positions=positions)
            except ImportError:
                pass
            raise ValueError(f"不支援的位置: {position}。支援: {list(positions.keys())}")

        # 品質設定
        quality_settings = {
            'high': ['-crf', '18', '-preset', 'slow'],
            'medium': ['-crf', '23', '-preset', 'medium'],
            'low': ['-crf', '28', '-preset', 'fast']
        }

        if quality not in quality_settings:
            quality = 'high'

        # 準備輸出路徑
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = Path(video_path).suffix
            output_filename = f"watermarked_{timestamp}{ext}"
            output_path = os.path.join(self.output_dir, output_filename)

        self.console.print(f"\n[#E8C4F0]💧 添加浮水印[/#E8C4F0]")
        self.console.print(f"浮水印: {os.path.basename(watermark_path)}")
        self.console.print(f"位置: {position}")
        self.console.print(f"不透明度: {opacity}")
        self.console.print(f"\n[#E8C4F0]⚠️  此操作需要重新編碼影片（使用高品質設置）[/#E8C4F0]\n")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("處理中...", total=None)

                # 構建 overlay 濾鏡
                overlay_filter = f"overlay={positions[position]}:format=auto,colorchannelmixer=aa={opacity}"

                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-i', watermark_path,
                    '-filter_complex', overlay_filter,
                    '-c:v', 'libx264',
                    *quality_settings[quality],
                    '-c:a', 'copy',
                    output_path
                ]

                subprocess.run(cmd, check=True, capture_output=True)
                progress.update(task, description="[#B565D8]✓ 完成[/#B565D8]")

            self.console.print(f"\n[#B565D8]✅ 浮水印已添加：{output_path}[/#B565D8]")
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            self.console.print(f"檔案大小：{file_size:.2f} MB")

            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.console.print(f"\n[dim #E8C4F0]❌ 處理失敗：{error_msg}[/dim]")
            raise


def main():
    """主程式 - 命令列介面"""
    import sys

    console.print(safe_t('common.processing', fallback='[bold #E8C4F0]Gemini 影片特效處理工具[/bold #E8C4F0]\n'))

    if len(sys.argv) < 3:
        console.print(safe_t('common.message', fallback='[#E8C4F0]用法：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  python gemini_video_effects.py <影片路徑> <指令> [參數...]'))
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]可用指令：[/#E8C4F0]'))
        console.print(safe_t('common.message', fallback='  trim <開始秒數> <結束秒數>           - 裁切時間段（無損）'))
        console.print(safe_t('common.message', fallback='  filter <濾鏡名稱> [品質]             - 應用濾鏡（grayscale, sepia, vintage, sharpen, blur）'))
        console.print(safe_t('common.message', fallback='  speed <倍數> [品質]                  - 調整速度（0.5=慢動作, 2.0=2倍速）'))
        console.print(safe_t('common.message', fallback='  watermark <圖片路徑> [位置] [透明度] - 添加浮水印'))
        console.print(safe_t('common.message', fallback='\n[#E8C4F0]範例：[/#E8C4F0]'))
        console.print("  python gemini_video_effects.py video.mp4 trim 10 30")
        console.print("  python gemini_video_effects.py video.mp4 filter grayscale high")
        console.print("  python gemini_video_effects.py video.mp4 speed 2.0")
        console.print("  python gemini_video_effects.py video.mp4 watermark logo.png bottom-right 0.7")
        return

    video_path = sys.argv[1]
    command = sys.argv[2]

    try:
        effects = VideoEffects()

        if command == 'trim':
            if len(sys.argv) < 5:
                console.print(safe_t('error.failed', fallback='[dim #E8C4F0]錯誤：trim 需要開始和結束時間[/dim]'))
                return
            start = float(sys.argv[3])
            end = float(sys.argv[4])
            output = effects.trim_video(video_path, start, end)

        elif command == 'filter':
            if len(sys.argv) < 4:
                console.print(safe_t('error.failed', fallback='[dim #E8C4F0]錯誤：filter 需要濾鏡名稱[/dim]'))
                return
            filter_name = sys.argv[3]
            quality = sys.argv[4] if len(sys.argv) > 4 else 'high'
            output = effects.apply_filter(video_path, filter_name, quality=quality)

        elif command == 'speed':
            if len(sys.argv) < 4:
                console.print(safe_t('error.failed', fallback='[dim #E8C4F0]錯誤：speed 需要速度倍數[/dim]'))
                return
            speed = float(sys.argv[3])
            quality = sys.argv[4] if len(sys.argv) > 4 else 'high'
            output = effects.adjust_speed(video_path, speed, quality=quality)

        elif command == 'watermark':
            if len(sys.argv) < 4:
                console.print(safe_t('error.failed', fallback='[dim #E8C4F0]錯誤：watermark 需要圖片路徑[/dim]'))
                return
            watermark = sys.argv[3]
            position = sys.argv[4] if len(sys.argv) > 4 else 'bottom-right'
            opacity = float(sys.argv[5]) if len(sys.argv) > 5 else 0.7
            output = effects.add_watermark(video_path, watermark, position, opacity)

        else:
            console.print(safe_t('common.message', fallback='[dim #E8C4F0]未知指令：{command}[/dim]', command=command))
            return

        console.print(safe_t('common.completed', fallback='\n[#B565D8]✅ 處理完成：{output}[/#B565D8]', output=output))

    except Exception as e:
        console.print(safe_t('error.failed', fallback='\n[dim #E8C4F0]錯誤：{e}[/dim]', e=e))
        sys.exit(1)


if __name__ == "__main__":
    main()
