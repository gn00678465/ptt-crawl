"""Error Recovery Integration Tests

These tests verify error handling and recovery mechanisms.
They MUST FAIL initially (no implementation exists yet).
"""
import asyncio

import pytest

from src.lib.error_handler import CrawlError, ErrorHandler
from src.models.crawl_state import CrawlStatus
from src.services.crawl_service import CrawlService
from src.services.state_service import StateService


class TestErrorRecoveryIntegration:
    """Test error recovery integration."""

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
    def error_handler(self):
        """Error handler instance for testing."""
        # This will fail until ErrorHandler is implemented
        pytest.fail("ErrorHandler not implemented yet")

    @pytest.fixture()
    def sample_board(self) -> str:
        """Sample board name for testing."""
        return "Stock"


class TestNetworkErrorRecovery:
    """Test network error recovery mechanisms."""

    @pytest.mark.asyncio()
    async def test_timeout_error_recovery(self, crawl_service: CrawlService, sample_board: str):
        """Test recovery from network timeout errors."""
        # Simulate network timeout
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_timeout=True
            )

        assert "timeout" in str(exc_info.value).lower()

        # Check that state reflects the error
        state = await crawl_service.get_crawl_state(sample_board)
        assert state.status == CrawlStatus.ERROR
        assert "timeout" in state.error_message.lower()

        # Recovery crawl should succeed
        result = await crawl_service.crawl_board(board=sample_board, category="心得", pages=3)

        assert result["status"] == "success"
        # Should have recovered from error state
        recovered_state = await crawl_service.get_crawl_state(sample_board)
        assert recovered_state.status == CrawlStatus.COMPLETED

    @pytest.mark.asyncio()
    async def test_connection_error_recovery(self, crawl_service: CrawlService, sample_board: str):
        """Test recovery from connection errors."""
        # Simulate connection failure
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_connection_error=True
            )

        assert "connection" in str(exc_info.value).lower()

        # State should track the error
        state = await crawl_service.get_crawl_state(sample_board)
        assert state.status == CrawlStatus.ERROR
        assert state.retry_count > 0

        # Recovery with backoff
        await asyncio.sleep(2)  # Simulate backoff delay

        result = await crawl_service.crawl_board(board=sample_board, category="心得", pages=3)

        assert result["status"] == "success"

    @pytest.mark.asyncio()
    async def test_rate_limit_error_recovery(self, crawl_service: CrawlService, sample_board: str):
        """Test recovery from rate limit errors."""
        # Simulate rate limiting
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board,
                category="心得",
                pages=10,  # Many pages to trigger rate limit
                simulate_rate_limit=True,
            )

        assert "rate limit" in str(exc_info.value).lower()

        # Should automatically retry with proper delays
        result = await crawl_service.crawl_board_with_retry(
            board=sample_board, category="心得", pages=3
        )

        assert result["status"] == "success"
        # Should indicate rate limiting was handled
        assert "rate_limited" in result.get("warnings", [])

    @pytest.mark.asyncio()
    async def test_partial_network_failure(self, crawl_service: CrawlService, sample_board: str):
        """Test handling of partial network failures."""
        # Simulate scenario where some URLs fail, others succeed
        result = await crawl_service.crawl_board(
            board=sample_board,
            category="心得",
            pages=5,
            simulate_partial_failure=True,
            failure_rate=0.3,  # 30% failure rate
        )

        # Should report partial success
        assert result["status"] == "partial_success"
        assert result["articles_found"] > 0
        assert result["articles_failed"] > 0

        # Failed URLs should be tracked for retry
        state = await crawl_service.get_crawl_state(sample_board)
        assert len(state.failed_urls) > 0

        # Retry failed URLs
        retry_result = await crawl_service.retry_failed_urls(sample_board)
        assert retry_result["urls_retried"] > 0


