#!/usr/bin/env python3
"""로컬 작업용 서버 (배포용 아님)
- 저장소 루트를 http://127.0.0.1:8765 로 제공
- ebook/ 아래 PUT 허용 → tools/pdf2webp.html 이 변환한 쪽 이미지를 저장
- annot/ 아래 PUT/GET → nginx WebDAV 메모 동기화 흉내 (인자로 '아이디:비밀번호'를 주면 Basic 인증 확인)

사용: python3 tools/devserver.py [아이디:비밀번호]
"""
import base64
import http.server
import sys
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parent.parent
AUTH = ("Basic " + base64.b64encode(sys.argv[1].encode()).decode()) if len(sys.argv) > 1 else None


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO), **kwargs)

    def _authorized(self):
        return AUTH is None or self.headers.get("Authorization") == AUTH

    def _deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="notes"')
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/annot/") and not self._authorized():
            return self._deny()
        return super().do_GET()

    def do_PUT(self):
        rel = unquote(self.path.split("?", 1)[0]).lstrip("/")
        if not (rel.startswith("ebook/") or rel.startswith("annot/")) or ".." in rel:
            self.send_response(403)
            self.end_headers()
            return
        if rel.startswith("annot/") and not self._authorized():
            return self._deny()
        target = REPO / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        self.send_response(201)
        self.end_headers()

    def end_headers(self):
        if self.path.startswith("/annot/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"http://127.0.0.1:8765  (저장소: {REPO})")
    http.server.ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
