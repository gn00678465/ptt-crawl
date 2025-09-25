"""Firecrawl API Integration Contract Tests

These tests verify the Firecrawl API integration matches the specifications.
They MUST FAIL initially (no implementation exists yet).
"""
import asyncio
from typing import Any

import pytest

from src.services.firecrawl_service import FirecrawlError, FirecrawlResponse, FirecrawlService


class TestFirecrawlAPIContracts:
    """Test Firecrawl API integration contracts."""

    @pytest.fixture()
    def mock_firecrawl_config(self) -> dict[str, Any]:
        """Mock Firecrawl configuration."""
        return {
            "api_url": "http://localhost:3002",
            "api_key": "test_api_key",
            "timeout": 30,
            "max_retries": 3,
        }

    @pytest.fixture()
    def firecrawl_service(self, mock_firecrawl_config: dict[str, Any]) -> FirecrawlService:
        """Firecrawl service instance."""
        # This will fail until FirecrawlService is implemented
        return FirecrawlService(mock_firecrawl_config)

    @pytest.fixture()
    def sample_board_url(self) -> str:
        """Sample PTT board URL."""
        return "https://www.ptt.cc/bbs/Stock/index.html"

    @pytest.fixture()
    def sample_article_url(self) -> str:
        """Sample PTT article URL."""
        return "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"

    @pytest.fixture()
    def expected_board_response(self) -> dict[str, Any]:
        """Expected response format for board page scraping."""
        return {
            "success": True,
            "data": {
                "markdown": "# PTT 看板內容...",
                "html": "<html>...</html>",
                "metadata": {
                    "title": "批踢踢實業坊 › Stock",
                    "description": "Stock 板文章列表",
                    "sourceURL": "https://www.ptt.cc/bbs/Stock/index.html",
                    "statusCode": 200,
                },
                "links": [
                    {
                        "text": "[心得] 今日操作心得分享",
                        "url": "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
                    }
                ],
            },
            "warning": None,
        }

    @pytest.fixture()
    def expected_article_response(self) -> dict[str, Any]:
        """Expected response format for article scraping."""
        return {
            "success": True,
            "data": {
                "markdown": "# [心得] 今日操作心得\n\n作者: user123\n時間: Mon Sep 25 10:30:00 2025\n\n文章內容...\n\n※ 發信站: 批踢踢實業坊(ptt.cc)",
                "metadata": {
                    "title": "[心得] 今日操作心得",
                    "author": "user123",
                    "board": "Stock",
                    "publishTime": "2025-09-25T10:30:00+08:00",
                    "sourceURL": "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
                    "statusCode": 200,
                },
            },
            "warning": None,
        }


class TestFirecrawlBoardScraping:
    """Test Firecrawl board page scraping."""

    @pytest.mark.asyncio()
    async def test_scrape_board_page_success(
        self, firecrawl_service: FirecrawlService, sample_board_url: str
    ):
        """Test successful board page scraping."""
        response = await firecrawl_service.scrape_board_page(sample_board_url)

        assert isinstance(response, FirecrawlResponse)
        assert response.success is True
        assert "markdown" in response.data
        assert "links" in response.data
        assert isinstance(response.data["links"], list)

    @pytest.mark.asyncio()
    async def test_scrape_board_page_with_pagination(self, firecrawl_service: FirecrawlService):
        """Test board page scraping with pagination."""
        url = "https://www.ptt.cc/bbs/Stock/index1234.html"
        response = await firecrawl_service.scrape_board_page(url)

        assert isinstance(response, FirecrawlResponse)
        # Should handle paginated URLs properly

    @pytest.mark.asyncio()
    async def test_extract_article_links(
        self, firecrawl_service: FirecrawlService, expected_board_response: dict[str, Any]
    ):
        """Test extracting article links from board page response."""
        links = firecrawl_service.extract_article_links(expected_board_response)

        assert isinstance(links, list)
        assert len(links) > 0

        for link in links:
            assert "text" in link
            assert "url" in link
            assert "https://www.ptt.cc/bbs/" in link["url"]

    @pytest.mark.asyncio()
    async def test_filter_articles_by_category(self, firecrawl_service: FirecrawlService):
        """Test filtering articles by category."""
        mock_links = [
            {"text": "[心得] 測試心得", "url": "https://example.com/1"},
            {"text": "[標的] 測試標的", "url": "https://example.com/2"},
            {"text": "[請益] 測試請益", "url": "https://example.com/3"},
        ]

        filtered = firecrawl_service.filter_articles_by_category(mock_links, "心得")
        assert len(filtered) == 1
        assert "[心得]" in filtered[0]["text"]


