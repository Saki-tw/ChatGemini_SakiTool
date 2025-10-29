#!/usr/bin/env python3
"""
Gemini 預防性驗證系統
在實際執行前檢查所有可能導致失敗的因素
"""
import os
import sys
import subprocess
import requests
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from rich.console import Console
from utils.i18n import safe_t
from rich.table import Table
from rich.panel import Panel
from google import genai
from google.genai import types

console = Console()


# ============================================================================
# 驗證結果資料結構
# ============================================================================

class ValidationLevel(Enum):
    """驗證嚴重程度"""
    INFO = "資訊"
    WARNING = "警告"
    ERROR = "錯誤"
    CRITICAL = "嚴重"


@dataclass
class ValidationResult:
    """驗證結果"""
    passed: bool
    level: ValidationLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None


@dataclass
class PreflightReport:
    """飛行前檢查報告"""
    overall_passed: bool
    checks: List[ValidationResult]
    warnings: int
    errors: int

    def display(self):
        """顯示檢查報告"""
        # 標題
        status_icon = "✅" if self.overall_passed else "❌"
        status_text = "通過" if self.overall_passed else "失敗"

        console.print(safe_t('common.message', fallback='\n[bold #DDA0DD]🔍 飛行前檢查報告 {status_icon} {status_text}[/bold #DDA0DD]\n', status_icon=status_icon, status_text=status_text))

        # 統計
        console.print(safe_t('common.message', fallback='[#DDA0DD]總檢查項目：[/#DDA0DD] {checks_count}', checks_count=len(self.checks)))
        console.print(safe_t('common.warning', fallback='[#DDA0DD]警告：[/#DDA0DD] {warnings}', warnings=self.warnings))
        console.print(safe_t('error.failed', fallback='[dim #DDA0DD]錯誤：[/red] {self.errors}', errors=self.errors))
        console.print()

        # 詳細結果
        for check in self.checks:
            icon = "✅" if check.passed else "❌"
            color = "green" if check.passed else "#DDA0DD" if check.level == ValidationLevel.WARNING else "red"

            console.print(f"{icon} [{color}]{check.message}[/{color}]")

            if check.details:
                for key, value in check.details.items():
                    console.print(f"   • {key}: {value}")

            if check.suggestions and not check.passed:
                console.print(safe_t('common.message', fallback='   [dim]建議：[/dim]'))
                for suggestion in check.suggestions:
                    console.print(f"   [dim]→ {suggestion}[/dim]")
            console.print()


# ============================================================================
# API 健康檢查
# ============================================================================

