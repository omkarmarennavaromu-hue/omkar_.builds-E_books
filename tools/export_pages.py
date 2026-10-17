"""Build a truthful, path-safe GitHub Pages edition in docs/.

GitHub Pages cannot run the Python/SQLite API. This export deliberately omits
feedback controls and admin access, while retaining the complete reader,
book downloads and promotional film. No votes/reviews are invented or copied.
Run: python tools/export_pages.py
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
DOCS = ROOT / 'docs'

if DOCS.exists():
    shutil.rmtree(DOCS)
shutil.copytree(PUBLIC, DOCS)
(DOCS / 'admin.html').unlink()
(DOCS / 'css' / 'admin.css').unlink()


def relative_html(source: str) -> str:
    """Make local URLs work under /<repository-name>/, not only domain root."""
    source = source.replace('href="/"', 'href="index.html"')
    for path in ('books/', 'media/', 'fonts/', 'css/', 'js/'):
        source = source.replace(f'="/{path}', f'="{path}')
        source = source.replace(f"='/{path}", f"='{path}")
    for path in ('reader.html', 'favicon.svg'):
        source = source.replace(f'="/{path}"', f'="{path}"')
        source = source.replace(f"='/{path}'", f"='{path}'")
    source = source.replace("url('/fonts/", "url('fonts/")
    return source


index = (DOCS / 'index.html').read_text(encoding='utf-8')
index = index.replace('<html lang="en">', '<html lang="en" data-static-site="true">', 1)
start = index.index('    <section class="community section-pad" id="community"')
end = index.index('    </section>', start) + len('    </section>')
static_community = '''    <section class="community section-pad" id="community" aria-labelledby="communityTitle">
      <div class="container section-head"><span>05 / READER RESPONSES</span><span>GITHUB PAGES / STATIC EDITION</span></div>
      <div class="container community-intro"><div><span class="eyebrow reveal">AN HONEST PLACE TO RESPOND</span><h2 id="communityTitle" class="display-title reveal">REAL READERS.<br><span class="stroke-text">NO MADE-UP SCORES.</span></h2></div><p class="reveal">This GitHub Pages edition is static. It cannot collect or display ratings, reactions, or reviews without a separate server. Nothing is fabricated to fill the space.</p></div>
      <div class="container static-feedback reveal"><span class="static-feedback-mark" aria-hidden="true">✳</span><div><span class="static-feedback-label">AN HONEST NOTE / 001</span><h3>THE BOOK IS HERE.<br><em>THE FEEDBACK ISN’T.</em></h3><p>Read and download the complete e-book above. The real feedback and moderation code is preserved in the GitHub repository, ready for a future server-backed deployment.</p></div><a class="button button-outline" href="#read">Read the book <span aria-hidden="true">↗</span></a></div>
    </section>'''
index = index[:start] + static_community + index[end:]
index = index.replace('<a href="/admin">REVIEW MODERATION ↗</a>', '<span>GITHUB PAGES / STATIC EDITION</span>')
index = relative_html(index)
(DOCS / 'index.html').write_text(index, encoding='utf-8')

reader = relative_html((DOCS / 'reader.html').read_text(encoding='utf-8'))
(DOCS / 'reader.html').write_text(reader, encoding='utf-8')

css_path = DOCS / 'css' / 'site.css'
css = css_path.read_text(encoding='utf-8')
css = css.replace("url('/fonts/", "url('../fonts/")
css += '''
/* The static edition has no fake ratings or non-functional feedback controls. */
.static-feedback{border:1px solid var(--line);border-radius:22px;padding:clamp(28px,4vw,54px);background:radial-gradient(circle at 6% 20%,#282313,transparent 31%),#18191b;display:grid;grid-template-columns:92px 1fr auto;align-items:center;gap:30px}.static-feedback-mark{font:normal 95px/.9 var(--sans);color:var(--accent)}.static-feedback-label{font:400 9px var(--mono);letter-spacing:.13em;color:var(--accent)}.static-feedback h3{font:700 clamp(33px,3.4vw,53px)/1 var(--sans);letter-spacing:-.055em;margin:16px 0}.static-feedback h3 em{font:italic 1.17em/.88 var(--serif);color:var(--accent)}.static-feedback p{max-width:580px;color:#aaa99f;font-size:13px;line-height:1.8;margin:0}.static-feedback .button{align-self:center}@media(max-width:1050px){.static-feedback{grid-template-columns:70px 1fr}.static-feedback .button{grid-column:2;justify-self:start}.static-feedback-mark{font-size:80px}}@media(max-width:650px){.static-feedback{display:block}.static-feedback-mark{display:block;font-size:80px;margin-bottom:10px}.static-feedback .button{margin-top:26px}.static-feedback h3{font-size:39px}}@media(max-width:360px){.static-feedback h3{font-size:32px}}
'''
css_path.write_text(css, encoding='utf-8')

js_path = DOCS / 'js' / 'site.js'
js = js_path.read_text(encoding='utf-8')
marker = "  // Only the server's real feedback appears here; no sample entries exist."
assert js.count(marker) == 1
js = js.split(marker, 1)[0].replace("frame.src = '/reader.html';", "frame.src = 'reader.html';")
js += "  // Pages has no API. No feedback data is requested or simulated.\n})();\n"
js_path.write_text(js, encoding='utf-8')
(DOCS / '.nojekyll').write_text('', encoding='utf-8')

for path in (DOCS / 'index.html', DOCS / 'reader.html'):
    text = path.read_text(encoding='utf-8')
    absolute = re.findall(r'''(?:href|src|poster|data-image)=["']/([^"']+)["']''', text)
    if absolute:
        raise RuntimeError(f'{path.name} still has root-relative URLs: {absolute}')
assert 'api/feedback' not in js
assert 'id="reviewForm"' not in index and 'id="likeButton"' not in index
assert len(list((DOCS / 'books').glob('*'))) == 2
print(f'Exported GitHub Pages edition to {DOCS}: reader, PDF, EPUB, film; no fake or broken feedback UI.')
