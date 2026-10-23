"""체험판 접속 설정 파일 만들기: SQLite 회원 데이터 저장, 웹 화면의 localhost 백엔드 연결.

실행 (저장소 최상위 디렉터리, conda 환경 CGI): python scripts\\setup_trial_env.py
- backend/.env: 회원 데이터를 storage/moa_trial.db 파일에 저장 (MySQL 불필요)
- frontend/.env.local: 웹 화면 요청을 localhost:8000 백엔드로 전송
- 이미 있는 파일은 덮어쓰지 않음 (MySQL 접속 설정 보호)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = {
    ROOT / "backend" / ".env": "DATABASE_URL=sqlite:///storage/moa_trial.db\n",
    ROOT / "frontend" / ".env.local": "VITE_API_MODE=mixed\nVITE_API_TARGET=http://localhost:8000\n",
}

if __name__ == "__main__":
    (ROOT / "storage").mkdir(exist_ok=True)
    for path, text in FILES.items():
        name = path.relative_to(ROOT).as_posix()
        if path.exists():
            print(f"[건너뜀] {name}: 이미 있음")
        else:
            path.write_text(text, encoding="utf-8")
            print(f"[생성] {name}")
    print("결과: 접속 설정 완료. 백엔드 첫 실행 시 storage/moa_trial.db와 테스트 계정 test / test1234 생성")
