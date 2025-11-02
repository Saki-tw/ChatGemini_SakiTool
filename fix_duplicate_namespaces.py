#!/usr/bin/env python3
"""
修復語言檔案中的重複命名空間問題

執行方式:
    python3 fix_duplicate_namespaces.py
"""

import yaml
import os
from collections import defaultdict
from pathlib import Path

def merge_duplicate_namespaces(yaml_file):
    """
    合併 YAML 檔案中的重複命名空間

    Args:
        yaml_file: YAML 檔案路徑
    """
    print(f"\n處理檔案: {yaml_file}")

    # 讀取原始檔案（保持順序）
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用 safe_load 會遺失順序，所以手動處理
    lines = content.split('\n')

    # 儲存合併後的內容
    merged = defaultdict(list)
    current_namespace = None
    current_block = []
    header_lines = []
    in_header = True

    for i, line in enumerate(lines):
        # 檢查是否為頂層命名空間 (不含縮排的 key:)
        if line and not line.startswith(' ') and not line.startswith('#') and ':' in line:
            in_header = False
            namespace = line.split(':')[0].strip()

            # 如果有上一個 block，儲存它
            if current_namespace:
                merged[current_namespace].append('\n'.join(current_block))

            # 開始新的 block
            current_namespace = namespace
            current_block = [line]
        elif in_header:
            # 儲存檔案頭部
            header_lines.append(line)
        elif current_namespace:
            # 屬於當前命名空間的內容
            current_block.append(line)

    # 儲存最後一個 block
    if current_namespace:
        merged[current_namespace].append('\n'.join(current_block))

    # 建立備份
    backup_file = f"{yaml_file}.backup_fix_duplicates"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ 已建立備份: {backup_file}")

    # 統計重複情況
    duplicates = {k: v for k, v in merged.items() if len(v) > 1}
    if duplicates:
        print(f"\n發現 {len(duplicates)} 個重複的命名空間:")
        for ns, blocks in duplicates.items():
            print(f"  • {ns}: {len(blocks)} 次")

    # 重建檔案內容
    output_lines = header_lines
    output_lines.append('')  # 空行分隔

    # 依照第一次出現的順序重建（保持原順序）
    seen = set()
    for line in lines:
        if line and not line.startswith(' ') and not line.startswith('#') and ':' in line:
            namespace = line.split(':')[0].strip()
            if namespace not in seen:
                seen.add(namespace)
                # 合併該命名空間的所有內容
                if len(merged[namespace]) > 1:
                    # 有重複，需要合併
                    print(f"\n合併命名空間: {namespace}")
                    combined_lines = []
                    combined_lines.append(f"{namespace}:")

                    for block in merged[namespace]:
                        block_lines = block.split('\n')[1:]  # 跳過命名空間行
                        # 移除空行和純註釋行
                        block_lines = [l for l in block_lines if l.strip() and not l.strip().startswith('#')]
                        combined_lines.extend(block_lines)

                    output_lines.extend(combined_lines)
                else:
                    # 無重複，直接使用
                    output_lines.extend(merged[namespace][0].split('\n'))

                output_lines.append('')  # 命名空間之間加空行

    # 寫入修復後的檔案
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"\n✓ 已修復並寫入: {yaml_file}")

    # 驗證 YAML 格式
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print("✓ YAML 格式驗證通過")
        return True
    except yaml.YAMLError as e:
        print(f"✗ YAML 格式錯誤: {e}")
        # 恢復備份
        with open(backup_file, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✗ 已從備份恢復: {yaml_file}")
        return False

def main():
    """主函數"""
    locales_dir = Path(__file__).parent / 'locales'

    yaml_files = [
        locales_dir / 'zh_TW.yaml',
        locales_dir / 'en.yaml',
        locales_dir / 'ja.yaml',
        locales_dir / 'ko.yaml',
    ]

    print("=" * 70)
    print("修復語言檔案重複命名空間問題")
    print("=" * 70)

    success_count = 0
    for yaml_file in yaml_files:
        if yaml_file.exists():
            if merge_duplicate_namespaces(yaml_file):
                success_count += 1
        else:
            print(f"\n⚠ 檔案不存在: {yaml_file}")

    print("\n" + "=" * 70)
    print(f"完成！成功修復 {success_count}/{len(yaml_files)} 個檔案")
    print("=" * 70)

if __name__ == "__main__":
    main()
