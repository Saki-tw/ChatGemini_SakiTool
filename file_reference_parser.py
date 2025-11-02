#!/usr/bin/env python3
"""
檔案引用解析器 - 支援 @ 語法
File Reference Parser - Support @ Syntax

功能：
- 解析 @檔案路徑 語法
- 自動載入檔案內容至對話上下文
- 支援多檔案引用
- 安全限制（檔案大小、類型檢查）

使用範例：
    user_input = "@config.py 這個配置檔有什麼問題？"
    cleaned_input, file_contents = parse_file_references(user_input)

作者：Saki-tw with Claude Code
日期：2025-11-01
"""

import re
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import logging

# 安全限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILES_PER_QUERY = 10  # 單次查詢最多引用 10 個檔案
ALLOWED_EXTENSIONS = {
    # 程式碼
    '.py', '.js', '.ts', '.jsx', '.tsx', '.c', '.cpp', '.h', '.hpp',
    '.java', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala',
    # 配置
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.env',
    # 文檔
    '.md', '.markdown', '.rst', '.txt', '.csv',
    # 腳本
    '.sh', '.bash', '.zsh', '.fish', '.ps1',
    # 資料庫/API
    '.sql', '.graphql', '.proto',
    # 前端
    '.html', '.css', '.scss', '.sass', '.less', '.vue',
}

# 日誌設置
logger = logging.getLogger(__name__)


@dataclass
class FileReference:
    """檔案引用資料結構"""
    path: str                # 原始路徑
    resolved_path: Path      # 解析後的絕對路徑
    content: Optional[str]   # 檔案內容
    error: Optional[str]     # 錯誤訊息
    size: int = 0            # 檔案大小（bytes）
    encoding: str = 'utf-8'  # 編碼


@dataclass
class ParseResult:
    """解析結果"""
    cleaned_input: str              # 清理後的輸入（移除 @ 引用）
    file_references: List[FileReference]  # 檔案引用列表
    formatted_content: str          # 格式化的檔案內容（用於注入 prompt）
    has_errors: bool                # 是否有錯誤
    error_messages: List[str]       # 錯誤訊息列表


class FileReferenceParser:
    """檔案引用解析器"""

    def __init__(self,
                 max_file_size: int = MAX_FILE_SIZE,
                 max_files: int = MAX_FILES_PER_QUERY,
                 allowed_extensions: set = ALLOWED_EXTENSIONS):
        """
        初始化解析器

        Args:
            max_file_size: 單一檔案大小限制（bytes）
            max_files: 單次查詢檔案數量限制
            allowed_extensions: 允許的檔案副檔名集合
        """
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.allowed_extensions = allowed_extensions

        # @ 語法正則表達式
        # 匹配 @檔案路徑（支援相對路徑、絕對路徑、空格路徑）
        self.pattern = re.compile(
            r'@(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))'
        )

    def parse(self, user_input: str, working_dir: Optional[str] = None) -> ParseResult:
        """
        解析用戶輸入中的 @ 檔案引用

        Args:
            user_input: 用戶輸入文本
            working_dir: 工作目錄（預設為當前目錄）

        Returns:
            ParseResult: 解析結果
        """
        if working_dir is None:
            working_dir = os.getcwd()

        # 提取所有 @ 引用
        matches = self.pattern.findall(user_input)

        if not matches:
            # 沒有檔案引用，直接返回
            return ParseResult(
                cleaned_input=user_input,
                file_references=[],
                formatted_content="",
                has_errors=False,
                error_messages=[]
            )

        # 限制檔案數量
        if len(matches) > self.max_files:
            return ParseResult(
                cleaned_input=user_input,
                file_references=[],
                formatted_content="",
                has_errors=True,
                error_messages=[
                    f"❌ 檔案引用數量超過限制（最多 {self.max_files} 個，發現 {len(matches)} 個）"
                ]
            )

        file_references = []
        error_messages = []

        for match in matches:
            # 提取檔案路徑（處理引號和無引號的情況）
            file_path = match[0] or match[1] or match[2]

            # 解析檔案
            file_ref = self._parse_single_file(file_path, working_dir)
            file_references.append(file_ref)

            if file_ref.error:
                error_messages.append(file_ref.error)

        # 移除輸入中的 @ 引用
        cleaned_input = self.pattern.sub('', user_input).strip()

        # 格式化檔案內容
        formatted_content = self._format_file_contents(file_references)

        return ParseResult(
            cleaned_input=cleaned_input,
            file_references=file_references,
            formatted_content=formatted_content,
            has_errors=len(error_messages) > 0,
            error_messages=error_messages
        )

    def _parse_single_file(self, file_path: str, working_dir: str) -> FileReference:
        """
        解析單一檔案

        Args:
            file_path: 檔案路徑
            working_dir: 工作目錄

        Returns:
            FileReference: 檔案引用物件
        """
        # 處理路徑
        path_obj = Path(file_path)

        # 如果是相對路徑，解析為絕對路徑
        if not path_obj.is_absolute():
            path_obj = Path(working_dir) / path_obj

        try:
            # 解析符號連結
            resolved_path = path_obj.resolve()
        except Exception as e:
            return FileReference(
                path=file_path,
                resolved_path=path_obj,
                content=None,
                error=f"❌ 路徑解析失敗 [{file_path}]: {e}",
                size=0
            )

        # 檢查檔案是否存在
        if not resolved_path.exists():
            return FileReference(
                path=file_path,
                resolved_path=resolved_path,
                content=None,
                error=f"❌ 檔案不存在: {file_path}",
                size=0
            )

        # 檢查是否為檔案（不是目錄）
        if not resolved_path.is_file():
            return FileReference(
                path=file_path,
                resolved_path=resolved_path,
                content=None,
                error=f"❌ 不是檔案（可能是目錄）: {file_path}",
                size=0
            )

        # 檢查副檔名
        if resolved_path.suffix.lower() not in self.allowed_extensions:
            return FileReference(
                path=file_path,
                resolved_path=resolved_path,
                content=None,
                error=f"❌ 不支援的檔案類型 [{resolved_path.suffix}]: {file_path}",
                size=0
            )

        # 檢查檔案大小
        file_size = resolved_path.stat().st_size
        if file_size > self.max_file_size:
            size_mb = file_size / (1024 * 1024)
            limit_mb = self.max_file_size / (1024 * 1024)
            return FileReference(
                path=file_path,
                resolved_path=resolved_path,
                content=None,
                error=f"❌ 檔案過大 ({size_mb:.2f} MB > {limit_mb:.2f} MB): {file_path}",
                size=file_size
            )

        # 讀取檔案內容
        try:
            content = resolved_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # 嘗試其他編碼
            try:
                content = resolved_path.read_text(encoding='latin-1')
                encoding = 'latin-1'
            except Exception as e:
                return FileReference(
                    path=file_path,
                    resolved_path=resolved_path,
                    content=None,
                    error=f"❌ 讀取檔案失敗（編碼問題）: {file_path}",
                    size=file_size
                )
        except Exception as e:
            return FileReference(
                path=file_path,
                resolved_path=resolved_path,
                content=None,
                error=f"❌ 讀取檔案失敗 [{file_path}]: {e}",
                size=file_size
            )

        # 成功讀取
        logger.info(f"成功載入檔案: {file_path} ({file_size} bytes)")
        return FileReference(
            path=file_path,
            resolved_path=resolved_path,
            content=content,
            error=None,
            size=file_size,
            encoding='utf-8'
        )

    def _format_file_contents(self, file_references: List[FileReference]) -> str:
        """
        格式化檔案內容為 Markdown 代碼區塊

        Args:
            file_references: 檔案引用列表

        Returns:
            str: 格式化的內容
        """
        if not file_references:
            return ""

        formatted_parts = []

        for ref in file_references:
            if ref.content is None:
                # 跳過讀取失敗的檔案
                continue

            # 獲取語法高亮語言
            language = self._get_language_for_highlight(ref.resolved_path.suffix)

            # 格式化為 Markdown 代碼區塊
            formatted = f"""
檔案: `{ref.path}` ({ref.size} bytes)

```{language}
{ref.content}
```
"""
            formatted_parts.append(formatted.strip())

        if not formatted_parts:
            return ""

        # 組合所有檔案內容
        header = "---\n**📁 引用的檔案內容：**\n"
        footer = "\n---\n"

        return header + "\n\n".join(formatted_parts) + footer

    def _get_language_for_highlight(self, suffix: str) -> str:
        """
        根據副檔名獲取語法高亮語言

        Args:
            suffix: 副檔名（例如 .py）

        Returns:
            str: 語言名稱
        """
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.fish': 'fish',
            '.ps1': 'powershell',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.sql': 'sql',
            '.md': 'markdown',
            '.markdown': 'markdown',
        }

        return language_map.get(suffix.lower(), '')


