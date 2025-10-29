#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_VERSION="1.0.3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="${SCRIPT_DIR}/venv_py314"
DETECTED_OS=""
INSTALL_CODEGEMINI=false
AUTO_MODE=false

# 檢查是否為自動模式
if [[ "$1" == "--auto" ]] || [[ "$1" == "-y" ]]; then
    AUTO_MODE=true
fi

show_progress() {
    local width=40
    for ((i=0; i<=width; i++)); do
        local percent=$((i * 100 / width))
        printf "\r  ["
        for ((j=0; j<i; j++)); do printf "█"; done
        for ((j=i; j<width; j++)); do printf "░"; done
        printf "] ${percent}%%"
        sleep 0.15
    done
    echo ""
}

select_os() {
    # 自動偵測作業系統
    if [[ "$OSTYPE" == "darwin"* ]]; then
        DETECTED_OS="macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        DETECTED_OS="Linux"
    else
        DETECTED_OS="Linux"  # 預設 Linux
    fi

    # 自動模式：跳過顯示
    if [[ "$AUTO_MODE" == true ]]; then
        return
    fi

    # 互動模式：顯示資訊
    clear
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   ${BOLD}ChatGemini_SakiTool v${PROJECT_VERSION}${NC}${CYAN}       ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "作業系統：${GREEN}${DETECTED_OS}${NC}"
    echo ""
    read -p "按 Enter 繼續..."
}

select_installation() {
    # 自動模式：預設安裝完整版（含 CodeGemini）
    if [[ "$AUTO_MODE" == true ]]; then
        INSTALL_CODEGEMINI=true
        return
    fi

    # 互動模式：詢問用戶
    clear
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   選擇安裝範圍                         ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${BOLD}[1] 基礎版 (ChatGemini)${NC} ${BLUE}(約 500 MB)${NC}"
    echo ""
    echo "將安裝："
    echo "  • ChatGemini 對話工具"
    echo "  • 圖像/影片分析與生成"
    echo "  • 自動快取系統"
    echo ""
    echo "包含套件："
    echo "  • Python 3.10+, pip, ffmpeg"
    echo "  • google-genai, rich, prompt-toolkit"
    echo "  • Pillow, numpy, requests 等"
    echo "  • 工具模組：requests, beautifulsoup4, html2text, duckduckgo-search (~1 MB)"
    echo ""

    echo -e "${BOLD}[2] 完整版 (ChatGemini + CodeGemini)${NC} ${BLUE}(約 550 MB，推薦)${NC}"
    echo ""
    echo "將安裝："
    echo "  • 基礎版所有功能"
    echo "  • CodeGemini 程式碼助手"
    echo "  • 向量資料庫搜尋（Codebase Embedding）"
    echo "  • MCP Server 整合"
    echo ""
    echo "額外套件："
    echo "  • Node.js 18+, npm"
    echo "  • Google Cloud SDK"
    echo "  • @google/generative-ai"
    echo ""
    echo -e "${GREEN}推薦選擇完整版，只多 50 MB 但功能更強大${NC}"
    echo ""

    read -p "選擇 [1/2]: " -n 1 -r INSTALL_CHOICE
    echo ""

    case $INSTALL_CHOICE in
        1) INSTALL_CODEGEMINI=false ;;
        2) INSTALL_CODEGEMINI=true ;;
        *) echo -e "${RED}無效選項${NC}"; exit 1 ;;
    esac
}

