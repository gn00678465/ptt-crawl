#!/bin/bash
# PTT Stock 爬蟲每日執行腳本
#
# 使用方式:
#   ./daily_crawl.sh                    # 使用預設設定
#   ./daily_crawl.sh --debug            # 除錯模式
#   ./daily_crawl.sh --force            # 強制重新爬取
#   ./daily_crawl.sh --categories "心得,標的,請益"  # 指定分類
#
# 設定為 cron job:
#   0 9 * * * /path/to/ptt-crawl/examples/scripts/daily_crawl.sh >> /var/log/ptt-crawler.log 2>&1

set -euo pipefail  # 嚴格模式：錯誤時退出，未定義變數報錯，管道錯誤傳遞

# 設定預設值
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/daily_crawl.log"
LOCK_FILE="$PROJECT_ROOT/tmp/daily_crawl.lock"
CONFIG_FILE="$PROJECT_ROOT/config.py"
VENV_PATH="$PROJECT_ROOT/.venv"

# 預設爬取設定
DEFAULT_BOARD="Stock"
DEFAULT_CATEGORIES="心得,標的,請益,新聞"
DEFAULT_PAGES=5
DEBUG_MODE=false
FORCE_MODE=false
CUSTOM_CATEGORIES=""

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 輸出函數
log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $*"
}

log_warn() {
    log "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    log "${RED}[ERROR]${NC} $*"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $*"
}

# 顯示使用說明
show_usage() {
    cat << EOF
PTT Stock 爬蟲每日執行腳本

使用方式:
  $0 [選項]

選項:
  --debug                     開啟除錯模式
  --force                     強制重新爬取（忽略增量爬取）
  --categories "分類1,分類2"   指定要爬取的分類（逗號分隔）
  --pages N                   每個分類爬取的頁數（預設: 5）
  --board BOARD              指定看板（預設: Stock）
  --help                      顯示此說明

範例:
  $0                                          # 使用預設設定
  $0 --debug --force                          # 除錯模式 + 強制爬取
  $0 --categories "心得,標的" --pages 3        # 只爬取心得和標的分類，各3頁
  $0 --board Gossiping --categories "問卦"     # 爬取八卦板的問卦分類

預設設定:
  看板: $DEFAULT_BOARD
  分類: $DEFAULT_CATEGORIES
  頁數: $DEFAULT_PAGES
  增量爬取: 啟用（除非使用 --force）
EOF
}

# 解析命令列參數
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --debug)
                DEBUG_MODE=true
                shift
                ;;
            --force)
                FORCE_MODE=true
                shift
                ;;
            --categories)
                CUSTOM_CATEGORIES="$2"
                shift 2
                ;;
            --pages)
                DEFAULT_PAGES="$2"
                shift 2
                ;;
            --board)
                DEFAULT_BOARD="$2"
                shift 2
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知參數: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# 檢查環境和依賴
check_environment() {
    log_info "檢查執行環境..."

    # 檢查專案目錄
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        log_error "找不到專案根目錄: $PROJECT_ROOT"
        exit 1
    fi

    # 檢查虛擬環境
    if [[ ! -d "$VENV_PATH" ]]; then
        log_error "找不到虛擬環境: $VENV_PATH"
        log_info "請執行: cd $PROJECT_ROOT && uv venv && uv install"
        exit 1
    fi

    # 建立必要目錄
    mkdir -p "$PROJECT_ROOT/logs" "$PROJECT_ROOT/tmp"

    # 檢查鎖定檔案
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
            log_error "另一個爬取程序正在執行 (PID: $lock_pid)"
            log_info "如果確定沒有其他程序，請刪除鎖定檔案: rm $LOCK_FILE"
            exit 1
        else
            log_warn "發現過期的鎖定檔案，正在清除..."
            rm -f "$LOCK_FILE"
        fi
    fi

    # 建立鎖定檔案
    echo $$ > "$LOCK_FILE"

    log_success "環境檢查完成"
}

# 啟用虛擬環境
activate_venv() {
    log_info "啟用虛擬環境..."

    if [[ -f "$VENV_PATH/bin/activate" ]]; then
        # Linux/macOS
        source "$VENV_PATH/bin/activate"
    elif [[ -f "$VENV_PATH/Scripts/activate" ]]; then
        # Windows (Git Bash)
        source "$VENV_PATH/Scripts/activate"
    else
        log_error "找不到虛擬環境啟用腳本"
        exit 1
    fi

    log_success "虛擬環境已啟用: $(python --version)"
}

# 檢查系統狀態
check_system_health() {
    log_info "檢查系統健康狀態..."

    cd "$PROJECT_ROOT"

    # 檢查系統狀態
    if ! python -m src.cli.main status >/dev/null 2>&1; then
        log_error "系統健康檢查失敗"
        log_info "請檢查資料庫、Redis 和 Firecrawl API 連線"
        return 1
    fi

    log_success "系統健康狀態正常"
}

