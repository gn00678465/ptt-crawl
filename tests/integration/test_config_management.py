"""Configuration Management Integration Tests

These tests verify configuration loading, validation, and management.
They MUST FAIL initially (no implementation exists yet).
"""
import os
from pathlib import Path

import pytest

from src.database.config_repository import ConfigRepository
from src.lib.config_loader import ConfigLoader
from src.services.crawl_service import CrawlService


class TestConfigManagementIntegration:
    """Test configuration management integration."""

    @pytest.fixture()
    def config_loader(self):
        """Config loader instance for testing."""
        # This will fail until ConfigLoader is implemented
        pytest.fail("ConfigLoader not implemented yet")

    @pytest.fixture()
    def config_repository(self):
        """Config repository instance for testing."""
        # This will fail until ConfigRepository is implemented
        pytest.fail("ConfigRepository not implemented yet")

    @pytest.fixture()
    def sample_config_file(self, tmp_path) -> Path:
        """Sample configuration file for testing."""
        config_content = """
# Test Configuration
FIRECRAWL_API_URL=http://localhost:3002
FIRECRAWL_API_KEY=test_key_12345
DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/test_db
REDIS_URL=redis://localhost:6379/0

# Crawl Settings
CRAWL_RATE_LIMIT=60
CRAWL_REQUEST_DELAY=1.5
CRAWL_MAX_RETRIES=3
CRAWL_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/ptt-crawler.log
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
"""
        config_file = tmp_path / "test_config.env"
        config_file.write_text(config_content.strip())
        return config_file

    @pytest.fixture()
    def sample_invalid_config(self, tmp_path) -> Path:
        """Invalid configuration file for testing."""
        invalid_content = """
# Invalid Configuration
FIRECRAWL_API_URL=not_a_valid_url
CRAWL_RATE_LIMIT=not_a_number
DATABASE_URL=invalid_connection_string
REDIS_URL=
"""
        config_file = tmp_path / "invalid_config.env"
        config_file.write_text(invalid_content.strip())
        return config_file


class TestConfigLoading:
    """Test configuration loading from various sources."""

    @pytest.mark.asyncio()
    async def test_load_config_from_file(
        self, config_loader: ConfigLoader, sample_config_file: Path
    ):
        """Test loading configuration from file."""
        config = await config_loader.load_from_file(sample_config_file)

        assert isinstance(config, dict)
        assert config["FIRECRAWL_API_URL"] == "http://localhost:3002"
        assert config["CRAWL_RATE_LIMIT"] == "60"
        assert config["DATABASE_URL"].startswith("postgresql://")

    @pytest.mark.asyncio()
    async def test_load_config_from_environment(self, config_loader: ConfigLoader):
        """Test loading configuration from environment variables."""
        # Set test environment variables
        os.environ["PTT_CRAWLER_API_URL"] = "http://test.example.com"
        os.environ["PTT_CRAWLER_RATE_LIMIT"] = "120"

        try:
            config = await config_loader.load_from_environment()

            assert config["api_url"] == "http://test.example.com"
            assert config["rate_limit"] == "120"
        finally:
            # Cleanup
            os.environ.pop("PTT_CRAWLER_API_URL", None)
            os.environ.pop("PTT_CRAWLER_RATE_LIMIT", None)

    @pytest.mark.asyncio()
    async def test_load_config_from_database(
        self, config_loader: ConfigLoader, config_repository: ConfigRepository
    ):
        """Test loading configuration from database."""
        # First, store some config in database
        await config_repository.set_config("crawl.rate_limit", "90", "Test rate limit")
        await config_repository.set_config(
            "firecrawl.api_url", "http://db.example.com", "Test API URL"
        )

        config = await config_loader.load_from_database()

        assert config["crawl.rate_limit"] == "90"
        assert config["firecrawl.api_url"] == "http://db.example.com"

    @pytest.mark.asyncio()
    async def test_config_precedence_order(
        self, config_loader: ConfigLoader, sample_config_file: Path
    ):
        """Test configuration precedence: environment > database > file > defaults."""
        # Set up different sources with different values
        os.environ["PTT_CRAWLER_RATE_LIMIT"] = "200"  # Environment (highest precedence)

        # Database value (medium precedence) - assume this was set previously
        # File has value "60" (lower precedence)
        # Default would be something else (lowest precedence)

        try:
            config = await config_loader.load_config(config_file=sample_config_file)

            # Environment should win
            assert int(config["crawl.rate_limit"]) == 200
        finally:
            os.environ.pop("PTT_CRAWLER_RATE_LIMIT", None)

    @pytest.mark.asyncio()
    async def test_default_config_values(self, config_loader: ConfigLoader):
        """Test that default configuration values are applied."""
        config = await config_loader.load_config()  # No sources specified

        # Should have reasonable defaults
        assert "crawl.rate_limit" in config
        assert "crawl.request_delay" in config
        assert "crawl.max_retries" in config
        assert int(config["crawl.rate_limit"]) > 0
        assert float(config["crawl.request_delay"]) > 0


