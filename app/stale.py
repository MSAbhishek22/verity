"""StaleCheck — Verity's stale-answer checker.

The job: take an old AI answer and the date it was written, pull out every
claim that carries a date, a number or a version, and check each one again
against sources fetched today.

Verdicts, one per claim:
  FRESH      a live source confirms the same value today.
  CHANGED    a live source has a different value for the same fact
             (old value and new value are both shown).
  STALE      the claim presents a date as still to come — a deadline, a
             launch, an opening — and that date has passed.
  UNVERIFIED no live source could be checked, or nothing in the sources
             matched the claim. A failed check is UNVERIFIED, never FRESH.

No LLM is involved. Claim extraction reuses Verity's own sentence splitter
and keyword code from synthesize.py, and the live path reuses search.py —
the same providers as the research mode. Every verdict carries the source
name and the date it was fetched on, so a verdict can be checked by hand.
"""

import datetime
import re

import search
import synthesize

VERDICTS = ("FRESH", "STALE", "CHANGED", "UNVERIFIED")

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_NUMBER_WORDS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}

_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_LONG_DATE_A = re.compile(
    rf"\b(\d{{1,2}})\s+({_MONTH_ALT})\s*,?\s+(\d{{4}})\b", re.IGNORECASE)
_LONG_DATE_B = re.compile(
    rf"\b({_MONTH_ALT})\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s+(\d{{4}})\b",
    re.IGNORECASE)
_MONTH_YEAR = re.compile(
    rf"\b({_MONTH_ALT})\s+(\d{{4}})\b", re.IGNORECASE)
_VERSION = re.compile(
    r"\bv(?:ersion)?\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\b"
    r"|\b(\d+)\.(\d+)\.(\d+)\b", re.IGNORECASE)
_NUMBER = re.compile(r"(?<![A-Za-z0-9-])\d{1,3}(?:,\d{3})+(?:\.\d+)?"
                     r"|(?<![A-Za-z0-9-])\d+(?:\.\d+)?")
_NUMBER_WORD = re.compile(
    r"\b(" + "|".join(_NUMBER_WORDS) + r")\b", re.IGNORECASE)
_BARE_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")

_FUTURE_WORDS = ("will", "shall", "upcoming", "scheduled", "planned",
                 "expected to")
_DEADLINE_WORDS = ("deadline", "due", "closes", "closing", "expires",
                   "expiry", "last date")


def _num_str(value):
    """Format a float the way it was probably written (7, not 7.0)."""
    if value == int(value):
        return str(int(value))
    return str(value)


def _date_value(year, month, day, raw):
    try:
        parsed = datetime.date(year, month, day)
    except ValueError:
        return None
    return {"kind": "date", "raw": raw, "value": parsed.isoformat()}


def extract_values(text):
    """Every checkable value in one sentence, in the order written.

    Returns a list of {"kind", "raw", "value"} where kind is "date",
    "year", "version" or "number" and value is the normalised form used
    for comparison (ISO date, int year, float number, version tuple as
    text). Spans claimed by a date or a version are not counted again
    as plain numbers.
    """
    found = []  # (start, end, priority, value-dict)

    def offer(match, priority, value):
        if value is not None:
            found.append((match.start(), match.end(), priority, value))

    for m in _ISO_DATE.finditer(text):
        offer(m, 0, _date_value(int(m.group(1)), int(m.group(2)),
                                int(m.group(3)), m.group(0)))
    for m in _LONG_DATE_A.finditer(text):
        offer(m, 0, _date_value(int(m.group(3)),
                                _MONTHS[m.group(2).lower()],
                                int(m.group(1)), m.group(0)))
    for m in _LONG_DATE_B.finditer(text):
        offer(m, 0, _date_value(int(m.group(3)),
                                _MONTHS[m.group(1).lower()],
                                int(m.group(2)), m.group(0)))
    for m in _MONTH_YEAR.finditer(text):
        offer(m, 1, _date_value(int(m.group(2)),
                                _MONTHS[m.group(1).lower()], 1, m.group(0)))
    for m in _VERSION.finditer(text):
        parts = [g for g in m.groups() if g is not None]
        offer(m, 2, {"kind": "version", "raw": m.group(0),
                     "value": ".".join(parts)})
    for m in _NUMBER.finditer(text):
        number = float(m.group(0).replace(",", ""))
        if number == int(number) and 1900 <= number <= 2099:
            offer(m, 3, {"kind": "year", "raw": m.group(0),
                         "value": str(int(number))})
        else:
            offer(m, 3, {"kind": "number", "raw": m.group(0),
                         "value": _num_str(number)})
    for m in _NUMBER_WORD.finditer(text):
        offer(m, 3, {"kind": "number", "raw": m.group(0),
                     "value": str(_NUMBER_WORDS[m.group(1).lower()])})
    for m in _BARE_YEAR.finditer(text):
        offer(m, 4, {"kind": "year", "raw": m.group(0), "value": m.group(1)})

    found.sort(key=lambda item: (item[0], item[2]))
    values, taken_end = [], -1
    for start, end, _priority, value in found:
        if start < taken_end:
            continue
        taken_end = end
        values.append(value)
    return values


