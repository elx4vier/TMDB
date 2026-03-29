from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from tmdb_client import TMDB
from listeners import KeywordQueryEventListener, ItemEnterEventListener

if __name__ == "__main__":
    TMDB(
        keyword_listener=(KeywordQueryEvent, KeywordQueryEventListener()),
        item_listener=(ItemEnterEvent, ItemEnterEventListener())
    ).run()
