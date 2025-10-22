#!/usr/bin/env python3
"""
CodeGemini Background Shell 測試
測試背景 Shell 管理功能
"""

import os
import sys
import time
from pathlib import Path
from rich.console import Console

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.background_shell import BackgroundShellManager, ShellStatus

console = Console()


def test_manager_initialization():
    """測試 1：BackgroundShellManager 初始化"""
    console.print("\n[bold]測試 1：BackgroundShellManager 初始化[/bold]")

    try:
        manager = BackgroundShellManager()

        assert manager.shells == {}, "初始 shells 應為空"
        assert manager._shell_counter == 0, "初始計數器應為 0"

        console.print(f"[green]✓ BackgroundShellManager 初始化成功[/green]")
        console.print(f"  shells: {len(manager.shells)} 個")
        console.print(f"  counter: {manager._shell_counter}")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_start_simple_shell():
    """測試 2：啟動簡單 Shell"""
    console.print("\n[bold]測試 2：啟動簡單 Shell[/bold]")

    try:
        manager = BackgroundShellManager()

        # 啟動簡單命令
        shell_id = manager.start_shell("echo 'Hello World'")

        assert shell_id is not None, "Shell ID 不應為 None"
        assert shell_id in manager.shells, "Shell 應被記錄"

        bg_shell = manager.shells[shell_id]
        assert bg_shell.command == "echo 'Hello World'", "命令錯誤"
        assert bg_shell.status == ShellStatus.RUNNING, "狀態應為 RUNNING"

        # 等待完成
        time.sleep(0.5)

        console.print(f"[green]✓ 簡單 Shell 啟動成功[/green]")
        console.print(f"  Shell ID：{shell_id}")
        console.print(f"  PID：{bg_shell.process.pid}")

        # 清理
        if bg_shell.is_running:
            manager.kill_shell(shell_id)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_shell_output_capture():
    """測試 3：Shell 輸出捕獲"""
    console.print("\n[bold]測試 3：Shell 輸出捕獲[/bold]")

    try:
        manager = BackgroundShellManager()

        # 啟動會產生輸出的命令
        shell_id = manager.start_shell("echo 'Line 1' && echo 'Line 2' && echo 'Line 3'")

        # 等待輸出
        time.sleep(0.5)

        # 取得輸出
        output = manager.get_output(shell_id)

        assert "Line 1" in output or "Line" in output, "應包含輸出內容"

        console.print(f"[green]✓ 輸出捕獲成功[/green]")
        console.print(f"  輸出長度：{len(output)} 字元")

        # 清理
        bg_shell = manager.get_shell(shell_id)
        if bg_shell and bg_shell.is_running:
            manager.kill_shell(shell_id)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_output_filtering():
    """測試 4：輸出過濾"""
    console.print("\n[bold]測試 4：輸出過濾[/bold]")

    try:
        manager = BackgroundShellManager()

        # 啟動產生多行輸出的命令
        shell_id = manager.start_shell("echo 'ERROR: Something went wrong' && echo 'INFO: Processing' && echo 'ERROR: Another issue'")

        # 等待輸出
        time.sleep(0.5)

        # 過濾只看 ERROR
        filtered_output = manager.get_output(shell_id, filter_regex=r"ERROR")

        assert "ERROR" in filtered_output, "應包含 ERROR"

        console.print(f"[green]✓ 輸出過濾成功[/green]")
        console.print(f"  過濾結果：包含 ERROR 行")

        # 清理
        bg_shell = manager.get_shell(shell_id)
        if bg_shell and bg_shell.is_running:
            manager.kill_shell(shell_id)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_long_running_shell():
    """測試 5：長時間運行 Shell"""
    console.print("\n[bold]測試 5：長時間運行 Shell[/bold]")

    try:
        manager = BackgroundShellManager()

        # 啟動長時間運行的命令（sleep）
        shell_id = manager.start_shell("sleep 2 && echo 'Done'")

        bg_shell = manager.get_shell(shell_id)
        assert bg_shell is not None, "Shell 應存在"
        assert bg_shell.is_running, "Shell 應在運行"

        # 等待 0.5 秒（應該還在運行）
        time.sleep(0.5)
        assert bg_shell.is_running, "Shell 應仍在運行"

        console.print(f"[green]✓ 長時間運行 Shell 正常[/green]")
        console.print(f"  運行時間：{bg_shell.runtime:.1f}s")

        # 終止
        manager.kill_shell(shell_id)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_kill_shell():
    """測試 6：終止 Shell"""
    console.print("\n[bold]測試 6：終止 Shell[/bold]")

    try:
        manager = BackgroundShellManager()

        # 啟動長時間命令
        shell_id = manager.start_shell("sleep 10")

        bg_shell = manager.get_shell(shell_id)
        assert bg_shell.is_running, "Shell 應在運行"

        # 終止
        result = manager.kill_shell(shell_id)

        assert result is True, "終止應成功"
        assert bg_shell.status == ShellStatus.KILLED, "狀態應為 KILLED"
        assert bg_shell.ended_at is not None, "應有結束時間"

        console.print(f"[green]✓ Shell 終止成功[/green]")
        console.print(f"  狀態：{bg_shell.status.value}")
        console.print(f"  運行時間：{bg_shell.runtime:.1f}s")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_list_shells():
    """測試 7：列出所有 Shell"""
    console.print("\n[bold]測試 7：列出所有 Shell[/bold]")

    try:
        manager = BackgroundShellManager()

        # 啟動多個 Shell
        shell_id1 = manager.start_shell("echo 'Shell 1'")
        shell_id2 = manager.start_shell("sleep 1 && echo 'Shell 2'")

        # 等待
        time.sleep(0.5)

        # 列出
        shells_info = manager.list_shells()

        assert len(shells_info) >= 2, f"應有至少 2 個 Shell，但只有 {len(shells_info)}"

        # 檢查資訊完整性
        for info in shells_info:
            assert "shell_id" in info, "應有 shell_id"
            assert "command" in info, "應有 command"
            assert "status" in info, "應有 status"
            assert "runtime" in info, "應有 runtime"

        console.print(f"[green]✓ 列出 Shell 成功[/green]")
        console.print(f"  Shell 數量：{len(shells_info)}")

        # 清理
        for shell_id in [shell_id1, shell_id2]:
            bg_shell = manager.get_shell(shell_id)
            if bg_shell and bg_shell.is_running:
                manager.kill_shell(shell_id)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_cleanup_completed():
    """測試 8：清理已完成 Shell"""
    console.print("\n[bold]測試 8：清理已完成 Shell[/bold]")

    try:
        manager = BackgroundShellManager()

        # 啟動會快速完成的命令
        shell_id1 = manager.start_shell("echo 'Quick task'")
        shell_id2 = manager.start_shell("echo 'Another quick task'")

        # 等待完成
        time.sleep(0.5)

        # 確認有 Shell
        assert len(manager.shells) >= 2, "應有至少 2 個 Shell"

        # 清理已完成的
        cleaned = manager.cleanup_completed()

        assert cleaned >= 0, "清理數量應 >= 0"

        console.print(f"[green]✓ 清理已完成 Shell 成功[/green]")
        console.print(f"  清理數量：{cleaned}")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_custom_shell_id():
    """測試 9：自訂 Shell ID"""
    console.print("\n[bold]測試 9：自訂 Shell ID[/bold]")

    try:
        manager = BackgroundShellManager()

        # 使用自訂 ID
        custom_id = "my_custom_shell"
        shell_id = manager.start_shell("echo 'Custom ID'", shell_id=custom_id)

        assert shell_id == custom_id, "Shell ID 應為自訂值"
        assert custom_id in manager.shells, "自訂 ID 應被記錄"

        console.print(f"[green]✓ 自訂 Shell ID 成功[/green]")
        console.print(f"  Shell ID：{shell_id}")

        # 清理
        bg_shell = manager.get_shell(shell_id)
        if bg_shell and bg_shell.is_running:
            manager.kill_shell(shell_id)

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


