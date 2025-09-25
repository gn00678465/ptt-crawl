# Firecrawl API 整合合約

## API 端點規格

### 基礎配置
- **基礎 URL**: `{FIRECRAWL_API_URL}` (從環境變數或配置檔案讀取)
- **API 金鑰**: `{FIRECRAWL_API_KEY}` (Bearer Token 驗證)
- **內容類型**: `application/json`
- **請求超時**: 30 秒

## 文章列表爬取

### 爬取 PTT 看板頁面
**端點**: `POST /v0/scrape`

**請求格式**:
```json
{
    "url": "https://www.ptt.cc/bbs/{board}/index{page}.html",
    "formats": ["markdown", "html"],
    "onlyMainContent": true,
    "includeTags": ["a", "div"],
    "timeout": 30000,
    "waitFor": 2000
}
```

**回應格式**:
```json
{
    "success": true,
    "data": {
        "markdown": "# PTT 看板內容...",
        "html": "<html>...</html>",
        "metadata": {
            "title": "批踢踢實業坊 › Stock",
            "description": "Stock 板文章列表",
            "sourceURL": "https://www.ptt.cc/bbs/Stock/index.html",
            "statusCode": 200
        },
        "links": [
            {
                "text": "[心得] 今日操作心得分享",
                "url": "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
            }
        ]
    },
    "warning": null
}
```

### 爬取單篇文章內容
**端點**: `POST /v0/scrape`

**請求格式**:
```json
{
    "url": "https://www.ptt.cc/bbs/{board}/M.{timestamp}.A.{hash}.html",
    "formats": ["markdown"],
    "onlyMainContent": true,
    "removeBase64Images": false,
    "includeTags": ["div", "span", "time"],
    "timeout": 30000,
    "waitFor": 3000
}
```

**回應格式**:
```json
{
    "success": true,
    "data": {
        "markdown": "# [心得] 今日操作心得\n\n作者: user123\n時間: Mon Sep 25 10:30:00 2025\n\n文章內容...\n\n※ 發信站: 批踢踢實業坊(ptt.cc)",
        "metadata": {
            "title": "[心得] 今日操作心得",
            "author": "user123",
            "board": "Stock",
            "publishTime": "2025-09-25T10:30:00+08:00",
            "sourceURL": "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
            "statusCode": 200
        }
    },
    "warning": null
}
```

## 錯誤處理合約

### 錯誤回應格式
```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "錯誤訊息描述",
        "details": {
            "url": "請求的 URL",
            "timestamp": "2025-09-25T10:30:00Z",
            "statusCode": 400
        }
    }
}
```

### 錯誤類型定義

#### 網路相關錯誤
- **TIMEOUT**: 請求超時
- **CONNECTION_FAILED**: 連線失敗
- **INVALID_URL**: URL 格式無效
- **BLOCKED_URL**: URL 被封鎖或無法存取

#### API 相關錯誤
- **UNAUTHORIZED**: API 金鑰無效或過期
- **RATE_LIMITED**: 超過 API 使用限制
- **QUOTA_EXCEEDED**: 配額已用完
- **INVALID_REQUEST**: 請求格式錯誤

#### 內容相關錯誤
- **CONTENT_NOT_FOUND**: 目標內容不存在（404）
- **PARSING_FAILED**: 內容解析失敗
- **CONTENT_BLOCKED**: 內容被防爬機制阻擋
- **INVALID_CONTENT**: 內容格式異常

### 重試機制規範

#### 可重試錯誤
- `TIMEOUT`
- `CONNECTION_FAILED`
- `RATE_LIMITED`
- `PARSING_FAILED`

#### 不可重試錯誤
- `UNAUTHORIZED`
- `INVALID_URL`
- `CONTENT_NOT_FOUND`
- `QUOTA_EXCEEDED`

#### 重試策略
```python
retry_config = {
    "max_retries": 3,
    "base_delay": 1,  # 秒
    "max_delay": 60,  # 秒
    "backoff_factor": 2,  # 指數退避
    "jitter": True  # 加入隨機延遲
}

# 重試延遲計算：min(max_delay, base_delay * (backoff_factor ^ attempt) + random_jitter)
```

