"""Configuration loader implementation.

This module implements configuration loading from environment variables and config files.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

from ..models.config import DEFAULT_CONFIG, validate_config_value
from ..database.config_repository import ConfigRepository

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置載入器，支援環境變數和配置檔案載入."""

    def __init__(self, config_repo: Optional[ConfigRepository] = None):
        self.config_repo = config_repo
        self._cached_config: Optional[Dict[str, str]] = None
        self._config_sources = []

        # 環境變數前綴
        self.env_prefix = "PTT_CRAWLER_"

        logger.info("配置載入器初始化完成")

    async def load_config(
        self,
        config_file: Optional[Path] = None,
        use_environment: bool = True,
        use_database: bool = True,
        use_defaults: bool = True,
    ) -> Dict[str, str]:
        """
        載入配置，按優先順序合併不同來源.

        優先順序: 環境變數 > 資料庫 > 配置檔案 > 預設值

        Args:
            config_file: 配置檔案路徑
            use_environment: 是否使用環境變數
            use_database: 是否使用資料庫配置
            use_defaults: 是否使用預設值

        Returns:
            Dict[str, str]: 合併後的配置
        """
        config = {}
        self._config_sources = []

        # 1. 載入預設值
        if use_defaults:
            for key, value in DEFAULT_CONFIG.items():
                config[key] = str(value)

            # Add CLI-compatible flat key mappings for easier usage
            flat_key_mappings = {
                "DATABASE_URL": "postgresql://ptt_user:password@localhost:5432/ptt_crawler",
                "REDIS_URL": "redis://localhost:6379",
                "FIRECRAWL_API_URL": "http://localhost:3002",
                "FIRECRAWL_API_KEY": "",
                "CRAWL_RATE_LIMIT": "60",
                "CRAWL_REQUEST_DELAY": "1.5",
                "CRAWL_MAX_RETRIES": "3",
                "CRAWL_TIMEOUT": "30"
            }
            config.update(flat_key_mappings)
            self._config_sources.append("defaults")
            logger.debug("載入預設配置")

        # 2. 載入配置檔案
        if config_file:
            file_config = await self.load_from_file(config_file)
            config.update(file_config)
            self._config_sources.append(f"file:{config_file}")
            logger.debug(f"載入檔案配置: {config_file}")

        # 3. 載入資料庫配置
        if use_database and self.config_repo:
            try:
                db_config = await self.load_from_database()
                config.update(db_config)
                self._config_sources.append("database")
                logger.debug("載入資料庫配置")
            except Exception as e:
                logger.warning(f"載入資料庫配置失敗: {e}")

        # 4. 載入環境變數 (最高優先順序)
        if use_environment:
            env_config = await self.load_from_environment()
            config.update(env_config)
            self._config_sources.append("environment")
            logger.debug("載入環境變數配置")

        # 5. 驗證配置
        validated_config = await self.validate_config(config)

        # 快取配置
        self._cached_config = validated_config

        logger.info(f"配置載入完成，來源: {', '.join(self._config_sources)}")
        return validated_config

    async def load_from_file(self, config_file: Path) -> Dict[str, str]:
        """從配置檔案載入配置."""
        config = {}

        if not config_file.exists():
            logger.warning(f"配置檔案不存在: {config_file}")
            return config

        try:
            if config_file.suffix.lower() == '.json':
                # JSON 格式
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        config[key] = str(value)
            else:
                # .env 或純文字格式
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()

                        # 跳過空行和註解
                        if not line or line.startswith('#'):
                            continue

                        # 解析 KEY=VALUE 格式
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()

                            # 移除引號
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]

                            # 轉換環境變數格式為內部格式
                            config_key = self._env_to_config_key(key)
                            config[config_key] = value
                        else:
                            logger.warning(f"無效的配置格式 ({config_file}:{line_num}): {line}")

            logger.debug(f"從檔案載入 {len(config)} 項配置: {config_file}")
            return config

        except Exception as e:
            logger.error(f"載入配置檔案失敗 ({config_file}): {e}")
            raise

    async def load_from_environment(self) -> Dict[str, str]:
        """從環境變數載入配置."""
        config = {}

        for env_key, env_value in os.environ.items():
            if env_key.startswith(self.env_prefix):
                # 轉換環境變數名稱為配置鍵
                config_key = self._env_to_config_key(env_key)
                config[config_key] = env_value

        logger.debug(f"從環境變數載入 {len(config)} 項配置")
        return config

    async def load_from_database(self) -> Dict[str, str]:
        """從資料庫載入配置."""
        if not self.config_repo:
            return {}

        try:
            config = await self.config_repo.get_all_configs()
            logger.debug(f"從資料庫載入 {len(config)} 項配置")
            return config
        except Exception as e:
            logger.error(f"從資料庫載入配置失敗: {e}")
            raise

    def _env_to_config_key(self, env_key: str) -> str:
        """轉換環境變數名稱為配置鍵."""
        # 移除前綴並轉為小寫，用點號分隔
        if env_key.startswith(self.env_prefix):
            key = env_key[len(self.env_prefix):].lower()
        else:
            key = env_key.lower()

        # 將底線替換為點號
        key = key.replace('_', '.')

        # 處理常見的映射
        key_mappings = {
            'api.url': 'firecrawl.api_url',
            'api.key': 'firecrawl.api_key',
            'db.url': 'database.url',
            'redis.url': 'redis.url',
            'rate.limit': 'crawl.rate_limit',
            'request.delay': 'crawl.request_delay',
        }

        return key_mappings.get(key, key)

    async def validate_config(self, config: Dict[str, str]) -> Dict[str, str]:
        """驗證配置值."""
        validated_config = {}
        errors = []

        for key, value in config.items():
            try:
                # 使用模型中的驗證函數
                if validate_config_value(key, value):
                    validated_config[key] = value
                else:
                    errors.append(f"配置值無效: {key}={value}")
            except Exception as e:
                errors.append(f"配置驗證錯誤 ({key}): {e}")

        # 檢查必要配置 - Use flat keys for CLI compatibility
        required_configs = [
            'FIRECRAWL_API_URL',
            'DATABASE_URL',
        ]

        # Check both dotted and flat key formats
        for required_key in required_configs:
            if required_key not in validated_config:
                # Check if dotted key equivalent exists
                dotted_equivalent = {
                    'FIRECRAWL_API_URL': 'firecrawl.api_url',
                    'DATABASE_URL': 'database.url'
                }.get(required_key)

                if not dotted_equivalent or dotted_equivalent not in validated_config:
                    errors.append(f"缺少必要配置: {required_key}")

        # 類型和範圍驗證
        validation_rules = {
            'crawl.rate_limit': lambda v: self._validate_positive_int(v, 1, 1000),
            'crawl.request_delay': lambda v: self._validate_positive_float(v, 0.1, 10.0),
            'crawl.max_retries': lambda v: self._validate_positive_int(v, 1, 10),
            'crawl.timeout': lambda v: self._validate_positive_int(v, 5, 300),
            'crawl.concurrent_limit': lambda v: self._validate_positive_int(v, 1, 20),
            'firecrawl.api_url': lambda v: self._validate_url(v),
        }

        for key, validator in validation_rules.items():
            if key in validated_config:
                try:
                    if not validator(validated_config[key]):
                        errors.append(f"配置值超出有效範圍: {key}={validated_config[key]}")
                except Exception as e:
                    errors.append(f"配置驗證失敗 ({key}): {e}")

        if errors:
            error_message = "配置驗證失敗:\n" + "\n".join(errors)
            logger.error(error_message)
            raise ValueError(error_message)

        logger.debug(f"配置驗證通過: {len(validated_config)} 項")
        return validated_config

    def _validate_positive_int(self, value: str, min_val: int, max_val: int) -> bool:
        """驗證正整數範圍."""
        try:
            int_val = int(value)
            return min_val <= int_val <= max_val
        except ValueError:
            return False

    def _validate_positive_float(self, value: str, min_val: float, max_val: float) -> bool:
        """驗證正浮點數範圍."""
        try:
            float_val = float(value)
            return min_val <= float_val <= max_val
        except ValueError:
            return False

    def _validate_url(self, value: str) -> bool:
        """驗證 URL 格式."""
        import re
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, value))

    async def get_config_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """取得單一配置值."""
        if self._cached_config:
            return self._cached_config.get(key, default)

        # 如果沒有快取，嘗試從資料庫載入
        if self.config_repo:
            try:
                value = await self.config_repo.get_config(key, default)
                return value
            except Exception as e:
                logger.warning(f"取得配置值失敗 ({key}): {e}")

        return default

    async def set_config_value(self, key: str, value: str, description: Optional[str] = None) -> bool:
        """設定單一配置值."""
        if not self.config_repo:
            logger.warning("無資料庫連線，無法設定配置值")
            return False

        try:
            # 驗證配置值
            if not validate_config_value(key, value):
                raise ValueError(f"無效的配置值: {key}={value}")

            # 儲存到資料庫
            await self.config_repo.set_config(key, value, description)

            # 更新快取
            if self._cached_config:
                self._cached_config[key] = value

            logger.info(f"配置值已更新: {key}={value}")
            return True

        except Exception as e:
            logger.error(f"設定配置值失敗 ({key}): {e}")
            return False

    async def reload_config(self) -> Dict[str, str]:
        """重新載入配置."""
        logger.info("重新載入配置")
        self._cached_config = None
        return await self.load_config()

    def get_config_sources(self) -> List[str]:
        """取得配置來源列表."""
        return self._config_sources.copy()

    def get_cached_config(self) -> Optional[Dict[str, str]]:
        """取得快取的配置."""
        return self._cached_config.copy() if self._cached_config else None

    async def export_config_to_file(self, output_file: Path, format: str = "env") -> bool:
        """匯出配置到檔案."""
        if not self._cached_config:
            logger.warning("無快取配置可匯出")
            return False

        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "json":
                # JSON 格式
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self._cached_config, f, indent=2, ensure_ascii=False)
            else:
                # .env 格式
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("# PTT Crawler 配置檔案\n")
                    f.write(f"# 匯出時間: {os.getenv('TZ', 'UTC')}\n\n")

                    for key, value in sorted(self._cached_config.items()):
                        # 轉換為環境變數格式
                        env_key = self._config_to_env_key(key)
                        f.write(f"{env_key}={value}\n")

            logger.info(f"配置已匯出到: {output_file}")
            return True

        except Exception as e:
            logger.error(f"匯出配置失敗: {e}")
            return False

    def _config_to_env_key(self, config_key: str) -> str:
        """轉換配置鍵為環境變數名稱."""
        # 轉為大寫並用底線分隔
        env_key = config_key.upper().replace('.', '_')
        return f"{self.env_prefix}{env_key}"

    async def validate_all_configs(self) -> List[str]:
        """驗證所有配置值."""
        if not self._cached_config:
            return ["無配置可驗證"]

        errors = []

        try:
            await self.validate_config(self._cached_config)
        except ValueError as e:
            errors.append(str(e))

        return errors

    # 測試用方法

    async def load_config_with_db_fallback(self) -> Dict[str, str]:
        """載入配置，資料庫連線失敗時使用檔案回退."""
        try:
            return await self.load_config(use_database=True)
        except Exception as e:
            logger.warning(f"資料庫配置載入失敗，使用檔案回退: {e}")
            return await self.load_config(use_database=False)

    async def load_from_database_with_connection_error(self):
        """模擬資料庫連線錯誤（測試用）."""
        raise ConnectionError("模擬資料庫連線失敗")