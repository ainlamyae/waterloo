"""Convert the "Help New Student" Word document into content/guide.md.

Pure standard library (zipfile + xml.etree.ElementTree) -- no pandoc or
python-docx dependency required. Only handles the subset of DOCX features
present in the source document: headings, bold/italic runs, hyperlinks,
bulleted/numbered lists, and simple tables. No images.

Usage:
    python scripts/docx_to_md.py "<path to .docx>" content/guide.md
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

SKIP_STYLES = {"TOCHeading", "TOC1", "TOC2"}

# Hand-authored embeds that aren't in the source docx, kept here (not in
# app.js) so content/guide.md stays the single source of truth for the page.
INTRO_BLOCK = "\n\n".join(
    [
        "## تور دانشگاه واترلو {#section-0}",
        "پیش از سفر، نگاهی تصویری به محوطه دانشگاه واترلو بیندازید.",
        '<div class="video-wrap">\n'
        '  <iframe src="https://www.youtube-nocookie.com/embed/yhhuSXlzi_c" title="تور دانشگاه واترلو" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>\n'
        "</div>",
        "نقشه محوطه دانشگاه واترلو:",
        '<div class="video-wrap map-wrap">\n'
        '  <iframe src="https://uwaterloo.ca/map/" title="نقشه دانشگاه واترلو" loading="lazy"></iframe>\n'
        "</div>",
    ]
)

DIRECTIONS_BLOCK = "\n\n".join(
    [
        "مسیر پیشنهادی از ترمینال ۱ فرودگاه پیرسون تورنتو تا دانشگاه واترلو:",
        '<div class="video-wrap map-wrap section-map">\n'
        '  <iframe src="https://www.google.com/maps?saddr=Toronto+Pearson+International+Airport+Terminal+1&daddr=University+of+Waterloo&output=embed" title="مسیر فرودگاه پیرسون تورنتو (ترمینال ۱) تا دانشگاه واترلو" loading="lazy"></iframe>\n'
        "</div>",
    ]
)


def load_rels(zf):
    try:
        data = zf.read("word/_rels/document.xml.rels")
    except KeyError:
        return {}
    root = ET.fromstring(data)
    rels = {}
    for rel in root:
        rels[rel.get("Id")] = rel.get("Target")
    return rels


def load_num_formats(zf):
    """Map (numId, ilvl) -> 'bullet' | 'decimal' | ... """
    try:
        data = zf.read("word/numbering.xml")
    except KeyError:
        return {}
    root = ET.fromstring(data)
    abstract_fmt = {}  # abstractNumId -> {ilvl: fmt}
    for an in root.findall(f"{W}abstractNum"):
        aid = an.get(f"{W}abstractNumId")
        levels = {}
        for lvl in an.findall(f"{W}lvl"):
            ilvl = lvl.get(f"{W}ilvl")
            fmt_el = lvl.find(f"{W}numFmt")
            levels[ilvl] = fmt_el.get(f"{W}val") if fmt_el is not None else "bullet"
        abstract_fmt[aid] = levels

    num_to_abstract = {}
    for num in root.findall(f"{W}num"):
        num_id = num.get(f"{W}numId")
        aid_el = num.find(f"{W}abstractNumId")
        if aid_el is not None:
            num_to_abstract[num_id] = aid_el.get(f"{W}val")

    result = {}
    for num_id, aid in num_to_abstract.items():
        levels = abstract_fmt.get(aid, {})
        for ilvl, fmt in levels.items():
            result[(num_id, ilvl)] = fmt
    return result


def run_text(run, rels):
    """Extract text + bold/italic flags from a single w:r, expanding tabs/breaks."""
    rpr = run.find(f"{W}rPr")
    bold = rpr is not None and rpr.find(f"{W}b") is not None and rpr.find(f"{W}b").get(f"{W}val") != "0"
    italic = rpr is not None and rpr.find(f"{W}i") is not None and rpr.find(f"{W}i").get(f"{W}val") != "0"
    parts = []
    for child in run:
        tag = child.tag
        if tag == f"{W}t":
            parts.append(child.text or "")
        elif tag == f"{W}tab":
            parts.append("\t")
        elif tag == f"{W}br":
            parts.append("\n")
    return "".join(parts), bold, italic


def merge_runs(runs):
    """Merge adjacent (text, bold, italic) runs with identical formatting, then wrap in ** / *."""
    merged = []
    for text, bold, italic in runs:
        if not text:
            continue
        if merged and merged[-1][1] == bold and merged[-1][2] == italic:
            merged[-1] = (merged[-1][0] + text, bold, italic)
        else:
            merged.append((text, bold, italic))
    out = []
    for text, bold, italic in merged:
        escaped = text
        if bold:
            escaped = f"**{escaped}**"
        if italic:
            escaped = f"*{escaped}*"
        out.append(escaped)
    return "".join(out)


def paragraph_inline_runs(p, rels):
    """Walk a w:p's direct children (runs + hyperlinks) into a list of (text, bold, italic)."""
    runs = []
    for child in p:
        tag = child.tag
        if tag == f"{W}r":
            runs.append(run_text(child, rels))
        elif tag == f"{W}hyperlink":
            rid = child.get(f"{R}id")
            url = rels.get(rid) if rid else None
            inner = []
            for r in child.findall(f"{W}r"):
                inner.append(run_text(r, rels))
            link_text = merge_runs(inner)
            if url and link_text.strip():
                runs.append((f"[{link_text}]({url})", False, False))
            elif link_text.strip():
                runs.append((link_text, False, False))
    return runs


