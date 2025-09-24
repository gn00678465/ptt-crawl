# Phase 1: 資料模型

## 實體: Article

代表一篇從 PTT 爬取的文章。

### 欄位

| 欄位名      | 資料類型        | 描述               | 驗證規則               |
|------------|-----------------|--------------------|------------------------|
| `id`       | `INTEGER`       | 唯一識別碼 (主鍵)    | 自動增長               |
| `title`    | `VARCHAR(255)`  | 文章標題           | 不可為空 (NOT NULL)      |
| `author`   | `VARCHAR(100)`  | 作者               |                        |
| `url`      | `VARCHAR(255)`  | 文章的唯一 URL     | 不可為空, 唯一 (UNIQUE) |
| `content`  | `TEXT`          | 文章的純文字內容   |                        |
| `created_at` | `TIMESTAMP`     | 文章在 PTT 上的發布時間 |                      |
| `crawled_at` | `TIMESTAMP`     | 爬取該文章的時間   | 預設為目前時間         |

### 狀態轉換

- **`new`**: 文章已被爬取但尚未儲存。
- **`saved`**: 文章已成功儲存至 PostgreSQL 資料庫。
- **`error`**: 在處理或儲存過程中發生錯誤。
