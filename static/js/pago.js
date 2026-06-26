
// ── Tabs ────────────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('.pg-section').forEach(s => s.classList.remove('active'));
  var section = document.getElementById('tab-' + name);
  if (section) section.classList.add('active');
}

// ── Registrar pago ──────────────────────────────────────────
function registrarPago(numeroOrden, ordenId, cliente, total) {
  const ordenSelect = document.querySelector('[name="pedido"]');
  if (ordenSelect) ordenSelect.value = ordenId;
  document.getElementById('orden-banner').classList.add('visible');
  document.getElementById('banner-orden-num').textContent = numeroOrden;
  document.getElementById('banner-cliente').textContent   = cliente;
  document.getElementById('banner-total').textContent     = '$' + Number(total).toLocaleString('es-CO');
  document.getElementById('form-titulo').textContent      = 'Pago — ' + numeroOrden;
  showTab('crear');
}

function cancelarPago() {
  const ordenSelect = document.querySelector('[name="pedido"]');
  if (ordenSelect) ordenSelect.value = '';
  document.getElementById('orden-banner').classList.remove('visible');
  document.getElementById('form-titulo').textContent = 'Registrar Pago';
  showTab('pendientes');
}

// ── Eliminar pago ───────────────────────────────────────────
function confirmarEliminar(pk, referencia) {
  document.getElementById('modal-form').action = `/pagos/${pk}/eliminar/`;
  document.getElementById('modal-msg').textContent =
    `¿Eliminar el pago de la orden "${referencia}"? Esta acción no se puede deshacer.`;
  document.getElementById('modal-eliminar').classList.add('open');
}
function cerrarModal() {
  document.getElementById('modal-eliminar').classList.remove('open');
}

// ── Cerrar caja ─────────────────────────────────────────────
function confirmarCierreCaja(cajaId, cajero) {
  document.getElementById('modal-cierre-caja-id').value = cajaId;
  document.getElementById('modal-cierre-msg').textContent =
    `¿Confirmas el cierre de la Caja #${cajaId} (${cajero})?`;
  document.getElementById('modal-cerrar-caja').classList.add('open');
}
function cerrarModalCierre() {
  document.getElementById('modal-cerrar-caja').classList.remove('open');
}

// ── Editar caja (AJAX) ──────────────────────────────────────
let _editandoCajaId = null;

function abrirEditarCaja(cajaId) {
  _editandoCajaId = cajaId;

  const fila = document.querySelector(`[data-caja-pk="${cajaId}"]`);
  const cajeroActual = fila ? fila.querySelector('[data-col="cajero"]').textContent.trim() : '';
  const obsActual    = fila ? fila.querySelector('[data-col="observaciones"]').textContent.trim() : '';

  document.getElementById('editar-cajero').value        = cajeroActual;
  document.getElementById('editar-observaciones').value = obsActual === '—' ? '' : obsActual;
  document.getElementById('modal-editar-titulo').textContent = 'Editando Caja #' + cajaId;

  const fb = document.getElementById('editar-feedback');
  fb.style.display = 'none';
  fb.textContent   = '';

  const btn = document.getElementById('btn-guardar-caja');
  btn.disabled    = false;
  btn.textContent = '💾 Guardar cambios';

  document.getElementById('modal-editar-caja').classList.add('open');
}

function cerrarEditarCaja() {
  document.getElementById('modal-editar-caja').classList.remove('open');
}

