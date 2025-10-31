#!/usr/bin/env python3
"""
Gemini 模型選擇器
從 gemini_chat.py 抽離
"""

from typing import Optional, List, Dict, Tuple
import logging
from rich.prompt import Prompt

# i18n 國際化
import utils  # 自動初始化並注入 t() 到 builtins

logger = logging.getLogger(__name__)

# 動態模型列表管理
try:
    from gemini_model_list import GeminiModelList
    model_list_manager = GeminiModelList()
except ImportError:
    logger.warning("無法載入 gemini_model_list,將使用靜態模型列表")
    model_list_manager = None


def _save_model_choice(model_name: str):
    """保存使用者選擇的模型"""
    try:
        from CodeGemini.config_manager import ConfigManager
        config_manager = ConfigManager()
        config_manager.config.system.default_model = model_name
        config_manager.save_config()
        logger.debug(f"✓ 模型選擇已保存: {model_name}")
    except Exception as e:
        logger.debug(f"保存模型選擇失敗: {e}")


def get_last_selected_model() -> Optional[str]:
    """取得上次選擇的模型"""
    try:
        from CodeGemini.config_manager import ConfigManager
        config_manager = ConfigManager()
        return config_manager.config.system.default_model
    except Exception:
        return None


# 主要推薦模型（啟動時顯示）
RECOMMENDED_MODELS = {
    '1': ('gemini-2.5-flash', 'Gemini 2.5 Flash（推薦,最快）'),
    '2': ('gemini-2.5-pro', 'Gemini 2.5 Pro（最強,較貴）'),
    '3': ('gemini-2.5-flash-lite', 'Gemini 2.5 Flash Lite（輕量版,更便宜）'),
}


def get_all_available_models() -> Dict[str, Tuple[str, str]]:
    """
    獲取所有可用模型（用於 /model 指令）

    Returns:
        模型字典,格式：{'1': ('model-name', 'description'), ...}
    """
    if model_list_manager:
        try:
            all_models = model_list_manager.get_all_models()
            result = {}
            for idx, model_name in enumerate(all_models, 1):
                # 為模型生成描述
                if 'flash' in model_name.lower():
                    desc = f"{model_name}（快速版）"
                elif 'pro' in model_name.lower():
                    desc = f"{model_name}（專業版）"
                elif 'exp' in model_name.lower():
                    desc = f"{model_name}（實驗版）"
                else:
                    desc = model_name
                result[str(idx)] = (model_name, desc)
            return result
        except Exception as e:
            logger.warning(f"無法從動態列表獲取模型：{e}")

    # 降級：返回推薦模型
    return RECOMMENDED_MODELS


def update_model_list(force: bool = False) -> bool:
    """
    更新模型列表（從 API 獲取最新模型）

    Args:
        force: 是否強制更新（忽略快取）

    Returns:
        更新是否成功
    """
    if model_list_manager:
        return model_list_manager.update_models(force=force)
    return False


