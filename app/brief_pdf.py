"""PDF export for Verity briefs.

The Markdown export (synthesize.render_markdown) is fine for notes, but a
finished research run usually gets shared — with a teacher, a teammate, a
client. Those readers open PDFs, and the receipts only help if the source
links still click. This module renders the same brief as a clean PDF:
question, cited claims with their [n] markers, the groundedness score and
verdict, and the full source list with a working link on every source.

Stdlib only, like the rest of the app. The PDF is written by hand (PDF 1.4,
base-14 Helvetica, uncompressed content streams) — no third-party library.
Layout is a simple line flow: blocks are word-wrapped up front, then paged.
"""

# A4, in points.
PAGE_W = 595.28
PAGE_H = 841.89
MARGIN = 56.0
TOP = 60.0            # first baseline offset from the top of the page
BOTTOM = 56.0         # keep this much clear at the bottom (footer lives there)
CONTENT_W = PAGE_W - 2 * MARGIN
LEADING = 1.45

INK = (0.10, 0.09, 0.07)
GREY = (0.42, 0.40, 0.36)
BLUE = (0.11, 0.30, 0.85)

# Characters a PDF literal string in WinAnsi can carry after cleaning.
# Anything else becomes "?" — a brief must never fail to render because a
# source used an exotic character.
_CHAR_MAP = {
    "‘": "'", "’": "'", "‚": "'", "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "―": "-", "…": "...", "•": "-",
    "→": "->", "←": "<-", "×": "x", " ": " ",
    "​": "", "﻿": "",
}


def _clean(text):
    """Map common Unicode punctuation to WinAnsi-safe text."""
    out = []
    for ch in str(text):
        out.append(_CHAR_MAP.get(ch, ch))
    return "".join(out).encode("cp1252", "replace").decode("cp1252")


def _char_width(ch, bold):
    """Approximate Helvetica advance width (1/1000 em), slightly generous
    so wrapped lines never overflow the page."""
    if ch in " ilj.,:;'!|()[]{}":
        width = 320
    elif ch in "ftr":
        width = 400
    elif ch in "mw":
        width = 860
    elif ch in "MW":
        width = 900
    elif ch.isupper():
        width = 700
    elif ch.isdigit():
        width = 556
    else:
        width = 560
    return width * 1.04 if bold else width


def _text_width(text, size, bold):
    return sum(_char_width(ch, bold) for ch in text) * size / 1000.0


def _wrap(text, size, bold, max_width, break_long=False):
    """Word-wrap text to lines of at most max_width points.

    With break_long=True (used for URLs) a single word longer than the
    line is split mid-word so it can never run off the page.
    """
    lines = []
    current = ""
    for word in str(text).split():
        candidate = word if not current else current + " " + word
        if _text_width(candidate, size, bold) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        while break_long and _text_width(word, size, bold) > max_width:
            cut = len(word)
            while cut > 1 and _text_width(word[:cut], size, bold) > max_width:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        current = word
    if current:
        lines.append(current)
    return lines or [""]


def _line(text, font, size, color, x=MARGIN, link=None, underline=False,
          space_before=0.0, space_after=0.0):
    return {
        "kind": "text", "text": text, "font": font, "size": size,
        "color": color, "x": x, "link": link, "underline": underline,
        "space_before": space_before, "space_after": space_after,
    }


def _rule(space_before=2.0, space_after=8.0):
    return {"kind": "rule", "space_before": space_before,
            "space_after": space_after}


