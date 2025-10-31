#!/usr/bin/env python3
"""
ChatGemini 自動更新檢查模組
實作非同步版本檢查,不阻塞主程式啟動
"""

import os
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from rich.console import Console

console = Console()

# ==========================================
# 設定常數
# ==========================================

# 檔案路徑
LAST_CHECK_FILE = '.last_update_check'
UPDATE_AVAILABLE_FILE = '.update_available'
UPDATE_INFO_FILE = '.update_info'

# 檢查間隔 (秒)
CHECK_INTERVAL = 86400  # 24 小時

# GitHub 設定
GITHUB_REPO = "Saki-tw/ChatGemini_SakiTool"
GITHUB_BRANCH = "main"

# ==========================================
# 核心函數
# ==========================================

def should_check_update() -> bool:
    """
    判斷是否該檢查更新 (極快,只讀本地檔案)

    Returns:
        True: 需要檢查 (距上次檢查超過 CHECK_INTERVAL)
        False: 不需要檢查
    """
    try:
        if not os.path.exists(LAST_CHECK_FILE):
            return True  # 首次執行

        with open(LAST_CHECK_FILE, 'r', encoding='utf-8') as f:
            last_check = float(f.read().strip())
            elapsed = time.time() - last_check

            # 除錯資訊
            # print(f"[DEBUG] 距上次檢查: {elapsed / 3600:.1f} 小時")

            return elapsed > CHECK_INTERVAL
    except Exception as e:
        # 讀取失敗,預設需要檢查
        return True


def check_git_available() -> bool:
    """
    檢查 git 是否可用

    Returns:
        True: git 可用
        False: git 不可用
    """
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False


