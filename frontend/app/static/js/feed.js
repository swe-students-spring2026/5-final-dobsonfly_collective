'use strict';

const arena = document.getElementById('feedArena');
const spinner = document.getElementById('feedSpinner');

let profiles = [];
let currentPage = 0;
let hasMore = true;
let isFetching = false;
let activeSwiper = null;
let searchName = '';
let searchCity = '';
let searchTimeout = null;

// ── Initials helper ───────────────────────────────────────────────────────────
function initials(name) {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
}

// ── Score ring SVG ────────────────────────────────────────────────────────────
function scoreRing(score, userId) {
  const r = 32;
  // seed jitter from userId so the same card always shows the same %
  const seed = userId ? [...userId].reduce((a, c) => a + c.charCodeAt(0), 0) : 0;
  const jitter = ((seed % 21) - 10) / 100;
  const display = Math.min(0.99, Math.max(0.15, score + jitter + 0.30));
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - display);
  const pct = Math.round(display * 100);
  return `
    <div class="match-ring">
      <svg viewBox="0 0 70 70">
        <circle class="track" cx="35" cy="35" r="${r}"/>
        <circle class="progress" cx="35" cy="35" r="${r}"
                stroke-dasharray="${circ.toFixed(1)}"
                stroke-dashoffset="${offset.toFixed(1)}"/>
      </svg>
      <div class="score-text">
        ${pct}%<span class="score-label">match</span>
      </div>
    </div>`;
}

// ── Build a card element ──────────────────────────────────────────────────────
function buildCard(profile) {
  const card = document.createElement('div');
  card.className = 'swipe-card';
  card.dataset.userId = profile.user_id;

  const genres = (profile.top_genres || []).slice(0, 5)
    .map(g => `<span class="genre-tag">${g}</span>`).join('');
  const artists = (profile.top_artists || []).slice(0, 3)
    .map(a => a.name).join(', ');

  card.innerHTML = `
    <div class="overlay-like">LIKE</div>
    <div class="overlay-nope">NOPE</div>
    <div class="card-vinyl-section">
      <div class="vinyl">
        <div class="vinyl-label">${initials(profile.display_name)}</div>
      </div>
      <div class="waveform">
        ${Array.from({length: 8}, () => '<div class="waveform-bar"></div>').join('')}
      </div>
    </div>
    <div class="card-info">
      <div class="card-top-row">
        <div>
          <div class="card-name">${profile.display_name}, ${profile.age}</div>
          <div class="card-meta">${profile.city}</div>
        </div>
        ${scoreRing(profile.match_score || 0, profile.user_id)}
      </div>
      ${profile.bio ? `<div class="card-bio">${profile.bio}</div>` : ''}
      <div class="genre-list">${genres}</div>
      ${artists ? `<div class="artists-row"><strong>playing</strong>${artists}</div>` : ''}
    </div>`;

  return card;
}

// ── Render stack (up to 3 cards visible) ─────────────────────────────────────
function renderStack() {
  arena.querySelectorAll('.swipe-card').forEach(c => c.remove());
  const visible = profiles.slice(0, 3);

  if (visible.length === 0) {
    if (!hasMore) {
      const msg = (searchName || searchCity)
        ? `<h3>No results</h3><p>Try a different name or city.</p>`
        : `<h3>You've seen everyone</h3><p>Check back later or update your preferences in settings.</p>`;
      arena.innerHTML = `<div class="feed-empty">${msg}</div>`;
    }
    return;
  }

  // Render in reverse so first card is on top
  [...visible].reverse().forEach(p => {
    const card = buildCard(p);
    arena.prepend(card);
  });

  attachSwipe(arena.querySelector('.swipe-card'));

  // Pre-fetch when stack gets low
  if (profiles.length <= 2 && hasMore && !isFetching) fetchProfiles();
}

