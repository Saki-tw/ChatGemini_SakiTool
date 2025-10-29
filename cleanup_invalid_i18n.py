#!/usr/bin/env python3
"""
i18n 無效調用清理工具

功能:
1. 識別並移除無效的 i18n 調用
2. 將格式化字串（符號、空白、換行）還原為硬編碼
3. 保留真正的使用者可見訊息翻譯
4. 生成清理報告

清理規則:
- 單字符字串: "=", "-", "\n" 等
- 純空白字串: "  ", "    " 等
- 分隔線: "="*50, "-"*70 等
- 縮排空格: 用於格式化的前導空格

作者: Claude Code (Sonnet 4.5)
日期: 2025-10-29
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass

@dataclass
class CleanupResult:
    """清理結果記錄"""
    file_path: str
    line_number: int
    original: str
    cleaned: str
    reason: str

class I18nCleanupTool:
    """i18n 無效調用清理工具"""

    def __init__(self, project_root: str, dry_run: bool = False):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.results: List[CleanupResult] = []
        self.stats = {
            'files_processed': 0,
            'invalid_calls_removed': 0,
            'lines_modified': 0
        }

        # 無效模式：這些應該還原為硬編碼
        # 使用 \b 確保 t 是單獨的函數名，不是其他詞的一部分（如 split）
        self.invalid_patterns = [
            # 單字符
            (r"\b(?:safe_)?t\(['\"]([=\-_\*#\+\.,:;!?])['\"](?:,\s*fallback=['\"].*?['\"])?\)",
             "單字符符號"),

            # 純換行
            (r"\b(?:safe_)?t\(['\"](\\n)['\"](?:,\s*fallback=['\"].*?['\"])?\)",
             "純換行符"),

            # 純空白（2個以上空格）
            (r"\b(?:safe_)?t\(['\"](\s{2,})['\"](?:,\s*fallback=['\"].*?['\"])?\)",
             "純空白"),

            # 僅包含符號和空格的組合（如 "  - ", "  = "）
            (r"\b(?:safe_)?t\(['\"](\s*[=\-_\*#\+\.,:;!?]\s*)['\"](?:,\s*fallback=['\"].*?['\"])?\)",
             "符號+空白組合"),

            # 重複符號（如 "===", "---"）
            (r"\b(?:safe_)?t\(['\"]([=\-_\*#\+]{2,})['\"](?:,\s*fallback=['\"].*?['\"])?\)",
             "重複符號"),
        ]

    def is_invalid_i18n_call(self, line: str) -> Tuple[bool, str, str]:
        """
        檢查是否為無效的 i18n 調用

        Returns:
            (是否無效, 原因, 匹配的字串值)
        """
        for pattern, reason in self.invalid_patterns:
            match = re.search(pattern, line)
            if match:
                return True, reason, match.group(1)
        return False, "", ""

    def extract_fallback_value(self, i18n_call: str) -> str:
        """從 safe_t() 調用中提取 fallback 值"""
        # 匹配 fallback='...' 或 fallback="..."
        fallback_match = re.search(r"fallback=['\"](.+?)['\"]", i18n_call)
        if fallback_match:
            return fallback_match.group(1)

        # 如果沒有 fallback，提取鍵名對應的值（但這是格式化字串，直接返回）
        key_match = re.search(r"['\"]([^'\"]+)['\"]", i18n_call)
        if key_match:
            key_value = key_match.group(1)
            # 如果鍵就是值本身（如 t('=')），直接返回
            if key_value in ['=', '-', '\n', ' ', '_', '*', '#', '+']:
                return key_value

        return ""

    def remove_i18n_call(self, line: str, i18n_call_pattern: str) -> str:
        """
        移除 i18n 調用，還原為硬編碼字串

        策略:
        1. 如果有 fallback，使用 fallback 值
        2. 如果沒有 fallback，提取原始鍵值
        3. 保持行的其餘部分不變
        """
        # 尋找完整的 i18n 調用（使用 word boundary）
        match = re.search(r"\b((?:safe_)?t)\(['\"]([^'\"]+)['\"](?:,\s*fallback=['\"](.+?)['\"])?\)", line)

        if not match:
            return line

        full_call = match.group(0)
        func_name = match.group(1)
        key = match.group(2)
        fallback = match.group(3) if match.group(3) else key

        # 替換整個調用為字串字面量
        cleaned_line = line.replace(full_call, f'"{fallback}"')

        return cleaned_line

    def clean_file(self, file_path: Path) -> int:
        """
        清理單一檔案

        Returns:
            修改的行數
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️  無法讀取 {file_path}: {e}")
            return 0

        modified_lines = 0
        new_lines = []

        for line_num, line in enumerate(lines, 1):
            is_invalid, reason, matched_str = self.is_invalid_i18n_call(line)

            if is_invalid:
                cleaned_line = self.remove_i18n_call(line, matched_str)

                # 記錄清理結果
                result = CleanupResult(
                    file_path=str(file_path.relative_to(self.project_root)),
                    line_number=line_num,
                    original=line.strip(),
                    cleaned=cleaned_line.strip(),
                    reason=reason
                )
                self.results.append(result)

                new_lines.append(cleaned_line)
                modified_lines += 1
                self.stats['invalid_calls_removed'] += 1
            else:
                new_lines.append(line)

        # 寫回檔案（除非是 dry run）
        if modified_lines > 0 and not self.dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            except Exception as e:
                print(f"❌ 無法寫入 {file_path}: {e}")
                return 0

        return modified_lines

    def clean_project(self) -> Dict:
        """清理整個專案"""
        print("🔍 掃描並清理無效的 i18n 調用...")

        for py_file in self.project_root.rglob('*.py'):
            # 跳過 venv, __pycache__, tests
            skip_patterns = ['venv', '__pycache__', 'test_', '.pytest', 'cleanup_invalid_i18n.py']
            if any(pattern in str(py_file) for pattern in skip_patterns):
                continue

            modified = self.clean_file(py_file)

            if modified > 0:
                self.stats['files_processed'] += 1
                self.stats['lines_modified'] += modified
                status = "🔧 [DRY RUN]" if self.dry_run else "✓"
                print(f"{status} {py_file.relative_to(self.project_root)}: {modified} 行已清理")

        return self.stats

    def generate_report(self):
        """生成清理報告"""
        print("\n" + "="*70)
        print("i18n 無效調用清理報告")
        print("="*70)

        if self.dry_run:
            print("\n⚠️  DRY RUN 模式 - 未實際修改檔案\n")

        # 統計資訊
        print(f"📊 清理統計:")
        print(f"  處理檔案: {self.stats['files_processed']}")
        print(f"  修改行數: {self.stats['lines_modified']}")
        print(f"  移除無效調用: {self.stats['invalid_calls_removed']}")

        # 按原因分類
        reason_counts = {}
        for result in self.results:
            reason_counts[result.reason] = reason_counts.get(result.reason, 0) + 1

        print(f"\n📋 清理原因分佈:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {reason}: {count} 個")

        # 範例清理
        if self.results:
            print(f"\n🔍 清理範例 (前 10 個):")
            for result in self.results[:10]:
                print(f"\n  檔案: {result.file_path}:{result.line_number}")
                print(f"  原因: {result.reason}")
                print(f"  原始: {result.original[:100]}")
                print(f"  清理: {result.cleaned[:100]}")

        print("\n" + "="*70)

        if self.stats['invalid_calls_removed'] > 0:
            if self.dry_run:
                print(f"✅ DRY RUN 完成: 發現 {self.stats['invalid_calls_removed']} 個無效調用")
                print("   執行時請移除 --dry-run 參數以實際清理")
            else:
                print(f"✅ 清理完成: 已移除 {self.stats['invalid_calls_removed']} 個無效調用")
                print("   建議執行 verify_i18n_completeness.py 驗證結果")
        else:
            print("✅ 未發現需要清理的無效調用")

def main():
    """主程式"""
    # 檢查虛擬環境
    if 'venv_py314' not in sys.prefix:
        print("❌ 錯誤: 必須在虛擬環境中執行")
        print("✅ 請執行: source venv_py314/bin/activate")
        return 1

    # 解析參數
    dry_run = '--dry-run' in sys.argv

    # 檢查專案根目錄
    project_root = Path(__file__).parent
    if not (project_root / 'locales').exists():
        print(f"❌ 錯誤: 找不到 locales 目錄")
        print(f"   當前路徑: {project_root}")
        return 1

    # 執行清理
    print("="*70)
    print("i18n 無效調用清理工具")
    if dry_run:
        print("模式: DRY RUN (預覽模式，不實際修改檔案)")
    print("="*70 + "\n")

    cleaner = I18nCleanupTool(str(project_root), dry_run=dry_run)
    cleaner.clean_project()
    cleaner.generate_report()

    print("\n" + "="*70)
    print("清理完成")
    print("="*70 + "\n")

    return 0

if __name__ == '__main__':
    sys.exit(main())
