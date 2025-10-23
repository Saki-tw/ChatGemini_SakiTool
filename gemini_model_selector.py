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
    """選擇 Gemini 模型"""
    print("\n" + "=" * 60)
    print("請選擇 Gemini 模型：")
    print("=" * 60)

    for key, (model_name, description) in RECOMMENDED_MODELS.items():
        print(f"{key}. {description}")

    print("\n0. 自訂模型名稱")
    print("-" * 60)

    # 預先獲取可用模型列表（用於自訂模型驗證）
    available_models = _get_available_models()

    while True:
        choice = input(f"\n請輸入選項 (1-{len(RECOMMENDED_MODELS)} 或 0): ").strip()

        if choice == '0':
            # 自訂模型名稱（必須是 API 支援的模型）
            if available_models is None:
                print("⚠️  無法驗證模型可用性，將直接使用您輸入的模型名稱")
                custom_model = input("請輸入模型名稱: ").strip()
                if custom_model:
                    return custom_model
                else:
                    print("模型名稱不能為空，請重試")
                    continue

            # 顯示可用模型列表
            print("\n可用的 Gemini 模型：")
            for i, model in enumerate(available_models, 1):
                print(f"  {i}. {model}")
            print()

            custom_model = input("請輸入模型名稱（必須是上列其中一個）: ").strip()

            if not custom_model:
                print("模型名稱不能為空，請重試")
                continue

            # 驗證模型是否存在
            if custom_model in available_models:
                return custom_model
            else:
                print(f"⚠️  模型 '{custom_model}' 不在可用列表中，請重新選擇")
                continue

        if choice in RECOMMENDED_MODELS:
            model_name, _ = RECOMMENDED_MODELS[choice]
            return model_name

        print("無效的選項，請重試")
