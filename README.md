# ChatGemini_SakiTool  
完整 Gemini AI 工具套件
English page:
https://github.com/Saki-tw/ChatGemini_SakiTool/blob/main/README_EN.md  

**ChatGemini_SakiTool:** Robust Gemini toolkit for text, image & *video* (Veo 3.1 gen, Flow Engine editing). Smart caching saves 50-95% tokens. Started as a personal script.

「一行安裝、一個指令」使用API不再麻煩
One-line install, one-command run. hassle-free API.


這是一個功能強大的 Google Gemini AI 工具套件，  
包含對話、圖片分析、影片分析、影片生成、快取管理等完整功能。  
需申請 Gemini API 才能用，  
每個月以 2.5 Pro 而言有兩百萬 Token 的免費額，  
快來白嫖  

**專案名稱**: ChatGemini_SakiTool  
**版本**: v1.0.1  
**作者**: Saki-tw, Claude Code  
**聯絡**: Saki@saki-studio.com.tw  
**最後更新**: 2025-10-22

---

---

## ✨ 主要特性

### 💬 對話功能（gemini_chat.py）

#### 🆕 v1.0.1 新增功能
- **✨ 進階文字介面**: 整合 prompt-toolkit，支援方向鍵瀏覽歷史、Tab 自動補全、自動建議
- **🧠 動態思考模式**: 即時控制 AI 思考深度 `[think:5000]` `[no-think]` `[think:auto]`
- **📎 智慧檔案附加**: 自動判斷文字檔（直接讀取）vs 媒體檔（上傳 API）
- **💾 自動快取管理**: 節省 75-90% API 成本，智慧觸發與成本分析
- **📖 互動式幫助系統**: 內建 6 大主題選單，無需查閱外部文檔

#### 核心功能
- **串流輸出 (Streaming Output)**: 即時顯示 AI 回應，無需等待完整生成
- **支援大量文字**: 可以貼上千行程式碼或長文本，無字數限制（200萬 tokens）
- **完美的中文支援**: 正確處理中文標點符號和編碼
- **多模型支援**: Gemini 2.5 Pro、2.5 Flash、2.5 Flash-8B、2.0 Flash
- **對話記錄管理**: 自動儲存對話到 JSON 檔案，支援載入歷史
- **新台幣計價**: 即時顯示每次對話花費

### 📷 圖像理解（gemini_image_analyzer.py）
- **圖像描述**: 詳細描述圖片內容、場景、氛圍
- **OCR 文字提取**: 提取圖片中的所有文字（多語言）
- **物體偵測**: 識別並定位圖片中的物體
- **圖像比較**: 比較多張圖片的異同
- **視覺問答**: 回答關於圖片的任何問題
- **批次處理**: 一次分析多張圖片
- **互動模式**: 針對圖片進行多輪問答

### 📹 影片理解（gemini_video_analyzer.py）
- **影片上傳分析**: 上傳影片並讓 Gemini 分析內容
- **支援多種格式**: mp4, mov, avi, webm 等
- **智慧處理**: 自動等待影片處理完成
- **互動式對話**: 針對影片內容進行多輪問答
- **長影片支援**: Gemini 2.5 Pro 可處理最長 2 小時影片

### 🎬 影片生成（gemini_veo_generator.py）
- **Veo 3.1 支援**: 使用最新的 Veo 3.1 生成高品質影片
- **文字轉影片**: 從文字描述生成 8 秒 720p/1080p 影片
- **原生音訊**: 自動生成對白、音效和背景音
- **多種長寬比**: 支援 16:9、9:16、1:1
- **參考圖片**: 可使用最多 3 張圖片引導生成
- **影片延伸**: 延長已生成的影片

### 🎞️ 自然語言影片編輯（Flow Engine）
- **處理能力**: 1080p 24fps
- **處理速度**: 30 分鐘內容約需 1 小時
- **場景偵測**: 自動識別場景切換
- **智慧裁切**: 根據描述裁切片段
- **濾鏡套用**: 黑白、復古、懷舊、銳化、模糊等
- **速度調整**: 慢動作、快轉
- **浮水印添加**: 自訂位置與透明度

