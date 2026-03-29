import os
import json
import logging
import unicodedata
import io
import requests
from PIL import Image, ImageOps, ImageDraw

logger = logging.getLogger(__name__)
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "ulauncher-movie-search")
DEFAULT_ICON = "images/icon.png"

def load_translations(lang_code):
    base_path = os.path.dirname(__file__)
    paths_to_try = [
        os.path.join(base_path, 'translations', f'{lang_code}.json'),
        os.path.join(base_path, 'translations', 'en.json')
    ]
    for path in paths_to_try:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {k: v['message'] for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading translation at {path}: {e}")
    return {}

def normalize_text(text):
    if not text: return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower().strip()

def get_flag_emoji(country_code):
    if not country_code: return ""
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def fetch_poster(session, img_base, movie_id, path):
    local_path = os.path.join(CACHE_DIR, f"{movie_id}_thumb.png")
    if os.path.exists(local_path): return local_path
    if not path: return None
    try:
        r = session.get(f"{img_base}{path}", timeout=5)
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            img = ImageOps.fit(img, (120, 180), Image.LANCZOS)
            mask = Image.new("L", (120, 180), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, 120, 180), radius=6, fill=255)
            img.putalpha(mask)
            img.save(local_path, "PNG")
            return local_path
    except: pass
    return None
