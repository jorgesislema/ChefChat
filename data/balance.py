"""Balance de masas del turno (ver docs/PLAN_BALANCE_TURNO.md).

lo que entro = lo bueno que salio + perdida normal + lo anotado + SIN EXPLICAR

Tres miradas: total en kg, por ingrediente (donde esta la fuga) y por unidades (producido contra recibido por otra persona).
Todo lo calcula codigo. La IA no interviene.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.formato import dinero
from core.normalizar import buscar_producto_id, clave
from core.unidades import convertir, familia
from data.esquema import asegurar_esquema, registrar_cambio
from data.proveedores import DatoInvalido

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
PERDIDA_NORMAL_DEFECTO = 3.0
TOLERANCIA_DEFECTO = 2.0
KG_POR_LITRO_DEFECTO = 1.0
TIPOS_SALIDA = ("comida_personal", "residuo_limpieza", "muestra", "otro")
NOMBRE_SALIDA = {"comida_personal": "Comida del personal", "residuo_limpieza": "Residuo de limpieza", "muestra": "Muestras", "otro": "Otro"}


def _n(x: float) -> str:
    """12.345 -> '12,3' (un decimal, coma como en la pantalla). Redondea 1,65 a 1,7 como la pantalla (no 1,6)."""
    from decimal import ROUND_HALF_UP, Decimal
    return str(Decimal(repr(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)).replace(".", ",")


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _validar_turno(fecha: str, turno: str) -> str:
    from data.turnos import TURNOS
    if turno not in TURNOS:
        raise DatoInvalido("El turno debe ser matutino, vespertino o nocturno.")
    try:
        f = date.fromisoformat(str(fecha)).isoformat()
    except ValueError:
        raise DatoInvalido("La fecha no es válida (usa año-mes-día).") from None
    if f > date.today().isoformat():
        raise DatoInvalido("No se puede anotar en un día que aún no llega.")
    return f


def _no_firmado(conn: sqlite3.Connection, fecha: str, turno: str) -> None:
    r = conn.execute("SELECT estado FROM InformesTurno WHERE fecha=? AND turno=?", (fecha, turno)).fetchone()
    if r and r["estado"] == "firmado":
        raise DatoInvalido("El informe de este turno ya está firmado: no se puede anotar nada más.")


# ---------------------------------------------------------------- conversion a kg
def a_kg(cantidad: Optional[float], unidad: Optional[str], kg_por_unidad: Optional[float]) -> Optional[float]:
    """Cantidad en kg. Litros: con el peso por litro (1 si no hay dato). Unidades: SOLO con el peso por unidad."""
    if cantidad is None:
        return None
    fam = familia(unidad)
    if fam == "kg":
        return convertir(cantidad, unidad, "kg")
    if fam == "l":
        return convertir(cantidad, unidad, "l") * (kg_por_unidad or KG_POR_LITRO_DEFECTO)
    if fam == "unidad":
        return cantidad * kg_por_unidad if kg_por_unidad else None
    return None


# ---------------------------------------------------------------- estandares por receta
def estandar(receta_id: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    conn = _conn(db_path)
    try:
        r = conn.execute("SELECT * FROM EstandaresReceta WHERE receta_id=?", (receta_id,)).fetchone()
    finally:
        conn.close()
    if r:
        return {**dict(r), "es_defecto": False}
    return {"receta_id": receta_id, "peso_unidad_g": None, "perdida_normal_pct": PERDIDA_NORMAL_DEFECTO,
            "tolerancia_pct": TOLERANCIA_DEFECTO, "notas": None, "es_defecto": True}


def guardar_estandar(receta_id: str, peso_unidad_g: Optional[float], perdida_normal_pct: float, tolerancia_pct: float,
                     notas: str = "", db_path: str = DB_PATH) -> None:
    if peso_unidad_g is not None and not 0 < peso_unidad_g <= 100000:
        raise DatoInvalido("El peso por unidad debe ser mayor que cero (en gramos).")
    if not 0 <= perdida_normal_pct < 60:
        raise DatoInvalido("La pérdida normal debe estar entre 0 y 60 %.")
    if not 0 < tolerancia_pct <= 30:
        raise DatoInvalido("La tolerancia debe estar entre 0 y 30 %.")
    conn = _conn(db_path)
    try:
        nombre = conn.execute("SELECT nombre FROM RecetasRAG WHERE id_receta=?", (receta_id,)).fetchone()
        if not nombre:
            raise DatoInvalido("No encuentro esa receta.")
        conn.execute("INSERT INTO EstandaresReceta (receta_id, peso_unidad_g, perdida_normal_pct, tolerancia_pct, notas, actualizado) "
                     "VALUES (?,?,?,?,?, datetime('now','localtime')) ON CONFLICT(receta_id) DO UPDATE SET peso_unidad_g=excluded.peso_unidad_g, "
                     "perdida_normal_pct=excluded.perdida_normal_pct, tolerancia_pct=excluded.tolerancia_pct, notas=excluded.notas, actualizado=excluded.actualizado",
                     (receta_id, peso_unidad_g, perdida_normal_pct, tolerancia_pct, " ".join((notas or "").split())[:300]))
        registrar_cambio(conn, "estandar", "cambiar", f"{nombre[0]}: pérdida normal {perdida_normal_pct:g} %, tolerancia {tolerancia_pct:g} %"
                         + (f", {peso_unidad_g:g} g por unidad" if peso_unidad_g else ""))
        conn.commit()
    finally:
        conn.close()


def poner_kg_por_unidad(producto: "str | int", kg: Optional[float], db_path: str = DB_PATH) -> None:
    """Peso de 1 unidad (o de 1 litro) de un producto. `producto` = nombre o id."""
    if kg is not None and not 0 < kg <= 1000:
        raise DatoInvalido("El peso debe ser mayor que cero (en kg).")
    conn = _conn(db_path)
    try:
        if isinstance(producto, int):
            r = conn.execute("SELECT id, nombre FROM Catalogo WHERE id=?", (producto,)).fetchone()
            pid, producto = (r["id"], r["nombre"]) if r else (None, producto)
        else:
            pid = buscar_producto_id(conn, producto)
        if pid is None:
            raise DatoInvalido("No encuentro ese producto.")
        conn.execute("UPDATE Catalogo SET kg_por_unidad=? WHERE id=?", (kg, pid))
        registrar_cambio(conn, "producto", "cambiar", f"{producto}: peso por unidad {kg:g} kg" if kg else f"{producto}: sin peso por unidad")
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- anotar movimientos
def anotar_movimiento(fecha: str, turno: str, tipo: str, producto: str, cantidad: float, unidad: str,
                      entrego: str = "", recibio: str = "", descontar_inventario: bool = True, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Entrega de bodega al turno (descuenta del inventario, lo que vence antes primero) o devolucion (lo vuelve a sumar)."""
    from data.inventario import entrada_ajuste, salida_fifo
    f = _validar_turno(fecha, turno)
    if tipo not in ("entrega", "devolucion"):
        raise DatoInvalido("El tipo debe ser entrega o devolución.")
    try:
        cant = round(float(cantidad), 3)
    except (TypeError, ValueError):
        raise DatoInvalido("La cantidad debe ser un número.") from None
    if not 0 < cant <= 100000:
        raise DatoInvalido("La cantidad debe ser mayor que cero.")
    if familia(unidad) is None:
        raise DatoInvalido("La unidad no es válida. Usa kg, g, l, ml, libra, qq o unidad.")
    conn = _conn(db_path)
    try:
        _no_firmado(conn, f, turno)
        pid = buscar_producto_id(conn, producto)
        if pid is None:
            raise DatoInvalido("Ese producto no está en tu lista.")
        nombre = conn.execute("SELECT nombre FROM Catalogo WHERE id=?", (pid,)).fetchone()[0]
        aviso = None
        if descontar_inventario:
            if tipo == "entrega":
                falto = salida_fifo(conn, pid, cant, unidad)
                if falto > 1e-6:
                    aviso = f"En el inventario no había suficiente {nombre}: faltaron {falto:g} {unidad}. Revisa el stock con un conteo."
            else:
                entrada_ajuste(conn, pid, cant, unidad, f, "DEV")
        mid = conn.execute("INSERT INTO MovimientosTurno (fecha, turno, tipo, producto_id, cantidad, unidad, entrego, recibio, desconto_inventario) "
                           "VALUES (?,?,?,?,?,?,?,?,?)",
                           (f, turno, tipo, pid, cant, unidad, " ".join(entrego.split())[:80], " ".join(recibio.split())[:80], int(descontar_inventario))).lastrowid
        registrar_cambio(conn, "bodega", "crear", f"{'Entrega' if tipo == 'entrega' else 'Devolución'} turno {turno} {f}: {cant:g} {unidad} de {nombre}")
        conn.commit()
        return {"id": mid, "aviso": aviso}
    finally:
        conn.close()


