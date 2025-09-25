"""Database initialization.

This module provides DDL scripts and database structure creation.
"""
import logging

from .connection import DatabaseConnection

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """資料庫初始化類別."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def create_tables(self) -> None:
        """建立所有資料表."""
        await self._create_articles_table()
        await self._create_crawl_states_table()
        await self._create_configs_table()
        await self._create_triggers()
        await self._create_indexes()

        logger.info("所有資料表建立完成")

    async def _create_articles_table(self) -> None:
        """建立 articles 表格."""
        ddl = """
        CREATE TABLE IF NOT EXISTS articles (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            author VARCHAR(50) NOT NULL,
            board VARCHAR(50) NOT NULL,
            url VARCHAR(500) NOT NULL UNIQUE,
            content TEXT,
            publish_date TIMESTAMP NOT NULL,
            crawl_date TIMESTAMP NOT NULL DEFAULT NOW(),
            category VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """

        await self.db.execute(ddl)
        logger.info("建立 articles 表格")

    async def _create_crawl_states_table(self) -> None:
        """建立 crawl_states 表格."""
        # 先建立 enum type
        enum_ddl = """
        DO $$ BEGIN
            CREATE TYPE crawl_status AS ENUM ('idle', 'crawling', 'paused', 'error', 'completed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """

        await self.db.execute(enum_ddl)

        # 建立表格
        table_ddl = """
        CREATE TABLE IF NOT EXISTS crawl_states (
            id SERIAL PRIMARY KEY,
            board VARCHAR(50) NOT NULL UNIQUE,
            last_crawl_time TIMESTAMP,
            last_page_crawled INTEGER DEFAULT 1,
            processed_urls JSONB DEFAULT '[]'::JSONB,
            failed_urls JSONB DEFAULT '[]'::JSONB,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            status crawl_status DEFAULT 'idle',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """

        await self.db.execute(table_ddl)
        logger.info("建立 crawl_states 表格")

    async def _create_configs_table(self) -> None:
        """建立 configs 表格."""
        ddl = """
        CREATE TABLE IF NOT EXISTS configs (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL,
            description VARCHAR(200),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """

        await self.db.execute(ddl)
        logger.info("建立 configs 表格")

    async def _create_triggers(self) -> None:
        """建立觸發器."""
        # 建立更新 updated_at 的函式
        function_ddl = """
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """

        await self.db.execute(function_ddl)

        # 為每個表格建立觸發器
        tables = ["articles", "crawl_states", "configs"]

        for table in tables:
            trigger_ddl = f"""
            DROP TRIGGER IF EXISTS {table}_updated_at ON {table};
            CREATE TRIGGER {table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at();
            """

            await self.db.execute(trigger_ddl)

        logger.info("建立 updated_at 觸發器")

    async def _create_indexes(self) -> None:
        """建立索引."""
        indexes = [
            # Articles 表格索引
            "CREATE INDEX IF NOT EXISTS idx_articles_board_date ON articles(board, publish_date);",
            "CREATE INDEX IF NOT EXISTS idx_articles_author ON articles(author);",
            "CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);",
            "CREATE INDEX IF NOT EXISTS idx_articles_crawl_date ON articles(crawl_date);",
            # CrawlStates 表格索引
            "CREATE INDEX IF NOT EXISTS idx_crawl_states_status ON crawl_states(status);",
            "CREATE INDEX IF NOT EXISTS idx_crawl_states_last_crawl ON crawl_states(last_crawl_time);",
            "CREATE INDEX IF NOT EXISTS idx_crawl_states_processed_urls USING GIN (processed_urls);",
            "CREATE INDEX IF NOT EXISTS idx_crawl_states_failed_urls USING GIN (failed_urls);",
        ]

        for index_ddl in indexes:
            await self.db.execute(index_ddl)

        logger.info("建立所有索引")

    async def drop_tables(self) -> None:
        """刪除所有資料表（用於測試或重置）."""
        tables = ["articles", "crawl_states", "configs"]

        for table in tables:
            await self.db.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

        # 刪除 enum type
        await self.db.execute("DROP TYPE IF EXISTS crawl_status;")

        # 刪除函式
        await self.db.execute("DROP FUNCTION IF EXISTS update_updated_at();")

        logger.warning("所有資料表已刪除")

    async def reset_database(self) -> None:
        """重置資料庫（刪除並重建所有表格）."""
        await self.drop_tables()
        await self.create_tables()
        logger.info("資料庫重置完成")

    async def insert_default_data(self) -> None:
        """插入預設資料."""
        await self._insert_default_configs()

    async def _insert_default_configs(self) -> None:
        """插入預設配置."""
        from ..database.config_repository import ConfigRepository

        config_repo = ConfigRepository(self.db)
        await config_repo.initialize_default_configs()

    async def check_table_exists(self, table_name: str) -> bool:
        """檢查表格是否存在."""
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = $1
        );
        """

        return await self.db.fetchval(query, table_name)

    async def get_table_info(self) -> dict:
        """取得資料表資訊."""
        tables = ["articles", "crawl_states", "configs"]
        info = {}

        for table in tables:
            exists = await self.check_table_exists(table)

            if exists:
                count_query = f"SELECT COUNT(*) FROM {table};"
                count = await self.db.fetchval(count_query)

                size_query = f"""
                SELECT pg_size_pretty(pg_total_relation_size('{table}'));
                """
                size = await self.db.fetchval(size_query)

                info[table] = {
                    "exists": True,
                    "row_count": count,
                    "size": size,
                }
            else:
                info[table] = {
                    "exists": False,
                    "row_count": 0,
                    "size": "0 bytes",
                }

        return info

    async def validate_schema(self) -> list[str]:
        """驗證資料庫架構."""
        errors = []

        # 檢查必要的表格
        required_tables = ["articles", "crawl_states", "configs"]

        for table in required_tables:
            exists = await self.check_table_exists(table)
            if not exists:
                errors.append(f"缺少必要的表格: {table}")

        # 檢查 enum type
        enum_query = """
        SELECT EXISTS (
            SELECT FROM pg_type
            WHERE typname = 'crawl_status'
        );
        """

        enum_exists = await self.db.fetchval(enum_query)
        if not enum_exists:
            errors.append("缺少 crawl_status enum 類型")

        # 檢查觸發器函式
        function_query = """
        SELECT EXISTS (
            SELECT FROM pg_proc
            WHERE proname = 'update_updated_at'
        );
        """

        function_exists = await self.db.fetchval(function_query)
        if not function_exists:
            errors.append("缺少 update_updated_at 函式")

        if not errors:
            logger.info("資料庫架構驗證通過")
        else:
            logger.error(f"資料庫架構驗證失敗: {errors}")

        return errors

    async def get_database_version(self) -> str:
        """取得資料庫版本."""
        return await self.db.fetchval("SELECT version();")

    async def get_database_stats(self) -> dict:
        """取得資料庫統計資訊."""
        stats = {
            "version": await self.get_database_version(),
            "tables": await self.get_table_info(),
            "connection_info": await self.db.get_connection_info(),
        }

        return stats
