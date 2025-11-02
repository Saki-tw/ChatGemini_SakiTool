# /memory - 編輯 ChatGemini.md 專案記憶

使用編輯器打開並編輯專案根目錄的 ChatGemini.md 檔案。

## 使用方式

```bash
/memory [編輯器]
```

## 參數

- `編輯器` (可選): 指定使用的編輯器
  - 若未指定，自動偵測可用編輯器（按優先順序）：
    1. `$EDITOR` 環境變數
    2. `vim`
    3. `nano`
    4. `vi`
  - 可指定編輯器：`vim`, `nano`, `code` (VSCode), `emacs` 等

## 功能

1. 自動打開 `ChatGemini.md` 檔案
2. 如果檔案不存在，自動建立繁體中文模板
3. 編輯完成後自動儲存
4. 下次啟動時新內容會自動載入

## 範例

### 使用預設編輯器
```bash
/memory
```

### 使用 vim
```bash
/memory vim
```

### 使用 VSCode
```bash
/memory code
```

### 使用 nano
```bash
/memory nano
```

## 編輯指南

### 專案概覽
更新專案名稱、類型、技術棧等基本資訊：

```markdown
## 專案概覽

**專案名稱**: ChatGemini SakiTool
**專案類型**: CLI工具
**主要技術棧**: Python 3.11+, Google Gemini API
```

### 當前任務
追蹤開發進度：

```markdown
## 當前任務

### 🔥 進行中
- [ ] 實作 ChatGemini.md 專案記憶系統
- [ ] 新增輸出格式化功能

### 📋 待辦事項
- [ ] 單元測試自動生成
- [ ] 程式碼複雜度分析

### ✅ 已完成
- [x] Extended Thinking 自動觸發
- [x] 輸出格式化（JSON/純文字）
```

### 已知問題
記錄 Bug 與修復計劃：

```markdown
## 已知問題

1. **問題描述**: Thinking 模式在某些複雜查詢可能不會自動觸發
   - **影響範圍**: gemini_thinking.py
   - **暫時方案**: 手動使用 --thinking 參數
   - **計劃修復**: 調整複雜度閾值
```

### 重要備註
AI 助手需要知道的專案特定資訊：

```markdown
## 重要備註

- 本專案使用 Google Gemini API，非 Claude API
- 所有 API 呼叫都使用 gemini_api_client.py 統一處理
- 測試必須達到 80% 覆蓋率
- 不要修改 venv_py314/ 目錄下的檔案
```

## 使用場景

- 專案資訊更新（新功能、架構變更）
- 任務追蹤（標記進度、新增待辦）
- Bug 記錄（記錄已知問題）
- 規範更新（編碼標準、命名約定）

## 技術實作

本指令呼叫 `core/project_memory.py` 的 `ProjectMemory.edit_memory()` 方法。

```python
from core.project_memory import ProjectMemory

pm = ProjectMemory()
pm.edit_memory(editor='vim')  # 或自動偵測
```

## 自動載入機制

編輯完成後，ChatGemini.md 會在下次啟動時自動載入：

1. `gemini_chat.py` 啟動時呼叫 `ProjectMemory.load_memory()`
2. 內容注入到系統提示詞
3. AI 助手可以存取專案上下文

## 相關指令

- `/init` - 初始化 ChatGemini.md 檔案（建立模板）

## 編輯器配置建議

### Vim
在 `~/.vimrc` 新增：
```vim
autocmd FileType markdown setlocal spell spelllang=zh_tw,en
autocmd BufRead,BufNewFile ChatGemini.md set filetype=markdown
```

### VSCode
安裝 Markdown 擴充功能：
- Markdown All in One
- Markdown Preview Enhanced

### Nano
使用語法高亮：
```bash
nano -Y markdown ChatGemini.md
```

## 注意事項

- 建議定期更新 ChatGemini.md（每個 Sprint/里程碑）
- 使用 Markdown 格式以保持可讀性
- 將 ChatGemini.md 納入版本控制
- 避免記錄敏感資訊（API Key、密碼等）

## 疑難排解

### 找不到編輯器
```bash
# 設定環境變數
export EDITOR=vim

# 或指定編輯器
/memory vim
```

### 檔案不存在
系統會自動建立繁體中文模板，或使用：
```bash
/init zh
```

---

**相關文件**: `core/project_memory.py`
**維護者**: ChatGemini SakiTool
