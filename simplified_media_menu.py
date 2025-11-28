#!/usr/bin/env python3
"""
精簡版影音功能選單
整合所有多媒體處理功能，減少選項，提升易用性
"""
import os
from rich.console import Console
from utils.input_helpers import safe_input

console = Console()


def show_simplified_media_menu(
    MEDIA_VIEWER_ENABLED,
    FLOW_ENGINE_ENABLED,
    IMAGEN_GENERATOR_ENABLED,
    AUDIO_PROCESSOR_ENABLED,
    VIDEO_EFFECTS_ENABLED,
    SUBTITLE_GENERATOR_ENABLED,
    SCENE_DETECTOR_ENABLED,
    CLIP_ADVISOR_ENABLED,
    VIDEO_SUMMARIZER_ENABLED,
    VIDEO_PREPROCESSOR_ENABLED,
    VIDEO_COMPOSITOR_ENABLED
):
    """顯示精簡版影音選單"""
    console.print("\n" + "=" * 60)
    console.print("[bold #E8C4F0]🎬 多媒體創作中心[/bold #E8C4F0]")
    console.print("=" * 60)

    # 第一層：核心功能（最常用）
    console.print("\n[bold #E8C4F0]>>> 創作生成[/bold #E8C4F0]")
    if FLOW_ENGINE_ENABLED:
        console.print("  [1] 影片生成 - Flow 引擎（1080p 長影片，自然語言）")
    console.print("  [2] 影片生成 - Veo 3.1（8秒快速生成）")
    if IMAGEN_GENERATOR_ENABLED:
        console.print("  [3] 圖像創作（生成/編輯/放大 - Imagen 3）")

    # 第二層：智能處理（整合多個工具）
    console.print("\n[bold #E8C4F0]>>> 智能處理[/bold #E8C4F0]")
    console.print("  [4] 影片工具箱（剪輯/特效/字幕/合併）")
    if AUDIO_PROCESSOR_ENABLED:
        console.print("  [5] 音訊工具箱（提取/混音/BGM/特效）")
    if MEDIA_VIEWER_ENABLED:
        console.print("  [6] 媒體分析器（圖片/影片 AI 分析）")

    # 第三層：AI 分析工具（進階）
    if SCENE_DETECTOR_ENABLED or CLIP_ADVISOR_ENABLED or VIDEO_SUMMARIZER_ENABLED:
        console.print("\n[bold #E8C4F0]>>> AI 影片分析（進階）[/bold #E8C4F0]")
        console.print("  [7] 完整 AI 分析（場景+剪輯+摘要）")

    console.print("\n  [0] 返回主選單\n")


