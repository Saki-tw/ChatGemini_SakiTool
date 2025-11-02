#!/usr/bin/env python3
"""
全域 print 追蹤器
在程式啟動時導入此模組，可以追蹤所有 print 調用
"""
import sys
import builtins
import traceback

# 保存原始 print
_original_print = builtins.print
_print_count = {}

def traced_print(*args, **kwargs):
    """追蹤版 print"""
    message = ' '.join(str(arg) for arg in args)

    # 只追蹤包含「沒有符合條件的任務」的訊息
    if '沒有符合條件' in message or '沒有符合' in message:
        stack = traceback.extract_stack()
        # 獲取調用者位置（跳過這個函數本身）
        caller = stack[-2]
        location = f"{caller.filename}:{caller.lineno}"

        _print_count[location] = _print_count.get(location, 0) + 1

        _original_print(f"\n{'='*70}")
        _original_print(f"🔍 偵測到「沒有符合條件的任務」訊息 (#{sum(_print_count.values())})")
        _original_print(f"{'='*70}")
        _original_print(f"調用位置: {location} in {caller.name}()")
        _original_print(f"訊息內容: {repr(message)}")
        _original_print(f"\n調用堆疊 (最近 5 層):")
        for i, frame in enumerate(stack[-6:-1], 1):
            _original_print(f"  {i}. {frame.filename}:{frame.lineno} in {frame.name}()")
            _original_print(f"     {frame.line}")
        _original_print(f"{'='*70}\n")

    return _original_print(*args, **kwargs)

def install():
    """安裝追蹤器"""
    builtins.print = traced_print
    _original_print("✅ Print 追蹤器已安裝")

def uninstall():
    """卸載追蹤器"""
    builtins.print = _original_print

def get_statistics():
    """獲取統計資訊"""
    if not _print_count:
        _original_print("\n✅ 沒有偵測到「沒有符合條件的任務」訊息")
        return

    _original_print("\n" + "="*70)
    _original_print("📊 Print 統計報告")
    _original_print("="*70)
    for location, count in sorted(_print_count.items(), key=lambda x: -x[1]):
        _original_print(f"  {location}: {count} 次")
    _original_print(f"\n總計: {sum(_print_count.values())} 次")
    _original_print("="*70)

# 自動安裝（當被導入時）
if __name__ != "__main__":
    install()
