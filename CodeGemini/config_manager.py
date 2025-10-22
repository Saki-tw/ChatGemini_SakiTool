#!/usr/bin/env python3
"""
CodeGemini Configuration Manager
配置管理模組 - 管理所有可配置的參數

功能：
1. 資料庫配置（正交模式、相似度閾值）
2. 持久化配置到 JSON 檔案
3. 互動式配置介面
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class CodebaseEmbeddingConfig:
    """Codebase Embedding 配置"""
    enabled: bool = False
    vector_db_path: str = ".embeddings"
    orthogonal_mode: bool = False
    similarity_threshold: float = 0.85
    collection_name: str = "codebase"


@dataclass
class CodeGeminiConfig:
    """CodeGemini 完整配置"""
    # Codebase Embedding 配置
    codebase_embedding: CodebaseEmbeddingConfig = field(default_factory=CodebaseEmbeddingConfig)

    # 未來可擴展其他配置
    # auto_model_selection: AutoModelConfig = ...
    # checkpoint_system: CheckpointConfig = ...


class ConfigManager:
    """配置管理器

    功能：
    - 載入/儲存配置到 JSON 檔案
    - 提供配置修改介面
    - 配置驗證
    """

    DEFAULT_CONFIG_PATH = Path.home() / ".codegemini" / "config.json"

    def __init__(self, config_path: Optional[Path] = None):
        """初始化配置管理器

        Args:
            config_path: 配置檔案路徑（預設：~/.codegemini/config.json）
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 載入配置
        self.config = self.load_config()
        logger.info(f"✓ ConfigManager 已初始化: {self.config_path}")

    def load_config(self) -> CodeGeminiConfig:
        """載入配置檔案

        Returns:
            CodeGeminiConfig 實例
        """
        if not self.config_path.exists():
            logger.info("配置檔案不存在，使用預設配置")
            return CodeGeminiConfig()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 解析配置
            codebase_emb_data = data.get('codebase_embedding', {})
            codebase_emb_config = CodebaseEmbeddingConfig(**codebase_emb_data)

            config = CodeGeminiConfig(codebase_embedding=codebase_emb_config)
            logger.info("✓ 配置檔案已載入")
            return config

        except Exception as e:
            logger.error(f"✗ 載入配置失敗: {e}")
            logger.info("使用預設配置")
            return CodeGeminiConfig()

    def save_config(self) -> bool:
        """儲存配置到檔案

        Returns:
            是否成功
        """
        try:
            # 轉換為字典
            config_dict = {
                'codebase_embedding': asdict(self.config.codebase_embedding)
            }

            # 儲存到 JSON
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ 配置已儲存: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"✗ 儲存配置失敗: {e}")
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
            similarity_threshold: 相似度閾值
            collection_name: Collection 名稱

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
                logger.error(f"✗ 無效的相似度閾值: {similarity_threshold}（應在 0.0-1.0 之間）")
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
        logger.info("✓ 配置已重置為預設值")
        return self.save_config()

    def get_config_summary(self) -> Dict[str, Any]:
        """獲取配置摘要（用於顯示）

        Returns:
            配置摘要字典
        """
        emb_config = self.config.codebase_embedding

        return {
            'config_path': str(self.config_path),
            'codebase_embedding': {
                'enabled': emb_config.enabled,
                'vector_db_path': emb_config.vector_db_path,
                'orthogonal_mode': emb_config.orthogonal_mode,
                'similarity_threshold': emb_config.similarity_threshold,
                'collection_name': emb_config.collection_name
            }
        }


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

    console = Console()

    while True:
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]CodeGemini 配置管理[/bold cyan]",
            border_style="cyan"
        ))

        # 顯示當前配置
        emb_config = config_manager.config.codebase_embedding

        table = Table(title="[bold]Codebase Embedding 配置[/bold]", show_header=True)
        table.add_column("設定項", style="cyan", width=25)
        table.add_column("當前值", style="green", width=30)
        table.add_column("說明", style="dim", width=40)

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
            "4. 相似度閾值",
            f"{emb_config.similarity_threshold:.2f}",
            "正交模式下的去重閾值 (0.0-1.0)"
        )
        table.add_row(
            "5. Collection 名稱",
            emb_config.collection_name,
            "向量資料庫 collection 名稱"
        )

        console.print(table)
        console.print("\n[bold yellow]其他選項：[/bold yellow]")
        console.print("  6. 重置為預設配置")
        console.print("  7. 查看配置檔案路徑")
        console.print("  0. 返回主選單")

        choice = Prompt.ask(
            "\n[bold cyan]請選擇要修改的設定[/bold cyan]",
            choices=["0", "1", "2", "3", "4", "5", "6", "7"],
            default="0"
        )

        if choice == "0":
            break

        elif choice == "1":
            # 切換啟用狀態
            new_enabled = Confirm.ask(
                "是否啟用 Codebase Embedding？",
                default=emb_config.enabled
            )
            config_manager.update_codebase_embedding_config(enabled=new_enabled)
            console.print("[green]✓ 已更新啟用狀態[/green]")
            console.input("\n按 Enter 繼續...")

        elif choice == "2":
            # 修改向量資料庫路徑
            new_path = Prompt.ask(
                "請輸入新的向量資料庫路徑",
                default=emb_config.vector_db_path
            )
            config_manager.update_codebase_embedding_config(vector_db_path=new_path)
            console.print("[green]✓ 已更新向量資料庫路徑[/green]")
            console.input("\n按 Enter 繼續...")

        elif choice == "3":
            # 切換正交模式
            new_orthogonal = Confirm.ask(
                "是否啟用正交模式（自動去重）？",
                default=emb_config.orthogonal_mode
            )
            config_manager.update_codebase_embedding_config(orthogonal_mode=new_orthogonal)
            console.print("[green]✓ 已更新正交模式[/green]")
            console.input("\n按 Enter 繼續...")

        elif choice == "4":
            # 修改相似度閾值
            console.print("\n[yellow]相似度閾值說明：[/yellow]")
            console.print("  - 0.95: 非常嚴格（只過濾幾乎完全相同的內容）")
            console.print("  - 0.85: 建議值（過濾高度相似的內容）")
            console.print("  - 0.75: 寬鬆（過濾明顯相似的內容）")

            new_threshold_str = Prompt.ask(
                "\n請輸入新的相似度閾值 (0.0-1.0)",
                default=str(emb_config.similarity_threshold)
            )

            try:
                new_threshold = float(new_threshold_str)
                if config_manager.update_codebase_embedding_config(similarity_threshold=new_threshold):
                    console.print("[green]✓ 已更新相似度閾值[/green]")
                else:
                    console.print("[red]✗ 更新失敗（閾值應在 0.0-1.0 之間）[/red]")
            except ValueError:
                console.print("[red]✗ 無效的數值[/red]")

            console.input("\n按 Enter 繼續...")

        elif choice == "5":
            # 修改 Collection 名稱
            new_collection = Prompt.ask(
                "請輸入新的 Collection 名稱",
                default=emb_config.collection_name
            )
            config_manager.update_codebase_embedding_config(collection_name=new_collection)
            console.print("[green]✓ 已更新 Collection 名稱[/green]")
            console.input("\n按 Enter 繼續...")

        elif choice == "6":
            # 重置為預設配置
            if Confirm.ask("[bold red]確定要重置所有配置為預設值嗎？[/bold red]", default=False):
                config_manager.reset_to_defaults()
                console.print("[green]✓ 配置已重置為預設值[/green]")
            console.input("\n按 Enter 繼續...")

        elif choice == "7":
            # 查看配置檔案路徑
            console.print(f"\n[cyan]配置檔案路徑：[/cyan] {config_manager.config_path}")
            console.print(f"[cyan]檔案存在：[/cyan] {'是' if config_manager.config_path.exists() else '否'}")
            console.input("\n按 Enter 繼續...")


# 測試用例
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("CodeGemini 配置管理器測試")
    print("=" * 60)

    # 建立配置管理器
    config_manager = ConfigManager()

    # 顯示當前配置
    print("\n當前配置：")
    summary = config_manager.get_config_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # 測試更新配置
    print("\n測試更新配置...")
    config_manager.update_codebase_embedding_config(
        enabled=True,
        orthogonal_mode=True,
        similarity_threshold=0.90
    )

    # 顯示更新後的配置
    print("\n更新後的配置：")
    summary = config_manager.get_config_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # 測試互動式選單（可選）
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_config_menu(config_manager)

    print("\n✓ 所有測試通過！")
