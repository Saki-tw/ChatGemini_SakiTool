#!/usr/bin/env python3
"""
PROJECT.md 專案記憶系統

本模組提供專案記憶功能，允許工具從專案根目錄的 PROJECT.md 載入專案上下文資訊。

核心功能：
1. 自動載入 PROJECT.md 專案記憶檔案
2. 注入到系統提示詞中
3. 提供 /init 和 /memory 斜線指令
4. 支援多語言（中英日）

設計理念：
- 專案記憶應在啟動時自動載入
- 記憶內容以 Markdown 格式存儲
- 支援模板初始化
- 提供簡易編輯介面

使用範例：
    from core.project_memory import ProjectMemory

    # 初始化專案記憶
    pm = ProjectMemory()

    # 載入記憶內容
    memory_content = pm.load_memory()

    # 生成系統提示詞片段
    prompt_injection = pm.get_memory_prompt()

    # 初始化 PROJECT.md 模板
    pm.init_memory_file()

    # 編輯記憶（呼叫編輯器）
    pm.edit_memory()
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import subprocess

logger = logging.getLogger(__name__)


class ProjectMemory:
    """
    專案記憶管理類別

    負責載入、管理和注入專案記憶（PROJECT.md）到系統提示詞。

    Attributes:
        memory_file (Path): PROJECT.md 檔案路徑
        root_dir (Path): 專案根目錄
        template_lang (str): 模板語言（zh/en/ja）
    """

    # PROJECT.md 檔案名稱
    MEMORY_FILENAME = 'PROJECT.md'

    # 預設模板（多語言）
    DEFAULT_TEMPLATES = {
        'zh': """# PROJECT.md - 專案記憶

> 本檔案用於為 AI 工具提供專案上下文資訊。
> 啟動時會自動載入並注入到系統提示詞中。

## 專案概覽

**專案名稱**: [請填寫專案名稱]
**專案類型**: [Web應用/CLI工具/函式庫/其他]
**主要技術棧**: [Python/JavaScript/其他]

**簡述**: [用一句話描述這個專案的核心功能]

---

## 專案結構

```
project/
├── core/          # 核心模組
├── utils/         # 工具函數
├── tests/         # 測試
└── docs/          # 文件
```

---

## 關鍵資訊

### 開發規範
- **程式碼風格**: [PEP 8 / Airbnb / Google / 自訂]
- **測試框架**: [pytest / unittest / jest / 其他]
- **文件標準**: [Google Docstrings / NumPy / JSDoc]

### 重要約定
- [列出專案中的命名約定、架構決策等]
- [例如：所有 API 函數必須包含型別提示]
- [例如：測試覆蓋率要求 > 80%]

### 常用指令
```bash
# 執行測試
python -m pytest tests/

# 程式碼檢查
flake8 .

# 建置專案
python setup.py build
```

---

## 當前任務

### 🔥 進行中
- [ ] 任務 1
- [ ] 任務 2

### 📋 待辦事項
- [ ] 待辦 1
- [ ] 待辦 2

### ✅ 已完成
- [x] 已完成任務 1
- [x] 已完成任務 2

---

## 已知問題

1. **問題描述**: [描述]
   - **影響範圍**: [模組/功能]
   - **暫時方案**: [Workaround]
   - **計劃修復**: [時間/方案]

---

## 重要備註

- [在這裡記錄任何 AI 助手應該知道的重要資訊]
- [例如：特殊的建置流程、環境設定要求等]
- [例如：某些檔案不應該修改的原因]

---

**最後更新**: {timestamp}
**維護者**: [你的名字]
""",

        'en': """# PROJECT.md - Project Memory

> This file provides project context information for AI tools.
> It will be automatically loaded and injected into the system prompt at startup.

## Project Overview

**Project Name**: [Fill in project name]
**Project Type**: [Web App/CLI Tool/Library/Other]
**Main Tech Stack**: [Python/JavaScript/Other]

**Description**: [Describe the core functionality of this project in one sentence]

---

## Project Structure

```
project/
├── core/          # Core modules
├── utils/         # Utility functions
├── tests/         # Tests
└── docs/          # Documentation
```

---

## Key Information

### Development Standards
- **Code Style**: [PEP 8 / Airbnb / Google / Custom]
- **Test Framework**: [pytest / unittest / jest / Other]
- **Documentation Standard**: [Google Docstrings / NumPy / JSDoc]

