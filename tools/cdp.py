# -*- coding: utf-8 -*-
"""Minimal Chrome DevTools Protocol client (standard library only) used to QA the viewer with a real headless Chrome: load a page, run JavaScript, click, press keys,
emulate a viewport and save a PNG of the WHOLE page (panel, menus and WebGL canvas together).

  # once (outside any sandbox): start a headless Chrome that listens on 9222
  ~/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell --no-sandbox --remote-debugging-port=9222 \
      --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --hide-scrollbars --user-data-dir=/tmp/c4qa about:blank &
  # then
  from cdp import Page
  p = Page(); p.size(1440, 900); p.go('http://127.0.0.1:8765/index.html'); p.wait('window.__dbg&&document.getElementById("ver")'); p.shot('/tmp/x.png')"""
import socket, base64, hashlib, os, json, struct, time, urllib.request


class WS:
    def __init__(self, host, port, path):
        self.s = socket.create_connection((host, port), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        req = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        self.s.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf: buf += self.s.recv(4096)
        head, self.rest = buf.split(b"\r\n\r\n", 1)
        if b" 101 " not in head.split(b"\r\n")[0]: raise RuntimeError(head.decode(errors="replace"))

    def _read(self, n):
        out = b""
        while len(out) < n:
            if self.rest:
                take = self.rest[:n - len(out)]; self.rest = self.rest[len(take):]; out += take
            else:
                chunk = self.s.recv(n - len(out))
                if not chunk: raise EOFError("socket closed")
                out += chunk
        return out

    def send(self, text):
        data = text.encode(); n = len(data); mask = os.urandom(4)
        hdr = bytearray([0x81])
        if n < 126: hdr.append(0x80 | n)
        elif n < 65536: hdr.append(0x80 | 126); hdr += struct.pack(">H", n)
        else: hdr.append(0x80 | 127); hdr += struct.pack(">Q", n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.s.sendall(bytes(hdr) + mask + masked)

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2); fin = b1 & 0x80; op = b1 & 0x0F; n = b2 & 0x7F
            if n == 126: n = struct.unpack(">H", self._read(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            if op == 0x9: continue                                   # ping
            if op == 0x8: raise EOFError("closed")
            msg += payload
            if fin: return msg.decode()


class Page:
    def __init__(self, host="127.0.0.1", port=9222):
        self.host, self.port = host, port
        t = json.load(urllib.request.urlopen(f"http://{host}:{port}/json/new?about:blank", data=b"")) if False else None
        req = urllib.request.Request(f"http://{host}:{port}/json/new?about:blank", method="PUT")
        t = json.load(urllib.request.urlopen(req))
        self.tid = t["id"]; self.ws = WS(host, port, t["webSocketDebuggerUrl"].split(str(port))[1]); self.n = 0
        self.call("Page.enable"); self.call("Runtime.enable")

    def call(self, method, **params):
        self.n += 1; i = self.n
        self.ws.send(json.dumps({"id": i, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == i:
                if "error" in m: raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})

    def size(self, w, h, scale=1, mobile=False):
        self.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=scale, mobile=mobile)

    def go(self, url, settle=1.0):
        self.call("Page.navigate", url=url); time.sleep(settle)

    def eval(self, js, await_=True):
        r = self.call("Runtime.evaluate", expression=js, returnByValue=True, awaitPromise=await_, timeout=120000)
        if "exceptionDetails" in r: raise RuntimeError(json.dumps(r["exceptionDetails"], ensure_ascii=False)[:600])
        return r.get("result", {}).get("value")

    def wait(self, cond, timeout=90, step=0.5):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if self.eval(f"Boolean({cond})", False): return True
            except Exception:
                pass
            time.sleep(step)
        raise TimeoutError(cond)

    def shot(self, path, w=None, h=None, clip=None):
        p = {"format": "png"}
        if clip: p["clip"] = {"x": clip[0], "y": clip[1], "width": clip[2], "height": clip[3], "scale": 1}
        r = self.call("Page.captureScreenshot", **p)
        open(path, "wb").write(base64.b64decode(r["data"])); return path

    def click(self, x, y, button="left"):
        for t in ("mousePressed", "mouseReleased"): self.call("Input.dispatchMouseEvent", type=t, x=x, y=y, button=button, clickCount=1)

    def key(self, key, code=None):
        for t in ("keyDown", "keyUp"): self.call("Input.dispatchKeyEvent", type=t, key=key, code=code or key)

    def close(self):
        try: urllib.request.urlopen(f"http://{self.host}:{self.port}/json/close/{self.tid}")
        except Exception: pass
