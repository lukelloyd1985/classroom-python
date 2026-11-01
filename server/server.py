#!/usr/bin/env python3
"""Classroom Python server (standard library only).

Serves the static web app in ../web and provides:

  * a teacher-controlled "mode" flag (client | server) that every tablet follows
  * server-side execution of student code in resource-limited subprocesses
    (used when mode == "server")

No logins.  Each tablet identifies itself with a random id stored in its
browser; code from one tablet never touches another's (separate temp dir and
process per run).  The teacher admin API is protected by a PIN.
"""
import argparse
import codecs
import json
import os
import resource
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
MODES = ("client", "server")
MAX_CODE = 100 * 1024
MAX_BODY = 256 * 1024
MAX_OUT = 100 * 1024
MAX_STDIN = 4096
ABANDON_AFTER = 20  # seconds without a poll => tablet gone, kill the run
KEEP_FINISHED = 60  # seconds to keep a finished session for late polls


class Busy(Exception):
    pass


class Config(object):
    def __init__(self, **kw):
        self.web_dir = os.path.join(HERE, "..", "web")
        self.data_dir = os.path.join(HERE, "data")
        self.default_mode = "client"
        self.cpu_seconds = 10
        self.wall_seconds = 300
        self.memory_mb = 384
        self.max_procs = 16
        self.python = sys.executable
        self.sandbox = True
        self.pin = None
        for k, v in kw.items():
            setattr(self, k, v)
        self.web_dir = os.path.realpath(self.web_dir)


def detect_net_sandbox():
    """True if `unshare -rn` (no-network user namespace) works here."""
    try:
        r = subprocess.run(["unshare", "-rn", "true"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


class State(object):
    """Persisted teacher settings: the mode flag and a "reset" counter (bumping it makes tablets clear their code)."""

    def __init__(self, cfg):
        self.path = os.path.join(cfg.data_dir, "state.json")
        self.lock = threading.Lock()
        self.mode = cfg.default_mode
        self.reset = 0
        try:
            with open(self.path) as f:
                data = json.load(f)
            if data.get("mode") in MODES:
                self.mode = data["mode"]
            if isinstance(data.get("reset"), int):
                self.reset = data["reset"]
        except Exception:
            pass

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"mode": self.mode, "reset": self.reset}, f)
        os.replace(tmp, self.path)

    def set_mode(self, mode):
        with self.lock:
            self.mode = mode
            self._save()

    def bump_reset(self):
        with self.lock:
            self.reset += 1
            self._save()


class Session(object):
    def __init__(self, sid, client, workdir, proc, cfg):
        self.id = sid
        self.client = client
        self.workdir = workdir
        self.proc = proc
        self.cfg = cfg
        self.lock = threading.Lock()
        self.out = ""
        self.done = False
        self.kill_reason = None
        self.started = time.time()
        self.last_poll = self.started
        self.finished_at = None
        t = threading.Thread(target=self._reader, daemon=True)
        t.start()

    def active(self):
        return not self.done and self.kill_reason is None

    def kill(self, reason):
        with self.lock:
            if self.done:
                return
            if self.kill_reason is None:
                self.kill_reason = reason
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    def _append(self, text):
        with self.lock:
            if self.kill_reason == "output":
                return
            room = MAX_OUT - len(self.out)
            self.out += text[:max(room, 0)]
            over = len(text) > room
        if over:
            self.kill("output")

    def _reader(self):
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        fd = self.proc.stdout.fileno()
        while True:
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            self._append(dec.decode(data))
        self.proc.wait()
        rc = self.proc.returncode
        with self.lock:
            reason = self.kill_reason
        c = self.cfg
        note = None
        if reason == "output":
            note = "Stopped: too much output"
        elif reason == "wall":
            note = "Stopped: the program ran for more than %d seconds" % c.wall_seconds
        elif reason == "stop":
            note = "Stopped"
        elif rc == -signal.SIGXCPU:
            note = ("Stopped: the program used more than %d seconds of computer "
                    "time. Is there an endless loop?" % c.cpu_seconds)
        elif rc is not None and rc < 0 and reason is None:
            note = "Stopped: the program crashed (signal %d)" % -rc
        with self.lock:
            if note:
                if self.out and not self.out.endswith("\n"):
                    self.out += "\n"
                self.out += "[%s]\n" % note
            self.done = True
            self.finished_at = time.time()
        shutil.rmtree(self.workdir, ignore_errors=True)

    def write_stdin(self, text):
        if self.done:
            return False
        try:
            self.proc.stdin.write(text.encode("utf-8"))
            self.proc.stdin.flush()
            return True
        except (BrokenPipeError, ValueError, OSError):
            return False

    def snapshot(self, pos):
        with self.lock:
            self.last_poll = time.time()
            return {"out": self.out[pos:], "pos": len(self.out), "done": self.done}


