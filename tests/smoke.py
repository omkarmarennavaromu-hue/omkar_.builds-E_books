"""Run an end-to-end smoke test in a TEMPORARY project copy.

All test feedback is written outside the delivered project's data directory.
Run: python tests/smoke.py
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


def available_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def run_test():
    with tempfile.TemporaryDirectory(prefix='omkar-smoke-') as work:
        work = Path(work)
        shutil.copyfile(ROOT / 'server.py', work / 'server.py')
        (work / 'public').symlink_to(ROOT / 'public', target_is_directory=True)
        (work / 'data').mkdir()
        port = available_port()
        process = subprocess.Popen([sys.executable, str(work/'server.py')], cwd=work,
                                   env={**os.environ, 'PORT':str(port)},
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        base = f'http://127.0.0.1:{port}'
        jar = http.cookiejar.CookieJar()
        opener = build_opener(HTTPCookieProcessor(jar))

        def request(path, data=None, expected=200, headers=None, method=None):
            body = None if data is None else json.dumps(data).encode()
            req = Request(base+path, body, headers={**({'Content-Type':'application/json'} if data is not None else {}), **(headers or {})}, method=method)
            try:
                response = opener.open(req, timeout=5)
            except HTTPError as error:
                response = error
            assert response.status == expected, (path, expected, response.status, response.read()[:200])
            content = response.read()
            return (json.loads(content) if response.headers.get_content_type() == 'application/json' else content), response.headers

        try:
            for _ in range(50):
                try:
                    request('/api/health')
                    break
                except (URLError, ConnectionError):
                    if process.poll() is not None:
                        raise RuntimeError('Test server stopped during startup.')
                    time.sleep(.1)
            else:
                raise RuntimeError('Test server did not become ready.')
            assert request('/api/health')[0]['ok']
            for path in ('/', '/admin', '/reader.html', '/css/site.css', '/js/site.js', '/favicon.svg',
                         '/books/how-to-seduce-anyone.epub', '/media/cover.webp', '/media/page-attention.webp'):
                content, headers = request(path)
                assert len(content) > 10, path
                if path == '/reader.html':
                    assert content.count(b'id="page-') == 29, 'The online reader must contain all 29 manuscript pages.'
            chunk, headers = request('/books/how-to-seduce-anyone.pdf', headers={'Range':'bytes=0-63'}, expected=206)
            assert chunk.startswith(b'%PDF') and len(chunk)==64
            assert headers['Content-Range'].startswith('bytes 0-63/')
            request('/media/promo-square.mp4', headers={'Range':'bytes=0-31'}, expected=206)
            request('/data/admin_access.txt', expected=404)
            request('/%2e%2e/data/admin_access.txt', expected=404)
            request('/api/admin/reviews', expected=401)
            clean,_ = request('/api/feedback')
            assert clean['ratingCount']==clean['likes']==clean['dislikes']==clean['reviewCount']==0
            assert clean['reviews']==[] and clean['averageRating'] is None
            assert all(x==0 for x in clean['distribution'].values())
            bad,_=request('/api/rating', {'stars':6}, expected=400)
            assert bad['error']
            first,_=request('/api/rating', {'stars':4})
            assert first['ratingCount']==1 and first['averageRating']==4
            changed,_=request('/api/rating', {'stars':5})
            assert changed['ratingCount']==1 and changed['averageRating']==5
            liked,_=request('/api/reaction', {'reaction':'like'})
            assert liked['likes']==1 and liked['dislikes']==0
            switched,_=request('/api/reaction', {'reaction':'dislike'})
            assert switched['likes']==0 and switched['dislikes']==1
            undone,_=request('/api/reaction', {'reaction':None})
            assert undone['likes']==undone['dislikes']==0
            text='An honest test review. The most useful part was the section on listening.'
            pending,_=request('/api/review', {'stars':5,'name':'Actual test guest','text':text})
            assert pending['reviewCount']==0 and pending['yours']['reviewStatus']=='pending'
            assert pending['reviews']==[]
            request('/api/admin/login', {'passphrase':'not-the-passphrase'}, expected=401)
            secret=(work/'data/admin_access.txt').read_text().strip()
            authorized,_=request('/api/admin/login', {'passphrase':secret})
            assert authorized['authenticated']
            pending_list,_=request('/api/admin/reviews?status=pending')
            assert len(pending_list['reviews'])==1
            review_id=pending_list['reviews'][0]['id']
            request(f'/api/admin/reviews/{review_id}', {'status':'approved'})
            published,_=request('/api/feedback')
            assert published['reviewCount']==1 and published['reviews'][0]['body']==text
            request(f'/api/admin/reviews/{review_id}', {'status':'rejected'})
            removed,_=request('/api/feedback')
            assert removed['reviewCount']==0 and removed['reviews']==[]
            revised,_=request('/api/review', {'stars':5,'name':'Actual test guest','text':text+' Revised.'})
            assert revised['yours']['reviewStatus']=='pending'
            assert len(request('/api/admin/reviews?status=pending')[0]['reviews'])==1
            request('/api/admin/logout', {})
            assert request('/api/admin/status')[0]['authenticated'] is False
            request('/api/admin/reviews', expected=401)
            print('PASS: assets, PDF/video ranges, private files, zero seed, validation, guest votes, moderation, resubmission and logout')
            print('All test feedback stayed in a temporary project directory.')
        finally:
            process.terminate()
            try: process.wait(timeout=4)
            except subprocess.TimeoutExpired: process.kill(); process.wait()


if __name__ == '__main__':
    run_test()