install_all() {
    clear
    echo ""
    echo -e "${CYAN}安裝中...${NC}"
    echo ""

    (
        if [ -d "${SCRIPT_DIR}/.git" ]; then
            git -C "$SCRIPT_DIR" pull --rebase --quiet 2>/dev/null || true
        fi

        if [[ "$DETECTED_OS" == "macOS" ]]; then
            if ! command -v brew &> /dev/null; then
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" < /dev/null
                if [[ $(uname -m) == 'arm64' ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                else
                    eval "$(/usr/local/bin/brew shellenv)"
                fi
            fi

            command -v python3 &> /dev/null || brew install python@3.14 || brew install python@3.10
            command -v ffmpeg &> /dev/null || brew install ffmpeg
            brew list python-yq &> /dev/null || brew install python-yq

            if [ "$INSTALL_CODEGEMINI" = true ]; then
                command -v node &> /dev/null || brew install node
                command -v gcloud &> /dev/null || brew install --cask google-cloud-sdk
            fi

        elif [[ "$DETECTED_OS" == "Linux" ]]; then
            if command -v apt &> /dev/null; then
                if ! command -v python3 &> /dev/null; then
                    sudo apt update
                    sudo apt install -y python3 python3-pip python3-venv
                fi
                command -v ffmpeg &> /dev/null || sudo apt install -y ffmpeg
                command -v yq &> /dev/null || sudo apt install -y yq

                if [ "$INSTALL_CODEGEMINI" = true ]; then
                    command -v node &> /dev/null || sudo apt install -y nodejs npm
                    if ! command -v gcloud &> /dev/null; then
                        curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
                        tar -xf google-cloud-cli-linux-x86_64.tar.gz
                        ./google-cloud-sdk/install.sh --quiet
                        rm -f google-cloud-cli-linux-x86_64.tar.gz
                    fi
                fi

            elif command -v yum &> /dev/null; then
                command -v python3 &> /dev/null || sudo yum install -y python3 python3-pip
                command -v ffmpeg &> /dev/null || sudo yum install -y ffmpeg

                if [ "$INSTALL_CODEGEMINI" = true ]; then
                    command -v node &> /dev/null || sudo yum install -y nodejs npm
                fi

            elif command -v pacman &> /dev/null; then
                command -v python3 &> /dev/null || sudo pacman -S --noconfirm python python-pip
                command -v ffmpeg &> /dev/null || sudo pacman -S --noconfirm ffmpeg

                if [ "$INSTALL_CODEGEMINI" = true ]; then
                    command -v node &> /dev/null || sudo pacman -S --noconfirm nodejs npm
                fi
            fi
        fi

        [ ! -d "$VENV_DIR" ] && python3 -m venv "$VENV_DIR"

        source "$VENV_DIR/bin/activate"
        pip install --upgrade pip setuptools wheel --quiet

        # 優先使用 brew 安裝可用的依賴（macOS）
        if [[ "$DETECTED_OS" == "macOS" ]]; then
            # brew 可安裝的套件（若可用）
            command -v ffmpeg &> /dev/null || brew install ffmpeg
        fi

        # pip 安裝所有 Python 依賴（包含工具模組）
        pip install -r "$SCRIPT_DIR/requirements.txt" --quiet

        [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/.env.example" ] && cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"

        if [ "$INSTALL_CODEGEMINI" = true ]; then
            npm install -g @google/generative-ai 2>/dev/null || true
        fi

        deactivate

        if [ -n "$ZSH_VERSION" ]; then
            SHELL_RC="$HOME/.zshrc"
        elif [ -n "$BASH_VERSION" ]; then
            SHELL_RC="$HOME/.bashrc"
            [[ "$OSTYPE" == "darwin"* ]] && SHELL_RC="$HOME/.bash_profile"
        else
            SHELL_RC="$HOME/.profile"
        fi

        if grep -q "# ChatGemini_SakiTool" "$SHELL_RC" 2>/dev/null; then
            sed -i.bak '/# ChatGemini_SakiTool/,/^$/d' "$SHELL_RC" 2>/dev/null
        fi

        cat >> "$SHELL_RC" << ALIASES

# ChatGemini_SakiTool Global Aliases (v${PROJECT_VERSION})
alias ChatGemini='GEMINI_OUTPUT_DIR=claude ${VENV_DIR}/bin/python ${SCRIPT_DIR}/gemini_chat.py'
alias chatgemini='GEMINI_OUTPUT_DIR=claude ${VENV_DIR}/bin/python ${SCRIPT_DIR}/gemini_chat.py'
alias CHATGEMINI='GEMINI_OUTPUT_DIR=claude ${VENV_DIR}/bin/python ${SCRIPT_DIR}/gemini_chat.py'
alias ChatGEMINI='GEMINI_OUTPUT_DIR=claude ${VENV_DIR}/bin/python ${SCRIPT_DIR}/gemini_chat.py'

ALIASES

    ) > /dev/null 2>&1 &

    INSTALL_PID=$!
    show_progress
    wait $INSTALL_PID

    echo ""
    echo -e "${GREEN}✓ 安裝完成${NC}"
    echo ""
}

setup_api_key() {
    # 自動模式：跳過互動式設定
    if [[ "$AUTO_MODE" == true ]]; then
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}📝 設定 API Key${NC}"
        echo ""
        echo "請編輯以下檔案並填入您的 API Key："
        echo -e "${GREEN}${SCRIPT_DIR}/.env${NC}"
        echo ""
        echo "取得 API Key 請前往："
        echo -e "${BLUE}https://aistudio.google.com/app/apikey${NC}"
        echo ""
        echo "完成後，在任意位置輸入 'ChatGemini' 即可啟動"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        return
    fi

    # 互動模式：提供立即設定選項
    clear
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   ${BOLD}設定 API Key${NC}${CYAN}                        ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}取得您的免費 API Key：${NC}"
    echo -e "${BLUE}https://aistudio.google.com/app/apikey${NC}"
    echo ""
    echo "步驟："
    echo "  1. 前往上述網址（Google AI Studio）"
    echo "  2. 登入 Google 帳號"
    echo "  3. 點擊「Create API Key」"
    echo "  4. 複製產生的 API Key"
    echo ""

    read -p "現在設定 API Key？(Y/n): " -n 1 -r SETUP_NOW
    echo ""

    if [[ $SETUP_NOW =~ ^[Nn]$ ]]; then
        echo ""
        echo -e "${YELLOW}稍後請編輯此檔案：${NC}"
        echo -e "${GREEN}${SCRIPT_DIR}/.env${NC}"
        echo ""
        echo "完成後，在任意位置輸入 'ChatGemini' 即可啟動"
        return
    fi

    echo ""
    echo -e "${CYAN}請貼上您的 API Key：${NC}"
    read -r API_KEY_INPUT

    if [[ -z "$API_KEY_INPUT" ]]; then
        echo ""
        echo -e "${YELLOW}未輸入 API Key，稍後請編輯：${NC}"
        echo -e "${GREEN}${SCRIPT_DIR}/.env${NC}"
        echo ""
        return
    fi

    # 寫入 .env 檔案
    if [[ -f "${SCRIPT_DIR}/.env" ]]; then
        # 替換現有的 API Key
        if grep -q "GEMINI_API_KEY=" "${SCRIPT_DIR}/.env"; then
            sed -i.bak "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=${API_KEY_INPUT}/" "${SCRIPT_DIR}/.env"
        else
            echo "GEMINI_API_KEY=${API_KEY_INPUT}" >> "${SCRIPT_DIR}/.env"
        fi
    else
        echo "GEMINI_API_KEY=${API_KEY_INPUT}" > "${SCRIPT_DIR}/.env"
    fi

    echo ""
    echo -e "${GREEN}✓ API Key 已儲存${NC}"
    echo ""
    echo "重新開啟終端機後，在任意位置輸入 'ChatGemini' 即可啟動"
    echo ""
}

select_os
select_installation
install_all
setup_api_key
