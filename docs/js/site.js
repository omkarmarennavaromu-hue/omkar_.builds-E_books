(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Navigation, progress and subtle movement driven by the page scroll.
  const header = $('#siteHeader');
  const progress = $('#scrollProgress');
  const menuButton = $('#menuToggle');
  const menu = $('#mobileNav');
  const navSections = $$('.desktop-nav a').map(link => ({link, section:$(link.getAttribute('href'))}));
  let scheduled = false;
  function onScroll() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      const y = scrollY;
      header.classList.toggle('is-scrolled', y > 30);
      const available = document.documentElement.scrollHeight - innerHeight;
      progress.style.width = `${available > 0 ? (y / available) * 100 : 0}%`;
      let current = null;
      for (const item of navSections) {
        if (item.section.getBoundingClientRect().top <= innerHeight * .45) current = item.link;
      }
      navSections.forEach(item => item.link.classList.toggle('is-active', item.link === current));
      if (!reducedMotion && y < innerHeight * 1.5) {
        document.documentElement.style.setProperty('--orbit-shift', `${Math.min(140, y * .15)}px`);
        document.documentElement.style.setProperty('--book-lift', `${Math.min(90, y * .12)}px`);
        document.documentElement.style.setProperty('--book-tilt', `${-4 + Math.min(8, y * .008)}deg`);
      }
      scheduled = false;
    });
  }
  addEventListener('scroll', onScroll, {passive:true});
  onScroll();
  function closeMenu() { menu.hidden = true; menuButton.setAttribute('aria-expanded', 'false'); menuButton.setAttribute('aria-label', 'Open menu'); }
  menuButton.addEventListener('click', () => {
    menu.hidden = !menu.hidden;
    menuButton.setAttribute('aria-expanded', String(!menu.hidden));
    menuButton.setAttribute('aria-label', menu.hidden ? 'Open menu' : 'Close menu');
  });
  $$('a', menu).forEach(link => link.addEventListener('click', closeMenu));
  addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });
  addEventListener('resize', () => { if (innerWidth > 950) closeMenu(); });

  // A subtle pointer accent, purely decorative; touch and reduced-motion users skip it.
  if (!reducedMotion && matchMedia('(hover:hover) and (pointer:fine)').matches) {
    const ring = $('#cursorRing');
    const dot = $('#cursorDot');
    let x = 0, y = 0, targetX = 0, targetY = 0, animating = false;
    function moveRing() {
      x += (targetX - x) * .3;
      y += (targetY - y) * .3;
      ring.style.transform = `translate3d(${x}px,${y}px,0)`;
      if (Math.abs(x-targetX) + Math.abs(y-targetY) > .4) requestAnimationFrame(moveRing);
      else animating = false;
    }
    addEventListener('pointermove', event => {
      document.body.classList.add('has-pointer');
      targetX = event.clientX; targetY = event.clientY;
      dot.style.transform = `translate3d(${targetX}px,${targetY}px,0)`;
      if (!animating) { animating = true; requestAnimationFrame(moveRing); }
    }, {passive:true});
    document.addEventListener('pointerover', event => {
      ring.classList.toggle('is-hot', !!event.target.closest('a,button,input,textarea'));
    });
    addEventListener('blur', () => document.body.classList.remove('has-pointer'));
  }

  if ('IntersectionObserver' in window && !reducedMotion) {
    const revealObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          revealObserver.unobserve(entry.target);
        }
      }
    }, {rootMargin:'0px 0px -35px 0px', threshold:0.08});
    $$('.reveal').forEach(el => revealObserver.observe(el));
  } else {
    $$('.reveal').forEach(el => el.classList.add('is-visible'));
  }

  // Actual pages extracted from the published PDF change as chapters scroll by.
  const preview = $('#pagePreview');
  const caption = $('#pageCaption');
  const chapters = $$('.chapter-item');
  let activeChapter = -1;
  function setChapter(index) {
    if (index === activeChapter || index < 0 || index >= chapters.length) return;
    activeChapter = index;
    chapters.forEach((el, i) => el.classList.toggle('is-active', i === index));
    preview.classList.add('switching');
    const item = chapters[index];
    const image = new Image();
    image.onload = () => {
      if (activeChapter !== index) return;
      preview.src = item.dataset.image;
      preview.alt = item.dataset.alt;
      caption.textContent = item.dataset.caption;
      requestAnimationFrame(() => preview.classList.remove('switching'));
    };
    image.onerror = () => preview.classList.remove('switching');
    image.src = item.dataset.image;
  }
  setChapter(0);
  if ('IntersectionObserver' in window) {
    const chapterObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) setChapter(chapters.indexOf(entry.target));
      });
    }, {rootMargin:'-25% 0px -47% 0px', threshold:0});
    chapters.forEach(el => chapterObserver.observe(el));
  }

  // The complete manuscript reads responsively in-page; the link still works without JS.
  const reader = $('#readerDialog');
  const frame = $('#readerFrame');
  $('#openReader').addEventListener('click', event => {
    if (typeof reader.showModal !== 'function') return;
    event.preventDefault();
    if (!reader.open) reader.showModal();
    frame.src = 'reader.html';
  });
  $('#closeReader').addEventListener('click', () => reader.close());
  reader.addEventListener('click', event => { if (event.target === reader) reader.close(); });
  reader.addEventListener('close', () => { frame.src = 'about:blank'; });

  const video = $('#promoVideo');
  video.controls = false; // Native controls remain if JavaScript is unavailable.
  const playButton = $('#videoPlay');
  playButton.addEventListener('click', async () => {
    video.muted = false; // Explicit user gesture: the original soundtrack plays.
    video.controls = true;
    playButton.classList.add('is-hidden');
    try { await video.play(); }
    catch { playButton.classList.remove('is-hidden'); }
  });
  video.addEventListener('ended', () => { video.controls = false; playButton.classList.remove('is-hidden'); });

  // Pages has no API. No feedback data is requested or simulated.
})();
