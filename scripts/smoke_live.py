"""Live smoke test for Verity — hits the REAL Wikipedia API (no Tavily key).

Starts the dev server on a scratch port, then:
  1. GET /            -> 200, contains "Verity"
  2. GET /api/health -> ok
  3. GET /api/status -> provider is wikipedia (no key set)
  4. POST /api/ask   -> real question, real live sources, verdict + claims
  5. POST /api/ask   -> nonsense question, expect NO EVIDENCE (honest)

Run from the project root:
    python3 scripts/smoke_live.py

Requires network access to en.wikipedia.org. Prints a PASS/FAIL summary
and exits non-zero on any failure.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 18081
BASE = f"http://127.0.0.1:{PORT}"

FAILURES = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as resp:
        return resp.status, resp.read()


def post(path, obj):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main():
    env = dict(os.environ)
    env.pop("TAVILY_API_KEY", None)  # force the free Wikipedia path
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "app", "server.py")],
        env={**env, "PORT": str(PORT)},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        # Wait for the server to answer.
        up = False
        for _ in range(30):
            try:
                status, _ = get("/api/health")
                if status == 200:
                    up = True
                    break
            except Exception:
                time.sleep(0.3)
        check("server starts", up)
        if not up:
            return 1

        status, body = get("/")
        check("homepage 200 + contains Verity",
              status == 200 and b"Verity" in body and b"Ask Verity" in body)

        status, body = get("/api/health")
        check("health ok", status == 200 and json.loads(body)["ok"])

        status, body = get("/api/status")
        info = json.loads(body)
        check("status reports wikipedia fallback (no key set)",
              status == 200 and info["provider"] == "wikipedia"
              and info["tavily_configured"] is False,
              f"provider={info.get('provider')}")

        status, body = post("/api/ask", {"question": "How does photosynthesis work?"})
        ans = json.loads(body)
        check("live ask returns 200", status == 200, f"status={status}")
        if status == 200:
            check("live ask uses wikipedia provider",
                  ans["provider"] == "wikipedia", f"provider={ans['provider']}")
            check("live ask returns cited claims",
                  len(ans["claims"]) >= 2,
                  f"{len(ans['claims'])} claims, verdict={ans['verdict']}, "
                  f"score={ans['score']}")
            check("every live claim cites a real source",
                  all(c["source_url"].startswith("https://en.wikipedia.org/wiki/")
                      for c in ans["claims"]))
            check("live verdict is GROUNDED or PARTIAL",
                  ans["verdict"] in ("GROUNDED", "PARTIAL"),
                  f"verdict={ans['verdict']} score={ans['score']}")
            print("\n--- live answer sample ---")
            for claim in ans["claims"][:3]:
                print(f"  [{claim['source_index'] + 1}] {claim['text']}")
            print(f"  verdict={ans['verdict']} score={ans['score']} "
                  f"took={ans['took_ms']}ms")
            print("--------------------------\n")

        status, body = post("/api/ask", {"question": "zxqvkj wobbleflorp zanzibar"})
        ans = json.loads(body)
        check("nonsense question returns NO EVIDENCE honestly",
              status == 200 and ans["verdict"] == "NO EVIDENCE"
              and ans["claims"] == [],
              f"verdict={ans.get('verdict')}")

        status, _ = post("/api/ask", {"question": "hi"})
        check("short question rejected with 400", status == 400)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"\n{'ALL LIVE CHECKS PASSED' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
