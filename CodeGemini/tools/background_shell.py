#!/usr/bin/env python3
"""
CodeGemini Background Shell Module
背景 Shell 管理工具 - 支援長時間運行的任務

此模組負責：
1. 啟動背景 Shell
2. 監控背景進程輸出
3. 過濾輸出（正則表達式）
4. 終止背景 Shell
5. 列出所有背景 Shell
"""

import os
import re
import subprocess
import threading
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from rich.console import Console
from rich.table import Table

console = Console()


class ShellStatus(str, Enum):
    """Shell 狀態"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


@dataclass
class BackgroundShell:
    """背景 Shell 資訊"""
    shell_id: str
    command: str
    process: subprocess.Popen
    status: ShellStatus = ShellStatus.RUNNING
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    output_buffer: List[str] = field(default_factory=list)
    error_buffer: List[str] = field(default_factory=list)
    output_lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def is_running(self) -> bool:
        """是否正在運行"""
        return self.status == ShellStatus.RUNNING and self.process.poll() is None

    @property
    def runtime(self) -> float:
        """運行時間（秒）"""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return (datetime.now() - self.started_at).total_seconds()


class BackgroundShellManager:
    """
    背景 Shell 管理器

    功能：
    - 啟動背景 Shell 並分配 ID
    - 實時捕獲輸出
    - 支援輸出過濾（正則表達式）
    - 終止背景進程
    - 列出所有背景 Shell
    """

    def __init__(self):
        """初始化背景 Shell 管理器"""
        self.shells: Dict[str, BackgroundShell] = {}
        self._shell_counter = 0
        self._lock = threading.Lock()

        console.print("[dim]BackgroundShellManager 初始化完成[/dim]")

    def start_shell(
        self,
        command: str,
        shell_id: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> str:
        """
        啟動背景 Shell

        Args:
            command: 要執行的命令
            shell_id: Shell ID（可選，自動生成）
            cwd: 工作目錄
            env: 環境變數

        Returns:
            str: Shell ID
        """
        console.print(f"\n[cyan]🚀 啟動背景 Shell...[/cyan]")
        console.print(f"[dim]命令：{command}[/dim]")

        # 生成 Shell ID
        if not shell_id:
            with self._lock:
                self._shell_counter += 1
                shell_id = f"shell_{self._shell_counter}"

        # 檢查 ID 是否已存在
        if shell_id in self.shells:
            console.print(f"[red]✗ Shell ID 已存在：{shell_id}[/red]")
            raise ValueError(f"Shell ID '{shell_id}' already exists")

        # 準備環境變數
        shell_env = os.environ.copy()
        if env:
            shell_env.update(env)

        try:
            # 啟動進程
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                cwd=cwd,
                env=shell_env,
                text=True,
                bufsize=1  # 行緩衝
            )

            # 建立 BackgroundShell
            bg_shell = BackgroundShell(
                shell_id=shell_id,
                command=command,
                process=process
            )

            # 儲存到管理器
            self.shells[shell_id] = bg_shell

            # 啟動輸出監控執行緒
            self._start_output_monitoring(bg_shell)

            console.print(f"[green]✓ 背景 Shell 已啟動[/green]")
            console.print(f"  Shell ID：{shell_id}")
            console.print(f"  PID：{process.pid}")

            return shell_id

        except Exception as e:
            console.print(f"[red]✗ 啟動失敗：{e}[/red]")
            raise

    def get_output(
        self,
        shell_id: str,
        filter_regex: Optional[str] = None,
        clear_buffer: bool = False
    ) -> str:
        """
        取得背景 Shell 輸出

        Args:
            shell_id: Shell ID
            filter_regex: 正則表達式過濾（可選）
            clear_buffer: 是否清空緩衝區

        Returns:
            str: 輸出內容
        """
        if shell_id not in self.shells:
            console.print(f"[red]✗ Shell 不存在：{shell_id}[/red]")
            return ""

        bg_shell = self.shells[shell_id]

        with bg_shell.output_lock:
            # 取得輸出
            output_lines = bg_shell.output_buffer.copy()

            # 應用過濾
            if filter_regex:
                pattern = re.compile(filter_regex)
                output_lines = [line for line in output_lines if pattern.search(line)]

            output = "".join(output_lines)

            # 清空緩衝區
            if clear_buffer:
                bg_shell.output_buffer.clear()

        return output

    def kill_shell(self, shell_id: str, force: bool = False) -> bool:
        """
        終止背景 Shell

        Args:
            shell_id: Shell ID
            force: 是否強制終止（SIGKILL）

        Returns:
            bool: 是否成功終止
        """
        console.print(f"\n[yellow]⚠️  終止背景 Shell：{shell_id}[/yellow]")

        if shell_id not in self.shells:
            console.print(f"[red]✗ Shell 不存在：{shell_id}[/red]")
            return False

        bg_shell = self.shells[shell_id]

        if not bg_shell.is_running:
            console.print(f"[yellow]⚠️  Shell 已停止[/yellow]")
            return True

        try:
            if force:
                bg_shell.process.kill()  # SIGKILL
            else:
                bg_shell.process.terminate()  # SIGTERM

            # 等待進程結束
            bg_shell.process.wait(timeout=5)

            # 更新狀態
            bg_shell.status = ShellStatus.KILLED
            bg_shell.ended_at = datetime.now()
            bg_shell.exit_code = bg_shell.process.returncode

            console.print(f"[green]✓ Shell 已終止[/green]")
            return True

        except subprocess.TimeoutExpired:
            console.print(f"[yellow]⚠️  終止超時，強制 kill[/yellow]")
            bg_shell.process.kill()
            bg_shell.status = ShellStatus.KILLED
            bg_shell.ended_at = datetime.now()
            return True

        except Exception as e:
            console.print(f"[red]✗ 終止失敗：{e}[/red]")
            return False

    def list_shells(self) -> List[Dict[str, Any]]:
        """
        列出所有背景 Shell

        Returns:
            List[Dict]: Shell 資訊列表
        """
        shells_info = []

        for shell_id, bg_shell in self.shells.items():
            # 更新狀態
            if bg_shell.is_running:
                if bg_shell.process.poll() is not None:
                    # 進程已結束
                    bg_shell.status = ShellStatus.COMPLETED
                    bg_shell.ended_at = datetime.now()
                    bg_shell.exit_code = bg_shell.process.returncode

            info = {
                "shell_id": shell_id,
                "command": bg_shell.command,
                "status": bg_shell.status.value,
                "pid": bg_shell.process.pid if bg_shell.is_running else None,
                "started_at": bg_shell.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                "runtime": f"{bg_shell.runtime:.1f}s",
                "exit_code": bg_shell.exit_code,
                "output_lines": len(bg_shell.output_buffer)
            }

            shells_info.append(info)

        return shells_info

    def display_shells(self) -> None:
        """展示所有背景 Shell"""
        shells_info = self.list_shells()

        if not shells_info:
            console.print("[yellow]⚠️  無背景 Shell[/yellow]")
            return

        console.print(f"\n[bold]🖥️  背景 Shell 列表（{len(shells_info)} 個）[/bold]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Shell ID", style="cyan")
        table.add_column("狀態", style="white")
        table.add_column("命令", style="dim")
        table.add_column("運行時間", style="yellow")
        table.add_column("輸出行數", style="green")

        for info in shells_info:
            # 狀態顏色
            status = info["status"]
            if status == "running":
                status_text = "[green]●[/green] 運行中"
            elif status == "completed":
                status_text = "[blue]✓[/blue] 已完成"
            elif status == "failed":
                status_text = "[red]✗[/red] 失敗"
            else:  # killed
                status_text = "[yellow]⊗[/yellow] 已終止"

            # 命令截斷
            command = info["command"]
            if len(command) > 40:
                command = command[:37] + "..."

            table.add_row(
                info["shell_id"],
                status_text,
                command,
                info["runtime"],
                str(info["output_lines"])
            )

        console.print(table)

    def get_shell(self, shell_id: str) -> Optional[BackgroundShell]:
        """取得 Shell 物件"""
        return self.shells.get(shell_id)

    def cleanup_completed(self) -> int:
        """清理已完成的 Shell"""
        to_remove = []

        for shell_id, bg_shell in self.shells.items():
            if not bg_shell.is_running:
                to_remove.append(shell_id)

        for shell_id in to_remove:
            del self.shells[shell_id]

        if to_remove:
            console.print(f"[green]✓ 清理了 {len(to_remove)} 個已完成的 Shell[/green]")

        return len(to_remove)

    def _start_output_monitoring(self, bg_shell: BackgroundShell) -> None:
        """啟動輸出監控執行緒"""

        def monitor_stdout():
            """監控標準輸出"""
            try:
                for line in bg_shell.process.stdout:
                    with bg_shell.output_lock:
                        bg_shell.output_buffer.append(line)
            except Exception:
                pass

        def monitor_stderr():
            """監控標準錯誤"""
            try:
                for line in bg_shell.process.stderr:
                    with bg_shell.output_lock:
                        bg_shell.error_buffer.append(line)
                        bg_shell.output_buffer.append(f"[ERROR] {line}")
            except Exception:
                pass

        # 啟動監控執行緒
        stdout_thread = threading.Thread(target=monitor_stdout, daemon=True)
        stderr_thread = threading.Thread(target=monitor_stderr, daemon=True)

        stdout_thread.start()
        stderr_thread.start()


# ==================== 命令列介面 ====================

def main():
    """Background Shell 命令列工具"""
    import sys

    console.print("\n[bold cyan]CodeGemini Background Shell Manager[/bold cyan]\n")

    if len(sys.argv) < 2:
        console.print("用法：")
        console.print("  python tools/background_shell.py start <command>")
        console.print("  python tools/background_shell.py output <shell_id> [--filter <regex>]")
        console.print("  python tools/background_shell.py kill <shell_id>")
        console.print("  python tools/background_shell.py list")
        console.print("\n範例：")
        console.print("  python tools/background_shell.py start 'ping -c 10 google.com'")
        console.print("  python tools/background_shell.py output shell_1")
        console.print("  python tools/background_shell.py kill shell_1")
        return

    manager = BackgroundShellManager()
    action = sys.argv[1]

    if action == "start" and len(sys.argv) >= 3:
        command = sys.argv[2]
        shell_id = manager.start_shell(command)
        console.print(f"\n[green]✓ Shell ID：{shell_id}[/green]")

    elif action == "output" and len(sys.argv) >= 3:
        shell_id = sys.argv[2]
        filter_regex = None

        # 解析 --filter 參數
        for i, arg in enumerate(sys.argv):
            if arg == "--filter" and i + 1 < len(sys.argv):
                filter_regex = sys.argv[i + 1]

        output = manager.get_output(shell_id, filter_regex=filter_regex)
        console.print(f"\n[bold]輸出：[/bold]\n")
        console.print(output)

    elif action == "kill" and len(sys.argv) >= 3:
        shell_id = sys.argv[2]
        manager.kill_shell(shell_id)

    elif action == "list":
        manager.display_shells()

    else:
        console.print("[red]✗ 無效的命令[/red]")


if __name__ == "__main__":
    main()
