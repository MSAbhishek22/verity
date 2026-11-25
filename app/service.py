"""Verity request handler — one function, used by the local dev server and
by the Vercel WSGI adapter alike (same pattern as GateFlat).

Routes:
  GET  /            -> the single-page UI (app/index.html)
  GET  /api/health -> {"ok": true, ...} (no network use)
  GET  /api/status -> provider configuration (no secrets in the response)
  POST /api/ask    -> {"question": "..."} -> cited answer + gate verdict
  POST /api/stale-check -> {"answer": "...", "generated_on": "YYYY-MM-DD"}
                       -> per-claim FRESH / STALE / CHANGED / UNVERIFIED
                          verdicts + one Stale Score (StaleCheck)
  POST /api/brief.pdf -> a finished answer -> the brief as a PDF download
  anything else    -> 404 JSON

POST /api/ask validation: question is required, 3–500 chars, body <= 8 KiB.
POST /api/brief.pdf validation: the client sends back the answer it is
showing (the app is stateless, so the brief is rendered from exactly what
the user sees — never re-searched); fields are type- and length-checked,
body <= 64 KiB.
Search failures from every provider return 502 with an honest message —
never a fabricated answer.
"""

import datetime
import json
import os
import time

import brief_pdf
import search
import stale
import synthesize

VERSION = "0.3.0"
MAX_BODY_BYTES = 8 * 1024
MAX_BRIEF_BODY_BYTES = 64 * 1024
MAX_STALE_BODY_BYTES = 16 * 1024
MAX_QUESTION_CHARS = 500
MIN_QUESTION_CHARS = 3
MIN_ANSWER_CHARS = 10
MAX_ANSWER_CHARS = 4000
VERDICTS = ("GROUNDED", "PARTIAL", "THIN", "NO EVIDENCE")

_HERE = os.path.dirname(os.path.abspath(__file__))


def _json(status, obj):
    payload = json.dumps(obj).encode("utf-8")
    return status, "application/json", payload


def _load_index():
    path = os.path.join(_HERE, "index.html")
    with open(path, "rb") as fh:
        return fh.read()


def _handle_ask(body):
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _json(400, {"error": "invalid_json",
                           "message": "Request body must be valid JSON."})
    if not isinstance(data, dict):
        return _json(400, {"error": "invalid_json",
                           "message": "Request body must be a JSON object."})
    question = data.get("question", "")
    if not isinstance(question, str):
        return _json(400, {"error": "invalid_question",
                           "message": "Question must be text."})
    question = question.strip()
    if len(question) < MIN_QUESTION_CHARS:
        return _json(400, {"error": "question_too_short",
                           "message": "Ask a question of at least 3 characters."})
    if len(question) > MAX_QUESTION_CHARS:
        return _json(400, {"error": "question_too_long",
                           "message": "Please keep the question under 500 characters."})

    started = time.monotonic()
    try:
        results, provider, fell_back = search.search(question)
    except search.SearchError:
        return _json(502, {
            "error": "search_unavailable",
            "message": "Both search providers failed. Check your connection "
                       "and try again.",
        })
    answer = synthesize.synthesize(question, results)
    took_ms = round((time.monotonic() - started) * 1000)
    return _json(200, {
        "question": question,
        "provider": provider,
        "fell_back": fell_back,
        "tavily_configured": search.tavily_configured(),
        "verdict": answer["verdict"],
        "score": answer["score"],
        "coverage": answer["coverage"],
        "sources_used": answer["sources_used"],
        "claims_found": answer["claims_found"],
        "keywords": answer["keywords"],
        "claims": answer["claims"],
        "sources": answer["sources"],
        "took_ms": took_ms,
    })


def _handle_stale_check(body):
    """StaleCheck: re-check an old answer's dated/numeric/versioned claims.

    Body: {"answer": "...", "generated_on": "YYYY-MM-DD"}. The answer is
    checked live, claim by claim; a claim whose live check fails comes
    back UNVERIFIED, never FRESH (see app/stale.py).
    """
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _json(400, {"error": "invalid_json",
                           "message": "Request body must be valid JSON."})
    if not isinstance(data, dict):
        return _json(400, {"error": "invalid_json",
                           "message": "Request body must be a JSON object."})
    answer = data.get("answer", "")
    if not isinstance(answer, str):
        return _json(400, {"error": "invalid_answer",
                           "message": "Answer must be text."})
    answer = answer.strip()
    if len(answer) < MIN_ANSWER_CHARS:
        return _json(400, {"error": "answer_too_short",
                           "message": "Paste an answer of at least 10 characters."})
    if len(answer) > MAX_ANSWER_CHARS:
        return _json(400, {"error": "answer_too_long",
                           "message": "Please keep the answer under 4000 characters."})
    generated_raw = data.get("generated_on", "")
    if not isinstance(generated_raw, str):
        return _json(400, {"error": "invalid_generated_on",
                           "message": "generated_on must be a date, YYYY-MM-DD."})
    try:
        generated_on = datetime.date.fromisoformat(generated_raw.strip())
    except ValueError:
        return _json(400, {"error": "invalid_generated_on",
                           "message": "generated_on must be a date, YYYY-MM-DD."})
    if generated_on > datetime.date.today():
        return _json(400, {"error": "generated_on_in_future",
                           "message": "The answer cannot have been written "
                                      "in the future."})

    started = time.monotonic()
    result = stale.check_answer(answer, generated_on)
    took_ms = round((time.monotonic() - started) * 1000)
    return _json(200, {
        "generated_on": result["generated_on"],
        "checked_on": result["checked_on"],
        "provider": search.default_provider(),
        "tavily_configured": search.tavily_configured(),
        "stale_score": result["stale_score"],
        "counts": result["counts"],
        "claims_found": result["claims_found"],
        "claims": result["claims"],
        "took_ms": took_ms,
    })


