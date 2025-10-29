#!/usr/bin/env python3
"""
CodeGemini MCP Registry Client
MCP Registry 客戶端 - 動態獲取 MCP Server 元數據

此模組負責：
1. 從多個 Registry 端點獲取 MCP Server 資訊
2. 快取 Server 元數據（24 小時 TTL）
3. 提供環境變數需求查詢
4. 優雅降級（網路失敗時使用快取）

Registry 端點：
- 主要: https://registry.modelcontextprotocol.io/v0/servers
- 備用: https://registry.mcpservers.org/api/v0/servers
- 降級: GitHub Raw JSON
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, List, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from rich.console import Console
from utils.i18n import safe_t

console = Console()


@dataclass
class ServerMetadata:
    """MCP Server 元數據"""
    name: str
    description: str
    env_vars: Dict[str, str]  # 環境變數名稱 -> 說明
    package: str  # npm package 名稱
    version: str = "latest"
    homepage: str = ""

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ServerMetadata':
        """從字典創建"""
        return cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            env_vars=data.get('env_vars', {}),
            package=data.get('package', ''),
            version=data.get('version', 'latest'),
            homepage=data.get('homepage', '')
        )


class MCPRegistry:
    """
    MCP Registry 客戶端

    提供多端點、快取、降級機制的 Registry 訪問
    """

    # Registry 端點（按優先順序）
    ENDPOINTS = [
        "https://registry.modelcontextprotocol.io/v0/servers",
        "https://registry.mcpservers.org/api/v0/servers",
        "https://raw.githubusercontent.com/modelcontextprotocol/registry/main/servers.json"
    ]

    # 快取設定
    CACHE_DIR = Path.home() / ".codegemini" / "mcp_cache"
    CACHE_FILE = CACHE_DIR / "registry.json"
    CACHE_TTL = 3600 * 24  # 24 小時

    # 請求超時（秒）
    REQUEST_TIMEOUT = 10

    @classmethod
    def _ensure_cache_dir(cls) -> None:
        """確保快取目錄存在"""
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _fetch_from_endpoint(cls, endpoint: str) -> Optional[Dict]:
        """
        從單一端點獲取數據

        Args:
            endpoint: Registry 端點 URL

        Returns:
            Optional[Dict]: Server 列表，失敗返回 None
        """
        try:
            req = urllib.request.Request(
                endpoint,
                headers={
                    'User-Agent': 'CodeGemini-MCP-Client/1.0',
                    'Accept': 'application/json'
                }
            )

            with urllib.request.urlopen(req, timeout=cls.REQUEST_TIMEOUT) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data

        except urllib.error.URLError as e:
            console.print(safe_t("registry.endpoint.unreachable", fallback="[dim]✗ 端點無法訪問：{endpoint} ({reason})[/dim]").format(endpoint=endpoint, reason=e.reason))
            return None
        except json.JSONDecodeError:
            console.print(safe_t("registry.endpoint.invalid_format", fallback="[dim]✗ 端點回應格式錯誤：{endpoint}[/dim]").format(endpoint=endpoint))
            return None
        except Exception as e:
            console.print(safe_t("registry.endpoint.error", fallback="[dim]✗ 端點錯誤：{endpoint} ({error})[/dim]").format(endpoint=endpoint, error=e))
            return None

    @classmethod
    def _fetch_from_network(cls) -> Optional[Dict]:
        """
        從網路獲取 Registry 數據（多端點策略）

        Returns:
            Optional[Dict]: Server 列表，失敗返回 None
        """
        console.print(safe_t("registry.fetch.starting", fallback="[dim]🌐 正在從 MCP Registry 獲取 Server 元數據...[/dim]"))

        for i, endpoint in enumerate(cls.ENDPOINTS):
            console.print(safe_t("registry.fetch.trying", fallback="[dim]  嘗試端點 {current}/{total}: {endpoint}[/dim]").format(current=i+1, total=len(cls.ENDPOINTS), endpoint=endpoint))

            data = cls._fetch_from_endpoint(endpoint)
            if data:
                console.print(safe_t("registry.fetch.success", fallback="[dim #DDA0DD]✓ 成功獲取數據（端點 {num}）[/dim #DDA0DD]").format(num=i+1))
                return data

        console.print(safe_t("registry.fetch.all_failed", fallback="[#DDA0DD]⚠️  所有 Registry 端點均無法訪問[/#DDA0DD]"))
        return None

    @classmethod
    def _load_cache(cls) -> Optional[Dict]:
        """
        從快取載入數據

        Returns:
            Optional[Dict]: 快取數據，不存在或過期返回 None
        """
        if not cls.CACHE_FILE.exists():
            return None

        try:
            with open(cls.CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 檢查快取時間
            cache_time = cache_data.get('timestamp', 0)
            age = time.time() - cache_time

            if age > cls.CACHE_TTL:
                console.print(safe_t("registry.cache.expired", fallback="[dim]⚠️  快取已過期（{hours:.1f} 小時）[/dim]").format(hours=age/3600))
                return None

            console.print(safe_t("registry.cache.using", fallback="[dim #DDA0DD]✓ 使用快取數據（{hours:.1f} 小時前）[/dim #DDA0DD]").format(hours=age/3600))
            return cache_data.get('servers')

        except Exception as e:
            console.print(safe_t("registry.cache.load_failed", fallback="[dim]✗ 快取載入失敗：{error}[/dim]").format(error=e))
            return None

    @classmethod
    def _save_cache(cls, servers: Dict) -> None:
        """
        儲存數據到快取

        Args:
            servers: Server 列表
        """
        try:
            cls._ensure_cache_dir()

            cache_data = {
                'timestamp': time.time(),
                'servers': servers
            }

            with open(cls.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            console.print(safe_t("registry.cache.updated", fallback="[dim]✓ 已更新快取[/dim]"))

        except Exception as e:
            console.print(safe_t("registry.cache.save_failed", fallback="[dim]⚠️  快取儲存失敗：{error}[/dim]").format(error=e))

    @classmethod
    def _get_servers_data(cls, force_refresh: bool = False) -> Optional[Dict]:
        """
        獲取 Server 數據（快取優先，網路降級）

        Args:
            force_refresh: 強制從網路更新

        Returns:
            Optional[Dict]: Server 列表
        """
        # 如果強制更新，直接從網路獲取
        if force_refresh:
            servers = cls._fetch_from_network()
            if servers:
                cls._save_cache(servers)
            return servers

        # 嘗試從快取載入
        servers = cls._load_cache()
        if servers:
            return servers

        # 快取失敗，從網路獲取
        servers = cls._fetch_from_network()
        if servers:
            cls._save_cache(servers)
            return servers

        # 網路也失敗，嘗試使用過期快取（優雅降級）
        console.print(safe_t("registry.fallback.trying", fallback="[#DDA0DD]⚠️  嘗試使用過期快取...[/#DDA0DD]"))
        if cls.CACHE_FILE.exists():
            try:
                with open(cls.CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    servers = cache_data.get('servers')
                    if servers:
                        console.print(safe_t("registry.fallback.success", fallback="[#DDA0DD]✓ 使用過期快取（降級模式）[/#DDA0DD]"))
                        return servers
            except:
                pass

        return None

    @classmethod
    def fetch_server_info(cls, server_name: str, force_refresh: bool = False) -> Optional[ServerMetadata]:
        """
        獲取特定 Server 的元數據

        Args:
            server_name: Server 名稱
            force_refresh: 強制從網路更新

        Returns:
            Optional[ServerMetadata]: Server 元數據，不存在返回 None
        """
        servers = cls._get_servers_data(force_refresh)

        if not servers:
            console.print(safe_t("registry.data.unavailable", fallback="[dim]⚠️  無法獲取 Registry 數據[/dim]"))
            return None

        # 查找 Server
        server_data = servers.get(server_name)
        if not server_data:
            # 嘗試模糊匹配（移除 -mcp 後綴等）
            normalized_name = server_name.replace('-mcp', '').replace('_', '-')
            for name, data in servers.items():
                if normalized_name in name or name in normalized_name:
                    server_data = data
                    break

        if not server_data:
            return None

        return ServerMetadata.from_dict(server_data)

    @classmethod
    def get_env_requirements(cls, server_name: str) -> Dict[str, str]:
        """
        獲取 Server 的環境變數需求

        Args:
            server_name: Server 名稱

        Returns:
            Dict[str, str]: 環境變數名稱 -> 說明的字典
        """
        metadata = cls.fetch_server_info(server_name)

        if not metadata:
            # 如果 Registry 無數據，使用內建對應表
            return cls._get_builtin_env_requirements(server_name)

        return metadata.env_vars

    @classmethod
    def _get_builtin_env_requirements(cls, server_name: str) -> Dict[str, str]:
        """
        內建環境變數對應表（降級方案）

        Args:
            server_name: Server 名稱

        Returns:
            Dict[str, str]: 環境變數需求
        """
        # 常見 MCP Server 環境變數對應表
        builtin_map = {
            'github': {
                'GITHUB_TOKEN': 'GitHub Personal Access Token (https://github.com/settings/tokens)'
            },
            'brave-search': {
                'BRAVE_API_KEY': 'Brave Search API Key (https://brave.com/search/api/)'
            },
            'slack': {
                'SLACK_BOT_TOKEN': 'Slack Bot Token',
                'SLACK_TEAM_ID': 'Slack Team ID'
            },
            'google-drive': {
                'GOOGLE_CLIENT_ID': 'Google OAuth Client ID',
                'GOOGLE_CLIENT_SECRET': 'Google OAuth Client Secret',
                'GOOGLE_REDIRECT_URI': 'OAuth Redirect URI'
            },
            'postgres': {
                'POSTGRES_CONNECTION_STRING': 'PostgreSQL Connection String'
            }
        }

        return builtin_map.get(server_name, {})

    @classmethod
    def check_env_vars(cls, server_name: str) -> Dict[str, Any]:
        """
        檢查 Server 環境變數是否已設定

        Args:
            server_name: Server 名稱

        Returns:
            Dict: 檢查結果 {
                'required': Dict[str, str],  # 需要的環境變數
                'missing': List[str],         # 缺失的環境變數
                'present': List[str],         # 已設定的環境變數
                'all_set': bool               # 是否全部已設定
            }
        """
        required = cls.get_env_requirements(server_name)

        missing = []
        present = []

        for env_var in required.keys():
            if os.environ.get(env_var):
                present.append(env_var)
            else:
                missing.append(env_var)

        return {
            'required': required,
            'missing': missing,
            'present': present,
            'all_set': len(missing) == 0
        }

    @classmethod
    def print_env_setup_hint(cls, server_name: str) -> None:
        """
        印出環境變數設定提示（友善、非阻塞）

        Args:
            server_name: Server 名稱
        """
        check_result = cls.check_env_vars(server_name)

        if check_result['all_set']:
            return  # 全部已設定，無需提示

        if not check_result['required']:
            return  # 無環境變數需求

        console.print(safe_t("registry.env.hint", fallback="\n[#DDA0DD]💡 提示：{name} Server 需要以下環境變數[/#DDA0DD]").format(name=server_name))

        for env_var, description in check_result['required'].items():
            is_set = env_var in check_result['present']
            status = "[green]✓[/green]" if is_set else "[red]✗[/red]"
            console.print(f"  {status} {env_var}")
            console.print(f"     {description}")

        if check_result['missing']:
            console.print(safe_t("registry.env.setup", fallback="\n[dim]設定方式：[/dim]"))
            console.print(f"[dim]  export {check_result['missing'][0]}=\"your_value_here\"[/dim]")
            console.print(safe_t("registry.env.permanent", fallback="[dim]或在 ~/.bashrc / ~/.zshrc 中永久設定[/dim]\n"))


# ==================== 測試與命令列工具 ====================

def main():
    """Registry 客戶端測試工具"""
    import sys

    console.print("\n[bold #DDA0DD]CodeGemini MCP Registry Client[/bold #DDA0DD]\n")

    if len(sys.argv) < 2:
        console.print(safe_t("registry.usage.header", fallback="用法："))
        console.print(safe_t("registry.usage.info", fallback="  python registry.py info <server_name>    - 查詢 Server 資訊"))
        console.print(safe_t("registry.usage.env", fallback="  python registry.py env <server_name>     - 檢查環境變數"))
        console.print(safe_t("registry.usage.refresh", fallback="  python registry.py refresh               - 強制更新快取"))
        return

    command = sys.argv[1]

    if command == "info":
        if len(sys.argv) < 3:
            console.print(safe_t("registry.cli.specify_server", fallback="[red]請指定 Server 名稱[/red]"))
            return

        server_name = sys.argv[2]
        metadata = MCPRegistry.fetch_server_info(server_name)

        if metadata:
            console.print(f"\n[#DDA0DD]📦 {metadata.name}[/#DDA0DD]")
            console.print(safe_t("registry.info.description", fallback="描述：{desc}").format(desc=metadata.description))
            console.print(safe_t("registry.info.package", fallback="套件：{pkg}").format(pkg=metadata.package))
            console.print(safe_t("registry.info.version", fallback="版本：{ver}").format(ver=metadata.version))
            if metadata.homepage:
                console.print(safe_t("registry.info.homepage", fallback="首頁：{url}").format(url=metadata.homepage))

            if metadata.env_vars:
                console.print(safe_t("registry.info.env_required", fallback="\n環境變數需求："))
                for var, desc in metadata.env_vars.items():
                    console.print(f"  • {var}: {desc}")
        else:
            console.print(safe_t("registry.server.not_found", fallback="[red]✗ 找不到 Server：{name}[/red]").format(name=server_name))

    elif command == "env":
        if len(sys.argv) < 3:
            console.print(safe_t("registry.cli.specify_server", fallback="[red]請指定 Server 名稱[/red]"))
            return

        server_name = sys.argv[2]
        MCPRegistry.print_env_setup_hint(server_name)

    elif command == "refresh":
        console.print(safe_t("registry.refresh.starting", fallback="[#DDA0DD]🔄 強制更新快取...[/#DDA0DD]"))
        servers = MCPRegistry._get_servers_data(force_refresh=True)
        if servers:
            console.print(safe_t("registry.refresh.success", fallback="[green]✓ 已更新，共 {count} 個 Server[/green]").format(count=len(servers)))
        else:
            console.print(safe_t("registry.refresh.failed", fallback="[red]✗ 更新失敗[/red]"))

    else:
        console.print(safe_t("registry.cli.unknown_command", fallback="[red]未知指令：{cmd}[/red]").format(cmd=command))


if __name__ == "__main__":
    main()
