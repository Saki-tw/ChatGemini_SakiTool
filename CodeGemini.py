#!/usr/bin/env python3
"""
CodeGemini - Google Gemini CLI 管理工具 (Python API)
版本：1.0.1
維護者：Saki-tw (with Claude Code)
日期：2025-10-21

用途：
  提供 Python API 介面來管理 Google Gemini CLI
  整合 Shell 腳本功能到 ChatGemini_SakiTool 生態系統

核心功能：
  - 環境檢查與驗證
  - Gemini CLI 安裝/更新/卸載
  - API Key 配置管理
  - MCP 配置管理
  - Templates 管理
  - 背景 Shell 管理（新增 v1.1.0）
  - 任務追蹤系統（新增 v1.1.0）
  - 互動式問答（新增 v1.1.0）
  - 與 ChatGemini 整合

相關檔案：
  - CodeGemini/INSTALL.sh - 安裝腳本
  - CodeGemini/CHECK.sh - 環境檢查腳本
  - CodeGemini/SETUP-API-KEY.sh - API Key 設定腳本
  - CodeGemini/UPDATE.sh - 更新腳本
  - CodeGemini/UNINSTALL.sh - 卸載腳本
"""

import os
import sys
import subprocess
import json
import logging
import threading
import time
import re
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


# Gemini API 定價資訊
USD_TO_TWD = 31.0  # 美元兌新台幣匯率（2025年10月）

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常數定義
CODEGEMINI_DIR = Path(__file__).parent / "CodeGemini"
REQUIRED_NODE_VERSION = 18
REQUIRED_NPM_VERSION = 9

# ============================================================================
# 資料結構
# ============================================================================

class InstallStatus(Enum):
    """安裝狀態枚舉"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    OUTDATED = "outdated"
    ERROR = "error"

class ShellStatus(str, Enum):
    """Shell 狀態枚舉"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"

class TodoStatus(str, Enum):
    """任務狀態枚舉"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

@dataclass
class EnvironmentCheck:
    """環境檢查結果"""
    os_type: str
    os_version: str
    arch: str
    node_installed: bool
    node_version: Optional[str]
    npm_installed: bool
    npm_version: Optional[str]
    gemini_cli_installed: bool
    gemini_cli_version: Optional[str]
    api_key_configured: bool
    passed: bool
    warnings: List[str]
    errors: List[str]

@dataclass
class GeminiCLIInfo:
    """Gemini CLI 資訊"""
    installed: bool
    version: Optional[str]
    install_path: Optional[str]
    status: InstallStatus

@dataclass
class BackgroundShell:
    """背景 Shell 資訊"""
    shell_id: str
    command: str
    process: subprocess.Popen
    status: ShellStatus = ShellStatus.RUNNING
    output: List[str] = field(default_factory=list)
    error_output: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    exit_code: Optional[int] = None

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

@dataclass
class Todo:
    """任務項目"""
    content: str  # 任務內容（祈使句）
    active_form: str  # 進行中形式（現在進行式）
    status: TodoStatus = TodoStatus.PENDING
    index: int = 0  # 任務索引
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def mark_in_progress(self) -> None:
        """標記為進行中"""
        self.status = TodoStatus.IN_PROGRESS
        if not self.started_at:
            self.started_at = datetime.now()

    def mark_completed(self) -> None:
        """標記為已完成"""
        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now()

    @property
    def is_pending(self) -> bool:
        return self.status == TodoStatus.PENDING

    @property
    def is_in_progress(self) -> bool:
        return self.status == TodoStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        return self.status == TodoStatus.COMPLETED

    @property
    def display_text(self) -> str:
        """顯示文字（根據狀態選擇）"""
        if self.is_in_progress:
            return self.active_form
        return self.content

@dataclass
class Question:
    """互動式問答題目"""
    question: str
    header: str
    options: List[Dict[str, str]]
    multi_select: bool = False

@dataclass
class Checkpoint:
    """Checkpoint 資訊"""
    checkpoint_id: str
    description: str
    created_at: datetime
    files_snapshot: Dict[str, str]  # {file_path: file_hash}
    metadata: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# 環境檢查模組
# ============================================================================

class EnvironmentChecker:
    """環境檢查器"""

    def __init__(self):
        self.warnings = []
        self.errors = []

    def check_command(self, command: str) -> bool:
        """檢查指令是否存在"""
        try:
            subprocess.run(
                ["which", command],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_command_version(self, command: str, version_flag: str = "--version") -> Optional[str]:
        """取得指令版本"""
        try:
            result = subprocess.run(
                [command, version_flag],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def check_node_version(self) -> Tuple[bool, Optional[str]]:
        """檢查 Node.js 版本"""
        if not self.check_command("node"):
            return False, None

        version_str = self.get_command_version("node", "-v")
        if not version_str:
            return False, None

        # 解析版本號 (v18.0.0 -> 18)
        try:
            major_version = int(version_str.strip('v').split('.')[0])
            if major_version < REQUIRED_NODE_VERSION:
                self.warnings.append(
                    f"Node.js 版本過舊 ({version_str})，建議升級至 v{REQUIRED_NODE_VERSION}+"
                )
            return True, version_str
        except ValueError:
            return False, version_str

    def check_npm_version(self) -> Tuple[bool, Optional[str]]:
        """檢查 npm 版本"""
        if not self.check_command("npm"):
            return False, None

        version_str = self.get_command_version("npm", "-v")
        return (True, version_str) if version_str else (False, None)

    def check_gemini_cli(self) -> Tuple[bool, Optional[str]]:
        """檢查 Gemini CLI 是否已安裝"""
        if not self.check_command("gemini"):
            return False, None

        version_str = self.get_command_version("gemini", "--version")
        return (True, version_str) if version_str else (True, "unknown")

    def check_api_key(self) -> bool:
        """檢查 API Key 是否已配置"""
        # 檢查環境變數
        if os.getenv("GEMINI_API_KEY"):
            return True

        # 檢查全域配置
        global_env = Path.home() / ".gemini" / ".env"
        if global_env.exists():
            with open(global_env) as f:
                if "GEMINI_API_KEY" in f.read():
                    return True

        # 檢查專案配置
        project_env = CODEGEMINI_DIR / ".env"
        if project_env.exists():
            with open(project_env) as f:
                if "GEMINI_API_KEY" in f.read():
                    return True

        return False

    def run_full_check(self) -> EnvironmentCheck:
        """執行完整環境檢查"""
        logger.info("開始環境檢查...")

        # 作業系統資訊
        os_type = os.uname().sysname
        os_version = os.uname().release
        arch = os.uname().machine

        # Node.js 檢查
        node_installed, node_version = self.check_node_version()
        if not node_installed:
            self.errors.append("Node.js 未安裝或版本不符")

        # npm 檢查
        npm_installed, npm_version = self.check_npm_version()
        if not npm_installed:
            self.errors.append("npm 未安裝")

        # Gemini CLI 檢查
        gemini_installed, gemini_version = self.check_gemini_cli()

        # API Key 檢查
        api_key_configured = self.check_api_key()
        if not api_key_configured:
            self.warnings.append("GEMINI_API_KEY 未配置")

        # 判斷是否通過
        passed = len(self.errors) == 0

        return EnvironmentCheck(
            os_type=os_type,
            os_version=os_version,
            arch=arch,
            node_installed=node_installed,
            node_version=node_version,
            npm_installed=npm_installed,
            npm_version=npm_version,
            gemini_cli_installed=gemini_installed,
            gemini_cli_version=gemini_version,
            api_key_configured=api_key_configured,
            passed=passed,
            warnings=self.warnings.copy(),
            errors=self.errors.copy()
        )

# ============================================================================
# 安裝管理模組
# ============================================================================

class GeminiCLIManager:
    """Gemini CLI 管理器"""

    def __init__(self):
        self.checker = EnvironmentChecker()

    def get_status(self) -> GeminiCLIInfo:
        """取得 Gemini CLI 狀態"""
        installed, version = self.checker.check_gemini_cli()

        if not installed:
            status = InstallStatus.NOT_INSTALLED
            install_path = None
        else:
            # 檢查安裝路徑
            try:
                result = subprocess.run(
                    ["which", "gemini"],
                    check=True,
                    stdout=subprocess.PIPE,
                    text=True
                )
                install_path = result.stdout.strip()
                status = InstallStatus.INSTALLED
            except subprocess.CalledProcessError:
                install_path = None
                status = InstallStatus.ERROR

        return GeminiCLIInfo(
            installed=installed,
            version=version,
            install_path=install_path,
            status=status
        )

    def install(self, use_script: bool = True) -> bool:
        """安裝 Gemini CLI

        Args:
            use_script: 使用 INSTALL.sh 腳本（推薦）或直接使用 npm

        Returns:
            安裝是否成功
        """
        logger.info("開始安裝 Gemini CLI...")

        if use_script:
            script_path = CODEGEMINI_DIR / "INSTALL.sh"
            if not script_path.exists():
                logger.error(f"安裝腳本不存在: {script_path}")
                return False

            try:
                subprocess.run([str(script_path)], check=True)
                logger.info("✓ Gemini CLI 安裝成功")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"✗ 安裝失敗: {e}")
                return False
        else:
            # 直接使用 npm 安裝
            try:
                subprocess.run(
                    ["npm", "install", "-g", "@google/gemini-cli"],
                    check=True
                )
                logger.info("✓ Gemini CLI 安裝成功")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"✗ 安裝失敗: {e}")
                return False

    def update(self) -> bool:
        """更新 Gemini CLI"""
        logger.info("開始更新 Gemini CLI...")

        script_path = CODEGEMINI_DIR / "UPDATE.sh"
        if script_path.exists():
            try:
                subprocess.run([str(script_path)], check=True)
                logger.info("✓ Gemini CLI 更新成功")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"✗ 更新失敗: {e}")
                return False
        else:
            # 使用 npm 更新
            try:
                subprocess.run(
                    ["npm", "update", "-g", "@google/gemini-cli"],
                    check=True
                )
                logger.info("✓ Gemini CLI 更新成功")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"✗ 更新失敗: {e}")
                return False

    def uninstall(self) -> bool:
        """卸載 Gemini CLI"""
        logger.info("開始卸載 Gemini CLI...")

        script_path = CODEGEMINI_DIR / "UNINSTALL.sh"
        if script_path.exists():
            try:
                subprocess.run([str(script_path)], check=True)
                logger.info("✓ Gemini CLI 卸載成功")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"✗ 卸載失敗: {e}")
                return False
        else:
            # 使用 npm 卸載
            try:
                subprocess.run(
                    ["npm", "uninstall", "-g", "@google/gemini-cli"],
                    check=True
                )
                logger.info("✓ Gemini CLI 卸載成功")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"✗ 卸載失敗: {e}")
                return False

# ============================================================================
# API Key 配置模組
# ============================================================================

class APIKeyManager:
    """API Key 管理器"""

    def __init__(self):
        self.global_env = Path.home() / ".gemini" / ".env"
        self.project_env = CODEGEMINI_DIR / ".env"

    def get_api_key(self) -> Optional[str]:
        """取得 API Key"""
        # 優先從環境變數
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            return api_key

        # 從全域配置
        if self.global_env.exists():
            with open(self.global_env) as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip()

        # 從專案配置
        if self.project_env.exists():
            with open(self.project_env) as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip()

        return None

    def set_api_key(self, api_key: str, scope: str = "global") -> bool:
        """設定 API Key

        Args:
            api_key: API 金鑰
            scope: 範圍 ("global" 或 "project")

        Returns:
            設定是否成功
        """
        if scope == "global":
            self.global_env.parent.mkdir(parents=True, exist_ok=True)
            target = self.global_env
        else:
            target = self.project_env

        try:
            with open(target, 'w') as f:
                f.write(f"GEMINI_API_KEY={api_key}\n")
            logger.info(f"✓ API Key 已設定至 {target}")
            return True
        except Exception as e:
            logger.error(f"✗ 設定失敗: {e}")
            return False

    def setup_interactive(self) -> bool:
        """互動式 API Key 設定"""
        script_path = CODEGEMINI_DIR / "SETUP-API-KEY.sh"
        if not script_path.exists():
            logger.error(f"設定腳本不存在: {script_path}")
            return False

        try:
            subprocess.run([str(script_path)], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ 設定失敗: {e}")
            return False

# ============================================================================
# MCP 配置模組
# ============================================================================

class MCPConfigManager:
    """MCP 配置管理器"""

    def __init__(self):
        self.config_path = CODEGEMINI_DIR / "mcp-config.json"

    def load_config(self) -> Optional[Dict]:
        """載入 MCP 配置"""
        if not self.config_path.exists():
            logger.warning(f"MCP 配置檔不存在: {self.config_path}")
            return None

        try:
            with open(self.config_path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"✗ MCP 配置格式錯誤: {e}")
            return None

    def save_config(self, config: Dict) -> bool:
        """儲存 MCP 配置"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"✓ MCP 配置已儲存至 {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"✗ 儲存失敗: {e}")
            return False

