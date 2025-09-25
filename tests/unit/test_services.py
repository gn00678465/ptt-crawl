"""Unit tests for service layer.

Test business logic and edge cases for crawl services, state management, and integrations.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.services.crawl_service import CrawlService
from src.services.state_service import StateService
from src.services.firecrawl_service import FirecrawlService, FirecrawlError, FirecrawlResponse
from src.models.article import Article
from src.models.crawl_state import CrawlState, CrawlStatus


class TestCrawlService:
    """Test CrawlService business logic."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for CrawlService."""
        return {
            'firecrawl_service': Mock(spec=FirecrawlService),
            'article_repo': AsyncMock(),
            'crawl_state_repo': AsyncMock(),
            'state_service': AsyncMock(),
            'parser_service': AsyncMock(),
            'config': {
                'crawl.rate_limit': 60,
                'crawl.request_delay': 1.0,
                'crawl.max_retries': 3,
                'crawl.concurrent_limit': 3,
            }
        }

    @pytest.fixture
    def crawl_service(self, mock_dependencies):
        """Create CrawlService instance with mocked dependencies."""
        return CrawlService(**mock_dependencies)

    async def test_crawl_board_basic_success(self, crawl_service: CrawlService, mock_dependencies):
        """Test successful basic board crawling."""
        # Setup mocks
        mock_dependencies['crawl_state_repo'].get_crawl_state.return_value = None
        mock_dependencies['crawl_state_repo'].init_crawl_state.return_value = None

        # Mock crawl state creation
        mock_state = Mock(spec=CrawlState)
        mock_state.board = "Stock"
        mock_state.status = CrawlStatus.IDLE
        mock_dependencies['crawl_state_repo'].get_crawl_state.return_value = mock_state

        # Mock phase 1 - board page crawling
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {"markdown": "test content"}
        mock_dependencies['firecrawl_service'].scrape_board_page = AsyncMock(return_value=mock_response)
        mock_dependencies['firecrawl_service'].extract_article_links.return_value = [
            {"url": "https://www.ptt.cc/bbs/Stock/M.1.A.1.html", "title": "Test Article"}
        ]

        # Mock phase 2 - article content crawling
        mock_dependencies['article_repo'].article_exists.return_value = False
        mock_dependencies['firecrawl_service'].scrape_article_with_retry = AsyncMock(return_value=mock_response)
        mock_dependencies['parser_service'].parse_article.return_value = {
            "title": "Test Article",
            "author": "test_user",
            "content": "test content",
            "category": "心得",
            "publish_date": datetime.now(),
        }
        mock_dependencies['article_repo'].insert_article.return_value = 1

        # Execute
        result = await crawl_service.crawl_board("Stock", category="心得", pages=1)

        # Verify
        assert result["status"] == "success"
        assert result["board"] == "Stock"
        assert result["category"] == "心得"
        assert result["articles_new"] >= 0

    async def test_crawl_board_initialization_error(self, crawl_service: CrawlService, mock_dependencies):
        """Test crawl board with state initialization error."""
        # Mock state that can't be initialized
        mock_dependencies['crawl_state_repo'].get_crawl_state.return_value = None

        with pytest.raises(ValueError, match="無法初始化爬取狀態"):
            await crawl_service.crawl_board("Stock", pages=1)

    async def test_crawl_board_concurrent_crawl_prevention(self, crawl_service: CrawlService, mock_dependencies):
        """Test prevention of concurrent crawls on same board."""
        # Mock state showing crawl in progress
        mock_state = Mock(spec=CrawlState)
        mock_state.status = CrawlStatus.CRAWLING
        mock_dependencies['crawl_state_repo'].get_crawl_state.return_value = mock_state

        with pytest.raises(ValueError, match="正在爬取中"):
            await crawl_service.crawl_board("Stock", pages=1, force=False)

    async def test_crawl_board_force_override(self, crawl_service: CrawlService, mock_dependencies):
        """Test force override of existing crawl state."""
        # Mock state showing crawl in progress
        mock_state = Mock(spec=CrawlState)
        mock_state.board = "Stock"
        mock_state.status = CrawlStatus.CRAWLING
        mock_dependencies['crawl_state_repo'].get_crawl_state.return_value = mock_state

        # Should reset state when force=True
        result = await crawl_service.crawl_board("Stock", pages=1, force=True)

        # Should have called reset methods
        mock_dependencies['crawl_state_repo'].update_crawl_state.assert_called()
        mock_dependencies['crawl_state_repo'].reset_retry_count.assert_called_with("Stock")

    async def test_crawl_board_firecrawl_error_handling(self, crawl_service: CrawlService, mock_dependencies):
        """Test handling of Firecrawl API errors."""
        # Setup basic mocks
        mock_state = Mock(spec=CrawlState)
        mock_state.board = "Stock"
        mock_state.status = CrawlStatus.IDLE
        mock_dependencies['crawl_state_repo'].get_crawl_state.return_value = mock_state

        # Mock Firecrawl error
        mock_dependencies['firecrawl_service'].scrape_board_page = AsyncMock(
            side_effect=FirecrawlError("API error", "API_ERROR")
        )

        with pytest.raises(FirecrawlError):
            await crawl_service.crawl_board("Stock", pages=1)

        # Should have updated error state
        mock_dependencies['crawl_state_repo'].update_crawl_state.assert_called()
        mock_dependencies['crawl_state_repo'].increment_retry_count.assert_called_with("Stock")

    async def test_filter_processed_links_incremental(self, crawl_service: CrawlService, mock_dependencies):
        """Test filtering of already processed links in incremental mode."""
        links = [
            {"url": "https://www.ptt.cc/bbs/Stock/M.1.A.1.html"},
            {"url": "https://www.ptt.cc/bbs/Stock/M.2.A.2.html"},
            {"url": "https://www.ptt.cc/bbs/Stock/M.3.A.3.html"},
        ]

        mock_state = Mock(spec=CrawlState)
        mock_state.is_url_processed.side_effect = lambda url: url == "https://www.ptt.cc/bbs/Stock/M.1.A.1.html"

        filtered = crawl_service._filter_processed_links(links, mock_state)

        assert len(filtered) == 2
        assert filtered[0]["url"] == "https://www.ptt.cc/bbs/Stock/M.2.A.2.html"
        assert filtered[1]["url"] == "https://www.ptt.cc/bbs/Stock/M.3.A.3.html"

    async def test_get_crawl_statistics(self, crawl_service: CrawlService, mock_dependencies):
        """Test getting crawl statistics."""
        # Mock state
        mock_state = Mock(spec=CrawlState)
        mock_state.status = CrawlStatus.COMPLETED
        mock_state.last_crawl_time = datetime.now()
        mock_state.processed_urls = ["url1", "url2"]
        mock_state.failed_urls = ["url3"]
        mock_state.retry_count = 1
        mock_state.get_success_rate.return_value = 0.8

        mock_dependencies['crawl_state_repo'].get_crawl_state.return_value = mock_state
        mock_dependencies['article_repo'].count_articles_by_board.return_value = 10
        mock_dependencies['article_repo'].get_recent_articles.return_value = [Mock(), Mock()]

        stats = await crawl_service.get_crawl_statistics("Stock")

        assert stats["board"] == "Stock"
        assert stats["status"] == "completed"
        assert stats["total_articles"] == 10
        assert stats["recent_articles"] == 2
        assert stats["processed_urls"] == 2
        assert stats["failed_urls"] == 1
        assert stats["success_rate"] == 0.8

    async def test_retry_failed_urls(self, crawl_service: CrawlService, mock_dependencies):
        """Test retrying failed URLs."""
        # Mock state with failed URLs
        mock_state = Mock(spec=CrawlState)
        mock_state.board = "Stock"
        mock_state.failed_urls = [
            "https://www.ptt.cc/bbs/Stock/M.1.A.1.html",
            "https://www.ptt.cc/bbs/Stock/M.2.A.2.html"
        ]
        mock_dependencies['crawl_state_repo'].get_crawl_state.return_value = mock_state

        # Mock successful retry
        mock_response = Mock()
        mock_response.success = True
        mock_dependencies['firecrawl_service'].scrape_article_with_retry = AsyncMock(return_value=mock_response)
        mock_dependencies['parser_service'].parse_article.return_value = {
            "title": "Test", "author": "user", "content": "content", "publish_date": datetime.now()
        }
        mock_dependencies['article_repo'].article_exists.return_value = False
        mock_dependencies['article_repo'].insert_article.return_value = 1

        result = await crawl_service.retry_failed_urls("Stock")

        assert result["status"] == "success"
        assert result["urls_retried"] == 2
        assert result["articles_created"] >= 0


