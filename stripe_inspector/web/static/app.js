const API_BASE = '';
let currentResult = null;

const keyInput = document.getElementById('keyInput');
const tokenInput = document.getElementById('tokenInput');
const inspectBtn = document.getElementById('inspectBtn');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');
const resultsContent = document.getElementById('resultsContent');

inspectBtn.addEventListener('click', runInspection);
keyInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') runInspection(); });

function toggleChip(el) {
    el.classList.toggle('active');
    updateModulesCount();
}

function getSelectedModules() {
    const chips = document.querySelectorAll('.module-chip.active');
    return Array.from(chips).map(c => c.dataset.module);
}

function updateModulesCount() {
    const total = document.querySelectorAll('.module-chip[data-module]').length;
    const selected = getSelectedModules().length;
    const el = document.getElementById('modulesCount');
    el.textContent = selected === total ? 'All selected' : `${selected}/${total} selected`;
}

function toggleAllModules(state) {
    document.querySelectorAll('.module-chip[data-module]').forEach(c => {
        if (state) c.classList.add('active');
        else c.classList.remove('active');
    });
    updateModulesCount();
}

async function runInspection() {
    const key = keyInput.value.trim();
    if (!key) return;

    const token = tokenInput.value.trim();
    const modules = getSelectedModules();
    if (modules.length === 0) {
        statusEl.style.display = 'block';
        statusEl.className = 'status error';
        statusEl.textContent = 'Select at least one module';
        return;
    }

    inspectBtn.disabled = true;
    resultsEl.style.display = 'none';
    statusEl.style.display = 'block';
    statusEl.className = 'status';
    statusEl.innerHTML = '<span class="spinner"></span> Connecting...';

    const total = document.querySelectorAll('.module-chip[data-module]').length;
    const deep = document.getElementById('deepToggle').checked;

    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const body = { key };
    if (modules.length < total) body.modules = modules;
    if (deep) body.deep = true;

    try {
        const resp = await fetch(`${API_BASE}/api/inspect/stream`, {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = JSON.parse(line.slice(6));

                if (data.type === 'progress') {
                    statusEl.innerHTML = `<span class="spinner"></span> Scanning <strong>${esc(data.module)}</strong>... (${data.current}/${data.total})`;
                } else if (data.type === 'module') {
                    // Module completed — could render incrementally here
                } else if (data.type === 'done') {
                    currentResult = data.result;
                    statusEl.style.display = 'none';
                    renderResults(currentResult);
                }
            }
        }
    } catch (err) {
        statusEl.className = 'status error';
        statusEl.textContent = `Error: ${err.message}`;
    } finally {
        inspectBtn.disabled = false;
    }
}

