#!/usr/bin/env python3
"""
對話歷史管理器 - ConversationHistoryManager

功能：
- 搜尋歷史對話
- 列出對話記錄
- 匯出對話記錄
- 刪除對話記錄（需二次確認）
- 統計資訊

設計原則：
- 智能降級：所有錯誤都優雅處理
- 記憶體優化：使用生成器處理大檔案
- 零破壞性：不修改現有日誌檔案
- 資料刪除原則：對話記錄屬於「財產」，刪除需二次確認
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Generator, Tuple
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# 從配置取得預設日誌目錄
try:
    from config import OUTPUT_DIRS
    DEFAULT_LOG_DIR = str(OUTPUT_DIRS.get('chat_logs', Path.cwd() / 'ChatLogs'))
except ImportError:
    DEFAULT_LOG_DIR = str(Path.cwd() / 'ChatLogs')


class ConversationHistoryManager:
    """
    對話歷史管理器

    使用生成器模式處理大型日誌檔案，避免記憶體溢出。
    """

    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化對話歷史管理器

        Args:
            log_dir: 日誌目錄路徑，預設使用 DEFAULT_LOG_DIR
        """
        if log_dir is None:
            log_dir = DEFAULT_LOG_DIR

        self.log_dir = Path(log_dir)

        # 確保目錄存在
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"無法建立日誌目錄 {self.log_dir}: {e}")
            # 降級：使用當前目錄
            self.log_dir = Path.cwd() / 'ChatLogs'
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def _read_messages(self, log_file: Path) -> Generator[Dict, None, None]:
        """
        生成器：逐行讀取對話記錄（JSONL 格式）

        Args:
            log_file: 日誌檔案路徑

        Yields:
            訊息字典
        """
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.debug(f"跳過無效 JSON 行: {e}")
                        continue
        except FileNotFoundError:
            logger.debug(f"日誌檔案不存在: {log_file}")
            return
        except Exception as e:
            logger.warning(f"讀取日誌失敗 {log_file}: {e}")
            return

    def _get_log_files(self) -> List[Path]:
        """
        獲取所有日誌檔案，按修改時間排序（新→舊）

        Returns:
            日誌檔案路徑列表
        """
        try:
            files = list(self.log_dir.glob('*.jsonl'))
            # 按修改時間排序，最新的在前
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            return files
        except Exception as e:
            logger.warning(f"獲取日誌檔案列表失敗: {e}")
            return []

    def search(
        self,
        keyword: str,
        limit: int = 50,
        case_sensitive: bool = False
    ) -> List[Dict]:
        """
        搜尋對話歷史

        Args:
            keyword: 搜尋關鍵字
            limit: 最多返回結果數量
            case_sensitive: 是否區分大小寫

        Returns:
            搜尋結果列表，每個元素包含：
            {
                'file': 檔案名稱,
                'timestamp': 時間戳,
                'role': 角色 (user/assistant),
                'content': 內容預覽 (前 200 字元),
                'full_content': 完整內容
            }
        """
        results = []
        search_keyword = keyword if case_sensitive else keyword.lower()

        try:
            for log_file in self._get_log_files():
                if len(results) >= limit:
                    break

                for message in self._read_messages(log_file):
                    if len(results) >= limit:
                        break

                    content = message.get('content', '')
                    search_content = content if case_sensitive else content.lower()

                    if search_keyword in search_content:
                        results.append({
                            'file': log_file.name,
                            'timestamp': message.get('timestamp', 'Unknown'),
                            'role': message.get('role', 'unknown'),
                            'content': content[:200] + ('...' if len(content) > 200 else ''),
                            'full_content': content
                        })
        except Exception as e:
            logger.error(f"搜尋過程發生錯誤: {e}")
            # 降級：返回已找到的結果

        return results

    def list_conversations(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        列出對話記錄

        Args:
            start_date: 開始日期（可選）
            end_date: 結束日期（可選）
            limit: 最多返回數量

        Returns:
            對話記錄列表，每個元素包含：
            {
                'file': 檔案名稱,
                'date': 日期,
                'message_count': 訊息數量,
                'size': 檔案大小（bytes）,
                'preview': 前 3 條訊息預覽
            }
        """
        conversations = []

        try:
            for log_file in self._get_log_files():
                if len(conversations) >= limit:
                    break

                # 檢查日期過濾
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if start_date and file_time < start_date:
                    continue
                if end_date and file_time > end_date:
                    continue

                # 統計訊息數量並取得預覽
                message_count = 0
                preview_messages = []

                for message in self._read_messages(log_file):
                    message_count += 1
                    if len(preview_messages) < 3:
                        preview_messages.append({
                            'role': message.get('role', 'unknown'),
                            'content': message.get('content', '')[:100]
                        })

                conversations.append({
                    'file': log_file.name,
                    'date': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message_count': message_count,
                    'size': log_file.stat().st_size,
                    'preview': preview_messages
                })
        except Exception as e:
            logger.error(f"列出對話時發生錯誤: {e}")
            # 降級：返回已收集的列表

        return conversations

    def export(
        self,
        output_path: str,
        format: str = 'json',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        匯出對話記錄

        Args:
            output_path: 輸出檔案路徑
            format: 匯出格式 ('json' 或 'markdown')
            start_date: 開始日期（可選）
            end_date: 結束日期（可選）

        Returns:
            (成功與否, 訊息)
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if format == 'json':
                return self._export_json(output_file, start_date, end_date)
            elif format == 'markdown':
                return self._export_markdown(output_file, start_date, end_date)
            else:
                return False, f"不支援的格式: {format}"

        except Exception as e:
            logger.error(f"匯出失敗: {e}")
            return False, str(e)

    def _export_json(
        self,
        output_file: Path,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> Tuple[bool, str]:
        """匯出為 JSON 格式"""
        try:
            all_conversations = []

            for log_file in self._get_log_files():
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if start_date and file_time < start_date:
                    continue
                if end_date and file_time > end_date:
                    continue

                conversation = {
                    'file': log_file.name,
                    'date': file_time.isoformat(),
                    'messages': list(self._read_messages(log_file))
                }
                all_conversations.append(conversation)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_conversations, f, ensure_ascii=False, indent=2)

            return True, f"已匯出 {len(all_conversations)} 個對話至 {output_file}"

        except Exception as e:
            return False, f"JSON 匯出失敗: {e}"

    def _export_markdown(
        self,
        output_file: Path,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> Tuple[bool, str]:
        """匯出為 Markdown 格式"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# 對話歷史記錄\n\n")
                f.write(f"**匯出時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                conversation_count = 0

                for log_file in self._get_log_files():
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if start_date and file_time < start_date:
                        continue
                    if end_date and file_time > end_date:
                        continue

                    conversation_count += 1
                    f.write(f"## 對話 {conversation_count}: {log_file.name}\n\n")
                    f.write(f"**日期**: {file_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                    for message in self._read_messages(log_file):
                        role = message.get('role', 'unknown')
                        content = message.get('content', '')
                        timestamp = message.get('timestamp', '')

                        role_emoji = {'user': '👤', 'assistant': '🤖', 'system': '⚙️'}.get(role, '❓')
                        f.write(f"### {role_emoji} {role.capitalize()} ({timestamp})\n\n")
                        f.write(f"{content}\n\n")
                        f.write("---\n\n")

            return True, f"已匯出 {conversation_count} 個對話至 {output_file}"

        except Exception as e:
            return False, f"Markdown 匯出失敗: {e}"

    def delete_conversation(
        self,
        file_name: str,
        confirm: bool = False
    ) -> Tuple[bool, str]:
        """
        刪除對話記錄（需二次確認）

        Args:
            file_name: 要刪除的檔案名稱
            confirm: 是否已確認刪除

        Returns:
            (成功與否, 訊息)
        """
        if not confirm:
            return False, "⚠️  刪除對話記錄需要確認（confirm=True）"

        try:
            file_path = self.log_dir / file_name

            if not file_path.exists():
                return False, f"檔案不存在: {file_name}"

            # 刪除檔案
            file_path.unlink()

            return True, f"✓ 已刪除對話記錄: {file_name}"

        except Exception as e:
            logger.error(f"刪除失敗: {e}")
            return False, f"刪除失敗: {e}"

    def get_statistics(self) -> Dict:
        """
        獲取對話統計資訊

        Returns:
            統計資訊字典：
            {
                'total_conversations': 對話總數,
                'total_messages': 訊息總數,
                'total_size': 總大小（bytes）,
                'date_range': (最早日期, 最新日期),
                'role_distribution': {'user': N, 'assistant': M}
            }
        """
        stats = {
            'total_conversations': 0,
            'total_messages': 0,
            'total_size': 0,
            'date_range': (None, None),
            'role_distribution': defaultdict(int)
        }

        try:
            log_files = self._get_log_files()
            stats['total_conversations'] = len(log_files)

            if not log_files:
                return stats

            # 日期範圍
            oldest_time = datetime.fromtimestamp(log_files[-1].stat().st_mtime)
            newest_time = datetime.fromtimestamp(log_files[0].stat().st_mtime)
            stats['date_range'] = (
                oldest_time.strftime('%Y-%m-%d'),
                newest_time.strftime('%Y-%m-%d')
            )

            # 統計訊息數量和角色分布
            for log_file in log_files:
                stats['total_size'] += log_file.stat().st_size

                for message in self._read_messages(log_file):
                    stats['total_messages'] += 1
                    role = message.get('role', 'unknown')
                    stats['role_distribution'][role] += 1

        except Exception as e:
            logger.error(f"統計資訊計算失敗: {e}")
            # 降級：返回部分統計

        return stats


# 便捷函數：獲取全域實例
_global_manager = None

def get_history_manager() -> ConversationHistoryManager:
    """獲取全域對話歷史管理器實例（單例模式）"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ConversationHistoryManager()
    return _global_manager


# 測試代碼
if __name__ == "__main__":
    # 基本測試
    manager = ConversationHistoryManager()

    print("=== 測試對話歷史管理器 ===\n")

    # 測試統計
    stats = manager.get_statistics()
    print(f"統計資訊:")
    print(f"  - 對話總數: {stats['total_conversations']}")
    print(f"  - 訊息總數: {stats['total_messages']}")
    print(f"  - 總大小: {stats['total_size']} bytes")
    print(f"  - 日期範圍: {stats['date_range'][0]} ~ {stats['date_range'][1]}")
    print(f"  - 角色分布: {dict(stats['role_distribution'])}\n")

    # 測試列表
    conversations = manager.list_conversations(limit=5)
    print(f"最近 {len(conversations)} 個對話:")
    for i, conv in enumerate(conversations, 1):
        print(f"  {i}. {conv['file']} - {conv['date']} ({conv['message_count']} 則訊息)")
    print()

    # 測試搜尋
    keyword = input("輸入搜尋關鍵字 (Enter 跳過): ").strip()
    if keyword:
        results = manager.search(keyword, limit=10)
        print(f"\n搜尋結果 ({len(results)} 筆):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. [{result['role']}] {result['content']}")
            print(f"     檔案: {result['file']}, 時間: {result['timestamp']}\n")
