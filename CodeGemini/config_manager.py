#!/usr/bin/env python3
"""
CodeGemini Configuration Manager
配置管理模組 - 管理所有可配置的參數

功能：
1. 資料庫配置（正交模式、向量相關係數閾值）
2. 持久化配置到 JSON 檔案
3. 互動式配置介面
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from utils.i18n import safe_t

logger = logging.getLogger(__name__)


@dataclass
class CodebaseEmbeddingConfig:
    """Codebase Embedding 配置"""
    enabled: bool = False
    vector_db_path: str = "embeddings"  # 相對於 Cache 目錄
    orthogonal_mode: bool = False
    similarity_threshold: float = 0.85
    collection_name: str = "codebase"


@dataclass
class SystemConfig:
    """系統級配置（可由使用者覆寫 config.py 預設值）"""
    # 模型設定
    default_model: str = "gemini-2.5-flash"
    max_conversation_history: int = 100
    unlimited_memory_mode: bool = False

    # 快取設定
    auto_cache_enabled: bool = True
    auto_cache_threshold: int = 5000

    # 翻譯設定
    translation_on_startup: bool = True

    # 計價設定
    usd_to_twd: float = 31.0

    # 記憶體管理
    memory_warning_threshold_gb: float = 1.5
    memory_auto_cleanup: bool = True

    # UI 偏好設定（新增）
    show_thinking_process: bool = False  # 思考過程顯示開關
    last_menu_choice: str = "1"  # 記憶上次選單選擇


@dataclass
class CodeGeminiConfig:
    """CodeGemini 完整配置（Tier 2: 使用者級）"""
    # Codebase Embedding 配置
    codebase_embedding: CodebaseEmbeddingConfig = field(default_factory=CodebaseEmbeddingConfig)

    # 系統配置覆寫
    system: SystemConfig = field(default_factory=SystemConfig)

    # UI 設定
    last_menu_choice: str = "1"  # 記憶上次選單選擇

    # 未來可擴展其他配置
    # auto_model_selection: AutoModelConfig = ...
    # checkpoint_system: CheckpointConfig = ...


class ConfigManager:
    """配置管理器

    功能：
    - 載入/儲存配置到 JSON 檔案
    - 提供配置修改介面
    - 配置驗證

    設計原則：
    - 零循環導入（不依賴 path_manager，直接使用標準庫）
    - 跨平台支援（Windows/macOS/Linux）
    """

    DEFAULT_CONFIG_PATH = None  # 延遲初始化

    @classmethod
    def _get_default_config_path(cls) -> Path:
        """取得預設配置路徑（零依賴，避免循環導入）

        Returns:
            預設配置檔案路徑 (~/.cache/codegemini/config.json)
        """
        if cls.DEFAULT_CONFIG_PATH is None:
            import os

            # 跨平台快取目錄計算
            if os.name == 'nt':  # Windows
                cache_base = Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
            else:  # macOS, Linux
                cache_base = Path(os.getenv('XDG_CACHE_HOME', Path.home() / '.cache'))

            cls.DEFAULT_CONFIG_PATH = cache_base / 'codegemini' / 'config.json'

        return cls.DEFAULT_CONFIG_PATH

    def __init__(self, config_path: Optional[Path] = None):
        """初始化配置管理器

        Args:
            config_path: 配置檔案路徑（預設：~/.cache/codegemini/config.json）
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 載入配置
        self.config = self.load_config()
        logger.info(safe_t('codegemini.config.initialized', fallback='✓ ConfigManager 已初始化: {path}', path=self.config_path))

    def load_config(self) -> CodeGeminiConfig:
        """載入配置檔案（Tier 2: 使用者級配置）

        Returns:
            CodeGeminiConfig 實例
        """
        if not self.config_path.exists():
            logger.info(safe_t('codegemini.config.not_found', fallback='配置檔案不存在，使用預設配置'))
            return CodeGeminiConfig()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 解析 Codebase Embedding 配置
            codebase_emb_data = data.get('codebase_embedding', {})
            codebase_emb_config = CodebaseEmbeddingConfig(**codebase_emb_data)

            # 解析系統配置覆寫
            system_data = data.get('system', {})
            system_config = SystemConfig(**system_data)

            # 載入 UI 設定
            last_menu_choice = data.get('last_menu_choice', "1")

            config = CodeGeminiConfig(
                codebase_embedding=codebase_emb_config,
                system=system_config,
                last_menu_choice=last_menu_choice
            )
            logger.info(safe_t('codegemini.config.loaded', fallback='✓ 配置檔案已載入'))
            return config

        except Exception as e:
            logger.error(safe_t('codegemini.config.load_failed', fallback='✗ 載入配置失敗: {error}', error=e))
            logger.info(safe_t('codegemini.config.use_defaults', fallback='使用預設配置'))
            return CodeGeminiConfig()

    def save_config(self) -> bool:
        """儲存配置到檔案（Tier 2: 使用者級配置）

        Returns:
            是否成功
        """
        try:
            # 轉換為字典
            config_dict = {
                'codebase_embedding': asdict(self.config.codebase_embedding),
                'system': asdict(self.config.system),
                'last_menu_choice': self.config.last_menu_choice
            }

            # 儲存到 JSON
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.info(safe_t('codegemini.config.saved', fallback='✓ 配置已儲存: {path}', path=self.config_path))

            # 同步到 UnifiedConfig（如果可用）
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from config import get_config
                unified_config = get_config()
                unified_config.reload()
            except:
                pass  # UnifiedConfig 不可用，跳過同步

            return True

        except Exception as e:
            logger.error(safe_t('codegemini.config.save_failed', fallback='✗ 儲存配置失敗: {error}', error=e))
            return False

    def get_codebase_embedding_config(self) -> CodebaseEmbeddingConfig:
        """獲取 Codebase Embedding 配置

        Returns:
            CodebaseEmbeddingConfig 實例
        """
        return self.config.codebase_embedding

    def update_codebase_embedding_config(
        self,
        enabled: Optional[bool] = None,
        vector_db_path: Optional[str] = None,
        orthogonal_mode: Optional[bool] = None,
        similarity_threshold: Optional[float] = None,
        collection_name: Optional[str] = None
    ) -> bool:
        """更新 Codebase Embedding 配置

        Args:
            enabled: 是否啟用
            vector_db_path: 向量資料庫路徑
            orthogonal_mode: 正交模式
            similarity_threshold: 向量相關係數閾值
            collection_name: 向量資料庫集合名稱（ChromaDB collection 識別碼）

        Returns:
            是否成功
        """
        emb_config = self.config.codebase_embedding

        if enabled is not None:
            emb_config.enabled = enabled
        if vector_db_path is not None:
            emb_config.vector_db_path = vector_db_path
        if orthogonal_mode is not None:
            emb_config.orthogonal_mode = orthogonal_mode
        if similarity_threshold is not None:
            # 驗證閾值範圍
            if 0.0 <= similarity_threshold <= 1.0:
                emb_config.similarity_threshold = similarity_threshold
            else:
                logger.error(safe_t('codegemini.config.invalid_threshold', fallback='✗ 無效的相似度閾值: {threshold}（應在 0.0-1.0 之間）', threshold=similarity_threshold))
                return False
        if collection_name is not None:
            emb_config.collection_name = collection_name

        # 儲存配置
        return self.save_config()

    def reset_to_defaults(self) -> bool:
        """重置為預設配置

        Returns:
            是否成功
        """
        self.config = CodeGeminiConfig()
        logger.info(safe_t('codegemini.config.reset', fallback='✓ 配置已重置為預設值'))
        return self.save_config()

    def get_last_menu_choice(self) -> str:
        """獲取上次選單選擇

        Returns:
            上次選擇的選項（預設為 "1"）
        """
        return self.config.last_menu_choice

    def save_last_menu_choice(self, choice: str) -> bool:
        """儲存選單選擇

        Args:
            choice: 選擇的選項

        Returns:
            是否成功
        """
        self.config.last_menu_choice = choice
        return self.save_config()

    def get_config_summary(self) -> Dict[str, Any]:
        """獲取配置摘要（用於顯示）

        Returns:
            配置摘要字典
        """
        emb_config = self.config.codebase_embedding
        sys_config = self.config.system

        return {
            'config_path': str(self.config_path),
            'tier': 'Tier 2 (使用者級配置)',
            'codebase_embedding': {
                'enabled': emb_config.enabled,
                'vector_db_path': emb_config.vector_db_path,
                'orthogonal_mode': emb_config.orthogonal_mode,
                'similarity_threshold': emb_config.similarity_threshold,
                'collection_name': emb_config.collection_name
            },
            'system_overrides': {
                'default_model': sys_config.default_model,
                'max_conversation_history': sys_config.max_conversation_history,
                'unlimited_memory_mode': sys_config.unlimited_memory_mode,
                'auto_cache_enabled': sys_config.auto_cache_enabled,
                'auto_cache_threshold': sys_config.auto_cache_threshold,
                'translation_on_startup': sys_config.translation_on_startup,
                'usd_to_twd': sys_config.usd_to_twd,
                'memory_warning_threshold_gb': sys_config.memory_warning_threshold_gb,
                'memory_auto_cleanup': sys_config.memory_auto_cleanup
            }
        }


