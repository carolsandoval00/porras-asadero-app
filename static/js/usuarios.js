(function(){

const PERMS=['Ver reservas','Crear reservas','Editar reservas','Eliminar reservas',
             'Ver mesas','Gestionar mesas','Ver reportes','Gestionar pagos',
             'Ver usuarios','Gestionar usuarios','Configuración','Acceso total'];
const COLS=['#1A1008','#C0392B','#E8651A','#8B2000','#D4A017','#633806','#C0502A'];



let djangoData = [];
try {
    djangoData = JSON.parse('{{ personal_list_json|escapejs }}');
} catch(e) {
    djangoData = [];
}

let uList = djangoData.length ? djangoData : JSON.parse(localStorage.getItem('poa_u') || '[]');
if(djangoData.length) localStorage.setItem('poa_u', JSON.stringify(uList));

let editId = null;
const save = () => localStorage.setItem('poa_u', JSON.stringify(uList));

function getCookie(name) {
    let val = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(c => {
            c = c.trim();
            if (c.startsWith(name + '=')) val = decodeURIComponent(c.slice(name.length + 1));
        });
    }
    return val;
}

const col = (i) => COLS[i % COLS.length];
const ini = (n, a) => ((n||'?')[0] + (a||'?')[0]).toUpperCase();
const bRol = (r) => {
    const m = {Administrador:'b-admin', Mesero:'b-mesero', Cajero:'b-cajero', Cocina:'b-cocina'};
    return `<span class="bdg ${m[r]||'b-admin'}">${r}</span>`;
};
const bEst = (e) => `<span class="bdg ${e==='activo'?'b-activo':'b-inactivo'}">${e}</span>`;

const avSm = (u, idx) => u.foto
    ? `<img src="${u.foto}" style="width:38px;height:38px;border-radius:50%;object-fit:cover;flex-shrink:0;">`
    : `<div class="av" style="background:${col(idx)}">${ini(u.nom, u.ape)}</div>`;

const avLg = (u, idx) => u.foto
    ? `<img src="${u.foto}" style="width:72px;height:72px;border-radius:50%;object-fit:cover;flex-shrink:0;border:3px solid #FDF7EC;">`
    : `<div class="av-lg" style="background:${col(idx)}">${ini(u.nom, u.ape)}</div>`;

window.nav = function(id) {
    document.querySelectorAll('.usr-sec').forEach(s => s.classList.remove('activa'));
    document.getElementById('sec-' + id).classList.add('activa');
    document.querySelectorAll('.usr-tab').forEach(t => t.classList.remove('activo'));
    document.querySelectorAll('.usr-tab').forEach(t => {
        if (t.getAttribute('onclick') && t.getAttribute('onclick').includes("'" + id + "'"))
            t.classList.add('activo');
    });
    if (id === 'lista') { stats(); renderTabla(); }
    if (id === 'crear' && !editId) { limpiar(); }
};

function toast(msg, tipo) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.className = 'toast show ' + (tipo || '');
    clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('show'), 2800);
}

window.cConfirm = () => document.getElementById('cf-bg').classList.remove('open');
function confirm2(tit, msg, cb) {
    document.getElementById('cf-tit').textContent = tit;
    document.getElementById('cf-msg').textContent = msg;
    document.getElementById('cf-ok').onclick = () => { cConfirm(); cb(); };
    document.getElementById('cf-bg').classList.add('open');
}
window.cModal = id => document.getElementById(id).classList.remove('open');

function stats() {
    const t  = uList.length,
          a  = uList.filter(u => u.e === 'activo').length,
          i  = uList.filter(u => u.e === 'inactivo').length,
          ad = uList.filter(u => u.rol === 'Administrador').length;
    document.getElementById('stats-ctn').innerHTML =
        `<div class="stat-box"><div class="stat-num">${t}</div><div class="stat-lbl"><span class="s-dot" style="background:#1A1008"></span>Total</div></div>
         <div class="stat-box"><div class="stat-num">${a}</div><div class="stat-lbl"><span class="s-dot" style="background:#E8651A"></span>Activos</div></div>
         <div class="stat-box"><div class="stat-num">${i}</div><div class="stat-lbl"><span class="s-dot" style="background:#C0392B"></span>Inactivos</div></div>
         <div class="stat-box"><div class="stat-num">${ad}</div><div class="stat-lbl"><span class="s-dot" style="background:#D4A017"></span>Admins</div></div>`;
}