### 🎵 音訊處理
- **音訊提取**: 從影片提取音訊
- **音訊合併**: 合併多個音訊檔案
- **音量調整**: 正規化、增益控制
- **淡入淡出**: 平滑音訊過渡
- **背景音樂**: 添加背景音樂並混音

### 📝 字幕生成
- **語音辨識**: 自動生成字幕
- **多語言翻譯**: 支援多國語言翻譯
- **字幕格式**: SRT、VTT
- **字幕燒錄**: 將字幕嵌入影片

### 🖼️ 圖片生成（Imagen）
- **文字生成圖片**: 從描述生成圖片
- **圖片編輯**: 編輯現有圖片
- **圖片放大**: 提升解析度
- **長寬比選擇**: 1:1、16:9、9:16
- **批次生成**: 一次生成多張

### 📊 Codebase Embedding（正交向量資料庫）
- **程式碼索引**: 建立程式碼向量資料庫
- **對話記錄搜尋**: 搜尋歷史對話內容
- **正交模式**: 自動去重，確保內容線性獨立
- **相似度閾值**: 可調整去重敏感度（預設 0.85）
- **輕量實作**: SQLite + NumPy，無需 ChromaDB
- **提示詞節費**: 累積對話內容建立快取，節省 50~95% 費用

### ⚡ 性能監控
- **CPU 監控**: 追蹤 CPU 使用率
- **記憶體監控**: 追蹤記憶體使用情況
- **操作計時**: 記錄各操作執行時間
- **瓶頸分析**: 識別性能瓶頸
- **報告匯出**: JSON 格式性能報告

### 🛡️ 錯誤處理強化
- **自動重試機制**: 可配置重試次數、延遲、指數退避
- **詳細錯誤訊息**: Rich 格式化顯示，包含建議解決方案
- **失敗恢復功能**: 檢查點機制，保存/載入/恢復失敗任務
- **錯誤記錄**: JSONL 格式日誌，錯誤統計分析
- **錯誤嚴重度分級**: LOW、MEDIUM、HIGH、CRITICAL

### 🚀 進階功能（實驗性）

#### AI 剪輯建議
- **智能片段推薦**: 自動識別精彩片段
- **參與度評分**: 評估片段吸引力（0-10）
- **編輯建議**: 提供具體剪輯技巧
- **場景檢測整合**: 結合場景分析

#### 影片智能摘要
- **多層次摘要**: 短/中/長三種摘要格式
- **章節標記**: 自動生成章節與時間戳
- **關鍵話題提取**: 識別影片主要內容
- **元數據生成**: 標籤、分類、語言檢測

#### 批次處理系統
- **任務排程**: 支援優先級與排程
- **並行處理**: 最多 3 個任務同時執行
- **進度追蹤**: 即時顯示處理狀態
- **失敗重試**: 自動重試失敗任務

#### 智能觸發器
- **意圖檢測**: 自動識別使用者需求
- **功能自動觸發**: 無需手動選擇
- **CodeGemini 整合**: 無痕整合 CodeGemini 功能

#### 相關對話建議
- **歷史搜尋**: 搜尋相似歷史對話
- **智能推薦**: 顯示前 3 個最相關對話
- **向量資料庫**: 基於 Codebase Embedding

#### 媒體查看器
- **檔案資訊**: 圖片/影片元數據查看
- **AI 分析**: 整合 Gemini 進行內容分析
- **格式支援**: 圖片、影片、音訊

#### 性能優化模組
- **LRU 快取**: 最近最少使用快取機制
- **並行處理**: ThreadPoolExecutor / ProcessPoolExecutor
- **記憶體優化**: 智能資源管理

---

## 📦 安裝

> **一行安裝，一個指令** - 完全自動化，無需任何互動

### 一鍵全自動安裝（推薦）

複製以下命令，貼到終端機執行：

```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git && cd ChatGemini_SakiTool && sh INSTALL.sh --auto
```

**完全自動化安裝**：
- 自動偵測作業系統（macOS/Linux）
- 自動安裝基礎版（約 500MB）
- 不需要任何互動或授權

安裝完成後：
1. 重新開啟終端機（或執行 `source ~/.zshrc` / `source ~/.bashrc`）
2. 在**任意位置**輸入 `ChatGemini` 即可啟動

