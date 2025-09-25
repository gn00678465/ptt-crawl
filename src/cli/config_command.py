"""Config command implementation."""
import asyncio
import logging
from typing import Any, Optional

import typer

from ..database.config_repository import ConfigRepository
from ..lib.config_loader import ConfigLoader
from ..lib.console import safe_echo

logger = logging.getLogger(__name__)

# Create config subapp
config = typer.Typer(help="Configuration management")


@config.command()
def show(key: Optional[str] = typer.Argument(None, help="Specific configuration key")):
    """Show configuration."""
    if key:
        safe_echo(f"[CONFIG] Show config: {key}")
    else:
        safe_echo("[CONFIG] Show all configurations")

    try:
        config_data = asyncio.run(_async_show_config(key))

        if key:
            # Show specific key
            if key in config_data:
                safe_echo(f"{key} = {config_data[key]}")
            else:
                safe_echo(f"[WARNING] Configuration key '{key}' not found")
                safe_echo("Available keys:")
                for k in sorted(config_data.keys()):
                    safe_echo(f"  - {k}")
        else:
            # Show all configurations
            safe_echo("\nCurrent Configuration:")
            safe_echo("=" * 50)

            # Group configurations by category
            categories = {}
            for k, v in config_data.items():
                category = k.split(".")[0] if "." in k else "general"
                if category not in categories:
                    categories[category] = []
                categories[category].append((k, v))

            for category, items in sorted(categories.items()):
                safe_echo(f"\n[{category.upper()}]")
                for k, v in sorted(items):
                    # Mask sensitive values
                    display_value = (
                        "***"
                        if any(word in k.lower() for word in ["password", "key", "token"])
                        else v
                    )
                    safe_echo(f"  {k} = {display_value}")

            safe_echo("=" * 50)

    except Exception as e:
        safe_echo(f"[ERROR] Failed to show configuration: {e!s}")
        logger.error(f"Config show command failed: {e}")
        raise typer.Exit(1)


@config.command()
def set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
):
    """Set configuration."""
    safe_echo(f"[CONFIG] Set config: {key} = {value}")

    try:
        result = asyncio.run(_async_set_config(key, value))

        if result:
            safe_echo(f"[SUCCESS] Configuration '{key}' updated successfully")

            # Show the new value (masked if sensitive)
            display_value = (
                "***"
                if any(word in key.lower() for word in ["password", "key", "token"])
                else value
            )
            safe_echo(f"New value: {key} = {display_value}")
        else:
            safe_echo(f"[ERROR] Failed to update configuration '{key}'")
            raise typer.Exit(1)

    except ValueError as e:
        safe_echo(f"[ERROR] Invalid configuration value: {e!s}")
        raise typer.Exit(1)
    except Exception as e:
        safe_echo(f"[ERROR] Failed to set configuration: {e!s}")
        logger.error(f"Config set command failed: {e}")
        raise typer.Exit(1)


@config.command()
def reset(key: Optional[str] = typer.Argument(None, help="Specific configuration key")):
    """Reset configuration."""
    if key:
        safe_echo(f"[CONFIG] Reset config: {key}")
    else:
        safe_echo("[CONFIG] Reset all configurations")

    # Confirm the reset operation
    if key:
        confirm_msg = f"Are you sure you want to reset '{key}' to its default value?"
    else:
        confirm_msg = "Are you sure you want to reset ALL configurations to default values?"

    if not typer.confirm(confirm_msg):
        safe_echo("[CANCELLED] Configuration reset cancelled")
        return

    try:
        result = asyncio.run(_async_reset_config(key))

        if result:
            if key:
                safe_echo(f"[SUCCESS] Configuration '{key}' reset to default value")
            else:
                safe_echo("[SUCCESS] All configurations reset to default values")
        else:
            safe_echo("[ERROR] Failed to reset configuration")
            raise typer.Exit(1)

    except Exception as e:
        safe_echo(f"[ERROR] Failed to reset configuration: {e!s}")
        logger.error(f"Config reset command failed: {e}")
        raise typer.Exit(1)