class APIHealthChecker:
    """API 健康檢查器"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def check_api_key(self) -> ValidationResult:
        """檢查 API 金鑰"""
        if not self.api_key:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.CRITICAL,
                message="API 金鑰未設定",
                suggestions=[
                    "設定環境變數：export GEMINI_API_KEY='你的金鑰'",
                    "或在 .env 檔案中設定：GEMINI_API_KEY=你的金鑰",
                    "從 https://aistudio.google.com/apikey 獲取金鑰"
                ]
            )

        # 驗證金鑰格式
        if not self.api_key.startswith('AIzaSy'):
            return ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message="API 金鑰格式不正確",
                details={"key_prefix": self.api_key[:10] + "..."},
                suggestions=[
                    "確認金鑰是否完整複製",
                    "Gemini API 金鑰應以 'AIzaSy' 開頭"
                ]
            )

        return ValidationResult(
            passed=True,
            level=ValidationLevel.INFO,
            message="API 金鑰格式正確"
        )

    def check_api_connectivity(self) -> ValidationResult:
        """檢查 API 連接性"""
        if not self.client:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.CRITICAL,
                message="無法初始化 API 客戶端"
            )

        try:
            # 嘗試列出模型（輕量級測試）
            models = list(self.client.models.list())

            return ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message="API 連接正常",
                details={"available_models": len(models)}
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.CRITICAL,
                message="API 連接失敗",
                details={"error": str(e)},
                suggestions=[
                    "檢查網路連接",
                    "確認 API 金鑰有效",
                    "查看 Gemini API 狀態：https://status.cloud.google.com/",
                    "檢查是否有防火牆阻擋"
                ]
            )

    def check_network(self) -> ValidationResult:
        """檢查網路連接"""
        test_urls = [
            "https://www.google.com",
            "https://generativelanguage.googleapis.com"
        ]

        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return ValidationResult(
                        passed=True,
                        level=ValidationLevel.INFO,
                        message="網路連接正常"
                    )
            except Exception:
                continue

        return ValidationResult(
            passed=False,
            level=ValidationLevel.CRITICAL,
            message="網路連接失敗",
            suggestions=[
                "檢查網路連接",
                "確認 DNS 設定正確",
                "檢查代理設定（如有使用）"
            ]
        )


# ============================================================================
# 參數驗證器
# ============================================================================

class ParameterValidator:
    """參數驗證器"""

    # Veo 限制
    VEO_MAX_DURATION = 8
    VEO_VALID_RESOLUTIONS = ["720p", "1080p"]
    VEO_VALID_ASPECT_RATIOS = ["16:9", "9:16", "1:1"]

    # 提示詞限制
    PROMPT_MIN_LENGTH = 10
    PROMPT_MAX_LENGTH = 2000

    # 檔案大小限制
    MAX_VIDEO_SIZE_MB = 2000
    MAX_IMAGE_SIZE_MB = 20

    @staticmethod
    def validate_veo_parameters(
        prompt: str,
        duration: int = 8,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9"
    ) -> List[ValidationResult]:
        """驗證 Veo 參數"""
        results = []

        # 1. 提示詞長度
        if len(prompt) < ParameterValidator.PROMPT_MIN_LENGTH:
            results.append(ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message=f"提示詞太短（{len(prompt)} 字元）",
                details={"min_length": ParameterValidator.PROMPT_MIN_LENGTH},
                suggestions=[
                    "提示詞至少需要 10 個字元",
                    "提供更詳細的場景描述",
                    "範例：A serene mountain landscape at sunset with golden light"
                ]
            ))
        elif len(prompt) > ParameterValidator.PROMPT_MAX_LENGTH:
            results.append(ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message=f"提示詞太長（{len(prompt)} 字元）",
                details={"max_length": ParameterValidator.PROMPT_MAX_LENGTH},
                suggestions=[
                    f"縮短提示詞至 {ParameterValidator.PROMPT_MAX_LENGTH} 字元以內",
                    "移除不必要的細節",
                    "專注於核心場景描述"
                ]
            ))
        else:
            results.append(ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message=f"提示詞長度適當（{len(prompt)} 字元）"
            ))

        # 2. 影片時長
        if duration > ParameterValidator.VEO_MAX_DURATION:
            results.append(ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message=f"影片時長超過限制（{duration} 秒）",
                details={"max_duration": ParameterValidator.VEO_MAX_DURATION},
                suggestions=[
                    f"Veo 3.1 最長支援 {ParameterValidator.VEO_MAX_DURATION} 秒",
                    "使用 Flow Engine 生成更長影片（自動分段）",
                    f"調整為 {ParameterValidator.VEO_MAX_DURATION} 秒或更短"
                ]
            ))
        else:
            results.append(ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message=f"影片時長符合限制（{duration} 秒）"
            ))

        # 3. 解析度
        if resolution not in ParameterValidator.VEO_VALID_RESOLUTIONS:
            results.append(ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message=f"不支援的解析度：{resolution}",
                details={"valid_resolutions": ParameterValidator.VEO_VALID_RESOLUTIONS},
                suggestions=[
                    f"使用支援的解析度：{', '.join(ParameterValidator.VEO_VALID_RESOLUTIONS)}",
                    "推薦：1080p（最高品質）"
                ]
            ))
        else:
            results.append(ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message=f"解析度有效（{resolution}）"
            ))

        # 4. 長寬比
        if aspect_ratio not in ParameterValidator.VEO_VALID_ASPECT_RATIOS:
            results.append(ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message=f"不支援的長寬比：{aspect_ratio}",
                details={"valid_aspect_ratios": ParameterValidator.VEO_VALID_ASPECT_RATIOS},
                suggestions=[
                    f"使用支援的長寬比：{', '.join(ParameterValidator.VEO_VALID_ASPECT_RATIOS)}",
                    "16:9 - 橫向影片（推薦）",
                    "9:16 - 直向影片（手機）",
                    "1:1 - 方形影片（社群媒體）"
                ]
            ))
        else:
            results.append(ValidationResult(
                passed=True,
                level=ValidationLevel.INFO,
                message=f"長寬比有效（{aspect_ratio}）"
            ))

        return results

    @staticmethod
    def validate_file(
        file_path: str,
        file_type: str = "video",
        check_size: bool = True
    ) -> ValidationResult:
        """驗證檔案"""
        # 1. 檔案存在性
        if not os.path.isfile(file_path):
            return ValidationResult(
                passed=False,
                level=ValidationLevel.CRITICAL,
                message=f"找不到{file_type}檔案",
                details={"path": file_path},
                suggestions=[
                    "檢查檔案路徑是否正確",
                    f"使用絕對路徑：{os.path.abspath(file_path)}",
                    "確認檔案是否存在"
                ]
            )

        # 2. 檔案大小
        if check_size:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            max_size = (ParameterValidator.MAX_VIDEO_SIZE_MB
                       if file_type == "video"
                       else ParameterValidator.MAX_IMAGE_SIZE_MB)

            if size_mb > max_size:
                return ValidationResult(
                    passed=False,
                    level=ValidationLevel.ERROR,
                    message=f"{file_type}檔案過大（{size_mb:.2f} MB）",
                    details={
                        "file_size_mb": f"{size_mb:.2f}",
                        "max_size_mb": max_size
                    },
                    suggestions=[
                        f"壓縮檔案至 {max_size} MB 以下",
                        "使用 gemini_video_preprocessor.py 壓縮",
                        f"或使用 ffmpeg：ffmpeg -i {file_path} -b:v 2M compressed.mp4"
                    ]
                )

        # 3. 檔案格式
        valid_extensions = {
            "video": [".mp4", ".mov", ".avi", ".mkv"],
            "image": [".jpg", ".jpeg", ".png", ".webp"],
            "audio": [".mp3", ".wav", ".aac", ".m4a"]
        }

        ext = Path(file_path).suffix.lower()
        if ext not in valid_extensions.get(file_type, []):
            return ValidationResult(
                passed=False,
                level=ValidationLevel.WARNING,
                message=f"不常見的{file_type}格式：{ext}",
                details={
                    "extension": ext,
                    "recommended": valid_extensions.get(file_type, [])
                },
                suggestions=[
                    f"推薦格式：{', '.join(valid_extensions.get(file_type, []))}",
                    "如果遇到問題，請轉換格式"
                ]
            )

        return ValidationResult(
            passed=True,
            level=ValidationLevel.INFO,
            message=f"{file_type}檔案有效",
            details={"path": os.path.basename(file_path)}
        )


# ============================================================================
# 依賴檢查器
# ============================================================================

class DependencyChecker:
    """依賴工具檢查器"""

    @staticmethod
    def check_ffmpeg() -> ValidationResult:
        """檢查 ffmpeg"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )

            if result.returncode == 0:
                # 解析版本
                version_line = result.stdout.decode().split('\n')[0]
                version = version_line.split()[2] if len(version_line.split()) > 2 else "unknown"

                return ValidationResult(
                    passed=True,
                    level=ValidationLevel.INFO,
                    message="ffmpeg 可用",
                    details={"version": version}
                )
            else:
                return ValidationResult(
                    passed=False,
                    level=ValidationLevel.ERROR,
                    message="ffmpeg 執行失敗"
                )

        except FileNotFoundError:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.CRITICAL,
                message="未安裝 ffmpeg",
                suggestions=[
                    "macOS：brew install ffmpeg",
                    "Ubuntu：sudo apt install ffmpeg",
                    "Windows：從 https://ffmpeg.org/ 下載"
                ]
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message="ffmpeg 檢查失敗",
                details={"error": str(e)}
            )

    @staticmethod
    def check_python_packages() -> ValidationResult:
        """檢查 Python 套件"""
        required_packages = [
            "google-genai",
            "rich",
            "python-dotenv",
            "requests"
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        if missing:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.CRITICAL,
                message="缺少必要的 Python 套件",
                details={"missing_packages": missing},
                suggestions=[
                    f"安裝缺少的套件：pip install {' '.join(missing)}",
                    "或使用：pip install -r requirements.txt"
                ]
            )

        return ValidationResult(
            passed=True,
            level=ValidationLevel.INFO,
            message="所有 Python 套件已安裝"
        )


