#!/usr/bin/env python3
"""
CodeGemini 安全掃描器 - SQL 注入與 XSS 檢測

此模組提供自動化安全漏洞檢測功能，包括：
- SQL 注入漏洞檢測
- XSS（跨站腳本攻擊）漏洞檢測
- 兩階段驗證（正則表達式 + Gemini 智能分析）
- 自動修復建議生成

作者: CodeGemini
版本: 1.0.0
日期: 2025-11-01
"""

import re
import os
import json
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path

# 嘗試導入 Gemini
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# 嘗試導入 Rich（用於美化輸出）
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    # 提供簡單的 Console fallback
    class Console:
        def print(self, *args, **kwargs):
            text = ' '.join(str(arg) for arg in args)
            # 移除 Rich 標記
            text = re.sub(r'\[.*?\]', '', text)
            print(text)


class VulnerabilityType(Enum):
    """漏洞類型枚舉"""
    SQL_INJECTION = "SQL 注入"
    XSS = "跨站腳本攻擊 (XSS)"
    COMMAND_INJECTION = "命令注入"
    PATH_TRAVERSAL = "路徑遍歷"
    UNSAFE_DESERIALIZATION = "不安全的反序列化"


class SeverityLevel(Enum):
    """嚴重度等級"""
    CRITICAL = "嚴重"
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"
    INFO = "資訊"


@dataclass
class SecurityIssue:
    """安全問題數據類別"""
    type: VulnerabilityType
    severity: SeverityLevel
    line_number: int
    line_content: str
    matched_pattern: str
    description: str
    fix_suggestion: str
    code_snippet: str
    is_verified: bool = False
    verification_result: Optional[str] = None
    fix_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        data = asdict(self)
        data['type'] = self.type.value
        data['severity'] = self.severity.value
        return data


