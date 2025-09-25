# 資料庫介面合約

## PostgreSQL 連線規格

### 連線參數
```python
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ptt_crawler",
    "user": "ptt_user", 
    "password": "secure_password",
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 3600
}
```

### 連線字串格式
```
postgresql://{user}:{password}@{host}:{port}/{database}
```

## 資料庫結構 DDL

### Articles 表格
```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(50) NOT NULL,
    board VARCHAR(50) NOT NULL,
    url VARCHAR(500) NOT NULL UNIQUE,
    content TEXT,
    publish_date TIMESTAMP NOT NULL,
    crawl_date TIMESTAMP NOT NULL DEFAULT NOW(),
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_articles_board_date ON articles(board, publish_date);
CREATE INDEX idx_articles_author ON articles(author);
CREATE INDEX idx_articles_category ON articles(category);
CREATE INDEX idx_articles_crawl_date ON articles(crawl_date);

-- 觸發器：自動更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

### CrawlStates 表格
```sql
CREATE TYPE crawl_status AS ENUM ('idle', 'crawling', 'paused', 'error', 'completed');

CREATE TABLE crawl_states (
    id SERIAL PRIMARY KEY,
    board VARCHAR(50) NOT NULL UNIQUE,
    last_crawl_time TIMESTAMP,
    last_page_crawled INTEGER DEFAULT 1,
    processed_urls JSONB DEFAULT '[]'::JSONB,
    failed_urls JSONB DEFAULT '[]'::JSONB,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    status crawl_status DEFAULT 'idle',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_crawl_states_status ON crawl_states(status);
CREATE INDEX idx_crawl_states_last_crawl ON crawl_states(last_crawl_time);
CREATE GIN INDEX idx_crawl_states_processed_urls ON crawl_states USING GIN (processed_urls);
CREATE GIN INDEX idx_crawl_states_failed_urls ON crawl_states USING GIN (failed_urls);

-- 觸發器：自動更新 updated_at
CREATE TRIGGER crawl_states_updated_at
    BEFORE UPDATE ON crawl_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

### Configs 表格
```sql
CREATE TABLE configs (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 觸發器：自動更新 updated_at
CREATE TRIGGER configs_updated_at
    BEFORE UPDATE ON configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 預設配置資料
INSERT INTO configs (key, value, description) VALUES
    ('crawl.rate_limit', '60', '每分鐘最大爬取數量'),
    ('crawl.request_delay', '1.5', '請求間隔秒數'),
    ('crawl.max_retries', '3', '最大重試次數'),
    ('crawl.timeout', '30', '請求超時時間（秒）'),
    ('firecrawl.api_url', 'http://localhost:3002', 'Firecrawl API 端點'),
    ('firecrawl.api_key', '', 'Firecrawl API 金鑰'),
    ('database.connection_pool_size', '10', '資料庫連接池大小'),
    ('redis.connection_string', 'redis://localhost:6379', 'Redis 連線字串'),
    ('logging.file_path', 'logs/ptt-crawler.log', '日誌檔案路徑'),
    ('logging.max_size', '10MB', '日誌檔案最大大小');
```

## CRUD 操作合約

### Articles 操作

#### 插入文章
```python
async def insert_article(article: Article) -> int:
    """
    插入新文章記錄
    
    Args:
        article: 文章物件
        
    Returns:
        int: 新插入記錄的 ID
        
    Raises:
        IntegrityError: URL 重複
        ValidationError: 欄位驗證失敗
    """
    query = """
        INSERT INTO articles (title, author, board, url, content, 
                            publish_date, category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
```

#### 查詢文章
```python
async def get_articles_by_board(
    board: str, 
    limit: int = 100, 
    offset: int = 0,
    category: Optional[str] = None
) -> List[Article]:
    """
    根據看板查詢文章
    
    Args:
        board: 看板名稱
        limit: 回傳數量限制
        offset: 偏移量
        category: 分類篩選
        
    Returns:
        List[Article]: 文章列表
    """
    base_query = """
        SELECT id, title, author, board, url, content, 
               publish_date, crawl_date, category, created_at, updated_at
        FROM articles 
        WHERE board = %s
    """
```

#### 更新文章內容
```python
async def update_article_content(url: str, content: str) -> bool:
    """
    更新文章內容
    
    Args:
        url: 文章 URL
        content: 新的內容
        
    Returns:
        bool: 是否成功更新
    """
    query = """
        UPDATE articles 
        SET content = %s, updated_at = NOW() 
        WHERE url = %s
    """
```

#### 檢查文章是否存在
```python
async def article_exists(url: str) -> bool:
    """
    檢查文章是否已存在
    
    Args:
        url: 文章 URL
        
    Returns:
        bool: 是否存在
    """
    query = "SELECT EXISTS(SELECT 1 FROM articles WHERE url = %s)"
```

### CrawlStates 操作

#### 初始化爬取狀態
```python
async def init_crawl_state(board: str) -> None:
    """
    初始化看板爬取狀態
    
    Args:
        board: 看板名稱
    """
    query = """
        INSERT INTO crawl_states (board, status)
        VALUES (%s, 'idle')
        ON CONFLICT (board) DO NOTHING
    """
```

#### 更新爬取狀態
```python
async def update_crawl_state(
    board: str,
    status: CrawlStatus,
    last_page_crawled: Optional[int] = None,
    error_message: Optional[str] = None
) -> None:
    """
    更新爬取狀態
    
    Args:
        board: 看板名稱
        status: 新的狀態
        last_page_crawled: 最後爬取頁面
        error_message: 錯誤訊息
    """
    query = """
        UPDATE crawl_states 
        SET status = %s, 
            last_crawl_time = NOW(),
            last_page_crawled = COALESCE(%s, last_page_crawled),
            error_message = %s
        WHERE board = %s
    """
```

#### 新增已處理 URL
```python
async def add_processed_url(board: str, url: str) -> None:
    """
    新增已處理的 URL
    
    Args:
        board: 看板名稱  
        url: 處理過的 URL
    """
    query = """
        UPDATE crawl_states 
        SET processed_urls = processed_urls || %s::jsonb
        WHERE board = %s
    """
```

#### 取得爬取狀態
```python
async def get_crawl_state(board: str) -> Optional[CrawlState]:
    """
    取得看板爬取狀態
    
    Args:
        board: 看板名稱
        
    Returns:
        Optional[CrawlState]: 爬取狀態，不存在時回傳 None
    """
    query = """
        SELECT id, board, last_crawl_time, last_page_crawled,
               processed_urls, failed_urls, retry_count, max_retries,
               status, error_message, created_at, updated_at
        FROM crawl_states
        WHERE board = %s
    """
```

### Configs 操作

#### 取得配置值
```python
async def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    取得配置值
    
    Args:
        key: 配置鍵名
        default: 預設值
        
    Returns:
        Optional[str]: 配置值
    """
    query = "SELECT value FROM configs WHERE key = %s"
```

#### 設定配置值
```python
async def set_config(key: str, value: str, description: Optional[str] = None) -> None:
    """
    設定配置值
    
    Args:
        key: 配置鍵名
        value: 配置值
        description: 配置說明
    """
    query = """
        INSERT INTO configs (key, value, description)
        VALUES (%s, %s, %s)
        ON CONFLICT (key) DO UPDATE SET
            value = EXCLUDED.value,
            description = COALESCE(EXCLUDED.description, configs.description),
            updated_at = NOW()
    """
```

## 交易管理

### 批次操作
```python
async def batch_insert_articles(articles: List[Article]) -> List[int]:
    """
    批次插入文章
    
    Args:
        articles: 文章列表
        
    Returns:
        List[int]: 插入成功的 ID 列表
    """
    async with connection.transaction():
        # 使用 COPY 或 executemany 提升效能
        pass
```

### 原子性操作
```python
async def update_crawl_progress(
    board: str, 
    processed_urls: List[str], 
    new_articles: List[Article]
) -> None:
    """
    原子性更新爬取進度和文章
    
    Args:
        board: 看板名稱
        processed_urls: 已處理 URL 列表
        new_articles: 新文章列表
    """
    async with connection.transaction():
        # 1. 插入新文章
        for article in new_articles:
            await insert_article(article)
        
        # 2. 更新爬取狀態
        await update_crawl_state(board, CrawlStatus.COMPLETED)
        
        # 3. 新增已處理 URL
        for url in processed_urls:
            await add_processed_url(board, url)
```

## 效能優化

### 連接池管理
```python
# 使用 asyncpg 連接池
import asyncpg

pool = await asyncpg.create_pool(
    dsn=DATABASE_URL,
    min_size=5,
    max_size=20,
    command_timeout=60
)
```

### 批次查詢
```python
# 使用 VALUES 子句進行批次查詢
async def check_articles_exist(urls: List[str]) -> Set[str]:
    """
    批次檢查文章是否存在
    
    Args:
        urls: URL 列表
        
    Returns:
        Set[str]: 已存在的 URL 集合
    """
    query = """
        SELECT url FROM articles 
        WHERE url = ANY($1)
    """
    rows = await connection.fetch(query, urls)
    return {row['url'] for row in rows}
```

### 索引使用指導
```sql
-- 查詢特定看板的最新文章
EXPLAIN ANALYZE 
SELECT * FROM articles 
WHERE board = 'Stock' 
ORDER BY publish_date DESC 
LIMIT 20;

-- 使用分類篩選
EXPLAIN ANALYZE
SELECT * FROM articles 
WHERE board = 'Stock' AND category LIKE '%心得%'
ORDER BY publish_date DESC;

-- JSONB 查詢已處理 URL
EXPLAIN ANALYZE
SELECT * FROM crawl_states 
WHERE processed_urls @> '["https://example.com"]'::jsonb;
```

## 備份與維護

### 定期備份
```sql
-- 每日備份腳本
pg_dump -h localhost -U ptt_user -d ptt_crawler -f backup_$(date +%Y%m%d).sql

-- 增量備份（WAL 歸檔）
archive_command = 'cp %p /backup/archive/%f'
```

### 資料清理
```sql
-- 清理過期的爬取狀態（超過 30 天）
DELETE FROM crawl_states 
WHERE last_crawl_time < NOW() - INTERVAL '30 days'
AND status = 'completed';

-- 歸檔舊文章（超過 1 年）
CREATE TABLE articles_archive (LIKE articles INCLUDING ALL);

WITH moved_articles AS (
    DELETE FROM articles 
    WHERE publish_date < NOW() - INTERVAL '1 year'
    RETURNING *
)
INSERT INTO articles_archive SELECT * FROM moved_articles;
```

### 監控查詢
```sql
-- 監控資料庫大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 監控活躍連線
SELECT count(*) as active_connections
FROM pg_stat_activity 
WHERE state = 'active';

-- 監控長時間執行的查詢
SELECT query, state, query_start, now() - query_start as duration
FROM pg_stat_activity 
WHERE state = 'active' 
AND now() - query_start > interval '1 minute';
```