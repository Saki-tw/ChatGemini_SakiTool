#!/bin/bash

################################################################################
# CodeGemini 環境檢查腳本
# 版本：1.0.0
# 用途：檢查系統環境、Gemini CLI 安裝狀態與配置
# 日期：2025-10-21
################################################################################

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# 專案資訊
PROJECT_NAME="CodeGemini"
PROJECT_VERSION="1.0.0"

# 計數器
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

################################################################################
# 輔助函數
################################################################################

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_section() {
    echo
    echo -e "${MAGENTA}▸ $1${NC}"
    echo -e "${MAGENTA}────────────────────────────────────────────────────────────${NC}"
}

print_success() {
    echo -e "${GREEN}  ✓ $1${NC}"
    ((PASSED_CHECKS++))
}

print_error() {
    echo -e "${RED}  ✗ $1${NC}"
    ((FAILED_CHECKS++))
}

print_warning() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
    ((WARNING_CHECKS++))
}

print_info() {
    echo -e "${BLUE}  ℹ $1${NC}"
}

check_command() {
    ((TOTAL_CHECKS++))
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

version_compare() {
    # 比較版本號（簡化版）
    local ver1=$1
    local ver2=$2
    if [ "$(printf '%s\n' "$ver2" "$ver1" | sort -V | head -n1)" = "$ver2" ]; then
        return 0
    else
        return 1
    fi
}

################################################################################
# 檢查函數
################################################################################

check_os() {
    print_section "作業系統資訊"

    OS_TYPE=$(uname -s)
    OS_VERSION=$(uname -r)
    ARCH=$(uname -m)

    print_info "系統類型：$OS_TYPE"
    print_info "系統版本：$OS_VERSION"
    print_info "架構：$ARCH"

    ((TOTAL_CHECKS++))
    if [[ "$OS_TYPE" == "Darwin" || "$OS_TYPE" == "Linux" ]]; then
        print_success "作業系統支援"
    else
        print_warning "作業系統可能不完全支援"
    fi
}

check_nodejs() {
    print_section "Node.js 環境"

    ((TOTAL_CHECKS++))
    if check_command node; then
        NODE_VERSION=$(node -v | cut -d'v' -f2)
        NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)

        print_info "Node.js 版本：v$NODE_VERSION"

        if [ "$NODE_MAJOR" -ge 18 ]; then
            print_success "Node.js 版本符合要求（需要 v18+）"
        else
            print_error "Node.js 版本過舊（當前：v$NODE_VERSION，需要：v18+）"
        fi

        NODE_PATH=$(which node)
        print_info "Node.js 路徑：$NODE_PATH"
    else
        print_error "Node.js 未安裝"
    fi

    ((TOTAL_CHECKS++))
    if check_command npm; then
        NPM_VERSION=$(npm -v)
        print_info "npm 版本：v$NPM_VERSION"
        print_success "npm 已安裝"

        NPM_PATH=$(which npm)
        print_info "npm 路徑：$NPM_PATH"

        # 檢查全域安裝目錄
        NPM_PREFIX=$(npm config get prefix)
        print_info "npm 全域目錄：$NPM_PREFIX"
    else
        print_error "npm 未安裝"
    fi
}

check_gemini_cli() {
    print_section "Gemini CLI 安裝狀態"

    ((TOTAL_CHECKS++))
    if check_command gemini; then
        print_success "Gemini CLI 已安裝"

        GEMINI_VERSION=$(gemini --version 2>/dev/null || echo "unknown")
        print_info "版本：$GEMINI_VERSION"

        GEMINI_PATH=$(which gemini)
        print_info "執行檔路徑：$GEMINI_PATH"

        # 檢查 npm 套件資訊
        if check_command npm; then
            NPM_INFO=$(npm list -g @google/gemini-cli 2>/dev/null | head -n 2 | tail -n 1 || echo "")
            if [ -n "$NPM_INFO" ]; then
                print_info "npm 套件：$NPM_INFO"
            fi

            # 檢查最新版本
            LATEST_VERSION=$(npm view @google/gemini-cli version 2>/dev/null || echo "unknown")
            if [ "$LATEST_VERSION" != "unknown" ]; then
                print_info "最新版本：$LATEST_VERSION"

                if [ "$GEMINI_VERSION" == "$LATEST_VERSION" ]; then
                    print_success "使用最新版本"
                else
                    print_warning "有新版本可用（執行 ./UPDATE.sh 更新）"
                fi
            fi
        fi
    else
        print_error "Gemini CLI 未安裝"
        print_info "執行 ./INSTALL.sh 進行安裝"
    fi
}