## 效能與限制

### API 限制
- **請求頻率**: 每分鐘最多 100 個請求
- **並發連線**: 最多 5 個同時連線
- **單次請求大小**: 最大 10MB 回應內容
- **每日配額**: 依據 API 方案而定

### 最佳化建議
- 使用連線池重複使用 HTTP 連線
- 實現請求佇列控制併發數量
- 快取常見頁面內容（如看板首頁）
- 監控 API 使用量避免超過限制

## 內容解析合約

### PTT 文章結構解析

#### 文章標題解析
從 Markdown 內容中提取標題：
```regex
# 正規表達式模式
TITLE_PATTERN = r'# \[(.*?)\] (.*?)(?:\n|$)'
# 捕獲群組: [分類] 標題
```

#### 作者資訊解析
```regex
AUTHOR_PATTERN = r'作者[：:]\s*([^\s\n]+)'
# 或從 metadata.author 直接取得
```

#### 發文時間解析
```regex
TIME_PATTERN = r'時間[：:]\s*([^\n]+)'
# ISO 格式: metadata.publishTime (優先使用)
```

#### 內容清理規則
1. 移除 PTT 系統訊息（※ 發信站等）
2. 移除推文區塊（推/噓/→）
3. 保留主要文章內容
4. 標準化換行格式

### 文章列表解析

#### 連結提取
從看板頁面提取文章連結：
```regex
ARTICLE_LINK_PATTERN = r'\[([^\]]+)\]\s*([^\n]+)\n.*?(https://www\.ptt\.cc/bbs/[^/]+/M\.[^\.]+\.A\.[^\.]+\.html)'
# 捕獲群組: [分類], 標題, URL
```

#### 分類篩選
支援的篩選模式：
```python
filter_patterns = {
    "exact": lambda category, target: category == target,
    "contains": lambda category, target: target in category,
    "regex": lambda category, target: re.match(target, category),
    "starts_with": lambda category, target: category.startswith(target)
}
```

## 整合測試規格

### 測試案例定義

#### 基礎功能測試
1. **成功爬取看板頁面**
   - 輸入：有效的看板 URL
   - 預期：回傳文章列表和連結

2. **成功爬取單篇文章**
   - 輸入：有效的文章 URL
   - 預期：回傳 Markdown 格式文章內容

3. **API 金鑰驗證**
   - 輸入：無效或過期的 API 金鑰
   - 預期：回傳 UNAUTHORIZED 錯誤

#### 錯誤處理測試
1. **網路超時測試**
   - 模擬：網路延遲超過設定時間
   - 預期：觸發重試機制

2. **內容解析失敗測試**
   - 輸入：格式異常的 PTT 頁面
   - 預期：回傳 PARSING_FAILED 錯誤

3. **速率限制測試**
   - 模擬：快速連續發送請求
   - 預期：觸發 RATE_LIMITED 錯誤

### Mock 服務規格
測試環境中使用 Mock Firecrawl 服務：
```python
mock_responses = {
    "success_board_page": {
        "success": True,
        "data": {"markdown": "# Stock 板\n...", "links": [...]}
    },
    "success_article_page": {
        "success": True,  
        "data": {"markdown": "# [心得] 測試文章\n..."}
    },
    "error_timeout": {
        "success": False,
        "error": {"code": "TIMEOUT", "message": "請求超時"}
    }
}
```

## 監控與日誌

### API 使用監控
記錄以下指標：
- 每小時/每日 API 調用次數
- 平均回應時間
- 成功/失敗率
- 錯誤類型分布

### 日誌記錄規範
```python
# 請求日誌
log.info(f"發送 Firecrawl 請求: {url}, 格式: {formats}")

# 成功日誌  
log.info(f"Firecrawl 請求成功: {url}, 回應大小: {len(content)} bytes")

# 錯誤日誌
log.error(f"Firecrawl 請求失敗: {url}, 錯誤: {error_code} - {error_message}")

# 重試日誌
log.warning(f"Firecrawl 請求重試 {attempt}/{max_retries}: {url}")
```