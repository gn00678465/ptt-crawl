"""Incremental Crawl Integration Tests

These tests verify incremental crawling and state management functionality.
They MUST FAIL initially (no implementation exists yet).
"""
import asyncio
from datetime import datetime, timedelta

import pytest

from src.models.article import Article
from src.models.crawl_state import CrawlState, CrawlStatus
from src.services.crawl_service import CrawlService
from src.services.state_service import StateService


class TestIncrementalCrawlIntegration:
    """Test incremental crawl integration."""

    @pytest.fixture()
    def crawl_service(self):
        """Crawl service instance for testing."""
        # This will fail until CrawlService is implemented
        pytest.fail("CrawlService not implemented yet")

    @pytest.fixture()
    def state_service(self):
        """State service instance for testing."""
        # This will fail until StateService is implemented
        pytest.fail("StateService not implemented yet")

    @pytest.fixture()
    def sample_board(self) -> str:
        """Sample board name for testing."""
        return "Stock"

    @pytest.fixture()
    def existing_articles(self) -> list[Article]:
        """Sample existing articles in database."""
        return [
            Article(
                id=i,
                title=f"[心得] 測試文章 {i}",
                author=f"user_{i}",
                board="Stock",
                url=f"https://www.ptt.cc/bbs/Stock/M.{i}.A.123.html",
                content=f"測試內容 {i}",
                publish_date=datetime.now() - timedelta(days=i),
                crawl_date=datetime.now() - timedelta(days=i),
                category="心得",
                created_at=datetime.now() - timedelta(days=i),
                updated_at=datetime.now() - timedelta(days=i),
            )
            for i in range(1, 6)
        ]


