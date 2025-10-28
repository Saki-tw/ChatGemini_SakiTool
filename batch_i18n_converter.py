#!/usr/bin/env python3
"""
Phase 5: 批次 i18n 自動轉換工具
自動處理所有剩餘模組的國際化轉換
"""
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

class I18nConverter:
    """i18n 自動轉換器"""

    def __init__(self, scan_report_path: str):
        """初始化轉換器"""
        self.scan_report_path = scan_report_path
        self.findings = []
        self.load_scan_report()

        # 已處理的模組
        self.processed_modules = {'gemini_error_handler.py'}

        # i18n 鍵名計數器（避免重複）
        self.key_counters = defaultdict(int)

        # 語言包條目
        self.i18n_entries_zh = {}
        self.i18n_entries_en = {}

    def load_scan_report(self):
        """載入掃描報告"""
        with open(self.scan_report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.findings = data['findings']
        print(f"✓ 載入 {len(self.findings)} 個掃描結果")

    def get_file_findings(self, filename: str) -> List[Dict]:
        """取得特定檔案的所有發現"""
        return [f for f in self.findings if f['file'] == filename]

    def generate_i18n_key(self, text: str, method: str, module_name: str) -> str:
        """生成 i18n 鍵名"""
        # 模組前綴（移除 gemini_ 和 .py）
        module = module_name.replace('gemini_', '').replace('.py', '')

        # 方法前綴
        method_map = {
            'print': 'msg',
            'f-string': 'msg',
            'logger': 'log',
            'console.print': 'msg',
            'Panel': 'panel',
            'Table': 'table'
        }
        prefix = method_map.get(method, 'text')

        # 文本關鍵詞（取前2-3個中文字）
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]+', text)
        if chinese_chars:
            keyword = ''.join(chinese_chars)[:10]
        else:
            keyword = 'text'

        # 生成基礎鍵名
        base_key = f"{module}.{prefix}.{keyword}"

        # 處理重複（加計數器）
        self.key_counters[base_key] += 1
        if self.key_counters[base_key] > 1:
            return f"{base_key}_{self.key_counters[base_key]}"
        return base_key

    def extract_user_visible_strings(self, filename: str) -> List[Dict]:
        """提取用戶可見字串（排除註釋和 docstrings）"""
        findings = self.get_file_findings(filename)

        # 過濾條件
        user_visible = []
        for f in findings:
            method = f['method']
            line = f['line']
            text = f['original']

            # 排除測試代碼（通常在 if __name__ == "__main__" 之後）
            # 簡化版：只處理 print, console.print, logger 等輸出
            if method in ['print', 'f-string', 'console.print', 'logger', 'Panel', 'Table']:
                user_visible.append(f)

        return user_visible

    def check_has_safe_t_import(self, filepath: Path) -> bool:
        """檢查檔案是否已導入 safe_t"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(2000)  # 只讀前 2000 字元
            return 'from utils.i18n import safe_t' in content
        except:
            return False

    def add_safe_t_import(self, filepath: Path) -> bool:
        """添加 safe_t 導入"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 找到最後一個 import 語句的位置
            last_import_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    last_import_idx = i

            if last_import_idx == -1:
                # 沒有 import，在第一個非註釋行後插入
                for i, line in enumerate(lines):
                    if not line.strip().startswith('#') and line.strip():
                        last_import_idx = i
                        break

            # 插入 safe_t 導入
            if last_import_idx >= 0:
                lines.insert(last_import_idx + 1, 'from utils.i18n import safe_t\n')

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
        except Exception as e:
            print(f"  ✗ 添加導入失敗: {e}")
        return False

    def translate_to_english(self, chinese_text: str) -> str:
        """簡易中翻英（使用規則）"""
        # 常見翻譯對照表
        translations = {
            '成功': 'success',
            '失敗': 'failed',
            '錯誤': 'error',
            '警告': 'warning',
            '載入': 'loading',
            '已載入': 'loaded',
            '卸載': 'unload',
            '已卸載': 'unloaded',
            '檔案': 'file',
            '上傳': 'upload',
            '下載': 'download',
            '讀取': 'read',
            '寫入': 'write',
            '處理': 'processing',
            '完成': 'completed',
            '測試': 'test',
            '已': '',
            '中': 'ing',
            '：': ':',
            '，': ',',
            '。': '.',
            '！': '!',
            '？': '?',
        }

        result = chinese_text
        for zh, en in translations.items():
            result = result.replace(zh, en)

        return result

    def process_module(self, filename: str) -> Dict:
        """處理單一模組"""
        print(f"\n處理模組: {filename}")

        # 取得用戶可見字串
        visible_strings = self.extract_user_visible_strings(filename)
        print(f"  找到 {len(visible_strings)} 個用戶可見字串")

        if len(visible_strings) == 0:
            print(f"  ⊘ 跳過（無用戶可見字串）")
            return {'filename': filename, 'status': 'skipped', 'count': 0}

        # 生成 i18n 條目
        entries_zh = {}
        entries_en = {}

        for item in visible_strings:
            text = item['original']
            method = item['method']

            # 生成鍵名
            key = self.generate_i18n_key(text, method, filename)

            # 儲存繁體中文
            entries_zh[key] = text

            # 生成英文（簡易翻譯）
            en_text = self.translate_to_english(text)
            entries_en[key] = en_text

        self.i18n_entries_zh.update(entries_zh)
        self.i18n_entries_en.update(entries_en)

        print(f"  ✓ 生成 {len(entries_zh)} 個 i18n 條目")

        # 檢查並添加 safe_t 導入
        filepath = Path(filename)
        if not self.check_has_safe_t_import(filepath):
            if self.add_safe_t_import(filepath):
                print(f"  ✓ 添加 safe_t 導入")
            else:
                print(f"  ! 無法添加導入（手動處理）")
        else:
            print(f"  ✓ 已有 safe_t 導入")

        return {
            'filename': filename,
            'status': 'processed',
            'count': len(entries_zh),
            'entries_zh': entries_zh,
            'entries_en': entries_en
        }

    def save_language_packs(self, output_dir: Path):
        """儲存語言包"""
        output_dir.mkdir(exist_ok=True)

        # 繁體中文
        zh_path = output_dir / 'phase5_i18n_zh_TW.yaml'
        with open(zh_path, 'w', encoding='utf-8') as f:
            f.write("# Phase 5: 批次轉換生成的繁體中文語言包\n\n")

            # 按模組分組
            grouped = defaultdict(dict)
            for key, value in sorted(self.i18n_entries_zh.items()):
                parts = key.split('.')
                if len(parts) >= 2:
                    module = parts[0]
                    sub_key = '.'.join(parts[1:])
                    grouped[module][sub_key] = value

            for module, entries in sorted(grouped.items()):
                f.write(f"{module}:\n")
                for sub_key, value in sorted(entries.items()):
                    # 轉義特殊字符
                    escaped = value.replace('"', '\\"').replace('\n', '\\n')
                    f.write(f'  {sub_key}: "{escaped}"\n')
                f.write('\n')

        print(f"\n✓ 繁體中文語言包已儲存: {zh_path}")

        # 英文
        en_path = output_dir / 'phase5_i18n_en_US.yaml'
        with open(en_path, 'w', encoding='utf-8') as f:
            f.write("# Phase 5: Batch-generated English language pack\n\n")

            grouped = defaultdict(dict)
            for key, value in sorted(self.i18n_entries_en.items()):
                parts = key.split('.')
                if len(parts) >= 2:
                    module = parts[0]
                    sub_key = '.'.join(parts[1:])
                    grouped[module][sub_key] = value

            for module, entries in sorted(grouped.items()):
                f.write(f"{module}:\n")
                for sub_key, value in sorted(entries.items()):
                    escaped = value.replace('"', '\\"').replace('\n', '\\n')
                    f.write(f'  {sub_key}: "{escaped}"\n')
                f.write('\n')

        print(f"✓ 英文語言包已儲存: {en_path}")

    def generate_report(self, results: List[Dict]) -> str:
        """生成處理報告"""
        total_modules = len(results)
        processed = [r for r in results if r['status'] == 'processed']
        skipped = [r for r in results if r['status'] == 'skipped']
        total_entries = sum(r.get('count', 0) for r in processed)

        report = f"""
# Phase 5 批次轉換報告

## 處理統計

- **總模組數**: {total_modules}
- **已處理**: {len(processed)} 個模組
- **已跳過**: {len(skipped)} 個模組
- **總 i18n 條目**: {total_entries} 個

## 處理詳情

### 已處理模組
"""
        for r in processed:
            report += f"- {r['filename']}: {r['count']} 個條目\n"

        if skipped:
            report += "\n### 已跳過模組\n"
            for r in skipped:
                report += f"- {r['filename']}: 無用戶可見字串\n"

        report += f"""

## 語言包檔案

- `phase5_i18n_zh_TW.yaml` - 繁體中文
- `phase5_i18n_en_US.yaml` - 英文

## 注意事項

⚠️ **此批次轉換工具只完成了第一步：生成語言包條目**

**仍需手動處理**：
1. 修改每個檔案中的 print/console.print 語句，將硬編碼字串替換為 safe_t() 調用
2. 測試每個模組的 i18n 功能
3. 調整英文翻譯（當前為自動生成，可能不準確）
4. 整合到主語言包 (locales/zh_TW.yaml, locales/en.yaml)

**建議使用 IDE 的搜尋替換功能**，配合生成的語言包進行批次替換。
"""

        return report


