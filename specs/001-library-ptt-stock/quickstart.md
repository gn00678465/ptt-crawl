# PTT Stock 爬蟲快速開始指南

## 前置需求

### 系統需求
- Python 3.11 或更高版本
- PostgreSQL 12 或更高版本  
- Redis 6 或更高版本
- 可存取網際網路（用於爬取 PTT 和呼叫 Firecrawl API）

### 硬體建議
- RAM: 最低 4GB，建議 8GB 或以上
- 磁碟空間: 最低 10GB 可用空間
- 網路: 穩定的寬頻連線

## 安裝步驟

### 1. 複製專案
```bash
git clone <repository-url>
cd ptt-crawl
```

### 2. 安裝 uv 套件管理工具
```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 建立虛擬環境並安裝依賴
```bash
# 建立虛擬環境
uv venv

# 啟用虛擬環境
# Windows
.venv\Scripts\activate

# macOS/Linux  
source .venv/bin/activate

# 安裝專案依賴
uv install
```

### 4. 設定資料庫

#### 安裝 PostgreSQL
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# macOS (使用 Homebrew)
brew install postgresql

# Windows - 下載並安裝 PostgreSQL installer
```

#### 建立資料庫
```sql
-- 連接到 PostgreSQL
sudo -u postgres psql

-- 建立使用者
CREATE USER ptt_user WITH PASSWORD 'secure_password';

-- 建立資料庫
CREATE DATABASE ptt_crawler OWNER ptt_user;

-- 授予權限
GRANT ALL PRIVILEGES ON DATABASE ptt_crawler TO ptt_user;
```

### 5. 設定 Redis
```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS (使用 Homebrew)
brew install redis

# Windows - 下載並安裝 Redis
```

啟動 Redis 服務：
```bash
# Ubuntu/Debian
sudo systemctl start redis-server

# macOS
brew services start redis

# 或手動啟動
redis-server
```

### 6. 設定 Firecrawl 服務

#### 使用 Docker Compose 啟動本地 Firecrawl 服務
```bash
# 進入 firecrawl 目錄
cd firecrawl

# 啟動服務
docker-compose up -d

# 確認服務運行
curl http://localhost:3002/health
```

#### 或使用現有的 Firecrawl 服務
如果您已有 Firecrawl 服務實例，請記錄其 API 端點和金鑰。

## 配置設定

### 建立配置檔案
建立 `config.py` 檔案（複製自 `config.example.py`）：

```python
# config.py
import os
from typing import Optional

class Settings:
    # 資料庫設定
    DATABASE_URL: str = "postgresql://ptt_user:secure_password@localhost:5432/ptt_crawler"
    
    # Redis 設定
    REDIS_URL: str = "redis://localhost:6379"
    
    # Firecrawl API 設定
    FIRECRAWL_API_URL: str = "http://localhost:3002"
    FIRECRAWL_API_KEY: Optional[str] = None  # 如果需要 API 金鑰
    
    # 爬取設定
    CRAWL_RATE_LIMIT: int = 60  # 每分鐘最大請求數
    CRAWL_REQUEST_DELAY: float = 1.5  # 請求間隔（秒）
    CRAWL_MAX_RETRIES: int = 3
    CRAWL_TIMEOUT: int = 30
    
    # 日誌設定
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/ptt-crawler.log"
    LOG_MAX_SIZE: str = "10MB"
    LOG_BACKUP_COUNT: int = 5

# 從環境變數載入設定（可選）
settings = Settings()

# 支援從環境變數覆蓋設定
if os.getenv("DATABASE_URL"):
    settings.DATABASE_URL = os.getenv("DATABASE_URL")
    
if os.getenv("REDIS_URL"):
    settings.REDIS_URL = os.getenv("REDIS_URL")
    
if os.getenv("FIRECRAWL_API_URL"):
    settings.FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL")
    
if os.getenv("FIRECRAWL_API_KEY"):
    settings.FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
```

