#!/usr/bin/env python3
"""
CodeGemini Template Engine Module
模板引擎 - 變數插值與邏輯處理

此模組負責：
1. 解析模板
2. 變數插值
3. 條件邏輯
4. 迴圈處理
"""
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from rich.console import Console
from utils.i18n import safe_t

console = Console()


@dataclass
class Template:
    """模板資料結構"""
    raw_template: str                              # 原始模板
    variables: List[str] = field(default_factory=list)  # 變數列表
    has_conditionals: bool = False                 # 是否有條件
    has_loops: bool = False                        # 是否有迴圈


class TemplateEngine:
    """模板引擎"""

    # 變數插值：{variable_name}
    VAR_PATTERN = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')

    # 預設值：{variable|default:"value"}
    VAR_DEFAULT_PATTERN = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\|default:"([^"]+)"\}')

    # 條件：{% if condition %}...{% endif %}
    IF_PATTERN = re.compile(r'\{%\s*if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}(.*?)\{%\s*endif\s*%\}', re.DOTALL)

    # else：{% if condition %}...{% else %}...{% endif %}
    IF_ELSE_PATTERN = re.compile(
        r'\{%\s*if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}',
        re.DOTALL
    )

    # 迴圈：{% for item in list %}...{% endfor %}
    FOR_PATTERN = re.compile(
        r'\{%\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}(.*?)\{%\s*endfor\s*%\}',
        re.DOTALL
    )

    def __init__(self):
        """初始化模板引擎"""
        pass

    def parse_template(self, template_str: str) -> Template:
        """
        解析模板

        Args:
            template_str: 模板字串

        Returns:
            Template: 模板物件
        """
        # 提取變數
        variables = []

        # 從簡單變數提取
        for match in self.VAR_PATTERN.finditer(template_str):
            var_name = match.group(1)
            if var_name not in variables:
                variables.append(var_name)

        # 從預設值提取
        for match in self.VAR_DEFAULT_PATTERN.finditer(template_str):
            var_name = match.group(1)
            if var_name not in variables:
                variables.append(var_name)

        # 從條件提取
        for match in self.IF_PATTERN.finditer(template_str):
            var_name = match.group(1)
            if var_name not in variables:
                variables.append(var_name)

        # 從 if-else 提取
        for match in self.IF_ELSE_PATTERN.finditer(template_str):
            var_name = match.group(1)
            if var_name not in variables:
                variables.append(var_name)

        # 從迴圈提取
        for match in self.FOR_PATTERN.finditer(template_str):
            list_name = match.group(2)
            if list_name not in variables:
                variables.append(list_name)

        # 檢測是否有條件和迴圈
        has_conditionals = bool(self.IF_PATTERN.search(template_str)) or \
                          bool(self.IF_ELSE_PATTERN.search(template_str))
        has_loops = bool(self.FOR_PATTERN.search(template_str))

        return Template(
            raw_template=template_str,
            variables=variables,
            has_conditionals=has_conditionals,
            has_loops=has_loops
        )

    def render(self, template: Template, variables: Dict[str, Any]) -> str:
        """
        渲染模板

        Args:
            template: 模板物件
            variables: 變數字典

        Returns:
            str: 渲染後的字串
        """
        result = template.raw_template

        # 步驟 1：處理迴圈
        if template.has_loops:
            result = self._process_loops(result, variables)

        # 步驟 2：處理條件（if-else）
        if template.has_conditionals:
            result = self._process_conditionals(result, variables)

        # 步驟 3：處理預設值變數
        result = self._process_defaults(result, variables)

        # 步驟 4：處理簡單變數插值
        result = self._process_variables(result, variables)

        return result

    def _process_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """處理簡單變數插值"""
        def replace_var(match):
            var_name = match.group(1)
            value = variables.get(var_name, f"{{{var_name}}}")  # 未找到時保留原樣
            return str(value)

        return self.VAR_PATTERN.sub(replace_var, text)

    def _process_defaults(self, text: str, variables: Dict[str, Any]) -> str:
        """處理預設值"""
        def replace_default(match):
            var_name = match.group(1)
            default_value = match.group(2)

            if var_name in variables:
                return str(variables[var_name])
            else:
                return default_value

        return self.VAR_DEFAULT_PATTERN.sub(replace_default, text)

    def _process_conditionals(self, text: str, variables: Dict[str, Any]) -> str:
        """處理條件邏輯"""
        # 先處理 if-else
        def replace_if_else(match):
            var_name = match.group(1)
            if_content = match.group(2)
            else_content = match.group(3)

            # 判斷變數真假
            var_value = variables.get(var_name, False)

            if self._is_truthy(var_value):
                return if_content
            else:
                return else_content

        text = self.IF_ELSE_PATTERN.sub(replace_if_else, text)

        # 再處理單純的 if
        def replace_if(match):
            var_name = match.group(1)
            if_content = match.group(2)

            # 判斷變數真假
            var_value = variables.get(var_name, False)

            if self._is_truthy(var_value):
                return if_content
            else:
                return ""

        text = self.IF_PATTERN.sub(replace_if, text)

        return text

    def _process_loops(self, text: str, variables: Dict[str, Any]) -> str:
        """處理迴圈"""
        def replace_for(match):
            item_name = match.group(1)
            list_name = match.group(2)
            loop_content = match.group(3)

            # 取得列表
            items = variables.get(list_name, [])

            if not isinstance(items, list):
                console.print(f"[#B565D8]{safe_t('templates.not_list_warning', '警告：\'{name}\' 不是列表，迴圈將被跳過', name=list_name)}[/#B565D8]")
                return ""

            # 迭代生成內容
            results = []
            for item in items:
                # 建立臨時變數字典
                temp_vars = variables.copy()
                temp_vars[item_name] = item

                # 渲染迴圈內容
                rendered = loop_content

                # 簡單替換（迴圈內變數）
                rendered = rendered.replace(f"{{{item_name}}}", str(item))

                results.append(rendered)

            return "".join(results)

        return self.FOR_PATTERN.sub(replace_for, text)

    def _is_truthy(self, value: Any) -> bool:
        """判斷值是否為真"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.lower() not in ['', 'false', '0', 'no']
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return bool(value)

    def validate_variables(
        self,
        template: Template,
        variables: Dict[str, Any]
    ) -> bool:
        """
        驗證變數

        Args:
            template: 模板物件
            variables: 變數字典

        Returns:
            bool: 是否所有必要變數都已提供
        """
        missing = [v for v in template.variables if v not in variables]

        if missing:
            console.print(f"[#B565D8]{safe_t('templates.missing_variables', '警告：缺少變數：{vars}', vars=', '.join(missing))}[/#B565D8]")
            return False

        return True

    def escape_html(self, text: str) -> str:
        """HTML 轉義（安全性功能）"""
        escape_dict = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
        }

        for char, escaped in escape_dict.items():
            text = text.replace(char, escaped)

        return text


class TemplateLibrary:
    """模板庫 - 管理預定義模板"""

    def __init__(self):
        """初始化模板庫"""
        self.templates: Dict[str, str] = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self):
        """載入內建模板"""
        # Python 函數模板
        self.templates['python_function'] = """請生成一個 Python 函數：

