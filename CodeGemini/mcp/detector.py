#!/usr/bin/env python3
"""
CodeGemini MCP 智慧偵測器
根據使用者輸入或命令自動判斷需要啟動哪個 MCP Server

此模組負責：
1. 分析使用者意圖
2. 偵測關鍵字與模式
3. 自動判斷需要的 MCP Server
4. 管理 Server 生命週期（啟動/關閉）
"""

import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class DetectionRule:
    """偵測規則"""
    server_name: str
    keywords: List[str]  # 關鍵字列表
    patterns: List[str]  # 正則表達式模式
    confidence: float  # 信心度（0-1）
    description: str


class MCPServerDetector:
    """
    MCP Server 智慧偵測器

    根據使用者輸入自動判斷需要啟動哪個 MCP Server
    """

    def __init__(self):
        """初始化偵測器"""
        self.rules: List[DetectionRule] = []
        self._load_default_rules()

    def _load_default_rules(self):
        """載入預設偵測規則"""

        # PostgreSQL 偵測規則
        self.rules.append(DetectionRule(
            server_name="postgres",
            keywords=[
                "資料庫", "database", "sql", "查詢", "query",
                "postgresql", "postgres", "pg",
                "資料表", "table", "欄位", "column",
                "新增資料", "刪除資料", "更新資料",
                "insert", "delete", "update", "select"
            ],
            patterns=[
                r"SELECT\s+.*\s+FROM",
                r"INSERT\s+INTO",
                r"UPDATE\s+.*\s+SET",
                r"DELETE\s+FROM",
                r"CREATE\s+TABLE",
                r"postgresql://",
                r"連接.*資料庫",
                r"查詢.*資料",
                r"^SELECT\s",  # SQL 查詢開頭
            ],
            confidence=0.9,
            description="PostgreSQL 資料庫操作"
        ))

        # Puppeteer 偵測規則
        self.rules.append(DetectionRule(
            server_name="puppeteer",
            keywords=[
                "網頁", "網站", "爬蟲", "抓取", "擷取",
                "screenshot", "截圖", "螢幕截圖",
                "瀏覽器", "browser", "chrome", "chromium",
                "自動化", "automation", "scrape", "crawl",
                "網頁內容", "html", "dom", "元素",
                "點擊", "click", "輸入", "填寫表單"
            ],
            patterns=[
                r"打開.*網頁",
                r"前往.*網站",
                r"擷取.*網頁",
                r"抓取.*資料",
                r"截圖.*網頁",
                r"螢幕截圖",
                r"https?://",
                r"瀏覽.*網站",
                r"自動化.*瀏覽器",
                r"網頁.*截圖"
            ],
            confidence=0.85,
            description="網頁自動化與爬蟲"
        ))

        # Slack 偵測規則
        self.rules.append(DetectionRule(
            server_name="slack",
            keywords=[
                "slack", "發送訊息", "傳訊息",
                "頻道", "channel", "私訊", "dm",
                "工作區", "workspace", "團隊", "team",
                "通知", "notification", "提醒",
                "上傳檔案", "分享檔案"
            ],
            patterns=[
                r"發送.*slack",
                r"傳送.*訊息.*給",
                r"在.*頻道.*發布",
                r"通知.*團隊",
                r"slack.*訊息",
                r"@\w+",  # Slack mention
                r"Slack\s*上.*通知",
                r"在\s*Slack"
            ],
            confidence=0.9,
            description="Slack 團隊協作"
        ))

        # Google Drive 偵測規則
        self.rules.append(DetectionRule(
            server_name="google-drive",
            keywords=[
                "google drive", "drive", "雲端硬碟",
                "上傳", "下載", "分享", "共享",
                "文件", "試算表", "簡報",
                "資料夾", "folder", "檔案",
                "gdrive", "google文件"
            ],
            patterns=[
                r"上傳.*drive",
                r"從.*drive.*下載",
                r"分享.*檔案",
                r"google\s*drive",
                r"雲端硬碟",
                r"共享.*文件"
            ],
            confidence=0.85,
            description="Google Drive 檔案管理"
        ))

    def detect(self, user_input: str, threshold: float = 0.6) -> List[Dict[str, any]]:
        """
        偵測使用者輸入需要哪些 MCP Server

        Args:
            user_input: 使用者輸入文字
            threshold: 信心度閾值（0-1），預設 0.6

        Returns:
            List[Dict]: 偵測結果列表，包含 server_name, confidence, reason
        """
        results = []
        user_input_lower = user_input.lower()

        for rule in self.rules:
            score = 0.0
            matched_keywords = []
            matched_patterns = []

            # 檢查關鍵字
            for keyword in rule.keywords:
                if keyword.lower() in user_input_lower:
                    score += 0.15
                    matched_keywords.append(keyword)

            # 檢查正則表達式模式
            for pattern in rule.patterns:
                if re.search(pattern, user_input, re.IGNORECASE):
                    score += 0.4
                    matched_patterns.append(pattern)

            # 計算最終信心度（至少要有一個關鍵字或模式匹配）
            if matched_keywords or matched_patterns:
                final_confidence = min(score * rule.confidence, 1.0)
            else:
                final_confidence = 0.0

            # 如果超過閾值，加入結果
            if final_confidence >= threshold:
                results.append({
                    "server_name": rule.server_name,
                    "confidence": final_confidence,
                    "description": rule.description,
                    "matched_keywords": matched_keywords[:3],  # 只顯示前 3 個
                    "matched_patterns": len(matched_patterns),
                    "reason": self._generate_reason(rule, matched_keywords, matched_patterns)
                })

        # 依信心度排序
        results.sort(key=lambda x: x["confidence"], reverse=True)

        return results

    def _generate_reason(self, rule: DetectionRule, keywords: List[str], patterns: List[str]) -> str:
        """生成偵測理由說明"""
        reasons = []

        if keywords:
            reasons.append(f"包含關鍵字：{', '.join(keywords[:3])}")

        if patterns:
            reasons.append(f"匹配 {len(patterns)} 個模式")

        return " | ".join(reasons) if reasons else "符合規則"

    def add_custom_rule(self, rule: DetectionRule):
        """新增自訂偵測規則"""
        self.rules.append(rule)
        console.print(f"[green]✓ 已新增自訂規則：{rule.server_name}[/green]")

    def remove_rule(self, server_name: str):
        """移除指定 Server 的規則"""
        self.rules = [r for r in self.rules if r.server_name != server_name]
        console.print(f"[yellow]✓ 已移除規則：{server_name}[/yellow]")

    def list_rules(self):
        """列出所有偵測規則"""
        console.print("\n[bold cyan]📋 MCP Server 偵測規則列表[/bold cyan]\n")

        for i, rule in enumerate(self.rules, 1):
            console.print(f"[cyan]{i}. {rule.server_name}[/cyan]")
            console.print(f"   說明：{rule.description}")
            console.print(f"   關鍵字數量：{len(rule.keywords)}")
            console.print(f"   模式數量：{len(rule.patterns)}")
            console.print(f"   信心度權重：{rule.confidence}")
            console.print()


# ==================== 使用範例 ====================

def demo():
    """示範偵測器使用"""
    detector = MCPServerDetector()

    test_cases = [
        "請查詢資料庫中所有使用者的資料",
        "幫我抓取 https://example.com 的網頁內容",
        "發送訊息到 Slack #general 頻道通知團隊",
        "上傳這個檔案到 Google Drive 並分享給團隊",
        "SELECT * FROM users WHERE age > 18",
        "截圖這個網頁並儲存",
        "在 Slack 上通知大家會議時間",
        "從雲端硬碟下載最新的簡報檔案"
    ]

    console.print("[bold magenta]🔍 MCP Server 智慧偵測器示範[/bold magenta]\n")

    for i, test_input in enumerate(test_cases, 1):
        console.print(f"[bold]測試 {i}:[/bold] {test_input}")
        results = detector.detect(test_input)

        if results:
            console.print(f"[green]✓ 偵測到 {len(results)} 個相關 Server：[/green]")
            for result in results:
                console.print(f"  • {result['server_name']} "
                            f"(信心度: {result['confidence']:.2f}) - {result['reason']}")
        else:
            console.print("[dim]✗ 未偵測到需要的 MCP Server[/dim]")

        console.print()


if __name__ == "__main__":
    demo()
