"""
generate_thumbs.py
Creates 600px-max JPEG thumbnails for the artofsyd gallery.
Input:  images/{category}/*.{jpg,jpeg,png}
Output: images/thumbs/{category}/*.jpg

Run from the website/ directory:
  python generate_thumbs.py
"""
import os
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
THUMBS_DIR = os.path.join(IMAGES_DIR, "thumbs")
MAX_SIZE   = 600
QUALITY    = 80
SKIP_DIRS  = {"thumbs"}


def run():
    for cat in sorted(os.listdir(IMAGES_DIR)):
        cat_path = os.path.join(IMAGES_DIR, cat)
        if not os.path.isdir(cat_path) or cat in SKIP_DIRS:
            continue
        out_dir = os.path.join(THUMBS_DIR, cat)
        os.makedirs(out_dir, exist_ok=True)
        for fname in sorted(os.listdir(cat_path)):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            src = os.path.join(cat_path, fname)
            out_name = os.path.splitext(fname)[0] + ".jpg"
            dst = os.path.join(out_dir, out_name)
            if os.path.exists(dst):
                print(f"  skip  {cat}/{out_name}")
                continue
            try:
                img = Image.open(src).convert("RGB")
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
                img.save(dst, "JPEG", quality=QUALITY, optimize=True)
                print(f"  OK    {cat}/{out_name}")
            except Exception as e:
                print(f"  ERROR {src}: {e}")


if __name__ == "__main__":
    run()
    print("Done.")
