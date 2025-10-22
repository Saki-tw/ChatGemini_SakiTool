#!/usr/bin/env python3
"""
Gemini Conversation Suggestion Module
相關對話建議功能 - 自動顯示相關歷史對話

功能：
- 自動搜尋相關歷史對話
- 顯示最相關的建議
- 整合到 Gemini Chat CLI
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
except ImportError:
    print("❌ 需要安裝 rich：pip install rich")
    sys.exit(1)

# 檢查 CodebaseEmbedding 是否可用
try:
    sys.path.insert(0, str(Path(__file__).parent / "CodeGemini"))
    from codebase_embedding import CodebaseEmbedding
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    print("⚠️  CodebaseEmbedding 不可用，相關對話建議功能將被停用")

console = Console()


class ConversationSuggestion:
    """相關對話建議管理器"""

    def __init__(
        self,
        embedding: Optional[CodebaseEmbedding] = None,
        enabled: bool = True,
        top_k: int = 3,
        min_similarity: float = 0.7
    ):
        """初始化對話建議管理器

        Args:
            embedding: CodebaseEmbedding 實例（若未提供則自動建立）
            enabled: 是否啟用建議功能
            top_k: 顯示前 k 個相關對話
            min_similarity: 最小相似度閾值（0-1）
        """
        self.enabled = enabled
        self.top_k = top_k
        self.min_similarity = min_similarity

        if EMBEDDING_AVAILABLE:
            self.embedding = embedding or CodebaseEmbedding(
                vector_db_path=".embeddings/conversations.db"
            )
        else:
            self.embedding = None
            self.enabled = False

    def add_conversation(
        self,
        question: str,
        answer: str,
        session_id: Optional[str] = None
    ) -> bool:
        """儲存對話記錄

        Args:
            question: 使用者問題
            answer: AI 回答
            session_id: 對話 Session ID

        Returns:
            成功返回 True
        """
        if not self.enabled or not self.embedding:
            return False

        try:
            timestamp = datetime.now().isoformat()
            chunk_id = self.embedding.add_conversation(
                question=question,
                answer=answer,
                timestamp=timestamp,
                session_id=session_id
            )
            return bool(chunk_id)
        except Exception as e:
            console.print(f"[yellow]⚠️  儲存對話失敗：{e}[/yellow]")
            return False

    def get_suggestions(
        self,
        current_question: str,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """獲取相關對話建議

        Args:
            current_question: 當前使用者問題
            session_id: 當前 Session ID（可選）

        Returns:
            相關對話列表
        """
        if not self.enabled or not self.embedding:
            return []

        try:
            # 搜尋相關對話
            results = self.embedding.search_conversations(
                query=current_question,
                top_k=self.top_k,
                session_id=None  # 搜尋所有 session
            )

            # 過濾低相似度結果
            filtered_results = [
                r for r in results
                if r.get('similarity', 0) >= self.min_similarity
            ]

            return filtered_results
        except Exception as e:
            console.print(f"[yellow]⚠️  搜尋對話失敗：{e}[/yellow]")
            return []

    def display_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        show_full: bool = False
    ):
        """顯示對話建議

        Args:
            suggestions: 建議列表
            show_full: 是否顯示完整對話
        """
        if not suggestions:
            return

        console.print("\n[bold cyan]💡 相關歷史對話建議[/bold cyan]")

        if show_full:
            # 完整模式：顯示完整對話內容
            for i, sug in enumerate(suggestions, 1):
                similarity = sug.get('similarity', 0)
                question = sug.get('question', '')
                answer = sug.get('answer', '')
                timestamp = sug.get('timestamp', '')

                panel_content = f"""**問題：**
{question}

**回答：**
{answer}

**時間：** {timestamp}
**相似度：** {similarity:.1%}"""

                console.print(Panel(
                    panel_content,
                    title=f"[bold]建議 {i}[/bold]",
                    border_style="cyan"
                ))
        else:
            # 簡潔模式：表格顯示摘要
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="cyan", width=3)
            table.add_column("問題", style="white")
            table.add_column("回答摘要", style="dim")
            table.add_column("相似度", style="green", width=10)

            for i, sug in enumerate(suggestions, 1):
                similarity = sug.get('similarity', 0)
                question = sug.get('question', '')[:50]
                answer = sug.get('answer', '')[:80]

                # 添加省略號
                if len(sug.get('question', '')) > 50:
                    question += "..."
                if len(sug.get('answer', '')) > 80:
                    answer += "..."

                table.add_row(
                    str(i),
                    question,
                    answer,
                    f"{similarity:.1%}"
                )

            console.print(table)
            console.print("[dim]輸入 /show_suggestion <編號> 查看完整對話[/dim]\n")

    def enable(self):
        """啟用建議功能"""
        if EMBEDDING_AVAILABLE:
            self.enabled = True
            console.print("[green]✓ 相關對話建議功能已啟用[/green]")
        else:
            console.print("[yellow]⚠️  CodebaseEmbedding 不可用[/yellow]")

    def disable(self):
        """停用建議功能"""
        self.enabled = False
        console.print("[yellow]✓ 相關對話建議功能已停用[/yellow]")

    def get_status(self) -> str:
        """獲取狀態"""
        if not EMBEDDING_AVAILABLE:
            return "不可用（缺少 CodebaseEmbedding）"
        if self.enabled:
            return f"已啟用（top_k={self.top_k}, min_sim={self.min_similarity:.2f}）"
        return "已停用"


# ===== 測試程式碼 =====

def test_conversation_suggestion():
    """測試對話建議功能"""
    console.print("\n[bold cyan]🧪 測試相關對話建議功能[/bold cyan]\n")

    # 建立實例
    suggestion = ConversationSuggestion(enabled=True)

    if not suggestion.enabled:
        console.print("[yellow]⚠️  功能不可用，測試中止[/yellow]")
        return

    # 測試 1：新增測試對話
    console.print("[bold]測試 1：新增測試對話[/bold]")
    test_conversations = [
        ("如何使用 Python 讀取 CSV 檔案？", "使用 pandas.read_csv() 方法可以輕鬆讀取 CSV 檔案..."),
        ("Python 如何處理例外？", "使用 try-except 語句來捕獲和處理例外..."),
        ("如何建立 Python 虛擬環境？", "使用 python -m venv 命令來建立虛擬環境..."),
    ]

    for q, a in test_conversations:
        success = suggestion.add_conversation(q, a, session_id="test_session")
        console.print(f"{'✓' if success else '✗'} 新增對話：{q[:30]}...")

    # 測試 2：搜尋相關對話
    console.print("\n[bold]測試 2：搜尋相關對話[/bold]")
    query = "Python 讀取 CSV 的方法"
    suggestions = suggestion.get_suggestions(query)
    console.print(f"查詢：{query}")
    console.print(f"找到 {len(suggestions)} 個相關對話\n")

    # 測試 3：顯示建議（簡潔模式）
    console.print("[bold]測試 3：顯示建議（簡潔模式）[/bold]")
    suggestion.display_suggestions(suggestions, show_full=False)

    # 測試 4：顯示建議（完整模式）
    console.print("\n[bold]測試 4：顯示建議（完整模式）[/bold]")
    if suggestions:
        suggestion.display_suggestions(suggestions[:1], show_full=True)

    console.print("\n[green]✅ 測試完成[/green]")


if __name__ == "__main__":
    test_conversation_suggestion()
