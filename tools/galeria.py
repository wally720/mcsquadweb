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

# Cuántas capturas se ven antes del botón "ver más". El corte real cae en el
# final de un bloque, así que el número exacto puede quedar un poco por encima.
VISIBLES = 10

# La rejilla tiene 4 columnas y todo se mide en unidades de 1 columna x 1 fila.
UNIDADES = {"norm": 1, "wide": 2, "tall": 2, "big": 4}
COLUMNAS = 4

# Con menos de esto no vale la pena la barra de filtros: se filtra con la vista.
MINIMO_PARA_FILTRAR = 6

# El orden manda en la barra. Solo salen las que tienen fotos.
CATEGORIAS = [
    ("bases", "Bases"),
    ("eventos", "Eventos"),
    ("rol", "Rol"),
    ("desastres", "Desastres"),
]

# Cuántos slots vacíos tiene el cofre cuando todavía no hay ninguna captura.
HUECOS_VACIA = 8

# Cada bloque suma 8 unidades, o sea 2 filas exactas de 4 columnas. Por eso el
# mosaico tesela sin agujeros por dentro, y por eso el corte del "ver más"
# tiene que caer entre bloques y no en cualquier foto.
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
    """Llama a cwebp. Salta si el destino ya está y es más nuevo que el origen."""
    if os.path.exists(destino) and os.path.getmtime(destino) >= os.path.getmtime(origen):
        return False
    cmd = ["cwebp", "-quiet", "-q", str(calidad), "-resize", str(ancho), "0", origen, "-o", destino]
    if check:
        print("      " + " ".join(cmd))
        return True
    subprocess.run(cmd, check=True)
    return True


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


def punto_de_corte(tamanos):
    """Dónde va el 'ver más': el último final de bloque que no pase de VISIBLES.
    Devuelve None si no hay tantas fotos como para que valga la pena cortar."""
    if len(tamanos) <= VISIBLES + 2:
        return None
    corte, i = 0, 0
    while True:
        bloque = BLOQUES[i % len(BLOQUES)]
        if corte + len(bloque) > VISIBLES or corte + len(bloque) >= len(tamanos):
            break
        corte += len(bloque)
        i += 1
    return corte or None


def huecos_para_cerrar(tamanos):
    """Cuántos slots vacíos hacen falta para que la última fila quede pareja."""
    unidades = sum(UNIDADES[t] for t in tamanos)
    return (-unidades) % COLUMNAS


# ------------------------------------------------------------------- lista

