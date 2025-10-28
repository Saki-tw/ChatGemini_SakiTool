#!/usr/bin/env python3
"""
Gemini 動態模組載入器
提供模組的動態載入、卸載與生命週期管理

核心功能:
1. 按需動態載入模組
2. 自動卸載閒置模組
3. 記憶體管理與資源釋放
4. 使用統計與效能監控
"""

import sys
import gc
import importlib
import time
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ModuleState:
    """模組狀態"""
    UNLOADED = "unloaded"      # 未載入
    LOADING = "loading"        # 載入中
    LOADED = "loaded"          # 已載入
    UNLOADING = "unloading"    # 卸載中
    ERROR = "error"            # 錯誤


class LoadedModule:
    """已載入模組的包裝類"""

    def __init__(self, module: Any, name: str):
        self.module = module
        self.name = name
        self.load_time = time.time()
        self.last_used = time.time()
        self.use_count = 0
        self.state = ModuleState.LOADED

    def mark_used(self):
        """標記模組被使用"""
        self.last_used = time.time()
        self.use_count += 1

    def idle_time(self) -> float:
        """獲取閒置時間（秒）"""
        return time.time() - self.last_used

    def __getattr__(self, name):
        """代理所有屬性訪問到實際模組"""
        self.mark_used()
        return getattr(self.module, name)


class ModuleLoader:
    """動態模組載入器

    設計理念:
    - 極簡核心：gemini_chat.py 只保留最小邏輯
    - 動態載入：模組按需載入，減少啟動時間
    - 自動卸載：閒置模組自動釋放記憶體
    - 資源優化：最大化資源使用效率
    """

    # 模組映射表（模組名 -> Python 模組路徑）
    MODULE_MAP = {
        # 原有模組
        'smart_triggers': 'gemini_smart_triggers',
        'performance': 'gemini_performance',
        'conversation_suggestion': 'gemini_conversation_suggestion',
        'performance_monitor': 'utils.performance_monitor',

        # Phase 2: 類別抽離
        'config_ui': 'gemini_config_ui',
        'cache': 'gemini_cache',
        'conversation': 'gemini_conversation',
        'logger': 'gemini_logger',
        'thinking': 'gemini_thinking',

        # Phase 3: 函數抽離
        'file_manager': 'gemini_file_manager',
        'model_selector': 'gemini_model_selector',

        # i18n 國際化系統
        'i18n': 'utils.i18n',
    }

    # 預載入模組（啟動時載入）
    PRELOAD_MODULES = [
        'logger',
        'i18n',  # i18n 應該在啟動時就載入
    ]

    # 閒置卸載時間（秒）
    IDLE_UNLOAD_TIME = 300  # 5 分鐘

    def __init__(self):
        self._loaded_modules: Dict[str, LoadedModule] = {}
        self._module_states: Dict[str, str] = {}
        self._enabled_modules: Dict[str, bool] = {}

        # 預載入核心模組
        for module_name in self.PRELOAD_MODULES:
            self._preload(module_name)

    def _preload(self, module_name: str):
        """預載入模組"""
        try:
            self.load(module_name)
            logger.info(f"✓ 預載入模組: {module_name}")
        except Exception as e:
            logger.warning(f"✗ 預載入失敗: {module_name} - {e}")

    def is_enabled(self, module_name: str) -> bool:
        """檢查模組是否啟用（從 config 讀取）

        注意：預載入模組 (PRELOAD_MODULES) 默認視為已啟用，
        因為它們是核心模組，不應受配置控制。
        """
        # 預載入模組默認啟用（核心模組，常駐記憶體）
        if module_name in self.PRELOAD_MODULES:
            return True

        if module_name not in self._enabled_modules:
            # 延遲導入 config 避免循環依賴
            try:
                import config
