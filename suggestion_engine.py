import random
import os
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from utils import DEFAULT_ICON, CACHE_DIR, fetch_poster
from text_utils import clean_text, format_movie_details

def render_suggestion_logic(extension, label, gid=None):
    api_key = extension.preferences.get("api_key")
    recent = extension.cache.get("recent_suggestions", [])

    try:
        # Tenta pegar uma página aleatória entre 1 e 10 para variar as sugestões
        url = f"{extension.base_url}/discover/movie?api_key={api_key}&language={extension.system_language}&page={random.randint(1,10)}"
        if gid: url += f"&with_genres={gid}"

        r = extension.session.get(url, timeout=3).json()
        movies = [m for m in r.get("results", []) if m["id"] not in recent]

        # Sorteia da lista de filmes retornados
        for m in random.sample(movies, len(movies)):
            info = extension.get_full_details(m["id"])
            if info:
                # Validação de runtime para evitar curtas ou documentários muito breves nas sugestões
                det = extension.session.get(f"{extension.base_url}/movie/{m['id']}?api_key={api_key}", timeout=2).json()
                if det.get("runtime", 0) < 70: continue

                recent.append(m["id"])
                extension.cache["recent_suggestions"] = recent[-20:]
                extension.save_cache()

                p = fetch_poster(extension.session, extension.img_base, m["id"], m.get("poster_path"))
                
                # Tradução do cabeçalho
                head = extension.i18n.get("suggestion_header_genre", "Suggestion for {genre}:").format(genre=label) if label else extension.i18n.get("suggestion_header", "Here is a suggestion:")
                
                # --- LIMPEZA DE TEXTO AQUI ---
                title_clean = clean_text(info.get('title', 'Unknown'))
                details_clean = format_movie_details(extension, info)

                return RenderResultListAction([
                    ExtensionResultItem(
                        icon=p if p else DEFAULT_ICON,
                        name=head,
                        description=f"\n{title_clean}, {info.get('year', 'N/A')}\n" + details_clean,
                        on_enter=OpenUrlAction(f"https://www.themoviedb.org/movie/{m['id']}")
                    )
                ])
    except Exception:
        # Fallback para o que já estiver no cache (Modo Offline)
        offline_pool = [v for k, v in extension.cache.items() if k.startswith("full_") and v.get("id") not in recent]
        if offline_pool:
            info = random.choice(offline_pool)
            p = os.path.join(CACHE_DIR, f"{info['id']}_thumb.png")
            
            # Limpeza no modo offline também por segurança
            title_off = clean_text(info.get('title', 'Unknown'))
            overview_off = clean_text(info.get('overview', ''))[:150]

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=p if os.path.exists(p) else DEFAULT_ICON,
                    name=extension.i18n.get("suggestion_header", "Suggestion:"),
                    description=f"\n{title_off}, {info.get('year', 'N/A')}\n{info.get('director', '')}\n\n{overview_off}...",
                    on_enter=DoNothingAction()
                )
            ])

    return RenderResultListAction([
        ExtensionResultItem(
            icon=DEFAULT_ICON, 
            name=extension.i18n.get("continue_typing", "Keep typing..."), 
            on_enter=DoNothingAction()
        )
    ])
