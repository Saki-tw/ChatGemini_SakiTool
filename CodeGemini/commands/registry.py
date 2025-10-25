#!/usr/bin/env python3
"""
CodeGemini Command Registry Module
命令註冊系統 - 管理自訂命令

此模組負責：
1. 註冊自訂命令
2. 執行命令
3. 命令列表管理
4. 從配置檔導入命令
"""
import os
import json
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class CommandType(Enum):
    """命令類型"""
    TEMPLATE = "template"      # 模板命令
    SCRIPT = "script"          # 腳本命令
    BUILTIN = "builtin"        # 內建命令


@dataclass
class CommandTemplate:
    """命令模板"""
    name: str                              # 命令名稱
    description: str                       # 命令描述
    template: str                          # 模板內容
    command_type: CommandType = CommandType.TEMPLATE
    parameters: List[str] = field(default_factory=list)  # 參數列表
    examples: List[str] = field(default_factory=list)    # 使用範例
    tags: List[str] = field(default_factory=list)        # 標籤
    author: str = "Unknown"                # 作者
    version: str = "1.0.0"                 # 版本


@dataclass
class CommandResult:
    """命令執行結果"""
    success: bool                          # 是否成功
    output: str                            # 輸出內容
    error_message: Optional[str] = None    # 錯誤訊息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元數據