function renderResults(result) {
    resultsEl.style.display = 'block';
    let html = '';

    // Key badge
    const isLive = result.is_live;
    const badgeClass = isLive ? 'live' : 'test';
    const label = (result.is_restricted ? 'RESTRICTED ' : '') + (isLive ? 'LIVE KEY' : 'TEST KEY');
    html += `<div class="key-badge ${badgeClass}">${label} &mdash; ${esc(result.masked_key)}</div>`;
    html += `<div style="font-size:12px;color:var(--text-dim);margin-bottom:16px;">${esc(result.timestamp || '')}</div>`;

    // Permissions bar
    const perms = result.permissions || {};
    const allowed = Object.values(perms).filter(v => v === 'allowed').length;
    const denied = Object.values(perms).filter(v => v === 'denied').length;
    const errors = Object.values(perms).filter(v => v === 'error').length;
    html += `<div class="permissions-bar">
        <div class="perm-item allowed">${allowed} allowed</div>
        <div class="perm-item denied">${denied} denied</div>
        <div class="perm-item errors">${errors} errors</div>
    </div>`;

    // Module cards
    const modules = result.modules || {};
    for (const [name, mod] of Object.entries(modules)) {
        const success = mod.success;
        const badgeCls = success ? 'success' : 'failed';
        const badgeTxt = success ? 'OK' : 'DENIED';

        html += `<div class="module-card${success ? ' open' : ''}" onclick="toggleModule(this)">
            <div class="module-header">
                <span class="module-title">${esc(name)}</span>
                <span class="module-badge ${badgeCls}">${badgeTxt}</span>
            </div>
            <div class="module-body">`;

        if (success) {
            html += renderModuleData(name, mod.data);
        } else {
            html += `<div style="color:var(--red);font-size:13px;">${esc(mod.error || 'Failed')}</div>`;
        }

        html += `</div></div>`;
    }

    // PII Summary
    const pii = result.pii || {};
    if (pii.total_pii_items > 0) {
        html += `<div class="module-card open" onclick="toggleModule(this)">
            <div class="module-header">
                <span class="module-title" style="color:var(--red);">PII EXPOSURE SUMMARY</span>
                <span class="module-badge" style="background:rgba(239,68,68,0.15);color:var(--red);">${pii.total_pii_items} items</span>
            </div>
            <div class="module-body">`;

        const piiTypes = [
            ['Emails', pii.emails, pii.email_count],
            ['Names', pii.names, pii.name_count],
            ['Phones', pii.phones, pii.phone_count],
            ['Cards', pii.cards, pii.card_count],
            ['Countries', pii.countries, pii.country_count],
        ];
        for (const [label, items, count] of piiTypes) {
            if (count > 0) {
                const samples = items.slice(0, 8).map(esc).join(', ');
                const more = count > 8 ? ` <span style="color:var(--text-dim)">(+${count - 8} more)</span>` : '';
                html += `<div class="kv-row"><div class="kv-key">${label} (${count})</div><div class="kv-val">${samples}${more}</div></div>`;
            }
        }
        html += `</div></div>`;
    }

    // Footer: rate limit + duration
    const rl = result.rate_limit || {};
    const dur = result.duration_seconds;
    let footerParts = [];
    if (rl.total_requests) footerParts.push(`API requests: ${rl.total_requests}`);
    if (rl.remaining !== null && rl.remaining !== undefined) footerParts.push(`Rate limit remaining: ${rl.remaining}`);
    if (dur !== undefined) footerParts.push(`Scan completed in ${dur}s`);
    if (footerParts.length) {
        html += `<div style="font-size:12px;color:var(--text-dim);margin-top:12px;">${footerParts.join(' | ')}</div>`;
    }

    // Actions
    html += `<div class="actions-bar">
        <button class="btn btn-outline" onclick="copyJSON()">Copy JSON</button>
        <button class="btn btn-outline" onclick="downloadJSON()">Download JSON</button>
        <button class="btn btn-outline" onclick="downloadReport()">Download HTML Report</button>
        <button class="btn btn-outline" onclick="shareReport()">Share Report</button>
    </div>`;

    resultsContent.innerHTML = html;
}

function renderModuleData(name, data) {
    if (name === 'account') return renderKV(data);
    if (name === 'balance') return renderBalance(data);
    if (name === 'permission_scan') return renderPermissionScan(data);

    // Find the list key
    const listKeys = ['customers', 'charges', 'intents', 'products', 'payouts',
                      'subscriptions', 'invoices', 'endpoints', 'events', 'accounts',
                      'disputes', 'refunds', 'transactions', 'coupons'];
    const listKey = listKeys.find(k => Array.isArray(data[k]));

    if (listKey && data[listKey].length > 0) {
        const count = data.count || data[listKey].length;
        const hasMore = data.has_more ? '+' : '';
        let html = `<div style="font-size:12px;color:var(--text-dim);margin-bottom:8px;">${count}${hasMore} found</div>`;
        html += renderTable(data[listKey]);
        return html;
    }

    if (listKey) return `<div style="color:var(--text-dim);font-size:13px;">None found</div>`;
    return renderKV(data);
}

function renderPermissionScan(data) {
    const allowed = data.allowed || [];
    const denied = data.denied || [];
    const errors = data.errors || [];

    let html = `<div style="font-size:13px;margin-bottom:12px;">
        <span style="color:var(--green);">${data.allowed_count || 0} allowed</span> /
        <span style="color:var(--red);">${data.denied_count || 0} denied</span> /
        <span style="color:var(--yellow);">${data.error_count || 0} errors</span>
        out of ${data.total_endpoints || 0} endpoints
    </div>`;

    html += '<table class="data-table"><tr><th>Status</th><th>Endpoint</th></tr>';
    for (const ep of allowed) {
        html += `<tr><td style="color:var(--green);font-weight:600;">OK</td><td>${esc(ep)}</td></tr>`;
    }
    for (const ep of denied) {
        html += `<tr><td style="color:var(--red);font-weight:600;">NO</td><td>${esc(ep)}</td></tr>`;
    }
    for (const err of errors) {
        html += `<tr><td style="color:var(--yellow);font-weight:600;">??</td><td>${esc(err.endpoint || '')} (${esc(err.error || '')})</td></tr>`;
    }
    html += '</table>';
    return html;
}

