# README 그림 원본

- README의 시스템 아키텍처 · DB 관계도 · 처리 흐름 그림을 만든 HTML 원본
- 그림을 고칠 때는 HTML을 수정한 뒤 `render.py`로 PNG 재생성

| 원본 | 결과 그림 | README 위치 |
|---|---|---|
| `architecture.html` | `../moa_system_architecture.png` | 3장 서비스 구조 |
| `erd.html` | `../moa_erd.png` | 3-1. DB 관계도 |
| `flow.html` | `../moa_flow.png` | 4-1. 단계별 처리 |

## 실행

```powershell
python docs/readme/src/render.py
```

- 저장소 최상위 폴더에서 실행, 세 그림을 `docs/readme/`에 다시 생성
- 하나만 생성: `python docs/readme/src/render.py erd` (`architecture`, `erd`, `flow` 중 선택)
- 저장소 그림을 덮어쓰지 않고 확인: `python docs/readme/src/render.py --out-dir 폴더`
- 결과: 너비 2400px PNG. 3배 크기로 캡처한 뒤 줄여 글자를 선명하게 유지

## 필요한 것

- Google Chrome (헤드리스 캡처). 설치 위치가 다르면 환경 변수 `CHROME`에 `chrome.exe` 경로 지정
- Pillow (conda 환경 `CGI`에 설치됨)
- Windows 글꼴 맑은 고딕, Consolas (HTML이 사용). 다른 글꼴 환경에서는 줄바꿈 위치가 달라질 수 있음

## 수정 시 주의

- 색: 포인트 `#2b3a67`, 연한 면 `#e9eef6`, 바탕 `#f4f2ee`. 바탕색을 바꾸면 `render.py`의 `BEIGE`도 변경 (아래 흰 여백을 자르는 기준)
- 문구: 부제목만 문장, 나머지는 개조식
- `erd.html`: 컬럼은 `backend/db.py` 기준, 테이블 구조가 바뀌면 파일 안의 `T` 수정
- `flow.html`: 단계별 API는 `docs/api.md` 기준, 파일 안의 `S` 수정
- 수정 뒤에는 `--out-dir`로 먼저 확인하고 줄바꿈이 어긋나지 않았는지 눈으로 점검
