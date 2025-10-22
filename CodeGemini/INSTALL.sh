#!/bin/bash

################################################################################
# CodeGemini 安裝腳本
# 版本：1.0.0
# 用途：自動化配置 Google Gemini CLI 環境
# 日期：2025-10-21
# 設計：兩階段選擇（作業系統 + CodeGemini 安裝）
################################################################################

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

################################################################################
# 主要安裝流程
################################################################################

print_header "$PROJECT_NAME v$PROJECT_VERSION - 安裝腳本"

echo
print_info "安裝目錄：$INSTALL_DIR"
echo

################################################################################
# 步驟 1: 選擇作業系統
################################################################################

print_step "步驟 1/7: 選擇您的作業系統"
echo

print_info "請選擇您的作業系統："
echo
echo "  [1] macOS（限 SoC 架構）"
echo "  [2] Linux"
echo

printf "請選擇 [1/2]: "
read -r OS_CHOICE

case "$OS_CHOICE" in
    1)
        OS_TYPE="Darwin"
        OS_DISPLAY="macOS（SoC）"
        print_success "已選擇：macOS（SoC）"
        ;;
    2)
        OS_TYPE="Linux"
        OS_DISPLAY="Linux"
        print_success "已選擇：Linux"
        ;;
    *)
        print_error "無效的選項"
        exit 1
        ;;
esac

echo

################################################################################
# 步驟 2: Node.js 檢查與安裝
################################################################################

print_step "步驟 2/7: Node.js 環境檢查"
echo

REQUIRED_NODE_VERSION=18

if check_command node; then
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    print_info "檢測到 Node.js 版本：v$(node -v | cut -d'v' -f2)"

    if [ "$NODE_VERSION" -ge "$REQUIRED_NODE_VERSION" ]; then
        print_success "Node.js 版本符合要求 (需要 v${REQUIRED_NODE_VERSION}+)"
    else
        print_error "Node.js 版本過舊 (當前: v${NODE_VERSION}, 需要: v${REQUIRED_NODE_VERSION}+)"
        print_info "請升級 Node.js 至 v${REQUIRED_NODE_VERSION} 或更高版本"
        echo
        print_info "安裝建議："

        if [[ "$OS_TYPE" == "Darwin" ]]; then
            echo "  使用 Homebrew: brew install node"
        elif [[ "$OS_TYPE" == "Linux" ]]; then
            echo "  使用 nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
            echo "  然後執行: nvm install 20"
        fi

        exit 1
    fi
else
    print_error "未檢測到 Node.js"
    print_info "Gemini CLI 需要 Node.js v${REQUIRED_NODE_VERSION} 或更高版本"
    echo
    print_info "安裝建議："

    if [[ "$OS_TYPE" == "Darwin" ]]; then
        echo "  1. 使用 Homebrew: brew install node"
        echo "  2. 從官網下載: https://nodejs.org/"
    elif [[ "$OS_TYPE" == "Linux" ]]; then
        echo "  1. 使用 nvm (推薦):"
        echo "     curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
        echo "     nvm install 20"
        echo "  2. 使用系統套件管理器:"
        echo "     Ubuntu/Debian: sudo apt install nodejs npm"
        echo "     CentOS/RHEL: sudo yum install nodejs npm"
    fi

    exit 1
fi

# 檢查 npm
if check_command npm; then
    NPM_VERSION=$(npm -v)
    print_info "檢測到 npm 版本：v${NPM_VERSION}"
    print_success "npm 已安裝"
else
    print_error "npm 未安裝"
    print_info "npm 通常隨 Node.js 一起安裝"
    exit 1
fi

echo

################################################################################
# 步驟 3: 安裝 Gemini CLI
################################################################################

print_step "步驟 3/7: 選擇安裝範圍"
echo

print_info "請選擇安裝內容："
echo
echo "  [1] 僅 ChatGemini 環境（約需 500MB）"
echo "  [2] ChatGemini 與 CodeGemini 環境（約需 550MB）"
echo

printf "請選擇 [1/2]: "
read -r INSTALL_CHOICE

case "$INSTALL_CHOICE" in
    1)
        INSTALL_CODEGEMINI=false
        print_success "已選擇：僅 ChatGemini 環境"
        ;;
    2)
        INSTALL_CODEGEMINI=true
        print_success "已選擇：ChatGemini 與 CodeGemini 環境"
        ;;
    *)
        print_error "無效的選項"
        exit 1
        ;;
esac

echo

################################################################################
# 步驟 4: 安裝 Gemini CLI
################################################################################

print_step "步驟 4/7: 安裝 Google Gemini CLI"
echo

