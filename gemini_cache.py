#!/usr/bin/env python3
"""
Gemini 自動快取管理器
從 gemini_chat.py 抽離
"""

import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)



class AutoCacheManager:
    """自動快取管理器"""

    def __init__(self, enabled: bool = False, mode: str = 'auto', threshold: int = 5000, ttl: int = 1):
        self.enabled = enabled
        self.mode = mode  # 'auto' 或 'prompt'
        self.threshold = threshold
        self.ttl_hours = ttl
        self.conversation_pairs = []  # [(user_msg, ai_msg, input_tokens), ...]
        self.total_input_tokens = 0
        self.cache_created = False
        self.active_cache = None
        self.exclude_next = False  # 下一次對話是否排除

    def add_conversation(self, user_msg: str, ai_msg: str, input_tokens: int):
        """記錄對話（除非被排除）"""
        if not self.exclude_next:
            self.conversation_pairs.append((user_msg, ai_msg, input_tokens))
            self.total_input_tokens += input_tokens
        self.exclude_next = False  # 重置排除標記

    def should_trigger(self) -> bool:
        """是否應該觸發快取建立"""
        return (self.enabled and
                not self.cache_created and
                self.total_input_tokens >= self.threshold)

    def show_trigger_prompt(self, model_name: str) -> bool:
        """顯示快取觸發提示（含精確成本計算）"""
        width = console.width - 4  # 減去邊距
        print("\n" + "🔔 " + "━" * (width - 2))
        print("快取觸發提醒")
        print("━" * width)
        print(f"📊 目前狀態：")
        print(f"  累積輸入：{self.total_input_tokens:,} tokens")
        print(f"  對話輪次：{len(self.conversation_pairs)} 次")
        print()

        # 計算快取本身的成本與節省
        if PRICING_ENABLED:
            try:
                # 1. 快取建立成本（一次性）
                cache_create_cost, _ = global_pricing_calculator.calculate_text_cost(
                    model_name, self.total_input_tokens, 0, 0
                )

                # 2. 未來使用快取的成本對比
                # 假設後續還會輸入相同數量的 tokens
                future_input = self.total_input_tokens
                future_output = 2000  # 假設平均輸出

                # 不使用快取：每次都要付全額
                no_cache_cost, _ = global_pricing_calculator.calculate_text_cost(
                    model_name, future_input, future_output, 0
                )

                # 使用快取：輸入部分享 90% 折扣
                cache_input_cost, _ = global_pricing_calculator.calculate_text_cost(
                    model_name, future_input, 0, 0
                )
                cache_output_cost, _ = global_pricing_calculator.calculate_text_cost(
                    model_name, 0, future_output, 0
                )
                with_cache_cost = (cache_input_cost * 0.1) + cache_output_cost

                # 每次節省
                per_query_savings = no_cache_cost - with_cache_cost

                # 計算損益平衡點（需要幾次查詢才回本）
                if per_query_savings > 0:
                    breakeven = int(cache_create_cost / per_query_savings) + 1
                else:
                    breakeven = 999

                print(f"💰 成本分析：")
                print(f"  快取建立成本：NT$ {cache_create_cost * USD_TO_TWD:.2f} (一次性)")
                print()
                print(f"  後續每次查詢（{future_input:,} tokens 輸入）：")
                print(f"    不使用快取：NT$ {no_cache_cost * USD_TO_TWD:.2f}")
                print(f"    使用快取：  NT$ {with_cache_cost * USD_TO_TWD:.2f}")
                print(f"    每次節省：  NT$ {per_query_savings * USD_TO_TWD:.2f} (省 {((per_query_savings/no_cache_cost)*100):.0f}%)")
                print()
                print(f"  💡 損益平衡：{breakeven} 次查詢後開始省錢")
                print(f"     (快取有效期 {self.ttl_hours} 小時)")
                print()

            except Exception as e:
                logger.warning(f"成本計算失敗: {e}")

        # 顯示快取內容預覽
        print(f"📦 快取內容預覽：")
        preview_count = min(3, len(self.conversation_pairs))
        for i in range(preview_count):
            user_msg, ai_msg, _ = self.conversation_pairs[i]
            user_preview = user_msg[:50] + "..." if len(user_msg) > 50 else user_msg
            ai_preview = ai_msg[:50] + "..." if len(ai_msg) > 50 else ai_msg
            print(f"  - 你: {user_preview}")
            print(f"  - AI: {ai_preview}")

        if len(self.conversation_pairs) > preview_count:
            print(f"  ... (共 {len(self.conversation_pairs)} 輪對話)")

        print("━" * (console.width - 4))
        response = input("建立快取？ (y/n) [y]: ").strip().lower()
        return response != 'n'

    def create_cache(self, model_name: str) -> bool:
        """建立快取"""
        if not CACHE_ENABLED:
            print("⚠️  快取功能未啟用（gemini_cache_manager.py 未找到）")
            return False

        try:
            # 組合對話歷史 - 優化：使用 list 累積，單次 join（避免 O(n²) 記憶體使用）
            cache_lines = []
            for user_msg, ai_msg, _ in self.conversation_pairs:
                cache_lines.append("User: ")
                cache_lines.append(user_msg)
                cache_lines.append("\n\nAssistant: ")
                cache_lines.append(ai_msg)
                cache_lines.append("\n\n")

            # 單次分配和拷貝 - O(n) 記憶體複雜度
            combined_content = "".join(cache_lines)

            # 建立快取
            print("\n⏳ 建立快取中...")
            cache = global_cache_manager.create_cache(
                model=model_name,
                contents=[combined_content],
                display_name=f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                ttl_hours=self.ttl_hours
            )

            self.active_cache = cache
            self.cache_created = True
            print("✅ 快取建立成功！後續對話將自動使用快取節省成本。\n")
            return True

        except Exception as e:
            print(f"⚠️  快取建立失敗：{e}")
            return False


def parse_cache_control(user_input: str, cache_mgr: 'AutoCacheManager') -> tuple:
    """
    解析快取即時控制指令

    Returns:
        (處理後的輸入, 快取動作)
    """
    import re

    # [cache:now] - 立即建立快取
    if re.search(r'\[cache:now\]', user_input, re.I):
        user_input = re.sub(r'\[cache:now\]', '', user_input, flags=re.I).strip()
        return user_input, 'create_now'

    # [cache:off] - 暫停自動快取
    if re.search(r'\[cache:off\]', user_input, re.I):
        user_input = re.sub(r'\[cache:off\]', '', user_input, flags=re.I).strip()
        cache_mgr.enabled = False
        print("⚠️  自動快取已暫停")
        return user_input, None

    # [cache:on] - 恢復自動快取
    if re.search(r'\[cache:on\]', user_input, re.I):
        user_input = re.sub(r'\[cache:on\]', '', user_input, flags=re.I).strip()
        cache_mgr.enabled = True
        print("✓ 自動快取已恢復")
        return user_input, None

    # [no-cache] - 本次對話不列入快取
    if re.search(r'\[no-cache\]', user_input, re.I):
        user_input = re.sub(r'\[no-cache\]', '', user_input, flags=re.I).strip()
        cache_mgr.exclude_next = True
        print("⚠️  本次對話不列入快取")
        return user_input, None

    return user_input, None
