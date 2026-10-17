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
    frame.src = '/reader.html';
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

  // Only the server's real feedback appears here; no sample entries exist.
  const toastNode = $('#toast');
  let toastTimer;
  function toast(message) {
    toastNode.textContent = message;
    toastNode.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastNode.classList.remove('show'), 4200);
  }
  async function api(path, payload) {
    const options = {credentials:'same-origin', cache:'no-store'};
    if (payload !== undefined) {
      options.method = 'POST';
      options.headers = {'Content-Type':'application/json'};
      options.body = JSON.stringify(payload);
    }
    const response = await fetch(path, options);
    let result;
    try { result = await response.json(); }
    catch { throw Error('The server did not return a readable response.'); }
    if (!response.ok) throw Error(result.error || 'Could not save your response.');
    return result;
  }

  const stars = $$('.star-picker button');
  const ratingNote = $('#yourRating');
  const reviewForm = $('#reviewForm');
  const reviewStatus = $('#reviewStatus');
  let myRating = null;
  let myReaction = null;
  let submittingRating = false;
  let submittingReaction = false;
  function renderStars(value) {
    stars.forEach((button, i) => {
      button.classList.toggle('is-selected', !!value && i < value);
      button.setAttribute('aria-pressed', String(i + 1 === value));
    });
  }
  function dateText(value) {
    try { return new Intl.DateTimeFormat('en', {day:'numeric', month:'short', year:'numeric'}).format(new Date(value)); }
    catch { return ''; }
  }
  function makeReview(item) {
    const article = document.createElement('article');
    article.className = 'review-item';
    const head = document.createElement('div');
    head.className = 'review-item-head';
    const author = document.createElement('strong');
    author.textContent = item.display_name;
    const date = document.createElement('time');
    date.dateTime = item.created_at;
    date.textContent = dateText(item.created_at);
    head.append(author, date);
    const starline = document.createElement('div');
    starline.className = 'review-stars';
    starline.setAttribute('aria-label', `${item.stars} out of 5 stars`);
    starline.textContent = '★'.repeat(item.stars) + '☆'.repeat(5 - item.stars);
    const body = document.createElement('p');
    body.textContent = item.body; // Never inject visitor text as HTML.
    article.append(head, starline, body);
    return article;
  }
  function renderFeedback(data) {
    const count = Number(data.ratingCount) || 0;
    const average = Number(data.averageRating) || 0;
    const mine = data.yours || {};
    myRating = mine.rating || null;
    myReaction = mine.reaction || null;
    $('#averageRating').textContent = count ? average.toFixed(1) : '—';
    const starline = $('.rating-stars');
    starline.textContent = count ? '★'.repeat(Math.round(average)) + '☆'.repeat(5 - Math.round(average)) : '☆☆☆☆☆';
    starline.setAttribute('aria-label', count ? `Average ${average.toFixed(1)} out of 5 stars` : 'No ratings yet');
    $('#ratingCount').textContent = count ? `Based on ${count} ${count === 1 ? 'rating' : 'ratings'}` : 'No ratings yet. Be the first.';
    for (let score = 1; score <= 5; score++) {
      const row = $(`.rating-bars [data-star="${score}"]`);
      const n = Number((data.distribution || {})[score] || 0);
      $('i', row).style.width = `${count ? n / count * 100 : 0}%`;
      $('.bar-number', row).textContent = n;
    }
    $('#likeCount').textContent = Number(data.likes) || 0;
    $('#dislikeCount').textContent = Number(data.dislikes) || 0;
    $('#likeButton').setAttribute('aria-pressed', String(myReaction === 'like'));
    $('#dislikeButton').setAttribute('aria-pressed', String(myReaction === 'dislike'));
    renderStars(myRating);
    ratingNote.textContent = myRating ? `You rated this ${myRating} of 5. Choose another star to update it.` : 'Choose a star to leave the first honest rating.';
    const total = Number(data.reviewCount) || 0;
    $('#reviewCount').textContent = `${total} PUBLISHED ${total === 1 ? 'REVIEW' : 'REVIEWS'}`;
    const list = $('#reviewList');
    list.replaceChildren();
    const reviews = data.reviews || [];
    if (!reviews.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-reviews';
      empty.innerHTML = '<span class="empty-mark" aria-hidden="true">“</span><h4>No published reviews yet.</h4><p>When readers share their thoughts and they’re approved, they’ll appear here.</p>';
      list.append(empty);
    } else {
      reviews.forEach(item => list.append(makeReview(item)));
    }
    const locked = mine.reviewStatus === 'pending' || mine.reviewStatus === 'approved';
    $$('input, textarea, button', reviewForm).forEach(el => el.disabled = locked);
    if (locked) {
      reviewStatus.textContent = mine.reviewStatus === 'pending' ? 'Your review has been received and is awaiting approval. Thank you.' : 'Your review is published. Thank you for sharing it.';
    } else if (mine.reviewStatus === 'rejected') {
      reviewStatus.textContent = 'Your previous review was not approved. You may edit and submit another.';
    }
  }
  async function loadFeedback() {
    try { renderFeedback(await api('/api/feedback')); }
    catch (error) {
      ratingNote.textContent = 'Feedback is temporarily unavailable. Please try again later.';
      reviewStatus.textContent = 'The feedback service could not be reached.';
      console.warn(error);
    }
  }
  stars.forEach(button => button.addEventListener('click', async () => {
    if (submittingRating) return;
    submittingRating = true;
    try {
      renderFeedback(await api('/api/rating', {stars:Number(button.dataset.stars)}));
      toast('Your rating has been saved. Thank you!');
    } catch (error) { toast(error.message); }
    finally { submittingRating = false; }
  }));
  ['like', 'dislike'].forEach(reaction => {
    $(`#${reaction}Button`).addEventListener('click', async () => {
      if (submittingReaction) return;
      submittingReaction = true;
      const selection = myReaction === reaction ? null : reaction;
      try {
        renderFeedback(await api('/api/reaction', {reaction:selection}));
        toast(selection ? 'Your response has been saved.' : 'Your response has been removed.');
      } catch (error) { toast(error.message); }
      finally { submittingReaction = false; }
    });
  });
  $('#reviewText').addEventListener('input', event => {
    $('#charCount').textContent = `${event.target.value.length} / 1,000`;
  });
  reviewForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!myRating) {
      reviewStatus.textContent = 'Please choose a star rating above before submitting your review.';
      stars[0].focus();
      return;
    }
    const form = new FormData(reviewForm);
    const text = String(form.get('text') || '').trim();
    if (text.length < 20 || text.length > 1000) {
      reviewStatus.textContent = 'Write a review between 20 and 1,000 characters.';
      $('#reviewText').focus();
      return;
    }
    const submit = $('#submitReview');
    submit.disabled = true;
    reviewStatus.textContent = 'Sending your review…';
    try {
      const result = await api('/api/review', {name:String(form.get('name') || '').trim(), text, stars:myRating});
      reviewForm.reset();
      $('#charCount').textContent = '0 / 1,000';
      renderFeedback(result);
      toast('Thank you. Your review is awaiting approval.');
    } catch (error) {
      submit.disabled = false;
      reviewStatus.textContent = error.message;
    }
  });
  loadFeedback();
})();
