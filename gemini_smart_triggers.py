#!/usr/bin/env python3
"""
智能觸發器模組 - 無痕整合 CodeGemini 功能

此模組負責：
1. 分析使用者輸入，檢測意圖（任務規劃、網頁搜尋、程式碼分析等）
2. 自動觸發相應的 CodeGemini 功能
3. 將功能結果無縫整合到對話上下文中

設計理念：
- 使用者無需明確指定功能
- 根據語義自動判斷並增強提示
- 所有功能在背景運行，不打斷對話流程
"""

import re
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


# ==========================================
# 意圖檢測函數
# ==========================================

def detect_task_planning_intent(user_input: str) -> bool:
    """
    檢測是否需要任務規劃功能

    觸發條件：
    - 包含開發、實作、建立等關鍵字
    - 要求創建新功能
    - 複雜的多步驟任務

    Args:
        user_input: 使用者輸入

    Returns:
        是否需要任務規劃
    """
    planning_keywords = [
        r'實作.*功能',
        r'開發.*系統',
        r'建立.*專案',
        r'寫.*程式',
        r'幫我.*做',
        r'如何實現',
        r'步驟.*完成',
        r'規劃.*任務',
        r'設計.*架構',
        r'create.*feature',
        r'develop.*system',
        r'build.*project',
        r'implement.*function',
    ]

    for pattern in planning_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            # 排除簡單問題（只是詢問不需要實作）
            if not re.search(r'^(什麼|為何|why|what|how\s+to)', user_input, re.IGNORECASE):
                return True

    return False


def detect_web_search_intent(user_input: str) -> bool:
    """
    檢測是否需要網頁搜尋功能

    觸發條件：
    - 詢問最新資訊、新聞、趨勢
    - 詢問外部知識（非純程式碼問題）
    - 需要即時數據

    Args:
        user_input: 使用者輸入

    Returns:
        是否需要網頁搜尋
    """
    search_keywords = [
        r'最新.*版本',
        r'最新.*消息',
        r'最近.*發生',
        r'現在.*趨勢',
        r'查詢.*資料',
        r'搜尋.*資訊',
        r'目前.*狀況',
        r'latest.*version',
        r'recent.*news',
        r'current.*trend',
        r'search.*for',
        r'find.*information',
    ]

    for pattern in search_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            return True

    # 如果包含年份且是近期（可能需要最新資訊）
    current_year = 2025
    if re.search(rf'{current_year - 1}|{current_year}', user_input):
        return True

    return False


def detect_code_analysis_intent(file_path: str) -> bool:
    """
    檢測是否需要程式碼分析功能

    觸發條件：
    - 附加的是程式碼檔案

    Args:
        file_path: 檔案路徑

    Returns:
        是否需要程式碼分析
    """
    code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go',
                       '.rs', '.cpp', '.c', '.h', '.rb', '.php'}

    ext = Path(file_path).suffix.lower()
    return ext in code_extensions


def detect_batch_processing_intent(user_input: str) -> bool:
    """
    檢測是否需要批次處理功能

    觸發條件：
    - 涉及多個檔案處理
    - 長時間運行的任務

    Args:
        user_input: 使用者輸入

    Returns:
        是否需要批次處理
    """
    batch_keywords = [
        r'批次.*處理',
        r'多個.*檔案',
        r'所有.*檔案',
        r'整個.*資料夾',
        r'batch.*process',
        r'multiple.*files',
        r'all.*files',
    ]

    for pattern in batch_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            return True

    return False


# ==========================================
# CodeGemini 功能觸發器
# ==========================================

def trigger_task_planning(user_input: str, api_key: str) -> Optional[tuple]:
    """
    觸發任務規劃功能

    Args:
        user_input: 使用者輸入
        api_key: API 金鑰

    Returns:
        (任務分析結果, token使用量) 如果成功，否則 None
        token使用量格式: {'api_input': int, 'api_output': int, 'model': str}
    """
    try:
        from CodeGemini.core.task_planner import TaskPlanner

        planner = TaskPlanner(api_key=api_key)
        logger.info("🔄 自動觸發任務規劃...")

        analysis = planner.analyze_request(user_input)

        if analysis:
            logger.info(f"✓ 任務規劃完成：{analysis.get('task_type', 'unknown')}")

            # 估算 token 使用量
            # TaskPlanner 通常使用 Flash 模型，估算：
            # - 輸入：user_input + system prompt ≈ len(user_input)//3 + 200
            # - 輸出：JSON 格式任務分析 ≈ 500-1000 tokens
            estimated_input = len(user_input) // 3 + 200
            estimated_output = 800  # 平均估算

            token_usage = {
                'api_input': estimated_input,
                'api_output': estimated_output,
                'model': 'gemini-2.5-flash'  # TaskPlanner 預設使用的模型
            }

            return analysis, token_usage

    except Exception as e:
        logger.debug(f"任務規劃觸發失敗: {e}")

    return None


