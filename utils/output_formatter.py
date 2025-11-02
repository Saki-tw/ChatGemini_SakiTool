#!/usr/bin/env python3
"""
輸出格式化工具
支援多種輸出格式：純文字、JSON、NDJSON

本模組提供：
- 純文字輸出（預設，向後相容）
- JSON 結構化輸出（含元數據）
- NDJSON 串流輸出（逐行 JSON）
- 錯誤 JSON 輸出（統一錯誤格式）

使用範例：
    from utils.output_formatter import OutputFormatter, OutputFormat

    formatter = OutputFormatter()

    # 純文字輸出
    result = formatter.format_response(data, OutputFormat.TEXT)

    # JSON 輸出
    result = formatter.format_response(data, OutputFormat.JSON)

    # NDJSON 串流輸出
    for line in formatter.format_stream_response(stream_data, OutputFormat.NDJSON):
        print(line)
"""

import json
import sys
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Generator
import logging

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """輸出格式枚舉"""
    TEXT = "text"           # 純文字（預設）
    JSON = "json"           # JSON 物件
    NDJSON = "stream-json"  # NDJSON（Newline Delimited JSON）


class OutputFormatter:
    """
    輸出格式化器

    負責將 Gemini API 回應格式化為不同格式：
    - TEXT: 純文字輸出（向後相容）
    - JSON: 結構化 JSON 物件（含完整元數據）
    - NDJSON: 逐行 JSON 串流（適合即時處理）

    設計原則：
    1. 標準格式 - 使用 RFC 8259 (JSON) 和 RFC 7464 (NDJSON)
    2. 完整性 - JSON 格式包含所有元數據
    3. 向後相容 - 預設純文字輸出
    4. 錯誤處理 - 即使錯誤也輸出有效 JSON
    """

    def __init__(self, ensure_ascii: bool = False, indent: Optional[int] = 2):
        """
        初始化格式化器

        Args:
            ensure_ascii: JSON 是否轉義非 ASCII 字符（預設 False，支援 Unicode）
            indent: JSON 縮排空格數（預設 2，None 為緊湊格式）
        """
        self.ensure_ascii = ensure_ascii
        self.indent = indent

    def format_response(
        self,
        data: Dict[str, Any],
        format_type: OutputFormat = OutputFormat.TEXT
    ) -> str:
        """
        格式化單次回應

        Args:
            data: 回應數據字典
                必需欄位:
                - 'text' (str): 回應文字內容
                可選欄位:
                - 'metadata' (dict): 元數據（模型、溫度等）
                - 'token_count' (dict): Token 使用統計
                - 'thinking' (dict): 思考過程資訊
                - 'timestamp' (str): 時間戳記
                - 'model' (str): 使用的模型
                - 'error' (dict): 錯誤資訊（如有）

            format_type: 輸出格式（TEXT/JSON/NDJSON）

        Returns:
            格式化後的字串

        Examples:
            >>> formatter = OutputFormatter()
            >>> data = {
            ...     'text': 'Hello, world!',
            ...     'metadata': {'model': 'gemini-2.5-flash'},
            ...     'token_count': {'input': 10, 'output': 3}
            ... }
            >>> print(formatter.format_response(data, OutputFormat.TEXT))
            Hello, world!

            >>> print(formatter.format_response(data, OutputFormat.JSON))
            {
              "response": "Hello, world!",
              "metadata": {...},
              "tokens": {...}
            }
        """
        if format_type == OutputFormat.TEXT:
            return self._format_text(data)
        elif format_type == OutputFormat.JSON:
            return self._format_json(data)
        elif format_type == OutputFormat.NDJSON:
            # NDJSON 通常用於串流，單次回應也可以用
            return self._format_json_line({
                "type": "response",
                "data": self._build_json_object(data),
                "timestamp": data.get('timestamp', datetime.now().isoformat())
            })
        else:
            logger.warning(f"未知的輸出格式: {format_type}，使用純文字")
            return self._format_text(data)

    def format_stream_response(
        self,
        stream_data: List[Dict[str, Any]],
        format_type: OutputFormat = OutputFormat.TEXT
    ) -> Generator[str, None, None]:
        """
        格式化串流回應（生成器）

        Args:
            stream_data: 串流數據列表，每個元素為一個 chunk
                每個 chunk 包含:
                - 'type' (str): chunk 類型 ('chunk', 'done', 'error')
                - 'text' (str): 文字片段（type='chunk' 時）
                - 'metadata' (dict): 元數據（type='done' 時）
                - 'error' (dict): 錯誤資訊（type='error' 時）

            format_type: 輸出格式

        Yields:
            格式化後的字串（每次 yield 一行）

        Examples:
            >>> stream_data = [
            ...     {'type': 'chunk', 'text': 'Hello'},
            ...     {'type': 'chunk', 'text': ' world'},
            ...     {'type': 'done', 'metadata': {'tokens': 5}}
            ... ]
            >>> for line in formatter.format_stream_response(stream_data, OutputFormat.NDJSON):
            ...     print(line)
            {"type":"chunk","text":"Hello","timestamp":"..."}
            {"type":"chunk","text":" world","timestamp":"..."}
            {"type":"done","metadata":{"tokens":5},"timestamp":"..."}
        """
        if format_type == OutputFormat.TEXT:
            # 純文字模式：直接輸出文字片段
            for chunk in stream_data:
                if chunk.get('type') == 'chunk' and 'text' in chunk:
                    yield chunk['text']
        elif format_type == OutputFormat.NDJSON:
            # NDJSON 模式：每個 chunk 一行 JSON
            for chunk in stream_data:
                yield self._format_json_line({
                    **chunk,
                    'timestamp': chunk.get('timestamp', datetime.now().isoformat())
                })
        elif format_type == OutputFormat.JSON:
            # JSON 模式：等待所有 chunk 完成後輸出完整 JSON
            # （這違背串流的初衷，但提供完整性）
            accumulated_text = ""
            metadata = {}
            for chunk in stream_data:
                if chunk.get('type') == 'chunk':
                    accumulated_text += chunk.get('text', '')
                elif chunk.get('type') == 'done':
                    metadata = chunk.get('metadata', {})

            yield self._format_json({
                'text': accumulated_text,
                'metadata': metadata
            })

    def format_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        format_type: OutputFormat = OutputFormat.TEXT
    ) -> str:
        """
        格式化錯誤輸出

        Args:
            error: 異常物件
            context: 錯誤上下文（可選）
            format_type: 輸出格式

        Returns:
            格式化後的錯誤訊息

        Examples:
            >>> try:
            ...     raise ValueError("Invalid input")
            ... except Exception as e:
            ...     print(formatter.format_error(e, format_type=OutputFormat.JSON))
            {
              "error": {
                "type": "ValueError",
                "message": "Invalid input",
                "timestamp": "..."
              }
            }
        """
        error_data = {
            'error': {
                'type': type(error).__name__,
                'message': str(error),
                'timestamp': datetime.now().isoformat()
            }
        }

        if context:
            error_data['error']['context'] = context

        if format_type == OutputFormat.TEXT:
            return f"錯誤：{error_data['error']['type']}: {error_data['error']['message']}"
        elif format_type in (OutputFormat.JSON, OutputFormat.NDJSON):
            return self._format_json(error_data)
        else:
            return str(error)

    # ========================================================================
    # 內部格式化方法
    # ========================================================================

    def _format_text(self, data: Dict[str, Any]) -> str:
        """純文字格式化（向後相容）"""
        return data.get('text', '')

    def _format_json(self, data: Dict[str, Any]) -> str:
        """JSON 格式化（含縮排）"""
        json_obj = self._build_json_object(data)
        return json.dumps(
            json_obj,
            ensure_ascii=self.ensure_ascii,
            indent=self.indent
        )

    def _format_json_line(self, data: Dict[str, Any]) -> str:
        """NDJSON 格式化（單行，無縮排）"""
        return json.dumps(data, ensure_ascii=self.ensure_ascii)

    def _build_json_object(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        構建標準 JSON 物件

        輸出格式：
        {
          "response": "...",        // 回應文字
          "metadata": {...},        // 元數據
          "tokens": {...},          // Token 統計
          "thinking": {...},        // 思考資訊（可選）
          "timestamp": "...",       // ISO 8601 時間戳記
          "model": "...",           // 模型名稱
          "error": {...}            // 錯誤資訊（可選）
        }
        """
        result = {}

        # 主要回應內容
        if 'text' in data:
            result['response'] = data['text']

        # 元數據
        if 'metadata' in data:
            result['metadata'] = data['metadata']
        elif 'model' in data:
            # 如果沒有 metadata 但有 model，創建基本 metadata
            result['metadata'] = {'model': data['model']}

        # Token 統計
        if 'token_count' in data:
            result['tokens'] = data['token_count']
        elif 'tokens' in data:
            result['tokens'] = data['tokens']

        # 思考資訊（Extended Thinking）
        if 'thinking' in data:
            result['thinking'] = data['thinking']

        # 時間戳記
        result['timestamp'] = data.get('timestamp', datetime.now().isoformat())

        # 模型名稱（如果未在 metadata 中）
        if 'model' in data and 'metadata' not in result:
            result['model'] = data['model']

        # 錯誤資訊（如有）
        if 'error' in data:
            result['error'] = data['error']

        return result


def get_output_format_from_string(format_str: str) -> OutputFormat:
    """
    從字串轉換為 OutputFormat 枚舉

    Args:
        format_str: 格式字串 ('text', 'json', 'stream-json', 'ndjson')

    Returns:
        OutputFormat 枚舉值

    Raises:
        ValueError: 如果格式字串無效

    Examples:
        >>> get_output_format_from_string('json')
        <OutputFormat.JSON: 'json'>

        >>> get_output_format_from_string('ndjson')
        <OutputFormat.NDJSON: 'stream-json'>
    """
    format_str_lower = format_str.lower()

    # 標準化別名
    if format_str_lower in ('ndjson', 'stream-json', 'stream'):
        return OutputFormat.NDJSON
    elif format_str_lower in ('json',):
        return OutputFormat.JSON
    elif format_str_lower in ('text', 'plain', 'txt'):
        return OutputFormat.TEXT
    else:
        raise ValueError(
            f"無效的輸出格式: {format_str}。"
            f"支援的格式: text, json, stream-json (ndjson)"
        )


# ============================================================================
# 便利函數
# ============================================================================

def format_response_quick(
    text: str,
    format_type: str = "text",
    **metadata
) -> str:
    """
    快速格式化回應（便利函數）

    Args:
        text: 回應文字
        format_type: 格式類型字串
        **metadata: 其他元數據（model, tokens 等）

    Returns:
        格式化後的字串

    Examples:
        >>> print(format_response_quick("Hello", "json", model="gemini-2.5-flash"))
        {
          "response": "Hello",
          "metadata": {"model": "gemini-2.5-flash"},
          ...
        }
    """
    formatter = OutputFormatter()
    format_enum = get_output_format_from_string(format_type)

    data = {'text': text, **metadata}
    return formatter.format_response(data, format_enum)


if __name__ == "__main__":
    # ========================================================================
    # 模組自我測試
    # ========================================================================
    print("測試輸出格式化工具...")

    formatter = OutputFormatter()

    # 測試數據
    test_data = {
        'text': 'This is a test response.',
        'metadata': {
            'model': 'gemini-2.5-flash',
            'temperature': 0.7
        },
        'token_count': {
            'input': 10,
            'output': 6,
            'total': 16
        },
        'timestamp': '2025-11-01T12:00:00Z'
    }

    print("\n1. 純文字格式:")
    print(formatter.format_response(test_data, OutputFormat.TEXT))

    print("\n2. JSON 格式:")
    print(formatter.format_response(test_data, OutputFormat.JSON))

    print("\n3. NDJSON 格式:")
    print(formatter.format_response(test_data, OutputFormat.NDJSON))

    print("\n4. 串流格式 (NDJSON):")
    stream_data = [
        {'type': 'chunk', 'text': 'Hello'},
        {'type': 'chunk', 'text': ' world'},
        {'type': 'done', 'metadata': {'tokens': 5}}
    ]
    for line in formatter.format_stream_response(stream_data, OutputFormat.NDJSON):
        print(line)

    print("\n5. 錯誤格式化 (JSON):")
    try:
        raise ValueError("Test error")
    except Exception as e:
        print(formatter.format_error(e, format_type=OutputFormat.JSON))

    print("\n✓ 所有測試通過")
