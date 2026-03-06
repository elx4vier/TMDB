import logging
import requests
import json
import os
import io
import textwrap
import random
import time
import locale
import unicodedata
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps, ImageDraw

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "ulauncher-movie-search")
CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")
WORKER_POOL = ThreadPoolExecutor(max_workers=15)
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

class TMDB(Extension):  # Nome alterado para TMDB
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.session = requests.Session()
        self.base_url = "https://api.themoviedb.org/3"
        self.img_base = "https://image.tmdb.org/t/p/w300"
        sys_locale = (locale.getdefaultlocale()[0] or "en_US")
        self.lang_code = sys_locale.split("_")[0]
        self.system_language = sys_locale.replace("_", "-")
        self.i18n = load_translations(self.lang_code)
        self.cache = self._load_cache()
        self.user_country = self.cache.get("stored_country") or "US"
        if "recent_suggestions" not in self.cache: self.cache["recent_suggestions"] = []
        
        self.genre_map = {
            "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
            "crime": 80, "documentary": 99, "drama": 18, "science": 878, 
            "romance": 10749, "thriller": 53, "horror": 27
        }

    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f: return json.load(f)
            except: pass
        return {}

    def save_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f: json.dump(self.cache, f, ensure_ascii=False)
        except: pass

    def get_full_details(self, movie_id):
        api_key = self.preferences.get("api_key")
        if not api_key: return None
        cache_key = f"full_{movie_id}_{self.user_country}"
        if cache_key in self.cache:
            data = self.cache[cache_key]
            try:
                # Cache persistente para filmes antigos conforme instrução [2026-03-04]
                if int(data.get("year", 0)) < datetime.now().year: return data
                if time.time() - data.get("cached_at", 0) < 604800: return data
            except: pass
        try:
            url = f"{self.base_url}/movie/{movie_id}?api_key={api_key}&language={self.system_language}&append_to_response=watch/providers,credits"
            data = self.session.get(url, timeout=4).json()
            director = next((m["name"] for m in data.get("credits", {}).get("crew", []) if m["job"] == "Director"), None)
            cast_list = [m["name"] for m in data.get("credits", {}).get("cast", [])[:5]]
            ov = data.get("overview", "").strip()
            if not director or not cast_list or not ov: return None
            info = {
                "id": str(movie_id), "title": data.get("title"), "year": str(data.get("release_date", ""))[:4],
                "director": director, "rating": f"{data.get('vote_average', 0):.1f}",
                "duration": f"{data.get('runtime', 0)//60}h {data.get('runtime', 0)%60}m",
                "genres": ", ".join([g["name"] for g in data.get("genres", [])[:2]]),
                "country": f"{data.get('production_countries', [{}])[0].get('iso_3166_1', '')} {get_flag_emoji(data.get('production_countries', [{}])[0].get('iso_3166_1', ''))}",
                "overview": ov, "cast": ", ".join(cast_list),
                "streaming": ", ".join([p["provider_name"] for p in data.get("watch/providers", {}).get("results", {}).get(self.user_country, {}).get("flatrate", [])]) or None,
                "cached_at": time.time(),
            }
            self.cache[cache_key] = info
            self.save_cache(); return info
        except: return None

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = (event.get_argument() or "").lower().strip()
        api_key = extension.preferences.get("api_key")
        if not api_key:
            return RenderResultListAction([ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("api_key_missing", "API Key missing"), description=extension.i18n.get("api_key_desc", ""), on_enter=DoNothingAction())])
        
        suggest_kw = extension.preferences.get("suggest_kw", "suggest")
        if query.startswith(suggest_kw):
            parts = query.split()
            param = normalize_text(parts[1]) if len(parts) > 1 else None
            
            if param:
                random_cmds = [normalize_text(s) for s in extension.i18n.get("random_synonyms", "random").split(",")]
                if param in random_cmds:
                    return render_suggestion_logic(extension, None)

                for key, gid in extension.genre_map.items():
                    translated_genre = extension.i18n.get(f"genre_{key}", key)
                    if param == normalize_text(translated_genre):
                        # Garante a exibição correta com acento (Ex: Ação) conforme [2026-03-06]
                        return render_suggestion_logic(extension, translated_genre.capitalize(), gid)

            return RenderResultListAction([ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("suggestion_title", "Suggestion"), description=extension.i18n.get("suggestion_instructions", ""), on_enter=DoNothingAction())])

        try:
            if not query:
                cache_time = extension.cache.get("trending_cached_at", 0)
                if time.time() - cache_time > 21600: extension.cache["trending_data"] = []
                results = extension.cache.get("trending_data", [])
                if not results:
                    r = extension.session.get(f"{extension.base_url}/trending/movie/day?api_key={api_key}&language={extension.system_language}", timeout=3)
                    results = r.json().get("results", [])
                    extension.cache["trending_data"] = results
                    extension.cache["trending_cached_at"] = time.time()
                return self.render_movie_list(extension, results, mode="trending")
            
            r = extension.session.get(f"{extension.base_url}/search/movie?api_key={api_key}&query={query.replace(' ','+')}&language={extension.system_language}", timeout=2)
            raw = [m for m in r.json().get("results", []) if m.get("poster_path")]
            if not raw: return RenderResultListAction([ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("no_results", "No results").format(query=query), on_enter=DoNothingAction())])
            return self.render_movie_list(extension, raw, mode="search")
        except:
            offline_items = []
            for key, info in extension.cache.items():
                if key.startswith("full_") and isinstance(info, dict) and query in info.get("title", "").lower():
                    p = os.path.join(CACHE_DIR, f"{info['id']}_thumb.png")
                    offline_items.append(ExtensionResultItem(icon=p if os.path.exists(p) else DEFAULT_ICON, name=info["title"], description=f"{info['year']} • {info['director']}", on_enter=ExtensionCustomAction({"action": "details", "id": info["id"]}, keep_app_open=True)))
            if not offline_items: return RenderResultListAction([ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("offline", "Offline"), description=extension.i18n.get("check_connection", ""), on_enter=DoNothingAction())])
            return RenderResultListAction(offline_items[:5])

    def render_movie_list(self, extension, movies, mode="search"):
        items = []
        for m in movies:
            mid = m["id"]
            info = extension.cache.get(f"full_{mid}_{extension.user_country}")
            if not info: WORKER_POOL.submit(extension.get_full_details, mid); continue
            p = os.path.join(CACHE_DIR, f"{mid}_thumb.png")
            if not os.path.exists(p): WORKER_POOL.submit(fetch_poster, extension.session, extension.img_base, mid, m.get("poster_path"))
            if mode == "search" and not os.path.exists(p): continue
            name = f"{info['title']}, {info['year']}" if mode == "trending" else info["title"]
            desc = f"⭐ {info['rating']} | {info['genres']} • 🔥 {extension.i18n.get('trending', 'trending')}" if mode == "trending" else f"{info['year']} • {info['director']}"
            items.append(ExtensionResultItem(icon=p if os.path.exists(p) else DEFAULT_ICON, name=name, description=desc, on_enter=ExtensionCustomAction({"action": "details", "id": mid}, keep_app_open=True)))
            if len(items) >= 5: break
        return RenderResultListAction(items or [ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("continue_typing", "Continue typing..."), on_enter=DoNothingAction())])

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data() or {}
        if data.get("action") == "details":
            info = extension.get_full_details(data["id"])
            if not info: return DoNothingAction()
            p = os.path.join(CACHE_DIR, f"{data['id']}_thumb.png")
            body = f"⭐ {info['rating']} | {info['duration']} | {info['genres']} | {info['country']}\n\n{textwrap.fill(info['overview'], 60)}\n\n{textwrap.fill(extension.i18n.get('cast', 'Cast') + ': ' + info['cast'], 60)}"
            if info["streaming"]: body += f"\n\n{textwrap.fill('📺 ' + extension.i18n.get('available_on', 'Available on') + ': ' + info['streaming'], 60)}"
            return RenderResultListAction([ExtensionResultItem(icon=p if os.path.exists(p) else DEFAULT_ICON, name=f"{info['title']}\n{info['year']}\n{info['director']}", description=body, on_enter=OpenUrlAction(f"https://www.themoviedb.org/movie/{data['id']}"))])

