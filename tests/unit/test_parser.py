"""Unit tests for parser service.

Test PTT content parsing logic for articles and board pages.
"""
import pytest
from datetime import datetime
from typing import Dict, Any

from src.services.parser_service import ParserService


class TestParserService:
    """Test PTT content parsing functionality."""

    @pytest.fixture
    def parser_service(self) -> ParserService:
        """Create parser service instance."""
        return ParserService()

    @pytest.fixture
    def sample_article_response(self) -> Dict[str, Any]:
        """Sample Firecrawl API response for article parsing."""
        return {
            "success": True,
            "data": {
                "markdown": """# [心得] 今日投資心得分享

作者: test_user
時間: Mon Sep 25 10:30:00 2024

今天的市場表現還不錯，台積電上漲了2%。
我覺得這個趨勢可能會持續一段時間。

建議大家可以考慮逢低買進。

※ 發信站: 批踢踢實業坊(ptt.cc)
※ 文章網址: https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html

推 user1: 感謝分享
→ user2: 同意這個觀點
噓 user3: 不同意""",
                "metadata": {
                    "title": "[心得] 今日投資心得分享",
                    "author": "test_user",
                    "publishTime": "Mon Sep 25 10:30:00 2024",
                    "board": "Stock",
                }
            }
        }

    @pytest.fixture
    def sample_board_response(self) -> Dict[str, Any]:
        """Sample board page response."""
        return {
            "success": True,
            "data": {
                "markdown": """# 批踢踢實業坊 › Stock

1. [心得] 今日投資心得分享 test_user
2. [標的] 2330 台積電分析報告 analyst_user
3. [請益] 新手投資建議求助 newbie_user

[心得] 投資心得文章
https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html

[標的] 股票分析文章
https://www.ptt.cc/bbs/Stock/M.9876543210.A.456.html""",
                "links": [
                    {
                        "text": "[心得] 投資心得文章",
                        "url": "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
                    },
                    {
                        "text": "[標的] 股票分析文章",
                        "url": "https://www.ptt.cc/bbs/Stock/M.9876543210.A.456.html"
                    }
                ]
            }
        }

    async def test_parse_article_success(self, parser_service: ParserService, sample_article_response: Dict[str, Any]):
        """Test successful article parsing."""
        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        result = await parser_service.parse_article(sample_article_response, url)

        assert result is not None
        assert result["title"] == "[心得] 今日投資心得分享"
        assert result["author"] == "test_user"
        assert result["category"] == "心得"
        assert result["board"] == "Stock"
        assert "今天的市場表現" in result["content"]
        assert "※ 發信站" not in result["content"]  # Should be cleaned
        assert "推 user1" not in result["content"]  # Comments should be removed

    async def test_parse_article_empty_content(self, parser_service: ParserService):
        """Test parsing article with empty content."""
        empty_response = {
            "success": True,
            "data": {
                "markdown": "",
                "metadata": {}
            }
        }

        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        result = await parser_service.parse_article(empty_response, url)

        assert result is None

    async def test_parse_article_missing_required_fields(self, parser_service: ParserService):
        """Test parsing article missing title or author."""
        incomplete_response = {
            "success": True,
            "data": {
                "markdown": "Some content without proper title or author",
                "metadata": {}
            }
        }

        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        result = await parser_service.parse_article(incomplete_response, url)

        assert result is None

    def test_extract_board_from_url(self, parser_service: ParserService):
        """Test board extraction from URLs."""
        test_cases = [
            ("https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html", "Stock"),
            ("https://www.ptt.cc/bbs/Gossiping/M.9876543210.A.456.html", "Gossiping"),
            ("https://www.ptt.cc/bbs/Tech_Job/M.1111111111.A.789.html", "Tech_Job"),
            ("invalid_url", "Unknown"),
        ]

        for url, expected_board in test_cases:
            board = parser_service._extract_board_from_url(url)
            assert board == expected_board

    def test_parse_title_with_category(self, parser_service: ParserService):
        """Test title parsing with category extraction."""
        test_cases = [
            ("# [心得] 投資心得分享", {"title": "[心得] 投資心得分享", "category": "心得"}),
            ("標題：[標的] 2330 台積電分析", {"title": "[標的] 2330 台積電分析", "category": "標的"}),
            ("Re: [請益] 新手問題", {"title": "Re: [請益] 新手問題", "category": "請益"}),
            ("沒有分類的標題", {"title": "沒有分類的標題", "category": None}),
        ]

        for content, expected in test_cases:
            result = parser_service._parse_title(content, {})
            if expected["title"]:
                assert result["title"] == expected["title"]
                assert result["category"] == expected["category"]
            else:
                assert result is None

    def test_extract_category_from_title(self, parser_service: ParserService):
        """Test category extraction from titles."""
        test_cases = [
            ("[心得] 投資分享", "心得"),
            ("[標的] 股票分析", "標的"),
            ("[請益] 求助問題", "請益"),
            ("[閒聊] 隨便聊聊", "閒聊"),
            ("[新聞] 重要消息", "新聞"),
            ("沒有分類", None),
            ("[自定義分類] 測試", "自定義分類"),
        ]

        for title, expected_category in test_cases:
            category = parser_service._extract_category_from_title(title)
            assert category == expected_category

    def test_parse_author_patterns(self, parser_service: ParserService):
        """Test author parsing with different patterns."""
        test_cases = [
            ("作者: test_user", "test_user"),
            ("Author: english_user", "english_user"),
            ("作者：user_with_info (學生)", "user_with_info"),
            ("※ 發信站: 批踢踢實業坊(ptt.cc), 來自: author_from_station", "author_from_station"),
            ("no author info", None),
        ]

        for content, expected_author in test_cases:
            author = parser_service._parse_author(content, {})
            if expected_author:
                assert author == expected_author

    def test_parse_time_string_formats(self, parser_service: ParserService):
        """Test parsing different time string formats."""
        test_cases = [
            ("Mon Sep 25 10:30:00 2024", True),
            ("2024/09/25 10:30:00", True),
            ("09/25/2024 10:30:00", True),
            ("2024-09-25 10:30:00", True),
            ("25/09/2024 10:30", True),
            ("2024/09/25", True),
            ("invalid_time", False),
            ("", False),
        ]

        for time_str, should_parse in test_cases:
            result = parser_service._parse_time_string(time_str)
            if should_parse:
                assert isinstance(result, datetime)
            else:
                assert result is None

    def test_clean_article_content(self, parser_service: ParserService):
        """Test article content cleaning."""
        dirty_content = """文章正文內容

這裡是正常內容。

※ 發信站: 批踢踢實業坊(ptt.cc)
※ 文章網址: https://example.com
※ 編輯: user123

推 user1: 推推
→ user2: 同意
噓 user3: 不同意
09/25 10:30

更多正常內容。"""

        cleaned = parser_service._clean_article_content(dirty_content)

        # Should remove system messages
        assert "※ 發信站" not in cleaned
        assert "※ 文章網址" not in cleaned
        assert "※ 編輯" not in cleaned

        # Should remove comments
        assert "推 user1" not in cleaned
        assert "→ user2" not in cleaned
        assert "噓 user3" not in cleaned

        # Should keep normal content
        assert "文章正文內容" in cleaned
        assert "這裡是正常內容" in cleaned
        assert "更多正常內容" in cleaned

        # Should normalize whitespace
        assert not cleaned.startswith(" ")
        assert not cleaned.endswith(" ")

    def test_parse_board_page(self, parser_service: ParserService, sample_board_response: Dict[str, Any]):
        """Test board page parsing for article links."""
        articles = parser_service.parse_board_page(sample_board_response)

        assert len(articles) >= 2

        # Check first article
        first_article = articles[0]
        assert "url" in first_article
        assert "title" in first_article
        assert "https://www.ptt.cc/bbs/Stock/" in first_article["url"]
        assert first_article["title"]

    def test_parse_board_page_empty(self, parser_service: ParserService):
        """Test parsing empty board page."""
        empty_response = {
            "success": True,
            "data": {
                "markdown": "",
                "links": []
            }
        }

        articles = parser_service.parse_board_page(empty_response)
        assert articles == []

    def test_validate_article_data_valid(self, parser_service: ParserService):
        """Test article data validation with valid data."""
        valid_data = {
            "title": "[心得] 測試標題",
            "author": "test_user",
            "content": "這是有足夠長度的文章內容，用來測試驗證功能是否正常運作。",
            "category": "心得",
            "board": "Stock",
            "publish_date": datetime.now(),
        }

        assert parser_service.validate_article_data(valid_data) is True

    def test_validate_article_data_invalid(self, parser_service: ParserService):
        """Test article data validation with invalid data."""
        # Missing required field
        invalid_data_missing = {
            "title": "[心得] 測試標題",
            "author": "",  # Empty author
            "content": "內容",
        }
        assert parser_service.validate_article_data(invalid_data_missing) is False

        # Content too short
        invalid_data_short = {
            "title": "[心得] 測試標題",
            "author": "test_user",
            "content": "短",  # Too short
        }
        assert parser_service.validate_article_data(invalid_data_short) is False

        # Empty title
        invalid_data_title = {
            "title": "",  # Empty title
            "author": "test_user",
            "content": "這是有足夠長度的內容",
        }
        assert parser_service.validate_article_data(invalid_data_title) is False

    def test_extract_keywords(self, parser_service: ParserService):
        """Test keyword extraction from content."""
        content = """這是一篇關於投資股票的文章。
        台積電是很好的投資標的，建議大家可以考慮投資台積電。
        股票市場最近表現不錯，投資機會很多。
        投資需要謹慎，建議做好風險控制。"""

        keywords = parser_service.extract_keywords(content, max_keywords=5)

        assert len(keywords) <= 5
        assert "投資" in keywords  # Should be high frequency
        assert "台積電" in keywords
        assert "股票" in keywords

        # Test with empty content
        empty_keywords = parser_service.extract_keywords("", max_keywords=5)
        assert empty_keywords == []

    def test_get_content_summary(self, parser_service: ParserService):
        """Test content summary generation."""
        # Long content
        long_content = "這是一個很長的文章內容。" * 50
        summary = parser_service.get_content_summary(long_content, max_length=50)

        assert len(summary) <= 53  # 50 + "..."
        assert summary.endswith("...")

        # Short content
        short_content = "這是短內容"
        summary = parser_service.get_content_summary(short_content, max_length=50)
        assert summary == short_content

        # Content with sentence breaks
        sentence_content = "第一句話。第二句話。第三句話很長很長很長很長很長很長很長。"
        summary = parser_service.get_content_summary(sentence_content, max_length=20)
        assert summary.endswith("。") or summary.endswith("...")

        # Empty content
        empty_summary = parser_service.get_content_summary("", max_length=50)
        assert empty_summary == ""

    def test_parser_error_handling(self, parser_service: ParserService):
        """Test parser error handling with malformed data."""
        # Malformed response structure
        malformed_response = {
            "success": True,
            "invalid_structure": "test"
        }

        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        result = await parser_service.parse_article(malformed_response, url)
        assert result is None

        # Response with success=False
        failed_response = {
            "success": False,
            "data": {
                "markdown": "content",
                "metadata": {}
            }
        }

        result = await parser_service.parse_article(failed_response, url)
        # Should still try to parse if data exists

    def test_parse_special_characters(self, parser_service: ParserService):
        """Test parsing content with special characters."""
        special_content = """標題：[心得] 特殊字符測試 🚀📈

作者: test_user
時間: 2024/09/25 10:30:00

這是包含特殊字符的內容：
• 項目一
• 項目二 ★★★
→ 箭頭符號
※ 特殊標記

中文字符：你好世界
英文字符：Hello World
數字：12345
符號：!@#$%^&*()"""

        response = {
            "success": True,
            "data": {
                "markdown": special_content,
                "metadata": {}
            }
        }

        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        result = await parser_service.parse_article(response, url)

        assert result is not None
        assert "你好世界" in result["content"]
        assert "Hello World" in result["content"]
        assert result["author"] == "test_user"

    async def test_parse_article_with_metadata_priority(self, parser_service: ParserService):
        """Test that metadata has priority over content parsing."""
        response = {
            "success": True,
            "data": {
                "markdown": "標題：[錯誤] 這是錯誤的標題\n作者: wrong_author",
                "metadata": {
                    "title": "[心得] 正確的標題",
                    "author": "correct_author",
                    "publishTime": "2024/09/25 10:30:00"
                }
            }
        }

        url = "https://www.ptt.cc/bbs/Stock/M.1234567890.A.123.html"
        result = await parser_service.parse_article(response, url)

        assert result is not None
        # Should use metadata values
        assert result["title"] == "[心得] 正確的標題"
        assert result["author"] == "correct_author"
        assert result["category"] == "心得"