window.renderTabla = function() {
    stats();
    const q = document.getElementById('f-buscar').value.toLowerCase();
    const r = document.getElementById('f-rol').value;
    const e = document.getElementById('f-est').value;
    let li = uList.filter(u =>
        (!q || u.nom.toLowerCase().includes(q) || u.ape.toLowerCase().includes(q) ||
               u.user.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)) &&
        (!r || u.rol === r) && (!e || u.e === e));
    const tb = document.getElementById('tbody');
    if (!li.length) {
        tb.innerHTML = `<tr><td colspan="7"><div class="vacio"><div class="v-ic">👤</div><p>Sin resultados con esos filtros</p></div></td></tr>`;
        return;
    }
    tb.innerHTML = li.map(u => `
        <tr id="fila-${u.id}">
          <td><div style="display:flex;align-items:center;gap:9px">
              ${avSm(u, uList.indexOf(u))}
              <strong>@${u.user}</strong></div></td>
          <td>${u.nom} ${u.ape}</td>
          <td style="font-size:.83rem;color:var(--muted)">${u.email}</td>
          <td>${bRol(u.rol)}</td>
          <td>${bEst(u.e)}</td>
          <td><div style="display:flex;gap:4px;flex-wrap:wrap">
              <button class="btn-ac btn-ver"  onclick="verPerfil(${u.id})">Ver perfil</button>
              <button class="btn-ac btn-edit" onclick="editar(${u.id})">Editar</button>
              <button class="btn-ac btn-del"  onclick="pedirDel(${u.id})">Eliminar</button>
          </div></td>
        </tr>`).join('');
};

window.verPerfil = function(id) {
    const u = uList.find(x => x.id === id); if (!u) return;
    const idx = uList.indexOf(u);
    document.getElementById('p-titulo').textContent = u.nom + ' ' + u.ape;
    document.getElementById('p-sub').textContent = '@' + u.user + ' · ' + u.rol;
    const tp = document.getElementById('tab-perfil');
    tp.style.display = '';
    document.getElementById('tab-perfil-txt').textContent = u.nom;
    document.getElementById('perfil-ctn').innerHTML = `
        <div class="p-hero">
            ${avLg(u, idx)}
            <div class="p-hero-info">
                <h3>${u.nom} ${u.ape}</h3>
                <div class="sub">@${u.user}</div>
                <div class="p-meta">${bRol(u.rol)} ${bEst(u.e)}</div>
            </div>
        </div>
        <div class="usr-card">
            <div class="c-label">Información personal</div>
            <div class="det-g">
                <div class="det-it"><div class="det-k">Nombre completo</div><div class="det-v">${u.nom} ${u.ape}</div></div>
                <div class="det-it"><div class="det-k">Correo</div><div class="det-v" style="font-weight:400;font-size:.85rem">${u.email}</div></div>
                <div class="det-it"><div class="det-k">Teléfono</div><div class="det-v">${u.tel||'—'}</div></div>
                <div class="det-it"><div class="det-k">Documento</div><div class="det-v">${u.tdoc?u.tdoc+' '+u.doc:u.doc||'—'}</div></div>
                <div class="det-it" style="grid-column:1/-1"><div class="det-k">Dirección</div><div class="det-v" style="font-weight:400">${u.dir||'—'}</div></div>
            </div>
        </div>
        <div class="usr-card">
            <div class="c-label">Cuenta del sistema</div>
            <div class="det-g">
                <div class="det-it"><div class="det-k">Usuario</div><div class="det-v">@${u.user}</div></div>
                <div class="det-it"><div class="det-k">Rol</div><div class="det-v">${bRol(u.rol)}</div></div>
                <div class="det-it"><div class="det-k">Estado</div><div class="det-v">${bEst(u.e)}</div></div>
                <div class="det-it"><div class="det-k">Último acceso</div><div class="det-v" style="font-weight:400;font-size:.85rem">${u.acc||'—'}</div></div>
                <div class="det-it"><div class="det-k">Registro</div><div class="det-v" style="font-weight:400;font-size:.85rem">${new Date(u.cr).toLocaleString('es-CO')}</div></div>
            </div>
        </div>
        <div class="usr-card">
            <div class="c-label">Permisos asignados (${(u.perms||[]).length})</div>
            <div class="perm-g">
                ${PERMS.map(p => `<div class="perm-it ${(u.perms||[]).includes(p)?'on':''}">
                    <div class="perm-dot"></div>${p}</div>`).join('')}
            </div>
        </div>
      
        ${u.notas ? `<div class="usr-card"><div class="c-label">Notas internas</div><p style="font-size:.88rem;color:#6B5A3E;line-height:1.6">${u.notas}</p></div>` : ''}
        <div style="display:flex;gap:.7rem;flex-wrap:wrap;margin-top:.5rem">
            <button class="btn btn-ok" onclick="editar(${u.id})"><i class="bi bi-pencil"></i> Editar</button>
            <button class="btn btn-del2" onclick="nav('lista');pedirDel(${u.id})"><i class="bi bi-trash"></i> Eliminar</button>
        </div>`;
    nav('perfil');
};