def _brief_lines(answer):
    """Lay the brief out as a flat list of drawable lines."""
    lines = []
    lines.append(_line("Verity brief", "F2", 21, INK, space_after=2))
    question = _clean(answer.get("question", ""))
    for ln in _wrap(question, 12.5, True, CONTENT_W):
        lines.append(_line(ln, "F2", 12.5, INK))
    lines[-1]["space_after"] = 6

    verdict = _clean(answer.get("verdict", ""))
    score = answer.get("score", 0)
    coverage = int(round(float(answer.get("coverage", 0) or 0) * 100))
    sources_used = answer.get("sources_used", 0)
    meta = (f"Verdict: {verdict} - groundedness {score}/100 - "
            f"keyword coverage {coverage}% - {sources_used} source(s) used")
    for ln in _wrap(meta, 10.5, False, CONTENT_W):
        lines.append(_line(ln, "F1", 10.5, INK))
    lines[-1]["space_after"] = 4
    note = ("Every claim below is a sentence copied from a retrieved "
            "source. Open a source before you quote it.")
    for ln in _wrap(note, 9, False, CONTENT_W):
        lines.append(_line(ln, "F1", 9, GREY))
    lines.append(_rule())

    lines.append(_line("Claims", "F2", 12.5, INK,
                       space_before=6, space_after=4))
    claims = answer.get("claims") or []
    if not claims:
        lines.append(_line(
            "No claims - the search found no sentence it could cite "
            "for this question.", "F1", 10.5, INK))
    for i, claim in enumerate(claims, start=1):
        text = _clean(claim.get("text", ""))
        marker = claim.get("source_index", 0)
        text = f"{text} [{marker + 1}]"
        prefix = f"{i}."
        wrapped = _wrap(text, 10.5, False, CONTENT_W - 20)
        lines.append(_line(prefix, "F2", 10.5, BLUE, x=MARGIN))
        for j, ln in enumerate(wrapped):
            entry = _line(ln, "F1", 10.5, INK, x=MARGIN + 20)
            if j == len(wrapped) - 1:
                entry["space_after"] = 5
            lines.append(entry)

    lines.append(_line("Sources", "F2", 12.5, INK,
                       space_before=10, space_after=4))
    sources = answer.get("sources") or []
    if not sources:
        lines.append(_line("No sources were retrieved.", "F1", 10.5, INK))
    for i, source in enumerate(sources, start=1):
        title = _clean(source.get("title", "") or "Untitled source")
        provider = _clean(source.get("provider", ""))
        heading = f"[{i}] {title}" + (f" ({provider})" if provider else "")
        wrapped = _wrap(heading, 10, True, CONTENT_W)
        for ln in wrapped:
            lines.append(_line(ln, "F2", 10, INK))
        url = str(source.get("url", "")).strip()
        if url:
            for ln in _wrap(url, 9, False, CONTENT_W, break_long=True):
                lines.append(_line(ln, "F1", 9, BLUE,
                                   link=url, underline=True))
        lines[-1]["space_after"] = 5

    lines.append(_rule(space_before=4, space_after=4))
    lines.append(_line(
        "Built by Verity. Extractive synthesis: every claim is a sentence "
        "from a retrieved source; nothing is generated.", "F1", 8.5, GREY))
    return lines


def _paginate(lines):
    """Split the flat line list into pages."""
    pages = []
    page = []
    cursor = TOP
    limit = PAGE_H - BOTTOM
    for entry in lines:
        height = entry["space_before"] + entry["space_after"]
        if entry["kind"] == "text":
            height += entry["size"] * LEADING
        else:
            height += 1.0
        if page and cursor + height > limit:
            pages.append(page)
            page = []
            cursor = TOP
        page.append((entry, cursor))
        cursor += height
    if page or not pages:
        pages.append(page)
    return pages


