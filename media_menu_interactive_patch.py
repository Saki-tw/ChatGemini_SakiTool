#!/usr/bin/env python3
"""
/media 選單互動式改進補丁

此補丁修復 gemini_chat.py 中的 /media 選單，
使其支援上下鍵導航。

修改位置：gemini_chat.py 第 3148-3197 行

使用方式：
1. 在 gemini_chat.py 第 76-77 行之後添加以下導入：
   from utils.interactive_menu import show_menu
   from utils.media_menu_builder import build_media_menu_options

2. 替換第 3148-3197 行的選單顯示與輸入邏輯：
   將原有的 console.print() 系列調用和 Prompt.ask()
   替換為 show_menu() 和 build_media_menu_options()

3. 保持後續的選項處理邏輯不變（3198-3969 行）
"""

# ========================================
# 修改前的代碼（第 3148-3197 行）
# ========================================
OLD_CODE = """
                try:
                    while True:
                        console.print("\\n" + "=" * 60)
                        console.print(safe_t('media_menu.title', fallback='[bold #B565D8]🎬 多媒體創作中心[/bold #B565D8]'))
                        console.print("=" * 60)

                        # 第一層：AI 生成（核心功能）
                        console.print(safe_t('media_menu.section.ai_generation', fallback='\\n[bold #E8C4F0]>>> AI 創作生成[/bold #E8C4F0]'))
                        # ... 省略大量 console.print() ...

                        # 使用 rich.prompt.Prompt 支援方向鍵編輯
                        media_choice = Prompt.ask(safe_t("chat.common.choose_prompt", fallback="請選擇"))
"""

# ========================================
# 修改後的代碼（新代碼）
# ========================================
NEW_CODE = """
                try:
                    while True:
                        # 建立選單選項（根據功能啟用狀態動態生成）
                        menu_options = build_media_menu_options(
                            FLOW_ENGINE_ENABLED=FLOW_ENGINE_ENABLED,
                            IMAGEN_GENERATOR_ENABLED=IMAGEN_GENERATOR_ENABLED,
                            VIDEO_PREPROCESSOR_ENABLED=VIDEO_PREPROCESSOR_ENABLED,
                            VIDEO_COMPOSITOR_ENABLED=VIDEO_COMPOSITOR_ENABLED,
                            VIDEO_EFFECTS_ENABLED=VIDEO_EFFECTS_ENABLED,
                            SUBTITLE_GENERATOR_ENABLED=SUBTITLE_GENERATOR_ENABLED,
                            AUDIO_PROCESSOR_ENABLED=AUDIO_PROCESSOR_ENABLED,
                            MEDIA_VIEWER_ENABLED=MEDIA_VIEWER_ENABLED,
                            VIDEO_ANALYZER_ENABLED=VIDEO_ANALYZER_ENABLED
                        )

                        # 顯示互動式選單（支援上下鍵導航）
                        media_choice = show_menu(
                            title='🎬 多媒體創作中心',
                            options=menu_options
                        )

                        # 處理取消操作（ESC 或取消按鈕）
                        if media_choice is None:
                            break
"""

# ========================================
# 具體修改步驟
# ========================================
MODIFICATION_STEPS = """
步驟 1: 添加導入語句
在 gemini_chat.py 第 77-78 行之間添加：

from utils.interactive_menu import show_menu  # 互動式選單（支援上下鍵）
from utils.media_menu_builder import build_media_menu_options  # 媒體選單建構器


步驟 2: 替換選單顯示代碼
找到 gemini_chat.py 第 3148-3197 行：

elif user_input.lower() in ['media', 'video', 'veo']:
    # ==========================================
    # 多媒體創作中心 - 精簡版選單
    # ==========================================
    try:
        while True:
            console.print("\\n" + "=" * 60)
            console.print(safe_t('media_menu.title', ...))
            ... (大量 console.print 語句)

            # 使用 rich.prompt.Prompt 支援方向鍵編輯
            media_choice = Prompt.ask(...)

替換為：

elif user_input.lower() in ['media', 'video', 'veo']:
    # ==========================================
    # 多媒體創作中心 - 互動式選單（支援上下鍵）
    # ==========================================
    try:
        while True:
            # 建立選單選項（根據功能啟用狀態動態生成）
            menu_options = build_media_menu_options(
                FLOW_ENGINE_ENABLED=FLOW_ENGINE_ENABLED,
                IMAGEN_GENERATOR_ENABLED=IMAGEN_GENERATOR_ENABLED,
                VIDEO_PREPROCESSOR_ENABLED=VIDEO_PREPROCESSOR_ENABLED,
                VIDEO_COMPOSITOR_ENABLED=VIDEO_COMPOSITOR_ENABLED,
                VIDEO_EFFECTS_ENABLED=VIDEO_EFFECTS_ENABLED,
                SUBTITLE_GENERATOR_ENABLED=SUBTITLE_GENERATOR_ENABLED,
                AUDIO_PROCESSOR_ENABLED=AUDIO_PROCESSOR_ENABLED,
                MEDIA_VIEWER_ENABLED=MEDIA_VIEWER_ENABLED,
                VIDEO_ANALYZER_ENABLED=VIDEO_ANALYZER_ENABLED
            )

            # 顯示互動式選單（支援上下鍵導航）
            media_choice = show_menu(
                title='🎬 多媒體創作中心',
                options=menu_options
            )

            # 處理取消操作（ESC 或取消按鈕）
            if media_choice is None:
                break


步驟 3: 保持後續處理邏輯不變
第 3198 行之後的所有 if/elif 處理邏輯保持不變：

            if media_choice == '99':
                break
            elif media_choice == '0' and MEDIA_VIEWER_ENABLED:
                # 媒體檔案查看器
                ...
            elif media_choice == '1' and FLOW_ENGINE_ENABLED:
                # Flow 引擎
                ...
            # ... 其他所有處理邏輯保持不變


步驟 4: 驗證修改
執行以下命令測試：

cd /Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool
source ../venv_py314/bin/activate
python gemini_chat.py

然後輸入 /media 或 media 測試選單：
- 按 ↑↓ 鍵應能在選項間導航
- 按 Enter 確認選擇
- 按 ESC 取消選單
- 按數字鍵應能快速選擇對應項目
"""

if __name__ == '__main__':
    print(MODIFICATION_STEPS)
