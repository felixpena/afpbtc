/* AFPBTC — panel de métricas (uPlot) */
(function () {
  'use strict';
  var A = window.AFP, $ = A.$;
  var DAY = 86400;
  var HALVING_2024 = Date.UTC(2024, 3, 20) / 1000;
  var RANGE_LABEL = { '365': 'último año', '1461': 'últimos 4 años', cycle: 'ciclo actual (desde el halving de abril 2024)', all: 'todo el histórico' };

  var state = { catalog: null, latest: null, byId: {}, id: null, range: 'all', logPrice: true, plot: null, data: null };

  /* ---------- Barra lateral ---------- */
  function buildSide() {
    var side = $('#side');
    side.innerHTML = '';
    var groups = state.catalog.groups.slice();
    // El termómetro va primero: es la puerta de entrada.
    groups.sort(function (a, b) { return (a === 'Ciclo' ? -1 : 0) - (b === 'Ciclo' ? -1 : 0); });
    groups.forEach(function (g) {
      var items = state.catalog.metrics.filter(function (m) { return m.group === g; });
      if (!items.length) return;
      var wrap = document.createElement('div');
      wrap.className = 'side-group';
      var h = document.createElement('h2');
      h.textContent = g;
      wrap.appendChild(h);
      items.forEach(function (m) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'side-item';
        b.dataset.id = m.id;
        b.dataset.search = (m.name + ' ' + m.group + ' ' + m.what).toLowerCase();
        b.textContent = m.name;
        if (m.source === 'afpbtc') {
          var s = document.createElement('span');
          s.className = 'src';
          s.textContent = 'AFPBTC';
          b.appendChild(s);
        }
        b.addEventListener('click', function () { select(m.id, true); });
        wrap.appendChild(b);
      });
      side.appendChild(wrap);
    });
  }

  function markSide() {
    document.querySelectorAll('.side-item').forEach(function (b) {
      var on = b.dataset.id === state.id;
      b.setAttribute('aria-current', on ? 'true' : 'false');
      if (on && window.innerWidth < 860) b.scrollIntoView({ block: 'nearest', inline: 'center' });
    });
  }

  $('#search').addEventListener('input', function (e) {
    var q = e.target.value.trim().toLowerCase();
    document.querySelectorAll('.side-item').forEach(function (b) {
      b.hidden = q && b.dataset.search.indexOf(q) === -1;
    });
    document.querySelectorAll('.side-group').forEach(function (g) {
      var any = Array.prototype.some.call(g.querySelectorAll('.side-item'), function (b) { return !b.hidden; });
      g.hidden = !any;
    });
  });

  /* ---------- Datos ---------- */
  function align(metric, price) {
    var t0 = Math.min(metric.t[0], price.t[0]);
    var t1 = Math.max(metric.t[metric.t.length - 1], price.t[price.t.length - 1]);
    var n = Math.round((t1 - t0) / DAY) + 1;
    var x = new Array(n), m = new Array(n), p = new Array(n);
    for (var i = 0; i < n; i++) { x[i] = t0 + i * DAY; m[i] = null; p[i] = null; }
    var om = Math.round((metric.t[0] - t0) / DAY), op = Math.round((price.t[0] - t0) / DAY);
    for (var j = 0; j < metric.v.length; j++) m[om + j] = metric.v[j];
    for (var k = 0; k < price.v.length; k++) p[op + k] = price.v[k];
    return [x, m, p];
  }

  function sliceRange(data) {
    var x = data[0];
    var last = x[x.length - 1];
    var from;
    if (state.range === 'all') {
      // Empieza donde la métrica tiene datos.
      var f = data[1].findIndex(function (v) { return v !== null; });
      from = x[Math.max(0, f)];
    } else if (state.range === 'cycle') from = HALVING_2024;
    else from = last - parseInt(state.range, 10) * DAY;
    var i0 = x.findIndex(function (t) { return t >= from; });
    if (i0 < 0) i0 = 0;
    return [x.slice(i0), data[1].slice(i0), data[2].slice(i0)];
  }

  /* ---------- Gráfico ---------- */
  function zonesPlugin(hints, scaleKey) {
    return {
      hooks: {
        drawClear: function (u) {
          var ctx = u.ctx, bb = u.bbox;
          ctx.save();
          if (hints.high !== undefined) {
            var yh = u.valToPos(hints.high, scaleKey, true);
            if (yh > bb.top) { ctx.fillStyle = 'rgba(184,68,30,0.16)'; ctx.fillRect(bb.left, bb.top, bb.width, Math.min(yh, bb.top + bb.height) - bb.top); }
          }
          if (hints.low !== undefined) {
            var yl = u.valToPos(hints.low, scaleKey, true);
            if (yl < bb.top + bb.height) { ctx.fillStyle = 'rgba(46,125,175,0.18)'; var top = Math.max(yl, bb.top); ctx.fillRect(bb.left, top, bb.width, bb.top + bb.height - top); }
          }
          if (hints.ref !== undefined) {
            var yr = u.valToPos(hints.ref, scaleKey, true);
            if (yr > bb.top && yr < bb.top + bb.height) {
              ctx.strokeStyle = 'rgba(237,234,227,0.45)'; ctx.setLineDash([5, 5]); ctx.lineWidth = 1;
              ctx.beginPath(); ctx.moveTo(bb.left, yr); ctx.lineTo(bb.left + bb.width, yr); ctx.stroke();
            }
          }
          ctx.restore();
        }
      }
    };
  }

  function axisFmt(unit) {
    return function (u, vals) {
      return vals.map(function (v) {
        if (v === null) return '';
        if (unit === 'USD') {
          var a = Math.abs(v);
          if (a >= 1e12) return '$' + (v / 1e12).toLocaleString('es-CL', { maximumFractionDigits: 1 }) + 'B';
          if (a >= 1e9) return '$' + (v / 1e9).toLocaleString('es-CL', { maximumFractionDigits: 1 }) + 'mM';
          if (a >= 1e6) return '$' + (v / 1e6).toLocaleString('es-CL', { maximumFractionDigits: 1 }) + 'M';
          if (a >= 1e3) return '$' + (v / 1e3).toLocaleString('es-CL', { maximumFractionDigits: 0 }) + 'k';
          return '$' + v.toLocaleString('es-CL', { maximumFractionDigits: 2 });
        }
        if (Math.abs(v) >= 1e6) return (v / 1e6).toLocaleString('es-CL', { maximumFractionDigits: 1 }) + 'M';
        if (Math.abs(v) >= 1e3) return (v / 1e3).toLocaleString('es-CL', { maximumFractionDigits: 1 }) + 'k';
        return v.toLocaleString('es-CL', { maximumFractionDigits: Math.abs(v) < 0.01 ? 5 : 2 });
      });
    };
  }

  function chartHeight() { return window.innerWidth < 640 ? 300 : 400; }

  function draw() {
    var meta = state.byId[state.id];
    var hints = meta.chart || {};
    var box = $('#chart');
    var d = sliceRange(state.data);
    var sameAxis = !!hints.same_axis_as_price;
    var mKey = sameAxis ? 'p' : 'm';

    // La escala log no admite ceros ni negativos.
    if (hints.log || sameAxis) d[1] = d[1].map(function (v) { return v !== null && v > 0 ? v : null; });
    if (state.logPrice) d[2] = d[2].map(function (v) { return v !== null && v > 0 ? v : null; });

    var grid = { stroke: 'rgba(237,234,227,0.07)', width: 1 };
    var ticks = { stroke: 'rgba(237,234,227,0.15)', width: 1, size: 4 };
    var font = '12px "JetBrains Mono", monospace';

    var scales = { x: { time: true }, p: { distr: state.logPrice || sameAxis ? 3 : 1 } };
    if (!sameAxis) {
      scales.m = { distr: hints.log ? 3 : 1 };
      if (hints.min !== undefined) scales.m.range = [hints.min, hints.max];
    }

    var axes = [
      { stroke: '#A39E93', grid: grid, ticks: ticks, font: font, space: 70 },
      { scale: mKey, stroke: '#F7931A', grid: grid, ticks: ticks, font: font, size: 64, values: axisFmt(sameAxis ? 'USD' : meta.unit) }
    ];
    if (!sameAxis) axes.push({ scale: 'p', side: 1, stroke: '#8C877D', grid: { show: false }, ticks: ticks, font: font, size: 64, values: axisFmt('USD') });

    var opts = {
      width: box.clientWidth || 800,
      height: chartHeight(),
      cursor: { drag: { x: true, y: false }, points: { size: 6 } },
      legend: { live: true },
      scales: scales,
      axes: axes,
      series: [
        { label: 'Fecha', value: function (u, v) { return v === null ? '—' : new Date(v * 1000).toLocaleDateString('es-CL', { timeZone: 'UTC' }); } },
        { label: meta.name, scale: mKey, stroke: '#F7931A', width: 2, spanGaps: false,
          value: function (u, v) { return A.fmt(v, meta.unit); } },
        { label: 'Precio BTC', scale: 'p', stroke: sameAxis ? '#EDEAE3' : '#8C877D', width: 1.4,
          value: function (u, v) { return A.fmt(v, 'USD'); } }
      ],
      plugins: [zonesPlugin(hints, mKey)]
    };

    if (state.plot) { state.plot.destroy(); state.plot = null; }
    box.innerHTML = '';
    state.plot = new uPlot(opts, d, box);

    A.text($('#m-caption'), 'Fuente: ' + meta.source_label + ' · Datos al ' + A.fmtDate((state.latest.metrics[state.id] || {}).date) +
      ' · Rango: ' + RANGE_LABEL[state.range] + ' · Arrastra sobre el gráfico para hacer zoom; doble clic para volver.' +
      (hints.high !== undefined || hints.low !== undefined ? ' Bandas: zonas históricas de sobrecalentamiento (rojo) y acumulación (azul).' : ''));
  }

  /* ---------- Selección de métrica ---------- */
  function select(id, push) {
    if (!state.byId[id]) id = 'mvrv_zscore';
    state.id = id;
    var m = state.byId[id];
    markSide();
    if (push) history.replaceState(null, '', '?m=' + id);
    document.title = m.name + ' — Panel onchain AFPBTC';
    A.text($('#m-group'), m.group);
    A.text($('#m-name'), m.name);
    A.text($('#m-what'), m.what);
    A.text($('#m-formula'), m.formula);
    A.text($('#m-read'), m.read);
    A.text($('#m-limits'), m.limits);
    var csv = $('#csv');
    csv.href = m.csv_url;
    csv.setAttribute('download', 'afpbtc-' + id + '.csv');

    var l = state.latest.metrics[id];
    A.text($('#m-value'), l ? A.fmt(l.value, m.unit) : '—');
    A.text($('#m-date'), l ? '· ' + A.fmtDate(l.date) : '');
    var ch = $('#m-change');
    ch.innerHTML = '';
    if (l) {
      [['7 d', l.change_7d_pct], ['30 d', l.change_30d_pct]].forEach(function (p, i) {
        if (p[1] === null || p[1] === undefined) return;
        var s = document.createElement('span');
        s.className = p[1] >= 0 ? 'up' : 'down';
        s.textContent = (i ? '  ' : '') + A.pct(p[1]) + ' ' + p[0];
        ch.appendChild(s);
      });
    }

    $('#chart').innerHTML = '<div class="chart-msg">Cargando datos…</div>';
    Promise.all([A.series(id), A.series('price')]).then(function (r) {
      if (state.id !== id) return;
      state.data = align(r[0], r[1]);
      draw();
    }).catch(function () {
      $('#chart').innerHTML = '<div class="chart-msg">No se pudieron cargar los datos de esta métrica.</div>';
    });
    if (window.innerWidth < 860 && push) $('#contenido').scrollIntoView({ behavior: 'smooth' });
  }

  /* ---------- Controles ---------- */
  document.querySelectorAll('[data-range]').forEach(function (b) {
    b.addEventListener('click', function () {
      state.range = b.dataset.range;
      document.querySelectorAll('[data-range]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      if (state.data) draw();
    });
  });
  $('#log-toggle').addEventListener('click', function (e) {
    state.logPrice = !state.logPrice;
    e.currentTarget.setAttribute('aria-pressed', state.logPrice ? 'true' : 'false');
    if (state.data) draw();
  });

  var rt;
  window.addEventListener('resize', function () {
    clearTimeout(rt);
    rt = setTimeout(function () {
      if (state.plot) state.plot.setSize({ width: $('#chart').clientWidth, height: chartHeight() });
    }, 120);
  });

  /* ---------- Inicio ---------- */
  Promise.all([A.getJSON('/data/catalog.json'), A.getJSON('/data/latest.json')]).then(function (r) {
    state.catalog = r[0];
    state.latest = r[1];
    state.catalog.metrics.forEach(function (m) { state.byId[m.id] = m; });
    A.text($('#attr'), state.catalog.attribution);
    buildSide();
    var q = new URLSearchParams(location.search).get('m');
    select(q || 'mvrv_zscore', false);
  }).catch(function () {
    A.text($('#m-name'), 'Datos no disponibles');
    $('#chart').innerHTML = '<div class="chart-msg">No se pudo cargar el catálogo de métricas. Intenta de nuevo en unos minutos.</div>';
  });
})();
