// Shared context-panel helpers. Loaded once so HTMX-swapped panels can call them.
(function () {
  window.ctxPanelSharedLoaded = true;

  window.ctxAfterItemChanged = function (id, msg) {
    window.ctxToast?.(id, msg);
    if (typeof window.calRefresh === 'function') window.calRefresh();
  };

  function mdRender(text) {
    if (!text) return '';
    let t = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    t = t.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    t = t.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    t = t.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    t = t.replace(/\*(.+?)\*/g, '<em>$1</em>');
    t = t.replace(/`(.+?)`/g, '<code>$1</code>');
    t = t.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    t = t.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    t = t.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    return t.split(/\n{2,}/).map(p => {
      if (/^<(h[1-3]|li|blockquote)/.test(p.trim())) return p;
      return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
    }).join('\n');
  }

  window.ctxOnStatusChange = function (id, status, btn) {
    btn?.closest('.ctx-status-seg')?.querySelectorAll('.ctx-status-btn').forEach(b => {
      b.classList.toggle('active', b === btn);
    });
    const panel = document.getElementById('ctx-panel-' + id);
    const badge = panel?.querySelector('.ctx-status');
    if (badge) {
      const labels = { todo: '대기', doing: '진행', waiting: '보류', done: '완료' };
      badge.textContent = '● ' + (labels[status] || status);
      badge.className = 'ctx-status ' + status;
    }
    const dot = document.getElementById('dot-' + id);
    if (dot) dot.outerHTML = `<span class="mc-dot" id="dot-${id}" data-status="${status}"></span>`;
    window.ctxAfterItemChanged(id);
  };

  window.ctxAfterStatusAction = function (id, status, msg) {
    const panel = document.getElementById('ctx-panel-' + id);
    const seg = panel?.querySelector('.ctx-status-seg');
    const btn = seg?.querySelector(`[data-status="${status}"]`) || null;
    window.ctxOnStatusChange(id, status, btn);
    seg?.querySelectorAll('.ctx-status-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.status === status);
    });
    window.ctxAfterItemChanged(id, msg);
  };

  window.ctxFocusEdit = function (id) {
    const title = document.getElementById('ctx-title-' + id);
    if (title && title.tagName !== 'INPUT') {
      window.ctxEditTitle(id);
      return;
    }
    window.ctxEditBody(id);
  };

  window.ctxAfterDelete = function (id) {
    document.getElementById('item-' + id)?.remove();
    const panel = document.getElementById('ctx-panel-' + id);
    if (panel) {
      panel.outerHTML = '<div style="padding:24px; color:var(--muted); font-size:13px;">삭제되었습니다.</div>';
    }
    if (typeof window.calRefresh === 'function') window.calRefresh();
  };

  window.ctxOpenSubtaskModal = function (id) {
    const modal = document.getElementById('sub-modal-' + id);
    modal?.classList.add('open');
    setTimeout(() => modal?.querySelector('input[name="title"]')?.focus(), 40);
  };

  window.ctxCloseSubtaskModal = function (id) {
    document.getElementById('sub-modal-' + id)?.classList.remove('open');
  };

  window.ctxLinkSearch = async function (id) {
    const q = document.getElementById('kg-query-' + id)?.value.trim() || '';
    const scope = document.getElementById('kg-scope-' + id)?.value || 'all';
    const box = document.getElementById('kg-suggest-' + id);
    if (!box) return;
    const canBrowseEmpty = ['github', 'calendar', 'drive', 'external'].includes(scope);
    if (!q && !canBrowseEmpty) {
      box.classList.remove('open');
      box.innerHTML = '';
      return;
    }
    const res = await fetch(`/api/link-search?q=${encodeURIComponent(q)}&scope=${encodeURIComponent(scope)}`);
    if (!res.ok) return;
    const data = await res.json();
    box.innerHTML = (data.results || []).map(row => {
      const type = row.type || 'item';
      const subtitle = type === 'project'
        ? [row.org_name, row.biz_name].filter(Boolean).join(' / ')
        : [row.project_title, row.parent_title ? `상위: ${row.parent_title}` : row.status].filter(Boolean).join(' · ');
      return `<div class="kg-opt" onclick="ctxPickLinkTarget(${id}, '${type}', ${row.id}, this)">
        ${escapeHtml(row.title || '')}<small>${escapeHtml(type)}${subtitle ? ' · ' + escapeHtml(subtitle) : ''}</small>
      </div>`;
    }).join('') || '<div class="kg-opt"><small>결과 없음</small></div>';
    box.classList.add('open');
  };

  window.ctxPickLinkTarget = function (id, type, targetId, el) {
    document.getElementById('kg-dst-type-' + id).value = type;
    document.getElementById('kg-dst-id-' + id).value = String(targetId);
    document.getElementById('kg-query-' + id).value = el.childNodes[0].textContent.trim();
    document.getElementById('kg-suggest-' + id)?.classList.remove('open');
  };

  window.ctxClearLinkForm = function (id) {
    const query = document.getElementById('kg-query-' + id);
    if (query) query.value = '';
    const dstType = document.getElementById('kg-dst-type-' + id);
    const dstId = document.getElementById('kg-dst-id-' + id);
    if (dstType) dstType.value = '';
    if (dstId) dstId.value = '';
    document.getElementById('kg-suggest-' + id)?.classList.remove('open');
    window.ctxInitLinkBrowser?.(id);
  };

  async function fetchBrowser(kind, params = {}) {
    const qs = new URLSearchParams({ kind });
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') qs.set(key, value);
    });
    const res = await fetch('/api/link-browser?' + qs.toString());
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || [];
  }

  function fillSelect(select, placeholder, rows, labelFn, emptyLabel = '선택 가능한 항목 없음') {
    if (!select) return;
    const empty = rows.length ? '' : `<option value="" disabled>${emptyLabel}</option>`;
    select.innerHTML = `<option value="">${placeholder}</option>` + empty + rows.map(row => {
      const label = escapeHtml(labelFn(row));
      return `<option value="${row.id}">${label}</option>`;
    }).join('');
  }

  function setBrowserTarget(id, type, targetId, label) {
    const dstType = document.getElementById('kg-dst-type-' + id);
    const dstId = document.getElementById('kg-dst-id-' + id);
    const preview = document.getElementById('kg-target-preview-' + id);
    if (dstType) dstType.value = type || '';
    if (dstId) dstId.value = targetId || '';
    if (preview) {
      preview.textContent = label || '연결할 프로젝트 또는 할 일을 선택하세요.';
      preview.classList.toggle('ready', Boolean(type && targetId));
    }
  }

  window.ctxInitLinkBrowser = async function (id) {
    const orgSelect = document.getElementById('kg-org-' + id);
    const businessSelect = document.getElementById('kg-business-' + id);
    if (!businessSelect) return;
    if (businessSelect.dataset.loaded === '1') return;
    businessSelect.dataset.loaded = '1';
    if (orgSelect) {
      const orgs = await fetchBrowser('org');
      fillSelect(orgSelect, '소속 선택', orgs, row => `${row.name} (${row.project_count || 0})`, '소속 없음');
    }
    await window.ctxBrowserOrgChanged(id);
  };

  window.ctxBrowserOrgChanged = async function (id) {
    const orgId = document.getElementById('kg-org-' + id)?.value || '';
    const businessSelect = document.getElementById('kg-business-' + id);
    const businesses = await fetchBrowser('business', { org_id: orgId });
    fillSelect(businessSelect, '사업 선택', businesses, row => {
      const org = row.org_name ? `${row.org_name} / ` : '';
      return `${org}${row.name} (${row.project_count || 0})`;
    });
    await window.ctxBrowserBusinessChanged(id);
  };

  window.ctxBrowserKindChanged = async function (id) {
    const itemSelect = document.getElementById('kg-item-' + id);
    if (itemSelect) itemSelect.style.display = '';
    setBrowserTarget(id, '', '', '');
    await window.ctxBrowserProjectChanged(id);
  };

  window.ctxBrowserBusinessChanged = async function (id) {
    const orgId = document.getElementById('kg-org-' + id)?.value || '';
    const businessId = document.getElementById('kg-business-' + id)?.value || '';
    const projectSelect = document.getElementById('kg-project-' + id);
    const projects = await fetchBrowser('project', { org_id: orgId, business_id: businessId });
    fillSelect(projectSelect, '프로젝트 선택', projects, row => {
      const prefix = [row.org_name, row.biz_name].filter(Boolean).join(' / ');
      const count = row.item_count ? ` (${row.item_count})` : '';
      return `${prefix ? prefix + ' / ' : ''}${row.title}${count}`;
    });
    await window.ctxBrowserProjectChanged(id);
  };

  window.ctxBrowserProjectChanged = async function (id) {
    const projectSelect = document.getElementById('kg-project-' + id);
    const projectId = projectSelect?.value || '';
    const projectLabel = projectSelect?.selectedOptions?.[0]?.textContent?.trim() || '';
    const itemSelect = document.getElementById('kg-item-' + id);
    setBrowserTarget(id, projectId ? 'project' : '', projectId, projectId ? `Project: ${projectLabel}` : '');
    if (false) {
      setBrowserTarget(id, projectId ? 'project' : '', projectId, projectId ? `프로젝트: ${projectLabel}` : '');
      if (itemSelect) fillSelect(itemSelect, '할 일 선택', [], row => row.title);
      return;
    }
    if (!projectId) setBrowserTarget(id, '', '', '');
    const items = projectId ? await fetchBrowser('item', { project_id: projectId }) : [];
    fillSelect(itemSelect, '할 일 선택', items, row => {
      const parent = row.parent_title ? `${row.parent_title} / ` : '';
      return `${parent}${row.title} - ${row.status}`;
    });
  };

  window.ctxBrowserItemChanged = function (id) {
    const itemSelect = document.getElementById('kg-item-' + id);
    const itemId = itemSelect?.value || '';
    const itemLabel = itemSelect?.selectedOptions?.[0]?.textContent?.trim() || '';
    if (!itemId) {
      window.ctxBrowserProjectChanged(id);
      return;
    }
    setBrowserTarget(id, itemId ? 'item' : '', itemId, itemId ? `할 일: ${itemLabel}` : '');
  };

  window.ctxInitProjectBrowser = async function (id) {
    const orgSelect = document.getElementById('proj-org-' + id);
    const businessSelect = document.getElementById('proj-business-' + id);
    if (!orgSelect || !businessSelect) return;
    if (businessSelect.dataset.loaded === '1') return;
    businessSelect.dataset.loaded = '1';
    const orgs = await fetchBrowser('org');
    fillSelect(orgSelect, '소속 선택', orgs, row => `${row.name} (${row.project_count || 0})`, '소속 없음');
    await window.ctxProjectOrgChanged(id);
  };

  window.ctxProjectOrgChanged = async function (id) {
    const orgId = document.getElementById('proj-org-' + id)?.value || '';
    const businessSelect = document.getElementById('proj-business-' + id);
    const businesses = await fetchBrowser('business', { org_id: orgId });
    fillSelect(businessSelect, '사업 선택', businesses, row => {
      const org = row.org_name ? `${row.org_name} / ` : '';
      return `${org}${row.name} (${row.project_count || 0})`;
    });
    await window.ctxProjectBusinessChanged(id);
  };

  window.ctxProjectBusinessChanged = async function (id) {
    const orgId = document.getElementById('proj-org-' + id)?.value || '';
    const businessId = document.getElementById('proj-business-' + id)?.value || '';
    const projectSelect = document.getElementById('proj-project-' + id);
    const projects = await fetchBrowser('project', { org_id: orgId, business_id: businessId });
    fillSelect(projectSelect, '프로젝트 선택', projects, row => {
      const prefix = [row.org_name, row.biz_name].filter(Boolean).join(' / ');
      return `${prefix ? prefix + ' / ' : ''}${row.title}`;
    });
  };

  window.ctxSubmitProjectLink = function (id) {
    const projectSelect = document.getElementById('proj-project-' + id);
    if (!projectSelect?.value) return;
    projectSelect.form?.requestSubmit();
  };

  window.ctxReorderPanelSections = function (id) {
    const panel = document.getElementById('ctx-panel-' + id);
    const header = panel?.querySelector('.ctx-h');
    const projectSection = panel?.querySelector('#proj-pick-' + id)?.closest('.ctx-section');
    const relatedSection = panel?.querySelector('#kg-links-item-' + id)?.closest('.ctx-section');
    if (header && projectSection && header.nextSibling !== projectSection) {
      header.after(projectSection);
    }
    if (relatedSection) {
      const actionSection = panel.querySelector('.ctx-action-bar')?.closest('.ctx-section');
      if (actionSection) actionSection.before(relatedSection);
      else panel.appendChild(relatedSection);
    }
  };

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  window.ctxRenderBody = function (id) {
    const el = document.getElementById('ctx-body-' + id);
    if (!el || el.tagName === 'TEXTAREA') return;
    const raw = el.dataset.raw || '';
    if (raw) {
      el.innerHTML = mdRender(raw);
      el.classList.remove('empty');
    } else {
      el.innerHTML = '<span style="color:var(--muted);">본문을 입력하려면 클릭하세요</span>';
      el.classList.add('empty');
    }
  };

  window.ctxEditTitle = function (id) {
    const el = document.getElementById('ctx-title-' + id);
    if (!el || el.tagName === 'INPUT') return;
    const cur = el.textContent.trim();
    const input = document.createElement('input');
    input.className = 'ctx-title-input';
    input.value = cur;
    input.id = 'ctx-title-' + id;
    el.replaceWith(input);
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);

    const save = async () => {
      const next = input.value.trim();
      if (!next) {
        input.value = cur;
        return input.blur();
      }
      const fd = new FormData();
      fd.append('title', next);
      await fetch('/api/items/' + id, { method: 'PATCH', body: fd });
      const div = document.createElement('div');
      div.className = 'ctx-title';
      div.id = 'ctx-title-' + id;
      div.textContent = next;
      div.onclick = () => window.ctxEditTitle(id);
      input.replaceWith(div);
      window.ctxAfterItemChanged(id);
    };
    input.addEventListener('blur', save, { once: true });
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
      if (e.key === 'Escape') { input.value = cur; input.blur(); }
    });
  };

  window.ctxEditBody = function (id) {
    const el = document.getElementById('ctx-body-' + id);
    if (!el || el.tagName === 'TEXTAREA') return;
    const cur = el.dataset.raw || '';
    const wrap = document.createElement('div');
    const ta = document.createElement('textarea');
    ta.className = 'ctx-body-textarea';
    ta.value = cur;
    ta.id = 'ctx-body-' + id;
    ta.rows = Math.max(6, cur.split('\n').length + 2);
    const hint = document.createElement('div');
    hint.className = 'ctx-body-hint';
    hint.textContent = 'Ctrl+Enter 저장, Esc 취소';
    wrap.appendChild(ta);
    wrap.appendChild(hint);
    el.replaceWith(wrap);
    ta.focus();

    const resize = () => { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; };
    ta.addEventListener('input', resize);
    resize();

    const save = async () => {
      const fd = new FormData();
      fd.append('body', ta.value);
      await fetch('/api/items/' + id, { method: 'PATCH', body: fd });
      const div = document.createElement('div');
      div.className = 'ctx-body-preview';
      div.id = 'ctx-body-' + id;
      div.dataset.raw = ta.value;
      div.onclick = () => window.ctxEditBody(id);
      wrap.replaceWith(div);
      window.ctxRenderBody(id);
      window.ctxToast(id);
    };
    ta.addEventListener('blur', save, { once: true });
    ta.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        ta.value = cur;
        ta.blur();
      }
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        ta.blur();
      }
    });
  };

  window.ctxQuickDate = async function (id, preset) {
    const now = new Date();
    let target = null;
    if (preset === 'today-9') { target = new Date(now); target.setHours(9, 0, 0, 0); }
    if (preset === 'today-14') { target = new Date(now); target.setHours(14, 0, 0, 0); }
    if (preset === 'tomorrow') { target = new Date(now); target.setDate(target.getDate() + 1); target.setHours(9, 0, 0, 0); }
    if (preset === 'next-mon') {
      target = new Date(now);
      const days = (8 - target.getDay()) % 7 || 7;
      target.setDate(target.getDate() + days);
      target.setHours(9, 0, 0, 0);
    }
    const value = target
      ? `${target.getFullYear()}-${String(target.getMonth() + 1).padStart(2, '0')}-${String(target.getDate()).padStart(2, '0')}T${String(target.getHours()).padStart(2, '0')}:${String(target.getMinutes()).padStart(2, '0')}`
      : '';
    const input = document.getElementById('date-' + id);
    if (input) input.value = value;
    const fd = new FormData();
    fd.append('scheduled_at', value);
    await fetch('/api/items/' + id, { method: 'PATCH', body: fd });
    window.ctxAfterItemChanged(id);
  };

  window.ctxToggleProjPick = function (id) {
    const picker = document.getElementById('proj-pick-' + id);
    picker?.classList.toggle('open');
    if (picker?.classList.contains('open')) window.ctxInitProjectBrowser?.(id);
  };

  window.ctxToast = function (id, msg) {
    const t = document.getElementById('ctx-toast-' + id);
    if (!t) return;
    const orig = t.textContent;
    if (msg) t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => {
      t.classList.remove('show');
      if (msg) setTimeout(() => { t.textContent = orig; }, 300);
    }, 1800);
  };

  window.ctxSetRecurrence = async function (id, rule) {
    const seg = document.getElementById('recur-seg-' + id);
    seg?.querySelectorAll('.ctx-recur-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('onclick')?.includes(`'${rule}'`));
    });
    const fd = new FormData();
    fd.append('recurrence_rule', rule);
    await fetch('/api/items/' + id, { method: 'PATCH', body: fd });
    const labels = { '': '없음', DAILY: '매일', WEEKDAYS: '평일', WEEKLY: '매주', MONTHLY: '매월' };
    window.ctxToast(id, rule ? `반복: ${labels[rule] || rule}` : '반복 없음');
  };

  window.ctxApplyMetaCommand = async function (id) {
    const input = document.getElementById('ctx-meta-input-' + id);
    const raw = input?.value.trim();
    if (!raw) return;
    const tokens = raw.split(/[, ]+/).map(v => v.trim()).filter(Boolean);
    for (const token of tokens) {
      const remove = token.startsWith('-');
      const clean = token.replace(/^-/, '');
      const isTag = clean.startsWith('#');
      const name = clean.replace(/^#/, '');
      if (!name) continue;
      const fd = new FormData();
      fd.append('name', name);
      fd.append('tag_name', name);
      const url = isTag
        ? `/api/items/${id}/tags/by-name`
        : `/api/items/${id}/labels/by-name`;
      await fetch(url, { method: remove ? 'DELETE' : 'POST', body: fd });
    }
    input.value = '';
    const panel = document.getElementById('ctx-panel-' + id);
    if (panel && window.htmx) {
      window.htmx.ajax('GET', `/partial/context/${id}`, { target: panel, swap: 'outerHTML' });
    }
  };

  window.ctxOpenFolder = async function (path) {
    if (!path) return;
    const res = await fetch('/api/folder-open?path=' + encodeURIComponent(path));
    if (!res.ok) {
      alert('폴더를 열 수 없습니다. 설정의 경로를 확인하세요.');
    }
  };

  document.addEventListener('htmx:afterSwap', e => {
    const panel = e.target?.matches?.('[id^="ctx-panel-"]')
      ? e.target
      : e.target?.querySelector?.('[id^="ctx-panel-"]');
    if (!panel) return;
    const id = panel.id.replace('ctx-panel-', '');
    window.ctxRenderBody(id);
    window.ctxReorderPanelSections(id);
  });

  document.addEventListener('focusin', e => {
    const form = e.target?.closest?.('.kg-form');
    const panel = form?.closest?.('[id^="ctx-panel-"]');
    if (!panel) return;
    window.ctxInitLinkBrowser(panel.id.replace('ctx-panel-', ''));
  });

  document.addEventListener('click', e => {
    const form = e.target?.closest?.('.kg-form');
    const panel = form?.closest?.('[id^="ctx-panel-"]');
    if (!panel) return;
    window.ctxInitLinkBrowser(panel.id.replace('ctx-panel-', ''));
  });
})();
