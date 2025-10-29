#!/usr/bin/env python3
"""
收集所有使用的 i18n 鍵並生成語言包條目
"""
import re
from pathlib import Path
from collections import defaultdict

def collect_keys_from_file(filepath: Path) -> list:
    """從檔案中收集所有 safe_t 調用的鍵"""
    keys = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 safe_t('key', fallback='text', ...)
    pattern = r"safe_t\('([^']+)',\s*fallback='([^']+)'"
    matches = re.findall(pattern, content)

    for key, fallback in matches:
        keys.append((key, fallback))

    return keys

def main():
    """主程式"""
    project_root = Path.cwd()

    # 收集所有鍵
    all_keys = defaultdict(set)

    # 掃描所有 Python 檔案
    for filepath in project_root.rglob('*.py'):
        if 'venv' in str(filepath) or '__pycache__' in str(filepath):
            continue

        keys = collect_keys_from_file(filepath)
        for key, fallback in keys:
            all_keys[key].add(fallback)

    # 按類別組織
    organized = defaultdict(dict)
    for key, fallbacks in sorted(all_keys.items()):
        parts = key.split('.')
        if len(parts) >= 2:
            category = parts[0]
            subkey = '.'.join(parts[1:])
            # 取第一個 fallback 作為預設值
            organized[category][subkey] = list(fallbacks)[0]
        else:
            organized['common'][key] = list(fallbacks)[0]

    # 生成 YAML 格式
    print("# 自動收集的翻譯鍵")
    print()

    for category in sorted(organized.keys()):
        print(f"{category}:")
        for subkey, fallback in sorted(organized[category].items()):
            # 移除 Rich 標籤用於顯示
            clean_fallback = re.sub(r'\[/?[^\]]+\]', '', fallback)
            # 移除表情符號
            clean_fallback = re.sub(r'[\U0001F300-\U0001F9FF]', '', clean_fallback)
            clean_fallback = clean_fallback.strip()

            # 如果有參數，顯示完整版本
            if '{' in fallback:
                print(f'  {subkey}: "{fallback}"')
            else:
                print(f'  {subkey}: "{clean_fallback}"')
        print()

    # 統計
    total_keys = sum(len(subkeys) for subkeys in organized.values())
    print(f"# 總計: {total_keys} 個翻譯鍵")
    print(f"# 類別: {len(organized)} 個")

if __name__ == '__main__':
    main()
