#!/usr/bin/env python3
"""
Gemini 智能影片摘要模組
使用 AI 分析影片內容，生成多層次摘要、章節標記和元數據
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
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# 導入現有模組
from gemini_video_preprocessor import VideoPreprocessor
from gemini_scene_detector import SceneDetector, Scene
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
class Chapter:
    """章節資料結構"""
    id: int
    title: str                 # 章節標題
    start_time: float          # 開始時間（秒）
    end_time: float            # 結束時間（秒）
    description: str           # 章節描述
    thumbnail: str             # 縮圖路徑
    key_points: List[str]      # 關鍵要點


@dataclass
class VideoSummary:
    """影片摘要資料結構"""
    video_path: str            # 影片路徑
    video_name: str            # 影片名稱
    duration: float            # 總長度（秒）

    # 多層次摘要
    title: str                 # 建議標題
    short_summary: str         # 短摘要（1-2 句，適合社群媒體）
    medium_summary: str        # 中摘要（1 段落，適合影片描述）
    long_summary: str          # 長摘要（詳細多段落）

    # 內容分析
    key_topics: List[str]      # 主要話題
    tags: List[str]            # 標籤
    category: str              # 分類
    language: str              # 語言

    # 章節
    chapters: List[Chapter]    # 章節列表

    # 元數據
    generated_at: str          # 生成時間
    confidence: float          # 整體置信度


class VideoSummarizer:
    """智能影片摘要器"""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        use_scene_detection: bool = True
    ):
        """
        初始化摘要器

        Args:
            model_name: 使用的 Gemini 模型
            use_scene_detection: 是否使用場景檢測
        """
        self.model_name = model_name
        self.use_scene_detection = use_scene_detection
        self.preprocessor = VideoPreprocessor()
        self.scene_detector = SceneDetector(model_name=model_name) if use_scene_detection else None

    def generate_summary(
        self,
        video_path: str,
        num_chapters: Optional[int] = None,
        summary_style: str = "balanced"
    ) -> VideoSummary:
        """
        生成影片摘要

        Args:
            video_path: 影片檔案路徑
            num_chapters: 章節數量（None 表示自動判斷）
            summary_style: 摘要風格（'concise', 'balanced', 'detailed'）

        Returns:
            VideoSummary 物件
        """
        console.print("\n[bold cyan]📝 智能影片摘要分析[/bold cyan]\n")
        console.print(f"📁 影片：{os.path.basename(video_path)}")

        # 1. 獲取影片資訊
        info = self.preprocessor.get_video_info(video_path)
        if not info:
            console.print("[red]錯誤：無法獲取影片資訊[/red]")
            return None

        duration = info['duration']
        console.print(f"⏱️  總長度：{self._format_time(duration)}")
        console.print(f"📊 風格：{summary_style}")

        # 2. 場景檢測
        scenes = []
        if self.use_scene_detection:
            console.print("\n[cyan]📦 執行場景檢測...[/cyan]")
            # 根據影片長度調整關鍵幀數
            num_keyframes = min(30, max(10, int(duration / 10)))
            scenes = self.scene_detector.detect_scenes(video_path, num_keyframes=num_keyframes)
            console.print(f"✓ 檢測到 {len(scenes)} 個場景")

        # 3. 生成內容概覽
        console.print("\n[cyan]🔍 分析影片內容...[/cyan]")
        content_overview = self._analyze_content_overview(video_path, scenes, duration)

        # 4. 生成摘要
        console.print("\n[cyan]✍️  生成多層次摘要...[/cyan]")
        summaries = self._generate_multilevel_summaries(
            video_path,
            scenes,
            content_overview,
            summary_style
        )

        # 5. 提取主題和標籤
        console.print("\n[cyan]🏷️  提取主題和標籤...[/cyan]")
        topics_and_tags = self._extract_topics_and_tags(scenes, content_overview)

        # 6. 創建章節
        console.print("\n[cyan]📑 生成章節標記...[/cyan]")
        chapters = self._create_chapters(video_path, scenes, num_chapters)
        console.print(f"✓ 已生成 {len(chapters)} 個章節")

        # 7. 組裝摘要物件
        summary = VideoSummary(
            video_path=video_path,
            video_name=os.path.basename(video_path),
            duration=duration,
            title=summaries['title'],
            short_summary=summaries['short'],
            medium_summary=summaries['medium'],
            long_summary=summaries['long'],
            key_topics=topics_and_tags['topics'],
            tags=topics_and_tags['tags'],
            category=topics_and_tags['category'],
            language=topics_and_tags.get('language', 'unknown'),
            chapters=chapters,
            generated_at=datetime.now().isoformat(),
            confidence=content_overview.get('confidence', 0.8)
        )

        console.print("\n[green]✓ 摘要生成完成！[/green]")

        return summary

    def _analyze_content_overview(
        self,
        video_path: str,
        scenes: List[Scene],
        duration: float
    ) -> Dict:
        """分析影片內容概覽"""
        overview = {
            'duration': duration,
            'scene_count': len(scenes),
            'content_density': 'unknown',
            'visual_elements': [],
            'likely_category': 'general',
            'confidence': 0.8
        }

        if not scenes:
            return overview

        # 收集所有場景元素
        all_elements = []
        for scene in scenes:
            all_elements.extend(scene.key_elements)

        # 統計元素頻率
        from collections import Counter
        element_counter = Counter(all_elements)
        most_common = element_counter.most_common(10)

        overview['visual_elements'] = [elem for elem, count in most_common]

        # 評估內容密度
        avg_scene_duration = duration / len(scenes) if scenes else 0
        if avg_scene_duration < 5:
            overview['content_density'] = 'high'  # 快節奏
        elif avg_scene_duration < 15:
            overview['content_density'] = 'medium'
        else:
            overview['content_density'] = 'low'  # 慢節奏

        # 推測類別（基於視覺元素）
        overview['likely_category'] = self._infer_category(overview['visual_elements'])

        # 計算平均置信度
        if scenes:
            avg_confidence = sum(s.confidence for s in scenes) / len(scenes)
            overview['confidence'] = avg_confidence

        return overview

    def _infer_category(self, visual_elements: List[str]) -> str:
        """推測影片類別"""
        # 定義類別關鍵字
        category_keywords = {
            'tutorial': ['screen', 'text', 'diagram', 'interface', 'cursor'],
            'vlog': ['person', 'face', 'outdoor', 'indoor', 'selfie'],
            'gaming': ['game', 'screen', 'ui', 'character', 'hud'],
            'nature': ['landscape', 'sky', 'water', 'tree', 'animal'],
            'music': ['instrument', 'stage', 'performer', 'audience'],
            'sports': ['field', 'player', 'action', 'stadium', 'ball'],
            'cooking': ['food', 'kitchen', 'cooking', 'ingredients'],
            'travel': ['landmark', 'city', 'outdoor', 'scenery']
        }

        # 計算每個類別的匹配分數
        scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for elem in visual_elements if any(kw in elem.lower() for kw in keywords))
            scores[category] = score

        # 返回最高分類別
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return 'general'

    def _generate_multilevel_summaries(
        self,
        video_path: str,
        scenes: List[Scene],
        overview: Dict,
        style: str
    ) -> Dict[str, str]:
        """生成多層次摘要"""

        # 收集場景描述
        scene_descriptions = [s.description for s in scenes[:10]]  # 取前 10 個場景

        # 構建提示詞
        prompt = self._build_summary_prompt(scene_descriptions, overview, style)

        # 調用 Gemini 生成摘要
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )

            # 解析響應
            summaries = self._parse_summary_response(response.text)

            # 計算成本
            if PRICING_ENABLED and global_pricing_calculator:
                global_pricing_calculator.calculate_and_display(
                    model=self.model_name,
                    response=response
                )

            return summaries

        except Exception as e:
            console.print(f"[yellow]警告：生成摘要時出錯，使用預設摘要: {e}[/yellow]")
            return self._generate_default_summaries(scenes, overview)

    def _build_summary_prompt(
        self,
        scene_descriptions: List[str],
        overview: Dict,
        style: str
    ) -> str:
        """構建摘要生成提示詞"""

        scenes_text = "\n".join([f"- {desc}" for desc in scene_descriptions])

        style_instructions = {
            'concise': '簡潔扼要，重點突出',
            'balanced': '平衡詳細程度和可讀性',
            'detailed': '詳盡完整，包含所有重要細節'
        }

        prompt = f"""
