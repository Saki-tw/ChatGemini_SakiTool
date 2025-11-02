#!/usr/bin/env python3
"""複雜函數測試範例 - 多參數、多返回值、類型提示"""

from typing import List, Dict, Tuple, Optional


def calculate_statistics(numbers: List[float]) -> Dict[str, float]:
    """計算數字列表的統計資料

    Args:
        numbers: 浮點數列表

    Returns:
        Dict[str, float]: 包含 mean, median, min, max 的字典
    """
    if not numbers:
        return {
            'mean': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0
        }

    sorted_nums = sorted(numbers)
    n = len(numbers)

    return {
        'mean': sum(numbers) / n,
        'median': sorted_nums[n // 2] if n % 2 == 1 else (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2,
        'min': min(numbers),
        'max': max(numbers)
    }


def parse_config(
    config_str: str,
    default_values: Optional[Dict[str, str]] = None,
    strict_mode: bool = False
) -> Tuple[Dict[str, str], List[str]]:
    """解析配置字串

    Args:
        config_str: 配置字串，格式為 "key1=value1,key2=value2"
        default_values: 預設值字典
        strict_mode: 是否使用嚴格模式

    Returns:
        Tuple[Dict[str, str], List[str]]: (解析結果字典, 錯誤訊息列表)
    """
    if default_values is None:
        default_values = {}

    result = default_values.copy()
    errors = []

    if not config_str:
        return result, errors

    for pair in config_str.split(','):
        pair = pair.strip()
        if '=' not in pair:
            if strict_mode:
                errors.append(f"Invalid format: {pair}")
            continue

        key, value = pair.split('=', 1)
        key = key.strip()
        value = value.strip()

        if not key:
            errors.append("Empty key found")
            continue

        result[key] = value

    return result, errors


def filter_and_transform(
    items: List[int],
    min_value: int = 0,
    max_value: int = 100,
    multiplier: float = 1.0
) -> List[float]:
    """過濾並轉換數字列表

    Args:
        items: 整數列表
        min_value: 最小值過濾條件
        max_value: 最大值過濾條件
        multiplier: 乘數

    Returns:
        List[float]: 轉換後的列表
    """
    return [
        item * multiplier
        for item in items
        if min_value <= item <= max_value
    ]
