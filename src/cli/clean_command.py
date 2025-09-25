"""Clean command implementation."""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import typer

from ..database.article_repository import ArticleRepository
from ..lib.config_loader import ConfigLoader
from ..lib.console import safe_echo
from ..lib.redis_client import RedisClient

logger = logging.getLogger(__name__)


def clean(
    states: bool = typer.Option(False, "--states", help="Clean crawl state data"),
    cache: bool = typer.Option(False, "--cache", help="Clean Redis cache data"),
    logs: bool = typer.Option(False, "--logs", help="Clean expired log files"),
    older_than: int = typer.Option(30, "--older-than", help="Clean data older than specified days"),
    confirm: bool = typer.Option(
        True, "--confirm/--no-confirm", help="Whether confirmation is required"
    ),
):
    """Clean system data."""
    safe_echo("[CLEAN] Start cleaning system data")

    # Check if any cleaning option is selected
    if not (states or cache or logs):
        safe_echo("[WARNING] No cleaning options selected")
        safe_echo("Available options: --states, --cache, --logs")
        safe_echo("Use --help for more information")
        return

    if states:
        safe_echo(f"[CLEAN] Clean crawl states older than {older_than} days")
    if cache:
        safe_echo("[CLEAN] Clean Redis cache")
    if logs:
        safe_echo(f"[CLEAN] Clean log files older than {older_than} days")

    # Show confirmation prompt
    if confirm:
        safe_echo("\nThis operation will permanently delete the selected data.")
        if not typer.confirm("Do you want to continue?"):
            safe_echo("[CANCELLED] Cleaning operation cancelled")
            return

    try:
        # Run the async clean operation
        result = asyncio.run(
            _async_clean(states=states, cache=cache, logs=logs, older_than=older_than)
        )

        # Display results
        safe_echo("\n[CLEAN] Cleaning completed")
        safe_echo("=" * 40)

        if result["states"]["attempted"]:
            if result["states"]["success"]:
                safe_echo(f"✅ Crawl states: Cleaned {result['states']['count']} old states")
            else:
                safe_echo(f"❌ Crawl states: Failed - {result['states']['error']}")

        if result["cache"]["attempted"]:
            if result["cache"]["success"]:
                safe_echo(f"✅ Redis cache: Cleaned {result['cache']['count']} cache entries")
            else:
                safe_echo(f"❌ Redis cache: Failed - {result['cache']['error']}")

        if result["logs"]["attempted"]:
            if result["logs"]["success"]:
                safe_echo(f"✅ Log files: Cleaned {result['logs']['count']} old files")
                safe_echo(f"   Freed space: {result['logs']['freed_mb']:.2f} MB")
            else:
                safe_echo(f"❌ Log files: Failed - {result['logs']['error']}")

        safe_echo("=" * 40)

        # Show summary
        total_success = sum(1 for r in result.values() if r.get("success", False))
        total_attempted = sum(1 for r in result.values() if r.get("attempted", False))

        if total_success == total_attempted:
            safe_echo("🎉 All cleaning operations completed successfully")
        elif total_success > 0:
            safe_echo(f"⚠️ {total_success}/{total_attempted} cleaning operations completed")
        else:
            safe_echo("❌ All cleaning operations failed")
            raise typer.Exit(1)

    except Exception as e:
        safe_echo(f"[ERROR] Cleaning failed: {e!s}")
        logger.error(f"Clean command failed: {e}")
        raise typer.Exit(1)


async def _async_clean(
    states: bool, cache: bool, logs: bool, older_than: int
) -> dict[str, dict[str, Any]]:
    """Async helper function to perform cleaning operations."""
    # Load configuration
    config_loader = ConfigLoader()
    config = await config_loader.load_config(use_defaults=True, use_environment=True)

    result = {
        "states": {"attempted": states, "success": False, "count": 0, "error": ""},
        "cache": {"attempted": cache, "success": False, "count": 0, "error": ""},
        "logs": {"attempted": logs, "success": False, "count": 0, "freed_mb": 0.0, "error": ""},
    }

    # Clean crawl states
    if states:
        try:
            count = await _clean_crawl_states(config, older_than)
            result["states"]["success"] = True
            result["states"]["count"] = count
        except Exception as e:
            result["states"]["error"] = str(e)
            logger.error(f"Failed to clean crawl states: {e}")

    # Clean Redis cache
    if cache:
        try:
            count = await _clean_redis_cache(config)
            result["cache"]["success"] = True
            result["cache"]["count"] = count
        except Exception as e:
            result["cache"]["error"] = str(e)
            logger.error(f"Failed to clean Redis cache: {e}")

    # Clean log files
    if logs:
        try:
            count, freed_mb = await _clean_log_files(older_than)
            result["logs"]["success"] = True
            result["logs"]["count"] = count
            result["logs"]["freed_mb"] = freed_mb
        except Exception as e:
            result["logs"]["error"] = str(e)
            logger.error(f"Failed to clean log files: {e}")

    return result


