#!/usr/bin/env python3
"""
分析 gemini_chat.py 啟動速度
追蹤所有模組載入時間，找出瓶頸
"""
import sys
import time
from collections import defaultdict

# 記錄所有導入
original_import = __builtins__.__import__
imports = []
import_tree = defaultdict(list)
current_importing = []

def tracking_import(name, *args, **kwargs):
    """追蹤並計時所有模組導入"""
    parent = current_importing[-1] if current_importing else None
    current_importing.append(name)

    start = time.time()
    try:
        result = original_import(name, *args, **kwargs)
        elapsed = (time.time() - start) * 1000  # ms

        imports.append((name, elapsed, parent))
        if parent:
            import_tree[parent].append((name, elapsed))

        return result
    finally:
        current_importing.pop()

# 開始追蹤
__builtins__.__import__ = tracking_import

print("開始分析 gemini_chat.py 啟動速度...\n")

# 導入主模組
start_total = time.time()
try:
    import gemini_chat
    success = True
except Exception as e:
    success = False
    error = str(e)
total_time = (time.time() - start_total) * 1000

# 還原
__builtins__.__import__ = original_import

# 分析結果
print(f"{'='*80}")
print(f"gemini_chat.py 啟動分析報告")
print(f"{'='*80}\n")

if not success:
    print(f"❌ 載入失敗: {error}\n")
else:
    print(f"✅ 總載入時間: {total_time:.0f} ms ({total_time/1000:.2f} 秒)\n")

# 統計分類
categories = {
    '標準庫': [],
    'Google/Gemini': [],
    'Rich/UI': [],
    '專案模組': [],
    '第三方庫': [],
}

for name, ms, parent in imports:
    if ms < 1:  # 忽略太快的
        continue

    if name in ['google', 'genai'] or name.startswith('google.'):
        categories['Google/Gemini'].append((name, ms))
    elif name.startswith('rich.') or name == 'rich':
        categories['Rich/UI'].append((name, ms))
    elif name.startswith('gemini_') or name in ['utils', 'config_unified', 'conversation_history_manager', 'interactive_language_menu']:
        categories['專案模組'].append((name, ms))
    elif name in sys.stdlib_module_names or name.startswith(('os', 'sys', 'time', 'json', 're', 'pathlib', 'datetime', 'logging')):
        categories['標準庫'].append((name, ms))
    else:
        categories['第三方庫'].append((name, ms))

# 顯示分類統計
print("=" * 80)
print("模組載入時間分類統計")
print("=" * 80)

for category, items in categories.items():
    if not items:
        continue

    total_cat = sum(ms for _, ms in items)
    percentage = (total_cat / total_time) * 100 if total_time > 0 else 0

    print(f"\n【{category}】總計: {total_cat:.0f} ms ({percentage:.1f}%)")
    print("-" * 80)

    # 排序並顯示前 5 名
    items.sort(key=lambda x: x[1], reverse=True)
    for i, (name, ms) in enumerate(items[:5], 1):
        print(f"  {i}. {name:<50} {ms:>8.1f} ms")

    if len(items) > 5:
        print(f"  ... 其他 {len(items) - 5} 個模組")

# TOP 20 最慢的模組
print("\n" + "=" * 80)
print("TOP 20 最慢模組")
print("=" * 80)

all_imports = [(name, ms) for name, ms, _ in imports if ms >= 1]
all_imports.sort(key=lambda x: x[1], reverse=True)

print(f"\n{'排名':<5} {'模組名稱':<50} {'耗時 (ms)':>12} {'佔比':>8}")
print("-" * 80)

for i, (name, ms) in enumerate(all_imports[:20], 1):
    percentage = (ms / total_time) * 100 if total_time > 0 else 0
    print(f"{i:<5} {name:<50} {ms:>12.1f} {percentage:>7.1f}%")

# 計算統計
total_slow = sum(ms for _, ms in all_imports)
print(f"\n{'='*80}")
print(f"總計: {len(all_imports)} 個慢速模組 (>1ms)")
print(f"前 10 名合計: {sum(ms for _, ms in all_imports[:10]):.0f} ms ({sum(ms for _, ms in all_imports[:10])/total_time*100:.1f}%)")
print(f"前 20 名合計: {sum(ms for _, ms in all_imports[:20]):.0f} ms ({sum(ms for _, ms in all_imports[:20])/total_time*100:.1f}%)")
print(f"{'='*80}\n")

# 優化建議
print("🔧 優化建議：\n")

# 檢查最慢的模組
top_3 = all_imports[:3]
for name, ms in top_3:
    if ms > 100:
        if 'google' in name or 'genai' in name:
            print(f"⚠️  {name} ({ms:.0f}ms) - 考慮延遲載入 Gemini SDK")
        elif 'sentence_transformers' in name or 'torch' in name:
            print(f"⚠️  {name} ({ms:.0f}ms) - 考慮條件載入（僅在需要時載入）")
        elif name.startswith('gemini_'):
            print(f"⚠️  {name} ({ms:.0f}ms) - 考慮使用動態載入器延遲載入")

# 檢查是否有重量級但非必要的模組
heavy_modules = ['sentence_transformers', 'torch', 'transformers', 'numpy', 'pandas']
loaded_heavy = [name for name, _ in all_imports if any(h in name for h in heavy_modules)]
if loaded_heavy:
    print(f"\n⚠️  檢測到重量級模組: {', '.join(set(loaded_heavy))}")
    print("   建議：僅在功能實際使用時才載入這些模組")

print("\n✅ 分析完成！")