# ============================================================================
# Templates 管理模組
# ============================================================================

class TemplateManager:
    """Templates 管理器"""

    def __init__(self):
        self.templates_dir = CODEGEMINI_DIR / "templates"

    def list_templates(self) -> List[str]:
        """列出所有 templates"""
        if not self.templates_dir.exists():
            return []

        return [f.name for f in self.templates_dir.iterdir() if f.is_file()]

    def load_template(self, name: str) -> Optional[str]:
        """載入 template"""
        template_path = self.templates_dir / name
        if not template_path.exists():
            logger.error(f"Template 不存在: {name}")
            return None

        try:
            with open(template_path) as f:
                return f.read()
        except Exception as e:
            logger.error(f"✗ 讀取失敗: {e}")
            return None

# ============================================================================
# Background Shells 管理模組
# ============================================================================

class BackgroundShellManager:
    """背景 Shell 管理器

    功能：
    - 啟動背景執行的 Shell 命令
    - 監控輸出並過濾
    - 管理 Shell 生命週期
    - 終止背景 Shell

    參考 Claude Code 的 Bash、BashOutput、KillShell 工具
    """

    def __init__(self):
        self.shells: Dict[str, BackgroundShell] = {}
        self._lock = threading.Lock()
        logger.info("BackgroundShellManager 已初始化")

    def start_shell(
        self,
        command: str,
        shell_id: Optional[str] = None,
        description: str = ""
    ) -> str:
        """啟動背景 Shell

        Args:
            command: 要執行的命令
            shell_id: Shell ID（若無則自動生成）
            description: 命令描述

        Returns:
            Shell ID
        """
        if not shell_id:
            shell_id = f"shell_{int(time.time() * 1000)}"

        with self._lock:
            if shell_id in self.shells:
                logger.warning(f"Shell ID 已存在: {shell_id}")
                return shell_id

            try:
                # 啟動背景進程
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                shell = BackgroundShell(
                    shell_id=shell_id,
                    command=command,
                    process=process
                )

                self.shells[shell_id] = shell

                # 啟動輸出收集線程
                thread = threading.Thread(
                    target=self._collect_output,
                    args=(shell_id,),
                    daemon=True
                )
                thread.start()

                logger.info(f"✓ 背景 Shell 已啟動: {shell_id}")
                if description:
                    logger.info(f"  描述: {description}")

                return shell_id

            except Exception as e:
                logger.error(f"✗ 啟動 Shell 失敗: {e}")
                raise

    def _collect_output(self, shell_id: str):
        """收集 Shell 輸出（在背景線程中執行）"""
        shell = self.shells.get(shell_id)
        if not shell:
            return

        try:
            for line in iter(shell.process.stdout.readline, ''):
                if not line:
                    break
                with self._lock:
                    shell.output.append(line.rstrip('\n'))

            exit_code = shell.process.wait()
            with self._lock:
                shell.exit_code = exit_code
                shell.ended_at = datetime.now()
                shell.status = ShellStatus.COMPLETED if exit_code == 0 else ShellStatus.FAILED

        except Exception as e:
            logger.error(f"✗ 收集輸出失敗 ({shell_id}): {e}")
            with self._lock:
                shell.status = ShellStatus.FAILED
                shell.ended_at = datetime.now()

    def get_output(
        self,
        shell_id: str,
        filter_regex: Optional[str] = None,
        clear: bool = False
    ) -> str:
        """獲取 Shell 輸出

        Args:
            shell_id: Shell ID
            filter_regex: 過濾正則表達式（僅返回匹配的行）
            clear: 是否清空已讀取的輸出

        Returns:
            輸出內容
        """
        with self._lock:
            shell = self.shells.get(shell_id)
            if not shell:
                logger.error(f"Shell 不存在: {shell_id}")
                return ""

            output = shell.output.copy()

            if clear:
                shell.output.clear()

            # 應用過濾器
            if filter_regex:
                try:
                    pattern = re.compile(filter_regex)
                    output = [line for line in output if pattern.search(line)]
                except re.error as e:
                    logger.error(f"✗ 正則表達式錯誤: {e}")

            return '\n'.join(output)

    def kill_shell(self, shell_id: str) -> bool:
        """終止背景 Shell

        Args:
            shell_id: Shell ID

        Returns:
            是否成功
        """
        with self._lock:
            shell = self.shells.get(shell_id)
            if not shell:
                logger.error(f"Shell 不存在: {shell_id}")
                return False

            try:
                shell.process.terminate()
                shell.process.wait(timeout=5)
                shell.status = ShellStatus.KILLED
                shell.ended_at = datetime.now()
                logger.info(f"✓ Shell 已終止: {shell_id}")
                return True

            except subprocess.TimeoutExpired:
                shell.process.kill()
                shell.status = ShellStatus.KILLED
                shell.ended_at = datetime.now()
                logger.warning(f"⚠ Shell 已強制終止: {shell_id}")
                return True

            except Exception as e:
                logger.error(f"✗ 終止 Shell 失敗: {e}")
                return False

    def list_shells(self) -> List[Dict[str, Any]]:
        """列出所有背景 Shell

        Returns:
            Shell 列表
        """
        with self._lock:
            return [
                {
                    "shell_id": shell.shell_id,
                    "command": shell.command,
                    "status": shell.status.value,
                    "is_running": shell.is_running,
                    "runtime": shell.runtime,
                    "started_at": shell.started_at.isoformat(),
                    "ended_at": shell.ended_at.isoformat() if shell.ended_at else None,
                    "exit_code": shell.exit_code,
                    "output_lines": len(shell.output)
                }
                for shell in self.shells.values()
            ]

    def cleanup_finished_shells(self):
        """清理已完成的 Shell"""
        with self._lock:
            finished = [
                sid for sid, shell in self.shells.items()
                if not shell.is_running
            ]
            for sid in finished:
                del self.shells[sid]

            if finished:
                logger.info(f"✓ 已清理 {len(finished)} 個完成的 Shell")