// ── Fetch profiles from proxy ─────────────────────────────────────────────────
function resetFeed() {
  profiles = [];
  currentPage = 0;
  hasMore = true;
  arena.querySelectorAll('.swipe-card').forEach(c => c.remove());
  arena.innerHTML = '<div class="spinner" id="feedSpinner"></div>';
  fetchProfiles();
}

function toggleSearch() {
  const panel = document.getElementById('searchPanel');
  const btn = document.getElementById('searchToggle');
  panel.classList.toggle('open');
  btn.classList.toggle('active');
}

function onSearchInput() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    const newName = document.getElementById('searchName').value.trim();
    const newCity = document.getElementById('searchCity').value.trim();
    if (newName !== searchName || newCity !== searchCity) {
      searchName = newName;
      searchCity = newCity;
      resetFeed();
    }
  }, 400);
}

function clearSearch() {
  document.getElementById('searchName').value = '';
  document.getElementById('searchCity').value = '';
  searchName = '';
  searchCity = '';
  resetFeed();
}

async function fetchProfiles() {
  if (isFetching) return;
  isFetching = true;
  try {
    const params = new URLSearchParams({ page: currentPage });
    if (searchName) params.set('search', searchName);
    if (searchCity) params.set('city', searchCity);
    const res = await fetch(`/api/feed?${params}`, { credentials: 'include' });
    if (res.status === 403) {
      arena.innerHTML = `
        <div class="feed-empty">
          <h3>Connect Spotify first</h3>
          <p>Your feed unlocks once your listening data is synced.</p>
          <a href="/spotify/connect" class="btn btn-spotify" style="margin-top:16px;">Connect Spotify</a>
        </div>`;
      return;
    }
    const data = await res.json();
    profiles.push(...(data.profiles || []));
    hasMore = data.has_more || false;
    currentPage++;
    renderStack();
  } catch (e) {
    arena.innerHTML = `<div class="feed-empty"><h3>Couldn't load feed</h3><p>Check your connection and refresh.</p></div>`;
  } finally {
    isFetching = false;
    spinner.style.display = 'none';
  }
}

// ── Swipe logic ───────────────────────────────────────────────────────────────
function attachSwipe(card) {
  if (!card) return;
  activeSwiper = new SwipeCard(card, () => topProfile(), onSwipeAction);
}

function topProfile() {
  return profiles[0];
}

class SwipeCard {
  constructor(el, getProfile, onSwipe) {
    this.el = el;
    this.getProfile = getProfile;
    this.onSwipe = onSwipe;
    this.startX = 0;
    this.startY = 0;
    this.dx = 0;
    this.dy = 0;
    this.active = false;

    this._onMouseDown = e => { e.preventDefault(); this.start(e.clientX, e.clientY); };
    this._onMouseMove = e => this.move(e.clientX, e.clientY);
    this._onMouseUp   = () => this.end();
    this._onTouchStart = e => this.start(e.touches[0].clientX, e.touches[0].clientY);
    this._onTouchMove  = e => { e.preventDefault(); this.move(e.touches[0].clientX, e.touches[0].clientY); };
    this._onTouchEnd   = () => this.end();

    el.addEventListener('mousedown', this._onMouseDown);
    document.addEventListener('mousemove', this._onMouseMove);
    document.addEventListener('mouseup', this._onMouseUp);
    el.addEventListener('touchstart', this._onTouchStart, { passive: true });
    el.addEventListener('touchmove', this._onTouchMove, { passive: false });
    el.addEventListener('touchend', this._onTouchEnd);
  }

  destroy() {
    this.el.removeEventListener('mousedown', this._onMouseDown);
    document.removeEventListener('mousemove', this._onMouseMove);
    document.removeEventListener('mouseup', this._onMouseUp);
    this.el.removeEventListener('touchstart', this._onTouchStart);
    this.el.removeEventListener('touchmove', this._onTouchMove);
    this.el.removeEventListener('touchend', this._onTouchEnd);
  }