def trigger_web_search(user_input: str) -> Optional[List[Dict[str, str]]]:
    """
    觸發網頁搜尋功能

    Args:
        user_input: 使用者輸入

    Returns:
        搜尋結果列表
    """
    try:
        from CodeGemini.tools.web_search import web_search

        # 提取搜尋關鍵字（簡化版）
        query = extract_search_query(user_input)

        logger.info(f"🔍 自動觸發網頁搜尋：{query}")

        results = web_search(query, max_results=3)

        if results:
            logger.info(f"✓ 找到 {len(results)} 筆搜尋結果")
            return results

    except Exception as e:
        logger.debug(f"網頁搜尋觸發失敗: {e}")

    return None


def trigger_code_analysis(file_path: str) -> Optional[Dict[str, Any]]:
    """
    觸發程式碼分析功能

    Args:
        file_path: 程式碼檔案路徑

    Returns:
        程式碼分析結果
    """
    try:
        from CodeGemini.context.scanner import CodeScanner

        scanner = CodeScanner()
        logger.info(f"🔬 自動分析程式碼：{file_path}")

        analysis = scanner.scan_file(file_path)

        if analysis:
            logger.info("✓ 程式碼分析完成")
            return analysis

    except Exception as e:
        logger.debug(f"程式碼分析觸發失敗: {e}")

    return None


# ==========================================
# Context 增強函數
# ==========================================

def enhance_prompt_with_task_plan(
    user_input: str,
    task_analysis: Dict[str, Any]
) -> str:
    """
    將任務規劃結果整合到 prompt 中

    Args:
        user_input: 原始使用者輸入
        task_analysis: 任務分析結果

    Returns:
        增強後的 prompt
    """
    if not task_analysis:
        return user_input

    # 提取關鍵資訊
    task_type = task_analysis.get('task_type', '未知')
    complexity = task_analysis.get('complexity', '中等')
    steps = task_analysis.get('steps', [])

    # 構建增強內容
    enhancement = "\n\n[系統分析]\n"
    enhancement += f"任務類型：{task_type}\n"
    enhancement += f"複雜度：{complexity}\n"

    if steps:
        enhancement += "建議步驟：\n"
        for i, step in enumerate(steps, 1):
            enhancement += f"{i}. {step}\n"

    return user_input + enhancement


def enhance_prompt_with_search_results(
    user_input: str,
    search_results: List[Dict[str, str]]
) -> str:
    """
    將網頁搜尋結果整合到 prompt 中

    Args:
        user_input: 原始使用者輸入
        search_results: 搜尋結果列表

    Returns:
        增強後的 prompt
    """
    if not search_results:
        return user_input

    # 構建增強內容
    enhancement = "\n\n[網路參考資料]\n"

    for i, result in enumerate(search_results, 1):
        title = result.get('title', '無標題')
        snippet = result.get('snippet', '')
        url = result.get('url', '')

        enhancement += f"\n來源 {i}：{title}\n"
        if snippet:
            enhancement += f"摘要：{snippet}\n"
        if url:
            enhancement += f"連結：{url}\n"

    enhancement += "\n請參考以上資料回答問題。"

    return user_input + enhancement


def enhance_prompt_with_code_analysis(
    user_input: str,
    code_analysis: Dict[str, Any],
    file_path: str
) -> str:
    """
    將程式碼分析結果整合到 prompt 中

    Args:
        user_input: 原始使用者輸入
        code_analysis: 程式碼分析結果
        file_path: 檔案路徑

    Returns:
        增強後的 prompt
    """
    if not code_analysis:
        return user_input

    # 構建增強內容
    enhancement = f"\n\n[程式碼分析：{Path(file_path).name}]\n"

    functions = code_analysis.get('functions', [])
    classes = code_analysis.get('classes', [])
    imports = code_analysis.get('imports', [])

    if classes:
        enhancement += f"類別數量：{len(classes)}\n"
        enhancement += f"主要類別：{', '.join(classes[:3])}\n"

    if functions:
        enhancement += f"函數數量：{len(functions)}\n"
        enhancement += f"主要函數：{', '.join(functions[:5])}\n"

    if imports:
        enhancement += f"依賴模組：{', '.join(imports[:5])}\n"

    return user_input + enhancement


# ==========================================
# 輔助函數
# ==========================================

def extract_search_query(user_input: str) -> str:
    """
    從使用者輸入中提取搜尋關鍵字

    Args:
        user_input: 使用者輸入

    Returns:
        搜尋關鍵字
    """
    # 移除常見的問句開頭
    query = re.sub(r'^(請問|想問|請教|幫我|what|how|can\s+you)\s*', '', user_input, flags=re.IGNORECASE)

    # 移除標點符號
    query = re.sub(r'[？?！!。.]', '', query)

    # 限制長度
    if len(query) > 100:
        query = query[:100]

    return query.strip()


# ==========================================
# 統一觸發介面
# ==========================================

