# Quickstart Guide: PTT Crawler

This guide provides the steps to set up and run the PTT Crawler CLI tool.

## 1. Prerequisites

- Python 3.11 or higher.
- `uv` package manager. If you don't have it, install it with:
  ```bash
  pip install uv
  ```
- Access to a PostgreSQL database.

## 2. Setup

### Step 1: Clone the Repository

```bash
# Clone the project repository
git clone <repository_url>
cd ptt-crawl
```

### Step 2: Create and Activate Virtual Environment

Use `uv` to create and activate a virtual environment.

```bash
# Create the virtual environment
uv venv

# Activate the environment
# On Windows (PowerShell/CMD)
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

### Step 3: Install Dependencies

Install the required Python packages using `uv`.

```bash
# Create a requirements.txt file with the following content:
# typer
# python-dotenv
# firecrawl-py
# psycopg2-binary

uv pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root by copying the example file.

```bash
cp .env.firecrawl.example .env
```

Now, edit the `.env` file with your specific configuration:

```dotenv
# .env

# Firecrawl Configuration
# Use the cloud service or your self-hosted instance URL
FIRECRAWL_API_URL="https://api.firecrawl.dev"
FIRECRAWL_API_KEY="your_firecrawl_api_key"

# PostgreSQL Database Configuration
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="your_db_user"
DB_PASSWORD="your_db_password"
DB_NAME="your_db_name"

# Crawler Configuration
# Max pages to crawl for the first run on a new board
MAX_CRAWL_PAGES=5
```

## 3. Usage

The primary interface is the command-line tool.

### Example: Crawl the 'Stock' board

This command will crawl the latest articles from the PTT 'Stock' board.

```bash
python -m src.main crawl Stock
```

### Example: Crawl with a Category Filter

This command will crawl only articles with the category '[新聞]' from the 'Stock' board.

```bash
python -m src.main crawl Stock --category "[新聞]"
```

## 4. Verification

After running the crawler, you can verify the results by connecting to your PostgreSQL database.

```sql
-- Connect to your database and run:
SELECT COUNT(*) FROM stock;

-- View the latest crawled articles:
SELECT title, author, publish_date FROM stock ORDER BY publish_date DESC LIMIT 10;
```