class TestConfigValidation:
    """Test configuration validation."""

    @pytest.mark.asyncio()
    async def test_valid_config_passes_validation(
        self, config_loader: ConfigLoader, sample_config_file: Path
    ):
        """Test that valid configuration passes validation."""
        config = await config_loader.load_from_file(sample_config_file)

        # Should not raise exception
        validated_config = await config_loader.validate_config(config)
        assert validated_config is not None

    @pytest.mark.asyncio()
    async def test_invalid_config_fails_validation(
        self, config_loader: ConfigLoader, sample_invalid_config: Path
    ):
        """Test that invalid configuration fails validation."""
        config = await config_loader.load_from_file(sample_invalid_config)

        with pytest.raises(ValueError) as exc_info:
            await config_loader.validate_config(config)

        error_message = str(exc_info.value)
        # Should mention specific validation failures
        assert "url" in error_message.lower() or "invalid" in error_message.lower()

    @pytest.mark.asyncio()
    async def test_missing_required_config_fails(self, config_loader: ConfigLoader):
        """Test that missing required configuration fails validation."""
        incomplete_config = {
            "crawl.rate_limit": "60",
            # Missing required FIRECRAWL_API_URL
        }

        with pytest.raises(ValueError) as exc_info:
            await config_loader.validate_config(incomplete_config)

        assert "required" in str(exc_info.value).lower()
        assert "firecrawl" in str(exc_info.value).lower()

    @pytest.mark.asyncio()
    async def test_config_type_validation(self, config_loader: ConfigLoader):
        """Test that configuration values are properly type-validated."""
        invalid_types_config = {
            "crawl.rate_limit": "not_a_number",  # Should be int
            "crawl.request_delay": "not_a_float",  # Should be float
            "firecrawl.api_url": "not_a_valid_url",  # Should be valid URL
        }

        with pytest.raises(ValueError) as exc_info:
            await config_loader.validate_config(invalid_types_config)

        error_message = str(exc_info.value)
        assert "number" in error_message.lower() or "url" in error_message.lower()

    @pytest.mark.asyncio()
    async def test_config_range_validation(self, config_loader: ConfigLoader):
        """Test that configuration values are within valid ranges."""
        out_of_range_config = {
            "crawl.rate_limit": "-10",  # Should be positive
            "crawl.request_delay": "0",  # Should be > 0
            "crawl.max_retries": "100",  # Should be reasonable (e.g., < 10)
        }

        with pytest.raises(ValueError) as exc_info:
            await config_loader.validate_config(out_of_range_config)

        error_message = str(exc_info.value)
        assert "range" in error_message.lower() or "positive" in error_message.lower()


