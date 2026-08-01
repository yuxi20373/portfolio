"""Site-specific scrapers, one pair of functions per source (see
app/services/news/news_sources.py for the registry that wires these up).
Each source's `fetch_listing`/`fetch_article` pair returns the same shapes:

    fetch_listing(listing_url, max_pages) -> [{"url", "title", "date_str"}, ...]
    fetch_article(url) -> {"title", "published_at" (naive local datetime or
                            None), "content_text"}

date_str is only a best-effort hint used for an early cutoff check in
news_service.py - the authoritative date always comes from fetch_article,
so it's fine if a source's date_str doesn't parse cleanly.

Deliberately dependency-light: plain requests + BeautifulSoup, no headless
browser (both sites are server-rendered / return real HTML from their
"load more" endpoints, no JS execution needed to see article content).
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from ...config import settings

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
_TIMEOUT = 20


# ---------------------------------------------------------------------------
# qbitai.com - pagination is a plain "?page=N" query param on the category URL.
# ---------------------------------------------------------------------------


def fetch_listing_qbitai(category_url: str, max_pages: int = 1) -> list[dict]:
    """Newest-first list of {url, title, date_str ("YYYY-MM-DD")} from the
    category page(s). date_str has no time component - that only lives on
    the article detail page (see fetch_article_qbitai)."""
    items = []
    seen = set()
    base = category_url.rstrip("/")
    for page in range(1, max_pages + 1):
        page_url = base if page == 1 else f"{base}?page={page}"
        try:
            resp = requests.get(page_url, headers=_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException:
            break  # later pages are a nice-to-have, not worth failing the run over

        soup = BeautifulSoup(resp.text, "html.parser")
        blocks = soup.select("div.picture_text")
        if not blocks:
            break

        for block in blocks:
            a = block.find("a", href=True)
            if not a or a["href"] in seen:
                continue
            title_el = block.select_one(".text_box h4")
            date_el = block.select_one(".info")
            if not title_el:
                continue
            seen.add(a["href"])
            items.append(
                {
                    "url": a["href"],
                    "title": title_el.get_text(strip=True),
                    "date_str": date_el.get_text(strip=True) if date_el else None,
                }
            )
    return items


def fetch_article_qbitai(url: str) -> dict:
    """Fetches one article page and returns title/published_at/content_text.
    content_text is plain text for summarization only - callers should
    discard it after summarizing, per the "don't keep raw article text"
    retention policy (see news_service.py)."""
    resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    h1 = soup.select_one("div.article h1") or soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    date_el = soup.select_one(".article_info .date")
    time_el = soup.select_one(".article_info .time")
    published_at = None
    date_str = date_el.get_text(strip=True) if date_el else None
    time_str = time_el.get_text(strip=True) if time_el else None
    if date_str and time_str:
        try:
            published_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            published_at = None
    if published_at is None and date_str:
        try:
            published_at = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            published_at = None

    article_el = soup.select_one("div.article")
    content_parts = []
    if article_el:
        for node in article_el.select("p, h1.pgc-h-forward-slash, h2, h3"):
            classes = node.get("class") or []
            if "pgc-img-caption" in classes:
                continue
            text = node.get_text(strip=True)
            if text:
                content_parts.append(text)

    return {
        "title": title,
        "published_at": published_at,
        "content_text": "\n".join(content_parts),
    }


# ---------------------------------------------------------------------------
# the-decoder.com - server-renders page 1; later pages come from a WordPress
# admin-ajax "load more" endpoint (action=load_more_posts) that needs a
# nonce + a few data-* params lifted off the page's "Load more" button.
# ---------------------------------------------------------------------------

_DECODER_AJAX_URL = "https://the-decoder.com/wp-admin/admin-ajax.php"


def _decoder_articles_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for block in soup.select("article"):
        overlay = block.select_one("a.absolute.inset-0")
        if not overlay or not overlay.get("href"):
            continue
        title = (overlay.get("title") or "").removeprefix("Read full article about: ").strip()
        date_el = block.select_one('[alt="Date of publication"]')
        items.append(
            {
                "url": overlay["href"],
                "title": title,
                "date_str": date_el.get_text(strip=True) if date_el else None,
            }
        )
    return items


def fetch_listing_decoder(listing_url: str, max_pages: int = 1) -> list[dict]:
    resp = requests.get(listing_url, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    html = resp.text

    seen = set()
    items = []
    for item in _decoder_articles_from_html(html):
        if item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)

    if max_pages <= 1:
        return items

    btn = BeautifulSoup(html, "html.parser").select_one("button.load-more-btn")
    nonce_match = re.search(r'var deepContent = (\{.*?\});', html)
    if not btn or not nonce_match:
        return items  # can't page further without these - first page's items are still valid

    import json

    nonce = json.loads(nonce_match.group(1)).get("nonce")
    post_type = btn.get("data-post-type", "post")
    archive_type = btn.get("data-archive-type", "")
    archive_value = btn.get("data-archive-value", "")

    for page in range(2, max_pages + 1):
        try:
            resp = requests.post(
                _DECODER_AJAX_URL,
                headers=_HEADERS,
                timeout=_TIMEOUT,
                data={
                    "action": "load_more_posts",
                    "page": page,
                    "post_type": post_type,
                    "archive_type": archive_type,
                    "archive_value": archive_value,
                    "nonce": nonce,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError):
            break  # later pages are a nice-to-have, not worth failing the run over

        if not payload.get("success") or not payload.get("html"):
            break

        page_items = _decoder_articles_from_html(payload["html"])
        if not page_items:
            break
        for item in page_items:
            if item["url"] not in seen:
                seen.add(item["url"])
                items.append(item)

    return items


def fetch_article_decoder(url: str) -> dict:
    resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    published_at = None
    meta = soup.find("meta", {"property": "article:published_time"})
    if meta and meta.get("content"):
        try:
            dt_utc = datetime.fromisoformat(meta["content"])
            published_at = dt_utc.astimezone(ZoneInfo(settings.news_timezone)).replace(tzinfo=None)
        except ValueError:
            published_at = None

    content_el = soup.select_one(".entry-content")
    content_parts = []
    if content_el:
        for node in content_el.select("p"):
            text = node.get_text(strip=True)
            if text:
                content_parts.append(text)

    return {
        "title": title,
        "published_at": published_at,
        "content_text": "\n".join(content_parts),
    }
