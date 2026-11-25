"""StaleBench-20 runner — offline, repeatable, no network.

    python3 benchmark/run_bench.py

What it does: for each of the 20 claims in stalebench20.json, it hands
StaleCheck (app/stale.py) the claim and the stored evidence sentence for
that claim — the same checker code the live /api/stale-check route runs,
fed from a file instead of the network, so the run can be repeated and
checked by hand. It prints one line per claim and a final accuracy.

What it does NOT do: it does not fetch anything live. The evidence
sentences were written down from the named sources when the bench was
built (see each item's note). A claim counts as detected when an item
expected to be CHANGED or STALE gets a CHANGED or STALE verdict, and an
item expected to be FRESH gets a FRESH verdict. The exact-match rate
(verdict exactly as expected) is printed too.

The number this script prints is the only StaleBench number Verity
reports. If it drops, the README and landing page must be corrected.
"""

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import stale  # noqa: E402

STALE_LIKE = ("STALE", "CHANGED")


def run(data):
    today = datetime.date.fromisoformat(data["as_of"])
    rows = []
    for item in data["items"]:
        evidence = [{
            "title": item["evidence_source_name"],
            "url": item["evidence_url"],
            "content": item["evidence_text"],
            "provider": "stalebench",
        }]
        result = stale.check_answer(
            item["answer"], item["generated_on"],
            fetcher=lambda claim, ev=evidence: ev, today=today)
        got = result["claims"][0]["verdict"] if result["claims"] else "NO CLAIM"
        expected = item["expected"]
        detected = (got in STALE_LIKE) if expected in STALE_LIKE \
            else (got == "FRESH")
        rows.append({
            "id": item["id"], "expected": expected, "got": got,
            "exact": got == expected, "detected": detected,
            "old_value": result["claims"][0]["old_value"] if result["claims"] else "",
            "new_value": result["claims"][0]["new_value"] if result["claims"] else "",
        })
    return rows


def main():
    path = os.path.join(ROOT, "benchmark", "stalebench20.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    rows = run(data)
    print(f"StaleBench-20 — as of {data['as_of']} — offline run, "
          "stored evidence, no network")
    print("-" * 78)
    for row in rows:
        mark = "ok  " if row["detected"] else "MISS"
        exact = "exact" if row["exact"] else "     "
        print(f"{mark} {exact} {row['id']:<34} expected {row['expected']:<8} "
              f"got {row['got']:<10} {row['old_value']} -> {row['new_value']}")
    print("-" * 78)
    detected = sum(1 for r in rows if r["detected"])
    exact = sum(1 for r in rows if r["exact"])
    print(f"Detection accuracy: {detected}/{len(rows)} = "
          f"{round(100 * detected / len(rows))}%")
    print(f"Exact verdict match: {exact}/{len(rows)} = "
          f"{round(100 * exact / len(rows))}%")
    return 0 if detected == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
