"""Parser service implementation.

This module implements PTT article content parsing logic.
"""
import logging
import re
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ParserService:
    """PTT 文章內容解析服務."""

    def __init__(self):
        # 常用的 PTT 文章格式正則表達式
        self.title_patterns = [
            r"# \[(.*?)\] (.*?)(?:\n|$)",  # Markdown 格式標題
            r"標題[：:]\s*\[(.*?)\] (.*?)(?:\n|$)",  # 傳統格式
            r"^Re: \[(.*?)\] (.*?)$",  # 回覆格式
        ]

        self.author_patterns = [
            r"作者[：:]\s*([^\s\n\(]+)",  # 標準作者格式
            r"Author[：:]\s*([^\s\n\(]+)",  # 英文格式
            r"※ 發信站:.*?\(([^)]+)\)",  # 從發信站資訊提取
        ]

        self.time_patterns = [
            r"時間[：:]\s*([^\n]+)",  # 標準時間格式
            r"Time[：:]\s*([^\n]+)",  # 英文格式
            r"※ 發信站:.*?(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})",  # 從發信站提取時間
        ]

        # PTT 系統訊息過濾
        self.system_message_patterns = [
            r"※ 發信站:.*?$",
            r"※ 文章網址:.*?$",
            r"※ 編輯:.*?$",
            r"※ 轉錄者:.*?$",
            r"※ 引述.*?$",
            r"--\n※ 發信站.*",  # 簽名檔開始
        ]

        # 推文過濾
        self.comment_patterns = [
            r"^(推|噓|→)\s+\w+\s*:.*?$",  # 推文格式
            r"^\d{2}/\d{2}\s+\d{2}:\d{2}$",  # 推文時間
        ]

        logger.info("PTT 解析服務初始化完成")

    async def parse_article(
        self, response_data: dict[str, Any], url: str
    ) -> Optional[dict[str, Any]]:
        """
        解析 PTT 文章資料.

        Args:
            response_data: Firecrawl API 回應資料
            url: 文章 URL

        Returns:
            Dict 包含解析後的文章資料，或 None 如果解析失敗
        """
        try:
            data = response_data.get("data", {})
            markdown_content = data.get("markdown", "")
            metadata = data.get("metadata", {})

            if not markdown_content:
                logger.warning(f"文章無內容: {url}")
                return None

            # 基本解析
            parsed_data = {
                "title": "",
                "author": "",
                "content": "",
                "publish_date": datetime.now(),
                "category": None,
                "board": self._extract_board_from_url(url),
            }

            # 解析標題和分類
            title_info = self._parse_title(markdown_content, metadata)
            if title_info:
                parsed_data.update(title_info)

            # 解析作者
            author = self._parse_author(markdown_content, metadata)
            if author:
                parsed_data["author"] = author

            # 解析發布時間
            publish_date = self._parse_publish_date(markdown_content, metadata)
            if publish_date:
                parsed_data["publish_date"] = publish_date

            # 清理文章內容
            cleaned_content = self._clean_article_content(markdown_content)
            parsed_data["content"] = cleaned_content

            # 驗證必要欄位
            if not parsed_data["title"] or not parsed_data["author"]:
                logger.warning(f"缺少必要欄位: {url}")
                return None

            logger.debug(f"文章解析成功: {url}")
            return parsed_data

        except Exception as e:
            logger.error(f"文章解析失敗 ({url}): {e}")
            return None

    def _extract_board_from_url(self, url: str) -> str:
        """從 URL 提取看板名稱."""
        match = re.search(r"/bbs/([^/]+)/", url)
        return match.group(1) if match else "Unknown"

    def _parse_title(self, content: str, metadata: dict[str, Any]) -> Optional[dict[str, str]]:
        """解析文章標題和分類."""
        # 優先使用 metadata
        if "title" in metadata:
            title = metadata["title"]
            category = self._extract_category_from_title(title)
            return {
                "title": title,
                "category": category,
            }

        # 使用正則表達式解析
        for pattern in self.title_patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                if len(match.groups()) >= 2:
                    category = match.group(1).strip()
                    title = f"[{category}] {match.group(2).strip()}"
                    return {
                        "title": title,
                        "category": category,
                    }
                else:
                    title = match.group(0).strip()
                    category = self._extract_category_from_title(title)
                    return {
                        "title": title,
                        "category": category,
                    }

        # 找不到標題格式，使用第一行
        first_line = content.split("\n")[0].strip()
        if first_line and not first_line.startswith("#"):
            category = self._extract_category_from_title(first_line)
            return {
                "title": first_line,
                "category": category,
            }

        return None

    def _extract_category_from_title(self, title: str) -> Optional[str]:
        """從標題中提取分類."""
        # 標準分類格式 [分類]
        match = re.search(r"\[([^\]]+)\]", title)
        if match:
            category = match.group(1).strip()
            # 常見分類正規化
            category_mapping = {
                "心得": "心得",
                "請益": "請益",
                "標的": "標的",
                "閒聊": "閒聊",
                "新聞": "新聞",
                "情報": "情報",
                "討論": "討論",
                "問卦": "問卦",
                "Re": "Re",
            }
            return category_mapping.get(category, category)

        return None

    def _parse_author(self, content: str, metadata: dict[str, Any]) -> Optional[str]:
        """解析文章作者."""
        # 優先使用 metadata
        if "author" in metadata:
            return metadata["author"]

        # 使用正則表達式解析
        for pattern in self.author_patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                author = match.group(1).strip()
                # 移除括號內容（如學校、職業等）
                author = re.sub(r"\s*\([^)]*\)", "", author)
                if author and len(author) > 0:
                    return author

        return None

    def _parse_publish_date(self, content: str, metadata: dict[str, Any]) -> Optional[datetime]:
        """解析文章發布時間."""
        # 優先使用 metadata
        if "publishTime" in metadata:
            time_str = metadata["publishTime"]
            return self._parse_time_string(time_str)

        # 使用正則表達式解析
        for pattern in self.time_patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                time_str = match.group(1).strip()
                parsed_time = self._parse_time_string(time_str)
                if parsed_time:
                    return parsed_time

        # 如果都找不到，返回當前時間
        return datetime.now()

    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """解析時間字串."""
        if not time_str:
            return None

        # 常見的時間格式
        time_formats = [
            "%a %b %d %H:%M:%S %Y",  # Mon Jan 01 12:00:00 2024
            "%Y/%m/%d %H:%M:%S",  # 2024/01/01 12:00:00
            "%m/%d/%Y %H:%M:%S",  # 01/01/2024 12:00:00
            "%Y-%m-%d %H:%M:%S",  # 2024-01-01 12:00:00
            "%d/%m/%Y %H:%M",  # 01/01/2024 12:00
            "%Y/%m/%d",  # 2024/01/01
        ]

        for fmt in time_formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue

        logger.debug(f"無法解析時間格式: {time_str}")
        return None

    def _clean_article_content(self, content: str) -> str:
        """清理文章內容."""
        if not content:
            return ""

        # 移除 PTT 系統訊息
        for pattern in self.system_message_patterns:
            content = re.sub(pattern, "", content, flags=re.MULTILINE)

        # 移除推文區塊
        lines = content.split("\n")
        cleaned_lines = []
        in_comments = False

        for line in lines:
            # 檢測推文開始
            if any(re.match(pattern, line) for pattern in self.comment_patterns):
                in_comments = True
                continue

            # 如果在推文區塊中，跳過
            if in_comments:
                # 檢查是否為推文相關行
                if (
                    line.strip()
                    and not any(re.match(pattern, line) for pattern in self.comment_patterns)
                    and not re.match(r"^\d{2}/\d{2}\s+\d{2}:\d{2}$", line.strip())
                ):
                    # 可能推文結束了
                    in_comments = False
                    cleaned_lines.append(line)
                continue

            cleaned_lines.append(line)

        content = "\n".join(cleaned_lines)

        # 標準化換行和空白
        content = re.sub(r"\n{3,}", "\n\n", content)  # 最多兩個連續換行
        content = re.sub(r"[ \t]+", " ", content)  # 多個空格合併為一個
        content = content.strip()

        return content

    def parse_board_page(self, response_data: dict[str, Any]) -> list[dict[str, str]]:
        """
        解析看板頁面，提取文章連結.

        Args:
            response_data: Firecrawl API 回應資料

        Returns:
            List[Dict]: 文章連結列表
        """
        try:
            data = response_data.get("data", {})
            markdown = data.get("markdown", "")

            if not markdown:
                return []

            articles = []

            # 解析文章列表的不同格式
            patterns = [
                # 標準格式: [分類] 標題 作者
                r"(\d+)\.\s*\[([^\]]+)\]\s*([^\n]+?)\s+(\w+)\s*$",
                # Markdown 連結格式
                r"\[([^\]]+)\]\s*([^\n]+)\n.*?(https://www\.ptt\.cc/bbs/[^/]+/M\.[^\.]+\.A\.[^\.]+\.html)",
                # 簡單格式
                r"•\s*([^\n]+?)\s+(https://www\.ptt\.cc/bbs/[^/]+/M\.[^\.]+\.A\.[^\.]+\.html)",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, markdown, re.MULTILINE | re.DOTALL)

                for match in matches:
                    if len(match) >= 3:
                        if "https://" in match[-1]:
                            # URL 在最後一個 group
                            url = match[-1]
                            title = match[-2] if len(match) > 1 else match[0]
                            category = match[0] if len(match) > 2 else None
                        else:
                            # 需要從其他地方找 URL
                            continue

                        article_info = {
                            "title": title.strip(),
                            "url": url.strip(),
                            "category": category.strip() if category else None,
                        }

                        articles.append(article_info)

            # 去除重複
            seen_urls = set()
            unique_articles = []

            for article in articles:
                url = article["url"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_articles.append(article)

            logger.debug(f"解析看板頁面：找到 {len(unique_articles)} 個文章連結")
            return unique_articles

        except Exception as e:
            logger.error(f"解析看板頁面失敗: {e}")
            return []

    def validate_article_data(self, article_data: dict[str, Any]) -> bool:
        """驗證文章資料完整性."""
        required_fields = ["title", "author", "content"]

        for field in required_fields:
            if not article_data.get(field):
                logger.warning(f"缺少必要欄位: {field}")
                return False

        # 檢查內容長度
        if len(article_data["content"]) < 10:
            logger.warning("文章內容過短")
            return False

        # 檢查標題格式
        title = article_data["title"]
        if not title or len(title.strip()) == 0:
            logger.warning("標題為空")
            return False

        return True

    def extract_keywords(self, content: str, max_keywords: int = 10) -> list[str]:
        """從文章內容中提取關鍵字."""
        if not content:
            return []

        # 移除標點符號和特殊字符
        clean_content = re.sub(r"[^\w\s]", " ", content)

        # 分詞（簡單以空格分割）
        words = clean_content.split()

        # 過濾停用詞和短詞
        stop_words = {
            "的",
            "是",
            "在",
            "有",
            "和",
            "或",
            "但",
            "如果",
            "因為",
            "所以",
            "這",
            "那",
            "了",
            "我",
            "你",
            "他",
            "她",
            "它",
            "們",
            "都",
            "也",
            "就",
            "會",
            "能",
            "要",
            "不",
            "沒",
            "很",
            "更",
            "最",
            "比",
            "從",
            "到",
            "與",
            "及",
            "以",
            "for",
            "the",
            "and",
            "or",
            "but",
            "if",
            "then",
            "this",
            "that",
            "with",
            "from",
        }

        filtered_words = [
            word.lower() for word in words if len(word) > 1 and word.lower() not in stop_words
        ]

        # 計算詞頻
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 按頻率排序並取前 N 個
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in keywords[:max_keywords]]

    def get_content_summary(self, content: str, max_length: int = 200) -> str:
        """生成內容摘要."""
        if not content:
            return ""

        # 移除多餘空白和換行
        clean_content = re.sub(r"\s+", " ", content).strip()

        if len(clean_content) <= max_length:
            return clean_content

        # 在句號、問號、驚嘆號處截斷
        for i in range(max_length, max_length // 2, -1):
            if i < len(clean_content) and clean_content[i] in "。？！.?!":
                return clean_content[: i + 1]

        # 找不到合適的截斷點，直接截斷並加省略號
        return clean_content[:max_length].rstrip() + "..."
