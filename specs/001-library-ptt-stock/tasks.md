# 任務：PTT Stock 板爬蟲

**輸入**: 設計文件來自 `/specs/001-library-ptt-stock/`
**先決條件**: plan.md, research.md, data-model.md, quickstart.md

**重要提示**: 在執行每個任務之前，請使用 `context7-mcp` 獲取相關 library 的最新文件和使用方法，以避免使用已棄用的功能。

## Phase 3.1: 專案設定
- [ ] T001: 根據 `plan.md` 建立專案目錄結構 (`src/models`, `src/services`, `src/cli`, `tests/integration`, `tests/unit`)。
- [ ] T002: 初始化 `uv` 專案，建立 `pyproject.toml` 並新增 `firecrawl`, `psycopg2-binary`, `beautifulsoup4`, `pytest` 等依賴。
- [ ] T003: [P] 設定 `ruff` 用於程式碼 linting 和 formatting，並在 `pyproject.toml` 中配置規則。

## Phase 3.2: 測試先行 (TDD) ⚠️ 必須在 3.3 之前完成
**關鍵：這些測試必須在任何實作之前編寫並確保會失敗**
- [ ] T004: [P] 在 `tests/integration/test_crawler_service.py` 中編寫整合測試，用於 `fetch_article_list`，模擬呼叫 PTT 並驗證回傳的 URL 列表是否正確篩選。
- [ ] T005: [P] 在 `tests/integration/test_crawler_service.py` 中編寫整合測試，用於 `fetch_article_content`，使用一個固定的 URL 並驗證回傳的 `Article` 物件內容是否符合預期。
- [ ] T006: [P] 在 `tests/integration/test_cli.py` 中編寫整合測試，模擬執行 `fetch-list` 和 `fetch-content` CLI 命令，並驗證檔案輸出與資料庫寫入是否成功。

## Phase 3.3: 核心實作 (僅在測試失敗後)
- [ ] T007: [P] 在 `src/models/article.py` 中根據 `data-model.md` 建立 `Article` 資料模型 (例如使用 Pydantic 或 dataclasses)。
- [ ] T008: 在 `src/services/crawler_service.py` 中實作 `fetch_article_list` 函式。此函式應接收看板名稱和主題，爬取文章列表，並回傳篩選後的 URL 列表。
- [ ] T009: 在 `src/services/crawler_service.py` 中實作 `fetch_article_content` 函式。此函式應接收一個 URL，使用 `firecrawl` 爬取文章內容，並使用 `BeautifulSoup` 解析 Markdown，最後回傳一個 `Article` 物件。
- [ ] T010: 在 `src/cli/main.py` 中建立 `fetch-list` 命令。此命令應呼叫 `fetch_article_list` 並將結果寫入指定的 JSON 檔案。
- [ ] T011: 在 `src/cli/main.py` 中建立 `fetch-content` 命令。此命令應讀取輸入的 JSON 檔案，逐一呼叫 `fetch_article_content`，並將結果儲存到資料庫。

## Phase 3.4: 整合
- [ ] T012: 在 `src/lib/database.py` 中建立 PostgreSQL 連接和資料庫操作函式 (例如 `save_article`)。
- [ ] T013: 將 `fetch-content` 命令與 `database.py` 中的 `save_article` 函式整合，以將 `Article` 物件存入 PostgreSQL。
- [ ] T014: 在 `src/cli/main.py` 中加入 `init-db` 命令，用於根據 `research.md` 中的綱要初始化資料庫資料表。
- [ ] T015: 在 `src/services/crawler_service.py` 和 `src/cli/main.py` 中加入完整的錯誤處理和日誌記錄機制。

## Phase 3.5: 優化與潤飾
- [ ] T016: [P] 為 `src/lib/database.py` 中的資料庫操作編寫單元測試 (`tests/unit/test_database.py`)。
- [ ] T017: [P] 為 `src/services/crawler_service.py` 中的 Markdown 解析邏輯編寫單元測試 (`tests/unit/test_parser.py`)。
- [ ] T018: [P] 撰寫或更新 `README.md`，包含完整的安裝、設定和使用說明。
- [ ] T019: 手動執行 `quickstart.md` 中的所有步驟，驗證端到端流程的正確性。

## 依賴關係
- 測試 (T004-T006) 必須在核心實作 (T007-T011) 之前完成。
- T007 (模型) 必須在 T009 (服務) 和 T013 (儲存) 之前完成。
- T012 (資料庫) 必須在 T013 (儲存) 之前完成。
- 核心實作 (T007-T011) 必須在整合 (T012-T015) 之前完成。

## 並行執行範例
```
# 以下任務可以同時啟動，因為它們操作不同的檔案且沒有直接依賴
Task: "T004 [P] 在 tests/integration/test_crawler_service.py 中編寫整合測試..."
Task: "T006 [P] 在 tests/integration/test_cli.py 中編寫整合測試..."
Task: "T007 [P] 在 src/models/article.py 中根據 data-model.md 建立 Article 資料模型..."
```
