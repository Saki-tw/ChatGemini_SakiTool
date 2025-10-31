#!/usr/bin/env python3
"""
ChatGemini 智能更新模組
策略: 小改動智能合併,大改動直接覆蓋
"""

import os
import subprocess
import shutil
import re
import ast
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()

# ==========================================
# 配置
# ==========================================

CONFIG_FILE = 'config.py'
BACKUP_DIR = 'backups'
SAFE_MERGE_THRESHOLD = 20  # 改動分數閾值

# ==========================================
# 改動檢測
# ==========================================

def extract_assignments(content: str) -> Dict[str, str]:
    """
    提取 Python 檔案中的所有賦值語句

    Returns:
        {變數名: 賦值表達式}
    """
    assignments = {}

    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # 只處理簡單賦值 (單一目標)
                if len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        # 取得賦值的原始程式碼
                        value_str = ast.get_source_segment(content, node.value)
                        if value_str:
                            assignments[var_name] = value_str
    except SyntaxError:
        # 語法錯誤,使用正則 fallback
        for line in content.splitlines():
            match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.+)$', line.strip())
            if match:
                var_name, value = match.groups()
                assignments[var_name] = value.strip()

    return assignments


def detect_structural_changes(old_content: str, new_content: str) -> Tuple[int, List[str]]:
    """
    檢測結構性改動程度

    Returns:
        (改動分數, 改動詳情列表)
    """
    score = 0
    changes = []

    old_assignments = extract_assignments(old_content)
    new_assignments = extract_assignments(new_content)

    old_vars = set(old_assignments.keys())
    new_vars = set(new_assignments.keys())

    # 1. 新增變數 (分數低)
    added_vars = new_vars - old_vars
    if added_vars:
        score += len(added_vars) * 1
        changes.append(f"新增 {len(added_vars)} 個變數: {', '.join(list(added_vars)[:3])}...")

    # 2. 刪除變數 (分數中)
    removed_vars = old_vars - new_vars
    if removed_vars:
        score += len(removed_vars) * 5
        changes.append(f"移除 {len(removed_vars)} 個變數: {', '.join(list(removed_vars)[:3])}...")

    # 3. 型別改變 (分數高)
    common_vars = old_vars & new_vars
    type_changes = 0

    for var in common_vars:
        old_val = old_assignments[var]
        new_val = new_assignments[var]

        # 簡單型別檢測
        old_type = detect_value_type(old_val)
        new_type = detect_value_type(new_val)

        if old_type != new_type:
            type_changes += 1
            score += 15
            if type_changes <= 3:  # 只顯示前3個
                changes.append(f"型別改變: {var} ({old_type} → {new_type})")

    if type_changes > 3:
        changes.append(f"...還有 {type_changes - 3} 個型別改變")

    # 4. 行數變化 (粗略判斷結構改動)
    old_lines = len(old_content.splitlines())
    new_lines = len(new_content.splitlines())
    line_diff = abs(new_lines - old_lines)

    if line_diff > 100:
        score += 10
        changes.append(f"檔案大小變化: {line_diff} 行")

    return score, changes


def detect_value_type(value_str: str) -> str:
    """檢測值的類型"""
    value_str = value_str.strip()

    if value_str.startswith('{') and value_str.endswith('}'):
        return 'dict'
    elif value_str.startswith('[') and value_str.endswith(']'):
        return 'list'
    elif value_str.startswith('(') and value_str.endswith(')'):
        return 'tuple'
    elif value_str.startswith('"') or value_str.startswith("'"):
        return 'str'
    elif value_str in ('True', 'False'):
        return 'bool'
    elif value_str == 'None':
        return 'None'
    elif value_str.isdigit() or (value_str.startswith('-') and value_str[1:].isdigit()):
        return 'int'
    elif '.' in value_str:
        try:
            float(value_str)
            return 'float'
        except:
            pass

    return 'unknown'


# ==========================================
# 智能合併
# ==========================================

