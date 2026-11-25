"""Recetas: lista, ficha y costo calculado con los precios de los proveedores.

El costo lo calcula codigo (nunca la IA):
  costo de un ingrediente = cantidad convertida a la unidad del precio x precio mas bajo vigente.
Los ingredientes sin producto, sin precio o sin conversion segura NO suman y se avisan.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.normalizar import clave
from core.unidades import convertir
from data.esquema import asegurar_esquema
from data.proveedores import DatoInvalido, mejor_precio_por_producto

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
SIN_COSTO_OK = {"agua", "hielo", "agua fria", "agua tibia", "agua caliente", "agua hirviendo"}
UNIDADES_MENORES = {"pizca", "gotas", "gota", "ralla", "rama", "ramas", "rodaja", "rebanadas", "dientes", "cucharada"}


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _calcular(conn: sqlite3.Connection, receta_id: str, mejores: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    lineas, total, con_costo, contables = [], 0.0, 0, 0
    for r in conn.execute(
        "SELECT ri.ingrediente, ri.cantidad, ri.unidad, ri.producto_id, c.nombre AS producto, c.tipo "
        "FROM RecetaIngredientes ri LEFT JOIN Catalogo c ON c.id=ri.producto_id WHERE ri.receta_id=? ORDER BY ri.id",
        (receta_id,),
    ):
        costo, nota, precio = None, None, None
        k = clave(r["ingrediente"])
        if k in SIN_COSTO_OK:
            nota = "No se cobra"
        elif clave(r["unidad"]) in UNIDADES_MENORES:
            nota = "Cantidad pequeña, no suma"
        else:
            contables += 1
            mejor = mejores.get(r["producto_id"]) if r["producto_id"] else None
            if r["producto_id"] is None:
                nota = "Sin producto en el catálogo"
            elif mejor is None:
                nota = "Sin precio de proveedor"
            else:
                cant = convertir(r["cantidad"], r["unidad"], mejor["unidad_precio"])
                if cant is None:
                    nota = f"No se puede pasar {r['unidad']} a {mejor['unidad_precio']}"
                else:
                    precio = mejor
                    costo = round(cant * mejor["precio"], 4)
                    total += costo
                    con_costo += 1
        lineas.append({"ingrediente": r["ingrediente"], "producto": r["producto"], "cantidad": r["cantidad"],
                       "unidad": r["unidad"], "costo": costo, "nota": nota,
                       "precio": precio["precio"] if precio else None, "unidad_precio": precio["unidad_precio"] if precio else None,
                       "proveedor": precio["proveedor"] if precio else None})
    return {"ingredientes": lineas, "costo_total": round(total, 2),
            "cobertura": round(con_costo / contables, 2) if contables else 1.0}


def _costo_plato(costo_archivo: Optional[float], costo_calculado_porcion: float) -> Dict[str, Any]:
    """Costo POR PLATO. El archivo de recetas trae 'costo estimado por plato': ese es el dato del dueño y manda.
    Si una receta no lo trae, se usa el calculado con precios de proveedores (y se dice)."""
    if costo_archivo:
        return {"costo_plato": round(float(costo_archivo), 2), "fuente_costo": "archivo"}
    return {"costo_plato": round(costo_calculado_porcion, 2), "fuente_costo": "calculado"}


def _precios_venta(conn: sqlite3.Connection) -> Dict[str, float]:
    return {r[0]: r[1] for r in conn.execute(
        "SELECT receta_id, avg(Precio_Venta_USD) FROM MenuSemanalPro WHERE receta_id IS NOT NULL GROUP BY receta_id")}


def listar(q: str = "", categoria: str = "", db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        mejores = mejor_precio_por_producto(conn)
        ventas = _precios_venta(conn)
        salida = []
        for r in conn.execute("SELECT id_receta, nombre, categoria, tiempo_prep, costo, alergenos, porciones FROM RecetasRAG ORDER BY categoria, nombre"):
            if q and clave(q) not in clave(r["nombre"]):
                continue
            if categoria and clave(categoria) != clave(r["categoria"]):
                continue
            c = _calcular(conn, r["id_receta"], mejores)
            porc = r["porciones"] or 1
            salida.append({"id_receta": r["id_receta"], "nombre": r["nombre"], "categoria": r["categoria"],
                           "tiempo_prep": r["tiempo_prep"], "alergenos": r["alergenos"], "costo_archivo": r["costo"],
                           "costo_calculado": c["costo_total"], "cobertura": c["cobertura"], "porciones": r["porciones"],
                           "costo_porcion": round(c["costo_total"] / porc, 2), "precio_venta": ventas.get(r["id_receta"]),
                           **_costo_plato(r["costo"], c["costo_total"] / porc)})
        return salida
    finally:
        conn.close()


def categorias(db_path: str = DB_PATH) -> List[str]:
    conn = _conn(db_path)
    try:
        vistos: Dict[str, str] = {}
        for (c,) in conn.execute("SELECT DISTINCT categoria FROM RecetasRAG WHERE categoria IS NOT NULL"):
            vistos.setdefault(clave(c), c)
        return sorted(vistos.values(), key=clave)
    finally:
        conn.close()


def ficha(receta_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        r = conn.execute("SELECT id_receta, nombre, categoria, tiempo_prep, costo, alergenos, instrucciones, porciones "
                         "FROM RecetasRAG WHERE id_receta=?", (receta_id,)).fetchone()
        if not r:
            return None
        c = _calcular(conn, receta_id, mejor_precio_por_producto(conn))
        porc = r["porciones"] or 1
        precio = _precios_venta(conn).get(receta_id)
        costo_porcion = round(c["costo_total"] / porc, 2)
        plato = _costo_plato(r["costo"], c["costo_total"] / porc)
        margen = round((precio - plato["costo_plato"]) / precio * 100, 1) if precio else None
        diferencia = (round((costo_porcion - plato["costo_plato"]) / plato["costo_plato"] * 100)
                      if plato["fuente_costo"] == "archivo" and plato["costo_plato"] and c["cobertura"] >= 0.8 else None)
        return {**dict(r), "porciones_supuestas": r["porciones"] is None, "porciones_usadas": porc, "costo_archivo": r["costo"],
                "costo_calculado": c["costo_total"], "cobertura": c["cobertura"], "costo_porcion": costo_porcion,
                **plato, "diferencia_pct": diferencia,
                "precio_venta": precio, "margen_pct": margen, "ingredientes": c["ingredientes"]}
    finally:
        conn.close()


def poner_porciones(receta_id: str, porciones: int, db_path: str = DB_PATH) -> None:
    if not isinstance(porciones, int) or not 1 <= porciones <= 500:
        raise DatoInvalido("Las porciones deben ser un número entre 1 y 500.")
    conn = _conn(db_path)
    try:
        n = conn.execute("UPDATE RecetasRAG SET porciones=? WHERE id_receta=?", (porciones, receta_id)).rowcount
        if not n:
            raise DatoInvalido("No encuentro esa receta.")
        conn.commit()
    finally:
        conn.close()
