#!/usr/bin/env python3
"""
媒體選單建構器
根據功能啟用狀態動態生成選單選項
"""
from typing import List, Tuple


def build_media_menu_options(
    FLOW_ENGINE_ENABLED: bool,
    IMAGEN_GENERATOR_ENABLED: bool,
    VIDEO_PREPROCESSOR_ENABLED: bool,
    VIDEO_COMPOSITOR_ENABLED: bool,
    VIDEO_EFFECTS_ENABLED: bool,
    SUBTITLE_GENERATOR_ENABLED: bool,
    AUDIO_PROCESSOR_ENABLED: bool,
    MEDIA_VIEWER_ENABLED: bool,
    VIDEO_ANALYZER_ENABLED: bool,
) -> List[Tuple[str, str, str]]:
    """
    建立媒體選單選項列表

    Args:
        各種功能的啟用狀態標誌

    Returns:
        選項列表，格式為 [(選項ID, 顯示文字, 描述), ...]
    """
    options = []

    # ========================================
    # 第一層：AI 創作生成（核心功能）
    # ========================================
    # 分組標題（不可選擇，僅顯示）
    options.append(('header_ai', '\n>>> AI 創作生成', ''))

    if FLOW_ENGINE_ENABLED:
        options.append((
            '1',
            '[1] Flow 影片生成',
            '1080p 長影片，自然語言生成'
        ))

    options.append((
        '2',
        '[2] Veo 影片生成',
        '8秒快速生成'
    ))

    if IMAGEN_GENERATOR_ENABLED:
        options.append((
            '12',
            '[12] Imagen 圖像生成',
            'Text-to-Image'
        ))
        options.append((
            '13',
            '[13] 智能圖片創作',
            'Gemini Vision + Imagen'
        ))

    # ========================================
    # 第二層：影片處理工具
    # ========================================
    options.append(('header_video', '\n>>> 影片處理', ''))

    if VIDEO_PREPROCESSOR_ENABLED:
        options.append((
            '3',
            '[3] 影片預處理',
            '分割/關鍵幀/資訊'
        ))

    if VIDEO_COMPOSITOR_ENABLED:
        options.append((
            '4',
            '[4] 影片合併',
            '無損拼接'
        ))

    if VIDEO_EFFECTS_ENABLED:
        options.append((
            '15',
            '[15] 時間裁切',
            '無損剪輯'
        ))
        options.append((
            '16',
            '[16] 濾鏡特效',
            '7種風格'
        ))
        options.append((
            '17',
            '[17] 速度調整',
            '快轉/慢動作'
        ))
        options.append((
            '18',
            '[18] 添加浮水印',
            ''
        ))

    if SUBTITLE_GENERATOR_ENABLED:
        options.append((
            '19',
            '[19] 生成字幕',
            '語音辨識+翻譯'
        ))
        options.append((
            '20',
            '[20] 燒錄字幕',
            '嵌入影片'
        ))

    # ========================================
    # 第三層：音訊處理
    # ========================================
    if AUDIO_PROCESSOR_ENABLED:
        options.append(('header_audio', '\n>>> 音訊處理', ''))
        options.append((
            '7',
            '[7] 提取音訊',
            '從影片提取音訊'
        ))
        options.append((
            '8',
            '[8] 合併音訊',
            '替換或混合音訊'
        ))
        options.append((
            '9',
            '[9] 音量調整',
            '調整影片/音訊音量'
        ))
        options.append((
            '10',
            '[10] 背景音樂',
            '添加BGM'
        ))
        options.append((
            '11',
            '[11] 淡入淡出',
            '音訊淡入淡出效果'
        ))

    # ========================================
    # 第四層：AI 分析工具
    # ========================================
    options.append(('header_analysis', '\n>>> AI 分析工具', ''))

    if MEDIA_VIEWER_ENABLED:
        options.append((
            '0',
            '[0] 媒體分析器',
            '圖片/影片 AI 分析'
        ))

    if VIDEO_ANALYZER_ENABLED:
        options.append((
            '21',
            '[21] 影片互動對話',
            '上傳後連續提問'
        ))

    options.append((
        '5',
        '[5] 影片內容分析',
        'AI 分析影片內容'
    ))

    options.append((
        '6',
        '[6] 圖像內容分析',
        'AI 分析圖片內容'
    ))

    # ========================================
    # 返回選項
    # ========================================
    options.append(('separator', '', ''))
    options.append((
        '99',
        '[99] 返回主選單',
        ''
    ))

    return options


def filter_selectable_options(options: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    """
    過濾掉不可選擇的選項（標題、分隔符等）

    Args:
        options: 原始選項列表

    Returns:
        可選擇的選項列表
    """
    return [
        opt for opt in options
        if not opt[0].startswith('header_') and opt[0] != 'separator'
    ]


# ============================================
# 測試代碼
# ============================================
if __name__ == '__main__':
    # 測試選單建構
    options = build_media_menu_options(
        FLOW_ENGINE_ENABLED=True,
        IMAGEN_GENERATOR_ENABLED=True,
        VIDEO_PREPROCESSOR_ENABLED=True,
        VIDEO_COMPOSITOR_ENABLED=True,
        VIDEO_EFFECTS_ENABLED=True,
        SUBTITLE_GENERATOR_ENABLED=True,
        AUDIO_PROCESSOR_ENABLED=True,
        MEDIA_VIEWER_ENABLED=True,
        VIDEO_ANALYZER_ENABLED=True
    )

    print("完整選項列表：")
    for opt_id, display, desc in options:
        if opt_id.startswith('header_'):
            print(f"\n{display}")
        elif opt_id == 'separator':
            print()
        else:
            if desc:
                print(f"  {display} - {desc}")
            else:
                print(f"  {display}")

    print("\n\n可選擇的選項：")
    selectable = filter_selectable_options(options)
    for opt_id, display, desc in selectable:
        print(f"  ID: {opt_id:3s} | {display}")
