# Feature Specification: PTT Crawler

**Feature Branch**: `001-ptt-crawler`
**Created**: 2025-09-26
**Status**: Draft
**Input**: User description: "建立一個爬蟲工具，能爬取 PTT 看板文章，依文章分類進行篩選並將文章儲存供分析，在初始階段僅提供 Command Line 介面操作，程式需具備可擴充性以利未來新增輸出格式或 GUI。"

## Clarifications

### Session 2025-09-26
- Q: What is the expected output format for the saved articles? → A: save in database
- Q: What type of database should be used for storing the articles? → A: PostgreSQL
- Q: By default, how many of the latest articles should the crawler retrieve from a board? → A: The first time it runs, the number of pages can be customized. Subsequent runs should crawl up to the last article crawled previously.
- Q: What specific data fields should be extracted from each article? → A: Category, Author, Title, Date, Content, URL
- Q: How should an article be uniquely identified in the database to prevent duplicate entries? → A: The article's URL should be the unique identifier.
- Q: Is there a maximum number of pages the user is allowed to specify for the initial crawl? → A: use environment variable(.env)

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a user, I want to crawl articles from a specific PTT board, filter them by category, and save them locally so that I can perform analysis on the content.

### Acceptance Scenarios
1. **Given** a valid PTT board name and a category, **When** I run the crawler, **Then** it should save the articles matching the category to a PostgreSQL database.
2. **Given** a valid PTT board name without a category, **When** I run the crawler, **Then** it should save all articles from the board to a PostgreSQL database.
3. **Given** an invalid PTT board name, **When** I run the crawler, **Then** it should display an error message.

### Edge Cases
- What happens when a PTT board is temporarily unavailable?
- How does the system handle articles with unusual formatting?
- What happens if the specified category does not exist on the board?

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The system MUST provide a command-line interface (CLI) for user interaction.
- **FR-002**: The system MUST allow users to specify a PTT board to crawl.
- **FR-003**: The system MUST allow users to optionally filter articles by their category.
- **FR-004**: The system MUST crawl the content of the articles from the specified board.
- **FR-005**: The system MUST save the crawled articles to a PostgreSQL database.
- **FR-006**: The system's design MUST be extensible to support new output formats in the future.
- **FR-007**: The system's design MUST be extensible to support a graphical user interface (GUI) in the future.
- **FR-008**: The system MUST handle errors gracefully, such as when a board is not found or is unavailable.
- **FR-009**: The system MUST extract the following fields for each article: Category, Author, Title, Date, Content, and URL.
- **FR-010**: For the initial crawl of a board, the user MUST be able to specify the number of pages to crawl.
- **FR-011**: For subsequent crawls of a board, the system MUST only retrieve articles newer than the last article previously crawled.
- **FR-012**: The system MUST use the article's URL as its unique identifier to prevent duplicate entries in the database.
- **FR-013**: The maximum number of pages for an initial crawl MUST be configurable via an environment variable.

### Key Entities *(include if feature involves data)*
- **Article**: Represents a single PTT article. Key attributes include:
    - Category
    - Author
    - Title
    - Date
    - Content
    - URL
- **Board**: Represents a PTT board. Key attributes include:
    - Name (e.g., 'Gossiping')
    - URL

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---