def get_local_commit() -> Optional[str]:
    """
    取得本地當前 commit SHA

    Returns:
        commit SHA (前 7 碼) 或 None (失敗時)
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short=7', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except:
        return None


def get_remote_commit() -> Optional[str]:
    """
    取得遠端最新 commit SHA (使用 git ls-remote)

    不需要 git fetch,更輕量

    Returns:
        commit SHA (前 7 碼) 或 None (失敗時)
    """
    try:
        # 使用 ls-remote 取得遠端 HEAD (不需要 fetch)
        result = subprocess.run(
            ['git', 'ls-remote', 'origin', GITHUB_BRANCH],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        if result.returncode == 0 and result.stdout:
            # 輸出格式: "SHA\trefs/heads/main"
            full_sha = result.stdout.split()[0]
            return full_sha[:7]  # 取前 7 碼
        return None
    except:
        return None


def get_update_info() -> Optional[Dict]:
    """
    檢查是否有可用更新

    Returns:
        {
            'has_update': bool,
            'local_version': str,
            'remote_version': str,
            'checked_at': str
        } 或 None (檢查失敗)
    """
    # 檢查 git 是否可用
    if not check_git_available():
        return None

    # 取得本地版本
    local_commit = get_local_commit()
    if not local_commit:
        return None

    # 取得遠端版本
    remote_commit = get_remote_commit()
    if not remote_commit:
        return None

    # 比對版本
    has_update = local_commit != remote_commit

    return {
        'has_update': has_update,
        'local_version': local_commit,
        'remote_version': remote_commit,
        'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def silent_check_update():
    """
    背景靜默檢查更新 (不阻塞主程式)

    此函數會在背景執行緒中執行:
    1. 檢查遠端是否有新版本
    2. 若有更新,寫入標記檔案
    3. 記錄檢查時間
    4. 靜默失敗 (不影響正常使用)
    """
    try:
        # 取得更新資訊
        update_info = get_update_info()

        if update_info:
            # 寫入檢查結果
            import json
            with open(UPDATE_INFO_FILE, 'w', encoding='utf-8') as f:
                json.dump(update_info, f, ensure_ascii=False, indent=2)

            # 若有更新,寫入標記
            if update_info['has_update']:
                with open(UPDATE_AVAILABLE_FILE, 'w', encoding='utf-8') as f:
                    f.write('true')
            else:
                # 無更新,移除標記 (如果存在)
                if os.path.exists(UPDATE_AVAILABLE_FILE):
                    os.remove(UPDATE_AVAILABLE_FILE)

        # 記錄檢查時間
        with open(LAST_CHECK_FILE, 'w', encoding='utf-8') as f:
            f.write(str(time.time()))

    except Exception as e:
        # 靜默失敗,不影響使用
        # 可選: 記錄到日誌
        pass


def start_background_update_check():
    """
    啟動背景更新檢查 (非阻塞)

    此函數會:
    1. 檢查是否該執行檢查 (根據時間間隔)
    2. 若需要,啟動背景執行緒檢查
    3. 立即返回,不阻塞主程式
    """
    if should_check_update():
        # 啟動 daemon 執行緒 (主程式結束時自動終止)
        thread = threading.Thread(
            target=silent_check_update,
            daemon=True,
            name="UpdateChecker"
        )
        thread.start()


def show_update_notification():
    """
    顯示更新通知 (在主選單上方)

    若有可用更新,顯示金黃色通知條
    """
    try:
        if os.path.exists(UPDATE_AVAILABLE_FILE):
            # 讀取更新資訊
            import json
            if os.path.exists(UPDATE_INFO_FILE):
                with open(UPDATE_INFO_FILE, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    local_ver = info.get('local_version', '?')
                    remote_ver = info.get('remote_version', '?')

                console.print(
                    f"\n[#FFD700]╔═══════════════════════════════════════════════════════════╗[/#FFD700]"
                )
                console.print(
                    f"[#FFD700]║  💡 發現新版本! {local_ver} → {remote_ver}                    ║[/#FFD700]"
                )
                console.print(
                    f"[#FFD700]║     輸入 [b]/update[/b] 查看詳情或更新                       ║[/#FFD700]"
                )
                console.print(
                    f"[#FFD700]╚═══════════════════════════════════════════════════════════╝[/#FFD700]\n"
                )
            else:
                # 簡化版通知
                console.print(
                    f"[#FFD700]💡 發現新版本! 輸入 /update 查看詳情[/#FFD700]\n"
                )
    except:
        # 顯示失敗,靜默忽略
        pass


def get_cached_update_info() -> Optional[Dict]:
    """
    取得快取的更新資訊 (不執行檢查)

    Returns:
        更新資訊 dict 或 None
    """
    try:
        import json
        if os.path.exists(UPDATE_INFO_FILE):
            with open(UPDATE_INFO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except:
        return None


def clear_update_notification():
    """
    清除更新通知標記

    用於使用者查看更新資訊後,不再重複提示
    """
    try:
        if os.path.exists(UPDATE_AVAILABLE_FILE):
            os.remove(UPDATE_AVAILABLE_FILE)
    except:
        pass


# ==========================================
# 測試函數
# ==========================================

def test_update_check():
    """測試更新檢查功能"""
    console.print("\n[b]測試 ChatGemini 更新檢查模組[/b]\n")

    # 1. 檢查 git
    console.print("1. 檢查 git 可用性...")
    if check_git_available():
        console.print("   ✓ git 可用\n")
    else:
        console.print("   ✗ git 不可用\n")
        return

    # 2. 取得本地版本
    console.print("2. 取得本地版本...")
    local = get_local_commit()
    console.print(f"   本地版本: {local}\n")

    # 3. 取得遠端版本
    console.print("3. 取得遠端版本 (需要網路連線)...")
    remote = get_remote_commit()
    console.print(f"   遠端版本: {remote}\n")

    # 4. 比對版本
    console.print("4. 比對版本...")
    if local and remote:
        if local == remote:
            console.print(f"   ✓ 已是最新版本 ({local})\n")
        else:
            console.print(f"   💡 有可用更新: {local} → {remote}\n")

    # 5. 測試更新資訊
    console.print("5. 取得完整更新資訊...")
    info = get_update_info()
    if info:
        import json
        console.print(f"   {json.dumps(info, ensure_ascii=False, indent=2)}\n")

    # 6. 測試通知顯示
    console.print("6. 測試更新通知顯示...")
    if info and info['has_update']:
        # 寫入臨時標記
        with open(UPDATE_AVAILABLE_FILE, 'w') as f:
            f.write('true')
        import json
        with open(UPDATE_INFO_FILE, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False)

        show_update_notification()


if __name__ == '__main__':
    # 直接執行時進行測試
    test_update_check()
