# 뉴스플로우 수집 모듈 (news-flow)

뉴스원별 최신 기사를 수집하고, 대시보드 "뉴스플로우" 탭이 쓰는 `data/news-flow.json` 스냅샷을 만드는 독립 모듈입니다. 대시보드 본체와 분리되어 별도 관리가 가능합니다.

## 수집 방식

| 방식 | 소스 | 동작 |
|---|---|---|
| **RSS 기본값** | `modules/news-flow/feeds.json` | `feedparser` 로 직접 파싱 |
| **RSS 확장** | 외부 뉴스봇의 `dynamic_feeds.json` | `TELEGRAM_BOT_DIR` 또는 GitHub Actions의 `NEWS_BOT_REPOSITORY`로 지정된 저장소를 사용 |
| **크롤** | 외부 뉴스봇의 `scraper.py` | `fetch_scraped_sources()` 를 import해 재사용 |

- 외부 뉴스봇 저장소가 없거나 접근할 수 없으면 기본 RSS 목록만 수집합니다.
- Playwright 기반 JS 렌더링 소스(`fetch_js_sources`)는 현재 제외했습니다(브라우저 설치 필요).
- 각 뉴스원은 최신 **30건**까지 보관합니다.

## 동작 (스냅샷 패턴)

```
collect.py --(RSS + 선택적 크롤)--> ../../data/news-flow.json  (커밋/서빙)
                                               │
                                       server.js /api/news
                                               │
                                  news.html (통합 테이블 표시)
```

- 인터넷 + Python이 있는 PC에서 실행합니다.
- 대시보드의 뉴스플로우 페이지 **새로고침 버튼**은 서버의 `POST /api/news/refresh`
  를 호출해 이 수집기를 다시 실행합니다(`server.js`).

## 실행

```bash
python modules/news-flow/collect.py            # RSS + 선택적 크롤
python modules/news-flow/collect.py --no-crawl # RSS만
```

외부 뉴스봇 프로젝트 경로가 있으면 환경변수로 지정합니다. 이 경로 안에 `dynamic_feeds.json` 또는 `scraper.py`가 있을 때만 확장 수집이 실행됩니다.

```bash
TELEGRAM_BOT_DIR=D:\path\to\external-news-bot python modules/news-flow/collect.py
```

## 의존성

- Python 3.9+ (`zoneinfo` 사용)
- `feedparser`, `requests` — RSS
- `beautifulsoup4`, `urllib3` — 크롤(외부 `scraper.py`가 사용하는 경우)

```bash
pip install feedparser requests beautifulsoup4
```

## 스냅샷 스키마 (`data/news-flow.json`)

```jsonc
{
  "generated_at": "2026-07-01T16:58:49+0900",
  "connected": true,
  "source_count": 1,
  "article_count": 30,
  "feed_source": "dashboard-default",
  "sources": [
    {
      "name": "DART 공시 RSS",
      "method": "rss",            // "rss" | "crawl"
      "home": "https://dart.fss.or.kr",
      "items": [
        { "title": "...", "url": "https://...", "published": "2026-07-01T09:12:00+0900" }
      ]
    }
  ]
}
```

## 참고

- 현재 기본 목록은 Google 뉴스 검색 피드를 제외하고 DART 공시 RSS만 사용합니다.
- 외부 뉴스봇 저장소를 연결하려면 GitHub Actions 변수 `NEWS_BOT_REPOSITORY`에 실제 저장소명을 `owner/repo` 형식으로 지정합니다.
- 뉴스는 자주 바뀌므로 스냅샷도 새로고침 때마다 갱신됩니다. GitHub에 매번 반영할 필요는 없고, 최신 상태로 다시 커밋하고 싶을 때만 `data/news-flow.json` 을 커밋하면 됩니다.
