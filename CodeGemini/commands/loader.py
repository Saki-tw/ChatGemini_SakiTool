#!/usr/bin/env python3
"""
CodeGemini Markdown Command Loader Module
Markdown 命令載入器 - 從 Markdown 檔案載入自訂命令

此模組負責：
1. 掃描 .chatgemini/commands/ 目錄
2. 解析 Markdown 格式的命令定義
3. 驗證命令格式與參數
4. 自動註冊到 CommandRegistry
5. Hot Reload 機制（檔案變更自動重新載入）
6. 衝突檢測與警告

Markdown 格式範例：
---
name: my-command
description: 命令描述
type: template
parameters:
  - param1
  - param2
tags:
  - tag1
  - tag2
author: User Name
version: 1.0.0
examples:
  - "my-command param1='value1' param2='value2'"
---

這裡是命令模板內容
可以使用 {param1} 和 {param2}
{% if condition %}條件內容{% endif %}
"""
import os
import sys
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .registry import CommandTemplate, CommandType, CommandRegistry

# 確保可以 import utils
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.i18n import safe_t

console = Console()

# Lazy import for yaml (only needed when actually loading Markdown commands)
def _import_yaml():
    """Lazy import yaml module"""
    try:
        import yaml
        return yaml
    except ImportError:
        console.print(safe_t("commands.error.missing_yaml", fallback="[dim #B565D8]錯誤：缺少 PyYAML 依賴[/dim #B565D8]"))
        console.print(safe_t("commands.error.install_yaml", fallback="[#B565D8]請執行：pip install pyyaml[/#B565D8]"))
        raise ImportError("PyYAML is required for Markdown command loading")


@dataclass
class CommandFile:
    """命令檔案資訊"""
    file_path: str                          # 檔案路徑
    file_name: str                          # 檔案名稱
    modified_time: float                    # 修改時間
    command_name: str                       # 命令名稱
    is_valid: bool = True                   # 是否有效
    error_message: Optional[str] = None     # 錯誤訊息