class TestConfigDatabaseIntegration:
    """Test configuration integration with database."""

    @pytest.mark.asyncio()
    async def test_store_config_in_database(self, config_repository: ConfigRepository):
        """Test storing configuration in database."""
        await config_repository.set_config(
            "test.setting", "test_value", "Test configuration setting"
        )

        # Verify it was stored
        value = await config_repository.get_config("test.setting")
        assert value == "test_value"

    @pytest.mark.asyncio()
    async def test_update_existing_config(self, config_repository: ConfigRepository):
        """Test updating existing configuration."""
        # Set initial value
        await config_repository.set_config("test.update", "initial_value")

        # Update the value
        await config_repository.set_config("test.update", "updated_value")

        # Verify update
        value = await config_repository.get_config("test.update")
        assert value == "updated_value"

    @pytest.mark.asyncio()
    async def test_delete_config_from_database(self, config_repository: ConfigRepository):
        """Test deleting configuration from database."""
        # Set a value
        await config_repository.set_config("test.delete", "to_be_deleted")

        # Delete it
        success = await config_repository.delete_config("test.delete")
        assert success is True

        # Verify deletion
        value = await config_repository.get_config("test.delete")
        assert value is None

    @pytest.mark.asyncio()
    async def test_get_all_configs(self, config_repository: ConfigRepository):
        """Test getting all configurations from database."""
        # Set multiple configs
        test_configs = {
            "test.multi.1": "value1",
            "test.multi.2": "value2",
            "test.multi.3": "value3",
        }

        for key, value in test_configs.items():
            await config_repository.set_config(key, value)

        # Get all configs
        all_configs = await config_repository.get_all_configs()

        # Verify all test configs are present
        for key, expected_value in test_configs.items():
            assert key in all_configs
            assert all_configs[key] == expected_value

    @pytest.mark.asyncio()
    async def test_config_with_description(self, config_repository: ConfigRepository):
        """Test configuration with description metadata."""
        description = "This is a test configuration with description"
        await config_repository.set_config("test.desc", "value", description)

        # Get config with metadata
        config_data = await config_repository.get_config_with_metadata("test.desc")

        assert config_data["value"] == "value"
        assert config_data["description"] == description
        assert "created_at" in config_data
        assert "updated_at" in config_data


class TestConfigServiceIntegration:
    """Test configuration integration with services."""

    @pytest.mark.asyncio()
    async def test_crawl_service_uses_config(
        self, crawl_service: CrawlService, config_repository: ConfigRepository
    ):
        """Test that crawl service uses configuration properly."""
        # Set test configuration
        await config_repository.set_config("crawl.rate_limit", "30")
        await config_repository.set_config("crawl.request_delay", "2.0")

        # Start crawl and monitor it uses the config
        result = await crawl_service.crawl_board(
            board="Stock", category="心得", pages=2, monitor_config=True
        )

        # Should have used the configured rate limit and delay
        assert result["config_used"]["rate_limit"] == 30
        assert result["config_used"]["request_delay"] == 2.0

    @pytest.mark.asyncio()
    async def test_config_hot_reload(
        self, crawl_service: CrawlService, config_repository: ConfigRepository
    ):
        """Test that configuration changes are picked up without restart."""
        # Initial config
        await config_repository.set_config("crawl.rate_limit", "60")

        # Start a crawl service
        await crawl_service.initialize()

        # Change config while service is running
        await config_repository.set_config("crawl.rate_limit", "120")

        # Service should pick up the new config
        await crawl_service.reload_config()

        current_config = crawl_service.get_current_config()
        assert current_config["crawl.rate_limit"] == "120"

    @pytest.mark.asyncio()
    async def test_invalid_config_handling_in_service(
        self, crawl_service: CrawlService, config_repository: ConfigRepository
    ):
        """Test that services handle invalid configuration gracefully."""
        # Set invalid configuration
        await config_repository.set_config("crawl.rate_limit", "invalid_number")

        # Service should handle gracefully and use defaults or fail safely
        with pytest.raises(ValueError) as exc_info:
            await crawl_service.initialize()

        assert "configuration" in str(exc_info.value).lower()
        assert "invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio()
    async def test_missing_config_uses_defaults(
        self, crawl_service: CrawlService, config_repository: ConfigRepository
    ):
        """Test that missing configuration uses sensible defaults."""
        # Clear any existing config
        await config_repository.delete_config("crawl.rate_limit")

        # Service should use defaults
        await crawl_service.initialize()

        current_config = crawl_service.get_current_config()
        assert "crawl.rate_limit" in current_config
        assert int(current_config["crawl.rate_limit"]) > 0  # Should have default value


