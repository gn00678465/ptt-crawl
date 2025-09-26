# Phase 0: Research & Technical Decisions

## 1. Firecrawl Deployment Strategy

- **Requirement**: The system must support both self-hosted and cloud-based Firecrawl services.
- **Decision**: The Firecrawl client will be configured via environment variables. Users can provide their `FIRECRAWL_API_URL` for a self-hosted instance or use the default cloud URL. An API key (`FIRECRAWL_API_KEY`) will also be required.
- **Rationale**: This approach provides flexibility for users. A developer can use a local instance for testing, while a production deployment might use the more robust cloud service. This aligns with the extensibility requirement.
- **Alternatives Considered**:
  - **Hardcoding URLs**: Inflexible and requires code changes to switch between environments.
  - **CLI arguments**: Less secure for API keys and more cumbersome for users than a `.env` file.

## 2. Command-Line Interface (CLI)

- **Requirement**: The project requires a CLI for user interaction. The user specified `typer`.
- **Decision**: Use `typer` to build the CLI application.
- **Rationale**: `typer` is a modern, easy-to-use library for creating CLIs with automatic help generation and type validation, which aligns with the project's need for a robust and user-friendly interface. It was explicitly requested.
- **Alternatives Considered**:
  - **`argparse`**: Built-in but more verbose and less intuitive than `typer`.
  - **`click`**: Another excellent choice, but `typer` is built on top of it and offers even more convenience.

## 3. Package & Environment Management

- **Requirement**: The constitution mandates `uv` for package and virtual environment management.
- **Decision**: The project will use `uv` for all dependency management. A `requirements.txt` file will list dependencies, and setup instructions will use `uv venv` and `uv pip install`.
- **Rationale**: This adheres to the constitutional requirement and leverages `uv`'s high performance for dependency resolution and installation.
- **Alternatives Considered**: None, as this is a constitutional mandate.

## 4. Environment Variable Management

- **Requirement**: Configuration, such as API keys and database credentials, should be managed via `.env` files.
- **Decision**: Use the `python-dotenv` library to load environment variables from a `.env` file into a centralized `config.py` module.
- **Rationale**: This is a standard, secure practice in Python applications. It separates configuration from code, making the application portable and preventing sensitive data from being committed to source control.
- **Alternatives Considered**:
  - **Manual environment variable setting**: Error-prone and not portable across different systems.
  - **YAML/JSON config files**: A valid alternative, but `.env` is simpler and more conventional for this type of application.

## 5. PostgreSQL Database Integration

- **Requirement**: Store crawled articles in a PostgreSQL database.
- **Decision**: Use the `psycopg2-binary` library for synchronous database operations. Table names will be dynamically generated based on the PTT board name to meet the storage requirement.
- **Rationale**: `psycopg2` is the most widely used and mature adapter for PostgreSQL in Python. Dynamic table naming directly addresses the user's requirement to segregate data by board.
- **Alternatives Considered**:
  - **`asyncpg`**: A high-performance asynchronous driver. While powerful, it adds complexity (async/await) that is not necessary for the initial CLI version of the tool. It can be considered for a future GUI or web service version.
  - **ORM (e.g., SQLAlchemy)**: Adds a layer of abstraction that increases complexity. For the defined scope of direct data insertion, a simpler, direct SQL approach is more efficient and easier to maintain.

## 6. State Persistence Mechanism

- **Requirement**: The constitution requires crawl state to be persisted in a JSON file for incremental crawling and recovery.
- **Decision**: A JSON file named `crawl_state.json` will be used. It will store a dictionary where keys are board names. Each board will have an associated object containing the timestamp and URL of the last successfully crawled article.
- **Rationale**: This structure directly supports the incremental crawling principle. On startup, the crawler will read this file to know where to resume for each board. The file will be updated atomically after each successful batch of articles is saved.
- **Alternatives Considered**:
  - **SQLite**: A lightweight database file. While robust, it's overkill for storing simple key-value state and violates the "JSON file" constitutional requirement.
  - **In-memory state**: Violates the persistence requirement and would lead to re-crawling on every run.
