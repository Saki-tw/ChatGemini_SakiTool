#!/usr/bin/env python3
"""
批次請求合併器
將多個 API 請求合併為單一調用，減少網路往返次數

特性：
1. 時間視窗合併（預設 500ms）
2. 請求 ID 追蹤與回應拆分
3. 智能拆分策略（標記 → 分隔符 → 平均分配）
4. 完整錯誤處理（部分失敗支援）
5. 統計資訊收集

作者：Claude Code (Sonnet 4.5)
日期：2025-10-25
版本：1.0.0
"""
import asyncio
import re
import time
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass, field
from rich.console import Console

console = Console()


# ==================== 資料結構 ====================

@dataclass
class BatchRequest:
    """批次請求資料結構"""
    request_id: int
    model: str
    content: str
    future: asyncio.Future
    timestamp: float = field(default_factory=time.time)


# ==================== 核心合併器 ====================

class BatchRequestMerger:
    """
    批次請求合併器

    將時間視窗內的多個請求合併為單一 API 調用，
    然後智能拆分回應並分配給各個請求。

    使用範例：
        merger = BatchRequestMerger(merge_window=0.5)

        # API 調用函數
        async def api_caller(content):
            response = await client.generate_content(content)
            return response.text

        # 提交請求（自動合併）
        result = await merger.submit(
            model='gemini-2.5-flash',
            content='分析這張圖片',
            api_caller=api_caller
        )
    """

    def __init__(
        self,
        merge_window: float = 0.5,
        max_batch_size: int = 10,
        enabled: bool = True,
        verbose: bool = False
    ):
        """
        初始化合併器

        Args:
            merge_window: 合併視窗時間（秒）
            max_batch_size: 單批次最大請求數
            enabled: 是否啟用合併
            verbose: 是否顯示詳細資訊
        """
        self.merge_window = merge_window
        self.max_batch_size = max_batch_size
        self.enabled = enabled
        self.verbose = verbose

        # 請求佇列 {model: [requests]}
        self.pending_requests: Dict[str, List[BatchRequest]] = {}

        # 計時器 {model: Task}
        self.merge_timers: Dict[str, asyncio.Task] = {}

        # 請求 ID 計數器
        self._next_request_id = 0

        # 統計資訊
        self.stats = {
            'total_requests': 0,
            'merged_batches': 0,
            'total_api_calls': 0,
            'total_merged_requests': 0
        }

        # 鎖（保護佇列）
        self._lock = asyncio.Lock()

    async def submit(
        self,
        model: str,
        content: str,
        api_caller: Callable[[str], Any]
    ) -> str:
        """
        提交請求（自動合併）

        Args:
            model: 模型名稱
            content: 請求內容
            api_caller: API 調用函數（接受 merged_content，返回 response）

        Returns:
            API 回應結果
        """
        if not self.enabled:
            # 合併器停用，直接調用
            return await api_caller(content)

        self.stats['total_requests'] += 1

        # 分配請求 ID
        request_id = self._next_request_id
        self._next_request_id += 1

        # 創建 future（用於等待結果）
        future = asyncio.Future()

        # 創建請求
        request = BatchRequest(
            request_id=request_id,
            model=model,
            content=content,
            future=future
        )

        # 加入佇列
        async with self._lock:
            if model not in self.pending_requests:
                self.pending_requests[model] = []

            self.pending_requests[model].append(request)

            # 檢查是否需要立即執行（達到批次大小）
            if len(self.pending_requests[model]) >= self.max_batch_size:
                # 立即執行（取消計時器）
                if model in self.merge_timers:
                    self.merge_timers[model].cancel()
                    del self.merge_timers[model]

                # 執行批次
                asyncio.create_task(self._execute_batch(model, api_caller))

            # 否則，啟動/重設計時器
            elif model not in self.merge_timers or self.merge_timers[model].done():
                self.merge_timers[model] = asyncio.create_task(
                    self._merge_timer(model, api_caller)
                )

        # 等待結果
        return await future

    async def _merge_timer(self, model: str, api_caller: Callable):
        """合併計時器（等待視窗結束後執行批次）"""
        await asyncio.sleep(self.merge_window)
        await self._execute_batch(model, api_caller)

    async def _execute_batch(self, model: str, api_caller: Callable):
        """
        執行批次請求

        1. 取出所有待處理請求
        2. 合併為單一請求
        3. 調用 API
        4. 拆分回應
        5. 分配結果
        """
        async with self._lock:
            # 取出請求
            if model not in self.pending_requests or not self.pending_requests[model]:
                return

            requests = self.pending_requests[model]
            self.pending_requests[model] = []

            # 清除計時器
            if model in self.merge_timers:
                del self.merge_timers[model]

        # 統計
        batch_size = len(requests)
        if batch_size > 1:
            self.stats['merged_batches'] += 1
            self.stats['total_merged_requests'] += batch_size

        self.stats['total_api_calls'] += 1

        # 提示（dim，不干擾）
        if self.verbose and batch_size > 1:
            console.print(f"[dim]🔗 合併批次：{batch_size} 個請求 → 1 次 API 調用[/dim]")

        # 合併請求
        merged_content = self._merge_requests(requests)

        try:
            # 調用 API
            merged_response = await api_caller(merged_content)

            # 拆分回應
            responses = self._split_response(merged_response, requests)

            # 分配結果
            for request, response in zip(requests, responses):
                if not request.future.done():
                    request.future.set_result(response)

        except Exception as e:
            # API 調用失敗，所有請求都標記為失敗
            for request in requests:
                if not request.future.done():
                    request.future.set_exception(e)

    def _merge_requests(self, requests: List[BatchRequest]) -> str:
        """
        合併多個請求為單一請求

        格式：
        [REQUEST_0]
        {content_0}
        [END_REQUEST_0]

        [REQUEST_1]
        {content_1}
        [END_REQUEST_1]
        ...
        """
        if len(requests) == 1:
            return requests[0].content

        merged_parts = []
        for req in requests:
            merged_parts.append(
                f"[REQUEST_{req.request_id}]\n"
                f"{req.content}\n"
                f"[END_REQUEST_{req.request_id}]"
            )

        return "\n\n".join(merged_parts)

    def _split_response(
        self,
        merged_response: str,
        requests: List[BatchRequest]
    ) -> List[str]:
        """
        拆分合併後的回應

        策略：
        1. 尋找 [RESPONSE_N] 標記
        2. 如果沒有標記，使用分隔符（---）
        3. 如果沒有分隔符，按長度平均分配

        Args:
            merged_response: 合併後的回應
            requests: 請求列表

        Returns:
            拆分後的回應列表
        """
        num_requests = len(requests)

        # 單一請求，無需拆分
        if num_requests == 1:
            return [merged_response]

        # 策略 1：尋找 [RESPONSE_N] 標記
        try:
            responses = self._split_by_markers(merged_response, requests)
            if responses:
                if self.verbose:
                    console.print(f"[dim]✂️  使用標記拆分回應[/dim]")
                return responses
        except Exception:
            pass

        # 策略 2：使用分隔符 (---)
        try:
            responses = self._split_by_delimiter(merged_response, num_requests)
            if responses:
                if self.verbose:
                    console.print(f"[dim]✂️  使用分隔符拆分回應[/dim]")
                return responses
        except Exception:
            pass

        # 策略 3：平均分配（降級）
        if self.verbose:
            console.print(f"[dim]⚠️  降級：使用平均分配拆分回應[/dim]")

        return self._split_by_length(merged_response, num_requests)

    def _split_by_markers(
        self,
        response: str,
        requests: List[BatchRequest]
    ) -> Optional[List[str]]:
        """策略 1：使用 [RESPONSE_N] 標記拆分"""
        # 尋找所有標記
        pattern = r'\[RESPONSE_(\d+)\](.*?)\[END_RESPONSE_\1\]'
        matches = re.findall(pattern, response, re.DOTALL)

        if len(matches) != len(requests):
            return None

        # 按 request_id 排序
        matches_dict = {int(match[0]): match[1].strip() for match in matches}

        # 按請求順序提取
        responses = []
        for req in requests:
            if req.request_id not in matches_dict:
                return None
            responses.append(matches_dict[req.request_id])

        return responses

    def _split_by_delimiter(
        self,
        response: str,
        num_requests: int
    ) -> Optional[List[str]]:
        """策略 2：使用分隔符 (---) 拆分"""
        # 嘗試多種分隔符
        delimiters = ['---', '***', '===', '___']

        for delimiter in delimiters:
            parts = response.split(delimiter)
            if len(parts) == num_requests:
                return [part.strip() for part in parts]

        return None

    def _split_by_length(
        self,
        response: str,
        num_requests: int
    ) -> List[str]:
        """策略 3：按長度平均分配（降級）"""
        # 計算每個部分的長度
        length_per_request = len(response) // num_requests

        responses = []
        for i in range(num_requests):
            start = i * length_per_request
            end = start + length_per_request if i < num_requests - 1 else len(response)
            responses.append(response[start:end].strip())

        return responses

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計資訊

        Returns:
            統計資訊字典
        """
        total_requests = self.stats['total_requests']
        total_api_calls = self.stats['total_api_calls']

        return {
            **self.stats,
            'reduction_rate': (
                1 - (total_api_calls / total_requests)
            ) if total_requests > 0 else 0,
            'avg_batch_size': (
                self.stats['total_merged_requests'] / self.stats['merged_batches']
            ) if self.stats['merged_batches'] > 0 else 1
        }

    async def close(self):
        """關閉合併器（清理資源）"""
        # 取消所有計時器
        for timer in self.merge_timers.values():
            if not timer.done():
                timer.cancel()

        self.merge_timers.clear()
        self.pending_requests.clear()


# ==================== 使用範例 ====================

if __name__ == "__main__":
    import random

    async def demo():
        """示範批次請求合併"""
        print("\n" + "="*70)
        print("批次請求合併器示範")
        print("="*70 + "\n")

        # 模擬 API 調用
        api_call_count = 0

        async def mock_api_caller(content: str) -> str:
            """模擬 API 調用"""
            nonlocal api_call_count
            api_call_count += 1

            await asyncio.sleep(0.1)  # 模擬網路延遲

            # 簡單回應（按標記分隔）
            lines = content.split('\n')
            responses = []

            for i, line in enumerate(lines):
                if '[REQUEST_' in line:
                    req_id = re.search(r'\[REQUEST_(\d+)\]', line)
                    if req_id:
                        responses.append(
                            f"[RESPONSE_{req_id.group(1)}]"
                            f"Response to request {req_id.group(1)}"
                            f"[END_RESPONSE_{req_id.group(1)}]"
                        )

            return "\n\n".join(responses)

        # 創建合併器
        merger = BatchRequestMerger(
            merge_window=0.5,
            max_batch_size=10,
            verbose=True
        )

        # 測試 1：並行提交多個請求
        print("測試 1：並行提交 20 個請求")
        print("-" * 70)

        start = time.time()

        tasks = [
            merger.submit(
                model='gemini-2.5-flash',
                content=f'分析任務 {i}',
                api_caller=mock_api_caller
            )
            for i in range(20)
        ]

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        print(f"\n✅ 完成 {len(results)} 個請求")
        print(f"⏱️  總耗時：{elapsed:.2f}s")
        print(f"📞 API 調用次數：{api_call_count} 次")
        print(f"📊 減少率：{(1 - api_call_count/20)*100:.1f}%")

        # 統計資訊
        stats = merger.get_stats()
        print(f"\n統計資訊：")
        print(f"  總請求數：{stats['total_requests']}")
        print(f"  合併批次數：{stats['merged_batches']}")
        print(f"  平均批次大小：{stats['avg_batch_size']:.1f}")
        print(f"  API 調用減少：{stats['reduction_rate']*100:.1f}%")

        print("\n" + "="*70)
        print("示範完成")
        print("="*70 + "\n")

        await merger.close()

    asyncio.run(demo())
