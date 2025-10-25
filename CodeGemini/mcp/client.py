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
import shutil
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# 匯入智慧偵測器和 Registry 客戶端
try:
    from .detector import MCPServerDetector
    from .registry import MCPRegistry
except ImportError:
    from detector import MCPServerDetector
    from registry import MCPRegistry

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

    def __init__(self, config_path: Optional[str] = None, enable_auto_detect: bool = True):
        """
        初始化 MCP 客戶端

        Args:
            config_path: MCP 配置檔路徑（JSON 格式）
            enable_auto_detect: 是否啟用智慧偵測器（預設 True）
        """
        self.config_path = config_path or self._get_default_config_path()
        self.servers: Dict[str, MCPServer] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.processes: Dict[str, subprocess.Popen] = {}

        # 初始化智慧偵測器
        self.enable_auto_detect = enable_auto_detect
        if enable_auto_detect:
            self.detector = MCPServerDetector()
            console.print("[dim magenta]✓ MCP 智慧偵測器已啟用[/dim magenta]")

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

    def _should_auto_enable_google_drive(self) -> Tuple[bool, str]:
        """
        偵測是否應自動啟用 Google Drive MCP Server

        檢查項目：
        1. Google Cloud SDK (gcloud) 是否安裝
        2. Google 認證檔案是否存在
        3. GOOGLE_APPLICATION_CREDENTIALS 環境變數
        4. OAuth 認證檔案

        Returns:
            Tuple[bool, str]: (是否啟用, 偵測原因)
        """
        # 檢查 gcloud CLI
        if shutil.which('gcloud'):
            # 檢查是否已登入
            gcloud_config = Path.home() / ".config" / "gcloud"
            if gcloud_config.exists():
                return (True, "偵測到 Google Cloud SDK 且已設定")

        # 檢查 Google 應用程式認證
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            cred_path = Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
            if cred_path.exists():
                return (True, "偵測到 GOOGLE_APPLICATION_CREDENTIALS")

        # 檢查常見的 Google 認證位置
        common_cred_paths = [
            Path.home() / ".config" / "gcloud" / "application_default_credentials.json",
            Path.home() / ".credentials" / "drive-python-quickstart.json",
            Path.home() / ".google" / "credentials.json"
        ]

        for cred_path in common_cred_paths:
            if cred_path.exists():
                return (True, f"偵測到 Google 認證檔案：{cred_path.name}")

        # 檢查 Google Drive 相關環境變數
        if os.environ.get('GDRIVE_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID'):
            return (True, "偵測到 Google Drive 環境變數")

        return (False, "未偵測到 Google 認證")

    def _should_auto_enable_slack(self) -> Tuple[bool, str]:
        """
        偵測是否應自動啟用 Slack MCP Server

        檢查項目：
        1. SLACK_BOT_TOKEN 環境變數
        2. SLACK_TEAM_ID 環境變數
        3. ~/.slack/ 配置目錄

        Returns:
            Tuple[bool, str]: (是否啟用, 偵測原因)
        """
        # 檢查環境變數
        if os.environ.get('SLACK_BOT_TOKEN'):
            return (True, "偵測到 SLACK_BOT_TOKEN 環境變數")

        if os.environ.get('SLACK_API_TOKEN'):
            return (True, "偵測到 SLACK_API_TOKEN 環境變數")

        # 檢查 Slack 配置目錄
        slack_config = Path.home() / ".slack"
        if slack_config.exists() and any(slack_config.iterdir()):
            return (True, "偵測到 ~/.slack/ 配置")

        return (False, "未偵測到 Slack 設定")

    def _should_auto_enable_postgres(self) -> Tuple[bool, str]:
        """
        偵測是否應自動啟用 PostgreSQL MCP Server

        檢查項目：
        1. psql 指令是否可用
        2. PostgreSQL 連線字串環境變數
        3. ~/.pgpass 檔案
        4. 本地 PostgreSQL 是否運行

        Returns:
            Tuple[bool, str]: (是否啟用, 偵測原因)
        """
        # 檢查 psql 是否安裝
        if not shutil.which('psql'):
            return (False, "未安裝 PostgreSQL 客戶端")

        # 檢查連線字串環境變數
        pg_env_vars = [
            'DATABASE_URL',
            'POSTGRES_CONNECTION_STRING',
            'POSTGRESQL_URL',
            'PG_CONNECTION_STRING'
        ]

        for env_var in pg_env_vars:
            if os.environ.get(env_var):
                return (True, f"偵測到 {env_var} 環境變數")

        # 檢查 .pgpass 檔案
        pgpass = Path.home() / ".pgpass"
        if pgpass.exists():
            return (True, "偵測到 ~/.pgpass 認證檔案")

        # 檢查本地 PostgreSQL 是否運行（簡單測試）
        try:
            result = subprocess.run(
                ['psql', '-U', 'postgres', '-c', 'SELECT 1', '-t'],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return (True, "偵測到本地 PostgreSQL 運行中")
        except:
            pass

        # psql 已安裝但無明確配置，保守不啟用
        return (False, "已安裝 psql 但未偵測到資料庫設定")

    def _should_auto_enable_puppeteer(self) -> Tuple[bool, str]:
        """
        偵測是否應自動啟用 Puppeteer MCP Server

        檢查項目：
        1. Chrome/Chromium 是否安裝
        2. 專案中是否有網頁相關檔案

        Returns:
            Tuple[bool, str]: (是否啟用, 偵測原因)
        """
        # 檢查 Chrome/Chromium
        browsers = ['google-chrome', 'chromium', 'chromium-browser', 'chrome']
        for browser in browsers:
            if shutil.which(browser):
                return (True, f"偵測到瀏覽器：{browser}")

        # 檢查 macOS Chrome
        mac_chrome = Path("/Applications/Google Chrome.app")
        if mac_chrome.exists():
            return (True, "偵測到 Google Chrome (macOS)")

        # Puppeteer 比較通用，預設不啟用
        return (False, "未偵測到 Chrome/Chromium")

    def _auto_enable_disabled_servers(self, config: Dict) -> List[str]:
        """
        智慧偵測並自動啟用 disabled servers

        Args:
            config: MCP 配置字典

        Returns:
            List[str]: 自動啟用的 server 名稱列表
        """
        auto_enabled = []

        # 偵測規則對應表
        detection_rules = {
            'google-drive': self._should_auto_enable_google_drive,
            'slack': self._should_auto_enable_slack,
            'postgres': self._should_auto_enable_postgres,
            'puppeteer': self._should_auto_enable_puppeteer
        }

        # 處理 mcpServers 字典格式（官方格式）
        mcp_servers = config.get('mcpServers', {})

        for server_name, server_config in mcp_servers.items():
            # 只處理 disabled 的 server
            if not server_config.get('disabled', False):
                continue

            # 檢查是否有偵測規則
            if server_name not in detection_rules:
                continue

            # 執行偵測
            should_enable, reason = detection_rules[server_name]()

            if should_enable:
                # 自動啟用
                server_config['disabled'] = False
                auto_enabled.append(server_name)

                console.print(f"[dim magenta]🔍 智慧啟用：{server_name}[/dim magenta]")
                console.print(f"[dim]   原因：{reason}[/dim]")

        return auto_enabled

    def load_config(self) -> None:
        """從配置檔載入 MCP 伺服器"""
        console.print(f"\n[magenta]📡 載入 MCP 配置：{self.config_path}[/magenta]")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 智慧偵測並自動啟用 disabled servers
            auto_enabled = self._auto_enable_disabled_servers(config)
            if auto_enabled:
                console.print(f"[dim magenta]✨ 自動啟用 {len(auto_enabled)} 個 Server[/dim magenta]\n")

            # 載入伺服器配置（處理 mcpServers 字典格式）
            enabled_servers = []
            mcp_servers = config.get('mcpServers', {})

            for server_name, server_config in mcp_servers.items():
                # 跳過仍為 disabled 的伺服器
                if server_config.get('disabled', False):
                    continue

                server = MCPServer(
                    name=server_name,
                    command=server_config['command'],
                    args=server_config.get('args', []),
                    env=server_config.get('env'),
                    description=server_config.get('description', ''),
                    capabilities=server_config.get('capabilities', [])
                )
                self.servers[server.name] = server
                enabled_servers.append(server.name)

            console.print(f"[bright_magenta]✓ 載入 {len(self.servers)} 個 MCP 伺服器[/bright_magenta]")

            # 動態檢查環境變數需求（非阻塞）
            self._check_env_requirements(enabled_servers)

        except FileNotFoundError:
            console.print(f"[magenta]⚠️  配置檔不存在：{self.config_path}[/yellow]")
        except json.JSONDecodeError as e:
            console.print(f"[dim magenta]✗ 配置檔格式錯誤：{e}[/red]")
        except Exception as e:
            console.print(f"[dim magenta]✗ 載入配置失敗：{e}[/red]")

    def _check_env_requirements(self, server_names: List[str]) -> None:
        """
        檢查伺服器環境變數需求（非阻塞）

        Args:
            server_names: 要檢查的伺服器名稱列表
        """
        servers_with_missing_vars = []

        for server_name in server_names:
            check_result = MCPRegistry.check_env_vars(server_name)

            # 只提示有缺失環境變數的伺服器
            if check_result['missing']:
                servers_with_missing_vars.append({
                    'name': server_name,
                    'missing': check_result['missing'],
                    'required': check_result['required']
                })

        # 如果有伺服器缺少環境變數，顯示友善提示
        if servers_with_missing_vars:
            console.print(f"\n[yellow]💡 環境變數提示[/yellow]")
            console.print(f"[dim]以下 MCP Server 需要環境變數才能完整運作：[/dim]\n")

            for server_info in servers_with_missing_vars:
                console.print(f"[yellow]• {server_info['name']}[/yellow]")
                for var in server_info['missing']:
                    desc = server_info['required'].get(var, '無說明')
                    console.print(f"  [dim]✗ {var}[/dim]")
                    console.print(f"    [dim]{desc}[/dim]")

            console.print(f"\n[dim]💡 設定方式：[/dim]")
            console.print(f"[dim]  export VARIABLE_NAME=\"your_value\"[/dim]")
            console.print(f"[dim]或在 ~/.bashrc / ~/.zshrc 中永久設定[/dim]")
            console.print(f"[dim]未設定環境變數的 Server 仍可載入，但部分功能可能受限[/dim]\n")

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
            console.print(f"[dim magenta]✗ 伺服器不存在：{server_name}[/red]")
            return False

        if server_name in self.processes:
            console.print(f"[magenta]伺服器已在運行：{server_name}[/yellow]")
            return True

        server = self.servers[server_name]
        console.print(f"\n[magenta]🚀 啟動 MCP 伺服器：{server_name}[/magenta]")
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
            console.print(f"[bright_magenta]✓ 伺服器已啟動（PID: {process.pid}）[/bright_magenta]")

            # 發現工具
            self._discover_tools(server_name)

            return True

        except Exception as e:
            console.print(f"[dim magenta]✗ 啟動失敗：{e}[/red]")
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
            console.print(f"[magenta]伺服器未運行：{server_name}[/yellow]")
            return True

        console.print(f"\n[magenta]🛑 停止 MCP 伺服器：{server_name}[/magenta]")

        try:
            process = self.processes[server_name]
            process.terminate()

            # 等待進程結束（最多 5 秒）
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                console.print("[magenta]強制終止進程...[/yellow]")
                process.kill()
                process.wait()

            del self.processes[server_name]
            console.print(f"[bright_magenta]✓ 伺服器已停止[/bright_magenta]")
            return True

        except Exception as e:
            console.print(f"[dim magenta]✗ 停止失敗：{e}[/red]")
            return False

    def stop_all_servers(self) -> None:
        """停止所有運行中的伺服器"""
        console.print(f"\n[magenta]🛑 停止所有 MCP 伺服器...[/magenta]")

        for server_name in list(self.processes.keys()):
            self.stop_server(server_name)

        console.print(f"[bright_magenta]✓ 所有伺服器已停止[/bright_magenta]")

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
                console.print(f"[dim magenta]✗ 工具不存在：{tool_name}[/red]")
                return None

            if len(matching_tools) > 1 and not server_name:
                console.print(f"[magenta]⚠️  發現多個同名工具，請指定伺服器[/yellow]")
                return None

            tool = matching_tools[0]

        # 檢查伺服器是否運行
        if tool.server_name not in self.processes:
            console.print(f"[magenta]伺服器未運行，嘗試啟動：{tool.server_name}[/yellow]")
            if not self.start_server(tool.server_name):
                return None

        console.print(f"\n[magenta]🔧 調用工具：{tool.name} @ {tool.server_name}[/magenta]")
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

            console.print(f"[bright_magenta]✓ 工具調用成功[/bright_magenta]")

            # 模擬回應
            return {
                "success": True,
                "tool": tool.name,
                "result": "（模擬結果 - 實際需要實作 MCP 協議）"
            }

        except Exception as e:
            console.print(f"[dim magenta]✗ 工具調用失敗：{e}[/red]")
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
        console.print("\n[magenta]📊 MCP 伺服器狀態[/magenta]\n")

        if not self.servers:
            console.print("[magenta]沒有配置任何 MCP 伺服器[/yellow]")
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

    def auto_start_by_intent(self, user_input: str, threshold: float = 0.65) -> List[str]:
        """
        根據使用者輸入自動偵測並啟動需要的 MCP Server

        Args:
            user_input: 使用者輸入的文字
            threshold: 信心度閾值（0-1），預設 0.65

        Returns:
            List[str]: 已啟動的 Server 名稱列表
        """
        if not self.enable_auto_detect:
            console.print("[yellow]⚠️  智慧偵測器未啟用[/yellow]")
            return []

        # 使用偵測器分析輸入
        detections = self.detector.detect(user_input, threshold=threshold)

        if not detections:
            return []

        console.print(f"\n[magenta]🔍 智慧偵測結果：[/magenta]")
        for detection in detections:
            console.print(f"  • {detection['server_name']} "
                        f"(信心度: {detection['confidence']:.2f}) - {detection['reason']}")

        started_servers = []

        # 自動啟動偵測到的 Server
        for detection in detections:
            server_name = detection['server_name']

            # 檢查 Server 是否存在於配置中
            if server_name not in self.servers:
                console.print(f"[yellow]⚠️  Server 未配置：{server_name}[/yellow]")
                continue

            # 檢查是否已經在運行
            if server_name in self.processes:
                console.print(f"[dim]Server 已運行：{server_name}[/dim]")
                started_servers.append(server_name)
                continue

            # 啟動 Server
            console.print(f"[magenta]🚀 自動啟動 Server：{server_name}[/magenta]")
            if self.start_server(server_name):
                started_servers.append(server_name)

        if started_servers:
            console.print(f"\n[green]✓ 已啟動 {len(started_servers)} 個 Server[/green]")

        return started_servers

    def __del__(self):
        """清理：停止所有伺服器"""
        self.stop_all_servers()


# ==================== 命令列介面 ====================

def main():
    """MCP Client 命令列工具"""
    import sys

    console.print("\n[bold magenta]CodeGemini MCP Client[/bold magenta]\n")

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
            console.print(f"[magenta]已配置的 MCP 伺服器（{len(servers)} 個）：[/magenta]\n")
            for server in servers:
                console.print(f"  • {server.name}")
                console.print(f"    {server.description}")
                console.print(f"    能力：{', '.join(server.capabilities)}\n")
        else:
            console.print("[magenta]沒有配置任何伺服器[/yellow]")

    elif command == "start":
        if len(sys.argv) < 3:
            console.print("[dim magenta]請指定伺服器名稱[/red]")
            return

        server_name = sys.argv[2]
        client.start_server(server_name)

    elif command == "stop":
        if len(sys.argv) < 3:
            console.print("[dim magenta]請指定伺服器名稱[/red]")
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

            console.print(f"[magenta]{title}：[/magenta]\n")

            for tool in tools:
                console.print(f"  • {tool.name} @ {tool.server_name}")
                console.print(f"    {tool.description}\n")
        else:
            console.print("[magenta]沒有可用工具[/yellow]")

    else:
        console.print(f"[dim magenta]未知指令：{command}[/red]")


if __name__ == "__main__":
    main()
