# 상대수익률 추이 모듈 (relative-return)

WISE 업종지수 시계열 엑셀을 읽어, 각 KSE 업종의 **KOSPI 대비 상대수익률**
(1개월·3개월)을 최근일 기준 5개 시점으로 뽑아 대시보드 "상대수익률 추이" 탭이
쓰는 `data/relative-return.json` 스냅샷을 만드는 독립 모듈입니다.

## 입력 데이터

- 엑셀: `상대수익률차트.xlsx` (기본 경로 `C:\Users\CHECK\Documents\Data\`)
  - WISEfn/QuantiWise 형식 시계열. 행 8=지수코드, 행 9=이름, 데이터는 행 15부터.
  - 지수마다 **2개 컬럼**: `1개월전대비수익률`, `3개월전대비수익률` (%).
  - `IKS900`=코스피, `IKQ900`=코스닥, `WI####`=KSE 업종.
- 경로 변경: 환경변수 `REL_RETURN_XLSX`.

## 계산

- **상대수익률 = 업종 수익률 − 코스피 수익률** (같은 기간, 같은 날짜)
  - X축: KOSPI 대비 1개월 수익률, Y축: KOSPI 대비 3개월 수익률
- 최근일 기준 5개 시점: **6개월 전 · 3개월 전 · 1개월 전 · 1주 전 · 최근**
  (달력 기준으로 목표일을 잡고, 그 이하에서 가장 가까운 거래일을 사용)
- 코스피·코스닥(벤치마크)은 플롯에서 제외.

## 실행

```bash
python modules/relative-return/collect.py
```

대시보드의 상대수익률 페이지 **새로고침 버튼**은 서버의
`POST /api/relative-return/refresh` 를 호출해 이 생성기를 다시 실행합니다.
엑셀을 새 데이터로 갱신한 뒤 새로고침하면 반영됩니다.

## 의존성

- Python 3.9+, `openpyxl`

```bash
pip install openpyxl
```

## 스냅샷 스키마 (`data/relative-return.json`)

```jsonc
{
  "generated_at": "...",
  "base_date": "2026-07-02",
  "x_label": "(KOSPI 대비 1개월 수익률)",
  "y_label": "(KOSPI 대비 3개월 수익률)",
  "points": [ { "key": "6m", "label": "6개월 전", "date": "2026-01-02" }, ... , { "key": "now", ... } ],
  "sectors": [
    {
      "code": "WI1620", "name": "반도체",
      "traj": [ [x,y], [x,y], [x,y], [x,y], [x,y] ]   // 과거→최근 순, 결측은 null
    }
  ]
}
```

`traj` 의 각 점은 `[상대 1개월(%), 상대 3개월(%)]` 이며, 화면에서는 과거→최근을
선으로 잇고 마지막(최근) 점에 화살표를 그립니다.
