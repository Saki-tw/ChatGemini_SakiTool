#!/usr/bin/env python3
"""
CodeGemini Task Planning Module
任務規劃模組 - Agent Mode 核心元件

此模組負責：
1. 分析使用者請求
2. 掃描程式碼庫上下文
3. 生成執行計畫
4. 展示計畫供批准
"""
import os
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from google import genai

console = Console()


class TaskType(Enum):
    """任務類型"""
    FEATURE = "feature"          # 新功能開發
    BUGFIX = "bugfix"            # 錯誤修復
    REFACTOR = "refactor"        # 重構
    OPTIMIZATION = "optimization" # 優化
    DOCUMENTATION = "documentation" # 文檔
    TEST = "test"                # 測試
    OTHER = "other"              # 其他


class RiskLevel(Enum):
    """風險等級"""
    LOW = "low"          # 低風險（新增檔案、文檔）
    MEDIUM = "medium"    # 中風險（修改檔案、重構）
    HIGH = "high"        # 高風險（核心邏輯、刪除檔案）


@dataclass
class FileChange:
    """檔案變更資訊"""
    file_path: str                 # 檔案路徑
    action: str                    # 動作：create, modify, delete
    description: str               # 變更描述
    estimated_lines: int = 0       # 預估變更行數
    dependencies: List[str] = field(default_factory=list)  # 依賴的其他檔案


@dataclass
class ExecutionStep:
    """執行步驟"""
    step_number: int               # 步驟編號
    description: str               # 步驟描述
    file_changes: List[FileChange] # 涉及的檔案變更
    estimated_time: str            # 預估時間
    dependencies: List[int] = field(default_factory=list)  # 依賴的步驟編號


@dataclass
class ExecutionPlan:
    """執行計畫"""
    task_type: TaskType            # 任務類型
    task_summary: str              # 任務摘要
    risk_level: RiskLevel          # 風險等級
    steps: List[ExecutionStep]     # 執行步驟
    affected_files: List[str]      # 受影響的檔案
    estimated_total_time: str      # 預估總時間
    considerations: List[str] = field(default_factory=list)  # 注意事項


@dataclass
class CodebaseContext:
    """程式碼庫上下文"""
    project_path: str              # 專案路徑
    project_type: str              # 專案類型（Python, JavaScript, etc.）
    framework: Optional[str] = None  # 使用的框架（Flask, React, etc.）
    file_count: int = 0            # 檔案數量
    relevant_files: List[str] = field(default_factory=list)  # 相關檔案
    dependencies: Dict[str, str] = field(default_factory=dict)  # 依賴套件
    existing_features: List[str] = field(default_factory=list)  # 現有功能


@dataclass
class TaskAnalysis:
    """任務分析結果"""
    user_request: str              # 原始請求
    intent: str                    # 意圖解析
    task_type: TaskType            # 任務類型
    complexity: str                # 複雜度（simple, medium, complex）
    required_files: List[str]      # 需要的檔案
    keywords: List[str] = field(default_factory=list)  # 關鍵字


class TaskPlanner:
    """任務規劃器"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化任務規劃器

        Args:
            api_key: Gemini API Key，若為 None 則從環境變數讀取
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise RuntimeError("請設置 GEMINI_API_KEY 環境變數")

        self.client = genai.Client(api_key=self.api_key)
        self.model = 'gemini-2.0-flash-exp'  # 使用最新的 Flash 模型

    def analyze_request(self, user_request: str) -> TaskAnalysis:
        """
        分析使用者請求

        Args:
            user_request: 使用者的原始請求

        Returns:
            TaskAnalysis: 任務分析結果
        """
        console.print(f"\n[cyan]🔍 分析使用者請求...[/cyan]")

        # 使用 Gemini 分析請求
        prompt = f"""你是一個專業的程式碼分析助手。請分析以下使用者請求：

「{user_request}」

請以 JSON 格式回應，包含以下欄位：
{{
  "intent": "使用者意圖的簡潔描述",
  "task_type": "feature/bugfix/refactor/optimization/documentation/test/other",
  "complexity": "simple/medium/complex",
  "required_files": ["可能涉及的檔案路徑列表"],
  "keywords": ["關鍵技術關鍵字"]
}}

