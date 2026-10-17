"""Build a complete, responsive HTML reader from the finished book manuscript.

This generator reads the canonical manuscript in the sibling e-book project.
The generated public/reader.html needs no Python or external files at runtime
except this website's self-hosted fonts/cover.
"""
from __future__ import annotations

import html
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'How_to_Seduce_Anyone' / '_source' / 'content.py'
OUTPUT = ROOT / 'public' / 'reader.html'

spec = importlib.util.spec_from_file_location('book_content', SOURCE)
book = importlib.util.module_from_spec(spec)
spec.loader.exec_module(book)


def e(value):
    return html.escape(str(value), quote=True)


def text(value):
    return e(value).replace('\n', '<br>')


def blocks_html(blocks):
    out = []
    for kind, value in blocks:
        if kind == 'p':
            out.append(f'<p>{text(value)}</p>')
        elif kind == 'highlight':
            out.append(f'<aside class="highlight">{text(value)}</aside>')
        elif kind == 'small':
            out.append(f'<p class="small-note">{text(value)}</p>')
        elif kind == 'steps':
            out.append('<ol class="steps">')
            for label, body in value:
                out.append(f'<li><strong>{text(label)}</strong><p>{text(body)}</p></li>')
            out.append('</ol>')
        elif kind == 'example':
            label, body = value
            out.append(f'<blockquote class="example"><span>{text(label)}</span><p>{text(body)}</p></blockquote>')
        elif kind == 'lines':
            out.append('<div class="prompts">')
            for label, n in value:
                out.append(f'<div class="prompt"><strong>{text(label)}</strong><div aria-hidden="true">'+ '<i></i>'*n +'</div></div>')
            out.append('</div>')
        elif kind == 'rules':
            out.append('<ol class="principles">')
            for rule in value:
                out.append(f'<li>{text(rule)}</li>')
            out.append('</ol>')
        elif kind == 'days':
            out.append('<div class="days">')
            for day, label, body in value:
                out.append(f'<div class="day"><span>{e(day)}</span><div><strong>{text(label)}</strong><p>{text(body)}</p></div></div>')
            out.append('</div>')
        else:
            raise ValueError(f'Unrecognized block type: {kind}')
    return '\n'.join(out)


def toc_html():
    return '\n'.join(f'<a href="#page-{page}"><span>{e(number)}</span>{e(title)}</a>' for page, number, title in book.TOC)


