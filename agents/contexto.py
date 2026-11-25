"""Contexto de la base y del RAG para la IA: lo que se sabe del tema de la pregunta.

Se agrega como mensaje de sistema cuando la pregunta no la resolvio ninguna consulta directa.
La IA debe responder SOLO con esto y decir cuando algo no esta.
"""

from __future__ import annotations

import sqlite3
from typing import List

from data import menu as m
from data import proveedores as prov
from data import rag_docs

MAX_LETRAS = 6000


def armar_contexto(pregunta: str, db_path: str = m.DB_PATH) -> str:
    partes: List[str] = []
    try:
        frags = rag_docs.buscar(pregunta, k=3, db_path=db_path, min_raices=1)
        if frags:
            partes.append("MANUALES (cita el documento y la sección):\n" + rag_docs.contexto(frags))
    except Exception:
        pass
    try:
        f = m.receta_por_nombre(pregunta, db_path)
        if f:
            ings = "; ".join(f"{i['cantidad']:g} {i['unidad']} {i['ingrediente']}" if i["cantidad"] else i["ingrediente"] for i in f["ingredientes"])
            partes.append(f"RECETA {f['nombre']} ({f['categoria']}): costo por plato ${f['costo_plato']:.2f}. Ingredientes: {ings}. Preparación: {f.get('instrucciones') or 'no registrada'}")
    except Exception:
        pass
    try:
        p = prov.producto_en_texto(pregunta, db_path)
        if p:
            precios = "; ".join(f"{x['proveedor']} ${x['precio']:.2f} por {x['unidad_precio']}" for x in prov.precios_de_producto(p["id"], db_path))
            conn = sqlite3.connect(db_path)
            try:
                stock = conn.execute("SELECT round(sum(cantidad_actual),1), min(unidad) FROM Inventario WHERE producto_id=? AND cantidad_actual>0", (p["id"],)).fetchone()
            finally:
                conn.close()
            partes.append(f"PRODUCTO {p['nombre']} ({p['categoria']}, {p['tipo']}): stock {stock[0] or 0} {stock[1] or ''}. Precios: {precios or 'sin precio de proveedor'}")
    except Exception:
        pass
    try:
        pv = prov.proveedor_en_texto(pregunta, db_path)
        if pv:
            d = prov.detalle(pv["id"], db_path)
            if d:
                lista = "; ".join(f"{x['producto']} ${x['precio']:.2f}/{x['unidad_precio']}" for x in d["productos"][:15])
                partes.append(f"PROVEEDOR {pv['nombre']} (entrega {d['proveedor'].get('dias_entrega') or 'sin dato'}): {lista}")
    except Exception:
        pass
    if not partes:
        return ""
    texto = ("DATOS DEL RESTAURANTE para esta pregunta. Responde SOLO con estos datos, en español, claro y corto. "
             "Si lo que preguntan no está aquí, di que no lo encuentras y sugiere una pregunta que sí puedas responder. "
             "No inventes precios, stock ni recetas.\n\n" + "\n\n".join(partes))
    return texto[:MAX_LETRAS]
