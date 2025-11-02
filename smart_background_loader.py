#!/usr/bin/env python3
"""
智能背景預載入系統
在使用者互動時預判並載入模組，使啟動感覺瞬間完成

設計理念：
1. 使用者選擇模型時 → 背景載入常用模組
2. 使用者輸入時 → 預判意圖並預載入相關模組
3. 使用者等待回應時 → 載入可能需要的模組
4. 分階段載入，優先載入最可能使用的

時間分配策略：
- 模型選擇（3-5秒）→ 載入 Tier 1（計價、快取）
- 首次輸入（5-10秒）→ 載入 Tier 2（翻譯、媒體查看）
- API 回應等待（2-5秒）→ 載入 Tier 3（低頻功能）
"""

import threading
import time
import queue
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LoadPriority(Enum):
    """載入優先級"""
    CRITICAL = 1    # 立即載入（啟動必要）
    HIGH = 2        # 使用者選擇模型時載入
    MEDIUM = 3      # 使用者首次輸入時載入
    LOW = 4         # API 回應等待時載入
    IDLE = 5        # 閒置時載入


@dataclass
class LoadTask:
    """載入任務"""
    name: str                       # 模組名稱
    loader: Callable[[], Any]       # 載入函數
    priority: LoadPriority          # 優先級
    estimated_time: float           # 預估載入時間（秒）
    loaded: bool = False            # 是否已載入
    module: Any = None              # 載入後的模組
    load_time: float = 0.0          # 實際載入時間


