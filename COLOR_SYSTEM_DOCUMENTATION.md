# ChatGemini 色系設計文檔

## 專案色系哲學

ChatGemini 採用**雙主色系設計**，靈感來自日本傳統色與現代馬卡龍色彩美學的結合。

---

## 🎨 色系定義

### 1. 馬卡龍紫色系 (Macaron Purple / マカロンパープル)

**主色**: `#B565D8`
- RGB: (181, 101, 216)
- 用途：主要功能標題、重要提示、品牌識別
- 特性：柔和而不失存在感，如同馬卡龍甜點的質感

**淡色**: `#E8C4F0`
- RGB: (232, 196, 240)
- 用途：背景、分隔線、次級標題
- 特性：輕盈、透明感，營造舒適的閱讀環境

**設計理念**：
馬卡龍紫色系代表「創造力」與「優雅」，使用此色系時：
- 避免過度飽和，保持柔和質感
- 主色用於吸引注意力的元素
- 淡色用於輔助視覺層次

**應用場景**：
```python
# 主要標題與面板
console.print("[bold #B565D8]CodeGemini 開發工具選單[/bold #B565D8]")
console.print(Panel.fit(..., border_style="#B565D8"))

# 成功訊息
console.print("[#B565D8]✓ 模組載入成功[/#B565D8]")

# 進度指示
console.print(f"[#B565D8]正在處理...[/#B565D8]")
```

---

### 2. 勿忘草色系 (わすれなぐさいろ / Forget-me-not)

**主色**: `#87CEEB`
- RGB: (135, 206, 235)
- 日本傳統色名：勿忘草色 (わすれなぐさいろ)
- 色彩特徵：清澈的天空藍，如同勿忘草小花的顏色
- 用途：互動元素、輸入提示、用戶操作引導

**淡色**: `#B0E0E6`
- RGB: (176, 224, 230)
- 色彩特徵：粉末藍 (Powder Blue)
- 用途：次要資訊、輔助說明、背景漸層

**文化背景**：
勿忘草（Myosotis）是一種小型的藍色花卉，在日本文化中象徵「永恆的記憶」與「真誠的友情」。此色系在日本傳統色譜中被稱為「わすれなぐさいろ」，是一種介於天空藍與淡藍之間的柔和色調。

**色彩心理學**：
- 清新、透明、可信賴
- 促進冷靜思考與專注
- 降低視覺疲勞
- 傳達友善與開放感

**應用場景**：
```python
# 用戶輸入提示
file_path = Prompt.ask("[#87CEEB]請輸入檔案路徑[/#87CEEB]")

# 互動選項
table.add_column("選項", style="#87CEEB")

# 操作標題
console.print("\n[bold #87CEEB]📝 文檔生成器[/bold #87CEEB]")

# 選項列表
console.print("[#87CEEB]1. 選項一[/#87CEEB]")
```

---

## 🎯 使用準則

### DO (正確做法)

✅ **使用十六進制色碼**
```python
# 正確
console.print("[#B565D8]訊息[/#B565D8]")
console.print("[#87CEEB]提示[/#87CEEB]")
```

✅ **根據用途選擇色系**
- 主要功能、標題 → 馬卡龍紫 `#B565D8`
- 用戶互動、輸入 → 勿忘草 `#87CEEB`
- 成功訊息 → 保持統一，優先使用 `#B565D8`
- 資訊提示 → 使用 `#87CEEB`

✅ **保持視覺層次**
```python
# 好的層次結構
console.print("[bold #B565D8]主標題[/bold #B565D8]")  # 最顯眼
console.print("[#87CEEB]次要提示[/#87CEEB]")           # 中等
console.print("[dim]輔助說明[/dim]")                  # 最淡
```

### DON'T (錯誤做法)

❌ **不要使用顏色名稱**
```python
# 錯誤 - Rich 不識別
console.print("[plum]訊息[/plum]")
console.print("[cyan]提示[/cyan]")

# 正確
console.print("[#B565D8]訊息[/#B565D8]")
console.print("[#87CEEB]提示[/#87CEEB]")
```

❌ **不要使用非標準色**
```python
# 錯誤 - 不符合專案色系
console.print("[#DDA0DD]訊息[/#DDA0DD]")  # 舊版 plum
console.print("[#DA70D6]訊息[/#DA70D6]")  # 舊版紫色
console.print("[cyan]提示[/cyan]")        # 預設 cyan

# 正確
console.print("[#B565D8]訊息[/#B565D8]")
console.print("[#87CEEB]提示[/#87CEEB]")
```

❌ **不要混淆用途**
```python
# 不佳 - 用途混淆
file_path = Prompt.ask("[#B565D8]請輸入檔案路徑[/#B565D8]")  # 輸入應用勿忘草色
console.print("[#87CEEB]✓ 載入成功[/#87CEEB]")              # 成功應用馬卡龍紫

# 正確
file_path = Prompt.ask("[#87CEEB]請輸入檔案路徑[/#87CEEB]")
console.print("[#B565D8]✓ 載入成功[/#B565D8]")
```

