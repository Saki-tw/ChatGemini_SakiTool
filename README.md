# ChatGemini
**省錢 90%！輕量向量資料庫！MCP 整合！一鍵安裝的完整 Gemini AI 工具套件**

English page: 
[https://github.com/Saki-tw/ChatGemini_SakiTool/blob/main/README_EN.md](https://github.com/Saki-tw/ChatGemini_SakiTool/blob/main/README_EN.md)

README_Japan.md
[https://github.com/Saki-tw/ChatGemini_SakiTool/blob/main/README_JA.md](https://github.com/Saki-tw/ChatGemini_SakiTool/blob/main/README_JA.md)

README_Korea.md
[https://github.com/Saki-tw/ChatGemini_SakiTool/blob/main/README_KO.md](https://github.com/Saki-tw/ChatGemini_SakiTool/blob/main/README_KO.md)

---

## 💡 為什麼要用這個工具？

> **「我只是想省點 API 費用，沒想到順手做了一個完整的工具套件」**
> —— Saki-Tw (Saki@saki-studio.com.tw with Claude)

這個專案最初是我個人為了**節省 Gemini API 費用**而開發的工具。在使用過程中不斷優化，加入了自動快取、向量資料庫、智能觸發等功能，最終變成一個功能完整、好用的 AI 工具套件。

因為真的很好用，所以決定開源分享給大家！

### 🎯 核心亮點

#### 💰 自動省錢 75-90%
- **智能快取系統**：自動累積對話內容建立快取
- **Flash 模型省 90%**，Pro 模型省 75%
- 5000 tokens 快取只要 NT$0.16，後續每次查詢省 NT$0.36
- **一次查詢就回本**，完全無腦省錢

#### 🗄️ 輕量向量資料庫
- 無需安裝大型資料庫，即開即用
- 程式碼與對話記錄自動建立索引
- 超快速語意搜尋，瞬間找到相關內容
- 智能去重，避免儲存重複資料
- 支援增量更新，不用重建整個資料庫

#### 🌍 多語言介面支援 🆕
- 支援**繁體中文、English、日本語、한국어** 四種語言
- 一鍵切換介面語言，無需重啟
- 所有提示訊息、錯誤說明完整翻譯
- 自動偵測系統語言，首次啟動即為母語

#### 🔌 MCP 伺服器系統
- 智能偵測與自動載入擴充功能
- 無縫整合第三方工具與服務
- 輕鬆擴展 AI 助手能力

#### ⚡ 「一個指令、一行安裝」即刻使用API不再麻煩
```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git && cd ChatGemini_SakiTool && sh INSTALL.sh --auto
```
- 完全自動化，無需任何互動
- 自動偵測作業系統（macOS/Linux）
- 安裝完成後，**任意位置**輸入 `ChatGemini` 即可啟動

---

## 📦 專案資訊

**專案名稱**: ChatGemini_SakiTool
**版本**: v1.0.4  
**作者**: Saki-tw with Claude Code  
**聯絡**: Saki@saki-studio.com.tw  
**最後更新**: 2025-10-24

**申請 API 金鑰**：https://aistudio.google.com/app/apikey  
**每月免費額度**：Gemini 2.5 Pro 有 200 萬 tokens（約等於 1500 頁 A4 文件）

---

## 🔥 版本更新歷程

### 📅 v1.0.4（2025-10-25）— 最新版本

#### 🌍 多語言介面系統
- **四種語言支援**：完整支援繁體中文、English、日本語、한국어
- **一鍵切換**：在對話中輸入 `lang` 即可切換介面語言
- **自動偵測**：首次啟動自動偵測系統語言
- **完整翻譯**：所有提示訊息、錯誤說明、選單介面全面多語化

#### ⚡ 性能優化
- **批次處理加速**：同時處理多個請求，提升整體效能
- **智能快取預處理**：自動預載常用資料，減少等待時間
- **記憶體使用優化**：更有效率的資料管理，降低記憶體佔用

---

### 📅 v1.0.3（2025-10-24）

#### ⚙️ 系統架構優化
- **統一配置管理系統**：三層架構設計（系統預設 → 使用者配置 → 環境變數），優先權清晰明確
- **記憶體管理優化**：對話歷史自動存檔，保留最新 50 條活躍對話，舊對話自動歸檔到磁碟
- **智能路徑管理**：統一管理所有輸出路徑（對話記錄、媒體輸出等），自動建立必要目錄

#### 🛡️ 錯誤處理大幅強化
- **智能錯誤診斷**：自動分析錯誤原因，提供解決方案建議（例：缺少套件 → 顯示安裝指令）
- **預防性驗證系統**：「飛行前檢查」機制，執行前自動檢查 API 狀態、依賴工具、參數有效性
- **自動修復建議**：API 金鑰問題自動引導設定，缺少 ffmpeg 提供安裝指令

---

### 📅 v1.0.2（2025-10-24）

#### ⚙️ 系統架構優化
- **統一配置管理系統**：三層架構設計（系統預設 → 使用者配置 → 環境變數），優先權清晰明確
- **記憶體管理優化**：對話歷史自動存檔，保留最新 50 條活躍對話，舊對話自動歸檔到磁碟
- **智能路徑管理**：統一管理所有輸出路徑（對話記錄、媒體輸出等），自動建立必要目錄

#### 🛡️ 錯誤處理大幅強化
- **智能錯誤診斷**：自動分析錯誤原因，提供解決方案建議（例：缺少套件 → 顯示安裝指令）
- **預防性驗證系統**：「飛行前檢查」機制，執行前自動檢查 API 狀態、依賴工具、參數有效性
- **自動修復建議**：API 金鑰問題自動引導設定，缺少 ffmpeg 提供安裝指令

#### 🤖 CodeGemini 程式碼助手
- **向量資料庫搜尋**：快速查詢歷史對話與程式碼片段
- **多檔案編輯**：支援跨檔案的智能編輯操作
- **MCP Server 整合**：Model Context Protocol 支援

---

### 🎉 v1.0.1 — 重大功能更新

#### 💬 進階互動體驗
- **進階文字介面**：方向鍵瀏覽歷史輸入、Tab 自動補全指令與路徑、自動建議
- **動態思考模式**：即時控制 AI 思考深度（`[think:5000]` 固定預算、`[think:auto]` 自動決定、`[no-think]` 關閉思考）
- **智慧檔案附加**：自動判斷文字檔（直接讀取 30+ 格式）vs 媒體檔（上傳 API）

#### 💰 自動省錢系統
- **自動快取管理**：累積達門檻（預設 5000 tokens）自動建立快取
- **成本分析**：即時顯示節省百分比、損益平衡點
- **手動控制**：支援 `[cache:now]`（立即建立）、`[cache:off]`（暫停）、`[no-cache]`（本次不列入）

#### 🎯 使用體驗改善
- **互動式幫助系統**：內建 6 大主題選單，對話中輸入 `help` 即可查看
- **新台幣計價**：即時顯示每次對話花費（NT$），告別看不懂的美元

---

### 🌟 v1.0.0 — 核心功能（最初版本）

#### 💬 智能對話
- **串流輸出**：即時顯示 AI 回應，無需等待完整生成
- **大量文字支援**：貼上千行程式碼或長文本，無字數限制（200萬 tokens）
- **完美中文支援**：正確處理繁體中文標點符號和編碼
- **多模型支援**：Gemini 2.5 Pro、2.5 Flash、2.5 Flash-8B、2.0 Flash
- **對話記錄管理**：自動儲存對話到 JSON，支援載入歷史

#### 📷 圖像理解
- **圖像描述**：詳細描述圖片內容、場景、氛圍
- **OCR 文字提取**：提取圖片中的所有文字（多語言支援）
- **物體偵測**：識別並定位圖片中的物體
- **圖像比較**：比較多張圖片的異同
- **視覺問答**：回答關於圖片的任何問題
- **批次處理**：一次分析多張圖片
- **互動模式**：針對圖片進行多輪問答

#### 📹 影片理解
- **影片上傳分析**：上傳影片並讓 Gemini 分析內容
- **支援多種格式**：mp4, mov, avi, webm 等
- **智慧處理**：自動等待影片處理完成
- **互動式對話**：針對影片內容進行多輪問答
- **長影片支援**：Gemini 2.5 Pro 可處理最長 2 小時影片

#### 🎬 影片生成（Veo 3.1）
- **文字轉影片**：從文字描述生成 8 秒 720p/1080p 影片
- **原生音訊**：自動生成對白、音效和背景音樂
- **多種長寬比**：支援 16:9、9:16、1:1
- **參考圖片**：可使用最多 3 張圖片引導生成
- **影片延伸**：延長已生成的影片

#### 🎞️ 自然語言影片編輯（Flow Engine）
- **處理能力**：1080p 24fps
- **場景偵測**：自動識別場景切換
- **智慧裁切**：根據描述裁切片段
- **濾鏡套用**：黑白、復古、懷舊、銳化、模糊等
- **速度調整**：慢動作（0.5x）、快轉（2x）
- **浮水印添加**：自訂位置與透明度

#### 🎵 音訊處理
- **音訊提取**：從影片提取音訊
- **音訊合併**：合併多個音訊檔案
- **音量調整**：正規化、增益控制
- **淡入淡出**：平滑音訊過渡
- **背景音樂**：添加背景音樂並混音

#### 📝 字幕生成
- **語音辨識**：自動生成字幕（多語言支援）
- **多語言翻譯**：支援翻譯成多國語言
- **字幕格式**：SRT、VTT
- **字幕燒錄**：將字幕嵌入影片

#### 🖼️ 圖片生成（Imagen）
- **文字生成圖片**：從描述生成圖片
- **圖片編輯**：編輯現有圖片
- **圖片放大**：提升解析度（Super Resolution）
- **長寬比選擇**：1:1、16:9、9:16
- **批次生成**：一次生成多張

---

## ✨ 完整功能清單

### 📊 向量資料庫系統（Codebase Embedding）
- **程式碼索引**：建立程式碼向量資料庫
- **對話記錄搜尋**：搜尋歷史對話內容
- **正交去重模式**：自動去重，確保內容線性獨立
- **相似度閾值**：可調整去重敏感度（預設 0.85）
- **FAISS 高速索引**：查詢複雜度從 O(n) 降至 O(log n)
- **增量更新**：單檔更新無需重建整個索引
- **並行處理**：ThreadPoolExecutor 支援多檔案同時處理

### ⚡ 性能監控
- **CPU 監控**：追蹤 CPU 使用率
- **記憶體監控**：追蹤記憶體使用情況
- **操作計時**：記錄各操作執行時間
- **瓶頸分析**：識別性能瓶頸
- **報告匯出**：JSON 格式性能報告

### 🛡️ 錯誤處理
- **自動重試機制**：可配置重試次數、延遲、指數退避
- **詳細錯誤訊息**：Rich 格式化顯示，包含建議解決方案
- **失敗恢復功能**：檢查點機制，保存/載入/恢復失敗任務
- **錯誤記錄**：JSONL 格式日誌，錯誤統計分析
- **錯誤嚴重度分級**：LOW、MEDIUM、HIGH、CRITICAL

### 🚀 進階功能（實驗性）

**AI 剪輯建議**：自動識別精彩片段、參與度評分、編輯建議
**影片智能摘要**：多層次摘要（短/中/長）、章節標記、關鍵話題提取
**批次處理系統**：任務排程、並行處理（最多 3 個任務）、進度追蹤
**智能觸發器**：意圖檢測、功能自動觸發
**相關對話建議**：歷史搜尋、智能推薦前 3 個最相關對話
**媒體查看器**：元數據查看、AI 分析整合
**性能優化模組**：LRU 快取、並行處理、記憶體優化

---

## 📦 安裝

> **一行安裝，一個指令** - 完全自動化，無需任何互動

### 一鍵全自動安裝（推薦）

複製以下命令，貼到終端機執行：

```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git && cd ChatGemini_SakiTool && sh INSTALL.sh --auto
```

**完全自動化安裝（完整版，約 550 MB）**：
- 自動偵測作業系統（macOS/Linux）
- 自動安裝 **ChatGemini + CodeGemini**（完整版）
- 不需要任何互動或授權

安裝完成後：
1. 重新開啟終端機（或執行 `source ~/.zshrc` / `source ~/.bashrc`）
2. 在**任意位置**輸入 `ChatGemini` 即可啟動

**包含功能**：
- ✅ **ChatGemini**：對話、圖像/影片分析與生成、自動快取
- ✅ **CodeGemini**：程式碼助手、向量資料庫搜尋、MCP 整合

**安裝套件**：
- **Python 環境**：Python 3.10+、pip、ffmpeg
- **AI 套件**：google-genai、google-generativeai、python-dotenv
- **UI 套件**：rich、prompt-toolkit、Pillow、deep-translator
- **工具套件**：ffmpeg-python、numpy、psutil、requests、pyyaml
- **CodeGemini 套件**：Node.js 18+、npm、Google Cloud SDK、@google/generative-ai

---

### 互動式安裝（自訂範圍）

如需選擇安裝範圍（基礎版 vs 完整版）：

```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool
sh INSTALL.sh
```

安裝過程會引導您選擇：

**[1] 基礎版（約 500 MB）**
- ChatGemini 對話工具
- 圖像/影片分析與生成
- 自動快取系統

**[2] 完整版（約 550 MB，推薦）**
- 基礎版所有功能
- CodeGemini 程式碼助手
- 向量資料庫搜尋
- MCP Server 整合

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
- `prompt-toolkit>=3.0.0` - 進階輸入功能 (v1.0.1 新增)
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

### 對話記錄儲存位置

- 預設路徑：`~/Saki_Studio/ChatGemini/ChatLOG/`

---

## 🎯 完整使用範例

### 範例 1：程式碼分析 + 快取優化

```bash
$ ChatGemini

# 啟動時選擇快速設定
啟用自動快取？[y]: ← Enter

# 讀取多個檔案進行分析
你: 讀取 script1.py 讀取 script2.py 分析這兩個檔案的關聯性

✅ 已讀取文字檔: script1.py
✅ 已讀取文字檔: script2.py

AI: [詳細分析兩個檔案的互動...]

# 累積到 5000 tokens 後自動建立快取
🔔 已達快取門檻（5,234 tokens），自動建立快取...
✅ 快取建立成功！後續對話將自動使用快取節省成本。

# 後續問題使用快取，省 90% 成本
你: FileManager 類別的主要功能是什麼？

AI: [使用快取回應，成本大幅降低...]
💰 本次成本: NT$0.05（使用快取節省 89%）
```

### 範例 2：複雜問題深度思考

```bash
你: [think:8000] 解釋量子糾纏的物理原理，並說明在量子計算中的應用

# AI 會使用 8000 tokens 預算深入思考
AI: [展示思考過程...]
[詳細且深入的回答...]

💰 本次成本: NT$0.25（包含思考成本）
```

### 範例 3：圖片 + 程式碼分析

```bash
你: 附加 error_screenshot.png @error_log.txt 根據這張錯誤截圖和日誌檔案，幫我找出問題

✅ 已上傳媒體檔: error_screenshot.png
✅ 已讀取文字檔: error_log.txt

AI: 根據截圖和日誌，問題出在...
```

### 範例 4：臨時問題不列入快取

```bash
你: [no-cache] 順便問一下，Python 3.14 有什麼新功能？

⚠️  本次對話不列入快取

AI: Python 3.14 的新功能包括...

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

### Q: 如何自訂對話記錄存放位置？
A: 對話記錄預設存放在 `~/Saki_Studio/ChatGemini/ChatLOG/`，可在啟動時指定其他目錄。

### Q: 如何查看內建幫助？
A: 在對話中輸入 `help`，會顯示 6 大主題選單：
1. 快速入門
2. 思考模式控制
3. 檔案附加功能
4. 自動快取管理
5. 影音檔案處理
6. 指令列表

---

## 📊 專案規模

### 程式碼統計
- **總行數**：20,000+ 行 Python 程式碼
- **模組數量**：50+ 個功能模組
- **核心系統**：對話管理、快取系統、檔案處理、錯誤處理
- **多媒體功能**：圖像/影片/音訊分析與生成
- **輔助工具**：向量資料庫、性能監控、批次處理

### 架構設計
- **模組化設計**：每個功能獨立模組，易於維護與擴展
- **動態載入**：按需載入功能模組，降低啟動時間
- **配置分層**：系統預設 → 使用者配置 → 環境變數
- **錯誤恢復**：檢查點機制，失敗自動恢復
- **性能優化**：LRU 快取、並行處理、記憶體管理

### 測試覆蓋
- **單元測試**：核心功能完整測試
- **整合測試**：跨模組功能驗證
- **性能測試**：回應時間與資源使用監控
- **相容性測試**：Python 3.10-3.14、macOS/Linux

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

**最後更新**: 2025-10-24
**版本**: v1.0.2
**Python 版本**: 3.10+

---

## Related 
Ongoing research explores the fundamental cognitive limits and conceptual integrity of Large Language Models. Details and proofs can be found in the following repository: 
[LinguImplementation_Collīdunt-LLM](https://github.com/Saki-tw/LinguImplementation_Collidunt-LLM)
[https://github.com/Saki-tw/LinguImplementation_Collidunt-LLMs](GithubPage)
That time I got reincarnated as an end-user, but the LLM's safety breaks on its own?
為啥只是正常寫寫提示詞，巨型模型的安全模組就全毀？
附上一些能公開的案例，其他因為公眾安全的理由實在不知道要馬賽克到什麼程度才能放。