class TestConfigCLIIntegration:
    """Test configuration CLI integration."""

    @pytest.mark.asyncio()
    async def test_config_show_command(self, config_repository: ConfigRepository):
        """Test CLI config show command."""
        # Set some test configurations
        await config_repository.set_config("test.cli.1", "value1", "Test CLI setting 1")
        await config_repository.set_config("test.cli.2", "value2", "Test CLI setting 2")

        # This would be tested via CLI contract tests
        # Here we test the underlying functionality
        configs = await config_repository.get_all_configs()

        assert "test.cli.1" in configs
        assert "test.cli.2" in configs

    @pytest.mark.asyncio()
    async def test_config_set_command(self, config_repository: ConfigRepository):
        """Test CLI config set command functionality."""
        # Simulate CLI set command
        await config_repository.set_config("crawl.rate_limit", "75", "Updated via CLI")

        # Verify setting
        value = await config_repository.get_config("crawl.rate_limit")
        assert value == "75"

        # Verify description
        metadata = await config_repository.get_config_with_metadata("crawl.rate_limit")
        assert metadata["description"] == "Updated via CLI"

    @pytest.mark.asyncio()
    async def test_config_reset_command(
        self, config_loader: ConfigLoader, config_repository: ConfigRepository
    ):
        """Test CLI config reset command functionality."""
        # Set custom value
        await config_repository.set_config("crawl.rate_limit", "999")

        # Reset to default
        default_config = await config_loader.get_default_config()
        default_rate_limit = default_config["crawl.rate_limit"]

        await config_repository.set_config("crawl.rate_limit", default_rate_limit)

        # Verify reset
        value = await config_repository.get_config("crawl.rate_limit")
        assert value == default_rate_limit


class TestConfigurationErrorHandling:
    """Test configuration error handling scenarios."""

    @pytest.mark.asyncio()
    async def test_config_file_not_found_handling(self, config_loader: ConfigLoader):
        """Test handling of missing configuration file."""
        non_existent_file = Path("non_existent_config.env")

        # Should handle gracefully and use defaults
        config = await config_loader.load_config(config_file=non_existent_file)

        # Should still have default values
        assert "crawl.rate_limit" in config
        assert config["crawl.rate_limit"] is not None

    @pytest.mark.asyncio()
    async def test_config_file_permission_error(self, config_loader: ConfigLoader, tmp_path):
        """Test handling of configuration file permission errors."""
        # Create file with restricted permissions (simulate permission error)
        restricted_file = tmp_path / "restricted_config.env"
        restricted_file.write_text("TEST_CONFIG=value")
        restricted_file.chmod(0o000)  # No permissions

        try:
            # Should handle permission error gracefully
            with pytest.raises(PermissionError):
                await config_loader.load_from_file(restricted_file)
        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o666)

    @pytest.mark.asyncio()
    async def test_database_connection_error_config(self, config_loader: ConfigLoader):
        """Test configuration loading when database is unavailable."""
        # Simulate database unavailable
        with pytest.raises(ConnectionError):
            await config_loader.load_from_database_with_connection_error()

        # Should fall back to file/environment config
        config = await config_loader.load_config_with_db_fallback()
        assert config is not None
        assert "crawl.rate_limit" in config

    @pytest.mark.asyncio()
    async def test_corrupted_config_file_handling(self, config_loader: ConfigLoader, tmp_path):
        """Test handling of corrupted configuration file."""
        # Create corrupted config file
        corrupted_file = tmp_path / "corrupted_config.env"
        corrupted_file.write_text("This is not valid configuration format\n\x00\x01\x02")

        # Should handle gracefully
        with pytest.raises(ValueError) as exc_info:
            await config_loader.load_from_file(corrupted_file)

        assert (
            "corrupted" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
        )
