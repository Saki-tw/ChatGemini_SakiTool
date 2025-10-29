#!/usr/bin/env python3
"""
模組載入分析工具
分析 ChatGemini 啟動時的模組載入情況
"""
import time
import sys
import importlib.util
from pathlib import Path

class ModuleLoadingAnalyzer:
    def __init__(self):
        self.load_times = {}
        self.total_start = time.time()

    def measure_import(self, module_name, import_func):
        """測量單個模組的導入時間"""
        start = time.time()
        try:
            result = import_func()
            elapsed = time.time() - start
            self.load_times[module_name] = {
                'time': elapsed,
                'success': True,
                'error': None
            }
            return result, True
        except Exception as e:
            elapsed = time.time() - start
            self.load_times[module_name] = {
                'time': elapsed,
                'success': False,
                'error': str(e)
            }
            return None, False

    def print_report(self):
        """打印分析報告"""
        total_time = time.time() - self.total_start

        print("\n" + "=" * 80)
        print("ChatGemini 模組載入分析報告")
        print("=" * 80)

        # 按時間排序
        sorted_modules = sorted(
            self.load_times.items(),
            key=lambda x: x[1]['time'],
            reverse=True
        )

        print(f"\n總載入時間: {total_time:.3f} 秒\n")

        print("模組載入時間排行 (由慢到快):")
        print("-" * 80)
        print(f"{'模組名稱':<40} {'時間 (秒)':<15} {'狀態':<10}")
        print("-" * 80)

        for module_name, data in sorted_modules:
            status = "✅ 成功" if data['success'] else f"❌ 失敗: {data['error'][:30]}"
            print(f"{module_name:<40} {data['time']:<15.4f} {status}")

        # 統計
        print("\n" + "=" * 80)
        total_modules = len(self.load_times)
        successful = sum(1 for d in self.load_times.values() if d['success'])
        failed = total_modules - successful

        slow_modules = [m for m, d in self.load_times.items() if d['time'] > 0.1]
        total_slow_time = sum(d['time'] for m, d in self.load_times.items() if d['time'] > 0.1)

        print(f"總模組數: {total_modules}")
        print(f"成功載入: {successful}")
        print(f"載入失敗: {failed}")
        print(f"慢速模組 (>0.1秒): {len(slow_modules)}")
        print(f"慢速模組總時間: {total_slow_time:.3f} 秒")
        print("=" * 80)

        if slow_modules:
            print("\n⚠️  慢速模組列表 (>0.1秒):")
            for module_name in slow_modules:
                data = self.load_times[module_name]
                print(f"  - {module_name}: {data['time']:.4f}秒")

# 創建分析器
analyzer = ModuleLoadingAnalyzer()

print("開始分析 ChatGemini 模組載入...")
print("=" * 80)

# 基礎導入
analyzer.measure_import("sys, os, json", lambda: __import__('sys') and __import__('os') and __import__('json'))
analyzer.measure_import("pathlib", lambda: __import__('pathlib'))
analyzer.measure_import("datetime", lambda: __import__('datetime'))
analyzer.measure_import("typing", lambda: __import__('typing'))
analyzer.measure_import("dotenv", lambda: __import__('dotenv'))
analyzer.measure_import("rich", lambda: __import__('rich'))
analyzer.measure_import("utils.i18n", lambda: __import__('utils.i18n'))

# Google Gemini SDK
analyzer.measure_import("google.genai", lambda: __import__('google.genai'))

# prompt_toolkit
analyzer.measure_import("prompt_toolkit", lambda: __import__('prompt_toolkit'))

# psutil
analyzer.measure_import("psutil", lambda: __import__('psutil'))

# 專案模組
analyzer.measure_import("gemini_module_loader", lambda: __import__('gemini_module_loader'))
analyzer.measure_import("config_unified", lambda: __import__('config_unified'))
analyzer.measure_import("gemini_checkpoint", lambda: __import__('gemini_checkpoint'))
analyzer.measure_import("interactive_language_menu", lambda: __import__('interactive_language_menu'))

# 可選模組
analyzer.measure_import("gemini_pricing", lambda: __import__('gemini_pricing'))
analyzer.measure_import("gemini_cache_manager", lambda: __import__('gemini_cache_manager'))
analyzer.measure_import("gemini_file_manager", lambda: __import__('gemini_file_manager'))
analyzer.measure_import("gemini_translator", lambda: __import__('gemini_translator'))
analyzer.measure_import("gemini_media_viewer", lambda: __import__('gemini_media_viewer'))
analyzer.measure_import("CodeGemini", lambda: __import__('CodeGemini'))
analyzer.measure_import("error_fix_suggestions", lambda: __import__('error_fix_suggestions'))
analyzer.measure_import("utils.api_retry", lambda: __import__('utils.api_retry'))
analyzer.measure_import("error_diagnostics", lambda: __import__('error_diagnostics'))
analyzer.measure_import("gemini_smart_triggers", lambda: __import__('gemini_smart_triggers'))
analyzer.measure_import("gemini_tools", lambda: __import__('gemini_tools'))

# 重量級模組 (影音處理)
analyzer.measure_import("gemini_flow_engine", lambda: __import__('gemini_flow_engine'))
analyzer.measure_import("gemini_video_preprocessor", lambda: __import__('gemini_video_preprocessor'))
analyzer.measure_import("gemini_video_compositor", lambda: __import__('gemini_video_compositor'))
analyzer.measure_import("gemini_audio_processor", lambda: __import__('gemini_audio_processor'))
analyzer.measure_import("gemini_subtitle_generator", lambda: __import__('gemini_subtitle_generator'))
analyzer.measure_import("gemini_imagen_generator", lambda: __import__('gemini_imagen_generator'))
analyzer.measure_import("gemini_video_effects", lambda: __import__('gemini_video_effects'))

# 打印報告
analyzer.print_report()

# 建議
print("\n💡 優化建議:")
print("=" * 80)
print("1. 將慢速模組改為延遲載入 (lazy loading)")
print("2. 只在使用者觸發相關功能時才載入對應模組")
print("3. 使用 config.py 控制預設不載入重量級模組")
print("4. 考慮使用 importlib 動態導入")
print("=" * 80)
