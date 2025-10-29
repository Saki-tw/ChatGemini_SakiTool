#!/usr/bin/env python3
"""
實際啟動時間測量工具
測量 gemini_chat.py 從開始到可以接受輸入的完整時間
"""
import time
import sys
import subprocess

print("=" * 80)
print("測量 ChatGemini 實際啟動時間")
print("=" * 80)

# 記錄開始時間
start_time = time.time()

# 執行 gemini_chat.py 並測量到第一個 input 提示的時間
# 使用 timeout 避免卡住
result = subprocess.run(
    ['python3', 'gemini_chat.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    timeout=30,
    input='\n'  # 立即輸入換行,讓它盡快停止
)

# 記錄結束時間
end_time = time.time()
elapsed = end_time - start_time

# 解析輸出
output_lines = result.stdout.split('\n')

print(f"\n總啟動時間: {elapsed:.2f} 秒\n")
print("啟動過程輸出:")
print("-" * 80)

# 分析輸出,找出耗時操作
loading_messages = []
for line in output_lines[:50]:  # 只看前50行
    if line.strip():
        print(line)
        if any(keyword in line for keyword in ['✅', '⚠️', '載入', '啟用', 'MCP', 'CodeGemini']):
            loading_messages.append(line)

print("-" * 80)
print(f"\n檢測到的載入操作 ({len(loading_messages)} 個):")
for msg in loading_messages:
    print(f"  {msg}")

print("\n" + "=" * 80)