def auto_enhance_prompt(
    user_input: str,
    api_key: Optional[str] = None,
    uploaded_files: Optional[List] = None,
    enable_task_planning: bool = True,
    enable_web_search: bool = True,
    enable_code_analysis: bool = True
) -> tuple:
    """
    自動檢測並增強 prompt（統一入口）

    此函數會：
    1. 檢測使用者意圖
    2. 觸發相應的 CodeGemini 功能
    3. 將結果整合到 prompt 中
    4. 返回增強後的 prompt 和 token 使用量

    Args:
        user_input: 原始使用者輸入
        api_key: API 金鑰（用於任務規劃）
        uploaded_files: 上傳的檔案列表
        enable_task_planning: 是否啟用任務規劃
        enable_web_search: 是否啟用網頁搜尋
        enable_code_analysis: 是否啟用程式碼分析

    Returns:
        (增強後的 prompt, token使用量統計)
        token使用量格式: {'api_input': int, 'api_output': int, 'model': str}
    """
    enhanced_input = user_input
    total_hidden_tokens = {
        'api_input': 0,
        'api_output': 0,
        'model': None
    }

    # 1. 任務規劃
    if enable_task_planning and api_key and detect_task_planning_intent(user_input):
        result = trigger_task_planning(user_input, api_key)
        if result:
            task_analysis, token_usage = result
            enhanced_input = enhance_prompt_with_task_plan(enhanced_input, task_analysis)

            # 累加 token 使用量
            total_hidden_tokens['api_input'] += token_usage['api_input']
            total_hidden_tokens['api_output'] += token_usage['api_output']
            if not total_hidden_tokens['model']:
                total_hidden_tokens['model'] = token_usage['model']

    # 2. 網頁搜尋（目前無額外 API 呼叫，僅添加文字）
    if enable_web_search and detect_web_search_intent(user_input):
        search_results = trigger_web_search(user_input)
        if search_results:
            enhanced_input = enhance_prompt_with_search_results(enhanced_input, search_results)
            # web_search 本身不呼叫 Gemini API，無額外 token 成本

    # 3. 程式碼分析（本地分析，無額外 API 成本）
    if enable_code_analysis and uploaded_files:
        for file_obj in uploaded_files:
            # 假設 file_obj 有 name 或 path 屬性
            file_path = getattr(file_obj, 'name', None) or getattr(file_obj, 'path', None)

            if file_path and detect_code_analysis_intent(file_path):
                code_analysis = trigger_code_analysis(file_path)
                if code_analysis:
                    enhanced_input = enhance_prompt_with_code_analysis(
                        enhanced_input, code_analysis, file_path
                    )
                    # CodeScanner 是本地分析，無額外 token 成本

    # 如果 prompt 有被增強，記錄日誌
    if enhanced_input != user_input:
        logger.info("✨ Prompt 已自動增強")
        if total_hidden_tokens['api_input'] > 0 or total_hidden_tokens['api_output'] > 0:
            logger.info(f"💰 智能觸發器額外用量：輸入 {total_hidden_tokens['api_input']} tokens, "
                       f"輸出 {total_hidden_tokens['api_output']} tokens "
                       f"(模型: {total_hidden_tokens['model']})")

    return enhanced_input, total_hidden_tokens


# ==========================================
# 待辦事項追蹤器（背景功能）
# ==========================================

class BackgroundTodoTracker:
    """
    背景待辦事項追蹤器

    此類別在對話過程中靜默運行，自動追蹤：
    - 提到的任務
    - 待完成的工作
    - 討論的問題

    不會顯示任何 UI，僅在後台記錄
    """

    def __init__(self):
        self.tracker = None
        self.enabled = False
        self._initialize()

    def _initialize(self):
        """初始化 TodoTracker"""
        try:
            from CodeGemini.modes.todo_tracker import TodoTracker
            self.tracker = TodoTracker()
            self.enabled = True
            logger.debug("✓ BackgroundTodoTracker 已初始化")
        except Exception as e:
            logger.debug(f"BackgroundTodoTracker 初始化失敗: {e}")
            self.enabled = False

    def update_from_conversation(self, user_input: str, assistant_response: str):
        """
        從對話中更新待辦事項

        Args:
            user_input: 使用者輸入
            assistant_response: 助手回應
        """
        if not self.enabled:
            return

        try:
            # 檢測待辦事項相關的語句
            todo_patterns = [
                r'需要.*完成',
                r'待.*處理',
                r'要.*實作',
                r'必須.*做',
                r'記得.*要',
                r'todo:?\s*(.+)',
                r'TODO:?\s*(.+)',
            ]

            for pattern in todo_patterns:
                matches = re.findall(pattern, user_input + " " + assistant_response, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, str) and len(match) > 5:
                        self.tracker.add_todo(match.strip())
                        logger.debug(f"📝 自動記錄待辦：{match.strip()[:50]}...")

        except Exception as e:
            logger.debug(f"更新待辦事項失敗: {e}")

    def get_summary(self) -> Optional[str]:
        """
        獲取待辦事項摘要

        Returns:
            待辦事項摘要（如果有）
        """
        if not self.enabled or not self.tracker:
            return None

        try:
            return self.tracker.get_summary()
        except Exception:
            return None