# ============================================================================
# Todo Tracking 模組
# ============================================================================

class TodoTracker:
    """任務追蹤器

    功能：
    - 追蹤任務狀態（pending/in_progress/completed）
    - 顯示進度給使用者
    - 支援 activeForm（進行中形式）

    參考 Claude Code 的 TodoWrite 工具
    """

    def __init__(self):
        self.todos: List[Todo] = []
        logger.info("TodoTracker 已初始化")

    def add_todo(self, content: str, active_form: str) -> None:
        """新增任務

        Args:
            content: 任務內容（命令式）
            active_form: 進行中形式（現在進行式）
        """
        todo = Todo(content=content, active_form=active_form)
        self.todos.append(todo)
        logger.info(f"✓ 任務已新增: {content}")

    def update_status(self, index: int, status: TodoStatus) -> bool:
        """更新任務狀態

        Args:
            index: 任務索引
            status: 新狀態（TodoStatus）

        Returns:
            是否成功
        """
        if not 0 <= index < len(self.todos):
            logger.error(f"任務索引超出範圍: {index}")
            return False

        todo = self.todos[index]
        old_status = todo.status

        # 使用 Todo 的方法更新狀態
        if status == TodoStatus.IN_PROGRESS:
            todo.mark_in_progress()
        elif status == TodoStatus.COMPLETED:
            todo.mark_completed()
        else:
            todo.status = status

        logger.info(f"✓ 任務狀態已更新: {todo.content} ({old_status.value} → {status.value})")
        return True

    def get_todos(self) -> List[Dict[str, Any]]:
        """獲取所有任務

        Returns:
            任務列表
        """
        return [
            {
                "content": todo.content,
                "active_form": todo.active_form,
                "status": todo.status.value,
                "display_text": todo.display_text,
                "created_at": todo.created_at.isoformat(),
                "started_at": todo.started_at.isoformat() if todo.started_at else None,
                "completed_at": todo.completed_at.isoformat() if todo.completed_at else None
            }
            for todo in self.todos
        ]

    def get_progress(self) -> Dict[str, Any]:
        """取得任務進度資訊

        Returns:
            進度資訊字典
        """
        total = len(self.todos)
        completed = sum(1 for t in self.todos if t.is_completed)
        in_progress = sum(1 for t in self.todos if t.is_in_progress)
        pending = sum(1 for t in self.todos if t.is_pending)

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "progress_percentage": (completed / total * 100) if total > 0 else 0
        }

    def clear_completed(self) -> int:
        """清除已完成的任務

        Returns:
            清除的任務數量
        """
        completed_count = sum(1 for t in self.todos if t.is_completed)
        self.todos = [t for t in self.todos if not t.is_completed]
        logger.info(f"✓ 已清除 {completed_count} 個已完成任務")
        return completed_count

# ============================================================================
# Interactive Q&A 模組
# ============================================================================

class InteractiveQA:
    """互動式問答

    功能：
    - 詢問使用者問題
    - 支援單選與多選
    - 提供選項說明

    參考 Claude Code 的 AskUserQuestion 工具
    """

    def __init__(self):
        logger.info("InteractiveQA 已初始化")

    def ask_question(
        self,
        question: str,
        options: List[Dict[str, str]],
        header: str = "",
        multi_select: bool = False
    ) -> List[str]:
        """詢問問題

        Args:
            question: 問題內容
            options: 選項列表 [{"label": "...", "description": "..."}, ...]
            header: 問題標題（短標籤，最多 12 字）
            multi_select: 是否支援多選

        Returns:
            選中的選項標籤列表
        """
        print("\n" + "=" * 60)
        if header:
            print(f"📌 {header}")
        print(f"❓ {question}")
        print("-" * 60)

        for i, option in enumerate(options, 1):
            label = option.get("label", "")
            description = option.get("description", "")
            print(f"  [{i}] {label}")
            if description:
                print(f"      {description}")

        if multi_select:
            print(f"\n  [0] 其他（自訂輸入）")
            print("提示：多選模式，輸入選項編號（用空格或逗號分隔），或輸入 0 自訂")
        else:
            print(f"\n  [0] 其他（自訂輸入）")
            print("提示：輸入選項編號，或輸入 0 自訂")

        print("=" * 60)

        while True:
            try:
                user_input = input("請選擇: ").strip()

                if not user_input:
                    print("⚠️  請輸入選項編號")
                    continue

                # 處理自訂輸入
                if user_input == "0":
                    custom = input("請輸入自訂答案: ").strip()
                    return [custom] if custom else []

                # 解析選擇
                if multi_select:
                    # 支援空格或逗號分隔
                    selections = re.split(r'[,\s]+', user_input)
                    indices = []
                    for s in selections:
                        try:
                            idx = int(s)
                            if 1 <= idx <= len(options):
                                indices.append(idx - 1)
                            else:
                                print(f"⚠️  無效的選項: {s}")
                                raise ValueError
                        except ValueError:
                            print(f"⚠️  請輸入有效的數字")
                            raise

                    if indices:
                        return [options[i]["label"] for i in indices]
                else:
                    idx = int(user_input)
                    if 1 <= idx <= len(options):
                        return [options[idx - 1]["label"]]
                    else:
                        print(f"⚠️  無效的選項: {idx}")
                        continue

            except ValueError:
                continue
            except KeyboardInterrupt:
                print("\n\n⚠️  已取消")
                return []

    def confirm(self, message: str, default: bool = True) -> bool:
        """詢問確認（是/否）

        Args:
            message: 確認訊息
            default: 預設值

        Returns:
            使用者選擇
        """
        default_text = "Y/n" if default else "y/N"
        print(f"\n❓ {message} ({default_text}): ", end="")

        try:
            response = input().strip().lower()

            if not response:
                return default

            return response in ['y', 'yes', '是', 'Y']

        except KeyboardInterrupt:
            print("\n⚠️  已取消")
            return False

# ============================================================================
# API 定價顯示模組
# ============================================================================

