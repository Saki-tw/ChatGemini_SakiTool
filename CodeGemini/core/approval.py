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
from utils.i18n import safe_t

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
        console.print(safe_t('codegemini.approval.change_preview', fallback='\n[bold #DDA0DD]📝 變更預覽[/bold #DDA0DD]\n'))

        # 建立變更表格
        table = Table(show_header=True, header_style="bold #DA70D6")
        console_width = console.width or 120
        table.add_column("動作", style="#DDA0DD", width=max(10, int(console_width * 0.10)))
        table.add_column("檔案路徑", style="white")
        table.add_column("變更描述", style="green")
        table.add_column("預估行數", justify="right", style="#DDA0DD")

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
                "[bold #DDA0DD]⚠️  中等風險[/bold #DDA0DD]\n\n"
                "此操作會修改現有檔案：\n"
                "• 建議先檢查變更內容\n"
                "• 確保有備份或版本控制",
                border_style="#DDA0DD",
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
        console.print(safe_t("approval.plan.summary_title", fallback="\n[bold #DDA0DD]任務摘要：[/bold #DDA0DD]"))
        console.print(f"  {plan.task_summary}")
        console.print(safe_t("approval.plan.stats_title", fallback="\n[bold #DDA0DD]統計：[/bold #DDA0DD]"))
        console.print(safe_t("approval.plan.steps", fallback="  • 步驟數量：{count}").format(count=len(plan.steps)))
        console.print(safe_t("approval.plan.files", fallback="  • 受影響檔案：{count}").format(count=len(plan.affected_files)))
        console.print(safe_t("approval.plan.time", fallback="  • 預估時間：{time}").format(time=plan.estimated_total_time))

        # 互動式確認
        while True:
            console.print(safe_t("approval.prompt.choose", fallback="\n[bold #DDA0DD]請選擇操作：[/bold #DDA0DD]"))
            options = [
                "[bold green]y[/bold green] - 批准並執行",
                "[bold red]n[/bold red] - 拒絕",
            ]

            if allow_preview and all_changes:
                options.append("[bold #DDA0DD]p[/bold #DDA0DD] - 預覽變更")

            if allow_step_by_step and len(plan.steps) > 1:
                options.append("[bold #DDA0DD]s[/bold #DDA0DD] - 分步執行")

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
                console.print(safe_t('codegemini.approval.approved', fallback='\n[bold green]✅ 已批准執行計畫[/bold green]'))
                return True

            elif choice == "n":
                # 拒絕
                request.status = ApprovalStatus.REJECTED
                console.print(safe_t('codegemini.approval.rejected', fallback='\n[bold red]❌ 已拒絕執行計畫[/bold red]'))

                # 可選：要求使用者輸入備註
                if Confirm.ask(safe_t('codegemini.approval.add_rejection_reason', fallback='是否要新增拒絕原因？'), default=False):
                    notes = Prompt.ask(safe_t('codegemini.approval.enter_reason', fallback='請輸入拒絕原因'))
                    request.user_notes = notes

                return False

            elif choice == "p" and allow_preview:
                # 預覽變更
                self.show_diff_preview(all_changes)
                console.print(safe_t("approval.prompt.continue", fallback="\n[dim]（按 Enter 繼續）[/dim]"))
                input()

            elif choice == "s" and allow_step_by_step:
                # 分步執行
                return self._step_by_step_confirmation(request)

            elif choice == "c":
                # 取消
                request.status = ApprovalStatus.CANCELLED
                console.print(safe_t('codegemini.approval.cancelled', fallback='\n[bold #DDA0DD]⏸️  已取消操作[/bold #DDA0DD]'))
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
        console.print(safe_t('codegemini.approval.step_by_step_mode', fallback='\n[bold #DDA0DD]🔄 分步確認模式[/bold #DDA0DD]\n'))

        approved_steps = []

        for step in plan.steps:
            console.print(safe_t("approval.step.title", fallback="\n[bold]步驟 {num}：[/bold]{desc}").format(num=step.step_number, desc=step.description))
            console.print(safe_t("approval.step.time", fallback="  預估時間：{time}").format(time=step.estimated_time))

            if step.file_changes:
                console.print(safe_t("approval.step.files", fallback="\n  變更檔案："))
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
                console.print(safe_t('codegemini.approval.step_approved', fallback='  [#DA70D6]✓ 步驟 {num} 已批准[/green]', num=step.step_number))
            else:
                console.print(safe_t('codegemini.approval.step_skipped', fallback='  [dim #DDA0DD]✗ 步驟 {num} 已跳過[/red]', num=step.step_number))

                # 詢問是否繼續
                if not Confirm.ask(safe_t('codegemini.approval.continue_review', fallback='\n是否繼續檢視剩餘步驟？'), default=True):
                    break

        # 摘要
        console.print(safe_t("approval.summary.title", fallback="\n[bold #DDA0DD]分步確認摘要：[/bold #DDA0DD]"))
        console.print(safe_t("approval.summary.approved", fallback="  已批准：{approved}/{total} 個步驟").format(approved=len(approved_steps), total=len(plan.steps)))

        if len(approved_steps) == 0:
            console.print(safe_t('codegemini.approval.no_steps_approved', fallback='\n[#DDA0DD]沒有任何步驟被批准[/#DDA0DD]'))
            request.status = ApprovalStatus.REJECTED
            return False

        elif len(approved_steps) < len(plan.steps):
            console.print(safe_t('codegemini.approval.partial_approval', fallback='\n[#DDA0DD]部分步驟被批准[/#DDA0DD]'))

            # 詢問是否執行已批准的步驟
            execute = Confirm.ask(safe_t('codegemini.approval.execute_approved', fallback='\n是否執行已批准的步驟？'), default=True)

            if execute:
                request.status = ApprovalStatus.APPROVED
                request.user_notes = f"部分批准：步驟 {approved_steps}"
                return True
            else:
                request.status = ApprovalStatus.CANCELLED
                return False

        else:
            console.print(safe_t('codegemini.approval.all_approved', fallback='\n[#DA70D6]所有步驟已批准[/green]'))
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
            console.print(safe_t('codegemini.approval.not_approved', fallback='[dim #DDA0DD]錯誤：計畫尚未被批准[/red]'))
            return False

        console.print(safe_t('codegemini.approval.executing', fallback='\n[bold #DDA0DD]🚀 開始執行計畫...[/bold #DDA0DD]\n'))

        if executor:
            # 使用提供的執行器
            try:
                success = executor(request.plan)

                if success:
                    console.print(safe_t('codegemini.approval.execution_success', fallback='\n[bold green]✅ 計畫執行成功！[/bold green]'))
                else:
                    console.print(safe_t('codegemini.approval.execution_failed', fallback='\n[bold red]❌ 計畫執行失敗[/bold red]'))

                return success

            except Exception as e:
                console.print(safe_t('codegemini.approval.execution_error', fallback='\n[bold red]錯誤：執行過程中發生異常 - {error}[/bold red]', error=e))
                return False
        else:
            # 預設行為：僅顯示執行步驟（實際執行需要整合 MultiFileEditor）
            for step in request.plan.steps:
                console.print(safe_t("approval.execute.step", fallback="\n[#DDA0DD]執行步驟 {num}：[/#DDA0DD]{desc}").format(num=step.step_number, desc=step.description))

                # 模擬執行
                import time
                time.sleep(0.5)

                console.print(safe_t("approval.execute.completed", fallback="  [#DA70D6]✓ 完成[/green]"))

            console.print(safe_t('codegemini.approval.simulation_complete', fallback='\n[bold green]✅ 所有步驟已執行（模擬模式）[/bold green]'))
            console.print(safe_t('codegemini.approval.requires_integration', fallback='[#DDA0DD]注意：實際執行需要整合 MultiFileEditor 模組[/#DDA0DD]'))

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

    console.print(safe_t("approval.test.title", fallback="[bold #DDA0DD]CodeGemini Approval Workflow 測試[/bold #DDA0DD]\n"))

    # 建立範例計畫
    try:
        planner = TaskPlanner()
        plan = planner.create_plan("新增使用者登入功能")

        # 建立批准流程
        workflow = ApprovalWorkflow()
        success = workflow.create_approval_flow(plan)

        if success:
            console.print(safe_t("approval.test.success", fallback="\n[bold green]✅ 流程完成[/bold green]"))
        else:
            console.print(safe_t("approval.test.cancelled", fallback="\n[bold #DDA0DD]⏸️  流程已取消或拒絕[/bold #DDA0DD]"))

    except Exception as e:
        console.print(safe_t("approval.test.error", fallback="\n[dim #DDA0DD]錯誤：{error}[/red]").format(error=e))
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
