"""명세 7장 사진 파일 보호: 시간 제한 열쇠 (10/15 결정, 후보 1).

- <img src>는 로그인 토큰을 붙이지 못한다 → 서버가 사진 주소를 줄 때 주소 자체에 열쇠를 붙인다
  예: /api/files/res_xxx.png?key=1760540000.3f9a... (만료 시각.서명)
- 열쇠는 로그인한 본인에게 가는 응답 안에만 있으므로 결국 주인만 열 수 있다
- 서명: 서버만 아는 비밀값으로 "파일 이름.만료 시각"을 HMAC-SHA256 (파이썬 기본 기능)
- 비밀값: storage/.file_key (처음 쓸 때 자동 생성, 저장소 제외 폴더라 PC마다 따로)
- 유효 시간: FILE_KEY_HOURS (3시간, 로그인 유효 시간과 같게)
"""
import hashlib
import hmac
import secrets
import threading
import time

from backend.config import STORAGE_DIR

FILE_KEY_HOURS = 3
_KEY_FILE = STORAGE_DIR / ".file_key"
_lock = threading.Lock()  # 첫 요청이 동시에 와도 비밀값을 한 번만 만들게
_secret = None


def _get_secret() -> bytes:
    global _secret
    with _lock:
        if _secret is None:
            if not _KEY_FILE.is_file():
                STORAGE_DIR.mkdir(parents=True, exist_ok=True)
                _KEY_FILE.write_text(secrets.token_hex(32), encoding="utf-8")
            _secret = bytes.fromhex(_KEY_FILE.read_text(encoding="utf-8").strip())
    return _secret


def _sign(name: str, expires: int) -> str:
    return hmac.new(_get_secret(), f"{name}.{expires}".encode(), hashlib.sha256).hexdigest()[:32]


def signed_url(name: str) -> str:
    """파일 이름 → 열쇠 붙은 주소 (지금부터 FILE_KEY_HOURS 동안 유효)"""
    expires = int(time.time()) + FILE_KEY_HOURS * 3600
    return f"/api/files/{name}?key={expires}.{_sign(name, expires)}"


def check_key(name: str, key: str | None) -> bool:
    """열쇠가 이 파일 것이고 만료 전이면 True"""
    if not key:
        return False
    expires, _, sig = key.partition(".")
    if not expires.isdigit() or int(expires) < time.time():
        return False
    return hmac.compare_digest(sig, _sign(name, int(expires)))
