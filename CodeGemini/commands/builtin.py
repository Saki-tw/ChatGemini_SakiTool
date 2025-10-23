#!/usr/bin/env python3
"""
CodeGemini Built-in Commands Module
內建命令 - 預定義的常用命令

此模組提供以下內建命令：
- /test - 生成單元測試
- /optimize - 優化程式碼
- /explain - 解釋程式碼
- /refactor - 重構建議
- /docs - 生成文檔
- /scaffold - 搭建專案結構
"""
from typing import List
from rich.console import Console

from .registry import CommandTemplate, CommandType, CommandRegistry

console = Console()


class BuiltinCommands:
    """內建命令管理器"""

    @staticmethod
    def get_all_commands() -> List[CommandTemplate]:
        """
        取得所有內建命令

        Returns:
            List[CommandTemplate]: 內建命令列表
        """
        return [
            BuiltinCommands.test_command(),
            BuiltinCommands.optimize_command(),
            BuiltinCommands.explain_command(),
            BuiltinCommands.refactor_command(),
            BuiltinCommands.docs_command(),
            BuiltinCommands.scaffold_command(),
            BuiltinCommands.review_command(),
            BuiltinCommands.debug_command(),
        ]

    @staticmethod
    def test_command() -> CommandTemplate:
        """生成單元測試命令"""
        return CommandTemplate(
            name="test",
            description="為指定的函數或類別生成單元測試",
            template="""請為以下程式碼生成單元測試：

目標：{target}
測試框架：{framework|default:"pytest"}
覆蓋率目標：{coverage|default:"80%"}

{% if test_cases %}
特定測試場景：
{% for case in test_cases %}  - {case}
{% endfor %}
{% endif %}

請確保：
1. 測試邊界條件
2. 測試異常處理
3. 測試正常流程
{% if include_mocks %}4. 使用 mock 處理外部依賴{% endif %}

程式碼：
{code}
""",
            command_type=CommandType.BUILTIN,
            parameters=["target", "code"],
            examples=[
                '/test target="calculate_sum 函數" code="<code>" framework="pytest"',
                '/test target="UserService 類別" code="<code>" include_mocks=true'
            ],
            tags=["testing", "quality-assurance"],
            author="CodeGemini",
            version="1.0.0"
        )

    @staticmethod
    def optimize_command() -> CommandTemplate:
        """優化程式碼命令"""
        return CommandTemplate(
            name="optimize",
            description="分析並優化程式碼效能",
            template="""請分析以下程式碼並提供優化建議：

優化目標：{goal|default:"效能"}
語言：{language}

程式碼：
{code}

請提供：
1. 目前程式碼的時間複雜度分析
2. 目前程式碼的空間複雜度分析
3. 效能瓶頸識別
4. 優化建議（附程式碼範例）
5. 優化後的預期效能提升

{% if benchmark %}請包含基準測試程式碼{% endif %}
{% if profile %}請包含效能分析建議{% endif %}
""",
            command_type=CommandType.BUILTIN,
            parameters=["code", "language"],
            examples=[
                '/optimize code="<code>" language="Python" goal="效能"',
                '/optimize code="<code>" language="JavaScript" benchmark=true'
            ],
            tags=["performance", "optimization"],
            author="CodeGemini",
            version="1.0.0"
        )

    @staticmethod
    def explain_command() -> CommandTemplate:
        """解釋程式碼命令"""
        return CommandTemplate(
            name="explain",
            description="解釋程式碼的功能與運作方式",
            template="""請詳細解釋以下程式碼：

程式碼：
{code}

{% if language %}語言：{language}{% endif %}

請提供：
1. 整體功能說明
2. 逐步執行流程
3. 關鍵邏輯解釋
4. 使用的演算法或設計模式
{% if beginner_friendly %}5. 新手友善的比喻說明{% endif %}
{% if include_diagram %}6. 流程圖或架構圖（使用 Mermaid 或 ASCII）{% endif %}
""",
            command_type=CommandType.BUILTIN,
            parameters=["code"],
            examples=[
                '/explain code="<code>" language="Python"',
                '/explain code="<code>" beginner_friendly=true include_diagram=true'
            ],
            tags=["documentation", "learning"],
            author="CodeGemini",
            version="1.0.0"
        )

    @staticmethod
    def refactor_command() -> CommandTemplate:
        """重構建議命令"""
        return CommandTemplate(
            name="refactor",
            description="提供程式碼重構建議",
            template="""請為以下程式碼提供重構建議：

程式碼：
{code}

{% if language %}語言：{language}{% endif %}
重構目標：{goal|default:"可讀性與維護性"}

請檢查：
1. 程式碼異味（Code Smells）
2. 違反 SOLID 原則的地方
3. 重複程式碼
4. 過於複雜的函數或類別
5. 命名改善建議

{% if design_patterns %}請建議適用的設計模式{% endif %}
{% if show_before_after %}請提供重構前後對比{% endif %}
""",
            command_type=CommandType.BUILTIN,
            parameters=["code"],
            examples=[
                '/refactor code="<code>" language="Python"',
                '/refactor code="<code>" design_patterns=true show_before_after=true'
            ],
            tags=["refactoring", "code-quality"],
            author="CodeGemini",
            version="1.0.0"
        )

    @staticmethod
    def docs_command() -> CommandTemplate:
        """生成文檔命令"""
        return CommandTemplate(
            name="docs",
            description="為程式碼生成文檔",
            template="""請為以下程式碼生成文檔：

程式碼：
{code}

{% if language %}語言：{language}{% endif %}
文檔格式：{format|default:"Markdown"}

請包含：
1. 函數/類別描述
2. 參數說明（類型、用途）
3. 返回值說明
4. 使用範例
{% if include_exceptions %}5. 可能拋出的異常{% endif %}
{% if include_examples %}6. 完整的程式碼範例{% endif %}

{% if style %}
文檔風格：{style}
{% endif %}
""",
            command_type=CommandType.BUILTIN,
            parameters=["code"],
            examples=[
                '/docs code="<code>" language="Python" style="Google Style"',
                '/docs code="<code>" format="JSDoc" include_examples=true'
            ],
            tags=["documentation"],
            author="CodeGemini",
            version="1.0.0"
        )

    @staticmethod
    def scaffold_command() -> CommandTemplate:
        """搭建專案結構命令"""
        return CommandTemplate(
            name="scaffold",
            description="搭建新專案或元件的檔案結構",
            template="""請搭建以下專案結構：

專案類型：{project_type}
專案名稱：{project_name}
{% if description %}描述：{description}{% endif %}

{% if language %}語言：{language}{% endif %}
{% if framework %}框架：{framework}{% endif %}

請生成：
1. 目錄結構
2. 必要的配置檔案
3. 範例程式碼檔案
{% if include_tests %}4. 測試目錄與範例測試{% endif %}
{% if include_ci %}5. CI/CD 配置{% endif %}
{% if include_docker %}6. Docker 配置{% endif %}
{% if include_readme %}7. README.md{% endif %}

{% if features %}
必要功能：
{% for feature in features %}  - {feature}
{% endfor %}
{% endif %}
""",
            command_type=CommandType.BUILTIN,
            parameters=["project_type", "project_name"],
            examples=[
                '/scaffold project_type="React App" project_name="my-app"',
                '/scaffold project_type="Python Library" project_name="my-lib" include_tests=true include_ci=true'
            ],
            tags=["scaffolding", "project-setup"],
            author="CodeGemini",
            version="1.0.0"
        )

    @staticmethod
    def review_command() -> CommandTemplate:
        """程式碼審查命令"""
        return CommandTemplate(
            name="review",
            description="進行全面的程式碼審查",
            template="""請審查以下程式碼：

程式碼：
{code}

{% if language %}語言：{language}{% endif %}
審查重點：{focus|default:"全面"}

審查項目：
1. **安全性**：潛在的安全漏洞
2. **效能**：效能問題與優化機會
3. **可讀性**：程式碼可讀性與命名
4. **最佳實踐**：是否遵循語言/框架最佳實踐
5. **錯誤處理**：異常處理是否完善
6. **測試覆蓋**：是否需要更多測試

{% if strict %}請使用嚴格標準{% endif %}
{% if provide_examples %}請提供改善範例{% endif %}

請以清單方式標註問題等級（🔴 嚴重、🟡 中等、🟢 建議）
""",
            command_type=CommandType.BUILTIN,
            parameters=["code"],
            examples=[
                '/review code="<code>" language="Python"',
                '/review code="<code>" focus="安全性" strict=true'
            ],
            tags=["code-review", "quality-assurance"],
            author="CodeGemini",
            version="1.0.0"
        )

    @staticmethod
    def debug_command() -> CommandTemplate:
        """除錯協助命令"""
        return CommandTemplate(
            name="debug",
            description="協助診斷並修復程式碼問題",
            template="""請協助除錯以下程式碼：

程式碼：
{code}

{% if error_message %}
錯誤訊息：
{error_message}
{% endif %}

{% if expected_behavior %}
預期行為：{expected_behavior}
{% endif %}

{% if actual_behavior %}
實際行為：{actual_behavior}
{% endif %}

請提供：
1. 問題診斷（可能的原因）
2. 建議的除錯步驟
3. 修復方案（附程式碼）
4. 預防類似問題的建議

{% if include_logging %}請建議日誌記錄策略{% endif %}
{% if include_tests %}請提供測試案例以驗證修復{% endif %}
""",
            command_type=CommandType.BUILTIN,
            parameters=["code"],
            examples=[
                '/debug code="<code>" error_message="IndexError: list index out of range"',
                '/debug code="<code>" expected_behavior="返回 5" actual_behavior="返回 3"'
            ],
            tags=["debugging", "troubleshooting"],
            author="CodeGemini",
            version="1.0.0"
        )

    @staticmethod
    def register_all(registry: CommandRegistry) -> int:
        """
        註冊所有內建命令到註冊表

        Args:
            registry: 命令註冊表

        Returns:
            int: 成功註冊的命令數量
        """
        commands = BuiltinCommands.get_all_commands()
        count = 0

        for cmd in commands:
            success = registry.register_command(
                cmd.name,
                cmd,
                save_to_config=False  # 內建命令不儲存到配置檔
            )
            if success:
                count += 1

        return count


def main():
    """測試用主程式"""
    console.print("[bold magenta]CodeGemini Built-in Commands 測試[/bold magenta]\n")

    # 取得所有內建命令
    commands = BuiltinCommands.get_all_commands()

    console.print(f"[bold]內建命令數量：{len(commands)}[/bold]\n")

    # 顯示每個命令的詳情
    for cmd in commands:
        console.print(f"[bold yellow]/{cmd.name}[/bold yellow]")
        console.print(f"  描述：{cmd.description}")
        console.print(f"  參數：{', '.join(cmd.parameters)}")
        console.print(f"  標籤：{', '.join(cmd.tags)}")
        console.print()

    # 測試註冊到 Registry
    from .registry import CommandRegistry

    console.print("[bold magenta]測試註冊到 Registry：[/bold magenta]")
    registry = CommandRegistry()
    count = BuiltinCommands.register_all(registry)

    console.print(f"\n[bright_magenta]✓ 成功註冊 {count} 個內建命令[/green]")

    # 顯示註冊表中的命令
    registry.show_commands_table(filter_type=CommandType.BUILTIN)


if __name__ == "__main__":
    main()
