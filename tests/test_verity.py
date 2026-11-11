"""Verity test suite — Python stdlib unittest, no network required.

Run from the project root:
    python3 -m unittest discover -s tests -v

Live-network behaviour is NOT asserted here (CI must not depend on the
network). The live path is covered by scripts/smoke_live.py, run manually
against the real Wikipedia API; its output is recorded in qa/SMOKE_LIVE.md.
"""

import io
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, ROOT)

import search  # noqa: E402
import service  # noqa: E402
import synthesize  # noqa: E402

FIXTURE_SOURCES = [
    {
        "title": "Tavily API",
        "url": "https://example.test/tavily",
        "content": ("The Tavily API provides web search designed for AI agents. "
                    "Tavily search returns relevant results with content excerpts. "
                    "Developers use Tavily to ground large language models in live web data."),
        "provider": "tavily",
    },
    {
        "title": "Tavily grounding",
        "url": "https://example.test/tavily-grounding",
        "content": ("Tavily is used by developers to ground AI agents in current web data. "
                    "A grounded answer cites the pages it was built from."),
        "provider": "tavily",
    },
    {
        "title": "Photosynthesis",
        "url": "https://example.test/photosynthesis",
        "content": ("Photosynthesis is a process used by plants to convert light energy "
                    "into chemical energy. It takes place in chloroplasts. "
                    "The process produces oxygen as a byproduct."),
        "provider": "wikipedia",
    },
]


class TestKeywords(unittest.TestCase):
    def test_extracts_content_words(self):
        keys = synthesize.keywords("What is the Tavily API used for?")
        self.assertEqual(keys, ["tavily", "api", "used"])

    def test_dedupes_and_drops_stopwords(self):
        keys = synthesize.keywords("How does photosynthesis work, and how does it work?")
        self.assertEqual(keys, ["photosynthesis"])

    def test_empty_question_has_no_keywords(self):
        self.assertEqual(synthesize.keywords("what is it?"), [])


class TestSentences(unittest.TestCase):
    def test_splits_on_sentence_endings(self):
        parts = synthesize.split_sentences(
            "First sentence here. Second one follows! And a third?")
        self.assertEqual(len(parts), 3)

    def test_does_not_split_on_abbreviations(self):
        parts = synthesize.split_sentences(
            "Anoxygenic photosynthesis uses hydrogen sulfide (e.g. H2S) "
            "instead of water. It is a real process.")
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[0].endswith("water."))
        self.assertIn("e.g. H2S", parts[0])

    def test_drops_fragments(self):
        parts = synthesize.split_sentences("Too short. This one is long enough to count.")
        self.assertEqual(parts, ["This one is long enough to count."])


class TestSynthesize(unittest.TestCase):
    def test_exact_score_on_deterministic_case(self):
        sources = [{
            "title": "T",
            "url": "https://example.test/t",
            "content": "Tavily API is a search API. Tavily API returns web results.",
            "provider": "tavily",
        }]
        out = synthesize.synthesize("tavily api", sources)
        # coverage 1.0, diversity 1/3, density 2/4
        # score = 100 * (0.5*1 + 0.3*(1/3) + 0.2*0.5) = 70
        self.assertEqual(out["score"], 70)
        self.assertEqual(out["verdict"], "GROUNDED")
        self.assertEqual(len(out["claims"]), 2)
        for claim in out["claims"]:
            self.assertEqual(claim["source_index"], 0)
            self.assertTrue(claim["source_url"].startswith("https://"))

    def test_every_claim_is_cited(self):
        out = synthesize.synthesize("What is the Tavily API used for?",
                                    FIXTURE_SOURCES)
        self.assertTrue(out["claims"])
        for claim in out["claims"]:
            src = FIXTURE_SOURCES[claim["source_index"]]
            self.assertEqual(claim["source_url"], src["url"])
            self.assertIn(claim["text"], src["content"])

    def test_grounded_when_evidence_is_strong(self):
        out = synthesize.synthesize("What is the Tavily API used for?",
                                    FIXTURE_SOURCES)
        self.assertEqual(out["verdict"], "GROUNDED")
        self.assertGreaterEqual(out["score"], 70)
        self.assertEqual(out["coverage"], 1.0)

    def test_thin_when_evidence_is_weak(self):
        out = synthesize.synthesize("quantum chromodynamics lattice gauge",
                                    FIXTURE_SOURCES)
        self.assertEqual(out["verdict"], "NO EVIDENCE")
        self.assertEqual(out["score"], 0)
        self.assertEqual(out["claims"], [])

    def test_empty_sources_give_no_evidence(self):
        out = synthesize.synthesize("tavily api", [])
        self.assertEqual(out["verdict"], "NO EVIDENCE")
        self.assertEqual(out["claims"], [])

    def test_dedupes_near_identical_sentences(self):
        sources = [{
            "title": "T",
            "url": "https://example.test/t",
            "content": ("Tavily API is a search API. "
                        "Tavily API is a search API. "
                        "Tavily API returns web results."),
            "provider": "tavily",
        }]
        out = synthesize.synthesize("tavily api", sources)
        texts = [c["text"] for c in out["claims"]]
        self.assertEqual(len(texts), len(set(texts)))

    def test_caps_claims_at_six(self):
        content = " ".join(
            f"Tavily API fact number {i} about search." for i in range(12))
        sources = [{"title": "T", "url": "https://example.test/t",
                    "content": content, "provider": "tavily"}]
        out = synthesize.synthesize("tavily api search", sources)
        self.assertLessEqual(len(out["claims"]), 6)

    def test_markdown_export_contains_claims_and_sources(self):
        out = synthesize.synthesize("What is the Tavily API used for?",
                                    FIXTURE_SOURCES)
        md = synthesize.render_markdown(out)
        self.assertIn("GROUNDED", md)
        self.assertIn("https://example.test/tavily", md)
        self.assertIn("## Claims", md)
        self.assertIn("## Sources", md)


