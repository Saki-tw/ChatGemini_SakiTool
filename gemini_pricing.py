#!/usr/bin/env python3
"""
Gemini API 即時計價模組
根據 token 使用量計算成本
支援新台幣顯示、思考模式 token 計價
"""
from typing import Dict, Tuple, Optional
from datetime import datetime
from utils.i18n import t, _

# 美元兌新台幣匯率（2025年10月）
# 若匯率有較大變動，請更新此值
USD_TO_TWD = 31.0

# Gemini API 定價表（2025年1月）
# 價格單位：美元 / 1000 tokens
PRICING_TABLE: Dict[str, Dict[str, float]] = {
    # Gemini 2.5 系列
    'gemini-2.5-pro': {
        'input_low': 0.00125,      # ≤200K tokens
        'output_low': 0.01,
        'input_high': 0.0025,      # >200K tokens
        'output_high': 0.015,
        'threshold': 200000,
    },
    'gemini-2.5-flash': {
        'input': 0.00015625,        # $0.15625 / 1M tokens
        'output': 0.000625,         # $0.625 / 1M tokens
    },
    'gemini-2.5-flash-8b': {
        'input': 0.00003125,        # $0.03125 / 1M tokens
        'output': 0.000125,         # $0.125 / 1M tokens
    },

    # Gemini 2.0 系列
    'gemini-2.0-flash-exp': {
        'input': 0.0001,            # $0.10 / 1M tokens
        'output': 0.0004,           # $0.40 / 1M tokens
    },
    'gemini-2.0-flash-thinking-exp': {
        'input': 0.0001,
        'output': 0.0004,
    },

    # Gemini 1.5 系列
    'gemini-1.5-pro': {
        'input_low': 0.00125,       # ≤128K tokens
        'output_low': 0.005,
        'input_high': 0.0025,       # >128K tokens
        'output_high': 0.015,
        'threshold': 128000,
    },
    'gemini-1.5-flash': {
        'input_low': 0.00003125,    # ≤128K tokens
        'output_low': 0.000125,
        'input_high': 0.0000625,    # >128K tokens
        'output_high': 0.00025,
        'threshold': 128000,
    },
    'gemini-1.5-flash-8b': {
        'input_low': 0.00001875,    # ≤128K tokens
        'output_low': 0.000075,
        'input_high': 0.0000375,    # >128K tokens
        'output_high': 0.00015,
        'threshold': 128000,
    },

    # 實驗版模型
    'gemini-exp-1206': {
        'input': 0.0,               # 實驗版免費
        'output': 0.0,
    },

    # 預設（Flash 定價）
    'default': {
        'input': 0.00015625,
        'output': 0.000625,
    }
}

# Veo 影片生成定價
VEO_PRICING = {
    'veo-3.1-generate-preview': {
        'per_second': 0.75,         # $0.75 per second
    },
    'veo-3.1-fast-generate-preview': {
        'per_second': 0.75,
    },
    'veo-3.0-generate-preview': {
        'per_second': 0.75,
    },
}

# Imagen 圖片生成定價 (2025年1月)
IMAGEN_PRICING = {
    'imagen-3.0-generate-001': {
        'per_image': 0.04,          # $0.04 per image (standard quality)
        'per_image_hd': 0.08,       # $0.08 per image (HD quality)
    },
    'imagen-3.0-fast-generate-001': {
        'per_image': 0.04,
    },
    'imagen-3.0-capability-upscale-001': {
        'per_image': 0.06,          # $0.06 per upscale
    },
    'imagen-3.0-capability-edit-001': {
        'per_image': 0.05,          # $0.05 per edit
    },
}


