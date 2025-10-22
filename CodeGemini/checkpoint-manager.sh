#!/usr/bin/env bash
# checkpoint-manager.sh
# Gemini CLI Checkpoint 管理工具
# 版本：1.0.0
# 維護者：Saki-tw
# 日期：2025-10-21

set -euo pipefail

# 顏色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# 常數定義
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly CHECKPOINTS_DIR="${HOME}/.gemini/checkpoints"

# ============================================================================
# 工具函數
# ============================================================================

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}  Gemini CLI - Checkpoint 管理工具${NC}"
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
        echo "  ${SCRIPT_DIR}/INSTALL.sh"
        echo ""
        return 1
    fi
    return 0
}

ensure_checkpoints_dir() {
    if [[ ! -d "$CHECKPOINTS_DIR" ]]; then
        mkdir -p "$CHECKPOINTS_DIR"
        print_info "已建立 checkpoints 目錄: $CHECKPOINTS_DIR"
    fi
}

# ============================================================================
# Checkpoint 操作函數
# ============================================================================

list_checkpoints() {
    echo -e "${CYAN}📋 Checkpoint 列表${NC}"
    echo ""

    if [[ ! -d "$CHECKPOINTS_DIR" ]] || [[ -z "$(ls -A "$CHECKPOINTS_DIR" 2>/dev/null)" ]]; then
        print_warning "目前沒有任何 checkpoint"
        echo ""
        echo "提示：在 Gemini CLI 中使用以下指令儲存對話："
        echo "  /save <checkpoint_name>"
        echo ""
        return 0
    fi

    local count=0
    echo -e "${BLUE}名稱${NC}                    ${BLUE}大小${NC}      ${BLUE}修改時間${NC}"
    echo "----------------------------------------------------"

    while IFS= read -r -d '' checkpoint; do
        local name=$(basename "$checkpoint")
        local size=$(du -h "$checkpoint" 2>/dev/null | cut -f1)
        local mtime=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$checkpoint" 2>/dev/null || stat -c "%y" "$checkpoint" 2>/dev/null | cut -d'.' -f1)

        printf "%-25s %-10s %s\n" "$name" "$size" "$mtime"
        ((count++))
    done < <(find "$CHECKPOINTS_DIR" -maxdepth 1 -type f -print0 | sort -z)

    echo ""
    print_info "共 $count 個 checkpoint"
    echo ""
}

save_checkpoint() {
    local checkpoint_name="$1"

    if [[ -z "$checkpoint_name" ]]; then
        print_error "請提供 checkpoint 名稱"
        echo ""
        echo "使用方式："
        echo "  $0 save <checkpoint_name>"
        echo ""
        return 1
    fi

    ensure_checkpoints_dir

    print_info "正在儲存 checkpoint: $checkpoint_name"
    echo ""
    print_warning "此功能需要在 Gemini CLI 執行階段中使用"
    echo ""
    echo "請在 Gemini CLI 中執行以下指令："
    echo -e "  ${CYAN}/save $checkpoint_name${NC}"
    echo ""
    echo "Checkpoint 將儲存至："
    echo "  $CHECKPOINTS_DIR/$checkpoint_name"
    echo ""
}

load_checkpoint() {
    local checkpoint_name="$1"

    if [[ -z "$checkpoint_name" ]]; then
        print_error "請提供 checkpoint 名稱"
        echo ""
        echo "使用方式："
        echo "  $0 load <checkpoint_name>"
        echo ""
        return 1
    fi

    local checkpoint_path="$CHECKPOINTS_DIR/$checkpoint_name"

    if [[ ! -f "$checkpoint_path" ]]; then
        print_error "Checkpoint 不存在: $checkpoint_name"
        echo ""
        list_checkpoints
        return 1
    fi

    print_success "找到 checkpoint: $checkpoint_name"
    echo ""
    print_info "啟動 Gemini CLI 並載入 checkpoint..."
    echo ""

    # 使用 --load 參數啟動
    gemini --load "$checkpoint_name"
}

