#!/usr/bin/env python3
"""
性能監控模組
提供處理時間統計、資源使用監控、瓶頸分析報告功能
"""
import time
import psutil
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps
from collections import defaultdict
import json
import os

# Rich 格式化輸出
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


@dataclass
class PerformanceMetrics:
    """性能指標資料結構"""
    name: str                           # 操作名稱
    start_time: float                   # 開始時間（timestamp）
    end_time: Optional[float] = None    # 結束時間（timestamp）
    duration: Optional[float] = None    # 持續時間（秒）
    cpu_usage_start: Optional[float] = None   # 開始時 CPU 使用率（%）
    cpu_usage_end: Optional[float] = None     # 結束時 CPU 使用率（%）
    cpu_usage_avg: Optional[float] = None     # 平均 CPU 使用率（%）
    memory_usage_start: Optional[float] = None  # 開始時記憶體使用（MB）
    memory_usage_end: Optional[float] = None    # 結束時記憶體使用（MB）
    memory_usage_peak: Optional[float] = None   # 峰值記憶體使用（MB）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 額外元數據


@dataclass
class BottleneckAnalysis:
    """瓶頸分析結果"""
    operation: str          # 操作名稱
    total_time: float       # 總耗時（秒）
    percentage: float       # 占總時間百分比
    count: int              # 執行次數
    avg_time: float         # 平均耗時（秒）
    max_time: float         # 最大耗時（秒）
    min_time: float         # 最小耗時（秒）
    memory_impact: float    # 記憶體影響（MB）
    cpu_impact: float       # CPU 影響（%）


