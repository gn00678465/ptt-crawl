"""Config data model.

This module defines the Config data class and default configuration values.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class Config:
    """配置管理資料模型."""

    key: str
    value: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Validate config data after initialization."""
        self._validate_key()
        self._validate_value()

    def _validate_key(self) -> None:
        """Validate config key."""
        if not self.key or not self.key.strip():
            raise ValueError("配置鍵名不可為空")

        if len(self.key) > 100:
            raise ValueError("配置鍵名長度不可超過 100 字符")

        # Key should follow dot notation pattern
        if not self.key.replace(".", "").replace("_", "").replace("-", "").isalnum():
            raise ValueError("配置鍵名格式無效")

    def _validate_value(self) -> None:
        """Validate config value."""
        if self.value is None:
            raise ValueError("配置值不可為 None")

        if len(str(self.value)) > 1000:
            raise ValueError("配置值長度不可超過 1000 字符")

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create config from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            description=data.get("description"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def get_typed_value(self) -> Any:
        """Get config value with appropriate type conversion."""
        # Try to parse as JSON first (for complex types)
        try:
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try common type conversions
        value_lower = self.value.lower().strip()

        # Boolean
        if value_lower in ("true", "false"):
            return value_lower == "true"

        # Integer
        try:
            if "." not in self.value:
                return int(self.value)
        except ValueError:
            pass

        # Float
        try:
            return float(self.value)
        except ValueError:
            pass

        # Return as string if no conversion possible
        return self.value

    def set_value(self, value: Any) -> None:
        """Set config value with appropriate serialization."""
        if isinstance(value, (dict, list)):
            self.value = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            self.value = "true" if value else "false"
        else:
            self.value = str(value)

        self.updated_at = datetime.now()

    def is_boolean(self) -> bool:
        """Check if config value is boolean."""
        return self.value.lower().strip() in ("true", "false")

    def is_numeric(self) -> bool:
        """Check if config value is numeric."""
        try:
            float(self.value)
            return True
        except ValueError:
            return False

    def is_json(self) -> bool:
        """Check if config value is JSON."""
        try:
            json.loads(self.value)
            return True
        except (json.JSONDecodeError, TypeError):
            return False


# Default configuration values
DEFAULT_CONFIG: dict[str, Any] = {
    "crawl.rate_limit": 60,  # 每分鐘最大爬取數量
    "crawl.request_delay": 1.5,  # 請求間隔秒數
    "crawl.max_retries": 3,  # 最大重試次數
    "crawl.timeout": 30,  # 請求超時時間
    "crawl.concurrent_limit": 3,  # 併發限制
    "crawl.batch_size": 10,  # 批次大小
    "firecrawl.api_url": "http://localhost:3002",  # Firecrawl API 端點
    "firecrawl.api_key": "",  # Firecrawl API 金鑰
    "database.connection_pool_size": 10,  # 資料庫連接池大小
    "database.connection_timeout": 30,  # 資料庫連接超時
    "database.query_timeout": 60,  # 查詢超時時間
    "redis.connection_string": "redis://localhost:6379",  # Redis 連線字串
    "redis.connection_timeout": 5,  # Redis 連接超時
    "redis.key_prefix": "ptt:crawl:",  # Redis 鍵名前綴
    "state.backup_interval": 300,  # 狀態備份間隔（秒）
    "state.cleanup_days": 30,  # 狀態清理天數
    "logging.level": "INFO",  # 日誌級別
    "logging.file_path": "logs/ptt-crawler.log",  # 日誌檔案路徑
    "logging.max_size": "10MB",  # 日誌檔案最大大小
    "logging.backup_count": 5,  # 日誌檔案備份數量
    "logging.format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",  # 日誌格式
}


class ConfigKey:
    """Configuration key constants."""

    # Crawl settings
    CRAWL_RATE_LIMIT = "crawl.rate_limit"
    CRAWL_REQUEST_DELAY = "crawl.request_delay"
    CRAWL_MAX_RETRIES = "crawl.max_retries"
    CRAWL_TIMEOUT = "crawl.timeout"
    CRAWL_CONCURRENT_LIMIT = "crawl.concurrent_limit"
    CRAWL_BATCH_SIZE = "crawl.batch_size"

    # Firecrawl settings
    FIRECRAWL_API_URL = "firecrawl.api_url"
    FIRECRAWL_API_KEY = "firecrawl.api_key"

    # Database settings
    DATABASE_CONNECTION_POOL_SIZE = "database.connection_pool_size"
    DATABASE_CONNECTION_TIMEOUT = "database.connection_timeout"
    DATABASE_QUERY_TIMEOUT = "database.query_timeout"

    # Redis settings
    REDIS_CONNECTION_STRING = "redis.connection_string"
    REDIS_CONNECTION_TIMEOUT = "redis.connection_timeout"
    REDIS_KEY_PREFIX = "redis.key_prefix"

    # State management settings
    STATE_BACKUP_INTERVAL = "state.backup_interval"
    STATE_CLEANUP_DAYS = "state.cleanup_days"

    # Logging settings
    LOGGING_LEVEL = "logging.level"
    LOGGING_FILE_PATH = "logging.file_path"
    LOGGING_MAX_SIZE = "logging.max_size"
    LOGGING_BACKUP_COUNT = "logging.backup_count"
    LOGGING_FORMAT = "logging.format"


def get_default_value(key: str) -> Any:
    """Get default value for configuration key."""
    return DEFAULT_CONFIG.get(key)


def is_required_key(key: str) -> bool:
    """Check if configuration key is required."""
    required_keys = {
        ConfigKey.FIRECRAWL_API_URL,
        ConfigKey.DATABASE_CONNECTION_POOL_SIZE,
        ConfigKey.REDIS_CONNECTION_STRING,
    }
    return key in required_keys


def validate_config_value(key: str, value: Any) -> None:
    """Validate configuration value for specific key."""
    if key == ConfigKey.CRAWL_RATE_LIMIT:
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError("crawl.rate_limit 必須為正數")
        if value > 1000:
            raise ValueError("crawl.rate_limit 不可超過 1000")

    elif key == ConfigKey.CRAWL_REQUEST_DELAY:
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError("crawl.request_delay 必須為非負數")

    elif key == ConfigKey.CRAWL_MAX_RETRIES:
        if not isinstance(value, int) or value < 0:
            raise ValueError("crawl.max_retries 必須為非負整數")
        if value > 10:
            raise ValueError("crawl.max_retries 不可超過 10")

    elif key == ConfigKey.CRAWL_TIMEOUT:
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError("crawl.timeout 必須為正數")

    elif key == ConfigKey.FIRECRAWL_API_URL:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("firecrawl.api_url 不可為空")
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("firecrawl.api_url 必須為有效的 URL")

    elif key == ConfigKey.DATABASE_CONNECTION_POOL_SIZE:
        if not isinstance(value, int) or value <= 0:
            raise ValueError("database.connection_pool_size 必須為正整數")

    elif key == ConfigKey.LOGGING_LEVEL:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if value not in valid_levels:
            raise ValueError(f"logging.level 必須為以下值之一: {valid_levels}")


def create_default_configs() -> list[Config]:
    """Create list of default configuration objects."""
    now = datetime.now()
    configs = []

    descriptions = {
        ConfigKey.CRAWL_RATE_LIMIT: "每分鐘最大爬取數量",
        ConfigKey.CRAWL_REQUEST_DELAY: "請求間隔秒數",
        ConfigKey.CRAWL_MAX_RETRIES: "最大重試次數",
        ConfigKey.CRAWL_TIMEOUT: "請求超時時間（秒）",
        ConfigKey.FIRECRAWL_API_URL: "Firecrawl API 端點",
        ConfigKey.FIRECRAWL_API_KEY: "Firecrawl API 金鑰",
        ConfigKey.DATABASE_CONNECTION_POOL_SIZE: "資料庫連接池大小",
        ConfigKey.REDIS_CONNECTION_STRING: "Redis 連線字串",
        ConfigKey.LOGGING_LEVEL: "日誌級別",
        ConfigKey.LOGGING_FILE_PATH: "日誌檔案路徑",
    }

    for key, value in DEFAULT_CONFIG.items():
        config = Config(
            key=key,
            value=str(value),
            description=descriptions.get(key),
            created_at=now,
            updated_at=now,
        )
        configs.append(config)

    return configs
