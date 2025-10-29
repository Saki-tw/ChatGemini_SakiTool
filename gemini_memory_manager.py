#!/usr/bin/env python3
"""
Gemini Memory Manager - 記憶體管理模組
=====================================

功能：
1. 記憶體池管理 (MemoryPoolManager)
2. 大型對話歷史分頁 (ConversationManager)
3. 圖片分塊載入 (load_image_chunked)
4. 影片分段處理 (process_video_chunked)
5. 檔案上傳斷點續傳 (ChunkedUploader)
6. 多線程處理框架 (ParallelProcessor)

Author: Saki-tw
Email: Saki@saki-studio.com.tw
Date: 2025-10-23
"""

import os
import io
import gc
import json
import time
import hashlib
import subprocess
import psutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from rich.console import Console
from utils.i18n import safe_t
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich import print as rprint

console = Console()


# ============================================================================
# 1. 記憶體池管理器
# ============================================================================

class MemoryPoolManager:
    """記憶體池管理器 - 監控並控制記憶體使用量"""

    def __init__(self, max_memory_mb: int = 2048):
        """
        初始化記憶體池管理器

        Args:
            max_memory_mb: 最大記憶體使用量 (MB)，預設 2GB
        """
        self.max_memory = max_memory_mb * 1024 * 1024  # 轉換為 bytes
        self.process = psutil.Process()
        self.peak_memory = 0
        start_memory=self.get_current_memory()

    def get_current_memory(self) -> int:
        """取得當前程序的記憶體使用量 (bytes)"""
        return self.process.memory_info().rss

    def get_current_memory_mb(self) -> float:
        """取得當前記憶體使用量 (MB)"""
        return self.get_current_memory() / (1024 * 1024)

    def check_memory_usage(self) -> Tuple[bool, float]:
        """
        檢查記憶體使用量是否超過限制

        Returns:
            (是否安全, 當前使用量 MB)
        """
        current_mb = self.get_current_memory_mb()
        self.peak_memory = max(self.peak_memory, current_mb)

        is_safe = current_mb < (self.max_memory / (1024 * 1024))
        return is_safe, current_mb

    def force_gc(self):
        """強制垃圾回收"""
        gc.collect()

    def get_memory_report(self) -> Dict[str, float]:
        """取得記憶體使用報告"""
        current_mb = self.get_current_memory_mb()
        start_mb = self.start_memory / (1024 * 1024)

        return {
            "current_mb": round(current_mb, 2),
            "peak_mb": round(self.peak_memory, 2),
            "start_mb": round(start_mb, 2),
            "delta_mb": round(current_mb - start_mb, 2),
            "max_limit_mb": round(self.max_memory / (1024 * 1024), 2),
            "usage_percent": round((current_mb / (self.max_memory / (1024 * 1024))) * 100, 2)
        }

    def print_memory_report(self):
        """輸出記憶體使用報告"""
        report = self.get_memory_report()

        console.print(Panel(
            f"""[bold #DDA0DD]記憶體使用報告[/bold #DDA0DD]

當前使用: [#DDA0DD]{report['current_mb']} MB[/#DDA0DD]
峰值使用: [dim #DDA0DD]{report['peak_mb']} MB[/red]
起始使用: [#DA70D6]{report['start_mb']} MB[/green]
增量使用: [#DDA0DD]{report['delta_mb']} MB[/#DDA0DD]
使用率: [{'red' if report['usage_percent'] > 80 else 'green'}]{report['usage_percent']}%[/]
記憶體限制: {report['max_limit_mb']} MB""",
            title="💾 Memory Report",
            border_style="#DA70D6"
        ))


# ============================================================================
# 2. 對話歷史管理器
# ============================================================================

