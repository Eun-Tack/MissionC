/* ── Radial Command Palette V1.5 ─────────────────────────────────────
   FR-RADIAL-01~05  |  ADR-011  |  BR-RADIAL-01~42
   Dependencies: 0 (native browser APIs only)
   ──────────────────────────────────────────────────────────────── */

const SLICES = [
  { id: 0, angle: -90,  symbol: '📥', label: '캡처',     shortcut: 'c', arrowKey: 'ArrowUp',    pattern: 'inline-form', formType: 'capture'  },
  { id: 1, angle: -45,  symbol: '🔍', label: '검색',     shortcut: 's',                          pattern: 'inline-form', formType: 'search'   },
  { id: 2, angle:   0,  symbol: '📅', label: '오늘',     shortcut: 't', arrowKey: 'ArrowRight',  pattern: 'route',       href: '/'            },
  { id: 3, angle:  45,  symbol: '🪟', label: '컨텍스트', shortcut: 'x',                          pattern: 'expand'                           },
  { id: 4, angle:  90,  symbol: '🌙', label: '회고',     shortcut: 'r', arrowKey: 'ArrowDown',   pattern: 'route',       hrefFn: 'review'     },
  { id: 5, angle: 135,  symbol: '🕘', label: '어제',     shortcut: 'y',                          pattern: 'modal',       modalId: 'yesterday' },
  { id: 6, angle: 180,  symbol: '🗂', label: '프로젝트', shortcut: 'p', arrowKey: 'ArrowLeft',   pattern: 'route',       href: '/hierarchy'   },
  { id: 7, angle: -135, symbol: '🎙', label: '음성',     shortcut: 'v',                          pattern: 'modal',       modalId: 'voice'     },
];

const ARROW_TO_IDX = {
  'ArrowUp': 0, 'ArrowRight': 2, 'ArrowDown': 4, 'ArrowLeft': 6,
};

/* SVG geometry constants */
const CX = 240, CY = 240, R_OUTER = 240, R_INNER = 80, LABEL_R = 165;

class RadialPalette {
  constructor() {
    this.root = document.getElementById('radial-root');
    if (!this.root) return;

    this.open        = false;
    this.focusedIdx  = null;
    this._searchTimer = null;
    this._searchResults = [];
    this._searchSel  = 0;
    this._inputListenerAdded = false;

    this._buildSlices();
    this._buildLabels();
    this._bindGlobalKeys();
    this._bindInternalEvents();
  }

  /* ── DOM construction ──────────────────────────────────────── */
  _buildSlices() {
    const svg = document.getElementById('radial-svg');
    SLICES.forEach((s, i) => {
      const a1 = _deg(s.angle);
      const a2 = _deg(s.angle + 45);

      const d = [
        `M ${_px(CX, R_INNER, a1)} ${_py(CY, R_INNER, a1)}`,
        `L ${_px(CX, R_OUTER, a1)} ${_py(CY, R_OUTER, a1)}`,
        `A ${R_OUTER} ${R_OUTER} 0 0 1 ${_px(CX, R_OUTER, a2)} ${_py(CY, R_OUTER, a2)}`,
        `L ${_px(CX, R_INNER, a2)} ${_py(CY, R_INNER, a2)}`,
        `A ${R_INNER} ${R_INNER} 0 0 0 ${_px(CX, R_INNER, a1)} ${_py(CY, R_INNER, a1)}`,
        'Z',
      ].join(' ');

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', d);
      path.setAttribute('class', 'radial-slice');
      path.setAttribute('id', `r-slice-${i}`);
      path.setAttribute('role', 'menuitem');
      path.setAttribute('aria-label', `${s.label}, ${s.shortcut} 키`);
      path.dataset.idx = i;
      svg.appendChild(path);
    });
  }

  _buildLabels() {
    const container = document.getElementById('radial-labels');
    SLICES.forEach((s, i) => {
      const mid = _deg(s.angle + 22.5);
      const lx  = (CX + LABEL_R * Math.cos(mid)) / 480 * 100;
      const ly  = (CY + LABEL_R * Math.sin(mid)) / 480 * 100;

      const el = document.createElement('div');
      el.className = 'radial-label';
      el.id = `r-label-${i}`;
      el.style.left = `${lx}%`;
      el.style.top  = `${ly}%`;
      el.innerHTML = `
        <span class="r-symbol">${s.symbol}</span>
        <span class="r-name">${s.label}</span>
        <span class="r-kbd">${s.shortcut}</span>`;
      container.appendChild(el);
    });
  }

