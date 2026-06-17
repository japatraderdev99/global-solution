'use strict';

/* Sentinela Orbital — console da estação de solo.
   API publicada no Google Cloud Run (Fase 3). Para rodar contra a API local,
   troque por 'http://localhost:8000'. */
const API_BASE = 'https://sentinela-api-520322249774.us-central1.run.app';

const RISK_COLORS = {
  critical: '#ff4d3d',
  high:     '#ff8a3d',
  moderate: '#f3c14b',
  low:      '#4fd08a',
};

const ORBITAL_LABELS = {
  fire:           'Fogo ativo',
  burned_scar:    'Cicatriz de queimada',
  healthy_forest: 'Floresta saudável',
  unknown:        'Indefinido',
};

const SIGNAL_LABELS = {
  critical: 'Crítico', high: 'Alto', moderate: 'Moderado', low: 'Baixo',
};

/* geometria do escópio: r=74 → circunferência; arco de 270° */
const GAUGE_C   = 2 * Math.PI * 74;
const GAUGE_ARC = GAUGE_C * 0.75;

const reduceMotion =
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

let map = null;
let marker = null;
let scoreAnim = null;

const el = (id) => document.getElementById(id);

/* escapa strings vindas da API antes de irem para innerHTML (defesa em profundidade) */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* ─── Relógio de missão (UTC) ─────────────────────── */
function tickClock() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  el('utc-clock').textContent =
    `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
}

/* ─── Mapa ────────────────────────────────────────── */
function initMap() {
  map = L.map('map', { center: [-3.4653, -62.2159], zoom: 6, zoomControl: true });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; ' +
      '<a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 18,
  }).addTo(map);
}

function markerIcon(level) {
  const color = RISK_COLORS[level] || '#607a70';
  const pulse = level === 'critical' ? 'pulse-critical'
              : level === 'high'     ? 'pulse-high' : '';
  return L.divIcon({
    className: '',
    html: `<div class="risk-marker ${pulse}" style="background:${color};"></div>`,
    iconSize: [14, 14], iconAnchor: [7, 7], popupAnchor: [0, -11],
  });
}

function updateMarker(lat, lng, level, popupHtml) {
  if (marker) { marker.remove(); }
  marker = L.marker([lat, lng], { icon: markerIcon(level) }).addTo(map).bindPopup(popupHtml);
  map.flyTo([lat, lng], 9, { duration: reduceMotion ? 0 : 1.3 });
  el('map-coords').textContent = `${toDMS(lat, 'N', 'S')}  ${toDMS(lng, 'E', 'W')}`;
}

/* coordenadas em graus-minutos-segundos (linguagem de estação) */
function toDMS(value, pos, neg) {
  const dir = value >= 0 ? pos : neg;
  const a = Math.abs(value);
  const d = Math.floor(a);
  const mf = (a - d) * 60;
  const m = Math.floor(mf);
  const s = Math.round((mf - m) * 60);
  const p = (n) => String(n).padStart(2, '0');
  return `${d}°${p(m)}'${p(s)}"${dir}`;
}

/* ─── Escópio: arco + contagem ────────────────────── */
function setGauge(score, level) {
  const fill = el('gauge-fill');
  const f = Math.max(0, Math.min(100, score)) / 100;
  fill.style.strokeDasharray = `${(GAUGE_ARC * f).toFixed(1)} ${GAUGE_C.toFixed(1)}`;
  fill.style.stroke = RISK_COLORS[level] || '#607a70';

  const target = Math.round(score);
  const node = el('risk-score');
  if (reduceMotion) { node.textContent = target; return; }

  if (scoreAnim) cancelAnimationFrame(scoreAnim);
  const from = parseInt(node.textContent, 10) || 0;
  const start = performance.now();
  const dur = 900;
  const step = (now) => {
    const t = Math.min(1, (now - start) / dur);
    const eased = 1 - Math.pow(1 - t, 3);
    node.textContent = Math.round(from + (target - from) * eased);
    if (t < 1) scoreAnim = requestAnimationFrame(step);
  };
  scoreAnim = requestAnimationFrame(step);
}

/* ─── Enlace ──────────────────────────────────────── */
function setStatus(ok) {
  el('status-dot').className = 'enlace-dot ' + (ok ? 'ok' : 'err');
  el('status-label').textContent = ok ? 'enlace ativo' : 'sem enlace';
}