只需回傳 JSON，不要有其他說明文字。"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            # 解析回應
            response_text = response.text.strip()

            # 移除可能的 markdown 標記
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()
            data = json.loads(response_text)

            # 構建 TaskAnalysis
            analysis = TaskAnalysis(
                user_request=user_request,
                intent=data.get('intent', '未知意圖'),
                task_type=TaskType(data.get('task_type', 'other')),
                complexity=data.get('complexity', 'medium'),
                required_files=data.get('required_files', []),
                keywords=data.get('keywords', [])
            )

            console.print(f"  [green]✓ 分析完成[/green]")
            console.print(f"  意圖：{analysis.intent}")
            console.print(f"  類型：{analysis.task_type.value}")
            console.print(f"  複雜度：{analysis.complexity}")

            return analysis

        except Exception as e:
            console.print(f"[yellow]警告：Gemini 分析失敗，使用備用分析 - {e}[/yellow]")

            # 備用：簡單的啟發式分析
            return self._fallback_analysis(user_request)

    def _fallback_analysis(self, user_request: str) -> TaskAnalysis:
        """備用分析方法（當 Gemini API 失敗時）"""
        # 簡單的關鍵字匹配
        request_lower = user_request.lower()

        if any(word in request_lower for word in ['add', 'create', 'implement', 'build', '新增', '創建', '實作']):
            task_type = TaskType.FEATURE
        elif any(word in request_lower for word in ['fix', 'bug', 'error', '修復', '錯誤']):
            task_type = TaskType.BUGFIX
        elif any(word in request_lower for word in ['refactor', 'restructure', '重構']):
            task_type = TaskType.REFACTOR
        elif any(word in request_lower for word in ['optimize', 'improve', '優化']):
            task_type = TaskType.OPTIMIZATION
        elif any(word in request_lower for word in ['test', '測試']):
            task_type = TaskType.TEST
        elif any(word in request_lower for word in ['document', 'doc', '文檔']):
            task_type = TaskType.DOCUMENTATION
        else:
            task_type = TaskType.OTHER

        return TaskAnalysis(
            user_request=user_request,
            intent=user_request,
            task_type=task_type,
            complexity='medium',
            required_files=[],
            keywords=[]
        )

    def scan_codebase(self, project_path: str, analysis: TaskAnalysis) -> CodebaseContext:
        """
        掃描程式碼庫（簡化版本，完整版本在 scanner.py）

        Args:
            project_path: 專案路徑
            analysis: 任務分析結果

        Returns:
            CodebaseContext: 程式碼庫上下文
        """
        console.print(f"\n[cyan]📂 掃描程式碼庫...[/cyan]")

        if not os.path.isdir(project_path):
            raise ValueError(f"專案路徑不存在：{project_path}")

        # 簡單的檔案掃描
        python_files = []
        for root, dirs, files in os.walk(project_path):
            # 忽略常見的目錄
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'venv', 'node_modules', '.venv']]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))

        # 檢測專案類型
        project_type = "Python"  # 目前只支援 Python

        # 檢測框架（簡化版）
        framework = None
        if any('flask' in f.lower() for f in python_files):
            framework = "Flask"
        elif any('django' in f.lower() for f in python_files):
            framework = "Django"

        context = CodebaseContext(
            project_path=project_path,
            project_type=project_type,
            framework=framework,
            file_count=len(python_files),
            relevant_files=python_files[:10],  # 取前 10 個檔案
        )

        console.print(f"  [green]✓ 掃描完成[/green]")
        console.print(f"  專案類型：{context.project_type}")
        console.print(f"  檔案數量：{context.file_count}")
        if context.framework:
            console.print(f"  框架：{context.framework}")

        return context

    def generate_plan(
        self,
        user_request: str,
        analysis: TaskAnalysis,
        context: CodebaseContext
    ) -> ExecutionPlan:
        """
        生成執行計畫

        Args:
            user_request: 使用者請求
            analysis: 任務分析結果
            context: 程式碼庫上下文

        Returns:
            ExecutionPlan: 執行計畫
        """
        console.print(f"\n[cyan]📋 生成執行計畫...[/cyan]")

        # 使用 Gemini 生成詳細計畫
        prompt = f"""你是一個專業的軟體開發規劃師。請為以下任務生成執行計畫：

任務請求：「{user_request}」

任務分析：
- 意圖：{analysis.intent}
- 類型：{analysis.task_type.value}
- 複雜度：{analysis.complexity}

專案上下文：
- 專案類型：{context.project_type}
- 框架：{context.framework or '無'}
- 檔案數量：{context.file_count}

請生成執行計畫，以 JSON 格式回應：
{{
  "task_summary": "任務摘要（1-2 句話）",
  "risk_level": "low/medium/high",
  "estimated_total_time": "預估總時間（如：2-3 小時）",
  "steps": [
    {{
      "step_number": 1,
      "description": "步驟描述",
      "file_changes": [
        {{
          "file_path": "檔案路徑",
          "action": "create/modify/delete",
          "description": "變更描述",
          "estimated_lines": 50
        }}
      ],
      "estimated_time": "預估時間"
    }}
  ],
  "affected_files": ["受影響的檔案列表"],
  "considerations": ["注意事項列表"]
}}

只需回傳 JSON，不要有其他說明文字。"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            # 解析回應
            response_text = response.text.strip()

            # 移除可能的 markdown 標記
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()
            data = json.loads(response_text)

            # 構建 ExecutionPlan
            steps = []
            for step_data in data.get('steps', []):
                file_changes = [
                    FileChange(
                        file_path=fc.get('file_path', ''),
                        action=fc.get('action', 'modify'),
                        description=fc.get('description', ''),
                        estimated_lines=fc.get('estimated_lines', 0)
                    )
                    for fc in step_data.get('file_changes', [])
                ]

                steps.append(ExecutionStep(
                    step_number=step_data.get('step_number', 0),
                    description=step_data.get('description', ''),
                    file_changes=file_changes,
                    estimated_time=step_data.get('estimated_time', '未知')
                ))

            plan = ExecutionPlan(
                task_type=analysis.task_type,
                task_summary=data.get('task_summary', analysis.intent),
                risk_level=RiskLevel(data.get('risk_level', 'medium')),
                steps=steps,
                affected_files=data.get('affected_files', []),
                estimated_total_time=data.get('estimated_total_time', '未知'),
                considerations=data.get('considerations', [])
            )

            console.print(f"  [green]✓ 計畫生成完成[/green]")
            console.print(f"  步驟數量：{len(plan.steps)}")
            console.print(f"  風險等級：{plan.risk_level.value}")

            return plan

        except Exception as e:
            console.print(f"[yellow]警告：Gemini 計畫生成失敗，使用備用計畫 - {e}[/yellow]")

            # 備用：生成簡單計畫
            return self._fallback_plan(analysis)

    def _fallback_plan(self, analysis: TaskAnalysis) -> ExecutionPlan:
        """備用計畫生成方法"""
        # 生成簡單的單步計畫
        step = ExecutionStep(
            step_number=1,
            description=f"執行任務：{analysis.intent}",
            file_changes=[],
            estimated_time="未知"
        )

        return ExecutionPlan(
            task_type=analysis.task_type,
            task_summary=analysis.intent,
            risk_level=RiskLevel.MEDIUM,
            steps=[step],
            affected_files=[],
            estimated_total_time="未知",
            considerations=["請手動檢查變更"]
        )

    def present_plan(self, plan: ExecutionPlan) -> str:
        """
        展示執行計畫（使用 Rich 格式化）

        Args:
            plan: 執行計畫

        Returns:
            str: 格式化的計畫文字（用於記錄）
        """
        console.print("\n" + "=" * 70)
        console.print(Panel.fit(
            f"[bold cyan]執行計畫[/bold cyan]\n\n"
            f"[bold]任務類型：[/bold]{plan.task_type.value}\n"
            f"[bold]風險等級：[/bold]{plan.risk_level.value}\n"
            f"[bold]預估時間：[/bold]{plan.estimated_total_time}",
            title="CodeGemini Agent Mode",
            border_style="cyan"
        ))

        console.print(f"\n[bold cyan]任務摘要：[/bold cyan]")
        console.print(f"  {plan.task_summary}")

        # 執行步驟
        console.print(f"\n[bold cyan]執行步驟：[/bold cyan]")
        for step in plan.steps:
            console.print(f"\n  [bold]步驟 {step.step_number}：[/bold]{step.description}")
            console.print(f"    預估時間：{step.estimated_time}")

            if step.file_changes:
                console.print(f"    檔案變更：")
                for fc in step.file_changes:
                    action_emoji = {
                        'create': '✨',
                        'modify': '✏️',
                        'delete': '🗑️'
                    }.get(fc.action, '📝')
                    console.print(f"      {action_emoji} {fc.action}: {fc.file_path}")
                    console.print(f"         {fc.description}")

        # 受影響的檔案
        if plan.affected_files:
            console.print(f"\n[bold cyan]受影響的檔案：[/bold cyan]")
            for file in plan.affected_files[:10]:  # 只顯示前 10 個
                console.print(f"  - {file}")
            if len(plan.affected_files) > 10:
                console.print(f"  ... 以及 {len(plan.affected_files) - 10} 個其他檔案")

        # 注意事項
        if plan.considerations:
            console.print(f"\n[bold yellow]注意事項：[/bold yellow]")
            for i, note in enumerate(plan.considerations, 1):
                console.print(f"  {i}. {note}")

        console.print("\n" + "=" * 70)

        # 返回純文字版本（用於記錄）
        return self._plan_to_text(plan)

    def _plan_to_text(self, plan: ExecutionPlan) -> str:
        """將計畫轉換為純文字"""
        lines = [
            "=" * 70,
            "執行計畫",
            "=" * 70,
            f"任務類型：{plan.task_type.value}",
            f"風險等級：{plan.risk_level.value}",
            f"預估時間：{plan.estimated_total_time}",
            "",
            "任務摘要：",
            f"  {plan.task_summary}",
            "",
            "執行步驟："
        ]

        for step in plan.steps:
            lines.append(f"\n步驟 {step.step_number}：{step.description}")
            lines.append(f"  預估時間：{step.estimated_time}")

            if step.file_changes:
                lines.append("  檔案變更：")
                for fc in step.file_changes:
                    lines.append(f"    {fc.action}: {fc.file_path}")
                    lines.append(f"      {fc.description}")

        if plan.affected_files:
            lines.append("\n受影響的檔案：")
            for file in plan.affected_files:
                lines.append(f"  - {file}")

        if plan.considerations:
            lines.append("\n注意事項：")
            for i, note in enumerate(plan.considerations, 1):
                lines.append(f"  {i}. {note}")

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)

    def create_plan(
        self,
        user_request: str,
        project_path: Optional[str] = None
    ) -> ExecutionPlan:
        """
        一鍵生成完整計畫（組合所有步驟）

        Args:
            user_request: 使用者請求
            project_path: 專案路徑（選用）

        Returns:
            ExecutionPlan: 完整的執行計畫
        """
        # 步驟 1：分析請求
        analysis = self.analyze_request(user_request)

        # 步驟 2：掃描程式碼庫（如果提供路徑）
        if project_path:
            context = self.scan_codebase(project_path, analysis)
        else:
            # 使用空上下文
            context = CodebaseContext(
                project_path=".",
                project_type="Unknown",
                file_count=0
            )

        # 步驟 3：生成計畫
        plan = self.generate_plan(user_request, analysis, context)

        # 步驟 4：展示計畫
        self.present_plan(plan)

        return plan


def main():
    """測試用主程式"""
    import sys

    if len(sys.argv) < 2:
        console.print("[cyan]用法：[/cyan]")
        console.print('  python task_planner.py "任務描述" [專案路徑]')
        console.print("\n[cyan]範例：[/cyan]")
        console.print('  python task_planner.py "新增使用者登入功能" .')
        sys.exit(1)

    user_request = sys.argv[1]
    project_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        planner = TaskPlanner()
        plan = planner.create_plan(user_request, project_path)

        console.print(f"\n[bold green]✅ 計畫生成成功！[/bold green]")

    except Exception as e:
        console.print(f"\n[red]錯誤：{e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