class PricingDisplay:
    """API 定價顯示器

    注意：
    - 當前實作的 Background Shells、Todo Tracking、Interactive Q&A
      三個功能本身**不會直接調用 Gemini API**，它們是純本地工具。

    - 但如果這些工具被整合到 Agent Mode 流程中使用時，
      Agent 本身會調用 API，此時可使用本模組顯示定價。

    定價參考：
    - Gemini 2.5 Pro: $1.25/1M tokens (input ≤200K)
    - Gemini 2.5 Flash: $0.15625/1M tokens (input)
    - Gemini 2.0 Flash Exp: $0.10/1M tokens (input)
    - Google Custom Search: $5/1000 queries (免費額度: 100/day)
    - Brave Search: ~$3/1000 queries (免費額度: 2000/month)
    """

    # Gemini API 定價表（美元 / 1M tokens）
    GEMINI_PRICING = {
        'gemini-2.5-pro': {
            'input_low': 1.25,      # ≤200K tokens
            'output_low': 10.0,
            'input_high': 2.5,      # >200K tokens
            'output_high': 15.0,
            'threshold': 200000,
        },
        'gemini-2.5-flash': {
            'input': 0.15625,
            'output': 0.625,
        },
        'gemini-2.5-flash-8b': {
            'input': 0.03125,
            'output': 0.125,
        },
        'gemini-2.0-flash-exp': {
            'input': 0.10,
            'output': 0.40,
        },
        'gemini-2.0-flash-thinking-exp': {
            'input': 0.10,
            'output': 0.40,
        },
    }

    # 搜尋 API 定價表
    SEARCH_API_PRICING = {
        'google_custom_search': {
            'cost_per_1000': 5.0,  # USD / 1000 queries
            'free_tier': 100,  # per day
            'note': '超過免費額度後計費'
        },
        'brave_search': {
            'cost_per_1000': 3.0,  # USD / 1000 queries (估計)
            'free_tier': 2000,  # per month
            'note': 'Free AI Plan: 2000/月，Basic AI: $3/1000 queries'
        },
        'duckduckgo': {
            'cost_per_1000': 0.0,  # 完全免費
            'free_tier': float('inf'),
            'note': '完全免費，無限制'
        }
    }

    def __init__(self, exchange_rate: float = USD_TO_TWD):
        self.exchange_rate = exchange_rate
        self.search_usage_count = {}  # {engine: count}
        logger.info("PricingDisplay 已初始化")

    def track_search_usage(self, engine: str, query_count: int = 1) -> Dict[str, Any]:
        """追蹤搜尋 API 使用量

        Args:
            engine: 搜尋引擎名稱
            query_count: 查詢次數

        Returns:
            使用統計與成本估算
        """
        if engine not in self.search_usage_count:
            self.search_usage_count[engine] = 0

        self.search_usage_count[engine] += query_count

        # 計算成本
        if engine in self.SEARCH_API_PRICING:
            pricing = self.SEARCH_API_PRICING[engine]
            total_queries = self.search_usage_count[engine]

            # 扣除免費額度
            billable_queries = max(0, total_queries - pricing['free_tier'])
            cost_usd = (billable_queries / 1000) * pricing['cost_per_1000']
            cost_twd = cost_usd * self.exchange_rate

            return {
                'engine': engine,
                'total_queries': total_queries,
                'free_tier': pricing['free_tier'],
                'billable_queries': billable_queries,
                'cost_usd': round(cost_usd, 6),
                'cost_twd': round(cost_twd, 4),
                'note': pricing['note']
            }

        return {'engine': engine, 'error': 'Unknown engine'}

    def estimate_search_cost(
        self,
        engine: str,
        query_count: int
    ) -> Dict[str, Any]:
        """預估搜尋 API 成本

        Args:
            engine: 搜尋引擎名稱
            query_count: 查詢次數

        Returns:
            成本資訊字典
        """
        if engine not in self.SEARCH_API_PRICING:
            return {'engine': engine, 'error': 'Unknown engine'}

        pricing = self.SEARCH_API_PRICING[engine]

        # 計算成本（假設已用完免費額度）
        cost_usd = (query_count / 1000) * pricing['cost_per_1000']
        cost_twd = cost_usd * self.exchange_rate

        return {
            'engine': engine,
            'query_count': query_count,
            'free_tier': pricing['free_tier'],
            'cost_per_1000': pricing['cost_per_1000'],
            'cost_usd': round(cost_usd, 6),
            'cost_twd': round(cost_twd, 4),
            'note': pricing['note']
        }

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int = 0
    ) -> Dict[str, Any]:
        """預估 Gemini API 調用成本

        Args:
            model: 模型名稱
            input_tokens: 輸入 token 數
            output_tokens: 輸出 token 數

        Returns:
            成本資訊字典
        """
        if model not in self.GEMINI_PRICING:
            model = 'gemini-2.5-flash'  # 預設使用 Flash

        pricing = self.GEMINI_PRICING[model]

        # 計算 input 成本
        if 'threshold' in pricing:
            # 階梯式定價
            if input_tokens <= pricing['threshold']:
                input_cost_usd = input_tokens * pricing['input_low'] / 1_000_000
                output_cost_usd = output_tokens * pricing['output_low'] / 1_000_000
            else:
                input_cost_usd = input_tokens * pricing['input_high'] / 1_000_000
                output_cost_usd = output_tokens * pricing['output_high'] / 1_000_000
        else:
            # 固定定價
            input_cost_usd = input_tokens * pricing['input'] / 1_000_000
            output_cost_usd = output_tokens * pricing['output'] / 1_000_000

        total_usd = input_cost_usd + output_cost_usd
        total_twd = total_usd * self.exchange_rate

        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'cost_usd': round(total_usd, 6),
            'cost_twd': round(total_twd, 4),
            'input_cost_usd': round(input_cost_usd, 6),
            'output_cost_usd': round(output_cost_usd, 6),
        }

    def display_estimate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int = 0,
        description: str = ""
    ) -> None:
        """顯示預估成本

        Args:
            model: 模型名稱
            input_tokens: 輸入 token 數
            output_tokens: 輸出 token 數
            description: 操作描述
        """
        cost_info = self.estimate_cost(model, input_tokens, output_tokens)

        print("\n" + "=" * 60)
        print("💰 API 成本預估")
        if description:
            print(f"📝 操作：{description}")
        print("-" * 60)
        print(f"🤖 模型：{cost_info['model']}")
        print(f"📊 Token：{cost_info['input_tokens']:,} (input) + {cost_info['output_tokens']:,} (output) = {cost_info['total_tokens']:,}")
        print(f"💵 成本：${cost_info['cost_usd']:.6f} USD ≈ NT${cost_info['cost_twd']:.4f} TWD")
        print("=" * 60 + "\n")

    def display_pricing_table(self) -> None:
        """顯示完整定價表"""
        print("\n" + "=" * 80)
        print("💰 Gemini API 定價表（2025年1月）")
        print("=" * 80)
        print(f"匯率：1 USD = {self.exchange_rate} TWD")
        print("-" * 80)

        for model, pricing in self.PRICING.items():
            print(f"\n🤖 {model}")

            if 'threshold' in pricing:
                # 階梯式定價
                print(f"  Input  (≤{pricing['threshold']:,} tokens): ${pricing['input_low']}/1M tokens "
                      f"(NT${pricing['input_low'] * self.exchange_rate:.2f}/1M tokens)")
                print(f"  Input  (>{pricing['threshold']:,} tokens): ${pricing['input_high']}/1M tokens "
                      f"(NT${pricing['input_high'] * self.exchange_rate:.2f}/1M tokens)")
                print(f"  Output (≤{pricing['threshold']:,} tokens): ${pricing['output_low']}/1M tokens "
                      f"(NT${pricing['output_low'] * self.exchange_rate:.2f}/1M tokens)")
                print(f"  Output (>{pricing['threshold']:,} tokens): ${pricing['output_high']}/1M tokens "
                      f"(NT${pricing['output_high'] * self.exchange_rate:.2f}/1M tokens)")
            else:
                # 固定定價
                print(f"  Input:  ${pricing['input']}/1M tokens "
                      f"(NT${pricing['input'] * self.exchange_rate:.2f}/1M tokens)")
                print(f"  Output: ${pricing['output']}/1M tokens "
                      f"(NT${pricing['output'] * self.exchange_rate:.2f}/1M tokens)")

        # 搜尋 API 定價
        print("\n🔍 搜尋 API 定價")
        print("-" * 80)

        for engine, pricing in self.SEARCH_API_PRICING.items():
            engine_display = {
                'google_custom_search': 'Google Custom Search',
                'brave_search': 'Brave Search',
                'duckduckgo': 'DuckDuckGo'
            }.get(engine, engine)

            print(f"\n🔎 {engine_display}")

            if pricing['cost_per_1000'] == 0:
                print(f"  價格：✅ 完全免費")
            else:
                print(f"  價格：${pricing['cost_per_1000']}/1000 queries "
                      f"(NT${pricing['cost_per_1000'] * self.exchange_rate:.2f}/1000 queries)")

            if pricing['free_tier'] != float('inf'):
                print(f"  免費額度：{pricing['free_tier']:,} queries")

            print(f"  說明：{pricing['note']}")

        print("\n" + "=" * 80)
        print("💡 提示：")
        print("  - Gemini API 費用以 Google Cloud 帳單為準")
        print("  - 搜尋 API 建議優先使用 DuckDuckGo（免費）")
        print("  - 付費搜尋 API 需在免費額度用完後才計費")
        print("=" * 80 + "\n")

    def display_usage_note(self) -> None:
        """顯示 API 使用說明"""
        print("\n" + "=" * 80)
        print("📌 CodeGemini API 使用說明")
        print("=" * 80)
        print("""
當前實作的功能模組：

1. ✅ Background Shells（背景 Shell 管理）
   - 功能：本地 Shell 進程管理
   - API 調用：❌ 無（純本地工具）

2. ✅ Todo Tracking（任務追蹤系統）
   - 功能：本地任務狀態追蹤
   - API 調用：❌ 無（純本地工具）

3. ✅ Interactive Q&A（互動式問答）
   - 功能：本地用戶互動
   - API 調用：❌ 無（純本地工具）

🔔 重要提示：
   這三個功能本身**不會直接調用 Gemini API**。

   但如果它們被整合到 Agent Mode 流程中使用時：
   - Agent 規劃任務 → 會調用 API
   - Agent 詢問用戶 → 會調用 API
   - Agent 執行背景任務 → 會調用 API

   此時的 API 成本來自 **Agent Mode 本身**，而非工具本身。

💰 如何控制成本：
   1. 使用較便宜的模型（如 gemini-2.5-flash）
   2. 限制輸出 token 數（max_output_tokens）
   3. 使用 token caching 減少重複輸入
   4. 定期檢查 Google Cloud 帳單
        """)
        print("=" * 80 + "\n")

