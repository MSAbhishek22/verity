"""Search providers for Verity.

Two providers, one shape:
- Tavily (https://api.tavily.com/search) — used when a TAVILY_API_KEY is set.
  Tavily is the Geek Room track partner; every participant gets 8,000 credits.
- Wikipedia REST API — free, no key. The always-on fallback so the demo never
  depends on a credential the user has not provided.

Both return a list of dicts: {title, url, content, provider}.
No API key is ever hard-coded here; the Tavily key comes from the
TAVILY_API_KEY environment variable only.

Stdlib only (urllib). Timeouts are short and fail-soft: a provider that
errors simply yields no results and the caller falls back.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

TAVILY_URL = "https://api.tavily.com/search"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "Verity/1.0 (Geek Room Global AI Hackathon prototype)"
SEARCH_TIMEOUT = 8  # seconds per provider call
OVERALL_BUDGET = 9  # seconds for the whole parallel search


class SearchError(Exception):
    """Raised when a provider call fails (network, HTTP error, bad payload)."""


def _post_json(url, payload, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SearchError(f"POST {url} failed: {exc}") from exc


def _get_json(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SearchError(f"GET {url} failed: {exc}") from exc


def search_tavily(query, api_key, max_results=5, timeout=SEARCH_TIMEOUT):
    """Live web search via Tavily. Returns [{title, url, content, provider}]."""
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
    }
    data = _post_json(TAVILY_URL, payload, timeout)
    results = []
    for item in data.get("results", [])[:max_results]:
        content = (item.get("content") or "").strip()
        url = (item.get("url") or "").strip()
        if not content or not url:
            continue
        results.append({
            "title": (item.get("title") or url).strip(),
            "url": url,
            "content": content,
            "provider": "tavily",
        })
    if not results:
        # Zero results is a valid outcome (the question matched nothing),
        # not a provider failure — the caller reports NO EVIDENCE.
        return []
    return results


def search_wikipedia(query, max_results=5, timeout=SEARCH_TIMEOUT):
    """Free, keyless search via the Wikipedia API.

    Step 1: list=search for matching article titles. The search string is
    built from the question's content keywords (not the full question):
    Wikipedia's full-text ranking buries the obvious article for natural
    questions ("How does photosynthesis work?" ranks "Photosynthesis" out
    of the top 5; "photosynthesis work" ranks it first). If the keyword
    query finds nothing, retry with the full question.
    Step 2: prop=extracts for the opening sentences of each article.
    Returns [{title, url, content, provider}] with provider 'wikipedia'.
    """
    import synthesize

    keys = synthesize.keywords(query)
    attempts = []
    if keys:
        attempts.append(" ".join(keys[:6]))
    attempts.append(query)
    hits = []
    for attempt in attempts:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": attempt,
            "srlimit": str(max_results),
            "format": "json",
        }
        data = _get_json(WIKIPEDIA_API + "?" + urllib.parse.urlencode(params), timeout)
        hits = (data.get("query") or {}).get("search", [])
        if hits:
            break
    titles = [h.get("title") for h in hits if h.get("title")]
    if not titles:
        return []
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "exintro": "1",
        "exsentences": "3",
        "titles": "|".join(titles[:max_results]),
        "format": "json",
    }
    data = _get_json(WIKIPEDIA_API + "?" + urllib.parse.urlencode(params), timeout)
    pages = (data.get("query") or {}).get("pages", {})
    by_title = {p.get("title"): p for p in pages.values() if p.get("title")}
    results = []
    # Preserve Wikipedia's relevance order: the API returns pages keyed by
    # pageid (unordered), so re-walk the titles in the order search gave us.
    for title in titles[:max_results]:
        page = by_title.get(title)
        if not page:
            continue
        extract = (page.get("extract") or "").strip()
        if not extract:
            continue
        url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(
            title.replace(" ", "_"))
        results.append({
            "title": title,
            "url": url,
            "content": extract,
            "provider": "wikipedia",
        })
    if not results:
        return []
    return results


def tavily_configured():
    """True when a Tavily key is present in the environment."""
    return bool(os.environ.get("TAVILY_API_KEY", "").strip())


def default_provider():
    """The provider the UI reports as primary."""
    return "tavily" if tavily_configured() else "wikipedia"


def search(query, max_results=5):
    """Search both providers in parallel; prefer Tavily when it works.

    Returns (results, provider_used, fell_back) where provider_used is
    'tavily' or 'wikipedia' and fell_back is True when Tavily was configured
    but failed and Wikipedia answered instead.

    Raises SearchError only when every attempted provider fails.
    """
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    jobs = []
    if key:
        jobs.append(("tavily", search_tavily, (query, key, max_results)))
    jobs.append(("wikipedia", search_wikipedia, (query, max_results)))

    outcomes = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {
            pool.submit(fn, *args): name for name, fn, args in jobs
        }
        for future in futures:
            name = futures[future]
            try:
                outcomes[name] = future.result(timeout=OVERALL_BUDGET)
            except (FuturesTimeout, SearchError):
                outcomes[name] = None
            except Exception:
                outcomes[name] = None

    if key and outcomes.get("tavily"):
        return outcomes["tavily"], "tavily", False
    if outcomes.get("wikipedia"):
        return outcomes["wikipedia"], "wikipedia", bool(key)
    # Both providers answered but found nothing (or one errored and the
    # other found nothing): an empty result is a valid outcome, not a
    # failure — the caller reports NO EVIDENCE instead of a 502.
    if outcomes.get("tavily") is not None:
        return [], "tavily", False
    if outcomes.get("wikipedia") is not None:
        return [], "wikipedia", bool(key)
    raise SearchError("All search providers failed")