### 環境變數設定（可選）
建立 `.env` 檔案：
```env
DATABASE_URL=postgresql://ptt_user:secure_password@localhost:5432/ptt_crawler
REDIS_URL=redis://localhost:6379
FIRECRAWL_API_URL=http://localhost:3002
FIRECRAWL_API_KEY=your_api_key_if_needed
LOG_LEVEL=INFO
```

## 初始化系統

### 1. 初始化資料庫結構
```bash
# 執行資料庫遷移腳本
python scripts/init_database.py

# 或使用 CLI 命令
ptt-crawler init-db
```

### 2. 驗證配置
```bash
# 測試資料庫連線
ptt-crawler config test-db

# 測試 Redis 連線  
ptt-crawler config test-redis

# 測試 Firecrawl API
ptt-crawler config test-firecrawl

# 或全部一起測試
ptt-crawler config test-all
```

### 3. 建立日誌目錄
```bash
mkdir -p logs
```

## 第一次執行

### 1. 查看系統狀態
```bash
# 檢查整體系統狀態
ptt-crawler status

# 預期輸出類似：
# ╭─────────────────────────────────────────────────────╮
# │                    系統狀態                          │
# ├─────────────────────────────────────────────────────┤
# │ 資料庫連線: ✅ 正常                                   │
# │ Redis 連線: ✅ 正常                                   │
# │ Firecrawl API: ✅ 正常                               │
# │ 配置檔案: ✅ 有效                                     │
# ╰─────────────────────────────────────────────────────╯
```

### 2. 設定基本配置
```bash
# 設定 Firecrawl API 端點（如果需要修改）
ptt-crawler config set firecrawl.api_url "http://localhost:3002"

# 設定爬取頻率限制
ptt-crawler config set crawl.rate_limit 60

# 查看所有配置
ptt-crawler config show
```

### 3. 執行第一次爬取
```bash
# 爬取 Stock 板的前 3 頁，篩選「心得」分類
ptt-crawler crawl Stock --category "心得" --pages 3

# 預期輸出類似：
# 🚀 開始爬取 PTT Stock 板
# 📝 篩選分類: 心得
# 📄 爬取頁面: 3 頁
# 
# ⏳ 正在爬取第 1 頁...
# ✅ 找到 8 篇符合條件的文章
# ⏳ 正在爬取第 2 頁...
# ✅ 找到 6 篇符合條件的文章
# ⏳ 正在爬取第 3 頁...
# ✅ 找到 7 篇符合條件的文章
# 
# 📊 爬取完成統計:
# • 總文章數: 21 篇
# • 新文章: 21 篇
# • 更新文章: 0 篇
# • 執行時間: 00:01:23
# • 儲存位置: PostgreSQL 資料庫
```

### 4. 驗證爬取結果
```bash
# 查看爬取狀態
ptt-crawler status Stock

# 預期輸出類似：
# ╭─────────────────────────────────────────────────────╮
# │                 Stock 板爬取狀態                      │
# ├─────────────────────────────────────────────────────┤
# │ 最後爬取時間: 2025-09-25 10:30:15                    │
# │ 爬取狀態: 已完成                                      │
# │ 文章數量: 21 篇                                       │
# │ 最後爬取頁面: 3                                       │
# │ 成功率: 100.0%                                       │
# │ 支援增量爬取: ✅                                       │
# ╰─────────────────────────────────────────────────────╯
```

## 常見使用場景

### 場景 1: 定期爬取新文章
```bash
# 使用增量爬取，只爬取新增的文章
ptt-crawler crawl Stock --category "心得" --incremental

# 設定為定期任務 (cron job)
# 每小時執行一次
# 0 * * * * cd /path/to/ptt-crawl && ptt-crawler crawl Stock --incremental
```

### 場景 2: 爬取特定分類文章
```bash
# 爬取「標的」分類文章
ptt-crawler crawl Stock --category "標的" --pages 5

# 爬取「請益」分類文章
ptt-crawler crawl Stock --category "請益" --pages 2

# 不限分類，爬取所有文章
ptt-crawler crawl Stock --pages 10
```

### 場景 3: 匯出爬取資料
```bash
# 匯出為 JSON 格式
ptt-crawler crawl Stock --category "心得" --pages 2 --output json --output-file output.json

# 匯出為 CSV 格式
ptt-crawler crawl Stock --category "標的" --pages 3 --output csv --output-file articles.csv
```

