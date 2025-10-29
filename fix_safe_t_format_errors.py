#!/usr/bin/env python3
"""
批量修復 safe_t() 中參數名稱包含格式化語法的錯誤

錯誤模式：
- parameter=parameter=value
- expression=value (其中 expression 包含非標識符字元)

修復策略：
1. 找出所有錯誤的參數
2. 為每個參數生成有效的變數名
3. 在 console.print() 之前插入變數定義
4. 替換參數為有效的變數名
"""

import re
import sys
from pathlib import Path

def fix_safe_t_format_errors(file_path):
    """修復檔案中的 safe_t 格式錯誤"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    lines = content.split('\n')
    new_lines = []
    modified = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # 檢查是否包含 console.print(safe_t(...))
        if 'console.print(safe_t(' in line:
            # 嘗試找出完整的 console.print 語句（可能跨多行）
            full_statement = line
            j = i + 1
            paren_count = line.count('(') - line.count(')')

            while paren_count > 0 and j < len(lines):
                full_statement += '\n' + lines[j]
                paren_count += lines[j].count('(') - lines[j].count(')')
                j += 1

            # 檢查是否有格式化語法錯誤
            # 模式 1: parameter:.2f=value
            pattern1 = r"(\w+):\.\d+f\s*="
            # 模式 2: parameter['key']:.2f=value
            pattern2 = r"\[\'[^']+\'\]:\.\d+f\s*="
            # 模式 3: expression=expression (無效的參數名)
            pattern3 = r"(['\"](?:[^'\"\\]|\\.)*['\"].*?)\s*=\s*\1"

            if re.search(pattern1, full_statement) or re.search(pattern2, full_statement) or re.search(pattern3, full_statement):
                # 找到錯誤，嘗試修復
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent

                # 提取 fallback 字串和參數
                match = re.search(r"fallback=(['\"])((?:[^\1\\]|\\.)*)\1,?\s*(.*)?\)", full_statement, re.DOTALL)
                if match:
                    quote = match.group(1)
                    fallback_str = match.group(2)
                    params_str = match.group(3) if match.group(3) else ""

                    # 找出所有參數
                    param_matches = list(re.finditer(r"(\w+|\[\'[^']+\'\])(:\.\d+f)?\s*=\s*([^,)]+)", params_str))

                    if param_matches:
                        # 生成修復後的程式碼
                        var_defs = []
                        new_params = []

                        for pm in param_matches:
                            param_name = pm.group(1)
                            format_spec = pm.group(2)
                            param_value = pm.group(3).strip()

                            # 如果參數名包含格式化語法或非標識符字元，生成新的變數名
                            if format_spec or not param_name.isidentifier():
                                # 生成乾淨的變數名
                                clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', param_name)
                                if format_spec:
                                    clean_name = clean_name.rstrip('_')

                                # 如果 param_value 中也有格式化語法，去掉它
                                clean_value = re.sub(r':\.\d+f$', '', param_value)

                                var_defs.append(f"{indent_str}{clean_name} = {clean_value}")

                                # 更新 fallback 字串中的佔位符
                                old_placeholder = f"{{{param_name}{format_spec or ''}}}"
                                new_placeholder = f"{{{clean_name}}}"
                                if format_spec:
                                    new_placeholder = f"{{{clean_name}{format_spec}}}"
                                fallback_str = fallback_str.replace(old_placeholder, new_placeholder)

                                new_params.append(f"{clean_name}={clean_name}")
                            else:
                                new_params.append(f"{param_name}={param_value}")

                        # 重構 console.print 語句
                        new_statement = f"{indent_str}console.print(safe_t("

                        # 提取 key
                        key_match = re.search(r"safe_t\((['\"][^'\"]+['\"])", full_statement)
                        if key_match:
                            key = key_match.group(1)
                            new_statement += f"{key}, fallback={quote}{fallback_str}{quote}"

                            if new_params:
                                new_statement += ", " + ", ".join(new_params)

                            new_statement += "))"

                            # 加入變數定義和新語句
                            if var_defs:
                                new_lines.extend(var_defs)
                            new_lines.append(new_statement)
                            modified = True
                            i = j  # 跳過已處理的行
                            continue

        new_lines.append(line)
        i += 1

    if modified:
        new_content = '\n'.join(new_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True

    return False

def main():
    # 要修復的檔案
    files_to_fix = [
        'gemini_imagen_generator.py',
        'gemini_video_analyzer.py',
        'gemini_veo_generator.py',
        'gemini_image_analyzer_async.py',
        'gemini_image_analyzer.py',
        'gemini_async_batch_processor.py',
        'gemini_flow_engine.py'
    ]

    fixed_count = 0
    for filename in files_to_fix:
        file_path = Path(__file__).parent / filename
        if file_path.exists():
            print(f"處理: {filename}")
            if fix_safe_t_format_errors(file_path):
                print(f"  ✅ 已修復")
                fixed_count += 1
            else:
                print(f"  ⊘ 無需修復")
        else:
            print(f"  ❌ 檔案不存在: {filename}")

    print(f"\n修復完成！共修復 {fixed_count} 個檔案")

if __name__ == '__main__':
    main()
