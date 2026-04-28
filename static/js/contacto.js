/* ============================================================
   contacto.js — Porras Asadero
   Incluye: validaciones, seguridad, animaciones, UX
   ============================================================ */

'use strict';

// ── 1. SANITIZACIÓN (previene XSS) ─────────────────────────
function sanitize(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ── 2. VALIDACIONES ─────────────────────────────────────────
const VALIDATORS = {
    nombre: {
        regex: /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]{2,60}$/,
        msg: 'El nombre solo puede tener letras y debe tener entre 2 y 60 caracteres.'
    },
    email: {
        regex: /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/,
        msg: 'Ingresa un correo electrónico válido.'
    },
    telefono: {
        regex: /^[0-9]{7,15}$/,
        msg: 'El teléfono debe tener entre 7 y 15 dígitos numéricos.'
    },
    mensaje: {
        validate: (val) => val.trim().length >= 10 && val.trim().length <= 1000,
        msg: 'El mensaje debe tener entre 10 y 1000 caracteres.'
    }
};

function validarCampo(name, value) {
    const rule = VALIDATORS[name];
    if (!rule) return null;
    if (rule.regex)     return rule.regex.test(value.trim())    ? null : rule.msg;
    if (rule.validate)  return rule.validate(value)             ? null : rule.msg;
    return null;
}

function mostrarError(field, msg) {
    limpiarError(field);
    field.classList.add('is-invalid');
    const err = document.createElement('div');
    err.className = 'invalid-feedback campo-error';
    err.textContent = msg;
    field.parentNode.appendChild(err);
}

function limpiarError(field) {
    field.classList.remove('is-invalid');
    field.classList.remove('is-valid');
    const prev = field.parentNode.querySelector('.campo-error');
    if (prev) prev.remove();
}

function marcarValido(field) {
    limpiarError(field);
    field.classList.add('is-valid');
}

// ── 3. ANTI-SPAM: rate limit por localStorage ───────────────
const SPAM_KEY   = 'contacto_ultimo_envio';
const SPAM_LIMIT = 60 * 1000; // 1 minuto entre envíos

function puedeEnviar() {
    const ultimo = localStorage.getItem(SPAM_KEY);
    if (!ultimo) return true;
    return (Date.now() - parseInt(ultimo)) > SPAM_LIMIT;
}

function registrarEnvio() {
    localStorage.setItem(SPAM_KEY, Date.now().toString());
}

function tiempoRestante() {
    const ultimo = localStorage.getItem(SPAM_KEY);
    if (!ultimo) return 0;
    const diff = SPAM_LIMIT - (Date.now() - parseInt(ultimo));
    return Math.max(0, Math.ceil(diff / 1000));
}

// ── 4. HONEYPOT (campo oculto anti-bots) ────────────────────
// Agrega en tu HTML dentro del form:
// <input type="text" name="website" id="honeypot" style="display:none;" tabindex="-1" autocomplete="off">
function verificarHoneypot(form) {
    const honey = form.querySelector('#honeypot');
    return honey ? honey.value === '' : true;
}

// ── 5. LONGITUD MÁXIMA en tiempo real ───────────────────────
function initContadores() {
    document.querySelectorAll('[data-maxlength]').forEach(field => {
        const max = parseInt(field.dataset.maxlength);
        const counter = document.createElement('small');
        counter.className = 'text-muted d-block text-end mt-1';
        counter.textContent = `0 / ${max}`;
        field.parentNode.appendChild(counter);

        field.addEventListener('input', () => {
            const len = field.value.length;
            counter.textContent = `${len} / ${max}`;
            counter.style.color = len > max * 0.9 ? '#e74c3c' : '';
            if (len > max) field.value = field.value.slice(0, max);
        });
    });
}

// ── 6. VALIDACIÓN EN TIEMPO REAL (al salir del campo) ───────
function initValidacionLive() {
    ['nombre', 'email', 'telefono', 'mensaje'].forEach(name => {
        const field = document.querySelector(`[name="${name}"]`);
        if (!field) return;

        field.addEventListener('blur', () => {
            const error = validarCampo(name, field.value);
            if (error) mostrarError(field, error);
            else if (field.value.trim()) marcarValido(field);
        });

        field.addEventListener('input', () => {
            if (field.classList.contains('is-invalid')) {
                const error = validarCampo(name, field.value);
                if (!error) marcarValido(field);
            }
        });
    });
}

