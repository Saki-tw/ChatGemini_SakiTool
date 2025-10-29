#!/usr/bin/env python3
"""
孤兒檔案清理工具
智能識別並清理專案中的孤兒檔案
"""
import os
import subprocess
from pathlib import Path
from datetime import datetime

# 可刪除的檔案類型
DELETABLE_PATTERNS = [
    '*.py.backup',
    '*.py.new',
    '*.py.old',
    '*.py.bak',
    '*.pyc',
    '*__pycache__*'
]

# 排除目錄
EXCLUDE_DIRS = {'venv_py314', '.git', 'node_modules'}

def get_deletable_files(root_dir: Path) -> dict:
    """獲取可刪除的檔案"""
    result = {
        'backup_files': [],
        'cache_files': [],
        'total_size': 0
    }

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 排除特定目錄
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            filepath = Path(dirpath) / filename

            # 備份檔案
            if any(filename.endswith(ext.replace('*', '')) for ext in ['.backup', '.new', '.old', '.bak']):
                if '.py' in filename:
                    size = filepath.stat().st_size
                    result['backup_files'].append({
                        'path': filepath,
                        'size': size
                    })
                    result['total_size'] += size

            # 快取檔案
            elif filename.endswith('.pyc') or '__pycache__' in str(filepath):
                size = filepath.stat().st_size
                result['cache_files'].append({
                    'path': filepath,
                    'size': size
                })
                result['total_size'] += size

    return result

def cleanup_files(files_info: dict, dry_run: bool = True) -> dict:
    """
    清理檔案

    Args:
        files_info: 檔案資訊
        dry_run: 是否為試運行（True=僅列出，False=實際刪除）

    Returns:
        清理統計資訊
    """
    stats = {
        'deleted_count': 0,
        'deleted_size': 0,
        'failed': []
    }

    all_files = files_info['backup_files'] + files_info['cache_files']

    for file_info in all_files:
        filepath = file_info['path']
        size = file_info['size']

        if dry_run:
            stats['deleted_count'] += 1
            stats['deleted_size'] += size
        else:
            try:
                if filepath.exists():
                    if filepath.is_dir():
                        # 刪除目錄（如 __pycache__）
                        import shutil
                        shutil.rmtree(filepath)
                    else:
                        # 刪除檔案
                        filepath.unlink()
                    stats['deleted_count'] += 1
                    stats['deleted_size'] += size
            except Exception as e:
                stats['failed'].append({
                    'path': filepath,
                    'error': str(e)
                })

    return stats

def main():
    """主函數"""
    root_dir = Path.cwd()

    print("=" * 80)
    print("🧹 孤兒檔案清理工具")
    print("=" * 80)
    print()

    # 掃描檔案
    print("📊 掃描可刪除檔案...")
    files_info = get_deletable_files(root_dir)

    backup_count = len(files_info['backup_files'])
    cache_count = len(files_info['cache_files'])
    total_size = files_info['total_size']

    print(f"\n找到以下檔案:")
    print(f"  - 備份檔案: {backup_count} 個")
    print(f"  - 快取檔案: {cache_count} 個")
    print(f"  - 總大小: {total_size:,} bytes ({total_size/1024:.1f} KB)")

    if backup_count + cache_count == 0:
        print("\n✅ 沒有需要清理的檔案！")
        return

    # 顯示詳細列表
    if backup_count > 0:
        print(f"\n備份檔案列表（前 10 個）:")
        for i, file_info in enumerate(files_info['backup_files'][:10], 1):
            rel_path = file_info['path'].relative_to(root_dir)
            size = file_info['size']
            print(f"  {i}. {rel_path} ({size:,} bytes)")
        if backup_count > 10:
            print(f"  ... 還有 {backup_count - 10} 個檔案")

    # 詢問確認
    print("\n" + "=" * 80)
    choice = input("是否刪除這些檔案？(y/N): ").strip().lower()

    if choice == 'y':
        print("\n🗑️  刪除檔案中...")
        stats = cleanup_files(files_info, dry_run=False)

        print("\n✅ 清理完成！")
        print(f"  - 刪除檔案數: {stats['deleted_count']} 個")
        print(f"  - 釋放空間: {stats['deleted_size']:,} bytes ({stats['deleted_size']/1024:.1f} KB)")

        if stats['failed']:
            print(f"\n⚠️  刪除失敗: {len(stats['failed'])} 個")
            for fail in stats['failed'][:5]:
                print(f"  - {fail['path']}: {fail['error']}")
    else:
        print("\n❌ 已取消清理操作")

if __name__ == "__main__":
    main()
