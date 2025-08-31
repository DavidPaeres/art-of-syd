#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_index.py (template A/B)
--------------------------------
Lee images/imagesManifest.csv y genera TOOLS/index.html usando el
template que nos compartiste (hero -> sticky nav -> side switch, Mode A y Mode B,
buscador global con auto-expand, "Show more" en WCP, Lightbox2).

CSV (mínimo):
  filename, categoria, subcategoria, publish
Reglas:
  - publish == "no" -> se ignora
  - categoria en {P,C,W} (mayúscula)
  - P: images/<subcategoria>/<filename>   (subcategoria en minúsculas para ruta)
  - C: images/crafts/<filename>
  - W: images/woodburnings/<filename>
Opcional:
  - title -> hover/data-title/alt (fallback al stem del filename)

Salida:
  - TOOLS/index.html (junto al script)
"""

from pathlib import Path
import csv
from collections import OrderedDict
import sys
import html

# === Configuración / mapeos ===

CATEGORY_MAP = {
    "P": "paintings",
    "C": "crafts",
    "W": "woodburnings",
}

# Títulos "bonitos" para subcategorías de Paintings
SUBCATEGORY_TITLES = {
    "watercolorpencils": "Watercolors & Colorpencils",
    "canvas": "Canvases",
}

# Orden preferido de subcategorías (canvas primero, wcp después, luego el resto)
PREFERRED_SUBCAT_ORDER = ["canvas", "watercolorpencils"]


# === Utilidades ===

def slugify(text: str) -> str:
    """Id simple para HTML."""
    return "".join((ch.lower() if ch.isalnum() else "-") for ch in (text or "").strip()).strip("-") or "section"

def _e(s: str) -> str:
    """HTML escape."""
    return html.escape(str(s), quote=True)

def _title_or_stem(filename: str, title: str) -> str:
    """Escoge title si existe; si no, usa el stem del filename."""
    if title:
        return title
    return Path(filename).stem


# === Lectura del manifest ===

def read_manifest(csv_path: Path):
    """
    Devuelve:
    {
      "paintings": OrderedDict({ subcat: [ {"filename":..., "title":...}, ...], ... }),
      "crafts": [ {"filename":..., "title":...}, ... ],
      "woodburnings": [ {"filename":..., "title":...}, ... ]
    }
    """
    if not csv_path.exists():
        print(f"❌ No se encontró el manifest: {csv_path}")
        sys.exit(1)

    paintings = OrderedDict()
    crafts = []
    woodburnings = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("❌ CSV vacío o sin encabezados.")
            sys.exit(1)
        reader.fieldnames = [h.lower().strip() for h in reader.fieldnames]

        required = {"filename", "categoria", "subcategoria", "publish"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"❌ Faltan columnas requeridas: {missing}")
            sys.exit(1)

        has_title = "title" in (reader.fieldnames or [])

        for row in reader:
            if (row.get("publish") or "").strip().lower() == "no":
                continue

            filename = (row.get("filename") or "").strip()
            cat_code = (row.get("categoria") or "").strip().upper()
            subcat   = (row.get("subcategoria") or "").strip()
            title    = (row.get("title") or "").strip() if has_title else ""

            if not filename or cat_code not in CATEGORY_MAP:
                continue

            item = {"filename": filename, "title": title}

            if cat_code == "P":
                key = (subcat or "general").lower()
                if key not in paintings:
                    paintings[key] = []
                paintings[key].append(item)

            elif cat_code == "C":
                crafts.append(item)

            elif cat_code == "W":
                woodburnings.append(item)

    return {"paintings": paintings, "crafts": crafts, "woodburnings": woodburnings}


def _order_painting_subcats(paintings_od: OrderedDict) -> list[tuple[str, list]]:
    """Devuelve lista [(subcat, items), ...] reordenada: preferidos primero y luego el resto en orden de aparición."""
    keys = list(paintings_od.keys())
    ordered = []
    for pref in PREFERRED_SUBCAT_ORDER:
        if pref in paintings_od:
            ordered.append((pref, paintings_od[pref]))
    for k in keys:
        if k not in PREFERRED_SUBCAT_ORDER:
            ordered.append((k, paintings_od[k]))
    return ordered


# === Generación de HTML ===

def build_html(model) -> str:
    # ---- Chips de Paintings ----
    subcats_ordered = _order_painting_subcats(model["paintings"])
    chips_html = []
    for subcat, _items in subcats_ordered:
        chips_html.append(f'<span class="chip">{_e(SUBCATEGORY_TITLES.get(subcat, subcat.capitalize()))}</span>')
    chips_block = "\n            ".join(chips_html) if chips_html else ""

    # ---- Mode A (accordions) para Paintings ----
    modeA_paintings_parts = []
    for subcat, items in subcats_ordered:
        display_name = SUBCATEGORY_TITLES.get(subcat, subcat.capitalize())
        acc_id = f"a-{slugify(display_name)}"  # p.ej., a-canvases, a-watercolors-colorpencils
        is_wcp = (subcat == "watercolorpencils")
        # IDs especiales para que el JS del template funcione:
        if is_wcp:
            grid_id = "grid-wcp"
        else:
            grid_id = f"grid-{slugify(subcat)}"
        details_open = " open" if subcat in ("canvas",) else ""

        modeA_paintings_parts.append(f'          <details id="{acc_id}"{details_open}>')
        modeA_paintings_parts.append(f'            <summary aria-label="Toggle { _e(display_name) }"><h3>{_e(display_name)}</h3></summary>')
        modeA_paintings_parts.append('            <div class="panel">')
        grid_attrs = f' id="{grid_id}"' + (' data-limit' if is_wcp else '')
        modeA_paintings_parts.append(f'              <div class="grid"{grid_attrs}>')

        for it in items:
            title = _title_or_stem(it["filename"], it.get("title", ""))
            safe_title = _e(title)
            src = f'images/{subcat}/{it["filename"]}'
            group = subcat  # grupo lightbox
            modeA_paintings_parts.append('                <div class="grid-item">')
            modeA_paintings_parts.append(f'                  <a href="{_e(src)}" data-lightbox="{_e(group)}" data-title="{safe_title}">')
            modeA_paintings_parts.append(f'                    <img loading="lazy" src="{_e(src)}" alt="{safe_title}">')
            modeA_paintings_parts.append(f'                    <div class="hover-text">{safe_title}</div>')
            modeA_paintings_parts.append('                  </a>')
            modeA_paintings_parts.append('                </div>')

        modeA_paintings_parts.append('              </div>')
        if is_wcp:
            modeA_paintings_parts.append('              <div class="showmore-wrap">')
            modeA_paintings_parts.append('                <button id="btn-more-wcp" class="button secondary">Show more</button>')
            modeA_paintings_parts.append('              </div>')
        modeA_paintings_parts.append('            </div>')
        modeA_paintings_parts.append('          </details>')

    modeA_paintings_html = "\n".join(modeA_paintings_parts)

    # ---- Mode B (horizontal) para Paintings ----
    modeB_paintings_parts = []
    for subcat, items in subcats_ordered:
        display_name = SUBCATEGORY_TITLES.get(subcat, subcat.capitalize())
        row_id = f"row-{slugify(subcat)}"
        strip_id = "strip-wcp" if subcat == "watercolorpencils" else f"strip-{slugify(subcat)}"
        modeB_paintings_parts.append(f'          <div class="row" id="{row_id}">')
        modeB_paintings_parts.append('            <div class="row-head">')
        modeB_paintings_parts.append(f'              <h3>{_e(display_name)}</h3>')
        modeB_paintings_parts.append('              <div class="row-ctrls">')
        modeB_paintings_parts.append(f'                <button class="button secondary" data-scroll="#{strip_id}" data-dir="left">⟵</button>')
        modeB_paintings_parts.append(f'                <button class="button secondary" data-scroll="#{strip_id}" data-dir="right">⟶</button>')
        modeB_paintings_parts.append('              </div>')
        modeB_paintings_parts.append('            </div>')
        modeB_paintings_parts.append(f'            <div class="strip" id="{strip_id}">')

        for it in items:
            title = _title_or_stem(it["filename"], it.get("title", ""))
            safe_title = _e(title)
            src = f'images/{subcat}/{it["filename"]}'
            group = subcat
            modeB_paintings_parts.append('              <div class="h-item">')
            modeB_paintings_parts.append(f'                <a href="{_e(src)}" data-lightbox="{_e(group)}" data-title="{safe_title}">')
            modeB_paintings_parts.append(f'                  <img loading="lazy" src="{_e(src)}" alt="{safe_title}">')
            modeB_paintings_parts.append(f'                  <div class="hover-text">{safe_title}</div>')
            modeB_paintings_parts.append('                </a>')
            modeB_paintings_parts.append('              </div>')

        modeB_paintings_parts.append('            </div>')
        modeB_paintings_parts.append('          </div>')

    modeB_paintings_html = "\n".join(modeB_paintings_parts)

    # ---- Helpers genéricos para Crafts/Woodburnings ----
    def _grid_items_simple(items, base_folder, group_name, item_class="grid-item"):
        out = []
        for it in items:
            title = _title_or_stem(it["filename"], it.get("title", ""))
            safe_title = _e(title)
            src = f"{base_folder}/{it['filename']}"
            out.append(f'                <div class="{item_class}">')
            out.append(f'                  <a href="{_e(src)}" data-lightbox="{_e(group_name)}" data-title="{safe_title}">')
            out.append(f'                    <img loading="lazy" src="{_e(src)}" alt="{safe_title}">')
            out.append(f'                    <div class="hover-text">{safe_title}</div>')
            out.append('                  </a>')
            out.append('                </div>')
        return "\n".join(out)

    crafts_grid_html = _grid_items_simple(model["crafts"], "images/crafts", "crafts", "grid-item")
    crafts_strip_html = _grid_items_simple(model["crafts"], "images/crafts", "crafts", "h-item")
    wood_grid_html = _grid_items_simple(model["woodburnings"], "images/woodburnings", "woodburnings", "grid-item")
    wood_strip_html = _grid_items_simple(model["woodburnings"], "images/woodburnings", "woodburnings", "h-item")

    # === Template base EXACTO (del usuario) con marcadores únicos ===
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Art made by Sydney</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <!-- Lightbox2 -->
  <link href="https://cdn.jsdelivr.net/npm/lightbox2@2/dist/css/lightbox.min.css" rel="stylesheet" />

  <style>
    :root{
      --bg:#111; --bg-2:#1a1a1a; --panel:#1c1c1c; --ink:#fff; --muted:#bbb;
      --accent:#ff69b4; --line:#2f2f2f; --chip:#262626;
      --radius:12px; --maxw:1200px;
      --sticky-h:72px; /* se recalcula en JS */
    }
    *{box-sizing:border-box}
    html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:Arial,system-ui,sans-serif}

    /* ===== Franja de bienvenida (primero) ===== */
    header.hero{
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      text-align: center;
      padding: 28px 16px 26px;
    }
    .hero h1{ margin:0; font-size:2.1rem; }
    .hero .subtitle{ color: var(--muted); margin:8px 0 16px; }
    .hero-actions{ display:flex; gap:10px; justify-content:center; flex-wrap:wrap; }

    /* ===== Banner de 3 botones (se hace sticky al hacer scroll) ===== */
    .sticky-nav{
      position: sticky; top: 0; z-index: 100;
      background: var(--panel); border-bottom: 1px solid var(--line);
      display:flex; justify-content:center;
    }
    .nav{ display:flex; gap:14px; padding:12px 12px; }
    .nav a{
      display:inline-flex; align-items:center; justify-content:center;
      height:40px; padding:0 16px; border-radius:999px;
      background:#232323; border:1px solid var(--line);
      color:#fff; text-decoration:none; font-weight:600; font-size:0.95rem;
    }
    .nav a:hover{ border-color:#444; background:#262626 }

    /* Para que los anchors no queden tapados cuando la barra está pegada arriba */
    :target{ scroll-margin-top: calc(var(--sticky-h) + 10px); }

    /* ===== Panel lateral: switch de modo (pequeño) ===== */
    .side-switch{
      position:fixed; right:16px; top:50vh; transform:translateY(-50%);
      display:flex; flex-direction:column; gap:6px;
      background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:6px;
      z-index:90;
    }
    .side-switch button{
      border:1px solid var(--line); background:#222; color:#fff;
      font-size:1.25rem; line-height:1;
      padding:6px 10px; border-radius:10px; cursor:pointer;
      min-width:46px;
    }
    .side-switch button.active{ background:var(--accent); border-color:transparent; color:#000; font-weight:700 }
    .side-switch .lbl{ font-size:0.75rem; color:var(--muted); text-align:center; margin-bottom:4px }

    /* ===== Layout principal ===== */
    main{ max-width:var(--maxw); margin:0 auto; padding: 20px 16px 24px 16px; }
    .container{ max-width:var(--maxw); margin:0 auto; }
    .section{padding:28px 0; border-bottom:1px solid var(--line)}
    .section h2{margin:0 0 8px 0; border-bottom:1px solid #444; padding-bottom:10px}

    /* Botones reutilizables */
    .button{
      display:inline-flex; align-items:center; gap:8px;
      background:var(--accent); color:#000; text-decoration:none;
      border:0; border-radius:999px; padding:10px 16px; font-weight:700; cursor:pointer;
    }
    .button.secondary{ background:transparent; color:#fff; border:1px solid var(--line) }

    /* Buscador global */
    .searchbar-global{display:flex; justify-content:center; margin:8px 0 18px}
    .searchbar-global input{
      width:100%; max-width:540px; padding:10px 12px; border-radius:10px; border:1px solid var(--line);
      background:#141414; color:#fff;
    }

    /* Chips */
    .subhead{display:flex; flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between; margin-top:10px}
    .chips{display:flex; gap:8px; flex-wrap:wrap}
    .chip{background:var(--chip); border:1px solid var(--line); color:#fff; border-radius:999px; padding:6px 10px; font-size:0.9rem}

    /* Accordions (Mode A) con chevron */
    details{border:1px solid var(--line); border-radius:var(--radius); background:var(--bg-2); margin-top:16px; overflow:hidden}
    summary{list-style:none; cursor:pointer; padding:12px 14px; display:flex; align-items:center; gap:10px; position:relative}
    summary::-webkit-details-marker{display:none}
    summary h3{margin:0; color:var(--accent)}
    summary::after{
      content:"▾"; color:#fff; margin-left:auto; transition:transform .2s ease;
      font-size:1.1rem; line-height:1;
    }
    details[open] summary::after{ transform:rotate(-180deg) }
    .panel{padding:10px 12px 16px 12px; border-top:1px solid var(--line)}

    /* Grids (Mode A) */
    .grid{display:flex; flex-wrap:wrap; gap:18px; margin-top:10px}
    .grid-item{position:relative; width:calc(33.333% - 12px)}
    .grid img{width:100%; height:auto; border-radius:10px; cursor:pointer; display:block}
    .hover-text{
      position:absolute; left:0; right:0; bottom:0; padding:8px 10px;
      background:rgba(0,0,0,.7); border-radius:0 0 10px 10px; opacity:0; transition:opacity .25s
    }
    .grid-item:hover .hover-text{opacity:1}

    /* Show more (WCP) */
    .grid[data-limit] .grid-item{display:none}
    .grid[data-limit] .grid-item:nth-child(-n+12){display:block}
    .showmore-wrap{margin-top:10px; display:flex; justify-content:center}

    /* Filas horizontales (Mode B) */
    .row{margin-top:16px; border:1px solid var(--line); border-radius:var(--radius); background:var(--bg-2)}
    .row-head{display:flex; justify-content:space-between; align-items:center; padding:10px 14px; border-bottom:1px solid var(--line)}
    .row-head h3{margin:0; color:var(--accent)}
    .strip{display:flex; gap:14px; overflow-x:auto; padding:14px; scroll-snap-type:x mandatory}
    .h-item{flex:0 0 auto; scroll-snap-align:start; width:280px; position:relative}
    .h-item img{width:100%; height:auto; border-radius:10px; display:block; cursor:pointer}
    .h-item .hover-text{position:absolute; left:0; right:0; bottom:0; padding:8px 10px; background:rgba(0,0,0,.7); border-radius:0 0 10px 10px; opacity:0; transition:opacity .25s}
    .h-item:hover .hover-text{opacity:1}
    .row-ctrls{display:flex; gap:8px}
    .row-ctrls .button{padding:6px 10px; background:transparent; border:1px solid var(--line); color:#fff; border-radius:999px; cursor:pointer}

    /* Visibilidad de modos */
    body[data-mode="A"] .modeA{display:block}
    body[data-mode="A"] .modeB{display:none}
    body[data-mode="B"] .modeA{display:none}
    body[data-mode="B"] .modeB{display:block}

    /* Responsive */
    @media (max-width: 900px){ .grid-item{width:calc(50% - 9px)} }
    @media (max-width: 640px){
      .side-switch{ right:10px; top:auto; bottom:16px; transform:none; font-size:1.4rem }
      .nav a{ height:36px; padding:0 12px; font-size:0.9rem }
      .h-item{ width:240px }
      .hero h1{font-size:1.7rem}

      /* Evitar zoom al enfocar inputs en iOS */
      input, textarea, select,
      .searchbar-global input{
        font-size:16px;
        line-height:1.2;
      }
    }
    @media (max-width: 480px){ .grid-item{width:100%} }
  </style>
</head>
<body data-mode="A">
  <!-- ===== Franja de bienvenida (primero) ===== -->
  <header class="hero" aria-label="Site intro">
    <h1>Art made by Sydney</h1>
    <p class="subtitle">Welcome to my trippy world.</p>
    <div class="hero-actions">
      <a class="button secondary" href="about.html">About Me</a>
      <a class="button" href="#contact">Contact</a>
    </div>
  </header>

  <!-- ===== Banner de 3 botones (se vuelve sticky al llegar arriba) ===== -->
  <div class="sticky-nav" id="stickyNav">
    <nav class="nav" aria-label="Primary">
      <a href="#paintings">Paintings</a>
      <a href="#crafts">Crafts</a>
      <a href="#woodburnings">Woodburnings</a>
    </nav>
  </div>

  <!-- ===== Switch lateral (pequeño) ===== -->
  <aside class="side-switch" aria-label="View mode switch">
    <div class="lbl">Scroll type</div>
    <button id="btnModeA" class="active" title="Vertical">&#x2195;&#xFE0E;</button>  <!-- ↕︎ -->
    <button id="btnModeB" title="Horizontal">&#x2194;&#xFE0E;</button>               <!-- ↔︎ -->
  </aside>

  <main>
    <div class="container">
      <!-- Buscador global -->
      <div class="searchbar-global">
        <input id="searchGlobal" type="search" placeholder="Search all artworks (title/alt)..." aria-label="Search artworks across all categories" />
      </div>

      <!-- =================== PAINTINGS =================== -->
      <section class="section" id="paintings">
        <h2>Paintings</h2>

        <div class="subhead">
          <div class="chips">
            %%CHIPS%%
          </div>
        </div>

        <!-- ===== Mode A (accordions) ===== -->
        <div class="modeA" id="modeA-paintings">
%%MODEA%%
        </div>

        <!-- ===== Mode B (horizontal) ===== -->
        <div class="modeB" id="modeB-paintings">
%%MODEB%%
        </div>
      </section>

      <!-- =================== CRAFTS =================== -->
      <section class="section" id="crafts">
        <h2>Crafts</h2>

        <!-- Mode A -->
        <div class="modeA">
          <details open>
            <summary aria-label="Toggle Crafts"><h3>Gallery</h3></summary>
            <div class="panel">
              <div class="grid" id="grid-crafts">
%%CRAFTS_GRID%%
              </div>
            </div>
          </details>
        </div>

        <!-- Mode B -->
        <div class="modeB">
          <div class="row">
            <div class="row-head">
              <h3>Gallery</h3>
              <div class="row-ctrls">
                <button class="button secondary" data-scroll="#strip-crafts" data-dir="left">⟵</button>
                <button class="button secondary" data-scroll="#strip-crafts" data-dir="right">⟶</button>
              </div>
            </div>
            <div class="strip" id="strip-crafts">
%%CRAFTS_STRIP%%
            </div>
          </div>
        </div>
      </section>

      <!-- =================== WOODBURNINGS =================== -->
      <section class="section" id="woodburnings">
        <h2>Woodburnings</h2>

        <!-- Mode A -->
        <div class="modeA">
          <details open>
            <summary aria-label="Toggle Woodburnings"><h3>Gallery</h3></summary>
            <div class="panel">
              <div class="grid" id="grid-wood">
%%WOOD_GRID%%
              </div>
            </div>
          </details>
        </div>

        <!-- Mode B -->
        <div class="modeB">
          <div class="row">
            <div class="row-head">
              <h3>Gallery</h3>
              <div class="row-ctrls">
                <button class="button secondary" data-scroll="#strip-wood" data-dir="left">⟵</button>
                <button class="button secondary" data-scroll="#strip-wood" data-dir="right">⟶</button>
              </div>
            </div>
            <div class="strip" id="strip-wood">
%%WOOD_STRIP%%
            </div>
          </div>
        </div>
      </section>
    </div>
  </main>

  <footer id="contact" style="text-align:center; padding:24px 16px; background:#1c1c1c; border-top:1px solid var(--line)">
    <h2>Contact</h2>
    <p>If you're interested in any piece, send an email to: <strong>sydney25th@gmail.com</strong></p>
  </footer>

  <!-- Lightbox2 -->
  <script src="https://cdn.jsdelivr.net/npm/lightbox2@2/dist/js/lightbox.min.js"></script>

  <script>
    // Medir la altura real del banner sticky para compensar anclas
    function setStickyVar(){
      const bar = document.getElementById('stickyNav');
      if (!bar) return;
      const h = Math.ceil(bar.getBoundingClientRect().height);
      document.documentElement.style.setProperty('--sticky-h', h + 'px');
    }
    window.addEventListener('load', setStickyVar);
    window.addEventListener('resize', setStickyVar);

    // Lightbox options
    if (window.lightbox) {
      lightbox.option({ albumLabel: "Image %1 of %2", fadeDuration: 200, resizeDuration: 200 });
    }

    // Persist & toggle modes (botones laterales)
    const root = document.body;
    const btnA = document.getElementById('btnModeA');
    const btnB = document.getElementById('btnModeB');
    const saved = localStorage.getItem('aos_mode');
    if (saved === 'B'){ setMode('B'); } else { setMode('A'); }
    btnA.addEventListener('click', ()=>setMode('A'));
    btnB.addEventListener('click', ()=>setMode('B'));
    function setMode(m){
      root.setAttribute('data-mode', m);
      btnA.classList.toggle('active', m==='A');
      btnB.classList.toggle('active', m==='B');
      localStorage.setItem('aos_mode', m);
    }

    // ====== Búsqueda Global con auto-expand ======
    const q = document.getElementById('searchGlobal');
    const btnMore = document.getElementById('btn-more-wcp');
    const wcpGrid = document.getElementById('grid-wcp');

    if (q){
      q.addEventListener('input', () => {
        const term = q.value.trim().toLowerCase();
        const isSearching = term.length > 0;

        // Mostrar todos los WCP durante la búsqueda para no ocultar coincidencias
        if (wcpGrid){
          if (isSearching){
            if (!wcpGrid.dataset._hadLimit){
              wcpGrid.dataset._hadLimit = wcpGrid.hasAttribute('data-limit') ? '1' : '';
            }
            wcpGrid.removeAttribute('data-limit');
            if (btnMore) btnMore.style.display = 'none';
          } else {
            if (wcpGrid.dataset._hadLimit === '1'){
              wcpGrid.setAttribute('data-limit','');
              if (btnMore) btnMore.style.display = '';
            }
          }
        }

        // Filtrar items en Mode A
        document.querySelectorAll('.grid-item').forEach(it=>{
          const img = it.querySelector('img');
          const text = (img?.alt || '').toLowerCase();
          it.style.display = isSearching ? (text.includes(term) ? '' : 'none') : '';
        });

        // Filtrar items en Mode B
        document.querySelectorAll('.h-item').forEach(it=>{
          const img = it.querySelector('img');
          const text = (img?.alt || '').toLowerCase();
          it.style.display = isSearching ? (text.includes(term) ? '' : 'none') : '';
        });

        // Auto-expand de <details> con coincidencias visibles
        if (isSearching){
          document.querySelectorAll('.modeA details').forEach(d=>{
            const hasVisible = Array.from(d.querySelectorAll('.grid-item')).some(child => child.style.display !== 'none');
            if (hasVisible) d.open = true;
          });
        }
      });
    }

    // Show more WCP (cuando no hay búsqueda)
    if (btnMore && wcpGrid){
      btnMore.addEventListener('click', ()=>{
        wcpGrid.removeAttribute('data-limit');
        btnMore.style.display='none';
      });
    }

    // Botones de scroll horizontal (Mode B)
    document.querySelectorAll('[data-scroll]').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const sel = btn.getAttribute('data-scroll');
        const dir = btn.getAttribute('data-dir');
        const el = document.querySelector(sel);
        if (!el) return;
        const delta = el.clientWidth * 0.8 * (dir==='right' ? 1 : -1);
        el.scrollBy({left: delta, behavior:'smooth'});
      });
    });
  </script>
</body>
</html>"""

    html_out = (template
                .replace("%%CHIPS%%", chips_block)
                .replace("%%MODEA%%", modeA_paintings_html)
                .replace("%%MODEB%%", modeB_paintings_html)
                .replace("%%CRAFTS_GRID%%", crafts_grid_html)
                .replace("%%CRAFTS_STRIP%%", crafts_strip_html)
                .replace("%%WOOD_GRID%%", wood_grid_html)
                .replace("%%WOOD_STRIP%%", wood_strip_html))
    return html_out


def main():
    # Rutas relativas al script (TOOLS/)
    script_path = Path(__file__).resolve()
    tools_dir = script_path.parent
    csv_path = tools_dir.parent / "images" / "imagesManifest.csv"
    out_html = tools_dir / "index.html"

    print(f"📄 Leyendo manifest: {csv_path}")
    model = read_manifest(csv_path)

    print("🧩 Generando HTML con template A/B…")
    html_text = build_html(model)

    out_html.write_text(html_text, encoding="utf-8")

    total_imgs = sum(len(v) for v in model["paintings"].values()) + len(model["crafts"]) + len(model["woodburnings"])
    print(f"✅ index.html generado con {total_imgs} imágenes publicadas")
    print(f"📂 Guardado en: {out_html.resolve()}")


if __name__ == "__main__":
    main()
