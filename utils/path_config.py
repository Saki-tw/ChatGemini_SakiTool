#!/usr/bin/env python3
"""
統一路徑配置模組
提供全專案統一的輸出路徑管理

根據使用者要求：
- 所有測試垃圾、報告、log 等生成於 ~/Saki_Studio/Claude/
- 專案目錄 ChatGemini_SakiTool/ 內不應有測試輸出
"""
import os
from pathlib import Path
from typing import Optional

# ============================================================================
# 基礎目錄配置
# ============================================================================

# 基礎輸出目錄（用戶要求的統一輸出位置）
BASE_DIR = Path.home() / "Saki_Studio" / "Claude"

# 子目錄定義
REPORTS_DIR = BASE_DIR / "Reports"          # 所有報告
LOGS_DIR = BASE_DIR / "Logs"                # 所有日誌
TESTS_DIR = BASE_DIR / "Tests"              # 所有測試結果
ARCHIVE_DIR = BASE_DIR / "Archive"          # 歸檔檔案
OUTPUTS_DIR = BASE_DIR / "outputs"          # 媒體輸出

# outputs 子目錄（與 【1803】依賴性改良任務清單 一致）
VIDEOS_OUTPUT_DIR = OUTPUTS_DIR / "videos"
IMAGES_OUTPUT_DIR = OUTPUTS_DIR / "images"
CACHE_DIR = OUTPUTS_DIR / "cache"
EMBEDDINGS_DIR = OUTPUTS_DIR / "embeddings"
BATCH_DIR = OUTPUTS_DIR / "batch"
RECOVERY_DIR = OUTPUTS_DIR / "recovery"
TEMP_DIR = OUTPUTS_DIR / "temp"

# ============================================================================
# 自動建立目錄結構
# ============================================================================

def ensure_directories() -> None:
    """
    確保所有必要的目錄存在

    在模組載入時自動執行
    """
    directories = [
        REPORTS_DIR,
        LOGS_DIR,
        TESTS_DIR,
        ARCHIVE_DIR,
        OUTPUTS_DIR,
        VIDEOS_OUTPUT_DIR,
        IMAGES_OUTPUT_DIR,
        CACHE_DIR,
        EMBEDDINGS_DIR,
        BATCH_DIR,
        RECOVERY_DIR,
        TEMP_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# 模組載入時自動建立目錄
ensure_directories()


# ============================================================================
# 路徑取得函數
# ============================================================================

def get_report_path(filename: str, subdirectory: Optional[str] = None) -> Path:
    """
    取得報告檔案路徑

    Args:
        filename: 檔案名稱
        subdirectory: 子目錄（可選，例如 "Phase1-Critical"）

    Returns:
        完整路徑 Path 物件

    Examples:
        >>> get_report_path("test_report.md")
        Path('/Users/xxx/Saki_Studio/Claude/Reports/test_report.md')

        >>> get_report_path("violation.md", "Phase1-Critical")
        Path('/Users/xxx/Saki_Studio/Claude/Reports/Phase1-Critical/violation.md')
    """
    if subdirectory:
        target_dir = REPORTS_DIR / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename
    return REPORTS_DIR / filename


def get_log_path(filename: str, subdirectory: Optional[str] = None) -> Path:
    """
    取得日誌檔案路徑

    Args:
        filename: 檔案名稱
        subdirectory: 子目錄（可選，例如 "errors", "conversations"）

    Returns:
        完整路徑 Path 物件

    Examples:
        >>> get_log_path("app.log")
        Path('/Users/xxx/Saki_Studio/Claude/Logs/app.log')
    """
    if subdirectory:
        target_dir = LOGS_DIR / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename
    return LOGS_DIR / filename


def get_test_path(filename: str, subdirectory: Optional[str] = None) -> Path:
    """
    取得測試結果檔案路徑

    Args:
        filename: 檔案名稱
        subdirectory: 子目錄（可選）

    Returns:
        完整路徑 Path 物件

    Examples:
        >>> get_test_path("test_results.json")
        Path('/Users/xxx/Saki_Studio/Claude/Tests/test_results.json')
    """
    if subdirectory:
        target_dir = TESTS_DIR / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename
    return TESTS_DIR / filename


def get_archive_path(filename: str, subdirectory: Optional[str] = None) -> Path:
    """
    取得歸檔檔案路徑

    Args:
        filename: 檔案名稱
        subdirectory: 子目錄（可選，例如 "removed_modules"）

    Returns:
        完整路徑 Path 物件
    """
    if subdirectory:
        target_dir = ARCHIVE_DIR / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename
    return ARCHIVE_DIR / filename


def get_output_path(
    category: str,
    filename: str,
    subdirectory: Optional[str] = None
) -> Path:
    """
    取得媒體輸出路徑（影片、圖片等）

    Args:
        category: 類別（videos, images, cache, embeddings, batch, recovery, temp）
        filename: 檔案名稱
        subdirectory: 子目錄（可選）

    Returns:
        完整路徑 Path 物件

    Examples:
        >>> get_output_path("videos", "output.mp4", "veo")
        Path('/Users/xxx/Saki_Studio/Claude/outputs/videos/veo/output.mp4')
    """
    category_map = {
        "videos": VIDEOS_OUTPUT_DIR,
        "images": IMAGES_OUTPUT_DIR,
        "cache": CACHE_DIR,
        "embeddings": EMBEDDINGS_DIR,
        "batch": BATCH_DIR,
        "recovery": RECOVERY_DIR,
        "temp": TEMP_DIR,
    }

    if category not in category_map:
        raise ValueError(
            f"Unknown category: {category}. "
            f"Must be one of {list(category_map.keys())}"
        )

    target_dir = category_map[category]
    if subdirectory:
        target_dir = target_dir / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)

    return target_dir / filename


