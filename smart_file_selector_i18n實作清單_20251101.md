# smart_file_selector.py i18n 實作清單

**生成時間**: 2025-11-01 23:05 CST
**目標**: 完成 smart_file_selector.py 的 i18n 整合，達到 100% 完成度

---

## 📊 現況分析

### ✅ 已完成項目
- **程式碼 i18n 轉換**: 100% 完成
  - 第 17 行已導入 `from i18n_utils import t`
  - 所有用戶可見字串已使用 `t()` 函數包裝
  - 共 51 個 t() 函數調用
  - 32 個唯一翻譯鍵

### ⚠️ 待完成項目
- **語言檔案整合**: 0% 完成
  - zh_TW.yaml: 缺少 file.selector 區段
  - en.yaml: 缺少 file.selector 區段
  - ja.yaml: 缺少 file.selector 區段
  - ko.yaml: 缺少 file.selector 區段

---

## 🔑 翻譯鍵清單 (32 個)

### 1. 定價與報價 (1 個)
- `file.selector.pricing.estimate` - 即時報價顯示

### 2. 表格顯示 (5 個)
- `file.selector.table.title` - 表格標題
- `file.selector.table.filename` - 檔案名稱欄位
- `file.selector.table.confidence` - 信心度欄位
- `file.selector.table.size` - 檔案大小欄位
- `file.selector.table.modified` - 修改時間欄位

### 3. 提示與說明 (4 個)
- `file.selector.prompt.select` - 選擇提示
- `file.selector.prompt.help_multi` - 多選說明
- `file.selector.prompt.help_all_cancel` - 全選/取消說明
- `file.selector.choice` - 選擇輸入提示

### 4. 錯誤訊息 (3 個)
- `file.selector.error.no_valid` - 無有效選擇
- `file.selector.error.invalid_format` - 格式錯誤
- `file.selector.cancelled` - 已取消

### 5. 互動訊息 (4 個)
- `file.selector.selected` - 已選擇提示（含參數: count）
- `file.selector.confirm` - 確認提示
- `file.selector.reselect` - 重新選擇提示
- `file.selector.unknown` - 未知值

### 6. 高信心度路徑 (6 個)
- `file.selector.best_match` - 最佳匹配顯示（含參數: name, confidence, path）
- `file.selector.use_default` - 使用預設提示
- `file.selector.manual_mode` - 手動模式提示
- `file.selector.sorted_confidence` - 按信心度排序標題（含參數: top_n）
- `file.selector.options.high_confidence` - 高信心度選項說明（含參數: max_num）
- `file.selector.please_select` - 請選擇提示

### 7. 低信心度路徑 (4 個)
- `file.selector.low_confidence_warning` - 低信心度警告
- `file.selector.top_confidence` - 信心度最高項目標題
- `file.selector.top_time` - 時間最近項目標題
- `file.selector.options.low_confidence` - 低信心度選項說明（含參數: max_num）

### 8. 通用選項 (4 個)
- `file.selector.all_files_time` - 顯示全部（時間排序）
- `file.selector.sorted_time` - 按時間排序標題
- `file.selector.select_from_list` - 從清單選擇提示
- `file.selector.no_files` - 無檔案錯誤

### 9. 主入口 (1 個)
- `file.selector.header` - 智能選擇標題（含參數: count, confidence）

---

## 📋 實作步驟

### Step 1: 提取翻譯鍵並生成 YAML 內容 ✅ 準備執行
**任務**: 從 smart_file_selector.py 提取所有中文字串對應到翻譯鍵
**輸出**: file_selector_translations_zh_TW.yaml

**方法**:
1. 逐行分析 smart_file_selector.py
2. 提取每個 t() 調用的 key 及其對應的中文原文
3. 生成標準 YAML 格式

**預計時間**: 10 分鐘

---

### Step 2: 整合到 zh_TW.yaml ✅ 準備執行
**任務**: 將新翻譯鍵加入 zh_TW.yaml 的 file 區段
**位置**: file: 區段下新增 selector: 子區段
**行號**: 第 929 行之後