class TestDatabaseErrorRecovery:
    """Test database error recovery mechanisms."""

    @pytest.mark.asyncio()
    async def test_database_connection_error_recovery(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test recovery from database connection errors."""
        # Simulate database connection failure
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_db_connection_error=True
            )

        assert "database" in str(exc_info.value).lower()

        # Should attempt to reconnect and retry
        await asyncio.sleep(1)  # Allow connection recovery

        result = await crawl_service.crawl_board(board=sample_board, category="心得", pages=3)

        assert result["status"] == "success"

    @pytest.mark.asyncio()
    async def test_transaction_error_recovery(self, crawl_service: CrawlService, sample_board: str):
        """Test recovery from transaction errors."""
        # Simulate transaction failure
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_transaction_error=True
            )

        assert "transaction" in str(exc_info.value).lower()

        # Database should be in consistent state (no partial data)
        articles = await crawl_service.get_articles_by_board(sample_board)
        # Should not have partial/corrupted articles
        for article in articles:
            assert article.title is not None
            assert article.url is not None

        # Retry should succeed
        result = await crawl_service.crawl_board(board=sample_board, category="心得", pages=3)

        assert result["status"] == "success"

    @pytest.mark.asyncio()
    async def test_disk_full_error_recovery(self, crawl_service: CrawlService, sample_board: str):
        """Test recovery from disk full errors."""
        # Simulate disk full scenario
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_disk_full=True
            )

        assert "disk" in str(exc_info.value).lower() or "space" in str(exc_info.value).lower()

        # Should gracefully handle and provide guidance
        error_guidance = await crawl_service.get_error_guidance(str(exc_info.value))
        assert "disk space" in error_guidance.lower()

    @pytest.mark.asyncio()
    async def test_constraint_violation_recovery(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test recovery from database constraint violations."""
        # First crawl to establish data
        await crawl_service.crawl_board(board=sample_board, category="心得", pages=2)

        # Simulate constraint violation (duplicate URL)
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=2, simulate_duplicate_url=True
        )

        # Should handle gracefully and skip duplicates
        assert result["status"] == "success"
        assert result.get("articles_skipped", 0) > 0


class TestRedisErrorRecovery:
    """Test Redis error recovery mechanisms."""

    @pytest.mark.asyncio()
    async def test_redis_connection_failure_recovery(
        self, crawl_service: CrawlService, state_service: StateService, sample_board: str
    ):
        """Test recovery when Redis connection fails."""
        # Start with Redis available
        await crawl_service.crawl_board(board=sample_board, category="心得", pages=2)

        # Simulate Redis failure
        await state_service.simulate_redis_failure()

        # Should fall back to JSON state management
        result = await crawl_service.crawl_board(board=sample_board, category="心得", pages=2)

        assert result["status"] == "success"
        # Should indicate fallback mode
        assert "json_fallback" in result.get("warnings", [])

        # When Redis recovers, should sync back
        await state_service.recover_redis_connection()
        await state_service.sync_redis_from_json(sample_board)

        # Verify sync worked
        redis_state = await state_service.get_redis_state(sample_board)
        json_state = await state_service.get_json_state(sample_board)
        assert redis_state["board"] == json_state["board"]

    @pytest.mark.asyncio()
    async def test_redis_data_corruption_recovery(
        self, crawl_service: CrawlService, state_service: StateService, sample_board: str
    ):
        """Test recovery from Redis data corruption."""
        # Establish normal state
        await crawl_service.crawl_board(board=sample_board, category="心得", pages=2)

        # Simulate Redis data corruption
        await state_service.simulate_redis_corruption(sample_board)

        # Should detect corruption and recover from JSON
        result = await crawl_service.crawl_board(board=sample_board, category="心得", pages=2)

        assert result["status"] == "success"
        # Should indicate recovery from JSON
        assert "recovered_from_json" in result.get("info", [])

    @pytest.mark.asyncio()
    async def test_json_file_corruption_recovery(
        self, crawl_service: CrawlService, state_service: StateService, sample_board: str
    ):
        """Test recovery from JSON file corruption."""
        # Establish state
        await crawl_service.crawl_board(board=sample_board, category="心得", pages=2)

        # Corrupt JSON file
        await state_service.simulate_json_corruption(sample_board)

        # Should rebuild from database or start fresh
        result = await crawl_service.crawl_board(board=sample_board, category="心得", pages=2)

        assert result["status"] == "success"
        # Should indicate state was rebuilt
        assert "state_rebuilt" in result.get("info", [])