# 檢查是否已安裝
if check_command gemini; then
    CURRENT_VERSION=$(gemini --version 2>/dev/null || echo "unknown")
    print_warning "檢測到已安裝的 Gemini CLI (版本: $CURRENT_VERSION)"

    printf "是否要重新安裝？[y/N]: "
    read -r REPLY
    if [ "$REPLY" = "y" ] || [ "$REPLY" = "Y" ]; then
        print_info "正在重新安裝 Gemini CLI..."
        npm install -g @google/gemini-cli
        print_success "Gemini CLI 已重新安裝"
    else
        print_info "跳過安裝，使用現有版本"
    fi
else
    print_info "正在安裝 @google/gemini-cli..."

    if npm install -g @google/gemini-cli; then
        print_success "Gemini CLI 安裝成功"
    else
        print_error "Gemini CLI 安裝失敗"
        print_info "請檢查 npm 權限或網路連線"
        print_info "您可能需要使用 sudo: sudo npm install -g @google/gemini-cli"
        exit 1
    fi
fi

echo

################################################################################
# 步驟 5: 驗證安裝
################################################################################

print_step "步驟 5/7: 驗證安裝"
echo

if check_command gemini; then
    INSTALLED_VERSION=$(gemini --version 2>/dev/null || echo "無法取得版本")
    print_success "Gemini CLI 已成功安裝"
    print_info "安裝版本：$INSTALLED_VERSION"

    # 檢查 gemini 命令位置
    GEMINI_PATH=$(which gemini)
    print_info "執行檔位置：$GEMINI_PATH"
else
    print_error "Gemini CLI 驗證失敗"
    print_info "請檢查安裝過程是否有錯誤"
    exit 1
fi

echo

################################################################################
# 步驟 6: CodeGemini 工具安裝（可選）
################################################################################

if [ "$INSTALL_CODEGEMINI" = true ]; then
    print_step "步驟 6/7: 安裝 CodeGemini 管理工具"
    echo

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    print_info "設置 Shell 腳本執行權限..."

    # 設置腳本執行權限（使用 POSIX 兼容方式）
    for script in CHECK.sh SETUP-API-KEY.sh UPDATE.sh UNINSTALL.sh \
                  gemini-with-context.sh checkpoint-manager.sh; do
        if [ -f "$SCRIPT_DIR/$script" ]; then
            chmod +x "$SCRIPT_DIR/$script"
            print_success "  $script"
        else
            print_warning "  找不到 $script"
        fi
    done

    echo
    print_info "設置 Python API 執行權限..."

    # 設置 CodeGemini.py 執行權限
    if [ -f "$SCRIPT_DIR/../CodeGemini.py" ]; then
        chmod +x "$SCRIPT_DIR/../CodeGemini.py"
        print_success "  CodeGemini.py"
    else
        print_warning "  找不到 CodeGemini.py"
    fi

    echo
    print_success "CodeGemini 管理工具安裝完成"
    echo
    print_info "可用工具："
    echo "  • ./CHECK.sh            - 環境檢查"
    echo "  • ./SETUP-API-KEY.sh    - API Key 設定"
    echo "  • ./UPDATE.sh           - 更新 Gemini CLI"
    echo "  • ./UNINSTALL.sh        - 卸載工具"
    echo "  • ./gemini-with-context.sh  - 帶上下文啟動"
    echo "  • ./checkpoint-manager.sh   - Checkpoint 管理"
    echo "  • ../CodeGemini.py status   - Python API（查看狀態）"
    echo
else
    print_step "步驟 6/7: 跳過 CodeGemini 工具安裝"
    echo
    print_info "已選擇僅安裝 Gemini CLI"
    print_info "如需安裝管理工具，請重新執行此腳本並選擇完整安裝"
    echo
fi

################################################################################
# 步驟 7: 環境配置
################################################################################

print_step "步驟 7/7: 環境配置設定"
echo

# 創建專案目錄結構
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

print_info "創建專案目錄結構..."

# 創建 .env.example
cat > "$INSTALL_DIR/.env.example" << 'EOF'
# CodeGemini 環境配置範例
# 複製此檔案為 .env 並填入您的實際金鑰

# Gemini API Key (從 Google AI Studio 取得)
# 網址: https://aistudio.google.com/apikey
GEMINI_API_KEY=your_api_key_here

# 選用配置
# GEMINI_MODEL=gemini-2.5-pro  # 預設模型
# GEMINI_TEMPERATURE=0.7        # 溫度參數 (0.0-1.0)
EOF

print_success "已創建 .env.example"

# 檢查是否已有 .env
if [ -f "$INSTALL_DIR/.env" ]; then
    print_warning ".env 檔案已存在，不覆蓋"
