#!/usr/bin/env python3
"""
i18n 字串分類工具
將掃描出的字串分類為：用戶可見訊息 vs Debug 訊息
"""
import re
import json
from pathlib import Path
from typing import List, Dict

class StringClassifier:
    def __init__(self, scan_report: Path):
        self.scan_report = scan_report

    def load_report(self) -> Dict:
        """載入掃描報告"""
        with open(self.scan_report, 'r', encoding='utf-8') as f:
            return json.load(f)

    def is_user_visible(self, finding: Dict) -> bool:
        """判斷字串是否為用戶可見訊息"""
        original = finding['original']
        full_line = finding.get('full_line', '')

        # 用戶可見的標誌
        user_visible_markers = [
            '✅', '❌', '⚠️', '🎬', '🎥', '🖼️', '🎵',  # 表情符號
            '🔊', '📂', '📄', '✓', '▶️', '🔄', '🚀',
            '完成', '失敗', '錯誤', '成功', '警告',
            '處理中', '載入', '開始', '結束',
            '請', '已', '無法', '未找到',
            'console.print',  # console.print 通常是用戶訊息
        ]

        # Debug 訊息標誌
        debug_markers = [
            '[dim]',  # Rich dim 通常是 debug
            'DEBUG:', 'debug:',
            '測試', '範例', 'test',
        ]

        # 檢查 Debug 標誌
        for marker in debug_markers:
            if marker in original or marker in full_line:
                return False

        # 檢查用戶可見標誌
        for marker in user_visible_markers:
            if marker in original or marker in full_line:
                return True

        # 檢查是否為錯誤訊息
        if '錯誤' in finding.get('file', '') or 'error' in finding.get('file', '').lower():
            return True

        # 預設：如果包含中文且不是純技術訊息，視為用戶可見
        if re.search(r'[\u4e00-\u9fff]', original):
            # 排除純技術訊息
            tech_patterns = [
                r'^\s*#',  # 註解
                r'^\s*"""',  # docstring
                r'^\s*\'\'\'',  # docstring
            ]
            for pattern in tech_patterns:
                if re.match(pattern, full_line):
                    return False
            return True

        return False

    def classify_all(self) -> Dict:
        """分類所有字串"""
        report = self.load_report()
        user_visible = []
        debug_only = []

        for finding in report['findings']:
            if self.is_user_visible(finding):
                user_visible.append(finding)
            else:
                debug_only.append(finding)

        # 按檔案統計
        user_by_file = {}
        debug_by_file = {}

        for finding in user_visible:
            file = finding['file']
            user_by_file[file] = user_by_file.get(file, 0) + 1

        for finding in debug_only:
            file = finding['file']
            debug_by_file[file] = debug_by_file.get(file, 0) + 1

        return {
            'user_visible': {
                'total': len(user_visible),
                'findings': user_visible,
                'by_file': user_by_file
            },
            'debug_only': {
                'total': len(debug_only),
                'findings': debug_only,
                'by_file': debug_by_file
            },
            'summary': {
                'total_strings': len(report['findings']),
                'user_visible_count': len(user_visible),
                'debug_only_count': len(debug_only),
                'user_visible_percent': len(user_visible) / len(report['findings']) * 100
            }
        }

    def generate_classification_report(self, results: Dict, output_path: Path):
        """生成分類報告"""
        # JSON 報告
        with open(output_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # 文字報告
        with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
            summary = results['summary']
            f.write(f"=== i18n 字串分類報告 ===\n\n")
            f.write(f"總字串數: {summary['total_strings']}\n")
            f.write(f"用戶可見: {summary['user_visible_count']} ({summary['user_visible_percent']:.1f}%)\n")
            f.write(f"Debug 訊息: {summary['debug_only_count']}\n\n")

            f.write(f"## 用戶可見訊息分佈\n\n")
            for file, count in sorted(results['user_visible']['by_file'].items(), key=lambda x: -x[1]):
                f.write(f"{file}: {count} 處\n")

            f.write(f"\n## Debug 訊息分佈\n\n")
            for file, count in sorted(results['debug_only']['by_file'].items(), key=lambda x: -x[1]):
                f.write(f"{file}: {count} 處\n")

            # 按優先級排序的建議處理順序
            f.write(f"\n## 建議處理順序（用戶可見訊息）\n\n")

            # 按類別分組
            categories = {
                'error': [],
                'video': [],
                'audio': [],
                'image': [],
                'file': [],
                'batch': [],
                'other': []
            }

            for file, count in results['user_visible']['by_file'].items():
                if 'error' in file:
                    categories['error'].append((file, count))
                elif 'video' in file or 'veo' in file or 'scene' in file or 'clip' in file:
                    categories['video'].append((file, count))
                elif 'audio' in file or 'subtitle' in file:
                    categories['audio'].append((file, count))
                elif 'image' in file or 'imagen' in file:
                    categories['image'].append((file, count))
                elif 'file' in file or 'upload' in file:
                    categories['file'].append((file, count))
                elif 'batch' in file:
                    categories['batch'].append((file, count))
                else:
                    categories['other'].append((file, count))

            priority_order = ['error', 'video', 'file', 'image', 'audio', 'batch', 'other']
            priority_names = {
                'error': '🔴 錯誤處理（最高優先級）',
                'video': '🎬 影片處理',
                'file': '📁 檔案管理',
                'image': '🖼️ 圖片處理',
                'audio': '🎵 音訊處理',
                'batch': '⚡ 批次處理',
                'other': '🔧 其他功能'
            }

            for category in priority_order:
                if categories[category]:
                    f.write(f"\n### {priority_names[category]}\n")
                    for file, count in sorted(categories[category], key=lambda x: -x[1]):
                        f.write(f"  - {file}: {count} 處\n")

if __name__ == '__main__':
    project_root = Path.cwd()
    scan_report = project_root / 'i18n_scan_report.json'

    if not scan_report.exists():
        print("❌ 找不到掃描報告")
        exit(1)

    classifier = StringClassifier(scan_report)

    print("🔍 分類字串...")
    results = classifier.classify_all()

    summary = results['summary']
    print(f"\n✅ 分類完成！")
    print(f"   總字串數: {summary['total_strings']}")
    print(f"   用戶可見: {summary['user_visible_count']} ({summary['user_visible_percent']:.1f}%)")
    print(f"   Debug 訊息: {summary['debug_only_count']}")

    # 生成報告
    output_path = Path('i18n_classification_report')
    classifier.generate_classification_report(results, output_path)
    print(f"\n📄 報告已儲存:")
    print(f"   - {output_path}.json")
    print(f"   - {output_path}.txt")
