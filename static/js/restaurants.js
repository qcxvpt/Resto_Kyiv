const map = L.map('map').setView([50.4501, 30.5234], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

function pizzaIcon() {
  return L.divIcon({
    className: '',
    html: '<div style="font-size:22px;line-height:1;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35));cursor:pointer;">🍕</div>',
    iconSize: [26, 26],
    iconAnchor: [13, 26],
    popupAnchor: [0, -26]
  });
}

const markers = [];
let restaurantsData = [];
const itemsPerPage = 10;
let currentPage = 1;
let highlightedIndex = null;
let currentRestoId = null;
let currentRestoData = null;

const t = () => window.i18n || {};

function starsHtml(avg, count) {
  if (avg === null) return `<span style="color:#94a3b8;font-size:.85rem;">${t().noRatings||'No ratings'}</span>`;
  const full = Math.round(avg);
  return `<span style="color:#f59e0b;font-size:1rem;">${'★'.repeat(full)}${'☆'.repeat(5-full)}</span>
          <span style="color:#64748b;font-size:.82rem;margin-left:.25rem;">${avg} (${count})</span>`;
}

function buildDetailsHtml(r) {
  const link = r.url ? `<a class="exchange-link" href="${r.url}" target="_blank" rel="noopener noreferrer">${t().openSite||'Open site'}</a>` : '';
  return `<div class="rates-block">
    ${link}
    <div style="font-size:.85rem;color:#475569;margin-bottom:.3rem;">📍 ${r.address}</div>
    <div style="font-size:.85rem;color:#475569;margin-bottom:.5rem;">🍴 ${r.cuisine}</div>
    <div style="margin-bottom:.6rem;">${starsHtml(r.avg_rating, r.review_count)}</div>
    <button class="review-open-btn" onclick="openReviewModal(${r.id}, '${r.name.replace(/'/g,"\\'")}')">
      💬 ${t().reviews||'Reviews'} (${r.review_count})
    </button>
  </div>`;
}

async function loadData() {
  try {
    const res = await fetch('/api/restaurants');
    const data = await res.json();
    restaurantsData = data.map((r, i) => ({ ...r, __index: i }));
    renderAllMarkers();
    renderList();
    if (currentRestoData) {
      const updated = restaurantsData.find(r => r.id === currentRestoData.id);
      if (updated) showInfoPanel(updated);
    }
  } catch (e) {}
}

function renderAllMarkers() {
  markers.forEach(m => map.removeLayer(m));
  markers.length = 0;
  restaurantsData.forEach(r => {
    const lat = Number(r.lat), lng = Number(r.lng);
    if (!isFinite(lat) || !isFinite(lng)) return;
    const marker = L.marker([lat, lng], { icon: pizzaIcon() })
      .addTo(map)
      .bindPopup(`<b>${r.name}</b><br><span style="color:#64748b;font-size:.85rem;">${r.cuisine}</span>`);
    marker.restoIndex = r.__index;
    marker.on('click', () => {
      const page = Math.floor(r.__index / itemsPerPage) + 1;
      if (page !== currentPage) currentPage = page;
      highlightedIndex = r.__index;
      renderList();
      map.setView([lat, lng], 15);
      markers.forEach(m => m.closePopup());
      marker.openPopup();
      showInfoPanel(r);
    });
    markers.push(marker);
  });
}

function renderList() {
  const section = document.getElementById('buttonsSection');
  section.innerHTML = '';
  const filter = document.getElementById('sortField').value.toLowerCase();
  const filtered = restaurantsData.filter(r =>
    r.name.toLowerCase().includes(filter) || r.cuisine.toLowerCase().includes(filter)
  );
  if (highlightedIndex !== null && !filtered.some(r => r.__index === highlightedIndex)) highlightedIndex = null;
  const total = Math.max(1, Math.ceil(filtered.length / itemsPerPage));
  if (currentPage > total) currentPage = total;
  const page = filtered.slice((currentPage-1)*itemsPerPage, currentPage*itemsPerPage);

  page.forEach(r => {
    const btn = document.createElement('button');
    btn.className = 'exchangeButton';
    btn.dataset.index = r.__index;
    btn.innerHTML = `<div class="exchangeContent">
      <div class="exchangeIcon">🍕</div>
      <div class="exchangeName">${r.name}<br><span style="font-size:.75rem;font-weight:400;color:#64748b;">${r.cuisine}</span></div>
      <span class="toggleArrow" style="margin-left:auto;cursor:pointer;">▶</span>
    </div>`;
    const arrow = btn.querySelector('.toggleArrow');
    const details = document.createElement('div');
    details.className = 'exchange-details';
    details.innerHTML = buildDetailsHtml(r);

    btn.addEventListener('click', e => {
      if (e.target === arrow) return;
      collapseAll();
      arrow.textContent = '▼';
      details.classList.add('show');
      btn.classList.add('active');
      highlightedIndex = r.__index;
      flyTo(r);
    });
    arrow.addEventListener('click', e => {
      e.stopPropagation();
      const showing = details.classList.contains('show');
      collapseAll();
      if (!showing) {
        details.classList.add('show');
        arrow.textContent = '▼';
        btn.classList.add('active');
        highlightedIndex = r.__index;
      } else {
        highlightedIndex = null;
      }
    });
    if (highlightedIndex === r.__index) {
      btn.classList.add('active');
      arrow.textContent = '▼';
      details.classList.add('show');
      setTimeout(() => btn.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50);
    }
    section.appendChild(btn);
    section.appendChild(details);
  });
  renderPagination(filtered.length);
}

function collapseAll() {
  document.querySelectorAll('.toggleArrow').forEach(a => a.textContent = '▶');
  document.querySelectorAll('.exchange-details').forEach(d => d.classList.remove('show'));
  document.querySelectorAll('.exchangeButton.active').forEach(b => b.classList.remove('active'));
}

function flyTo(r) {
  map.setView([r.lat, r.lng], 15);
  const marker = markers.find(m => m.restoIndex === r.__index);
  if (marker) { markers.forEach(m => m.closePopup()); marker.openPopup(); }
  showInfoPanel(r);
}

function getKyivHour() {
  const now = new Date();
  return parseInt(now.toLocaleString('en-GB', { timeZone: 'Europe/Kiev', hour: 'numeric', hour12: false }), 10);
}

function getKyivDayOfWeek() {
  const now = new Date();
  const dayStr = now.toLocaleString('en-GB', { timeZone: 'Europe/Kiev', weekday: 'short' });
  return { Sun:0, Mon:1, Tue:2, Wed:3, Thu:4, Fri:5, Sat:6 }[dayStr] ?? new Date().getDay();
}

function isOpenNow(r) {
  if (!r.hours) return null;
  const hour = getKyivHour();
  const dow = getKyivDayOfWeek();
  const sched = r.schedule || 'all';
  if (sched === 'mon-fri' && (dow === 0 || dow === 6)) return false;
  if (sched === 'mon-sat' && dow === 0) return false;
  return hour >= r.hours[0] && hour < r.hours[1];
}

function getDesc(r) {
  const lang = localStorage.getItem('lang') || 'uk';
  if (lang !== 'uk' && r['desc_' + lang]) return r['desc_' + lang];
  return r.desc || '';
}

function showInfoPanel(r) {
  currentRestoData = r;
  const panel = document.getElementById('restoInfoPanel');
  if (!panel) return;
  const tr = t();

  document.getElementById('info-name').textContent    = r.name;
  document.getElementById('info-cuisine').textContent = '🍴 ' + r.cuisine;
  document.getElementById('info-address').textContent = '📍 ' + r.address;
  document.getElementById('info-desc').textContent    = getDesc(r);

  const open = isOpenNow(r);
  const statusEl = document.getElementById('info-status');
  if (open === null) {
    statusEl.innerHTML = '';
  } else if (open) {
    statusEl.innerHTML = `<span class="status-open">${tr.statusOpen||'🟢 Open'}</span><span class="status-sub"> · ${tr.closesAt||'Closes at'} ${r.hours[1]}:00</span>`;
  } else {
    statusEl.innerHTML = `<span class="status-closed">${tr.statusClosed||'🔴 Closed'}</span><span class="status-sub"> · ${tr.opensAt||'Opens at'} ${r.hours[0]}:00</span>`;
  }

  document.getElementById('info-hours').textContent = r.hours ? `${tr.hoursLabel||'Hours:'} ${r.hours[0]}:00 – ${r.hours[1]}:00` : '';
  const schedMap = { all: tr.scheduleAll, 'mon-fri': tr.scheduleMF, 'mon-sat': tr.scheduleMS };
  document.getElementById('info-schedule').textContent = schedMap[r.schedule] || tr.scheduleAll || '';

  panel.style.display = 'block';
}

function renderPagination(total) {
  const old = document.getElementById('paginationControls');
  if (old) old.remove();
  const pages = Math.ceil(total / itemsPerPage);
  if (pages <= 1) return;
  const div = document.createElement('div');
  div.id = 'paginationControls';
  div.style.cssText = 'margin-top:10px;display:flex;justify-content:center;gap:10px;';
  const prev = document.createElement('button');
  prev.textContent = t().prev || '← Prev';
  prev.disabled = currentPage === 1;
  prev.onclick = () => { if (currentPage > 1) { currentPage--; highlightedIndex = null; renderList(); }};
  const next = document.createElement('button');
  next.textContent = t().next || 'Next →';
  next.disabled = currentPage === pages;
  next.onclick = () => { if (currentPage < pages) { currentPage++; highlightedIndex = null; renderList(); }};
  div.appendChild(prev);
  div.appendChild(next);
  document.getElementById('buttonsSection').appendChild(div);
}

document.getElementById('sortField').addEventListener('input', () => {
  currentPage = 1; highlightedIndex = null; renderList();
});

let editingReviewId = null;

function setStars(val) {
  document.getElementById('selectedRating').value = val;
  document.querySelectorAll('.star').forEach(s =>
    s.textContent = parseInt(s.dataset.val) <= val ? '★' : '☆'
  );
}

async function openReviewModal(id, name) {
  currentRestoId  = id;
  editingReviewId = null;
  document.getElementById('reviewModalTitle').textContent = `💬 ${t().reviews||'Reviews'}: ${name}`;
  resetReviewForm();
  const warn = document.getElementById('one-review-warning');
  if (warn) warn.style.display = 'none';
  document.getElementById('reviewModal').style.display = 'flex';
  loadReviews(id);
  if (LOGGED_IN) {
    try {
      const res  = await fetch(`/api/my-review/${id}`);
      const mine = await res.json();
      if (mine) {
        editingReviewId = mine.id;
        document.getElementById('reviewText').value = mine.text;
        setStars(mine.rating);
        showEditMode(true);
        if (warn) {
          warn.textContent = t().oneReviewWarning || '⚠️ You already left a review. Edit or delete it.';
          warn.style.display = 'block';
        }
      } else {
        showEditMode(false);
      }
    } catch(e) {}
  }
}

function resetReviewForm() {
  const txt = document.getElementById('reviewText');
  if (txt) txt.value = '';
  setStars(0);
  const err = document.getElementById('reviewError');
  if (err) err.textContent = '';
  const anonBox = document.getElementById('anonCheck');
  if (anonBox) anonBox.checked = false;
  showEditMode(false);
}

function showEditMode(isEdit) {
  const lbl = document.getElementById('form-mode-label');
  const btn = document.getElementById('submitReview');
  if (!lbl || !btn) return;
  if (isEdit) {
    lbl.textContent = t().editYourReview || '✏️ Edit your review:';
    lbl.style.color = '#1d4ed8';
    btn.textContent = t().saveReview || 'Save';
    btn.style.background = '#1d4ed8';
  } else {
    lbl.textContent = t().rateLabel || 'Your rating:';
    lbl.style.color = '';
    btn.textContent = t().sendReview || 'Submit';
    btn.style.background = '#e50914';
  }
}

async function loadReviews(id) {
  const list = document.getElementById('reviewsList');
  list.innerHTML = `<p style="color:#94a3b8;font-size:.85rem;">${t().loading||'Loading...'}</p>`;
  try {
    const res  = await fetch(`/api/reviews/${id}`);
    const data = await res.json();
    if (!data.length) {
      list.innerHTML = `<p style="color:#94a3b8;font-size:.85rem;">${t().noReviews||'No reviews yet.'}</p>`;
      return;
    }
    list.innerHTML = data.map(rv => `
      <div style="border-bottom:1px solid #e2e8f0;padding:.6rem 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem;">
          <span style="font-weight:600;color:${rv.anonymous ? '#94a3b8' : '#1e3a8a'};">${rv.anonymous ? (t().anonDisplay||'Anonymous') : rv.author}</span>
          <span style="color:#f59e0b;">${'★'.repeat(rv.rating)}${'☆'.repeat(5-rv.rating)}</span>
          ${rv.mine ? `
            <button onclick="prepareEdit(${rv.id},'${rv.text.replace(/'/g,'&#39;').replace(/"/g,'&quot;')}',${rv.rating})"
              style="background:none;border:1px solid #3b82f6;color:#3b82f6;border-radius:5px;padding:.15rem .45rem;cursor:pointer;font-size:.75rem;">✏️</button>
            <button onclick="deleteReview(${rv.id})"
              style="background:none;border:none;color:#e50914;cursor:pointer;font-size:.8rem;">✕</button>
          ` : ''}
        </div>
        <div style="font-size:.9rem;color:#374151;margin-top:.25rem;">${rv.text}</div>
        <div style="font-size:.72rem;color:#94a3b8;">${rv.created_at}</div>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<p style="color:#e50914;">${t().loadError||'Error.'}</p>`;
  }
}

