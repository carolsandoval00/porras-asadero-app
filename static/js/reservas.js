/* ============================================================
   Reservas y mesas — Asadero Porras
   Todo el estado vive en la base de datos de Django.
   Este archivo solo pinta la interfaz y llama a la API:
     GET  /reservas/api/reservas/           (admite filtros)
     POST /reservas/api/reservas/guardar/
     POST /reservas/api/reservas/eliminar/
     GET  /reservas/api/mesas/
     POST /reservas/api/mesas/guardar/
     POST /reservas/api/mesas/eliminar/
   ============================================================ */
(function () {
  'use strict';

  const API = {
    reservas:        '/reservas/api/reservas/',
    reservaGuardar:  '/reservas/api/reservas/guardar/',
    reservaEliminar: '/reservas/api/reservas/eliminar/',
    mesas:           '/reservas/api/mesas/',
    mesaGuardar:     '/reservas/api/mesas/guardar/',
    mesaEliminar:    '/reservas/api/mesas/eliminar/',
  };

  // Estado en memoria: copia de lo que devolvió el servidor.
  let reservas = [];          // reservas de la tabla (respetan los filtros de la tabla)
  let reservasDiagrama = [];  // TODAS las reservas, sin filtros (para el diagrama y el detalle de mesa)
  let mesas = [];
  let editandoId = null;          // id de reserva en edición
  let editandoMesaNumero = null;  // número de mesa en edición

  // ★ PAGINACIÓN de la tabla de reservas (se hace en el navegador)
  const POR_PAGINA = 10;          // reservas por página
  let paginaActual = 1;

  const soloLectura = () => window.MC_PUEDE_EDITAR === false;

  // ─── Utilidades ───────────────────────────────────────────
  function $(id) { return document.getElementById(id); }

  function hoy() {
    const d = new Date();
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      .toISOString().slice(0, 10);
  }

  function esc(valor) {
    return String(valor == null ? '' : valor)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function getCookie(name) {
    let value = null;
    if (document.cookie) {
      document.cookie.split(';').forEach(c => {
        const cv = c.trim();
        if (cv.startsWith(name + '=')) value = decodeURIComponent(cv.substring(name.length + 1));
      });
    }
    return value;
  }

  async function apiGet(url, params) {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    const res = await fetch(url + qs, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.error || 'Error al consultar el servidor');
    return data;
  }

  async function apiPost(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.error || 'Error al guardar en el servidor');
    return data;
  }

  // ─── Etiquetas y clases de estado ─────────────────────────
  const ETIQUETA_RESERVA = { PENDIENTE: 'Pendiente', CONFIRMADA: 'Confirmada', CANCELADA: 'Cancelada' };
  const ETIQUETA_MESA    = { LIBRE: 'Disponible', RESERVADA: 'Reservada', OCUPADA: 'Ocupada' };
  // Clase CSS de cada estado de mesa (definidas en reservas.css: .mc-mesa.disponible, etc.)
  const CLASE_MESA       = { LIBRE: 'disponible', RESERVADA: 'reservada', OCUPADA: 'ocupada' };

  // Colores en línea para el borde/fondo de cada mesa: así el color sale aunque el CSS
  // esté en caché o lo pise otra regla.
  const ESTILO_MESA = {
    LIBRE:     'background:#DFF5E1;border-color:#3B6D11;color:#1A6B2A;',
    RESERVADA: 'background:#FAEEDA;border-color:#E8651A;color:#8B4000;',
    OCUPADA:   'background:#FAE0DC;border-color:#C0392B;color:#C0392B;',
  };

  function badgeClass(estado) {
    if (estado === 'CONFIRMADA' || estado === 'LIBRE') return 'mc-badge-ok';
    if (estado === 'PENDIENTE' || estado === 'RESERVADA') return 'mc-badge-warn';
    return 'mc-badge-danger';
  }

  // Normaliza lo que llega del servidor para que no importe si viene como
  // "LIBRE", "libre" o "Disponible": internamente siempre es LIBRE/RESERVADA/OCUPADA.
  function normalizarEstadoMesa(e) {
    const v = String(e == null ? '' : e).trim().toUpperCase();
    if (v === 'DISPONIBLE') return 'LIBRE';
    return v;
  }

  function normalizarMesa(m) {
    return Object.assign({}, m, {
      numero:    Number(m.numero),
      capacidad: Number(m.capacidad),
      estado:    normalizarEstadoMesa(m.estado),
    });
  }

  function normalizarReserva(r) {
    return Object.assign({}, r, {
      estado: String(r.estado == null ? '' : r.estado).trim().toUpperCase(),
      mesa:   (r.mesa == null || r.mesa === '') ? null : Number(r.mesa),
    });
  }

  function getMesa(numero)      { return mesas.find(m => m.numero === Number(numero)); }
  function getMesaLabel(numero) { const m = getMesa(numero); return m ? 'Mesa ' + m.numero : '—'; }

  // ─── Modales / avisos ─────────────────────────────────────
  // Aviso en modal. `titulo` es opcional; si no se pasa se usa uno por defecto.
  function toast(msg, tipo, titulo) {
    const tit = $('mc-msg-title'), texto = $('mc-msg-text'), overlay = $('mc-msg-overlay');
    if (!overlay) { console.log(msg); return; }
    tit.textContent = titulo || (tipo === 'error' ? 'Atención' : '¡Listo!');
    texto.textContent = msg;
    overlay.classList.toggle('error', tipo === 'error');
    overlay.classList.add('open');
  }

  window.mcCloseMsg = function () {
    const el = $('mc-msg-overlay');
    if (el) el.classList.remove('open');
  };

  window.mcCloseConfirm = function () {
    const el = $('mc-confirm-overlay');
    if (el) el.classList.remove('open');
  };

  function mcConfirm(titulo, msg, cb) {
    $('mc-confirm-title').textContent = titulo;
    $('mc-confirm-msg').textContent = msg;
    $('mc-confirm-ok').onclick = () => { mcCloseConfirm(); cb(); };
    $('mc-confirm-overlay').classList.add('open');
  }

  window.mcCloseModal = function (id) {
    const el = $(id);
    if (el) el.classList.remove('open');
  };

  // ─── Navegación entre secciones ───────────────────────────
  window.mcShow = function (id) {
    if (soloLectura() && (id === 'crear' || id === 'crear-mesa')) {
      toast('No tienes permisos para realizar esta acción', 'error');
      return;
    }
    document.querySelectorAll('.mc-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.mc-nav-btn').forEach(b => b.classList.remove('active'));
    const sec = $('mc-' + id);
    if (sec) sec.classList.add('active');
    document.querySelectorAll('.mc-nav-btn').forEach(b => {
      const oc = b.getAttribute('onclick');
      if (oc && oc.includes("'" + id + "'")) b.classList.add('active');
    });

    if (id === 'reservas')   mcRenderTabla();
    // El diagrama se muestra "en tiempo real": se vuelven a pedir las mesas al servidor.
    if (id === 'mesas')      cargarMesas().then(() => mcRenderDiagrama());
    if (id === 'crear-mesa') mcRenderTablaMesas();
    if (id === 'crear' && !editandoId) { mcLimpiar(); }
  };

  // ─── Carga de datos desde el servidor ─────────────────────
  function filtrosActuales() {
    const filtros = {};
    const buscar = $('mc-buscar');
    const fecha  = $('mc-filtro-fecha');
    const dia    = $('mc-filtro-fecha-dia');
    const mes    = $('mc-filtro-fecha-mes');
    const desde  = $('mc-filtro-desde');
    const hasta  = $('mc-filtro-hasta');
    const estado = $('mc-filtro-estado');

    if (buscar && buscar.value.trim()) filtros.q = buscar.value.trim();
    if (estado && estado.value) filtros.estado = estado.value;
    if (fecha && fecha.value) {
      filtros.fecha = fecha.value;
      if (fecha.value === 'dia' && dia && dia.value) filtros.dia = dia.value;
      if (fecha.value === 'mes' && mes && mes.value) filtros.mes = mes.value;
      if (fecha.value === 'rango') {
        if (desde && desde.value) filtros.desde = desde.value;
        if (hasta && hasta.value) filtros.hasta = hasta.value;
      }
    }
    return filtros;
  }

  async function cargarReservas() {
    try {
      const data = await apiGet(API.reservas, filtrosActuales());
      reservas = data.reservas.map(normalizarReserva);
      return true;
    } catch (e) {
      console.error(e);
      toast('No se pudieron cargar las reservas: ' + e.message, 'error');
      return false;
    }
  }

  // Todas las reservas SIN filtros: las usa el diagrama (tooltip) y el detalle de cada mesa,
  // para que no dependan de los filtros que haya puesto el usuario en la tabla de reservas.
  async function cargarReservasDiagrama() {
    try {
      const data = await apiGet(API.reservas);
      reservasDiagrama = data.reservas.map(normalizarReserva);
      return true;
    } catch (e) {
      console.error(e);
      return false;
    }
  }

  async function cargarMesas() {
    try {
      const data = await apiGet(API.mesas);
      mesas = data.mesas.map(normalizarMesa);
      return true;
    } catch (e) {
      console.error(e);
      toast('No se pudieron cargar las mesas: ' + e.message, 'error');
      return false;
    }
  }

  // Reservas vigentes (no canceladas, de hoy en adelante) de una mesa, ordenadas por fecha y hora.
  function reservasVigentesDeMesa(numero) {
    const hoyStr = hoy();
    return reservasDiagrama
      .filter(r => r.mesa === Number(numero) && r.estado !== 'CANCELADA' && String(r.fecha) >= hoyStr)
      .sort((a, b) => (String(a.fecha) + String(a.hora)).localeCompare(String(b.fecha) + String(b.hora)));
  }

  // Estado con el que se PINTA la mesa en el diagrama, calculado a partir de sus reservas:
  //   1. Si la mesa está OCUPADA (alguien sentado), se queda OCUPADA.
  //   2. Si tiene una reserva vigente (pendiente o confirmada) para HOY, se pinta RESERVADA.
  //   3. En cualquier otro caso se usa el estado guardado en la mesa.
  function estadoEfectivoMesa(m) {
    if (m.estado === 'OCUPADA') return 'OCUPADA';
    const hoyStr = hoy();
    const tieneHoy = reservasVigentesDeMesa(m.numero)
      .some(r => String(r.fecha).slice(0, 10) === hoyStr);
    if (tieneHoy) return 'RESERVADA';
    return m.estado;
  }

  // ─── Filtro por fechas ────────────────────────────────────
  // Muestra u oculta los campos según el modo elegido y recarga.
  window.mcToggleFiltroFecha = function () {
    const modo  = $('mc-filtro-fecha') ? $('mc-filtro-fecha').value : '';
    const dia   = $('mc-filtro-fecha-dia');
    const mes   = $('mc-filtro-fecha-mes');
    const rango = $('mc-filtro-rango');

    if (dia)   dia.style.display   = modo === 'dia'   ? 'block' : 'none';
    if (mes)   mes.style.display   = modo === 'mes'   ? 'block' : 'none';
    if (rango) rango.style.display = modo === 'rango' ? 'flex'  : 'none';

    // Al salir de un modo se limpia su valor para no arrastrar filtros ocultos.
    if (modo !== 'dia' && dia) dia.value = '';
    if (modo !== 'mes' && mes) mes.value = '';
    if (modo !== 'rango') {
      if ($('mc-filtro-desde')) $('mc-filtro-desde').value = '';
      if ($('mc-filtro-hasta')) $('mc-filtro-hasta').value = '';
    }
    mcRenderTabla();
  };

  window.mcLimpiarFiltros = function () {
    ['mc-buscar', 'mc-filtro-estado', 'mc-filtro-fecha',
     'mc-filtro-fecha-dia', 'mc-filtro-fecha-mes',
     'mc-filtro-desde', 'mc-filtro-hasta'].forEach(id => {
      const el = $(id);
      if (el) el.value = '';
    });
    mcToggleFiltroFecha();
  };

  // ─── Tabla de reservas (con paginación) ───────────────────
  // Números de página a mostrar: 1 … anterior, actual, siguiente … última
  function numerosPagina(actual, total) {
    const set = new Set([1, total, actual, actual - 1, actual + 1]);
    const nums = Array.from(set).filter(n => n >= 1 && n <= total).sort((a, b) => a - b);
    const resultado = [];
    let previo = 0;
    nums.forEach(n => {
      if (n - previo > 1) resultado.push('...');
      resultado.push(n);
      previo = n;
    });
    return resultado;
  }

  // Dibuja los botones de página debajo de la tabla.
  function mcRenderPaginacion() {
    const cont = $('mc-paginacion');
    if (!cont) return;

    const total = reservas.length;
    if (!total) { cont.innerHTML = ''; return; }

    const totalPaginas = Math.max(1, Math.ceil(total / POR_PAGINA));
    const inicio = (paginaActual - 1) * POR_PAGINA + 1;
    const fin = Math.min(paginaActual * POR_PAGINA, total);

    let links = '';
    if (paginaActual > 1) {
      links += `<button type="button" class="pm-btn pm-btn-light pm-btn-sm" onclick="mcIrPagina(${paginaActual - 1})">« Anterior</button>`;
    }
    numerosPagina(paginaActual, totalPaginas).forEach(n => {
      if (n === '...') {
        links += '<span class="mc-pag-puntos">…</span>';
      } else if (n === paginaActual) {
        links += `<span class="pm-btn pm-btn-primary pm-btn-sm mc-pag-actual">${n}</span>`;
      } else {
        links += `<button type="button" class="pm-btn pm-btn-light pm-btn-sm" onclick="mcIrPagina(${n})">${n}</button>`;
      }
    });
    if (paginaActual < totalPaginas) {
      links += `<button type="button" class="pm-btn pm-btn-light pm-btn-sm" onclick="mcIrPagina(${paginaActual + 1})">Siguiente »</button>`;
    }

    cont.innerHTML = `
      <div class="mc-pag-info">Mostrando ${inicio}–${fin} de ${total} reserva${total !== 1 ? 's' : ''}</div>
      <div class="mc-pag-links">${links}</div>`;
  }

  // Pinta la página actual con las reservas que ya están en memoria.
  function pintarTabla() {
    const tb = $('mc-tbody-reservas');
    if (!tb) return;

    const contador = $('mc-contador-reservas');
    if (contador) {
      contador.textContent = reservas.length + ' reserva' + (reservas.length !== 1 ? 's' : '');
    }

    if (!reservas.length) {
      tb.innerHTML = `<tr><td colspan="8"><div class="mc-empty">
        <div class="mc-empty-icon">&#128467;</div>
        <p>No se encontraron reservas con los filtros actuales</p>
      </div></td></tr>`;
      mcRenderPaginacion();
      return;
    }

    // Si la página actual quedó fuera de rango (por ejemplo al borrar), se ajusta.
    const totalPaginas = Math.max(1, Math.ceil(reservas.length / POR_PAGINA));
    if (paginaActual > totalPaginas) paginaActual = totalPaginas;
    if (paginaActual < 1) paginaActual = 1;

    const desde = (paginaActual - 1) * POR_PAGINA;
    const pagina = reservas.slice(desde, desde + POR_PAGINA);

    tb.innerHTML = pagina.map(r => `<tr>
      <td style="font-family:monospace;font-size:11px;color:var(--hint)">#${String(r.id).padStart(2, '0')}</td>
      <td>
        <div style="font-weight:500">${esc(r.nombre)}</div>
        <div style="font-size:12px;color:var(--muted)">${esc(r.telefono)}</div>
      </td>
      <td>${esc(getMesaLabel(r.mesa))}</td>
      <td>${esc(r.fecha)}</td>
      <td>${esc(r.hora)}</td>
      <td style="text-align:center">${esc(r.personas)}</td>
      <td><span class="mc-badge ${badgeClass(r.estado)}">${ETIQUETA_RESERVA[r.estado] || r.estado}</span></td>
      <td><div class="mc-action-btns">
        <button class="mc-icon-btn" onclick="mcVerReserva(${r.id})">Ver</button>
        ${!soloLectura() ? `
          <button class="mc-icon-btn edit" onclick="mcEditarReserva(${r.id})">Editar</button>
          <button class="mc-icon-btn del" onclick="mcPedirEliminarReserva(${r.id})">Borrar</button>
        ` : ''}
      </div></td>
    </tr>`).join('');

    mcRenderPaginacion();
  }

  // Cambia de página SIN volver a pedir los datos al servidor.
  window.mcIrPagina = function (n) {
    paginaActual = n;
    pintarTabla();
  };

  // Pide las reservas al servidor y las pinta.
  // Sin argumentos vuelve a la página 1 (al filtrar/buscar);
  // con `true` se queda en la página actual (al borrar, por ejemplo).
  window.mcRenderTabla = async function (mantenerPagina) {
    const tb = $('mc-tbody-reservas');
    if (!tb) return;

    if (mantenerPagina !== true) paginaActual = 1;

    tb.innerHTML = '<tr><td colspan="8"><div class="mc-empty"><p>Cargando…</p></div></td></tr>';
    await cargarReservas();
    pintarTabla();
  };

  window.mcVerReserva = function (id) {
    // Se busca en la tabla y, si no está (por los filtros), en la lista completa.
    const r = reservas.find(x => x.id === id) || reservasDiagrama.find(x => x.id === id);
    if (!r) return;
    $('mc-modal-r-title').textContent = 'Reserva — ' + r.nombre;
    $('mc-modal-r-body').innerHTML = `
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Cliente</div><div class="mc-detail-val">${esc(r.nombre)}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Teléfono</div><div class="mc-detail-val">${esc(r.telefono)}</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Email</div><div class="mc-detail-val" style="font-weight:400">${esc(r.email) || '—'}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Personas</div><div class="mc-detail-val">${esc(r.personas)}</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Fecha</div><div class="mc-detail-val">${esc(r.fecha)}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Hora</div><div class="mc-detail-val">${esc(r.hora)}</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Mesa</div><div class="mc-detail-val">${esc(getMesaLabel(r.mesa))}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Estado</div><div class="mc-detail-val"><span class="mc-badge ${badgeClass(r.estado)}">${ETIQUETA_RESERVA[r.estado] || r.estado}</span></div></div>
      </div>
      ${r.ocasion ? `<div class="mc-detail-item" style="margin-bottom:10px"><div class="mc-detail-key">Ocasión</div><div class="mc-detail-val">${esc(r.ocasion)}</div></div>` : ''}
      ${r.notas ? `<div class="mc-detail-item" style="margin-bottom:10px"><div class="mc-detail-key">Notas</div><div class="mc-detail-val" style="font-weight:400;font-size:13px;line-height:1.5">${esc(r.notas)}</div></div>` : ''}
      ${r.creada ? `<div style="font-size:11px;color:var(--hint);margin-bottom:1rem">Creada el ${new Date(r.creada).toLocaleString('es-CO')}</div>` : ''}
      <div class="mc-btn-row">
        <button class="mc-btn mc-btn-secondary" onclick="mcCloseModal('mc-modal-reserva')">Cerrar</button>
        ${!soloLectura() ? `<button class="mc-btn mc-btn-primary" onclick="mcCloseModal('mc-modal-reserva');mcEditarReserva(${r.id})">Editar reserva</button>` : ''}
      </div>`;
    $('mc-modal-reserva').classList.add('open');
  };

  // ─── Selector de mesas disponibles ────────────────────────
  window.mcPoblarMesas = async function () {
    const sel = $('mc-c-mesa');
    if (!sel) return;

    const fecha = $('mc-c-fecha') ? $('mc-c-fecha').value : '';
    const hora  = $('mc-c-hora') ? $('mc-c-hora').value : '';
    const seleccionActual = sel.value;

    const ocupadas = new Set();
    if (fecha) {
      // Se le pregunta al servidor qué mesas ya están tomadas ese día.
      try {
        const data = await apiGet(API.reservas, { fecha: 'dia', dia: fecha });
        data.reservas
          .map(normalizarReserva)
          .filter(r => r.estado !== 'CANCELADA' && r.id !== editandoId &&
                       (!hora || r.hora.slice(0, 2) === hora.slice(0, 2)))
          .forEach(r => ocupadas.add(r.mesa));
      } catch (e) {
        console.error(e);
      }
    }

    sel.innerHTML = '<option value="">— Seleccionar mesa —</option>';
    mesas.forEach(m => {
      const libre = !ocupadas.has(m.numero);
      if (libre || String(m.numero) === seleccionActual) {
        sel.innerHTML += `<option value="${m.numero}">Mesa ${m.numero} — ${m.capacidad} pers. (${esc(m.ubicacion)})</option>`;
      }
    });
    if (seleccionActual) sel.value = seleccionActual;
  };

  // ─── Crear / actualizar reserva ───────────────────────────
  window.mcGuardarReserva = async function () {
    if (soloLectura()) { toast('No tienes permisos para realizar esta acción', 'error'); return; }

    const payload = {
      id:              editandoId,
      nombre_cliente:  $('mc-c-nombre').value.trim(),
      telefono:        $('mc-c-telefono').value.trim(),
      email:           $('mc-c-email').value.trim(),
      numero_personas: $('mc-c-personas').value,
      fecha_reserva:   $('mc-c-fecha').value,
      hora_reserva:    $('mc-c-hora').value,
      numero_mesa:     $('mc-c-mesa').value,
      ocasion:         $('mc-c-ocasion').value,
      estado:          $('mc-c-estado').value,
      notas:           $('mc-c-notas').value.trim(),
    };

    // Validación rápida en el navegador; el servidor vuelve a validar todo.
    if (!payload.nombre_cliente || !payload.telefono || !payload.numero_personas ||
        !payload.fecha_reserva || !payload.hora_reserva || !payload.numero_mesa) {
      toast('Completa todos los campos obligatorios (*)', 'error');
      return;
    }

    // Reglas de teléfono, personas y correo.
    const errorValidacion = validarReserva(payload);
    if (errorValidacion) {
      toast(errorValidacion, 'error');
      return;
    }

    const btn = $('mc-btn-guardar');
    const textoOriginal = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = 'Guardando…'; }

    try {
      await apiPost(API.reservaGuardar, payload);
      if (editandoId) toast('La reserva se actualizó correctamente.', 'ok', 'Reserva actualizada');
      else            toast('La reserva se creó correctamente.', 'ok', 'Reserva creada');
      editandoId = null;
      await cargarMesas();
      mcLimpiar();
      mcShow('reservas');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
    }
  };

  window.mcLimpiar = function () {
    editandoId = null;
    ['mc-c-nombre', 'mc-c-telefono', 'mc-c-email', 'mc-c-personas',
     'mc-c-fecha', 'mc-c-hora', 'mc-c-notas'].forEach(id => {
      const el = $(id);
      if (el) el.value = '';
    });
    if ($('mc-c-ocasion')) $('mc-c-ocasion').value = '';
    if ($('mc-c-estado'))  $('mc-c-estado').value  = 'CONFIRMADA';
    if ($('mc-c-mesa'))    $('mc-c-mesa').value    = '';
    if ($('mc-crear-titulo')) $('mc-crear-titulo').textContent = 'Nueva reserva';
    if ($('mc-crear-sub'))    $('mc-crear-sub').textContent    = 'Completa los datos para registrar la reserva';
    if ($('mc-btn-guardar'))  $('mc-btn-guardar').textContent  = 'Guardar reserva';
    fijarFechaMin();
    mcPoblarMesas();
  };

  window.mcEditarReserva = async function (id) {
    if (soloLectura()) { toast('No tienes permisos para realizar esta acción', 'error'); return; }
    const r = reservas.find(x => x.id === id) || reservasDiagrama.find(x => x.id === id);
    if (!r) return;

    editandoId = id;
    mcShow('crear');

    $('mc-c-nombre').value   = r.nombre;
    $('mc-c-telefono').value = r.telefono;
    $('mc-c-email').value    = r.email || '';
    $('mc-c-personas').value = r.personas;
    $('mc-c-fecha').value    = r.fecha;
    $('mc-c-hora').value     = r.hora;
    $('mc-c-ocasion').value  = r.ocasion || '';
    $('mc-c-estado').value   = r.estado;
    $('mc-c-notas').value    = r.notas || '';

    await mcPoblarMesas();
    $('mc-c-mesa').value = r.mesa || '';

    $('mc-crear-titulo').textContent = 'Editar reserva';
    $('mc-crear-sub').textContent    = 'Modificando reserva de ' + r.nombre;
    $('mc-btn-guardar').textContent  = 'Actualizar reserva';
  };

  window.mcPedirEliminarReserva = function (id) {
    if (soloLectura()) { toast('No tienes permisos para realizar esta acción', 'error'); return; }
    const r = reservas.find(x => x.id === id);
    if (!r) return;
    mcConfirm('Eliminar reserva',
      `¿Eliminar la reserva de ${r.nombre} del ${r.fecha}? Esta acción no se puede deshacer.`,
      async () => {
        try {
          await apiPost(API.reservaEliminar, { id });
          await cargarMesas();
          await mcRenderTabla(true);   // se queda en la misma página
          mcRenderDiagrama();
          toast('La reserva se eliminó correctamente.', 'ok', 'Reserva eliminada');
        } catch (e) {
          toast(e.message, 'error');
        }
      });
  };

  // ─── Logo y encabezado de los reportes ────────────────────
  // Igual que en pedidos: se toma static/img/logo.png, se le quita el espacio
  // en blanco sobrante y se reduce a 600 px de ancho. Se calcula una sola vez.
  // Si el logo no carga, el reporte sale igual, solo con texto.
  const LOGO_URL = window.MC_LOGO_URL || '/static/img/logo.png';
  const COLOR_MARCA = [192, 57, 43];   // #C0392B
  let logoPromesa = null;

  function cargarLogo() {
    if (logoPromesa) return logoPromesa;
    logoPromesa = new Promise(resolve => {
      const img = new Image();
      img.onload = () => {
        try {
          const w = img.naturalWidth, h = img.naturalHeight;
          const lienzo = document.createElement('canvas');
          lienzo.width = w; lienzo.height = h;
          const ctx = lienzo.getContext('2d');
          ctx.fillStyle = '#fff';               // lo transparente pasa a blanco
          ctx.fillRect(0, 0, w, h);
          ctx.drawImage(img, 0, 0);
          const px = ctx.getImageData(0, 0, w, h).data;
          // recorte al contenido (todo lo que no sea casi blanco)
          let x0 = w, y0 = h, x1 = -1, y1 = -1;
          for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
              const i = (y * w + x) * 4;
              if (0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2] < 245) {
                if (x < x0) x0 = x;
                if (x > x1) x1 = x;
                if (y < y0) y0 = y;
                if (y > y1) y1 = y;
              }
            }
          }
          if (x1 < 0) { x0 = 0; y0 = 0; x1 = w - 1; y1 = h - 1; }   // imagen vacía: no recortar
          const cw = x1 - x0 + 1, ch = y1 - y0 + 1;
          const ancho = 600, alto = Math.round(ch * ancho / cw);
          const salida = document.createElement('canvas');
          salida.width = ancho; salida.height = alto;
          const sctx = salida.getContext('2d');
          sctx.imageSmoothingQuality = 'high';
          sctx.drawImage(lienzo, x0, y0, cw, ch, 0, 0, ancho, alto);
          resolve({ dataUrl: salida.toDataURL('image/png'), proporcion: ancho / alto });
        } catch (e) {
          resolve(null);
        }
      };
      img.onerror = () => resolve(null);
      img.src = LOGO_URL;
    }).then(logo => {
      if (!logo) logoPromesa = null;   // si falló, se reintenta en el próximo reporte
      return logo;
    });
    return logoPromesa;
  }

  function fechaHoraReporte() {
    const d = new Date(), p = n => String(n).padStart(2, '0');
    return p(d.getDate()) + '/' + p(d.getMonth() + 1) + '/' + d.getFullYear() +
      ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }

  const subtituloReporte = detalle =>
    'Porras Asadero · Generado el ' + fechaHoraReporte() + ' · ' + detalle;

  // PDF: logo a la izquierda, título y fecha a la derecha y una línea roja debajo.
  // Devuelve la posición Y donde debe empezar la tabla.
  function pdfEncabezado(doc, titulo, detalle, logo) {
    const margen = 14, top = 10, altoLogo = 20;
    const anchoPagina = doc.internal.pageSize.getWidth();
    let x = margen;
    if (logo) {
      const anchoLogo = altoLogo * logo.proporcion;
      doc.addImage(logo.dataUrl, 'PNG', margen, top, anchoLogo, altoLogo);
      x = margen + anchoLogo + 6;
    }
    const centro = top + altoLogo / 2;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    doc.setTextColor(...COLOR_MARCA);
    doc.text(titulo, x, centro - 1);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(85);
    doc.text(subtituloReporte(detalle), x, centro + 6);
    doc.setDrawColor(...COLOR_MARCA);
    doc.setLineWidth(0.5);
    doc.line(margen, top + altoLogo + 3, anchoPagina - margen, top + altoLogo + 3);
    doc.setTextColor(0);
    return top + altoLogo + 9;
  }

  // Excel (ExcelJS, porque SheetJS no permite meter imágenes): mismo diseño que
  // los Excel de pedidos: logo arriba a la izquierda, título al lado y la tabla
  // con los colores del PDF. `anchos` va en caracteres de columna.
  async function descargarExcel({ titulo, detalle, hoja, archivo, encabezados, filas, anchos }) {
    const logo = await cargarLogo();
    const libro = new ExcelJS.Workbook();
    const ws = libro.addWorksheet(hoja, {
      pageSetup: { orientation: 'landscape', fitToPage: true, fitToWidth: 1, fitToHeight: 0 },
      views: [{ state: 'frozen', ySplit: 6 }],
    });
    ws.columns = anchos.map(width => ({ width }));

    // Logo (arriba a la izquierda)
    let anchoLogoPx = 0;
    if (logo) {
      const alto = 80;
      anchoLogoPx = Math.round(alto * logo.proporcion);
      const idImagen = libro.addImage({ base64: logo.dataUrl, extension: 'png' });
      ws.addImage(idImagen, { tl: { col: 0, row: 0 }, ext: { width: anchoLogoPx, height: alto } });
    }

    // El título va en la primera columna que quede libre a la derecha del logo
    let acumulado = 0, colTitulo = 1;
    for (let i = 1; i <= anchos.length; i++) {
      acumulado += anchos[i - 1] * 7 + 5;
      colTitulo = i + 1;
      if (acumulado >= anchoLogoPx + 8) break;
    }
    colTitulo = Math.min(colTitulo, Math.max(encabezados.length, 2));

    ws.getRow(2).height = 26;
    ws.getRow(3).height = 16;
    const celdaTitulo = ws.getCell(2, colTitulo);
    celdaTitulo.value = titulo;
    celdaTitulo.font = { name: 'Calibri', size: 16, bold: true, color: { argb: 'FFC0392B' } };
    celdaTitulo.alignment = { vertical: 'middle' };
    const celdaSub = ws.getCell(3, colTitulo);
    celdaSub.value = subtituloReporte(detalle);
    celdaSub.font = { name: 'Calibri', size: 9, color: { argb: 'FF555555' } };

    const lado = { style: 'thin', color: { argb: 'FFD4C4A0' } };
    const borde = { top: lado, left: lado, bottom: lado, right: lado };

    // Encabezados de la tabla (fila 6)
    const filaEnc = 6;
    encabezados.forEach((texto, j) => {
      const c = ws.getCell(filaEnc, j + 1);
      c.value = texto;
      c.font = { name: 'Calibri', size: 10, bold: true, color: { argb: 'FFF5ECD7' } };
      c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFC0392B' } };
      c.alignment = { vertical: 'middle', horizontal: 'left' };
      c.border = borde;
    });
    ws.getRow(filaEnc).height = 20;

    // Filas de datos con fondo alternado
    const claros = ['FFFDF7EC', 'FFEDE3C8'];
    filas.forEach((fila, i) => {
      fila.forEach((valor, j) => {
        const c = ws.getCell(filaEnc + 1 + i, j + 1);
        c.value = valor;
        c.font = { name: 'Calibri', size: 10 };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: claros[i % 2] } };
        c.border = borde;
        c.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true };
      });
    });
    ws.pageSetup.printTitlesRow = filaEnc + ':' + filaEnc;

    const buffer = await libro.xlsx.writeBuffer();
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = archivo;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // Imprimir: mismo encabezado (logo + título + fecha) y debajo la tabla.
  async function imprimirTabla(titulo, detalle, tablaHtml) {
    let area = $('mc-print-area');
    if (!area) {   // por si la plantilla no lo trae
      area = document.createElement('div');
      area.id = 'mc-print-area';
      area.className = 'mc-print-only';
      document.body.appendChild(area);
    }
    const logo = await cargarLogo();
    area.innerHTML = `
      <div class="mc-print-header">
        ${logo ? `<img class="mc-print-logo" src="${logo.dataUrl}" alt="Porras Asadero">` : ''}
        <div class="mc-print-titulo">
          <h1>${esc(titulo)}</h1>
          <p>${esc(subtituloReporte(detalle))}</p>
        </div>
      </div>
      ${tablaHtml}`;
    const imagen = area.querySelector('img');
    if (imagen && imagen.decode) { try { await imagen.decode(); } catch (e) { /* se imprime igual */ } }
    window.print();
  }

  // ─── Reportes de reservas ─────────────────────────────────
  // Los reportes usan TODAS las reservas del filtro, no solo la página visible.
  window.mcExportarPDF = async function () {
    if (!reservas.length) { toast('No hay reservas para exportar', 'error'); return; }
    if (!window.jspdf) { toast('No se pudo cargar la librería de PDF', 'error'); return; }
    const { jsPDF } = window.jspdf;
    const logo = await cargarLogo();
    const doc = new jsPDF();
    const inicioTabla = pdfEncabezado(doc, 'Reporte de Reservas', reservas.length + ' reserva(s)', logo);
    const filas = reservas.map(r => [
      '#' + String(r.id).padStart(2, '0'),
      r.nombre, r.telefono, getMesaLabel(r.mesa),
      r.fecha, r.hora, String(r.personas), ETIQUETA_RESERVA[r.estado] || r.estado,
    ]);
    doc.autoTable({
      head: [['ID', 'Cliente', 'Teléfono', 'Mesa', 'Fecha', 'Hora', 'Personas', 'Estado']],
      body: filas, startY: inicioTabla,
      styles: { font: 'helvetica', fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [192, 57, 43], textColor: 255 },
      alternateRowStyles: { fillColor: [245, 236, 215] },
    });
    doc.save('reservas_' + hoy() + '.pdf');
    toast('Reporte PDF generado');
  };

  window.mcExportarExcel = async function () {
    if (!reservas.length) { toast('No hay reservas para exportar', 'error'); return; }
    if (!window.ExcelJS) { toast('No se pudo cargar la librería de Excel', 'error'); return; }
    try {
      await descargarExcel({
        titulo: 'Reporte de Reservas',
        detalle: reservas.length + ' reserva(s)',
        hoja: 'Reservas',
        archivo: 'reservas_' + hoy() + '.xlsx',
        encabezados: ['ID', 'Cliente', 'Teléfono', 'Correo', 'Mesa', 'Fecha', 'Hora',
                      'Personas', 'Ocasión', 'Estado', 'Notas'],
        filas: reservas.map(r => [
          '#' + String(r.id).padStart(2, '0'),
          r.nombre, r.telefono, r.email || '',
          getMesaLabel(r.mesa), r.fecha, r.hora,
          r.personas, r.ocasion || '',
          ETIQUETA_RESERVA[r.estado] || r.estado, r.notas || '',
        ]),
        anchos: [8, 22, 13, 24, 22, 11, 9, 9, 18, 12, 32],
      });
      toast('Reporte Excel generado');
    } catch (e) {
      toast('No se pudo generar el Excel', 'error');
    }
  };

  window.mcImprimir = async function () {
    if (!reservas.length) { toast('No hay reservas para imprimir', 'error'); return; }
    const filas = reservas.map(r => `<tr>
        <td>#${String(r.id).padStart(2, '0')}</td>
        <td>${esc(r.nombre)}</td><td>${esc(r.telefono)}</td>
        <td>${esc(getMesaLabel(r.mesa))}</td>
        <td>${esc(r.fecha)}</td><td>${esc(r.hora)}</td>
        <td>${esc(r.personas)}</td><td>${ETIQUETA_RESERVA[r.estado] || r.estado}</td>
      </tr>`).join('');
    await imprimirTabla('Reporte de Reservas', reservas.length + ' reserva(s)', `
      <table>
        <thead><tr>
          <th>ID</th><th>Cliente</th><th>Teléfono</th><th>Mesa</th>
          <th>Fecha</th><th>Hora</th><th>Personas</th><th>Estado</th>
        </tr></thead>
        <tbody>${filas}</tbody>
      </table>`);
  };

  // ─── Mesas ────────────────────────────────────────────────
  window.mcCrearMesa = async function () {
    if (soloLectura()) { toast('No tienes permisos para realizar esta acción', 'error'); return; }
    const num = parseInt($('mc-m-numero').value, 10);
    const cap = parseInt($('mc-m-capacidad').value, 10);
    const ubi = $('mc-m-ubicacion').value;
    const est = $('mc-m-estado').value;

    if (!num || !cap) { toast('Ingresa número y capacidad', 'error'); return; }
    if (!editandoMesaNumero && getMesa(num)) {
      toast('Ya existe una mesa con ese número', 'error');
      return;
    }

    try {
      await apiPost(API.mesaGuardar, {
        numero_mesa: num, capacidad: cap, ubicacion: ubi, estado: est,
      });
      toast(editandoMesaNumero ? 'Mesa actualizada' : 'Mesa ' + num + ' agregada');
      editandoMesaNumero = null;
      await cargarMesas();
      mcRenderTablaMesas();
      mcRenderDiagrama();
      mcPoblarMesas();
      mcLimpiarFormMesa();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  function mcLimpiarFormMesa() {
    $('mc-m-numero').value = '';
    $('mc-m-capacidad').value = '';
    $('mc-m-ubicacion').value = 'Salón principal';
    $('mc-m-estado').value = 'LIBRE';
    const titulo = document.querySelector('#mc-crear-mesa .mc-card-title');
    if (titulo) titulo.textContent = 'Agregar mesa';
    const header = document.querySelector('#mc-crear-mesa .mc-sec-header h2');
    if (header) header.textContent = 'Gestión de mesas';
    const boton = document.querySelector('#mc-crear-mesa .mc-btn-primary');
    if (boton) boton.textContent = 'Agregar mesa';
  }

  function mcListaMesasFiltrada() {
    const buscar    = $('mc-buscar-mesa') ? $('mc-buscar-mesa').value.toLowerCase() : '';
    const ubicacion = $('mc-filtro-ubicacion') ? $('mc-filtro-ubicacion').value : '';
    const capacidad = $('mc-filtro-capacidad') ? $('mc-filtro-capacidad').value : '';
    return mesas.filter(m =>
      String(m.numero).includes(buscar) &&
      (!ubicacion || m.ubicacion === ubicacion) &&
      (!capacidad || String(m.capacidad) === String(capacidad))
    );
  }

  window.mcRenderTablaMesas = function () {
    const tb = $('mc-tbody-mesas');
    if (!tb) return;
    const lista = mcListaMesasFiltrada();
    if (!lista.length) {
      tb.innerHTML = '<tr><td colspan="5"><div class="mc-empty"><p>No se encontraron mesas</p></div></td></tr>';
      return;
    }
    // Ver / Editar trabajan con el NÚMERO de mesa (getMesa busca por número).
    tb.innerHTML = lista.map(m => `<tr>
      <td style="font-weight:500">Mesa ${m.numero}</td>
      <td>${m.capacidad} pers.</td>
      <td style="font-size:12px;color:var(--muted)">${esc(m.ubicacion)}</td>
      <td><span class="mc-badge ${badgeClass(m.estado)}">${ETIQUETA_MESA[m.estado] || m.estado}</span></td>
      <td><div class="mc-action-btns">
        <button class="mc-icon-btn" data-tooltip="Ver el detalle de esta mesa" onclick="mcVerMesa(${m.numero})">Ver</button>
        ${!soloLectura() ? `
          <button class="mc-icon-btn edit" data-tooltip="Editar esta mesa" onclick="mcEditarMesa(${m.numero})">Editar</button>
        ` : ''}
      </div></td>
    </tr>`).join('');
  };

  window.mcEditarMesa = function (numero) {
    if (soloLectura()) { toast('No tienes permisos para realizar esta acción', 'error'); return; }
    const m = getMesa(numero);
    if (!m) return;
    editandoMesaNumero = numero;
    mcShow('crear-mesa');
    $('mc-m-numero').value    = m.numero;
    $('mc-m-capacidad').value = m.capacidad;
    $('mc-m-ubicacion').value = m.ubicacion;
    $('mc-m-estado').value    = m.estado;
    const titulo = document.querySelector('#mc-crear-mesa .mc-card-title');
    if (titulo) titulo.textContent = 'Editar mesa';
    const header = document.querySelector('#mc-crear-mesa .mc-sec-header h2');
    if (header) header.textContent = 'Editando mesa ' + m.numero;
    const boton = document.querySelector('#mc-crear-mesa .mc-btn-primary');
    if (boton) boton.textContent = 'Actualizar mesa';
  };

  // ─── Diagrama de mesas ────────────────────────────────────
  window.mcRenderDiagrama = async function () {
    const cont = $('mc-floor-mesas');
    const wrap = $('mc-floor');
    if (!cont || !wrap) return;

    // Reservas sin filtros, para mostrar la próxima reserva en el tooltip.
    await cargarReservasDiagrama();

    const fe = $('mc-filtro-diagrama') ? $('mc-filtro-diagrama').value : '';
    const fu = $('mc-filtro-zona') ? $('mc-filtro-zona').value : '';
    // El filtro y el resumen usan el estado calculado con las reservas de hoy.
    let lista = mesas;
    if (fe) lista = lista.filter(m => estadoEfectivoMesa(m) === fe);
    if (fu) lista = lista.filter(m => m.ubicacion === fu);

    const d = mesas.filter(m => estadoEfectivoMesa(m) === 'LIBRE').length;
    const r = mesas.filter(m => estadoEfectivoMesa(m) === 'RESERVADA').length;
    const o = mesas.filter(m => estadoEfectivoMesa(m) === 'OCUPADA').length;
    if ($('mc-resumen')) $('mc-resumen').textContent = `${d} disponibles · ${r} reservadas · ${o} ocupadas`;
    if ($('mc-floor-count')) $('mc-floor-count').textContent = lista.length + ' mesa' + (lista.length !== 1 ? 's' : '') + ' mostradas';
    if ($('mc-zone-label')) $('mc-zone-label').textContent = fu || 'Todas las zonas';

    if (!lista.length) {
      cont.innerHTML = '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--hint);font-size:14px">Sin mesas para mostrar</div>';
      wrap.style.minHeight = '200px';
      return;
    }

    const cols = 4, size = 92, gap = 18, offX = 28, offY = 46;
    const rows = Math.ceil(lista.length / cols);
    wrap.style.minHeight = (rows * (size + gap) + offY + 36) + 'px';

    cont.innerHTML = lista.map((m, i) => {
      const col = i % cols, row = Math.floor(i / cols);
      const x = offX + col * (size + gap), y = offY + row * (size + gap);

      // Color según el estado calculado (clase + estilo en línea de respaldo).
      const est = estadoEfectivoMesa(m);
      if (!CLASE_MESA[est]) console.warn('Estado de mesa desconocido:', m.numero, m.estado);
      const clase = CLASE_MESA[est] || '';
      const colores = ESTILO_MESA[est] || '';

      // Tooltip: si está reservada, muestra la próxima reserva; si no, capacidad y zona.
      const proxima = reservasVigentesDeMesa(m.numero)[0];
      const tip = (est === 'RESERVADA' && proxima)
        ? `${proxima.nombre} · ${proxima.fecha} ${proxima.hora}`
        : `${m.capacidad} personas · ${m.ubicacion}`;

      return `<div class="mc-mesa ${clase}" data-estado="${est}" style="${colores}left:${x}px;top:${y}px;width:${size}px;height:76px" data-tooltip="${esc(tip)}" onclick="mcVerMesa(${m.numero})">
        <div class="mc-mesa-num">Mesa ${m.numero}</div>
        <div class="mc-mesa-cap">${m.capacidad} pers.</div>
        <div class="mc-mesa-dot"></div>
      </div>`;
    }).join('');
  };

  // Detalle de una mesa (se abre al hacer clic en el diagrama o en "Ver" de la tabla).
  window.mcVerMesa = async function (numero) {
    const m = getMesa(numero);
    if (!m) return;

    // Se piden las reservas al servidor para que el detalle esté siempre al día
    // y no dependa de los filtros de la tabla de reservas.
    await cargarReservasDiagrama();
    const ras = reservasVigentesDeMesa(m.numero);
    const efectivo = estadoEfectivoMesa(m);
    const hoyStr = hoy();

    $('mc-modal-m-title').textContent = 'Mesa ' + m.numero;
    $('mc-modal-m-body').innerHTML = `
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Número</div><div class="mc-detail-val">Mesa ${m.numero}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Capacidad</div><div class="mc-detail-val">${m.capacidad} personas</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Ubicación</div><div class="mc-detail-val">${esc(m.ubicacion)}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Estado</div><div class="mc-detail-val"><span class="mc-badge ${badgeClass(efectivo)}">${ETIQUETA_MESA[efectivo] || efectivo}</span></div></div>
      </div>
      ${ras.length ? `
        <div style="margin:14px 0 10px;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)">Reservas de esta mesa (${ras.length})</div>
        ${ras.map(r => `<div style="padding:10px 12px;margin-bottom:8px;border:1px solid var(--border);border-radius:8px;background:var(--bg2);font-size:13px">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
            <div style="font-weight:600">${esc(r.nombre)}${String(r.fecha).slice(0, 10) === hoyStr ? ' <span class="mc-badge mc-badge-info" style="margin-left:4px">Hoy</span>' : ''}</div>
            <span class="mc-badge ${badgeClass(r.estado)}">${ETIQUETA_RESERVA[r.estado] || r.estado}</span>
          </div>
          <div style="font-size:12px;color:var(--muted);margin-top:4px">${esc(r.fecha)} · ${esc(r.hora)} · ${esc(r.personas)} pers. · Tel. ${esc(r.telefono)}</div>
          ${r.ocasion ? `<div style="font-size:12px;color:var(--muted);margin-top:2px">Ocasión: ${esc(r.ocasion)}</div>` : ''}
          ${r.notas ? `<div style="font-size:12px;color:var(--muted);margin-top:2px">Notas: ${esc(r.notas)}</div>` : ''}
          <div class="mc-action-btns" style="margin-top:8px">
            <button class="mc-icon-btn" onclick="mcCloseModal('mc-modal-mesa');mcVerReserva(${r.id})">Ver reserva</button>
            ${!soloLectura() ? `<button class="mc-icon-btn edit" onclick="mcCloseModal('mc-modal-mesa');mcEditarReserva(${r.id})">Editar</button>` : ''}
          </div>
        </div>`).join('')}`
        : '<p style="font-size:13px;color:var(--muted);margin:12px 0">Esta mesa no tiene reservas vigentes.</p>'}
      ${!soloLectura() ? `
      <div style="margin-top:1.2rem;padding-top:1rem;border-top:1px solid var(--border)">
        <label class="mc-label" style="display:block;margin-bottom:7px">Cambiar estado</label>
        <div style="display:flex;gap:8px;align-items:center">
          <select class="mc-select" id="mc-nuevo-estado" style="flex:1">
            <option value="LIBRE"     ${m.estado === 'LIBRE' ? 'selected' : ''}>Disponible</option>
            <option value="RESERVADA" ${m.estado === 'RESERVADA' ? 'selected' : ''}>Reservada</option>
            <option value="OCUPADA"   ${m.estado === 'OCUPADA' ? 'selected' : ''}>Ocupada</option>
          </select>
          <button class="mc-btn mc-btn-primary" data-tooltip="Guardar el nuevo estado" onclick="mcCambiarEstadoMesa(${m.numero})">Actualizar</button>
        </div>
      </div>` : ''}
      <div class="mc-btn-row">
        <button class="mc-btn mc-btn-secondary" data-tooltip="Cerrar esta ventana" onclick="mcCloseModal('mc-modal-mesa')">Cerrar</button>
      </div>`;
    $('mc-modal-mesa').classList.add('open');
  };

  window.mcCambiarEstadoMesa = async function (numero) {
    if (soloLectura()) { toast('No tienes permisos para realizar esta acción', 'error'); return; }
    const m = getMesa(numero);
    if (!m) return;
    const est = $('mc-nuevo-estado').value;
    try {
      await apiPost(API.mesaGuardar, {
        numero_mesa: numero, capacidad: m.capacidad, ubicacion: m.ubicacion, estado: est,
      });
      await cargarMesas();
      mcCloseModal('mc-modal-mesa');
      mcRenderDiagrama();
      mcRenderTablaMesas();
      toast('Estado actualizado');
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  window.mcExportarMesasPDF = async function () {
    const lista = mcListaMesasFiltrada();
    if (!lista.length) { toast('No hay mesas para exportar', 'error'); return; }
    if (!window.jspdf) { toast('No se pudo cargar la librería de PDF', 'error'); return; }
    const { jsPDF } = window.jspdf;
    const logo = await cargarLogo();
    const doc = new jsPDF();
    const inicioTabla = pdfEncabezado(doc, 'Reporte de Mesas', lista.length + ' mesa(s)', logo);
    const filas = lista.map(m => ['Mesa ' + m.numero, m.capacidad + ' pers.', m.ubicacion, ETIQUETA_MESA[m.estado] || m.estado]);
    doc.autoTable({
      head: [['Mesa', 'Capacidad', 'Ubicación', 'Estado']], body: filas, startY: inicioTabla,
      styles: { font: 'helvetica', fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [192, 57, 43], textColor: 255 },
      alternateRowStyles: { fillColor: [245, 236, 215] },
    });
    doc.save('mesas_' + hoy() + '.pdf');
    toast('Reporte PDF generado');
  };

  window.mcExportarMesasExcel = async function () {
    const lista = mcListaMesasFiltrada();
    if (!lista.length) { toast('No hay mesas para exportar', 'error'); return; }
    if (!window.ExcelJS) { toast('No se pudo cargar la librería de Excel', 'error'); return; }
    try {
      await descargarExcel({
        titulo: 'Reporte de Mesas',
        detalle: lista.length + ' mesa(s)',
        hoja: 'Mesas',
        archivo: 'mesas_' + hoy() + '.xlsx',
        encabezados: ['Mesa', 'Capacidad', 'Ubicación', 'Estado'],
        filas: lista.map(m => ['Mesa ' + m.numero, m.capacidad, m.ubicacion, ETIQUETA_MESA[m.estado] || m.estado]),
        anchos: [12, 12, 22, 14],
      });
      toast('Reporte Excel generado');
    } catch (e) {
      toast('No se pudo generar el Excel', 'error');
    }
  };

  window.mcImprimirMesas = async function () {
    const lista = mcListaMesasFiltrada();
    if (!lista.length) { toast('No hay mesas para imprimir', 'error'); return; }
    const filas = lista.map(m => `<tr>
        <td>Mesa ${m.numero}</td><td>${m.capacidad} pers.</td>
        <td>${esc(m.ubicacion)}</td><td>${ETIQUETA_MESA[m.estado] || m.estado}</td>
      </tr>`).join('');
    await imprimirTabla('Reporte de Mesas', lista.length + ' mesa(s)', `
      <table>
        <thead><tr><th>Mesa</th><th>Capacidad</th><th>Ubicación</th><th>Estado</th></tr></thead>
        <tbody>${filas}</tbody>
      </table>`);
  };

  // ─── Validaciones del formulario de reserva ───────────────
  const MAX_PERSONAS = 10;
  const RE_TEL_CO = /^3\d{9}$/;   // celular colombiano: 10 dígitos, empieza por 3
  // Nombre de usuario con al menos una letra, sin puntos/guiones al inicio, al final ni repetidos;
  // dominio con etiquetas válidas y extensión de solo letras.
  const RE_EMAIL  = /^(?=.*[A-Za-z])[A-Za-z0-9]+([._-][A-Za-z0-9]+)*@([A-Za-z0-9]+(-[A-Za-z0-9]+)*\.)+[A-Za-z]{2,}$/;
  const PROVEEDORES_COMUNES = ['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com', 'icloud.com'];

  // Correo con formato válido y dominio colombiano (.co / .com.co) o proveedor común.
  function correoValido(v) {
    if (!RE_EMAIL.test(v)) return false;
    const dominio = v.split('@')[1].toLowerCase();
    return dominio.endsWith('.co') || PROVEEDORES_COMUNES.includes(dominio);
  }

  // Devuelve un mensaje de error, o '' si todo está bien.
  function validarReserva(p) {
    if (!RE_TEL_CO.test(p.telefono))
      return 'El teléfono debe tener 10 dígitos y empezar por 3 (ej: 3001234567).';
    const n = parseInt(p.numero_personas, 10);
    if (!Number.isInteger(n) || n < 1 || n > MAX_PERSONAS)
      return 'El número de personas debe estar entre 1 y ' + MAX_PERSONAS + '.';
    if (p.email && !correoValido(p.email))
      return 'Ingresa un correo válido (ej: nombre@gmail.com o nombre@empresa.com.co).';
    return '';
  }

  // Ajusta los campos mientras el usuario escribe.
  function configurarValidaciones() {
    const tel = $('mc-c-telefono'), per = $('mc-c-personas');
    if (tel) {
      tel.setAttribute('inputmode', 'numeric');
      tel.setAttribute('maxlength', '10');
      tel.addEventListener('input', () => {
        tel.value = tel.value.replace(/\D/g, '').slice(0, 10);
      });
    }
    if (per) {
      per.min = 1; per.max = MAX_PERSONAS; per.step = 1;
      per.addEventListener('input', () => {
        const n = parseInt(per.value, 10);
        if (n > MAX_PERSONAS) per.value = MAX_PERSONAS;
        if (n < 1) per.value = 1;
      });
    }
  }

  // ─── Arranque ─────────────────────────────────────────────
  function fijarFechaMin() {
    const input = $('mc-c-fecha');
    if (input) input.min = hoy();
  }

  async function iniciar() {
    configurarValidaciones();
    fijarFechaMin();
    try {
      await cargarMesas();
      await mcRenderTabla();
      mcRenderDiagrama();
      mcRenderTablaMesas();
      mcPoblarMesas();
    } catch (e) {
      console.error(e);
    } finally {
      // ?tab=crear / mesas / crear-mesa desde los enlaces del menú lateral.
      // Va en finally para que un error al pintar no impida abrir la sección.
      const tabInicial = new URLSearchParams(window.location.search).get('tab');
      if (tabInicial && $('mc-' + tabInicial)) mcShow(tabInicial);

      // Mensajes que llegan desde las vistas de Django (crear/editar por formulario HTML).
      const msj = (window.MC_MENSAJES || [])[0];
      if (msj) {
        const error = /error/.test(msj.tipo);
        let titulo = 'Atención';
        if (!error) {
          if (/creada/.test(msj.texto)) titulo = 'Reserva creada';
          else if (/actualizada/.test(msj.texto)) titulo = 'Reserva actualizada';
          else if (/eliminada/.test(msj.texto)) titulo = 'Reserva eliminada';
          else titulo = '¡Listo!';
        }
        toast(msj.texto, error ? 'error' : 'ok', titulo);
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();

/**
 * Tooltips flotantes delegados para botones dentro de modales
 * (.mc-modal, .mc-confirm-box) y para las mesas del diagrama
 * (.mc-floor-container). Estos contenedores recortarían un
 * tooltip CSS normal, así que el tooltip se crea con JS y se
 * pega al <body>. Usa delegación de eventos en document para
 * funcionar también con elementos que se agregan después vía
 * innerHTML (como "Actualizar" y "Cerrar" dentro de mcVerMesa).
 */
(function () {
    let bubble = null;
    let elActual = null;

    function showTooltip(el) {
        const text = el.getAttribute('data-tooltip');
        if (!text) return;

        bubble = document.createElement('div');
        bubble.className = 'js-tooltip-bubble';
        bubble.textContent = text;
        document.body.appendChild(bubble);

        const rect = el.getBoundingClientRect();
        const bubbleRect = bubble.getBoundingClientRect();

        let left = rect.left + rect.width / 2 - bubbleRect.width / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - bubbleRect.width - 8));

        const espacioArriba = rect.top - bubbleRect.height - 10;
        let top;
        let abajo = false;
        if (espacioArriba < 8) {
            top = rect.bottom + 10;
            abajo = true;
        } else {
            top = espacioArriba;
        }

        bubble.classList.toggle('abajo', abajo);
        bubble.style.left = left + 'px';
        bubble.style.top = top + 'px';

        requestAnimationFrame(() => bubble.classList.add('show'));
    }

    function hideTooltip() {
        if (bubble) {
            bubble.remove();
            bubble = null;
        }
        elActual = null;
    }

    document.addEventListener('mouseover', function (e) {
        const el = e.target.closest('.mc-modal [data-tooltip], .mc-confirm-box [data-tooltip], .mc-floor-container [data-tooltip]');
        if (el && el !== elActual) {
            hideTooltip();
            elActual = el;
            showTooltip(el);
        }
    });

    document.addEventListener('mouseout', function (e) {
        const el = e.target.closest('.mc-modal [data-tooltip], .mc-confirm-box [data-tooltip], .mc-floor-container [data-tooltip]');
        if (el && (!e.relatedTarget || !el.contains(e.relatedTarget))) {
            hideTooltip();
        }
    });

    document.addEventListener('focusin', function (e) {
        const el = e.target.closest('.mc-modal [data-tooltip], .mc-confirm-box [data-tooltip], .mc-floor-container [data-tooltip]');
        if (el && el !== elActual) {
            hideTooltip();
            elActual = el;
            showTooltip(el);
        }
    });
    document.addEventListener('focusout', function (e) {
        const el = e.target.closest('.mc-modal [data-tooltip], .mc-confirm-box [data-tooltip], .mc-floor-container [data-tooltip]');
        if (el) hideTooltip();
    });

    // Oculta el tooltip al hacer clic en cualquier lado (por ejemplo,
    // al presionar "Cerrar", "Actualizar" o cualquier botón que
    // cierre el modal o dispare una acción).
    document.addEventListener('scroll', hideTooltip, true);
    document.addEventListener('click', hideTooltip, true);
    document.addEventListener('mousedown', hideTooltip, true);
})();