# ============================================================================
# 內容政策檢查器
# ============================================================================

class ContentPolicyChecker:
    """內容政策檢查器"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def check_prompt_safety(self, prompt: str) -> ValidationResult:
        """檢查提示詞安全性"""
        if not self.client:
            return ValidationResult(
                passed=True,
                level=ValidationLevel.WARNING,
                message="無法檢查內容政策（API 客戶端未初始化）"
            )

        # 簡單的關鍵詞檢查（快速預檢）
        unsafe_keywords = [
            "暴力", "血腥", "色情", "裸露", "武器", "毒品",
            "violence", "blood", "porn", "nude", "weapon", "drug"
        ]

        prompt_lower = prompt.lower()
        found_keywords = [kw for kw in unsafe_keywords if kw in prompt_lower]

        if found_keywords:
            return ValidationResult(
                passed=False,
                level=ValidationLevel.WARNING,
                message="提示詞可能包含敏感內容",
                details={"keywords": found_keywords},
                suggestions=[
                    "移除敏感關鍵詞",
                    "參考 Gemini 內容政策：https://ai.google.dev/gemini-api/docs/safety-settings",
                    "使用更中性的描述"
                ]
            )

        return ValidationResult(
            passed=True,
            level=ValidationLevel.INFO,
            message="提示詞通過初步安全檢查"
        )


# ============================================================================
# 整合飛行前檢查器
# ============================================================================

class PreflightChecker:
    """飛行前檢查器（整合所有驗證）"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.api_health = APIHealthChecker(self.api_key)
        self.param_validator = ParameterValidator()
        self.dependency_checker = DependencyChecker()
        self.content_checker = ContentPolicyChecker(self.api_key)

    def check_veo_generation(
        self,
        prompt: str,
        duration: int = 8,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        reference_image: Optional[str] = None,
        video_to_extend: Optional[str] = None
    ) -> PreflightReport:
        """Veo 影片生成飛行前檢查"""
        checks = []

        # 1. API 健康檢查
        console.print(safe_t('common.message', fallback='[#DDA0DD]🔍 檢查 API 狀態...[/#DDA0DD]'))
        checks.append(self.api_health.check_api_key())
        checks.append(self.api_health.check_network())
        checks.append(self.api_health.check_api_connectivity())

        # 2. 依賴檢查
        console.print(safe_t('common.message', fallback='[#DDA0DD]🔍 檢查依賴工具...[/#DDA0DD]'))
        checks.append(self.dependency_checker.check_ffmpeg())
        checks.append(self.dependency_checker.check_python_packages())

        # 3. 參數驗證
        console.print(safe_t('common.message', fallback='[#DDA0DD]🔍 驗證參數...[/#DDA0DD]'))
        checks.extend(self.param_validator.validate_veo_parameters(
            prompt, duration, resolution, aspect_ratio
        ))

        # 4. 內容政策檢查
        console.print(safe_t('common.message', fallback='[#DDA0DD]🔍 檢查內容政策...[/#DDA0DD]'))
        checks.append(self.content_checker.check_prompt_safety(prompt))

        # 5. 檔案檢查
        if reference_image:
            console.print(safe_t('common.message', fallback='[#DDA0DD]🔍 檢查參考圖片...[/#DDA0DD]'))
            checks.append(self.param_validator.validate_file(
                reference_image, file_type="image"
            ))

        if video_to_extend:
            console.print(safe_t('common.message', fallback='[#DDA0DD]🔍 檢查延伸影片...[/#DDA0DD]'))
            checks.append(self.param_validator.validate_file(
                video_to_extend, file_type="video"
            ))

        # 統計結果
        warnings = sum(1 for c in checks if not c.passed and c.level == ValidationLevel.WARNING)
        errors = sum(1 for c in checks if not c.passed and c.level in [ValidationLevel.ERROR, ValidationLevel.CRITICAL])
        overall_passed = errors == 0

        return PreflightReport(
            overall_passed=overall_passed,
            checks=checks,
            warnings=warnings,
            errors=errors
        )

    def check_flow_generation(
        self,
        description: str,
        target_duration: int = 30,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9"
    ) -> PreflightReport:
        """Flow Engine 飛行前檢查"""
        checks = []

        # 基本檢查
        checks.append(self.api_health.check_api_key())
        checks.append(self.api_health.check_network())
        checks.append(self.api_health.check_api_connectivity())
        checks.append(self.dependency_checker.check_ffmpeg())

        # Flow 特定檢查
        if len(description) < 20:
            checks.append(ValidationResult(
                passed=False,
                level=ValidationLevel.WARNING,
                message="描述過於簡短，可能影響分段品質",
                suggestions=["提供更詳細的場景描述", "至少 20 個字元"]
            ))

        # 預估片段數
        segment_duration = 8
        num_segments = (target_duration + segment_duration - 1) // segment_duration

        if num_segments > 10:
            checks.append(ValidationResult(
                passed=False,
                level=ValidationLevel.WARNING,
                message=f"片段數量較多（{num_segments} 段），生成時間較長",
                details={"estimated_time": f"{num_segments * 3}-{num_segments * 5} 分鐘"},
                suggestions=[
                    "考慮縮短目標時長",
                    "準備等待較長時間",
                    "確保網路連接穩定"
                ]
            ))

        warnings = sum(1 for c in checks if not c.passed and c.level == ValidationLevel.WARNING)
        errors = sum(1 for c in checks if not c.passed and c.level in [ValidationLevel.ERROR, ValidationLevel.CRITICAL])
        overall_passed = errors == 0

        return PreflightReport(
            overall_passed=overall_passed,
            checks=checks,
            warnings=warnings,
            errors=errors
        )


