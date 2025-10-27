#!/usr/bin/env python3
"""
批次 i18n 掃描與分析工具
掃描專案中所有需要國際化的中文字串
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple

class I18nScanner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = []

    def scan_file(self, filepath: Path) -> List[Dict]:
        """掃描單一檔案，提取需要國際化的字串"""
        findings = []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return findings

        for line_num, line in enumerate(lines, 1):
            # 跳過註解
            if line.strip().startswith('#'):
                continue

            # 搜尋含中文的 print/console.print 語句
            patterns = [
                (r'print\s*\(\s*["\']([^"\']*[\u4e00-\u9fff]+[^"\']*)["\']', 'print'),
                (r'console\.print\s*\(\s*["\']([^"\']*[\u4e00-\u9fff]+[^"\']*)["\']', 'console.print'),
                (r'print\s*\(\s*f["\']([^"\']*[\u4e00-\u9fff]+[^"\']*)["\']', 'f-string'),
            ]

            for pattern, method in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    chinese_text = match.group(1)

                    # 生成翻譯鍵建議
                    suggested_key = self._generate_key(chinese_text, filepath)

                    findings.append({
                        'file': str(filepath.relative_to(self.project_root)),
                        'line': line_num,
                        'original': chinese_text,
                        'method': method,
                        'suggested_key': suggested_key,
                        'full_line': line.strip()
                    })

        return findings

    def _generate_key(self, text: str, filepath: Path) -> str:
        """根據文字內容和檔案路徑生成建議的翻譯鍵"""
        # 移除表情符號和特殊字元
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)

        # 根據檔案類型推斷類別
        filename = filepath.stem

        if 'error' in filename or 'Error' in filename:
            category = 'error'
        elif 'video' in filename or 'media' in filename:
            category = 'media'
        elif 'cache' in filename:
            category = 'cache'
        elif 'file' in filename:
            category = 'file'
        elif 'batch' in filename:
            category = 'batch'
        else:
            category = 'system'

        # 生成子鍵（基於內容關鍵字）
        if '完成' in text or '成功' in text:
            subkey = 'complete'
        elif '失敗' in text or '錯誤' in text:
            subkey = 'failed'
        elif '處理' in text:
            subkey = 'processing'
        elif '載入' in text:
            subkey = 'loading'
        else:
            # 使用前幾個中文字
            chinese_chars = re.findall(r'[\u4e00-\u9fff]+', clean_text)
            if chinese_chars:
                subkey = chinese_chars[0][:4]
            else:
                subkey = 'message'

        return f"{category}.{subkey}"

    def scan_directory(self, directory: Path, patterns: List[str]) -> Dict:
        """掃描目錄下符合 pattern 的所有檔案"""
        all_findings = []

        for pattern in patterns:
            for filepath in directory.rglob(pattern):
                # 跳過特定目錄
                if any(skip in str(filepath) for skip in ['venv', '__pycache__', '.git', 'tests']):
                    continue

                findings = self.scan_file(filepath)
                all_findings.extend(findings)

        return {
            'total_files': len(set(f['file'] for f in all_findings)),
            'total_strings': len(all_findings),
            'findings': all_findings
        }

    def generate_report(self, results: Dict, output_path: Path):
        """生成掃描報告"""
        # JSON 報告
        with open(output_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # 文字報告
        with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
            f.write(f"=== i18n 掃描報告 ===\n\n")
            f.write(f"總檔案數: {results['total_files']}\n")
            f.write(f"總字串數: {results['total_strings']}\n\n")

            # 按檔案分組
            by_file = {}
            for finding in results['findings']:
                file = finding['file']
                if file not in by_file:
                    by_file[file] = []
                by_file[file].append(finding)

            for file, findings in sorted(by_file.items()):
                f.write(f"\n## {file} ({len(findings)} 處)\n")
                for idx, finding in enumerate(findings, 1):
                    f.write(f"{idx}. Line {finding['line']}: {finding['original']}\n")
                    f.write(f"   建議鍵: {finding['suggested_key']}\n")

if __name__ == '__main__':
    project_root = Path.cwd()
    scanner = I18nScanner(project_root)

    # 掃描主要 Python 檔案
    print("🔍 掃描專案中需要國際化的字串...")
    results = scanner.scan_directory(project_root, ['gemini_*.py'])

    print(f"\n✅ 掃描完成！")
    print(f"   總檔案數: {results['total_files']}")
    print(f"   總字串數: {results['total_strings']}")

    # 生成報告
    output_path = Path('i18n_scan_report')
    scanner.generate_report(results, output_path)
    print(f"\n📄 報告已儲存:")
    print(f"   - {output_path}.json")
    print(f"   - {output_path}.txt")
