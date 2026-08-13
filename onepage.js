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

// Volver arriba: el logo y el enlace del pie.
// #top vive en el header, que es position:fixed, asi que el salto nativo del
// navegador no mueve nada (un elemento fijo ya esta "a la vista"). Se lleva a
// mano al inicio del documento.
document.querySelectorAll('a[href="#top"]').forEach((link) => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});

// Visor de la galería: <dialog> nativo mas View Transitions donde las haya.
// Si la galería todavía no tiene capturas, no engancha nada y se va.
(() => {
  const box = document.getElementById('gal-box');
  const todos = Array.from(document.querySelectorAll('.gal-grid--full .gal-slot'));
  if (!box || !todos.length) return;

  const boxImg = document.getElementById('gal-box-img');
  const elTitle = document.getElementById('gal-box-title');
  const elMeta = document.getElementById('gal-box-meta');
  const elCount = document.getElementById('gal-box-count');
  const quieto = window.matchMedia('(prefers-reduced-motion: reduce)');

  // Las que están detrás del "ver más" no cuentan hasta que se despliegan:
  // se recalcula al abrir, para que las flechas no salten a una foto oculta
  let slots = todos;
  let i = 0;

  // Envuelve el cambio en una transición cuando el navegador la tiene.
  // Si no, ejecuta y ya: el visor abre igual, sin el morfeo.
  const conTransicion = (fn) =>
    (document.startViewTransition && !quieto.matches)
      ? document.startViewTransition(fn)
      : (fn(), { finished: Promise.resolve() });

  const pintar = (n) => {
    const slot = slots[n];
    const img = slot.querySelector('img');
    const tip = slot.querySelector('.gal-tip');
    // data-full es la versión grande; si no está, sirve la miniatura
    boxImg.src = img.dataset.full || img.src;
    boxImg.alt = img.alt;
    elTitle.textContent = tip?.querySelector('b')?.textContent ?? '';
    elMeta.textContent = tip?.querySelector('span')?.textContent ?? '';
    elCount.textContent = `${n + 1} / ${slots.length}`;
    i = n;
  };

  const abrir = (slot) => {
    slots = todos.filter((s) => s.offsetParent !== null);
    const n = slots.indexOf(slot);
    const origen = slots[n].querySelector('img');
    origen.style.viewTransitionName = 'gal-hero';
    const vt = conTransicion(() => {
      // Se libera el nombre acá dentro: dos elementos no pueden compartirlo
      origen.style.viewTransitionName = '';
      boxImg.style.viewTransitionName = 'gal-hero';
      pintar(n);
      box.showModal();
    });
    vt.finished.finally(() => { boxImg.style.viewTransitionName = ''; });
  };

  const cerrar = () => {
    const destino = slots[i].querySelector('img');
    boxImg.style.viewTransitionName = 'gal-hero';
    const vt = conTransicion(() => {
      boxImg.style.viewTransitionName = '';
      destino.style.viewTransitionName = 'gal-hero';
      box.close();
    });
    vt.finished.finally(() => { destino.style.viewTransitionName = ''; });
  };

  const mover = (paso) => pintar((i + paso + slots.length) % slots.length);

  todos.forEach((slot) => {
    slot.querySelector('.gal-open')?.addEventListener('click', () => abrir(slot));
  });

  box.querySelector('.gal-close').addEventListener('click', cerrar);
  box.querySelector('.gal-prev').addEventListener('click', () => mover(-1));
  box.querySelector('.gal-next').addEventListener('click', () => mover(1));

  // Escape lo maneja <dialog> solo, pero hay que interceptarlo por la transición
  box.addEventListener('cancel', (e) => { e.preventDefault(); cerrar(); });
  box.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') mover(-1);
    if (e.key === 'ArrowRight') mover(1);
  });
  // Clic en el fondo negro también cierra
  box.addEventListener('click', (e) => { if (e.target === box) cerrar(); });

  // Deslizar en el celular
  let x0 = null;
  box.addEventListener('touchstart', (e) => { x0 = e.changedTouches[0].clientX; }, { passive: true });
  box.addEventListener('touchend', (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 55) mover(dx < 0 ? 1 : -1);
    x0 = null;
  }, { passive: true });
})();

