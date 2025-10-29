#!/usr/bin/env python3
"""
孤兒檔案分析工具
分析專案中沒有被其他檔案導入的 Python 檔案
"""

import os
import re
from pathlib import Path
from typing import Set, Dict, List

# 排除的目錄
EXCLUDE_DIRS = {'venv_py314', '__pycache__', '.git', 'node_modules', 'deprecated'}

# 核心入口檔案（這些檔案不會被標記為孤兒）
ENTRY_POINTS = {
    'gemini_chat.py',
    'CodeGemini.py',
    'gemini_lang.py',
    'INSTALL.sh',
    'setup.py'
}

# 工具腳本類別（可能是孤兒但有用途）
TOOL_SCRIPTS = {
    'analyze_', 'test_', 'verify_', 'profile_', 'measure_',
    'batch_', 'scan_', 'extract_', 'collect_', 'merge_',
    'migrate_', 'translate_', 'convert_', 'update_', 'create_',
    'cleanup_', 'fix_', 'auto_', 'comprehensive_', 'i18n_'
}

def get_python_files(root_dir: Path) -> List[Path]:
    """獲取所有 Python 檔案"""
    python_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 排除特定目錄
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            if filename.endswith('.py'):
                filepath = Path(dirpath) / filename
                python_files.append(filepath.relative_to(root_dir))

    return python_files

def extract_imports(filepath: Path) -> Set[str]:
    """提取檔案中的所有導入"""
    imports = set()

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 import xxx
        for match in re.finditer(r'^import\s+([\w.]+)', content, re.MULTILINE):
            imports.add(match.group(1))

        # 匹配 from xxx import yyy
        for match in re.finditer(r'^from\s+([\w.]+)\s+import', content, re.MULTILINE):
            imports.add(match.group(1))

    except Exception as e:
        print(f"警告: 讀取 {filepath} 失敗: {e}")

    return imports

def module_to_file(module_name: str, root_dir: Path) -> Set[Path]:
    """將模組名稱轉換為可能的檔案路徑"""
    possible_files = set()

    # 處理相對導入
    parts = module_name.split('.')

    # 可能是單一檔案
    possible_files.add(Path(f"{module_name.replace('.', '/')}.py"))

    # 可能是包
    possible_files.add(Path(f"{module_name.replace('.', '/')}/__init__.py"))

    # 處理第一級模組
    if len(parts) > 0:
        possible_files.add(Path(f"{parts[0]}.py"))
        possible_files.add(Path(f"{parts[0]}/__init__.py"))

    return possible_files

def is_tool_script(filename: str) -> bool:
    """判斷是否為工具腳本"""
    for prefix in TOOL_SCRIPTS:
        if filename.startswith(prefix):
            return True
    return False

def analyze_orphans(root_dir: Path):
    """分析孤兒檔案"""
    print("🔍 掃描專案檔案...")
    python_files = get_python_files(root_dir)
    print(f"找到 {len(python_files)} 個 Python 檔案\n")

    print("📊 分析導入關係...")
    # 建立導入關係圖
    imported_modules = set()

    for filepath in python_files:
        imports = extract_imports(root_dir / filepath)
        for imp in imports:
            possible_files = module_to_file(imp, root_dir)
            imported_modules.update(possible_files)

    # 識別孤兒檔案
    print("\n" + "="*80)
    print("🧹 孤兒檔案分析結果")
    print("="*80)

    orphans = []
    tool_scripts = []
    entry_points = []
    active_files = []

    for filepath in python_files:
        filename = filepath.name

        # 分類
        if filename in ENTRY_POINTS or str(filepath) in ENTRY_POINTS:
            entry_points.append(filepath)
        elif is_tool_script(filename):
            # 檢查是否被導入
            if filepath not in imported_modules:
                tool_scripts.append(filepath)
            else:
                active_files.append(filepath)
        elif filepath in imported_modules:
            active_files.append(filepath)
        else:
            orphans.append(filepath)

    # 輸出結果
    print(f"\n✅ 活躍檔案: {len(active_files)} 個")
    print(f"🚪 入口點: {len(entry_points)} 個")
    print(f"🔧 工具腳本 (未被導入): {len(tool_scripts)} 個")
    print(f"👻 孤兒檔案: {len(orphans)} 個\n")

    # 詳細列表
    if orphans:
        print("\n" + "="*80)
        print("👻 孤兒檔案列表 (可能可以刪除)")
        print("="*80)
        for f in sorted(orphans):
            size = (root_dir / f).stat().st_size
            print(f"  ❌ {f} ({size:,} bytes)")

    if tool_scripts:
        print("\n" + "="*80)
        print("🔧 工具腳本列表 (未被導入但可能有用)")
        print("="*80)
        for f in sorted(tool_scripts):
            size = (root_dir / f).stat().st_size
            print(f"  ⚠️  {f} ({size:,} bytes)")

    # 統計
    total_orphan_size = sum((root_dir / f).stat().st_size for f in orphans)
    total_tool_size = sum((root_dir / f).stat().st_size for f in tool_scripts)

    print("\n" + "="*80)
    print("📊 統計摘要")
    print("="*80)
    print(f"孤兒檔案總大小: {total_orphan_size:,} bytes ({total_orphan_size/1024:.1f} KB)")
    print(f"工具腳本總大小: {total_tool_size:,} bytes ({total_tool_size/1024:.1f} KB)")
    print(f"可節省空間: {(total_orphan_size + total_tool_size):,} bytes ({(total_orphan_size + total_tool_size)/1024:.1f} KB)")

    return {
        'orphans': orphans,
        'tool_scripts': tool_scripts,
        'entry_points': entry_points,
        'active_files': active_files,
        'total_orphan_size': total_orphan_size,
        'total_tool_size': total_tool_size
    }

if __name__ == "__main__":
    root_dir = Path.cwd()
    result = analyze_orphans(root_dir)

    print("\n✅ 分析完成！")