# 執行爬取
run_crawl() {
    local categories="${CUSTOM_CATEGORIES:-$DEFAULT_CATEGORIES}"
    local board="$DEFAULT_BOARD"
    local pages="$DEFAULT_PAGES"

    log_info "開始執行每日爬取任務"
    log_info "設定: 看板=$board, 分類=$categories, 頁數=$pages, 強制模式=$FORCE_MODE"

    cd "$PROJECT_ROOT"

    local total_articles=0
    local total_errors=0
    local start_time=$(date +%s)

    # 分割分類並逐一處理
    IFS=',' read -ra CATEGORY_ARRAY <<< "$categories"

    for category in "${CATEGORY_ARRAY[@]}"; do
        category=$(echo "$category" | xargs)  # 去除空白
        log_info "正在爬取分類: $category"

        # 建構命令
        local cmd=(python -m src.cli.main crawl "$board" --category "$category" --pages "$pages")

        if [[ "$FORCE_MODE" == "true" ]]; then
            cmd+=(--force)
        else
            cmd+=(--incremental)
        fi

        if [[ "$DEBUG_MODE" == "true" ]]; then
            cmd+=(--log-level DEBUG)
        fi

        # 執行爬取
        local category_start=$(date +%s)
        if "${cmd[@]}" 2>&1 | tee -a "$LOG_FILE"; then
            local category_end=$(date +%s)
            local category_duration=$((category_end - category_start))
            log_success "分類 $category 爬取完成 (耗時: ${category_duration}s)"
            ((total_articles += $(get_last_crawl_count))) || true
        else
            log_error "分類 $category 爬取失敗"
            ((total_errors += 1))
        fi

        # 分類間短暫延遲
        sleep 2
    done

    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))

    log_info "每日爬取任務完成"
    log_info "統計: 總文章數=$total_articles, 錯誤數=$total_errors, 總耗時=${total_duration}s"

    # 如果有錯誤，返回失敗狀態
    if [[ $total_errors -gt 0 ]]; then
        return 1
    fi
}

# 獲取最後一次爬取的文章數（簡化版）
get_last_crawl_count() {
    # 這裡應該解析實際的爬取結果，目前返回預設值
    echo "0"
}

# 執行清理工作
cleanup_old_data() {
    log_info "執行資料清理..."

    cd "$PROJECT_ROOT"

    # 清理 30 天前的爬取狀態
    if python -m src.cli.main clean --states --older-than 30 --confirm >/dev/null 2>&1; then
        log_success "狀態資料清理完成"
    else
        log_warn "狀態資料清理失敗"
    fi

    # 清理 7 天前的日誌檔案
    if python -m src.cli.main clean --logs --older-than 7 --confirm >/dev/null 2>&1; then
        log_success "日誌檔案清理完成"
    else
        log_warn "日誌檔案清理失敗"
    fi
}

# 生成每日報告
generate_daily_report() {
    log_info "生成每日報告..."

    local report_file="$PROJECT_ROOT/logs/daily_report_$(date +%Y%m%d).log"

    cd "$PROJECT_ROOT"

    {
        echo "=========================="
        echo "PTT 爬蟲每日報告"
        echo "日期: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "=========================="
        echo

        # 系統狀態
        echo "系統狀態:"
        python -m src.cli.main status --detailed 2>/dev/null || echo "  狀態查詢失敗"
        echo

        # 看板狀態
        echo "Stock 板狀態:"
        python -m src.cli.main status Stock --detailed 2>/dev/null || echo "  狀態查詢失敗"
        echo

        # 磁碟空間
        echo "磁碟空間:"
        df -h "$PROJECT_ROOT" 2>/dev/null || echo "  磁碟空間查詢失敗"
        echo

        # 記憶體使用
        echo "記憶體使用:"
        free -h 2>/dev/null || echo "  記憶體查詢失敗"
        echo

    } > "$report_file"

    log_success "每日報告已生成: $report_file"
}

# 清理函數
cleanup() {
    log_info "執行清理作業..."

    # 移除鎖定檔案
    [[ -f "$LOCK_FILE" ]] && rm -f "$LOCK_FILE"

    # 停用虛擬環境（如果啟用了）
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        deactivate 2>/dev/null || true
    fi

    log_info "清理完成"
}

# 主執行函數
main() {
    local exit_code=0

    # 設定信號處理
    trap cleanup EXIT
    trap 'log_warn "收到中斷信號，正在清理..."; exit 130' INT TERM

    log_info "開始執行 PTT Stock 每日爬取腳本"
    log_info "PID: $$, 參數: $*"

    # 解析參數
    parse_arguments "$@"

    # 檢查環境
    check_environment

    # 啟用虛擬環境
    activate_venv

    # 檢查系統健康狀態
    if ! check_system_health; then
        log_error "系統健康檢查失敗，跳過爬取任務"
        exit_code=1
    else
        # 執行爬取
        if ! run_crawl; then
            log_error "爬取任務執行失敗"
            exit_code=1
        fi

        # 清理舊資料（即使爬取失敗也執行）
        cleanup_old_data

        # 生成每日報告
        generate_daily_report
    fi

    if [[ $exit_code -eq 0 ]]; then
        log_success "每日爬取腳本執行完成"
    else
        log_error "每日爬取腳本執行失敗"
    fi

    exit $exit_code
}

# 執行主函數
main "$@"
