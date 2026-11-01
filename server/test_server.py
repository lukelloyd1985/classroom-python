import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

import server


def call(base, path, data=None, pin=None):
    headers = {"Content-Type": "application/json"}
    if pin:
        headers["X-Admin-Pin"] = pin
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(base + path, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cfg = server.Config(data_dir=cls.tmp.name, cpu_seconds=1, wall_seconds=4, max_procs=3, pin="1234")
        cls.httpd = server.make_server(cfg, "127.0.0.1", 0)
        cls.base = "http://127.0.0.1:%d" % cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.tmp.cleanup()

    def run_code(self, code, client="c1", stdin=None, timeout=8):
        st, r = call(self.base, "/api/run", {"client": client, "code": code})
        self.assertEqual(st, 200, r)
        sid, pos, out = r["id"], 0, ""
        sent = False
        end = time.time() + timeout
        while time.time() < end:
            if stdin is not None and not sent:
                time.sleep(0.3)
                call(self.base, "/api/stdin", {"id": sid, "text": stdin})
                sent = True
            st, p = call(self.base, "/api/poll?id=%s&pos=%d" % (sid, pos))
            out += p["out"]
            pos = p["pos"]
            if p["done"]:
                return out
            time.sleep(0.1)
        self.fail("timed out; output so far: %r" % out)

    def test_static_and_config(self):
        st, cfg = call(self.base, "/api/config")
        self.assertEqual((st, cfg["mode"]), (200, "client"))
        with urllib.request.urlopen(self.base + "/") as r:
            self.assertIn(b"<html", r.read().lower())
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(self.base + "/../server/server.py")
        self.assertEqual(cm.exception.code, 404)
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(self.base + "/%2e%2e/server/server.py")
        self.assertEqual(cm.exception.code, 404)

    def test_hello_and_traceback(self):
        self.assertEqual(self.run_code("print('hi', 7 // 2)"), "hi 3\n")
        out = self.run_code("print(f'x{1+1}')\nprint(1/0)")
        self.assertIn("x2", out)
        self.assertIn("ZeroDivisionError", out)

    def test_input(self):
        out = self.run_code("n = input('name? ')\nprint('hello ' + n)", stdin="Sam\n")
        self.assertEqual(out, "name? hello Sam\n")

    def test_infinite_loop_cpu_limit(self):
        out = self.run_code("while True: pass", timeout=8)
        self.assertIn("endless loop", out)

    def test_memory_limit(self):
        out = self.run_code("x = bytearray(2 * 1024**3)\nprint('no')")
        self.assertNotIn("no\n", out)
        self.assertIn("MemoryError", out)

    def test_output_limit(self):
        out = self.run_code("while True: print('x' * 1000)")
        self.assertIn("too much output", out)

    def test_runs_are_isolated(self):
        a = self.run_code("open('mine.txt', 'w').write('A')\nimport os\nprint(sorted(os.listdir('.')))", client="a")
        b = self.run_code("import os\nprint(sorted(os.listdir('.')))", client="b")
        self.assertEqual(a, "['main.py', 'mine.txt']\n")
        self.assertEqual(b, "['main.py']\n")

    def test_no_network_when_sandboxed(self):
        if not self.httpd.handler.mgr.net_sandbox:
            self.skipTest("unshare -rn not available here")
        out = self.run_code("import socket\ns = socket.socket()\ns.settimeout(2)\n"
                            "try:\n    s.connect(('127.0.0.1', %d))\n    print('CONNECTED')\n"
                            "except OSError:\n    print('blocked')" % self.httpd.server_address[1])
        self.assertEqual(out, "blocked\n")

    def test_new_run_replaces_old_and_kill(self):
        st, r = call(self.base, "/api/run", {"client": "k", "code": "import time\ntime.sleep(60)"})
        call(self.base, "/api/run", {"client": "k", "code": "print(1)"})
        time.sleep(0.5)
        st, p = call(self.base, "/api/poll?id=%s&pos=0" % r["id"])
        self.assertTrue(p["done"])
        st, r = call(self.base, "/api/run", {"client": "k2", "code": "import time\ntime.sleep(60)"})
        call(self.base, "/api/kill", {"id": r["id"]})
        time.sleep(0.5)
        st, p = call(self.base, "/api/poll?id=%s&pos=0" % r["id"])
        self.assertTrue(p["done"])
        self.assertIn("[Stopped]", p["out"])

    def test_busy(self):
        ids = []
        for i in range(3):
            st, r = call(self.base, "/api/run", {"client": "busy%d" % i, "code": "import time\ntime.sleep(30)"})
            self.assertEqual(st, 200)
            ids.append(r["id"])
        st, r = call(self.base, "/api/run", {"client": "busy9", "code": "print(1)"})
        self.assertEqual((st, r["error"]), (503, "busy"))
        call(self.base, "/api/admin/killall", {}, pin="1234")
        time.sleep(0.5)
        st, r = call(self.base, "/api/run", {"client": "busy9", "code": "print(1)"})
        self.assertEqual(st, 200)

    def test_admin_mode_requires_pin_and_persists(self):
        st, r = call(self.base, "/api/admin/mode", {"mode": "server"}, pin="0000")
        self.assertEqual(st, 403)
        st, r = call(self.base, "/api/admin/mode", {"mode": "server"}, pin="1234")
        self.assertEqual((st, r["mode"]), (200, "server"))
        self.assertEqual(call(self.base, "/api/config")[1]["mode"], "server")
        self.assertEqual(server.State(self.httpd.handler.cfg).mode, "server")
        st, r = call(self.base, "/api/admin/mode", {"mode": "bogus"}, pin="1234")
        self.assertEqual(st, 400)
        call(self.base, "/api/admin/mode", {"mode": "client"}, pin="1234")
        st, r = call(self.base, "/api/admin/status", pin="1234")
        self.assertEqual(st, 200)
        self.assertIn("running", r)

    def test_admin_reset_counter(self):
        n = call(self.base, "/api/config")[1]["reset"]
        st, r = call(self.base, "/api/admin/reset", {}, pin="0000")
        self.assertEqual(st, 403)
        self.assertEqual(call(self.base, "/api/config")[1]["reset"], n)
        st, r = call(self.base, "/api/admin/reset", {}, pin="1234")
        self.assertEqual((st, r["reset"]), (200, n + 1))
        self.assertEqual(server.State(self.httpd.handler.cfg).reset, n + 1)


if __name__ == "__main__":
    unittest.main()
