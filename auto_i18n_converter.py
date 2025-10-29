#!/usr/bin/env python3
"""
自動 i18n 轉換工具

功能：
1. 掃描 Python 檔案中的硬編碼中文
2. 自動生成語義化翻譯鍵
3. 批次替換為 safe_t() 調用
4. 生成語言包條目模板
5. （可選）使用 AI 自動翻譯其他語言

作者: Saki-tw (with Claude Code)
日期: 2025-10-29
"""

import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

class AutoI18nConverter:
    def __init__(self, dry_run: bool = True):
        """
        初始化轉換器

        Args:
            dry_run: 是否為模擬執行（不實際修改檔案）
        """
        self.dry_run = dry_run
        self.translations = {}  # {key: {lang: translation}}
        self.conversions = []   # 轉換記錄

        # 翻譯鍵計數器（用於生成唯一 key）
        self.key_counters = {}

    def generate_key(self, context: str, text: str, line_num: int) -> str:
        """
        生成語義化的翻譯鍵

        策略：
        1. 從文件路徑提取模組名稱
        2. 從代碼上下文推斷類別
        3. 從文字內容提取關鍵詞
        4. 確保唯一性

        Args:
            context: 上下文（檔案路徑、函數名稱等）
            text: 中文文字
            line_num: 行號

        Returns:
            翻譯鍵，例如：'chat.system.config_loaded'
        """
        # 提取模組名稱
        if 'gemini_chat.py' in context:
            module = 'chat'
        elif 'CodeGemini.py' in context:
            module = 'codegemini'
        elif 'CodeGemini/' in context:
            submodule = context.split('CodeGemini/')[1].split('.py')[0]
            module = f'codegemini.{submodule.replace("/", ".")}'
        else:
            filename = Path(context).stem
            module = filename.replace('gemini_', '').replace('_', '')

        # 分類
        category = self._classify_message(text)

        # 提取關鍵詞
        keyword = self._extract_keyword(text)

        # 組合鍵
        base_key = f"{module}.{category}.{keyword}"

        # 確保唯一性
        if base_key in self.key_counters:
            self.key_counters[base_key] += 1
            return f"{base_key}_{self.key_counters[base_key]}"
        else:
            self.key_counters[base_key] = 0
            return base_key

    def _classify_message(self, text: str) -> str:
        """分類訊息類型"""
        text_lower = text.lower()

        # 系統訊息
        if any(kw in text for kw in ['✅', '已載入', '啟用', '初始化', '配置']):
            return 'system'

        # 錯誤訊息
        if any(kw in text for kw in ['❌', '錯誤', '失敗', '無法', '不存在']):
            return 'error'

        # 警告訊息
        if any(kw in text for kw in ['⚠️', '警告', '注意', '建議']):
            return 'warning'

        # 幫助訊息
        if any(kw in text for kw in ['指令', '命令', '用法', '說明', '範例']):
            return 'help'

        # 提示訊息
        if any(kw in text for kw in ['請', '輸入', '選擇', '確認']):
            return 'prompt'

        # 狀態訊息
        if any(kw in text for kw in ['處理中', '載入中', '完成', '成功']):
            return 'status'

        # 預設為一般訊息
        return 'message'

    def _extract_keyword(self, text: str) -> str:
        """從文字中提取關鍵詞"""
        # 移除表情符號和特殊符號
        clean_text = re.sub(r'[✅❌⚠️💾🧠🔧📝📊🎨🔍]', '', text)
        clean_text = re.sub(r'[\s\(\)（）：:：，,。.！!？?]', '_', clean_text)

        # 移除連續的底線
        clean_text = re.sub(r'_+', '_', clean_text)
        clean_text = clean_text.strip('_')

        # 限制長度
        if len(clean_text) > 30:
            # 取前幾個關鍵詞
            words = clean_text.split('_')
            clean_text = '_'.join(words[:3])

        # 轉為小寫（保留中文）
        # 只轉換英文部分
        result = ''
        for char in clean_text:
            if 'A' <= char <= 'Z':
                result += char.lower()
            else:
                result += char

        return result or 'msg'

    def find_chinese_strings(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """
        找出檔案中的硬編碼中文字串

        Returns:
            List of (line_number, original_line, chinese_text)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            results = []
            for i, line in enumerate(lines, 1):
                # 跳過註解
                if line.strip().startswith('#'):
                    continue

                # 跳過已使用 i18n 的行
                if 'safe_t(' in line or re.search(r'\bt\(', line):
                    continue

                # 跳過 docstring
                if '"""' in line or "'''" in line:
                    continue

                # 檢查是否包含中文且為用戶可見
                if re.search(r'[\u4e00-\u9fff]', line):
                    if self._is_user_visible(line):
                        # 提取中文字串
                        chinese_texts = self._extract_chinese_texts(line)
                        for text in chinese_texts:
                            results.append((i, line, text))

            return results

        except Exception as e:
            print(f"⚠️  讀取失敗: {file_path} - {e}")
            return []

    def _is_user_visible(self, line: str) -> bool:
        """判斷是否為用戶可見訊息"""
        line_lower = line.lower()
        return any(pattern in line_lower for pattern in [
            'print(', 'console.print(', 'logger.info(',
            'logger.warning(', 'logger.error(', 'rich.print(',
            'click.echo(', 'sys.stdout.write(', 'sys.stderr.write('
        ])

    def _extract_chinese_texts(self, line: str) -> List[str]:
        """從行中提取所有中文字串"""
        # 匹配字串字面量
        patterns = [
            r'"([^"]*[\u4e00-\u9fff][^"]*)"',  # 雙引號
            r"'([^']*[\u4e00-\u9fff][^']*)'",  # 單引號
        ]

        texts = []
        for pattern in patterns:
            matches = re.findall(pattern, line)
            texts.extend(matches)

        return texts

    def convert_line(self, original_line: str, chinese_text: str,
                    translation_key: str) -> str:
        """
        轉換單行代碼

        Args:
            original_line: 原始行
            chinese_text: 要替換的中文文字
            translation_key: 翻譯鍵

        Returns:
            轉換後的行
        """
        # 檢查是否有格式化參數
        has_format = '{' in chinese_text and '}' in chinese_text

        # 提取格式化參數
        format_params = []
        if has_format:
            format_params = re.findall(r'\{(\w+)\}', chinese_text)

        # 構建 safe_t() 調用
        if format_params:
            params_str = ', '.join(f'{p}={p}' for p in format_params)
            safe_t_call = f"safe_t('{translation_key}', fallback='{chinese_text}', {params_str})"
        else:
            safe_t_call = f"safe_t('{translation_key}', fallback='{chinese_text}')"

        # 替換原始字串
        # 處理雙引號和單引號
        for quote in ['"', "'"]:
            pattern = f'{quote}{re.escape(chinese_text)}{quote}'
            if pattern.replace('\\', '') in original_line:
                converted_line = original_line.replace(
                    f'{quote}{chinese_text}{quote}',
                    safe_t_call
                )
                return converted_line

        # 如果直接替換失敗，返回原始行
        return original_line

    def convert_file(self, file_path: Path) -> Dict:
        """
        轉換整個檔案

        Returns:
            轉換統計資料
        """
        print(f"\n📄 處理: {file_path}")

        # 找出所有硬編碼中文
        chinese_strings = self.find_chinese_strings(file_path)

        if not chinese_strings:
            print(f"   ✅ 無需轉換")
            return {'converted': 0, 'skipped': 0}

        print(f"   發現 {len(chinese_strings)} 處硬編碼")

        # 讀取檔案內容
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        converted_count = 0
        skipped_count = 0

        # 轉換每一行
        for line_num, original_line, chinese_text in chinese_strings:
            # 生成翻譯鍵
            context = str(file_path)
            translation_key = self.generate_key(context, chinese_text, line_num)

            # 轉換行
            converted_line = self.convert_line(
                original_line,
                chinese_text,
                translation_key
            )

            if converted_line != original_line:
                # 記錄轉換
                lines[line_num - 1] = converted_line

                # 記錄翻譯
                if translation_key not in self.translations:
                    self.translations[translation_key] = {
                        'zh-TW': chinese_text
                    }

                self.conversions.append({
                    'file': str(file_path),
                    'line': line_num,
                    'key': translation_key,
                    'original': original_line.strip(),
                    'converted': converted_line.strip()
                })

                converted_count += 1
                print(f"   Line {line_num:4d}: {translation_key}")
            else:
                skipped_count += 1

        # 寫回檔案（如果不是 dry-run）
        if not self.dry_run and converted_count > 0:
            # 確保檔案開頭有 safe_t 導入
            self._ensure_safe_t_import(lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            print(f"   ✅ 已轉換 {converted_count} 處")
        else:
            print(f"   🔍 [DRY-RUN] 將轉換 {converted_count} 處")

        return {'converted': converted_count, 'skipped': skipped_count}

    def _ensure_safe_t_import(self, lines: List[str]) -> None:
        """確保檔案開頭有 safe_t 導入"""
        # 檢查是否已有導入
        has_import = any('from utils import' in line and 'safe_t' in line
                        for line in lines[:30])  # 只檢查前 30 行

        if not has_import:
            # 尋找合適的插入位置（在其他 import 之後）
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    insert_pos = i + 1

            # 插入導入
            lines.insert(insert_pos, 'from utils import safe_t\n')

    def export_translations(self, output_file: str = 'i18n_translations_new.yaml'):
        """匯出翻譯鍵"""
        import yaml

        print(f"\n📝 匯出翻譯鍵至: {output_file}")
        print(f"   總計: {len(self.translations)} 個鍵")

        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.translations, f, allow_unicode=True, sort_keys=False)

    def export_report(self, output_file: str = 'i18n_conversion_report.json'):
        """匯出轉換報告"""
        print(f"\n📊 匯出轉換報告至: {output_file}")

        report = {
            'total_conversions': len(self.conversions),
            'total_keys': len(self.translations),
            'conversions': self.conversions
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(
        description='自動轉換硬編碼中文至 i18n'
    )
    parser.add_argument(
        'files',
        nargs='+',
        help='要轉換的檔案路徑'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='實際執行轉換（預設為 dry-run）'
    )

    args = parser.parse_args()

    # 創建轉換器
    converter = AutoI18nConverter(dry_run=not args.execute)

    if converter.dry_run:
        print("\n⚠️  DRY-RUN 模式：不會實際修改檔案")
    else:
        print("\n🔧 執行模式：將實際修改檔案")

    print("=" * 80)

    # 轉換每個檔案
    total_converted = 0
    total_skipped = 0

    for file_path_str in args.files:
        file_path = Path(file_path_str)
        if file_path.exists():
            stats = converter.convert_file(file_path)
            total_converted += stats['converted']
            total_skipped += stats['skipped']
        else:
            print(f"❌ 檔案不存在: {file_path}")

    # 匯出結果
    print("\n" + "=" * 80)
    print("📊 轉換總結")
    print("=" * 80)
    print(f"總計轉換: {total_converted} 處")
    print(f"總計跳過: {total_skipped} 處")
    print(f"新增翻譯鍵: {len(converter.translations)} 個")

    if converter.conversions:
        converter.export_translations()
        converter.export_report()

    print("\n✅ 完成")


if __name__ == "__main__":
    main()