async function checkHealth() {
  try { setStatus((await fetch(`${API_BASE}/health`)).ok); }
  catch { setStatus(false); }
}

/* ─── Render ──────────────────────────────────────── */
const pct = (v) => `${(v * 100).toFixed(0)}%`;

function renderResult(data) {
  const { orbital, sensor, risk, recommendation, location } = data;

  el('risk-card').className = `panel scope-panel level-${risk.level}`;
  el('risk-badge').textContent = risk.label.replace(/^Risco\s+/i, '');
  setGauge(risk.score, risk.level);
  el('risk-action').textContent = recommendation.message;

  el('factor-list').innerHTML = risk.factors.length
    ? risk.factors.map((f) => `<li class="factor-tag">${escapeHtml(f.replace(/_/g, ' '))}</li>`).join('')
    : '<li class="factor-empty">nenhuma anomalia sinalizada</li>';

  el('orbital-class').textContent = ORBITAL_LABELS[orbital.class] ?? orbital.class;
  el('orbital-conf').textContent  = `confiança ${(orbital.confidence * 100).toFixed(0)}%`;
  // defaults para 0 caso a API real omita uma classe (contrato pede as 3 sempre)
  const p = orbital.probabilities || {};
  const pf = p.fire ?? 0, ps = p.burned_scar ?? 0, pfo = p.healthy_forest ?? 0;
  el('p-fire').style.width   = pct(pf);
  el('p-scar').style.width   = pct(ps);
  el('p-forest').style.width = pct(pfo);
  el('pv-fire').textContent   = pct(pf);
  el('pv-scar').textContent   = pct(ps);
  el('pv-forest').textContent = pct(pfo);

  el('s-smoke').textContent = sensor.smoke_ppm.toFixed(0);
  el('s-temp').textContent  = sensor.temperature_c.toFixed(1);
  el('s-hum').textContent   = sensor.humidity_pct != null ? sensor.humidity_pct.toFixed(0) : '—';
  const sig = el('s-signal');
  sig.textContent = SIGNAL_LABELS[sensor.signal_level] ?? sensor.signal_level;
  sig.className = `t-val signal signal-${sensor.signal_level}`;
  el('s-device').textContent = sensor.device_id;

  el('last-update').textContent =
    `varredura ${new Date(data.generated_at).toLocaleTimeString('pt-BR')}`;

  if (location?.latitude != null && location?.longitude != null) {
    const popup = `
      <div class="pp-title" style="color:${RISK_COLORS[risk.level]}">
        ${risk.label} · ${risk.score}/100
      </div>
      <div class="pp-row">orbital: <b>${escapeHtml(ORBITAL_LABELS[orbital.class] ?? orbital.class)}</b></div>
      <div class="pp-row">fumaça: <b>${sensor.smoke_ppm.toFixed(0)} ppm</b></div>
      <div class="pp-row">temperatura: <b>${sensor.temperature_c.toFixed(1)} °C</b></div>`;
    updateMarker(location.latitude, location.longitude, risk.level, popup);
  }
}

/* ─── Amostra automática ──────────────────────────── */
const SAMPLE_PAYLOAD = {
  request_id: 'ui-bootstrap',
  image: { source_type: 'sample', uri: 'samples/amazon-fire-001.jpg' },
  sensor: {
    device_id: 'esp32-wokwi-001', smoke_ppm: 620, temperature_c: 42.6,
    humidity_pct: 31.4, latitude: -3.4653, longitude: -62.2159,
  },
};

async function loadSample() {
  // carga inicial via endpoint dedicado; se indisponível (ex.: Cloud Run sem /sample-response),
  // recai para POST /analyze com payload embutido, mantendo o console populado na demo.
  try {
    const r = await fetch(`${API_BASE}/sample-response`);
    if (r.ok) { renderResult(await r.json()); return; }
  } catch { /* segue para o fallback */ }

  try {
    const r = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(SAMPLE_PAYLOAD),
    });
    if (r.ok) renderResult(await r.json());
  } catch { /* sem enlace — console permanece em espera */ }
}

