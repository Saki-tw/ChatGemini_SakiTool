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


def _arrow_key_select(models_dict: Dict[str, Tuple[str, str]], console) -> Optional[str]:
    """
    使用方向鍵選擇模型

    Args:
        models_dict: 模型字典 {'1': ('model-name', 'description'), ...}
        console: Rich Console 實例

    Returns:
        選擇的模型鍵（如 '1', '2', ...），或 None 表示取消

    使用方式:
        ↑/↓: 移動選擇
        PgUp/PgDn: 快速移動 (10個選項)
        Home/End: 跳到開頭/結尾
        Enter: 確認選擇
        數字鍵: 快速跳到該選項
        Esc/Ctrl+C: 取消
    """
    from prompt_toolkit import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import Layout, HSplit
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.formatted_text import HTML
    import sys

    try:
        # 建立排序的選項列表
        sorted_items = sorted(
            models_dict.items(),
            key=lambda x: int(x[0]) if x[0].isdigit() else 999
        )

        # 當前選擇的索引與視窗滾動位置
        selected_index = [0]  # 使用列表以便在閉包中修改
        scroll_offset = [0]   # 滾動偏移量

        # 計算可視區域高度（預留 5 行給標題和提示）
        import shutil
        terminal_height = shutil.get_terminal_size().lines
        visible_lines = max(10, terminal_height - 5)  # 至少顯示 10 行

        def get_formatted_text_list():
            """生成格式化的選項列表（支援滾動）"""
            result = []
            result.append(('', '\n'))
            result.append(('class:header', '🔽 使用 ↑↓ 鍵選擇，Enter 確認，Esc 取消\n'))
            result.append(('', '\n'))

            # 計算顯示範圍
            start_idx = scroll_offset[0]
            end_idx = min(len(sorted_items), scroll_offset[0] + visible_lines)

            # 顯示滾動提示
            if start_idx > 0:
                result.append(('class:info', f'  ⬆ 向上還有 {start_idx} 個選項\n'))

            # 顯示當前視窗內的選項
            for idx in range(start_idx, end_idx):
                key, (model_name, desc) = sorted_items[idx]
                if idx == selected_index[0]:
                    # 高亮當前選項
                    result.append(('class:selected', f'  ▶ [{key}] {desc.split("（")[0]}\n'))
                else:
                    result.append(('', f'    [{key}] {desc.split("（")[0]}\n'))

            # 顯示滾動提示
            if end_idx < len(sorted_items):
                remaining = len(sorted_items) - end_idx
                result.append(('class:info', f'  ⬇ 向下還有 {remaining} 個選項\n'))

            result.append(('', '\n'))
            result.append(('class:footer', f'  第 {selected_index[0] + 1}/{len(sorted_items)} 個模型\n'))
            return result

        # 建立鍵綁定
        kb = KeyBindings()

        def adjust_scroll():
            """調整滾動位置以確保當前選項可見"""
            # 如果當前選項在視窗上方，向上滾動
            if selected_index[0] < scroll_offset[0]:
                scroll_offset[0] = selected_index[0]
            # 如果當前選項在視窗下方，向下滾動
            elif selected_index[0] >= scroll_offset[0] + visible_lines:
                scroll_offset[0] = selected_index[0] - visible_lines + 1

        @kb.add(Keys.Up)
        def move_up(event):
            if selected_index[0] > 0:
                selected_index[0] -= 1
                adjust_scroll()

        @kb.add(Keys.Down)
        def move_down(event):
            if selected_index[0] < len(sorted_items) - 1:
                selected_index[0] += 1
                adjust_scroll()

        @kb.add(Keys.PageUp)
        def page_up(event):
            selected_index[0] = max(0, selected_index[0] - 10)
            adjust_scroll()

        @kb.add(Keys.PageDown)
        def page_down(event):
            selected_index[0] = min(len(sorted_items) - 1, selected_index[0] + 10)
            adjust_scroll()

        @kb.add(Keys.Home)
        def go_home(event):
            selected_index[0] = 0
            scroll_offset[0] = 0

        @kb.add(Keys.End)
        def go_end(event):
            selected_index[0] = len(sorted_items) - 1
            # 讓最後一個選項顯示在視窗底部
            scroll_offset[0] = max(0, len(sorted_items) - visible_lines)

        @kb.add(Keys.Enter)
        def confirm(event):
            event.app.exit(result=sorted_items[selected_index[0]][0])

        @kb.add(Keys.Escape)
        @kb.add('c-c')
        def cancel(event):
            event.app.exit(result=None)

        # 數字鍵快速跳轉
        number_input = ['']  # 累積的數字輸入

        for digit in '0123456789':
            def make_digit_handler(d):
                def handle_digit(event):
                    number_input[0] += d
                    # 檢查是否有匹配的選項
                    for idx, (key, _) in enumerate(sorted_items):
                        if key == number_input[0]:
                            selected_index[0] = idx
                            adjust_scroll()  # 調整滾動位置
                            number_input[0] = ''  # 重置
                            break
                    # 如果累積的數字超過2位，重置
                    if len(number_input[0]) > 2:
                        number_input[0] = ''
                return handle_digit
            kb.add(digit)(make_digit_handler(digit))

        # 建立布局
        text_control = FormattedTextControl(
            text=get_formatted_text_list,
            focusable=True,
            show_cursor=False
        )

        window = Window(
            content=text_control,
            wrap_lines=False
        )

        layout = Layout(HSplit([window]))

        # 建立應用程式
        app = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=False,
            mouse_support=False,
            style=None
        )

        # 運行應用程式
        result = app.run()
        console.print()  # 換行
        return result

    except (KeyboardInterrupt, EOFError):
        console.print()
        return None
    except Exception as e:
        logger.debug(f"方向鍵選單失敗: {e}")
        console.print(f"\n[yellow]⚠️  方向鍵選單不可用: {e}[/yellow]\n")
        return None


