#!/usr/bin/env python3
"""
自動翻譯缺失的 i18n 鍵值
使用 Gemini API 批次翻譯
"""
import yaml
import os
from pathlib import Path
from utils.api_client import get_gemini_client

def translate_batch(texts, target_lang, source_lang='zh-TW'):
    """批次翻譯"""
    from google import genai
    import os

    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=api_key)

    lang_names = {
        'en': 'English',
        'ja': 'Japanese',
        'ko': 'Korean'
    }

    prompt = f"""Translate the following Traditional Chinese texts to {lang_names[target_lang]}.
Rules:
- Keep Rich markup tags like [bold], [#87CEEB], etc.
- Keep placeholder variables like {{name}}, {{count}}, etc.
- Keep emojis
- Return only the translations, one per line, in the same order

Texts to translate:
"""
    for i, text in enumerate(texts, 1):
        prompt += f"{i}. {text}\n"

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        translations = response.text.strip().split('\n')

        # 清理行號前綴
        cleaned = []
        for line in translations:
            # 移除 "1. ", "2. " 等前綴
            cleaned_line = line
            if '. ' in line[:5]:
                parts = line.split('. ', 1)
                if len(parts) == 2 and parts[0].strip().isdigit():
                    cleaned_line = parts[1]
            cleaned.append(cleaned_line.strip())

        return cleaned
    except Exception as e:
        print(f"翻譯錯誤: {e}")
        return texts  # 失敗時返回原文

def main():
    base_path = Path('/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/locales')

    # 讀取所有語言檔
    with open(base_path / 'zh_TW.yaml', 'r', encoding='utf-8') as f:
        zh_data = yaml.safe_load(f)
    with open(base_path / 'en.yaml', 'r', encoding='utf-8') as f:
        en_data = yaml.safe_load(f) or {}
    with open(base_path / 'ja.yaml', 'r', encoding='utf-8') as f:
        ja_data = yaml.safe_load(f) or {}
    with open(base_path / 'ko.yaml', 'r', encoding='utf-8') as f:
        ko_data = yaml.safe_load(f) or {}

    # 收集需要翻譯的內容
    to_translate = {'en': {}, 'ja': {}, 'ko': {}}

    for ns in zh_data:
        if not isinstance(zh_data[ns], dict):
            continue

        for key, value in zh_data[ns].items():
            if not isinstance(value, str):
                continue

            full_key = f"{ns}.{key}"

            # 檢查英文
            if ns not in en_data or key not in en_data[ns]:
                if ns not in to_translate['en']:
                    to_translate['en'][ns] = {}
                to_translate['en'][ns][key] = value

            # 檢查日文
            if ns not in ja_data or key not in ja_data[ns]:
                if ns not in to_translate['ja']:
                    to_translate['ja'][ns] = {}
                to_translate['ja'][ns][key] = value

            # 檢查韓文
            if ns not in ko_data or key not in ko_data[ns]:
                if ns not in to_translate['ko']:
                    to_translate['ko'][ns] = {}
                to_translate['ko'][ns][key] = value

    print("=" * 70)
    print("自動翻譯 i18n 缺失鍵值")
    print("=" * 70)
    print(f"英文缺失: {sum(len(v) for v in to_translate['en'].values())} 個鍵")
    print(f"日文缺失: {sum(len(v) for v in to_translate['ja'].values())} 個鍵")
    print(f"韓文缺失: {sum(len(v) for v in to_translate['ko'].values())} 個鍵")
    print()

    # 批次翻譯
    batch_size = 50

    for lang in ['en', 'ja', 'ko']:
        if not to_translate[lang]:
            continue

        print(f"正在翻譯到 {lang.upper()}...")

        all_items = []
        for ns in to_translate[lang]:
            for key, value in to_translate[lang][ns].items():
                all_items.append((ns, key, value))

        total = len(all_items)
        translated_count = 0

        # 分批翻譯
        for i in range(0, total, batch_size):
            batch = all_items[i:i+batch_size]
            texts = [item[2] for item in batch]

            print(f"  翻譯批次 {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} ({len(batch)} 個鍵)...")
            translations = translate_batch(texts, lang)

            # 寫入結果
            for j, (ns, key, original) in enumerate(batch):
                if j < len(translations):
                    # 確保命名空間存在
                    if lang == 'en':
                        if ns not in en_data:
                            en_data[ns] = {}
                        en_data[ns][key] = translations[j]
                    elif lang == 'ja':
                        if ns not in ja_data:
                            ja_data[ns] = {}
                        ja_data[ns][key] = translations[j]
                    elif lang == 'ko':
                        if ns not in ko_data:
                            ko_data[ns] = {}
                        ko_data[ns][key] = translations[j]
                    translated_count += 1

        print(f"  ✓ {lang.upper()} 完成 {translated_count}/{total} 個翻譯")

    # 寫入檔案
    print("\n正在寫入語言檔案...")

    with open(base_path / 'en.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(en_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("✓ en.yaml 已更新")

    with open(base_path / 'ja.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(ja_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("✓ ja.yaml 已更新")

    with open(base_path / 'ko.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(ko_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("✓ ko.yaml 已更新")

    print("\n" + "=" * 70)
    print("翻譯完成！")
    print("=" * 70)

if __name__ == "__main__":
    main()