# ============================================================================
# 命令行介面
# ============================================================================

def main():
    """命令行介面"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Gemini 預防性驗證系統 - 在執行前檢查所有可能問題",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例：
  # 執行完整系統檢查
  python gemini_validator.py --full-check

  # 驗證 Veo 影片生成參數
  python gemini_validator.py --check-veo "山景日落" --duration 8

  # 檢查提示詞內容政策
  python gemini_validator.py --check-prompt "A serene landscape"

  # 檢查檔案
  python gemini_validator.py --check-file video.mp4

  # 僅檢查 API 狀態
  python gemini_validator.py --check-api
        """
    )

    parser.add_argument(
        "--full-check",
        action="store_true",
        help="執行完整系統檢查（API、網路、依賴工具）"
    )

    parser.add_argument(
        "--check-veo",
        type=str,
        metavar="PROMPT",
        help="檢查 Veo 影片生成參數"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=8,
        help="影片時長（秒），預設 8"
    )

    parser.add_argument(
        "--resolution",
        type=str,
        default="1080p",
        choices=["720p", "1080p"],
        help="影片解析度，預設 1080p"
    )

    parser.add_argument(
        "--aspect-ratio",
        type=str,
        default="16:9",
        choices=["16:9", "9:16", "1:1"],
        help="影片長寬比，預設 16:9"
    )

    parser.add_argument(
        "--check-prompt",
        type=str,
        metavar="PROMPT",
        help="檢查提示詞內容政策"
    )

    parser.add_argument(
        "--check-file",
        type=str,
        metavar="FILE",
        help="檢查檔案（影片/圖片）"
    )

    parser.add_argument(
        "--check-api",
        action="store_true",
        help="僅檢查 API 連接狀態"
    )

    args = parser.parse_args()

    # 顯示標題
    console.print(safe_t('common.message', fallback='\n[bold #DDA0DD]🔍 Gemini 預防性驗證系統[/bold #DDA0DD]\n'))

    checker = PreflightChecker()

    # 執行對應的檢查
    if args.full_check:
        # 完整系統檢查
        console.print(safe_t('common.message', fallback='[#DDA0DD]執行完整系統檢查...[/#DDA0DD]\n'))
        report = checker.run_full_check()
        report.display()

        # 🎯 智能引導：自動修復常見問題
        if not report.overall_passed:
            console.print(safe_t('common.message', fallback='\n[bold #DDA0DD]💡 智能修復建議[/bold #DDA0DD]\n'))

            # 收集錯誤
            api_key_missing = False
            missing_packages = []
            ffmpeg_missing = False

            for check in report.checks:
                if "API 金鑰未設定" in check.message:
                    api_key_missing = True
                elif "缺少必要的 Python 套件" in check.message and check.details:
                    missing_packages = check.details.get("missing_packages", [])
                elif "ffmpeg 不可用" in check.message:
                    ffmpeg_missing = True

            # 提供自動修復選項
            from rich.prompt import Confirm

            # 1. 安裝缺少的套件
            if missing_packages:
                packages_list = ', '.join(missing_packages)
                console.print(safe_t('common.message', fallback='[#DDA0DD]發現缺少的套件：[/#DDA0DD] {packages_list}', packages_list=packages_list))
                if Confirm.ask("是否立即安裝？", default=True):
                    import subprocess
                    try:
                        console.print("\n[#DDA0DD]執行：[/#DDA0DD] pip install " + " ".join(missing_packages))
                        subprocess.run(
                            ["pip", "install"] + missing_packages,
                            check=True
                        )
                        console.print(safe_t('common.completed', fallback='[#DA70D6]✅ 套件安裝成功！[/green]\n'))
                    except subprocess.CalledProcessError as e:
                        console.print(safe_t('error.failed', fallback='[dim #DDA0DD]❌ 安裝失敗：{e}[/red]\n', e=e))

            # 2. 設定 API 金鑰
            if api_key_missing:
                console.print(safe_t('common.message', fallback='[#DDA0DD]API 金鑰未設定[/#DDA0DD]'))

                # 顯示申請資訊
                console.print(safe_t('common.message', fallback='\n[dim]💡 申請 API 金鑰：https://aistudio.google.com/app/apikey[/dim]\n'))

                if Confirm.ask("是否現在設定？", default=True):
                    from rich.prompt import Prompt, IntPrompt
                    from rich.table import Table

                    # 統一配置介面
                    console.print(safe_t('common.message', fallback='[bold bright_magenta]API 金鑰配置方式[/bold bright_magenta]'))

                    config_table = Table(show_header=False, box=None, padding=(0, 2))
                    console_width = console.width or 120
                    config_table.add_column("", style="bright_magenta", width=max(4, int(console_width * 0.03)))
                    config_table.add_column("", style="white")

                    config_table.add_row("1", "直接輸入 API 金鑰")
                    config_table.add_row("2", "從 .env 檔案載入")
                    config_table.add_row("3", "從環境變數載入")

                    console.print(config_table)

                    config_choice = IntPrompt.ask("\n請選擇", choices=["1", "2", "3"], default="1", show_default=True)

                    api_key = None

                    if config_choice == 1:
                        # 方式 1: 直接輸入
                        api_key = Prompt.ask("請輸入 API 金鑰", password=True)

                        # 儲存選項
                        console.print(safe_t('common.saving', fallback='\n[#DA70D6]儲存位置：[/#DA70D6]'))
                        console.print(safe_t('common.message', fallback='  1. .env 檔案（推薦）'))
                        console.print(safe_t('common.message', fallback='  2. 環境變數（本次會話）'))
                        console.print(safe_t('common.message', fallback='  3. 僅顯示設定指令'))

                        save_choice = IntPrompt.ask("請選擇", default=1)

                        if save_choice == 1:
                            env_path = os.path.join(os.getcwd(), ".env")
                            with open(env_path, "a") as f:
                                f.write(f"\nGEMINI_API_KEY={api_key}\n")
                            console.print(safe_t('common.completed', fallback='\n[#DA70D6]✅ 已儲存到 {env_path}[/#DA70D6]', env_path=env_path))
                            console.print(safe_t('common.loading', fallback='[#DDA0DD]提示：請重新啟動程式以載入設定[/#DDA0DD]'))
                        elif save_choice == 2:
                            os.environ["GEMINI_API_KEY"] = api_key
                            console.print(safe_t('common.completed', fallback='\n[#DA70D6]✅ 已設定（本次會話有效）[/#DA70D6]'))
                        else:
                            console.print(safe_t('common.message', fallback='\n[#DA70D6]請執行：[/#DA70D6]'))
                            console.print(f"export GEMINI_API_KEY='{api_key}'")

                    elif config_choice == 2:
                        # 方式 2: 從檔案載入
                        default_env_path = os.path.join(os.getcwd(), ".env")
                        env_file_path = Prompt.ask("請輸入 .env 檔案路徑", default=default_env_path)
                        env_file_path = os.path.expanduser(env_file_path)

                        if os.path.exists(env_file_path):
                            try:
                                with open(env_file_path, 'r') as f:
                                    for line in f:
                                        if line.strip().startswith('GEMINI_API_KEY='):
                                            api_key = line.strip().split('=', 1)[1].strip('\'"')
                                            os.environ["GEMINI_API_KEY"] = api_key
                                            console.print(safe_t('common.completed', fallback='\n[#DA70D6]✅ 已從 {env_file_path} 載入[/#DA70D6]', env_file_path=env_file_path))
                                            break
                                if not api_key:
                                    console.print(safe_t('common.message', fallback='[#DDA0DD]⚠ 檔案中未找到 GEMINI_API_KEY[/#DDA0DD]'))
                            except Exception as e:
                                console.print(safe_t('error.failed', fallback='[red]❌ 讀取失敗：{e}[/red]', e=e))
                        else:
                            console.print(safe_t('error.failed', fallback='[red]❌ 檔案不存在：{env_file_path}[/red]', env_file_path=env_file_path))

                    elif config_choice == 3:
                        # 方式 3: 從環境變數載入
                        env_var_name = Prompt.ask("請輸入環境變數名稱", default="GEMINI_API_KEY")
                        api_key = os.getenv(env_var_name)

                        if api_key:
                            os.environ["GEMINI_API_KEY"] = api_key
                            console.print(safe_t('common.completed', fallback='\n[#DA70D6]✅ 已從環境變數 {env_var_name} 載入[/#DA70D6]', env_var_name=env_var_name))
                        else:
                            console.print(safe_t('common.message', fallback='[#DDA0DD]⚠ 環境變數 {env_var_name} 未設定[/#DDA0DD]', env_var_name=env_var_name))
                            console.print(safe_t('common.message', fallback='\n[#DA70D6]請先執行：[/#DA70D6]'))
                            console.print(f"export {env_var_name}='your_api_key_here'")

            # 3. 安裝 ffmpeg
            if ffmpeg_missing:
                console.print(safe_t('common.message', fallback='[#DDA0DD]ffmpeg 未安裝[/#DDA0DD]'))
                console.print(safe_t('common.message', fallback='\n[#DDA0DD]安裝指令（依平台選擇）：[/#DDA0DD]'))
                console.print("  macOS:   brew install ffmpeg")
                console.print("  Ubuntu:  sudo apt install ffmpeg")
                console.print("  Windows: choco install ffmpeg")

                if Confirm.ask("\n是否打開安裝指南？", default=False):
                    import webbrowser
                    webbrowser.open("https://ffmpeg.org/download.html")

            # 重新檢查
            if missing_packages or api_key_missing:
                console.print("\n[#DDA0DD]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/#DDA0DD]")
                if Confirm.ask("是否重新執行檢查？", default=True):
                    console.print(safe_t('common.message', fallback='\n[#DDA0DD]重新執行系統檢查...[/#DDA0DD]\n'))
                    report = checker.run_full_check()
                    report.display()

    elif args.check_veo:
        # Veo 參數檢查
        console.print(safe_t('common.generating', fallback='[#DDA0DD]檢查 Veo 影片生成參數...[/#DDA0DD]\n'))
        console.print(safe_t('common.message', fallback='  提示詞: {check_veo_value}', check_veo_value=args.check_veo))
        console.print(safe_t('common.message', fallback='  時長: {args.duration} 秒', duration_value=args.duration))
        console.print(safe_t('common.message', fallback='  解析度: {args.resolution}', resolution_value=args.resolution))
        console.print(safe_t('common.message', fallback='  長寬比: {args.aspect_ratio}\n', aspect_ratio_value=args.aspect_ratio))

        report = checker.check_veo_generation(
            prompt=args.check_veo,
            duration=args.duration,
            resolution=args.resolution,
            aspect_ratio=args.aspect_ratio
        )
        report.display()

        # 🎯 智能引導：時長超過限制時提供 Flow Engine 選項
        duration_error = None
        for check in report.checks:
            if "時長超過限制" in check.message:
                duration_error = check
                break

        if duration_error and args.duration > 8:
            console.print(safe_t('common.message', fallback='\n[bold #DDA0DD]💡 智能建議[/bold #DDA0DD]'))
            console.print(safe_t('common.generating', fallback='[#DDA0DD]您想要生成 {args.duration} 秒的影片，但 Veo 3.1 限制為 8 秒。[/#DDA0DD]', duration_value=args.duration))
            console.print(safe_t('common.generating', fallback='[#DDA0DD]我可以幫您使用 Flow Engine 自動分段生成！[/#DDA0DD]\n'))

            from rich.prompt import Confirm
            # ✅ M1 修復：合併為單次確認，移除後續的「立即執行」重複確認
            if Confirm.ask("是否使用 Flow Engine 立即生成長影片？", default=True):
                console.print(safe_t('common.completed', fallback='\n[#DA70D6]✅ 正在啟動 Flow Engine...[/green]\n'))

                # 計算分段數量
                num_segments = (args.duration + 7) // 8  # 向上取整

                # 生成 Flow Engine 指令
                flow_command = f"python3 gemini_flow_demo.py --prompt \"{check_veo_value}\" --duration {args.duration}"

                console.print(safe_t('common.message', fallback='[#DDA0DD]執行指令：[/#DDA0DD]'))
                console.print(f"[bold]{flow_command}[/bold]\n")

                # ✅ M1 修復：移除重複確認，直接執行（已在上方確認過）
                import subprocess
                try:
                    console.print(safe_t('common.message', fallback='[#DDA0DD]啟動 Flow Engine...[/#DDA0DD]\n'))
                    result = subprocess.run(
                        flow_command.split(),
                        check=True,
                        capture_output=False
                    )
                    console.print(safe_t('common.completed', fallback='\n[#DA70D6]✅ Flow Engine 執行完成！[/green]'))
                    return 0
                except FileNotFoundError:
                    console.print(safe_t('error.failed', fallback='\n[dim #DDA0DD]❌ gemini_flow_demo.py 不存在[/red]'))
                    console.print(safe_t('common.message', fallback='[#DDA0DD]請手動執行上述指令[/#DDA0DD]'))
                except subprocess.CalledProcessError as e:
                    console.print(safe_t('error.failed', fallback='\n[dim #DDA0DD]❌ 執行失敗：{e}[/red]', e=e))
            else:
                console.print(safe_t('common.message', fallback='\n[#DDA0DD]好的，請調整參數後重試[/#DDA0DD]'))

    elif args.check_prompt:
        # 提示詞檢查
        console.print(safe_t('common.message', fallback='[#DDA0DD]檢查提示詞內容政策...[/#DDA0DD]\n'))
        results = ContentPolicyChecker.check_prompt(args.check_prompt)

        has_error = False
        for result in results:
            if result.passed:
                console.print(f"[#DA70D6]✅ {result.message}[/green]")
            else:
                has_error = True
                level_color = {
                    ValidationLevel.WARNING: "#DDA0DD",
                    ValidationLevel.ERROR: "red"
                }.get(result.level, "white")

                console.print(f"[{level_color}]❌ {result.message}[/{level_color}]")
                if result.suggestions:
                    console.print(safe_t('common.message', fallback='   建議：'))
                    for sug in result.suggestions:
                        console.print(f"   → {sug}")

        # 🎯 智能引導：提示詞問題
        if has_error:
            console.print(safe_t('common.message', fallback='\n[bold #DDA0DD]💡 智能建議[/bold #DDA0DD]'))
            if len(args.check_prompt) < 10:
                console.print(safe_t('common.message', fallback='[#DDA0DD]您的提示詞太短，我可以幫您擴展！[/#DDA0DD]\n'))
                console.print(safe_t('common.message', fallback='[#DDA0DD]原始提示詞：[/#DDA0DD] {args.check_prompt}', check_prompt_value=args.check_prompt))

                examples = [
                    f"{args.check_prompt}, cinematic lighting, high quality, 4K",
                    f"A detailed scene of {args.check_prompt} with beautiful composition",
                    f"{args.check_prompt}, professional photography, stunning visuals"
                ]

                console.print(safe_t('common.message', fallback='\n[#DDA0DD]建議的擴展版本：[/#DDA0DD]'))
                for i, ex in enumerate(examples, 1):
                    console.print(f"  {i}. {ex}")

                from rich.prompt import IntPrompt
                choice = IntPrompt.ask("\n選擇一個版本 (1-3, 0=手動輸入)", default=1, show_default=True)

                if choice in [1, 2, 3]:
                    selected = examples[choice - 1]
                    console.print(safe_t('common.completed', fallback='\n[#DA70D6]✅ 已選擇：[/green] {selected}', selected=selected))
                    console.print(safe_t('common.message', fallback='\n[#DDA0DD]重新執行驗證...[/#DDA0DD]\n'))

                    # 重新驗證
                    import sys
                    sys.argv = ["gemini_validator.py", "--check-prompt", selected]
                    return main()
                elif choice == 0:
                    from rich.prompt import Prompt
                    new_prompt = Prompt.ask("\n請輸入新的提示詞")
                    console.print(safe_t('common.message', fallback='\n[#DDA0DD]重新執行驗證...[/#DDA0DD]\n'))
                    import sys
                    sys.argv = ["gemini_validator.py", "--check-prompt", new_prompt]
                    return main()

    elif args.check_file:
        # 檔案檢查
        console.print(safe_t('common.message', fallback='[#DDA0DD]檢查檔案...[/#DDA0DD]\n'))
        results = ParameterValidator.validate_file(args.check_file)

        for result in results:
            if result.passed:
                console.print(f"[#DA70D6]✅ {result.message}[/green]")
            else:
                console.print(f"[dim #DDA0DD]❌ {result.message}[/red]")
                if result.suggestions:
                    console.print(safe_t('common.message', fallback='   建議：'))
                    for sug in result.suggestions:
                        console.print(f"   → {sug}")

    elif args.check_api:
        # API 檢查
        console.print(safe_t('common.message', fallback='[#DDA0DD]檢查 API 連接狀態...[/#DDA0DD]\n'))
        api_checks = APIHealthChecker.check_api_status()

        for check in api_checks:
            if check.passed:
                console.print(f"[#DA70D6]✅ {check.message}[/green]")
            else:
                console.print(f"[dim #DDA0DD]❌ {check.message}[/red]")
                if check.suggestions:
                    console.print(safe_t('common.message', fallback='   建議：'))
                    for sug in check.suggestions:
                        console.print(f"   → {sug}")

    else:
        # 沒有指定任何選項，執行簡單測試
        console.print(safe_t('common.message', fallback='[#DDA0DD]執行基本測試...[/#DDA0DD]\n'))
        console.print(safe_t('common.message', fallback='[dim]提示：使用 --help 查看所有選項[/dim]\n'))

        report = checker.check_veo_generation(
            prompt="A serene mountain landscape at sunset",
            duration=8,
            resolution="1080p",
            aspect_ratio="16:9"
        )
        report.display()

    # 總結
    console.print()
    if hasattr(locals().get('report'), 'overall_passed'):
        if report.overall_passed:
            console.print(safe_t('common.completed', fallback='[bold green]✅ 所有檢查通過，可以安全執行！[/bold green]\n'))
            return 0
        else:
            console.print(safe_t('error.failed', fallback='[bold red]❌ 檢查失敗，請修正錯誤後再執行[/bold red]\n'))
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
