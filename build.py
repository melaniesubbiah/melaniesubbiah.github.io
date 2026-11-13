#!/usr/bin/env python3
"""Build the site: render src/*.html through src/_layout.html into the repo root.

Usage:  python3 build.py          (no dependencies beyond the Python 3 standard library)

Placeholders available inside src/ pages:
  {{ publications }}   the full publication list, newest first
  {{ selected }}       cards for entries marked `selected = {true}`
  {{ theme:<key> }}    compact list of entries tagged with theme <key> (the tag as a slug)
  {{ theme_links }}    research themes as pills linking to the filtered publications page
  {{ theme_filters }}  filter buttons for the publications page
  {{ mentee_flow }}     flow diagram of MENTEES (teaching page)
  {{ updated }}        build date, e.g. "October 2026"
"""

import datetime
import html
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
BIB = ROOT / "data" / "publications.bib"
SITE_URL = "https://melaniesubbiah.github.io/"
ME = "Subbiah"  # surname to bold in author lists
MAX_AUTHORS = 10

# Luna (dog 2) marks the current page in the nav (on the dogs page, which has no nav item, she stands
# just right of the name instead). Clicking her opens the dogs page with her photo outlined.
NAV_DOG = ('<a class="dog dog-2" href="dogs.html#luna" title="Meet Luna">'
           '<img src="assets/img/dog-2.svg" alt="Luna the dog" width="58" height="46"></a>')

# Research themes come from the `tags` field in the .bib: any new tag becomes a theme
# automatically (homepage pill, filter button, colored dot). This list only sets the
# display order; tags not listed here follow in the order they first appear in the file.
THEME_ORDER = [
    "Psychology & mental health",
    "Interpretability & steering",
    "Safety & fairness",
    "Narrative",
]
THEME_COLORS = 12  # --t-1 ... --t-12 in style.css; colors repeat after that

# Columbia research mentees, drawn as the flow diagram on the teaching page ({{ mentee_flow }}).
# Each path runs left to right through FLOW_COLUMNS; a path can skip a column (undergrads who
# didn't stay for a master's go straight to their outcome).
MENTEES = [
    ("Haaris Mian", ["Master's", "Paper", "Ph.D."]),
    ("Zara Hall", ["Undergrad", "Master's", "Paper", "Ph.D."]),
    ("Marvin Limpijankit", ["Master's", "Paper", "Ph.D."]),
    ("Adam Štorek", ["Undergrad", "Master's", "Paper", "Ph.D."]),
    ("Bobby Yilun Hua", ["Undergrad", "Paper", "Ph.D."]),
    ("Sean Zhang", ["Master's", "Paper", "Industry"]),
    ("Akankshya Mishra", ["Master's", "Paper", "Industry"]),
    ("Kate Harwood", ["Master's", "Paper", "Industry"]),
    ("Mukur Gupta", ["Master's", "Paper", "Industry"]),
    ("Nikhil Varimalla", ["Master's", "Paper", "Industry"]),
    ("Jacklyn Tsai", ["Undergrad", "Thesis", "Industry"]),
]
# columns left to right, nodes top to bottom (this order keeps bands from crossing)
FLOW_COLUMNS = [["Undergrad"], ["Master's"], ["Thesis", "Paper"], ["Industry", "Ph.D."]]
# what the diagram shows for each milestone (nodes not listed show their key)
FLOW_LABELS = {"Thesis": "Wrote a thesis", "Paper": "Published a paper",
               "Industry": "Working in industry", "Ph.D.": "Completing a PhD"}
FLOW_BELOW = {"Paper"}   # nodes labelled below the diagram (with a leader line) instead of beside

LINK_FIELDS = [  # (bib field, label) in display order
    ("url", "Paper"),
    ("pdf", "PDF"),
    ("code", "Code"),
    ("data", "Data"),
    ("slides", "Slides"),
    ("poster", "Poster"),
    ("video", "Video"),
]