**自動安裝內容**：
- Python 3.10+、pip、ffmpeg
- google-genai、google-generativeai、python-dotenv
- rich、prompt-toolkit、Pillow、deep-translator
- google-cloud-translate、ffmpeg-python、numpy
- psutil、requests、pyyaml、html2text
- beautifulsoup4、cachetools

---

### 互動式安裝（進階用戶）

如需自訂安裝範圍（完整版包含 Node.js、Google Cloud SDK）：

```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool
sh INSTALL.sh
```

安裝過程會引導您選擇安裝範圍（基礎版 500MB / 完整版 550MB）

### 方法二：手動安裝

#### 前置需求
- Python 3.10 或更高版本（建議 3.14）
- pip 套件管理器
- Google Gemini API 金鑰

#### 步驟

1. **克隆專案**
```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool
```

2. **創建虛擬環境**
```bash
python3 -m venv venv_py314
source venv_py314/bin/activate  # macOS/Linux
# 或
venv_py314\Scripts\activate  # Windows
```

3. **安裝依賴套件**
```bash
pip install -r requirements.txt
```

**依賴套件清單**：
- `google-generativeai>=0.3.0` - Gemini API
- `google-genai>=1.45.0` - 新版 SDK
- `python-dotenv>=1.0.0` - 環境變數管理
- `rich>=13.0.0` - 終端美化輸出
- `prompt-toolkit>=3.0.0` - 進階輸入功能 (v2.1 新增)
- `Pillow>=10.0.0` - 圖片處理

4. **設定 API 金鑰**

從範例檔案創建 `.env` 檔案：
```bash
cp .env.example .env
nano .env  # 或使用你喜歡的編輯器
```

**詳細的 API Key 設定說明**，請參閱 [API_KEY_SETUP.md](API_KEY_SETUP.md)

---

## 🚀 使用方式

### 1️⃣ 對話工具（gemini_chat.py）

#### 快速啟動

使用 Shell 別名（安裝後）：
```bash
ChatGemini  # 對話記錄存到 ~/SakiStudio/ChatGemini/ChatLOG
```

或直接執行（手動安裝）：
```bash
python3 gemini_chat.py
```

#### 互動模式指令

| 指令 | 說明 |
|------|------|
| `exit` / `quit` | 退出程式並儲存對話記錄 |
| `clear` | 清除對話歷史，開始新對話 |
| `model` | 切換使用的模型 |
| `cache` | 快取管理（節省 50-95% 成本）|
| `media` | 影音功能選單（20+ 功能）|
| `debug` / `test` | 除錯與測試工具 |
| `help` | 互動式幫助系統 |

#### 🆕 v1.0.1 新語法

**思考模式控制**：
```bash
你: [think:5000] 深入分析量子計算原理
你: [no-think] 簡單解釋什麼是遞迴
你: [think:auto] 這是複雜問題，讓 AI 自己決定
```

**檔案附加**：
```bash
你: @/path/to/code.py 分析這段程式碼
你: 讀取 requirements.txt 解釋依賴關係
你: 附加 screenshot.png 這張圖有什麼問題？
你: 上傳 demo.mp4 分析這個影片
```

**快取控制**：
```bash
你: [cache:now] 立即建立快取
你: [cache:off] 暫停自動快取
你: [cache:on] 恢復自動快取
你: [no-cache] 這個問題不要列入快取
```

#### 啟動時配置

第一次執行會詢問自動快取設定：
```
啟用自動快取？
  [y] 是（推薦，5000 tokens 自動建立）
  [c] 自訂設定
  [n] 否

你的選擇 [y]: ← 直接按 Enter 使用推薦設定
```

---

### 2️⃣ 圖像分析工具（gemini_image_analyzer.py）

#### 分析圖片
```bash
# 描述圖片
python3 gemini_image_analyzer.py describe photo.jpg

# OCR 文字提取
python3 gemini_image_analyzer.py ocr document.png

# 物體偵測
python3 gemini_image_analyzer.py objects scene.jpg

# 比較圖片
python3 gemini_image_analyzer.py compare before.jpg after.jpg

# 互動模式
python3 gemini_image_analyzer.py interactive image.jpg
```