def handle_flow_video_generation(PRICING_ENABLED, global_pricing_calculator, FlowEngine):
    """處理 Flow 引擎影片生成 - 使用 1080p 預設參數"""
    console.print("\n[#E8C4F0]🎬 Flow 引擎 - 智能影片生成（預設 1080p）[/#E8C4F0]\n")

    description = safe_input("請描述您想要的影片內容：").strip()
    if not description:
        console.print("[#E8C4F0]未輸入描述，取消操作[/#E8C4F0]")
        safe_input("\n按 Enter 繼續...")
        return

    duration_input = safe_input("目標時長（秒，預設 30）：").strip()
    target_duration = int(duration_input) if duration_input.isdigit() else 30

    # 智能建議
    if target_duration > 60:
        console.print("[dim yellow]💡 長影片已自動使用最佳參數：1080p, 16:9[/dim yellow]\n")

    # 預設使用最佳參數
    resolution = "1080p"
    aspect_ratio = "16:9"

    # 僅在需要時提供自訂選項
    custom_settings = safe_input("使用預設最佳參數（1080p, 16:9）？(Y/n): ").strip().lower()
    if custom_settings == 'n':
        # 解析度選擇
        console.print("\n[#E8C4F0]解析度：[/#E8C4F0]")
        console.print("  [1] 1080p (預設)")
        console.print("  [2] 720p")
        resolution_choice = safe_input("請選擇：").strip()
        resolution = "1080p" if resolution_choice != '2' else "720p"

        # 比例選擇
        console.print("\n[#E8C4F0]比例：[/#E8C4F0]")
        console.print("  [1] 16:9 (預設)")
        console.print("  [2] 9:16")
        ratio_choice = safe_input("請選擇：").strip()
        aspect_ratio = "16:9" if ratio_choice != '2' else "9:16"

    try:
        # 初始化 Flow Engine（傳入計價器與影片配置）
        if PRICING_ENABLED:
            engine = FlowEngine(
                pricing_calculator=global_pricing_calculator,
                resolution=resolution,
                aspect_ratio=aspect_ratio
            )
        else:
            engine = FlowEngine(
                resolution=resolution,
                aspect_ratio=aspect_ratio
            )

        console.print(f"\n[#E8C4F0]⏳ 開始生成 {target_duration}秒 影片（{resolution}, {aspect_ratio}）...[/#E8C4F0]")

        video_path = engine.generate_from_description(
            description=description,
            target_duration=target_duration,
            show_cost=PRICING_ENABLED
        )

        if video_path:
            console.print(f"\n[#B565D8]✅ 影片生成完成！[/#B565D8]")
            console.print(f"儲存路徑：{video_path}")
        else:
            console.print("\n[#E8C4F0]已取消生成[/#E8C4F0]")
    except Exception as e:
        console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    safe_input("\n按 Enter 繼續...")


def handle_veo_generation():
    """處理 Veo 基本生成"""
    console.print("\n[#E8C4F0]🎬 Veo 3.1 - 快速影片生成（8秒）[/#E8C4F0]\n")
    console.print("使用獨立工具：")
    console.print("  python gemini_veo_generator.py\n")
    console.print("功能：")
    console.print("  - 文字生成影片（8 秒，Veo 3.1）")
    console.print("  - 支援參考圖片")
    console.print("  - 自訂長寬比")
    safe_input("\n按 Enter 繼續...")


