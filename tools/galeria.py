#!/usr/bin/env python3
"""Arma la galería del sitio a partir de una carpeta de capturas.

El flujo es:

  1. Pones las capturas tal como salen del juego en  img/galeria/originales/
  2. Ejecutas  python3 tools/galeria.py
     - convierte cada una a dos WebP (miniatura de 640px y grande de 1920px)
     - agrega a img/galeria/fotos.txt una línea por cada captura nueva,
       con los datos en blanco para que los completes
  3. Completas título, servidor, año, categorías y alt en fotos.txt
  4. Lo vuelves a ejecutar: reescribe el bloque de la galería en index.html

Ejecutarlo de nuevo sin cambios no hace nada: solo convierte lo que falta o lo
que cambió. Las líneas de fotos.txt sin título no salen al sitio, así que una
captura a medio documentar nunca llega a publicarse.

  --check   dice qué haría, sin tocar ningún archivo
  --destino otro HTML (por defecto index.html)

Necesita cwebp, del paquete `webp`:
  Debian/Ubuntu   sudo apt install webp
  macOS           brew install webp
  Windows         https://developers.google.com/speed/webp/download
"""

import argparse
import html
import os
import shutil
import struct
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ORIGINALES = "img/galeria/originales"
SALIDA = "img/galeria"
LISTA = "img/galeria/fotos.txt"
DESTINO = "index.html"

INICIO = "<!-- GALERIA:INICIO (lo genera tools/galeria.py, no editar a mano) -->"
FIN = "<!-- GALERIA:FIN -->"

ANCHO_MINI, CALIDAD_MINI = 640, 78
ANCHO_FULL, CALIDAD_FULL = 1920, 80

# La rejilla se lee por columnas y todo se mide en unidades de 1 columna x
# 1 fila. La galería no crece hacia abajo: crece hacia el costado.
UNIDADES = {"norm": 1, "wide": 2, "tall": 2, "big": 4}
COLUMNAS = 4

# Con menos de esto no vale la pena la barra de filtros: se filtra con la vista.
MINIMO_PARA_FILTRAR = 6

# Cuántos slots vacíos tiene el cofre cuando todavía no hay ninguna captura.
HUECOS_VACIA = 8

# Cada bloque suma 8 unidades, o sea 2 columnas exactas de 4 filas. Por eso el
# mosaico tesela sin agujeros por dentro mientras no se filtre nada.
BLOQUES = [
    ("big", "norm", "norm", "wide"),
    ("tall", "norm", "norm", "norm", "norm", "wide"),
    ("wide", "wide", "wide", "norm", "norm"),
]


# --------------------------------------------------------------- utilidades

class Aviso(Exception):
    pass


