/* =====================================================
   ACCESIBILIDAD - Porras Asadero  (v2)
   Lógica del widget: tamaño de texto, fuente, temas y
   toggles simples, con persistencia en localStorage.
   ===================================================== */
(function () {
    'use strict';

    const STORAGE_KEY = 'porrasA11yPrefs';
    const HTML = document.documentElement;

    const TOGGLE_CLASSES = ['a11y-underline-links', 'a11y-no-motion', 'a11y-big-cursor'];
    const THEME_CLASS_PREFIX = 'a11y-theme-';
    const THEMES = ['normal', 'oscuro', 'grises', 'daltonismo'];

    // Escala de tamaños: ratio respecto a 18 px (normal) y su etiqueta en px.
    const FONT_SIZES = [
        { ratio: 0.89, px: 16 },
        { ratio: 1,    px: 18 },
        { ratio: 1.11, px: 20 },
        { ratio: 1.22, px: 22 },
        { ratio: 1.33, px: 24 },
        { ratio: 1.44, px: 26 },
        { ratio: 1.56, px: 28 },
        { ratio: 1.78, px: 32 },
        { ratio: 2,    px: 36 }
    ];

    const defaults = {
        fontSize: '1',        // ratio (1 = 18 px). Se aplica en px reales, no con zoom.
        fontFamily: '',       // vacío = fuente original del sitio
        theme: 'normal',      // normal | oscuro | grises | daltonismo
        'a11y-underline-links': false,
        'a11y-no-motion': false,
        'a11y-big-cursor': false
    };

    function loadPrefs() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return { ...defaults };
            const p = { ...defaults, ...JSON.parse(raw) };
            // Migra valores antiguos/inválidos (p. ej. "alto-contraste")
            if (THEMES.indexOf(p.theme) === -1) p.theme = 'normal';
            return p;
        } catch (e) {
            return { ...defaults };
        }
    }

    function savePrefs(p) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
        } catch (e) {
            /* localStorage no disponible: se degrada sin persistencia */
        }
    }

    let prefs = loadPrefs();

    /* ---------- Tamaño de texto ---------- */
    const FONT_SIZE_ATTR = 'data-a11y-orig-fs';
    const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'LINK', 'META', 'NOSCRIPT', 'TEMPLATE']);

    // Nunca se toca el propio widget: el panel debe seguir siendo legible
    // sin importar qué tan grande se ponga el texto del sitio.
    function isInsideWidget(el) {
        return !!el.closest('.a11y-toggle, .a11y-panel, .a11y-svg-filters');
    }

    function sizeIndex(ratioStr) {
        const r = parseFloat(ratioStr);
        const i = FONT_SIZES.findIndex(function (s) { return Math.abs(s.ratio - r) < 0.005; });
        return i === -1 ? 1 : i;
    }

    function applyFontSize(ratioStr) {
        const ratio = parseFloat(ratioStr) || 1;
        const els = Array.prototype.filter.call(document.body.querySelectorAll('*'), function (el) {
            return !SKIP_TAGS.has(el.tagName) && !isInsideWidget(el);
        });

        // Tamaño normal: solo se limpian los elementos que ya se habían escalado.
        if (ratio === 1) {
            els.forEach(function (el) {
                if (el.hasAttribute(FONT_SIZE_ATTR)) el.style.removeProperty('font-size');
            });
            return;
        }

        // Pasada 1 (solo lectura): guarda el tamaño original de cada elemento
        // ANTES de modificar ninguno. Si se leyera y escribiera en el mismo
        // recorrido, los hijos heredarían el tamaño ya escalado del padre y
        // se escalarían dos veces (el texto "explotaba").
        const pending = els.map(function (el) {
            let orig = el.getAttribute(FONT_SIZE_ATTR);
            if (orig === null) {
                orig = parseFloat(window.getComputedStyle(el).fontSize);
                el.setAttribute(FONT_SIZE_ATTR, orig);
            }
            return [el, parseFloat(orig)];
        });

        // Pasada 2 (solo escritura)
        pending.forEach(function (item) {
            item[0].style.setProperty('font-size', (item[1] * ratio) + 'px', 'important');
        });
    }

    /* ---------- Fuente y tema ---------- */
    function applyFontFamily(value) {
        HTML.style.setProperty('--a11y-font-family', value || 'inherit');
        HTML.classList.toggle('a11y-font-family', !!value);
    }

    function applyTheme(theme) {
        Array.from(HTML.classList)
            .filter(function (c) { return c.indexOf(THEME_CLASS_PREFIX) === 0; })
            .forEach(function (c) { HTML.classList.remove(c); });
        if (theme && theme !== 'normal') {
            HTML.classList.add(THEME_CLASS_PREFIX + theme);
        }
    }

    function applyAll() {
        applyFontSize(prefs.fontSize);
        applyFontFamily(prefs.fontFamily);
        applyTheme(prefs.theme);
        TOGGLE_CLASSES.forEach(function (cls) {
            HTML.classList.toggle(cls, !!prefs[cls]);
        });
    }

    /* ---------- Sincronizar la interfaz del panel ---------- */
    function syncControls(root) {
        const familySelect = root.querySelector('#a11y-font-family-select');
        if (familySelect) familySelect.value = prefs.fontFamily;

        // Stepper de tamaño
        const idx = sizeIndex(prefs.fontSize);
        const out = root.querySelector('#a11y-font-size-value');
        const dec = root.querySelector('#a11y-font-dec');
        const inc = root.querySelector('#a11y-font-inc');
        if (out) out.textContent = FONT_SIZES[idx].px + ' px' + (idx === 1 ? ' (normal)' : '');
        if (dec) dec.disabled = idx === 0;
        if (inc) inc.disabled = idx === FONT_SIZES.length - 1;

        // Tarjetas de tema
        root.querySelectorAll('[data-a11y-theme]').forEach(function (btn) {
            btn.setAttribute('aria-pressed', String(btn.getAttribute('data-a11y-theme') === prefs.theme));
        });

        // Interruptores
        TOGGLE_CLASSES.forEach(function (cls) {
            const btn = root.querySelector('[data-a11y-toggle="' + cls + '"]');
            if (btn) btn.setAttribute('aria-checked', String(!!prefs[cls]));
        });
    }

    function resetPrefs(root) {
        prefs = { ...defaults };
        savePrefs(prefs);
        applyAll();
        syncControls(root);
    }

    // Garantiza que el botón, el panel y el filtro SVG sean SIEMPRE hijos
    // directos de <body>, para que position:fixed se ancle a la ventana.
    function reanclarAlBody() {
        const toggleBtn = document.getElementById('a11y-toggle-btn');
        const panel = document.getElementById('a11y-panel');
        const svgFiltros = document.querySelector('.a11y-svg-filters');
        [svgFiltros, toggleBtn, panel].forEach(function (el) {
            if (el && el.parentElement !== document.body) {
                document.body.appendChild(el);
            }
        });
    }

    function init() {
        reanclarAlBody();
        applyAll();

        const toggleBtn = document.getElementById('a11y-toggle-btn');
        const panel = document.getElementById('a11y-panel');
        const closeBtn = document.getElementById('a11y-close-btn');
        const resetBtn = document.getElementById('a11y-reset-btn');
        const familySelect = document.getElementById('a11y-font-family-select');
        const decBtn = document.getElementById('a11y-font-dec');
        const incBtn = document.getElementById('a11y-font-inc');

        if (!toggleBtn || !panel) return;

        syncControls(panel);

        function openPanel() {
            panel.classList.add('is-open');
            toggleBtn.setAttribute('aria-expanded', 'true');
            const firstFocusable = panel.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) firstFocusable.focus();
        }

        function closePanel(returnFocus) {
            panel.classList.remove('is-open');
            toggleBtn.setAttribute('aria-expanded', 'false');
            if (returnFocus) toggleBtn.focus();
        }

        toggleBtn.addEventListener('click', function () {
            if (panel.classList.contains('is-open')) { closePanel(true); } else { openPanel(); }
        });

        if (closeBtn) closeBtn.addEventListener('click', function () { closePanel(true); });

        panel.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closePanel(true);
        });

        document.addEventListener('click', function (e) {
            if (!panel.classList.contains('is-open')) return;
            if (panel.contains(e.target) || toggleBtn.contains(e.target)) return;
            closePanel(false);
        });

        // Tamaño de texto: botones A− / A+
        function stepSize(delta) {
            const next = Math.min(FONT_SIZES.length - 1, Math.max(0, sizeIndex(prefs.fontSize) + delta));
            prefs.fontSize = String(FONT_SIZES[next].ratio);
            savePrefs(prefs);
            applyFontSize(prefs.fontSize);
            syncControls(panel);
        }
        if (decBtn) decBtn.addEventListener('click', function () { stepSize(-1); });
        if (incBtn) incBtn.addEventListener('click', function () { stepSize(1); });

        // Tipo de fuente
        if (familySelect) {
            familySelect.addEventListener('change', function () {
                prefs.fontFamily = familySelect.value;
                savePrefs(prefs);
                applyFontFamily(prefs.fontFamily);
            });
        }

        // Tema visual (tarjetas)
        panel.querySelectorAll('[data-a11y-theme]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                prefs.theme = btn.getAttribute('data-a11y-theme');
                savePrefs(prefs);
                applyTheme(prefs.theme);
                syncControls(panel);
            });
        });

        // Interruptores
        panel.querySelectorAll('[data-a11y-toggle]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const cls = btn.getAttribute('data-a11y-toggle');
                prefs[cls] = !prefs[cls];
                savePrefs(prefs);
                HTML.classList.toggle(cls, prefs[cls]);
                syncControls(panel);
            });
        });

        if (resetBtn) resetBtn.addEventListener('click', function () { resetPrefs(panel); });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();