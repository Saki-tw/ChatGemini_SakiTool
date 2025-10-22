#!/bin/bash

################################################################################
# CodeGemini 更新腳本
# 版本：1.0.0
# 用途：更新 Gemini CLI 至最新版本
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
# 主要更新流程
################################################################################

print_header "$PROJECT_NAME - 更新腳本"
echo

################################################################################
# 步驟 1: 檢查當前版本
################################################################################

print_step "步驟 1/4: 檢查當前安裝狀態"
echo

if ! check_command gemini; then
    print_error "未檢測到 Gemini CLI"
    print_info "請先執行 INSTALL.sh 進行安裝"
    exit 1
fi

CURRENT_VERSION=$(gemini --version 2>/dev/null || echo "unknown")
print_info "當前版本：$CURRENT_VERSION"

if ! check_command npm; then
    print_error "npm 未安裝"
    exit 1
fi

echo

################################################################################
# 步驟 2: 檢查最新版本
################################################################################

print_step "步驟 2/4: 檢查最新版本"
echo

print_info "正在查詢 npm registry..."
LATEST_VERSION=$(npm view @google/gemini-cli version 2>/dev/null)

if [ -z "$LATEST_VERSION" ]; then
    print_error "無法取得最新版本資訊"
    print_info "請檢查網路連線"
    exit 1
fi

print_info "最新版本：$LATEST_VERSION"
echo

# 比較版本
if [ "$CURRENT_VERSION" == "$LATEST_VERSION" ]; then
    print_success "您已經使用最新版本！"
    echo
    read -p "是否要重新安裝？[y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "更新已取消"
        exit 0
    fi
fi

################################################################################
# 步驟 3: 備份配置
################################################################################

print_step "步驟 3/4: 備份現有配置"
echo

BACKUP_DIR="$HOME/.gemini/backup-$(date +%Y%m%d-%H%M%S)"

if [ -d "$HOME/.gemini" ]; then
    print_info "創建備份目錄：$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"

    # 備份配置檔案
    if [ -f "$HOME/.gemini/.env" ]; then
        cp "$HOME/.gemini/.env" "$BACKUP_DIR/"
        print_success "已備份 .env"
    fi

    # 備份 checkpoints
    if [ -d "$HOME/.gemini/checkpoints" ]; then
        cp -r "$HOME/.gemini/checkpoints" "$BACKUP_DIR/"
        print_success "已備份 checkpoints"
    fi

    echo
    print_info "備份位置：$BACKUP_DIR"
else
    print_info "未發現需要備份的配置"
fi

echo

################################################################################
# 步驟 4: 更新 Gemini CLI
################################################################################

print_step "步驟 4/4: 更新 Gemini CLI"
echo

print_info "正在更新 @google/gemini-cli..."
echo

if npm update -g @google/gemini-cli; then
    print_success "Gemini CLI 更新成功"
else
    print_error "更新失敗"
    print_info "嘗試使用重新安裝方式..."

    if npm install -g @google/gemini-cli; then
        print_success "Gemini CLI 重新安裝成功"
    else
        print_error "重新安裝失敗"
        print_info "您可能需要使用 sudo 權限："
        echo "  sudo npm install -g @google/gemini-cli"
        exit 1
    fi
fi

echo

################################################################################
# 驗證更新
################################################################################

print_step "驗證更新"
echo

if check_command gemini; then
    NEW_VERSION=$(gemini --version 2>/dev/null || echo "unknown")
    print_success "更新後版本：$NEW_VERSION"
else
    print_error "更新後驗證失敗"
    exit 1
fi

echo

################################################################################
# 完成
################################################################################

print_header "更新完成"
echo

print_success "Gemini CLI 已成功更新"
echo

print_info "版本變更："
echo "  從: $CURRENT_VERSION"
echo "  到: $NEW_VERSION"
echo

if [ -d "$BACKUP_DIR" ]; then
    print_info "備份位置：$BACKUP_DIR"
    echo
fi

print_info "您可以開始使用更新後的 Gemini CLI："
echo "  gemini --version  # 查看版本"
echo "  gemini            # 啟動 CLI"
echo

print_header "更新成功"
