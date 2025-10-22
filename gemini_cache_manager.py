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
            console.print(f"[yellow]警告：{model} 可能不支援 Context Caching[/yellow]")

        # 檢查最低 token 要求
        min_tokens = MIN_TOKENS.get(model, 1024)
        console.print(f"\n[cyan]📦 建立 Context Cache[/cyan]")
        console.print(f"   模型：{model}")
        console.print(f"   最低 tokens：{min_tokens:,}")
        console.print(f"   TTL：{ttl_seconds} 秒 ({ttl_seconds / 3600:.1f} 小時)")

        if display_name:
            console.print(f"   名稱：{display_name}")

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
            console.print("\n[cyan]⏳ 建立中...[/cyan]")

            cache = client.caches.create(
                model=f"models/{model}",
                config=types.CreateCachedContentConfig(**config_params)
            )

            console.print(f"[green]✓ 快取已建立[/green]")
            console.print(f"   快取名稱：{cache.name}")
            console.print(f"   過期時間：{cache.expire_time}")

            # 儲存到活動快取
            cache_key = display_name or cache.name
            self.active_caches[cache_key] = cache

            # 顯示省錢資訊
            self._show_savings_info(model)

            return cache

        except Exception as e:
            console.print(f"[red]✗ 建立快取失敗：{e}[/red]")

            # 檢查常見錯誤
            error_str = str(e).lower()
            if 'token' in error_str and 'minimum' in error_str:
                console.print(f"\n[yellow]提示：內容可能少於最低 {min_tokens} tokens[/yellow]")
                console.print(f"[yellow]請增加內容長度以使用 Context Caching[/yellow]")
            elif 'not support' in error_str:
                console.print(f"\n[yellow]提示：{model} 可能不支援 Context Caching[/yellow]")

            raise

    def _check_model_support(self, model: str) -> bool:
        """檢查模型是否支援 Context Caching"""
        supported_models = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash']
        return any(supported in model for supported in supported_models)

    def _show_savings_info(self, model: str):
        """顯示省錢資訊"""
        discount = CACHE_DISCOUNT.get(model, 0.75)
        discount_percent = int(discount * 100)

        console.print(f"\n[bold green]💰 成本節省資訊[/bold green]")
        console.print(f"   快取折扣：{discount_percent}%")
        console.print(f"   範例：原本 $1.00 → 現在 ${1.00 * (1 - discount):.2f}")

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
            console.print(f"[yellow]在本地找不到快取，嘗試從 API 獲取...[/yellow]")
            cache = self._find_cache_by_name(cache_name_or_key)
            if not cache:
                raise ValueError(f"找不到快取：{cache_name_or_key}")

        console.print(f"\n[cyan]🔍 使用快取查詢[/cyan]")
        console.print(f"   快取：{cache.name}")
        console.print(f"   問題：{question}\n")

        try:
            # 使用快取進行查詢
            response = client.models.generate_content(
                model=cache.model,
                contents=question,
                config=types.GenerateContentConfig(
                    cached_content=cache.name
                )
            )

            console.print("[cyan]Gemini (使用快取)：[/cyan]")
            console.print(response.text)

            return response.text

        except Exception as e:
            console.print(f"[red]✗ 查詢失敗：{e}[/red]")
            raise

    def _find_cache_by_name(self, name: str) -> Optional[Any]:
        """通過名稱查找快取"""
        try:
            caches = client.caches.list()
            for cache in caches:
                if name in cache.name or (hasattr(cache, 'display_name') and cache.display_name == name):
                    return cache
        except Exception as e:
            console.print(f"[red]列出快取失敗：{e}[/red]")
        return None

    def list_caches(self) -> List[Any]:
        """列出所有快取"""
        console.print("\n[cyan]📦 已建立的 Context Caches：[/cyan]\n")

        try:
            caches = list(client.caches.list())

            if not caches:
                console.print("[yellow]沒有找到快取[/yellow]")
                return []

            # 建立表格
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("名稱", style="green")
            table.add_column("模型")
            table.add_column("建立時間")
            table.add_column("過期時間")
            table.add_column("狀態", justify="center")

            for cache in caches:
                display_name = getattr(cache, 'display_name', cache.name.split('/')[-1])

                # 檢查是否過期
                now = datetime.now()
                expire_time = cache.expire_time
                is_expired = expire_time < now if expire_time else False

                status = "[red]已過期[/red]" if is_expired else "[green]有效[/green]"

                table.add_row(
                    display_name,
                    cache.model.split('/')[-1],
                    str(cache.create_time).split('.')[0] if cache.create_time else "N/A",
                    str(expire_time).split('.')[0] if expire_time else "N/A",
                    status
                )

            console.print(table)
            console.print(f"\n總計：{len(caches)} 個快取")

            return caches

        except Exception as e:
            console.print(f"[red]✗ 列出快取失敗：{e}[/red]")
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
            console.print(f"[green]✓ 已刪除快取：{cache_name_or_key}[/green]")

            # 從 active_caches 移除
            if cache_name_or_key in self.active_caches:
                del self.active_caches[cache_name_or_key]

            return True

        except Exception as e:
            console.print(f"[red]✗ 刪除快取失敗：{e}[/red]")
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
[cyan]模型：[/cyan] {model}
[cyan]快取 Tokens：[/cyan] {result['cached_tokens']:,}
[cyan]查詢次數：[/cyan] {result['query_count']}

[yellow]不使用快取成本：[/yellow] ${result['without_cache']:.6f}
[green]使用快取成本：[/green] ${result['with_cache']:.6f}
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
            console.print("[red]錯誤：請提供 --content[/red]")
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
            console.print("[red]錯誤：請提供 --cache[/red]")
            sys.exit(1)
        manager.delete_cache(args.cache)

    elif args.command == 'query':
        if not args.cache or not args.question:
            console.print("[red]錯誤：請提供 --cache 和 --question[/red]")
            sys.exit(1)
        manager.query_with_cache(args.cache, args.question)

    elif args.command == 'calculate':
        if not args.tokens:
            console.print("[red]錯誤：請提供 --tokens[/red]")
            sys.exit(1)
        manager.show_savings_report(
            model=args.model,
            cached_tokens=args.tokens,
            query_count=args.queries
        )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        console.print("\n[bold cyan]Gemini Context Caching 管理器[/bold cyan]\n")
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
