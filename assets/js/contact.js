/* AFPBTC — formulario de contacto (Formspree, envío sin recargar) */
(function () {
  'use strict';
  var form = document.getElementById('contact-form');
  if (!form) return;
  var status = document.getElementById('c-status');
  var btn = document.getElementById('c-submit');
  var topic = document.getElementById('c-topic');
  var subject = document.getElementById('c-subject');

  // Preselecciona el interés desde los botones del sitio: /contacto/?interes=patrimonio
  var map = { sesion: 'Sesión 1 a 1', patrimonio: 'Gestión patrimonial', research: 'Research / prensa', otro: 'Otro' };
  var q = new URLSearchParams(location.search).get('interes');
  if (q && map[q]) topic.value = map[q];

  function setStatus(msg, kind) {
    status.textContent = msg;
    status.className = 'form-status' + (kind ? ' ' + kind : '');
  }

  form.addEventListener('input', function () {
    if (status.classList.contains('err')) setStatus('');
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      setStatus('Revisa los campos marcados.', 'err');
      return;
    }
    subject.value = 'afpbtc.com · ' + topic.value + ' · ' + document.getElementById('c-name').value.trim();
    btn.disabled = true;
    btn.textContent = 'Enviando…';
    setStatus('');
    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { Accept: 'application/json' }
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) { return { ok: r.ok, data: data }; });
    }).then(function (res) {
      if (res.ok) {
        form.reset();
        setStatus('¡Gracias! Recibimos tu mensaje y te responderemos por correo.', 'ok');
        btn.textContent = 'Mensaje enviado';
        return;
      }
      var detail = res.data && res.data.errors ? res.data.errors.map(function (x) { return x.message; }).join(' ') : '';
      throw new Error(detail);
    }).catch(function (err) {
      btn.disabled = false;
      btn.textContent = 'Enviar mensaje';
      setStatus('No pudimos enviar el mensaje. ' + (err && err.message ? err.message + ' ' : '') + 'Inténtalo de nuevo en unos minutos.', 'err');
    });
  });
})();
