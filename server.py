"""Public e-book site with genuine SQLite-backed visitor feedback.

Run: python server.py
No third-party Python dependencies. No sample ratings, likes, dislikes or reviews.
"""
from __future__ import annotations

import hmac
import hashlib
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
DB_PATH = DATA / 'feedback.sqlite3'
ADMIN_SECRET_PATH = DATA / 'admin_access.txt'
SIGNING_SECRET_PATH = DATA / 'visitor_signing.key'
BOOK_ID = 'how-to-seduce-anyone'
SITE_NAME = 'omkar_.builds-E-books'
SESSION_SECONDS = 8 * 60 * 60
ADMIN_SESSIONS: dict[str, float] = {}
SESSION_LOCK = threading.Lock()
RATE_BUCKETS: dict[tuple[str, str], list[float]] = {}
RATE_LOCK = threading.Lock()


def secret_file(path: Path, nbytes: int) -> bytes:
    if not path.exists():
        value = secrets.token_urlsafe(nbytes).encode('ascii')
        with open(path, 'xb') as f:
            f.write(value)
    os.chmod(path, 0o600)
    return path.read_bytes().strip()


ADMIN_SECRET = secret_file(ADMIN_SECRET_PATH, 24)
SIGNING_SECRET = secret_file(SIGNING_SECRET_PATH, 32)


