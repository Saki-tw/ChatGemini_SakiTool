#!/usr/bin/env python3
"""
CodeGemini Plan Mode Module
規劃模式 - 提供規劃與執行分離

此模組負責：
1. 進入規劃模式（純規劃，不執行）
2. 生成詳細的實作計畫
3. 展示計畫供用戶審查
4. 用戶批准後退出規劃模式
5. 根據用戶反饋更新計畫
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

# 確保可以 import utils
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.i18n import safe_t

console = Console()


@dataclass
class PlanStep:
    """計畫步驟"""
    step_number: int
    title: str
    description: str
    estimated_time: str  # 預估時間
    dependencies: List[int] = field(default_factory=list)  # 依賴的步驟
    files_affected: List[str] = field(default_factory=list)  # 影響的檔案
    risks: List[str] = field(default_factory=list)  # 風險點
    completed: bool = False


@dataclass
class Plan:
    """實作計畫"""
    task_description: str
    steps: List[PlanStep]
    total_estimated_time: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    approved: bool = False
    feedback: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: PlanStep) -> None:
        """新增步驟"""
        self.steps.append(step)
        self.updated_at = datetime.now()

    def update_step(self, step_number: int, **kwargs) -> None:
        """更新步驟"""
        for step in self.steps:
            if step.step_number == step_number:
                for key, value in kwargs.items():
                    if hasattr(step, key):
                        setattr(step, key, value)
                self.updated_at = datetime.now()
                break

    def mark_step_completed(self, step_number: int) -> None:
        """標記步驟為已完成"""
        self.update_step(step_number, completed=True)

    def get_next_step(self) -> Optional[PlanStep]:
        """取得下一個待執行的步驟"""
        for step in self.steps:
            if not step.completed:
                # 檢查依賴是否完成
                deps_completed = all(
                    any(s.step_number == dep and s.completed for s in self.steps)
                    for dep in step.dependencies
                )
                if deps_completed or not step.dependencies:
                    return step
        return None

    def get_progress(self) -> Dict[str, Any]:
        """取得進度資訊"""
        total = len(self.steps)
        completed = sum(1 for step in self.steps if step.completed)
        return {
            "total_steps": total,
            "completed_steps": completed,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
            "remaining_steps": total - completed
        }


class PlanMode:
    """
    規劃模式管理器

    提供規劃與執行分離的能力：
    - 進入規劃模式：分析任務並生成計畫
    - 展示計畫：以結構化方式呈現計畫
    - 更新計畫：根據用戶反饋調整
    - 退出規劃模式：批准計畫並準備執行
    """

    def __init__(self):
        """初始化規劃模式"""
        self.current_plan: Optional[Plan] = None
        self.mode_active: bool = False
        self.plan_history: List[Plan] = []

    def enter_plan_mode(self, task: str, context: Optional[Dict[str, Any]] = None) -> Plan:
        """
        進入規劃模式

        Args:
            task: 任務描述
            context: 上下文資訊（選用）

        Returns:
            Plan: 生成的計畫
        """
        console.print(safe_t('codegemini.plan.enter_mode', fallback="\n[bold #DDA0DD]🎯 進入規劃模式...[/bold #DDA0DD]"))
        console.print(safe_t('codegemini.plan.task', fallback="[#DDA0DD]任務：{task}[/#DDA0DD]\n", task=task))

        self.mode_active = True

        # 分析任務並生成計畫
        plan = self._analyze_and_plan(task, context or {})
        self.current_plan = plan

        console.print(safe_t('codegemini.plan.generated', fallback="[#DA70D6]✓ 計畫生成完成[/green]"))

        return plan

    def exit_plan_mode(self, approved: bool = True, feedback: Optional[str] = None) -> Optional[Plan]:
        """
        退出規劃模式

        Args:
            approved: 是否批准計畫
            feedback: 用戶反饋（選用）

        Returns:
            Optional[Plan]: 如果批准則返回計畫，否則返回 None
        """
        if not self.mode_active:
            console.print(safe_t('codegemini.plan.not_in_mode', fallback="[#DDA0DD]⚠️  未在規劃模式中[/#DDA0DD]"))
            return None

        if not self.current_plan:
            console.print(safe_t('codegemini.plan.no_plan', fallback="[dim #DDA0DD]✗ 無有效計畫[/red]"))
            return None

        self.mode_active = False

        if approved:
            self.current_plan.approved = True
            if feedback:
                self.current_plan.feedback.append(feedback)

            console.print(safe_t('codegemini.plan.approved', fallback="\n[bold green]✅ 計畫已批准！準備執行...[/bold green]"))

            # 儲存到歷史
            self.plan_history.append(self.current_plan)

            approved_plan = self.current_plan
            self.current_plan = None

            return approved_plan
        else:
            console.print(safe_t('codegemini.plan.rejected', fallback="\n[bold #DDA0DD]⚠️  計畫已拒絕[/bold #DDA0DD]"))
            if feedback:
                console.print(safe_t('codegemini.plan.feedback', fallback="反饋：{feedback}", feedback=feedback))

            # 儲存到歷史但標記為未批准
            self.plan_history.append(self.current_plan)
            self.current_plan = None

            return None

    def update_plan(self, feedback: str) -> Plan:
        """
        根據用戶反饋更新計畫

        Args:
            feedback: 用戶反饋

        Returns:
            Plan: 更新後的計畫
        """
        if not self.current_plan:
            raise ValueError(safe_t('codegemini.plan.error_no_plan_update', fallback="無有效計畫可更新"))

        console.print(safe_t('codegemini.plan.updating', fallback="\n[#DDA0DD]📝 根據反饋更新計畫...[/#DDA0DD]"))
        console.print(safe_t('codegemini.plan.feedback_detail', fallback="反饋：{feedback}\n", feedback=feedback))

        self.current_plan.feedback.append(feedback)

        # 這裡應該根據反饋實際調整計畫
        # 目前僅記錄反饋
        self.current_plan.updated_at = datetime.now()

        console.print(safe_t('codegemini.plan.updated', fallback="[#DA70D6]✓ 計畫已更新[/green]"))

        return self.current_plan

    def display_plan(self, plan: Optional[Plan] = None) -> None:
        """
        展示計畫

        Args:
            plan: 要展示的計畫（選用，預設為當前計畫）
        """
        display_plan = plan or self.current_plan

        if not display_plan:
            console.print(safe_t('codegemini.plan.no_plan_display', fallback="[#DDA0DD]⚠️  無計畫可展示[/#DDA0DD]"))
            return

        # 標題
        console.print(safe_t('codegemini.plan.separator', fallback=f"\n[bold #DDA0DD]{'=' * 70}[/bold #DDA0DD]"))
        console.print(safe_t('codegemini.plan.title', fallback="[bold white]📋 實作計畫[/bold white]"))
        console.print(safe_t('codegemini.plan.separator', fallback=f"[bold #DDA0DD]{'=' * 70}[/bold #DDA0DD]\n"))

        # 任務描述（使用 Markdown 渲染）
        console.print(Panel(
            Markdown(display_plan.task_description),
            title=safe_t('codegemini.plan.task_desc', fallback="[bold]任務描述[/bold]"),
            border_style="#DDA0DD"
        ))

        # 基本資訊
        info_table = Table(show_header=False, box=None)
        info_table.add_column(safe_t('codegemini.plan.info_item', fallback="項目"), style="#DDA0DD")
        info_table.add_column(safe_t('codegemini.plan.info_value', fallback="值"), style="white")

        info_table.add_row(safe_t('codegemini.plan.total_steps', fallback="總步驟數"), str(len(display_plan.steps)))
        info_table.add_row(safe_t('codegemini.plan.total_time', fallback="預估總時間"), display_plan.total_estimated_time)
        info_table.add_row(safe_t('codegemini.plan.created_at', fallback="建立時間"), display_plan.created_at.strftime("%Y-%m-%d %H:%M:%S"))

        if display_plan.approved:
            info_table.add_row(safe_t('codegemini.plan.status', fallback="狀態"), safe_t('codegemini.plan.status_approved', fallback="[#DA70D6]✅ 已批准[/green]"))
        else:
            info_table.add_row(safe_t('codegemini.plan.status', fallback="狀態"), safe_t('codegemini.plan.status_pending', fallback="[#DDA0DD]⏳ 待批准[/#DDA0DD]"))

        console.print(info_table)
        console.print()

        # 步驟詳情
        console.print(safe_t('codegemini.plan.steps', fallback="[bold white]📝 實作步驟：[/bold white]\n"))

        for step in display_plan.steps:
            self._display_step(step)

        # 反饋（如果有）
        if display_plan.feedback:
            console.print(safe_t('codegemini.plan.user_feedback', fallback="\n[bold white]💬 用戶反饋：[/bold white]"))
            for i, fb in enumerate(display_plan.feedback, 1):
                console.print(f"  {i}. {fb}")

        console.print(safe_t('codegemini.plan.separator_end', fallback="\n[bold #DDA0DD]{'=' * 70}[/bold #DDA0DD]\n"))

    def _display_step(self, step: PlanStep) -> None:
        """展示單個步驟"""
        # 步驟標題
        status = safe_t('codegemini.plan.step_completed', fallback="✅") if step.completed else safe_t('codegemini.plan.step_pending', fallback="⏳")
        console.print(safe_t('codegemini.plan.step_title', fallback="[bold]{status} 步驟 {num}: {title}[/bold]", status=status, num=step.step_number, title=step.title))

        # 描述
        console.print(safe_t('codegemini.plan.step_desc', fallback="   {desc}", desc=step.description))

        # 預估時間
        console.print(safe_t('codegemini.plan.step_time', fallback="   ⏱️  預估時間：{time}", time=step.estimated_time))

        # 依賴
        if step.dependencies:
            deps_str = ", ".join(f"#{d}" for d in step.dependencies)
            console.print(safe_t('codegemini.plan.step_deps', fallback="   🔗 依賴步驟：{deps}", deps=deps_str))

        # 影響的檔案
        if step.files_affected:
            console.print(safe_t('codegemini.plan.step_files', fallback="   📄 影響檔案：{count} 個", count=len(step.files_affected)))
            for file in step.files_affected[:3]:  # 最多顯示 3 個
                console.print(f"      - {file}")
            if len(step.files_affected) > 3:
                console.print(safe_t('codegemini.plan.step_files_more', fallback="      ... 還有 {count} 個", count=len(step.files_affected) - 3))

        # 風險
        if step.risks:
            console.print(safe_t('codegemini.plan.step_risks', fallback="   ⚠️  風險："))
            for risk in step.risks:
                console.print(f"      - {risk}")

        console.print()

    def _analyze_and_plan(self, task: str, context: Dict[str, Any]) -> Plan:
        """
        分析任務並生成計畫

        這是一個簡化版本，實際應該使用 AI 進行分析

        Args:
            task: 任務描述
            context: 上下文資訊

        Returns:
            Plan: 生成的計畫
        """
        # 這裡應該使用 AI 來分析任務並生成詳細計畫
        # 目前使用模板生成示例計畫

        steps = []

        # 示例：根據任務類型生成不同的步驟
        task_lower = task.lower()
        if safe_t('codegemini.plan.keyword_test', fallback="測試") in task or "test" in task_lower:
            steps = self._generate_test_plan_steps(task, context)
        elif safe_t('codegemini.plan.keyword_doc', fallback="文檔") in task or "doc" in task_lower:
            steps = self._generate_doc_plan_steps(task, context)
        elif safe_t('codegemini.plan.keyword_feature', fallback="功能") in task or "feature" in task_lower:
            steps = self._generate_feature_plan_steps(task, context)
        else:
            steps = self._generate_generic_plan_steps(task, context)

        # 計算總預估時間
        total_time = self._calculate_total_time(steps)

        plan = Plan(
            task_description=task,
            steps=steps,
            total_estimated_time=total_time,
            metadata=context
        )

        return plan

    def _generate_test_plan_steps(self, task: str, context: Dict[str, Any]) -> List[PlanStep]:
        """生成測試計畫步驟"""
        return [
            PlanStep(
                step_number=1,
                title=safe_t('codegemini.plan.test_analyze', fallback="分析待測試模組"),
                description=safe_t('codegemini.plan.test_analyze_desc', fallback="使用 AST 分析目標模組，提取函數和類別資訊"),
                estimated_time=safe_t('codegemini.plan.time_5min', fallback="5 分鐘"),
                files_affected=["generators/test_gen.py"]
            ),
            PlanStep(
                step_number=2,
                title=safe_t('codegemini.plan.test_generate', fallback="生成測試程式碼"),
                description=safe_t('codegemini.plan.test_generate_desc', fallback="根據分析結果生成 pytest 或 unittest 測試程式碼"),
                estimated_time=safe_t('codegemini.plan.time_10min', fallback="10 分鐘"),
                dependencies=[1],
                files_affected=["tests/test_*.py"]
            ),
            PlanStep(
                step_number=3,
                title=safe_t('codegemini.plan.test_verify', fallback="執行測試驗證"),
                description=safe_t('codegemini.plan.test_verify_desc', fallback="運行生成的測試，確保測試可執行"),
                estimated_time=safe_t('codegemini.plan.time_5min', fallback="5 分鐘"),
                dependencies=[2],
                risks=[safe_t('codegemini.plan.test_risk1', fallback="測試可能失敗"), safe_t('codegemini.plan.test_risk2', fallback="需要手動調整")]
            )
        ]

    def _generate_doc_plan_steps(self, task: str, context: Dict[str, Any]) -> List[PlanStep]:
        """生成文檔計畫步驟"""
        return [
            PlanStep(
                step_number=1,
                title=safe_t('codegemini.plan.doc_scan', fallback="掃描專案結構"),
                description=safe_t('codegemini.plan.doc_scan_desc', fallback="遞迴掃描專案目錄，識別所有 Python 模組"),
                estimated_time=safe_t('codegemini.plan.time_5min', fallback="5 分鐘"),
                files_affected=["generators/doc_gen.py"]
            ),
            PlanStep(
                step_number=2,
                title=safe_t('codegemini.plan.doc_analyze', fallback="分析模組內容"),
                description=safe_t('codegemini.plan.doc_analyze_desc', fallback="提取每個模組的 docstring、函數和類別資訊"),
                estimated_time=safe_t('codegemini.plan.time_10min', fallback="10 分鐘"),
                dependencies=[1]
            ),
            PlanStep(
                step_number=3,
                title=safe_t('codegemini.plan.doc_readme', fallback="生成 README"),
                description=safe_t('codegemini.plan.doc_readme_desc', fallback="根據專案結構生成 README.md"),
                estimated_time=safe_t('codegemini.plan.time_5min', fallback="5 分鐘"),
                dependencies=[2],
                files_affected=["README.md"]
            ),
            PlanStep(
                step_number=4,
                title=safe_t('codegemini.plan.doc_api', fallback="生成 API 文檔"),
                description=safe_t('codegemini.plan.doc_api_desc', fallback="根據模組資訊生成 API 參考文檔"),
                estimated_time=safe_t('codegemini.plan.time_5min', fallback="5 分鐘"),
                dependencies=[2],
                files_affected=["API.md"]
            )
        ]

    def _generate_feature_plan_steps(self, task: str, context: Dict[str, Any]) -> List[PlanStep]:
        """生成功能實作計畫步驟"""
        return [
            PlanStep(
                step_number=1,
                title=safe_t('codegemini.plan.feature_analyze', fallback="需求分析"),
                description=safe_t('codegemini.plan.feature_analyze_desc', fallback="分析功能需求，確定實作範圍"),
                estimated_time=safe_t('codegemini.plan.time_10min', fallback="10 分鐘")
            ),
            PlanStep(
                step_number=2,
                title=safe_t('codegemini.plan.feature_design', fallback="設計架構"),
                description=safe_t('codegemini.plan.feature_design_desc', fallback="設計模組結構、類別和介面"),
                estimated_time=safe_t('codegemini.plan.time_15min', fallback="15 分鐘"),
                dependencies=[1]
            ),
            PlanStep(
                step_number=3,
                title=safe_t('codegemini.plan.feature_implement', fallback="實作核心功能"),
                description=safe_t('codegemini.plan.feature_implement_desc', fallback="編寫主要功能程式碼"),
                estimated_time=safe_t('codegemini.plan.time_30min', fallback="30 分鐘"),
                dependencies=[2],
                risks=[safe_t('codegemini.plan.feature_risk1', fallback="可能需要重構現有程式碼")]
            ),
            PlanStep(
                step_number=4,
                title=safe_t('codegemini.plan.feature_test', fallback="編寫測試"),
                description=safe_t('codegemini.plan.feature_test_desc', fallback="為新功能編寫單元測試"),
                estimated_time=safe_t('codegemini.plan.time_20min', fallback="20 分鐘"),
                dependencies=[3]
            ),
            PlanStep(
                step_number=5,
                title=safe_t('codegemini.plan.feature_integration', fallback="整合測試"),
                description=safe_t('codegemini.plan.feature_integration_desc', fallback="執行測試並修正問題"),
                estimated_time=safe_t('codegemini.plan.time_15min', fallback="15 分鐘"),
                dependencies=[4],
                risks=[safe_t('codegemini.plan.feature_risk2', fallback="可能發現整合問題")]
            )
        ]

    def _generate_generic_plan_steps(self, task: str, context: Dict[str, Any]) -> List[PlanStep]:
        """生成通用計畫步驟"""
        return [
            PlanStep(
                step_number=1,
                title=safe_t('codegemini.plan.generic_analyze', fallback="分析任務"),
                description=safe_t('codegemini.plan.generic_analyze_desc', fallback="分析任務：{task}", task=task),
                estimated_time=safe_t('codegemini.plan.time_5min', fallback="5 分鐘")
            ),
            PlanStep(
                step_number=2,
                title=safe_t('codegemini.plan.generic_prepare', fallback="準備環境"),
                description=safe_t('codegemini.plan.generic_prepare_desc', fallback="準備必要的檔案和依賴"),
                estimated_time=safe_t('codegemini.plan.time_5min', fallback="5 分鐘"),
                dependencies=[1]
            ),
            PlanStep(
                step_number=3,
                title=safe_t('codegemini.plan.generic_execute', fallback="執行任務"),
                description=safe_t('codegemini.plan.generic_execute_desc', fallback="執行主要任務"),
                estimated_time=safe_t('codegemini.plan.time_10min', fallback="10 分鐘"),
                dependencies=[2]
            ),
            PlanStep(
                step_number=4,
                title=safe_t('codegemini.plan.generic_verify', fallback="驗證結果"),
                description=safe_t('codegemini.plan.generic_verify_desc', fallback="檢查執行結果並驗證"),
                estimated_time=safe_t('codegemini.plan.time_5min', fallback="5 分鐘"),
                dependencies=[3]
            )
        ]

    def _calculate_total_time(self, steps: List[PlanStep]) -> str:
        """計算總預估時間"""
        total_minutes = 0

        for step in steps:
            # 從 "X 分鐘" 中提取數字
            time_str = step.estimated_time
            if safe_t('codegemini.plan.time_unit_minute', fallback="分鐘") in time_str:
                try:
                    minutes = int(time_str.split()[0])
                    total_minutes += minutes
                except (ValueError, IndexError):
                    pass

        if total_minutes < 60:
            return safe_t('codegemini.plan.time_total_minutes', fallback="{minutes} 分鐘", minutes=total_minutes)
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if minutes > 0:
                return safe_t('codegemini.plan.time_total_hours_minutes', fallback="{hours} 小時 {minutes} 分鐘", hours=hours, minutes=minutes)
            else:
                return safe_t('codegemini.plan.time_total_hours', fallback="{hours} 小時", hours=hours)


# ==================== 命令列介面 ====================

def main():
    """Plan Mode 命令列工具"""
    console.print(safe_t('codegemini.plan.demo_title', fallback="\n[bold #DDA0DD]CodeGemini Plan Mode Demo[/bold #DDA0DD]\n"))

    # 建立 PlanMode 實例
    pm = PlanMode()

    # 示例：測試任務
    task = safe_t('codegemini.plan.demo_task', fallback="為 calculator.py 模組生成完整的測試套件")

    # 進入規劃模式
    plan = pm.enter_plan_mode(task, context={"framework": "pytest"})

    # 展示計畫
    pm.display_plan()

    # 模擬用戶批准
    console.print(safe_t('codegemini.plan.demo_review', fallback="[#DDA0DD]➜ 用戶審查計畫...[/#DDA0DD]"))
    console.input(safe_t('codegemini.plan.demo_approve_prompt', fallback="\n按 Enter 鍵批准計畫..."))

    # 退出規劃模式
    approved_plan = pm.exit_plan_mode(approved=True, feedback=safe_t('codegemini.plan.demo_feedback', fallback="計畫清楚完整"))

    if approved_plan:
        console.print(safe_t('codegemini.plan.demo_approved', fallback="\n[#DA70D6]✓ 計畫已批准，可以開始執行[/green]"))

        # 展示進度
        progress = approved_plan.get_progress()
        console.print(safe_t('codegemini.plan.demo_progress', fallback="\n進度：{completed}/{total} 步驟完成", completed=progress['completed_steps'], total=progress['total_steps']))


if __name__ == "__main__":
    main()