class TestAPIErrorRecovery:
    """Test API error recovery mechanisms."""

    @pytest.mark.asyncio()
    async def test_firecrawl_api_key_error_recovery(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test recovery from API key errors."""
        # Simulate invalid API key
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_invalid_api_key=True
            )

        assert (
            "api key" in str(exc_info.value).lower()
            or "unauthorized" in str(exc_info.value).lower()
        )

        # Should provide clear guidance
        error_guidance = await crawl_service.get_error_guidance(str(exc_info.value))
        assert "api key" in error_guidance.lower()

    @pytest.mark.asyncio()
    async def test_firecrawl_quota_exceeded_recovery(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test recovery from API quota exceeded."""
        # Simulate quota exceeded
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=10, simulate_quota_exceeded=True
            )

        assert "quota" in str(exc_info.value).lower()

        # Should provide guidance and estimated recovery time
        error_guidance = await crawl_service.get_error_guidance(str(exc_info.value))
        assert "quota" in error_guidance.lower()
        assert "time" in error_guidance.lower()  # Should mention when quota resets

    @pytest.mark.asyncio()
    async def test_firecrawl_service_unavailable_recovery(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test recovery from Firecrawl service being unavailable."""
        # Simulate service unavailable
        with pytest.raises(CrawlError) as exc_info:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_service_unavailable=True
            )

        assert "service unavailable" in str(exc_info.value).lower() or "503" in str(exc_info.value)

        # Should retry with exponential backoff
        await asyncio.sleep(2)  # Simulate wait

        # Mock service recovery
        result = await crawl_service.crawl_board_with_retry(
            board=sample_board, category="心得", pages=3
        )

        assert result["status"] == "success"


class TestErrorStateConsistency:
    """Test error state consistency across components."""

    @pytest.mark.asyncio()
    async def test_error_state_consistency_database_redis(
        self, crawl_service: CrawlService, state_service: StateService, sample_board: str
    ):
        """Test that error states are consistent between database and Redis."""
        # Cause an error during crawl
        try:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_random_error=True
            )
        except CrawlError:
            pass  # Expected

        # Check state consistency
        db_state = await crawl_service.get_crawl_state(sample_board)
        redis_state = await state_service.get_redis_state(sample_board)
        json_state = await state_service.get_json_state(sample_board)

        # All should reflect the same error state
        assert db_state.status == CrawlStatus.ERROR
        assert redis_state["status"] == "error"
        assert json_state["status"] == "error"

        # Error messages should be consistent
        assert db_state.error_message == redis_state["error_message"]
        assert db_state.error_message == json_state["error_message"]

    @pytest.mark.asyncio()
    async def test_partial_failure_state_consistency(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test state consistency during partial failures."""
        # Run crawl with partial failures
        result = await crawl_service.crawl_board(
            board=sample_board, category="心得", pages=5, simulate_partial_failure=True
        )

        # Check that all components reflect partial success state
        state = await crawl_service.get_crawl_state(sample_board)

        assert result["status"] == "partial_success"
        assert len(state.failed_urls) > 0
        assert len(state.processed_urls) > 0
        assert state.status == CrawlStatus.COMPLETED  # Still completed despite failures

    @pytest.mark.asyncio()
    async def test_recovery_state_transitions(self, crawl_service: CrawlService, sample_board: str):
        """Test proper state transitions during error recovery."""
        # Create error state
        try:
            await crawl_service.crawl_board(
                board=sample_board, category="心得", pages=3, simulate_error=True
            )
        except CrawlError:
            pass

        # Verify error state
        state = await crawl_service.get_crawl_state(sample_board)
        assert state.status == CrawlStatus.ERROR

        # Start recovery
        recovery_task = asyncio.create_task(
            crawl_service.crawl_board(board=sample_board, category="心得", pages=3)
        )

        # Check intermediate state
        await asyncio.sleep(0.5)  # Let recovery start
        intermediate_state = await crawl_service.get_crawl_state(sample_board)
        assert intermediate_state.status == CrawlStatus.CRAWLING

        # Complete recovery
        result = await recovery_task

        # Check final state
        final_state = await crawl_service.get_crawl_state(sample_board)
        assert result["status"] == "success"
        assert final_state.status == CrawlStatus.COMPLETED
        assert final_state.error_message is None  # Error should be cleared


class TestErrorGuidanceSystem:
    """Test error guidance and user messaging."""

    @pytest.mark.asyncio()
    async def test_error_categorization(self, error_handler: ErrorHandler):
        """Test that errors are properly categorized."""
        # Test different error types
        network_error = CrawlError("Connection timeout", error_type="network")
        db_error = CrawlError("Database connection failed", error_type="database")
        api_error = CrawlError("API key invalid", error_type="api")

        network_guidance = await error_handler.get_guidance(network_error)
        db_guidance = await error_handler.get_guidance(db_error)
        api_guidance = await error_handler.get_guidance(api_error)

        # Each should have appropriate guidance
        assert "network" in network_guidance.lower()
        assert "database" in db_guidance.lower()
        assert "api" in api_guidance.lower()

    @pytest.mark.asyncio()
    async def test_recovery_suggestions(self, error_handler: ErrorHandler):
        """Test that appropriate recovery suggestions are provided."""
        timeout_error = CrawlError("Request timeout", error_type="network")
        guidance = await error_handler.get_guidance(timeout_error)

        # Should provide actionable suggestions
        assert any(word in guidance.lower() for word in ["retry", "wait", "check"])
        assert "suggestion" in guidance.lower() or "try" in guidance.lower()

    @pytest.mark.asyncio()
    async def test_user_friendly_error_messages(
        self, crawl_service: CrawlService, sample_board: str
    ):
        """Test that error messages are user-friendly."""
        try:
            await crawl_service.crawl_board(
                board=sample_board,
                category="心得",
                pages=3,
                simulate_user_error=True,  # Simulate user configuration error
            )
        except CrawlError as e:
            # Error message should be in Chinese and user-friendly
            error_msg = str(e)
            assert any(char in error_msg for char in "設定配置錯誤")  # Should contain Chinese
            assert "請" in error_msg  # Should be polite/instructional
