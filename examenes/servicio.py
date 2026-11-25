"""Logica de examenes: banco de preguntas, intentos, notas y reportes.

Sin IA aqui: la nota es una cuenta exacta y repetible.
Diseno: docs/DISENO_EXAMENES.md
"""

from __future__ import annotations

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.normalizar import clave

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
NOTA_MINIMA = 80.0
INTENTOS_EVALUACION = 2
N_DEFECTO = 10
MINUTOS_EVALUACION = 15
FMT = "%Y-%m-%d %H:%M:%S"

MSG_SIN_INTENTOS = "Ya usaste tus {n} intentos. Habla con tu encargado."
MSG_SIN_PREGUNTAS = "Este tema aún no tiene preguntas aprobadas."


class ExamenError(ValueError):
    """Error que se puede mostrar tal cual al usuario."""


def _conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS PreguntasExamen (
            id INTEGER PRIMARY KEY, tema TEXT NOT NULL, tipo TEXT NOT NULL DEFAULT 'opcion',
            enunciado TEXT NOT NULL, opciones TEXT NOT NULL, correcta INTEGER NOT NULL,
            explicacion TEXT, documento TEXT, seccion TEXT, puntaje_jev REAL,
            estado TEXT NOT NULL DEFAULT 'pendiente', clave_enunciado TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS Intentos (
            id INTEGER PRIMARY KEY, id_empleado TEXT NOT NULL, tema TEXT NOT NULL, modo TEXT NOT NULL,
            preguntas TEXT NOT NULL, inicio TEXT NOT NULL, fin TEXT, minutos INTEGER,
            nota REAL, aprobado INTEGER);
        CREATE TABLE IF NOT EXISTS RespuestasExamen (
            intento_id INTEGER NOT NULL, pregunta_id INTEGER NOT NULL, elegida INTEGER,
            correcta INTEGER, PRIMARY KEY (intento_id, pregunta_id));
        """
    )
    return conn


# ---------------------------------------------------------------- banco
def guardar_pregunta(tema: str, enunciado: str, opciones: List[str], correcta: int, explicacion: str = "",
                     documento: str = "", seccion: str = "", puntaje_jev: Optional[float] = None,
                     estado: str = "pendiente", db_path: str = DB_PATH) -> Optional[int]:
    """Guarda una pregunta. Devuelve None si ya existia (mismo enunciado)."""
    if len(opciones) != 4 or not 0 <= correcta < 4 or len({clave(o) for o in opciones}) != 4:
        raise ExamenError("La pregunta necesita 4 opciones distintas y una correcta.")
    conn = _conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO PreguntasExamen (tema, enunciado, opciones, correcta, explicacion, documento, seccion,"
            " puntaje_jev, estado, clave_enunciado) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (tema, enunciado.strip(), json.dumps(opciones, ensure_ascii=False), correcta, explicacion,
             documento, seccion, puntaje_jev, estado, clave(enunciado)))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def _pregunta_dict(r: sqlite3.Row) -> Dict[str, Any]:
    d = dict(r)
    d["opciones"] = json.loads(d["opciones"])
    d.pop("clave_enunciado", None)
    return d


def listar_preguntas(estado: Optional[str] = None, tema: Optional[str] = None, db_path: str = DB_PATH):
    conn = _conn(db_path)
    sql, args = "SELECT * FROM PreguntasExamen WHERE 1=1", []
    if estado:
        sql += " AND estado=?"; args.append(estado)
    if tema:
        sql += " AND tema=?"; args.append(tema)
    try:
        return [_pregunta_dict(r) for r in conn.execute(sql + " ORDER BY puntaje_jev DESC, id", args)]
    finally:
        conn.close()


def cambiar_estado(pregunta_id: int, estado: str, editado: Optional[Dict[str, Any]] = None, db_path: str = DB_PATH):
    if estado not in ("aprobada", "retirada", "pendiente", "revisar"):
        raise ExamenError("Estado no válido.")
    conn = _conn(db_path)
    try:
        if editado:
            ops = editado.get("opciones")
            if ops is not None and (len(ops) != 4 or len({clave(o) for o in ops}) != 4):
                raise ExamenError("La pregunta necesita 4 opciones distintas.")
            conn.execute(
                "UPDATE PreguntasExamen SET enunciado=coalesce(?,enunciado), opciones=coalesce(?,opciones),"
                " correcta=coalesce(?,correcta), explicacion=coalesce(?,explicacion) WHERE id=?",
                (editado.get("enunciado"), json.dumps(ops, ensure_ascii=False) if ops else None,
                 editado.get("correcta"), editado.get("explicacion"), pregunta_id))
        n = conn.execute("UPDATE PreguntasExamen SET estado=? WHERE id=?", (estado, pregunta_id)).rowcount
        if not n:
            raise ExamenError("No existe esa pregunta.")
        conn.commit()
    finally:
        conn.close()


def temas(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = _conn(db_path)
    try:
        return [dict(r) for r in conn.execute(
            "SELECT tema, sum(estado='aprobada') AS aprobadas, sum(estado='pendiente') AS pendientes "
            "FROM PreguntasExamen GROUP BY tema ORDER BY tema")]
    finally:
        conn.close()


# ---------------------------------------------------------------- intentos
def _publica(p: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Pregunta para mostrar al trabajador: SIN la respuesta, opciones mezcladas."""
    ops = [{"i": i, "texto": t} for i, t in enumerate(p["opciones"])]
    rng.shuffle(ops)
    return {"id": p["id"], "enunciado": p["enunciado"], "opciones": ops}


def iniciar_intento(id_empleado: str, tema: str, modo: str, n: int = N_DEFECTO, db_path: str = DB_PATH,
                    semilla: Optional[int] = None) -> Dict[str, Any]:
    if modo not in ("practica", "evaluacion"):
        raise ExamenError("Elige práctica o evaluación.")
    conn = _conn(db_path)
    try:
        if not conn.execute("SELECT 1 FROM Trabajadores WHERE id_empleado=?", (id_empleado,)).fetchone():
            raise ExamenError("No encuentro a esa persona.")
        if modo == "evaluacion":
            usados = conn.execute("SELECT count(*) FROM Intentos WHERE id_empleado=? AND tema=? AND modo='evaluacion'"
                                  " AND fin IS NOT NULL", (id_empleado, tema)).fetchone()[0]
            if usados >= INTENTOS_EVALUACION:
                raise ExamenError(MSG_SIN_INTENTOS.format(n=INTENTOS_EVALUACION))
        pregs = [_pregunta_dict(r) for r in conn.execute(
            "SELECT * FROM PreguntasExamen WHERE tema=? AND estado='aprobada'", (tema,))]
        if not pregs:
            raise ExamenError(MSG_SIN_PREGUNTAS)
        rng = random.Random(semilla)
        rng.shuffle(pregs)
        pregs = pregs[:n]
        minutos = MINUTOS_EVALUACION if modo == "evaluacion" else None
        cur = conn.execute(
            "INSERT INTO Intentos (id_empleado, tema, modo, preguntas, inicio, minutos) VALUES (?,?,?,?,?,?)",
            (id_empleado, tema, modo, json.dumps([p["id"] for p in pregs]), datetime.now().strftime(FMT), minutos))
        conn.commit()
        return {"intento_id": cur.lastrowid, "modo": modo, "minutos": minutos,
                "preguntas": [_publica(p, rng) for p in pregs]}
    finally:
        conn.close()


def _intento(conn, intento_id: int) -> sqlite3.Row:
    r = conn.execute("SELECT * FROM Intentos WHERE id=?", (intento_id,)).fetchone()
    if not r:
        raise ExamenError("No existe ese intento.")
    if r["fin"]:
        raise ExamenError("Este examen ya terminó.")
    return r


def responder(intento_id: int, pregunta_id: int, elegida: int, db_path: str = DB_PATH) -> Dict[str, Any]:
    conn = _conn(db_path)
    try:
        it = _intento(conn, intento_id)
        if pregunta_id not in json.loads(it["preguntas"]):
            raise ExamenError("Esa pregunta no es de este examen.")
        p = _pregunta_dict(conn.execute("SELECT * FROM PreguntasExamen WHERE id=?", (pregunta_id,)).fetchone())
        ok = int(elegida == p["correcta"])
        conn.execute("INSERT OR REPLACE INTO RespuestasExamen VALUES (?,?,?,?)", (intento_id, pregunta_id, elegida, ok))
        conn.commit()
        if it["modo"] == "practica":
            return {"correcta": bool(ok), "respuesta_correcta": p["correcta"], "explicacion": p["explicacion"],
                    "fuente": f"{p['documento']}, {p['seccion']}"}
        return {"guardada": True}
    finally:
        conn.close()


def cerrar_intento(intento_id: int, db_path: str = DB_PATH) -> Dict[str, Any]:
    conn = _conn(db_path)
    try:
        it = _intento(conn, intento_id)
        ids = json.loads(it["preguntas"])
        resp = {r["pregunta_id"]: r["correcta"] for r in conn.execute(
            "SELECT pregunta_id, correcta FROM RespuestasExamen WHERE intento_id=?", (intento_id,))}
        # tiempo agotado: lo no respondido cuenta como mal (solo se detecta aqui)
        aciertos = sum(1 for i in ids if resp.get(i) == 1)
        nota = round(100.0 * aciertos / len(ids), 1) if ids else 0.0
        aprobado = int(nota >= NOTA_MINIMA) if it["modo"] == "evaluacion" else None
        conn.execute("UPDATE Intentos SET fin=?, nota=?, aprobado=? WHERE id=?",
                     (datetime.now().strftime(FMT), nota, aprobado, intento_id))
        conn.commit()
        falladas = [{"pregunta": p["enunciado"], "fuente": f"{p['documento']}, {p['seccion']}",
                     "explicacion": p["explicacion"], "respuesta_correcta": p["opciones"][p["correcta"]]}
                    for p in (_pregunta_dict(conn.execute("SELECT * FROM PreguntasExamen WHERE id=?", (i,)).fetchone())
                              for i in ids if resp.get(i) != 1)]
        tarde = bool(it["minutos"] and datetime.now() - datetime.strptime(it["inicio"], FMT) > timedelta(minutes=it["minutos"] + 1))
        return {"nota": nota, "aprobado": bool(aprobado) if aprobado is not None else None, "aciertos": aciertos,
                "total": len(ids), "nota_minima": NOTA_MINIMA, "fuera_de_tiempo": tarde, "falladas": falladas}
    finally:
        conn.close()


def reporte(db_path: str = DB_PATH) -> Dict[str, Any]:
    conn = _conn(db_path)
    try:
        por_persona = [dict(r) for r in conn.execute(
            "SELECT t.id_empleado, t.nombre_completo AS nombre, i.tema, count(*) AS intentos, max(i.nota) AS mejor_nota,"
            " max(i.aprobado) AS aprobado FROM Intentos i JOIN Trabajadores t ON t.id_empleado=i.id_empleado "
            "WHERE i.modo='evaluacion' AND i.fin IS NOT NULL GROUP BY t.id_empleado, i.tema ORDER BY t.nombre_completo")]
        mas_falladas = [dict(r) for r in conn.execute(
            "SELECT p.enunciado, p.documento, p.seccion, count(*) AS fallos FROM RespuestasExamen r "
            "JOIN PreguntasExamen p ON p.id=r.pregunta_id WHERE r.correcta=0 GROUP BY p.id ORDER BY fallos DESC LIMIT 5")]
        return {"por_persona": por_persona, "mas_falladas": mas_falladas}
    finally:
        conn.close()
