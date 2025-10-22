#!/usr/bin/env python3
"""
CodeGemini Approval Workflow Module
批准流程模組 - 互動式確認與執行

此模組負責：
1. 請求使用者批准執行計畫
2. 展示變更預覽
3. 等待使用者確認
4. 執行已批准的計畫
"""
import os
import sys
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

from .task_planner import ExecutionPlan, ExecutionStep, FileChange, RiskLevel

console = Console()


class ApprovalStatus(Enum):
    """批准狀態"""
    PENDING = "pending"       # 等待批准
    APPROVED = "approved"     # 已批准
    REJECTED = "rejected"     # 已拒絕
    CANCELLED = "cancelled"   # 已取消


@dataclass
class ApprovalRequest:
    """批准請求"""
    plan: ExecutionPlan                    # 執行計畫
    request_id: str                        # 請求 ID
    status: ApprovalStatus = ApprovalStatus.PENDING
    user_notes: str = ""                   # 使用者備註


class ApprovalWorkflow:
    """批准流程管理器"""

    def __init__(self):
        """初始化批准流程管理器"""
        self.current_request: Optional[ApprovalRequest] = None

    def request_approval(self, plan: ExecutionPlan) -> ApprovalRequest:
        """
        建立批准請求

        Args:
            plan: 執行計畫

        Returns:
            ApprovalRequest: 批准請求物件
        """
        # 生成請求 ID
        import time
        request_id = f"req_{int(time.time())}"

        request = ApprovalRequest(
            plan=plan,
            request_id=request_id,
            status=ApprovalStatus.PENDING
        )

        self.current_request = request
        return request

    def show_diff_preview(self, changes: List[FileChange]) -> None:
        """
        展示變更預覽

        Args:
            changes: 檔案變更列表
        """
        console.print("\n[bold cyan]📝 變更預覽[/bold cyan]\n")

        # 建立變更表格
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("動作", style="yellow", width=10)
        table.add_column("檔案路徑", style="white")
        table.add_column("變更描述", style="green")
        table.add_column("預估行數", justify="right", style="blue")

        for change in changes:
            action_emoji = {
                'create': '✨ 新增',
                'modify': '✏️  修改',
                'delete': '🗑️  刪除'
            }.get(change.action, '📝 變更')

            table.add_row(
                action_emoji,
                change.file_path,
                change.description,
                str(change.estimated_lines) if change.estimated_lines > 0 else "-"
            )

        console.print(table)

    def show_risk_warning(self, risk_level: RiskLevel) -> None:
        """
        展示風險警告

        Args:
            risk_level: 風險等級
        """
        if risk_level == RiskLevel.HIGH:
            console.print(Panel(
                "[bold red]⚠️  高風險警告 ⚠️[/bold red]\n\n"
                "此操作涉及核心邏輯或刪除檔案，請謹慎確認：\n"
                "• 建議先備份程式碼\n"
                "• 確保已理解所有變更\n"
                "• 可使用版本控制系統回滾",
                border_style="red",
                title="風險評估"
            ))
        elif risk_level == RiskLevel.MEDIUM:
            console.print(Panel(
                "[bold yellow]⚠️  中等風險[/bold yellow]\n\n"
                "此操作會修改現有檔案：\n"
                "• 建議先檢查變更內容\n"
                "• 確保有備份或版本控制",
                border_style="yellow",
                title="風險評估"
            ))
        else:
            console.print(Panel(
                "[bold green]✓ 低風險[/bold green]\n\n"
                "此操作風險較低（新增檔案或文檔）",
                border_style="green",
                title="風險評估"
            ))

    def wait_for_confirmation(
        self,
        request: ApprovalRequest,
        allow_preview: bool = True,
        allow_step_by_step: bool = True
    ) -> bool:
        """
        等待使用者確認

        Args:
            request: 批准請求
            allow_preview: 是否允許預覽
            allow_step_by_step: 是否允許分步執行

        Returns:
            bool: 是否批准（True = 批准，False = 拒絕/取消）
        """
        plan = request.plan

        # 展示風險警告
        self.show_risk_warning(plan.risk_level)

        # 收集所有變更
        all_changes = []
        for step in plan.steps:
            all_changes.extend(step.file_changes)

        # 展示摘要
        console.print(f"\n[bold cyan]任務摘要：[/bold cyan]")
        console.print(f"  {plan.task_summary}")
        console.print(f"\n[bold cyan]統計：[/bold cyan]")
        console.print(f"  • 步驟數量：{len(plan.steps)}")
        console.print(f"  • 受影響檔案：{len(plan.affected_files)}")
        console.print(f"  • 預估時間：{plan.estimated_total_time}")

        # 互動式確認
        while True:
            console.print("\n[bold cyan]請選擇操作：[/bold cyan]")
            options = [
                "[bold green]y[/bold green] - 批准並執行",
                "[bold red]n[/bold red] - 拒絕",
            ]

            if allow_preview and all_changes:
                options.append("[bold yellow]p[/bold yellow] - 預覽變更")

            if allow_step_by_step and len(plan.steps) > 1:
                options.append("[bold blue]s[/bold blue] - 分步執行")

            options.append("[bold white]c[/bold white] - 取消")

            for opt in options:
                console.print(f"  {opt}")

            choice = Prompt.ask(
                "\n您的選擇",
                choices=["y", "n", "p", "s", "c"],
                default="n"
            ).lower()

            if choice == "y":
                # 批准
                request.status = ApprovalStatus.APPROVED
                console.print("\n[bold green]✅ 已批准執行計畫[/bold green]")
                return True

            elif choice == "n":
                # 拒絕
                request.status = ApprovalStatus.REJECTED
                console.print("\n[bold red]❌ 已拒絕執行計畫[/bold red]")

                # 可選：要求使用者輸入備註
                if Confirm.ask("是否要新增拒絕原因？", default=False):
                    notes = Prompt.ask("請輸入拒絕原因")
                    request.user_notes = notes

                return False

            elif choice == "p" and allow_preview:
                # 預覽變更
                self.show_diff_preview(all_changes)
                console.print("\n[dim]（按 Enter 繼續）[/dim]")
                input()

            elif choice == "s" and allow_step_by_step:
                # 分步執行
                return self._step_by_step_confirmation(request)

            elif choice == "c":
                # 取消
                request.status = ApprovalStatus.CANCELLED
                console.print("\n[bold yellow]⏸️  已取消操作[/bold yellow]")
                return False

    def _step_by_step_confirmation(self, request: ApprovalRequest) -> bool:
        """
        分步確認模式

        Args:
            request: 批准請求

        Returns:
            bool: 是否全部批准
        """
        plan = request.plan
        console.print("\n[bold cyan]🔄 分步確認模式[/bold cyan]\n")

        approved_steps = []

        for step in plan.steps:
            console.print(f"\n[bold]步驟 {step.step_number}：[/bold]{step.description}")
            console.print(f"  預估時間：{step.estimated_time}")

            if step.file_changes:
                console.print(f"\n  變更檔案：")
                for fc in step.file_changes:
                    action_emoji = {
                        'create': '✨',
                        'modify': '✏️',
                        'delete': '🗑️'
                    }.get(fc.action, '📝')
                    console.print(f"    {action_emoji} {fc.action}: {fc.file_path}")

            # 詢問是否批准此步驟
            approved = Confirm.ask(
                f"\n是否批准步驟 {step.step_number}？",
                default=True
            )

            if approved:
                approved_steps.append(step.step_number)
                console.print(f"  [green]✓ 步驟 {step.step_number} 已批准[/green]")
            else:
                console.print(f"  [red]✗ 步驟 {step.step_number} 已跳過[/red]")

                # 詢問是否繼續
                if not Confirm.ask("\n是否繼續檢視剩餘步驟？", default=True):
                    break

        # 摘要
        console.print(f"\n[bold cyan]分步確認摘要：[/bold cyan]")
        console.print(f"  已批准：{len(approved_steps)}/{len(plan.steps)} 個步驟")

        if len(approved_steps) == 0:
            console.print("\n[yellow]沒有任何步驟被批准[/yellow]")
            request.status = ApprovalStatus.REJECTED
            return False

        elif len(approved_steps) < len(plan.steps):
            console.print("\n[yellow]部分步驟被批准[/yellow]")

            # 詢問是否執行已批准的步驟
            execute = Confirm.ask("\n是否執行已批准的步驟？", default=True)

            if execute:
                request.status = ApprovalStatus.APPROVED
                request.user_notes = f"部分批准：步驟 {approved_steps}"
                return True
            else:
                request.status = ApprovalStatus.CANCELLED
                return False

        else:
            console.print("\n[green]所有步驟已批准[/green]")
            request.status = ApprovalStatus.APPROVED
            return True

    def execute_approved_plan(
        self,
        request: ApprovalRequest,
        executor: Optional[Callable[[ExecutionPlan], bool]] = None
    ) -> bool:
        """
        執行已批准的計畫

        Args:
            request: 批准請求
            executor: 執行函數（選用），接收 ExecutionPlan，返回 bool

        Returns:
            bool: 執行是否成功
        """
        if request.status != ApprovalStatus.APPROVED:
            console.print("[red]錯誤：計畫尚未被批准[/red]")
            return False

        console.print("\n[bold cyan]🚀 開始執行計畫...[/bold cyan]\n")

        if executor:
            # 使用提供的執行器
            try:
                success = executor(request.plan)

                if success:
                    console.print("\n[bold green]✅ 計畫執行成功！[/bold green]")
                else:
                    console.print("\n[bold red]❌ 計畫執行失敗[/bold red]")

                return success

            except Exception as e:
                console.print(f"\n[bold red]錯誤：執行過程中發生異常 - {e}[/bold red]")
                return False
        else:
            # 預設行為：僅顯示執行步驟（實際執行需要整合 MultiFileEditor）
            for step in request.plan.steps:
                console.print(f"\n[cyan]執行步驟 {step.step_number}：[/cyan]{step.description}")

                # 模擬執行
                import time
                time.sleep(0.5)

                console.print(f"  [green]✓ 完成[/green]")

            console.print("\n[bold green]✅ 所有步驟已執行（模擬模式）[/bold green]")
            console.print("[yellow]注意：實際執行需要整合 MultiFileEditor 模組[/yellow]")

            return True

    def create_approval_flow(
        self,
        plan: ExecutionPlan,
        executor: Optional[Callable[[ExecutionPlan], bool]] = None
    ) -> bool:
        """
        完整批准流程（一鍵執行）

        Args:
            plan: 執行計畫
            executor: 執行函數（選用）

        Returns:
            bool: 是否成功執行
        """
        # 建立批准請求
        request = self.request_approval(plan)

        # 等待確認
        approved = self.wait_for_confirmation(request)

        if not approved:
            return False

        # 執行計畫
        return self.execute_approved_plan(request, executor)


def main():
    """測試用主程式"""
    from .task_planner import TaskPlanner

    console.print("[bold cyan]CodeGemini Approval Workflow 測試[/bold cyan]\n")

    # 建立範例計畫
    try:
        planner = TaskPlanner()
        plan = planner.create_plan("新增使用者登入功能")

        # 建立批准流程
        workflow = ApprovalWorkflow()
        success = workflow.create_approval_flow(plan)

        if success:
            console.print("\n[bold green]✅ 流程完成[/bold green]")
        else:
            console.print("\n[bold yellow]⏸️  流程已取消或拒絕[/bold yellow]")

    except Exception as e:
        console.print(f"\n[red]錯誤：{e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