class PerformanceMonitor:
    """
    性能監控器

    功能：
    1. 處理時間統計 - 追蹤每個操作的執行時間
    2. 資源使用監控 - 監控 CPU、記憶體使用情況
    3. 瓶頸分析報告 - 識別性能瓶頸並生成報告

    使用方式：
    1. 裝飾器：@monitor.track_performance("操作名稱")
    2. 上下文管理器：with monitor.measure("操作名稱"):
    3. 手動調用：monitor.start() / monitor.stop()
    """

    def __init__(self, enabled: bool = True):
        """
        初始化性能監控器

        Args:
            enabled: 是否啟用監控（預設 True）
        """
        self.enabled = enabled
        self.metrics: List[PerformanceMetrics] = []
        self.current_operations: Dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._resource_samples: Dict[str, List[tuple]] = defaultdict(list)  # {operation: [(timestamp, cpu, mem), ...]}

    def enable(self):
        """啟用監控"""
        self.enabled = True

    def disable(self):
        """停用監控"""
        self.enabled = False

    def clear(self):
        """清除所有記錄"""
        with self._lock:
            self.metrics.clear()
            self.current_operations.clear()
            self._resource_samples.clear()

    def _get_current_resources(self) -> tuple:
        """
        獲取當前資源使用情況

        Returns:
            (cpu_percent, memory_mb)
        """
        try:
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_mb = process.memory_info().rss / 1024 / 1024
            return cpu_percent, memory_mb
        except Exception:
            return 0.0, 0.0

    def _start_resource_monitoring(self, operation_name: str, interval: float = 0.5):
        """
        開始背景資源監控

        Args:
            operation_name: 操作名稱
            interval: 採樣間隔（秒）
        """
        def monitor_loop():
            while not self._stop_monitoring.is_set():
                timestamp = time.time()
                cpu, mem = self._get_current_resources()
                with self._lock:
                    self._resource_samples[operation_name].append((timestamp, cpu, mem))
                time.sleep(interval)

        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitoring_thread.start()

    def _stop_resource_monitoring(self):
        """停止背景資源監控"""
        if self._monitoring_thread:
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=1.0)
            self._monitoring_thread = None

    @contextmanager
    def measure(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        上下文管理器：測量代碼塊性能

        使用範例：
            with monitor.measure("影片分析"):
                # 你的代碼
                analyze_video()

        Args:
            name: 操作名稱
            metadata: 額外元數據
        """
        if not self.enabled:
            yield
            return

        # 開始測量
        start_time = time.time()
        cpu_start, mem_start = self._get_current_resources()

        # 啟動背景資源監控
        self._start_resource_monitoring(name)

        metric = PerformanceMetrics(
            name=name,
            start_time=start_time,
            cpu_usage_start=cpu_start,
            memory_usage_start=mem_start,
            metadata=metadata or {}
        )

        with self._lock:
            self.current_operations[name] = metric

        try:
            yield
        finally:
            # 停止背景監控
            self._stop_resource_monitoring()

            # 結束測量
            end_time = time.time()
            cpu_end, mem_end = self._get_current_resources()

            metric.end_time = end_time
            metric.duration = end_time - start_time
            metric.cpu_usage_end = cpu_end
            metric.memory_usage_end = mem_end

            # 計算平均值與峰值
            with self._lock:
                samples = self._resource_samples.get(name, [])
                if samples:
                    cpu_values = [s[1] for s in samples]
                    mem_values = [s[2] for s in samples]
                    metric.cpu_usage_avg = sum(cpu_values) / len(cpu_values)
                    metric.memory_usage_peak = max(mem_values)
                else:
                    metric.cpu_usage_avg = (cpu_start + cpu_end) / 2
                    metric.memory_usage_peak = max(mem_start, mem_end)

                self.current_operations.pop(name, None)
                self.metrics.append(metric)
                self._resource_samples.pop(name, None)

    def track_performance(self, name: Optional[str] = None):
        """
        裝飾器：追蹤函數性能

        使用範例：
            @monitor.track_performance("影片處理")
            def process_video():
                pass

        Args:
            name: 操作名稱（若未提供則使用函數名）
        """
        def decorator(func: Callable) -> Callable:
            operation_name = name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                with self.measure(operation_name):
                    return func(*args, **kwargs)

            return wrapper
        return decorator

    def get_summary(self) -> Dict[str, Any]:
        """
        獲取性能摘要

        Returns:
            包含總體統計的字典
        """
        if not self.metrics:
            return {
                "total_operations": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "total_memory_used": 0.0,
                "avg_cpu_usage": 0.0
            }

        total_time = sum(m.duration for m in self.metrics if m.duration)
        avg_time = total_time / len(self.metrics) if self.metrics else 0

        memory_deltas = [
            (m.memory_usage_end - m.memory_usage_start)
            for m in self.metrics
            if m.memory_usage_start and m.memory_usage_end
        ]
        total_memory = sum(memory_deltas) if memory_deltas else 0

        cpu_values = [
            m.cpu_usage_avg
            for m in self.metrics
            if m.cpu_usage_avg
        ]
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0

        return {
            "total_operations": len(self.metrics),
            "total_time": total_time,
            "avg_time": avg_time,
            "total_memory_used": total_memory,
            "avg_cpu_usage": avg_cpu,
            "operations": [m.name for m in self.metrics]
        }

    def analyze_bottlenecks(self, top_n: int = 10) -> List[BottleneckAnalysis]:
        """
        分析性能瓶頸

        Args:
            top_n: 返回前 N 個瓶頸

        Returns:
            瓶頸分析結果列表（按總耗時降序排列）
        """
        if not self.metrics:
            return []

        # 按操作名稱分組
        operation_groups: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        for metric in self.metrics:
            operation_groups[metric.name].append(metric)

        # 計算總時間
        total_time = sum(m.duration for m in self.metrics if m.duration)
        if total_time == 0:
            return []

        # 分析每個操作
        analyses = []
        for op_name, op_metrics in operation_groups.items():
            durations = [m.duration for m in op_metrics if m.duration]
            if not durations:
                continue

            op_total_time = sum(durations)
            op_count = len(durations)

            # 記憶體影響
            memory_deltas = [
                (m.memory_usage_peak - m.memory_usage_start)
                for m in op_metrics
                if m.memory_usage_peak and m.memory_usage_start
            ]
            memory_impact = sum(memory_deltas) / len(memory_deltas) if memory_deltas else 0

            # CPU 影響
            cpu_values = [m.cpu_usage_avg for m in op_metrics if m.cpu_usage_avg]
            cpu_impact = sum(cpu_values) / len(cpu_values) if cpu_values else 0

            analysis = BottleneckAnalysis(
                operation=op_name,
                total_time=op_total_time,
                percentage=(op_total_time / total_time) * 100,
                count=op_count,
                avg_time=op_total_time / op_count,
                max_time=max(durations),
                min_time=min(durations),
                memory_impact=memory_impact,
                cpu_impact=cpu_impact
            )
            analyses.append(analysis)

        # 按總耗時降序排列
        analyses.sort(key=lambda x: x.total_time, reverse=True)

        return analyses[:top_n]

    def print_summary(self):
        """列印性能摘要（使用 Rich 格式化）"""
        summary = self.get_summary()

        if RICH_AVAILABLE and console:
            table = Table(title="⚡ 性能監控摘要", show_header=True, header_style="bold bright_magenta")
            table.add_column("指標", style="bright_magenta")
            table.add_column("數值", style="#DDA0DD")

            table.add_row("總操作數", f"{summary['total_operations']:,}")
            table.add_row("總耗時", f"{summary['total_time']:.2f} 秒")
            table.add_row("平均耗時", f"{summary['avg_time']:.2f} 秒")
            table.add_row("記憶體使用", f"{summary['total_memory_used']:.2f} MB")
            table.add_row("平均 CPU 使用率", f"{summary['avg_cpu_usage']:.1f}%")

            console.print(table)
        else:
            print("\n⚡ 性能監控摘要")
            print("=" * 50)
            print(f"總操作數: {summary['total_operations']:,}")
            print(f"總耗時: {summary['total_time']:.2f} 秒")
            print(f"平均耗時: {summary['avg_time']:.2f} 秒")
            print(f"記憶體使用: {summary['total_memory_used']:.2f} MB")
            print(f"平均 CPU 使用率: {summary['avg_cpu_usage']:.1f}%")
            print("=" * 50)

    def print_bottleneck_report(self, top_n: int = 10):
        """
        列印瓶頸分析報告

        Args:
            top_n: 顯示前 N 個瓶頸
        """
        bottlenecks = self.analyze_bottlenecks(top_n=top_n)

        if not bottlenecks:
            if RICH_AVAILABLE and console:
                console.print("[#DDA0DD]沒有性能數據可供分析[/#DDA0DD]")
            else:
                print("沒有性能數據可供分析")
            return

        if RICH_AVAILABLE and console:
            table = Table(
                title=f"🔍 瓶頸分析報告（Top {len(bottlenecks)}）",
                show_header=True,
                header_style="bold #DDA0DD"
            )
            console_width = console.width or 120
            table.add_column("排名", style="bright_magenta", width=max(6, int(console_width * 0.05)))
            table.add_column("操作", style="#DDA0DD")
            table.add_column("總耗時", style="red")
            table.add_column("占比", style="red")
            table.add_column("次數", style="green")
            table.add_column("平均", style="bright_magenta")
            table.add_column("記憶體", style="#DDA0DD")
            table.add_column("CPU", style="bright_magenta")

            for idx, b in enumerate(bottlenecks, 1):
                table.add_row(
                    f"#{idx}",
                    b.operation,
                    f"{b.total_time:.2f}s",
                    f"{b.percentage:.1f}%",
                    f"{b.count}",
                    f"{b.avg_time:.2f}s",
                    f"{b.memory_impact:.1f}MB",
                    f"{b.cpu_impact:.1f}%"
                )

            console.print(table)

            # 建議
            console.print("\n[bold #DDA0DD]💡 優化建議：[/bold #DDA0DD]")
            for idx, b in enumerate(bottlenecks[:3], 1):
                suggestion = self._get_optimization_suggestion(b)
                console.print(f"  {idx}. {b.operation}: {suggestion}")
        else:
            print(f"\n🔍 瓶頸分析報告（Top {len(bottlenecks)}）")
            print("=" * 100)
            print(f"{'排名':<6} {'操作':<30} {'總耗時':<12} {'占比':<8} {'次數':<6} {'平均':<10} {'記憶體':<10} {'CPU':<8}")
            print("-" * 100)

            for idx, b in enumerate(bottlenecks, 1):
                print(f"#{idx:<5} {b.operation:<30} {b.total_time:>10.2f}s {b.percentage:>6.1f}% "
                      f"{b.count:>6} {b.avg_time:>8.2f}s {b.memory_impact:>8.1f}MB {b.cpu_impact:>6.1f}%")

            print("=" * 100)

    def _get_optimization_suggestion(self, bottleneck: BottleneckAnalysis) -> str:
        """
        根據瓶頸分析提供優化建議

        Args:
            bottleneck: 瓶頸分析結果

        Returns:
            優化建議字串
        """
        suggestions = []

        # 時間建議
        if bottleneck.percentage > 50:
            suggestions.append("此操作占用超過 50% 總時間，應優先優化")
        elif bottleneck.avg_time > 10:
            suggestions.append("平均耗時較長，考慮並行處理或快取")

        # 記憶體建議
        if bottleneck.memory_impact > 500:
            suggestions.append("記憶體使用量大，考慮分批處理")
        elif bottleneck.memory_impact > 100:
            suggestions.append("注意記憶體使用，可能需要優化資料結構")

        # CPU 建議
        if bottleneck.cpu_impact > 80:
            suggestions.append("CPU 使用率高，考慮使用多執行緒")

        # 執行次數建議
        if bottleneck.count > 100:
            suggestions.append("執行次數多，考慮批次處理或快取結果")

        return "；".join(suggestions) if suggestions else "運作正常"

    def export_report(self, output_path: str = "performance_report.json"):
        """
        匯出性能報告為 JSON 檔案

        Args:
            output_path: 輸出檔案路徑
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "bottlenecks": [
                {
                    "operation": b.operation,
                    "total_time": b.total_time,
                    "percentage": b.percentage,
                    "count": b.count,
                    "avg_time": b.avg_time,
                    "max_time": b.max_time,
                    "min_time": b.min_time,
                    "memory_impact": b.memory_impact,
                    "cpu_impact": b.cpu_impact
                }
                for b in self.analyze_bottlenecks(top_n=20)
            ],
            "detailed_metrics": [
                {
                    "name": m.name,
                    "duration": m.duration,
                    "cpu_usage_avg": m.cpu_usage_avg,
                    "memory_usage_peak": m.memory_usage_peak,
                    "timestamp": datetime.fromtimestamp(m.start_time).isoformat(),
                    "metadata": m.metadata
                }
                for m in self.metrics
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        if RICH_AVAILABLE and console:
            console.print(f"[#DA70D6]✓ 性能報告已匯出：{output_path}[/green]")
        else:
            print(f"✓ 性能報告已匯出：{output_path}")


# 全域監控器實例（單例模式）
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(enabled: bool = True) -> PerformanceMonitor:
    """
    獲取全域性能監控器（單例模式）

    Args:
        enabled: 是否啟用監控

    Returns:
        PerformanceMonitor 實例
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor(enabled=enabled)
    return _global_monitor


def reset_monitor():
    """重置全域監控器"""
    global _global_monitor
    if _global_monitor:
        _global_monitor.clear()


# 便捷函數
def measure(name: str, metadata: Optional[Dict[str, Any]] = None):
    """
    便捷函數：測量性能（上下文管理器）

    使用範例：
        from utils.performance_monitor import measure

        with measure("影片處理"):
            process_video()
    """
    monitor = get_performance_monitor()
    return monitor.measure(name, metadata)


def track_performance(name: Optional[str] = None):
    """
    便捷函數：追蹤性能（裝飾器）

    使用範例：
        from utils.performance_monitor import track_performance

        @track_performance("影片分析")
        def analyze_video():
            pass
    """
    monitor = get_performance_monitor()
    return monitor.track_performance(name)


def print_performance_summary():
    """便捷函數：列印性能摘要"""
    monitor = get_performance_monitor()
    monitor.print_summary()


def print_bottleneck_report(top_n: int = 10):
    """便捷函數：列印瓶頸報告"""
    monitor = get_performance_monitor()
    monitor.print_bottleneck_report(top_n)


def export_performance_report(output_path: str = "performance_report.json"):
    """便捷函數：匯出性能報告"""
    monitor = get_performance_monitor()
    monitor.export_report(output_path)


if __name__ == "__main__":
    # 測試性能監控器
    monitor = get_performance_monitor()

    # 測試 1: 使用上下文管理器
    with monitor.measure("測試操作 1"):
        time.sleep(1.0)
        # 模擬一些 CPU 密集操作
        sum([i**2 for i in range(1000000)])

    # 測試 2: 使用裝飾器
    @monitor.track_performance("測試操作 2")
    def test_function():
        time.sleep(0.5)
        return "完成"

    test_function()
    test_function()

    # 測試 3: 多次執行
    for i in range(3):
        with monitor.measure("重複操作"):
            time.sleep(0.2)

    # 顯示結果
    print("\n" + "=" * 50)
    monitor.print_summary()
    print()
    monitor.print_bottleneck_report()
    print()

    # 匯出報告
    monitor.export_report("test_performance_report.json")
