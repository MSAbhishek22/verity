"""StaleCheck tests — Python stdlib unittest, no network required.

Run from the project root:
    python3 -m unittest discover -s tests -v

The live search path is never called here: checkers are fed fake
fetchers, and the route test patches search.search. The StaleBench
test runs the bench runner offline against the stored evidence,
exactly as benchmark/run_bench.py does.
"""

import datetime
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
sys.path.insert(0, ROOT)

import search  # noqa: E402
import service  # noqa: E402
import stale  # noqa: E402

TODAY = datetime.date(2026, 11, 25)


def source(content, title="S", url="https://example.test/s", provider="test"):
    return [{"title": title, "url": url, "content": content,
             "provider": provider}]


class TestExtractValues(unittest.TestCase):
    def test_long_date(self):
        values = stale.extract_values("The deadline is 31 March 2023.")
        self.assertEqual(values, [{"kind": "date", "raw": "31 March 2023",
                                   "value": "2023-03-31"}])

    def test_iso_and_us_dates(self):
        self.assertEqual(
            stale.extract_values("It starts on 2024-07-26 today")[0]["value"],
            "2024-07-26")
        self.assertEqual(
            stale.extract_values("It starts July 26, 2024 today")[0]["value"],
            "2024-07-26")

    def test_version_needs_the_word_or_three_parts(self):
        self.assertEqual(
            stale.extract_values("Running version 3.9 now")[0],
            {"kind": "version", "raw": "version 3.9", "value": "3.9"})
        self.assertEqual(
            stale.extract_values("Running 1.2.3 now")[0]["kind"], "version")

    def test_plain_decimal_is_a_number_not_a_version(self):
        values = stale.extract_values("The population is 8.2 billion.")
        self.assertEqual(values, [{"kind": "number", "raw": "8.2",
                                   "value": "8.2"}])

    def test_comma_number_and_number_word(self):
        self.assertEqual(
            stale.extract_values("It travels 299,792 km per second")[0]["value"],
            "299792")
        self.assertEqual(
            stale.extract_values("It has eight planets")[0],
            {"kind": "number", "raw": "eight", "value": "8"})

    def test_no_stray_number_from_covid_19(self):
        values = stale.extract_values(
            "The WHO declared COVID-19 a pandemic on 11 March 2020.")
        self.assertEqual(values, [{"kind": "date", "raw": "11 March 2020",
                                   "value": "2020-03-11"}])

    def test_bare_year(self):
        self.assertEqual(stale.extract_values("Released in 1991."),
                         [{"kind": "year", "raw": "1991", "value": "1991"}])


class TestExtractClaims(unittest.TestCase):
    def test_only_sentences_with_values_are_claims(self):
        claims = stale.extract_claims(
            "The sky is blue and clear. The tower is 828 metres tall. "
            "Nobody knows why.")
        self.assertEqual(len(claims), 1)
        self.assertIn("828", claims[0]["text"])

    def test_bullet_lines_are_claims(self):
        claims = stale.extract_claims(
            "- The deadline is 31 March 2023\n- It has 206 bones")
        self.assertEqual(len(claims), 2)


class TestCheckClaim(unittest.TestCase):
    def _check(self, text, sources):
        claim = stale.extract_claims(text)[0]
        return stale.check_claim(claim, sources, TODAY)

    def test_fresh_when_live_source_confirms_same_value(self):
        out = self._check(
            "The Burj Khalifa in Dubai is 828 metres tall.",
            source("The Burj Khalifa in Dubai is 828 metres tall."))
        self.assertEqual(out["verdict"], "FRESH")
        self.assertEqual(out["new_value"], "828")
        self.assertEqual(out["fetched_on"], "2026-11-25")
        self.assertEqual(out["source_url"], "https://example.test/s")

    def test_changed_when_live_source_has_new_value(self):
        out = self._check(
            "Our solar system has 9 planets.",
            source("The Solar System has eight planets in total."))
        self.assertEqual(out["verdict"], "CHANGED")
        self.assertEqual(out["old_value"], "9")
        self.assertEqual(out["new_value"], "eight")

    def test_stale_when_future_claim_date_has_passed(self):
        out = self._check(
            "The Paris Olympics will open on 26 July 2024.",
            source("The Paris 2024 Olympic Games opened on 26 July 2024."))
        self.assertEqual(out["verdict"], "STALE")

    def test_loose_sentence_with_other_number_does_not_overturn(self):
        """A loosely related sentence carrying a different quantity (the
        Jeddah Tower case from the live smoke) must not beat a source
        that confirms the claim itself."""
        sources = [
            {"title": "Jeddah Tower", "url": "https://example.test/j",
             "content": "Jeddah Tower is planned to be the first "
                        "1-kilometre-tall building, taller than the "
                        "Burj Khalifa.",
             "provider": "test"},
            {"title": "Burj Khalifa", "url": "https://example.test/b",
             "content": "The Burj Khalifa in Dubai is 828 metres tall.",
             "provider": "test"},
        ]
        out = self._check(
            "The Burj Khalifa in Dubai is 828 metres tall.", sources)
        self.assertEqual(out["verdict"], "FRESH")

    def test_better_matching_new_value_still_wins(self):
        sources = [
            {"title": "Old", "url": "https://example.test/o",
             "content": "The stamp was 58.",
             "provider": "test"},
            {"title": "New", "url": "https://example.test/n",
             "content": "The stamp costs 78 cents today.",
             "provider": "test"},
        ]
        out = self._check("The stamp costs 58 cents.", sources)
        self.assertEqual(out["verdict"], "CHANGED")
        self.assertEqual(out["new_value"], "78")

    def test_unverified_when_fetch_failed(self):
        out = self._check("The tower is 828 metres tall.", None)
        self.assertEqual(out["verdict"], "UNVERIFIED")

    def test_unverified_when_no_sources(self):
        out = self._check("The tower is 828 metres tall.", [])
        self.assertEqual(out["verdict"], "UNVERIFIED")

    def test_unverified_when_nothing_matches(self):
        out = self._check(
            "The tower is 828 metres tall.",
            source("Photosynthesis converts light into chemical energy."))
        self.assertEqual(out["verdict"], "UNVERIFIED")


