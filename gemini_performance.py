#!/usr/bin/env python3
"""
Gemini 性能優化模組
提供並行處理、記憶體優化、快取機制強化
"""
import os
import hashlib
import functools
from typing import Any, Callable, Optional, Dict, List
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import json

console = Console()

# ==================== 快取機制 ====================

class LRUCache:
    """LRU (Least Recently Used) 快取"""
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []

    def _is_expired(self, item: Dict[str, Any]) -> bool:
        if 'timestamp' not in item:
            return True
        timestamp = datetime.fromisoformat(item['timestamp'])
        return datetime.now() - timestamp > timedelta(seconds=self.ttl)

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        item = self.cache[key]
        if self._is_expired(item):
            self.delete(key)
            return None
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
        return item['value']

    def set(self, key: str, value: Any):
        if len(self.cache) >= self.max_size and key not in self.cache:
            if self.access_order:
                oldest_key = self.access_order.pop(0)
                del self.cache[oldest_key]
        self.cache[key] = {'value': value, 'timestamp': datetime.now().isoformat()}
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)

    def clear(self):
        self.cache.clear()
        self.access_order.clear()

    def size(self) -> int:
        return len(self.cache)

    def cleanup_expired(self):
        expired_keys = [key for key, item in self.cache.items() if self._is_expired(item)]
        for key in expired_keys:
            self.delete(key)
        return len(expired_keys)

def cached(ttl: int = 3600, max_size: int = 100):
    """快取裝飾器"""
    cache = LRUCache(max_size=max_size, ttl=ttl)
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        wrapper.cache_info = lambda: {'size': cache.size(), 'max_size': cache.max_size, 'ttl': cache.ttl}
        return wrapper
    return decorator

# ==================== 並行處理 ====================

class ParallelProcessor:
    """並行處理器"""
    def __init__(self, max_workers: Optional[int] = None, use_processes: bool = False):
        self.max_workers = max_workers
        self.use_processes = use_processes

    def map(self, func: Callable, items: List[Any], show_progress: bool = True, description: str = "處理中") -> List[Any]:
        ExecutorClass = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        results = []
        with ExecutorClass(max_workers=self.max_workers) as executor:
            futures = {executor.submit(func, item): i for i, item in enumerate(items)}
            if show_progress:
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), 
                             BarColumn(), TaskProgressColumn(), console=console) as progress:
                    task = progress.add_task(description, total=len(items))
                    results = [None] * len(items)
                    for future in as_completed(futures):
                        index = futures[future]
                        try:
                            results[index] = future.result()
                        except Exception as e:
                            console.print(f"[red]任務 {index} 失敗：{e}[/red]")
                            results[index] = None
                        progress.update(task, advance=1)
            else:
                results = [None] * len(items)
                for future in as_completed(futures):
                    index = futures[future]
                    try:
                        results[index] = future.result()
                    except Exception as e:
                        console.print(f"[red]任務 {index} 失敗：{e}[/red]")
                        results[index] = None
        return results

    def execute_concurrent(self, tasks: List[Callable], show_progress: bool = True) -> List[Any]:
        return self.map(func=lambda task: task(), items=tasks, show_progress=show_progress, description="執行任務")

# ==================== 記憶體優化 ====================

class ChunkedProcessor:
    """分塊處理器（用於處理大型資料集）"""
    def __init__(self, chunk_size: int = 100):
        self.chunk_size = chunk_size

    def process_in_chunks(self, items: List[Any], processor: Callable[[List[Any]], List[Any]], 
                         show_progress: bool = True) -> List[Any]:
        results = []
        total_chunks = (len(items) + self.chunk_size - 1) // self.chunk_size
        if show_progress:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                         BarColumn(), TaskProgressColumn(), console=console) as progress:
                task = progress.add_task(f"分塊處理（共 {total_chunks} 塊）", total=total_chunks)
                for i in range(0, len(items), self.chunk_size):
                    chunk = items[i:i + self.chunk_size]
                    chunk_results = processor(chunk)
                    results.extend(chunk_results)
                    progress.update(task, advance=1)
        else:
            for i in range(0, len(items), self.chunk_size):
                chunk = items[i:i + self.chunk_size]
                chunk_results = processor(chunk)
                results.extend(chunk_results)
        return results

# ==================== 結果快取 ====================

class ResultCache:
    """持久化結果快取（用於 API 調用結果）"""
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / "gemini_videos" / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        cache_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{cache_key}.json"

    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if ttl is not None:
                timestamp = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - timestamp > timedelta(seconds=ttl):
                    cache_path.unlink()
                    return None
            return data['value']
        except Exception as e:
            console.print(f"[yellow]讀取快取失敗：{e}[/yellow]")
            return None

    def set(self, key: str, value: Any):
        cache_path = self._get_cache_path(key)
        try:
            data = {'key': key, 'value': value, 'timestamp': datetime.now().isoformat()}
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(f"[red]保存快取失敗：{e}[/red]")

    def delete(self, key: str):
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()

    def clear(self):
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def cleanup_expired(self, ttl: int = 86400):
        deleted = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                timestamp = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - timestamp > timedelta(seconds=ttl):
                    cache_file.unlink()
                    deleted += 1
            except Exception:
                continue
        return deleted
