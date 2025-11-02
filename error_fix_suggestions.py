#!/usr/bin/env python3
"""
錯誤修復建議系統
提供一鍵式修復方案，自動偵測系統並給出對應的解決步驟
"""
import os
from utils import safe_t
import platform
import subprocess
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm, IntPrompt

# 導入智能檔案選擇器 (C-2 違規修復)
from smart_file_selector import SmartFileSelector

console = Console()

# ========================================
# 全域錯誤記錄器（記憶體洩漏修復）
# ========================================

# Diagnostics 目錄路徑
DIAGNOSTICS_DIR = os.path.join(os.path.dirname(__file__), "Diagnostics")
os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)

# 全域 ErrorLogger 實例（延遲初始化，在類別定義後）
_error_logger = None


def _get_error_logger():
    """
    獲取全域 ErrorLogger 實例（延遲初始化）

    Returns:
        ErrorLogger 實例
    """
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger(
            log_file=os.path.join(DIAGNOSTICS_DIR, "error_diagnostics.log"),
            max_errors=1000
        )
    return _error_logger


def _simplify_path(path: str) -> str:
    """
    簡化路徑顯示，使其更簡潔易讀

    策略：
    1. 如果路徑在當前工作目錄下，顯示相對路徑 (./...)
    2. 如果路徑在家目錄下，使用 ~ 代替 (~/)
    3. 否則顯示完整絕對路徑

    Args:
        path: 完整路徑字符串

    Returns:
        簡化後的路徑字符串

    Examples:
        /Users/user/project/file.py -> ./file.py (如果在 /Users/user/project 目錄)
        /Users/user/documents/file.txt -> ~/documents/file.txt
        /opt/system/file.conf -> /opt/system/file.conf (保持原樣)
    """
    try:
        path_obj = Path(path).resolve()
        cwd = Path.cwd()
        home = Path.home()

        # 嘗試獲取相對於當前目錄的路徑
        try:
            rel_path = path_obj.relative_to(cwd)
            return f"./{rel_path}"
        except ValueError:
            pass

        # 嘗試使用 ~ 代替家目錄
        try:
            rel_home = path_obj.relative_to(home)
            return f"~/{rel_home}"
        except ValueError:
            pass

        # 如果都不適用，返回絕對路徑
        return str(path_obj)

    except Exception:
        # 如果發生任何錯誤，返回原始路徑
        return path


def _convert_paths_to_file_info(paths: List[str]) -> List[Dict]:
    """
    將路徑列表轉換為檔案資訊字典列表 (供智能選擇器使用)

    Args:
        paths: 檔案路徑列表

    Returns:
        檔案資訊字典列表
    """
    file_infos = []

    for path_str in paths:
        path_str = path_str.strip()
        if not os.path.isfile(path_str):
            continue

        try:
            stat = os.stat(path_str)
            file_size = stat.st_size
            mod_time = stat.st_mtime
            mod_time_str = datetime.fromtimestamp(mod_time)

            # 計算時間差
            now = datetime.now()
            time_diff = now - mod_time_str

            if time_diff.days > 0:
                time_ago = f"{time_diff.days} 天前"
            elif time_diff.seconds > 3600:
                time_ago = f"{time_diff.seconds // 3600} 小時前"
            elif time_diff.seconds > 60:
                time_ago = f"{time_diff.seconds // 60} 分鐘前"
            else:
                time_ago = safe_t("error_handler.error_fix_suggestions.msg_0001", fallback="剛才")

            file_infos.append({
                'name': os.path.basename(path_str),
                'path': path_str,
                'size': file_size,
                'similarity': 0.70,  # 搜尋結果預設中等信心度
                'time_ago': time_ago,
                'modified_time': mod_time
            })
        except (OSError, FileNotFoundError):
            continue

    return file_infos


