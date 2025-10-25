# 媒體檔案處理指南

**專案**: ChatGemini_SakiTool
**版本**: v1.0.3
**最後更新**: 2025-10-24

本指南說明如何使用圖片、影片、音訊等媒體檔案，包含對話整合、獨立工具使用與進階功能。

---

## 📋 目錄

1. [對話中使用媒體檔案](#對話中使用媒體檔案)
2. [圖片分析工具](#圖片分析工具)
3. [影片分析工具](#影片分析工具)
4. [影片生成工具](#影片生成工具)
5. [影片編輯功能](#影片編輯功能)
6. [音訊處理功能](#音訊處理功能)
7. [字幕生成功能](#字幕生成功能)
8. [圖片生成功能](#圖片生成功能)

---

## 對話中使用媒體檔案

### 支援格式

#### 文字檔（直接讀取，30+ 格式）
.py, .js, .ts, .jsx, .tsx, .txt, .md, .json, .yaml, .yml, .xml, .html, .css, .sh, .bash, .sql, .go, .rs, .java, .c, .cpp, .h, .rb, .php, .swift, .kt, .scala, .r, .m, .csv

#### 媒體檔（上傳 API）
- **圖片**: .jpg, .jpeg, .png, .gif, .bmp, .webp
- **影片**: .mp4, .mov, .avi, .webm, .mkv
- **文檔**: .pdf

### 使用語法

```bash
# 方式 1: @ 符號
你: @/path/to/image.jpg 這張圖片有什麼問題？
你: @screenshot.png 分析這個錯誤訊息

# 方式 2: 自然語言
你: 讀取 code.py 解釋這段程式碼
你: 附加 diagram.png 說明這個架構圖
你: 上傳 demo.mp4 分析影片內容
```

### 自動判斷邏輯

- **文字檔**: 直接讀取內容，嵌入對話
- **媒體檔**: 自動上傳至 Gemini Files API，取得檔案 URI

### 範例：混合使用

```bash
你: 讀取 error_log.txt 附加 error_screenshot.png 根據日誌和截圖找出問題

✅ 已讀取文字檔: error_log.txt (520 tokens)
✅ 已上傳媒體檔: error_screenshot.png

Gemini: 根據日誌和截圖，問題出在...
```

---

## 圖片分析工具

### 啟動方式

```bash
python3 gemini_image_analyzer.py [指令] [圖片路徑]
```

### 支援指令

#### 1. 圖片描述
```bash
python3 gemini_image_analyzer.py describe photo.jpg
```

輸出：詳細描述圖片內容、場景、氛圍、構圖。

#### 2. OCR 文字提取
```bash
python3 gemini_image_analyzer.py ocr document.png
```

輸出：圖片中的所有文字（多語言支援）。

#### 3. 物體偵測
```bash
python3 gemini_image_analyzer.py objects scene.jpg
```

輸出：圖片中的物體清單與位置。

#### 4. 圖片比較
```bash
python3 gemini_image_analyzer.py compare before.jpg after.jpg
```

輸出：兩張圖片的異同分析。

#### 5. 互動模式
```bash
python3 gemini_image_analyzer.py interactive image.jpg
```

進入互動模式，可針對圖片進行多輪問答。

### 批次處理

```bash
python3 gemini_image_analyzer.py describe img1.jpg img2.jpg img3.jpg
```

一次分析多張圖片。

---

## 影片分析工具

### 啟動方式

```bash
python3 gemini_video_analyzer.py [影片路徑] [問題]
```

### 使用範例

#### 互動模式
```bash
python3 gemini_video_analyzer.py demo.mp4
```

自動上傳影片並進入問答模式：
```
✅ 影片上傳成功: demo.mp4
⏳ 等待影片處理完成...
✅ 影片處理完成！

你的問題: 這個影片在講什麼？
Gemini: 這個影片...

你的問題: 主要角色有誰？
Gemini: 主要角色包括...
```

#### 直接提問
```bash
python3 gemini_video_analyzer.py demo.mp4 "描述這個影片的內容"
```

#### 列出已上傳的影片
```bash
python3 gemini_video_analyzer.py --list
```

### 支援格式
mp4, mov, avi, webm, mkv

### 限制
- 最長時長：2 小時（Gemini 2.5 Pro）
- 檔案大小：依 Gemini API 限制

---

## 影片生成工具

### 啟動方式

```bash
python3 gemini_veo_generator.py [描述]
```

### 使用範例

#### 互動模式（推薦）
```bash
python3 gemini_veo_generator.py
```

互動式引導：
```
請描述您想生成的影片:
> 一隻金毛獵犬在陽光下的花園玩耍

選擇長寬比:
  1. 16:9（橫式）
  2. 9:16（直式）
  3. 1:1（正方形）

選擇解析度:
  1. 720p
  2. 1080p

是否需要參考圖片？(y/n):
```

#### 命令行模式
```bash
python3 gemini_veo_generator.py "A golden retriever playing in a sunny garden"
```

### 進階功能

#### 使用參考圖片
```bash
python3 gemini_veo_generator.py --image ref1.jpg --image ref2.jpg "Generate video based on these images"
```

最多 3 張參考圖片。

#### 影片延伸
```bash
python3 gemini_veo_generator.py --extend video_id "Continue the previous scene"
```

### 輸出
生成的影片會自動下載到 `MediaOutputs/` 目錄。

### 限制
- 需要 Google AI Studio 付費專案或 Google AI Ultra 訂閱
- 生成時間：約 3-5 分鐘
- 價格：$0.75/秒（約 $6/8秒影片）

---

## 影片編輯功能

### Flow Engine（自然語言編輯）

在對話中輸入 `media` 進入影音功能選單，選擇「影片編輯」。

### 功能清單

#### 1. 場景偵測
自動識別影片中的場景切換。

#### 2. 智慧裁切
根據描述裁切特定片段：
```
裁切 10 秒到 30 秒的片段
```

#### 3. 濾鏡套用
支援濾鏡：
- 黑白
- 復古
- 懷舊
- 銳化
- 模糊

#### 4. 速度調整
```
將影片速度調整為 0.5x（慢動作）
將影片速度調整為 2x（快轉）
```

#### 5. 浮水印添加
自訂位置與透明度。

### 處理能力
- 解析度：1080p
- 幀率：24fps
- 處理速度：30 分鐘素材約需 1 小時

---

## 音訊處理功能

### 啟動方式

在對話中輸入 `media`，選擇「音訊處理」。

### 功能清單

#### 1. 音訊提取
從影片提取音訊：
```
從 video.mp4 提取音訊
```

輸出：audio.mp3 或 audio.wav

#### 2. 音訊合併
合併多個音訊檔案：
```
合併 audio1.mp3 和 audio2.mp3
```

#### 3. 音量調整
```
將音量提升 10dB
正規化音量
```

#### 4. 淡入淡出
```
添加 3 秒淡入效果
添加 5 秒淡出效果
```

#### 5. 背景音樂
```
添加背景音樂 bgm.mp3，音量 30%
```

---

## 字幕生成功能

### 啟動方式

在對話中輸入 `media`，選擇「字幕生成」。

### 功能清單

#### 1. 語音辨識
自動生成字幕：
```
為 video.mp4 生成字幕
```

支援語言：中文、英文、日文、韓文等。

#### 2. 字幕翻譯
```
將字幕翻譯成英文
```

#### 3. 字幕格式
支援格式：
- SRT
- VTT

#### 4. 字幕燒錄
將字幕嵌入影片：
```
將字幕燒錄到 video.mp4
```

輸出：帶字幕的新影片。

---

## 圖片生成功能

### 啟動方式

在對話中輸入 `media`，選擇「圖片生成（Imagen）」。

### 使用範例

```
生成一張圖片：金色的日落海灘
```

### 功能清單

#### 1. 文字生成圖片
從描述生成圖片。

#### 2. 圖片編輯
編輯現有圖片：
```
編輯 image.jpg，將背景改成藍色
```

#### 3. 圖片放大
提升解析度（Super Resolution）。

#### 4. 長寬比選擇
- 1:1（正方形）
- 16:9（橫式）
- 9:16（直式）

#### 5. 批次生成
```
生成 5 張不同的日落圖片
```

---

## 💡 最佳實踐

### 1. 對話中快速處理
簡單任務（如圖片分析、檔案讀取）直接在對話中使用：
```bash
你: 附加 screenshot.png 這個錯誤是什麼？
```

### 2. 複雜任務使用專用工具
批次處理、影片分析等使用專用工具效率更高。

### 3. 檔案路徑補全
支援 Tab 補全，輸入檔案路徑時按 Tab 自動完成。

### 4. 快取優化
讀取大量檔案後建立快取：
```bash
你: 讀取 file1.py 讀取 file2.py
你: [cache:now]
```

### 5. 媒體檔案管理
生成的媒體檔案統一存放在 `MediaOutputs/` 目錄。

---

## 🐛 常見問題

### Q: 支援哪些圖片格式？
A: jpg, jpeg, png, gif, bmp, webp

### Q: 影片上傳失敗怎麼辦？
A: 檢查檔案大小與格式，Gemini API 有檔案大小限制（通常為 2GB）。

### Q: 可以同時附加多個檔案嗎？
A: 可以，使用多次 `@` 或自然語言：
```bash
你: 讀取 file1.py 讀取 file2.py 附加 image.png
```

### Q: 文字檔和媒體檔有什麼差別？
A: 文字檔直接讀取並嵌入對話（計入輸入 tokens），媒體檔上傳至 Gemini Files API（另外計費）。

### Q: 影片生成需要多久？
A: 約 3-5 分鐘，視伺服器負載而定。

### Q: Flow Engine 支援哪些影片格式？
A: mp4, mov, avi（輸出統一為 mp4）。

---

## 🔗 相關文檔

- [功能實作清單](FEATURES_IMPLEMENTED.md)
- [自動快取指南](AUTO_CACHE_GUIDE.md)
- [API 金鑰設定](API_KEY_SETUP.md)

---

**作者**: Saki-TW (Saki@saki-studio.com.tw) with Claude
**最後更新**: 2025-10-24
**版本**: v1.0.3
