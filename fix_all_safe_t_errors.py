#!/usr/bin/env python3
"""
批次修復所有 Python 檔案中的 safe_t() 語法錯誤
"""

import re
import glob
import sys

def fix_safe_t_errors(content):
    """修復 safe_t() 調用中的語法錯誤"""

    # 模式 1: 移除格式說明符 (e.g., cost_twd=cost_twd -> cost_twd=cost_twd)
    content = re.sub(r'(\w+):[,\.\d%]+\s*=\s*\1(?::[,\.\d%]+)?', r'\1=\1', content)

    # 模式 2: 提取字典鍵訪問 (e.g., stats['key']=stats['key'] -> key=stats['key'])
    content = re.sub(r"(\w+)\['(\w+)'\]\s*=\s*\1\['(\w+)'\]", r'\2=\1["\2"]', content)

    # 模式 3: 修復函數調用在參數名中 (e.g., len(items)=len(items) -> items_count=len(items))
    content = re.sub(r'len\((\w+)\)\s*=\s*len\(\1\)', r'\1_count=len(\1)', content)

    # 模式 4: 修復切片操作 (e.g., text[:8]=text[:8] -> text_short=text[:8])
    content = re.sub(r'(\w+)\[:(\d+)\]\s*=\s*\1\[:(\d+)\]', r'\1_short=\1[:\2]', content)

    # 模式 5: 修復 f-string 模板中的字典訪問，改為使用參數
    # 在 fallback 字串中找到 {stats['key']} 並替換為 {key}
    def replace_dict_in_template(match):
        full_call = match.group(0)
        # 尋找 fallback 字串中的字典訪問
        fallback_match = re.search(r"fallback\s*=\s*['\"]([^'\"]*)['\"]", full_call)
        if fallback_match:
            fallback = fallback_match.group(1)
            # 替換 {dict['key']} 為 {key}
            new_fallback = re.sub(r"\{(\w+)\['(\w+)'\]\}", r'{\2}', fallback)
            full_call = full_call.replace(fallback, new_fallback)
        return full_call

    # 這個較複雜，我們只針對明顯的案例

    return content

def process_file(filepath):
    """處理單個檔案"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original = f.read()

        fixed = fix_safe_t_errors(original)

        if fixed != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed)
            print(f"✓ 已修復: {filepath}")
            return True
        else:
            print(f"  跳過（無需修改）: {filepath}")
            return False
    except Exception as e:
        print(f"✗ 錯誤: {filepath} - {e}")
        return False

def main():
    """主函數"""
    print("=== 批次修復 safe_t() 語法錯誤 ===\n")

    # 找出所有 Python 檔案
    patterns = [
        'gemini_*.py',
        'CodeGemini/**/*.py',
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))

    # 去重
    files = list(set(files))

    print(f"找到 {len(files)} 個 Python 檔案\n")

    fixed_count = 0
    for filepath in sorted(files):
        if process_file(filepath):
            fixed_count += 1

    print(f"\n=== 完成 ===")
    print(f"已修復: {fixed_count} 個檔案")
    print(f"總計: {len(files)} 個檔案")

if __name__ == '__main__':
    main()