class MarkdownCommandLoader:
    """Markdown 命令載入器"""

    # Frontmatter 分隔符號
    FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n(.*)', re.DOTALL)

    def __init__(
        self,
        commands_dir: Optional[str] = None,
        registry: Optional[CommandRegistry] = None
    ):
        """
        初始化 Markdown 命令載入器

        Args:
            commands_dir: 命令目錄，預設為 ~/.chatgemini/commands/
            registry: 命令註冊表，若未提供則創建新的
        """
        if commands_dir is None:
            commands_dir = os.path.join(
                os.path.expanduser("~"),
                ".chatgemini",
                "commands"
            )

        self.commands_dir = commands_dir
        self.registry = registry or CommandRegistry()

        # 確保命令目錄存在
        os.makedirs(commands_dir, exist_ok=True)

        # 已載入的命令檔案
        self.loaded_files: Dict[str, CommandFile] = {}

        # 命令名稱到檔案的映射
        self.command_file_map: Dict[str, str] = {}

    def scan_and_load(
        self,
        force_reload: bool = False,
        silent: bool = False
    ) -> int:
        """
        掃描並載入所有 Markdown 命令檔案

        Args:
            force_reload: 強制重新載入所有檔案
            silent: 靜默模式，不顯示訊息

        Returns:
            int: 成功載入的命令數量
        """
        if not silent:
            console.print(safe_t("commands.scan.starting", fallback="\n[#B565D8]🔍 掃描命令目錄：{dir}[/#B565D8]").format(dir=self.commands_dir))

        # 查找所有 .md 檔案
        md_files = list(Path(self.commands_dir).glob("*.md"))

        if not md_files:
            if not silent:
                console.print(safe_t("commands.scan.no_files", fallback="[#B565D8]未找到任何 Markdown 命令檔案[/#B565D8]"))
            return 0

        loaded_count = 0
        skipped_count = 0
        error_count = 0

        for md_file in md_files:
            file_path = str(md_file)
            file_name = md_file.name

            # 檢查是否需要重新載入
            should_load = force_reload or self._should_reload_file(file_path)

            if not should_load:
                skipped_count += 1
                continue

            # 載入命令
            try:
                command = self.load_command_from_file(file_path)

                if command:
                    # 檢測衝突
                    conflict = self._detect_conflict(command.name, file_path)

                    if conflict:
                        error_count += 1
                        continue

                    # 註冊命令
                    success = self.registry.register_command(
                        command.name,
                        command,
                        save_to_config=False  # Markdown 命令不儲存到 YAML 配置
                    )

                    if success:
                        # 記錄已載入的檔案
                        self.loaded_files[file_path] = CommandFile(
                            file_path=file_path,
                            file_name=file_name,
                            modified_time=os.path.getmtime(file_path),
                            command_name=command.name,
                            is_valid=True
                        )

                        # 更新映射
                        self.command_file_map[command.name] = file_path

                        loaded_count += 1

                        if not silent:
                            console.print(
                                f"[#B565D8]  ✓ 載入：{file_name} → /{command.name}[/#B565D8]"
                            )
                    else:
                        error_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                if not silent:
                    console.print(safe_t("commands.load.error", fallback="[dim #B565D8]  ✗ 錯誤：{file} - {error}[/dim #B565D8]").format(file=file_name, error=e))

                # 記錄錯誤
                self.loaded_files[file_path] = CommandFile(
                    file_path=file_path,
                    file_name=file_name,
                    modified_time=os.path.getmtime(file_path),
                    command_name="",
                    is_valid=False,
                    error_message=str(e)
                )

        if not silent:
            console.print(
                f"\n[#B565D8]✓ 載入完成：{loaded_count} 個成功"
                f"{f'、{skipped_count} 個跳過' if skipped_count > 0 else ''}"
                f"{f'、{error_count} 個錯誤' if error_count > 0 else ''}[/#B565D8]"
            )

        return loaded_count

    def load_command_from_file(self, file_path: str) -> Optional[CommandTemplate]:
        """
        從 Markdown 檔案載入命令

        Args:
            file_path: 檔案路徑

        Returns:
            Optional[CommandTemplate]: 命令模板，若失敗則返回 None
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"檔案不存在：{file_path}")

        # 讀取檔案
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 Frontmatter
        metadata, template_content = self._parse_markdown(content)

        if not metadata:
            raise ValueError("無法解析 Frontmatter，請確認格式正確")

        # 驗證必要欄位
        if 'name' not in metadata:
            raise ValueError("缺少必要欄位：name")

        if 'description' not in metadata:
            raise ValueError("缺少必要欄位：description")

        if not template_content or not template_content.strip():
            raise ValueError("命令模板內容為空")

        # 建立 CommandTemplate
        try:
            command = CommandTemplate(
                name=metadata['name'],
                description=metadata['description'],
                template=template_content.strip(),
                command_type=CommandType(metadata.get('type', 'template')),
                parameters=metadata.get('parameters', []),
                examples=metadata.get('examples', []),
                tags=metadata.get('tags', []),
                author=metadata.get('author', 'Unknown'),
                version=metadata.get('version', '1.0.0')
            )

            return command

        except Exception as e:
            raise ValueError(f"建立命令模板失敗：{e}")

    def _parse_markdown(self, content: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        解析 Markdown 內容（Frontmatter + 模板）

        Args:
            content: Markdown 內容

        Returns:
            Tuple[Optional[Dict[str, Any]], str]: (metadata, template_content)
        """
        match = self.FRONTMATTER_PATTERN.match(content)

        if not match:
            return None, content

        frontmatter_str = match.group(1)
        template_content = match.group(2)

        try:
            yaml = _import_yaml()
            metadata = yaml.safe_load(frontmatter_str)
            return metadata, template_content

        except Exception as e:
            if "YAMLError" in str(type(e)):
                raise ValueError(f"YAML 解析錯誤：{e}")
            raise

    def _should_reload_file(self, file_path: str) -> bool:
        """
        檢查檔案是否需要重新載入

        Args:
            file_path: 檔案路徑

        Returns:
            bool: 是否需要重新載入
        """
        # 如果是新檔案，需要載入
        if file_path not in self.loaded_files:
            return True

        # 檢查檔案修改時間
        current_mtime = os.path.getmtime(file_path)
        loaded_file = self.loaded_files[file_path]

        # 如果檔案已被修改，需要重新載入
        if current_mtime > loaded_file.modified_time:
            return True

        return False

    def _detect_conflict(self, command_name: str, file_path: str) -> bool:
        """
        檢測命令名稱衝突

        Args:
            command_name: 命令名稱
            file_path: 檔案路徑

        Returns:
            bool: 是否有衝突
        """
        # 檢查是否與內建命令衝突
        existing_command = self.registry.get_command(command_name)

        if existing_command:
            if existing_command.command_type == CommandType.BUILTIN:
                console.print(
                    f"[dim #B565D8]✗ 衝突：'{command_name}' 與內建命令衝突，已跳過[/dim #B565D8]"
                )
                return True

        # 檢查是否與其他 Markdown 命令衝突
        if command_name in self.command_file_map:
            existing_file = self.command_file_map[command_name]

            if existing_file != file_path:
                console.print(
                    f"[#B565D8]⚠ 警告：'{command_name}' 重複定義於多個檔案：[/#B565D8]"
                )
                console.print(f"  - {existing_file}")
                console.print(f"  - {file_path}")
                console.print(safe_t("commands.conflict.use_first", fallback="  將使用第一個定義"))
                return True

        return False

    def watch_and_reload(
        self,
        check_interval: int = 5,
        callback: Optional[callable] = None
    ):
        """
        監視命令目錄並自動重新載入（Hot Reload）

        Args:
            check_interval: 檢查間隔（秒）
            callback: 重新載入後的回調函數

        Note:
            這是一個簡單的輪詢實作。對於生產環境，
            建議使用 watchdog 庫進行檔案監視。
        """
        console.print(
            f"\n[#B565D8]👀 開始監視命令目錄（每 {check_interval} 秒檢查一次）[/#B565D8]"
        )
        console.print(safe_t("commands.watch.hint", fallback="[dim]按 Ctrl+C 停止監視[/dim]\n"))

        try:
            while True:
                time.sleep(check_interval)

                # 掃描並載入變更的檔案
                loaded_count = self.scan_and_load(silent=True)

                if loaded_count > 0:
                    console.print(
                        f"[#B565D8]🔄 重新載入：{loaded_count} 個命令已更新[/#B565D8]"
                    )

                    if callback:
                        callback(loaded_count)

        except KeyboardInterrupt:
            console.print(safe_t("commands.watch.stopped", fallback="\n[#B565D8]已停止監視[/#B565D8]"))

    def reload_command(self, command_name: str) -> bool:
        """
        重新載入指定命令

        Args:
            command_name: 命令名稱

        Returns:
            bool: 是否成功重新載入
        """
        if command_name not in self.command_file_map:
            console.print(safe_t("commands.reload.not_found", fallback="[dim #B565D8]錯誤：找不到命令 '{name}'[/dim #B565D8]").format(name=command_name))
            return False

        file_path = self.command_file_map[command_name]

        try:
            # 先取消註冊舊命令
            self.registry.unregister_command(command_name)

            # 重新載入
            command = self.load_command_from_file(file_path)

            if command:
                success = self.registry.register_command(
                    command.name,
                    command,
                    save_to_config=False
                )

                if success:
                    # 更新記錄
                    self.loaded_files[file_path].modified_time = os.path.getmtime(file_path)

                    console.print(safe_t("commands.reload.success", fallback="[#B565D8]✓ 已重新載入命令：{name}[/#B565D8]").format(name=command_name))
                    return True

            return False

        except Exception as e:
            console.print(safe_t("commands.reload.failed", fallback="[dim #B565D8]錯誤：重新載入失敗 - {error}[/dim #B565D8]").format(error=e))
            return False

    def show_loaded_commands(self):
        """顯示已載入的命令列表"""
        if not self.loaded_files:
            console.print(safe_t("commands.list.empty", fallback="[#B565D8]尚未載入任何 Markdown 命令[/#B565D8]"))
            return

        table = Table(show_header=True, header_style="bold #B565D8")
        table.add_column("命令名稱", style="#B565D8")
        table.add_column("檔案名稱", style="white")
        table.add_column("狀態", style="green")
        table.add_column("修改時間", style="#B565D8")

        for file_info in self.loaded_files.values():
            # 格式化時間
            mtime = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(file_info.modified_time)
            )

            # 狀態
            status = "✓ 有效" if file_info.is_valid else "✗ 錯誤"

            table.add_row(
                file_info.command_name or "-",
                file_info.file_name,
                status,
                mtime
            )

        console.print(safe_t("commands.list.header", fallback="\n[bold #B565D8]已載入的 Markdown 命令（共 {count} 個）：[/bold #B565D8]").format(count=len(self.loaded_files)))
        console.print(table)

        # 顯示錯誤詳情
        error_files = [f for f in self.loaded_files.values() if not f.is_valid]

        if error_files:
            console.print(safe_t("commands.list.errors", fallback="\n[bold #B565D8]錯誤詳情：[/bold #B565D8]"))
            for file_info in error_files:
                console.print(f"  [dim #B565D8]✗ {file_info.file_name}：{file_info.error_message}[/dim #B565D8]")

    def create_example_command(self, command_name: str = "example") -> str:
        """
        創建範例命令檔案

        Args:
            command_name: 命令名稱

        Returns:
            str: 創建的檔案路徑
        """
        file_path = os.path.join(self.commands_dir, f"{command_name}.md")

        if os.path.exists(file_path):
            console.print(safe_t("commands.example.exists", fallback="[#B565D8]警告：檔案已存在：{path}[/#B565D8]").format(path=file_path))
            return file_path

        example_content = """---
name: example
description: 這是一個範例自訂命令
type: template
parameters:
  - task
  - language
tags:
  - example
  - tutorial
author: ChatGemini User
version: 1.0.0
examples:
  - "example task='寫一個函數' language='Python'"
  - "example task='建立類別' language='Java'"
---

請執行以下任務：

**任務**：{task}
**程式語言**：{language|default:"Python"}

{% if include_tests %}
請同時包含單元測試。
{% endif %}

{% if documentation %}
請包含詳細的文檔註釋。
{% endif %}

請確保程式碼：
1. 清晰易讀
2. 遵循最佳實踐
3. 包含錯誤處理
"""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(example_content)

        console.print(safe_t("commands.example.created", fallback="[#B565D8]✓ 已創建範例命令：{path}[/#B565D8]").format(path=file_path))

        return file_path

    def get_statistics(self) -> Dict[str, Any]:
        """
        取得載入統計資訊

        Returns:
            Dict[str, Any]: 統計資訊
        """
        total = len(self.loaded_files)
        valid = len([f for f in self.loaded_files.values() if f.is_valid])
        invalid = total - valid

        return {
            'total_files': total,
            'valid_files': valid,
            'invalid_files': invalid,
            'commands_dir': self.commands_dir,
            'loaded_commands': list(self.command_file_map.keys())
        }


