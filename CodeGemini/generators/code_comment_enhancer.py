#!/usr/bin/env python3
"""
程式碼註解增強模組 - Code Comment Enhancement

設計哲學：
- 適度註解 - 只為複雜邏輯添加註解，避免過度註解
- 清晰表達 - 使用自然語言解釋「為什麼」而非「做什麼」
- 格式保留 - 完美保留原始縮排和程式碼結構

Created: 2025-11-01
Author: Claude Code with Saki-tw
"""

import ast
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


@dataclass
class ComplexityMarker:
    """複雜度標記"""
    line_number: int        # 行號
    complexity_type: str    # 複雜度類型: nested_loop, complex_condition, algorithm
    severity: int           # 嚴重程度 1-5
    context: str           # 程式碼上下文
    indentation: str       # 縮排空格
    description: str = ""  # 描述


class ComplexityAnalyzer:
    """程式碼複雜度分析器"""

    def __init__(self):
        self.markers: List[ComplexityMarker] = []

    def analyze(self, code: str) -> List[ComplexityMarker]:
        """分析程式碼複雜度"""
        self.markers = []

        try:
            tree = ast.parse(code)
            self._analyze_tree(tree, code)
        except SyntaxError as e:
            console.print(f"[red]✗ 程式碼語法錯誤: {e}[/red]")
            return []

        # 依照行號排序
        self.markers.sort(key=lambda m: m.line_number)
        return self.markers

    def _analyze_tree(self, tree: ast.AST, code: str):
        """分析 AST 樹"""
        code_lines = code.split('\n')

        # 遍歷所有節點
        for node in ast.walk(tree):
            # 檢測嵌套迴圈
            if isinstance(node, (ast.For, ast.While)):
                depth = self._get_loop_depth(node)
                if depth >= 2:
                    line_num = node.lineno
                    indentation = self._get_indentation(code_lines, line_num - 1)

                    self.markers.append(ComplexityMarker(
                        line_number=line_num,
                        complexity_type='nested_loop',
                        severity=min(depth, 5),
                        context=self._get_node_context(node, code_lines),
                        indentation=indentation,
                        description=f'嵌套迴圈深度: {depth}'
                    ))

            # 檢測複雜條件判斷
            elif isinstance(node, ast.If):
                condition_complexity = self._get_condition_complexity(node.test)
                if condition_complexity >= 3:
                    line_num = node.lineno
                    indentation = self._get_indentation(code_lines, line_num - 1)

                    self.markers.append(ComplexityMarker(
                        line_number=line_num,
                        complexity_type='complex_condition',
                        severity=min(condition_complexity, 5),
                        context=self._get_node_context(node, code_lines),
                        indentation=indentation,
                        description=f'複雜條件: {condition_complexity} 個邏輯運算'
                    ))

            # 檢測複雜函數（行數 > 50 或參數 > 5）
            elif isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno'):
                    func_lines = node.end_lineno - node.lineno
                    param_count = len(node.args.args)

                    if func_lines > 50 or param_count > 5:
                        line_num = node.lineno
                        indentation = self._get_indentation(code_lines, line_num - 1)

                        severity = 2
                        if func_lines > 100:
                            severity = 4
                        elif param_count > 8:
                            severity = 3

                        self.markers.append(ComplexityMarker(
                            line_number=line_num,
                            complexity_type='algorithm',
                            severity=severity,
                            context=self._get_node_context(node, code_lines),
                            indentation=indentation,
                            description=f'複雜函數: {func_lines} 行, {param_count} 個參數'
                        ))

    def _get_loop_depth(self, node: ast.AST, depth: int = 1) -> int:
        """計算迴圈嵌套深度"""
        max_depth = depth

        for child in ast.walk(node):
            if child != node and isinstance(child, (ast.For, ast.While)):
                child_depth = self._get_loop_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _get_condition_complexity(self, node: ast.AST) -> int:
        """計算條件複雜度（邏輯運算符數量）"""
        complexity = 0

        for child in ast.walk(node):
            if isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.Compare):
                # 比較運算符數量
                complexity += len(child.ops)

        return complexity

    def _get_indentation(self, lines: List[str], line_index: int) -> str:
        """取得行的縮排"""
        if 0 <= line_index < len(lines):
            line = lines[line_index]
            match = re.match(r'^(\s*)', line)
            return match.group(1) if match else ''
        return ''

    def _get_node_context(self, node: ast.AST, lines: List[str]) -> str:
        """取得節點的程式碼上下文"""
        if hasattr(node, 'lineno'):
            line_num = node.lineno - 1
            if 0 <= line_num < len(lines):
                # 取得該行和後續 2 行（如果存在）
                context_lines = []
                for i in range(3):
                    if line_num + i < len(lines):
                        context_lines.append(lines[line_num + i])
                return '\n'.join(context_lines)
        return ''


