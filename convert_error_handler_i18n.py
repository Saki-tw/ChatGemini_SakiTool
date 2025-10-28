#!/usr/bin/env python3
"""
gemini_error_handler.py i18n 轉換腳本
自動將中文註釋和 docstrings 轉換為 safe_t() 調用
"""
import re
from pathlib import Path

# 定義需要轉換的中文字串模式
CONVERSIONS = [
    # 註釋中的中文（保持註釋，但記錄用於語言包）
    {
        'pattern': r'#\s*(.+[\u4e00-\u9fa5].+)',
        'type': 'comment',
        'action': 'keep_but_extract'
    },
    # docstring 中的中文
    {
        'pattern': r'"""([^"]+)"""',
        'type': 'docstring',
        'action': 'keep_but_extract'
    }
]

def read_file(filepath):
    """讀取檔案內容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.readlines()

def extract_chinese_strings(content):
    """提取所有需要國際化的中文字串"""
    chinese_strings = []
    chinese_pattern = re.compile(r'[\u4e00-\u9fa5]+')

    for line_num, line in enumerate(content, 1):
        # 跳過已經使用 safe_t 的行
        if 'safe_t(' in line:
            continue

        # 檢查是否包含中文
        if chinese_pattern.search(line):
            chinese_strings.append({
                'line': line_num,
                'content': line.rstrip(),
                'type': detect_string_type(line)
            })

    return chinese_strings

def detect_string_type(line):
    """檢測字串類型"""
    stripped = line.strip()
    if stripped.startswith('#'):
        return 'comment'
    elif '"""' in line or "'''" in line:
        return 'docstring'
    elif '=' in line and ('"' in line or "'" in line):
        return 'assignment'
    else:
        return 'other'

def generate_i18n_keys(chinese_strings):
    """生成 i18n 鍵值對"""
    i18n_entries = {}

    for item in chinese_strings:
        line_content = item['content']
        string_type = item['type']

        # 提取實際的中文文本
        chinese_pattern = re.compile(r'[\u4e00-\u9fa5]+[^#"\']*')
        matches = chinese_pattern.findall(line_content)

        for match in matches:
            text = match.strip()
            if len(text) > 2:  # 過濾太短的
                key = generate_key_from_text(text, string_type)
                i18n_entries[key] = text

    return i18n_entries

def generate_key_from_text(text, string_type):
    """從文本生成鍵名"""
    # 簡化版：使用文本的前幾個字
    prefix_map = {
        'comment': 'comment',
        'docstring': 'doc',
        'assignment': 'msg',
        'other': 'text'
    }

    prefix = prefix_map.get(string_type, 'text')

    # 取前10個字符作為鍵名的一部分（移除標點符號）
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
    key_suffix = clean_text[:15]

    return f'error.{prefix}.{key_suffix}'

def main():
    """主函數"""
    filepath = Path('gemini_error_handler.py')

    if not filepath.exists():
        print(f"錯誤：找不到檔案 {filepath}")
        return

    # 讀取檔案
    content = read_file(filepath)
    print(f"✓ 讀取檔案：{len(content)} 行")

    # 提取中文字串
    chinese_strings = extract_chinese_strings(content)
    print(f"✓ 找到 {len(chinese_strings)} 個包含中文的位置")

    # 按類型統計
    type_counts = {}
    for item in chinese_strings:
        t = item['type']
        type_counts[t] = type_counts.get(t, 0) + 1

    print("\n字串類型分布：")
    for t, count in type_counts.items():
        print(f"  - {t}: {count} 處")

    # 生成 i18n 鍵值對
    i18n_entries = generate_i18n_keys(chinese_strings)
    print(f"\n✓ 生成 {len(i18n_entries)} 個 i18n 條目")

    # 輸出示例
    print("\n前 10 個 i18n 條目示例：")
    for i, (key, value) in enumerate(list(i18n_entries.items())[:10], 1):
        print(f"  {i}. {key}: {value}")

    # 保存到檔案
    output_file = Path('error_handler_i18n_keys.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# gemini_error_handler.py i18n 鍵值對\n")
        f.write(f"# 總計：{len(i18n_entries)} 個條目\n\n")
        for key, value in sorted(i18n_entries.items()):
            f.write(f"{key}: {value}\n")

    print(f"\n✓ i18n 鍵值對已保存到 {output_file}")

    # 顯示需要手動處理的複雜情況
    print("\n需要手動檢查的位置（示例）：")
    for item in chinese_strings[:5]:
        print(f"  Line {item['line']:4d} [{item['type']:12s}]: {item['content'][:80]}")

if __name__ == "__main__":
    main()