class PricingCalculator:
    """即時計價計算器"""

    def __init__(self):
        self.total_cost = 0.0
        self.session_start = datetime.now()
        self.transactions = []

    def get_model_pricing(self, model_name: str) -> Dict:
        """
        獲取模型定價

        Args:
            model_name: 模型名稱

        Returns:
            定價資訊字典
        """
        # 精確匹配
        if model_name in PRICING_TABLE:
            return PRICING_TABLE[model_name]

        # 部分匹配
        for key in PRICING_TABLE.keys():
            if key in model_name:
                return PRICING_TABLE[key]

        # 預設定價
        return PRICING_TABLE['default']

    def calculate_text_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0,
        hidden_trigger_tokens: Optional[Dict[str, int]] = None
    ) -> Tuple[float, Dict]:
        """
        計算文字生成成本（含思考模式與智能觸發器成本）

        Args:
            model_name: 模型名稱
            input_tokens: 輸入 token 數（不含思考）
            output_tokens: 輸出 token 數
            thinking_tokens: 思考模式使用的 token 數（按輸入計價）
            hidden_trigger_tokens: 智能觸發器產生的額外 token 用量
                格式: {
                    'api_input': int,     # API 呼叫的 input tokens
                    'api_output': int,    # API 呼叫的 output tokens
                    'model': str          # 使用的模型名稱（可能不同於主對話）
                }

        Returns:
            (總成本, 詳細資訊)
        """
        pricing = self.get_model_pricing(model_name)

        # 總輸入 tokens = 一般輸入 + 思考 tokens
        total_input_tokens = input_tokens + thinking_tokens

        # 處理分級定價
        if 'threshold' in pricing:
            threshold = pricing['threshold']

            if total_input_tokens <= threshold:
                input_cost = (total_input_tokens / 1000) * pricing['input_low']
            else:
                # 分段計算
                low_cost = (threshold / 1000) * pricing['input_low']
                high_cost = ((total_input_tokens - threshold) / 1000) * pricing['input_high']
                input_cost = low_cost + high_cost

            if output_tokens <= threshold:
                output_cost = (output_tokens / 1000) * pricing['output_low']
            else:
                low_cost = (threshold / 1000) * pricing['output_low']
                high_cost = ((output_tokens - threshold) / 1000) * pricing['output_high']
                output_cost = low_cost + high_cost
        else:
            # 固定定價
            input_cost = (total_input_tokens / 1000) * pricing.get('input', 0)
            output_cost = (output_tokens / 1000) * pricing.get('output', 0)

        # 計算思考成本（按輸入計價）
        if thinking_tokens > 0 and 'threshold' in pricing:
            if thinking_tokens <= pricing['threshold']:
                thinking_cost = (thinking_tokens / 1000) * pricing['input_low']
            else:
                low = (pricing['threshold'] / 1000) * pricing['input_low']
                high = ((thinking_tokens - pricing['threshold']) / 1000) * pricing['input_high']
                thinking_cost = low + high
        elif thinking_tokens > 0:
            thinking_cost = (thinking_tokens / 1000) * pricing.get('input', 0)
        else:
            thinking_cost = 0

        # 計算智能觸發器的隱藏成本
        hidden_cost = 0
        hidden_input_tokens = 0
        hidden_output_tokens = 0
        hidden_model = None

        if hidden_trigger_tokens:
            hidden_input_tokens = hidden_trigger_tokens.get('api_input', 0)
            hidden_output_tokens = hidden_trigger_tokens.get('api_output', 0)
            hidden_model = hidden_trigger_tokens.get('model', model_name)

            # 使用觸發器指定的模型計價（可能不同於主對話模型）
            hidden_pricing = self.get_model_pricing(hidden_model)

            # 計算隱藏的輸入成本
            if hidden_input_tokens > 0:
                if 'threshold' in hidden_pricing:
                    if hidden_input_tokens <= hidden_pricing['threshold']:
                        hidden_input_cost = (hidden_input_tokens / 1000) * hidden_pricing['input_low']
                    else:
                        low = (hidden_pricing['threshold'] / 1000) * hidden_pricing['input_low']
                        high = ((hidden_input_tokens - hidden_pricing['threshold']) / 1000) * hidden_pricing['input_high']
                        hidden_input_cost = low + high
                else:
                    hidden_input_cost = (hidden_input_tokens / 1000) * hidden_pricing.get('input', 0)
            else:
                hidden_input_cost = 0

            # 計算隱藏的輸出成本
            if hidden_output_tokens > 0:
                if 'threshold' in hidden_pricing:
                    if hidden_output_tokens <= hidden_pricing['threshold']:
                        hidden_output_cost = (hidden_output_tokens / 1000) * hidden_pricing['output_low']
                    else:
                        low = (hidden_pricing['threshold'] / 1000) * hidden_pricing['output_low']
                        high = ((hidden_output_tokens - hidden_pricing['threshold']) / 1000) * hidden_pricing['output_high']
                        hidden_output_cost = low + high
                else:
                    hidden_output_cost = (hidden_output_tokens / 1000) * hidden_pricing.get('output', 0)
            else:
                hidden_output_cost = 0

            hidden_cost = hidden_input_cost + hidden_output_cost

        total_cost = input_cost + output_cost + thinking_cost + hidden_cost

        # 記錄交易
        transaction = {
            'timestamp': datetime.now(),
            'model': model_name,
            'type': 'text',
            'input_tokens': input_tokens,
            'thinking_tokens': thinking_tokens,
            'output_tokens': output_tokens,
            'input_cost': input_cost,
            'thinking_cost': thinking_cost,
            'output_cost': output_cost,
            'hidden_trigger_tokens': hidden_input_tokens + hidden_output_tokens,
            'hidden_trigger_cost': hidden_cost,
            'total_cost': total_cost
        }
        self.transactions.append(transaction)
        self.total_cost += total_cost

        details = {
            'input_tokens': input_tokens,
            'thinking_tokens': thinking_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + thinking_tokens + output_tokens,
            'input_cost': input_cost,
            'thinking_cost': thinking_cost,
            'output_cost': output_cost,
            'hidden_trigger_input_tokens': hidden_input_tokens,
            'hidden_trigger_output_tokens': hidden_output_tokens,
            'hidden_trigger_cost': hidden_cost,
            'hidden_trigger_model': hidden_model,
            'total_cost': total_cost,
            'total_cost_twd': total_cost * USD_TO_TWD,
            'pricing': pricing
        }

        return total_cost, details

    def calculate_video_generation_cost(
        self,
        model_name: str,
        duration_seconds: int
    ) -> Tuple[float, Dict]:
        """
        計算影片生成成本

        Args:
            model_name: Veo 模型名稱
            duration_seconds: 影片長度（秒）

        Returns:
            (總成本, 詳細資訊)
        """
        if model_name not in VEO_PRICING:
            # 預設使用 Veo 3.1 定價
            model_name = 'veo-3.1-generate-preview'

        per_second = VEO_PRICING[model_name]['per_second']
        total_cost = duration_seconds * per_second

        # 記錄交易
        transaction = {
            'timestamp': datetime.now(),
            'model': model_name,
            'type': 'video_generation',
            'duration_seconds': duration_seconds,
            'per_second_rate': per_second,
            'total_cost': total_cost
        }
        self.transactions.append(transaction)
        self.total_cost += total_cost

        details = {
            'duration_seconds': duration_seconds,
            'per_second_rate': per_second,
            'total_cost': total_cost
        }

        return total_cost, details

    def calculate_image_generation_cost(
        self,
        model_name: str,
        number_of_images: int = 1,
        operation: str = 'generate'
    ) -> Tuple[float, Dict]:
        """
        計算圖片生成成本

        Args:
            model_name: Imagen 模型名稱
            number_of_images: 圖片數量
            operation: 操作類型 ('generate', 'edit', 'upscale')

        Returns:
            (總成本, 詳細資訊)
        """
        if model_name not in IMAGEN_PRICING:
            # 預設使用 Imagen 3.0 定價
            model_name = 'imagen-3.0-generate-001'

        # 根據操作類型選擇價格
        pricing_info = IMAGEN_PRICING[model_name]
        if operation == 'upscale':
            per_image = IMAGEN_PRICING.get('imagen-3.0-capability-upscale-001', {}).get('per_image', 0.06)
        elif operation == 'edit':
            per_image = IMAGEN_PRICING.get('imagen-3.0-capability-edit-001', {}).get('per_image', 0.05)
        else:  # generate
            per_image = pricing_info.get('per_image', 0.04)

        total_cost = number_of_images * per_image

        # 記錄交易
        transaction = {
            'timestamp': datetime.now(),
            'model': model_name,
            'type': f'image_{operation}',
            'number_of_images': number_of_images,
            'per_image_rate': per_image,
            'total_cost': total_cost
        }
        self.transactions.append(transaction)
        self.total_cost += total_cost

        details = {
            'number_of_images': number_of_images,
            'per_image_rate': per_image,
            'operation': operation,
            'total_cost': total_cost
        }

        return total_cost, details

    def calculate_video_understanding_cost(
        self,
        model_name: str,
        video_duration_seconds: int,
        fps: float = 1.0,
        additional_input_tokens: int = 0,
        output_tokens: int = 0
    ) -> Tuple[float, Dict]:
        """
        計算影片理解成本

        影片會被處理成 frames + audio，每個 frame 算作 token

        Args:
            model_name: 模型名稱
            video_duration_seconds: 影片長度（秒）
            fps: 處理的 FPS（Gemini 預設 1 FPS）
            additional_input_tokens: 額外的文字輸入 tokens
            output_tokens: 輸出 tokens

        Returns:
            (總成本, 詳細資訊)
        """
        # 估算影片 token 數
        # 根據 Gemini 文檔，1秒影片 ≈ 258 tokens (1 FPS)
        tokens_per_second = 258
        video_tokens = int(video_duration_seconds * tokens_per_second)

        # 總輸入 tokens = 影片 tokens + 文字 tokens
        total_input_tokens = video_tokens + additional_input_tokens

        # 使用文字成本計算
        cost, details = self.calculate_text_cost(
            model_name,
            total_input_tokens,
            output_tokens
        )

        # 更新細節
        details['video_duration_seconds'] = video_duration_seconds
        details['video_tokens'] = video_tokens
        details['text_input_tokens'] = additional_input_tokens
        details['fps'] = fps

        # 更新交易類型
        if self.transactions:
            self.transactions[-1]['type'] = 'video_understanding'

        return cost, details

    def calculate_flow_engine_cost(
        self,
        target_duration: int,
        segment_duration: int = 8,
        planning_model: str = 'gemini-2.0-flash-exp',
        veo_model: str = 'veo-3.1-generate-preview',
        estimated_planning_tokens: int = 2000
    ) -> Tuple[float, Dict]:
        """
        計算 Flow Engine 影片生成成本（預估）

        Flow Engine 會進行：
        1. Gemini 分段計畫生成（文字生成）
        2. 多段 Veo 影片生成（每段 8 秒）

        Args:
            target_duration: 目標影片時長（秒）
            segment_duration: 每段時長（秒），預設 8 秒
            planning_model: 計畫生成模型，預設 gemini-2.0-flash-exp
            veo_model: Veo 模型名稱
            estimated_planning_tokens: 估算的計畫生成 token 數（輸入+輸出）

        Returns:
            (總成本, 詳細資訊)
        """
        # 計算所需片段數量
        num_segments = (target_duration + segment_duration - 1) // segment_duration

        # 1. Gemini 分段計畫成本
        # 估算：輸入約 500 tokens，輸出約 1500 tokens（JSON 格式）
        planning_input_tokens = 500
        planning_output_tokens = estimated_planning_tokens - planning_input_tokens

        planning_cost, planning_details = self.calculate_text_cost(
            planning_model,
            planning_input_tokens,
            planning_output_tokens
        )

        # 2. Veo 影片生成成本（多段）
        total_veo_duration = num_segments * segment_duration
        veo_cost, veo_details = self.calculate_video_generation_cost(
            veo_model,
            total_veo_duration
        )

        # 總成本
        total_cost = planning_cost + veo_cost

        # 記錄交易
        transaction = {
            'timestamp': datetime.now(),
            'type': 'flow_engine',
            'target_duration': target_duration,
            'num_segments': num_segments,
            'segment_duration': segment_duration,
            'planning_model': planning_model,
            'veo_model': veo_model,
            'planning_cost': planning_cost,
            'veo_cost': veo_cost,
            'total_cost': total_cost
        }
        self.transactions.append(transaction)

        # 注意：因為已經在子方法中累加了，這裡不需要再累加
        # 但我們需要扣除重複累加的部分
        self.total_cost -= (planning_cost + veo_cost)
        self.total_cost += total_cost

        details = {
            'type': 'flow_engine',
            'target_duration': target_duration,
            'num_segments': num_segments,
            'segment_duration': segment_duration,
            'actual_duration': total_veo_duration,
            'planning_model': planning_model,
            'veo_model': veo_model,
            'planning_cost': planning_cost,
            'planning_tokens': estimated_planning_tokens,
            'veo_cost': veo_cost,
            'veo_duration': total_veo_duration,
            'total_cost': total_cost,
            'total_cost_twd': total_cost * USD_TO_TWD
        }

        return total_cost, details

    def estimate_flow_cost(
        self,
        target_duration: int,
        segment_duration: int = 8
    ) -> Dict:
        """
        快速估算 Flow Engine 成本（不記錄交易）

        Args:
            target_duration: 目標時長（秒）
            segment_duration: 片段時長（秒）

        Returns:
            成本詳情字典
        """
        num_segments = (target_duration + segment_duration - 1) // segment_duration
        actual_duration = num_segments * segment_duration

        # Gemini 計畫成本（估算）
        planning_pricing = self.get_model_pricing('gemini-2.0-flash-exp')
        planning_cost = (2000 / 1000) * planning_pricing.get('input', 0.0001)

        # Veo 生成成本
        veo_per_second = VEO_PRICING['veo-3.1-generate-preview']['per_second']
        veo_cost = actual_duration * veo_per_second

        total_cost = planning_cost + veo_cost

        return {
            'target_duration': target_duration,
            'num_segments': num_segments,
            'actual_duration': actual_duration,
            'planning_cost': planning_cost,
            'veo_cost': veo_cost,
            'total_cost': total_cost,
            'total_cost_twd': total_cost * USD_TO_TWD,
            'breakdown': {
                'planning': f"NT${planning_cost * USD_TO_TWD:.2f} (${planning_cost:.4f} USD) - Gemini 分段計畫",
                'veo': f"NT${veo_cost * USD_TO_TWD:.2f} (${veo_cost:.4f} USD) - {num_segments} 段 x {segment_duration} 秒",
                'total': f"NT${total_cost * USD_TO_TWD:.2f} (${total_cost:.4f} USD)"
            }
        }


    def get_session_summary(self) -> Dict:
        """獲取會話總結"""
        duration = (datetime.now() - self.session_start).total_seconds()

        return {
            'session_start': self.session_start,
            'session_duration_seconds': duration,
            'total_cost': self.total_cost,
            'total_transactions': len(self.transactions),
            'transactions': self.transactions
        }

    def format_cost(self, cost: float, currency: str = 'TWD') -> str:
        """
        格式化成本顯示（預設顯示新台幣）

        Args:
            cost: 成本（美元）
            currency: 貨幣單位 ('TWD' 或 'USD')

        Returns:
            格式化字串
        """
        if currency == 'TWD':
            return f"NT${cost * USD_TO_TWD:.2f}"
        elif currency == 'USD':
            return f"${cost:.6f}"
        else:
            return f"{cost:.6f} {currency}"

    def print_cost_summary(self, details: Dict, show_breakdown: bool = True):
        """
        打印成本摘要（新台幣顯示）

        Args:
            details: 成本詳情
            show_breakdown: 是否顯示詳細分解
        """
        print("\n" + "=" * 60)
        print(t("pricing.cost_calculation"))
        print("=" * 60)

        if details.get('type') == 'flow_engine':
            # Flow Engine
            print(t("pricing.flow_engine_type"))
            print(t("pricing.target_duration", duration=details['target_duration']))
            print(t("pricing.actual_duration", duration=details['actual_duration']))
            print(t("pricing.segment_count", num=details['num_segments'], seconds=details['segment_duration']))
            print("-" * 60)
            if show_breakdown:
                cost_str = f"{self.format_cost(details['planning_cost'])} ({self.format_cost(details['planning_cost'], 'USD')}) - {details['planning_model']}"
                print(t("pricing.planning_cost_label", cost=cost_str))
                veo_str = f"{self.format_cost(details['veo_cost'])} ({self.format_cost(details['veo_cost'], 'USD')}) - {details['num_segments']} 段"
                print(t("pricing.veo_cost_label", cost=veo_str))
                print("-" * 60)
        elif 'video_duration_seconds' in details:
            # 影片理解
            print(t("pricing.video_duration", duration=details['video_duration_seconds']))
            print(t("pricing.video_tokens_count", tokens=details['video_tokens']))
            if details.get('text_input_tokens', 0) > 0:
                print(t("pricing.text_input_tokens_count", tokens=details['text_input_tokens']))
        elif 'duration_seconds' in details:
            # 影片生成 (Veo)
            print(t("pricing.video_duration", duration=details['duration_seconds']))
            rate_twd = details['per_second_rate'] * USD_TO_TWD
            rate_usd = details['per_second_rate']
            print(t("pricing.per_second_rate", currency="NT$", rate=f"{rate_twd:.2f}", usd=f"{rate_usd:.2f}"))
        else:
            # 純文字
            if show_breakdown:
                print(t("pricing.input_tokens_count", tokens=details['input_tokens']))
                if details.get('thinking_tokens', 0) > 0:
                    print(t("pricing.thinking_tokens_count", tokens=details['thinking_tokens']))
                print(t("pricing.output_tokens_count", tokens=details['output_tokens']))
                print(t("pricing.total_tokens_count", tokens=details['total_tokens']))

        if details.get('type') != 'flow_engine':
            print("-" * 60)

        if 'input_cost' in details and show_breakdown and details.get('type') != 'flow_engine':
            print(t("pricing.input_cost_label", cost=self.format_cost(details['input_cost'])))
            if details.get('thinking_cost', 0) > 0:
                print(t("pricing.thinking_cost_label", cost=self.format_cost(details['thinking_cost'])))
            print(t("pricing.output_cost_label", cost=self.format_cost(details['output_cost'])))
            print("-" * 60)

        current_cost = f"{self.format_cost(details['total_cost'])} ({self.format_cost(details['total_cost'], 'USD')})"
        print(t("pricing.current_cost_label", cost=current_cost, percent=""))
        total_cost = f"{self.format_cost(self.total_cost)} ({self.format_cost(self.total_cost, 'USD')})"
        print(t("pricing.total_cost_label", cost=total_cost, percent=""))
        print("=" * 60 + "\n")


