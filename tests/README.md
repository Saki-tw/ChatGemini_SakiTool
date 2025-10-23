# ChatGemini_SakiTool 測試框架說明

## 📋 目錄

1. [測試框架概述](#測試框架概述)
2. [測試結構](#測試結構)
3. [如何運行測試](#如何運行測試)
4. [測試撰寫規範](#測試撰寫規範)
5. [測試覆蓋率目標](#測試覆蓋率目標)
6. [常見問題](#常見問題)

---

## 測試框架概述

本專案使用 **pytest** 作為測試框架，提供簡潔且強大的測試能力。

### 為什麼選擇 pytest？

- ✅ 簡潔的語法（無需繼承 unittest.TestCase）
- ✅ 強大的 fixture 系統
- ✅ 詳細的錯誤報告
- ✅ 豐富的插件生態系統
- ✅ 支援參數化測試
- ✅ 並行測試執行

### 安裝測試依賴

```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio pytest-xdist
```

---

## 測試結構

```
tests/
├── README.md                          # 本文件
├── conftest.py                        # pytest 全局配置與 fixtures
├── run_all_tests.sh                   # 一鍵運行所有測試
│
├── test_gemini_chat.py                # 主對話系統測試
├── test_gemini_file_manager.py        # 檔案管理器測試
├── test_codebase_embedding.py         # 代碼嵌入測試
├── test_memory_management.py          # 記憶體管理測試（已完成）
├── test_orthogonality_optimization.py # 正交優化測試（已完成）
│
└── fixtures/                          # 測試數據與 fixtures
    ├── sample_code.py                 # 範例代碼檔案
    ├── sample_image.jpg               # 範例圖片
    └── sample_video.mp4               # 範例影片
```

### 測試文件命名規範

- 測試文件必須以 `test_` 開頭：`test_module_name.py`
- 測試類別必須以 `Test` 開頭：`class TestClassName:`
- 測試函數必須以 `test_` 開頭：`def test_function_name():`

---

## 如何運行測試

### 運行所有測試

```bash
# 使用一鍵腳本（推薦）
./tests/run_all_tests.sh

# 或直接使用 pytest
pytest tests/
```

### 運行特定測試文件

```bash
pytest tests/test_gemini_chat.py
```

### 運行特定測試函數

```bash
pytest tests/test_gemini_chat.py::test_chat_initialization
```

### 運行測試並顯示覆蓋率

```bash
pytest tests/ --cov=. --cov-report=html
```

生成的報告位於 `htmlcov/index.html`

### 並行運行測試（加速）

```bash
pytest tests/ -n auto  # 自動使用所有 CPU 核心
```

### 詳細輸出模式

```bash
pytest tests/ -v        # verbose 模式
pytest tests/ -vv       # 更詳細的輸出
pytest tests/ -s        # 顯示 print 輸出
```

---

## 測試撰寫規範

### 1. 基本測試結構

```python
import pytest
from module_name import function_to_test

def test_function_behavior():
    """測試函數的基本行為

    Arrange（準備）: 設置測試數據
    Act（執行）: 調用被測試的函數
    Assert（斷言）: 驗證結果
    """
    # Arrange
    input_data = "test input"
    expected_output = "expected result"

    # Act
    result = function_to_test(input_data)

    # Assert
    assert result == expected_output
```

### 2. 使用 Fixtures

```python
@pytest.fixture
def sample_config():
    """提供測試用的配置對象"""
    return {
        'api_key': 'test_key',
        'model': 'gemini-2.0-flash-exp'
    }

def test_with_fixture(sample_config):
    """使用 fixture 的測試"""
    assert sample_config['model'] == 'gemini-2.0-flash-exp'
```

### 3. 參數化測試

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("pytest", "PYTEST"),
])
def test_uppercase(input, expected):
    """參數化測試多組數據"""
    assert input.upper() == expected
```

### 4. 測試異常

```python
def test_function_raises_error():
    """測試函數是否正確拋出異常"""
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_should_raise("bad input")
```

### 5. Mock 外部依賴

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """使用 Mock 替代外部依賴"""
    mock_api = Mock()
    mock_api.get_response.return_value = "mocked response"

    result = function_using_api(mock_api)

    assert result == "mocked response"
    mock_api.get_response.assert_called_once()
```

### 6. 異步測試

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """測試異步函數"""
    result = await async_function()
    assert result is not None
```

---

## 測試覆蓋率目標

### 當前狀態（2025-10-23）

| 模組 | 覆蓋率 | 狀態 | 目標 |
|------|--------|------|------|
| **gemini_chat.py** | 0% | ❌ 待建立 | 60% |
| **gemini_file_manager.py** | 0% | ❌ 待建立 | 70% |
| **codebase_embedding.py** | 0% | ❌ 待建立 | 80% |
| **memory_management** | 85% | ✅ 已完成 | 85% |
| **orthogonality_optimization** | 90% | ✅ 已完成 | 90% |
| **整體專案** | ~15% | ⚠️ 低 | **60%** |

### 階段性目標

#### Phase 1（本次實作）- 基礎建設
- ✅ 建立測試框架
- ✅ 建立核心模組測試骨架
- 🎯 目標：整體覆蓋率達到 **25%**

#### Phase 2（1-2 週內）
- 補充核心功能測試
- 增加邊界條件測試
- 🎯 目標：整體覆蓋率達到 **40%**

#### Phase 3（1 個月內）
- 補充整合測試
- 增加錯誤處理測試
- 🎯 目標：整體覆蓋率達到 **60%**

### 優先測試模組

**高優先級**（核心功能）:
1. ✅ memory_management（已完成）
2. ✅ orthogonality_optimization（已完成）
3. ❌ gemini_chat.py（主對話系統）
4. ❌ gemini_file_manager.py（檔案管理）
5. ❌ codebase_embedding.py（代碼嵌入）

**中優先級**（輔助功能）:
6. gemini_upload_helper.py
7. config.py
8. gemini_error_handler.py

**低優先級**（工具與輔助）:
9. utils/path_manager.py
10. utils/performance_monitor.py

---

## 常見問題

### Q1: 為什麼測試失敗？

**常見原因**:
1. 缺少環境變數（GEMINI_API_KEY）
2. Mock 未正確配置
3. 測試數據不正確

**解決方法**:
```bash
# 設置測試環境變數
export GEMINI_API_KEY="your_test_key"

# 使用 -v 查看詳細錯誤
pytest tests/ -v
```

### Q2: 如何跳過特定測試？

```python
@pytest.mark.skip(reason="功能尚未實作")
def test_unimplemented_feature():
    pass

@pytest.mark.skipif(condition, reason="條件不符")
def test_conditional():
    pass
```

### Q3: 如何只運行特定標記的測試？

```python
# 標記測試
@pytest.mark.slow
def test_slow_function():
    pass

# 運行時篩選
pytest tests/ -m slow      # 只運行 slow 標記的測試
pytest tests/ -m "not slow"  # 跳過 slow 標記的測試
```

### Q4: 如何測試需要 API 的功能？

**方法 1: 使用 Mock**（推薦）
```python
@patch('module.api_call')
def test_with_mock_api(mock_api):
    mock_api.return_value = "mocked response"
    result = function_using_api()
    assert result is not None
```

**方法 2: 使用測試 API Key**
```bash
export GEMINI_API_KEY_TEST="test_key_here"
pytest tests/ --use-real-api
```

### Q5: 測試覆蓋率如何計算？

```bash
# 生成 HTML 報告
pytest tests/ --cov=. --cov-report=html

# 生成終端報告
pytest tests/ --cov=. --cov-report=term-missing

# 檢查覆蓋率是否達標
pytest tests/ --cov=. --cov-fail-under=60
```

---

## 最佳實踐

### ✅ DO（推薦做法）

1. **測試應該獨立且可重複執行**
   - 不依賴執行順序
   - 每次運行結果一致

2. **使用有意義的測試名稱**
   ```python
   # Good
   def test_user_login_with_valid_credentials():

   # Bad
   def test_1():
   ```

3. **一個測試只驗證一個行為**
   ```python
   # Good - 分開測試
   def test_add_positive_numbers():
   def test_add_negative_numbers():

   # Bad - 混合太多邏輯
   def test_add_all_cases():
   ```

4. **使用 Fixtures 重用測試數據**

5. **為邊界條件撰寫測試**
   - 空輸入、None、極大值、極小值

### ❌ DON'T（避免做法）

1. **不要在測試中使用真實的外部資源**
   - ❌ 不要連接真實 API
   - ❌ 不要修改真實文件
   - ✅ 使用 Mock 或 Stub

2. **不要忽略失敗的測試**
   - 修復測試或移除測試
   - 不要用 `@pytest.mark.skip` 無限期跳過

3. **不要測試第三方庫的功能**
   - 只測試自己的代碼邏輯

4. **不要過度 Mock**
   - Mock 應該模擬外部依賴，而非內部邏輯

---

## 參考資源

- [pytest 官方文檔](https://docs.pytest.org/)
- [pytest-cov 文檔](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://testdriven.io/blog/python-testing/)
- [Real Python - Testing Guide](https://realpython.com/pytest-python-testing/)

---

**文件版本**: v1.0
**建立時間**: 2025-10-23
**維護者**: Saki-tw
**狀態**: ✅ 使用中
