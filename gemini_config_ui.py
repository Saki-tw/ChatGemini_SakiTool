#!/usr/bin/env python3
"""
Gemini 互動式配置 UI
從 gemini_chat.py 抽離
"""

from pathlib import Path
from typing import Dict
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

# 從 gemini_chat.py 導入必要的常量
RECOMMENDED_MODELS = {
    "1": ("gemini-2.5-pro", "最強大模型，適合複雜任務"),
    "2": ("gemini-2.5-flash", "推薦：平衡速度與品質"),
    "3": ("gemini-2.5-flash-8b", "最快速，適合簡單任務"),
    "4": ("gemini-2.0-flash-exp", "實驗版本，免費但不穩定"),
}

# ==========================================
# 互動式配置 UI 類別（v2.1 新增）
# ==========================================
class ConfigUI:
    """
    互動式配置 UI
    提供友善的配置引導介面，降低新使用者配置門檻

    功能：
    - 模型選擇（使用 Rich Prompt）
    - 模組啟用/停用（計價、快取、翻譯等）
    - 自動生成 config.py 檔案
    - 配置預覽與確認
    """

    def __init__(self):
        self.console = Console()
        self.config_path = Path(__file__).parent / "config.py"

    def interactive_setup(self) -> Dict:
        """
        啟動互動式配置流程

        Returns:
            配置字典
        """
        self.console.print(Panel(
            "[bold magenta]🎛️  歡迎使用 ChatGemini 互動式配置[/bold magenta]\n\n"
            "[dim]此工具將引導您完成初始配置，讓您快速開始使用。\n"
            "您可以隨時修改 config.py 來調整這些設定。[/dim]",
            title="[bold magenta]互動式配置精靈[/bold magenta]",
            border_style="magenta"
        ))

        # 提供最佳預設值，避免多餘互動
        config_dict = {}

        # ========================================
        # 步驟 1：模型選擇（必要，涉及費用）
        # ========================================
        config_dict['DEFAULT_MODEL'] = self._prompt_model_selection()

        # ========================================
        # 步驟 2：詢問是否需要調整進階設定
        # ========================================
        self.console.print("\n" + "─" * 60)
        self.console.print("[bold magenta]進階設定（可選）[/bold magenta]")
        self.console.print("[dim]包含：模組啟用/停用、匯率、快取門檻等參數[/dim]\n")

        customize = self.console.input(
            "[bold yellow]是否需要調整進階設定？[/bold yellow] y/[bright_magenta]N[/green] [dim](直接按 Enter 使用最佳預設值)[/dim]: "
        ).strip().lower()

        if customize in ['y', 'yes', '是', '1']:
            # 使用者選擇調整
            config_dict['MODULES'] = self._prompt_module_toggles()
            config_dict.update(self._prompt_advanced_settings())
        else:
            # 使用者跳過，使用最佳預設值
            self.console.print("[bright_magenta]✓ 使用最佳預設值[/green]\n")
            config_dict['MODULES'] = self._get_default_modules()
            config_dict.update(self._get_default_advanced_settings())

        # ========================================
        # 顯示預覽並生成
        # ========================================
        self._display_config_preview(config_dict)
        self._generate_config_file(config_dict)

        return config_dict

    def _get_default_modules(self) -> Dict:
        """
        返回推薦的預設模組配置（核心模組全開，實驗性模組關閉）
        """
        return {
            'pricing': {'enabled': True},
            'cache_manager': {'enabled': True},
            'file_manager': {'enabled': True},
            'translator': {'enabled': True},
            'flow_engine': {'enabled': False},
            'video_preprocessor': {'enabled': False},
            'video_compositor': {'enabled': False},
        }

    def _get_default_advanced_settings(self) -> Dict:
        """
        返回推薦的預設進階設定
        """
        return {
            'USD_TO_TWD': 31.0,
            'AUTO_CACHE_THRESHOLD': 5000,
            'CACHE_TTL_HOURS': 1,
            'TRANSLATION_ON_STARTUP': True,
        }

    def _prompt_model_selection(self) -> str:
        """
        互動式模型選擇

        Returns:
            選擇的模型名稱
        """
        from rich.table import Table

        self.console.print("\n[bold magenta]步驟 1: 選擇預設模型（涉及費用，請確認）[/bold magenta]")

        # 建立模型比較表
        table = Table(title="可用的 Gemini 模型", show_header=True, header_style="bold magenta")
        console_width = self.console.width or 120
        table.add_column("選項", style="magenta", width=max(6, int(console_width * 0.05)))
        table.add_column("模型名稱", style="green", width=max(22, int(console_width * 0.30)))
        table.add_column("描述", style="white", width=max(30, int(console_width * 0.45)))

        for key, (model_name, description) in RECOMMENDED_MODELS.items():
            table.add_row(key, model_name, description)

        self.console.print(table)

        # 使用 Rich Prompt 選擇
        while True:
            choice = self.console.input("\n[bold magenta]請選擇模型 (1-4)[/bold magenta] [dim][預設: 2][/dim]: ").strip()

            if not choice:
                choice = '2'  # 預設選擇 gemini-2.5-flash

            if choice in RECOMMENDED_MODELS:
                model_name, description = RECOMMENDED_MODELS[choice]
                self.console.print(f"[bright_magenta]✓ 已選擇: {model_name}[/green]")
                return model_name
            else:
                self.console.print("[dim magenta]❌ 無效的選項，請輸入 1-4[/red]")

    def _prompt_module_toggles(self) -> Dict:
        """
        互動式功能模組啟用/停用

        Returns:
            模組配置字典
        """
        from rich.table import Table

        self.console.print("\n[bold magenta]模組配置[/bold magenta]")
        self.console.print("[dim]按 Enter 接受預設值，輸入 y/n 來啟用/停用[/dim]\n")

        modules_config = {}

        # 定義模組列表（名稱、說明、預設值）
        module_options = [
            ('pricing', '💰 計價系統 - 顯示 API 使用費用', True),
            ('cache_manager', '🗄️  快取管理 - 自動管理上下文快取', True),
            ('file_manager', '📁 檔案管理 - 支援檔案上傳與管理', True),
            ('translator', '🌐 翻譯功能 - 自動翻譯思考過程', True),
            ('flow_engine', '🔄 流程引擎 - 多步驟任務處理（實驗性）', False),
            ('video_preprocessor', '🎬 影片前處理 - 影片分析前處理（實驗性）', False),
            ('video_compositor', '🎞️  影片合成器 - 影片編輯功能（實驗性）', False),
        ]

        for module_name, description, default in module_options:
            default_text = "[bright_magenta]Y[/green]/n" if default else "y/[dim magenta]N[/red]"
            user_input = self.console.input(
                f"  {description} [{default_text}]: "
            ).strip().lower()

            # 處理輸入
            if not user_input:
                enabled = default
            elif user_input in ['y', 'yes', '是', '1']:
                enabled = True
            elif user_input in ['n', 'no', '否', '0']:
                enabled = False
            else:
                self.console.print(f"    [magenta]⚠️  無效輸入，使用預設值: {'啟用' if default else '停用'}[/yellow]")
                enabled = default

            modules_config[module_name] = {'enabled': enabled}
            status_icon = "✅" if enabled else "❌"
            self.console.print(f"    {status_icon} {module_name}: {'啟用' if enabled else '停用'}")

        return modules_config

    def _prompt_advanced_settings(self) -> Dict:
        """
        進階設定（匯率、快取門檻等）

        Returns:
            進階配置字典
        """
        self.console.print("\n[bold magenta]進階參數[/bold magenta]")
        self.console.print("[dim]一般使用者可直接按 Enter 使用預設值[/dim]\n")

        config = {}

        # USD 匯率
        usd_input = self.console.input(
            "  💱 美元匯率 (USD to TWD) [dim][預設: 31.0][/dim]: "
        ).strip()
        config['USD_TO_TWD'] = float(usd_input) if usd_input else 31.0

        # 自動快取門檻
        cache_input = self.console.input(
            "  🗄️  自動快取門檻 (tokens) [dim][預設: 5000][/dim]: "
        ).strip()
        config['AUTO_CACHE_THRESHOLD'] = int(cache_input) if cache_input else 5000

        # 快取有效期
        ttl_input = self.console.input(
            "  ⏱️  快取有效期 (小時) [dim][預設: 1][/dim]: "
        ).strip()
        config['CACHE_TTL_HOURS'] = int(ttl_input) if ttl_input else 1

        # 啟動時翻譯
        trans_input = self.console.input(
            "  🌐 啟動時啟用翻譯功能 [bright_magenta]Y[/green]/n: "
        ).strip().lower()
        config['TRANSLATION_ON_STARTUP'] = trans_input not in ['n', 'no', '否', '0']

        self.console.print("\n[bright_magenta]✓ 進階設定完成[/green]")

        return config

    def _display_config_preview(self, config_dict: Dict):
        """
        顯示配置預覽

        Args:
            config_dict: 配置字典
        """
        from rich.table import Table

        self.console.print("\n[bold magenta]配置預覽[/bold magenta]")

        table = Table(show_header=True, header_style="bold magenta")
        console_width = self.console.width or 120
        table.add_column("設定項目", style="magenta", width=max(25, int(console_width * 0.30)))
        table.add_column("數值", style="green")

        # 基本設定
        table.add_row("預設模型", config_dict.get('DEFAULT_MODEL', 'N/A'))
        table.add_row("美元匯率", f"{config_dict.get('USD_TO_TWD', 31.0):.2f}")
        table.add_row("自動快取門檻", f"{config_dict.get('AUTO_CACHE_THRESHOLD', 5000):,} tokens")
        table.add_row("快取有效期", f"{config_dict.get('CACHE_TTL_HOURS', 1)} 小時")
        table.add_row("啟動時翻譯", "✅" if config_dict.get('TRANSLATION_ON_STARTUP', True) else "❌")

        self.console.print(table)

        # 模組狀態
        modules_table = Table(title="功能模組", show_header=True, header_style="bold magenta")
        console_width = self.console.width or 120
        modules_table.add_column("模組名稱", style="magenta", width=max(22, int(console_width * 0.30)))
        modules_table.add_column("狀態", style="green", width=max(10, int(console_width * 0.10)))

        for module_name, module_config in config_dict.get('MODULES', {}).items():
            status = "✅ 啟用" if module_config.get('enabled', False) else "❌ 停用"
            modules_table.add_row(module_name, status)

        self.console.print(modules_table)

    def _generate_config_file(self, config_dict: Dict):
        """
        生成 config.py 檔案

        Args:
            config_dict: 配置字典
        """
        config_content = f'''"""
ChatGemini_SakiTool 配置檔案
由互動式配置精靈自動生成於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

# ==========================================
# 基本配置
# ==========================================

# 預設模型
DEFAULT_MODEL = '{config_dict.get('DEFAULT_MODEL', 'gemini-2.5-flash')}'

# 美元匯率（USD to TWD）
USD_TO_TWD = {config_dict.get('USD_TO_TWD', 31.0)}

# ==========================================
# 功能模組配置
# ==========================================

MODULES = {{
'''

        # 添加模組配置
        for module_name, module_config in config_dict.get('MODULES', {}).items():
            enabled = module_config.get('enabled', False)
            config_content += f"    '{module_name}': {{'enabled': {enabled}}},\n"

        config_content += f'''}}

# ==========================================
# 快取配置
# ==========================================

# 自動快取啟用
AUTO_CACHE_ENABLED = True

# 自動快取門檻（tokens）
AUTO_CACHE_THRESHOLD = {config_dict.get('AUTO_CACHE_THRESHOLD', 5000)}

# 快取有效期（小時）
CACHE_TTL_HOURS = {config_dict.get('CACHE_TTL_HOURS', 1)}

# ==========================================
# 翻譯配置
# ==========================================

# 啟動時啟用翻譯
TRANSLATION_ON_STARTUP = {config_dict.get('TRANSLATION_ON_STARTUP', True)}

# 預設顯示思考過程（由 Ctrl+T 即時切換，不需配置）
SHOW_THINKING_PROCESS = False

# ==========================================
# Codebase Embedding 配置
# ==========================================

# 啟動時自動啟用 Codebase Embedding
EMBEDDING_ENABLE_ON_STARTUP = False

# 向量資料庫路徑
EMBEDDING_VECTOR_DB_PATH = "./codebase_vectors"
'''

        # 寫入檔案
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)

            self.console.print(f"\n[bold green]✅ 配置檔案已成功建立：{self.config_path}[/bold green]")
            self.console.print("[dim]您可以隨時編輯此檔案來調整配置[/dim]\n")
        except Exception as e:
            self.console.print(f"\n[bold red]❌ 建立配置檔案失敗：{e}[/bold red]")
            self.console.print("[magenta]⚠️  將使用預設配置繼續執行[/yellow]\n")