class TestSearchParsing(unittest.TestCase):
    def test_tavily_parses_results(self):
        orig = search._post_json
        search._post_json = lambda url, payload, timeout: {
            "results": [
                {"title": "A", "url": "https://a.test/",
                 "content": "Alpha content here."},
                {"title": "B", "url": "https://b.test/",
                 "content": "Beta content here."},
            ]
        }
        try:
            out = search.search_tavily("test", "fake-key")
        finally:
            search._post_json = orig
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["provider"], "tavily")
        self.assertEqual(out[0]["url"], "https://a.test/")

    def test_tavily_returns_empty_list_on_no_results(self):
        orig = search._post_json
        search._post_json = lambda url, payload, timeout: {"results": []}
        try:
            out = search.search_tavily("test", "fake-key")
        finally:
            search._post_json = orig
        self.assertEqual(out, [])

    def test_search_returns_empty_list_when_both_find_nothing(self):
        orig_t, orig_w = search.search_tavily, search.search_wikipedia
        search.search_tavily = lambda q, k, m=5: []
        search.search_wikipedia = lambda q, m=5: []
        os.environ["TAVILY_API_KEY"] = "fake-key"
        try:
            results, provider, fell_back = search.search("zxqvkj wobbleflorp")
        finally:
            search.search_tavily, search.search_wikipedia = orig_t, orig_w
            del os.environ["TAVILY_API_KEY"]
        self.assertEqual(results, [])
        self.assertEqual(provider, "tavily")
        self.assertFalse(fell_back)

    def test_wikipedia_preserves_search_ranking(self):
        """Pages come back keyed by pageid (unordered); results must follow
        the order list=search returned, so the most relevant article wins
        ties in synthesis."""

        def fake_get(url, timeout):
            if "list=search" in url:
                return {"query": {"search": [{"title": "Photosynthesis"},
                                             {"title": "Artificial photosynthesis"}]}}
            # Deliberately unordered: artificial first.
            return {"query": {"pages": {
                "9": {"title": "Artificial photosynthesis",
                      "extract": "Artificial photosynthesis mimics the natural process."},
                "2": {"title": "Photosynthesis",
                      "extract": "Photosynthesis converts light into chemical energy."},
            }}}
        orig = search._get_json
        search._get_json = fake_get
        try:
            out = search.search_wikipedia("photosynthesis", max_results=2)
        finally:
            search._get_json = orig
        self.assertEqual([r["title"] for r in out],
                         ["Photosynthesis", "Artificial photosynthesis"])

    def test_wikipedia_parses_search_and_extracts(self):
        calls = []

        def fake_get(url, timeout):
            calls.append(url)
            if "list=search" in url:
                return {"query": {"search": [{"title": "Paris"}, {"title": "France"}]}}
            return {"query": {"pages": {
                "1": {"title": "Paris",
                      "extract": "Paris is the capital of France. It is known for the Eiffel Tower."},
                "2": {"title": "France",
                      "extract": "France is a country in Western Europe."},
            }}}
        orig = search._get_json
        search._get_json = fake_get
        try:
            out = search.search_wikipedia("paris", max_results=2)
        finally:
            search._get_json = orig
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["provider"], "wikipedia")
        self.assertTrue(out[0]["url"].startswith("https://en.wikipedia.org/wiki/Paris"))

    def test_search_prefers_tavily_when_it_works(self):
        orig_t, orig_w = search.search_tavily, search.search_wikipedia
        search.search_tavily = lambda q, k, m=5: [{"title": "T", "url": "https://t.test/",
                                                   "content": "Tavily wins.", "provider": "tavily"}]
        search.search_wikipedia = lambda q, m=5: [{"title": "W", "url": "https://w.test/",
                                                    "content": "Wiki also.", "provider": "wikipedia"}]
        os.environ["TAVILY_API_KEY"] = "fake-key"
        try:
            results, provider, fell_back = search.search("tavily api")
        finally:
            search.search_tavily, search.search_wikipedia = orig_t, orig_w
            del os.environ["TAVILY_API_KEY"]
        self.assertEqual(provider, "tavily")
        self.assertFalse(fell_back)

    def test_search_falls_back_to_wikipedia_when_tavily_fails(self):
        orig_t, orig_w = search.search_tavily, search.search_wikipedia

        def boom(*args, **kwargs):
            raise search.SearchError("tavily down")
        search.search_tavily = boom
        search.search_wikipedia = lambda q, m=5: [{"title": "W", "url": "https://w.test/",
                                                    "content": "Wiki fallback.", "provider": "wikipedia"}]
        os.environ["TAVILY_API_KEY"] = "fake-key"
        try:
            results, provider, fell_back = search.search("tavily api")
        finally:
            search.search_tavily, search.search_wikipedia = orig_t, orig_w
            del os.environ["TAVILY_API_KEY"]
        self.assertEqual(provider, "wikipedia")
        self.assertTrue(fell_back)

    def test_search_raises_when_all_providers_fail(self):
        orig_t, orig_w = search.search_tavily, search.search_wikipedia

        def boom(*args, **kwargs):
            raise search.SearchError("down")
        search.search_tavily = boom
        search.search_wikipedia = boom
        os.environ["TAVILY_API_KEY"] = "fake-key"
        try:
            with self.assertRaises(search.SearchError):
                search.search("tavily api")
        finally:
            search.search_tavily, search.search_wikipedia = orig_t, orig_w
            del os.environ["TAVILY_API_KEY"]


