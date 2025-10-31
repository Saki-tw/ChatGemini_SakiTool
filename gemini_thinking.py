#!/usr/bin/env python3
"""
Gemini 思考簽名管理器
從 gemini_chat.py 抽離
"""

from typing import Optional, Dict
import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 安全翻譯函數（支援降級運行）
try:
    from utils import safe_t
except ImportError:
    # 降級：使用基本 fallback 函數
    def safe_t(key: str, fallback: str = None, **kwargs):
        """降級版本的 safe_t"""
        if fallback is None:
            fallback = key.split('.')[-1].replace('_', ' ').title()
        try:
            return fallback.format(**kwargs) if kwargs else fallback
        except (KeyError, ValueError):
            return fallback

# 預設日誌目錄
DEFAULT_LOG_DIR = str(Path(__file__).parent / "ChatLogs")


class ThinkingSignatureManager:
    """思考簽名持久化管理器

    用於保存和載入思考簽名,以維持多輪對話的思考脈絡。
    注意：思考簽名僅在啟用函數呼叫時產生。
    """

    def __init__(self, state_dir: str = DEFAULT_LOG_DIR):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.state_file = os.path.join(state_dir, "thinking_signature_state.json")
        self.last_response_parts = None  # 保存最後一次完整的 response parts
        self.has_function_calling = False  # 標記是否啟用函數呼叫

        # 啟動時自動載入
        self._load_state()

    def _load_state(self):
        """從檔案載入最後保存的思考簽名狀態"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.has_function_calling = data.get('has_function_calling', False)
                    # 注意：response parts 無法直接序列化,這裡只記錄狀態
                    if self.has_function_calling:
                        logger.info(safe_t('thinking.signature_loaded',
                                         fallback="已載入思考簽名狀態（函數呼叫已啟用）"))
                    else:
                        logger.debug(safe_t('thinking.signature_disabled',
                                          fallback="思考簽名狀態：函數呼叫未啟用"))
        except Exception as e:
            logger.warning(safe_t('thinking.load_failed',
                                fallback="載入思考簽名狀態失敗：{error}",
                                error=str(e)))

    def save_response(self, response, has_function_calling: bool = False):
        """保存完整的 response（包含思考簽名）

        Args:
            response: Gemini API 回應物件
            has_function_calling: 當前請求是否包含函數宣告
        """
        self.has_function_calling = has_function_calling

        if has_function_calling and hasattr(response, 'candidates'):
            # 只有啟用函數呼叫時才保存 parts
            try:
                # 提取完整的 parts（包含 thought_signature）
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        self.last_response_parts = candidate.content.parts
                        logger.debug(safe_t('thinking.signature_saved',
                                          fallback="已保存思考簽名（含 parts）"))
            except Exception as e:
                logger.warning(safe_t('thinking.save_failed',
                                    fallback="保存思考簽名失敗：{error}",
                                    error=str(e)))

        # 保存狀態到檔案
        self._save_state()

    def _save_state(self):
        """保存狀態到檔案"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'has_function_calling': self.has_function_calling,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            logger.debug(safe_t('thinking.state_saved',
                              fallback="思考簽名狀態已保存"))
        except Exception as e:
            logger.warning(safe_t('thinking.state_save_failed',
                                fallback="保存思考簽名狀態失敗：{error}",
                                error=str(e)))

    def get_last_response_parts(self):
        """獲取最後保存的 response parts（用於下次請求）

        Returns:
            最後一次的 response parts,如果沒有則返回 None
        """
        return self.last_response_parts if self.has_function_calling else None

    def clear(self):
        """清除保存的思考簽名"""
        self.last_response_parts = None
        self.has_function_calling = False
        self._save_state()
        logger.info(safe_t('thinking.signature_cleared',
                         fallback="已清除思考簽名"))