# 各模型的最低快取門檻要求（tokens）
# 根據 Gemini API Context Caching 規範
MIN_TOKENS = {
    'gemini-2.5-pro': 4096,           # Pro 版本需要更多
    'gemini-2.5-flash': 1024,         # Flash 版本標準
    'gemini-2.5-flash-8b': 1024,      # Flash-8B 版本標準
    'gemini-2.0-flash-exp': 32768,    # 2.0 實驗版需要較多
    'gemini-2.0-flash': 32768,        # 2.0 標準版
}

# 初始化 prompt_toolkit 歷史記錄
if PROMPT_TOOLKIT_AVAILABLE:
    input_history = InMemoryHistory()

    # 增強的自動補全器
    class SmartCompleter(Completer):
        """智能自動補全器：支援指令、語法、檔案路徑"""
        def __init__(self):
            self.commands = ['cache', 'media', 'video', 'veo', 'model', 'clear', 'exit', 'help', 'debug', 'test']
            if CODEGEMINI_ENABLED:
                self.commands.extend(['cli', 'gemini-cli'])
            if CODEBASE_EMBEDDING_ENABLED:
                self.commands.extend(['/search_code', '/search_history'])

            # 思考模式語法提示
            self.think_patterns = [
                '[think:auto]',
                '[think:1000]',
                '[think:2000]',
                '[think:5000]',
                '[think:1000,response:500]',
                '[no-think]'
            ]

        def get_completions(self, document, complete_event):
            word = document.get_word_before_cursor()
            text = document.text_before_cursor

            # 1. 思考模式語法補全
            if '[think' in text.lower() or word.startswith('['):
                for pattern in self.think_patterns:
                    if pattern.lower().startswith(word.lower()):
                        yield Completion(
                            pattern,
                            start_position=-len(word),
                            display_meta='思考模式語法'
                        )

            # 2. 指令補全
            elif not text or text.isspace() or (len(text) < 10 and not any(c in text for c in '[/@')):
                for cmd in self.commands:
                    if cmd.lower().startswith(word.lower()):
                        yield Completion(
                            cmd,
                            start_position=-len(word),
                            display_meta='指令'
                        )

    command_completer = SmartCompleter()

    # 創建輸入樣式（馬卡龍紫色系）
    input_style = Style.from_dict({
        'prompt': '#b19cd9 bold',  # 馬卡龍薰衣草紫
        'multiline': '#c8b1e4 italic',  # 淡紫色
    })

    # 創建按鍵綁定
    key_bindings = KeyBindings()

    @key_bindings.add('c-t')
    def toggle_thinking_display(event):
        """Ctrl+T: 切換思考過程顯示（循環：隱藏 → 翻譯 → 雙語對照）"""
        global SHOW_THINKING_PROCESS, LAST_THINKING_PROCESS, LAST_THINKING_TRANSLATED, CTRL_T_PRESS_COUNT

        # 沒有思考過程時提示
        if not LAST_THINKING_PROCESS:
            console.print("\n[magenta]💭 尚未產生思考過程[/magenta]\n")
            event.app.current_buffer.insert_text("")
            return

        # 循環切換：0(隱藏) → 1(翻譯) → 2(雙語) → 0
        CTRL_T_PRESS_COUNT = (CTRL_T_PRESS_COUNT + 1) % 3

        if CTRL_T_PRESS_COUNT == 1:
            # 第一次按下：顯示翻譯（或原文）
            SHOW_THINKING_PROCESS = True
            console.print("\n[bright_magenta]━━━ 🧠 思考過程（翻譯） ━━━[/bright_magenta]")

            # 如果有翻譯且翻譯功能啟用，顯示翻譯；否則顯示原文
            if TRANSLATOR_ENABLED and global_translator and LAST_THINKING_TRANSLATED:
                console.print(f"[dim]{LAST_THINKING_TRANSLATED}[/dim]")
            else:
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
                if TRANSLATOR_ENABLED and global_translator:
                    console.print("[dim magenta]💡 提示：翻譯功能可能未啟用或無可用引擎[/dim magenta]")

            console.print("[bright_magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━[/bright_magenta]\n")

        elif CTRL_T_PRESS_COUNT == 2:
            # 第二次按下：顯示雙語對照
            console.print("\n[bright_magenta]━━━ 🧠 思考過程（雙語對照） ━━━[/bright_magenta]")

            if TRANSLATOR_ENABLED and global_translator and LAST_THINKING_TRANSLATED:
                console.print("[bold bright_magenta]🇹🇼 繁體中文：[/bold bright_magenta]")
                console.print(f"[dim]{LAST_THINKING_TRANSLATED}[/dim]\n")
                console.print("[bold bright_magenta]🇬🇧 英文原文：[/bold bright_magenta]")
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
            else:
                console.print("[bold bright_magenta]🇬🇧 英文原文：[/bold bright_magenta]")
                console.print(f"[dim]{LAST_THINKING_PROCESS}[/dim]")
                if TRANSLATOR_ENABLED and global_translator:
                    console.print("[dim magenta]💡 提示：翻譯功能可能未啟用或無可用引擎[/dim magenta]")

            console.print("[bright_magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━[/bright_magenta]\n")

        else:
            # 第三次按下：隱藏
            SHOW_THINKING_PROCESS = False
            console.print("\n[magenta]💭 思考過程已隱藏[/magenta]\n")

        event.app.current_buffer.insert_text("")  # 保持輸入狀態

    @key_bindings.add('escape', 'enter')
    def insert_newline(event):
        """Alt+Enter: 插入新行（多行編輯）"""
        event.app.current_buffer.insert_text('\n')

    @key_bindings.add('c-d')
    def show_help_hint(event):
        """Ctrl+D: 顯示輸入提示"""
        console.print("\n[bright_magenta]💡 輸入提示：[/bright_magenta]")
        console.print("  • [bold]Alt+Enter[/bold] - 插入新行（多行輸入）")
        console.print("  • [bold]Ctrl+T[/bold] - 切換思考過程顯示")
        console.print("  • [bold]↑/↓[/bold] - 瀏覽歷史記錄")
        console.print("  • [bold]Tab[/bold] - 自動補全指令與語法")
        console.print("  • [bold][think:1000,response:500][/bold] - 指定思考與回應 tokens")
        console.print()
        event.app.current_buffer.insert_text("")


