#!/usr/bin/env python3
"""
Gemini Context Caching 管理器
使用快取減少 API 成本（最高省 90%）
"""
import os
import sys
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from google.genai import types
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 導入價格模組（統一匯率）
from gemini_pricing import USD_TO_TWD, print_savings_summary

# 共用工具模組
from utils.api_client import get_gemini_client
from utils.pricing_loader import (
    get_pricing_calculator,
    PRICING_ENABLED,
    USD_TO_TWD
)

# 導入 i18n 國際化支援
from utils.i18n import safe_t

console = Console()

# 初始化 API 客戶端
client = get_gemini_client()

# 初始化計價器
global_pricing_calculator = get_pricing_calculator(silent=True)

# Context Caching 最低 token 要求
MIN_TOKENS = {
    'gemini-2.5-pro': 4096,
    'gemini-2.5-flash': 1024,
    'gemini-2.0-flash': 32768,  # 2.0 Flash 需要更多
}

# 快取折扣率
CACHE_DISCOUNT = {
    'gemini-2.5-pro': 0.90,      # 90% 折扣
    'gemini-2.5-flash': 0.90,    # 90% 折扣
    'gemini-2.0-flash': 0.75,    # 75% 折扣
}


class CacheManager:
    """Context Caching 管理器"""

    def __init__(self):
        self.active_caches: Dict[str, Any] = {}

    def create_cache(
        self,
        model: str,
        contents: List[str],
        display_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        ttl_seconds: int = 3600,
        ttl_hours: Optional[int] = None
    ) -> Any:
        """
        建立 Context Cache

        Args:
            model: 模型名稱（如 "gemini-2.5-pro"）
            contents: 要快取的內容列表
            display_name: 快取顯示名稱
            system_instruction: 系統指令（可選）
            ttl_seconds: 快取存活時間（秒）
            ttl_hours: 快取存活時間（小時），會覆蓋 ttl_seconds

        Returns:
            快取物件
        """
        # 計算 TTL
        if ttl_hours:
            ttl_seconds = ttl_hours * 3600

        # 檢查模型支援
        if not self._check_model_support(model):
            console.print(f"[magenta]{safe_t('cache.warning_model_not_support', fallback='警告：{model} 可能不支援 Context Caching', model=model)}[/yellow]")

        # 檢查最低 token 要求
        min_tokens = MIN_TOKENS.get(model, 1024)
        console.print(f"\n[magenta]{safe_t('cache.create_title', fallback='📦 建立 Context Cache')}[/magenta]")
        console.print(f"   {safe_t('cache.model_info', fallback='模型：{model}', model=model)}")
        console.print(f"   {safe_t('cache.min_tokens_info', fallback='最低 tokens：{min}', min=f'{min_tokens:,}')}")
        console.print(f"   {safe_t('cache.ttl_info', fallback='TTL：{seconds} 秒 ({hours} 小時)', seconds=ttl_seconds, hours=f'{ttl_seconds/3600:.1f}')}")

        if display_name:
            console.print(f"   {safe_t('cache.display_name_info', fallback='名稱：{name}', name=display_name)}")

        try:
            # 準備配置
            config_params = {
                "contents": contents,
                "ttl": f"{ttl_seconds}s"
            }

            if system_instruction:
                config_params["system_instruction"] = system_instruction

            if display_name:
                config_params["display_name"] = display_name

            # 建立快取
            console.print(f"\n[magenta]{safe_t('cache.creating', fallback='⏳ 建立中...')}[/magenta]")

            cache = client.caches.create(
                model=f"models/{model}",
                config=types.CreateCachedContentConfig(**config_params)
            )

            console.print(f"[bright_magenta]{safe_t('cache.created_success', fallback='✓ 快取已建立')}[/green]")
            console.print(f"   {safe_t('cache.cache_name_info', fallback='快取名稱：{name}', name=cache.name)}")
            console.print(f"   {safe_t('cache.expire_time_info', fallback='過期時間：{time}', time=cache.expire_time)}")

            # 儲存到活動快取
            cache_key = display_name or cache.name
            self.active_caches[cache_key] = cache

            # 顯示省錢資訊
            self._show_savings_info(model)

            return cache

        except Exception as e:
            console.print(f"[dim magenta]{safe_t('cache.create_failed', fallback='✗ 建立快取失敗：{error}', error=str(e))}[/red]")

            # 檢查常見錯誤
            error_str = str(e).lower()
            if 'token' in error_str and 'minimum' in error_str:
                console.print(f"\n[magenta]{safe_t('cache.hint_content_too_short', fallback='提示：內容可能少於最低 {min_tokens} tokens', min_tokens=min_tokens)}[/yellow]")
                console.print(f"[magenta]{safe_t('cache.hint_increase_content', fallback='請增加內容長度以使用 Context Caching')}[/yellow]")
            elif 'not support' in error_str:
                console.print(f"\n[magenta]{safe_t('cache.hint_model_not_support', fallback='提示：{model} 可能不支援 Context Caching', model=model)}[/yellow]")

            raise

    def _check_model_support(self, model: str) -> bool:
        """檢查模型是否支援 Context Caching"""
        supported_models = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash']
        return any(supported in model for supported in supported_models)

    def _show_savings_info(self, model: str):
        """顯示省錢資訊"""
        discount = CACHE_DISCOUNT.get(model, 0.75)
        discount_percent = int(discount * 100)

        console.print(f"\n[bold green]{safe_t('cache.savings_info_title', fallback='💰 成本節省資訊')}[/bold green]")
        console.print(f"   {safe_t('cache.discount_info', fallback='快取折扣：{discount}%', discount=discount_percent)}")
        console.print(f"   {safe_t('cache.example_savings', fallback='範例：原本 ${original} → 現在 ${discounted}', original='1.00', discounted=f'{1.00 * (1 - discount):.2f}')}")

    def query_with_cache(
        self,
        cache_name_or_key: str,
        question: str,
        model: Optional[str] = None
    ) -> str:
        """
        使用快取進行查詢

        Args:
            cache_name_or_key: 快取名稱或 key
            question: 問題
            model: 模型（可選，會從快取獲取）

        Returns:
            回應文字
        """
        # 獲取快取
        cache = self.active_caches.get(cache_name_or_key)
        if not cache:
            # 嘗試列出並查找
            console.print(f"[magenta]{safe_t('cache.trying_api', fallback='在本地找不到快取，嘗試從 API 獲取...')}[/yellow]")
            cache = self._find_cache_by_name(cache_name_or_key)
            if not cache:
                raise ValueError(safe_t('cache.cache_not_found', fallback='找不到快取：{name}', name=cache_name_or_key))

        console.print(f"\n[magenta]{safe_t('cache.query_title', fallback='🔍 使用快取查詢')}[/magenta]")
        console.print(f"   {safe_t('cache.cache_info', fallback='快取：{name}', name=cache.name)}")
        console.print(f"   {safe_t('cache.question_info', fallback='問題：{question}', question=question)}\n")

        try:
            # 使用快取進行查詢
            response = client.models.generate_content(
                model=cache.model,
                contents=question,
                config=types.GenerateContentConfig(
                    cached_content=cache.name
                )
            )

            # 提取並計算成本（含快取折扣）
            if PRICING_ENABLED and global_pricing_calculator:
                cached_tokens = getattr(response.usage_metadata, 'cached_content_token_count', 0)
                thinking_tokens = getattr(response.usage_metadata, 'thinking_tokens', 0)
                input_tokens = getattr(response.usage_metadata, 'prompt_tokens', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_tokens', 0)

                # 計算成本
                cost, details = global_pricing_calculator.calculate_text_cost(
                    cache.model,
                    input_tokens,
                    output_tokens,
                    thinking_tokens
                )

                # 顯示成本資訊（含快取折扣說明）
                if cost > 0 or cached_tokens > 0:
                    console.print(f"\n[dim]{safe_t('cache.query_cost', fallback='💰 查詢成本 (使用快取): NT${twd} (${usd} USD)', twd=f'{cost * USD_TO_TWD:.2f}', usd=f'{cost:.6f}')}[/dim]")
                    console.print(f"[dim]   {safe_t('cache.cached_tokens_detail', fallback='快取 tokens: {cached} (90% 折扣)', cached=f'{cached_tokens:,}')}[/dim]")
                    console.print(f"[dim]   {safe_t('cache.tokens_detail', fallback='輸入: {input} tokens, 輸出: {output} tokens, 思考: {thinking} tokens', input=f'{input_tokens:,}', output=f'{output_tokens:,}', thinking=f'{thinking_tokens:,}')}[/dim]")

                    # 計算如果不使用快取的成本
                    if cached_tokens > 0:
                        full_cost, _ = global_pricing_calculator.calculate_text_cost(
                            cache.model,
                            input_tokens + cached_tokens,
                            output_tokens,
                            thinking_tokens
                        )
                        savings = full_cost - cost
                        savings_percent = (savings / full_cost * 100) if full_cost > 0 else 0
                        console.print(f"[dim]   {safe_t('cache.savings_detail', fallback='💸 節省成本: NT${twd} (約 {percent}%)', twd=f'{savings * USD_TO_TWD:.2f}', percent=f'{savings_percent:.0f}')}[/dim]")

                    console.print(f"[dim]   {safe_t('cache.cumulative_cost_info', fallback='累計成本: NT${twd} (${usd} USD)', twd=f'{global_pricing_calculator.total_cost * USD_TO_TWD:.2f}', usd=f'{global_pricing_calculator.total_cost:.6f}')}[/dim]\n")

            console.print(f"[magenta]{safe_t('cache.using_cache_label', fallback='Gemini (使用快取)：')}[/magenta]")
            console.print(response.text)

            return response.text

        except Exception as e:
            console.print(f"[dim magenta]{safe_t('cache.query_failed', fallback='✗ 查詢失敗：{error}', error=str(e))}[/red]")
            raise

    def _find_cache_by_name(self, name: str) -> Optional[Any]:
        """通過名稱查找快取"""
        try:
            caches = client.caches.list()
            for cache in caches:
                if name in cache.name or (hasattr(cache, 'display_name') and cache.display_name == name):
                    return cache
        except Exception as e:
            console.print(f"[dim magenta]列出快取失敗：{e}[/red]")
        return None

    def list_caches(self) -> List[Any]:
        """列出所有快取"""
        console.print(f"\n[magenta]{safe_t('cache.list_title', fallback='📦 已建立的 Context Caches：')}[/magenta]\n")

        try:
            caches = list(client.caches.list())

            if not caches:
                console.print(f"[magenta]{safe_t('cache.no_caches_found', fallback='沒有找到快取')}[/yellow]")
                return []

            # 建立表格
            table = Table(show_header=True, header_style="bold bright_magenta")
            table.add_column(safe_t('cache.table_col_name', fallback='名稱'), style="green")
            table.add_column(safe_t('cache.table_col_model', fallback='模型'))
            table.add_column(safe_t('cache.table_col_created', fallback='建立時間'))
            table.add_column(safe_t('cache.table_col_expire', fallback='過期時間'))
            table.add_column(safe_t('cache.table_col_status', fallback='狀態'), justify="center")

            for cache in caches:
                display_name = getattr(cache, 'display_name', cache.name.split('/')[-1])

                # 檢查是否過期
                now = datetime.now()
                expire_time = cache.expire_time
                is_expired = expire_time < now if expire_time else False

                status = f"[dim magenta]{safe_t('cache.status_expired', fallback='已過期')}[/red]" if is_expired else f"[bright_magenta]{safe_t('cache.status_valid', fallback='有效')}[/green]"

                table.add_row(
                    display_name,
                    cache.model.split('/')[-1],
                    str(cache.create_time).split('.')[0] if cache.create_time else "N/A",
                    str(expire_time).split('.')[0] if expire_time else "N/A",
                    status
                )

            console.print(table)
            console.print(f"\n{safe_t('cache.total_caches', fallback='總計：{count} 個快取', count=len(caches))}")

            return caches

        except Exception as e:
            console.print(f"[dim magenta]{safe_t('cache.list_failed', fallback='✗ 列出快取失敗：{error}', error=str(e))}[/red]")
            return []

    def delete_cache(self, cache_name_or_key: str) -> bool:
        """
        刪除快取

        Args:
            cache_name_or_key: 快取名稱或 key

        Returns:
            是否成功刪除
        """
        try:
            # 嘗試從 active_caches 獲取
            cache = self.active_caches.get(cache_name_or_key)
            if cache:
                cache_name = cache.name
            else:
                # 假設是完整名稱
                cache_name = cache_name_or_key
                if not cache_name.startswith('cachedContents/'):
                    cache_name = f"cachedContents/{cache_name}"

            client.caches.delete(name=cache_name)
            console.print(f"[bright_magenta]✓ 已刪除快取：{cache_name_or_key}[/green]")

            # 從 active_caches 移除
            if cache_name_or_key in self.active_caches:
                del self.active_caches[cache_name_or_key]

            return True

        except Exception as e:
            console.print(f"[dim magenta]✗ 刪除快取失敗：{e}[/red]")
            return False

    def calculate_savings(
        self,
        model: str,
        cached_tokens: int,
        query_count: int
    ) -> Dict[str, float]:
        """
        計算使用快取的成本節省

        Args:
            model: 模型名稱
            cached_tokens: 快取的 token 數
            query_count: 查詢次數

        Returns:
            成本資訊字典
        """
        from gemini_pricing import PRICING_TABLE

        # 獲取定價
        pricing = PRICING_TABLE.get(model, PRICING_TABLE['default'])
        input_price = pricing.get('input', pricing.get('input_low', 0))

        # 計算成本
        without_cache = (cached_tokens / 1000) * input_price * query_count
        discount = CACHE_DISCOUNT.get(model, 0.75)
        with_cache = without_cache * (1 - discount)
        savings = without_cache - with_cache

        return {
            'without_cache': without_cache,
            'with_cache': with_cache,
            'savings': savings,
            'discount_percent': int(discount * 100),
            'query_count': query_count,
            'cached_tokens': cached_tokens
        }

    def show_savings_report(
        self,
        model: str,
        cached_tokens: int,
        query_count: int
    ):
        """顯示成本節省報告"""
        result = self.calculate_savings(model, cached_tokens, query_count)

        panel_content = f"""
[magenta]模型：[/magenta] {model}
[magenta]快取 Tokens：[/magenta] {result['cached_tokens']:,}
[magenta]查詢次數：[/magenta] {result['query_count']}

[magenta]不使用快取成本：[/yellow] ${result['without_cache']:.6f}
[bright_magenta]使用快取成本：[/green] ${result['with_cache']:.6f}
[bold green]節省：[/bold green] ${result['savings']:.6f} ({result['discount_percent']}% 折扣)

[dim]約合台幣節省：NT${result['savings'] * USD_TO_TWD:.2f}[/dim]
        """

        console.print(Panel(panel_content, title="💰 成本節省報告", border_style="green"))


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='Gemini Context Caching 管理器')
    parser.add_argument('command', choices=['create', 'list', 'delete', 'query', 'calculate'],
                       help='命令')
    parser.add_argument('--model', default='gemini-2.5-flash', help='模型名稱')
    parser.add_argument('--content', help='快取內容（文字或檔案路徑）')
    parser.add_argument('--name', help='快取名稱')
    parser.add_argument('--ttl', type=int, default=1, help='存活時間（小時）')
    parser.add_argument('--question', help='查詢問題')
    parser.add_argument('--cache', help='快取名稱（query 時使用）')
    parser.add_argument('--tokens', type=int, help='Token 數量（calculate 時使用）')
    parser.add_argument('--queries', type=int, default=10, help='查詢次數（calculate 時使用）')

    args = parser.parse_args()

    manager = CacheManager()

    if args.command == 'create':
        if not args.content:
            console.print("[dim magenta]錯誤：請提供 --content[/red]")
            sys.exit(1)

        # 檢查是否為檔案
        content = args.content
        if os.path.isfile(content):
            with open(content, 'r', encoding='utf-8') as f:
                content = f.read()

        manager.create_cache(
            model=args.model,
            contents=[content],
            display_name=args.name,
            ttl_hours=args.ttl
        )

    elif args.command == 'list':
        manager.list_caches()

    elif args.command == 'delete':
        if not args.cache:
            console.print("[dim magenta]錯誤：請提供 --cache[/red]")
            sys.exit(1)
        manager.delete_cache(args.cache)

    elif args.command == 'query':
        if not args.cache or not args.question:
            console.print("[dim magenta]錯誤：請提供 --cache 和 --question[/red]")
            sys.exit(1)
        manager.query_with_cache(args.cache, args.question)

    elif args.command == 'calculate':
        if not args.tokens:
            console.print("[dim magenta]錯誤：請提供 --tokens[/red]")
            sys.exit(1)
        manager.show_savings_report(
            model=args.model,
            cached_tokens=args.tokens,
            query_count=args.queries
        )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        console.print("\n[bold magenta]Gemini Context Caching 管理器[/bold magenta]\n")
        console.print("💰 [bold]使用快取可節省最高 90% 的成本！[/bold]\n")
        console.print("使用方式：")
        console.print("  建立快取：")
        console.print("    python gemini_cache_manager.py create --model gemini-2.5-pro --content 'long text...' --name my_cache --ttl 2")
        console.print("    python gemini_cache_manager.py create --content file.txt --name doc_cache\n")
        console.print("  列出快取：")
        console.print("    python gemini_cache_manager.py list\n")
        console.print("  使用快取查詢：")
        console.print("    python gemini_cache_manager.py query --cache my_cache --question '問題'\n")
        console.print("  刪除快取：")
        console.print("    python gemini_cache_manager.py delete --cache my_cache\n")
        console.print("  計算節省：")
        console.print("    python gemini_cache_manager.py calculate --model gemini-2.5-pro --tokens 10000 --queries 100\n")
        sys.exit(0)
    else:
        main()
