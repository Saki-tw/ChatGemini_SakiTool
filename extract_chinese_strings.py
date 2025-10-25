#!/usr/bin/env python3
"""
中文字串提取工具

從所有 gemini_*.py 模組中提取中文字串，並分類整理。

作者: Saki-tw (with Claude Code)
日期: 2025-10-25
"""

import re
from pathlib import Path
from collections import defaultdict
import json

def extract_chinese_strings(file_path):
    """
    提取檔案中的中文字串

    Args:
        file_path: 檔案路徑

    Returns:
        中文字串列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 讀取失敗 {file_path}: {e}")
        return []

    # 匹配引號內包含中文的字串
    # 支援單引號和雙引號
    patterns = [
        r'["\']([^"\']*[\u4e00-\u9fa5]+[^"\']*)["\']',  # 基本中文字串
        r'f["\']([^"\']*[\u4e00-\u9fa5]+[^"\']*)["\']',  # f-string
    ]

    strings = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        strings.update(matches)

    # 過濾掉過長或過短的字串
    filtered = [s for s in strings if 1 < len(s) < 200]

    return sorted(filtered)

def categorize_string(string):
    """
    根據字串內容自動分類

    Returns:
        分類名稱
    """
    # 關鍵字映射
    keywords = {
        'common': ['是', '否', '確定', '取消', '繼續', '返回', '退出', '離開', '成功', '失敗', '錯誤', '警告'],
        'chat': ['歡迎', '對話', '訊息', '輸入', '回應', '思考', '生成', '模型'],
        'pricing': ['成本', '費用', '價格', '計價', '累計', '節省', '折扣', 'tokens', 'Token'],
        'cache': ['快取', '緩存', '儲存', 'cache', 'Cache'],
        'checkpoint': ['檢查點', '回溯', '恢復', '保存', '快照', 'checkpoint', 'Checkpoint'],
        'errors': ['錯誤', '失敗', '異常', '無效', '找不到', '不存在'],
        'media': ['圖片', '影片', '音訊', '視訊', '媒體', '檔案', '上傳', '下載', '處理'],
        'file': ['檔案', '路徑', '目錄', '資料夾'],
        'config': ['配置', '設定', '選項'],
    }

    string_lower = string.lower()

    for category, words in keywords.items():
        for word in words:
            if word.lower() in string_lower:
                return category

    return 'other'

def main():
    print("=" * 60)
    print("中文字串提取工具")
    print("=" * 60)

    # 取得所有 gemini_*.py 檔案
    gemini_files = sorted(Path('.').glob('gemini_*.py'))

    print(f"\n找到 {len(gemini_files)} 個模組")

    # 提取所有字串
    all_strings = defaultdict(list)
    file_stats = {}

    for py_file in gemini_files:
        strings = extract_chinese_strings(py_file)
        file_stats[py_file.name] = len(strings)

        # 分類
        for s in strings:
            category = categorize_string(s)
            all_strings[category].append({
                'string': s,
                'file': py_file.name
            })

        print(f"  ✓ {py_file.name:35s} {len(strings):4d} 個中文字串")

    # 統計
    print(f"\n" + "=" * 60)
    print("統計結果")
    print("=" * 60)

    total_strings = sum(len(v) for v in all_strings.values())
    print(f"總字串數: {total_strings}")
    print(f"\n分類統計:")

    for category, items in sorted(all_strings.items(), key=lambda x: len(x[1]), reverse=True):
        unique_strings = len(set(item['string'] for item in items))
        print(f"  {category:15s}: {unique_strings:4d} 個（重複後 {len(items)} 個）")

    # 匯出到 JSON
    output_file = 'chinese_strings_extracted.json'

    # 去重
    categorized_strings = {}
    for category, items in all_strings.items():
        unique = {}
        for item in items:
            string = item['string']
            if string not in unique:
                unique[string] = []
            unique[string].append(item['file'])

        categorized_strings[category] = [
            {'string': k, 'files': v} for k, v in unique.items()
        ]

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total': total_strings,
            'file_stats': file_stats,
            'categorized': categorized_strings
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 結果已儲存至: {output_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