### Important Conventions
- [List naming conventions, architectural decisions, etc.]
- [e.g., All API functions must include type hints]
- [e.g., Test coverage requirement > 80%]

### Common Commands
```bash
# Run tests
python -m pytest tests/

# Code linting
flake8 .

# Build project
python setup.py build
```

---

## Current Tasks

### 🔥 In Progress
- [ ] Task 1
- [ ] Task 2

### 📋 Todo
- [ ] Todo 1
- [ ] Todo 2

### ✅ Completed
- [x] Completed task 1
- [x] Completed task 2

---

## Known Issues

1. **Issue Description**: [Description]
   - **Impact Scope**: [Module/Feature]
   - **Workaround**: [Temporary solution]
   - **Planned Fix**: [Timeline/Solution]

---

## Important Notes

- [Record any important information that the AI assistant should know]
- [e.g., Special build processes, environment setup requirements, etc.]
- [e.g., Reasons why certain files should not be modified]

---

**Last Updated**: {timestamp}
**Maintainer**: [Your Name]
""",

        'ja': """# PROJECT.md - プロジェクトメモリ

> このファイルは AI ツールにプロジェクトコンテキスト情報を提供します。
> 起動時に自動的にロードされ、システムプロンプトに注入されます。

## プロジェクト概要

**プロジェクト名**: [プロジェクト名を記入]
**プロジェクトタイプ**: [Webアプリ/CLIツール/ライブラリ/その他]
**主要技術スタック**: [Python/JavaScript/その他]

**説明**: [このプロジェクトのコア機能を一文で説明]

---

## プロジェクト構造

```
project/
├── core/          # コアモジュール
├── utils/         # ユーティリティ関数
├── tests/         # テスト
└── docs/          # ドキュメント
```

---

## 重要情報

### 開発標準
- **コードスタイル**: [PEP 8 / Airbnb / Google / カスタム]
- **テストフレームワーク**: [pytest / unittest / jest / その他]
- **ドキュメント標準**: [Google Docstrings / NumPy / JSDoc]

### 重要な規約
- [命名規則、アーキテクチャの決定などをリスト]
- [例：すべてのAPI関数は型ヒントを含める必要があります]
- [例：テストカバレッジ要件 > 80%]

### よく使うコマンド
```bash
# テスト実行
python -m pytest tests/

# コードチェック
flake8 .

# プロジェクトビルド
python setup.py build
```

---

## 現在のタスク

### 🔥 進行中
- [ ] タスク 1
- [ ] タスク 2

### 📋 Todo
- [ ] Todo 1
- [ ] Todo 2

### ✅ 完了
- [x] 完了タスク 1
- [x] 完了タスク 2

---

## 既知の問題

1. **問題の説明**: [説明]
   - **影響範囲**: [モジュール/機能]
   - **回避策**: [一時的な解決策]
   - **修正予定**: [タイムライン/ソリューション]

---

## 重要な注意事項

- [AI アシスタントが知っておくべき重要な情報をここに記録]
- [例：特別なビルドプロセス、環境設定要件など]
- [例：特定のファイルを変更してはいけない理由]

---

