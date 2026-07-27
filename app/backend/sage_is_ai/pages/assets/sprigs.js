// Sprigs panel island — Phase 0 of the frontend migration.
//
// The same panel as app/src/lib/components/admin/Sprigs.svelte, with no
// compiler between this file and the browser. Edit it, reload, done.
//
// What it deliberately does NOT use: the generated API wrapper layer. That
// layer is 3,839 lines mirroring endpoints the browser could call directly,
// and it is the single biggest deletion the migration buys. Three fetches here
// stand in for three of its 335 functions.

const TOKEN = () => localStorage.getItem('token');

const el = {
  list: document.getElementById('sprigs'),
  count: document.querySelector('[data-cy="sprigs-grafted-count"]'),
  refresh: document.querySelector('[data-cy="sprigs-refresh"]'),
  toasts: document.getElementById('toasts')
};

// Supervisor lifecycle state -> operator-facing label. Kept identical to the
// Svelte panel's table, because one guard-rail spec asserts against both and a
// divergence here would read as a migration regression.
const LABEL = { rooted: 'Grafted', wilted: 'Wilted', delivered: 'Delivered' };
const GRAFTED_STATES = new Set(['rooted', 'delivered']);

let busyName = null;

// --- plumbing ---------------------------------------------------------------

function toast(message, kind = 'info') {
  const node = document.createElement('div');
  node.className = `toast toast-${kind}`;
  // textContent, never innerHTML: `message` carries backend error detail, and
  // backend detail can carry a filename, a URL, or anything else an operator
  // typed into a config field.
  node.textContent = message;
  el.toasts.append(node);
  setTimeout(() => node.remove(), 12000);
}

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: {
      Authorization: `Bearer ${TOKEN()}`,
      ...(body ? { 'Content-Type': 'application/json' } : {})
    },
    ...(body ? { body: JSON.stringify(body) } : {})
  });
  let payload = null;
  try {
    payload = await res.json();
  } catch {
    /* a proxy error page, or 204 — handled by the status check below */
  }
  if (!res.ok) {
    // FastAPI puts the actionable half in `detail` ("cultivar needs numpy —
    // graft vector-chroma first"). Losing it and showing "Failed to graft" is
    // the exact Poka-Yoke regression the guard-rail spec exists to catch.
    const err = new Error(payload?.detail || `${res.status} ${res.statusText}`);
    err.detail = payload?.detail;
    throw err;
  }
  return payload;
}

// --- rendering --------------------------------------------------------------

function card(name, spec, grafted) {
  const g = grafted[name];
  const isGrafted = Boolean(g && GRAFTED_STATES.has(g.state));
  const incompatible = spec.compatible === false;

  const node = document.createElement('div');
  node.className = 'sprig-card';
  node.dataset.cy = 'sprig-card';
  node.dataset.sprig = name;

  const badge = document.createElement('span');
  badge.className = `badge badge-${g ? g.state : 'sprouted'}`;
  badge.dataset.cy = 'sprig-state';
  // The spec reads this attribute, not the label, so wording stays free to
  // change without breaking the guard-rail.
  badge.dataset.state = g?.state ?? 'sprouted';
  badge.textContent = g ? (LABEL[g.state] ?? 'Sprouted') : 'Sprouted';

  const main = document.createElement('div');
  main.className = 'sprig-main';

  const title = document.createElement('div');
  title.className = 'sprig-name';
  title.textContent = name;

  const meta = document.createElement('div');
  meta.className = 'sprig-meta';
  meta.textContent = [spec.capability, spec.model, spec.dim && `${spec.dim}d`]
    .filter(Boolean)
    .join(' · ');
  main.append(title, meta);

  if (incompatible && !isGrafted) {
    const warn = document.createElement('div');
    warn.className = 'sprig-warn';
    warn.dataset.cy = 'sprig-incompatible';
    warn.textContent = `Not available on this server (${spec.host_arch || 'unknown'})`;
    main.append(warn);
  }

  if (g) {
    const where = document.createElement('div');
    where.className = 'sprig-where';
    where.textContent = g.base_url + (g.pid ? ` · pid ${g.pid}` : '');
    main.append(where);
  }

  const actions = document.createElement('div');
  actions.className = 'sprig-actions';

  if (isGrafted) {
    if (g?.base_url) {
      const health = document.createElement('a');
      health.className = 'btn';
      health.href = '/admin/diagnostics';
      health.title = 'View health in Diagnostics';
      health.textContent = 'Health';
      actions.append(health);
    }
    const prune = document.createElement('button');
    prune.type = 'button';
    prune.className = 'btn btn-danger';
    prune.dataset.cy = 'sprig-prune';
    prune.textContent = 'Prune';
    prune.title = 'Terminate and remove this Sprig™';
    prune.disabled = busyName === name;
    prune.addEventListener('click', () => pruneSprig(name));
    actions.append(prune);
  } else {
    const graft = document.createElement('button');
    graft.type = 'button';
    graft.className = 'btn btn-primary';
    graft.dataset.cy = 'sprig-graft';
    graft.textContent = g?.state === 'wilted' ? 'Revive' : 'Graft';
    graft.disabled = busyName === name || incompatible;
    if (incompatible) graft.title = 'This Sprig™ requires a different server architecture';
    graft.addEventListener('click', () => graftSprig(name, spec.capability));
    actions.append(graft);
  }

  node.append(badge, main, actions);
  return node;
}