# 全域計價器實例
global_calculator = PricingCalculator()


# 便捷函數
def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """快速計算成本"""
    cost, _ = global_calculator.calculate_text_cost(model_name, input_tokens, output_tokens)
    return cost


def print_cost(model_name: str, input_tokens: int, output_tokens: int):
    """計算並打印成本"""
    cost, details = global_calculator.calculate_text_cost(model_name, input_tokens, output_tokens)
    global_calculator.print_cost_summary(details)
    return cost


# ==================== 新增：省錢功能 ====================

def print_zero_cost_message(feature_name: str = None):
    """
    顯示零成本訊息（本地處理功能）

    Args:
        feature_name: 功能名稱
    """
    if feature_name is None:
        feature_name = t("pricing.this_feature")
    print("\n" + "=" * 60)
    print(t("pricing.cost_calculation"))
    print("=" * 60)
    print(t("pricing.local_processing", feature=feature_name))
    print(t("pricing.zero_cost_line"))
    print("=" * 60 + "\n")


def calculate_cache_savings(
    model_name: str,
    cached_tokens: int,
    query_count: int,
    discount: float = 0.75
) -> Dict[str, float]:
    """
    計算使用 Context Caching 的成本節省

    Args:
        model_name: 模型名稱
        cached_tokens: 快取的 token 數
        query_count: 查詢次數
        discount: 快取折扣（預設 75%）

    Returns:
        成本資訊字典（包含新台幣）
    """
    calc = PricingCalculator()
    pricing = calc.get_model_pricing(model_name)

    # 計算單次快取 token 的成本
    if 'threshold' in pricing:
        # 分級定價
        if cached_tokens <= pricing['threshold']:
            base_cost_per_token = pricing['input_low'] / 1000
        else:
            # 簡化計算：使用平均值
            base_cost_per_token = (pricing['input_low'] + pricing['input_high']) / 2000
    else:
        # 固定定價
        base_cost_per_token = pricing.get('input', 0) / 1000

    # 不使用快取的成本（每次查詢都要付全額）
    without_cache = base_cost_per_token * cached_tokens * query_count

    # 使用快取的成本（第一次全額，後續打折）
    first_query_cost = base_cost_per_token * cached_tokens
    subsequent_queries_cost = base_cost_per_token * cached_tokens * (query_count - 1) * (1 - discount)
    with_cache = first_query_cost + subsequent_queries_cost

    # 節省的成本
    savings = without_cache - with_cache
    savings_percent = (savings / without_cache * 100) if without_cache > 0 else 0

    return {
        'model': model_name,
        'cached_tokens': cached_tokens,
        'query_count': query_count,
        'discount_percent': int(discount * 100),
        'without_cache': without_cache,
        'with_cache': with_cache,
        'savings': savings,
        'savings_percent': savings_percent,
        'without_cache_twd': without_cache * USD_TO_TWD,
        'with_cache_twd': with_cache * USD_TO_TWD,
        'savings_twd': savings * USD_TO_TWD
    }


