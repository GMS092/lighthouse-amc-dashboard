# -*- coding: utf-8 -*-
"""Built-in crawler sources for the dashboard news flow.

These crawlers intentionally use broad article-link extraction so the GitHub
Actions snapshot can run without depending on the separate Telegram bot repo.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (compatible; Lighthouse AMC news crawler)"}
REQUEST_TIMEOUT = 6

CRAWL_SOURCES = [
    {
        "name": "Semiconductor Engineering",
        "home": "https://semiengineering.com",
        "urls": ["https://semiengineering.com/category/manufacturing/"],
        "include": ["semiengineering.com/"],
        "exclude": ["/author/", "/tag/", "/category/", "#", "mailto:"],
    },
    {
        "name": "TrendForce",
        "home": "https://www.trendforce.com",
        "urls": ["https://www.trendforce.com/news/"],
        "include": ["trendforce.com/news/"],
        "exclude": ["/presscenter/", "#", "mailto:"],
    },
    {
        "name": "WCCFetch",
        "home": "https://wccftech.com",
        "urls": ["https://wccftech.com/category/hardware/"],
        "include": ["wccftech.com/"],
        "exclude": ["/category/", "/tag/", "/author/", "/page/", "#", "mailto:"],
    },
    {
        "name": "a16Z News",
        "home": "https://a16z.com",
        "urls": ["https://a16z.com/news/"],
        "include": ["a16z.com/"],
        "exclude": ["/podcast/", "/author/", "/tag/", "/category/", "#", "mailto:"],
    },
]

BAD_TITLE_BITS = (
    "privacy", "terms", "subscribe", "newsletter", "advertise", "contact",
    "cookie", "login", "sign in", "about", "events", "webinar"
)


def _home_of(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else ""


def _is_article_like(url: str, title: str, source: dict) -> bool:
    lower_url = url.lower()
    lower_title = title.lower()
    if not title or len(title) < 12:
        return False
    if any(bit in lower_title for bit in BAD_TITLE_BITS):
        return False
    if any(bit in lower_url for bit in source.get("exclude", [])):
        return False
    if not any(bit in lower_url for bit in source.get("include", [])):
        return False
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path or path.count("/") < 1:
        return False
    return True


def _parse_datetime(raw: str | None) -> str | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except Exception:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")


def _node_time(node) -> str | None:
    for current in [node, node.parent, node.parent.parent if node.parent else None]:
        if not current:
            continue
        time_node = current.find("time") if hasattr(current, "find") else None
        if time_node:
            parsed = _parse_datetime(time_node.get("datetime") or time_node.get("pubdate") or time_node.get_text(" ", strip=True))
            if parsed:
                return parsed
        for attr in ("datetime", "data-date", "data-published", "data-time"):
            raw = current.get(attr) if hasattr(current, "get") else None
            parsed = _parse_datetime(raw)
            if parsed:
                return parsed
    return None


def _title_from_anchor(anchor) -> str:
    title = anchor.get("title") or anchor.get("aria-label") or anchor.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", title or "").strip()


def _extract_from_page(source: dict, page_url: str) -> list[dict]:
    try:
        res = requests.get(page_url, timeout=REQUEST_TIMEOUT, headers=UA)
        res.raise_for_status()
    except Exception as exc:
        print(f"  [builtin-crawl:err] {source['name']} {page_url}: {exc}")
        return []
    soup = BeautifulSoup(res.text, "lxml")
    items = []
    seen = set()
    for anchor in soup.select("article a[href], h1 a[href], h2 a[href], h3 a[href], a[href]"):
        href = anchor.get("href") or ""
        url = urljoin(page_url, href).split("?")[0].rstrip("/")
        title = _title_from_anchor(anchor)
        if url in seen or not _is_article_like(url, title, source):
            continue
        seen.add(url)
        items.append({"title": title, "url": url, "published": _node_time(anchor)})
    return items


def _dedupe(items: Iterable[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in items:
        key = (item.get("url") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def fetch_builtin_crawl_sources(per_source_limit) -> list[dict]:
    sources = []
    for source in CRAWL_SOURCES:
        items = []
        for page_url in source["urls"]:
            items.extend(_extract_from_page(source, page_url))
        items = _dedupe(items)
        items.sort(key=lambda item: item.get("published") or "", reverse=True)
        limit = per_source_limit(source["name"])
        sources.append({
            "name": source["name"],
            "method": "crawl",
            "home": source.get("home") or _home_of(source["urls"][0]),
            "items": items[:limit],
        })
    total = sum(len(source["items"]) for source in sources)
    print(f"  [builtin-crawl] {len(sources)}개 소스, 기사 {total}건")
    return sources
