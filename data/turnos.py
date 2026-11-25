"""Informe del turno para el gerente (etapa F).

El chef abre el informe de una fecha y un turno. El programa llena solo lo que ya esta en la base
(producido y vendido, merma del dia, sobrantes, compras recibidas, personal del turno, incidencias)
y el chef completa: quien fue el chef, quienes trabajaron, lo producido si no esta registrado,
incidencias y observaciones. Al FIRMAR se guarda una foto de los numeros y el informe ya no cambia.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.normalizar import clave
from data.esquema import asegurar_esquema, registrar_cambio
from data.proveedores import DatoInvalido

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
TURNOS: Dict[str, tuple] = {"matutino": ("desayuno", "almuerzo"), "vespertino": ("merienda", "cena"), "nocturno": ()}
NOMBRE_TURNO = {"matutino": "Mañana", "vespertino": "Tarde", "nocturno": "Noche"}
TIPOS_INCIDENCIA = ("equipo", "personal", "proveedor", "cliente", "seguridad", "higiene", "otro")
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MAX_TEXTO = 1000


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _validar(fecha: str, turno: str) -> str:
    if turno not in TURNOS:
        raise DatoInvalido("El turno debe ser matutino, vespertino o nocturno.")
    try:
        f = date.fromisoformat(str(fecha)).isoformat()
    except ValueError:
        raise DatoInvalido("La fecha no es válida (usa año-mes-día).") from None
    if f > date.today().isoformat():
        raise DatoInvalido("No se puede hacer el informe de un día que aún no llega.")
    return f


def _descansa(texto: Optional[str], dia: int) -> bool:
    """'Sabado-Domingo', 'lunes-martes', 'Martes-Miercoles', 'Lunes' -> ¿ese dia de la semana descansa?"""
    partes = [p for p in re.split(r"[-,/ y]+", clave(texto)) if p]
    return DIAS[dia] in partes


def personal_del_turno(fecha: str, turno: str, db_path: str = DB_PATH) -> Dict[str, List[Dict[str, Any]]]:
    """Quienes deberian estar ese dia en ese turno, quienes descansan y quienes estan ausentes (permiso, reposo...)."""
    dia = date.fromisoformat(fecha).weekday()
    conn = _conn(db_path)
    try:
        filas = conn.execute("SELECT id_empleado, nombre_completo, cargo, turno, estado, fecha_inicio_ausencia, fecha_fin_ausencia, "
                             "motivo_ausencia, dias_descanso FROM Trabajadores ORDER BY nombre_completo").fetchall()
    finally:
        conn.close()
    trabajan, descansan, ausentes = [], [], []
    for t in filas:
        if clave(t["turno"]) != turno:
            continue
        p = {"id_empleado": t["id_empleado"], "nombre": t["nombre_completo"], "cargo": t["cargo"]}
        ini, fin = t["fecha_inicio_ausencia"], t["fecha_fin_ausencia"]
        if ini and fin and ini <= fecha <= fin:
            ausentes.append({**p, "motivo": t["motivo_ausencia"] or (t["estado"] or "").replace("_", " "), "hasta": fin})
        elif _descansa(t["dias_descanso"], dia):
            descansan.append(p)
        else:
            trabajan.append(p)
    return {"trabajan": trabajan, "descansan": descansan, "ausentes": ausentes}


def chefs(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        return [{"id_empleado": r[0], "nombre": r[1], "cargo": r[2]} for r in conn.execute(
            "SELECT id_empleado, nombre_completo, cargo FROM Trabajadores ORDER BY nombre_completo")
            if re.search(r"chef|cocin|jefe|sous|paste|repost", clave(r[2]))]
    finally:
        conn.close()


def datos_automaticos(fecha: str, turno: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Todo lo que la base ya sabe de ese dia y turno."""
    from data import recetas as rec
    costos = {r["id_receta"]: r["costo_plato"] for r in rec.listar(db_path=db_path)}
    servicios = TURNOS[turno]
    conn = _conn(db_path)
    try:
        ventas = conn.execute("SELECT servicio, plato, receta_id, producido, vendido, precio_unitario FROM Ventas WHERE fecha=? ORDER BY servicio, plato",
                              (fecha,)).fetchall()
        mermas = conn.execute("SELECT producto, cantidad, unidad, motivo, costo_estimado FROM Mermas WHERE fecha=? ORDER BY costo_estimado DESC",
                              (fecha,)).fetchall()
        sobr = conn.execute("SELECT id_sobrante, producto_sopro, cantidad, unidad, turno, destino_actual, valor_estimado, fecha_registro, fecha_destino "
                            "FROM SobrantesReutilizables WHERE fecha_registro=? OR fecha_destino=?", (fecha, fecha)).fetchall()
        compras = conn.execute("SELECT p.nombre AS proveedor, k.nombre AS producto, c.cantidad, c.unidad, c.total FROM Compras c "
                               "JOIN Proveedores p ON p.id=c.proveedor_id JOIN Catalogo k ON k.id=c.producto_id WHERE c.fecha=? ORDER BY c.id", (fecha,)).fetchall()
        bitacora = conn.execute("SELECT categoria, descripcion, timestamp FROM Bitacora_Diaria WHERE date(timestamp)=? ORDER BY id", (fecha,)).fetchall()
    finally:
        conn.close()
    producido = [{"receta_id": v["receta_id"], "plato": v["plato"], "servicio": v["servicio"], "producido": v["producido"], "vendido": v["vendido"],
                  "costo_plato": costos.get(v["receta_id"])} for v in ventas if clave(v["servicio"]) in servicios]
    merma_total = round(sum(m["costo_estimado"] or 0 for m in mermas), 2)
    recuperado = [s for s in sobr if s["destino_actual"] == "reutilizado" and s["fecha_destino"] == fecha and (not s["turno"] or clave(s["turno"]) == turno)]
    nuevos = [s for s in sobr if s["fecha_registro"] == fecha and (not s["turno"] or clave(s["turno"]) == turno)]
    return {
        "producido": producido,
        "mermas": [dict(m) for m in mermas], "merma_total": merma_total,
        "nota_merma": "Las mermas no se anotan por turno: aquí salen todas las del día." if mermas else None,
        "recuperado": [{"producto": s["producto_sopro"], "cantidad": s["cantidad"], "unidad": s["unidad"], "valor": s["valor_estimado"]} for s in recuperado],
        "recuperado_total": round(sum(s["valor_estimado"] or 0 for s in recuperado), 2),
        "sobrantes_nuevos": [{"producto": s["producto_sopro"], "cantidad": s["cantidad"], "unidad": s["unidad"], "destino": s["destino_actual"]} for s in nuevos],
        "compras": [dict(c) for c in compras], "compras_total": round(sum(c["total"] for c in compras), 2),
        "incidencias_registradas": [{"tipo": b["categoria"], "descripcion": b["descripcion"], "hora": str(b["timestamp"])[11:16]} for b in bitacora],
        "personal": personal_del_turno(fecha, turno, db_path),
    }


