#!/usr/bin/env python3
"""
i18n 批次轉換工具
自動將 Python 檔案中的中文字串轉換為 safe_t() 調用
"""
import re
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import shutil
from datetime import datetime

# 跳過的模式（不轉換這些內容）
SKIP_PATTERNS = [
    r'""".*?"""',  # Docstrings
    r"'''.*?'''",  # Docstrings
    r'#.*$',       # Comments
    r'safe_t\(',   # 已經使用 safe_t 的行
]

# 檔案與翻譯鍵前綴的映射
FILE_KEY_MAPPING = {
    'gemini_async_batch_processor.py': 'batch.async',
    'gemini_file_manager.py': 'file.manager',
    'smart_file_selector.py': 'file.selector',
    'gemini_error_handler.py': 'error.handler',
    'gemini_clip_advisor.py': 'clip.advisor',
    'gemini_upload_helper.py': 'upload.helper',
}

class I18nConverter:
    """i18n 轉換器"""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.translation_keys = {
            'zh_TW': {},
            'en': {},
            'ja': {},
            'ko': {}
        }
        self.stats = {}

    def find_chinese_strings(self, content: str, file_path: str) -> List[Tuple[str, int]]:
        """找出所有需要轉換的中文字串"""
        chinese_pattern = r'(["\'])([^"\']*[\u4e00-\u9fff]+[^"\']*)\1'
        results = []

        for match in re.finditer(chinese_pattern, content, re.MULTILINE):
            line_num = content[:match.start()].count('\n') + 1
            chinese_text = match.group(2)

            # 檢查是否應該跳過
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            if line_end == -1:
                line_end = len(content)
            line = content[line_start:line_end]

            # 跳過已經使用 safe_t 的行
            if 'safe_t(' in line:
                continue

            # 跳過註釋
            if line.strip().startswith('#'):
                continue

            # 跳過 docstring
            if '"""' in line or "'''" in line:
                continue

            results.append((chinese_text, line_num))

        return results

    def generate_key(self, prefix: str, text: str, index: int) -> str:
        """生成翻譯鍵名"""
        # 簡化文字作為鍵的一部分
        simplified = re.sub(r'[^\w\s]', '', text)
        simplified = re.sub(r'\s+', '_', simplified.strip())

        # 如果文字太長，使用索引
        if len(simplified) > 30:
            simplified = f"text_{index}"
        elif not simplified:
            simplified = f"text_{index}"

        return f"{prefix}.{simplified.lower()}"

    def convert_file(self, file_path: str, prefix: str) -> Dict:
        """轉換單個檔案"""
        file_path = Path(file_path)

        if not file_path.exists():
            return {
                'status': 'error',
                'message': f'檔案不存在: {file_path}'
            }

        # 備份原檔案
        backup_path = str(file_path) + f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(file_path, backup_path)

        # 讀取檔案內容
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # 計算原有的 safe_t 數量
        original_safe_t_count = original_content.count('safe_t(')

        # 找出所有中文字串
        chinese_strings = self.find_chinese_strings(original_content, str(file_path))

        if not chinese_strings:
            os.remove(backup_path)  # 沒有需要轉換的，刪除備份
            return {
                'status': 'success',
                'file': str(file_path),
                'before_count': original_safe_t_count,
                'after_count': original_safe_t_count,
                'new_keys': 0,
                'backup': None
            }

        print(f"\n處理 {file_path.name}: 找到 {len(chinese_strings)} 個中文字串")

        # 按位置從後往前替換（避免位置偏移）
        content = original_content
        new_keys = []

        # 由於替換會改變位置，我們需要記錄所有替換，然後從後往前處理
        replacements = []

        for idx, (text, line_num) in enumerate(chinese_strings):
            key = self.generate_key(prefix, text, idx)

            # 檢查鍵是否已存在，如果存在則添加數字後綴
            base_key = key
            counter = 1
            while key in self.translation_keys['zh_TW']:
                key = f"{base_key}_{counter}"
                counter += 1

            # 記錄翻譯鍵
            self.translation_keys['zh_TW'][key] = text
            self.translation_keys['en'][key] = f"[TODO: translate] {text}"
            self.translation_keys['ja'][key] = f"[TODO: translate] {text}"
            self.translation_keys['ko'][key] = f"[TODO: translate] {text}"

            new_keys.append(key)

            # 查找並記錄需要替換的位置
            # 使用更精確的模式匹配
            pattern = rf'(["\']){re.escape(text)}\1'
            for match in re.finditer(pattern, content):
                # 檢查這個位置是否在已經有 safe_t 的行中
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_end = content.find('\n', match.end())
                if line_end == -1:
                    line_end = len(content)
                line = content[line_start:line_end]

                if 'safe_t(' not in line:
                    quote = match.group(1)
                    replacement = f'safe_t({quote}{key}{quote}, fallback={quote}{text}{quote})'
                    replacements.append((match.start(), match.end(), replacement))

        # 從後往前替換
        replacements.sort(key=lambda x: x[0], reverse=True)
        for start, end, replacement in replacements:
            content = content[:start] + replacement + content[end:]

        # 檢查是否需要添加 import
        if 'from utils.i18n import safe_t' not in content and new_keys:
            # 找到其他 import 語句的位置
            import_pos = content.find('import ')
            if import_pos != -1:
                # 在第一個 import 之前插入
                content = content[:import_pos] + 'from utils.i18n import safe_t\n' + content[import_pos:]

        # 寫回檔案
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 計算新的 safe_t 數量
        new_safe_t_count = content.count('safe_t(')

        # 驗證語法
        import py_compile
        try:
            py_compile.compile(str(file_path), doraise=True)
            syntax_ok = True
        except Exception as e:
            print(f"語法錯誤: {e}")
            # 恢復備份
            shutil.copy2(backup_path, file_path)
            syntax_ok = False

        return {
            'status': 'success' if syntax_ok else 'failed',
            'file': str(file_path),
            'before_count': original_safe_t_count,
            'after_count': new_safe_t_count,
            'new_keys': len(new_keys),
            'keys': new_keys,
            'backup': backup_path,
            'syntax_check': 'pass' if syntax_ok else 'fail'
        }

    def convert_files(self, files: List[str]) -> Dict:
        """批次轉換多個檔案"""
        results = {}

        for file_path in files:
            filename = Path(file_path).name
            prefix = FILE_KEY_MAPPING.get(filename, 'unknown')

            print(f"\n{'='*60}")
            print(f"處理檔案: {filename}")
            print(f"翻譯鍵前綴: {prefix}")
            print(f"{'='*60}")

            result = self.convert_file(file_path, prefix)
            results[filename] = result

            if result['status'] == 'success':
                print(f"✓ 成功: {result['new_keys']} 個新鍵")
            else:
                print(f"✗ 失敗: {result.get('message', '未知錯誤')}")

        return results

    def generate_report(self, results: Dict) -> Dict:
        """生成報告"""
        total_files = len(results)
        total_conversions = sum(r.get('new_keys', 0) for r in results.values())
        successful = sum(1 for r in results.values() if r['status'] == 'success')

        report = {
            'files_processed': total_files,
            'successful': successful,
            'failed': total_files - successful,
            'total_conversions': total_conversions,
            'files_detail': results,
            'translation_keys': self.translation_keys,
            'summary': {
                'zh_TW_keys': len(self.translation_keys['zh_TW']),
                'en_keys': len(self.translation_keys['en']),
                'ja_keys': len(self.translation_keys['ja']),
                'ko_keys': len(self.translation_keys['ko'])
            }
        }

        return report