window.editar = function(id) {
    const u = uList.find(x => x.id === id); if (!u) return;
    editId = id; nav('crear');
    setTimeout(() => {
        document.getElementById('cr-titulo').textContent = 'Editar usuario';
        document.getElementById('cr-sub').textContent = 'Modificando datos de ' + u.nom + ' ' + u.ape;
        document.getElementById('btn-grd').innerHTML = '<i class="bi bi-check-lg"></i> Guardar cambios';
        document.getElementById('u-nom').value   = u.nom;
        document.getElementById('u-ape').value   = u.ape;
        document.getElementById('u-email').value = u.email;
        document.getElementById('u-tel').value   = u.tel || '';
        document.getElementById('u-doc').value   = u.doc || '';
        document.getElementById('u-tdoc').value  = u.tdoc || '';
        document.getElementById('u-dir').value   = u.dir || '';
        document.getElementById('u-user').value  = u.user;
        document.getElementById('u-rol').value   = u.rol;
        document.getElementById('u-est').value   = u.e;
        document.getElementById('u-notas').value = u.notas || '';
        document.getElementById('pw-nuevo').style.display = 'none';
        document.getElementById('pw-edit').style.display  = '';
        document.getElementById('cb-pw').checked = false;
        document.getElementById('pw-edit-campos').style.display = 'none';
        renderPermsForm(u.perms || []);
    }, 30);
};

window.guardar = function() {
    const nom = document.getElementById('u-nom').value.trim();
    const ape = document.getElementById('u-ape').value.trim();
    const ema = document.getElementById('u-email').value.trim();
    const usr = document.getElementById('u-user').value.trim();
    const rol = document.getElementById('u-rol').value;
    const tel = document.getElementById('u-tel').value.trim();

    if (!nom || !ape || !ema || !usr || !rol) { toast('Completa los campos obligatorios (*)', 'err'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(ema)) { toast('El correo electrónico no es válido', 'err'); return; }
    if (tel) {
        if (!/^\d+$/.test(tel)) { toast('El teléfono solo debe contener números', 'err'); return; }
        if (tel.length > 10)    { toast('El teléfono no puede tener más de 10 dígitos', 'err'); return; }
    }
    const doc = document.getElementById('u-doc').value.trim();
    if (doc) {
        if (!/^\d+$/.test(doc))           { toast('El documento solo debe contener números', 'err'); return; }
        if (doc.length < 6 || doc.length > 10) { toast('El documento debe tener entre 6 y 10 dígitos', 'err'); return; }
    }
    if (!editId) {
        const pw  = document.getElementById('u-pw').value;
        const pw2 = document.getElementById('u-pw2').value;
        if (!pw || pw.length < 6) { toast('Contraseña mínimo 6 caracteres', 'err'); return; }
        if (pw !== pw2)           { toast('Las contraseñas no coinciden', 'err'); return; }
        if (uList.find(u => u.user === usr)) { toast('Ese usuario ya existe', 'err'); return; }
    }
    if (editId && document.getElementById('cb-pw').checked) {
        const pw  = document.getElementById('u-pw-e').value;
        const pw2 = document.getElementById('u-pw2-e').value;
        if (!pw || pw.length < 6) { toast('Contraseña mínimo 6 caracteres', 'err'); return; }
        if (pw !== pw2)           { toast('Las contraseñas no coinciden', 'err'); return; }
    }
    const perms = [];
    document.querySelectorAll('#perm-form .perm-it.on').forEach(el => perms.push(el.dataset.p));
    const obj = {
        id: editId || Date.now(), nom, ape, email: ema, user: usr, rol,
        e:    document.getElementById('u-est').value,
        tel,
        doc:  document.getElementById('u-doc').value.trim(),
        tdoc: document.getElementById('u-tdoc').value,
        dir:  document.getElementById('u-dir').value.trim(),
        notas:document.getElementById('u-notas').value.trim(),
        foto: editId ? (uList.find(u => u.id === editId) || {}).foto || '' : '',
        perms,
        acc:  editId ? (uList.find(u => u.id === editId) || {}).acc || '—' : '—',
        cr:   editId ? (uList.find(u => u.id === editId) || {}).cr  || new Date().toISOString() : new Date().toISOString()
    };
    const url = editId ? `/usuarios/editar/${editId}/` : `/usuarios/crear/`;
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(obj),
    })
    .then(res => res.json())
    .then(data => {
        if (data.ok) {
            if (!editId && data.id) obj.id = data.id;
            if (editId) {
                uList = uList.map(u => u.id === editId ? obj : u);
                toast('Usuario actualizado', 'ok');
            } else {
                uList.push(obj);
                toast('Usuario creado', 'ok');
            }
            save(); limpiar(); nav('lista');
        } else {
            toast(data.error || 'Error al guardar', 'err');
        }
    })
    .catch(() => toast('Error de conexión', 'err'));
};

