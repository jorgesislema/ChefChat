"""Normalizacion de textos ANTES de guardar en la base.

Una sola regla para todo el programa, asi no nacen duplicados como
"Crema Para Batir" y "Crema para Batir".
"""

import sqlite3
import unicodedata
from typing import Optional


def clave(texto: Optional[str]) -> str:
    """Forma comparable: sin acentos, minusculas, espacios simples."""
    t = unicodedata.normalize("NFD", str(texto or "").strip().lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.split())


def nombre_canonico(texto: Optional[str]) -> str:
    """'  crema   para BATIR ' -> 'Crema Para Batir' (conserva acentos)."""
    return " ".join(w.capitalize() for w in str(texto or "").split())


def unidad_canonica(texto: Optional[str]) -> str:
    return " ".join(str(texto or "").lower().split())


def motivo_canonico(texto: Optional[str]) -> str:
    t = " ".join(str(texto or "").split())
    return t[:1].upper() + t[1:].lower()


def categoria_canonica(conn: sqlite3.Connection, texto: Optional[str]) -> str:
    """Si ya existe la categoria (con o sin acento), usa la existente."""
    k = clave(texto)
    for (c,) in conn.execute("SELECT DISTINCT categoria FROM Catalogo WHERE categoria IS NOT NULL"):
        if clave(c) == k:
            return c
    return nombre_canonico(texto)


def buscar_producto_id(conn: sqlite3.Connection, nombre: Optional[str]) -> Optional[int]:
    """Id del producto del catalogo que coincide ignorando mayusculas y acentos."""
    k = clave(nombre)
    for pid, n in conn.execute("SELECT id, nombre FROM Catalogo"):
        if clave(n) == k:
            return pid
    return None