// ── 7. ENVÍO DEL FORMULARIO ──────────────────────────────────
function enviarForm(e) {
    e.preventDefault();
    const form = e.target;
    const btn  = document.getElementById('btnSubmit');

    // Honeypot check
    if (!verificarHoneypot(form)) {
        console.warn('Bot detectado.');
        return;
    }

    // Rate limit
    if (!puedeEnviar()) {
        const seg = tiempoRestante();
        mostrarAlerta(`Espera ${seg} segundos antes de enviar otro mensaje.`, 'warning');
        return;
    }

    // Validar todos los campos
    const campos = ['nombre', 'email', 'telefono', 'mensaje'];
    let valido = true;

    campos.forEach(name => {
        const field = form.querySelector(`[name="${name}"]`);
        if (!field) return;
        const error = validarCampo(name, field.value);
        if (error) {
            mostrarError(field, error);
            valido = false;
        } else {
            marcarValido(field);
        }
    });

    if (!valido) {
        mostrarAlerta('Por favor corrige los errores antes de enviar.', 'danger');
        return;
    }

    // Sanitizar antes de "enviar"
    campos.forEach(name => {
        const field = form.querySelector(`[name="${name}"]`);
        if (field) field.value = sanitize(field.value);
    });

    // Éxito
    registrarEnvio();
    btn.disabled    = true;
    btn.textContent = '✓ Mensaje Enviado';
    btn.style.background = '#2ecc71';

    mostrarAlerta('¡Mensaje enviado! Te responderemos pronto.', 'success');

    setTimeout(() => {
        btn.textContent     = 'Enviar Mensaje';
        btn.style.background = '';
        btn.disabled        = false;
        form.reset();
        form.querySelectorAll('.is-valid, .is-invalid').forEach(f => {
            f.classList.remove('is-valid', 'is-invalid');
        });
        form.querySelectorAll('.campo-error').forEach(e => e.remove());
    }, 3000);
}

// ── 8. ALERTA FLOTANTE ───────────────────────────────────────
function mostrarAlerta(msg, tipo = 'success') {
    const existing = document.querySelector('.alerta-flotante');
    if (existing) existing.remove();

    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alerta-flotante shadow`;
    alerta.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 9999;
        min-width: 280px; max-width: 360px;
        animation: slideIn .3s ease;
    `;
    alerta.textContent = msg;
    document.body.appendChild(alerta);
    setTimeout(() => alerta.remove(), 4000);
}

// ── 9. ANIMACIONES DE SCROLL ─────────────────────────────────
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.style.opacity   = '1';
            e.target.style.transform = 'translateY(0)';
            observer.unobserve(e.target); // deja de observar una vez visible
        }
    });
}, { threshold: 0.1 });

function initAnimaciones() {
    document.querySelectorAll('.menu-card, .contacto-card').forEach((el, i) => {
        el.style.opacity    = '0';
        el.style.transform  = 'translateY(20px)';
        el.style.transition = `opacity .5s ease ${i * 0.08}s, transform .5s ease ${i * 0.08}s`;
        observer.observe(el);
    });
}

// ── 10. INIT ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initAnimaciones();
    initValidacionLive();
    initContadores();

    // Inyectar keyframe para la alerta flotante
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(40px); }
            to   { opacity: 1; transform: translateX(0); }
        }
    `;
    document.head.appendChild(style);
});
// ═══════════════════════════════════════════
// MODAL EDITAR ORDEN
// ═══════════════════════════════════════════
function abrirEditarOrden(pk, numero, pedidoPk, estado, subtotal, impuesto, notas) {
  document.getElementById('modal-orden-numero').textContent = numero;
  document.getElementById('modal-orden-pedido').value   = pedidoPk;
  document.getElementById('modal-orden-estado').value   = estado;
  document.getElementById('modal-orden-subtotal').value = subtotal;
  document.getElementById('modal-orden-impuesto').value = impuesto;
  document.getElementById('modal-orden-notas').value    = notas;

  // Apunta el form a la URL correcta de edición
  const base = "{% url 'pedidos:orden_editar' 9999 %}";
  document.getElementById('form-editar-orden').action = base.replace('9999', pk);

  document.getElementById('modal-editar-orden').classList.add('open');
}

function closeModalOrden() {
  document.getElementById('modal-editar-orden').classList.remove('open');
}

document.getElementById('modal-editar-orden').addEventListener('click', function(e) {
  if (e.target === this) closeModalOrden();
});