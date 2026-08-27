/* =====================================================
   ACCESIBILIDAD - Porras Asadero
   Lógica del widget: selects de tamaño/fuente, temas y
   toggles simples, con persistencia en localStorage.
   ===================================================== */
(function () {
    'use strict';

    const STORAGE_KEY = 'porrasA11yPrefs';
    const HTML = document.documentElement;

    const TOGGLE_CLASSES = ['a11y-underline-links', 'a11y-no-motion', 'a11y-big-cursor'];
    const THEME_CLASS_PREFIX = 'a11y-theme-';

    const defaults = {
        fontSize: '1',         // 1 = 18px (normal), 1.11 = 20px, etc. Se aplica en px reales, no zoom.
        fontFamily: '',       // vacío = fuente original del sitio
        theme: 'normal',      // normal | oscuro | alto-contraste | grises | daltonismo
        'a11y-underline-links': false,
        'a11y-no-motion': false,
        'a11y-big-cursor': false
    };

    function loadPrefs() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return { ...defaults };
            return { ...defaults, ...JSON.parse(raw) };
        } catch (e) {
            return { ...defaults };
        }
    }

    function savePrefs(prefs) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
        } catch (e) {
            /* localStorage no disponible: se degrada sin persistencia */
        }
    }

    let prefs = loadPrefs();

    const FONT_SIZE_ATTR = 'data-a11y-orig-fs';
    // Selector de "raíz de exclusión": nunca tocar el propio widget,
    // para que el panel siga siendo legible y alcanzable sin importar
    // qué tan grande se ponga el texto del resto del sitio.
    function isInsideWidget(el) {
        return !!el.closest('.a11y-toggle, .a11y-panel, .a11y-svg-filters');
    }

    function applyFontSize(ratioStr) {
        const ratio = parseFloat(ratioStr) || 1;
        const all = document.body.querySelectorAll('*');

        all.forEach(function (el) {
            if (isInsideWidget(el)) return;

            // La primera vez que se toca un elemento, se guarda su
            // tamaño real (en px) para poder escalarlo siempre desde
            // ahí y no desde un valor ya modificado (eso es lo que
            // causaba que el texto "explotara" con los porcentajes).
            if (!el.hasAttribute(FONT_SIZE_ATTR)) {
                const originalPx = parseFloat(window.getComputedStyle(el).fontSize);
                el.setAttribute(FONT_SIZE_ATTR, originalPx);
            }

            if (ratio === 1) {
                el.style.removeProperty('font-size');
            } else {
                const originalPx = parseFloat(el.getAttribute(FONT_SIZE_ATTR));
                el.style.setProperty('font-size', (originalPx * ratio) + 'px', 'important');
            }
        });
    }

    function applyFontFamily(value) {
        HTML.style.setProperty('--a11y-font-family', value || 'inherit');
        HTML.classList.toggle('a11y-font-family', !!value);
    }

    function applyTheme(theme) {
        // Quita cualquier clase de tema anterior
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

    function syncControls(root) {
        const sizeSelect = root.querySelector('#a11y-font-size-select');
        const familySelect = root.querySelector('#a11y-font-family-select');
        const themeSelect = root.querySelector('#a11y-theme-select');
        if (sizeSelect) sizeSelect.value = prefs.fontSize;
        if (familySelect) familySelect.value = prefs.fontFamily;
        if (themeSelect) themeSelect.value = prefs.theme;

        TOGGLE_CLASSES.forEach(function (cls) {
            const btn = root.querySelector('[data-a11y-toggle="' + cls + '"]');
            if (btn) btn.setAttribute('aria-pressed', String(!!prefs[cls]));
        });
    }

    function resetPrefs(root) {
        prefs = { ...defaults };
        savePrefs(prefs);
        applyAll();
        syncControls(root);
    }

    function init() {
        applyAll(); // Aplicar antes de pintar el panel, para evitar parpadeos

        const toggleBtn = document.getElementById('a11y-toggle-btn');
        const panel = document.getElementById('a11y-panel');
        const closeBtn = document.getElementById('a11y-close-btn');
        const resetBtn = document.getElementById('a11y-reset-btn');
        const sizeSelect = document.getElementById('a11y-font-size-select');
        const familySelect = document.getElementById('a11y-font-family-select');
        const themeSelect = document.getElementById('a11y-theme-select');

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
            const isOpen = panel.classList.contains('is-open');
            if (isOpen) { closePanel(true); } else { openPanel(); }
        });

        if (closeBtn) {
            closeBtn.addEventListener('click', function () { closePanel(true); });
        }

        panel.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closePanel(true);
        });

        document.addEventListener('click', function (e) {
            if (!panel.classList.contains('is-open')) return;
            if (panel.contains(e.target) || toggleBtn.contains(e.target)) return;
            closePanel(false);
        });

        // Tamaño de texto (desplegable numérico, como en Word)
        if (sizeSelect) {
            sizeSelect.addEventListener('change', function () {
                prefs.fontSize = sizeSelect.value;
                savePrefs(prefs);
                applyFontSize(prefs.fontSize);
            });
        }

        // Tipo de fuente (desplegable)
        if (familySelect) {
            familySelect.addEventListener('change', function () {
                prefs.fontFamily = familySelect.value;
                savePrefs(prefs);
                applyFontFamily(prefs.fontFamily);
            });
        }

        // Tema visual (oscuro / alto contraste / daltonismo / grises)
        if (themeSelect) {
            themeSelect.addEventListener('change', function () {
                prefs.theme = themeSelect.value;
                savePrefs(prefs);
                applyTheme(prefs.theme);
            });
        }

        // Botones de alternancia simples
        panel.querySelectorAll('[data-a11y-toggle]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const cls = btn.getAttribute('data-a11y-toggle');
                prefs[cls] = !prefs[cls];
                savePrefs(prefs);
                HTML.classList.toggle(cls, prefs[cls]);
                syncControls(panel);
            });
        });

        if (resetBtn) {
            resetBtn.addEventListener('click', function () { resetPrefs(panel); });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();