def parse_thinking_config(user_input: str, model_name: str = "") -> tuple:
    """
    解析思考模式配置

    支援格式:
    - [think:2000] 使用指定 tokens 思考
    - [think:1000,response:500] 同時指定思考與回應 tokens
    - [think:auto] 或 [think:-1] 動態思考
    - [no-think] 或 [think:0] 不思考（部分模型支援）
    - [max_token:500] 單獨限制輸出長度（可與 think 同時使用）
    - [think:2000] [max_token:500] 可同時使用（分別控制思考與輸出）

    各模型限制（基於 Google 官方文檔,2025-10-29）：

    Thinking Tokens:
    - gemini-2.5-pro: -1 (動態) 或 512-32768 tokens,無法停用
    - gemini-2.5-flash: -1 (動態) 或 0-24576 tokens,0=停用
    - gemini-2.5-flash-lite: -1 (動態) 或 512-24576 tokens,0=停用

    Max Output Tokens:
    - gemini-2.5-pro/flash/flash-lite: 1-65536 tokens
    - gemini-2.0-flash: 1-8192 tokens

    Args:
        user_input: 使用者輸入
        model_name: 模型名稱

    Returns:
        (清理後的輸入, 是否使用思考, 思考預算, 最大輸出tokens)
    """
    import re

    # 判斷模型類型
    is_pro = 'pro' in model_name.lower()
    is_lite = '8b' in model_name.lower() or 'lite' in model_name.lower()
    is_2_0 = '2.0' in model_name or '2-0' in model_name

    # ============================================================================
    # 根據官方文檔設定各模型的硬限制（2025-10-29）
    # ============================================================================

    # Thinking Tokens 限制
    if is_pro:
        THINK_MAX = 32768    # 官方文檔值,API 可能實際限制為 24576
        THINK_MIN = 512      # API 實際驗證值（文檔提到 128 但不穩定）
        ALLOW_DISABLE = False
    elif is_lite:
        THINK_MAX = 24576
        THINK_MIN = 512
        ALLOW_DISABLE = True
    else:  # flash (2.5)
        THINK_MAX = 24576
        THINK_MIN = 0        # Flash 可設為 0 停用思考
        ALLOW_DISABLE = True

    # Max Output Tokens 限制
    if is_2_0:
        OUTPUT_MAX = 8192    # Gemini 2.0 系列上限
    else:
        OUTPUT_MAX = 65536   # Gemini 2.5 系列上限

    OUTPUT_MIN = 1           # 所有模型最小值

    # 預設值
    use_thinking = True
    thinking_budget = -1  # 動態
    max_output_tokens = None  # None 表示使用模型預設值

    # 1. 檢查輸出限制：[max_token:N] 或 [max:N] 或 [output:N]（三者為同義詞）
    max_token_pattern = r'\[(?:max_token|max|output):(\d+)\]'
    max_token_match = re.search(max_token_pattern, user_input, re.IGNORECASE)
    if max_token_match:
        try:
            output_tokens = int(max_token_match.group(1))
            # 防止惡意超大值（溢位保護）
            if output_tokens > 2**31 - 1:  # INT_MAX
                print(safe_t('thinking.overflow_protection',
                            fallback="❌ 數值過大（溢位保護）,已限制為模型最大值 {max:,}",
                            max=OUTPUT_MAX))
                output_tokens = OUTPUT_MAX
        except (ValueError, OverflowError) as e:
            logger.warning(f"解析 max_token 時發生錯誤: {e}")
            print(safe_t('thinking.parse_error',
                        fallback="❌ 數值解析失敗,已使用預設值"))
            output_tokens = OUTPUT_MAX

        # 嚴格驗證範圍（防止溢位漏洞）
        if output_tokens < OUTPUT_MIN:
            print(safe_t('thinking.output_below_min',
                        fallback="❌ 輸出 tokens 不可小於 {min},已調整",
                        min=OUTPUT_MIN))
            max_output_tokens = OUTPUT_MIN
        elif output_tokens > OUTPUT_MAX:
            print(safe_t('thinking.output_above_max',
                        fallback="❌ 輸出 tokens 超過 {model} 上限 {max:,},已調整為最大值",
                        model=model_name,
                        max=OUTPUT_MAX))
            max_output_tokens = OUTPUT_MAX
        else:
            max_output_tokens = output_tokens

        # 顯示價格預估（動態範圍）
        try:
            from utils import get_pricing_calculator, USD_TO_TWD, PRICING_ENABLED

            if PRICING_ENABLED:
                pricing_calc = get_pricing_calculator(silent=True)
                if pricing_calc:
                    pricing = pricing_calc.get_model_pricing(model_name)
                    output_price = pricing.get('output', pricing.get('output_low', 0))

                    # 計算價格範圍（假設實際使用 50%-100%）
                    min_tokens = int(max_output_tokens * 0.5)
                    max_tokens = max_output_tokens

                    min_cost_usd = (min_tokens / 1000) * output_price
                    max_cost_usd = (max_tokens / 1000) * output_price
                    min_cost_twd = min_cost_usd * USD_TO_TWD
                    max_cost_twd = max_cost_usd * USD_TO_TWD

                    print(safe_t('thinking.max_token_with_cost_range',
                                fallback='📊 [輸出上限] {tokens:,} tokens | 預估成本：NT$ {min_twd:.4f}~{max_twd:.4f} (${min_usd:.6f}~${max_usd:.6f})',
                                tokens=max_output_tokens,
                                min_twd=min_cost_twd,
                                max_twd=max_cost_twd,
                                min_usd=min_cost_usd,
                                max_usd=max_cost_usd))
                else:
                    print(safe_t('thinking.max_token_limit',
                                fallback='📊 [輸出上限] {tokens:,} tokens',
                                tokens=max_output_tokens))
            else:
                print(safe_t('thinking.max_token_limit',
                            fallback='📊 [輸出上限] {tokens:,} tokens',
                            tokens=max_output_tokens))
        except (ImportError, KeyError, AttributeError, TypeError) as e:
            logger.debug(f"價格預估失敗: {e}")
            print(safe_t('thinking.max_token_limit',
                        fallback='📊 [輸出上限] {tokens:,} tokens',
                        tokens=max_output_tokens))

        # 移除輸出限制標記（[max_token:N]、[max:N]、[output:N]）
        user_input = re.sub(max_token_pattern, '', user_input, flags=re.IGNORECASE).strip()

    # 2. 檢查是否禁用思考
    no_think_pattern = r'\[no-think\]'
    if re.search(no_think_pattern, user_input, re.IGNORECASE):
        if not ALLOW_DISABLE:
            print(safe_t('thinking.no_disable_warning',
                        fallback="⚠️  {model} 不支援停用思考,將使用動態模式",
                        model=model_name))
            thinking_budget = -1
        else:
            thinking_budget = 0
        user_input = re.sub(no_think_pattern, '', user_input, flags=re.IGNORECASE).strip()
        return user_input, use_thinking, thinking_budget, max_output_tokens

    # 3. 檢查帶 response 參數的思考預算: [think:1000,response:500]
    think_response_pattern = r'\[think:(-?\d+|auto),\s*response:(\d+)\]'
    match = re.search(think_response_pattern, user_input, re.IGNORECASE)
    if match:
        budget_str = match.group(1).lower()

        # 解析並保護 response tokens
        try:
            response_tokens = int(match.group(2))
            if response_tokens > 2**31 - 1:
                print(safe_t('thinking.overflow_protection',
                            fallback="❌ response 數值過大,已限制為模型最大值 {max:,}",
                            max=OUTPUT_MAX))
                response_tokens = OUTPUT_MAX
        except (ValueError, OverflowError) as e:
            logger.warning(f"解析 response 時發生錯誤: {e}")
            response_tokens = OUTPUT_MAX

        # 處理思考預算
        if budget_str == 'auto':
            thinking_budget = -1
        else:
            try:
                thinking_budget = int(budget_str)
                if thinking_budget > 2**31 - 1 and thinking_budget != -1:
                    print(safe_t('thinking.overflow_protection',
                                fallback="❌ think 數值過大,已限制為模型最大值 {max:,}",
                                max=THINK_MAX))
                    thinking_budget = THINK_MAX
            except (ValueError, OverflowError) as e:
                logger.warning(f"解析 thinking_budget 時發生錯誤: {e}")
                thinking_budget = -1  # 降級到 auto

            # 驗證思考預算範圍
            if thinking_budget == 0:
                if not ALLOW_DISABLE:
                    print(safe_t('thinking.no_disable_adjusted',
                                fallback="⚠️  {model} 不支援停用思考（0 tokens）,已調整為最小值 {min_tokens} tokens",
                                model=model_name, min_tokens=THINK_MIN))
                    thinking_budget = THINK_MIN
            elif thinking_budget == -1:
                pass  # 保持 -1
            elif thinking_budget < THINK_MIN:
                print(safe_t('thinking.budget_below_min',
                            fallback="⚠️  思考預算低於最小值 {min_tokens} tokens,已調整",
                            min_tokens=THINK_MIN))
                thinking_budget = THINK_MIN
            elif thinking_budget > THINK_MAX:
                print(safe_t('thinking.budget_above_max',
                            fallback="⚠️  思考預算超過上限 {max_tokens:,} tokens,已調整為最大值",
                            max_tokens=THINK_MAX))
                thinking_budget = THINK_MAX

        # 設定輸出 tokens（使用模型限制）
        if response_tokens < OUTPUT_MIN:
            print(safe_t('thinking.response_below_min',
                        fallback="❌ 回應 tokens 不可小於 {min},已調整",
                        min=OUTPUT_MIN))
            max_output_tokens = OUTPUT_MIN
        elif response_tokens > OUTPUT_MAX:
            print(safe_t('thinking.response_above_max',
                        fallback="❌ 回應 tokens 超過 {model} 上限 {max:,},已調整為最大值",
                        model=model_name,
                        max=OUTPUT_MAX))
            max_output_tokens = OUTPUT_MAX
        else:
            max_output_tokens = response_tokens

        # 顯示價格預估（動態範圍）
        try:
            from utils import get_pricing_calculator, USD_TO_TWD, PRICING_ENABLED

            if PRICING_ENABLED:
                pricing_calc = get_pricing_calculator(silent=True)
                if pricing_calc:
                    pricing = pricing_calc.get_model_pricing(model_name)
                    input_price = pricing.get('input', pricing.get('input_low', 0))
                    output_price = pricing.get('output', pricing.get('output_low', 0))

                    # 思考成本範圍（假設實際使用 50%-100%）
                    if thinking_budget > 0:
                        min_think_tokens = int(thinking_budget * 0.5)
                        max_think_tokens = thinking_budget
                        min_think_cost_usd = (min_think_tokens / 1000) * input_price
                        max_think_cost_usd = (max_think_tokens / 1000) * input_price
                        min_think_cost_twd = min_think_cost_usd * USD_TO_TWD
                        max_think_cost_twd = max_think_cost_usd * USD_TO_TWD
                    else:
                        min_think_cost_twd = max_think_cost_twd = 0
                        min_think_cost_usd = max_think_cost_usd = 0

                    # 輸出成本範圍（假設實際使用 50%-100%）
                    min_output_tokens = int(max_output_tokens * 0.5)
                    max_output_tokens_val = max_output_tokens
                    min_output_cost_usd = (min_output_tokens / 1000) * output_price
                    max_output_cost_usd = (max_output_tokens_val / 1000) * output_price
                    min_output_cost_twd = min_output_cost_usd * USD_TO_TWD
                    max_output_cost_twd = max_output_cost_usd * USD_TO_TWD

                    # 總成本範圍
                    total_min_twd = min_think_cost_twd + min_output_cost_twd
                    total_max_twd = max_think_cost_twd + max_output_cost_twd
                    total_min_usd = min_think_cost_usd + min_output_cost_usd
                    total_max_usd = max_think_cost_usd + max_output_cost_usd

                    if thinking_budget == -1:
                        think_display = 'auto'
                    elif thinking_budget == 0:
                        think_display = '0'
                    else:
                        think_display = f'{thinking_budget:,}'

                    print(safe_t('thinking.think_response_with_cost_range',
                                fallback='🧠 [思考模式] think:{think} + response:{response:,} | 預估成本：NT$ {min_twd:.4f}~{max_twd:.4f} (${min_usd:.6f}~${max_usd:.6f})',
                                think=think_display,
                                response=max_output_tokens,
                                min_twd=total_min_twd,
                                max_twd=total_max_twd,
                                min_usd=total_min_usd,
                                max_usd=total_max_usd))
                else:
                    print(safe_t('thinking.think_response_set',
                                fallback='🧠 [思考模式] think:{think} + response:{response:,}',
                                think='auto' if thinking_budget == -1 else thinking_budget,
                                response=max_output_tokens))
            else:
                print(safe_t('thinking.think_response_set',
                            fallback='🧠 [思考模式] think:{think} + response:{response:,}',
                            think='auto' if thinking_budget == -1 else thinking_budget,
                            response=max_output_tokens))
        except (ImportError, KeyError, AttributeError, TypeError) as e:
            logger.debug(f"價格預估失敗: {e}")
            print(safe_t('thinking.think_response_set',
                        fallback='🧠 [思考模式] think:{think} + response:{response:,}',
                        think='auto' if thinking_budget == -1 else thinking_budget,
                        response=max_output_tokens))

        user_input = re.sub(think_response_pattern, '', user_input, flags=re.IGNORECASE).strip()
        return user_input, use_thinking, thinking_budget, max_output_tokens

    # 4. 檢查單獨的思考預算: [think:2000]
    think_pattern = r'\[think:(-?\d+|auto)\]'
    match = re.search(think_pattern, user_input, re.IGNORECASE)
    if match:
        budget_str = match.group(1).lower()
        if budget_str == 'auto':
            thinking_budget = -1
        else:
            try:
                thinking_budget = int(budget_str)
                # 溢位保護
                if thinking_budget > 2**31 - 1 and thinking_budget != -1:
                    print(safe_t('thinking.overflow_protection',
                                fallback="❌ think 數值過大,已限制為模型最大值 {max:,}",
                                max=THINK_MAX))
                    thinking_budget = THINK_MAX
            except (ValueError, OverflowError) as e:
                logger.warning(f"解析 thinking_budget 時發生錯誤: {e}")
                thinking_budget = -1  # 降級到 auto

            # 處理停用請求 (0)
            if thinking_budget == 0:
                if not ALLOW_DISABLE:
                    print(safe_t('thinking.no_disable_adjusted',
                                fallback="⚠️  {model} 不支援停用思考（0 tokens）,已調整為最小值 {min_tokens} tokens",
                                model=model_name, min_tokens=THINK_MIN))
                    thinking_budget = THINK_MIN
                # else: thinking_budget = 0 保持不變
            # 處理動態請求 (-1)
            elif thinking_budget == -1:
                pass  # 保持 -1
            # 處理指定 tokens
            elif thinking_budget < THINK_MIN:
                print(safe_t('thinking.budget_below_min',
                            fallback="⚠️  思考預算低於最小值 {min_tokens} tokens,已調整",
                            min_tokens=THINK_MIN))
                thinking_budget = THINK_MIN
            elif thinking_budget > THINK_MAX:
                print(safe_t('thinking.budget_above_max',
                            fallback="⚠️  思考預算超過上限 {max_tokens:,} tokens,已調整為最大值",
                            max_tokens=THINK_MAX))
                thinking_budget = THINK_MAX

        # 顯示價格預估（僅思考 tokens）
        if thinking_budget > 0:
            try:
                from utils import get_pricing_calculator, USD_TO_TWD, PRICING_ENABLED

                if PRICING_ENABLED:
                    pricing_calc = get_pricing_calculator(silent=True)
                    if pricing_calc:
                        pricing = pricing_calc.get_model_pricing(model_name)
                        input_price = pricing.get('input', pricing.get('input_low', 0))

                        # 思考成本範圍（假設實際使用 50%-100%）
                        min_tokens = int(thinking_budget * 0.5)
                        max_tokens = thinking_budget

                        min_cost_usd = (min_tokens / 1000) * input_price
                        max_cost_usd = (max_tokens / 1000) * input_price
                        min_cost_twd = min_cost_usd * USD_TO_TWD
                        max_cost_twd = max_cost_usd * USD_TO_TWD

                        print(safe_t('thinking.think_with_cost_range',
                                    fallback='🧠 [思考預算] {tokens:,} tokens | 預估成本：NT$ {min_twd:.4f}~{max_twd:.4f} (${min_usd:.6f}~${max_usd:.6f})',
                                    tokens=thinking_budget,
                                    min_twd=min_cost_twd,
                                    max_twd=max_cost_twd,
                                    min_usd=min_cost_usd,
                                    max_usd=max_cost_usd))
                    else:
                        print(safe_t('thinking.think_set',
                                    fallback='🧠 [思考預算] {tokens:,} tokens',
                                    tokens=thinking_budget))
                else:
                    print(safe_t('thinking.think_set',
                                fallback='🧠 [思考預算] {tokens:,} tokens',
                                tokens=thinking_budget))
            except (ImportError, KeyError, AttributeError, TypeError) as e:
                logger.debug(f"價格預估失敗: {e}")
                print(safe_t('thinking.think_set',
                            fallback='🧠 [思考預算] {tokens:,} tokens',
                            tokens=thinking_budget))
        elif thinking_budget == -1:
            print(safe_t('thinking.think_auto',
                        fallback='🧠 [思考預算] 自動（動態決定深度）'))
        elif thinking_budget == 0:
            print(safe_t('thinking.think_disabled',
                        fallback='🧠 [思考預算] 已停用'))

        user_input = re.sub(think_pattern, '', user_input, flags=re.IGNORECASE).strip()

    return user_input, use_thinking, thinking_budget, max_output_tokens