def paragraph_text(p, rels):
    return merge_runs(paragraph_inline_runs(p, rels))


def paragraph_style(p):
    ppr = p.find(f"{W}pPr")
    if ppr is None:
        return None
    pstyle = ppr.find(f"{W}pStyle")
    return pstyle.get(f"{W}val") if pstyle is not None else None


def paragraph_num_info(p):
    ppr = p.find(f"{W}pPr")
    if ppr is None:
        return None
    numpr = ppr.find(f"{W}numPr")
    if numpr is None:
        return None
    ilvl_el = numpr.find(f"{W}ilvl")
    numid_el = numpr.find(f"{W}numId")
    ilvl = ilvl_el.get(f"{W}val") if ilvl_el is not None else "0"
    numid = numid_el.get(f"{W}val") if numid_el is not None else None
    return ilvl, numid


def cell_text(tc, rels):
    texts = []
    for p in tc.findall(f"{W}p"):
        t = paragraph_text(p, rels)
        if t.strip():
            texts.append(t.strip())
    return "<br>".join(texts)


def table_to_markdown(tbl, rels):
    rows = []
    for tr in tbl.findall(f"{W}tr"):
        cells = [cell_text(tc, rels) for tc in tr.findall(f"{W}tc")]
        rows.append(cells)
    if not rows:
        return None
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]

    def esc(cell):
        return cell.replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(esc(c) for c in rows[0]) + " |"]
    lines.append("| " + " | ".join(["---"] * ncols) + " |")
    for r in rows[1:]:
        lines.append("| " + " | ".join(esc(c) for c in r) + " |")
    return "\n".join(lines)


def convert(docx_path, out_path):
    with zipfile.ZipFile(docx_path) as zf:
        rels = load_rels(zf)
        num_formats = load_num_formats(zf)
        doc = ET.fromstring(zf.read("word/document.xml"))

    body = doc.find(f"{W}body")

    title = ""
    blocks = []
    list_buffer = []  # accumulate consecutive list-item lines
    h1_count = 0
    h2_count = 0

    def flush_list():
        nonlocal list_buffer
        if list_buffer:
            blocks.append("\n".join(list_buffer))
            list_buffer = []

    for el in body:
        tag = el.tag
        if tag == f"{W}p":
            style = paragraph_style(el)
            if style in SKIP_STYLES:
                continue
            if style == "Title":
                title = paragraph_text(el, rels).strip()
                continue

            num_info = paragraph_num_info(el)
            text = paragraph_text(el, rels).strip()
            if not text:
                continue

            if style == "Heading1":
                flush_list()
                h1_count += 1
                h2_count = 0
                blocks.append(f"## {text} {{#section-{h1_count}}}")
                if h1_count == 1:
                    blocks.append(DIRECTIONS_BLOCK)
            elif style == "Heading2":
                flush_list()
                h2_count += 1
                blocks.append(f"### {text} {{#section-{h1_count}-{h2_count}}}")
            elif num_info is not None:
                ilvl, numid = num_info
                fmt = num_formats.get((numid, ilvl), "bullet")
                indent = "  " * int(ilvl)
                marker = "1." if fmt == "decimal" else "-"
                list_buffer.append(f"{indent}{marker} {text}")
            else:
                flush_list()
                blocks.append(text)
        elif tag == f"{W}tbl":
            flush_list()
            md_table = table_to_markdown(el, rels)
            if md_table:
                blocks.append(md_table)

    flush_list()

    frontmatter = f"---\ntitle: {title}\nlang: fa\n---\n"
    content = frontmatter + "\n\n" + INTRO_BLOCK + "\n\n" + "\n\n".join(blocks) + "\n"

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    print(f"Wrote {out_path}")
    print(f"  sections (H1): {h1_count}")
    print(f"  subsections (H2): {sum(1 for b in blocks if b.startswith('### '))}")
    print(f"  tables: {sum(1 for b in blocks if b.startswith('| '))}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python docx_to_md.py <input.docx> <output.md>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
