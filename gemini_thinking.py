#!/usr/bin/env python3
"""
Gemini 思考簽名管理器
從 gemini_chat.py 抽離
"""

from typing import Optional, Dict
import hashlib
import logging

logger = logging.getLogger(__name__)



class ThinkingSignatureManager:
    """思考簽名持久化管理器

    用於保存和載入思考簽名，以維持多輪對話的思考脈絡。
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
                    # 注意：response parts 無法直接序列化，這裡只記錄狀態
                    if self.has_function_calling:
                        logger.info("已載入思考簽名狀態（函數呼叫已啟用）")
                    else:
                        logger.debug("思考簽名狀態：函數呼叫未啟用")
        except Exception as e:
            logger.warning(f"載入思考簽名狀態失敗：{e}")

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
                        logger.debug("已保存思考簽名（含 parts）")
            except Exception as e:
                logger.warning(f"保存思考簽名失敗：{e}")

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
            logger.debug("思考簽名狀態已保存")
        except Exception as e:
            logger.warning(f"保存思考簽名狀態失敗：{e}")

    def get_last_response_parts(self):
        """獲取最後保存的 response parts（用於下次請求）

        Returns:
            最後一次的 response parts，如果沒有則返回 None
        """
        return self.last_response_parts if self.has_function_calling else None

    def clear(self):
        """清除保存的思考簽名"""
        self.last_response_parts = None
        self.has_function_calling = False
        self._save_state()
        logger.info("已清除思考簽名")


def parse_thinking_config(user_input: str, model_name: str = "") -> tuple:
    """
    解析思考模式配置

    支援格式:
    - [think:2000] 使用指定 tokens 思考
    - [think:1000,response:500] 同時指定思考與回應 tokens
    - [think:auto] 或 [think:-1] 動態思考
    - [no-think] 或 [think:0] 不思考（部分模型支援）

    各模型限制：
    - gemini-2.5-pro: -1 (動態) 或 128-32768 tokens，無法停用
    - gemini-2.5-flash: -1 (動態) 或 0-24576 tokens，0=停用
    - gemini-2.5-flash-8b (lite): -1 (動態) 或 512-24576 tokens，0=停用

    Args:
        user_input: 使用者輸入
        model_name: 模型名稱

    Returns:
        (清理後的輸入, 是否使用思考, 思考預算, 最大輸出tokens)
    """
    import re

    # 根據模型判斷限制
    is_pro = 'pro' in model_name.lower()
    is_lite = '8b' in model_name.lower() or 'lite' in model_name.lower()

    # 設定各模型的限制
    if is_pro:
        MAX_TOKENS = 32768
        MIN_TOKENS = 128
        ALLOW_DISABLE = False  # Pro 無法停用思考
    elif is_lite:
        MAX_TOKENS = 24576
        MIN_TOKENS = 512
        ALLOW_DISABLE = True
    else:  # flash
        MAX_TOKENS = 24576
        MIN_TOKENS = 0
        ALLOW_DISABLE = True

    # 預設值
    use_thinking = True
    thinking_budget = -1  # 動態
    max_output_tokens = None  # None 表示使用模型預設值

    # 檢查是否禁用思考
    no_think_pattern = r'\[no-think\]'
    if re.search(no_think_pattern, user_input, re.IGNORECASE):
        if not ALLOW_DISABLE:
            print(f"⚠️  {model_name} 不支援停用思考，將使用動態模式")
            thinking_budget = -1
        else:
            thinking_budget = 0
        user_input = re.sub(no_think_pattern, '', user_input, flags=re.IGNORECASE).strip()
        return user_input, use_thinking, thinking_budget, max_output_tokens

    # 檢查帶 response 參數的思考預算: [think:1000,response:500]
    think_response_pattern = r'\[think:(-?\d+|auto),\s*response:(\d+)\]'
    match = re.search(think_response_pattern, user_input, re.IGNORECASE)
    if match:
        budget_str = match.group(1).lower()
        response_tokens = int(match.group(2))

        # 處理思考預算
        if budget_str == 'auto':
            thinking_budget = -1
        else:
            thinking_budget = int(budget_str)

            # 驗證思考預算範圍
            if thinking_budget == 0:
                if not ALLOW_DISABLE:
                    print(f"⚠️  {model_name} 不支援停用思考（0 tokens），已調整為最小值 {MIN_TOKENS} tokens")
                    thinking_budget = MIN_TOKENS
            elif thinking_budget == -1:
                pass  # 保持 -1
            elif thinking_budget < MIN_TOKENS:
                print(f"⚠️  思考預算低於最小值 {MIN_TOKENS} tokens，已調整")
                thinking_budget = MIN_TOKENS
            elif thinking_budget > MAX_TOKENS:
                print(f"⚠️  思考預算超過上限 {MAX_TOKENS:,} tokens，已調整為最大值")
                thinking_budget = MAX_TOKENS

        # 設定輸出 tokens（最大 8192）
        if response_tokens < 1:
            print(f"⚠️  回應 tokens 至少為 1，已調整")
            max_output_tokens = 1
        elif response_tokens > 8192:
            print(f"⚠️  回應 tokens 超過上限 8192，已調整為最大值")
            max_output_tokens = 8192
        else:
            max_output_tokens = response_tokens

        user_input = re.sub(think_response_pattern, '', user_input, flags=re.IGNORECASE).strip()
        return user_input, use_thinking, thinking_budget, max_output_tokens

    # 檢查單獨的思考預算: [think:2000]
    think_pattern = r'\[think:(-?\d+|auto)\]'
    match = re.search(think_pattern, user_input, re.IGNORECASE)
    if match:
        budget_str = match.group(1).lower()
        if budget_str == 'auto':
            thinking_budget = -1
        else:
            thinking_budget = int(budget_str)

            # 處理停用請求 (0)
            if thinking_budget == 0:
                if not ALLOW_DISABLE:
                    print(f"⚠️  {model_name} 不支援停用思考（0 tokens），已調整為最小值 {MIN_TOKENS} tokens")
                    thinking_budget = MIN_TOKENS
                # else: thinking_budget = 0 保持不變
            # 處理動態請求 (-1)
            elif thinking_budget == -1:
                pass  # 保持 -1
            # 處理指定 tokens
            elif thinking_budget < MIN_TOKENS:
                print(f"⚠️  思考預算低於最小值 {MIN_TOKENS} tokens，已調整")
                thinking_budget = MIN_TOKENS
            elif thinking_budget > MAX_TOKENS:
                print(f"⚠️  思考預算超過上限 {MAX_TOKENS:,} tokens，已調整為最大值")
                thinking_budget = MAX_TOKENS

        user_input = re.sub(think_pattern, '', user_input, flags=re.IGNORECASE).strip()

    return user_input, use_thinking, thinking_budget, max_output_tokens