from utils.i18n import safe_t
                module_config = config.MODULES.get(module_name, {})
                self._enabled_modules[module_name] = module_config.get('enabled', False)
            except (ImportError, AttributeError):
                self._enabled_modules[module_name] = False

        return self._enabled_modules[module_name]

    def load(self, module_name: str, force_reload: bool = False) -> Optional[LoadedModule]:
        """動態載入模組

        Args:
            module_name: 模組名稱（簡稱，如 'smart_triggers'）
            force_reload: 是否強制重新載入

        Returns:
            LoadedModule 實例，失敗返回 None
        """
        # 如果已載入且不強制重載，直接返回
        if module_name in self._loaded_modules and not force_reload:
            loaded = self._loaded_modules[module_name]
            loaded.mark_used()
            return loaded

        # 檢查模組是否在映射表中
        if module_name not in self.MODULE_MAP:
            logger.error(f"✗ 未知模組: {module_name}")
            return None

        python_module = self.MODULE_MAP[module_name]

        try:
            self._module_states[module_name] = ModuleState.LOADING

            # 動態導入
            if force_reload and python_module in sys.modules:
                # 強制重載：先卸載再載入
                self.unload(module_name)

            module = importlib.import_module(python_module)

            # 包裝為 LoadedModule
            loaded = LoadedModule(module, module_name)
            self._loaded_modules[module_name] = loaded
            self._module_states[module_name] = ModuleState.LOADED

            logger.info(f"✓ 模組已載入: {module_name}")
            return loaded

        except ImportError as e:
            self._module_states[module_name] = ModuleState.ERROR
            logger.warning(f"✗ 模組載入失敗: {module_name} - {e}")
            return None

        except Exception as e:
            self._module_states[module_name] = ModuleState.ERROR
            logger.error(f"✗ 模組載入錯誤: {module_name} - {e}")
            return None

    def unload(self, module_name: str, force: bool = False):
        """徹底卸載模組（釋放記憶體）

        Args:
            module_name: 模組名稱
            force: 是否強制卸載（忽略使用中狀態）
        """
        if module_name not in self._loaded_modules:
            return

        loaded = self._loaded_modules[module_name]

        # 檢查是否可以卸載
        if not force and loaded.idle_time() < self.IDLE_UNLOAD_TIME:
            logger.debug(f"模組仍在活躍期，暫不卸載: {module_name}")
            return

        try:
            self._module_states[module_name] = ModuleState.UNLOADING

            # 1. 刪除模組引用
            del self._loaded_modules[module_name]

            # 2. 從 sys.modules 移除
            python_module = self.MODULE_MAP[module_name]
            if python_module in sys.modules:
                del sys.modules[python_module]

            # 3. 觸發垃圾回收
            gc.collect()

            self._module_states[module_name] = ModuleState.UNLOADED
            logger.info(f"✓ 模組已卸載: {module_name}")

        except Exception as e:
            logger.error(f"✗ 模組卸載失敗: {module_name} - {e}")

    def get(self, module_name: str) -> Optional[Any]:
        """獲取模組（自動載入）

        Args:
            module_name: 模組名稱

        Returns:
            模組實例，失敗返回 None
        """
        # 檢查是否啟用
        if not self.is_enabled(module_name):
            logger.debug(f"模組未啟用: {module_name}")
            return None

        # 自動載入
        loaded = self.load(module_name)
        return loaded.module if loaded else None

    def get_function(self, module_name: str, function_name: str) -> Optional[Callable]:
        """獲取模組中的函數

        Args:
            module_name: 模組名稱
            function_name: 函數名稱

        Returns:
            函數對象，失敗返回 None
        """
        module = self.get(module_name)
        if module is None:
            return None

        try:
            return getattr(module, function_name)
        except AttributeError:
            logger.error(f"✗ 函數不存在: {module_name}.{function_name}")
            return None

    def cleanup_idle_modules(self):
        """清理閒置模組"""
        to_unload = []

        for name, loaded in self._loaded_modules.items():
            if name in self.PRELOAD_MODULES:
                # 預載入模組不自動卸載
                continue

            if loaded.idle_time() > self.IDLE_UNLOAD_TIME:
                to_unload.append(name)

        for name in to_unload:
            self.unload(name)

    def get_stats(self) -> Dict[str, Any]:
        """獲取載入統計

        Returns:
            統計資訊字典
        """
        return {
            'loaded_count': len(self._loaded_modules),
            'loaded_modules': list(self._loaded_modules.keys()),
            'module_stats': {
                name: {
                    'use_count': loaded.use_count,
                    'idle_time': loaded.idle_time(),
                    'state': loaded.state
                }
                for name, loaded in self._loaded_modules.items()
            }
        }

    def __repr__(self):
        return f"<ModuleLoader: {len(self._loaded_modules)} modules loaded>"


# 全域單例
_module_loader = None


def get_module_loader() -> ModuleLoader:
    """獲取全域模組載入器單例"""
    global _module_loader
    if _module_loader is None:
        _module_loader = ModuleLoader()
    return _module_loader


# 便捷函數
def load_module(module_name: str) -> Optional[Any]:
    """載入模組（便捷函數）"""
    return get_module_loader().get(module_name)


def unload_module(module_name: str):
    """卸載模組（便捷函數）"""
    get_module_loader().unload(module_name)


def cleanup_modules():
    """清理閒置模組（便捷函數）"""
    get_module_loader().cleanup_idle_modules()


# 測試程式碼
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== 動態模組載入器測試 ===\n")

    loader = get_module_loader()

    # 測試 1: 載入模組
    print("1. 測試載入模組:")
    module = loader.get('smart_triggers')
    if module:
        print(f"   ✓ 載入成功: smart_triggers")
    else:
        print(f"   ✗ 載入失敗（模組可能未啟用或不存在）")

    # 測試 2: 統計資訊
    print("\n2. 載入統計:")
    stats = loader.get_stats()
    print(f"   已載入模組數: {stats['loaded_count']}")
    print(f"   已載入模組: {stats['loaded_modules']}")

    # 測試 3: 卸載
    print("\n3. 測試卸載模組:")
    loader.unload('smart_triggers', force=True)
    print(f"   已載入模組: {loader.get_stats()['loaded_modules']}")

    print("\n✓ 測試完成")
