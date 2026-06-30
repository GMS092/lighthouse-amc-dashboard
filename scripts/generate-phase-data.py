# -*- coding: utf-8 -*-
r"""
헤게모니 국면 분류 스냅샷 생성기 (lighthouse-amc-dashboard)

financial.db(분기 재무데이터)가 있는 PC에서만 실행한다. 검증된
ai_agent/phase_classifier.py 의 분류 로직을 그대로 재사용해 전 종목
국면 분류 결과를 data/phase-classification.json 으로 출력한다.

- 다른 PC는 이 스크립트를 실행할 필요가 없다. GitHub에 커밋된
  data/phase-classification.json 만 git pull 로 받아 동일하게 사용한다.
- 60일 수익률(return_60d)은 새 대시보드에서 사용하지 않으므로 출력에서 제외한다.

사용:
    python scripts/generate-phase-data.py
    AI_AGENT_DIR=D:\path\to\ai_agent python scripts/generate-phase-data.py

추후 financial.db 가 온라인 DB로 이전되면, ai_agent/phase_classifier.py 의
데이터 소스만 교체하면 이 생성기는 그대로 동작한다.
"""
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "phase-classification.json"

# 분류 로직이 들어있는 ai_agent 프로젝트 경로 (이 PC 전용).
# 기본값: lighthouse 레포와 형제 디렉터리인 ../ai_agent
DEFAULT_AI_AGENT = REPO_ROOT.parent / "ai_agent"
AI_AGENT_DIR = Path(os.environ.get("AI_AGENT_DIR", str(DEFAULT_AI_AGENT)))

# 출력에서 제거할 필드 (새 대시보드 미사용)
DROP_FIELDS = ("return_60d",)


def main() -> int:
    if not AI_AGENT_DIR.exists():
        print(f"[!] ai_agent 디렉터리를 찾을 수 없습니다: {AI_AGENT_DIR}")
        print("    AI_AGENT_DIR 환경변수로 경로를 지정하세요.")
        return 1

    # phase_classifier 가 같은 폴더의 krx_client 등을 import 하므로 경로 추가
    sys.path.insert(0, str(AI_AGENT_DIR))

    try:
        import phase_classifier  # noqa: E402
    except Exception as e:  # pragma: no cover
        print(f"[!] phase_classifier import 실패: {e}")
        return 1

    print(f"[*] 분류 시작 (DB: {phase_classifier.FINANCIAL_DB})")
    result = phase_classifier.classify_all(force_refresh=True)

    if result.get("error"):
        print(f"[!] 분류 오류: {result['error']}")
        return 1

    companies = result.get("companies", [])
    for c in companies:
        for f in DROP_FIELDS:
            c.pop(f, None)

    payload = {
        "quarter": result.get("quarter"),
        "prev_quarter": result.get("prev_quarter"),
        "summary": result.get("summary", {}),
        "companies": companies,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, separators=(",", ":"))

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"[OK] {len(companies)}개사 → {OUTPUT_PATH} ({size_kb:.0f} KB)")
    print(f"     기준 분기: {payload['quarter']} vs {payload['prev_quarter']}")
    print(f"     요약: {payload['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