class TestIncrementalCrawlLogic:
    """Test incremental crawl logic."""

    @pytest.mark.asyncio()
    async def test_first_time_crawl_creates_state(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test that first-time crawl creates initial state."""
        # No existing state
        state = await crawl_service.get_crawl_state(sample_board)
        assert state is None

        # Run first crawl
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        # Should create state
        state = await crawl_service.get_crawl_state(sample_board)
        assert isinstance(state, CrawlState)
        assert state.board == sample_board
        assert state.status == CrawlStatus.COMPLETED
        assert len(state.processed_urls) > 0

    @pytest.mark.asyncio()
    async def test_subsequent_crawl_uses_existing_state(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test that subsequent crawls use existing state."""
        # First crawl
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        first_state = await crawl_service.get_crawl_state(sample_board)
        first_processed_count = len(first_state.processed_urls)

        # Second crawl
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        second_state = await crawl_service.get_crawl_state(sample_board)
        second_processed_count = len(second_state.processed_urls)

        # Should have processed additional URLs
        assert second_processed_count >= first_processed_count
        assert second_state.last_crawl_time > first_state.last_crawl_time

    @pytest.mark.asyncio()
    async def test_incremental_crawl_skips_processed_urls(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test that incremental crawl skips already processed URLs."""
        # First crawl to establish baseline
        result1 = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=3, incremental=True
        )

        # Second crawl immediately after (same content should be available)
        result2 = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=3, incremental=True
        )

        # Second crawl should find fewer new articles
        assert result2["articles_new"] < result1["articles_new"]
        assert result2["articles_skipped"] > 0

    @pytest.mark.asyncio()
    async def test_incremental_crawl_detects_new_content(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test that incremental crawl detects new content."""
        # Initial crawl
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        # Simulate new content appearing (mock new articles on PTT)
        await crawl_service.simulate_new_ptt_content(sample_board, count=3)

        # Incremental crawl should detect new content
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        assert result["articles_new"] >= 3
        assert result["status"] == "success"

    @pytest.mark.asyncio()
    async def test_incremental_crawl_updates_existing_content(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test that incremental crawl can update existing articles."""
        # Initial crawl
        result1 = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        # Simulate content updates (articles got more replies/edits)
        await crawl_service.simulate_content_updates(sample_board, count=2)

        # Incremental crawl should detect and update changed content
        result2 = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        assert result2["articles_updated"] >= 2
        assert result2["status"] == "success"


class TestStateManagementDuringIncremental:
    """Test state management during incremental crawls."""

    @pytest.mark.asyncio()
    async def test_state_updated_progressively(
        self, crawl_service: CrawlService, state_service: StateService, sample_board: str
    ):
        """Test that state is updated progressively during crawl."""
        # Start incremental crawl
        crawl_task = asyncio.create_task(
            crawl_service.crawl_board(board=sample_board, pages=5, incremental=True)
        )

        # Monitor state changes during crawl
        previous_processed_count = 0
        state_updates = []

        for _ in range(3):  # Check 3 times during crawl
            await asyncio.sleep(1)  # Let some processing happen

            current_state = await state_service.get_state(sample_board)
            if current_state:
                current_processed_count = len(current_state.processed_urls)
                if current_processed_count > previous_processed_count:
                    state_updates.append(current_processed_count)
                    previous_processed_count = current_processed_count

        await crawl_task

        # Should have seen progressive updates
        assert len(state_updates) > 0
        # Updates should be increasing
        assert all(state_updates[i] <= state_updates[i + 1] for i in range(len(state_updates) - 1))

    @pytest.mark.asyncio()
    async def test_state_persistence_during_incremental(
        self, crawl_service: CrawlService, state_service: StateService, sample_board: str
    ):
        """Test that state persists correctly during incremental crawl."""
        # Run incremental crawl
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=3, incremental=True
        )

        # Check both Redis and JSON state
        redis_state = await state_service.get_redis_state(sample_board)
        json_state = await state_service.get_json_state(sample_board)

        # Both should exist and be consistent
        assert redis_state is not None
        assert json_state is not None
        assert redis_state["board"] == json_state["board"]
        assert len(redis_state["processed_urls"]) == len(json_state["processed_urls"])

    @pytest.mark.asyncio()
    async def test_state_recovery_continues_incremental(
        self, crawl_service: CrawlService, state_service: StateService, sample_board: str
    ):
        """Test that state recovery allows incremental crawl to continue."""
        # Start crawl and let it establish state
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        # Simulate Redis failure and recovery
        await state_service.simulate_redis_failure()
        await state_service.recover_from_json(sample_board)

        # Continue incremental crawl should work
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        assert result["status"] == "success"
        # Should indicate it continued from previous state
        assert result["articles_skipped"] > 0

    @pytest.mark.asyncio()
    async def test_failed_urls_tracking(self, crawl_service: CrawlService, sample_board: str):
        """Test that failed URLs are tracked and can be retried."""
        # Simulate some URLs failing during crawl
        await crawl_service.simulate_url_failures(sample_board, failure_rate=0.3)

        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=3, incremental=True
        )

        # Check state includes failed URLs
        state = await crawl_service.get_crawl_state(sample_board)
        assert len(state.failed_urls) > 0
        assert result["articles_failed"] > 0

        # Retry crawl should attempt failed URLs again
        retry_result = await crawl_service.retry_failed_urls(sample_board)
        assert retry_result["urls_retried"] == len(state.failed_urls)


class TestIncrementalCrawlEdgeCases:
    """Test edge cases in incremental crawling."""

    @pytest.mark.asyncio()
    async def test_incremental_with_force_flag(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test incremental crawl behavior with force flag."""
        # First crawl
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        # Force crawl should ignore existing state
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True, force=True
        )

        assert result["status"] == "success"
        # Should not skip any articles when forced
        assert result.get("articles_skipped", 0) == 0

    @pytest.mark.asyncio()
    async def test_incremental_with_different_categories(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test incremental crawl with different category filters."""
        # Crawl with "心得" category
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        # Crawl with "標的" category should be independent
        result = await crawl_service.crawl_board(
            board=sample_board, category="標的", pages=2, incremental=True
        )

        assert result["status"] == "success"
        # Should find articles since it's a different category filter
        assert result["articles_found"] > 0

    @pytest.mark.asyncio()
    async def test_incremental_after_error_recovery(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test incremental crawl after error recovery."""
        # Start crawl that will encounter error
        try:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, incremental=True, simulate_error=True
            )
        except Exception:
            pass  # Expected error

        # Check state shows error
        state = await crawl_service.get_crawl_state(sample_board)
        assert state.status == CrawlStatus.ERROR
        assert state.error_message is not None

        # Recovery crawl should continue from last good state
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=3, incremental=True
        )

        assert result["status"] == "success"
        # Should have recovered and continued
        final_state = await crawl_service.get_crawl_state(sample_board)
        assert final_state.status == CrawlStatus.COMPLETED

    @pytest.mark.asyncio()
    async def test_incremental_with_pagination_boundaries(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test incremental crawl across pagination boundaries."""
        # First crawl - pages 1-3
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=3, incremental=True
        )

        # Second crawl - pages 1-5 (should efficiently skip already processed)
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=5, incremental=True
        )

        assert result["status"] == "success"
        # Should have processed only new pages (4-5)
        assert result["pages_crawled"] <= 2  # Only new pages

    @pytest.mark.asyncio()
    async def test_incremental_state_cleanup(
        self, crawl_service: CrawlService, state_service: StateService, sample_board: str
    ):
        """Test that incremental state is properly cleaned up when needed."""
        # Run multiple incremental crawls to build up state
        for i in range(3):
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=2, incremental=True
            )

        state = await crawl_service.get_crawl_state(sample_board)
        initial_url_count = len(state.processed_urls)

        # Trigger state cleanup (e.g., for very old URLs)
        await state_service.cleanup_old_state(sample_board, days_old=30)

        # State should still be functional but possibly cleaned
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, incremental=True
        )

        assert result["status"] == "success"


class TestIncrementalPerformance:
    """Test performance aspects of incremental crawling."""

    @pytest.mark.asyncio()
    async def test_incremental_faster_than_full_crawl(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test that incremental crawl is faster than full crawl."""
        # Full crawl timing
        start_time = asyncio.get_event_loop().time()
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=5, incremental=False
        )
        full_crawl_time = asyncio.get_event_loop().time() - start_time

        # Incremental crawl timing (should be faster since content exists)
        start_time = asyncio.get_event_loop().time()
        await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=5, incremental=True
        )
        incremental_crawl_time = asyncio.get_event_loop().time() - start_time

        # Incremental should be significantly faster
        assert incremental_crawl_time < full_crawl_time * 0.7

    @pytest.mark.asyncio()
    async def test_large_state_performance(self, crawl_service: CrawlService, sample_board: str):
        """Test performance with large state (many processed URLs)."""
        # Build up large state
        await crawl_service.simulate_large_state(sample_board, url_count=10000)

        # Incremental crawl should still perform well
        start_time = asyncio.get_event_loop().time()
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=3, incremental=True
        )
        elapsed_time = asyncio.get_event_loop().time() - start_time

        assert result["status"] == "success"
        # Should complete within reasonable time even with large state
        assert elapsed_time < 60  # Less than 1 minute

    @pytest.mark.asyncio()
    async def test_memory_efficiency_incremental(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test memory efficiency of incremental crawl."""
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Measure memory before
        initial_memory = process.memory_info().rss

        # Run multiple incremental crawls
        for i in range(5):
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, incremental=True
            )

        # Measure memory after
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be minimal for incremental crawls
        assert memory_increase < 50 * 1024 * 1024  # Less than 50MB increase
