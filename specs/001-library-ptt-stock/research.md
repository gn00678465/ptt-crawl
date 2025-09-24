# Phase 0: 研究

## 1. `firecrawl` Markdown 輸出格式研究

- **決策**: 使用 `BeautifulSoup` library 解析 `firecrawl` 回傳的 Markdown 內容。
- **理由**: `firecrawl` 的輸出是標準的 Markdown 格式，但其中可能包含 HTML 標籤。`BeautifulSoup` 能夠有效地處理這種混合內容，並從中提取結構化資訊，如作者、標題、發布時間和內文。
- **考慮過的替代方案**: 純手動解析 Markdown，但這種方法複雜且容易出錯，特別是在處理不規則的 HTML 結構時。

## 2. PostgreSQL 資料庫綱要 (Schema) 設計

- **決策**: 建立一個名為 `articles` 的資料表，用於儲存爬取到的文章。
- **綱要**:
  ```sql
  CREATE TABLE articles (
      id SERIAL PRIMARY KEY,
      title VARCHAR(255) NOT NULL,
      author VARCHAR(100),
      url VARCHAR(255) UNIQUE NOT NULL,
      content TEXT,
      created_at TIMESTAMP,
      crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- **理由**: 這個綱要包含了文章的基本資訊，`url` 欄位設定為 `UNIQUE` 以防止重複儲存。`crawled_at` 時間戳有助於追蹤爬取狀態。

## 3. 爬取頻率與延遲定義

- **決策**: 設定每次 API 請求之間有 2 秒的延遲。
- **理由**: 遵循「尊重來源網站」的原則，避免對 PTT 伺服器或 `firecrawl` API 造成過大負擔。這個延遲可以在設定檔中進行調整。
- **考慮過的替代方案**: 更短的延遲可能會提高爬取速度，但會增加被封鎖的風險。
