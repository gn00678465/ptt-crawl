# PTT Stock 板爬蟲工具

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)

一個高效能的 PTT Stock 板爬蟲工具，支援增量爬取、分類過濾、狀態管理和資料匯出功能。

## 🚀 功能特色

- **兩階段爬取架構**：先爬取文章列表，再爬取文章內容，提供更好的錯誤處理和狀態追蹤
- **增量爬取支援**：智慧避免重複爬取已獲取的文章，大幅提升效率
- **分類過濾**：支援依文章分類（心得、標的、請益等）進行精確爬取
- **雙重狀態管理**：Redis + JSON 備份，確保狀態資料在系統故障時不遺失
- **多格式輸出**：支援 JSON、CSV 格式匯出，方便後續資料分析
- **錯誤恢復機制**：自動重試、網路異常處理、服務降級等完整錯誤處理
- **效能最佳化**：請求頻率控制、並發限制、記憶體管理等效能優化
- **完整日誌系統**：分級日誌記錄、檔案輪轉、錯誤追蹤等監控功能

## 📋 系統需求

### 最低需求
- **Python**: 3.11 或更高版本
- **PostgreSQL**: 12 或更高版本
- **Redis**: 6 或更高版本
- **RAM**: 4GB（建議 8GB 或以上）
- **磁碟空間**: 10GB 可用空間
- **網路**: 穩定的寬頻連線

### 外部服務
- **Firecrawl API**: 用於網頁爬取（支援自建或雲端服務）
- **可存取網際網路**: 用於爬取 PTT 內容

## 🛠 快速安裝

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

