"""
pytest 全局配置與共用 fixtures

本文件定義了所有測試共用的配置、fixtures 和工具函數。

Fixtures 說明：
- sample_config: 測試用配置對象
- temp_dir: 臨時測試目錄
- mock_api_response: Mock Gemini API 響應
- sample_files: 測試用檔案集合
"""

import pytest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List

# 添加專案根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# pytest 配置
# ============================================================================

def pytest_configure(config):
    """pytest 啟動時的配置"""
    # 註冊自訂標記
    config.addinivalue_line(
        "markers", "slow: 標記為慢速測試（運行時間 > 1秒）"
    )
    config.addinivalue_line(
        "markers", "integration: 標記為整合測試"
    )
    config.addinivalue_line(
        "markers", "unit: 標記為單元測試"
    )
    config.addinivalue_line(
        "markers", "requires_api: 需要真實 API 的測試"
    )


def pytest_collection_modifyitems(config, items):
    """修改測試收集行為"""
    # 跳過需要 API 的測試（除非明確指定）
    if not config.getoption("--use-real-api", default=False):
        skip_api = pytest.mark.skip(reason="需要 --use-real-api 標誌")
        for item in items:
            if "requires_api" in item.keywords:
                item.add_marker(skip_api)


def pytest_addoption(parser):
    """添加自訂命令行選項"""
    parser.addoption(
        "--use-real-api",
        action="store_true",
        default=False,
        help="使用真實 Gemini API 進行測試（需要有效的 API Key）"
    )


# ============================================================================
# 基礎 Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def project_root() -> Path:
    """專案根目錄路徑"""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def tests_dir() -> Path:
    """測試目錄路徑"""
    return Path(__file__).parent


@pytest.fixture
def temp_dir():
    """臨時測試目錄（每個測試獨立）

    使用後自動清理

    Example:
        def test_file_operations(temp_dir):
            test_file = temp_dir / "test.txt"
            test_file.write_text("test content")
            assert test_file.exists()
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # 測試結束後清理
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture(scope="session")
def shared_temp_dir():
    """共用臨時目錄（整個測試會話共用）

    所有測試共用同一個臨時目錄，測試結束後清理
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    if temp_path.exists():
        shutil.rmtree(temp_path)


