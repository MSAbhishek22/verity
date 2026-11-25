# StaleBench-20 — measured results

Run: 25 Nov 2026, with `python3 benchmark/run_bench.py`.
Mode: **offline**. The checker (app/stale.py) was fed the evidence
sentence stored in stalebench20.json for each claim — the same checker
code the live /api/stale-check route runs, with stored sources instead
of network fetches, so the run can be repeated by anyone. Nothing in
this run was fetched live.

Result:
- Detection accuracy: **20/20 = 100%** (a changed item counts as
  detected when it gets a CHANGED or STALE verdict; an unchanged item
  counts when it gets FRESH).
- Exact verdict match: **20/20 = 100%**.

Per claim (old value -> new value):

| Claim | Expected | Got |
|---|---|---|
| Solar system has 9 planets | CHANGED | CHANGED (9 -> eight) |
| World population is 7 billion | CHANGED | CHANGED (7 -> 8.2) |
| India's population is 1.38 billion | CHANGED | CHANGED (1.38 -> 1.45) |
| EU has 28 member countries | CHANGED | CHANGED (28 -> 27) |
| Euro is used by 19 countries | CHANGED | CHANGED (19 -> 20) |
| Latest Android is version 12 | CHANGED | CHANGED (version 12 -> version 16) |
| PAN–Aadhaar deadline 31 March 2023 | CHANGED | CHANGED (31 March 2023 -> 30 June 2023) |
| Forever stamp costs 58 cents | CHANGED | CHANGED (58 -> 78) |
| Webb will launch on 18 December 2021 | CHANGED | CHANGED (18 December 2021 -> 25 December 2021) |
| Paris Olympics will open on 26 July 2024 | STALE | STALE (date passed, spoken of as future) |
| Burj Khalifa is 828 metres | FRESH | FRESH |
| Water boils at 100 degrees Celsius | FRESH | FRESH |
| First Moon landing 20 July 1969 | FRESH | FRESH |
| India independent on 15 August 1947 | FRESH | FRESH |
| Speed of light 299,792 km/s | FRESH | FRESH |
| Everest is 8,848.86 metres | FRESH | FRESH |
| 2016 Olympics in Rio de Janeiro | FRESH | FRESH |
| Python first released in 1991 | FRESH | FRESH |
| Adult skeleton has 206 bones | FRESH | FRESH |
| COVID-19 declared a pandemic 11 March 2020 | FRESH | FRESH |

Honest limits of this bench: 20 claims is a small set, and the evidence
sentences were written down by hand from the named sources when the
bench was built. A 100% score on 20 hand-picked claims does not mean
the checker is right on every real answer. It means the checker passes
this fixed, public test — and anyone can re-run it and check.
