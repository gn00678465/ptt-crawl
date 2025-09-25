"""Complete Crawl Workflow Integration Tests

These tests verify the complete crawl workflow from PTT page to database storage.
They MUST FAIL initially (no implementation exists yet).
"""
import asyncio

import pytest

from src.models.crawl_state import CrawlState, CrawlStatus
from src.services.crawl_service import CrawlService


class TestCrawlWorkflowIntegration:
    """Test complete crawl workflow integration."""

    @pytest.fixture()
    def mock_database(self):
        """Mock database for integration testing."""
        # This will fail until database integration is implemented
        pytest.fail("Database integration not implemented yet")

    @pytest.fixture()
    def mock_firecrawl_service(self):
        """Mock Firecrawl service for testing."""
        # This will fail until Firecrawl service is implemented
        pytest.fail("Firecrawl service not implemented yet")

    @pytest.fixture()
    def mock_redis_client(self):
        """Mock Redis client for testing."""
        # This will fail until Redis integration is implemented
        pytest.fail("Redis integration not implemented yet")

    @pytest.fixture()
    def crawl_service(
        self, mock_database, mock_firecrawl_service, mock_redis_client
    ) -> CrawlService:
        """Crawl service instance for testing."""
        return CrawlService(
            database=mock_database,
            firecrawl_service=mock_firecrawl_service,
            redis_client=mock_redis_client,
        )

    @pytest.fixture()
    def sample_crawl_config(self):
        """Sample crawl configuration."""
        return {
            "board": "Stock",
            "category": "心得",
            "pages": 3,
            "incremental": True,
            "force": False,
        }


