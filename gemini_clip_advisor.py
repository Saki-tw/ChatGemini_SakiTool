#!/usr/bin/env python3
"""
Gemini AI 驅動的剪輯建議模組
使用 AI 分析影片內容,提供智能剪輯建議和編輯推薦
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
from gemini_scene_detector import SceneDetector, Scene
from utils.api_client import get_gemini_client
from google.genai import types

# 導入價格模組
from utils.pricing_loader import get_pricing_calculator, PRICING_ENABLED
from gemini_pricing import USD_TO_TWD
from utils.i18n import safe_t

console = Console()
client = get_gemini_client()

# 初始化價格計算器
global_pricing_calculator = get_pricing_calculator(silent=True)


@dataclass
class ClipSuggestion:
    """剪輯建議資料結構"""
    id: int
    start_time: float          # 開始時間（秒）
    end_time: float            # 結束時間（秒）
    duration: float            # 持續時間（秒）
    clip_type: str             # 類型："highlight", "transition", "key_moment", "intro", "outro"
    description: str           # 片段描述
    reasoning: str             # 推薦理由
    confidence: float          # 置信度（0-1）
    engagement_score: float    # 參與度評分（0-10）
    tags: List[str]            # 標籤列表
    frame_preview: str         # 預覽幀路徑
    editing_tips: List[str]    # 編輯建議


class ClipAdvisor:
    """AI 剪輯建議器"""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        use_scene_detection: bool = True
    ):
        """
        初始化剪輯建議器

        Args:
            model_name: 使用的 Gemini 模型
            use_scene_detection: 是否使用場景檢測結果
        """
        self.model_name = model_name
        self.use_scene_detection = use_scene_detection
        self.preprocessor = VideoPreprocessor()
        self.scene_detector = SceneDetector(model_name=model_name) if use_scene_detection else None

    def analyze_and_suggest(
        self,
        video_path: str,
        target_duration: Optional[float] = None,
        clip_types: Optional[List[str]] = None,
        num_suggestions: int = 10
    ) -> List[ClipSuggestion]:
        """
        分析影片並生成剪輯建議

        Args:
            video_path: 影片檔案路徑
            target_duration: 目標總長度（秒）,None 表示不限制
            clip_types: 要生成的片段類型列表,None 表示全部
            num_suggestions: 建議數量

        Returns:
            剪輯建議列表
        """
        console.print(safe_t('media.clip.analysis_title', fallback='\n[bold #E8C4F0]🎬 AI 剪輯建議分析[/bold #E8C4F0]\n'))
        console.print(safe_t('media.clip.video_file', fallback='📁 影片：{name}', name=os.path.basename(video_path)))

        # 1. 獲取影片資訊
        info = self.preprocessor.get_video_info(video_path)
        if not info:
            console.print(safe_t('error.video_info_failed', fallback='[dim #E8C4F0]錯誤：無法獲取影片資訊[/red]'))
            return []

        duration = info['duration']
        console.print(safe_t('media.clip.total_duration', fallback='⏱️  總長度：{time}', time=self._format_time(duration)))

        if target_duration:
            console.print(safe_t('media.clip.target_duration', fallback='🎯 目標長度：{time}', time=self._format_time(target_duration)))

        # 2. 場景檢測（如果啟用）
        scenes = []
        if self.use_scene_detection:
            console.print(safe_t('media.clip.scene_detection', fallback='\n[#E8C4F0]📦 執行場景檢測...[/#E8C4F0]'))
            scenes = self.scene_detector.detect_scenes(video_path, num_keyframes=20)
            console.print(safe_t('media.clip.scenes_found', fallback='✓ 檢測到 {count} 個場景', count=len(scenes)))

        # 3. 分析內容特徵
        console.print(safe_t('media.clip.analyzing_features', fallback='\n[#E8C4F0]🔍 分析影片內容特徵...[/#E8C4F0]'))
        content_features = self._analyze_content_features(video_path, scenes, duration)

        # 4. 生成剪輯建議
        console.print(safe_t('media.clip.generating_suggestions', fallback='\n[#E8C4F0]💡 生成剪輯建議...[/#E8C4F0]'))
        suggestions = self._generate_suggestions(
            video_path,
            scenes,
            content_features,
            duration,
            target_duration,
            clip_types,
            num_suggestions
        )

        # 5. 排序並篩選
        suggestions = self._rank_and_filter_suggestions(suggestions, num_suggestions)

        console.print(safe_t('media.clip.suggestions_generated', fallback='\n[#B565D8]✓ 已生成 {count} 個剪輯建議[/green]', count=len(suggestions)))

        return suggestions

    def _analyze_content_features(
        self,
        video_path: str,
        scenes: List[Scene],
        duration: float
    ) -> Dict:
        """分析影片內容特徵"""
        features = {
            'has_scenes': len(scenes) > 0,
            'scene_count': len(scenes),
            'avg_scene_duration': 0,
            'scene_variety': 0,
            'key_moments': [],
            'pacing': 'unknown'
        }

        if scenes:
            # 計算平均場景長度
            scene_durations = [s.end_time - s.start_time for s in scenes]
            features['avg_scene_duration'] = sum(scene_durations) / len(scene_durations)

            # 評估場景多樣性（基於描述差異）
            unique_keywords = set()
            for scene in scenes:
                unique_keywords.update(scene.key_elements)
            features['scene_variety'] = len(unique_keywords)

            # 識別關鍵時刻（高置信度或長場景）
            for scene in scenes:
                scene_duration = scene.end_time - scene.start_time
                if scene.confidence > 0.8 or scene_duration > features['avg_scene_duration'] * 1.5:
                    features['key_moments'].append({
                        'time': scene.start_time,
                        'description': scene.description,
                        'duration': scene_duration
                    })

            # 評估節奏（快速/中等/緩慢）
            if features['avg_scene_duration'] < 5:
                features['pacing'] = 'fast'
            elif features['avg_scene_duration'] < 10:
                features['pacing'] = 'medium'
            else:
                features['pacing'] = 'slow'

        return features

    def _generate_suggestions(
        self,
        video_path: str,
        scenes: List[Scene],
        features: Dict,
        duration: float,
        target_duration: Optional[float],
        clip_types: Optional[List[str]],
        num_suggestions: int
    ) -> List[ClipSuggestion]:
        """生成剪輯建議"""
        suggestions = []
        suggestion_id = 1

        # 定義片段類型策略
        all_clip_types = ['highlight', 'key_moment', 'transition', 'intro', 'outro']
        requested_types = clip_types if clip_types else all_clip_types

        # 1. 開場建議（如果請求）
        if 'intro' in requested_types and duration > 10:
            suggestions.append(self._suggest_intro(video_path, scenes, suggestion_id))
            suggestion_id += 1

        # 2. 結尾建議（如果請求）
        if 'outro' in requested_types and duration > 10:
            suggestions.append(self._suggest_outro(video_path, scenes, duration, suggestion_id))
            suggestion_id += 1

        # 3. 關鍵時刻建議
        if 'key_moment' in requested_types:
            for moment in features['key_moments'][:5]:  # 最多 5 個
                suggestion = self._suggest_key_moment(
                    video_path,
                    moment,
                    features,
                    suggestion_id
                )
                if suggestion:
                    suggestions.append(suggestion)
                    suggestion_id += 1

        # 4. 精彩片段建議
        if 'highlight' in requested_types and scenes:
            highlight_suggestions = self._suggest_highlights(
                video_path,
                scenes,
                features,
                num_suggestions,
                suggestion_id
            )
            suggestions.extend(highlight_suggestions)
            suggestion_id += len(highlight_suggestions)

        # 5. 轉場建議
        if 'transition' in requested_types and scenes:
            transition_suggestions = self._suggest_transitions(
                video_path,
                scenes,
                suggestion_id
            )
            suggestions.extend(transition_suggestions[:3])  # 最多 3 個

        return suggestions

    def _suggest_intro(
        self,
        video_path: str,
        scenes: List[Scene],
        suggestion_id: int
    ) -> ClipSuggestion:
        """建議開場片段"""
        # 使用前 5-10 秒作為開場
        start_time = 0
        end_time = min(10.0, scenes[0].end_time if scenes else 10.0)
        duration = end_time - start_time

        # 提取預覽幀
        frame_path = self._extract_preview_frame(video_path, start_time + duration / 2)

        return ClipSuggestion(
            id=suggestion_id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            clip_type="intro",
            description="影片開場片段",
            reasoning="開場片段可以吸引觀眾注意,建立影片基調",
            confidence=0.9,
            engagement_score=8.0,
            tags=["opening", "intro", "start"],
            frame_preview=frame_path,
            editing_tips=[
                "可添加標題文字或 Logo",
                "考慮添加背景音樂淡入效果",
                "確保音量平衡"
            ]
        )

    def _suggest_outro(
        self,
        video_path: str,
        scenes: List[Scene],
        duration: float,
        suggestion_id: int
    ) -> ClipSuggestion:
        """建議結尾片段"""
        # 使用最後 5-10 秒作為結尾
        end_time = duration
        start_time = max(duration - 10.0, scenes[-1].start_time if scenes else duration - 10.0)
        clip_duration = end_time - start_time

        # 提取預覽幀
        frame_path = self._extract_preview_frame(video_path, start_time + clip_duration / 2)

        return ClipSuggestion(
            id=suggestion_id,
            start_time=start_time,
            end_time=end_time,
            duration=clip_duration,
            clip_type="outro",
            description="影片結尾片段",
            reasoning="結尾片段可以總結內容,引導後續行動",
            confidence=0.9,
            engagement_score=7.5,
            tags=["ending", "outro", "conclusion"],
            frame_preview=frame_path,
            editing_tips=[
                "可添加 CTA（行動呼籲）",
                "考慮添加相關影片推薦",
                "添加音樂淡出效果"
            ]
        )

    def _suggest_key_moment(
        self,
        video_path: str,
        moment: Dict,
        features: Dict,
        suggestion_id: int
    ) -> Optional[ClipSuggestion]:
        """建議關鍵時刻片段"""
        start_time = max(0, moment['time'] - 2)  # 前 2 秒
        end_time = min(moment['time'] + moment['duration'] + 2, moment['time'] + 15)  # 最多 15 秒
        duration = end_time - start_time

        # 提取預覽幀
        frame_path = self._extract_preview_frame(video_path, moment['time'])

        # 分析該時刻的內容
        analysis = self._analyze_moment(video_path, moment['time'], moment['description'])

        return ClipSuggestion(
            id=suggestion_id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            clip_type="key_moment",
            description=moment['description'],
            reasoning=f"關鍵時刻：{analysis.get('reasoning', '重要場景或轉折點')}",
            confidence=0.85,
            engagement_score=analysis.get('engagement_score', 8.5),
            tags=analysis.get('tags', ['important', 'key']),
            frame_preview=frame_path,
            editing_tips=analysis.get('tips', [
                "考慮添加特效或慢動作",
                "可能適合添加字幕說明",
                "確保音訊清晰"
            ])
        )

    def _suggest_highlights(
        self,
        video_path: str,
        scenes: List[Scene],
        features: Dict,
        num_suggestions: int,
        start_id: int
    ) -> List[ClipSuggestion]:
        """建議精彩片段"""
        suggestions = []

        # 根據場景置信度和長度選擇精彩片段
        scored_scenes = []
        for scene in scenes:
            # 跳過太短的場景
            scene_duration = scene.end_time - scene.start_time
            if scene_duration < 3:
                continue

            # 計算分數（置信度 + 長度適中性）
            duration_score = 1.0 if 5 <= scene_duration <= 15 else 0.5
            total_score = scene.confidence * 0.7 + duration_score * 0.3

            scored_scenes.append((total_score, scene))

        # 排序並選擇前 N 個
        scored_scenes.sort(reverse=True, key=lambda x: x[0])
        top_scenes = scored_scenes[:min(num_suggestions, len(scored_scenes))]

        for idx, (score, scene) in enumerate(top_scenes):
            scene_duration = scene.end_time - scene.start_time

            # 分析場景內容
            analysis = self._analyze_scene_for_highlight(scene)

            suggestions.append(ClipSuggestion(
                id=start_id + idx,
                start_time=scene.start_time,
                end_time=scene.end_time,
                duration=scene_duration,
                clip_type="highlight",
                description=scene.description,
                reasoning=f"高質量場景：{analysis.get('reasoning', '視覺效果好,內容豐富')}",
                confidence=score,
                engagement_score=analysis.get('engagement_score', score * 10),
                tags=scene.key_elements + analysis.get('extra_tags', []),
                frame_preview=scene.start_frame_path,
                editing_tips=analysis.get('tips', [
                    "可作為獨立短片發布",
                    "適合社群媒體分享",
                    "考慮添加背景音樂"
                ])
            ))

        return suggestions

    def _suggest_transitions(
        self,
        video_path: str,
        scenes: List[Scene],
        start_id: int
    ) -> List[ClipSuggestion]:
        """建議轉場片段"""
        suggestions = []

        # 識別場景間的轉場點
        for i in range(len(scenes) - 1):
            current_scene = scenes[i]
            next_scene = scenes[i + 1]

            # 轉場區間：當前場景結束前 1 秒到下一場景開始後 1 秒
            start_time = max(0, current_scene.end_time - 1)
            end_time = min(next_scene.start_time + 1, next_scene.end_time)
            duration = end_time - start_time

            if duration < 0.5:  # 跳過太短的轉場
                continue

            # 提取預覽幀
            frame_path = self._extract_preview_frame(video_path, current_scene.end_time)

            # 分析轉場類型
            transition_type = self._analyze_transition_type(current_scene, next_scene)

            suggestions.append(ClipSuggestion(
                id=start_id + i,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                clip_type="transition",
                description=f"從「{current_scene.description}」到「{next_scene.description}」",
                reasoning=f"場景轉換點：{transition_type}",
                confidence=0.7,
                engagement_score=6.0,
                tags=["transition", transition_type, "scene_change"],
                frame_preview=frame_path,
                editing_tips=[
                    f"建議使用{transition_type}轉場效果",
                    "確保音訊順暢過渡",
                    "可添加轉場音效"
                ]
            ))

        return suggestions

    def _analyze_moment(self, video_path: str, timestamp: float, description: str) -> Dict:
        """分析關鍵時刻"""
        # 簡化版：基於描述的關鍵字分析
        keywords = description.lower()

        analysis = {
            'reasoning': '重要場景或轉折點',
            'engagement_score': 8.0,
            'tags': ['important', 'key'],
            'tips': [
                "考慮添加特效或慢動作",
                "可能適合添加字幕說明",
                "確保音訊清晰"
            ]
        }

        # 根據關鍵字調整
        if any(word in keywords for word in ['person', 'people', 'face', '人物', '人']):
            analysis['tags'].append('人物')
            analysis['engagement_score'] += 0.5
            analysis['tips'].append("人物特寫可提升觀眾連結")

        if any(word in keywords for word in ['action', 'moving', 'motion', '動作', '運動']):
            analysis['tags'].append('動態')
            analysis['engagement_score'] += 0.5
            analysis['tips'].append("動態畫面可考慮慢動作效果")

        if any(word in keywords for word in ['text', 'sign', 'writing', '文字', '標誌']):
            analysis['tags'].append('資訊')
            analysis['reasoning'] = '包含重要文字或標誌資訊'

        return analysis

    def _analyze_scene_for_highlight(self, scene: Scene) -> Dict:
        """分析場景作為精彩片段的潛力"""
        analysis = {
            'reasoning': '視覺效果好,內容豐富',
            'engagement_score': scene.confidence * 10,
            'extra_tags': [],
            'tips': [
                "可作為獨立短片發布",
                "適合社群媒體分享"
            ]
        }

        # 根據場景元素調整
        if len(scene.key_elements) > 5:
            analysis['reasoning'] = '內容元素豐富,視覺層次多'
            analysis['engagement_score'] += 0.5

        # 根據場景長度調整
        duration = scene.end_time - scene.start_time
        if 8 <= duration <= 12:
            analysis['extra_tags'].append('optimal_length')
            analysis['tips'].append("長度適中,適合各平台")
        elif duration > 15:
            analysis['tips'].append("可考慮剪輯為多個片段")

        return analysis

    def _analyze_transition_type(self, scene1: Scene, scene2: Scene) -> str:
        """分析轉場類型"""
        # 基於場景元素的相似度判斷轉場類型
        common_elements = set(scene1.key_elements) & set(scene2.key_elements)
        similarity = len(common_elements) / max(len(scene1.key_elements), len(scene2.key_elements), 1)

        if similarity > 0.5:
            return "淡入淡出（內容相關）"
        elif similarity > 0.2:
            return "交叉淡化（部分相關）"
        else:
            return "切換（對比場景）"

    def _extract_preview_frame(self, video_path: str, timestamp: float) -> str:
        """提取預覽幀"""
        output_dir = Path(video_path).parent / f"{Path(video_path).stem}_clip_previews"
        output_dir.mkdir(exist_ok=True)

        frame_filename = f"preview_{timestamp:.2f}s.jpg"
        frame_path = output_dir / frame_filename

        # 使用 FFmpeg 提取幀
        import subprocess
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            str(frame_path)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return str(frame_path)
        except Exception as e:
            console.print(safe_t('media.clip.preview_frame_warning', fallback='[#E8C4F0]警告：提取預覽幀失敗 ({time}s): {error}[/#E8C4F0]', time=timestamp, error=e))
            return ""

    def _rank_and_filter_suggestions(
        self,
        suggestions: List[ClipSuggestion],
        max_count: int
    ) -> List[ClipSuggestion]:
        """排序並篩選建議"""
        # 綜合評分：置信度 40% + 參與度評分 60%
        for suggestion in suggestions:
            suggestion.engagement_score = (
                suggestion.confidence * 0.4 * 10 +
                suggestion.engagement_score * 0.6
            )

        # 排序
        suggestions.sort(key=lambda x: x.engagement_score, reverse=True)

        # 限制數量
        return suggestions[:max_count]

    def display_suggestions(self, suggestions: List[ClipSuggestion]):
        """顯示剪輯建議"""
        if not suggestions:
            console.print(safe_t('media.clip.no_suggestions', fallback='[#E8C4F0]沒有生成剪輯建議[/#E8C4F0]'))
            return

        console.print(safe_t('media.clip.suggestions_list', fallback='\n[bold #E8C4F0]📋 剪輯建議列表（{count} 個）[/bold #E8C4F0]\n', count=len(suggestions)))

        # 創建表格
        table = Table(show_header=True, header_style="bold #B565D8")
        console_width = console.width or 120
        table.add_column("#", style="dim", width=max(4, int(console_width * 0.03)))
        table.add_column("類型", width=max(10, int(console_width * 0.10)))
        table.add_column("時間範圍", width=max(18, int(console_width * 0.15)))
        table.add_column("描述", width=max(35, int(console_width * 0.50)))
        table.add_column("評分", justify="right", width=max(8, int(console_width * 0.08)))

        for suggestion in suggestions:
            # 類型顏色
            type_colors = {
                'intro': '#E8C4F0',
                'outro': '#E8C4F0',
                'highlight': 'green',
                'key_moment': '#E8C4F0',
                'transition': '#E8C4F0'
            }
            type_color = type_colors.get(suggestion.clip_type, 'white')

            # 時間範圍
            time_range = f"{self._format_time(suggestion.start_time)} - {self._format_time(suggestion.end_time)}"

            # 評分顏色
            score = suggestion.engagement_score
            if score >= 8:
                score_style = "bold green"
            elif score >= 6:
                score_style = "#E8C4F0"
            else:
                score_style = "dim"

            table.add_row(
                str(suggestion.id),
                f"[{type_color}]{suggestion.clip_type}[/{type_color}]",
                time_range,
                suggestion.description[:40] + "..." if len(suggestion.description) > 40 else suggestion.description,
                f"[{score_style}]{score:.1f}[/{score_style}]"
            )

        console.print(table)

        # 顯示詳細資訊
        console.print(safe_t('media.clip.detailed_suggestions', fallback='\n[bold #E8C4F0]💡 詳細建議：[/bold #E8C4F0]\n'))
        for suggestion in suggestions[:5]:  # 只顯示前 5 個的詳細資訊
            self._display_suggestion_detail(suggestion)

    def _display_suggestion_detail(self, suggestion: ClipSuggestion):
        """顯示單個建議的詳細資訊"""
        content = f"""
