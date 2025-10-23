#!/usr/bin/env python3
"""
Gemini 自動場景檢測模組
使用 AI 分析影片關鍵幀，自動檢測場景變化並生成場景索引
"""
import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# 導入現有模組
from gemini_video_preprocessor import VideoPreprocessor
from utils.api_client import get_gemini_client
from google.genai import types

# 導入價格模組
from utils.pricing_loader import get_pricing_calculator, PRICING_ENABLED
from gemini_pricing import USD_TO_TWD

console = Console()
client = get_gemini_client()

# 初始化價格計算器
global_pricing_calculator = get_pricing_calculator(silent=True)


@dataclass
class Scene:
    """場景資料結構"""
    id: int
    start_time: float          # 開始時間（秒）
    end_time: float            # 結束時間（秒）
    start_frame_path: str      # 開始幀圖片路徑
    end_frame_path: str        # 結束幀圖片路徑
    description: str           # 場景描述
    confidence: float          # 置信度（0-1）
    key_elements: List[str]    # 關鍵元素列表


class SceneDetector:
    """自動場景檢測器"""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        output_dir: Optional[str] = None
    ):
        """
        初始化場景檢測器

        Args:
            model_name: 使用的 Gemini 模型
            output_dir: 輸出目錄
        """
        self.model_name = model_name
        self.preprocessor = VideoPreprocessor()

        if output_dir is None:
            # 使用統一輸出目錄配置
            from utils.path_manager import get_video_dir
            output_dir = str(get_video_dir('scenes'))
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def detect_scenes(
        self,
        video_path: str,
        num_keyframes: int = 30,
        similarity_threshold: float = 0.7,
        show_cost: bool = True
    ) -> List[Scene]:
        """
        檢測影片中的場景變化

        Args:
            video_path: 影片路徑
            num_keyframes: 提取的關鍵幀數量（預設 30）
            similarity_threshold: 相似度閾值（0-1），低於此值視為場景切換
            show_cost: 是否顯示成本

        Returns:
            場景列表
        """
        console.print(Panel.fit(
            "[bold magenta]🎬 自動場景檢測[/bold magenta]",
            border_style="bright_magenta"
        ))

        # 1. 提取關鍵幀
        console.print(f"\n[magenta]📹 分析影片：{os.path.basename(video_path)}[/magenta]")

        # 獲取影片資訊
        video_info = self.preprocessor.get_video_info(video_path)
        duration = video_info["duration"]

        console.print(f"[dim]  時長：{duration:.2f} 秒[/dim]")
        console.print(f"[dim]  將提取 {num_keyframes} 個關鍵幀[/dim]\n")

        # 修改 extract_keyframes 為支持更多幀數
        keyframes = self._extract_uniform_frames(video_path, num_keyframes, duration)

        console.print(f"[bright_magenta]✓ 已提取 {len(keyframes)} 個關鍵幀[/green]\n")

        # 2. 分析每個幀的內容
        console.print("[magenta]🤖 使用 Gemini Vision 分析關鍵幀...[/magenta]\n")

        frame_descriptions = []
        total_cost = 0.0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console
        ) as progress:
            task = progress.add_task("分析中", total=len(keyframes))

            for frame_data in keyframes:
                description = self._analyze_frame(
                    frame_data['path'],
                    frame_data['timestamp'],
                    show_cost=False
                )

                frame_descriptions.append({
                    **frame_data,
                    'description': description
                })

                progress.update(task, advance=1)

        # 3. 檢測場景變化
        console.print("\n[magenta]🔍 檢測場景變化...[/magenta]")
        scenes = self._detect_scene_changes(
            frame_descriptions,
            similarity_threshold
        )

        console.print(f"[bright_magenta]✓ 檢測到 {len(scenes)} 個場景[/green]\n")

        # 4. 顯示成本
        if PRICING_ENABLED and show_cost and global_pricing_calculator:
            console.print(f"[dim]💰 本次成本: NT${global_pricing_calculator.total_cost * USD_TO_TWD:.2f} (${global_pricing_calculator.total_cost:.6f})[/dim]\n")

        return scenes

    def _extract_uniform_frames(
        self,
        video_path: str,
        num_frames: int,
        duration: float
    ) -> List[Dict]:
        """
        等距提取關鍵幀

        Args:
            video_path: 影片路徑
            num_frames: 幀數
            duration: 影片時長

        Returns:
            幀資訊列表 [{'path': ..., 'timestamp': ...}, ...]
        """
        import subprocess

        # 計算時間間隔
        interval = duration / (num_frames + 1)
        timestamps = [interval * (i + 1) for i in range(num_frames)]

        frame_paths = []
        base_name = os.path.splitext(os.path.basename(video_path))[0]

        for i, timestamp in enumerate(timestamps):
            output_filename = f"{base_name}_scene_frame_{i+1:03d}_{timestamp:.2f}s.jpg"
            output_path = os.path.join(self.preprocessor.output_dir, output_filename)

            cmd = [
                "ffmpeg",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
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
                frame_paths.append({
                    'path': output_path,
                    'timestamp': timestamp,
                    'frame_number': i + 1
                })
            except subprocess.CalledProcessError as e:
                console.print(f"[magenta]警告：提取幀 {i+1} 失敗[/yellow]")

        return frame_paths

    def _analyze_frame(
        self,
        frame_path: str,
        timestamp: float,
        show_cost: bool = False
    ) -> str:
        """
        分析單個幀的內容

        Args:
            frame_path: 幀圖片路徑
            timestamp: 時間戳
            show_cost: 是否顯示成本

        Returns:
            幀內容描述
        """
        # 上傳圖片
        try:
            with open(frame_path, 'rb') as f:
                image_data = f.read()

            uploaded_file = client.files.upload(file=image_data)

            # 分析提示
            prompt = """請簡潔描述這個畫面的主要內容，包括：
1. 場景類型（室內/戶外/特寫等）
2. 主要物體或人物
3. 主要動作或狀態
4. 整體氛圍

用 1-2 句話總結即可。"""

            # 發送請求
            response = client.models.generate_content(
                model=self.model_name,
                contents=[uploaded_file, prompt]
            )

            # 提取 tokens
            if PRICING_ENABLED and global_pricing_calculator:
                thinking_tokens = getattr(response.usage_metadata, 'thinking_tokens', 0)
                input_tokens = getattr(response.usage_metadata, 'prompt_tokens', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_tokens', 0)

                cost, _ = global_pricing_calculator.calculate_text_cost(
                    self.model_name,
                    input_tokens,
                    output_tokens,
                    thinking_tokens
                )

            return response.text.strip()

        except Exception as e:
            console.print(f"[magenta]警告：分析幀失敗：{e}[/yellow]")
            return "無法分析"

    def _detect_scene_changes(
        self,
        frame_descriptions: List[Dict],
        threshold: float = 0.7
    ) -> List[Scene]:
        """
        根據幀描述檢測場景變化

        Args:
            frame_descriptions: 幀描述列表
            threshold: 相似度閾值

        Returns:
            場景列表
        """
        scenes = []
        current_scene_start = 0
        scene_id = 1

        for i in range(1, len(frame_descriptions)):
            prev_desc = frame_descriptions[i-1]['description']
            curr_desc = frame_descriptions[i]['description']

            # 使用 Gemini 判斷兩個描述是否屬於同一場景
            is_same_scene = self._compare_scenes(prev_desc, curr_desc, threshold)

            if not is_same_scene:
                # 場景切換，保存前一個場景
                scene = Scene(
                    id=scene_id,
                    start_time=frame_descriptions[current_scene_start]['timestamp'],
                    end_time=frame_descriptions[i-1]['timestamp'],
                    start_frame_path=frame_descriptions[current_scene_start]['path'],
                    end_frame_path=frame_descriptions[i-1]['path'],
                    description=self._summarize_scene(
                        frame_descriptions[current_scene_start:i]
                    ),
                    confidence=0.8,  # 簡化版本使用固定值
                    key_elements=self._extract_key_elements(
                        frame_descriptions[current_scene_start:i]
                    )
                )
                scenes.append(scene)

                # 開始新場景
                current_scene_start = i
                scene_id += 1

        # 添加最後一個場景
        scene = Scene(
            id=scene_id,
            start_time=frame_descriptions[current_scene_start]['timestamp'],
            end_time=frame_descriptions[-1]['timestamp'],
            start_frame_path=frame_descriptions[current_scene_start]['path'],
            end_frame_path=frame_descriptions[-1]['path'],
            description=self._summarize_scene(
                frame_descriptions[current_scene_start:]
            ),
            confidence=0.8,
            key_elements=self._extract_key_elements(
                frame_descriptions[current_scene_start:]
            )
        )
        scenes.append(scene)

        return scenes

    def _compare_scenes(
        self,
        desc1: str,
        desc2: str,
        threshold: float
    ) -> bool:
        """
        比較兩個場景描述是否相似

        Args:
            desc1: 描述 1
            desc2: 描述 2
            threshold: 相似度閾值

        Returns:
            是否為同一場景
        """
        # 簡化版本：使用關鍵詞比較
        # 在生產環境中可以使用 Gemini 的 embedding 或更精確的比較方法

        # 提取關鍵詞
        keywords1 = set(desc1.lower().split())
        keywords2 = set(desc2.lower().split())

        # 計算 Jaccard 相似度
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)

        similarity = intersection / union if union > 0 else 0

        return similarity >= threshold

    def _summarize_scene(self, frames: List[Dict]) -> str:
        """總結場景描述"""
        if not frames:
            return "未知場景"

        # 使用第一幀的描述作為場景描述
        return frames[0]['description']

    def _extract_key_elements(self, frames: List[Dict]) -> List[str]:
        """提取場景的關鍵元素"""
        # 簡化版本：從描述中提取名詞
        all_words = []
        for frame in frames:
            all_words.extend(frame['description'].split())

        # 返回前 5 個常見詞（簡化）
        from collections import Counter
        common_words = Counter(all_words).most_common(5)
        return [word for word, _ in common_words if len(word) > 2]

    def display_scenes(self, scenes: List[Scene]):
        """
        以表格形式顯示場景

        Args:
            scenes: 場景列表
        """
        table = Table(title="🎬 場景列表", show_header=True, header_style="bold magenta")

        console_width = console.width or 120
        table.add_column("#", style="dim", width=max(4, int(console_width * 0.03)))
        table.add_column("時間範圍", width=max(18, int(console_width * 0.15)))
        table.add_column("時長", width=max(8, int(console_width * 0.08)))
        table.add_column("描述", width=max(35, int(console_width * 0.40)))
        table.add_column("關鍵元素", width=max(20, int(console_width * 0.25)))

        for scene in scenes:
            duration = scene.end_time - scene.start_time
            time_range = f"{self._format_time(scene.start_time)} - {self._format_time(scene.end_time)}"

            table.add_row(
                str(scene.id),
                time_range,
                f"{duration:.1f}s",
                scene.description,
                ", ".join(scene.key_elements[:3]) if scene.key_elements else "-"
            )

        console.print("\n")
        console.print(table)
        console.print("\n")

    def save_scenes(
        self,
        scenes: List[Scene],
        video_path: str,
        format: str = "json"
    ) -> str:
        """
        保存場景索引到檔案

        Args:
            scenes: 場景列表
            video_path: 原影片路徑
            format: 輸出格式（json 或 txt）

        Returns:
            輸出檔案路徑
        """
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            output_file = os.path.join(
                self.output_dir,
                f"{base_name}_scenes_{timestamp}.json"
            )

            data = {
                'video': os.path.basename(video_path),
                'total_scenes': len(scenes),
                'generated_at': datetime.now().isoformat(),
                'scenes': [asdict(scene) for scene in scenes]
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif format == "txt":
            output_file = os.path.join(
                self.output_dir,
                f"{base_name}_scenes_{timestamp}.txt"
            )

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"影片場景索引\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(f"影片：{os.path.basename(video_path)}\n")
                f.write(f"場景數量：{len(scenes)}\n")
                f.write(f"生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"{'=' * 60}\n\n")

                for scene in scenes:
                    duration = scene.end_time - scene.start_time
                    f.write(f"場景 {scene.id}\n")
                    f.write(f"-" * 40 + "\n")
                    f.write(f"時間：{self._format_time(scene.start_time)} - {self._format_time(scene.end_time)} ({duration:.1f}s)\n")
                    f.write(f"描述：{scene.description}\n")
                    if scene.key_elements:
                        f.write(f"關鍵元素：{', '.join(scene.key_elements)}\n")
                    f.write(f"\n")

        console.print(f"[bright_magenta]✓ 場景索引已保存：{output_file}[/green]")
        return output_file

    def _format_time(self, seconds: float) -> str:
        """格式化時間（秒 -> mm:ss）"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"


# ==================== CLI 介面 ====================

def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='Gemini 自動場景檢測')
    parser.add_argument('video', help='影片檔案路徑')
    parser.add_argument('--frames', type=int, default=30, help='提取關鍵幀數量（預設 30）')
    parser.add_argument('--threshold', type=float, default=0.7, help='相似度閾值（預設 0.7）')
    parser.add_argument('--model', default='gemini-2.0-flash-exp', help='使用的模型')
    parser.add_argument('--output', choices=['json', 'txt', 'both'], default='both', help='輸出格式')

    args = parser.parse_args()

    # 檢查檔案
    if not os.path.isfile(args.video):
        console.print(f"[dim magenta]錯誤：找不到影片檔案：{args.video}[/red]")
        return

    # 創建檢測器
    detector = SceneDetector(model_name=args.model)

    # 檢測場景
    scenes = detector.detect_scenes(
        args.video,
        num_keyframes=args.frames,
        similarity_threshold=args.threshold
    )

    # 顯示結果
    detector.display_scenes(scenes)

    # 保存結果
    if args.output in ['json', 'both']:
        detector.save_scenes(scenes, args.video, format='json')

    if args.output in ['txt', 'both']:
        detector.save_scenes(scenes, args.video, format='txt')


if __name__ == "__main__":
    main()
