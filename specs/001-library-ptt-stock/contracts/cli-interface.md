# PTT 爬蟲 CLI 介面合約

## 命令列介面規格

### 主命令結構
```bash
ptt-crawler [OPTIONS] COMMAND [ARGS]...
```

### 全域選項
- `--config-file PATH`: 指定配置檔案路徑（預設: `config.py`）
- `--log-level LEVEL`: 設定日誌級別 [DEBUG|INFO|WARNING|ERROR]（預設: `INFO`）
- `--dry-run`: 模擬執行，不實際爬取或寫入資料庫
- `--help`: 顯示說明訊息

## 爬取命令 (crawl)

### 命令格式
```bash
ptt-crawler crawl [OPTIONS] [BOARD]
```

### 參數規格
- `BOARD`: 目標看板名稱（預設: `Stock`）

### 選項規格
- `--category TEXT`: 篩選文章分類/關鍵字
- `--pages INTEGER`: 爬取頁面數量（預設: `1`，範圍: 1-50）
- `--output FORMAT`: 輸出格式 [json|csv|database]（預設: `database`）
- `--output-file PATH`: 輸出檔案路徑（當 output 非 database 時必填）
- `--force`: 強制重新爬取，忽略已處理狀態
- `--incremental / --no-incremental`: 是否使用增量爬取（預設: `--incremental`）

### 輸入驗證
- `BOARD` 必須符合 PTT 看板命名規則（英數字，長度 3-20 字符）
- `--category` 不可為空字串，最大長度 100 字符
- `--pages` 必須為正整數且不超過 50
- `--output-file` 路徑必須可寫入

### 輸出格式

#### 成功回應
```json
{
    "status": "success",
    "board": "Stock",
    "category": "心得",
    "pages_crawled": 3,
    "articles_found": 45,
    "articles_new": 12,
    "articles_updated": 2,
    "execution_time": "00:02:34",
    "output_location": "/path/to/database or file"
}
```

#### 錯誤回應
```json
{
    "status": "error",
    "error_code": "NETWORK_ERROR",
    "error_message": "無法連接到 PTT 伺服器",
    "suggestions": [
        "檢查網路連線",
        "稍後再試"
    ]
}
```

### 退出碼
- `0`: 成功完成
- `1`: 一般錯誤
- `2`: 網路連線錯誤
- `3`: 配置檔案錯誤
- `4`: 權限錯誤
- `5`: 資料庫錯誤

## 狀態命令 (status)

### 命令格式
```bash
ptt-crawler status [OPTIONS] [BOARD]
```

### 參數規格
- `BOARD`: 查詢特定看板狀態（省略則顯示所有看板）

### 選項規格
- `--format FORMAT`: 輸出格式 [table|json|yaml]（預設: `table`）
- `--detailed`: 顯示詳細狀態資訊

### 輸出格式
```json
{
    "crawl_states": [
        {
            "board": "Stock",
            "last_crawl_time": "2025-09-25T10:30:00+08:00",
            "status": "completed",
            "articles_count": 1250,
            "last_page_crawled": 10,
            "success_rate": 98.5,
            "next_incremental_available": true
        }
    ],
    "system_status": {
        "database_connected": true,
        "redis_connected": true,
        "firecrawl_api_available": true,
        "config_valid": true
    }
}
```

## 配置命令 (config)

### 命令格式
```bash
ptt-crawler config COMMAND [OPTIONS]
```

### 子命令

#### 顯示配置 (show)
```bash
ptt-crawler config show [KEY]
```
- `KEY`: 特定配置鍵名（省略則顯示所有配置）

#### 設定配置 (set)
```bash
ptt-crawler config set KEY VALUE
```
- `KEY`: 配置鍵名
- `VALUE`: 配置值

#### 重置配置 (reset)
```bash
ptt-crawler config reset [KEY]
```
- `KEY`: 重置特定配置（省略則重置所有配置）

### 可配置項目
```json
{
    "crawl.rate_limit": 60,
    "crawl.request_delay": 1.5,
    "crawl.max_retries": 3,
    "crawl.timeout": 30,
    "firecrawl.api_url": "http://localhost:3002",
    "firecrawl.api_key": "",
    "database.connection_string": "",
    "redis.connection_string": "redis://localhost:6379",
    "logging.file_path": "logs/ptt-crawler.log",
    "logging.max_size": "10MB"
}
```

## 清理命令 (clean)

### 命令格式
```bash
ptt-crawler clean [OPTIONS]
```

### 選項規格
- `--states`: 清理爬取狀態資料
- `--cache`: 清理 Redis 快取資料
- `--logs`: 清理過期日誌檔案
- `--older-than DAYS`: 清理指定天數前的資料（預設: 30）
- `--confirm / --no-confirm`: 是否需要確認（預設: `--confirm`）

## 錯誤處理規範

### 錯誤類型定義
```python
class ErrorCodes:
    NETWORK_ERROR = "NETWORK_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    API_ERROR = "API_ERROR"
```

### 錯誤訊息規範
- 所有錯誤訊息使用繁體中文
- 包含具體的錯誤描述和建議解決方案
- 提供相關的幫助文件連結或命令

### 日誌格式
```
2025-09-25 10:30:15,123 [INFO] ptt_crawler.crawl: 開始爬取 Stock 板，分類: 心得
2025-09-25 10:30:16,234 [DEBUG] ptt_crawler.firecrawl: 發送 API 請求: https://www.ptt.cc/bbs/Stock/index.html
2025-09-25 10:30:17,345 [WARNING] ptt_crawler.state: Redis 連線失敗，切換至 JSON 備份模式
2025-09-25 10:30:18,456 [ERROR] ptt_crawler.crawl: 爬取失敗 - NETWORK_ERROR: 無法連接到目標伺服器
```

## 效能與限制

### 併發控制
- 同時最多 3 個爬取執行緒
- 每個看板獨立的速率限制
- 全域請求佇列管理

### 記憶體使用
- 單次爬取任務記憶體使用不超過 500MB
- 實現串流處理避免大量資料一次載入
- 定期釋放未使用的記憶體

### 儲存空間
- 預估每篇文章平均 10KB 儲存空間
- 狀態檔案每個看板約 1MB
- 日誌檔案自動輪轉，最多保留 10 個檔案