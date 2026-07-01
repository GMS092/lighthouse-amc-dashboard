# -*- coding: utf-8 -*-
r"""
뉴스플로우 수집 모듈 (lighthouse-amc-dashboard)

기존 텔레그램 뉴스 봇(telegram-news-bot)의 소스 목록을 재사용해 뉴스원별 최신
기사를 수집하고 data/news-flow.json 스냅샷을 만든다.

수집 2가지 방식:
  - RSS  : telegram-news-bot/dynamic_feeds.json 의 피드들을 feedparser 로 파싱
  - 크롤 : telegram-news-bot/scraper.py 의 fetch_scraped_sources() 를 그대로 재사용
           (더벨·한국금융신문·딜사이트·IR협의회 등 requests+bs4 기반)
  ※ Playwright 기반 JS 렌더링 소스(fetch_js_sources)는 이번 단계에서 제외.

- 이 모듈은 대시보드 본체와 분리된 독립 모듈이다(별도 관리 목적).
- 인터넷 + 봇 소스 파일이 있는 PC에서 실행한다. 봇 프로젝트 경로는
  TELEGRAM_BOT_DIR 환경변수로 바꿀 수 있다(기본: ../telegram-news-bot).

사용:
    python modules/news-flow/collect.py
    python modules/news-flow/collect.py --no-crawl   # RSS만
    TELEGRAM_BOT_DIR=D:\path\to\telegram-news-bot python modules/news-flow/collect.py
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "news-flow.json"

BOT_DIR = Path(os.environ.get("TELEGRAM_BOT_DIR", str(REPO_ROOT.parent / "telegram-news-bot")))
FEEDS_PATH = Path(os.environ.get("NEWS_FEEDS", str(BOT_DIR / "dynamic_feeds.json")))

PER_SOURCE = 30            # 뉴스원별 최대 보관 기사 수
KST = ZoneInfo("Asia/Seoul")
UA = {"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"}


def _decode_feed(raw: bytes, http_ct: str) -> str:
    """RSS/XML 바이트를 올바른 인코딩으로 디코딩(봇 fetcher와 동일 로직)."""
    m = re.search(rb'encoding=["\']([^"\']+)["\']', raw[:500])
    if m:
        return raw.decode(m.group(1).decode("ascii", errors="ignore"), errors="replace")
    m2 = re.search(r"charset\s*=\s*([^\s;]+)", http_ct, re.IGNORECASE)
    if m2:
        return raw.decode(m2.group(1), errors="replace")
    return raw.decode("utf-8", errors="replace")


def _to_kst_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).strftime("%Y-%m-%dT%H:%M:%S%z")


def _home_of(url: str) -> str:
    try:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}" if p.netloc else ""
    except Exception:
        return ""


def fetch_rss_source(feed: dict) -> dict:
    """RSS 피드 하나 → {name, method, home, items:[...]}"""
    name = feed["name"]
    items = []
    try:
        try:
            resp = requests.get(feed["url"], timeout=12, headers=UA, verify=False)
            text = _decode_feed(resp.content, resp.headers.get("Content-Type", ""))
            parsed = feedparser.parse(text)
        except Exception:
            parsed = feedparser.parse(feed["url"])  # 폴백

        fp = urlparse(feed["url"])
        feed_base = f"{fp.scheme}://{fp.netloc}"

        for entry in parsed.entries[:PER_SOURCE]:
            title = (entry.get("title") or "").strip()
            url = (entry.get("link") or "").strip()
            if not title or not url:
                continue
            if url and not url.startswith("http"):
                url = feed_base + ("" if url.startswith("/") else "/") + url
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            published = _to_kst_iso(datetime(*pub[:6], tzinfo=timezone.utc)) if pub else None
            items.append({"title": title, "url": url, "published": published})
    except Exception as e:
        print(f"  [rss:err] {name}: {e}")

    items.sort(key=lambda it: it["published"] or "", reverse=True)
    return {"name": name, "method": "rss", "home": feed_base if items else _home_of(feed["url"]),
            "items": items[:PER_SOURCE]}


def collect_rss(feeds: list[dict]) -> list[dict]:
    sources = [None] * len(feeds)
    with ThreadPoolExecutor(max_workers=min(20, len(feeds) or 1)) as ex:
        futs = {ex.submit(fetch_rss_source, f): i for i, f in enumerate(feeds)}
        for fut in as_completed(futs):
            sources[futs[fut]] = fut.result()
    ok = [s for s in sources if s]
    total = sum(len(s["items"]) for s in ok)
    print(f"  [rss] {len(ok)}개 소스, 기사 {total}건")
    return ok


def collect_crawl() -> list[dict]:
    """봇의 scraper.fetch_scraped_sources() 재사용 → 소스별 그룹화."""
    if not BOT_DIR.exists():
        print(f"  [crawl:skip] 봇 경로 없음: {BOT_DIR}")
        return []
    sys.path.insert(0, str(BOT_DIR))
    try:
        import scraper  # telegram-news-bot/scraper.py
    except Exception as e:
        print(f"  [crawl:skip] scraper import 실패: {e}")
        return []

    try:
        raw = scraper.fetch_scraped_sources()
    except Exception as e:
        print(f"  [crawl:err] {e}")
        return []

    grouped: dict[str, dict] = {}
    for it in raw:
        name = it.get("source") or "크롤"
        url = (it.get("url") or "").strip()
        title = (it.get("title") or "").strip()
        if not title or not url:
            continue
        pub = it.get("published_at")
        published = _to_kst_iso(pub) if isinstance(pub, datetime) else None
        g = grouped.setdefault(name, {"name": name, "method": "crawl", "home": _home_of(url), "items": []})
        g["items"].append({"title": title, "url": url, "published": published})

    for g in grouped.values():
        g["items"].sort(key=lambda x: x["published"] or "", reverse=True)
        g["items"] = g["items"][:PER_SOURCE]
    print(f"  [crawl] {len(grouped)}개 소스, 기사 {sum(len(g['items']) for g in grouped.values())}건")
    return list(grouped.values())


def main() -> int:
    ap = argparse.ArgumentParser(description="뉴스플로우 수집기 (RSS + 크롤)")
    ap.add_argument("--no-crawl", action="store_true", help="RSS만 수집(크롤 생략)")
    args = ap.parse_args()

    if not FEEDS_PATH.exists():
        print(f"[!] 피드 목록을 찾을 수 없습니다: {FEEDS_PATH}")
        print("    TELEGRAM_BOT_DIR 또는 NEWS_FEEDS 환경변수로 경로를 지정하세요.")
        return 1

    with open(FEEDS_PATH, encoding="utf-8") as f:
        feeds = json.load(f)

    print(f"[*] 뉴스 수집 시작 — RSS 피드 {len(feeds)}개" + ("" if args.no_crawl else " + 크롤"))
    sources = collect_rss(feeds)
    if not args.no_crawl:
        sources += collect_crawl()

    total = sum(len(s["items"]) for s in sources)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "connected": True,
        "source_count": len(sources),
        "article_count": total,
        "sources": sources,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"[OK] {len(sources)}개 소스 / {total}건 → {OUTPUT_PATH} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    # 서버가 파이프로 실행할 때 stdout 기본 인코딩(cp949)에서 일부 문자(—)가
    # 인코딩 불가로 크래시하는 것을 방지 — UTF-8 로 강제.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    raise SystemExit(main())