分析以下影片場景，生成多層次摘要。

**影片資訊：**
- 總長度：{overview['duration']:.1f} 秒
- 場景數：{overview['scene_count']}
- 內容密度：{overview['content_density']}
- 推測類別：{overview['likely_category']}

**場景描述：**
{scenes_text}

**任務：**
請生成以下格式的摘要（使用繁體中文）：

1. **建議標題**（吸引人且準確）
2. **短摘要**（1-2 句話，不超過 280 字元，適合社群媒體）
3. **中摘要**（1 段落，100-200 字，適合影片描述）
4. **長摘要**（2-3 段落，詳細描述影片內容、亮點、適合觀眾）

**風格要求：** {style_instructions.get(style, '平衡')}

**輸出格式：**
TITLE: [標題]
SHORT: [短摘要]
MEDIUM: [中摘要]
LONG: [長摘要]
"""
        return prompt

    def _parse_summary_response(self, response_text: str) -> Dict[str, str]:
        """解析摘要響應"""
        summaries = {
            'title': '',
            'short': '',
            'medium': '',
            'long': ''
        }

        lines = response_text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith('TITLE:'):
                current_section = 'title'
                summaries['title'] = line.replace('TITLE:', '').strip()
            elif line.startswith('SHORT:'):
                current_section = 'short'
                summaries['short'] = line.replace('SHORT:', '').strip()
            elif line.startswith('MEDIUM:'):
                current_section = 'medium'
                summaries['medium'] = line.replace('MEDIUM:', '').strip()
            elif line.startswith('LONG:'):
                current_section = 'long'
                summaries['long'] = line.replace('LONG:', '').strip()
            elif current_section and line:
                # 繼續添加到當前段落
                summaries[current_section] += ' ' + line

        # 清理空白
        for key in summaries:
            summaries[key] = summaries[key].strip()

        return summaries

    def _generate_default_summaries(
        self,
        scenes: List[Scene],
        overview: Dict
    ) -> Dict[str, str]:
        """生成預設摘要（當 AI 生成失敗時）"""

        # 收集前幾個場景的關鍵元素
        key_elements = []
        for scene in scenes[:5]:
            key_elements.extend(scene.key_elements[:3])
        key_elements = list(set(key_elements))[:10]

        return {
            'title': f"{overview['likely_category'].title()} 影片",
            'short': f"包含 {overview['scene_count']} 個場景，展示 {', '.join(key_elements[:3])} 等內容。",
            'medium': f"這是一部 {overview['likely_category']} 類型的影片，總長度 {overview['duration']:.0f} 秒。影片包含 {overview['scene_count']} 個不同場景，主要展示 {', '.join(key_elements[:5])} 等元素。內容節奏為 {overview['content_density']}。",
            'long': f"這是一部 {overview['likely_category']} 類型的影片，總長度約 {overview['duration'] / 60:.1f} 分鐘。\n\n影片包含 {overview['scene_count']} 個不同的場景，內容密度為 {overview['content_density']}，節奏 {'較快' if overview['content_density'] == 'high' else '適中' if overview['content_density'] == 'medium' else '較慢'}。主要視覺元素包括：{', '.join(key_elements)}。\n\n整體而言，這是一部內容豐富的 {overview['likely_category']} 影片，適合對相關主題感興趣的觀眾觀看。"
        }

    def _extract_topics_and_tags(
        self,
        scenes: List[Scene],
        overview: Dict
    ) -> Dict:
        """提取主題和標籤"""

        # 收集所有關鍵元素
        all_elements = []
        for scene in scenes:
            all_elements.extend(scene.key_elements)

        # 統計頻率
        from collections import Counter
        element_counter = Counter(all_elements)

        # 提取主要話題（出現次數 > 2）
        topics = [elem for elem, count in element_counter.most_common(10) if count > 2]

        # 提取標籤（出現次數 > 1）
        tags = [elem for elem, count in element_counter.most_common(20) if count > 1]

        # 添加類別標籤
        tags.insert(0, overview['likely_category'])

        # 添加內容密度標籤
        if overview['content_density'] == 'high':
            tags.append('fast-paced')
        elif overview['content_density'] == 'low':
            tags.append('slow-paced')

        return {
            'topics': topics[:5],  # 最多 5 個主題
            'tags': list(set(tags))[:15],  # 最多 15 個標籤，去重
            'category': overview['likely_category'],
            'language': 'zh-TW'  # 繁體中文
        }

    def _create_chapters(
        self,
        video_path: str,
        scenes: List[Scene],
        num_chapters: Optional[int] = None
    ) -> List[Chapter]:
        """創建章節標記"""

        if not scenes:
            return []

        # 決定章節數量
        if num_chapters is None:
            # 自動判斷：每 3-5 個場景一個章節
            num_chapters = max(3, min(10, len(scenes) // 4))

        # 將場景分組為章節
        scenes_per_chapter = len(scenes) // num_chapters
        chapters = []

        for i in range(num_chapters):
            start_idx = i * scenes_per_chapter
            end_idx = start_idx + scenes_per_chapter if i < num_chapters - 1 else len(scenes)

            chapter_scenes = scenes[start_idx:end_idx]

            if not chapter_scenes:
                continue

            # 創建章節
            chapter = self._create_single_chapter(
                video_path,
                chapter_scenes,
                i + 1
            )
            chapters.append(chapter)

        return chapters

    def _create_single_chapter(
        self,
        video_path: str,
        scenes: List[Scene],
        chapter_id: int
    ) -> Chapter:
        """創建單個章節"""

        start_time = scenes[0].start_time
        end_time = scenes[-1].end_time

        # 收集所有場景描述
        descriptions = [s.description for s in scenes]

        # 生成章節標題（使用第一個場景的主要元素）
        main_elements = scenes[0].key_elements[:2]
        if main_elements:
            title = f"第 {chapter_id} 章：{' & '.join(main_elements).title()}"
        else:
            title = f"第 {chapter_id} 章"

        # 生成章節描述（合併前 3 個場景的描述）
        description = " → ".join(descriptions[:3])
        if len(descriptions) > 3:
            description += "..."

        # 收集關鍵要點（取出現頻率最高的元素）
        all_elements = []
        for scene in scenes:
            all_elements.extend(scene.key_elements)

        from collections import Counter
        element_counter = Counter(all_elements)
        key_points = [elem for elem, count in element_counter.most_common(5)]

        # 使用第一個場景的幀作為縮圖
        thumbnail = scenes[0].start_frame_path if scenes[0].start_frame_path else ""

        return Chapter(
            id=chapter_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            thumbnail=thumbnail,
            key_points=key_points
        )

    def display_summary(self, summary: VideoSummary):
        """顯示摘要"""
        if not summary:
            console.print("[yellow]沒有可顯示的摘要[/yellow]")
            return

        console.print("\n" + "=" * 80)
        console.print(f"[bold cyan]📝 影片摘要：{summary.video_name}[/bold cyan]")
        console.print("=" * 80 + "\n")

        # 1. 基本資訊
        info_panel = f"""