  start(x, y) {
    this.active = true;
    this.startX = x; this.startY = y;
    this.dx = 0; this.dy = 0;
    this.el.style.transition = 'none';
    this.el.classList.add('is-dragging');
  }

  move(x, y) {
    if (!this.active) return;
    this.dx = x - this.startX;
    this.dy = y - this.startY;
    const rot = this.dx * 0.07;
    this.el.style.transform = `translate(${this.dx}px, ${this.dy * 0.25}px) rotate(${rot}deg)`;

    const like = this.el.querySelector('.overlay-like');
    const nope = this.el.querySelector('.overlay-nope');
    const thr = 60;
    if (this.dx > thr) {
      like.style.opacity = Math.min((this.dx - thr) / 80, 1);
      nope.style.opacity = 0;
    } else if (this.dx < -thr) {
      nope.style.opacity = Math.min((-this.dx - thr) / 80, 1);
      like.style.opacity = 0;
    } else {
      like.style.opacity = 0;
      nope.style.opacity = 0;
    }
  }

  end() {
    if (!this.active) return;
    this.active = false;
    this.el.classList.remove('is-dragging');
    const thr = 100;
    if (this.dx > thr) {
      this.fling('right');
    } else if (this.dx < -thr) {
      this.fling('left');
    } else {
      this.el.style.transition = 'transform 0.4s cubic-bezier(0.175,0.885,0.32,1.275)';
      this.el.style.transform = '';
      this.el.querySelector('.overlay-like').style.opacity = 0;
      this.el.querySelector('.overlay-nope').style.opacity = 0;
    }
  }

  fling(dir) {
    this.destroy();
    const vx = dir === 'right' ? window.innerWidth + 300 : -(window.innerWidth + 300);
    this.el.style.transition = 'transform 0.38s ease-out, opacity 0.38s ease-out';
    this.el.style.transform = `translate(${vx}px, ${this.dy * 0.5}px) rotate(${dir === 'right' ? 35 : -35}deg)`;
    this.el.style.opacity = '0';
    setTimeout(() => {
      this.el.remove();
      this.onSwipe(dir === 'right' ? 'like' : 'skip', this.getProfile());
    }, 380);
  }
}

// ── Swipe action handler ──────────────────────────────────────────────────────
async function onSwipeAction(action, profile) {
  profiles.shift();
  renderStack();

  if (action === 'like' && profile) {
    try {
      const res = await fetch(`/api/likes/${profile.user_id}`, {
        method: 'POST',
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        if (data.matched) showMatchNotif(profile);
      } else if (res.status === 429) {
        showToast("Daily like limit reached — come back tomorrow.");
      }
    } catch (_) {}
  }
}

// ── Button triggers ───────────────────────────────────────────────────────────
function triggerLike() {
  const top = arena.querySelector('.swipe-card');
  if (!top || !activeSwiper) return;
  activeSwiper.fling('right');
}

function triggerSkip() {
  const top = arena.querySelector('.swipe-card');
  if (!top || !activeSwiper) return;
  activeSwiper.fling('left');
}

// ── Match notification ────────────────────────────────────────────────────────
function showMatchNotif(profile) {
  document.getElementById('matchSubtitle').textContent =
    `You and ${profile.display_name} both vibed on this.`;

  const vinyls = document.getElementById('matchVinyls');
  vinyls.innerHTML = `
    <div class="vinyl" style="width:80px;height:80px;">
      <div class="vinyl-label" style="width:34px;height:34px;font-size:0.8rem;">
        You
      </div>
    </div>
    <div class="vinyl" style="width:80px;height:80px;margin-left:-16px;">
      <div class="vinyl-label" style="width:34px;height:34px;font-size:0.8rem;">
        ${initials(profile.display_name)}
      </div>
    </div>`;

  document.getElementById('matchBackdrop').classList.add('visible');
}

function closeMatchNotif() {
  document.getElementById('matchBackdrop').classList.remove('visible');
}

// ── Boot ──────────────────────────────────────────────────────────────────────
fetchProfiles();