def get_thinking_budget_info(model_name: str) -> dict:
    """
    取得各模型的 thinking budget 參考資訊

    Args:
        model_name: 模型名稱

    Returns:
        {
            'min': 最小值,
            'max': 最大值,
            'default': 預設值 (-1),
            'allow_disable': 是否可停用 (0),
            'recommended': [推薦值列表],
            'description': 說明
        }
    """
    is_pro = 'pro' in model_name.lower()
    is_lite = '8b' in model_name.lower() or 'lite' in model_name.lower()

    if is_pro:
        return {
            'min': 128,
            'max': 32768,
            'default': -1,
            'allow_disable': False,
            'recommended': [
                (-1, '自動（推薦）', '模型自動決定思考深度'),
                (1024, '輕量思考', '簡單任務,快速回應'),
                (4096, '標準思考', '一般複雜度任務'),
                (8192, '深度思考', '需要仔細推理的任務'),
                (16384, '極深思考', '高度複雜的邏輯問題'),
            ],
            'description': 'gemini-2.5-pro: 無法停用思考,最小 128 tokens'
        }
    elif is_lite:
        return {
            'min': 512,
            'max': 24576,
            'default': -1,
            'allow_disable': True,
            'recommended': [
                (-1, '自動（推薦）', '模型自動決定思考深度'),
                (0, '不思考', '最快速度,最低成本'),
                (1024, '輕量思考', '簡單推理'),
                (2048, '標準思考', '一般任務'),
                (4096, '深度思考', '複雜推理'),
            ],
            'description': 'gemini-2.5-flash-lite: 可停用,最小 512 tokens'
        }
    else:  # flash
        return {
            'min': 0,
            'max': 24576,
            'default': -1,
            'allow_disable': True,
            'recommended': [
                (-1, '自動（推薦）', '模型自動決定思考深度'),
                (0, '不思考', '最快速度,最低成本'),
                (1024, '輕量思考', '簡單推理'),
                (2048, '標準思考', '一般任務'),
                (4096, '深度思考', '複雜推理'),
                (8192, '極深思考', '高難度問題'),
            ],
            'description': 'gemini-2.5-flash: 可停用,最小 0 tokens'
        }