class SecurityScanner:
    """安全掃描器核心類別"""

    # SQL 注入檢測模式
    SQL_INJECTION_PATTERNS = {
        'string_formatting': {
            'pattern': r'(?:execute|executemany|cursor\.execute)\s*\(\s*["\'].*%.*["\']',
            'severity': SeverityLevel.HIGH,
            'description': '使用字串格式化 (%) 構建 SQL 查詢可能導致 SQL 注入',
        },
        'string_concatenation': {
            'pattern': r'(?:execute|executemany|cursor\.execute)\s*\([^)]*\+[^)]*\)',
            'severity': SeverityLevel.HIGH,
            'description': '使用字串拼接 (+) 構建 SQL 查詢可能導致 SQL 注入',
        },
        'fstring_sql': {
            'pattern': r'(?:execute|executemany|cursor\.execute)\s*\(\s*f["\']',
            'severity': SeverityLevel.HIGH,
            'description': '使用 f-string 構建 SQL 查詢可能導致 SQL 注入',
        },
        'django_raw': {
            'pattern': r'\.raw\s*\(\s*["\'].*%.*["\']',
            'severity': SeverityLevel.MEDIUM,
            'description': 'Django raw SQL 使用字串格式化可能導致 SQL 注入',
        },
        'format_method': {
            'pattern': r'(?:execute|cursor\.execute)\s*\([^)]*\.format\(',
            'severity': SeverityLevel.HIGH,
            'description': '使用 .format() 構建 SQL 查詢可能導致 SQL 注入',
        },
    }

    # XSS 檢測模式
    XSS_PATTERNS = {
        'innerHTML': {
            'pattern': r'\.innerHTML\s*=\s*[^;]+',
            'severity': SeverityLevel.HIGH,
            'description': '直接設置 innerHTML 可能導致 XSS 攻擊',
        },
        'dangerouslySetInnerHTML': {
            'pattern': r'dangerouslySetInnerHTML\s*=\s*\{\{',
            'severity': SeverityLevel.HIGH,
            'description': 'React dangerouslySetInnerHTML 可能導致 XSS 攻擊',
        },
        'document_write': {
            'pattern': r'document\.write\s*\(',
            'severity': SeverityLevel.MEDIUM,
            'description': 'document.write() 可能導致 XSS 攻擊',
        },
        'eval': {
            'pattern': r'eval\s*\(',
            'severity': SeverityLevel.CRITICAL,
            'description': 'eval() 執行動態程式碼可能導致程式碼注入',
        },
        'outerHTML': {
            'pattern': r'\.outerHTML\s*=\s*[^;]+',
            'severity': SeverityLevel.HIGH,
            'description': '直接設置 outerHTML 可能導致 XSS 攻擊',
        },
        'insertAdjacentHTML': {
            'pattern': r'\.insertAdjacentHTML\s*\(',
            'severity': SeverityLevel.MEDIUM,
            'description': 'insertAdjacentHTML 可能導致 XSS 攻擊',
        },
    }

    # 安全模式排除（減少誤報）
    SAFE_PATTERNS = [
        r'#.*(?:test|example|demo)',  # 註解中的測試程式碼
        r'""".*?"""',  # Docstring
        r"'''.*?'''",  # Docstring
        r'execute\s*\([^)]*,\s*\[',  # 參數化查詢（有參數列表）
        r'execute\s*\([^)]*,\s*\(',  # 參數化查詢（有參數元組）
        r'execute\s*\([^)]*,\s*{',  # 參數化查詢（有參數字典）
    ]

    def __init__(self, file_path: str, use_gemini_verification: bool = True):
        """
        初始化安全掃描器

        Args:
            file_path: 要掃描的檔案路徑
            use_gemini_verification: 是否使用 Gemini 進行智能驗證
        """
        self.file_path = file_path
        self.use_gemini_verification = use_gemini_verification and HAS_GEMINI
        self.issues: List[SecurityIssue] = []
        self.code_lines: List[str] = []
        self.language = self._detect_language()

        # 初始化 Gemini
        if self.use_gemini_verification:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("警告: 未找到 GEMINI_API_KEY 環境變數，將停用 Gemini 驗證")
                self.use_gemini_verification = False
            else:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash')

    def _detect_language(self) -> str:
        """偵測檔案語言"""
        ext = Path(self.file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.php': 'php',
            '.rb': 'ruby',
        }
        return language_map.get(ext, 'unknown')

    def _load_file(self) -> bool:
        """載入檔案內容"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.code_lines = f.readlines()
            return True
        except Exception as e:
            print(f"錯誤: 無法讀取檔案 {self.file_path}: {e}")
            return False

    def _is_safe_context(self, line: str) -> bool:
        """檢查是否為安全上下文（減少誤報）"""
        for pattern in self.SAFE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE | re.DOTALL):
                return True
        return False

    def _get_code_snippet(self, line_number: int, context: int = 2) -> str:
        """獲取程式碼片段（包含上下文）"""
        start = max(0, line_number - context - 1)
        end = min(len(self.code_lines), line_number + context)
        snippet_lines = []
        for i in range(start, end):
            prefix = '→ ' if i == line_number - 1 else '  '
            snippet_lines.append(f"{prefix}{i+1:4d} | {self.code_lines[i].rstrip()}")
        return '\n'.join(snippet_lines)

    def _scan_sql_injection(self):
        """掃描 SQL 注入漏洞"""
        if self.language not in ['python', 'java', 'php', 'ruby']:
            return

        for line_num, line in enumerate(self.code_lines, 1):
            # 跳過安全上下文
            if self._is_safe_context(line):
                continue

            for pattern_name, pattern_info in self.SQL_INJECTION_PATTERNS.items():
                if re.search(pattern_info['pattern'], line):
                    issue = SecurityIssue(
                        type=VulnerabilityType.SQL_INJECTION,
                        severity=pattern_info['severity'],
                        line_number=line_num,
                        line_content=line.strip(),
                        matched_pattern=pattern_name,
                        description=pattern_info['description'],
                        fix_suggestion=self._get_sql_fix_suggestion(pattern_name),
                        code_snippet=self._get_code_snippet(line_num),
                    )
                    self.issues.append(issue)

    def _scan_xss(self):
        """掃描 XSS 漏洞"""
        if self.language not in ['javascript', 'typescript', 'python', 'php']:
            return

        for line_num, line in enumerate(self.code_lines, 1):
            # 跳過安全上下文
            if self._is_safe_context(line):
                continue

            for pattern_name, pattern_info in self.XSS_PATTERNS.items():
                if re.search(pattern_info['pattern'], line):
                    issue = SecurityIssue(
                        type=VulnerabilityType.XSS,
                        severity=pattern_info['severity'],
                        line_number=line_num,
                        line_content=line.strip(),
                        matched_pattern=pattern_name,
                        description=pattern_info['description'],
                        fix_suggestion=self._get_xss_fix_suggestion(pattern_name),
                        code_snippet=self._get_code_snippet(line_num),
                    )
                    self.issues.append(issue)

    def _get_sql_fix_suggestion(self, pattern_name: str) -> str:
        """獲取 SQL 注入修復建議"""
        suggestions = {
            'string_formatting': """使用參數化查詢：
  # 不安全
  cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)

  # 安全
  cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))""",

            'string_concatenation': """使用參數化查詢：
  # 不安全
  cursor.execute("SELECT * FROM users WHERE name = '" + name + "'")

  # 安全
  cursor.execute("SELECT * FROM users WHERE name = %s", (name,))""",

            'fstring_sql': """使用參數化查詢：
  # 不安全
  cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

  # 安全
  cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))""",

            'django_raw': """使用 Django ORM 參數化查詢：
  # 不安全
  User.objects.raw("SELECT * FROM users WHERE id = %s" % user_id)

  # 安全
  User.objects.raw("SELECT * FROM users WHERE id = %s", [user_id])""",

            'format_method': """使用參數化查詢：
  # 不安全
  cursor.execute("SELECT * FROM users WHERE name = '{}'".format(name))

  # 安全
  cursor.execute("SELECT * FROM users WHERE name = %s", (name,))""",
        }
        return suggestions.get(pattern_name, "使用參數化查詢來防止 SQL 注入")

    def _get_xss_fix_suggestion(self, pattern_name: str) -> str:
        """獲取 XSS 修復建議"""
        suggestions = {
            'innerHTML': """使用安全的 API：
  // 不安全
  element.innerHTML = userInput;

  // 安全
  element.textContent = userInput;
  // 或使用 DOMPurify 清理
  element.innerHTML = DOMPurify.sanitize(userInput);""",

            'dangerouslySetInnerHTML': """使用安全的替代方案：
  // 不安全
  <div dangerouslySetInnerHTML={{__html: userInput}} />

  // 安全
  <div>{userInput}</div>
  // 或使用 DOMPurify
  <div dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(userInput)}} />""",

            'document_write': """使用安全的 DOM 操作：
  // 不安全
  document.write(userInput);

  // 安全
  const div = document.createElement('div');
  div.textContent = userInput;
  document.body.appendChild(div);""",

            'eval': """避免使用 eval()：
  // 不安全
  eval(userInput);

  // 安全
  // 使用 JSON.parse() 處理 JSON 資料
  const data = JSON.parse(jsonString);
  // 或使用 Function 構造器（仍需謹慎）
  const fn = new Function('return ' + expression);""",

            'outerHTML': """使用 textContent 或 createElement：
  // 不安全
  element.outerHTML = userInput;

  // 安全
  element.textContent = userInput;""",

            'insertAdjacentHTML': """使用安全的 DOM 操作：
  // 不安全
  element.insertAdjacentHTML('beforeend', userInput);

  // 安全
  const div = document.createElement('div');
  div.textContent = userInput;
  element.appendChild(div);""",
        }
        return suggestions.get(pattern_name, "避免直接插入未經清理的使用者輸入")

    def _gemini_verify_issue(self, issue: SecurityIssue) -> bool:
        """使用 Gemini 驗證漏洞是否為真"""
        if not self.use_gemini_verification:
            return True

        prompt = f"""你是一個安全專家。請分析以下程式碼片段，判斷是否存在真正的 {issue.type.value} 漏洞。