class TestFirecrawlArticleScraping:
    """Test Firecrawl article scraping."""

    @pytest.mark.asyncio()
    async def test_scrape_article_success(
        self, firecrawl_service: FirecrawlService, sample_article_url: str
    ):
        """Test successful article scraping."""
        response = await firecrawl_service.scrape_article(sample_article_url)

        assert isinstance(response, FirecrawlResponse)
        assert response.success is True
        assert "markdown" in response.data
        assert "metadata" in response.data

    @pytest.mark.asyncio()
    async def test_parse_article_metadata(
        self, firecrawl_service: FirecrawlService, expected_article_response: dict[str, Any]
    ):
        """Test parsing article metadata from response."""
        metadata = firecrawl_service.parse_article_metadata(expected_article_response)

        assert "title" in metadata
        assert "author" in metadata
        assert "publishTime" in metadata
        assert "board" in metadata

    @pytest.mark.asyncio()
    async def test_clean_article_content(self, firecrawl_service: FirecrawlService):
        """Test cleaning article content."""
        raw_content = "# [心得] 測試\n\n內容...\n\n※ 發信站: 批踢踢實業坊(ptt.cc)"
        cleaned = firecrawl_service.clean_article_content(raw_content)

        assert isinstance(cleaned, str)
        assert "※ 發信站" not in cleaned  # System messages should be removed


class TestFirecrawlErrorHandling:
    """Test Firecrawl API error handling."""

    @pytest.mark.asyncio()
    async def test_handle_timeout_error(self, firecrawl_service: FirecrawlService):
        """Test handling timeout errors."""
        # Mock a timeout scenario
        with pytest.raises(FirecrawlError) as exc_info:
            await firecrawl_service.scrape_article("https://timeout.example.com")

        assert exc_info.value.error_code == "TIMEOUT"

    @pytest.mark.asyncio()
    async def test_handle_unauthorized_error(self, firecrawl_service: FirecrawlService):
        """Test handling unauthorized errors."""
        # Should fail with invalid API key
        service = FirecrawlService({"api_key": "invalid_key", "api_url": "http://localhost:3002"})

        with pytest.raises(FirecrawlError) as exc_info:
            await service.scrape_article("https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html")

        assert exc_info.value.error_code == "UNAUTHORIZED"

    @pytest.mark.asyncio()
    async def test_handle_rate_limit_error(self, firecrawl_service: FirecrawlService):
        """Test handling rate limit errors."""
        with pytest.raises(FirecrawlError) as exc_info:
            # Simulate rapid requests to trigger rate limit
            tasks = [
                firecrawl_service.scrape_article(f"https://example.com/{i}")
                for i in range(200)  # Exceed rate limit
            ]
            await asyncio.gather(*tasks)

        assert exc_info.value.error_code == "RATE_LIMITED"

    @pytest.mark.asyncio()
    async def test_handle_invalid_url_error(self, firecrawl_service: FirecrawlService):
        """Test handling invalid URL errors."""
        with pytest.raises(FirecrawlError) as exc_info:
            await firecrawl_service.scrape_article("not-a-valid-url")

        assert exc_info.value.error_code == "INVALID_URL"

    @pytest.mark.asyncio()
    async def test_handle_content_not_found_error(self, firecrawl_service: FirecrawlService):
        """Test handling 404 content not found errors."""
        with pytest.raises(FirecrawlError) as exc_info:
            await firecrawl_service.scrape_article("https://www.ptt.cc/bbs/Stock/nonexistent.html")

        assert exc_info.value.error_code == "CONTENT_NOT_FOUND"