def extract_thinking_process(response) -> Optional[str]:
    """
    從回應中提取思考過程內容

    Args:
        response: Gemini API 回應物件

    Returns:
        思考過程文字，如果不存在則回傳 None
    """
    try:
        if not hasattr(response, 'candidates') or not response.candidates:
            return None

        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
            return None

        # 遍歷所有 parts，查找思考內容
        thinking_parts = []
        for part in candidate.content.parts:
            # 檢查是否有 thought 或 thinking 欄位
            if hasattr(part, 'thought'):
                thinking_parts.append(part.thought)
            elif hasattr(part, 'thinking'):
                thinking_parts.append(part.thinking)
            # 有些實作可能用不同的欄位名
            elif hasattr(part, 'reasoning'):
                thinking_parts.append(part.reasoning)

        if thinking_parts:
            return '\n'.join(thinking_parts)

        return None
    except Exception as e:
        logger.warning(f"提取思考過程失敗: {e}")
        return None


def parse_thinking_config(user_input: str, model_name: str = "") -> tuple:
    """
    解析思考模式配置

    支援格式:
    - [think:2000] 使用指定 tokens 思考
    - [think:1000,response:500] 同時指定思考與回應 tokens
    - [think:auto] 或 [think:-1] 動態思考
    - [no-think] 或 [think:0] 不思考（部分模型支援）

    各模型限制：
    - gemini-2.5-pro: -1 (動態) 或 128-32768 tokens，無法停用
    - gemini-2.5-flash: -1 (動態) 或 0-24576 tokens，0=停用
    - gemini-2.5-flash-8b (lite): -1 (動態) 或 512-24576 tokens，0=停用

    Args:
        user_input: 使用者輸入
        model_name: 模型名稱

    Returns:
        (清理後的輸入, 是否使用思考, 思考預算, 最大輸出tokens)
    """
    # 根據模型判斷限制
    is_pro = 'pro' in model_name.lower()
    is_lite = '8b' in model_name.lower() or 'lite' in model_name.lower()

    # 設定各模型的限制
    if is_pro:
        MAX_TOKENS = 32768
        MIN_TOKENS = 128
        ALLOW_DISABLE = False  # Pro 無法停用思考
    elif is_lite:
        MAX_TOKENS = 24576
        MIN_TOKENS = 512
        ALLOW_DISABLE = True
    else:  # flash
        MAX_TOKENS = 24576
        MIN_TOKENS = 0
        ALLOW_DISABLE = True

    # 預設值
    use_thinking = True
    thinking_budget = -1  # 動態
    max_output_tokens = None  # None 表示使用模型預設值

    # 檢查是否禁用思考
    no_think_pattern = r'\[no-think\]'
    if re.search(no_think_pattern, user_input, re.IGNORECASE):
        if not ALLOW_DISABLE:
            print(f"⚠️  {model_name} 不支援停用思考，將使用動態模式")
            thinking_budget = -1
        else:
            thinking_budget = 0
        user_input = re.sub(no_think_pattern, '', user_input, flags=re.IGNORECASE).strip()
        return user_input, use_thinking, thinking_budget, max_output_tokens

    # 檢查帶 response 參數的思考預算: [think:1000,response:500]
    think_response_pattern = r'\[think:(-?\d+|auto),\s*response:(\d+)\]'
    match = re.search(think_response_pattern, user_input, re.IGNORECASE)
    if match:
        budget_str = match.group(1).lower()
        response_tokens = int(match.group(2))

        # 處理思考預算
        if budget_str == 'auto':
            thinking_budget = -1
        else:
            thinking_budget = int(budget_str)

            # 驗證思考預算範圍
            if thinking_budget == 0:
                if not ALLOW_DISABLE:
                    print(f"⚠️  {model_name} 不支援停用思考（0 tokens），已調整為最小值 {MIN_TOKENS} tokens")
                    thinking_budget = MIN_TOKENS
            elif thinking_budget == -1:
                pass  # 保持 -1
            elif thinking_budget < MIN_TOKENS:
                print(f"⚠️  思考預算低於最小值 {MIN_TOKENS} tokens，已調整")
                thinking_budget = MIN_TOKENS
            elif thinking_budget > MAX_TOKENS:
                print(f"⚠️  思考預算超過上限 {MAX_TOKENS:,} tokens，已調整為最大值")
                thinking_budget = MAX_TOKENS

        # 設定輸出 tokens（最大 8192）
        if response_tokens < 1:
            print(f"⚠️  回應 tokens 至少為 1，已調整")
            max_output_tokens = 1
        elif response_tokens > 8192:
            print(f"⚠️  回應 tokens 超過上限 8192，已調整為最大值")
            max_output_tokens = 8192
        else:
            max_output_tokens = response_tokens

        user_input = re.sub(think_response_pattern, '', user_input, flags=re.IGNORECASE).strip()
        return user_input, use_thinking, thinking_budget, max_output_tokens

    # 檢查單獨的思考預算: [think:2000]
    think_pattern = r'\[think:(-?\d+|auto)\]'
    match = re.search(think_pattern, user_input, re.IGNORECASE)
    if match:
        budget_str = match.group(1).lower()
        if budget_str == 'auto':
            thinking_budget = -1
        else:
            thinking_budget = int(budget_str)

            # 處理停用請求 (0)
            if thinking_budget == 0:
                if not ALLOW_DISABLE:
                    print(f"⚠️  {model_name} 不支援停用思考（0 tokens），已調整為最小值 {MIN_TOKENS} tokens")
                    thinking_budget = MIN_TOKENS
                # else: thinking_budget = 0 保持不變
            # 處理動態請求 (-1)
            elif thinking_budget == -1:
                pass  # 保持 -1
            # 處理指定 tokens
            elif thinking_budget < MIN_TOKENS:
                print(f"⚠️  思考預算低於最小值 {MIN_TOKENS} tokens，已調整")
                thinking_budget = MIN_TOKENS
            elif thinking_budget > MAX_TOKENS:
                print(f"⚠️  思考預算超過上限 {MAX_TOKENS:,} tokens，已調整為最大值")
                thinking_budget = MAX_TOKENS

        user_input = re.sub(think_pattern, '', user_input, flags=re.IGNORECASE).strip()

    return user_input, use_thinking, thinking_budget, max_output_tokens