function renderKV(obj, prefix = '') {
    let html = '';
    for (const [key, val] of Object.entries(obj)) {
        if (val === null || val === undefined) continue;
        if (typeof val === 'object' && !Array.isArray(val)) {
            html += `<div class="kv-row"><div class="kv-key">${esc(key)}</div><div class="kv-val" style="color:var(--accent);">▼</div></div>`;
            html += renderKV(val);
        } else if (Array.isArray(val)) {
            html += `<div class="kv-row"><div class="kv-key">${esc(key)}</div><div class="kv-val">${esc(val.join(', '))}</div></div>`;
        } else {
            html += `<div class="kv-row"><div class="kv-key">${esc(key)}</div><div class="kv-val">${esc(String(val))}</div></div>`;
        }
    }
    return html;
}

function renderBalance(data) {
    let html = '<table class="data-table"><tr><th>Type</th><th>Amount</th><th>Currency</th></tr>';
    for (const item of (data.available || [])) {
        html += `<tr><td>Available</td><td>${item.amount.toFixed(2)}</td><td>${esc((item.currency||'').toUpperCase())}</td></tr>`;
    }
    for (const item of (data.pending || [])) {
        html += `<tr><td>Pending</td><td>${item.amount.toFixed(2)}</td><td>${esc((item.currency||'').toUpperCase())}</td></tr>`;
    }
    html += '</table>';
    return html;
}

function renderTable(items) {
    if (!items.length) return '';
    const cols = Object.keys(items[0]).filter(k => k !== 'metadata');
    let html = '<table class="data-table"><tr>';
    for (const col of cols) html += `<th>${esc(col)}</th>`;
    html += '</tr>';
    for (const item of items.slice(0, 20)) {
        html += '<tr>';
        for (const col of cols) {
            let val = item[col];
            if (val === null || val === undefined) val = '';
            else if (typeof val === 'object') val = JSON.stringify(val);
            html += `<td title="${esc(String(val))}">${esc(String(val))}</td>`;
        }
        html += '</tr>';
    }
    html += '</table>';
    return html;
}

function toggleModule(card) {
    if (event.target.closest('.module-body')) return;
    card.classList.toggle('open');
}

function downloadJSON() {
    if (!currentResult) return;
    const blob = new Blob([JSON.stringify(currentResult, null, 2)], { type: 'application/json' });
    download(blob, `stripe-inspector-${Date.now()}.json`);
}

async function downloadReport() {
    if (!currentResult) return;
    const token = tokenInput.value.trim();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const resp = await fetch(`${API_BASE}/api/report`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ result: currentResult }),
        });
        const html = await resp.text();
        const blob = new Blob([html], { type: 'text/html' });
        download(blob, `stripe-inspector-report-${Date.now()}.html`);
    } catch (err) {
        alert('Failed to generate report: ' + err.message);
    }
}

function download(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function copyJSON() {
    if (!currentResult) return;
    const text = JSON.stringify(currentResult, null, 2);
    const size = new Blob([text]).size;

    if (size > 500000) {
        if (!confirm(`Result is ${(size / 1024).toFixed(0)}KB. Copy to clipboard anyway?`)) return;
    }

    const btn = event.target;
    const orig = btn.textContent;

    function onSuccess() {
        btn.textContent = 'Copied!';
        btn.style.color = 'var(--green)';
        btn.style.borderColor = 'var(--green)';
        setTimeout(() => { btn.textContent = orig; btn.style.color = ''; btn.style.borderColor = ''; }, 1500);
    }

    // Try modern API first, fall back to execCommand
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(onSuccess).catch(() => fallbackCopy(text, onSuccess));
    } else {
        fallbackCopy(text, onSuccess);
    }
}

function fallbackCopy(text, onSuccess) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;';
    document.body.appendChild(ta);
    ta.select();
    try {
        document.execCommand('copy');
        onSuccess();
    } catch (e) {
        alert('Copy failed. Try Ctrl+C manually.');
    }
    document.body.removeChild(ta);
}

async function shareReport() {
    if (!currentResult) return;
    const token = tokenInput.value.trim();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const resp = await fetch(`${API_BASE}/api/report`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ result: currentResult }),
        });
        const html = await resp.text();
        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
    } catch (err) {
        alert('Failed to generate report: ' + err.message);
    }
}

// Theme toggle
function toggleTheme() {
    const body = document.body;
    body.classList.toggle('light-theme');
    const isLight = body.classList.contains('light-theme');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    document.getElementById('themeIcon').textContent = isLight ? '🌙' : '☀️';
}

// Load saved theme
(function() {
    if (localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light-theme');
        const icon = document.getElementById('themeIcon');
        if (icon) icon.textContent = '🌙';
    }
})();

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}
