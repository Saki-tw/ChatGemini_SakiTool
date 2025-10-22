# CodeGemini

**版本:** 1.1.0
**建立日期:** 2025-10-21
**維護者:** Saki-tw (with Claude Code)

Google Gemini CLI 的配置與管理工具，提供自動化安裝腳本、環境設定、背景 Shell 管理、任務追蹤與互動式問答。

---

## 📋 目錄

- [專案簡介](#專案簡介)
- [功能特色](#功能特色)
- [系統需求](#系統需求)
- [快速開始](#快速開始)
- [環境配置](#環境配置)
- [使用指南](#使用指南)
- [版本檢查](#版本檢查)
- [故障排除](#故障排除)
- [相關資源](#相關資源)

---

## 專案簡介

CodeGemini 是基於 [Google Gemini CLI](https://github.com/google-gemini/gemini-cli) 的配置管理專案，提供：

- **自動化安裝腳本** - 一鍵配置 Gemini CLI 環境
- **環境變數管理** - 簡化 API Key 設定
- **版本檢查工具** - 確認已安裝的 Gemini CLI 版本
- **使用說明文件** - 完整的設定與使用指南

### 什麼是 Gemini CLI？

Gemini CLI 是 Google 官方開源的 AI 代理工具，具備：

- **1M Token 上下文窗口** - 使用 Gemini 2.5 Pro 模型
- **內建工具** - Google 搜尋、檔案操作、Shell 命令、網頁抓取
- **MCP 支援** - Model Context Protocol 整合
- **Context Files** - 透過 GEMINI.md 提供持久化上下文
- **Checkpointing** - 儲存並恢復對話
- **Token Caching** - 優化 token 使用

---

## 功能特色

### 🚀 自動化安裝

- ✅ 自動檢查 Node.js 版本（需要 v18+）
- ✅ 一鍵安裝 `@google/gemini-cli`
- ✅ 環境變數配置引導
- ✅ 安裝驗證與版本檢查

### 🔧 環境管理

- ✅ `.env` 檔案模板
- ✅ Shell 配置建議
- ✅ 多種認證方式支援（OAuth, API Key, Vertex AI）

### 🎯 新增功能（v1.1.0）

#### 背景 Shell 管理（Background Shells）
- ✅ 啟動背景執行的 Shell 命令
- ✅ 實時監控輸出（支援正則過濾）
- ✅ 管理多個背景任務
- ✅ 優雅終止與強制終止

參考 Claude Code 的 Bash、BashOutput、KillShell 工具。

#### 任務追蹤系統（Todo Tracking）
- ✅ 追蹤任務狀態（pending/in_progress/completed）
- ✅ 顯示任務進度
- ✅ 支援 activeForm（進行中形式）
- ✅ 清除已完成任務

參考 Claude Code 的 TodoWrite 工具。

#### 互動式問答（Interactive Q&A）
- ✅ 單選與多選問答
- ✅ 選項說明與描述
- ✅ 自訂輸入支援
- ✅ 確認對話框

參考 Claude Code 的 AskUserQuestion 工具。

#### 💰 API 定價顯示（API Pricing Display）
- ✅ 預估 API 調用成本
- ✅ 顯示台幣與美元定價
- ✅ 完整 Gemini API 定價表
- ✅ API 使用說明與成本控制建議

**重要說明：**
- Background Shells、Todo Tracking、Interactive Q&A **本身不調用 API**
- 這些是純本地工具，不會產生費用
- 但如果被整合到 Agent Mode，Agent 本身會調用 API
- 可使用 PricingDisplay 顯示成本預估

**CLI 指令：**
```bash
# 顯示完整定價表（台幣 + 美元）
python3 CodeGemini.py pricing

# 顯示 API 使用說明
python3 CodeGemini.py pricing-note
```

**定價範例（2025年1月）：**
- Gemini 2.5 Flash: $0.15625/1M tokens (input) ≈ NT$4.84/1M tokens
- Gemini 2.5 Pro: $1.25/1M tokens (input ≤200K) ≈ NT$38.75/1M tokens
- Gemini 2.0 Flash Exp: $0.10/1M tokens (input) ≈ NT$3.10/1M tokens

### 📚 完整文檔

- ✅ 詳細的安裝步驟
- ✅ 使用範例
- ✅ 故障排除指南
- ✅ API 參考文檔

---

## 系統需求

### 必要條件

| 項目 | 最低版本 | 建議版本 | 檢查指令 |
|------|---------|---------|---------|
| **作業系統** | macOS / Linux | - | `uname -s` |
| **Node.js** | v18.0.0+ | v20.0.0+ | `node -v` |
| **npm** | v9.0.0+ | v10.0.0+ | `npm -v` |

### 選用條件

- **Google 帳號** - 用於 OAuth 登入
- **Gemini API Key** - 從 [Google AI Studio](https://aistudio.google.com/apikey) 取得
- **網路連線** - 安裝套件與 API 呼叫

---

## 快速開始

### 方法 1: 使用自動化安裝腳本（推薦）

```bash
# 1. 進入專案目錄
cd ~/Saki_Studio/Claude/ChatGemini_SakiTool/CodeGemini

# 2. 執行安裝腳本
./INSTALL.sh
```

### 方法 2: 手動安裝

```bash
# 1. 檢查 Node.js 版本
node -v  # 需要 v18+

# 2. 安裝 Gemini CLI
npm install -g @google/gemini-cli

# 3. 驗證安裝
gemini --version

# 4. 設定 API Key (選擇其中一種方式)
# 方式 A: 環境變數
export GEMINI_API_KEY="your_api_key_here"

# 方式 B: .env 檔案
echo "GEMINI_API_KEY=your_api_key_here" > ~/.gemini/.env

# 方式 C: Shell 配置檔 (.bashrc 或 .zshrc)
echo 'export GEMINI_API_KEY="your_api_key_here"' >> ~/.zshrc
```

---

## 環境配置

### 取得 API Key

1. 前往 [Google AI Studio](https://aistudio.google.com/apikey)
2. 使用 Google 帳號登入
3. 點選「Create API Key」
4. 複製產生的 API Key

### 設定方式

#### 方式 1: 使用 .env 檔案（本專案推薦）

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env 檔案
nano .env
```

填入以下內容：

```env
GEMINI_API_KEY=your_actual_api_key_here
```

#### 方式 2: Shell 環境變數

編輯 `~/.zshrc` 或 `~/.bashrc`：

```bash
# Gemini CLI API Key
export GEMINI_API_KEY="your_actual_api_key_here"
```

套用設定：

```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

#### 方式 3: 全域配置（所有專案共用）

```bash
# 創建全域配置目錄
mkdir -p ~/.gemini

# 創建全域 .env
echo "GEMINI_API_KEY=your_api_key_here" > ~/.gemini/.env
```

---

## 使用指南

### 啟動 Gemini CLI

#### 使用 OAuth 登入（推薦）

```bash
gemini
```

首次執行會開啟瀏覽器進行 Google 帳號登入。

#### 使用 API Key

```bash
# 方式 1: 臨時設定
GEMINI_API_KEY=your_key gemini

# 方式 2: 已在環境變數中設定
gemini
```

### 基本指令

#### CLI 內部指令（前綴 `/`）

| 指令 | 說明 |
|------|------|
| `/about` | 查看版本資訊 |
| `/help` | 查看可用指令 |
| `/models` | 列出可用模型 |
| `/model <name>` | 切換模型 |
| `/context` | 查看當前上下文 |
| `/clear` | 清除對話歷史 |
| `/save <name>` | 儲存對話檢查點 |
| `/load <name>` | 載入對話檢查點 |
| `/exit` 或 `/quit` | 退出 CLI |

#### 命令列參數

```bash
# 指定模型
gemini --model gemini-2.5-pro

# 使用上下文檔案
gemini --context ./GEMINI.md

# 載入檢查點
gemini --load my-checkpoint

# 查看版本
gemini --version

# 查看幫助
gemini --help
```

### 使用範例

#### 範例 1: 基本對話

```bash
$ gemini
Gemini CLI v1.0.0
> 你好，請介紹一下自己

我是 Gemini，Google 開發的大型語言模型...
```

#### 範例 2: 程式碼分析

```bash
$ gemini
> 分析這個 Python 函數的時間複雜度

def find_duplicates(arr):
    seen = set()
    duplicates = []
    for num in arr:
        if num in seen:
            duplicates.append(num)
        seen.add(num)
    return duplicates

[Gemini 會分析並回答...]
```

#### 範例 3: 使用 Context File

創建 `GEMINI.md`：

```markdown
# 專案上下文

這是一個 Python Web 應用，使用 Flask 框架。

## 技術棧
- Python 3.11
- Flask 3.0
- PostgreSQL 15
```

使用上下文：

```bash
gemini --context ./GEMINI.md
```

---

## 版本檢查

### 檢查 Gemini CLI 版本

```bash
# 方法 1: 命令列參數
gemini --version

# 方法 2: CLI 內部指令
$ gemini
> /about

# 方法 3: 使用 npm
npm list -g @google/gemini-cli
```

### 檢查 Node.js 與 npm 版本

```bash
# Node.js 版本
node -v

# npm 版本
npm -v
```

### 更新 Gemini CLI

```bash
# 查看最新版本
npm view @google/gemini-cli version

# 更新至最新版本
npm update -g @google/gemini-cli

# 或重新安裝
npm install -g @google/gemini-cli
```

---

## 故障排除

### 問題 1: `gemini: command not found`

**原因:** Gemini CLI 未正確安裝或不在 PATH 中

**解決方案:**

```bash
# 檢查是否已安裝
npm list -g @google/gemini-cli

# 重新安裝
npm install -g @google/gemini-cli

# 檢查 npm 全域安裝路徑
npm config get prefix

# 確認路徑在 PATH 中
echo $PATH
```

### 問題 2: `Node.js 版本過舊`

**原因:** Node.js 版本低於 v18

**解決方案:**

```bash
# macOS (使用 Homebrew)
brew upgrade node

# Linux (使用 nvm)
nvm install 20
nvm use 20

# 驗證版本
node -v
```

### 問題 3: `API Key 無效`

**原因:** API Key 未設定或已失效

**解決方案:**

```bash
# 1. 確認 API Key 是否正確設定
echo $GEMINI_API_KEY

# 2. 重新取得 API Key
# 前往 https://aistudio.google.com/apikey

# 3. 更新環境變數
export GEMINI_API_KEY="new_api_key"

# 4. 或編輯 .env 檔案
nano ~/.gemini/.env
```

### 問題 4: `npm install 權限錯誤`

**原因:** 沒有全域安裝權限

**解決方案:**

```bash
# 方法 1: 使用 sudo (不建議)
sudo npm install -g @google/gemini-cli

# 方法 2: 更改 npm 預設目錄 (推薦)
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
source ~/.zshrc

# 然後重新安裝
npm install -g @google/gemini-cli
```

### 問題 5: OAuth 登入失敗

**原因:** 瀏覽器未開啟或網路問題

**解決方案:**

```bash
# 改用 API Key 方式
export GEMINI_API_KEY="your_api_key"
gemini

# 或手動開啟授權 URL
# CLI 會顯示授權 URL，手動複製到瀏覽器
```

---

## 相關資源

### 官方資源

- **Gemini CLI GitHub**: https://github.com/google-gemini/gemini-cli
- **Google AI Studio**: https://aistudio.google.com/
- **API Key 管理**: https://aistudio.google.com/apikey
- **Gemini API 文檔**: https://ai.google.dev/gemini-api/docs
- **Cloud Gemini CLI 文檔**: https://cloud.google.com/gemini/docs/codeassist/gemini-cli

### 教學資源

- **DataCamp 教學**: [Gemini CLI: A Guide With Practical Examples](https://www.datacamp.com/tutorial/gemini-cli)
- **Google Codelabs**: [Hands-on with Gemini CLI](https://codelabs.developers.google.com/gemini-cli-hands-on)
- **Medium 教學系列**: [Gemini CLI Tutorial Series](https://medium.com/google-cloud/gemini-cli-tutorial-series-77da7d494718)
- **Cheatsheet**: [Google Gemini CLI Cheatsheet](https://www.philschmid.de/gemini-cli-cheatsheet)

### 社群資源

- **npm 套件**: https://www.npmjs.com/package/@google/gemini-cli
- **GitHub Releases**: https://github.com/google-gemini/gemini-cli/releases
- **GitHub Discussions**: https://github.com/google-gemini/gemini-cli/discussions

---

## 專案結構

```
CodeGemini/
├── INSTALL.sh          # 自動化安裝腳本
├── README.md           # 專案說明文件（本檔案）
├── .env.example        # 環境變數範例檔
└── .env               # 實際環境變數（需自行創建，不納入版控）
```

---

## 更新日誌

### v1.0.0 (2025-10-21)

- ✨ 初始版本發布
- ✅ 自動化安裝腳本
- ✅ 完整 README 文檔
- ✅ 環境配置範例

---

## 授權

本專案遵循 MIT License。

Google Gemini CLI 遵循 Apache-2.0 License，詳見 [官方儲存庫](https://github.com/google-gemini/gemini-cli)。

---

## 維護者

**Saki_tw** (with Claude Code)

如有問題或建議，歡迎提出 Issue 或 Pull Request。

---

**最後更新:** 2025-10-21