function render({ catalog, grafted, host_arch: hostArch }) {
  const entries = Object.entries(catalog ?? {});
  el.list.replaceChildren();
  el.list.removeAttribute('aria-busy');

  if (entries.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'page-muted';
    empty.textContent = 'No Sprigs in the catalog.';
    el.list.append(empty);
    el.count.textContent = '';
    return;
  }

  for (const [name, spec] of entries) {
    el.list.append(card(name, { ...spec, host_arch: hostArch }, grafted ?? {}));
  }

  // Counted the same way the cards decide their own badge, so the header line
  // cannot contradict the badges underneath it — a bug this panel has had once
  // already, when the counter looked only at 'rooted'.
  const count = Object.values(grafted ?? {}).filter((g) => GRAFTED_STATES.has(g?.state)).length;
  el.count.textContent = `${count} of ${entries.length} grafted`;
}

// --- actions ----------------------------------------------------------------

async function load() {
  el.refresh.disabled = true;
  try {
    render(await api('/api/v1/retrieval/sprigs/catalog'));
  } catch (e) {
    el.list.removeAttribute('aria-busy');
    toast(e.detail || 'Failed to load Sprig catalog', 'error');
  }
  el.refresh.disabled = false;
}

async function graftSprig(name, capability) {
  busyName = name;
  try {
    const res = await api('/api/v1/retrieval/sprigs/graft', {
      method: 'POST',
      body: { name, capability }
    });
    toast(`Grafted ${name}`, 'success');
    if (res?.warning) toast(res.warning, 'warning');
  } catch (e) {
    toast(e.detail ? `Failed to graft ${name}: ${e.detail}` : `Failed to graft ${name}`, 'error');
  }
  busyName = null;
  await load();
}

async function pruneSprig(name) {
  busyName = name;
  try {
    const res = await api('/api/v1/retrieval/sprigs/prune', {
      method: 'POST',
      body: { name }
    });
    toast(`Pruned ${name}`, 'success');
    // Pruning a delivered capability silently changes what the rest of the
    // product can do. Say so, per capability, exactly as the Svelte panel does.
    if (res?.embedding_reset) {
      toast('Embedding dispatch reset — graft a cultivar to restore document search.');
    }
    if (res?.reranking_reset) {
      toast('Reranking reset — hybrid search runs without rerank until a reranker is grafted.');
    }
    if (res?.stt_reset) {
      toast('Speech-to-text reset — graft an STT Sprig™ to restore local voice input.');
    }
    if (res?.theme_reset) {
      toast('Theme reset — the interface returns to the default look on reload.');
    }
  } catch (e) {
    toast(e.detail ? `Failed to prune ${name}: ${e.detail}` : `Failed to prune ${name}`, 'error');
  }
  busyName = null;
  await load();
}

// --- boot -------------------------------------------------------------------

el.refresh.addEventListener('click', load);

if (!TOKEN()) {
  el.list.removeAttribute('aria-busy');
  el.list.replaceChildren();
  const p = document.createElement('p');
  p.className = 'page-muted';
  p.textContent = 'Sign in as an administrator to manage Sprigs.';
  el.list.append(p);
} else {
  load();
}