def process_file_attachments(user_input: str) -> tuple:
    """
    處理檔案附加（智慧判斷文字檔vs媒體檔）

    支援格式:
    - @/path/to/file.txt  （文字檔：直接讀取）
    - 附加 image.jpg      （圖片：上傳API）
    - 讀取 ~/code.py      （程式碼：直接讀取）
    - 上傳 video.mp4      （影片：上傳API）

    Args:
        user_input: 使用者輸入

    Returns:
        (處理後的輸入, 上傳的檔案物件列表)
    """
    # 偵測檔案路徑模式
    file_patterns = [
        r'@([^\s]+)',           # @file.txt
        r'附加\s+([^\s]+)',     # 附加 file.txt
        r'讀取\s+([^\s]+)',     # 讀取 file.txt
        r'上傳\s+([^\s]+)',     # 上傳 file.mp4
    ]

    # 文字檔副檔名（直接讀取）
    TEXT_EXTENSIONS = {'.txt', '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.xml',
                       '.html', '.css', '.md', '.yaml', '.yml', '.toml', '.ini',
                       '.sh', '.bash', '.zsh', '.c', '.cpp', '.h', '.java', '.go',
                       '.rs', '.php', '.rb', '.sql', '.log', '.csv', '.env'}

    # 媒體檔副檔名（上傳API）
    MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg',
                        '.mp4', '.mpeg', '.mov', '.avi', '.flv', '.webm', '.mkv',
                        '.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a',
                        '.pdf', '.doc', '.docx', '.ppt', '.pptx'}

    files_content = []
    uploaded_files = []

    for pattern in file_patterns:
        matches = re.findall(pattern, user_input)
        for file_path in matches:
            file_path = os.path.expanduser(file_path)

            if not os.path.isfile(file_path):
                # 使用錯誤修復建議系統
                if ERROR_FIX_ENABLED:
                    suggest_file_not_found(file_path)
                else:
                    print(f"⚠️  找不到檔案: {file_path}")
                continue

            # 判斷檔案類型
            ext = os.path.splitext(file_path)[1].lower()

            if ext in TEXT_EXTENSIONS:
                # 文字檔：直接讀取
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        files_content.append(f"\n\n[檔案: {file_path}]\n```{ext[1:]}\n{content}\n```\n")
                        print(f"✅ 已讀取文字檔: {file_path}")
                except UnicodeDecodeError:
                    # 嘗試其他編碼
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                            files_content.append(f"\n\n[檔案: {file_path}]\n```\n{content}\n```\n")
                            print(f"✅ 已讀取文字檔: {file_path} (latin-1)")
                    except Exception as e:
                        print(f"⚠️  無法讀取檔案 {file_path}: {e}")
                except Exception as e:
                    print(f"⚠️  無法讀取檔案 {file_path}: {e}")

            elif ext in MEDIA_EXTENSIONS:
                # 媒體檔：上傳 API
                if FILE_MANAGER_ENABLED:
                    try:
                        # 媒體查看器：上傳前顯示檔案資訊（自動整合）
                        if MEDIA_VIEWER_AUTO_ENABLED and global_media_viewer:
                            try:
                                global_media_viewer.show_file_info(file_path)
                            except Exception as e:
                                logger.debug(f"媒體查看器顯示失敗: {e}")

                        uploaded_file = global_file_manager.upload_file(file_path)
                        uploaded_files.append(uploaded_file)
                        print(f"✅ 已上傳媒體檔: {file_path}")
                    except Exception as e:
                        print(f"⚠️  上傳失敗 {file_path}: {e}")
                else:
                    print(f"⚠️  檔案管理器未啟用，無法上傳 {file_path}")

            else:
                # 未知類型：嘗試當文字檔讀取
                print(f"⚠️  未知檔案類型 {ext}，嘗試當文字檔讀取...")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        files_content.append(f"\n\n[檔案: {file_path}]\n```\n{content}\n```\n")
                        print(f"✅ 已讀取檔案: {file_path}")
                except Exception as e:
                    print(f"⚠️  無法處理檔案 {file_path}: {e}")

    # 移除檔案路徑標記
    for pattern in file_patterns:
        user_input = re.sub(pattern, '', user_input)

    # 將文字檔案內容添加到 prompt
    if files_content:
        user_input = user_input.strip() + "\n" + "\n".join(files_content)

    return user_input, uploaded_files