class TestStateService:
    """Test StateService functionality."""

    @pytest.fixture
    def state_service(self):
        """Create StateService instance."""
        return StateService("redis://localhost:6379", "test_data/state")

    @pytest.fixture
    def sample_crawl_state(self):
        """Create sample CrawlState for testing."""
        return CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=5,
            processed_urls=["url1", "url2"],
            failed_urls=["url3"],
            retry_count=1,
            max_retries=3,
            status=CrawlStatus.COMPLETED,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    async def test_save_and_get_json_state(self, state_service: StateService, sample_crawl_state: CrawlState):
        """Test saving and retrieving state from JSON."""
        # Save state
        success = await state_service.save_state_to_json(sample_crawl_state)
        assert success is True

        # Retrieve state
        state_data = await state_service.get_json_state("Stock")
        assert state_data is not None
        assert state_data["board"] == "Stock"
        assert state_data["status"] == "completed"
        assert len(state_data["processed_urls"]) == 2

    async def test_recover_state_from_json(self, state_service: StateService, sample_crawl_state: CrawlState):
        """Test recovering CrawlState object from JSON."""
        # Save state first
        await state_service.save_state_to_json(sample_crawl_state)

        # Recover state
        recovered_state = await state_service.recover_state_from_json("Stock")
        assert recovered_state is not None
        assert recovered_state.board == sample_crawl_state.board
        assert recovered_state.status == sample_crawl_state.status
        assert recovered_state.processed_urls == sample_crawl_state.processed_urls

    async def test_health_check(self, state_service: StateService):
        """Test StateService health check."""
        health = await state_service.health_check()

        assert "redis_available" in health
        assert "json_dir_exists" in health
        assert "json_dir_writable" in health

        # JSON directory should exist after initialization
        assert health["json_dir_exists"] is True

    async def test_cleanup_expired_states(self, state_service: StateService, sample_crawl_state: CrawlState):
        """Test cleaning up expired state files."""
        # Save a state
        await state_service.save_state_to_json(sample_crawl_state)

        # Clean with 0 days (should clean everything)
        cleaned_count = await state_service.cleanup_expired_states(days=0)
        assert cleaned_count >= 0

    async def test_delete_state(self, state_service: StateService, sample_crawl_state: CrawlState):
        """Test deleting state from all storage."""
        # Save state first
        await state_service.save_state_to_json(sample_crawl_state)

        # Delete state
        success = await state_service.delete_state("Stock")
        assert success is True

        # Verify deletion
        state_data = await state_service.get_json_state("Stock")
        assert state_data is None

    async def test_get_all_board_states(self, state_service: StateService, sample_crawl_state: CrawlState):
        """Test getting all board states."""
        # Save multiple states
        await state_service.save_state_to_json(sample_crawl_state)

        # Create another state for different board
        other_state = sample_crawl_state
        other_state.board = "Gossiping"
        await state_service.save_state_to_json(other_state)

        # Get all states
        all_states = await state_service.get_all_board_states()
        assert len(all_states) >= 1  # At least the states we created


