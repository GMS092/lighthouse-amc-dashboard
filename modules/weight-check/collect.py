# -*- coding: utf-8 -*-
r"""
전자·닉스 시가총액 비중 수집 모듈 (lighthouse-amc-dashboard)

금융투자협회(KOFIA) 공지사항에서 "삼성전자 등 및 SK하이닉스 시가총액 비중안내"
월간 공지를 최근 N개월치 수집하고, 각 공지의 월간 PDF에서 시가총액 비중(%)을
파싱해 data/weight-check.json 스냅샷을 만든다.

- 이 모듈은 lighthouse 대시보드 본체와 분리된 독립 모듈이다. KOFIA 수집/파싱
  로직은 전부 이 폴더 안에 있다(별도 관리 목적).
- 스냅샷은 인터넷 + pymupdf 가 있는 PC에서만 생성한다. 다른 PC는 커밋된
  data/weight-check.json 을 git pull 로 받아 동일하게 사용한다(재수집 불필요).
- 비중 정의(KOFIA/코스콤): 해당 월 매일의 그 주식 최종시가 총액을 유가증권시장
  전체 최종시가 총액으로 나눈 비율의 1개월 평균.

사용:
    python modules/weight-check/collect.py            # 최근 24개월
    python modules/weight-check/collect.py --months 3 # 검증용 소량
"""
import argparse
import datetime as dt
import html
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://www.kofia.or.kr/brd/m_17/"
LIST_URL = BASE_URL + "list.do"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LighthouseWeightCollector/1.0"

# 월간 비중안내 공지 판별. SK하이닉스는 2025-10부터 제목/첨부에 등장하므로
# 제목 필수 토큰에서는 제외하고, SK PDF 유무로 개별 처리한다.
TITLE_MUST_INCLUDE = ["삼성전자", "시가총액", "비중안내"]

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "weight-check.json"

MAX_PAGES = 60          # 안전장치: 이 이상은 넘기지 않음
REQUEST_DELAY = 0.3     # 요청 간 예의상 지연(초)


def http_get(url, binary=False, retries=3):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            return data if binary else data.decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError,
                http.client.HTTPException, ConnectionError, OSError) as e:
            last_err = e
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"HTTP GET 실패: {url} ({last_err})")


def is_target_title(title):
    return all(tok in title for tok in TITLE_MUST_INCLUDE)


def month_from_title(title):
    """제목의 'YYYY년 M월' → 'YYYY-MM' (데이터 기준 월)."""
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월", title)
    if not m:
        return None
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"


def parse_notices(list_html):
    """공지 목록 HTML → 대상 공지 레코드 리스트."""
    notices = []
    rows = re.split(r"<tr\b[^>]*>", list_html)
    for row in rows:
        if "view.do?seq=" not in row:
            continue
        m_seq = re.search(r"view\.do\?seq=(\d+)", row)
        if not m_seq:
            continue
        seq = m_seq.group(1)

        m_title = re.search(r"view\.do\?seq=\d+[^>]*>(.*?)</a>", row, re.S)
        title = ""
        if m_title:
            title = html.unescape(re.sub(r"<[^>]+>", "", m_title.group(1))).strip()
        title = re.sub(r"\s+", " ", title)
        if not is_target_title(title):
            continue

        m_date = re.search(r"(\d{4}-\d{2}-\d{2})", row)
        post_date = m_date.group(1) if m_date else ""

        attachments = []
        for m in re.finditer(
            r'href="(?:\./)?(down\.do\?[^"]*seq=\d+[^"]*file_seq=\d+)"[^>]*>'
            r'(?:.*?alt="([^"]*?)")?',
            row, re.S,
        ):
            rel = html.unescape(m.group(1))
            alt = html.unescape(m.group(2) or "")
            fn = re.search(r"([^\s\"/>]+\.(?:pdf|hwp|hwpx|xlsx?|zip|docx?))", alt, re.I)
            attachments.append({
                "url": BASE_URL + rel,
                "filename": fn.group(1) if fn else "",
            })

        notices.append({
            "seq": seq,
            "title": title,
            "post_date": post_date,
            "month": month_from_title(title),
            "view_url": f"{BASE_URL}view.do?seq={seq}",
            "attachments": attachments,
        })
    return notices


def _monthly(attachments):
    """상/하반기 요약이 아닌 월간 PDF 첨부만."""
    return [a for a in attachments
            if a["filename"].lower().endswith(".pdf")
            and "상반기" not in a["filename"]
            and "하반기" not in a["filename"]]


