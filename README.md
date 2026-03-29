# 🎬 TMDB Movie Search for Ulauncher

A high-performance extension for Ulauncher that allows you to browse, search, and discover movies using The Movie Database (TMDB) API.

## ✨ Features

- **Lightning Fast Search**: Find any movie instantly as you type.
- **Trending Movies**: See what's popular right now by triggering the extension with no query.
- **Smart Suggestions**: Get random movie recommendations or filter them by genre.
- **Detailed Insights**: View ratings (⭐), runtime, genres, cast, and director.
- **Streaming Availability**: Check where to watch movies (Flatrate) based on your region.
- **Offline Support**: Access previously cached results even without an internet connection.

## 🚀 Installation

1. Open Ulauncher Preferences.
2. Go to **Extensions > Add extension**.
3. Paste the repository URL:  
   `https://github.com/elx4vier/TMDB`

## 🔑 Configuration

To use this extension, you must provide your own TMDB API Key:

1. Create an account at [TheMovieDB.org](https://www.themoviedb.org/).
2. Go to **Settings > API**.
3. Generate a personal API Key (v3 auth).
4. In the Ulauncher extension settings, paste your key into the **TMDB API Key** field.

## 🛠️ Usage

| Command                  | Action |
|--------------------------|--------|
| `m <query>`              | Search for a specific movie title |
| `m` (no query)           | Show currently trending movies |
| `m sugest random`          | Get a completely random movie suggestion (minimum 70 min runtime) |
| `m sugest <genre>`         | Get a suggestion from a specific genre (e.g. `sugest drama`, `sugest horror`) |

**Supported Genres:** Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Science Fiction, Romance, Thriller, and Horror.

## ⚙️ How to Customize Trigger Keywords

You can easily change the default trigger keywords (`m` and `sugest`) to whatever you prefer:

1. Open Ulauncher Preferences.
2. Go to the **TMDB Movie Search** extension settings.
3. Find the following fields:
   - **TMDB Keyword** (default: `m`)
   - **Movie Suggestion** (default: `sugest`)
4. Change them to your preferred keywords (e.g. `movie`, `film`, `rec`, `suggest`, etc.).
5. Save the settings.

**Examples after customization:**
- `movie inception`
- `film` (to see trending)
- `rec random`
- `rec horror`

> **Tip**: Choose short and easy-to-type triggers for the best experience.

## ⚙️ Technical Details

- **Debounce**: 0.1s query debounce to optimize API calls.
- **Image Processing**: Automatically fetches posters, resizes them to 120x180, and applies rounded corners for a native look.
- **Data Reliability**: Implements deep HTML unescaping to ensure titles and descriptions are displayed correctly.
- **Caching**: Stores movie details and posters locally to reduce data usage and improve speed.

## 🌐 Available Translations

This extension supports the following languages:

- **English**
- **Español** (Spanish)
- **Deutsch** (German)
- **Português** (Portuguese)
- **Русский** (Russian)
- **Français** (French)

## 👤 Credits

- **Data Provider**: The Movie Database (TMDB)