def smart_merge_config(old_content: str, new_content: str) -> str:
    """
    智能合併配置檔案 (僅處理簡單賦值)

    策略:
    - 保留舊檔案中的賦值
    - 採用新檔案的結構與註解
    - 加入新檔案中新增的變數
    """
    old_assignments = extract_assignments(old_content)
    new_lines = new_content.splitlines()

    result_lines = []

    for line in new_lines:
        # 檢查是否為賦值語句
        match = re.match(r'^(\s*)([A-Z_][A-Z0-9_]*)\s*=\s*(.+)$', line)

        if match:
            indent, var_name, new_value = match.groups()

            # 如果舊檔案中有這個變數,使用舊的值
            if var_name in old_assignments:
                old_value = old_assignments[var_name]
                result_lines.append(f'{indent}{var_name} = {old_value}')
            else:
                # 新變數,保留新值
                result_lines.append(line)
        else:
            # 非賦值語句 (註解、空行等),直接保留
            result_lines.append(line)

    return '\n'.join(result_lines)


# ==========================================
# 備份與恢復
# ==========================================

def create_backup() -> str:
    """
    建立備份

    Returns:
        備份目錄路徑
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'backup_{timestamp}')

    os.makedirs(backup_path, exist_ok=True)

    # 備份 config.py
    if os.path.exists(CONFIG_FILE):
        shutil.copy2(CONFIG_FILE, os.path.join(backup_path, 'config.py'))

    # 備份 .env (如果存在)
    if os.path.exists('.env'):
        shutil.copy2('.env', os.path.join(backup_path, '.env'))

    return backup_path


def restore_backup(backup_path: str) -> bool:
    """恢復備份"""
    try:
        config_backup = os.path.join(backup_path, 'config.py')
        if os.path.exists(config_backup):
            shutil.copy2(config_backup, CONFIG_FILE)
            return True
    except Exception as e:
        console.print(f"[red]恢復備份失敗: {e}[/red]")

    return False


# ==========================================
# Git 操作
# ==========================================

def git_fetch_and_compare() -> Tuple[bool, str, str]:
    """
    取得遠端更新並比對 config.py

    Returns:
        (是否有更新, 本地 config.py, 遠端 config.py)
    """
    # Fetch 遠端更新
    result = subprocess.run(
        ['git', 'fetch', 'origin', 'main'],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        return False, "", ""

    # 讀取本地 config.py
    local_config = ""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            local_config = f.read()

    # 讀取遠端 config.py
    result = subprocess.run(
        ['git', 'show', f'origin/main:{CONFIG_FILE}'],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode != 0:
        return False, local_config, ""

    remote_config = result.stdout

    # 比對是否相同
    has_update = local_config != remote_config

    return has_update, local_config, remote_config


def git_pull_force() -> bool:
    """強制 git pull (覆蓋本地修改)"""
    try:
        # 重置本地修改
        subprocess.run(['git', 'reset', '--hard', 'HEAD'], check=True)

        # Pull 遠端更新
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            capture_output=True,
            text=True,
            timeout=30
        )

        return result.returncode == 0
    except:
        return False


# ==========================================
# 主要更新流程
# ==========================================

def upgrade_interactive():
    """互動式更新流程"""

    console.print("\n[bold #B565D8]╔═══════════════════════════════════════════════════════╗[/bold #B565D8]")
    console.print("[bold #B565D8]║          ChatGemini 智能更新                          ║[/bold #B565D8]")
    console.print("[bold #B565D8]╚═══════════════════════════════════════════════════════╝[/bold #B565D8]\n")

    # 1. 檢查更新
    console.print("🔍 檢查遠端更新...")

    try:
        has_update, local_config, remote_config = git_fetch_and_compare()
    except Exception as e:
        console.print(f"[red]✗ 檢查更新失敗: {e}[/red]")
        return False

    if not has_update:
        console.print("[green]✓ 已是最新版本,無需更新[/green]")
        return True

    console.print("[yellow]✓ 發現可用更新[/yellow]\n")

    # 2. 分析改動
    console.print("📊 分析改動程度...")

    score, changes = detect_structural_changes(local_config, remote_config)

    console.print(f"\n改動分析:")
    for change in changes:
        console.print(f"  • {change}")
    console.print(f"\n改動分數: {score} (閾值: {SAFE_MERGE_THRESHOLD})")

    # 3. 決定策略
    if score <= SAFE_MERGE_THRESHOLD:
        console.print("\n[green]✓ 檢測到小規模改動,可以智能合併[/green]")
        strategy = "merge"
    else:
        console.print("\n[yellow]⚠️  檢測到大規模改動,建議直接覆蓋[/yellow]")
        strategy = "overwrite"

    # 4. 詢問使用者
    console.print()

    if strategy == "merge":
        console.print(Panel(
            "[#B565D8]更新策略: 智能合併[/#B565D8]\n\n"
            "✓ 保留您在 config.py 中的賦值\n"
            "✓ 採用新版本的結構與註解\n"
            "✓ 加入新版本的新增變數\n\n"
            "[dim]註: 您的 .env 檔案不會被修改[/dim]",
            border_style="#B565D8"
        ))
    else:
        console.print(Panel(
            "[#FFD700]更新策略: 直接覆蓋[/#FFD700]\n\n"
            "⚠️  config.py 會被新版本完全覆蓋\n"
            "✓ 會在更新前自動備份\n"
            "✓ 您的 .env 檔案不會被修改\n\n"
            "[dim]註: 更新後可能需要重新檢查 config.py 設定[/dim]",
            border_style="#FFD700"
        ))

    console.print()

    if not Confirm.ask("是否繼續更新?", default=True):
        console.print("[yellow]已取消更新[/yellow]")
        return False

    # 5. 建立備份
    console.print("\n💾 建立備份...")
    backup_path = create_backup()
    console.print(f"[green]✓ 已備份到: {backup_path}[/green]")

    # 6. 執行更新
    console.print(f"\n⬇️  執行更新 (策略: {strategy})...")

    try:
        if strategy == "merge":
            # 智能合併
            merged_config = smart_merge_config(local_config, remote_config)

            # 寫入合併結果
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(merged_config)

            # Pull 其他檔案
            result = subprocess.run(
                ['git', 'pull', 'origin', 'main'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if "CONFLICT" in result.stderr:
                    console.print("[yellow]⚠️  檢測到衝突,切換為覆蓋模式[/yellow]")
                    subprocess.run(['git', 'merge', '--abort'], capture_output=True)
                    strategy = "overwrite"  # 改用覆蓋模式
                else:
                    raise Exception(result.stderr)

        if strategy == "overwrite":
            # 直接覆蓋
            success = git_pull_force()

            if not success:
                raise Exception("git pull 失敗")

        console.print("[green]✓ 更新成功[/green]")

    except Exception as e:
        console.print(f"[red]✗ 更新失敗: {e}[/red]")
        console.print("\n正在恢復備份...")

        if restore_backup(backup_path):
            console.print("[green]✓ 已恢復備份[/green]")
        else:
            console.print(f"[red]✗ 自動恢復失敗,請手動從 {backup_path} 恢復[/red]")

        return False

    # 7. 顯示變更日誌
    console.print("\n📝 最近的變更:")
    subprocess.run(['git', 'log', '--oneline', '-5'])

    # 8. 完成提示
    console.print()
    console.print(Panel(
        "[bold green]🎉 更新完成！[/bold green]\n\n"
        f"備份位置: {backup_path}\n\n"
        "建議:\n"
        "  1. 檢查 config.py 中的 MODULES 設定\n"
        "  2. 重新啟動程式以使用新版本\n\n"
        "[dim]如遇問題,可從備份恢復: cp {}/config.py ./config.py[/dim]".format(backup_path),
        border_style="green"
    ))

    return True


# ==========================================
# 測試函數
# ==========================================

def test_change_detection():
    """測試改動檢測"""

    old = """
API_KEY = "test-key"
DEFAULT_MODEL = "gemini-2.0-flash"
ENABLE_CACHE = True
MAX_TOKENS = 1000
"""

    new_small = """
API_KEY = ""
DEFAULT_MODEL = "gemini-2.0-flash"
ENABLE_CACHE = True
MAX_TOKENS = 1000
NEW_SETTING = False  # 新增
"""

    new_large = """
AUTH = {
    'api_key': "",
    'region': "us"
}
MODEL = {
    'primary': "gemini-2.5-flash",
    'fallback': "gemini-2.0-flash"
}
CACHE_ENABLED = True
"""

    print("=== 小改動測試 ===")
    score, changes = detect_structural_changes(old, new_small)
    print(f"分數: {score}")
    for c in changes:
        print(f"  {c}")

    print("\n=== 大改動測試 ===")
    score, changes = detect_structural_changes(old, new_large)
    print(f"分數: {score}")
    for c in changes:
        print(f"  {c}")

    print("\n=== 智能合併測試 ===")
    merged = smart_merge_config(old, new_small)
    print(merged)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_change_detection()
    else:
        upgrade_interactive()
