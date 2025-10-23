#!/usr/bin/env python3
"""
Gemini Checkpoint System
檢查點系統 - 自動保存與回溯功能

此模組提供：
1. 自動檢查點保存（檔案變更前）
2. 回溯功能（/rewind 指令 + Esc 雙擊）
3. 增量儲存（diff 演算法）
4. 檢查點管理（列表、刪除、清理）

設計理念：
- 輕量級：僅保存差異，降低儲存空間
- 快速：使用 difflib 進行增量計算
- 安全：SQLite 事務保證資料完整性
- 可視化：Rich UI 展示檢查點清單

作者：Saki-tw (with Claude Code)
日期：2025-10-23
版本：1.0.0
"""

import os
import sqlite3
import gzip
import json
import shutil
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import difflib
import uuid

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.tree import Tree

console = Console()


# ============================================================================
# 資料結構
# ============================================================================

class CheckpointType(Enum):
    """檢查點類型"""
    AUTO = "auto"           # 自動檢查點（檔案變更前）
    MANUAL = "manual"       # 手動檢查點（使用者明確建立）
    SNAPSHOT = "snapshot"   # 完整快照（非增量）
    BRANCH = "branch"       # 分支檢查點（實驗性變更）


class FileChangeType(Enum):
    """檔案變更類型"""
    CREATED = "created"     # 新建檔案
    MODIFIED = "modified"   # 修改檔案
    DELETED = "deleted"     # 刪除檔案
    RENAMED = "renamed"     # 重命名檔案


@dataclass
class FileChange:
    """檔案變更資訊"""
    file_path: str                      # 檔案路徑（相對於專案根目錄）
    change_type: FileChangeType         # 變更類型
    content_before: Optional[str] = None  # 變更前內容
    content_after: Optional[str] = None   # 變更後內容
    diff: Optional[str] = None          # 差異（unified diff 格式）
    hash_before: Optional[str] = None   # 變更前雜湊
    hash_after: Optional[str] = None    # 變更後雜湊
    size_before: int = 0                # 變更前大小（bytes）
    size_after: int = 0                 # 變更後大小（bytes）

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'file_path': self.file_path,
            'change_type': self.change_type.value,
            'content_before': self.content_before,
            'content_after': self.content_after,
            'diff': self.diff,
            'hash_before': self.hash_before,
            'hash_after': self.hash_after,
            'size_before': self.size_before,
            'size_after': self.size_after
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileChange':
        """從字典建立"""
        data['change_type'] = FileChangeType(data['change_type'])
        return cls(**data)