else
    print_info "請創建 .env 檔案並設定 GEMINI_API_KEY"
    echo
    print_info "步驟："
    echo "  1. 複製範例檔案: cp .env.example .env"
    echo "  2. 前往 Google AI Studio 取得 API Key:"
    echo "     https://aistudio.google.com/apikey"
    echo "  3. 編輯 .env 檔案，填入您的 API Key"
    echo

    read -p "是否現在設定 API Key？[y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo
        print_info "請輸入您的 Gemini API Key:"
        read -r API_KEY

        if [ -n "$API_KEY" ]; then
            cat > "$INSTALL_DIR/.env" << EOF
# CodeGemini 環境配置
GEMINI_API_KEY=$API_KEY
EOF
            print_success ".env 檔案已創建並設定 API Key"
        else
            print_warning "未輸入 API Key，請稍後手動設定"
        fi
    fi
fi

echo

# 提供 shell 配置建議
print_info "Shell 環境配置建議："
echo

SHELL_TYPE=$(basename "$SHELL")
case "$SHELL_TYPE" in
    bash)
        PROFILE_FILE="$HOME/.bashrc"
        ;;
    zsh)
        PROFILE_FILE="$HOME/.zshrc"
        ;;
    *)
        PROFILE_FILE="$HOME/.profile"
        ;;
esac

print_info "檢測到 Shell: $SHELL_TYPE"
print_info "建議將以下內容加入 $PROFILE_FILE:"
echo
echo "  # Gemini CLI API Key"
echo "  export GEMINI_API_KEY=\"your_api_key_here\""
echo
print_info "或者將 API Key 放在 ~/.gemini/.env 中供全域使用"

echo

################################################################################
# 完成安裝
################################################################################

echo
print_header "安裝成功"
echo

if [ "$INSTALL_CODEGEMINI" = true ]; then
    print_success "CodeGemini 完整安裝已完成"
else
    print_success "Gemini CLI 安裝已完成"
fi
echo

print_info "您的選擇："
echo "  • 作業系統: $OS_DISPLAY"
echo "  • CodeGemini: $([ "$INSTALL_CODEGEMINI" = true ] && echo "已安裝" || echo "未安裝")"
echo

print_info "版本資訊："
echo "  • Gemini CLI: $INSTALLED_VERSION"
echo "  • Node.js: v$(node -v | cut -d'v' -f2)"
echo "  • npm: v$NPM_VERSION"
echo

if [ "$INSTALL_CODEGEMINI" = true ]; then
    print_info "專案目錄："
    echo "  $INSTALL_DIR"
    echo
fi

print_info "下一步操作："
echo
echo "  1. 設定 API Key (如果尚未設定):"
echo "     • 前往 https://aistudio.google.com/apikey 取得 API Key"
if [ "$INSTALL_CODEGEMINI" = true ]; then
    echo "     • 執行設定工具: cd $INSTALL_DIR && ./SETUP-API-KEY.sh"
    echo "     • 或編輯 $INSTALL_DIR/.env 填入 API Key"
fi
echo "     • 或設定環境變數: export GEMINI_API_KEY=\"your_key\""
echo

echo "  2. 啟動 Gemini CLI:"
if [ "$INSTALL_CODEGEMINI" = true ]; then
    echo "     • 使用 CodeGemini 工具:"
    echo "       cd $INSTALL_DIR && ./gemini-with-context.sh"
    echo "     • 或直接啟動:"
fi
echo "       gemini  (OAuth 登入)"
echo "       GEMINI_API_KEY=your_key gemini  (使用 API Key)"
echo

if [ "$INSTALL_CODEGEMINI" = true ]; then
    echo "  3. 使用 CodeGemini 管理工具:"
    echo "     cd $INSTALL_DIR"
    echo "     ./CHECK.sh              - 環境檢查"
    echo "     ./SETUP-API-KEY.sh      - API Key 設定"
    echo "     ./gemini-with-context.sh - 帶上下文啟動"
    echo "     ./checkpoint-manager.sh  - Checkpoint 管理"
    echo "     ./UPDATE.sh             - 更新 Gemini CLI"
    echo "     ./UNINSTALL.sh          - 卸載工具"
    echo
fi

echo "  $([ "$INSTALL_CODEGEMINI" = true ] && echo "4" || echo "3"). Gemini CLI 基本指令:"
echo "     gemini --version    - 查看版本"
echo "     gemini --help       - 查看幫助"
echo

echo "  $([ "$INSTALL_CODEGEMINI" = true ] && echo "5" || echo "4"). CLI 內部指令（輸入 gemini 後）:"
echo "     /about     - 查看版本資訊"
echo "     /help      - 查看可用指令"
echo "     /models    - 列出可用模型"
echo "     /exit      - 退出 CLI"
echo

print_info "認證方式："
echo "  • OAuth 登入: 首次執行 gemini 時會提示登入"
echo "  • API Key: 設定 GEMINI_API_KEY 環境變數"
echo

print_header "安裝完成"
