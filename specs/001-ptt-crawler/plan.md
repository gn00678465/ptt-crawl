# Implementation Plan: PTT Crawler

**Branch**: `001-ptt-crawler` | **Date**: 2025-09-26 | **Spec**: [E:\not_company\ptt-crawl\specs\001-ptt-crawler\spec.md](E:\not_company\ptt-crawl\specs\001-ptt-crawler\spec.md)
**Input**: Feature specification from `/specs/001-ptt-crawler/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

## Summary
The project will create a Python-based CLI tool to crawl articles from PTT. It will use the Firecrawl library to fetch content, allow filtering by article category, and store the results in a PostgreSQL database, with tables dynamically named after the PTT board. The system is designed for incremental crawling, persisting its state in a JSON file to avoid duplicate work.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: `firecrawl-py`, `typer`, `python-dotenv`, `psycopg2-binary`, `uv`
**Storage**: PostgreSQL
**Testing**: `pytest`
**Target Platform**: Command-Line Interface (CLI) on Windows, macOS, and Linux
**Project Type**: Single project
**Performance Goals**: Respectful crawling limits (approx. 1 request/sec), stable memory usage.
**Constraints**: Must support both cloud and self-hosted Firecrawl. Must follow incremental crawling and JSON state persistence principles from the constitution.
**Scale/Scope**: Crawl specified PTT boards, filter by category, and store structured article data.

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Incremental Crawling**: **PASS**. The design includes a `crawl_state.json` file to track progress and avoid re-crawling.
- **II. Respectful Crawling**: **PASS**. The implementation will include delays between requests to avoid overloading the PTT servers.
- **III. Reliability First**: **PASS**. The design includes error handling for network issues and database operations. State persistence ensures recovery.
- **IV. State Persistence**: **PASS**. The design explicitly uses a JSON file for state persistence, with atomic writes planned.
- **V. Structured Data Processing**: **PASS**. PTT articles will be parsed into a structured `Article` dataclass before being stored in PostgreSQL.
- **VI. Language and Style Guide**: **PASS**. All generated documents are in Traditional Chinese as required.

## Project Structure

### Documentation (this feature)
```
specs/001-ptt-crawler/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/
│   └── article.py       # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── main.py              # CLI entry point using Typer
├── config.py            # Environment variable loading
├── crawler.py           # Firecrawl logic for fetching pages
├── parser.py            # HTML parsing logic
├── database.py          # PostgreSQL interaction logic
└── state_manager.py     # JSON state persistence logic
└── models.py            # Data models (e.g., Article)

tests/
├── integration/
│   └── test_cli.py
└── unit/
    ├── test_parser.py
    └── test_state_manager.py

.env
requirements.txt
```

**Structure Decision**: The project will use a "Single project" structure. This is a simple, effective layout for a self-contained CLI tool. The source code is organized into feature-specific modules (`crawler.py`, `database.py`, etc.) under a single `src` directory, which is a standard Python practice.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context**: Completed.
2. **Generate and dispatch research agents**: Completed.
3. **Consolidate findings** in `research.md`: Completed.

**Output**: `research.md` with all technical decisions resolved.

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`: Completed.
2. **Generate API contracts** from functional requirements → `contracts/article.py`: Completed.
3. **Generate contract tests**: Will be done in the implementation phase.
4. **Extract test scenarios** from user stories → `quickstart.md`: Completed.
5. **Update agent file incrementally**: Skipped for this workflow as it is not required.

**Output**: `data-model.md`, `contracts/article.py`, `quickstart.md`.

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base.
- Generate tasks from the files created in Phase 1 (`data-model.md`, `contracts/article.py`, `quickstart.md`) and the project structure defined above.
- Create tasks for each component:
  - **Setup**: Project scaffolding, `uv` setup, `requirements.txt`.
  - **Core Logic**: `config.py`, `database.py`, `state_manager.py`, `crawler.py`, `parser.py`.
  - **CLI**: `main.py` with Typer commands.
  - **Testing**: Unit tests for parser and state manager, integration test for the CLI.

**Ordering Strategy**:
- **Foundation First**: Setup, config, and models.
- **TDD Order**: Write tests before the implementation for key components.
- **Dependency Order**: `database.py` and `state_manager.py` before `crawler.py`. `crawler.py` before `main.py`.
- Mark tasks that can be done in parallel with `[P]`.

**Estimated Output**: 15-20 numbered, ordered tasks in `tasks.md`.

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*No constitutional violations were identified that require justification.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A       | N/A        | N/A                                 |

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution v1.1.0 - See `.specify/memory/constitution.md`*