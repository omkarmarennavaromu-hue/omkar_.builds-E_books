# omkar_.builds-E-books

A responsive, scroll-led e-book site for Omkar Marennavar's first release, **How to Seduce Anyone**. Includes the complete book as a responsive in-page HTML reader and free PDF/EPUB downloads; the original 20-second promotional film; and real, SQLite-backed visitor feedback.

## Visual direction

Inspired by the user-supplied portfolio reference: near-black surfaces, warm yellow accents, oversized solid/outlined typography, monospaced editorial labels, framed media and scroll-led motion. The layout and e-book-specific content were built for this project; the portfolio's personal photos, project screenshots, copy and scripts are not used. Motion respects reduced-motion preferences.

## GitHub Pages edition

`docs/` is the static edition for the requested public GitHub Pages repository `omkar_.builds-E_books`. It preserves the full book, online reader, PDF/EPUB downloads and film. Pages cannot run the Python/SQLite feedback server, so this edition clearly says feedback is unavailable instead of showing fake or non-functional ratings. The full-featured server version remains in `public/` and `server.py`. See **[PUBLISH.md](PUBLISH.md)** for secure, exact publication steps. Rebuild `docs/` after source changes with `python tools/export_pages.py`.

## Preview locally

Requires Python 3.10+; no Python packages, Node tooling, or external CDNs are needed.

```bash
cd /home/user/omkar_builds_ebooks
PORT=8000 python server.py
```

Open `http://localhost:8000` (or the Arena live preview). The server listens on `0.0.0.0` so the preview can reach it. To use another port, set `PORT`. Run `python tests/smoke.py` for a server/API test that writes all test responses to a temporary database rather than the live feedback database.

## Moderate reviews

1. On first startup, the server creates `data/admin_access.txt` containing a random admin passphrase and `data/visitor_signing.key` for signed guest cookies. The files are private server-side material; **never expose or commit them**.
2. As the owner, read the passphrase from your server shell: `cat data/admin_access.txt`.
3. Visit `/admin`, enter the passphrase, and approve or decline submitted reviews. Admin authentication uses an HttpOnly cookie with an eight-hour server-side session. Sign out when finished.

The public review list includes **approved reviews only**. Ratings and like/dislike totals update immediately; written reviews start pending. There are **no seeded testimonials, votes, or reviews**. The feedback database lives in `data/feedback.sqlite3`, outside the public web root.

Guest votes are limited to one active rating and one active like/dislike per signed browser cookie; ratings can be changed and a reaction can be switched or removed. Reviews are one per cookie at a time, and declined reviews may be revised. This does **not** identify or verify individual humans—clearing cookies or using another browser may create another guest identity. Basic per-cookie request throttling reduces accidental rapid submissions but is not anti-abuse protection against a determined attacker. HTTPS previews use Secure partitioned cookies to support the embedded live preview; if your browser disallows all embedded storage, open the preview in a new tab.

## Project layout

- `server.py`: standard-library HTTP server, SQLite API, file serving with byte-range support for video/PDF, and moderation routes.
- `public/index.html`, `public/css/site.css`, `public/js/site.js`: public experience, responsive design, in-page reader dialog and feedback UI.
- `public/reader.html`: complete 29-page manuscript as a responsive HTML reading edition, also usable directly without JavaScript; `tools/build_reader.py` regenerates it from the canonical manuscript in the sibling e-book project.
- `public/admin.html`, `public/css/admin.css`: private moderation interface (requires server-issued session).
- `public/books/`: complete PDF and EPUB from the finished e-book.
- `public/media/`: book-cover artwork, actual book-page previews, original film and poster.
- `public/fonts/`: locally served typefaces with license text.
- `data/`: persistent database and secrets; deliberately **not** under `public/` and excluded from Git/ZIP.
- `docs/`: path-safe static GitHub Pages export; no admin panel or simulated feedback.
- `.github/workflows/pages.yml`: deploys only `docs/` to GitHub Pages after an authenticated push.

## Before permanent deployment

The static Pages edition is prepared but not published until you push the repository and enable Pages. To launch the **full feedback-enabled server** publicly later, put it behind HTTPS with a trusted reverse proxy, supply persistent storage for `data/`, back up the SQLite database securely, add proxy-level abuse and login-rate limits, and keep the passphrase/signing key private. Keep the application on a single origin so guest/admin cookies work. The HTML reader works without embedded PDF support; direct PDF and EPUB links are available separately.

Book credits: author **Omkar Marennavar**, with the user-authorized official collaboration credit **The Diary Of A CEO × Omkar Marennavar**. The cover uses portraits from the real episode thumbnail; the film is newly made motion design rather than podcast footage. Font license files are in `public/fonts/`.
