# -*- coding: utf-8 -*-
r"""
뉴스플로우 수집 모듈 (lighthouse-amc-dashboard)

뉴스원별 최신 기사를 수집하고 data/news-flow.json 스냅샷을 만든다.

수집 방식:
  - RSS 기본값: modules/news-flow/feeds.json 의 피드들을 feedparser 로 파싱
  - RSS 확장: TELEGRAM_BOT_DIR 또는 NEWS_FEEDS 로 지정한 dynamic_feeds.json 사용
  - 크롤: 대시보드 내장 크롤러를 실행하고, 외부 뉴스봇 scraper.py 가 있으면 추가 병합
  - 중요도: 제목/출처 기반 자동 점수 + data/news-labels.json 수동 라벨 병합
"""
import argparse
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODULE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = REPO_ROOT / "data" / "news-flow.json"
LABELS_PATH = REPO_ROOT / "data" / "news-labels.json"

BOT_DIR = Path(os.environ.get("TELEGRAM_BOT_DIR", str(REPO_ROOT.parent / "external-news-bot")))
LOCAL_FEEDS_PATH = MODULE_DIR / "feeds.json"
BOT_FEEDS_PATH = BOT_DIR / "dynamic_feeds.json"
FEEDS_PATH = Path(os.environ["NEWS_FEEDS"]) if os.environ.get("NEWS_FEEDS") else (
    BOT_FEEDS_PATH if BOT_FEEDS_PATH.exists() else LOCAL_FEEDS_PATH
)

PER_SOURCE = 30
PER_SOURCE_OVERRIDES = {
    "SemiAnalysis": 100,
    "DRAMeXchange": 100,
    "Semiconductor Engineering": 100,
    "TrendForce": 100,
    "WCCFetch": 100,
    "WCCFTech": 100,
    "a16Z News": 100,
    "a16z News": 100,
}
KST = ZoneInfo("Asia/Seoul")
UA = {"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"}

SOURCE_WEIGHTS = [
    ("DART", 35, "공시 출처"), ("KRX KIND", 35, "공시 출처"),
    ("연합인포맥스", 15, "시장 전문 출처"), ("BOK", 15, "정책·매크로 출처"),
    ("FRB", 15, "정책·매크로 출처"), ("KDI", 12, "정책·매크로 출처"),
]
KEYWORD_RULES = [
    (45, "공시·거래 리스크", ["상장폐지", "거래정지", "관리종목", "감사의견", "횡령", "배임", "불성실공시"]),
    (40, "자본 변동", ["유상증자", "무상증자", "감자", "전환사채", "CB", "BW", "신주인수권", "자사주"]),
    (38, "M&A", ["인수", "합병", "매각", "M&A", "공개매수", "경영권", "최대주주"]),
    (35, "실적", ["실적", "영업이익", "매출", "순이익", "어닝", "컨센서스", "잠정"]),
    (32, "계약·수주", ["수주", "공급계약", "계약 체결", "LOI", "MOU", "공동개발"]),
    (30, "매크로", ["금리", "환율", "FOMC", "연준", "물가", "CPI", "PCE", "고용", "GDP"]),
    (28, "정책", ["정책", "규제", "세제", "정부", "금융위", "금감원", "한국은행", "국회"]),
    (26, "핵심 산업", ["반도체", "HBM", "DRAM", "NAND", "AI", "데이터센터", "전력", "원전", "배터리"]),
    (22, "시장 가격", ["급등", "급락", "강세", "약세", "사상 최고", "신고가", "하락", "상승"]),
]
LABEL_SCORES = {"high": 90, "medium": 55, "low": 20, "exclude": 0}
LABEL_TEXT = {"high": "높음", "medium": "보통", "low": "낮음", "exclude": "제외"}


def _per_source_limit(source_name: str) -> int:
    return PER_SOURCE_OVERRIDES.get(source_name, PER_SOURCE)