**操作**:
```yaml
file:
  # ... 既有內容 ...

  # 智能檔案選擇器 (smart_file_selector.py)
  selector:
    # 定價與報價
    pricing:
      estimate: |
        💰 預估費用
        選擇檔案數: {selected_count}
        單檔成本: NT$ {single_cost:.4f}
        總計: NT$ {total_cost_twd:.2f} (≈ ${total_cost_usd:.4f} USD)

    # ... 其他 31 個鍵 ...
```

**預計時間**: 5 分鐘

---

### Step 3: 整合到 en.yaml（待翻譯標記） ✅ 準備執行
**任務**: 複製結構到 en.yaml，保留中文並加上「待翻譯」標記
**位置**: file: 區段下新增 selector: 子區段

**標記格式**:
```yaml
# smart_file_selector.py - 待翻譯 (2025-11-01)
selector:
  pricing:
    estimate: |
      💰 預估費用
      選擇檔案數: {selected_count}
      ...
```

**預計時間**: 3 分鐘

---

### Step 4: 整合到 ja.yaml（待翻譯標記） ✅ 準備執行
**任務**: 同 Step 3，複製到 ja.yaml
**預計時間**: 3 分鐘

---

### Step 5: 整合到 ko.yaml（待翻譯標記） ✅ 準備執行
**任務**: 同 Step 3，複製到 ko.yaml
**預計時間**: 3 分鐘

---

### Step 6: 驗證語言檔案語法 ✅ 準備執行
**任務**: 使用 Python YAML parser 驗證 4 個語言檔案

**驗證腳本**:
```python
import yaml

files = ['zh_TW.yaml', 'en.yaml', 'ja.yaml', 'ko.yaml']
for f in files:
    with open(f'locales/{f}', 'r', encoding='utf-8') as file:
        yaml.safe_load(file)
        print(f"✓ {f} 語法正確")
```

**預計時間**: 2 分鐘

---

### Step 7: 測試 smart_file_selector.py 運行 ✅ 準備執行
**任務**: 執行測試代碼驗證翻譯正常運作

**測試命令**:
```bash
python3 smart_file_selector.py
```

**驗證點**:
- 所有 t() 調用成功讀取翻譯
- 無 KeyError 或 fallback 警告
- 界面顯示繁體中文

**預計時間**: 5 分鐘

---

### Step 8: 生成最終完成報告 ✅ 準備執行
**任務**: 生成 i18n Phase 5 100% 完成報告

**報告內容**:
- 最終統計數據
- 所有檔案轉換清單
- 語言檔案行數變化
- 時間戳記與簽名

**預計時間**: 5 分鐘

---

## 📈 整體完成度預估

| 階段 | 狀態 | 預計時間 |
|------|------|----------|
| 程式碼轉換 | ✅ 100% | - |
| 翻譯鍵提取 | ⏳ 準備中 | 10 分鐘 |
| zh_TW 整合 | ⏳ 準備中 | 5 分鐘 |
| en/ja/ko 整合 | ⏳ 準備中 | 9 分鐘 |
| 語法驗證 | ⏳ 準備中 | 2 分鐘 |
| 運行測試 | ⏳ 準備中 | 5 分鐘 |
| 完成報告 | ⏳ 準備中 | 5 分鐘 |
| **總計** | **50%** | **36 分鐘** |

---

## 🎯 預期成果

完成後將達到：
- ✅ smart_file_selector.py 完全 i18n 化
- ✅ 4 個語言檔案包含完整的 file.selector 區段
- ✅ 所有翻譯鍵在 zh_TW.yaml 中有正確的繁體中文翻譯
- ✅ en/ja/ko.yaml 有完整結構（待專業翻譯）
- ✅ 界面顯示正常，無 KeyError
- ✅ i18n Phase 5 達到 100% 完成度

---

## 📝 備註

1. **不修改程式碼**: smart_file_selector.py 已經正確使用 t() 函數，無需修改
2. **翻譯策略**: 先完成 zh_TW，en/ja/ko 保留中文待後續專業翻譯
3. **測試優先**: 每個步驟後都驗證語法正確性
4. **時間戳記**: 所有修改都記錄時間戳記以供追蹤

---

**生成者**: Claude Code
**審核狀態**: 待執行
**預計完成時間**: 2025-11-01 23:45 CST
