#!/usr/bin/env python3
"""
CodeGemini Smart Context Builder Module
智能上下文建構器 - 為任務選擇最相關的程式碼上下文

此模組負責：
1. 建立任務專屬的上下文
2. 檔案相關性評分與優先排序
3. 提取相關程式碼片段
4. Token 預算管理
5. 漸進式上下文載入
6. 上下文壓縮策略
"""
import os
import re
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .scanner import ProjectContext, CodebaseScanner
from utils.i18n import safe_t

console = Console()


class RelevanceLevel(Enum):
    """相關性等級"""
    CRITICAL = "critical"      # 關鍵（>= 0.8）
    HIGH = "high"              # 高（>= 0.6）
    MEDIUM = "medium"          # 中（>= 0.4）
    LOW = "low"                # 低（>= 0.2）
    MINIMAL = "minimal"        # 最低（< 0.2）


@dataclass
class CodeSnippet:
    """程式碼片段"""
    file_path: str                      # 檔案路徑
    start_line: int                     # 起始行號
    end_line: int                       # 結束行號
    content: str                        # 內容
    relevance_score: float = 0.0        # 相關性分數
    context_type: str = "code"          # 類型（code, import, class, function）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileContext:
    """檔案上下文"""
    file_path: str                      # 檔案路徑
    relevance_score: float              # 相關性分數
    snippets: List[CodeSnippet] = field(default_factory=list)
    full_content: Optional[str] = None  # 完整內容（選用）
    estimated_tokens: int = 0           # 預估 token 數
    priority: int = 0                   # 優先級


