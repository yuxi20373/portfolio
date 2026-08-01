"""Registry of scraped news sources. Each source pairs a listing URL with
the scraper functions that know how to read that specific site's HTML (see
news_scraper_service.py). To add a new source: write its
fetch_listing_X/fetch_article_X pair there, then add one entry here -
nothing else needs to change (news_service.py just loops over this list,
and the News sidebar/API list sources from here too)."""

from . import news_scraper_service as scraper

SOURCES = [
    {
        "key": "qbitai",
        "name": "量子位",
        "listing_url": "https://www.qbitai.com/category/资讯",
        "listing_pages": 6,
        "fetch_listing": scraper.fetch_listing_qbitai,
        "fetch_article": scraper.fetch_article_qbitai,
    },
    {
        "key": "decoder",
        "name": "The Decoder",
        "listing_url": "https://the-decoder.com/artificial-intelligence-news/short-news/",
        "listing_pages": 6,
        "fetch_listing": scraper.fetch_listing_decoder,
        "fetch_article": scraper.fetch_article_decoder,
    },
]

SOURCES_BY_KEY = {s["key"]: s for s in SOURCES}