def _decode_feed(raw: bytes, http_ct: str) -> str:
    m = re.search(rb'encoding=["\']([^"\']+)["\']', raw[:500])
    if m:
        return raw.decode(m.group(1).decode("ascii", errors="ignore"), errors="replace")
    m2 = re.search(r"charset\s*=\s*([^\s;]+)", http_ct, re.IGNORECASE)
    if m2:
        return raw.decode(m2.group(1), errors="replace")
    return raw.decode("utf-8", errors="replace")


def _to_kst_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST).strftime("%Y-%m-%dT%H:%M:%S%z")


def _parse_entry_datetime(raw: str, default_tz) -> datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt:
            return dt if dt.tzinfo else dt.replace(tzinfo=default_tz)
    except Exception:
        pass
    normalized = value.replace("Z", "+00:00")
    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", normalized)
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            dt = datetime.fromisoformat(normalized) if fmt is None else datetime.strptime(value, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=default_tz)
        except Exception:
            continue
    return None


def _entry_published_iso(entry, default_tz) -> str | None:
    raw = entry.get("published") or entry.get("updated") or entry.get("created")
    dt = _parse_entry_datetime(raw, default_tz)
    if dt:
        return _to_kst_iso(dt)
    pub = entry.get("published_parsed") or entry.get("updated_parsed")
    return _to_kst_iso(datetime(*pub[:6], tzinfo=timezone.utc)) if pub else None


def _home_of(url: str) -> str:
    try:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}" if p.netloc else ""
    except Exception:
        return ""


