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

// Resaltar enlace activo en navegación según sección visible
const sections = Array.from(document.querySelectorAll('main section'));
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

// Botón "Volver arriba"
const backToTop = document.querySelector('.back-to-top');
if (backToTop) {
  backToTop.addEventListener('click', (e) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}