function guardarEditarCaja() {
  const cajero        = document.getElementById('editar-cajero').value.trim();
  const observaciones = document.getElementById('editar-observaciones').value.trim();
  const btn           = document.getElementById('btn-guardar-caja');
  const fb            = document.getElementById('editar-feedback');

  if (!cajero) {
    mostrarFeedback(fb, 'error', '⚠️ El nombre del cajero no puede estar vacío.');
    return;
  }

  btn.disabled    = true;
  btn.textContent = 'Guardando…';

  const formData = new FormData();
  formData.append('action',               'editar_caja');
  formData.append('caja_id',             _editandoCajaId);
  formData.append('cajero',              cajero);
  formData.append('observaciones',       observaciones);
  formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

  fetch("{% url 'pago:dashboard' %}", { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      btn.disabled    = false;
      btn.textContent = '💾 Guardar cambios';

      if (data.ok) {
        const fila = document.querySelector(`[data-caja-pk="${_editandoCajaId}"]`);
        if (fila) {
          const tdCajero = fila.querySelector('[data-col="cajero"]');
          const tdObs    = fila.querySelector('[data-col="observaciones"]');
          if (tdCajero) tdCajero.textContent = data.cajero;
          if (tdObs)    tdObs.textContent    = data.observaciones;
        }
        mostrarFeedback(fb, 'success', '✅ Cambios guardados correctamente.');
        setTimeout(cerrarEditarCaja, 1200);
      } else {
        mostrarFeedback(fb, 'error', '❌ ' + (data.error || 'Error al guardar.'));
      }
    })
    .catch(() => {
      btn.disabled    = false;
      btn.textContent = '💾 Guardar cambios';
      mostrarFeedback(fb, 'error', '❌ Error de conexión. Intenta de nuevo.');
    });
}

function mostrarFeedback(el, tipo, texto) {
  el.textContent           = texto;
  el.style.display         = 'block';
  el.style.background      = tipo === 'success' ? '#FFF0DC' : '#FAE0DC';
  el.style.color           = tipo === 'success' ? '#C0502A' : '#C0392B';
  el.style.borderLeftColor = tipo === 'success' ? 'var(--p-accent)' : 'var(--p-primary)';
}

function getCookie(name) {
  let v = null;
  document.cookie.split(';').forEach(c => {
    const [k, val] = c.trim().split('=');
    if (k === name) v = decodeURIComponent(val);
  });
  return v;
}

// ── Fecha apertura ──────────────────────────────────────────
function setFechaApertura() {
  const el = document.getElementById('fecha-apertura-display');
  if (!el) return;
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  el.value = `${pad(now.getDate())}/${pad(now.getMonth()+1)}/${now.getFullYear()}  ${pad(now.getHours())}:${pad(now.getMinutes())}`;
}
setFechaApertura();
setInterval(setFechaApertura, 30000);

// ── Cerrar modales al clic en overlay ──────────────────────
document.getElementById('modal-eliminar').addEventListener('click',     function(e){ if(e.target===this) cerrarModal(); });
document.getElementById('modal-cerrar-caja').addEventListener('click',  function(e){ if(e.target===this) cerrarModalCierre(); });
document.getElementById('modal-editar-caja').addEventListener('click',  function(e){ if(e.target===this) cerrarEditarCaja(); });
document.getElementById('modal-pago-exito').addEventListener('click',   function(e){ if(e.target===this) this.classList.remove('open'); });
// ── Buscador de pagos (client-side) ─────────────────────────
function filtrarPagos() {
  const texto  = document.getElementById('buscador-pagos').value.toLowerCase().trim();
  const metodo = document.getElementById('filtro-metodo').value;
  const filas  = document.querySelectorAll('.fila-pago');
  const grupos = document.querySelectorAll('[data-fecha-grupo]');
  let hayAlgo  = false;

  filas.forEach(function(fila) {
    const orden      = fila.dataset.orden      || '';
    const cliente    = fila.dataset.cliente    || '';
    const referencia = fila.dataset.referencia || '';
    const mFila      = fila.dataset.metodo     || '';
    const coincideTexto  = !texto  || orden.includes(texto) || cliente.includes(texto) || referencia.includes(texto);
    const coincideMetodo = !metodo || mFila === metodo;
    if (coincideTexto && coincideMetodo) {
      fila.classList.remove('fila-oculta'); hayAlgo = true;
    } else {
      fila.classList.add('fila-oculta');
    }
  });

  grupos.forEach(function(grupo) {
    const visibles = grupo.querySelectorAll('.fila-pago:not(.fila-oculta)');
    grupo.style.display = visibles.length > 0 ? '' : 'none';
  });

  const sinRes = document.getElementById('sin-resultados');
  if (sinRes) sinRes.style.display = hayAlgo ? 'none' : 'block';
}

// ── Init ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

    if (window.pagoConfig?.formErrors) {
        showTab('crear');
    } 
    else if (window.pagoConfig?.aperturaErrors) {
        showTab('abrir-caja');
    } 
    else if (window.pagoConfig?.tabActivo) {
        showTab(window.pagoConfig.tabActivo);
    }

});
