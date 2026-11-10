"""Read/write smoke test for at most 35 local fake students.

Runs only against loopback; it will never send load to Railway or a public host.
Uses dummy signed Telegram data, a disposable SQLite database, and no secrets.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import hmac
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request

DUMMY_TOKEN = "111111:test-only-token"


def signature(uid: int) -> str:
    data = {
        "user": json.dumps({"id": uid, "first_name": "Fake Student"}, separators=(",", ":")),
        "auth_date": str(int(time.time())),
    }
    secret = hmac.new(b"WebAppData", DUMMY_TOKEN.encode(), hashlib.sha256).digest()
    canonical = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    data["hash"] = hmac.new(secret, canonical.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(data)


def exercise_student(base: str, number: int) -> list[float]:
    uid = 900_000_000 + number
    auth = signature(uid)
    timings = []

    def call(path: str, payload: dict | None = None):
        headers = {"X-Telegram-Init-Data": auth}
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            base + path, data=body, headers=headers,
            method="POST" if body is not None else "GET",
        )
        start = time.perf_counter()
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError(f"Unexpected status {response.status} for {path}")
            result = json.loads(response.read())
        timings.append((time.perf_counter() - start) * 1000)
        return result

    call("/api/consent", {})
    catalog = call("/api/catalog")
    assert len(catalog["subjects"]) == 6
    lesson = call("/api/lessons/ergonomika")
    assert lesson["id"] == "ergonomika"
    questions = lesson["questions"]
    assert len(questions) > 0
    result = call("/api/attempts", {
        "lesson_id": lesson["id"],
        "question_ids": [q["id"] for q in questions],
        "answers": [0 for _ in questions],
    })
    assert result["total"] == len(questions)
    progress = call("/api/progress")
    assert progress["attempts_count"] == 1
    return timings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:17890")
    parser.add_argument("--students", type=int, default=35)
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.base)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to load test a non-local server.")
    if not 1 <= args.students <= 35:
        raise SystemExit("Student count must be between 1 and 35.")
    started = time.perf_counter()
    all_timings: list[float] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.students) as pool:
        results = list(pool.map(lambda n: exercise_student(args.base.rstrip("/"), n),
                                range(args.students)))
    for timings in results:
        all_timings.extend(timings)
    sorted_ms = sorted(all_timings)
    p95 = sorted_ms[min(len(sorted_ms) - 1, int(len(sorted_ms) * .95))]
    print(json.dumps({
        "status": "pass",
        "students": args.students,
        "successful_requests": len(all_timings),
        "median_ms": round(statistics.median(all_timings), 1),
        "p95_ms": round(p95, 1),
        "elapsed_s": round(time.perf_counter() - started, 1),
        "note": "Synthetic short CI workload only; not real-world load capacity guarantee",
    }))


if __name__ == "__main__":
    main()