---

### 3️⃣ 影片分析工具（gemini_video_analyzer.py）

```bash
# 互動模式
python gemini_video_analyzer.py video.mp4

# 直接提問
python gemini_video_analyzer.py video.mp4 "描述這個影片的內容"

# 列出已上傳的影片
python gemini_video_analyzer.py --list
```

---

### 4️⃣ 影片生成工具（gemini_veo_generator.py）

```bash
# 互動模式（推薦）
python gemini_veo_generator.py

# 命令行模式
python gemini_veo_generator.py "A golden retriever playing in a sunny garden"
```

---

## 🤖 支援的模型

### 推薦模型（互動模式選單）

1. **Gemini 2.5 Pro** - 最強大（思考模式）
2. **Gemini 2.5 Flash** - 快速且智慧（推薦）
3. **Gemini 2.5 Flash-8B** - 最便宜
4. **Gemini 2.0 Flash** - 快速版

您也可以：
- 在互動模式中輸入 `model` 切換模型
- 自訂輸入任何 Gemini 模型名稱

---

## 📁 檔案結構

```
ChatGemini_SakiTool/
├── gemini_chat.py                  # 主對話工具
├── gemini_image_analyzer.py        # 圖像分析
├── gemini_video_analyzer.py        # 影片分析
├── gemini_veo_generator.py         # 影片生成（Veo 3.1）
├── gemini_flow_engine.py           # 自然語言影片編輯
├── gemini_audio_processor.py       # 音訊處理
├── gemini_subtitle_generator.py    # 字幕生成
├── gemini_imagen_generator.py      # 圖片生成（Imagen）
├── gemini_video_effects.py         # 影片特效
├── gemini_video_preprocessor.py    # 影片預處理
├── gemini_video_compositor.py      # 影片合成
├── gemini_scene_detector.py        # 場景偵測
├── gemini_file_manager.py          # 檔案管理
├── gemini_pricing.py               # 定價計算
├── gemini_translator.py            # 翻譯功能
├── gemini_error_handler.py         # 錯誤處理
├── gemini_cache_manager.py         # 快取管理
├── gemini_validator.py             # 驗證系統
├── error_fix_suggestions.py        # 錯誤修復建議
├── config.py                       # 配置管理
├── CodeGemini.py                   # Codebase Embedding 主程式
│
├── 進階功能（實驗性）/
│   ├── gemini_clip_advisor.py     # AI 剪輯建議
│   ├── gemini_video_summarizer.py # 影片智能摘要
│   ├── gemini_batch_processor.py  # 批次處理系統
│   ├── gemini_smart_triggers.py   # 智能觸發器
│   ├── gemini_conversation_suggestion.py  # 相關對話建議
│   ├── gemini_media_viewer.py     # 媒體查看器
│   ├── gemini_performance.py      # 性能優化
│   ├── api_retry_wrapper.py       # API 重試機制
│   ├── error_diagnostics.py       # 智能錯誤診斷
│   └── simplified_media_menu.py   # 精簡版選單
│
├── CodeGemini/                     # CodeGemini 子模組
│   ├── codebase_embedding.py      # 正交向量資料庫
│   ├── commands/                  # 指令系統
│   ├── context/                   # 上下文建構
│   ├── core/                      # 核心功能
│   ├── generators/                # 文檔/測試生成
│   ├── mcp/                       # MCP 整合
│   ├── modes/                     # 互動模式
│   ├── tools/                     # Web Fetch/Search
│   ├── tests/                     # 測試套件
│   └── requirements.txt           # CodeGemini 依賴
│
├── utils/                          # 工具模組
│   ├── performance_monitor.py     # 性能監控
│   └── thinking_helpers.py        # 思考模式輔助
│
├── requirements.txt                # Python 依賴套件
├── INSTALL.sh                      # 一鍵安裝腳本
├── .env.example                    # 環境變數範例
├── README.md                       # 本文檔
└── venv_py314/                     # Python 虛擬環境
```

---

## 💾 對話記錄

### 自動儲存

對話記錄會自動儲存到指定目錄，檔案格式：