# Short venue names, matched in order against booktitle/journal when `venue` is absent.
VENUE_PATTERNS = [
    (r"Findings.*EMNLP|Empirical Methods.*Findings", "Findings of EMNLP"),
    (r"Findings.*ACL|Findings of the Association", "Findings of ACL"),
    (r"Transactions of the Association for Computational Linguistics", "TACL"),
    (r"Empirical Methods in Natural Language Processing|EMNLP", "EMNLP"),
    (r"North American Chapter|NAACL", "NAACL"),
    (r"European Chapter|EACL", "EACL"),
    (r"Annual Meeting of the Association for Computational Linguistics|\bACL\b", "ACL"),
    (r"Neural Information Processing Systems|NeurIPS", "NeurIPS"),
    (r"International Conference on Learning Representations|ICLR", "ICLR"),
    (r"International Conference on Machine Learning|ICML", "ICML"),
    (r"Conference on Language Modeling|COLM", "COLM"),
    (r"Natural Language Generation|INLG", "INLG"),
    (r"COLING|Computational Linguistics", "COLING"),
    (r"CHI Conference|Human Factors in Computing", "CHI"),
    (r"AAAI", "AAAI"),
    (r"arXiv", "arXiv"),
]


# --------------------------------------------------------------------------- BibTeX

def parse_bib(text):
    """Parse BibTeX into a list of {'type', 'key', field: value} dicts, in file order."""
    entries = []
    i = 0
    while True:
        m = re.compile(r"@(\w+)\s*\{\s*([^,\s]*)\s*,").search(text, i)
        if not m:
            break
        entry = {"type": m.group(1).lower(), "key": m.group(2)}
        i = m.end()
        while True:
            fm = re.compile(r"\s*(\w+)\s*=\s*").match(text, i)
            if not fm:
                break
            name = fm.group(1).lower()
            i = fm.end()
            if text[i] == "{":
                depth, j = 0, i
                while True:
                    if text[j] == "{":
                        depth += 1
                    elif text[j] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                value, i = text[i + 1:j], j + 1
            elif text[i] == '"':
                j = text.index('"', i + 1)
                value, i = text[i + 1:j], j + 1
            else:
                vm = re.compile(r"[^,}\s]+").match(text, i)
                value, i = vm.group(0), vm.end()
            entry[name] = " ".join(value.split())
            sep = re.compile(r"\s*,?").match(text, i)
            i = sep.end()
        if entry["type"] not in ("comment", "string", "preamble"):
            entries.append(entry)
    return entries


ACCENTS = {"'": "\u0301", "`": "\u0300", "^": "\u0302", '"': "\u0308", "~": "\u0303",
           "v": "\u030c", "c": "\u0327", "u": "\u0306", "=": "\u0304", ".": "\u0307"}


def delatex(s):
    """Turn common LaTeX escapes into plain Unicode text."""
    s = re.sub(r"\\([`'^\"~=.]|[vcu](?![a-zA-Z]))\s*\{?\\?([a-zA-Z])\}?",
               lambda m: m.group(2) + ACCENTS[m.group(1)], s)
    s = s.replace("\\&", "&").replace("--", "\u2013").replace("~", "\u00a0")
    s = re.sub(r"\\(textit|emph|textbf)\{([^}]*)\}", r"\2", s)
    s = s.replace("{", "").replace("}", "")
    return unicodedata.normalize("NFC", s)


# --------------------------------------------------------------------------- formatting

def esc(s):
    return html.escape(s, quote=True)


def format_name(raw):
    raw = raw.strip()
    star = "*" in raw
    raw = raw.replace("*", "").strip()
    if "," in raw:
        last, first = [p.strip() for p in raw.split(",", 1)]
        name = f"{first} {last}".strip()
    else:
        last = raw.split()[-1] if raw else raw
        name = raw
    text = esc(name) + ("*" if star else "")
    if last == ME:
        text = f'<strong class="me">{text}</strong>'
    return text, star


def format_authors(field):
    names = [n for n in re.split(r"\s+and\s+", delatex(field)) if n.strip()]
    truncated = names and names[-1].strip().lower() == "others"
    if truncated:
        names = names[:-1]
    if len(names) > MAX_AUTHORS:
        mine = [k for k, n in enumerate(names) if ME in n]
        keep = max(6, (mine[0] + 1) if mine else 0)
        truncated, names = True, names[:keep]
    parts = [format_name(n) for n in names]
    out = ", ".join(p for p, _ in parts)
    if truncated:
        out += ", et al."
    return out, any(s for _, s in parts)


def guess_venue(e):
    if e.get("venue"):
        return delatex(e["venue"])
    where = delatex(e.get("booktitle") or e.get("journal") or e.get("publisher") or "")
    for pattern, short in VENUE_PATTERNS:
        if re.search(pattern, where):
            return f"{short} {e.get('year', '')}".strip()
    return f"{where} {e.get('year', '')}".strip()