@dataclass
class Checkpoint:
    """檢查點資料結構"""
    id: str                             # 檢查點 ID（UUID）
    timestamp: datetime                 # 建立時間
    checkpoint_type: CheckpointType     # 檢查點類型
    description: str                    # 描述
    tags: List[str] = field(default_factory=list)  # 標籤
    file_changes: List[FileChange] = field(default_factory=list)  # 檔案變更清單
    parent_id: Optional[str] = None     # 父檢查點 ID（用於分支）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 額外元數據
    total_size: int = 0                 # 總大小（bytes）
    compressed_size: int = 0            # 壓縮後大小（bytes）

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'checkpoint_type': self.checkpoint_type.value,
            'description': self.description,
            'tags': self.tags,
            'file_changes': [fc.to_dict() for fc in self.file_changes],
            'parent_id': self.parent_id,
            'metadata': self.metadata,
            'total_size': self.total_size,
            'compressed_size': self.compressed_size
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """從字典建立"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['checkpoint_type'] = CheckpointType(data['checkpoint_type'])
        data['file_changes'] = [FileChange.from_dict(fc) for fc in data['file_changes']]
        return cls(**data)


# ============================================================================
# 快照引擎（Diff 演算法）
# ============================================================================

class SnapshotEngine:
    """
    快照引擎 - 負責計算檔案差異與快照

    功能：
    - 計算兩個檔案版本的差異（unified diff）
    - 應用差異以恢復檔案
    - 計算檔案雜湊
    - 壓縮/解壓縮內容
    """

    @staticmethod
    def calculate_hash(content: str) -> str:
        """計算內容雜湊（SHA-256）"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_diff(content_before: str, content_after: str, filename: str = "file") -> str:
        """
        生成 unified diff

        Args:
            content_before: 變更前內容
            content_after: 變更後內容
            filename: 檔案名稱（用於 diff 標頭）

        Returns:
            unified diff 字串
        """
        lines_before = content_before.splitlines(keepends=True)
        lines_after = content_after.splitlines(keepends=True)

        diff = difflib.unified_diff(
            lines_before,
            lines_after,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=''
        )

        return ''.join(diff)

    @staticmethod
    def apply_diff(content_before: str, diff: str) -> str:
        """
        應用 diff 以恢復內容

        Args:
            content_before: 原始內容
            diff: unified diff

        Returns:
            應用 diff 後的內容
        """
        # 解析 unified diff
        lines_before = content_before.splitlines(keepends=True)

        # 使用 difflib 的內部方法應用 diff
        # 注意：這是簡化版本，完整實作需要解析 diff 格式
        # TODO: 實作完整的 diff 應用邏輯

        # 暫時使用簡單的行替換邏輯
        diff_lines = diff.splitlines()
        result_lines = lines_before.copy()

        line_num = 0
        for diff_line in diff_lines:
            if diff_line.startswith('@@'):
                # 解析行號範圍
                # 格式: @@ -start,count +start,count @@
                parts = diff_line.split()
                if len(parts) >= 3:
                    try:
                        new_range = parts[2][1:]  # 移除 '+'
                        line_num = int(new_range.split(',')[0]) - 1
                    except (ValueError, IndexError):
                        continue
            elif diff_line.startswith('-'):
                # 刪除行
                if line_num < len(result_lines):
                    result_lines.pop(line_num)
            elif diff_line.startswith('+'):
                # 新增行
                new_line = diff_line[1:] + '\n'
                if line_num <= len(result_lines):
                    result_lines.insert(line_num, new_line)
                    line_num += 1
            elif diff_line.startswith(' '):
                # 未變更行
                line_num += 1

        return ''.join(result_lines)

    @staticmethod
    def compress(content: str) -> bytes:
        """壓縮內容（gzip）"""
        return gzip.compress(content.encode('utf-8'))

    @staticmethod
    def decompress(data: bytes) -> str:
        """解壓縮內容（gzip）"""
        return gzip.decompress(data).decode('utf-8')

    @staticmethod
    def create_file_change(
        file_path: str,
        content_before: Optional[str],
        content_after: Optional[str],
        change_type: FileChangeType = FileChangeType.MODIFIED
    ) -> FileChange:
        """
        建立檔案變更物件

        Args:
            file_path: 檔案路徑
            content_before: 變更前內容
            content_after: 變更後內容
            change_type: 變更類型

        Returns:
            FileChange 物件
        """
        file_change = FileChange(
            file_path=file_path,
            change_type=change_type
        )

        # 計算雜湊與大小
        if content_before:
            file_change.content_before = content_before
            file_change.hash_before = SnapshotEngine.calculate_hash(content_before)
            file_change.size_before = len(content_before.encode('utf-8'))

        if content_after:
            file_change.content_after = content_after
            file_change.hash_after = SnapshotEngine.calculate_hash(content_after)
            file_change.size_after = len(content_after.encode('utf-8'))

        # 生成 diff（僅對修改的檔案）
        if change_type == FileChangeType.MODIFIED and content_before and content_after:
            file_change.diff = SnapshotEngine.generate_diff(
                content_before,
                content_after,
                filename=os.path.basename(file_path)
            )

        return file_change


# ============================================================================
# 檢查點管理器
# ============================================================================

