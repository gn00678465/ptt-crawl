"""Database Interface Contract Tests

These tests verify the database operations match the specifications.
They MUST FAIL initially (no implementation exists yet).
"""
from datetime import datetime

import pytest

from src.database.article_repository import ArticleRepository
from src.database.config_repository import ConfigRepository
from src.database.crawl_state_repository import CrawlStateRepository
from src.models.article import Article
from src.models.crawl_state import CrawlState, CrawlStatus


class TestDatabaseContracts:
    """Test database operation contracts."""

    @pytest.fixture()
    def mock_db_pool(self):
        """Mock database connection pool."""
        # This will fail until database connection is implemented
        pytest.fail("Database connection not implemented yet")

    @pytest.fixture()
    def article_repo(self, mock_db_pool) -> ArticleRepository:
        """Article repository instance."""
        return ArticleRepository(mock_db_pool)

    @pytest.fixture()
    def crawl_state_repo(self, mock_db_pool) -> CrawlStateRepository:
        """CrawlState repository instance."""
        return CrawlStateRepository(mock_db_pool)

    @pytest.fixture()
    def config_repo(self, mock_db_pool) -> ConfigRepository:
        """Config repository instance."""
        return ConfigRepository(mock_db_pool)

    @pytest.fixture()
    def sample_article(self) -> Article:
        """Sample article for testing."""
        return Article(
            id=0,
            title="[心得] 測試文章標題",
            author="test_user",
            board="Stock",
            url="https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
            content="# 測試文章內容\n\n這是測試內容。",
            publish_date=datetime.now(),
            crawl_date=datetime.now(),
            category="心得",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @pytest.fixture()
    def sample_crawl_state(self) -> CrawlState:
        """Sample crawl state for testing."""
        return CrawlState(
            id=0,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=1,
            processed_urls=["https://example.com/1", "https://example.com/2"],
            failed_urls=[],
            retry_count=0,
            max_retries=3,
            status=CrawlStatus.IDLE,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


class TestArticleRepository:
    """Test Article repository operations."""

    @pytest.mark.asyncio()
    async def test_insert_article(self, article_repo: ArticleRepository, sample_article: Article):
        """Test inserting a new article."""
        # This should fail - no implementation yet
        article_id = await article_repo.insert_article(sample_article)
        assert isinstance(article_id, int)
        assert article_id > 0

    @pytest.mark.asyncio()
    async def test_article_exists(self, article_repo: ArticleRepository):
        """Test checking if article exists by URL."""
        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        exists = await article_repo.article_exists(url)
        assert isinstance(exists, bool)

    @pytest.mark.asyncio()
    async def test_get_articles_by_board(self, article_repo: ArticleRepository):
        """Test getting articles by board name."""
        articles = await article_repo.get_articles_by_board("Stock", limit=10)
        assert isinstance(articles, list)

    @pytest.mark.asyncio()
    async def test_get_articles_by_board_with_category(self, article_repo: ArticleRepository):
        """Test getting articles by board and category."""
        articles = await article_repo.get_articles_by_board("Stock", category="心得", limit=5)
        assert isinstance(articles, list)

    @pytest.mark.asyncio()
    async def test_update_article_content(self, article_repo: ArticleRepository):
        """Test updating article content."""
        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        content = "# Updated content\n\nThis is updated content."
        success = await article_repo.update_article_content(url, content)
        assert isinstance(success, bool)

    @pytest.mark.asyncio()
    async def test_batch_insert_articles(self, article_repo: ArticleRepository):
        """Test batch inserting multiple articles."""
        articles = [
            Article(
                id=0,
                title=f"[心得] 測試文章 {i}",
                author=f"user_{i}",
                board="Stock",
                url=f"https://www.ptt.cc/bbs/Stock/M.{i}.A.123.html",
                content=f"測試內容 {i}",
                publish_date=datetime.now(),
                crawl_date=datetime.now(),
                category="心得",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for i in range(3)
        ]
        ids = await article_repo.batch_insert_articles(articles)
        assert isinstance(ids, list)
        assert len(ids) == len(articles)


class TestCrawlStateRepository:
    """Test CrawlState repository operations."""

    @pytest.mark.asyncio()
    async def test_init_crawl_state(self, crawl_state_repo: CrawlStateRepository):
        """Test initializing crawl state for a board."""
        await crawl_state_repo.init_crawl_state("Stock")
        # Should not raise exception

    @pytest.mark.asyncio()
    async def test_get_crawl_state(self, crawl_state_repo: CrawlStateRepository) -> None:
        """Test getting crawl state for a board."""
        state = await crawl_state_repo.get_crawl_state("Stock")
        assert state is None or isinstance(state, CrawlState)

    @pytest.mark.asyncio()
    async def test_update_crawl_state(self, crawl_state_repo: CrawlStateRepository):
        """Test updating crawl state."""
        await crawl_state_repo.update_crawl_state(
            board="Stock", status=CrawlStatus.CRAWLING, last_page_crawled=5
        )
        # Should not raise exception

    @pytest.mark.asyncio()
    async def test_add_processed_url(self, crawl_state_repo: CrawlStateRepository):
        """Test adding a processed URL."""
        await crawl_state_repo.add_processed_url(
            "Stock", "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        )
        # Should not raise exception

    @pytest.mark.asyncio()
    async def test_add_failed_url(self, crawl_state_repo: CrawlStateRepository):
        """Test adding a failed URL."""
        await crawl_state_repo.add_failed_url(
            "Stock", "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        )
        # Should not raise exception

    @pytest.mark.asyncio()
    async def test_increment_retry_count(self, crawl_state_repo: CrawlStateRepository):
        """Test incrementing retry count."""
        await crawl_state_repo.increment_retry_count("Stock")
        # Should not raise exception

    @pytest.mark.asyncio()
    async def test_reset_retry_count(self, crawl_state_repo: CrawlStateRepository):
        """Test resetting retry count."""
        await crawl_state_repo.reset_retry_count("Stock")
        # Should not raise exception


class TestConfigRepository:
    """Test Config repository operations."""

    @pytest.mark.asyncio()
    async def test_get_config(self, config_repo: ConfigRepository):
        """Test getting config value."""
        value = await config_repo.get_config("crawl.rate_limit")
        assert value is None or isinstance(value, str)

    @pytest.mark.asyncio()
    async def test_get_config_with_default(self, config_repo: ConfigRepository):
        """Test getting config value with default."""
        value = await config_repo.get_config("nonexistent.key", "default_value")
        assert isinstance(value, str)

    @pytest.mark.asyncio()
    async def test_set_config(self, config_repo: ConfigRepository):
        """Test setting config value."""
        await config_repo.set_config("test.key", "test_value", "Test description")
        # Should not raise exception

    @pytest.mark.asyncio()
    async def test_get_all_configs(self, config_repo: ConfigRepository):
        """Test getting all config values."""
        configs = await config_repo.get_all_configs()
        assert isinstance(configs, dict)

    @pytest.mark.asyncio()
    async def test_delete_config(self, config_repo: ConfigRepository):
        """Test deleting config value."""
        success = await config_repo.delete_config("test.key")
        assert isinstance(success, bool)


class TestDatabaseTransactions:
    """Test database transaction operations."""

    @pytest.mark.asyncio()
    async def test_atomic_crawl_progress_update(
        self,
        article_repo: ArticleRepository,
        crawl_state_repo: CrawlStateRepository,
        sample_article: Article,
    ):
        """Test atomic update of crawl progress with articles."""
        # This tests the transaction requirement from the contract
        processed_urls = ["https://example.com/1", "https://example.com/2"]
        new_articles = [sample_article]

        # Should be atomic - either all succeed or all fail
        await article_repo.update_crawl_progress("Stock", processed_urls, new_articles)
        # Should not raise exception if transaction is successful