class SmartBackgroundLoader:
    """
    智能背景載入器

    根據使用者行為預判並在背景載入模組
    使 17 秒的啟動時間感覺像 2-3 秒
    """

    def __init__(self):
        self._tasks: Dict[str, LoadTask] = {}
        self._load_queue = queue.PriorityQueue()
        self._loader_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        self._stats = {
            'total_loaded': 0,
            'total_time': 0.0,
            'background_time': 0.0
        }

    def register_task(self,
                      name: str,
                      loader: Callable[[], Any],
                      priority: LoadPriority,
                      estimated_time: float = 0.1):
        """
        註冊載入任務

        Args:
            name: 模組名稱
            loader: 載入函數
            priority: 優先級
            estimated_time: 預估載入時間（秒）
        """
        with self._lock:
            self._tasks[name] = LoadTask(
                name=name,
                loader=loader,
                priority=priority,
                estimated_time=estimated_time
            )
            logger.debug(f"註冊載入任務: {name} (優先級: {priority.name})")

    def start_background_loading(self):
        """啟動背景載入線程"""
        if self._loader_thread is None or not self._loader_thread.is_alive():
            self._stop_flag.clear()
            self._loader_thread = threading.Thread(
                target=self._background_loader,
                daemon=True,
                name="SmartBackgroundLoader"
            )
            self._loader_thread.start()
            logger.info("背景載入器已啟動")

    def trigger_loading(self, priority: LoadPriority, available_time: float):
        """
        觸發特定優先級的載入

        Args:
            priority: 要載入的優先級
            available_time: 可用時間（秒）

        使用時機：
        - 使用者選擇模型 → trigger_loading(LoadPriority.HIGH, 5.0)
        - 使用者輸入中 → trigger_loading(LoadPriority.MEDIUM, 10.0)
        - 等待 API 回應 → trigger_loading(LoadPriority.LOW, 3.0)
        """
        tasks_to_load = []
        total_time = 0.0

        with self._lock:
            # 選擇符合優先級且未載入的任務
            for task in self._tasks.values():
                if task.priority == priority and not task.loaded:
                    if total_time + task.estimated_time <= available_time:
                        tasks_to_load.append(task)
                        total_time += task.estimated_time

        # 加入載入隊列
        for task in tasks_to_load:
            # 使用優先級值作為排序（數字越小優先級越高）
            self._load_queue.put((task.priority.value, task.name))

        logger.debug(f"觸發載入 {len(tasks_to_load)} 個任務 "
                    f"(優先級: {priority.name}, 預估時間: {total_time:.1f}s)")

    def load_now(self, name: str) -> Optional[Any]:
        """
        立即載入指定模組（同步）

        Args:
            name: 模組名稱

        Returns:
            載入的模組，如果失敗則返回 None
        """
        with self._lock:
            task = self._tasks.get(name)
            if not task:
                logger.warning(f"未找到載入任務: {name}")
                return None

            if task.loaded:
                logger.debug(f"模組已載入: {name}")
                return task.module

        # 執行載入
        start = time.time()
        try:
            module = task.loader()
            load_time = time.time() - start

            with self._lock:
                task.loaded = True
                task.module = module
                task.load_time = load_time
                self._stats['total_loaded'] += 1
                self._stats['total_time'] += load_time

            logger.info(f"✓ 同步載入完成: {name} ({load_time:.2f}s)")
            return module
        except Exception as e:
            logger.error(f"✗ 載入失敗: {name} - {e}")
            return None

    def get_module(self, name: str) -> Optional[Any]:
        """
        獲取模組（如果已載入）

        Args:
            name: 模組名稱

        Returns:
            已載入的模組，未載入則返回 None
        """
        with self._lock:
            task = self._tasks.get(name)
            if task and task.loaded:
                return task.module
        return None

    def _background_loader(self):
        """背景載入線程主循環"""
        logger.info("背景載入線程開始運行")

        while not self._stop_flag.is_set():
            try:
                # 等待載入任務（1秒超時）
                priority_value, task_name = self._load_queue.get(timeout=1.0)

                with self._lock:
                    task = self._tasks.get(task_name)
                    if not task or task.loaded:
                        continue

                # 執行背景載入
                start = time.time()
                try:
                    module = task.loader()
                    load_time = time.time() - start

                    with self._lock:
                        task.loaded = True
                        task.module = module
                        task.load_time = load_time
                        self._stats['total_loaded'] += 1
                        self._stats['total_time'] += load_time
                        self._stats['background_time'] += load_time

                    logger.debug(f"✓ 背景載入完成: {task_name} ({load_time:.2f}s)")
                except Exception as e:
                    logger.error(f"✗ 背景載入失敗: {task_name} - {e}")

            except queue.Empty:
                # 隊列為空，繼續等待
                continue
            except Exception as e:
                logger.error(f"背景載入線程錯誤: {e}")

        logger.info("背景載入線程已停止")

    def stop(self):
        """停止背景載入"""
        self._stop_flag.set()
        if self._loader_thread:
            self._loader_thread.join(timeout=2.0)
        logger.info("背景載入器已停止")

    def get_stats(self) -> Dict[str, Any]:
        """獲取載入統計"""
        with self._lock:
            total_tasks = len(self._tasks)
            loaded_tasks = sum(1 for t in self._tasks.values() if t.loaded)
            return {
                'total_tasks': total_tasks,
                'loaded_tasks': loaded_tasks,
                'loading_rate': loaded_tasks / total_tasks if total_tasks > 0 else 0,
                'total_load_time': self._stats['total_time'],
                'background_load_time': self._stats['background_time'],
                'foreground_load_time': self._stats['total_time'] - self._stats['background_time']
            }

    def print_stats(self):
        """打印載入統計"""
        stats = self.get_stats()
        print("\n" + "="*60)
        print("智能背景載入統計")
        print("="*60)
        print(f"總任務數: {stats['total_tasks']}")
        print(f"已載入: {stats['loaded_tasks']} ({stats['loading_rate']*100:.1f}%)")
        print(f"總載入時間: {stats['total_load_time']:.2f}s")
        print(f"  - 背景載入: {stats['background_load_time']:.2f}s")
        print(f"  - 前景載入: {stats['foreground_load_time']:.2f}s")
        print(f"時間節省: {stats['background_load_time']:.2f}s")
        print("="*60)


