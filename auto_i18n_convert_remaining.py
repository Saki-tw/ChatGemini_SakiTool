#!/usr/bin/env python3
"""
Phase 5 剩餘檔案自動 i18n 轉換腳本
處理所有 gemini_*.py 檔案
"""
import re
import os
from pathlib import Path

def add_i18n_import(filepath: Path) -> bool:
    """添加 i18n 導入"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 檢查是否已有導入
    if 'from utils.i18n import safe_t' in content:
        return False

    # 尋找適當位置插入
    patterns = [
        (r'(from rich\..*\n)', r'\1from utils.i18n import safe_t\n'),
        (r'(from gemini_pricing import.*\n)', r'\1from utils.i18n import safe_t\n'),
        (r'(import os\nimport sys\n)', r'\1from utils.i18n import safe_t\n'),
        (r'(import json\n)', r'\1from utils.i18n import safe_t\n'),
    ]

    modified = False
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content, count=1)
            modified = True
            break

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def convert_simple_prints(filepath: Path) -> int:
    """轉換簡單的 console.print 語句"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    converted = 0
    new_lines = []

    for line in lines:
        # 跳過已經轉換的
        if 'safe_t(' in line:
            new_lines.append(line)
            continue

        # 模式 1: console.print(f"文字")
        match = re.match(r'(\s*)console\.print\(f?"([^"]*[\u4e00-\u9fff]+[^"]*)"\)', line)
        if match:
            indent = match.group(1)
            text = match.group(2)

            # 提取參數
            params = re.findall(r'\{([^}]+)\}', text)
            if params:
                # 有參數
                key = generate_key(text)
                param_str = ', '.join(f"{p}={p}" for p in params)
                new_line = f"{indent}console.print(safe_t('{key}', fallback='{text}', {param_str}))\n"
            else:
                # 無參數
                key = generate_key(text)
                new_line = f"{indent}console.print(safe_t('{key}', fallback='{text}'))\n"

            new_lines.append(new_line)
            converted += 1
            continue

        # 模式 2: console.print("文字") 帶 Rich 標籤
        match = re.match(r'(\s*)console\.print\("(\[.*?\].*?[\u4e00-\u9fff]+.*?)"\)', line)
        if match:
            indent = match.group(1)
            text = match.group(2)
            key = generate_key(text)
            new_line = f"{indent}console.print(safe_t('{key}', fallback='{text}'))\n"
            new_lines.append(new_line)
            converted += 1
            continue

        new_lines.append(line)

    if converted > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return converted

def generate_key(text: str) -> str:
    """生成翻譯鍵"""
    # 移除 Rich 標籤和表情符號
    clean = re.sub(r'\[/?[^\]]+\]', '', text)
    clean = re.sub(r'[^\w\s\u4e00-\u9fff]', '', clean)

    # 根據關鍵字判斷類別
    if '錯誤' in text or '失敗' in text or '❌' in text:
        category = 'error'
        if '找不到' in text or '未找到' in text:
            return 'error.not_found'
        elif '無法' in text:
            return 'error.cannot_process'
        else:
            return 'error.failed'
    elif '警告' in text or '⚠️' in text:
        return 'common.warning'
    elif '完成' in text or '✓' in text or '✅' in text:
        return 'common.completed'
    elif '處理' in text:
        return 'common.processing'
    elif '載入' in text:
        return 'common.loading'
    elif '分析' in text:
        return 'common.analyzing'
    elif '生成' in text:
        return 'common.generating'
    elif '儲存' in text or '保存' in text:
        return 'common.saving'
    else:
        return 'common.message'

def process_file(filepath: Path) -> dict:
    """處理單個檔案"""
    print(f"處理: {filepath.name}")

    # 1. 添加導入
    import_added = add_i18n_import(filepath)

    # 2. 轉換 print 語句
    converted = convert_simple_prints(filepath)

    return {
        'file': filepath.name,
        'import_added': import_added,
        'converted': converted
    }

def main():
    """主程式"""
    project_root = Path.cwd()

    # 掃描所有 gemini_*.py 檔案
    all_gemini_files = sorted(project_root.glob('gemini_*.py'))

    # 過濾出尚未處理的檔案
    target_files = []
    for filepath in all_gemini_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # 如果檔案有中文但沒有 safe_t 導入，則需要處理
            if 'from utils.i18n import safe_t' not in content and re.search(r'[\u4e00-\u9fff]', content):
                target_files.append(filepath)

    if not target_files:
        print("✅ 所有檔案都已處理完成！")
        return

    print(f"\n找到 {len(target_files)} 個待處理檔案\n")

    total_converted = 0
    total_files = 0

    for filepath in target_files:
        result = process_file(filepath)
        total_converted += result['converted']
        total_files += 1

        print(f"  ✓ 轉換 {result['converted']} 處")

    print(f"\n總計:")
    print(f"  處理檔案: {total_files}")
    print(f"  轉換訊息: {total_converted}")

if __name__ == '__main__':
    main()