程式語言: {self.language}
漏洞類型: {issue.type.value}
檢測模式: {issue.matched_pattern}
程式碼片段:
```
{issue.code_snippet}
```

問題行: {issue.line_content}

請回答：
1. 這是否為真正的安全漏洞？（是/否）
2. 理由是什麼？
3. 嚴重程度評估（嚴重/高/中/低）

請以 JSON 格式回答：
{{
    "is_vulnerable": true/false,
    "reason": "理由說明",
    "severity": "嚴重/高/中/低"
}}
"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # 提取 JSON
            json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                issue.is_verified = True
                issue.verification_result = result.get('reason', '')

                # 更新嚴重度
                severity_map = {
                    '嚴重': SeverityLevel.CRITICAL,
                    '高': SeverityLevel.HIGH,
                    '中': SeverityLevel.MEDIUM,
                    '低': SeverityLevel.LOW,
                }
                gemini_severity = result.get('severity', '')
                if gemini_severity in severity_map:
                    issue.severity = severity_map[gemini_severity]

                return result.get('is_vulnerable', True)

        except Exception as e:
            print(f"Gemini 驗證失敗: {e}")

        return True  # 預設保留問題

    def _gemini_generate_fix(self, issue: SecurityIssue) -> Optional[str]:
        """使用 Gemini 生成客製化修復程式碼"""
        if not self.use_gemini_verification:
            return None

        prompt = f"""你是一個安全專家。請為以下 {issue.type.value} 漏洞生成修復後的安全程式碼。

程式語言: {self.language}
原始程式碼:
```{self.language}
{issue.line_content}
```

問題描述: {issue.description}

請直接提供修復後的程式碼（僅程式碼，不需要解釋）：
"""

        try:
            response = self.model.generate_content(prompt)
            fix_code = response.text.strip()
            # 移除 markdown 程式碼區塊標記
            fix_code = re.sub(r'```\w*\n', '', fix_code)
            fix_code = re.sub(r'```$', '', fix_code)
            return fix_code.strip()
        except Exception as e:
            print(f"生成修復程式碼失敗: {e}")
            return None

    def scan(self, vulnerability_types: List[str] = None) -> List[SecurityIssue]:
        """
        執行安全掃描

        Args:
            vulnerability_types: 要掃描的漏洞類型列表 ['sql', 'xss', 'all']

        Returns:
            發現的安全問題列表
        """
        if not self._load_file():
            return []

        if vulnerability_types is None or 'all' in vulnerability_types:
            vulnerability_types = ['sql', 'xss']

        # 階段 1: 正則表達式掃描
        if 'sql' in vulnerability_types:
            self._scan_sql_injection()

        if 'xss' in vulnerability_types:
            self._scan_xss()

        # 階段 2: Gemini 驗證
        if self.use_gemini_verification:
            verified_issues = []
            for issue in self.issues:
                if self._gemini_verify_issue(issue):
                    verified_issues.append(issue)
            self.issues = verified_issues

        return self.issues

    def generate_fixes(self):
        """為所有問題生成修復程式碼"""
        for issue in self.issues:
            if not issue.fix_code:
                issue.fix_code = self._gemini_generate_fix(issue)

    def generate_report(self, output_format: str = 'text') -> str:
        """
        生成掃描報告

        Args:
            output_format: 輸出格式 ('text', 'json', 'markdown')

        Returns:
            格式化的報告字串
        """
        if output_format == 'json':
            return self._generate_json_report()
        elif output_format == 'markdown':
            return self._generate_markdown_report()
        else:
            return self._generate_text_report()

    def _generate_json_report(self) -> str:
        """生成 JSON 格式報告"""
        report = {
            'file': self.file_path,
            'language': self.language,
            'total_issues': len(self.issues),
            'issues_by_severity': self._get_severity_stats(),
            'issues': [issue.to_dict() for issue in self.issues],
        }
        return json.dumps(report, ensure_ascii=False, indent=2)

    def _generate_markdown_report(self) -> str:
        """生成 Markdown 格式報告"""
        lines = [
            f"# 安全掃描報告",
            f"",
            f"**檔案**: `{self.file_path}`",
            f"**語言**: {self.language}",
            f"**發現問題**: {len(self.issues)} 個",
            f"",
            f"## 問題統計",
            f"",
        ]

        stats = self._get_severity_stats()
        for severity, count in stats.items():
            lines.append(f"- **{severity}**: {count} 個")

        lines.append("")
        lines.append("## 詳細問題")
        lines.append("")

        for i, issue in enumerate(self.issues, 1):
            lines.extend([
                f"### {i}. {issue.type.value} - {issue.severity.value}",
                f"",
                f"**位置**: 第 {issue.line_number} 行",
                f"**程式碼**: `{issue.line_content}`",
                f"**描述**: {issue.description}",
                f"",
                f"**修復建議**:",
                f"```",
                issue.fix_suggestion,
                f"```",
                f"",
            ])

            if issue.verification_result:
                lines.extend([
                    f"**Gemini 驗證**: {issue.verification_result}",
                    f"",
                ])

        return '\n'.join(lines)

    def _generate_text_report(self) -> str:
        """生成純文字格式報告"""
        console = Console()

        # 標題
        lines = []
        lines.append("=" * 80)
        lines.append(f"🔒 安全掃描報告")
        lines.append("=" * 80)
        lines.append(f"檔案: {self.file_path}")
        lines.append(f"語言: {self.language}")
        lines.append(f"發現問題: {len(self.issues)} 個")
        lines.append("")

        # 統計
        stats = self._get_severity_stats()
        lines.append("📊 問題統計:")
        for severity, count in stats.items():
            if count > 0:
                lines.append(f"  {severity}: {count} 個")
        lines.append("")

        # 詳細問題
        lines.append("📋 詳細問題:")
        lines.append("")

        for i, issue in enumerate(self.issues, 1):
            severity_icon = {
                SeverityLevel.CRITICAL: '🔴',
                SeverityLevel.HIGH: '🟠',
                SeverityLevel.MEDIUM: '🟡',
                SeverityLevel.LOW: '🟢',
                SeverityLevel.INFO: '🔵',
            }.get(issue.severity, '⚪')

            lines.append(f"{i}. {severity_icon} {issue.type.value} - {issue.severity.value}")
            lines.append(f"   位置: 第 {issue.line_number} 行")
            lines.append(f"   內容: {issue.line_content}")
            lines.append(f"   描述: {issue.description}")
            lines.append("")
            lines.append("   💡 修復建議:")
            for line in issue.fix_suggestion.split('\n'):
                lines.append(f"     {line}")
            lines.append("")

            if issue.verification_result:
                lines.append(f"   🤖 Gemini 驗證: {issue.verification_result}")
                lines.append("")

            if issue.fix_code:
                lines.append("   ✅ 修復程式碼:")
                lines.append(f"     {issue.fix_code}")
                lines.append("")

            lines.append("   " + "-" * 76)
            lines.append("")

        lines.append("=" * 80)

        return '\n'.join(lines)

    def _get_severity_stats(self) -> Dict[str, int]:
        """獲取嚴重度統計"""
        stats = {
            '嚴重': 0,
            '高': 0,
            '中': 0,
            '低': 0,
            '資訊': 0,
        }
        for issue in self.issues:
            stats[issue.severity.value] += 1
        return stats