window.limpiar = function() {
    editId = null;
    ['u-nom','u-ape','u-email','u-tel','u-doc','u-user','u-dir','u-notas','u-pw','u-pw2']
        .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    document.getElementById('u-tdoc').value = '';
    document.getElementById('u-rol').value  = '';
    document.getElementById('u-est').value  = 'activo';
    document.getElementById('cr-titulo').textContent = 'Nuevo usuario';
    document.getElementById('cr-sub').textContent    = 'Completa los datos del nuevo integrante';
    document.getElementById('btn-grd').innerHTML     = '<i class="bi bi-person-check"></i> Crear usuario';
    document.getElementById('pw-nuevo').style.display = '';
    document.getElementById('pw-edit').style.display  = 'none';
    renderPermsForm([]);
};

function renderPermsForm(activos) {
    document.getElementById('perm-form').innerHTML =
        PERMS.map(p => `<div class="perm-it ${activos.includes(p)?'on':''}" data-p="${p}"
            onclick="this.classList.toggle('on')"><div class="perm-dot"></div>${p}</div>`).join('');
}

window.pedirDel = function(id) {
    const u = uList.find(x => x.id === id); if (!u) return;
    confirm2(
        'Eliminar usuario',
        `¿Eliminar a ${u.nom} ${u.ape} (@${u.user})? Esta acción no se puede deshacer.`,
        () => {
            const fila = document.getElementById('fila-' + id);
            if (fila) {
                fila.style.transition = 'opacity .3s, transform .3s';
                fila.style.opacity    = '0';
                fila.style.transform  = 'translateX(20px)';
            }
            fetch(`/usuarios/eliminar/${id}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(res => {
                if (res.ok || res.redirected) {
                    setTimeout(() => {
                        uList = uList.filter(x => x.id !== id);
                        save();
                        renderTabla();
                        toast('Usuario eliminado correctamente', 'err');
                    }, 300);
                } else {
                    if (fila) { fila.style.opacity = '1'; fila.style.transform = 'none'; }
                    toast('Error al eliminar el usuario', 'err');
                }
            })
            .catch(() => {
                if (fila) { fila.style.opacity = '1'; fila.style.transform = 'none'; }
                toast('Error de conexión', 'err');
            });
        }
    );
};

window.tPw = function(id, btn) {
    const el = document.getElementById(id);
    const h  = el.type === 'password';
    el.type  = h ? 'text' : 'password';
    btn.textContent = h ? 'Ocultar' : 'Ver';
};
window.tPwEdit = function() {
    document.getElementById('pw-edit-campos').style.display =
        document.getElementById('cb-pw').checked ? '' : 'none';
};

function initDemo() {
    if (uList.length) return;
    uList = [
        {id:1,nom:'Admin',ape:'Sistema',email:'admin@porras.com',user:'admin',rol:'Administrador',e:'activo',tel:'3001111111',doc:'1000001',tdoc:'Cédula de Ciudadanía',dir:'Calle 1 #1-1',notas:'Cuenta principal.',foto:'',perms:PERMS,acc:'Hoy 09:15',cr:new Date().toISOString()},
        {id:3,nom:'Carlos',ape:'Mendoza',email:'carlos@porras.com',user:'cmendoza',rol:'Mesero',e:'activo',tel:'3204567890',doc:'3000003',tdoc:'Cédula de Ciudadanía',dir:'Av. 68 #23-4',notas:'Turno diurno.',foto:'',perms:['Ver reservas','Crear reservas'],acc:'Ayer 20:10',cr:new Date().toISOString()},
        {id:4,nom:'Sofía',ape:'Torres',email:'sofia@porras.com',user:'storres',rol:'Cajero',e:'activo',tel:'3156789012',doc:'4000004',tdoc:'Cédula de Ciudadanía',dir:'Calle 93 #15-20',notas:'',foto:'',perms:['Gestionar pagos','Ver reportes'],acc:'Ayer 21:00',cr:new Date().toISOString()},
        {id:5,nom:'Miguel',ape:'Vargas',email:'miguel@porras.com',user:'mvargas',rol:'Cocina',e:'inactivo',tel:'3009876543',doc:'5000005',tdoc:'Cédula de Ciudadanía',dir:'Transversal 20 #8-3',notas:'En vacaciones.',foto:'',perms:[],acc:'15/03/2026',cr:new Date().toISOString()},
    ];
    save();
}

initDemo(); stats(); renderTabla();

const params = new URLSearchParams(window.location.search);
if (params.get('seccion') === 'crear') nav('crear');

})();
