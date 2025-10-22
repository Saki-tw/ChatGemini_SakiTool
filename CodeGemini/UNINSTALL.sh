#!/bin/bash

################################################################################
# CodeGemini 卸載腳本
# 版本：1.0.0
# 用途：完整卸載 Gemini CLI 與相關配置
# 日期：2025-10-21
################################################################################

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 專案資訊
PROJECT_NAME="CodeGemini"
PROJECT_VERSION="1.0.0"

################################################################################
# 輔助函數
################################################################################

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_step() {
    echo -e "${CYAN}➤ $1${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

################################################################################
# 主要卸載流程
################################################################################

print_header "$PROJECT_NAME - 卸載腳本"
echo

print_warning "此腳本將完整移除 Gemini CLI 與相關配置"
print_info "以下項目將被移除："
echo "  • @google/gemini-cli npm 套件"
echo "  • ~/.gemini 配置目錄（包含 API Keys 與 checkpoints）"
echo "  • Shell 環境變數（需手動）"
echo

read -p "確定要繼續嗎？[y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "卸載已取消"
    exit 0
fi

echo

################################################################################
# 步驟 1: 檢查安裝狀態
################################################################################

print_step "步驟 1/5: 檢查安裝狀態"
echo

if check_command gemini; then
    CURRENT_VERSION=$(gemini --version 2>/dev/null || echo "unknown")
    print_info "檢測到 Gemini CLI 版本：$CURRENT_VERSION"
else
    print_warning "未檢測到 Gemini CLI"
fi

if ! check_command npm; then
    print_error "npm 未安裝，無法卸載 npm 套件"
    print_info "請手動刪除相關檔案"
    exit 1
fi

echo

################################################################################
# 步驟 2: 備份重要資料
################################################################################

print_step "步驟 2/5: 備份選項"
echo

BACKUP_DIR="$HOME/.gemini-backup-$(date +%Y%m%d-%H%M%S)"

if [ -d "$HOME/.gemini" ]; then
    print_info "檢測到配置目錄：~/.gemini"
    echo
    read -p "是否要備份配置與 checkpoints？[Y/n] " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_info "創建備份目錄：$BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
        cp -r "$HOME/.gemini" "$BACKUP_DIR/"
        print_success "備份完成：$BACKUP_DIR"
        echo
    else
        print_warning "跳過備份"
        echo
    fi
else
    print_info "未發現配置目錄"
    echo
fi

################################################################################
# 步驟 3: 卸載 Gemini CLI
################################################################################

print_step "步驟 3/5: 卸載 Gemini CLI"
echo

if check_command gemini; then
    print_info "正在卸載 @google/gemini-cli..."

    if npm uninstall -g @google/gemini-cli; then
        print_success "Gemini CLI 已卸載"
    else
        print_error "卸載失敗"
        print_info "您可能需要使用 sudo 權限："
        echo "  sudo npm uninstall -g @google/gemini-cli"
        exit 1
    fi
else
    print_info "Gemini CLI 未安裝，跳過卸載"
fi

echo

################################################################################
# 步驟 4: 移除配置檔案
################################################################################

print_step "步驟 4/5: 移除配置檔案"
echo

if [ -d "$HOME/.gemini" ]; then
    print_warning "即將刪除：~/.gemini"
    echo
    read -p "確認刪除配置目錄？[y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.gemini"
        print_success "配置目錄已刪除"
    else
        print_info "保留配置目錄"
    fi
else
    print_info "未發現配置目錄"
fi

echo

################################################################################
# 步驟 5: 清理環境變數
################################################################################

print_step "步驟 5/5: 清理環境變數提示"
echo

print_info "請手動從 Shell 配置檔中移除以下內容："
echo

SHELL_TYPE=$(basename "$SHELL")
case "$SHELL_TYPE" in
    bash)
        PROFILE_FILE="~/.bashrc"
        ;;
    zsh)
        PROFILE_FILE="~/.zshrc"
        ;;
    *)
        PROFILE_FILE="~/.profile"
        ;;
esac

echo "  檔案：$PROFILE_FILE"
echo "  內容："
echo "    export GEMINI_API_KEY=\"...\""
echo

print_info "編輯指令："
echo "  nano $PROFILE_FILE"
echo

print_info "編輯完成後，重新載入配置："
echo "  source $PROFILE_FILE"
echo

################################################################################
# 驗證卸載
################################################################################

print_step "驗證卸載"
echo

if ! check_command gemini; then
    print_success "Gemini CLI 已完全移除"
else
    print_warning "gemini 指令仍然存在"
    print_info "可能需要重新啟動 Shell 或手動檢查 PATH"
fi

echo

################################################################################
# 完成
################################################################################

print_header "卸載完成"
echo

print_success "Gemini CLI 已成功卸載"
echo

if [ -d "$BACKUP_DIR" ]; then
    print_info "備份位置：$BACKUP_DIR"
    print_warning "如需恢復，請手動複製檔案回 ~/.gemini"
    echo
fi

print_info "後續步驟："
echo "  1. 編輯 Shell 配置檔移除環境變數"
echo "  2. 重新啟動 Terminal 或執行 source 指令"
echo "  3. 如需重新安裝，執行 ./INSTALL.sh"
echo

print_info "感謝使用 CodeGemini！"
echo

print_header "卸載成功"