def load_publications():
    pubs = []
    for order, e in enumerate(parse_bib(BIB.read_text(encoding="utf-8"))):
        authors, has_equal = format_authors(e.get("author", ""))
        pubs.append({
            "key": e["key"],
            "order": order,
            "year": int(re.sub(r"\D", "", e.get("year", "0")) or 0),
            "title": delatex(e.get("title", "Untitled")),
            "authors": authors,
            "equal": has_equal,
            "venue": guess_venue(e),
            "award": delatex(e.get("award", "")),
            "selected": e.get("selected", "").lower() in ("true", "yes", "1"),
            "blurb": delatex(e.get("blurb", "")),
            "tags": [delatex(t).strip() for t in e.get("tags", "").split(",") if t.strip()],
            "links": [(label, e[f]) for f, label in LINK_FIELDS if e.get(f)],
        })
    pubs.sort(key=lambda p: (-p["year"], p["order"]))
    return pubs


def slug(label):
    s = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def collect_themes(pubs):
    """Turn every pub's tags into themes: [(slug, label, color)] in display order.
    Tags match case-insensitively; each pub gets p["themes"] as a list of slugs."""
    labels = {}
    for label in THEME_ORDER:
        labels.setdefault(slug(label), label)
    used = set()
    for p in sorted(pubs, key=lambda p: p["order"]):   # file order, for new tags
        p["themes"] = []
        for tag in p["tags"]:
            key = slug(tag)
            labels.setdefault(key, tag)
            if key not in p["themes"]:
                p["themes"].append(key)
            used.add(key)
    ordered = [k for k in labels if k in used]
    for p in pubs:   # dots follow the same order as the filter buttons
        p["themes"].sort(key=ordered.index)
    return [(k, labels[k], i % THEME_COLORS + 1) for i, k in enumerate(ordered)]


def link_attrs(href):
    external = href.startswith("http")
    return f'href="{esc(href)}"' + (' target="_blank" rel="noopener"' if external else "")


def render_links(p):
    return "".join(f'<a class="pub-link" {link_attrs(h)}>{esc(label)}</a>' for label, h in p["links"])


def render_title(p, cls="pub-title"):
    if p["links"]:
        return f'<a class="{cls}" {link_attrs(p["links"][0][1])}>{esc(p["title"])}</a>'
    return f'<span class="{cls}">{esc(p["title"])}</span>'


def render_award(p):
    return f'<span class="award">{esc(p["award"])}</span>' if p["award"] else ""


def theme_attrs(key, color):
    return f'data-theme="{key}" style="--t: var(--t-{color})"'


def render_dots(p, themes):
    """One colored dot per research theme; hover shows the theme name."""
    if not p["themes"]:
        return ""
    info = {k: (label, color) for k, label, color in themes}
    dots = "".join(f'<span class="dot" {theme_attrs(k, info[k][1])} title="{esc(info[k][0])}"></span>'
                   for k in p["themes"])
    return f'<span class="dots" aria-hidden="true">{dots}</span>'


def render_pub(p, themes, blurb=False):
    keys = " ".join(p["themes"])
    note = f'\n    <span class="pub-blurb">{esc(p["blurb"])}</span>' if blurb and p["blurb"] else ""
    award = f'<span class="pub-award">{render_award(p)}</span>' if p["award"] else ""
    awarded = ' data-award' if p["award"] else ""
    return f"""<li class="pub" data-themes="{esc(keys)}"{awarded}>
  <span class="pub-venue">{esc(p["venue"])}{render_dots(p, themes)}{award}</span>
  <div class="pub-body">
    {render_title(p)}
    <span class="pub-authors">{p["authors"]}</span>{note}
    <span class="pub-meta">{render_links(p)}</span>
  </div>
</li>"""


def render_publications(pubs, themes):
    out = ['<ol class="pub-list pub-all">']
    out.extend(render_pub(p, themes) for p in pubs)
    out.append("</ol>")
    if any(p["equal"] for p in pubs):
        out.append('<p class="footnote">* indicates equal contribution</p>')
    return "\n".join(out)


def render_selected(pubs, themes):
    items = "\n".join(render_pub(p, themes, blurb=True) for p in pubs if p["selected"])
    return f'<ol class="pub-list">\n{items}\n</ol>'


def render_theme(pubs, key):
    items = [p for p in pubs if key in p["themes"]]
    lis = "\n".join(f'<li>{render_title(p, "theme-title")} <span class="theme-venue">{esc(p["venue"])}</span></li>'
                    for p in items)
    return f'<ul class="theme-list">\n{lis}\n</ul>'