### 4. 設定資料庫和 Redis
請參考 [完整安裝指南](specs/001-library-ptt-stock/quickstart.md#安裝步驟) 進行詳細設定。

## ⚡ 快速開始

### 1. 檢查系統狀態
```bash
# 檢查整體系統狀態
ptt-crawler status
```

### 2. 第一次爬取
```bash
# 爬取 Stock 板的心得文章，前 3 頁
ptt-crawler crawl Stock --category "心得" --pages 3
```

### 3. 查看爬取結果
```bash
# 查看 Stock 板爬取狀態
ptt-crawler status Stock
```

## 📖 使用說明

### 基本命令

#### 爬取文章
```bash
# 基本爬取
ptt-crawler crawl Stock --pages 5

# 分類過濾爬取
ptt-crawler crawl Stock --category "心得" --pages 3

# 增量爬取（只爬取新文章）
ptt-crawler crawl Stock --incremental

# 強制重新爬取
ptt-crawler crawl Stock --force --pages 2
```

#### 匯出資料
```bash
# 匯出為 JSON
ptt-crawler crawl Stock --output json --output-file articles.json

# 匯出為 CSV
ptt-crawler crawl Stock --output csv --output-file articles.csv
```

#### 系統管理
```bash
# 查看系統狀態
ptt-crawler status --detailed

# 查看看板狀態
ptt-crawler status Stock

# 清理過期狀態
ptt-crawler clean --states --older-than 30

# 清理 Redis 快取
ptt-crawler clean --cache
```

#### 配置管理
```bash
# 查看所有配置
ptt-crawler config show

# 設定配置值
ptt-crawler config set crawl.rate_limit 60

# 重置配置
ptt-crawler config reset crawl.rate_limit
```

### 進階功能

#### 定期爬取設定
```bash
# 設定 cron job 進行定期爬取
# 每小時執行增量爬取
0 * * * * cd /path/to/ptt-crawl && ptt-crawler crawl Stock --incremental
```

#### 效能調校
```python
# 調整爬取參數
ptt-crawler config set crawl.request_delay 1.0      # 請求間隔
ptt-crawler config set crawl.rate_limit 100         # 頻率限制
ptt-crawler config set crawl.concurrent_limit 5     # 並發限制
ptt-crawler config set crawl.batch_size 20          # 批次大小
```

## 🏗 架構說明

### 核心組件
- **CrawlService**: 兩階段爬取邏輯實作
- **StateService**: Redis + JSON 雙重狀態管理
- **ParserService**: PTT 文章內容解析
- **RedisClient**: Redis 連線管理與錯誤恢復
- **ConfigLoader**: 多來源配置載入

### 資料流程
```
1. 爬取看板頁面 → 提取文章連結
2. 爬取個別文章 → 解析文章內容
3. 狀態管理 → Redis 快取 + JSON 備份
4. 資料儲存 → PostgreSQL 資料庫
5. 結果輸出 → JSON/CSV 檔案
```

### 錯誤處理
- **網路錯誤**: 自動重試機制，指數退避策略
- **服務降級**: Redis 無法使用時降級至 JSON 狀態管理
- **資料驗證**: 完整的資料格式驗證和清理
- **狀態恢復**: 系統重啟後自動恢復爬取狀態

## 🧪 測試

### 執行測試
```bash
# 執行所有測試
uv run python -m pytest

# 執行單元測試
uv run python -m pytest tests/unit/

# 執行整合測試
uv run python -m pytest tests/integration/

# 執行效能測試
uv run python -m pytest tests/performance/

# 生成測試覆蓋率報告
uv run python -m pytest --cov=src tests/
```

### 測試覆蓋
- **單元測試**: 模型、服務、CLI 命令
- **整合測試**: 資料庫、Redis、Firecrawl 整合
- **效能測試**: 記憶體使用、並發處理、大量資料測試

## 📊 監控與維護

### 日誌管理
```bash
# 查看即時日誌
tail -f logs/ptt-crawler.log

# 查看錯誤日誌
grep ERROR logs/ptt-crawler.log

# Debug 模式執行
ptt-crawler --log-level DEBUG crawl Stock
```

### 系統維護
```bash
# 清理舊資料
ptt-crawler clean --states --older-than 30
ptt-crawler clean --logs --older-than 7

# 備份資料
pg_dump -h localhost -U ptt_user ptt_crawler > backup.sql
redis-cli --rdb redis_backup.rdb
```

## 🤝 開發指南

### 開發環境設定
```bash
# 安裝開發依賴
uv install --group dev

# 安裝 pre-commit hooks
pre-commit install

# 執行程式碼檢查
ruff check src/
black src/
mypy src/
```

### 程式碼貢獻
1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

### 專案結構
```
ptt-crawl/
├── src/                    # 主要程式碼
│   ├── cli/               # CLI 命令介面
│   ├── models/            # 資料模型
│   ├── repositories/      # 資料存取層
│   ├── services/          # 業務邏輯層
│   └── lib/               # 工具函式庫
├── tests/                  # 測試程式
├── docs/                   # 文件
├── specs/                  # 規格說明
└── examples/               # 使用範例
```

## 🔧 疑難排解

### 常見問題

#### 資料庫連線失敗
```bash
# 檢查連線設定
ptt-crawler config test-db

# 更新連線字串
ptt-crawler config set database.connection_string "postgresql://user:pass@host:port/db"
```

#### Redis 連線失敗
```bash
# 檢查 Redis 狀態
sudo systemctl status redis-server

# 重新啟動 Redis
sudo systemctl restart redis-server
```

#### Firecrawl API 錯誤
```bash
# 檢查 API 健康狀態
curl http://localhost:3002/health

# 重新啟動 Firecrawl 服務
cd firecrawl && docker-compose restart
```

### 效能問題
- **記憶體使用過高**: 減少 `concurrent_limit` 和 `batch_size`
- **爬取速度過慢**: 調整 `request_delay` 和 `rate_limit`
- **資料庫效能**: 增加 PostgreSQL `shared_buffers` 和 `work_mem`

更多疑難排解資訊請參考 [完整疑難排解指南](specs/001-library-ptt-stock/quickstart.md#疑難排解)。

## 📚 文件

- [快速開始指南](specs/001-library-ptt-stock/quickstart.md)
- [API 合約文件](specs/001-library-ptt-stock/contracts/)
- [任務實作計畫](specs/001-library-ptt-stock/tasks.md)
- [專案規格說明](specs/001-library-ptt-stock/spec.md)

## 📄 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案。

## 🙏 致謝

- [PTT](https://www.ptt.cc/) - 提供豐富的討論內容
- [Firecrawl](https://firecrawl.dev/) - 優秀的網頁爬取服務
- [Typer](https://typer.tiangolo.com/) - 現代 Python CLI 框架
- [FastAPI](https://fastapi.tiangolo.com/) 團隊 - 相關生態系工具

## 📞 聯繫方式

- 問題回報: [GitHub Issues](../../issues)
- 功能建議: [GitHub Discussions](../../discussions)
- 電子郵件: [專案維護者信箱]

---

**注意**: 請遵守 PTT 的使用條款和爬蟲政策，適度使用本工具，避免對 PTT 伺服器造成過大負擔。