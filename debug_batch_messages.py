#!/usr/bin/env python3
"""
調試批次處理器訊息輸出
追蹤「沒有符合條件的任務」訊息的來源
"""
import os
import sys

# 設置環境
os.environ.setdefault('GOOGLE_API_KEY', 'test_key')

# Monkey patch print 來追蹤所有輸出
original_print = print
call_count = {}

def traced_print(*args, **kwargs):
    message = ' '.join(str(arg) for arg in args)

    # 追蹤「沒有符合條件的任務」訊息
    if '沒有符合條件的任務' in message or '沒有符合' in message:
        import traceback
        stack = traceback.extract_stack()

        # 記錄調用位置
        caller = stack[-2]
        location = f"{caller.filename}:{caller.lineno} in {caller.name}"

        call_count[location] = call_count.get(location, 0) + 1

        original_print(f"\n🔍 發現「沒有符合條件的任務」訊息 (第 {sum(call_count.values())} 次)")
        original_print(f"   調用位置: {location}")
        original_print(f"   完整訊息: {message}")
        original_print(f"   調用堆疊:")
        for frame in stack[-5:-1]:  # 顯示最近 4 層調用
            original_print(f"     {frame.filename}:{frame.lineno} in {frame.name}")
        original_print()

    return original_print(*args, **kwargs)

# 替換 print
__builtins__.print = traced_print

try:
    # 導入 codegemini_manager 並初始化
    from codegemini_manager import get_codegemini_manager

    original_print("\n" + "="*60)
    original_print("開始初始化 CodeGemini Manager...")
    original_print("="*60 + "\n")

    manager = get_codegemini_manager()

    original_print("\n" + "="*60)
    original_print("初始化完成")
    original_print("="*60)

    # 統計
    if call_count:
        original_print("\n📊 訊息統計:")
        for location, count in sorted(call_count.items(), key=lambda x: x[1], reverse=True):
            original_print(f"  {location}: {count} 次")
        original_print(f"\n總計: {sum(call_count.values())} 次")
    else:
        original_print("\n✅ 沒有發現「沒有符合條件的任務」訊息")

except Exception as e:
    import traceback
    original_print(f"\n❌ 錯誤: {e}")
    original_print(f"\n堆疊追蹤:")
    traceback.print_exc()
finally:
    # 恢復原始 print
    __builtins__.print = original_print