function prepareEdit(id, text, rating) {
  editingReviewId = id;
  document.getElementById('reviewText').value = text;
  setStars(rating);
  showEditMode(true);
  document.getElementById('reviewText').focus();
}

async function deleteReview(id) {
  const token = await getCsrfToken();
  await fetch(`/api/reviews/${id}`, { method:'DELETE', headers:{'X-CSRFToken':token} });
  editingReviewId = null;
  resetReviewForm();
  const warn = document.getElementById('one-review-warning');
  if (warn) warn.style.display = 'none';
  loadReviews(currentRestoId);
  loadData();
}

async function getCsrfToken() {
  const r = await fetch('/api/csrf-token');
  const d = await r.json();
  return d.token;
}

document.getElementById('closeReviewModal').addEventListener('click', () => {
  document.getElementById('reviewModal').style.display = 'none';
});

document.querySelectorAll('.star').forEach(star => {
  star.addEventListener('click', () => setStars(parseInt(star.dataset.val)));
});

const submitBtn = document.getElementById('submitReview');
if (submitBtn) {
  submitBtn.addEventListener('click', async () => {
    const text   = document.getElementById('reviewText').value.trim();
    const rating = parseInt(document.getElementById('selectedRating').value);
    const errEl  = document.getElementById('reviewError');
    errEl.textContent = '';
    if (!text || text.length < 3) { errEl.textContent = t().reviewShort || 'Too short.'; return; }
    if (!rating)                  { errEl.textContent = t().chooseRating || 'Choose rating.'; return; }
    const token = await getCsrfToken();
    let res;
    if (editingReviewId) {
      res = await fetch(`/api/reviews/${editingReviewId}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json', 'X-CSRFToken':token},
        body: JSON.stringify({text, rating, anonymous: document.getElementById('anonCheck')?.checked || false})
      });
    } else {
      res = await fetch('/api/reviews', {
        method: 'POST',
        headers: {'Content-Type':'application/json', 'X-CSRFToken':token},
        body: JSON.stringify({resto_id: currentRestoId, text, rating, anonymous: document.getElementById('anonCheck')?.checked || false})
      });
      if (res.status === 409) {
        const d = await res.json();
        editingReviewId = d.review_id;
        res = await fetch(`/api/reviews/${editingReviewId}`, {
          method: 'PUT',
          headers: {'Content-Type':'application/json', 'X-CSRFToken':token},
          body: JSON.stringify({text, rating, anonymous: document.getElementById('anonCheck')?.checked || false})
        });
      }
    }
    if (res.ok) {
      editingReviewId = null;
      resetReviewForm();
      const warn = document.getElementById('one-review-warning');
      if (warn) warn.style.display = 'none';
      loadReviews(currentRestoId);
      loadData();
    } else {
      const d = await res.json();
      errEl.textContent = d.error || 'Error.';
    }
  });
}

loadData();
