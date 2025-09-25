"""Status command implementation."""
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional

import typer

from ..database.article_repository import ArticleRepository
from ..lib.config_loader import ConfigLoader
from ..lib.console import safe_echo
from ..lib.redis_client import RedisClient
from ..services.state_service import StateService

logger = logging.getLogger(__name__)


def status(
    board: Optional[str] = typer.Argument(None, help="Query specific board status"),
    format: str = typer.Option("table", "--format", help="Output format [table|json|yaml]"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed status information"),
):
    """View system and crawl status."""
    if board:
        safe_echo(f"[STATUS] Query board status: {board}")
    else:
        safe_echo("[STATUS] Query system status")

    try:
        # Run the async status check
        status_data = asyncio.run(_async_status(board, detailed))

        # Display results based on format
        if format == "json":
            safe_echo(json.dumps(status_data, indent=2, ensure_ascii=False, default=str))
        elif format == "yaml":
            _display_yaml_status(status_data)
        else:  # table format (default)
            _display_table_status(status_data, board, detailed)

    except Exception as e:
        safe_echo(f"[ERROR] Status query failed: {e!s}")
        logger.error(f"Status command failed: {e}")
        raise typer.Exit(1)


async def _async_status(board: Optional[str], detailed: bool) -> dict[str, Any]:
    """Async helper function to gather status information."""
    # Load configuration
    config_loader = ConfigLoader()
    config = await config_loader.load_config(use_defaults=True, use_environment=True)

    status_data = {
        "timestamp": datetime.now().isoformat(),
        "system": await _check_system_status(config),
        "services": await _check_services_status(config),
    }

    if board:
        status_data["board"] = await _check_board_status(board, config)

    if detailed:
        status_data["details"] = await _gather_detailed_info(config)

    return status_data


async def _check_system_status(config: dict[str, str]) -> dict[str, Any]:
    """Check basic system status."""
    from pathlib import Path

    import psutil

    project_root = Path(__file__).parent.parent.parent

    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "memory_usage": {
            "used_percent": psutil.virtual_memory().percent,
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        },
        "disk_usage": {
            "used_percent": round(
                psutil.disk_usage(str(project_root)).used
                / psutil.disk_usage(str(project_root)).total
                * 100,
                2,
            ),
            "free_gb": round(psutil.disk_usage(str(project_root)).free / (1024**3), 2),
        },
        "project_root": str(project_root),
    }


async def _check_services_status(config: dict[str, str]) -> dict[str, Any]:
    """Check external services status."""
    services = {}

    # Check Redis
    redis_client = None
    try:
        redis_client = RedisClient(
            url=config.get("REDIS_URL", "redis://localhost:6379"), retry_attempts=1, retry_delay=0.5
        )
        redis_health = await redis_client.health_check()
        services["redis"] = {
            "status": redis_health.get("status", "unknown"),
            "url": config.get("REDIS_URL", "redis://localhost:6379"),
            "details": redis_health,
        }
    except Exception as e:
        services["redis"] = {
            "status": "error",
            "url": config.get("REDIS_URL", "redis://localhost:6379"),
            "error": str(e),
        }
    finally:
        if redis_client:
            await redis_client.close()

    # Check Database
    article_repository = None
    try:
        article_repository = ArticleRepository(
            connection_string=config.get(
                "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
            )
        )
        db_healthy = await article_repository.health_check()
        services["database"] = {
            "status": "healthy" if db_healthy else "error",
            "url": _mask_password(config.get("DATABASE_URL", "")),
        }

        if db_healthy:
            # Get database statistics
            stats = await article_repository.get_database_stats()
            services["database"]["stats"] = stats

    except Exception as e:
        services["database"] = {
            "status": "error",
            "url": _mask_password(config.get("DATABASE_URL", "")),
            "error": str(e),
        }
    finally:
        if article_repository:
            await article_repository.close()

    # Check Firecrawl API
    try:
        import aiohttp

        api_url = config.get("FIRECRAWL_API_URL", "http://localhost:3002")
        health_endpoint = f"{api_url}/health"

        async with aiohttp.ClientSession() as session:
            async with session.get(health_endpoint, timeout=5) as response:
                if response.status == 200:
                    services["firecrawl"] = {
                        "status": "healthy",
                        "url": api_url,
                        "status_code": response.status,
                    }
                else:
                    services["firecrawl"] = {
                        "status": "error",
                        "url": api_url,
                        "status_code": response.status,
                    }
    except Exception as e:
        services["firecrawl"] = {
            "status": "error",
            "url": config.get("FIRECRAWL_API_URL", "http://localhost:3002"),
            "error": str(e),
        }

    return services


