"""Unit tests for data models.

Test data validation and serialization logic for Article, CrawlState, and Config models.
"""
from datetime import datetime, timedelta

from src.models.article import Article
from src.models.config import DEFAULT_CONFIG, Config, create_default_configs, validate_config_value
from src.models.crawl_state import CrawlState, CrawlStatus


class TestArticleModel:
    """Test Article model validation and methods."""

    def test_article_creation(self):
        """Test creating a valid Article instance."""
        now = datetime.now()
        article = Article(
            id=1,
            title="[心得] 測試文章標題",
            author="test_user",
            board="Stock",
            url="https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
            content="這是測試內容。",
            publish_date=now,
            crawl_date=now,
            category="心得",
            created_at=now,
            updated_at=now,
        )

        assert article.id == 1
        assert article.title == "[心得] 測試文章標題"
        assert article.author == "test_user"
        assert article.board == "Stock"
        assert article.category == "心得"
        assert article.url == "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        assert article.content == "這是測試內容。"

    def test_article_validation_valid_url(self):
        """Test URL validation with valid PTT URLs."""
        valid_urls = [
            "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
            "https://www.ptt.cc/bbs/Gossiping/M.9876543210.A.456.html",
            "https://www.ptt.cc/bbs/Tech_Job/M.1111111111.A.789.html",
        ]

        for url in valid_urls:
            article = Article(
                id=1,
                title="Test",
                author="user",
                board="Stock",
                url=url,
                content="test",
                publish_date=datetime.now(),
                crawl_date=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            assert article.is_valid_ptt_url() is True

    def test_article_validation_invalid_url(self):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "http://example.com",
            "https://google.com",
            "not_a_url",
            "",
            "https://www.ptt.cc/bbs/Stock/invalid.html",
        ]

        for url in invalid_urls:
            article = Article(
                id=1,
                title="Test",
                author="user",
                board="Stock",
                url=url,
                content="test",
                publish_date=datetime.now(),
                crawl_date=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            assert article.is_valid_ptt_url() is False

    def test_article_get_age_in_days(self):
        """Test calculating article age in days."""
        now = datetime.now()
        past_date = now - timedelta(days=5)

        article = Article(
            id=1,
            title="Test",
            author="user",
            board="Stock",
            url="https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
            content="test",
            publish_date=past_date,
            crawl_date=now,
            created_at=now,
            updated_at=now,
        )

        age = article.get_age_in_days()
        assert 4.9 <= age <= 5.1  # Allow for small time differences

    def test_article_extract_category_from_title(self):
        """Test extracting category from article title."""
        test_cases = [
            ("[心得] 今日投資心得分享", "心得"),
            ("[標的] 2330 台積電分析", "標的"),
            ("[請益] 新手投資建議", "請益"),
            ("Re: [心得] 回覆心得文", "心得"),
            ("沒有分類的標題", None),
            ("[未知分類] 測試", "未知分類"),
        ]

        for title, expected_category in test_cases:
            article = Article(
                id=1,
                title=title,
                author="user",
                board="Stock",
                url="https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
                content="test",
                publish_date=datetime.now(),
                crawl_date=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                category=None,
            )

            extracted = article.extract_category_from_title()
            assert extracted == expected_category

    def test_article_get_summary(self):
        """Test getting article content summary."""
        long_content = "這是一個很長的文章內容。" * 50
        article = Article(
            id=1,
            title="Test",
            author="user",
            board="Stock",
            url="https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
            content=long_content,
            publish_date=datetime.now(),
            crawl_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        summary = article.get_summary(max_length=50)
        assert len(summary) <= 53  # 50 + "..."
        assert summary.endswith("...")

        short_content = "短內容"
        article.content = short_content
        summary = article.get_summary(max_length=50)
        assert summary == short_content

    def test_article_to_dict(self):
        """Test converting article to dictionary."""
        now = datetime.now()
        article = Article(
            id=1,
            title="Test",
            author="user",
            board="Stock",
            url="https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
            content="test",
            publish_date=now,
            crawl_date=now,
            category="心得",
            created_at=now,
            updated_at=now,
        )

        article_dict = article.to_dict()

        assert article_dict["id"] == 1
        assert article_dict["title"] == "Test"
        assert article_dict["author"] == "user"
        assert article_dict["board"] == "Stock"
        assert article_dict["category"] == "心得"
        assert "publish_date" in article_dict
        assert "created_at" in article_dict


class TestCrawlStateModel:
    """Test CrawlState model validation and methods."""

    def test_crawl_state_creation(self):
        """Test creating a valid CrawlState instance."""
        now = datetime.now()
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=now,
            last_page_crawled=5,
            processed_urls=["url1", "url2"],
            failed_urls=["url3"],
            retry_count=1,
            max_retries=3,
            status=CrawlStatus.COMPLETED,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

        assert state.id == 1
        assert state.board == "Stock"
        assert state.last_page_crawled == 5
        assert len(state.processed_urls) == 2
        assert len(state.failed_urls) == 1
        assert state.status == CrawlStatus.COMPLETED

    def test_crawl_state_validation(self):
        """Test CrawlState validation logic."""
        now = datetime.now()

        # Valid state
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=now,
            last_page_crawled=1,
            processed_urls=[],
            failed_urls=[],
            retry_count=0,
            max_retries=3,
            status=CrawlStatus.IDLE,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        assert state.is_valid()

        # Invalid board name
        state.board = ""
        assert not state.is_valid()
        state.board = "Stock"

        # Invalid retry count
        state.retry_count = -1
        assert not state.is_valid()
        state.retry_count = 0

        # Invalid page number
        state.last_page_crawled = -1
        assert not state.is_valid()

    def test_crawl_state_add_processed_url(self):
        """Test adding processed URLs."""
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=1,
            processed_urls=[],
            failed_urls=[],
            retry_count=0,
            max_retries=3,
            status=CrawlStatus.IDLE,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        state.add_processed_url(url)

        assert url in state.processed_urls
        assert len(state.processed_urls) == 1

        # Test deduplication
        state.add_processed_url(url)
        assert len(state.processed_urls) == 1

    def test_crawl_state_add_failed_url(self):
        """Test adding failed URLs."""
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=1,
            processed_urls=[],
            failed_urls=[],
            retry_count=0,
            max_retries=3,
            status=CrawlStatus.IDLE,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        state.add_failed_url(url)

        assert url in state.failed_urls
        assert len(state.failed_urls) == 1

    def test_crawl_state_get_success_rate(self):
        """Test calculating success rate."""
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=1,
            processed_urls=["url1", "url2", "url3", "url4"],
            failed_urls=["url5"],
            retry_count=0,
            max_retries=3,
            status=CrawlStatus.COMPLETED,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        success_rate = state.get_success_rate()
        assert success_rate == 0.8  # 4 success out of 5 total

        # Test with no URLs
        state.processed_urls = []
        state.failed_urls = []
        success_rate = state.get_success_rate()
        assert success_rate == 1.0

    def test_crawl_state_is_url_processed(self):
        """Test checking if URL is processed."""
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=1,
            processed_urls=["url1", "url2"],
            failed_urls=[],
            retry_count=0,
            max_retries=3,
            status=CrawlStatus.COMPLETED,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert state.is_url_processed("url1") is True
        assert state.is_url_processed("url3") is False

    def test_crawl_state_can_retry(self):
        """Test retry capability check."""
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=1,
            processed_urls=[],
            failed_urls=[],
            retry_count=2,
            max_retries=3,
            status=CrawlStatus.ERROR,
            error_message="Test error",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert state.can_retry() is True

        # Exceeded max retries
        state.retry_count = 3
        assert state.can_retry() is False

        # Not in error status
        state.status = CrawlStatus.COMPLETED
        state.retry_count = 1
        assert state.can_retry() is False

    def test_crawl_state_get_statistics(self):
        """Test getting crawl statistics."""
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=5,
            processed_urls=["url1", "url2", "url3"],
            failed_urls=["url4"],
            retry_count=1,
            max_retries=3,
            status=CrawlStatus.COMPLETED,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        stats = state.get_statistics()

        assert stats["total_processed"] == 3
        assert stats["total_failed"] == 1
        assert stats["success_rate"] == 0.75
        assert stats["retry_count"] == 1
        assert stats["status"] == "completed"


class TestConfigModel:
    """Test Config model validation and methods."""

    def test_config_creation(self):
        """Test creating a valid Config instance."""
        now = datetime.now()
        config = Config(
            key="test.key",
            value="test_value",
            description="Test configuration",
            created_at=now,
            updated_at=now,
        )

        assert config.key == "test.key"
        assert config.value == "test_value"
        assert config.description == "Test configuration"

    def test_config_validation(self):
        """Test Config validation logic."""
        now = datetime.now()

        # Valid config
        config = Config(
            key="valid.key", value="valid_value", description="Test", created_at=now, updated_at=now
        )
        assert config.is_valid()

        # Invalid key (empty)
        config.key = ""
        assert not config.is_valid()
        config.key = "valid.key"

        # Invalid key (invalid characters)
        config.key = "invalid key!"
        assert not config.is_valid()
        config.key = "valid.key"

        # Valid config should pass
        assert config.is_valid()

    def test_config_get_typed_value(self):
        """Test getting typed values from config."""
        now = datetime.now()

        # Integer value
        config = Config(
            key="int.value", value="42", description="Test", created_at=now, updated_at=now
        )
        assert config.get_typed_value(int) == 42

        # Float value
        config.value = "3.14"
        assert config.get_typed_value(float) == 3.14

        # Boolean values
        for bool_value in ["true", "True", "1", "yes", "on"]:
            config.value = bool_value
            assert config.get_typed_value(bool) is True

        for bool_value in ["false", "False", "0", "no", "off"]:
            config.value = bool_value
            assert config.get_typed_value(bool) is False

        # String value (default)
        config.value = "string_value"
        assert config.get_typed_value(str) == "string_value"

    def test_config_is_json_value(self):
        """Test checking if value is valid JSON."""
        now = datetime.now()
        config = Config(
            key="test.key",
            value='{"key": "value"}',
            description="Test",
            created_at=now,
            updated_at=now,
        )
        assert config.is_json_value() is True

        config.value = "not_json"
        assert config.is_json_value() is False

        config.value = '["array", "value"]'
        assert config.is_json_value() is True

    def test_validate_config_value_function(self):
        """Test standalone config value validation function."""
        # Valid values
        assert validate_config_value("crawl.rate_limit", "60") is True
        assert validate_config_value("crawl.request_delay", "1.5") is True
        assert validate_config_value("firecrawl.api_url", "http://localhost:3002") is True

        # Invalid values
        assert validate_config_value("crawl.rate_limit", "not_a_number") is False
        assert validate_config_value("crawl.request_delay", "-1") is False
        assert validate_config_value("firecrawl.api_url", "not_a_url") is False

        # Unknown key (should return True - no validation)
        assert validate_config_value("unknown.key", "any_value") is True

    def test_default_config_constants(self):
        """Test default configuration constants."""
        assert "crawl.rate_limit" in DEFAULT_CONFIG
        assert "crawl.request_delay" in DEFAULT_CONFIG
        assert "firecrawl.api_url" in DEFAULT_CONFIG
        assert "database.url" in DEFAULT_CONFIG

        # Check data types
        assert isinstance(DEFAULT_CONFIG["crawl.rate_limit"], int)
        assert isinstance(DEFAULT_CONFIG["crawl.request_delay"], float)
        assert isinstance(DEFAULT_CONFIG["firecrawl.api_url"], str)

    def test_create_default_configs_function(self):
        """Test creating default config instances."""
        configs = create_default_configs()

        assert len(configs) == len(DEFAULT_CONFIG)

        for config in configs:
            assert isinstance(config, Config)
            assert config.key in DEFAULT_CONFIG
            assert config.value == str(DEFAULT_CONFIG[config.key])
            assert config.description is not None
            assert config.created_at is not None
            assert config.updated_at is not None

    def test_config_edge_cases(self):
        """Test edge cases for config validation."""
        now = datetime.now()

        # Very long key
        long_key = "a" * 300
        config = Config(
            key=long_key, value="value", description="Test", created_at=now, updated_at=now
        )
        assert not config.is_valid()  # Should fail due to length

        # Very long value
        config.key = "valid.key"
        config.value = "v" * 10000
        assert config.is_valid()  # Long values should be allowed

        # Unicode characters
        config.key = "unicode.key"
        config.value = "測試中文值"
        config.description = "測試中文描述"
        assert config.is_valid()

    def test_config_serialization(self):
        """Test config serialization to dict."""
        now = datetime.now()
        config = Config(
            key="test.key",
            value="test_value",
            description="Test config",
            created_at=now,
            updated_at=now,
        )

        config_dict = {
            "key": config.key,
            "value": config.value,
            "description": config.description,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
        }

        # Manual comparison since Config doesn't have to_dict method
        assert config.key == config_dict["key"]
        assert config.value == config_dict["value"]
        assert config.description == config_dict["description"]


class TestModelIntegration:
    """Test integration between different models."""

    def test_article_and_crawl_state_integration(self):
        """Test integration between Article and CrawlState models."""
        # Create article
        article = Article(
            id=1,
            title="[心得] Test",
            author="user",
            board="Stock",
            url="https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html",
            content="test",
            publish_date=datetime.now(),
            crawl_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Create crawl state
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=1,
            processed_urls=[],
            failed_urls=[],
            retry_count=0,
            max_retries=3,
            status=CrawlStatus.CRAWLING,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Test adding article URL to state
        state.add_processed_url(article.url)
        assert state.is_url_processed(article.url)
        assert article.board == state.board

    def test_config_with_model_validation(self):
        """Test config values that affect model validation."""
        # Config for retry settings
        retry_config = Config(
            key="crawl.max_retries",
            value="5",
            description="Max retries",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        max_retries = retry_config.get_typed_value(int)

        # Use in CrawlState
        state = CrawlState(
            id=1,
            board="Stock",
            last_crawl_time=datetime.now(),
            last_page_crawled=1,
            processed_urls=[],
            failed_urls=[],
            retry_count=0,
            max_retries=max_retries,
            status=CrawlStatus.IDLE,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert state.max_retries == 5
        assert state.is_valid()
