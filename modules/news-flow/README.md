# 뉴스플로우 수집 모듈 (news-flow)

기존 텔레그램 뉴스 봇(`telegram-news-bot`)의 소스 목록을 재사용해 뉴스원별 최신
기사를 수집하고, 대시보드 "뉴스플로우" 탭이 쓰는 `data/news-flow.json` 스냅샷을
만드는 독립 모듈입니다. 대시보드 본체와 분리되어 별도 관리가 가능합니다.

## 수집 방식 (2가지)

| 방식 | 소스 | 재사용 대상 |
|---|---|---|
| **RSS** | `telegram-news-bot/dynamic_feeds.json` 의 피드(~49개) | `feedparser` 로 직접 파싱 |
| **크롤** | 더벨·한국금융신문·딜사이트·IR협의회·Semiconductor Engineering·Chips and Cheese·TrendForce·WCCFtech 등 | 봇의 `scraper.py` `fetch_scraped_sources()` 를 그대로 import 재사용 |

- Playwright 기반 JS 렌더링 소스(`fetch_js_sources`)는 현재 제외했습니다(브라우저 설치 필요).
- 각 뉴스원은 최신 **30건**까지 보관합니다(화면은 20줄까지 노출 후 스크롤).

## 동작 (스냅샷 패턴)

```
collect.py --(RSS + 크롤)--> ../../data/news-flow.json  (커밋/서빙)
                                     │
                             server.js /api/news
                                     │
                                news.html (뉴스원별 표시)
```

- 인터넷 + Python + 봇 소스 파일이 있는 PC에서 실행합니다.
- 대시보드의 뉴스플로우 페이지 **새로고침 버튼**은 서버의 `POST /api/news/refresh`
  를 호출해 이 수집기를 다시 실행합니다(`server.js`).

## 실행

```bash
python modules/news-flow/collect.py            # RSS + 크롤
python modules/news-flow/collect.py --no-crawl # RSS만
```

봇 프로젝트 경로가 다르면 환경변수로 지정:

```bash
TELEGRAM_BOT_DIR=D:\path\to\telegram-news-bot python modules/news-flow/collect.py
```

## 의존성

- Python 3.9+ (`zoneinfo` 사용)
- `feedparser`, `requests` — RSS
- `beautifulsoup4`, `urllib3` — 크롤(봇 `scraper.py` 가 사용)

```bash
pip install feedparser requests beautifulsoup4
```

## 스냅샷 스키마 (`data/news-flow.json`)

```jsonc
{
  "generated_at": "2026-07-01T16:58:49+0900",
  "connected": true,
  "source_count": 58,
  "article_count": 1342,
  "sources": [
    {
      "name": "연합뉴스",
      "method": "rss",            // "rss" | "crawl"
      "home": "https://www.yna.co.kr",
      "items": [
        { "title": "...", "url": "https://...", "published": "2026-07-01T09:12:00+0900" }
      ]
    }
  ]
}
```

## 참고

- 현재는 뉴스원별 최신 기사를 그대로 보여줍니다(시장 관련성/스포츠·연예 제외 같은
  키워드 필터는 적용하지 않음). 필요 시 봇 `config.py` 의 필터를 이식할 수 있습니다.
- 뉴스는 자주 바뀌므로 스냅샷도 새로고침 때마다 갱신됩니다. GitHub에 매번 반영할
  필요는 없고, 최신 상태로 다시 커밋하고 싶을 때만 `data/news-flow.json` 을 커밋하면 됩니다.
