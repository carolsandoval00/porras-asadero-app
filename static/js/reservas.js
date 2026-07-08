(function(){
  let reservas       = JSON.parse(localStorage.getItem('mc_reservas') || '[]');
  let mesas          = JSON.parse(localStorage.getItem('mc_mesas')    || '[]');
  let contadorM      = parseInt(localStorage.getItem('mc_contador_m') || '0');
  let editandoId     = null;
  let editandoMesaId = null;

  // Helper de permisos — lee el div que Django pone solo si el usuario es cajero
  const esCajero = () => !!document.getElementById('mc-es-cajero');

  localStorage.removeItem('mc_contador_r');
  function nextIdR(){ return reservas.length ? Math.max(...reservas.map(r=>r.id||0)) + 1 : 1; }
  function nextIdM(){ contadorM++; localStorage.setItem('mc_contador_m', contadorM); return contadorM; }

  function save(){
    localStorage.setItem('mc_reservas',   JSON.stringify(reservas));
    localStorage.setItem('mc_mesas',      JSON.stringify(mesas));
    localStorage.setItem('mc_contador_m', contadorM);
  }

  function getCookie(name) {
    let value = null;
    if (document.cookie) {
      document.cookie.split(';').forEach(c => {
        const cv = c.trim();
        if (cv.startsWith(name + '='))
          value = decodeURIComponent(cv.substring(name.length + 1));
      });
    }
    return value;
  }

  function djangoPost(url, data) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(data),
    });
  }

  window.mcShow = function(id){
    // Bloquear secciones de edición para cajero
    if(esCajero() && (id==='crear' || id==='crear-mesa')){
      toast('No tienes permisos para realizar esta acción', 'error');
      return;
    }
    document.querySelectorAll('.mc-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.mc-nav-btn').forEach(b => b.classList.remove('active'));
    const sec = document.getElementById('mc-' + id);
    if(sec) sec.classList.add('active');
    document.querySelectorAll('.mc-nav-btn').forEach(b => {
      if(b.getAttribute('onclick') && b.getAttribute('onclick').includes("'"+id+"'"))
        b.classList.add('active');
    });
    if(id==='reservas')   mcRenderTabla();
    if(id==='mesas')      mcRenderDiagrama();
    if(id==='crear-mesa') mcRenderTablaMesas();
    if(id==='crear' && !editandoId){ mcLimpiar(); mcPoblarMesas(); }
  };

  function toast(msg, tipo){
    document.getElementById('mc-msg-title').textContent = tipo === 'error' ? 'Atención' : '¡Listo!';
    document.getElementById('mc-msg-text').textContent  = msg;
    document.getElementById('mc-msg-overlay').classList.add('open');
  }

  window.mcCloseConfirm = function(){ document.getElementById('mc-confirm-overlay').classList.remove('open'); };
  function mcConfirm(titulo, msg, cb){
    document.getElementById('mc-confirm-title').textContent = titulo;
    document.getElementById('mc-confirm-msg').textContent   = msg;
    document.getElementById('mc-confirm-ok').onclick = ()=>{ mcCloseConfirm(); cb(); };
    document.getElementById('mc-confirm-overlay').classList.add('open');
  }

  window.mcCloseModal = function(id){ document.getElementById(id).classList.remove('open'); };

  function getMesa(id)      { return mesas.find(m => m.id === id); }
  function getMesaLabel(id) { const m = getMesa(id); return m ? 'Mesa '+m.numero : '—'; }
  function hoy()            { return new Date().toISOString().slice(0,10); }
  function badgeClass(estado){
    return estado==='confirmada'?'mc-badge-ok':estado==='pendiente'?'mc-badge-warn':'mc-badge-danger';
  }

  function mcPoblarMesas(){
    const sel = document.getElementById('mc-c-mesa');
    if(!sel) return;
    const fecha = document.getElementById('mc-c-fecha').value;
    const hora  = document.getElementById('mc-c-hora').value;
    const r     = editandoId ? reservas.find(x => x.id === editandoId) : null;
    const mesasOcupadas = new Set(
      reservas
        .filter(x => x.fecha===fecha && x.hora===hora && x.estado!=='cancelada' && x.id!==editandoId)
        .map(x => x.mesaId)
    );
    sel.innerHTML = '<option value="">— Seleccionar mesa —</option>';
    mesas.forEach(m => {
      const ocupada    = mesasOcupadas.has(m.id);
      const esLaActual = r && r.mesaId === m.id;
      if (!ocupada || esLaActual)
        sel.innerHTML += `<option value="${m.id}">Mesa ${m.numero} — ${m.capacidad} pers. (${m.ubicacion})</option>`;
    });
  }

  window.mcGuardarReserva = function(){
    if(esCajero()){ toast('No tienes permisos para realizar esta acción','error'); return; }
    const nom = document.getElementById('mc-c-nombre').value.trim();
    const tel = document.getElementById('mc-c-telefono').value.trim();
    const per = document.getElementById('mc-c-personas').value;
    const fec = document.getElementById('mc-c-fecha').value;
    const hor = document.getElementById('mc-c-hora').value;
    const mes = document.getElementById('mc-c-mesa').value;

    if(!nom||!tel||!per||!fec||!hor||!mes){ toast('Completa todos los campos obligatorios (*)','error'); return; }
    if(tel.length !== 10){ toast('El teléfono debe tener exactamente 10 dígitos','error'); return; }
    if(fec < hoy()){ toast('No se pueden crear reservas en fechas pasadas','error'); return; }
    const emailVal = document.getElementById('mc-c-email').value.trim();
    if(emailVal && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)){ toast('El correo electrónico no es válido','error'); return; }
    const conflicto = reservas.find(x =>
      x.fecha===fec && x.hora===hor && x.mesaId===parseInt(mes) && x.estado!=='cancelada' && x.id!==editandoId
    );
    if(conflicto){ toast('Esa mesa ya está reservada para ese día y hora','error'); return; }

    const obj = {
      id:       editandoId || nextIdR(),
      nombre:   nom, telefono: tel,
      email:    document.getElementById('mc-c-email').value.trim(),
      personas: parseInt(per), fecha:fec, hora:hor, mesaId:parseInt(mes),
      ocasion:  document.getElementById('mc-c-ocasion').value,
      estado:   document.getElementById('mc-c-estado').value,
      notas:    document.getElementById('mc-c-notas').value.trim(),
      creada:   editandoId
                ? (reservas.find(r=>r.id===editandoId)||{}).creada||new Date().toISOString()
                : new Date().toISOString()
    };

    if(editandoId){ reservas = reservas.map(r=>r.id===editandoId?obj:r); toast('Reserva actualizada'); }
    else          { reservas.push(obj); toast('Reserva creada exitosamente'); }
    save(); mcLimpiar(); mcShow('reservas');
  };

  window.mcLimpiar = function(){
    editandoId = null;
    ['mc-c-nombre','mc-c-telefono','mc-c-email','mc-c-personas','mc-c-fecha','mc-c-hora','mc-c-notas']
      .forEach(id=>{ const el=document.getElementById(id); if(el) el.value=''; });
    document.getElementById('mc-c-ocasion').value = '';
    document.getElementById('mc-c-estado').value  = 'confirmada';
    document.getElementById('mc-c-mesa').value    = '';
    document.getElementById('mc-crear-titulo').textContent = 'Nueva reserva';
    document.getElementById('mc-crear-sub').textContent   = 'Completa los datos para registrar la reserva';
    document.getElementById('mc-btn-guardar').textContent  = 'Guardar reserva';
    mcPoblarMesas(); fijarFechaMin();
  };

  function mcListaFiltrada(){
    const buscar = document.getElementById('mc-buscar').value.toLowerCase();
    const estado = document.getElementById('mc-filtro-estado').value;
    const fecha  = document.getElementById('mc-filtro-fecha').value;
    const h = hoy();
    return reservas.filter(r=>{
      const mb = r.nombre.toLowerCase().includes(buscar)||r.telefono.includes(buscar);
      const me = !estado||r.estado===estado;
      let mf=true;
      if(fecha==='hoy')     mf=r.fecha===h;
      if(fecha==='futuras') mf=r.fecha>=h;
      if(fecha==='pasadas') mf=r.fecha<h;
      return mb&&me&&mf;
    }).sort((a,b)=>(a.fecha+a.hora).localeCompare(b.fecha+b.hora));
  }

  window.mcRenderTabla = function(){
    let lista = mcListaFiltrada();
    const tb = document.getElementById('mc-tbody-reservas');
    if(!lista.length){
      tb.innerHTML=`<tr><td colspan="8"><div class="mc-empty">
        <div class="mc-empty-icon">&#128467;</div>
        <p>No se encontraron reservas con los filtros actuales</p>
      </div></td></tr>`;
      return;
    }
    tb.innerHTML = lista.map(r=>`<tr>
      <td style="font-family:monospace;font-size:11px;color:var(--hint)">#${String(r.id).padStart(2,'0')}</td>
      <td><div style="font-weight:500">${r.nombre}</div><div style="font-size:12px;color:var(--muted)">${r.telefono}</div></td>
      <td>${getMesaLabel(r.mesaId)}</td>
      <td>${r.fecha}</td><td>${r.hora}</td>
      <td style="text-align:center">${r.personas}</td>
      <td><span class="mc-badge ${badgeClass(r.estado)}">${r.estado}</span></td>
      <td><div class="mc-action-btns">
        <button class="mc-icon-btn" onclick="mcVerReserva(${r.id})">Ver</button>
        ${!esCajero() ? `
          <button class="mc-icon-btn edit" onclick="mcEditarReserva(${r.id})">Editar</button>
          <button class="mc-icon-btn del" onclick="mcPedirEliminarReserva(${r.id})">Borrar</button>
        ` : ''}
      </div></td>
    </tr>`).join('');
  };

  window.mcVerReserva = function(id){
    const r = reservas.find(x=>x.id===id); if(!r) return;
    document.getElementById('mc-modal-r-title').textContent = 'Reserva — '+r.nombre;
    document.getElementById('mc-modal-r-body').innerHTML = `
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Cliente</div><div class="mc-detail-val">${r.nombre}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Teléfono</div><div class="mc-detail-val">${r.telefono}</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Email</div><div class="mc-detail-val" style="font-weight:400">${r.email||'—'}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Personas</div><div class="mc-detail-val">${r.personas}</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Fecha</div><div class="mc-detail-val">${r.fecha}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Hora</div><div class="mc-detail-val">${r.hora}</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Mesa</div><div class="mc-detail-val">${getMesaLabel(r.mesaId)}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Estado</div><div class="mc-detail-val"><span class="mc-badge ${badgeClass(r.estado)}">${r.estado}</span></div></div>
      </div>
      ${r.ocasion?`<div class="mc-detail-item" style="margin-bottom:10px"><div class="mc-detail-key">Ocasión</div><div class="mc-detail-val">${r.ocasion}</div></div>`:''}
      ${r.notas?`<div class="mc-detail-item" style="margin-bottom:10px"><div class="mc-detail-key">Notas</div><div class="mc-detail-val" style="font-weight:400;font-size:13px;line-height:1.5">${r.notas}</div></div>`:''}
      <div style="font-size:11px;color:var(--hint);margin-bottom:1rem">
        Creada el ${new Date(r.creada).toLocaleString('es-CO')}
      </div>
      <div class="mc-btn-row">
        <button class="mc-btn mc-btn-secondary" onclick="mcCloseModal('mc-modal-reserva')">Cerrar</button>
        ${!esCajero() ? `<button class="mc-btn mc-btn-primary" onclick="mcCloseModal('mc-modal-reserva');mcEditarReserva(${r.id})">Editar reserva</button>` : ''}
      </div>`;
    document.getElementById('mc-modal-reserva').classList.add('open');
  };

  window.mcEditarReserva = function(id){
    if(esCajero()){ toast('No tienes permisos para realizar esta acción','error'); return; }
    const r = reservas.find(x=>x.id===id); if(!r) return;
    editandoId = id; mcPoblarMesas(); mcShow('crear');
    setTimeout(()=>{
      document.getElementById('mc-c-nombre').value   = r.nombre;
      document.getElementById('mc-c-telefono').value = r.telefono;
      document.getElementById('mc-c-email').value    = r.email||'';
      document.getElementById('mc-c-personas').value = r.personas;
      document.getElementById('mc-c-fecha').value    = r.fecha;
      document.getElementById('mc-c-hora').value     = r.hora;
      mcPoblarMesas();
      document.getElementById('mc-c-mesa').value     = r.mesaId||'';
      document.getElementById('mc-c-ocasion').value  = r.ocasion||'';
      document.getElementById('mc-c-estado').value   = r.estado;
      document.getElementById('mc-c-notas').value    = r.notas||'';
      document.getElementById('mc-crear-titulo').textContent = 'Editar reserva';
      document.getElementById('mc-crear-sub').textContent   = 'Modificando reserva de '+r.nombre;
      document.getElementById('mc-btn-guardar').textContent  = 'Actualizar reserva';
    },30);
  };

  window.mcPedirEliminarReserva = function(id){
    if(esCajero()){ toast('No tienes permisos para realizar esta acción','error'); return; }
    const r = reservas.find(x=>x.id===id); if(!r) return;
    mcConfirm('Eliminar reserva',
      `¿Eliminar la reserva de ${r.nombre} del ${r.fecha}? Esta acción no se puede deshacer.`,
      ()=>{ reservas=reservas.filter(x=>x.id!==id); save(); mcRenderTabla(); toast('Reserva eliminada'); });
  };

  window.mcExportarPDF = function(){
    const lista = mcListaFiltrada();
    if(!lista.length){ toast('No hay reservas para exportar','error'); return; }
    if(!window.jspdf){ toast('No se pudo cargar la librería de PDF','error'); return; }
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text('Asadero Porras — Reporte de Reservas', 14, 16);
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text('Generado el ' + new Date().toLocaleString('es-CO') + '  •  ' + lista.length + ' reserva(s)', 14, 22);
    const filas = lista.map(r => [
      '#' + String(r.id).padStart(2, '0'),
      r.nombre, r.telefono, getMesaLabel(r.mesaId),
      r.fecha, r.hora, String(r.personas), r.estado,
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

  window.mcExportarExcel = function(){
    const lista = mcListaFiltrada();
    if(!lista.length){ toast('No hay reservas para exportar','error'); return; }
    if(!window.XLSX){ toast('No se pudo cargar la librería de Excel','error'); return; }
    const datos = lista.map(r => ({
      'ID': '#' + String(r.id).padStart(2, '0'),
      'Cliente': r.nombre, 'Teléfono': r.telefono, 'Correo': r.email || '',
      'Mesa': getMesaLabel(r.mesaId), 'Fecha': r.fecha, 'Hora': r.hora,
      'Personas': r.personas, 'Ocasión': r.ocasion || '',
      'Estado': r.estado, 'Notas': r.notas || '',
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

  window.mcImprimir = function(){
    const lista = mcListaFiltrada();
    if(!lista.length){ toast('No hay reservas para imprimir','error'); return; }
    const filas = lista.map(r => `<tr>
        <td>#${String(r.id).padStart(2,'0')}</td>
        <td>${r.nombre}</td><td>${r.telefono}</td>
        <td>${getMesaLabel(r.mesaId)}</td>
        <td>${r.fecha}</td><td>${r.hora}</td>
        <td>${r.personas}</td><td>${r.estado}</td>
      </tr>`).join('');
    document.getElementById('mc-print-area').innerHTML = `
      <h2>Asadero Porras — Reporte de Reservas</h2>
      <p>Generado el ${new Date().toLocaleString('es-CO')} — ${lista.length} reserva(s)</p>
      <table>
        <thead><tr>
          <th>ID</th><th>Cliente</th><th>Teléfono</th><th>Mesa</th>
          <th>Fecha</th><th>Hora</th><th>Personas</th><th>Estado</th>
        </tr></thead>
        <tbody>${filas}</tbody>
      </table>`;
    window.print();
  };

  window.mcCrearMesa = function(){
    if(esCajero()){ toast('No tienes permisos para realizar esta acción','error'); return; }
    const num = parseInt(document.getElementById('mc-m-numero').value);
    const cap = parseInt(document.getElementById('mc-m-capacidad').value);
    const ubi = document.getElementById('mc-m-ubicacion').value;
    const est = document.getElementById('mc-m-estado').value;
    if(!num || !cap){ toast('Ingresa número y capacidad','error'); return; }
    if(editandoMesaId){
      if(mesas.find(m => m.numero===num && m.id!==editandoMesaId)){
        toast('Ya existe una mesa con ese número','error'); return;
      }
      mesas = mesas.map(m =>
        m.id===editandoMesaId ? {...m, numero:num, capacidad:cap, ubicacion:ubi, estado:est} : m
      );
      djangoPost('/reservas/mesa/guardar/', { numero_mesa:num, capacidad:cap, ubicacion:ubi, estado:est })
        .catch(e => console.error('Error guardando mesa:', e));
      toast('Mesa actualizada');
    } else {
      if(mesas.find(m=>m.numero===num)){ toast('Ya existe una mesa con ese número','error'); return; }
      const cols=4, size=92, gap=20, offX=28, offY=46;
      const idx=mesas.length, col=idx%cols, row=Math.floor(idx/cols);
      mesas.push({
        id: nextIdM(), numero:num, capacidad:cap, ubicacion:ubi, estado:est,
        x: offX+col*(size+gap), y: offY+row*(size+gap)
      });
      djangoPost('/reservas/mesa/guardar/', { numero_mesa:num, capacidad:cap, ubicacion:ubi, estado:est })
        .catch(e => console.error('Error guardando mesa:', e));
      toast('Mesa '+num+' agregada');
    }
    save(); mcRenderTablaMesas(); mcRenderDiagrama();
    document.getElementById('mc-m-numero').value='';
    document.getElementById('mc-m-capacidad').value='';
    document.getElementById('mc-m-ubicacion').value='Salón principal';
    document.getElementById('mc-m-estado').value='disponible';
    document.querySelector('.mc-card-title').textContent = 'Agregar mesa';
    document.querySelector('#mc-crear-mesa .mc-sec-header h2').textContent = 'Gestión de mesas';
    document.querySelector('#mc-crear-mesa .mc-btn-primary').textContent = 'Agregar mesa';
    editandoMesaId = null;
  };

  function mcListaMesasFiltrada(){
    const buscar    = document.getElementById('mc-buscar-mesa')?.value.toLowerCase() || '';
    const ubicacion = document.getElementById('mc-filtro-ubicacion')?.value || '';
    const capacidad = document.getElementById('mc-filtro-capacidad')?.value || '';
    return mesas.filter(m =>
      String(m.numero).includes(buscar) &&
      (!ubicacion || m.ubicacion===ubicacion) &&
      (!capacidad || m.capacidad==capacidad)
    );
  }

  window.mcRenderTablaMesas = function(){
    const tb = document.getElementById('mc-tbody-mesas');
    if(!tb) return;
    let lista = mcListaMesasFiltrada();
    if(!lista.length){
      tb.innerHTML = `<tr><td colspan="5"><div class="mc-empty"><p>No se encontraron mesas</p></div></td></tr>`;
      return;
    }
    tb.innerHTML = lista.map(m=>`<tr>
      <td style="font-weight:500">Mesa ${m.numero}</td>
      <td>${m.capacidad} pers.</td>
      <td style="font-size:12px;color:var(--muted)">${m.ubicacion}</td>
      <td><span class="mc-badge ${m.estado==='disponible'?'mc-badge-ok':m.estado==='reservada'?'mc-badge-warn':'mc-badge-danger'}">${m.estado}</span></td>
      <td><div class="mc-action-btns">
        <button class="mc-icon-btn" onclick="mcVerMesa(${m.id})">Ver</button>
        ${!esCajero() ? `
          <button class="mc-icon-btn edit" onclick="mcEditarMesa(${m.id})">Editar</button>
          <button class="mc-icon-btn del" onclick="mcPedirEliminarMesa(${m.id})">Borrar</button>
        ` : ''}
      </div></td>
    </tr>`).join('');
  };

  window.mcEditarMesa = function(id){
    if(esCajero()){ toast('No tienes permisos para realizar esta acción','error'); return; }
    const m = mesas.find(x=>x.id===id); if(!m) return;
    editandoMesaId = id;
    mcShow('crear-mesa');
    setTimeout(()=>{
      document.getElementById('mc-m-numero').value    = m.numero;
      document.getElementById('mc-m-capacidad').value = m.capacidad;
      document.getElementById('mc-m-ubicacion').value = m.ubicacion;
      document.getElementById('mc-m-estado').value    = m.estado;
      document.querySelector('.mc-card-title').textContent = 'Editar mesa';
      document.querySelector('#mc-crear-mesa .mc-sec-header h2').textContent = 'Editando mesa ' + m.numero;
      document.querySelector('#mc-crear-mesa .mc-btn-primary').textContent = 'Actualizar mesa';
    },30);
    toast('Editando mesa ' + m.numero);
  };

  window.mcRenderDiagrama = function(){
    const fe = document.getElementById('mc-filtro-diagrama').value;
    const fu = document.getElementById('mc-filtro-zona').value;
    let lista = mesas;
    if(fe) lista=lista.filter(m=>m.estado===fe);
    if(fu) lista=lista.filter(m=>m.ubicacion===fu);
    const d=mesas.filter(m=>m.estado==='disponible').length;
    const r=mesas.filter(m=>m.estado==='reservada').length;
    const o=mesas.filter(m=>m.estado==='ocupada').length;
    document.getElementById('mc-resumen').textContent=`${d} disponibles · ${r} reservadas · ${o} ocupadas`;
    document.getElementById('mc-floor-count').textContent=lista.length+' mesa'+(lista.length!==1?'s':'')+' mostradas';
    document.getElementById('mc-zone-label').textContent=fu||'Todas las zonas';
    const cont=document.getElementById('mc-floor-mesas');
    const wrap=document.getElementById('mc-floor');
    if(!lista.length){
      cont.innerHTML=`<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--hint);font-size:14px">Sin mesas para mostrar</div>`;
      wrap.style.minHeight='200px'; return;
    }
    const cols=4,size=92,gap=18,offX=28,offY=46;
    const rows=Math.ceil(lista.length/cols);
    wrap.style.minHeight=(rows*(size+gap)+offY+36)+'px';
    cont.innerHTML=lista.map((m,i)=>{
      const col=i%cols,row=Math.floor(i/cols);
      const x=offX+col*(size+gap), y=offY+row*(size+gap);
      const ra=reservas.find(r=>r.mesaId===m.id&&r.estado==='confirmada');
      const tip=m.estado==='reservada'&&ra?`${ra.nombre} · ${ra.fecha} ${ra.hora}`:`${m.capacidad} personas · ${m.ubicacion}`;
      return `<div class="mc-mesa ${m.estado}" style="left:${x}px;top:${y}px;width:${size}px;height:76px" onclick="mcVerMesa(${m.id})">
        <div class="mc-mesa-num">Mesa ${m.numero}</div>
        <div class="mc-mesa-cap">${m.capacidad} pers.</div>
        <div class="mc-mesa-dot"></div>
        <div class="mc-tooltip">${tip}</div>
      </div>`;
    }).join('');
  };

  window.mcVerMesa = function(id){
    const m=mesas.find(x=>x.id===id); if(!m) return;
    const ras=reservas.filter(r=>r.mesaId===id&&r.estado!=='cancelada');
    const bc=m.estado==='disponible'?'mc-badge-ok':m.estado==='reservada'?'mc-badge-warn':'mc-badge-danger';
    document.getElementById('mc-modal-m-title').textContent='Mesa '+m.numero;
    document.getElementById('mc-modal-m-body').innerHTML=`
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Número</div><div class="mc-detail-val">Mesa ${m.numero}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Capacidad</div><div class="mc-detail-val">${m.capacidad} personas</div></div>
      </div>
      <div class="mc-detail-row">
        <div class="mc-detail-item"><div class="mc-detail-key">Ubicación</div><div class="mc-detail-val">${m.ubicacion}</div></div>
        <div class="mc-detail-item"><div class="mc-detail-key">Estado</div><div class="mc-detail-val"><span class="mc-badge ${bc}">${m.estado}</span></div></div>
      </div>
      ${ras.length?`
        <div style="margin:14px 0 10px;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)">Reservas activas (${ras.length})</div>
        ${ras.map(r=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--border);font-size:13px">
          <div><div style="font-weight:500">${r.nombre}</div><div style="font-size:12px;color:var(--muted)">${r.personas} pers. · ${r.fecha} ${r.hora}</div></div>
          <span class="mc-badge ${badgeClass(r.estado)}">${r.estado}</span>
        </div>`).join('')}`
        :`<p style="font-size:13px;color:var(--muted);margin:12px 0">Sin reservas activas en esta mesa.</p>`}
      ${!esCajero() ? `
      <div style="margin-top:1.2rem;padding-top:1rem;border-top:1px solid var(--border)">
        <label class="mc-label" style="display:block;margin-bottom:7px">Cambiar estado</label>
        <div style="display:flex;gap:8px;align-items:center">
          <select class="mc-select" id="mc-nuevo-estado" style="flex:1">
            <option value="disponible" ${m.estado==='disponible'?'selected':''}>Disponible</option>
            <option value="reservada"  ${m.estado==='reservada'?'selected':''}>Reservada</option>
            <option value="ocupada"    ${m.estado==='ocupada'?'selected':''}>Ocupada</option>
          </select>
          <button class="mc-btn mc-btn-primary" onclick="mcCambiarEstadoMesa(${m.id},${m.numero})">Actualizar</button>
        </div>
      </div>` : ''}
      <div class="mc-btn-row">
        <button class="mc-btn mc-btn-secondary" onclick="mcCloseModal('mc-modal-mesa')">Cerrar</button>
      </div>`;
    document.getElementById('mc-modal-mesa').classList.add('open');
  };

  window.mcCambiarEstadoMesa = function(id, numeroMesa){
    if(esCajero()){ toast('No tienes permisos para realizar esta acción','error'); return; }
    const est = document.getElementById('mc-nuevo-estado').value;
    const mesa = mesas.find(m=>m.id===id);
    mesas = mesas.map(m=>m.id===id?{...m,estado:est}:m);
    if(mesa){
      djangoPost('/reservas/mesa/guardar/', {
        numero_mesa: numeroMesa, capacidad: mesa.capacidad,
        ubicacion: mesa.ubicacion, estado: est,
      }).catch(e => console.error('Error actualizando estado:', e));
    }
    save(); mcCloseModal('mc-modal-mesa'); mcRenderDiagrama(); mcRenderTablaMesas(); toast('Estado actualizado');
  };

  window.mcPedirEliminarMesa = function(id){
    if(esCajero()){ toast('No tienes permisos para realizar esta acción','error'); return; }
    const m=mesas.find(x=>x.id===id); if(!m) return;
    mcConfirm('Eliminar mesa',
      `¿Eliminar la Mesa ${m.numero}? También se perderán sus reservas asociadas.`,
      ()=>{
        mesas   = mesas.filter(x=>x.id!==id);
        reservas= reservas.filter(r=>r.mesaId!==id);
        djangoPost('/reservas/mesa/eliminar/', { numero_mesa: m.numero })
          .catch(e => console.error('Error eliminando mesa:', e));
        save(); mcRenderTablaMesas(); mcRenderDiagrama(); toast('Mesa eliminada');
      });
  };

  window.mcExportarMesasPDF = function(){
    const lista = mcListaMesasFiltrada();
    if(!lista.length){ toast('No hay mesas para exportar','error'); return; }
    if(!window.jspdf){ toast('No se pudo cargar la librería de PDF','error'); return; }
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text('Asadero Porras — Reporte de Mesas', 14, 16);
    doc.setFontSize(10); doc.setTextColor(100);
    doc.text('Generado el ' + new Date().toLocaleString('es-CO') + '  •  ' + lista.length + ' mesa(s)', 14, 22);
    const filas = lista.map(m => ['Mesa ' + m.numero, String(m.capacidad) + ' pers.', m.ubicacion, m.estado]);
    doc.autoTable({
      head: [['Mesa', 'Capacidad', 'Ubicación', 'Estado']], body: filas, startY: 28,
      styles: { font: 'helvetica', fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [192, 57, 43], textColor: 255 },
      alternateRowStyles: { fillColor: [245, 236, 215] },
    });
    doc.save('mesas_' + hoy() + '.pdf');
    toast('Reporte PDF generado');
  };

  window.mcExportarMesasExcel = function(){
    const lista = mcListaMesasFiltrada();
    if(!lista.length){ toast('No hay mesas para exportar','error'); return; }
    if(!window.XLSX){ toast('No se pudo cargar la librería de Excel','error'); return; }
    const datos = lista.map(m => ({
      'Mesa': 'Mesa ' + m.numero, 'Capacidad': m.capacidad,
      'Ubicación': m.ubicacion, 'Estado': m.estado,
    }));
    const hoja = XLSX.utils.json_to_sheet(datos);
    hoja['!cols'] = [{ wch: 12 }, { wch: 12 }, { wch: 22 }, { wch: 14 }];
    const libro = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(libro, hoja, 'Mesas');
    XLSX.writeFile(libro, 'mesas_' + hoy() + '.xlsx');
    toast('Reporte Excel generado');
  };

  window.mcImprimirMesas = function(){
    const lista = mcListaMesasFiltrada();
    if(!lista.length){ toast('No hay mesas para imprimir','error'); return; }
    const filas = lista.map(m => `<tr>
        <td>Mesa ${m.numero}</td><td>${m.capacidad} pers.</td>
        <td>${m.ubicacion}</td><td>${m.estado}</td>
      </tr>`).join('');
    document.getElementById('mc-print-area').innerHTML = `
      <h2>Asadero Porras — Reporte de Mesas</h2>
      <p>Generado el ${new Date().toLocaleString('es-CO')} — ${lista.length} mesa(s)</p>
      <table>
        <thead><tr><th>Mesa</th><th>Capacidad</th><th>Ubicación</th><th>Estado</th></tr></thead>
        <tbody>${filas}</tbody>
      </table>`;
    window.print();
  };

  if(mesas.length) contadorM = Math.max(contadorM, ...mesas.map(m=>m.id||0));

  function fijarFechaMin(){
    const input = document.getElementById('mc-c-fecha');
    if(input) input.min = hoy();
  }

  save();
  fijarFechaMin();
  mcPoblarMesas();
  mcRenderTabla();
})();