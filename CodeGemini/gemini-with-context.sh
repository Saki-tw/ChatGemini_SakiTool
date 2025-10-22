#!/usr/bin/env bash
# gemini-with-context.sh
# 帶專案上下文啟動 Gemini CLI
# 版本：1.0.0
# 維護者：Saki-tw
# 日期：2025-10-21

set -euo pipefail

# 顏色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# 常數定義
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DEFAULT_CONTEXT_FILE="${SCRIPT_DIR}/GEMINI.md"

# ============================================================================
# 工具函數
# ============================================================================

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}  Gemini CLI - 帶上下文啟動${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# ============================================================================
# 檢查函數
# ============================================================================

check_gemini_cli() {
    if ! command -v gemini &> /dev/null; then
        print_error "Gemini CLI 未安裝"
        echo ""
        echo "請先執行以下指令安裝："
        echo "  ./INSTALL.sh"
        echo ""
        exit 1
    fi
    print_success "Gemini CLI 已安裝"
}

check_api_key() {
    if [[ -z "${GEMINI_API_KEY:-}" ]]; then
        # 檢查全域配置
        if [[ -f "$HOME/.gemini/.env" ]]; then
            if grep -q "GEMINI_API_KEY" "$HOME/.gemini/.env"; then
                print_success "API Key 已配置（全域）"
                return 0
            fi
        fi

        # 檢查專案配置
        if [[ -f "${SCRIPT_DIR}/.env" ]]; then
            if grep -q "GEMINI_API_KEY" "${SCRIPT_DIR}/.env"; then
                print_success "API Key 已配置（專案）"
                return 0
            fi
        fi

        print_warning "GEMINI_API_KEY 未配置"
        echo ""
        echo "建議執行以下指令配置 API Key："
        echo "  ./SETUP-API-KEY.sh"
        echo ""
        echo "或使用 OAuth 登入（啟動後會自動開啟瀏覽器）"
        echo ""
    else
        print_success "API Key 已配置（環境變數）"
    fi
}

check_context_file() {
    local context_file="$1"

    if [[ ! -f "$context_file" ]]; then
        print_error "上下文文件不存在: $context_file"
        return 1
    fi

    print_success "上下文文件: $context_file"

    # 顯示文件資訊
    local file_size=$(wc -c < "$context_file" | tr -d ' ')
    local line_count=$(wc -l < "$context_file" | tr -d ' ')
    print_info "檔案大小: ${file_size} bytes, 行數: ${line_count}"

    return 0
}

# ============================================================================
# 主要函數
# ============================================================================

show_usage() {
    cat << EOF
使用方式：
  $0 [選項] [上下文文件路徑]

選項：
  -h, --help          顯示此幫助訊息
  -v, --version       顯示版本資訊
  -m, --model MODEL   指定使用的模型（預設：gemini-2.0-flash-exp）

範例：
  # 使用預設上下文文件（GEMINI.md）
  $0

  # 使用自訂上下文文件
  $0 ~/my-project/context.md

  # 指定模型
  $0 --model gemini-2.5-pro

  # 使用自訂文件並指定模型
  $0 --model gemini-2.5-pro ~/my-project/context.md

EOF
}

show_version() {
    echo "gemini-with-context.sh v1.0.0"
}

main() {
    local context_file="$DEFAULT_CONTEXT_FILE"
    local model=""

    # 解析參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--version)
                show_version
                exit 0
                ;;
            -m|--model)
                if [[ -n "${2:-}" ]]; then
                    model="$2"
                    shift 2
                else
                    print_error "選項 --model 需要提供模型名稱"
                    exit 1
                fi
                ;;
            -*)
                print_error "未知選項: $1"
                show_usage
                exit 1
                ;;
            *)
                # 假設是上下文文件路徑
                context_file="$1"
                shift
                ;;
        esac
    done

    print_header

    # 環境檢查
    echo "🔍 檢查環境..."
    echo ""
    check_gemini_cli
    check_api_key

    # 檢查上下文文件
    echo ""
    echo "📄 檢查上下文文件..."
    echo ""
    if ! check_context_file "$context_file"; then
        echo ""
        print_info "可用的上下文文件："
        if [[ -f "$DEFAULT_CONTEXT_FILE" ]]; then
            echo "  - $DEFAULT_CONTEXT_FILE（預設）"
        fi
        if [[ -f "${SCRIPT_DIR}/README.md" ]]; then
            echo "  - ${SCRIPT_DIR}/README.md"
        fi
        echo ""
        exit 1
    fi

    # 準備啟動指令
    local launch_cmd="gemini --context \"$context_file\""

    if [[ -n "$model" ]]; then
        launch_cmd="$launch_cmd --model $model"
        print_info "使用模型: $model"
    fi

    # 顯示啟動資訊
    echo ""
    echo "🚀 準備啟動 Gemini CLI..."
    echo ""
    print_info "執行指令: $launch_cmd"
    echo ""
    echo -e "${GREEN}提示：${NC}"
    echo "  - 輸入 ${BLUE}/help${NC} 查看可用指令"
    echo "  - 輸入 ${BLUE}/context${NC} 查看當前上下文"
    echo "  - 輸入 ${BLUE}/exit${NC} 或 ${BLUE}/quit${NC} 退出"
    echo ""
    echo "按 Enter 繼續，或 Ctrl+C 取消..."
    read -r

    # 啟動 Gemini CLI
    eval "$launch_cmd"
}

# 執行主程式
main "$@"