def get_user_input(prompt_text: str = "你: ") -> str:
    """
    獲取使用者輸入（支援 prompt_toolkit 增強功能）

    功能：
    - Alt+Enter: 多行編輯（插入新行）
    - Ctrl+T: 切換思考過程顯示
    - Ctrl+D: 顯示輸入提示
    - ↑/↓: 瀏覽歷史記錄
    - Tab: 自動補全指令與語法

    Args:
        prompt_text: 提示文字

    Returns:
        使用者輸入
    """
    if PROMPT_TOOLKIT_AVAILABLE:
        try:
            # 使用 HTML 格式化提示文字，支援顏色
            formatted_prompt = HTML(f'<ansimagenta><b>{prompt_text}</b></ansimagenta>')  # 馬卡龍紫色

            return prompt(
                formatted_prompt,
                history=input_history,
                auto_suggest=AutoSuggestFromHistory(),
                completer=command_completer,
                key_bindings=key_bindings,
                enable_suspend=True,  # 允許 Ctrl+Z 暫停
                mouse_support=False,  # 禁用滑鼠支援避免衝突
                multiline=False,  # 預設單行，使用 Alt+Enter 可插入新行
                prompt_continuation=lambda width, line_number, is_soft_wrap: '... ',  # 多行續行提示
                complete_while_typing=True,  # 打字時即時補全
                style=input_style,  # 應用自訂樣式
            ).strip()
        except (KeyboardInterrupt, EOFError):
            return ""
        except Exception as e:
            # 降級到標準 input()
            logger.debug(f"prompt_toolkit 錯誤，降級到標準 input(): {e}")
            try:
                return input(prompt_text).strip()
            except (KeyboardInterrupt, EOFError):
                return ""
    else:
        # 降級到標準 input()
        try:
            return input(prompt_text).strip()
        except (KeyboardInterrupt, EOFError):
            return ""