class TestService(unittest.TestCase):
    def test_homepage_returns_html(self):
        status, ctype, payload = service.handle("GET", "/", {}, None)
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"Verity", payload)
        self.assertIn(b"Ask Verity", payload)

    def test_health(self):
        status, _, payload = service.handle("GET", "/api/health", {}, None)
        self.assertEqual(status, 200)
        body = json.loads(payload)
        self.assertTrue(body["ok"])
        self.assertEqual(body["service"], "verity")

    def test_status_reports_provider_without_secrets(self):
        status, _, payload = service.handle("GET", "/api/status", {}, None)
        body = json.loads(payload)
        self.assertEqual(status, 200)
        self.assertIn(body["provider"], ("tavily", "wikipedia"))
        self.assertNotIn("TAVILY_API_KEY", payload.decode())

    def test_ask_rejects_short_question(self):
        status, _, payload = service.handle(
            "POST", "/api/ask", {}, json.dumps({"question": "hi"}).encode())
        self.assertEqual(status, 400)
        self.assertIn("too_short", payload.decode())

    def test_ask_rejects_long_question(self):
        status, _, payload = service.handle(
            "POST", "/api/ask", {}, json.dumps({"question": "x" * 501}).encode())
        self.assertEqual(status, 400)
        self.assertIn("too_long", payload.decode())

    def test_ask_rejects_invalid_json(self):
        status, _, _ = service.handle("POST", "/api/ask", {}, b"{not json")
        self.assertEqual(status, 400)

    def test_ask_rejects_oversized_body(self):
        status, _, _ = service.handle(
            "POST", "/api/ask", {}, b"x" * (service.MAX_BODY_BYTES + 1))
        self.assertEqual(status, 413)

    def test_ask_happy_path_with_mocked_search(self):
        orig = search.search
        search.search = lambda q, max_results=5: (FIXTURE_SOURCES, "tavily", False)
        try:
            status, _, payload = service.handle(
                "POST", "/api/ask", {},
                json.dumps({"question": "What is the Tavily API used for?"}).encode())
        finally:
            search.search = orig
        self.assertEqual(status, 200)
        body = json.loads(payload)
        self.assertEqual(body["verdict"], "GROUNDED")
        self.assertTrue(body["claims"])
        self.assertEqual(body["provider"], "tavily")
        self.assertIn("took_ms", body)

    def test_ask_returns_502_when_search_fails(self):
        orig = search.search

        def boom(*args, **kwargs):
            raise search.SearchError("all down")
        search.search = boom
        try:
            status, _, payload = service.handle(
                "POST", "/api/ask", {},
                json.dumps({"question": "What is the Tavily API?"}).encode())
        finally:
            search.search = orig
        self.assertEqual(status, 502)
        self.assertIn("search_unavailable", payload.decode())

    def test_unknown_route_is_404(self):
        status, _, _ = service.handle("GET", "/nope", {}, None)
        self.assertEqual(status, 404)


class TestVercelAdapter(unittest.TestCase):
    def test_wsgi_health(self):
        sys.path.insert(0, os.path.join(ROOT, "api"))
        import importlib
        index = importlib.import_module("index")
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(index.app({
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/health",
            "QUERY_STRING": "",
            "wsgi.input": io.BytesIO(b""),
            "CONTENT_LENGTH": "0",
        }, start_response))
        self.assertTrue(captured["status"].startswith("200"))
        self.assertTrue(json.loads(body)["ok"])


if __name__ == "__main__":
    unittest.main()