def _candidate_sentences(text):
    """Sentences from a pasted answer, bullets and line breaks included."""
    out = []
    for chunk in text.replace("\r", "\n").split("\n"):
        chunk = re.sub(r"^\s*(?:[-•*]|\d+[.)])\s+", "", chunk.strip())
        if not chunk:
            continue
        parts = synthesize.split_sentences(chunk)
        if parts:
            out.extend(parts)
        elif len(chunk.split()) >= 4:
            out.append(chunk)
    return out


def extract_claims(answer_text):
    """The checkable claims in an answer: sentences carrying a value."""
    claims = []
    for sentence in _candidate_sentences(answer_text):
        values = extract_values(sentence)
        if values:
            claims.append({"text": sentence, "values": values})
    return claims


def _claim_date(claim):
    """The earliest date/year a claim carries, as a date (or None)."""
    dates = []
    for value in claim["values"]:
        if value["kind"] == "date":
            dates.append(datetime.date.fromisoformat(value["value"]))
        elif value["kind"] == "year":
            dates.append(datetime.date(int(value["value"]), 1, 1))
    return min(dates) if dates else None


def _matching_sentences(claim, sources):
    """Source sentences that talk about the claim, best overlap first.

    Reuses Verity's keyword extraction: a source sentence counts as being
    about the claim when it shares enough of the claim's content words.
    Returns [(overlap, source, sentence), ...].
    """
    keys = synthesize.keywords(claim["text"])
    if not keys:
        return []
    needed = 2 if len(keys) >= 3 else 1
    scored = []
    for s_idx, source in enumerate(sources):
        for sentence in synthesize.split_sentences(source.get("content", "")):
            tokens = set(synthesize._WORD.findall(sentence.lower()))
            overlap = sum(1 for k in keys if k in tokens)
            if overlap >= needed:
                scored.append((-overlap, s_idx, sentence, source))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [(-neg, source, sentence) for neg, _idx, sentence, source in scored]


