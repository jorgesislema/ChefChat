"""Chat: recetas (por ingrediente o nombre), recetas para la merma y proveedores. Todo sale de la base, sin IA.

responder_consulta(pregunta) devuelve el texto o None si la pregunta no es de este tema.
Nunca devuelve texto vacio: si no encuentra algo, lo dice y sugiere que preguntar.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from agents.menu_chat import _dinero, _sin
from core.normalizar import clave
from data import menu as m
from data import proveedores as prov

_UNIDAD = {"kg": "kg", "l": "litro", "unidad": "unidad"}


def _num(x) -> str:
    return f"{x:g}" if x is not None else ""


def _fmt_ficha(f: dict) -> str:
    out = [f"**{f['nombre']}** ({f['categoria']}, {f['tiempo_prep']} min)" if f.get("tiempo_prep") else f"**{f['nombre']}** ({f['categoria']})"]
    out.append(f"Costo por plato: {_dinero(f['costo_plato'])}" + (f" · precio de venta {_dinero(f['precio_venta'])}" if f.get("precio_venta") else ""))
    out.append("Ingredientes:")
    for i in f["ingredientes"]:
        cant = f"{_num(i['cantidad'])} {i['unidad']} de " if i["cantidad"] else ""
        out.append(f"- {cant}{i['ingrediente']}")
    if f.get("instrucciones"):
        out.append("Preparación: " + f["instrucciones"].strip())
    alerg = f.get("alergenos_revisados") or []
    out.append("Alérgenos: " + (", ".join(alerg) if alerg else "ninguno detectado") + ". " + m.AVISO_ALERGENOS)
    return "\n".join(out)


def _fmt_ingrediente(r: dict) -> str:
    if not r["recetas"]:
        return f"No encontré recetas con «{r['ingrediente']}». Prueba con otro ingrediente, por ejemplo «recetas con pollo»."
    if r["total"] <= len(r["recetas"]):
        out = [f"Recetas con {r['ingrediente']} ({r['total']}):"]
    else:
        out = [f"Recetas con {r['ingrediente']} ({r['total']} en total; te muestro {len(r['recetas'])}, las que más lo usan y cuestan menos):"]
    for x in r["recetas"]:
        out.append(f"- {x['nombre']} ({x['categoria']}) | costo por plato {_dinero(x['costo_plato'])} | usa {'; '.join(x['usa'])}")
    out.append("Pídeme «receta de <nombre>» para ver los pasos.")
    if r.get("aviso"):
        out.append(r["aviso"])
    return "\n".join(out)


def _fmt_merma(r: dict) -> str:
    p = r["periodo"]
    if not r["productos"]:
        return "No encontré recetas que usen los productos que más se desperdician."
    out = [f"Lo que más se desperdició (mermas registradas del {p['desde']} al {p['hasta']}) y recetas para aprovecharlo:"]
    for x in r["productos"]:
        recs = ", ".join(f"{y['nombre']} ({_dinero(y['costo_plato'])})" for y in x["recetas"])
        out.append(f"- {x['producto']}: se perdieron {_dinero(x['costo_perdido'])} en {x['veces']} registros → prueba: {recs}")
    out.append("Para los sobrantes ya cocinados pregúntame «¿cómo aprovecho los sobrantes?».")
    return "\n".join(out)


def _fmt_producto(p: dict, filas: list, stock: Optional[dict] = None) -> str:
    en_stock = ""
    if stock is not None:
        en_stock = f"En inventario tienes {_num(stock['cantidad'])} {stock['unidad']}.\n" if stock["cantidad"] else "No tienes stock en inventario.\n"
    if not filas:
        return f"{en_stock}{p['nombre']}: ningún proveedor tiene precio cargado. Agrégalo en la pantalla Proveedores."
    out = [f"{en_stock}Precio de {p['nombre']} por proveedor:"]
    for i, f in enumerate(filas):
        cambio = f" (subió {f['cambio_pct']:g} %)" if f["cambio_pct"] and f["cambio_pct"] > 0 else f" (bajó {abs(f['cambio_pct']):g} %)" if f["cambio_pct"] and f["cambio_pct"] < 0 else ""
        barato = " ← más barato" if i == 0 and len(filas) > 1 else ""
        out.append(f"- {f['proveedor']}: {_dinero(f['precio'])} por {_UNIDAD.get(f['unidad_precio'], f['unidad_precio'])}{cambio}{barato}")
    return "\n".join(out)


def _fmt_proveedor(d: dict) -> str:
    p = d["proveedor"]
    cab = f"**{p['nombre']}**" + (f" · contacto {p['contacto']}" if p["contacto"] else "") + (f" · tel. {p['telefono']}" if p["telefono"] else "")
    out = [cab]
    if p["dias_entrega"]:
        out.append(f"Entrega: {p['dias_entrega']}")
    prods = d["productos"]
    if not prods:
        out.append("Aún no tiene productos con precio.")
        return "\n".join(out)
    out.append(f"Vende {len(prods)} productos. Algunos:")
    for x in prods[:12]:
        out.append(f"- {x['producto']}: {_dinero(x['precio'])} por {_UNIDAD.get(x['unidad_precio'], x['unidad_precio'])}" + (" (el más barato)" if x["es_mas_barato"] else ""))
    if len(prods) > 12:
        out.append("Mira todos en la pantalla Proveedores.")
    return "\n".join(out)


def _fmt_lista(lista: list) -> str:
    if not lista:
        return "Aún no hay proveedores. Agrégalos en la pantalla Proveedores."
    out = [f"Tienes {len(lista)} proveedores:"]
    for p in lista:
        out.append(f"- {p['nombre']}: {p['n_productos']} productos" + (f", entrega {p['dias_entrega']}" if p["dias_entrega"] else ""))
    out.append("Pregúntame «¿qué vende <proveedor>?» o «¿quién vende pollo?».")
    return "\n".join(out)


def _fmt_alertas(a: dict) -> str:
    if not a["alertas"]:
        return f"Ningún precio subió más de {a['umbral_pct']:g} %."
    out = [f"Subidas de precio de más de {a['umbral_pct']:g} %:"]
    for x in a["alertas"]:
        out.append(f"- {x['producto']} ({x['proveedor']}): de {_dinero(x['anterior'])} a {_dinero(x['actual'])} por {_UNIDAD.get(x['unidad_precio'], x['unidad_precio'])} (+{x['cambio_pct']:g} %)")
    return "\n".join(out)


def _producto(texto: str, db_path: str):
    """El producto mencionado: uno exacto, o una lista si el nombre es parcial y hay varios ('camaron' -> 3 productos)."""
    p = prov.producto_en_texto(texto, db_path)
    if p:
        return p
    cands = prov.productos_candidatos(texto, db_path=db_path)
    if len(cands) == 1:
        return cands[0]
    return cands or None


def _fmt_candidatos(cands: list, db_path: str) -> str:
    out = ["Encontré varios productos parecidos. Esto es lo más barato de cada uno:"]
    for c in cands:
        filas = prov.precios_de_producto(c["id"], db_path)
        if filas:
            f = filas[0]
            out.append(f"- {c['nombre']}: {_dinero(f['precio'])} por {_UNIDAD.get(f['unidad_precio'], f['unidad_precio'])} ({f['proveedor']})")
        else:
            out.append(f"- {c['nombre']}: sin precio cargado")
    out.append("Escribe el nombre completo para ver todos los proveedores.")
    return "\n".join(out)


def _termino_ingrediente(t: str) -> str:
    resto = t.rsplit(" con ", 1)[1] if " con " in t else ""
    resto = re.split(r"\b(sin|que|para|y que)\b|[?.,;]", resto)[0]
    palabras = [w for w in resto.split() if w not in {"el", "la", "los", "las", "un", "una", "unos", "unas", "algo", "de", "del", "mucho", "mucha", "poco"}]
    return " ".join(palabras[:3])


def responder_consulta(pregunta: str, hoy: Optional[date] = None, db_path: str = m.DB_PATH) -> Optional[str]:
    t = clave(pregunta)
    try:
        # 1) recetas para aprovechar la merma
        if re.search(r"merma|desperdicio", t) and re.search(r"receta|cocin|prepar|aprovech|usar|plato|que hago|reutiliz", t) \
                and not re.search(r"cost|cuanto|motivo|reporte|registr|exporta", t):
            return _fmt_merma(m.aprovechar_merma(db_path=db_path))

        # 2) cuanto cuesta un plato / precio de un producto
        if re.search(r"cuanto (cuesta|vale|sale|cobro)|precio|costo de", t) and not re.search(r"persona|desayuno|almuerzo|merienda|cena", t):
            f = m.receta_por_nombre(t, db_path)
            p = _producto(t, db_path)
            if isinstance(p, list):  # nombre parcial con varios productos: si hay un plato con ese nombre, gana el plato
                if not f:
                    return _fmt_candidatos(p, db_path)
                p = None
            # "cuanto cuesta el pollo": si lo escrito es solo el nombre de un producto, es el producto (no el "Mole con Pollo")
            palabras = {w for w in re.findall(r"[a-z0-9]+", t) if w not in m._PALABRAS_VACIAS and len(w) > 2}
            nombre_p = set(re.findall(r"[a-z0-9]+", clave(p["nombre"]))) if p else set()
            solo_producto = bool(p) and palabras <= (nombre_p | {w + "s" for w in nombre_p})
            if f and not solo_producto:
                return f"**{f['nombre']}**: costo por plato {_dinero(f['costo_plato'])}" + (f", precio de venta {_dinero(f['precio_venta'])}, margen {f['margen_pct']:g} %" if f.get("precio_venta") else "") + "."
            if p:
                return _fmt_producto(p, prov.precios_de_producto(p["id"], db_path), prov.stock_de_producto(p["id"], db_path))

        # 3) receta de un plato (ingredientes y pasos)
        if re.search(r"receta (de|del|para)|como (se )?(prepara|hace|cocina|preparo|hago|cocino)|ingredientes (de|del)|pasos (de|del)|preparacion (de|del)|dame la receta", t):
            f = m.receta_por_nombre(t, db_path)
            if f:
                return _fmt_ficha(f)
            if " con " not in t:
                return "No encontré esa receta. Pídeme «recetas con pollo» (o con otro ingrediente) y te muestro las que tengo."

        # 4) recetas con un ingrediente
        if re.search(r"\b(recetas?|platos?|cocin\w+|prepar\w+|hacer|hago)\b.*\bcon\b", t) and not re.search(r"venc|caduc|sobrante|persona|menu|merma", t):
            termino = _termino_ingrediente(pregunta.lower())  # con acentos, para mostrarlo bien
            if termino:
                return _fmt_ingrediente(m.recetas_con_ingrediente(termino, _sin(t), db_path=db_path))

        # 5) proveedores
        if re.search(r"proveedor|quien (me )?vende|a quien (le )?compr|donde compr|mas barato|mejor precio|subio|subieron|alza|aumento de precio|vende[n]?\b", t):
            if re.search(r"subi|alza|aument", t) and re.search(r"precio|proveedor", t):
                return _fmt_alertas({"alertas": prov.alertas_de_precio(db_path=db_path), "umbral_pct": prov.ALERTA_SUBIDA})
            pv = prov.proveedor_en_texto(t, db_path)
            # las palabras del nombre del proveedor ("Carnes" de "Carnes del Valle") no cuentan como producto
            t_prod = t
            if pv:
                for w in clave(pv["nombre"]).split():
                    t_prod = re.sub(rf"\b{re.escape(w)}\b", " ", t_prod)
            p = _producto(t_prod, db_path)
            if isinstance(p, list):
                return _fmt_candidatos(p, db_path)
            if pv and p:
                filas = [f for f in prov.precios_de_producto(p["id"], db_path) if f["proveedor"] == pv["nombre"]]
                if filas:
                    f = filas[0]
                    return f"{pv['nombre']} vende {p['nombre']} a {_dinero(f['precio'])} por {_UNIDAD.get(f['unidad_precio'], f['unidad_precio'])}."
                return f"{pv['nombre']} no tiene precio cargado para {p['nombre']}."
            if pv:
                return _fmt_proveedor(prov.detalle(pv["id"], db_path))
            if p:
                return _fmt_producto(p, prov.precios_de_producto(p["id"], db_path), prov.stock_de_producto(p["id"], db_path))
            if re.search(r"proveedor", t):
                return _fmt_lista(prov.listar(db_path))
    except m.MenuError as e:
        return str(e)
    return None