class TestCheckAnswer(unittest.TestCase):
    def test_score_counts_stale_and_changed(self):
        def fetcher(claim):
            if "planets" in claim["text"]:
                return source("The Solar System has eight planets.")
            return source("The Burj Khalifa in Dubai is 828 metres tall.")
        out = stale.check_answer(
            "Our solar system has 9 planets. "
            "The Burj Khalifa in Dubai is 828 metres tall.",
            "2020-05-01", fetcher=fetcher, today=TODAY)
        self.assertEqual(out["claims_found"], 2)
        self.assertEqual(out["counts"]["CHANGED"], 1)
        self.assertEqual(out["counts"]["FRESH"], 1)
        self.assertEqual(out["stale_score"], 50)

    def test_fetcher_exception_means_unverified_never_fresh(self):
        def boom(claim):
            raise RuntimeError("network down")
        out = stale.check_answer(
            "The tower is 828 metres tall.", "2022-01-01",
            fetcher=boom, today=TODAY)
        self.assertEqual(out["counts"]["UNVERIFIED"], 1)
        self.assertEqual(out["counts"]["FRESH"], 0)

    def test_answer_without_claims_scores_zero(self):
        out = stale.check_answer(
            "A short note with nothing to check.", "2022-01-01",
            fetcher=lambda claim: [], today=TODAY)
        self.assertEqual(out["claims_found"], 0)
        self.assertEqual(out["stale_score"], 0)


class TestStaleBench(unittest.TestCase):
    def setUp(self):
        path = os.path.join(ROOT, "benchmark", "stalebench20.json")
        with open(path, encoding="utf-8") as fh:
            self.data = json.load(fh)

    def test_dataset_shape(self):
        items = self.data["items"]
        self.assertEqual(len(items), 20)
        stale_like = [i for i in items if i["expected"] in ("CHANGED", "STALE")]
        fresh = [i for i in items if i["expected"] == "FRESH"]
        self.assertEqual(len(stale_like), 10)
        self.assertEqual(len(fresh), 10)
        for item in items:
            self.assertTrue(item["evidence_text"])
            self.assertTrue(item["evidence_source_name"])
            self.assertTrue(item["evidence_url"].startswith("http"))
            self.assertTrue(item["note"])

    def test_runner_detects_everything_offline(self):
        import run_bench
        rows = run_bench.run(self.data)
        detected = sum(1 for r in rows if r["detected"])
        self.assertEqual(detected, 20)
        exact = sum(1 for r in rows if r["exact"])
        self.assertEqual(exact, 20)


class TestStaleCheckRoute(unittest.TestCase):
    def _post(self, payload):
        body = payload if isinstance(payload, bytes) \
            else json.dumps(payload).encode()
        return service.handle("POST", "/api/stale-check", {}, body)

    def test_happy_path_with_mocked_search(self):
        orig = search.search
        search.search = lambda q, max_results=5: (
            source("The Burj Khalifa in Dubai is 828 metres tall.",
                   title="Burj", url="https://example.test/burj",
                   provider="wikipedia"), "wikipedia", False)
        try:
            status, _, payload = self._post({
                "answer": "The Burj Khalifa in Dubai is 828 metres tall.",
                "generated_on": "2022-01-01",
            })
        finally:
            search.search = orig
        self.assertEqual(status, 200)
        body = json.loads(payload)
        self.assertEqual(body["claims_found"], 1)
        self.assertEqual(body["claims"][0]["verdict"], "FRESH")
        self.assertEqual(body["stale_score"], 0)
        self.assertIn("checked_on", body)

    def test_rejects_short_answer(self):
        status, _, payload = self._post(
            {"answer": "short", "generated_on": "2022-01-01"})
        self.assertEqual(status, 400)
        self.assertIn("answer_too_short", payload.decode())

    def test_rejects_bad_and_future_dates(self):
        status, _, payload = self._post(
            {"answer": "The tower is 828 metres tall.",
             "generated_on": "not-a-date"})
        self.assertEqual(status, 400)
        self.assertIn("invalid_generated_on", payload.decode())
        status, _, payload = self._post(
            {"answer": "The tower is 828 metres tall.",
             "generated_on": "2999-01-01"})
        self.assertEqual(status, 400)
        self.assertIn("generated_on_in_future", payload.decode())

    def test_rejects_invalid_json_and_oversized_body(self):
        status, _, _ = self._post(b"{not json")
        self.assertEqual(status, 400)
        status, _, _ = self._post(b"x" * (service.MAX_STALE_BODY_BYTES + 1))
        self.assertEqual(status, 413)

    def test_homepage_leads_with_stalecheck(self):
        status, _, payload = service.handle("GET", "/", {}, None)
        self.assertEqual(status, 200)
        self.assertIn(b"StaleCheck", payload)
        self.assertIn(b"staleForm", payload)
        self.assertIn(b"Research mode", payload)


if __name__ == "__main__":
    unittest.main()
