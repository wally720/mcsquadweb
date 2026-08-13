# MCSquad — mcsquad.cc

Sitio web de **MCSquad**, *una comunidad de gamers para gamers*. Más de cuatro años
encima: nació de tres personas que se conocieron trabajando en una carnicería in-game, y
de ahí salieron una docena larga de servidores de Minecraft y de Rust, además de un
launcher propio.

La web tiene un solo trabajo: que quien llegue acabe en el Discord. Todo lo demás es
secundario.

> **Tono del copy.** Se escribe en presente y desde una comunidad que está activa. Nada de
> "estamos volviendo", "la comunidad está dormida" ni frases que den a entender que esto
> estuvo muerto. La historia se cuenta con orgullo, no como despedida.

👉 **Discord:** https://discord.com/invite/rGk6Q2dsDN

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
| `onepage.js` | Scroll-reveal, nav activa, menú móvil y el visor de la galería |
| `tools/galeria.py` | Arma la galería: convierte las capturas y escribe su bloque en `index.html` |
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

**El HTML de la galería no se edita a mano.** El bloque entre los marcadores
`<!-- GALERIA:INICIO -->` y `<!-- GALERIA:FIN -->` de `index.html` lo escribe
`tools/galeria.py`. Si lo tocas a mano, la próxima corrida se lo lleva por delante.

```
1. Tiras las capturas tal como salen del juego en  img/galeria/originales/
2. python3 tools/galeria.py
3. Completas título, servidor, año, categorías y alt en  img/galeria/fotos.txt
4. python3 tools/galeria.py
```

La primera corrida convierte cada captura a dos WebP y te agrega una línea en blanco por
foto nueva en `fotos.txt`. La segunda reescribe el bloque. Correrlo de nuevo sin cambios no
hace nada; `--check` dice qué haría sin escribir.

El script decide el tamaño de cada foto en el mosaico y arma los chips de filtro con los
años y los servidores que encuentre. Es la parte tediosa y fácil de errar a mano.

Una línea de `fotos.txt` completa:

```
2023-puerto | El puerto de noche | Canitas Wipe | 2023 | CanitasWipe | Muelles y edificios iluminados sobre el agua, de noche
```

**El campo de categorías es el id del servidor**, y de ahí salen los chips del filtro, tal
cual lo escribas. La columna `servidor` es el nombre largo que se ve en la etiqueta de la
foto y en el visor; la categoría es el nombre corto por el que se filtra. Se puede poner
más de uno separados por espacio, si una captura pertenece a dos.

Los filtros son dos y se combinan: **año** y **servidor**. Cada grupo aparece solo si hay
más de una opción, y ninguno se escribe a mano.

La galería no crece hacia abajo: crece hacia el costado. En pantalla grande son páginas de
mosaico que se pasan con las flechas o los puntitos; en el celular es una tira de dos filas
que se arrastra con el dedo. Con veinte capturas o con doscientas, la sección mide lo mismo.

El orden del archivo es el orden de la galería, pero **invertido**: la última línea es la
primera foto, para que lo nuevo quede adelante. Para mover una foto, mueves su línea. Las
líneas sin título se ignoran, así que una captura a medio documentar no llega al sitio por
accidente. Sin ninguna captura completa se publica el cofre vacío, que es un estado válido
de la sección.

**Dos tamaños por foto, y de eso se encarga el script:** una miniatura de 640 px (60–90 KB)
que es lo que carga la página, y una de 1920 px (200–300 KB) que solo se descarga al abrir
el visor. Sin esto, doce capturas PNG del juego son 30 MB y en datos móviles la sección no
abre.

**El alt no es opcional.** Describe lo que se ve, no lo que es: *«Base de piedra con torre
iluminada sobre un lago, de noche»*, no *«captura1»*.

Lo único que hay que instalar es `cwebp`, del paquete `webp`:

| Sistema | Cómo |
|---|---|
| Debian/Ubuntu | `sudo apt install webp` |
| macOS | `brew install webp` |
| Windows | [zip oficial de Google](https://developers.google.com/speed/webp/download) |

Los originales de `img/galeria/originales/` no hace falta subirlos al repo: pesan y no se
publican. Lo que sirve el sitio son los WebP de `img/galeria/`.

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