# ============================================================================
# 配置 Fixtures
# ============================================================================

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """測試用配置對象

    Returns:
        包含所有必要配置的字典
    """
    return {
        'api_key': 'test_gemini_api_key_' + 'x' * 32,
        'default_model': 'gemini-2.0-flash-exp',
        'max_conversation_history': 50,
        'unlimited_memory_mode': False,
        'auto_cache_enabled': True,
        'auto_cache_threshold': 10000,
        'translation_on_startup': False,
        'usd_to_twd': 31.5,
        'output_dir': './test_output',
        'upload_dir': './test_uploads',
        'log_level': 'DEBUG',
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """設置測試環境變數

    Args:
        monkeypatch: pytest 的 monkeypatch fixture

    Example:
        def test_with_env(mock_env_vars):
            import os
            assert os.getenv('GEMINI_API_KEY') == 'test_key'
    """
    monkeypatch.setenv('GEMINI_API_KEY', 'test_gemini_api_key_' + 'x' * 32)
    monkeypatch.setenv('GEMINI_DEFAULT_MODEL', 'gemini-2.0-flash-exp')
    monkeypatch.setenv('GEMINI_OUTPUT_DIR', './test_output')


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API 響應

    Returns:
        Mock 響應對象，模擬 Gemini API 的回應

    Example:
        def test_chat(mock_gemini_response):
            response = mock_gemini_response
            assert response.text == "This is a test response"
    """
    mock_response = Mock()
    mock_response.text = "This is a test response from Gemini"
    mock_response.parts = [Mock(text="This is a test response from Gemini")]
    mock_response.candidates = [
        Mock(
            content=Mock(
                parts=[Mock(text="This is a test response from Gemini")]
            ),
            finish_reason="STOP"
        )
    ]
    return mock_response


@pytest.fixture
def mock_gemini_model():
    """Mock Gemini 模型對象

    Returns:
        Mock GenerativeModel 對象

    Example:
        def test_generate(mock_gemini_model):
            response = mock_gemini_model.generate_content("test")
            assert response is not None
    """
    mock_model = MagicMock()

    # Mock generate_content 方法
    mock_response = Mock()
    mock_response.text = "Test response"
    mock_response.parts = [Mock(text="Test response")]
    mock_model.generate_content.return_value = mock_response

    # Mock start_chat 方法
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response
    mock_model.start_chat.return_value = mock_chat

    return mock_model


@pytest.fixture
def mock_file_upload():
    """Mock 檔案上傳響應

    Returns:
        Mock File 對象

    Example:
        def test_upload(mock_file_upload):
            file = mock_file_upload
            assert file.uri.startswith('https://generativelanguage')
    """
    mock_file = Mock()
    mock_file.name = "files/test_file_id"
    mock_file.display_name = "test_file.txt"
    mock_file.mime_type = "text/plain"
    mock_file.size_bytes = 1024
    mock_file.state = "ACTIVE"
    mock_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test_file_id"
    return mock_file


# ============================================================================
# 測試檔案 Fixtures
# ============================================================================

@pytest.fixture
def sample_text_file(temp_dir) -> Path:
    """建立範例文字檔案

    Args:
        temp_dir: 臨時目錄 fixture

    Returns:
        文字檔案路徑
    """
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is a sample text file for testing.\nSecond line.\n")
    return file_path


@pytest.fixture
def sample_python_file(temp_dir) -> Path:
    """建立範例 Python 檔案

    Args:
        temp_dir: 臨時目錄 fixture

    Returns:
        Python 檔案路徑
    """
    file_path = temp_dir / "sample.py"
    content = '''#!/usr/bin/env python3
"""Sample Python file for testing"""

def hello_world():
    """Return greeting"""
    return "Hello, World!"

class SampleClass:
    """Sample class for testing"""
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

if __name__ == "__main__":
    print(hello_world())
'''
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_json_file(temp_dir) -> Path:
    """建立範例 JSON 檔案

    Args:
        temp_dir: 臨時目錄 fixture

    Returns:
        JSON 檔案路徑
    """
    import json
    file_path = temp_dir / "sample.json"
    data = {
        "name": "Test Project",
        "version": "1.0.0",
        "features": ["feature1", "feature2"],
        "config": {
            "enabled": True,
            "timeout": 30
        }
    }
    file_path.write_text(json.dumps(data, indent=2))
    return file_path


@pytest.fixture
def sample_files(temp_dir) -> Dict[str, Path]:
    """建立多個測試檔案

    Args:
        temp_dir: 臨時目錄 fixture

    Returns:
        檔案路徑字典 {'text': Path, 'python': Path, 'json': Path}
    """
    files = {}

    # 文字檔案
    text_file = temp_dir / "test.txt"
    text_file.write_text("Test content\n")
    files['text'] = text_file

    # Python 檔案
    py_file = temp_dir / "test.py"
    py_file.write_text("def test(): pass\n")
    files['python'] = py_file

    # JSON 檔案
    import json
    json_file = temp_dir / "test.json"
    json_file.write_text(json.dumps({"test": "data"}))
    files['json'] = json_file

    return files


# ============================================================================
# CodeGemini Fixtures
# ============================================================================

@pytest.fixture
def sample_codebase(temp_dir) -> Path:
    """建立範例代碼庫結構

    Args:
        temp_dir: 臨時目錄 fixture

    Returns:
        代碼庫根目錄路徑
    """
    codebase_root = temp_dir / "sample_project"
    codebase_root.mkdir()

    # 建立基本目錄結構
    (codebase_root / "src").mkdir()
    (codebase_root / "tests").mkdir()
    (codebase_root / "docs").mkdir()

    # 建立範例檔案
    (codebase_root / "README.md").write_text("# Sample Project\n")
    (codebase_root / "src" / "main.py").write_text("def main(): pass\n")
    (codebase_root / "src" / "utils.py").write_text("def helper(): pass\n")
    (codebase_root / "tests" / "test_main.py").write_text("def test_main(): pass\n")

    return codebase_root


@pytest.fixture
def mock_vector_db():
    """Mock 向量資料庫

    Returns:
        Mock VectorDatabase 對象
    """
    mock_db = MagicMock()
    mock_db.add_chunk.return_value = "chunk_id_123"
    mock_db.search_similar.return_value = [
        ("chunk_id_1", 0.95, "Sample code chunk 1"),
        ("chunk_id_2", 0.88, "Sample code chunk 2"),
    ]
    mock_db.get_stats.return_value = {
        'total_chunks': 100,
        'total_files': 20,
    }
    return mock_db


# ============================================================================
# 工具函數
# ============================================================================

@pytest.fixture
def assert_file_exists():
    """斷言檔案存在的輔助函數

    Returns:
        檢查函數

    Example:
        def test_file_creation(temp_dir, assert_file_exists):
            file_path = temp_dir / "new_file.txt"
            file_path.write_text("content")
            assert_file_exists(file_path)
    """
    def _assert(file_path: Path, message: str = ""):
        assert file_path.exists(), f"檔案不存在: {file_path} {message}"
        assert file_path.is_file(), f"路徑不是檔案: {file_path} {message}"
    return _assert


@pytest.fixture
def assert_dir_exists():
    """斷言目錄存在的輔助函數

    Returns:
        檢查函數
    """
    def _assert(dir_path: Path, message: str = ""):
        assert dir_path.exists(), f"目錄不存在: {dir_path} {message}"
        assert dir_path.is_dir(), f"路徑不是目錄: {dir_path} {message}"
    return _assert


# ============================================================================
# 測試標記範例（供參考）
# ============================================================================

"""
測試標記使用範例：

@pytest.mark.slow
def test_slow_operation():
    '''耗時測試'''
    pass

@pytest.mark.integration
def test_integration_feature():
    '''整合測試'''
    pass

@pytest.mark.unit
def test_unit_feature():
    '''單元測試'''
    pass

@pytest.mark.requires_api
def test_with_real_api():
    '''需要真實 API'''
    pass

運行特定標記的測試：
    pytest -m slow             # 只運行慢速測試
    pytest -m "not slow"       # 跳過慢速測試
    pytest -m "unit or integration"  # 運行單元或整合測試
"""
