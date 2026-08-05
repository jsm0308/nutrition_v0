from __future__ import annotations

import json
import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from optimizer import optimize

ROOT = Path(__file__).parent


class AppHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send(
                HTTPStatus.OK,
                b'{"status":"ok","service":"school-meal-balance","mode":"deterministic_demo","data":"synthetic_estimates"}',
                "application/json; charset=utf-8",
            )
            return
        if path in {"/", "/index.html"}:
            self._send(HTTPStatus.OK, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        self._send(HTTPStatus.NOT_FOUND, b'{"error":"not found"}', "application/json; charset=utf-8")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/optimize":
            self._send(HTTPStatus.NOT_FOUND, b'{"error":"not found"}', "application/json; charset=utf-8")
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 20_000:
                raise ValueError("요청이 너무 큽니다.")
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            result = optimize(payload)
            self._send(HTTPStatus.OK, json.dumps(result, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        except (json.JSONDecodeError, ValueError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, json.dumps({"error": str(exc)}, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:  # keep terminal readable
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="다음 급식: 청소년 식단 밸런스 데모 서버")
    parser.add_argument("--port", type=int, default=8103, help="서버 포트 (기본값: 8103)")
    args = parser.parse_args()
    print(f"School Meal Balance: http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), AppHandler).serve_forever()
