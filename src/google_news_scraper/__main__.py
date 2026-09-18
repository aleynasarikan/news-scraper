"""
    Main module for google_news_scraper.
"""

import logging

import click

from google_news_scraper.scraper import GoogleNewsScraper


logging.basicConfig(level=logging.INFO)


@click.command()
@click.option(
    "--topic",
    "topics",
    multiple=True,
    required=True,
    help="The ID of a Google News topic to scrape. Repeat to scrape multiple "
    "topics into a single output file.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Path to the output file. Defaults to articles.csv or articles.json "
    "depending on --format.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["csv", "json"]),
    default="csv",
    help="Output file format.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of articles to save, across all requested topics.",
)
def scrape_google_news(
    topics: tuple[str, ...],
    output: str | None,
    output_format: str,
    limit: int | None,
) -> None:
    scraper = GoogleNewsScraper(output_file=output, output_format=output_format)
    scraper.scrape(topics, limit=limit)


if __name__ == "__main__":
    scrape_google_news()
