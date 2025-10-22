#!/bin/bash

################################################################################
# CodeGemini API Key 設定腳本
# 版本：1.0.0
# 用途：互動式設定 Gemini API Key
# 日期：2025-10-21
################################################################################

set -e

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
INSTALL_DIR="$HOME/Saki_Studio/Claude/ChatGemini_SakiTool/CodeGemini"

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

print_option() {
    echo -e "${MAGENTA}  [$1] $2${NC}"
}

validate_api_key() {
    local key=$1
    local length=${#key}

    # 基本驗證：長度檢查
    if [ $length -lt 20 ]; then
        return 1
    fi

    # 檢查是否包含明顯的佔位符
    if [[ "$key" == *"your_api_key"* ]] || [[ "$key" == *"paste_here"* ]]; then
        return 1
    fi

    return 0
}

################################################################################
# 主要流程
################################################################################

print_header "$PROJECT_NAME - API Key 設定工具"
echo

print_info "此工具將協助您設定 Gemini API Key"
echo

################################################################################
# 步驟 1: 檢查現有配置
################################################################################

print_step "步驟 1/4: 檢查現有配置"
echo

HAS_ENV_VAR=false
HAS_PROJECT_ENV=false
HAS_GLOBAL_ENV=false
HAS_SHELL_CONFIG=false

# 檢查環境變數
if [ -n "$GEMINI_API_KEY" ]; then
    HAS_ENV_VAR=true
    KEY_LENGTH=${#GEMINI_API_KEY}
    MASKED_KEY="${GEMINI_API_KEY:0:4}...${GEMINI_API_KEY: -4}"
    print_info "環境變數已設定：$MASKED_KEY（長度：$KEY_LENGTH）"
fi

# 檢查專案 .env
if [ -f "$INSTALL_DIR/.env" ]; then
    HAS_PROJECT_ENV=true
    print_info "專案 .env 檔案存在"
fi

# 檢查全域 .env
if [ -f "$HOME/.gemini/.env" ]; then
    HAS_GLOBAL_ENV=true
    print_info "全域 .env 檔案存在：~/.gemini/.env"
fi

# 檢查 shell 配置
SHELL_TYPE=$(basename "$SHELL")
case "$SHELL_TYPE" in
    bash)
        SHELL_CONFIG="$HOME/.bashrc"
        ;;
    zsh)
        SHELL_CONFIG="$HOME/.zshrc"
        ;;
    *)
        SHELL_CONFIG="$HOME/.profile"
        ;;
esac

if [ -f "$SHELL_CONFIG" ] && grep -q "GEMINI_API_KEY" "$SHELL_CONFIG"; then
    HAS_SHELL_CONFIG=true
    print_info "Shell 配置檔包含 API Key：$SHELL_CONFIG"
fi

echo

################################################################################
# 步驟 2: 選擇設定方式
################################################################################

print_step "步驟 2/4: 選擇設定方式"
echo

print_info "請選擇 API Key 的設定方式："
echo

print_option "1" "專案 .env 檔案（僅此專案使用，推薦）"
print_option "2" "全域 .env 檔案（所有專案共用）"
print_option "3" "Shell 配置檔（永久生效，$SHELL_CONFIG）"
print_option "4" "顯示所有方式的設定方法"
print_option "5" "取消"

echo
read -p "請輸入選項 [1-5]: " -n 1 -r SETUP_CHOICE
echo
echo

case $SETUP_CHOICE in
    1)
        SETUP_METHOD="project"
        SETUP_FILE="$INSTALL_DIR/.env"
        print_info "將設定專案 .env：$SETUP_FILE"
        ;;
    2)
        SETUP_METHOD="global"
        SETUP_FILE="$HOME/.gemini/.env"
        print_info "將設定全域 .env：$SETUP_FILE"
        ;;
    3)
        SETUP_METHOD="shell"
        SETUP_FILE="$SHELL_CONFIG"
        print_info "將設定 Shell 配置檔：$SETUP_FILE"
        ;;
    4)
        print_header "所有設定方式"
        echo
        echo "方式 1: 專案 .env 檔案"
        echo "  檔案：$INSTALL_DIR/.env"
        echo "  設定：GEMINI_API_KEY=your_key_here"
        echo "  優點：僅影響此專案，安全性高"
        echo
        echo "方式 2: 全域 .env 檔案"
        echo "  檔案：~/.gemini/.env"
        echo "  設定：GEMINI_API_KEY=your_key_here"
        echo "  優點：所有專案共用，方便管理"
        echo
        echo "方式 3: Shell 配置檔"
        echo "  檔案：$SHELL_CONFIG"
        echo "  設定：export GEMINI_API_KEY=\"your_key_here\""
        echo "  優點：永久生效，Terminal 啟動時自動載入"
        echo
        echo "方式 4: 臨時環境變數"
        echo "  指令：export GEMINI_API_KEY=\"your_key_here\""
        echo "  優點：臨時測試，不寫入檔案"
        echo "  缺點：關閉 Terminal 後失效"
        echo
        exit 0
        ;;
    5)
        print_info "已取消設定"
        exit 0
        ;;
    *)
        print_error "無效的選項"
        exit 1
        ;;
esac

################################################################################
# 步驟 3: 取得 API Key
################################################################################

print_step "步驟 3/4: 取得 API Key"
echo

print_info "如何取得 API Key："
echo "  1. 前往 Google AI Studio"
echo "  2. 使用 Google 帳號登入"
echo "  3. 點選「Create API Key」或「Get API Key」"
echo "  4. 複製產生的 API Key"
echo

