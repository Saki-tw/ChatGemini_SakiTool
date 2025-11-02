# CodeGemini 測試程式碼生成器

自動為 Python 程式碼生成高品質的單元測試，使用 Gemini 2.0 Flash 智能分析程式碼邏輯並生成對應的測試案例。

## 功能特點

- ✅ **自動生成單元測試**: 使用 Gemini AI 分析函數邏輯並生成測試案例
- ✅ **多框架支援**: pytest（預設）、unittest 兩種測試框架
- ✅ **智能測試案例**:
  - 正常情況測試
  - 邊界條件測試
  - 異常處理測試
  - Mock 物件處理
- ✅ **批次處理**: 支援單檔案或整個目錄的測試生成
- ✅ **預覽模式**: 在實際寫入前預覽生成的測試程式碼
- ✅ **自動備份**: 覆寫現有測試檔案前自動建立備份
- ✅ **語法驗證**: 確保生成的測試程式碼語法正確

## 安裝依賴

```bash
# 安裝測試框架
pip install pytest pytest-mock

# 或使用 unittest（Python 內建，無需安裝）
```

## 快速開始

### 基本使用

```bash
# 為單一檔案生成測試
python3 CodeGemini/generators/test_gen.py myfile.py

# 為整個目錄生成測試
python3 CodeGemini/generators/test_gen.py src/ --output tests/

# 預覽模式（不實際寫入檔案）
python3 CodeGemini/generators/test_gen.py myfile.py --preview
```

### 進階使用

```bash
# 使用 unittest 框架
python3 CodeGemini/generators/test_gen.py myfile.py --framework unittest

# 覆寫現有測試檔案
python3 CodeGemini/generators/test_gen.py myfile.py --overwrite

# 指定輸出目錄
python3 CodeGemini/generators/test_gen.py myfile.py --output tests/unit/

# 批次處理目錄並覆寫
python3 CodeGemini/generators/test_gen.py src/ --output tests/ --overwrite
```

## CLI 參數說明

### 位置參數

- `source_path`: 要生成測試的 Python 檔案或目錄路徑（必填）

### 可選參數

- `--framework {pytest,unittest}`: 測試框架選擇（預設: pytest）
  - `pytest`: 使用 pytest 框架（推薦）
  - `unittest`: 使用 Python 內建 unittest 框架

- `--output OUTPUT_DIR`: 測試檔案輸出目錄（預設: tests/）
  - 單檔案: 輸出為 `OUTPUT_DIR/test_<filename>.py`
  - 目錄: 保持相同目錄結構於輸出目錄下

- `--preview`: 預覽模式，顯示生成的測試但不寫入檔案
  - 用於檢查生成品質
  - 不會建立任何檔案

- `--overwrite`: 覆寫現有測試檔案
  - 預設行為: 如果測試檔案已存在則跳過
  - 使用此參數: 覆寫前會自動建立帶時間戳的備份

## 使用範例

### 範例 1: 單檔案生成（基本）

為 `calculator.py` 生成 pytest 測試：

```bash
python3 CodeGemini/generators/test_gen.py calculator.py
```

生成結果:
- 輸出檔案: `tests/test_calculator.py`
- 包含所有函數的測試案例
- 使用 pytest 框架

### 範例 2: 整個目錄生成

為 `src/` 目錄下所有 Python 檔案生成測試：

```bash
python3 CodeGemini/generators/test_gen.py src/ --output tests/
```

目錄結構範例:
```
src/
├── models/
│   ├── user.py
│   └── product.py
└── utils/
    └── helpers.py

tests/
├── models/
│   ├── test_user.py
│   └── test_product.py
└── utils/
    └── test_helpers.py
```

### 範例 3: 預覽模式

在實際寫入前預覽生成的測試：

```bash
python3 CodeGemini/generators/test_gen.py myfile.py --preview
```

輸出範例:
```
🧪 CodeGemini 測試生成器 - 預覽模式

檔案: myfile.py
框架: pytest
輸出: tests/test_myfile.py

生成的測試程式碼:
================================================================================
import pytest
from myfile import calculate_sum, process_data

def test_calculate_sum():
    """測試 calculate_sum 函數"""
    # 正常情況
    assert calculate_sum(1, 2) == 3
    assert calculate_sum(0, 0) == 0

    # 負數
    assert calculate_sum(-1, 1) == 0
    assert calculate_sum(-5, -3) == -8

...
================================================================================

✓ 語法驗證: 通過
預覽模式: 未寫入檔案
```

### 範例 4: 使用 unittest 框架

生成使用 unittest 框架的測試：

```bash
python3 CodeGemini/generators/test_gen.py myfile.py --framework unittest
```

生成的測試程式碼範例:
```python
import unittest
from myfile import calculate_sum

class TestCalculateSum(unittest.TestCase):
    def test_normal_case(self):
        """測試正常情況"""
        self.assertEqual(calculate_sum(1, 2), 3)
        self.assertEqual(calculate_sum(0, 0), 0)

    def test_negative_numbers(self):
        """測試負數"""
        self.assertEqual(calculate_sum(-1, 1), 0)
        self.assertEqual(calculate_sum(-5, -3), -8)

if __name__ == '__main__':
    unittest.main()
```

### 範例 5: 覆寫現有測試