def _fila(conn: sqlite3.Connection, fecha: str, turno: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM InformesTurno WHERE fecha=? AND turno=?", (fecha, turno)).fetchone()


def _cargar(r: sqlite3.Row) -> Dict[str, Any]:
    def js(txt, defecto):
        try:
            return json.loads(txt) if txt else defecto
        except (TypeError, ValueError):
            return defecto
    return {"id": r["id"], "fecha": r["fecha"], "turno": r["turno"], "chef_id": r["chef_id"],
            "personal": [p for p in (r["personal"] or "").split(",") if p], "producido": js(r["producido"], None),
            "incidencias": js(r["incidencias"], []), "observaciones": r["observaciones"] or "", "estado": r["estado"],
            "firmado_por": r["firmado_por"], "firmado_en": r["firmado_en"], "datos": js(r["datos_json"], None), "actualizado": r["actualizado"]}


def _totales(producido: List[Dict[str, Any]], datos: Dict[str, Any]) -> Dict[str, Any]:
    prod = sum(int(p.get("producido") or 0) for p in producido)
    vend = sum(int(p.get("vendido") or 0) for p in producido)
    costo_sobra = round(sum((int(p.get("producido") or 0) - int(p.get("vendido") or 0)) * (p.get("costo_plato") or 0) for p in producido), 2)
    return {"platos_producidos": prod, "platos_vendidos": vend, "platos_sobrantes": prod - vend, "costo_sobrante": costo_sobra,
            "merma": datos["merma_total"], "recuperado": datos["recuperado_total"], "compras": datos["compras_total"]}


def abrir(fecha: str, turno: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    """El informe de ese dia y turno: lo guardado (si hay) + los datos de la base. Si esta firmado, se devuelve la foto."""
    f = _validar(fecha, turno)
    conn = _conn(db_path)
    try:
        r = _fila(conn, f, turno)
    finally:
        conn.close()
    guardado = _cargar(r) if r else None
    if guardado and guardado["estado"] == "firmado" and guardado["datos"]:
        datos = guardado["datos"]
    else:
        datos = datos_automaticos(f, turno, db_path)
    producido = guardado["producido"] if guardado and guardado["producido"] is not None else datos["producido"]
    if not (guardado and guardado["estado"] == "firmado" and datos.get("balance")):
        from data import balance
        datos = {**datos, "balance": balance.calcular(f, turno, producido, db_path)}
    personal = guardado["personal"] if guardado and guardado["personal"] else [p["id_empleado"] for p in datos["personal"]["trabajan"]]
    return {"fecha": f, "turno": turno, "nombre_turno": NOMBRE_TURNO[turno], "servicios": list(TURNOS[turno]),
            "id": guardado["id"] if guardado else None, "estado": guardado["estado"] if guardado else "nuevo",
            "chef_id": guardado["chef_id"] if guardado else None, "personal": personal, "producido": producido,
            "producido_editado": bool(guardado and guardado["producido"] is not None),
            "incidencias": guardado["incidencias"] if guardado else [], "observaciones": guardado["observaciones"] if guardado else "",
            "firmado_por": guardado["firmado_por"] if guardado else None, "firmado_en": guardado["firmado_en"] if guardado else None,
            "datos": datos, "totales": _totales(producido, datos), "chefs": chefs(db_path), "tipos_incidencia": list(TIPOS_INCIDENCIA)}


def _limpiar_producido(producido: Optional[Iterable[Dict[str, Any]]], db_path: str) -> Optional[List[Dict[str, Any]]]:
    if producido is None:
        return None
    from data import recetas as rec
    costos = {r["id_receta"]: (r["nombre"], r["costo_plato"]) for r in rec.listar(db_path=db_path)}
    out = []
    for p in producido:
        try:
            prod, vend = int(p.get("producido") or 0), int(p.get("vendido") or 0)
        except (TypeError, ValueError):
            raise DatoInvalido("Producido y vendido deben ser números enteros.") from None
        if prod < 0 or vend < 0 or prod > 100000:
            raise DatoInvalido("Producido y vendido deben ser números entre 0 y 100000.")
        if vend > prod:
            raise DatoInvalido(f"«{p.get('plato')}»: no se pueden vender más platos de los que se produjeron.")
        rec_txt = p.get("recibido")
        recibido = None
        if rec_txt not in (None, ""):
            try:
                recibido = int(rec_txt)
            except (TypeError, ValueError):
                raise DatoInvalido("Lo recibido debe ser un número entero.") from None
            if not 0 <= recibido <= prod:
                raise DatoInvalido(f"«{p.get('plato')}»: lo recibido debe estar entre 0 y lo producido.")
        rid = p.get("receta_id")
        nombre, costo = costos.get(rid, (" ".join(str(p.get("plato") or "").split()), None))
        if not nombre:
            raise DatoInvalido("Cada plato necesita un nombre.")
        out.append({"receta_id": rid if rid in costos else None, "plato": nombre, "servicio": p.get("servicio"),
                    "producido": prod, "vendido": vend, "recibido": recibido, "costo_plato": costo})
    return out


def guardar(fecha: str, turno: str, chef_id: Optional[str] = None, personal: Optional[List[str]] = None,
            producido: Optional[List[Dict[str, Any]]] = None, incidencias: Optional[List[Dict[str, Any]]] = None,
            observaciones: str = "", db_path: str = DB_PATH) -> Dict[str, Any]:
    """Guarda el borrador. Un informe firmado no se puede cambiar."""
    f = _validar(fecha, turno)
    obs = (observaciones or "").strip()
    if len(obs) > MAX_TEXTO:
        raise DatoInvalido(f"Las observaciones pueden tener hasta {MAX_TEXTO} letras.")
    inc = []
    for i in incidencias or []:
        tipo = clave(i.get("tipo") or "otro")
        desc = " ".join(str(i.get("descripcion") or "").split())
        if tipo not in TIPOS_INCIDENCIA:
            raise DatoInvalido(f"Tipo de incidencia no válido: {i.get('tipo')}.")
        if not desc:
            raise DatoInvalido("Cada incidencia necesita una descripción.")
        inc.append({"tipo": tipo, "descripcion": desc[:MAX_TEXTO]})
    prod = _limpiar_producido(producido, db_path)
    conn = _conn(db_path)
    try:
        ids = {r[0] for r in conn.execute("SELECT id_empleado FROM Trabajadores")}
        if chef_id and chef_id not in ids:
            raise DatoInvalido("No encuentro a ese chef en el personal.")
        pers = list(dict.fromkeys(personal or []))
        malos = [p for p in pers if p not in ids]
        if malos:
            raise DatoInvalido("No encuentro a estas personas en el personal: " + ", ".join(malos) + ".")
        r = _fila(conn, f, turno)
        if r and r["estado"] == "firmado":
            raise DatoInvalido("Este informe ya está firmado y no se puede cambiar.")
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        valores = (chef_id, ",".join(pers), json.dumps(prod, ensure_ascii=False) if prod is not None else None,
                   json.dumps(inc, ensure_ascii=False), obs, ahora)
        if r:
            conn.execute("UPDATE InformesTurno SET chef_id=?, personal=?, producido=?, incidencias=?, observaciones=?, actualizado=? WHERE id=?",
                         (*valores, r["id"]))
            iid = r["id"]
        else:
            iid = conn.execute("INSERT INTO InformesTurno (fecha, turno, chef_id, personal, producido, incidencias, observaciones, actualizado, estado) "
                               "VALUES (?,?,?,?,?,?,?,?, 'borrador')", (f, turno, *valores)).lastrowid
        conn.commit()
        return {"id": iid, "estado": "borrador"}
    finally:
        conn.close()


def firmar(fecha: str, turno: str, firmado_por: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Cierra el informe: guarda la foto de los numeros y pasa las incidencias a la bitacora."""
    f = _validar(fecha, turno)
    nombre = " ".join((firmado_por or "").split())
    if len(nombre) < 2:
        raise DatoInvalido("Escribe el nombre de quien firma.")
    inf = abrir(f, turno, db_path)
    if inf["estado"] == "nuevo":
        raise DatoInvalido("Primero guarda el informe.")
    if inf["estado"] == "firmado":
        raise DatoInvalido("Este informe ya está firmado.")
    if not inf["chef_id"]:
        raise DatoInvalido("Falta indicar quién fue el chef del turno.")
    if not inf["personal"]:
        raise DatoInvalido("Falta indicar quiénes trabajaron en el turno.")
    datos = dict(inf["datos"])
    datos["producido"] = inf["producido"]
    datos["totales"] = inf["totales"]
    conn = _conn(db_path)
    try:
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE InformesTurno SET estado='firmado', firmado_por=?, firmado_en=?, datos_json=? WHERE id=?",
                     (nombre, ahora, json.dumps(datos, ensure_ascii=False), inf["id"]))
        for i in inf["incidencias"]:
            conn.execute("INSERT INTO Bitacora_Diaria (timestamp, categoria, descripcion) VALUES (?,?,?)",
                         (f"{f} {ahora[11:]}", i["tipo"], f"[Turno {NOMBRE_TURNO[turno].lower()}] {i['descripcion']}"))
        registrar_cambio(conn, "informe", "crear", f"Informe del turno {NOMBRE_TURNO[turno].lower()} del {f} firmado por {nombre}")
        conn.commit()
    finally:
        conn.close()
    return {"id": inf["id"], "estado": "firmado", "firmado_en": ahora}


def listar(desde: Optional[str] = None, hasta: Optional[str] = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        nombres = {r[0]: r[1] for r in conn.execute("SELECT id_empleado, nombre_completo FROM Trabajadores")}
        filas = conn.execute("SELECT * FROM InformesTurno WHERE fecha BETWEEN ? AND ? ORDER BY fecha DESC, turno",
                             (desde or "0000-01-01", hasta or "9999-12-31")).fetchall()
    finally:
        conn.close()
    out = []
    for r in filas:
        d = _cargar(r)
        tot = (d["datos"] or {}).get("totales") if d["estado"] == "firmado" else None
        out.append({"id": d["id"], "fecha": d["fecha"], "turno": d["turno"], "nombre_turno": NOMBRE_TURNO.get(d["turno"], d["turno"]),
                    "chef": nombres.get(d["chef_id"]), "estado": d["estado"], "firmado_por": d["firmado_por"], "firmado_en": d["firmado_en"],
                    "n_incidencias": len(d["incidencias"]), "totales": tot})
    return out
