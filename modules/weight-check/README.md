# 전자·닉스 비중 체크 모듈 (weight-check)

삼성전자·SK하이닉스의 **시가총액 비중(%)** 최근 24개월 동향을 수집해
대시보드의 "전자, 닉스 비중 체크" 탭에 표시하기 위한 독립 모듈입니다.

대시보드 본체(Node/HTML)와 분리되어 있으며, KOFIA 수집·PDF 파싱 로직은
모두 이 폴더 안에 있습니다. 별도로 떼어내 관리하거나 이식하기 쉽습니다.

## 데이터 출처

- 금융투자협회(KOFIA) 공지사항 "삼성전자 등 및 SK하이닉스 시가총액 비중안내"
  - 목록: https://www.kofia.or.kr/brd/m_17/list.do
  - 매월 첫 영업일에 전월 데이터 기준 공지 게시. 첨부 PDF에서 비중을 파싱합니다.
- 비중 정의(코스콤 데이터): 해당 월 매일의 그 주식 최종시가총액을 유가증권시장
  전체 최종시가총액으로 나눈 비율의 **1개월 평균**.

## 동작 방식 (스냅샷 패턴)

502MB급 원천 데이터가 아니어도, 외부 사이트 스크래핑과 PDF 파싱을 매 PC에서
반복하지 않도록 **스냅샷**만 커밋해 공유합니다.

```
collect.py  --(KOFIA 수집 + PDF 파싱)-->  ../../data/weight-check.json  (커밋)
                                                    │
                                          server.js /api/weight
                                                    │
                                             weight.html (표시)
```

- 스냅샷 생성은 **인터넷 + pymupdf 가 있는 PC**에서만 실행합니다.
- 다른 PC는 `git pull` 로 받은 `data/weight-check.json` 을 그대로 사용합니다(재수집 불필요).

## 생성 / 갱신

```bash
# 저장소 루트에서
python modules/weight-check/collect.py            # 최근 24개월
python modules/weight-check/collect.py --months 3 # 소량(검증용)
```

매월 새 공지가 올라오면 다시 실행해 스냅샷을 갱신하고 커밋합니다.

```bash
python modules/weight-check/collect.py
git add data/weight-check.json
git commit -m "chore: update weight snapshot"
git push
```

## 의존성

- Python 3, `pymupdf`(fitz) — PDF 텍스트 추출용. 그 외에는 표준 라이브러리만 사용.

  ```bash
  pip install pymupdf
  ```

## 스냅샷 스키마 (`data/weight-check.json`)

```jsonc
{
  "source": "...", "metric": "...",
  "months": 24, "latest_month": "2026-06",
  "rows": [
    {
      "month": "2026-06", "post_date": "2026-07-01", "seq": "2384",
      "samsung_common": 28.24,   // 삼성전자 보통주(A) 비중(%)
      "samsung_pref": 2.48,      // 삼성전자 우선주(B) 비중(%)
      "samsung_total": 30.72,    // 합계(A+B) 비중(%)
      "sk_hynix": 24.96          // SK하이닉스 보통주 비중(%), 2025-10 이전은 null
    }
    // ... 최신 월 → 과거 월 순
  ]
}
```

## 참고

- SK하이닉스는 시가총액 집중도 기준을 넘어 별도 안내 대상이 된 **2025년 10월**부터
  제공됩니다. 그 이전 월은 KOFIA 공지에 SK PDF가 없어 `sk_hynix: null` 입니다.
- 관련 원천 봇: `kofia-bot`(공지 감지·PDF 다운로드). 이 모듈은 그와 별개로
  비중 수치를 파싱해 시계열 스냅샷을 만드는 역할입니다.