@contextmanager
def database():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA busy_timeout = 15000')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    with database() as db:
        db.execute('PRAGMA journal_mode = WAL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS ratings (
                book_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, visitor_id)
            );
            CREATE TABLE IF NOT EXISTS reactions (
                book_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                reaction TEXT NOT NULL CHECK (reaction IN ('like','dislike')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, visitor_id)
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                body TEXT NOT NULL,
                stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
                status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(book_id, visitor_id)
            );
            CREATE INDEX IF NOT EXISTS reviews_public ON reviews(book_id,status,created_at);
        ''')


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sign_visitor(visitor_id: str):
    digest = hmac.new(SIGNING_SECRET, visitor_id.encode('utf-8'), hashlib.sha256).hexdigest()
    return f'{visitor_id}.{digest}'


def validate_visitor(token: str | None):
    if not token or '.' not in token:
        return None
    visitor_id, signature = token.rsplit('.', 1)
    if not re.fullmatch(r'[A-Za-z0-9_-]{18,80}', visitor_id):
        return None
    expected = sign_visitor(visitor_id).rsplit('.', 1)[1]
    return visitor_id if hmac.compare_digest(signature, expected) else None


def book_feedback(db, visitor_id: str):
    row = db.execute(
        'SELECT COUNT(*) AS count, AVG(stars) AS average FROM ratings WHERE book_id=?',
        (BOOK_ID,)
    ).fetchone()
    star_rows = db.execute(
        'SELECT stars, COUNT(*) AS n FROM ratings WHERE book_id=? GROUP BY stars',
        (BOOK_ID,)
    ).fetchall()
    dist = {str(i): 0 for i in range(1, 6)}
    for item in star_rows:
        dist[str(item['stars'])] = item['n']
    reactions = {'like': 0, 'dislike': 0}
    for item in db.execute(
        'SELECT reaction, COUNT(*) AS n FROM reactions WHERE book_id=? GROUP BY reaction',
        (BOOK_ID,)
    ):
        reactions[item['reaction']] = item['n']
    published = db.execute(
        '''SELECT id, display_name, body, stars, created_at
           FROM reviews WHERE book_id=? AND status='approved'
           ORDER BY created_at DESC, id DESC LIMIT 30''', (BOOK_ID,)
    ).fetchall()
    total_reviews = db.execute(
        "SELECT COUNT(*) FROM reviews WHERE book_id=? AND status='approved'", (BOOK_ID,)
    ).fetchone()[0]
    my_rating = db.execute(
        'SELECT stars FROM ratings WHERE book_id=? AND visitor_id=?',
        (BOOK_ID, visitor_id)
    ).fetchone()
    my_reaction = db.execute(
        'SELECT reaction FROM reactions WHERE book_id=? AND visitor_id=?',
        (BOOK_ID, visitor_id)
    ).fetchone()
    my_review = db.execute(
        'SELECT status FROM reviews WHERE book_id=? AND visitor_id=?',
        (BOOK_ID, visitor_id)
    ).fetchone()
    return {
        'bookId': BOOK_ID,
        'ratingCount': row['count'],
        'averageRating': round(row['average'], 2) if row['count'] else None,
        'distribution': dist,
        'likes': reactions['like'],
        'dislikes': reactions['dislike'],
        'reviewCount': total_reviews,
        'reviews': [dict(item) for item in published],
        'yours': {
            'rating': my_rating['stars'] if my_rating else None,
            'reaction': my_reaction['reaction'] if my_reaction else None,
            'reviewStatus': my_review['status'] if my_review else None,
        },
    }


class SiteHandler(BaseHTTPRequestHandler):
    server_version = 'OmkarBooks/1.0'

    def log_message(self, fmt, *args):
        # Never log cookies, admin passphrases or review bodies.
        print('%s [%s] %s' % (self.address_string(), self.log_date_time_string(), fmt % args), flush=True)

    def parsed(self):
        return urlsplit(self.path)

    def cookies(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            pass
        return cookie

    def cookie_policy(self, admin=False):
        # HTTPS previews are embedded cross-site. Partitioned cookies let modern
        # browsers keep guest/admin sessions inside that iframe without asking
        # for unrestricted third-party cookies. Local HTTP remains usable too.
        forwarded = self.headers.get('X-Forwarded-Proto', '').split(',')[0].strip().lower()
        host = self.headers.get('Host', '').split(':')[0].lower()
        https = forwarded == 'https' or host.endswith('.e2b.app')
        if https:
            return '; SameSite=None; Secure; Partitioned'
        return '; SameSite=Strict' if admin else '; SameSite=Lax'

    def visitor(self):
        jar = self.cookies()
        value = jar['visitor'].value if 'visitor' in jar else None
        visitor_id = validate_visitor(value)
        if visitor_id:
            return visitor_id, None
        visitor_id = secrets.token_urlsafe(24)
        token = sign_visitor(visitor_id)
        return visitor_id, f'visitor={token}; Path=/; Max-Age=31536000; HttpOnly{self.cookie_policy()}'

    def is_admin(self):
        jar = self.cookies()
        token = jar['admin_session'].value if 'admin_session' in jar else None
        if not token:
            return False
        with SESSION_LOCK:
            expiry = ADMIN_SESSIONS.get(token, 0)
            if expiry > time.monotonic():
                return True
            ADMIN_SESSIONS.pop(token, None)
        return False

    def admin_cookie(self, token: str, age: int):
        return f'admin_session={token}; Path=/; Max-Age={age}; HttpOnly{self.cookie_policy(admin=True)}'

    def common_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        # No X-Frame-Options/frame-ancestors restriction: Arena's live preview
        # displays this site in a cross-origin iframe.

    def json(self, status: int, payload: dict, cookie: str | None = None):
        raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.common_headers()
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(raw)

    def problem(self, status: int, message: str):
        self.json(status, {'error': message})

    def read_json(self):
        if not self.headers.get('Content-Type', '').lower().startswith('application/json'):
            raise ValueError('Send JSON to this endpoint.')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ValueError('Invalid request length.')
        if length < 1 or length > 16000:
            raise ValueError('Request is empty or too large.')
        try:
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError('Invalid JSON.')
        if not isinstance(body, dict):
            raise ValueError('Expected a JSON object.')
        return body

    def limited(self, visitor_id: str, route: str, max_per_minute=24):
        key = (visitor_id, route)
        now = time.monotonic()
        with RATE_LOCK:
            recent = RATE_BUCKETS.get(key, [])
            recent = [t for t in recent if now-t < 60]
            if len(recent) >= max_per_minute:
                RATE_BUCKETS[key] = recent
                return True
            recent.append(now)
            RATE_BUCKETS[key] = recent
        return False

    def static(self, path: str):
        if path == '/':
            path = '/index.html'
        elif path == '/admin':
            path = '/admin.html'
        try:
            f = (PUBLIC / unquote(path).lstrip('/')).resolve()
            if not f.is_relative_to(PUBLIC.resolve()) or not f.is_file():
                self.problem(404, 'Page not found.')
                return
        except (ValueError, OSError):
            self.problem(404, 'Page not found.')
            return
        size = f.stat().st_size
        mime = mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
        if f.suffix == '.woff2':
            mime = 'font/woff2'
        if f.suffix == '.epub':
            mime = 'application/epub+zip'
        start, end = 0, size - 1
        status = 200
        range_header = self.headers.get('Range', '')
        if range_header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header.strip())
            if not match or (not match.group(1) and not match.group(2)):
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.common_headers();self.end_headers();return
            if not match.group(1):
                take = int(match.group(2))
                start = max(0, size - take)
            else:
                start = int(match.group(1))
                if match.group(2):
                    end = min(int(match.group(2)), size-1)
            if start > end or start >= size:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.common_headers();self.end_headers();return
            status = 206
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(end-start+1))
        self.send_header('Accept-Ranges', 'bytes')
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Cache-Control', 'public, max-age=3600')
        self.common_headers()
        self.end_headers()
        if self.command == 'HEAD':
            return
        try:
            with f.open('rb') as stream:
                stream.seek(start)
                remaining = end-start+1
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Browser may stop reading during video/PDF seeking.

    def do_HEAD(self):
        if self.parsed().path.startswith('/api/'):
            self.problem(405, 'Use GET or POST.')
        else:
            self.static(self.parsed().path)

    def do_GET(self):
        path = self.parsed().path
        if path == '/api/health':
            return self.json(200, {'ok': True, 'site': SITE_NAME})
        if path == '/api/feedback':
            visitor_id, cookie = self.visitor()
            with database() as db:
                payload = book_feedback(db, visitor_id)
            return self.json(200, payload, cookie)
        if path == '/api/admin/status':
            return self.json(200, {'authenticated': self.is_admin()})
        if path == '/api/admin/reviews':
            if not self.is_admin():
                return self.problem(401, 'Admin login required.')
            raw = parse_qs(self.parsed().query).get('status', ['pending'])[0]
            if raw not in ('pending', 'approved', 'rejected'):
                return self.problem(400, 'Invalid review status.')
            with database() as db:
                rows = db.execute(
                    '''SELECT id, display_name, body, stars, status, created_at, updated_at
                       FROM reviews WHERE book_id=? AND status=?
                       ORDER BY created_at DESC, id DESC LIMIT 100''',
                    (BOOK_ID, raw)
                ).fetchall()
            return self.json(200, {'reviews': [dict(row) for row in rows], 'status': raw})
        return self.static(path)

    def do_POST(self):
        path = self.parsed().path
        try:
            body = self.read_json()
            if path == '/api/admin/login':
                submitted = str(body.get('passphrase', '')).encode('utf-8')
                if not hmac.compare_digest(submitted, ADMIN_SECRET):
                    return self.problem(401, 'Incorrect passphrase.')
                token = secrets.token_urlsafe(32)
                with SESSION_LOCK:
                    ADMIN_SESSIONS[token] = time.monotonic()+SESSION_SECONDS
                return self.json(200, {'authenticated': True}, self.admin_cookie(token, SESSION_SECONDS))
            if path == '/api/admin/logout':
                jar = self.cookies()
                if 'admin_session' in jar:
                    with SESSION_LOCK:
                        ADMIN_SESSIONS.pop(jar['admin_session'].value, None)
                return self.json(200, {'authenticated': False}, self.admin_cookie('', 0))
            match = re.fullmatch(r'/api/admin/reviews/(\d+)', path)
            if match:
                if not self.is_admin():
                    return self.problem(401, 'Admin login required.')
                status = body.get('status')
                if status not in ('approved','rejected','pending'):
                    return self.problem(400, 'Choose approved, rejected or pending.')
                with database() as db:
                    cur = db.execute(
                        'UPDATE reviews SET status=?, updated_at=? WHERE id=? AND book_id=?',
                        (status, now_utc(), int(match.group(1)), BOOK_ID)
                    )
                if cur.rowcount != 1:
                    return self.problem(404, 'Review not found.')
                return self.json(200, {'ok': True, 'status': status})
            if path not in ('/api/rating', '/api/reaction', '/api/review'):
                return self.problem(404, 'Endpoint not found.')
            visitor_id, cookie = self.visitor()
            if self.limited(visitor_id, path, 20 if path != '/api/review' else 5):
                return self.json(429, {'error': 'Too many requests. Please wait a minute.'}, cookie)
            stamp = now_utc()
            with database() as db:
                if path == '/api/rating':
                    stars = body.get('stars')
                    if isinstance(stars, bool) or type(stars) is not int or not 1 <= stars <= 5:
                        return self.json(400, {'error': 'Choose a rating from 1 to 5 stars.'}, cookie)
                    db.execute(
                        '''INSERT INTO ratings (book_id,visitor_id,stars,created_at,updated_at)
                           VALUES (?,?,?,?,?) ON CONFLICT(book_id,visitor_id)
                           DO UPDATE SET stars=excluded.stars, updated_at=excluded.updated_at''',
                        (BOOK_ID, visitor_id, stars, stamp, stamp)
                    )
                elif path == '/api/reaction':
                    reaction = body.get('reaction')
                    if reaction is None:
                        db.execute('DELETE FROM reactions WHERE book_id=? AND visitor_id=?',
                                   (BOOK_ID, visitor_id))
                    elif reaction in ('like','dislike'):
                        db.execute(
                            '''INSERT INTO reactions (book_id,visitor_id,reaction,created_at,updated_at)
                               VALUES (?,?,?,?,?) ON CONFLICT(book_id,visitor_id)
                               DO UPDATE SET reaction=excluded.reaction, updated_at=excluded.updated_at''',
                            (BOOK_ID, visitor_id, reaction, stamp, stamp)
                        )
                    else:
                        return self.json(400, {'error': 'Choose like or dislike.'}, cookie)
                elif path == '/api/review':
                    stars = body.get('stars')
                    if isinstance(stars, bool) or type(stars) is not int or not 1 <= stars <= 5:
                        return self.json(400, {'error': 'Choose 1–5 stars before submitting.'}, cookie)
                    name = str(body.get('name', '')).strip()
                    text = str(body.get('text', '')).strip()
                    name = re.sub(r'[\x00-\x1f<>]', '', name)[:40] or 'Anonymous reader'
                    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
                    if len(text) < 20 or len(text) > 1000:
                        return self.json(400, {'error': 'Write a review between 20 and 1,000 characters.'}, cookie)
                    db.execute(
                        '''INSERT INTO ratings (book_id,visitor_id,stars,created_at,updated_at)
                           VALUES (?,?,?,?,?) ON CONFLICT(book_id,visitor_id)
                           DO UPDATE SET stars=excluded.stars, updated_at=excluded.updated_at''',
                        (BOOK_ID, visitor_id, stars, stamp, stamp)
                    )
                    db.execute(
                        '''INSERT INTO reviews (book_id,visitor_id,display_name,body,stars,status,created_at,updated_at)
                           VALUES (?,?,?,?,?,'pending',?,?)
                           ON CONFLICT(book_id,visitor_id) DO UPDATE SET
                           display_name=excluded.display_name, body=excluded.body,
                           stars=excluded.stars, status='pending', updated_at=excluded.updated_at''',
                        (BOOK_ID, visitor_id, name, text, stars, stamp, stamp)
                    )
                response = book_feedback(db, visitor_id)
            if path == '/api/review':
                response['message'] = 'Your review is awaiting moderation.'
            return self.json(200, response, cookie)
        except ValueError as e:
            return self.problem(400, str(e))
        except sqlite3.Error as e:
            self.log_error('Database error: %s', e)
            return self.problem(500, 'Could not save right now. Please try again.')
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == '__main__':
    init_database()
    port = int(os.environ.get('PORT', '8000'))
    server = ThreadingHTTPServer(('0.0.0.0', port), SiteHandler)
    server.daemon_threads = True
    print(f'{SITE_NAME} listening on 0.0.0.0:{port}', flush=True)
    print('Feedback database starts empty unless real visitors have submitted data.', flush=True)
    server.serve_forever()
