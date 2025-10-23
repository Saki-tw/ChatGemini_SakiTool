#!/usr/bin/env python3
"""
CodeGemini Custom Commands 系統測試
測試 Command Registry、Template Engine、Built-in Commands
"""
import os
import sys
import tempfile
from pathlib import Path
from rich.console import Console

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from commands.registry import CommandRegistry, CommandTemplate, CommandType
from commands.templates import TemplateEngine, TemplateLibrary
from commands.builtin import BuiltinCommands

console = Console()


def test_template_engine():
    """測試 TemplateEngine"""
    console.print("\n[bold magenta]測試 1：Template Engine[/bold magenta]")

    try:
        engine = TemplateEngine()
        console.print("[bright_magenta]✓ TemplateEngine 初始化成功[/green]")

        # 測試簡單變數
        template1 = engine.parse_template("Hello, {name}!")
        result1 = engine.render(template1, {"name": "CodeGemini"})
        assert result1 == "Hello, CodeGemini!", "簡單變數插值失敗"
        console.print("[bright_magenta]✓ 簡單變數插值測試通過[/green]")

        # 測試預設值
        template2 = engine.parse_template("{lang|default:\"Python\"}")
        result2 = engine.render(template2, {})
        assert result2 == "Python", "預設值處理失敗"
        console.print("[bright_magenta]✓ 預設值測試通過[/green]")

        # 測試條件
        template3 = engine.parse_template("{% if premium %}VIP{% else %}Normal{% endif %}")
        result3a = engine.render(template3, {"premium": True})
        result3b = engine.render(template3, {"premium": False})
        assert result3a == "VIP" and result3b == "Normal", "條件邏輯失敗"
        console.print("[bright_magenta]✓ 條件邏輯測試通過[/green]")

        # 測試迴圈
        template4 = engine.parse_template("{% for item in items %}{item} {% endfor %}")
        result4 = engine.render(template4, {"items": ["A", "B", "C"]})
        assert "A" in result4 and "B" in result4 and "C" in result4, "迴圈處理失敗"
        console.print("[bright_magenta]✓ 迴圈處理測試通過[/green]")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_template_library():
    """測試 TemplateLibrary"""
    console.print("\n[bold magenta]測試 2：Template Library[/bold magenta]")

    try:
        library = TemplateLibrary()
        console.print("[bright_magenta]✓ TemplateLibrary 初始化成功[/green]")

        # 檢查內建模板
        templates = library.list_templates()
        assert len(templates) > 0, "沒有內建模板"
        console.print(f"[bright_magenta]✓ 找到 {len(templates)} 個內建模板[/green]")

        # 測試取得模板
        python_func = library.get_template('python_function')
        assert python_func is not None, "python_function 模板不存在"
        console.print("[bright_magenta]✓ 內建模板可正常取得[/green]")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_command_registry():
    """測試 CommandRegistry"""
    console.print("\n[bold magenta]測試 3：Command Registry[/bold magenta]")

    try:
        # 使用臨時目錄
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = CommandRegistry(config_dir=temp_dir)
            console.print("[bright_magenta]✓ CommandRegistry 初始化成功[/green]")

            # 註冊測試命令
            test_cmd = CommandTemplate(
                name="test-cmd",
                description="測試命令",
                template="Task: {task}",
                parameters=["task"]
            )

            success = registry.register_command("test-cmd", test_cmd, save_to_config=False)
            assert success, "命令註冊失敗"
            console.print("[bright_magenta]✓ 命令註冊成功[/green]")

            # 執行命令
            result = registry.execute_command("test-cmd", {"task": "測試任務"})
            assert result.success, "命令執行失敗"
            assert "測試任務" in result.output, "命令輸出不正確"
            console.print("[bright_magenta]✓ 命令執行成功[/green]")

            # 列出命令
            commands = registry.list_commands()
            assert len(commands) == 1, "命令列表不正確"
            console.print("[bright_magenta]✓ 命令列表正確[/green]")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_builtin_commands():
    """測試 BuiltinCommands"""
    console.print("\n[bold magenta]測試 4：Built-in Commands[/bold magenta]")

    try:
        # 取得所有內建命令
        commands = BuiltinCommands.get_all_commands()
        assert len(commands) > 0, "沒有內建命令"
        console.print(f"[bright_magenta]✓ 找到 {len(commands)} 個內建命令[/green]")

        # 驗證命令結構
        for cmd in commands:
            assert cmd.name, "命令名稱為空"
            assert cmd.description, "命令描述為空"
            assert cmd.template, "命令模板為空"
            assert cmd.command_type == CommandType.BUILTIN, "命令類型不正確"

        console.print("[bright_magenta]✓ 所有內建命令結構正確[/green]")

        # 測試註冊到 Registry
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = CommandRegistry(config_dir=temp_dir)
            count = BuiltinCommands.register_all(registry)
            assert count == len(commands), "註冊數量不正確"
            console.print(f"[bright_magenta]✓ 成功註冊 {count} 個內建命令[/green]")

            # 測試執行內建命令
            test_result = registry.execute_command(
                "test",
                {
                    "target": "example_function",
                    "code": "def example(): pass"
                }
            )
            assert test_result.success, "內建命令執行失敗"
            console.print("[bright_magenta]✓ 內建命令執行成功[/green]")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_import_export():
    """測試命令導入/匯出"""
    console.print("\n[bold magenta]測試 5：命令導入/匯出[/bold magenta]")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = CommandRegistry(config_dir=temp_dir)

            # 註冊測試命令
            test_cmd = CommandTemplate(
                name="export-test",
                description="匯出測試",
                template="Test: {value}",
                parameters=["value"]
            )
            registry.register_command("export-test", test_cmd, save_to_config=False)

            # 匯出命令
            export_file = os.path.join(temp_dir, "test_export.yaml")
            success = registry.export_commands(export_file)
            assert success, "匯出失敗"
            assert os.path.exists(export_file), "匯出檔案不存在"
            console.print("[bright_magenta]✓ 命令匯出成功[/green]")

            # 建立新 Registry 並導入
            registry2 = CommandRegistry(config_dir=temp_dir)
            count = registry2.import_commands(export_file)
            assert count == 1, "導入數量不正確"
            console.print("[bright_magenta]✓ 命令導入成功[/green]")

            # 驗證導入的命令
            imported_cmd = registry2.get_command("export-test")
            assert imported_cmd is not None, "導入的命令不存在"
            assert imported_cmd.description == "匯出測試", "導入的命令內容不正確"
            console.print("[bright_magenta]✓ 導入內容正確[/green]")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_default_commands_config():
    """測試預設命令配置檔"""
    console.print("\n[bold magenta]測試 6：預設命令配置檔[/bold magenta]")

    try:
        # 找到配置檔
        config_file = Path(__file__).parent.parent / "config" / "default_commands.yaml"

        if not config_file.exists():
            console.print(f"[magenta]⚠️  配置檔不存在：{config_file}[/yellow]")
            console.print("[bright_magenta]✓ 跳過此測試[/green]")
            return True

        # 導入配置檔
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = CommandRegistry(config_dir=temp_dir)
            count = registry.import_commands(str(config_file))

            assert count > 0, "沒有從配置檔導入任何命令"
            console.print(f"[bright_magenta]✓ 從配置檔導入 {count} 個命令[/green]")

            # 驗證命令可執行
            commands = registry.list_commands()
            for cmd in commands[:3]:  # 測試前 3 個
                # 構建測試參數
                test_args = {param: f"test_{param}" for param in cmd.parameters}
                result = registry.execute_command(cmd.name, test_args)
                assert result.success, f"命令 {cmd.name} 執行失敗"

            console.print("[bright_magenta]✓ 配置檔中的命令可正常執行[/green]")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """執行所有測試"""
    console.print("\n" + "=" * 70)
    console.print("[bold magenta]CodeGemini Custom Commands - 測試套件[/bold magenta]")
    console.print("=" * 70)

    tests = [
        ("Template Engine", test_template_engine),
        ("Template Library", test_template_library),
        ("Command Registry", test_command_registry),
        ("Built-in Commands", test_builtin_commands),
        ("Import/Export", test_import_export),
        ("Default Commands Config", test_default_commands_config),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    # 測試總結
    console.print("\n" + "=" * 70)
    console.print("[bold magenta]測試總結[/bold magenta]")
    console.print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[bright_magenta]✅ 通過[/green]" if result else "[dim magenta]❌ 失敗[/red]"
        console.print(f"  {name}: {status}")

    console.print("\n" + "-" * 70)
    console.print(f"[bold]總計：{passed}/{total} 測試通過[/bold]")

    if passed == total:
        console.print("\n[bold green]🎉 所有測試通過！Custom Commands 系統準備就緒。[/bold green]")
        return 0
    else:
        console.print(f"\n[bold yellow]⚠️  {total - passed} 個測試失敗[/bold yellow]")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