class TestFirecrawlRetryMechanism:
    """Test Firecrawl retry mechanisms."""

    @pytest.mark.asyncio()
    async def test_retry_on_timeout(self, firecrawl_service: FirecrawlService):
        """Test retry mechanism on timeout errors."""
        # This should retry up to max_retries times
        with pytest.raises(FirecrawlError):
            await firecrawl_service.scrape_article_with_retry("https://timeout.example.com")

    @pytest.mark.asyncio()
    async def test_no_retry_on_unauthorized(self, firecrawl_service: FirecrawlService):
        """Test that unauthorized errors are not retried."""
        service = FirecrawlService({"api_key": "invalid", "api_url": "http://localhost:3002"})

        # Should fail immediately without retries
        with pytest.raises(FirecrawlError) as exc_info:
            await service.scrape_article_with_retry("https://www.ptt.cc/bbs/Stock/M.1.A.1.html")

        assert exc_info.value.error_code == "UNAUTHORIZED"

    @pytest.mark.asyncio()
    async def test_exponential_backoff(self, firecrawl_service: FirecrawlService):
        """Test exponential backoff in retry mechanism."""
        # Should implement exponential backoff between retries
        import time

        start_time = time.time()

        with pytest.raises(FirecrawlError):
            await firecrawl_service.scrape_article_with_retry("https://retry.example.com")

        elapsed = time.time() - start_time
        # Should take time due to backoff delays
        assert elapsed > 1  # At least some delay should occur


class TestFirecrawlRateLimiting:
    """Test Firecrawl rate limiting."""

    @pytest.mark.asyncio()
    async def test_rate_limiting_enforcement(self, firecrawl_service: FirecrawlService):
        """Test that rate limiting is enforced."""
        # Should respect rate limits defined in config
        urls = [f"https://example.com/{i}" for i in range(10)]

        start_time = asyncio.get_event_loop().time()

        # This should be rate-limited
        for url in urls:
            await firecrawl_service.scrape_article(url)

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should take some time due to rate limiting
        assert elapsed > 0.5  # Some delay should be enforced

    @pytest.mark.asyncio()
    async def test_concurrent_request_limiting(self, firecrawl_service: FirecrawlService):
        """Test concurrent request limiting."""
        urls = [f"https://example.com/{i}" for i in range(20)]

        # Should limit concurrent requests
        tasks = [firecrawl_service.scrape_article(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Should handle concurrent limits gracefully
        assert len(responses) == len(urls)


class TestFirecrawlConfiguration:
    """Test Firecrawl service configuration."""

    def test_service_initialization(self, mock_firecrawl_config: dict[str, Any]):
        """Test service initialization with config."""
        service = FirecrawlService(mock_firecrawl_config)

        assert service.api_url == mock_firecrawl_config["api_url"]
        assert service.timeout == mock_firecrawl_config["timeout"]
        assert service.max_retries == mock_firecrawl_config["max_retries"]

    def test_invalid_configuration_raises_error(self):
        """Test that invalid configuration raises appropriate errors."""
        with pytest.raises(ValueError):
            FirecrawlService({})  # Missing required config

        with pytest.raises(ValueError):
            FirecrawlService({"api_url": ""})  # Invalid API URL

    def test_default_configuration_values(self):
        """Test default configuration values are applied."""
        config = {"api_url": "http://localhost:3002"}
        service = FirecrawlService(config)

        # Should apply defaults for missing values
        assert service.timeout > 0
        assert service.max_retries > 0