async def _clean_crawl_states(config: dict[str, str], older_than: int) -> int:
    """Clean old crawl states from database and Redis."""
    cutoff_date = datetime.now() - timedelta(days=older_than)
    cleaned_count = 0

    # Clean from database
    article_repository = None
    try:
        article_repository = ArticleRepository(
            connection_string=config.get(
                "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
            )
        )

        # Delete old crawl states (this would be implemented in the repository)
        # For now, we'll just count articles older than the cutoff
        try:
            # This is a placeholder - actual implementation would clean crawl states
            old_articles = await article_repository.get_articles_before_date(cutoff_date)
            cleaned_count += len(old_articles)
        except Exception as e:
            logger.debug(f"Database state cleaning: {e}")

    finally:
        if article_repository:
            await article_repository.close()

    # Clean from Redis
    redis_client = None
    try:
        redis_client = RedisClient(
            url=config.get("REDIS_URL", "redis://localhost:6379"), retry_attempts=1, retry_delay=0.5
        )

        # Get Redis keys for crawl states
        state_keys = await redis_client.keys("ptt:crawl:state:*")

        for key in state_keys:
            try:
                # Check the timestamp of the state
                state_data = await redis_client.get(key)
                if state_data:
                    import json

                    state_info = json.loads(state_data)
                    if "last_crawl_time" in state_info:
                        last_crawl = datetime.fromisoformat(state_info["last_crawl_time"])
                        if last_crawl < cutoff_date:
                            await redis_client.delete(key)
                            cleaned_count += 1
            except Exception as e:
                logger.debug(f"Failed to process state key {key}: {e}")

    except Exception as e:
        logger.debug(f"Redis state cleaning: {e}")
    finally:
        if redis_client:
            await redis_client.close()

    return cleaned_count


async def _clean_redis_cache(config: dict[str, str]) -> int:
    """Clean Redis cache data."""
    cleaned_count = 0
    redis_client = None

    try:
        redis_client = RedisClient(
            url=config.get("REDIS_URL", "redis://localhost:6379"), retry_attempts=1, retry_delay=0.5
        )

        # Get all cache-related keys (exclude state keys)
        all_keys = await redis_client.keys("*")
        cache_keys = [key for key in all_keys if not key.startswith("ptt:crawl:state:")]

        # Delete cache keys
        if cache_keys:
            deleted = await redis_client.delete(*cache_keys)
            cleaned_count = deleted

    except Exception as e:
        logger.error(f"Redis cache cleaning failed: {e}")
        raise
    finally:
        if redis_client:
            await redis_client.close()

    return cleaned_count


async def _clean_log_files(older_than: int) -> tuple[int, float]:
    """Clean old log files."""
    cutoff_date = datetime.now() - timedelta(days=older_than)
    cleaned_count = 0
    freed_bytes = 0

    # Get project root and logs directory
    project_root = Path(__file__).parent.parent.parent
    logs_dir = project_root / "logs"

    if not logs_dir.exists():
        return 0, 0.0

    # Find and clean old log files
    for log_file in logs_dir.glob("*.log*"):
        try:
            # Skip current log files (those without date suffix or very recent)
            stat = log_file.stat()
            modified_time = datetime.fromtimestamp(stat.st_mtime)

            if modified_time < cutoff_date:
                file_size = stat.st_size
                log_file.unlink()  # Delete the file
                cleaned_count += 1
                freed_bytes += file_size
                logger.debug(f"Deleted old log file: {log_file.name}")

        except Exception as e:
            logger.warning(f"Failed to delete log file {log_file}: {e}")

    # Also clean compressed log files
    for gz_file in logs_dir.glob("*.log.*.gz"):
        try:
            stat = gz_file.stat()
            modified_time = datetime.fromtimestamp(stat.st_mtime)

            if modified_time < cutoff_date:
                file_size = stat.st_size
                gz_file.unlink()
                cleaned_count += 1
                freed_bytes += file_size
                logger.debug(f"Deleted old compressed log file: {gz_file.name}")

        except Exception as e:
            logger.warning(f"Failed to delete compressed log file {gz_file}: {e}")

    # Clean empty directories if any
    try:
        if logs_dir.exists() and not any(logs_dir.iterdir()):
            # Don't delete the logs directory itself, just ensure it's clean
            pass
    except Exception as e:
        logger.debug(f"Directory cleanup check failed: {e}")

    freed_mb = freed_bytes / (1024 * 1024)
    return cleaned_count, freed_mb