check_api_configuration() {
    print_section "API 配置檢查"

    # 檢查環境變數
    ((TOTAL_CHECKS++))
    if [ -n "$GEMINI_API_KEY" ]; then
        print_success "環境變數 GEMINI_API_KEY 已設定"

        # 顯示部分 API Key（隱藏敏感資訊）
        KEY_LENGTH=${#GEMINI_API_KEY}
        if [ $KEY_LENGTH -gt 8 ]; then
            MASKED_KEY="${GEMINI_API_KEY:0:4}...${GEMINI_API_KEY: -4}"
            print_info "API Key：$MASKED_KEY（長度：$KEY_LENGTH）"
        else
            print_warning "API Key 長度異常（過短）"
        fi
    else
        print_warning "環境變數 GEMINI_API_KEY 未設定"
    fi

    # 檢查專案 .env
    ((TOTAL_CHECKS++))
    if [ -f ".env" ]; then
        print_success "專案 .env 檔案存在"

        if grep -q "GEMINI_API_KEY=" .env; then
            print_info ".env 包含 GEMINI_API_KEY 設定"
        else
            print_warning ".env 未包含 GEMINI_API_KEY"
        fi
    else
        print_warning "專案 .env 檔案不存在"
        print_info "建議執行：cp .env.example .env"
    fi

    # 檢查全域配置
    ((TOTAL_CHECKS++))
    if [ -d "$HOME/.gemini" ]; then
        print_success "全域配置目錄存在：~/.gemini"

        if [ -f "$HOME/.gemini/.env" ]; then
            print_info "全域 .env 檔案存在"
        fi

        if [ -d "$HOME/.gemini/checkpoints" ]; then
            CHECKPOINT_COUNT=$(ls -1 "$HOME/.gemini/checkpoints" 2>/dev/null | wc -l)
            print_info "Checkpoints：$CHECKPOINT_COUNT 個"
        fi
    else
        print_info "全域配置目錄不存在"
    fi
}

check_shell_config() {
    print_section "Shell 配置"

    CURRENT_SHELL=$(basename "$SHELL")
    print_info "當前 Shell：$CURRENT_SHELL"

    case "$CURRENT_SHELL" in
        bash)
            CONFIG_FILE="$HOME/.bashrc"
            ;;
        zsh)
            CONFIG_FILE="$HOME/.zshrc"
            ;;
        *)
            CONFIG_FILE="$HOME/.profile"
            ;;
    esac

    ((TOTAL_CHECKS++))
    if [ -f "$CONFIG_FILE" ]; then
        print_success "Shell 配置檔存在：$CONFIG_FILE"

        if grep -q "GEMINI_API_KEY" "$CONFIG_FILE"; then
            print_info "配置檔包含 GEMINI_API_KEY 設定"
        else
            print_info "配置檔未包含 GEMINI_API_KEY"
        fi
    else
        print_warning "Shell 配置檔不存在"
    fi

    # 檢查 PATH
    print_info "PATH 設定："
    echo "$PATH" | tr ':' '\n' | while read -r path_entry; do
        if [[ "$path_entry" == *"npm"* ]] || [[ "$path_entry" == *"node"* ]]; then
            print_info "  - $path_entry"
        fi
    done
}

check_network() {
    print_section "網路連線"

    # 檢查是否可以連接 Google AI Studio
    ((TOTAL_CHECKS++))
    if ping -c 1 google.com &> /dev/null; then
        print_success "網路連線正常"
    else
        print_warning "網路連線異常"
    fi

    # 檢查 npm registry 連線
    ((TOTAL_CHECKS++))
    if curl -s https://registry.npmjs.org/@google/gemini-cli > /dev/null 2>&1; then
        print_success "npm registry 可連接"
    else
        print_warning "無法連接 npm registry"
    fi
}

check_permissions() {
    print_section "權限檢查"

    # 檢查 npm 全域安裝權限
    ((TOTAL_CHECKS++))
    NPM_PREFIX=$(npm config get prefix 2>/dev/null || echo "$HOME/.npm-global")

    if [ -w "$NPM_PREFIX" ]; then
        print_success "npm 全域目錄可寫入：$NPM_PREFIX"
    else
        print_warning "npm 全域目錄權限不足"
        print_info "建議配置使用者級別的 npm 目錄"
    fi

    # 檢查專案目錄權限
    ((TOTAL_CHECKS++))
    if [ -w "." ]; then
        print_success "當前目錄可寫入"
    else
        print_error "當前目錄權限不足"
    fi
}

################################################################################
# 主要流程
################################################################################

main() {
    print_header "$PROJECT_NAME v$PROJECT_VERSION - 環境檢查"
    echo
    print_info "檢查時間：$(date '+%Y-%m-%d %H:%M:%S')"
    print_info "檢查目錄：$(pwd)"

    # 執行所有檢查
    check_os
    check_nodejs
    check_gemini_cli
    check_api_configuration
    check_shell_config
    check_network
    check_permissions

    # 顯示總結
    print_header "檢查總結"
    echo

    echo -e "${CYAN}總檢查項目：$TOTAL_CHECKS${NC}"
    echo -e "${GREEN}通過：$PASSED_CHECKS${NC}"
    echo -e "${RED}失敗：$FAILED_CHECKS${NC}"
    echo -e "${YELLOW}警告：$WARNING_CHECKS${NC}"
    echo

    # 計算通過率
    if [ $TOTAL_CHECKS -gt 0 ]; then
        PASS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
        echo -e "${CYAN}通過率：${PASS_RATE}%${NC}"
        echo
    fi

    # 建議
    print_section "建議事項"

    if [ $FAILED_CHECKS -gt 0 ]; then
        print_error "發現 $FAILED_CHECKS 項失敗，建議修復後再使用"
    fi

    if [ $WARNING_CHECKS -gt 0 ]; then
        print_warning "發現 $WARNING_CHECKS 項警告，建議檢查"
    fi

    if [ $FAILED_CHECKS -eq 0 ] && [ $WARNING_CHECKS -eq 0 ]; then
        print_success "所有檢查通過！環境配置正常"
    fi

    echo
    print_header "檢查完成"
}

# 執行主程式
main
