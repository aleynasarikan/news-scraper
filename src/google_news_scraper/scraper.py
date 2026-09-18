"""
    Main module for scraping and storing Google News data.
"""

import logging
import time

from typing import List, Sequence

import httpx
import pandas as pd

from google_news_scraper.conf import google_news_scraper_settings
from google_news_scraper.cookies import GoogleNewsCookieRetriever
from google_news_scraper.models import Article
from google_news_scraper.parser import GoogleNewsHTMLParser


DEFAULT_OUTPUT_FILENAMES = {"csv": "articles.csv", "json": "articles.json"}
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GoogleNewsConnectionError(BaseException):
    message = "Unable to access Google News for getting HTML content."


class GoogleNewsGetHTMLError(BaseException):
    message = "Unable to get HTML content from Google News."


class GoogleNewsScraper:
    """Class for scraping Google News data"""

    def __init__(
        self,
        output_file: str | None = None,
        output_format: str = "csv",
        logger: logging.Logger | None = None,
    ) -> None:
        self._cookie_retriever = GoogleNewsCookieRetriever()
        self._output_format = output_format
        self._output_file = (
            output_file if output_file else DEFAULT_OUTPUT_FILENAMES[output_format]
        )
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Connection": "keep-alive",
        }
        self._logger = logger if logger else logging.getLogger(__name__)
        self._parser = GoogleNewsHTMLParser(logger=self._logger)

    def _save(self, articles: List[Article]) -> None:
        """Saves given list of articles to the configured output file and format."""
        self._logger.info(f"Writing {len(articles)} articles to {self._output_file}..")
        if not articles:
            self._logger.warning(
                "No articles were scraped; writing an empty output file."
            )

        article_objects = [article.model_dump() for article in articles]
        df = pd.DataFrame(article_objects)
        if self._output_format == "json":
            df.to_json(
                self._output_file,
                orient="records",
                indent=2,
                date_format="iso",
                force_ascii=False,
            )
        else:
            # Semicolon avoids column-splitting issues in Excel/Numbers on
            # locales (e.g. tr_TR) where comma is the decimal separator.
            with open(self._output_file, "w", encoding="utf-8-sig", newline="") as f:
                f.write("sep=;\n")
                df.to_csv(f, index=False, sep=";")

    def _get_html_with_retry(self, topic_id: str, cookies: dict | None) -> str:
        """Fetches HTML content for a topic, retrying on transient failures."""
        last_error: Exception | None = None
        max_attempts = google_news_scraper_settings.max_retries + 1

        for attempt in range(max_attempts):
            try:
                response = httpx.get(
                    google_news_scraper_settings.get_url_for_topic(topic_id),
                    headers=self._headers,
                    cookies=cookies,
                    timeout=google_news_scraper_settings.request_timeout_seconds,
                )
                response.raise_for_status()
                return response.text
            except httpx.RequestError as e:
                last_error = e
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in RETRYABLE_STATUS_CODES:
                    raise GoogleNewsGetHTMLError from e
                last_error = e

            if attempt < max_attempts - 1:
                backoff = google_news_scraper_settings.retry_backoff_seconds * (
                    2**attempt
                )
                self._logger.warning(
                    f"Request for topic {topic_id} failed (attempt {attempt + 1}/"
                    f"{max_attempts}), retrying in {backoff:.1f}s.."
                )
                time.sleep(backoff)

        if isinstance(last_error, httpx.HTTPStatusError):
            raise GoogleNewsGetHTMLError from last_error
        raise GoogleNewsConnectionError from last_error

    def _scrape_single_topic(
        self, topic_id: str, cookies: dict | None
    ) -> List[Article]:
        """Scrapes a single Google News topic and returns its parsed articles."""
        self._logger.info(f"Scraping topic {topic_id}..")
        html_content = self._get_html_with_retry(topic_id, cookies)
        return self._parser.parse(html_content, topic_id=topic_id)

    def scrape(self, topic_ids: str | Sequence[str], limit: int | None = None) -> None:
        """
        Scrapes data from one or more Google News topics and stores it to a file.

        Args:
            topic_ids (str | Sequence[str]): The ID(s) of Google News topic(s) to scrape.
            limit (int | None): Maximum number of articles to keep, applied to the
                combined results across all requested topics.
        Raises:
            GoogleNewsConnectionError: Unable to establish connection with Google News.
            GoogleNewsGetHTMLError: Unable to retrieve HTML content due to bad status code.
        """
        if isinstance(topic_ids, str):
            topic_ids = [topic_ids]

        cookies = self._cookie_retriever.get_consent_cookies()
        if not cookies:
            self._logger.warning("Got empty consent cookies. Scraping might fail.")

        all_articles: List[Article] = []
        for topic_id in topic_ids:
            all_articles.extend(self._scrape_single_topic(topic_id, cookies))

        if limit is not None:
            all_articles = all_articles[:limit]

        self._save(all_articles)
