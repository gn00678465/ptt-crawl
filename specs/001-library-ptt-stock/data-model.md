# 資料模型設計

## 核心實體定義

### Article (文章)
PTT 文章的核心資料模型，包含文章的完整資訊。

**欄位定義**:
```python
@dataclass
class Article:
    id: int  # 主鍵，自動遞增
    title: str  # 文章標題，必填，最大長度 500 字符
    author: str  # 作者 ID，必填，最大長度 50 字符  
    board: str  # 看板名稱，必填，最大長度 50 字符
    url: str  # 文章 URL，必填且唯一，最大長度 500 字符
    content: str | None  # Markdown 格式內容，可為空
    publish_date: datetime  # 發表時間，必填
    crawl_date: datetime  # 爬取時間，必填，預設為當前時間
    category: str | None  # 文章分類標籤，可為空，最大長度 100 字符
    created_at: datetime  # 記錄建立時間，自動設定
    updated_at: datetime  # 記錄更新時間，自動更新
```

**驗證規則**:
- `title` 不可為空字串
- `url` 必須為有效的 PTT URL 格式
- `author` 不可包含特殊字符
- `publish_date` 不可晚於 `crawl_date`
- `board` 必須符合 PTT 看板命名規則

**索引設計**:
- 主索引: `id` (PRIMARY KEY)
- 唯一索引: `url` (UNIQUE)
- 複合索引: `(board, publish_date)` - 支援按看板和時間查詢
- 索引: `author` - 支援按作者查詢
- 索引: `category` - 支援按分類查詢

### CrawlState (爬取狀態)
管理爬取進度和狀態，支援增量爬取和故障恢復。

**欄位定義**:
```python
@dataclass  
class CrawlState:
    id: int  # 主鍵，自動遞增
    board: str  # 看板名稱，必填且唯一，最大長度 50 字符
    last_crawl_time: datetime  # 最後成功爬取時間
    last_page_crawled: int  # 最後爬取的頁面編號，預設 1
    processed_urls: list[str]  # 已處理的 URL 列表，JSON 格式儲存
    failed_urls: list[str]  # 爬取失敗的 URL 列表，JSON 格式儲存
    retry_count: int  # 當前重試次數，預設 0
    max_retries: int  # 最大重試次數，預設 3
    status: CrawlStatus  # 爬取狀態枚舉
    error_message: str | None  # 最近一次錯誤訊息，可為空
    created_at: datetime  # 記錄建立時間，自動設定
    updated_at: datetime  # 記錄更新時間，自動更新
```

**狀態枚舉**:
```python
class CrawlStatus(Enum):
    IDLE = "idle"          # 閒置狀態
    CRAWLING = "crawling"  # 正在爬取
    PAUSED = "paused"      # 暫停中
    ERROR = "error"        # 錯誤狀態
    COMPLETED = "completed" # 完成
```

**驗證規則**:
- `board` 不可為空且符合看板命名規則
- `retry_count` 不可超過 `max_retries`
- `processed_urls` 和 `failed_urls` 必須為有效的 URL 列表
- `last_crawl_time` 不可晚於當前時間

**索引設計**:
- 主索引: `id` (PRIMARY KEY)
- 唯一索引: `board` (UNIQUE)
- 索引: `status` - 支援按狀態查詢
- 索引: `last_crawl_time` - 支援按時間排序

### Config (配置管理)
儲存系統配置和參數設定。

**欄位定義**:
```python
@dataclass
class Config:
    key: str  # 配置鍵名，主鍵，最大長度 100 字符
    value: str  # 配置值，JSON 格式儲存，最大長度 1000 字符
    description: str | None  # 配置說明，可為空，最大長度 200 字符
    created_at: datetime  # 建立時間，自動設定
    updated_at: datetime  # 更新時間，自動更新
```

**預設配置項**:
```python
DEFAULT_CONFIG = {
    "crawl.rate_limit": "60",  # 每分鐘最大爬取數量
    "crawl.request_delay": "1.5",  # 請求間隔秒數
    "crawl.max_retries": "3",  # 最大重試次數
    "crawl.timeout": "30",  # 請求超時時間
    "firecrawl.api_url": "",  # Firecrawl API 端點
    "firecrawl.api_key": "",  # Firecrawl API 金鑰
    "database.connection_pool_size": "10",  # 資料庫連接池大小
}
```

## 實體關聯

### 一對多關聯
- `CrawlState` → `Article`: 一個爬取狀態對應多篇文章
  - 外鍵: `Article.board` → `CrawlState.board`
  - 級聯操作: 刪除 CrawlState 時保留 Article

### 資料一致性約束
- 確保每篇文章都有對應的爬取狀態記錄
- 防止重複 URL 的文章被插入
- 維護爬取狀態的時間順序一致性

## 資料庫架構考量

### PostgreSQL 特定優化
- 使用 JSONB 欄位型別儲存 `processed_urls` 和 `failed_urls`
- 建立 GIN 索引支援 JSONB 查詢
- 使用 PostgreSQL 的 UPSERT 功能處理狀態更新

### 分區策略（未來擴展）
- 按時間分區 Article 表格（每月一個分區）
- 提升大量歷史資料的查詢效能

### 備份策略
- 定期自動備份所有表格
- 重點保護 CrawlState 表格的狀態資料
- 支援增量備份和完整備份

## 狀態管理流程

### Redis 狀態結構
```python
# Redis 鍵名規範
REDIS_KEYS = {
    "crawl_state": "ptt:crawl:state:{board}",  # 爬取狀態
    "processed_urls": "ptt:crawl:processed:{board}",  # 已處理 URL 集合
    "failed_urls": "ptt:crawl:failed:{board}",  # 失敗 URL 集合  
    "rate_limit": "ptt:crawl:rate_limit:{board}",  # 速率限制計數器
}
```

### JSON 備份格式
```python
# 狀態備份檔案格式
{
    "version": "1.0",
    "timestamp": "2025-09-25T10:00:00Z",
    "board": "Stock",
    "crawl_state": {
        "last_crawl_time": "2025-09-25T09:30:00Z",
        "last_page_crawled": 5,
        "status": "completed",
        "retry_count": 0,
        "error_message": null
    },
    "processed_urls": ["url1", "url2", "..."],
    "failed_urls": ["failed_url1", "..."],
    "statistics": {
        "total_processed": 150,
        "total_failed": 2,
        "success_rate": 98.67
    }
}
```

### 狀態同步機制
1. **寫入操作**: 先更新 Redis，再同步至 JSON 檔案
2. **讀取操作**: 優先從 Redis 讀取，失敗則從 JSON 恢復
3. **一致性檢查**: 定期比對 Redis 和 JSON 的狀態差異
4. **故障恢復**: 系統啟動時自動檢測並恢復狀態