def print_savings_summary(
    model_name: str,
    cached_tokens: int,
    query_count: int,
    discount: float = 0.75
):
    """
    顯示省錢摘要（Context Caching）

    Args:
        model_name: 模型名稱
        cached_tokens: 快取的 token 數
        query_count: 查詢次數
        discount: 快取折扣（預設 75%）
    """
    result = calculate_cache_savings(model_name, cached_tokens, query_count, discount)

    print("\n" + "=" * 60)
    print(t("pricing.cache_report_title"))
    print("=" * 60)
    print(t("pricing.cache_model", model=result['model']))
    print(t("pricing.cache_tokens_info", tokens=result['cached_tokens']))
    print(t("pricing.cache_query_count", count=result['query_count']))
    print(t("pricing.cache_discount_info", percent=result['discount_percent']))
    print("-" * 60)
    print(t("pricing.without_cache_cost", currency="NT$", twd=f"{result['without_cache_twd']:.2f}", usd=f"{result['without_cache']:.6f}"))
    print(t("pricing.with_cache_cost", currency="NT$", twd=f"{result['with_cache_twd']:.2f}", usd=f"{result['with_cache']:.6f}"))
    print(t("pricing.cache_savings_amount", currency="NT$", twd=f"{result['savings_twd']:.2f}", usd=f"{result['savings']:.6f}"))
    print(t("pricing.cache_savings_percent", percent=f"{result['savings_percent']:.1f}"))
    print("=" * 60 + "\n")