class TestFullCrawlWorkflow:
    """Test full crawl workflow scenarios."""

    @pytest.mark.asyncio()
    async def test_complete_crawl_workflow_new_board(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test complete crawl workflow for a new board."""
        # This is the main integration test
        result = await crawl_service.crawl_board(**sample_crawl_config)

        # Verify the workflow completed successfully
        assert result["status"] == "success"
        assert result["board"] == "Stock"
        assert result["pages_crawled"] > 0
        assert result["articles_found"] >= 0
        assert "execution_time" in result

    @pytest.mark.asyncio()
    async def test_crawl_workflow_with_existing_state(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test crawl workflow when crawl state already exists."""
        # First crawl to establish state
        await crawl_service.crawl_board(**sample_crawl_config)

        # Second crawl should use incremental mode
        result = await crawl_service.crawl_board(**sample_crawl_config)

        assert result["status"] == "success"
        # Should indicate incremental crawl was performed
        assert "incremental" in str(result).lower()

    @pytest.mark.asyncio()
    async def test_crawl_workflow_force_mode(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test crawl workflow in force mode (ignore existing state)."""
        config = sample_crawl_config.copy()
        config["force"] = True

        result = await crawl_service.crawl_board(**config)

        assert result["status"] == "success"
        # Should indicate force mode was used

    @pytest.mark.asyncio()
    async def test_crawl_workflow_category_filtering(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test crawl workflow with category filtering."""
        # Test different categories
        categories = ["心得", "標的", "請益"]

        for category in categories:
            config = sample_crawl_config.copy()
            config["category"] = category

            result = await crawl_service.crawl_board(**config)

            assert result["status"] == "success"
            assert result["category"] == category


class TestCrawlErrorHandling:
    """Test crawl workflow error handling."""

    @pytest.mark.asyncio()
    async def test_crawl_network_error_recovery(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test crawl workflow recovery from network errors."""
        # Simulate network error during crawl
        config = sample_crawl_config.copy()
        config["simulate_network_error"] = True

        result = await crawl_service.crawl_board(**config)

        # Should handle error gracefully and update state
        assert result["status"] in ["error", "partial_success"]
        assert "error_message" in result

    @pytest.mark.asyncio()
    async def test_crawl_database_error_recovery(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test crawl workflow recovery from database errors."""
        # Simulate database error during crawl
        config = sample_crawl_config.copy()
        config["simulate_db_error"] = True

        result = await crawl_service.crawl_board(**config)

        # Should handle error gracefully
        assert result["status"] == "error"
        assert "database" in result["error_message"].lower()

    @pytest.mark.asyncio()
    async def test_crawl_firecrawl_api_error_recovery(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test crawl workflow recovery from Firecrawl API errors."""
        # Simulate Firecrawl API error
        config = sample_crawl_config.copy()
        config["simulate_firecrawl_error"] = True

        result = await crawl_service.crawl_board(**config)

        # Should handle API errors with retry mechanism
        assert result["status"] in ["error", "partial_success"]
        assert "retry" in str(result).lower()

    @pytest.mark.asyncio()
    async def test_crawl_partial_failure_handling(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test crawl workflow handling of partial failures."""
        # Simulate scenario where some articles fail to crawl
        config = sample_crawl_config.copy()
        config["simulate_partial_failure"] = True

        result = await crawl_service.crawl_board(**config)

        # Should report partial success
        assert result["status"] == "partial_success"
        assert result["articles_found"] > 0
        assert result["articles_failed"] > 0


class TestStateManagement:
    """Test crawl state management during workflow."""

    @pytest.mark.asyncio()
    async def test_state_initialization(self, crawl_service: CrawlService, sample_crawl_config):
        """Test crawl state is properly initialized."""
        # Start crawl for new board
        await crawl_service.crawl_board(**sample_crawl_config)

        # Verify state was created
        state = await crawl_service.get_crawl_state("Stock")
        assert isinstance(state, CrawlState)
        assert state.board == "Stock"
        assert state.status in [CrawlStatus.COMPLETED, CrawlStatus.CRAWLING]

    @pytest.mark.asyncio()
    async def test_state_updates_during_crawl(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test crawl state is updated during crawl process."""
        # Monitor state changes during crawl
        crawl_task = asyncio.create_task(crawl_service.crawl_board(**sample_crawl_config))

        # Check intermediate states
        await asyncio.sleep(0.1)  # Let crawl start

        state = await crawl_service.get_crawl_state("Stock")
        if state:
            assert state.status in [CrawlStatus.CRAWLING, CrawlStatus.COMPLETED]

        await crawl_task

    @pytest.mark.asyncio()
    async def test_state_persistence_redis_json(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test state persistence in both Redis and JSON backup."""
        result = await crawl_service.crawl_board(**sample_crawl_config)

        # Verify state exists in Redis
        redis_state = await crawl_service.get_redis_state("Stock")
        assert redis_state is not None

        # Verify state exists in JSON backup
        json_state = await crawl_service.get_json_state("Stock")
        assert json_state is not None

        # States should be consistent
        assert redis_state["board"] == json_state["board"]

    @pytest.mark.asyncio()
    async def test_state_recovery_from_json(self, crawl_service: CrawlService, sample_crawl_config):
        """Test state recovery from JSON when Redis is unavailable."""
        # First, create state
        await crawl_service.crawl_board(**sample_crawl_config)

        # Simulate Redis failure
        await crawl_service.simulate_redis_failure()

        # Should recover state from JSON
        state = await crawl_service.get_crawl_state("Stock")
        assert isinstance(state, CrawlState)
        assert state.board == "Stock"


class TestDataIntegrity:
    """Test data integrity during crawl workflow."""

    @pytest.mark.asyncio()
    async def test_no_duplicate_articles(self, crawl_service: CrawlService, sample_crawl_config):
        """Test that duplicate articles are not created."""
        # Run same crawl twice
        result1 = await crawl_service.crawl_board(**sample_crawl_config)
        result2 = await crawl_service.crawl_board(**sample_crawl_config)

        # Second crawl should find fewer new articles
        assert result2["articles_new"] <= result1["articles_new"]

    @pytest.mark.asyncio()
    async def test_atomic_operations(self, crawl_service: CrawlService, sample_crawl_config):
        """Test that crawl operations are atomic."""
        # Simulate interruption during crawl
        config = sample_crawl_config.copy()
        config["simulate_interruption"] = True

        try:
            await crawl_service.crawl_board(**config)
        except Exception:
            pass  # Expected interruption

        # Database should be in consistent state
        # No partial articles should exist
        articles = await crawl_service.get_articles_by_board("Stock")
        for article in articles:
            assert article.url  # All articles should have URLs
            assert article.title  # All articles should have titles

    @pytest.mark.asyncio()
    async def test_transaction_rollback_on_error(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test transaction rollback when errors occur."""
        # Get initial article count
        initial_count = await crawl_service.count_articles("Stock")

        # Simulate error that should trigger rollback
        config = sample_crawl_config.copy()
        config["simulate_transaction_error"] = True

        try:
            await crawl_service.crawl_board(**config)
        except Exception:
            pass  # Expected error

        # Article count should be unchanged
        final_count = await crawl_service.count_articles("Stock")
        assert final_count == initial_count


class TestPerformanceAndLimits:
    """Test performance and rate limiting during crawl."""

    @pytest.mark.asyncio()
    async def test_rate_limiting_compliance(self, crawl_service: CrawlService, sample_crawl_config):
        """Test that rate limiting is properly enforced."""
        config = sample_crawl_config.copy()
        config["pages"] = 5  # More pages to test rate limiting

        start_time = asyncio.get_event_loop().time()
        result = await crawl_service.crawl_board(**config)
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should take reasonable time due to rate limiting
        expected_min_time = config["pages"] * 1.5  # Based on rate limit config
        assert elapsed >= expected_min_time * 0.8  # Some tolerance

    @pytest.mark.asyncio()
    async def test_memory_usage_stability(self, crawl_service: CrawlService, sample_crawl_config):
        """Test that memory usage remains stable during large crawls."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Run large crawl
        config = sample_crawl_config.copy()
        config["pages"] = 10

        await crawl_service.crawl_board(**config)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for test)
        assert memory_increase < 100 * 1024 * 1024

    @pytest.mark.asyncio()
    async def test_concurrent_crawl_prevention(
        self, crawl_service: CrawlService, sample_crawl_config
    ):
        """Test that concurrent crawls of same board are prevented."""
        # Start two crawls simultaneously
        task1 = asyncio.create_task(crawl_service.crawl_board(**sample_crawl_config))
        task2 = asyncio.create_task(crawl_service.crawl_board(**sample_crawl_config))

        results = await asyncio.gather(task1, task2, return_exceptions=True)

        # One should succeed, one should be rejected or queued
        success_count = sum(
            1 for r in results if isinstance(r, dict) and r.get("status") == "success"
        )
        assert success_count <= 1  # At most one should succeed simultaneously
