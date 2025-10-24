# API 金鑰設定指南

本指南將協助您完成 Google Gemini API 金鑰的申請與設定。

---

## 📋 前置需求

- Google 帳號
- 網路瀏覽器
- 文字編輯器（nano、vim、VS Code 等）

---

## 🔑 步驟一：申請 Gemini API 金鑰

### 1. 前往 Google AI Studio

開啟瀏覽器，前往：
```
https://aistudio.google.com/app/apikey
```

### 2. 登入 Google 帳號

使用您的 Google 帳號登入。如果尚未登入，系統會要求您登入。

### 3. 建立 API 金鑰

點擊「**Create API Key**」按鈕。

系統會顯示您的 API 金鑰，類似：
```
AIzaSyD...（長串隨機字元）
```

⚠️ **重要**：請妥善保管此金鑰，不要分享給任何人。

### 4. 複製 API 金鑰

點擊「**Copy**」按鈕，將 API 金鑰複製到剪貼簿。

---

## ⚙️ 步驟二：設定環境變數

### 方法一：使用 .env 檔案（推薦）

1. **進入專案目錄**

```bash
cd ChatGemini_SakiTool
```

2. **複製範例檔案**

```bash
cp .env.example .env
```

3. **編輯 .env 檔案**

```bash
nano .env
```

或使用您喜歡的編輯器：
```bash
vim .env
code .env  # VS Code
```

4. **填入 API 金鑰**

將檔案內容修改為：
```bash
# Google Gemini API 金鑰
GEMINI_API_KEY=AIzaSyD...（貼上您的 API 金鑰）

# 可選：Google Cloud Translation API（用於翻譯功能）
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

5. **儲存並關閉**

- nano: `Ctrl + X`，然後按 `Y`，再按 `Enter`
- vim: 按 `Esc`，輸入 `:wq`，按 `Enter`

### 方法二：設定系統環境變數

#### macOS / Linux

編輯 shell 配置檔：

**Zsh** (macOS 預設):
```bash
nano ~/.zshrc
```

**Bash**:
```bash
nano ~/.bashrc
```

加入以下內容：
```bash
export GEMINI_API_KEY="AIzaSyD...（您的 API 金鑰）"
```

重新載入配置：
```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

---

## ✅ 步驟三：驗證設定

### 測試 API 連線

執行對話工具：
```bash
python3 gemini_chat.py
```

如果設定正確，您會看到：
```
✅ 已載入統一配置管理器（三層架構）
✅ 檢查點系統已啟用
```

如果出現錯誤：
```
❌ 未找到 GEMINI_API_KEY 環境變數
```

請重新檢查步驟二的設定。

---

## 💡 常見問題

### Q1: API 金鑰放在哪裡最安全？

**推薦**: 使用 `.env` 檔案（方法一）

優點：
- 不會被 git 追蹤（已加入 .gitignore）
- 容易管理和更新
- 專案獨立，不影響系統環境

### Q2: 可以在程式碼中直接寫入 API 金鑰嗎？

**絕對不要這麼做！**

原因：
- ❌ 容易不小心上傳到 GitHub
- ❌ 任何看到程式碼的人都能取得金鑰
- ❌ 金鑰洩漏後需要重新申請

### Q3: 忘記備份 API 金鑰怎麼辦？

前往 Google AI Studio，刪除舊金鑰並建立新的：
```
https://aistudio.google.com/app/apikey
```

### Q4: API 金鑰有使用期限嗎？

Gemini API 金鑰目前**沒有到期日**，除非您主動刪除。

### Q5: 如何檢查 API 用量？

前往 Google AI Studio 查看：
```
https://aistudio.google.com/app/quota
```

可查看：
- 每日請求次數
- 每分鐘請求上限
- Token 用量統計

---

## 🎯 進階設定

### 多專案管理

如果您有多個專案需要不同的 API 金鑰：

1. **每個專案使用獨立 .env 檔案**

```bash
project-a/
  └── .env  # API 金鑰 A

project-b/
  └── .env  # API 金鑰 B
```

2. **使用環境變數切換**

```bash
# 切換到專案 A
export GEMINI_API_KEY="API_KEY_A"
cd project-a && python3 gemini_chat.py

# 切換到專案 B
export GEMINI_API_KEY="API_KEY_B"
cd project-b && python3 gemini_chat.py
```

### Google Cloud Translation API（可選）

如需使用翻譯功能，額外需要：

1. **啟用 Cloud Translation API**
   - 前往 [Google Cloud Console](https://console.cloud.google.com/)
   - 建立專案或選擇現有專案
   - 啟用 Cloud Translation API

2. **建立服務帳號金鑰**
   - 在 IAM & Admin → Service Accounts 建立服務帳號
   - 下載 JSON 金鑰檔案

3. **設定環境變數**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```

---

## 🔒 安全最佳實踐

1. **不要將 API 金鑰上傳到 GitHub**
   - 確認 `.env` 已在 `.gitignore` 中
   - 使用 `git status` 檢查

2. **定期更換 API 金鑰**
   - 建議每 3-6 個月更換一次
   - 或在金鑰可能外洩時立即更換

3. **限制 API 金鑰權限**
   - 在 Google AI Studio 設定 API 金鑰的使用限制
   - 設定 IP 白名單（如需要）

4. **監控 API 用量**
   - 定期檢查用量是否異常
   - 設定用量警告

---

## 🆘 疑難排解

### 問題：出現 "API key not valid" 錯誤

**可能原因**：
1. API 金鑰複製不完整
2. API 金鑰包含多餘的空格或換行
3. API 金鑰已被刪除或撤銷

**解決方法**：
1. 重新複製 API 金鑰，確保完整無誤
2. 檢查 `.env` 檔案中的金鑰前後沒有空格
3. 前往 Google AI Studio 確認金鑰仍有效

### 問題：程式找不到 .env 檔案

**檢查項目**：
```bash
# 確認 .env 檔案存在
ls -la .env

# 確認檔案權限
chmod 600 .env

# 確認檔案內容
cat .env
```

### 問題：環境變數設定後仍無效

**嘗試**：
```bash
# 重新開啟終端機
exit
# 然後重新開啟

# 或重新載入 shell 配置
source ~/.zshrc  # 或 ~/.bashrc
```

---

## 📚 相關資源

- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API 官方文檔](https://ai.google.dev/)
- [API 配額說明](https://ai.google.dev/pricing)

---

**作者**: Saki-TW (Saki@saki-studio.com.tw) with Claude
**最後更新**: 2025-10-24
**版本**: v1.0.2
