#!/usr/bin/env python3
"""
掃描專案中所有硬編碼中文字串並生成 i18n 轉換報告

功能：
1. 掃描所有 .py 檔案中的硬編碼中文
2. 排除已使用 safe_t/t() 的行
3. 分類：用戶可見訊息 vs Debug/註解
4. 生成優先級報告

作者: Saki-tw (with Claude Code)
日期: 2025-10-29
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple
import json

class ChineseStringScanner:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results = {}

        # 排除的目錄
        self.exclude_dirs = {
            'venv_py314', '__pycache__', '.git', 'locales',
            'tests', 'dist', 'build', '.pytest_cache'
        }

        # 排除的檔案模式
        self.exclude_files = {
            'test_', 'scan_', 'extract_', 'classify_',
            'batch_', 'verify_', 'translate_', 'convert_',
            'fix_', 'merge_', 'update_'
        }

    def should_skip_file(self, file_path: Path) -> bool:
        """判斷是否應跳過此檔案"""
        # 跳過排除的目錄
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return True

        # 跳過工具腳本
        filename = file_path.name
        for pattern in self.exclude_files:
            if filename.startswith(pattern):
                return True

        return False

    def is_user_visible(self, line: str) -> bool:
        """判斷是否為用戶可見訊息"""
        line_lower = line.lower()

        # 明確的用戶輸出
        user_output_patterns = [
            'print(', 'console.print(', 'logger.info(',
            'logger.warning(', 'logger.error(',
            'rich.print(', 'click.echo(',
            'sys.stdout.write(', 'sys.stderr.write('
        ]

        for pattern in user_output_patterns:
            if pattern in line_lower:
                return True

        # 排除註解
        if line.strip().startswith('#'):
            return False

        # 排除 docstring
        if '"""' in line or "'''" in line:
            return False

        # 排除變數名稱中的中文（較少見但可能存在）
        if ' = ' in line and not any(p in line_lower for p in ['print', 'log', 'echo']):
            return False

        return True

    def find_chinese_in_file(self, file_path: Path) -> List[Tuple[int, str, bool]]:
        """找出檔案中的硬編碼中文

        Returns:
            List of (line_number, line_content, is_user_visible)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            results = []
            for i, line in enumerate(lines, 1):
                # 跳過已使用 i18n 的行
                if 'safe_t(' in line or re.search(r'\bt\(', line):
                    continue

                # 檢查是否包含中文
                if re.search(r'[\u4e00-\u9fff]', line):
                    is_visible = self.is_user_visible(line)
                    results.append((i, line.strip(), is_visible))

            return results

        except Exception as e:
            print(f"⚠️  讀取失敗: {file_path} - {e}")
            return []

    def scan_project(self) -> Dict:
        """掃描整個專案"""
        print("🔍 開始掃描專案...")

        py_files = list(self.project_root.rglob("*.py"))
        total_files = len(py_files)
        scanned = 0

        for file_path in py_files:
            if self.should_skip_file(file_path):
                continue

            results = self.find_chinese_in_file(file_path)
            if results:
                rel_path = str(file_path.relative_to(self.project_root))
                self.results[rel_path] = results
                scanned += 1

        print(f"✅ 掃描完成: {scanned}/{total_files} 個檔案包含硬編碼中文")
        return self.results

    def generate_report(self) -> str:
        """生成報告"""
        if not self.results:
            return "✅ 未發現硬編碼中文字串"

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("硬編碼中文字串掃描報告")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 統計資料
        total_strings = sum(len(strings) for strings in self.results.values())
        user_visible = sum(1 for strings in self.results.values()
                          for _, _, is_visible in strings if is_visible)
        debug_only = total_strings - user_visible

        report_lines.append(f"📊 總計: {len(self.results)} 個檔案, {total_strings} 處硬編碼")
        report_lines.append(f"   - 用戶可見: {user_visible} 處 ({user_visible*100//total_strings}%)")
        report_lines.append(f"   - Debug/註解: {debug_only} 處 ({debug_only*100//total_strings}%)")
        report_lines.append("")

        # 按檔案分類
        priority_files = {
            'gemini_chat.py': '🔴 核心對話界面',
            'CodeGemini.py': '🔴 CodeGemini 主程式',
            'interactive_language_menu.py': '🟡 語言選單',
        }

        # 優先級檔案
        report_lines.append("=" * 80)
        report_lines.append("🔴 高優先級檔案 (核心用戶界面)")
        report_lines.append("=" * 80)
        report_lines.append("")

        for filename, desc in priority_files.items():
            if filename in self.results:
                strings = self.results[filename]
                visible = sum(1 for _, _, is_visible in strings if is_visible)
                report_lines.append(f"{desc}")
                report_lines.append(f"📄 {filename}")
                report_lines.append(f"   總計: {len(strings)} 處 | 用戶可見: {visible} 處")
                report_lines.append("")

        # CodeGemini 子目錄
        codegemini_files = {k: v for k, v in self.results.items()
                           if k.startswith('CodeGemini/')}

        if codegemini_files:
            report_lines.append("=" * 80)
            report_lines.append("🟡 CodeGemini 子模組")
            report_lines.append("=" * 80)
            report_lines.append("")

            for filepath, strings in sorted(codegemini_files.items()):
                visible = sum(1 for _, _, is_visible in strings if is_visible)
                if visible > 0:  # 只顯示有用戶可見訊息的檔案
                    report_lines.append(f"📄 {filepath}")
                    report_lines.append(f"   總計: {len(strings)} 處 | 用戶可見: {visible} 處")

        # 其他核心模組
        other_files = {k: v for k, v in self.results.items()
                      if not k.startswith('CodeGemini/')
                      and k not in priority_files}

        if other_files:
            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append("🟢 其他模組")
            report_lines.append("=" * 80)
            report_lines.append("")

            # 按用戶可見訊息數量排序
            sorted_others = sorted(other_files.items(),
                                  key=lambda x: sum(1 for _, _, v in x[1] if v),
                                  reverse=True)

            for filepath, strings in sorted_others[:20]:  # 只顯示前 20 個
                visible = sum(1 for _, _, is_visible in strings if is_visible)
                if visible > 5:  # 只顯示有較多用戶可見訊息的檔案
                    report_lines.append(f"📄 {filepath}")
                    report_lines.append(f"   總計: {len(strings)} 處 | 用戶可見: {visible} 處")

        report_lines.append("")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def export_json(self, output_file: str = "hardcoded_chinese_report.json"):
        """匯出 JSON 格式報告"""
        export_data = {}

        for filepath, strings in self.results.items():
            export_data[filepath] = {
                'total': len(strings),
                'user_visible': sum(1 for _, _, v in strings if v),
                'debug_only': sum(1 for _, _, v in strings if not v),
                'strings': [
                    {
                        'line': line_num,
                        'content': content[:100],  # 限制長度
                        'user_visible': is_visible
                    }
                    for line_num, content, is_visible in strings
                ]
            }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"📄 JSON 報告已匯出: {output_file}")

    def get_priority_list(self) -> List[Tuple[str, int, int]]:
        """取得優先級處理清單

        Returns:
            List of (filepath, total_strings, user_visible_strings)
        """
        priority = []

        for filepath, strings in self.results.items():
            visible = sum(1 for _, _, is_visible in strings if is_visible)
            if visible > 0:
                priority.append((filepath, len(strings), visible))

        # 按用戶可見訊息數量排序
        priority.sort(key=lambda x: x[2], reverse=True)

        return priority


def main():
    """主程式"""
    print("\n" + "=" * 80)
    print("ChatGemini_SakiTool - 硬編碼中文掃描工具")
    print("=" * 80)
    print()

    scanner = ChineseStringScanner()
    scanner.scan_project()

    # 生成報告
    report = scanner.generate_report()
    print("\n" + report)

    # 匯出 JSON
    scanner.export_json()

    # 顯示優先級清單
    print("\n" + "=" * 80)
    print("📋 建議處理順序 (按用戶可見訊息數量)")
    print("=" * 80)
    print()

    priority_list = scanner.get_priority_list()
    for i, (filepath, total, visible) in enumerate(priority_list[:10], 1):
        print(f"{i:2d}. {filepath:50s} - {visible:3d} 處用戶可見")

    print("\n" + "=" * 80)
    print("✅ 掃描完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