class ConversationManager:
    """對話歷史管理器 - 支援分頁與自動存檔

    .. deprecated:: v1.0.3
        建議使用 gemini_conversation.ConversationManager，該版本提供更完整的功能。
        此版本將在 v2.0 移除。
    """

    def __init__(
        self,
        max_history: int = 100,
        archive_path: Optional[Path] = None,
        auto_archive: bool = True
    ):
        """
        初始化對話管理器

        Args:
            max_history: 記憶體中最多保留的對話數
            archive_path: 存檔路徑，預設為 ~/.gemini_conversations/
            auto_archive: 是否自動存檔
        """
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.archived: List[Dict[str, Any]] = []
        self.auto_archive = auto_archive

        # 設定存檔路徑
        if archive_path is None:
            # 使用統一快取目錄
            from utils.path_manager import get_cache_dir
            self.archive_path = get_cache_dir('memory_archive')
        else:
            self.archive_path = Path(archive_path)
            self.archive_path.mkdir(parents=True, exist_ok=True)

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        新增訊息到對話歷史

        Args:
            role: 角色 (user/model)
            content: 訊息內容
            metadata: 額外資訊 (如時間戳、token 數等)
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }

        self.history.append(message)

        # 檢查是否需要存檔
        if len(self.history) > self.max_history and self.auto_archive:
            self._archive_old_messages()

    def _archive_old_messages(self):
        """將舊訊息存檔到磁碟"""
        # 保留最近 50% 的訊息
        split_point = self.max_history // 2

        to_archive = self.history[:split_point]
        history=self.history[split_point:]

        # 寫入存檔
        timestamp = int(time.time())
        archive_file = self.archive_path / f"conversation_{timestamp}.json"

        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(to_archive, f, ensure_ascii=False, indent=2)

        console.print(safe_t('common.message', fallback='[dim]📁 已存檔 {len(to_archive)} 則對話到 {archive_file.name}[/dim]', to_archive_count=len(to_archive), name=archive_file.name))

        # 強制垃圾回收
        gc.collect()

    def get_recent_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """取得最近 N 則對話"""
        return self.history[-count:]

    def clear_history(self, save_archive: bool = True):
        """清除所有對話歷史"""
        if save_archive and len(self.history) > 0:
            self._archive_old_messages()
        self.history.clear()
        gc.collect()

    def get_statistics(self) -> Dict[str, Any]:
        """取得對話統計資訊"""
        return {
            "current_count": len(self.history),
            "max_history": self.max_history,
            "archive_count": len(list(self.archive_path.glob("*.json"))),
            "usage_percent": round((len(self.history) / self.max_history) * 100, 2)
        }


# ============================================================================
# 3. 圖片分塊載入
# ============================================================================

def load_image_chunked(
    file_path: str,
    max_size: Tuple[int, int] = (1920, 1080),
    quality: int = 85
) -> bytes:
    """
    分塊載入圖片，避免記憶體溢出

    Args:
        file_path: 圖片檔案路徑
        max_size: 最大尺寸 (寬, 高)，預設 1920x1080
        quality: JPEG 品質 (1-100)

    Returns:
        圖片的 bytes 資料

    Example:
        >>> image_data = load_image_chunked("4k_image.jpg")
        >>> # 可安全處理 4K 圖片而不會 OOM
    """
    try:
        with Image.open(file_path) as img:
            # 取得原始尺寸
            original_size = img.size
            original_format = img.format or 'JPEG'

            # 縮放至最大尺寸（保持比例）
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # 轉換為 RGB（如果是 RGBA 或其他格式）
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 轉換為 bytes（使用 BytesIO 避免載入整個圖片到記憶體）
            buffer = io.BytesIO()

            # 根據原始格式選擇輸出格式
            if original_format in ('JPEG', 'JPG'):
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
            elif original_format == 'PNG':
                img.save(buffer, format='PNG', optimize=True)
            else:
                img.save(buffer, format='JPEG', quality=quality, optimize=True)

            image_bytes = buffer.getvalue()
            buffer.close()

            # 輸出處理資訊
            new_size = img.size
            reduction = round((1 - len(image_bytes) / os.path.getsize(file_path)) * 100, 2)

            console.print(safe_t('common.processing', fallback='[dim]🖼️  圖片處理: {original_size} → {new_size}, 記憶體減少 {reduction}%[/dim]', original_size=original_size, new_size=new_size, reduction=reduction))

            return image_bytes

    except Exception as e:
        console.print(safe_t('error.failed', fallback='[dim #DDA0DD]❌ 圖片載入失敗: {e}[/red]', e=e))
        raise