# ============================================================================
# 預定義載入計劃
# ============================================================================

class LoadingPlan:
    """預定義的載入計劃"""

    @staticmethod
    def register_default_tasks(loader: SmartBackgroundLoader):
        """
        註冊預設載入任務

        根據啟動分析報告的數據設定優先級和預估時間
        """

        # Tier 1: 核心功能（使用者選擇模型時載入）
        # 預估可用時間：3-5 秒

        loader.register_task(
            name='pricing',
            loader=lambda: __import__('gemini_pricing'),
            priority=LoadPriority.HIGH,
            estimated_time=0.05  # 計價系統很輕量
        )

        loader.register_task(
            name='cache_manager',
            loader=lambda: __import__('gemini_cache_manager'),
            priority=LoadPriority.HIGH,
            estimated_time=0.05  # gemini_cache_manager: 50.8ms
        )

        loader.register_task(
            name='checkpoint',
            loader=lambda: __import__('gemini_checkpoint'),
            priority=LoadPriority.HIGH,
            estimated_time=0.1  # 38KB，檢查點系統
        )

        loader.register_task(
            name='streaming_display',
            loader=lambda: __import__('gemini_streaming_display'),
            priority=LoadPriority.HIGH,
            estimated_time=0.03  # 11KB，串流顯示
        )

        # Tier 2: 常用功能（使用者首次輸入時載入）
        # 預估可用時間：5-10 秒

        loader.register_task(
            name='translator',
            loader=lambda: __import__('gemini_translator').get_translator(),
            priority=LoadPriority.MEDIUM,
            estimated_time=0.15  # deep_translator + bs4: ~150ms
        )

        loader.register_task(
            name='media_viewer',
            loader=lambda: __import__('gemini_media_viewer'),
            priority=LoadPriority.MEDIUM,
            estimated_time=0.05
        )

        loader.register_task(
            name='smart_triggers',
            loader=lambda: __import__('gemini_smart_triggers'),
            priority=LoadPriority.MEDIUM,
            estimated_time=0.02
        )

        loader.register_task(
            name='file_manager',
            loader=lambda: __import__('gemini_file_manager'),
            priority=LoadPriority.MEDIUM,
            estimated_time=0.05  # 20KB，檔案處理功能
        )

        # Tier 3: 低頻功能（API 回應等待時載入）
        # 預估可用時間：2-5 秒

        loader.register_task(
            name='video_analyzer',
            loader=lambda: __import__('gemini_video_analyzer'),
            priority=LoadPriority.LOW,
            estimated_time=0.2
        )

        loader.register_task(
            name='imagen_generator',
            loader=lambda: __import__('gemini_imagen_generator'),
            priority=LoadPriority.LOW,
            estimated_time=0.15
        )

        loader.register_task(
            name='audio_processor',
            loader=lambda: __import__('gemini_audio_processor'),
            priority=LoadPriority.LOW,
            estimated_time=0.1
        )

        loader.register_task(
            name='subtitle_generator',
            loader=lambda: __import__('gemini_subtitle_generator'),
            priority=LoadPriority.LOW,
            estimated_time=0.1
        )

        # Tier 4: 閒置時載入
        # 在完全閒置時才載入

        loader.register_task(
            name='flow_engine',
            loader=lambda: __import__('gemini_flow_engine'),
            priority=LoadPriority.IDLE,
            estimated_time=0.3
        )

        # Update 系統相關模組（條件式載入）
        # 這些模組不會自動載入，需要明確觸發

        loader.register_task(
            name='updater',
            loader=lambda: __import__('gemini_updater'),
            priority=LoadPriority.CRITICAL,  # 啟動時載入
            estimated_time=0.01  # 非常輕量
        )

        loader.register_task(
            name='upgrade',
            loader=lambda: __import__('gemini_upgrade'),
            priority=LoadPriority.HIGH,  # 發現更新後載入
            estimated_time=0.05  # 相對較重（14KB）
        )