def quitar_movimiento(mov_id: int, db_path: str = DB_PATH) -> None:
    """Quita un movimiento mal anotado y deshace su efecto en el inventario."""
    from data.inventario import entrada_ajuste, salida_fifo
    conn = _conn(db_path)
    try:
        m = conn.execute("SELECT m.*, c.nombre FROM MovimientosTurno m JOIN Catalogo c ON c.id=m.producto_id WHERE m.id=?", (mov_id,)).fetchone()
        if not m:
            raise DatoInvalido("No encuentro ese movimiento.")
        _no_firmado(conn, m["fecha"], m["turno"])
        if m["desconto_inventario"]:
            if m["tipo"] == "entrega":
                entrada_ajuste(conn, m["producto_id"], m["cantidad"], m["unidad"], m["fecha"], "DEV")
            else:
                salida_fifo(conn, m["producto_id"], m["cantidad"], m["unidad"])
        conn.execute("DELETE FROM MovimientosTurno WHERE id=?", (mov_id,))
        registrar_cambio(conn, "bodega", "quitar", f"{m['tipo']} turno {m['turno']} {m['fecha']}: {m['cantidad']:g} {m['unidad']} de {m['nombre']}")
        conn.commit()
    finally:
        conn.close()


def anotar_salida(fecha: str, turno: str, tipo: str, kg: float, nota: str = "", persona: str = "", producto: Optional[str] = None,
                  db_path: str = DB_PATH) -> Dict[str, Any]:
    f = _validar_turno(fecha, turno)
    if tipo not in TIPOS_SALIDA:
        raise DatoInvalido("Tipo no válido. Usa comida del personal, residuo de limpieza, muestra u otro.")
    try:
        k = round(float(kg), 3)
    except (TypeError, ValueError):
        raise DatoInvalido("Los kilos deben ser un número.") from None
    if not 0 < k <= 10000:
        raise DatoInvalido("Los kilos deben ser mayores que cero.")
    conn = _conn(db_path)
    try:
        _no_firmado(conn, f, turno)
        pid = buscar_producto_id(conn, producto) if producto else None
        sid = conn.execute("INSERT INTO SalidasTurno (fecha, turno, tipo, kg, producto_id, nota, persona) VALUES (?,?,?,?,?,?,?)",
                           (f, turno, tipo, k, pid, " ".join((nota or "").split())[:200], " ".join((persona or "").split())[:80])).lastrowid
        registrar_cambio(conn, "turno", "crear", f"{NOMBRE_SALIDA[tipo]} turno {turno} {f}: {k:g} kg")
        conn.commit()
        return {"id": sid}
    finally:
        conn.close()


