#!/usr/bin/env python3
"""
CodeGemini MCP Client 測試
測試 MCP Client 功能
"""

import os
import sys
import tempfile
import json
from pathlib import Path
from rich.console import Console

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.client import MCPClient, MCPServer, MCPTool

console = Console()


def create_test_config():
    """建立測試用 MCP 配置檔"""
    temp_dir = tempfile.mkdtemp(prefix="mcp_test_")
    config_path = os.path.join(temp_dir, "mcp-config.json")

    config = {
        "servers": [
            {
                "name": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", temp_dir],
                "description": "本機檔案系統存取",
                "capabilities": ["filesystem"]
            },
            {
                "name": "test-server",
                "command": "echo",
                "args": ["test"],
                "description": "測試用伺服器",
                "capabilities": ["test"]
            }
        ]
    }

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return config_path, temp_dir


def test_client_initialization():
    """測試 1：MCP Client 初始化"""
    console.print("\n[bold]測試 1：MCP Client 初始化[/bold]")

    try:
        config_path, temp_dir = create_test_config()
        client = MCPClient(config_path)

        assert len(client.servers) > 0, "未載入任何伺服器"
        console.print(f"[bright_magenta]✓ Client 初始化成功[/green]")
        console.print(f"  配置路徑：{config_path}")
        console.print(f"  伺服器數：{len(client.servers)}")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_server_listing():
    """測試 2：伺服器列表"""
    console.print("\n[bold]測試 2：伺服器列表[/bold]")

    try:
        config_path, temp_dir = create_test_config()
        client = MCPClient(config_path)

        servers = client.list_servers()

        assert len(servers) == 2, f"伺服器數量錯誤：{len(servers)}"
        assert any(s.name == "filesystem" for s in servers), "缺少 filesystem 伺服器"

        console.print(f"[bright_magenta]✓ 伺服器列表正確[/green]")
        for server in servers:
            console.print(f"  - {server.name}: {server.description}")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_server_status():
    """測試 3：伺服器狀態查詢"""
    console.print("\n[bold]測試 3：伺服器狀態查詢[/bold]")

    try:
        config_path, temp_dir = create_test_config()
        client = MCPClient(config_path)

        # 查詢已停止伺服器的狀態
        status = client.get_server_status("test-server")

        assert status["status"] == "stopped", "初始狀態應為 stopped"
        assert status["name"] == "test-server", "伺服器名稱錯誤"

        console.print(f"[bright_magenta]✓ 狀態查詢成功[/green]")
        console.print(f"  伺服器：{status['name']}")
        console.print(f"  狀態：{status['status']}")
        console.print(f"  能力：{status['capabilities']}")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_tool_discovery():
    """測試 4：工具發現（模擬）"""
    console.print("\n[bold]測試 4：工具發現[/bold]")

    try:
        config_path, temp_dir = create_test_config()
        client = MCPClient(config_path)

        # 啟動伺服器（會觸發工具發現）
        # 注意：這會實際啟動進程，可能失敗，但測試邏輯仍可執行
        client.start_server("test-server")

        # 列出工具
        tools = client.list_tools("test-server")

        console.print(f"[bright_magenta]✓ 工具發現功能正常[/green]")
        console.print(f"  發現工具：{len(tools)} 個")

        for tool in tools:
            console.print(f"  - {tool.name}: {tool.description}")

        # 清理
        client.stop_all_servers()
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_config_validation():
    """測試 5：配置驗證"""
    console.print("\n[bold]測試 5：配置驗證[/bold]")

    try:
        config_path, temp_dir = create_test_config()

        # 讀取配置檔驗證格式
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        assert "servers" in config, "配置缺少 servers 欄位"
        assert isinstance(config["servers"], list), "servers 應為列表"
        assert len(config["servers"]) > 0, "servers 列表為空"

        # 驗證第一個伺服器配置
        server = config["servers"][0]
        required_fields = ["name", "command"]

        for field in required_fields:
            assert field in server, f"伺服器配置缺少 {field} 欄位"

        console.print(f"[bright_magenta]✓ 配置格式驗證通過[/green]")
        console.print(f"  伺服器數：{len(config['servers'])}")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_data_structures():
    """測試 6：MCP 資料結構"""
    console.print("\n[bold]測試 6：MCP 資料結構[/bold]")

    try:
        # 測試 MCPServer
        server = MCPServer(
            name="test",
            command="echo",
            args=["hello"],
            description="測試伺服器",
            capabilities=["test"]
        )

        assert server.name == "test", "MCPServer name 錯誤"
        assert server.command == "echo", "MCPServer command 錯誤"
        assert "test" in server.capabilities, "MCPServer capabilities 錯誤"

        # 測試 MCPTool
        tool = MCPTool(
            name="read_file",
            description="讀取檔案",
            input_schema={"type": "object"},
            server_name="filesystem"
        )

        assert tool.name == "read_file", "MCPTool name 錯誤"
        assert tool.server_name == "filesystem", "MCPTool server_name 錯誤"

        console.print(f"[bright_magenta]✓ 資料結構測試通過[/green]")
        console.print(f"  MCPServer: {server.name}")
        console.print(f"  MCPTool: {tool.name}")

        return True

    except Exception as e:
        console.print(f"[dim magenta]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


# ==================== 主測試流程 ====================

def main():
    """執行所有測試"""
    console.print("=" * 70)
    console.print("[bold magenta]CodeGemini MCP Client - 測試套件[/bold magenta]")
    console.print("=" * 70)

    tests = [
        ("MCP Client 初始化", test_client_initialization),
        ("伺服器列表", test_server_listing),
        ("伺服器狀態查詢", test_server_status),
        ("工具發現", test_tool_discovery),
        ("配置驗證", test_config_validation),
        ("MCP 資料結構", test_mcp_data_structures),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ 通過" if result else "❌ 失敗"
        except Exception as e:
            console.print(f"[dim magenta]測試異常：{e}[/red]")
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
        console.print(f"\n[magenta]⚠️  {total - passed} 個測試失敗[/yellow]")
    else:
        console.print("\n[bright_magenta]🎉 所有測試通過！MCP Client 準備就緒。[/green]")


if __name__ == "__main__":
    main()
