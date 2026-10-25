/* AFPBTC — página de inicio */
(function () {
  'use strict';
  var A = window.AFP, $ = A.$;

  function setTick(id, txt) { A.text($('#' + id), txt); }

  function renderTicker(latest) {
    var m = latest.metrics || {};
    if (m.price) setTick('t-price', A.fmt(m.price.value, 'USD').replace('US$', '$'));
    if (m.mvrv_zscore) setTick('t-z', A.fmt(m.mvrv_zscore.value, 'σ'));
    if (m.nupl) setTick('t-nupl', A.fmt(m.nupl.value, 'ratio'));
    if (m.hashrate) setTick('t-hash', A.fmt(m.hashrate.value, 'EH/s'));
    var tk = latest.ticker || {};
    if (tk.fees) setTick('t-fee', A.fmt(tk.fees.halfHourFee, 'sat/vB'));
    if (tk.block_height) setTick('t-block', new Intl.NumberFormat('es-CL').format(tk.block_height));
  }

  /* Comisiones y altura de bloque en vivo (API pública compatible con mempool.space) */
  function live() {
    var api = A.LIVE_API;
    Promise.all([
      fetch(api + '/api/v1/fees/recommended').then(function (r) { return r.json(); }),
      fetch(api + '/api/blocks/tip/height').then(function (r) { return r.text(); })
    ]).then(function (res) {
      setTick('t-fee', A.fmt(res[0].halfHourFee, 'sat/vB'));
      setTick('t-block', new Intl.NumberFormat('es-CL').format(parseInt(res[1], 10)));
      var dot = '<span class="live-dot" aria-hidden="true"></span>';
      $('#t-fee-src').innerHTML = dot + 'Mempool · en vivo';
      $('#t-block-src').innerHTML = dot + 'Red · en vivo';
    }).catch(function () { /* se mantiene el último dato diario */ });
  }

  function renderCycle(latest) {
    var c = latest.cycle || {};
    if (c.value === null || c.value === undefined) { A.text($('#cyc-phase'), 'Sin datos'); return; }
    var mark = $('#thermo-mark');
    mark.hidden = false;
    requestAnimationFrame(function () { mark.style.left = Math.max(0.5, Math.min(99.5, c.value)) + '%'; });
    A.text($('#cyc-value'), A.fmt(c.value, '0–100'));
    A.text($('#cyc-phase'), c.phase || A.phaseOf(c.value));
    A.text($('#cyc-meta'), 'Actualizado ' + A.fmtDate(c.date));
    $('#thermo').setAttribute('aria-label', 'Termómetro de ciclo: ' + A.fmt(c.value, '0–100') + ' de 100, fase ' + (c.phase || ''));
  }

  function renderCycleHistory() {
    A.series('cycle_index').then(function (s) {
      var w = 1000, h = 140, ns = 'http://www.w3.org/2000/svg';
      var svg = document.createElementNS(ns, 'svg');
      svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
      svg.setAttribute('preserveAspectRatio', 'none');
      var bands = [['#1F4E79', 0, 20], ['#2E7DAF', 20, 40], ['#8A8F7A', 40, 60], ['#D9822B', 60, 80], ['#B8441E', 80, 100]];
      bands.forEach(function (b) {
        var r = document.createElementNS(ns, 'rect');
        r.setAttribute('x', 0); r.setAttribute('width', w);
        r.setAttribute('y', h - (b[2] / 100) * h); r.setAttribute('height', ((b[2] - b[1]) / 100) * h);
        r.setAttribute('fill', b[0]); r.setAttribute('opacity', '0.16');
        svg.appendChild(r);
      });
      // Normaliza a la escala fija 0–100.
      var vals = s.v.slice();
      var first = vals.findIndex(function (v) { return v !== null; });
      vals = vals.slice(first);
      var n = vals.length - 1, d = '', pen = false;
      for (var i = 0; i < vals.length; i++) {
        var v = vals[i];
        if (v === null) { pen = false; continue; }
        d += (pen ? 'L' : 'M') + ((i / n) * w).toFixed(1) + ' ' + (h - (v / 100) * h).toFixed(1);
        pen = true;
      }
      var p = document.createElementNS(ns, 'path');
      p.setAttribute('d', d); p.setAttribute('fill', 'none'); p.setAttribute('stroke', '#EDEAE3');
      p.setAttribute('stroke-width', '1.6'); p.setAttribute('vector-effect', 'non-scaling-stroke');
      svg.appendChild(p);
      $('#cyc-hist').appendChild(svg);
      var startYear = new Date(s.t[first] * 1000).getUTCFullYear();
      A.text($('#cyc-range'), startYear + ' – hoy');
    }).catch(function () { $('#cyc-hist').closest('figure').hidden = true; });
  }

  function renderLayers(latest, catalog) {
    var units = {};
    (catalog.metrics || []).forEach(function (m) { units[m.id] = m.unit; });
    document.querySelectorAll('#layers [data-metric]').forEach(function (card) {
      var id = card.getAttribute('data-metric');
      var m = (latest.metrics || {})[id];
      var valEl = card.querySelector('[data-value]');
      if (m) {
        valEl.textContent = A.fmt(m.value, units[id]);
        if (m.change_30d_pct !== null && m.change_30d_pct !== undefined) {
          var sm = document.createElement('small');
          sm.textContent = A.pct(m.change_30d_pct) + ' 30 d';
          valEl.appendChild(sm);
        }
      }
      A.series(id).then(function (s) {
        card.querySelector('[data-spark]').appendChild(A.sparkSVG(s.v.slice(-365)));
      }).catch(function () {});
    });
  }

  function renderGlossary(catalog) {
    var dl = $('#glossary');
    var pick = ['realized_price', 'mvrv', 'mvrv_zscore', 'sopr', 'nupl', 'lth_supply', 'hashprice', 'puell_multiple', 'reserve_risk', 'cycle_index'];
    var byId = {};
    (catalog.metrics || []).forEach(function (m) { byId[m.id] = m; });
    pick.forEach(function (id) {
      var m = byId[id];
      if (!m) return;
      var div = document.createElement('div');
      var dt = document.createElement('dt');
      var a = document.createElement('a');
      a.href = '/metricas/?m=' + id;
      a.textContent = m.name;
      dt.appendChild(a);
      var dd = document.createElement('dd');
      dd.textContent = m.what;
      div.appendChild(dt); div.appendChild(dd);
      dl.appendChild(div);
    });
  }

  Promise.all([A.getJSON('/data/latest.json'), A.getJSON('/data/catalog.json')]).then(function (r) {
    var latest = r[0], catalog = r[1];
    renderTicker(latest);
    renderCycle(latest);
    renderLayers(latest, catalog);
    renderGlossary(catalog);
    A.text($('#f-updated'), 'Actualizado: ' + A.fmtDate(latest.generated_at));
  }).catch(function () {
    A.text($('#cyc-phase'), 'Datos no disponibles por el momento');
  });
  renderCycleHistory();
  live();
  setInterval(live, 60000);
})();