---

## 📋 快速參考

### 顏色代碼速查

| 用途 | 色系 | 色碼 | 範例 |
|------|------|------|------|
| 主標題 | 馬卡龍紫 | `#B565D8` | `[bold #B565D8]CodeGemini[/bold #B565D8]` |
| 次標題 | 馬卡龍紫淡 | `#E8C4F0` | `[#E8C4F0]副標題[/#E8C4F0]` |
| 用戶輸入 | 勿忘草 | `#87CEEB` | `Prompt.ask("[#87CEEB]輸入[/#87CEEB]")` |
| 互動選項 | 勿忘草 | `#87CEEB` | `style="#87CEEB"` |
| 成功訊息 | 馬卡龍紫 | `#B565D8` | `[#B565D8]✓ 成功[/#B565D8]` |
| 處理中 | 馬卡龍紫 | `#B565D8` | `[#B565D8]處理中...[/#B565D8]` |
| 分隔線 | 馬卡龍紫淡 | `#E8C4F0` | `border_style="#E8C4F0"` |

### 配色組合建議

**組合 1：標題 + 內容**
```python
console.print("[bold #B565D8]主標題[/bold #B565D8]")
console.print("[#87CEEB]相關內容說明[/#87CEEB]")
```

**組合 2：問答式互動**
```python
console.print("[#B565D8]系統提示[/#B565D8]")
answer = Prompt.ask("[#87CEEB]請選擇[/#87CEEB]")
```

**組合 3：狀態顯示**
```python
console.print("[#B565D8]✓ 完成[/#B565D8]")
console.print("[#87CEEB]○ 等待中[/#87CEEB]")
console.print("[dim]✗ 跳過[/dim]")
```

---

## 🔍 日本傳統色：勿忘草色詳解

### 歷史與文化

**色名由來**：
- 日文：わすれなぐさいろ（勿忘草色）
- 英文：Forget-me-not blue
- 花語：「真實的愛」、「永恆的記憶」

**色彩特徵**：
- 明度：中等偏高（明亮但不刺眼）
- 彩度：中等（不過度鮮豔）
- 色相：介於天空藍與粉末藍之間
- 溫度：冷色調，但帶有溫暖的柔和感

**傳統應用**：
在日本傳統藝術中，勿忘草色常用於：
- 春季和服的配色
- 文具與書籍設計
- 傳統工藝品
- 現代數位介面設計

### 與西方色彩的對應

| 日本傳統色 | 近似西方色名 | 色碼 | 差異 |
|-----------|------------|------|------|
| 勿忘草色 | Sky Blue | `#87CEEB` | 完全相同 |
| - | Powder Blue | `#B0E0E6` | 更淡，用於次要元素 |
| - | Light Sky Blue | `#87CEFA` | 略亮，較少使用 |

---

## 🛠️ 實作檢查清單

### 新增功能時

- [ ] 確認使用 `#B565D8` 或 `#87CEEB`
- [ ] 避免使用顏色名稱（如 `plum`, `cyan`）
- [ ] 主要功能用馬卡龍紫
- [ ] 用戶互動用勿忘草色
- [ ] 保持一致的視覺層次

### Code Review 時

- [ ] 搜尋 `[plum]`, `[cyan]` 等顏色名稱
- [ ] 搜尋 `#DDA0DD`, `#DA70D6` 等非標準色碼
- [ ] 確認顏色用途符合準則
- [ ] 檢查視覺層次是否清晰

### 檢查指令

```bash
# 檢查非標準色
grep -r "plum\|cyan\|#DDA0DD\|#DA70D6" *.py

# 統計標準色使用
grep -ro "#B565D8" *.py | wc -l
grep -ro "#87CEEB" *.py | wc -l

# 檢查顏色一致性
grep -E "\[(bold )?[a-z]+\]" *.py | grep -v "#"
```

---

## 📚 參考資料

### 日本傳統色資源
- [日本の伝統色 和色大辞典](https://www.colordic.org/w/)
- [NIPPON COLORS - 日本の伝統色](https://nipponcolors.com/)
- 書籍：《日本の伝統色》長崎盛輝 著

### 色彩設計原則
- Material Design Color System
- Apple Human Interface Guidelines
- 《配色設計原理》SendPoints 編

### 終端 UI 最佳實踐
- Rich Documentation: https://rich.readthedocs.io/
- ANSI Color Standards
- Terminal Color Schemes Design Guide

---

## 📝 變更歷史

**2025-11-01**
- ✅ 統一 codegemini_manager.py 色系
- ✅ 移除所有 `plum` 顏色名稱
- ✅ 替換 `cyan` 為 `#87CEEB`
- ✅ 替換非標準紫色為 `#B565D8`
- ✅ 建立此色系文檔

---

**維護者**: ChatGemini Development Team  
**最後更新**: 2025-11-01  
**版本**: 1.0.0
