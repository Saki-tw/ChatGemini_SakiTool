#!/usr/bin/env python3
"""
i18n 完整性驗證工具

功能:
1. 掃描所有 Python 檔案的 safe_t() 和 t() 調用
2. 提取使用的翻譯鍵
3. 檢查 4 個語言包的覆蓋率
4. 生成缺失鍵報告
5. 檢測重複鍵和無效鍵

作者: Claude Code (Sonnet 4.5)
日期: 2025-10-29
"""

import os
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class KeyUsage:
    """翻譯鍵使用記錄"""
    key: str
    file_path: str
    line_number: int
    context: str

class I18nCompletenessChecker:
    """i18n 完整性檢查器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.locales_dir = self.project_root / 'locales'
        self.used_keys: Dict[str, List[KeyUsage]] = defaultdict(list)
        self.language_packs: Dict[str, Dict] = {}
        self.stats = {
            'files_scanned': 0,
            'keys_found': 0,
            'safe_t_calls': 0,
            't_calls': 0
        }

    def is_valid_translation_key(self, key: str) -> bool:
        """驗證是否為有效的翻譯鍵

        規則:
        - 長度 3-50 字元
        - 必須包含點號 (分層結構)
        - 只包含 a-z, 0-9, _, .
        - 以小寫字母開頭
        - 不是純符號或空白
        """
        # 長度檢查
        if len(key) < 3 or len(key) > 50:
            return False

        # 必須包含點號 (分層結構)
        if '.' not in key:
            return False

        # 不能是純符號
        if key in ['=', '-', '\n', ' ', '.', '..', '---', '===']:
            return False

        # 必須符合命名規範: 小寫字母開頭, 只包含 a-z0-9._
        if not re.match(r'^[a-z][a-z0-9._]*$', key):
            return False

        # 不包含連續點號
        if '..' in key:
            return False

        # 每個部分都要有效
        parts = key.split('.')
        for part in parts:
            if not part:  # 空部分
                return False
            if part[0].isdigit():  # 以數字開頭
                return False

        return True

    def scan_python_files(self) -> Dict[str, List[KeyUsage]]:
        """掃描所有 Python 檔案,提取使用的翻譯鍵"""
        # 匹配 t('key') 或 safe_t('key') 或 t("key") 或 safe_t("key")
        # 使用 \b 確保 t 是函數名，不是其他詞的一部分（如 print）
        pattern = re.compile(r"\b(?:safe_)?t\(['\"]([^'\"]+)['\"]")

        print("🔍 掃描 Python 檔案...")

        for py_file in self.project_root.rglob('*.py'):
            # 跳過 venv, __pycache__, tests
            skip_patterns = ['venv', '__pycache__', 'test_', '.pytest']
            if any(pattern in str(py_file) for pattern in skip_patterns):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    # 跳過註解行
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue

                    # 移除行尾註解（但保留字串內的 #）
                    # 簡化處理：如果有 #，檢查它是否在引號外
                    code_part = line
                    if '#' in line:
                        # 粗略處理：只處理明顯的註解
                        parts = line.split('#')
                        if len(parts) > 1:
                            # 檢查 # 前是否有未閉合的引號
                            before_hash = parts[0]
                            single_quotes = before_hash.count("'") - before_hash.count("\\'")
                            double_quotes = before_hash.count('"') - before_hash.count('\\"')
                            if single_quotes % 2 == 0 and double_quotes % 2 == 0:
                                code_part = before_hash

                    matches = pattern.finditer(code_part)
                    for match in matches:
                        key = match.group(1)

                        # 檢查匹配位置前是否有 r' 或 r" (原始字串)
                        start_pos = match.start()
                        if start_pos >= 2:
                            before_match = code_part[start_pos-2:start_pos]
                            if before_match in ["r'", 'r"', "R'", 'R"']:
                                continue  # 跳過原始字串中的模式

                        # 驗證是否為有效的翻譯鍵
                        if not self.is_valid_translation_key(key):
                            continue  # 跳過無效鍵 (硬編碼字串)

                        # 統計調用類型
                        if 'safe_t(' in match.group(0):
                            self.stats['safe_t_calls'] += 1
                        else:
                            self.stats['t_calls'] += 1

                        # 記錄使用位置
                        usage = KeyUsage(
                            key=key,
                            file_path=str(py_file.relative_to(self.project_root)),
                            line_number=line_num,
                            context=line.strip()
                        )
                        self.used_keys[key].append(usage)

                self.stats['files_scanned'] += 1

            except Exception as e:
                print(f"⚠️  無法讀取 {py_file}: {e}")

        self.stats['keys_found'] = len(self.used_keys)
        print(f"✓ 掃描完成: {self.stats['files_scanned']} 個檔案, {self.stats['keys_found']} 個翻譯鍵")

        return self.used_keys

    def load_language_packs(self) -> Dict[str, Dict]:
        """載入所有語言包"""
        print("\n📚 載入語言包...")

        for lang_file in self.locales_dir.glob('*.yaml'):
            # 跳過備份檔案
            if 'backup' in lang_file.name or 'bak' in lang_file.name:
                continue

            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.language_packs[lang_code] = yaml.safe_load(f) or {}
                print(f"✓ 載入 {lang_code}.yaml")
            except Exception as e:
                print(f"❌ 無法載入 {lang_file}: {e}")

        return self.language_packs

    def check_key_exists(self, key: str, lang_dict: Dict) -> bool:
        """檢查翻譯鍵是否存在"""
        keys = key.split('.')
        current = lang_dict

        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return False
            current = current[k]

        return True

    def get_key_value(self, key: str, lang_dict: Dict) -> any:
        """獲取翻譯鍵的值"""
        keys = key.split('.')
        current = lang_dict

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return None

    def check_completeness(self) -> Dict[str, Dict]:
        """檢查每個語言包的完整性"""
        results = {}

        for lang_code, lang_dict in self.language_packs.items():
            missing_keys = []
            invalid_keys = []  # 鍵存在但值不是字串

            for key in self.used_keys.keys():
                if not self.check_key_exists(key, lang_dict):
                    missing_keys.append(key)
                else:
                    # 檢查值是否為字串
                    value = self.get_key_value(key, lang_dict)
                    if not isinstance(value, str):
                        invalid_keys.append((key, type(value).__name__))

            total_keys = len(self.used_keys)
            found_keys = total_keys - len(missing_keys)
            coverage = (found_keys / total_keys * 100) if total_keys > 0 else 0

            results[lang_code] = {
                'coverage': coverage,
                'found': found_keys,
                'missing': missing_keys,
                'invalid': invalid_keys,
                'total_keys': total_keys
            }

        return results

    def find_duplicate_keys(self) -> List[Tuple[str, int]]:
        """查找使用次數最多的翻譯鍵 (可能的重複或常用鍵)"""
        duplicates = []
        for key, usages in self.used_keys.items():
            if len(usages) > 10:  # 使用超過 10 次
                duplicates.append((key, len(usages)))

        return sorted(duplicates, key=lambda x: x[1], reverse=True)

    def generate_detailed_report(self, results: Dict[str, Dict]):
        """生成詳細報告"""
        print("\n" + "="*70)
        print("i18n 完整性驗證報告")
        print("="*70)

        # 統計資訊
        print(f"\n📊 掃描統計:")
        print(f"  檔案數量: {self.stats['files_scanned']}")
        print(f"  t() 調用: {self.stats['t_calls']}")
        print(f"  safe_t() 調用: {self.stats['safe_t_calls']}")
        print(f"  總調用次數: {self.stats['t_calls'] + self.stats['safe_t_calls']}")
        print(f"  唯一翻譯鍵: {self.stats['keys_found']}")

        # 語言包完整性
        print(f"\n🌐 語言包完整性:")
        all_complete = True

        for lang_code in sorted(results.keys()):
            data = results[lang_code]
            coverage = data['coverage']
            found = data['found']
            total = data['total_keys']
            missing = data['missing']
            invalid = data['invalid']

            status = "✅" if coverage == 100 and not invalid else "⚠️ "
            print(f"\n  {status} {lang_code}:")
            print(f"     覆蓋率: {found}/{total} ({coverage:.1f}%)")

            if missing:
                all_complete = False
                print(f"     ❌ 缺失 {len(missing)} 個鍵:")
                for key in sorted(missing)[:5]:  # 只顯示前 5 個
                    usages = self.used_keys[key]
                    first_usage = usages[0]
                    print(f"        - {key}")
                    print(f"          使用於: {first_usage.file_path}:{first_usage.line_number}")
                if len(missing) > 5:
                    print(f"        ... 還有 {len(missing) - 5} 個")

            if invalid:
                all_complete = False
                print(f"     ⚠️  無效鍵 {len(invalid)} 個 (非字串值):")
                for key, key_type in invalid[:5]:
                    print(f"        - {key} (類型: {key_type})")
                if len(invalid) > 5:
                    print(f"        ... 還有 {len(invalid) - 5} 個")

        # 高頻使用鍵
        duplicates = self.find_duplicate_keys()
        if duplicates:
            print(f"\n🔥 高頻使用鍵 (使用 > 10 次):")
            for key, count in duplicates[:10]:
                print(f"  - {key}: {count} 次")

        # 總結
        print("\n" + "="*70)

        if all_complete:
            print("✅ 所有語言包完整性檢查通過!")
            print("   所有翻譯鍵都已定義且為有效字串")
            return 0
        else:
            print("⚠️  部分語言包存在問題")
            print("   請根據上方報告修復缺失或無效的翻譯鍵")
            return 1

    def export_missing_keys(self, results: Dict[str, Dict], output_file: str):
        """匯出缺失鍵到 YAML 模板"""
        print(f"\n📝 匯出缺失鍵到 {output_file}...")

        missing_by_lang = {}
        for lang_code, data in results.items():
            if data['missing']:
                missing_by_lang[lang_code] = {}
                for key in data['missing']:
                    # 獲取 zh_TW 的值作為參考
                    zh_value = self.get_key_value(key, self.language_packs.get('zh_TW', {}))
                    if zh_value:
                        missing_by_lang[lang_code][key] = f"[TO_TRANSLATE] {zh_value}"
                    else:
                        missing_by_lang[lang_code][key] = "[TO_TRANSLATE]"

        if missing_by_lang:
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(missing_by_lang, f, allow_unicode=True, sort_keys=False)
            print(f"✓ 已匯出缺失鍵模板")
        else:
            print("✓ 無缺失鍵,無需匯出")

def main():
    """主程式"""
    # 檢查虛擬環境
    if 'venv_py314' not in sys.prefix:
        print("❌ 錯誤: 必須在虛擬環境中執行")
        print("✅ 請執行: source venv_py314/bin/activate")
        return 1

    # 檢查專案根目錄
    project_root = Path(__file__).parent
    if not (project_root / 'locales').exists():
        print(f"❌ 錯誤: 找不到 locales 目錄")
        print(f"   當前路徑: {project_root}")
        return 1

    # 執行檢查
    checker = I18nCompletenessChecker(str(project_root))

    print("=" * 70)
    print("i18n 完整性驗證工具")
    print("=" * 70)

    checker.scan_python_files()
    checker.load_language_packs()

    results = checker.check_completeness()
    exit_code = checker.generate_detailed_report(results)

    # 匯出缺失鍵
    output_file = project_root / 'missing_i18n_keys.yaml'
    checker.export_missing_keys(results, str(output_file))

    print("\n" + "=" * 70)
    print(f"報告生成完成")
    print("=" * 70 + "\n")

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
