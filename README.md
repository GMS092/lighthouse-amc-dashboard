# Lighthouse AMC Dashboard

KRX Open API 데이터를 사용해 KOSPI/KOSDAQ 지수 현황을 보여주는 로컬 대시보드입니다.

## 실행

```bash
npm start
```

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:4174/dashboard.html
```

## 환경변수

`.env.example`을 참고해 `.env` 파일을 만듭니다.

```text
KRX_AUTH_KEY=your_krx_api_key_here
PORT=4174
```

`.env`는 API 키를 포함하므로 GitHub에 올리지 않습니다.

## 프로젝트 노트

기능 변경 이력과 구현 메모는 `docs/UPDATE_NOTES.md`에 기록합니다.
보관된 구현 코드는 `archive/` 폴더에 둡니다.
