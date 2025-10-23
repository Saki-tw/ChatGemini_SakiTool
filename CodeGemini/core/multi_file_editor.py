#!/usr/bin/env python3
"""
CodeGemini Multi-File Editor Module
多檔案編輯器 - 批次檔案操作

此模組負責：
1. 批次編輯多個檔案
2. 驗證變更
3. 原子性操作（全部成功或全部回滾）
4. Git 整合
"""
import os
import shutil
import tempfile
import subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax

from .task_planner import FileChange

console = Console()


class EditStatus(Enum):
    """編輯狀態"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class EditResult:
    """編輯結果"""
    edit_id: str                              # 編輯 ID
    status: EditStatus                        # 狀態
    success_count: int = 0                    # 成功檔案數
    failed_count: int = 0                     # 失敗檔案數
    error_messages: List[str] = field(default_factory=list)
    backup_id: Optional[str] = None           # 備份 ID


@dataclass
class ValidationResult:
    """驗證結果"""
    is_valid: bool                            # 是否有效
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class MultiFileEditor:
    """多檔案編輯器"""

    def __init__(
        self,
        project_path: str,
        auto_backup: bool = True,
        git_integration: bool = True
    ):
        """
        初始化多檔案編輯器

        Args:
            project_path: 專案路徑
            auto_backup: 是否自動備份
            git_integration: 是否啟用 Git 整合
        """
        self.project_path = os.path.abspath(project_path)
        self.auto_backup = auto_backup
        self.git_integration = git_integration

        # 備份目錄
        self.backup_dir = os.path.join(
            tempfile.gettempdir(),
            f"codegemini_backups_{int(time.time())}"
        )

        # 檢查 Git
        self._has_git = self._check_git()

    def _check_git(self) -> bool:
        """檢查是否為 Git 倉庫"""
        if not self.git_integration:
            return False

        git_dir = os.path.join(self.project_path, '.git')
        return os.path.isdir(git_dir)

    def batch_edit(
        self,
        changes: List[FileChange],
        create_commit: bool = False,
        commit_message: Optional[str] = None
    ) -> EditResult:
        """
        批次編輯檔案（原子性操作）

        Args:
            changes: 檔案變更列表
            create_commit: 是否建立 Git commit
            commit_message: Commit 訊息

        Returns:
            EditResult: 編輯結果
        """
        # 生成編輯 ID
        edit_id = f"edit_{int(time.time())}"

        console.print(f"\n[magenta]✏️  開始批次編輯（ID: {edit_id}）[/magenta]\n")

        # 步驟 1：驗證變更
        validation = self.validate_changes(changes)

        if not validation.is_valid:
            console.print(f"[dim magenta]✗ 驗證失敗：[/red]")
            for error in validation.errors:
                console.print(f"  - {error}")

            return EditResult(
                edit_id=edit_id,
                status=EditStatus.FAILED,
                failed_count=len(changes),
                error_messages=validation.errors
            )

        # 顯示警告
        if validation.warnings:
            console.print(f"[magenta]⚠️  警告：[/yellow]")
            for warning in validation.warnings:
                console.print(f"  - {warning}")

        # 步驟 2：建立備份
        backup_id = None
        if self.auto_backup:
            try:
                backup_id = self.create_backup([c.file_path for c in changes])
                console.print(f"[bright_magenta]✓ 已建立備份：{backup_id}[/green]")
            except Exception as e:
                console.print(f"[magenta]警告：備份失敗 - {e}[/yellow]")

        # 步驟 3：執行變更
        result = EditResult(
            edit_id=edit_id,
            status=EditStatus.IN_PROGRESS,
            backup_id=backup_id
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("執行變更...", total=len(changes))

            for change in changes:
                try:
                    self._apply_single_change(change)
                    result.success_count += 1

                except Exception as e:
                    result.failed_count += 1
                    result.error_messages.append(f"{change.file_path}: {str(e)}")

                    # 原子性：若有失敗，回滾所有變更
                    console.print(f"\n[dim magenta]✗ 錯誤：{change.file_path} - {e}[/red]")
                    console.print(f"[magenta]回滾所有變更...[/yellow]")

                    if backup_id:
                        self.rollback(edit_id, backup_id)
                        result.status = EditStatus.ROLLED_BACK
                    else:
                        result.status = EditStatus.FAILED

                    return result

                progress.update(task, advance=1)

        # 步驟 4：建立 Git commit（選用）
        if create_commit and self._has_git:
            try:
                self._create_git_commit(
                    message=commit_message or f"CodeGemini edit {edit_id}",
                    files=[c.file_path for c in changes]
                )
                console.print(f"[bright_magenta]✓ 已建立 Git commit[/green]")
            except Exception as e:
                console.print(f"[magenta]警告：Git commit 失敗 - {e}[/yellow]")

        result.status = EditStatus.SUCCESS
        console.print(f"\n[bold green]✅ 批次編輯完成[/bold green]")
        console.print(f"  成功：{result.success_count}/{len(changes)} 個檔案")

        return result

    def _apply_single_change(self, change: FileChange):
        """套用單一檔案變更"""
        file_path = os.path.join(self.project_path, change.file_path)

        if change.action == 'create':
            # 建立新檔案
            self._create_file(file_path, change.description)

        elif change.action == 'modify':
            # 修改現有檔案
            self._modify_file(file_path, change.description)

        elif change.action == 'delete':
            # 刪除檔案
            self._delete_file(file_path)

        else:
            raise ValueError(f"未知的操作：{change.action}")

    def _create_file(self, file_path: str, content: str):
        """建立新檔案"""
        if os.path.exists(file_path):
            raise FileExistsError(f"檔案已存在：{file_path}")

        # 建立目錄
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 寫入檔案
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _modify_file(self, file_path: str, new_content: str):
        """修改現有檔案"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"檔案不存在：{file_path}")

        # 寫入新內容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    def _delete_file(self, file_path: str):
        """刪除檔案"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"檔案不存在：{file_path}")

        os.remove(file_path)

    def validate_changes(self, changes: List[FileChange]) -> ValidationResult:
        """
        驗證變更

        Args:
            changes: 檔案變更列表

        Returns:
            ValidationResult: 驗證結果
        """
        result = ValidationResult(is_valid=True)

        for change in changes:
            file_path = os.path.join(self.project_path, change.file_path)

            # 檢查 create 操作
            if change.action == 'create':
                if os.path.exists(file_path):
                    result.errors.append(f"檔案已存在，無法建立：{change.file_path}")
                    result.is_valid = False

            # 檢查 modify/delete 操作
            elif change.action in ['modify', 'delete']:
                if not os.path.exists(file_path):
                    result.errors.append(f"檔案不存在，無法 {change.action}：{change.file_path}")
                    result.is_valid = False

            # 檢查路徑安全性（防止路徑遍歷攻擊）
            if '..' in change.file_path or change.file_path.startswith('/'):
                result.errors.append(f"不安全的路徑：{change.file_path}")
                result.is_valid = False

        # 檢查是否有衝突
        file_paths = [c.file_path for c in changes]
        if len(file_paths) != len(set(file_paths)):
            result.warnings.append("存在重複的檔案路徑")

        return result

    def rollback(self, edit_id: str, backup_id: Optional[str] = None) -> bool:
        """
        回滾變更

        Args:
            edit_id: 編輯 ID
            backup_id: 備份 ID

        Returns:
            bool: 是否成功回滾
        """
        console.print(f"\n[magenta]🔄 回滾變更（編輯 ID: {edit_id}）[/yellow]")

        if not backup_id:
            console.print("[dim magenta]錯誤：沒有備份 ID，無法回滾[/red]")
            return False

        backup_path = os.path.join(self.backup_dir, backup_id)

        if not os.path.exists(backup_path):
            console.print(f"[dim magenta]錯誤：找不到備份：{backup_path}[/red]")
            return False

        try:
            # 從備份還原檔案
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    backup_file = os.path.join(root, file)
                    rel_path = os.path.relpath(backup_file, backup_path)
                    target_file = os.path.join(self.project_path, rel_path)

                    # 還原檔案
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    shutil.copy2(backup_file, target_file)

            console.print(f"[bright_magenta]✓ 已從備份還原[/green]")
            return True

        except Exception as e:
            console.print(f"[dim magenta]錯誤：回滾失敗 - {e}[/red]")
            return False

    def create_backup(self, files: List[str]) -> str:
        """
        建立備份

        Args:
            files: 要備份的檔案路徑列表（相對路徑）

        Returns:
            str: 備份 ID
        """
        backup_id = f"backup_{int(time.time())}"
        backup_path = os.path.join(self.backup_dir, backup_id)

        os.makedirs(backup_path, exist_ok=True)

        for file_path in files:
            src_file = os.path.join(self.project_path, file_path)

            if os.path.exists(src_file):
                # 建立目標路徑
                dst_file = os.path.join(backup_path, file_path)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                # 複製檔案
                shutil.copy2(src_file, dst_file)

        return backup_id

    def _create_git_commit(self, message: str, files: List[str]):
        """建立 Git commit"""
        if not self._has_git:
            raise RuntimeError("非 Git 倉庫")

        # Git add
        for file_path in files:
            full_path = os.path.join(self.project_path, file_path)
            if os.path.exists(full_path):
                subprocess.run(
                    ['git', 'add', file_path],
                    cwd=self.project_path,
                    check=True,
                    capture_output=True
                )

        # Git commit
        subprocess.run(
            ['git', 'commit', '-m', message],
            cwd=self.project_path,
            check=True,
            capture_output=True
        )

    def show_change_preview(self, changes: List[FileChange]):
        """顯示變更預覽"""
        console.print("\n[bold magenta]📝 變更預覽[/bold magenta]\n")

        for i, change in enumerate(changes, 1):
            action_emoji = {
                'create': '✨',
                'modify': '✏️',
                'delete': '🗑️'
            }.get(change.action, '📝')

            console.print(f"{i}. {action_emoji} {change.action.upper()}: {change.file_path}")

            if change.description:
                # 顯示內容預覽（限制長度）
                preview = change.description[:200] + "..." if len(change.description) > 200 else change.description

                if change.action in ['create', 'modify']:
                    # 嘗試語法高亮
                    ext = os.path.splitext(change.file_path)[1]
                    lexer = {
                        '.py': 'python',
                        '.js': 'javascript',
                        '.ts': 'typescript',
                        '.java': 'java',
                        '.go': 'go',
                    }.get(ext, 'text')

                    syntax = Syntax(preview, lexer, theme="monokai", line_numbers=False)
                    console.print(syntax)
                else:
                    console.print(f"   {preview}")

            console.print()


def main():
    """測試用主程式"""
    import sys

    console.print("[bold magenta]CodeGemini Multi-File Editor 測試[/bold magenta]\n")

    # 建立測試變更
    test_changes = [
        FileChange(
            file_path="test_file_1.py",
            action="create",
            description='# 測試檔案 1\n\ndef hello():\n    print("Hello, World!")\n',
            estimated_lines=4
        ),
        FileChange(
            file_path="test_file_2.py",
            action="create",
            description='# 測試檔案 2\n\ndef goodbye():\n    print("Goodbye!")\n',
            estimated_lines=4
        ),
    ]

    try:
        # 使用當前目錄作為測試
        editor = MultiFileEditor(project_path=".", git_integration=False)

        # 預覽變更
        editor.show_change_preview(test_changes)

        # 執行批次編輯
        result = editor.batch_edit(test_changes)

        if result.status == EditStatus.SUCCESS:
            console.print("\n[bold green]✅ 測試成功[/bold green]")

            # 清理測試檔案
            console.print("\n[magenta]清理測試檔案...[/magenta]")
            for change in test_changes:
                if os.path.exists(change.file_path):
                    os.remove(change.file_path)
            console.print("[bright_magenta]✓ 清理完成[/green]")

        else:
            console.print(f"\n[dim magenta]✗ 測試失敗：{result.status.value}[/red]")

    except Exception as e:
        console.print(f"\n[dim magenta]錯誤：{e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
