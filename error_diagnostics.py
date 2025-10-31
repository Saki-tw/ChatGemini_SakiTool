#!/usr/bin/env python3
"""
智能錯誤診斷系統

當錯誤發生時：
1. 自動診斷問題根源
2. 生成一鍵解決方案（如果可行）
3. 提供可執行的修復指令
4. 如果無法自動修復，則顯示清晰的錯誤訊息
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class Solution:
    """解決方案數據結構"""
    title: str  # 解決方案標題
    description: str  # 詳細說明
    command: Optional[str] = None  # 可執行指令（一鍵修復）
    manual_steps: Optional[List[str]] = None  # 手動步驟
    priority: int = 1  # 優先級（1=最高）
    auto_fixable: bool = False  # 是否可自動修復
    fix_function: Optional[callable] = None  # 自動修復函數


class ErrorDiagnostics:
    """智能錯誤診斷系統"""

    def __init__(self):
        self.console = Console()

    def diagnose_and_suggest(
        self,
        error: Exception,
        operation: str,
        context: dict
    ) -> Tuple[str, List[Solution]]:
        """
        診斷錯誤並提供解決方案

        Args:
            error: 發生的異常
            operation: 操作名稱（如「音訊提取」）
            context: 上下文資訊 {
                'input_files': [...],
                'output_file': '...',
                'stderr': '...',
                ...
            }

        Returns:
            (error_message, solutions): 錯誤訊息和解決方案列表
        """
        error_str = str(error)
        solutions = []

        # 1. 磁碟空間不足
        if "Disk quota exceeded" in error_str or "No space left" in error_str:
            solutions = self._solve_disk_space_issue(context)

        # 2. 權限不足
        elif "Permission denied" in error_str:
            solutions = self._solve_permission_issue(context)

        # 3. 檔案損壞或格式錯誤
        elif any(kw in error_str for kw in ["Invalid data", "moov atom not found", "corrupt"]):
            solutions = self._solve_corrupted_file(context)

        # 4. 缺少音訊串流
        elif "does not contain any stream" in error_str:
            solutions = self._solve_no_audio_stream(context)

        # 5. 編碼格式不支援
        elif "codec not currently supported" in error_str:
            solutions = self._solve_unsupported_codec(context)

        # 6. 檔案不存在
        elif "No such file" in error_str or isinstance(error, FileNotFoundError):
            solutions = self._solve_file_not_found(context)

        # 7. 字型問題（字幕燒錄）
        elif "Fontconfig" in error_str or "font" in error_str.lower():
            solutions = self._solve_font_issue(context)

        # 8. 記憶體不足
        elif "out of memory" in error_str.lower() or "cannot allocate" in error_str.lower():
            solutions = self._solve_memory_issue(context)

        # 9. Python 參數錯誤（TypeError: unexpected keyword argument）
        elif "unexpected keyword argument" in error_str or isinstance(error, TypeError):
            solutions = self._solve_python_argument_error(error_str, context)

        # 10. Python 導入錯誤（ModuleNotFoundError, ImportError）
        elif "No module named" in error_str or isinstance(error, (ModuleNotFoundError, ImportError)):
            solutions = self._solve_python_import_error(error_str, context)

        # 11. Python 屬性錯誤（AttributeError）
        elif "has no attribute" in error_str or isinstance(error, AttributeError):
            solutions = self._solve_python_attribute_error(error_str, context)

        # 12. API 相關錯誤
        elif any(kw in error_str for kw in ["API", "quota", "rate limit", "401", "403", "429", "500", "503"]):
            solutions = self._solve_api_error(error_str, context)

        # 生成錯誤訊息
        error_message = self._format_error_message(error, operation, context)

        return error_message, solutions

    def _solve_disk_space_issue(self, context: dict) -> List[Solution]:
        """解決磁碟空間不足問題"""
        output_dir = os.path.dirname(context.get('output_file', ''))
        if not output_dir:
            output_dir = os.getcwd()

        # 取得磁碟使用情況
        try:
            total, used, free = shutil.disk_usage(output_dir)
            free_gb = free / (1024**3)
        except:
            free_gb = 0

        solutions = [
            Solution(
                title="清理臨時檔案",
                description=f"當前剩餘空間：{free_gb:.2f} GB。清理系統臨時檔案可釋放空間。",
                command=f"find /tmp -type f -name '*.tmp' -o -name '*.temp' | xargs rm -f",
                priority=1,
                auto_fixable=False  # 需要用戶確認
            ),
            Solution(
                title="清理專案臨時檔案",
                description="清理本專案的臨時音訊/影片檔案",
                command=f"find {output_dir} -type f -name '*_temp.*' -o -name '*_tmp.*' | xargs rm -f",
                priority=2,
                auto_fixable=False
            ),
            Solution(
                title="更改輸出目錄",
                description="將輸出目錄改為空間較大的磁碟",
                manual_steps=[
                    "1. 使用 df -h 查看可用磁碟空間",
                    "2. 修改輸出路徑參數至空間充足的目錄",
                    "3. 重新執行操作"
                ],
                priority=3
            )
        ]

        return solutions

    def _solve_permission_issue(self, context: dict) -> List[Solution]:
        """解決權限不足問題"""
        input_files = context.get('input_files', [])
        output_file = context.get('output_file', '')

        # 檢查哪個檔案有權限問題
        problem_files = []
        for f in input_files + [output_file]:
            if f and os.path.exists(f):
                if not os.access(f, os.R_OK):
                    problem_files.append((f, '讀取'))
                elif f == output_file and not os.access(os.path.dirname(f) or '.', os.W_OK):
                    problem_files.append((f, '寫入'))

        solutions = []

        if problem_files:
            for file_path, permission_type in problem_files:
                solutions.append(Solution(
                    title=f"修復檔案權限：{os.path.basename(file_path)}",
                    description=f"檔案缺少{permission_type}權限",
                    command=f"chmod 644 '{file_path}'",
                    priority=1,
                    auto_fixable=False
                ))

        # 通用解決方案
        if output_file:
            output_dir = os.path.dirname(output_file) or '.'
            solutions.append(Solution(
                title="修復輸出目錄權限",
                description="確保對輸出目錄有寫入權限",
                command=f"chmod 755 '{output_dir}'",
                priority=2,
                auto_fixable=False
            ))

        return solutions

    def _solve_corrupted_file(self, context: dict) -> List[Solution]:
        """解決檔案損壞問題"""
        input_files = context.get('input_files', [])

        solutions = [
            Solution(
                title="驗證檔案完整性",
                description="使用 ffprobe 檢查檔案是否真的損壞",
                command=f"ffprobe -v error '{input_files[0]}'" if input_files else None,
                priority=1,
                auto_fixable=False
            ),
            Solution(
                title="嘗試修復檔案",
                description="使用 ffmpeg 重新封裝檔案（可能修復輕微損壞）",
                command=f"ffmpeg -i '{input_files[0]}' -c copy '{input_files[0]}.repaired.mp4'" if input_files else None,
                priority=2,
                auto_fixable=False
            ),
            Solution(
                title="重新下載或獲取檔案",
                description="如果檔案確實損壞，建議重新獲取原始檔案",
                manual_steps=[
                    "1. 確認檔案來源",
                    "2. 重新下載或複製檔案",
                    "3. 驗證檔案完整性（檢查檔案大小、MD5 等）",
                    "4. 重新執行操作"
                ],
                priority=3
            )
        ]

        return solutions

    def _solve_no_audio_stream(self, context: dict) -> List[Solution]:
        """解決缺少音訊串流問題"""
        input_files = context.get('input_files', [])

        solutions = [
            Solution(
                title="檢查檔案串流資訊",
                description="確認檔案是否包含音訊軌",
                command=f"ffprobe -v error -show_streams '{input_files[0]}'" if input_files else None,
                priority=1,
                auto_fixable=False
            ),
            Solution(
                title="使用其他檔案",
                description="如果檔案確實沒有音訊，請使用包含音訊的檔案",
                manual_steps=[
                    "1. 確認影片檔案是否包含音軌",
                    "2. 如果是無聲影片，請先添加音軌",
                    "3. 或使用其他包含音訊的影片"
                ],
                priority=2
            )
        ]

        return solutions

    def _solve_unsupported_codec(self, context: dict) -> List[Solution]:
        """解決編碼格式不支援問題"""
        input_files = context.get('input_files', [])

        solutions = [
            Solution(
                title="轉換為常見格式",
                description="將檔案轉換為 H.264/AAC 格式（最廣泛支援）",
                command=f"ffmpeg -i '{input_files[0]}' -c:v libx264 -c:a aac '{input_files[0]}.converted.mp4'" if input_files else None,
                priority=1,
                auto_fixable=False
            ),
            Solution(
                title="檢查 ffmpeg 編碼器",
                description="查看 ffmpeg 支援的編碼器",
                command="ffmpeg -codecs",
                priority=2,
                auto_fixable=False
            )
        ]

        return solutions

    def _solve_file_not_found(self, context: dict) -> List[Solution]:
        """解決檔案不存在問題"""
        input_files = context.get('input_files', [])

        solutions = []

        for file_path in input_files:
            if not file_path:
                continue

            # 嘗試找相似檔名
            parent_dir = os.path.dirname(file_path) or '.'
            filename = os.path.basename(file_path)

            similar_files = []
            if os.path.isdir(parent_dir):
                for f in os.listdir(parent_dir):
                    if f.lower().startswith(filename[:5].lower()):
                        similar_files.append(f)

            if similar_files:
                solutions.append(Solution(
                    title="可能的相似檔案",
                    description=f"在 {parent_dir} 找到相似檔案：{', '.join(similar_files[:3])}",
                    manual_steps=[
                        "1. 確認檔案路徑是否正確",
                        "2. 檢查上述相似檔案是否為目標檔案",
                        "3. 更正檔案路徑後重試"
                    ],
                    priority=1
                ))

            solutions.append(Solution(
                title="檢查檔案路徑",
                description="確認檔案是否存在於指定位置",
                command=f"ls -lh '{parent_dir}'",
                priority=2,
                auto_fixable=False
            ))

        return solutions

    def _solve_font_issue(self, context: dict) -> List[Solution]:
        """解決字型問題"""
        solutions = [
            Solution(
                title="安裝中文字型",
                description="字幕燒錄需要中文字型支援",
                command="brew install --cask font-noto-sans-cjk",  # macOS
                priority=1,
                auto_fixable=False
            ),
            Solution(
                title="指定字型檔案",
                description="在字幕樣式中明確指定字型檔案路徑",
                manual_steps=[
                    "1. 找到系統中的字型檔案（.ttf 或 .otf）",
                    "2. 在字幕參數中指定字型路徑",
                    "3. 重新執行燒錄"
                ],
                priority=2
            )
        ]

        return solutions

    def _solve_memory_issue(self, context: dict) -> List[Solution]:
        """解決記憶體不足問題"""
        solutions = [
            Solution(
                title="降低處理品質",
                description="使用較低的解析度或位元率",
                manual_steps=[
                    "1. 調整輸出解析度（如 1080p → 720p）",
                    "2. 降低位元率參數",
                    "3. 重新執行操作"
                ],
                priority=1
            ),
            Solution(
                title="分段處理",
                description="將大檔案分段處理後再合併",
                manual_steps=[
                    "1. 使用 ffmpeg 將影片分段",
                    "2. 逐段處理",
                    "3. 合併處理後的片段"
                ],
                priority=2
            ),
            Solution(
                title="釋放系統記憶體",
                description="關閉其他應用程式以釋放記憶體",
                manual_steps=[
                    "1. 關閉不必要的應用程式",
                    "2. 清理系統快取",
                    "3. 重新執行操作"
                ],
                priority=3
            )
        ]

        return solutions

    def _solve_python_argument_error(self, error_str: str, context: dict) -> List[Solution]:
        """解決 Python 參數錯誤"""
        solutions = []

        # 分析錯誤訊息，提取不支援的參數名稱
        if "unexpected keyword argument" in error_str:
            # 提取參數名稱，例如：got an unexpected keyword argument 'flush'
            import re
            match = re.search(r"unexpected keyword argument '(\w+)'", error_str)
            param_name = match.group(1) if match else "unknown"

            # 提取函數名稱
            func_match = re.search(r"(\w+\.?\w+)\(\)", error_str)
            func_name = func_match.group(1) if func_match else "函數"

            solutions.append(Solution(
                title=f"移除不支援的參數 '{param_name}'",
                description=f"{func_name} 不支援 '{param_name}' 參數，這通常是因為版本不相容",
                manual_steps=[
                    f"1. 檢查 {func_name} 的版本和文檔",
                    f"2. 移除或替換 '{param_name}' 參數",
                    "3. 或升級相關套件到支援該參數的版本"
                ],
                priority=1
            ))

            # 針對 Rich Console.print(flush=True) 的特殊處理
            if "console.print" in error_str.lower() and param_name == "flush":
                def fix_console_flush():
                    """自動修復 console.print(flush=True) 問題"""
                    import re
                    import glob

                    # 搜尋所有 Python 檔案
                    files_modified = []
                    pattern = r'console\.print\(([^)]*),\s*flush=True\)'

                    for py_file in glob.glob('**/*.py', recursive=True):
                        if 'venv' in py_file or '__pycache__' in py_file:
                            continue

                        try:
                            with open(py_file, 'r', encoding='utf-8') as f:
                                content = f.read()

                            # 檢查是否有需要修復的地方
                            if re.search(pattern, content):
                                # 移除 flush=True 參數
                                new_content = re.sub(pattern, r'console.print(\1)', content)

                                with open(py_file, 'w', encoding='utf-8') as f:
                                    f.write(new_content)

                                files_modified.append(py_file)
                        except Exception as e:
                            console.print(f"[yellow]⚠️  無法處理 {py_file}: {e}[/yellow]")

                    return files_modified

                solutions.append(Solution(
                    title="Rich Console 不支援 flush 參數",
                    description="Rich 的 console.print() 會自動處理輸出緩衝，不需要 flush 參數",
                    manual_steps=[
                        "1. 移除 console.print() 中的 flush=True 參數",
                        "2. 如需立即輸出，Rich 會自動處理",
                        "3. 或改用標準 print() 函數（支援 flush 參數）"
                    ],
                    command="# 自動搜尋並修復所有 console.print(flush=True)",
                    priority=1,
                    auto_fixable=True,
                    fix_function=fix_console_flush
                ))

        return solutions

    def _solve_python_import_error(self, error_str: str, context: dict) -> List[Solution]:
        """解決 Python 導入錯誤"""
        solutions = []

        # 提取模組名稱
        import re
        match = re.search(r"No module named '(\S+)'", error_str)
        module_name = match.group(1) if match else "unknown"

        # 特殊處理：config_manager 導入錯誤（ChatGemini 內部模組）
        if module_name == "config_manager" and context.get('command') == 'config':
            solutions.append(Solution(
                title="CodeGemini 配置管理器路徑問題",
                description="config_manager 是 CodeGemini 內部模組，應該從 CodeGemini.config_manager 導入",
                manual_steps=[
                    "1. 檢查 CodeGemini/ 目錄是否存在",
                    "2. 檢查 CodeGemini/config_manager.py 是否存在",
                    "3. 系統將自動嘗試重新載入配置管理器"
                ],
                priority=1,
                auto_fixable=True
            ))
            return solutions

        # 一般的模組導入錯誤
        solutions.append(Solution(
            title=f"安裝缺少的模組 '{module_name}'",
            description=f"系統找不到模組 '{module_name}'，需要安裝",
            command=f"pip install {module_name}",
            priority=1,
            auto_fixable=False
        ))

        # 常見套件的特殊處理
        package_map = {
            "prompt_toolkit": "prompt-toolkit",
            "google.genai": "google-generativeai",
            "PIL": "Pillow",
            "cv2": "opencv-python",
            "interactive_config_menu": "CodeGemini.config_manager"
        }

        if module_name in package_map:
            actual_package = package_map[module_name]
            if module_name == "interactive_config_menu":
                solutions[0].title = "導入路徑錯誤"
                solutions[0].description = f"'{module_name}' 應該從 '{actual_package}' 導入"
                solutions[0].command = None
                solutions[0].manual_steps = [
                    f"將 'from {module_name} import ...' 改為 'from {actual_package} import ...'"
                ]
            else:
                solutions[0].command = f"pip install {actual_package}"
                solutions[0].description = f"模組 '{module_name}' 需要安裝套件 '{actual_package}'"

        return solutions

    def _solve_python_attribute_error(self, error_str: str, context: dict) -> List[Solution]:
        """解決 Python 屬性錯誤"""
        solutions = []

        # 提取物件和屬性名稱
        import re
        match = re.search(r"'(\w+)' object has no attribute '(\w+)'", error_str)
        if match:
            object_type, attr_name = match.groups()

            solutions.append(Solution(
                title=f"'{object_type}' 物件缺少屬性 '{attr_name}'",
                description="這可能是因為版本不相容或 API 變更",
                manual_steps=[
                    "1. 檢查相關套件的版本",
                    "2. 查看最新的 API 文檔",
                    "3. 確認屬性名稱是否正確",
                    "4. 考慮更新或降級相關套件"
                ],
                priority=1
            ))

        return solutions

    def _solve_api_error(self, error_str: str, context: dict) -> List[Solution]:
        """解決 API 相關錯誤"""
        solutions = []

        # API 金鑰錯誤
        if "401" in error_str or "unauthorized" in error_str.lower():
            solutions.append(Solution(
                title="API 金鑰無效",
                description="請檢查 API 金鑰是否正確設定",
                manual_steps=[
                    "1. 確認環境變數 GEMINI_API_KEY 已設定",
                    "2. 檢查 API 金鑰是否正確",
                    "3. 確認 API 金鑰尚未過期",
                    "4. 到 https://makersuite.google.com/app/apikey 重新生成金鑰"
                ],
                command="echo $GEMINI_API_KEY",
                priority=1
            ))

        # 速率限制
        elif "429" in error_str or "rate limit" in error_str.lower():
            solutions.append(Solution(
                title="API 速率限制",
                description="請求過於頻繁，需要降低請求頻率",
                manual_steps=[
                    "1. 等待一段時間後重試",
                    "2. 在請求間加入延遲",
                    "3. 考慮升級 API 配額"
                ],
                priority=1
            ))

        # 配額用盡
        elif "quota" in error_str.lower() or "resource exhausted" in error_str.lower():
            solutions.append(Solution(
                title="API 配額已用盡",
                description="已達到 API 使用限制",
                manual_steps=[
                    "1. 檢查配額使用情況",
                    "2. 等待配額重置（通常為每分鐘或每日）",
                    "3. 考慮升級到付費方案"
                ],
                priority=1
            ))

        # 伺服器錯誤
        elif any(code in error_str for code in ["500", "503", "502", "504"]):
            solutions.append(Solution(
                title="API 伺服器錯誤",
                description="Gemini API 伺服器暫時無法使用",
                manual_steps=[
                    "1. 等待幾分鐘後重試",
                    "2. 檢查 Google Cloud 服務狀態",
                    "3. 如持續發生，請回報問題"
                ],
                priority=1
            ))

        return solutions

    def _format_error_message(
        self,
        error: Exception,
        operation: str,
        context: dict
    ) -> str:
        """格式化錯誤訊息"""
        error_str = str(error)

        # 簡化常見錯誤訊息
        if "Invalid data found" in error_str or "moov atom not found" in error_str:
            return f"{operation}失敗：影片檔案格式錯誤或損壞"
        elif "Permission denied" in error_str:
            return f"{operation}失敗：檔案權限不足"
        elif "Disk quota exceeded" in error_str or "No space left" in error_str:
            return f"{operation}失敗：磁碟空間不足"
        elif "does not contain any stream" in error_str:
            return f"{operation}失敗：檔案不包含有效音訊串流"
        elif "codec not currently supported" in error_str:
            return f"{operation}失敗：不支援的編碼格式"
        elif isinstance(error, FileNotFoundError):
            return f"{operation}失敗：找不到指定檔案"
        elif "unexpected keyword argument" in error_str:
            return f"{operation}失敗：函數參數不相容（可能是套件版本問題）"
        elif "No module named" in error_str:
            return f"{operation}失敗：缺少必要的 Python 模組"
        elif "has no attribute" in error_str:
            return f"{operation}失敗：API 不相容（可能是版本問題）"
        elif any(kw in error_str for kw in ["401", "403", "API key"]):
            return f"{operation}失敗：API 金鑰無效或權限不足"
        elif any(kw in error_str for kw in ["429", "rate limit"]):
            return f"{operation}失敗：API 請求頻率過高"
        elif any(kw in error_str for kw in ["500", "503", "502", "504"]):
            return f"{operation}失敗：API 伺服器錯誤"
        else:
            return f"{operation}失敗：{error_str}"

    def display_solutions(
        self,
        error_message: str,
        solutions: List[Solution]
    ) -> None:
        """
        顯示錯誤訊息和解決方案

        Args:
            error_message: 錯誤訊息
            solutions: 解決方案列表
        """
        # 顯示錯誤訊息
        console.print(f"\n[dim #E8C4F0]✗ {error_message}[/red]\n")

        if not solutions:
            console.print("[dim]無可用的自動解決方案[/dim]")
            return

        # 按優先級排序
        solutions.sort(key=lambda s: s.priority)

        # 顯示解決方案
        console.print("[#E8C4F0]💡 建議的解決方案：[/#E8C4F0]\n")

        for i, solution in enumerate(solutions, 1):
            # 解決方案標題
            if solution.auto_fixable:
                icon = "🔧"
                auto_tag = " [#B565D8](可自動修復)[/green]"
            elif solution.command:
                icon = "⚡"
                auto_tag = " [#E8C4F0](一鍵執行)[/#E8C4F0]"
            else:
                icon = "📝"
                auto_tag = ""

            console.print(f"{icon} [bold]{i}. {solution.title}{auto_tag}[/bold]")
            console.print(f"   [dim]{solution.description}[/dim]")

            # 顯示指令
            if solution.command:
                console.print(f"   [#B565D8]執行指令：[/green]")
                console.print(Panel(
                    solution.command,
                    border_style="green",
                    padding=(0, 1)
                ))

            # 顯示手動步驟
            if solution.manual_steps:
                console.print(f"   [#E8C4F0]手動步驟：[/#E8C4F0]")
                for step in solution.manual_steps:
                    console.print(f"   {step}")

            console.print()  # 空行

        # 互動式修復提示（僅針對可自動修復的方案）
        auto_fixable_solutions = [s for s in solutions if s.auto_fixable and s.fix_function]
        if auto_fixable_solutions:
            console.print("\n[#B565D8]🔧 自動修復選項：[/#B565D8]")
            try:
                response = input("是否要自動修復此問題？(y/n): ").strip().lower()
                if response in ['y', 'yes', 'Y', 'YES']:
                    # 執行第一個可自動修復的方案
                    solution = auto_fixable_solutions[0]
                    console.print(f"\n[#B565D8]執行修復：{solution.title}[/#B565D8]")

                    try:
                        result = solution.fix_function()
                        if result:
                            console.print(f"\n[#B565D8]✅ 修復完成！[/green]")
                            if isinstance(result, list):
                                console.print(f"   已修改 {len(result)} 個檔案：")
                                for file in result[:5]:  # 只顯示前 5 個
                                    console.print(f"   - {file}")
                                if len(result) > 5:
                                    console.print(f"   ... 以及其他 {len(result) - 5} 個檔案")
                        else:
                            console.print("\n[yellow]⚠️  未找到需要修復的項目[/yellow]")
                    except Exception as fix_error:
                        console.print(f"\n[red]✗ 自動修復失敗：{fix_error}[/red]")
                        console.print("[dim]請嘗試手動修復[/dim]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]已取消自動修復[/dim]")


def diagnose_error(
    error: Exception,
    operation: str,
    context: dict
) -> Tuple[str, List[Solution]]:
    """
    便捷函數：診斷錯誤並返回訊息和解決方案

    Args:
        error: 發生的異常
        operation: 操作名稱
        context: 上下文資訊

    Returns:
        (error_message, solutions)
    """
    diagnostics = ErrorDiagnostics()
    return diagnostics.diagnose_and_suggest(error, operation, context)


def display_error_with_solutions(
    error: Exception,
    operation: str,
    context: dict
) -> None:
    """
    便捷函數：診斷錯誤並顯示解決方案

    Args:
        error: 發生的異常
        operation: 操作名稱
        context: 上下文資訊
    """
    diagnostics = ErrorDiagnostics()
    error_message, solutions = diagnostics.diagnose_and_suggest(error, operation, context)
    diagnostics.display_solutions(error_message, solutions)


if __name__ == "__main__":
    # 測試範例
    console.print("[bold #E8C4F0]智能錯誤診斷系統 - 測試範例[/bold #E8C4F0]\n")

    # 模擬磁碟空間不足錯誤
    error = RuntimeError("ffmpeg: Disk quota exceeded")
    context = {
        'input_files': ['/path/to/video.mp4'],
        'output_file': '/path/to/output.mp4',
        'stderr': 'Disk quota exceeded'
    }

    display_error_with_solutions(error, "音訊提取", context)
