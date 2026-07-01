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

## GitHub Pages

보기 전용 대시보드는 GitHub Pages로 배포할 수 있습니다. Pages에서는 서버 API를 실행할 수 없으므로 `phase.html`, `news.html`, `weight.html`은 로컬 서버가 아닌 환경에서 `data/*.json` 스냅샷을 직접 읽습니다.

GitHub 저장소 설정에서 `Settings > Pages > Build and deployment > Source`를 `GitHub Actions`로 지정하면, `main` 브랜치에 push될 때 `.github/workflows/pages.yml`이 정적 파일만 골라 배포합니다.

배포 대상은 `index.html`, `dashboard.html`, `phase.html`, `news.html`, `weight.html`, `assets/`, `data/`, `docs/UPDATE_NOTES.md`입니다. 데이터 수집과 새로고침 기능은 로컬 서버 또는 별도 수집 작업에서 실행합니다.

## Windows 자동 실행

PC 부팅 후 Windows에 로그인할 때 GitHub의 최신 내용을 먼저 받은 다음 로컬 서버를 실행하려면 아래 파일을 한 번 실행합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-startup-task.ps1
```

등록 후에는 로그인할 때마다 `scripts/start-dashboard.ps1`이 실행됩니다. 이 스크립트는 `git pull --ff-only origin main`으로 최신 내용을 확인하고, 의존성을 설치한 뒤 `npm start`로 서버를 실행합니다.

자동 실행을 해제하려면 아래 파일을 실행합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\uninstall-startup-task.ps1
```

자동 실행 로그는 `logs/startup.log`에 기록됩니다. `logs/` 폴더는 로컬 실행 기록이므로 GitHub에는 올리지 않습니다.
