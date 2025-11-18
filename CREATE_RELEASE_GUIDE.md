# GitHub Release 建立指南 - v1.0.8

**版本**: v1.0.8
**標題**: 新增 Gemini Pro 3.0 Preview 支援

---

## 📝 手動建立 Release 步驟

### 1. 進入 GitHub Releases 頁面
訪問以下網址:
```
https://github.com/Saki-tw/ChatGemini_SakiTool/releases/new
```

### 2. 選擇 Tag
在「Choose a tag」下拉選單中選擇:
```
v1.0.8
```

### 3. 填寫 Release 標題
在「Release title」欄位輸入:
```
v1.0.8 - 新增 Gemini Pro 3.0 Preview 支援
```

### 4. 填寫 Release 描述
在「Describe this release」大文字框中貼上以下內容:

```markdown
## 🎁 新增 Gemini Pro 3.0 Preview 支援

本版本主要新增 Google 最新發布的 Gemini Pro 3.0 Preview 模型支援，並修復模型選擇器的滾動問題。

### ✨ 主要更新

- **新增 Gemini Pro 3.0 Preview 模型支援**
  - 支援最新的 Gemini Pro 3.0 預覽版本
  - 動態模型列表自動獲取最新可用模型

- **修復模型選擇器滾動問題**
  - 修復 `/model` 指令無法滾動查看所有模型的問題
  - 支援無限數量的模型顯示
  - 新增滾動提示與位置指示

### 🚀 安裝與更新

```bash
# 更新到最新版本
git pull origin main
git checkout v1.0.8

# 或重新安裝
git clone -b v1.0.8 https://github.com/Saki-tw/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool
sh INSTALL.sh --auto
```

### 📋 完整更新日誌

詳見 [CHANGELOG.md](https://github.com/Saki-tw/ChatGemini_SakiTool/blob/main/CHANGELOG.md)

---

**發布日期**: 2025-11-19
**維護者**: Saki-tw with Claude Code
```

### 5. 設定選項
- ✅ 確認「Set as the latest release」已勾選
- ❌ 不要勾選「Set as a pre-release」
- ❌ 不要勾選「Create a discussion for this release」(可選)

### 6. 發布
點擊綠色的「Publish release」按鈕

---

## 🔗 預期結果

Release 建立後,將可在以下網址查看:
```
https://github.com/Saki-tw/ChatGemini_SakiTool/releases/tag/v1.0.8
```

---

## 📸 預覽

Release 頁面將顯示:
- 標題: **v1.0.8 - 新增 Gemini Pro 3.0 Preview 支援**
- 標籤: `v1.0.8`
- 發布時間: 2025-11-19
- 描述: 完整的更新說明與安裝指引
- 資產: 自動生成的 Source code (zip) 與 Source code (tar.gz)

---

**建立時間**: 2025-11-19 03:48:00 CST
**狀態**: 待手動建立
