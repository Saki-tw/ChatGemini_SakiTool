#!/usr/bin/env python3
"""
Gemini 模型選擇器
從 gemini_chat.py 抽離
"""

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


# 推薦模型清單（從 gemini_chat.py 導入）
RECOMMENDED_MODELS = {
    '1': ('gemini-2.5-flash', 'Gemini 2.5 Flash（推薦，最快）'),
    '2': ('gemini-2.5-pro', 'Gemini 2.5 Pro（最強，較貴）'),
    '3': ('gemini-2.5-flash-8b', 'Gemini 2.5 Flash 8B（精簡版，更快）'),
}


def _get_available_models() -> Optional[List[str]]:
    """
    從 API 獲取可用的模型列表

    Returns:
        模型名稱列表，失敗時返回 None
    """
    try:
        from google import genai
        client = genai.Client()
        models = client.models.list()
        # 只返回 Gemini 模型名稱
        available_models = [m.name.replace('models/', '') for m in models if 'gemini' in m.name.lower()]
        return available_models
    except Exception as e:
        logger.warning(f"無法從 API 獲取模型列表：{e}")
        return None


def select_model() -> str:
    """選擇 Gemini 模型（含思考模式資訊與價格預估）"""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()

    console.print("\n")
    console.print(Panel.fit(
        "[bold #DDA0DD]🤖 Gemini 模型選擇[/bold #DDA0DD]",
        border_style="#DDA0DD"
    ))

    # 建立模型資訊表格
    table = Table(show_header=True, header_style="bold #DDA0DD", border_style="#DDA0DD")
    table.add_column("選項", style="#DA70D6", justify="center")
    table.add_column("模型名稱", style="white")
    table.add_column("Thinking Token 範圍", style="#BA55D3")
    table.add_column("價格範圍 (NT$)", style="#FF00FF", justify="right")

    # 導入價格計算
    try:
        from gemini_thinking import get_thinking_budget_info, estimate_thinking_cost
        from gemini_pricing import PricingCalculator

        calculator = PricingCalculator()

        for key, (model_name, description) in RECOMMENDED_MODELS.items():
            # 取得思考資訊
            thinking_info = get_thinking_budget_info(model_name)

            # Token 範圍顯示
            min_token = thinking_info['min']
            max_token = thinking_info['max']
            thinking_desc = f"{min_token:,} ~ {max_token:,} tokens"
            if not thinking_info['allow_disable']:
                thinking_desc += " [dim](必開)[/dim]"

            # 計算價格範圍：從最小到最大 thinking tokens
            cost_min = estimate_thinking_cost(min_token, model_name, input_tokens=0)
            cost_max = estimate_thinking_cost(max_token, model_name, input_tokens=0)

            price_range = f"{cost_min['cost_twd']:.4f} ~ {cost_max['cost_twd']:.4f}"

            table.add_row(
                key,
                description.split('（')[0],  # 只取模型名稱
                thinking_desc,
                price_range
            )
    except Exception as e:
        # 降級為簡單顯示
        logger.warning(f"價格計算失敗：{e}")
        for key, (model_name, description) in RECOMMENDED_MODELS.items():
            table.add_row(key, description, "N/A", "N/A")

    console.print(table)
    console.print("\n[#DA70D6]0.[/#DA70D6] 自訂模型名稱")
    console.print("[dim]─[/dim]" * 60)

    # 預先獲取可用模型列表（用於自訂模型驗證）
    available_models = _get_available_models()

    while True:
        choice = console.input(f"\n[#DDA0DD]請輸入選項 (1-{len(RECOMMENDED_MODELS)} 或 0):[/#DDA0DD] ").strip()

        # 支援 exit/quit 退出
        if choice.lower() in ('exit', 'quit', 'q'):
            console.print("[#DA70D6]已取消選擇[/#DA70D6]")
            import sys
            sys.exit(0)

        if choice == '0':
            # 自訂模型名稱（必須是 API 支援的模型）
            if available_models is None:
                console.print("[#DA70D6]⚠️  無法驗證模型可用性，將直接使用您輸入的模型名稱[/#DA70D6]")
                custom_model = console.input("[#DDA0DD]請輸入模型名稱:[/#DDA0DD] ").strip()
                if custom_model:
                    return custom_model
                else:
                    console.print("[#DA70D6]模型名稱不能為空，請重試[/#DA70D6]")
                    continue

            # 顯示可用模型列表
            console.print("\n[#DDA0DD]可用的 Gemini 模型：[/#DDA0DD]")
            for i, model in enumerate(available_models, 1):
                console.print(f"  [#DA70D6]{i}.[/#DA70D6] [white]{model}[/white]")
            console.print()

            custom_model = console.input("[#DDA0DD]請輸入模型名稱（必須是上列其中一個）:[/#DDA0DD] ").strip()

            if not custom_model:
                console.print("[#DA70D6]模型名稱不能為空，請重試[/#DA70D6]")
                continue

            # 驗證模型是否存在
            if custom_model in available_models:
                return custom_model
            else:
                console.print(f"[#DA70D6]⚠️  模型 '{custom_model}' 不在可用列表中，請重新選擇[/#DA70D6]")
                continue

        if choice in RECOMMENDED_MODELS:
            model_name, _ = RECOMMENDED_MODELS[choice]
            return model_name

        console.print("[#DA70D6]無效的選項，請重試[/#DA70D6]")
