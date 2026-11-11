"""Extractive synthesis + verification gate for Verity.

No LLM is involved. The answer is built ONLY from sentences retrieved from
live sources, so every claim can be traced to a sentence the user can open.

Pipeline:
1. Split every source's content into sentences.
2. Score each sentence by keyword overlap with the question.
3. Pick the best sentences (deduplicated), each keeping its source citation.
4. Gate: score the answer's groundedness from keyword coverage, source
   diversity and claim count. Verdicts: GROUNDED / PARTIAL / THIN / NO EVIDENCE.

The gate is the product: when evidence is weak, Verity says so instead of
bluffing. The score formula and every input to it are returned with the
answer so the verdict is auditable.
"""

import re

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "by", "at", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "it", "its", "this", "that", "these", "those", "what",
    "which", "who", "whom", "when", "where", "why", "how", "do", "does",
    "did", "can", "could", "should", "would", "will", "shall", "may",
    "might", "must", "have", "has", "had", "i", "you", "he", "she", "we",
    "they", "them", "his", "her", "their", "our", "your", "not", "no",
    "yes", "if", "then", "than", "so", "such", "about", "into", "over",
    "under", "after", "before", "between", "through", "during", "each",
    "other", "some", "any", "all", "both", "more", "most", "much", "many",
    "there", "here", "also", "just", "like", "get", "got", "make", "made",
    # Question verbs — generic in "how does X work?" style questions; the
    # topic words carry the meaning, not these.
    "work", "works", "working", "happen", "happens", "occur", "occurs",
}

_SENTENCE_SPLIT = re.compile(
    r"(?<!e\.g\.)(?<!i\.e\.)(?<!etc\.)(?<!Dr\.)(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)"
    r"(?<!vs\.)(?<!U\.S\.)(?<!U\.K\.)(?<=[.!?])\s+"
)
_WORD = re.compile(r"[a-z0-9]+")


def keywords(question):
    """Ordered, de-duplicated content words from the question."""
    seen = []
    for word in _WORD.findall(question.lower()):
        if len(word) < 3 or word in STOPWORDS:
            continue
        if word not in seen:
            seen.append(word)
    return seen


def split_sentences(text):
    """Split text into candidate sentences (3–60 words, ends with . ! or ?)."""
    out = []
    for part in _SENTENCE_SPLIT.split(text.replace("\n", " ").strip()):
        sent = part.strip()
        words = sent.split()
        if 3 <= len(words) <= 60 and sent and sent[-1] in ".!?":
            out.append(sent)
    return out


def _tokens(text):
    return set(_WORD.findall(text.lower()))


def _similar(a, b):
    """Jaccard similarity of two sentences' token sets."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _score_sentence(sentence, keys):
    """Keyword hits, with a small bonus for sentences that name the topic."""
    tokens = _tokens(sentence)
    hits = sum(1 for k in keys if k in tokens)
    return hits


def synthesize(question, sources, max_claims=6):
    """Build a cited answer from retrieved sources.

    Returns a dict with claims, sources, score (0–100), verdict and the
    audit trail (coverage, sources used, keywords). Never raises on empty
    input — it returns a NO EVIDENCE result instead.
    """
    keys = keywords(question)
    result = {
        "question": question,
        "keywords": keys,
        "claims": [],
        "sources": sources,
        "score": 0,
        "verdict": "NO EVIDENCE",
        "coverage": 0.0,
        "sources_used": 0,
        "claims_found": 0,
    }
    if not sources or not keys:
        return result

    # Score every sentence from every source.
    scored = []
    for idx, source in enumerate(sources):
        for sent in split_sentences(source.get("content", "")):
            score = _score_sentence(sent, keys)
            if score > 0:
                scored.append((score, idx, sent))
    scored.sort(key=lambda item: (-item[0], item[1]))
    result["claims_found"] = len(scored)
    if not scored:
        return result

    # Pick the best sentences, dropping near-duplicates.
    claims = []
    for score, idx, sent in scored:
        if len(claims) >= max_claims:
            break
        if any(_similar(sent, c["text"]) > 0.75 for c in claims):
            continue
        source = sources[idx]
        claims.append({
            "text": sent,
            "source_index": idx,
            "source_title": source.get("title", ""),
            "source_url": source.get("url", ""),
            "provider": source.get("provider", ""),
            "keyword_hits": score,
        })
    result["claims"] = claims

    # Gate: coverage + source diversity + claim count.
    covered = {k for k in keys if any(k in _tokens(c["text"]) for c in claims)}
    coverage = len(covered) / len(keys) if keys else 0.0
    used = {c["source_index"] for c in claims}
    diversity = min(1.0, len(used) / 3.0)
    density = min(1.0, len(claims) / 4.0)
    score = round(100 * (0.5 * coverage + 0.3 * diversity + 0.2 * density))
    result["coverage"] = round(coverage, 2)
    result["sources_used"] = len(used)
    result["score"] = score
    if score >= 70:
        result["verdict"] = "GROUNDED"
    elif score >= 40:
        result["verdict"] = "PARTIAL"
    else:
        result["verdict"] = "THIN"
    return result


def render_markdown(answer):
    """Export the answer as a Markdown brief with full citations."""
    lines = [
        f"# Verity brief — {answer['question']}",
        "",
        f"Verdict: **{answer['verdict']}** (groundedness {answer['score']}/100; "
        f"keyword coverage {int(answer['coverage'] * 100)}%; "
        f"{answer['sources_used']} source(s) used)",
        "",
        "## Claims",
        "",
    ]
    for i, claim in enumerate(answer["claims"], start=1):
        lines.append(f"{i}. {claim['text']} [{claim['source_index'] + 1}]")
    lines += ["", "## Sources", ""]
    for i, source in enumerate(answer["sources"], start=1):
        lines.append(f"[{i}] {source.get('title', '')} — {source.get('url', '')} "
                     f"({source.get('provider', '')})")
    lines += [
        "",
        "---",
        "Built by Verity (Geek Room Global AI Hackathon 2026). Extractive "
        "synthesis: every claim is a sentence from a retrieved source.",
    ]
    return "\n".join(lines)
