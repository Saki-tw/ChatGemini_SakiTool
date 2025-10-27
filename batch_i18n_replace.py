#!/usr/bin/env python3
"""
批次 i18n 字串替換工具
自動將中文字串替換為 safe_t() 調用
"""
import re
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class I18nReplacer:
    def __init__(self, project_root: Path, scan_report: Path):
        self.project_root = project_root
        self.scan_report = scan_report
        self.replacements = []
        self.backup_dir = project_root / 'backups' / f'i18n_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    def load_scan_report(self) -> Dict:
        """載入掃描報告"""
        with open(self.scan_report, 'r', encoding='utf-8') as f:
            return json.load(f)

    def generate_translation_key(self, finding: Dict) -> str:
        """根據掃描結果生成翻譯鍵"""
        suggested_key = finding.get('suggested_key', 'system.message')

        # 改進建議鍵的生成邏輯
        original = finding['original']
        file = finding['file']

        # 根據檔案類型決定主類別
        if 'video' in file:
            category = 'media.video'
        elif 'audio' in file:
            category = 'media.audio'
        elif 'image' in file or 'imagen' in file:
            category = 'media.image'
        elif 'error' in file:
            category = 'error'
        elif 'batch' in file:
            category = 'batch'
        elif 'file' in file or 'upload' in file:
            category = 'file'
        elif 'cache' in file:
            category = 'cache'
        else:
            category = 'system'

        # 根據內容決定子鍵
        if '✅' in original or '完成' in original or '成功' in original:
            subkey = 'complete'
        elif '❌' in original or '失敗' in original or '錯誤' in original:
            subkey = 'failed'
        elif '⚠️' in original or '警告' in original:
            subkey = 'warning'
        elif '處理' in original or '執行' in original:
            subkey = 'processing'
        elif '載入' in original or '讀取' in original:
            subkey = 'loading'
        elif '儲存' in original or '保存' in original:
            subkey = 'saving'
        elif '開始' in original:
            subkey = 'start'
        else:
            # 使用前幾個中文字
            chinese_chars = re.findall(r'[\u4e00-\u9fff]+', original)
            if chinese_chars:
                subkey = chinese_chars[0][:3].lower()
            else:
                subkey = 'message'

        return f"{category}.{subkey}"

    def create_safe_t_call(self, original: str, key: str) -> str:
        """生成 safe_t() 調用代碼"""
        # 移除 Rich 標籤
        clean_text = re.sub(r'\[/?[^\]]+\]', '', original)

        # 檢查是否有格式化參數
        format_params = re.findall(r'\{([^}]+)\}', original)

        if format_params:
            # 有參數的情況
            # 將原始字串中的參數轉換為佔位符
            param_dict = {}
            for i, param in enumerate(format_params):
                param_name = f'param{i+1}'
                param_dict[param_name] = param

            # 構建 safe_t 調用
            params_str = ', '.join(f"{k}={v}" for k, v in param_dict.items())
            return f"safe_t('{key}', fallback='{clean_text}', {params_str})"
        else:
            # 沒有參數的情況
            return f"safe_t('{key}', fallback='{clean_text}')"

    def backup_file(self, filepath: Path):
        """備份檔案"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = self.backup_dir / filepath.name
        shutil.copy2(filepath, backup_path)

    def replace_in_file(self, filepath: Path, findings: List[Dict], dry_run: bool = True) -> List[Dict]:
        """在單一檔案中進行替換"""
        if not dry_run:
            self.backup_file(filepath)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return []

        changes = []
        modified_lines = {}

        # 按行號分組
        findings_by_line = {}
        for finding in findings:
            line_num = finding['line']
            if line_num not in findings_by_line:
                findings_by_line[line_num] = []
            findings_by_line[line_num].append(finding)

        # 處理每一行
        for line_num, line_findings in findings_by_line.items():
            if line_num > len(lines):
                continue

            original_line = lines[line_num - 1]
            modified_line = original_line

            # 對每個發現進行替換
            for finding in line_findings:
                original_text = finding['original']
                key = self.generate_translation_key(finding)
                safe_t_call = self.create_safe_t_call(original_text, key)

                # 尋找並替換
                # 處理 print() 和 console.print()
                patterns = [
                    (rf'print\s*\(\s*["\']({re.escape(original_text)})["\']', f'print({safe_t_call})'),
                    (rf'console\.print\s*\(\s*["\']({re.escape(original_text)})["\']', f'console.print({safe_t_call})'),
                    (rf'print\s*\(\s*f["\']({re.escape(original_text)})["\']', f'print({safe_t_call})'),
                ]

                for pattern, replacement in patterns:
                    if re.search(pattern, modified_line):
                        modified_line = re.sub(pattern, replacement, modified_line, count=1)
                        changes.append({
                            'file': str(filepath.relative_to(self.project_root)),
                            'line': line_num,
                            'original': original_line.strip(),
                            'modified': modified_line.strip(),
                            'key': key
                        })
                        break

            if modified_line != original_line:
                modified_lines[line_num - 1] = modified_line

        # 應用修改
        if not dry_run and modified_lines:
            for line_idx, new_line in modified_lines.items():
                lines[line_idx] = new_line

            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)

        return changes

    def process_files(self, file_filter: str = None, dry_run: bool = True) -> Dict:
        """批次處理檔案"""
        report = self.load_scan_report()
        all_changes = []

        # 按檔案分組
        by_file = {}
        for finding in report['findings']:
            file = finding['file']
            if file_filter and file_filter not in file:
                continue

            if file not in by_file:
                by_file[file] = []
            by_file[file].append(finding)

        # 處理每個檔案
        for file, findings in by_file.items():
            filepath = self.project_root / file
            if not filepath.exists():
                continue

            changes = self.replace_in_file(filepath, findings, dry_run)
            all_changes.extend(changes)

        return {
            'total_files': len(by_file),
            'total_changes': len(all_changes),
            'changes': all_changes,
            'dry_run': dry_run
        }

    def generate_change_report(self, results: Dict, output_path: Path):
        """生成變更報告"""
        with open(output_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
            mode = "預覽模式" if results['dry_run'] else "實際執行"
            f.write(f"=== i18n 批次替換報告 ({mode}) ===\n\n")
            f.write(f"總檔案數: {results['total_files']}\n")
            f.write(f"總變更數: {results['total_changes']}\n\n")

            # 按檔案分組
            by_file = {}
            for change in results['changes']:
                file = change['file']
                if file not in by_file:
                    by_file[file] = []
                by_file[file].append(change)

            for file, changes in sorted(by_file.items()):
                f.write(f"\n## {file} ({len(changes)} 處變更)\n")
                for idx, change in enumerate(changes, 1):
                    f.write(f"\n{idx}. Line {change['line']}: {change['key']}\n")
                    f.write(f"   原始: {change['original']}\n")
                    f.write(f"   修改: {change['modified']}\n")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='批次 i18n 字串替換工具')
    parser.add_argument('--module', help='要處理的模組名稱（檔案名稱篩選）')
    parser.add_argument('--dry-run', action='store_true', help='預覽模式，不實際修改檔案')
    parser.add_argument('--confirm', action='store_true', help='確認執行替換')

    args = parser.parse_args()

    project_root = Path.cwd()
    scan_report = project_root / 'i18n_scan_report.json'

    if not scan_report.exists():
        print("❌ 找不到掃描報告，請先執行 batch_i18n_scanner.py")
        exit(1)

    replacer = I18nReplacer(project_root, scan_report)

    # 確定模式
    dry_run = not args.confirm
    mode_text = "🔍 預覽模式" if dry_run else "⚡ 執行模式"

    print(f"\n{mode_text}")
    if args.module:
        print(f"📁 檔案篩選: {args.module}")
    print()

    # 執行處理
    results = replacer.process_files(
        file_filter=args.module,
        dry_run=dry_run
    )

    print(f"✅ 處理完成！")
    print(f"   總檔案數: {results['total_files']}")
    print(f"   總變更數: {results['total_changes']}")

    # 生成報告
    output_path = Path('i18n_replace_report')
    replacer.generate_change_report(results, output_path)
    print(f"\n📄 報告已儲存:")
    print(f"   - {output_path}.json")
    print(f"   - {output_path}.txt")

    if dry_run:
        print(f"\n💡 提示: 使用 --confirm 參數執行實際替換")