def main():
    """CLI 主程式"""
    parser = argparse.ArgumentParser(
        description='CodeGemini 安全掃描器 - SQL 注入與 XSS 檢測'
    )
    parser.add_argument('file', help='要掃描的檔案路徑')
    parser.add_argument(
        '--type',
        choices=['sql', 'xss', 'all'],
        default='all',
        help='要掃描的漏洞類型 (預設: all)'
    )
    parser.add_argument(
        '--output-format',
        choices=['text', 'json', 'markdown'],
        default='text',
        help='輸出格式 (預設: text)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='使用 Gemini 生成修復程式碼'
    )
    parser.add_argument(
        '--no-gemini',
        action='store_true',
        help='停用 Gemini 智能驗證（僅使用正則表達式）'
    )
    parser.add_argument(
        '--output',
        help='輸出報告到檔案'
    )

    args = parser.parse_args()

    # 檢查檔案是否存在
    if not os.path.exists(args.file):
        print(f"錯誤: 檔案不存在 - {args.file}")
        return 1

    # 初始化掃描器
    print(f"🔒 CodeGemini 安全掃描器")
    print()

    scanner = SecurityScanner(
        args.file,
        use_gemini_verification=not args.no_gemini
    )

    # 執行掃描
    vulnerability_types = [args.type] if args.type != 'all' else ['sql', 'xss']
    print(f"掃描檔案: {args.file}")
    print(f"漏洞類型: {', '.join(vulnerability_types)}")
    print(f"Gemini 驗證: {'啟用' if scanner.use_gemini_verification else '停用'}")
    print()

    issues = scanner.scan(vulnerability_types)

    # 生成修復程式碼
    if args.fix and issues:
        print("生成修復程式碼...")
        scanner.generate_fixes()
        print()

    # 生成報告
    report = scanner.generate_report(args.output_format)

    # 輸出報告
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"報告已儲存至: {args.output}")
    else:
        print(report)

    # 回傳錯誤碼（如果發現問題）
    return 1 if issues else 0


if __name__ == '__main__':
    exit(main())
