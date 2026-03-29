import html
import textwrap

def clean_text(text):
    if not text:
        return ""
    # Desfaz escape de HTML (ex: &amp; -> &)
    text = html.unescape(text)
    # Força substituição manual de casos teimosos
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    return text.strip()

def format_movie_details(extension, info):
    body = (
        f"⭐ {info['rating']} | {info['duration']} | {info['genres']} | {info['country']}\n\n"
        f"{textwrap.fill(info['overview'], 60)}\n\n"
        f"{textwrap.fill(extension.i18n.get('cast', 'Cast') + ': ' + info['cast'], 60)}"
    )
    if info.get("streaming"):
        body += f"\n\n{textwrap.fill('📺 ' + extension.i18n.get('available_on', 'Available on') + ': ' + info['streaming'], 60)}"
    return body