def quitar_salida(salida_id: int, db_path: str = DB_PATH) -> None:
    conn = _conn(db_path)
    try:
        s = conn.execute("SELECT * FROM SalidasTurno WHERE id=?", (salida_id,)).fetchone()
        if not s:
            raise DatoInvalido("No encuentro ese registro.")
        _no_firmado(conn, s["fecha"], s["turno"])
        conn.execute("DELETE FROM SalidasTurno WHERE id=?", (salida_id,))
        registrar_cambio(conn, "turno", "quitar", f"{NOMBRE_SALIDA.get(s['tipo'], s['tipo'])} turno {s['turno']} {s['fecha']}: {s['kg']:g} kg")
        conn.commit()
    finally:
        conn.close()


def anotar_merma(fecha: str, turno: str, producto: str, cantidad: float, unidad: str, motivo: str, costo: Optional[float] = None,
                 db_path: str = DB_PATH) -> Dict[str, Any]:
    """Merma pesada del turno (va a la tabla Mermas con su turno). Si no se da el costo, se calcula con el precio del producto."""
    from core.normalizar import motivo_canonico, nombre_canonico, unidad_canonica
    from data import proveedores as prov
    f = _validar_turno(fecha, turno)
    try:
        cant = round(float(cantidad), 3)
    except (TypeError, ValueError):
        raise DatoInvalido("La cantidad debe ser un número.") from None
    if not 0 < cant <= 100000:
        raise DatoInvalido("La cantidad debe ser mayor que cero.")
    if familia(unidad) is None:
        raise DatoInvalido("La unidad no es válida. Usa kg, g, l, ml, libra, qq o unidad.")
    if not (motivo or "").strip():
        raise DatoInvalido("Escribe el motivo de la merma.")
    conn = _conn(db_path)
    try:
        _no_firmado(conn, f, turno)
        pid = buscar_producto_id(conn, producto)
        nombre = conn.execute("SELECT nombre FROM Catalogo WHERE id=?", (pid,)).fetchone()[0] if pid else nombre_canonico(producto)
        if costo is None and pid:
            m = prov.mejor_precio_por_producto(conn).get(pid)
            eq = convertir(cant, unidad, m["unidad_precio"]) if m else None
            costo = round(eq * m["precio"], 2) if eq is not None else None
        mid = conn.execute("INSERT INTO Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado, turno) VALUES (?,?,?,?,?,?,?)",
                           (f, nombre, cant, unidad_canonica(unidad), motivo_canonico(motivo), costo or 0.0, turno)).lastrowid
        registrar_cambio(conn, "merma", "crear", f"Turno {turno} {f}: {cant:g} {unidad} de {nombre} ({motivo_canonico(motivo)})")
        conn.commit()
        return {"id": mid, "costo": costo}
    finally:
        conn.close()


