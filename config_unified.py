#!/usr/bin/env python3
"""
ChatGemini_SakiTool - 統一配置管理系統
Unified Configuration Management System

設計理念：
1. 三層配置架構（Tier 1 → Tier 2 → Tier 3）
2. 零絕對路徑（所有路徑動態計算）
3. 零配置啟動（智能預設值）
4. 環境變數完整支援（20+ 變數）
5. 配置驗證與類型轉換

三層架構：
- Tier 1: config.py（系統預設，最低優先級）
- Tier 2: 使用者配置 JSON（~/.cache/codegemini/user_config.json）
- Tier 3: 環境變數（最高優先級）

優先級: Tier 3 > Tier 2 > Tier 1

Author: Claude Code (Sonnet 4.5)
Created: 2025-10-24
Version: 2.0.0 (重大改版：零絕對路徑設計)
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ==========================================
# 動態路徑管理（零絕對路徑）
# ==========================================

class DynamicPathManager:
    """動態路徑管理器

    設計原則：
    - ❌ 不使用任何硬編碼絕對路徑
    - ✅ 所有路徑基於 PROJECT_ROOT 動態計算
    - ✅ 確保跨機器/環境可移植性
    - ✅ 零絕對路徑設計
    """

    # 專案根目錄（動態計算，基於當前檔案位置）
    PROJECT_ROOT = Path(__file__).parent

    # 使用者配置目錄（動態計算，基於使用者 HOME）
    USER_CACHE_DIR = Path.home() / ".cache" / "codegemini"

    @classmethod
    def get_project_root(cls) -> Path:
        """取得專案根目錄（動態）

        Returns:
            專案根目錄 Path 物件
        """
        return cls.PROJECT_ROOT

    @classmethod
    def get_user_config_path(cls) -> Path:
        """取得使用者配置檔案路徑（動態）

        Returns:
            使用者配置檔案 Path 物件
        """
        config_path = cls.USER_CACHE_DIR / "user_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return config_path

    @classmethod
    def get_output_dir(cls, subdir: str = "output") -> Path:
        """取得輸出目錄（動態，相對於專案根目錄）

        Args:
            subdir: 子目錄名稱

        Returns:
            輸出目錄 Path 物件
        """
        output_path = cls.PROJECT_ROOT / subdir
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    @classmethod
    def get_cache_dir(cls, subdir: str = "cache") -> Path:
        """取得快取目錄（動態，基於使用者 CACHE）

        Args:
            subdir: 子目錄名稱

        Returns:
            快取目錄 Path 物件
        """
        cache_path = cls.USER_CACHE_DIR / subdir
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path


# ==========================================
# 環境變數映射與類型轉換
# ==========================================

class EnvironmentVariableManager:
    """環境變數管理器

    功能：
    - 支援 20+ 環境變數
    - 自動類型轉換（str → int/float/bool）
    - 錯誤處理與驗證
    """

    # 環境變數映射表（變數名 → (配置鍵, 類型)）
    ENV_VAR_MAPPING = {
        # ========== API 設定 ==========
        'GEMINI_API_KEY': ('GEMINI_API_KEY', str),
        'DEFAULT_MODEL': ('DEFAULT_MODEL', str),
        'MAX_CONTEXT_TOKENS': ('MAX_CONTEXT_TOKENS', int),

        # ========== 快取設定 ==========
        'AUTO_CACHE_ENABLED': ('AUTO_CACHE_ENABLED', bool),
        'AUTO_CACHE_THRESHOLD': ('AUTO_CACHE_THRESHOLD', int),
        'AUTO_CACHE_MODE': ('AUTO_CACHE_MODE', str),
        'CACHE_TTL_HOURS': ('CACHE_TTL_HOURS', int),

        # ========== 記憶體管理 ==========
        'MAX_CONVERSATION_HISTORY': ('MAX_CONVERSATION_HISTORY', int),
        'MEMORY_WARNING_THRESHOLD_GB': ('MEMORY_WARNING_THRESHOLD_GB', float),
        'MEMORY_AUTO_CLEANUP': ('MEMORY_AUTO_CLEANUP', bool),
        'UNLIMITED_MEMORY_MODE': ('UNLIMITED_MEMORY_MODE', bool),

        # ========== 工具管理 ==========
        'AUTO_TOOL_ENABLED': ('AUTO_TOOL_ENABLED', bool),
        'AUTO_TOOL_UNLOAD_TIMEOUT': ('AUTO_TOOL_UNLOAD_TIMEOUT', int),
        'SHOW_TOOL_LOAD_MESSAGE': ('SHOW_TOOL_LOAD_MESSAGE', bool),

        # ========== 搜尋引擎 ==========
        'SEARCH_ENGINE': ('SEARCH_ENGINE', str),
        'SEARCH_API_KEY': ('SEARCH_API_KEY', str),

        # ========== 網頁抓取 ==========
        'WEB_FETCH_TIMEOUT': ('WEB_FETCH_TIMEOUT', int),
        'WEB_FETCH_CACHE_TTL': ('WEB_FETCH_CACHE_TTL', int),

        # ========== 翻譯設定 ==========
        'TRANSLATION_ON_STARTUP': ('TRANSLATION_ON_STARTUP', bool),

        # ========== 計價設定 ==========
        'USD_TO_TWD': ('USD_TO_TWD', float),

        # ========== Embedding ==========
        'EMBEDDING_ENABLE_ON_STARTUP': ('EMBEDDING_ENABLE_ON_STARTUP', bool),
        'EMBEDDING_AUTO_SAVE_CONVERSATIONS': ('EMBEDDING_AUTO_SAVE_CONVERSATIONS', bool),
        'EMBEDDING_VECTOR_DB_PATH': ('EMBEDDING_VECTOR_DB_PATH', str),

        # ========== 思考模式 ==========
        'SHOW_THINKING_PROCESS': ('SHOW_THINKING_PROCESS', bool),
        'MAX_THINKING_BUDGET': ('MAX_THINKING_BUDGET', int),
    }

    @classmethod
    def get_from_env(cls, env_var: str) -> Optional[Any]:
        """從環境變數讀取配置

        Args:
            env_var: 環境變數名稱

        Returns:
            轉換後的值（根據類型），若不存在返回 None
        """
        if env_var not in cls.ENV_VAR_MAPPING:
            return None

        config_key, var_type = cls.ENV_VAR_MAPPING[env_var]
        value = os.environ.get(env_var)

        if value is None:
            return None

        try:
            return cls._convert_type(value, var_type)
        except (ValueError, TypeError) as e:
            logger.warning(f"環境變數 {env_var} 類型轉換失敗: {e}，使用預設值")
            return None

    @classmethod
    def _convert_type(cls, value: str, var_type: type) -> Any:
        """類型轉換

        Args:
            value: 字串值
            var_type: 目標類型

        Returns:
            轉換後的值
        """
        if var_type == bool:
            # 布林值特殊處理
            return value.lower() in ('true', '1', 'yes', 'on')
        elif var_type == int:
            return int(value)
        elif var_type == float:
            return float(value)
        else:
            return value

    @classmethod
    def get_all_env_overrides(cls) -> Dict[str, Any]:
        """取得所有環境變數覆寫

        Returns:
            配置字典（僅包含已設定的環境變數）
        """
        overrides = {}
        for env_var in cls.ENV_VAR_MAPPING.keys():
            value = cls.get_from_env(env_var)
            if value is not None:
                config_key = cls.ENV_VAR_MAPPING[env_var][0]
                overrides[config_key] = value
        return overrides


# ==========================================
# 統一配置管理器
# ==========================================

class UnifiedConfigManager:
    """統一配置管理器

    三層配置架構：
    - Tier 1: config.py（系統預設）
    - Tier 2: user_config.json（使用者配置）
    - Tier 3: 環境變數（最高優先級）

    優先級: Tier 3 > Tier 2 > Tier 1

    設計特點：
    - 零絕對路徑（所有路徑動態計算）
    - 零配置啟動（智能預設值）
    - 環境變數完整支援（20+ 變數）
    """

    def __init__(self):
        """初始化配置管理器"""
        self.path_manager = DynamicPathManager()
        self.env_manager = EnvironmentVariableManager()

        # 載入 Tier 1: config.py（系統預設）
        self._tier1_config = self._load_tier1_config()

        # 載入 Tier 2: user_config.json（使用者配置）
        self._tier2_config = self._load_tier2_config()

        # 載入 Tier 3: 環境變數（最高優先級）
        self._tier3_config = self.env_manager.get_all_env_overrides()

        logger.info("✅ 統一配置管理器已初始化（三層架構）")
        logger.debug(f"  Tier 1 (系統預設): {len(self._tier1_config)} 項")
        logger.debug(f"  Tier 2 (使用者配置): {len(self._tier2_config)} 項")
        logger.debug(f"  Tier 3 (環境變數): {len(self._tier3_config)} 項")

    def _load_tier1_config(self) -> Dict[str, Any]:
        """載入 Tier 1: config.py（系統預設）

        Returns:
            配置字典
        """
        try:
            import config as config_module

            # 提取所有大寫變數（公開配置）
            tier1 = {}
            for key in dir(config_module):
                if key.isupper() and not key.startswith('_'):
                    tier1[key] = getattr(config_module, key)

            logger.info(f"✓ 載入 Tier 1（系統預設）: {len(tier1)} 項")
            return tier1
        except ImportError:
            logger.warning("config.py 未找到，使用空預設配置")
            return {}

    def _load_tier2_config(self) -> Dict[str, Any]:
        """載入 Tier 2: user_config.json（使用者配置）

        Returns:
            配置字典
        """
        config_path = self.path_manager.get_user_config_path()

        if not config_path.exists():
            logger.debug("使用者配置不存在，使用空配置")
            return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                tier2 = json.load(f)
            logger.info(f"✓ 載入 Tier 2（使用者配置）: {config_path}")
            return tier2
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"使用者配置載入失敗: {e}，使用空配置")
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """取得配置值（三層合併）

        Args:
            key: 配置鍵
            default: 預設值

        Returns:
            配置值（優先級: Tier 3 > Tier 2 > Tier 1 > default）
        """
        # Tier 3: 環境變數（最高優先級）
        if key in self._tier3_config:
            return self._tier3_config[key]

        # Tier 2: 使用者配置
        if key in self._tier2_config:
            return self._tier2_config[key]

        # Tier 1: 系統預設
        if key in self._tier1_config:
            return self._tier1_config[key]

        # 預設值
        return default

    def set_user_config(self, key: str, value: Any) -> bool:
        """設定使用者配置（Tier 2）

        Args:
            key: 配置鍵
            value: 配置值

        Returns:
            是否成功
        """
        self._tier2_config[key] = value
        return self._save_tier2_config()

    def _save_tier2_config(self) -> bool:
        """儲存使用者配置

        Returns:
            是否成功
        """
        config_path = self.path_manager.get_user_config_path()

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._tier2_config, f, ensure_ascii=False, indent=2)
            logger.info(f"✓ 儲存使用者配置: {config_path}")
            return True
        except IOError as e:
            logger.error(f"使用者配置儲存失敗: {e}")
            return False

    def get_all_config(self) -> Dict[str, Any]:
        """取得完整配置（三層合併）

        Returns:
            完整配置字典
        """
        # 合併三層配置（優先級: Tier 3 > Tier 2 > Tier 1）
        merged = {}
        merged.update(self._tier1_config)  # Tier 1
        merged.update(self._tier2_config)  # Tier 2
        merged.update(self._tier3_config)  # Tier 3
        return merged

    def get_config_source(self, key: str) -> str:
        """查詢配置來源

        Args:
            key: 配置鍵

        Returns:
            配置來源（"環境變數" / "使用者配置" / "系統預設" / "未設定"）
        """
        if key in self._tier3_config:
            return "環境變數 (Tier 3)"
        elif key in self._tier2_config:
            return "使用者配置 (Tier 2)"
        elif key in self._tier1_config:
            return "系統預設 (Tier 1)"
        else:
            return "未設定"

    def reset_user_config(self) -> bool:
        """重置使用者配置（清空 Tier 2）

        Returns:
            是否成功
        """
        self._tier2_config = {}
        return self._save_tier2_config()

    # ==========================================
    # 便利屬性（向後兼容）
    # ==========================================

    @property
    def MODULES(self) -> Dict:
        """模組啟用設定"""
        return self.get('MODULES', {})

    @property
    def DEFAULT_MODEL(self) -> str:
        """預設模型"""
        return self.get('DEFAULT_MODEL', 'gemini-2.5-flash')

    @property
    def AUTO_CACHE_ENABLED(self) -> bool:
        """是否啟用自動快取"""
        return self.get('AUTO_CACHE_ENABLED', True)

    @property
    def AUTO_CACHE_THRESHOLD(self) -> int:
        """自動快取門檻"""
        return self.get('AUTO_CACHE_THRESHOLD', 5000)

    @property
    def CACHE_TTL_HOURS(self) -> int:
        """快取有效期（小時）"""
        return self.get('CACHE_TTL_HOURS', 1)

    @property
    def USD_TO_TWD(self) -> float:
        """美元轉新台幣匯率"""
        return self.get('USD_TO_TWD', 31.0)

    @property
    def MAX_CONVERSATION_HISTORY(self) -> int:
        """最大對話歷史"""
        return self.get('MAX_CONVERSATION_HISTORY', 100)

    @property
    def UNLIMITED_MEMORY_MODE(self) -> bool:
        """無限記憶體模式"""
        return self.get('UNLIMITED_MEMORY_MODE', False)

    @property
    def TRANSLATION_ON_STARTUP(self) -> bool:
        """啟動時是否啟用翻譯"""
        return self.get('TRANSLATION_ON_STARTUP', True)

    @property
    def PROJECT_ROOT(self) -> Path:
        """專案根目錄（動態路徑）"""
        return self.path_manager.get_project_root()

    @property
    def OUTPUT_DIRS(self) -> Dict[str, Path]:
        """輸出目錄字典（動態路徑）"""
        return self.get('OUTPUT_DIRS', {})

    @property
    def EMBEDDING_ENABLE_ON_STARTUP(self) -> bool:
        """啟動時是否啟用 Embedding"""
        return self.get('EMBEDDING_ENABLE_ON_STARTUP', False)


# ==========================================
# 全局實例（單例）
# ==========================================

# 創建全局統一配置管理器
unified_config = UnifiedConfigManager()

# 向後兼容：導出常用配置
MODULES = unified_config.MODULES
DEFAULT_MODEL = unified_config.DEFAULT_MODEL
AUTO_CACHE_ENABLED = unified_config.AUTO_CACHE_ENABLED
AUTO_CACHE_THRESHOLD = unified_config.AUTO_CACHE_THRESHOLD
CACHE_TTL_HOURS = unified_config.CACHE_TTL_HOURS
USD_TO_TWD = unified_config.USD_TO_TWD
PROJECT_ROOT = unified_config.PROJECT_ROOT
MAX_CONVERSATION_HISTORY = unified_config.MAX_CONVERSATION_HISTORY
UNLIMITED_MEMORY_MODE = unified_config.UNLIMITED_MEMORY_MODE
TRANSLATION_ON_STARTUP = unified_config.TRANSLATION_ON_STARTUP
EMBEDDING_ENABLE_ON_STARTUP = unified_config.EMBEDDING_ENABLE_ON_STARTUP


# ==========================================
# 測試程式
# ==========================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("\n" + "=" * 60)
    print("統一配置管理系統測試")
    print("=" * 60)

    # 測試 1: 讀取配置
    print("\n【測試 1: 讀取配置】")
    print(f"DEFAULT_MODEL: {unified_config.DEFAULT_MODEL}")
    print(f"  來源: {unified_config.get_config_source('DEFAULT_MODEL')}")

    print(f"\nAUTO_CACHE_ENABLED: {unified_config.AUTO_CACHE_ENABLED}")
    print(f"  來源: {unified_config.get_config_source('AUTO_CACHE_ENABLED')}")

    print(f"\nUSD_TO_TWD: {unified_config.USD_TO_TWD}")
    print(f"  來源: {unified_config.get_config_source('USD_TO_TWD')}")

    # 測試 2: 動態路徑（零絕對路徑）
    print("\n【測試 2: 動態路徑（零絕對路徑）】")
    print(f"專案根目錄: {unified_config.PROJECT_ROOT}")
    print(f"使用者配置: {DynamicPathManager.get_user_config_path()}")
    print(f"快取目錄: {DynamicPathManager.get_cache_dir()}")
    print(f"輸出目錄: {DynamicPathManager.get_output_dir()}")

    # 測試 3: 環境變數覆寫
    print("\n【測試 3: 環境變數覆寫】")
    print("設定環境變數: DEFAULT_MODEL=gemini-2.5-pro")
    os.environ['DEFAULT_MODEL'] = 'gemini-2.5-pro'
    test_config = UnifiedConfigManager()
    print(f"DEFAULT_MODEL (環境變數覆寫): {test_config.DEFAULT_MODEL}")
    print(f"  來源: {test_config.get_config_source('DEFAULT_MODEL')}")

    # 測試 4: 三層配置統計
    print("\n【測試 4: 三層配置統計】")
    print(f"Tier 1 (系統預設): {len(test_config._tier1_config)} 項")
    print(f"Tier 2 (使用者配置): {len(test_config._tier2_config)} 項")
    print(f"Tier 3 (環境變數): {len(test_config._tier3_config)} 項")
    print(f"合併後總計: {len(test_config.get_all_config())} 項")

    print("\n" + "=" * 60)
    print("✓ 測試完成")
    print("=" * 60 + "\n")