def _get_available_models() -> Optional[List[str]]:
    """
    從 API 獲取可用的模型列表

    Returns:
        模型名稱列表,失敗時返回 None
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

    # 🎯 觸發背景載入（v2.3 智能預載入）
    # 使用者選擇模型時,預估有 3-5 秒可用時間,載入 Tier 1 模組
    try:
        from smart_background_loader import on_model_selection_start
        on_model_selection_start()
    except Exception as e:
        logger.debug(f"背景載入觸發失敗（不影響功能）: {e}")

    console.print("\n")

    # 使用 safe_t 支援降級運行
    try:
        from utils import safe_t
        title_text = safe_t('model.selector_title', fallback='🤖 Gemini 模型選擇')
        col_option = safe_t('model.col_option', fallback='選項')
        col_name = safe_t('model.col_name', fallback='模型名稱')
        col_thinking = safe_t('model.col_thinking_range', fallback='Thinking Token 範圍')
        col_price = safe_t('model.col_price_range', fallback='價格範圍 (NT$)')
    except (ImportError, NameError):
        # 降級：使用硬編碼文字
        title_text = '🤖 Gemini 模型選擇'
        col_option = '選項'
        col_name = '模型名稱'
        col_thinking = 'Thinking Token 範圍'
        col_price = '價格範圍 (NT$)'

    console.print(Panel.fit(
        f"[bold #E8C4F0]{title_text}[/bold #E8C4F0]",
        border_style="#E8C4F0"
    ))

    # 🔄 動態獲取所有可用模型
    all_models = get_all_available_models()

    # 如果動態列表失敗,降級使用推薦模型
    if not all_models or all_models == RECOMMENDED_MODELS:
        logger.debug("使用推薦模型列表")
        display_models = RECOMMENDED_MODELS
    else:
        logger.debug(f"使用動態模型列表（{len(all_models)} 個模型）")
        display_models = all_models

    # 建立模型資訊表格
    table = Table(show_header=True, header_style="bold #E8C4F0", border_style="#E8C4F0")
    table.add_column(col_option, style="#B565D8", justify="center")
    table.add_column(col_name, style="white")
    table.add_column(col_thinking, style="#B565D8")
    table.add_column(col_price, style="#B565D8", justify="right")

    # 導入價格計算
    try:
        from gemini_thinking import get_thinking_budget_info, estimate_thinking_cost
        from gemini_pricing import PricingCalculator

        calculator = PricingCalculator()

        for key, (model_name, description) in display_models.items():
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
        for key, (model_name, description) in display_models.items():
            table.add_row(key, description, "N/A", "N/A")

    console.print(table)

    # 使用 i18n 翻譯或降級為硬編碼文字
    try:
        custom_model_text = t('model.custom_model')
    except (NameError, AttributeError):
        custom_model_text = "自訂模型名稱"

    console.print(f"\n[#B565D8]0.[/#B565D8] {custom_model_text}")
    console.print("[dim]─[/dim]" * 60)

    # 預先獲取可用模型列表（用於自訂模型驗證）
    available_models = _get_available_models()

    while True:
        # 使用 i18n 翻譯提示文字,降級為硬編碼
        try:
            prompt_text = t('model.select_prompt', count=len(display_models))
        except (NameError, AttributeError, TypeError):
            prompt_text = f"請輸入選項 (1-{len(display_models)} 或 0)"

        choice = Prompt.ask(f"\n{prompt_text}")

        # 支援 exit/quit 退出
        if choice.lower() in ('exit', 'quit', 'q'):
            try:
                cancel_text = t('common.cancel')
            except (NameError, AttributeError):
                cancel_text = "已取消選擇"
            console.print(f"[#B565D8]{cancel_text}[/#B565D8]")
            import sys
            sys.exit(0)

        if choice == '0':
            # 自訂模型名稱（必須是 API 支援的模型）
            if available_models is None:
                try:
                    warning_text = t('model.validation_warning')
                except (NameError, AttributeError):
                    warning_text = "⚠️  無法驗證模型可用性,將直接使用您輸入的模型名稱"
                console.print(f"[#B565D8]{warning_text}[/#B565D8]")

                try:
                    input_prompt = t('model.enter_name')
                except (NameError, AttributeError):
                    input_prompt = "請輸入模型名稱"
                custom_model = Prompt.ask(input_prompt)

                if custom_model:
                    _save_model_choice(custom_model)
                    return custom_model
                else:
                    try:
                        empty_text = t('model.name_empty')
                    except (NameError, AttributeError):
                        empty_text = "模型名稱不能為空,請重試"
                    console.print(f"[#B565D8]{empty_text}[/#B565D8]")
                    continue

            # 顯示可用模型列表
            try:
                available_text = t('model.available_models')
            except (NameError, AttributeError):
                available_text = "可用的 Gemini 模型"
            console.print(f"\n[#E8C4F0]{available_text}：[/#E8C4F0]")

            for i, model in enumerate(available_models, 1):
                console.print(f"  [#B565D8]{i}.[/#B565D8] [white]{model}[/white]")
            console.print()

            try:
                enter_prompt = t('model.enter_from_list')
            except (NameError, AttributeError):
                enter_prompt = "請輸入模型名稱（必須是上列其中一個）"
            custom_model = Prompt.ask(enter_prompt)

            if not custom_model:
                try:
                    empty_text = t('model.name_empty')
                except (NameError, AttributeError):
                    empty_text = "模型名稱不能為空,請重試"
                console.print(f"[#B565D8]{empty_text}[/#B565D8]")
                continue

            # 驗證模型是否存在
            if custom_model in available_models:
                _save_model_choice(custom_model)
                return custom_model
            else:
                try:
                    not_in_list_text = t('model.not_in_list', model=custom_model)
                except (NameError, AttributeError):
                    not_in_list_text = f"⚠️  模型 '{custom_model}' 不在可用列表中,請重新選擇"
                console.print(f"[#B565D8]{not_in_list_text}[/#B565D8]")
                continue

        if choice in display_models:
            model_name, _ = display_models[choice]
            # 保存模型選擇
            _save_model_choice(model_name)
            return model_name

        try:
            invalid_text = t('model.invalid_option')
        except (NameError, AttributeError):
            invalid_text = "無效的選項,請重試"
        console.print(f"[#B565D8]{invalid_text}[/#B565D8]")
