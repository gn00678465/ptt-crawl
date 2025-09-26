# Data Model: PTT Article

## 1. Entity: Article

This document defines the data structure for storing a crawled PTT article in the PostgreSQL database.

### Schema

- **Database**: PostgreSQL
- **Table Naming Convention**: Tables are dynamically named after the PTT board being crawled (e.g., `stock`, `gossiping`). This ensures data from different boards is segregated as required.
- **Primary Key**: The `url` field serves as the unique identifier for each article to prevent duplicates, as specified in the clarifications.

### Column Definitions

All tables created for PTT boards will share the following schema:

| Column Name     | Data Type             | Constraints              | Description                                      |
|-----------------|-----------------------|--------------------------|--------------------------------------------------|
| `id`            | `SERIAL`              | `PRIMARY KEY`            | Auto-incrementing integer for internal row ID.   |
| `category`      | `VARCHAR(50)`         |                          | The article's category (e.g., '[新聞]', '[心得]'). |
| `author`        | `VARCHAR(255)`        |                          | The author of the article.                       |
| `title`         | `VARCHAR(255)`        | `NOT NULL`               | The title of the article.                        |
| `publish_date`  | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`               | The date and time the article was published.     |
| `content`       | `TEXT`                |                          | The full Markdown content of the article.        |
| `url`           | `VARCHAR(512)`        | `UNIQUE NOT NULL`        | The unique URL of the article.                   |
| `crawled_at`    | `TIMESTAMP WITH TIME ZONE` | `DEFAULT CURRENT_TIMESTAMP` | The timestamp when the article was crawled.      |

### Example SQL (for a board named 'Stock')

```sql
CREATE TABLE IF NOT EXISTS stock (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50),
    author VARCHAR(255),
    title VARCHAR(255) NOT NULL,
    publish_date TIMESTAMP WITH TIME ZONE NOT NULL,
    content TEXT,
    url VARCHAR(512) UNIQUE NOT NULL,
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## 2. State Persistence Model

- **File**: `crawl_state.json`
- **Purpose**: To track the progress of the crawler for each board to enable incremental crawling.

### JSON Schema

```json
{
  "<board_name>": {
    "last_crawled_url": "<url_of_last_article>",
    "last_crawled_timestamp": "<iso_8601_timestamp>"
  },
  "<another_board_name>": {
    "last_crawled_url": "<url_of_last_article>",
    "last_crawled_timestamp": "<iso_8601_timestamp>"
  }
}
```

### Example

```json
{
  "Stock": {
    "last_crawled_url": "https://www.ptt.cc/bbs/Stock/M.1678886400.A.123.html",
    "last_crawled_timestamp": "2025-09-26T10:00:00Z"
  }
}
```
