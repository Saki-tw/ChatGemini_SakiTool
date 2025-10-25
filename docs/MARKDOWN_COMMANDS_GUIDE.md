# Markdown 自訂指令使用指南

**功能代號**：M-6
**版本**：1.0.0
**最後更新**：2025-10-25

---

## 📖 目錄

1. [功能概述](#功能概述)
2. [快速開始](#快速開始)
3. [Markdown 格式規範](#markdown-格式規範)
4. [進階功能](#進階功能)
5. [實用範例](#實用範例)
6. [常見問題](#常見問題)
7. [最佳實踐](#最佳實踐)

---

## 功能概述

### 什麼是 Markdown 自訂指令？

Markdown 自訂指令功能允許你使用簡單的 Markdown 檔案定義自己的命令，無需編寫 Python 程式碼。這些命令會自動載入到 CodeGemini/ChatGemini 系統中，讓你能夠：

- 🎯 **快速建立**：用 Markdown 編寫，無需程式設計經驗
- 🔄 **即時生效**：支援 Hot Reload，修改後自動重新載入
- 🛡️ **安全可靠**：內建衝突檢測與錯誤處理
- 🎨 **功能豐富**：支援變數、條件、迴圈等模板語法
- 📦 **易於分享**：Markdown 檔案可輕鬆分享給其他人

### 核心功能

| 功能 | 說明 |
|------|------|
| 自動掃描 | 自動掃描 `~/.chatgemini/commands/` 目錄下的所有 `.md` 檔案 |
| Markdown 解析 | 解析 YAML Frontmatter + 模板內容 |
| 命令註冊 | 自動註冊到 CommandRegistry |
| 衝突檢測 | 檢測與內建命令或其他自訂命令的名稱衝突 |
| Hot Reload | 檔案修改後自動重新載入 |
| 錯誤處理 | 完善的錯誤提示與記錄 |

---

## 快速開始

### 1. 建立命令目錄

```bash
mkdir -p ~/.chatgemini/commands
```

### 2. 創建第一個自訂命令

建立檔案：`~/.chatgemini/commands/hello.md`

```markdown
---
name: hello
description: 簡單的問候命令
type: template
parameters:
  - name
tags:
  - greeting
author: Your Name
version: 1.0.0
examples:
  - "hello name='世界'"
---

你好，{name}！

今天過得如何？
```

### 3. 在 Python 中使用

```python
from CodeGemini.commands import MarkdownCommandLoader, CommandRegistry

# 建立註冊表
registry = CommandRegistry()

# 建立 Markdown 載入器
loader = MarkdownCommandLoader(registry=registry)

# 掃描並載入所有 Markdown 命令
loader.scan_and_load()

# 執行命令
result = registry.execute_command("hello", args={"name": "Alice"})

if result.success:
    print(result.output)
    # 輸出：你好，Alice！
    #      今天過得如何？
```

---

## Markdown 格式規範

### 基本結構

Markdown 命令檔案由兩部分組成：

1. **YAML Frontmatter**（元資料）
2. **命令模板**（內容）

```markdown
---
# 這是 YAML Frontmatter
name: command-name
description: 命令描述
type: template
parameters:
  - param1
  - param2
---

這是命令模板內容
可以使用 {param1} 和 {param2}
```

### Frontmatter 欄位說明

| 欄位 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `name` | ✅ | 命令名稱（唯一識別符） | `my-command` |
| `description` | ✅ | 命令描述 | `這是我的自訂命令` |
| `type` | ❌ | 命令類型 | `template`（預設） |
| `parameters` | ❌ | 參數列表 | `- param1`<br>`- param2` |
| `tags` | ❌ | 標籤（用於分類） | `- coding`<br>`- python` |
| `author` | ❌ | 作者名稱 | `Your Name` |
| `version` | ❌ | 版本號 | `1.0.0` |
| `examples` | ❌ | 使用範例 | `- "my-command param1='value'"` |

### 模板語法

#### 1. 變數插值

```markdown
{variable_name}
```

**範例**：
```markdown
你好，{name}！
```

#### 2. 預設值

```markdown
{variable_name|default:"預設值"}
```

**範例**：
```markdown
使用語言：{language|default:"Python"}
```

#### 3. 條件判斷

```markdown
{% if condition %}
  條件為真時顯示
{% endif %}
```

**範例**：
```markdown
{% if include_tests %}
請包含單元測試。
{% endif %}
```

#### 4. If-Else

```markdown
{% if condition %}
  條件為真
{% else %}
  條件為假
{% endif %}
```

**範例**：
```markdown
{% if premium %}
您是高級會員
{% else %}
您是普通會員
{% endif %}
```

#### 5. 迴圈

```markdown
{% for item in list %}
  - {item}
{% endfor %}
```

**範例**：
```markdown
需求列表：
{% for req in requirements %}
  - {req}
{% endfor %}
```

---

## 進階功能

### 1. Hot Reload（熱重載）

Markdown Loader 支援檔案變更自動重新載入。

#### 方式 1：手動檢查

```python
# 只載入變更的檔案
loader.scan_and_load()
```

#### 方式 2：自動監視

```python
# 每 5 秒檢查一次
loader.watch_and_reload(check_interval=5)
```

#### 方式 3：重載單一命令

```python
loader.reload_command("my-command")
```

### 2. 衝突檢測

系統會自動檢測：

- ❌ **內建命令衝突**：無法覆蓋內建命令（如 `test`, `optimize` 等）
- ⚠️ **重複定義**：多個檔案定義同名命令時發出警告

**範例輸出**：
```
✗ 衝突：'test' 與內建命令衝突，已跳過
⚠ 警告：'my-cmd' 重複定義於多個檔案：
  - ~/.chatgemini/commands/cmd1.md
  - ~/.chatgemini/commands/cmd2.md
  將使用第一個定義
```

### 3. 統計與監控

```python
# 取得載入統計
stats = loader.get_statistics()

print(f"總檔案數：{stats['total_files']}")
print(f"有效檔案：{stats['valid_files']}")
print(f"無效檔案：{stats['invalid_files']}")
print(f"已載入命令：{stats['loaded_commands']}")
```

### 4. 顯示已載入命令

```python
# 顯示已載入命令的詳細資訊
loader.show_loaded_commands()
```

**輸出範例**：
```
已載入的 Markdown 命令（共 4 個）：
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ 命令名稱     ┃ 檔案名稱       ┃ 狀態  ┃ 修改時間          ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ hello        │ hello.md       │ ✓ 有效│ 2025-10-25 10:30:00│
│ api-design   │ api-design.md  │ ✓ 有效│ 2025-10-25 10:31:00│
└──────────────┴────────────────┴───────┴────────────────────┘
```

---

## 實用範例

### 範例 1：程式碼審查命令

檔案：`~/.chatgemini/commands/code-review-zh.md`

```markdown
---
name: code-review-zh
description: 繁體中文程式碼審查
type: template
parameters:
  - code
  - language
tags:
  - code-review
  - quality
author: ChatGemini
version: 1.0.0
---

請審查以下 {language} 程式碼：

```{language}
{code}
```

請檢查：
1. 安全性
2. 效能
3. 可讀性
4. 最佳實踐

{% if strict %}
請使用嚴格標準進行審查。
{% endif %}
```

**使用**：
```python
result = registry.execute_command(
    "code-review-zh",
    args={
        "code": "def hello(): print('Hello')",
        "language": "Python",
        "strict": True
    }
)
```

### 範例 2：API 設計助手

檔案：`~/.chatgemini/commands/api-design.md`

```markdown
---
name: api-design
description: RESTful API 設計助手
type: template
parameters:
  - resource
  - description
tags:
  - api
  - backend
---

請設計 RESTful API：

**資源**：{resource}
**說明**：{description}

請提供：
1. 端點設計
2. 資料模型
3. 錯誤處理
4. API 文檔

{% if include_auth %}
請包含認證機制設計。
{% endif %}
```

### 範例 3：Commit Message 生成器

檔案：`~/.chatgemini/commands/commit-msg.md`

```markdown
---
name: commit-msg
description: Git Commit Message 生成器
type: template
parameters:
  - changes
tags:
  - git
  - version-control
---

根據以下變更生成 Conventional Commits 格式的訊息：

{changes}

{% if type %}
類型：{type}
{% endif %}

請遵循 Conventional Commits 規範。
```

---

## 常見問題

### Q1: 命令檔案應該放在哪裡？

**A**: 預設目錄是 `~/.chatgemini/commands/`

你也可以自訂目錄：
```python
loader = MarkdownCommandLoader(commands_dir="/custom/path")
```

### Q2: 為什麼我的命令沒有被載入？

**可能原因**：

1. **檔案格式錯誤**
   - 檢查 Frontmatter 是否正確（`---` 包圍）
   - 檢查 YAML 語法是否正確

2. **缺少必要欄位**
   - 確認有 `name` 和 `description` 欄位

3. **命令名稱衝突**
   - 檢查是否與內建命令同名
   - 檢查是否有其他檔案定義了同名命令

4. **檔案副檔名錯誤**
   - 必須是 `.md` 檔案

**除錯方式**：
```python
# 不使用靜默模式，查看詳細輸出
loader.scan_and_load(silent=False)

# 查看載入統計
stats = loader.get_statistics()
if stats['invalid_files'] > 0:
    loader.show_loaded_commands()  # 會顯示錯誤詳情
```

### Q3: 如何測試我的命令？

```python
# 1. 載入命令
loader.scan_and_load()

# 2. 檢查命令是否存在
command = registry.get_command("my-command")
if command:
    print(f"✓ 命令已載入：{command.name}")

    # 3. 查看命令詳情
    registry.show_command_details("my-command")

    # 4. 執行測試
    result = registry.execute_command(
        "my-command",
        args={"param": "test"}
    )

    if result.success:
        print("✓ 執行成功")
        print(result.output)
    else:
        print(f"✗ 執行失敗：{result.error_message}")
```

### Q4: Hot Reload 如何運作？

Hot Reload 透過檢查檔案修改時間實現：

1. 系統記錄每個檔案的最後載入時間
2. 再次掃描時比較檔案的修改時間
3. 如果檔案已被修改，則重新載入

**注意**：目前實作是輪詢式，每次呼叫 `scan_and_load()` 才會檢查。

若要自動監視：
```python
# 每 5 秒自動檢查一次
loader.watch_and_reload(check_interval=5)
```

### Q5: 可以在模板中使用 Markdown 格式嗎？

**可以！** 模板內容會原樣保留，包括 Markdown 格式：

```markdown
---
name: my-doc
description: 文檔生成器
parameters:
  - title
---

# {title}

## 概述

這是 **粗體** 和 *斜體* 文字。

### 程式碼範例

```python
def hello():
    print("Hello")
```

- 項目 1
- 項目 2
```

---

## 最佳實踐

### 1. 命名規範

- ✅ **使用小寫加連字號**：`my-command`
- ✅ **描述性命名**：`code-review-zh`, `api-design`
- ❌ **避免**：`myCommand`, `my_command`, `cmd1`

### 2. 檔案組織

```
~/.chatgemini/commands/
├── code-review-zh.md      # 程式碼審查
├── api-design.md          # API 設計
├── commit-msg.md          # Commit 訊息
├── algo-explain.md        # 演算法解釋
└── custom/                # 自訂子目錄（可選）
    ├── team-cmd1.md
    └── team-cmd2.md
```

**注意**：目前只掃描頂層目錄，不遞迴掃描子目錄。

### 3. 參數設計

- ✅ **必要參數放前面**：`parameters: [code, language, style]`
- ✅ **使用預設值**：`{language|default:"Python"}`
- ✅ **參數命名清晰**：`code` 而非 `c` 或 `input`

### 4. 文檔完整性

每個命令都應該包含：

```markdown
---
name: my-command
description: 清晰的一句話描述
type: template
parameters:
  - param1      # 必填參數
  - param2      # 必填參數
tags:
  - category1
  - category2
author: Your Name
version: 1.0.0
examples:
  - "my-command param1='value1' param2='value2'"
  - "my-command param1='example' param2='test' optional=true"
---
```

### 5. 模板設計

#### 清晰的結構

```markdown
# 主要任務說明

**輸入**：{input}
**目標**：{goal}

## 步驟 1：分析

請先分析...

## 步驟 2：實作

請實作...

## 步驟 3：驗證

請確認...
```

#### 善用條件與迴圈

```markdown
{% if detailed %}
## 詳細分析

請提供詳細的...
{% endif %}

{% if examples %}
## 範例

{% for example in examples %}
### 範例 {example}

請展示...
{% endfor %}
{% endif %}
```

### 6. 版本管理

建議使用 Git 管理你的自訂命令：

```bash
cd ~/.chatgemini/commands
git init
git add *.md
git commit -m "Initial custom commands"
```

### 7. 分享與協作

Markdown 命令檔案可以輕鬆分享：

```bash
# 分享給同事
cp ~/.chatgemini/commands/my-command.md /path/to/share/

# 或透過 Git
git clone https://github.com/team/chatgemini-commands.git ~/.chatgemini/commands
```

---

## 進階整合範例

### 整合到 ChatGemini 主程式

```python
from CodeGemini.commands import (
    MarkdownCommandLoader,
    CommandRegistry,
    BuiltinCommands
)

def initialize_commands():
    """初始化命令系統"""
    # 1. 建立註冊表
    registry = CommandRegistry()

    # 2. 註冊內建命令
    builtin_count = BuiltinCommands.register_all(registry)
    print(f"✓ 載入 {builtin_count} 個內建命令")

    # 3. 載入 Markdown 自訂命令
    loader = MarkdownCommandLoader(registry=registry)
    custom_count = loader.scan_and_load()
    print(f"✓ 載入 {custom_count} 個自訂命令")

    # 4. 顯示所有命令
    registry.show_commands_table()

    return registry, loader

# 使用
registry, loader = initialize_commands()

# 執行命令
result = registry.execute_command("my-command", args={...})
```

### 命令行介面整合

```python
import argparse

def main():
    parser = argparse.ArgumentParser(description='ChatGemini CLI')
    parser.add_argument('command', help='命令名稱')
    parser.add_argument('--reload', action='store_true', help='重新載入命令')

    args = parser.parse_args()

    # 初始化
    registry, loader = initialize_commands()

    # 重新載入
    if args.reload:
        loader.scan_and_load(force_reload=True)
        print("✓ 命令已重新載入")

    # 執行命令
    # ... (根據 args.command 執行)

if __name__ == "__main__":
    main()
```

---

## 技術細節

### 支援的 YAML 語法

Frontmatter 使用標準 YAML 語法：

```yaml
# 字串
name: my-command
description: "描述文字"

# 列表
parameters:
  - param1
  - param2

tags: [tag1, tag2, tag3]  # 簡寫

# 巢狀結構（不建議，模板引擎目前不支援）
metadata:
  author: Name
  email: email@example.com
```

### 模板引擎限制

目前的模板引擎支援：
- ✅ 簡單變數插值
- ✅ 預設值
- ✅ If/If-Else 條件
- ✅ For 迴圈
- ❌ 複雜運算式（如 `{% if count > 5 %}`）
- ❌ 巢狀迴圈
- ❌ 過濾器（如 `{name|upper}`，僅支援 `default`）

### 效能考量

- **檔案掃描**：O(n)，n 為 .md 檔案數量
- **Hot Reload**：只重載變更的檔案
- **記憶體使用**：每個命令約 1-2 KB

建議：
- 不要在同一目錄放置過多命令（建議 < 100 個）
- Hot Reload 檢查間隔不要太短（建議 ≥ 5 秒）

---

## 故障排除

### 問題：YAML 解析錯誤

**錯誤訊息**：
```
✗ 錯誤：my-command.md - YAML 解析錯誤：...
```

**解決方式**：
1. 檢查 Frontmatter 是否正確包圍在 `---` 之間
2. 檢查 YAML 縮排（必須使用空格，不可使用 Tab）
3. 檢查特殊字元是否需要引號

### 問題：命令無法執行

**檢查清單**：
1. 命令是否已載入？
   ```python
   command = registry.get_command("my-command")
   print(command)  # 應該不為 None
   ```

2. 參數是否正確？
   ```python
   print(command.parameters)  # 查看必要參數
   ```

3. 執行結果是什麼？
   ```python
   result = registry.execute_command("my-command", args={...})
   if not result.success:
       print(f"錯誤：{result.error_message}")
   ```

---

## 相關資源

- **專案文檔**：`/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/`
- **測試腳本**：`CodeGemini/tests/test_markdown_loader.py`
- **範例命令**：`~/.chatgemini/commands/`

---

## 更新日誌

### v1.0.0 (2025-10-25)

- ✨ 首次發布
- ✨ 支援 Markdown 格式命令定義
- ✨ 支援 Hot Reload
- ✨ 支援衝突檢測
- ✨ 支援完整的模板語法（變數、條件、迴圈）
- 📝 完整的使用指南與範例

---

**撰寫者**：Claude Code (Sonnet 4.5)
**日期**：2025-10-25
**版本**：1.0.0
