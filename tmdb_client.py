import os
import json
import time
import requests
import locale
from datetime import datetime
from ulauncher.api.client.Extension import Extension
from utils import CACHE_DIR, load_translations, get_flag_emoji

CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")

class TMDB(Extension):
    def __init__(self, keyword_listener, item_listener):
        super().__init__()
        from main import KeywordQueryEventListener, ItemEnterEventListener
        self.subscribe(keyword_listener[0], keyword_listener[1])
        self.subscribe(item_listener[0], item_listener[1])
        
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
            with open(CACHE_FILE, "w", encoding="utf-8") as f: 
                json.dump(self.cache, f, ensure_ascii=False)
        except: pass

    def get_full_details(self, movie_id):
        api_key = self.preferences.get("api_key")
        if not api_key: return None
        cache_key = f"full_{movie_id}_{self.user_country}"
        if cache_key in self.cache:
            data = self.cache[cache_key]
            try:
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