# ============================================================================
# 便利函數
# ============================================================================

def get_timestamped_filename(
    base_name: str,
    extension: str,
    timestamp_format: str = "%Y%m%d_%H%M%S"
) -> str:
    """
    生成帶時間戳的檔案名

    Args:
        base_name: 基礎檔案名
        extension: 副檔名（需包含點，例如 ".md"）
        timestamp_format: 時間戳格式

    Returns:
        帶時間戳的檔案名

    Examples:
        >>> get_timestamped_filename("report", ".md")
        "report_20251023_191630.md"
    """
    from datetime import datetime
    timestamp = datetime.now().strftime(timestamp_format)
    return f"{base_name}_{timestamp}{extension}"


# ============================================================================
# 向後兼容：舊路徑遷移提示
# ============================================================================

def check_old_paths() -> dict:
    """
    檢查是否存在舊的輸出路徑

    Returns:
        包含舊路徑資訊的字典
    """
    old_paths = {
        "gemini_videos": Path.home() / "gemini_videos",
        "gemini_images": Path.home() / "gemini_images",
        "saki_studio_old": Path.home() / "SakiStudio" / "ChatGemini" / "ChatLOG",
    }

    existing_old_paths = {}
    for name, path in old_paths.items():
        if path.exists():
            existing_old_paths[name] = {
                "path": str(path),
                "exists": True,
                "file_count": len(list(path.glob("*"))) if path.is_dir() else 0
            }

    return existing_old_paths


# ============================================================================
# 模組測試
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # 測試 1: 顯示所有路徑
    console.print("\n[bold bright_magenta]統一路徑配置測試[/bold bright_magenta]\n")

    table = Table(title="標準輸出路徑", show_header=True, header_style="bold bright_magenta")
    table.add_column("類別", style="bright_magenta")
    table.add_column("路徑", style="yellow")

    table.add_row("基礎目錄", str(BASE_DIR))
    table.add_row("報告", str(REPORTS_DIR))
    table.add_row("日誌", str(LOGS_DIR))
    table.add_row("測試", str(TESTS_DIR))
    table.add_row("歸檔", str(ARCHIVE_DIR))
    table.add_row("媒體輸出", str(OUTPUTS_DIR))

    console.print(table)

    # 測試 2: 測試路徑生成
    console.print("\n[bold bright_magenta]路徑生成測試[/bold bright_magenta]\n")

    test_cases = [
        ("報告", get_report_path("test.md")),
        ("報告（子目錄）", get_report_path("test.md", "Phase1")),
        ("日誌", get_log_path("app.log")),
        ("測試", get_test_path("results.json")),
        ("影片輸出", get_output_path("videos", "video.mp4", "veo")),
    ]

    for name, path in test_cases:
        console.print(f"[bright_magenta]✓[/bright_magenta] {name}: {path}")

    # 測試 3: 檢查舊路徑
    console.print("\n[bold bright_magenta]舊路徑遷移檢查[/bold bright_magenta]\n")
    old_paths = check_old_paths()

    if old_paths:
        console.print("[yellow]⚠️  發現舊輸出路徑：[/yellow]")
        for name, info in old_paths.items():
            console.print(f"  • {name}: {info['path']} ({info['file_count']} 個檔案)")
    else:
        console.print("[bright_magenta]✓ 無舊路徑[/bright_magenta]")

    console.print("\n[bright_magenta]✅ 路徑配置模組測試完成[/bright_magenta]\n")
