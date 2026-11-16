#!/usr/bin/env python3
"""Minimal Chrome DevTools client for pages that require a real browser.

Bank of Taiwan's rate site sometimes answers plain HTTP clients with an
Imperva "Challenge Validation" page. A local Chrome/Chromium solves that
check; this module then reads the page (or runs fetch() inside it) and
returns the text. No third-party browser library is required.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import struct
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class BrowserFetchError(RuntimeError):
    pass


def find_chrome() -> Optional[str]:
    env = os.environ.get("CHROME_PATH")
    candidates = [
        env,
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/local/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = shutil.which(candidate) or (candidate if os.path.isfile(candidate) and os.access(candidate, os.X_OK) else None)
        if path:
            return path
    return None


class _WebSocket:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buf = b""

    def send_text(self, text: str) -> None:
        data = text.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + mask + masked)

    def _read_exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise BrowserFetchError("Chrome DevTools 連線中斷")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv_text(self) -> str:
        while True:
            header = self._read_exact(2)
            opcode = header[0] & 0x0F
            length = header[1] & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            if header[1] & 0x80:
                mask = self._read_exact(4)
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read_exact(length)))
            else:
                payload = self._read_exact(length)
            if opcode == 0x9:  # ping
                pong = bytearray([0x8A, 0x80 | len(payload)])
                mask = os.urandom(4)
                pong.extend(mask)
                pong.extend(b ^ mask[i % 4] for i, b in enumerate(payload))
                self.sock.sendall(bytes(pong))
                continue
            if opcode == 0x8:
                raise BrowserFetchError("Chrome DevTools 關閉連線")
            if opcode == 0x1:
                return payload.decode("utf-8", errors="replace")


def _connect_ws(ws_url: str) -> _WebSocket:
    parsed = urlparse(ws_url)
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    sock = socket.create_connection((parsed.hostname, port), timeout=30)
    sock.settimeout(30)
    key = __import__("base64").b64encode(os.urandom(16)).decode()
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {parsed.hostname}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(request.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise BrowserFetchError("Chrome DevTools 握手失敗")
        buf += chunk
    status = buf.split(b"\r\n", 1)[0]
    if b" 101 " not in status:
        raise BrowserFetchError(f"Chrome DevTools 握手被拒: {status.decode(errors='replace')}")
    extra = buf.split(b"\r\n\r\n", 1)[1]
    ws = _WebSocket(sock)
    ws.buf = extra
    return ws


class ChromeSession:
    """One headless Chrome, reused so the anti-bot cookie is solved once."""

    def __init__(self, chrome_path: str):
        self.chrome_path = chrome_path
        self.proc: Optional[subprocess.Popen] = None
        self.ws: Optional[_WebSocket] = None
        self._next_id = 0
        self.port = 0

    def __enter__(self) -> "ChromeSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def start(self) -> None:
        profile = Path(os.environ.get("TMPDIR", "/tmp")) / f"bot-chrome-{os.getpid()}"
        profile.mkdir(parents=True, exist_ok=True)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        self.port = sock.getsockname()[1]
        sock.close()
        self.proc = subprocess.Popen(
            [
                self.chrome_path,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--remote-debugging-port={self.port}",
                "--remote-allow-origins=*",
                f"--user-data-dir={profile}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        version_url = f"http://127.0.0.1:{self.port}/json/version"
        last_error = None
        for _ in range(50):
            if self.proc.poll() is not None:
                raise BrowserFetchError("Chrome 啟動後立即結束")
            try:
                with urllib.request.urlopen(version_url, timeout=1) as resp:
                    json.loads(resp.read().decode())
                break
            except Exception as exc:  # noqa: BLE001 - retry until the port listens
                last_error = exc
                time.sleep(0.2)
        else:
            raise BrowserFetchError(f"無法連上 Chrome DevTools: {last_error}")

        new_url = f"http://127.0.0.1:{self.port}/json/new?about:blank"
        req = urllib.request.Request(new_url, method="PUT", data=b"")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                target = json.loads(resp.read().decode())
        except Exception:
            with urllib.request.urlopen(new_url, timeout=10) as resp:
                target = json.loads(resp.read().decode())
        self.ws = _connect_ws(target["webSocketDebuggerUrl"])
        self.call("Page.enable")
        self.call("Runtime.enable")

    def close(self) -> None:
        if self.ws is not None:
            try:
                self.ws.sock.close()
            except Exception:
                pass
            self.ws = None
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def call(self, method: str, params: Optional[dict] = None, timeout: float = 30) -> dict:
        if self.ws is None:
            raise BrowserFetchError("Chrome 尚未啟動")
        self._next_id += 1
        msg_id = self._next_id
        self.ws.send_text(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.ws.sock.settimeout(max(0.5, deadline - time.time()))
            try:
                message = json.loads(self.ws.recv_text())
            except socket.timeout:
                continue
            if message.get("id") == msg_id:
                if "error" in message:
                    raise BrowserFetchError(f"CDP {method} 失敗: {message['error']}")
                return message.get("result") or {}
        raise BrowserFetchError(f"CDP {method} 逾時")

    def navigate(self, url: str, timeout: float = 60) -> None:
        self.call("Page.navigate", {"url": url}, timeout=timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            state = self.evaluate("document.readyState")
            title = self.evaluate("document.title") or ""
            if state == "complete" and "Challenge" not in title:
                return
            time.sleep(0.4)
        title = self.evaluate("document.title") or ""
        if "Challenge" in title:
            raise BrowserFetchError(f"瀏覽器仍停在驗證頁: {url}")

    def evaluate(self, expression: str, await_promise: bool = False, timeout: float = 60):
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": await_promise,
                "returnByValue": True,
            },
            timeout=timeout,
        )
        remote = result.get("result") or {}
        if remote.get("subtype") == "error" or result.get("exceptionDetails"):
            details = result.get("exceptionDetails") or remote
            raise BrowserFetchError(f"頁面腳本失敗: {details}")
        return remote.get("value")

    def fetch_text(self, url: str) -> str:
        """GET a URL from inside the page so the solved cookie is sent."""
        expression = (
            "fetch(" + json.dumps(url) + ", {credentials: 'include'})"
            ".then(async (r) => ({status: r.status, text: await r.text()}))"
        )
        payload = self.evaluate(expression, await_promise=True, timeout=60)
        if not isinstance(payload, dict):
            raise BrowserFetchError(f"瀏覽器 fetch 沒有回傳內容: {url}")
        status = payload.get("status")
        text = payload.get("text") or ""
        if status != 200:
            raise BrowserFetchError(f"瀏覽器 fetch {url} HTTP {status}")
        return text

    def page_html(self) -> str:
        html = self.evaluate("document.documentElement.outerHTML")
        return html or ""
