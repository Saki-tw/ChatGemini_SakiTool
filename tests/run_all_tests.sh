#!/bin/bash
# ChatGemini_SakiTool 自動化測試腳本
# 運行所有測試並生成覆蓋率報告

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 獲取腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}ChatGemini_SakiTool 測試套件${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

# 檢查 pytest 是否安裝
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest 未安裝${NC}"
    echo -e "${YELLOW}請執行: pip install pytest pytest-cov pytest-mock pytest-asyncio pytest-xdist${NC}"
    exit 1
fi

# 切換到專案根目錄
cd "$PROJECT_ROOT"

echo -e "${BLUE}📍 專案根目錄: ${PROJECT_ROOT}${NC}"
echo ""

# 解析命令行參數
COVERAGE=true
VERBOSE=false
PARALLEL=false
SLOW=false
CLEAN=false
HTML_REPORT=false
FAIL_FAST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cov)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -n|--parallel)
            PARALLEL=true
            shift
            ;;
        --with-slow)
            SLOW=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --html)
            HTML_REPORT=true
            shift
            ;;
        -x|--fail-fast)
            FAIL_FAST=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [選項]"
            echo ""
            echo "選項:"
            echo "  --no-cov         不生成覆蓋率報告"
            echo "  -v, --verbose    詳細輸出模式"
            echo "  -n, --parallel   並行運行測試（使用所有 CPU 核心）"
            echo "  --with-slow      包含慢速測試"
            echo "  --clean          清理快取和報告後退出"
            echo "  --html           生成 HTML 覆蓋率報告"
            echo "  -x, --fail-fast  第一個測試失敗時立即停止"
            echo "  -h, --help       顯示此幫助訊息"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ 未知選項: $1${NC}"
            echo "使用 -h 或 --help 查看幫助"
            exit 1
            ;;
    esac
done

# 清理模式
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}🧹 清理快取和報告...${NC}"
    rm -rf .pytest_cache
    rm -rf htmlcov
    rm -rf .coverage
    rm -rf tests/__pycache__
    rm -rf tests/.pytest_cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${GREEN}✓ 清理完成${NC}"
    exit 0
fi

# 建構 pytest 命令
PYTEST_CMD="pytest tests/"

# 添加詳細輸出
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -q"
fi

# 添加並行執行
if [ "$PARALLEL" = true ]; then
    if ! command -v pytest-xdist &> /dev/null; then
        echo -e "${YELLOW}⚠ pytest-xdist 未安裝，跳過並行模式${NC}"
        echo -e "${YELLOW}  安裝: pip install pytest-xdist${NC}"
    else
        PYTEST_CMD="$PYTEST_CMD -n auto"
        echo -e "${BLUE}⚡ 啟用並行測試（自動檢測 CPU 核心數）${NC}"
    fi
fi

# 添加覆蓋率選項
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=term-missing"
    if [ "$HTML_REPORT" = true ]; then
        PYTEST_CMD="$PYTEST_CMD --cov-report=html"
        echo -e "${BLUE}📊 將生成 HTML 覆蓋率報告${NC}"
    fi
fi

# 跳過慢速測試（除非明確啟用）
if [ "$SLOW" = false ]; then
    PYTEST_CMD="$PYTEST_CMD -m 'not slow'"
    echo -e "${BLUE}⏩ 跳過慢速測試（使用 --with-slow 啟用）${NC}"
fi

# 添加 fail-fast
if [ "$FAIL_FAST" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -x"
    echo -e "${BLUE}⚠ Fail-fast 模式啟用${NC}"
fi

# 添加彩色輸出
PYTEST_CMD="$PYTEST_CMD --color=yes"

echo ""
echo -e "${MAGENTA}🚀 運行測試...${NC}"
echo -e "${BLUE}命令: ${PYTEST_CMD}${NC}"
echo ""

# 運行測試
START_TIME=$(date +%s)

if eval "$PYTEST_CMD"; then
    EXIT_CODE=0
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}✅ 所有測試通過！${NC}"
    echo -e "${GREEN}================================${NC}"
    echo -e "${CYAN}執行時間: ${DURATION} 秒${NC}"

    # 如果生成了 HTML 報告，顯示連結
    if [ "$HTML_REPORT" = true ] && [ -f "htmlcov/index.html" ]; then
        echo ""
        echo -e "${BLUE}📊 覆蓋率報告已生成:${NC}"
        echo -e "${CYAN}   file://$(pwd)/htmlcov/index.html${NC}"
        echo ""
        echo -e "${YELLOW}使用瀏覽器打開查看詳細報告${NC}"
    fi

else
    EXIT_CODE=$?
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    echo -e "${RED}================================${NC}"
    echo -e "${RED}❌ 測試失敗${NC}"
    echo -e "${RED}================================${NC}"
    echo -e "${CYAN}執行時間: ${DURATION} 秒${NC}"
    echo ""
    echo -e "${YELLOW}建議:${NC}"
    echo -e "${YELLOW}  1. 使用 -v 選項查看詳細錯誤${NC}"
    echo -e "${YELLOW}  2. 檢查失敗的測試日誌${NC}"
    echo -e "${YELLOW}  3. 確認測試環境配置正確${NC}"
fi

echo ""
echo -e "${CYAN}================================${NC}"
echo ""

# 顯示快速幫助
echo -e "${BLUE}💡 提示:${NC}"
echo -e "  ${CYAN}• 詳細輸出:${NC} ./tests/run_all_tests.sh -v"
echo -e "  ${CYAN}• 並行測試:${NC} ./tests/run_all_tests.sh -n"
echo -e "  ${CYAN}• HTML 報告:${NC} ./tests/run_all_tests.sh --html"
echo -e "  ${CYAN}• 包含慢速測試:${NC} ./tests/run_all_tests.sh --with-slow"
echo -e "  ${CYAN}• 清理快取:${NC} ./tests/run_all_tests.sh --clean"
echo ""

exit $EXIT_CODE