[cyan]影片名稱：[/cyan] {summary.video_name}
[cyan]總長度：[/cyan] {self._format_time(summary.duration)}
[cyan]類別：[/cyan] {summary.category}
[cyan]語言：[/cyan] {summary.language}
[cyan]章節數：[/cyan] {len(summary.chapters)}
[cyan]置信度：[/cyan] {summary.confidence:.1%}
"""
        console.print(Panel(info_panel, title="📊 基本資訊", border_style="cyan"))

        # 2. 建議標題
        console.print(f"\n[bold yellow]💡 建議標題：[/bold yellow] {summary.title}\n")

        # 3. 多層次摘要
        console.print("[bold cyan]📄 摘要內容：[/bold cyan]\n")

        console.print(Panel(summary.short_summary, title="短摘要（社群媒體）", border_style="green"))
        console.print(Panel(summary.medium_summary, title="中摘要（影片描述）", border_style="blue"))
        console.print(Panel(summary.long_summary, title="長摘要（詳細說明）", border_style="magenta"))

        # 4. 主題和標籤
        console.print(f"\n[bold cyan]🏷️  主要話題：[/bold cyan] {', '.join(summary.key_topics)}")
        console.print(f"[bold cyan]🔖 標籤：[/bold cyan] {', '.join(summary.tags[:10])}\n")

        # 5. 章節列表
        if summary.chapters:
            console.print("[bold cyan]📑 章節標記：[/bold cyan]\n")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("#", width=4)
            table.add_column("標題", width=30)
            table.add_column("時間範圍", width=20)
            table.add_column("關鍵要點", width=30)

            for chapter in summary.chapters:
                time_range = f"{self._format_time(chapter.start_time)} - {self._format_time(chapter.end_time)}"
                key_points = ", ".join(chapter.key_points[:3])

                table.add_row(
                    str(chapter.id),
                    chapter.title,
                    time_range,
                    key_points
                )

            console.print(table)

    def save_summary(
        self,
        summary: VideoSummary,
        format: str = 'json'
    ) -> str:
        """
        保存摘要

        Args:
            summary: VideoSummary 物件
            format: 輸出格式（'json', 'txt', 'md', 'youtube', 'all'）

        Returns:
            輸出檔案路徑
        """
        video_path = summary.video_path
        video_name = Path(video_path).stem
        output_dir = Path(video_path).parent
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        saved_files = []

        # JSON 格式
        if format in ['json', 'all']:
            output_file = output_dir / f"{video_name}_summary_{timestamp}.json"
            data = asdict(summary)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            saved_files.append(output_file)
            console.print(f"[green]✓ JSON 已保存：{output_file}[/green]")

        # TXT 格式
        if format in ['txt', 'all']:
            output_file = output_dir / f"{video_name}_summary_{timestamp}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"影片摘要 - {summary.video_name}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"標題：{summary.title}\n")
                f.write(f"總長度：{self._format_time(summary.duration)}\n")
                f.write(f"類別：{summary.category}\n")
                f.write(f"生成時間：{summary.generated_at}\n\n")

                f.write("短摘要：\n")
                f.write(summary.short_summary + "\n\n")

                f.write("中摘要：\n")
                f.write(summary.medium_summary + "\n\n")

                f.write("長摘要：\n")
                f.write(summary.long_summary + "\n\n")

                f.write(f"主要話題：{', '.join(summary.key_topics)}\n")
                f.write(f"標籤：{', '.join(summary.tags)}\n\n")

                if summary.chapters:
                    f.write("章節：\n")
                    for chapter in summary.chapters:
                        f.write(f"  {chapter.id}. {chapter.title} ({self._format_time(chapter.start_time)} - {self._format_time(chapter.end_time)})\n")
                        f.write(f"     {chapter.description}\n")
                        f.write(f"     關鍵要點：{', '.join(chapter.key_points)}\n\n")

            saved_files.append(output_file)
            console.print(f"[green]✓ TXT 已保存：{output_file}[/green]")

        # Markdown 格式
        if format in ['md', 'all']:
            output_file = output_dir / f"{video_name}_summary_{timestamp}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {summary.title}\n\n")
                f.write(f"**影片：** {summary.video_name}  \n")
                f.write(f"**總長度：** {self._format_time(summary.duration)}  \n")
                f.write(f"**類別：** {summary.category}  \n")
                f.write(f"**生成時間：** {summary.generated_at}  \n\n")

                f.write("## 📄 摘要\n\n")
                f.write(f"### 短摘要（社群媒體）\n\n{summary.short_summary}\n\n")
                f.write(f"### 中摘要（影片描述）\n\n{summary.medium_summary}\n\n")
                f.write(f"### 詳細摘要\n\n{summary.long_summary}\n\n")

                f.write("## 🏷️ 主題與標籤\n\n")
                f.write(f"**主要話題：** {', '.join(summary.key_topics)}  \n")
                f.write(f"**標籤：** {', '.join(summary.tags)}  \n\n")

                if summary.chapters:
                    f.write("## 📑 章節\n\n")
                    for chapter in summary.chapters:
                        f.write(f"### {chapter.id}. {chapter.title}\n\n")
                        f.write(f"**時間：** {self._format_time(chapter.start_time)} - {self._format_time(chapter.end_time)}  \n")
                        f.write(f"**描述：** {chapter.description}  \n")
                        f.write(f"**關鍵要點：** {', '.join(chapter.key_points)}  \n\n")

            saved_files.append(output_file)
            console.print(f"[green]✓ Markdown 已保存：{output_file}[/green]")

        # YouTube 描述格式
        if format in ['youtube', 'all']:
            output_file = output_dir / f"{video_name}_youtube_description_{timestamp}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(summary.medium_summary + "\n\n")

                if summary.chapters:
                    f.write("章節：\n")
                    for chapter in summary.chapters:
                        # YouTube 章節格式：MM:SS 標題
                        f.write(f"{self._format_time(chapter.start_time)} {chapter.title}\n")
                    f.write("\n")

                f.write(f"#{'  #'.join(summary.tags[:10])}\n")

            saved_files.append(output_file)
            console.print(f"[green]✓ YouTube 描述已保存：{output_file}[/green]")

        return str(saved_files[0]) if saved_files else ""

    def _format_time(self, seconds: float) -> str:
        """格式化時間（秒 -> mm:ss）"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"