# ============================================================================
# Checkpointing System 模組
# ============================================================================

class CheckpointManager:
    """Checkpoint 管理器

    功能：
    - 建立 checkpoint（保存當前程式碼狀態）
    - 列出所有 checkpoints
    - 恢復到指定 checkpoint
    - 回退 N 個 checkpoint（rewind）

    參考 Claude Code 的 Checkpointing System
    完全本地執行，無 API 成本
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        if checkpoint_dir is None:
            self.checkpoint_dir = Path.cwd() / ".checkpoints"
        else:
            self.checkpoint_dir = Path(checkpoint_dir)

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: List[Checkpoint] = []
        self._load_checkpoints()
        logger.info("CheckpointManager 已初始化")

    def _load_checkpoints(self):
        """載入所有 checkpoints"""
        metadata_file = self.checkpoint_dir / "checkpoints.json"
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    data = json.load(f)
                    for cp_data in data:
                        checkpoint = Checkpoint(
                            checkpoint_id=cp_data['checkpoint_id'],
                            description=cp_data['description'],
                            created_at=datetime.fromisoformat(cp_data['created_at']),
                            files_snapshot=cp_data['files_snapshot'],
                            metadata=cp_data.get('metadata', {})
                        )
                        self.checkpoints.append(checkpoint)
            except Exception as e:
                logger.error(f"✗ 載入 checkpoints 失敗: {e}")

    def _save_checkpoints(self):
        """保存 checkpoints 元數據"""
        metadata_file = self.checkpoint_dir / "checkpoints.json"
        try:
            data = [
                {
                    'checkpoint_id': cp.checkpoint_id,
                    'description': cp.description,
                    'created_at': cp.created_at.isoformat(),
                    'files_snapshot': cp.files_snapshot,
                    'metadata': cp.metadata
                }
                for cp in self.checkpoints
            ]
            with open(metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"✗ 保存 checkpoints 失敗: {e}")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """計算檔案 hash"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"✗ 計算 hash 失敗 ({file_path}): {e}")
            return ""

    def _snapshot_files(self, paths: List[str]) -> Dict[str, str]:
        """對指定檔案建立 snapshot"""
        snapshot = {}
        for path_str in paths:
            path = Path(path_str)
            if path.exists() and path.is_file():
                snapshot[path_str] = self._calculate_file_hash(path)
        return snapshot

    def _backup_files(self, checkpoint_id: str, paths: List[str]):
        """備份檔案到 checkpoint 目錄"""
        backup_dir = self.checkpoint_dir / checkpoint_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        for path_str in paths:
            src_path = Path(path_str)
            if src_path.exists() and src_path.is_file():
                # 保持相對路徑結構
                rel_path = src_path.relative_to(Path.cwd()) if src_path.is_absolute() else src_path
                dst_path = backup_dir / rel_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)

    def create_checkpoint(
        self,
        description: str,
        files: Optional[List[str]] = None
    ) -> str:
        """建立 checkpoint

        Args:
            description: Checkpoint 描述
            files: 要備份的檔案列表（None = 當前目錄所有檔案）

        Returns:
            Checkpoint ID
        """
        # 生成 checkpoint ID
        timestamp = int(time.time() * 1000)
        checkpoint_id = f"cp_{timestamp}"

        # 如果未指定檔案，掃描當前目錄
        if files is None:
            files = [str(p) for p in Path.cwd().rglob("*")
                    if p.is_file() and not str(p).startswith('.')]

        # 建立 snapshot
        files_snapshot = self._snapshot_files(files)

        # 備份檔案
        self._backup_files(checkpoint_id, files)

        # 建立 checkpoint
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            description=description,
            created_at=datetime.now(),
            files_snapshot=files_snapshot
        )

        self.checkpoints.append(checkpoint)
        self._save_checkpoints()

        logger.info(f"✓ Checkpoint 已建立: {checkpoint_id}")
        logger.info(f"  描述: {description}")
        logger.info(f"  檔案數: {len(files_snapshot)}")

        return checkpoint_id

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有 checkpoints

        Returns:
            Checkpoints 列表
        """
        return [
            {
                'checkpoint_id': cp.checkpoint_id,
                'description': cp.description,
                'created_at': cp.created_at.isoformat(),
                'files_count': len(cp.files_snapshot)
            }
            for cp in self.checkpoints
        ]

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """恢復到指定 checkpoint

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            是否成功
        """
        # 查找 checkpoint
        checkpoint = None
        for cp in self.checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                checkpoint = cp
                break

        if not checkpoint:
            logger.error(f"Checkpoint 不存在: {checkpoint_id}")
            return False

        # 恢復檔案
        backup_dir = self.checkpoint_dir / checkpoint_id
        if not backup_dir.exists():
            logger.error(f"Checkpoint 備份目錄不存在: {backup_dir}")
            return False

        try:
            restored_count = 0
            for file_path in checkpoint.files_snapshot.keys():
                src_path = backup_dir / Path(file_path).relative_to(Path.cwd())
                dst_path = Path(file_path)

                if src_path.exists():
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    restored_count += 1

            logger.info(f"✓ Checkpoint 已恢復: {checkpoint_id}")
            logger.info(f"  恢復檔案數: {restored_count}")
            return True

        except Exception as e:
            logger.error(f"✗ 恢復 checkpoint 失敗: {e}")
            return False

    def rewind(self, steps: int = 1) -> bool:
        """回退 N 個 checkpoint

        Args:
            steps: 回退步數（預設 1）

        Returns:
            是否成功
        """
        if steps <= 0:
            logger.error("回退步數必須大於 0")
            return False

        if len(self.checkpoints) < steps:
            logger.error(f"Checkpoints 數量不足（現有 {len(self.checkpoints)}）")
            return False

        # 獲取目標 checkpoint
        target_checkpoint = self.checkpoints[-(steps + 1)]

        logger.info(f"回退 {steps} 步到: {target_checkpoint.checkpoint_id}")
        return self.restore_checkpoint(target_checkpoint.checkpoint_id)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """刪除 checkpoint

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            是否成功
        """
        # 查找並刪除 checkpoint
        for i, cp in enumerate(self.checkpoints):
            if cp.checkpoint_id == checkpoint_id:
                # 刪除備份目錄
                backup_dir = self.checkpoint_dir / checkpoint_id
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)

                # 從列表中移除
                self.checkpoints.pop(i)
                self._save_checkpoints()

                logger.info(f"✓ Checkpoint 已刪除: {checkpoint_id}")
                return True

        logger.error(f"Checkpoint 不存在: {checkpoint_id}")
        return False

    def cleanup_old_checkpoints(self, keep_count: int = 10):
        """清理舊的 checkpoints

        Args:
            keep_count: 保留的 checkpoint 數量
        """
        if len(self.checkpoints) <= keep_count:
            return

        # 刪除最舊的 checkpoints
        to_delete = self.checkpoints[:-(keep_count)]
        for cp in to_delete:
            self.delete_checkpoint(cp.checkpoint_id)

        logger.info(f"✓ 已清理 {len(to_delete)} 個舊 checkpoints")

# ============================================================================
# Custom Slash Commands（自訂斜線指令）
# ============================================================================

class SlashCommand:
    """Slash Command 資訊"""
    def __init__(self, name: str, content: str, file_path: Path):
        self.name = name
        self.content = content
        self.file_path = file_path
        self.metadata = self._parse_metadata()

    def _parse_metadata(self) -> Dict[str, str]:
        """解析 markdown 中的 metadata（YAML front matter）"""
        metadata = {}
        lines = self.content.split('\n')

        if lines and lines[0].strip() == '---':
            # 有 YAML front matter
            end_idx = None
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    end_idx = i
                    break

            if end_idx:
                # 解析 YAML（簡單版本，只支援 key: value）
                for line in lines[1:end_idx]:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()

        return metadata

    def get_description(self) -> str:
        """取得指令描述"""
        return self.metadata.get('description', 'No description')

    def get_prompt(self) -> str:
        """取得指令提示詞（移除 metadata）"""
        lines = self.content.split('\n')

        if lines and lines[0].strip() == '---':
            # 跳過 YAML front matter
            end_idx = None
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    end_idx = i + 1
                    break

            if end_idx:
                return '\n'.join(lines[end_idx:]).strip()

        return self.content.strip()


class SlashCommandManager:
    """Slash Command 管理器

    功能：
    - 載入自訂 slash commands（從 .gemini/commands/ 目錄）
    - 執行 slash commands
    - 列出可用 commands

    參考 Claude Code 的 SlashCommand 系統
    完全本地執行，無 API 成本

    目錄結構：
    .gemini/
    └── commands/
        ├── review-pr.md      # /review-pr 指令
        ├── fix-bugs.md       # /fix-bugs 指令
        └── optimize.md       # /optimize 指令
    """

    def __init__(self, commands_dir: Optional[Path] = None):
        """初始化 Slash Command 管理器

        Args:
            commands_dir: commands 目錄路徑，預設為 .gemini/commands/
        """
        if commands_dir is None:
            # 預設使用 ~/.gemini/commands/
            self.commands_dir = Path.home() / ".gemini" / "commands"
        else:
            self.commands_dir = Path(commands_dir)

        self.commands: Dict[str, SlashCommand] = {}
        self._load_commands()

        logger.info(f"SlashCommandManager 已初始化")
        logger.info(f"Commands 目錄: {self.commands_dir}")

    def _load_commands(self):
        """載入所有 slash commands"""
        if not self.commands_dir.exists():
            logger.warning(f"Commands 目錄不存在: {self.commands_dir}")
            logger.info(f"提示：建立目錄並新增 .md 檔案來定義自訂指令")
            return

        # 尋找所有 .md 檔案
        md_files = list(self.commands_dir.glob("*.md"))

        for md_file in md_files:
            try:
                command_name = md_file.stem  # 檔名（不含副檔名）
                content = md_file.read_text(encoding='utf-8')

                command = SlashCommand(
                    name=command_name,
                    content=content,
                    file_path=md_file
                )

                self.commands[command_name] = command
                logger.debug(f"載入指令: /{command_name}")

            except Exception as e:
                logger.error(f"載入指令失敗 {md_file}: {e}")

        logger.info(f"✓ 已載入 {len(self.commands)} 個 slash commands")

    def list_commands(self) -> List[Dict[str, str]]:
        """列出所有可用的 slash commands

        Returns:
            指令列表，每個項目包含 name, description, file_path
        """
        commands_list = []

        for name, cmd in sorted(self.commands.items()):
            commands_list.append({
                'name': f"/{name}",
                'description': cmd.get_description(),
                'file_path': str(cmd.file_path)
            })

        return commands_list

    def get_command(self, command_name: str) -> Optional[SlashCommand]:
        """取得指定的 slash command

        Args:
            command_name: 指令名稱（可含或不含 / 前綴）

        Returns:
            SlashCommand 物件，若不存在則回傳 None
        """
        # 移除 / 前綴
        if command_name.startswith('/'):
            command_name = command_name[1:]

        return self.commands.get(command_name)

    def execute_command(self, command_name: str, args: Optional[str] = None) -> Optional[str]:
        """執行 slash command

        Args:
            command_name: 指令名稱
            args: 指令參數（可選）

        Returns:
            指令的提示詞（prompt），準備送給 LLM
        """
        cmd = self.get_command(command_name)

        if cmd is None:
            logger.error(f"指令不存在: /{command_name}")
            return None

        prompt = cmd.get_prompt()

        # 如果有參數，將參數附加到提示詞
        if args:
            prompt = f"{prompt}\n\n參數: {args}"

        logger.info(f"✓ 執行指令: /{command_name}")
        return prompt

    def reload_commands(self):
        """重新載入所有 commands"""
        self.commands.clear()
        self._load_commands()
        logger.info("✓ 已重新載入所有 slash commands")

    def create_command_template(self, command_name: str, description: str, prompt: str) -> Path:
        """建立新的 slash command 範本

        Args:
            command_name: 指令名稱
            description: 指令描述
            prompt: 指令提示詞

        Returns:
            建立的檔案路徑
        """
        # 建立 commands 目錄（如果不存在）
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        # 建立 markdown 檔案
        file_path = self.commands_dir / f"{command_name}.md"

        content = f"""---