@dataclass
class Context:
    """任務上下文"""
    task_description: str               # 任務描述
    project_context: ProjectContext     # 專案上下文
    file_contexts: List[FileContext] = field(default_factory=list)
    total_tokens: int = 0               # 總 token 數
    token_budget: int = 100000          # Token 預算（預設 100k）
    included_files: int = 0             # 包含的檔案數
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextBuilder:
    """智能上下文建構器"""

    # Token 估算常數（粗略估算：1 token ≈ 4 字元）
    CHARS_PER_TOKEN = 4

    # 最大上下文窗口（Gemini 2.0 Flash：1M tokens）
    MAX_CONTEXT_TOKENS = 1000000

    def __init__(
        self,
        project_path: str,
        token_budget: int = 100000,
        scanner: Optional[CodebaseScanner] = None
    ):
        """
        初始化上下文建構器

        Args:
            project_path: 專案路徑
            token_budget: Token 預算
            scanner: 程式碼庫掃描器（選用）
        """
        self.project_path = os.path.abspath(project_path)
        self.token_budget = min(token_budget, self.MAX_CONTEXT_TOKENS)
        self.scanner = scanner or CodebaseScanner()

        # 掃描專案（使用快取）
        self.project_context: Optional[ProjectContext] = None

    def build_for_task(
        self,
        task_description: str,
        keywords: Optional[List[str]] = None,
        max_files: int = 20,
        include_tests: bool = False
    ) -> Context:
        """
        為任務建立上下文

        Args:
            task_description: 任務描述
            keywords: 關鍵字列表（選用）
            max_files: 最大檔案數
            include_tests: 是否包含測試檔案

        Returns:
            Context: 建立的上下文
        """
        console.print(safe_t("context.build.starting", fallback="\n[#B565D8]🔨 建立任務上下文...[/#B565D8]"))
        console.print(safe_t("context.build.task", fallback="  任務：{task}...").format(task=task_description[:60]))

        # 步驟 1：掃描專案（如果還沒掃描）
        if not self.project_context:
            self.project_context = self.scanner.scan_project(
                self.project_path,
                build_symbol_index=False
            )

        # 步驟 2：提取關鍵字
        if not keywords:
            keywords = self._extract_keywords(task_description)

        console.print(safe_t("context.build.keywords", fallback="  關鍵字：{keywords}{more}").format(keywords=', '.join(keywords[:5]), more='...' if len(keywords) > 5 else ''))

        # 步驟 3：獲取候選檔案
        candidate_files = self.project_context.source_files
        if include_tests:
            candidate_files = candidate_files + self.project_context.test_files

        # 步驟 4：檔案優先級排序
        prioritized_files = self.prioritize_files(
            task_description,
            candidate_files,
            keywords
        )

        # 步驟 5：建立檔案上下文（漸進式載入）
        file_contexts = self._build_file_contexts(
            prioritized_files[:max_files],
            keywords,
            self.token_budget
        )

        # 步驟 6：計算總 token 數
        total_tokens = sum(fc.estimated_tokens for fc in file_contexts)

        # 步驟 7：建立上下文
        context = Context(
            task_description=task_description,
            project_context=self.project_context,
            file_contexts=file_contexts,
            total_tokens=total_tokens,
            token_budget=self.token_budget,
            included_files=len(file_contexts),
            metadata={
                'keywords': keywords,
                'max_files': max_files
            }
        )

        console.print(safe_t("context.build.completed", fallback="[#B565D8]✓ 上下文已建立[/#B565D8]"))
        console.print(safe_t("context.build.files", fallback="  包含檔案：{count}").format(count=context.included_files))
        console.print(safe_t("context.build.tokens", fallback="  預估 tokens：{tokens:,}").format(tokens=context.total_tokens))
        console.print(safe_t("context.build.usage", fallback="  預算使用率：{usage:.1f}%").format(usage=context.total_tokens / context.token_budget * 100))

        return context

    def prioritize_files(
        self,
        task_description: str,
        files: List[str],
        keywords: List[str]
    ) -> List[str]:
        """
        檔案優先級排序

        Args:
            task_description: 任務描述
            files: 檔案列表
            keywords: 關鍵字列表

        Returns:
            List[str]: 排序後的檔案列表（由高到低）
        """
        console.print(safe_t("context.relevance.calculating", fallback="\n[#B565D8]📊 計算檔案相關性...[/#B565D8]"))

        file_scores: List[Tuple[str, float]] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("評分中...", total=len(files))

            for file_path in files:
                score = self._calculate_file_relevance(
                    file_path,
                    task_description,
                    keywords
                )
                file_scores.append((file_path, score))
                progress.update(task, advance=1)

        # 排序（分數由高到低）
        file_scores.sort(key=lambda x: x[1], reverse=True)

        # 顯示前 10 個最相關的檔案
        console.print(safe_t("context.relevance.completed", fallback="[#B565D8]✓ 相關性評分完成[/#B565D8]"))
        console.print(safe_t("context.relevance.top10", fallback="\n[#B565D8]前 10 個最相關檔案：[/#B565D8]"))
        for i, (file, score) in enumerate(file_scores[:10], 1):
            level = self._get_relevance_level(score)
            console.print(f"  {i}. [{level.value}] {os.path.basename(file)} ({score:.2f})")

        return [file for file, _ in file_scores]

    def extract_relevant_code(
        self,
        file_path: str,
        keywords: List[str],
        max_snippets: int = 5
    ) -> List[CodeSnippet]:
        """
        提取相關程式碼片段

        Args:
            file_path: 檔案路徑
            keywords: 關鍵字列表
            max_snippets: 最大片段數

        Returns:
            List[CodeSnippet]: 程式碼片段列表
        """
        full_path = os.path.join(self.project_path, file_path)

        if not os.path.exists(full_path):
            return []

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            snippets = []

            # 簡單策略：找出包含關鍵字的行及其上下文
            for i, line in enumerate(lines):
                line_lower = line.lower()

                # 檢查是否包含關鍵字
                matches = [kw for kw in keywords if kw.lower() in line_lower]

                if matches:
                    # 提取上下文（前後 5 行）
                    start = max(0, i - 5)
                    end = min(len(lines), i + 6)

                    snippet = CodeSnippet(
                        file_path=file_path,
                        start_line=start + 1,
                        end_line=end,
                        content=''.join(lines[start:end]),
                        relevance_score=len(matches) / len(keywords),
                        metadata={'matched_keywords': matches}
                    )

                    snippets.append(snippet)

            # 合併重疊的片段
            snippets = self._merge_overlapping_snippets(snippets)

            # 排序並限制數量
            snippets.sort(key=lambda s: s.relevance_score, reverse=True)
            return snippets[:max_snippets]

        except Exception as e:
            console.print(safe_t("context.file.read_error", fallback="[#B565D8]警告：無法讀取 {path} - {error}[/#B565D8]").format(path=file_path, error=e))
            return []

    def estimate_token_usage(self, context: Context) -> int:
        """
        估算 Token 使用量

        Args:
            context: 上下文

        Returns:
            int: 估算的 token 數
        """
        # 使用已經計算好的 estimated_tokens，確保與 build_for_task 一致
        total_tokens = sum(fc.estimated_tokens for fc in context.file_contexts)

        return total_tokens

    def compress_context(
        self,
        context: Context,
        target_reduction: float = 0.5
    ) -> Context:
        """
        壓縮上下文（移除低相關性內容）

        Args:
            context: 原始上下文
            target_reduction: 目標減少比例（0-1）

        Returns:
            Context: 壓縮後的上下文
        """
        console.print(safe_t("context.compress.starting", fallback="\n[#B565D8]🗜️  壓縮上下文...[/#B565D8]"))
        console.print(safe_t("context.compress.original", fallback="  原始 tokens：{tokens:,}").format(tokens=context.total_tokens))
        console.print(safe_t("context.compress.target", fallback="  目標減少：{percent:.0f}%").format(percent=target_reduction * 100))

        # 策略 1：移除低相關性檔案
        threshold = 0.3
        filtered_files = [
            fc for fc in context.file_contexts
            if fc.relevance_score >= threshold
        ]

        # 策略 2：每個檔案只保留最相關的片段
        for fc in filtered_files:
            if len(fc.snippets) > 3:
                fc.snippets = fc.snippets[:3]

        # 重新計算 token
        compressed_context = Context(
            task_description=context.task_description,
            project_context=context.project_context,
            file_contexts=filtered_files,
            token_budget=context.token_budget,
            metadata=context.metadata
        )

        compressed_context.total_tokens = self.estimate_token_usage(compressed_context)
        compressed_context.included_files = len(filtered_files)

        console.print(safe_t("context.compress.completed", fallback="[#B565D8]✓ 壓縮完成[/#B565D8]"))
        console.print(safe_t("context.compress.after", fallback="  壓縮後 tokens：{tokens:,}").format(tokens=compressed_context.total_tokens))
        console.print(safe_t("context.compress.actual", fallback="  實際減少：{percent:.0f}%").format(percent=(1 - compressed_context.total_tokens / context.total_tokens) * 100))

        return compressed_context

    # ==================== 私有方法 ====================

    def _extract_keywords(self, text: str) -> List[str]:
        """從文字中提取關鍵字"""
        # 簡單的關鍵字提取（實際應使用 NLP）
        # 移除常見詞彙
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'please', 'can', 'could', 'should', 'would', 'will', 'do', 'does',
            '請', '的', '了', '在', '是', '和', '與', '或', '但', '為', '以',
            '實作', '新增', '建立', '修改', '刪除', '功能'
        }

        # 提取單詞（支援英文和中文）
        # 英文單詞
        english_words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        # 中文詞彙（2-4個字元）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)

        all_words = english_words + chinese_words

        # 過濾停用詞和短詞
        keywords = [
            w for w in all_words
            if len(w) > 1 and w.lower() not in stop_words
        ]

        # 去重並限制數量
        return list(dict.fromkeys(keywords))[:20]

    def _calculate_file_relevance(
        self,
        file_path: str,
        task_description: str,
        keywords: List[str]
    ) -> float:
        """
        計算檔案相關性分數（0-1）

        評分因素：
        1. 檔案名稱匹配（20%）
        2. 關鍵字出現頻率（50%）
        3. 檔案大小（適中優先）（10%）
        4. 最近修改時間（10%）
        5. 檔案類型（10%）
        """
        score = 0.0

        # 因素 1：檔案名稱匹配
        file_name = os.path.basename(file_path).lower()
        name_matches = sum(1 for kw in keywords if kw.lower() in file_name)
        score += (name_matches / max(len(keywords), 1)) * 0.2

        # 因素 2：關鍵字出現頻率
        full_path = os.path.join(self.project_path, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()

                keyword_count = sum(content.count(kw.lower()) for kw in keywords)
                # 正規化（避免過大）
                keyword_score = min(keyword_count / 10, 1.0)
                score += keyword_score * 0.5

                # 因素 3：檔案大小（適中優先，避免過大或過小）
                size = len(content)
                if 500 < size < 10000:  # 理想大小
                    score += 0.1
                elif 100 < size < 50000:  # 可接受
                    score += 0.05

            except Exception:
                pass

        # 因素 4：檔案類型（優先 .py 等源碼檔案）
        if file_path.endswith(('.py', '.js', '.ts', '.java')):
            score += 0.1

        return min(score, 1.0)

    def _get_relevance_level(self, score: float) -> RelevanceLevel:
        """取得相關性等級"""
        if score >= 0.8:
            return RelevanceLevel.CRITICAL
        elif score >= 0.6:
            return RelevanceLevel.HIGH
        elif score >= 0.4:
            return RelevanceLevel.MEDIUM
        elif score >= 0.2:
            return RelevanceLevel.LOW
        else:
            return RelevanceLevel.MINIMAL

    def _build_file_contexts(
        self,
        files: List[str],
        keywords: List[str],
        token_budget: int
    ) -> List[FileContext]:
        """建立檔案上下文（漸進式載入）"""
        file_contexts = []
        used_tokens = 0

        for file_path in files:
            # 檢查預算
            if used_tokens >= token_budget:
                console.print(safe_t("context.load.budget_reached", fallback="[#B565D8]已達 token 預算上限，停止載入[/#B565D8]"))
                break

            # 提取相關片段
            snippets = self.extract_relevant_code(file_path, keywords)

            # 如果沒有匹配的片段，至少包含檔案的開頭部分
            if not snippets:
                full_path = os.path.join(self.project_path, file_path)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            # 取前 50 行作為片段
                            preview_lines = min(50, len(lines))
                            snippet = CodeSnippet(
                                file_path=file_path,
                                start_line=1,
                                end_line=preview_lines,
                                content=''.join(lines[:preview_lines]),
                                relevance_score=0.1,  # 低相關性，但至少有內容
                                metadata={'type': 'file_preview'}
                            )
                            snippets = [snippet]
                    except Exception as e:
                        console.print(safe_t("context.file.read_error", fallback="[#B565D8]警告：無法讀取 {path} - {error}[/#B565D8]").format(path=file_path, error=e))
                        continue
                else:
                    continue

            # 計算相關性分數
            relevance_score = self._calculate_file_relevance(
                file_path,
                "",  # 這裡不再需要 task_description
                keywords
            )

            # 估算 tokens
            estimated_tokens = sum(
                len(s.content) // self.CHARS_PER_TOKEN
                for s in snippets
            )

            # 建立檔案上下文
            file_context = FileContext(
                file_path=file_path,
                relevance_score=relevance_score,
                snippets=snippets,
                estimated_tokens=estimated_tokens
            )

            file_contexts.append(file_context)
            used_tokens += estimated_tokens

        return file_contexts

    def _merge_overlapping_snippets(
        self,
        snippets: List[CodeSnippet]
    ) -> List[CodeSnippet]:
        """合併重疊的程式碼片段"""
        if not snippets:
            return []

        # 按起始行排序
        sorted_snippets = sorted(snippets, key=lambda s: s.start_line)

        merged = [sorted_snippets[0]]

        for current in sorted_snippets[1:]:
            last = merged[-1]

            # 如果重疊或相鄰，合併
            if current.start_line <= last.end_line + 1:
                # 合併
                last.end_line = max(last.end_line, current.end_line)
                last.content = self._merge_content(
                    last.file_path,
                    last.start_line,
                    last.end_line
                )
                last.relevance_score = max(last.relevance_score, current.relevance_score)
            else:
                merged.append(current)

        return merged

    def _merge_content(
        self,
        file_path: str,
        start_line: int,
        end_line: int
    ) -> str:
        """重新讀取合併後的內容"""
        full_path = os.path.join(self.project_path, file_path)

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            return ''.join(lines[start_line - 1:end_line])
        except Exception:
            return ""


def main():
    """測試用主程式"""
    import sys

    if len(sys.argv) < 2:
        console.print(safe_t("context.usage.title", fallback="[#B565D8]用法：[/#B565D8]"))
        console.print(safe_t("context.usage.syntax", fallback='  python builder.py <專案路徑> "<任務描述>"'))
        console.print(safe_t("context.usage.example_title", fallback="\n[#B565D8]範例：[/#B565D8]"))
        console.print(safe_t("context.usage.example", fallback='  python builder.py . "新增使用者登入功能"'))
        sys.exit(1)

    project_path = sys.argv[1]
    task_description = sys.argv[2] if len(sys.argv) > 2 else "測試任務"

    try:
        builder = ContextBuilder(project_path, token_budget=50000)
        context = builder.build_for_task(task_description, max_files=10)

        console.print(safe_t("context.main.success", fallback="\n[bold green]✅ 上下文建立成功[/bold green]"))
        console.print(safe_t("context.main.summary", fallback="\n[#B565D8]上下文摘要：[/#B565D8]"))
        console.print(safe_t("context.main.task", fallback="  任務：{task}").format(task=context.task_description))
        console.print(safe_t("context.main.files", fallback="  檔案數：{count}").format(count=context.included_files))
        console.print(safe_t("context.build.tokens", fallback="  預估 tokens：{tokens:,}").format(tokens=context.total_tokens))

        # 顯示檔案列表
        console.print(safe_t("context.main.files_list", fallback="\n[#B565D8]包含的檔案：[/#B565D8]"))
        for fc in context.file_contexts[:5]:
            console.print(safe_t("context.main.file_snippet", fallback="  - {path} (分數: {score:.2f}, 片段: {count})").format(path=fc.file_path, score=fc.relevance_score, count=len(fc.snippets)))

    except Exception as e:
        console.print(safe_t("context.main.error", fallback="\n[dim #B565D8]錯誤：{error}[/red]").format(error=e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