async def _check_board_status(board: str, config: dict[str, str]) -> dict[str, Any]:
    """Check specific board crawl status."""
    redis_client = None
    state_service = None
    article_repository = None

    try:
        # Initialize services
        redis_client = RedisClient(
            url=config.get("REDIS_URL", "redis://localhost:6379"), retry_attempts=1, retry_delay=0.5
        )
        state_service = StateService(redis_client=redis_client)
        article_repository = ArticleRepository(
            connection_string=config.get(
                "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
            )
        )

        # Get board state
        board_state = await state_service.get_board_state(board)
        board_info = {
            "board": board,
            "last_crawl": None,
            "total_articles": 0,
            "last_page": 0,
            "status": "never_crawled",
        }

        if board_state:
            board_info.update(
                {
                    "last_crawl": board_state.last_crawl_time.isoformat()
                    if board_state.last_crawl_time
                    else None,
                    "total_articles": board_state.total_articles,
                    "last_page": board_state.last_page_crawled,
                    "status": board_state.status.value if board_state.status else "unknown",
                    "success_rate": board_state.success_rate,
                }
            )

        # Get article count from database
        try:
            db_count = await article_repository.count_articles_by_board(board)
            board_info["database_articles"] = db_count
        except:
            board_info["database_articles"] = 0

        return board_info

    except Exception as e:
        return {"board": board, "status": "error", "error": str(e)}
    finally:
        if redis_client:
            await redis_client.close()
        if article_repository:
            await article_repository.close()


async def _gather_detailed_info(config: dict[str, str]) -> dict[str, Any]:
    """Gather detailed system information."""
    from pathlib import Path

    import psutil

    project_root = Path(__file__).parent.parent.parent

    # Log files info
    log_dir = project_root / "logs"
    log_files = []
    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            stat = log_file.stat()
            log_files.append(
                {
                    "name": log_file.name,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

    return {
        "process": {
            "pid": psutil.Process().pid,
            "memory_mb": round(psutil.Process().memory_info().rss / (1024 * 1024), 2),
            "cpu_percent": psutil.Process().cpu_percent(),
        },
        "log_files": log_files,
        "configuration": {
            key: "***" if "password" in key.lower() or "key" in key.lower() else value
            for key, value in config.items()
        },
    }


def _display_table_status(status_data: dict[str, Any], board: Optional[str], detailed: bool):
    """Display status in table format."""
    safe_echo("\n" + "=" * 60)
    safe_echo("🏥 PTT Stock 爬蟲系統狀態報告")
    safe_echo("=" * 60)
    safe_echo(f"檢查時間: {status_data['timestamp']}")

    # System status
    safe_echo("\n📊 系統狀態:")
    system = status_data["system"]
    safe_echo(f"  Python 版本: {system['python_version']}")
    safe_echo(
        f"  記憶體使用: {system['memory_usage']['used_percent']:.1f}% (可用: {system['memory_usage']['available_gb']:.1f} GB)"
    )
    safe_echo(
        f"  磁碟使用: {system['disk_usage']['used_percent']:.1f}% (可用: {system['disk_usage']['free_gb']:.1f} GB)"
    )

    # Services status
    safe_echo("\n🔧 外部服務:")
    for service_name, service_info in status_data["services"].items():
        status_icon = "✅" if service_info["status"] == "healthy" else "❌"
        safe_echo(f"  {status_icon} {service_name.upper()}: {service_info['status']}")

        if service_info["status"] != "healthy" and "error" in service_info:
            safe_echo(f"    錯誤: {service_info['error']}")
        elif service_name == "database" and "stats" in service_info:
            stats = service_info["stats"]
            safe_echo(f"    文章總數: {stats.get('total_articles', 0)}")

    # Board specific status
    if board and "board" in status_data:
        safe_echo(f"\n📋 {board} 板狀態:")
        board_info = status_data["board"]
        safe_echo(f"  爬取狀態: {board_info['status']}")
        safe_echo(f"  最後爬取: {board_info['last_crawl'] or '從未爬取'}")
        safe_echo(f"  文章數量: {board_info.get('database_articles', 0)} 篇")
        if "success_rate" in board_info:
            safe_echo(f"  成功率: {board_info['success_rate']:.1%}")

    # Detailed information
    if detailed and "details" in status_data:
        details = status_data["details"]
        safe_echo("\n🔍 詳細資訊:")
        safe_echo(f"  程序 PID: {details['process']['pid']}")
        safe_echo(f"  記憶體使用: {details['process']['memory_mb']:.1f} MB")

        if details["log_files"]:
            safe_echo("  日誌檔案:")
            for log_file in details["log_files"]:
                safe_echo(f"    - {log_file['name']}: {log_file['size_mb']:.1f} MB")

    safe_echo("=" * 60)


def _display_yaml_status(status_data: dict[str, Any]):
    """Display status in YAML-like format."""

    def _print_dict(data, indent=0):
        for key, value in data.items():
            if isinstance(value, dict):
                safe_echo("  " * indent + f"{key}:")
                _print_dict(value, indent + 1)
            else:
                safe_echo("  " * indent + f"{key}: {value}")

    _print_dict(status_data)


def _mask_password(connection_string: str) -> str:
    """Mask password in connection string."""
    import re

    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", connection_string)
