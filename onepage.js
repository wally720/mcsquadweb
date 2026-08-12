// Año dinámico en el footer
document.getElementById('year').textContent = new Date().getFullYear();

// Scroll reveal con IntersectionObserver (siempre activo y más temprano)
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (e.isIntersecting) {
      e.target.classList.add('visible');
    } else {
      e.target.classList.remove('visible');
    }
  }
}, { threshold: 0.05, rootMargin: '30% 0px 30% 0px' });

document.querySelectorAll('.reveal').forEach(el => io.observe(el));

// La portada se queda fuera: no tiene enlace en la nav y no debe entrar con fade
const sections = Array.from(document.querySelectorAll('main section:not(.hero)'));
const navLinks = Array.from(document.querySelectorAll('.main-nav a'));

const byId = (id) => navLinks.find(a => a.getAttribute('href') === `#${id}`);

const sectionIO = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      // Estado activo en navegación
      navLinks.forEach(a => a.classList.remove('active'));
      const link = byId(entry.target.id);
      if (link) link.classList.add('active');
    }
  });
}, { threshold: 0.45, rootMargin: '10% 0px 10% 0px' });

sections.forEach(s => sectionIO.observe(s));

// Fade de secciones completo (temprano y repetible)
sections.forEach(s => s.classList.add('fade-init'));
const sectionFadeIO = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('fade-in');
    } else {
      entry.target.classList.remove('fade-in');
    }
  });
}, { threshold: 0.08, rootMargin: '25% 0px 25% 0px' });

sections.forEach(s => sectionFadeIO.observe(s));

// Menú móvil: la nav está oculta bajo 820px y se abre con la hamburguesa
const navToggle = document.getElementById('nav-toggle');
const mainNav = document.getElementById('main-nav');

if (navToggle && mainNav) {
  const setNav = (open) => {
    mainNav.dataset.open = String(open);
    navToggle.setAttribute('aria-expanded', String(open));
    navToggle.setAttribute('aria-label', open ? 'Cerrar menú de navegación' : 'Abrir menú de navegación');
  };

  setNav(false);

  navToggle.addEventListener('click', () => {
    setNav(navToggle.getAttribute('aria-expanded') !== 'true');
  });

  // Al elegir un destino, el menú estorba: se cierra
  mainNav.addEventListener('click', (e) => {
    if (e.target.closest('a')) setNav(false);
  });

  // Escape cierra y devuelve el foco al botón
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && navToggle.getAttribute('aria-expanded') === 'true') {
      setNav(false);
      navToggle.focus();
    }
  });

  // Tocar fuera del panel también cierra
  document.addEventListener('click', (e) => {
    if (navToggle.getAttribute('aria-expanded') !== 'true') return;
    if (!mainNav.contains(e.target) && !navToggle.contains(e.target)) setNav(false);
  });

  // Si se pasa a escritorio con el menú abierto, se limpia el estado
  window.matchMedia('(min-width: 821px)').addEventListener('change', (e) => {
    if (e.matches) setNav(false);
  });
}

// El Discord flotante solo aparece cuando la portada ya no se ve: alli arriba
// estaria duplicando el boton grande que la portada ya tiene.
const floatBtn = document.querySelector('.discord-float');
const hero = document.querySelector('.hero');
if (floatBtn && hero) {
  new IntersectionObserver(([entry]) => {
    floatBtn.classList.toggle('is-visible', !entry.isIntersecting);
  }, { threshold: 0.15 }).observe(hero);
} else if (floatBtn) {
  // Sin portada que observar, mejor visible que perdido
  floatBtn.classList.add('is-visible');
}

// Botón "Volver arriba"
const backToTop = document.querySelector('.back-to-top');
if (backToTop) {
  backToTop.addEventListener('click', (e) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}
