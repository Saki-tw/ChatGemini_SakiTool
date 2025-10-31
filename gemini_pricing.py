#!/usr/bin/env python3
"""
Gemini API 即時計價模組
根據 token 使用量計算成本
支援新台幣顯示、思考模式 token 計價
"""
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from utils.i18n import t, _

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

# 美元兌新台幣匯率（2025年10月）
# 若匯率有較大變動,請更新此值
USD_TO_TWD = 31.0

# Gemini API 定價表（2025年10月 - 根據官方文檔更新）
# 價格單位：美元 / 1000 tokens
# 資料來源：https://ai.google.dev/gemini-api/docs/pricing
PRICING_TABLE: Dict[str, Dict[str, float]] = {
    # Gemini 2.5 系列（付費定價）
    'gemini-2.5-pro': {
        'input_low': 0.00125,      # ≤200K tokens - $1.25/百萬
        'output_low': 0.01,         # ≤200K tokens - $10/百萬
        'input_high': 0.0025,      # >200K tokens - $2.50/百萬
        'output_high': 0.015,       # >200K tokens - $15/百萬
        'threshold': 200000,
    },
    'gemini-2.5-flash': {
        'input': 0.0003,            # $0.30 / 1M tokens (文字/圖片/影片)
        'output': 0.0025,           # $2.50 / 1M tokens
    },
    'gemini-2.5-flash-lite': {
        'input': 0.0001,            # $0.10 / 1M tokens
        'output': 0.0004,           # $0.40 / 1M tokens
    },

    # Gemini 2.0 系列（付費定價）
    'gemini-2.0-flash': {
        'input': 0.0001,            # $0.10 / 1M tokens
        'output': 0.0004,           # $0.40 / 1M tokens
    },
    'gemini-2.0-flash-lite': {
        'input': 0.000075,          # $0.075 / 1M tokens
        'output': 0.0003,           # $0.30 / 1M tokens
    },
    'gemini-2.0-flash-thinking-exp': {
        'input': 0.0001,            # $0.10 / 1M tokens
        'output': 0.0004,           # $0.40 / 1M tokens
    },
    'gemini-2.0-flash-exp': {
        'input': 0.0,               # 實驗版免費
        'output': 0.0,
    },

    # Gemini 1.5 系列（向後相容）
    'gemini-1.5-pro': {
        'input_low': 0.00125,       # ≤128K tokens
        'output_low': 0.005,
        'input_high': 0.0025,       # >128K tokens
        'output_high': 0.015,
        'threshold': 128000,
    },
    'gemini-1.5-flash': {
        'input_low': 0.000075,      # ≤128K tokens - $0.075/1M (2024降價後)
        'output_low': 0.0003,       # ≤128K tokens - $0.30/1M
        'input_high': 0.00015,      # >128K tokens - $0.15/1M
        'output_high': 0.0006,      # >128K tokens - $0.60/1M
        'threshold': 128000,
    },
    # 注意：API 中沒有 gemini-1.5-flash-8b 或 gemini-1.5-flash-lite
    # 1.5 系列只有 gemini-1.5-flash 和 gemini-1.5-pro

    # 嵌入模型
    'gemini-embedding-001': {
        'input': 0.00015,           # $0.15 / 1M tokens
        'output': 0.0,
    },

    # Gemma 開源模型（完全免費）
    'gemma-3': {
        'input': 0.0,
        'output': 0.0,
    },
    'gemma-3n': {
        'input': 0.0,
        'output': 0.0,
    },

    # 實驗版模型
    'gemini-exp-1206': {
        'input': 0.0,               # 實驗版免費
        'output': 0.0,
    },

    # 預設（使用 Flash 定價）
    'default': {
        'input': 0.0003,
        'output': 0.0025,
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
    'imagen-4.0-generate-001': {
        'per_image': 0.04,          # $0.04 per image
    },
    'imagen-4.0-ultra-generate-001': {
        'per_image': 0.08,          # $0.08 per image
    },
    'imagen-4.0-fast-generate-001': {
        'per_image': 0.02,          # $0.02 per image (最便宜)
    },
}

# 多模態 Token 轉換率（官方文檔：https://ai.google.dev/gemini-api/docs/tokens）
# 圖片按 tile 計算,每個 tile = 258 tokens
IMAGE_TOKEN_BASE = 258  # 小圖 (≤384px 兩個維度) 或每個 tile 的固定 token 數

def calculate_image_tokens(width: int, height: int) -> int:
    """
    計算圖片消耗的 token 數量

    官方規則：
    - 小圖 (寬≤384 且 高≤384): 258 tokens
    - 大圖: 分割為 768x768 的 tiles,每個 tile = 258 tokens

    Args:
        width: 圖片寬度（像素）
        height: 圖片高度（像素）

    Returns:
        token 數量

    來源: https://ai.google.dev/gemini-api/docs/tokens
    """
    if width <= 384 and height <= 384:
        return IMAGE_TOKEN_BASE

    # 大圖：計算需要多少個 768x768 tiles
    tiles_width = (width + 767) // 768   # 向上取整
    tiles_height = (height + 767) // 768
    return tiles_width * tiles_height * IMAGE_TOKEN_BASE

# 影片 Token 轉換率（每秒約 258 tokens）
VIDEO_TOKEN_PER_SECOND = 258

# 音訊 Token 轉換率（每秒約 32 tokens）
AUDIO_TOKEN_PER_SECOND = 32


class PricingCalculator:
    """
    即時計價計算器

    功能：
    - 計算 Gemini 文字/多模態 token 成本
    - 計算 Imagen 圖片生成成本
    - 計算 Gemini + Imagen 組合成本
    - 預算控制與警告
    - 成本追蹤與統計

    設計原則：
    - 完全獨立,不依賴 gemini_chat.py
    - 提供清晰的公開接口供外部調用
    - 內部管理所有計價邏輯
    """

    def __init__(self, enable_budget_control: bool = False,
                 daily_limit_usd: float = 5.0,
                 monthly_limit_usd: float = 100.0):
        """
        初始化計價計算器

        Args:
            enable_budget_control: 是否啟用預算控制
            daily_limit_usd: 每日預算上限（美元）
            monthly_limit_usd: 每月預算上限（美元）
        """
        self.total_cost = 0.0
        self.session_start = datetime.now()
        self.transactions = []

        # 預算控制
        self.enable_budget_control = enable_budget_control
        self.daily_limit_usd = daily_limit_usd
        self.monthly_limit_usd = monthly_limit_usd
        self.daily_cost = 0.0
        self.monthly_cost = 0.0
        self.last_reset_date = datetime.now().date()
        self.last_reset_month = datetime.now().strftime('%Y-%m')
        self.budget_warnings_sent = set()

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

    def calculate_multimodal_cost(
        self,
        model_name: str,
        prompt_tokens: int,
        images: Optional[List[Tuple[int, int]]] = None,
        video_seconds: float = 0,
        audio_seconds: float = 0,
        output_tokens: int = 0,
        thinking_tokens: int = 0
    ) -> Tuple[float, Dict]:
        """
        計算多模態請求成本（Gemini Vision/Audio）

        支援：
        - 文字 + 圖片
        - 文字 + 影片
        - 文字 + 音訊
        - 組合多種模態

        Args:
            model_name: Gemini 模型名稱
            prompt_tokens: 文字提示 token 數
            images: 圖片列表 [(寬, 高), ...] 或 None
            video_seconds: 影片秒數
            audio_seconds: 音訊秒數
            output_tokens: 輸出 token 數
            thinking_tokens: 思考模式 token 數（僅特定模型）

        Returns:
            (總成本, 詳細資訊)

        Examples:
            # 文字 + 1 張圖片
            cost, details = calc.calculate_multimodal_cost(
                model_name="gemini-2.5-flash",
                prompt_tokens=100,
                images=[(1920, 1080)],  # 1 張 Full HD 圖片
                output_tokens=200
            )

            # 文字 + 影片
            cost, details = calc.calculate_multimodal_cost(
                model_name="gemini-2.5-pro",
                prompt_tokens=50,
                video_seconds=30,  # 30 秒影片
                output_tokens=500
            )
        """
        # 計算圖片 token
        image_tokens = 0
        if images:
            for width, height in images:
                image_tokens += calculate_image_tokens(width, height)

        # 計算影片 token
        video_tokens = int(video_seconds * VIDEO_TOKEN_PER_SECOND)

        # 計算音訊 token
        audio_tokens = int(audio_seconds * AUDIO_TOKEN_PER_SECOND)

        # 總輸入 token
        total_input_tokens = prompt_tokens + image_tokens + video_tokens + audio_tokens

        # 使用現有的文字計價方法
        total_cost, text_details = self.calculate_text_cost(
            model_name=model_name,
            input_tokens=total_input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens
        )

        # 擴展詳細資訊
        details = {
            **text_details,
            'prompt_tokens': prompt_tokens,
            'image_tokens': image_tokens,
            'image_count': len(images) if images else 0,
            'video_tokens': video_tokens,
            'video_seconds': video_seconds,
            'audio_tokens': audio_tokens,
            'audio_seconds': audio_seconds,
            'total_input_tokens': total_input_tokens,
        }

        return total_cost, details

    def calculate_gemini_imagen_combo_cost(
        self,
        gemini_model: str,
        imagen_model: str,
        analysis_prompt_tokens: int,
        source_images: Optional[List[Tuple[int, int]]] = None,
        analysis_output_tokens: int = 500,
        number_of_generated_images: int = 1
    ) -> Tuple[float, Dict]:
        """
        計算 Gemini Vision + Imagen 組合創作成本

        流程：
        1. Gemini Vision 分析原圖 (多模態成本)
        2. Imagen 生成新圖片 (圖片生成成本)

        Args:
            gemini_model: Gemini 模型 (如 'gemini-2.5-flash')
            imagen_model: Imagen 模型 (如 'imagen-3.0-fast-generate-001')
            analysis_prompt_tokens: 分析提示 token 數
            source_images: 原始圖片尺寸列表
            analysis_output_tokens: Gemini 分析輸出 token 數（預估）
            number_of_generated_images: 要生成的圖片數量

        Returns:
            (總成本, 詳細資訊)

        Example:
            # 分析 1 張圖片 + 生成 1 張新圖片
            cost, details = calc.calculate_gemini_imagen_combo_cost(
                gemini_model="gemini-2.5-flash",
                imagen_model="imagen-4.0-fast-generate-001",
                analysis_prompt_tokens=150,
                source_images=[(1920, 1080)],
                analysis_output_tokens=500,
                number_of_generated_images=1
            )
        """
        # Step 1: Gemini Vision 分析成本
        gemini_cost, gemini_details = self.calculate_multimodal_cost(
            model_name=gemini_model,
            prompt_tokens=analysis_prompt_tokens,
            images=source_images,
            output_tokens=analysis_output_tokens
        )

        # Step 2: Imagen 生成成本
        imagen_cost, imagen_details = self.calculate_image_generation_cost(
            model_name=imagen_model,
            number_of_images=number_of_generated_images
        )

        # 總成本
        total_cost = gemini_cost + imagen_cost

        # 組合詳細資訊
        details = {
            'gemini_analysis_cost': gemini_cost,
            'gemini_details': gemini_details,
            'imagen_generation_cost': imagen_cost,
            'imagen_details': imagen_details,
            'total_cost': total_cost,
            'operation': 'gemini_imagen_combo'
        }

        # 記錄組合交易
        transaction = {
            'timestamp': datetime.now(),
            'type': 'gemini_imagen_combo',
            'gemini_model': gemini_model,
            'imagen_model': imagen_model,
            'gemini_cost': gemini_cost,
            'imagen_cost': imagen_cost,
            'total_cost': total_cost
        }
        self.transactions.append(transaction)

        return total_cost, details

    def check_budget(self, estimated_cost: float) -> Tuple[bool, str, Dict]:
        """
        檢查預算是否足夠

        Args:
            estimated_cost: 預估成本（美元）

        Returns:
            (是否可執行, 警告訊息, 預算狀態)

        Example:
            can_proceed, warning, status = calc.check_budget(0.05)
            if not can_proceed:
                print(safe_t('pricing.budget_insufficient', fallback="預算不足：{warning}", warning=warning))
                return
            if warning:
                print(safe_t('pricing.budget_warning_prefix', fallback="警告：{warning}", warning=warning))
        """
        if not self.enable_budget_control:
            return True, "", {}

        # 重置每日/每月計數
        self._reset_budget_if_needed()

        # 預估執行後的成本
        projected_daily = self.daily_cost + estimated_cost
        projected_monthly = self.monthly_cost + estimated_cost

        # 檢查每日預算
        if projected_daily > self.daily_limit_usd:
            warning = safe_t('pricing.budget_exceeded_daily',
                           fallback="超過每日預算：${projected} > ${limit}",
                           projected=f"{projected_daily:.4f}",
                           limit=f"{self.daily_limit_usd:.2f}")
            status = self.get_budget_status()
            return False, warning, status

        # 檢查每月預算
        if projected_monthly > self.monthly_limit_usd:
            warning = safe_t('pricing.budget_exceeded_monthly',
                           fallback="超過每月預算：${projected} > ${limit}",
                           projected=f"{projected_monthly:.4f}",
                           limit=f"{self.monthly_limit_usd:.2f}")
            status = self.get_budget_status()
            return False, warning, status

        # 檢查警告閾值（80%）
        warning_threshold = 0.8
        warning_msg = ""

        if projected_daily > self.daily_limit_usd * warning_threshold:
            usage_percent = (projected_daily / self.daily_limit_usd * 100)
            warning_msg = safe_t('pricing.budget_usage_daily',
                               fallback="已使用 {percent}% 每日預算",
                               percent=f"{usage_percent:.1f}")

        status = self.get_budget_status()
        return True, warning_msg, status

    def _reset_budget_if_needed(self):
        """內部方法：檢查並重置每日/每月預算計數"""
        today = datetime.now().date()
        current_month = datetime.now().strftime('%Y-%m')

        # 重置每日
        if today != self.last_reset_date:
            self.daily_cost = 0.0
            self.last_reset_date = today
            self.budget_warnings_sent.clear()

        # 重置每月
        if current_month != self.last_reset_month:
            self.monthly_cost = 0.0
            self.last_reset_month = current_month

    def record_actual_cost(self, actual_cost: float):
        """
        記錄實際成本到預算追蹤

        在請求完成後調用,更新每日/每月成本

        Args:
            actual_cost: 實際成本（美元）
        """
        if self.enable_budget_control:
            self._reset_budget_if_needed()
            self.daily_cost += actual_cost
            self.monthly_cost += actual_cost

    def get_budget_status(self) -> Dict:
        """
        取得預算使用狀態

        Returns:
            預算狀態字典

        Example:
            status = calc.get_budget_status()
            print(safe_t('pricing.today_usage', fallback="今日使用：{percent}%", percent=f"{status['daily_usage_percent']:.1f}"))
        """
        if not self.enable_budget_control:
            return {
                'enabled': False,
                'daily_cost': 0,
                'daily_limit': 0,
                'daily_usage_percent': 0,
                'monthly_cost': 0,
                'monthly_limit': 0,
                'monthly_usage_percent': 0
            }

        self._reset_budget_if_needed()

        return {
            'enabled': True,
            'daily_cost': self.daily_cost,
            'daily_limit': self.daily_limit_usd,
            'daily_usage_percent': (self.daily_cost / self.daily_limit_usd * 100)
                                    if self.daily_limit_usd > 0 else 0,
            'daily_remaining': max(0, self.daily_limit_usd - self.daily_cost),
            'monthly_cost': self.monthly_cost,
            'monthly_limit': self.monthly_limit_usd,
            'monthly_usage_percent': (self.monthly_cost / self.monthly_limit_usd * 100)
                                      if self.monthly_limit_usd > 0 else 0,
            'monthly_remaining': max(0, self.monthly_limit_usd - self.monthly_cost),
        }

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

        影片會被處理成 frames + audio,每個 frame 算作 token

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
        # 根據 Gemini 文檔,1秒影片 ≈ 258 tokens (1 FPS)
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
            segment_duration: 每段時長（秒）,預設 8 秒
            planning_model: 計畫生成模型,預設 gemini-2.0-flash-exp
            veo_model: Veo 模型名稱
            estimated_planning_tokens: 估算的計畫生成 token 數（輸入+輸出）

        Returns:
            (總成本, 詳細資訊)
        """
        # 計算所需片段數量
        num_segments = (target_duration + segment_duration - 1) // segment_duration

        # 1. Gemini 分段計畫成本
        # 估算：輸入約 500 tokens,輸出約 1500 tokens（JSON 格式）
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

        # 注意：因為已經在子方法中累加了,這裡不需要再累加
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
                'planning': f"NT${planning_cost * USD_TO_TWD:.2f} (${planning_cost:.4f} USD) - {safe_t('pricing.gemini_planning', fallback='Gemini 分段計畫')}",
                'veo': f"NT${veo_cost * USD_TO_TWD:.2f} (${veo_cost:.4f} USD) - {safe_t('pricing.veo_segments', fallback='{num} 段 x {sec} 秒', num=num_segments, sec=segment_duration)}",
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
            symbol = t("format.currency_symbol.twd", fallback="NT$")
            return f"{symbol}{cost * USD_TO_TWD:.2f}"
        elif currency == 'USD':
            symbol = t("format.currency_symbol.usd", fallback="US$")
            return f"{symbol}{cost:.6f}"
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
                segment_unit = t("format.unit.segment", fallback="段")
                veo_str = f"{self.format_cost(details['veo_cost'])} ({self.format_cost(details['veo_cost'], 'USD')}) - {details['num_segments']}{segment_unit}"
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

    # 使用快取的成本（第一次全額,後續打折）
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

    separator = t("format.separator", fallback="：")
    twd_symbol = t("format.currency_symbol.twd", fallback="NT$")
    usd_symbol = t("format.currency_symbol.usd", fallback="$")

    print("\n" + "=" * 60)
    print(t("pricing.cost_comparison_title", feature=feature_name))
    print("=" * 60)
    print(f"❌ {method1_name}{separator}{twd_symbol}{method1_cost * USD_TO_TWD:.2f} ({usd_symbol}{method1_cost:.6f})")
    print(f"✅ {method2_name}{separator}{twd_symbol}{method2_cost * USD_TO_TWD:.2f} ({usd_symbol}{method2_cost:.6f})")
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

    print(safe_t('pricing.test_1_title', fallback="\n\n    === 測試 1: Gemini 2.5 Pro 文字生成 ==="))
    cost, details = calc.calculate_text_cost(
        'gemini-2.5-pro',
        input_tokens=1000,
        output_tokens=500
    )
    calc.print_cost_summary(details)

    print(safe_t('pricing.test_2_title', fallback="\n\n    === 測試 2: Gemini 2.5 Flash 文字生成 ==="))
    cost, details = calc.calculate_text_cost(
        'gemini-2.5-flash',
        input_tokens=10000,
        output_tokens=2000
    )
    calc.print_cost_summary(details)

    print(safe_t('pricing.test_3_title', fallback="\n\n    === 測試 3: Veo 3.1 影片生成（8秒）==="))
    cost, details = calc.calculate_video_generation_cost(
        'veo-3.1-generate-preview',
        duration_seconds=8
    )
    calc.print_cost_summary(details)

    print(safe_t('pricing.test_4_title', fallback="\n\n    === 測試 4: 影片理解（60秒影片）==="))
    cost, details = calc.calculate_video_understanding_cost(
        'gemini-2.5-pro',
        video_duration_seconds=60,
        additional_input_tokens=100,
        output_tokens=500
    )
    calc.print_cost_summary(details)

    print(safe_t('pricing.test_summary_title', fallback="\n\n    === 會話總結 ==="))
    summary = calc.get_session_summary()
    print(safe_t('pricing.total_transactions_line', fallback="總交易次數: {count}", count=summary['total_transactions']))
    print(safe_t('pricing.session_total_cost', fallback="會話總成本: ${cost:.6f}", cost=summary['total_cost']))
    print(safe_t('pricing.twd_equivalent', fallback="約合台幣: {currency}{amount}", currency="NT$", amount=f"{summary['total_cost'] * 31:.2f}"))
