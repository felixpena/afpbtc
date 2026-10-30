/* AFPBTC — utilidades compartidas (sin dependencias) */
(function () {
  'use strict';

  var DAY = 86400;
  var cache = {};

  function getJSON(url) {
    if (!cache[url]) {
      cache[url] = fetch(url, { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error(r.status + ' ' + url);
        return r.json();
      });
    }
    return cache[url];
  }

  /* Serie publicada → { t: [segundos UTC], v: [valores] } */
  function series(id) {
    return getJSON('/data/series/' + id + '.json').then(function (doc) {
      var t0 = Date.parse(doc.start_date + 'T00:00:00Z') / 1000;
      var t = new Array(doc.values.length);
      for (var i = 0; i < t.length; i++) t[i] = t0 + i * DAY;
      return { id: id, unit: doc.unit, t: t, v: doc.values, doc: doc };
    });
  }

  var nf = function (d) { return new Intl.NumberFormat('es-CL', { minimumFractionDigits: d, maximumFractionDigits: d }); };
  var NF = { 0: nf(0), 1: nf(1), 2: nf(2), 3: nf(3), 4: nf(4) };

  function decimalsFor(v) {
    var a = Math.abs(v);
    if (a >= 1000) return 0;
    if (a >= 100) return 1;
    if (a >= 10) return 2;
    if (a >= 0.1) return 3;
    return 4;
  }

  function compact(v) {
    var a = Math.abs(v);
    if (a >= 1e12) return NF[2].format(v / 1e12) + ' bill.';
    if (a >= 1e9) return NF[1].format(v / 1e9) + ' mil M';
    if (a >= 1e6) return NF[2].format(v / 1e6) + ' M';
    return null;
  }

  /* Formatea un valor según su unidad */
  function fmt(v, unit) {
    if (v === null || v === undefined || !isFinite(v)) return '—';
    if (unit === 'USD') {
      var c = compact(v);
      return c ? 'US$' + c : 'US$' + NF[v >= 100 ? 0 : 2].format(v);
    }
    if (unit === 'BTC') {
      var cb = compact(v);
      return (cb || NF[0].format(v)) + ' BTC';
    }
    if (unit === '%') return NF[1].format(v) + '%';
    if (unit === 'EH/s') return NF[0].format(v) + ' EH/s';
    if (unit === 'T') return NF[1].format(v) + ' T';
    if (unit === 'sat/vB') return NF[v < 10 ? 2 : 1].format(v) + ' sat/vB';
    if (unit === 'USD/PH/día') return 'US$' + NF[2].format(v) + '/PH/día';
    if (unit === '0–100') return NF[1].format(v);
    if (unit === '×') return NF[decimalsFor(v)].format(v) + '×';
    if (unit === 'σ') return NF[2].format(v);
    if (unit === 'ratio' || unit === '' || !unit) {
      var d = Math.abs(v) < 0.01 ? 6 : decimalsFor(v);
      return new Intl.NumberFormat('es-CL', { maximumFractionDigits: d, minimumFractionDigits: Math.min(d, 2) }).format(v);
    }
    return NF[decimalsFor(v)].format(v) + ' ' + unit;
  }

  function pct(v) {
    if (v === null || v === undefined || !isFinite(v)) return '';
    return (v > 0 ? '+' : '') + NF[1].format(v) + '%';
  }

  function fmtDate(iso) {
    if (!iso) return '';
    var d = new Date(iso.length <= 10 ? iso + 'T12:00:00Z' : iso);
    return d.toLocaleDateString('es-CL', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  }

  /* Ruta SVG de una serie (para sparklines) */
  function sparkPath(values, w, h, pad) {
    pad = pad || 3;
    var pts = [];
    var min = Infinity, max = -Infinity;
    for (var i = 0; i < values.length; i++) {
      var v = values[i];
      if (v === null || !isFinite(v)) continue;
      if (v < min) min = v;
      if (v > max) max = v;
    }
    if (!isFinite(min)) return '';
    var span = max - min || 1;
    var n = values.length - 1 || 1;
    var d = '';
    var pen = false;
    for (var j = 0; j < values.length; j++) {
      var y = values[j];
      if (y === null || !isFinite(y)) { pen = false; continue; }
      var px = (j / n) * w;
      var py = pad + (1 - (y - min) / span) * (h - 2 * pad);
      d += (pen ? 'L' : 'M') + px.toFixed(1) + ' ' + py.toFixed(1);
      pen = true;
    }
    return d;
  }

  function sparkSVG(values, opts) {
    opts = opts || {};
    var w = opts.w || 240, h = opts.h || 52;
    var color = opts.color || '#F7931A';
    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('class', opts.cls || 'spark');
    var p = document.createElementNS(ns, 'path');
    p.setAttribute('d', sparkPath(values, w, h));
    p.setAttribute('fill', 'none');
    p.setAttribute('stroke', color);
    p.setAttribute('stroke-width', opts.stroke || 2);
    p.setAttribute('vector-effect', 'non-scaling-stroke');
    p.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(p);
    return svg;
  }

  function phaseOf(v) {
    if (v === null || v === undefined || !isFinite(v)) return null;
    if (v < 20) return 'Capitulación';
    if (v < 40) return 'Acumulación';
    if (v < 60) return 'Optimismo';
    if (v < 80) return 'Creencia';
    return 'Euforia';
  }

  /* Menú móvil */
  function initNav() {
    var btn = document.querySelector('.nav-toggle');
    var nav = document.getElementById('nav');
    if (!btn || !nav) return;
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') { nav.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); }
    });
  }

  function text(el, s) { if (el) el.textContent = s; }
  function $(sel, root) { return (root || document).querySelector(sel); }

  document.addEventListener('DOMContentLoaded', initNav);

  window.AFP = {
    getJSON: getJSON, series: series, fmt: fmt, pct: pct, fmtDate: fmtDate,
    sparkSVG: sparkSVG, sparkPath: sparkPath, phaseOf: phaseOf, text: text, $: $,
    LIVE_API: 'https://bitview.space'
  };
})();