def main():
    """測試用主程式"""
    console.print(safe_t("commands.test.title", fallback="[bold #B565D8]CodeGemini Markdown Command Loader 測試[/bold #B565D8]\n"))

    # 建立載入器
    loader = MarkdownCommandLoader()

    # 創建範例命令
    console.print(safe_t("commands.test.step1", fallback="[bold]1. 創建範例命令檔案[/bold]"))
    loader.create_example_command("example")
    loader.create_example_command("test-command")

    # 掃描並載入
    console.print(safe_t("commands.test.step2", fallback="\n[bold]2. 掃描並載入命令[/bold]"))
    loaded_count = loader.scan_and_load()

    # 顯示已載入的命令
    console.print(safe_t("commands.test.step3", fallback="\n[bold]3. 已載入的命令[/bold]"))
    loader.show_loaded_commands()

    # 顯示統計資訊
    console.print(safe_t("commands.test.step4", fallback="\n[bold]4. 統計資訊[/bold]"))
    stats = loader.get_statistics()
    console.print(Panel(
        f"""[bold]總檔案數：[/bold]{stats['total_files']}
[bold]有效檔案：[/bold]{stats['valid_files']}
[bold]無效檔案：[/bold]{stats['invalid_files']}
[bold]命令目錄：[/bold]{stats['commands_dir']}
[bold]已載入命令：[/bold]{', '.join(stats['loaded_commands']) if stats['loaded_commands'] else '無'}""",
        title="統計資訊",
        border_style="#B565D8"
    ))

    # 顯示命令詳情
    if loaded_count > 0:
        console.print(safe_t("commands.test.step5", fallback="\n[bold]5. 命令詳情（範例）[/bold]"))
        loader.registry.show_command_details("example")

    console.print(safe_t("commands.test.completed", fallback="\n[bold green]✅ 測試完成[/bold green]"))


if __name__ == "__main__":
    main()