async def _async_show_config(key: Optional[str]) -> dict[str, str]:
    """Async helper to load and show configuration."""
    config_loader = ConfigLoader()

    try:
        # Try to load with validation first
        config = await config_loader.load_config(use_defaults=True, use_environment=True)
    except ValueError:
        # If validation fails, load raw configuration for display
        config = {}

        # Load defaults
        if hasattr(config_loader, "_load_defaults"):
            defaults = await config_loader._load_defaults()
            config.update(defaults)

        # Load from environment
        if hasattr(config_loader, "load_from_environment"):
            env_config = await config_loader.load_from_environment()
            config.update(env_config)

        # If that doesn't work, provide a basic fallback
        if not config:
            config = {
                "DATABASE_URL": "postgresql://ptt_user:password@localhost:5432/ptt_crawler",
                "REDIS_URL": "redis://localhost:6379",
                "FIRECRAWL_API_URL": "http://localhost:3002",
                "FIRECRAWL_API_KEY": "",
                "CRAWL_RATE_LIMIT": "60",
                "CRAWL_REQUEST_DELAY": "1.5",
                "CRAWL_MAX_RETRIES": "3",
                "CRAWL_TIMEOUT": "30",
            }

    if key:
        # Return just the specific key if found
        return {key: config.get(key, "")} if key in config else {}
    else:
        # Return all configuration
        return config


async def _async_set_config(key: str, value: str) -> bool:
    """Async helper to set configuration value."""
    # Load current configuration to get database connection
    config_loader = ConfigLoader()
    config = await config_loader.load_config(use_defaults=True, use_environment=True)

    # Initialize repository
    config_repository = ConfigRepository(
        connection_string=config.get(
            "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
        )
    )

    try:
        # Validate and set the configuration
        success = await config_repository.set_config(key, value)
        return success
    finally:
        await config_repository.close()


async def _async_reset_config(key: Optional[str]) -> bool:
    """Async helper to reset configuration to defaults."""
    # Load current configuration to get database connection
    config_loader = ConfigLoader()
    config = await config_loader.load_config(use_defaults=True, use_environment=True)

    # Initialize repository
    config_repository = ConfigRepository(
        connection_string=config.get(
            "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
        )
    )

    try:
        if key:
            # Reset specific key to default
            success = await config_repository.reset_config(key)
        else:
            # Reset all configurations to defaults
            success = await config_repository.reset_all_config()

        return success
    finally:
        await config_repository.close()


# Add test configuration command for debugging
@config.command()
def test():
    """Test configuration system connectivity."""
    safe_echo("[CONFIG] Testing configuration system...")

    try:
        result = asyncio.run(_async_test_config())

        if result["database_connection"]:
            safe_echo("✅ Database connection: OK")
        else:
            safe_echo("❌ Database connection: FAILED")

        if result["config_loaded"]:
            safe_echo(f"✅ Configuration loaded: {result['config_count']} entries")
        else:
            safe_echo("❌ Configuration loading: FAILED")

        safe_echo("\nTest completed")

    except Exception as e:
        safe_echo(f"[ERROR] Configuration test failed: {e!s}")
        logger.error(f"Config test command failed: {e}")
        raise typer.Exit(1)


async def _async_test_config() -> dict[str, Any]:
    """Test configuration system components."""
    result = {"database_connection": False, "config_loaded": False, "config_count": 0}

    try:
        # Test configuration loading
        config_loader = ConfigLoader()
        config = await config_loader.load_config(use_defaults=True, use_environment=True)
        result["config_loaded"] = True
        result["config_count"] = len(config)

        # Test database connection for config repository
        config_repository = ConfigRepository(
            connection_string=config.get(
                "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
            )
        )

        try:
            # Try a simple operation
            await config_repository.get_config("test.connection")
            result["database_connection"] = True
        except:
            # Database might not be initialized, which is expected
            result["database_connection"] = False
        finally:
            await config_repository.close()

    except Exception as e:
        logger.debug(f"Config test error: {e}")

    return result