def handle_imagen_creation(PRICING_ENABLED, generate_image, edit_image, upscale_image):
    """處理圖像創作（生成/編輯/放大）"""
    console.print("\n[#E8C4F0]🎨 Imagen 3 圖像創作[/#E8C4F0]\n")
    console.print("選擇功能：")
    console.print("  [1] 生成圖片（Text-to-Image）")
    console.print("  [2] 編輯圖片（Image Editing）")
    console.print("  [3] 放大圖片（Upscaling）")
    console.print("  [0] 返回\n")

    img_choice = safe_input("請選擇：").strip()

    if img_choice == '1':
        # 生成圖片
        prompt = safe_input("\n請描述您想生成的圖片：").strip()
        if not prompt:
            console.print("[#E8C4F0]未輸入描述[/#E8C4F0]")
            safe_input("\n按 Enter 繼續...")
            return

        negative_prompt = safe_input("\n負面提示（避免的內容，可留空）：").strip()
        if not negative_prompt:
            negative_prompt = None

        console.print("\n選擇長寬比：")
        console.print("  1. 1:1 (正方形，預設)")
        console.print("  2. 16:9 (橫向)")
        console.print("  3. 9:16 (直向)")
        aspect_choice = safe_input("請選擇 (1-3, 預設=1): ").strip() or '1'
        aspect_ratios = {'1': '1:1', '2': '16:9', '3': '9:16'}
        aspect_ratio = aspect_ratios.get(aspect_choice, '1:1')

        num_input = safe_input("\n生成數量（1-4，預設=1）：").strip()
        number_of_images = int(num_input) if num_input.isdigit() and 1 <= int(num_input) <= 4 else 1

        try:
            output_paths = generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                show_cost=PRICING_ENABLED
            )
            console.print(f"\n[#B565D8]✅ 圖片已生成：{len(output_paths)} 張[/#B565D8]")

            open_img = safe_input("\n要開啟圖片嗎？(y/N): ").strip().lower()
            if open_img == 'y':
                for path in output_paths:
                    os.system(f'open "{path}"')
        except Exception as e:
            console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    elif img_choice == '2':
        # 編輯圖片
        image_path = safe_input("\n圖片路徑：").strip()
        if not os.path.isfile(image_path):
            console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
            safe_input("\n按 Enter 繼續...")
            return

        prompt = safe_input("\n請描述如何編輯此圖片：").strip()
        if not prompt:
            console.print("[#E8C4F0]未輸入編輯描述[/#E8C4F0]")
            safe_input("\n按 Enter 繼續...")
            return

        try:
            output_path = edit_image(
                image_path=image_path,
                prompt=prompt,
                show_cost=PRICING_ENABLED
            )
            console.print(f"\n[#B565D8]✅ 圖片已編輯：{output_path}[/#B565D8]")

            open_img = safe_input("\n要開啟圖片嗎？(y/N): ").strip().lower()
            if open_img == 'y':
                os.system(f'open "{output_path}"')
        except Exception as e:
            console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    elif img_choice == '3':
        # 放大圖片
        image_path = safe_input("\n圖片路徑：").strip()
        if not os.path.isfile(image_path):
            console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
            safe_input("\n按 Enter 繼續...")
            return

        try:
            output_path = upscale_image(
                image_path=image_path,
                show_cost=PRICING_ENABLED
            )
            console.print(f"\n[#B565D8]✅ 圖片已放大：{output_path}[/#B565D8]")

            open_img = safe_input("\n要開啟圖片嗎？(y/N): ").strip().lower()
            if open_img == 'y':
                os.system(f'open "{output_path}"')
        except Exception as e:
            console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    safe_input("\n按 Enter 繼續...")