# ==========================================
# 便捷函數（向後兼容）
# ==========================================

_default_parser = None


def get_default_parser() -> FileReferenceParser:
    """獲取預設解析器（單例模式）"""
    global _default_parser
    if _default_parser is None:
        _default_parser = FileReferenceParser()
    return _default_parser


def parse_file_references(user_input: str, working_dir: Optional[str] = None) -> Tuple[str, str, bool, List[str]]:
    """
    解析檔案引用（便捷函數）

    Args:
        user_input: 用戶輸入
        working_dir: 工作目錄

    Returns:
        Tuple[str, str, bool, List[str]]: (清理後的輸入, 格式化的檔案內容, 是否有錯誤, 錯誤訊息列表)
    """
    parser = get_default_parser()
    result = parser.parse(user_input, working_dir)

    return (
        result.cleaned_input,
        result.formatted_content,
        result.has_errors,
        result.error_messages
    )


# ==========================================
# 測試程式碼
# ==========================================

if __name__ == "__main__":
    # 測試用例
    test_cases = [
        "@config.py 這個配置檔有什麼問題？",
        "@file1.py @file2.js 比較這兩個檔案",
        '@"path with spaces/file.py" 檢查這個檔案',
        "沒有檔案引用的普通輸入",
        "@nonexistent.txt 不存在的檔案",
    ]

    parser = FileReferenceParser()

    for i, test_input in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"測試案例 {i}: {test_input}")
        print(f"{'='*60}")

        result = parser.parse(test_input)

        print(f"\n清理後的輸入: {result.cleaned_input}")
        print(f"檔案引用數量: {len(result.file_references)}")

        if result.has_errors:
            print(f"\n錯誤訊息:")
            for error in result.error_messages:
                print(f"  {error}")

        if result.formatted_content:
            print(f"\n格式化內容:")
            print(result.formatted_content)

        for ref in result.file_references:
            print(f"\n檔案: {ref.path}")
            print(f"  解析路徑: {ref.resolved_path}")
            print(f"  大小: {ref.size} bytes")
            if ref.error:
                print(f"  錯誤: {ref.error}")
            else:
                print(f"  狀態: ✅ 成功載入")