def _handle_brief_pdf(body):
    """Render a finished answer as a PDF brief.

    The request body is the answer object the UI already shows (question,
    verdict, score, coverage, sources_used, claims, sources). Every field
    is validated before rendering; anything malformed is a 400, never a
    half-rendered PDF.
    """
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _json(400, {"error": "invalid_json",
                           "message": "Request body must be valid JSON."})
    if not isinstance(data, dict):
        return _json(400, {"error": "invalid_json",
                           "message": "Request body must be a JSON object."})

    def bad(field, message):
        return _json(400, {"error": f"invalid_{field}", "message": message})

    question = data.get("question", "")
    if not isinstance(question, str) or not (
            MIN_QUESTION_CHARS <= len(question.strip()) <= MAX_QUESTION_CHARS):
        return bad("question", "A brief needs the question it answers "
                               "(3–500 characters).")
    verdict = data.get("verdict", "")
    if verdict not in VERDICTS:
        return bad("verdict", "Verdict must be one of: "
                              + ", ".join(VERDICTS) + ".")
    score = data.get("score", 0)
    if isinstance(score, bool) or not isinstance(score, int) \
            or not 0 <= score <= 100:
        return bad("score", "Score must be a whole number from 0 to 100.")
    coverage = data.get("coverage", 0)
    if isinstance(coverage, bool) \
            or not isinstance(coverage, (int, float)) \
            or not 0 <= coverage <= 1:
        return bad("coverage", "Coverage must be a number from 0 to 1.")
    sources_used = data.get("sources_used", 0)
    if isinstance(sources_used, bool) or not isinstance(sources_used, int) \
            or sources_used < 0:
        return bad("sources_used", "Sources used must be 0 or more.")

    claims = data.get("claims", [])
    if not isinstance(claims, list) or len(claims) > 12:
        return bad("claims", "Claims must be a list of at most 12 items.")
    clean_claims = []
    for claim in claims:
        if not isinstance(claim, dict) \
                or not isinstance(claim.get("text"), str) \
                or not 1 <= len(claim["text"]) <= 2000 \
                or isinstance(claim.get("source_index"), bool) \
                or not isinstance(claim.get("source_index"), int) \
                or claim["source_index"] < 0:
            return bad("claims", "Each claim needs its text and the index "
                                 "of the source it came from.")
        clean_claims.append({"text": claim["text"],
                             "source_index": claim["source_index"]})

    sources = data.get("sources", [])
    if not isinstance(sources, list) or len(sources) > 20:
        return bad("sources", "Sources must be a list of at most 20 items.")
    clean_sources = []
    for source in sources:
        if not isinstance(source, dict) \
                or not isinstance(source.get("title"), str) \
                or len(source["title"]) > 300 \
                or not isinstance(source.get("url"), str) \
                or len(source["url"]) > 2000 \
                or not source["url"].startswith(("http://", "https://")) \
                or not isinstance(source.get("provider", ""), str) \
                or len(source.get("provider", "")) > 50:
            return bad("sources", "Each source needs a title and an "
                                  "http(s) link.")
        clean_sources.append({
            "title": source["title"],
            "url": source["url"],
            "provider": source.get("provider", ""),
        })

    answer = {
        "question": question.strip(),
        "verdict": verdict,
        "score": score,
        "coverage": coverage,
        "sources_used": sources_used,
        "claims": clean_claims,
        "sources": clean_sources,
    }
    return 200, "application/pdf", brief_pdf.render_pdf(answer)


def handle(method, path, query, body):
    """Pure handler: (method, path, query-dict, raw-body-bytes-or-None).

    Returns (http-status, content-type, payload-bytes).
    """
    path = path or "/"
    if method == "GET" and path == "/":
        return 200, "text/html; charset=utf-8", _load_index()
    if method == "GET" and path == "/api/health":
        return _json(200, {
            "ok": True,
            "service": "verity",
            "version": VERSION,
            "provider": search.default_provider(),
        })
    if method == "GET" and path == "/api/status":
        return _json(200, {
            "service": "verity",
            "version": VERSION,
            "provider": search.default_provider(),
            "tavily_configured": search.tavily_configured(),
            "fallback": "wikipedia",
            "synthesis": "extractive — no LLM; claims are sentences from "
                         "retrieved sources only",
        })
    if method == "POST" and path == "/api/ask":
        if body is not None and len(body) > MAX_BODY_BYTES:
            return _json(413, {"error": "body_too_large",
                               "message": "Request body too large."})
        return _handle_ask(body or b"")
    if method == "POST" and path == "/api/stale-check":
        if body is not None and len(body) > MAX_STALE_BODY_BYTES:
            return _json(413, {"error": "body_too_large",
                               "message": "Request body too large."})
        return _handle_stale_check(body or b"")
    if method == "POST" and path == "/api/brief.pdf":
        if body is not None and len(body) > MAX_BRIEF_BODY_BYTES:
            return _json(413, {"error": "body_too_large",
                               "message": "Request body too large."})
        return _handle_brief_pdf(body or b"")
    return _json(404, {"error": "not_found",
                       "message": f"No route for {method} {path}."})