class CommentGenerator:
    """註解生成器"""

    def __init__(self, api_key: Optional[str] = None):
        """初始化生成器

        Args:
            api_key: Gemini API 金鑰，如果為 None 則使用環境變數
        """
        import os
        from google import genai

        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("未找到 Gemini API 金鑰")

        self.client = genai.Client(api_key=self.api_key)

    def generate_comment(self, marker: ComplexityMarker) -> str:
        """為標記的複雜程式碼生成註解"""

        # 根據複雜度類型設計 prompt
        if marker.complexity_type == 'nested_loop':
            prompt_type = "嵌套迴圈"
            focus = "解釋迴圈的目的、迭代邏輯和時間複雜度"
        elif marker.complexity_type == 'complex_condition':
            prompt_type = "複雜條件判斷"
            focus = "解釋條件的業務邏輯和判斷意圖"
        else:
            prompt_type = "複雜函數或演算法"
            focus = "解釋函數的整體目的和核心邏輯"

        prompt = f"""你是一個專業的程式碼註解助手。請為以下 Python 程式碼生成簡潔、清晰的註解。

程式碼類型: {prompt_type}
複雜度描述: {marker.description}

程式碼片段:
```python
{marker.context}
```

請生成註解，要求：
1. 使用繁體中文
2. {focus}
3. 只輸出註解內容（不包含 # 符號和程式碼）
4. 不超過 2 行
5. 清晰、專業、避免廢話

註解內容:"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )

            # 提取並清理註解
            comment = response.text.strip()

            # 移除可能的 markdown 標記
            comment = re.sub(r'```.*?```', '', comment, flags=re.DOTALL)
            comment = comment.strip()

            # 移除開頭的 # 符號（如果有）
            comment = re.sub(r'^#+\s*', '', comment, flags=re.MULTILINE)

            return comment

        except Exception as e:
            console.print(f"[yellow]⚠ 註解生成失敗: {e}[/yellow]")
            # 返回預設註解
            return f"複雜度: {marker.description}"

    def batch_generate(self, markers: List[ComplexityMarker]) -> Dict[int, str]:
        """批次生成多個註解

        Returns:
            Dict[行號, 註解內容]
        """
        comments = {}

        for i, marker in enumerate(markers, 1):
            console.print(f"[dim]生成註解 {i}/{len(markers)}...[/dim]")
            comment = self.generate_comment(marker)
            comments[marker.line_number] = (comment, marker.indentation)

        return comments


class CodeFormatter:
    """程式碼格式化器 - 負責註解插入和格式保留"""

    @staticmethod
    def insert_comments(code: str, comments: Dict[int, Tuple[str, str]]) -> str:
        """插入註解到程式碼

        Args:
            code: 原始程式碼
            comments: Dict[行號, (註解內容, 縮排)]

        Returns:
            插入註解後的程式碼
        """
        lines = code.split('\n')
        result_lines = []

        for i, line in enumerate(lines, 1):
            # 如果這一行需要插入註解
            if i in comments:
                comment_text, indentation = comments[i]

                # 將多行註解分割
                comment_lines = comment_text.split('\n')

                # 插入註解（每行都加上 # 和縮排）
                for comment_line in comment_lines:
                    if comment_line.strip():
                        result_lines.append(f"{indentation}# {comment_line.strip()}")

            # 保留原始程式碼行
            result_lines.append(line)

        return '\n'.join(result_lines)

    @staticmethod
    def preview_changes(original: str, enhanced: str) -> None:
        """預覽變更（使用 Rich 語法高亮）"""
        console.print("\n[bold #B565D8]📝 註解增強預覽[/bold #B565D8]\n")

        # 原始程式碼
        console.print(Panel(
            Syntax(original, "python", theme="monokai", line_numbers=True),
            title="[bold]原始程式碼[/bold]",
            border_style="dim"
        ))

        console.print("\n[bold green]↓ 增強後 ↓[/bold green]\n")

        # 增強後程式碼
        console.print(Panel(
            Syntax(enhanced, "python", theme="monokai", line_numbers=True),
            title="[bold]增強後程式碼[/bold]",
            border_style="green"
        ))


class CodeCommentEnhancer:
    """程式碼註解增強主類別"""

    def __init__(self, api_key: Optional[str] = None):
        self.analyzer = ComplexityAnalyzer()
        self.generator = CommentGenerator(api_key)
        self.formatter = CodeFormatter()

    def enhance(self, code: str, preview: bool = True) -> str:
        """增強程式碼註解

        Args:
            code: 原始程式碼
            preview: 是否預覽變更

        Returns:
            增強後的程式碼
        """
        console.print("\n[bold #B565D8]🔍 分析程式碼複雜度...[/bold #B565D8]")

        # 1. 分析複雜度
        markers = self.analyzer.analyze(code)

        if not markers:
            console.print("[green]✓ 程式碼結構簡單，無需額外註解[/green]")
            return code

        console.print(f"[#87CEEB]發現 {len(markers)} 個需要註解的位置[/#87CEEB]\n")

        # 顯示標記
        for i, marker in enumerate(markers, 1):
            severity_color = "yellow" if marker.severity < 3 else "red"
            console.print(
                f"  [{severity_color}]{i}. 第 {marker.line_number} 行 - "
                f"{marker.complexity_type} (嚴重度: {marker.severity})[/{severity_color}]"
            )

        console.print(f"\n[bold #B565D8]💬 生成註解...[/bold #B565D8]")

        # 2. 生成註解
        comments = self.generator.batch_generate(markers)

        # 3. 插入註解
        enhanced_code = self.formatter.insert_comments(code, comments)

        # 4. 預覽變更
        if preview:
            self.formatter.preview_changes(code, enhanced_code)

        return enhanced_code

    def enhance_file(self, file_path: str, output_path: Optional[str] = None, preview: bool = True) -> bool:
        """增強檔案的註解

        Args:
            file_path: 輸入檔案路徑
            output_path: 輸出檔案路徑（如果為 None 則覆蓋原檔案）
            preview: 是否預覽變更

        Returns:
            是否成功
        """
        try:
            # 讀取原始檔案
            with open(file_path, 'r', encoding='utf-8') as f:
                original_code = f.read()

            # 增強註解
            enhanced_code = self.enhance(original_code, preview=preview)

            # 寫入結果
            output = output_path or file_path
            with open(output, 'w', encoding='utf-8') as f:
                f.write(enhanced_code)

            console.print(f"\n[green]✓ 已儲存到: {output}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]✗ 處理失敗: {e}[/red]")
            return False


def main():
    """主程式 - 供測試使用"""
    import sys

    if len(sys.argv) < 2:
        console.print("[yellow]用法: python code_comment_enhancer.py <檔案路徑> [輸出路徑][/yellow]")
        sys.exit(1)

    file_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    enhancer = CodeCommentEnhancer()
    success = enhancer.enhance_file(file_path, output_path)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