def main():
    """主程式"""
    base_dir = '/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool'

    # 要處理的檔案
    files_to_process = [
        os.path.join(base_dir, 'gemini_async_batch_processor.py'),
        os.path.join(base_dir, 'gemini_file_manager.py'),
        os.path.join(base_dir, 'smart_file_selector.py'),
        os.path.join(base_dir, 'gemini_error_handler.py'),
        os.path.join(base_dir, 'gemini_clip_advisor.py'),
        os.path.join(base_dir, 'gemini_upload_helper.py'),
    ]

    converter = I18nConverter(base_dir)

    print("開始批次轉換...")
    print(f"基礎目錄: {base_dir}")
    print(f"檔案數量: {len(files_to_process)}")

    results = converter.convert_files(files_to_process)
    report = converter.generate_report(results)

    # 儲存報告
    report_path = os.path.join(base_dir, 'i18n_conversion_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*60}")
    print("轉換完成!")
    print(f"{'='*60}")
    print(f"處理檔案: {report['files_processed']}")
    print(f"成功: {report['successful']}")
    print(f"失敗: {report['failed']}")
    print(f"總轉換數: {report['total_conversions']}")
    print(f"報告已儲存至: {report_path}")

    return report


if __name__ == '__main__':
    report = main()
    sys.exit(0 if report['failed'] == 0 else 1)
