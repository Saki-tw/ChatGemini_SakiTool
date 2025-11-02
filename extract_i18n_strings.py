#!/usr/bin/env python3
"""
Phase 5 - i18n 字串提取工具（安全版本）

只提取中文字串生成翻譯鍵，不修改原檔案
供手動轉換參考使用
"""
import re
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class I18nExtractor:
    """i18n 字串提取器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        self.extracted_strings = []

    def extract(self) -> Dict:
        """提取所有中文字串"""
        print(f"\n分析: {self.file_path.name}")

        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        in_docstring = False
        docstring_quote = None

        stats = {
            'total_lines': len(lines),
            'chinese_lines': 0,
            'pure_strings': 0,
            'fstrings': 0,
            'comments': 0,
            'docstrings': 0
        }

        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()

            # Docstring 檢測
            if '"""' in line or "'''" in line:
                quote = '"""' if '"""' in line else "'''"
                count = line.count(quote)

                if not in_docstring:
                    in_docstring = True
                    docstring_quote = quote
                    if count >= 2:
                        in_docstring = False
                        stats['docstrings'] += 1
                elif docstring_quote == quote:
                    in_docstring = False
                    stats['docstrings'] += 1
                continue

            if in_docstring:
                continue

            # 註釋行
            if stripped.startswith('#'):
                if self.chinese_pattern.search(line):
                    stats['comments'] += 1
                continue

            # 包含中文
            if not self.chinese_pattern.search(line):
                continue

            stats['chinese_lines'] += 1

            # 提取字串
            self._extract_from_line(line, lineno, stats)

        print(f"  • {stats['chinese_lines']} 行包含中文")
        print(f"  • {stats['pure_strings']} 個純字串")
        print(f"  • {stats['fstrings']} 個 f-string")
        print(f"  • {stats['comments']} 個註釋")
        print(f"  • {stats['docstrings']} 個 docstring")

        return {
            'file': str(self.file_path),
            'stats': stats,
            'strings': self.extracted_strings
        }

    def _extract_from_line(self, line: str, lineno: int, stats: Dict):
        """從一行提取字串信息"""
        # F-strings
        for match in re.finditer(r'f["\']([^"\']+)["\']', line):
            content = match.group(1)
            if self.chinese_pattern.search(content):
                self.extracted_strings.append({
                    'lineno': lineno,
                    'type': 'f-string',
                    'content': content,
                    'line_preview': line.strip()[:80]
                })
                stats['fstrings'] += 1

        # 普通字串
        for match in re.finditer(r'(?<!f)["\']([^"\']+)["\']', line):
            content = match.group(1)
            if self.chinese_pattern.search(content):
                # 排除已經是 safe_t 調用的
                if 'safe_t(' in line:
                    continue

                self.extracted_strings.append({
                    'lineno': lineno,
                    'type': 'string',
                    'content': content,
                    'line_preview': line.strip()[:80]
                })
                stats['pure_strings'] += 1


def generate_report(results: List[Dict]) -> str:
    """生成 Markdown 報告"""
    lines = [
        "# Phase 5 - i18n 字串提取報告",
        "",
        f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]

    total_strings = sum(r['stats']['pure_strings'] for r in results)
    total_fstrings = sum(r['stats']['fstrings'] for r in results)

    lines.extend([
        "## 統計摘要",
        "",
        f"- 處理檔案: {len(results)}",
        f"- 純字串（可直接轉換）: **{total_strings}**",
        f"- F-strings（需手動處理）: **{total_fstrings}**",
        "",
        "---",
        ""
    ])

    for result in results:
        file_name = Path(result['file']).name
        stats = result['stats']

        lines.extend([
            f"## {file_name}",
            "",
            f"- 總行數: {stats['total_lines']}",
            f"- 包含中文行數: {stats['chinese_lines']}",
            f"- 純字串: {stats['pure_strings']}",
            f"- F-strings: {stats['fstrings']}",
            f"- 註釋: {stats['comments']}",
            f"- Docstrings: {stats['docstrings']}",
            "",
            "### 提取的字串示例（前10個）",
            ""
        ])

        for i, string_info in enumerate(result['strings'][:10], 1):
            lines.append(f"{i}. **行 {string_info['lineno']}** ({string_info['type']})")
            lines.append(f"   - 內容: `{string_info['content'][:50]}`")
            lines.append(f"   - 預覽: `{string_info['line_preview']}`")
            lines.append("")

        if len(result['strings']) > 10:
            lines.append(f"   ... 以及其他 {len(result['strings']) - 10} 個字串")
            lines.append("")

        lines.append("---")
        lines.append("")

    return '\n'.join(lines)


def generate_translation_keys(results: List[Dict]) -> Dict:
    """生成翻譯鍵字典"""
    all_keys = {}
    global_index = 1

    for result in results:
        module_name = Path(result['file']).stem

        for string_info in result['strings']:
            if string_info['type'] == 'string':  # 只為純字串生成鍵
                key = f"error_handler.{module_name}.msg_{global_index:04d}"
                all_keys[key] = {
                    'zh_TW': string_info['content'],
                    'en_US': '',
                    'file': result['file'],
                    'lineno': string_info['lineno']
                }
                global_index += 1

    return all_keys


def main():
    """主程序"""
    print("\n" + "="*70)
    print(" Phase 5 - i18n 字串提取（安全分析）")
    print("="*70)

    target_files = [
        '/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/error_fix_suggestions.py',
        '/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/error_diagnostics.py'
    ]

    results = []
    for file_path in target_files:
        if not Path(file_path).exists():
            print(f"\n✗ 檔案不存在: {file_path}")
            continue

        extractor = I18nExtractor(file_path)
        result = extractor.extract()
        results.append(result)

    # 生成報告
    report_md = generate_report(results)
    report_path = '/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/phase5_extraction_report.md'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_md)

    print(f"\n✓ 已生成分析報告: {report_path}")

    # 生成翻譯鍵
    translation_keys = generate_translation_keys(results)
    keys_path = '/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/phase5_translation_keys.json'

    with open(keys_path, 'w', encoding='utf-8') as f:
        json.dump(translation_keys, f, indent=2, ensure_ascii=False)

    print(f"✓ 已生成翻譯鍵: {keys_path}")
    print(f"✓ 共 {len(translation_keys)} 個可轉換的純字串")

    # 生成詳細結果
    detailed_path = '/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/phase5_detailed_analysis.json'
    with open(detailed_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✓ 已生成詳細分析: {detailed_path}")

    # 摘要
    total_pure = sum(r['stats']['pure_strings'] for r in results)
    total_fstrings = sum(r['stats']['fstrings'] for r in results)

    print("\n" + "="*70)
    print(" 分析完成")
    print("="*70)
    print(f"\n建議:")
    print(f"  1. {total_pure} 個純字串可使用自動化工具轉換")
    print(f"  2. {total_fstrings} 個 f-string 建議手動處理")
    print(f"  3. 使用生成的翻譯鍵檔案進行後續轉換")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    main()