description: {description}
---

{prompt}
"""

        file_path.write_text(content, encoding='utf-8')

        # 重新載入 commands
        self.reload_commands()

        logger.info(f"✓ 已建立指令: /{command_name}")
        logger.info(f"  檔案: {file_path}")

        return file_path

# ============================================================================
# Auto Model Selection（自動模型選擇）
# ============================================================================

class ModelProfile:
    """模型特性檔案"""
    def __init__(self, name: str, cost_per_1m_input: float, cost_per_1m_output: float,
                 speed: str, context_window: int, strengths: List[str]):
        self.name = name
        self.cost_per_1m_input = cost_per_1m_input  # USD
        self.cost_per_1m_output = cost_per_1m_output  # USD
        self.speed = speed  # "fast", "medium", "slow"
        self.context_window = context_window
        self.strengths = strengths  # ["code", "reasoning", "creative", etc.]


class AutoModelSelector:
    """自動模型選擇器

    功能：
    - 根據任務類型自動選擇最合適的 Gemini 模型
    - 考慮成本、速度、能力的平衡
    - 支援自訂選擇策略

    參考 Claude Code 與 Cursor AI 的自動模型選擇
    完全本地邏輯，無 API 成本

    策略：
    - cost_optimized: 優先選擇低成本模型
    - speed_optimized: 優先選擇快速模型
    - quality_optimized: 優先選擇高品質模型
    - balanced: 平衡成本、速度、品質
    """

    def __init__(self, strategy: str = "balanced"):
        """初始化自動模型選擇器

        Args:
            strategy: 選擇策略 (cost_optimized, speed_optimized, quality_optimized, balanced)
        """
        self.strategy = strategy
        self.models = self._init_models()
        logger.info(f"AutoModelSelector 已初始化（策略: {strategy}）")

    def _init_models(self) -> Dict[str, ModelProfile]:
        """初始化模型資料"""
        return {
            "gemini-2.0-flash-exp": ModelProfile(
                name="gemini-2.0-flash-exp",
                cost_per_1m_input=0.10,
                cost_per_1m_output=0.40,
                speed="fast",
                context_window=1000000,
                strengths=["code", "speed", "general"]
            ),
            "gemini-2.5-flash": ModelProfile(
                name="gemini-2.5-flash",
                cost_per_1m_input=0.15625,
                cost_per_1m_output=0.625,
                speed="fast",
                context_window=1000000,
                strengths=["code", "reasoning", "general"]
            ),
            "gemini-2.5-pro": ModelProfile(
                name="gemini-2.5-pro",
                cost_per_1m_input=1.25,  # ≤200K tokens
                cost_per_1m_output=5.00,
                speed="medium",
                context_window=2000000,
                strengths=["reasoning", "complex", "quality"]
            ),
            "gemini-1.5-flash": ModelProfile(
                name="gemini-1.5-flash",
                cost_per_1m_input=0.075,
                cost_per_1m_output=0.30,
                speed="fast",
                context_window=1000000,
                strengths=["speed", "general"]
            ),
            "gemini-1.5-pro": ModelProfile(
                name="gemini-1.5-pro",
                cost_per_1m_input=1.25,
                cost_per_1m_output=5.00,
                speed="slow",
                context_window=2000000,
                strengths=["quality", "reasoning"]
            ),
        }

    def select_model(self, task_type: str, estimated_tokens: Optional[int] = None) -> str:
        """根據任務類型選擇最佳模型

        Args:
            task_type: 任務類型 (code, reasoning, creative, chat, simple, complex)
            estimated_tokens: 預估的 token 數量（用於成本計算）

        Returns:
            推薦的模型名稱
        """
        if self.strategy == "cost_optimized":
            return self._select_by_cost(task_type)
        elif self.strategy == "speed_optimized":
            return self._select_by_speed(task_type)
        elif self.strategy == "quality_optimized":
            return self._select_by_quality(task_type)
        else:  # balanced
            return self._select_balanced(task_type, estimated_tokens)

    def _select_by_cost(self, task_type: str) -> str:
        """成本優先策略"""
        # 總是選最便宜的模型
        if task_type in ["simple", "chat"]:
            return "gemini-1.5-flash"
        elif task_type == "code":
            return "gemini-2.0-flash-exp"
        else:
            return "gemini-2.5-flash"

    def _select_by_speed(self, task_type: str) -> str:
        """速度優先策略"""
        # 選擇 fast 模型
        if task_type == "code":
            return "gemini-2.0-flash-exp"
        else:
            return "gemini-2.5-flash"

    def _select_by_quality(self, task_type: str) -> str:
        """品質優先策略"""
        # 複雜任務用 Pro，簡單任務用 Flash
        if task_type in ["reasoning", "complex"]:
            return "gemini-2.5-pro"
        elif task_type == "code":
            return "gemini-2.5-flash"
        else:
            return "gemini-2.5-flash"

    def _select_balanced(self, task_type: str, estimated_tokens: Optional[int]) -> str:
        """平衡策略"""
        # 根據任務類型平衡選擇
        task_mapping = {
            "simple": "gemini-1.5-flash",      # 簡單任務用最便宜的
            "chat": "gemini-2.0-flash-exp",    # 聊天用 2.0 Flash
            "code": "gemini-2.5-flash",        # 程式碼用 2.5 Flash
            "reasoning": "gemini-2.5-flash",   # 推理用 2.5 Flash（平衡）
            "complex": "gemini-2.5-pro",       # 複雜任務用 Pro
            "creative": "gemini-2.5-flash",    # 創意任務用 2.5 Flash
        }

        return task_mapping.get(task_type, "gemini-2.5-flash")

    def get_model_info(self, model_name: str) -> Optional[ModelProfile]:
        """取得模型資訊

        Args:
            model_name: 模型名稱

        Returns:
            ModelProfile 或 None
        """
        return self.models.get(model_name)

    def estimate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """預估成本

        Args:
            model_name: 模型名稱
            input_tokens: 輸入 token 數
            output_tokens: 輸出 token 數

        Returns:
            包含 USD 和 TWD 成本的字典
        """
        model = self.get_model_info(model_name)
        if not model:
            return {"usd": 0, "twd": 0}

        input_cost = (input_tokens / 1_000_000) * model.cost_per_1m_input
        output_cost = (output_tokens / 1_000_000) * model.cost_per_1m_output
        total_usd = input_cost + output_cost
        total_twd = total_usd * USD_TO_TWD

        return {
            "usd": round(total_usd, 6),
            "twd": round(total_twd, 4)
        }

    def compare_models(self, task_type: str, input_tokens: int = 1000, output_tokens: int = 500):
        """比較不同模型的成本與特性

        Args:
            task_type: 任務類型
            input_tokens: 預估輸入 token 數
            output_tokens: 預估輸出 token 數
        """
        print(f"\n任務類型: {task_type}")
        print(f"預估 Tokens: {input_tokens:,} input + {output_tokens:,} output\n")
        print(f"{'模型':<25} {'速度':<10} {'成本 (USD)':<15} {'成本 (TWD)':<15} {'推薦'}")
        print("-" * 80)

        recommended = self.select_model(task_type)

        for name, model in sorted(self.models.items(), key=lambda x: x[1].cost_per_1m_input):
            cost = self.estimate_cost(name, input_tokens, output_tokens)
            is_recommended = "⭐" if name == recommended else ""

            print(f"{name:<25} {model.speed:<10} ${cost['usd']:<14.6f} NT${cost['twd']:<14.2f} {is_recommended}")

        print(f"\n✓ 推薦模型: {recommended}")
        print(f"  策略: {self.strategy}")

    def set_strategy(self, strategy: str):
        """更改選擇策略

        Args:
            strategy: 新策略 (cost_optimized, speed_optimized, quality_optimized, balanced)
        """
        valid_strategies = ["cost_optimized", "speed_optimized", "quality_optimized", "balanced"]
        if strategy not in valid_strategies:
            logger.error(f"無效的策略: {strategy}，可用策略: {valid_strategies}")
            return

        self.strategy = strategy
        logger.info(f"✓ 已切換至策略: {strategy}")

# ============================================================================
# 主要 CodeGemini 類別
# ============================================================================

class CodeGemini:
    """CodeGemini 主要類別 - Google Gemini CLI 管理工具"""

    def __init__(self):
        self.env_checker = EnvironmentChecker()
        self.cli_manager = GeminiCLIManager()
        self.api_key_manager = APIKeyManager()
        self.mcp_manager = MCPConfigManager()
        self.template_manager = TemplateManager()

        # 新增功能模組（v1.1.0）
        self.shell_manager = BackgroundShellManager()
        self.todo_tracker = TodoTracker()
        self.interactive_qa = InteractiveQA()
        self.pricing = PricingDisplay()

        # 新增功能模組（v1.2.0）- 預設不載入，使用者選用
        self.checkpoint_manager = None
        self.codebase_embedding = None
        self.slash_commands = None
        self.auto_model_selector = None
        self.thinking_mode = None

        logger.info("CodeGemini 已初始化")
        logger.info("💡 提示：v1.2.0 新功能需手動啟用，請使用 enable_*() 方法")

    def enable_checkpointing(self, checkpoint_dir: Optional[Path] = None):
        """啟用 Checkpointing System（可選功能）"""
        if self.checkpoint_manager is None:
            self.checkpoint_manager = CheckpointManager(checkpoint_dir)
            logger.info("✓ Checkpointing System 已啟用")
            logger.info("  使用 disable_checkpointing() 可卸載")
        return self.checkpoint_manager

    def disable_checkpointing(self):
        """卸載 Checkpointing System"""
        if self.checkpoint_manager is not None:
            self.checkpoint_manager = None
            logger.info("✓ Checkpointing System 已卸載")

    def enable_slash_commands(self, commands_dir: Optional[Path] = None):
        """啟用 Custom Slash Commands（可選功能）"""
        if self.slash_commands is None:
            self.slash_commands = SlashCommandManager(commands_dir)
            logger.info("✓ Custom Slash Commands 已啟用")
            logger.info("  使用 disable_slash_commands() 可卸載")
        return self.slash_commands

    def disable_slash_commands(self):
        """卸載 Custom Slash Commands"""
        if self.slash_commands is not None:
            self.slash_commands = None
            logger.info("✓ Custom Slash Commands 已卸載")

    def enable_auto_model_selector(self, strategy: str = "balanced"):
        """啟用 Auto Model Selection（可選功能）"""
        if self.auto_model_selector is None:
            self.auto_model_selector = AutoModelSelector(strategy)
            logger.info("✓ Auto Model Selection 已啟用")
            logger.info("  使用 disable_auto_model_selector() 可卸載")
        return self.auto_model_selector

    def disable_auto_model_selector(self):
        """卸載 Auto Model Selection"""
        if self.auto_model_selector is not None:
            self.auto_model_selector = None
            logger.info("✓ Auto Model Selection 已卸載")

    def enable_codebase_embedding(
        self,
        vector_db_path: str = ".embeddings",
        api_key: Optional[str] = None,
        collection_name: str = "codebase",
        orthogonal_mode: bool = False,
        similarity_threshold: float = 0.85
    ):
        """啟用 Codebase Embedding（可選功能）

        Args:
            vector_db_path: 向量資料庫路徑
            api_key: Gemini API Key
            collection_name: Collection 名稱
            orthogonal_mode: 是否啟用正交模式（自動去重，保持內容線性獨立）
            similarity_threshold: 正交模式下的相似度閾值（預設 0.85）

        Returns:
            CodebaseEmbedding 實例
        """
        if self.codebase_embedding is None:
            try:
                # 動態導入模組
                import sys
                codebase_embedding_path = Path(__file__).parent / "CodeGemini"
                sys.path.insert(0, str(codebase_embedding_path))

                from codebase_embedding import CodebaseEmbedding

                self.codebase_embedding = CodebaseEmbedding(
                    vector_db_path=vector_db_path,
                    api_key=api_key or self.api_key_manager.get_api_key(),
                    collection_name=collection_name,
                    orthogonal_mode=orthogonal_mode,
                    similarity_threshold=similarity_threshold
                )
                logger.info("✓ Codebase Embedding 已啟用")
                if orthogonal_mode:
                    logger.info(f"  正交模式已啟用（相似度閾值: {similarity_threshold}）")
                logger.info("  使用 disable_codebase_embedding() 可卸載")

            except ImportError as e:
                logger.error(f"✗ 無法啟用 Codebase Embedding: {e}")
                logger.info("  請確認 numpy 已安裝")
                return None

        return self.codebase_embedding

    def disable_codebase_embedding(self):
        """卸載 Codebase Embedding"""
        if self.codebase_embedding is not None:
            self.codebase_embedding = None
            logger.info("✓ Codebase Embedding 已卸載")

    def check_environment(self) -> EnvironmentCheck:
        """檢查環境"""
        return self.env_checker.run_full_check()

    def print_status(self):
        """顯示狀態"""
        env_check = self.check_environment()
        cli_info = self.cli_manager.get_status()

        print("\n" + "="*60)
        print("  CodeGemini - Google Gemini CLI 管理工具")
        print("="*60)

        print("\n📊 環境狀態:")
        print(f"  作業系統: {env_check.os_type} {env_check.os_version}")
        print(f"  架構: {env_check.arch}")
        print(f"  Node.js: {'✓' if env_check.node_installed else '✗'} {env_check.node_version or 'N/A'}")
        print(f"  npm: {'✓' if env_check.npm_installed else '✗'} {env_check.npm_version or 'N/A'}")

        print("\n🔧 Gemini CLI:")
        print(f"  安裝狀態: {'✓ 已安裝' if cli_info.installed else '✗ 未安裝'}")
        print(f"  版本: {cli_info.version or 'N/A'}")
        print(f"  路徑: {cli_info.install_path or 'N/A'}")

        print("\n🔑 API Key:")
        api_key = self.api_key_manager.get_api_key()
        if api_key:
            masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
            print(f"  狀態: ✓ 已配置")
            print(f"  金鑰: {masked_key}")
        else:
            print(f"  狀態: ✗ 未配置")

        if env_check.warnings:
            print("\n⚠️  警告:")
            for warning in env_check.warnings:
                print(f"  - {warning}")

        if env_check.errors:
            print("\n✗ 錯誤:")
            for error in env_check.errors:
                print(f"  - {error}")

        print("\n" + "="*60)

        return env_check.passed

# ============================================================================
# CLI 介面
# ============================================================================

def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(
        description="CodeGemini - Google Gemini CLI 管理工具"
    )
    parser.add_argument(
        "command",
        choices=["status", "check", "install", "update", "uninstall", "setup-api-key", "pricing", "pricing-note", "slash-commands", "create-command", "select-model", "compare-models"],
        help="要執行的指令"
    )
    parser.add_argument(
        "--name",
        help="指令名稱（用於 create-command）"
    )
    parser.add_argument(
        "--description",
        help="指令描述（用於 create-command）"
    )
    parser.add_argument(
        "--prompt",
        help="指令提示詞（用於 create-command）"
    )
    parser.add_argument(
        "--task-type",
        choices=["simple", "chat", "code", "reasoning", "complex", "creative"],
        help="任務類型（用於 select-model）"
    )
    parser.add_argument(
        "--strategy",
        choices=["cost_optimized", "speed_optimized", "quality_optimized", "balanced"],
        default="balanced",
        help="模型選擇策略（用於 select-model, compare-models）"
    )
    parser.add_argument(
        "--input-tokens",
        type=int,
        default=1000,
        help="預估輸入 token 數（用於 compare-models）"
    )
    parser.add_argument(
        "--output-tokens",
        type=int,
        default=500,
        help="預估輸出 token 數（用於 compare-models）"
    )

    args = parser.parse_args()

    cg = CodeGemini()

    if args.command == "status":
        cg.print_status()

    elif args.command == "check":
        env_check = cg.check_environment()
        if env_check.passed:
            print("✓ 環境檢查通過")
            sys.exit(0)
        else:
            print("✗ 環境檢查失敗")
            sys.exit(1)

    elif args.command == "install":
        if cg.cli_manager.install():
            print("✓ 安裝成功")
            sys.exit(0)
        else:
            print("✗ 安裝失敗")
            sys.exit(1)

    elif args.command == "update":
        if cg.cli_manager.update():
            print("✓ 更新成功")
            sys.exit(0)
        else:
            print("✗ 更新失敗")
            sys.exit(1)

    elif args.command == "uninstall":
        if cg.cli_manager.uninstall():
            print("✓ 卸載成功")
            sys.exit(0)
        else:
            print("✗ 卸載失敗")
            sys.exit(1)

    elif args.command == "setup-api-key":
        if cg.api_key_manager.setup_interactive():
            print("✓ API Key 設定完成")
            sys.exit(0)
        else:
            print("✗ API Key 設定失敗")
            sys.exit(1)

    elif args.command == "pricing":
        cg.pricing.display_pricing_table()
        sys.exit(0)

    elif args.command == "pricing-note":
        cg.pricing.display_usage_note()
        sys.exit(0)

    elif args.command == "slash-commands":
        # 列出所有 slash commands
        cg.enable_slash_commands()
        commands = cg.slash_commands.list_commands()

        if not commands:
            print("目前沒有自訂的 slash commands")
            print(f"\n提示：在 {cg.slash_commands.commands_dir} 建立 .md 檔案來定義指令")
            sys.exit(0)

        print(f"\n可用的 Slash Commands ({len(commands)} 個)：\n")
        for cmd in commands:
            print(f"  {cmd['name']:<20} - {cmd['description']}")
            print(f"  {'':20}   檔案: {cmd['file_path']}\n")

        sys.exit(0)

    elif args.command == "create-command":
        # 建立新的 slash command
        if not args.name or not args.description or not args.prompt:
            print("錯誤：建立指令需要 --name、--description 和 --prompt 參數")
            sys.exit(1)

        cg.enable_slash_commands()
        file_path = cg.slash_commands.create_command_template(
            command_name=args.name,
            description=args.description,
            prompt=args.prompt
        )

        print(f"✓ 已建立指令: /{args.name}")
        print(f"  檔案: {file_path}")
        print(f"\n使用方式：")
        print(f"  cg.enable_slash_commands()")
        print(f"  prompt = cg.slash_commands.execute_command('{args.name}')")
        sys.exit(0)

    elif args.command == "select-model":
        # 選擇最佳模型
        if not args.task_type:
            print("錯誤：請使用 --task-type 指定任務類型")
            sys.exit(1)

        cg.enable_auto_model_selector(strategy=args.strategy)
        model = cg.auto_model_selector.select_model(args.task_type)

        print(f"\n任務類型: {args.task_type}")
        print(f"選擇策略: {args.strategy}")
        print(f"\n✓ 推薦模型: {model}")

        # 顯示模型資訊
        model_info = cg.auto_model_selector.get_model_info(model)
        if model_info:
            print(f"\n模型資訊：")
            print(f"  速度: {model_info.speed}")
            print(f"  Context Window: {model_info.context_window:,} tokens")
            print(f"  成本: ${model_info.cost_per_1m_input}/1M (input), ${model_info.cost_per_1m_output}/1M (output)")
            print(f"  優勢: {', '.join(model_info.strengths)}")

        sys.exit(0)

    elif args.command == "compare-models":
        # 比較模型
        if not args.task_type:
            print("錯誤：請使用 --task-type 指定任務類型")
            sys.exit(1)

        cg.enable_auto_model_selector(strategy=args.strategy)
        cg.auto_model_selector.compare_models(
            task_type=args.task_type,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens
        )
        sys.exit(0)

if __name__ == "__main__":
    main()