delete_checkpoint() {
    local checkpoint_name="$1"

    if [[ -z "$checkpoint_name" ]]; then
        print_error "請提供 checkpoint 名稱"
        echo ""
        echo "使用方式："
        echo "  $0 delete <checkpoint_name>"
        echo ""
        return 1
    fi

    local checkpoint_path="$CHECKPOINTS_DIR/$checkpoint_name"

    if [[ ! -f "$checkpoint_path" ]]; then
        print_error "Checkpoint 不存在: $checkpoint_name"
        echo ""
        return 1
    fi

    # 顯示 checkpoint 資訊
    local size=$(du -h "$checkpoint_path" 2>/dev/null | cut -f1)
    echo ""
    echo -e "${YELLOW}即將刪除 checkpoint：${NC}"
    echo "  名稱：$checkpoint_name"
    echo "  大小：$size"
    echo "  路徑：$checkpoint_path"
    echo ""

    # 確認刪除
    read -p "確定要刪除嗎？(y/N) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$checkpoint_path"
        print_success "已刪除 checkpoint: $checkpoint_name"
    else
        print_info "已取消刪除"
    fi
    echo ""
}

rename_checkpoint() {
    local old_name="$1"
    local new_name="$2"

    if [[ -z "$old_name" ]] || [[ -z "$new_name" ]]; then
        print_error "請提供原名稱和新名稱"
        echo ""
        echo "使用方式："
        echo "  $0 rename <old_name> <new_name>"
        echo ""
        return 1
    fi

    local old_path="$CHECKPOINTS_DIR/$old_name"
    local new_path="$CHECKPOINTS_DIR/$new_name"

    if [[ ! -f "$old_path" ]]; then
        print_error "Checkpoint 不存在: $old_name"
        echo ""
        return 1
    fi

    if [[ -f "$new_path" ]]; then
        print_error "目標名稱已存在: $new_name"
        echo ""
        return 1
    fi

    mv "$old_path" "$new_path"
    print_success "已重新命名: $old_name → $new_name"
    echo ""
}

show_checkpoint_info() {
    local checkpoint_name="$1"

    if [[ -z "$checkpoint_name" ]]; then
        print_error "請提供 checkpoint 名稱"
        echo ""
        echo "使用方式："
        echo "  $0 info <checkpoint_name>"
        echo ""
        return 1
    fi

    local checkpoint_path="$CHECKPOINTS_DIR/$checkpoint_name"

    if [[ ! -f "$checkpoint_path" ]]; then
        print_error "Checkpoint 不存在: $checkpoint_name"
        echo ""
        return 1
    fi

    echo -e "${CYAN}📊 Checkpoint 資訊${NC}"
    echo ""
    echo "名稱：$checkpoint_name"
    echo "路徑：$checkpoint_path"

    # 檔案大小
    local size=$(du -h "$checkpoint_path" 2>/dev/null | cut -f1)
    echo "大小：$size"

    # 修改時間
    local mtime=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$checkpoint_path" 2>/dev/null || stat -c "%y" "$checkpoint_path" 2>/dev/null)
    echo "修改時間：$mtime"

    # 建立時間（僅 macOS）
    if [[ "$(uname)" == "Darwin" ]]; then
        local btime=$(stat -f "%SB" -t "%Y-%m-%d %H:%M:%S" "$checkpoint_path" 2>/dev/null)
        echo "建立時間：$btime"
    fi

    # 行數（如果是文字檔）
    if file "$checkpoint_path" | grep -q "text"; then
        local lines=$(wc -l < "$checkpoint_path" | tr -d ' ')
        echo "行數：$lines"
    fi

    echo ""
}

# ============================================================================
# 互動式選單
# ============================================================================