def render_page(page, index):
    kind = page['kind']
    number = f'{index:02d} / 29'
    if kind == 'cover':
        return f'''<section class="reader-cover" id="page-{index}">
          <img src="/media/cover-large.webp" alt="Cover of How to Seduce Anyone, featuring Robert Greene and Steven Bartlett" width="1200" height="1800">
          <div><span class="eyebrow">THE COMPLETE FIRST EDITION</span><h1>How to<br><em>Seduce Anyone.</em></h1><p>A simple guide to attention, confidence &amp; real connection.</p><small>By Omkar Marennavar<br>Official collaboration credit: The Diary Of A CEO × Omkar Marennavar</small></div>
        </section>'''
    if kind == 'title':
        return f'''<section class="reader-page title-page" id="page-{index}"><span class="page-kicker">TITLE PAGE</span><h2>How to<br><em>Seduce Anyone.</em></h2><p class="lead">A simple guide to attention, confidence &amp; real connection.</p><div class="title-rule"></div><p>Written by Omkar Marennavar.</p><p>Original companion e-book inspired by a conversation with Robert Greene on The Diary Of A CEO.</p><span class="page-number">{number}</span></section>'''
    if kind == 'toc':
        return f'''<section class="reader-page contents-page" id="page-{index}"><span class="page-kicker">YOUR MAP THROUGH THE BOOK</span><h2>Contents<span class="period">.</span></h2><nav class="contents-list" aria-label="Book contents">{toc_html()}</nav><span class="page-number">{number}</span></section>'''
    if kind == 'divider':
        return f'''<section class="reader-page part-divider" id="page-{index}"><span class="page-kicker">{e(page['part'])} / {number}</span><span class="big-number" aria-hidden="true">{e(page['num'])}</span><h2>{e(page['title'])}<span class="period">.</span></h2><p class="lead">{e(page['line'])}</p><p class="divider-micro">{e(page['micro'])}</p><span class="page-number">{number}</span></section>'''
    if kind == 'sources':
        entries = '\n'.join(f'<li><a href="{e(book.VIDEO_URL)}&amp;t={seconds}s" target="_blank" rel="noopener noreferrer"><span>{e(timestamp)}</span><strong>{e(topic)}</strong><span aria-hidden="true">↗</span></a></li>' for timestamp, topic, seconds in book.SOURCES)
        return f'''<section class="reader-page source-page" id="page-{index}"><span class="page-kicker">THE CONVERSATION THAT INSPIRED THIS BOOK</span><h2>Sources &amp;<br><em>episode guide.</em></h2><p>This original companion e-book draws on themes discussed by Robert Greene in an episode of <cite>The Diary Of A CEO</cite>. These links take you to moments in the source conversation; this book does not reproduce its transcript.</p><ol class="source-list">{entries}</ol><p class="small-note">Episode: {e(book.VIDEO_TITLE)}. Written by Omkar Marennavar. The Diary Of A CEO × Omkar Marennavar collaboration credit appears by permission.</p><span class="page-number">{number}</span></section>'''
    if kind in ('intro', 'content'):
        title = text(page['title'])
        lead = f'<p class="lead">{text(page["lead"])}</p>' if page.get('lead') else ''
        chapter = f'<span class="chapter-id">CHAPTER {e(page["chapter"])}</span>' if page.get('chapter') else ''
        return f'''<section class="reader-page" id="page-{index}"><div class="page-label"><span class="page-kicker">{e(page['kicker'])}</span>{chapter}</div><h2>{title}</h2>{lead}<div class="page-body">{blocks_html(page['blocks'])}</div><span class="page-number">{number}</span></section>'''
    raise ValueError(f'Unrecognized page type: {kind}')


page_markup = '\n'.join(render_page(page, index) for index, page in enumerate(book.PAGES, 1))
nav_markup = toc_html()

