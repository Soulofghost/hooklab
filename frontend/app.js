const API_BASE = '/api';

let currentEndpoints = [];
let currentEvents = [];
let selectedEvent = null;

document.addEventListener('DOMContentLoaded', () => {
  initModal();
  initSimulator();
  initCopy();
  initReplay();
  loadStats();
  loadEndpoints();

  document.getElementById('refreshEventsBtn')?.addEventListener('click', () => {
    const sel = document.getElementById('endpointSelect').value;
    if (sel) loadEvents(sel);
  });
});

function initModal() {
  const modal = document.getElementById('endpointModal');
  const openBtn = document.getElementById('openEndpointModal');
  const closeBtn = document.getElementById('closeEndpointBtn');
  const cancelBtn = document.getElementById('cancelEndpointBtn');
  const form = document.getElementById('createEndpointForm');

  openBtn?.addEventListener('click', () => modal.classList.add('active'));
  closeBtn?.addEventListener('click', () => modal.classList.remove('active'));
  cancelBtn?.addEventListener('click', () => modal.classList.remove('active'));

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('epName').value.trim();
    const secret = document.getElementById('epSecret').value.trim();
    const forward_url = document.getElementById('epForward').value.trim();

    try {
      const res = await fetch(`${API_BASE}/endpoints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, secret, forward_url })
      });

      if (!res.ok) throw new Error('Failed to create endpoint');
      const data = await res.json();
      modal.classList.remove('active');
      form.reset();
      await loadStats();
      await loadEndpoints();
      document.getElementById('endpointSelect').value = data.id;
      onEndpointChange(data.id);
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  });
}

function initCopy() {
  const btn = document.getElementById('copyUrlBtn');
  btn?.addEventListener('click', () => {
    const text = document.getElementById('webhookUrlDisplay').innerText;
    navigator.clipboard.writeText(text).then(() => {
      btn.innerText = '✅ Copied!';
      setTimeout(() => btn.innerText = '📋 Copy', 2000);
    });
  });
}

function initReplay() {
  const btn = document.getElementById('replayBtn');
  btn?.addEventListener('click', async () => {
    if (!selectedEvent) return;
    btn.disabled = true;
    btn.innerText = 'Replaying...';

    try {
      const res = await fetch(`${API_BASE}/events/${selectedEvent.id}/replay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      if (!res.ok) throw new Error('Replay failed');
      const data = await res.json();
      alert(`Webhook Delivered Successfully!\nTarget: ${data.target_url}\nStatus: HTTP ${data.http_status}\nLatency: ${data.response_time_ms} ms`);
      loadStats();
    } catch (err) {
      alert(`Replay failed: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerText = '⚡ Replay Event';
    }
  });
}

function initSimulator() {
  const btn = document.getElementById('sendSimBtn');
  btn?.addEventListener('click', async () => {
    const sel = document.getElementById('endpointSelect');
    const ep = currentEndpoints.find(e => e.id === sel.value);
    if (!ep) {
      alert('Please select an endpoint first.');
      return;
    }

    const payload = document.getElementById('simPayloadInput').value.trim();

    try {
      const res = await fetch(`/webhook/${ep.token}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'HookLab-Simulator/1.0',
          'X-Simulated-Webhook': 'true'
        },
        body: payload
      });

      if (!res.ok) throw new Error('Failed to send webhook');
      await loadStats();
      await loadEvents(ep.id);
    } catch (err) {
      alert(`Send failed: ${err.message}`);
    }
  });
}

async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    const data = await res.json();
    document.getElementById('statEndpoints').innerText = data.totalEndpoints;
    document.getElementById('statEvents').innerText = data.totalEventsCaptured;
    document.getElementById('statVerified').innerText = data.verifiedEventsCount;
  } catch (err) {
    console.warn('Failed to load stats', err);
  }
}

