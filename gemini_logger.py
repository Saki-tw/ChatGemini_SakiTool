#!/usr/bin/env python3
"""
Gemini 對話日誌記錄器
從 gemini_chat.py 抽離
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# 從配置取得預設日誌目錄
try:
    from config import OUTPUT_DIRS
    DEFAULT_LOG_DIR = str(OUTPUT_DIRS.get('chat_logs', Path.cwd() / 'ChatLogs'))
except ImportError:
    DEFAULT_LOG_DIR = str(Path.cwd() / 'ChatLogs')

# 導入對話管理器（如果可用）
try:
    from gemini_conversation import ConversationManager
except ImportError:
    logger.warning("ConversationManager 不可用，使用簡化版對話記錄")
    ConversationManager = None



class ChatLogger:
    """
    對話記錄管理器 - 優化版

    改良重點：
    - 使用持久檔案句柄，避免重複開啟/關閉檔案（減少 OS 系統呼叫）
    - 使用緩衝區，批次寫入（降低 I/O 次數）
    - 避免長時間會話中的檔案句柄耗盡問題
    """

    def __init__(self, log_dir: str = DEFAULT_LOG_DIR):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.session_start = datetime.now()
        self.session_file = os.path.join(
            log_dir,
            f"conversation_{self.session_start.strftime('%Y%m%d_%H%M%S')}.txt"
        )
        # JSON 記錄檔案（包含思考過程）
        self.json_file = os.path.join(
            log_dir,
            f"conversation_{self.session_start.strftime('%Y%m%d_%H%M%S')}.json"
        )
        self.model_name = None

        # 🔧 記憶體洩漏修復：使用 ConversationManager 管理對話歷史
        if ConversationManager:
            self.conversation_manager = ConversationManager(max_history=100, archive_dir=log_dir)
        else:
            self.conversation_manager = None

        # 優化：保持檔案句柄開啟，使用 64KB 緩衝區
        self._log_file_handle = open(self.session_file, 'a', encoding='utf-8', buffering=64*1024)
        self._buffer = []  # 記錄緩衝區
        self._buffer_size = 10  # 每 10 條訊息刷新一次

        logger.info(f"對話記錄將儲存至：{self.session_file}")

    def set_model(self, model_name: str):
        """設定當前使用的模型"""
        self.model_name = model_name
        self._log_message("SYSTEM", f"使用模型: {model_name}")
        # 🔧 使用 ConversationManager
        if self.conversation_manager:
            self.conversation_manager.add_message({
                "role": "system",
                "content": f"使用模型: {model_name}",
                "timestamp": datetime.now().isoformat()
            })

    def log_user(self, message: str):
        """記錄使用者訊息"""
        self._log_message("USER", message)
        # 🔧 使用 ConversationManager
        if self.conversation_manager:
            self.conversation_manager.add_message({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })

    def log_assistant(self, message: str, thinking_process: Optional[str] = None):
        """
        記錄助手回應

        Args:
            message: 助手回應內容
            thinking_process: 思考過程（可選）
        """
        self._log_message("ASSISTANT", message)

        # 如果有思考過程，也記錄到文字檔
        if thinking_process:
            self._log_message("THINKING", thinking_process)

        # 記錄到 JSON（包含思考過程）
        entry = {
            "role": "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        if thinking_process:
            entry["thinking_process"] = thinking_process

        # 🔧 使用 ConversationManager
        if self.conversation_manager:
            self.conversation_manager.add_message(entry)

    def _log_message(self, role: str, message: str):
        """內部記錄方法 - 優化：使用緩衝區批次寫入"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"\n[{timestamp}] {role}:\n{message}\n" + "-" * 80 + "\n"
            self._buffer.append(log_entry)

            # 達到緩衝大小時自動刷新
            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()
        except Exception as e:
            logger.error(f"記錄失敗：{e}")

    def _flush_buffer(self):
        """刷新緩衝區到檔案"""
        if self._buffer:
            try:
                self._log_file_handle.writelines(self._buffer)
                self._log_file_handle.flush()  # 確保立即寫入磁碟
                self._buffer.clear()
            except Exception as e:
                logger.error(f"刷新緩衝區失敗：{e}")

    def save_session(self):
        """儲存會話（同時儲存文字和 JSON）- 優化：先刷新緩衝區"""
        # 優化：確保所有未寫入的記錄都刷新到檔案
        self._flush_buffer()

        # 儲存 JSON
        try:
            # 🔧 從 ConversationManager 獲取活躍對話歷史
            with open(self.json_file, 'w', encoding='utf-8') as f:
                data = {
                    "session_start": self.session_start.isoformat(),
                    "model": self.model_name
                }
                if self.conversation_manager:
                    data["conversation"] = self.conversation_manager.get_recent_history()
                    data["stats"] = self.conversation_manager.get_stats()
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON 記錄已儲存至：{self.json_file}")
        except Exception as e:
            logger.error(f"JSON 儲存失敗：{e}")

        logger.info(f"對話已儲存至：{self.session_file}")

    def __del__(self):
        """清理：關閉檔案句柄"""
        if hasattr(self, '_log_file_handle') and self._log_file_handle:
            try:
                self._flush_buffer()  # 最後一次刷新
                self._log_file_handle.close()
            except Exception:
                pass
