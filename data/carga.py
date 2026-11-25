"""Cargar recetas (CSV) y manuales (md, txt, docx, pdf) desde la pantalla.

Todo se valida antes de guardar y se dice claro que se rechazo y por que.
Los archivos originales se guardan en data_source/ para no perderlos.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.normalizar import clave
from data import rag_docs, vinculos
from data.esquema import asegurar_esquema

RAIZ = Path(__file__).resolve().parent.parent
DB_PATH = str(RAIZ / "chefchat.db")
MAX_BYTES = 5 * 1024 * 1024
MAX_RECETAS_POR_ARCHIVO = 2000
MIN_LETRAS_MANUAL = 200

SINONIMOS = {
    "id_receta": ("id_receta", "id", "codigo"),
    "nombre": ("nombre_plato", "nombre", "plato", "receta"),
    "categoria": ("categoria",),
    "tiempo": ("tiempo_prep_min", "tiempo_prep", "tiempo", "minutos"),
    "costo": ("costo_estimado_usd", "costo_estimado", "costo", "precio_estimado"),
    "ingredientes": ("ingredientes_estructurados", "ingredientes"),
    "alergenos": ("alergenos",),
    "instrucciones": ("instrucciones", "preparacion", "pasos"),
}
OBLIGATORIAS = ("id_receta", "nombre", "ingredientes")


class CargaError(ValueError):
    """Error que se puede mostrar tal cual al usuario (HTTP 400)."""


def nombre_seguro(nombre: str) -> str:
    base = Path(nombre.replace("\\", "/")).name  # nunca rutas: solo el nombre
    base = re.sub(r"[^\w\-. ()áéíóúñÁÉÍÓÚÑüÜ]", "_", base).strip(" .")
    return base[:100] or "archivo"


def _texto(contenido: bytes) -> str:
    for cod in ("utf-8-sig", "cp1252"):
        try:
            return contenido.decode(cod)
        except UnicodeDecodeError:
            continue
    raise CargaError("No pude leer el texto del archivo. Guárdalo como UTF-8.")


def _num(txt: str) -> Optional[float]:
    t = (txt or "").strip().replace("$", "").replace(",", ".")
    try:
        return float(t) if t else None
    except ValueError:
        return None


def _validar_ingredientes(txt: str) -> int:
    """Cuantos ingredientes validos hay en 'cant|unidad|nombre; cant|unidad|nombre'."""
    n = 0
    for parte in (txt or "").split(";"):
        p = [x.strip() for x in parte.split("|")]
        if len(p) == 3 and p[2] and vinculos._numero(p[0]) is not None:
            n += 1
    return n


def _conn(db_path: str) -> sqlite3.Connection:
    asegurar_esquema(db_path)
    return sqlite3.connect(db_path)


# ---------------------------------------------------------------- recetas
def leer_recetas_csv(contenido: bytes) -> Dict[str, Any]:
    """Valida el CSV sin guardar nada. Devuelve {validas:[...], rechazadas:[{fila, motivo}]}."""
    if len(contenido) > MAX_BYTES:
        raise CargaError("El archivo pesa más de 5 MB.")
    texto = _texto(contenido)
    if not texto.strip():
        raise CargaError("El archivo está vacío.")
    cabecera = texto.splitlines()[0]
    delim = max((";", ",", "\t"), key=cabecera.count)
    lector = csv.DictReader(io.StringIO(texto), delimiter=delim)
    campos = {clave(c).replace(" ", "_"): c for c in (lector.fieldnames or [])}
    columna: Dict[str, str] = {}
    for k, opciones in SINONIMOS.items():
        for o in opciones:
            if o in campos:
                columna[k] = campos[o]
                break
    faltan = [k for k in OBLIGATORIAS if k not in columna]
    if faltan:
        nombres = {"id_receta": "ID_Receta", "nombre": "Nombre_Plato", "ingredientes": "Ingredientes_Estructurados"}
        raise CargaError("Faltan columnas obligatorias: " + ", ".join(nombres[f] for f in faltan) + ".")
    validas: List[Dict[str, Any]] = []
    rechazadas: List[Dict[str, Any]] = []
    vistos = set()
    for i, fila in enumerate(lector, start=2):
        if i - 1 > MAX_RECETAS_POR_ARCHIVO:
            raise CargaError(f"El archivo tiene más de {MAX_RECETAS_POR_ARCHIVO} recetas.")
        g = lambda k: (fila.get(columna.get(k, "")) or "").strip()  # noqa: E731
        rid, nombre = g("id_receta"), g("nombre")
        if not rid or not nombre:
            rechazadas.append({"fila": i, "motivo": "Falta el ID o el nombre del plato."})
            continue
        if clave(rid) in vistos:
            rechazadas.append({"fila": i, "motivo": f"El ID {rid} está repetido en el archivo."})
            continue
        if _validar_ingredientes(g("ingredientes")) == 0:
            rechazadas.append({"fila": i, "motivo": f"{nombre}: los ingredientes deben ser «cantidad|unidad|nombre; …»."})
            continue
        costo = _num(g("costo"))
        if g("costo") and (costo is None or costo < 0 or costo > 100000):
            rechazadas.append({"fila": i, "motivo": f"{nombre}: el costo no es un número válido."})
            continue
        tiempo = re.search(r"\d+", g("tiempo"))
        vistos.add(clave(rid))
        validas.append({"id_receta": rid, "nombre": nombre, "categoria": g("categoria") or "Sin categoría",
                        "tiempo_prep": int(tiempo.group()) if tiempo else None, "costo": costo,
                        "ingredientes": g("ingredientes"), "alergenos": g("alergenos") or "Ninguno",
                        "instrucciones": g("instrucciones")})
    if not validas and not rechazadas:
        raise CargaError("El archivo no tiene recetas.")
    return {"validas": validas, "rechazadas": rechazadas}


def cargar_recetas_csv(contenido: bytes, nombre_archivo: str, db_path: str = DB_PATH,
                       carpeta: Optional[Path] = None) -> Dict[str, Any]:
    leidas = leer_recetas_csv(contenido)
    if not leidas["validas"]:
        raise CargaError("Ninguna receta es válida. Primer problema: " + leidas["rechazadas"][0]["motivo"])
    nombre = nombre_seguro(nombre_archivo)
    if not nombre.lower().endswith(".csv"):
        nombre += ".csv"
    carpeta = carpeta or RAIZ / "data_source" / "1_recetas"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre
    destino.write_bytes(contenido)
    conn = _conn(db_path)
    try:
        doc = conn.execute("SELECT id FROM DocumentosRAG WHERE nombre=? AND tipo='receta' AND estado='activo'", (nombre,)).fetchone()
        if doc:
            doc_id = doc[0]
        else:
            doc_id = conn.execute(
                "INSERT INTO DocumentosRAG (tipo, nombre, path, extension, tamano_bytes, columnas, filas, contenido_preview) "
                "VALUES ('receta', ?, ?, '.csv', ?, '[]', ?, '')", (nombre, str(destino), len(contenido), len(leidas["validas"]))).lastrowid
        nuevas = actualizadas = 0
        for r in leidas["validas"]:
            ya = conn.execute("SELECT id FROM RecetasRAG WHERE id_receta=?", (r["id_receta"],)).fetchone()
            if ya:
                conn.execute("UPDATE RecetasRAG SET nombre=?, categoria=?, tiempo_prep=?, costo=?, ingredientes_json=?, alergenos=?, "
                             "instrucciones=? WHERE id=?", (r["nombre"], r["categoria"], r["tiempo_prep"], r["costo"], r["ingredientes"],
                                                            r["alergenos"], r["instrucciones"], ya[0]))
                actualizadas += 1
            else:
                conn.execute("INSERT INTO RecetasRAG (documento_id, id_receta, nombre, categoria, tiempo_prep, costo, ingredientes_json, "
                             "alergenos, instrucciones) VALUES (?,?,?,?,?,?,?,?,?)",
                             (doc_id, r["id_receta"], r["nombre"], r["categoria"], r["tiempo_prep"], r["costo"], r["ingredientes"],
                              r["alergenos"], r["instrucciones"]))
                nuevas += 1
        vinculos.paso_ingredientes(conn, limpiar_auto=False)  # liga los ingredientes nuevos con el catalogo
        conn.commit()
        return {"archivo": nombre, "nuevas": nuevas, "actualizadas": actualizadas, "rechazadas": leidas["rechazadas"][:20],
                "n_rechazadas": len(leidas["rechazadas"])}
    finally:
        conn.close()


# ---------------------------------------------------------------- manuales
def extraer_texto(contenido: bytes, nombre_archivo: str) -> str:
    if len(contenido) > MAX_BYTES:
        raise CargaError("El archivo pesa más de 5 MB.")
    ext = Path(nombre_archivo).suffix.lower()
    if ext in (".md", ".txt"):
        texto = _texto(contenido)
    elif ext == ".pdf":
        if not contenido.startswith(b"%PDF"):
            raise CargaError("El archivo no es un PDF válido.")
        try:
            from pypdf import PdfReader
            lector = PdfReader(io.BytesIO(contenido))
            if len(lector.pages) > 300:
                raise CargaError("El PDF tiene más de 300 páginas.")
            texto = "\n\n".join((p.extract_text() or "").strip() for p in lector.pages)
        except CargaError:
            raise
        except Exception:
            raise CargaError("No pude leer el PDF. Puede estar dañado o protegido.") from None
    elif ext == ".docx":
        if not zipfile.is_zipfile(io.BytesIO(contenido)):
            raise CargaError("El archivo no es un Word (.docx) válido.")
        try:
            from docx import Document
            doc = Document(io.BytesIO(contenido))
            partes = []
            for p in doc.paragraphs:
                t = p.text.strip()
                if not t:
                    continue
                estilo = (p.style.name or "").lower() if p.style is not None else ""
                m = re.match(r"(heading|título|titulo)\s*(\d)", estilo)
                partes.append(("#" * min(int(m.group(2)), 4) + " " + t) if m else t)
            for tabla in doc.tables:
                for fila in tabla.rows:
                    partes.append(" | ".join(c.text.strip() for c in fila.cells))
            texto = "\n\n".join(partes)
        except Exception:
            raise CargaError("No pude leer el Word. Puede estar dañado.") from None
    else:
        raise CargaError("Solo acepto archivos .md, .txt, .docx o .pdf.")
    texto = texto.replace("\x00", "").strip()
    if len(texto) < MIN_LETRAS_MANUAL:
        raise CargaError("El archivo casi no tiene texto." + (" Si es un PDF escaneado, necesita pasar por un lector de texto (OCR)." if ext == ".pdf" else ""))
    return texto


def cargar_manual(contenido: bytes, nombre_archivo: str, db_path: str = DB_PATH, carpeta: Optional[Path] = None) -> Dict[str, Any]:
    texto = extraer_texto(contenido, nombre_archivo)
    seguro = nombre_seguro(nombre_archivo)
    nombre = Path(seguro).stem + ".md"
    carpeta = carpeta or RAIZ / "data_source" / "manuales"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / seguro
    destino.write_bytes(contenido)
    palabras = sorted({w for w in re.findall(r"[a-záéíóúñ]{5,}", texto.lower())})[:40]
    conn = _conn(db_path)
    try:
        doc = conn.execute("SELECT id FROM DocumentosRAG WHERE nombre=? AND tipo='manual_bpm' AND estado='activo' ORDER BY id LIMIT 1",
                           (nombre,)).fetchone()
        reemplazo = doc is not None
        if doc:
            doc_id = doc[0]
            conn.execute("UPDATE DocumentosRAG SET path=?, tamano_bytes=?, contenido_preview=? WHERE id=?",
                         (str(destino), len(contenido), texto[:300], doc_id))
            conn.execute("DELETE FROM DocumentosTexto WHERE documento_id=?", (doc_id,))
        else:
            doc_id = conn.execute(
                "INSERT INTO DocumentosRAG (tipo, nombre, path, extension, tamano_bytes, columnas, filas, contenido_preview) "
                "VALUES ('manual_bpm', ?, ?, '.md', ?, '[]', 0, ?)", (nombre, str(destino), len(contenido), texto[:300])).lastrowid
        conn.execute("INSERT INTO DocumentosTexto (documento_id, contenido_completo, palabras_clave) VALUES (?,?,?)",
                     (doc_id, texto, json.dumps(palabras, ensure_ascii=False)))
        conn.commit()
    finally:
        conn.close()
    r = rag_docs.reindexar(db_path)
    return {"archivo": nombre, "caracteres": len(texto), "reemplazo": reemplazo, "manuales": r["documentos"], "fragmentos": r["fragmentos"]}