  /* ── Key bindings (capture phase — BR-RADIAL-01~05) ────────── */
  _bindGlobalKeys() {
    document.addEventListener('keydown', (e) => {
      /* Cmd+K / Ctrl+K — toggle (BR-RADIAL-01,02,05) */
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        e.stopPropagation();
        if (this._isInputFocused()) document.activeElement.blur();
        this.toggle();
        return;
      }

      /* / — open when not in input (BR-RADIAL-02) */
      if (e.key === '/' && !this._isInputFocused() && !this.open) {
        e.preventDefault();
        this.show();
        return;
      }

      if (!this.open) return;

      /* Esc (BR-RADIAL-03) */
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        if (!document.getElementById('hub-form').hidden) {
          this._closeInlineForm();
        } else {
          this.hide();
        }
        return;
      }

      /* Keys when InlineForm is active — pass to input except special ones */
      if (!document.getElementById('hub-form').hidden) {
        if (e.key === 'Enter') { e.preventDefault(); this._submitInlineForm(); }
        if (e.key === 'ArrowDown') { e.preventDefault(); this._searchNav(1); }
        if (e.key === 'ArrowUp')   { e.preventDefault(); this._searchNav(-1); }
        return;
      }

      /* Arrow keys → slice highlight (BR-RADIAL-10) */
      if (ARROW_TO_IDX.hasOwnProperty(e.key)) {
        e.preventDefault();
        this._focus(ARROW_TO_IDX[e.key]);
        return;
      }

      /* Tab / Shift+Tab — cycle all 8 (BR-RADIAL-10) */
      if (e.key === 'Tab') {
        e.preventDefault();
        const cur = this.focusedIdx ?? -1;
        this._focus(e.shiftKey
          ? (cur <= 0 ? SLICES.length - 1 : cur - 1)
          : (cur >= SLICES.length - 1 ? 0 : cur + 1));
        return;
      }

      /* Enter → execute focused slice (BR-RADIAL-11) */
      if (e.key === 'Enter' && this.focusedIdx !== null) {
        e.preventDefault();
        this._execute(this.focusedIdx);
        return;
      }

      /* Single-char shortcuts — immediate execute (BR-RADIAL-12) */
      if (!e.isComposing && e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const idx = SLICES.findIndex(s => s.shortcut === e.key.toLowerCase());
        if (idx !== -1) { e.preventDefault(); this._execute(idx); }
      }
    }, true /* capture phase */);
  }

  _bindInternalEvents() {
    /* Overlay click → close (BR-RADIAL-04) */
    this.root.querySelector('.radial-overlay')
      .addEventListener('click', () => this.hide());

    const svg = document.getElementById('radial-svg');

    /* Slice click → execute (BR-RADIAL-13) */
    svg.addEventListener('click', (e) => {
      const path = e.target.closest('.radial-slice');
      if (path) this._execute(parseInt(path.dataset.idx));
    });

    /* Slice hover → focus */
    svg.addEventListener('mouseover', (e) => {
      const path = e.target.closest('.radial-slice');
      if (path) this._focus(parseInt(path.dataset.idx), false);
    });
  }

  /* ── Show / Hide (BR-RADIAL-40) ────────────────────────────── */
  show() {
    if (this.open) return;
    const t0 = performance.now();
    this.root.hidden = false;
    this.open = true;
    this.focusedIdx = null;
    this._applyContext();

    const wheel = this.root.querySelector('.radial-wheel');
    if (_reduced()) {
      wheel.style.opacity = '1';
    } else {
      wheel.animate(
        [{ transform: 'scale(0.72)', opacity: 0 }, { transform: 'scale(1)', opacity: 1 }],
        { duration: 120, easing: 'cubic-bezier(0.32, 0.72, 0, 1)', fill: 'both' }
      );
      /* Stagger slices */
      this.root.querySelectorAll('.radial-slice').forEach((el, i) =>
        el.animate(
          [{ opacity: 0 }, { opacity: 1 }],
          { duration: 80, delay: i * 10, fill: 'both' }
        )
      );
    }

    requestAnimationFrame(() => {
      const elapsed = performance.now() - t0;
      if (elapsed > 100) console.warn(`[Radial] slow open: ${elapsed.toFixed(1)}ms`);
    });
  }

  hide() {
    if (!this.open) return;
    this.open = false;
    this._clearFocus();
    this._closeInlineForm(true);

    const wheel = this.root.querySelector('.radial-wheel');
    if (_reduced()) {
      this.root.hidden = true;
    } else {
      wheel.animate(
        [{ transform: 'scale(1)', opacity: 1 }, { transform: 'scale(0.95)', opacity: 0 }],
        { duration: 100, easing: 'ease-out', fill: 'both' }
      ).finished.then(() => { this.root.hidden = true; });
    }
  }

  toggle() { this.open ? this.hide() : this.show(); }

  /* ── Slice focus ────────────────────────────────────────────── */
  _focus(idx, updateHub = true) {
    this._clearFocus();
    this.focusedIdx = idx;
    document.getElementById(`r-slice-${idx}`)?.classList.add('focused');
    document.getElementById(`r-label-${idx}`)?.classList.add('focused');

    if (updateHub) {
      const hl = document.getElementById('hub-label');
      hl.textContent = SLICES[idx].label;
      hl.classList.add('large');
    }
  }

  _clearFocus() {
    this.root.querySelectorAll('.radial-slice.focused, .radial-label.focused')
      .forEach(el => el.classList.remove('focused'));
    const hl = document.getElementById('hub-label');
    hl.textContent = 'Cmd+K';
    hl.classList.remove('large');
    this.focusedIdx = null;
  }

  /* ── Execute slice action ───────────────────────────────────── */
  _execute(idx) {
    const slice = SLICES[idx];
    const el = document.getElementById(`r-slice-${idx}`);

    /* BR-RADIAL-14: disabled → shake, ignore */
    if (el?.classList.contains('disabled')) {
      this._shake(el);
      return;
    }

    const ctx = this._context();
    switch (slice.pattern) {
      case 'route':       this._doRoute(slice, ctx);      break;
      case 'inline-form': this._doInlineForm(slice, ctx); break;
      case 'modal':       this._doModal(slice, ctx);      break;
      case 'expand':      this._doExpand(ctx);            break;
    }
  }

  /* route → navigate */
  _doRoute(slice, ctx) {
    this.hide();
    let href = slice.href;

    /* BR-RADIAL-22~23: review time-aware */
    if (slice.hrefFn === 'review') {
      href = new Date().getHours() < 12 ? '/morning' : '/evening';
    }
    setTimeout(() => { window.location.href = href; }, 90);
  }

  /* inline-form → morph hub (BR-RADIAL-30) */
  _doInlineForm(slice, ctx) {
    const hub   = document.getElementById('radial-hub');
    const hl    = document.getElementById('hub-label');
    const form  = document.getElementById('hub-form');
    const input = document.getElementById('hub-input');

    hl.hidden  = true;
    form.hidden = false;
    hub.classList.add('form-active');

    input.placeholder = slice.formType === 'capture' ? '새 항목 입력…' : '검색어 입력…';
    input.dataset.type      = slice.formType;
    input.dataset.projectId = ctx.projectId || '';
    input.value = '';

    if (!_reduced()) {
      form.animate(
        [{ opacity: 0, transform: 'scale(0.92)' }, { opacity: 1, transform: 'scale(1)' }],
        { duration: 200, easing: 'cubic-bezier(0.4, 0, 0.2, 1)', fill: 'both' }
      );
    }
    setTimeout(() => input.focus(), 60);

    /* Attach search listener once */
    if (!this._inputListenerAdded) {
      input.addEventListener('input', () => {
        if (input.dataset.type !== 'search') return;
        clearTimeout(this._searchTimer);
        const q = input.value.trim();
        if (q.length >= 2) {
          this._searchTimer = setTimeout(() => this._runSearch(q), 250);
        } else {
          this._clearSearchPanel();
        }
      });
      this._inputListenerAdded = true;
    }
  }

  _closeInlineForm(silent = false) {
    const hub   = document.getElementById('radial-hub');
    const hl    = document.getElementById('hub-label');
    const form  = document.getElementById('hub-form');
    const input = document.getElementById('hub-input');
    if (form.hidden) return;

    form.hidden = true;
    hl.hidden   = false;
    hl.textContent = 'Cmd+K';
    hl.classList.remove('large');
    hub.classList.remove('form-active');
    input.value = '';
    this._clearSearchPanel();
  }

  async _submitInlineForm() {
    const input = document.getElementById('hub-input');
    const val   = input.value.trim();

    /* BR-RADIAL-31: empty submit → error flash */
    if (!val) {
      input.classList.add('error');
      setTimeout(() => input.classList.remove('error'), 350);
      return;
    }

    if (input.dataset.type === 'capture') {
      await this._captureItem(val, input.dataset.projectId);
      this.hide();
      _toast('✓ 저장됨'); /* BR-RADIAL-32 */
    } else {
      /* Search: navigate with query */
      this.hide();
      setTimeout(() => { window.location.href = `/search?q=${encodeURIComponent(val)}`; }, 90);
    }
  }

  async _captureItem(title, projectId) {
    const fd = new FormData();
    fd.append('title', title);
    fd.append('type', 'task');
    if (projectId) fd.append('project_id', projectId);
    try {
      await fetch('/api/items', { method: 'POST', body: fd });
    } catch (err) {
      console.error('[Radial] capture failed', err);
    }
  }

  /* modal → delegate to existing mechanism */
  _doModal(slice, ctx) {
    this.hide();
    setTimeout(() => {
      if (slice.modalId === 'voice') {
        const btn = document.getElementById('voice-capture-btn');
        if (btn) btn.click();
        else window.dispatchEvent(new CustomEvent('mc:open-voice'));
      } else if (slice.modalId === 'yesterday') {
        this._openYesterdayModal();
      }
    }, 110);
  }

  /* expand → toggle context panel */
  _doExpand(ctx) {
    this.hide();
    setTimeout(() => {
      /* Project page drawer */
      const drawer = document.getElementById('proj-ctx-drawer');
      if (drawer) {
        if (typeof openProjCtx === 'function') openProjCtx(null);
        else drawer.classList.toggle('open');
        return;
      }
      /* Generic custom event — each page can handle */
      window.dispatchEvent(new CustomEvent('mc:toggle-context'));
    }, 80);
  }

  /* ── Search panel ───────────────────────────────────────────── */
  async _runSearch(q) {
    try {
      const res  = await fetch('/api/cmdk?q=' + encodeURIComponent(q));
      const data = await res.json();
      this._searchResults = data.results || [];
      this._searchSel = 0;
      this._renderSearchPanel();
    } catch (_) {
      this._searchResults = [];
    }
  }

  _renderSearchPanel() {
    const panel = document.getElementById('radial-search-panel');
    const rows  = this._searchResults;
    if (!rows.length) { panel.hidden = true; panel.innerHTML = ''; return; }

    panel.hidden = false;
    panel.innerHTML = rows.map((r, i) => `
      <div class="r-search-row ${i === 0 ? 'sel' : ''}" data-idx="${i}">
        <span>${r.icon || '·'}</span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis">${_esc(r.title)}</span>
        <span class="r-kind">${r.kind === 'item' ? '항목' : '프로젝트'}</span>
      </div>`).join('');

    panel.querySelectorAll('.r-search-row').forEach(el =>
      el.addEventListener('click', () => {
        const r = this._searchResults[parseInt(el.dataset.idx)];
        if (r?.url) { this.hide(); window.location.href = r.url; }
      })
    );
  }

  _clearSearchPanel() {
    this._searchResults = [];
    const panel = document.getElementById('radial-search-panel');
    panel.hidden = true;
    panel.innerHTML = '';
  }

  _searchNav(dir) {
    if (!this._searchResults.length) return;
    this._searchSel = Math.max(0, Math.min(this._searchResults.length - 1, this._searchSel + dir));
    document.querySelectorAll('#radial-search-panel .r-search-row').forEach((el, i) =>
      el.classList.toggle('sel', i === this._searchSel)
    );
  }

  /* ── Context awareness (FR-RADIAL-03) ─────────────────────── */
  _context() {
    const p = window.location.pathname;
    const m = p.match(/^\/project\/(\d+)/);
    return {
      projectId:  m ? m[1] : null,
      isInbox:    p === '/inbox',
      isReview:   p === '/morning' || p === '/evening',
      isCalendar: p === '/calendar',
    };
  }

  _applyContext() {
    const ctx = this._context();

    /* Capture label update (BR-RADIAL-24) */
    const cap = document.querySelector('#r-label-0 .r-name');
    if (cap) {
      if (ctx.isInbox)        cap.textContent = '분류로 점프';
      else if (ctx.projectId) cap.textContent = '캡처 (프로젝트)';
      else                    cap.textContent = '캡처';
    }

    /* Context slice (idx 3) — only enable on project pages with a toggleable drawer */
    const hasDrawer = !!document.getElementById('proj-ctx-drawer');
    this._setDisabled(3, !hasDrawer);

    /* Voice slice (idx 7) — check mic permission (BR-RADIAL-25) */
    if (navigator.permissions) {
      navigator.permissions.query({ name: 'microphone' })
        .then(p => this._setDisabled(7, p.state === 'denied'))
        .catch(() => {});
    }
  }

  _setDisabled(idx, disabled) {
    document.getElementById(`r-slice-${idx}`)?.classList.toggle('disabled', disabled);
    document.getElementById(`r-label-${idx}`)?.classList.toggle('disabled', disabled);
  }

  /* ── Yesterday modal ─────────────────────────────────────────── */
  _openYesterdayModal() {
    fetch('/api/items?limit=5&sort=updated')
      .then(r => r.json())
      .then(data => {
        const items = Array.isArray(data) ? data : (data.items || []);
        const overlay = document.createElement('div');
        overlay.style.cssText =
          'position:fixed;inset:0;z-index:3000;background:oklch(0% 0 0/0.5);' +
          'backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center';
        overlay.innerHTML = `
          <div style="background:var(--surface);border:1px solid var(--border);border-radius:16px;
                      padding:24px;width:min(400px,90vw);box-shadow:0 24px 64px oklch(0% 0 0/0.3)">
            <div style="font-size:16px;font-weight:700;margin-bottom:16px">최근 항목</div>
            ${items.length ? items.map(it => `
              <div style="display:flex;align-items:center;gap:10px;padding:9px 0;
                          border-bottom:1px solid var(--border)">
                <span class="mc-dot" data-status="${_esc(it.status)}"></span>
                <span style="font-size:14px">${_esc(it.title)}</span>
              </div>`).join('') :
              '<div style="color:var(--muted);font-size:13px">항목이 없습니다.</div>'}
            <button onclick="this.closest('[style]').remove()"
                    style="margin-top:16px;padding:8px 16px;background:var(--surface-2);
                           border:1px solid var(--border);border-radius:8px;
                           cursor:pointer;font-size:13px;font-family:inherit">닫기</button>
          </div>`;
        overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
        document.body.appendChild(overlay);
      })
      .catch(() => {});
  }

  /* ── Utilities ──────────────────────────────────────────────── */
  _shake(el) {
    el.classList.remove('shake');
    void el.offsetWidth;
    el.classList.add('shake');
    setTimeout(() => el.classList.remove('shake'), 250);
  }

  _isInputFocused() {
    const el = document.activeElement;
    return el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) && !el.readOnly;
  }
}