def estimate_thinking_cost(thinking_budget: int, model_name: str, input_tokens: int = 1000) -> dict:
    """
    預估使用特定 thinking budget 的成本

    Args:
        thinking_budget: 思考預算 (-1 或具體數值)
        model_name: 模型名稱
        input_tokens: 預估的輸入 tokens（預設 1000）

    Returns:
        {
            'thinking_tokens': 預估思考 tokens,
            'cost_usd': 美元成本,
            'cost_twd': 新台幣成本,
            'note': 說明
        }
    """
    # 導入計價模組
    try:
        from gemini_pricing import PricingCalculator
        calculator = PricingCalculator()
        pricing = calculator.get_model_pricing(model_name)
    except:
        # 無法載入計價模組,使用簡化計算
        pricing = {'input': 0.00015625}  # Flash 預設價格

    # 如果是動態模式 (-1),使用範圍中位數作為預估
    if thinking_budget == -1:
        info = get_thinking_budget_info(model_name)
        # 動態模式預估：使用 max 的 30%（經驗值）
        estimated_thinking = int(info['max'] * 0.3)
        note = '動態模式（實際用量依任務複雜度而定）'
    else:
        estimated_thinking = thinking_budget
        note = '固定預算模式'

    # 計算成本（thinking tokens 按 input 計價）
    total_input = input_tokens + estimated_thinking

    if 'threshold' in pricing:
        # 分級定價
        if total_input <= pricing['threshold']:
            cost_usd = (total_input / 1000) * pricing['input_low']
        else:
            low = (pricing['threshold'] / 1000) * pricing['input_low']
            high = ((total_input - pricing['threshold']) / 1000) * pricing['input_high']
            cost_usd = low + high
    else:
        # 固定定價
        cost_usd = (total_input / 1000) * pricing.get('input', 0)

    # 換算新台幣（使用 config 中的匯率）
    try:
        import config
        usd_to_twd = config.USD_TO_TWD
    except:
        usd_to_twd = 31.0

    cost_twd = cost_usd * usd_to_twd

    return {
        'thinking_tokens': estimated_thinking,
        'cost_usd': cost_usd,
        'cost_twd': cost_twd,
        'note': note
    }


