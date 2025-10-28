#!/usr/bin/env python3
"""
整合 Phase 5 語言包到主語言包
"""
import yaml
from pathlib import Path


def load_yaml(filepath):
    """載入 YAML 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_yaml(filepath, data):
    """儲存 YAML 檔案"""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=True, indent=2)


def deep_merge(base, updates):
    """深度合併兩個字典"""
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def main():
    """主函數"""
    print("="*70)
    print("整合 Phase 5 語言包到主語言包")
    print("="*70)

    # Phase 5 語言包
    phase5_zh = load_yaml('phase5_i18n_zh_TW.yaml')
    phase5_en = load_yaml('phase5_i18n_en_US.yaml')

    print(f"\n✓ 載入 Phase 5 語言包")
    print(f"  - 繁中: {len(phase5_zh)} 個模組")
    print(f"  - 英文: {len(phase5_en)} 個模組")

    # 現有語言包
    zh_tw_path = Path('locales/zh_TW.yaml')
    en_path = Path('locales/en.yaml')

    existing_zh = load_yaml(zh_tw_path) if zh_tw_path.exists() else {}
    existing_en = load_yaml(en_path) if en_path.exists() else {}

    print(f"\n✓ 載入現有語言包")
    print(f"  - 繁中: {len(existing_zh)} 個頂層鍵")
    print(f"  - 英文: {len(existing_en)} 個頂層鍵")

    # 備份現有語言包
    if zh_tw_path.exists():
        backup_zh = zh_tw_path.parent / f'{zh_tw_path.stem}_backup.yaml'
        with open(zh_tw_path, 'r') as src, open(backup_zh, 'w') as dst:
            dst.write(src.read())
        print(f"\n✓ 備份繁中語言包: {backup_zh}")

    if en_path.exists():
        backup_en = en_path.parent / f'{en_path.stem}_backup.yaml'
        with open(en_path, 'r') as src, open(backup_en, 'w') as dst:
            dst.write(src.read())
        print(f"✓ 備份英文語言包: {backup_en}")

    # 合併語言包
    print(f"\n⏳ 合併語言包...")
    merged_zh = deep_merge(existing_zh, phase5_zh)
    merged_en = deep_merge(existing_en, phase5_en)

    # 儲存合併後的語言包
    save_yaml(zh_tw_path, merged_zh)
    save_yaml(en_path, merged_en)

    print(f"\n✓ 繁中語言包已更新: {zh_tw_path}")
    print(f"  總計: {len(merged_zh)} 個頂層鍵")

    print(f"✓ 英文語言包已更新: {en_path}")
    print(f"  總計: {len(merged_en)} 個頂層鍵")

    print("\n" + "="*70)
    print("整合完成！")
    print("="*70)


if __name__ == "__main__":
    main()
