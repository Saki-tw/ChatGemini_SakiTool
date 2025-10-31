#!/usr/bin/env python3
"""
Gemini 對話管理器
從 gemini_chat.py 抽離
"""

import os
import json
from utils.i18n import safe_t
import logging
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 從配置取得預設日誌目錄
try:
    from config import OUTPUT_DIRS
    DEFAULT_LOG_DIR = str(OUTPUT_DIRS.get('chat_logs', Path.cwd() / 'ChatLogs'))
except ImportError:
    DEFAULT_LOG_DIR = str(Path.cwd() / 'ChatLogs')



class ConversationManager:
    """
    對話歷史管理器 - 防止記憶體洩漏

    功能：
    - 限制活躍對話歷史為 100 條
    - 自動存檔舊對話到磁碟
    - 釋放不再需要的記憶體
    """

    def __init__(self, max_history: int = 100, archive_dir: str = None):
        """
        初始化對話管理器

        Args:
            max_history: 最大活躍對話數量（預設 100 條）
            archive_dir: 存檔目錄（預設使用 DEFAULT_LOG_DIR）
        """
        self.max_history = max_history
        self.history = []  # 活躍對話（記憶體中）
        self.archived_count = 0  # 已存檔的對話數量

        if archive_dir is None:
            archive_dir = DEFAULT_LOG_DIR
        self.archive_dir = archive_dir
        os.makedirs(archive_dir, exist_ok=True)

        self.archive_file = os.path.join(
            archive_dir,
            f"archived_conversations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )

        logger.info(f"對話管理器已初始化：最多保留 {max_history} 條活躍對話")

    def add_message(self, message: dict):
        """
        添加訊息到對話歷史

        Args:
            message: 訊息字典,格式：
                {
                    "role": "user" | "assistant" | "system",
                    "content": "訊息內容",
                    "timestamp": "ISO時間戳",
                    ...
                }
        """
        self.history.append(message)

        # 檢查是否超過限制
        if len(self.history) > self.max_history:
            self._archive_old_messages()

    def _archive_old_messages(self):
        """
        存檔舊對話並清理記憶體

        策略：保留最新的 50 條,存檔前 50 條
        """
        archive_count = len(self.history) - 50

        if archive_count <= 0:
            return

        # 取出要存檔的訊息
        to_archive = self.history[:archive_count]

        # 寫入存檔檔案（JSONL 格式,每行一條訊息）
        try:
            with open(self.archive_file, 'a', encoding='utf-8') as f:
                for msg in to_archive:
                    json.dump(msg, f, ensure_ascii=False)
                    f.write('\n')

            self.archived_count += archive_count
            logger.info(f"已存檔 {archive_count} 條對話（總計 {self.archived_count} 條）")

            # 更新活躍歷史（僅保留最新的 50 條）
            history=self.history[archive_count:]

            # 提示：Python 的 GC 會自動回收不再引用的物件

        except Exception as e:
            logger.error(f"存檔對話失敗：{e}")

    def get_recent_history(self, count: int = None) -> List[dict]:
        """
        獲取最近的對話歷史

        Args:
            count: 返回的訊息數量（None=返回全部活躍歷史）

        Returns:
            對話列表
        """
        if count is None:
            return self.history.copy()
        return self.history[-count:] if count > 0 else []

    def clear(self):
        """清空所有對話歷史（謹慎使用）"""
        self.history.clear()
        logger.info("對話歷史已清空")

    def get_stats(self) -> dict:
        """
        獲取統計資訊

        Returns:
            統計字典
        """
        return {
            'active_messages': len(self.history),
            'archived_messages': self.archived_count,
            'total_messages': len(self.history) + self.archived_count,
            'max_history': self.max_history,
            'archive_file': self.archive_file
        }

    def search(self, keyword: str, role: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        搜尋對話記錄

        Args:
            keyword: 搜尋關鍵字
            role: 篩選角色 ("user", "assistant", "system"),None=所有角色
            limit: 最大返回數量

        Returns:
            符合條件的訊息列表
        """
        results = []
        keyword_lower = keyword.lower()

        # 搜尋活躍歷史
        for msg in self.history:
            if len(results) >= limit:
                break

            # 角色篩選
            if role and msg.get('role') != role:
                continue

            # 關鍵字搜尋
            content = msg.get('content', '')
            if isinstance(content, str) and keyword_lower in content.lower():
                results.append(msg.copy())

        # 如果還需要更多結果,搜尋存檔
        if len(results) < limit and os.path.exists(self.archive_file):
            try:
                with open(self.archive_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if len(results) >= limit:
                            break

                        try:
                            msg = json.loads(line.strip())

                            # 角色篩選
                            if role and msg.get('role') != role:
                                continue

                            # 關鍵字搜尋
                            content = msg.get('content', '')
                            if isinstance(content, str) and keyword_lower in content.lower():
                                results.append(msg)
                        except json.JSONDecodeError:
                            continue

            except Exception as e:
                logger.error(f"搜尋存檔失敗：{e}")

        logger.info(f"搜尋 '{keyword}' 找到 {len(results)} 條結果")
        return results

    def export_to_json(self, output_path: str, include_archived: bool = True) -> bool:
        """
        匯出對話記錄為 JSON 格式

        Args:
            output_path: 輸出檔案路徑
            include_archived: 是否包含已存檔的對話

        Returns:
            是否成功
        """
        try:
            export_data = {
                'metadata': {
                    'export_time': datetime.now().isoformat(),
                    'total_messages': len(self.history) + (self.archived_count if include_archived else 0),
                    'active_messages': len(self.history),
                    'archived_messages': self.archived_count if include_archived else 0
                },
                'conversations': []
            }

            # 匯出活躍對話
            export_data['conversations'].extend(self.history)

            # 匯出存檔對話
            if include_archived and os.path.exists(self.archive_file):
                with open(self.archive_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            msg = json.loads(line.strip())
                            export_data['conversations'].append(msg)
                        except json.JSONDecodeError:
                            continue

            # 寫入檔案
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logger.info(f"已匯出 {len(export_data['conversations'])} 條對話到 {output_path}")
            return True

        except Exception as e:
            logger.error(f"匯出對話失敗：{e}")
            return False

    def export_to_markdown(self, output_path: str, include_archived: bool = True) -> bool:
        """
        匯出對話記錄為 Markdown 格式

        Args:
            output_path: 輸出檔案路徑
            include_archived: 是否包含已存檔的對話

        Returns:
            是否成功
        """
        try:
            messages = []

            # 收集活躍對話
            messages.extend(self.history)

            # 收集存檔對話
            if include_archived and os.path.exists(self.archive_file):
                with open(self.archive_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            msg = json.loads(line.strip())
                            messages.append(msg)
                        except json.JSONDecodeError:
                            continue

            # 生成 Markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# 對話記錄\n\n")
                f.write(f"**匯出時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**總訊息數**: {len(messages)}\n\n")
                f.write("---\n\n")

                for i, msg in enumerate(messages, 1):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    timestamp = msg.get('timestamp', 'N/A')

                    # 角色圖示
                    role_icon = {
                        'user': '👤',
                        'assistant': '🤖',
                        'system': '⚙️'
                    }.get(role, '❓')

                    f.write(f"## {i}. {role_icon} {role.title()}\n\n")
                    f.write(f"**時間**: {timestamp}\n\n")
                    f.write(f"{content}\n\n")
                    f.write("---\n\n")

            logger.info(f"已匯出 {len(messages)} 條對話到 {output_path}")
            return True

        except Exception as e:
            logger.error(f"匯出 Markdown 失敗：{e}")
            return False
