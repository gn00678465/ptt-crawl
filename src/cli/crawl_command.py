"""Crawl command implementation."""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import typer

from ..lib.console import safe_echo
from ..lib.config_loader import ConfigLoader
from ..lib.redis_client import RedisClient
from ..services.crawl_service import CrawlService
from ..services.state_service import StateService
from ..services.parser_service import ParserService
from ..database.article_repository import ArticleRepository

logger = logging.getLogger(__name__)


def crawl(
    board: str = typer.Argument("Stock", help="Target board name"),
    category: Optional[str] = typer.Option(
        None, "--category", help="Filter article category/keyword"
    ),
    pages: int = typer.Option(1, "--pages", min=1, max=50, help="Number of pages to crawl"),
    output: str = typer.Option("database", "--output", help="Output format [json|csv|database]"),
    output_file: Optional[Path] = typer.Option(None, "--output-file", help="Output file path"),
    force: bool = typer.Option(False, "--force", help="Force re-crawl, ignore processed state"),
    incremental: bool = typer.Option(
        True, "--incremental/--no-incremental", help="Use incremental crawling"
    ),
):
    """Crawl PTT board articles."""
    safe_echo(f"[CRAWL] Start crawling PTT {board} board")
    if category:
        safe_echo(f"[CRAWL] Filter category: {category}")
    safe_echo(f"[CRAWL] Crawl pages: {pages}")

    try:
        # Run the async crawl operation
        result = asyncio.run(_async_crawl(
            board=board,
            category=category,
            pages=pages,
            output=output,
            output_file=output_file,
            force=force,
            incremental=incremental
        ))

        # Display results
        safe_echo(f"[SUCCESS] Crawl completed successfully")
        safe_echo(f"[STATS] Articles processed: {result.get('articles_crawled', 0)}")
        safe_echo(f"[STATS] Articles saved: {result.get('articles_saved', 0)}")
        safe_echo(f"[STATS] Errors: {result.get('errors_count', 0)}")
        safe_echo(f"[STATS] Duration: {result.get('duration', 0):.2f} seconds")

        # Handle output file if specified
        if output_file and output != "database":
            safe_echo(f"[OUTPUT] Results saved to: {output_file}")

    except Exception as e:
        safe_echo(f"[ERROR] Crawl failed: {str(e)}")
        logger.error(f"Crawl command failed: {e}")
        raise typer.Exit(1)


async def _async_crawl(
    board: str,
    category: Optional[str],
    pages: int,
    output: str,
    output_file: Optional[Path],
    force: bool,
    incremental: bool
):
    """Async helper function to handle crawl operations."""
    # Load configuration
    config_loader = ConfigLoader()
    config = await config_loader.load_config(use_defaults=True, use_environment=True)

    # Initialize services
    redis_client = RedisClient(
        url=config.get("REDIS_URL", "redis://localhost:6379"),
        retry_attempts=3,
        retry_delay=1.0
    )

    state_service = StateService(redis_client=redis_client)
    parser_service = ParserService()

    article_repository = ArticleRepository(
        connection_string=config.get(
            "DATABASE_URL",
            "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
        )
    )

    crawl_service = CrawlService(
        state_service=state_service,
        parser_service=parser_service,
        article_repository=article_repository,
        firecrawl_api_url=config.get("FIRECRAWL_API_URL", "http://localhost:3002"),
        firecrawl_api_key=config.get("FIRECRAWL_API_KEY")
    )

    try:
        # Execute the crawl
        result = await crawl_service.crawl_board(
            board=board,
            category=category,
            pages=pages,
            incremental=incremental,
            force=force
        )

        # Handle output file if specified
        if output_file and output != "database":
            await _export_results(result, output, output_file, article_repository, board)

        return result

    finally:
        # Clean up resources
        if redis_client:
            await redis_client.close()
        if article_repository:
            await article_repository.close()


async def _export_results(result, output_format: str, output_file: Path, article_repository: ArticleRepository, board: str):
    """Export crawl results to file."""
    try:
        if output_format == "json":
            await _export_to_json(result, output_file, article_repository, board)
        elif output_format == "csv":
            await _export_to_csv(result, output_file, article_repository, board)
    except Exception as e:
        logger.error(f"Export failed: {e}")
        safe_echo(f"[WARNING] Export failed: {e}")


async def _export_to_json(result, output_file: Path, article_repository: ArticleRepository, board: str):
    """Export results to JSON file."""
    # Get recent articles for this board
    articles = await article_repository.get_articles_by_board(board=board, limit=result.get('articles_saved', 100))

    export_data = {
        "crawl_summary": {
            "board": board,
            "status": result.get("status"),
            "articles_crawled": result.get("articles_crawled", 0),
            "articles_saved": result.get("articles_saved", 0),
            "errors_count": result.get("errors_count", 0),
            "duration": result.get("duration", 0),
            "timestamp": result.get("start_time")
        },
        "articles": [
            {
                "id": article.id,
                "title": article.title,
                "author": article.author,
                "category": article.category,
                "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
                "publish_date": article.publish_date.isoformat() if article.publish_date else None,
                "crawl_date": article.crawl_date.isoformat() if article.crawl_date else None,
                "board": article.board,
                "url": article.url
            }
            for article in articles
        ]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)


async def _export_to_csv(result, output_file: Path, article_repository: ArticleRepository, board: str):
    """Export results to CSV file."""
    import csv

    # Get recent articles for this board
    articles = await article_repository.get_articles_by_board(board=board, limit=result.get('articles_saved', 100))

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'ID', 'Title', 'Author', 'Category', 'Board', 'URL',
            'Publish Date', 'Crawl Date', 'Content Length'
        ])

        # Write article data
        for article in articles:
            writer.writerow([
                article.id,
                article.title,
                article.author,
                article.category or '',
                article.board,
                article.url,
                article.publish_date.isoformat() if article.publish_date else '',
                article.crawl_date.isoformat() if article.crawl_date else '',
                len(article.content)
            ])