async function loadEndpoints() {
  const select = document.getElementById('endpointSelect');
  try {
    const res = await fetch(`${API_BASE}/endpoints`);
    const list = await res.json();
    currentEndpoints = list || [];

    if (currentEndpoints.length === 0) {
      // Seed default endpoint
      const seed = await fetch(`${API_BASE}/endpoints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Stripe Payment Ingest', secret: 'whsec_prod_live_99' })
      });
      if (seed.ok) return loadEndpoints();
    }

    select.innerHTML = currentEndpoints.map(e => `<option value="${e.id}">${escapeHtml(e.name)}</option>`).join('');
    select.onchange = () => onEndpointChange(select.value);

    if (currentEndpoints.length > 0) {
      onEndpointChange(currentEndpoints[0].id);
    }
  } catch (err) {
    select.innerHTML = `<option value="">Error loading endpoints</option>`;
  }
}

function onEndpointChange(epId) {
  const ep = currentEndpoints.find(e => e.id === epId);
  if (!ep) return;
  document.getElementById('webhookUrlDisplay').innerText = ep.webhook_url;
  loadEvents(epId);
}

async function loadEvents(epId) {
  const listEl = document.getElementById('eventsList');
  try {
    const res = await fetch(`${API_BASE}/endpoints/${epId}/events`);
    const list = await res.json();
    currentEvents = list || [];

    if (currentEvents.length === 0) {
      listEl.innerHTML = `<div class="empty-state">No events captured yet for this endpoint.</div>`;
      clearInspector();
      return;
    }

    listEl.innerHTML = currentEvents.map(e => `
      <div class="event-item ${selectedEvent?.id === e.id ? 'active' : ''}" onclick="selectEvent('${e.id}')">
        <div class="event-item-top">
          <span class="badge badge-info">${e.method}</span>
          <span class="badge ${e.signature_verified ? 'badge-verified' : 'badge-unverified'}">${e.signature_verified ? 'HMAC VERIFIED' : 'UNVERIFIED'}</span>
        </div>
        <div class="event-item-bottom">
          <span class="text-mono">${e.client_ip}</span>
          <span>${new Date(e.received_at).toLocaleTimeString()}</span>
        </div>
      </div>
    `).join('');

    if (!selectedEvent && currentEvents.length > 0) {
      selectEvent(currentEvents[0].id);
    }
  } catch (err) {
    listEl.innerHTML = `<div class="empty-state" style="color:var(--accent-red);">Error loading events: ${err.message}</div>`;
  }
}

window.selectEvent = function(eventId) {
  selectedEvent = currentEvents.find(e => e.id === eventId);
  if (!selectedEvent) return;

  document.querySelectorAll('.event-item').forEach(el => el.classList.remove('active'));
  event.currentTarget?.classList.add('active');

  document.getElementById('inspectorPlaceholder').style.display = 'none';
  document.getElementById('inspectorContent').style.display = 'block';

  document.getElementById('detailMethod').innerText = selectedEvent.method;
  document.getElementById('detailIp').innerText = selectedEvent.client_ip;
  document.getElementById('detailTime').innerText = new Date(selectedEvent.received_at).toLocaleString();

  const hmacBadge = document.getElementById('hmacBadge');
  hmacBadge.innerText = selectedEvent.signature_verified ? 'HMAC-SHA256 SIGNATURE VALID' : 'NO HMAC / UNVERIFIED';
  hmacBadge.className = 'badge ' + (selectedEvent.signature_verified ? 'badge-verified' : 'badge-unverified');

  document.getElementById('detailHeaders').innerText = JSON.stringify(selectedEvent.headers, null, 2);

  try {
    const parsed = JSON.parse(selectedEvent.body);
    document.getElementById('detailBody').innerText = JSON.stringify(parsed, null, 2);
  } catch (e) {
    document.getElementById('detailBody').innerText = selectedEvent.body || '(Empty body)';
  }

  document.getElementById('replayBtn').disabled = false;
};

function clearInspector() {
  selectedEvent = null;
  document.getElementById('inspectorContent').style.display = 'none';
  document.getElementById('inspectorPlaceholder').style.display = 'block';
  document.getElementById('replayBtn').disabled = true;
  document.getElementById('hmacBadge').innerText = 'SELECT AN EVENT';
  document.getElementById('hmacBadge').className = 'badge';
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