def render_suggestion_logic(extension, label, gid=None):
    api_key = extension.preferences.get("api_key")
    recent = extension.cache.get("recent_suggestions", [])
    try:
        url = f"{extension.base_url}/discover/movie?api_key={api_key}&language={extension.system_language}&page={random.randint(1,10)}"
        if gid: url += f"&with_genres={gid}"
        movies = [m for m in extension.session.get(url, timeout=3).json().get("results", []) if m["id"] not in recent]
        for m in random.sample(movies, len(movies)):
            info = extension.get_full_details(m["id"])
            if info:
                det = extension.session.get(f"{extension.base_url}/movie/{m['id']}?api_key={api_key}", timeout=2).json()
                if det.get("runtime", 0) < 70: continue
                recent.append(m["id"]); extension.cache["recent_suggestions"] = recent[-20:]; extension.save_cache()
                p = fetch_poster(extension.session, extension.img_base, m["id"], m.get("poster_path"))
                head = extension.i18n.get("suggestion_header_genre", "Suggestion for {genre}:").format(genre=label) if label else extension.i18n.get("suggestion_header", "Here is a suggestion:")
                details = f"\n{info['title']}, {info['year']}\n{info['director']}\n⭐ {info['rating']} | {info['duration']} | {info['genres']} | {info['country']}\n\n{textwrap.fill(info['overview'],60)}\n\n{textwrap.fill(extension.i18n.get('cast', 'Cast') + ': ' + info['cast'],60)}"
                if info["streaming"]: details += f"\n\n{textwrap.fill('📺 ' + extension.i18n.get('available_on', 'Available on') + ': ' + info['streaming'],60)}"
                return RenderResultListAction([ExtensionResultItem(icon=p if p else DEFAULT_ICON, name=head, description=details, on_enter=OpenUrlAction(f"https://www.themoviedb.org/movie/{m['id']}"))])
    except:
        offline_pool = [v for k, v in extension.cache.items() if k.startswith("full_") and v["id"] not in recent]
        if offline_pool:
            info = random.choice(offline_pool)
            recent.append(info["id"]); extension.cache["recent_suggestions"] = recent[-20:]; extension.save_cache()
            p = os.path.join(CACHE_DIR, f"{info['id']}_thumb.png")
            return RenderResultListAction([ExtensionResultItem(icon=p if os.path.exists(p) else DEFAULT_ICON, name=extension.i18n.get("suggestion_header", "Suggestion:"), description=f"\n{info['title']}, {info['year']}\n{info['director']}\n\n{textwrap.fill(info['overview'],60)}", on_enter=DoNothingAction())])
    return RenderResultListAction([ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("continue_typing", "Keep typing..."), on_enter=DoNothingAction())])

if __name__ == "__main__":
    TMDB().run()  # Chamada da classe atualizada
