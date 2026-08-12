# MCSquad — mcsquad.cc

Sitio web de **MCSquad**, una comunidad gamer con más de cuatro años encima. Nació de
tres personas que se conocieron trabajando en una carnicería in-game, y de ahí salieron
una docena larga de servidores de Minecraft y de Rust.

La web es una **convocatoria**: su único trabajo es que la gente que estuvo vuelva a caer
al Discord. Todo lo demás es secundario.

👉 **Discord:** https://discord.com/invite/8uvAN9CTH9

## Cómo verla en local

No hay build ni dependencias. HTML, CSS y JS a secas.

```bash
python3 -m http.server 8000
```

Y abrir http://localhost:8000

> Ábrela por HTTP, no con doble clic en `index.html`. Con `file://` las rutas relativas y
> el `IntersectionObserver` no se comportan igual.

## Estructura

| Archivo | Qué es |
|---|---|
| `index.html` | La web. Una sola página, siete secciones |
| `onepage.css` | Estilos. Los fondos de sección y las animaciones van al final |
| `onepage.js` | Scroll-reveal, nav activa y menú móvil |
| `tele.html` | Teleprompter. Herramienta aparte, enlazada desde *Herramientas* |
| `micalc.html` | Calculadora de trading. **Huérfana a propósito**, no se enlaza desde ningún lado |
| `img/` | Fondos de sección, tarjeta social y galería |
| `CNAME` | Dominio de GitHub Pages |

## Las animaciones

Van ligadas al scroll con CSS (`animation-timeline`), sin librerías. Corren en el
compositor, fuera del hilo principal, que es lo que las mantiene fluidas en celular.

Tres reglas si las tocas:

1. **Anima solo `transform` y `opacity`.** Cualquier otra propiedad fuerza repintados y
   tira los 60 fps justo en móvil.
2. **Todo dentro de `@supports (animation-timeline: view())`.** Donde no exista, el
   `IntersectionObserver` de `onepage.js` sigue dando el reveal básico.
3. **Respeta `prefers-reduced-motion`.** El bloque ya está escrito; el movimiento intenso
   marea a bastante gente y esto no es opcional.

Cuidado con los rangos (`animation-range`): si un elemento está al final de la página y el
scroll se acaba antes de que complete su rango, se queda invisible para siempre. Después de
cambiarlos, baja hasta el fondo del todo y comprueba que no quedó nada translúcido.

## Cómo añadir un proyecto a la línea de tiempo

En `<section id="proyectos">`, dentro del grupo que le corresponda (`.tl-group`), añade un
`<li>` más:

```html
<li class="tl-item">
  <h4>Nombre del servidor</h4>
  <p>Una línea de qué era.</p>
</li>
```

El eje, los puntos y el dibujado salen solos. Para un grupo nuevo, copia un `.tl-group`
entero con su `<h3 class="tl-title">`.

Solo un proyecto debería llevar `tl-group--live` y `tl-item--live` a la vez: es la marca de
"EN LÍNEA" y pierde sentido si la tienen varios.

## Cómo completar las tarjetas del squad

Cada miembro tiene su color (`.member--wally`, `--markuz`, `--jonks`, `--choko`) definido en
`onepage.css`, y cuatro campos dentro de `<dl class="member-facts">`.

> ⚠️ **"A qué se dedica" y "Qué piensa hacer" son de relleno**, escritos en broma hasta que
> cada uno ponga el suyo. Se cambian editando el `<dd>` que toca.

### Las cabezas de skin

Van en dos capas, para que se actualicen solas sin quedar a merced de un servicio ajeno:

1. El `src` apunta a **`mc-heads.net` en vivo**, así que la web muestra el skin que cada uno
   tenga puesto en ese momento. Si alguien se cambia el skin, la página lo refleja sola.
2. El `onerror` cae a un **PNG guardado en `img/squad/`** si el servicio no responde.

| Miembro | Identificador que se pide |
|---|---|
| Wally | `wallyenteras` |
| Choko | UUID `714b5f43-d02b-4139-9bff-1bccb74f44d7` |
| Markuz | `Markuz_Diaz` |
| Jonks | `eljonks` |

Choko va por UUID porque el usuario que se probó primero (`chokolv3`) no existía. **Los
UUID son permanentes; los nombres de usuario se pueden cambiar.** Si alguien se cambia el
nombre, su cabeza dejará de cargar y se quedará en el respaldo: la solución es pasar esa
tarjeta a UUID.

Para refrescar un respaldo local:

```bash
curl -o img/squad/wally.png https://mc-heads.net/avatar/wallyenteras/128
```

El CSS les aplica `image-rendering: pixelated`, que es lo que evita que una cabeza de 8×8
salga borrosa al ampliarla.

> ⚠️ **Cuidado al verificar un usuario.** Estos servicios devuelven un skin por defecto, sin
> dar error, cuando el nombre no existe. Y hay **más de un** skin por defecto: comparar solo
> contra Steve no basta y da falsos positivos. Compara contra el resultado de un nombre
> inventado **y** el de un nombre inválido como `0`.

**Si cambias un color:** los `--c` (color vivo) se usan en texto pequeño sobre el fondo
`--c-deep`. Los tonos medios se quedan en 3,6–4,1:1 y no pasan AA — por eso son claros. Si
tocas uno, mide el contraste antes de subirlo.

## Cómo agregar fotos a la galería

1. Mete las imágenes en `img/galeria/`.
2. En `index.html`, dentro de `<section id="galeria">`, borra el bloque
   `<div class="gallery-empty">` y descomenta el `<div class="grid gallery">` que está justo
   encima.
3. Un `<img>` por foto. El CSS ya las recorta a un grid parejo:

```html
<img src="img/galeria/lo-que-sea.jpg" alt="Descripción de la foto"
     loading="lazy" width="600" height="400" />
```

**Comprime antes de subir.** Las fotos van a datos móviles. Como referencia, los siete
fondos de sección pesan ~500 KB entre todos.

## Deploy

GitHub Pages sirve la rama por defecto. El dominio `mcsquad.cc` se configura con el archivo
`CNAME` más los registros DNS en Cloudflare (A y AAAA al apex, CNAME de `www`), todos en
**DNS only**: con el proxy activado GitHub no puede emitir el certificado. El modo SSL/TLS
tiene que estar en **Full (strict)**; en *Flexible* el sitio entra en bucle de
redirecciones.

## Convenciones

- Sin frameworks y sin build. Si algo necesita una dependencia, probablemente no la necesita.
- **Nada de contenido inventado.** Si no hay fotos, la galería lo dice; no se rellena con
  placeholders. Si no hay testimonios reales, no hay testimonios.
- **Nunca poner claves de API en el código.** Este sitio es estático y público: todo lo que
  esté acá lo puede leer cualquiera, por más que se parta en variables.
- **Este archivo va en UTF-8.** Estuvo guardado en UTF-16 y se veía como basura en GitHub.