def _pick_samsung(attachments):
    """삼성 월간 PDF. 신형(파일명에 '삼성')이면 그걸, 구형(2025-09 이전 단일
    '붙임_YYYY년M월시가총액비중안내.pdf')이면 하이닉스가 아닌 PDF를 선택."""
    monthly = _monthly(attachments)
    named = [a for a in monthly if "삼성" in a["filename"]]
    pool = named or [a for a in monthly if "하이닉스" not in a["filename"]]
    return pool[0] if pool else None


def _pick_sk(attachments):
    """SK하이닉스 월간 PDF (2025-10 이후에만 존재). 없으면 None."""
    cands = [a for a in _monthly(attachments) if "하이닉스" in a["filename"]]
    return cands[0] if cands else None


def _pdf_text(pdf_bytes):
    import fitz  # pymupdf
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _num(pattern, text):
    m = re.search(pattern, text)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def parse_samsung(pdf_bytes):
    """삼성전자 보통주(A)/우선주(B)/합계(A+B) 비중(%)."""
    t = _pdf_text(pdf_bytes)
    return {
        "samsung_common": _num(r"보통주\(A\)\s*([\d,]+\.\d+)", t),
        "samsung_pref": _num(r"우선주\(B\)\s*([\d,]+\.\d+)", t),
        "samsung_total": _num(r"합계\(A\+B\)\s*([\d,]+\.\d+)", t),
    }


def parse_sk(pdf_bytes):
    """SK하이닉스 보통주 비중(%)."""
    t = _pdf_text(pdf_bytes)
    v = _num(r"SK하이닉스\s*보통주\s*([\d,]+\.\d+)", t)
    if v is None:
        v = _num(r"보통주\s*([\d,]+\.\d+)", t)
    return v


def collect(months=24):
    by_month = {}   # "YYYY-MM" -> record
    page = 1
    while page <= MAX_PAGES and len(by_month) < months:
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        try:
            page_html = http_get(url)
        except Exception as e:
            print(f"  [warn] page {page} 로드 실패, 건너뜀: {e}")
            page += 1
            time.sleep(REQUEST_DELAY)
            continue
        if "view.do?seq=" not in page_html:
            break  # 게시글이 더 없음 → 종료
        notices = parse_notices(page_html)
        for n in notices:
            mon = n["month"]
            if not mon or mon in by_month:
                continue
            sam = _pick_samsung(n["attachments"])
            sk = _pick_sk(n["attachments"])
            if not sam:
                print(f"  [skip] {mon} seq={n['seq']} 삼성 PDF 없음")
                continue
            try:
                s = parse_samsung(http_get(sam["url"], binary=True))
                k = None
                if sk:
                    time.sleep(REQUEST_DELAY)
                    k = parse_sk(http_get(sk["url"], binary=True))
            except Exception as e:
                print(f"  [err] {mon} seq={n['seq']} PDF 파싱 실패: {e}")
                continue
            by_month[mon] = {
                "month": mon,
                "post_date": n["post_date"],
                "seq": n["seq"],
                "samsung_common": s["samsung_common"],
                "samsung_pref": s["samsung_pref"],
                "samsung_total": s["samsung_total"],
                "sk_hynix": k,
            }
            print(f"  [ok] {mon}  삼성 {s['samsung_total']}  SK {k}")
            time.sleep(REQUEST_DELAY)
        page += 1
        time.sleep(REQUEST_DELAY)

    rows = sorted(by_month.values(), key=lambda r: r["month"], reverse=True)[:months]
    return rows


def main():
    ap = argparse.ArgumentParser(description="전자·닉스 시가총액 비중 수집기")
    ap.add_argument("--months", type=int, default=24, help="수집할 최근 개월 수")
    args = ap.parse_args()

    print(f"[*] KOFIA 비중 공지 수집 시작 (최근 {args.months}개월)")
    rows = collect(months=args.months)
    if not rows:
        print("[!] 수집된 데이터가 없습니다.")
        return 1

    payload = {
        "source": "KOFIA 금융투자협회 · 시가총액 비중안내 (데이터: 코스콤)",
        "metric": "해당 월 매일의 최종시가총액 / 유가증권시장 전체 최종시가총액 비율의 1개월 평균(%)",
        "months": len(rows),
        "latest_month": rows[0]["month"],
        "rows": rows,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"[OK] {len(rows)}개월 → {OUTPUT_PATH} ({size_kb:.0f} KB)")
    print(f"     최신: {rows[0]['month']} 삼성 {rows[0]['samsung_total']} / SK {rows[0]['sk_hynix']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
