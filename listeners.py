import os
import time
import html
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction

from utils import DEFAULT_ICON, CACHE_DIR, normalize_text, fetch_poster
from text_utils import clean_text, format_movie_details
from suggestion_engine import render_suggestion_logic

WORKER_POOL = ThreadPoolExecutor(max_workers=15)

def full_unescape(text):
    """Aplica html.unescape repetidamente até estabilizar e substitui &amp; por &."""
    if not text:
        return text
    prev = None
    current = text
    while prev != current:
        prev = current
        current = html.unescape(current)
    return current.replace('&amp;', '&')

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = (event.get_argument() or "").lower().strip()
        api_key = extension.preferences.get("api_key")

        if not api_key:
            return RenderResultListAction([ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("api_key_missing", "API Key missing"), on_enter=DoNothingAction())])

        suggest_kw = extension.preferences.get("suggest_kw", "suggest")
        if query.startswith(suggest_kw):
            parts = query.split()
            param = normalize_text(parts[1]) if len(parts) > 1 else None
            if param:
                if param in [normalize_text(s) for s in extension.i18n.get("random_synonyms", "random").split(",")]:
                    return render_suggestion_logic(extension, None)
                for key, gid in extension.genre_map.items():
                    genre_display_name = extension.i18n.get(f"genre_{key}", key)
                    if param == normalize_text(genre_display_name):
                        return render_suggestion_logic(extension, genre_display_name.capitalize(), gid)
            return RenderResultListAction([ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("suggestion_title", "Suggestion"), description=extension.i18n.get("suggestion_instructions", ""), on_enter=DoNothingAction())])

        try:
            if not query:
                # Carregamento do Trending com validação rigorosa
                results = extension.cache.get("trending_data", [])
                if not results or (time.time() - extension.cache.get("trending_cached_at", 0) > 21600):
                    r = extension.session.get(f"{extension.base_url}/trending/movie/day?api_key={api_key}&language={extension.system_language}", timeout=3)
                    results = r.json().get("results", [])
                    extension.cache.update({"trending_data": results, "trending_cached_at": time.time()})
                return self.render_movie_list(extension, results, mode="trending")

            r = extension.session.get(f"{extension.base_url}/search/movie?api_key={api_key}&query={quote_plus(query)}&language={extension.system_language}", timeout=2)
            raw = [m for m in r.json().get("results", []) if m.get("poster_path")]
            return self.render_movie_list(extension, raw, mode="search")
        except:
            offline = [v for k, v in extension.cache.items() if k.startswith("full_") and query in v.get("title", "").lower()]
            return self.render_movie_list(extension, offline[:5], mode="search")

    def render_movie_list(self, extension, movies, mode="search"):
        items = []
        for m in movies:
            mid = m["id"]
            p = os.path.join(CACHE_DIR, f"{mid}_thumb.png")
            info = extension.cache.get(f"full_{mid}_{extension.user_country}")

            # REGRA: Nunca mostrar sem poster ou sem detalhes
            if not info or not os.path.exists(p):
                WORKER_POOL.submit(extension.get_full_details, mid)
                WORKER_POOL.submit(fetch_poster, extension.session, extension.img_base, mid, m.get("poster_path"))
                continue

            # Para o modo trending, aplicamos um filtro radical:
            # Se qualquer campo textual (título, diretor, gêneros, nota) contiver "&" (ampersand),
            # o filme é ignorado. Isso evita qualquer problema de exibição.
            if mode == "trending":
                title_raw = info.get("title", m.get("title", ""))
                director_raw = info.get("director", "")
                genres_raw = info.get("genres", "")
                rating_raw = info.get("rating", "")
                # Verifica tanto "&" quanto "&amp;" (por segurança)
                if any("&" in field for field in [title_raw, director_raw, genres_raw, rating_raw] if field):
                    continue

            # Aplica desescapamento completo a todos os campos
            title_to_show = full_unescape(clean_text(info.get("title", m.get("title", ""))))
            director_to_show = full_unescape(clean_text(info.get("director", "")))
            genres_to_show = full_unescape(info.get("genres", ""))
            rating_to_show = full_unescape(info.get("rating", ""))

            year = info.get("year", "N/A")
            if mode == "trending":
                desc = f"⭐ {rating_to_show} | {genres_to_show} • 🔥 {extension.i18n.get('trending', 'em alta')}"
            else:
                desc = f"{year} • {director_to_show}"

            name = f"{title_to_show}, {year}" if mode == "trending" else title_to_show

            items.append(ExtensionResultItem(
                icon=p, 
                name=name, 
                description=desc, 
                on_enter=ExtensionCustomAction({"action": "details", "id": mid}, keep_app_open=True)
            ))
            if len(items) >= 5: break
            
        return RenderResultListAction(items or [ExtensionResultItem(icon=DEFAULT_ICON, name=extension.i18n.get("continue_typing", "Buscando..."), on_enter=DoNothingAction())])

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data() or {}
        if data.get("action") == "details":
            info = extension.get_full_details(data["id"])
            if not info: return DoNothingAction()
            p = os.path.join(CACHE_DIR, f"{data['id']}_thumb.png")
            
            title = full_unescape(clean_text(info['title']))
            director = full_unescape(clean_text(info['director']))
            details_desc = full_unescape(format_movie_details(extension, info))

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=p if os.path.exists(p) else DEFAULT_ICON,
                    name=f"{title}\n{info['year']}\n{director}",
                    description=details_desc,
                    on_enter=OpenUrlAction(f"https://www.themoviedb.org/movie/{data['id']}")
                )
            ])
