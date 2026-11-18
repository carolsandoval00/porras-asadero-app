/**
 * Muestra una pestaña específica en la interfaz ocultando las demás secciones.
 *
 * @param {string} name - Nombre identificador de la pestaña a mostrar.
 */
function showTab(name) {
  document.querySelectorAll('.pg-section').forEach(s => s.classList.remove('active'));
  var section = document.getElementById('tab-' + name);
  if (section) section.classList.add('active');
}

/**
 * Prepara el formulario para registrar un pago asociado a una orden y activa la pestaña correspondiente.
 *
 * @param {string} numeroOrden - Número identificador visible de la orden.
 * @param {number} ordenId - ID interno de la orden en la base de datos.
 * @param {string} cliente - Nombre del cliente asociado a la orden.
 * @param {number|string} total - Monto total a pagar.
 */
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
  const obsActual = fila ? fila.querySelector('[data-col="observaciones"]').textContent.trim() : '';

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
  const observaciones = document.getElementById('editar-observaciones').value.trim();
  const btn           = document.getElementById('btn-guardar-caja');
  const fb            = document.getElementById('editar-feedback');

  btn.disabled    = true;
  btn.textContent = 'Guardando…';

  const formData = new FormData();
  formData.append('action',               'editar_caja');
  formData.append('caja_id',             _editandoCajaId);
  formData.append('observaciones',       observaciones);
  formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

  fetch(window.pagoConfig.dashboardUrl, { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      btn.disabled    = false;
      btn.textContent = '💾 Guardar cambios';

      if (data.ok) {
        const fila = document.querySelector(`[data-caja-pk="${_editandoCajaId}"]`);
        if (fila) {
          const tdObs = fila.querySelector('[data-col="observaciones"]');
          if (tdObs) tdObs.textContent = data.observaciones;
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


// ── Foto del comprobante (solo transferencia) ───────────────
const MAX_FOTO_MB = 8;

function formatoPeso(bytes) {
  return bytes >= 1048576
    ? (bytes / 1048576).toFixed(1) + ' MB'
    : Math.max(1, Math.round(bytes / 1024)) + ' KB';
}

document.addEventListener('DOMContentLoaded', function () {
  const metodo   = document.querySelector('[name="metodo_pago"]');
  const archivo  = document.getElementById('id_comprobante');
  const bloque   = document.getElementById('bloque-comprobante');
  if (!metodo || !archivo || !bloque) return;

  const drop     = document.getElementById('upload-drop');
  const result   = document.getElementById('upload-result');
  const preview  = document.getElementById('preview-comprobante');
  const nombre   = document.getElementById('upload-nombre');
  const peso     = document.getElementById('upload-peso');
  const errorMsg = document.getElementById('upload-error');
  let urlActual  = null;

  function mostrarError(texto) {
    errorMsg.textContent = texto;
    errorMsg.hidden = !texto;
    bloque.classList.toggle('has-error', !!texto);
  }

  function limpiarFoto() {
    archivo.value = '';
    if (urlActual) { URL.revokeObjectURL(urlActual); urlActual = null; }
    preview.removeAttribute('src');
    result.hidden = true;
    drop.hidden = false;
  }

  function actualizarVisibilidad() {
    const esTransferencia = metodo.value === 'TRANSFERENCIA';
    bloque.hidden = !esTransferencia;
    if (!esTransferencia) { limpiarFoto(); mostrarError(''); }
  }

  archivo.addEventListener('change', function () {
    const f = archivo.files && archivo.files[0];
    if (!f) { limpiarFoto(); return; }

    if (f.size > MAX_FOTO_MB * 1048576) {
      limpiarFoto();
      mostrarError('La foto es demasiado pesada (máximo ' + MAX_FOTO_MB + ' MB).');
      return;
    }
    if (urlActual) URL.revokeObjectURL(urlActual);
    urlActual = URL.createObjectURL(f);
    preview.src = urlActual;
    nombre.textContent = f.name;
    peso.textContent = formatoPeso(f.size);
    drop.hidden = true;
    result.hidden = false;
    mostrarError('');
  });

  document.getElementById('upload-cambiar').addEventListener('click', function () { archivo.click(); });
  document.getElementById('upload-quitar').addEventListener('click', function () { limpiarFoto(); });

  metodo.addEventListener('change', actualizarVisibilidad);

  // Si es transferencia y no hay foto, no deja enviar (el servidor también lo valida).
  if (archivo.form) {
    archivo.form.addEventListener('submit', function (e) {
      if (metodo.value === 'TRANSFERENCIA' && !(archivo.files && archivo.files.length)) {
        e.preventDefault();
        mostrarError('Debes tomar la foto del comprobante para pagos por transferencia.');
        bloque.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
  }

  actualizarVisibilidad();
});