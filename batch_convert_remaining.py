#!/usr/bin/env python3
"""
批次轉換剩餘 CodeGemini 子模組的硬編碼中文
"""
import re
from pathlib import Path

# 要處理的檔案列表
FILES_TO_PROCESS = [
    'CodeGemini/config_manager.py',
    'CodeGemini/context/builder.py',
    'CodeGemini/commands/loader.py',
    'CodeGemini/context/scanner.py',
    'CodeGemini/core/approval.py',
]

def extract_chinese_strings(file_path):
    """提取檔案中的所有硬編碼中文字串"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    chinese_strings = []
    for i, line in enumerate(lines, 1):
        if 'print' in line and re.search(r'[\u4e00-\u9fff]', line):
            if 'safe_t' not in line and not line.strip().startswith('#'):
                chinese_strings.append((i, line.rstrip()))

    return chinese_strings

def generate_translation_key(module_name, chinese_text, index):
    """生成語義化的翻譯鍵"""
    # 移除 Rich 標記
    clean_text = re.sub(r'\[/?[^\]]+\]', '', chinese_text)

    # 根據關鍵字生成鍵名
    if '載入' in clean_text or '讀取' in clean_text:
        return f"{module_name}.load.item{index}"
    elif '保存' in clean_text or '儲存' in clean_text:
        return f"{module_name}.save.item{index}"
    elif '成功' in clean_text or '完成' in clean_text or '✓' in clean_text or '✅' in clean_text:
        return f"{module_name}.success.item{index}"
    elif '失敗' in clean_text or '錯誤' in clean_text or '✗' in clean_text or '❌' in clean_text:
        return f"{module_name}.error.item{index}"
    elif '警告' in clean_text or '⚠️' in clean_text:
        return f"{module_name}.warning.item{index}"
    elif '提示' in clean_text or '💡' in clean_text:
        return f"{module_name}.hint.item{index}"
    else:
        return f"{module_name}.msg.item{index}"

def convert_print_to_safe_t(line, key, original_text):
    """將 print 語句轉換為 safe_t 調用"""
    # 檢測是否有變數
    if 'f"' in line or "f'" in line:
        # 有 f-string，需要處理變數
        # 提取變數
        vars_in_text = re.findall(r'\{([^}]+)\}', original_text)

        # 替換變數為參數化格式
        parameterized = original_text
        format_args = []

        for var in vars_in_text:
            # 簡化變數名
            simple_var = var.split('.')[-1].split('[')[0].split('(')[0]
            parameterized = parameterized.replace(f'{{{var}}}', f'{{{simple_var}}}', 1)
            format_args.append(f'{simple_var}={var}')

        if format_args:
            format_str = ', '.join(format_args)
            return f'safe_t("{key}", fallback="{parameterized}").format({format_str})'
        else:
            return f'safe_t("{key}", fallback="{original_text}")'
    else:
        # 純文字
        return f'safe_t("{key}", fallback="{original_text}")'

def process_file(file_path):
    """處理單個檔案"""
    print(f"\n處理: {file_path}")

    module_name = Path(file_path).stem

    # 讀取檔案
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 檢查是否已導入 safe_t
    if 'from utils.i18n import safe_t' not in content and 'from utils import safe_t' not in content:
        print(f"  ⚠️ 檔案未導入 safe_t，跳過")
        return 0

    # 提取硬編碼
    chinese_strings = extract_chinese_strings(file_path)

    if not chinese_strings:
        print(f"  ✓ 無硬編碼，跳過")
        return 0

    print(f"  發現 {len(chinese_strings)} 處硬編碼")

    # 逐行轉換
    converted = 0
    for idx, (line_num, line) in enumerate(chinese_strings[:30], 1):  # 限制每個檔案處理前30處
        # 提取 print 語句中的文字
        match = re.search(r'print\((.*)\)', line)
        if not match:
            continue

        print_content = match.group(1)

        # 提取引號內的內容
        text_match = re.search(r'[f]?["\']([^"\']+)["\']', print_content)
        if not text_match:
            continue

        original_text = text_match.group(1)

        # 生成翻譯鍵
        key = generate_translation_key(module_name, original_text, idx)

        # 生成新的語句
        new_statement = convert_print_to_safe_t(line, key, original_text)

        # 替換
        # 注意：這是簡化版本，實際應該更精確地匹配整行
        old_line = line.strip()
        new_line = line.replace(print_content, new_statement)

        if old_line in content:
            content = content.replace(old_line, new_line.strip())
            converted += 1

    # 寫回檔案
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓ 已轉換 {converted} 處")
    return converted

def main():
    """主函數"""
    print("=" * 70)
    print("批次轉換 CodeGemini 子模組硬編碼")
    print("=" * 70)

    total_converted = 0

    for file_path in FILES_TO_PROCESS:
        if not Path(file_path).exists():
            print(f"\n✗ 檔案不存在: {file_path}")
            continue

        converted = process_file(file_path)
        total_converted += converted

    print(f"\n{'=' * 70}")
    print(f"總計轉換: {total_converted} 處")
    print(f"{'=' * 70}")

if __name__ == '__main__':
    main()