def _article_id(source: str, title: str, url: str) -> str:
    key = (url or "").strip().lower() or f"{source}|{title}".strip().lower()
    return hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _label_from_score(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def classify_importance(source: str, method: str, title: str) -> dict:
    text = f"{source} {title}".upper()
    score = 8
    reasons = []
    for needle, weight, reason in SOURCE_WEIGHTS:
        if needle.upper() in text:
            score += weight
            reasons.append(reason)
            break
    if method == "crawl":
        score += 8
        reasons.append("크롤링 소스")
    for weight, reason, keywords in KEYWORD_RULES:
        if any(keyword.upper() in text for keyword in keywords):
            score += weight
            reasons.append(reason)
    score = min(score, 100)
    label = _label_from_score(score)
    return {"score": score, "label": label, "label_text": LABEL_TEXT[label], "reasons": reasons[:4] or ["기본 분류"]}


def load_labels() -> dict:
    if not LABELS_PATH.exists():
        return {}
    try:
        with open(LABELS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"  [labels:skip] {e}")
        return {}


def apply_importance(sources: list[dict], labels: dict) -> None:
    for source in sources:
        source_name = source.get("name") or ""
        method = source.get("method") or "rss"
        for item in source.get("items", []):
            title = item.get("title") or ""
            url = item.get("url") or ""
            aid = _article_id(source_name, title, url)
            auto = classify_importance(source_name, method, title)
            manual = labels.get(aid) if isinstance(labels.get(aid), dict) else None
            item["article_id"] = aid
            item["auto_importance_score"] = auto["score"]
            item["auto_importance_label"] = auto["label"]
            item["auto_importance_reasons"] = auto["reasons"]
            item["importance_score"] = auto["score"]
            item["importance_label"] = auto["label"]
            item["importance_label_text"] = auto["label_text"]
            item["importance_reasons"] = auto["reasons"]
            item["importance_source"] = "auto"
            if manual and manual.get("label") in LABEL_SCORES:
                label = manual["label"]
                item["importance_score"] = LABEL_SCORES[label]
                item["importance_label"] = label
                item["importance_label_text"] = LABEL_TEXT[label]
                item["importance_reasons"] = [manual.get("reason") or "사용자 라벨"]
                item["importance_source"] = "manual"
                item["manual_label_updated_at"] = manual.get("updated_at")


def fetch_rss_source(feed: dict) -> dict:
    name = feed["name"]
    limit = _per_source_limit(name)
    feed_base = _home_of(feed["url"])
    default_tz = KST if feed.get("lang") == "ko" else timezone.utc
    items = []
    try:
        try:
            resp = requests.get(feed["url"], timeout=12, headers=UA, verify=False)
            text = _decode_feed(resp.content, resp.headers.get("Content-Type", ""))
            parsed = feedparser.parse(text)
        except Exception:
            parsed = feedparser.parse(feed["url"])
        fp = urlparse(feed["url"])
        feed_base = f"{fp.scheme}://{fp.netloc}" if fp.netloc else feed_base
        for entry in parsed.entries[:limit]:
            title = (entry.get("title") or "").strip()
            url = (entry.get("link") or "").strip()
            if not title or not url:
                continue
            if url and not url.startswith("http"):
                url = feed_base + ("" if url.startswith("/") else "/") + url
            published = _entry_published_iso(entry, default_tz)
            items.append({"title": title, "url": url, "published": published})
    except Exception as e:
        print(f"  [rss:err] {name}: {e}")
    items.sort(key=lambda it: it["published"] or "", reverse=True)
    return {"name": name, "method": "rss", "home": feed_base, "items": items[:limit]}


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


def collect_external_crawl() -> list[dict]:
    if not BOT_DIR.exists():
        print(f"  [external-crawl:skip] 봇 경로 없음: {BOT_DIR}")
        return []
    sys.path.insert(0, str(BOT_DIR))
    try:
        import scraper
    except Exception as e:
        print(f"  [external-crawl:skip] scraper import 실패: {e}")
        return []
    try:
        raw = scraper.fetch_scraped_sources()
    except Exception as e:
        print(f"  [external-crawl:err] {e}")
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
        limit = _per_source_limit(g["name"])
        g["items"].sort(key=lambda x: x["published"] or "", reverse=True)
        g["items"] = g["items"][:limit]
    print(f"  [external-crawl] {len(grouped)}개 소스, 기사 {sum(len(g['items']) for g in grouped.values())}건")
    return list(grouped.values())


def collect_builtin_crawl() -> list[dict]:
    try:
        from builtin_crawl import fetch_builtin_crawl_sources
    except Exception as e:
        print(f"  [builtin-crawl:skip] import 실패: {e}")
        return []
    try:
        return fetch_builtin_crawl_sources(_per_source_limit)
    except Exception as e:
        print(f"  [builtin-crawl:err] {e}")
        return []


def collect_crawl() -> list[dict]:
    return collect_builtin_crawl() + collect_external_crawl()


def main() -> int:
    ap = argparse.ArgumentParser(description="뉴스플로우 수집기 (RSS + 크롤)")
    ap.add_argument("--no-crawl", action="store_true", help="RSS만 수집(크롤 생략)")
    args = ap.parse_args()
    if not FEEDS_PATH.exists():
        print(f"[!] 피드 목록을 찾을 수 없습니다: {FEEDS_PATH}")
        return 1
    with open(FEEDS_PATH, encoding="utf-8") as f:
        feeds = json.load(f)
    using_bot_feeds = FEEDS_PATH == BOT_FEEDS_PATH
    print(f"[*] 뉴스 수집 시작 - RSS 피드 {len(feeds)}개 ({FEEDS_PATH})" + ("" if args.no_crawl else " + 크롤"))
    sources = collect_rss(feeds)
    if not args.no_crawl:
        sources += collect_crawl()
    labels = load_labels()
    apply_importance(sources, labels)
    total = sum(len(s["items"]) for s in sources)
    payload = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "connected": True,
        "source_count": len(sources),
        "article_count": total,
        "feed_source": "external-news-bot" if using_bot_feeds else "dashboard-default",
        "labels_count": len(labels),
        "sources": sources,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"[OK] {len(sources)}개 소스 / {total}건 -> {OUTPUT_PATH} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    raise SystemExit(main())