class Manager(object):
    def __init__(self, cfg, net_sandbox):
        self.cfg = cfg
        self.net_sandbox = net_sandbox and cfg.sandbox
        self.lock = threading.Lock()
        self.sessions = {}
        self.by_client = {}
        t = threading.Thread(target=self._reaper, daemon=True)
        t.start()

    def start(self, client, code):
        c = self.cfg
        with self.lock:
            old = self.sessions.get(self.by_client.get(client))
            if old is not None:
                old.kill("replaced")
            running = len([s for s in self.sessions.values() if s.active()])
            if running >= c.max_procs:
                raise Busy()
            workdir = tempfile.mkdtemp(prefix="cp-")
            try:
                with open(os.path.join(workdir, "main.py"), "w", encoding="utf-8") as f:
                    f.write(code)
                cmd = [c.python, "-I", "-B", "-u", "main.py"]
                if self.net_sandbox:
                    cmd = ["unshare", "-rn"] + cmd
                env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                       "PYTHONIOENCODING": "utf-8", "HOME": workdir}
                proc = subprocess.Popen(
                    cmd, cwd=workdir, env=env, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    start_new_session=True, close_fds=True)
                self._limit(proc.pid)
            except Exception:
                shutil.rmtree(workdir, ignore_errors=True)
                raise
            sid = secrets.token_hex(8)
            s = Session(sid, client, workdir, proc, c)
            self.sessions[sid] = s
            self.by_client[client] = sid
            return s

    def _limit(self, pid):
        c = self.cfg
        mem = c.memory_mb * 1024 * 1024
        # CPU: soft limit sends SIGXCPU (clear message), hard limit is the SIGKILL backstop
        for res, soft, hard in ((resource.RLIMIT_CPU, c.cpu_seconds, c.cpu_seconds + 2),
                                (resource.RLIMIT_AS, mem, mem),
                                (resource.RLIMIT_FSIZE, 1024 * 1024, 1024 * 1024),
                                (resource.RLIMIT_NOFILE, 64, 64),
                                (resource.RLIMIT_CORE, 0, 0)):
            try:
                resource.prlimit(pid, res, (soft, hard))
            except (OSError, ValueError):
                pass

    def get(self, sid):
        with self.lock:
            return self.sessions.get(sid)

    def kill_all(self):
        with self.lock:
            sessions = list(self.sessions.values())
        for s in sessions:
            s.kill("stop")

    def counts(self):
        with self.lock:
            return len([s for s in self.sessions.values() if s.active()])

    def _reaper(self):
        while True:
            time.sleep(1)
            now = time.time()
            with self.lock:
                items = list(self.sessions.items())
            for sid, s in items:
                if s.active():
                    if now - s.last_poll > ABANDON_AFTER:
                        s.kill("abandoned")
                    elif now - s.started > self.cfg.wall_seconds:
                        s.kill("wall")
                elif s.done and now - (s.finished_at or now) > KEEP_FINISHED:
                    with self.lock:
                        self.sessions.pop(sid, None)
                        if self.by_client.get(s.client) == sid:
                            self.by_client.pop(s.client, None)


TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".json": "application/json", ".txt": "text/plain; charset=utf-8",
         ".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "ClassroomPython"
    cfg = None
    state = None
    mgr = None

    def log_message(self, fmt, *args):  # keep the Pi's journal quiet
        pass

    # ---- helpers
    def _json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0 or n > MAX_BODY:
            return None
        try:
            obj = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        return obj if isinstance(obj, dict) else None

    def _admin(self):
        pin = self.headers.get("X-Admin-Pin", "")
        if secrets.compare_digest(pin.encode("utf-8"), self.cfg.pin.encode("utf-8")):
            return True
        time.sleep(0.5)  # slow down guessing
        self._json({"error": "wrong PIN"}, 403)
        return False

    # ---- routing
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/config":
            return self._json(self._config())
        if u.path == "/api/poll":
            q = parse_qs(u.query)
            s = self.mgr.get((q.get("id") or [""])[0])
            if s is None:
                return self._json({"error": "unknown run"}, 404)
            try:
                pos = max(int((q.get("pos") or ["0"])[0]), 0)
            except ValueError:
                pos = 0
            return self._json(s.snapshot(pos))
        if u.path == "/api/admin/status":
            if not self._admin():
                return
            d = self._config()
            d.update({"running": self.mgr.counts(), "maxProcs": self.cfg.max_procs,
                      "networkSandbox": self.mgr.net_sandbox,
                      "python": sys.version.split()[0]})
            return self._json(d)
        if u.path.startswith("/api/"):
            return self._json({"error": "not found"}, 404)
        return self._static(u.path)

    def do_POST(self):
        u = urlparse(self.path)
        data = self._body()
        if data is None:
            return self._json({"error": "bad request"}, 400)
        if u.path == "/api/run":
            client = str(data.get("client", ""))[:64]
            code = data.get("code")
            if not client or not isinstance(code, str) or len(code) > MAX_CODE:
                return self._json({"error": "bad request"}, 400)
            try:
                s = self.mgr.start(client, code)
            except Busy:
                return self._json({"error": "busy"}, 503)
            return self._json({"id": s.id})
        if u.path in ("/api/stdin", "/api/kill"):
            s = self.mgr.get(str(data.get("id", "")))
            if s is None:
                return self._json({"error": "unknown run"}, 404)
            if u.path == "/api/kill":
                s.kill("stop")
                return self._json({"ok": True})
            text = data.get("text")
            if not isinstance(text, str) or len(text) > MAX_STDIN:
                return self._json({"error": "bad request"}, 400)
            return self._json({"ok": s.write_stdin(text)})
        if u.path == "/api/admin/mode":
            if not self._admin():
                return
            if data.get("mode") not in MODES:
                return self._json({"error": "bad mode"}, 400)
            self.state.set_mode(data["mode"])
            return self._json(self._config())
        if u.path == "/api/admin/reset":
            if not self._admin():
                return
            self.state.bump_reset()
            return self._json(self._config())
        if u.path == "/api/admin/killall":
            if not self._admin():
                return
            self.mgr.kill_all()
            return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)

    def _config(self):
        c = self.cfg
        return {"mode": self.state.mode, "reset": self.state.reset,
                "limits": {"cpuSeconds": c.cpu_seconds, "wallSeconds": c.wall_seconds}}

    def _static(self, path):
        if path.endswith("/"):
            path += "index.html"
        full = os.path.realpath(os.path.join(self.cfg.web_dir, path.lstrip("/")))
        root = self.cfg.web_dir
        if full != root and not full.startswith(root + os.sep):
            self.send_error(404)
            return
        if not os.path.isfile(full):
            self.send_error(404)
            return
        with open(full, "rb") as f:
            body = f.read()
        ext = os.path.splitext(full)[1].lower()
        self.send_response(200)
        self.send_header("Content-Type", TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        # vendor libraries never change; app files must refresh when updated
        cache = "max-age=86400" if "/vendor/" in full else "no-cache"
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)


def make_server(cfg, host="0.0.0.0", port=8000):
    os.makedirs(cfg.data_dir, exist_ok=True)
    if not cfg.pin:
        pin_file = os.path.join(cfg.data_dir, "admin_pin.txt")
        try:
            with open(pin_file) as f:
                cfg.pin = f.read().strip()
        except OSError:
            cfg.pin = ""
        if not cfg.pin:
            cfg.pin = "%04d" % secrets.randbelow(10000)
            with open(pin_file, "w") as f:
                f.write(cfg.pin + "\n")
            os.chmod(pin_file, 0o600)
    handler = type("BoundHandler", (Handler,), {})
    handler.cfg = cfg
    handler.state = State(cfg)
    handler.mgr = Manager(cfg, detect_net_sandbox() if cfg.sandbox else False)
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    httpd.request_queue_size = 64
    httpd.handler = handler
    return httpd


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--data-dir", default=os.environ.get("CLASSROOM_DATA", os.path.join(HERE, "data")))
    ap.add_argument("--mode", choices=MODES, default="client",
                    help="mode used until the teacher changes it (default: client)")
    ap.add_argument("--pin", default=os.environ.get("CLASSROOM_PIN"),
                    help="teacher PIN (default: random, saved in <data-dir>/admin_pin.txt)")
    ap.add_argument("--cpu-seconds", type=int, default=10, help="CPU time limit per run")
    ap.add_argument("--wall-seconds", type=int, default=300, help="wall-clock limit per run")
    ap.add_argument("--memory-mb", type=int, default=384, help="memory limit per run")
    ap.add_argument("--max-procs", type=int, default=16, help="max simultaneous runs")
    ap.add_argument("--no-sandbox", action="store_true", help="do not cut off network for student code")
    a = ap.parse_args()
    cfg = Config(data_dir=a.data_dir, default_mode=a.mode, pin=a.pin, cpu_seconds=a.cpu_seconds,
                 wall_seconds=a.wall_seconds, memory_mb=a.memory_mb, max_procs=a.max_procs,
                 sandbox=not a.no_sandbox)
    httpd = make_server(cfg, a.host, a.port)
    print("Classroom Python on http://%s:%d  mode=%s  teacher PIN=%s  network-sandbox=%s" % (
        a.host, httpd.server_address[1], httpd.handler.state.mode, cfg.pin, httpd.handler.mgr.net_sandbox),
        flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
