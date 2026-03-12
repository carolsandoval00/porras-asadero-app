function enviarForm(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmit');
    btn.textContent = '✓ Mensaje Enviado';
    btn.style.background = '#2ecc71';
    setTimeout(() => {
        btn.textContent = 'Enviar Mensaje';
        btn.style.background = '';
        e.target.reset();
    }, 3000);
}


const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.style.opacity = '1';
            e.target.style.transform = 'translateY(0)';
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.menu-card, .contacto-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity .5s ease, transform .5s ease';
    observer.observe(el);
});