"""
    Module for parsing Google News HTML content.
"""

import logging

from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from google_news_scraper.conf import google_news_scraper_settings
from google_news_scraper.models import Article


class GoogleNewsHTMLParser:
    """Class for parsing Google News HTML content."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger if logger else logging.getLogger(__name__)

    def _parse_article(self, article: BeautifulSoup, topic_id: str) -> Article | None:
        """Parses single Google News article from extracted HTML"""
        title = article.find("a", {"class": "gPFEn"})
        title_text = title.get_text(strip=True) if title else None
        url = (
            urljoin(google_news_scraper_settings.url, title.get("href"))
            if title
            else None
        )
        if not any((title_text, url)):
            return None

        source = article.find("div", {"class": "vr1PYe"})
        source_text = source.get_text(strip=True) if source else None

        time_elem = article.find("time", {"class": "hvbAAd"})
        published_at = time_elem.get("datetime") if time_elem else None
        relative_time = time_elem.get_text(strip=True) if time_elem else None

        authors_elem = article.find("div", {"class": "bInasb"})
        authors = authors_elem.get_text(strip=True) if authors_elem else None
        if authors:
            authors = authors.removeprefix("By ")

        image = article.find("img", {"class": "vwBmvb"})
        image_url = (
            urljoin(google_news_scraper_settings.url, image.get("src"))
            if image and image.get("src")
            else None
        )

        return Article(
            title=title_text,
            url=url,
            source=source_text,
            published_at=published_at,
            relative_time=relative_time,
            authors=authors,
            image_url=image_url,
            topic_id=topic_id,
        )

    def parse(self, html: str, topic_id: str = "") -> List[Article]:
        """
        Parses HTML content from Google News into a list of Article objects.

        Args:
            html (str): HTML content from a Google News page.
            topic_id (str): The topic ID the HTML was fetched for, stored on
                each parsed Article to trace its origin.

        Returns:
            List[Article]: A list of Article objects.
        """
        soup = BeautifulSoup(html, "html.parser")
        articles: List[BeautifulSoup] = soup.find_all(
            "c-wiz", {"class": "PO9Zff Ccj79 kUVvS"}
        )
        parsed_articles = [
            parsed_article
            for article in articles
            if (parsed_article := self._parse_article(article, topic_id))
        ]
        if not parsed_articles:
            self._logger.warning(
                "Parsed 0 articles from Google News HTML. Google's markup may "
                "have changed, or the page content was blocked/empty."
            )
        return parsed_articles