class CommandRegistry:
    """命令註冊系統"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化命令註冊系統

        Args:
            config_dir: 配置目錄，預設為 ~/.codegemini/
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".codegemini")

        self.config_dir = config_dir
        self.commands_file = os.path.join(config_dir, "commands.yaml")

        # 確保配置目錄存在
        os.makedirs(config_dir, exist_ok=True)

        # 命令註冊表
        self.commands: Dict[str, CommandTemplate] = {}

        # 執行歷史
        self.history: List[Dict[str, Any]] = []

        # 載入命令
        self._load_commands()

    def register_command(
        self,
        name: str,
        template: CommandTemplate,
        save_to_config: bool = True
    ) -> bool:
        """
        註冊命令

        Args:
            name: 命令名稱
            template: 命令模板
            save_to_config: 是否儲存到配置檔

        Returns:
            bool: 是否成功註冊
        """
        # 驗證名稱
        if not name or not isinstance(name, str):
            console.print(f"[dim magenta]錯誤：命令名稱無效[/dim magenta]")
            return False

        # 檢查是否已存在
        if name in self.commands:
            console.print(f"[magenta]警告：命令 '{name}' 已存在，將被覆蓋[/yellow]")

        # 註冊命令
        self.commands[name] = template

        console.print(f"[bright_magenta]✓ 已註冊命令：{name}[/bright_magenta]")

        # 儲存到配置檔
        if save_to_config:
            self._save_commands()

        return True

    def unregister_command(self, name: str) -> bool:
        """
        取消註冊命令

        Args:
            name: 命令名稱

        Returns:
            bool: 是否成功取消註冊
        """
        if name not in self.commands:
            console.print(f"[dim magenta]錯誤：命令 '{name}' 不存在[/dim magenta]")
            return False

        # 檢查是否為內建命令
        if self.commands[name].command_type == CommandType.BUILTIN:
            console.print(f"[dim magenta]錯誤：無法取消註冊內建命令[/dim magenta]")
            return False

        del self.commands[name]
        console.print(f"[bright_magenta]✓ 已取消註冊命令：{name}[/bright_magenta]")

        # 儲存到配置檔
        self._save_commands()

        return True

    def execute_command(
        self,
        name: str,
        args: Optional[Dict[str, Any]] = None,
        executor: Optional[Any] = None
    ) -> CommandResult:
        """
        執行命令

        Args:
            name: 命令名稱
            args: 命令參數
            executor: 執行器（用於實際執行，如 Gemini API）

        Returns:
            CommandResult: 執行結果
        """
        if name not in self.commands:
            return CommandResult(
                success=False,
                output="",
                error_message=f"命令 '{name}' 不存在"
            )

        command = self.commands[name]
        args = args or {}

        console.print(f"\n[magenta]🚀 執行命令：{name}[/magenta]")

        # 驗證參數
        validation_result = self._validate_parameters(command, args)
        if not validation_result['valid']:
            return CommandResult(
                success=False,
                output="",
                error_message=f"參數驗證失敗：{validation_result['message']}"
            )

        try:
            # 使用模板引擎渲染
            from .templates import TemplateEngine

            template_engine = TemplateEngine()
            rendered = template_engine.render(
                template_engine.parse_template(command.template),
                args
            )

            console.print(f"[bright_magenta]✓ 命令已渲染[/bright_magenta]")

            # 記錄歷史
            self._add_to_history(name, args, rendered)

            # 如果有執行器，實際執行
            if executor:
                console.print(f"[magenta]使用執行器執行...[/magenta]")
                # 這裡可以整合 Gemini API 或其他執行器
                # 目前返回渲染結果
                pass

            return CommandResult(
                success=True,
                output=rendered,
                metadata={
                    'command_name': name,
                    'command_type': command.command_type.value,
                    'parameters': args
                }
            )

        except Exception as e:
            console.print(f"[dim magenta]錯誤：{e}[/dim magenta]")
            return CommandResult(
                success=False,
                output="",
                error_message=str(e)
            )

    def list_commands(
        self,
        filter_type: Optional[CommandType] = None,
        filter_tags: Optional[List[str]] = None
    ) -> List[CommandTemplate]:
        """
        列出命令

        Args:
            filter_type: 過濾命令類型
            filter_tags: 過濾標籤

        Returns:
            List[CommandTemplate]: 命令列表
        """
        commands = list(self.commands.values())

        # 過濾類型
        if filter_type:
            commands = [c for c in commands if c.command_type == filter_type]

        # 過濾標籤
        if filter_tags:
            commands = [
                c for c in commands
                if any(tag in c.tags for tag in filter_tags)
            ]

        return commands

    def get_command(self, name: str) -> Optional[CommandTemplate]:
        """
        取得命令

        Args:
            name: 命令名稱

        Returns:
            Optional[CommandTemplate]: 命令模板
        """
        return self.commands.get(name)

    def import_commands(self, config_file: str) -> int:
        """
        從配置檔導入命令

        Args:
            config_file: 配置檔路徑（YAML 或 JSON）

        Returns:
            int: 成功導入的命令數量
        """
        if not os.path.exists(config_file):
            console.print(f"[dim magenta]錯誤：配置檔不存在：{config_file}[/dim magenta]")
            return 0

        console.print(f"\n[magenta]📥 導入命令：{config_file}[/magenta]")

        try:
            # 讀取檔案
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    data = yaml.safe_load(f)
                elif config_file.endswith('.json'):
                    data = json.load(f)
                else:
                    console.print(f"[dim magenta]錯誤：不支援的檔案格式[/dim magenta]")
                    return 0

            # 解析命令
            count = 0
            for cmd_data in data.get('commands', []):
                try:
                    template = CommandTemplate(
                        name=cmd_data['name'],
                        description=cmd_data['description'],
                        template=cmd_data['template'],
                        command_type=CommandType(cmd_data.get('type', 'template')),
                        parameters=cmd_data.get('parameters', []),
                        examples=cmd_data.get('examples', []),
                        tags=cmd_data.get('tags', []),
                        author=cmd_data.get('author', 'Unknown'),
                        version=cmd_data.get('version', '1.0.0')
                    )

                    self.register_command(
                        cmd_data['name'],
                        template,
                        save_to_config=False  # 批次導入不立即儲存
                    )
                    count += 1

                except Exception as e:
                    console.print(f"[magenta]警告：導入命令 '{cmd_data.get('name', 'unknown')}' 失敗 - {e}[/yellow]")

            # 儲存所有導入的命令
            if count > 0:
                self._save_commands()

            console.print(f"[bright_magenta]✓ 成功導入 {count} 個命令[/bright_magenta]")
            return count

        except Exception as e:
            console.print(f"[dim magenta]錯誤：導入失敗 - {e}[/dim magenta]")
            return 0

    def export_commands(self, output_file: str) -> bool:
        """
        匯出命令到配置檔

        Args:
            output_file: 輸出檔案路徑

        Returns:
            bool: 是否成功匯出
        """
        console.print(f"\n[magenta]📤 匯出命令：{output_file}[/magenta]")

        try:
            # 準備資料
            commands_data = []
            for name, cmd in self.commands.items():
                # 跳過內建命令
                if cmd.command_type == CommandType.BUILTIN:
                    continue

                commands_data.append({
                    'name': name,
                    'description': cmd.description,
                    'template': cmd.template,
                    'type': cmd.command_type.value,
                    'parameters': cmd.parameters,
                    'examples': cmd.examples,
                    'tags': cmd.tags,
                    'author': cmd.author,
                    'version': cmd.version
                })

            data = {'commands': commands_data}

            # 寫入檔案
            with open(output_file, 'w', encoding='utf-8') as f:
                if output_file.endswith('.yaml') or output_file.endswith('.yml'):
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
                elif output_file.endswith('.json'):
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    console.print(f"[dim magenta]錯誤：不支援的檔案格式[/dim magenta]")
                    return False

            console.print(f"[bright_magenta]✓ 成功匯出 {len(commands_data)} 個命令[/bright_magenta]")
            return True

        except Exception as e:
            console.print(f"[dim magenta]錯誤：匯出失敗 - {e}[/dim magenta]")
            return False

    def show_command_details(self, name: str):
        """顯示命令詳情"""
        command = self.get_command(name)

        if not command:
            console.print(f"[dim magenta]命令 '{name}' 不存在[/dim magenta]")
            return

        # 建立詳情面板
        details = f"""[bold]名稱：[/bold]{command.name}