def medidas(ruta):
    """Ancho y alto de un PNG, JPEG o WebP, leyendo solo la cabecera."""
    with open(ruta, "rb") as f:
        cab = f.read(32)

        if cab[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", cab[16:24])

        if cab[:4] == b"RIFF" and cab[8:12] == b"WEBP":
            tipo = cab[12:16]
            if tipo == b"VP8 ":                       # con pérdida
                return (struct.unpack("<H", cab[26:28])[0] & 0x3FFF,
                        struct.unpack("<H", cab[28:30])[0] & 0x3FFF)
            if tipo == b"VP8L":                       # sin pérdida
                b = struct.unpack("<I", cab[21:25])[0]
                return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
            if tipo == b"VP8X":                       # extendido
                w = cab[24] | cab[25] << 8 | cab[26] << 16
                h = cab[27] | cab[28] << 8 | cab[29] << 16
                return w + 1, h + 1
            raise Aviso(f"WebP de un tipo que no sé leer: {ruta}")

        if cab[:2] == b"\xff\xd8":                    # JPEG: buscar el SOF
            f.seek(2)
            while True:
                marca = f.read(2)
                if len(marca) < 2 or marca[0] != 0xFF:
                    raise Aviso(f"JPEG ilegible: {ruta}")
                largo = struct.unpack(">H", f.read(2))[0]
                if 0xC0 <= marca[1] <= 0xCF and marca[1] not in (0xC4, 0xC8, 0xCC):
                    datos = f.read(5)
                    return struct.unpack(">H", datos[3:5])[0], struct.unpack(">H", datos[1:3])[0]
                f.seek(largo - 2, 1)

    raise Aviso(f"No reconozco el formato de {ruta}")


def convertir(origen, destino, ancho, calidad, check):
    """Llama a cwebp. Devuelve 'saltada' si el destino ya está al día, 'ok' si
    la convirtió, o el motivo del fallo. No revienta: una captura rota no puede
    llevarse por delante a las demás."""
    if os.path.exists(destino) and os.path.getmtime(destino) >= os.path.getmtime(origen):
        return "saltada", ""
    cmd = ["cwebp", "-quiet", "-q", str(calidad), "-resize", str(ancho), "0", origen, "-o", destino]
    if check:
        print("      " + " ".join(cmd))
        return "ok", ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        return "fallo", str(e)
    if r.returncode != 0:
        # cwebp puede dejar un destino a medio escribir: si queda, la próxima
        # corrida lo daría por bueno y el sitio serviría un archivo corrupto.
        if os.path.exists(destino):
            os.remove(destino)
        motivo = (r.stderr or r.stdout or "").strip().splitlines()
        return "fallo", (motivo[-1] if motivo else f"cwebp terminó con código {r.returncode}")
    return "ok", ""


def asignar_tamanos(cuantas):
    """Reparte big/wide/tall/norm siguiendo los bloques, en orden."""
    tamanos, i = [], 0
    while len(tamanos) < cuantas:
        bloque = BLOQUES[i % len(BLOQUES)]
        if len(tamanos) + len(bloque) > cuantas:
            break                      # la cola no llega a completar el bloque
        tamanos += list(bloque)
        i += 1
    tamanos += ["norm"] * (cuantas - len(tamanos))   # la cola va toda normal
    return tamanos


def clave(texto):
    """Un token de categoría convertido en algo que sirva de id de HTML."""
    limpio = "".join(c if c.isalnum() else "-" for c in texto.lower())
    return limpio.strip("-") or "x"


# ------------------------------------------------------------------- lista

CABECERA = (
    "# Una línea por captura. Los campos van separados por |\n"
    "#\n"
    "#   archivo | título | servidor | año | categorías | alt\n"
    "#\n"
    "# archivo      nombre del original sin extensión, tal como está en originales/\n"
    "# categorías   el id interno del servidor (MildcraftV2, PokecraftV2...).\n"
    "#              De acá salen los chips de filtro, tal cual los escribas.\n"
    "#              Se puede poner más de uno, separados por espacio.\n"
    "# alt          qué se ve en la captura, para quien no la puede ver.\n"
    "#              Describe la escena, no el archivo.\n"
    "#\n"
    "# Las líneas sin título se ignoran: la captura no sale al sitio hasta que\n"
    "# la completes. El orden de este archivo es el orden de la galería.\n"
)

CAMPOS = ("archivo", "titulo", "servidor", "anio", "categorias", "alt")


def leer_lista(ruta):
    entradas = []
    if not os.path.exists(ruta):
        return entradas
    for n, linea in enumerate(open(ruta, encoding="utf-8"), 1):
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        partes = [p.strip() for p in linea.split("|")]
        partes += [""] * (len(CAMPOS) - len(partes))
        entradas.append(dict(zip(CAMPOS, partes[:len(CAMPOS)]), linea=n))
    return entradas


def escribir_lista(ruta, entradas, nuevas):
    existente = open(ruta, encoding="utf-8").read() if os.path.exists(ruta) else CABECERA
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(existente.rstrip("\n") + "\n")
        for stem in nuevas:
            f.write(f"{stem} |  |  |  |  | \n")


# -------------------------------------------------------------------- html

def figura(e, tamano, indent):
    src = f"{SALIDA}/{e['archivo']}-thumb.webp"
    full = f"{SALIDA}/{e['archivo']}.webp"
    try:
        w, h = medidas(os.path.join(RAIZ, src))
    except (OSError, Aviso):
        w, h = 640, 360
    titulo = html.escape(e["titulo"])
    meta = " · ".join(x for x in (e["servidor"], e["anio"]) if x)
    talla = f' data-size="{tamano}"' if tamano != "norm" else ""
    anio = f' data-anio="{html.escape(e["anio"])}"' if e["anio"] else ""
    i = " " * indent
    return (
        f'{i}<figure class="gal-slot" data-cat="{html.escape(e["categorias"])}"{anio}{talla}>\n'
        f'{i}  <img src="{src}" data-full="{full}"\n'
        f'{i}       alt="{html.escape(e["alt"])}"\n'
        f'{i}       loading="lazy" width="{w}" height="{h}" />\n'
        f'{i}  <figcaption class="gal-tip"><b>{titulo}</b><span>{html.escape(meta)}</span></figcaption>\n'
        f'{i}  <button class="gal-open" type="button" aria-label="Ampliar: {titulo}"></button>\n'
        f'{i}</figure>\n'
    )


def servidores_presentes(entradas):
    """Los servidores salen del campo 'categorías', que es donde vive el id
    interno de cada servidor. Se listan en el orden en que aparecen."""
    vistos = []
    for e in entradas:
        for token in e["categorias"].split():
            if token not in vistos:
                vistos.append(token)
    return vistos


def anios_presentes(entradas):
    """Los años, del más nuevo al más viejo."""
    return sorted({e["anio"] for e in entradas if e["anio"]}, reverse=True)


def grupo_filtros(nombre, etiqueta, valores, indent):
    """Un grupo de chips. Los valores son los que van al data- de la figura;
    'todo' es el que viene marcado."""
    i = " " * indent
    chips = [f'{i}    <input type="radio" name="{nombre}" id="{nombre}-todo" '
             f'value="" checked /><label for="{nombre}-todo">Todo</label>\n']
    for v in valores:
        vid = f"{nombre}-{clave(v)}"
        chips.append(f'{i}    <input type="radio" name="{nombre}" id="{vid}" '
                     f'value="{html.escape(v, quote=True)}" />'
                     f'<label for="{vid}">{html.escape(v)}</label>\n')
    return (
        f'{i}  <div class="gal-bar">\n'
        f'{i}    <span class="gal-bar-label">{etiqueta}</span>\n'
        f'{i}    <fieldset class="gal-filters">\n'
        f'{i}      <legend class="sr-only">Filtrar capturas por {etiqueta.lower()}</legend>\n'
        + "".join(f"  {c}" for c in chips) +
        f'{i}    </fieldset>\n'
        f'{i}  </div>\n'
    )


def barra_filtros(entradas, indent):
    """Dos grupos de chips, año y servidor, sacados de lo que hay en la lista.
    Cada grupo sale por su cuenta: con un solo año no hay nada que elegir."""
    if len(entradas) < MINIMO_PARA_FILTRAR:
        return ""
    anios = anios_presentes(entradas)
    servidores = servidores_presentes(entradas)
    grupos = ""
    if len(anios) > 1:
        grupos += grupo_filtros("galf-anio", "Año", anios, indent)
    if len(servidores) > 1:
        grupos += grupo_filtros("galf-serv", "Servidor", servidores, indent)
    if not grupos:
        return ""
    i = " " * indent
    return f'{i}<div class="gal-bars">\n{grupos}{i}</div>\n\n'


def cofre_vacio(indent):
    """Lo que se ve mientras no hay ninguna captura subida. Los huecos son
    parte del diseño: el cofre se ve vacío, no roto."""
    i = " " * indent
    mitad = HUECOS_VACIA // 2
    hueco = f'{i}  <div class="gal-hole"></div>\n'
    return (
        f'{i}<div class="gal-grid gal-grid--empty">\n'
        + hueco * mitad +
        f'{i}  <div class="gal-call">\n'
        f'{i}    <h4>El cofre está vacío</h4>\n'
        f'{i}    <p>\n'
        f'{i}      Todavía no hay nada subido. ¿Tienes capturas de cualquiera de nuestros\n'
        f'{i}      servidores? Mándalas al Discord y las montamos aquí.\n'
        f'{i}    </p>\n'
        f'{i}    <a href="https://discord.com/invite/rGk6Q2dsDN" target="_blank" rel="noopener">'
        f'Mandar capturas al Discord →</a>\n'
        f'{i}  </div>\n'
        + hueco * mitad +
        f'{i}</div>\n'
    )


def construir_html(entradas, indent=12):
    """Devuelve la galería entera: filtros y la tira de capturas.
    Sin entradas devuelve el cofre vacío, que es un estado válido del sitio.

    Las capturas van de la más nueva a la más vieja, al revés de fotos.txt,
    que se lee de arriba hacia abajo como un diario."""
    if not entradas:
        return cofre_vacio(indent), 0

    entradas = list(reversed(entradas))
    tamanos = asignar_tamanos(len(entradas))
    i = " " * indent
    salida = [
        barra_filtros(entradas, indent),
        f'{i}<div class="gal-strip">\n'
        f'{i}  <div class="gal-grid gal-grid--full" role="group" '
        f'aria-label="Capturas de la comunidad">\n'
    ]

    for e, t in zip(entradas, tamanos):
        salida.append(figura(e, t, indent=indent + 4))

    salida.append(
        f'{i}  </div>\n'
        f'{i}  <p class="gal-nada" hidden>No hay capturas con ese filtro. '
        f'Prueba con otro año o servidor.</p>\n'
        f'{i}  <div class="gal-turns" hidden>\n'
        f'{i}    <button class="gal-turn gal-turn--prev" type="button" '
        f'aria-label="Capturas anteriores"></button>\n'
        f'{i}    <div class="gal-dots" role="tablist" aria-label="Páginas de la galería"></div>\n'
        f'{i}    <button class="gal-turn gal-turn--next" type="button" '
        f'aria-label="Capturas siguientes"></button>\n'
        f'{i}  </div>\n'
        f'{i}</div>\n'
    )
    return "".join(salida), len(entradas)


def splicear(ruta, bloque, check):
    texto = open(ruta, encoding="utf-8").read()
    if INICIO not in texto or FIN not in texto:
        raise Aviso(
            f"{os.path.relpath(ruta, RAIZ)} no tiene los marcadores de la galería.\n"
            f"  Pon estas dos líneas donde va la rejilla, y el bloque de adentro lo escribe este script:\n"
            f"    {INICIO}\n"
            f"    {FIN}"
        )
    a = texto.index(INICIO) + len(INICIO)
    b = texto.index(FIN)
    nuevo = texto[:a] + "\n" + bloque + " " * 10 + texto[b:]
    if nuevo == texto:
        return False
    if not check:
        open(ruta, "w", encoding="utf-8").write(nuevo)
    return True


# -------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Arma la galería a partir de img/galeria/originales/")
    ap.add_argument("--check", action="store_true", help="dice qué haría, sin escribir nada")
    ap.add_argument("--destino", default=DESTINO, help=f"HTML a reescribir (por defecto {DESTINO})")
    args = ap.parse_args()

    orig_dir = os.path.join(RAIZ, ORIGINALES)
    lista = os.path.join(RAIZ, LISTA)
    destino = os.path.join(RAIZ, args.destino)

    if not os.path.isdir(orig_dir):
        os.makedirs(orig_dir, exist_ok=True)
        print(f"Creé {ORIGINALES}/. Pon ahí las capturas y vuelve a ejecutarme.")

    stems = sorted(
        os.path.splitext(f)[0] for f in os.listdir(orig_dir)
        if os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".webp")
    ) if os.path.isdir(orig_dir) else []
    if not stems:
        # Se sigue igual: hay que dejar el cofre vacío publicado, no lo de antes
        print(f"No hay capturas en {ORIGINALES}/.")

    entradas = leer_lista(lista)
    conocidas = {e["archivo"] for e in entradas}

    # 1. Capturas nuevas -> se agregan a la lista en blanco
    nuevas = [s for s in stems if s not in conocidas]
    if nuevas:
        if not args.check:
            escribir_lista(lista, entradas, nuevas)
        print(f"{len(nuevas)} captura(s) nueva(s) en {LISTA}. Completa los datos:")
        for s in nuevas:
            print(f"      {s}")

    # 2. Líneas cuyo original ya no está
    huerfanas = [e["archivo"] for e in entradas if e["archivo"] not in stems]
    for h in huerfanas:
        print(f"AVISO  {LISTA} nombra '{h}' pero no hay ningún original con ese nombre.")

    # 3. Convertir. Sin capturas no hace falta cwebp: se sigue de largo.
    if stems and not shutil.which("cwebp") and not args.check:
        print("\nFalta cwebp. Instálalo y vuelve a ejecutarme:")
        print("      Debian/Ubuntu  sudo apt install webp")
        print("      macOS          brew install webp")
        print("      Windows        https://developers.google.com/speed/webp/download")
        return 1

    convertidas, fallidas = 0, {}
    for f in sorted(os.listdir(orig_dir)):
        stem, ext = os.path.splitext(f)
        if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        origen = os.path.join(orig_dir, f)
        for nombre, ancho, calidad in ((f"{stem}-thumb.webp", ANCHO_MINI, CALIDAD_MINI),
                                       (f"{stem}.webp", ANCHO_FULL, CALIDAD_FULL)):
            estado, motivo = convertir(origen, os.path.join(RAIZ, SALIDA, nombre), ancho, calidad, args.check)
            if estado == "ok":
                convertidas += 1
            elif estado == "fallo":
                fallidas.setdefault(stem, motivo)
    print(f"{convertidas} archivo(s) convertido(s)." if convertidas else "Nada que convertir.")

    if fallidas:
        print(f"\nNo pude convertir {len(fallidas)} captura(s):")
        for stem, motivo in fallidas.items():
            print(f"      {stem}: {motivo}")
        print("\nSi el error habla de una librería que falta (libtiff, libpng, libjpeg),")
        print("cwebp está instalado pero roto, casi siempre porque una dependencia se")
        print("actualizó por debajo. Se arregla reinstalándolo:")
        print("      macOS          brew reinstall webp")
        print("      Debian/Ubuntu  sudo apt install --reinstall webp")
        print("\nLas demás capturas siguen su camino; estas se quedan fuera del sitio")
        print("hasta que la conversión funcione.")

    # 4. Reescribir el HTML, solo con las que están completas y convertidas.
    #    Publicar una cuya conversión falló dejaría un hueco roto en la galería.
    #    Manda el WebP, no el original: los originales están fuera del repo, así
    #    que exigirlos borraba la galería entera en cualquier clon limpio.
    def publicable(e):
        if not e["titulo"]:
            return False
        if os.path.exists(os.path.join(RAIZ, SALIDA, f"{e['archivo']}-thumb.webp")):
            return True
        return args.check and e["archivo"] in stems

    listas = [e for e in entradas if publicable(e)]
    incompletas = len([e for e in entradas if not e["titulo"]])
    if incompletas:
        print(f"{incompletas} línea(s) sin título: esas no salen al sitio todavía.")

    # Sin capturas completas se publica el cofre vacío, que es un estado
    # legítimo de la sección: mejor eso que dejar lo de la corrida anterior.
    bloque, publicadas = construir_html(listas)
    if not splicear(destino, bloque, args.check):
        print(f"{args.destino} ya estaba al día.")
        return 0

    verbo = "Actualizaría" if args.check else "Actualicé"
    if not listas:
        print(f"{verbo} {args.destino}: sin capturas, queda el cofre vacío.")
        return 0

    anios = len(anios_presentes(listas))
    servidores = len(servidores_presentes(listas))
    print(f"{verbo} {args.destino}: {publicadas} capturas, "
          f"{anios} año(s) y {servidores} servidor(es) en los filtros.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Aviso as e:
        print(f"ERROR  {e}")
        sys.exit(1)