def handle_video_toolbox(VIDEO_EFFECTS_ENABLED, SUBTITLE_GENERATOR_ENABLED, VIDEO_COMPOSITOR_ENABLED, VideoEffects, SubtitleGenerator):
    """處理影片工具箱（整合多個工具）"""
    console.print("\n[#E8C4F0]✂️ 影片工具箱[/#E8C4F0]\n")
    console.print("選擇工具：")
    console.print("  [1] 剪輯影片（時間裁切）")
    console.print("  [2] 添加特效（濾鏡/速度/浮水印）")
    if VIDEO_COMPOSITOR_ENABLED:
        console.print("  [3] 合併影片（無損拼接）")
    if SUBTITLE_GENERATOR_ENABLED:
        console.print("  [4] 字幕處理（生成/燒錄）")
    console.print("  [5] 影片資訊查詢")
    console.print("  [0] 返回\n")

    tool_choice = safe_input("請選擇：").strip()

    if tool_choice == '1' and VIDEO_EFFECTS_ENABLED:
        # 時間裁切
        video_path = safe_input("\n影片路徑：").strip()
        if not os.path.isfile(video_path):
            console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
            safe_input("\n按 Enter 繼續...")
            return

        start_input = safe_input("\n開始時間（秒，預設0）：").strip()
        end_input = safe_input("結束時間（秒，留空=影片結尾）：").strip()

        try:
            start_time = float(start_input) if start_input else 0
            end_time = float(end_input) if end_input else None

            effects = VideoEffects()
            output_path = effects.trim_video(video_path, start_time=start_time, end_time=end_time)
            console.print(f"\n[#B565D8]✅ 影片已裁切：{output_path}[/#B565D8]")
            console.print("[dim]提示：使用 -c copy 無損裁切，保持原始品質[/dim]")
        except Exception as e:
            console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    elif tool_choice == '2':
        # 特效子選單
        console.print("\n[#E8C4F0]選擇特效類型：[/#E8C4F0]")
        console.print("  [1] 濾鏡（黑白/復古/銳化等）")
        console.print("  [2] 速度調整（快轉/慢動作）")
        console.print("  [3] 添加浮水印")

        effect_choice = safe_input("\n請選擇：").strip()

        if effect_choice == '1' and VIDEO_EFFECTS_ENABLED:
            # 濾鏡效果
            video_path = safe_input("\n影片路徑：").strip()
            if not os.path.isfile(video_path):
                console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
                safe_input("\n按 Enter 繼續...")
                return

            console.print("\n[#E8C4F0]選擇濾鏡：[/#E8C4F0]")
            console.print("  [1] 黑白 (grayscale)")
            console.print("  [2] 復古 (sepia)")
            console.print("  [3] 懷舊 (vintage)")
            console.print("  [4] 銳化 (sharpen)")
            console.print("  [5] 模糊 (blur)")
            console.print("  [6] 增亮 (brighten)")
            console.print("  [7] 增強對比 (contrast)")
            filter_choice = safe_input("請選擇 (1-7): ").strip()

            filter_map = {
                '1': 'grayscale',
                '2': 'sepia',
                '3': 'vintage',
                '4': 'sharpen',
                '5': 'blur',
                '6': 'brighten',
                '7': 'contrast'
            }
            filter_name = filter_map.get(filter_choice)

            if filter_name:
                try:
                    effects = VideoEffects()
                    output_path = effects.apply_filter(video_path, filter_name=filter_name, quality='medium')
                    console.print(f"\n[#B565D8]✅ 濾鏡已套用：{output_path}[/#B565D8]")
                except Exception as e:
                    console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

        elif effect_choice == '2' and VIDEO_EFFECTS_ENABLED:
            # 速度調整
            video_path = safe_input("\n影片路徑：").strip()
            if not os.path.isfile(video_path):
                console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
                safe_input("\n按 Enter 繼續...")
                return

            console.print("\n[#E8C4F0]常用速度：[/#E8C4F0]")
            console.print("  0.5 = 慢動作（一半速度）")
            console.print("  1.0 = 正常速度")
            console.print("  2.0 = 快轉（兩倍速度）")
            speed_input = safe_input("\n請輸入速度倍數（預設1.0）：").strip()

            try:
                speed_factor = float(speed_input) if speed_input else 1.0
                if speed_factor > 0:
                    effects = VideoEffects()
                    output_path = effects.adjust_speed(video_path, speed_factor=speed_factor, quality='medium')
                    console.print(f"\n[#B565D8]✅ 速度已調整：{output_path}[/#B565D8]")
                else:
                    console.print("[#E8C4F0]速度必須大於0[/#E8C4F0]")
            except ValueError:
                console.print("[#E8C4F0]無效的數值[/#E8C4F0]")
            except Exception as e:
                console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    elif tool_choice == '4' and SUBTITLE_GENERATOR_ENABLED:
        # 字幕處理
        console.print("\n[#E8C4F0]字幕處理：[/#E8C4F0]")
        console.print("  [1] 生成字幕（語音辨識+翻譯）")
        console.print("  [2] 燒錄字幕（已有字幕檔）")

        sub_choice = safe_input("\n請選擇：").strip()

        if sub_choice == '1':
            # 生成字幕
            video_path = safe_input("\n影片路徑：").strip()
            if not os.path.isfile(video_path):
                console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
                safe_input("\n按 Enter 繼續...")
                return

            translate_choice = safe_input("\n是否翻譯字幕？(y/N): ").strip().lower()
            translate = (translate_choice == 'y')

            target_lang = "zh-TW" if translate else None

            try:
                generator = SubtitleGenerator()
                subtitle_path = generator.generate_subtitles(
                    video_path=video_path,
                    format="srt",
                    translate=translate,
                    target_language=target_lang,
                    show_cost=False
                )
                console.print(f"\n[#B565D8]✅ 字幕已生成：{subtitle_path}[/#B565D8]")

                burn_choice = safe_input("\n要將字幕燒錄到影片嗎？(y/N): ").strip().lower()
                if burn_choice == 'y':
                    video_with_subs = generator.burn_subtitles(video_path, subtitle_path)
                    console.print(f"\n[#B565D8]✅ 燒錄完成：{video_with_subs}[/#B565D8]")
            except Exception as e:
                console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    elif tool_choice == '5':
        # 影片資訊查詢
        console.print("\n[#E8C4F0]影片資訊查詢[/#E8C4F0]\n")
        console.print("使用工具：")
        console.print("  python gemini_video_preprocessor.py <影片路徑> info")

    safe_input("\n按 Enter 繼續...")