### 場景 4: 強制重新爬取
```bash
# 忽略已爬取狀態，強制重新爬取
ptt-crawler crawl Stock --category "心得" --pages 3 --force
```

## 維護作業

### 清理舊資料
```bash
# 清理 30 天前的爬取狀態
ptt-crawler clean --states --older-than 30

# 清理 Redis 快取
ptt-crawler clean --cache

# 清理過期日誌
ptt-crawler clean --logs --older-than 7
```

### 監控系統健康狀態
```bash
# 定期檢查系統狀態
ptt-crawler status --detailed

# 查看特定看板狀態
ptt-crawler status Stock --detailed
```

### 備份與恢復
```bash
# 備份資料庫
pg_dump -h localhost -U ptt_user ptt_crawler > backup.sql

# 恢復資料庫
psql -h localhost -U ptt_user ptt_crawler < backup.sql

# 備份 Redis 狀態
redis-cli --rdb redis_backup.rdb

# 備份配置
cp config.py config_backup.py
```

## 疑難排解

### 常見錯誤與解決方案

#### 資料庫連線失敗
```bash
# 錯誤: FATAL: password authentication failed
# 解決: 檢查資料庫帳號密碼和連線字串
ptt-crawler config set database.connection_string "postgresql://correct_user:correct_password@localhost:5432/ptt_crawler"
```

#### Redis 連線失敗
```bash
# 錯誤: Redis connection failed
# 解決: 確認 Redis 服務運行
sudo systemctl status redis-server

# 或啟動 Redis
sudo systemctl start redis-server
```

#### Firecrawl API 錯誤
```bash
# 錯誤: Firecrawl API not available
# 解決: 檢查 Firecrawl 服務狀態
curl http://localhost:3002/health

# 重新啟動 Firecrawl 服務
cd firecrawl && docker-compose restart
```

#### 爬取速度過慢
```bash
# 調整爬取參數
ptt-crawler config set crawl.request_delay 1.0  # 縮短請求間隔
ptt-crawler config set crawl.rate_limit 100    # 提高頻率限制
```

#### 記憶體使用過高
```bash
# 減少並發數量和批次大小
ptt-crawler config set crawl.concurrent_limit 2
ptt-crawler config set crawl.batch_size 10
```

### 查看詳細日誌
```bash
# 查看即時日誌
tail -f logs/ptt-crawler.log

# 查看錯誤日誌
grep ERROR logs/ptt-crawler.log

# 使用 debug 模式執行
ptt-crawler --log-level DEBUG crawl Stock --category "心得"
```

### 重置系統狀態
```bash
# 重置特定看板狀態
ptt-crawler reset-state Stock

# 清空所有狀態（謹慎使用）
ptt-crawler reset-state --all --confirm
```

## 效能調校

### 最佳化建議
1. **調整 PostgreSQL 設定**：
   - 增加 `shared_buffers` 和 `work_mem`
   - 啟用 `log_slow_queries` 監控慢查詢

2. **調整 Redis 設定**：
   - 啟用 AOF 持久化: `appendonly yes`
   - 設定記憶體策略: `maxmemory-policy allkeys-lru`

3. **調整爬取參數**：
   - 根據網路狀況調整 `request_delay`
   - 根據伺服器效能調整 `rate_limit`

4. **監控資源使用**：
   - 定期檢查磁碟空間使用
   - 監控資料庫和 Redis 記憶體使用
   - 觀察網路頻寬使用情況

## 下一步

完成快速開始後，您可以：

1. **閱讀進階文件**：
   - 查看 API 合約文件了解詳細介面
   - 閱讀資料模型文件了解資料結構

2. **客製化配置**：
   - 根據需求調整爬取參數
   - 設定自動化任務排程

3. **擴展功能**：
   - 新增其他 PTT 看板支援
   - 整合資料分析工具
   - 建立資料視覺化介面

4. **參與開發**：
   - 提交 Issue 回報問題
   - 提交 Pull Request 貢獻程式碼
   - 參與討論改進建議