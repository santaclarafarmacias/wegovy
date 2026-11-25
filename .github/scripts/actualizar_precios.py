#!/usr/bin/env python3
"""Actualiza los precios de la landing con los precios de Tienda Nube.

Lee precios.json (precio que hoy muestra la página para cada producto),
consulta el precio actual de cada producto en santaclarafarmacias.com y
reemplaza el precio viejo por el nuevo en los archivos listados.

No hay que editar este archivo. El precio se cambia solo en Tienda Nube.
"""
import json
import re
import sys
import time
import urllib.request

CONFIG = "precios.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")


def precio_tienda(url):
    """Precio final (con promoción) de la ficha, o None si no está disponible."""
    for intento in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("utf-8", "replace")
            m = re.search(r'tiendanube:price"\s+content="([0-9.]+)"', html)
            if not m:
                return None
            v = float(m.group(1))
            return int(v) if v == int(v) else v
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5)
        except Exception:
            time.sleep(5)
    raise RuntimeError(f"No se pudo leer {url}")


def con_comas(n):
    return f"{n:,}" if isinstance(n, int) else f"{n:,.2f}"


def reemplazar(texto, cambios):
    """Cambia todos los precios en una sola pasada (evita cambios en cadena)."""
    viejos = sorted(cambios, key=lambda x: -len(str(x)))
    alt_comas = "|".join(re.escape(con_comas(v)) for v in viejos)
    alt_plano = "|".join(re.escape(str(v)) for v in viejos)
    por_texto = {}
    for v, n in cambios.items():
        por_texto[con_comas(v)] = con_comas(n)
        por_texto[str(v)] = str(n)

    # $3,988  /  $ 3,988  /  $3988
    patron_peso = re.compile(r"(\$\s?)(" + alt_comas + "|" + alt_plano + r")(?![\d,])")
    # "3988" (datos para Google y listas de precios en el código)
    patron_comillas = re.compile(r'(")(' + alt_plano + r')(")')
    # "price": 3988 sin comillas
    patron_json = re.compile(r'("(?:price|lowPrice|highPrice)"\s*:\s*)(' + alt_plano + r')(?![\d.])')

    def sub(m):
        grupos = m.groups()
        return grupos[0] + por_texto[grupos[1]] + (grupos[2] if len(grupos) > 2 else "")

    total = 0
    for p in (patron_peso, patron_comillas, patron_json):
        texto, k = p.subn(sub, texto)
        total += k
    return texto, total


def main():
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    productos = cfg["productos"]
    nuevos, avisos = {}, []
    for url, viejo in productos.items():
        actual = precio_tienda(url)
        if actual is None:
            avisos.append(f"AVISO: sin precio en la tienda (no publicado o no existe): {url}")
            continue
        if actual != viejo:
            nuevos[url] = actual

    for a in avisos:
        print(a)
    if not nuevos:
        print("Sin cambios de precio.")
        return 0

    # Un precio viejo compartido por varios productos que cambian distinto es ambiguo.
    cambios, ambiguos = {}, set()
    for url, n in nuevos.items():
        v = productos[url]
        mismos = [u for u, p in productos.items() if p == v]
        destinos = {nuevos.get(u, v) for u in mismos}
        if len(destinos) > 1:
            ambiguos.add(v)
        else:
            cambios[v] = n
    for v in ambiguos:
        print(f"ERROR: el precio ${con_comas(v)} lo comparten varios productos y no "
              "cambiaron igual. Hay que corregir esta página a mano.")

    for archivo in cfg["archivos"]:
        t = open(archivo, encoding="utf-8").read()
        t2, k = reemplazar(t, cambios)
        if t2 != t:
            open(archivo, "w", encoding="utf-8").write(t2)
        print(f"{archivo}: {k} reemplazos")

    for url, n in nuevos.items():
        if productos[url] in cambios:
            print(f"{url}: ${con_comas(productos[url])} -> ${con_comas(n)}")
            productos[url] = n
    json.dump(cfg, open(CONFIG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(CONFIG, "a", encoding="utf-8").write("\n")
    return 1 if ambiguos else 0


if __name__ == "__main__":
    sys.exit(main())