CABECERA = (
    "# Una línea por captura. Los campos van separados por |\n"
    "#\n"
    "#   archivo | título | servidor | año | categorías | alt\n"
    "#\n"
    "# archivo      nombre del original sin extensión, tal como está en originales/\n"
    "# categorías   bases, eventos, rol o desastres. Se puede poner más de una,\n"
    "#              separadas por espacio.\n"
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

def figura(e, tamano, extra, indent):
    src = f"{SALIDA}/{e['archivo']}-thumb.webp"
    full = f"{SALIDA}/{e['archivo']}.webp"
    try:
        w, h = medidas(os.path.join(RAIZ, src))
    except (OSError, Aviso):
        w, h = 640, 360
    titulo = html.escape(e["titulo"])
    meta = " · ".join(x for x in (e["servidor"], e["anio"]) if x)
    clase = "gal-slot gal-slot--extra" if extra else "gal-slot"
    talla = f' data-size="{tamano}"' if tamano != "norm" else ""
    i = " " * indent
    return (
        f'{i}<figure class="{clase}" data-cat="{html.escape(e["categorias"])}"{talla}>\n'
        f'{i}  <img src="{src}" data-full="{full}"\n'
        f'{i}       alt="{html.escape(e["alt"])}"\n'
        f'{i}       loading="lazy" width="{w}" height="{h}" />\n'
        f'{i}  <figcaption class="gal-tip"><b>{titulo}</b><span>{html.escape(meta)}</span></figcaption>\n'
        f'{i}  <button class="gal-open" type="button" aria-label="Ampliar: {titulo}"></button>\n'
        f'{i}</figure>\n'
    )


def barra_filtros(entradas, indent):
    """La barra solo sale si hay bastantes fotos y más de una categoría."""
    presentes = {c for e in entradas for c in e["categorias"].split()}
    usadas = [(k, etiqueta) for k, etiqueta in CATEGORIAS if k in presentes]
    if len(entradas) < MINIMO_PARA_FILTRAR or len(usadas) < 2:
        return ""
    i = " " * indent
    chips = [f'{i}    <input type="radio" name="galf" id="galf-todo" checked />'
             f'<label for="galf-todo">Todo</label>\n']
    for k, etiqueta in usadas:
        chips.append(f'{i}    <input type="radio" name="galf" id="galf-{k}" />'
                     f'<label for="galf-{k}">{etiqueta}</label>\n')
    return (
        f'{i}<div class="gal-bar">\n'
        f'{i}  <span class="gal-bar-label">Filtrar</span>\n'
        f'{i}  <fieldset class="gal-filters">\n'
        f'{i}    <legend class="sr-only">Filtrar capturas por tipo</legend>\n'
        + "".join(chips) +
        f'{i}  </fieldset>\n'
        f'{i}</div>\n\n'
    )


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
    """Devuelve la rejilla entera: filtros, figuras, huecos y botón.
    Sin entradas devuelve el cofre vacío, que es un estado válido del sitio."""
    if not entradas:
        return cofre_vacio(indent), None

    tamanos = asignar_tamanos(len(entradas))
    corte = punto_de_corte(tamanos)
    i = " " * indent
    salida = [barra_filtros(entradas, indent), f'{i}<div class="gal-grid gal-grid--full">\n']

    for n, (e, t) in enumerate(zip(entradas, tamanos)):
        salida.append(figura(e, t, extra=corte is not None and n >= corte, indent=indent + 2))

    # Huecos que cierran la última fila. Hacen falta dos juegos: con el botón
    # plegado la rejilla termina en otro punto que con todo desplegado.
    if corte is not None:
        for _ in range(huecos_para_cerrar(tamanos[:corte])):
            salida.append(f'{i}  <div class="gal-hole gal-hole--corte"></div>\n')
    for _ in range(huecos_para_cerrar(tamanos)):
        salida.append(f'{i}  <div class="gal-hole gal-hole--fin"></div>\n')

    salida.append(f'{i}</div>\n')

    if corte is not None:
        restantes = len(entradas) - corte
        salida.append(
            f'\n{i}<input type="checkbox" id="gal-mas" class="gal-mas-check" />\n'
            f'{i}<label class="gal-mas" for="gal-mas">'
            f'Ver las {restantes} restantes<span aria-hidden="true">▾</span></label>\n'
        )
    return "".join(salida), corte


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

    convertidas = 0
    for f in sorted(os.listdir(orig_dir)):
        stem, ext = os.path.splitext(f)
        if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        origen = os.path.join(orig_dir, f)
        if convertir(origen, os.path.join(RAIZ, SALIDA, f"{stem}-thumb.webp"), ANCHO_MINI, CALIDAD_MINI, args.check):
            convertidas += 1
        if convertir(origen, os.path.join(RAIZ, SALIDA, f"{stem}.webp"), ANCHO_FULL, CALIDAD_FULL, args.check):
            convertidas += 1
    print(f"{convertidas} archivo(s) convertido(s)." if convertidas else "Nada que convertir.")

    # 4. Reescribir el HTML, solo con las que están completas
    listas = [e for e in entradas if e["titulo"] and e["archivo"] in stems]
    incompletas = len([e for e in entradas if not e["titulo"]])
    if incompletas:
        print(f"{incompletas} línea(s) sin título: esas no salen al sitio todavía.")

    # Sin capturas completas se publica el cofre vacío, que es un estado
    # legítimo de la sección: mejor eso que dejar lo de la corrida anterior.
    bloque, corte = construir_html(listas)
    if not splicear(destino, bloque, args.check):
        print(f"{args.destino} ya estaba al día.")
        return 0

    verbo = "Actualizaría" if args.check else "Actualicé"
    if not listas:
        print(f"{verbo} {args.destino}: sin capturas, queda el cofre vacío.")
        return 0

    visibles = corte if corte is not None else len(listas)
    detalle = f" y {len(listas) - visibles} detrás del botón." if corte is not None else "."
    print(f"{verbo} {args.destino}: {len(listas)} capturas, {visibles} a la vista{detalle}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Aviso as e:
        print(f"ERROR  {e}")
        sys.exit(1)
