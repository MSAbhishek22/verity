"""Verity request handler — one function, used by the local dev server and
by the Vercel WSGI adapter alike (same pattern as GateFlat).

Routes:
  GET  /            -> the single-page UI (app/index.html)
  GET  /api/health -> {"ok": true, ...} (no network use)
  GET  /api/status -> provider configuration (no secrets in the response)
  POST /api/ask    -> {"question": "..."} -> cited answer + gate verdict
  anything else    -> 404 JSON

POST /api/ask validation: question is required, 3–500 chars, body <= 8 KiB.
Search failures from every provider return 502 with an honest message —
never a fabricated answer.
"""

import json
import os
import time

import search
import synthesize

VERSION = "0.1.0"
MAX_BODY_BYTES = 8 * 1024
MAX_QUESTION_CHARS = 500
MIN_QUESTION_CHARS = 3

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
    return _json(404, {"error": "not_found",
                       "message": f"No route for {method} {path}."})