# ============================================================================
# 全域實例
# ============================================================================

_global_loader: Optional[SmartBackgroundLoader] = None


def get_smart_loader() -> SmartBackgroundLoader:
    """獲取全域智能載入器"""
    global _global_loader
    if _global_loader is None:
        _global_loader = SmartBackgroundLoader()
        # 註冊預設任務
        LoadingPlan.register_default_tasks(_global_loader)
        # 啟動背景載入
        _global_loader.start_background_loading()
    return _global_loader


# ============================================================================
# 便捷函數
# ============================================================================

def on_model_selection_start():
    """使用者開始選擇模型時調用"""
    loader = get_smart_loader()
    # 預估使用者選擇模型需要 3-5 秒
    loader.trigger_loading(LoadPriority.HIGH, available_time=5.0)
    logger.debug("🎯 觸發 Tier 1 載入（使用者選擇模型中）")


def on_first_input_start():
    """使用者開始首次輸入時調用"""
    loader = get_smart_loader()
    # 預估使用者輸入需要 5-10 秒
    loader.trigger_loading(LoadPriority.MEDIUM, available_time=10.0)
    logger.debug("🎯 觸發 Tier 2 載入（使用者輸入中）")


def on_api_call_start():
    """開始 API 調用時調用"""
    loader = get_smart_loader()
    # 預估 API 回應需要 2-5 秒
    loader.trigger_loading(LoadPriority.LOW, available_time=5.0)
    logger.debug("🎯 觸發 Tier 3 載入（等待 API 回應中）")


def get_module_lazy(name: str) -> Optional[Any]:
    """
    延遲獲取模組

    如果已載入則立即返回，否則同步載入

    Args:
        name: 模組名稱

    Returns:
        模組實例
    """
    loader = get_smart_loader()

    # 先檢查是否已載入
    module = loader.get_module(name)
    if module:
        return module

    # 未載入則同步載入
    return loader.load_now(name)


def on_update_available():
    """
    發現有更新可用時調用

    觸發 upgrade 模組的預載入，讓使用者輸入 /upgrade 時無需等待
    """
    loader = get_smart_loader()
    # 預載入 upgrade 模組（使用者很可能會執行更新）
    loader.trigger_loading(LoadPriority.HIGH, available_time=1.0)
    logger.debug("🎯 觸發 upgrade 模組預載入（發現可用更新）")


if __name__ == "__main__":
    # 測試
    logging.basicConfig(level=logging.INFO)

    print("測試智能背景載入器...\n")

    # 創建載入器並註冊測試任務
    loader = SmartBackgroundLoader()

    # 註冊測試任務
    def slow_loader():
        time.sleep(0.5)
        return "SlowModule"

    def fast_loader():
        time.sleep(0.1)
        return "FastModule"

    loader.register_task('slow', slow_loader, LoadPriority.HIGH, 0.5)
    loader.register_task('fast', fast_loader, LoadPriority.MEDIUM, 0.1)

    # 啟動背景載入
    loader.start_background_loading()

    # 模擬使用者選擇模型
    print("使用者選擇模型中...")
    loader.trigger_loading(LoadPriority.HIGH, 1.0)

    # 等待背景載入
    time.sleep(1.0)

    # 檢查載入狀態
    print("\n檢查 'slow' 模組:", loader.get_module('slow'))
    print("檢查 'fast' 模組:", loader.get_module('fast'))

    # 模擬使用者輸入
    print("\n使用者輸入中...")
    loader.trigger_loading(LoadPriority.MEDIUM, 0.5)

    time.sleep(0.5)

    # 打印統計
    loader.print_stats()

    # 停止
    loader.stop()
    print("\n✅ 測試完成")
