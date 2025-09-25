# Tasks: PTT Stock 板爬蟲

**Input**: Design documents from `specs/001-library-ptt-stock/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract: Python 3.11+, typer, firecrawl-py, uv, psycopg2-binary
   → Structure: src/, tests/ (single project)
2. Load design documents:
   → data-model.md: Article, CrawlState, Config entities
   → contracts/: CLI interface, database operations, Firecrawl API
   → research.md: Two-phase crawling, uv package management
   → quickstart.md: Installation and usage scenarios
3. Generate tasks by category:
   → Setup: project init with uv, dependencies, linting
   → Tests: contract tests for each interface
   → Core: models, services, CLI commands
   → Integration: database, Redis, Firecrawl API
   → Polish: unit tests, performance validation
4. Apply TDD ordering: Tests before implementation
5. Mark [P] for parallel execution (independent files)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Phase 3.1: Setup
- [ ] T001 建立專案結構：建立 `src/`, `tests/`, `logs/` 目錄結構
- [ ] T002 初始化 Python 專案：使用 uv 建立 `pyproject.toml` 並安裝 typer, firecrawl-py, psycopg2-binary, redis 依賴
- [ ] T003 [P] 配置開發工具：設定 ruff（linting）、pytest（testing）和 pre-commit hooks

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests
- [ ] T004 [P] CLI 合約測試：在 `tests/contract/test_cli_interface.py` 測試 crawl、status、config 命令介面
- [ ] T005 [P] 資料庫合約測試：在 `tests/contract/test_database.py` 測試 Article/CrawlState/Config CRUD 操作
- [ ] T006 [P] Firecrawl API 合約測試：在 `tests/contract/test_firecrawl_api.py` 測試 scrape 端點和錯誤處理

### Integration Tests  
- [ ] T007 [P] 完整爬取流程測試：在 `tests/integration/test_crawl_workflow.py` 測試從 PTT 頁面到資料庫儲存的完整流程
- [ ] T008 [P] 增量爬取測試：在 `tests/integration/test_incremental_crawl.py` 測試狀態管理和避免重複爬取
- [ ] T009 [P] 錯誤恢復測試：在 `tests/integration/test_error_recovery.py` 測試網路錯誤、API 錯誤和狀態恢復
- [ ] T010 [P] 配置管理測試：在 `tests/integration/test_config_management.py` 測試配置讀取、設定和驗證

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models
- [ ] T011 [P] Article 模型：在 `src/models/article.py` 實作 Article 資料類別和驗證邏輯
- [ ] T012 [P] CrawlState 模型：在 `src/models/crawl_state.py` 實作 CrawlState 資料類別和狀態枚舉
- [ ] T013 [P] Config 模型：在 `src/models/config.py` 實作 Config 資料類別和預設配置

### Database Layer
- [ ] T014 [P] 資料庫初始化：在 `src/database/init.py` 實作 DDL 腳本和資料庫結構建立
- [ ] T015 [P] Article 資料庫操作：在 `src/database/article_repository.py` 實作 insert/query/update/exists 方法
- [ ] T016 [P] CrawlState 資料庫操作：在 `src/database/crawl_state_repository.py` 實作狀態管理和 URL 追蹤
- [ ] T017 [P] Config 資料庫操作：在 `src/database/config_repository.py` 實作配置儲存和讀取

### Services
- [ ] T018 爬取服務：在 `src/services/crawl_service.py` 實作兩階段爬取邏輯（文章列表→內容）
- [ ] T019 Firecrawl 整合服務：在 `src/services/firecrawl_service.py` 實作 API 調用、重試機制和內容解析
- [ ] T020 狀態管理服務：在 `src/services/state_service.py` 實作 Redis + JSON 雙層狀態管理
- [ ] T021 內容解析服務：在 `src/services/parser_service.py` 實作 PTT 文章標題/作者/內容解析

### CLI Commands
- [ ] T022 CLI 主程式：在 `src/cli/main.py` 實作 typer 應用程式和全域選項
- [ ] T023 [P] 爬取命令：在 `src/cli/crawl_command.py` 實作 crawl 命令和參數驗證
- [ ] T024 [P] 狀態命令：在 `src/cli/status_command.py` 實作 status 命令和格式化輸出
- [ ] T025 [P] 配置命令：在 `src/cli/config_command.py` 實作 config show/set/reset 子命令
- [ ] T026 [P] 清理命令：在 `src/cli/clean_command.py` 實作 clean 命令和確認機制

## Phase 3.4: Integration
- [ ] T027 資料庫連線管理：在 `src/database/connection.py` 實作 asyncpg 連線池和交易管理
- [ ] T028 Redis 連線管理：在 `src/lib/redis_client.py` 實作 Redis 連線和故障切換
- [ ] T029 配置載入器：在 `src/lib/config_loader.py` 實作環境變數和配置檔案載入
- [ ] T030 日誌設定：在 `src/lib/logging.py` 實作日誌格式化和檔案輪轉
- [ ] T031 錯誤處理中介層：在 `src/lib/error_handler.py` 實作統一錯誤處理和使用者友善訊息

## Phase 3.5: Polish
- [ ] T032 [P] 模型單元測試：在 `tests/unit/test_models.py` 測試資料驗證和序列化
- [ ] T033 [P] 解析器單元測試：在 `tests/unit/test_parser.py` 測試 PTT 內容解析邏輯
- [ ] T034 [P] 服務單元測試：在 `tests/unit/test_services.py` 測試業務邏輯和邊界條件
- [ ] T035 [P] CLI 單元測試：在 `tests/unit/test_cli.py` 測試命令參數和輸出格式
- [ ] T036 效能測試：在 `tests/performance/test_crawl_performance.py` 驗證爬取速度和記憶體使用
- [ ] T037 [P] 更新文件：更新 README.md 包含安裝、使用和 API 說明
- [ ] T038 [P] 範例腳本：建立 `examples/` 目錄包含基本使用範例
- [ ] T039 執行快速開始驗證：依照 `quickstart.md` 步驟驗證完整安裝和使用流程

## Dependencies
- Setup (T001-T003) before everything
- Contract tests (T004-T006) before implementation (T011+)
- Integration tests (T007-T010) before implementation (T011+)  
- Models (T011-T013) before repositories (T014-T017)
- Repositories (T014-T017) before services (T018-T021)
- Services (T018-T021) before CLI commands (T022-T026)
- Core implementation (T011-T026) before integration (T027-T031)
- Everything before polish (T032-T039)

**Critical TDD Dependencies:**
- T018 (crawl_service) requires T004, T005, T006, T007 to be failing
- T019 (firecrawl_service) requires T006 to be failing  
- T015-T017 (repositories) require T005 to be failing
- T023-T026 (CLI commands) require T004 to be failing

## Parallel Example
```
# Launch contract tests together (Phase 3.2):
Task: "CLI 合約測試：在 tests/contract/test_cli_interface.py 測試 crawl、status、config 命令介面"
Task: "資料庫合約測試：在 tests/contract/test_database.py 測試 Article/CrawlState/Config CRUD 操作"  
Task: "Firecrawl API 合約測試：在 tests/contract/test_firecrawl_api.py 測試 scrape 端點和錯誤處理"

