#!/usr/bin/env python3
"""
系統健康檢查模組 - /doctor 斜線指令實作

設計哲學：
- 一鍵診斷 - 快速定位問題
- 預防性維護 - 發現潛在風險
- 清晰報告 - 視覺化狀態顯示

Created: 2025-11-01
Author: Claude Code with Saki-tw
"""

import os
import sys
import shutil
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


@dataclass
class HealthCheckResult:
    """健康檢查結果"""
    name: str           # 檢查項目名稱
    status: str         # ok, warning, error
    value: str          # 檢查結果值
    message: str = ""   # 附加訊息
    fix_suggestion: str = ""  # 修復建議


class SystemDoctor:
    """系統健康檢查器"""

    def __init__(self):
        self.console = Console()
        self.results: List[HealthCheckResult] = []

    def run_all_checks(self) -> List[HealthCheckResult]:
        """執行所有健康檢查"""
        self.console.print("\n[bold #B565D8]🔍 執行系統健康檢查...[/bold #B565D8]\n")

        # 1. 環境檢查
        self.check_python_version()
        self.check_api_key()

        # 2. 依賴檢查
        self.check_dependencies()

        # 3. 資源檢查
        self.check_disk_space()
        self.check_network()

        # 4. 工具檢查
        self.check_ffmpeg()
        self.check_git()

        return self.results

    def check_python_version(self):
        """檢查 Python 版本"""
        version_info = sys.version_info
        current_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

        if version_info >= (3, 8):
            self.results.append(HealthCheckResult(
                name="Python 版本",
                status="ok",
                value=current_version
            ))
        elif version_info >= (3, 7):
            self.results.append(HealthCheckResult(
                name="Python 版本",
                status="warning",
                value=current_version,
                message="建議升級到 Python 3.8+",
                fix_suggestion="使用 pyenv 或系統套件管理器升級 Python"
            ))
        else:
            self.results.append(HealthCheckResult(
                name="Python 版本",
                status="error",
                value=current_version,
                message="版本過舊，不支援",
                fix_suggestion="必須升級到 Python 3.8 或更高版本"
            ))

    def check_api_key(self):
        """檢查 Gemini API 金鑰"""
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')

        if api_key:
            # 遮蔽顯示（只顯示前8字元）
            masked_key = f"{api_key[:8]}...{'*' * 20}"
            self.results.append(HealthCheckResult(
                name="Gemini API 金鑰",
                status="ok",
                value=f"已設定 ({masked_key})"
            ))
        else:
            self.results.append(HealthCheckResult(
                name="Gemini API 金鑰",
                status="error",
                value="未設定",
                message="無法使用 Gemini API",
                fix_suggestion="在 .env 檔案設定 GOOGLE_API_KEY 或 GEMINI_API_KEY"
            ))

    def check_dependencies(self):
        """檢查必要套件"""
        required_packages = {
            'google-genai': 'google.genai',
            'rich': 'rich',
            'pyyaml': 'yaml',
            'python-dotenv': 'dotenv',
            'requests': 'requests',
        }

        missing_packages = []

        for package_name, import_name in required_packages.items():
            try:
                # 直接使用 importlib.util 檢查模組是否存在
                spec = importlib.util.find_spec(import_name)
                if spec is None:
                    raise ImportError(f"No module named '{import_name}'")

                self.results.append(HealthCheckResult(
                    name=f"套件: {package_name}",
                    status="ok",
                    value="已安裝"
                ))
            except ImportError:
                missing_packages.append(package_name)
                self.results.append(HealthCheckResult(
                    name=f"套件: {package_name}",
                    status="error",
                    value="未安裝",
                    fix_suggestion=f"執行: pip install {package_name}"
                ))

        # 總結依賴狀態
        if missing_packages:
            fix_cmd = f"pip install {' '.join(missing_packages)}"
            self.results.append(HealthCheckResult(
                name="依賴套件總結",
                status="error",
                value=f"{len(missing_packages)} 個套件缺失",
                fix_suggestion=f"一鍵安裝: {fix_cmd}"
            ))
        else:
            self.results.append(HealthCheckResult(
                name="依賴套件總結",
                status="ok",
                value="全部已安裝"
            ))

    def check_disk_space(self):
        """檢查磁碟空間"""
        try:
            stat = shutil.disk_usage('.')
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            used_percent = (stat.used / stat.total) * 100

            if free_gb > 5.0:
                status = "ok"
                message = ""
            elif free_gb > 1.0:
                status = "warning"
                message = "可用空間不足"
            else:
                status = "error"
                message = "可用空間嚴重不足"

            self.results.append(HealthCheckResult(
                name="磁碟空間",
                status=status,
                value=f"{free_gb:.1f} GB 可用 / {total_gb:.1f} GB 總容量 (使用 {used_percent:.1f}%)",
                message=message,
                fix_suggestion="清理不必要的檔案或擴充儲存空間" if status != "ok" else ""
            ))
        except Exception as e:
            self.results.append(HealthCheckResult(
                name="磁碟空間",
                status="warning",
                value="無法檢查",
                message=str(e)
            ))

    def check_network(self):
        """檢查網路連線"""
        try:
            import socket
            # 測試 Google AI API 連線
            socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=5)

            self.results.append(HealthCheckResult(
                name="網路連線",
                status="ok",
                value="正常 (可連接 Gemini API)"
            ))
        except (socket.timeout, socket.error) as e:
            self.results.append(HealthCheckResult(
                name="網路連線",
                status="error",
                value="無法連接",
                message=str(e),
                fix_suggestion="檢查網路設定或防火牆規則"
            ))
        except Exception as e:
            self.results.append(HealthCheckResult(
                name="網路連線",
                status="warning",
                value="檢查失敗",
                message=str(e)
            ))

    def check_ffmpeg(self):
        """檢查 FFmpeg（媒體功能需要）"""
        ffmpeg_path = shutil.which('ffmpeg')

        if ffmpeg_path:
            try:
                # 取得 FFmpeg 版本
                result = subprocess.run(
                    ['ffmpeg', '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                # 提取版本號（第一行）
                version_line = result.stdout.split('\n')[0]
                version = version_line.split(' ')[2] if len(version_line.split(' ')) > 2 else "未知"

                self.results.append(HealthCheckResult(
                    name="FFmpeg",
                    status="ok",
                    value=f"已安裝 (版本 {version})"
                ))
            except Exception as e:
                self.results.append(HealthCheckResult(
                    name="FFmpeg",
                    status="warning",
                    value="已安裝但無法取得版本",
                    message=str(e)
                ))
        else:
            self.results.append(HealthCheckResult(
                name="FFmpeg",
                status="warning",
                value="未安裝",
                message="媒體處理功能將受限",
                fix_suggestion=(
                    "macOS: brew install ffmpeg\n"
                    "Ubuntu: sudo apt install ffmpeg\n"
                    "Windows: 從 https://ffmpeg.org/download.html 下載"
                )
            ))

    def check_git(self):
        """檢查 Git（版本控制需要）"""
        git_path = shutil.which('git')

        if git_path:
            try:
                # 取得 Git 版本
                result = subprocess.run(
                    ['git', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                version = result.stdout.strip().replace('git version ', '')

                self.results.append(HealthCheckResult(
                    name="Git",
                    status="ok",
                    value=f"已安裝 (版本 {version})"
                ))
            except Exception as e:
                self.results.append(HealthCheckResult(
                    name="Git",
                    status="warning",
                    value="已安裝但無法取得版本",
                    message=str(e)
                ))
        else:
            self.results.append(HealthCheckResult(
                name="Git",
                status="warning",
                value="未安裝",
                message="版本控制功能將受限",
                fix_suggestion=(
                    "macOS: brew install git\n"
                    "Ubuntu: sudo apt install git\n"
                    "Windows: 從 https://git-scm.com/download/win 下載"
                )
            ))

    def display_report(self):
        """顯示健康檢查報告"""
        # 建立報告表格
        table = Table(
            title="系統健康檢查報告",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold #B565D8"
        )

        table.add_column("檢查項目", style="#87CEEB", width=25)
        table.add_column("狀態", width=10)
        table.add_column("結果", style="white", width=50)

        # 統計
        ok_count = 0
        warning_count = 0
        error_count = 0

        for result in self.results:
            # 狀態圖示和顏色
            if result.status == "ok":
                status_display = "[green]✓ 正常[/green]"
                ok_count += 1
            elif result.status == "warning":
                status_display = "[yellow]⚠ 警告[/yellow]"
                warning_count += 1
            else:
                status_display = "[red]✗ 錯誤[/red]"
                error_count += 1

            # 結果顯示（包含訊息）
            value_display = result.value
            if result.message:
                value_display += f"\n[dim]{result.message}[/dim]"

            table.add_row(
                result.name,
                status_display,
                value_display
            )

        # 顯示表格
        self.console.print("\n")
        self.console.print(table)

        # 顯示統計
        self.console.print(f"\n[bold]檢查統計:[/bold]")
        self.console.print(f"  [green]✓ 正常: {ok_count}[/green]")
        self.console.print(f"  [yellow]⚠ 警告: {warning_count}[/yellow]")
        self.console.print(f"  [red]✗ 錯誤: {error_count}[/red]")

        # 顯示修復建議
        issues = [r for r in self.results if r.status in ('warning', 'error') and r.fix_suggestion]
        if issues:
            self.console.print(f"\n[bold yellow]📋 修復建議:[/bold yellow]\n")

            for i, issue in enumerate(issues, 1):
                self.console.print(Panel(
                    f"[bold]{issue.name}[/bold]\n\n"
                    f"問題: {issue.message or issue.value}\n\n"
                    f"[green]建議解決方案:[/green]\n{issue.fix_suggestion}",
                    border_style="yellow",
                    title=f"問題 {i}",
                    title_align="left"
                ))

        # 總體健康度評分
        total_checks = len(self.results)
        health_score = ((ok_count * 1.0 + warning_count * 0.5) / total_checks) * 100 if total_checks > 0 else 0

        if health_score >= 90:
            health_status = "[green]優秀[/green]"
            health_emoji = "🎉"
        elif health_score >= 70:
            health_status = "[yellow]良好[/yellow]"
            health_emoji = "👍"
        elif health_score >= 50:
            health_status = "[yellow]尚可[/yellow]"
            health_emoji = "⚠️"
        else:
            health_status = "[red]需要改善[/red]"
            health_emoji = "❌"

        self.console.print(f"\n{health_emoji} [bold]系統健康度:[/bold] {health_status} ([bold]{health_score:.0f}[/bold]/100)")

        # 生成時間戳記
        self.console.print(f"\n[dim]檢查時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")


def run_doctor():
    """執行系統健康檢查（供外部調用）"""
    doctor = SystemDoctor()
    doctor.run_all_checks()
    doctor.display_report()

    # 返回是否有嚴重錯誤
    has_errors = any(r.status == 'error' for r in doctor.results)
    return not has_errors


if __name__ == '__main__':
    # 獨立執行測試
    success = run_doctor()
    sys.exit(0 if success else 1)
