"""Menu y costos (etapa D). TODO lo numerico lo calcula codigo, la IA no inventa precios ni platos.

- costo_por_persona: costo de un desayuno / almuerzo / merienda segun las recetas.
- armar_menu: propone menu del dia o de la semana con tope de costo por persona y sin ciertos alergenos.
- que_cocinar: recetas que usan lo que vence pronto, con cuantas porciones alcanzan.
- aprovechar_sobrantes: recetas para los sobrantes registrados.

El costo de un plato es el "costo estimado por plato" del archivo de recetas (ver data/recetas.py).
Los alergenos se revisan por lo que dice la receta Y por sus ingredientes (criterio prudente: ante la duda, se excluye).
"""

from __future__ import annotations

import itertools
import math
import random
import re
import sqlite3
import statistics
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from agents import vencimientos
from core.normalizar import clave
from core.unidades import convertir, familia
from data import recetas as rec
from data.esquema import asegurar_esquema

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")

# Que categorias de receta forman cada comida (cada tupla es un "puesto" del menu).
PLANTILLAS: Dict[str, List[tuple]] = {
    "desayuno": [("bebidas",), ("entrantes", "entrada")],
    "almuerzo": [("sopas",), ("platos fuertes", "principal"), ("postres",)],
    "merienda": [("bebidas",), ("postres",)],
    "cena": [("sopas",), ("platos fuertes", "principal")],
}
REPARTO = {"desayuno": 0.25, "almuerzo": 0.45, "merienda": 0.15, "cena": 0.35}  # parte del tope diario
# Eventos: platos para grupos, no para el menu diario. Entrada/Principal: son las 5 recetas de recetas_principales.csv;
# su valor (18 a 35) parece precio de venta y no costo, asi que no se mezcla con el costo de los demas platos.
EXCLUIR_CATEGORIAS = {"eventos especiales", "entrada", "principal"}
COBERTURA_MIN_CALCULADO = 0.8

ALERGENOS = {
    "gluten": r"gluten|trigo",
    "lacteos": r"lacte|leche",
    "huevo": r"huev",
    "frutos secos": r"fruto|nuez|nueces|almendra",
    "mani": r"\bmani\b|cacahuate",
    "soya": r"soya|soja",
    "pescado": r"pescado",
    "mariscos": r"marisco|crust|molusco",
}
# palabras de ingredientes que delatan un alergeno aunque la receta diga "Ninguno"
INGREDIENTES_ALERGENO = {
    "gluten": r"\b(harina de trigo|trigo|pan|pan rallado|panko|pasta|fideos?|galletas?|cerveza|cebada|centeno|masa de hojaldre|hojaldre|tortillas? de harina)\b",
    "lacteos": r"\b(leche|queso|crema|mantequilla|yogur|yogurt|nata|manjar|suero)\b",
    "huevo": r"\b(huevos?|clara|yema|mayonesa)\b",
    "frutos secos": r"\b(nueces|nuez|almendras?|avellanas?|pistachos?|castanas?|merey|pecanas?)\b",
    "mani": r"\b(mani|cacahuates?)\b",
    "soya": r"\b(soya|soja|tofu|salsa de soya)\b",
    "pescado": r"\b(pescado|atun|salmon|corvina|trucha|bacalao|tilapia|dorado|sardinas?|anchoas?)\b",
    "mariscos": r"\b(camarones?|langostinos?|pulpo|calamar(es)?|conchas?|mejillones?|cangrejo|almejas?|mariscos?)\b",
}
AVISO_ALERGENOS = "Revisa siempre los alérgenos con el chef antes de servir."


class MenuError(ValueError):
    """Error que se puede mostrar tal cual al usuario (HTTP 400)."""


