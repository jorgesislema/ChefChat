"""RAG de documentos y capacitaciones (manuales, protocolos, BPM).

Cortes por seccion + buscador de texto SQLite FTS5 (ranking bm25).
Es local, rapido y no usa IA para buscar. La IA solo redacta la respuesta
con los fragmentos encontrados y debe citar el documento.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from core.normalizar import clave

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")
_MAX = 900  # letras por fragmento (aprox.)
_STOP = set("""de la el los las un una unos unas y o en a al del con por para que se es son como cual cuales
cuando donde qué que me mi mis tu tus su sus lo le les ya hay debo debe deben hacer puedo puede segun sobre
cuanto cuantos cuantas quien quienes este esta estos estas ese esa eso muy mas menos si no""".split())


def _conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ChunksDoc (id INTEGER PRIMARY KEY, documento TEXT, seccion TEXT, "
        "texto TEXT, huella TEXT UNIQUE)"
    )
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS ChunksFTS USING fts5(documento, seccion, texto, "
        "content='ChunksDoc', content_rowid='id', tokenize='unicode61 remove_diacritics 2')"
    )
    return conn


def trocear(texto: str) -> List[Dict[str, str]]:
    """Parte un documento por titulos (#) y luego por parrafos hasta ~_MAX letras."""
    texto = re.sub(r"^---\n.*?\n---\n", "", texto, flags=re.S)  # quita cabecera yaml
    secciones, titulo, buf = [], "", []
    for linea in texto.splitlines():
        if re.match(r"^#{1,4}\s", linea):
            if buf:
                secciones.append((titulo, "\n".join(buf)))
            titulo, buf = linea.lstrip("# ").strip(), []
        else:
            buf.append(linea)
    if buf:
        secciones.append((titulo, "\n".join(buf)))
    out = []
    for tit, cuerpo in secciones:
        actual = ""
        for par in re.split(r"\n\s*\n", cuerpo):
            par = par.strip()
            if not par:
                continue
            if actual and len(actual) + len(par) > _MAX:
                out.append({"seccion": tit, "texto": actual})
                actual = ""
            actual = (actual + "\n\n" + par).strip()
        if actual:
            out.append({"seccion": tit, "texto": actual})
    return out


def reindexar(db_path: str = DB_PATH) -> Dict[str, int]:
    """Reconstruye el indice desde DocumentosTexto. Repetible: no crea copias."""
    conn = _conn(db_path)
    conn.execute("DELETE FROM ChunksDoc")
    docs = conn.execute(
        "SELECT d.nombre, t.contenido_completo FROM DocumentosRAG d JOIN DocumentosTexto t ON t.documento_id=d.id "
        "WHERE d.estado='activo' AND length(coalesce(t.contenido_completo,''))>200 AND d.tipo IN ('manual_bpm','capacitacion','generico') "
        "AND d.extension IN ('.md','.txt') ORDER BY d.id"
    ).fetchall()
    nombres = set()
    n = 0
    for d in docs:
        nombre = re.sub(r"\.(md|txt)$", "", d["nombre"])
        for ch in trocear(d["contenido_completo"]):
            h = hashlib.sha1((clave(nombre) + clave(ch["texto"])).encode()).hexdigest()
            try:
                conn.execute("INSERT INTO ChunksDoc (documento, seccion, texto, huella) VALUES (?,?,?,?)",
                             (nombre, ch["seccion"], ch["texto"], h))
                n += 1
                nombres.add(nombre)
            except sqlite3.IntegrityError:
                pass  # mismo fragmento ya indexado
    conn.execute("INSERT INTO ChunksFTS(ChunksFTS) VALUES('rebuild')")
    conn.commit()
    conn.close()
    return {"documentos": len(nombres), "fragmentos": n}


def _consulta_fts(pregunta: str) -> str:
    toks = [t for t in re.findall(r"[a-z0-9]+", clave(pregunta)) if t not in _STOP and len(t) > 2]
    # raiz simple: primeras 4 letras (alergico/alergenos -> aler*, lavarme/lavado -> lava*)
    terms = [(t[:4] if len(t) >= 6 else t[:-1] if len(t) == 5 else t) + "*" for t in toks]
    return " OR ".join(terms)


def buscar(pregunta: str, k: int = 4, db_path: str = DB_PATH, min_raices: int = 2) -> List[Dict[str, Any]]:
    q = _consulta_fts(pregunta)
    if not q:
        return []
    conn = _conn(db_path)
    try:
        filas = conn.execute(
            "SELECT c.documento, c.seccion, c.texto, bm25(ChunksFTS, 3.0, 2.0, 1.0) AS puntaje "
            "FROM ChunksFTS JOIN ChunksDoc c ON c.id = ChunksFTS.rowid WHERE ChunksFTS MATCH ? "
            "ORDER BY puntaje LIMIT ?", (q, k)
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
    # Un fragmento debe contener al menos 2 raices distintas de la pregunta (si ella tiene 2 o mas):
    # evita responder con un texto que solo comparte una palabra suelta.
    raices = [r.rstrip("*") for r in q.split(" OR ")]
    buenos = []
    for f in filas:
        cuerpo = clave(f["documento"] + " " + f["seccion"] + " " + f["texto"])
        if sum(1 for r in raices if r in cuerpo) >= min(min_raices, len(raices)):
            buenos.append(dict(f))
    return buenos


SISTEMA = (
    "Eres ChefChat, asistente de un restaurante. Responde SOLO con los fragmentos de documentos dados. "
    "Si la respuesta no esta en los fragmentos, di: 'No encuentro eso en los documentos cargados.' "
    "No inventes pasos ni datos. Responde en espanol, claro y corto. Al final escribe 'Fuente:' con el "
    "nombre del documento y la seccion."
)


def contexto(frags: List[Dict[str, Any]]) -> str:
    return "\n\n".join(f"[{f['documento']} > {f['seccion']}]\n{f['texto']}" for f in frags)