**最終更新**: {timestamp}
**メンテナー**: [あなたの名前]
"""
    }

    def __init__(
        self,
        root_dir: Optional[Path] = None,
        memory_filename: Optional[str] = None
    ):
        """
        初始化專案記憶管理器

        Args:
            root_dir: 專案根目錄（預設為當前工作目錄）
            memory_filename: 記憶檔案名稱（預設為 'PROJECT.md'）
        """
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()
        self.memory_filename = memory_filename or self.MEMORY_FILENAME
        self.memory_file = self.root_dir / self.memory_filename

        logger.debug(f"ProjectMemory 初始化: root_dir={self.root_dir}, memory_file={self.memory_file}")

    # ========================================================================
    # 核心功能
    # ========================================================================

    def load_memory(self) -> str:
        """
        載入專案記憶內容

        Returns:
            記憶內容（Markdown 格式），如果檔案不存在則返回空字串

        Examples:
            >>> pm = ProjectMemory()
            >>> content = pm.load_memory()
            >>> if content:
            ...     print(f"已載入 {len(content)} 字元的專案記憶")
        """
        if not self.memory_file.exists():
            logger.debug(f"專案記憶檔案不存在: {self.memory_file}")
            return ""

        try:
            content = self.memory_file.read_text(encoding='utf-8')
            logger.info(f"成功載入專案記憶: {self.memory_file} ({len(content)} 字元)")
            return content
        except Exception as e:
            logger.error(f"載入專案記憶失敗: {e}", exc_info=True)
            return ""

    def get_memory_prompt(self, section_title: Optional[str] = None) -> str:
        """
        生成專案記憶的系統提示詞片段

        將載入的記憶內容格式化為適合注入系統提示詞的格式。

        Args:
            section_title: 區塊標題（預設自動判斷語言）

        Returns:
            格式化後的提示詞片段，如果無記憶則返回空字串

        Examples:
            >>> pm = ProjectMemory()
            >>> prompt = pm.get_memory_prompt()
            >>> system_prompt = base_prompt + prompt
        """
        memory = self.load_memory()
        if not memory:
            return ""

        # 自動判斷語言（根據記憶內容）
        if section_title is None:
            if '專案記憶' in memory or '專案概覽' in memory:
                section_title = "專案記憶（來自 PROJECT.md）"
            elif 'プロジェクト' in memory:
                section_title = "プロジェクトメモリ（PROJECT.md より）"
            else:
                section_title = "Project Memory (from PROJECT.md)"

        # 格式化為系統提示詞
        prompt = f"\n\n## {section_title}\n\n{memory}\n\n"
        logger.debug(f"生成記憶提示詞: {len(prompt)} 字元")
        return prompt

    def memory_exists(self) -> bool:
        """
        檢查專案記憶檔案是否存在

        Returns:
            True 如果檔案存在，否則 False
        """
        return self.memory_file.exists()

    def get_memory_info(self) -> Dict[str, Any]:
        """
        獲取專案記憶的詳細資訊

        Returns:
            包含檔案資訊的字典：
            - exists: 檔案是否存在
            - path: 檔案完整路徑
            - size: 檔案大小（位元組）
            - lines: 行數
            - last_modified: 最後修改時間

        Examples:
            >>> pm = ProjectMemory()
            >>> info = pm.get_memory_info()
            >>> if info['exists']:
            ...     print(f"記憶檔案: {info['lines']} 行, {info['size']} 位元組")
        """
        info = {
            'exists': self.memory_file.exists(),
            'path': str(self.memory_file.absolute()),
            'size': 0,
            'lines': 0,
            'last_modified': None
        }

        if info['exists']:
            try:
                stat = self.memory_file.stat()
                info['size'] = stat.st_size
                info['last_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()

                # 計算行數
                content = self.load_memory()
                info['lines'] = len(content.splitlines())
            except Exception as e:
                logger.error(f"獲取記憶檔案資訊失敗: {e}")

        return info

    # ========================================================================
    # 初始化功能（/init 指令）
    # ========================================================================

    def init_memory_file(
        self,
        language: str = 'zh',
        force: bool = False,
        project_name: Optional[str] = None
    ) -> bool:
        """
        初始化 PROJECT.md 模板

        Args:
            language: 模板語言 ('zh', 'en', 'ja')
            force: 是否強制覆蓋已存在的檔案
            project_name: 專案名稱（可選，用於自動填充）

        Returns:
            True 如果成功，False 如果失敗或檔案已存在且未強制覆蓋

        Examples:
            >>> pm = ProjectMemory()
            >>> if pm.init_memory_file(language='zh'):
            ...     print("PROJECT.md 模板已建立")
        """
        # 檢查檔案是否已存在
        if self.memory_file.exists() and not force:
            logger.warning(f"專案記憶檔案已存在: {self.memory_file}（使用 force=True 覆蓋）")
            return False

        # 獲取模板
        if language not in self.DEFAULT_TEMPLATES:
            logger.error(f"不支援的語言: {language}（支援: zh, en, ja）")
            return False

        template = self.DEFAULT_TEMPLATES[language]

        # 填充時間戳記
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        template = template.format(timestamp=timestamp)

        # 如果提供專案名稱，自動填充
        if project_name:
            if language == 'zh':
                template = template.replace('[請填寫專案名稱]', project_name)
            elif language == 'en':
                template = template.replace('[Fill in project name]', project_name)
            elif language == 'ja':
                template = template.replace('[プロジェクト名を記入]', project_name)

        # 寫入檔案
        try:
            self.memory_file.write_text(template, encoding='utf-8')
            logger.info(f"成功建立專案記憶模板: {self.memory_file} ({language})")
            return True
        except Exception as e:
            logger.error(f"建立專案記憶模板失敗: {e}", exc_info=True)
            return False

    # ========================================================================
    # 編輯功能（/memory 指令）
    # ========================================================================

    def edit_memory(self, editor: Optional[str] = None) -> bool:
        """
        使用編輯器編輯專案記憶

        自動偵測可用的編輯器，或使用指定的編輯器。

        Args:
            editor: 指定編輯器（如 'vim', 'nano', 'code'）
                   如果為 None，將按順序嘗試：$EDITOR, vim, nano, vi

        Returns:
            True 如果成功打開編輯器，False 如果失敗

        Examples:
            >>> pm = ProjectMemory()
            >>> pm.edit_memory()  # 使用預設編輯器
            >>> pm.edit_memory(editor='code')  # 使用 VSCode
        """
        # 如果檔案不存在，先初始化
        if not self.memory_file.exists():
            logger.info("專案記憶檔案不存在，將建立模板...")
            self.init_memory_file()

        # 決定使用的編輯器
        if editor is None:
            editor = self._get_default_editor()

        if not editor:
            logger.error("找不到可用的編輯器")
            return False

        # 打開編輯器
        try:
            logger.info(f"使用編輯器 '{editor}' 打開: {self.memory_file}")
            subprocess.run([editor, str(self.memory_file)], check=True)
            return True
        except FileNotFoundError:
            logger.error(f"編輯器不存在: {editor}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"編輯器執行失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"打開編輯器時發生錯誤: {e}", exc_info=True)
            return False

    def _get_default_editor(self) -> Optional[str]:
        """
        獲取預設編輯器

        按優先順序嘗試：
        1. $EDITOR 環境變數
        2. vim
        3. nano
        4. vi

        Returns:
            編輯器名稱，如果找不到則返回 None
        """
        # 1. 檢查環境變數
        env_editor = os.environ.get('EDITOR')
        if env_editor:
            return env_editor

        # 2. 嘗試常見編輯器
        for editor in ['vim', 'nano', 'vi']:
            try:
                subprocess.run(
                    ['which', editor],
                    capture_output=True,
                    check=True
                )
                return editor
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        return None


# ============================================================================
# 便利函數
# ============================================================================

def get_project_memory(root_dir: Optional[Path] = None) -> str:
    """
    快速獲取專案記憶內容（便利函數）

    Args:
        root_dir: 專案根目錄（預設為當前目錄）

    Returns:
        記憶內容

    Examples:
        >>> memory = get_project_memory()
        >>> if memory:
        ...     print("已載入專案記憶")
    """
    pm = ProjectMemory(root_dir=root_dir)
    return pm.load_memory()


def inject_project_memory_to_prompt(
    base_prompt: str,
    root_dir: Optional[Path] = None
) -> str:
    """
    將專案記憶注入到系統提示詞（便利函數）

    Args:
        base_prompt: 基礎系統提示詞
        root_dir: 專案根目錄

    Returns:
        注入記憶後的完整提示詞

    Examples:
        >>> system_prompt = "You are a helpful assistant."
        >>> full_prompt = inject_project_memory_to_prompt(system_prompt)
    """
    pm = ProjectMemory(root_dir=root_dir)
    memory_prompt = pm.get_memory_prompt()
    return base_prompt + memory_prompt


# ============================================================================
# 模組測試
# ============================================================================

if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("ProjectMemory 模組測試")
    print("=" * 80)

    # 建立測試實例
    pm = ProjectMemory()

    # 1. 檢查記憶檔案資訊
    print("\n1. 記憶檔案資訊:")
    info = pm.get_memory_info()
    print(f"   檔案存在: {info['exists']}")
    print(f"   路徑: {info['path']}")
    if info['exists']:
        print(f"   大小: {info['size']} 位元組")
        print(f"   行數: {info['lines']}")
        print(f"   最後修改: {info['last_modified']}")

    # 2. 測試載入記憶
    print("\n2. 載入記憶:")
    memory = pm.load_memory()
    if memory:
        print(f"   載入成功: {len(memory)} 字元")
        print(f"   前 100 字元: {memory[:100]}...")
    else:
        print("   檔案不存在或為空")

    # 3. 測試生成提示詞
    print("\n3. 生成提示詞片段:")
    prompt = pm.get_memory_prompt()
    if prompt:
        print(f"   提示詞長度: {len(prompt)} 字元")
        print(f"   前 200 字元:\n{prompt[:200]}...")
    else:
        print("   無記憶內容")

    print("\n" + "=" * 80)
    print("✓ 測試完成")
    print("=" * 80)