def suggest_file_not_found(file_path: str, auto_fix: bool = True) -> Optional[str]:
    """
    顯示檔案不存在的修復建議並提供一鍵修復

    Args:
        file_path: 找不到的檔案路徑
        auto_fix: 是否提供自動修復選項（預設 True）

    Returns:
        Optional[str]: 如果用戶選擇了替代檔案，返回新路徑；否則返回 None
    """
    # 🔧 記錄錯誤到 ErrorLogger
    _get_error_logger().log_error(
        error_type="FileNotFound",
        file_path=file_path,
        details={
            'auto_fix': auto_fix,
            'parent_dir': os.path.dirname(file_path) or '.',
            'filename': os.path.basename(file_path)
        }
    )

    console.print(f"\n[dim #E8C4F0]✗ 找不到檔案：{file_path}[/red]\n")
    console.print(Markdown("**💡 解決方案：**\n"))

    # 嘗試找相似檔案
    parent_dir = os.path.dirname(file_path) or '.'
    target_filename = os.path.basename(file_path)
    target_name, target_ext = os.path.splitext(target_filename)

    similar_files = []

    if os.path.isdir(parent_dir):
        try:
            for filename in os.listdir(parent_dir):
                full_path = os.path.join(parent_dir, filename)

                if not os.path.isfile(full_path):
                    continue

                # 計算相似度
                similarity = SequenceMatcher(
                    None,
                    target_filename.lower(),
                    filename.lower()
                ).ratio()

                # 相似度 > 0.5 或相同副檔名
                if similarity > 0.5 or (target_ext and filename.endswith(target_ext)):
                    file_size = os.path.getsize(full_path)
                    mod_time = os.path.getmtime(full_path)
                    mod_time_str = datetime.fromtimestamp(mod_time)

                    # 計算時間差
                    now = datetime.now()
                    time_diff = now - mod_time_str

                    if time_diff.days > 0:
                        time_ago = f"{time_diff.days} 天前"
                    elif time_diff.seconds > 3600:
                        time_ago = f"{time_diff.seconds // 3600} 小時前"
                    elif time_diff.seconds > 60:
                        time_ago = f"{time_diff.seconds // 60} 分鐘前"
                    else:
                        time_ago = safe_t("error_handler.error_fix_suggestions.msg_0002", fallback="剛才")

                    similar_files.append({
                        'name': filename,
                        'path': full_path,
                        'size': file_size,
                        'similarity': similarity,
                        'time_ago': time_ago,
                        'modified_time': mod_time  # 添加時間戳供智能選擇器使用
                    })

            # 按相似度排序 (保留所有找到的檔案，不限制數量)
            similar_files.sort(key=lambda x: x['similarity'], reverse=True)

        except PermissionError:
            pass

    # 🎯 使用智能檔案選擇器 (C-2 違規修復)
    if similar_files and auto_fix:
        try:
            selector = SmartFileSelector()
            selected_files = selector.smart_select(similar_files)

            if selected_files:
                # 返回第一個選中的檔案 (保持向後兼容性)
                selected_path = selected_files[0]['path']

                if len(selected_files) > 1:
                    console.print(
                        f"\n[#B565D8]ℹ️ 您選擇了 {len(selected_files)} 個檔案，"
                        f"當前將使用: {selected_files[0]['name']}[/#B565D8]\n"
                    )
                else:
                    console.print(
                        f"\n[#B565D8]✅ 已選擇: {selected_files[0]['name']}[/#B565D8]"
                    )

                simplified_path = _simplify_path(selected_path)
                console.print(f"[dim]路徑: {simplified_path}[/dim]\n")
                return selected_path
            else:
                console.print("\n[#E8C4F0]已取消選擇[/#E8C4F0]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[#E8C4F0]已取消[/#E8C4F0]")
        except Exception as e:
            console.print(f"\n[#E8C4F0]選擇器錯誤: {e}[/#E8C4F0]")
            console.print("[dim]將繼續執行搜尋流程...[/dim]\n")

    # 搜尋指令
    console.print("[bold]🔍 搜尋檔案：[/bold]")
    console.print("   執行指令在整個目錄樹中搜尋：")

    # 根據作業系統提供不同指令
    if platform.system() == "Windows":
        search_cmd = f'dir /s /b "{parent_dir}\\*{target_name}*"'
    else:
        search_cmd = f'find "{parent_dir}" -name "*{target_name}*"'

    console.print(Panel(search_cmd, border_style="#E8C4F0"))

    if target_ext:
        console.print(f"\n   或只搜尋 {target_ext} 檔案：")
        if platform.system() == "Windows":
            ext_search_cmd = f'dir /s /b "{parent_dir}\\*{target_ext}"'
        else:
            ext_search_cmd = f'find "{parent_dir}" -name "*{target_ext}"'
        console.print(Panel(ext_search_cmd, border_style="#E8C4F0"))

    console.print()

    # 🎯 一鍵執行搜尋
    if auto_fix:
        console.print("[bold #E8C4F0]⚡ 一鍵搜尋[/bold #E8C4F0]")
        if Confirm.ask("立即執行搜尋指令？", default=False):
            try:
                result = subprocess.run(
                    search_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.stdout:
                    console.print("\n[#B565D8]🔍 搜尋結果[/#B565D8]")
                    lines = result.stdout.strip().split('\n')
                    console.print(f"[dim]找到 {len(lines)} 個檔案[/dim]\n")

                    # 🎯 使用智能檔案選擇器 (C-3 違規修復)
                    try:
                        # 轉換路徑為檔案資訊格式
                        search_file_infos = _convert_paths_to_file_info(lines)

                        if search_file_infos:
                            selector = SmartFileSelector()
                            selected_files = selector.smart_select(search_file_infos)

                            if selected_files:
                                selected_path = selected_files[0]['path']

                                if len(selected_files) > 1:
                                    console.print(
                                        f"\n[#B565D8]ℹ️ 您選擇了 {len(selected_files)} 個檔案，"
                                        f"當前將使用: {selected_files[0]['name']}[/#B565D8]\n"
                                    )
                                else:
                                    console.print(f"\n[#B565D8]✅ 已選擇: {selected_files[0]['name']}[/#B565D8]")

                                simplified_path = _simplify_path(selected_path)
                                console.print(f"[dim]路徑: {simplified_path}[/dim]\n")
                                return selected_path
                        else:
                            console.print("[#E8C4F0]⚠ 無法獲取檔案資訊[/#E8C4F0]")
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[#E8C4F0]已取消[/#E8C4F0]")
                    except Exception as e:
                        console.print(f"\n[#E8C4F0]選擇器錯誤: {e}[/#E8C4F0]")
                else:
                    console.print("[#E8C4F0]未找到符合的檔案[/#E8C4F0]")

            except subprocess.TimeoutExpired:
                console.print("[#E8C4F0]搜尋超時[/#E8C4F0]")
            except Exception as e:
                console.print(f"[dim #E8C4F0]搜尋失敗：{e}[/red]")

        console.print()

    # 檢查目錄
    console.print("[bold]📝 檢查路徑：[/bold]")
    console.print("   確認目錄內容：")

    if platform.system() == "Windows":
        ls_cmd = f'dir "{parent_dir}"'
    else:
        ls_cmd = f'ls -lh "{parent_dir}/"'

    console.print(Panel(ls_cmd, border_style="#E8C4F0"))
    console.print()

    # 常見原因
    console.print("[bold #E8C4F0]⚠️  常見原因：[/bold #E8C4F0]")
    console.print("   1. 檔案路徑拼寫錯誤")
    console.print("   2. 檔案已被移動或刪除")
    console.print("   3. 檔案名稱大小寫不符（Linux/macOS 區分大小寫）")
    console.print("   4. 相對路徑與絕對路徑混淆")
    console.print()

    return None


def suggest_ffmpeg_install() -> None:
    """
    顯示 ffmpeg 安裝建議

    自動偵測作業系統並提供對應的一鍵安裝指令
    """
    # 偵測作業系統
    system = platform.system()

    # 🔧 記錄錯誤到 ErrorLogger
    _get_error_logger().log_error(
        error_type="FFmpegNotInstalled",
        file_path="",
        details={
            'system': system,
            'platform_version': platform.version()
        }
    )

    console.print("\n[dim #E8C4F0]✗ ffmpeg 未安裝[/red]\n")
    console.print("[#E8C4F0]💡 一鍵修復方案：[/#E8C4F0]\n")

    # macOS
    if system == "Darwin":
        console.print("[bold #E8C4F0]🔧 macOS 用戶（推薦）[/bold green]")

        # 檢查是否有 Homebrew
        has_brew = _check_command("brew")

        if has_brew:
            console.print("   [dim]已偵測到 Homebrew[/dim]")
            console.print(Panel(
                "brew install ffmpeg",
                border_style="#E8C4F0",
                title="📋 執行指令",
                padding=(0, 1)
            ))
        else:
            console.print("   [#E8C4F0]未偵測到 Homebrew，請先安裝 Homebrew：[/#E8C4F0]")
            console.print(Panel(
                '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                border_style="#E8C4F0",
                title="1️⃣ 安裝 Homebrew",
                padding=(0, 1)
            ))
            console.print("\n   [#E8C4F0]然後安裝 ffmpeg：[/green]")
            console.print(Panel(
                "brew install ffmpeg",
                border_style="#E8C4F0",
                title="2️⃣ 安裝 ffmpeg",
                padding=(0, 1)
            ))
        console.print()

    # Linux
    elif system == "Linux":
        distro = _detect_linux_distro()

        if distro == "ubuntu" or distro == "debian":
            console.print("[bold #E8C4F0]🔧 Linux (Ubuntu/Debian) 用戶（推薦）[/bold green]")
            console.print(Panel(
                "sudo apt-get update && sudo apt-get install -y ffmpeg",
                border_style="#E8C4F0",
                title="📋 執行指令",
                padding=(0, 1)
            ))
        elif distro == "fedora" or distro == "rhel" or distro == "centos":
            console.print("[bold #E8C4F0]🔧 Linux (Fedora/CentOS/RHEL) 用戶（推薦）[/bold green]")
            console.print(Panel(
                "sudo dnf install -y ffmpeg",
                border_style="#E8C4F0",
                title="📋 執行指令",
                padding=(0, 1)
            ))
        elif distro == "arch":
            console.print("[bold #E8C4F0]🔧 Linux (Arch) 用戶（推薦）[/bold green]")
            console.print(Panel(
                "sudo pacman -S ffmpeg",
                border_style="#E8C4F0",
                title="📋 執行指令",
                padding=(0, 1)
            ))
        else:
            # 無法檢測發行版，顯示所有選項
            console.print("[bold]🔧 Linux 用戶[/bold]")
            console.print("\n[#E8C4F0]根據你的發行版選擇：[/#E8C4F0]\n")

            console.print("   [#E8C4F0]Ubuntu/Debian：[/#E8C4F0]")
            console.print(Panel(
                "sudo apt-get update && sudo apt-get install -y ffmpeg",
                border_style="#E8C4F0",
                padding=(0, 1)
            ))

            console.print("\n   [#E8C4F0]Fedora/CentOS/RHEL：[/#E8C4F0]")
            console.print(Panel(
                "sudo dnf install -y ffmpeg",
                border_style="#E8C4F0",
                padding=(0, 1)
            ))

            console.print("\n   [#E8C4F0]Arch Linux：[/#E8C4F0]")
            console.print(Panel(
                "sudo pacman -S ffmpeg",
                border_style="#E8C4F0",
                padding=(0, 1)
            ))
        console.print()

    # Windows
    elif system == "Windows":
        console.print("[bold #E8C4F0]🔧 Windows 用戶[/bold #E8C4F0]")
        console.print("\n[#E8C4F0]方案 1：使用 Chocolatey（推薦）[/#E8C4F0]")

        has_choco = _check_command("choco")
        if has_choco:
            console.print("   [dim]已偵測到 Chocolatey[/dim]")
            console.print(Panel(
                "choco install ffmpeg",
                border_style="#E8C4F0",
                title="📋 執行指令（以管理員身分執行 PowerShell）",
                padding=(0, 1)
            ))
        else:
            console.print("   [#E8C4F0]未偵測到 Chocolatey，請先安裝：[/#E8C4F0]")
            console.print(Panel(
                'Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString(\'https://community.chocolatey.org/install.ps1\'))',
                border_style="#E8C4F0",
                title="1️⃣ 安裝 Chocolatey（以管理員身分執行 PowerShell）",
                padding=(0, 1)
            ))
            console.print("\n   [#E8C4F0]然後安裝 ffmpeg：[/green]")
            console.print(Panel(
                "choco install ffmpeg",
                border_style="#E8C4F0",
                title="2️⃣ 安裝 ffmpeg",
                padding=(0, 1)
            ))

        console.print("\n[#E8C4F0]方案 2：手動安裝[/#E8C4F0]")
        console.print("   [dim]手動安裝步驟：[/dim]")
        console.print("   1. 前往 [#B565D8]https://ffmpeg.org/download.html[/#B565D8]")
        console.print("   2. 點擊 'Windows builds from gyan.dev'")
        console.print("   3. 下載 'ffmpeg-release-full.7z'")
        console.print("   4. 解壓縮到 [#E8C4F0]C:\\ffmpeg[/#E8C4F0]")
        console.print("   5. 將 [#E8C4F0]C:\\ffmpeg\\bin[/#E8C4F0] 添加到系統 PATH：")
        console.print("      • 右鍵「本機」→「內容」→「進階系統設定」")
        console.print("      • 點擊「環境變數」")
        console.print("      • 在「系統變數」中找到「Path」，點擊「編輯」")
        console.print("      • 點擊「新增」，輸入 [#E8C4F0]C:\\ffmpeg\\bin[/#E8C4F0]")
        console.print("      • 按「確定」儲存")
        console.print()

    # 其他系統
    else:
        console.print("[bold]🔧 其他系統[/bold]")
        console.print("   請前往 [#B565D8]https://ffmpeg.org/download.html[/#B565D8] 下載對應版本")
        console.print()

    # 通用提示
    console.print("[#E8C4F0]⏸️  安裝完成後，請重新執行程式[/#E8C4F0]\n")

    # 驗證安裝
    console.print("[#E8C4F0]📝 驗證安裝：[/#E8C4F0]")
    console.print(Panel(
        "ffmpeg -version",
        border_style="#E8C4F0",
        title="執行指令檢查版本",
        padding=(0, 1)
    ))
    console.print()


def suggest_api_key_setup() -> None:
    """
    顯示 Gemini API 金鑰設定建議

    提供完整的設定指引，包括：
    - API 金鑰申請步驟
    - 三種設定方式（臨時、永久、.env）
    - 平台特定的指令
    - 安全提醒
    - 驗證方法
    """
    system = platform.system()

    # 🔧 記錄錯誤到 ErrorLogger
    _get_error_logger().log_error(
        error_type="APIKeyNotSet",
        file_path="",
        details={
            'system': system,
            'env_var_name': 'GEMINI_API_KEY'
        }
    )

    # 錯誤標題
    console.print("\n[dim #E8C4F0]✗ Gemini API 金鑰未設定[/red]\n")
    console.print("[#E8C4F0]💡 設定方式：[/#E8C4F0]\n")

    # ==================== 方法 1：臨時環境變數 ====================
    console.print("[bold]🔧 方法 1：使用環境變數（臨時，本次終端有效）[/bold]\n")

    if system in ["Darwin", "Linux"]:
        console.print("   macOS/Linux:")
        console.print(Panel(
            'export GEMINI_API_KEY="your-api-key-here"',
            border_style="#E8C4F0",
            title="執行指令",
            padding=(0, 1)
        ))
    elif system == "Windows":
        console.print("   Windows (PowerShell):")
        console.print(Panel(
            '$env:GEMINI_API_KEY="your-api-key-here"',
            border_style="#E8C4F0",
            title="執行指令",
            padding=(0, 1)
        ))
    console.print()

    # ==================== 方法 2：永久設定 ====================
    console.print("[bold]🔧 方法 2：寫入設定檔（永久，推薦）[/bold]\n")

    if system in ["Darwin", "Linux"]:
        # 檢測 shell
        shell = _detect_shell()

        if shell == "zsh":
            console.print("   macOS/Linux (zsh):")
            console.print(Panel(
                'echo \'export GEMINI_API_KEY="your-key"\' >> ~/.zshrc\nsource ~/.zshrc',
                border_style="#E8C4F0",
                title="執行指令",
                padding=(0, 1)
            ))
        else:
            console.print("   macOS/Linux (bash):")
            console.print(Panel(
                'echo \'export GEMINI_API_KEY="your-key"\' >> ~/.bashrc\nsource ~/.bashrc',
                border_style="#E8C4F0",
                title="執行指令",
                padding=(0, 1)
            ))

    elif system == "Windows":
        console.print("   Windows (永久):")
        console.print("   [dim]手動步驟：[/dim]")
        console.print("   1. 搜尋「環境變數」")
        console.print("   2. 點擊「編輯系統環境變數」")
        console.print("   3. 點擊「環境變數」")
        console.print("   4. 在「用戶變數」中新增：")
        console.print("      變數名：[#E8C4F0]GEMINI_API_KEY[/#E8C4F0]")
        console.print("      變數值：[#E8C4F0]your-api-key-here[/#E8C4F0]")
    console.print()

    # ==================== 方法 3：.env 檔案 ====================
    console.print("[bold]🔧 方法 3：使用 .env 檔案（專案專用）[/bold]\n")
    console.print(Panel(
        "echo 'GEMINI_API_KEY=your-api-key' > .env",
        border_style="#E8C4F0",
        title="在專案目錄執行",
        padding=(0, 1)
    ))
    console.print()

    # ==================== 如何取得 API 金鑰 ====================
    console.print("[bold #E8C4F0]📝 如何取得 API 金鑰：[/bold #E8C4F0]\n")

    console.print("   1. 前往 Google AI Studio")
    console.print("      🔗 [link=https://aistudio.google.com/apikey]https://aistudio.google.com/apikey[/link]")
    console.print()

    console.print("   2. 使用 Google 帳號登入")
    console.print()

    console.print("   3. 點擊「Create API Key」或「Get API Key」")
    console.print()

    console.print("   4. 選擇或創建 Google Cloud 專案")
    console.print()

    console.print("   5. 複製 API 金鑰（格式：AIza...）")
    console.print()

    console.print("   6. 使用上述任一方法設定金鑰")
    console.print()

    # ==================== 安全提醒 ====================
    console.print("[bold #E8C4F0]⚠️  安全提醒：[/bold #E8C4F0]")
    console.print("   - 不要將 API 金鑰提交到 Git")
    console.print("   - 不要在公開場合分享金鑰")
    console.print("   - 定期輪換金鑰以確保安全")
    console.print()

    # ==================== 驗證設定 ====================
    console.print("[bold #E8C4F0]✅ 驗證設定：[/bold #E8C4F0]")
    console.print("   執行指令檢查：")

    if system in ["Darwin", "Linux"]:
        console.print(Panel(
            "echo $GEMINI_API_KEY",
            border_style="#E8C4F0",
            title="macOS/Linux",
            padding=(0, 1)
        ))
    elif system == "Windows":
        console.print(Panel(
            "echo %GEMINI_API_KEY%  # Windows CMD\necho $env:GEMINI_API_KEY  # Windows PowerShell",
            border_style="#E8C4F0",
            title="Windows",
            padding=(0, 1)
        ))

    console.print("\n   [dim]應顯示您的 API 金鑰（AIza...）[/dim]\n")


def suggest_missing_module(module_name: str, install_command: Optional[str] = None) -> None:
    """
    顯示缺少 Python 模組的安裝建議

    Args:
        module_name: 模組名稱
        install_command: 自訂安裝指令（若未提供則使用預設的 pip install）
    """
    # 🔧 記錄錯誤到 ErrorLogger
    _get_error_logger().log_error(
        error_type="ModuleMissing",
        file_path="",
        details={
            'module_name': module_name,
            'install_command': install_command or f"pip install {module_name}",
            'in_virtualenv': _check_virtualenv()
        }
    )

    console.print(f"\n[dim #E8C4F0]✗ Python 模組 '{module_name}' 未安裝[/red]\n")
    console.print("[#E8C4F0]💡 一鍵修復方案：[/#E8C4F0]\n")

    if install_command is None:
        install_command = f"pip install {module_name}"

    console.print("[bold #E8C4F0]🔧 使用 pip 安裝（推薦）[/bold green]")
    console.print(Panel(
        install_command,
        border_style="#E8C4F0",
        title="📋 執行指令",
        padding=(0, 1)
    ))

    # 如果在虛擬環境中
    in_venv = _check_virtualenv()
    if in_venv:
        console.print("\n[#E8C4F0]✓ 已偵測到虛擬環境[/green]")
    else:
        console.print("\n[#E8C4F0]⚠️  建議在虛擬環境中安裝[/#E8C4F0]")
        console.print("   [dim]如果尚未建立虛擬環境，可執行：[/dim]")
        console.print(Panel(
            "python3 -m venv venv\nsource venv/bin/activate  # macOS/Linux\nvenv\\Scripts\\activate  # Windows",
            border_style="#E8C4F0",
            title="建立並啟用虛擬環境",
            padding=(0, 1)
        ))

    console.print("\n[#E8C4F0]⏸️  安裝完成後，請重新執行程式[/#E8C4F0]\n")


# ==================== 輔助函數 ====================

def _check_command(command: str) -> bool:
    """
    檢查命令是否存在

    Args:
        command: 命令名稱

    Returns:
        命令是否存在
    """
    try:
        subprocess.run(
            [command, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _detect_linux_distro() -> Optional[str]:
    """
    偵測 Linux 發行版

    Returns:
        發行版名稱（ubuntu, debian, fedora, centos, rhel, arch）或 None
    """
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = f.read().lower()

        if 'ubuntu' in os_info:
            return 'ubuntu'
        elif 'debian' in os_info:
            return 'debian'
        elif 'fedora' in os_info:
            return 'fedora'
        elif 'centos' in os_info:
            return 'centos'
        elif 'rhel' in os_info or 'red hat' in os_info:
            return 'rhel'
        elif 'arch' in os_info:
            return 'arch'
    except:
        pass

    return None


def _detect_shell() -> str:
    """
    偵測當前 Shell

    Returns:
        shell 名稱（zsh, bash, 等）
    """
    import os
    shell = os.environ.get('SHELL', '')
    if 'zsh' in shell:
        return 'zsh'
    elif 'bash' in shell:
        return 'bash'
    else:
        return 'unknown'


def _check_virtualenv() -> bool:
    """
    檢查是否在虛擬環境中

    Returns:
        是否在虛擬環境中
    """
    import sys
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )


def suggest_file_corrupted(file_path: str, ffprobe_error: str = "") -> None:
    """
    顯示檔案損壞的修復建議

    提供多種修復選項：
    1. 重新封裝（-c copy）
    2. 重新編碼（-c:v libx264 -c:a aac）
    3. 驗證檔案完整性（ffprobe -v error）
    4. 重新獲取檔案

    Args:
        file_path: 損壞的檔案路徑
        ffprobe_error: ffprobe 錯誤訊息
    """
    console.print(f"\n[dim #E8C4F0]✗ 檔案格式錯誤或損壞：{file_path}[/red]\n")

    # 顯示錯誤詳細資訊
    if ffprobe_error:
        console.print("[#E8C4F0]詳細資訊：[/#E8C4F0]")
        # 只顯示前3行錯誤
        error_lines = ffprobe_error.strip().split('\n')[:3]
        for line in error_lines:
            console.print(f"  {line}")
        console.print()

    # 顯示檔案資訊
    if os.path.isfile(file_path):
        size = os.path.getsize(file_path) / (1024 * 1024)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

        console.print("[#E8C4F0]檔案資訊：[/#E8C4F0]")
        console.print(f"  - 大小：{size:.1f} MB")
        console.print(f"  - 建立時間：{mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print()

    console.print("[#E8C4F0]💡 修復選項：[/#E8C4F0]\n")

    # ==================== 選項 1：重新封裝 ====================
    console.print("[bold]🔧 選項 1：嘗試修復檔案（重新封裝，推薦）[/bold]\n")
    console.print("   此方法適用於輕微損壞的檔案，成功率約 70%\n")

    repaired_path = f"{Path(file_path).stem}_repaired{Path(file_path).suffix}"
    repaired_full_path = os.path.join(os.path.dirname(file_path), repaired_path)

    console.print("   執行指令：")
    console.print(Panel(
        f'ffmpeg -i "{file_path}"\n'
        f'       -c copy\n'
        f'       "{repaired_full_path}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0003", fallback="修復檔案")
    ))

    console.print("\n   [#E8C4F0]⚠️  注意：[/#E8C4F0]")
    console.print("   - 原檔案不會被修改")
    console.print("   - 修復後檔案會略小（去除損壞部分）")
    console.print("   - 如果修復失敗，請嘗試選項 2")
    console.print()

    # ==================== 選項 2：重新編碼 ====================
    console.print("[bold]🔧 選項 2：重新編碼檔案（強制轉換）[/bold]\n")
    console.print("   此方法成功率更高，但會重新編碼（較慢）\n")

    converted_path = f"{Path(file_path).stem}_converted.mp4"
    converted_full_path = os.path.join(os.path.dirname(file_path), converted_path)

    console.print("   執行指令：")
    console.print(Panel(
        f'ffmpeg -i "{file_path}"\n'
        f'       -c:v libx264 -c:a aac\n'
        f'       "{converted_full_path}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0004", fallback="重新編碼")
    ))

    # 估算處理時間
    if os.path.isfile(file_path):
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        estimated_minutes = max(1, int(size_mb / 20))  # 假設 20 MB/分鐘
        console.print(f"\n   [dim]預估時間：約 {estimated_minutes} 分鐘（視檔案大小而定）[/dim]")
    console.print()

    # ==================== 選項 3：驗證 ====================
    console.print("[bold]⚡ 選項 3：驗證檔案完整性[/bold]\n")
    console.print("   先檢查檔案的詳細錯誤資訊：")
    console.print(Panel(
        f'ffprobe -v error "{file_path}"',
        border_style="#E8C4F0"
    ))
    console.print()

    # ==================== 選項 4：重新獲取 ====================
    console.print("[bold]🔄 選項 4：重新獲取檔案[/bold]\n")
    console.print("   如果檔案確實損壞且無法修復：\n")
    console.print("   1. 確認檔案來源（雲端、網路下載等）")
    console.print("   2. 重新下載或複製檔案")
    console.print("   3. 驗證檔案完整性：")
    console.print("      - 檢查檔案大小是否正確")
    console.print("      - 比對 MD5/SHA256 校驗碼（如有提供）")
    console.print("   4. 重新執行操作")
    console.print()

    # ==================== 常見原因 ====================
    console.print("[bold #E8C4F0]📝 常見損壞原因：[/bold #E8C4F0]")
    console.print("   - 下載未完成或中斷")
    console.print("   - 傳輸過程中發生錯誤")
    console.print("   - 儲存媒體故障")
    console.print("   - 檔案系統錯誤")
    console.print("   - 不當的檔案轉換")
    console.print()

    console.print("[bold #E8C4F0]✅ 修復成功後：[/bold green]")
    console.print("   重新執行原始指令，使用修復後的檔案路徑\n")


def try_fix_json(json_text: str) -> tuple[Optional[str], List[str]]:
    """
    嘗試自動修復常見的 JSON 格式錯誤

    Args:
        json_text: 原始 JSON 文字

    Returns:
        (修復後的 JSON 文字, 套用的修復列表)，如果無法修復則返回 (None, 修復列表)
    """
    import re
    import json

    fixed_text = json_text
    fixes_applied = []

    # 1. 移除 JavaScript 風格的註解
    if "//" in fixed_text or "/*" in fixed_text:
        # 移除單行註解
        fixed_text = re.sub(r'//.*?$', '', fixed_text, flags=re.MULTILINE)
        # 移除多行註解
        fixed_text = re.sub(r'/\*.*?\*/', '', fixed_text, flags=re.DOTALL)
        fixes_applied.append("移除註解")

    # 2. 修復缺少引號的屬性名
    # 匹配類似 start: 0.0 的模式，改為 "start": 0.0
    if re.search(r'(\n\s+)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', fixed_text):
        fixed_text = re.sub(
            r'(\n\s+)([a-zA-Z_][a-zA-Z0-9_]*)\s*:',
            r'\1"\2":',
            fixed_text
        )
        fixes_applied.append("修復缺少引號的屬性名")

    # 3. 移除尾隨逗號
    if re.search(r',\s*([}\]])', fixed_text):
        fixed_text = re.sub(r',\s*([}\]])', r'\1', fixed_text)
        fixes_applied.append("移除尾隨逗號")

    # 4. 修復單引號（替換為雙引號）
    # 注意：這可能在某些情況下造成問題，所以要小心處理
    if "'" in fixed_text:
        # 只替換看起來像 JSON 屬性的單引號
        fixed_text = re.sub(r"'([^']*)'(\s*:)", r'"\1"\2', fixed_text)
        fixes_applied.append("替換單引號為雙引號")

    # 5. 驗證修復後的 JSON
    try:
        json.loads(fixed_text)
        return fixed_text, fixes_applied
    except json.JSONDecodeError:
        return None, fixes_applied


def suggest_json_parse_failed(
    json_text: str,
    error_message: str,
    context: str = "語音辨識"
) -> Optional[str]:
    """
    顯示 JSON 解析失敗的修復建議

    提供多種修復選項：
    1. 自動修復 JSON 格式（推薦）
    2. 重新請求 Gemini 生成
    3. 查看完整回應
    4. 手動修復後重新導入

    Args:
        json_text: 原始 JSON 文字
        error_message: 錯誤訊息
        context: 錯誤發生的上下文（預設：語音辨識）

    Returns:
        修復後的 JSON 文字（如果自動修復成功），否則返回 None
    """
    console.print(f"\n[dim #E8C4F0]✗ {context}結果解析失敗[/red]\n")

    # 顯示錯誤訊息
    console.print(f"[#E8C4F0]JSON 解析錯誤：{error_message}[/#E8C4F0]\n")

    # 顯示原始回應預覽
    preview_length = 500
    preview_text = json_text[:preview_length]
    if len(json_text) > preview_length:
        preview_text += "\n... (已截斷)"

    console.print("[#E8C4F0]原始回應預覽（前 500 字元）：[/#E8C4F0]")
    console.print(Panel(
        preview_text,
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0005", fallback="JSON 內容")
    ))
    console.print()

    console.print("[#E8C4F0]💡 修復選項：[/#E8C4F0]\n")

    # ==================== 選項 1：自動修復 JSON ====================
    console.print("[bold]🔄 選項 1：自動修復 JSON 格式（推薦）[/bold]\n")
    console.print("   嘗試修復常見 JSON 格式錯誤...\n")

    fixed_json, fixes = try_fix_json(json_text)

    if fixed_json:
        # 修復成功
        console.print("[#E8C4F0]   ✓ JSON 修復成功！[/green]\n")
        if fixes:
            console.print("   [dim]已套用的修復：[/dim]")
            for fix in fixes:
                console.print(f"   [#E8C4F0]✓[/green] {fix}")
        console.print()
        console.print("   [bold #E8C4F0]已自動使用修復後的 JSON 繼續處理[/bold green]")
        console.print()
        return fixed_json
    else:
        # 修復失敗
        console.print("   [#E8C4F0]✗ 自動修復失敗[/#E8C4F0]")
        if fixes:
            console.print("   [dim]已嘗試：[/dim]")
            for fix in fixes:
                console.print(f"   • {fix}")
        console.print("\n   請嘗試選項 2 或 3\n")

    # ==================== 選項 2：重新請求 ====================
    console.print("[bold]⚡ 選項 2：重新請求 Gemini 生成（自動重試）[/bold]\n")
    console.print("   程式將自動重新請求 Gemini API（最多重試 3 次）")
    console.print("   [dim]此選項需要在程式碼中實作重試邏輯[/dim]")
    console.print()

    # ==================== 選項 3：查看完整回應 ====================
    console.print("[bold]📝 選項 3：查看完整回應[/bold]\n")

    # 保存完整回應到臨時檔案
    import tempfile

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_file = os.path.join(
        tempfile.gettempdir(),
        f"gemini_response_failed_{timestamp}.txt"
    )

    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(json_text)
        console.print(f"   完整回應已保存至：")
        console.print(f"   [#E8C4F0]{temp_file}[/#E8C4F0]\n")

        console.print("   執行指令查看：")
        console.print(Panel(
            f'cat "{temp_file}"',
            border_style="#E8C4F0"
        ))
    except Exception as e:
        console.print(f"   [#E8C4F0]⚠️  無法保存檔案：{e}[/#E8C4F0]")
    console.print()

    # ==================== 選項 4：手動修復 ====================
    console.print("[bold]🔧 選項 4：手動修復後重新導入[/bold]\n")
    console.print("   1. 編輯保存的回應檔案")
    console.print("   2. 修復 JSON 格式錯誤")
    console.print("   3. 使用以下指令重新導入：\n")

    console.print(Panel(
        f'# 範例：手動修復後重新處理\n'
        f'# （需要自行實作導入功能）\n'
        f'python import_subtitles.py "{temp_file}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0006", fallback="手動修復")
    ))
    console.print()

    # ==================== 重試失敗建議 ====================
    console.print("[bold #E8C4F0]⚠️  若重試 3 次仍失敗：[/bold #E8C4F0]\n")

    console.print("   可能原因：")
    console.print("   1. 音訊品質過差（噪音過多、不清晰）")
    console.print("   2. 音訊語言不明確")
    console.print("   3. Gemini API 暫時性問題")
    console.print("   4. 音訊內容過於複雜或特殊")
    console.print()

    console.print("   建議：")
    console.print("   1. 檢查音訊品質，必要時重新錄製")
    console.print("   2. 明確指定音訊語言（如：中文、英文）")
    console.print("   3. 嘗試較短的音訊片段（< 5 分鐘）")
    console.print("   4. 稍後重試（API 可能暫時繁忙）")
    console.print("   5. 檢查 Gemini API 配額限制")
    console.print()

    return None


def suggest_video_file_not_found(file_path: str, auto_fix: bool = True) -> Optional[str]:
    """
    顯示影片檔案不存在的修復建議並提供一鍵修復（專門針對影片）

    Args:
        file_path: 找不到的影片檔案路徑
        auto_fix: 是否提供自動修復選項（預設 True）

    Returns:
        Optional[str]: 如果用戶選擇了替代檔案，返回新路徑；否則返回 None
    """
    console.print(f"\n[bold red]✗ 影片檔案不存在[/bold red]")
    console.print(f"\n[dim]找不到：{file_path}[/dim]\n")

    # 常見影片格式
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}

    # 搜尋相似影片檔案
    directory = os.path.dirname(file_path) or '.'
    filename = os.path.basename(file_path)

    similar_files = []

    if os.path.isdir(directory):
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if not os.path.isfile(item_path):
                    continue

                # 只考慮影片檔案
                item_ext = os.path.splitext(item)[1].lower()
                if item_ext not in VIDEO_EXTENSIONS:
                    continue

                # 計算檔名相似度
                similarity = SequenceMatcher(None, filename.lower(), item.lower()).ratio()

                # 如果相似度 > 0.6 或檔名前 5 個字元相符，則加入候選
                if similarity > 0.6 or filename.lower()[:5] in item.lower():
                    size = os.path.getsize(item_path)
                    mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                    similar_files.append((item, size, mtime, similarity, item_path))

            # 按相似度排序 (保留所有，不限制數量)
            similar_files.sort(key=lambda x: x[3], reverse=True)

            if similar_files:
                # 轉換為字典格式供智能選擇器使用
                similar_files_dict = []
                for (name, size, mtime, similarity, full_path) in similar_files:
                    # 計算時間差顯示
                    now = datetime.now()
                    time_diff = now - mtime
                    if time_diff.days > 0:
                        time_ago = f"{time_diff.days} 天前"
                    elif time_diff.seconds > 3600:
                        time_ago = f"{time_diff.seconds // 3600} 小時前"
                    elif time_diff.seconds > 60:
                        time_ago = f"{time_diff.seconds // 60} 分鐘前"
                    else:
                        time_ago = safe_t("error_handler.error_fix_suggestions.msg_0007", fallback="剛才")

                    similar_files_dict.append({
                        'name': name,
                        'path': full_path,
                        'size': size,
                        'similarity': similarity,
                        'time_ago': time_ago,
                        'modified_time': mtime.timestamp()
                    })

                # 🎯 使用智能檔案選擇器 (C-2/C-3 違規修復)
                if auto_fix:
                    try:
                        selector = SmartFileSelector()
                        selected_files = selector.smart_select(similar_files_dict)

                        if selected_files:
                            selected_path = selected_files[0]['path']

                            if len(selected_files) > 1:
                                console.print(
                                    f"\n[#B565D8]ℹ️ 您選擇了 {len(selected_files)} 個檔案，"
                                    f"當前將使用: {selected_files[0]['name']}[/#B565D8]\n"
                                )
                            else:
                                console.print(f"\n[#B565D8]✅ 已選擇: {selected_files[0]['name']}[/#B565D8]")

                            simplified_path = _simplify_path(selected_path)
                            console.print(f"[dim]路徑: {simplified_path}[/dim]\n")
                            return selected_path
                        else:
                            console.print("\n[#E8C4F0]已取消選擇[/#E8C4F0]")
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[#E8C4F0]已取消[/#E8C4F0]")
                    except Exception as e:
                        console.print(f"\n[#E8C4F0]選擇器錯誤: {e}[/#E8C4F0]")

        except Exception:
            pass

    # 搜尋指令
    console.print("[bold #E8C4F0]🔍 在目錄中搜尋[/bold green]")
    console.print("   執行以下指令：")
    search_term = os.path.splitext(filename)[0][:10]  # 取檔名前10字元
    console.print(Panel(
        f'find {directory} -name "*{search_term}*" -type f',
        border_style="#E8C4F0",
        padding=(0, 2)
    ))

    # 常見原因
    console.print("\n[#E8C4F0]📝 常見原因：[/#E8C4F0]")
    console.print("   • 檔案路徑拼寫錯誤")
    console.print("   • 檔案已被移動或刪除")
    console.print("   • 使用了相對路徑（建議使用絕對路徑）\n")

    return None


def suggest_invalid_watermark_params(
    opacity: Optional[float] = None,
    position: Optional[str] = None,
    supported_positions: Optional[Dict[str, str]] = None
) -> None:
    """
    顯示浮水印參數無效的修復建議

    提供正確的參數設定指引：
    1. 不透明度範圍和常用值
    2. 支援的位置選項
    3. 正確使用範例

    Args:
        opacity: 無效的不透明度值（如果有）
        position: 無效的位置值（如果有）
        supported_positions: 支援的位置字典
    """
    console.print(f"\n[bold red]✗ 浮水印參數無效[/bold red]\n")

    # 診斷問題
    has_opacity_error = False
    has_position_error = False

    if opacity is not None and (opacity < 0.0 or opacity > 1.0):
        console.print(f"[dim #E8C4F0]問題 1: 不透明度 {opacity} 超出範圍[/red]")
        has_opacity_error = True

    if position is not None and supported_positions is not None:
        if position not in supported_positions:
            console.print(f"[dim #E8C4F0]問題 2: 不支援的位置 {position}[/red]")
            has_position_error = True

    console.print("\n[bold #E8C4F0]💡 正確參數設定：[/bold #E8C4F0]\n")

    # ==================== 不透明度說明 ====================
    console.print("[bold]📊 不透明度 (opacity)[/bold]")
    console.print("   範圍：0.0 ~ 1.0\n")
    console.print("   常用值：")
    console.print("   • 1.0 - 完全不透明（100%）")
    console.print("   • 0.7 - 半透明（推薦）")
    console.print("   • 0.5 - 中度透明")
    console.print("   • 0.3 - 高度透明")
    console.print("   • 0.0 - 完全透明（隱形）")

    # 如果有不透明度錯誤，給出修正建議
    if has_opacity_error:
        if opacity > 1.0:
            suggested = 1.0
            console.print(f"\n   [#E8C4F0]💡 建議：將 {opacity} 改為 {suggested}[/#E8C4F0]")
        elif opacity < 0.0:
            suggested = 0.0
            console.print(f"\n   [#E8C4F0]💡 建議：將 {opacity} 改為 {suggested}[/#E8C4F0]")
    console.print()

    # ==================== 位置說明 ====================
    console.print("[bold]📍 位置 (position)[/bold]")
    console.print("   支援的位置：\n")

    if supported_positions:
        for pos_name, pos_desc in [
            ('top-left', '左上角'),
            ('top-right', '右上角'),
            ('bottom-left', '左下角（常用）'),
            ('bottom-right', '右下角（最常用）')
        ]:
            if pos_name in supported_positions:
                console.print(f"   • {pos_name:<15} - {pos_desc}")

        # 如果還有其他支援的位置
        extra_positions = set(supported_positions.keys()) - {
            'top-left', 'top-right', 'bottom-left', 'bottom-right'
        }
        if extra_positions:
            for pos_name in sorted(extra_positions):
                console.print(f"   • {pos_name}")
    else:
        console.print("   • top-left      - 左上角")
        console.print("   • top-right     - 右上角")
        console.print("   • bottom-left   - 左下角（常用）")
        console.print("   • bottom-right  - 右下角（最常用）")

    # 如果有位置錯誤，給出修正建議
    if has_position_error:
        # 嘗試找出最相似的位置
        if supported_positions:
            from difflib import get_close_matches
            matches = get_close_matches(position, supported_positions.keys(), n=1, cutoff=0.3)
            if matches:
                console.print(f"\n   [#E8C4F0]💡 建議：將 '{position}' 改為 '{matches[0]}'[/#E8C4F0]")
            else:
                console.print(f"\n   [#E8C4F0]💡 建議：使用 'bottom-right'（最常用）[/#E8C4F0]")

    console.print()

    # ==================== 使用範例 ====================
    console.print("[bold #E8C4F0]⚡ 正確使用範例：[/bold green]")

    # 根據錯誤類型顯示修正後的範例
    example_opacity = 0.7
    example_position = "bottom-right"

    if has_opacity_error:
        if opacity > 1.0:
            example_opacity = 1.0
        elif opacity < 0.0:
            example_opacity = 0.0
        else:
            example_opacity = 0.7

    if has_position_error and supported_positions:
        from difflib import get_close_matches
        matches = get_close_matches(position, supported_positions.keys(), n=1, cutoff=0.3)
        if matches:
            example_position = matches[0]

    console.print(Panel(
        f'add_watermark(\n'
        f'    video_path,\n'
        f'    watermark_path,\n'
        f'    position="{example_position}",\n'
        f'    opacity={example_opacity}\n'
        f')',
        border_style="#E8C4F0",
        padding=(0, 2)
    ))
    console.print()



def suggest_video_transcode_failed(
    input_path: str,
    output_path: str,
    stderr: str
) -> None:
    """
    顯示影片轉碼失敗的修復建議

    提供診斷和解決方案：
    1. 缺少編碼器（libx264）
    2. 磁碟空間不足
    3. 輸入檔案損壞
    4. 替代方案：使用 copy 模式

    Args:
        input_path: 輸入影片路徑
        output_path: 輸出影片路徑
        stderr: ffmpeg 錯誤訊息
    """
    console.print(f"\n[bold red]✗ 影片轉碼失敗[/bold red]\n")
    console.print(f"[dim]輸入檔案：{input_path}[/dim]")
    console.print(f"[dim]輸出檔案：{output_path}[/dim]\n")

    console.print("[bold]錯誤詳情：[/bold]")
    # 限制錯誤訊息長度，避免過長
    error_preview = stderr[:300] if len(stderr) > 300 else stderr
    if len(stderr) > 300:
        error_preview += "\n... (錯誤訊息已截斷)"
    console.print(f"[dim #E8C4F0]{error_preview}[/red]\n")

    console.print("[bold #E8C4F0]💡 診斷與解決：[/bold #E8C4F0]\n")

    console.print("[#E8C4F0]⚠️  常見錯誤原因：[/#E8C4F0]\n")

    # ==================== 原因 1：缺少編碼器 ====================
    if "not found" in stderr.lower() or "encoder" in stderr.lower() or "codec" in stderr.lower():
        console.print("[bold]1️⃣ 缺少編碼器 (libx264 或其他編碼器)[/bold]")
        console.print("   解決：重新安裝完整版 ffmpeg\n")

        system = platform.system()
        if system == "Darwin":
            console.print("   macOS:")
            console.print(Panel(
                "brew reinstall ffmpeg",
                border_style="#E8C4F0",
                padding=(0, 2)
            ))
            console.print("\n   [dim]如需完整編碼器支援：[/dim]")
            console.print(Panel(
                "brew install ffmpeg --with-libx264 --with-libx265",
                border_style="#E8C4F0",
                padding=(0, 2)
            ))
        elif system == "Linux":
            console.print("   Linux (Ubuntu/Debian):")
            console.print(Panel(
                "sudo apt update\nsudo apt install ffmpeg libx264-dev libx265-dev",
                border_style="#E8C4F0",
                padding=(0, 2)
            ))
            console.print("\n   Linux (Fedora/CentOS):")
            console.print(Panel(
                "sudo dnf install ffmpeg x264-devel x265-devel",
                border_style="#E8C4F0",
                padding=(0, 2)
            ))
        else:
            console.print("   請參考 ffmpeg 官方網站下載完整版本")
        console.print()

    # ==================== 原因 2：磁碟空間不足 ====================
    if "no space" in stderr.lower() or "disk" in stderr.lower():
        console.print("[bold]2️⃣ 磁碟空間不足（已檢測到相關錯誤）[/bold]")
    else:
        console.print("[bold]2️⃣ 磁碟空間不足（可能原因）[/bold]")

    console.print("   檢查可用空間：")

    parent_dir = os.path.dirname(output_path) or '.'
    console.print(Panel(
        f"df -h {parent_dir}",
        border_style="#E8C4F0",
        padding=(0, 2)
    ))
    console.print()

    # ==================== 原因 3：檔案損壞 ====================
    if "invalid" in stderr.lower() or "corrupt" in stderr.lower() or "moov" in stderr.lower():
        console.print("[bold]3️⃣ 輸入檔案損壞（已檢測到相關錯誤）[/bold]")
    else:
        console.print("[bold]3️⃣ 輸入檔案損壞（可能原因）[/bold]")

    console.print("   驗證檔案：")
    console.print(Panel(
        f'ffmpeg -v error -i "{input_path}" -f null -',
        border_style="#E8C4F0",
        padding=(0, 2)
    ))
    console.print("\n   [dim]如果顯示錯誤，表示檔案確實損壞[/dim]")
    console.print()

    # ==================== 替代方案 ====================
    console.print("[bold #E8C4F0]🔧 嘗試使用不同的編碼參數[/bold green]\n")

    console.print("   [bold]方案 1：僅複製串流（最快，不重新編碼）[/bold]")
    console.print(Panel(
        f'ffmpeg -i "{input_path}"\n'
        f'       -c:v copy -c:a copy\n'
        f'       "{output_path}"',
        border_style="#E8C4F0",
        padding=(0, 2),
        title=safe_t("error_handler.error_fix_suggestions.msg_0008", fallback="快速複製")
    ))
    console.print("   [dim]優點：速度極快，無品質損失[/dim]")
    console.print("   [dim]缺點：無法改變格式或解析度[/dim]\n")

    console.print("   [bold]方案 2：使用不同的編碼器（相容性更好）[/bold]")
    console.print(Panel(
        f'ffmpeg -i "{input_path}"\n'
        f'       -c:v libx264 -preset fast -crf 23\n'
        f'       -c:a aac -b:a 128k\n'
        f'       "{output_path}"',
        border_style="#E8C4F0",
        padding=(0, 2),
        title=safe_t("error_handler.error_fix_suggestions.msg_0009", fallback="標準編碼")
    ))
    console.print("   [dim]優點：相容性好，可調整參數[/dim]")
    console.print("   [dim]缺點：速度較慢[/dim]\n")

    console.print("   [bold]方案 3：降低品質以加快速度[/bold]")
    console.print(Panel(
        f'ffmpeg -i "{input_path}"\n'
        f'       -c:v libx264 -preset ultrafast -crf 28\n'
        f'       -c:a copy\n'
        f'       "{output_path}"',
        border_style="#E8C4F0",
        padding=(0, 2),
        title=safe_t("error_handler.error_fix_suggestions.msg_0010", fallback="快速編碼")
    ))
    console.print("   [dim]優點：速度快[/dim]")
    console.print("   [dim]缺點：品質稍降[/dim]\n")

    # ==================== 進階診斷 ====================
    console.print("[bold #E8C4F0]🔍 進階診斷：[/bold #E8C4F0]")
    console.print("   1. 檢查 ffmpeg 版本和支援的編碼器：")
    console.print(Panel("ffmpeg -codecs | grep x264", border_style="#E8C4F0", padding=(0, 2)))
    console.print("\n   2. 查看完整的 ffmpeg 輸出（用於診斷）：")
    console.print(Panel(
        f'ffmpeg -i "{input_path}" "{output_path}"',
        border_style="#E8C4F0",
        padding=(0, 2)
    ))
    console.print()


def suggest_video_upload_failed(
    file_path: str,
    error_message: str,
    uploaded_bytes: Optional[int] = None
) -> None:
    """
    顯示影片上傳失敗的修復建議

    提供多種解決方案：
    1. 自動重試上傳（使用更長的超時時間）
    2. 壓縮影片後重試（快速壓縮和最佳壓縮）
    3. 分割影片後逐段處理
    4. 檢查網路連線
    5. Gemini API 檔案大小限制說明
    6. 故障排除建議

    Args:
        file_path: 影片檔案路徑
        error_message: 錯誤訊息
        uploaded_bytes: 已上傳的位元組數（可選）
    """
    console.print(f"\n[dim #E8C4F0]✗ 影片上傳失敗：{error_message}[/red]\n")

    # ==================== 檔案資訊 ====================
    if os.path.isfile(file_path):
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)

        # 獲取影片時長
        duration_str = safe_t("error_handler.error_fix_suggestions.msg_0011", fallback="未知")
        try:
            import subprocess
            import json
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                 '-show_format', file_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                duration_str = f"{int(duration//60)}:{int(duration%60):02d}"
        except Exception:
            pass

        console.print("[#E8C4F0]檔案資訊：[/#E8C4F0]")
        console.print(f"  - 路徑：{file_path}")
        console.print(f"  - 大小：{size_mb:.1f} MB")
        console.print(f"  - 時長：{duration_str}")
        console.print()

        # 上傳進度
        if uploaded_bytes:
            progress_pct = (uploaded_bytes / size_bytes) * 100
            uploaded_mb = uploaded_bytes / (1024 * 1024)
            console.print(f"上傳進度：已上傳 {uploaded_mb:.1f} MB / {size_mb:.1f} MB ({progress_pct:.0f}%)")
            console.print()
    else:
        console.print(f"[#E8C4F0]⚠️  無法讀取檔案資訊：{file_path}[/#E8C4F0]\n")
        size_mb = 0  # 預設值

    console.print("[#E8C4F0]💡 解決方案：[/#E8C4F0]\n")

    # ==================== 選項 1：自動重試 ====================
    console.print("[bold]🔄 選項 1：自動重試上傳（推薦）[/bold]\n")
    console.print("   [Y] 是 - 立即重試（使用更長的超時時間：180秒）")
    console.print("   [N] 否 - 查看其他選項")
    console.print()

    # ==================== 選項 2：壓縮影片 ====================
    console.print("[bold]⚡ 選項 2：壓縮影片後重試[/bold]\n")
    console.print("   目標大小：50-80 MB（成功率 >95%）\n")

    if os.path.isfile(file_path):
        # 快速壓縮
        console.print("   快速壓縮（降低解析度）：")
        compressed_path = f"{Path(file_path).stem}_compressed{Path(file_path).suffix}"
        compressed_full_path = os.path.join(os.path.dirname(file_path), compressed_path)

        console.print(Panel(
            f'ffmpeg -i "{file_path}"\n'
            f'       -vf "scale=1280:-2"\n'
            f'       -c:v libx264 -crf 28\n'
            f'       -c:a aac -b:a 128k\n'
            f'       "{compressed_full_path}"',
            border_style="#E8C4F0"
        ))

        # 估算時間和大小
        est_minutes = max(3, int(size_mb / 50))
        est_size_min = int(size_mb * 0.25)
        est_size_max = int(size_mb * 0.35)

        console.print(f"\n   [dim]預估時間：約 {est_minutes}-{est_minutes+2} 分鐘[/dim]")
        console.print(f"   [dim]預估壓縮後大小：{est_size_min}-{est_size_max} MB[/dim]\n")

        # 最佳壓縮
        console.print("   最佳壓縮（保持解析度，降低畫質）：")
        optimized_path = f"{Path(file_path).stem}_optimized{Path(file_path).suffix}"
        optimized_full_path = os.path.join(os.path.dirname(file_path), optimized_path)

        console.print(Panel(
            f'ffmpeg -i "{file_path}"\n'
            f'       -c:v libx264 -crf 32\n'
            f'       -preset fast\n'
            f'       -c:a aac -b:a 96k\n'
            f'       "{optimized_full_path}"',
            border_style="#E8C4F0"
        ))

        est_size_min2 = int(size_mb * 0.20)
        est_size_max2 = int(size_mb * 0.28)
        console.print(f"\n   [dim]預估時間：約 {est_minutes+1}-{est_minutes+3} 分鐘[/dim]")
        console.print(f"   [dim]預估壓縮後大小：{est_size_min2}-{est_size_max2} MB[/dim]")
    console.print()

    # ==================== 選項 3：分割影片 ====================
    console.print("[bold]📝 選項 3：分割影片後逐段處理[/bold]\n")
    console.print("   將影片分割成多個片段，逐段上傳並分析\n")
    console.print("   分割為 5 分鐘片段：")

    if os.path.isfile(file_path):
        segment_pattern = os.path.join(os.path.dirname(file_path), "segment_%03d.mp4")
        console.print(Panel(
            f'ffmpeg -i "{file_path}"\n'
            f'       -c copy -f segment\n'
            f'       -segment_time 300\n'
            f'       -reset_timestamps 1\n'
            f'       "{segment_pattern}"',
            border_style="#E8C4F0"
        ))
    else:
        console.print(Panel(
            f'ffmpeg -i "/path/to/video.mp4"\n'
            f'       -c copy -f segment\n'
            f'       -segment_time 300\n'
            f'       -reset_timestamps 1\n'
            f'       "segment_%03d.mp4"',
            border_style="#E8C4F0"
        ))

    console.print("\n   [dim]將生成：segment_001.mp4, segment_002.mp4, ...[/dim]")
    console.print()

    # ==================== 選項 4：網路診斷 ====================
    console.print("[bold]🔍 選項 4：檢查網路連線[/bold]\n")
    console.print("   執行網路診斷：")
    console.print(Panel("ping -c 5 google.com", border_style="#E8C4F0"))
    console.print("\n   測試上傳速度：")
    console.print(Panel(
        "curl -o /dev/null http://speedtest.wdc01.softlayer.com/downloads/test100.zip",
        border_style="#E8C4F0"
    ))
    console.print()

    # ==================== API 限制說明 ====================
    console.print("[bold #E8C4F0]📊 Gemini API 檔案大小限制：[/bold #E8C4F0]")
    console.print("   - 免費版：最大 20 MB")
    console.print("   - 付費版：最大 2 GB")
    console.print("   - 建議大小：< 100 MB（最佳上傳速度）")
    console.print()

    # ==================== 故障排除 ====================
    console.print("[bold #E8C4F0]⚠️  故障排除：[/bold #E8C4F0]")
    console.print("   1. 確認網路連線穩定")
    console.print("   2. 確認是否在限制時間內（免費版可能有限制）")
    console.print("   3. 嘗試分時段上傳（避開尖峰時段）")
    console.print("   4. 使用有線網路而非 Wi-Fi（如可能）")
    console.print()


def suggest_empty_file(file_path: str) -> None:
    """
    顯示空檔案的診斷和修復建議

    提供多種可能原因和解決方案：
    1. 下載未完成或中斷
    2. 檔案傳輸過程中斷
    3. 磁碟空間不足導致寫入失敗
    4. 檔案系統錯誤

    Args:
        file_path: 空檔案路徑
    """
    console.print(f"\n[dim #E8C4F0]✗ 檔案為空（0 bytes）：{file_path}[/red]\n")

    # ==================== 檔案資訊 ====================
    if os.path.exists(file_path):
        from datetime import datetime
        ctime = datetime.fromtimestamp(os.path.getctime(file_path))
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

        console.print("[#E8C4F0]檔案資訊：[/#E8C4F0]")
        console.print(f"  - 路徑：{file_path}")
        console.print(f"  - 大小：0 bytes")
        console.print(f"  - 建立時間：{ctime.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"  - 修改時間：{mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        # 如果建立和修改時間相同，可能是傳輸失敗
        if abs((mtime - ctime).total_seconds()) < 1:
            console.print("\n  [#E8C4F0]⚠️  建立和修改時間幾乎相同，可能是傳輸失敗[/#E8C4F0]")

        console.print()

    console.print("[#E8C4F0]💡 可能的原因與解決方案：[/#E8C4F0]\n")

    # ==================== 原因 1：下載未完成 ====================
    console.print("[bold]🔍 原因 1：下載未完成或中斷[/bold]\n")
    console.print("   檢查步驟：")
    console.print("   1. 確認下載是否已完成")
    console.print("   2. 檢查下載工具是否報錯")
    console.print("   3. 查看預期檔案大小（如果已知）\n")

    console.print("   解決方案：")
    console.print("   - 重新下載檔案")
    console.print("   - 使用支援斷點續傳的下載工具（如 wget, curl -C -）\n")

    console.print("   執行指令（使用 wget 續傳）：")
    console.print(Panel(
        'wget -c "https://example.com/video.mp4"\n'
        f'     -O "{file_path}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0012", fallback="斷點續傳下載")
    ))
    console.print()

    # ==================== 原因 2：傳輸中斷 ====================
    console.print("[bold]🔍 原因 2：檔案傳輸過程中斷[/bold]\n")
    console.print("   檢查步驟：")
    console.print("   1. 確認傳輸來源是否可達")
    console.print("   2. 檢查網路連線狀態")
    console.print("   3. 驗證來源檔案是否完整\n")

    console.print("   解決方案：")
    console.print("   - 重新複製/傳輸檔案")
    console.print("   - 使用可靠的傳輸方式（rsync, scp）\n")

    console.print("   執行指令（使用 rsync）：")
    console.print(Panel(
        f'rsync -avz --progress source:/path/to/video.mp4\n'
        f'      "{file_path}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0013", fallback="可靠傳輸")
    ))
    console.print()

    # ==================== 原因 3：磁碟空間不足 ====================
    console.print("[bold]🔍 原因 3：磁碟空間不足導致寫入失敗[/bold]\n")
    console.print("   檢查步驟：")
    console.print("   執行指令檢查磁碟空間：")

    parent_dir = os.path.dirname(file_path) or '.'
    console.print(Panel(f'df -h {parent_dir}', border_style="#E8C4F0"))

    console.print("\n   解決方案：")
    console.print("   - 清理磁碟空間")
    console.print("   - 使用空間充足的目錄")
    console.print()

    # ==================== 原因 4：檔案系統錯誤 ====================
    console.print("[bold]🔍 原因 4：檔案系統錯誤[/bold]\n")
    console.print("   檢查步驟：")
    console.print("   - 檢查檔案系統是否有錯誤")
    console.print("   - 確認檔案權限是否正確\n")

    console.print("   解決方案：")

    system = platform.system()
    if system == "Darwin":
        console.print("   執行指令檢查檔案系統（macOS）：")
        console.print(Panel('diskutil verifyVolume /', border_style="#E8C4F0"))
    elif system == "Linux":
        console.print("   執行指令檢查檔案系統（Linux）：")
        console.print(Panel('sudo fsck /dev/sdX  # 替換為實際裝置', border_style="#E8C4F0"))
    console.print()

    # ==================== 清理空檔案 ====================
    console.print("[bold]🗑️  清理空檔案：[/bold]\n")
    console.print("   執行指令刪除空檔案：")
    console.print(Panel(f'rm "{file_path}"', border_style="red", title="刪除檔案"))

    console.print("\n   或搜尋並刪除所有空檔案（小心使用）：")
    console.print(Panel(
        f'find {parent_dir} -type f -size 0 -delete',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0014", fallback="⚠️  危險操作")
    ))
    console.print()

    # ==================== 建議 ====================
    console.print("[bold #E8C4F0]⚠️  建議：[/bold #E8C4F0]")
    console.print("   1. 確認檔案來源可靠")
    console.print("   2. 使用校驗碼驗證檔案完整性（MD5, SHA256）")
    console.print("   3. 重新獲取檔案後再次執行程式")
    console.print()


def suggest_image_load_failed(file_path: str, error: Exception) -> None:
    """
    顯示圖片載入失敗的修復建議

    Args:
        file_path: 圖片檔案路徑
        error: 載入錯誤的異常物件
    """
    console.print(f"\n[dim #E8C4F0]✗ 無法載入圖片：{str(error)}[/red]\n")

    # 檔案資訊
    size_mb = 0
    actual_format = None
    mismatch = False

    if os.path.isfile(file_path):
        size_mb = os.path.getsize(file_path) / (1024 * 1024)

        console.print("[#E8C4F0]檔案資訊：[/#E8C4F0]")
        console.print(f"  - 路徑：{file_path}")
        console.print(f"  - 大小：{size_mb:.1f} MB")

        # 使用 file 指令檢測實際格式
        try:
            result = subprocess.run(
                ['file', file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            actual_format = result.stdout.split(':', 1)[1].strip() if ':' in result.stdout else "未知"

            console.print(f"  - 實際格式：{actual_format}")

            # 檢查副檔名是否匹配
            extension = Path(file_path).suffix.lower()
            format_lower = actual_format.lower()

            if extension in ['.jpg', '.jpeg'] and 'png' in format_lower:
                console.print("\n[#E8C4F0]⚠️  問題：檔案副檔名與實際格式不符[/#E8C4F0]")
                console.print(f"   副檔名：{extension}")
                console.print(f"   實際格式：PNG")
                mismatch = True
            elif extension == '.png' and 'jpeg' in format_lower:
                console.print("\n[#E8C4F0]⚠️  問題：檔案副檔名與實際格式不符[/#E8C4F0]")
                console.print(f"   副檔名：{extension}")
                console.print(f"   實際格式：JPEG")
                mismatch = True

        except Exception:
            # file 指令執行失敗，忽略
            pass

        console.print()

    console.print("[#E8C4F0]💡 解決方案：[/#E8C4F0]\n")

    # 選項 1：修正副檔名（如果檢測到不符）
    if mismatch and actual_format:
        console.print("[bold]🔧 選項 1：修正副檔名（推薦，最快）[/bold]\n")

        # 建議正確的副檔名
        format_lower = actual_format.lower()
        if 'png' in format_lower:
            correct_ext = '.png'
        elif 'jpeg' in format_lower or 'jpg' in format_lower:
            correct_ext = '.jpg'
        elif 'gif' in format_lower:
            correct_ext = '.gif'
        elif 'webp' in format_lower:
            correct_ext = '.webp'
        else:
            correct_ext = '.png'  # 預設

        new_path = str(Path(file_path).with_suffix(correct_ext))

        console.print("   執行指令重新命名：")
        console.print(Panel(
            f'mv "{file_path}" "{new_path}"',
            border_style="#E8C4F0",
            title=safe_t("error_handler.error_fix_suggestions.msg_0015", fallback="修正副檔名")
        ))
        console.print("\n   [dim]然後使用新路徑重新執行[/dim]\n")

    # 選項 2：轉換格式
    console.print("[bold]⚡ 選項 2：轉換圖片格式[/bold]\n")

    parent_dir = os.path.dirname(file_path) or '.'
    stem = Path(file_path).stem
    converted_jpg = os.path.join(parent_dir, f"{stem}_converted.jpg")
    converted_png = os.path.join(parent_dir, f"{stem}_converted.png")

    console.print("   轉換為標準 JPEG 格式：")
    console.print(Panel(
        f'ffmpeg -i "{file_path}" "{converted_jpg}"',
        border_style="#E8C4F0"
    ))

    console.print("\n   或轉換為 PNG：")
    console.print(Panel(
        f'ffmpeg -i "{file_path}" "{converted_png}"',
        border_style="#E8C4F0"
    ))
    console.print()

    # 選項 3：檢查詳細資訊
    console.print("[bold]🔍 選項 3：檢查圖片詳細資訊[/bold]\n")
    console.print("   執行指令查看實際格式：")
    console.print(Panel(f'file "{file_path}"', border_style="#E8C4F0"))

    console.print("\n   使用 ImageMagick 識別：")
    console.print(Panel(f'identify "{file_path}"', border_style="#E8C4F0"))
    console.print()

    # 選項 4：修復圖片
    console.print("[bold]📝 選項 4：驗證圖片完整性[/bold]\n")
    console.print("   如果圖片損壞，嘗試修復：")
    repaired = os.path.join(parent_dir, f"{stem}_repaired{Path(file_path).suffix}")
    console.print(Panel(
        f'convert "{file_path}" "{repaired}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0016", fallback="使用 ImageMagick 修復")
    ))
    console.print()

    # 支援格式
    console.print("[bold #E8C4F0]✅ 支援的圖片格式：[/bold green]")
    console.print("   - JPEG/JPG (.jpg, .jpeg)")
    console.print("   - PNG (.png)")
    console.print("   - GIF (.gif)")
    console.print("   - BMP (.bmp)")
    console.print("   - TIFF (.tiff, .tif)")
    console.print("   - WEBP (.webp)")
    console.print("   - ICO (.ico)")
    console.print()

    # 常見問題
    console.print("[bold #E8C4F0]⚠️  常見問題：[/bold #E8C4F0]")
    console.print("   1. 檔案副檔名與實際格式不符")
    console.print("   2. 圖片檔案損壞或不完整")
    console.print("   3. 不支援的圖片格式或編碼")
    console.print("   4. 圖片尺寸過大（超過 PIL 限制）")
    console.print()

    # 尺寸過大的解決方案
    if size_mb > 50:
        console.print("[bold #E8C4F0]💡 圖片尺寸過大，建議壓縮：[/bold #E8C4F0]")
        resized = os.path.join(parent_dir, f"{stem}_resized{Path(file_path).suffix}")
        console.print(Panel(
            f'ffmpeg -i "{file_path}"\n'
            f'       -vf "scale=iw/2:ih/2"\n'
            f'       "{resized}"',
            border_style="#E8C4F0",
            title=safe_t("error_handler.error_fix_suggestions.msg_0017", fallback="壓縮圖片（縮小為原尺寸的 1/2）")
        ))
        console.print()


def suggest_cannot_get_duration(file_path: str, error: Exception = None) -> None:
    """
    顯示無法獲取檔案時長的診斷建議

    Args:
        file_path: 無法獲取時長的檔案路徑
        error: 可選的錯誤物件，用於顯示詳細錯誤資訊
    """
    if error:
        console.print(f"\n[dim #E8C4F0]✗ 無法獲取檔案時長：{file_path}[/red]")
        console.print(f"[dim]錯誤詳情：{error}[/dim]\n")
    else:
        console.print(f"\n[dim #E8C4F0]✗ 無法獲取檔案時長：{file_path}[/red]\n")
    console.print("[#E8C4F0]💡 診斷與解決方案：[/#E8C4F0]\n")

    # ==================== 步驟 1：手動檢查 ====================
    console.print("[bold]🔍 步驟 1：手動檢查檔案時長[/bold]\n")
    console.print("   執行指令：")
    console.print(Panel(
        f'ffprobe -v error\n'
        f'        -show_entries format=duration\n'
        f'        -of default=noprint_wrappers=1\n'
        f'        "{file_path}"',
        border_style="#E8C4F0",
        title="獲取時長",
        padding=(0, 1)
    ))
    console.print("\n   [dim]預期輸出：duration=123.456[/dim]\n")

    console.print("[bold #E8C4F0]⚠️  可能的原因：[/bold #E8C4F0]\n")

    # ==================== 原因 1：檔案損壞 ====================
    console.print("[bold]📝 原因 1：檔案損壞或格式錯誤[/bold]\n")
    console.print("   解決方案：參考「任務 4：檔案損壞修復」\n")
    console.print("   快速嘗試重新封裝：")

    file_path_obj = Path(file_path)
    repaired = f"{file_path_obj.parent}/{file_path_obj.stem}_repaired{file_path_obj.suffix}"

    console.print(Panel(
        f'ffmpeg -i "{file_path}"\n'
        f'       -c copy\n'
        f'       "{repaired}"',
        border_style="#E8C4F0",
        title="重新封裝",
        padding=(0, 1)
    ))
    console.print()

    # ==================== 原因 2：格式不支援 ====================
    console.print("[bold]📝 原因 2：檔案格式不支援或編碼異常[/bold]\n")
    console.print("   解決方案：轉換為通用格式\n")
    console.print("   執行指令：")

    converted = f"{file_path_obj.parent}/{file_path_obj.stem}_converted.mp4"

    console.print(Panel(
        f'ffmpeg -i "{file_path}"\n'
        f'       -c:v libx264 -c:a aac\n'
        f'       "{converted}"',
        border_style="#E8C4F0",
        title="轉換格式",
        padding=(0, 1)
    ))
    console.print()

    # ==================== 原因 3：權限問題 ====================
    console.print("[bold]📝 原因 3：ffprobe 權限問題[/bold]\n")
    console.print("   解決方案：檢查 ffprobe 是否可執行\n")
    console.print("   執行指令：")
    console.print(Panel(
        'which ffprobe\n'
        'ffprobe -version',
        border_style="#E8C4F0",
        title="檢查 ffprobe",
        padding=(0, 1)
    ))
    console.print()

    # ==================== 臨時解決方案 ====================
    console.print("[bold]🔧 臨時解決方案：手動指定時長[/bold]\n")
    console.print("   如果您知道檔案時長，可以修改程式碼手動指定：\n")
    console.print("   [dim]duration = 123.45  # 您的檔案時長（秒）[/dim]\n")

    # ==================== 更多資訊 ====================
    console.print("[bold #E8C4F0]💡 獲取更多檔案資訊：[/bold #E8C4F0]\n")
    console.print("   執行指令查看完整資訊：")
    console.print(Panel(
        f'ffprobe -v error -show_format -show_streams\n'
        f'        "{file_path}"',
        border_style="#E8C4F0",
        title="完整檔案資訊",
        padding=(0, 1)
    ))
    console.print()


def suggest_invalid_speed(speed: float) -> None:
    """
    顯示速度倍數無效的建議

    Args:
        speed: 用戶輸入的無效速度倍數
    """
    console.print(f"\n[bold red]✗ 速度倍數無效：{speed}[/bold red]\n")
    console.print("[bold red]❌ 問題：速度倍數必須大於 0[/bold red]\n")

    console.print("[bold #E8C4F0]💡 常用速度設定：[/bold #E8C4F0]\n")

    console.print("[bold]⏩ 快速播放[/bold]")
    console.print("   • 1.5x - 輕微加速（適合演講）")
    console.print("   • 2.0x - 2 倍速（常見加速）")
    console.print("   • 3.0x - 3 倍速（快速瀏覽）\n")

    console.print("[bold]⏪ 慢動作[/bold]")
    console.print("   • 0.5x - 半速（常見慢動作）")
    console.print("   • 0.25x - 1/4 速（細節觀察）\n")

    console.print("[bold]⏸️  正常速度[/bold]")
    console.print("   • 1.0x - 原始速度\n")

    console.print("[#E8C4F0]📝 參數說明：[/#E8C4F0]")
    console.print("   • 值 > 1：加速播放（如 2.0 = 2倍速）")
    console.print("   • 值 < 1：慢動作（如 0.5 = 半速）")
    console.print("   • 值 = 1：正常速度")
    console.print("   • 值必須 > 0\n")


def suggest_unsupported_subtitle_format(requested_format: str) -> None:
    """
    顯示不支援字幕格式的建議

    Args:
        requested_format: 使用者請求的字幕格式
    """
    # 格式名稱映射
    format_names = {
        'srt': 'SubRip',
        'vtt': 'WebVTT',
        'ass': 'Advanced SubStation Alpha',
        'ssa': 'SubStation Alpha',
        'sub': 'MicroDVD/SUB',
        'smi': 'SAMI',
        'stl': 'Spruce STL'
    }

    format_full_name = format_names.get(
        requested_format.lower(),
        requested_format.upper()
    )

    console.print(f"\n[dim #E8C4F0]✗ 不支援的字幕格式：{requested_format}[/red]\n")
    console.print(f"您請求的格式：{format_full_name}\n")

    console.print("[#E8C4F0]💡 支援的字幕格式：[/#E8C4F0]\n")

    # ==================== SRT ====================
    console.print("[bold #E8C4F0]✅ srt (SubRip)[/bold green]")
    console.print("   - 最通用的字幕格式")
    console.print("   - 幾乎所有播放器都支援")
    console.print("   - 格式簡單，易於編輯")
    console.print("   - [#E8C4F0]推薦用於大多數場景[/green]\n")

    # ==================== VTT ====================
    console.print("[bold #E8C4F0]✅ vtt (WebVTT)[/bold green]")
    console.print("   - HTML5 標準字幕格式")
    console.print("   - 適用於網頁播放器")
    console.print("   - 支援樣式和定位")
    console.print("   - [#E8C4F0]推薦用於網頁應用[/green]\n")

    console.print("[#E8C4F0]⚡ 解決方案：[/#E8C4F0]\n")

    # ==================== 選項 1：使用 SRT ====================
    console.print("[bold]🔧 選項 1：使用 SRT 格式（推薦）[/bold]\n")
    console.print("   重新執行程式，將格式參數改為 'srt'\n")
    console.print("   範例：")
    console.print(Panel(
        'generator.generate_subtitles(\n'
        '    video_path="video.mp4",\n'
        '    format="srt"  # ← 使用 SRT 格式\n'
        ')',
        border_style="#E8C4F0",
        title="使用 SRT",
        padding=(0, 1)
    ))
    console.print()

    # ==================== 選項 2：使用 VTT ====================
    console.print("[bold]🔧 選項 2：使用 VTT 格式[/bold]\n")
    console.print("   重新執行程式，將格式參數改為 'vtt'\n")
    console.print("   範例：")
    console.print(Panel(
        'generator.generate_subtitles(\n'
        '    video_path="video.mp4",\n'
        '    format="vtt"  # ← 使用 VTT 格式\n'
        ')',
        border_style="#E8C4F0",
        title="使用 VTT",
        padding=(0, 1)
    ))
    console.print()

    # ==================== 選項 3：轉換格式 ====================
    console.print("[bold]🔄 選項 3：轉換現有字幕檔[/bold]\n")
    console.print("   如果您已有其他格式的字幕檔，可以轉換\n")

    # 常見轉換
    conversions = [
        ("ASS → SRT", f"ffmpeg -i subtitle.{requested_format} subtitle.srt"),
        ("SRT → VTT", "ffmpeg -i subtitle.srt subtitle.vtt"),
        ("VTT → SRT", "ffmpeg -i subtitle.vtt subtitle.srt"),
    ]

    for name, cmd in conversions:
        console.print(f"   {name}：")
        console.print(Panel(
            cmd,
            border_style="#E8C4F0",
            padding=(0, 1)
        ))
        console.print()

    console.print("   任意格式轉換：")
    console.print(Panel(
        f"ffmpeg -i input_subtitle.{requested_format} output.srt",
        border_style="#E8C4F0",
        title="通用轉換",
        padding=(0, 1)
    ))
    console.print()

    # ==================== 格式比較表 ====================
    console.print("[bold #E8C4F0]📊 格式比較：[/bold #E8C4F0]\n")

    from rich.table import Table
    table = Table()
    table.add_column("格式", style="#E8C4F0")
    table.add_column("相容性", style="green")
    table.add_column("樣式支援")
    table.add_column("檔案大小")
    table.add_column("推薦場景")

    table.add_row("SRT", "⭐⭐⭐⭐⭐", "基本", "小", "通用，離線播放")
    table.add_row("VTT", "⭐⭐⭐⭐", "進階", "中", "網頁播放器")

    console.print(table)
    console.print()

    # ==================== 常見轉換 ====================
    console.print("[bold #E8C4F0]💡 常見其他格式轉換：[/bold #E8C4F0]\n")
    console.print("   - ASS/SSA → SRT：適用於進階字幕轉通用格式")
    console.print("   - SUB → SRT：DVD 字幕轉換")
    console.print("   - SMI → SRT：SAMI 格式轉換")
    console.print()

    # ==================== 線上工具 ====================
    console.print("[bold #E8C4F0]🔗 線上轉換工具（如果不想用指令）：[/bold #E8C4F0]")
    console.print("   - https://subtitletools.com/convert-to-srt-online")
    console.print("   - https://www.nikse.dk/SubtitleEdit/Online")
    console.print()


def suggest_ffprobe_parse_failed(file_path: str, error: Exception) -> None:
    """
    建議：解析 ffprobe 輸出失敗

    當無法解析 ffprobe 的 JSON 輸出時提供診斷和修復建議

    Args:
        file_path: 影片檔案路徑
        error: 原始異常
    """
    console.print(f"\n[bold red]✗ 解析 ffprobe 輸出失敗[/bold red]")
    console.print(f"\n[dim]檔案：{file_path}[/dim]\n")

    console.print("[bold red]❌ 問題：無法解析影片元數據（可能是 ffprobe 版本問題）[/bold red]\n")

    console.print("[bold #E8C4F0]💡 解決方案：[/bold #E8C4F0]\n")

    # ==================== 步驟 1：檢查版本 ====================
    console.print("[bold]⚡ 步驟 1：檢查 ffprobe 版本[/bold]")
    console.print("   執行以下指令：")
    console.print(Panel(
        "ffprobe -version",
        border_style="#E8C4F0",
        title="檢查版本",
        padding=(0, 1)
    ))
    console.print("   [dim]建議版本：4.0 或更高[/dim]\n")

    # ==================== 步驟 2：手動獲取資訊 ====================
    console.print("[bold]⚡ 步驟 2：手動獲取影片資訊（JSON 格式）[/bold]")
    console.print("   執行以下指令：")
    console.print(Panel(
        f'ffprobe -v quiet -print_format json\n'
        f'        -show_format -show_streams\n'
        f'        "{file_path}"',
        border_style="#E8C4F0",
        title="獲取影片資訊",
        padding=(0, 1)
    ))
    console.print()

    # ==================== 步驟 3：檢查檔案是否損壞 ====================
    console.print("[bold]⚡ 步驟 3：檢查檔案是否損壞[/bold]")
    console.print("   嘗試使用基本的 ffprobe 指令：")
    console.print(Panel(
        f'ffprobe "{file_path}"',
        border_style="#E8C4F0",
        title="基本檢查",
        padding=(0, 1)
    ))
    console.print("   [dim]如果此指令也失敗，檔案可能已損壞[/dim]\n")

    # ==================== 更新 ffmpeg/ffprobe ====================
    console.print("[bold #E8C4F0]🔧 更新 ffmpeg/ffprobe[/bold green]\n")

    system = platform.system()
    if system == "Darwin":
        console.print("   macOS:")
        console.print(Panel(
            "brew upgrade ffmpeg",
            border_style="#E8C4F0",
            title="Homebrew 更新",
            padding=(0, 1)
        ))
    elif system == "Linux":
        console.print("   Linux:")
        console.print(Panel(
            "sudo apt update && sudo apt upgrade ffmpeg",
            border_style="#E8C4F0",
            title="APT 更新",
            padding=(0, 1)
        ))
    elif system == "Windows":
        console.print("   Windows:")
        console.print("   1. 前往 https://ffmpeg.org/download.html")
        console.print("   2. 下載最新版本")
        console.print("   3. 解壓縮並替換舊版本")
    console.print()

    # ==================== 替代方案 ====================
    console.print("[bold #E8C4F0]🔄 替代方案：使用其他工具獲取影片資訊[/bold #E8C4F0]\n")

    console.print("   選項 1：使用 mediainfo")
    console.print(Panel(
        f'mediainfo "{file_path}"',
        border_style="#E8C4F0",
        title="MediaInfo 指令",
        padding=(0, 1)
    ))
    console.print("   [dim]安裝 mediainfo：brew install mediainfo (macOS) 或 sudo apt install mediainfo (Linux)[/dim]\n")

    console.print("   選項 2：使用 exiftool")
    console.print(Panel(
        f'exiftool "{file_path}"',
        border_style="#E8C4F0",
        title="ExifTool 指令",
        padding=(0, 1)
    ))
    console.print("   [dim]安裝 exiftool：brew install exiftool (macOS) 或 sudo apt install libimage-exiftool-perl (Linux)[/dim]\n")

    # ==================== 詳細錯誤資訊 ====================
    console.print("[bold red]🐛 詳細錯誤資訊：[/bold red]")
    console.print(f"   {type(error).__name__}: {str(error)}\n")


# ==================== 測試函數 ====================

def test_suggestions():
    """測試所有建議功能"""
    console.print("[bold #E8C4F0]===== 測試 ffmpeg 安裝建議 =====[/bold #E8C4F0]")
    suggest_ffmpeg_install()

    console.print("\n[bold #E8C4F0]===== 測試 API 金鑰設定建議 =====[/bold #E8C4F0]")
    suggest_api_key_setup()

    console.print("\n[bold #E8C4F0]===== 測試缺少模組建議 =====[/bold #E8C4F0]")
    suggest_missing_module("psutil")

    console.print("\n[bold #E8C4F0]===== 測試檔案損壞建議 =====[/bold #E8C4F0]")
    suggest_file_corrupted(
        "/path/to/video.mp4",
        "moov atom not found\nInvalid data found when processing input"
    )

    console.print("\n[bold #E8C4F0]===== 測試影片上傳失敗建議 =====[/bold #E8C4F0]")
    suggest_video_upload_failed(
        "/path/to/large_video.mp4",
        "Connection timeout after 60s",
        uploaded_bytes=120 * 1024 * 1024  # 120 MB
    )

    console.print("\n[bold #E8C4F0]===== 測試空檔案建議 =====[/bold #E8C4F0]")
    suggest_empty_file("/path/to/empty_video.mp4")

    console.print("\n[bold #E8C4F0]===== 測試 JSON 解析失敗建議 =====[/bold #E8C4F0]")
    bad_json = '''{
  "segments": [
    {
      start: 0.0,
      "end": 5.2,
      "text": "這是第一段字幕"
    }
  ]
}'''
    suggest_json_parse_failed(
        bad_json,
        "Expecting property name enclosed in double quotes: line 4 column 7",
        "語音辨識"
    )



def suggest_unsupported_filter(filter_name: str, supported_filters: dict) -> None:
    """
    建議：不支援的濾鏡

    當使用者指定了不支援的濾鏡時，顯示所有支援的濾鏡及其詳細說明

    Args:
        filter_name: 使用者請求的濾鏡名稱
        supported_filters: 支援的濾鏡字典 {name: ffmpeg_filter_string}
    """
    console.print(f"\n[dim #E8C4F0]✗ 不支援的濾鏡：{filter_name}[/red]\n")

    # 濾鏡的中文名稱和詳細說明
    filter_descriptions = {
        'grayscale': {
            'name': '黑白效果',
            'desc': '將影片轉為灰階，呈現經典黑白電影風格',
            'use_case': '藝術創作、懷舊風格、強調對比'
        },
        'sepia': {
            'name': '懷舊效果',
            'desc': '棕褐色調，復古照片風格',
            'use_case': '復古影片、懷舊氛圍、老照片效果'
        },
        'vintage': {
            'name': '復古效果',
            'desc': '經典復古色調，模擬老電影質感',
            'use_case': '老電影風格、藝術創作'
        },
        'sharpen': {
            'name': '銳化',
            'desc': '增強邊緣清晰度，使畫面更清晰',
            'use_case': '模糊影片修復、提升清晰度'
        },
        'blur': {
            'name': '模糊效果',
            'desc': '高斯模糊，柔化畫面',
            'use_case': '隱私保護、藝術效果、背景虛化'
        },
        'brighten': {
            'name': '增亮',
            'desc': '增加畫面亮度',
            'use_case': '暗部影片修復、提升可見度'
        },
        'contrast': {
            'name': '高對比',
            'desc': '增強對比度，使色彩更鮮明',
            'use_case': '灰暗影片增強、色彩強化'
        },
    }

    console.print("[#E8C4F0]💡 支援的濾鏡：[/#E8C4F0]\n")

    # 顯示所有支援的濾鏡
    for fname in supported_filters.keys():
        info = filter_descriptions.get(fname, {
            'name': fname,
            'desc': '影片濾鏡效果',
            'use_case': '影片處理'
        })

        console.print(f"[bold #E8C4F0]✅ {fname}[/bold green] - {info['name']}")
        console.print(f"   說明：{info['desc']}")
        console.print(f"   適用：{info['use_case']}\n")

    console.print("[#E8C4F0]⚡ 使用方式：[/#E8C4F0]\n")

    # 顯示使用範例
    console.print("[bold]Python API 使用範例：[/bold]\n")

    example_filter = list(supported_filters.keys())[0]  # 使用第一個濾鏡作為範例
    console.print(Panel(
        f'from gemini_video_effects import VideoEffects\n\n'
        f'effects = VideoEffects()\n'
        f'effects.apply_filter(\n'
        f'    video_path="input.mp4",\n'
        f'    filter_name="{example_filter}",  # ← 使用支援的濾鏡名稱\n'
        f'    quality="high"\n'
        f')',
        border_style="#E8C4F0",
        title="範例代碼",
        padding=(0, 1)
    ))
    console.print()

    # 命令列使用範例
    console.print("[bold]命令列使用範例：[/bold]\n")

    for i, fname in enumerate(list(supported_filters.keys())[:3], 1):
        info = filter_descriptions.get(fname, {'name': fname})
        console.print(f"   {i}. {info['name']}（{fname}）：")
        console.print(Panel(
            f'python gemini_video_effects.py input.mp4 --filter {fname}',
            border_style="#E8C4F0",
            padding=(0, 1)
        ))
        console.print()

    # 修正建議
    console.print("[bold #E8C4F0]🔧 修正建議：[/bold #E8C4F0]\n")

    # 尋找相似的濾鏡名稱
    similar_filters = []
    for fname in supported_filters.keys():
        similarity = SequenceMatcher(None, filter_name.lower(), fname.lower()).ratio()
        if similarity > 0.6:
            similar_filters.append((fname, similarity))

    # 按相似度排序
    similar_filters.sort(key=lambda x: x[1], reverse=True)

    if similar_filters:
        console.print("   您可能想使用：\n")
        for fname, similarity in similar_filters[:3]:
            info = filter_descriptions.get(fname, {'name': fname})
            similarity_pct = int(similarity * 100)
            console.print(f"   • [#E8C4F0]{fname}[/green] ({info['name']}) - 相似度 {similarity_pct}%")
        console.print()
    else:
        console.print("   請從上述支援的濾鏡中選擇一個\n")

    # 組合使用提示
    console.print("[bold #E8C4F0]💡 進階技巧：[/bold #E8C4F0]")
    console.print("   可以使用 ffmpeg 直接組合多個濾鏡效果：")
    console.print(Panel(
        'ffmpeg -i input.mp4 \\\n'
        '       -vf "hue=s=0,eq=contrast=1.2" \\\n'
        '       output.mp4\n'
        '# 黑白 + 高對比',
        border_style="#E8C4F0",
        title="組合濾鏡",
        padding=(0, 1)
    ))
    console.print()

    # 列出所有支援的濾鏡名稱
    console.print(f"[bold]📝 完整濾鏡列表：[/bold]")
    console.print(f"   {', '.join(supported_filters.keys())}\n")



def suggest_missing_stream(file_path: str, stream_type: str = "audio") -> None:
    """
    建議：影片缺少音訊或視訊串流

    當影片檔案不包含有效的音訊或視訊串流時，提供診斷和修復建議

    Args:
        file_path: 影片檔案路徑
        stream_type: 缺少的串流類型 ("audio" 或 "video")
    """
    stream_name = safe_t("error_handler.error_fix_suggestions.msg_0018", fallback="音訊") if stream_type == "audio" else "視訊"
    
    console.print(f"\n[dim #E8C4F0]✗ 影片檔案不包含有效{stream_name}串流：{file_path}[/red]\n")

    console.print("[#E8C4F0]💡 診斷與解決方案：[/#E8C4F0]\n")

    # ==================== 步驟 1：檢查串流資訊 ====================
    console.print(f"[bold]🔍 步驟 1：檢查影片串流資訊[/bold]\n")
    console.print("   執行指令查看影片詳細資訊：")
    console.print(Panel(
        f'ffprobe -v error\n'
        f'        -show_entries stream=codec_type,codec_name\n'
        f'        -of default=noprint_wrappers=1\n'
        f'        "{file_path}"',
        border_style="#E8C4F0",
        title="檢查串流",
        padding=(0, 1)
    ))
    console.print("\n   [dim]預期會看到 codec_type=audio 或 codec_type=video[/dim]\n")

    if stream_type == "audio":
        # ==================== 音訊串流缺失的解決方案 ====================
        
        # 方案 1：添加靜音音軌
        console.print("[bold #E8C4F0]✅ 方案 1：添加靜音音軌（最快，適合無聲影片）[/bold green]\n")
        console.print("   如果影片本來就無聲，可以添加一個靜音音軌：\n")
        
        file_path_obj = Path(file_path)
        with_audio = f"{file_path_obj.parent}/{file_path_obj.stem}_with_audio{file_path_obj.suffix}"
        
        console.print(Panel(
            f'ffmpeg -i "{file_path}"\n'
            f'       -f lavfi -i anullsrc=r=44100:cl=stereo\n'
            f'       -c:v copy -c:a aac -shortest\n'
            f'       "{with_audio}"',
            border_style="#E8C4F0",
            title="添加靜音音軌",
            padding=(0, 1)
        ))
        console.print()

        # 方案 2：從其他檔案添加音訊
        console.print("[bold #E8C4F0]✅ 方案 2：從其他音訊檔案合併（如果有音訊源）[/bold green]\n")
        console.print("   如果有對應的音訊檔案（如 .mp3, .wav），可以合併：\n")
        console.print(Panel(
            f'ffmpeg -i "{file_path}"\n'
            f'       -i "audio.mp3"\n'
            f'       -c:v copy -c:a aac -shortest\n'
            f'       "{with_audio}"',
            border_style="#E8C4F0",
            title="合併音訊",
            padding=(0, 1)
        ))
        console.print()

        # 方案 3：提取音訊（如果確定有音訊但檢測不到）
        console.print("[bold #E8C4F0]✅ 方案 3：重新封裝影片（可能修復損壞的音訊串流）[/bold green]\n")
        console.print("   有時音訊串流資訊損壞，重新封裝可以修復：\n")
        
        remuxed = f"{file_path_obj.parent}/{file_path_obj.stem}_remuxed{file_path_obj.suffix}"
        console.print(Panel(
            f'ffmpeg -i "{file_path}"\n'
            f'       -c copy\n'
            f'       "{remuxed}"',
            border_style="#E8C4F0",
            title="重新封裝",
            padding=(0, 1)
        ))
        console.print()

        # 方案 4：轉換格式
        console.print("[bold #E8C4F0]✅ 方案 4：轉換為標準格式[/bold green]\n")
        console.print("   某些格式可能不包含音訊，轉換為標準 MP4：\n")
        
        converted = f"{file_path_obj.parent}/{file_path_obj.stem}_converted.mp4"
        console.print(Panel(
            f'ffmpeg -i "{file_path}"\n'
            f'       -c:v libx264 -c:a aac\n'
            f'       "{converted}"',
            border_style="#E8C4F0",
            title="轉換格式",
            padding=(0, 1)
        ))
        console.print()

    else:
        # ==================== 視訊串流缺失的解決方案 ====================
        
        console.print("[bold #E8C4F0]✅ 方案 1：檢查檔案類型[/bold green]\n")
        console.print("   這可能是純音訊檔案（如 .mp3, .wav）：\n")
        console.print("   執行指令檢查：")
        console.print(Panel(f'file "{file_path}"', border_style="#E8C4F0"))
        console.print()

        console.print("[bold #E8C4F0]✅ 方案 2：從音訊生成影片（添加靜態影像）[/bold green]\n")
        console.print("   可以將音訊檔案轉換為影片，添加靜態背景：\n")
        
        file_path_obj = Path(file_path)
        video_output = f"{file_path_obj.parent}/{file_path_obj.stem}_video.mp4"
        
        console.print(Panel(
            f'ffmpeg -loop 1 -i background.jpg\n'
            f'       -i "{file_path}"\n'
            f'       -c:v libx264 -c:a aac\n'
            f'       -shortest\n'
            f'       "{video_output}"',
            border_style="#E8C4F0",
            title="音訊轉影片",
            padding=(0, 1)
        ))
        console.print()

    # ==================== 常見原因 ====================
    console.print(f"[bold #E8C4F0]📝 {stream_name}串流缺失的常見原因：[/bold #E8C4F0]")
    
    if stream_type == "audio":
        console.print("   1. 影片本來就是無聲影片（如螢幕錄製、動畫）")
        console.print("   2. 音訊在編輯過程中被移除")
        console.print("   3. 檔案轉換時音訊編碼失敗")
        console.print("   4. 音訊串流資訊損壞")
        console.print("   5. 使用了不支援音訊的格式（如某些 GIF 轉 MP4）")
    else:
        console.print("   1. 檔案實際上是音訊檔案（.mp3, .wav, .aac）")
        console.print("   2. 檔案擴展名錯誤（音訊檔被命名為 .mp4）")
        console.print("   3. 視訊串流在處理過程中損壞")
    
    console.print()

    # ==================== 驗證方案 ====================
    console.print("[bold #E8C4F0]✅ 驗證修復結果：[/bold #E8C4F0]")
    console.print("   修復後執行以下指令驗證：\n")
    console.print(Panel(
        f'ffprobe -v error\n'
        f'        -show_entries stream=codec_type\n'
        f'        -of default=noprint_wrappers=1\n'
        f'        "[修復後的檔案路徑]"',
        border_style="#E8C4F0",
        title="驗證串流",
        padding=(0, 1)
    ))
    console.print(f"\n   [dim]應該會看到 codec_type={stream_type}[/dim]\n")


def suggest_invalid_time_range(
    start_time: float,
    end_time: float,
    duration: float,
    video_path: str
) -> None:
    """
    建議：無效的時間範圍

    當影片剪輯時間範圍無效時提供詳細的診斷和修正方案

    Args:
        start_time: 開始時間（秒）
        end_time: 結束時間（秒）
        duration: 影片總長度（秒）
        video_path: 影片檔案路徑
    """
    console.print(f"\n[bold red]✗ 無效的時間範圍[/bold red]\n")
    console.print(f"[dim]參數：開始 {start_time}s，結束 {end_time}s[/dim]")
    console.print(f"[dim]影片長度：{duration}s[/dim]\n")

    # 診斷問題
    if end_time > duration:
        console.print(
            f"[bold red]❌ 問題：結束時間 ({end_time}s) 超過影片長度 ({duration}s)[/bold red]\n"
        )
    elif start_time >= end_time:
        console.print(
            f"[bold red]❌ 問題：開始時間 ({start_time}s) 大於等於結束時間 ({end_time}s)[/bold red]\n"
        )
    elif start_time < 0:
        console.print(
            f"[bold red]❌ 問題：開始時間 ({start_time}s) 不能為負數[/bold red]\n"
        )

    console.print("[bold #E8C4F0]💡 修正建議：[/bold #E8C4F0]\n")

    # 建議 1：調整範圍
    console.print("[bold #E8C4F0]✅ 方法 1：調整時間範圍到有效範圍內[/bold green]\n")
    console.print("   推薦參數：")
    console.print(f"   - 開始：0s (影片開頭)")
    console.print(f"   - 結束：{duration}s (影片結尾)\n")

    # 保持片段長度
    segment_length = end_time - start_time
    if segment_length > 0 and segment_length < duration:
        new_start = max(0, duration - segment_length)
        console.print(f"   或保持相同片段長度 ({segment_length}s)：")
        console.print(f"   - 開始：{new_start}s")
        console.print(f"   - 結束：{duration}s\n")

    # 建議 2：查看完整資訊
    console.print("[bold #E8C4F0]✅ 方法 2：查看影片完整資訊[/bold green]")
    console.print("   執行以下指令：")
    console.print(Panel(
        f'ffprobe -v quiet -show_format -show_streams\n'
        f'        "{video_path}"',
        border_style="#E8C4F0",
        padding=(0, 2)
    ))

    # 建議 3：使用百分比（新增）
    console.print("\n[bold #E8C4F0]✅ 方法 3：使用百分比計算時間點[/bold green]")
    console.print("   示例：")
    console.print(f"   - 前 50%：0s ~ {duration * 0.5:.1f}s")
    console.print(f"   - 後 50%：{duration * 0.5:.1f}s ~ {duration}s")
    console.print(f"   - 中間 50%：{duration * 0.25:.1f}s ~ {duration * 0.75:.1f}s\n")

    # 建議 4：常見時間片段（新增）
    console.print("[bold #E8C4F0]✅ 方法 4：使用常見時間片段[/bold green]")
    console.print("   示例：")

    # 前 30 秒
    if duration >= 30:
        console.print(f"   - 前 30 秒：0s ~ 30s")

    # 前 1 分鐘
    if duration >= 60:
        console.print(f"   - 前 1 分鐘：0s ~ 60s")

    # 最後 30 秒
    if duration >= 30:
        console.print(f"   - 最後 30 秒：{max(0, duration - 30):.1f}s ~ {duration}s")

    # 中間 1 分鐘
    if duration >= 60:
        mid_point = duration / 2
        console.print(f"   - 中間 1 分鐘：{max(0, mid_point - 30):.1f}s ~ {min(duration, mid_point + 30):.1f}s")

    console.print()

    # 建議 5：自動修正建議（新增）
    console.print("[bold #E8C4F0]✅ 方法 5：自動修正到最接近的有效範圍[/bold green]")

    # 計算自動修正後的值
    auto_start = max(0, min(start_time, duration))
    auto_end = max(auto_start + 1, min(end_time, duration))  # 至少 1 秒

    # 如果原本的範圍太大，縮小到影片長度
    if auto_end - auto_start > duration:
        auto_start = 0
        auto_end = duration

    console.print("   自動修正後的參數：")
    console.print(f"   - 開始：{auto_start}s")
    console.print(f"   - 結束：{auto_end}s")
    console.print(f"   - 片段長度：{auto_end - auto_start}s\n")

    # 有效範圍說明
    console.print(f"[#E8C4F0]📝 有效時間範圍：[/#E8C4F0]")
    console.print(f"   • 開始時間：0 ~ {duration}s")
    console.print(f"   • 結束時間：0 ~ {duration}s")
    console.print(f"   • 結束時間必須大於開始時間\n")


def suggest_watermark_not_found(watermark_path: str) -> None:
    """
    顯示浮水印檔案不存在的修復建議

    提供多種解決方案：
    1. 檢查檔案位置
    2. 搜尋浮水印檔案
    3. 使用 ImageMagick 製作文字浮水印
    4. 支援的浮水印格式說明

    Args:
        watermark_path: 找不到的浮水印檔案路徑
    """
    console.print(f"\n[bold red]✗ 浮水印檔案不存在[/bold red]")
    console.print(f"\n[dim]找不到：{watermark_path}[/dim]\n")

    console.print("[bold #E8C4F0]💡 解決方案：[/bold #E8C4F0]\n")

    # ==================== 檢查檔案位置 ====================
    console.print("[bold]📂 檢查檔案位置[/bold]")
    console.print("   請確認浮水印檔案是否存在於指定路徑\n")

    # ==================== 支援的格式 ====================
    console.print("[bold #E8C4F0]✅ 支援的浮水印格式：[/bold green]")
    console.print("   • PNG（推薦，支援透明背景）")
    console.print("   • JPG")
    console.print("   • GIF")
    console.print("   • BMP\n")

    # ==================== 搜尋檔案 ====================
    directory = os.path.dirname(watermark_path) or '.'
    console.print("[bold #E8C4F0]⚡ 搜尋浮水印檔案[/bold green]")
    console.print("   執行以下指令：")
    console.print(Panel(
        f'find {directory} -name "*watermark*" -type f',
        border_style="#E8C4F0",
        padding=(0, 2)
    ))
    console.print()

    # ==================== 製作浮水印 ====================
    console.print("[bold #E8C4F0]🎨 製作簡單文字浮水印[/bold green]")
    console.print("   使用 ImageMagick：")
    console.print(Panel(
        'convert -size 300x100 xc:none\n'
        '        -font Arial -pointsize 30\n'
        '        -fill white -annotate +10+50 "Copyright"\n'
        '        watermark.png',
        border_style="#E8C4F0",
        padding=(0, 2)
    ))
    console.print()

    # ==================== 替代方案：ffmpeg 文字浮水印 ====================
    console.print("[bold #E8C4F0]💡 替代方案：直接用 ffmpeg 添加文字浮水印[/bold #E8C4F0]")
    console.print("   不需要圖片檔案，直接在影片上加文字：")
    console.print(Panel(
        'ffmpeg -i input.mp4\n'
        '       -vf "drawtext=text=\'Copyright\':fontsize=30:fontcolor=white:x=10:y=10"\n'
        '       output.mp4',
        border_style="#E8C4F0",
        title="使用 ffmpeg 繪製文字",
        padding=(0, 2)
    ))
    console.print()

    # ==================== 下載範例浮水印 ====================
    console.print("[bold #E8C4F0]📥 下載範例浮水印[/bold #E8C4F0]")
    console.print("   您可以從以下網站下載免費浮水印圖片：")
    console.print("   • Pixabay: https://pixabay.com/ (搜尋 'watermark')")
    console.print("   • Unsplash: https://unsplash.com/ (搜尋 'logo')")
    console.print("   • Flaticon: https://www.flaticon.com/ (搜尋 'copyright')")
    console.print()


def suggest_no_images_loaded(attempted_count: int, file_paths: list) -> None:
    """
    顯示沒有成功載入任何圖片的診斷和修復建議

    提供多種解決方案：
    1. 檢查所有圖片檔案是否存在
    2. 檢查圖片檔案是否損壞
    3. 檢查圖片格式是否支援
    4. 批次驗證圖片
    5. 批次轉換格式

    Args:
        attempted_count: 嘗試載入的圖片數量
        file_paths: 圖片檔案路徑列表
    """
    console.print(f"\n[bold red]✗ 沒有成功載入任何圖片[/bold red]\n")
    console.print(f"[dim]嘗試載入：{attempted_count} 個圖片檔案[/dim]")
    console.print(f"[dim]成功載入：0 個[/dim]\n")

    console.print("[bold #E8C4F0]💡 可能的原因：[/bold #E8C4F0]\n")

    # ==================== 原因 1：檔案不存在 ====================
    console.print("[bold]1️⃣ 所有圖片檔案都不存在[/bold]")
    console.print("   • 檢查檔案路徑是否正確")
    console.print("   • 檢查檔案是否已被移動或刪除\n")

    # ==================== 原因 2：檔案損壞 ====================
    console.print("[bold]2️⃣ 所有圖片檔案都已損壞[/bold]")
    console.print("   • 嘗試用其他工具開啟圖片")
    console.print("   • 檢查下載/傳輸是否完整\n")

    # ==================== 原因 3：格式不支援 ====================
    console.print("[bold]3️⃣ 圖片格式不支援[/bold]")
    console.print("   • 支援格式：JPG, PNG, GIF, BMP, WEBP")
    console.print("   • 使用 file 指令檢查實際格式\n")

    console.print("[bold #E8C4F0]⚡ 建議操作：[/bold #E8C4F0]\n")

    # ==================== 選項 1：檢查第一個檔案 ====================
    if file_paths:
        first_file = file_paths[0]
        console.print("[bold #E8C4F0]🔍 選項 1：檢查第一個檔案[/bold green]")
        console.print("   執行以下指令：")
        console.print(Panel(
            f'file "{first_file}"\n'
            f'ls -lh "{first_file}"',
            border_style="#E8C4F0",
            padding=(0, 2)
        ))
        console.print()

    # ==================== 選項 2：批次檢查所有檔案 ====================
    console.print("[bold #E8C4F0]📋 選項 2：批次檢查所有檔案是否存在[/bold green]")
    if file_paths and len(file_paths) <= 10:
        console.print("   檢查以下檔案：")
        for i, path in enumerate(file_paths, 1):
            exists = "✓" if os.path.exists(path) else "✗"
            console.print(f"   {exists} {i}. {os.path.basename(path)}")
    else:
        console.print("   執行以下指令：")
        if file_paths:
            directory = os.path.dirname(file_paths[0]) or '.'
            console.print(Panel(
                f'ls -lh {directory}/*.{{jpg,png,gif,bmp,webp}}',
                border_style="#E8C4F0"
            ))
    console.print()

    # ==================== 選項 3：使用 ImageMagick 驗證 ====================
    console.print("[bold #E8C4F0]🔍 選項 3：使用 ImageMagick 驗證圖片完整性[/bold green]")
    console.print("   執行以下指令：")
    if file_paths and len(file_paths) <= 3:
        for path in file_paths[:3]:
            console.print(Panel(
                f'identify -verbose "{path}"',
                border_style="#E8C4F0",
                title=f"驗證 {os.path.basename(path)}"
            ))
    else:
        console.print(Panel(
            'for img in *.jpg *.png; do\n'
            '  identify "$img" 2>&1 | grep -q "identify:" && echo "損壞: $img" || echo "正常: $img"\n'
            'done',
            border_style="#E8C4F0",
            title=safe_t("error_handler.error_fix_suggestions.msg_0019", fallback="批次驗證")
        ))
    console.print()

    # ==================== 選項 4：批次轉換格式 ====================
    console.print("[bold #E8C4F0]🔧 選項 4：批次轉換為標準格式（PNG）[/bold green]")
    console.print("   執行以下指令：")
    console.print(Panel(
        'for img in *.jpg *.jpeg; do\n'
        '  convert "$img" "${img%.*}.png"\n'
        'done',
        border_style="#E8C4F0",
        padding=(0, 2)
    ))
    console.print()

    # ==================== 選項 5：使用 ffmpeg 轉換 ====================
    console.print("[bold #E8C4F0]⚡ 選項 5：使用 ffmpeg 批次轉換[/bold green]")
    console.print("   執行以下指令：")
    console.print(Panel(
        'for img in *.jpg; do\n'
        '  ffmpeg -i "$img" -q:v 2 "${img%.jpg}_converted.jpg"\n'
        'done',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0020", fallback="高品質轉換")
    ))
    console.print()

    # ==================== 選項 6：檢查檔案權限 ====================
    console.print("[bold #E8C4F0]🔐 選項 6：檢查檔案權限[/bold green]")
    if file_paths:
        console.print("   執行以下指令：")
        console.print(Panel(
            f'chmod 644 {os.path.dirname(file_paths[0]) or "."}/*.{{jpg,png}}',
            border_style="#E8C4F0",
            title=safe_t("error_handler.error_fix_suggestions.msg_0021", fallback="添加讀取權限")
        ))
    console.print()

    # ==================== 選項 7：重新下載 ====================
    console.print("[bold #E8C4F0]📥 選項 7：如果圖片來自網路，重新下載[/bold #E8C4F0]")
    console.print("   • 確認下載連結是否有效")
    console.print("   • 使用可靠的下載工具（wget, curl）")
    console.print("   • 驗證下載完整性（檔案大小、MD5）")
    console.print()

    # ==================== 測試單一圖片 ====================
    console.print("[bold #E8C4F0]💡 測試建議：[/bold #E8C4F0]")
    console.print("   1. 先用單一已知正常的圖片測試")
    console.print("   2. 確認程式能正確載入該圖片")
    console.print("   3. 再逐步增加其他圖片")
    console.print()


def suggest_ffmpeg_not_installed() -> None:
    """
    建議：ffmpeg 未安裝（gemini_video_effects.py 專用別名）

    此函數是 suggest_ffmpeg_install() 的別名，
    專為 gemini_video_effects.py 錯誤處理設計
    """
    suggest_ffmpeg_install()


def suggest_no_video_stream(file_path: str) -> None:
    """
    任務 23: 找不到影片流

    當 ffprobe 無法在檔案中找到影片串流時顯示修復建議

    Args:
        file_path: 檔案路徑
    """
    console.print(f"\n[bold red]❌ 錯誤：找不到影片串流[/bold red]")
    console.print(f"[dim #E8C4F0]檔案：{file_path}[/red]\n")

    console.print("[#E8C4F0]🔍 診斷資訊：[/#E8C4F0]")

    # 使用 ffprobe 檢查串流
    try:
        import json
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_streams', file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            probe_data = json.loads(result.stdout)
            streams = probe_data.get('streams', [])

            console.print(f"   檔案包含 {len(streams)} 個串流：")
            for idx, stream in enumerate(streams):
                codec_type = stream.get('codec_type', 'unknown')
                codec_name = stream.get('codec_name', 'unknown')
                console.print(f"   - 串流 {idx}: {codec_type} ({codec_name})")

            has_video = any(s.get('codec_type') == 'video' for s in streams)
            has_audio = any(s.get('codec_type') == 'audio' for s in streams)

            if not has_video and has_audio:
                console.print("\n   ℹ️  這是一個純音訊檔案（如 MP3、WAV）")
                console.print("   此類型檔案不包含影片串流\n")
            elif not has_video:
                console.print("\n   ❌ 檔案中確實沒有影片串流\n")
    except Exception as e:
        console.print(f"   ⚠️  無法讀取串流資訊：{e}\n")

    console.print("[#E8C4F0]🔧 修復方案：[/#E8C4F0]\n")

    console.print("[bold #E8C4F0]⚡ 方案 1：從音訊檔建立影片（添加靜態圖片）[/bold green]")
    console.print("   執行以下指令：")
    console.print(Panel(
        f'ffmpeg -loop 1 -i cover.jpg -i "{file_path}" \\\n'
        '  -c:v libx264 -tune stillimage -c:a copy \\\n'
        '  -shortest output.mp4',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0022", fallback="添加封面圖片")
    ))
    console.print()

    console.print("[bold #E8C4F0]⚡ 方案 2：檢查檔案類型[/bold green]")
    console.print("   確認這是否為正確的影片檔案：")
    console.print(Panel(
        f'file "{file_path}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0023", fallback="檢查檔案類型")
    ))
    console.print()

    console.print("[bold #E8C4F0]⚡ 方案 3：如果檔案損壞，嘗試修復[/bold #E8C4F0]")
    suggest_file_corrupted(file_path)


def suggest_ffprobe_failed(file_path: str, error: Exception) -> None:
    """
    任務 24: ffprobe 執行失敗

    當 ffprobe 命令無法執行或返回錯誤時顯示修復建議

    Args:
        file_path: 檔案路徑
        error: 錯誤異常
    """
    console.print(f"\n[bold red]❌ 錯誤：ffprobe 執行失敗[/bold red]")
    console.print(f"[dim #E8C4F0]檔案：{file_path}[/red]")
    console.print(f"[dim #E8C4F0]錯誤：{error}[/red]\n")

    console.print("[#E8C4F0]🔍 診斷資訊：[/#E8C4F0]")

    # 檢查 ffprobe 是否存在
    if not _check_command('ffprobe'):
        console.print("   ❌ ffprobe 未安裝或不在 PATH 中\n")
        suggest_ffmpeg_install()
        return

    console.print("   ✓ ffprobe 已安裝")

    # 檢查檔案是否存在
    if not os.path.exists(file_path):
        console.print(f"   ❌ 檔案不存在：{file_path}\n")
        suggest_video_file_not_found(file_path)
        return

    console.print("   ✓ 檔案存在")

    # 檢查檔案權限
    if not os.access(file_path, os.R_OK):
        console.print("   ❌ 沒有讀取權限\n")
        console.print("[#E8C4F0]🔧 修復方案：[/#E8C4F0]\n")
        console.print(Panel(
            f'chmod +r "{file_path}"',
            border_style="#E8C4F0",
            title=safe_t("error_handler.error_fix_suggestions.msg_0024", fallback="添加讀取權限")
        ))
        return

    console.print("   ✓ 檔案可讀取")

    # 檢查檔案大小
    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            console.print("   ❌ 檔案為空\n")
            suggest_empty_file(file_path)
            return
        console.print(f"   ✓ 檔案大小：{file_size / (1024*1024):.2f} MB")
    except Exception:
        pass

    console.print()
    console.print("[#E8C4F0]🔧 修復方案：[/#E8C4F0]\n")

    console.print("[bold #E8C4F0]⚡ 方案 1：使用更詳細的錯誤輸出[/bold green]")
    console.print("   執行以下指令查看詳細錯誤：")
    console.print(Panel(
        f'ffprobe -v error "{file_path}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0025", fallback="詳細錯誤診斷")
    ))
    console.print()

    console.print("[bold #E8C4F0]⚡ 方案 2：嘗試重新封裝檔案[/bold green]")
    console.print("   執行以下指令：")
    console.print(Panel(
        f'ffmpeg -i "{file_path}" -c copy "{file_path}.fixed.mp4"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0026", fallback="重新封裝")
    ))
    console.print()

    console.print("[bold #E8C4F0]⚡ 方案 3：檢查檔案是否損壞[/bold #E8C4F0]")
    suggest_file_corrupted(file_path, str(error))


def suggest_video_processing_failed(file_path: str, error: Exception) -> None:
    """
    任務 35: 影片處理失敗

    當影片處理（如上傳、轉碼、分析）失敗時顯示修復建議

    Args:
        file_path: 檔案路徑
        error: 錯誤異常
    """
    console.print(f"\n[bold red]❌ 錯誤：影片處理失敗[/bold red]")
    console.print(f"[dim #E8C4F0]檔案：{file_path}[/red]")
    console.print(f"[dim #E8C4F0]錯誤：{error}[/red]\n")

    error_msg = str(error).lower()

    console.print("[#E8C4F0]🔍 診斷資訊：[/#E8C4F0]")

    # 根據錯誤訊息分類
    if 'state' in error_msg or 'processing' in error_msg or 'active' in error_msg:
        console.print("   ℹ️  影片可能仍在處理中，尚未完成")
        console.print("   處理時間通常取決於檔案大小和複雜度\n")

        console.print("[#E8C4F0]💡 建議等待時間：[/#E8C4F0]")
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            estimated_time = max(1, int(file_size_mb / 10))
            console.print(f"   檔案大小：{file_size_mb:.2f} MB")
            console.print(f"   預估處理時間：約 {estimated_time} 分鐘\n")
        except Exception:
            console.print("   建議等待 2-5 分鐘後重試\n")

    elif 'timeout' in error_msg:
        console.print("   ❌ 處理超時\n")
        console.print("[#E8C4F0]💡 可能原因：[/#E8C4F0]")
        console.print("   1. 檔案過大")
        console.print("   2. 網路連線不穩定")
        console.print("   3. API 伺服器負載過高\n")

    elif 'format' in error_msg or 'codec' in error_msg:
        console.print("   ❌ 格式或編碼問題\n")
        suggest_video_transcode_failed(file_path, None, str(error))
        return

    elif 'upload' in error_msg or 'network' in error_msg:
        console.print("   ❌ 上傳或網路問題\n")
        suggest_video_upload_failed(file_path, error)
        return

    else:
        console.print(f"   未知錯誤類型：{error}\n")

    console.print("[#E8C4F0]🔧 修復方案：[/#E8C4F0]\n")

    console.print("[bold #E8C4F0]⚡ 方案 1：檢查影片檔案[/bold green]")
    console.print("   確認檔案完整性：")
    console.print(Panel(
        f'ffprobe -v error -show_format -show_streams "{file_path}"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0027", fallback="檢查影片資訊")
    ))
    console.print()

    console.print("[bold #E8C4F0]⚡ 方案 2：壓縮影片以減小檔案大小[/bold green]")
    console.print("   執行以下指令：")
    console.print(Panel(
        f'ffmpeg -i "{file_path}" \\\n'
        '  -c:v libx264 -crf 28 -preset fast \\\n'
        '  -c:a aac -b:a 128k \\\n'
        f'  "{file_path}.compressed.mp4"',
        border_style="#E8C4F0",
        title=safe_t("error_handler.error_fix_suggestions.msg_0028", fallback="壓縮影片")
    ))
    console.print()

    console.print("[bold #E8C4F0]⚡ 方案 3：稍後重試[/bold #E8C4F0]")
    console.print("   • 等待幾分鐘後重新執行")
    console.print("   • 檢查網路連線狀態")
    console.print("   • 確認 API 服務正常運作")
    console.print()

    console.print("[bold #E8C4F0]⚡ 方案 4：檢查 API 配額[/bold #E8C4F0]")
    console.print("   前往 Google AI Studio 檢查 API 使用狀況：")
    console.print("   https://aistudio.google.com/app/apikey")
    console.print()


class ErrorLogger:
    """
    錯誤診斷記錄器 - 🔧 加入記憶體洩漏修復

    記錄所有錯誤和修復建議的歷史，用於分析和統計

    改良：
    - 限制記憶體中的錯誤記錄數量（最多 1000 條）
    - 自動輪轉：超過限制時保留最新 500 條，存檔舊的 500 條
    """

    def __init__(self, log_file: str = "error_diagnostics.log", max_errors: int = 1000):
        """
        初始化錯誤記錄器

        Args:
            log_file: 日誌檔案路徑
            max_errors: 記憶體中最多保留的錯誤數量（預設 1000）
        """
        self.log_file = log_file
        self.errors = []
        self.max_errors = max_errors
        self.archived_count = 0  # 已存檔的錯誤數量

    def log_error(self, error_type: str, file_path: str, details: Dict[str, Any]) -> None:
        """
        記錄一個錯誤

        Args:
            error_type: 錯誤類型（如 "FileNotFound", "FFmpegNotInstalled"）
            file_path: 相關檔案路徑
            details: 錯誤詳細資訊
        """
        import json
        from datetime import datetime

        entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'file_path': file_path,
            'details': details,
            'platform': platform.system(),
            'platform_version': platform.version()
        }

        self.errors.append(entry)

        # 🔧 記憶體洩漏修復：檢查是否需要輪轉
        if len(self.errors) > self.max_errors:
            self._rotate_errors()

        # 寫入日誌檔案
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            console.print(f"[dim red]警告：無法寫入日誌：{e}[/dim red]")

    def _rotate_errors(self) -> None:
        """
        輪轉錯誤記錄：保留最新 500 條，存檔舊的 500 條
        """
        import json
        from datetime import datetime

        keep_count = self.max_errors // 2  # 保留一半
        archive_count = len(self.errors) - keep_count

        if archive_count <= 0:
            return

        # 取出要存檔的錯誤
        to_archive = self.errors[:archive_count]

        # 存檔到輪轉檔案
        archive_file = f"{self.log_file}.archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            with open(archive_file, 'w', encoding='utf-8') as f:
                for error in to_archive:
                    f.write(json.dumps(error, ensure_ascii=False) + '\n')

            self.archived_count += archive_count
            console.print(f"[dim yellow]已輪轉 {archive_count} 條錯誤記錄到 {archive_file}[/dim yellow]")

            # 僅保留最新的錯誤
            self.errors = self.errors[archive_count:]

        except Exception as e:
            console.print(f"[dim red]警告：無法輪轉日誌：{e}[/dim red]")

    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取錯誤統計資訊

        Returns:
            包含統計資訊的字典
        """
        from collections import Counter

        if not self.errors:
            return {
                'total_errors': 0,
                'error_types': {},
                'most_common': []
            }

        error_types = Counter(e['error_type'] for e in self.errors)
        platforms = Counter(e.get('platform', 'unknown') for e in self.errors)

        return {
            'total_errors': len(self.errors),
            'error_types': dict(error_types),
            'most_common': error_types.most_common(5),
            'platforms': dict(platforms)
        }

    def print_statistics(self) -> None:
        """顯示錯誤統計資訊"""
        from rich.table import Table

        stats = self.get_statistics()

        if stats['total_errors'] == 0:
            console.print("\n[#E8C4F0]✓ 沒有記錄到錯誤[/green]\n")
            return

        console.print("\n[bold #E8C4F0]📊 錯誤統計[/bold #E8C4F0]\n")
        console.print(f"總錯誤數：{stats['total_errors']}\n")

        if stats['most_common']:
            table = Table(title="最常見錯誤（Top 5）", show_header=True, header_style="bold #E8C4F0")
            console_width = console.width or 120
            table.add_column("錯誤類型", style="#E8C4F0", width=max(25, int(console_width * 0.50)))
            table.add_column("次數", style="red", justify="right", width=max(8, int(console_width * 0.10)))
            table.add_column("百分比", style="bright_magenta", justify="right", width=max(8, int(console_width * 0.10)))

            total = stats['total_errors']
            for error_type, count in stats['most_common']:
                percentage = (count / total) * 100
                table.add_row(error_type, str(count), f"{percentage:.1f}%")

            console.print(table)
            console.print()

        if stats.get('platforms'):
            console.print("[bold]平台分布：[/bold]")
            for platform_name, count in stats['platforms'].items():
                console.print(f"   {platform_name}: {count}")
            console.print()

    def clear_log(self) -> None:
        """清除日誌記錄"""
        self.errors = []
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            console.print(f"[#E8C4F0]✓ 已清除日誌：{self.log_file}[/green]")
        except Exception as e:
            console.print(f"[dim #E8C4F0]✗ 無法清除日誌：{e}[/red]")

    def export_report(self, output_file: str = "error_report.json") -> None:
        """
        匯出錯誤報告

        Args:
            output_file: 輸出檔案路徑
        """
        import json

        report = {
            'generated_at': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'errors': self.errors
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            console.print(f"[#E8C4F0]✓ 報告已匯出：{output_file}[/green]")
        except Exception as e:
            console.print(f"[dim #E8C4F0]✗ 無法匯出報告：{e}[/red]")


# ========================================
# 🔧 ErrorLogger 公開 API（記憶體洩漏修復）
# ========================================

def get_error_statistics() -> Dict[str, Any]:
    """
    獲取錯誤統計資訊

    Returns:
        包含統計資訊的字典:
        - total_errors: 總錯誤數量
        - error_types: 錯誤類型分布
        - most_common: 最常見錯誤（Top 5）
        - platforms: 平台分布
        - archived_count: 已封存的錯誤數量
    """
    logger = _get_error_logger()
    stats = logger.get_statistics()
    stats['archived_count'] = logger.archived_count
    stats['active_errors'] = len(logger.errors)
    stats['max_errors'] = logger.max_errors
    return stats


def print_error_statistics() -> None:
    """顯示錯誤統計資訊（格式化輸出）"""
    _get_error_logger().print_statistics()


def export_error_diagnostics(output_file: str = None) -> None:
    """
    匯出錯誤診斷報告到檔案

    Args:
        output_file: 輸出檔案路徑（預設：Diagnostics/error_report_YYYYMMDD_HHMMSS.json）
    """
    _get_error_logger().export_report(output_file)


if __name__ == "__main__":
    test_suggestions()
