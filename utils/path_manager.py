#!/usr/bin/env python3
"""
統一路徑管理工具
管理所有輸入與輸出路徑，支援絕對路徑與相對路徑

功能：
1. 輸出路徑管理（7 個標準目錄）
2. 輸入路徑解析（支援絕對/相對路徑）
3. 路徑驗證與標準化
4. 輸入來源管理
"""

import sys
from pathlib import Path
from typing import Optional, Literal, Union

# 動態添加父目錄到 sys.path（避免 import 循環）
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_unified import unified_config

# 從統一配置獲取路徑設定
OUTPUT_DIRS = unified_config.get('output_dirs', {})
MEDIA_SUBDIRS = unified_config.get('media_subdirs', {})
PROJECT_ROOT = unified_config.get('project_root', Path(__file__).parent.parent)


# ==========================================
# 輸出路徑管理
# ==========================================

def get_output_dir(
    category: Literal['chat_logs', 'code_logs', 'diagnostics',
                      'system_tool', 'cache', 'videos', 'images', 'audio'],
    subdir: Optional[str] = None,
    create: bool = True
) -> Path:
    """取得輸出目錄路徑

    Args:
        category: 目錄類別
            - 'chat_logs': 對話日誌
            - 'code_logs': CodeGemini 日誌
            - 'diagnostics': 診斷輸出
            - 'system_tool': 系統工具輸出
            - 'cache': 快取檔案
            - 'videos': 影片輸出
            - 'images': 圖片輸出
            - 'audio': 音訊輸出
        subdir: 子目錄名稱（可選）
        create: 是否自動建立目錄

    Returns:
        Path 物件

    Example:
        >>> get_output_dir('videos', 'veo')
        PosixPath('.../MediaOutputs/Videos/veo')
    """
    # 媒體類別從 MEDIA_SUBDIRS 取得
    if category in ['videos', 'images', 'audio']:
        base_dir = MEDIA_SUBDIRS[category]
    else:
        base_dir = OUTPUT_DIRS[category]

    # 處理子目錄
    if subdir:
        output_dir = base_dir / subdir
    else:
        output_dir = base_dir

    # 自動建立目錄
    if create:
        output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


# ========== 便利函數（輸出路徑）==========

def get_video_dir(video_type: Optional[str] = None) -> Path:
    """取得影片輸出目錄

    Args:
        video_type: 影片類型（可選），例如 'veo', 'effects', 'flow' 等

    Returns:
        Path 物件

    Example:
        >>> get_video_dir('veo')
        PosixPath('.../MediaOutputs/Videos/veo')
    """
    return get_output_dir('videos', video_type)


def get_image_dir(image_type: Optional[str] = None) -> Path:
    """取得圖片輸出目錄

    Args:
        image_type: 圖片類型（可選），例如 'imagen', 'generated' 等

    Returns:
        Path 物件
    """
    return get_output_dir('images', image_type)


def get_audio_dir(audio_type: Optional[str] = None) -> Path:
    """取得音訊輸出目錄

    Args:
        audio_type: 音訊類型（可選），例如 'extracted', 'processed' 等

    Returns:
        Path 物件
    """
    return get_output_dir('audio', audio_type)


def get_chat_log_dir() -> Path:
    """取得對話日誌目錄

    Returns:
        Path 物件
    """
    return OUTPUT_DIRS['chat_logs']


def get_code_log_dir() -> Path:
    """取得 CodeGemini 日誌目錄

    Returns:
        Path 物件
    """
    return OUTPUT_DIRS['code_logs']


def get_cache_dir(cache_type: Optional[str] = None) -> Path:
    """取得快取目錄

    Args:
        cache_type: 快取類型（可選），例如 'api_cache', 'embeddings' 等

    Returns:
        Path 物件
    """
    return get_output_dir('cache', cache_type)


def get_diagnostics_dir(subtype: Optional[str] = None) -> Path:
    """取得診斷輸出目錄

    Args:
        subtype: 診斷子類型（可選），例如 'recovery', 'error_logs', 'batch' 等

    Returns:
        Path 物件
    """
    return get_output_dir('diagnostics', subtype)


def get_system_tool_dir(tool_name: Optional[str] = None) -> Path:
    """取得系統工具輸出目錄

    Args:
        tool_name: 工具名稱（可選）

    Returns:
        Path 物件
    """
    return get_output_dir('system_tool', tool_name)


# ==========================================
# 輸入路徑管理
# ==========================================