def validate_thinking_budget(thinking_budget: int, model_name: str) -> int:
    """
    驗證並修正 thinking_budget,確保符合模型限制

    Args:
        thinking_budget: 使用者指定的思考預算
        model_name: 模型名稱

    Returns:
        修正後的思考預算（-1 或符合模型限制的值）
    """
    # -1 (自動思考) 所有模型都支援,直接返回
    if thinking_budget == -1:
        return -1

    # 根據模型判斷限制
    is_pro = 'pro' in model_name.lower()
    is_lite = '8b' in model_name.lower() or 'lite' in model_name.lower()

    # 設定各模型的限制
    if is_pro:
        THINK_MAX = 32768
        THINK_MIN = 128
        ALLOW_DISABLE = False
    elif is_lite:
        THINK_MAX = 24576
        THINK_MIN = 512
        ALLOW_DISABLE = True
    else:  # flash
        THINK_MAX = 24576
        THINK_MIN = 0
        ALLOW_DISABLE = True

    # 檢查是否為停用 (0)
    if thinking_budget == 0:
        if not ALLOW_DISABLE:
            # Pro 不支援停用,改用自動模式
            return -1
        return 0

    # 檢查是否低於最小值
    if thinking_budget < THINK_MIN:
        # 低於最小值,使用自動模式
        return -1

    # 檢查是否超過最大值
    if thinking_budget > THINK_MAX:
        # 超過最大值,使用最大值
        return THINK_MAX

    # 符合限制,返回原值
    return thinking_budget

