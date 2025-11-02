# /init - 初始化 ChatGemini.md 專案記憶

初始化專案根目錄的 ChatGemini.md 檔案，建立專案記憶模板。

## 使用方式

```bash
/init [語言]
```

## 參數

- `語言` (可選): 模板語言，支援：
  - `zh` - 繁體中文（預設）
  - `en` - English
  - `ja` - 日本語

## 功能

1. 在專案根目錄建立 `ChatGemini.md` 檔案
2. 填充多語言模板（包含專案結構、開發規範、任務追蹤等）
3. 自動填入當前時間戳記
4. 如果檔案已存在，會提示使用者（不會覆蓋）

## 範例

### 繁體中文模板（預設）
```bash
/init
/init zh
```

### English Template
```bash
/init en
```

### 日本語テンプレート
```bash
/init ja
```

## ChatGemini.md 模板內容

模板包含以下區塊：

1. **專案概覽** - 專案名稱、類型、技術棧
2. **專案結構** - 目錄結構說明
3. **關鍵資訊** - 開發規範、重要約定、常用指令
4. **當前任務** - 進行中/待辦/已完成任務清單
5. **已知問題** - Bug 追蹤與修復計劃
6. **重要備註** - AI 助手應該知道的專案特定資訊

## 使用場景

- 新專案啟動時建立專案記憶
- 為現有專案添加 AI 工具上下文
- 團隊協作時統一專案資訊

## 技術實作

本指令呼叫 `core/project_memory.py` 的 `ProjectMemory.init_memory_file()` 方法。

```python
from core.project_memory import ProjectMemory

pm = ProjectMemory()
pm.init_memory_file(language='zh')
```

## 相關指令

- `/memory` - 編輯 ChatGemini.md 檔案

## 注意事項

- ChatGemini.md 會在啟動時自動載入並注入到系統提示詞
- 請定期更新 ChatGemini.md 以保持專案資訊同步
- 建議將 ChatGemini.md 加入版本控制（Git）

---

**相關文件**: `core/project_memory.py`
**維護者**: ChatGemini SakiTool
