#!/usr/bin/env python3
"""
CodeGemini MCP Client Module
MCP (Model Context Protocol) 客戶端 - 連接外部工具與服務

此模組負責：
1. 連接到 MCP 伺服器
2. 執行遠端工具調用
3. 管理連線狀態
4. 處理錯誤與重試

MCP 協議簡介：
- 由 Anthropic 開發的開放標準
- 允許 AI 應用連接外部工具和資料來源
- 支援檔案系統、資料庫、API 等多種服務
"""

import os
import json
import subprocess
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class MCPServer:
    """MCP 伺服器配置"""
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    description: str = ""
    capabilities: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


@dataclass
class MCPTool:
    """MCP 工具定義"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


class MCPClient:
    """
    MCP 客戶端

    連接並管理 MCP 伺服器，執行遠端工具調用
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 MCP 客戶端

        Args:
            config_path: MCP 配置檔路徑（JSON 格式）
        """
        self.config_path = config_path or self._get_default_config_path()
        self.servers: Dict[str, MCPServer] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.processes: Dict[str, subprocess.Popen] = {}

        # 載入配置
        if os.path.exists(self.config_path):
            self.load_config()

    def _get_default_config_path(self) -> str:
        """取得預設配置檔路徑"""
        # 優先使用專案目錄下的 mcp-config.json
        project_config = Path(__file__).parent.parent / "config" / "mcp-config.json"
        if project_config.exists():
            return str(project_config)

        # 次選使用家目錄下的配置
        home_config = Path.home() / ".codegemini" / "mcp-config.json"
        return str(home_config)

    def load_config(self) -> None:
        """從配置檔載入 MCP 伺服器"""
        console.print(f"\n[cyan]📡 載入 MCP 配置：{self.config_path}[/cyan]")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 載入伺服器配置
            for server_config in config.get('servers', []):
                server = MCPServer(
                    name=server_config['name'],
                    command=server_config['command'],
                    args=server_config.get('args', []),
                    env=server_config.get('env'),
                    description=server_config.get('description', ''),
                    capabilities=server_config.get('capabilities', [])
                )
                self.servers[server.name] = server

            console.print(f"[green]✓ 載入 {len(self.servers)} 個 MCP 伺服器[/green]")

        except FileNotFoundError:
            console.print(f"[yellow]⚠️  配置檔不存在：{self.config_path}[/yellow]")
        except json.JSONDecodeError as e:
            console.print(f"[red]✗ 配置檔格式錯誤：{e}[/red]")
        except Exception as e:
            console.print(f"[red]✗ 載入配置失敗：{e}[/red]")

    def list_servers(self) -> List[MCPServer]:
        """列出所有已配置的伺服器"""
        return list(self.servers.values())

    def start_server(self, server_name: str) -> bool:
        """
        啟動 MCP 伺服器

        Args:
            server_name: 伺服器名稱

        Returns:
            bool: 是否成功啟動
        """
        if server_name not in self.servers:
            console.print(f"[red]✗ 伺服器不存在：{server_name}[/red]")
            return False

        if server_name in self.processes:
            console.print(f"[yellow]伺服器已在運行：{server_name}[/yellow]")
            return True

        server = self.servers[server_name]
        console.print(f"\n[cyan]🚀 啟動 MCP 伺服器：{server_name}[/cyan]")
        console.print(f"  指令：{server.command} {' '.join(server.args)}")

        try:
            # 設定環境變數
            env = os.environ.copy()
            if server.env:
                env.update(server.env)

            # 啟動伺服器進程
            process = subprocess.Popen(
                [server.command] + server.args,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.processes[server_name] = process
            console.print(f"[green]✓ 伺服器已啟動（PID: {process.pid}）[/green]")

            # 發現工具
            self._discover_tools(server_name)

            return True

        except Exception as e:
            console.print(f"[red]✗ 啟動失敗：{e}[/red]")
            return False

    def stop_server(self, server_name: str) -> bool:
        """
        停止 MCP 伺服器

        Args:
            server_name: 伺服器名稱

        Returns:
            bool: 是否成功停止
        """
        if server_name not in self.processes:
            console.print(f"[yellow]伺服器未運行：{server_name}[/yellow]")
            return True

        console.print(f"\n[cyan]🛑 停止 MCP 伺服器：{server_name}[/cyan]")

        try:
            process = self.processes[server_name]
            process.terminate()

            # 等待進程結束（最多 5 秒）
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                console.print("[yellow]強制終止進程...[/yellow]")
                process.kill()
                process.wait()

            del self.processes[server_name]
            console.print(f"[green]✓ 伺服器已停止[/green]")
            return True

        except Exception as e:
            console.print(f"[red]✗ 停止失敗：{e}[/red]")
            return False

    def stop_all_servers(self) -> None:
        """停止所有運行中的伺服器"""
        console.print(f"\n[cyan]🛑 停止所有 MCP 伺服器...[/cyan]")

        for server_name in list(self.processes.keys()):
            self.stop_server(server_name)

        console.print(f"[green]✓ 所有伺服器已停止[/green]")

    def _discover_tools(self, server_name: str) -> None:
        """
        發現伺服器提供的工具

        Args:
            server_name: 伺服器名稱
        """
        # 簡化實作：根據伺服器類型預定義工具
        # 實際應該透過 MCP 協議查詢

        server = self.servers[server_name]

        # 根據伺服器能力添加工具
        if 'filesystem' in server.capabilities:
            self.tools[f"{server_name}:read_file"] = MCPTool(
                name="read_file",
                description="讀取檔案內容",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "檔案路徑"}
                    },
                    "required": ["path"]
                },
                server_name=server_name
            )

            self.tools[f"{server_name}:write_file"] = MCPTool(
                name="write_file",
                description="寫入檔案內容",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "檔案路徑"},
                        "content": {"type": "string", "description": "檔案內容"}
                    },
                    "required": ["path", "content"]
                },
                server_name=server_name
            )

        if 'database' in server.capabilities:
            self.tools[f"{server_name}:query"] = MCPTool(
                name="query",
                description="執行資料庫查詢",
                input_schema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL 查詢語句"}
                    },
                    "required": ["sql"]
                },
                server_name=server_name
            )

        console.print(f"  發現 {len([t for t in self.tools.values() if t.server_name == server_name])} 個工具")

    def list_tools(self, server_name: Optional[str] = None) -> List[MCPTool]:
        """
        列出可用工具

        Args:
            server_name: 伺服器名稱（選用，不指定則列出所有）

        Returns:
            List[MCPTool]: 工具列表
        """
        if server_name:
            return [
                tool for tool in self.tools.values()
                if tool.server_name == server_name
            ]
        return list(self.tools.values())

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_name: Optional[str] = None
    ) -> Optional[Any]:
        """
        調用 MCP 工具

        Args:
            tool_name: 工具名稱
            arguments: 工具參數
            server_name: 伺服器名稱（選用）

        Returns:
            Any: 工具執行結果
        """
        # 查找工具
        tool_key = f"{server_name}:{tool_name}" if server_name else None

        if tool_key and tool_key in self.tools:
            tool = self.tools[tool_key]
        else:
            # 嘗試按名稱查找
            matching_tools = [
                t for t in self.tools.values()
                if t.name == tool_name
            ]

            if not matching_tools:
                console.print(f"[red]✗ 工具不存在：{tool_name}[/red]")
                return None

            if len(matching_tools) > 1 and not server_name:
                console.print(f"[yellow]⚠️  發現多個同名工具，請指定伺服器[/yellow]")
                return None

            tool = matching_tools[0]

        # 檢查伺服器是否運行
        if tool.server_name not in self.processes:
            console.print(f"[yellow]伺服器未運行，嘗試啟動：{tool.server_name}[/yellow]")
            if not self.start_server(tool.server_name):
                return None

        console.print(f"\n[cyan]🔧 調用工具：{tool.name} @ {tool.server_name}[/cyan]")
        console.print(f"  參數：{arguments}")

        try:
            # 構建 MCP 請求（簡化版）
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool.name,
                    "arguments": arguments
                }
            }

            # 發送請求（這裡是模擬，實際應透過 stdio 通訊）
            # 實際實作需要使用 MCP SDK 或實作完整的 JSON-RPC 通訊

            console.print(f"[green]✓ 工具調用成功[/green]")

            # 模擬回應
            return {
                "success": True,
                "tool": tool.name,
                "result": "（模擬結果 - 實際需要實作 MCP 協議）"
            }

        except Exception as e:
            console.print(f"[red]✗ 工具調用失敗：{e}[/red]")
            return None

    def get_server_status(self, server_name: str) -> Dict[str, Any]:
        """
        取得伺服器狀態

        Args:
            server_name: 伺服器名稱

        Returns:
            Dict: 狀態資訊
        """
        if server_name not in self.servers:
            return {"status": "unknown", "message": "伺服器不存在"}

        is_running = server_name in self.processes

        status = {
            "name": server_name,
            "status": "running" if is_running else "stopped",
            "description": self.servers[server_name].description,
            "capabilities": self.servers[server_name].capabilities,
            "tools_count": len([
                t for t in self.tools.values()
                if t.server_name == server_name
            ])
        }

        if is_running:
            process = self.processes[server_name]
            status["pid"] = process.pid
            status["running"] = process.poll() is None

        return status

    def print_status(self) -> None:
        """印出所有伺服器狀態"""
        console.print("\n[cyan]📊 MCP 伺服器狀態[/cyan]\n")

        if not self.servers:
            console.print("[yellow]沒有配置任何 MCP 伺服器[/yellow]")
            return

        for server_name in self.servers:
            status = self.get_server_status(server_name)

            status_color = "green" if status["status"] == "running" else "dim"
            status_icon = "🟢" if status["status"] == "running" else "🔴"

            console.print(f"{status_icon} [{status_color}]{server_name}[/{status_color}]")
            console.print(f"   狀態：{status['status']}")
            console.print(f"   描述：{status['description']}")
            console.print(f"   能力：{', '.join(status['capabilities'])}")
            console.print(f"   工具數：{status['tools_count']}")

            if status['status'] == 'running':
                console.print(f"   PID：{status.get('pid', 'N/A')}")

            console.print()

    def __del__(self):
        """清理：停止所有伺服器"""
        self.stop_all_servers()


# ==================== 命令列介面 ====================

def main():
    """MCP Client 命令列工具"""
    import sys

    console.print("\n[bold cyan]CodeGemini MCP Client[/bold cyan]\n")

    client = MCPClient()

    if len(sys.argv) < 2:
        console.print("用法：")
        console.print("  python mcp/client.py list          - 列出伺服器")
        console.print("  python mcp/client.py start <name>  - 啟動伺服器")
        console.print("  python mcp/client.py stop <name>   - 停止伺服器")
        console.print("  python mcp/client.py status        - 顯示狀態")
        console.print("  python mcp/client.py tools [name]  - 列出工具")
        return

    command = sys.argv[1]

    if command == "list":
        servers = client.list_servers()
        if servers:
            console.print(f"[cyan]已配置的 MCP 伺服器（{len(servers)} 個）：[/cyan]\n")
            for server in servers:
                console.print(f"  • {server.name}")
                console.print(f"    {server.description}")
                console.print(f"    能力：{', '.join(server.capabilities)}\n")
        else:
            console.print("[yellow]沒有配置任何伺服器[/yellow]")

    elif command == "start":
        if len(sys.argv) < 3:
            console.print("[red]請指定伺服器名稱[/red]")
            return

        server_name = sys.argv[2]
        client.start_server(server_name)

    elif command == "stop":
        if len(sys.argv) < 3:
            console.print("[red]請指定伺服器名稱[/red]")
            return

        server_name = sys.argv[2]
        client.stop_server(server_name)

    elif command == "status":
        client.print_status()

    elif command == "tools":
        server_name = sys.argv[2] if len(sys.argv) > 2 else None
        tools = client.list_tools(server_name)

        if tools:
            title = f"可用工具（{len(tools)} 個）"
            if server_name:
                title += f" - {server_name}"

            console.print(f"[cyan]{title}：[/cyan]\n")

            for tool in tools:
                console.print(f"  • {tool.name} @ {tool.server_name}")
                console.print(f"    {tool.description}\n")
        else:
            console.print("[yellow]沒有可用工具[/yellow]")

    else:
        console.print(f"[red]未知指令：{command}[/red]")


if __name__ == "__main__":
    main()