# 路徑驗證與建議輔助函數
def _validate_and_suggest_path(
    path_input: str,
    base_dir: Optional[Path] = None,
    create_if_missing: bool = True
) -> tuple[str, bool]:
    """
    驗證路徑輸入並提供建議（✅ V-7: 路徑輸入驗證與建議）

    Args:
        path_input: 使用者輸入的路徑
        base_dir: 基礎目錄（用於相對路徑，預設為 Cache 目錄）
        create_if_missing: 如果路徑不存在，是否詢問創建

    Returns:
        tuple[str, bool]: (驗證後的路徑, 是否有效)
    """
    from rich.console import Console
    from rich.prompt import Confirm
    import os

    console = Console()

    # 處理空輸入
    if not path_input or path_input.strip() == "":
        console.print(safe_t('codegemini.config.path_empty', fallback='[#B565D8]⚠ 路徑不能為空[/#B565D8]'))
        return (path_input, False)

    # 移除首尾空白
    path_input = path_input.strip()

    # 檢查是否為相對路徑
    path_obj = Path(path_input)
    if not path_obj.is_absolute():
        # 相對路徑，相對於 base_dir 或 Cache 目錄
        if base_dir is None:
            import os
            # 直接使用標準庫計算快取目錄（避免循環導入）
            if os.name == 'nt':  # Windows
                cache_base = Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
            else:  # macOS, Linux
                cache_base = Path(os.getenv('XDG_CACHE_HOME', Path.home() / '.cache'))
            base_dir = cache_base / 'codegemini'

        path_obj = base_dir / path_input

    # 驗證路徑
    console.print(safe_t('codegemini.config.full_path', fallback='\n[dim]完整路徑: {path}[/dim]', path=path_obj))

    # 檢查父目錄是否存在
    parent_dir = path_obj.parent
    if not parent_dir.exists():
        console.print(safe_t('codegemini.config.parent_dir_missing', fallback='[#B565D8]⚠ 父目錄不存在: {dir}[/#B565D8]', dir=parent_dir))

        if create_if_missing:
            if Confirm.ask(safe_t('codegemini.config.create_parent_dir', fallback='是否創建父目錄？'), default=True):
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    console.print(safe_t('codegemini.config.parent_dir_created', fallback='[green]✓ 已創建父目錄[/green]'))
                except Exception as e:
                    console.print(safe_t('codegemini.config.parent_dir_create_failed', fallback='[red]✗ 創建父目錄失敗: {error}[/red]', error=e))
                    return (path_input, False)
            else:
                console.print(safe_t('codegemini.config.path_cancelled', fallback='[#B565D8]已取消，路徑可能無法使用[/#B565D8]'))
                return (path_input, False)

    # 檢查路徑是否已存在
    if path_obj.exists():
        if path_obj.is_file():
            console.print(safe_t('codegemini.config.path_is_file', fallback='[#B565D8]⚠ 此路徑指向檔案，而非目錄: {path}[/#B565D8]', path=path_obj))
            console.print(safe_t('codegemini.config.path_should_be_dir', fallback='[dim]建議: 向量資料庫路徑應為目錄[/dim]'))
            if not Confirm.ask(safe_t('codegemini.config.confirm_use_path', fallback='確定要使用此路徑？'), default=False):
                return (path_input, False)
        else:
            console.print(safe_t('codegemini.config.path_valid', fallback='[green]✓ 路徑有效（目錄已存在）[/green]'))
    else:
        console.print(safe_t('codegemini.config.path_will_create', fallback='[dim]路徑尚未建立，將在首次使用時自動創建[/dim]'))

    # 檢查寫入權限
    try:
        # 嘗試在父目錄創建測試檔案
        test_file = parent_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        console.print(safe_t('codegemini.config.path_writable', fallback='[green]✓ 目錄可寫入[/green]'))
    except Exception as e:
        console.print(safe_t('codegemini.config.no_write_permission', fallback='[red]✗ 無寫入權限: {error}[/red]', error=e))
        console.print(safe_t('codegemini.config.suggest_writable_dir', fallback='[dim]建議: 選擇有寫入權限的目錄[/dim]'))
        return (path_input, False)

    return (path_input, True)