def _filter_ansi_sequences(input_string: str) -> str:
    """
    過濾 ANSI 轉義序列（方向鍵等控制字元）

    ANSI 轉義序列格式: ESC [ <parameters> <command>
    例如: ↑ = \\x1b[A, ↓ = \\x1b[B, → = \\x1b[C, ← = \\x1b[D

    Args:
        input_string: 原始輸入字串（可能包含 ANSI 序列）

    Returns:
        過濾後的字串（移除所有 ANSI 轉義序列並去除首尾空白）

    Examples:
        >>> _filter_ansi_sequences("^[[A^[[B")
        ""
        >>> _filter_ansi_sequences("hello^[[A")
        "hello"
        >>> _filter_ansi_sequences("^[[Agemini-2.5-pro^[[B")
        "gemini-2.5-pro"
    """
    import re
    return re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', input_string).strip()


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
    '1': ('gemini-3-pro-preview', 'Gemini 3.0 Pro Preview（最新最強）'),
    '2': ('gemini-2.5-flash', 'Gemini 2.5 Flash（推薦,最快）'),
    '3': ('gemini-2.5-pro', 'Gemini 2.5 Pro（強大,較貴）'),
    '4': ('gemini-2.5-flash-lite', 'Gemini 2.5 Flash Lite（輕量版,更便宜）'),
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


def select_model(use_arrow_keys: bool = True) -> str:
    """
    選擇 Gemini 模型（含思考模式資訊與價格預估）

    Args:
        use_arrow_keys: 是否使用方向鍵選單（預設 True）
    """
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

    if use_arrow_keys:
        console.print("\n[dim]💡 提示：使用 ↑↓ 方向鍵選擇模型，Enter 確認，或直接輸入數字[/dim]")
    else:
        console.print("\n[dim]💡 提示：請輸入數字選擇模型[/dim]")

    # 預先獲取可用模型列表（用於自訂模型驗證）
    available_models = _get_available_models()

    # 🎯 方向鍵選單模式
    if use_arrow_keys:
        try:
            selected_key = _arrow_key_select(display_models, console)
            if selected_key is not None:
                if selected_key == '0':
                    # 處理自訂模型（下面會處理）
                    pass
                elif selected_key in display_models:
                    model_name, _ = display_models[selected_key]
                    _save_model_choice(model_name)
                    return model_name
        except KeyboardInterrupt:
            # Ctrl+C 或其他中斷，回到文字輸入模式
            console.print("\n[dim]已切換到文字輸入模式[/dim]")
        except Exception as e:
            logger.debug(f"方向鍵選單失敗，回到文字輸入: {e}")
            console.print("\n[dim]方向鍵選單不可用，使用文字輸入模式[/dim]")

    while True:
        # 使用 i18n 翻譯提示文字,降級為硬編碼
        try:
            prompt_text = t('model.select_prompt', count=len(display_models))
        except (NameError, AttributeError, TypeError):
            prompt_text = f"請輸入選項 (1-{len(display_models)} 或 0)"

        choice_raw = Prompt.ask(f"\n{prompt_text}")
        choice = _filter_ansi_sequences(choice_raw)

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
                custom_model_raw = Prompt.ask(input_prompt)
                custom_model = _filter_ansi_sequences(custom_model_raw)

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
            custom_model_raw = Prompt.ask(enter_prompt)
            custom_model = _filter_ansi_sequences(custom_model_raw)

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