def check_claim(claim, sources, today):
    """One claim against fetched sources. sources=None means fetch failed."""
    base = {
        "text": claim["text"],
        "values": claim["values"],
        "verdict": "UNVERIFIED",
        "old_value": claim["values"][0]["raw"] if claim["values"] else "",
        "new_value": "",
        "source_title": "",
        "source_url": "",
        "provider": "",
        "fetched_on": today.isoformat(),
        "evidence": "",
        "reason": "",
    }
    if sources is None:
        base["reason"] = "The live check failed, so this claim was not checked."
        return base
    if not sources:
        base["reason"] = "The live check found no sources for this claim."
        return base

    # Per-sentence outcomes first. A CHANGED verdict must beat the best
    # confirming sentence on overlap: an equally relevant source that
    # confirms the claim wins, because a different number in a loosely
    # related sentence is often a different quantity (a height in feet,
    # another building), not an update to this fact.
    fresh = None        # (overlap, source, sentence, value)
    changed_hit = None  # (overlap, source, sentence, claim value, ev value)
    for overlap, source, sentence in _matching_sentences(claim, sources):
        ev_values = extract_values(sentence)
        if not ev_values:
            continue
        ev_by_kind = {}
        for ev in ev_values:
            ev_by_kind.setdefault(ev["kind"], []).append(ev)
        sentence_changed = None
        sentence_fresh = None
        for value in claim["values"]:
            candidates = ev_by_kind.get(value["kind"], [])
            if not candidates:
                continue
            if any(c["value"] == value["value"] for c in candidates):
                if sentence_fresh is None:
                    sentence_fresh = (source, sentence, value)
                continue
            if sentence_changed is None:
                sentence_changed = (value, candidates[0])
        if sentence_changed is not None and changed_hit is None:
            value, ev_value = sentence_changed
            changed_hit = (overlap, source, sentence, value, ev_value)
        elif sentence_fresh is not None and fresh is None:
            src, sent, value = sentence_fresh
            fresh = (overlap, src, sent, value)

    if changed_hit is not None and (
            fresh is None or changed_hit[0] > fresh[0]):
        _overlap, source, sentence, value, ev_value = changed_hit
        changed = dict(base)
        changed.update({
            "verdict": "CHANGED",
            "old_value": value["raw"],
            "new_value": ev_value["raw"],
            "source_title": source.get("title", ""),
            "source_url": source.get("url", ""),
            "provider": source.get("provider", ""),
            "evidence": sentence,
            "reason": "A live source gives a different "
                      f"{value['kind']} for this fact.",
        })
        return changed
    if fresh is not None:
        _overlap, src, sent, val = fresh
        fresh = (src, sent, val)

    claim_date = _claim_date(claim)
    lowered = claim["text"].lower()
    presents_future = any(w in lowered for w in _FUTURE_WORDS + _DEADLINE_WORDS)
    if claim_date is not None and claim_date < today and presents_future:
        base.update({
            "verdict": "STALE",
            "new_value": base["old_value"],
            "reason": "The claim presents this date as still to come, "
                      "and the date has passed.",
        })
        if fresh is not None:
            source, sentence, _value = fresh
            base.update({
                "source_title": source.get("title", ""),
                "source_url": source.get("url", ""),
                "provider": source.get("provider", ""),
                "evidence": sentence,
            })
        return base

    if fresh is not None:
        source, sentence, value = fresh
        base.update({
            "verdict": "FRESH",
            "new_value": value["raw"],
            "source_title": source.get("title", ""),
            "source_url": source.get("url", ""),
            "provider": source.get("provider", ""),
            "evidence": sentence,
            "reason": "A live source confirms the same value today.",
        })
        return base

    base["reason"] = "No live source matched this claim closely enough."
    return base


def _live_fetcher(claim):
    """Fetch live sources for one claim via Verity's own search."""
    keys = synthesize.keywords(claim["text"])
    query = " ".join(keys[:6])
    if claim["values"]:
        query = (query + " " + claim["values"][0]["raw"]).strip()
    try:
        results, _provider, _fell_back = search.search(query)
    except search.SearchError:
        return None
    return results


def check_answer(answer_text, generated_on, fetcher=None, today=None):
    """Check a whole pasted answer.

    generated_on: the date the answer was written (date or ISO string).
    fetcher: optional callable claim -> list of source dicts (or None when
    the fetch failed); defaults to the live search in search.py. Tests and
    the StaleBench runner pass their own fetcher.
    today: the check date; defaults to the real today.
    """
    if isinstance(generated_on, str):
        generated_on = datetime.date.fromisoformat(generated_on)
    if today is None:
        today = datetime.date.today()
    if fetcher is None:
        fetcher = _live_fetcher

    checked = []
    counts = {verdict: 0 for verdict in VERDICTS}
    for claim in extract_claims(answer_text):
        try:
            sources = fetcher(claim)
        except Exception:
            sources = None
        result = check_claim(claim, sources, today)
        counts[result["verdict"]] += 1
        checked.append(result)

    total = len(checked)
    stale_like = counts["STALE"] + counts["CHANGED"]
    stale_score = round(100 * stale_like / total) if total else 0
    return {
        "generated_on": generated_on.isoformat(),
        "checked_on": today.isoformat(),
        "claims": checked,
        "claims_found": total,
        "counts": counts,
        "stale_score": stale_score,
    }