[#E8C4F0]時間：[/#E8C4F0] {self._format_time(suggestion.start_time)} - {self._format_time(suggestion.end_time)} ({suggestion.duration:.1f}s)
[#E8C4F0]類型：[/#E8C4F0] {suggestion.clip_type}
[#E8C4F0]描述：[/#E8C4F0] {suggestion.description}
[#E8C4F0]推薦理由：[/#E8C4F0] {suggestion.reasoning}
[#E8C4F0]評分：[/#E8C4F0] {suggestion.engagement_score:.1f}/10
[#E8C4F0]標籤：[/#E8C4F0] {', '.join(suggestion.tags)}

[#E8C4F0]編輯建議：[/#E8C4F0]
"""
        for tip in suggestion.editing_tips:
            content += f"  • {tip}\n"

        console.print(Panel(content, title=f"[bold]#{suggestion.id} - {suggestion.clip_type.upper()}[/bold]", border_style="#B565D8"))
        console.print()

    def save_suggestions(
        self,
        suggestions: List[ClipSuggestion],
        video_path: str,
        format: str = 'json'
    ) -> str:
        """
        保存剪輯建議

        Args:
            suggestions: 建議列表
            video_path: 影片路徑
            format: 輸出格式（'json', 'txt', 'edl'）

        Returns:
            輸出檔案路徑
        """
        video_name = Path(video_path).stem
        output_dir = Path(video_path).parent
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == 'json':
            output_file = output_dir / f"{video_name}_clip_suggestions_{timestamp}.json"
            data = {
                'video': os.path.basename(video_path),
                'generated_at': datetime.now().isoformat(),
                'total_suggestions': len(suggestions),
                'suggestions': [asdict(s) for s in suggestions]
            }
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif format == 'txt':
            output_file = output_dir / f"{video_name}_clip_suggestions_{timestamp}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"影片剪輯建議 - {os.path.basename(video_path)}\n")
                f.write(f"生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"總建議數：{len(suggestions)}\n")
                f.write("=" * 80 + "\n\n")

                for suggestion in suggestions:
                    f.write(f"#{suggestion.id} - {suggestion.clip_type.upper()}\n")
                    f.write(f"時間：{self._format_time(suggestion.start_time)} - {self._format_time(suggestion.end_time)} ({suggestion.duration:.1f}s)\n")
                    f.write(f"描述：{suggestion.description}\n")
                    f.write(f"推薦理由：{suggestion.reasoning}\n")
                    f.write(f"評分：{suggestion.engagement_score:.1f}/10\n")
                    f.write(f"標籤：{', '.join(suggestion.tags)}\n")
                    f.write("編輯建議：\n")
                    for tip in suggestion.editing_tips:
                        f.write(f"  • {tip}\n")
                    f.write("-" * 80 + "\n\n")

        elif format == 'edl':
            output_file = output_dir / f"{video_name}_clip_suggestions_{timestamp}.edl"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("TITLE: Clip Suggestions\n")
                f.write("FCM: NON-DROP FRAME\n\n")

                for idx, suggestion in enumerate(suggestions, 1):
                    # EDL 格式：編號 源 通道 類型 起始 結束 起始 結束
                    start_tc = self._seconds_to_timecode(suggestion.start_time)
                    end_tc = self._seconds_to_timecode(suggestion.end_time)

                    f.write(f"{idx:03d}  001      V     C        {start_tc} {end_tc} {start_tc} {end_tc}\n")
                    f.write(f"* FROM CLIP NAME: {suggestion.description}\n")
                    f.write(f"* COMMENT: {suggestion.clip_type} - {suggestion.reasoning}\n\n")

        else:
            console.print(safe_t('error.unsupported_format', fallback='[dim #E8C4F0]不支援的格式：{format}[/red]', format=format))
            return ""

        console.print(safe_t('media.clip.suggestions_saved', fallback='[#B565D8]✓ 剪輯建議已保存：{file}[/green]', file=output_file))
        return str(output_file)

    def _format_time(self, seconds: float) -> str:
        """格式化時間（秒 -> mm:ss）"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _seconds_to_timecode(self, seconds: float) -> str:
        """轉換秒數為時間碼（HH:MM:SS:FF）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * 30)  # 假設 30 fps
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


# ==================== CLI 介面 ====================

def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='Gemini AI 剪輯建議')
    parser.add_argument('video', help='影片檔案路徑')
    parser.add_argument('--model', default='gemini-2.0-flash-exp', help='使用的模型')
    parser.add_argument('--num', type=int, default=10, help='建議數量（預設 10）')
    parser.add_argument('--target-duration', type=float, help='目標總長度（秒）')
    parser.add_argument('--types', nargs='+', choices=['highlight', 'key_moment', 'transition', 'intro', 'outro'],
                       help='片段類型')
    parser.add_argument('--no-scene-detection', action='store_true', help='停用場景檢測')
    parser.add_argument('--output', choices=['json', 'txt', 'edl', 'all'], default='all', help='輸出格式')

    args = parser.parse_args()

    # 檢查檔案
    if not os.path.isfile(args.video):
        console.print(safe_t('error.video_not_found', fallback='[dim #E8C4F0]錯誤：找不到影片檔案：{path}[/red]', path=args.video))
        return

    # 創建建議器
    advisor = ClipAdvisor(
        model_name=args.model,
        use_scene_detection=not args.no_scene_detection
    )

    # 分析並生成建議
    suggestions = advisor.analyze_and_suggest(
        args.video,
        target_duration=args.target_duration,
        clip_types=args.types,
        num_suggestions=args.num
    )

    # 顯示結果
    advisor.display_suggestions(suggestions)

    # 保存結果
    if args.output == 'all':
        advisor.save_suggestions(suggestions, args.video, format='json')
        advisor.save_suggestions(suggestions, args.video, format='txt')
        advisor.save_suggestions(suggestions, args.video, format='edl')
    else:
        advisor.save_suggestions(suggestions, args.video, format=args.output)


if __name__ == "__main__":
    main()
