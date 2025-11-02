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
import sys
import json
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 確保可以 import utils
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.i18n import safe_t

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
            console.print(f"[dim #B565D8]{safe_t('registry.error.invalid_name', '錯誤：命令名稱無效')}[/dim #B565D8]")
            return False

        # 檢查是否已存在
        if name in self.commands:
            console.print(f"[#B565D8]{safe_t('registry.warning.command_exists', '警告：命令已存在，將被覆蓋', name=name)}[/#B565D8]")

        # 註冊命令
        self.commands[name] = template

        console.print(f"[#B565D8]✓ {safe_t('registry.success.registered', '已註冊命令', name=name)}[/#B565D8]")

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
            console.print(f"[dim #B565D8]{safe_t('registry.error.command_not_found', '錯誤：命令不存在', name=name)}[/dim #B565D8]")
            return False

        # 檢查是否為內建命令
        if self.commands[name].command_type == CommandType.BUILTIN:
            console.print(f"[dim #B565D8]{safe_t('registry.error.cannot_unregister_builtin', '錯誤：無法取消註冊內建命令')}[/dim #B565D8]")
            return False

        del self.commands[name]
        console.print(f"[#B565D8]✓ {safe_t('registry.success.unregistered', '已取消註冊命令', name=name)}[/#B565D8]")

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
                error_message=safe_t('registry.error.command_not_found', '命令不存在', name=name)
            )

        command = self.commands[name]
        args = args or {}

        console.print(f"\n[#B565D8]🚀 {safe_t('registry.execute.running', '執行命令', name=name)}[/#B565D8]")

        # 驗證參數
        validation_result = self._validate_parameters(command, args)
        if not validation_result['valid']:
            return CommandResult(
                success=False,
                output="",
                error_message=safe_t('registry.error.validation_failed', '參數驗證失敗', message=validation_result['message'])
            )

        try:
            # 使用模板引擎渲染
            from .templates import TemplateEngine

            template_engine = TemplateEngine()
            rendered = template_engine.render(
                template_engine.parse_template(command.template),
                args
            )

            console.print(f"[#B565D8]✓ {safe_t('registry.execute.rendered', '命令已渲染')}[/#B565D8]")

            # 記錄歷史
            self._add_to_history(name, args, rendered)

            # 如果有執行器，實際執行
            if executor:
                console.print(f"[#B565D8]{safe_t('registry.execute.using_executor', '使用執行器執行...')}[/#B565D8]")
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
            console.print(f"[dim #B565D8]{safe_t('registry.error.generic', '錯誤', error=str(e))}[/dim #B565D8]")
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
            console.print(f"[dim #B565D8]{safe_t('registry.error.file_not_found', '錯誤：配置檔不存在', file=config_file)}[/dim #B565D8]")
            return 0

        console.print(f"\n[#B565D8]📥 {safe_t('registry.import.importing', '導入命令', file=config_file)}[/#B565D8]")

        try:
            # 讀取檔案
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    data = yaml.safe_load(f)
                elif config_file.endswith('.json'):
                    data = json.load(f)
                else:
                    console.print(f"[dim #B565D8]{safe_t('registry.error.unsupported_format', '錯誤：不支援的檔案格式')}[/dim #B565D8]")
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
                    console.print(f"[#B565D8]{safe_t('registry.warning.import_failed', '警告：導入命令失敗', name=cmd_data.get('name', 'unknown'), error=str(e))}[/#B565D8]")

            # 儲存所有導入的命令
            if count > 0:
                self._save_commands()

            console.print(f"[#B565D8]✓ {safe_t('registry.import.success', '成功導入命令', count=count)}[/#B565D8]")
            return count

        except Exception as e:
            console.print(f"[dim #B565D8]{safe_t('registry.error.import_failed', '錯誤：導入失敗', error=str(e))}[/dim #B565D8]")
            return 0

    def export_commands(self, output_file: str) -> bool:
        """
        匯出命令到配置檔

        Args:
            output_file: 輸出檔案路徑

        Returns:
            bool: 是否成功匯出
        """
        console.print(f"\n[#B565D8]📤 {safe_t('registry.export.exporting', '匯出命令', file=output_file)}[/#B565D8]")

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
                    console.print(f"[dim #B565D8]{safe_t('registry.error.unsupported_format', '錯誤：不支援的檔案格式')}[/dim #B565D8]")
                    return False

            console.print(f"[#B565D8]✓ {safe_t('registry.export.success', '成功匯出命令', count=len(commands_data))}[/#B565D8]")
            return True

        except Exception as e:
            console.print(f"[dim #B565D8]{safe_t('registry.error.export_failed', '錯誤：匯出失敗', error=str(e))}[/dim #B565D8]")
            return False

    def show_command_details(self, name: str):
        """顯示命令詳情"""
        command = self.get_command(name)

        if not command:
            console.print(f"[dim #B565D8]{safe_t('registry.error.command_not_found', '命令不存在', name=name)}[/dim #B565D8]")
            return

        # 建立詳情面板
        details = f"""[bold]{safe_t('registry.details.name', '名稱')}：[/bold]{command.name}
[bold]{safe_t('registry.details.description', '描述')}：[/bold]{command.description}
[bold]{safe_t('registry.details.type', '類型')}：[/bold]{command.command_type.value}
[bold]{safe_t('registry.details.version', '版本')}：[/bold]{command.version}
[bold]{safe_t('registry.details.author', '作者')}：[/bold]{command.author}
"""

        if command.parameters:
            details += f"\n[bold]{safe_t('registry.details.parameters', '參數')}：[/bold]{', '.join(command.parameters)}"

        if command.tags:
            details += f"\n[bold]{safe_t('registry.details.tags', '標籤')}：[/bold]{', '.join(command.tags)}"

        console.print(Panel(details, title=safe_t('registry.details.title', '命令詳情'), border_style="#B565D8"))

        # 顯示模板
        console.print(f"\n[bold #B565D8]{safe_t('registry.details.template', '模板內容')}：[/bold #B565D8]")
        console.print(command.template)

        # 顯示範例
        if command.examples:
            console.print(f"\n[bold #B565D8]{safe_t('registry.details.examples', '使用範例')}：[/bold #B565D8]")
            for i, example in enumerate(command.examples, 1):
                console.print(f"  {i}. {example}")

    def show_commands_table(self, filter_type: Optional[CommandType] = None):
        """顯示命令表格"""
        commands = self.list_commands(filter_type=filter_type)

        if not commands:
            console.print(f"[#B565D8]{safe_t('registry.table.no_commands', '沒有已註冊的命令')}[/#B565D8]")
            return

        table = Table(show_header=True, header_style="bold #B565D8")
        table.add_column(safe_t('registry.table.name', '名稱'), style="#B565D8")
        table.add_column(safe_t('registry.table.description', '描述'), style="white")
        table.add_column(safe_t('registry.table.type', '類型'), style="green")
        table.add_column(safe_t('registry.table.parameters', '參數'), style="#B565D8")

        for cmd in commands:
            table.add_row(
                cmd.name,
                cmd.description[:50] + "..." if len(cmd.description) > 50 else cmd.description,
                cmd.command_type.value,
                str(len(cmd.parameters))
            )

        console.print(f"\n[bold #B565D8]{safe_t('registry.table.header', '已註冊命令', count=len(commands))}：[/bold #B565D8]")
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
                'message': safe_t('registry.validation.missing_params', '缺少必要參數', params=', '.join(missing_params))
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
                console.print(f"[#B565D8]{safe_t('registry.warning.load_failed', '警告：載入命令失敗', error=str(e))}[/#B565D8]")

    def _save_commands(self):
        """儲存命令到配置檔"""
        try:
            self.export_commands(self.commands_file)
        except Exception as e:
            console.print(f"[#B565D8]{safe_t('registry.warning.save_failed', '警告：儲存命令失敗', error=str(e))}[/#B565D8]")

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
    console.print(f"[bold #B565D8]{safe_t('registry.test.header', 'CodeGemini Command Registry 測試')}[/bold #B565D8]\n")

    # 建立註冊表
    registry = CommandRegistry()

    # 註冊測試命令
    test_command = CommandTemplate(
        name="test-example",
        description=safe_t('registry.test.example_desc', '測試命令範例'),
        template=safe_t('registry.test.example_template', '請執行以下任務：{task}\n使用語言：{language}'),
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
        console.print(f"\n[bold green]✅ {safe_t('registry.test.success', '命令執行成功')}[/bold green]")
        console.print(f"\n[#B565D8]{safe_t('registry.test.output', '輸出')}：[/#B565D8]")
        console.print(result.output)
    else:
        console.print(f"\n[bold red]❌ {safe_t('registry.test.failed', '命令執行失敗')}[/bold red]")
        console.print(f"{safe_t('registry.test.error', '錯誤')}：{result.error_message}")


if __name__ == "__main__":
    main()