def print_cost_comparison(
    feature_name: str,
    method1_name: str,
    method1_cost: float,
    method2_name: str,
    method2_cost: float
):
    """
    顯示成本比較（兩種方法）

    Args:
        feature_name: 功能名稱
        method1_name: 方法1名稱
        method1_cost: 方法1成本（美元）
        method2_name: 方法2名稱
        method2_cost: 方法2成本（美元）
    """
    savings = method1_cost - method2_cost
    savings_percent = (savings / method1_cost * 100) if method1_cost > 0 else 0

    print("\n" + "=" * 60)
    print(t("pricing.cost_comparison_title", feature=feature_name))
    print("=" * 60)
    print(f"❌ {method1_name}：NT${method1_cost * USD_TO_TWD:.2f} (${method1_cost:.6f})")
    print(f"✅ {method2_name}：NT${method2_cost * USD_TO_TWD:.2f} (${method2_cost:.6f})")
    print("-" * 60)
    if savings > 0:
        print(t("pricing.savings_comparison", currency="NT$", twd=f"{savings * USD_TO_TWD:.2f}", usd=f"{savings:.6f}"))
        print(t("pricing.savings_percent_line", percent=f"{savings_percent:.1f}"))
        print(t("pricing.recommend_method", method=method2_name))
    elif savings < 0:
        print(t("pricing.extra_cost", currency="NT$", twd=f"{abs(savings) * USD_TO_TWD:.2f}", usd=f"{abs(savings):.6f}"))
        print(t("pricing.recommend_method", method=method1_name))
    else:
        print(t("pricing.same_cost"))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # 測試範例
    calc = PricingCalculator()

    print("\n=== 測試 1: Gemini 2.5 Pro 文字生成 ===")
    cost, details = calc.calculate_text_cost(
        'gemini-2.5-pro',
        input_tokens=1000,
        output_tokens=500
    )
    calc.print_cost_summary(details)

    print("\n=== 測試 2: Gemini 2.5 Flash 文字生成 ===")
    cost, details = calc.calculate_text_cost(
        'gemini-2.5-flash',
        input_tokens=10000,
        output_tokens=2000
    )
    calc.print_cost_summary(details)

    print("\n=== 測試 3: Veo 3.1 影片生成（8秒）===")
    cost, details = calc.calculate_video_generation_cost(
        'veo-3.1-generate-preview',
        duration_seconds=8
    )
    calc.print_cost_summary(details)

    print("\n=== 測試 4: 影片理解（60秒影片）===")
    cost, details = calc.calculate_video_understanding_cost(
        'gemini-2.5-pro',
        video_duration_seconds=60,
        additional_input_tokens=100,
        output_tokens=500
    )
    calc.print_cost_summary(details)

    print("\n=== 會話總結 ===")
    summary = calc.get_session_summary()
    print(f"總交易次數: {summary['total_transactions']}")
    print(f"會話總成本: ${summary['total_cost']:.6f}")
    print(f"約合台幣: NT${summary['total_cost'] * 31:.2f}")
