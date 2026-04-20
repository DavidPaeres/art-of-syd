#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_index.py
Reads images/imagesManifest.csv -> writes index.html at the repo root.

CSV columns: filename, title, categoria, alt_text, publish, sort_order, notes
Valid categories: Canvases | Watercolors | Colorpencils | Crafts | Woodburnings
"""

from pathlib import Path
import csv, sys, html
from collections import OrderedDict

CATEGORY_ORDER = ["Canvases", "Watercolors", "Colorpencils", "Crafts", "Woodburnings"]

CATEGORY_FOLDER = {
    "Canvases":     "canvas",
    "Watercolors":  "watercolorpencils",
    "Colorpencils": "colorpencils",
    "Crafts":       "crafts",
    "Woodburnings": "woodburnings",
}

SHOW_MORE_CATS = {"Watercolors", "Colorpencils"}
SHOW_MORE_LIMIT = 12


def _e(s):
    return html.escape(str(s), quote=True)

def slug(t):
    return "".join(c.lower() if c.isalnum() else "-" for c in (t or "").strip()).strip("-") or "sec"

def title_or_stem(filename, title):
    return title if title else Path(filename).stem


def read_manifest(csv_path: Path) -> OrderedDict:
    data = OrderedDict((c, []) for c in CATEGORY_ORDER)

    if not csv_path.exists():
        print(f"ERROR: Manifest not found: {csv_path}")
        sys.exit(1)

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.lower().strip() for h in reader.fieldnames]

        required = {"filename", "categoria", "publish"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"ERROR: Missing required columns: {missing}")
            sys.exit(1)

        has_title = "title" in (reader.fieldnames or [])

        for row in reader:
            if (row.get("publish") or "").strip().lower() != "yes":
                continue
            fn  = (row.get("filename") or "").strip()
            cat = (row.get("categoria") or "").strip()
            ttl = (row.get("title") or "").strip() if has_title else ""

            if fn and cat in data:
                data[cat].append({"filename": fn, "title": ttl})

    return data


def _items_html(items, folder, group, item_class):
    out = []
    for it in items:
        t = _e(title_or_stem(it["filename"], it["title"]))
        s = _e(f"images/{folder}/{it['filename']}")
        g = _e(group)
        out.append(
            f'                <div class="{item_class}">\n'
            f'                  <a href="{s}" data-lightbox="{g}" data-title="{t}">\n'
            f'                    <img loading="lazy" src="{s}" alt="{t}">\n'
            f'                    <div class="hover-text">{t}</div>\n'
            f'                  </a>\n'
            f'                </div>'
        )
    return "\n".join(out)


def build_nav_and_sections(data: OrderedDict):
    nav_parts, section_parts = [], []

    for cat, items in data.items():
        if not items:
            continue

        sid      = slug(cat)
        folder   = CATEGORY_FOLDER[cat]
        more     = cat in SHOW_MORE_CATS
        grid_id  = f"grid-{sid}"
        strip_id = f"strip-{sid}"
        limit    = ' data-limit' if more else ''
        btn_more = (
            f'              <div class="showmore-wrap">\n'
            f'                <button id="btn-more-{sid}" class="button secondary">Show more</button>\n'
            f'              </div>\n'
        ) if more else ''

        grid_html  = _items_html(items, folder, cat, "grid-item")
        strip_html = _items_html(items, folder, cat, "h-item")

        nav_parts.append(f'      <a href="#{sid}">{_e(cat)}</a>')

        section_parts.append(f"""
      <!-- ===== {cat.upper()} ===== -->
      <section class="section" id="{sid}">
        <h2>{_e(cat)}</h2>

        <!-- Mode A -->
        <div class="modeA">
          <details open>
            <summary aria-label="Toggle {_e(cat)}"><h3>Gallery</h3></summary>
            <div class="panel">
              <div class="grid" id="{grid_id}"{limit}>
{grid_html}
              </div>
{btn_more}            </div>
          </details>
        </div>

        <!-- Mode B -->
        <div class="modeB">
          <div class="row">
            <div class="row-head">
              <h3>{_e(cat)}</h3>
              <div class="row-ctrls">
                <button class="button secondary" data-scroll="#{strip_id}" data-dir="left">&#x27F5;</button>
                <button class="button secondary" data-scroll="#{strip_id}" data-dir="right">&#x27F6;</button>
              </div>
            </div>
            <div class="strip" id="{strip_id}">
{strip_html}
            </div>
          </div>
        </div>
      </section>""")

    return "\n".join(nav_parts), "\n".join(section_parts)


def build_showmore_js(data: OrderedDict) -> str:
    parts = []
    for cat in SHOW_MORE_CATS:
        if not data.get(cat):
            continue
        sid = slug(cat)
        parts.append(
            f"    const _g{sid} = document.getElementById('grid-{sid}');\n"
            f"    const _b{sid} = document.getElementById('btn-more-{sid}');\n"
            f"    if (_b{sid} && _g{sid}) {{\n"
            f"      _b{sid}.addEventListener('click', () => {{\n"
            f"        _g{sid}.removeAttribute('data-limit');\n"
            f"        _b{sid}.style.display = 'none';\n"
            f"      }});\n"
            f"    }}"
        )
    return "\n".join(parts)


def build_search_js(data: OrderedDict) -> str:
    grid_ids = [f"'grid-{slug(c)}'" for c in SHOW_MORE_CATS if data.get(c)]
    btn_ids  = [f"'btn-more-{slug(c)}'" for c in SHOW_MORE_CATS if data.get(c)]
    g_list   = ", ".join(grid_ids)
    b_list   = ", ".join(btn_ids)
    return (
        f"    const _smGrids = [{g_list}].map(id => document.getElementById(id)).filter(Boolean);\n"
        f"    const _smBtns  = [{b_list}].map(id => document.getElementById(id)).filter(Boolean);\n"
        f"    const _smHad   = _smGrids.map(g => g.hasAttribute('data-limit'));\n"
    )


def build_html(data: OrderedDict) -> str:
    nav_html, sections_html = build_nav_and_sections(data)
    showmore_js = build_showmore_js(data)
    search_js   = build_search_js(data)

    return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Art made by Sydney</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link href="https://cdn.jsdelivr.net/npm/lightbox2@2/dist/css/lightbox.min.css" rel="stylesheet" />
  <style>
    :root{
      --bg:#111; --bg-2:#1a1a1a; --panel:#1c1c1c; --ink:#fff; --muted:#bbb;
      --accent:#ff69b4; --line:#2f2f2f;
      --radius:12px; --maxw:1200px; --sticky-h:72px;
    }
    *{box-sizing:border-box}
    html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:Arial,system-ui,sans-serif}

    header.hero{background:var(--panel);border-bottom:1px solid var(--line);text-align:center;padding:28px 16px 26px}
    .hero h1{margin:0;font-size:2.1rem}
    .hero .subtitle{color:var(--muted);margin:8px 0 16px}
    .hero-actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}

    .sticky-nav{position:sticky;top:0;z-index:100;background:var(--panel);border-bottom:1px solid var(--line);display:flex;justify-content:center}
    .nav{display:flex;gap:10px;padding:12px;flex-wrap:wrap;justify-content:center}
    .nav a{display:inline-flex;align-items:center;height:40px;padding:0 16px;border-radius:999px;background:#232323;border:1px solid var(--line);color:#fff;text-decoration:none;font-weight:600;font-size:0.95rem}
    .nav a:hover{border-color:#444;background:#2a2a2a}
    :target{scroll-margin-top:calc(var(--sticky-h) + 10px)}

    .side-switch{position:fixed;right:16px;top:50vh;transform:translateY(-50%);display:flex;flex-direction:column;gap:6px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:6px;z-index:90}
    .side-switch button{border:1px solid var(--line);background:#222;color:#fff;font-size:1.25rem;line-height:1;padding:6px 10px;border-radius:10px;cursor:pointer;min-width:46px}
    .side-switch button.active{background:var(--accent);border-color:transparent;color:#000;font-weight:700}
    .side-switch .lbl{font-size:0.75rem;color:var(--muted);text-align:center;margin-bottom:4px}
    .side-switch .arrow{font-size:1.35rem;line-height:1;display:inline-block}

    main{max-width:var(--maxw);margin:0 auto;padding:20px 16px 24px}
    .section{padding:28px 0;border-bottom:1px solid var(--line)}
    .section h2{margin:0 0 8px;border-bottom:1px solid #444;padding-bottom:10px}

    .button{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:#000;text-decoration:none;border:0;border-radius:999px;padding:10px 16px;font-weight:700;cursor:pointer}
    .button.secondary{background:transparent;color:#fff;border:1px solid var(--line)}

    .searchbar-global{display:flex;justify-content:center;margin:8px 0 18px}
    .searchbar-global input{width:100%;max-width:540px;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:#141414;color:#fff}

    details{border:1px solid var(--line);border-radius:var(--radius);background:var(--bg-2);margin-top:16px;overflow:hidden}
    summary{list-style:none;cursor:pointer;padding:12px 14px;display:flex;align-items:center;gap:10px}
    summary::-webkit-details-marker{display:none}
    summary h3{margin:0;color:var(--accent)}
    summary::after{content:"▾";color:#fff;margin-left:auto;transition:transform .2s ease;font-size:1.1rem}
    details[open] summary::after{transform:rotate(-180deg)}
    .panel{padding:10px 12px 16px;border-top:1px solid var(--line)}

    .grid{display:flex;flex-wrap:wrap;gap:18px;margin-top:10px}
    .grid-item{position:relative;width:calc(33.333% - 12px)}
    .grid img{width:100%;height:auto;border-radius:10px;cursor:pointer;display:block}
    .hover-text{position:absolute;left:0;right:0;bottom:0;padding:8px 10px;background:rgba(0,0,0,.7);border-radius:0 0 10px 10px;opacity:0;transition:opacity .25s}
    .grid-item:hover .hover-text,.h-item:hover .hover-text{opacity:1}

    .grid[data-limit] .grid-item{display:none}
    .grid[data-limit] .grid-item:nth-child(-n+""" + str(SHOW_MORE_LIMIT) + """){display:block}
    .showmore-wrap{margin-top:10px;display:flex;justify-content:center}

    .row{margin-top:16px;border:1px solid var(--line);border-radius:var(--radius);background:var(--bg-2)}
    .row-head{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--line)}
    .row-head h3{margin:0;color:var(--accent)}
    .strip{display:flex;gap:14px;overflow-x:auto;padding:14px;scroll-snap-type:x mandatory}
    .h-item{flex:0 0 auto;scroll-snap-align:start;width:280px;position:relative}
    .h-item img{width:100%;height:auto;border-radius:10px;display:block;cursor:pointer}
    .h-item .hover-text{position:absolute;left:0;right:0;bottom:0;padding:8px 10px;background:rgba(0,0,0,.7);border-radius:0 0 10px 10px;opacity:0;transition:opacity .25s}
    .row-ctrls{display:flex;gap:8px}
    .row-ctrls .button{padding:6px 10px;background:transparent;border:1px solid var(--line);color:#fff;border-radius:999px;cursor:pointer}

    body[data-mode="A"] .modeA{display:block}
    body[data-mode="A"] .modeB{display:none}
    body[data-mode="B"] .modeA{display:none}
    body[data-mode="B"] .modeB{display:block}

    @media(max-width:900px){.grid-item{width:calc(50% - 9px)}}
    @media(max-width:640px){
      .side-switch{right:10px;top:auto;bottom:16px;transform:none}
      .nav a{height:36px;padding:0 10px;font-size:0.85rem}
      .h-item{width:220px}
      .hero h1{font-size:1.7rem}
      input,.searchbar-global input{font-size:16px}
    }
    @media(max-width:480px){.grid-item{width:100%}}
  </style>
</head>
<body data-mode="A">

  <header class="hero" aria-label="Site intro">
    <h1>Art made by Sydney</h1>
    <p class="subtitle">Welcome to my trippy world.</p>
    <div class="hero-actions">
      <a class="button secondary" href="about.html">About Me</a>
      <a class="button" href="#contact">Contact</a>
    </div>
  </header>

  <div class="sticky-nav" id="stickyNav">
    <nav class="nav" aria-label="Primary">
%%NAV%%
    </nav>
  </div>

  <aside class="side-switch" aria-label="View mode switch">
    <div class="lbl">Scroll type</div>
    <button id="btnModeA" class="active" title="Vertical"><span class="arrow">&#x2195;&#xFE0E;</span></button>
    <button id="btnModeB" title="Horizontal"><span class="arrow">&#x2194;&#xFE0E;</span></button>
  </aside>

  <main>
    <div class="searchbar-global">
      <input id="searchGlobal" type="search" placeholder="Search all artworks..." aria-label="Search artworks" />
    </div>
%%SECTIONS%%
  </main>

  <footer id="contact" style="text-align:center;padding:24px 16px;background:#1c1c1c;border-top:1px solid var(--line)">
    <h2>Contact</h2>
    <p>If you&#39;re interested in any piece, send an email to: <strong>sydney25th@gmail.com</strong></p>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/lightbox2@2/dist/js/lightbox.min.js"></script>
  <script>
    function setStickyVar() {
      const bar = document.getElementById('stickyNav');
      if (bar) document.documentElement.style.setProperty('--sticky-h', Math.ceil(bar.getBoundingClientRect().height) + 'px');
    }
    window.addEventListener('load', setStickyVar);
    window.addEventListener('resize', setStickyVar);

    if (window.lightbox) lightbox.option({ albumLabel: "Image %1 of %2", fadeDuration: 200, resizeDuration: 200 });

    const root = document.body;
    const btnA = document.getElementById('btnModeA');
    const btnB = document.getElementById('btnModeB');
    if (localStorage.getItem('aos_mode') === 'B') setMode('B'); else setMode('A');
    btnA.addEventListener('click', () => setMode('A'));
    btnB.addEventListener('click', () => setMode('B'));
    function setMode(m) {
      root.setAttribute('data-mode', m);
      btnA.classList.toggle('active', m === 'A');
      btnB.classList.toggle('active', m === 'B');
      localStorage.setItem('aos_mode', m);
    }

%%SEARCH_JS%%

    const q = document.getElementById('searchGlobal');
    if (q) {
      q.addEventListener('input', () => {
        const term = q.value.trim().toLowerCase();
        const searching = term.length > 0;

        _smGrids.forEach((g, i) => {
          if (searching) {
            g.removeAttribute('data-limit');
            if (_smBtns[i]) _smBtns[i].style.display = 'none';
          } else {
            if (_smHad[i]) g.setAttribute('data-limit', '');
            if (_smBtns[i]) _smBtns[i].style.display = '';
          }
        });

        document.querySelectorAll('.grid-item, .h-item').forEach(it => {
          const text = (it.querySelector('img')?.alt || '').toLowerCase();
          it.style.display = searching ? (text.includes(term) ? '' : 'none') : '';
        });

        if (searching) {
          document.querySelectorAll('.modeA details').forEach(d => {
            if (Array.from(d.querySelectorAll('.grid-item')).some(c => c.style.display !== 'none')) d.open = true;
          });
        }
      });
    }

%%SHOWMORE_JS%%

    document.querySelectorAll('[data-scroll]').forEach(btn => {
      btn.addEventListener('click', () => {
        const el = document.querySelector(btn.getAttribute('data-scroll'));
        if (!el) return;
        el.scrollBy({ left: el.clientWidth * 0.8 * (btn.getAttribute('data-dir') === 'right' ? 1 : -1), behavior: 'smooth' });
      });
    });
  </script>
</body>
</html>""".replace("%%NAV%%", nav_html).replace("%%SECTIONS%%", sections_html).replace("%%SEARCH_JS%%", search_js).replace("%%SHOWMORE_JS%%", showmore_js)


def main():
    repo_root = Path(__file__).resolve().parent.parent
    csv_path  = repo_root / "images" / "imagesManifest.csv"
    out_html  = repo_root / "index.html"

    print(f"Reading: {csv_path}")
    data = read_manifest(csv_path)

    print("Generating index.html...")
    out_html.write_text(build_html(data), encoding="utf-8")

    total = sum(len(v) for v in data.values())
    print(f"Done: {total} published images -> {out_html}")


if __name__ == "__main__":
    main()