interactive_menu() {
    while true; do
        print_header

        echo "請選擇操作："
        echo ""
        echo "  ${CYAN}[1]${NC} 列出所有 checkpoints"
        echo "  ${CYAN}[2]${NC} 載入 checkpoint"
        echo "  ${CYAN}[3]${NC} 刪除 checkpoint"
        echo "  ${CYAN}[4]${NC} 重新命名 checkpoint"
        echo "  ${CYAN}[5]${NC} 顯示 checkpoint 資訊"
        echo "  ${CYAN}[6]${NC} 開啟 checkpoints 目錄"
        echo "  ${CYAN}[0]${NC} 退出"
        echo ""
        read -p "請輸入選項 [0-6]: " -n 1 -r choice
        echo ""
        echo ""

        case $choice in
            1)
                list_checkpoints
                ;;
            2)
                echo "可用的 checkpoints："
                echo ""
                list_checkpoints
                read -p "請輸入要載入的 checkpoint 名稱: " name
                if [[ -n "$name" ]]; then
                    load_checkpoint "$name"
                    exit 0
                fi
                ;;
            3)
                echo "可用的 checkpoints："
                echo ""
                list_checkpoints
                read -p "請輸入要刪除的 checkpoint 名稱: " name
                if [[ -n "$name" ]]; then
                    delete_checkpoint "$name"
                fi
                ;;
            4)
                echo "可用的 checkpoints："
                echo ""
                list_checkpoints
                read -p "請輸入原 checkpoint 名稱: " old_name
                read -p "請輸入新名稱: " new_name
                if [[ -n "$old_name" ]] && [[ -n "$new_name" ]]; then
                    rename_checkpoint "$old_name" "$new_name"
                fi
                ;;
            5)
                echo "可用的 checkpoints："
                echo ""
                list_checkpoints
                read -p "請輸入 checkpoint 名稱: " name
                if [[ -n "$name" ]]; then
                    show_checkpoint_info "$name"
                fi
                ;;
            6)
                ensure_checkpoints_dir
                print_info "開啟目錄: $CHECKPOINTS_DIR"
                echo ""
                if command -v open &> /dev/null; then
                    open "$CHECKPOINTS_DIR"
                elif command -v xdg-open &> /dev/null; then
                    xdg-open "$CHECKPOINTS_DIR"
                else
                    print_warning "無法自動開啟，請手動前往："
                    echo "  $CHECKPOINTS_DIR"
                fi
                ;;
            0)
                print_info "再見！"
                echo ""
                exit 0
                ;;
            *)
                print_error "無效的選項"
                echo ""
                ;;
        esac

        if [[ $choice != "2" ]]; then
            read -p "按 Enter 繼續..." -r
            clear
        fi
    done
}

# ============================================================================
# 主要函數
# ============================================================================

show_usage() {
    cat << EOF
Gemini CLI Checkpoint 管理工具

使用方式：
  $0 [指令] [參數]

指令：
  list                    列出所有 checkpoints
  load <name>             載入指定的 checkpoint
  delete <name>           刪除指定的 checkpoint
  rename <old> <new>      重新命名 checkpoint
  info <name>             顯示 checkpoint 資訊
  interactive             啟動互動式選單（預設）

選項：
  -h, --help              顯示此幫助訊息
  -v, --version           顯示版本資訊

範例：
  # 列出所有 checkpoints
  $0 list

  # 載入 checkpoint
  $0 load my-session

  # 刪除 checkpoint
  $0 delete old-session

  # 重新命名
  $0 rename old-name new-name

  # 顯示資訊
  $0 info my-session

  # 互動式選單
  $0
  $0 interactive

說明：
  Checkpoints 儲存於: ~/.gemini/checkpoints/

  在 Gemini CLI 中儲存 checkpoint：
    /save <checkpoint_name>

  載入 checkpoint 並啟動：
    gemini --load <checkpoint_name>

EOF
}

show_version() {
    echo "checkpoint-manager.sh v1.0.0"
}

main() {
    # 檢查 Gemini CLI
    if ! check_gemini_cli; then
        exit 1
    fi

    # 確保目錄存在
    ensure_checkpoints_dir

    # 解析參數
    case "${1:-interactive}" in
        list)
            list_checkpoints
            ;;
        load)
            load_checkpoint "${2:-}"
            ;;
        delete)
            delete_checkpoint "${2:-}"
            ;;
        rename)
            rename_checkpoint "${2:-}" "${3:-}"
            ;;
        info)
            show_checkpoint_info "${2:-}"
            ;;
        interactive)
            interactive_menu
            ;;
        -h|--help)
            show_usage
            ;;
        -v|--version)
            show_version
            ;;
        *)
            print_error "未知指令: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# 執行主程式
main "$@"