[bold]描述：[/bold]{command.description}
[bold]類型：[/bold]{command.command_type.value}
[bold]版本：[/bold]{command.version}
[bold]作者：[/bold]{command.author}
"""

        if command.parameters:
            details += f"\n[bold]參數：[/bold]{', '.join(command.parameters)}"

        if command.tags:
            details += f"\n[bold]標籤：[/bold]{', '.join(command.tags)}"

        console.print(Panel(details, title=f"命令詳情", border_style="bright_magenta"))

        # 顯示模板
        console.print(f"\n[bold magenta]模板內容：[/bold magenta]")
        console.print(command.template)

        # 顯示範例
        if command.examples:
            console.print(f"\n[bold magenta]使用範例：[/bold magenta]")
            for i, example in enumerate(command.examples, 1):
                console.print(f"  {i}. {example}")

    def show_commands_table(self, filter_type: Optional[CommandType] = None):
        """顯示命令表格"""
        commands = self.list_commands(filter_type=filter_type)

        if not commands:
            console.print("[magenta]沒有已註冊的命令[/yellow]")
            return

        table = Table(show_header=True, header_style="bold bright_magenta")
        table.add_column("名稱", style="yellow")
        table.add_column("描述", style="white")
        table.add_column("類型", style="green")
        table.add_column("參數", style="magenta")

        for cmd in commands:
            table.add_row(
                cmd.name,
                cmd.description[:50] + "..." if len(cmd.description) > 50 else cmd.description,
                cmd.command_type.value,
                str(len(cmd.parameters))
            )

        console.print(f"\n[bold magenta]已註冊命令（共 {len(commands)} 個）：[/bold magenta]")
        console.print(table)

    def _validate_parameters(
        self,
        command: CommandTemplate,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """驗證參數"""
        # 簡單驗證：檢查必要參數是否都有提供
        missing_params = [p for p in command.parameters if p not in args]

        if missing_params:
            return {
                'valid': False,
                'message': f"缺少必要參數：{', '.join(missing_params)}"
            }

        return {'valid': True, 'message': ''}

    def _add_to_history(self, name: str, args: Dict[str, Any], output: str):
        """添加到執行歷史"""
        import time

        self.history.append({
            'command': name,
            'args': args,
            'output': output,
            'timestamp': time.time()
        })

        # 限制歷史記錄數量
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def _load_commands(self):
        """從配置檔載入命令"""
        if os.path.exists(self.commands_file):
            try:
                self.import_commands(self.commands_file)
            except Exception as e:
                console.print(f"[magenta]警告：載入命令失敗 - {e}[/yellow]")

    def _save_commands(self):
        """儲存命令到配置檔"""
        try:
            self.export_commands(self.commands_file)
        except Exception as e:
            console.print(f"[magenta]警告：儲存命令失敗 - {e}[/yellow]")

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        取得執行歷史

        Args:
            limit: 數量限制

        Returns:
            List[Dict[str, Any]]: 歷史記錄
        """
        return self.history[-limit:]


def main():
    """測試用主程式"""
    console.print("[bold magenta]CodeGemini Command Registry 測試[/bold magenta]\n")

    # 建立註冊表
    registry = CommandRegistry()

    # 註冊測試命令
    test_command = CommandTemplate(
        name="test-example",
        description="測試命令範例",
        template="請執行以下任務：{task}\n使用語言：{language}",
        parameters=["task", "language"],
        examples=[
            "test-example task='寫一個函數' language='Python'",
            "test-example task='建立類別' language='Java'"
        ],
        tags=["test", "example"]
    )

    registry.register_command("test-example", test_command)

    # 顯示命令列表
    registry.show_commands_table()

    # 顯示命令詳情
    console.print()
    registry.show_command_details("test-example")

    # 執行命令
    result = registry.execute_command(
        "test-example",
        args={"task": "寫一個排序函數", "language": "Python"}
    )

    if result.success:
        console.print(f"\n[bold green]✅ 命令執行成功[/bold green]")
        console.print(f"\n[magenta]輸出：[/magenta]")
        console.print(result.output)
    else:
        console.print(f"\n[bold red]❌ 命令執行失敗[/bold red]")
        console.print(f"錯誤：{result.error_message}")


if __name__ == "__main__":
    main()
