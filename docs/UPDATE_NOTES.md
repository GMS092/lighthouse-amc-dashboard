# 업데이트 노트

이 파일은 Lighthouse AMC 대시보드의 기능 변경, 제거, 보류 사항을 기록합니다. 앞으로 대시보드 기능을 추가하거나 수정한 뒤에는 제가 이 노트를 함께 갱신합니다.

## 2026-07-01

### 부팅 자동 실행
- Windows 로그인 시 GitHub의 최신 내용을 먼저 받은 뒤 로컬 서버를 실행하는 `scripts/start-dashboard.ps1`을 추가했습니다.
- 작업 스케줄러에 자동 실행을 등록하는 `scripts/install-startup-task.ps1`과 해제용 `scripts/uninstall-startup-task.ps1`을 추가했습니다.
- 간단히 수동 실행할 수 있는 `start-dashboard.bat`을 추가했습니다.
- 자동 실행 로그를 `logs/startup.log`에 남기고, `logs/`는 GitHub에 올리지 않도록 설정했습니다.

## 2026-06-30

### 작업공간
- 활성 프로젝트 작업공간을 `D:\OneDrive\문서\Code\lighthouse-amc-dashboard`로 이동했습니다.
- 다른 컴퓨터에서도 다시 실행할 수 있도록 `server.js`, `package.json`, `.env.example`, `.gitignore`, `README.md`를 추가했습니다.

### 브랜딩 및 테마
- `Lighthouse AMC` 대시보드 기본 화면을 구성했습니다.
- 등대 이미지를 제목 왼쪽의 원형 로고로 추가했습니다.
- 좌측 하단에 흑/백 테마 전환 버튼을 추가했습니다.

### 시장 위젯
- TradingView 시장 요약 위젯을 추가했습니다.
- Investing.com 경제 캘린더 iframe을 추가했습니다.
- Investing.com 위젯은 현재 localhost 환경에서 서비스 활성화 안내가 표시되어 임시 보류했습니다.
- Investing.com 경제 캘린더 iframe을 제거하고 TradingView Economic Calendar 위젯으로 교체했습니다.
- TradingView Stock Heatmap 위젯을 경제 캘린더 옆에 추가했습니다.

### KRX 국내 지수 현황
- KRX Open API 기반 KOSPI/KOSDAQ 지수 테이블을 구현했습니다.
- 종가, 거래대금, 1일/1주/1개월/3개월/6개월/12개월/YTD 수익률을 표시하도록 구성했습니다.
- 최신 데이터 반영 신뢰도가 충분하지 않아 현재 대시보드 화면에서는 제거했습니다.
- 구현 코드는 나중에 재사용할 수 있도록 `archive/krx-market-index-implementation.md`에 보관했습니다.

### 업데이트 노트 표시
- 대시보드 하단에 업데이트 노트 패널을 추가했습니다.
- 패널은 `docs/UPDATE_NOTES.md`를 읽어 최근 날짜별 변경 사항을 표시합니다.
- 업데이트 노트 표시 방식을 접이식 목록으로 변경했습니다.
- 각 항목은 날짜, 제목, 내용 요약을 한 줄로 보여주고 클릭하면 세부 내용을 펼쳐볼 수 있습니다.
- 업데이트 노트 목록을 테이블 형태로 변경해 날짜, 제목, 요약, 상세 구분을 더 명확하게 만들었습니다.
- 업데이트 노트 표시 개수를 최근 10개로 확장했습니다.
- 항목이 많아질 때 테이블 내부에서 스크롤해 볼 수 있도록 구성했습니다.
- 앞으로 기능을 추가하거나 제거할 때 이 노트를 제가 함께 갱신합니다.

## 작성 형식

### YYYY-MM-DD
- 추가:
- 변경:
- 제거:
- 알려진 이슈:
- 후속 작업:
