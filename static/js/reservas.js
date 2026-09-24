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
  let reservas = [];
  let mesas = [];
  let editandoId = null;          // id de reserva en edición
  let editandoMesaNumero = null;  // número de mesa en edición

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
  const CLASE_MESA       = { LIBRE: 'disponible', RESERVADA: 'reservada', OCUPADA: 'ocupada' };

  function badgeClass(estado) {
    if (estado === 'CONFIRMADA' || estado === 'LIBRE') return 'mc-badge-ok';
    if (estado === 'PENDIENTE' || estado === 'RESERVADA') return 'mc-badge-warn';
    return 'mc-badge-danger';
  }

  function getMesa(numero)      { return mesas.find(m => m.numero === numero); }
  function getMesaLabel(numero) { const m = getMesa(numero); return m ? 'Mesa ' + m.numero : '—'; }

  // ─── Modales / avisos ─────────────────────────────────────
  function toast(msg, tipo) {
    const titulo = $('mc-msg-title'), texto = $('mc-msg-text'), overlay = $('mc-msg-overlay');
    if (!overlay) { console.log(msg); return; }
    titulo.textContent = tipo === 'error' ? 'Atención' : '¡Listo!';
    texto.textContent = msg;
    overlay.classList.add('open');
  }

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
    if (id === 'mesas')      mcRenderDiagrama();
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

    if (buscar && buscar.value.trim()) filtros.q = buscar.value.trim();
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
      reservas = data.reservas;
      return true;
    } catch (e) {
      console.error(e);
      toast('No se pudieron cargar las reservas: ' + e.message, 'error');
      return false;
    }
  }

  async function cargarMesas() {
    try {
      const data = await apiGet(API.mesas);
      mesas = data.mesas;
      return true;
    } catch (e) {
      console.error(e);
      toast('No se pudieron cargar las mesas: ' + e.message, 'error');
      return false;
    }
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
    ['mc-buscar', 'mc-filtro-fecha',
     'mc-filtro-fecha-dia', 'mc-filtro-fecha-mes',
     'mc-filtro-desde', 'mc-filtro-hasta'].forEach(id => {
      const el = $(id);
      if (el) el.value = '';
    });
    mcToggleFiltroFecha();
  };

  // ─── Tabla de reservas ────────────────────────────────────
  window.mcRenderTabla = async function () {
    const tb = $('mc-tbody-reservas');
    if (!tb) return;

    tb.innerHTML = '<tr><td colspan="8"><div class="mc-empty"><p>Cargando…</p></div></td></tr>';
    await cargarReservas();

    const contador = $('mc-contador-reservas');
    if (contador) {
      contador.textContent = reservas.length + ' reserva' + (reservas.length !== 1 ? 's' : '');
    }

    if (!reservas.length) {
      tb.innerHTML = `<tr><td colspan="8"><div class="mc-empty">
        <div class="mc-empty-icon">&#128467;</div>
        <p>No se encontraron reservas con los filtros actuales</p>
      </div></td></tr>`;
      return;
    }

    tb.innerHTML = reservas.map(r => `<tr>
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
  };

  window.mcVerReserva = function (id) {
    const r = reservas.find(x => x.id === id);
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

    const btn = $('mc-btn-guardar');
    const textoOriginal = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = 'Guardando…'; }

    try {
      await apiPost(API.reservaGuardar, payload);
      toast(editandoId ? 'Reserva actualizada' : 'Reserva creada exitosamente');
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
    const r = reservas.find(x => x.id === id);
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
          await mcRenderTabla();
          mcRenderDiagrama();
          toast('Reserva eliminada');
        } catch (e) {
          toast(e.message, 'error');
        }
      });
  };

  // ─── Reportes de reservas ─────────────────────────────────
  window.mcExportarPDF = function () {
    if (!reservas.length) { toast('No hay reservas para exportar', 'error'); return; }
    if (!window.jspdf) { toast('No se pudo cargar la librería de PDF', 'error'); return; }
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text('Asadero Porras — Reporte de Reservas', 14, 16);
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text('Generado el ' + new Date().toLocaleString('es-CO') + '  •  ' + reservas.length + ' reserva(s)', 14, 22);
    const filas = reservas.map(r => [
      '#' + String(r.id).padStart(2, '0'),
      r.nombre, r.telefono, getMesaLabel(r.mesa),
      r.fecha, r.hora, String(r.personas), ETIQUETA_RESERVA[r.estado] || r.estado,
    ]);
    doc.autoTable({
      head: [['ID', 'Cliente', 'Teléfono', 'Mesa', 'Fecha', 'Hora', 'Personas', 'Estado']],
      body: filas, startY: 28,
      styles: { font: 'helvetica', fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [192, 57, 43], textColor: 255 },
      alternateRowStyles: { fillColor: [245, 236, 215] },
    });
    doc.save('reservas_' + hoy() + '.pdf');
    toast('Reporte PDF generado');
  };

  window.mcExportarExcel = function () {
    if (!reservas.length) { toast('No hay reservas para exportar', 'error'); return; }
    if (!window.XLSX) { toast('No se pudo cargar la librería de Excel', 'error'); return; }
    const datos = reservas.map(r => ({
      'ID': '#' + String(r.id).padStart(2, '0'),
      'Cliente': r.nombre, 'Teléfono': r.telefono, 'Correo': r.email || '',
      'Mesa': getMesaLabel(r.mesa), 'Fecha': r.fecha, 'Hora': r.hora,
      'Personas': r.personas, 'Ocasión': r.ocasion || '',
      'Estado': ETIQUETA_RESERVA[r.estado] || r.estado, 'Notas': r.notas || '',
    }));
    const hoja = XLSX.utils.json_to_sheet(datos);
    hoja['!cols'] = [
      { wch: 8 }, { wch: 22 }, { wch: 13 }, { wch: 24 }, { wch: 22 },
      { wch: 11 }, { wch: 9 }, { wch: 9 }, { wch: 18 }, { wch: 12 }, { wch: 32 },
    ];
    const libro = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(libro, hoja, 'Reservas');
    XLSX.writeFile(libro, 'reservas_' + hoy() + '.xlsx');
    toast('Reporte Excel generado');
  };

  window.mcImprimir = function () {
    if (!reservas.length) { toast('No hay reservas para imprimir', 'error'); return; }
    const filas = reservas.map(r => `<tr>
        <td>#${String(r.id).padStart(2, '0')}</td>
        <td>${esc(r.nombre)}</td><td>${esc(r.telefono)}</td>
        <td>${esc(getMesaLabel(r.mesa))}</td>
        <td>${esc(r.fecha)}</td><td>${esc(r.hora)}</td>
        <td>${esc(r.personas)}</td><td>${ETIQUETA_RESERVA[r.estado] || r.estado}</td>
      </tr>`).join('');
    $('mc-print-area').innerHTML = `
      <h2>Asadero Porras — Reporte de Reservas</h2>
      <p>Generado el ${new Date().toLocaleString('es-CO')} — ${reservas.length} reserva(s)</p>
      <table>
        <thead><tr>
          <th>ID</th><th>Cliente</th><th>Teléfono</th><th>Mesa</th>
          <th>Fecha</th><th>Hora</th><th>Personas</th><th>Estado</th>
        </tr></thead>
        <tbody>${filas}</tbody>
      </table>`;
    window.print();
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
    tb.innerHTML = lista.map(m => `<tr>
      <td style="font-weight:500">Mesa ${m.numero}</td>
      <td>${m.capacidad} pers.</td>
      <td style="font-size:12px;color:var(--muted)">${esc(m.ubicacion)}</td>
      <td><span class="mc-badge ${badgeClass(m.estado)}">${ETIQUETA_MESA[m.estado] || m.estado}</span></td>
      <td><div class="mc-action-btns">
        <button class="mc-icon-btn" data-tooltip="Ver el detalle de esta mesa" onclick="mcVerMesa(${m.id})">Ver</button>
        ${!esCajero() ? `
          <button class="mc-icon-btn edit" data-tooltip="Editar esta mesa" onclick="mcEditarMesa(${m.id})">Editar</button>
          <button class="mc-icon-btn del" data-tooltip="Borrar esta mesa" onclick="mcPedirEliminarMesa(${m.id})">Borrar</button>
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

  window.mcRenderDiagrama = function () {
    const cont = $('mc-floor-mesas');
    const wrap = $('mc-floor');
    if (!cont || !wrap) return;

    const fe = $('mc-filtro-diagrama') ? $('mc-filtro-diagrama').value : '';
    const fu = $('mc-filtro-zona') ? $('mc-filtro-zona').value : '';
    let lista = mesas;
    if (fe) lista = lista.filter(m => m.estado === fe);
    if (fu) lista = lista.filter(m => m.ubicacion === fu);

    const d = mesas.filter(m => m.estado === 'LIBRE').length;
    const r = mesas.filter(m => m.estado === 'RESERVADA').length;
    const o = mesas.filter(m => m.estado === 'OCUPADA').length;
    if ($('mc-resumen')) $('mc-resumen').textContent = `${d} disponibles · ${r} reservadas · ${o} ocupadas`;
    if ($('mc-floor-count')) $('mc-floor-count').textContent = lista.length + ' mesa' + (lista.length !== 1 ? 's' : '') + ' mostradas';
    if ($('mc-zone-label')) $('mc-zone-label').textContent = fu || 'Todas las zonas';

    if (!lista.length) {
      cont.innerHTML = '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--hint);font-size:14px">Sin mesas para mostrar</div>';
      wrap.style.minHeight = '200px';
      return;
    }
    const cols=4,size=92,gap=18,offX=28,offY=46;
    const rows=Math.ceil(lista.length/cols);
    wrap.style.minHeight=(rows*(size+gap)+offY+36)+'px';
    cont.innerHTML=lista.map((m,i)=>{
      const col=i%cols,row=Math.floor(i/cols);
      const x=offX+col*(size+gap), y=offY+row*(size+gap);
      const ra=reservas.find(r=>r.mesaId===m.id&&r.estado==='confirmada');
      const tip=(m.estado==='reservada'&&ra?`${ra.nombre} · ${ra.fecha} ${ra.hora}`:`${m.capacidad} personas · ${m.ubicacion}`).replace(/"/g,'&quot;');
      return `<div class="mc-mesa ${m.estado}" style="left:${x}px;top:${y}px;width:${size}px;height:76px" data-tooltip="${tip}" onclick="mcVerMesa(${m.id})">
        <div class="mc-mesa-num">Mesa ${m.numero}</div>
        <div class="mc-mesa-cap">${m.capacidad} pers.</div>
        <div class="mc-mesa-dot"></div>
      </div>`;
    }).join('');
  };

  window.mcVerMesa = function (numero) {
    const m = getMesa(numero);
    if (!m) return;
    const ras = reservas.filter(r => r.mesa === numero && r.estado !== 'CANCELADA');
    $('mc-modal-m-title').textContent = 'Mesa ' + m.numero;
    $('mc-modal-m-body').innerHTML = `
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Número</div><div class="mc-detail-val">Mesa ${m.numero}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Capacidad</div><div class="mc-detail-val">${m.capacidad} personas</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Ubicación</div><div class="mc-detail-val">${esc(m.ubicacion)}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Estado</div><div class="mc-detail-val"><span class="mc-badge ${badgeClass(m.estado)}">${ETIQUETA_MESA[m.estado] || m.estado}</span></div></div>
      </div>
      ${ras.length ? `
        <div style="margin:14px 0 10px;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)">Reservas activas (${ras.length})</div>
        ${ras.map(r => `<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--border);font-size:13px">
          <div><div style="font-weight:500">${esc(r.nombre)}</div><div style="font-size:12px;color:var(--muted)">${r.personas} pers. · ${r.fecha} ${r.hora}</div></div>
          <span class="mc-badge ${badgeClass(r.estado)}">${ETIQUETA_RESERVA[r.estado] || r.estado}</span>
        </div>`).join('')}`
        : '<p style="font-size:13px;color:var(--muted);margin:12px 0">Sin reservas activas en esta mesa (según los filtros actuales).</p>'}
      ${!soloLectura() ? `
      <div style="margin-top:1.2rem;padding-top:1rem;border-top:1px solid var(--border)">
        <label class="mc-label" style="display:block;margin-bottom:7px">Cambiar estado</label>
        <div style="display:flex;gap:8px;align-items:center">
          <select class="mc-select" id="mc-nuevo-estado" style="flex:1">
            <option value="LIBRE"     ${m.estado === 'LIBRE' ? 'selected' : ''}>Disponible</option>
            <option value="RESERVADA" ${m.estado === 'RESERVADA' ? 'selected' : ''}>Reservada</option>
            <option value="OCUPADA"   ${m.estado === 'OCUPADA' ? 'selected' : ''}>Ocupada</option>
          </select>
          <button class="mc-btn mc-btn-primary" data-tooltip="Guardar el nuevo estado" onclick="mcCambiarEstadoMesa(${m.id},${m.numero})">Actualizar</button>
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

  window.mcPedirEliminarMesa = function (numero) {
    if (soloLectura()) { toast('No tienes permisos para realizar esta acción', 'error'); return; }
    const m = getMesa(numero);
    if (!m) return;
    mcConfirm('Eliminar mesa',
      `¿Eliminar la Mesa ${m.numero}? También se eliminarán sus reservas asociadas.`,
      async () => {
        try {
          await apiPost(API.mesaEliminar, { numero_mesa: numero });
          await cargarMesas();
          mcRenderTablaMesas();
          await mcRenderTabla();
          mcRenderDiagrama();
          mcPoblarMesas();
          toast('Mesa eliminada');
        } catch (e) {
          toast(e.message, 'error');
        }
      });
  };

  window.mcExportarMesasPDF = function () {
    const lista = mcListaMesasFiltrada();
    if (!lista.length) { toast('No hay mesas para exportar', 'error'); return; }
    if (!window.jspdf) { toast('No se pudo cargar la librería de PDF', 'error'); return; }
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text('Asadero Porras — Reporte de Mesas', 14, 16);
    doc.setFontSize(10); doc.setTextColor(100);
    doc.text('Generado el ' + new Date().toLocaleString('es-CO') + '  •  ' + lista.length + ' mesa(s)', 14, 22);
    const filas = lista.map(m => ['Mesa ' + m.numero, m.capacidad + ' pers.', m.ubicacion, ETIQUETA_MESA[m.estado] || m.estado]);
    doc.autoTable({
      head: [['Mesa', 'Capacidad', 'Ubicación', 'Estado']], body: filas, startY: 28,
      styles: { font: 'helvetica', fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [192, 57, 43], textColor: 255 },
      alternateRowStyles: { fillColor: [245, 236, 215] },
    });
    doc.save('mesas_' + hoy() + '.pdf');
    toast('Reporte PDF generado');
  };

  window.mcExportarMesasExcel = function () {
    const lista = mcListaMesasFiltrada();
    if (!lista.length) { toast('No hay mesas para exportar', 'error'); return; }
    if (!window.XLSX) { toast('No se pudo cargar la librería de Excel', 'error'); return; }
    const datos = lista.map(m => ({
      'Mesa': 'Mesa ' + m.numero, 'Capacidad': m.capacidad,
      'Ubicación': m.ubicacion, 'Estado': ETIQUETA_MESA[m.estado] || m.estado,
    }));
    const hoja = XLSX.utils.json_to_sheet(datos);
    hoja['!cols'] = [{ wch: 12 }, { wch: 12 }, { wch: 22 }, { wch: 14 }];
    const libro = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(libro, hoja, 'Mesas');
    XLSX.writeFile(libro, 'mesas_' + hoy() + '.xlsx');
    toast('Reporte Excel generado');
  };

  window.mcImprimirMesas = function () {
    const lista = mcListaMesasFiltrada();
    if (!lista.length) { toast('No hay mesas para imprimir', 'error'); return; }
    const filas = lista.map(m => `<tr>
        <td>Mesa ${m.numero}</td><td>${m.capacidad} pers.</td>
        <td>${esc(m.ubicacion)}</td><td>${ETIQUETA_MESA[m.estado] || m.estado}</td>
      </tr>`).join('');
    $('mc-print-area').innerHTML = `
      <h2>Asadero Porras — Reporte de Mesas</h2>
      <p>Generado el ${new Date().toLocaleString('es-CO')} — ${lista.length} mesa(s)</p>
      <table>
        <thead><tr><th>Mesa</th><th>Capacidad</th><th>Ubicación</th><th>Estado</th></tr></thead>
        <tbody>${filas}</tbody>
      </table>`;
    window.print();
  };

  // ─── Arranque ─────────────────────────────────────────────
  function fijarFechaMin() {
    const input = $('mc-c-fecha');
    if (input) input.min = hoy();
  }

  async function iniciar() {
    fijarFechaMin();
    await cargarMesas();
    await mcRenderTabla();
    mcRenderDiagrama();
    mcRenderTablaMesas();
    mcPoblarMesas();

    // ?tab=crear / mesas / crear-mesa desde los enlaces del menú lateral.
    const tabInicial = new URLSearchParams(window.location.search).get('tab');
    if (tabInicial && $('mc-' + tabInicial)) mcShow(tabInicial);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();

/**
 * Tooltips flotantes delegados para botones dentro de modales
 * (.mc-modal, .mc-confirm-box). Estos contenedores tienen
 * overflow-y:auto y recortarían un tooltip CSS normal, así que
 * el tooltip se crea con JS y se pega al <body>. Usa delegación
 * de eventos en document para funcionar también con botones
 * que se agregan después vía innerHTML (como "Actualizar" y
 * "Cerrar" dentro de mcVerMesa).
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