def main():
    """主函數"""
    print("="*70)
    print("Phase 5: 批次 i18n 自動轉換工具")
    print("="*70)

    # 初始化轉換器
    converter = I18nConverter('i18n_scan_report.json')

    # 取得所有需要處理的檔案
    all_files = set(f['file'] for f in converter.findings)

    # 排除已處理的
    to_process = sorted(all_files - converter.processed_modules)

    print(f"\n待處理模組: {len(to_process)} 個")
    print("="*70)

    # 處理每個模組
    results = []
    for i, filename in enumerate(to_process, 1):
        print(f"\n[{i}/{len(to_process)}]", end=" ")
        result = converter.process_module(filename)
        results.append(result)

    # 儲存語言包
    print("\n" + "="*70)
    print("儲存語言包...")
    converter.save_language_packs(Path('.'))

    # 生成報告
    report = converter.generate_report(results)
    report_path = Path('PHASE5_BATCH_CONVERSION_REPORT.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✓ 處理報告已儲存: {report_path}")

    print("\n" + "="*70)
    print("批次轉換完成！")
    print("="*70)
    print(f"\n總計生成 {len(converter.i18n_entries_zh)} 個 i18n 條目")
    print("\n⚠️  請注意：仍需手動修改各檔案中的 print 語句")
    print("   建議使用 IDE 搜尋替換功能配合生成的語言包進行處理")


if __name__ == "__main__":
    main()