def render_theme_links(themes):
    lis = "\n".join(f'<li {theme_attrs(k, c)}><a href="publications.html#{k}"><span class="dot"></span>{esc(label)}</a></li>'
                    for k, label, c in themes)
    return f'<ul class="themes">\n{lis}\n</ul>'


def render_theme_filters(themes):
    buttons = ['<button class="filter" type="button" data-filter="" aria-pressed="true">All</button>']
    buttons += [f'<button class="filter" type="button" data-filter="{k}" {theme_attrs(k, c)} aria-pressed="false">{esc(label)}</button>'
                for k, label, c in themes]
    buttons.append('<button class="filter filter-award" type="button" data-filter="awards" aria-pressed="false">Awards</button>')
    return "\n".join(buttons)


def render_mentee_flow():
    """Flow (Sankey) diagram of MENTEES as inline SVG, with a color key. Bands are colored by
    where the student started (undergrad or master's)."""
    unit, gap, node_w = 16, 14, 12          # px per student, gap between nodes, node width
    width, pad_l, pad_r, top = 820, 104, 160, 36  # top: room for a label above a thin node; pad_r fits "Working in industry 6"
    ncol = len(FLOW_COLUMNS)
    col_x = [pad_l + c * (width - pad_l - pad_r - node_w) / (ncol - 1) for c in range(ncol)]
    col_of = {name: c for c, col in enumerate(FLOW_COLUMNS) for name in col}
    paths = [(name, [(col_of[n], n) for n in path]) for name, path in MENTEES]
    links = {}   # (src, dst, start) -> names
    for name, path in paths:
        for a, b in zip(path, path[1:]):
            links.setdefault((a, b, path[0][1]), []).append(name)
    size = {}
    for (a, b, _), names in links.items():
        size.setdefault(a, [0, 0])[1] += len(names)
        size.setdefault(b, [0, 0])[0] += len(names)
    nodes = {}   # (col, name) -> [x, y, h]
    for c, col in enumerate(FLOW_COLUMNS):
        # bands that skip over this column pass above its nodes, so start the stack below them
        skip = sum(len(v) for (a, b, _), v in links.items() if a[0] < c < b[0])
        y = top + (skip * unit + gap * 2 if skip else 0)
        for name in col:
            h = max(size.get((c, name), [0, 0])) * unit
            if h:
                nodes[(c, name)] = [col_x[c], y, h]
                y += h + gap
    bottom = max(y + h for _, y, h in nodes.values())
    height = bottom + (40 if any(k[1] in FLOW_BELOW for k in nodes) else 6)   # room for labels hung below the diagram
    out_y = {k: v[1] for k, v in nodes.items()}
    in_y = {k: v[1] for k, v in nodes.items()}
    color = {"Undergrad": "ug", "Master's": "ms"}
    bands = []
    for key in sorted(links, key=lambda k: (nodes[k[0]][1], nodes[k[1]][1], k[2] != "Undergrad")):
        a, b, start = key
        names = links[key]
        h = len(names) * unit
        x0, x1 = nodes[a][0] + node_w, nodes[b][0]
        y0, y1 = out_y[a], in_y[b]
        out_y[a] += h
        in_y[b] += h
        mx = (x0 + x1) / 2
        d = (f"M{x0:.1f},{y0:.1f} C{mx:.1f},{y0:.1f} {mx:.1f},{y1:.1f} {x1:.1f},{y1:.1f} "
             f"L{x1:.1f},{y1 + h:.1f} C{mx:.1f},{y1 + h:.1f} {mx:.1f},{y0 + h:.1f} {x0:.1f},{y0 + h:.1f} Z")
        bands.append(f'<path class="flow-band flow-{color[start]}" d="{d}"></path>')
    rects, labels, leaders = [], [], []
    for (c, name), (x, y, h) in nodes.items():
        rects.append(f'<rect class="flow-node" x="{x:.1f}" y="{y:.1f}" width="{node_w}" height="{h:.1f}" rx="3"></rect>')
        n = max(size[(c, name)])
        text = f'{esc(FLOW_LABELS.get(name, name))} <tspan class="flow-count">{n}</tspan>'
        if c < 2:     # starting columns: label to the left, clear of the bands
            # Master's: centre on the part of the node below its incoming bands
            inc = sum(len(v) for (a, b, _), v in links.items() if b == (c, name)) * unit
            labels.append(f'<text class="flow-label" x="{x - 8:.1f}" y="{y + inc + (h - inc) / 2:.1f}" '
                          f'text-anchor="end" dy=".35em">{text}</text>')
        elif name in FLOW_BELOW:   # label hung below the whole diagram, tied to its node by a thin line
            cx = x + node_w / 2
            leaders.append(f'<line class="flow-leader" x1="{cx:.1f}" y1="{y + h + 4:.1f}" x2="{cx:.1f}" y2="{bottom + 20:.1f}"></line>')
            labels.append(f'<text class="flow-label" x="{cx:.1f}" y="{bottom + 34:.1f}" text-anchor="middle">{text}</text>')
        elif h <= unit:   # a one-student node is too thin to label beside, so label it above, tied by a thin line
            cx = x + node_w / 2
            leaders.append(f'<line class="flow-leader" x1="{cx:.1f}" y1="{y - 4:.1f}" x2="{cx:.1f}" y2="{y - 12:.1f}"></line>')
            labels.append(f'<text class="flow-label" x="{cx:.1f}" y="{y - 17:.1f}" text-anchor="middle">{text}</text>')
        else:
            cls = "flow-label" + (" flow-label-mid" if c < ncol - 1 else "")
            labels.append(f'<text class="{cls}" x="{x + node_w + 8:.1f}" y="{y + h / 2:.1f}" dy=".35em">{text}</text>')
    counts = {}
    for _, path in MENTEES:
        route = " \u2192 ".join(FLOW_LABELS.get(n, n) for n in path)
        counts[route] = counts.get(route, 0) + 1
    desc = "; ".join(f"{n} {'student' if n == 1 else 'students'}: {route}" for route, n in counts.items())
    return (f'<figure class="mentee-flow"><svg viewBox="0 0 {width} {height:.0f}" role="img" '
            f'aria-label="Flow of {len(MENTEES)} Columbia research mentees from undergrad or master\'s, to what came of the project, to where they went next">'
            f'<desc>{esc(desc)}</desc>{"".join(bands)}{"".join(leaders)}{"".join(rects)}{"".join(labels)}</svg>'
            '<figcaption class="flow-key"><span><i class="flow-swatch flow-ug"></i>Started as an undergrad</span>'
            '<span><i class="flow-swatch flow-ms"></i>Started as a master\'s student</span></figcaption></figure>')