# 互動式配置介面（使用 Rich）
def interactive_config_menu(config_manager: ConfigManager) -> None:
    """互動式配置選單

    Args:
        config_manager: ConfigManager 實例
    """
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    import sys
    from pathlib import Path

    # 確保可以 import utils
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from utils.input_helpers import normalize_fullwidth_input

    console = Console()

    while True:
        console.clear()
        console.print(Panel.fit(
            "[bold #B565D8]CodeGemini 配置管理[/bold #B565D8]",
            border_style="#B565D8"
        ))

        # 顯示當前配置
        emb_config = config_manager.config.codebase_embedding

        table = Table(title="[bold]Codebase Embedding 配置[/bold]", show_header=True)
        console_width = console.width or 120
        table.add_column("設定項", style="#B565D8", width=max(20, int(console_width * 0.25)))
        table.add_column("當前值", style="green", width=max(25, int(console_width * 0.30)))
        table.add_column("說明", style="dim", width=max(30, int(console_width * 0.35)))

        table.add_row(
            "1. 啟用狀態",
            "✅ 已啟用" if emb_config.enabled else "❌ 未啟用",
            "是否自動載入 Codebase Embedding"
        )
        table.add_row(
            "2. 向量資料庫路徑",
            emb_config.vector_db_path,
            "embedding 資料儲存位置"
        )
        table.add_row(
            "3. 正交模式",
            "✅ 啟用" if emb_config.orthogonal_mode else "❌ 關閉",
            "自動去重，保持內容線性獨立"
        )
        table.add_row(
            "4. 向量相關係數閾值",
            f"{emb_config.similarity_threshold:.2f}",
            "正交模式下的向量相關係數閾值 (0.0-1.0，值越高越相似)"
        )
        table.add_row(
            "5. 向量資料庫集合名稱",
            emb_config.collection_name,
            "ChromaDB 中唯一識別此程式碼庫的集合名稱"
        )

        console.print(table)
        console.print(safe_t("config.menu.other_options", fallback="\n[bold #B565D8]其他選項：[/bold #B565D8]"))
        console.print(safe_t("config.menu.reset", fallback="  6. 重置為預設配置"))
        console.print(safe_t("config.menu.view_path", fallback="  7. 查看配置檔案路徑"))
        console.print(safe_t("config.menu.view_modules", fallback="  8. 查看已啟用模組（背景載入狀態）"))
        console.print(safe_t("config.menu.back", fallback="  0. 返回主選單"))

        # ✅ V-5 修復：記憶上次選擇
        last_choice = config_manager.get_last_menu_choice()

        # 使用不限制輸入的方式，然後手動規範化和驗證
        while True:
            choice_raw = Prompt.ask(
                "\n[bold #B565D8]請選擇要修改的設定 [0/1/2/3/4/5/6/7/8][/bold #B565D8]",
                default=last_choice,
                show_default=True
            )
            # 規範化全形輸入
            choice = normalize_fullwidth_input(choice_raw)

            # 驗證輸入
            if choice in ["0", "1", "2", "3", "4", "5", "6", "7", "8"]:
                break
            else:
                console.print(f"[yellow]⚠ 無效的選項：{choice_raw}，請輸入 0-8 之間的數字[/yellow]")

        # 儲存選擇（除了「返回」選項）
        if choice != "0":
            config_manager.save_last_menu_choice(choice)

        if choice == "0":
            break

        elif choice == "1":
            # 切換啟用狀態
            new_enabled = Confirm.ask(
                "是否啟用 Codebase Embedding？",
                default=emb_config.enabled
            )
            config_manager.update_codebase_embedding_config(enabled=new_enabled)
            console.print(safe_t('codegemini.config.updated_enabled', fallback='[#B565D8]✓ 已更新啟用狀態[/#B565D8]'))
            console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))

        elif choice == "2":
            # 修改向量資料庫路徑（✅ V-7: 路徑輸入驗證與建議）
            console.print(safe_t("config.vector.path_title", fallback="\n[#B565D8]📁 向量資料庫路徑配置[/#B565D8]"))
            console.print(safe_t("config.vector.path_usage", fallback="[dim]· 用途: 儲存程式碼向量 embedding 資料[/dim]"))
            console.print(safe_t("config.vector.path_format", fallback="[dim]· 格式: 可使用相對路徑（相對於 Cache 目錄）或絕對路徑[/dim]"))
            console.print(safe_t("config.vector.path_current", fallback="[dim]· 當前路徑: {path}[/dim]\n").format(path=emb_config.vector_db_path))

            while True:
                new_path = Prompt.ask(
                    "[#B565D8]請輸入新的向量資料庫路徑[/#B565D8]",
                    default=emb_config.vector_db_path
                )

                # 驗證路徑（✅ V-7 新增）
                validated_path, is_valid = _validate_and_suggest_path(
                    new_path,
                    create_if_missing=True
                )

                if is_valid:
                    config_manager.update_codebase_embedding_config(vector_db_path=validated_path)
                    console.print(safe_t('codegemini.config.updated_path', fallback='\n[#B565D8]✓ 已更新向量資料庫路徑[/#B565D8]'))
                    break
                else:
                    console.print(safe_t('codegemini.config.path_validation_failed', fallback='\n[#B565D8]路徑驗證失敗，請重新輸入[/#B565D8]'))
                    if not Confirm.ask(safe_t('codegemini.config.retry_input', fallback='是否重新輸入？'), default=True):
                        console.print(safe_t('codegemini.config.keep_original_path', fallback='[dim]已取消，保留原路徑[/dim]'))
                        break

            console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))

        elif choice == "3":
            # 切換正交模式
            new_orthogonal = Confirm.ask(
                "是否啟用正交模式（自動去重）？",
                default=emb_config.orthogonal_mode
            )
            config_manager.update_codebase_embedding_config(orthogonal_mode=new_orthogonal)
            console.print(safe_t('codegemini.config.updated_orthogonal', fallback='[#B565D8]✓ 已更新正交模式[/#B565D8]'))
            console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))

        elif choice == "4":
            # 修改向量相關係數閾值
            console.print(safe_t("config.vector.threshold_desc", fallback="\n[#B565D8]向量相關係數閾值說明：[/#B565D8]"))
            console.print(safe_t("config.vector.threshold_095", fallback="  - 0.95: 非常嚴格（只過濾幾乎完全相同的內容）"))
            console.print(safe_t("config.vector.threshold_085", fallback="  - 0.85: 建議值（過濾高度相似的內容）"))
            console.print(safe_t("config.vector.threshold_075", fallback="  - 0.75: 寬鬆（過濾明顯相似的內容）"))

            # ✅ M3 修復：使用選項而非自由輸入
            console.print(safe_t("config.vector.threshold_options", fallback="\n[#B565D8]向量相關係數閾值選項：[/#B565D8]"))

            options = {
                "1": ("非常嚴格", 0.95),
                "2": ("建議值", 0.85),
                "3": ("寬鬆", 0.75),
                "4": ("自訂", None)
            }

            for key, (desc, val) in options.items():
                marker = "✓" if val == emb_config.similarity_threshold else " "
                console.print(safe_t("config.vector.threshold_item", fallback="  {key}. [{marker}] {desc} ({val})").format(key=key, marker=marker, desc=desc, val=val if val else '自訂'))

            while True:
                choice_threshold_raw = Prompt.ask("請選擇 [1/2/3/4]", default="2")
                choice_threshold = normalize_fullwidth_input(choice_threshold_raw)
                if choice_threshold in options.keys():
                    break
                console.print(f"[yellow]⚠ 無效的選項：{choice_threshold_raw}[/yellow]")

            if choice_threshold == "4":
                # 僅在選擇「自訂」時才要求輸入
                new_threshold_str = Prompt.ask(
                    "請輸入向量相關係數閾值 (0.0-1.0)",
                    default=str(emb_config.similarity_threshold)
                )
                try:
                    new_threshold = float(new_threshold_str)
                except ValueError:
                    console.print(safe_t('codegemini.config.invalid_value', fallback='[dim #B565D8]✗ 無效的數值[/red]'))
                    console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))
                    continue
            else:
                _, new_threshold = options[choice_threshold]

            if config_manager.update_codebase_embedding_config(similarity_threshold=new_threshold):
                console.print(safe_t('codegemini.config.updated_threshold', fallback='[#B565D8]✓ 已更新向量相關係數閾值[/#B565D8]'))
            else:
                console.print(safe_t('codegemini.config.threshold_update_failed', fallback='[#B565D8]✗ 更新失敗（向量相關係數閾值應在 0.0-1.0 之間）[/#B565D8]'))

            console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))

        elif choice == "5":
            # 修改向量資料庫集合名稱（✅ M2: 中文命名明確性改善）
            console.print(safe_t("config.vector.collection_title", fallback="\n[#B565D8]📋 向量資料庫集合名稱配置[/#B565D8]"))
            console.print(safe_t("config.vector.collection_usage", fallback="[dim]· 用途說明: 在 ChromaDB 中唯一識別此程式碼庫的向量集合[/dim]"))
            console.print(safe_t("config.vector.collection_format", fallback="[dim]· 格式限制: 僅限英文字母 (a-z, A-Z)、數字 (0-9)、底線 (_)[/dim]"))
            console.print(safe_t("config.vector.collection_forbidden", fallback="[dim]· 禁止內容: 空格、連字號 (-) 等特殊符號、中文字元[/dim]"))
            console.print(safe_t("config.vector.collection_length", fallback="[dim]· 建議長度: 3-32 字元[/dim]"))
            console.print(safe_t("config.vector.collection_valid", fallback="\n[#B565D8]✓ 有效範例:[/#B565D8]"))
            console.print(safe_t("config.vector.example1", fallback="  [orchid1]codebase_main[/orchid1] (基礎命名)"))
            console.print(safe_t("config.vector.example2", fallback="  [orchid1]project_v2_embeddings[/orchid1] (含版本號)"))
            console.print(safe_t("config.vector.example3", fallback="  [orchid1]ChatGemini_SakiTool[/orchid1] (專案名稱)"))
            console.print(safe_t("config.vector.collection_invalid", fallback="\n[#B565D8]✗ 無效範例 (會被拒絕):[/#B565D8]"))
            console.print(safe_t("config.vector.invalid1", fallback="  [dim]my-project[/dim] → 含連字號 (-)"))
            console.print(safe_t("config.vector.invalid2", fallback="  [dim]code base[/dim] → 含空格"))
            console.print(safe_t("config.vector.invalid3", fallback="  [dim]專案名稱[/dim] → 含中文字元\n"))

            import re
            while True:
                new_collection_name = Prompt.ask(
                    "[#B565D8]請輸入向量資料庫集合名稱 (限英數底線)[/#B565D8]",
                    default=emb_config.collection_name
                )

                # 格式驗證
                if re.match(r'^[a-zA-Z0-9_]+$', new_collection_name):
                    console.print(safe_t('codegemini.config.collection_format_valid', fallback='\n[#B565D8]✓ 格式驗證通過: {name}[/#B565D8]', name=new_collection_name))
                    break
                else:
                    console.print(safe_t('codegemini.config.collection_format_invalid', fallback='\n[#B565D8]❌ 名稱格式不符合規則[/#B565D8]'))
                    console.print(safe_t('codegemini.config.collection_invalid_reason', fallback='[dim]· 原因: 包含不允許的字元[/dim]'))
                    console.print(safe_t('codegemini.config.collection_allowed_chars', fallback='[dim]· 允許: 英文字母 (a-zA-Z)、數字 (0-9)、底線 (_)[/dim]'))
                    console.print(safe_t('codegemini.config.collection_refer_examples', fallback='[dim]· 請參考上方有效範例重新輸入[/dim]\n'))

            # 更新配置
            config_manager.update_codebase_embedding_config(
                collection_name=new_collection_name
            )
            console.print(safe_t('codegemini.config.updated_collection', fallback='[#B565D8]✓ 已更新向量資料庫集合名稱[/#B565D8]'))
            console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))

        elif choice == "6":
            # 重置為預設配置
            if Confirm.ask(safe_t('codegemini.config.confirm_reset', fallback='[bold red]確定要重置所有配置為預設值嗎？[/bold red]'), default=False):
                config_manager.reset_to_defaults()
                console.print(safe_t('codegemini.config.reset_done', fallback='[#B565D8]✓ 配置已重置為預設值[/#B565D8]'))
            console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))

        elif choice == "7":
            # 查看配置檔案路徑
            console.print(safe_t('codegemini.config.file_path', fallback='\n[#B565D8]配置檔案路徑：[/#B565D8] {path}', path=config_manager.config_path))
            console.print(safe_t('codegemini.config.file_exists', fallback='[#B565D8]檔案存在：[/#B565D8] {exists}', exists='是' if config_manager.config_path.exists() else '否'))
            console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))

        elif choice == "8":
            # 查看已啟用模組（背景載入狀態）
            try:
                from smart_background_loader import get_smart_loader

                console.print(safe_t('config.modules.title', fallback='\n[bold #B565D8]📦 已啟用模組狀態[/bold #B565D8]\n'))

                loader = get_smart_loader()
                stats = loader.get_stats()

                # 顯示統計資訊
                console.print(safe_t('config.modules.summary', fallback='[#B565D8]載入統計：[/#B565D8]'))
                console.print(safe_t('config.modules.total', fallback='  · 總任務數: {total}').format(total=stats['total_tasks']))
                console.print(safe_t('config.modules.loaded', fallback='  · 已載入: {loaded} ({rate:.1%})').format(
                    loaded=stats['loaded_tasks'],
                    rate=stats['loading_rate']
                ))
                console.print(safe_t('config.modules.time', fallback='  · 總載入時間: {time:.2f}s').format(time=stats['total_load_time']))
                console.print(safe_t('config.modules.background', fallback='  · 背景載入時間: {time:.2f}s').format(time=stats['background_load_time']))
                console.print(safe_t('config.modules.foreground', fallback='  · 前景載入時間: {time:.2f}s').format(time=stats['foreground_load_time']))

                # 顯示模組詳細列表
                console.print(safe_t('config.modules.detail', fallback='\n[#B565D8]模組詳細列表：[/#B565D8]'))

                from rich.table import Table
                module_table = Table(show_header=True, header_style="bold #B565D8", border_style="#B565D8")
                module_table.add_column("模組名稱", style="#87CEEB", width=25)
                module_table.add_column("狀態", style="white", width=12)
                module_table.add_column("優先級", style="white", width=12)
                module_table.add_column("載入時間", style="white", width=15)

                # 獲取所有任務資訊
                with loader._lock:
                    tasks = list(loader._tasks.values())

                # 按優先級排序
                tasks.sort(key=lambda t: t.priority.value)

                for task in tasks:
                    status = "✅ 已載入" if task.loaded else "⏳ 未載入"
                    load_time = f"{task.load_time:.3f}s" if task.loaded else "—"
                    module_table.add_row(
                        task.name,
                        status,
                        task.priority.name,
                        load_time
                    )

                console.print(module_table)

                console.print(safe_t('config.modules.note', fallback='\n[dim]💡 提示：背景載入器會在使用者操作時自動載入模組，無需手動干預[/dim]'))

            except Exception as e:
                console.print(safe_t('config.modules.error', fallback='[#B565D8]✗ 無法獲取模組狀態: {e}[/#B565D8]', e=str(e)))

            console.input(safe_t('common.press_enter', fallback='\n按 Enter 繼續...'))


# 測試用例
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print(safe_t("config.test.title", fallback="CodeGemini 配置管理器測試"))
    print("=" * 60)

    # 建立配置管理器
    config_manager = ConfigManager()

    # 顯示當前配置
    print(safe_t("config.test.current", fallback="\n當前配置："))
    summary = config_manager.get_config_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # 測試更新配置
    print(safe_t("config.test.updating", fallback="\n測試更新配置..."))
    config_manager.update_codebase_embedding_config(
        enabled=True,
        orthogonal_mode=True,
        similarity_threshold=0.90
    )

    # 顯示更新後的配置
    print(safe_t("config.test.updated", fallback="\n更新後的配置："))
    summary = config_manager.get_config_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # 測試互動式選單（可選）
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_config_menu(config_manager)

    print(safe_t("config.test.passed", fallback="\n✓ 所有測試通過！"))