# ---------------------------------------------------------------- el balance
def _kg_producto(conn: sqlite3.Connection) -> Dict[int, Optional[float]]:
    return {r[0]: r[1] for r in conn.execute("SELECT id, kg_por_unidad FROM Catalogo")}


def calcular(fecha: str, turno: str, producido: Optional[List[Dict[str, Any]]] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Balance del turno. `producido` = filas del informe [{receta_id, plato, producido, vendido, recibido?}]; si no se da,
    se usan las ventas registradas de ese turno."""
    from data import proveedores as prov
    from data.turnos import TURNOS
    f = _validar_turno(fecha, turno)
    conn = _conn(db_path)
    try:
        if producido is None:
            servicios = TURNOS[turno]
            producido = [{"receta_id": r["receta_id"], "plato": r["plato"], "producido": r["producido"], "vendido": r["vendido"]}
                         for r in conn.execute("SELECT receta_id, plato, producido, vendido, servicio FROM Ventas WHERE fecha=?", (f,))
                         if clave(r["servicio"]) in servicios]
        kgu = _kg_producto(conn)
        nombres = {r[0]: r[1] for r in conn.execute("SELECT id, nombre FROM Catalogo")}
        mejores = prov.mejor_precio_por_producto(conn)
        movs = conn.execute("SELECT * FROM MovimientosTurno WHERE fecha=? AND turno=? ORDER BY id", (f, turno)).fetchall()
        salidas = conn.execute("SELECT s.*, c.nombre AS producto FROM SalidasTurno s LEFT JOIN Catalogo c ON c.id=s.producto_id "
                               "WHERE s.fecha=? AND s.turno=? ORDER BY s.id", (f, turno)).fetchall()
        mermas = conn.execute("SELECT id, producto, cantidad, unidad, motivo, costo_estimado FROM Mermas WHERE fecha=? AND turno=? ORDER BY id",
                              (f, turno)).fetchall()
        mermas_sin_turno = conn.execute("SELECT count(*), round(coalesce(sum(costo_estimado),0),2) FROM Mermas WHERE fecha=? AND turno IS NULL",
                                        (f,)).fetchone()
        ingredientes = {}
        for p in producido:
            rid = p.get("receta_id")
            if rid and rid not in ingredientes:
                ingredientes[rid] = conn.execute("SELECT producto_id, ingrediente, cantidad, unidad FROM RecetaIngredientes WHERE receta_id=?",
                                                 (rid,)).fetchall()
        est = {r["receta_id"]: dict(r) for r in conn.execute("SELECT * FROM EstandaresReceta")}
    finally:
        conn.close()

    avisos: List[str] = []
    sin_peso: set = set()

    # -- lo que entro (por producto, en kg)
    por_ing: Dict[int, Dict[str, Any]] = {}

    def fila(pid: int) -> Dict[str, Any]:
        return por_ing.setdefault(pid, {"producto_id": pid, "producto": nombres.get(pid, "?"), "entregado": 0.0, "devuelto": 0.0,
                                        "uso_receta": 0.0, "merma": 0.0, "calculable": True})

    for m in movs:
        kg = a_kg(m["cantidad"], m["unidad"], kgu.get(m["producto_id"]))
        if kg is None:
            sin_peso.add(nombres.get(m["producto_id"], "?"))
            fila(m["producto_id"])["calculable"] = False
            continue
        fila(m["producto_id"])["entregado" if m["tipo"] == "entrega" else "devuelto"] += kg

    # -- lo que se uso segun receta, lo bueno que salio y la perdida normal (por plato)
    platos: List[Dict[str, Any]] = []
    salio_bueno = perdida_normal = suma_tol = suma_peso_tol = 0.0
    for p in producido:
        rid = p.get("receta_id")
        unidades = int(p.get("producido") or 0)
        e = est.get(rid) or {}
        perd = float(e.get("perdida_normal_pct", PERDIDA_NORMAL_DEFECTO)) / 100
        tol = float(e.get("tolerancia_pct", TOLERANCIA_DEFECTO))
        masa_receta = 0.0  # kg de ingredientes por unidad
        faltan_pesos = False
        for ing in ingredientes.get(rid, []):
            if ing["producto_id"] is None:
                continue  # agua, hielo...
            kg = a_kg(ing["cantidad"], ing["unidad"], kgu.get(ing["producto_id"]))
            if kg is None:
                if familia(ing["unidad"]) == "unidad":
                    sin_peso.add(nombres.get(ing["producto_id"], ing["ingrediente"]))
                    faltan_pesos = True
                continue  # pizca, rama...: no suman
            masa_receta += kg
            fila(ing["producto_id"])["uso_receta"] += kg * unidades
        if e.get("peso_unidad_g"):
            bueno = unidades * e["peso_unidad_g"] / 1000
            origen = "peso por unidad"
        else:
            bueno = unidades * masa_receta * (1 - perd)
            origen = "peso de la receta"
        normal = bueno / (1 - perd) - bueno if perd < 1 else 0.0
        salio_bueno += bueno
        perdida_normal += normal
        suma_tol += tol * (bueno + normal)
        suma_peso_tol += bueno + normal
        rec = p.get("recibido")
        platos.append({"receta_id": rid, "plato": p.get("plato"), "producido": unidades, "vendido": int(p.get("vendido") or 0),
                       "recibido": int(rec) if rec is not None and rec != "" else None,
                       "perdidas_unidades": unidades - int(rec) if rec not in (None, "") else None,
                       "kg_bueno": round(bueno, 3), "kg_perdida_normal": round(normal, 3), "origen_peso": origen,
                       "perdida_normal_pct": round(perd * 100, 2), "tolerancia_pct": tol, "estandar_por_defecto": rid not in est,
                       "faltan_pesos": faltan_pesos})

    # -- lo anotado: merma pesada del turno + salidas
    merma_kg = 0.0
    lista_mermas = []
    por_nombre = {clave(n): i for i, n in nombres.items()}
    for m in mermas:
        pid = por_nombre.get(clave(m["producto"]))
        kg = a_kg(m["cantidad"], m["unidad"], kgu.get(pid) if pid else None)
        if kg is None:
            sin_peso.add(m["producto"])
        else:
            merma_kg += kg
            if pid:
                fila(pid)["merma"] += kg
        lista_mermas.append({"id": m["id"], "producto": m["producto"], "cantidad": m["cantidad"], "unidad": m["unidad"], "motivo": m["motivo"],
                             "kg": round(kg, 3) if kg is not None else None, "costo": m["costo_estimado"]})
    salidas_kg = {t: 0.0 for t in TIPOS_SALIDA}
    for s in salidas:
        salidas_kg[s["tipo"]] += s["kg"]
    anotado = merma_kg + sum(salidas_kg.values())

    entregado = sum(r["entregado"] for r in por_ing.values())
    devuelto = sum(r["devuelto"] for r in por_ing.values())
    entro = entregado - devuelto
    sin_explicar = entro - salio_bueno - perdida_normal - anotado
    tolerancia = round(suma_tol / suma_peso_tol, 2) if suma_peso_tol else TOLERANCIA_DEFECTO
    pct = sin_explicar / entro * 100 if entro else None

    # costo promedio por kg de lo entregado (precio mas barato vigente)
    valor_entregado = kg_valorados = 0.0
    for m in movs:
        if m["tipo"] != "entrega":
            continue
        mejor = mejores.get(m["producto_id"])
        kg = a_kg(m["cantidad"], m["unidad"], kgu.get(m["producto_id"]))
        eq = convertir(m["cantidad"], m["unidad"], mejor["unidad_precio"]) if mejor else None
        if mejor and kg and eq is not None:
            valor_entregado += eq * mejor["precio"]
            kg_valorados += kg
    costo_kg = valor_entregado / kg_valorados if kg_valorados else None

    # -- por ingrediente
    lineas = []
    for r in por_ing.values():
        neto = r["entregado"] - r["devuelto"]
        dif = neto - r["uso_receta"] - r["merma"]
        mejor = mejores.get(r["producto_id"])
        precio_kg = None
        if mejor:
            un_kg = a_kg(1, mejor["unidad_precio"], kgu.get(r["producto_id"]))
            precio_kg = mejor["precio"] / un_kg if un_kg else None
        lineas.append({**r, "entregado": round(r["entregado"], 3), "devuelto": round(r["devuelto"], 3), "uso_receta": round(r["uso_receta"], 3),
                       "merma": round(r["merma"], 3), "neto": round(neto, 3), "diferencia": round(dif, 3),
                       "diferencia_pct": round(dif / r["uso_receta"] * 100, 1) if r["uso_receta"] else None,
                       "valor_diferencia": round(dif * precio_kg, 2) if precio_kg is not None else None,
                       "sin_entrega": r["uso_receta"] > 0 and neto <= 0})
    # diferencia positiva = se entrego mas de lo que se uso y se anoto = FALTA. Primero lo que mas dinero pierde.
    lineas.sort(key=lambda l: -(l["valor_diferencia"] if l["valor_diferencia"] is not None else 0))

    # -- estado y mensajes
    if not movs:
        estado = "sin_entregas"
    elif pct is None:
        estado = "sin_datos"
    elif abs(pct) > tolerancia:
        estado = "alarma"
    elif abs(pct) > tolerancia * 0.75:
        estado = "cerca"
    else:
        estado = "bien"
    mensajes: List[str] = []
    if estado == "sin_entregas":
        mensajes.append("Bodega no ha anotado entregas para este turno: sin eso no hay balance. Anota lo que se entregó a producción.")
    else:
        lado = "faltan" if sin_explicar > 0 else "sobran"  # sin explicar > 0: entro mas de lo que se explica
        dinero_txt = f" (unos {dinero(abs(sin_explicar) * costo_kg)})" if costo_kg else ""
        mensajes.append(f"Entraron {_n(entro)} kg y se explican {_n(entro - sin_explicar)} kg: {lado} {_n(abs(sin_explicar))} kg"
                        f"{dinero_txt}, el {_n(abs(pct or 0))} % de lo que entró.")
        if estado == "alarma":
            mensajes.append(f"ALARMA: pasa la tolerancia de {tolerancia:g} %." + (" Revisa los ingredientes de abajo: el primero es donde más se pierde."
                                                                                    if sin_explicar > 0 else " Revisa si la receta pide más de lo que se usa de verdad."))
        peor = next((l for l in lineas if (l["valor_diferencia"] or 0) > 0), None)
        if peor and sin_explicar > 0:
            mensajes.append(f"El ingrediente con más faltante es {peor['producto']}: {_n(abs(peor['diferencia']))} kg ({dinero(abs(peor['valor_diferencia']))}).")
    faltan_entrega = [l["producto"] for l in lineas if l["sin_entrega"]]
    if movs and faltan_entrega:
        mensajes.append(f"Las recetas usaron productos que bodega no entregó: {', '.join(faltan_entrega[:5])}" + ("…" if len(faltan_entrega) > 5 else "") +
                        ". Puede faltar anotar una entrega.")
    if sin_peso:
        avisos.append("Falta el peso por unidad de: " + ", ".join(sorted(sin_peso)) + ". Esas líneas no suman.")
    if mermas_sin_turno[0]:
        avisos.append(f"Hay {mermas_sin_turno[0]} mermas del día sin turno ({dinero(mermas_sin_turno[1])}): no entran en ningún balance.")
    if any(pl["estandar_por_defecto"] for pl in platos):
        avisos.append(f"Algunas recetas usan el estándar por defecto ({PERDIDA_NORMAL_DEFECTO:g} % de pérdida, {TOLERANCIA_DEFECTO:g} % de tolerancia): mídelo en tu cocina.")

    redondo = lambda x: round(x, 3)  # noqa: E731
    return {
        "fecha": f, "turno": turno, "estado": estado,
        "kg": {"entregado": redondo(entregado), "devuelto": redondo(devuelto), "entro": redondo(entro), "salio_bueno": redondo(salio_bueno),
               "perdida_normal": redondo(perdida_normal), "merma": redondo(merma_kg), **{k: redondo(v) for k, v in salidas_kg.items()},
               "anotado": redondo(anotado), "sin_explicar": redondo(sin_explicar)},
        "sin_explicar_pct": round(pct, 2) if pct is not None else None, "tolerancia_pct": tolerancia,
        "costo_kg": round(costo_kg, 4) if costo_kg else None,
        "sin_explicar_dinero": round(sin_explicar * costo_kg, 2) if costo_kg else None,
        "por_ingrediente": lineas, "por_plato": platos,
        "unidades": {"producido": sum(pl["producido"] for pl in platos), "vendido": sum(pl["vendido"] for pl in platos),
                     "recibido": sum(pl["recibido"] for pl in platos if pl["recibido"] is not None) if any(pl["recibido"] is not None for pl in platos) else None,
                     "perdidas": sum(pl["perdidas_unidades"] for pl in platos if pl["perdidas_unidades"] is not None)
                     if any(pl["perdidas_unidades"] is not None for pl in platos) else None},
        "movimientos": [{"id": m["id"], "tipo": m["tipo"], "producto": nombres.get(m["producto_id"]), "cantidad": m["cantidad"], "unidad": m["unidad"],
                         "entrego": m["entrego"], "recibio": m["recibio"], "es_demo": m["es_demo"]} for m in movs],
        "salidas": [{"id": s["id"], "tipo": s["tipo"], "nombre_tipo": NOMBRE_SALIDA[s["tipo"]], "kg": s["kg"], "producto": s["producto"],
                     "nota": s["nota"], "persona": s["persona"]} for s in salidas],
        "mermas": lista_mermas, "mensajes": mensajes, "avisos": avisos,
    }


def tendencia(desde: Optional[str] = None, hasta: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Sin explicar por dia y turno (solo turnos con entregas de bodega). Para ver si siempre falla el mismo turno."""
    conn = _conn(db_path)
    try:
        pares = conn.execute("SELECT DISTINCT fecha, turno FROM MovimientosTurno WHERE fecha BETWEEN ? AND ? ORDER BY fecha, turno",
                             (desde or "0000-01-01", hasta or "9999-12-31")).fetchall()
        firmados = {(r["fecha"], r["turno"]): r for r in conn.execute("SELECT fecha, turno, producido, datos_json, estado FROM InformesTurno")}
    finally:
        conn.close()
    import json
    filas = []
    for p in pares:
        inf = firmados.get((p["fecha"], p["turno"]))
        b = None
        if inf and inf["estado"] == "firmado" and inf["datos_json"]:
            b = (json.loads(inf["datos_json"]) or {}).get("balance")
        if b is None:
            prod = json.loads(inf["producido"]) if inf and inf["producido"] else None
            b = calcular(p["fecha"], p["turno"], prod, db_path)
        filas.append({"fecha": p["fecha"], "turno": p["turno"], "estado": b["estado"], "entro_kg": b["kg"]["entro"],
                      "sin_explicar_kg": b["kg"]["sin_explicar"], "sin_explicar_pct": b["sin_explicar_pct"], "tolerancia_pct": b["tolerancia_pct"],
                      "sin_explicar_dinero": b["sin_explicar_dinero"]})
    por_turno: Dict[str, List[float]] = {}
    for f in filas:
        if f["sin_explicar_pct"] is not None:
            por_turno.setdefault(f["turno"], []).append(f["sin_explicar_pct"])
    resumen = [{"turno": t, "turnos": len(v), "promedio_pct": round(sum(v) / len(v), 2), "alarmas": sum(1 for x in filas if x["turno"] == t and x["estado"] == "alarma")}
               for t, v in por_turno.items()]
    resumen.sort(key=lambda r: -r["promedio_pct"])  # primero el turno que mas pierde
    mensajes = []
    alarmas = [f for f in filas if f["estado"] == "alarma"]
    if not filas:
        mensajes.append("Aún no hay turnos con entregas de bodega anotadas.")
    else:
        mensajes.append(f"{len(alarmas)} de {len(filas)} turnos pasaron su tolerancia.")
        if resumen and resumen[0]["promedio_pct"] > 0:
            r = resumen[0]
            nombre = {"matutino": "mañana", "vespertino": "tarde", "nocturno": "noche"}.get(r["turno"], r["turno"])
            mensajes.append(f"El turno de la {nombre} es el que más pierde en promedio: {_n(abs(r['promedio_pct']))} % sin explicar.")
        dinero_total = sum(f["sin_explicar_dinero"] or 0 for f in filas if (f["sin_explicar_dinero"] or 0) > 0)
        if dinero_total:
            mensajes.append(f"En total faltan unos {dinero(dinero_total)} sin explicar en estos turnos.")
    return {"turnos": filas, "por_turno": resumen, "mensajes": mensajes}