def _escape(text):
    raw = _clean(text).encode("cp1252", "replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _num(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _page_stream(entries, page_no, page_count):
    """Draw one page: returns (content-stream bytes, link annots list)."""
    ops = []
    annots = []
    for entry, y_top in entries:
        if entry["kind"] == "rule":
            y = PAGE_H - (y_top + entry["space_before"] + 0.5)
            ops.append(
                (f"{GREY[0]} {GREY[1]} {GREY[2]} rg "
                 f"{_num(MARGIN)} {_num(y)} {_num(CONTENT_W)} 0.7 re f").encode())
            continue
        size = entry["size"]
        baseline = PAGE_H - (y_top + entry["space_before"] + size)
        r, g, b = entry["color"]
        text = _escape(entry["text"])
        ops.append(
            (f"BT /{entry['font']} {_num(size)} Tf {r} {g} {b} rg "
             f"1 0 0 1 {_num(entry['x'])} {_num(baseline)} Tm ").encode()
            + b"(" + text + b") Tj ET")
        width = _text_width(entry["text"], size, entry["font"] == "F2")
        if entry["underline"]:
            ops.append(
                (f"{r} {g} {b} RG 0.7 w "
                 f"{_num(entry['x'])} {_num(baseline - 2)} m "
                 f"{_num(entry['x'] + width)} {_num(baseline - 2)} l S").encode())
        if entry["link"]:
            annots.append({
                "rect": (entry["x"], baseline - size * 0.28,
                         entry["x"] + width, baseline + size * 0.75),
                "uri": entry["link"],
            })
    footer = ("Built by Verity - extractive synthesis; every claim is a "
              "sentence from a retrieved source.")
    ops.append(
        (f"BT /F1 8 Tf {GREY[0]} {GREY[1]} {GREY[2]} rg "
         f"1 0 0 1 {_num(MARGIN)} 40 Tm ").encode()
        + b"(" + _escape(footer) + b") Tj ET")
    label = f"Page {page_no} of {page_count}"
    label_x = PAGE_W - MARGIN - _text_width(label, 8, False)
    ops.append(
        (f"BT /F1 8 Tf {GREY[0]} {GREY[1]} {GREY[2]} rg "
         f"1 0 0 1 {_num(label_x)} 40 Tm ").encode()
        + b"(" + _escape(label) + b") Tj ET")
    return b"\n".join(ops) + b"\n", annots


def render_pdf(answer):
    """Render a finished Verity answer (the synthesize() result shape) as
    PDF bytes with a clickable link on every source."""
    pages = _paginate(_brief_lines(answer))
    page_count = len(pages)

    # Reserve: 1 = catalog, 2 = pages, 3 = F1, 4 = F2. Page/content/annot
    # objects follow from 5.
    page_nums = []
    pending = []
    next_num = 5
    for i, entries in enumerate(pages, start=1):
        stream, annots = _page_stream(entries, i, page_count)
        content_num = next_num + 1
        annot_nums = []
        annot_objs = []
        n = content_num + 1
        for annot in annots:
            annot_nums.append(n)
            x1, y1, x2, y2 = annot["rect"]
            annot_objs.append((
                n,
                f"<< /Type /Annot /Subtype /Link "
                f"/Rect [{_num(x1)} {_num(y1)} {_num(x2)} {_num(y2)}] "
                f"/Border [0 0 0] /A << /S /URI /URI (".encode()
                + _escape(annot["uri"]) + b") >> >>"))
            n += 1
        page_body = (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {_num(PAGE_W)} {_num(PAGE_H)}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_num} 0 R"
        )
        if annot_nums:
            page_body += " /Annots [" + " ".join(
                f"{num} 0 R" for num in annot_nums) + "]"
        page_body += " >>"
        pending.append((next_num, page_body.encode()))
        pending.append((content_num,
                        f"<< /Length {len(stream)} >>\nstream\n".encode()
                        + stream + b"endstream"))
        pending.extend(annot_objs)
        page_nums.append(next_num)
        next_num = n

    kids = " ".join(f"{num} 0 R" for num in page_nums)
    header_objs = [
        (1, b"<< /Type /Catalog /Pages 2 0 R >>"),
        (2, f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode()),
        (3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>"),
        (4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>"),
    ]
    all_objs = sorted(header_objs + pending)

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num, body in all_objs:
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    max_num = max(num for num, _ in all_objs)
    out += f"xref\n0 {max_num + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, max_num + 1):
        out += f"{offsets[num]:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {max_num + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n").encode()
    return bytes(out)
