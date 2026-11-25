"""Conversion de unidades de receta a unidades de precio (kg, l, unidad).

Solo convierte lo que se puede convertir sin adivinar:
masa -> kg, volumen -> l, conteo -> unidad.
Pizca, rama, gotas, cucharada, etc. no tienen conversion segura: devuelve None.
"""

from __future__ import annotations

from typing import Optional

from core.normalizar import clave

_MASA = {"g": 0.001, "gr": 0.001, "gramo": 0.001, "gramos": 0.001, "kg": 1.0, "kilo": 1.0, "kilos": 1.0,
         "kilogramo": 1.0, "kilogramos": 1.0, "lb": 0.45359237, "libra": 0.45359237, "libras": 0.45359237,
         "qq": 45.359237, "quintal": 45.359237}
_VOLUMEN = {"ml": 0.001, "mililitro": 0.001, "mililitros": 0.001, "l": 1.0, "lt": 1.0, "litro": 1.0, "litros": 1.0}
_CONTEO = {"unidad": 1.0, "unidades": 1.0, "u": 1.0, "und": 1.0, "pieza": 1.0, "piezas": 1.0}


def familia(unidad: Optional[str]) -> Optional[str]:
    u = clave(unidad)
    if u in _MASA:
        return "kg"
    if u in _VOLUMEN:
        return "l"
    if u in _CONTEO:
        return "unidad"
    return None


def convertir(cantidad: Optional[float], unidad_origen: Optional[str], unidad_destino: Optional[str]) -> Optional[float]:
    """Cantidad expresada en la unidad de precio, o None si no se puede convertir con seguridad."""
    if cantidad is None:
        return None
    u = clave(unidad_origen)
    destino = clave(unidad_destino)
    fam = familia(u)
    if fam is None or fam != familia(destino):
        return None
    tabla = {"kg": _MASA, "l": _VOLUMEN, "unidad": _CONTEO}[fam]
    para_destino = tabla.get(destino, 1.0)  # el destino "kg", "l" o "unidad" vale 1.0
    return cantidad * tabla[u] / para_destino
