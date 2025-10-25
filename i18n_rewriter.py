#!/usr/bin/env python3
"""
i18n 改寫輔助工具

功能：
1. 掃描 Python 檔案中的中文字串
2. 自動匹配 locales/zh_TW.yaml 中的翻譯鍵值
3. 生成改寫建議報告

作者: Saki-tw (with Claude Code)
日期: 2025-10-25
"""

import re
import yaml
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher


class I18nRewriter:
    """i18n 改寫輔助工具"""

    def __init__(self, yaml_path: str = "locales/zh_TW.yaml"):
        """
        初始化

        Args:
            yaml_path: YAML 語言包路徑
        """
        self.yaml_path = Path(yaml_path)
        self.translations = self._load_yaml()
        self.string_to_key = self._build_reverse_map()

    def _load_yaml(self) -> Dict:
        """載入 YAML 語言包"""
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_reverse_map(self) -> Dict[str, str]:
        """
        建立 中文字串 → 翻譯鍵值 的反向映射

        Returns:
            映射字典
        """
        mapping = {}

        def traverse(data, prefix=""):
            """遞迴遍歷 YAML 結構"""
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == 'meta':
                        continue  # 跳過 meta 資訊

                    new_prefix = f"{prefix}.{key}" if prefix else key

                    if isinstance(value, str):
                        # 移除 Rich 格式標記進行匹配
                        clean_value = self._strip_rich_tags(value)
                        mapping[clean_value] = new_prefix
                        mapping[value] = new_prefix  # 也保留原始版本
                    elif isinstance(value, dict):
                        traverse(value, new_prefix)

        traverse(self.translations)
        return mapping

    def _strip_rich_tags(self, text: str) -> str:
        """移除 Rich 格式標記"""
        return re.sub(r'\[/?[^\]]+\]', '', text)

    def _contains_chinese(self, text: str) -> bool:
        """檢查字串是否包含中文"""
        return bool(re.search(r'[\u4e00-\u9fa5]', text))

    def _similarity(self, a: str, b: str) -> float:
        """計算字串相似度（0-1）"""
        return SequenceMatcher(None, a, b).ratio()

    def find_translation_key(self, chinese_str: str, threshold: float = 0.85) -> Optional[str]:
        """
        智能匹配翻譯鍵值

        Args:
            chinese_str: 中文字串
            threshold: 相似度閾值

        Returns:
            翻譯鍵值或 None
        """
        # 移除前後空白
        chinese_str = chinese_str.strip()

        # 1. 精確匹配
        if chinese_str in self.string_to_key:
            return self.string_to_key[chinese_str]

        # 2. 移除 Rich 格式後匹配
        clean_str = self._strip_rich_tags(chinese_str)
        if clean_str in self.string_to_key:
            return self.string_to_key[clean_str]

        # 3. 模糊匹配（只對短字串，避免誤匹配）
        if len(chinese_str) < 50:
            best_match = None
            best_score = 0

            for key_str, key in self.string_to_key.items():
                score = self._similarity(clean_str, self._strip_rich_tags(key_str))
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = key

            if best_match:
                return best_match

        return None

    def extract_chinese_strings(self, file_path: str) -> List[Tuple[int, str, str]]:
        """
        提取檔案中的中文字串

        Args:
            file_path: Python 檔案路徑

        Returns:
            [(行號, 原始字串, 建議鍵值), ...]
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        results = []

        # 使用正則表達式提取字串（簡化版，適用於大多數情況）
        patterns = [
            (r'\"([^\"]*[\u4e00-\u9fa5]+[^\"]*)\"', '雙引號'),
            (r"'([^']*[\u4e00-\u9fa5]+[^']*)'", '單引號'),
            (r'f\"([^\"]*[\u4e00-\u9fa5]+[^\"]*)\"', 'f-string 雙引號'),
            (r"f'([^']*[\u4e00-\u9fa5]+[^']*)'", 'f-string 單引號'),
        ]

        lines = content.split('\n')

        for line_no, line in enumerate(lines, 1):
            # 跳過註解
            if line.strip().startswith('#'):
                continue

            for pattern, pattern_type in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    chinese_str = match.group(1)

                    # 跳過過短或過長的字串
                    if len(chinese_str) < 2 or len(chinese_str) > 200:
                        continue

                    # 查找翻譯鍵值
                    key = self.find_translation_key(chinese_str)

                    results.append((line_no, chinese_str, key))

        return results

    def generate_report(self, file_path: str) -> str:
        """
        生成改寫報告

        Args:
            file_path: Python 檔案路徑

        Returns:
            Markdown 格式報告
        """
        strings = self.extract_chinese_strings(file_path)

        report = []
        report.append(f"# i18n 改寫報告: {Path(file_path).name}\n")
        report.append(f"**掃描時間**: 2025-10-25\n")
        report.append(f"**檔案路徑**: {file_path}\n")
        report.append(f"**發現中文字串**: {len(strings)} 個\n")

        # 統計
        matched = sum(1 for _, _, key in strings if key)
        unmatched = len(strings) - matched

        report.append(f"\n## 📊 統計\n")
        report.append(f"- ✅ 已匹配: {matched} 個\n")
        report.append(f"- ❌ 未匹配: {unmatched} 個\n")
        report.append(f"- 📈 匹配率: {matched/len(strings)*100:.1f}%\n" if strings else "- 📈 匹配率: N/A\n")

        # 詳細列表
        report.append(f"\n## 📋 詳細列表\n")

        if matched > 0:
            report.append(f"\n### ✅ 已匹配字串 ({matched} 個)\n")
            for line_no, chinese_str, key in strings:
                if key:
                    # 截斷過長字串
                    display_str = chinese_str if len(chinese_str) <= 50 else chinese_str[:50] + "..."
                    report.append(f"- **L{line_no}**: `{display_str}`\n")
                    report.append(f"  - 鍵值: `{key}`\n")
                    report.append(f"  - 建議: `t('{key}')`\n")

        if unmatched > 0:
            report.append(f"\n### ❌ 未匹配字串 ({unmatched} 個)\n")
            report.append(f"**這些字串需要手動處理或添加到 zh_TW.yaml**\n\n")
            for line_no, chinese_str, key in strings:
                if not key:
                    display_str = chinese_str if len(chinese_str) <= 50 else chinese_str[:50] + "..."
                    report.append(f"- **L{line_no}**: `{display_str}`\n")

        # 改寫建議
        report.append(f"\n## 🛠️ 改寫步驟\n")
        report.append(f"\n1. 在檔案開頭添加導入:\n")
        report.append(f"```python\n")
        report.append(f"from utils.i18n import t, _\n")
        report.append(f"```\n")

        report.append(f"\n2. 替換已匹配的字串（{matched} 處）\n")

        if unmatched > 0:
            report.append(f"\n3. 處理未匹配字串（{unmatched} 處）:\n")
            report.append(f"   - 選項 A: 添加到 locales/zh_TW.yaml\n")
            report.append(f"   - 選項 B: 保持原樣（如果是動態字串或不需翻譯）\n")

        report.append(f"\n## ✅ 完成檢查清單\n")
        report.append(f"- [ ] 添加 i18n 導入語句\n")
        report.append(f"- [ ] 替換所有已匹配字串\n")
        report.append(f"- [ ] 處理未匹配字串\n")
        report.append(f"- [ ] 測試檔案語法正確性\n")
        report.append(f"- [ ] 測試功能完整性\n")

        return ''.join(report)

    def analyze_file(self, file_path: str):
        """
        分析檔案並輸出報告（命令列使用）

        Args:
            file_path: Python 檔案路徑
        """
        print("=" * 60)
        print(f"分析檔案: {file_path}")
        print("=" * 60)

        strings = self.extract_chinese_strings(file_path)

        print(f"\n發現 {len(strings)} 個中文字串")

        matched = [(line, s, k) for line, s, k in strings if k]
        unmatched = [(line, s, k) for line, s, k in strings if not k]

        print(f"✅ 已匹配: {len(matched)} 個")
        print(f"❌ 未匹配: {len(unmatched)} 個")

        if matched:
            print(f"\n前 5 個已匹配範例:")
            for line_no, chinese_str, key in matched[:5]:
                display_str = chinese_str[:40] + "..." if len(chinese_str) > 40 else chinese_str
                print(f"  L{line_no}: {display_str}")
                print(f"        → t('{key}')")

        if unmatched:
            print(f"\n前 5 個未匹配字串:")
            for line_no, chinese_str, _ in unmatched[:5]:
                display_str = chinese_str[:40] + "..." if len(chinese_str) > 40 else chinese_str
                print(f"  L{line_no}: {display_str}")

        print("\n" + "=" * 60)


def main():
    """命令列入口"""
    import sys

    if len(sys.argv) < 2:
        print("使用方式: python i18n_rewriter.py <python_file>")
        print("範例: python i18n_rewriter.py gemini_pricing.py")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"❌ 檔案不存在: {file_path}")
        sys.exit(1)

    rewriter = I18nRewriter()

    # 分析檔案
    rewriter.analyze_file(file_path)

    # 生成詳細報告
    report = rewriter.generate_report(file_path)
    report_path = Path(file_path).stem + "_i18n_report.md"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📝 詳細報告已儲存至: {report_path}")


if __name__ == "__main__":
    main()