html_doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#f8f6f0"><meta name="description" content="Read the complete original e-book How to Seduce Anyone by Omkar Marennavar online, free."><title>Read How to Seduce Anyone — omkar_.builds-E-books</title><link rel="icon" href="/favicon.svg" type="image/svg+xml"><style>
@font-face{{font-family:Instrument;src:url('/fonts/InstrumentSerif-Regular.ttf') format('truetype');font-display:swap}}@font-face{{font-family:Instrument;src:url('/fonts/InstrumentSerif-Italic.ttf') format('truetype');font-style:italic;font-display:swap}}@font-face{{font-family:Manrope;src:url('/fonts/Manrope-Regular.ttf') format('truetype');font-display:swap}}@font-face{{font-family:Manrope;src:url('/fonts/Manrope-Bold.ttf') format('truetype');font-weight:700;font-display:swap}}
:root{{--ink:#26302c;--muted:#677168;--line:#d9d7ca;--paper:#f8f6f0;--sand:#eae5d9;--accent:#a36a51;--serif:Instrument,Georgia,serif;--sans:Manrope,Arial,sans-serif}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.75 var(--sans);-webkit-font-smoothing:antialiased}}img{{max-width:100%;height:auto;display:block}}a{{color:inherit;text-decoration:none}}a:focus-visible,summary:focus-visible{{outline:2px solid var(--accent);outline-offset:4px}}::selection{{background:#bb8b73;color:white}}section[id]{{scroll-margin-top:88px}}.progress{{position:fixed;z-index:30;top:0;left:0;height:3px;background:var(--accent);width:0}}.topbar{{height:69px;position:sticky;z-index:20;top:0;background:#f8f6f0f5;backdrop-filter:blur(14px);border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:10px;padding:0 clamp(18px,5vw,64px)}}.brand{{font:normal 26px var(--serif);white-space:nowrap}}.brand span{{color:var(--accent)}}.top-actions{{display:flex;align-items:center;gap:20px;font-size:10px;font-weight:700;letter-spacing:.05em}}.top-actions a:first-child{{color:var(--accent)}}.top-actions a:hover,.index a:hover,.contents-list a:hover{{color:var(--accent)}}.shell{{max-width:1200px;margin:0 auto;padding:0 45px;display:grid;grid-template-columns:220px minmax(0,1fr);gap:clamp(55px,8vw,125px)}}.index{{position:sticky;top:106px;align-self:start;padding:43px 0;height:max-content}}.index-heading,.eyebrow,.page-kicker,.chapter-id,.page-number{{font-size:9px;font-weight:700;letter-spacing:.16em;color:var(--accent)}}.index h2{{font:normal 43px var(--serif);margin:5px 0 27px}}.index nav a{{display:flex;gap:12px;padding:9px 0;border-top:1px solid var(--line);line-height:1.3;color:#6b756d;font-size:10px}}.index nav a span{{color:var(--accent);font-weight:700;min-width:18px}}.index-foot{{font-size:9px;letter-spacing:.1em;color:#8c978c;margin-top:32px;border-top:1px solid var(--line);padding-top:19px}}.book{{min-width:0}}.reader-cover{{display:grid;grid-template-columns:minmax(150px,.78fr) 1fr;gap:38px;align-items:center;padding:90px 0 140px;border-bottom:1px solid var(--line)}}.reader-cover img{{width:100%;box-shadow:14px 20px 35px #6c554c36;transform:rotate(-3deg)}}.reader-cover h1{{font:normal clamp(60px,6.5vw,98px)/.91 var(--serif);letter-spacing:-.035em;margin:23px 0}}.reader-cover h1 em,.title-page em,.source-page em{{color:var(--accent)}}.reader-cover p{{font:italic 26px/1.1 var(--serif);color:#736056;max-width:300px;margin:0 0 33px}}.reader-cover small{{font-size:10px;line-height:1.75;color:var(--muted)}}.mobile-toc{{display:none}}.reader-page{{padding:100px 0 110px;border-bottom:1px solid var(--line);position:relative}}.page-label{{display:flex;justify-content:space-between;gap:16px}}.chapter-id{{color:#9aa298}}.reader-page h2{{font:normal clamp(59px,6.1vw,89px)/.99 var(--serif);letter-spacing:-.035em;margin:19px 0 28px}}.reader-page h2 em{{font-style:italic}}.reader-page .lead{{font:italic 31px/1.23 var(--serif);color:var(--accent);margin:0 0 36px}}.page-body>p,.source-page>p,.title-page>p{{max-width:670px;line-height:1.85;color:#434d45;font-size:16px;margin:0 0 20px}}.page-body .small-note,.small-note{{font-size:11px!important;line-height:1.75!important;color:#778176!important;margin-top:30px!important}}.highlight{{border-left:3px solid var(--accent);background:#eae4d6;padding:26px 29px;margin:31px 0 15px;font:italic 35px/1.18 var(--serif);color:#72594c}}.steps{{list-style:none;margin:24px 0 30px;padding:0;border-top:1px solid var(--line)}}.steps li{{display:grid;grid-template-columns:.85fr 1.5fr;gap:25px;padding:19px 0;border-bottom:1px solid var(--line)}}.steps strong{{font:normal 28px/1.06 var(--serif)}}.steps p{{font-size:13px;line-height:1.65;color:#5e675e;margin:2px 0 0}}.example{{background:#e9e3d6;padding:25px 28px;margin:28px 0 30px;border-left:2px solid var(--accent)}}.example span{{font-size:9px;letter-spacing:.16em;font-weight:700;color:var(--accent)}}.example p{{font:italic 26px/1.32 var(--serif);white-space:normal;margin:15px 0 0}}.prompts{{margin:30px 0}}.prompt{{padding:17px 0 26px;border-top:1px solid var(--line)}}.prompt strong{{font:normal 25px var(--serif)}}.prompt>div{{padding-top:20px}}.prompt i{{display:block;border-bottom:1px solid #bdbeb3;height:31px}}.principles{{list-style:none;counter-reset:principle;margin:34px 0;padding:0}}.principles li{{counter-increment:principle;display:grid;grid-template-columns:43px 1fr;align-items:center;gap:10px;border-top:1px solid var(--line);padding:13px 0;font:normal 24px/1.2 var(--serif)}}.principles li:last-child{{border-bottom:1px solid var(--line)}}.principles li::before{{content:counter(principle,decimal-leading-zero);font:700 10px var(--sans);color:var(--accent)}}.days{{margin:28px 0}}.day{{display:grid;grid-template-columns:45px 1fr;gap:15px;border-top:1px solid var(--line);padding:18px 0}}.day:last-child{{border-bottom:1px solid var(--line)}}.day>span{{font:italic 29px var(--serif);color:var(--accent)}}.day strong{{font:normal 27px var(--serif)}}.day p{{font-size:13px;color:#5d685e;line-height:1.7;margin:4px 0}}.page-number{{display:block;text-align:right;color:#8b968c;margin-top:50px}}.title-page{{min-height:720px}}.title-page .title-rule{{width:46px;height:1px;background:var(--accent);margin:50px 0 27px}}.contents-page .period,.part-divider .period{{color:var(--accent)}}.contents-list{{border-top:1px solid var(--line);margin-top:33px}}.contents-list a{{display:grid;grid-template-columns:40px 1fr;gap:10px;border-bottom:1px solid var(--line);padding:14px 2px;font:normal 23px/1.12 var(--serif)}}.contents-list a span{{font:700 11px var(--sans);color:var(--accent)}}.part-divider{{background:#eae4d7;padding:75px 48px 75px;min-height:620px;overflow:hidden}}.part-divider .big-number{{display:block;font:normal 160px/.95 var(--serif);color:#d2bdab;margin-top:42px}}.part-divider h2{{margin:0 0 16px}}.part-divider .lead{{max-width:480px}}.divider-micro{{font-size:9px;font-weight:700;color:#967461;letter-spacing:.18em;margin-top:45px}}.source-list{{list-style:none;margin:42px 0;padding:0;border-top:1px solid var(--line)}}.source-list li{{border-bottom:1px solid var(--line)}}.source-list a{{display:grid;grid-template-columns:80px 1fr 20px;gap:10px;padding:16px 0;align-items:center;font-size:13px}}.source-list a:hover{{color:var(--accent)}}.source-list a span:first-child{{color:var(--accent);font-size:11px;font-weight:700}}.source-list strong{{font-weight:400}}.reading-end{{padding:70px 0 100px;text-align:center}}.reading-end span{{font-size:9px;color:var(--accent);letter-spacing:.16em;font-weight:700}}.reading-end p{{font:italic 42px var(--serif);margin:18px 0 32px}}.download-links{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap}}.download-links a{{background:#a66a52;color:white;font-size:11px;font-weight:700;padding:12px 20px}}.download-links a:hover{{background:#8c543d}}@media(max-width:1050px){{.shell{{grid-template-columns:190px 1fr;gap:35px;padding-inline:30px}}.index nav a{{font-size:9px}}.reader-cover h1{{font-size:70px}}}}@media(max-width:750px){{.shell{{display:block;padding:0 22px}}.index{{display:none}}.topbar{{padding-inline:19px;height:61px}}.brand{{font-size:21px}}.top-actions{{gap:12px;font-size:9px}}.top-actions a:last-child{{display:none}}.reader-cover{{grid-template-columns:1fr;gap:28px;padding:55px 0 70px}}.reader-cover img{{max-width:265px;width:72%;margin:0 auto}}.reader-cover h1{{font-size:clamp(64px,12vw,90px)}}.reader-cover p{{margin-bottom:18px}}.mobile-toc{{display:block;margin:0 0 20px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.mobile-toc summary{{padding:17px 0;font-size:11px;font-weight:700;letter-spacing:.1em;cursor:pointer}}.mobile-toc nav{{padding:0 0 12px}}.mobile-toc a{{display:flex;gap:15px;font-size:11px;padding:10px 0;border-top:1px solid var(--line)}}.mobile-toc a span{{color:var(--accent);min-width:16px}}.reader-page{{padding:68px 0 72px}}.reader-page h2{{font-size:clamp(62px,12vw,79px)}}.reader-page .lead{{font-size:28px}}.page-body>p,.source-page>p,.title-page>p{{font-size:15px}}.highlight{{font-size:31px}}.steps li{{display:block}}.steps p{{margin-top:8px}}.part-divider{{margin-inline:-22px;padding:60px 22px;min-height:0}}.part-divider .big-number{{font-size:125px}}.contents-list a{{font-size:21px}}.source-list a{{grid-template-columns:65px 1fr 14px}}}}@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}
/* Dark-and-gold library chrome; the pages remain warm paper for comfortable reading. */
:root{{--paper:#f7f4eb;--ink:#1a1b1c;--accent:#94671e;--bright:#ffd154}}
.progress{{background:var(--bright)}}.topbar{{background:#121315f7;color:#f5f2e9;border-bottom-color:#3a3b3b}}.brand span,.top-actions a:first-child{{color:var(--bright)}}.top-actions a:last-child{{color:#dad8cd}}.top-actions a:hover{{color:#fff}}.index h2{{font-family:Manrope,Arial,sans-serif;font-weight:700;text-transform:uppercase;font-size:28px;letter-spacing:-.06em;line-height:1.04}}.index-heading,.page-kicker,.chapter-id,.page-number{{font-family:ui-monospace,Menlo,monospace;letter-spacing:.13em}}.reader-cover h1{{font-family:Manrope,Arial,sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:-.065em;font-size:clamp(48px,5.3vw,78px)}}.reader-cover h1 em{{font-family:Instrument,Georgia,serif;font-weight:400;text-transform:none;font-size:1.12em}}.reader-cover p{{color:#665847}}.highlight{{background:#ede5d2;color:#625039}}.part-divider{{background:#ebe2ce}}.download-links a{{background:var(--bright);color:#151617;border-radius:100px}}.download-links a:hover{{background:#fbe49b}}@media(max-width:750px){{.reader-cover h1{{font-size:clamp(56px,11vw,78px)}}.index h2{{font-size:28px}}}}
</style></head><body>
<div class="progress" id="readerProgress" aria-hidden="true"></div><header class="topbar"><a class="brand" href="/">omkar_.builds<span>—E-books</span></a><div class="top-actions"><a href="/books/how-to-seduce-anyone.pdf" target="_blank" rel="noopener">OPEN PDF ↗</a><a href="/books/how-to-seduce-anyone.epub" download="How_to_Seduce_Anyone.epub">GET EPUB ↓</a></div></header>
<div class="shell"><aside class="index" aria-label="Reader chapter navigation"><span class="index-heading">THE READING INDEX</span><h2>Find your place.</h2><nav>{nav_markup}</nav><p class="index-foot">COMPLETE FIRST EDITION / 2026<br>BY OMKAR MARENNAVAR</p></aside>
<main class="book"><details class="mobile-toc"><summary>OPEN THE CHAPTER INDEX</summary><nav aria-label="Reader chapter navigation">{nav_markup}</nav></details>{page_markup}<div class="reading-end"><span>END OF THE FIRST EDITION</span><p>Keep what helps.</p><div class="download-links"><a href="/books/how-to-seduce-anyone.pdf" download="How_to_Seduce_Anyone.pdf">Download PDF ↓</a><a href="/books/how-to-seduce-anyone.epub" download="How_to_Seduce_Anyone.epub">Download EPUB ↓</a></div></div></main></div>
<script>const bar=document.getElementById('readerProgress');let scheduled=false;addEventListener('scroll',()=>{{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{{const max=document.documentElement.scrollHeight-innerHeight;bar.style.width=`${{max?scrollY/max*100:0}}%`;scheduled=false;}})}},{{passive:true}});</script>
</body></html>'''

OUTPUT.write_text(html_doc, encoding='utf-8')
print(f'Built {OUTPUT.name}: {len(book.PAGES)} complete manuscript pages, {len(html_doc):,} characters')