def handle_audio_toolbox(AUDIO_PROCESSOR_ENABLED, AudioProcessor):
    """處理音訊工具箱"""
    console.print("\n[#E8C4F0]🎵 音訊工具箱[/#E8C4F0]\n")
    console.print("選擇工具：")
    console.print("  [1] 提取音訊（從影片提取）")
    console.print("  [2] 混音/替換（合併音訊到影片）")
    console.print("  [3] 音量調整")
    console.print("  [4] 添加背景音樂（BGM）")
    console.print("  [5] 淡入淡出效果")
    console.print("  [0] 返回\n")

    audio_choice = safe_input("請選擇：").strip()

    if audio_choice == '1':
        # 提取音訊
        video_path = safe_input("\n影片路徑：").strip()
        if not os.path.isfile(video_path):
            console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
            safe_input("\n按 Enter 繼續...")
            return

        console.print("\n[#E8C4F0]音訊格式：[/#E8C4F0]")
        console.print("  [1] AAC (預設)")
        console.print("  [2] MP3")
        console.print("  [3] WAV")
        format_choice = safe_input("請選擇：").strip()
        format_map = {'1': 'aac', '2': 'mp3', '3': 'wav'}
        audio_format = format_map.get(format_choice, 'aac')

        try:
            processor = AudioProcessor()
            output_path = processor.extract_audio(video_path, format=audio_format)
            console.print(f"\n[#B565D8]✅ 音訊已提取：{output_path}[/#B565D8]")
        except Exception as e:
            console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    elif audio_choice == '3':
        # 音量調整
        file_path = safe_input("\n影片/音訊路徑：").strip()
        if not os.path.isfile(file_path):
            console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
            safe_input("\n按 Enter 繼續...")
            return

        volume_input = safe_input("音量倍數（0.5=50%, 1.0=100%, 2.0=200%，預設1.0）：").strip()
        try:
            volume = float(volume_input) if volume_input else 1.0
            if volume > 0:
                processor = AudioProcessor()
                output_path = processor.adjust_volume(file_path, volume)
                console.print(f"\n[#B565D8]✅ 音量已調整：{output_path}[/#B565D8]")
            else:
                console.print("[#E8C4F0]音量必須大於0[/#E8C4F0]")
        except ValueError:
            console.print("[#E8C4F0]無效的數值[/#E8C4F0]")
        except Exception as e:
            console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    elif audio_choice == '4':
        # 添加背景音樂
        video_path = safe_input("\n影片路徑：").strip()
        music_path = safe_input("背景音樂路徑：").strip()

        if os.path.isfile(video_path) and os.path.isfile(music_path):
            try:
                processor = AudioProcessor()
                output_path = processor.add_background_music(
                    video_path, music_path,
                    music_volume=0.3,
                    fade_duration=2.0
                )
                console.print(f"\n[#B565D8]✅ 背景音樂已添加：{output_path}[/#B565D8]")
            except Exception as e:
                console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")
        else:
            console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")

    safe_input("\n按 Enter 繼續...")