class PathResolver:
    """路徑解析器（支援絕對路徑與相對路徑）

    用於統一處理使用者輸入的路徑，自動識別絕對路徑與相對路徑，
    並提供路徑驗證、標準化等功能。
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """初始化路徑解析器

        Args:
            base_dir: 相對路徑的基準目錄（預設為專案根目錄）
        """
        self.base_dir = base_dir or PROJECT_ROOT

    def resolve(self, path: Union[str, Path], must_exist: bool = True) -> Path:
        """解析路徑（自動處理絕對/相對路徑）

        Args:
            path: 輸入路徑（字串或 Path 物件）
            must_exist: 是否要求檔案/目錄必須存在

        Returns:
            解析後的絕對路徑

        Raises:
            FileNotFoundError: 當 must_exist=True 且檔案不存在時
            ValueError: 當路徑格式無效時

        Example:
            >>> resolver = PathResolver()
            >>> resolver.resolve("/absolute/path/file.mp4")
            PosixPath('/absolute/path/file.mp4')
            >>> resolver.resolve("relative/path/file.mp4")
            PosixPath('.../ChatGemini_SakiTool/relative/path/file.mp4')
        """
        if not path:
            raise ValueError("路徑不能為空")

        # 轉換為 Path 物件
        path_obj = Path(path)

        # 處理絕對路徑
        if path_obj.is_absolute():
            resolved = path_obj
        else:
            # 處理相對路徑（相對於 base_dir）
            resolved = (self.base_dir / path_obj).resolve()

        # 驗證存在性
        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"路徑不存在: {resolved}")

        return resolved

    def resolve_file(self, path: Union[str, Path], must_exist: bool = True) -> Path:
        """解析檔案路徑（確保是檔案）

        Args:
            path: 檔案路徑
            must_exist: 是否要求檔案必須存在

        Returns:
            解析後的絕對路徑

        Raises:
            FileNotFoundError: 檔案不存在
            ValueError: 路徑不是檔案
        """
        resolved = self.resolve(path, must_exist)

        if must_exist and not resolved.is_file():
            raise ValueError(f"路徑不是檔案: {resolved}")

        return resolved

    def resolve_dir(self, path: Union[str, Path], must_exist: bool = True) -> Path:
        """解析目錄路徑（確保是目錄）

        Args:
            path: 目錄路徑
            must_exist: 是否要求目錄必須存在

        Returns:
            解析後的絕對路徑

        Raises:
            FileNotFoundError: 目錄不存在
            ValueError: 路徑不是目錄
        """
        resolved = self.resolve(path, must_exist)

        if must_exist and not resolved.is_dir():
            raise ValueError(f"路徑不是目錄: {resolved}")

        return resolved

    def to_relative(self, path: Union[str, Path]) -> Path:
        """將絕對路徑轉換為相對路徑（相對於 base_dir）

        Args:
            path: 輸入路徑

        Returns:
            相對路徑（如果無法轉換則返回原路徑）

        Example:
            >>> resolver = PathResolver()
            >>> resolver.to_relative("/path/to/ChatGemini_SakiTool/file.mp4")
            PosixPath('file.mp4')
        """
        path_obj = Path(path)

        if not path_obj.is_absolute():
            return path_obj

        try:
            return path_obj.relative_to(self.base_dir)
        except ValueError:
            # 無法轉換為相對路徑（不在 base_dir 下）
            return path_obj


# 全域預設解析器（專案根目錄）
default_resolver = PathResolver(PROJECT_ROOT)


# ========== 便利函數（輸入路徑）==========

def resolve_input_path(path: Union[str, Path], must_exist: bool = True) -> Path:
    """解析輸入路徑（使用預設解析器）

    Args:
        path: 輸入路徑
        must_exist: 是否要求路徑必須存在

    Returns:
        解析後的絕對路徑
    """
    return default_resolver.resolve(path, must_exist)


def resolve_input_file(path: Union[str, Path], must_exist: bool = True) -> Path:
    """解析輸入檔案路徑（使用預設解析器）

    Args:
        path: 輸入檔案路徑
        must_exist: 是否要求檔案必須存在

    Returns:
        解析後的絕對路徑
    """
    return default_resolver.resolve_file(path, must_exist)


def resolve_input_dir(path: Union[str, Path], must_exist: bool = True) -> Path:
    """解析輸入目錄路徑（使用預設解析器）

    Args:
        path: 輸入目錄路徑
        must_exist: 是否要求目錄必須存在

    Returns:
        解析後的絕對路徑
    """
    return default_resolver.resolve_dir(path, must_exist)


def to_relative_path(path: Union[str, Path]) -> Path:
    """轉換為相對路徑（相對於專案根目錄）

    Args:
        path: 輸入路徑

    Returns:
        相對路徑
    """
    return default_resolver.to_relative(path)


# ==========================================
# 輸入來源管理
# ==========================================

class InputSource:
    """輸入來源枚舉"""
    USER_FILES = "user_files"           # 使用者檔案（任意位置）
    PROJECT_FILES = "project_files"     # 專案內檔案
    TEMP_FILES = "temp_files"           # 臨時檔案
    DOWNLOADED_FILES = "downloaded"     # 下載的檔案
    UPLOADED_FILES = "uploaded"         # 上傳的檔案（Gemini File API）


def get_input_base_dir(source: str) -> Path:
    """取得不同輸入來源的基準目錄

    Args:
        source: 輸入來源（InputSource 枚舉值）

    Returns:
        基準目錄 Path

    Raises:
        ValueError: 不支援的輸入來源
    """
    if source == InputSource.USER_FILES:
        return Path.home()  # 使用者主目錄

    elif source == InputSource.PROJECT_FILES:
        return PROJECT_ROOT  # 專案根目錄

    elif source == InputSource.TEMP_FILES:
        return Path("/tmp")  # 系統臨時目錄

    elif source == InputSource.DOWNLOADED_FILES:
        return Path.home() / "Downloads"  # 下載目錄

    elif source == InputSource.UPLOADED_FILES:
        # Gemini File API 上傳的檔案（無本地路徑）
        return PROJECT_ROOT  # 回傳專案根目錄作為後備

    else:
        raise ValueError(f"不支援的輸入來源: {source}")


def create_resolver_for_source(source: str) -> PathResolver:
    """為特定輸入來源建立路徑解析器

    Args:
        source: 輸入來源（InputSource 枚舉值）

    Returns:
        PathResolver 實例

    Example:
        >>> resolver = create_resolver_for_source(InputSource.DOWNLOADED_FILES)
        >>> video_path = resolver.resolve("video.mp4")
        PosixPath('/Users/username/Downloads/video.mp4')
    """
    base_dir = get_input_base_dir(source)
    return PathResolver(base_dir)


# ==========================================
# 測試與驗證
# ==========================================

def test_path_manager():
    """測試路徑管理工具"""
    print("=" * 60)
    print("路徑管理工具測試")
    print("=" * 60)

    # ========== 測試輸出路徑 ==========
    print("\n【測試 1】輸出路徑管理")
    print("-" * 60)

    print("\n1. 基礎輸出目錄:")
    for category in ['chat_logs', 'code_logs', 'diagnostics', 'system_tool', 'cache']:
        dir_path = get_output_dir(category, create=False)
        print(f"  {category:15s}: {dir_path}")

    print("\n2. 媒體輸出目錄:")
    for category in ['videos', 'images', 'audio']:
        dir_path = get_output_dir(category, create=False)
        print(f"  {category:15s}: {dir_path}")

    print("\n3. 子目錄範例:")
    examples = [
        ('videos', 'veo'),
        ('images', 'imagen'),
        ('cache', 'api_cache'),
        ('diagnostics', 'recovery'),
    ]
    for category, subdir in examples:
        dir_path = get_output_dir(category, subdir, create=False)
        print(f"  {category}/{subdir:15s}: {dir_path}")

    # ========== 測試輸入路徑 ==========
    print("\n【測試 2】輸入路徑解析")
    print("-" * 60)

    # 建立測試檔案
    test_file = PROJECT_ROOT / "test_file.txt"
    test_file.write_text("test")

    print("\n1. 絕對路徑:")
    abs_path = str(test_file)
    resolved = resolve_input_path(abs_path)
    print(f"  輸入: {abs_path}")
    print(f"  解析: {resolved}")

    print("\n2. 相對路徑:")
    rel_path = "test_file.txt"
    resolved = resolve_input_path(rel_path)
    print(f"  輸入: {rel_path}")
    print(f"  解析: {resolved}")

    print("\n3. 路徑轉換:")
    converted = to_relative_path(test_file)
    print(f"  絕對: {test_file}")
    print(f"  相對: {converted}")

    # 清理測試檔案
    test_file.unlink()

    # ========== 測試輸入來源 ==========
    print("\n【測試 3】輸入來源管理")
    print("-" * 60)

    sources = [
        InputSource.USER_FILES,
        InputSource.PROJECT_FILES,
        InputSource.TEMP_FILES,
        InputSource.DOWNLOADED_FILES,
    ]

    for source in sources:
        base_dir = get_input_base_dir(source)
        print(f"  {source:20s}: {base_dir}")

    # ========== 測試 PathResolver ==========
    print("\n【測試 4】PathResolver 類別")
    print("-" * 60)

    # 建立測試檔案
    test_file = PROJECT_ROOT / "test_file.txt"
    test_file.write_text("test")

    resolver = PathResolver(PROJECT_ROOT)

    print("\n1. 解析檔案:")
    try:
        resolved = resolver.resolve_file("test_file.txt")
        print(f"  ✓ 成功: {resolved}")
    except Exception as e:
        print(f"  ✗ 失敗: {e}")

    print("\n2. 解析目錄:")
    try:
        resolved = resolver.resolve_dir(".")
        print(f"  ✓ 成功: {resolved}")
    except Exception as e:
        print(f"  ✗ 失敗: {e}")

    print("\n3. 不存在的檔案（should fail）:")
    try:
        resolved = resolver.resolve_file("nonexistent.txt")
        print(f"  ✗ 應該失敗但成功了: {resolved}")
    except FileNotFoundError as e:
        print(f"  ✓ 正確失敗: {type(e).__name__}")

    print("\n4. 不存在的檔案（不要求存在）:")
    try:
        resolved = resolver.resolve("nonexistent.txt", must_exist=False)
        print(f"  ✓ 成功: {resolved}")
    except Exception as e:
        print(f"  ✗ 失敗: {e}")

    # 清理測試檔案
    test_file.unlink()

    print("\n" + "=" * 60)
    print("✓ 所有測試完成")
    print("=" * 60)


if __name__ == "__main__":
    test_path_manager()
