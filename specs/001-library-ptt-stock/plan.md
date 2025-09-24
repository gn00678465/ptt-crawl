# 實作計畫：PTT Stock 板爬蟲 (v2)

**分支**: `001-library-ptt-stock` | **日期**: 2025年9月24日 | **規格**: [spec.md](./spec.md)
**輸入**: 功能規格來自 `/specs/001-library-ptt-stock/spec.md`

## 總結
本計畫旨在建立一個 Python 爬蟲專案，用於爬取 PTT Stock 板的文章。此專案將採用兩階段爬取流程：首先爬取文章列表並依主題篩選，然後再根據篩選結果爬取完整的文章內容。專案將使用 `uv` 進行套件管理，並利用 `firecrawl` library 爬取文章內容為 Markdown 格式。爬取後的資料將經過解析，並儲存於 PostgreSQL 資料庫中，以供後續分析。

## 技術背景
**語言/版本**: Python 3.11+
**主要依賴**: firecrawl, psycopg2-binary, beautifulsoup4
**儲存**: PostgreSQL
**測試**: pytest
**目標平台**: 本機或伺服器端執行環境
**專案類型**: 單一專案 (Single project)
**效能目標**: [NEEDS CLARIFICATION: 爬取頻率與延遲需求]
**限制**: 遵守 PTT 的 robots.txt 及 firecrawl API 的使用限制
**規模/範圍**: 初步完成 Stock 板的爬取，可擴展至其他看板

## 憲法檢查
*GATE: 必須在 Phase 0 研究前通過。在 Phase 1 設計後重新檢查。*

- **增量爬取原則**: ✅ 計畫將包含狀態記錄機制，以避免重複爬取。
- **尊重來源網站**: ✅ 將設定合理的爬取延遲，並處理 API 錯誤。
- **可靠性優先**: ✅ 程式碼將包含錯誤處理與重試機制。
- **狀態持久化**: ✅ 將使用 PostgreSQL 資料庫儲存爬取狀態與文章資料，符合持久化要求。
- **結構化數據處理**: ✅ 爬取的 Markdown 將被解析為結構化資料後儲存。

## 專案結構

### 文件 (此功能)
```
specs/001-library-ptt-stock/
├── plan.md              # 本檔案 (/plan 指令輸出)
├── research.md          # Phase 0 輸出 (/plan 指令)
├── data-model.md        # Phase 1 輸出 (/plan 指令)
├── quickstart.md        # Phase 1 輸出 (/plan 指令)
├── contracts/           # Phase 1 輸出 (/plan 指令)
└── tasks.md             # Phase 2 輸出 (/tasks 指令 -不由 /plan 建立)
```

### 原始碼 (儲存庫根目錄)
```
# 選項 1: 單一專案 (預設)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

**結構決策**: 選項 1: 單一專案

## Phase 0: 輪廓與研究
1.  **從技術背景中提取未知數**:
    *   研究 `firecrawl` 的 Markdown 輸出格式，以確定解析方法。
    *   確認 PostgreSQL 的最佳實踐，特別是資料庫綱要 (schema) 設計。
    *   定義爬取頻率與延遲的具體數值。

2.  **產生並分派研究代理**:
    *   任務: "研究 `firecrawl` 的 Markdown 輸出，為 PTT 文章內容解析提供方案"
    *   任務: "為爬蟲專案設計 PostgreSQL 的 `articles` 資料表綱要"

3.  **在 `research.md` 中整合研究結果**。

**輸出**: `research.md`，其中所有 [NEEDS CLARIFICATION] 都已解決。

## Phase 1: 設計與合約
*先決條件: research.md 已完成*

1.  **從功能規格中提取實體** → `data-model.md`:
    *   定義 `Article` 實體，包含 `id`, `title`, `url`, `content`, `author`, `created_at` 等欄位。

2.  **產生 API 合約** (如果適用，此處為內部介面):
    *   定義 `CrawlerService` 的介面，包含 `fetch_article_list(board_name, topic)` 和 `fetch_article_content(url)` 方法。
    *   輸出至 `/contracts/`。

3.  **從合約產生合約測試**:
    *   為 `CrawlerService` 的介面撰寫測試，驗證輸入與輸出。

4.  **從使用者故事中提取測試場景**:
    *   每個故事 → 整合測試場景。
    *   `quickstart.md` 的測試 = 故事驗證步驟。

**輸出**: data-model.md, /contracts/*, 失敗的測試, quickstart.md

## Phase 2: 任務規劃方法
*本節描述 /tasks 指令將執行的操作 - 不在 /plan 期間執行*

**任務產生策略**:
-   從 Phase 1 的設計文件 (合約、資料模型、快速入門) 產生任務。
-   `fetch_article_list` → 爬取文章列表並篩選的任務。
-   `fetch_article_content` → 根據 URL 爬取單一文章內容的任務。
-   每個合約 → 合約測試任務 [P]
-   每個實體 → 模型建立任務 [P]
-   每個使用者故事 → 整合測試任務
-   為使測試通過而進行的實作任務。

**排序策略**:
-   TDD 順序: 測試先於實作。
-   依賴順序: 模型 → 服務 → CLI。
-   標記 [P] 表示可並行執行 (獨立檔案)。

## 進度追蹤
*此檢查清單在執行流程中更新*

**階段狀態**:
- [X] Phase 0: 研究完成 (/plan 指令)
- [X] Phase 1: 設計完成 (/plan 指令)
- [ ] Phase 2: 任務規劃完成 (/plan 指令 - 僅描述方法)
- [ ] Phase 3: 任務已產生 (/tasks 指令)
- [ ] Phase 4: 實作完成
- [ ] Phase 5: 驗證通過

**閘門狀態**:
- [X] 初始憲法檢查: 通過
- [X] 設計後憲法檢查: 通過
- [ ] 所有 [NEEDS CLARIFICATION] 已解決
- [ ] 複雜度偏差已記錄

---
*基於 Constitution v1.1.1 - 請參閱 `/memory/constitution.md`*
