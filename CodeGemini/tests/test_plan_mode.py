#!/usr/bin/env python3
"""
CodeGemini Plan Mode 測試
測試規劃模式功能
"""

import os
import sys
from pathlib import Path
from rich.console import Console

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from modes.plan_mode import PlanMode, Plan, PlanStep

console = Console()


def test_plan_mode_initialization():
    """測試 1：PlanMode 初始化"""
    console.print("\n[bold]測試 1：PlanMode 初始化[/bold]")

    try:
        pm = PlanMode()

        assert pm.current_plan is None, "初始計畫應為 None"
        assert pm.mode_active is False, "初始模式應為非啟用"
        assert len(pm.plan_history) == 0, "初始歷史應為空"

        console.print(f"[green]✓ PlanMode 初始化成功[/green]")
        console.print(f"  current_plan: {pm.current_plan}")
        console.print(f"  mode_active: {pm.mode_active}")
        console.print(f"  plan_history: {len(pm.plan_history)} 個")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_enter_plan_mode():
    """測試 2：進入規劃模式"""
    console.print("\n[bold]測試 2：進入規劃模式[/bold]")

    try:
        pm = PlanMode()
        task = "實作一個簡單的計算器功能"

        plan = pm.enter_plan_mode(task, context={"priority": "high"})

        assert plan is not None, "計畫不應為 None"
        assert pm.mode_active is True, "模式應為啟用"
        assert pm.current_plan == plan, "當前計畫應設置正確"
        assert plan.task_description == task, "任務描述應匹配"
        assert len(plan.steps) > 0, "計畫應包含步驟"

        console.print(f"[green]✓ 進入規劃模式成功[/green]")
        console.print(f"  mode_active: {pm.mode_active}")
        console.print(f"  計畫步驟數: {len(plan.steps)}")
        console.print(f"  預估時間: {plan.total_estimated_time}")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_plan_steps_generation():
    """測試 3：計畫步驟生成"""
    console.print("\n[bold]測試 3：計畫步驟生成[/bold]")

    try:
        pm = PlanMode()

        # 測試不同類型的任務
        test_cases = [
            ("為模組生成測試", "測試"),
            ("生成專案文檔", "文檔"),
            ("實作新功能", "功能"),
            ("重構程式碼", "其他")
        ]

        for task, expected_type in test_cases:
            plan = pm.enter_plan_mode(task)

            assert len(plan.steps) > 0, f"{expected_type}計畫應包含步驟"

            # 檢查步驟編號
            for i, step in enumerate(plan.steps, 1):
                assert step.step_number == i, f"步驟編號應為 {i}"

            console.print(f"  ✓ {expected_type}計畫：{len(plan.steps)} 個步驟")

            # 重置
            pm.exit_plan_mode(approved=False)

        console.print(f"[green]✓ 計畫步驟生成成功[/green]")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_exit_plan_mode_approved():
    """測試 4：退出規劃模式（批准）"""
    console.print("\n[bold]測試 4：退出規劃模式（批准）[/bold]")

    try:
        pm = PlanMode()
        task = "實作測試功能"

        # 進入規劃模式
        plan = pm.enter_plan_mode(task)

        # 批准並退出
        approved_plan = pm.exit_plan_mode(approved=True, feedback="計畫很好")

        assert approved_plan is not None, "批准的計畫不應為 None"
        assert approved_plan.approved is True, "計畫應標記為已批准"
        assert "計畫很好" in approved_plan.feedback, "反饋應記錄"
        assert pm.mode_active is False, "模式應退出"
        assert pm.current_plan is None, "當前計畫應清空"
        assert len(pm.plan_history) == 1, "歷史應包含計畫"

        console.print(f"[green]✓ 退出規劃模式（批准）成功[/green]")
        console.print(f"  計畫已批准: {approved_plan.approved}")
        console.print(f"  反饋數量: {len(approved_plan.feedback)}")
        console.print(f"  歷史計畫數: {len(pm.plan_history)}")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_exit_plan_mode_rejected():
    """測試 5：退出規劃模式（拒絕）"""
    console.print("\n[bold]測試 5：退出規劃模式（拒絕）[/bold]")

    try:
        pm = PlanMode()
        task = "實作測試功能"

        # 進入規劃模式
        plan = pm.enter_plan_mode(task)

        # 拒絕並退出
        result = pm.exit_plan_mode(approved=False, feedback="需要調整")

        assert result is None, "拒絕的計畫應返回 None"
        assert pm.mode_active is False, "模式應退出"
        assert pm.current_plan is None, "當前計畫應清空"
        assert len(pm.plan_history) == 1, "歷史應包含計畫"
        assert pm.plan_history[0].approved is False, "歷史中的計畫應標記為未批准"

        console.print(f"[green]✓ 退出規劃模式（拒絕）成功[/green]")
        console.print(f"  返回結果: {result}")
        console.print(f"  歷史計畫已批准: {pm.plan_history[0].approved}")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_update_plan():
    """測試 6：更新計畫"""
    console.print("\n[bold]測試 6：更新計畫[/bold]")

    try:
        pm = PlanMode()
        task = "實作測試功能"

        # 進入規劃模式
        original_plan = pm.enter_plan_mode(task)
        original_time = original_plan.updated_at

        # 等待一小段時間確保時間戳不同
        import time
        time.sleep(0.1)

        # 更新計畫
        updated_plan = pm.update_plan("請增加錯誤處理步驟")

        assert updated_plan == pm.current_plan, "更新後的計畫應為當前計畫"
        assert "請增加錯誤處理步驟" in updated_plan.feedback, "反饋應記錄"
        assert updated_plan.updated_at > original_time, "更新時間應改變"

        console.print(f"[green]✓ 更新計畫成功[/green]")
        console.print(f"  反饋數量: {len(updated_plan.feedback)}")
        console.print(f"  時間已更新: {updated_plan.updated_at > original_time}")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_plan_step_operations():
    """測試 7：計畫步驟操作"""
    console.print("\n[bold]測試 7：計畫步驟操作[/bold]")

    try:
        pm = PlanMode()
        task = "實作測試功能"

        plan = pm.enter_plan_mode(task)

        # 測試 get_next_step
        next_step = plan.get_next_step()
        assert next_step is not None, "應有下一個步驟"
        assert next_step.step_number == 1, "第一個步驟應為 #1"
        assert next_step.completed is False, "步驟應未完成"

        # 標記步驟為完成
        plan.mark_step_completed(1)
        assert plan.steps[0].completed is True, "步驟 #1 應標記為已完成"

        # 再次取得下一個步驟
        next_step = plan.get_next_step()
        if next_step:
            assert next_step.step_number == 2, "下一個步驟應為 #2"

        # 測試進度
        progress = plan.get_progress()
        assert progress["completed_steps"] == 1, "應有 1 個完成步驟"
        assert progress["total_steps"] == len(plan.steps), "總步驟數應正確"
        assert 0 < progress["progress_percentage"] < 100, "進度百分比應在 0-100 之間"

        console.print(f"[green]✓ 計畫步驟操作成功[/green]")
        console.print(f"  已完成步驟: {progress['completed_steps']}/{progress['total_steps']}")
        console.print(f"  進度: {progress['progress_percentage']:.1f}%")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_plan_dependencies():
    """測試 8：步驟依賴處理"""
    console.print("\n[bold]測試 8：步驟依賴處理[/bold]")

    try:
        # 建立帶有依賴的計畫
        steps = [
            PlanStep(step_number=1, title="步驟1", description="第一步", estimated_time="5分鐘"),
            PlanStep(step_number=2, title="步驟2", description="第二步", estimated_time="5分鐘", dependencies=[1]),
            PlanStep(step_number=3, title="步驟3", description="第三步", estimated_time="5分鐘", dependencies=[1, 2])
        ]

        plan = Plan(
            task_description="測試依賴",
            steps=steps,
            total_estimated_time="15分鐘"
        )

        # 測試：步驟 2 和 3 不應該是下一個步驟（因為依賴未完成）
        next_step = plan.get_next_step()
        assert next_step.step_number == 1, "只有步驟 1 沒有依賴"

        # 完成步驟 1
        plan.mark_step_completed(1)

        # 現在步驟 2 應該可以執行
        next_step = plan.get_next_step()
        assert next_step.step_number == 2, "步驟 1 完成後，步驟 2 應可執行"

        # 完成步驟 2
        plan.mark_step_completed(2)

        # 現在步驟 3 應該可以執行
        next_step = plan.get_next_step()
        assert next_step.step_number == 3, "步驟 1、2 完成後，步驟 3 應可執行"

        console.print(f"[green]✓ 步驟依賴處理成功[/green]")
        console.print(f"  依賴鏈正確執行: ✓")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_display_plan():
    """測試 9：展示計畫"""
    console.print("\n[bold]測試 9：展示計畫[/bold]")

    try:
        pm = PlanMode()
        task = "實作測試功能"

        plan = pm.enter_plan_mode(task)

        # 展示計畫（不應拋出異常）
        pm.display_plan()

        console.print(f"[green]✓ 展示計畫成功[/green]")

        return True

    except Exception as e:
        console.print(f"[red]✗ 失敗：{e}[/red]")
        import traceback
        traceback.print_exc()
        return False


