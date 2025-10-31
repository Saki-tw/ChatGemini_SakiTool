#!/usr/bin/env python3
"""
Git 推送前安全檢查腳本
根據 PROJECT_PHILOSOPHY.md 的規範執行完整檢查
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict

class PrePushChecker:
    def __init__(self):
        self.root_dir = Path.cwd()
        self.issues = []
        self.orphan_files = []

    def check_all(self) -> Tuple[List[str], List[str]]:
        """執行所有檢查"""
        print("🔍 開始執行推送前安全檢查...\n")

        # 1. 檢查開發文件
        self.check_dev_documents()

        # 2. 檢查路徑洩漏
        self.check_path_leaks()

        # 3. 檢查孤兒檔案
        self.check_orphan_files()

        # 4. 檢查備份檔案
        self.check_backup_files()

        # 5. 檢查臨時檔案
        self.check_temp_files()

        return self.issues, self.orphan_files

    def check_dev_documents(self):
        """檢查不應該推送的開發文件"""
        print("📄 檢查開發文件...")

        # 不應推送的文件模式
        forbidden_patterns = [
            r'.*Phase\d+.*\.md$',  # Phase*.md
            r'.*計畫\.md$',         # *計畫.md
            r'.*計劃\.md$',         # *計劃.md
            r'.*報告_\d{8}.*\.md$', # *報告_YYYYMMDD.md
            r'.*日誌\.md$',         # *日誌.md
            r'.*SPEC\.md$',         # *SPEC.md
            r'.*架構說明.*\.md$',   # *架構說明*.md
            r'OPTIMIZATION.*\.md$', # OPTIMIZATION*.md
            r'ROLLBACK.*\.md$',     # ROLLBACK*.md
            r'.*extracted\.json$',  # *extracted.json
            r'.*dump\.json$',       # *dump.json
        ]

        for md_file in self.root_dir.rglob('*.md'):
            if 'venv_py314' in str(md_file) or 'node_modules' in str(md_file):
                continue

            rel_path = md_file.relative_to(self.root_dir)

            for pattern in forbidden_patterns:
                if re.match(pattern, str(rel_path)):
                    self.issues.append(f"❌ 開發文件: {rel_path}")
                    break

    def check_path_leaks(self):
        """檢查本地路徑洩漏"""
        print("🔐 檢查路徑洩漏...")

        path_patterns = [
            r'/Users/\w+',
            r'/home/\w+',
            r'C:\\Users\\',
        ]

        for md_file in self.root_dir.rglob('*.md'):
            if 'venv_py314' in str(md_file) or 'node_modules' in str(md_file):
                continue

            try:
                content = md_file.read_text(encoding='utf-8')
                for pattern in path_patterns:
                    if re.search(pattern, content):
                        rel_path = md_file.relative_to(self.root_dir)
                        self.issues.append(f"⚠️  路徑洩漏: {rel_path} (包含 {pattern})")
                        break
            except Exception:
                pass

    def check_orphan_files(self):
        """檢查孤兒檔案（開發工具產生的檔案）"""
        print("🧹 檢查孤兒檔案...")

        # 孤兒檔案模式
        orphan_patterns = [
            # 開發腳本
            r'auto_i18n_.*\.py$',
            r'analyze_.*\.py$',
            r'batch_.*\.py$',
            r'cleanup_.*\.py$',
            r'collect_.*\.py$',
            r'convert_.*\.py$',
            r'extract_.*\.py$',
            r'fix_.*\.py$',
            r'i18n_rewriter\.py$',
            r'measure_.*\.py$',
            r'merge_.*\.py$',
            r'optimize_.*\.py$',
            r'profile_.*\.py$',
            r'scan_.*\.py$',
            r'trace_.*\.py$',
            r'translate_.*\.py$',
            r'verify_.*\.py$',
            r'update_.*\.py$',
            r'classify_.*\.py$',
            r'comprehensive_.*\.py$',
            r'deep_module_audit\.py$',
            r'module_health_check\.py$',

            # YAML 翻譯鍵檔案
            r'.*i18n_keys\.yaml$',
            r'.*translations_.*\.yaml$',
            r'collected_i18n_keys\.yaml$',
            r'missing_i18n_keys\.yaml$',
            r'temp_i18n_keys\.yaml$',
            r'media_modules_.*\.yaml$',
            r'MEDIA_TRANSLATION_KEYS.*\.yaml$',
            r'error_handler_i18n.*\.yaml$',

            # 日誌檔案
            r'.*\.log$',

            # 文本檔案
            r'.*i18n_keys\.txt$',
            r'append_i18n_keys\.txt$',

            # Markdown 檔案
            r'MEDIA_.*\.md$',
            r'錯誤診斷增強實作完成報告.*\.md$',
            r'\.context_continuation_multimodal\.md$',

            # 其他
            r'apply_cache_menu_fix\.py$',
            r'cache_menu_refactored\.py$',
        ]

        for file_path in self.root_dir.rglob('*'):
            if not file_path.is_file():
                continue

            if 'venv_py314' in str(file_path) or 'node_modules' in str(file_path):
                continue

            rel_path = file_path.relative_to(self.root_dir)

            for pattern in orphan_patterns:
                if re.match(pattern, str(rel_path.name)):
                    self.orphan_files.append(str(rel_path))
                    break

    def check_backup_files(self):
        """檢查備份檔案"""
        print("💾 檢查備份檔案...")

        for backup_file in self.root_dir.rglob('*.backup'):
            if 'venv_py314' in str(backup_file):
                continue

            rel_path = backup_file.relative_to(self.root_dir)
            self.orphan_files.append(str(rel_path))

    def check_temp_files(self):
        """檢查臨時檔案"""
        print("🗑️  檢查臨時檔案...")

        temp_patterns = [
            r'.*\.tmp$',
            r'.*\.temp$',
            r'.*~$',
            r'\._.*',
        ]

        for file_path in self.root_dir.rglob('*'):
            if not file_path.is_file():
                continue

            if 'venv_py314' in str(file_path):
                continue

            rel_path = file_path.relative_to(self.root_dir)

            for pattern in temp_patterns:
                if re.match(pattern, str(rel_path.name)):
                    self.orphan_files.append(str(rel_path))
                    break

    def print_summary(self):
        """打印檢查摘要"""
        print("\n" + "="*60)
        print("📊 檢查摘要")
        print("="*60)

        if self.issues:
            print(f"\n⚠️  發現 {len(self.issues)} 個安全問題:")
            for issue in self.issues:
                print(f"  {issue}")
        else:
            print("\n✅ 未發現安全問題")

        if self.orphan_files:
            print(f"\n🧹 發現 {len(self.orphan_files)} 個孤兒檔案:")
            for orphan in sorted(self.orphan_files):
                print(f"  • {orphan}")
        else:
            print("\n✅ 未發現孤兒檔案")

        print("\n" + "="*60)

def main():
    checker = PrePushChecker()
    issues, orphans = checker.check_all()
    checker.print_summary()

    # 生成清理建議
    if orphans:
        print("\n💡 清理建議:")
        print("  執行以下命令刪除所有孤兒檔案:")
        print(f"  python3 pre_push_check.py --clean")

    # 返回狀態碼
    if issues:
        print("\n❌ 檢查失敗：存在安全問題")
        return 1
    else:
        print("\n✅ 檢查通過：可以安全推送")
        return 0

if __name__ == '__main__':
    import sys

    if '--clean' in sys.argv:
        # 執行清理
        checker = PrePushChecker()
        checker.check_all()

        print(f"\n🗑️  準備刪除 {len(checker.orphan_files)} 個孤兒檔案...")

        for orphan in checker.orphan_files:
            file_path = Path(orphan)
            if file_path.exists():
                file_path.unlink()
                print(f"  ✓ 已刪除: {orphan}")

        print(f"\n✅ 清理完成！已刪除 {len(checker.orphan_files)} 個檔案")
    else:
        sys.exit(main())