/* ─── Formulário ──────────────────────────────────── */
function detectSourceType(uri) {
  if (/^https?:\/\//i.test(uri)) return 'url';
  if (uri.startsWith('samples/')) return 'sample';
  return 'url';
}

async function handleSubmit(e) {
  e.preventDefault();
  const btn = el('btn-submit');
  const label = btn.querySelector('.btn-label');
  const errEl = el('form-error');
  errEl.textContent = '';

  const uri = el('f-uri').value.trim();
  if (!uri) { errEl.textContent = 'Informe a URI da imagem orbital.'; return; }

  const smoke = parseFloat(el('f-smoke').value);
  const temp  = parseFloat(el('f-temp').value);
  const lat   = parseFloat(el('f-lat').value);
  const lng   = parseFloat(el('f-lon').value);

  // valida números antes de enviar — campo vazio vira NaN→null e quebra o backend
  if (!Number.isFinite(smoke) || smoke < 0) {
    errEl.textContent = 'Fumaça deve ser um número maior ou igual a 0.'; return;
  }
  if (!Number.isFinite(temp) || temp < -20 || temp > 80) {
    errEl.textContent = 'Temperatura deve estar entre -20 e 80 °C.'; return;
  }

  btn.disabled = true;
  label.textContent = 'varrendo…';

  const sensor = { device_id: 'esp32-wokwi-001', smoke_ppm: smoke, temperature_c: temp };
  if (Number.isFinite(lat) && Number.isFinite(lng) &&
      Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
    sensor.latitude = lat; sensor.longitude = lng;
  }

  const payload = {
    request_id: `ui-${Date.now()}`,
    image: { source_type: detectSourceType(uri), uri },
    sensor,
  };

  try {
    const r = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await r.json();
    if (r.ok) {
      renderResult(data);
    } else {
      const code = data?.error?.code;
      const msg  = data?.error?.message ?? `Falha na varredura (${r.status}).`;
      errEl.textContent = code ? `${code} · ${msg}` : msg;
    }
  } catch {
    errEl.textContent = 'Sem enlace com a estação. Verifique se a API está ativa.';
  }

  btn.disabled = false;
  label.textContent = 'executar varredura';
}

/* ─── Vista de Dados / EDA ────────────────────────── */
/* servir o dashboard a partir da raiz do repo p/ alcançar docs/eda/ */
const EDA_URL = '/docs/eda/eda_summary.json';
const MODEL_URL = '/docs/eda/model_metrics.json';
const CLASS_ORDER  = ['fire', 'burned_scar', 'healthy_forest'];
const CLASS_LABELS = { fire: 'Fogo', burned_scar: 'Cicatriz', healthy_forest: 'Floresta' };
const CLASS_COLORS = { fire: '#ff4d3d', burned_scar: '#f3c14b', healthy_forest: '#4fd08a' };
const SPLIT_ORDER  = ['train', 'val', 'test'];
const SPLIT_LABELS = { train: 'Treino', val: 'Validação', test: 'Teste' };

let edaLoaded = false;

function bar(name, value, total, max, color) {
  const w = max > 0 ? (value / max) * 100 : 0;
  const p = total > 0 ? ((value / total) * 100).toFixed(0) : '0';
  return `<div class="cbar">
    <span class="cbar-name">${escapeHtml(name)}</span>
    <div class="cbar-track"><div class="cbar-fill" style="width:${w}%;background:${color}"></div></div>
    <span class="cbar-val">${value}<span>${p}%</span></span>
  </div>`;
}

function renderEda(d) {
  el('eda-total').textContent = d.total_samples ?? '—';
  el('eda-gen').textContent = d.meta?.generated_at
    ? `gerado ${d.meta.generated_at.replace('T', ' ').replace('Z', ' UTC')}` : '—';

  // distribuição por classe
  const cc = d.class_counts || {};
  const maxC = Math.max(1, ...CLASS_ORDER.map((k) => cc[k] || 0));
  el('eda-classbars').innerHTML = CLASS_ORDER
    .map((k) => bar(CLASS_LABELS[k], cc[k] || 0, d.total_samples, maxC, CLASS_COLORS[k]))
    .join('');

  // divisão por split
  const sc = d.split_counts || {};
  const maxS = Math.max(1, ...SPLIT_ORDER.map((k) => sc[k] || 0));
  el('eda-splitbars').innerHTML = SPLIT_ORDER
    .map((k) => bar(SPLIT_LABELS[k], sc[k] || 0, d.total_samples, maxS, 'var(--signal)'))
    .join('');

  // matriz split × classe
  const m = d.split_class_matrix || {};
  let head = '<thead><tr><th>Split</th>' +
    CLASS_ORDER.map((k) => `<th><span class="dot" style="background:${CLASS_COLORS[k]}"></span>${CLASS_LABELS[k]}</th>`).join('') +
    '<th>Total</th></tr></thead>';
  const colTot = { fire: 0, burned_scar: 0, healthy_forest: 0 };
  let bodyRows = SPLIT_ORDER.filter((s) => m[s]).map((s) => {
    let rt = 0;
    const cells = CLASS_ORDER.map((k) => { const v = m[s][k] || 0; colTot[k] += v; rt += v; return `<td>${v}</td>`; }).join('');
    return `<tr><td>${SPLIT_LABELS[s]}</td>${cells}<td>${rt}</td></tr>`;
  }).join('');
  const grand = CLASS_ORDER.reduce((a, k) => a + colTot[k], 0);
  bodyRows += `<tr class="row-total"><td>Total</td>` +
    CLASS_ORDER.map((k) => `<td>${colTot[k]}</td>`).join('') + `<td>${grand}</td></tr>`;
  el('eda-matrix').innerHTML = head + '<tbody>' + bodyRows + '</tbody>';

  // razão de pixels positivos
  const pr = d.positive_ratio_by_label || {};
  const fmt = (x) => (x == null ? '—' : Number(x).toFixed(4));
  el('eda-ratio').innerHTML =
    '<thead><tr><th>Classe</th><th>mín</th><th>mediana</th><th>máx</th></tr></thead><tbody>' +
    CLASS_ORDER.map((k) => {
      const r = pr[k] || {};
      return `<tr><td><span class="dot" style="background:${CLASS_COLORS[k]}"></span>${CLASS_LABELS[k]}</td>` +
        `<td>${fmt(r.min)}</td><td>${fmt(r.median)}</td><td>${fmt(r.max)}</td></tr>`;
    }).join('') + '</tbody>';

  // verificação de vazamento
  const leak = d.group_leakage || {};
  const keys = Object.keys(leak);
  el('eda-leak').innerHTML = keys.length === 0
    ? `<div class="leak-badge ok"><span class="ic">✓</span> Sem vazamento entre splits</div>
       <p class="leak-note">Nenhum <code>group_id</code> aparece em mais de um split — treino, validação e teste são disjuntos por evento/cena.</p>`
    : `<div class="leak-badge bad"><span class="ic">⚠</span> ${keys.length} grupo(s) vazando</div>
       <ul class="leak-list">${keys.slice(0, 8).map((g) =>
          `<li><b>${escapeHtml(g)}</b>: ${(leak[g] || []).map(escapeHtml).join(', ')}</li>`).join('')}</ul>`;

  // proveniência
  const meta = d.meta || {};
  const th = meta.thresholds || {};
  const src = meta.sources || {};
  const sen = src.sen2fire || {}, flo = src.floga || {};
  el('eda-prov').innerHTML = `
    <div class="prov-block"><span class="prov-k">limiares de rótulo</span>
      <div class="prov-thresh">
        <span class="chip">fire ≥ ${th.fire ?? '—'}</span>
        <span class="chip">burned ≥ ${th.burned_scar ?? '—'}</span>
        <span class="chip">neg ≤ ${th.negative ?? '—'}</span>
      </div></div>
    <div class="prov-block"><span class="prov-k">Sen2Fire</span>
      <span class="prov-v">DOI ${escapeHtml(sen.doi ?? '—')} · ${escapeHtml(sen.license ?? '—')}</span></div>
    <div class="prov-block"><span class="prov-k">FLOGA</span>
      <span class="prov-v">${flo.repository
        ? `<a href="${escapeHtml(flo.repository)}" target="_blank" rel="noopener">repositório</a>` : '—'}
        · dados ${escapeHtml(flo.data_license ?? '—')} · código ${escapeHtml(flo.code_license ?? '—')}</span></div>
    <div class="prov-block"><span class="prov-k">manifesto</span>
      <span class="prov-v">${escapeHtml(meta.manifest_path ?? '—')}</span></div>`;

  edaLoaded = true;
}

async function loadEda() {
  try {
    const r = await fetch(EDA_URL);
    if (!r.ok) throw new Error('404');
    renderEda(await r.json());
  } catch {
    el('eda-grid').hidden = true;
    el('eda-empty').hidden = false;
  }
}

/* ─── Métricas do modelo (Fase 2) ─────────────────── */
let modelLoaded = false;
const f3 = (x) => (x == null ? '—' : Number(x).toFixed(3));

function renderModel(d) {
  const o = d.overall || {};
  el('model-name').textContent = `${d.meta?.model ?? 'modelo'} · ${d.meta?.epochs ?? '?'} épocas`;
  el('m-f1macro').textContent = f3(o.f1_macro);
  el('m-acc').textContent = f3(o.accuracy);
  el('m-f1w').textContent = f3(o.f1_weighted);
  el('m-testn').textContent = d.dataset?.test ?? '—';
  el('m-trainn').textContent = d.dataset?.train ?? '—';
  el('m-input').textContent = d.meta?.input ?? '';

  // tabela por classe
  const pc = d.per_class || {};
  el('model-perclass').innerHTML =
    '<thead><tr><th>Classe</th><th>precisão</th><th>recall</th><th>F1</th><th>suporte</th></tr></thead><tbody>' +
    CLASS_ORDER.map((k) => {
      const m = pc[k] || {};
      return `<tr><td><span class="dot" style="background:${CLASS_COLORS[k]}"></span>${CLASS_LABELS[k]}</td>` +
        `<td>${f3(m.precision)}</td><td>${f3(m.recall)}</td><td>${f3(m.f1)}</td><td>${m.support ?? '—'}</td></tr>`;
    }).join('') + '</tbody>';

  // matriz de confusão (linhas=verdadeiro, colunas=previsto), célula sombreada
  const cm = d.confusion_matrix || {};
  const labels = cm.labels || CLASS_ORDER;
  const mat = cm.matrix || [];
  const max = Math.max(1, ...mat.flat());
  let head = '<thead><tr><th>real \\ prev.</th>' +
    labels.map((k) => `<th><span class="dot" style="background:${CLASS_COLORS[k]}"></span>${CLASS_LABELS[k] ?? k}</th>`).join('') +
    '</tr></thead>';
  const body = mat.map((row, i) =>
    '<tr><td>' + (CLASS_LABELS[labels[i]] ?? labels[i]) + '</td>' +
    row.map((v, j) => {
      const a = (v / max) * 0.85 + (v ? 0.06 : 0);
      const diag = i === j ? ' cm-diag' : '';
      return `<td><span class="cm-cell${diag}" style="background:rgba(56,211,201,${a.toFixed(3)})">${v}</span></td>`;
    }).join('') + '</tr>'
  ).join('');
  el('model-cm').innerHTML = head + '<tbody>' + body + '</tbody>';

  el('model-note').textContent =
    `Rebalanceamento: ${d.meta?.rebalancing ?? '—'} ${d.meta?.notes ? '— ' + d.meta.notes : ''}`;

  modelLoaded = true;
}

async function loadModel() {
  try {
    const r = await fetch(MODEL_URL);
    if (!r.ok) throw new Error('404');
    renderModel(await r.json());
  } catch {
    el('model-grid').hidden = true;
    el('model-empty').hidden = false;
  }
}

function setView(view) {
  const ops = view === 'ops';
  el('view-ops').hidden = !ops;
  el('view-data').hidden = ops;
  el('tab-ops').classList.toggle('active', ops);
  el('tab-data').classList.toggle('active', !ops);
  el('tab-ops').setAttribute('aria-selected', String(ops));
  el('tab-data').setAttribute('aria-selected', String(!ops));
  if (!ops && !edaLoaded) loadEda();
  if (!ops && !modelLoaded) loadModel();
  if (ops && map) setTimeout(() => map.invalidateSize(), 60); // Leaflet recalc após reexibir
}

el('tab-ops').addEventListener('click', () => setView('ops'));
el('tab-data').addEventListener('click', () => setView('data'));

/* ─── Init ────────────────────────────────────────── */
initMap();
tickClock();
setInterval(tickClock, 1000);
checkHealth();
setInterval(checkHealth, 15000);
loadSample();
el('analyze-form').addEventListener('submit', handleSubmit);
