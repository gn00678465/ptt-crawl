# 快速入門指南：PTT Stock 板爬蟲 (v3)

本指南將引導您完成設定與執行 PTT Stock 板爬蟲的完整流程。

## 1. 環境設定

### 安裝 `uv`

首先，請確保您已安裝 `uv`。如果尚未安裝，請參考官方文件進行安裝。

### 建立虛擬環境

```bash
# 建立虛擬環境
uv venv

# 啟用虛擬環境 (Windows)
.venv\Scripts\activate

# 啟用虛擬環境 (macOS/Linux)
source .venv/bin/activate
```

### 安裝依賴

使用 `uv sync` 來安裝 `pyproject.toml` 中定義的所有依賴。

```bash
# 同步虛擬環境與 pyproject.toml 中的依賴
uv sync
```

若要新增套件，請使用 `uv add`。

```bash
# 範例：新增一個名為 `requests` 的套件
uv add requests
```

## 2. 資料庫設定

- 確保您的 PostgreSQL 服務正在運行。
- 在您的資料庫中建立一個名為 `ptt_articles` 的資料庫 (或您偏好的名稱)。
- 設定環境變數以連接到您的資料庫。建立一個 `.env` 檔案，並填入以下內容:

```
DATABASE_URL="postgresql://user:password@host:port/database"
```

## 3. 執行資料庫遷移 (初始化)

執行指令碼以在資料庫中建立 `articles` 資料表。

```bash
python -m src.cli init-db
```

## 4. 執行爬蟲 (兩階段流程)

### 第一階段：爬取並篩選文章列表

此命令會爬取 Stock 板上標題包含「心得」的文章列表，並將結果 (URL 列表) 儲存到一個暫存檔案中。

```bash
python -m src.cli fetch-list --board Stock --topic 心得 --output-file article_urls.json
```

### 第二階段：根據列表爬取文章內容

此命令會讀取暫存檔案中的 URL 列表，逐一爬取每篇文章的完整內容，並儲存到資料庫。

```bash
python -m src.cli fetch-content --input-file article_urls.json
```

## 5. 驗證結果

執行爬蟲後，您可以連接到 PostgreSQL 資料庫並查詢 `articles` 資料表，以確認文章資料是否已成功儲存。

```sql
SELECT * FROM articles LIMIT 10;
```