# --------------------------------------------------------------------------- pages

def read_page(path):
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text


def build():
    pubs = load_publications()
    themes = collect_themes(pubs)
    layout = (SRC / "_layout.html").read_text(encoding="utf-8")
    updated = datetime.date.today().strftime("%B %Y")
    pages = sorted(p for p in SRC.glob("*.html") if not p.name.startswith("_"))
    for path in pages:
        meta, body = read_page(path)

        def fill(m):
            name = m.group(1).strip()
            if name == "publications":
                return render_publications(pubs, themes)
            if name == "selected":
                return render_selected(pubs, themes)
            if name.startswith("theme:"):
                return render_theme(pubs, name.split(":", 1)[1].strip())
            if name == "theme_links":
                return render_theme_links(themes)
            if name == "theme_filters":
                return render_theme_filters(themes)
            if name == "mentee_flow":
                return render_mentee_flow()
            if name == "updated":
                return updated
            raise KeyError(f"{path.name}: unknown placeholder {{{{ {name} }}}}")

        body = re.sub(r"\{\{\s*([\w:-]+)\s*\}\}", fill, body)
        nav = meta.get("nav", path.stem)
        out = layout
        for key, value in {
            "title": meta.get("title", "Melanie Subbiah"),
            "description": meta.get("description", ""),
            "canonical": SITE_URL + ("" if path.name == "index.html" else path.name),
            "content": body,
            "updated": updated,
        }.items():
            out = out.replace("{{ " + key + " }}", value)
        # mark the current page in the nav, with dog 2 standing in front of it
        out = re.sub(r'<a data-nav="%s"' % re.escape(nav),
                     NAV_DOG + '<a data-nav="%s" aria-current="page"' % nav, out)
        if nav == "dogs":   # right of the name, so the name never shifts
            out = re.sub(r'(<a class="wordmark".*?</a>)', lambda m: m.group(1) + NAV_DOG, out, count=1, flags=re.S)
        (ROOT / path.name).write_text(out, encoding="utf-8")
        print(f"built {path.name}")

    urls = "\n".join(
        f"  <url><loc>{SITE_URL}{'' if p.name == 'index.html' else p.name}</loc></url>" for p in pages)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n', encoding="utf-8")
    print(f"{len(pubs)} publications")


if __name__ == "__main__":
    build()