```json
{
  "session_start": "2025-10-20T10:30:00",
  "session_end": "2025-10-20T11:00:00",
  "model": "gemini-2.5-flash",
  "conversations": [
    {
      "timestamp": "2025-10-20T10:31:00",
      "prompt": "什麼是機器學習？",
      "response": "機器學習是人工智慧的一個分支...",
      "cost_twd": 0.05
    }
  ]
}
```

### 兩種輸出模式

- **Gemini**（大寫）: 存到 `~/Saki_Studio/gemini_conversations/`
- **gemini**（小寫）: 存到 `~/Saki_Studio/Claude/gemini_conversations/`

---

## 🎯 v2.1 完整使用範例

### 範例 1：程式碼分析 + 快取優化

```bash
$ Gemini

# 啟動時選擇快速設定
啟用自動快取？[y]: ← Enter

# 讀取多個檔案進行分析
你: 讀取 gemini_chat.py 讀取 gemini_file_manager.py 分析這兩個檔案的關聯性

✅ 已讀取文字檔: gemini_chat.py
✅ 已讀取文字檔: gemini_file_manager.py

Gemini: [詳細分析兩個檔案的互動...]

# 累積到 5000 tokens 後自動建立快取
🔔 已達快取門檻（5,234 tokens），自動建立快取...
✅ 快取建立成功！後續對話將自動使用快取節省成本。

# 後續問題使用快取，省 90% 成本
你: FileManager 類別的主要功能是什麼？

Gemini: [使用快取回應，成本大幅降低...]
💰 本次成本: NT$0.05（使用快取節省 89%）
```

### 範例 2：複雜問題深度思考

```bash
你: [think:8000] 解釋量子糾纏的物理原理，並說明在量子計算中的應用

# AI 會使用 8000 tokens 預算深入思考
Gemini: [展示思考過程...]
[詳細且深入的回答...]

💰 本次成本: NT$0.25（包含思考成本）
```

### 範例 3：圖片 + 程式碼分析

```bash
你: 附加 error_screenshot.png @error_log.txt 根據這張錯誤截圖和日誌檔案，幫我找出問題

✅ 已上傳媒體檔: error_screenshot.png
✅ 已讀取文字檔: error_log.txt

Gemini: 根據截圖和日誌，問題出在...
```

### 範例 4：臨時問題不列入快取

```bash
你: [no-cache] 順便問一下，Python 3.14 有什麼新功能？

⚠️  本次對話不列入快取

Gemini: Python 3.14 的新功能包括...

# 這個回應不會加入快取內容，節省快取空間
```

---

## 💰 定價資訊

### Gemini API（對話 & 影片理解）

**Gemini 2.5 Flash**（推薦）:
- 輸入: $0.000001 / token (NT$ 0.000031)
- 輸出: $0.000004 / token (NT$ 0.000124)
- 快取: 90% 折扣（輸入 $0.0000001 / token）

**Gemini 2.5 Pro**（思考模式）:
- 輸入: $0.00315 / 1K tokens
- 輸出: $0.0126 / 1K tokens
- 思考 tokens: 與輸入同價

### 快取成本範例

假設累積 5000 tokens：

```
快取建立成本（一次性）: NT$ 0.16

後續每次查詢節省（假設 5000 tokens 輸入）:
  不使用快取: NT$ 0.40
  使用快取:   NT$ 0.04
  每次節省:   NT$ 0.36（省 90%）

損益平衡: 1 次查詢後開始真正省錢
```

### Veo 3.1（影片生成）
- **定價**: $0.75 per second（約 $6 / 8秒影片）
- **需求**: Google AI Studio 付費專案或 Google AI Ultra 訂閱

---

## 🐛 常見問題

### Q: 出現 "未找到 GEMINI_API_KEY 環境變數" 錯誤
A: 請確認您已建立 `.env` 檔案並正確設定 API 金鑰。參考 [API_KEY_SETUP.md](API_KEY_SETUP.md)

### Q: 方向鍵、Tab 不能用？
A: 確認已安裝 `prompt-toolkit`：
```bash
pip install prompt-toolkit>=3.0.0
```