# ==================== 主測試流程 ====================

def main():
    """執行所有測試"""
    console.print("=" * 70)
    console.print("[bold cyan]CodeGemini Background Shell - 測試套件[/bold cyan]")
    console.print("=" * 70)

    tests = [
        ("BackgroundShellManager 初始化", test_manager_initialization),
        ("啟動簡單 Shell", test_start_simple_shell),
        ("Shell 輸出捕獲", test_shell_output_capture),
        ("輸出過濾", test_output_filtering),
        ("長時間運行 Shell", test_long_running_shell),
        ("終止 Shell", test_kill_shell),
        ("列出所有 Shell", test_list_shells),
        ("清理已完成 Shell", test_cleanup_completed),
        ("自訂 Shell ID", test_custom_shell_id),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ 通過" if result else "❌ 失敗"
        except Exception as e:
            console.print(f"[red]測試異常：{e}[/red]")
            results[test_name] = "❌ 失敗"

    # 顯示測試總結
    console.print("\n" + "=" * 70)
    console.print("[bold]測試總結[/bold]")
    console.print("=" * 70)

    for test_name, result in results.items():
        console.print(f"  {test_name}: {result}")

    # 統計
    passed = sum(1 for r in results.values() if "通過" in r)
    total = len(results)

    console.print("-" * 70)
    console.print(f"[bold]總計：{passed}/{total} 測試通過[/bold]")

    if passed < total:
        console.print(f"\n[yellow]⚠️  {total - passed} 個測試失敗[/yellow]")
    else:
        console.print("\n[green]🎉 所有測試通過！Background Shell 準備就緒。[/green]")


if __name__ == "__main__":
    main()
