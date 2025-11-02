#!/usr/bin/env python3
"""有外部依賴的函數測試範例 - 需要 Mock"""

import requests
import os
from pathlib import Path
from typing import Optional, Dict


def fetch_api_data(url: str, timeout: int = 30) -> Optional[Dict]:
    """從 API 獲取資料

    Args:
        url: API 網址
        timeout: 超時秒數

    Returns:
        Optional[Dict]: API 回應資料，失敗則返回 None
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def read_config_file(file_path: str) -> Dict[str, str]:
    """讀取配置檔案

    Args:
        file_path: 配置檔案路徑

    Returns:
        Dict[str, str]: 配置字典
    """
    config = {}

    if not os.path.exists(file_path):
        return config

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

    return config


def save_to_database(data: Dict, db_connection) -> bool:
    """儲存資料到資料庫

    Args:
        data: 要儲存的資料
        db_connection: 資料庫連接物件

    Returns:
        bool: 是否成功
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute(
            "INSERT INTO data (key, value) VALUES (?, ?)",
            (data.get('key'), data.get('value'))
        )
        db_connection.commit()
        return True
    except Exception:
        return False


def process_external_service(input_data: str) -> str:
    """處理外部服務

    Args:
        input_data: 輸入資料

    Returns:
        str: 處理結果
    """
    # 模擬外部服務調用
    api_result = fetch_api_data(f"https://api.example.com/process?data={input_data}")

    if not api_result:
        return "Error: API call failed"

    # 處理結果
    processed = api_result.get('result', '')
    return f"Processed: {processed}"