### Q: 快取建立失敗，顯示 tokens 不足
A: 不同模型有最低 tokens 要求：
- gemini-2.5-flash: 最低 1024 tokens
- gemini-2.5-pro: 最低 4096 tokens

繼續對話累積更多內容即可。

### Q: 如何關閉自動快取？
A: 啟動時選 `[n]`，或對話中輸入 `[cache:off]`

### Q: 檔案附加支援哪些格式？
A:
- **文字檔**（直接讀取）: .py, .js, .txt, .md, .json, .xml, .yaml 等 30+ 格式
- **媒體檔**（上傳 API）: .jpg, .png, .mp4, .pdf 等

### Q: Gemini 和 gemini 有什麼差別？
A: 只是對話記錄存放位置不同：
- `Gemini`（大寫）: `~/Saki_Studio/gemini_conversations/`
- `gemini`（小寫）: `~/Saki_Studio/Claude/gemini_conversations/`

### Q: 如何查看內建幫助？
A: 在對話中輸入 `help`，會顯示 6 大主題選單：
1. 快速入門
2. 思考模式控制
3. 檔案附加功能
4. 自動快取管理
5. 影音檔案處理
6. 指令列表

---

## 📝 v2.1 改進摘要

相比 v2.0，此版本實現了以下重大改進：

### ✨ 新功能
- ✅ **進階文字介面** - prompt-toolkit 整合（方向鍵、Tab、歷史）
- ✅ **動態思考模式** - 即時控制 AI 思考深度
- ✅ **智慧檔案附加** - 自動判斷文字檔 vs 媒體檔
- ✅ **自動快取管理** - 節省 75-90% API 成本
- ✅ **互動式 Help** - 內建 6 主題幫助系統
- ✅ **即時成本顯示** - 新台幣計價，每次對話顯示花費

### 🔧 技術改進
- ✅ **Python 3.14 支援** - 使用最新 Python 版本
- ✅ **虛擬環境管理** - 智慧偵測多版本環境
- ✅ **Shell 別名配置** - 全局命令快速啟動
- ✅ **向後相容性** - prompt-toolkit 可選，未安裝時降級

### 📚 文檔完善
- ✅ **FEATURES_IMPLEMENTED.md** - 功能實作清單
- ✅ **AUTO_CACHE_GUIDE.md** - 自動快取完整指南
- ✅ **MEDIA_FILES_GUIDE.md** - 媒體檔案處理說明
- ✅ **MAINTENANCE_REPORT.md** - 維護測試報告

---

## 🔗 相關文檔

- [功能實作清單](FEATURES_IMPLEMENTED.md) - 詳細技術實作
- [自動快取指南](AUTO_CACHE_GUIDE.md) - 完整使用教學
- [媒體檔案指南](MEDIA_FILES_GUIDE.md) - 圖片/影片處理
- [API 金鑰設定](API_KEY_SETUP.md) - 設定步驟
- [維護報告](MAINTENANCE_REPORT.md) - 最新測試結果

---

## 📄 授權

本專案採用 **MIT License** 授權。

詳細授權條款請參閱 [LICENSE](LICENSE) 檔案。

簡單來說，你可以自由地：
- ✅ 使用此專案
- ✅ 修改此專案
- ✅ 分發此專案
- ✅ 用於商業用途

唯一要求是保留原始授權聲明和版權聲明。

唯二致謝：曾公益中、蔡師傅律安。

---

**享受與 Gemini AI 的對話！** 🎉

**最後更新**: 2025-10-22
**版本**: v1.0.1
**Python 版本**: 3.10+

---

## Related 
Ongoing research explores the fundamental cognitive limits and conceptual integrity of Large Language Models. Details and proofs can be found in the following repository: 
[LinguImplementation_Collīdunt-LLM](https://github.com/Saki-tw/LinguImplementation_Collidunt-LLM)
[https://github.com/Saki-tw/LinguImplementation_Collidunt-LLMs](GithubPage)
That time I got reincarnated as an end-user, but the LLM's safety breaks on its own?
為啥只是正常寫寫提示詞，巨型模型的安全模組就全毀？
附上一些能公開的案例，其他因為公眾安全的理由實在不知道要馬賽克到什麼程度才能放。