# Launch model creation together (Phase 3.3):
Task: "Article 模型：在 src/models/article.py 實作 Article 資料類別和驗證邏輯"
Task: "CrawlState 模型：在 src/models/crawl_state.py 實作 CrawlState 資料類別和狀態枚舉"
Task: "Config 模型：在 src/models/config.py 實作 Config 資料類別和預設配置"
```

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts**:
   - cli-interface.md → T004 (CLI contract test) + T023-T026 (CLI commands)
   - database.md → T005 (DB contract test) + T014-T017 (repositories)
   - firecrawl-api.md → T006 (API contract test) + T019 (Firecrawl service)

2. **From Data Model**:
   - Article entity → T011 (Article model) + T015 (Article repository)
   - CrawlState entity → T012 (CrawlState model) + T016 (CrawlState repository)
   - Config entity → T013 (Config model) + T017 (Config repository)

3. **From Quickstart Scenarios**:
   - Installation steps → T001-T002 (project setup)
   - First crawl example → T007 (integration test)
   - Status checking → T008 (incremental test)
   - Error scenarios → T009 (error recovery test)

4. **From Research Decisions**:
   - uv package management → T002 (uv setup)
   - Two-phase crawling → T018 (crawl service)
   - Redis + JSON state → T020 (state service)

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] All contracts have corresponding tests (T004-T006)
- [x] All entities have model tasks (T011-T013)  
- [x] All tests come before implementation (T004-T010 before T011+)
- [x] Parallel tasks truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] TDD workflow enforced: failing tests required before implementation