def handle_media_analyzer(MEDIA_VIEWER_ENABLED, MediaViewer):
    """處理媒體分析器"""
    console.print("\n[#E8C4F0]🔍 媒體分析器（AI）[/#E8C4F0]\n")
    file_path = safe_input("檔案路徑（圖片/影片）：").strip()

    if not os.path.isfile(file_path):
        console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
        safe_input("\n按 Enter 繼續...")
        return

    try:
        viewer = MediaViewer()
        viewer.view_file(file_path)

        # 詢問是否進行 AI 分析
        if viewer.ai_analysis_enabled:
            analyze = safe_input("\n[#E8C4F0]進行 AI 分析？(y/N): [/#E8C4F0]").strip().lower()
            if analyze == 'y':
                custom = safe_input("[#E8C4F0]自訂分析提示（可留空使用預設）：[/#E8C4F0]\n").strip()
                viewer.analyze_with_ai(file_path, custom if custom else None)

        # 詢問是否開啟檔案
        open_file = safe_input("\n[#E8C4F0]開啟檔案？(y/N): [/#E8C4F0]").strip().lower()
        if open_file == 'y':
            os.system(f'open "{file_path}"')

    except Exception as e:
        console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    safe_input("\n按 Enter 繼續...")


def handle_ai_video_analysis_complete(
    SCENE_DETECTOR_ENABLED,
    CLIP_ADVISOR_ENABLED,
    VIDEO_SUMMARIZER_ENABLED,
    PRICING_ENABLED,
    global_pricing_calculator
):
    """處理完整 AI 影片分析（場景+剪輯+摘要）"""
    console.print("\n[#E8C4F0]🤖 完整 AI 影片分析[/#E8C4F0]\n")

    video_path = safe_input("影片路徑：").strip()
    if not os.path.isfile(video_path):
        console.print("[#E8C4F0]檔案不存在[/#E8C4F0]")
        safe_input("\n按 Enter 繼續...")
        return

    console.print("\n[#E8C4F0]分析項目：[/#E8C4F0]")
    do_scene = 'y'
    do_clip = 'y'
    do_summary = 'y'

    custom_choice = safe_input("\n執行完整分析（場景+剪輯+摘要）？(Y/n): ").strip().lower()
    if custom_choice == 'n':
        do_scene = safe_input("  場景檢測？(Y/n): ").strip().lower() or 'y'
        do_clip = safe_input("  剪輯建議？(Y/n): ").strip().lower() or 'y'
        do_summary = safe_input("  影片摘要？(Y/n): ").strip().lower() or 'y'

    try:
        if do_scene == 'y' and SCENE_DETECTOR_ENABLED:
            console.print("\n[#E8C4F0]▶ 執行場景檢測...[/#E8C4F0]")
            console.print("[dim]使用工具：gemini_scene_detector.py[/dim]")
            console.print("[dim]參數：30 幀，0.7 相似度閾值[/dim]")

        if do_clip == 'y' and CLIP_ADVISOR_ENABLED:
            console.print("\n[#E8C4F0]▶ 執行剪輯建議...[/#E8C4F0]")
            console.print("[dim]使用工具：gemini_clip_advisor.py[/dim]")

        if do_summary == 'y' and VIDEO_SUMMARIZER_ENABLED:
            console.print("\n[#E8C4F0]▶ 執行影片摘要...[/#E8C4F0]")
            console.print("[dim]使用工具：gemini_video_summarizer.py[/dim]")

        console.print("\n[#B565D8]✅ 分析完成[/#B565D8]")
        console.print("\n[dim]提示：以上工具可獨立使用，執行：")
        console.print("  python gemini_scene_detector.py <影片> --frames 30")
        console.print("  python gemini_clip_advisor.py <影片>")
        console.print("  python gemini_video_summarizer.py <影片>[/dim]")

    except Exception as e:
        console.print(f"\n[dim #E8C4F0]錯誤：{e}[/dim]")

    safe_input("\n按 Enter 繼續...")