# ==================== CLI 介面 ====================

def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='Gemini 智能影片摘要')
    parser.add_argument('video', help='影片檔案路徑')
    parser.add_argument('--model', default='gemini-2.0-flash-exp', help='使用的模型')
    parser.add_argument('--chapters', type=int, help='章節數量（預設自動判斷）')
    parser.add_argument('--style', choices=['concise', 'balanced', 'detailed'], default='balanced',
                       help='摘要風格')
    parser.add_argument('--no-scene-detection', action='store_true', help='停用場景檢測')
    parser.add_argument('--output', choices=['json', 'txt', 'md', 'youtube', 'all'], default='all',
                       help='輸出格式')

    args = parser.parse_args()

    # 檢查檔案
    if not os.path.isfile(args.video):
        console.print(f"[red]錯誤：找不到影片檔案：{args.video}[/red]")
        return

    # 創建摘要器
    summarizer = VideoSummarizer(
        model_name=args.model,
        use_scene_detection=not args.no_scene_detection
    )

    # 生成摘要
    summary = summarizer.generate_summary(
        args.video,
        num_chapters=args.chapters,
        summary_style=args.style
    )

    if summary:
        # 顯示結果
        summarizer.display_summary(summary)

        # 保存結果
        summarizer.save_summary(summary, format=args.output)


if __name__ == "__main__":
    main()
