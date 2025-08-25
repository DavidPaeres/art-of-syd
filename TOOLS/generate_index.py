#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_index.py
-----------------
Genera un index.html a partir de images/imagesManifest.csv.

CSV esperado (mínimo):
- columnas: filename, categoria, subcategoria, publish
- publish == "no" -> ignorar fila (insensible a mayúsculas)
- categoria es UNA letra MAYÚSCULA:
    P -> Paintings
    C -> Crafts
    W -> Woodburnings

Reglas de rutas:
- P (Paintings):      images/<subcategoria>/<filename>
- C (Crafts):         images/crafts/<filename>
- W (Woodburnings):   images/woodburnings/<filename>

Salida:
- Escribe index.html JUNTO AL SCRIPT (TOOLS/index.html)
- Imprime la ruta absoluta donde se guardó
"""

from pathlib import Path
import csv
from collections import OrderedDict
import sys

# Mapeo de categoría en el CSV (MAYÚSCULAS) -> nombre lógico
CATEGORY_MAP = {
    "P": "paintings",
    "C": "crafts",
    "W": "woodburnings",
}

def slugify(text: str) -> str:
    """Convierte texto a un id seguro para HTML (simple, sin dependencias)."""
    return "".join((ch.lower() if ch.isalnum() else "-") for ch in (text or "").strip()).strip("-") or "section"

def read_manifest(csv_path: Path):
    """
    Lee el CSV y devuelve un modelo de datos:
    {
      "paintings": OrderedDict({ subcat: [filename, ...], ... }),
      "crafts": [filename, ...],
      "woodburnings": [filename, ...]
    }

    Pasos:
    1) Verifica archivo y columnas mínimas.
    2) Filtra filas con publish == "no" (cualquier mayúsc./minúsc.).
    3) Interpreta categoria como UNA letra MAYÚSCULA (P/C/W).
    4) Para P, agrupa por subcategoria (en orden de aparición).
    5) Para C y W, acumula listas planas (en orden de aparición).
    """
    if not csv_path.exists():
        print(f"❌ No se encontró el manifest: {csv_path}")
        sys.exit(1)

    paintings = OrderedDict()  # subcat -> [filenames]
    crafts = []
    woodburnings = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Normalizamos encabezados a minúsculas (tolerante a variantes)
        reader.fieldnames = [h.lower().strip() for h in reader.fieldnames]

        required = {"filename", "categoria", "subcategoria", "publish"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"❌ Faltan columnas requeridas: {missing}")
            sys.exit(1)

        for row in reader:
            # 1) Filtro publish == "no"
            if (row.get("publish") or "").strip().lower() == "no":
                continue

            filename = (row.get("filename") or "").strip()
            cat_code = (row.get("categoria") or "").strip().upper()  # MAYÚSCULA
            subcat   = (row.get("subcategoria") or "").strip()

            if not filename or cat_code not in CATEGORY_MAP:
                # Si falta filename o la categoría no es P/C/W, saltamos
                continue

            if cat_code == "P":
                # Paintings: subcategoría define la carpeta dentro de images/
                sub_key = subcat if subcat else "general"
                # Normalicemos el nombre de carpeta a minúsculas por seguridad en rutas
                sub_key_folder = sub_key.lower()
                if sub_key_folder not in paintings:
                    paintings[sub_key_folder] = []
                paintings[sub_key_folder].append(filename)

            elif cat_code == "C":
                crafts.append(filename)

            elif cat_code == "W":
                woodburnings.append(filename)

    return {
        "paintings": paintings,
        "crafts": crafts,
        "woodburnings": woodburnings
    }

def build_html(model):
    """
    Construye el HTML final con:
    - Head/estilos y header estáticos.
    - Bloque AUTOGENERADO con 3 secciones:
        Paintings (dividido por subcategorías),
        Crafts,
        Woodburnings.
    - Footer/scripts.
    """
    head = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Art made by Sydney</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://cdn.jsdelivr.net/npm/lightbox2@2/dist/css/lightbox.min.css" rel="stylesheet">
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #111; color: #fff; }
    header { text-align: center; padding: 40px 20px; background: #222; }
    h1 { font-size: 2.5em; }
    p.subtitle { font-size: 1.2em; color: #ccc; }
    nav { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-top: 12px; }
    nav a { color: #ff69b4; text-decoration: none; font-size: 0.95em; }
    nav a:hover { text-decoration: underline; }
    .gallery-section { padding: 40px 20px; }
    h2 { border-bottom: 1px solid #444; padding-bottom: 10px; }
    h3 { color: #ff69b4; margin-top: 30px; }
    .grid { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px; }
    .grid-item { position: relative; width: calc(33.333% - 20px); }
    .grid img { width: 100%; height: auto; border-radius: 8px; cursor: pointer; }
    .hover-text {
      position: absolute; bottom: 0; left: 0; right: 0;
      background: rgba(0, 0, 0, 0.7); color: #fff; padding: 10px;
      opacity: 0; transition: opacity 0.3s ease-in-out;
      border-radius: 0 0 8px 8px;
    }
    .grid-item:hover .hover-text { opacity: 1; }
    footer { text-align: center; padding: 20px; background: #222; margin-top: 40px; }
    a.button { display: inline-block; padding: 10px 20px; background: #ff69b4; color: #fff; text-decoration: none; border-radius: 5px; margin-top: 20px; }
    @media (max-width: 900px) { .grid-item { width: calc(50% - 20px); } }
    @media (max-width: 600px) { .grid-item { width: 100%; } }
  </style>
</head>
<body>
<header>
  <h1>Art made by Sydney</h1>
  <p class="subtitle">Welcome to my trippy world.</p>
  <a class="button" href="#contact">Contact</a>
  <nav>
    <a href="#paintings">Paintings</a>
    <a href="#crafts">Crafts</a>
    <a href="#woodburnings">Woodburnings</a>
  </nav>
</header>
"""
    parts = []
    parts.append("<!-- BEGIN AUTO-GENERATED -->")
    parts.append("<!-- Generado por TOOLS/generate_index.py usando images/imagesManifest.csv -->")
    parts.append("<!-- publish=='no' se excluye; secciones: Paintings (subcats), Crafts, Woodburnings -->")

    # ===== Paintings (con subcategorías) =====
    parts.append('<section class="gallery-section" id="paintings">')
    parts.append('  <h2>Paintings</h2>')
    for subcat, files in model["paintings"].items():
        sub_id = slugify(f"paintings-{subcat}")
        parts.append(f'  <h3 id="{sub_id}">{subcat}</h3>')
        parts.append('  <div class="grid">')
        for f in files:
            alt = Path(f).stem
            src = f"images/{subcat}/{f}"
            parts.append('    <div class="grid-item">')
            parts.append(f'      <a href="{src}" data-lightbox="{subcat}" data-title="{alt}">')
            parts.append(f'        <img src="{src}" alt="{alt}">')
            parts.append(f'        <div class="hover-text">{alt}</div>')
            parts.append('      </a>')
            parts.append('    </div>')
        parts.append('  </div>')
    parts.append('</section>')

    # ===== Crafts =====
    parts.append('<section class="gallery-section" id="crafts">')
    parts.append('  <h2>Crafts</h2>')
    parts.append('  <div class="grid">')
    for f in model["crafts"]:
        alt = Path(f).stem
        src = f"images/crafts/{f}"
        parts.append('    <div class="grid-item">')
        parts.append(f'      <a href="{src}" data-lightbox="crafts" data-title="{alt}">')
        parts.append(f'        <img src="{src}" alt="{alt}">')
        parts.append(f'        <div class="hover-text">{alt}</div>')
        parts.append('      </a>')
        parts.append('    </div>')
    parts.append('  </div>')
    parts.append('</section>')

    # ===== Woodburnings =====
    parts.append('<section class="gallery-section" id="woodburnings">')
    parts.append('  <h2>Woodburnings</h2>')
    parts.append('  <div class="grid">')
    for f in model["woodburnings"]:
        alt = Path(f).stem
        src = f"images/woodburnings/{f}"
        parts.append('    <div class="grid-item">')
        parts.append(f'      <a href="{src}" data-lightbox="woodburnings" data-title="{alt}">')
        parts.append(f'        <img src="{src}" alt="{alt}">')
        parts.append(f'        <div class="hover-text">{alt}</div>')
        parts.append('      </a>')
        parts.append('    </div>')
    parts.append('  </div>')
    parts.append('</section>')

    parts.append("<!-- END AUTO-GENERATED -->")

    footer = """
<footer id="contact">
  <h2>Contact</h2>
  <p>If you're interested in any piece, send an email to: <strong>artofsyd@gmail.com</strong></p>
</footer>
<script src="https://cdn.jsdelivr.net/npm/lightbox2@2/dist/js/lightbox.min.js"></script>
</body>
</html>
"""
    return head + "\n".join(parts) + footer

def main():
    """
    Flujo:
    - Determina rutas relativas a este script (TOOLS/).
    - Lee el CSV en images/imagesManifest.csv.
    - Construye el HTML y lo guarda en TOOLS/index.html.
    - Imprime ruta absoluta del archivo generado.
    """
    script_path = Path(__file__).resolve()
    tools_dir   = script_path.parent
    csv_path    = tools_dir.parent / "images" / "imagesManifest.csv"
    out_html    = tools_dir / "index.html"   # Guardar JUNTO AL SCRIPT

    print(f"📄 Leyendo manifest: {csv_path}")
    model = read_manifest(csv_path)

    print("🧩 Generando HTML…")
    html = build_html(model)

    out_html.write_text(html, encoding="utf-8")

    total_imgs = (
        sum(len(v) for v in model["paintings"].values())
        + len(model["crafts"])
        + len(model["woodburnings"])
    )

    print(f"✅ index.html generado con {total_imgs} imágenes publicadas")
    print(f"📂 Guardado en: {out_html.resolve()}")

if __name__ == "__main__":
    main()