# ==================== 主測試流程 ====================

def main():
    """執行所有測試"""
    console.print("=" * 70)
    console.print("[bold cyan]CodeGemini Plan Mode - 測試套件[/bold cyan]")
    console.print("=" * 70)

    tests = [
        ("PlanMode 初始化", test_plan_mode_initialization),
        ("進入規劃模式", test_enter_plan_mode),
        ("計畫步驟生成", test_plan_steps_generation),
        ("退出規劃模式（批准）", test_exit_plan_mode_approved),
        ("退出規劃模式（拒絕）", test_exit_plan_mode_rejected),
        ("更新計畫", test_update_plan),
        ("計畫步驟操作", test_plan_step_operations),
        ("步驟依賴處理", test_plan_dependencies),
        ("展示計畫", test_display_plan),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ 通過" if result else "❌ 失敗"
        except Exception as e:
            console.print(f"[red]測試異常：{e}[/red]")
            results[test_name] = "❌ 失敗"

    # 顯示測試總結
    console.print("\n" + "=" * 70)
    console.print("[bold]測試總結[/bold]")
    console.print("=" * 70)

    for test_name, result in results.items():
        console.print(f"  {test_name}: {result}")

    # 統計
    passed = sum(1 for r in results.values() if "通過" in r)
    total = len(results)

    console.print("-" * 70)
    console.print(f"[bold]總計：{passed}/{total} 測試通過[/bold]")

    if passed < total:
        console.print(f"\n[yellow]⚠️  {total - passed} 個測試失敗[/yellow]")
    else:
        console.print("\n[green]🎉 所有測試通過！Plan Mode 準備就緒。[/green]")


if __name__ == "__main__":
    main()