更新現有測試檔案（會自動備份）：

```bash
python3 CodeGemini/generators/test_gen.py myfile.py --overwrite
```

輸出範例:
```
⚠️  測試檔案已存在: tests/test_myfile.py
✓ 備份已建立: tests/test_myfile.py.backup_20251101_103000
✓ 測試生成成功: tests/test_myfile.py
```

## 工作流程

1. **程式碼分析**: 使用 AST 解析 Python 原始碼
2. **函數提取**: 識別所有可測試的函數和方法
3. **測試生成**: 使用 Gemini AI 分析函數邏輯並生成測試案例
4. **語法驗證**: 確保生成的測試程式碼語法正確
5. **檔案寫入**: 將測試寫入指定輸出目錄

## 生成的測試品質

每個函數會生成以下類型的測試案例:

### 1. 正常情況測試
- 驗證函數的基本功能
- 測試預期的輸入輸出

### 2. 邊界條件測試
- 空值測試 (`None`, `[]`, `{}`)
- 極值測試（最大值、最小值）
- 特殊值測試

### 3. 異常處理測試
- 驗證錯誤處理邏輯
- 測試預期的異常拋出

### 4. Mock 測試（如適用）
- 外部依賴的 Mock
- 檔案 I/O 的 Mock
- API 調用的 Mock

## 輸出檔案命名規則

### 單檔案
- 輸入: `myfile.py`
- 輸出: `tests/test_myfile.py`

### 目錄結構
保持與原始碼相同的目錄結構:
- 輸入: `src/models/user.py`
- 輸出: `tests/models/test_user.py`

## 限制與已知問題

### 限制
1. **僅支援 Python**: 目前僅支援 Python 程式碼測試生成
2. **函數級別**: 僅生成函數/方法級別的測試，不處理模組級別的程式碼
3. **Gemini API 配額**: 大量生成測試時可能遇到 API 配額限制
4. **複雜邏輯**: 非常複雜的函數可能生成不夠全面的測試案例

### 已知問題
1. **Mock 自動生成**: 複雜的外部依賴可能需要手動調整 Mock 設定
2. **私有函數**: 以 `_` 開頭的私有函數預設不生成測試（可考慮未來支援）
3. **裝飾器**: 某些複雜裝飾器可能影響測試生成品質
4. **異步函數**: `async`/`await` 函數的測試支援有限

### 建議
- **人工審查**: 生成的測試應經過人工審查和調整
- **邊界案例**: 根據業務邏輯補充額外的邊界案例測試
- **整合測試**: 此工具專注單元測試，整合測試需額外撰寫
- **測試覆蓋率**: 使用 `pytest-cov` 檢查測試覆蓋率並補充遺漏部分

## 範例專案結構

```
my_project/
├── src/
│   ├── __init__.py
│   ├── calculator.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── test_user.py
│   └── utils/
│       ├── __init__.py
│       └── test_helpers.py
├── pytest.ini
└── requirements.txt
```

## 設定檔案範例

### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

### requirements.txt
```
pytest>=7.0.0
pytest-mock>=3.0.0
pytest-cov>=4.0.0
```

## 進階技巧

### 1. 批次生成並檢查覆蓋率

```bash
# 生成測試
python3 CodeGemini/generators/test_gen.py src/ --output tests/

# 執行測試並檢查覆蓋率
pytest tests/ --cov=src --cov-report=html

# 查看覆蓋率報告
open htmlcov/index.html
```

### 2. 僅為特定模組生成測試

```bash
# 僅為 models 目錄生成測試
python3 CodeGemini/generators/test_gen.py src/models/ --output tests/models/
```

### 3. 預覽後手動調整

```bash
# 先預覽
python3 CodeGemini/generators/test_gen.py myfile.py --preview > preview.txt

# 檢查後再生成
python3 CodeGemini/generators/test_gen.py myfile.py
```

## 疑難排解

### 問題: Gemini API 錯誤

```
錯誤: 未找到 GEMINI_API_KEY 環境變數
```

**解決方案**:
```bash
export GEMINI_API_KEY="your_api_key_here"
```

### 問題: 語法錯誤

```
⚠️ 語法驗證失敗: invalid syntax
```

**解決方案**:
- 使用預覽模式檢查生成的程式碼
- 如果問題持續，請手動調整或重新生成

### 問題: 測試檔案已存在

```
⚠️ 測試檔案已存在，使用 --overwrite 參數覆寫
```

**解決方案**:
```bash
python3 CodeGemini/generators/test_gen.py myfile.py --overwrite
```

## 相關工具

- [pytest](https://pytest.org/) - Python 測試框架
- [pytest-mock](https://pytest-mock.readthedocs.io/) - Mock 支援
- [pytest-cov](https://pytest-cov.readthedocs.io/) - 覆蓋率報告
- [unittest](https://docs.python.org/3/library/unittest.html) - Python 內建測試框架

## 授權

此工具為 CodeGemini 專案的一部分。

## 貢獻

歡迎提交 Issue 或 Pull Request！

## 變更日誌

### v1.0.0 (2025-11-01)
- ✅ 初始版本發布
- ✅ 支援 pytest 和 unittest 框架
- ✅ 支援單檔案和目錄批次生成
- ✅ 預覽模式
- ✅ 自動備份功能
- ✅ 語法驗證
