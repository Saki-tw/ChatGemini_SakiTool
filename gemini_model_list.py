#!/usr/bin/env python3
"""
Gemini 模型列表管理器
從 API 動態獲取可用模型,並快取結果
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google import genai


# 快取檔案路徑
CACHE_DIR = os.path.expanduser('~/.cache/chatgemini')
CACHE_FILE = os.path.join(CACHE_DIR, 'model_list_cache.json')

# 快取有效期（24 小時）
CACHE_EXPIRY = timedelta(hours=24)


def get_api_models(api_key: str) -> List[Dict]:
    """
    從 Gemini API 獲取可用模型列表

    Args:
        api_key: Google API 金鑰

    Returns:
        模型資訊列表
    """
    try:
        # 使用新版統一 SDK
        client = genai.Client(api_key=api_key)
        models = client.models.list()

        # 篩選出支援對話生成的模型
        model_list = []
        for model in models:
            # 新版 SDK 使用不同的屬性名稱
            model_name = model.name.replace('models/', '') if hasattr(model, 'name') else str(model)
            supported_methods = getattr(model, 'supported_generation_methods', [])

            if 'generateContent' in supported_methods:
                model_info = {
                    'name': model_name,
                    'display_name': getattr(model, 'display_name', model_name),
                    'description': getattr(model, 'description', ''),
                    'supported_methods': supported_methods,
                }
                model_list.append(model_info)

        return model_list

    except Exception as e:
        print(f"⚠️  無法從 API 獲取模型列表: {e}")
        return []


def load_cached_models() -> Optional[Dict]:
    """
    載入快取的模型列表

    Returns:
        快取資料（包含模型列表和時間戳記）或 None
    """
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)

        # 檢查快取是否過期
        cached_time = datetime.fromisoformat(cache['timestamp'])
        if datetime.now() - cached_time > CACHE_EXPIRY:
            return None

        return cache

    except Exception as e:
        print(f"⚠️  無法載入快取: {e}")
        return None


def save_models_cache(models: List[Dict]) -> None:
    """
    儲存模型列表到快取

    Args:
        models: 模型資訊列表
    """
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)

        cache = {
            'timestamp': datetime.now().isoformat(),
            'models': models
        }

        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"⚠️  無法儲存快取: {e}")


def get_models(api_key: str, force_refresh: bool = False) -> List[Dict]:
    """
    獲取模型列表（優先使用快取）

    Args:
        api_key: Google API 金鑰
        force_refresh: 是否強制重新從 API 獲取

    Returns:
        模型資訊列表
    """
    # 如果不強制刷新,先嘗試載入快取
    if not force_refresh:
        cached = load_cached_models()
        if cached:
            return cached['models']

    # 從 API 獲取最新列表
    models = get_api_models(api_key)

    # 儲存到快取
    if models:
        save_models_cache(models)

    return models


def categorize_models(models: List[Dict]) -> Dict[str, List[Dict]]:
    """
    將模型分類

    Args:
        models: 模型資訊列表

    Returns:
        分類後的模型字典
    """
    categories = {
        'gemini_30': [],      # Gemini 3.0 系列 (NEW!)
        'gemini_25': [],      # Gemini 2.5 系列
        'gemini_20': [],      # Gemini 2.0 系列
        'gemini_15': [],      # Gemini 1.5 系列
        'gemma': [],          # Gemma 系列
        'experimental': [],   # 實驗性模型
        'other': []           # 其他模型
    }

    for model in models:
        name = model['name'].lower()

        if '3.0' in name or 'gemini-3' in name or '3-0' in name:
            categories['gemini_30'].append(model)
        elif '2.5' in name or 'gemini-2-5' in name:
            categories['gemini_25'].append(model)
        elif '2.0' in name or 'gemini-2-0' in name:
            categories['gemini_20'].append(model)
        elif '1.5' in name or 'gemini-1-5' in name:
            categories['gemini_15'].append(model)
        elif 'gemma' in name:
            categories['gemma'].append(model)
        elif 'exp' in name or 'preview' in name:
            categories['experimental'].append(model)
        else:
            categories['other'].append(model)

    return categories


def get_recommended_models(models: List[Dict]) -> List[Dict]:
    """
    獲取推薦的主要模型

    Args:
        models: 完整模型列表

    Returns:
        推薦模型列表（3-5 個）
    """
    # 推薦模型的優先順序（2025-11-29 更新）
    priority_names = [
        'gemini-3-pro-preview',      # 最新最強 (2025-11-18)
        'gemini-2.5-flash',          # 性價比最高
        'gemini-2.5-pro',            # 最強推理
        'gemini-2.5-flash-lite',     # 輕量快速
        'gemini-2.0-flash',          # 穩定版
    ]

    recommended = []

    # 按優先順序查找
    for name in priority_names:
        for model in models:
            if model['name'] == name:
                recommended.append(model)
                break

    return recommended


def format_model_display(model: Dict, index: int = None) -> str:
    """
    格式化模型顯示文字

    Args:
        model: 模型資訊
        index: 選項編號（可選）

    Returns:
        格式化的顯示文字
    """
    name = model['name']

    # 生成友善的顯示名稱
    if 'gemini-3' in name and 'pro' in name:
        display = "✨ 3.0 Pro Preview（最新最強）"
    elif 'flash-lite' in name:
        display = "Flash Lite（輕量版）"
    elif 'flash' in name and '2.5' in name:
        display = "Flash（快速版）"
    elif 'pro' in name and '2.5' in name:
        display = "Pro（強大版）"
    elif 'flash' in name and '2.0' in name:
        display = "2.0 Flash"
    else:
        display = model.get('display_name', name)

    if index is not None:
        return f"[{index}] {display}"
    else:
        return display


def initialize_models(api_key: str) -> bool:
    """
    初始化模型列表（初次運行時調用）

    Args:
        api_key: Google API 金鑰

    Returns:
        是否成功初始化
    """
    print("🔄 正在從 API 獲取最新模型列表...")

    models = get_models(api_key, force_refresh=True)

    if models:
        print(f"✅ 成功獲取 {len(models)} 個可用模型")

        # 顯示推薦模型
        recommended = get_recommended_models(models)
        print(f"\n推薦模型 ({len(recommended)} 個):")
        for i, model in enumerate(recommended, 1):
            print(f"  {i}. {model['name']}")

        return True
    else:
        print("❌ 無法獲取模型列表")
        return False


# 預設的後備模型列表（當 API 無法訪問時使用）
FALLBACK_MODELS = [
    {
        'name': 'gemini-3-pro-preview',
        'display_name': 'Gemini 3.0 Pro Preview',
        'description': '最新最強的模型',
    },
    {
        'name': 'gemini-2.5-flash',
        'display_name': 'Gemini 2.5 Flash',
        'description': '快速且智慧的模型',
    },
    {
        'name': 'gemini-2.5-pro',
        'display_name': 'Gemini 2.5 Pro',
        'description': '最強大的模型',
    },
    {
        'name': 'gemini-2.5-flash-lite',
        'display_name': 'Gemini 2.5 Flash Lite',
        'description': '輕量版模型',
    },
]


class GeminiModelList:
    """
    Gemini 模型列表管理器（類別封裝版）
    提供動態模型獲取、快取管理和分類功能
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化模型管理器

        Args:
            api_key: Google API 金鑰（如果未提供,從環境變數讀取）
        """
        self.api_key = api_key or os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
        self._models_cache = None

    def get_models(self, force_refresh: bool = False) -> List[Dict]:
        """
        獲取模型列表（優先使用快取）

        Args:
            force_refresh: 是否強制重新從 API 獲取

        Returns:
            模型資訊列表
        """
        if self._models_cache and not force_refresh:
            return self._models_cache

        # 如果不強制刷新,先嘗試載入快取
        if not force_refresh:
            cached = load_cached_models()
            if cached:
                self._models_cache = cached['models']
                return self._models_cache

        # 從 API 獲取最新列表
        models = get_api_models(self.api_key)

        # 儲存到快取
        if models:
            save_models_cache(models)
            self._models_cache = models
        else:
            # 降級到後備列表
            self._models_cache = FALLBACK_MODELS

        return self._models_cache

    def update_models(self, force: bool = False) -> bool:
        """
        更新模型列表

        Args:
            force: 是否強制更新

        Returns:
            是否成功更新
        """
        try:
            models = self.get_models(force_refresh=force)
            return len(models) > 0
        except Exception as e:
            print(f"⚠️  更新模型列表失敗: {e}")
            return False

    def get_cache_info(self) -> Dict:
        """
        獲取快取資訊

        Returns:
            快取資訊字典（包含 exists、count、last_update、timestamp 等）
        """
        cached = load_cached_models()
        if cached:
            timestamp_str = cached['timestamp']
            try:
                dt = datetime.fromisoformat(timestamp_str)
                last_update = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                last_update = timestamp_str

            return {
                'exists': True,
                'count': len(cached['models']),
                'timestamp': timestamp_str,
                'last_update': last_update,
                'is_expired': False
            }

        # 檢查是否有過期快取
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                timestamp_str = cache.get('timestamp', 'unknown')
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    last_update = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    last_update = timestamp_str

                return {
                    'exists': True,
                    'count': len(cache.get('models', [])),
                    'timestamp': timestamp_str,
                    'last_update': last_update,
                    'is_expired': True
                }
            except:
                pass

        return {
            'exists': False,
            'count': 0,
            'timestamp': None,
            'last_update': None,
            'is_expired': False
        }

    def categorize_models(self, models: Optional[List[Dict]] = None) -> Dict[str, List[Dict]]:
        """
        將模型分類

        Args:
            models: 模型資訊列表（如果未提供,使用快取）

        Returns:
            分類後的模型字典
        """
        if models is None:
            models = self.get_models()

        return categorize_models(models)

    def get_recommended_models(self, models: Optional[List[Dict]] = None) -> List[Dict]:
        """
        獲取推薦的主要模型

        Args:
            models: 完整模型列表（如果未提供,使用快取）

        Returns:
            推薦模型列表（3-5 個）
        """
        if models is None:
            models = self.get_models()

        return get_recommended_models(models)

    def get_all_models(self) -> List[str]:
        """
        獲取所有模型名稱列表（用於模型選擇器）

        Returns:
            模型名稱列表
        """
        models = self.get_models()
        return [model['name'] for model in models]

    def format_model_display(self, model: Dict, index: int = None) -> str:
        """
        格式化模型顯示文字

        Args:
            model: 模型資訊
            index: 選項編號（可選）

        Returns:
            格式化的顯示文字
        """
        return format_model_display(model, index)


if __name__ == '__main__':
    """測試模組"""
    import sys

    api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')

    if not api_key:
        print("❌ 請設定 GOOGLE_API_KEY 或 GEMINI_API_KEY 環境變數")
        sys.exit(1)

    print("=" * 70)
    print("🧪 Gemini 模型列表測試")
    print("=" * 70)

    # 測試類別封裝
    print("\n測試 GeminiModelList 類別:")
    print("-" * 70)
    manager = GeminiModelList(api_key)

    # 測試獲取模型
    models = manager.get_models()
    print(f"\n總共 {len(models)} 個模型\n")

    # 測試快取資訊
    cache_info = manager.get_cache_info()
    print(f"快取資訊: {cache_info}\n")

    # 測試分類
    categories = manager.categorize_models()

    for category, model_list in categories.items():
        if model_list:
            print(f"\n{category.upper()} ({len(model_list)} 個):")
            for model in model_list[:5]:  # 只顯示前 5 個
                print(f"  - {model['name']}")
            if len(model_list) > 5:
                print(f"  ... 還有 {len(model_list) - 5} 個")

    # 測試推薦模型
    print("\n" + "=" * 70)
    print("推薦模型:")
    print("=" * 70)
    recommended = manager.get_recommended_models()
    for i, model in enumerate(recommended, 1):
        print(f"{i}. {model['name']}")
