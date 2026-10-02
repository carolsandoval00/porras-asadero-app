/* Tooltips flotantes para .mc-nav-row (tiene overflow-x:auto y recortaría el tooltip CSS).
   Mismo enfoque que el script de .pm-nav en Pedidos. */
(function () {
  var bubble = null;
  function show(el) {
    var text = el.getAttribute('data-tooltip');
    if (!text) return;
    hide();
    bubble = document.createElement('div');
    bubble.className = 'js-tooltip-bubble';
    bubble.textContent = text;
    document.body.appendChild(bubble);
    var r = el.getBoundingClientRect(), b = bubble.getBoundingClientRect();
    var left = Math.max(8, Math.min(r.left + r.width / 2 - b.width / 2, window.innerWidth - b.width - 8));
    var up = r.top - b.height - 10, abajo = up < 8;
    bubble.classList.toggle('abajo', abajo);
    bubble.style.left = left + 'px';
    bubble.style.top = (abajo ? r.bottom + 10 : up) + 'px';
    requestAnimationFrame(function () { if (bubble) bubble.classList.add('show'); });
  }
  function hide() { if (bubble) { bubble.remove(); bubble = null; } }
  document.querySelectorAll('.mc-nav-row [data-tooltip]').forEach(function (el) {
    el.addEventListener('mouseenter', function () { show(el); });
    el.addEventListener('mouseleave', hide);
    el.addEventListener('focus', function () { show(el); });
    el.addEventListener('blur', hide);
  });
  window.addEventListener('scroll', hide, true);
})();