print_warning "注意：API Key 是敏感資訊，請妥善保管"
echo

# 提供連結
print_info "Google AI Studio 網址："
echo "  https://aistudio.google.com/apikey"
echo

read -p "按 Enter 繼續，或 Ctrl+C 取消..."
echo

# 輸入 API Key
echo
print_info "請貼上您的 Gemini API Key："
read -r -s API_KEY
echo

# 驗證 API Key
if ! validate_api_key "$API_KEY"; then
    print_error "API Key 格式似乎不正確"
    echo
    read -p "是否仍要繼續？[y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "已取消設定"
        exit 0
    fi
fi

################################################################################
# 步驟 4: 寫入設定
################################################################################

print_step "步驟 4/4: 寫入設定"
echo

case $SETUP_METHOD in
    project)
        # 創建或更新專案 .env
        if [ -f "$SETUP_FILE" ]; then
            # 備份現有檔案
            cp "$SETUP_FILE" "$SETUP_FILE.backup-$(date +%Y%m%d-%H%M%S)"
            print_info "已備份現有 .env"

            # 更新或新增 API Key
            if grep -q "^GEMINI_API_KEY=" "$SETUP_FILE"; then
                # 使用 sed 替換（macOS 和 Linux 相容）
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$API_KEY|" "$SETUP_FILE"
                else
                    sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$API_KEY|" "$SETUP_FILE"
                fi
                print_success "已更新 .env 中的 API Key"
            else
                echo "GEMINI_API_KEY=$API_KEY" >> "$SETUP_FILE"
                print_success "已新增 API Key 到 .env"
            fi
        else
            # 創建新檔案
            cat > "$SETUP_FILE" << EOF
# CodeGemini 環境配置
# 由 SETUP-API-KEY.sh 自動生成
# 生成時間：$(date '+%Y-%m-%d %H:%M:%S')

GEMINI_API_KEY=$API_KEY
EOF
            print_success "已創建 .env 並設定 API Key"
        fi

        # 設定檔案權限
        chmod 600 "$SETUP_FILE"
        print_success "已設定檔案權限（600）"
        ;;

    global)
        # 創建目錄
        mkdir -p "$HOME/.gemini"

        if [ -f "$SETUP_FILE" ]; then
            cp "$SETUP_FILE" "$SETUP_FILE.backup-$(date +%Y%m%d-%H%M%S)"
            print_info "已備份現有 .env"

            if grep -q "^GEMINI_API_KEY=" "$SETUP_FILE"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$API_KEY|" "$SETUP_FILE"
                else
                    sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$API_KEY|" "$SETUP_FILE"
                fi
                print_success "已更新全域 .env"
            else
                echo "GEMINI_API_KEY=$API_KEY" >> "$SETUP_FILE"
                print_success "已新增 API Key 到全域 .env"
            fi
        else
            cat > "$SETUP_FILE" << EOF
# Gemini CLI 全域配置
GEMINI_API_KEY=$API_KEY
EOF
            print_success "已創建全域 .env"
        fi

        chmod 600 "$SETUP_FILE"
        print_success "已設定檔案權限"
        ;;

    shell)
        # 備份 shell 配置
        cp "$SETUP_FILE" "$SETUP_FILE.backup-$(date +%Y%m%d-%H%M%S)"
        print_info "已備份 Shell 配置檔"

        if grep -q "GEMINI_API_KEY" "$SETUP_FILE"; then
            print_warning "Shell 配置檔已包含 GEMINI_API_KEY"
            echo
            read -p "是否要更新？[y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                # 移除舊的設定並新增
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' '/GEMINI_API_KEY/d' "$SETUP_FILE"
                else
                    sed -i '/GEMINI_API_KEY/d' "$SETUP_FILE"
                fi
                echo "" >> "$SETUP_FILE"
                echo "# Gemini CLI API Key" >> "$SETUP_FILE"
                echo "export GEMINI_API_KEY=\"$API_KEY\"" >> "$SETUP_FILE"
                print_success "已更新 Shell 配置檔"
            fi
        else
            echo "" >> "$SETUP_FILE"
            echo "# Gemini CLI API Key (由 CodeGemini SETUP-API-KEY.sh 設定)" >> "$SETUP_FILE"
            echo "export GEMINI_API_KEY=\"$API_KEY\"" >> "$SETUP_FILE"
            print_success "已新增 API Key 到 Shell 配置檔"
        fi

        print_warning "需要重新載入 Shell 配置才會生效"
        echo
        read -p "是否現在重新載入？[Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            source "$SETUP_FILE"
            print_success "已重新載入 Shell 配置"
        else
            print_info "請執行：source $SETUP_FILE"
        fi
        ;;
esac

echo

################################################################################
# 完成
################################################################################

print_header "設定完成"
echo

print_success "API Key 已成功設定"
echo

print_info "設定位置："
echo "  $SETUP_FILE"
echo

print_info "驗證設定："

case $SETUP_METHOD in
    project)
        echo "  1. 檢查檔案：cat $SETUP_FILE"
        echo "  2. 執行驗證：./CHECK.sh"
        ;;
    global)
        echo "  1. 檢查檔案：cat $SETUP_FILE"
        echo "  2. 執行驗證：./CHECK.sh"
        ;;
    shell)
        echo "  1. 開啟新 Terminal"
        echo "  2. 執行：echo \$GEMINI_API_KEY"
        echo "  3. 執行驗證：./CHECK.sh"
        ;;
esac

echo

print_info "開始使用："
echo "  gemini            # 啟動 Gemini CLI"
echo "  gemini --version  # 查看版本"
echo

print_header "設定成功"