函數名稱：{function_name}
功能描述：{description}
參數：{parameters|default:"無"}
返回值：{return_type|default:"無"}

{% if include_docstring %}請包含完整的文檔字串{% endif %}
{% if include_tests %}請包含單元測試{% endif %}
"""

        # React 元件模板
        self.templates['react_component'] = """請生成一個 React 元件：

元件名稱：{component_name}
功能描述：{description}
{% if props %}Props：
{% for prop in props %}  - {prop}
{% endfor %}{% endif %}

{% if use_typescript %}請使用 TypeScript{% endif %}
{% if use_hooks %}請使用 React Hooks{% endif %}
"""

        # 測試案例模板
        self.templates['test_case'] = """請為以下功能生成測試案例：

測試目標：{target}
測試框架：{framework|default:"pytest"}

{% if test_scenarios %}測試場景：
{% for scenario in test_scenarios %}  - {scenario}
{% endfor %}{% endif %}
"""

        # 文檔模板
        self.templates['documentation'] = """請為以下項目生成文檔：

項目名稱：{project_name}
項目描述：{description}

{% if include_installation %}請包含安裝指南{% endif %}
{% if include_usage %}請包含使用範例{% endif %}
{% if include_api %}請包含 API 參考{% endif %}
"""

    def get_template(self, name: str) -> Optional[str]:
        """取得模板"""
        return self.templates.get(name)

    def add_template(self, name: str, template: str):
        """新增模板"""
        self.templates[name] = template

    def list_templates(self) -> List[str]:
        """列出所有模板"""
        return list(self.templates.keys())


def main():
    """測試用主程式"""
    console.print(f"[bold #B565D8]{safe_t('templates.test_title', 'CodeGemini Template Engine 測試')}[/bold #B565D8]\n")

    engine = TemplateEngine()

    # 測試 1：簡單變數插值
    console.print(f"[bold]{safe_t('templates.test1', '測試 1：簡單變數插值')}[/bold]")
    template1 = engine.parse_template("你好，{name}！今天是 {day}。")
    result1 = engine.render(template1, {"name": "Saki", "day": "星期一"})
    console.print(f"{safe_t('templates.result', '結果')}：{result1}\n")

    # 測試 2：預設值
    console.print(f"[bold]{safe_t('templates.test2', '測試 2：預設值')}[/bold]")
    template2 = engine.parse_template("語言：{language|default:\"Python\"}")
    result2 = engine.render(template2, {})
    console.print(f"{safe_t('templates.result', '結果')}：{result2}\n")

    # 測試 3：條件
    console.print(f"[bold]{safe_t('templates.test3', '測試 3：條件邏輯')}[/bold]")
    template3 = engine.parse_template("{% if premium %}您是高級會員{% else %}您是普通會員{% endif %}")
    result3_premium = engine.render(template3, {"premium": True})
    result3_normal = engine.render(template3, {"premium": False})
    console.print(f"{safe_t('templates.premium_member', '高級會員')}：{result3_premium}")
    console.print(f"{safe_t('templates.normal_member', '普通會員')}：{result3_normal}\n")

    # 測試 4：迴圈
    console.print(f"[bold]{safe_t('templates.test4', '測試 4：迴圈')}[/bold]")
    template4 = engine.parse_template("項目：\n{% for item in items %}  - {item}\n{% endfor %}")
    result4 = engine.render(template4, {"items": ["蘋果", "香蕉", "橘子"]})
    console.print(f"{safe_t('templates.result', '結果')}：\n{result4}\n")

    # 測試 5：模板庫
    console.print(f"[bold]{safe_t('templates.test5', '測試 5：模板庫')}[/bold]")
    library = TemplateLibrary()
    python_func_template = library.get_template('python_function')
    if python_func_template:
        template5 = engine.parse_template(python_func_template)
        result5 = engine.render(template5, {
            "function_name": "calculate_sum",
            "description": "計算兩個數字的和",
            "parameters": "a: int, b: int",
            "return_type": "int",
            "include_docstring": True,
            "include_tests": False
        })
        console.print(f"{safe_t('templates.result', '結果')}：\n{result5}")

    console.print(f"\n[bold green]✅ {safe_t('templates.all_tests_complete', '所有測試完成')}[/bold green]")


if __name__ == "__main__":
    main()