# ============================================================================
# 4. 影片分段處理
# ============================================================================

def get_video_duration(video_path: str) -> float:
    """
    取得影片時長（秒）

    Args:
        video_path: 影片檔案路徑

    Returns:
        影片時長（秒）
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    except Exception as e:
        console.print(safe_t('error.cannot_process', fallback='[dim #DDA0DD]❌ 無法取得影片時長: {e}[/red]', e=e))
        return 0.0


def process_video_chunked(
    video_path: str,
    output_path: str,
    chunk_duration: int = 60,
    process_func: Optional[Callable] = None,
    cleanup: bool = True
) -> bool:
    """
    分段處理影片，避免記憶體溢出

    Args:
        video_path: 輸入影片路徑
        output_path: 輸出影片路徑
        chunk_duration: 每段時長（秒），預設 60 秒
        process_func: 處理函數，接收 (chunk_path, chunk_index) 並返回處理後的路徑
        cleanup: 是否清理臨時檔案

    Returns:
        是否成功

    Example:
        >>> def my_process(chunk_path, idx):
        ...     # 對 chunk 進行處理
        ...     return processed_path
        >>> process_video_chunked("long_video.mp4", "output.mp4", process_func=my_process)
    """
    try:
        # 取得影片總時長
        duration = get_video_duration(video_path)
        if duration == 0:
            return False

        # 計算分段數
        num_chunks = int(duration // chunk_duration) + 1
        temp_dir = Path(output_path).parent / "temp_chunks"
        temp_dir.mkdir(exist_ok=True)

        processed_chunks = []

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task(f"🎬 分段處理影片 ({num_chunks} 段)", total=num_chunks)

            for i in range(num_chunks):
                start_time = i * chunk_duration
                chunk_path = temp_dir / f"chunk_{i:04d}.mp4"

                # 切割影片片段
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-ss', str(start_time),
                    '-t', str(chunk_duration),
                    '-c', 'copy',  # 無損複製
                    '-y',  # 覆寫輸出
                    str(chunk_path)
                ]

                subprocess.run(cmd, capture_output=True, check=True)

                # 如果有處理函數，則處理此片段
                if process_func:
                    processed_path = process_func(str(chunk_path), i)
                    processed_chunks.append(processed_path)
                else:
                    processed_chunks.append(str(chunk_path))

                progress.update(task, advance=1)

                # 強制垃圾回收
                gc.collect()

        # 合併所有片段
        console.print(safe_t('common.message', fallback='[#DDA0DD]🔗 合併影片片段...[/#DDA0DD]'))
        _merge_video_chunks(processed_chunks, output_path)

        # 清理臨時檔案
        if cleanup:
            console.print(safe_t('common.message', fallback='[dim]🧹 清理臨時檔案...[/dim]'))
            for chunk in processed_chunks:
                if os.path.exists(chunk):
                    os.remove(chunk)
            if temp_dir.exists():
                temp_dir.rmdir()

        console.print(safe_t('common.completed', fallback='[#DA70D6]✅ 影片處理完成: {output_path}[/green]', output_path=output_path))
        return True

    except Exception as e:
        console.print(safe_t('error.failed', fallback='[dim #DDA0DD]❌ 影片處理失敗: {e}[/red]', e=e))
        return False


def _merge_video_chunks(chunk_paths: List[str], output_path: str):
    """合併影片片段"""
    # 建立 concat 檔案清單
    concat_file = Path(output_path).parent / "concat_list.txt"

    with open(concat_file, 'w') as f:
        for chunk_path in chunk_paths:
            f.write(f"file '{chunk_path}'\n")

    # 使用 ffmpeg concat
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        '-y',
        output_path
    ]

    subprocess.run(cmd, capture_output=True, check=True)

    # 清理 concat 清單
    if concat_file.exists():
        concat_file.unlink()


# ============================================================================
# 5. 檔案上傳斷點續傳
# ============================================================================

class ChunkedUploader:
    """檔案分塊上傳器 - 支援斷點續傳"""

    CHUNK_SIZE = 5 * 1024 * 1024  # 5MB per chunk

    def __init__(self, progress_dir: Optional[Path] = None):
        """
        初始化分塊上傳器

        Args:
            progress_dir: 進度檔案存放目錄
        """
        if progress_dir is None:
            # 使用統一快取目錄
            from utils.path_manager import get_cache_dir
            self.progress_dir = get_cache_dir('upload_progress')
        else:
            self.progress_dir = Path(progress_dir)

        self.progress_dir.mkdir(parents=True, exist_ok=True)

    def _get_progress_file(self, file_path: str) -> Path:
        """取得進度檔案路徑"""
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        return self.progress_dir / f"upload_{file_hash}.json"

    def _load_progress(self, file_path: str) -> Dict[str, Any]:
        """載入上傳進度"""
        progress_file = self._get_progress_file(file_path)

        if progress_file.exists():
            with open(progress_file, 'r') as f:
                return json.load(f)

        return {"uploaded_chunks": [], "total_chunks": 0, "completed": False}

    def _save_progress(self, file_path: str, progress: Dict[str, Any]):
        """儲存上傳進度"""
        progress_file = self._get_progress_file(file_path)

        with open(progress_file, 'w') as f:
            json.dump(progress, f)

    def _clear_progress(self, file_path: str):
        """清除上傳進度"""
        progress_file = self._get_progress_file(file_path)
        if progress_file.exists():
            progress_file.unlink()

    def upload_file(
        self,
        file_path: str,
        upload_func: Callable[[bytes, int, int], bool],
        resume: bool = True
    ) -> bool:
        """
        分塊上傳檔案

        Args:
            file_path: 檔案路徑
            upload_func: 上傳函數，接收 (chunk_data, chunk_index, total_chunks) 並返回是否成功
            resume: 是否啟用斷點續傳

        Returns:
            是否上傳成功

        Example:
            >>> def my_upload(data, idx, total):
            ...     # 上傳 chunk 到 API
            ...     return True
            >>> uploader = ChunkedUploader()
            >>> uploader.upload_file("large_file.mp4", my_upload)
        """
        try:
            file_size = os.path.getsize(file_path)
            total_chunks = (file_size // self.CHUNK_SIZE) + 1

            # 載入進度
            progress = self._load_progress(file_path) if resume else {
                "uploaded_chunks": [],
                "total_chunks": total_chunks,
                "completed": False
            }

            # 如果已完成，直接返回
            if progress.get("completed"):
                console.print(safe_t('common.completed', fallback='[#DA70D6]✅ 檔案已上傳完成（使用快取）[/green]'))
                return True

            uploaded_chunks = set(progress["uploaded_chunks"])

            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("[#DDA0DD]{task.completed}/{task.total} chunks"),
                TimeRemainingColumn(),
                console=console
            ) as progress_bar:

                task = progress_bar.add_task(
                    f"📤 上傳 {Path(file_path).name}",
                    total=total_chunks
                )

                # 設定初始進度
                progress_bar.update(task, completed=len(uploaded_chunks))

                with open(file_path, 'rb') as f:
                    for chunk_idx in range(total_chunks):
                        # 跳過已上傳的 chunk
                        if chunk_idx in uploaded_chunks:
                            continue

                        # 讀取 chunk
                        f.seek(chunk_idx * self.CHUNK_SIZE)
                        chunk_data = f.read(self.CHUNK_SIZE)

                        # 上傳 chunk
                        success = upload_func(chunk_data, chunk_idx, total_chunks)

                        if not success:
                            console.print(safe_t('error.failed', fallback='[dim #DDA0DD]❌ Chunk {chunk_idx} 上傳失敗[/red]', chunk_idx=chunk_idx))
                            return False

                        # 更新進度
                        uploaded_chunks.add(chunk_idx)
                        progress["uploaded_chunks"] = list(uploaded_chunks)
                        self._save_progress(file_path, progress)

                        progress_bar.update(task, advance=1)

                        # 釋放記憶體
                        del chunk_data
                        gc.collect()

            # 標記為完成
            progress["completed"] = True
            self._save_progress(file_path, progress)

            console.print(safe_t('common.completed', fallback='[#DA70D6]✅ 檔案上傳完成: {file_path}[/green]', file_path=file_path))
            return True

        except Exception as e:
            console.print(safe_t('error.failed', fallback='[dim #DDA0DD]❌ 上傳失敗: {e}[/red]', e=e))
            return False


# ============================================================================
# 6. 多線程處理框架
# ============================================================================

class ParallelProcessor:
    """多線程並行處理器"""

    def __init__(self, max_workers: int = 4):
        """
        初始化並行處理器

        Args:
            max_workers: 最大執行緒數，預設 4
        """
        self.max_workers = max_workers

    def process_batch(
        self,
        items: List[Any],
        process_func: Callable[[Any], Any],
        description: str = "處理中"
    ) -> List[Dict[str, Any]]:
        """
        批次並行處理項目

        Args:
            items: 要處理的項目列表
            process_func: 處理函數，接收單一項目並返回結果
            description: 進度描述

        Returns:
            結果列表，每個結果包含 {"item", "status", "result"/"error"}

        Example:
            >>> def process_image(path):
            ...     return analyze_image(path)
            >>> processor = ParallelProcessor(max_workers=4)
            >>> results = processor.process_batch(image_paths, process_image, "分析圖片")
        """
        results = []

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total}"),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task(f"⚡ {description}", total=len(items))

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任務
                futures = {
                    executor.submit(process_func, item): item
                    for item in items
                }

                # 收集結果
                for future in as_completed(futures):
                    item = futures[future]

                    try:
                        result = future.result()
                        results.append({
                            "item": item,
                            "status": "success",
                            "result": result
                        })
                    except Exception as e:
                        results.append({
                            "item": item,
                            "status": "error",
                            "error": str(e)
                        })

                    progress.update(task, advance=1)

        # 輸出統計
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = len(results) - success_count

        console.print(safe_t('error.failed', fallback='\n[#DA70D6]✅ 成功: {success_count}[/green] | [dim #DDA0DD]❌ 失敗: {error_count}[/red]', success_count=success_count, error_count=error_count))

        return results


# ============================================================================
# 主程式 (測試用)
# ============================================================================

if __name__ == "__main__":
    console.print(Panel(
        """[bold #DDA0DD]Gemini Memory Manager[/bold #DDA0DD]

✅ 記憶體池管理器 (MemoryPoolManager)
✅ 對話歷史管理器 (ConversationManager)
✅ 圖片分塊載入 (load_image_chunked)
✅ 影片分段處理 (process_video_chunked)
✅ 檔案上傳斷點續傳 (ChunkedUploader)
✅ 多線程處理框架 (ParallelProcessor)

[dim]Author: Saki-tw | Email: Saki@saki-studio.com.tw[/dim]""",
        title="💾 Memory Management Tools",
        border_style="#DA70D6"
    ))

    # 示範記憶體管理器
    mem_manager = MemoryPoolManager(max_memory_mb=2048)
    mem_manager.print_memory_report()
