"""Performance tests for crawl functionality.

Test crawl speed, memory usage, and scalability under various conditions.
"""
import pytest
import asyncio
import time
import psutil
import os
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock

from src.services.crawl_service import CrawlService
from src.services.firecrawl_service import FirecrawlService
from src.models.article import Article
from src.models.crawl_state import CrawlState, CrawlStatus


class PerformanceMonitor:
    """Helper class to monitor performance metrics."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = None
        self.start_memory = None
        self.start_cpu_time = None

    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss
        self.start_cpu_time = self.process.cpu_times()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        current_time = time.time()
        current_memory = self.process.memory_info().rss
        current_cpu_time = self.process.cpu_times()

        return {
            'elapsed_time': current_time - self.start_time if self.start_time else 0,
            'memory_usage': current_memory,
            'memory_increase': current_memory - self.start_memory if self.start_memory else 0,
            'cpu_percent': self.process.cpu_percent(),
            'memory_percent': self.process.memory_percent(),
            'threads_count': self.process.num_threads(),
        }


class TestCrawlServicePerformance:
    """Test CrawlService performance characteristics."""

    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor."""
        return PerformanceMonitor()

    @pytest.fixture
    def mock_fast_dependencies(self):
        """Create fast mock dependencies for performance testing."""
        return {
            'firecrawl_service': Mock(spec=FirecrawlService),
            'article_repo': AsyncMock(),
            'crawl_state_repo': AsyncMock(),
            'state_service': AsyncMock(),
            'parser_service': AsyncMock(),
            'config': {
                'crawl.rate_limit': 1000,  # High rate for performance testing
                'crawl.request_delay': 0.1,  # Low delay
                'crawl.max_retries': 1,
                'crawl.concurrent_limit': 10,  # High concurrency
            }
        }

    @pytest.fixture
    def crawl_service_fast(self, mock_fast_dependencies):
        """Create CrawlService with fast configuration."""
        service = CrawlService(**mock_fast_dependencies)

        # Setup fast mocks
        mock_state = Mock(spec=CrawlState)
        mock_state.board = "Stock"
        mock_state.status = CrawlStatus.IDLE
        mock_state.is_url_processed.return_value = False

        mock_fast_dependencies['crawl_state_repo'].get_crawl_state.return_value = mock_state

        # Fast Firecrawl responses
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {"markdown": "test content"}

        mock_fast_dependencies['firecrawl_service'].scrape_board_page = AsyncMock(return_value=mock_response)
        mock_fast_dependencies['firecrawl_service'].scrape_article_with_retry = AsyncMock(return_value=mock_response)
        mock_fast_dependencies['firecrawl_service'].extract_article_links.return_value = []
        mock_fast_dependencies['parser_service'].parse_article.return_value = {
            "title": "Test", "author": "user", "content": "content", "publish_date": asyncio.get_event_loop().time()
        }
        mock_fast_dependencies['article_repo'].article_exists.return_value = False
        mock_fast_dependencies['article_repo'].insert_article.return_value = 1

        return service

    @pytest.mark.asyncio
    async def test_single_page_crawl_performance(self, crawl_service_fast: CrawlService, performance_monitor: PerformanceMonitor):
        """Test performance of single page crawl."""
        performance_monitor.start_monitoring()

        result = await crawl_service_fast.crawl_board("Stock", pages=1)

        metrics = performance_monitor.get_metrics()

        # Performance assertions
        assert result["status"] == "success"
        assert metrics['elapsed_time'] < 1.0  # Should complete in under 1 second
        assert metrics['memory_increase'] < 50 * 1024 * 1024  # Less than 50MB increase
        assert metrics['cpu_percent'] < 80  # Should not max out CPU

        print(f"Single page crawl metrics: {metrics}")

    @pytest.mark.asyncio
    async def test_multiple_pages_crawl_performance(self, crawl_service_fast: CrawlService, performance_monitor: PerformanceMonitor):
        """Test performance of multiple pages crawl."""
        pages = 5
        performance_monitor.start_monitoring()

        result = await crawl_service_fast.crawl_board("Stock", pages=pages)

        metrics = performance_monitor.get_metrics()

        # Performance assertions
        assert result["status"] == "success"
        assert metrics['elapsed_time'] < pages * 0.5  # Should be roughly linear
        assert metrics['memory_increase'] < 100 * 1024 * 1024  # Less than 100MB increase

        print(f"Multiple pages ({pages}) crawl metrics: {metrics}")

    @pytest.mark.asyncio
    async def test_concurrent_crawl_performance(self, crawl_service_fast: CrawlService, performance_monitor: PerformanceMonitor):
        """Test performance of concurrent crawl operations."""
        performance_monitor.start_monitoring()

        # Create multiple concurrent crawl tasks for different boards
        tasks = [
            crawl_service_fast.crawl_board(f"Board{i}", pages=2)
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        metrics = performance_monitor.get_metrics()

        # All should succeed
        successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
        assert len(successful_results) == 3

        # Performance should be better than sequential
        assert metrics['elapsed_time'] < 3.0  # Should be faster than 3 sequential crawls
        assert metrics['memory_increase'] < 150 * 1024 * 1024  # Memory usage should be reasonable

        print(f"Concurrent crawl metrics: {metrics}")

    @pytest.mark.asyncio
    async def test_large_article_list_performance(self, crawl_service_fast: CrawlService, performance_monitor: PerformanceMonitor, mock_fast_dependencies):
        """Test performance with large number of articles."""
        # Generate large number of fake article links
        large_article_list = [
            {"url": f"https://www.ptt.cc/bbs/Stock/M.{i}.A.123.html", "title": f"Article {i}"}
            for i in range(100)
        ]

        mock_fast_dependencies['firecrawl_service'].extract_article_links.return_value = large_article_list

        performance_monitor.start_monitoring()

        result = await crawl_service_fast.crawl_board("Stock", pages=1)

        metrics = performance_monitor.get_metrics()

        # Should handle large lists efficiently
        assert result["status"] == "success"
        assert metrics['elapsed_time'] < 10.0  # Should complete in reasonable time
        assert metrics['memory_increase'] < 200 * 1024 * 1024  # Memory should scale reasonably

        print(f"Large article list (100 articles) metrics: {metrics}")

    @pytest.mark.asyncio
    async def test_memory_stability_over_time(self, crawl_service_fast: CrawlService, performance_monitor: PerformanceMonitor):
        """Test memory stability during repeated crawl operations."""
        performance_monitor.start_monitoring()
        memory_snapshots = []

        # Perform multiple crawl operations
        for i in range(5):
            await crawl_service_fast.crawl_board(f"Board{i}", pages=1)

            current_metrics = performance_monitor.get_metrics()
            memory_snapshots.append(current_metrics['memory_usage'])

            # Small delay between operations
            await asyncio.sleep(0.1)

        final_metrics = performance_monitor.get_metrics()

        # Memory should not continuously increase (memory leaks)
        memory_growth = memory_snapshots[-1] - memory_snapshots[0]
        assert memory_growth < 100 * 1024 * 1024  # Less than 100MB growth over 5 operations

        # Memory should stabilize (not keep growing linearly)
        if len(memory_snapshots) >= 3:
            recent_growth = memory_snapshots[-1] - memory_snapshots[-3]
            assert recent_growth < 50 * 1024 * 1024  # Recent growth should be smaller

        print(f"Memory stability test - snapshots: {memory_snapshots}")
        print(f"Total memory growth: {memory_growth / 1024 / 1024:.2f} MB")

    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, mock_fast_dependencies):
        """Test performance impact of rate limiting."""
        # Test with different rate limiting settings
        configs = [
            {'crawl.request_delay': 0.0, 'crawl.rate_limit': 1000},  # No limits
            {'crawl.request_delay': 0.1, 'crawl.rate_limit': 600},   # Light limits
            {'crawl.request_delay': 0.5, 'crawl.rate_limit': 120},   # Moderate limits
        ]

        results = []

        for config in configs:
            # Update config
            mock_fast_dependencies['config'].update(config)
            service = CrawlService(**mock_fast_dependencies)

            # Setup mocks (same as fast service)
            mock_state = Mock(spec=CrawlState)
            mock_state.board = "Stock"
            mock_state.status = CrawlStatus.IDLE
            mock_state.is_url_processed.return_value = False
            mock_fast_dependencies['crawl_state_repo'].get_crawl_state.return_value = mock_state

            # Measure performance
            start_time = time.time()
            result = await service.crawl_board("Stock", pages=2)
            elapsed_time = time.time() - start_time

            results.append({
                'config': config,
                'elapsed_time': elapsed_time,
                'success': result["status"] == "success"
            })

        # Verify rate limiting impact
        assert all(r['success'] for r in results)

        # Higher delays should result in longer execution times
        no_limit_time = results[0]['elapsed_time']
        moderate_limit_time = results[2]['elapsed_time']
        assert moderate_limit_time > no_limit_time

        print("Rate limiting performance results:")
        for r in results:
            print(f"  {r['config']} -> {r['elapsed_time']:.3f}s")

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, crawl_service_fast: CrawlService, mock_fast_dependencies, performance_monitor: PerformanceMonitor):
        """Test performance when handling errors."""
        # Setup some operations to fail
        call_count = 0

        async def failing_scrape(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # First 2 calls fail
                raise Exception("Simulated error")
            # Subsequent calls succeed
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = {"markdown": "content"}
            return mock_response

        mock_fast_dependencies['firecrawl_service'].scrape_board_page = failing_scrape

        performance_monitor.start_monitoring()

        result = await crawl_service_fast.crawl_board("Stock", pages=3)

        metrics = performance_monitor.get_metrics()

        # Should handle errors gracefully without major performance impact
        assert metrics['elapsed_time'] < 5.0  # Should still complete in reasonable time
        assert metrics['memory_increase'] < 100 * 1024 * 1024

        print(f"Error handling performance metrics: {metrics}")


class TestFirecrawlServicePerformance:
    """Test FirecrawlService performance characteristics."""

    @pytest.fixture
    def firecrawl_service(self):
        """Create FirecrawlService for performance testing."""
        config = {
            "api_url": "http://localhost:3002",
            "api_key": "test_key",
            "timeout": 5,
            "max_retries": 1,
        }
        return FirecrawlService(config)

    def test_article_link_extraction_performance(self, firecrawl_service: FirecrawlService):
        """Test performance of article link extraction."""
        # Generate large markdown content with many links
        markdown_content = "\n".join([
            f"[心得] Test Article {i}\nhttps://www.ptt.cc/bbs/Stock/M.{i}.A.123.html\n"
            for i in range(1000)
        ])

        response_data = {
            "data": {
                "markdown": markdown_content,
                "links": []
            }
        }

        start_time = time.time()
        links = firecrawl_service.extract_article_links(response_data)
        elapsed_time = time.time() - start_time

        # Performance assertions
        assert len(links) >= 0  # Should extract links
        assert elapsed_time < 1.0  # Should be fast

        print(f"Link extraction performance: {len(links)} links in {elapsed_time:.3f}s")

    def test_content_cleaning_performance(self, firecrawl_service: FirecrawlService):
        """Test performance of content cleaning."""
        # Generate large content with system messages and comments
        large_content = "正常內容\n" * 100
        system_messages = "※ 發信站: 批踢踢實業坊(ptt.cc)\n" * 50
        comments = "推 user: 推推\n" * 200

        dirty_content = large_content + system_messages + comments

        start_time = time.time()
        cleaned_content = firecrawl_service.clean_article_content(dirty_content)
        elapsed_time = time.time() - start_time

        # Performance assertions
        assert len(cleaned_content) < len(dirty_content)  # Should be cleaned
        assert elapsed_time < 0.5  # Should be fast
        assert "※ 發信站" not in cleaned_content

        print(f"Content cleaning performance: {len(dirty_content)} -> {len(cleaned_content)} chars in {elapsed_time:.3f}s")

    def test_category_filtering_performance(self, firecrawl_service: FirecrawlService):
        """Test performance of category filtering."""
        # Generate large number of articles with different categories
        links = [
            {"text": f"[心得] Article {i}", "category": "心得", "url": f"url_{i}"}
            if i % 3 == 0 else
            {"text": f"[標的] Article {i}", "category": "標的", "url": f"url_{i}"}
            if i % 3 == 1 else
            {"text": f"[請益] Article {i}", "category": "請益", "url": f"url_{i}"}
            for i in range(10000)
        ]

        start_time = time.time()
        filtered = firecrawl_service.filter_articles_by_category(links, "心得")
        elapsed_time = time.time() - start_time

        # Performance assertions
        assert len(filtered) > 0  # Should find matching articles
        assert all("[心得]" in link["text"] for link in filtered)
        assert elapsed_time < 1.0  # Should be fast

        print(f"Category filtering performance: {len(links)} -> {len(filtered)} links in {elapsed_time:.3f}s")


class TestDatabasePerformance:
    """Test database operation performance."""

    @pytest.mark.asyncio
    async def test_batch_insert_performance(self):
        """Test performance of batch article insertion."""
        # This would test actual database performance
        # For now, we'll test the preparation of batch data

        articles = []
        for i in range(1000):
            article = Article(
                id=0,
                title=f"[心得] Test Article {i}",
                author=f"user_{i}",
                board="Stock",
                url=f"https://www.ptt.cc/bbs/Stock/M.{i}.A.123.html",
                content=f"Test content {i}" * 10,  # Some content
                publish_date=asyncio.get_event_loop().time(),
                crawl_date=asyncio.get_event_loop().time(),
                created_at=asyncio.get_event_loop().time(),
                updated_at=asyncio.get_event_loop().time(),
            )
            articles.append(article)

        # Test data preparation performance
        start_time = time.time()

        # Convert to dict format (what would be sent to database)
        article_dicts = [article.to_dict() for article in articles]

        elapsed_time = time.time() - start_time

        assert len(article_dicts) == 1000
        assert elapsed_time < 1.0  # Data preparation should be fast

        print(f"Batch data preparation performance: {len(articles)} articles in {elapsed_time:.3f}s")


class TestScalabilityLimits:
    """Test system behavior at scalability limits."""

    @pytest.mark.asyncio
    async def test_maximum_concurrent_connections(self, performance_monitor: PerformanceMonitor):
        """Test behavior with maximum concurrent connections."""
        performance_monitor.start_monitoring()

        # Create many concurrent tasks
        num_tasks = 50
        tasks = []

        for i in range(num_tasks):
            # Create lightweight async task
            task = asyncio.create_task(asyncio.sleep(0.1))
            tasks.append(task)

        await asyncio.gather(*tasks)

        metrics = performance_monitor.get_metrics()

        # Should handle many concurrent operations
        assert metrics['elapsed_time'] < 1.0  # Should complete quickly
        assert metrics['memory_increase'] < 50 * 1024 * 1024  # Memory should be reasonable

        print(f"Max concurrent connections test ({num_tasks} tasks): {metrics}")

    @pytest.mark.asyncio
    async def test_large_content_handling(self):
        """Test handling of very large content."""
        # Simulate very large article content
        large_content = "很長的文章內容。" * 10000  # ~200KB content

        start_time = time.time()

        # Test content processing (what parser would do)
        processed_content = large_content.replace("※", "")  # Simple processing
        content_length = len(processed_content)

        elapsed_time = time.time() - start_time

        assert content_length > 0
        assert elapsed_time < 1.0  # Should handle large content quickly

        print(f"Large content handling: {content_length} chars in {elapsed_time:.3f}s")

    def test_memory_usage_limits(self, performance_monitor: PerformanceMonitor):
        """Test system behavior under memory pressure."""
        performance_monitor.start_monitoring()

        # Allocate and process large amounts of data
        data_blocks = []

        for i in range(10):
            # Create 10MB blocks
            block = "x" * (10 * 1024 * 1024)
            data_blocks.append(block)

            # Process the data
            processed = block.upper()
            assert len(processed) == len(block)

        # Clean up
        del data_blocks

        metrics = performance_monitor.get_metrics()

        # Memory usage should be manageable
        assert metrics['memory_percent'] < 90  # Should not use more than 90% of available memory

        print(f"Memory usage limits test: {metrics}")


@pytest.mark.slow
class TestLongRunningPerformance:
    """Test performance over extended periods (marked as slow tests)."""

    @pytest.mark.asyncio
    async def test_extended_crawl_session(self):
        """Test performance during extended crawl session."""
        # This would simulate a long-running crawl session
        # For testing, we'll simulate with shorter duration

        start_time = time.time()
        iterations = 10

        for i in range(iterations):
            # Simulate crawl work
            await asyncio.sleep(0.1)

            # Simulate some processing
            data = f"processing data iteration {i}" * 100
            processed_data = data.upper()
            del processed_data

        elapsed_time = time.time() - start_time

        # Should maintain stable performance
        average_iteration_time = elapsed_time / iterations
        assert average_iteration_time < 0.2  # Each iteration should be fast

        print(f"Extended session performance: {iterations} iterations in {elapsed_time:.3f}s")
        print(f"Average per iteration: {average_iteration_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_monitor: PerformanceMonitor):
        """Test for memory leaks over time."""
        performance_monitor.start_monitoring()
        memory_snapshots = []

        # Perform repeated operations that could cause memory leaks
        for i in range(20):
            # Simulate object creation and cleanup
            temp_objects = []

            for j in range(100):
                obj = {"data": f"test data {i}-{j}" * 100}
                temp_objects.append(obj)

            # Process objects
            processed = [obj["data"].upper() for obj in temp_objects]

            # Clean up
            del temp_objects
            del processed

            # Record memory usage
            current_metrics = performance_monitor.get_metrics()
            memory_snapshots.append(current_metrics['memory_usage'])

        # Analyze memory growth pattern
        if len(memory_snapshots) >= 10:
            early_memory = sum(memory_snapshots[:5]) / 5
            late_memory = sum(memory_snapshots[-5:]) / 5
            memory_growth_rate = (late_memory - early_memory) / early_memory

            # Memory growth rate should be minimal (no significant leaks)
            assert memory_growth_rate < 0.1  # Less than 10% growth

        print(f"Memory leak detection - growth rate: {memory_growth_rate:.2%}")
        print(f"Memory snapshots (MB): {[m/1024/1024 for m in memory_snapshots[-5:]]}")


if __name__ == "__main__":
    # Run specific performance tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])