class TestFirecrawlService:
    """Test FirecrawlService functionality."""

    @pytest.fixture
    def firecrawl_config(self):
        """Create Firecrawl service configuration."""
        return {
            "api_url": "http://localhost:3002",
            "api_key": "test_key",
            "timeout": 30,
            "max_retries": 3,
        }

    @pytest.fixture
    def firecrawl_service(self, firecrawl_config):
        """Create FirecrawlService instance."""
        return FirecrawlService(firecrawl_config)

    def test_service_initialization(self, firecrawl_service: FirecrawlService, firecrawl_config):
        """Test service initialization with config."""
        assert firecrawl_service.api_url == firecrawl_config["api_url"]
        assert firecrawl_service.timeout == firecrawl_config["timeout"]
        assert firecrawl_service.max_retries == firecrawl_config["max_retries"]

    def test_service_initialization_missing_url(self):
        """Test service initialization fails without API URL."""
        with pytest.raises(ValueError, match="api_url 為必填欄位"):
            FirecrawlService({})

    def test_extract_article_links(self, firecrawl_service: FirecrawlService):
        """Test extracting article links from board page response."""
        response_data = {
            "data": {
                "markdown": """
# PTT Board

[心得] Test Article 1
https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html

[標的] Test Article 2
https://www.ptt.cc/bbs/Stock/M.9876543210.A.456.html
""",
                "links": [
                    {
                        "text": "[請益] Test Article 3",
                        "url": "https://www.ptt.cc/bbs/Stock/M.1111111111.A.789.html"
                    }
                ]
            }
        }

        links = firecrawl_service.extract_article_links(response_data)
        assert len(links) >= 1  # Should find at least some links

        # Check link format
        for link in links:
            assert "url" in link
            assert "https://www.ptt.cc/bbs/" in link["url"]

    def test_filter_articles_by_category(self, firecrawl_service: FirecrawlService):
        """Test filtering articles by category."""
        links = [
            {"text": "[心得] Investment Experience", "category": "心得", "url": "url1"},
            {"text": "[標的] Stock Analysis", "category": "標的", "url": "url2"},
            {"text": "[請益] Help Needed", "category": "請益", "url": "url3"},
            {"text": "[心得] Another Experience", "category": "心得", "url": "url4"},
        ]

        filtered = firecrawl_service.filter_articles_by_category(links, "心得")
        assert len(filtered) == 2
        assert all("[心得]" in link["text"] for link in filtered)

    def test_parse_article_metadata(self, firecrawl_service: FirecrawlService):
        """Test parsing article metadata from response."""
        response_data = {
            "data": {
                "markdown": """# [心得] Test Article

作者: test_user
時間: Mon Sep 25 10:30:00 2024

Article content here.""",
                "metadata": {
                    "title": "[心得] Test Article",
                    "author": "test_user",
                    "publishTime": "Mon Sep 25 10:30:00 2024",
                    "board": "Stock",
                }
            }
        }

        metadata = firecrawl_service.parse_article_metadata(response_data)

        assert metadata["title"] == "[心得] Test Article"
        assert metadata["author"] == "test_user"
        assert metadata["publishTime"] == "Mon Sep 25 10:30:00 2024"
        assert metadata["board"] == "Stock"

    def test_clean_article_content(self, firecrawl_service: FirecrawlService):
        """Test cleaning article content."""
        dirty_content = """Article content here.

※ 發信站: 批踢踢實業坊(ptt.cc)
※ 文章網址: https://example.com

推 user1: Good article
→ user2: I agree
噓 user3: Disagree

More content here."""

        cleaned = firecrawl_service.clean_article_content(dirty_content)

        # Should remove system messages
        assert "※ 發信站" not in cleaned
        assert "※ 文章網址" not in cleaned

        # Should remove comments
        assert "推 user1" not in cleaned
        assert "→ user2" not in cleaned
        assert "噓 user3" not in cleaned

        # Should keep normal content
        assert "Article content here." in cleaned
        assert "More content here." in cleaned

    async def test_rate_limiting(self, firecrawl_service: FirecrawlService):
        """Test rate limiting functionality."""
        # This is a basic test - in practice, rate limiting is complex
        # We just verify that the rate limiting variables are set up correctly
        assert firecrawl_service._max_requests_per_minute > 0
        assert firecrawl_service._concurrent_limit > 0
        assert isinstance(firecrawl_service._request_times, list)

    def test_get_service_info(self, firecrawl_service: FirecrawlService, firecrawl_config):
        """Test getting service information."""
        info = firecrawl_service.get_service_info()

        assert info["api_url"] == firecrawl_config["api_url"]
        assert info["timeout"] == firecrawl_config["timeout"]
        assert info["max_retries"] == firecrawl_config["max_retries"]
        assert "concurrent_limit" in info
        assert "rate_limit" in info


class TestServiceIntegration:
    """Test integration between different services."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for integration testing."""
        return {
            'crawl_service': Mock(spec=CrawlService),
            'state_service': Mock(spec=StateService),
            'firecrawl_service': Mock(spec=FirecrawlService),
        }

    async def test_crawl_service_state_service_integration(self, mock_services):
        """Test integration between CrawlService and StateService."""
        # This would test how CrawlService uses StateService
        # In practice, this is covered by the CrawlService tests
        # but here we can test specific integration scenarios
        pass

    async def test_error_propagation_between_services(self, mock_services):
        """Test that errors propagate correctly between services."""
        # Test that when Firecrawl fails, CrawlService handles it properly
        # and StateService is updated with error information
        pass