class CheckpointManager:
    """
    檢查點管理器 - 核心管理類別

    功能：
    - 建立/刪除/列出檢查點
    - 回溯至指定檢查點
    - 自動清理舊檢查點
    - 檢查點搜尋與過濾
    """

    def __init__(self, project_root: Path, checkpoints_dir: Optional[Path] = None):
        """
        初始化檢查點管理器

        Args:
            project_root: 專案根目錄
            checkpoints_dir: 檢查點儲存目錄（預設為 .checkpoints）
        """
        self.project_root = Path(project_root).resolve()
        self.checkpoints_dir = checkpoints_dir or (self.project_root / ".checkpoints")
        self.snapshots_dir = self.checkpoints_dir / "snapshots"
        self.db_path = self.checkpoints_dir / "metadata.db"

        # 建立目錄結構
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        # 初始化資料庫
        self._init_database()

        console.print(f"[dim]✓ CheckpointManager 初始化完成: {self.checkpoints_dir}[/dim]")

    def _init_database(self):
        """初始化 SQLite 資料庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 建立檢查點表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                checkpoint_type TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                parent_id TEXT,
                metadata TEXT,
                total_size INTEGER,
                compressed_size INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立檔案變更表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checkpoint_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                change_type TEXT NOT NULL,
                hash_before TEXT,
                hash_after TEXT,
                size_before INTEGER,
                size_after INTEGER,
                snapshot_path TEXT,
                FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id) ON DELETE CASCADE
            )
        """)

        # 建立索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON checkpoints(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON checkpoints(checkpoint_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoint_id ON file_changes(checkpoint_id)")

        conn.commit()
        conn.close()

    def create_checkpoint(
        self,
        file_changes: List[FileChange],
        description: str = "",
        checkpoint_type: CheckpointType = CheckpointType.AUTO,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = None
    ) -> Checkpoint:
        """
        建立新檢查點

        Args:
            file_changes: 檔案變更清單
            description: 描述
            checkpoint_type: 檢查點類型
            tags: 標籤
            parent_id: 父檢查點 ID

        Returns:
            建立的 Checkpoint 物件
        """
        checkpoint_id = str(uuid.uuid4())
        timestamp = datetime.now()

        # 建立檢查點物件
        checkpoint = Checkpoint(
            id=checkpoint_id,
            timestamp=timestamp,
            checkpoint_type=checkpoint_type,
            description=description or f"自動檢查點 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            tags=tags or [],
            file_changes=file_changes,
            parent_id=parent_id
        )

        # 儲存快照檔案
        total_size = 0
        compressed_size = 0

        for file_change in file_changes:
            snapshot_data = file_change.to_dict()
            snapshot_json = json.dumps(snapshot_data, ensure_ascii=False, indent=2)

            # 壓縮並儲存
            compressed = SnapshotEngine.compress(snapshot_json)
            snapshot_filename = f"{checkpoint_id}_{hashlib.md5(file_change.file_path.encode()).hexdigest()}.json.gz"
            snapshot_path = self.snapshots_dir / snapshot_filename

            with open(snapshot_path, 'wb') as f:
                f.write(compressed)

            total_size += len(snapshot_json.encode('utf-8'))
            compressed_size += len(compressed)

        checkpoint.total_size = total_size
        checkpoint.compressed_size = compressed_size

        # 儲存至資料庫
        self._save_checkpoint_to_db(checkpoint)

        console.print(f"[green]✓[/green] 檢查點已建立: [cyan]{checkpoint_id[:8]}[/cyan]")
        console.print(f"  └─ 檔案變更: {len(file_changes)} 個")
        console.print(f"  └─ 壓縮率: {compressed_size / total_size * 100:.1f}%" if total_size > 0 else "  └─ 空檢查點")

        return checkpoint

    def _save_checkpoint_to_db(self, checkpoint: Checkpoint):
        """儲存檢查點至資料庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 插入檢查點
            cursor.execute("""
                INSERT INTO checkpoints (
                    id, timestamp, checkpoint_type, description, tags,
                    parent_id, metadata, total_size, compressed_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                checkpoint.id,
                checkpoint.timestamp.isoformat(),
                checkpoint.checkpoint_type.value,
                checkpoint.description,
                json.dumps(checkpoint.tags),
                checkpoint.parent_id,
                json.dumps(checkpoint.metadata),
                checkpoint.total_size,
                checkpoint.compressed_size
            ))

            # 插入檔案變更
            for file_change in checkpoint.file_changes:
                snapshot_filename = f"{checkpoint.id}_{hashlib.md5(file_change.file_path.encode()).hexdigest()}.json.gz"

                cursor.execute("""
                    INSERT INTO file_changes (
                        checkpoint_id, file_path, change_type,
                        hash_before, hash_after, size_before, size_after, snapshot_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    checkpoint.id,
                    file_change.file_path,
                    file_change.change_type.value,
                    file_change.hash_before,
                    file_change.hash_after,
                    file_change.size_before,
                    file_change.size_after,
                    snapshot_filename
                ))

            conn.commit()
        except Exception as e:
            conn.rollback()
            console.print(f"[red]✗[/red] 儲存檢查點失敗: {e}")
            raise
        finally:
            conn.close()

    def list_checkpoints(
        self,
        limit: int = 20,
        checkpoint_type: Optional[CheckpointType] = None,
        tags: Optional[List[str]] = None
    ) -> List[Checkpoint]:
        """
        列出檢查點

        Args:
            limit: 最大數量
            checkpoint_type: 過濾檢查點類型
            tags: 過濾標籤

        Returns:
            Checkpoint 物件清單
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM checkpoints WHERE 1=1"
        params = []

        if checkpoint_type:
            query += " AND checkpoint_type = ?"
            params.append(checkpoint_type.value)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        checkpoints = []
        for row in rows:
            checkpoint_data = {
                'id': row[0],
                'timestamp': row[1],
                'checkpoint_type': row[2],
                'description': row[3],
                'tags': json.loads(row[4]) if row[4] else [],
                'parent_id': row[5],
                'metadata': json.loads(row[6]) if row[6] else {},
                'total_size': row[7],
                'compressed_size': row[8],
                'file_changes': []
            }

            # 載入檔案變更
            cursor.execute("""
                SELECT file_path, change_type, hash_before, hash_after,
                       size_before, size_after, snapshot_path
                FROM file_changes
                WHERE checkpoint_id = ?
            """, (row[0],))

            file_changes_rows = cursor.fetchall()
            for fc_row in file_changes_rows:
                file_change_dict = {
                    'file_path': fc_row[0],
                    'change_type': fc_row[1],
                    'hash_before': fc_row[2],
                    'hash_after': fc_row[3],
                    'size_before': fc_row[4] or 0,
                    'size_after': fc_row[5] or 0,
                    'content_before': None,
                    'content_after': None,
                    'diff': None
                }
                checkpoint_data['file_changes'].append(file_change_dict)

            checkpoint = Checkpoint.from_dict(checkpoint_data)

            # 過濾標籤
            if tags:
                if any(tag in checkpoint.tags for tag in tags):
                    checkpoints.append(checkpoint)
            else:
                checkpoints.append(checkpoint)

        conn.close()
        return checkpoints

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """取得指定檢查點"""
        checkpoints = self.list_checkpoints(limit=1000)
        for cp in checkpoints:
            if cp.id.startswith(checkpoint_id):
                return cp
        return None

    def rewind_to_checkpoint(self, checkpoint_id: str, confirm: bool = True) -> bool:
        """
        回溯至指定檢查點

        Args:
            checkpoint_id: 檢查點 ID（可為部分 ID）
            confirm: 是否需要確認

        Returns:
            是否成功回溯
        """
        checkpoint = self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            console.print(f"[red]✗[/red] 找不到檢查點: {checkpoint_id}")
            return False

        # 顯示檢查點資訊
        self._display_checkpoint_detail(checkpoint)

        # 確認
        if confirm:
            if not Confirm.ask(f"\n確定要回溯至此檢查點嗎？"):
                console.print("[yellow]已取消回溯[/yellow]")
                return False

        # 執行回溯
        console.print(f"\n[cyan]開始回溯至檢查點 {checkpoint.id[:8]}...[/cyan]")

        success_count = 0
        fail_count = 0

        for file_change in checkpoint.file_changes:
            try:
                file_path = self.project_root / file_change.file_path

                # 載入快照
                snapshot_filename = f"{checkpoint.id}_{hashlib.md5(file_change.file_path.encode()).hexdigest()}.json.gz"
                snapshot_path = self.snapshots_dir / snapshot_filename

                if not snapshot_path.exists():
                    console.print(f"  [yellow]⚠[/yellow] 快照檔案不存在: {file_change.file_path}")
                    fail_count += 1
                    continue

                with open(snapshot_path, 'rb') as f:
                    compressed_data = f.read()
                    snapshot_json = SnapshotEngine.decompress(compressed_data)
                    snapshot_data = json.loads(snapshot_json)

                # 根據變更類型執行操作
                if file_change.change_type == FileChangeType.CREATED:
                    # 刪除新建的檔案
                    if file_path.exists():
                        file_path.unlink()
                        console.print(f"  [green]✓[/green] 刪除: {file_change.file_path}")
                    success_count += 1

                elif file_change.change_type == FileChangeType.DELETED:
                    # 恢復刪除的檔案
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(snapshot_data['content_before'] or '')
                    console.print(f"  [green]✓[/green] 恢復: {file_change.file_path}")
                    success_count += 1

                elif file_change.change_type == FileChangeType.MODIFIED:
                    # 恢復修改的檔案
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(snapshot_data['content_before'] or '')
                    console.print(f"  [green]✓[/green] 恢復: {file_change.file_path}")
                    success_count += 1

            except Exception as e:
                console.print(f"  [red]✗[/red] 失敗: {file_change.file_path} - {e}")
                fail_count += 1

        # 顯示結果
        console.print(f"\n[green]✓[/green] 回溯完成:")
        console.print(f"  └─ 成功: {success_count} 個檔案")
        if fail_count > 0:
            console.print(f"  └─ 失敗: {fail_count} 個檔案")

        return fail_count == 0

    def _display_checkpoint_detail(self, checkpoint: Checkpoint):
        """顯示檢查點詳細資訊"""
        panel = Panel(
            f"[bold cyan]{checkpoint.description}[/bold cyan]\n\n"
            f"ID: {checkpoint.id[:8]}...\n"
            f"時間: {checkpoint.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"類型: {checkpoint.checkpoint_type.value}\n"
            f"檔案變更: {len(checkpoint.file_changes)} 個\n"
            f"大小: {checkpoint.total_size / 1024:.2f} KB → {checkpoint.compressed_size / 1024:.2f} KB "
            f"(壓縮率 {checkpoint.compressed_size / checkpoint.total_size * 100:.1f}%)",
            title="[bold]檢查點資訊[/bold]",
            border_style="cyan"
        )
        console.print(panel)

        # 顯示檔案清單
        if checkpoint.file_changes:
            table = Table(title="檔案變更清單", show_header=True, header_style="bold magenta")
            table.add_column("變更類型", style="cyan", width=12)
            table.add_column("檔案路徑", style="white")
            table.add_column("大小變化", justify="right", style="yellow")

            for fc in checkpoint.file_changes:
                change_emoji = {
                    FileChangeType.CREATED: "➕ 新建",
                    FileChangeType.MODIFIED: "📝 修改",
                    FileChangeType.DELETED: "➖ 刪除",
                    FileChangeType.RENAMED: "🔄 重命名"
                }.get(fc.change_type, "❓ 未知")

                size_change = f"{fc.size_before} → {fc.size_after}" if fc.change_type == FileChangeType.MODIFIED else str(fc.size_after)

                table.add_row(change_emoji, fc.file_path, size_change)

            console.print(table)

    def show_checkpoints_ui(self, limit: int = 20):
        """顯示檢查點清單 UI"""
        checkpoints = self.list_checkpoints(limit=limit)

        if not checkpoints:
            console.print("[yellow]沒有檢查點[/yellow]")
            return

        table = Table(title=f"檢查點清單（最近 {len(checkpoints)} 個）", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=10)
        table.add_column("時間", style="white", width=20)
        table.add_column("類型", style="yellow", width=10)
        table.add_column("描述", style="white")
        table.add_column("檔案數", justify="right", style="green", width=8)

        for cp in checkpoints:
            type_emoji = {
                CheckpointType.AUTO: "🤖",
                CheckpointType.MANUAL: "👤",
                CheckpointType.SNAPSHOT: "📸",
                CheckpointType.BRANCH: "🌿"
            }.get(cp.checkpoint_type, "❓")

            table.add_row(
                cp.id[:8],
                cp.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                f"{type_emoji} {cp.checkpoint_type.value}",
                cp.description[:50] + "..." if len(cp.description) > 50 else cp.description,
                str(len(cp.file_changes))
            )

        console.print(table)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """刪除檢查點"""
        checkpoint = self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            console.print(f"[red]✗[/red] 找不到檢查點: {checkpoint_id}")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 刪除快照檔案
            for file_change in checkpoint.file_changes:
                snapshot_filename = f"{checkpoint.id}_{hashlib.md5(file_change.file_path.encode()).hexdigest()}.json.gz"
                snapshot_path = self.snapshots_dir / snapshot_filename
                if snapshot_path.exists():
                    snapshot_path.unlink()

            # 刪除資料庫記錄
            cursor.execute("DELETE FROM file_changes WHERE checkpoint_id = ?", (checkpoint.id,))
            cursor.execute("DELETE FROM checkpoints WHERE id = ?", (checkpoint.id,))
            conn.commit()

            console.print(f"[green]✓[/green] 已刪除檢查點: {checkpoint.id[:8]}")
            return True

        except Exception as e:
            conn.rollback()
            console.print(f"[red]✗[/red] 刪除失敗: {e}")
            return False
        finally:
            conn.close()

    def cleanup_old_checkpoints(self, keep_count: int = 50, dry_run: bool = True):
        """
        清理舊檢查點

        Args:
            keep_count: 保留最近 N 個檢查點
            dry_run: 是否為試運行（不實際刪除）
        """
        checkpoints = self.list_checkpoints(limit=1000)

        if len(checkpoints) <= keep_count:
            console.print(f"[green]無需清理（共 {len(checkpoints)} 個檢查點，保留 {keep_count} 個）[/green]")
            return

        to_delete = checkpoints[keep_count:]

        console.print(f"\n[yellow]將刪除 {len(to_delete)} 個舊檢查點:[/yellow]")
        for cp in to_delete[:10]:  # 顯示前 10 個
            console.print(f"  - {cp.id[:8]} | {cp.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {cp.description[:40]}")

        if len(to_delete) > 10:
            console.print(f"  ... 及其他 {len(to_delete) - 10} 個")

        if dry_run:
            console.print("\n[cyan]（試運行模式，未實際刪除）[/cyan]")
            return

        if not Confirm.ask("\n確定要刪除這些檢查點嗎？"):
            console.print("[yellow]已取消清理[/yellow]")
            return

        deleted_count = 0
        for cp in to_delete:
            if self.delete_checkpoint(cp.id):
                deleted_count += 1

        console.print(f"\n[green]✓[/green] 已清理 {deleted_count} 個舊檢查點")


# ============================================================================
# 便利函數
# ============================================================================

# 全域管理器實例（延遲初始化）
_global_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager(project_root: Optional[Path] = None) -> CheckpointManager:
    """取得全域檢查點管理器"""
    global _global_checkpoint_manager

    if _global_checkpoint_manager is None:
        if project_root is None:
            project_root = Path.cwd()
        _global_checkpoint_manager = CheckpointManager(project_root)

    return _global_checkpoint_manager


def auto_checkpoint(file_paths: List[str], description: str = ""):
    """
    自動建立檢查點（便利函數）

    Args:
        file_paths: 檔案路徑清單
        description: 描述
    """
    manager = get_checkpoint_manager()

    file_changes = []
    for file_path in file_paths:
        full_path = Path(file_path)
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_change = SnapshotEngine.create_file_change(
                file_path=str(full_path.relative_to(manager.project_root)),
                content_before=content,
                content_after=content,
                change_type=FileChangeType.MODIFIED
            )
            file_changes.append(file_change)

    if file_changes:
        manager.create_checkpoint(
            file_changes=file_changes,
            description=description,
            checkpoint_type=CheckpointType.AUTO
        )


# ============================================================================
# CLI 測試介面
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gemini Checkpoint System")
    parser.add_argument('command', choices=['list', 'create', 'rewind', 'delete', 'cleanup', 'test'],
                        help='指令')
    parser.add_argument('--id', help='檢查點 ID')
    parser.add_argument('--limit', type=int, default=20, help='列出數量')
    parser.add_argument('--keep', type=int, default=50, help='保留數量')
    parser.add_argument('--description', help='描述')
    parser.add_argument('--files', nargs='+', help='檔案清單')
    parser.add_argument('--dry-run', action='store_true', help='試運行')

    args = parser.parse_args()

    manager = get_checkpoint_manager()

    if args.command == 'list':
        manager.show_checkpoints_ui(limit=args.limit)

    elif args.command == 'create':
        if not args.files:
            console.print("[red]需要指定 --files[/red]")
        else:
            auto_checkpoint(args.files, args.description or "")

    elif args.command == 'rewind':
        if not args.id:
            console.print("[red]需要指定 --id[/red]")
        else:
            manager.rewind_to_checkpoint(args.id)

    elif args.command == 'delete':
        if not args.id:
            console.print("[red]需要指定 --id[/red]")
        else:
            manager.delete_checkpoint(args.id)

    elif args.command == 'cleanup':
        manager.cleanup_old_checkpoints(keep_count=args.keep, dry_run=args.dry_run)

    elif args.command == 'test':
        # 測試模式
        console.print("[cyan]測試模式 - 建立範例檢查點[/cyan]\n")

        # 建立測試檔案
        test_file = Path("test_checkpoint.txt")
        test_file.write_text("Hello, World!\nThis is a test file.")

        # 建立檢查點
        auto_checkpoint([str(test_file)], "測試檢查點")

        # 列出檢查點
        manager.show_checkpoints_ui(limit=5)

        # 清理
        test_file.unlink()
        console.print("\n[green]✓[/green] 測試完成")