def alergeno_canonico(texto: str) -> Optional[str]:
    t = clave(texto)
    for nombre, patron in ALERGENOS.items():
        if re.search(patron, t):
            return nombre
    return None


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _alergenos_de(declarado: Optional[str], ingredientes: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for tok in re.split(r"[,;/]|\by\b", declarado or ""):
        a = alergeno_canonico(tok)
        if a:
            out.add(a)
    for ing in ingredientes:
        k = clave(ing)
        for nombre, patron in INGREDIENTES_ALERGENO.items():
            if re.search(patron, k) and not (nombre == "gluten" and "maiz" in k):
                out.add(nombre)
    return out


def cargar_recetas(db_path: str = DB_PATH, todas: bool = False) -> List[Dict[str, Any]]:
    """Recetas con costo por plato, alergenos (declarados e inferidos) y productos que usan.
    Por defecto solo las del menu diario; todas=True incluye eventos y las 5 recetas principales."""
    base = {r["id_receta"]: r for r in rec.listar(db_path=db_path)}
    conn = _conn(db_path)
    try:
        ings: Dict[str, List[sqlite3.Row]] = {}
        for r in conn.execute("SELECT receta_id, producto_id, ingrediente, cantidad, unidad FROM RecetaIngredientes ORDER BY id"):
            ings.setdefault(r["receta_id"], []).append(r)
    finally:
        conn.close()
    out = []
    for rid, r in base.items():
        cat = clave(r["categoria"])
        if (cat in EXCLUIR_CATEGORIAS and not todas) or not r["costo_plato"]:
            continue
        lineas = ings.get(rid, [])
        out.append({
            "id_receta": rid, "nombre": r["nombre"], "categoria": r["categoria"], "cat": cat,
            "costo_plato": r["costo_plato"], "fuente_costo": r["fuente_costo"], "cobertura": r["cobertura"],
            "alergenos": sorted(_alergenos_de(r["alergenos"], (l["ingrediente"] for l in lineas))),
            "ingredientes": [dict(l) for l in lineas], "productos": {l["producto_id"] for l in lineas if l["producto_id"]},
        })
    return out


# ---------------------------------------------------------------- lo que vence pronto
def por_vencer(dias: int = 1, hoy: Optional[date] = None, db_path: str = DB_PATH) -> Dict[int, Dict[str, Any]]:
    """{producto_id: {producto, vence, dias, stock:{kg|l|unidad: cantidad}}} de ALIMENTOS que vencen hoy o dentro de `dias`."""
    hoy = hoy or date.today()
    conn = _conn(db_path)
    try:
        ids = {r["nombre"]: r["id"] for r in conn.execute("SELECT id, nombre FROM Catalogo")}
    finally:
        conn.close()
    out: Dict[int, Dict[str, Any]] = {}
    for lote in vencimientos.vencen_entre(hoy, hoy + timedelta(days=dias), db_path):
        if lote.get("tipo") == "limpieza" or lote["producto"] not in ids:
            continue
        pid = ids[lote["producto"]]
        fam = familia(lote["unidad"])
        d = out.setdefault(pid, {"producto": lote["producto"], "vence": lote["vence"], "stock": {}})
        d["vence"] = min(d["vence"], lote["vence"])
        if fam:
            d["stock"][fam] = d["stock"].get(fam, 0.0) + (convertir(lote["cantidad"], lote["unidad"], fam) or 0.0)
    for d in out.values():
        d["dias"] = (date.fromisoformat(d["vence"]) - hoy).days
    return out


def que_cocinar(dias: int = 1, hoy: Optional[date] = None, limite: int = 8, excluir: Iterable[str] = (),
                db_path: str = DB_PATH) -> Dict[str, Any]:
    """Recetas que gastan lo que vence en `dias` dias, con cuantas porciones alcanzan con ese stock."""
    hoy = hoy or date.today()
    prohibidos = _validar_alergenos(excluir)
    pv = por_vencer(dias, hoy, db_path)
    sugeridas = []
    for r in cargar_recetas(db_path):
        if prohibidos & set(r["alergenos"]):
            continue
        usa, alcanzan = [], []
        for ing in r["ingredientes"]:
            d = pv.get(ing["producto_id"]) if ing["producto_id"] else None
            fam = familia(ing["unidad"])
            if not d or not fam or not ing["cantidad"]:
                continue
            necesita = convertir(ing["cantidad"], ing["unidad"], fam) or 0.0
            if necesita < 0.02 and fam != "unidad":  # menos de 20 g o 20 ml: no cuenta como ingrediente principal
                continue
            stock = d["stock"].get(fam)
            if not stock:
                continue
            alcanza = math.floor(stock / necesita) if necesita else 0
            usa.append({"producto": d["producto"], "vence": d["vence"], "dias": d["dias"], "stock": round(stock, 2),
                        "unidad": fam, "necesita_por_plato": round(necesita, 3), "alcanza_para": alcanza})
            alcanzan.append(alcanza)
        if usa and min(alcanzan) >= 1:
            sugeridas.append({"id_receta": r["id_receta"], "nombre": r["nombre"], "categoria": r["categoria"],
                              "costo_plato": r["costo_plato"], "alergenos": r["alergenos"], "usa": usa,
                              "porciones_posibles": min(alcanzan)})
    sugeridas.sort(key=lambda s: (-len(s["usa"]), -s["porciones_posibles"], s["nombre"]))
    return {"hoy": hoy.isoformat(), "dias": dias, "por_vencer": [
        {"producto_id": k, **{kk: vv for kk, vv in v.items()}} for k, v in sorted(pv.items(), key=lambda kv: kv[1]["vence"])],
        "recetas": sugeridas[:limite], "aviso": AVISO_ALERGENOS if prohibidos else None}


# ---------------------------------------------------------------- costo por persona
def _validar_alergenos(excluir: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for e in excluir:
        txt = clave(re.sub(r"^sin\s+", "", clave(e)))
        if not txt:
            continue
        a = alergeno_canonico(txt)
        if not a:
            raise MenuError(f"No conozco el alérgeno «{e}». Puedo evitar: {', '.join(ALERGENOS)}.")
        out.add(a)
    return out


def _por_puesto(recetas: List[Dict[str, Any]], servicio: str, prohibidos: Set[str]) -> List[List[Dict[str, Any]]]:
    if servicio not in PLANTILLAS:
        raise MenuError(f"No conozco la comida «{servicio}». Puedo armar: {', '.join(PLANTILLAS)}.")
    return [[r for r in recetas if r["cat"] in puesto and not (prohibidos & set(r["alergenos"]))] for puesto in PLANTILLAS[servicio]]


def costo_por_persona(db_path: str = DB_PATH) -> Dict[str, Any]:
    """Costo de una comida por persona: minimo (lo mas barato), tipico (promedio) y maximo."""
    recetas = cargar_recetas(db_path)
    out = {}
    for servicio in PLANTILLAS:
        puestos = _por_puesto(recetas, servicio, set())
        if not all(puestos):
            out[servicio] = None
            continue
        out[servicio] = {
            "minimo": round(sum(min(r["costo_plato"] for r in p) for p in puestos), 2),
            "tipico": round(sum(statistics.mean(r["costo_plato"] for r in p) for p in puestos), 2),
            "maximo": round(sum(max(r["costo_plato"] for r in p) for p in puestos), 2),
            "platos": [", ".join(sorted({r["categoria"].lower() for r in p})) for p in puestos],
        }
    return {"por_comida": out, "nota": "Costo por persona = suma del costo estimado por plato de cada puesto de la comida."}


# ---------------------------------------------------------------- armar menu
def _armar_servicio(servicio: str, tope: Optional[float], prohibidos: Set[str], usadas: Set[str], recetas: List[Dict[str, Any]],
                    preferidos: Set[int], rng: random.Random) -> Dict[str, Any]:
    puestos = _por_puesto(recetas, servicio, prohibidos)
    if not all(puestos):
        return {"servicio": servicio, "platos": [], "costo_persona": None, "cumple_tope": False,
                "nota": "No hay recetas suficientes para esta comida con esas condiciones."}
    finalistas = []
    for p in puestos:
        libres = [r for r in p if r["id_receta"] not in usadas] or p  # si ya se usaron todas, se permite repetir
        orden = sorted(libres, key=lambda r: (-len(r["productos"] & preferidos), r["costo_plato"]))
        baratas = sorted(libres, key=lambda r: r["costo_plato"])[:6]
        pool = list({r["id_receta"]: r for r in orden[:10] + baratas}.values())
        rng.shuffle(pool)
        finalistas.append(pool)
    mejor, mejor_clave = None, None
    objetivo = tope * 0.85 if tope else None
    for combo in itertools.product(*finalistas):
        costo = sum(r["costo_plato"] for r in combo)
        if tope is not None and costo > tope:
            continue
        score = sum(len(r["productos"] & preferidos) for r in combo)
        k = (score, -abs(costo - objetivo)) if objetivo else (score, 0)
        if mejor_clave is None or k > mejor_clave:
            mejor, mejor_clave = combo, k
    cumple = mejor is not None
    if mejor is None:  # nada cabe en el tope: se muestra lo mas barato y se dice claro
        mejor = tuple(min(p, key=lambda r: r["costo_plato"]) for p in finalistas)
    platos = [{"id_receta": r["id_receta"], "nombre": r["nombre"], "categoria": r["categoria"], "costo_plato": r["costo_plato"],
               "fuente_costo": r["fuente_costo"], "alergenos": r["alergenos"],
               "usa_por_vencer": [i["ingrediente"] for i in r["ingredientes"] if i["producto_id"] in preferidos][:4]} for r in mejor]
    total = round(sum(p["costo_plato"] for p in platos), 2)
    return {"servicio": servicio, "platos": platos, "costo_persona": total, "tope": round(tope, 2) if tope else None,
            "cumple_tope": cumple if tope else True,
            "nota": None if cumple or not tope else f"Lo más barato posible cuesta {total:.2f} por persona y supera el tope de {tope:.2f}."}


def armar_menu(servicios: Iterable[str] = ("desayuno", "almuerzo", "merienda"), tope_dia: Optional[float] = None,
               excluir: Iterable[str] = (), dias: int = 1, preferir_por_vencer: bool = True, dias_vencer: int = 3,
               hoy: Optional[date] = None, semilla: int = 0, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Menu de 1 a 7 dias. `tope_dia` = costo maximo por persona por dia, repartido entre las comidas pedidas."""
    servicios = [clave(s) for s in servicios]
    if not servicios:
        raise MenuError("Elige al menos una comida.")
    if not 1 <= dias <= 7:
        raise MenuError("Puedo armar de 1 a 7 días.")
    if tope_dia is not None and tope_dia <= 0:
        raise MenuError("El tope por persona debe ser mayor que cero.")
    for s in servicios:
        if s not in PLANTILLAS:
            raise MenuError(f"No conozco la comida «{s}». Puedo armar: {', '.join(PLANTILLAS)}.")
    prohibidos = _validar_alergenos(excluir)
    hoy = hoy or date.today()
    recetas = cargar_recetas(db_path)
    preferidos = set(por_vencer(dias_vencer, hoy, db_path)) if preferir_por_vencer else set()
    suma = sum(REPARTO[s] for s in servicios)
    rng = random.Random(semilla)
    usadas: Set[str] = set()
    plan = []
    for i in range(dias):
        dia = hoy + timedelta(days=i)
        comidas = []
        for s in servicios:
            tope = tope_dia * REPARTO[s] / suma if tope_dia else None
            c = _armar_servicio(s, tope, prohibidos, usadas, recetas, preferidos, rng)
            usadas.update(p["id_receta"] for p in c["platos"])
            comidas.append(c)
        costos = [c["costo_persona"] for c in comidas]
        plan.append({"fecha": dia.isoformat(), "comidas": comidas,
                     "costo_persona": round(sum(costos), 2) if all(x is not None for x in costos) else None})
    total_dia = [p["costo_persona"] for p in plan if p["costo_persona"] is not None]
    return {"dias": plan, "tope_dia": tope_dia, "excluye": sorted(prohibidos), "usa_por_vencer": preferir_por_vencer,
            "costo_promedio_dia": round(statistics.mean(total_dia), 2) if total_dia else None,
            "cumple_tope": all(c["cumple_tope"] for p in plan for c in p["comidas"]),
            "aviso": AVISO_ALERGENOS if prohibidos else None}


# ---------------------------------------------------------------- sobrantes
def aprovechar_sobrantes(hoy: Optional[date] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Para cada sobrante registrado: si aun esta dentro de su plazo sanitario y que recetas lo usan."""
    hoy = hoy or date.today()
    conn = _conn(db_path)
    try:
        filas = conn.execute("SELECT * FROM SobrantesReutilizables WHERE destino_actual='almacenado' ORDER BY fecha_registro DESC").fetchall()
    finally:
        conn.close()
    recetas = cargar_recetas(db_path)
    salida = []
    for f in filas:
        limite = date.fromisoformat(f["fecha_registro"][:10]) + timedelta(days=int(f["dias_reutilizacion_sanitaria"] or 0))
        vigente = limite >= hoy
        palabras = [w for w in clave(f["producto_sopro"]).split() if len(w) > 3 and w not in ("cocido", "guisado", "frito", "asado", "hervido")]
        ideas = []
        if vigente and palabras:
            for r in recetas:
                if any(w in clave(i["ingrediente"]) for i in r["ingredientes"] for w in palabras) and r["cat"] != "postres":
                    ideas.append({"id_receta": r["id_receta"], "nombre": r["nombre"], "costo_plato": r["costo_plato"]})
        salida.append({"id": f["id_sobrante"], "producto": f["producto_sopro"], "cantidad": f["cantidad"], "unidad": f["unidad"],
                       "registrado": f["fecha_registro"], "usar_hasta": limite.isoformat(), "vigente": vigente,
                       "recetas": ideas[:5],
                       "mensaje": None if vigente else "Pasó el plazo sanitario. No se debe reutilizar."})
    return {"sobrantes": salida}


# ---------------------------------------------------------------- buscar recetas (ingrediente, nombre, merma)
_PALABRAS_VACIAS = {"de", "del", "la", "el", "los", "las", "con", "para", "una", "un", "que", "como", "por", "en", "y", "al",
                    "receta", "recetas", "plato", "platos", "preparar", "preparo", "hacer", "hago", "cocinar", "dame", "dime",
                    "quiero", "puedo", "pasos", "ingredientes", "preparacion", "cual", "cuales", "me", "mi", "se", "tiene", "tienes",
                    "cuanto", "cuesta", "vale", "sale", "cobro", "precio", "costo", "kilo", "litro"}


def _raices(termino: str) -> List[str]:
    k = clave(termino)
    s = k[:-2] if k.endswith("es") and len(k) > 4 else k[:-1] if k.endswith("s") and len(k) > 3 else k
    return list(dict.fromkeys([k, s]))


def recetas_con_ingrediente(termino: str, excluir: Iterable[str] = (), limite: int = 8, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Recetas que llevan `termino` como ingrediente (por nombre del ingrediente o del producto del catalogo)."""
    prohibidos = _validar_alergenos(excluir)
    raices = [r for r in _raices(termino) if r]
    if not raices:
        raise MenuError("Dime qué ingrediente quieres usar.")
    patron = re.compile(r"\b(" + "|".join(re.escape(r) for r in raices) + ")")
    encontradas = []
    for r in cargar_recetas(db_path, todas=True):
        if prohibidos & set(r["alergenos"]):
            continue
        coinciden = [i for i in r["ingredientes"] if patron.search(clave(i["ingrediente"]))]
        if coinciden:
            encontradas.append({"id_receta": r["id_receta"], "nombre": r["nombre"], "categoria": r["categoria"],
                                "costo_plato": r["costo_plato"], "alergenos": r["alergenos"],
                                "usa": [f"{i['cantidad']:g} {i['unidad']} de {i['ingrediente']}" if i["cantidad"] else i["ingrediente"]
                                        for i in coinciden][:3]})
    encontradas.sort(key=lambda x: (-len(x["usa"]), x["costo_plato"], x["nombre"]))
    return {"ingrediente": termino, "total": len(encontradas), "recetas": encontradas[:limite],
            "aviso": AVISO_ALERGENOS if prohibidos else None}


def receta_por_nombre(texto: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """La receta cuyo nombre mejor coincide con lo que se escribio. None si ninguna coincide bien."""
    tokens = [t for t in re.findall(r"[a-z0-9]+", clave(texto)) if t not in _PALABRAS_VACIAS and len(t) > 2]
    if not tokens:
        return None
    mejor, mejor_k = None, None
    for r in cargar_recetas(db_path, todas=True):
        nombre = clave(r["nombre"])
        palabras = set(re.findall(r"[a-z0-9]+", nombre))
        aciertos = sum(1 for t in tokens if t in palabras or any(p.startswith(t) or t.startswith(p) for p in palabras if len(p) > 3 and len(t) > 3))
        cobertura = aciertos / len(tokens)
        if cobertura < 0.6 or aciertos == 0:
            continue
        k = (cobertura, aciertos / max(len(palabras), 1), -len(nombre))
        if mejor_k is None or k > mejor_k:
            mejor, mejor_k = r, k
    if mejor is None:
        return None
    ficha = rec.ficha(mejor["id_receta"], db_path)
    ficha["alergenos_revisados"] = mejor["alergenos"]
    return ficha


def aprovechar_merma(limite: int = 5, recetas_por_producto: int = 3, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Lo que mas se desperdicia (segun el registro de mermas) y recetas que lo usan para aprovecharlo."""
    conn = _conn(db_path)
    try:
        filas = conn.execute("SELECT producto, round(sum(costo_estimado),2) AS costo, count(*) AS veces, round(sum(cantidad),1) AS cantidad, "
                             "min(unidad) AS unidad FROM Mermas WHERE producto IS NOT NULL AND trim(producto)!='' "
                             "GROUP BY lower(trim(producto)) ORDER BY costo DESC LIMIT 40").fetchall()
        rango = conn.execute("SELECT min(fecha), max(fecha) FROM Mermas").fetchone()
    finally:
        conn.close()
    pool = cargar_recetas(db_path)
    salida = []
    for f in filas:
        raices = [r for r in _raices(f["producto"]) if r]
        patron = re.compile(r"\b(" + "|".join(re.escape(r) for r in raices) + ")")
        recetas = [x for x in pool if any(patron.search(clave(i["ingrediente"])) for i in x["ingredientes"])]
        if not recetas:
            continue
        recetas.sort(key=lambda x: (x["costo_plato"], x["nombre"]))
        salida.append({"producto": f["producto"], "costo_perdido": f["costo"], "veces": f["veces"], "cantidad": f["cantidad"], "unidad": f["unidad"],
                       "recetas": [{"id_receta": x["id_receta"], "nombre": x["nombre"], "costo_plato": x["costo_plato"]} for x in recetas[:recetas_por_producto]]})
        if len(salida) >= limite:
            break
    return {"periodo": {"desde": rango[0], "hasta": rango[1]}, "productos": salida}