// Filtros de la galería (año y servidor) y paginado horizontal.
// Los dos filtros se combinan: año Y servidor, no uno u otro. Esconder de
// verdad las que no pasan es lo que deja que la rejilla se rearme sola, y de
// paso el visor las saltea, porque descarta las que no están en pantalla.
(() => {
  const gal = document.querySelector('.gal');
  const grid = gal && gal.querySelector('.gal-grid--full');
  if (!grid) return;

  const slots = Array.from(grid.querySelectorAll('.gal-slot'));
  const nada = gal.querySelector('.gal-nada');
  const mandos = gal.querySelector('.gal-turns');
  const antes = gal.querySelector('.gal-turn--prev');
  const luego = gal.querySelector('.gal-turn--next');
  const puntos = gal.querySelector('.gal-dots');

  const elegido = (grupo) =>
    gal.querySelector(`input[name="${grupo}"]:checked`)?.value || '';

  // Cuál de los puntos queda encendido, y si las flechas llegaron al borde.
  // El margen de 8px es para que el redondeo del scroll no deje una flecha
  // viva sin nada adonde ir.
  const marcar = () => {
    const paso = grid.clientWidth;
    if (!paso || !puntos.children.length) return;
    const n = Math.min(puntos.children.length - 1, Math.round(grid.scrollLeft / paso));
    Array.from(puntos.children).forEach((p, k) =>
      p.setAttribute('aria-selected', String(k === n)));
    antes.disabled = grid.scrollLeft < 8;
    luego.disabled = grid.scrollLeft + paso >= grid.scrollWidth - 8;
  };

  // Las páginas no están en el HTML: son cuántas veces entra el ancho visible
  // en el ancho total. Por eso sobreviven a un filtro sin rearmar nada.
  const paginar = () => {
    const paso = grid.clientWidth;
    const total = paso > 0 ? Math.max(1, Math.ceil(grid.scrollWidth / paso)) : 1;
    mandos.hidden = grid.hidden || total < 2;
    if (mandos.hidden) {
      puntos.replaceChildren();
      return;
    }
    if (puntos.children.length !== total) {
      puntos.replaceChildren(...Array.from({ length: total }, (_, n) => {
        const p = document.createElement('button');
        p.type = 'button';
        p.className = 'gal-dot';
        p.setAttribute('role', 'tab');
        p.setAttribute('aria-label', `Página ${n + 1} de ${total}`);
        p.addEventListener('click', () => grid.scrollTo({ left: n * grid.clientWidth }));
        return p;
      }));
    }
    marcar();
  };

  const filtrar = () => {
    const anio = elegido('galf-anio');
    const serv = elegido('galf-serv');
    let quedan = 0;
    slots.forEach((s) => {
      const suyos = (s.dataset.cat || '').split(/\s+/);
      const pasa = (!anio || s.dataset.anio === anio) && (!serv || suyos.includes(serv));
      s.classList.toggle('is-off', !pasa);
      if (pasa) quedan += 1;
    });
    grid.hidden = quedan === 0;
    if (nada) nada.hidden = quedan > 0;
    // Cambiar de filtro devuelve al principio: quedarse en la página 4 de una
    // tira que ahora tiene dos es quedarse mirando el vacío.
    grid.scrollTo({ left: 0, behavior: 'auto' });
    paginar();
  };

  antes.addEventListener('click', () => grid.scrollBy({ left: -grid.clientWidth }));
  luego.addEventListener('click', () => grid.scrollBy({ left: grid.clientWidth }));
  gal.querySelectorAll('.gal-filters input').forEach((f) =>
    f.addEventListener('change', filtrar));

  // Sin throttle a proposito: marcar() son tres lecturas y un atributo, y el
  // navegador ya emite scroll a lo sumo una vez por cuadro.
  grid.addEventListener('scroll', marcar, { passive: true });

  new ResizeObserver(paginar).observe(grid);
  filtrar();
})();