/* ── Pure helpers ───────────────────────────────────────────── */
function _deg(d)          { return d * Math.PI / 180; }
function _px(cx, r, rad)  { return +(cx + r * Math.cos(rad)).toFixed(3); }
function _py(cy, r, rad)  { return +(cy + r * Math.sin(rad)).toFixed(3); }
function _reduced()       { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; }
function _esc(s) {
  return String(s).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function _toast(msg) {
  const el = document.createElement('div');
  el.style.cssText =
    'position:fixed;bottom:88px;left:50%;transform:translateX(-50%);' +
    'background:var(--fg);color:var(--bg);padding:8px 18px;' +
    'border-radius:8px;font-size:13px;font-weight:500;z-index:9999;pointer-events:none';
  el.textContent = msg;
  document.body.appendChild(el);
  if (!_reduced()) {
    el.animate(
      [{ opacity: 0, transform: 'translateX(-50%) translateY(6px)' },
       { opacity: 1, transform: 'translateX(-50%) translateY(0)' }],
      { duration: 180, easing: 'ease-out', fill: 'both' }
    );
  }
  setTimeout(() => {
    if (!_reduced()) {
      el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 180, fill: 'both' })
        .finished.then(() => el.remove());
    } else {
      el.remove();
    }
  }, 1500);
}

/* ── Bootstrap ──────────────────────────────────────────────── */
function _initRadial() {
  window.radialPalette = new RadialPalette();
  window.openRadial  = () => window.radialPalette?.show();
  window.closeRadial = () => window.radialPalette?.hide();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _initRadial);
} else {
  _initRadial();
}
