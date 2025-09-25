# PTT Stock 爬蟲配置範例
# 複製此檔案為 config.py 並修改相關設定

# 資料庫設定
DATABASE_URL = "postgresql://ptt_user:password@localhost:5432/ptt_crawler"

# Redis 設定
REDIS_URL = "redis://localhost:6379"

# Firecrawl API 設定
FIRECRAWL_API_URL = "http://localhost:3002"
FIRECRAWL_API_KEY = ""  # 如果需要 API 金鑰請填入

# 爬取設定
CRAWL_RATE_LIMIT = 60  # 每分鐘最大請求數
CRAWL_REQUEST_DELAY = 1.5  # 請求間隔（秒）
CRAWL_MAX_RETRIES = 3  # 最大重試次數
CRAWL_TIMEOUT = 30  # 請求超時時間（秒）
CRAWL_CONCURRENT_LIMIT = 3  # 並發限制
CRAWL_BATCH_SIZE = 10  # 批次大小

# 資料庫連線設定
DATABASE_CONNECTION_POOL_SIZE = 10  # 連線池大小
DATABASE_CONNECTION_TIMEOUT = 30  # 連線超時時間
DATABASE_QUERY_TIMEOUT = 60  # 查詢超時時間

# Redis 連線設定
REDIS_CONNECTION_TIMEOUT = 5  # 連線超時時間
REDIS_KEY_PREFIX = "ptt:crawl:"  # 鍵值前綴

# 狀態管理設定
STATE_BACKUP_INTERVAL = 300  # 狀態備份間隔（秒）
STATE_CLEANUP_DAYS = 30  # 狀態清理天數

# 日誌設定
LOG_LEVEL = "INFO"
LOG_FILE_PATH = "logs/ptt-crawler.log"
LOG_MAX_SIZE = "10MB"
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
